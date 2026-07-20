"""
VGK Team Member Auth API Endpoints (DC Protocol Mar 2026)
Separate JWT auth for VGK_TEAM official partners (member portal).
"""

import logging
import re as _re
from fastapi import APIRouter, Depends, HTTPException, status, Request, UploadFile, File, Form, Body
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

from decimal import Decimal

from app.core.database import get_db
from app.core.security import SecurityManager
from app.core.config import settings
from app.models.staff_accounts import OfficialPartner, VGKTeamIncomeEntry, PartnerOrder, VGKPINPurchaseRequest, VGKPointsLedger
from app.models.crm import CRMLead
from app.models.ticket import ServiceTicket
from app.models.kyc_document import KYCDocument
from app.services.universal_upload_service import UniversalUploadService
from sqlalchemy import func, text as sa_text

router = APIRouter()

# [DC-PERF-001] Module-level QR cache — partner referral URL never changes so we
# generate once per partner per process lifetime instead of on every request.
_qr_b64_cache: dict = {}  # partner_code → base64 PNG data-URI string


def _setattr_safe(obj, attr: str, val):
    """Silently set an attribute only if the column exists on the model (safe for migrated columns)."""
    try:
        if hasattr(obj.__class__, attr) or attr in obj.__mapper__.columns.keys():
            setattr(obj, attr, val)
    except Exception:
        try:
            setattr(obj, attr, val)
        except Exception:
            pass


def get_indian_time():
    from pytz import timezone
    return datetime.now(timezone('Asia/Kolkata'))


class VGKLoginRequest(BaseModel):
    identifier: str = Field(..., description="Partner Code or Phone")
    password: str = Field(..., min_length=1)


class VGKLoginResponse(BaseModel):
    success: bool
    message: str
    access_token: Optional[str] = None
    token_type: str = "bearer"
    partner: Optional[dict] = None
    terms_and_conditions: Optional[dict] = None
    requires_terms_acceptance: bool = False


def get_current_vgk_member(request: Request, db: Session = Depends(get_db)) -> OfficialPartner:
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authorization header",
                            headers={"WWW-Authenticate": "Bearer"})
    token = auth_header.split(" ")[1]
    try:
        from jose import jwt, JWTError
        from jose.exceptions import ExpiredSignatureError
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        if payload.get("user_type") != "vgk_member":
            raise HTTPException(status_code=401, detail="Invalid token type")
        partner_id = int(payload.get("sub"))
        partner = db.query(OfficialPartner).filter(
            OfficialPartner.id == partner_id,
            OfficialPartner.category == 'VGK_TEAM'
        ).first()
        if not partner:
            raise HTTPException(status_code=401, detail="VGK member not found")
        return partner
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid or expired token",
                            headers={"WWW-Authenticate": "Bearer"})


@router.post("/auth/login", response_model=VGKLoginResponse)
def vgk_login(request: VGKLoginRequest, db: Session = Depends(get_db)):
    identifier = request.identifier.strip()
    partner = db.query(OfficialPartner).filter(
        OfficialPartner.category == 'VGK_TEAM',
        or_(
            OfficialPartner.partner_code.ilike(identifier),
            OfficialPartner.phone == identifier
        )
    ).first()

    if not partner:
        return VGKLoginResponse(success=False, message="Invalid credentials")

    if not partner.password_hash:
        return VGKLoginResponse(success=False, message="Password not set. Contact admin.")

    if not SecurityManager.verify_password(request.password, partner.password_hash):
        partner.failed_login_attempts = (partner.failed_login_attempts or 0) + 1
        try:
            db.commit()
        except Exception:
            db.rollback()
        return VGKLoginResponse(success=False, message="Invalid credentials")

    partner.failed_login_attempts = 0
    partner.last_login = get_indian_time()
    partner.login_count = (partner.login_count or 0) + 1
    _current_login_count = partner.login_count
    try:
        db.commit()
    except Exception:
        db.rollback()
        _current_login_count = 0

    # [DC-REFERRAL] Credit 1,000 pts to referrer at exactly the 3rd login of referred member
    if _current_login_count == 3 and partner.parent_partner_id:
        try:
            from app.services.vgk_commission import add_vgk_points_entry
            referrer = db.query(OfficialPartner).filter(
                OfficialPartner.id == partner.parent_partner_id,
                OfficialPartner.category == 'VGK_TEAM'
            ).first()
            if referrer and referrer.partner_code != VGK_DEFAULT_ROOT:
                add_vgk_points_entry(
                    db=db,
                    partner_id=referrer.id,
                    points_credit=Decimal('1000'),
                    points_debit=Decimal('0'),
                    reason_code='CAMPAIGN_BONUS',
                    reference_type='referral_login',
                    reference_id=partner.id,
                    notes=f'Referral login reward — {partner.partner_code} completed 3rd login',
                    created_by=None,
                )
                db.commit()
                logger.info(f"[DC-REFERRAL] 1,000 pts credited to {referrer.partner_code} for 3rd login of referred {partner.partner_code}")
        except Exception as _rl:
            logger.warning(f"[DC-REFERRAL] Referral login reward failed: {_rl}")
            try:
                db.rollback()
            except Exception:
                pass

    from jose import jwt
    from datetime import timedelta
    payload = {
        "sub": str(partner.id),
        "user_type": "vgk_member",
        "partner_code": partner.partner_code,
        "partner_name": partner.partner_name,
        "category": "VGK_TEAM",
        "vgk_role": partner.vgk_role,
        "company_id": partner.company_id,
        "exp": get_indian_time() + timedelta(hours=24)
    }
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

    logger.info(f"[VGK-AUTH] Login success: {partner.partner_code}")

    # DC Protocol Mar 2026: Check if VGK-platform T&C acceptance is needed
    tc_payload = None
    needs_tc = False
    try:
        from app.models.system_control import TermsAndConditionsVersion
        from sqlalchemy import or_ as sa_or
        _vgk_f = sa_or(
            TermsAndConditionsVersion.platform_type == 'VGK',
            TermsAndConditionsVersion.platform_type == 'ALL',
        )
        active_tc = db.query(TermsAndConditionsVersion).filter(
            TermsAndConditionsVersion.is_active == True, _vgk_f
        ).order_by(TermsAndConditionsVersion.id.desc()).first()
        if not active_tc:
            active_tc = db.query(TermsAndConditionsVersion).filter(
                _vgk_f
            ).order_by(TermsAndConditionsVersion.id.desc()).first()
        if active_tc:
            partner_accepted = getattr(partner, 'accepted_terms_version', None)
            if partner_accepted != active_tc.version:
                needs_tc = True
            tc_payload = {
                "version": active_tc.version,
                "content": active_tc.content,
                "activated_at": active_tc.activated_at.isoformat() if active_tc.activated_at else None,
            }
    except Exception as _tc_err:
        logger.warning(f"[VGK-AUTH] T&C lookup failed (non-fatal): {_tc_err}")

    return VGKLoginResponse(
        success=True,
        message="Login successful",
        access_token=token,
        partner={
            "id": partner.id,
            "partner_code": partner.partner_code,
            "partner_name": partner.partner_name,
            "vgk_role": partner.vgk_role,
            "company_id": partner.company_id
        },
        terms_and_conditions=tc_payload,
        requires_terms_acceptance=needs_tc,
    )


@router.get("/auth/me")
def vgk_me(current_member: OfficialPartner = Depends(get_current_vgk_member), db: Session = Depends(get_db)):
    d = current_member.to_dict()
    if current_member.parent_partner_id:
        ref = db.query(OfficialPartner).filter(OfficialPartner.id == current_member.parent_partner_id).first()
        d['referrer_name'] = ref.partner_name if ref else None
        d['referrer_code'] = ref.partner_code if ref else None

    # T&C check — same as login so already-logged-in members also see pending T&C
    tc_payload = None
    needs_tc = False
    try:
        from app.models.system_control import TermsAndConditionsVersion
        from sqlalchemy import or_ as _sa_or
        _vgk_f2 = _sa_or(
            TermsAndConditionsVersion.platform_type == 'VGK',
            TermsAndConditionsVersion.platform_type == 'ALL',
        )
        active_tc = db.query(TermsAndConditionsVersion).filter(
            TermsAndConditionsVersion.is_active == True, _vgk_f2
        ).order_by(TermsAndConditionsVersion.id.desc()).first()
        if not active_tc:
            active_tc = db.query(TermsAndConditionsVersion).filter(
                _vgk_f2
            ).order_by(TermsAndConditionsVersion.id.desc()).first()
        if active_tc:
            partner_accepted = getattr(current_member, 'accepted_terms_version', None)
            if partner_accepted != active_tc.version:
                needs_tc = True
            tc_payload = {
                "version": active_tc.version,
                "content": active_tc.content,
                "activated_at": active_tc.activated_at.isoformat() if active_tc.activated_at else None,
            }
    except Exception as _tc_err:
        logger.warning(f"[VGK-ME] T&C lookup failed (non-fatal): {_tc_err}")

    return {
        "success": True,
        "data": d,
        "requires_terms_acceptance": needs_tc,
        "terms_and_conditions": tc_payload,
    }


@router.get("/member/visiting-card")
def vgk_visiting_card(
    current_member: OfficialPartner = Depends(get_current_vgk_member),
    db: Session = Depends(get_db)
):
    """DC Protocol Apr 2026: Return VGK member's visiting card data + eligibility status.
    Eligibility tiers:
      - Source (L1): revenue >= 5,00,000
      - Guru   (L2): revenue >= 10,00,000
      - Z-Guru (L3): revenue >= 20,00,000
      - Support(L4): revenue >=  5,00,000
    Any tier reaching its threshold → card_eligible = True.
    """
    import qrcode, io, base64 as _b64
    pid = current_member.id

    # ── Income per level (RELEASED + PENDING count as business done) ───────────
    rows = db.execute(sa_text(
        "SELECT level, COALESCE(SUM(revenue_amount),0) AS rev "
        "FROM vgk_team_income_entries "
        "WHERE partner_id = :pid AND status IN ('RELEASED','PENDING','CONFIRMED') "
        "GROUP BY level"
    ), {"pid": pid}).fetchall()
    rev_by_level = {int(r[0]): float(r[1]) for r in rows}

    L1 = rev_by_level.get(1, 0.0)
    L2 = rev_by_level.get(2, 0.0)
    L3 = rev_by_level.get(3, 0.0)
    L4 = rev_by_level.get(4, 0.0)

    THRESHOLDS = {1: 500000, 2: 1000000, 3: 2000000, 4: 500000}
    TIER_LABELS = {1: "Source", 2: "Guru", 3: "Z-Guru", 4: "Support"}

    eligible_tier   = None
    best_pct        = 0.0
    best_level_num  = 1
    best_rev        = L1
    best_threshold  = THRESHOLDS[1]

    for lvl, threshold in THRESHOLDS.items():
        rev = rev_by_level.get(lvl, 0.0)
        pct = min(100.0, (rev / threshold) * 100) if threshold else 0
        if rev >= threshold and eligible_tier is None:
            eligible_tier = TIER_LABELS[lvl]
        if pct > best_pct:
            best_pct       = pct
            best_level_num = lvl
            best_rev       = rev
            best_threshold = threshold

    card_eligible = eligible_tier is not None

    # ── Build referral QR code as base64 ──────────────────────────────────────
    host = "https://www.vgk4u.com"
    referral_url = f"{host}/vgk/login?tab=signup&ref={current_member.partner_code}"
    qr_b64 = ""
    try:
        qr = qrcode.QRCode(version=2, box_size=12, border=3,
                           error_correction=qrcode.constants.ERROR_CORRECT_M)
        qr.add_data(referral_url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buf = io.BytesIO()
        img.save(buf, format='PNG')
        qr_b64 = "data:image/png;base64," + _b64.b64encode(buf.getvalue()).decode()
    except Exception as _qe:
        logger.warning(f"[DC-VCARD] QR generation failed: {_qe}")

    # ── Name & location ───────────────────────────────────────────────────────
    safe_get = lambda attr: (getattr(current_member, attr, None) or '')
    name_title = safe_get('name_title')
    first_name  = safe_get('first_name')
    last_name   = safe_get('last_name')
    gender      = safe_get('gender')
    city        = safe_get('city')
    address     = safe_get('address')
    display_name = current_member.partner_name or ''
    if first_name and last_name:
        display_name = ' '.join(p for p in [name_title, first_name, last_name] if p)
    elif name_title and display_name and not display_name.startswith(name_title):
        display_name = f"{name_title} {display_name}"

    location = city or ''
    if address and not city:
        location = address.split(',')[-1].strip() if ',' in address else address

    # [DC-PASSPORT-PHOTO] Include approved passport photo URL for ID card display
    passport_photo_url = ''
    try:
        pp_doc = db.query(KYCDocument).filter(
            KYCDocument.partner_id == current_member.id,
            KYCDocument.document_type == 'passport_photo',
            KYCDocument.status == 'Approved'
        ).first()
        if pp_doc and pp_doc.file_path:
            passport_photo_url = f'/storage/{pp_doc.file_path}'
    except Exception:
        pass

    return {
        "success": True,
        "card_eligible": card_eligible,
        "eligible_tier": eligible_tier,
        "progress": {
            "best_level": best_level_num,
            "best_level_label": TIER_LABELS[best_level_num],
            "current_revenue": best_rev,
            "threshold": best_threshold,
            "percentage": round(best_pct, 1),
            "gap": max(0.0, best_threshold - best_rev),
        },
        "all_levels": {
            f"L{lvl}": {
                "revenue": rev_by_level.get(lvl, 0.0),
                "threshold": thr,
                "pct": round(min(100, rev_by_level.get(lvl, 0) / thr * 100), 1) if thr else 0,
                "label": TIER_LABELS[lvl],
            }
            for lvl, thr in THRESHOLDS.items()
        },
        "card_data": {
            "partner_code":      current_member.partner_code,
            "display_name":      display_name,
            "name_title":        name_title,
            "first_name":        first_name,
            "last_name":         last_name,
            "gender":            gender,
            "phone":             current_member.phone or '',
            "company_phone":     "+91 858585 2738",
            "city":              city,
            "location":          location,
            "referral_url":      referral_url,
            "qr_b64":            qr_b64,
            "blood_group":       getattr(current_member, 'blood_group', None) or '',
            "passport_photo_url": passport_photo_url,
            "designation_label": _compute_cp_designation(current_member, db).get("tier_label", "Channel Partner"),
        },
    }


class _CardFlagsPayload(BaseModel):
    vcard_enabled:  Optional[bool] = None
    idcard_enabled: Optional[bool] = None


@router.patch("/staff/card-flags/{member_id}")
def vgk_staff_patch_card_flags(
    member_id: int,
    payload: _CardFlagsPayload = Body(...),
    db: Session = Depends(get_db),
    request: Request = None,
):
    """[DC-CARD-FLAGS-001] Any staff can toggle vcard_enabled / idcard_enabled for a VGK member.
    Only those two fields are writable through this endpoint (no other member data touched).
    """
    from app.api.v1.endpoints.staff_auth import get_current_staff_user
    from app.models.staff import StaffEmployee

    try:
        get_current_staff_user(request, db)
    except Exception:
        raise HTTPException(status_code=401, detail="Staff authentication required.")

    member = db.query(OfficialPartner).filter(
        OfficialPartner.id == member_id,
        OfficialPartner.category == 'VGK_TEAM'
    ).first()
    if not member:
        raise HTTPException(status_code=404, detail="Member not found.")

    changed = False
    if payload.vcard_enabled is not None:
        member.vcard_enabled = payload.vcard_enabled
        changed = True
    if payload.idcard_enabled is not None:
        member.idcard_enabled = payload.idcard_enabled
        changed = True

    if changed:
        db.commit()
        db.refresh(member)

    return {"success": True, "vcard_enabled": bool(member.vcard_enabled), "idcard_enabled": bool(member.idcard_enabled)}


@router.get("/staff/member-card/{member_id}")
def vgk_staff_member_card(
    member_id: int,
    db: Session = Depends(get_db),
    request: Request = None,
):
    """[DC-ID-CARD-STAFF] Staff-only endpoint: returns card_data for any VGK member.
    No earnings threshold check. Accessible only to MR10001 (VGK Mentor) and EA designation staff.
    Auth: Staff JWT (Authorization: Bearer <token>).
    """
    import qrcode, io, base64 as _b64
    from app.api.v1.endpoints.staff_auth import get_current_staff_user
    from app.models.staff import StaffEmployee

    # ── Staff auth + role gate ─────────────────────────────────────────────
    try:
        staff: StaffEmployee = get_current_staff_user(request, db)
    except Exception:
        raise HTTPException(status_code=401, detail="Staff authentication required.")

    # [DC-ID-CARD-STAFF-FIX] Any authenticated staff may view member cards.
    # (Previously restricted to MR10001/EA — too narrow; any staff with page access should work.)

    # ── Fetch the target member ─────────────────────────────────────────────
    member = db.query(OfficialPartner).filter(
        OfficialPartner.id == member_id,
        OfficialPartner.category == 'VGK_TEAM'
    ).first()
    if not member:
        raise HTTPException(status_code=404, detail="Member not found.")

    # ── Build QR code ──────────────────────────────────────────────────────
    host = "https://www.vgk4u.com"
    referral_url = f"{host}/vgk/login?tab=signup&ref={member.partner_code}"
    qr_b64 = ""
    try:
        qr = qrcode.QRCode(version=2, box_size=12, border=3,
                           error_correction=qrcode.constants.ERROR_CORRECT_M)
        qr.add_data(referral_url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buf = io.BytesIO()
        img.save(buf, format='PNG')
        qr_b64 = "data:image/png;base64," + _b64.b64encode(buf.getvalue()).decode()
    except Exception as _qe:
        logger.warning(f"[DC-VCARD-STAFF] QR generation failed: {_qe}")

    # ── Build name & location ──────────────────────────────────────────────
    safe = lambda attr: (getattr(member, attr, None) or '')
    name_title   = safe('name_title')
    first_name   = safe('first_name')
    last_name    = safe('last_name')
    gender       = safe('gender')
    city         = safe('city')
    address      = safe('address')
    display_name = member.partner_name or ''
    if first_name and last_name:
        display_name = ' '.join(p for p in [name_title, first_name, last_name] if p)
    elif name_title and display_name and not display_name.startswith(name_title):
        display_name = f"{name_title} {display_name}"
    location = city or ''
    if address and not city:
        location = address.split(',')[-1].strip() if ',' in address else address
    # [DC-PASSPORT-PHOTO] Same lookup as member-card-preview endpoint
    passport_photo_url = ''
    try:
        pp_doc = db.query(KYCDocument).filter(
            KYCDocument.partner_id == member.id,
            KYCDocument.document_type == 'passport_photo',
            KYCDocument.status == 'Approved'
        ).first()
        if pp_doc and pp_doc.file_path:
            passport_photo_url = f'/storage/{pp_doc.file_path}'
    except Exception:
        pass

    return {
        "success": True,
        "card_data": {
            "partner_code":       member.partner_code,
            "display_name":       display_name,
            "name_title":         name_title,
            "first_name":         first_name,
            "last_name":          last_name,
            "gender":             gender,
            "phone":              member.phone or '',
            "company_phone":      "+91 858585 2738",
            "city":               city,
            "location":           location,
            "referral_url":       referral_url,
            "qr_b64":             qr_b64,
            "blood_group":        getattr(member, 'blood_group', None) or '',
            "passport_photo_url": passport_photo_url,
            "designation_label":  _compute_cp_designation(member, db).get("tier_label", "Channel Partner"),
        },
    }


# [DC-ID-CARD-MEMBER] VGK member JWT ─ is-card-admin check (no staff token required)
@router.get("/auth/is-card-admin")
def vgk_is_card_admin(
    current_member: OfficialPartner = Depends(get_current_vgk_member),
    db: Session = Depends(get_db),
):
    """Returns card visibility flags for the logged-in VGK member."""
    return {
        "is_card_admin":  bool(getattr(current_member, 'is_card_admin',  False)),
        "vcard_enabled":  bool(getattr(current_member, 'vcard_enabled',  False)),
        "idcard_enabled": bool(getattr(current_member, 'idcard_enabled', False)),
        "member_id": current_member.id,
    }


# [DC-ID-CARD-MEMBER] VGK member JWT ─ OWN card data — no gate, every member can view their own
@router.get("/member-card-preview/me")
def vgk_member_own_card_preview(
    current_member: OfficialPartner = Depends(get_current_vgk_member),
    db: Session = Depends(get_db),
):
    """Returns card data for the currently logged-in VGK member. No is_card_admin required."""
    import qrcode, io, base64 as _b64
    member = current_member
    host = "https://www.vgk4u.com"
    referral_url = f"{host}/vgk/login?tab=signup&ref={member.partner_code}"
    qr_b64 = ""
    try:
        qr = qrcode.QRCode(version=2, box_size=12, border=3,
                           error_correction=qrcode.constants.ERROR_CORRECT_M)
        qr.add_data(referral_url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buf = io.BytesIO()
        img.save(buf, format='PNG')
        qr_b64 = "data:image/png;base64," + _b64.b64encode(buf.getvalue()).decode()
    except Exception as _qe:
        pass
    safe = lambda attr: (getattr(member, attr, None) or '')
    name_title   = safe('name_title')
    first_name   = safe('first_name')
    last_name    = safe('last_name')
    city         = safe('city')
    address      = safe('address')
    display_name = member.partner_name or ''
    if first_name and last_name:
        display_name = ' '.join(p for p in [name_title, first_name, last_name] if p)
    elif name_title and display_name and not display_name.startswith(name_title):
        display_name = f"{name_title} {display_name}"
    location = city or ''
    if address and not city:
        location = address.split(',')[-1].strip() if ',' in address else address
    # [DC-PASSPORT-PHOTO] Include approved passport photo URL for ID card display
    passport_photo_url = ''
    try:
        pp_doc = db.query(KYCDocument).filter(
            KYCDocument.partner_id == member.id,
            KYCDocument.document_type == 'passport_photo',
            KYCDocument.status == 'Approved'
        ).first()
        if pp_doc and pp_doc.file_path:
            passport_photo_url = f'/storage/{pp_doc.file_path}'
    except Exception:
        pass
    return {
        "success": True,
        "card_data": {
            "partner_code":       member.partner_code,
            "display_name":       display_name,
            "name_title":         name_title,
            "first_name":         first_name,
            "last_name":          last_name,
            "gender":             safe('gender'),
            "phone":              member.phone or '',
            "company_phone":      "+91 858585 2738",
            "city":               city,
            "location":           location,
            "referral_url":       referral_url,
            "qr_b64":             qr_b64,
            "blood_group":        safe('blood_group'),
            "passport_photo_url": passport_photo_url,
            "designation_label":  _compute_cp_designation(member, db).get("tier_label", "Channel Partner"),
        }
    }


# [DC-ID-CARD-MEMBER] VGK member JWT ─ card data for authorized members (MR10001/EA phone match)
@router.get("/member-card-preview/{member_id}")
def vgk_member_card_preview(
    member_id: int,
    current_member: OfficialPartner = Depends(get_current_vgk_member),
    db: Session = Depends(get_db),
):
    """[DC-ID-CARD-MEMBER] VGK member auth version of the staff card preview.
    Gate: logged-in member's phone must match a MR10001 or EA staff employee.
    """
    import qrcode, io, base64 as _b64

    # ── Role gate: is_card_admin flag on the logged-in VGK member ─────────
    if not bool(getattr(current_member, 'is_card_admin', False)):
        raise HTTPException(status_code=403, detail="Not authorised to preview member cards.")

    # ── Fetch target member ────────────────────────────────────────────────
    member = db.query(OfficialPartner).filter(
        OfficialPartner.id == member_id,
        OfficialPartner.category == 'VGK_TEAM'
    ).first()
    if not member:
        raise HTTPException(status_code=404, detail="Member not found.")

    # ── QR code ────────────────────────────────────────────────────────────
    host = "https://www.vgk4u.com"
    referral_url = f"{host}/vgk/login?tab=signup&ref={member.partner_code}"
    qr_b64 = ""
    try:
        qr = qrcode.QRCode(version=2, box_size=12, border=3,
                           error_correction=qrcode.constants.ERROR_CORRECT_M)
        qr.add_data(referral_url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buf = io.BytesIO()
        img.save(buf, format='PNG')
        qr_b64 = "data:image/png;base64," + _b64.b64encode(buf.getvalue()).decode()
    except Exception as _qe:
        logger.warning(f"[DC-VCARD-MEMBER] QR generation failed: {_qe}")

    # ── Name / location ────────────────────────────────────────────────────
    safe = lambda attr: (getattr(member, attr, None) or '')
    name_title   = safe('name_title')
    first_name   = safe('first_name')
    last_name    = safe('last_name')
    gender       = safe('gender')
    city         = safe('city')
    address      = safe('address')
    display_name = member.partner_name or ''
    if first_name and last_name:
        display_name = ' '.join(p for p in [name_title, first_name, last_name] if p)
    elif name_title and display_name and not display_name.startswith(name_title):
        display_name = f"{name_title} {display_name}"
    location = city or ''
    if address and not city:
        location = address.split(',')[-1].strip() if ',' in address else address

    # [DC-PASSPORT-PHOTO] Include approved passport photo URL for ID card display
    passport_photo_url = ''
    try:
        pp_doc = db.query(KYCDocument).filter(
            KYCDocument.partner_id == member.id,
            KYCDocument.document_type == 'passport_photo',
            KYCDocument.status == 'Approved'
        ).first()
        if pp_doc and pp_doc.file_path:
            passport_photo_url = f'/storage/{pp_doc.file_path}'
    except Exception:
        pass

    return {
        "success": True,
        "card_data": {
            "partner_code":       member.partner_code,
            "display_name":       display_name,
            "name_title":         name_title,
            "first_name":         first_name,
            "last_name":          last_name,
            "gender":             gender,
            "phone":              member.phone or '',
            "company_phone":      "+91 858585 2738",
            "city":               city,
            "location":           location,
            "referral_url":       referral_url,
            "qr_b64":             qr_b64,
            "blood_group":        getattr(member, 'blood_group', None) or '',
            "passport_photo_url": passport_photo_url,
            "designation_label":  _compute_cp_designation(member, db).get("tier_label", "Channel Partner"),
        },
    }


@router.get("/dashboard/earnings")
def vgk_my_earnings(
    current_member: OfficialPartner = Depends(get_current_vgk_member),
    db: Session = Depends(get_db)
):
    entries = db.query(VGKTeamIncomeEntry).filter(
        VGKTeamIncomeEntry.company_id == current_member.company_id,
        VGKTeamIncomeEntry.partner_id == current_member.id,
        VGKTeamIncomeEntry.status != 'CANCELLED',
    ).order_by(VGKTeamIncomeEntry.id.desc()).limit(50).all()

    from pytz import timezone
    now = datetime.now(timezone('Asia/Kolkata'))
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    total_pending = sum(float(e.commission_amount or 0) + float(e.bonus_amount or 0) for e in entries if e.status == 'PENDING')
    total_confirmed = sum(float(e.commission_amount or 0) + float(e.bonus_amount or 0) for e in entries if e.status == 'CONFIRMED')
    this_month = sum(
        float(e.commission_amount or 0) + float(e.bonus_amount or 0)
        for e in entries
        if e.status != 'CANCELLED' and e.created_at and e.created_at.replace(tzinfo=None) >= month_start.replace(tzinfo=None)
    )

    return {
        "success": True,
        "summary": {
            "points_balance": float(current_member.vgk_points_balance or 0),
            "total_pending": total_pending,
            "total_confirmed": total_confirmed,
            "this_month": this_month
        },
        "data": [e.to_dict() for e in entries]
    }


@router.get("/dashboard/network")
def vgk_my_network(
    current_member: OfficialPartner = Depends(get_current_vgk_member),
    db: Session = Depends(get_db)
):
    upline = []
    current = current_member
    for _ in range(3):
        if not current.parent_partner_id:
            break
        parent = db.query(OfficialPartner).filter(OfficialPartner.id == current.parent_partner_id).first()
        if not parent:
            break
        upline.append({
            "id": parent.id, "partner_code": parent.partner_code,
            "partner_name": parent.partner_name, "is_active": parent.is_active
        })
        current = parent

    def build_down(p: OfficialPartner, depth: int) -> dict:
        # [DC-REFERRAL] Include referrer (parent) data for team referral columns
        parent_code = None
        if p.parent_partner_id:
            _parent = db.query(OfficialPartner.partner_code).filter(
                OfficialPartner.id == p.parent_partner_id
            ).first()
            parent_code = _parent[0] if _parent else None
        node = {
            "id": p.id, "partner_code": p.partner_code, "partner_name": p.partner_name,
            "is_active": p.is_active, "vgk_points_balance": float(p.vgk_points_balance or 0),
            "vgk_activated_at": p.vgk_activated_at.isoformat() if p.vgk_activated_at else None,
            "created_at": p.created_at.isoformat() if p.created_at else None,
            "parent_partner_code": parent_code,
            "children": []
        }
        direct_count = db.query(OfficialPartner).filter(
            OfficialPartner.parent_partner_id == p.id,
            OfficialPartner.category == 'VGK_TEAM'
        ).count()
        node["direct_count"] = direct_count
        if depth > 0 and direct_count > 0:
            kids = db.query(OfficialPartner).filter(
                OfficialPartner.parent_partner_id == p.id,
                OfficialPartner.category == 'VGK_TEAM'
            ).order_by(OfficialPartner.id).all()
            node["children"] = [build_down(k, depth - 1) for k in kids]
        return node

    downline = build_down(current_member, depth=3)

    # [DC-REFERRAL] Referral reward summary: points earned from each referred member's events
    from app.models.staff_accounts import VGKPointsLedger
    referral_rewards = {}
    try:
        reward_entries = db.query(VGKPointsLedger).filter(
            VGKPointsLedger.partner_id == current_member.id,
            VGKPointsLedger.reference_type.in_(['referral_login', 'referral_activation']),
        ).order_by(VGKPointsLedger.created_at.asc()).all()
        for entry in reward_entries:
            ref_id = str(entry.reference_id) if entry.reference_id else None
            if ref_id:
                if ref_id not in referral_rewards:
                    referral_rewards[ref_id] = {"points": 0, "last_date": None}
                referral_rewards[ref_id]["points"] += float(entry.points_credit or 0)
                referral_rewards[ref_id]["last_date"] = entry.created_at.isoformat() if entry.created_at else None
    except Exception as _rre:
        logger.warning(f"[DC-REFERRAL] Referral rewards summary failed: {_rre}")

    return {"success": True, "data": {"upline": upline, "downline": downline, "referral_rewards": referral_rewards}}


@router.get("/dashboard/member-network/{partner_code}")
def vgk_member_network_view(
    partner_code: str,
    current_member: OfficialPartner = Depends(get_current_vgk_member),
    db: Session = Depends(get_db)
):
    """
    VGK member-authenticated endpoint: view any member's profile + 3-level downline.
    Used by the VGK dashboard member click-to-view feature.
    """
    target = db.query(OfficialPartner).filter(
        OfficialPartner.partner_code == partner_code.strip().upper(),
        OfficialPartner.category == 'VGK_TEAM'
    ).first()
    if not target:
        raise HTTPException(status_code=404, detail="Member not found")

    upline_info = None
    if target.parent_partner_id:
        parent = db.query(OfficialPartner).filter(OfficialPartner.id == target.parent_partner_id).first()
        if parent:
            upline_info = {"partner_code": parent.partner_code, "partner_name": parent.partner_name}

    def build_down_member(p: OfficialPartner, depth: int) -> dict:
        node = {
            "id": p.id, "partner_code": p.partner_code, "partner_name": p.partner_name,
            "is_active": p.is_active, "is_paid_activation": p.is_paid_activation,
            "is_loyal_coupon": p.is_loyal_coupon,
            "vgk_points_balance": float(p.vgk_points_balance or 0),
            "vgk_activated_at": p.vgk_activated_at.isoformat() if p.vgk_activated_at else None,
            "created_at": p.created_at.isoformat() if p.created_at else None,
            "children": []
        }
        direct_count = db.query(OfficialPartner).filter(
            OfficialPartner.parent_partner_id == p.id,
            OfficialPartner.category == 'VGK_TEAM'
        ).count()
        node["direct_count"] = direct_count
        if depth > 0 and direct_count > 0:
            kids = db.query(OfficialPartner).filter(
                OfficialPartner.parent_partner_id == p.id,
                OfficialPartner.category == 'VGK_TEAM'
            ).order_by(OfficialPartner.id).all()
            node["children"] = [build_down_member(k, depth - 1) for k in kids]
        return node

    downline = build_down_member(target, depth=3)

    return {
        "success": True,
        "data": {
            "id": target.id,
            "partner_code": target.partner_code,
            "partner_name": target.partner_name,
            "is_active": target.is_active,
            "is_paid_activation": target.is_paid_activation,
            "is_loyal_coupon": target.is_loyal_coupon,
            "vgk_points_balance": float(target.vgk_points_balance or 0),
            "vgk_activated_at": target.vgk_activated_at.isoformat() if target.vgk_activated_at else None,
            "created_at": target.created_at.isoformat() if target.created_at else None,
            "upline": upline_info,
            "downline": downline,
        }
    }


@router.get("/dashboard/leads")
def vgk_my_leads(
    page: int = 1,
    segment: str = "source",
    search: Optional[str] = None,
    status: Optional[str] = None,
    priority: Optional[str] = None,
    sort_by: str = "created_at",
    sort_dir: str = "desc",
    followup_filter: Optional[str] = None,
    current_member: OfficialPartner = Depends(get_current_vgk_member),
    db: Session = Depends(get_db)
):
    """
    DC Protocol Apr 2026 / Jun 2026: VGK member leads — 6-segment support system.
    segment=overall       → all leads across any role
    segment=source        → L1 source (associated_partner_id == member.id) — with support info
    segment=guru          → L2 leads (income entry level=2 for this member)
    segment=zguru         → L3 leads (income entry level=3 for this member)
    segment=core          → L4 CORE leads (income entry level=4 for this member) [DC-VGK-L4CORE-001]
    segment=support       → L5 field support (vgk_field_support_id == member.id)
    Legacy segments source_marked/field_assistant still accepted as aliases.
    """
    from sqlalchemy import asc, desc as sqldesc

    page_size = 20
    mid = current_member.id

    # --- Tab counts (unfiltered) ---
    source_count = db.query(CRMLead).filter(CRMLead.associated_partner_id == mid).count()
    support_count = db.query(CRMLead).filter(CRMLead.vgk_field_support_id == mid).count()

    guru_lead_ids = [
        r[0] for r in db.execute(
            sa_text("SELECT DISTINCT source_lead_id FROM vgk_team_income_entries "
                    "WHERE partner_id=:pid AND level=2 AND source_lead_id IS NOT NULL"),
            {"pid": mid}
        ).fetchall()
    ]
    zguru_lead_ids = [
        r[0] for r in db.execute(
            sa_text("SELECT DISTINCT source_lead_id FROM vgk_team_income_entries "
                    "WHERE partner_id=:pid AND level=3 AND source_lead_id IS NOT NULL"),
            {"pid": mid}
        ).fetchall()
    ]
    core_lead_ids = [
        r[0] for r in db.execute(
            sa_text("SELECT DISTINCT source_lead_id FROM vgk_team_income_entries "
                    "WHERE partner_id=:pid AND level=4 AND source_lead_id IS NOT NULL"),
            {"pid": mid}
        ).fetchall()
    ]
    guru_count = len(guru_lead_ids)
    zguru_count = len(zguru_lead_ids)
    core_count  = len(core_lead_ids)

    all_lead_ids = list(set(
        [r.id for r in db.query(CRMLead.id).filter(CRMLead.associated_partner_id == mid).all()] +
        [r.id for r in db.query(CRMLead.id).filter(CRMLead.vgk_field_support_id == mid).all()] +
        guru_lead_ids + zguru_lead_ids + core_lead_ids
    ))
    overall_count = len(all_lead_ids)

    # --- Build base query by segment ---
    norm = segment.lower()
    if norm in ("source", "source_marked"):
        query = db.query(CRMLead).filter(CRMLead.associated_partner_id == mid)
    elif norm in ("support", "field_assistant"):
        query = db.query(CRMLead).filter(CRMLead.vgk_field_support_id == mid)
    elif norm == "core":
        if core_lead_ids:
            query = db.query(CRMLead).filter(CRMLead.id.in_(core_lead_ids))
        else:
            query = db.query(CRMLead).filter(CRMLead.id == -1)
    elif norm == "guru":
        if guru_lead_ids:
            query = db.query(CRMLead).filter(CRMLead.id.in_(guru_lead_ids))
        else:
            query = db.query(CRMLead).filter(CRMLead.id == -1)
    elif norm == "zguru":
        if zguru_lead_ids:
            query = db.query(CRMLead).filter(CRMLead.id.in_(zguru_lead_ids))
        else:
            query = db.query(CRMLead).filter(CRMLead.id == -1)
    else:
        if all_lead_ids:
            query = db.query(CRMLead).filter(CRMLead.id.in_(all_lead_ids))
        else:
            query = db.query(CRMLead).filter(CRMLead.id == -1)

    # Filters
    if status:
        query = query.filter(CRMLead.status == status)
    if priority:
        query = query.filter(CRMLead.priority == priority)
    if search:
        term = "%" + search + "%"
        query = query.filter(or_(
            CRMLead.name.ilike(term),
            CRMLead.phone.ilike(term),
            CRMLead.email.ilike(term),
            CRMLead.city.ilike(term),
        ))
    if followup_filter == 'today':
        from sqlalchemy import func as sqlfunc
        query = query.filter(
            CRMLead.next_followup_date.isnot(None),
            sqlfunc.date(CRMLead.next_followup_date) == sqlfunc.current_date()
        )
    elif followup_filter == 'overdue':
        from sqlalchemy import func as sqlfunc
        query = query.filter(
            CRMLead.next_followup_date.isnot(None),
            CRMLead.next_followup_date < sqlfunc.now(),
            CRMLead.status.not_in(['won', 'lost'])
        )

    sort_col_map = {
        "created_at": CRMLead.created_at,
        "updated_at": CRMLead.updated_at,
        "next_followup_date": CRMLead.next_followup_date,
        "deal_value_total": CRMLead.deal_value_total,
    }
    sort_col = sort_col_map.get(sort_by, CRMLead.created_at)
    order_fn = sqldesc if sort_dir == "desc" else asc
    query = query.order_by(order_fn(sort_col))

    total = query.count()
    leads = query.offset((page - 1) * page_size).limit(page_size).all()

    def _get_support_info(lead):
        """For Source tab: resolve L2/L3 income entries and handler info for this lead."""
        info = {"guru": None, "zguru": None, "handlers": []}

        # L2 entry for this lead
        l2_entry = db.query(VGKTeamIncomeEntry).filter(
            VGKTeamIncomeEntry.source_lead_id == lead.id,
            VGKTeamIncomeEntry.level == 2,
            VGKTeamIncomeEntry.status.in_(["PENDING", "HOLD"])
        ).first()
        if l2_entry:
            l2p = db.query(OfficialPartner).filter(OfficialPartner.id == l2_entry.partner_id).first()
            info["guru"] = {
                "entry_id": l2_entry.id,
                "partner_id": l2_entry.partner_id,
                "partner_name": l2p.partner_name if l2p else "—",
                "partner_code": l2p.partner_code if l2p else "—",
                "support_confirmed": l2_entry.support_confirmed,
                "commission_amount": float(l2_entry.commission_amount or 0),
            }

        # L3 entry for this lead
        l3_entry = db.query(VGKTeamIncomeEntry).filter(
            VGKTeamIncomeEntry.source_lead_id == lead.id,
            VGKTeamIncomeEntry.level == 3,
            VGKTeamIncomeEntry.status.in_(["PENDING", "HOLD"])
        ).first()
        if l3_entry:
            l3p = db.query(OfficialPartner).filter(OfficialPartner.id == l3_entry.partner_id).first()
            info["zguru"] = {
                "entry_id": l3_entry.id,
                "partner_id": l3_entry.partner_id,
                "partner_name": l3p.partner_name if l3p else "—",
                "partner_code": l3p.partner_code if l3p else "—",
                "support_confirmed": l3_entry.support_confirmed,
                "commission_amount": float(l3_entry.commission_amount or 0),
            }

        # Extra handlers: showroom/partner (vendor_id)
        if getattr(lead, 'vendor_id', None):
            vp = db.query(OfficialPartner).filter(OfficialPartner.id == lead.vendor_id).first()
            if vp:
                info["handlers"].append({
                    "type": "partner",
                    "name": vp.partner_name,
                    "code": vp.partner_code,
                    "id": vp.id,
                })

        return info

    def lead_dict(l):
        base = {
            "id": l.id,
            "name": l.name,
            "phone": l.phone or "—",
            "email": l.email or "",
            "city": l.city or "—",
            "state": l.state or "",
            "status": l.status,
            "priority": l.priority,
            "source": l.source or "",
            "looking_for": l.looking_for or "",
            "category_name": getattr(l, 'category_name', None) or "",
            "solar_pipeline_status": getattr(l, 'solar_pipeline_status', None),
            "ev_b2b_stage": getattr(l, 'ev_b2b_stage', None),
            "description": l.description or "",
            "deal_value_total": float(l.deal_value_total or 0),
            "deal_value_received": float(l.deal_value_received or 0),
            "next_followup_date": l.next_followup_date.isoformat() if l.next_followup_date else None,
            "created_at": l.created_at.isoformat() if l.created_at else None,
            "updated_at": l.updated_at.isoformat() if l.updated_at else None,
            "company_id": l.company_id,
        }
        if norm in ("source", "source_marked"):
            base["support_info"] = _get_support_info(l)
        elif norm == "guru":
            e = db.query(VGKTeamIncomeEntry).filter(
                VGKTeamIncomeEntry.source_lead_id == l.id,
                VGKTeamIncomeEntry.partner_id == mid,
                VGKTeamIncomeEntry.level == 2
            ).first()
            base["support_confirmed"] = e.support_confirmed if e else None
            base["income_status"] = e.status if e else None
            base["commission_amount"] = float(e.commission_amount or 0) if e else 0
        elif norm == "zguru":
            e = db.query(VGKTeamIncomeEntry).filter(
                VGKTeamIncomeEntry.source_lead_id == l.id,
                VGKTeamIncomeEntry.partner_id == mid,
                VGKTeamIncomeEntry.level == 3
            ).first()
            base["support_confirmed"] = e.support_confirmed if e else None
            base["income_status"] = e.status if e else None
            base["commission_amount"] = float(e.commission_amount or 0) if e else 0
        return base

    return {
        "success": True,
        "total": total,
        "page": page,
        "segment": segment,
        "tab_counts": {
            "overall": overall_count,
            "source": source_count,
            "guru": guru_count,
            "zguru": zguru_count,
            "core": core_count,
            "support": support_count,
            "source_marked": source_count,
            "field_assistant": support_count,
        },
        "data": [lead_dict(l) for l in leads]
    }


class SupportConfirmRequest(BaseModel):
    level: int = Field(..., description="Income level to confirm: 2 (Guru) or 3 (Z Guru)")
    confirmed: Optional[bool] = Field(None, description="True=supported, False=not supported, None=reset")


@router.post("/dashboard/leads/{lead_id}/set-support")
def vgk_set_support(
    lead_id: int,
    body: SupportConfirmRequest,
    current_member: OfficialPartner = Depends(get_current_vgk_member),
    db: Session = Depends(get_db)
):
    """
    DC Protocol Apr 2026: Source (L1) member marks whether Guru (L2) or Z Guru (L3)
    supported a specific lead. Only the L1 member (associated_partner_id) may call this.
    level: 2=Guru, 3=Z Guru. confirmed: true/false/null.
    """
    from datetime import datetime
    from pytz import timezone
    now = datetime.now(timezone('Asia/Kolkata')).replace(tzinfo=None)

    lead = db.query(CRMLead).filter(CRMLead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    if lead.associated_partner_id != current_member.id:
        raise HTTPException(status_code=403, detail="Only the Source (L1) member of this lead can confirm support")
    if body.level not in (2, 3):
        raise HTTPException(status_code=400, detail="Level must be 2 (Guru) or 3 (Z Guru)")

    entry = db.query(VGKTeamIncomeEntry).filter(
        VGKTeamIncomeEntry.source_lead_id == lead_id,
        VGKTeamIncomeEntry.level == body.level,
        VGKTeamIncomeEntry.status.in_(["PENDING", "HOLD"])
    ).first()
    if not entry:
        raise HTTPException(status_code=404, detail=f"No active L{body.level} income entry for this lead")

    entry.support_confirmed = body.confirmed
    entry.support_confirmed_at = now
    entry.support_confirmed_by_id = current_member.id
    entry.support_confirmed_by_type = "source"
    entry.updated_at = now

    # [DC-VGK-SYNC] Mirror to CRMLead so staff CRM confirmation section stays in sync
    if body.level == 2:
        lead.guru_supported = body.confirmed
    elif body.level == 3:
        lead.z_guru_supported = body.confirmed

    db.commit()

    action = "confirmed" if body.confirmed is True else ("denied" if body.confirmed is False else "reset")
    return {
        "success": True,
        "message": f"L{body.level} support {action} for lead #{lead_id}",
        "entry_id": entry.id,
        "support_confirmed": entry.support_confirmed,
    }


@router.get("/dashboard/my-commissions")
def vgk_my_commissions(
    page: int = 1,
    status: Optional[str] = None,
    current_member: OfficialPartner = Depends(get_current_vgk_member),
    db: Session = Depends(get_db)
):
    """
    DC Protocol (Apr 2026): VGK member's CRM commission entries.
    Returns crm_commission_entries where referrer_type='partner' and referrer_id=str(member.id).
    """
    from app.models.crm_commission import CRMCommissionEntry
    page_size = 20
    ref_id = str(current_member.id)

    query = db.query(CRMCommissionEntry).filter(
        CRMCommissionEntry.referrer_type == 'partner',
        CRMCommissionEntry.referrer_id == ref_id,
    )
    if status:
        query = query.filter(CRMCommissionEntry.status == status)

    total = query.count()
    entries = query.order_by(CRMCommissionEntry.id.desc()).offset((page - 1) * page_size).limit(page_size).all()

    from sqlalchemy import func as _func
    pending_amt = db.query(
        _func.coalesce(_func.sum(CRMCommissionEntry.commission_amount), 0)
    ).filter(
        CRMCommissionEntry.referrer_type == 'partner',
        CRMCommissionEntry.referrer_id == ref_id,
        CRMCommissionEntry.status == 'PENDING',
    ).scalar() or 0

    confirmed_amt = db.query(
        _func.coalesce(_func.sum(CRMCommissionEntry.commission_amount), 0)
    ).filter(
        CRMCommissionEntry.referrer_type == 'partner',
        CRMCommissionEntry.referrer_id == ref_id,
        CRMCommissionEntry.status == 'CONFIRMED',
    ).scalar() or 0

    return {
        "success": True,
        "total": total,
        "page": page,
        "summary": {
            "pending_amount": float(pending_amt),
            "confirmed_amount": float(confirmed_amt),
        },
        "data": [e.to_dict() for e in entries],
    }


@router.get("/dashboard/orders")
def vgk_my_orders(
    page: int = 1,
    current_member: OfficialPartner = Depends(get_current_vgk_member),
    db: Session = Depends(get_db)
):
    """Partner orders linked to this VGK member."""
    page_size = 20
    query = db.query(PartnerOrder).filter(PartnerOrder.partner_id == current_member.id)
    total = query.count()
    orders = query.order_by(PartnerOrder.id.desc()).offset((page - 1) * page_size).limit(page_size).all()

    def order_dict(o):
        return {
            "id": o.id,
            "order_number": o.order_number,
            "pi_number": o.pi_number or "—",
            "status": o.status,
            "order_date": o.order_date.isoformat() if o.order_date else None,
            "grand_total": float(o.grand_total or 0),
            "commitment_date": o.commitment_date.isoformat() if o.commitment_date else None,
            "created_at": o.created_at.isoformat() if o.created_at else None,
        }

    return {
        "success": True,
        "total": total,
        "page": page,
        "data": [order_dict(o) for o in orders]
    }


@router.get("/dashboard/tickets")
def vgk_my_tickets(
    page: int = 1,
    current_member: OfficialPartner = Depends(get_current_vgk_member),
    db: Session = Depends(get_db)
):
    """Service tickets attributed to this VGK member's customers."""
    page_size = 20
    query = db.query(ServiceTicket).filter(ServiceTicket.partner_id == current_member.id)
    total = query.count()
    tickets = query.order_by(ServiceTicket.id.desc()).offset((page - 1) * page_size).limit(page_size).all()

    def ticket_dict(t):
        return {
            "id": t.id,
            "ticket_id": t.ticket_id,
            "customer_name": getattr(t, 'customer_name', None) or "—",
            "customer_phone": getattr(t, 'customer_phone', None) or "—",
            "issue_category": t.issue_category,
            "status": t.status,
            "priority": t.priority,
            "sla_status": t.sla_status,
            "created_date": t.created_date.isoformat() if t.created_date else None,
        }

    return {
        "success": True,
        "total": total,
        "page": page,
        "data": [ticket_dict(t) for t in tickets]
    }


class VGKCreateTicketRequest(BaseModel):
    issue_category: str
    issue_description: str
    priority: str = "Medium"
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None


@router.post("/dashboard/tickets")
def vgk_create_ticket(
    request: VGKCreateTicketRequest,
    current_member: OfficialPartner = Depends(get_current_vgk_member),
    db: Session = Depends(get_db)
):
    """Create a new service ticket as a VGK member (DC Protocol Mar 2026)."""
    import random, string
    suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    ticket_id = f"VGK-TKT-{suffix}"

    if request.priority not in ('Low', 'Medium', 'High', 'Critical'):
        raise HTTPException(status_code=400, detail="Invalid priority value")

    # [DC_DAR_003 / Task #53] Tag company_id from the VGK member's partner row
    # so the ticket counts toward that company in the DAR.
    from app.services.ticket_service import _derive_ticket_company_id
    t = ServiceTicket(
        ticket_id=ticket_id,
        issue_category=request.issue_category,
        issue_description=request.issue_description,
        priority=request.priority,
        status='Open',
        sla_status='Within SLA',
        ticket_type='general',
        source_channel='vgk_portal',
        partner_id=current_member.id,
        created_date=datetime.utcnow(),
        company_id=_derive_ticket_company_id(db, partner_id=current_member.id),
    )
    if request.customer_name:
        t.customer_name = request.customer_name
    if request.customer_phone:
        t.customer_phone = request.customer_phone
    db.add(t)
    db.commit()
    db.refresh(t)
    return {"success": True, "ticket_id": t.ticket_id, "message": "Ticket created successfully"}


# ─── Public Signup ────────────────────────────────────────────────────────────

VGK_DEFAULT_ROOT = 'VGK07102207'


class VGKSignupRequest(BaseModel):
    partner_name: str = Field(..., min_length=2)
    phone: str = Field(..., min_length=10)
    email: Optional[str] = None
    password: str = Field(..., min_length=6)
    referrer_code: Optional[str] = None
    promo_code: Optional[str] = None
    # [DC-NAME-GENDER] Apr 2026 — split name fields (optional; partner_name stays the display name)
    name_title: Optional[str] = None   # Mr. / Ms. / Mrs.
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    gender: Optional[str] = None       # Male / Female / Other
    # [DC-PHONE-OTP-001] Phone verification token (optional — issued by /auth/signup/verify-otp)
    phone_verified_token: Optional[str] = None
    # [DC-VGK-STAFF-REG-001] Staff who referred/registered this member (optional)
    registered_by_emp_code: Optional[str] = None


class PhoneOTPSendRequest(BaseModel):
    phone: str = Field(..., min_length=10)


class PhoneOTPVerifyRequest(BaseModel):
    phone: str = Field(..., min_length=10)
    otp_code: str = Field(..., min_length=6, max_length=6)


@router.post("/auth/signup/send-otp")
def vgk_signup_send_otp(req: PhoneOTPSendRequest, db: Session = Depends(get_db)):
    """[DC-PHONE-OTP-001] Send WhatsApp OTP to phone for VGK self-signup verification."""
    phone = req.phone.strip()
    if len(phone) < 10 or not phone.isdigit():
        raise HTTPException(status_code=400, detail="Please enter a valid 10-digit mobile number.")
    existing = db.query(OfficialPartner).filter(
        OfficialPartner.phone == phone, OfficialPartner.category == 'VGK_TEAM'
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="This phone number is already registered as a VGK Channel Partner.")
    from app.utils.phone_otp import generate_and_send_otp
    return generate_and_send_otp(phone=phone, purpose='vgk_signup', db=db)


@router.post("/auth/signup/verify-otp")
def vgk_signup_verify_otp(req: PhoneOTPVerifyRequest, db: Session = Depends(get_db)):
    """[DC-PHONE-OTP-001] Verify OTP and issue a phone_verified_token for VGK self-signup."""
    from app.utils.phone_otp import verify_otp_and_issue_token
    token = verify_otp_and_issue_token(phone=req.phone.strip(), otp_code=req.otp_code.strip(), purpose='vgk_signup', db=db)
    return {"success": True, "phone_verified_token": token, "message": "Phone verified successfully."}


@router.post("/auth/signup")
def vgk_signup(request: VGKSignupRequest, db: Session = Depends(get_db)):
    """Public self-registration for new VGK members. Account created as inactive — activation via CRM flow."""
    import random as _rnd

    phone = request.phone.strip()

    # [DC-PHONE-OTP-001] Phone verification token is REQUIRED for self-signup
    if not request.phone_verified_token:
        raise HTTPException(
            status_code=400,
            detail="Phone verification required. Please verify your WhatsApp number with OTP before registering."
        )
    from app.utils.phone_otp import validate_and_consume_token
    validate_and_consume_token(phone=phone, token=request.phone_verified_token, purpose='vgk_signup', db=db)

    existing = db.query(OfficialPartner).filter(
        OfficialPartner.phone == phone,
        OfficialPartner.category == 'VGK_TEAM'
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="A VGK member with this phone number is already registered.")

    _referrer_explicitly_provided = bool((request.referrer_code or '').strip())
    referrer_code = (request.referrer_code or '').strip().upper() or VGK_DEFAULT_ROOT
    referrer = db.query(OfficialPartner).filter(
        OfficialPartner.partner_code == referrer_code,
        OfficialPartner.category == 'VGK_TEAM'
    ).first()
    if not referrer and referrer_code != VGK_DEFAULT_ROOT:
        referrer = db.query(OfficialPartner).filter(
            OfficialPartner.partner_code == VGK_DEFAULT_ROOT,
            OfficialPartner.category == 'VGK_TEAM'
        ).first()
    parent_id = referrer.id if referrer else None

    partner_code = None
    for _ in range(50):
        rand4 = _rnd.randint(1000, 9999)
        code = f"VGK0710{rand4}"
        if not db.query(OfficialPartner).filter(OfficialPartner.partner_code == code).first():
            partner_code = code
            break
    if not partner_code:
        raise HTTPException(status_code=500, detail="Could not generate a unique Member ID. Please try again.")

    company_id = 4
    try:
        row = db.execute(sa_text("SELECT MIN(id) FROM associated_companies")).scalar()
        if row:
            company_id = int(row)
    except Exception:
        pass

    password_hash = SecurityManager.get_password_hash(request.password)
    now = get_indian_time()
    # [DC-NAME-GENDER] Build display name from split fields if provided
    _title     = (request.name_title  or '').strip()
    _first     = (request.first_name  or '').strip()
    _last      = (request.last_name   or '').strip()
    _full_name = request.partner_name.strip()
    if _first and _last:
        _full_name = ' '.join(p for p in [_title, _first, _last] if p)
    member = OfficialPartner(
        company_id=company_id,
        partner_code=partner_code,
        partner_name=_full_name,
        phone=phone,
        email=(request.email or '').strip() or None,
        category='VGK_TEAM',
        is_active=False,
        parent_partner_id=parent_id,
        vgk_role='VGK_ASSOCIATE',
        vgk_points_balance=Decimal('0'),
        password_hash=password_hash,
        created_at=now,
        updated_at=now
    )
    # Save split name fields via setattr (columns added by migration)
    if _title: _setattr_safe(member, 'name_title', _title)
    if _first: _setattr_safe(member, 'first_name', _first)
    if _last:  _setattr_safe(member, 'last_name',  _last)
    if request.gender: _setattr_safe(member, 'gender', request.gender.strip())
    # [DC-VGK-STAFF-REG-001] Staff who referred/registered this member
    if request.registered_by_emp_code:
        _setattr_safe(member, 'registered_by_emp_code', request.registered_by_emp_code.strip().upper() or None)
    db.add(member)
    db.commit()
    db.refresh(member)

    try:
        from app.services.vgk_commission import add_vgk_points_entry, process_held_commissions
        add_vgk_points_entry(
            db=db,
            partner_id=member.id,
            points_credit=Decimal('10000'),
            points_debit=Decimal('0'),
            reason_code='WELCOME_BONUS',
            reference_type='signup',
            reference_id=None,
            notes='Welcome bonus — 10,000 VGK Discount Credits on registration',
            created_by=None,
        )
        db.commit()
        process_held_commissions(db, member.id)
    except Exception as _we:
        logger.warning(f"[VGK-SIGNUP] Could not write welcome points ledger entry for {partner_code}: {_we}")

    logger.info(f"[VGK-SIGNUP] New member {partner_code} registered via self-signup, referrer={referrer_code}, 10000 welcome points credited")

    # [DC-REFERRAL] +5,000 additional bonus for using any referral code (explicitly entered)
    referral_bonus_applied = False
    if referrer and _referrer_explicitly_provided:
        try:
            from app.services.vgk_commission import add_vgk_points_entry as _apv
            _apv(
                db=db,
                partner_id=member.id,
                points_credit=Decimal('5000'),
                points_debit=Decimal('0'),
                reason_code='CAMPAIGN_BONUS',
                reference_type='referral_signup',
                reference_id=None,
                notes=f'Referral code bonus — joined via {referrer.partner_code} (+5,000 additional points)',
                created_by=None,
            )
            db.commit()
            referral_bonus_applied = True
            logger.info(f"[DC-REFERRAL] 5,000 referral bonus credited to {partner_code} for using referrer {referrer.partner_code}")
        except Exception as _rb:
            logger.warning(f"[DC-REFERRAL] Referral signup bonus failed for {partner_code}: {_rb}")
            try:
                db.rollback()
            except Exception:
                pass

    # [DC-PROMO-BONUS] If referral code belongs to a promoter with signup_bonus_points configured, credit those too
    if referrer_code and referrer_code != VGK_DEFAULT_ROOT:
        try:
            from sqlalchemy import text as _text
            promo_row = db.execute(_text(
                "SELECT id, COALESCE(signup_bonus_points,0) as sbp FROM promo_influencers "
                "WHERE referral_code = :rc AND status != 'inactive' LIMIT 1"
            ), {"rc": referrer_code}).fetchone()
            if promo_row and int(promo_row[1] or 0) > 0:
                bonus_pts = int(promo_row[1])
                from app.services.vgk_commission import add_vgk_points_entry as _apv2
                _apv2(
                    db=db,
                    partner_id=member.id,
                    points_credit=Decimal(str(bonus_pts)),
                    points_debit=Decimal('0'),
                    reason_code='CAMPAIGN_BONUS',
                    reference_type='promo_referral',
                    reference_id=None,
                    notes=f'Promoter referral bonus — joined via promoter code {referrer_code} (+{bonus_pts:,} points)',
                    created_by=None,
                )
                db.commit()
                logger.info(f"[DC-PROMO-BONUS] {bonus_pts} promoter bonus pts credited to {partner_code} via promoter code {referrer_code}")
                # [DC-REFERRAL-INFL] Also credit the 5,000 referral bonus for using a valid influencer/promoter code
                if not referral_bonus_applied:
                    try:
                        _apv2(
                            db=db,
                            partner_id=member.id,
                            points_credit=Decimal('5000'),
                            points_debit=Decimal('0'),
                            reason_code='CAMPAIGN_BONUS',
                            reference_type='referral_signup',
                            reference_id=None,
                            notes=f'Referral bonus — joined via influencer/promoter code {referrer_code} (+5,000 points)',
                            created_by=None,
                        )
                        db.commit()
                        referral_bonus_applied = True
                        logger.info(f"[DC-REFERRAL-INFL] 5,000 referral bonus credited to {partner_code} via influencer referrer code {referrer_code}")
                    except Exception as _rbi:
                        logger.warning(f"[DC-REFERRAL-INFL] 5k referral bonus failed for {partner_code}: {_rbi}")
                        try:
                            db.rollback()
                        except Exception:
                            pass
        except Exception as _pb:
            logger.warning(f"[DC-PROMO-BONUS] Promoter signup bonus failed for {partner_code}: {_pb}")
            try:
                db.rollback()
            except Exception:
                pass

    # ── Auto-redeem promo code if provided (GENERAL type only at signup) ───────
    promo_redeemed = None
    promo_points = 0
    promo_error = None
    if request.promo_code:
        import datetime as _dt
        import pytz as _pytz
        try:
            promo_val = request.promo_code.strip().upper()
            pc = db.query(VGKPromoCode).filter(VGKPromoCode.code == promo_val).first()
            if not pc:
                # [DC-INFLUENCER] Check if it's an influencer referral code in the promo field
                from sqlalchemy import text as _infl_text
                _infl_row = db.execute(_infl_text(
                    "SELECT id, COALESCE(signup_bonus_points, 0) FROM promo_influencers "
                    "WHERE referral_code = :rc AND status != 'inactive' LIMIT 1"
                ), {"rc": promo_val}).fetchone()
                _infl_bonus = int(_infl_row[1] or 0) if _infl_row else 0
                # Guard: skip if already credited via referrer_code to prevent double-crediting
                _already_via_referrer = (referrer_code == promo_val)
                if _infl_row and _infl_bonus > 0 and not _already_via_referrer:
                    try:
                        from app.services.vgk_commission import add_vgk_points_entry as _apv3
                        _apv3(
                            db=db,
                            partner_id=member.id,
                            points_credit=Decimal(str(_infl_bonus)),
                            points_debit=Decimal('0'),
                            reason_code='CAMPAIGN_BONUS',
                            reference_type='promo_referral',
                            reference_id=None,
                            notes=f'Influencer referral bonus — joined via code {promo_val} (+{_infl_bonus:,} points)',
                            created_by=None,
                        )
                        # Track referral event for the influencer
                        try:
                            db.execute(_infl_text(
                                "INSERT INTO promo_referral_events "
                                "(influencer_id, referral_code, portal, event_type, source_ref_id, source_name, source_phone, created_at) "
                                "VALUES (:iid, :rc, 'vgk', 'registration', :sref, :sname, :sphone, NOW())"
                            ), {"iid": _infl_row[0], "rc": promo_val,
                                "sref": partner_code, "sname": _full_name, "sphone": phone})
                        except Exception:
                            pass
                        db.commit()
                        promo_redeemed = promo_val
                        promo_points = _infl_bonus
                        logger.info(f"[DC-INFL-PROMO] {_infl_bonus} pts credited to {partner_code} via influencer code {promo_val}")
                        # [DC-REFERRAL-INFL] Also credit the 5,000 referral bonus for using a valid influencer code in promo field
                        if not referral_bonus_applied:
                            try:
                                _apv3(
                                    db=db,
                                    partner_id=member.id,
                                    points_credit=Decimal('5000'),
                                    points_debit=Decimal('0'),
                                    reason_code='CAMPAIGN_BONUS',
                                    reference_type='referral_signup',
                                    reference_id=None,
                                    notes=f'Referral bonus — joined via influencer code {promo_val} (+5,000 points)',
                                    created_by=None,
                                )
                                db.commit()
                                referral_bonus_applied = True
                                logger.info(f"[DC-REFERRAL-INFL] 5,000 referral bonus credited to {partner_code} via influencer promo code {promo_val}")
                            except Exception as _rbi2:
                                logger.warning(f"[DC-REFERRAL-INFL] 5k referral bonus (promo path) failed for {partner_code}: {_rbi2}")
                                try:
                                    db.rollback()
                                except Exception:
                                    pass
                    except Exception as _ipe:
                        logger.warning(f"[DC-INFL-PROMO] Influencer promo bonus failed for {partner_code}: {_ipe}")
                elif not _infl_row:
                    promo_error = "Promo code not found."
                # If _already_via_referrer: influencer code already credited via referrer path — silently skip
            elif pc.status != 'ACTIVE':
                promo_error = "Promo code is not active."
            elif pc.promo_type not in ('GENERAL',):
                promo_error = f"This {pc.promo_type.replace('_', ' ').title()} code requires additional verification — redeem it from your dashboard after login."
            else:
                _now = _dt.datetime.now(_pytz.timezone('Asia/Kolkata')).replace(tzinfo=None)
                if pc.valid_from and _now < pc.valid_from:
                    promo_error = "Promo code is not yet valid."
                elif pc.valid_to and _now > pc.valid_to:
                    promo_error = "Promo code has expired."
                elif pc.usage_limit and pc.times_used >= pc.usage_limit:
                    promo_error = "Promo code usage limit reached."
                else:
                    from app.services.vgk_commission import add_vgk_points_entry
                    pts = Decimal(str(pc.points_credit))
                    add_vgk_points_entry(
                        db=db,
                        partner_id=member.id,
                        points_credit=pts,
                        points_debit=Decimal('0'),
                        reason_code='CAMPAIGN_BONUS',
                        reference_type='PROMO_CODE',
                        reference_id=pc.id,
                        notes=f"Promo code redemption at signup: {promo_val} | {pc.label or ''}",
                        created_by=None,
                    )
                    redemption = VGKPromoRedemption(
                        promo_code_id=pc.id,
                        partner_id=member.id,
                        redeemed_at=_dt.datetime.now(_pytz.timezone('Asia/Kolkata')).replace(tzinfo=None),
                        verified_ref=None,
                        points_awarded=pts,
                        notes=f"Auto-redeemed at signup",
                    )
                    db.add(redemption)
                    pc.times_used = (pc.times_used or 0) + 1
                    db.commit()
                    promo_redeemed = promo_val
                    promo_points = int(pts)
                    logger.info(f"[VGK-SIGNUP] Promo {promo_val} auto-redeemed for {partner_code}: +{pts} pts")
        except Exception as _pe:
            logger.warning(f"[VGK-SIGNUP] Promo auto-redeem failed for {partner_code}: {_pe}")
            promo_error = "Could not apply promo code. You can redeem it from your dashboard after login."

    msg = f"Registration successful! Your Member ID is {partner_code}."
    # [DC-PROMO-BONUS] Compute total referral bonus credited for response display
    referral_bonus_total = 5000 if referral_bonus_applied else 0
    if referrer_code and _referrer_explicitly_provided:
        try:
            from sqlalchemy import text as _text2
            _pb_row = db.execute(_text2(
                "SELECT COALESCE(signup_bonus_points,0) FROM promo_influencers WHERE referral_code = :rc AND status != 'inactive' LIMIT 1"
            ), {"rc": referrer_code}).scalar()
            if _pb_row and int(_pb_row) > 0:
                referral_bonus_total += int(_pb_row)
        except Exception:
            pass

    if referral_bonus_applied:
        msg += f" Referral bonus: +{referral_bonus_total:,} additional points credited!"
    if promo_redeemed:
        msg += f" Promo code {promo_redeemed} applied — {promo_points:,} bonus points credited!"
    elif promo_error:
        msg += f" Note: {promo_error}"

    return {
        "success": True,
        "message": msg,
        "partner_code": partner_code,
        "referrer_code": referrer.partner_code if referrer else None,
        "referrer_name": referrer.partner_name if referrer else None,
        "referral_bonus_applied": referral_bonus_applied,
        "referral_bonus_points": referral_bonus_total,
        "promo_redeemed": promo_redeemed,
        "promo_points": promo_points,
        "promo_error": promo_error,
    }


# ─── DC Protocol Mar 2026: VGK Profile Edit + KYC ────────────────────────────

_KYC_DOC_TYPE_MAP = {
    'aadhaar_front': 'aadhar_front',
    'aadhaar_back': 'aadhar_back',
    'aadhar_front': 'aadhar_front',
    'aadhar_back': 'aadhar_back',
    'pan_card': 'pan_card',
    'passport_photo': 'passport_photo',
    # [DC-BANK-DETAILS-001] Apr 2026: Bank passbook/cheque upload
    'bank_passbook': 'bank_passbook',
}
_KYC_REQUIRED = {'aadhar_front', 'aadhar_back', 'pan_card', 'passport_photo'}
_KYC_VALID_INPUT = list(_KYC_DOC_TYPE_MAP.keys())


class VGKProfileUpdateRequest(BaseModel):
    email: Optional[str] = None
    whatsapp_number: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None
    # [DC-VGK-DOB] Date of Birth — YYYY-MM-DD string from date input
    dob_document: Optional[str] = None
    dob_actual: Optional[str] = None
    # [DC-NAME-GENDER] Apr 2026 — split name fields
    name_title: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    gender: Optional[str] = None
    # [DC-BLOOD-GROUP] Apr 2026
    blood_group: Optional[str] = None


@router.put("/auth/profile")
def vgk_update_profile(
    body: VGKProfileUpdateRequest,
    current_member: OfficialPartner = Depends(get_current_vgk_member),
    db: Session = Depends(get_db)
):
    """DC Protocol Mar 2026: VGK member updates own profile.
    Locked: partner_code, partner_name, phone. Editable: email, whatsapp, address fields."""
    if body.email is not None:
        dup = db.query(OfficialPartner).filter(
            OfficialPartner.email == body.email.strip(),
            OfficialPartner.id != current_member.id
        ).first()
        if dup:
            raise HTTPException(status_code=400, detail="Email already in use by another partner.")
        current_member.email = body.email.strip() or None
    if body.whatsapp_number is not None:
        current_member.whatsapp_number = body.whatsapp_number.strip() or None
    if body.address is not None:
        current_member.address = body.address.strip() or None
    if body.city is not None:
        current_member.city = body.city.strip() or None
    if body.state is not None:
        current_member.state = body.state.strip() or None
    if body.pincode is not None:
        current_member.pincode = body.pincode.strip() or None
    # [DC-VGK-DOB] Save date of birth fields (YYYY-MM-DD → Python date)
    if body.dob_document is not None:
        try:
            from datetime import date as _date
            current_member.dob_document = _date.fromisoformat(body.dob_document) if body.dob_document.strip() else None
        except ValueError:
            raise HTTPException(status_code=400, detail="dob_document must be a valid date (YYYY-MM-DD)")
    if body.dob_actual is not None:
        try:
            from datetime import date as _date
            current_member.dob_actual = _date.fromisoformat(body.dob_actual) if body.dob_actual.strip() else None
        except ValueError:
            raise HTTPException(status_code=400, detail="dob_actual must be a valid date (YYYY-MM-DD)")
    # [DC-NAME-GENDER] Save split name fields and rebuild display name
    if body.name_title is not None: _setattr_safe(current_member, 'name_title', body.name_title.strip() or None)
    if body.first_name is not None:  _setattr_safe(current_member, 'first_name', body.first_name.strip() or None)
    if body.last_name is not None:   _setattr_safe(current_member, 'last_name',  body.last_name.strip() or None)
    if body.gender is not None:      _setattr_safe(current_member, 'gender',     body.gender.strip() or None)
    # [DC-BLOOD-GROUP]
    if body.blood_group is not None:
        _allowed_bg = {'A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-', ''}
        if body.blood_group.strip() not in _allowed_bg:
            raise HTTPException(status_code=400, detail="Invalid blood group. Must be one of: A+, A-, B+, B-, AB+, AB-, O+, O-")
        _setattr_safe(current_member, 'blood_group', body.blood_group.strip() or None)
    # Rebuild partner_name from split fields if both first+last are now present
    _t  = getattr(current_member, 'name_title', None) or ''
    _fn = getattr(current_member, 'first_name', None) or ''
    _ln = getattr(current_member, 'last_name',  None) or ''
    if _fn and _ln:
        current_member.partner_name = ' '.join(p for p in [_t, _fn, _ln] if p)
    current_member.updated_at = get_indian_time()
    db.commit()
    db.refresh(current_member)
    return {"success": True, "message": "Profile updated successfully"}


@router.get("/dashboard/payment-history")
def vgk_payment_history(
    current_member: OfficialPartner = Depends(get_current_vgk_member),
    db: Session = Depends(get_db)
):
    from sqlalchemy import or_
    entries = db.query(VGKTeamIncomeEntry).filter(
        VGKTeamIncomeEntry.partner_id == current_member.id,
        VGKTeamIncomeEntry.level == 0,
        VGKTeamIncomeEntry.status != 'CANCELLED',
        or_(VGKTeamIncomeEntry.notes == None, ~VGKTeamIncomeEntry.notes.like('DEBIT:%'))
    ).order_by(VGKTeamIncomeEntry.created_at.desc()).all()

    payments = []
    for e in entries:
        payments.append({
            "id": e.id,
            "date": e.created_at.isoformat() if e.created_at else None,
            "amount": float(e.revenue_amount or 0),
            "points_credited": float(e.commission_amount or 0),
            "reference": e.entry_number,
            "status": e.status,
            "notes": e.notes,
            "confirmed_at": e.confirmed_at.isoformat() if e.confirmed_at else None
        })

    return {
        "success": True,
        "data": payments
    }


@router.get("/dashboard/ledger")
def vgk_ledger(
    page: int = 1,
    current_member: OfficialPartner = Depends(get_current_vgk_member),
    db: Session = Depends(get_db)
):
    """Commission income ledger — financial entries only (excludes points)."""
    page_size = 50
    query = db.query(VGKTeamIncomeEntry).filter(
        VGKTeamIncomeEntry.partner_id == current_member.id,
        VGKTeamIncomeEntry.status == 'CONFIRMED',
        VGKTeamIncomeEntry.level >= 1,
    ).order_by(VGKTeamIncomeEntry.created_at.asc())

    total = query.count()
    all_entries = query.all()

    level_desc = {1: 'L1 Commission', 2: 'L2 Commission', 3: 'L3 Commission',
                  4: 'L4 Core Commission', 5: 'L5 Support Commission'}

    ledger_rows = []
    running_balance = Decimal('0')
    for e in all_entries:
        is_debit = (e.notes or '').startswith('DEBIT:')
        amount = (e.commission_amount or Decimal('0')) + (e.bonus_amount or Decimal('0'))

        if is_debit:
            running_balance -= abs(amount)
            ledger_rows.append({
                "id": e.id,
                "date": e.created_at.isoformat() if e.created_at else None,
                "type": "DEBIT",
                "description": (e.notes or '').replace('DEBIT: ', ''),
                "amount": float(abs(amount)),
                "running_balance": float(running_balance),
                "entry_number": e.entry_number,
                "level": e.level,
                "status": e.status
            })
        else:
            running_balance += amount
            desc = level_desc.get(e.level, f'L{e.level} Commission')
            if e.source_lead_id:
                desc += f' on Lead #{e.source_lead_id}'
            ledger_rows.append({
                "id": e.id,
                "date": e.created_at.isoformat() if e.created_at else None,
                "type": "CREDIT",
                "description": desc,
                "amount": float(amount),
                "running_balance": float(running_balance),
                "entry_number": e.entry_number,
                "level": e.level,
                "status": e.status,
                "support_confirmed": e.support_confirmed if e.level in (2, 3) else None,
                "support_confirmed_at": e.support_confirmed_at.isoformat() if (e.level in (2, 3) and e.support_confirmed_at) else None,
                "source_lead_id": e.source_lead_id,
            })

    start = (page - 1) * page_size
    end = start + page_size
    paginated = list(reversed(ledger_rows))[start:end]

    return {
        "success": True,
        "total": total,
        "page": page,
        "data": paginated
    }


@router.get("/dashboard/points")
def vgk_points_ledger(
    page: int = 1,
    current_member: OfficialPartner = Depends(get_current_vgk_member),
    db: Session = Depends(get_db)
):
    """
    VGK Discount Credits ledger.
    Shows all credit and debit movements in the partner's points account.
    Points are promotional discount credits — not financial income.
    Cannot be transferred, withdrawn as cash, or used for activation.
    """
    page_size = 50

    all_entries = (
        db.query(VGKPointsLedger)
        .filter(VGKPointsLedger.partner_id == current_member.id)
        .order_by(VGKPointsLedger.created_at.asc())
        .all()
    )

    # INCOME_EARNED credit entries are internal accounting corrections (retro-fix refunds).
    # They are not real earnings — filter them from the member-visible ledger and totals.
    visible_entries = [
        e for e in all_entries
        if not (e.reason_code == 'INCOME_EARNED' and (e.points_credit or 0) > 0)
    ]

    total_credits  = sum(float(e.points_credit or 0) for e in visible_entries)
    total_debits   = sum(float(e.points_debit  or 0) for e in visible_entries)
    # DC-VGK-PTS-RULE-001: only INCOME_EARNED debits (at PAID stage) count as "utilised for income".
    # MANUAL_ADJUSTMENT debits are admin cap-enforcement corrections, not income deductions.
    income_debits  = sum(
        float(e.points_debit or 0) for e in visible_entries
        if e.reason_code == 'INCOME_EARNED' and (e.points_debit or 0) > 0
    )
    available_balance = float(current_member.vgk_points_balance or 0)
    # Pending Points: sum of (net_payout × 0.9) for income entries awaiting payment.
    # Shown when balance is 0 to show the member what points will flow once income is paid.
    _pend_row = db.execute(sa_text(
        "SELECT COALESCE(SUM(net_payout * 0.9),0) AS pts "
        "FROM vgk_cash_income_entries "
        "WHERE partner_id=:pid AND status IN ('PENDING','RELEASED')"
    ), {"pid": current_member.id}).fetchone()
    pending_points = float(_pend_row.pts if _pend_row else 0)

    reason_labels = {
        'WELCOME_BONUS':         'Registration Bonus',
        'ACTIVATION_BONUS':      'Activation Bonus',
        'LOYAL_BONUS':           'Loyal Coupon Bonus',
        'BONANZA_REWARD':        'Bonanza Reward',
        'CAMPAIGN_BONUS':        'Campaign Reward',
        'INCOME_EARNED':         'Points Utilised for Income',
        'BONANZA_CASH_CREDIT':   'Bonanza Cash Credited',
        'PRODUCT_DISCOUNT':      'Discount Applied — Marketplace',
        'SERVICE_DISCOUNT':      'Discount Applied — Service',
        'INVOICE_DISCOUNT':      'Discount Applied — Invoice',
        'COMMISSION_ADJUSTMENT': 'Commission Adjustment',
        'MANUAL_ADJUSTMENT':     'Manual Adjustment',
        'MIGRATION_BALANCE':     'Opening Balance',
        'COMPANY_ROYALTY':       'Company Side Royalty Points',
    }

    ref_labels = {
        'signup':        'Registration',
        'activation':    'Activation Payment',
        'loyal_coupon':  'Loyal Coupon Grant',
        'marketplace':   'Marketplace Purchase',
        'service':       'Service Ticket',
        'invoice':       'Sales Invoice',
        'migration':     'Opening Balance',
    }

    # Pre-fetch promo code labels for PROMO_CODE entries (avoids N+1 in loop)
    _promo_code_ids = list({e.reference_id for e in visible_entries
                            if e.reference_type == 'PROMO_CODE' and e.reference_id})
    _promo_code_map = {}
    if _promo_code_ids:
        _pc_rows = db.query(VGKPromoCode.id, VGKPromoCode.code).filter(
            VGKPromoCode.id.in_(_promo_code_ids)
        ).all()
        _promo_code_map = {r.id: r.code for r in _pc_rows}

    # DC_VGK_POINTS_VIEW_001: Pre-fetch VCI entries for INCOME_EARNED debit rows so the
    # View modal can show the full income breakdown (advance+slab, deductions, UTR, paid date).
    _vci_ids = list({
        e.reference_id for e in visible_entries
        if e.reason_code == 'INCOME_EARNED'
        and (e.points_debit or 0) > 0
        and e.reference_type == 'VGK_CASH_INCOME'
        and e.reference_id
    })
    _vci_map: dict = {}
    if _vci_ids:
        try:
            from app.models.vgk_cash_income import VGKCashIncomeEntry as _VCIE
            _vci_rows = db.query(_VCIE).filter(_VCIE.id.in_(_vci_ids)).all()
            for _vr in _vci_rows:
                _vci_map[_vr.id] = {
                    'entry_number':      _vr.entry_number,
                    'commission_amount': float(_vr.commission_amount or 0),
                    'admin_charges':     float(_vr.admin_charges or 0),
                    'tds_amount':        float(_vr.tds_amount or 0),
                    'net_payout':        float(_vr.net_payout or 0),
                    'payment_mode':      _vr.payment_mode,
                    'payment_utr':       _vr.payment_utr,
                    'paid_at':           _vr.paid_at.isoformat() if _vr.paid_at else None,
                    'source_lead_id':    _vr.source_lead_id,
                    'kind':              _vr.kind,
                }
        except Exception as _vci_e:
            pass  # non-fatal — View modal degrades gracefully

    utilization_by_type = {}
    rows = []
    _running_balance = 0.0          # computed oldest→newest from visible entries only
    for e in visible_entries:
        is_debit = (e.points_debit or Decimal('0')) > 0
        _cr = float(e.points_credit or 0)
        _dr = float(e.points_debit  or 0)
        _running_balance += _cr - _dr
        ref_type = e.reference_type or 'other'
        if ref_type == 'PROMO_CODE' and e.reference_id and e.reference_id in _promo_code_map:
            used_at_label = _promo_code_map[e.reference_id]
        elif ref_type == 'PROMO_CODE' and not e.reference_id and e.notes:
            # Direct ID entry — extract the ID from notes: "Direct ID: MNR123 | ..."
            _m = _re.search(r'Direct ID:\s*(\S+)', e.notes)
            used_at_label = _m.group(1).rstrip('|').strip() if _m else 'Promo Code'
        elif ref_type == 'VGK_CASH_INCOME' and e.reason_code == 'INCOME_EARNED' and is_debit:
            # DC_VGK_POINTS_VIEW_001: Solar advance income — show "Vgk Solar Adv" label
            used_at_label = 'Vgk Solar Adv'
        else:
            used_at_label = ref_labels.get(ref_type, ref_type.replace('_', ' ').title()) if e.reference_type else None

        # Build income_entry sub-object for View modal (only for PAID advance debit rows)
        _income_entry = None
        if (e.reason_code == 'INCOME_EARNED' and is_debit
                and e.reference_type == 'VGK_CASH_INCOME' and e.reference_id
                and e.reference_id in _vci_map):
            _income_entry = _vci_map[e.reference_id]

        rows.append({
            "id": e.id,
            "date": e.created_at.isoformat() if e.created_at else None,
            "type": "DEBIT" if is_debit else "CREDIT",
            "description": reason_labels.get(e.reason_code, (e.reason_code or '').replace('_', ' ').title()),
            "reason_code": e.reason_code,
            "points_credit": _cr,
            "points_debit": _dr,
            "balance_after": round(_running_balance, 2),   # live-computed, not stored value
            "running_balance": round(_running_balance, 2),
            "notes": e.notes,
            "reference_type": e.reference_type,
            "reference_id": e.reference_id,
            "used_at": used_at_label,
            "income_entry": _income_entry,
        })
        # DC-VGK-PTS-RULE-001: only income/discount deductions go in utilization breakdown.
        # MANUAL_ADJUSTMENT (admin cap corrections) must not appear as "points used".
        if is_debit and float(e.points_debit or 0) > 0 and e.reason_code != 'MANUAL_ADJUSTMENT':
            key = used_at_label or 'Other'
            utilization_by_type[key] = utilization_by_type.get(key, 0) + float(e.points_debit or 0)

    start = (page - 1) * page_size
    end = start + page_size
    paginated = list(reversed(rows))[start:end]

    held_entries = db.query(VGKTeamIncomeEntry).filter(
        VGKTeamIncomeEntry.partner_id == current_member.id,
        VGKTeamIncomeEntry.status == 'HOLD',
    ).all()
    held_count          = len(held_entries)
    held_total_amount   = sum(float(e.commission_amount or 0) + float(e.bonus_amount or 0) for e in held_entries)
    held_points_needed  = sum(float(e.required_points_debit or 0) for e in held_entries)

    return {
        "success": True,
        "label": "VGK Points Balance",
        "point_value": "1 Point = ₹1",
        "policy": (
            "1 VGK Point = ₹1 discount. Points are debited automatically whenever your "
            "VGK Member ID is applied as a discount code — at marketplace checkout, "
            "service payments, invoices, or any other eligible transaction. "
            "Points are for your account only and cannot be transferred to others."
        ),
        "summary": {
            "total_credits": total_credits,
            "total_debits": total_debits,
            "income_debits": income_debits,
            "available_balance": available_balance,
            "pending_points": pending_points,
        },
        "utilization_breakdown": [
            {"label": k, "points_used": v}
            for k, v in sorted(utilization_by_type.items(), key=lambda x: -x[1])
        ],
        "held_incentives": {
            "count": held_count,
            "total_amount": held_total_amount,
            "points_needed_to_release": held_points_needed,
        },
        "total": len(rows),
        "total_entries": len(rows),
        "page": page,
        "data": paginated,
        "entries": paginated,
    }


@router.get("/dashboard/summary")
def vgk_dashboard_summary(
    current_member: OfficialPartner = Depends(get_current_vgk_member),
    db: Session = Depends(get_db)
):
    """Aggregated dashboard summary: member info, earnings, team, leads, orders, tickets, upline, recent activity.
    DC Protocol: Optimised — SQL aggregates replace Python-side full-table scans; N+1 L2 resolved with subquery."""
    from pytz import timezone
    from sqlalchemy import case as sa_case
    now = datetime.now(timezone('Asia/Kolkata'))
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    pid = current_member.id

    # [DC-PERF-001] Combined CTE: 5 separate aggregate queries → 1 round-trip to Neon.
    # Saves ~4 × 20-50ms Neon round-trips per dashboard load.
    _agg = db.execute(sa_text("""
        WITH earn AS (
            SELECT
                COALESCE(SUM(CASE WHEN status='CONFIRMED' THEN commission_amount+bonus_amount ELSE 0 END),0) AS confirmed,
                COALESCE(SUM(CASE WHEN status='PENDING'   THEN commission_amount+bonus_amount ELSE 0 END),0) AS pending,
                COALESCE(SUM(CASE WHEN status<>'CANCELLED' AND created_at>=:month_start
                                  THEN commission_amount+bonus_amount ELSE 0 END),0) AS this_month
            FROM vgk_team_income_entries WHERE partner_id=:pid AND level>=1
        ),
        pts AS (
            SELECT COALESCE(SUM(points_credit),0) AS credits,
                   COALESCE(SUM(points_debit),0)  AS debits,
                   COALESCE(SUM(CASE WHEN reason_code='INCOME_EARNED' THEN points_debit ELSE 0 END),0) AS income_debits
            FROM vgk_points_ledger WHERE partner_id=:pid
        ),
        pend_pts AS (
            SELECT COALESCE(SUM(net_payout * 0.9),0) AS pts
            FROM vgk_cash_income_entries
            WHERE partner_id=:pid AND status IN ('PENDING','RELEASED')
        ),
        leads AS (
            SELECT COUNT(*)                               AS total,
                   COUNT(CASE WHEN status='NEW' THEN 1 END) AS new_c,
                   COUNT(CASE WHEN status='WON' THEN 1 END) AS won
            FROM crm_leads WHERE associated_partner_id=:pid
        ),
        orders AS (
            SELECT COUNT(*) AS total,
                   COUNT(CASE WHEN status IN ('PENDING','PROCESSING') THEN 1 END) AS pend
            FROM partner_orders WHERE partner_id=:pid
        ),
        tickets AS (
            SELECT COUNT(*) AS total,
                   COUNT(CASE WHEN status IN ('Open','In Progress') THEN 1 END) AS open_c
            FROM service_ticket WHERE partner_id=:pid
        ),
        team AS (
            SELECT
                COUNT(*) FILTER (WHERE parent_partner_id=:pid) AS l1_count,
                COUNT(*) FILTER (WHERE parent_partner_id IN (
                    SELECT id FROM official_partners
                    WHERE parent_partner_id=:pid AND category='VGK_TEAM'
                )) AS l2_count
            FROM official_partners WHERE category='VGK_TEAM'
              AND (parent_partner_id=:pid OR parent_partner_id IN (
                    SELECT id FROM official_partners
                    WHERE parent_partner_id=:pid AND category='VGK_TEAM'
              ))
        )
        SELECT earn.confirmed, earn.pending, earn.this_month,
               pts.credits, pts.debits, pts.income_debits,
               pend_pts.pts AS pending_pts,
               leads.total  AS leads_total,  leads.new_c AS leads_new,  leads.won AS leads_won,
               orders.total AS orders_total, orders.pend AS orders_pend,
               tickets.total AS tickets_total, tickets.open_c AS tickets_open,
               team.l1_count, team.l2_count
        FROM earn, pts, pend_pts, leads, orders, tickets, team
    """), {"pid": pid, "month_start": month_start.replace(tzinfo=None)}).fetchone()

    total_confirmed   = float(_agg.confirmed)
    total_pending     = float(_agg.pending)
    this_month        = float(_agg.this_month)
    pts_total_credits  = float(_agg.credits)
    pts_total_debits   = float(_agg.debits)
    pts_income_debits  = float(_agg.income_debits)
    pts_available      = float(current_member.vgk_points_balance or 0)
    pts_pending        = float(_agg.pending_pts or 0)
    l1_direct  = int(_agg.l1_count or 0)
    l2_count   = int(_agg.l2_count or 0)
    total_team = l1_direct + l2_count
    leads_total = int(_agg.leads_total); leads_new = int(_agg.leads_new); leads_converted = int(_agg.leads_won)
    orders_total = int(_agg.orders_total); orders_pend = int(_agg.orders_pend)
    tickets_total = int(_agg.tickets_total); tickets_open = int(_agg.tickets_open)

    # ── 5. Upline ──────────────────────────────────────────────────────────────
    upline_info = None
    if current_member.parent_partner_id:
        parent = db.query(OfficialPartner).filter(
            OfficialPartner.id == current_member.parent_partner_id
        ).first()
        if parent:
            upline_info = {"partner_code": parent.partner_code,
                           "partner_name": parent.partner_name,
                           "is_active": parent.is_active}

    # ── 6. Recent commission entries (last 5 confirmed) — LIMIT in DB ─────────
    level_desc = {1: 'L1 Commission', 2: 'L2 Commission', 3: 'L3 Commission',
                  4: 'L4 Core Commission', 5: 'L5 Support Commission'}
    recent_entries = db.query(VGKTeamIncomeEntry).filter(
        VGKTeamIncomeEntry.partner_id == pid,
        VGKTeamIncomeEntry.level >= 1,
        VGKTeamIncomeEntry.status == 'CONFIRMED',
    ).order_by(VGKTeamIncomeEntry.id.desc()).limit(5).all()
    recent_ledger = []
    for e in recent_entries:
        is_debit = (e.notes or '').startswith('DEBIT:')
        amount = float(e.commission_amount or 0) + float(e.bonus_amount or 0)
        desc = level_desc.get(e.level, f'L{e.level} Commission')
        if e.source_lead_id:
            desc += f' on Lead #{e.source_lead_id}'
        if is_debit:
            desc = (e.notes or '').replace('DEBIT: ', '')
        recent_ledger.append({
            "description": desc, "amount": amount,
            "type": "DEBIT" if is_debit else "CREDIT",
            "date": e.created_at.isoformat() if e.created_at else None,
            "entry_number": e.entry_number,
        })

    # ── 7. Recent points movements (last 5) — LIMIT in DB ────────────────────
    reason_labels = {
        'WELCOME_BONUS': 'Welcome Bonus', 'ACTIVATION_BONUS': 'Activation Bonus',
        'BONANZA_REWARD': 'Bonanza Reward', 'PRODUCT_DISCOUNT': 'Product Discount Used',
        'CAMPAIGN_BONUS': 'Campaign Reward', 'COMMISSION_ADJUSTMENT': 'Commission Adjustment',
        'MANUAL_ADJUSTMENT': 'Manual Adjustment', 'MIGRATION_BALANCE': 'Opening Balance',
    }
    recent_pts_rows = db.query(VGKPointsLedger).filter(
        VGKPointsLedger.partner_id == pid
    ).order_by(VGKPointsLedger.id.desc()).limit(5).all()
    recent_pts_list = []
    for e in recent_pts_rows:
        is_debit = (e.points_debit or Decimal('0')) > 0
        recent_pts_list.append({
            "description": reason_labels.get(e.reason_code, e.reason_code or ''),
            "points_credit": float(e.points_credit or 0),
            "points_debit":  float(e.points_debit  or 0),
            "balance_after": float(e.balance_after  or 0),
            "type": "DEBIT" if is_debit else "CREDIT",
            "date": e.created_at.isoformat() if e.created_at else None,
        })

    return {
        "success": True,
        "member": {
            "partner_code": current_member.partner_code,
            "partner_name": current_member.partner_name,
            "phone": current_member.phone,
            "email": current_member.email,
            "is_active": current_member.is_active,
            "vgk_role": current_member.vgk_role or 'VGK_ASSOCIATE',
            "vgk_activated_at": current_member.vgk_activated_at.isoformat() if current_member.vgk_activated_at else None,
            "is_loyal_coupon": getattr(current_member, 'is_loyal_coupon', False),
            "created_at": current_member.created_at.isoformat() if current_member.created_at else None,
        },
        "earnings": {
            "total_confirmed": total_confirmed,
            "total_pending":   total_pending,
            "this_month":      this_month,
        },
        "discount_credits": {
            "label": "VGK Discount Credits",
            "available_balance": pts_available,
            "total_credits": pts_total_credits,
            "total_debits":  pts_total_debits,
            "income_debits": pts_income_debits,
            "pending_points": pts_pending,
            "recent": recent_pts_list,
        },
        "team":    {"total": total_team, "l1_direct": l1_direct, "l2": l2_count},
        "leads":   {"total": leads_total,   "new": leads_new,  "converted": leads_converted},
        "orders":  {"total": orders_total,  "pending": orders_pend},
        "tickets": {"total": tickets_total, "open": tickets_open},
        "upline":  upline_info,
        "recent_ledger": recent_ledger,
    }


class VGKLeadSubmitRequest(BaseModel):
    customer_name: str = Field(..., min_length=2, max_length=200)
    customer_phone: str = Field(..., min_length=10, max_length=15)
    product_type: str = Field(..., description="SOLAR, EV, INSURANCE, TRAINING, or REAL_ESTATE")
    notes: Optional[str] = Field(None, max_length=500)
    handler_staff_id: Optional[int] = Field(None, description="Staff employee ID to assign as handler")
    create_vgk_account: Optional[bool] = Field(False, description="Auto-create VGK member account for this lead")


@router.post("/dashboard/leads/submit")
def vgk_submit_lead(
    req: VGKLeadSubmitRequest,
    current_member: OfficialPartner = Depends(get_current_vgk_member),
    db: Session = Depends(get_db)
):
    """[DC-VGK-LEAD-SUBMIT] VGK member submits a customer lead. All types auto-created as fresh unassigned CRM leads with source VGK4U."""
    valid_products = {'SOLAR', 'EV', 'INSURANCE', 'TRAINING', 'REAL_ESTATE'}
    pt = (req.product_type or '').upper().strip()
    if pt not in valid_products:
        raise HTTPException(status_code=400, detail="product_type must be SOLAR, EV, INSURANCE, TRAINING, or REAL_ESTATE")

    # Human-readable label for description
    pt_labels = {
        'SOLAR': 'Solar Energy',
        'EV': 'Electric Vehicle (EV)',
        'INSURANCE': 'Insurance',
        'TRAINING': 'Training / ETC',
        'REAL_ESTATE': 'Real Estate',
    }
    pt_label = pt_labels.get(pt, pt)

    parts = [f"Product Interest: {pt_label}"]
    if req.notes:
        parts.append(req.notes)
    parts.append(f"Submitted via VGK4U member portal by {current_member.partner_code}")
    full_desc = " | ".join(parts)

    # [DC-STAFF-ASSIGN] Validate staff if provided
    handler_staff = None
    staff_not_found_warning = None
    if req.handler_staff_id:
        from app.models.staff import StaffEmployee
        handler_staff = db.query(StaffEmployee).filter(
            StaffEmployee.id == req.handler_staff_id,
            StaffEmployee.status == 'active'
        ).first()
        if handler_staff:
            parts.append(f"Assigned to: {handler_staff.full_name} (Staff)")
        else:
            staff_not_found_warning = f"Staff ID {req.handler_staff_id} not found or inactive — lead created without staff assignment."

    lead = CRMLead(
        company_id=current_member.company_id or 4,
        name=req.customer_name.strip(),
        phone=req.customer_phone.strip(),
        status='new',
        source='VGK4U',
        associated_partner_id=current_member.id,
        source_ref_type='vgk',
        source_ref_id=str(current_member.id),
        source_ref_name=current_member.partner_name,
        description=" | ".join(parts),
        field_staff_id=handler_staff.id if handler_staff else None,
    )
    db.add(lead)
    db.commit()
    db.refresh(lead)
    logger.info("[DC-VGK-LEAD-SUBMIT] Lead #%s created by %s product=%s staff=%s", lead.id, current_member.partner_code, pt, handler_staff.id if handler_staff else None)

    # [DC-VGK-ACCOUNT] Auto-create VGK account for lead if requested
    vgk_account_data = None
    if req.create_vgk_account:
        import random as _rnd2
        import string as _str2
        phone_clean = req.customer_phone.strip().replace(' ', '').replace('-', '')
        existing_vgk = db.query(OfficialPartner).filter(
            OfficialPartner.phone == phone_clean,
            OfficialPartner.category == 'VGK_TEAM'
        ).first()
        if existing_vgk:
            vgk_account_data = {"created": False, "reason": "already_exists", "partner_code": existing_vgk.partner_code}
        else:
            # Generate unique partner code
            new_partner_code = None
            for _ in range(50):
                rand4 = _rnd2.randint(1000, 9999)
                _code = f"VGK0710{rand4}"
                if not db.query(OfficialPartner).filter(OfficialPartner.partner_code == _code).first():
                    new_partner_code = _code
                    break
            if new_partner_code:
                # Auto-generate password
                auto_pwd = ''.join(_rnd2.choices(_str2.ascii_uppercase + _str2.digits, k=8))
                pwd_hash = SecurityManager.get_password_hash(auto_pwd)
                now2 = get_indian_time()
                company_id2 = current_member.company_id or 4
                new_vgk = OfficialPartner(
                    company_id=company_id2,
                    partner_code=new_partner_code,
                    partner_name=req.customer_name.strip(),
                    phone=phone_clean,
                    category='VGK_TEAM',
                    is_active=False,
                    parent_partner_id=current_member.id,
                    vgk_role='VGK_ASSOCIATE',
                    vgk_points_balance=Decimal('0'),
                    password_hash=pwd_hash,
                    created_at=now2,
                    updated_at=now2,
                )
                db.add(new_vgk)
                db.commit()
                db.refresh(new_vgk)
                # Credit 10,000 welcome + 5,000 lead-origin bonus
                try:
                    from app.services.vgk_commission import add_vgk_points_entry as _apv2
                    _apv2(db=db, partner_id=new_vgk.id, points_credit=Decimal('10000'),
                          points_debit=Decimal('0'), reason_code='WELCOME_BONUS',
                          reference_type='signup', reference_id=None,
                          notes='Welcome bonus — 10,000 VGK Discount Credits on registration', created_by=None)
                    _apv2(db=db, partner_id=new_vgk.id, points_credit=Decimal('5000'),
                          points_debit=Decimal('0'), reason_code='CAMPAIGN_BONUS',
                          reference_type='lead_origin', reference_id=lead.id,
                          notes=f'Lead origin bonus — account created via VGK lead by {current_member.partner_code}', created_by=None)
                    db.commit()
                    logger.info("[DC-VGK-ACCOUNT] New VGK account %s created from lead #%s by %s, 15000 pts credited", new_partner_code, lead.id, current_member.partner_code)
                except Exception as _pe2:
                    logger.warning(f"[DC-VGK-ACCOUNT] Points credit failed for {new_partner_code}: {_pe2}")
                vgk_account_data = {
                    "created": True,
                    "partner_code": new_partner_code,
                    "partner_name": req.customer_name.strip(),
                    "phone": phone_clean,
                    "auto_password": auto_pwd,
                    "login_url": "https://vgk4u.com/vgk/login",
                }
            else:
                vgk_account_data = {"created": False, "reason": "code_generation_failed"}

    resp = {"success": True, "lead_id": lead.id, "message": "Lead submitted successfully", "vgk_account": vgk_account_data}
    if staff_not_found_warning:
        resp["staff_warning"] = staff_not_found_warning
    return resp


class VGKPointsRedeemRequest(BaseModel):
    points_to_use: float = Field(..., gt=0, description="Points to redeem as product discount")
    order_id: Optional[int] = Field(None, description="Partner order reference ID")
    notes: Optional[str] = None


@router.post("/member/redeem-points")
def vgk_redeem_points(
    body: VGKPointsRedeemRequest,
    current_member: OfficialPartner = Depends(get_current_vgk_member),
    db: Session = Depends(get_db)
):
    """
    Redeem VGK Discount Credits against a vendor product purchase.
    Rules:
      - Points can only be used by the partner who owns them.
      - Points cannot be transferred to other partners or customers.
      - Points cannot be withdrawn as cash.
      - Points cannot be used for partner activation.
      - Redemption cannot exceed the partner's available balance.
    """
    from app.services.vgk_commission import add_vgk_points_entry

    debit_amount = Decimal(str(body.points_to_use)).quantize(Decimal('0.01'))
    current_balance = current_member.vgk_points_balance or Decimal('0')

    if debit_amount > current_balance:
        raise HTTPException(
            status_code=400,
            detail=f"Insufficient VGK Discount Credits. Available: {float(current_balance)}, Requested: {float(debit_amount)}"
        )

    try:
        entry = add_vgk_points_entry(
            db=db,
            partner_id=current_member.id,
            points_credit=Decimal('0'),
            points_debit=debit_amount,
            reason_code='PRODUCT_DISCOUNT',
            reference_type='partner_order' if body.order_id else None,
            reference_id=body.order_id,
            notes=body.notes or f"Product discount redemption of {float(debit_amount)} VGK Credits",
            created_by=None,
        )
        db.commit()
        db.refresh(current_member)
        return {
            "success": True,
            "message": f"{float(debit_amount)} VGK Discount Credits redeemed successfully.",
            "points_used": float(debit_amount),
            "new_balance": float(current_member.vgk_points_balance or 0),
            "ledger_entry_id": entry.id,
        }
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        db.rollback()
        logger.error(f"[VGK-REDEEM] Failed for partner {current_member.partner_code}: {e}")
        raise HTTPException(status_code=500, detail="Redemption failed. Please try again.")


@router.get("/membership-receipt")
async def vgk_membership_receipt(
    current_member: OfficialPartner = Depends(get_current_vgk_member),
    db: Session = Depends(get_db)
):
    """Download VGK membership activation receipt PDF (DC Protocol Mar 2026)."""
    from fastapi.responses import StreamingResponse
    from app.utils.receipt_generator import generate_vgk_receipt

    activation_date = current_member.vgk_activated_at or current_member.created_at
    if activation_date:
        act_str = activation_date.strftime('%d %B %Y')
    else:
        act_str = 'N/A'

    join_date = current_member.created_at
    join_str = join_date.strftime('%d %B %Y') if join_date else 'N/A'

    receipt_number = f"VGK-RCP-{current_member.partner_code[-6:]}"
    role_labels = {'VGK_ASSOCIATE': 'VGK Associate', 'VGK_MENTOR': 'VGK Mentor', 'VGK_LEADER': 'VGK Leader'}
    role_display = role_labels.get(current_member.vgk_role or 'VGK_ASSOCIATE', current_member.vgk_role or 'VGK Associate')

    from pytz import timezone as _tz
    ist_now = datetime.now(_tz('Asia/Kolkata'))
    generated_on_str = ist_now.strftime('%d %B %Y, %I:%M %p IST')

    receipt_data = {
        "member_name":     current_member.partner_name or 'N/A',
        "vgk_id":          current_member.partner_code,
        "phone":           current_member.phone or 'N/A',
        "email":           current_member.email or 'N/A',
        "role":            role_display,
        "join_date":       join_str,
        "activation_date": act_str,
        "points_credited": 51000,
        "receipt_number":  receipt_number,
        "generated_on":    generated_on_str,
    }

    pdf_buffer = generate_vgk_receipt(receipt_data)

    # Filename: Name_VGKID_ActivationDate.pdf
    safe_name = (current_member.partner_name or 'Member').replace(' ', '_').replace('/', '-')
    act_date_short = (current_member.vgk_activated_at or current_member.created_at or datetime.utcnow()).strftime('%d%b%Y')
    filename = f"{safe_name}_{current_member.partner_code}_{act_date_short}.pdf"
    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/kyc/status")
def vgk_kyc_status(
    current_member: OfficialPartner = Depends(get_current_vgk_member),
    db: Session = Depends(get_db)
):
    """DC Protocol Mar 2026: Get KYC documents and overall status for the logged-in VGK member."""
    docs = db.query(KYCDocument).filter(KYCDocument.partner_id == current_member.id).all()
    frontend_map = {'aadhar_front': 'aadhaar_front', 'aadhar_back': 'aadhaar_back',
                    'pan_card': 'pan_card', 'passport_photo': 'passport_photo',
                    'bank_passbook': 'bank_passbook'}
    # DC-VGK-PARTNER-SYNC-001 follow-up: expose file_url + mime_type so the
    # member can preview their own uploaded document inside a viewer modal.
    def _doc_url(fp):
        if not fp or fp == 'pending_upload':
            return None
        return '/storage/' + str(fp).lstrip('/')
    return {
        "success": True,
        "kyc_status": current_member.kyc_status or 'Not Submitted',
        "documents": [
            {
                "id": d.id,
                "document_type": frontend_map.get(d.document_type, d.document_type),
                "file_name": d.original_filename or d.file_name,
                "status": d.status,
                "uploaded_at": d.uploaded_at.isoformat() if d.uploaded_at else None,
                "rejection_reason": d.rejection_reason,
                "file_url": _doc_url(d.file_path),
                "mime_type": d.mime_type or 'application/octet-stream',
            }
            for d in docs
        ]
    }


@router.post("/kyc/upload")
async def vgk_kyc_upload(
    document_type: str = Form(...),
    file: UploadFile = File(...),
    current_member: OfficialPartner = Depends(get_current_vgk_member),
    db: Session = Depends(get_db)
):
    """DC Protocol Mar 2026: Upload KYC document for VGK member.
    Supports: aadhaar_front, aadhaar_back, pan_card, passport_photo.
    Blocks re-upload if document is already Approved."""
    if document_type not in _KYC_DOC_TYPE_MAP:
        raise HTTPException(status_code=400, detail=f"Invalid document type. Must be one of: {', '.join(_KYC_VALID_INPUT)}")
    doc_type_db = _KYC_DOC_TYPE_MAP[document_type]

    existing = db.query(KYCDocument).filter(
        and_(KYCDocument.partner_id == current_member.id, KYCDocument.document_type == doc_type_db)
    ).first()
    if existing:
        was_approved = existing.status == 'Approved'
        doc = existing
        from app.services.object_storage import storage_service
        for path in [existing.file_path, existing.compressed_path]:
            if path:
                try:
                    storage_service.delete_file(path)
                except Exception:
                    pass
        doc.status = 'Pending'
        doc.rejection_reason = None
        if was_approved:
            fresh_partner = db.query(OfficialPartner).filter(OfficialPartner.id == current_member.id).first()
            if fresh_partner and fresh_partner.kyc_status == 'Approved':
                fresh_partner.kyc_status = 'Pending'
        record_id = existing.id
    else:
        doc = KYCDocument(
            partner_id=current_member.id,
            document_type=doc_type_db,
            file_path='pending_upload',
            file_name='pending',
            original_filename=file.filename,
            file_size=1,
            mime_type='application/octet-stream',
            processing_status='pending',
            status='Pending',
            version=1,
            is_current_version=True
        )
        db.add(doc)
        db.flush()
        record_id = doc.id

    upload_result = await UniversalUploadService.handle_upload(
        file=file,
        table_name='kyc_document',
        record_id=record_id,
        uploaded_by_id=f"vgk_{current_member.id}",
        uploaded_by_type='partner',
        storage_dir='kyc_documents',
        db=db
    )

    doc.file_path = upload_result['file_path']
    doc.file_name = upload_result['file_name']
    doc.original_filename = upload_result['original_filename']
    doc.file_size = upload_result['file_size']
    doc.mime_type = upload_result['file_type']
    doc.processing_status = 'pending' if upload_result['needs_compression'] else 'completed'
    doc.uploaded_at = get_indian_time()

    db.commit()

    all_docs = db.query(KYCDocument).filter(KYCDocument.partner_id == current_member.id).all()
    uploaded_types = {d.document_type for d in all_docs}
    if _KYC_REQUIRED.issubset(uploaded_types):
        partner = db.query(OfficialPartner).filter(OfficialPartner.id == current_member.id).first()
        if partner and partner.kyc_status not in ('Pending', 'Approved'):
            partner.kyc_status = 'Pending'
            db.commit()

    return {
        "success": True,
        "message": f"{document_type.replace('_', ' ').title()} uploaded successfully",
        "status": "Pending verification"
    }


# ─── [DC-BANK-DETAILS-001] Apr 2026: Bank Details CRUD + Approval ─────────────

class BankDetailsRequest(BaseModel):
    bank_name: Optional[str] = None
    account_number: Optional[str] = None
    ifsc_code: Optional[str] = None
    bank_branch: Optional[str] = None


@router.get("/auth/bank-details/status")
def vgk_bank_details_status(
    current_member: OfficialPartner = Depends(get_current_vgk_member),
    db: Session = Depends(get_db)
):
    """[DC-BANK-DETAILS-001] Get bank details and passbook upload status for the logged-in VGK member."""
    passbook_doc = db.query(KYCDocument).filter(
        and_(KYCDocument.partner_id == current_member.id,
             KYCDocument.document_type == 'bank_passbook')
    ).first()
    return {
        "success": True,
        "bank_name": current_member.bank_name,
        "account_number": current_member.account_number,
        "ifsc_code": current_member.ifsc_code,
        "bank_branch": current_member.bank_branch,
        "bank_details_status": current_member.bank_details_status or 'Not Submitted',
        "bank_rejection_reason": current_member.bank_rejection_reason,
        "passbook_doc": {
            "id": passbook_doc.id,
            "file_name": passbook_doc.original_filename or passbook_doc.file_name,
            "status": passbook_doc.status,
            "uploaded_at": passbook_doc.uploaded_at.isoformat() if passbook_doc.uploaded_at else None,
            "rejection_reason": passbook_doc.rejection_reason
        } if passbook_doc else None
    }


@router.put("/auth/bank-details")
def vgk_save_bank_details(
    payload: BankDetailsRequest,
    current_member: OfficialPartner = Depends(get_current_vgk_member),
    db: Session = Depends(get_db)
):
    """[DC-BANK-DETAILS-001] Save bank details and set status to Pending. Blocked if Approved."""
    if current_member.bank_details_status == 'Approved':
        raise HTTPException(status_code=400, detail="Bank details already Approved. Contact support to update.")

    partner = db.query(OfficialPartner).filter(OfficialPartner.id == current_member.id).first()
    if not partner:
        raise HTTPException(status_code=404, detail="Member not found")

    if payload.bank_name is not None:
        partner.bank_name = payload.bank_name.strip() or None
    if payload.account_number is not None:
        acc = payload.account_number.strip()
        if acc and not acc.isdigit():
            raise HTTPException(status_code=400, detail="Account number must contain digits only.")
        partner.account_number = acc or None
    if payload.ifsc_code is not None:
        ifsc = payload.ifsc_code.strip().upper()
        if ifsc and len(ifsc) != 11:
            raise HTTPException(status_code=400, detail="IFSC code must be exactly 11 characters.")
        partner.ifsc_code = ifsc or None
    if payload.bank_branch is not None:
        partner.bank_branch = payload.bank_branch.strip() or None

    if partner.bank_details_status not in ('Approved',):
        partner.bank_details_status = 'Pending'
        partner.bank_rejection_reason = None

    db.commit()
    return {"success": True, "message": "Bank details saved and submitted for review."}


@router.post("/staff/bank-approve/{member_id}")
def staff_bank_approve(
    member_id: int,
    action: str = Body(..., embed=True),
    rejection_reason: Optional[str] = Body(None, embed=True),
    db: Session = Depends(get_db),
    request: Request = None,
):
    """[DC-BANK-DETAILS-001] Staff approves or rejects bank details for a VGK member.
    action: 'approve' or 'reject'. rejection_reason required for reject."""
    from app.api.v1.endpoints.staff_auth import get_current_staff_user
    from app.models.staff import StaffEmployee
    try:
        current_user: StaffEmployee = get_current_staff_user(request, db)
    except Exception:
        raise HTTPException(status_code=401, detail="Staff authentication required")

    if action not in ('approve', 'reject'):
        raise HTTPException(status_code=400, detail="action must be 'approve' or 'reject'")
    if action == 'reject' and not (rejection_reason or '').strip():
        raise HTTPException(status_code=400, detail="rejection_reason is required when rejecting.")

    member = db.query(OfficialPartner).filter(
        OfficialPartner.id == member_id,
        OfficialPartner.category == 'VGK_TEAM'
    ).first()
    if not member:
        raise HTTPException(status_code=404, detail="VGK member not found")

    passbook_doc = db.query(KYCDocument).filter(
        and_(KYCDocument.partner_id == member_id,
             KYCDocument.document_type == 'bank_passbook')
    ).first()

    if action == 'approve':
        member.bank_details_status = 'Approved'
        member.bank_rejection_reason = None
        if passbook_doc:
            passbook_doc.status = 'Approved'
            passbook_doc.reviewed_by_id = current_user.id
            passbook_doc.reviewed_at = get_indian_time()
            passbook_doc.rejection_reason = None
    else:
        member.bank_details_status = 'Rejected'
        member.bank_rejection_reason = rejection_reason.strip()
        if passbook_doc and passbook_doc.status != 'Approved':
            passbook_doc.status = 'Rejected'
            passbook_doc.rejection_reason = rejection_reason.strip()
            passbook_doc.reviewed_by_id = current_user.id
            passbook_doc.reviewed_at = get_indian_time()

    try:
        db.commit()
        past = 'approved' if action == 'approve' else 'rejected'
        logger.info(f"[DC-BANK-DETAILS-001] Staff {current_user.id} {past} bank details for member {member_id}")
        return {"success": True, "message": f"Bank details {past} successfully."}
    except Exception as e:
        db.rollback()
        logger.error(f"[DC-BANK-DETAILS-001] Bank approve failed for {member_id}: {e}")
        raise HTTPException(status_code=500, detail="Action failed. Please try again.")


@router.post("/dashboard/pin-purchase-request")
async def vgk_submit_pin_purchase(
    payment_method: str = Form(...),
    transaction_ref: str = Form(None),
    payment_notes: str = Form(None),
    file: UploadFile = File(None),
    current_member: OfficialPartner = Depends(get_current_vgk_member),
    db: Session = Depends(get_db)
):
    if current_member.is_active and current_member.vgk_activated_at:
        raise HTTPException(status_code=400, detail="Your account is already activated")
    existing = db.query(VGKPINPurchaseRequest).filter(
        VGKPINPurchaseRequest.partner_id == current_member.id,
        VGKPINPurchaseRequest.status == 'PENDING'
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="You already have a pending PIN purchase request. Please wait for staff approval.")

    pin_req = VGKPINPurchaseRequest(
        partner_id=current_member.id,
        company_id=current_member.company_id or 1,
        amount=Decimal('5000'),
        payment_method=payment_method.strip(),
        transaction_ref=transaction_ref.strip() if transaction_ref else None,
        payment_notes=payment_notes.strip() if payment_notes else None,
        status='PENDING',
    )
    db.add(pin_req)
    db.flush()

    screenshot_url = None
    if file and file.filename:
        upload_result = await UniversalUploadService.handle_upload(
            file=file,
            table_name='vgk_pin_purchase_requests',
            record_id=pin_req.id,
            uploaded_by_id=f"vgk_{current_member.id}",
            uploaded_by_type='partner',
            storage_dir='vgk_pin_screenshots',
            db=db
        )
        screenshot_url = upload_result.get('file_path') or upload_result.get('url')
        pin_req.payment_screenshot_url = screenshot_url

    db.commit()
    db.refresh(pin_req)
    logger.info(f"[VGK-PIN-REQ] Member {current_member.partner_code} submitted PIN purchase request #{pin_req.id}")
    return {
        "success": True,
        "message": "PIN purchase request submitted successfully. Staff will review and approve shortly.",
        "data": pin_req.to_dict()
    }


@router.get("/dashboard/pin-purchase-status")
def vgk_pin_purchase_status(
    current_member: OfficialPartner = Depends(get_current_vgk_member),
    db: Session = Depends(get_db)
):
    requests = db.query(VGKPINPurchaseRequest).filter(
        VGKPINPurchaseRequest.partner_id == current_member.id
    ).order_by(VGKPINPurchaseRequest.created_at.desc()).all()

    return {
        "success": True,
        "data": [r.to_dict() for r in requests],
        "has_pending": any(r.status == 'PENDING' for r in requests)
    }


# ── DC Protocol Mar 2026: VGK Terms & Conditions ─────────────────────────────

@router.get("/public/terms")
def vgk_public_terms(db: Session = Depends(get_db)):
    """Return the current VGK-platform Terms & Conditions (active preferred; falls back to most recent draft)."""
    from app.models.system_control import TermsAndConditionsVersion
    from sqlalchemy import or_ as sa_or
    _vgk_filter = sa_or(
        TermsAndConditionsVersion.platform_type == 'VGK',
        TermsAndConditionsVersion.platform_type == 'ALL',
    )
    tc = db.query(TermsAndConditionsVersion).filter(
        TermsAndConditionsVersion.is_active == True,
        _vgk_filter
    ).order_by(TermsAndConditionsVersion.id.desc()).first()
    if not tc:
        tc = db.query(TermsAndConditionsVersion).filter(
            _vgk_filter
        ).order_by(TermsAndConditionsVersion.id.desc()).first()
    if not tc:
        return {"success": False, "message": "No VGK Terms & Conditions found", "data": None}
    return {
        "success": True,
        "data": {
            "version": tc.version,
            "content": tc.content,
            "activated_at": tc.activated_at.isoformat() if tc.activated_at else None,
            "platform_type": tc.platform_type,
        }
    }


@router.post("/member/accept-terms")
def vgk_accept_terms(
    request: Request,
    current_member: OfficialPartner = Depends(get_current_vgk_member),
    db: Session = Depends(get_db)
):
    """Record that the authenticated VGK member has accepted the current T&C version."""
    from app.models.system_control import TermsAndConditionsVersion
    from sqlalchemy import or_ as sa_or, text as sa_text
    tc = db.query(TermsAndConditionsVersion).filter(
        TermsAndConditionsVersion.is_active == True,
        sa_or(
            TermsAndConditionsVersion.platform_type == 'VGK',
            TermsAndConditionsVersion.platform_type == 'ALL',
        )
    ).order_by(TermsAndConditionsVersion.id.desc()).first()
    if not tc:
        raise HTTPException(status_code=404, detail="No active VGK Terms & Conditions found")

    ip_address = request.headers.get("X-Forwarded-For", request.client.host if request.client else "unknown")
    user_agent = request.headers.get("User-Agent", "")

    try:
        db.execute(sa_text("""
            INSERT INTO vgk_terms_acceptance_log (partner_id, version, ip_address, user_agent, accepted_at, created_at)
            VALUES (:pid, :ver, :ip, :ua, NOW(), NOW())
        """), {"pid": current_member.id, "ver": tc.version, "ip": ip_address[:45], "ua": user_agent})

        db.execute(sa_text("""
            UPDATE official_partners
               SET accepted_terms_version = :ver, terms_accepted_at = NOW()
             WHERE id = :pid
        """), {"pid": current_member.id, "ver": tc.version})

        db.commit()
        logger.info(f"[VGK-TERMS] Partner {current_member.partner_code} accepted T&C v{tc.version}")
    except Exception as e:
        db.rollback()
        logger.error(f"[VGK-TERMS] accept-terms failed for {current_member.partner_code}: {e}")
        raise HTTPException(status_code=500, detail="Failed to record T&C acceptance")

    return {"success": True, "message": f"Terms & Conditions v{tc.version} accepted.", "version": tc.version}


@router.get("/member/earning-capacity")
def vgk_earning_capacity(
    current_member: OfficialPartner = Depends(get_current_vgk_member),
    db: Session = Depends(get_db)
):
    """
    DC Protocol Mar 2026: VGK member earning capacity.
    Returns configured commission rates (L1-L4) per deal category,
    actual earnings per category/level from income entries,
    marketplace segment discounts, and monthly trend.
    No negative impact on existing income/ledger endpoints.
    """
    from app.models.signup_category import SignupCategory
    from app.models.staff_accounts import VGKTeamCommissionConfig
    from app.models.marketplace import MarketplaceSegment
    from sqlalchemy import text as sa_text

    company_id = current_member.company_id
    partner_id = current_member.id
    is_loyal = bool(getattr(current_member, 'is_loyal_coupon', False))

    # 1. Commission configs joined with category names
    # DC Protocol: NO company_id restriction on commission config — VGK rates are universal.
    # Fetch all active configs; split into activated-tier and registered-tier lists for
    # the tabbed UI (Tab 1 = Activated rates, Tab 2 = Registered rates, Tab 3 = Calculator).
    _all_configs = (
        db.query(VGKTeamCommissionConfig, SignupCategory)
        .join(SignupCategory, VGKTeamCommissionConfig.category_id == SignupCategory.id)
        .filter(VGKTeamCommissionConfig.is_active == True)
        .order_by(
            SignupCategory.display_order,
            SignupCategory.name,
            VGKTeamCommissionConfig.updated_at.desc(),
        )
        .all()
    )
    _seen_act: set = set()
    _seen_reg: set = set()
    activated_cfgs: list = []
    registered_cfgs: list = []
    for _c, _cat in _all_configs:
        # [DC-VGK-REFBONUS-DEDUP] Dedup by category NAME (not id) so that multiple
        # signup_category rows sharing the same display name collapse to one row.
        _cname = _cat.name
        if bool(_c.is_paid_member):
            if _cname not in _seen_act:
                _seen_act.add(_cname)
                activated_cfgs.append((_c, _cat))
        else:
            if _cname not in _seen_reg:
                _seen_reg.add(_cname)
                registered_cfgs.append((_c, _cat))
    # DC Protocol: Build category-name ↔ category-id maps so earnings recorded under
    # any company's category_id (sibling cat_ids with the same name) are aggregated
    # correctly regardless of which cat_id was stamped on the income entry.
    _cat_id_to_name: dict = {}
    _name_to_cat_ids: dict = {}
    for _c, _cat in _all_configs:
        _cat_id_to_name[_c.category_id] = _cat.name
        _name_to_cat_ids.setdefault(_cat.name, set()).add(_c.category_id)

    def _merge_earnings(cat_id: int, lvl: int) -> dict:
        """Sum earnings across all category_ids sharing the same name."""
        sibling_ids = _name_to_cat_ids.get(_cat_id_to_name.get(cat_id, ''), {cat_id})
        merged: dict = {}
        for _sid in sibling_ids:
            _e = earnings_map.get((_sid, lvl))
            if not _e:
                continue
            merged['total_earned']  = merged.get('total_earned',  0) + _e.get('total_earned',  0)
            merged['confirmed']     = merged.get('confirmed',     0) + _e.get('confirmed',     0)
            merged['pending']       = merged.get('pending',       0) + _e.get('pending',       0)
            merged['hold']          = merged.get('hold',          0) + _e.get('hold',          0)
            merged['deal_count']    = merged.get('deal_count',    0) + _e.get('deal_count',    0)
            _lat = _e.get('last_earned_at')
            if _lat and (not merged.get('last_earned_at') or _lat > merged['last_earned_at']):
                merged['last_earned_at'] = _lat
        return merged

    # For earnings column: match member's own tier
    member_is_paid = bool(getattr(current_member, 'is_paid_activation', False))
    configs = activated_cfgs if member_is_paid else registered_cfgs

    # 2. Earnings aggregated per category_id + level (excluding cancelled)
    earnings_rows = db.execute(sa_text("""
        SELECT
            category_id,
            level,
            SUM(commission_amount + bonus_amount)                                                    AS total_earned,
            SUM(CASE WHEN status='CONFIRMED' THEN commission_amount + bonus_amount ELSE 0 END)       AS confirmed,
            SUM(CASE WHEN status='PENDING'   THEN commission_amount + bonus_amount ELSE 0 END)       AS pending_amt,
            SUM(CASE WHEN status='HOLD'      THEN commission_amount + bonus_amount ELSE 0 END)       AS hold_amt,
            COUNT(*)                                                                                 AS deal_count,
            MAX(created_at)                                                                          AS last_earned_at
        FROM vgk_team_income_entries
        WHERE partner_id = :pid
          AND company_id = :cid
          AND status != 'CANCELLED'
          AND level > 0
        GROUP BY category_id, level
    """), {"pid": partner_id, "cid": company_id}).fetchall()

    earnings_map = {}
    for row in earnings_rows:
        earnings_map[(row.category_id, row.level)] = {
            'total_earned':  float(row.total_earned  or 0),
            'confirmed':     float(row.confirmed     or 0),
            'pending':       float(row.pending_amt   or 0),
            'hold':          float(row.hold_amt      or 0),
            'deal_count':    int(row.deal_count      or 0),
            'last_earned_at': row.last_earned_at.isoformat() if row.last_earned_at else None,
        }

    # 3. Grand totals across all categories
    totals = db.execute(sa_text("""
        SELECT
            SUM(commission_amount + bonus_amount)                                                    AS grand_total,
            SUM(CASE WHEN status='CONFIRMED' THEN commission_amount + bonus_amount ELSE 0 END)       AS confirmed_total,
            SUM(CASE WHEN status='PENDING'   THEN commission_amount + bonus_amount ELSE 0 END)       AS pending_total,
            SUM(CASE WHEN status='HOLD'      THEN commission_amount + bonus_amount ELSE 0 END)       AS hold_total,
            COUNT(*)                                                                                 AS total_deals
        FROM vgk_team_income_entries
        WHERE partner_id = :pid
          AND company_id = :cid
          AND status != 'CANCELLED'
          AND level > 0
    """), {"pid": partner_id, "cid": company_id}).fetchone()

    # 4. Monthly trend — last 6 months
    monthly_rows = db.execute(sa_text("""
        SELECT
            TO_CHAR(created_at AT TIME ZONE 'Asia/Kolkata', 'YYYY-MM')  AS month,
            TO_CHAR(created_at AT TIME ZONE 'Asia/Kolkata', 'Mon YYYY') AS month_label,
            SUM(commission_amount + bonus_amount)                        AS total
        FROM vgk_team_income_entries
        WHERE partner_id = :pid
          AND company_id = :cid
          AND status != 'CANCELLED'
          AND level > 0
          AND created_at >= NOW() - INTERVAL '6 months'
        GROUP BY 1, 2
        ORDER BY 1
    """), {"pid": partner_id, "cid": company_id}).fetchall()

    # 5. Marketplace segments — vgk_pct per segment
    segments = (
        db.query(MarketplaceSegment)
        .filter(
            MarketplaceSegment.company_id == company_id,
            MarketplaceSegment.is_active == True
        )
        .order_by(MarketplaceSegment.sort_order)
        .all()
    )

    # Build per-category list from a given config set; include earnings only for own-tier
    def _build_cat_list(cfg_pairs, include_earnings=False):
        result = []
        for cfg, cat in cfg_pairs:
            cat_id = cfg.category_id
            levels = []
            for lvl in [1, 2, 3, 4]:
                pct   = float(getattr(cfg, f'level{lvl}_pct') or 0)
                amt   = float(getattr(cfg, f'level{lvl}_amt') or 0)
                ltype = getattr(cfg, f'level{lvl}_type') or 'PCT'
                earned = _merge_earnings(cat_id, lvl) if include_earnings else {}
                restricted = is_loyal and lvl in (3, 4)
                levels.append({
                    'level':          lvl,
                    'pct':            pct,
                    'amt':            amt,
                    'type':           ltype,
                    'restricted':     restricted,
                    'total_earned':   earned.get('total_earned', 0),
                    'confirmed':      earned.get('confirmed', 0),
                    'pending':        earned.get('pending', 0),
                    'hold':           earned.get('hold', 0),
                    'deal_count':     earned.get('deal_count', 0),
                    'last_earned_at': earned.get('last_earned_at'),
                })
            result.append({
                'category_id':    cat_id,
                'category_name':  cat.name,
                'category_icon':  cat.icon or 'fas fa-handshake',
                'monthly_target': float(cfg.monthly_target or 0),
                'bonus_pct':      float(cfg.bonus_pct or 0),
                'levels':         levels,
            })
        return result

    # Build both tier lists; earnings only on the member's own tier
    category_list          = _build_cat_list(configs,          include_earnings=True)
    activated_category_list = _build_cat_list(activated_cfgs,  include_earnings=member_is_paid)
    registered_category_list= _build_cat_list(registered_cfgs, include_earnings=not member_is_paid)

    return {
        'success':    True,
        'is_loyal_coupon': is_loyal,
        'member_is_paid': member_is_paid,
        'summary': {
            'grand_total':     float(totals.grand_total     or 0) if totals else 0,
            'confirmed_total': float(totals.confirmed_total or 0) if totals else 0,
            'pending_total':   float(totals.pending_total   or 0) if totals else 0,
            'hold_total':      float(totals.hold_total      or 0) if totals else 0,
            'total_deals':     int(totals.total_deals       or 0) if totals else 0,
        },
        'commission_configs':     category_list,
        'activated_configs':      activated_category_list,
        'registered_configs':     registered_category_list,
        'monthly_trend': [
            {'month': r.month, 'label': r.month_label, 'total': float(r.total or 0)}
            for r in monthly_rows
        ],
        'marketplace_segments': [
            {
                'segment_id':   s.id,
                'segment_name': s.name,
                'vgk_pct':      float(s.vgk_pct or 0),
            }
            for s in segments
        ],
    }


@router.get("/public/commission-rates")
def vgk_public_commission_rates(db: Session = Depends(get_db)):
    """
    Public endpoint — no auth required.
    Returns commission rate structure (Registered + Activated) per product category.
    DC Protocol: NO company_id restriction — VGK rates are universal across all companies.
    Reads all active configs, deduplicates by (category_name, is_paid_member) keeping
    the most recently updated record so admin changes reflect immediately everywhere.
    """
    from app.models.staff_accounts import VGKTeamCommissionConfig
    from app.models.signup_category import SignupCategory

    # No company_id filter — VGK rates are global. Order by updated_at DESC so the
    # most recently edited config wins when deduplicating across companies.
    configs = (
        db.query(VGKTeamCommissionConfig, SignupCategory)
        .join(SignupCategory, VGKTeamCommissionConfig.category_id == SignupCategory.id)
        .filter(
            VGKTeamCommissionConfig.is_active == True,
        )
        .order_by(
            SignupCategory.display_order,
            SignupCategory.name,
            VGKTeamCommissionConfig.is_paid_member,
            VGKTeamCommissionConfig.updated_at.desc(),
        )
        .all()
    )

    def _rate_block(cfg):
        l1p  = float(cfg.level1_pct  or 0)
        l2p  = float(cfg.level2_pct  or 0)
        l3p  = float(cfg.level3_pct  or 0)
        l4cp = float(getattr(cfg, 'level4_core_pct', None) or 0)
        l5p  = float(cfg.level4_pct  or 0)   # L5 Support (stored as level4_pct)
        l1a  = float(cfg.level1_amt  or 0)
        l2a  = float(cfg.level2_amt  or 0)
        l3a  = float(cfg.level3_amt  or 0)
        l4ca = float(getattr(cfg, 'level4_core_amt', None) or 0)
        l5a  = float(cfg.level4_amt  or 0)
        has_rates = any(v > 0 for v in [l1p, l2p, l3p, l4cp, l5p, l1a, l2a, l3a, l4ca, l5a])
        return {
            "level1_pct":      l1p,
            "level2_pct":      l2p,
            "level3_pct":      l3p,
            "level4_core_pct": l4cp,
            "level4_pct":      l5p,
            "level1_type":     cfg.level1_type or "PCT",
            "level2_type":     cfg.level2_type or "PCT",
            "level3_type":     cfg.level3_type or "PCT",
            "level4_core_type": getattr(cfg, 'level4_core_type', None) or "PCT",
            "level4_type":     cfg.level4_type or "PCT",
            "level1_amt":      l1a,
            "level2_amt":      l2a,
            "level3_amt":      l3a,
            "level4_core_amt": l4ca,
            "level4_amt":      l5a,
            "bonus_pct":       float(cfg.bonus_pct   or 0),
            "markup_pct":      float(cfg.markup_pct  or 0),
            "has_rates":       has_rates,
        }

    # Deduplicate: first occurrence per (category_name, is_paid_member) = latest updated
    seen: set = set()
    cat_map: dict = {}
    for cfg, cat in configs:
        cname = cat.name
        key = (cname, bool(cfg.is_paid_member))
        if key in seen:
            continue
        seen.add(key)
        if cname not in cat_map:
            cat_map[cname] = {
                "category_id":    cat.id,
                "category_name":  cname,
                "display_order":  cat.display_order or 0,
                "registered":     None,
                "activated":      None,
            }
        if cfg.is_paid_member:
            cat_map[cname]["activated"]  = _rate_block(cfg)
        else:
            cat_map[cname]["registered"] = _rate_block(cfg)

    # Only return categories where at least one config (registered or activated)
    # has at least one non-zero rate — skips "No Config" categories shown in admin.
    def _cat_has_rates(entry):
        reg = entry.get("registered")
        act = entry.get("activated")
        return (reg and reg.get("has_rates")) or (act and act.get("has_rates"))

    result = sorted(
        [e for e in cat_map.values() if _cat_has_rates(e)],
        key=lambda x: (x["display_order"], x["category_name"])
    )
    return {"success": True, "data": result}


@router.get("/member/staff-search")
def vgk_staff_search(
    q: str = "",
    current_member: OfficialPartner = Depends(get_current_vgk_member),
    db: Session = Depends(get_db)
):
    """[DC-STAFF-SEARCH] VGK member search for active staff to assign as lead handler."""
    from app.models.staff import StaffEmployee
    query = q.strip()
    if len(query) < 2:
        return {"success": True, "data": []}
    results = db.query(StaffEmployee).filter(
        StaffEmployee.status == 'active',
        or_(
            StaffEmployee.full_name.ilike(f"%{query}%"),
            StaffEmployee.emp_code.ilike(f"%{query}%"),
        )
    ).order_by(StaffEmployee.full_name).limit(10).all()
    return {"success": True, "data": [
        {"id": s.id, "full_name": s.full_name, "emp_code": s.emp_code,
         "designation": getattr(s, 'designation', None) or ''}
        for s in results
    ]}


@router.get("/public/member-lookup")
async def public_member_lookup(q: str = "", db: Session = Depends(get_db)):
    """
    Public lookup: find VGK members by partial code, phone, or name.
    Returns up to 10 results — no sensitive data exposed.
    DC Protocol: partial code search + list response for UX.
    """
    query = q.strip()
    if len(query) < 3:
        raise HTTPException(status_code=400, detail="Search term too short (min 3 chars)")

    # DC Protocol: include all VGK_TEAM members regardless of activation status
    partners = db.query(OfficialPartner).filter(
        OfficialPartner.category == 'VGK_TEAM',
        or_(
            OfficialPartner.partner_code.ilike(f'%{query}%'),
            OfficialPartner.phone == query,
            OfficialPartner.partner_name.ilike(f'%{query}%')
        )
    ).order_by(
        OfficialPartner.partner_name.asc()
    ).limit(10).all()

    if not partners:
        raise HTTPException(status_code=404, detail="No VGK member found")
    return {
        "results": [
            {"id": p.id, "partner_name": p.partner_name, "partner_code": p.partner_code}
            for p in partners
        ]
    }


@router.get("/public/influencer-lookup")
def public_influencer_lookup(code: str = "", db: Session = Depends(get_db)):
    """
    Public endpoint — no auth required.
    Look up an influencer by their referral code.
    Used by the signup form to auto-fill fields from influencer referral links.
    Returns: found, name, code, vgk_member_id (if any), signup_bonus_points.
    """
    from sqlalchemy import text as _itext
    code_val = code.strip().upper()
    if not code_val or len(code_val) < 2:
        return {"found": False}
    row = db.execute(_itext(
        "SELECT id, name, referral_code, vgk_member_id, COALESCE(signup_bonus_points, 0) "
        "FROM promo_influencers WHERE referral_code = :rc AND status != 'inactive' LIMIT 1"
    ), {"rc": code_val}).fetchone()
    if not row:
        return {"found": False}
    return {
        "found": True,
        "name": row[1],
        "code": row[2],
        "vgk_member_id": row[3],
        "signup_bonus_points": int(row[4] or 0),
    }


@router.get("/public/promo-check")
def public_promo_check(code: str = "", db: Session = Depends(get_db)):
    """
    Public endpoint — no auth required.
    Preview a VGK promo code before signup/login.
    Returns basic info: valid, label, promo_type, points_credit.
    Does NOT redeem the code.
    """
    import datetime as _dt
    import pytz as _pytz

    code_val = code.strip().upper()
    if not code_val:
        raise HTTPException(status_code=400, detail="Code is required")

    from app.models.staff_accounts import VGKPromoCode as _VPC
    pc = db.query(_VPC).filter(_VPC.code == code_val).first()
    if not pc:
        # [DC-INFLUENCER] Also check if it's an influencer referral code
        from sqlalchemy import text as _itext2
        infl = db.execute(_itext2(
            "SELECT name, referral_code, COALESCE(signup_bonus_points, 0), gender, name_title "
            "FROM promo_influencers WHERE referral_code = :rc AND status != 'inactive' LIMIT 1"
        ), {"rc": code_val}).fetchone()
        if infl and int(infl[2] or 0) > 0:
            return {
                "valid": True,
                "code": infl[1],
                "label": infl[0],
                "gender": infl[3] or '',
                "name_title": infl[4] or '',
                "promo_type": "INFLUENCER",
                "type_label": "Influencer Referral",
                "points_credit": float(infl[2]),
                "needs_verification": False,
            }
        return {"valid": False, "error": "Promo code not found. Please check and try again."}
    if pc.status != 'ACTIVE':
        return {"valid": False, "error": "This promo code is not currently active."}

    _now = _dt.datetime.now(_pytz.timezone('Asia/Kolkata')).replace(tzinfo=None)
    if pc.valid_from and _now < pc.valid_from:
        return {"valid": False, "error": "This promo code is not yet valid."}
    if pc.valid_to and _now > pc.valid_to:
        return {"valid": False, "error": "This promo code has expired."}
    if pc.usage_limit and pc.times_used >= pc.usage_limit:
        return {"valid": False, "error": "This promo code has reached its usage limit."}

    # Build a friendly label for the promo type
    type_label = {
        'GENERAL': 'Campaign Code',
        'MNR_MEMBER': 'MNR Member Code',
        'ETC_STUDENT': 'ETC Student Code',
    }.get(pc.promo_type, pc.promo_type)

    # For non-GENERAL codes, signal that extra verification is needed after login
    needs_verification = pc.promo_type != 'GENERAL'

    return {
        "valid": True,
        "code": pc.code,
        "label": pc.label or "",
        "promo_type": pc.promo_type,
        "type_label": type_label,
        "points_credit": float(pc.points_credit or 0),
        "needs_verification": needs_verification,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# VGK PROMO CODE — Member Redemption  (DC Protocol Apr 2026)
# ═══════════════════════════════════════════════════════════════════════════════

from app.models.staff_accounts import VGKPromoCode, VGKPromoRedemption


class PromoRedeemRequest(BaseModel):
    code: str = Field(..., min_length=1)
    verified_ref: Optional[str] = None


@router.post("/member/redeem-promo")
def member_redeem_promo(
    body: PromoRedeemRequest,
    current_member: OfficialPartner = Depends(get_current_vgk_member),
    db: Session = Depends(get_db),
):
    """
    Member redeems a VGK promo code.
    - GENERAL: type code → points awarded immediately.
    - MNR_MEMBER: verified_ref = MNR User ID → check user.coupon_status for activation.
    - ETC_STUDENT: verified_ref = Student ID → look up etc_students.package_value → tier_config points.
    All codes: one-time per member (unique promo_code_id + partner_id constraint).
    """
    import datetime as _dt
    import pytz as _pytz
    import sqlalchemy as _sa

    from app.services.vgk_commission import add_vgk_points_entry
    from decimal import Decimal

    code_val = body.code.strip().upper()

    # ── Direct ID pattern detection (MNR / ETC / VGK) ─────────────────────────
    # These ID formats are accepted directly as promo codes without a vgk_promo_codes row.
    # Dedup is tracked via vgk_points_ledger notes (promo_code_id FK is not nullable so
    # VGKPromoRedemption cannot be used here).
    _now_tz = _dt.datetime.now(_pytz.timezone('Asia/Kolkata')).replace(tzinfo=None)

    def _direct_already_used(dedup_key: str) -> bool:
        hit = db.execute(
            _sa.text(
                "SELECT id FROM vgk_points_ledger "
                "WHERE partner_id = :pid AND notes LIKE :pat LIMIT 1"
            ),
            {"pid": current_member.id, "pat": f"%Direct ID: {dedup_key}%"}
        ).fetchone()
        return hit is not None

    def _direct_category_used(prefix: str) -> bool:
        """Returns True if this member has already redeemed ANY ID of the given prefix (MNR/ETC/VGK)."""
        hit = db.execute(
            _sa.text(
                "SELECT id FROM vgk_points_ledger "
                "WHERE partner_id = :pid AND notes LIKE :pat LIMIT 1"
            ),
            {"pid": current_member.id, "pat": f"%Direct ID: {prefix}%"}
        ).fetchone()
        return hit is not None

    def _award_direct(pts: Decimal, notes: str) -> dict:
        add_vgk_points_entry(
            db=db,
            partner_id=current_member.id,
            points_credit=pts,
            points_debit=Decimal('0'),
            reason_code='CAMPAIGN_BONUS',
            reference_type='PROMO_CODE',
            reference_id=None,
            notes=notes,
        )
        db.commit()
        new_bal = float(current_member.vgk_points_balance or 0)
        return {
            "success": True,
            "message": f"🎉 {int(pts):,} points credited to your account!",
            "points_awarded": float(pts),
            "new_balance": new_bal,
        }

    # ── MNR User ID (e.g. MNR1800143) ────────────────────────────────────────
    if _re.match(r'^MNR\d{5,}$', code_val):
        from app.models.user import User as _MNRUser
        if _direct_category_used('MNR'):
            raise HTTPException(status_code=409, detail="You have already redeemed an MNR Member ID. Only one MNR ID is allowed per member.")
        if _direct_already_used(code_val):
            raise HTTPException(status_code=409, detail="You have already redeemed this MNR ID.")
        mnr_user = db.query(_MNRUser).filter(_MNRUser.id == code_val).first()
        if not mnr_user:
            raise HTTPException(status_code=404, detail="MNR User ID not found. Please check and try again.")
        _mnr_status = (mnr_user.coupon_status or '').strip().lower()
        if _mnr_status in ('active', 'activated'):
            pts = Decimal('15000')
            tier_label = 'Activated'
        else:
            pts = Decimal('5000')
            tier_label = 'Non-Activated'
        return _award_direct(
            pts,
            f"Direct ID: {code_val} | MNR Member ({tier_label}) | {int(pts)} pts"
        )

    # ── ETC Student ID (e.g. ETC-001234 or ETC001234) ─────────────────────────
    if _re.match(r'^ETC[-]?\d+$', code_val):
        if _direct_category_used('ETC'):
            raise HTTPException(status_code=409, detail="You have already redeemed an ETC Student ID. Only one ETC ID is allowed per member.")
        if _direct_already_used(code_val):
            raise HTTPException(status_code=409, detail="You have already redeemed this ETC Student ID.")
        etc_row = db.execute(
            _sa.text(
                "SELECT student_id, package_value, training_completed_date FROM etc_students "
                "WHERE LOWER(student_id) = LOWER(:sid) AND is_active = TRUE LIMIT 1"
            ),
            {"sid": code_val}
        ).fetchone()
        if not etc_row:
            raise HTTPException(status_code=404, detail="ETC Student ID not found. Please verify your ID and try again.")
        if not etc_row.training_completed_date:
            raise HTTPException(status_code=400, detail="Training not yet completed. Points will be available once your training completion is recorded.")
        pkg_val = float(etc_row.package_value) if etc_row.package_value else 0.0
        # Default tier config for direct ETC redemption
        if pkg_val >= 10000:
            etc_pts = Decimal('10000')
        elif pkg_val >= 5000:
            etc_pts = Decimal('7500')
        else:
            etc_pts = Decimal('5000')
        return _award_direct(
            etc_pts,
            f"Direct ID: {code_val} | ETC Student | Pkg: ₹{pkg_val:,.0f} | {int(etc_pts)} pts"
        )

    # ── VGK Partner/Promoter ID (e.g. VGK07100001) ────────────────────────────
    if _re.match(r'^VGK\d{8}$', code_val):
        if code_val == (current_member.partner_code or '').upper():
            raise HTTPException(status_code=400, detail="You cannot use your own VGK ID as a promo code.")
        if _direct_category_used('VGK'):
            raise HTTPException(status_code=409, detail="You have already redeemed a VGK Promoter ID. Only one VGK ID is allowed per member.")
        if _direct_already_used(code_val):
            raise HTTPException(status_code=409, detail="You have already redeemed this VGK Promoter ID.")
        vgk_promoter = db.query(OfficialPartner).filter(
            OfficialPartner.partner_code == code_val,
            OfficialPartner.category == 'VGK_TEAM',
        ).first()
        if not vgk_promoter:
            raise HTTPException(status_code=404, detail="VGK Promoter ID not found. Please check and try again.")
        vgk_pts = Decimal('5000')
        return _award_direct(
            vgk_pts,
            f"Direct ID: {code_val} | VGK Promoter Referral | {int(vgk_pts)} pts"
        )

    # ── Standard promo code flow (vgk_promo_codes table lookup) ───────────────
    pc = db.query(VGKPromoCode).filter(VGKPromoCode.code == code_val).first()

    # ── Existence & status checks ─────────────────────────────────────────────
    if not pc:
        raise HTTPException(status_code=404, detail="Promo code not found. Please check the code and try again.")
    if pc.status != 'ACTIVE':
        raise HTTPException(status_code=400, detail="This promo code is currently not active.")

    # ── Validity window ───────────────────────────────────────────────────────
    now = _dt.datetime.now(_pytz.timezone('Asia/Kolkata')).replace(tzinfo=None)
    if pc.valid_from and now < pc.valid_from:
        raise HTTPException(status_code=400, detail="This promo code is not yet valid.")
    if pc.valid_to and now > pc.valid_to:
        raise HTTPException(status_code=400, detail="This promo code has expired.")

    # ── Usage limit ───────────────────────────────────────────────────────────
    if pc.usage_limit and pc.times_used >= pc.usage_limit:
        raise HTTPException(status_code=400, detail="This promo code has reached its usage limit.")

    # ── One-time per member check ─────────────────────────────────────────────
    already = db.query(VGKPromoRedemption).filter(
        VGKPromoRedemption.promo_code_id == pc.id,
        VGKPromoRedemption.partner_id == current_member.id,
    ).first()
    if already:
        raise HTTPException(status_code=409, detail="You have already redeemed this promo code.")

    # ── Applicability: activation status check ────────────────────────────────
    appl_status = (pc.applicability_status or 'ALL').upper()
    if appl_status == 'ACTIVATED' and not current_member.is_active:
        raise HTTPException(status_code=403, detail="This promo code is for activated members only.")

    # ── Applicability: member timing check (Option A — date comparison) ────────
    appl_timing = (pc.applicability_timing or 'BOTH').upper()
    if appl_timing != 'BOTH':
        member_joined = current_member.created_at  # naive datetime
        code_created  = pc.created_at              # naive datetime
        if member_joined and code_created:
            if appl_timing == 'EXISTING' and member_joined > code_created:
                raise HTTPException(status_code=403, detail="This promo code is for members who joined before it was created.")
            if appl_timing == 'NEW' and member_joined <= code_created:
                raise HTTPException(status_code=403, detail="This promo code is for newly joined members only.")

    # ── Type-specific validation & points calculation ─────────────────────────
    points_to_award = Decimal(str(pc.points_credit))
    verified_ref = None
    notes = f"Promo code redemption: {code_val}"

    if pc.promo_type == 'MNR_MEMBER':
        ref = (body.verified_ref or '').strip()
        if not ref:
            raise HTTPException(status_code=400, detail="Please provide your MNR User ID.")
        # Look up the MNR user
        from app.models.user import User as MNRUser
        mnr_user = db.query(MNRUser).filter(MNRUser.id == ref).first()
        if not mnr_user:
            raise HTTPException(status_code=404, detail="MNR User ID not found. Please verify your ID and try again.")
        # Check this MNR ID hasn't been used by another VGK partner
        already_used = db.query(VGKPromoRedemption).filter(
            VGKPromoRedemption.promo_code_id == pc.id,
            VGKPromoRedemption.verified_ref == ref,
        ).first()
        if already_used:
            raise HTTPException(status_code=409, detail="This MNR User ID has already been used to claim this code.")
        # Award points based on activation status
        _mnr_cs = (mnr_user.coupon_status or '').strip().lower()
        if _mnr_cs in ('active', 'activated'):
            points_to_award = Decimal('15000')
            notes = f"MNR Member Code: {code_val} | MNR ID: {ref} (Activated) | 15,000 pts"
        else:
            points_to_award = Decimal('5000')
            notes = f"MNR Member Code: {code_val} | MNR ID: {ref} (Non-Activated) | 5,000 pts"
        verified_ref = ref

    elif pc.promo_type == 'ETC_STUDENT':
        ref = (body.verified_ref or '').strip()
        if not ref:
            raise HTTPException(status_code=400, detail="Please provide your ETC Student ID.")
        # Look up ETC student
        row = db.execute(
            _sa.text(
                "SELECT student_id, package_value, training_completed_date FROM etc_students "
                "WHERE LOWER(student_id) = LOWER(:sid) AND is_active = TRUE LIMIT 1"
            ),
            {"sid": ref}
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="ETC Student ID not found. Please verify your ID and try again.")
        pkg_val = float(row.package_value) if row.package_value else None
        tcd = row.training_completed_date
        if not tcd:
            raise HTTPException(status_code=400, detail="Training not yet completed. Points will be available once your training completion is recorded.")
        if not pkg_val or pkg_val <= 0:
            raise HTTPException(
                status_code=400,
                detail="No package value is recorded for your student profile. Please contact the VGK or ETC team to update your details."
            )
        # Resolve points from tier_config
        tier_cfg = pc.tier_config or []
        resolved_pts = None
        for tier in sorted(tier_cfg, key=lambda t: t.get('min_val', 0)):
            min_v = float(tier.get('min_val', 0))
            max_v = tier.get('max_val')
            pts = float(tier.get('points', 0))
            if max_v is not None:
                if min_v <= pkg_val <= float(max_v):
                    resolved_pts = pts
                    break
            else:
                if pkg_val >= min_v:
                    resolved_pts = pts
                    break
        if resolved_pts is None or resolved_pts <= 0:
            raise HTTPException(status_code=400, detail="No points are configured for your training package value. Please contact the VGK or ETC team.")
        points_to_award = Decimal(str(resolved_pts))
        notes = f"ETC Student Code: {code_val} | Student ID: {ref} | Pkg: ₹{pkg_val:,.0f} | {int(resolved_pts)} pts"
        verified_ref = ref

    # ── Award points ──────────────────────────────────────────────────────────
    add_vgk_points_entry(
        db=db,
        partner_id=current_member.id,
        points_credit=points_to_award,
        points_debit=Decimal('0'),
        reason_code='CAMPAIGN_BONUS',
        reference_type='PROMO_CODE',
        reference_id=pc.id,
        notes=notes,
    )

    # ── Record redemption ─────────────────────────────────────────────────────
    redemption = VGKPromoRedemption(
        promo_code_id=pc.id,
        partner_id=current_member.id,
        verified_ref=verified_ref,
        points_awarded=points_to_award,
        notes=notes,
    )
    db.add(redemption)

    # ── Increment usage counter ───────────────────────────────────────────────
    pc.times_used = (pc.times_used or 0) + 1
    pc.updated_at = _dt.datetime.now(_pytz.timezone('Asia/Kolkata')).replace(tzinfo=None)

    db.commit()

    new_balance = float(current_member.vgk_points_balance or 0)
    return {
        "success": True,
        "message": f"🎉 {int(points_to_award):,} points credited to your account!",
        "points_awarded": float(points_to_award),
        "new_balance": new_balance,
    }


# ── VGK Lead Update (DC Protocol Apr 2026) ────────────────────────────────────
@router.put("/dashboard/leads/{lead_id}/update")
async def vgk_update_lead(
    lead_id: int,
    db: Session = Depends(get_db),
    current_member: OfficialPartner = Depends(get_current_vgk_member),
    status: Optional[str] = Body(None),
    next_followup_date: Optional[str] = Body(None),
    vgk_field_support_id: Optional[int] = Body(None),
    vgk_field_support_clear: bool = Body(False),
    guru_supported: Optional[bool] = Body(None),
    z_guru_supported: Optional[bool] = Body(None),
    adi_guru_supported: Optional[bool] = Body(None),
    telecaller_supported: Optional[bool] = Body(None),
    showroom_supported: Optional[bool] = Body(None),
    field_support_supported: Optional[bool] = Body(None),
):
    """
    VGK member lead update endpoint.
    Only the Source partner (associated_partner_id) may update their own lead.
    Allows: status, next_followup_date, vgk_field_support_id, support confirmations.
    """
    lead = db.query(CRMLead).filter(CRMLead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    if lead.associated_partner_id != current_member.id:
        raise HTTPException(status_code=403, detail="You can only edit leads you submitted as Source")

    _old_status = lead.status

    if status:
        lead.status = status

    if next_followup_date is not None:
        if next_followup_date:
            try:
                lead.next_followup_date = datetime.fromisoformat(next_followup_date)
            except Exception:
                pass
        else:
            lead.next_followup_date = None

    if vgk_field_support_clear:
        lead.vgk_field_support_id = None
    elif vgk_field_support_id is not None:
        support_partner = db.query(OfficialPartner).filter(OfficialPartner.id == vgk_field_support_id).first()
        if not support_partner:
            raise HTTPException(status_code=400, detail="VGK Field Support member not found")
        lead.vgk_field_support_id = vgk_field_support_id

    if guru_supported is not None:
        lead.guru_supported = guru_supported
    if z_guru_supported is not None:
        lead.z_guru_supported = z_guru_supported
    if adi_guru_supported is not None:
        lead.adi_guru_supported = adi_guru_supported
    if telecaller_supported is not None:
        lead.telecaller_supported = telecaller_supported
    if showroom_supported is not None:
        lead.showroom_supported = showroom_supported
    if field_support_supported is not None:
        lead.field_support_supported = field_support_supported

    lead.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(lead)

    # DC-VGK-DRAFT-TRIGGER-001 (May 2026): Generate commission DRAFTs when status
    # transitions to 'completed' — mirrors the same hook in the staff CRM endpoint.
    # Applies to all categories (Solar, EV B2C, EV B2B, etc.) with a commission config.
    if status == 'completed' and _old_status != 'completed':
        try:
            from app.services.vgk_cash_income import generate_vgk_cash_income_drafts
            _drafted = generate_vgk_cash_income_drafts(db, lead)
            if _drafted:
                db.commit()
                logger.info(f'[DC-VGK-DRAFT-TRIGGER-001] Lead#{lead_id}: {_drafted} DRAFT(s) created on VGK member status → completed')
        except Exception as _draft_e:
            logger.warning(f'[DC-VGK-DRAFT-TRIGGER-001] Lead#{lead_id}: draft generation failed (non-fatal): {_draft_e}')

    return {"success": True, "message": "Lead updated successfully", "lead_id": lead_id}


# ── DC_CIBIL_ADVANCE_001: VGK Member — Solar CIBIL Advances ─────────────────

@router.get("/dashboard/solar-advances")
def member_solar_advances(
    current_member: OfficialPartner = Depends(get_current_vgk_member),
    db: Session = Depends(get_db),
):
    """
    VGK member: view all Solar CIBIL advances for their referred leads.
    Shows PENDING, RELEASED, ADJUSTED, RECOVERED, DEFICIT entries.
    """
    from sqlalchemy import text as _t
    rows = db.execute(_t("""
        SELECT a.id, a.entry_number, a.advance_amount, a.status,
               a.stage_at_eligibility, a.cibil_score_at_check,
               a.released_at, a.recovery_amount, a.recovery_reason, a.recovered_at,
               a.adjustment_amount, a.adjusted_at,
               a.created_at, a.lead_id,
               a.slab_bonus_paid, a.slab_bonus_amount,
               l.name AS lead_name, l.solar_pipeline_status,
               l.cibil_confirmed, l.cibil_score
        FROM vgk_solar_cibil_advances a
        LEFT JOIN crm_leads l ON l.id = a.lead_id
        WHERE a.partner_id = :pid
        ORDER BY a.created_at DESC
    """), {'pid': current_member.id}).fetchall()

    advances = []
    for r in rows:
        net = float(r.advance_amount or 0)
        if r.status == 'RECOVERED':
            net = -float(r.recovery_amount or 0)
        elif r.status == 'DEFICIT':
            net = -float(r.recovery_amount or 0)
        elif r.status == 'ADJUSTED':
            net = 0.0

        _slab_paid   = bool(r.slab_bonus_paid) if r.slab_bonus_paid else False
        _slab_amt    = float(r.slab_bonus_amount) if r.slab_bonus_amount else 0.0
        _adv_amt     = float(r.advance_amount or 0)
        advances.append({
            'id': r.id,
            'entry_number': r.entry_number,
            'lead_id': r.lead_id,
            'lead_name': r.lead_name or f'Lead #{r.lead_id}',
            'solar_pipeline_status': r.solar_pipeline_status,
            'advance_amount': _adv_amt,
            'status': r.status,
            'stage_at_eligibility': r.stage_at_eligibility,
            'cibil_score_at_check': r.cibil_score_at_check,
            'released_at': r.released_at.isoformat() if r.released_at else None,
            'recovery_amount': float(r.recovery_amount or 0),
            'recovery_reason': r.recovery_reason,
            'recovered_at': r.recovered_at.isoformat() if r.recovered_at else None,
            'adjustment_amount': float(r.adjustment_amount or 0),
            'adjusted_at': r.adjusted_at.isoformat() if r.adjusted_at else None,
            'created_at': r.created_at.isoformat() if r.created_at else None,
            'lead_cibil_confirmed': r.cibil_confirmed,
            'lead_cibil_score': r.cibil_score,
            'net_effect': net,
            # DC_BONANZA_SLABWISE_AUTO_001
            'slab_bonus_paid':   _slab_paid,
            'slab_bonus_amount': _slab_amt,
            'total_payout':      _adv_amt + (_slab_amt if _slab_paid else 0.0),
        })

    total_released = sum(float(a['advance_amount']) for a in advances if a['status'] in ('RELEASED', 'ADJUSTED'))
    total_adjusted = sum(float(a['adjustment_amount']) for a in advances if a['status'] == 'ADJUSTED')
    total_recovered = sum(float(a['recovery_amount']) for a in advances if a['status'] in ('RECOVERED', 'DEFICIT'))
    deficit_pending = sum(
        float(a['advance_amount']) - float(a['recovery_amount'])
        for a in advances if a['status'] == 'DEFICIT'
    )
    # DC-VGK-PARTNER-SYNC-001: gross "earned" = ₹1,000 × every advance
    # regardless of status (PENDING + RELEASED + ADJUSTED + RECOVERED + DEFICIT).
    total_earned_gross = sum(float(a['advance_amount']) for a in advances)

    return {
        'advances': advances,
        'summary': {
            'total': len(advances),
            'total_earned_gross': total_earned_gross,
            'total_released': total_released,
            'total_adjusted': total_adjusted,
            'total_recovered': total_recovered,
            'deficit_pending': deficit_pending,
        }
    }


# ════════════════════════════════════════════════════════════════════════════
# DC_CP_CARD_001 — Channel Partner Designation & Card System (Apr 2026)
# ════════════════════════════════════════════════════════════════════════════

_CP_TIER_LABELS = {
    'none':               '—',
    'channel_partner':    'Channel Partner',
    'sr_channel_partner': 'Sr. Channel Partner',
    'official_partner':   'Lead Channel Partner',
}

_CP_TIER_ORDER = ['none', 'channel_partner', 'sr_channel_partner', 'official_partner']


def _compute_cp_designation(partner, db) -> dict:
    """DC_CP_CARD_001: Compute CP designation tier from coupon activations + people activated.
    Source-only (direct), tiers only move up, never down.
    Thresholds:
      Channel Partner:      manually_activated OR is_paid_activation OR coupons_used >= 100 (₹5 L) OR activated_people >= 10
      Sr. Channel Partner:  coupons_used >= 300 OR activated_people >= 15  (₹15 L)
      Lead Channel Partner: coupons_used >= 600 OR activated_people >= 30  (₹30 L)
    """
    pid = partner.id

    coupon_row = db.execute(sa_text(
        "SELECT COALESCE(SUM(quantity), 0) FROM vgk_coupon_ledger "
        "WHERE partner_id = :pid AND transaction_type = 'activation_used'"
    ), {"pid": pid}).fetchone()
    coupons_used = int(coupon_row[0]) if coupon_row else 0

    act_row = db.execute(sa_text(
        "SELECT COUNT(*) FROM vgk_member_activation_requests "
        "WHERE requesting_partner_id = :pid AND status = 'APPROVED'"
    ), {"pid": pid}).fetchone()
    activated_people = int(act_row[0]) if act_row else 0

    revenue = coupons_used * 5000
    # DC-VCARD-FIX-001 (Apr 24 2026): treat vcard_enabled (staff "Show Visiting Card" toggle)
    # as equivalent to card_manually_activated — both gates should unlock the card.
    manually = (bool(getattr(partner, 'card_manually_activated', False))
                or bool(getattr(partner, 'vcard_enabled', False)))
    # DC-CP-TIER-001 (Apr 25 2026): member who paid ₹5,000 and got activated qualifies for Channel Partner.
    paid_activated = bool(getattr(partner, 'is_paid_activation', False))

    # Resolve tier (highest threshold wins)
    tier = 'none'
    if coupons_used >= 600 or activated_people >= 30:
        tier = 'official_partner'
    elif coupons_used >= 300 or activated_people >= 15:
        tier = 'sr_channel_partner'
    elif manually or paid_activated or coupons_used >= 100 or activated_people >= 10:
        tier = 'channel_partner'

    return {
        "tier":               tier,
        "tier_label":         _CP_TIER_LABELS.get(tier, '—'),
        "manually_activated": manually,
        "coupons_used":       coupons_used,
        "activated_people":   activated_people,
        "revenue":            revenue,
        "is_card_visible":    tier != 'none',
        "progress": {
            "channel_partner": {
                "label":           "Channel Partner",
                "coupons_needed":  100,
                "coupons_done":    min(coupons_used, 100),
                "revenue_needed":  500000,
                "revenue_done":    min(revenue, 500000),
                "people_needed":   10,
                "people_done":     min(activated_people, 10),
                "unlocked":        tier in ('channel_partner', 'sr_channel_partner', 'official_partner') or manually or paid_activated,
            },
            "sr_channel_partner": {
                "label":           "Sr. Channel Partner",
                "coupons_needed":  300,
                "coupons_done":    min(coupons_used, 300),
                "revenue_needed":  1500000,
                "revenue_done":    min(revenue, 1500000),
                "people_needed":   15,
                "people_done":     min(activated_people, 15),
                "unlocked":        tier in ('sr_channel_partner', 'official_partner'),
            },
            "official_partner": {
                "label":           "Lead Channel Partner",
                "coupons_needed":  600,
                "coupons_done":    min(coupons_used, 600),
                "revenue_needed":  3000000,
                "revenue_done":    min(revenue, 3000000),
                "people_needed":   30,
                "people_done":     min(activated_people, 30),
                "unlocked":        tier == 'official_partner',
            },
        },
    }


@router.get("/designation/progress")
def vgk_designation_progress(
    current_member: OfficialPartner = Depends(get_current_vgk_member),
    db: Session = Depends(get_db)
):
    """DC_CP_CARD_001: Return CP designation tier, progress toward next tier, and visiting card data."""
    desig = _compute_cp_designation(current_member, db)

    host = "https://www.vgk4u.com"
    referral_url = f"{host}/vgk/login?tab=signup&ref={current_member.partner_code}"
    # [DC-PERF-001] Use cached QR — generate only once per partner per process lifetime
    qr_b64 = _qr_b64_cache.get(current_member.partner_code, '')
    if not qr_b64:
        try:
            import qrcode, io, base64 as _b64
            qr = qrcode.QRCode(version=2, box_size=12, border=3,
                               error_correction=qrcode.constants.ERROR_CORRECT_M)
            qr.add_data(referral_url)
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")
            buf = io.BytesIO()
            img.save(buf, format='PNG')
            qr_b64 = "data:image/png;base64," + _b64.b64encode(buf.getvalue()).decode()
            _qr_b64_cache[current_member.partner_code] = qr_b64
        except Exception as _qe:
            logger.warning(f"[DC-CP-CARD] QR generation failed: {_qe}")

    safe_get = lambda attr: (getattr(current_member, attr, None) or '')
    name_title = safe_get('name_title')
    first_name  = safe_get('first_name')
    last_name   = safe_get('last_name')
    city        = safe_get('city')
    display_name = current_member.partner_name or ''
    if first_name and last_name:
        display_name = ' '.join(p for p in [name_title, first_name, last_name] if p)
    elif name_title and display_name and not display_name.startswith(name_title):
        display_name = f"{name_title} {display_name}"

    # [DC-PASSPORT-PHOTO] Include approved passport photo so ID card renders photo automatically
    passport_photo_url = ''
    try:
        pp_doc = db.query(KYCDocument).filter(
            KYCDocument.partner_id == current_member.id,
            KYCDocument.document_type == 'passport_photo',
            KYCDocument.status == 'Approved'
        ).first()
        if pp_doc and pp_doc.file_path:
            passport_photo_url = f'/storage/{pp_doc.file_path}'
    except Exception:
        pass

    safe_get2 = lambda attr: (getattr(current_member, attr, None) or '')
    desig["card_data"] = {
        "partner_code":       current_member.partner_code,
        "display_name":       display_name,
        "name_title":         safe_get('name_title'),
        "phone":              current_member.phone or '',
        "company_phone":      "+91 858585 2738",
        "city":               city,
        "referral_url":       referral_url,
        "qr_b64":             qr_b64,
        "blood_group":        safe_get2('blood_group'),
        "designation_label":  desig["tier_label"],
        "passport_photo_url": passport_photo_url,
    }
    desig["idcard_enabled"] = bool(getattr(current_member, 'idcard_enabled', False))
    desig["vcard_enabled"]  = bool(getattr(current_member, 'vcard_enabled',  False))
    return {"success": True, **desig}


@router.post("/staff/designation/activate/{member_id}")
def staff_activate_cp_card(
    member_id: int,
    db: Session = Depends(get_db),
    request: Request = None,
):
    """DC_CP_CARD_001: Staff manually activates a CP's card (sets card_manually_activated=TRUE).
    Grants minimum Channel Partner tier if currently none."""
    from app.api.v1.endpoints.staff_auth import get_current_staff_user
    from app.models.staff import StaffEmployee
    try:
        current_user: StaffEmployee = get_current_staff_user(request, db)
    except Exception:
        raise HTTPException(status_code=401, detail="Staff authentication required")

    member = db.query(OfficialPartner).filter(
        OfficialPartner.id == member_id,
        OfficialPartner.category == 'VGK_TEAM'
    ).first()
    if not member:
        raise HTTPException(status_code=404, detail="Channel Partner not found")

    try:
        db.execute(sa_text(
            "UPDATE official_partners SET card_manually_activated = TRUE WHERE id = :pid"
        ), {"pid": member_id})
        db.commit()
        db.refresh(member)
        desig = _compute_cp_designation(member, db)
        logger.info(f"[DC-CP-CARD] Staff {current_user.id} activated card for CP {member_id}")
        return {"success": True, "message": "Card activated successfully", "designation": desig}
    except Exception as e:
        db.rollback()
        logger.error(f"[DC-CP-CARD] Activate card failed for {member_id}: {e}")
        raise HTTPException(status_code=500, detail="Activation failed")
