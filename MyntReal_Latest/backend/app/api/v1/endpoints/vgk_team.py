"""
VGK Team Partner Module API Endpoints (DC Protocol Mar 2026)
4-level commission system (level-wise, unlimited referrals per member).
L1=self, L2=upline of L1, L3=upline of L2, L4=field support per lead.
Staff-facing: member management, commission config, income management.
"""

import logging
from fastapi import APIRouter, Body, Depends, HTTPException, Query, Path, Request
from sqlalchemy.orm import Session
from sqlalchemy import func, or_, and_, text
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field
from decimal import Decimal

logger = logging.getLogger(__name__)

from app.core.database import get_db
from app.models.staff_accounts import OfficialPartner, VGKTeamCommissionConfig, VGKTeamIncomeEntry, VGKPINPurchaseRequest, VGKPointsLedger, VGKUplineChangeLog
from app.models.signup_category import SignupCategory
from app.api.v1.endpoints.staff_auth import get_current_staff_user
from app.models.staff import StaffEmployee

router = APIRouter()


def get_indian_time():
    from pytz import timezone
    return datetime.now(timezone('Asia/Kolkata'))


def _get_staff_company_id(current_user) -> int:
    """Extract company_id from StaffEmployee (uses base_company_id)."""
    cid = getattr(current_user, 'base_company_id', None)
    if not cid:
        cid = getattr(current_user, 'company_id', None)
    return int(cid) if cid else 4


def require_vgk_admin(current_user: StaffEmployee = Depends(get_current_staff_user)):
    st = (current_user.staff_type or '').upper()
    if 'VGK' not in st and st != 'EA':
        raise HTTPException(status_code=403, detail="VGK Admin access required (EA or VGK Mentor only)")
    return current_user


def require_ea(current_user: StaffEmployee = Depends(get_current_staff_user)):
    st = (current_user.staff_type or '').upper()
    if st != 'EA':
        raise HTTPException(status_code=403, detail="EA access required")
    return current_user


def _next_vgk_partner_code(db: Session, company_id: int) -> str:
    import random as _rnd
    for _ in range(50):
        rand4 = _rnd.randint(1000, 9999)
        code = f"VGK0710{rand4}"
        exists = db.query(OfficialPartner).filter(OfficialPartner.partner_code == code).first()
        if not exists:
            return code
    raise ValueError("Could not generate unique VGK partner code")


def _next_vgk_entry_number(db: Session, company_id: int, prefix: str = None) -> str:
    from pytz import timezone
    now = datetime.now(timezone('Asia/Kolkata'))
    yymm = now.strftime('%y%m')
    tag = prefix or 'VGK'
    like_pat = f"{tag}-{yymm}-%"
    result = db.execute(text(
        "SELECT COUNT(*) FROM vgk_team_income_entries "
        "WHERE entry_number LIKE :prefix"
    ), {"prefix": like_pat}).scalar()
    seq = (result or 0) + 1
    return f"{tag}-{yymm}-{seq:04d}"


def _collect_tree_codes(partner: OfficialPartner, db: Session, depth: int) -> list:
    """Collect all partner_codes in the downline tree for batch CRM queries (DC-VGK-TREE-BATCH-001)."""
    codes = [partner.partner_code]
    if depth <= 0:
        return codes
    children = db.query(OfficialPartner).filter(
        OfficialPartner.parent_partner_id == partner.id,
        OfficialPartner.category == 'VGK_TEAM'
    ).all()
    for c in children:
        codes.extend(_collect_tree_codes(c, db, depth - 1))
    return codes


def _build_tree_node(partner: OfficialPartner, db: Session, depth: int, direction: str, lead_counts: dict = None) -> dict:
    # [DC-VGK-TREE-BATCH-001] Use pre-fetched batch counts when available to avoid N+1 CRM queries
    if lead_counts is not None:
        lead_total = lead_counts.get(partner.partner_code, 0)
        leads_by_status = {}
    else:
        # Legacy per-node query path (wrapped in try/except for production resilience)
        try:
            from app.models.crm import CRMLeadDeal
            lead_total = db.query(func.count(CRMLeadDeal.id)).filter(
                or_(
                    CRMLeadDeal.deal_source_id == partner.partner_code,
                    CRMLeadDeal.deal_referrer_id == partner.partner_code,
                    CRMLeadDeal.deal_field_support_id == partner.partner_code,
                )
            ).scalar() or 0
        except Exception:
            lead_total = 0
        try:
            from app.models.crm import CRMLeadDeal, CRMLead
            status_rows = db.query(CRMLead.status, func.count(CRMLead.id)).join(
                CRMLeadDeal, CRMLeadDeal.lead_id == CRMLead.id
            ).filter(
                or_(
                    CRMLeadDeal.deal_source_id == partner.partner_code,
                    CRMLeadDeal.deal_referrer_id == partner.partner_code,
                    CRMLeadDeal.deal_field_support_id == partner.partner_code,
                )
            ).group_by(CRMLead.status).all()
            leads_by_status = {row[0]: row[1] for row in status_rows}
        except Exception:
            leads_by_status = {}

    node = {
        "id": partner.id,
        "partner_code": partner.partner_code,
        "partner_name": partner.partner_name,
        "phone": partner.phone,
        "is_active": partner.is_active,
        "vgk_role": partner.vgk_role,
        "vgk_points_balance": float(partner.vgk_points_balance or 0),
        "created_at": partner.created_at.isoformat() if partner.created_at else None,
        "vgk_activated_at": partner.vgk_activated_at.isoformat() if partner.vgk_activated_at else None,
        "leads_total": lead_total,
        "leads_by_status": leads_by_status,
        "direct_count": 0,
        "children": []
    }
    if depth <= 0:
        return node
    if direction == "down":
        children = db.query(OfficialPartner).filter(
            OfficialPartner.parent_partner_id == partner.id,
            OfficialPartner.category == 'VGK_TEAM'
        ).order_by(OfficialPartner.id).all()
        node["direct_count"] = len(children)
        node["children"] = [_build_tree_node(c, db, depth - 1, "down", lead_counts) for c in children]
    return node


# ─── Member Endpoints ────────────────────────────────────────────────────────

class VGKMemberCreate(BaseModel):
    partner_name: Optional[str] = None   # display name — auto-built from title+first+last if omitted
    # [DC-PHONE-LEN-001] max_length=30 matches widened VARCHAR(30) on official_partners.phone
    phone: str = Field(..., min_length=10, max_length=30)
    email: Optional[str] = None
    parent_partner_id: Optional[int] = None
    password: Optional[str] = None
    vgk_role: Optional[str] = "VGK_ASSOCIATE"
    # [DC-NAME-GENDER] Apr 2026 split name fields
    name_title: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    gender: Optional[str] = None
    # [DC-PHONE-OTP-001] Phone verification token — required unless bypass applies
    phone_verified_token: Optional[str] = None
    # [DC-VGK-STAFF-REG-001] Registering staff emp code — auto-filled from current_user if omitted
    registered_by_emp_code: Optional[str] = None


class VGKMemberUpdate(BaseModel):
    partner_name: Optional[str] = None
    # [DC-PHONE-LEN-001] max_length=30 matches widened VARCHAR(30) on official_partners.phone
    phone: Optional[str] = Field(None, max_length=30)
    email: Optional[str] = None
    parent_partner_id: Optional[int] = None
    vgk_role: Optional[str] = None
    is_active: Optional[bool] = None
    is_card_admin:  Optional[bool] = None   # [DC_VGK_CARD_ADMIN_001]
    vcard_enabled:  Optional[bool] = None   # [DC_VGK_CARD_ENABLED_001]
    idcard_enabled: Optional[bool] = None   # [DC_VGK_CARD_ENABLED_001]
    # [DC-VGK-STAFF-REG-001] Admin-editable: which staff emp registered this member
    registered_by_emp_code: Optional[str] = None


@router.get("/members/search")
def search_vgk_members(
    q: str = Query("", description="Name, phone or partner code search"),
    active_only: bool = Query(True, description="True = active members only (default). False = include inactive."),
    db: Session = Depends(get_db)
):
    """Search VGK members — used by CRM dropdowns (active_only=True default) and upline change (active_only=False)."""
    query = db.query(OfficialPartner).filter(OfficialPartner.category == 'VGK_TEAM')
    if active_only:
        query = query.filter(OfficialPartner.is_active == True)
    if q.strip():
        term = f"%{q.strip()}%"
        query = query.filter(or_(
            OfficialPartner.partner_name.ilike(term),
            OfficialPartner.phone.ilike(term),
            OfficialPartner.partner_code.ilike(term)
        ))
    members = query.order_by(OfficialPartner.partner_name).limit(30).all()
    return {
        "success": True,
        "data": [
            {
                "id": m.id,
                "partner_name": m.partner_name,
                "phone": m.phone,
                "partner_code": m.partner_code,
                "is_active": m.is_active,
            }
            for m in members
        ]
    }


@router.get("/members")
def list_vgk_members(
    is_active: Optional[bool] = Query(None),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=5, le=100),
    reg_period: Optional[str] = Query(None, description="today|yesterday|week|mtd"),
    reg_from: Optional[str] = Query(None, description="YYYY-MM-DD registered from"),
    reg_to: Optional[str] = Query(None, description="YYYY-MM-DD registered to"),
    sort_by: Optional[str] = Query(None, description="registered|last_login|login_count|name|code|downline_count|src_revenue|leads_total|leads_won|leads_lost|registered_by"),
    sort_dir: Optional[str] = Query("desc", description="asc|desc"),
    designation_tier: Optional[str] = Query(None, description="none|channel_partner|sr_channel_partner|official_partner"),
    # [DC-VGK-STAFF-REG-001] Filter by registering staff emp code
    registered_by_emp_code: Optional[str] = Query(None, description="Filter by registering staff emp code"),
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    from datetime import date, timedelta
    query = db.query(OfficialPartner).filter(OfficialPartner.category == 'VGK_TEAM')
    if is_active is not None:
        query = query.filter(OfficialPartner.is_active == is_active)
    if search:
        term = f"%{search.strip()}%"
        query = query.filter(or_(
            OfficialPartner.partner_name.ilike(term),
            OfficialPartner.phone.ilike(term),
            OfficialPartner.whatsapp_number.ilike(term),
            OfficialPartner.partner_code.ilike(term)
        ))
    # [DC-VGK-STAFF-REG-001] Filter by registering staff emp_code OR full_name
    if registered_by_emp_code:
        _rbq = registered_by_emp_code.strip()
        try:
            _matched = db.execute(text(
                "SELECT emp_code FROM staff_employees WHERE UPPER(emp_code) = :code OR full_name ILIKE :name"
            ), {"code": _rbq.upper(), "name": f"%{_rbq}%"}).fetchall()
            _matched_codes = [r[0] for r in _matched]
        except Exception:
            _matched_codes = [_rbq.upper()]
        if _matched_codes:
            query = query.filter(OfficialPartner.registered_by_emp_code.in_(_matched_codes))
        else:
            query = query.filter(OfficialPartner.registered_by_emp_code == _rbq.upper())
    # Date range filters on created_at (registration date)
    today = date.today()
    if reg_period:
        if reg_period == 'today':
            reg_from = reg_to = today.isoformat()
        elif reg_period == 'yesterday':
            yest = (today - timedelta(days=1)).isoformat()
            reg_from = reg_to = yest
        elif reg_period == 'week':
            reg_from = (today - timedelta(days=today.weekday())).isoformat()
            reg_to = today.isoformat()
        elif reg_period == 'mtd':
            reg_from = today.replace(day=1).isoformat()
            reg_to = today.isoformat()
    if reg_from:
        query = query.filter(OfficialPartner.created_at >= datetime.strptime(reg_from, '%Y-%m-%d'))
    if reg_to:
        query = query.filter(OfficialPartner.created_at <= datetime.strptime(reg_to + 'T23:59:59', '%Y-%m-%dT%H:%M:%S'))
    # DC_CP_CARD_001: computed fields that require full-dataset Python sort/filter
    _COMPUTED_SORT_FIELDS = {'downline_count', 'src_revenue', 'leads_total', 'leads_won', 'leads_lost'}
    _do_python_sort  = sort_by in _COMPUTED_SORT_FIELDS
    _needs_full_fetch = _do_python_sort or bool(designation_tier)

    # Sorting
    _sort_col = OfficialPartner.id
    if sort_by == 'registered':
        _sort_col = OfficialPartner.created_at
    elif sort_by == 'last_login':
        _sort_col = OfficialPartner.last_login
    elif sort_by == 'login_count':
        _sort_col = OfficialPartner.login_count
    elif sort_by == 'name':
        _sort_col = OfficialPartner.partner_name
    elif sort_by == 'code':
        _sort_col = OfficialPartner.partner_code
    elif sort_by == 'registered_by':   # [DC-VGK-STAFF-REG-001]
        _sort_col = OfficialPartner.registered_by_emp_code
    _order = _sort_col.asc() if sort_dir == 'asc' else _sort_col.desc()
    total = query.count()
    if _needs_full_fetch:
        members = query.order_by(_order).all()
    else:
        members = query.order_by(_order).offset((page - 1) * page_size).limit(page_size).all()

    # Bulk fetch income totals — vgk_cash_income_entries, RELEASED+PAID = confirmed/paid out
    member_ids = [m.id for m in members]
    income_rows = db.execute(text(
        "SELECT partner_id, SUM(commission_amount) "
        "FROM vgk_cash_income_entries WHERE partner_id = ANY(:ids) "
        "AND status IN ('RELEASED','PAID') AND status != 'CANCELLED' "
        "GROUP BY partner_id"
    ), {"ids": member_ids}).fetchall() if member_ids else []
    income_map = {row[0]: float(row[1]) for row in income_rows}

    VGK_INITIAL_POINTS = 60000

    # Bulk CRM source lookup by phone
    phone_list = list({(m.phone or m.whatsapp_number or '').strip() for m in members if (m.phone or m.whatsapp_number or '').strip()})
    crm_source_map = {}
    wa_count_map = {}
    if phone_list:
        try:
            crm_rows = db.execute(text(
                "SELECT DISTINCT ON (phone) phone, source FROM crm_leads "
                "WHERE phone = ANY(:phones) ORDER BY phone, id DESC"
            ), {"phones": phone_list}).fetchall()
            for row in crm_rows:
                if row[0]:
                    crm_source_map[row[0]] = row[1] or 'crm'
        except Exception:
            pass
        try:
            wa_rows = db.execute(text(
                "SELECT phone, COUNT(*) FROM whatsapp_campaign_logs "
                "WHERE phone = ANY(:phones) AND status NOT IN ('failed','skipped','queued') "
                "GROUP BY phone"
            ), {"phones": phone_list}).fetchall()
            for row in wa_rows:
                if row[0]:
                    wa_count_map[row[0]] = int(row[1])
        except Exception:
            pass

    # Bulk fetch actual points debited per member from vgk_points_ledger
    pts_debit_map: dict = {}
    if member_ids:
        try:
            pd_rows = db.execute(text(
                "SELECT partner_id, COALESCE(SUM(points_debit),0) FROM vgk_points_ledger "
                "WHERE partner_id = ANY(:ids) "
                "GROUP BY partner_id"
            ), {"ids": member_ids}).fetchall()
            pts_debit_map = {int(r[0]): float(r[1]) for r in pd_rows}
        except Exception:
            pass

    # DC_CP_CARD_001: Bulk fetch coupon usage + activation counts for designation computation
    _CP_TIER_LABELS = {
        'none':               '—',
        'channel_partner':    'Channel Partner',
        'sr_channel_partner': 'Sr. Channel Partner',
        'official_partner':   'Official Partner',
    }
    coupon_map: dict = {}
    activ_map: dict = {}
    if member_ids:
        try:
            c_rows = db.execute(text(
                "SELECT partner_id, COALESCE(SUM(quantity),0) FROM vgk_coupon_ledger "
                "WHERE partner_id = ANY(:ids) AND transaction_type = 'activation_used' "
                "GROUP BY partner_id"
            ), {"ids": member_ids}).fetchall()
            coupon_map = {int(r[0]): int(r[1]) for r in c_rows}
        except Exception:
            pass
        try:
            a_rows = db.execute(text(
                "SELECT requesting_partner_id, COUNT(*) FROM vgk_member_activation_requests "
                "WHERE requesting_partner_id = ANY(:ids) AND status = 'APPROVED' "
                "GROUP BY requesting_partner_id"
            ), {"ids": member_ids}).fetchall()
            activ_map = {int(r[0]): int(r[1]) for r in a_rows}
        except Exception:
            pass

    # DC_CP_CARD_001: Bulk CRM lead stats via associated_partner_id (authoritative link)
    # source_ref_type='partner' only back-filled from May 2026; older leads only have associated_partner_id
    lead_stats_map: dict = {}
    if member_ids:
        try:
            lead_rows = db.execute(text(
                "SELECT associated_partner_id, "
                "COUNT(*) AS total, "
                "COUNT(*) FILTER (WHERE status='won') AS won, "
                "COUNT(*) FILTER (WHERE status IN ('lost','cancelled')) AS lost_cancelled "
                "FROM crm_leads "
                "WHERE associated_partner_id = ANY(:member_ids) "
                "GROUP BY associated_partner_id"
            ), {"member_ids": member_ids}).fetchall()
            lead_stats_map = {str(r[0]): {"total": int(r[1]), "won": int(r[2]), "lost": int(r[3])} for r in lead_rows}
        except Exception:
            pass

    def _resolve_tier(m, coupons_used: int, activated_people: int) -> str:
        manually = bool(getattr(m, 'card_manually_activated', False))
        if coupons_used >= 600 or activated_people >= 30:
            return 'official_partner'
        elif coupons_used >= 300 or activated_people >= 15:
            return 'sr_channel_partner'
        elif manually or coupons_used >= 100:
            return 'channel_partner'
        return 'none'

    items = []
    for m in members:
        d = m.to_dict()
        if m.parent_partner_id:
            ref = db.query(OfficialPartner).filter(OfficialPartner.id == m.parent_partner_id).first()
            d['referrer_name'] = ref.partner_name if ref else None
            d['referrer_code'] = ref.partner_code if ref else None
        else:
            d['referrer_name'] = None
            d['referrer_code'] = None
        balance = float(m.vgk_points_balance or 0)
        d['points_utilised'] = pts_debit_map.get(m.id, 0.0)
        d['confirmed_income_total'] = income_map.get(m.id, 0.0)
        phone = (m.phone or m.whatsapp_number or '').strip()
        if phone in crm_source_map:
            d['registration_source'] = crm_source_map[phone]
        elif m.parent_partner_id:
            d['registration_source'] = 'Reference'
        else:
            d['registration_source'] = 'Signup'
        d['wa_message_count'] = wa_count_map.get(phone, 0)
        # DC_CP_CARD_001: attach designation + computed metrics
        c_used = coupon_map.get(m.id, 0)
        a_done = activ_map.get(m.id, 0)
        tier   = _resolve_tier(m, c_used, a_done)
        d['designation_tier']  = tier
        d['designation_label'] = _CP_TIER_LABELS.get(tier, '—')
        d['coupons_used']      = c_used
        d['activated_people']  = a_done
        d['src_revenue']       = c_used * 5000
        ls = lead_stats_map.get(str(m.id), {})
        d['leads_total']       = ls.get('total', 0)
        d['leads_won']         = ls.get('won', 0)
        d['leads_lost']        = ls.get('lost', 0)
        items.append(d)

    # DC_CP_CARD_001: designation filter (Python-side)
    if designation_tier:
        items = [i for i in items if i.get('designation_tier') == designation_tier]

    # DC_CP_CARD_001: Python-side sort for computed fields
    if _do_python_sort:
        _sort_key_map = {
            'downline_count': 'activated_people',
            'src_revenue':    'src_revenue',
            'leads_total':    'leads_total',
            'leads_won':      'leads_won',
            'leads_lost':     'leads_lost',
        }
        _sk = _sort_key_map.get(sort_by, sort_by)
        items.sort(key=lambda x: x.get(_sk, 0), reverse=(sort_dir == 'desc'))

    # Apply Python-side pagination when we fetched the full dataset
    if _needs_full_fetch:
        total = len(items)
        _start = (page - 1) * page_size
        items  = items[_start: _start + page_size]

    # [DC-VGK-STAFF-REG-001] Batch resolve registered_by_name from staff_employees
    _emp_codes = list({d.get('registered_by_emp_code') for d in items if d.get('registered_by_emp_code')})
    _emp_name_map: dict = {}
    if _emp_codes:
        try:
            _emp_rows = db.execute(text(
                "SELECT emp_code, full_name FROM staff_employees WHERE emp_code = ANY(:codes)"
            ), {"codes": _emp_codes}).fetchall()
            _emp_name_map = {r[0]: r[1] for r in _emp_rows}
        except Exception:
            pass
    for d in items:
        d['registered_by_name'] = _emp_name_map.get(d.get('registered_by_emp_code'), None)

    return {"success": True, "total": total, "page": page, "page_size": page_size, "data": items}


@router.post("/members/send-otp")
def staff_member_send_otp(
    payload: dict,
    current_user: StaffEmployee = Depends(require_vgk_admin),
    db: Session = Depends(get_db)
):
    """[DC-PHONE-OTP-001] Send WhatsApp OTP to a phone number for staff-initiated VGK member creation."""
    phone = (payload.get("phone") or "").strip()
    if not phone or len(phone) < 10 or not phone.isdigit():
        raise HTTPException(status_code=400, detail="Please provide a valid 10-digit mobile number.")
    existing = db.query(OfficialPartner).filter(
        OfficialPartner.phone == phone, OfficialPartner.category == 'VGK_TEAM'
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="This phone number is already registered as a VGK Channel Partner.")
    from app.utils.phone_otp import generate_and_send_otp
    return generate_and_send_otp(phone=phone, purpose='vgk_staff_add', db=db)


@router.post("/members/verify-otp")
def staff_member_verify_otp(
    payload: dict,
    current_user: StaffEmployee = Depends(require_vgk_admin),
    db: Session = Depends(get_db)
):
    """[DC-PHONE-OTP-001] Verify OTP and issue phone_verified_token for staff VGK member creation."""
    phone = (payload.get("phone") or "").strip()
    otp_code = (payload.get("otp_code") or "").strip()
    if not phone or not otp_code:
        raise HTTPException(status_code=400, detail="Phone and OTP code are required.")
    from app.utils.phone_otp import verify_otp_and_issue_token
    token = verify_otp_and_issue_token(phone=phone, otp_code=otp_code, purpose='vgk_staff_add', db=db)
    return {"success": True, "phone_verified_token": token, "message": "Phone verified successfully."}


@router.post("/members", status_code=201)
def create_vgk_member(
    payload: VGKMemberCreate,
    current_user: StaffEmployee = Depends(require_vgk_admin),
    db: Session = Depends(get_db)
):
    from app.utils.phone_otp import VGK_MENTOR_BYPASS_CODE
    company_id = _get_staff_company_id(current_user)
    phone = payload.phone.strip()

    existing = db.query(OfficialPartner).filter(
        OfficialPartner.phone == phone,
        OfficialPartner.category == 'VGK_TEAM'
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="VGK member with this phone already exists")

    # [DC-PHONE-OTP-001] OTP bypass rules:
    # 1. No referrer (default root will be used) → OTP bypassed
    # 2. Staff emp_code == MR10001 → OTP bypassed
    # 3. Otherwise → phone_verified_token required
    _otp_bypass = (
        not payload.parent_partner_id or
        (getattr(current_user, 'emp_code', '') or '').strip().upper() == VGK_MENTOR_BYPASS_CODE.upper()
    )
    if not _otp_bypass:
        if not payload.phone_verified_token:
            raise HTTPException(
                status_code=400,
                detail="Phone verification required. Please send an OTP to the member's WhatsApp and verify before creating."
            )
        from app.utils.phone_otp import validate_and_consume_token
        validate_and_consume_token(phone=phone, token=payload.phone_verified_token, purpose='vgk_staff_add', db=db)

    if payload.parent_partner_id:
        parent = db.query(OfficialPartner).filter(
            OfficialPartner.id == payload.parent_partner_id,
            OfficialPartner.category == 'VGK_TEAM'
        ).first()
        if not parent:
            raise HTTPException(status_code=400, detail="Upline (parent partner) not found or not a VGK member")

    partner_code = _next_vgk_partner_code(db, company_id)
    password_hash = None
    if payload.password:
        from app.core.security import SecurityManager
        password_hash = SecurityManager.get_password_hash(payload.password)

    # [DC-NAME-GENDER] Build display name from split fields if provided
    _fn = (payload.first_name or '').strip()
    _ln = (payload.last_name  or '').strip()
    _t  = (payload.name_title or '').strip()
    if _fn and _ln:
        _display_name = ' '.join(p for p in [_t, _fn, _ln] if p)
    else:
        _display_name = (payload.partner_name or '').strip() or f"{_fn} {_ln}".strip() or 'VGK Member'

    member = OfficialPartner(
        company_id=company_id,
        partner_code=partner_code,
        partner_name=_display_name,
        phone=phone,
        email=payload.email,
        category='VGK_TEAM',
        is_active=False,
        parent_partner_id=payload.parent_partner_id,
        vgk_role=payload.vgk_role or 'VGK_ASSOCIATE',
        vgk_points_balance=Decimal('0'),
        password_hash=password_hash,
        created_at=get_indian_time(),
        updated_at=get_indian_time()
    )
    # [DC-NAME-GENDER] Set split name fields if provided
    if _fn: member.first_name = _fn
    if _ln: member.last_name  = _ln
    if _t:  member.name_title = _t
    if payload.gender: member.gender = payload.gender.strip()
    # [DC-VGK-STAFF-REG-001] Auto-fill registering staff emp_code (payload overrides, else use current_user)
    _reg_emp = ((payload.registered_by_emp_code or '').strip().upper() or
                (getattr(current_user, 'emp_code', '') or '').strip().upper())
    if _reg_emp:
        member.registered_by_emp_code = _reg_emp
    db.add(member)
    db.commit()
    db.refresh(member)

    # DC Protocol Apr 2026: Credit 10,000 welcome bonus points on registration (non-paid status).
    # Full 50,000 activation bonus is credited separately when the member pays ₹4,999 PIN.
    try:
        from app.services.vgk_commission import add_vgk_points_entry
        add_vgk_points_entry(
            db=db,
            partner_id=member.id,
            points_credit=Decimal('10000'),
            points_debit=Decimal('0'),
            reason_code='WELCOME_BONUS',
            reference_type='registration',
            reference_id=None,
            notes='Welcome bonus on VGK registration — 10,000 VGK Discount Credits',
            created_by=current_user.id,
        )
        db.commit()
        db.refresh(member)
        logger.info(f"[VGK] 10,000 welcome bonus credited to {member.partner_code}")
    except Exception as _wb_err:
        logger.warning(f"[VGK] Welcome bonus credit failed (non-fatal): {_wb_err}")

    logger.info(f"[VGK] Created member {member.partner_code} (id={member.id}) by staff {current_user.emp_code}")

    # DC-VGK-WELCOME-WA: Fire WhatsApp welcome message trigger
    try:
        from app.services.whatsapp_auto_service import send_auto_whatsapp
        _wa_phone = (member.whatsapp_number or member.phone or "").strip()
        if _wa_phone:
            send_auto_whatsapp(
                db=db,
                event_key="vgk_member_created",
                phone=_wa_phone,
                context={
                    "1": member.partner_name or "Member",
                    "2": member.partner_code,
                    "3": "https://vgk4u.com/vgk/login",
                    "4": "10,000",
                },
            )
    except Exception as _wa_err:
        logger.warning(f"[VGK] Welcome WA send failed (non-fatal): {_wa_err}")

    return {"success": True, "message": "VGK member created. Activation pending via CRM flow.", "data": member.to_dict()}


@router.get("/members/bulk-wa-preview")
def bulk_send_preview(
    target_filter: str = Query(..., description="all_active | never_logged_in | inactive_3_days | inactive_7_days"),
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db),
):
    """DC-VGK-WA-SEND-001: Preview count of members matched by the target filter."""
    from datetime import timedelta
    company_id = _get_staff_company_id(current_user)
    base_q = db.query(OfficialPartner).filter(
        OfficialPartner.company_id == company_id,
        OfficialPartner.is_active == True,
        (OfficialPartner.phone != None) | (OfficialPartner.whatsapp_number != None),
    )
    if target_filter == "all_active":
        count = base_q.count()
    elif target_filter == "never_logged_in":
        count = base_q.filter(
            (OfficialPartner.login_count == 0) | (OfficialPartner.login_count == None)
        ).count()
    elif target_filter == "inactive_3_days":
        cutoff = datetime.utcnow() - timedelta(days=3)
        count = base_q.filter(
            (OfficialPartner.last_login == None) | (OfficialPartner.last_login < cutoff)
        ).count()
    elif target_filter == "inactive_7_days":
        cutoff = datetime.utcnow() - timedelta(days=7)
        count = base_q.filter(
            (OfficialPartner.last_login == None) | (OfficialPartner.last_login < cutoff)
        ).count()
    else:
        count = 0
    return {"success": True, "target_filter": target_filter, "count": count}


@router.get("/members/{member_id}")
def get_vgk_member(
    member_id: int = Path(...),
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    member = db.query(OfficialPartner).filter(
        OfficialPartner.id == member_id,
        OfficialPartner.category == 'VGK_TEAM'
    ).first()
    if not member:
        raise HTTPException(status_code=404, detail="VGK member not found")

    d = member.to_dict()
    if member.parent_partner_id:
        upline = db.query(OfficialPartner).filter(OfficialPartner.id == member.parent_partner_id).first()
        d['upline_name'] = upline.partner_name if upline else None
        d['upline_code'] = upline.partner_code if upline else None

    recent_income = db.query(VGKTeamIncomeEntry).filter(
        VGKTeamIncomeEntry.partner_id == member_id,
        VGKTeamIncomeEntry.status != 'CANCELLED'
    ).order_by(VGKTeamIncomeEntry.id.desc()).limit(10).all()
    d['recent_income'] = [e.to_dict() for e in recent_income]
    d['pending_income_total'] = float(sum(e.commission_amount + (e.bonus_amount or 0) for e in recent_income if e.status == 'PENDING' and not (e.notes or '').startswith('DEBIT:')))
    d['confirmed_income_total'] = float(sum(e.commission_amount + (e.bonus_amount or 0) for e in recent_income if e.status == 'CONFIRMED' and not (e.notes or '').startswith('DEBIT:')))

    # WA message count for this member
    try:
        phone = (member.phone or member.whatsapp_number or '').strip()
        if phone:
            wa_row = db.execute(text(
                "SELECT COUNT(*) FROM whatsapp_campaign_logs "
                "WHERE phone = :ph AND status NOT IN ('failed','skipped','queued')"
            ), {"ph": phone}).scalar()
            d['wa_message_count'] = int(wa_row or 0)
        else:
            d['wa_message_count'] = 0
    except Exception:
        d['wa_message_count'] = 0

    # Registration source
    try:
        phone = (member.phone or member.whatsapp_number or '').strip()
        if phone:
            crm_src = db.execute(text(
                "SELECT source FROM crm_leads WHERE phone = :ph OR alternate_phone = :ph ORDER BY id DESC LIMIT 1"
            ), {"ph": phone}).scalar()
            if crm_src:
                d['registration_source'] = crm_src
            elif member.parent_partner_id:
                d['registration_source'] = 'Reference'
            else:
                d['registration_source'] = 'Signup'
        elif member.parent_partner_id:
            d['registration_source'] = 'Reference'
        else:
            d['registration_source'] = 'Signup'
    except Exception:
        d['registration_source'] = None

    # DC-VGK-CRM-LINK-001: Phone-based CRM registration lookup (no schema change needed)
    d['crm_registration'] = None
    try:
        lookup_phone = (member.phone or member.whatsapp_number or '').strip()
        if lookup_phone:
            from sqlalchemy import text as _t
            crm_row = db.execute(_t("""
                SELECT id, name, phone, alternate_phone, email, status, source,
                       source_details, city, state, created_at
                FROM crm_leads
                WHERE phone = :ph OR alternate_phone = :ph
                ORDER BY id DESC LIMIT 1
            """), {"ph": lookup_phone}).fetchone()
            if crm_row:
                d['crm_registration'] = {
                    "lead_id":      crm_row[0],
                    "name":         crm_row[1],
                    "phone":        crm_row[2],
                    "alt_phone":    crm_row[3],
                    "email":        crm_row[4],
                    "status":       crm_row[5],
                    "source":       crm_row[6],
                    "source_details": crm_row[7],
                    "city":         crm_row[8],
                    "state":        crm_row[9],
                    "created_at":   str(crm_row[10]) if crm_row[10] else None,
                }
    except Exception as _crm_err:
        logger.warning(f"[DC-VGK-CRM-LINK-001] CRM lookup failed (non-fatal): {_crm_err}")

    # DC-VGK-STAFF-REG-001: resolve registered_by staff name for side panel display
    try:
        emp_code = member.registered_by_emp_code
        if emp_code:
            reg_staff = db.query(StaffEmployee).filter(
                StaffEmployee.emp_code == emp_code
            ).first()
            d['registered_by_name'] = reg_staff.full_name if reg_staff else None
        else:
            d['registered_by_name'] = None
    except Exception:
        d['registered_by_name'] = None

    return {"success": True, "data": d}


@router.patch("/members/{member_id}")
def update_vgk_member(
    member_id: int = Path(...),
    payload: VGKMemberUpdate = None,
    current_user: StaffEmployee = Depends(require_vgk_admin),
    db: Session = Depends(get_db)
):
    member = db.query(OfficialPartner).filter(
        OfficialPartner.id == member_id,
        OfficialPartner.category == 'VGK_TEAM'
    ).first()
    if not member:
        raise HTTPException(status_code=404, detail="VGK member not found")

    if payload.partner_name is not None:
        member.partner_name = payload.partner_name
    if payload.phone is not None:
        member.phone = payload.phone.strip()  # [DC-PHONE-LEN-001] always strip whitespace
    if payload.email is not None:
        member.email = payload.email
    if payload.vgk_role is not None:
        member.vgk_role = payload.vgk_role
    if payload.is_active is not None:
        member.is_active = payload.is_active
    if payload.is_card_admin is not None:   # [DC_VGK_CARD_ADMIN_001]
        member.is_card_admin = payload.is_card_admin
    if payload.vcard_enabled is not None:   # [DC_VGK_CARD_ENABLED_001]
        member.vcard_enabled = payload.vcard_enabled
    if payload.idcard_enabled is not None:  # [DC_VGK_CARD_ENABLED_001]
        member.idcard_enabled = payload.idcard_enabled
    # [DC-VGK-STAFF-REG-001] Admin-editable: update registering staff emp_code
    if payload.registered_by_emp_code is not None:
        _new_reg = payload.registered_by_emp_code.strip().upper()
        member.registered_by_emp_code = _new_reg if _new_reg else None
    if payload.parent_partner_id is not None:
        if payload.parent_partner_id == 0:
            member.parent_partner_id = None
        else:
            parent = db.query(OfficialPartner).filter(
                OfficialPartner.id == payload.parent_partner_id,
                OfficialPartner.category == 'VGK_TEAM'
            ).first()
            if not parent:
                raise HTTPException(status_code=400, detail="Upline not found or not a VGK member")
            member.parent_partner_id = payload.parent_partner_id
    member.updated_at = get_indian_time()
    db.commit()
    db.refresh(member)
    return {"success": True, "message": "Member updated", "data": member.to_dict()}


@router.get("/members/{member_id}/tree")
def get_vgk_member_tree(
    member_id: int = Path(...),
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    member = db.query(OfficialPartner).filter(
        OfficialPartner.id == member_id,
        OfficialPartner.category == 'VGK_TEAM'
    ).first()
    if not member:
        raise HTTPException(status_code=404, detail="VGK member not found")

    upline = []
    current = member
    for _ in range(3):
        if not current.parent_partner_id:
            break
        parent = db.query(OfficialPartner).filter(OfficialPartner.id == current.parent_partner_id).first()
        if not parent:
            break
        upline.append({"id": parent.id, "partner_code": parent.partner_code, "partner_name": parent.partner_name, "is_active": parent.is_active})
        current = parent

    # [DC-VGK-TREE-BATCH-001] Batch-fetch CRM lead counts for entire tree in 3 queries
    # instead of 2 queries per node (eliminates N+1, fixes production timeout on Neon)
    lead_counts: dict = {}
    try:
        all_codes = list(set(_collect_tree_codes(member, db, depth=3)))
        if all_codes:
            from app.models.crm import CRMLeadDeal
            src_rows = db.query(CRMLeadDeal.deal_source_id, func.count(CRMLeadDeal.id)).filter(
                CRMLeadDeal.deal_source_id.in_(all_codes)
            ).group_by(CRMLeadDeal.deal_source_id).all()
            ref_rows = db.query(CRMLeadDeal.deal_referrer_id, func.count(CRMLeadDeal.id)).filter(
                CRMLeadDeal.deal_referrer_id.in_(all_codes),
                CRMLeadDeal.deal_referrer_id.isnot(None)
            ).group_by(CRMLeadDeal.deal_referrer_id).all()
            fs_rows = db.query(CRMLeadDeal.deal_field_support_id, func.count(CRMLeadDeal.id)).filter(
                CRMLeadDeal.deal_field_support_id.in_(all_codes),
                CRMLeadDeal.deal_field_support_id.isnot(None)
            ).group_by(CRMLeadDeal.deal_field_support_id).all()
            for code, cnt in list(src_rows) + list(ref_rows) + list(fs_rows):
                if code:
                    lead_counts[code] = lead_counts.get(code, 0) + cnt
    except Exception:
        lead_counts = {}  # CRM unavailable — tree still renders without lead counts

    downline = _build_tree_node(member, db, depth=3, direction="down", lead_counts=lead_counts)

    return {"success": True, "data": {"member": member.to_dict(), "upline": upline, "downline": downline}}


# ---------------------------------------------------------------------------
# Upline Change — Impact Preview
# ---------------------------------------------------------------------------

@router.get("/members/{member_id}/upline-impact")
def get_upline_impact(
    member_id: int = Path(...),
    current_user: StaffEmployee = Depends(require_vgk_admin),
    db: Session = Depends(get_db)
):
    """
    Preview the impact of a future upline change.
    Returns: current upline chain, count of PENDING income entries
    where the current upline is credited at L2 or L3.
    """
    member = db.query(OfficialPartner).filter(
        OfficialPartner.id == member_id,
        OfficialPartner.category == 'VGK_TEAM'
    ).first()
    if not member:
        raise HTTPException(status_code=404, detail="VGK member not found")

    # Build upline chain (up to 3 levels)
    upline_chain = []
    current = member
    for _ in range(3):
        if not current.parent_partner_id:
            break
        parent = db.query(OfficialPartner).filter(OfficialPartner.id == current.parent_partner_id).first()
        if not parent:
            break
        upline_chain.append({
            "id": parent.id,
            "partner_code": parent.partner_code,
            "partner_name": parent.partner_name,
            "is_active": parent.is_active,
        })
        current = parent

    # Count PENDING income entries where immediate upline is credited at L2/L3
    pending_affected = 0
    if member.parent_partner_id:
        pending_affected = db.query(VGKTeamIncomeEntry).filter(
            VGKTeamIncomeEntry.partner_id == member.parent_partner_id,
            VGKTeamIncomeEntry.status == 'PENDING',
            VGKTeamIncomeEntry.level.in_([2, 3]),
        ).count()

    # History of past upline changes for this member
    history = db.query(VGKUplineChangeLog).filter(
        VGKUplineChangeLog.member_id == member_id
    ).order_by(VGKUplineChangeLog.created_at.desc()).limit(20).all()

    history_out = []
    for h in history:
        row = h.to_dict()
        # Resolve names for readability
        if h.old_upline_id:
            p = db.query(OfficialPartner).filter(OfficialPartner.id == h.old_upline_id).first()
            row['old_upline_name'] = p.partner_name if p else None
            row['old_upline_code'] = p.partner_code if p else None
        else:
            row['old_upline_name'] = None
            row['old_upline_code'] = None
        if h.new_upline_id:
            p = db.query(OfficialPartner).filter(OfficialPartner.id == h.new_upline_id).first()
            row['new_upline_name'] = p.partner_name if p else None
            row['new_upline_code'] = p.partner_code if p else None
        else:
            row['new_upline_name'] = None
            row['new_upline_code'] = None
        if h.changed_by_id:
            s = db.query(StaffEmployee).filter(StaffEmployee.id == h.changed_by_id).first()
            row['changed_by_name'] = s.full_name if s else None
        else:
            row['changed_by_name'] = None
        history_out.append(row)

    return {
        "success": True,
        "data": {
            "member": {
                "id": member.id,
                "partner_code": member.partner_code,
                "partner_name": member.partner_name,
                "phone": member.phone,
                "is_active": member.is_active,
                "current_upline_id": member.parent_partner_id,
            },
            "upline_chain": upline_chain,
            "pending_entries_affected": pending_affected,
            "change_history": history_out,
        }
    }


# ---------------------------------------------------------------------------
# Upline Change — Apply
# ---------------------------------------------------------------------------

class ChangeUplinePayload(BaseModel):
    new_upline_id:    Optional[int] = Field(None, description="ID of new upline; pass null/0 to remove upline")
    reason:           str           = Field(..., min_length=5, description="Mandatory reason for the change")
    reassign_pending: bool          = Field(False, description="If true, reassign PENDING L2/L3 entries of old upline to new upline")


@router.post("/members/{member_id}/change-upline")
def change_member_upline(
    member_id: int = Path(...),
    payload: ChangeUplinePayload = Body(...),
    current_user: StaffEmployee = Depends(require_vgk_admin),
    db: Session = Depends(get_db)
):
    """
    Audited upline change for a VGK member.
    Validates circular chain, applies change, writes audit log.
    Default: PENDING income entries stay with old upline (reassign_pending=False).
    """
    member = db.query(OfficialPartner).filter(
        OfficialPartner.id == member_id,
        OfficialPartner.category == 'VGK_TEAM'
    ).first()
    if not member:
        raise HTTPException(status_code=404, detail="VGK member not found")

    old_upline_id = member.parent_partner_id

    # Resolve new upline
    new_upline_id = payload.new_upline_id if payload.new_upline_id and payload.new_upline_id != 0 else None
    new_upline = None
    if new_upline_id:
        if new_upline_id == member_id:
            raise HTTPException(status_code=400, detail="A member cannot be their own upline")
        new_upline = db.query(OfficialPartner).filter(
            OfficialPartner.id == new_upline_id,
            OfficialPartner.category == 'VGK_TEAM',
        ).first()
        if not new_upline:
            raise HTTPException(status_code=400, detail="New upline not found or is not a VGK member")

        # Circular chain check — walk up from new_upline; if we reach member_id, it's circular
        check = new_upline
        for _ in range(10):
            if not check.parent_partner_id:
                break
            if check.parent_partner_id == member_id:
                raise HTTPException(
                    status_code=400,
                    detail=f"Circular chain detected: {new_upline.partner_code} is already in {member.partner_code}'s downline"
                )
            check = db.query(OfficialPartner).filter(OfficialPartner.id == check.parent_partner_id).first()
            if not check:
                break

    if old_upline_id == new_upline_id:
        raise HTTPException(status_code=400, detail="New upline is the same as the current upline — no change made")

    # Count pending entries that will be affected
    pending_affected = 0
    if old_upline_id:
        pending_affected = db.query(VGKTeamIncomeEntry).filter(
            VGKTeamIncomeEntry.partner_id == old_upline_id,
            VGKTeamIncomeEntry.status == 'PENDING',
            VGKTeamIncomeEntry.level.in_([2, 3]),
        ).count()

    # Optionally reassign PENDING L2/L3 entries to new upline
    entries_reassigned = False
    if payload.reassign_pending and old_upline_id and new_upline_id and pending_affected > 0:
        db.query(VGKTeamIncomeEntry).filter(
            VGKTeamIncomeEntry.partner_id == old_upline_id,
            VGKTeamIncomeEntry.status == 'PENDING',
            VGKTeamIncomeEntry.level.in_([2, 3]),
        ).update({VGKTeamIncomeEntry.partner_id: new_upline_id}, synchronize_session=False)
        entries_reassigned = True

    # Apply upline change
    member.parent_partner_id = new_upline_id
    member.updated_at = get_indian_time()

    # Write audit log
    log = VGKUplineChangeLog(
        member_id=member_id,
        old_upline_id=old_upline_id,
        new_upline_id=new_upline_id,
        changed_by_id=current_user.id,
        reason=payload.reason,
        pending_entries_affected=pending_affected,
        entries_reassigned=entries_reassigned,
    )
    db.add(log)
    db.commit()
    db.refresh(member)

    new_name = new_upline.partner_name if new_upline else None
    new_code = new_upline.partner_code if new_upline else None

    return {
        "success": True,
        "message": "Upline changed successfully",
        "data": {
            "member_id": member_id,
            "old_upline_id": old_upline_id,
            "new_upline_id": new_upline_id,
            "new_upline_name": new_name,
            "new_upline_code": new_code,
            "pending_entries_affected": pending_affected,
            "entries_reassigned": entries_reassigned,
        }
    }


# ---------------------------------------------------------------------------
# Upline Change — Global Audit Log List
# ---------------------------------------------------------------------------

@router.get("/upline-change-logs")
def list_upline_change_logs(
    member_id:  Optional[int] = Query(None),
    page:       int           = Query(1, ge=1),
    per_page:   int           = Query(30, ge=1, le=100),
    current_user: StaffEmployee = Depends(require_vgk_admin),
    db: Session = Depends(get_db)
):
    """Paginated audit log of all upline changes, optionally filtered by member."""
    q = db.query(VGKUplineChangeLog)
    if member_id:
        q = q.filter(VGKUplineChangeLog.member_id == member_id)
    total = q.count()
    logs = q.order_by(VGKUplineChangeLog.created_at.desc()).offset((page - 1) * per_page).limit(per_page).all()

    # Bulk-resolve names
    all_partner_ids = set()
    all_staff_ids   = set()
    for lg in logs:
        if lg.member_id:    all_partner_ids.add(lg.member_id)
        if lg.old_upline_id: all_partner_ids.add(lg.old_upline_id)
        if lg.new_upline_id: all_partner_ids.add(lg.new_upline_id)
        if lg.changed_by_id: all_staff_ids.add(lg.changed_by_id)

    partners = {}
    if all_partner_ids:
        for p in db.query(OfficialPartner).filter(OfficialPartner.id.in_(all_partner_ids)).all():
            partners[p.id] = {"name": p.partner_name, "code": p.partner_code}
    staff_map = {}
    if all_staff_ids:
        for s in db.query(StaffEmployee).filter(StaffEmployee.id.in_(all_staff_ids)).all():
            staff_map[s.id] = s.full_name

    out = []
    for lg in logs:
        row = lg.to_dict()
        row['member_name']     = partners.get(lg.member_id,     {}).get('name')
        row['member_code']     = partners.get(lg.member_id,     {}).get('code')
        row['old_upline_name'] = partners.get(lg.old_upline_id, {}).get('name')
        row['old_upline_code'] = partners.get(lg.old_upline_id, {}).get('code')
        row['new_upline_name'] = partners.get(lg.new_upline_id, {}).get('name')
        row['new_upline_code'] = partners.get(lg.new_upline_id, {}).get('code')
        row['changed_by_name'] = staff_map.get(lg.changed_by_id)
        out.append(row)

    return {
        "success": True,
        "data":    out,
        "total":   total,
        "page":    page,
        "per_page": per_page,
        "pages":   (total + per_page - 1) // per_page,
    }


class VGKPasswordResetPayload(BaseModel):
    reset_type: str = Field("permanent", description="'permanent' = set to partner_code, 'temporary' = use custom_password")
    custom_password: Optional[str] = Field(None, description="Required when reset_type='temporary'")


@router.post("/members/{member_id}/reset-password")
def reset_vgk_member_password(
    member_id: int = Path(...),
    payload: VGKPasswordResetPayload = None,
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    from app.core.security import SecurityManager
    member = db.query(OfficialPartner).filter(
        OfficialPartner.id == member_id,
        OfficialPartner.category == 'VGK_TEAM'
    ).first()
    if not member:
        raise HTTPException(status_code=404, detail="VGK member not found")

    if payload is None:
        payload = VGKPasswordResetPayload()

    reset_type = payload.reset_type or "permanent"

    if reset_type == "temporary":
        new_password = (payload.custom_password or "").strip()
        if not new_password or len(new_password) < 6:
            raise HTTPException(status_code=400, detail="Temporary password must be at least 6 characters")
    else:
        new_password = member.partner_code

    try:
        member.password_hash = SecurityManager.get_password_hash(new_password)
        member.failed_login_attempts = 0
        member.login_status = 'active'
        from pytz import timezone as _tz
        member.password_changed_at = datetime.now(_tz('Asia/Kolkata'))
        db.commit()
        return {
            "success": True,
            "message": "Password reset successfully",
            "reset_type": reset_type,
            "temporary_password": new_password if reset_type == "temporary" else None,
            "partner_code": member.partner_code,
            "partner_name": member.partner_name
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to reset password: {str(e)}")


# ─── Commission Config Endpoints ─────────────────────────────────────────────

class VGKConfigUpsert(BaseModel):
    level1_pct: float = Field(5.0, ge=0, le=100)
    level1_type: str = Field('PCT', pattern='^(PCT|AMOUNT)$')
    level1_amt: float = Field(0.0, ge=0)
    level2_pct: float = Field(3.0, ge=0, le=100)
    level2_type: str = Field('PCT', pattern='^(PCT|AMOUNT)$')
    level2_amt: float = Field(0.0, ge=0)
    level3_pct: float = Field(1.0, ge=0, le=100)
    level3_type: str = Field('PCT', pattern='^(PCT|AMOUNT)$')
    level3_amt: float = Field(0.0, ge=0)
    # L4 CORE (DC-VGK-L4CORE-001): upliner of L3 — configurable, default 50% of L3
    level4_core_pct: float = Field(0.0, ge=0, le=100)
    level4_core_type: str = Field('PCT', pattern='^(PCT|AMOUNT)$')
    level4_core_amt: float = Field(0.0, ge=0)
    # L5 SUPPORT (stored as level4_* in DB for backward compat)
    level4_pct: float = Field(0.0, ge=0, le=100)
    level4_type: str = Field('PCT', pattern='^(PCT|AMOUNT)$')
    level4_amt: float = Field(0.0, ge=0)
    # L6 SHOWROOM (DC-SHOWROOM-COMMISSION-001)
    showroom_pct: float = Field(0.0, ge=0, le=100)
    showroom_type: str = Field('PCT', pattern='^(PCT|AMOUNT)$')
    showroom_amt: float = Field(0.0, ge=0)
    monthly_target: float = Field(0, ge=0)
    bonus_pct: float = Field(0, ge=0, le=100)
    markup_pct: float = Field(0, ge=0, le=100)
    is_active: bool = True
    is_paid_member: bool = False


@router.get("/config")
def list_vgk_config(
    current_user: StaffEmployee = Depends(require_vgk_admin),
    db: Session = Depends(get_db)
):
    company_id = _get_staff_company_id(current_user)
    categories = db.query(SignupCategory).filter(
        SignupCategory.company_id == company_id,
        SignupCategory.is_active == True
    ).order_by(SignupCategory.name).all()

    # DC Protocol: NO company_id restriction on commission config reads.
    # VGK rates are universal — query all, deduplicate by (category_id, is_paid_member)
    # keeping the most recently updated config per pair.
    configs_by_cat: dict = {}
    all_existing = (
        db.query(VGKTeamCommissionConfig)
        .order_by(VGKTeamCommissionConfig.updated_at.desc())
        .all()
    )
    for c in all_existing:
        key = (c.category_id, bool(c.is_paid_member))
        if key not in configs_by_cat:
            configs_by_cat[key] = c

    total_vgk = db.query(OfficialPartner).filter(
        OfficialPartner.category == 'VGK_TEAM'
    ).count()
    active_vgk = db.query(OfficialPartner).filter(
        OfficialPartner.category == 'VGK_TEAM',
        OfficialPartner.is_active == True
    ).count()

    configured_cats = len({k[0] for k in configs_by_cat})
    result = []
    for cat in categories:
        cfg_reg = configs_by_cat.get((cat.id, False))
        cfg_act = configs_by_cat.get((cat.id, True))
        result.append({
            "category_id": cat.id,
            "category_name": cat.name,
            "config_registered": cfg_reg.to_dict() if cfg_reg else None,
            "config_activated": cfg_act.to_dict() if cfg_act else None,
            "has_config": cfg_reg is not None or cfg_act is not None,
        })

    return {
        "success": True,
        "summary": {"total_vgk_members": total_vgk, "active_vgk_members": active_vgk, "configured_categories": configured_cats},
        "data": result
    }


@router.put("/config/{category_id}")
def upsert_vgk_config(
    category_id: int = Path(...),
    is_paid_member: bool = Query(False),
    payload: VGKConfigUpsert = None,
    current_user: StaffEmployee = Depends(require_vgk_admin),
    db: Session = Depends(get_db)
):
    cat = db.query(SignupCategory).filter(
        SignupCategory.id == category_id
    ).first()
    if not cat:
        raise HTTPException(status_code=404, detail="Category not found")

    # DC Protocol: VGK rates are universal — propagate to ALL company_ids AND to ALL
    # signup_category IDs that share the same category name (one cat_id per company).
    # This ensures staff from any company see the same rates on the public offers page
    # regardless of which company's category_id appears in the PUT path.
    all_same_cat_ids = [
        r[0] for r in db.query(SignupCategory.id).filter(
            SignupCategory.name == cat.name,
            SignupCategory.is_active == True
        ).all()
    ]
    if not all_same_cat_ids:
        all_same_cat_ids = [category_id]

    paid_flag = payload.is_paid_member if payload is not None and hasattr(payload, 'is_paid_member') else is_paid_member
    now = get_indian_time()

    from sqlalchemy import text as _sa_text
    _cid_rows = db.execute(_sa_text(
        "SELECT DISTINCT company_id FROM signup_categories WHERE is_active = TRUE "
        "UNION SELECT DISTINCT company_id FROM vgk_team_commission_config"
    )).fetchall()
    all_company_ids = list({int(r[0]) for r in _cid_rows if r[0]})
    if not all_company_ids:
        all_company_ids = [_get_staff_company_id(current_user)]

    last_cfg = None
    _total_rows = 0
    for ccat_id in all_same_cat_ids:
        for cid in all_company_ids:
            cfg = db.query(VGKTeamCommissionConfig).filter(
                VGKTeamCommissionConfig.company_id == cid,
                VGKTeamCommissionConfig.category_id == ccat_id,
                VGKTeamCommissionConfig.is_paid_member == paid_flag
            ).first()
            if cfg:
                cfg.level1_pct = Decimal(str(payload.level1_pct))
                cfg.level1_type = payload.level1_type
                cfg.level1_amt = Decimal(str(payload.level1_amt))
                cfg.level2_pct = Decimal(str(payload.level2_pct))
                cfg.level2_type = payload.level2_type
                cfg.level2_amt = Decimal(str(payload.level2_amt))
                cfg.level3_pct = Decimal(str(payload.level3_pct))
                cfg.level3_type = payload.level3_type
                cfg.level3_amt = Decimal(str(payload.level3_amt))
                cfg.level4_core_pct = Decimal(str(payload.level4_core_pct))
                cfg.level4_core_type = payload.level4_core_type
                cfg.level4_core_amt = Decimal(str(payload.level4_core_amt))
                cfg.level4_pct = Decimal(str(payload.level4_pct))
                cfg.level4_type = payload.level4_type
                cfg.level4_amt = Decimal(str(payload.level4_amt))
                cfg.showroom_pct       = Decimal(str(payload.showroom_pct))
                cfg.showroom_type      = payload.showroom_type
                cfg.showroom_amt       = Decimal(str(payload.showroom_amt))
                cfg.monthly_target = Decimal(str(payload.monthly_target))
                cfg.bonus_pct = Decimal(str(payload.bonus_pct))
                cfg.markup_pct = Decimal(str(payload.markup_pct))
                cfg.is_active = payload.is_active
                cfg.updated_at = now
            else:
                cfg = VGKTeamCommissionConfig(
                    company_id=cid,
                    category_id=ccat_id,
                    is_paid_member=paid_flag,
                    level1_pct=Decimal(str(payload.level1_pct)),
                    level1_type=payload.level1_type,
                    level1_amt=Decimal(str(payload.level1_amt)),
                    level2_pct=Decimal(str(payload.level2_pct)),
                    level2_type=payload.level2_type,
                    level2_amt=Decimal(str(payload.level2_amt)),
                    level3_pct=Decimal(str(payload.level3_pct)),
                    level3_type=payload.level3_type,
                    level3_amt=Decimal(str(payload.level3_amt)),
                    level4_core_pct=Decimal(str(payload.level4_core_pct)),
                    level4_core_type=payload.level4_core_type,
                    level4_core_amt=Decimal(str(payload.level4_core_amt)),
                    level4_pct=Decimal(str(payload.level4_pct)),
                    level4_type=payload.level4_type,
                    level4_amt=Decimal(str(payload.level4_amt)),
                    showroom_pct=Decimal(str(payload.showroom_pct)),
                    showroom_type=payload.showroom_type,
                    showroom_amt=Decimal(str(payload.showroom_amt)),
                    monthly_target=Decimal(str(payload.monthly_target)),
                    bonus_pct=Decimal(str(payload.bonus_pct)),
                    markup_pct=Decimal(str(payload.markup_pct)),
                    is_active=payload.is_active,
                    created_at=now,
                    updated_at=now
                )
                db.add(cfg)
            _total_rows += 1
            if ccat_id == category_id and last_cfg is None:
                last_cfg = cfg

    db.commit()
    if last_cfg is not None:
        db.refresh(last_cfg)
    logger.info(
        f"[VGK] Config propagated for category '{cat.name}' (cat_id={category_id}) paid={paid_flag} "
        f"across {len(all_same_cat_ids)} cat_id(s) × {len(all_company_ids)} company_id(s) "
        f"= {_total_rows} rows by {current_user.emp_code}"
    )
    return {"success": True, "message": "Commission config saved", "data": last_cfg.to_dict() if last_cfg else {}}


# ─── Income / Commission Endpoints ───────────────────────────────────────────

@router.get("/income")
def list_vgk_income(
    partner_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    level: Optional[int] = Query(None),
    category_id: Optional[int] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=5, le=100),
    current_user: StaffEmployee = Depends(require_vgk_admin),
    db: Session = Depends(get_db)
):
    query = db.query(VGKTeamIncomeEntry)
    if partner_id:
        query = query.filter(VGKTeamIncomeEntry.partner_id == partner_id)
    if status and status != 'ALL':
        query = query.filter(VGKTeamIncomeEntry.status == status.upper())
    else:
        query = query.filter(VGKTeamIncomeEntry.status != 'CANCELLED')
    if level is not None:
        query = query.filter(VGKTeamIncomeEntry.level == level)
    if category_id:
        query = query.filter(VGKTeamIncomeEntry.category_id == category_id)
    if date_from:
        try:
            query = query.filter(VGKTeamIncomeEntry.created_at >= datetime.fromisoformat(date_from))
        except Exception:
            pass
    if date_to:
        try:
            query = query.filter(VGKTeamIncomeEntry.created_at <= datetime.fromisoformat(date_to + "T23:59:59"))
        except Exception:
            pass

    total = query.count()
    entries = query.order_by(VGKTeamIncomeEntry.id.desc()).offset((page - 1) * page_size).limit(page_size).all()

    items = []
    for e in entries:
        d = e.to_dict()
        partner = db.query(OfficialPartner).filter(OfficialPartner.id == e.partner_id).first()
        d['partner_name'] = partner.partner_name if partner else None
        d['partner_code'] = partner.partner_code if partner else None
        if e.category_id:
            cat = db.query(SignupCategory).filter(SignupCategory.id == e.category_id).first()
            d['category_name'] = cat.name if cat else None
        items.append(d)

    from sqlalchemy import or_
    _not_debit = or_(VGKTeamIncomeEntry.notes == None, ~VGKTeamIncomeEntry.notes.like('DEBIT:%'))
    pending_amt = db.query(func.sum(VGKTeamIncomeEntry.commission_amount + VGKTeamIncomeEntry.bonus_amount)).filter(
        VGKTeamIncomeEntry.status == 'PENDING',
        _not_debit
    ).scalar() or 0
    confirmed_amt = db.query(func.sum(VGKTeamIncomeEntry.commission_amount + VGKTeamIncomeEntry.bonus_amount)).filter(
        VGKTeamIncomeEntry.status == 'CONFIRMED',
        _not_debit
    ).scalar() or 0

    from pytz import timezone
    now = datetime.now(timezone('Asia/Kolkata'))
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    month_amt = db.query(func.sum(VGKTeamIncomeEntry.commission_amount + VGKTeamIncomeEntry.bonus_amount)).filter(
        VGKTeamIncomeEntry.created_at >= month_start,
        VGKTeamIncomeEntry.status != 'CANCELLED',
        _not_debit
    ).scalar() or 0

    return {
        "success": True,
        "summary": {
            "total_pending": float(pending_amt),
            "total_confirmed": float(confirmed_amt),
            "this_month": float(month_amt),
            "total_entries": total
        },
        "total": total,
        "page": page,
        "page_size": page_size,
        "data": items
    }



_AUTO_REFILL_AMOUNT = Decimal('50000')
_AUTO_REFILL_WINDOW_DAYS = 180  # 180 days
_AUTO_REFILL_MAX_COUNT = 2      # maximum 2 refills per member lifetime


def _check_and_apply_auto_refill(partner: OfficialPartner, db: Session, now) -> bool:
    """
    [DC-POINTS-REFILL] Apr 2026
    After any points debit: if an activated member's balance hits 0 within 180 days
    of the most recent 50k credit (activation or last refill), auto-credit 50,000 more.
    Maximum 2 refills total per member (lifetime cap).

    Returns True if a refill was applied, False otherwise.
    Caller must NOT commit — the enclosing transaction handles that.
    """
    if not partner.is_paid_activation:
        return False
    current_balance = partner.vgk_points_balance or Decimal('0')
    if current_balance > Decimal('0'):
        return False

    refill_count = partner.vgk_points_refill_count or 0
    if refill_count >= _AUTO_REFILL_MAX_COUNT:
        return False

    if refill_count == 0:
        window_start = partner.vgk_activated_at
    else:
        window_start = partner.vgk_points_last_refill_at

    if not window_start:
        return False

    window_start_naive = window_start.replace(tzinfo=None) if window_start.tzinfo else window_start
    now_naive = now.replace(tzinfo=None) if hasattr(now, 'tzinfo') and now.tzinfo else now
    days_elapsed = (now_naive - window_start_naive).days
    if days_elapsed > _AUTO_REFILL_WINDOW_DAYS:
        return False

    new_balance = _AUTO_REFILL_AMOUNT
    partner.vgk_points_balance = new_balance
    partner.vgk_points_refill_count = refill_count + 1
    partner.vgk_points_last_refill_at = now_naive
    partner.updated_at = now_naive

    refill_num = refill_count + 1
    ledger_entry = VGKPointsLedger(
        partner_id=partner.id,
        points_credit=_AUTO_REFILL_AMOUNT,
        points_debit=Decimal('0'),
        balance_after=new_balance,
        reason_code='AUTO_REFILL',
        reference_type='AUTO_REFILL',
        reference_id=None,
        notes=f'Auto-refill #{refill_num}: Balance zeroed within 180 days of last credit',
        created_at=now_naive,
        created_by=None,
    )
    db.add(ledger_entry)
    logger.info(
        '[DC-POINTS-REFILL] Partner %s: auto-refill #%d applied (%s pts), window_start=%s, days_elapsed=%d',
        partner.id, refill_num, _AUTO_REFILL_AMOUNT, window_start_naive, days_elapsed,
    )
    return True


def _create_payout_debit_entry(db: Session, entry: VGKTeamIncomeEntry):
    level_names = {1: 'L1 Commission Payout', 2: 'L2 Commission Payout',
                   3: 'L3 Commission Payout', 4: 'Field Support Commission Payout'}
    desc = level_names.get(entry.level, f'L{entry.level} Commission Payout')
    if entry.source_lead_id:
        desc += f' (Lead #{entry.source_lead_id})'
    amount = entry.commission_amount + (entry.bonus_amount or Decimal('0'))
    now = get_indian_time()
    debit_entry_no = _next_vgk_entry_number(db, entry.company_id, prefix='VGKD')
    debit = VGKTeamIncomeEntry(
        company_id=entry.company_id,
        entry_number=debit_entry_no,
        partner_id=entry.partner_id,
        source_lead_id=entry.source_lead_id,
        source_transaction_id=entry.source_transaction_id,
        category_id=entry.category_id,
        level=entry.level,
        revenue_amount=Decimal('0'),
        commission_pct=Decimal('0'),
        commission_amount=amount,
        bonus_amount=Decimal('0'),
        status='CONFIRMED',
        notes=f'DEBIT: {desc}',
        confirmed_at=now,
        confirmed_by=entry.confirmed_by,
        created_at=now,
        updated_at=now
    )
    db.add(debit)
    partner = db.query(OfficialPartner).filter(OfficialPartner.id == entry.partner_id).first()
    if partner:
        partner.vgk_points_balance = (partner.vgk_points_balance or Decimal('0')) - amount
        partner.updated_at = now
        _check_and_apply_auto_refill(partner, db, now)


def _apply_support_redistribution(db: Session, triggering_entry: VGKTeamIncomeEntry, staff_id: int, now) -> list:
    """
    DC Protocol Apr 2026: When confirming an L2 or L3 entry with support_confirmed != True,
    apply the 30/30/30/10 redistribution of the combined L2+L3 pool for this lead.
    Returns all L2/L3 entries that were adjusted (to be confirmed in the same batch).
    """
    from app.models.crm import CRMLead

    lead_id = triggering_entry.source_lead_id
    if not lead_id:
        return [triggering_entry]

    # Collect ALL pending L2+L3 entries for this lead (not yet confirmed)
    unconfirmed_l23 = db.query(VGKTeamIncomeEntry).filter(
        VGKTeamIncomeEntry.source_lead_id == lead_id,
        VGKTeamIncomeEntry.level.in_([2, 3]),
        VGKTeamIncomeEntry.status == 'PENDING',
    ).all()

    # Separate confirmed vs unconfirmed (by support_confirmed flag)
    unconf = [e for e in unconfirmed_l23 if e.support_confirmed is not True]
    confirmed_ok = [e for e in unconfirmed_l23 if e.support_confirmed is True]

    if not unconf:
        return [triggering_entry]

    pool = sum(e.commission_amount or Decimal('0') for e in unconf)
    if pool <= 0:
        return unconf

    l2_share = (pool * Decimal('0.30')).quantize(Decimal('0.01'))
    l3_share = (pool * Decimal('0.10')).quantize(Decimal('0.01'))
    l1_bonus = (pool * Decimal('0.30')).quantize(Decimal('0.01'))
    l4_bonus = (pool * Decimal('0.30')).quantize(Decimal('0.01'))

    l2_entry = next((e for e in unconf if e.level == 2), None)
    l3_entry = next((e for e in unconf if e.level == 3), None)

    if l2_entry:
        l2_entry.commission_amount = l2_share
        old_notes = l2_entry.notes or ''
        l2_entry.notes = old_notes + f' | RDIST: support unconfirmed, 30% of pool ₹{float(pool):.2f}'
        l2_entry.updated_at = now
    if l3_entry:
        l3_entry.commission_amount = l3_share
        old_notes = l3_entry.notes or ''
        l3_entry.notes = old_notes + f' | RDIST: support unconfirmed, 10% of pool ₹{float(pool):.2f}'
        l3_entry.updated_at = now

    ref = unconf[0]

    # Find lead to resolve L1 and L4
    lead = db.query(CRMLead).filter(CRMLead.id == lead_id).first()
    if lead and l1_bonus > 0 and lead.associated_partner_id:
        l1p = db.query(OfficialPartner).filter(OfficialPartner.id == lead.associated_partner_id).first()
        if l1p:
            eNo = _next_vgk_entry_number(db, ref.company_id, 'VGK')
            bonus_e = VGKTeamIncomeEntry(
                company_id=ref.company_id, entry_number=eNo,
                partner_id=l1p.id, source_lead_id=lead_id,
                source_transaction_id=ref.source_transaction_id, category_id=ref.category_id,
                level=1, revenue_amount=ref.revenue_amount, commission_pct=Decimal('0'),
                commission_amount=l1_bonus, bonus_amount=Decimal('0'),
                required_points_debit=Decimal('0'), status='CONFIRMED',
                confirmed_at=now, confirmed_by=staff_id,
                notes=f'RDIST-L1: 30% redistribution (L2/L3 support unconfirmed) lead #{lead_id} pool ₹{float(pool):.2f}',
                created_at=now, updated_at=now
            )
            db.add(bonus_e)
            l1p.vgk_points_balance = (l1p.vgk_points_balance or Decimal('0')) + l1_bonus
            l1p.updated_at = now
            logger.info(f"[VGK-RDIST] L1 bonus ₹{float(l1_bonus):.2f} → partner {l1p.partner_code}")

    if lead and l4_bonus > 0 and lead.vgk_field_support_id:
        l4p = db.query(OfficialPartner).filter(OfficialPartner.id == lead.vgk_field_support_id).first()
        if l4p:
            eNo = _next_vgk_entry_number(db, ref.company_id, 'VGK')
            bonus_e = VGKTeamIncomeEntry(
                company_id=ref.company_id, entry_number=eNo,
                partner_id=l4p.id, source_lead_id=lead_id,
                source_transaction_id=ref.source_transaction_id, category_id=ref.category_id,
                level=4, revenue_amount=ref.revenue_amount, commission_pct=Decimal('0'),
                commission_amount=l4_bonus, bonus_amount=Decimal('0'),
                required_points_debit=Decimal('0'), status='CONFIRMED',
                confirmed_at=now, confirmed_by=staff_id,
                notes=f'RDIST-L4: 30% redistribution (L2/L3 support unconfirmed) lead #{lead_id} pool ₹{float(pool):.2f}',
                created_at=now, updated_at=now
            )
            db.add(bonus_e)
            l4p.vgk_points_balance = (l4p.vgk_points_balance or Decimal('0')) + l4_bonus
            l4p.updated_at = now
            logger.info(f"[VGK-RDIST] L4 bonus ₹{float(l4_bonus):.2f} → partner {l4p.partner_code}")

    return unconf


@router.post("/income/{entry_id}/confirm")
def confirm_vgk_income(
    entry_id: int = Path(...),
    current_user: StaffEmployee = Depends(require_ea),
    db: Session = Depends(get_db)
):
    entry = db.query(VGKTeamIncomeEntry).filter(
        VGKTeamIncomeEntry.id == entry_id
    ).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Income entry not found")
    if entry.status != 'PENDING':
        raise HTTPException(status_code=400, detail=f"Cannot confirm entry with status: {entry.status}")

    now = get_indian_time()

    # DC Protocol Apr 2026: Support redistribution for unconfirmed L2/L3 entries
    entries_to_confirm = [entry]
    if entry.level in (2, 3) and entry.support_confirmed is not True:
        entries_to_confirm = _apply_support_redistribution(db, entry, current_user.id, now)

    for e in entries_to_confirm:
        if e.status != 'PENDING':
            continue
        e.status = 'CONFIRMED'
        e.confirmed_at = now
        e.confirmed_by = current_user.id
        e.updated_at = now
        partner = db.query(OfficialPartner).filter(OfficialPartner.id == e.partner_id).first()
        if partner:
            partner.vgk_points_balance = (partner.vgk_points_balance or Decimal('0')) + e.commission_amount + (e.bonus_amount or Decimal('0'))
            partner.updated_at = now
        if e.level > 0:
            _create_payout_debit_entry(db, e)

    db.commit()
    db.refresh(entry)
    logger.info(f"[VGK] Income entry {entry.entry_number} confirmed by {current_user.emp_code}")
    return {"success": True, "message": "Income entry confirmed and points credited", "data": entry.to_dict()}


class StaffSupportConfirmRequest(BaseModel):
    confirmed: Optional[bool] = Field(None, description="True=supported, False=not supported, None=reset")


@router.get("/income/by-lead/{lead_id}")
def get_income_by_lead(
    lead_id: int = Path(...),
    current_user: StaffEmployee = Depends(require_ea),
    db: Session = Depends(get_db)
):
    """
    DC Protocol Apr 2026: Fetch all VGK income entries for a specific lead.
    Used by staff MNR leads master page to show support confirmation toggles.
    """
    entries = db.query(VGKTeamIncomeEntry).filter(
        VGKTeamIncomeEntry.source_lead_id == lead_id,
        VGKTeamIncomeEntry.deleted_at == None,
        VGKTeamIncomeEntry.status != 'CANCELLED',
    ).order_by(VGKTeamIncomeEntry.level.asc(), VGKTeamIncomeEntry.id.asc()).all()

    result = []
    for e in entries:
        p = db.query(OfficialPartner).filter(OfficialPartner.id == e.partner_id).first()
        result.append({
            **e.to_dict(),
            "partner_name": p.partner_name if p else "—",
            "partner_code": p.partner_code if p else "—",
        })

    return {"success": True, "lead_id": lead_id, "entries": result}


@router.post("/income/retrigger")
def retrigger_income_drafts(
    lead_id: int = Query(..., description="CRM lead ID to retrigger VGK income for"),
    current_user: StaffEmployee = Depends(require_vgk_admin),
    db: Session = Depends(get_db)
):
    """
    DC-TEAM-RETRIGGER-001 (Jun 2026): Manually retrigger VGK income draft generation for a
    specific completed lead. Idempotent — only creates entries for levels that don't already
    have one. Use to recover leads whose income was missed (e.g. pre-fix UnboundLocalError).
    """
    from app.models.crm import CRMLead
    from app.services.vgk_cash_income import generate_vgk_cash_income_drafts
    lead = db.query(CRMLead).filter(
        CRMLead.id == lead_id,
        CRMLead.company_id == current_user.company_id
    ).first()
    if not lead:
        raise HTTPException(status_code=404, detail='Lead not found')
    if lead.status != 'completed':
        raise HTTPException(status_code=400, detail=f'Lead status is {lead.status!r} — income only generates for completed leads')
    if not lead.associated_partner_id:
        raise HTTPException(status_code=400, detail='Lead has no associated VGK partner set')
    n = generate_vgk_cash_income_drafts(db, lead)
    db.commit()
    return {
        'success': True,
        'new_drafts_created': n,
        'lead_id': lead_id,
        'message': f'{n} new DRAFT income entr{"y" if n==1 else "ies"} created' if n
                   else 'No new entries — all levels already exist or have 0% config'
    }


@router.get("/income/audit-missing")
def audit_missing_income(
    current_user: StaffEmployee = Depends(require_vgk_admin),
    db: Session = Depends(get_db)
):
    """
    DC-TEAM-RETRIGGER-001 (Jun 2026): Returns completed leads with a VGK partner but
    zero vgk_cash_income_entries (COMMISSION kind). Identifies leads affected by the
    pre-fix income generation failure. Use with /income/retrigger to recover.
    """
    rows = db.execute(text("""
        SELECT
            l.id              AS lead_id,
            l.customer_name,
            l.category_id,
            l.associated_partner_id,
            l.actual_close_date,
            op.partner_name,
            op.partner_code
        FROM crm_leads l
        JOIN official_partners op ON op.id = l.associated_partner_id
        LEFT JOIN vgk_cash_income_entries vci
               ON vci.source_lead_id = l.id
              AND vci.status NOT IN ('CANCELLED')
              AND vci.kind = 'COMMISSION'
        WHERE l.status = 'completed'
          AND l.associated_partner_id IS NOT NULL
          AND l.company_id = :cid
        GROUP BY l.id, l.customer_name, l.category_id, l.associated_partner_id,
                 l.actual_close_date, op.partner_name, op.partner_code
        HAVING COUNT(vci.id) = 0
        ORDER BY l.actual_close_date DESC NULLS LAST
        LIMIT 200
    """), {'cid': current_user.company_id}).fetchall()
    return {
        'success': True,
        'affected_count': len(rows),
        'leads': [dict(r._mapping) for r in rows]
    }


@router.post("/income/{entry_id}/set-support")
def staff_set_support(
    entry_id: int = Path(...),
    body: StaffSupportConfirmRequest = Body(...),
    current_user: StaffEmployee = Depends(require_vgk_admin),
    db: Session = Depends(get_db)
):
    """
    DC Protocol Apr 2026: Staff sets support_confirmed on an L2/L3 income entry.
    Only applicable to level 2 (Guru) and level 3 (Z Guru) entries.
    """
    entry = db.query(VGKTeamIncomeEntry).filter(VGKTeamIncomeEntry.id == entry_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Income entry not found")
    if entry.level not in (2, 3):
        raise HTTPException(status_code=400, detail="Support confirmation only applies to L2 (Guru) and L3 (Z Guru) entries")

    now = get_indian_time()
    entry.support_confirmed = body.confirmed
    entry.support_confirmed_at = now
    entry.support_confirmed_by_id = current_user.id
    entry.support_confirmed_by_type = "staff"
    entry.updated_at = now
    db.commit()

    action = "confirmed" if body.confirmed is True else ("denied" if body.confirmed is False else "reset")
    return {
        "success": True,
        "message": f"L{entry.level} support {action} by staff",
        "entry_id": entry.id,
        "support_confirmed": entry.support_confirmed,
    }


@router.post("/income/{entry_id}/cancel")
def cancel_vgk_income(
    entry_id: int = Path(...),
    current_user: StaffEmployee = Depends(require_ea),
    db: Session = Depends(get_db)
):
    entry = db.query(VGKTeamIncomeEntry).filter(
        VGKTeamIncomeEntry.id == entry_id
    ).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Income entry not found")
    if entry.status == 'CONFIRMED':
        raise HTTPException(status_code=400, detail="Cannot cancel a confirmed entry")

    entry.status = 'CANCELLED'
    entry.updated_at = get_indian_time()
    db.commit()
    db.refresh(entry)
    logger.info(f"[VGK] Income entry {entry.entry_number} cancelled by {current_user.emp_code}")
    return {"success": True, "message": "Income entry cancelled", "data": entry.to_dict()}


@router.post("/income/bulk-confirm")
def bulk_confirm_vgk_income(
    entry_ids: List[int],
    current_user: StaffEmployee = Depends(require_ea),
    db: Session = Depends(get_db)
):
    confirmed = 0
    errors = []
    already_processed_leads = set()  # Track lead IDs already redistributed in this batch
    now = get_indian_time()

    for entry_id in entry_ids:
        entry = db.query(VGKTeamIncomeEntry).filter(
            VGKTeamIncomeEntry.id == entry_id,
            VGKTeamIncomeEntry.status == 'PENDING'
        ).first()
        if not entry:
            errors.append(entry_id)
            continue

        entries_to_confirm = [entry]
        if entry.level in (2, 3) and entry.support_confirmed is not True:
            lead_id = entry.source_lead_id
            if lead_id and lead_id not in already_processed_leads:
                entries_to_confirm = _apply_support_redistribution(db, entry, current_user.id, now)
                already_processed_leads.add(lead_id)

        for e in entries_to_confirm:
            if e.status != 'PENDING':
                continue
            e.status = 'CONFIRMED'
            e.confirmed_at = now
            e.confirmed_by = current_user.id
            e.updated_at = now
            partner = db.query(OfficialPartner).filter(OfficialPartner.id == e.partner_id).first()
            if partner:
                partner.vgk_points_balance = (partner.vgk_points_balance or Decimal('0')) + e.commission_amount + (e.bonus_amount or Decimal('0'))
                partner.updated_at = now
            if e.level > 0:
                _create_payout_debit_entry(db, e)
            confirmed += 1

    db.commit()
    return {"success": True, "confirmed": confirmed, "skipped": len(errors), "skipped_ids": errors}


# ============= VGK My Deals (partner-facing) =============

def _get_vgk_member(request: Request, db: Session = Depends(get_db)) -> OfficialPartner:
    from app.api.v1.endpoints.vgk_auth import get_current_vgk_member
    return get_current_vgk_member(request, db)


@router.get("/my-deals")
def get_vgk_my_deals(
    request: Request,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    credit_role: Optional[str] = Query(None, description="Filter: source | referrer | field_support"),
    db: Session = Depends(get_db),
    current_member: OfficialPartner = Depends(_get_vgk_member)
):
    """
    DC Protocol: VGK partner's deals — returns crm_lead_deals where any credit field
    matches this partner's partner_code. credit_role label included per deal.
    Auth: VGK member JWT token.
    """
    from app.models.crm import CRMLeadDeal, CRMLead
    from app.models.signup_category import SignupCategory
    from sqlalchemy import or_

    credit_id = current_member.partner_code

    if credit_role == 'source':
        query = db.query(CRMLeadDeal).filter(CRMLeadDeal.deal_source_id == credit_id)
    elif credit_role == 'referrer':
        query = db.query(CRMLeadDeal).filter(CRMLeadDeal.deal_referrer_id == credit_id)
    elif credit_role == 'field_support':
        query = db.query(CRMLeadDeal).filter(CRMLeadDeal.deal_field_support_id == credit_id)
    else:
        query = db.query(CRMLeadDeal).filter(
            or_(
                CRMLeadDeal.deal_source_id == credit_id,
                CRMLeadDeal.deal_referrer_id == credit_id,
                CRMLeadDeal.deal_field_support_id == credit_id
            )
        )

    if status:
        query = query.filter(CRMLeadDeal.status == status)

    total = query.count()
    deals = query.order_by(CRMLeadDeal.created_at.desc()).offset((page - 1) * per_page).limit(per_page).all()

    cat_ids = list({d.revenue_category_id for d in deals if d.revenue_category_id})
    lead_ids = list({d.lead_id for d in deals})
    cats = {c.id: c.name for c in db.query(SignupCategory).filter(SignupCategory.id.in_(cat_ids)).all()} if cat_ids else {}
    leads_map = {l.id: l for l in db.query(CRMLead).filter(CRMLead.id.in_(lead_ids)).all()} if lead_ids else {}

    result = []
    for d in deals:
        dd = d.to_dict()
        dd['category_name'] = cats.get(d.revenue_category_id)
        lead = leads_map.get(d.lead_id)
        dd['lead_name'] = lead.name if lead else None
        dd['lead_phone'] = lead.phone if lead else None
        roles = []
        if d.deal_source_id == credit_id:
            roles.append('Source')
        if d.deal_referrer_id == credit_id:
            roles.append('Referrer')
        if d.deal_field_support_id == credit_id:
            roles.append('Field Support')
        dd['credit_role'] = ', '.join(roles)
        result.append(dd)

    return {
        'success': True,
        'data': result,
        'total': total,
        'page': page,
        'per_page': per_page,
        'pages': (total + per_page - 1) // per_page if per_page else 1
    }


# ============= VGK Member Coupon System (DC Protocol Mar 2026) =============
# Flow: Member buys N×₹5000 coupons (pay+upload proof) → Staff approves → coupons credited
# Buy 20 = get 2 free (22 delivered). Transfer = instant. Activate-member = staff-confirmed.

_COUPON_CREDIT_TYPES  = ('purchase_credit', 'bonus_credit', 'transfer_in', 'admin_credit')
_COUPON_DEBIT_TYPES   = ('transfer_out', 'activation_used', 'admin_debit')
_MONTHLY_TRANSFER_LIMIT = 50  # configurable default per partner per calendar month


def _get_coupon_balance(partner_id: int, db: Session) -> int:
    """Return current coupon balance for a VGK partner from vgk_coupon_ledger.
    Credits: purchase_credit, bonus_credit, transfer_in, admin_credit
    Debits:  transfer_out, activation_used, admin_debit
    manual_adjustment can be either — handled via signed quantity convention (negative = debit).
    """
    try:
        row = db.execute(text(
            "SELECT COALESCE(SUM("
            "  CASE WHEN transaction_type IN ('purchase_credit','bonus_credit','transfer_in','admin_credit') THEN quantity "
            "       WHEN transaction_type IN ('transfer_out','activation_used','admin_debit') THEN -quantity "
            "       WHEN transaction_type = 'manual_adjustment' THEN quantity "
            "       ELSE 0 END"
            "), 0) FROM vgk_coupon_ledger WHERE partner_id = :pid"
        ), {"pid": partner_id}).scalar()
        return int(row or 0)
    except Exception:
        return 0


def _get_coupon_breakdown(partner_id: int, db: Session) -> dict:
    """Return detailed coupon statistics for a partner (for dashboard display)."""
    try:
        rows = db.execute(text(
            "SELECT transaction_type, COALESCE(SUM(quantity), 0) AS total "
            "FROM vgk_coupon_ledger WHERE partner_id = :pid GROUP BY transaction_type"
        ), {"pid": partner_id}).fetchall()
        sums = {r.transaction_type: int(r.total) for r in rows}
        purchased   = sums.get('purchase_credit', 0)
        bonus       = sums.get('bonus_credit', 0)
        transfer_in = sums.get('transfer_in', 0)
        admin_cr    = sums.get('admin_credit', 0)
        activation  = sums.get('activation_used', 0)
        transferred = sums.get('transfer_out', 0)
        admin_db    = sums.get('admin_debit', 0)
        manual_adj  = sums.get('manual_adjustment', 0)
        total_credits = purchased + bonus + transfer_in + admin_cr + manual_adj
        total_debits  = activation + transferred + admin_db
        available     = total_credits - total_debits
        return {
            "total_purchased": purchased,
            "bonus_received": bonus,
            "received_from_transfers": transfer_in,
            "used_for_activation": activation,
            "transferred_out": transferred,
            "available_balance": max(0, available),
        }
    except Exception:
        return {"total_purchased": 0, "bonus_received": 0, "received_from_transfers": 0,
                "used_for_activation": 0, "transferred_out": 0, "available_balance": 0}


def _get_monthly_transfer_out(partner_id: int, db: Session) -> int:
    """Return total coupons transferred OUT by this partner in the current calendar month."""
    try:
        row = db.execute(text(
            "SELECT COALESCE(SUM(quantity), 0) FROM vgk_coupon_ledger "
            "WHERE partner_id = :pid AND transaction_type = 'transfer_out' "
            "AND date_trunc('month', created_at) = date_trunc('month', NOW())"
        ), {"pid": partner_id}).scalar()
        return int(row or 0)
    except Exception:
        return 0


class VGKCouponPurchaseRequest(BaseModel):
    quantity: int = Field(..., ge=1, le=200)
    payment_method: Optional[str] = None
    transaction_ref: Optional[str] = None
    payment_proof_url: Optional[str] = None
    payment_notes: Optional[str] = None


class VGKCouponTransferRequest(BaseModel):
    to_vgk_id: str = Field(..., min_length=4)
    quantity: int = Field(..., ge=1, le=50)
    notes: Optional[str] = None


class VGKActivateMemberRequest(BaseModel):
    target_vgk_id: str = Field(..., min_length=4)
    notes: Optional[str] = None


@router.get("/member/coupons/balance")
def vgk_member_coupon_balance(
    request: Request,
    db: Session = Depends(get_db)
):
    from app.api.v1.endpoints.vgk_auth import get_current_vgk_member
    current_member = get_current_vgk_member(request, db)
    breakdown = _get_coupon_breakdown(current_member.id, db)
    monthly_used = _get_monthly_transfer_out(current_member.id, db)
    return {
        "success": True,
        "data": {
            "partner_code": current_member.partner_code,
            "balance": breakdown["available_balance"],
            "total_purchased": breakdown["total_purchased"],
            "bonus_received": breakdown["bonus_received"],
            "received_from_transfers": breakdown["received_from_transfers"],
            "used_for_activation": breakdown["used_for_activation"],
            "transferred_out": breakdown["transferred_out"],
            "available_balance": breakdown["available_balance"],
            "monthly_transfer_used": monthly_used,
            "monthly_transfer_limit": _MONTHLY_TRANSFER_LIMIT,
            "monthly_transfer_remaining": max(0, _MONTHLY_TRANSFER_LIMIT - monthly_used),
            "policy": {
                "purpose": "Activation credits only — not currency",
                "can_use_for": ["activating a partner account", "transferring to another active partner"],
                "cannot_use_for": ["cash redemption", "points conversion", "external resale"],
            }
        }
    }


@router.get("/member/coupons/purchases")
def vgk_member_coupon_purchases(
    request: Request,
    page: int = Query(1, ge=1),
    db: Session = Depends(get_db)
):
    from app.api.v1.endpoints.vgk_auth import get_current_vgk_member
    current_member = get_current_vgk_member(request, db)
    per_page = 10
    try:
        total_row = db.execute(text(
            "SELECT COUNT(*) FROM vgk_coupon_purchases WHERE partner_id = :pid"
        ), {"pid": current_member.id}).scalar() or 0
        rows = db.execute(text(
            "SELECT id, quantity, bonus_quantity, unit_price, total_amount, payment_method, "
            "transaction_ref, payment_proof_url, payment_notes, status, rejection_reason, "
            "created_at, approved_at FROM vgk_coupon_purchases "
            "WHERE partner_id = :pid ORDER BY created_at DESC LIMIT :lim OFFSET :off"
        ), {"pid": current_member.id, "lim": per_page, "off": (page-1)*per_page}).fetchall()
        purchases = [dict(r._mapping) for r in rows]
        for p in purchases:
            for k in ('created_at', 'approved_at'):
                if p.get(k):
                    p[k] = p[k].isoformat()
    except Exception as e:
        purchases = []
        total_row = 0
    return {"success": True, "data": purchases, "total": int(total_row), "page": page, "pages": max(1, (int(total_row)+per_page-1)//per_page)}


@router.post("/member/coupons/purchase")
def vgk_member_buy_coupons(
    request: Request,
    payload: VGKCouponPurchaseRequest,
    db: Session = Depends(get_db)
):
    from app.api.v1.endpoints.vgk_auth import get_current_vgk_member
    current_member = get_current_vgk_member(request, db)
    qty = payload.quantity
    # 20+ coupons = 2 free per every 20
    bonus = 2 * (qty // 20)
    unit_price = 5000
    total = qty * unit_price
    try:
        result = db.execute(text(
            "INSERT INTO vgk_coupon_purchases "
            "(partner_id, quantity, bonus_quantity, unit_price, total_amount, payment_method, "
            "transaction_ref, payment_proof_url, payment_notes, status, created_at, updated_at) "
            "VALUES (:pid, :qty, :bonus, :unit, :total, :pm, :ref, :proof, :notes, 'PENDING', NOW(), NOW()) RETURNING id"
        ), {
            "pid": current_member.id, "qty": qty, "bonus": bonus,
            "unit": unit_price, "total": total,
            "pm": payload.payment_method, "ref": payload.transaction_ref,
            "proof": payload.payment_proof_url, "notes": payload.payment_notes
        }).scalar()
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to submit purchase request: {e}")
    return {
        "success": True,
        "message": f"Purchase request submitted. {qty} coupons + {bonus} bonus = {qty+bonus} total on approval.",
        "data": {"id": result, "quantity": qty, "bonus": bonus, "total_quantity": qty+bonus, "total_amount": total}
    }


@router.get("/member/coupons/transactions")
def vgk_member_coupon_transactions(
    request: Request,
    page: int = Query(1, ge=1),
    db: Session = Depends(get_db)
):
    from app.api.v1.endpoints.vgk_auth import get_current_vgk_member
    current_member = get_current_vgk_member(request, db)
    per_page = 20
    balance = _get_coupon_balance(current_member.id, db)
    try:
        total_row = db.execute(text(
            "SELECT COUNT(*) FROM vgk_coupon_ledger WHERE partner_id = :pid"
        ), {"pid": current_member.id}).scalar() or 0
        rows = db.execute(text(
            "SELECT l.id, l.transaction_type, l.quantity, l.notes, l.created_at, "
            "op.partner_code AS related_code, op.partner_name AS related_name "
            "FROM vgk_coupon_ledger l "
            "LEFT JOIN official_partners op ON op.id = l.related_partner_id "
            "WHERE l.partner_id = :pid ORDER BY l.created_at DESC LIMIT :lim OFFSET :off"
        ), {"pid": current_member.id, "lim": per_page, "off": (page-1)*per_page}).fetchall()
        txns = [dict(r._mapping) for r in rows]
        for t in txns:
            if t.get('created_at'):
                t['created_at'] = t['created_at'].isoformat()
    except Exception as e:
        txns = []
        total_row = 0
    return {"success": True, "data": txns, "balance": balance, "total": int(total_row),
            "page": page, "pages": max(1, (int(total_row)+per_page-1)//per_page)}


@router.get("/member/coupons/lookup-member")
def vgk_member_lookup(
    request: Request,
    vgk_id: str = Query(..., min_length=4),
    db: Session = Depends(get_db)
):
    from app.api.v1.endpoints.vgk_auth import get_current_vgk_member
    current_member = get_current_vgk_member(request, db)
    target = db.query(OfficialPartner).filter(
        OfficialPartner.partner_code == vgk_id.strip().upper(),
        OfficialPartner.category == 'VGK_TEAM'
    ).first()
    if not target:
        raise HTTPException(status_code=404, detail="VGK member not found")
    if target.id == current_member.id:
        raise HTTPException(status_code=400, detail="Cannot target yourself")
    return {"success": True, "data": {
        "id": target.id,
        "partner_code": target.partner_code,
        "partner_name": target.partner_name,
        "is_active": target.is_active,
        "kyc_status": target.kyc_status or "Not Submitted",
        "vgk_activated_at": target.vgk_activated_at.isoformat() if target.vgk_activated_at else None
    }}


@router.post("/member/coupons/transfer")
def vgk_member_transfer_coupon(
    request: Request,
    payload: VGKCouponTransferRequest,
    db: Session = Depends(get_db)
):
    from app.api.v1.endpoints.vgk_auth import get_current_vgk_member
    current_member = get_current_vgk_member(request, db)

    # Rule: Sender must be active
    if not current_member.is_active:
        raise HTTPException(status_code=403, detail="Your account is not active. Cannot transfer coupons.")

    # Find recipient
    recipient = db.query(OfficialPartner).filter(
        OfficialPartner.partner_code == payload.to_vgk_id.strip().upper(),
        OfficialPartner.category == 'VGK_TEAM'
    ).first()
    if not recipient:
        raise HTTPException(status_code=404, detail="Recipient VGK member not found")
    if recipient.id == current_member.id:
        raise HTTPException(status_code=400, detail="Cannot transfer coupons to yourself")

    # Rule: Receiver must be an active partner
    if not recipient.is_active:
        raise HTTPException(status_code=400, detail=f"{recipient.partner_code} is not an active partner and cannot receive coupons.")

    # Rule: Receiver must have completed KYC
    kyc_ok = (recipient.kyc_status or '').strip().lower() in ('approved', 'verified', 'completed')
    if not kyc_ok:
        raise HTTPException(
            status_code=400,
            detail=f"{recipient.partner_code} has not completed KYC verification (status: {recipient.kyc_status or 'Not Submitted'}). KYC approval required before receiving coupons."
        )

    # Rule: Monthly transfer limit per sender
    monthly_used = _get_monthly_transfer_out(current_member.id, db)
    if monthly_used + payload.quantity > _MONTHLY_TRANSFER_LIMIT:
        remaining = max(0, _MONTHLY_TRANSFER_LIMIT - monthly_used)
        raise HTTPException(
            status_code=400,
            detail=f"Monthly transfer limit of {_MONTHLY_TRANSFER_LIMIT} coupons reached. "
                   f"Used this month: {monthly_used}. Remaining: {remaining}."
        )

    # Check balance
    balance = _get_coupon_balance(current_member.id, db)
    if balance < payload.quantity:
        raise HTTPException(status_code=400, detail=f"Insufficient coupon balance. Available: {balance}")

    notes_out = payload.notes or f"Transfer to {recipient.partner_code}"
    notes_in  = f"Transfer from {current_member.partner_code}" + (f" — {payload.notes}" if payload.notes else "")
    try:
        db.execute(text(
            "INSERT INTO vgk_coupon_ledger (partner_id, transaction_type, quantity, related_partner_id, notes, created_at) "
            "VALUES (:pid, 'transfer_out', :qty, :rpid, :notes, NOW())"
        ), {"pid": current_member.id, "qty": payload.quantity, "rpid": recipient.id, "notes": notes_out})
        db.execute(text(
            "INSERT INTO vgk_coupon_ledger (partner_id, transaction_type, quantity, related_partner_id, notes, created_at) "
            "VALUES (:pid, 'transfer_in', :qty, :rpid, :notes, NOW())"
        ), {"pid": recipient.id, "qty": payload.quantity, "rpid": current_member.id, "notes": notes_in})
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Transfer failed: {e}")
    return {
        "success": True,
        "message": f"{payload.quantity} coupon(s) transferred to {recipient.partner_name} ({recipient.partner_code}).",
        "data": {
            "new_balance": balance - payload.quantity,
            "monthly_transfer_used": monthly_used + payload.quantity,
            "monthly_transfer_remaining": max(0, _MONTHLY_TRANSFER_LIMIT - monthly_used - payload.quantity),
        }
    }


@router.post("/member/coupons/activate-member")
def vgk_member_activate_other(
    request: Request,
    payload: VGKActivateMemberRequest,
    db: Session = Depends(get_db)
):
    from app.api.v1.endpoints.vgk_auth import get_current_vgk_member
    current_member = get_current_vgk_member(request, db)
    # Find target
    target = db.query(OfficialPartner).filter(
        OfficialPartner.partner_code == payload.target_vgk_id.strip().upper(),
        OfficialPartner.category == 'VGK_TEAM'
    ).first()
    if not target:
        raise HTTPException(status_code=404, detail="Target VGK member not found")
    if target.id == current_member.id:
        raise HTTPException(status_code=400, detail="Cannot activate yourself with this method")
    if target.vgk_activated_at:
        raise HTTPException(status_code=400, detail=f"{target.partner_code} is already activated")
    # Check balance
    balance = _get_coupon_balance(current_member.id, db)
    if balance < 1:
        raise HTTPException(status_code=400, detail="No coupons available. Purchase coupons first.")
    # Check no pending activation request for this target
    try:
        pending = db.execute(text(
            "SELECT id FROM vgk_member_activation_requests WHERE target_partner_id = :tid AND status = 'PENDING' LIMIT 1"
        ), {"tid": target.id}).scalar()
        if pending:
            raise HTTPException(status_code=400, detail=f"{target.partner_code} already has a pending activation request")
        # Debit coupon from activating member (hold — pending staff approval)
        ledger_id = db.execute(text(
            "INSERT INTO vgk_coupon_ledger (partner_id, transaction_type, quantity, related_partner_id, notes, created_at) "
            "VALUES (:pid, 'activation_used', 1, :tpid, :notes, NOW()) RETURNING id"
        ), {"pid": current_member.id, "tpid": target.id,
            "notes": f"Coupon used to activate {target.partner_code} — pending staff approval"}).scalar()
        # Create activation request
        db.execute(text(
            "INSERT INTO vgk_member_activation_requests "
            "(requesting_partner_id, target_partner_id, coupon_ledger_id, status, notes, created_at, updated_at) "
            "VALUES (:rid, :tid, :lid, 'PENDING', :notes, NOW(), NOW())"
        ), {"rid": current_member.id, "tid": target.id, "lid": ledger_id,
            "notes": payload.notes or f"Activation requested by {current_member.partner_code}"})
        db.commit()
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Activation request failed: {e}")
    return {
        "success": True,
        "message": f"Activation request submitted for {target.partner_name} ({target.partner_code}). Staff will review and credit 50,000 points upon approval.",
        "data": {"new_balance": balance - 1}
    }


@router.get("/member/coupons/activation-requests")
def vgk_member_activation_requests(
    request: Request,
    db: Session = Depends(get_db)
):
    from app.api.v1.endpoints.vgk_auth import get_current_vgk_member
    current_member = get_current_vgk_member(request, db)
    try:
        rows = db.execute(text(
            "SELECT r.id, r.status, r.notes, r.created_at, r.updated_at, r.rejection_reason, "
            "op.partner_code AS target_code, op.partner_name AS target_name "
            "FROM vgk_member_activation_requests r "
            "JOIN official_partners op ON op.id = r.target_partner_id "
            "WHERE r.requesting_partner_id = :pid ORDER BY r.created_at DESC LIMIT 50"
        ), {"pid": current_member.id}).fetchall()
        results = [dict(r._mapping) for r in rows]
        for r in results:
            for k in ('created_at', 'updated_at'):
                if r.get(k):
                    r[k] = r[k].isoformat()
    except Exception:
        results = []
    return {"success": True, "data": results}


# ============= VGK Coupon Staff Portal =============


@router.get("/coupons/purchase-requests")
def staff_list_coupon_purchase_requests(
    status_filter: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """List all VGK coupon purchase requests (staff view)."""
    from app.api.v1.endpoints.staff_mnr_user_sidebar import check_mnr_user_access
    if not check_mnr_user_access(db, current_user, 'vgk_coupons', require_edit=False):
        raise HTTPException(status_code=403, detail="Access denied")
    status_clause = "AND p.status = :sf" if status_filter else ""
    params: dict = {"lim": page_size, "off": (page-1)*page_size}
    if status_filter:
        params["sf"] = status_filter.upper()
    total = db.execute(text(
        f"SELECT COUNT(*) FROM vgk_coupon_purchases p {status_clause.replace('AND ', 'WHERE ')}"
    ), params).scalar() or 0
    rows = db.execute(text(
        f"SELECT p.id, p.partner_id, p.quantity, p.bonus_quantity, p.unit_price, p.total_amount, "
        f"p.payment_method, p.transaction_ref, p.payment_proof_url, p.payment_notes, p.status, "
        f"p.rejection_reason, p.created_at, p.approved_at, "
        f"op.partner_code, op.partner_name, op.phone "
        f"FROM vgk_coupon_purchases p "
        f"JOIN official_partners op ON op.id = p.partner_id "
        f"{'WHERE p.status = :sf' if status_filter else ''} "
        f"ORDER BY p.created_at DESC LIMIT :lim OFFSET :off"
    ), params).fetchall()
    data = []
    for r in rows:
        d = dict(r._mapping)
        for k in ('created_at', 'approved_at'):
            if d.get(k):
                d[k] = d[k].isoformat()
        data.append(d)
    return {"success": True, "total": int(total), "page": page, "page_size": page_size, "data": data}


@router.post("/coupons/purchase-requests/{purchase_id}/approve")
def staff_approve_coupon_purchase(
    purchase_id: int = Path(...),
    staff_notes: Optional[str] = Body(None, embed=True),
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """Approve a VGK coupon purchase request.
    Creates two separate ledger entries:
      - purchase_credit (base quantity)
      - bonus_credit (bonus quantity, if > 0)
    No cash payments are tracked here — coupons are activation credits only.
    """
    from app.api.v1.endpoints.staff_mnr_user_sidebar import check_mnr_user_access, log_staff_action
    if not check_mnr_user_access(db, current_user, 'vgk_coupons', require_edit=True):
        raise HTTPException(status_code=403, detail="Access denied")
    purchase = db.execute(text(
        "SELECT id, partner_id, quantity, bonus_quantity, total_amount, status "
        "FROM vgk_coupon_purchases WHERE id = :pid"
    ), {"pid": purchase_id}).first()
    if not purchase:
        raise HTTPException(status_code=404, detail="Purchase request not found")
    if purchase.status != 'PENDING':
        raise HTTPException(status_code=400, detail=f"Purchase is already {purchase.status}")
    partner = db.query(OfficialPartner).filter(OfficialPartner.id == purchase.partner_id).first()
    if not partner:
        raise HTTPException(status_code=404, detail="Partner not found")
    try:
        # Create purchase_credit entry for base quantity
        note_base = f"Purchase approved by staff {current_user.emp_code} — {purchase.quantity} coupons"
        if staff_notes:
            note_base += f" | {staff_notes}"
        db.execute(text(
            "INSERT INTO vgk_coupon_ledger "
            "(partner_id, transaction_type, quantity, purchase_id, notes, created_at) "
            "VALUES (:pid, 'purchase_credit', :qty, :purch_id, :notes, NOW())"
        ), {"pid": purchase.partner_id, "qty": purchase.quantity,
            "purch_id": purchase.id, "notes": note_base})
        # Create separate bonus_credit entry if bonus > 0
        if purchase.bonus_quantity > 0:
            note_bonus = (
                f"Bonus coupons (20+2 offer) — {purchase.bonus_quantity} bonus "
                f"for purchase of {purchase.quantity} coupons"
            )
            db.execute(text(
                "INSERT INTO vgk_coupon_ledger "
                "(partner_id, transaction_type, quantity, purchase_id, notes, created_at) "
                "VALUES (:pid, 'bonus_credit', :qty, :purch_id, :notes, NOW())"
            ), {"pid": purchase.partner_id, "qty": purchase.bonus_quantity,
                "purch_id": purchase.id, "notes": note_bonus})
        # Mark purchase as approved
        db.execute(text(
            "UPDATE vgk_coupon_purchases SET status='APPROVED', approved_by=:ab, approved_at=NOW(), updated_at=NOW() "
            "WHERE id=:id"
        ), {"ab": current_user.id, "id": purchase.id})
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Approval failed: {e}")

    try:
        from app.services.vgk_commission import process_held_commissions
        process_held_commissions(db, partner.id)
    except Exception as _hc:
        logger.warning(f"[VGK-COUPON-APPROVE] process_held_commissions failed for {partner.partner_code}: {_hc}")

    total_credited = purchase.quantity + purchase.bonus_quantity
    log_staff_action(db, current_user.id, current_user.emp_code, partner.partner_code,
                     'VGK_COUPON_PURCHASE_APPROVE',
                     f'Approved coupon purchase #{purchase_id} for {partner.partner_code}: '
                     f'{purchase.quantity} + {purchase.bonus_quantity} bonus = {total_credited} total',
                     '/staff/vgk/coupons/available')
    return {
        "success": True,
        "message": f"Purchase approved. {purchase.quantity} coupons + {purchase.bonus_quantity} bonus = {total_credited} total credited to {partner.partner_code}.",
        "data": {
            "purchase_id": purchase.id,
            "partner_code": partner.partner_code,
            "purchase_credit": purchase.quantity,
            "bonus_credit": purchase.bonus_quantity,
            "total_credited": total_credited,
        }
    }


@router.post("/coupons/purchase-requests/{purchase_id}/reject")
def staff_reject_coupon_purchase(
    purchase_id: int = Path(...),
    rejection_reason: str = Body(..., embed=True),
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """Reject a VGK coupon purchase request."""
    from app.api.v1.endpoints.staff_mnr_user_sidebar import check_mnr_user_access, log_staff_action
    if not check_mnr_user_access(db, current_user, 'vgk_coupons', require_edit=True):
        raise HTTPException(status_code=403, detail="Access denied")
    purchase = db.execute(text(
        "SELECT id, partner_id, quantity, status FROM vgk_coupon_purchases WHERE id = :pid"
    ), {"pid": purchase_id}).first()
    if not purchase:
        raise HTTPException(status_code=404, detail="Purchase request not found")
    if purchase.status != 'PENDING':
        raise HTTPException(status_code=400, detail=f"Purchase is already {purchase.status}")
    partner = db.query(OfficialPartner).filter(OfficialPartner.id == purchase.partner_id).first()
    try:
        db.execute(text(
            "UPDATE vgk_coupon_purchases SET status='REJECTED', rejection_reason=:reason, "
            "approved_by=:ab, approved_at=NOW(), updated_at=NOW() WHERE id=:id"
        ), {"reason": rejection_reason, "ab": current_user.id, "id": purchase.id})
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Rejection failed: {e}")
    if partner:
        log_staff_action(db, current_user.id, current_user.emp_code, partner.partner_code,
                         'VGK_COUPON_PURCHASE_REJECT',
                         f'Rejected coupon purchase #{purchase_id} for {partner.partner_code}: {rejection_reason}',
                         '/staff/vgk/coupons/available')
    return {"success": True, "message": f"Purchase request #{purchase_id} rejected.", "data": {"purchase_id": purchase.id}}


@router.get("/coupons/search-member")
def vgk_coupon_search_member(
    code: str = Query(..., min_length=3),
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    from app.api.v1.endpoints.staff_mnr_user_sidebar import check_mnr_user_access
    if not check_mnr_user_access(db, current_user, 'vgk_coupons', require_edit=False):
        raise HTTPException(status_code=403, detail="Access denied")
    partner = db.query(OfficialPartner).filter(
        OfficialPartner.partner_code == code.strip().upper(),
        OfficialPartner.category == 'VGK_TEAM'
    ).first()
    if not partner:
        raise HTTPException(status_code=404, detail="VGK member not found")
    return {
        "success": True,
        "data": {
            "id": partner.id,
            "partner_code": partner.partner_code,
            "partner_name": partner.partner_name,
            "phone": partner.phone,
            "is_active": partner.is_active,
            "vgk_activated_at": partner.vgk_activated_at.isoformat() if partner.vgk_activated_at else None,
            "vgk_points_balance": float(partner.vgk_points_balance or 0),
            "kyc_status": partner.kyc_status,
        }
    }


@router.post("/coupons/buy-pin")
def vgk_coupon_buy_pin(
    partner_code: str = Body(..., embed=True),
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    from app.api.v1.endpoints.staff_mnr_user_sidebar import check_mnr_user_access
    if not check_mnr_user_access(db, current_user, 'vgk_coupons', require_edit=True):
        raise HTTPException(status_code=403, detail="Access denied")
    partner = db.query(OfficialPartner).filter(
        OfficialPartner.partner_code == partner_code.strip().upper(),
        OfficialPartner.category == 'VGK_TEAM'
    ).first()
    if not partner:
        raise HTTPException(status_code=404, detail="VGK member not found")
    if partner.is_active:
        raise HTTPException(status_code=400, detail="Member is already activated. Cannot buy another PIN.")
    existing_pending = db.query(VGKTeamIncomeEntry).filter(
        VGKTeamIncomeEntry.partner_id == partner.id,
        VGKTeamIncomeEntry.level == 0,
        VGKTeamIncomeEntry.status == 'PENDING',
        VGKTeamIncomeEntry.notes.like('%PIN purchased%')
    ).first()
    if existing_pending:
        raise HTTPException(status_code=400, detail=f"A pending PIN already exists for this member (ref: {existing_pending.entry_number})")

    now = get_indian_time()
    entry_no = _next_vgk_entry_number(db, partner.company_id or 1, prefix="VGK-PIN")
    pin_entry = VGKTeamIncomeEntry(
        company_id=partner.company_id or 1,
        entry_number=entry_no,
        partner_id=partner.id,
        source_lead_id=None,
        source_transaction_id=None,
        category_id=None,
        level=0,
        revenue_amount=Decimal('5000'),
        commission_pct=Decimal('0'),
        commission_amount=Decimal('0'),
        bonus_amount=Decimal('0'),
        status='PENDING',
        notes=f'5K PIN purchased offline by staff {current_user.emp_code}',
        confirmed_at=None,
        confirmed_by=None,
        created_at=now,
        updated_at=now
    )
    db.add(pin_entry)
    db.commit()
    db.refresh(pin_entry)

    from app.api.v1.endpoints.staff_mnr_user_sidebar import log_staff_action
    log_staff_action(db, current_user.id, current_user.emp_code, partner_code,
                     'VGK_PIN_PURCHASE', f'5K PIN purchased for {partner_code}, entry {entry_no}',
                     '/staff/vgk/coupons/available')

    logger.info(f"[VGK-PIN] PIN bought for {partner_code} by staff {current_user.emp_code}, entry {entry_no}")
    return {"success": True, "message": f"5K PIN purchased for {partner_code}", "entry_number": entry_no, "entry_id": pin_entry.id}


@router.post("/coupons/activate-pin")
def vgk_coupon_activate_pin(
    partner_code: str = Body(..., embed=True),
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    from app.api.v1.endpoints.staff_mnr_user_sidebar import check_mnr_user_access
    if not check_mnr_user_access(db, current_user, 'vgk_coupons', require_edit=True):
        raise HTTPException(status_code=403, detail="Access denied")
    from app.services.vgk_commission import activate_vgk_member
    partner = db.query(OfficialPartner).filter(
        OfficialPartner.partner_code == partner_code.strip().upper(),
        OfficialPartner.category == 'VGK_TEAM'
    ).first()
    if not partner:
        raise HTTPException(status_code=404, detail="VGK member not found")
    if partner.is_active and partner.is_paid_activation:
        raise HTTPException(status_code=400, detail="Member is already paid-activated.")

    pending_pin = db.query(VGKTeamIncomeEntry).filter(
        VGKTeamIncomeEntry.partner_id == partner.id,
        VGKTeamIncomeEntry.level == 0,
        VGKTeamIncomeEntry.status == 'PENDING',
        VGKTeamIncomeEntry.notes.like('%PIN purchased%')
    ).first()
    if not pending_pin:
        raise HTTPException(status_code=400, detail="No pending 5K PIN found for this member. Buy a PIN first.")

    pending_pin.status = 'CONFIRMED'
    pending_pin.confirmed_at = get_indian_time()
    pending_pin.confirmed_by = current_user.id
    pending_pin.updated_at = get_indian_time()

    result = activate_vgk_member(db, partner.id, partner.company_id or 1, current_user.id)
    if not result:
        raise HTTPException(status_code=500, detail="Activation failed. Check logs.")

    from app.api.v1.endpoints.staff_mnr_user_sidebar import log_staff_action
    log_staff_action(db, current_user.id, current_user.emp_code, partner_code,
                     'VGK_PIN_ACTIVATE', f'VGK PIN paid-activated for {partner_code}, 50000 points credited (total 60,000)',
                     '/staff/vgk/coupons/available')

    logger.info(f"[VGK-PIN] PIN paid-activated for {partner_code} by staff {current_user.emp_code}")
    return {"success": True, "message": f"VGK member {partner_code} paid-activated — 50,000 points credited (total 60,000)"}


@router.post("/staff/manual-activate/{partner_code}")
def vgk_staff_manual_activate(
    partner_code: str,
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db),
):
    """
    DC-VGK-MANUAL-ACTIVATE-001: Staff-initiated VGK activation — same effect as PIN activation.
    Restricted to: emp_code MR10001  OR  (Accounts department AND full_name contains Subhash).
    No PIN purchase required — admin override path.
    """
    _emp = (getattr(current_user, 'emp_code', '') or '').strip().upper()
    _dept = str(getattr(current_user, 'department', '') or '').lower()
    _name = (getattr(current_user, 'full_name', '') or getattr(current_user, 'name', '') or '').lower()
    _allowed = _emp == 'MR10001' or ('account' in _dept and 'subhash' in _name)
    if not _allowed:
        raise HTTPException(
            status_code=403,
            detail="Access denied. Manual VGK activation is restricted to MR10001 and Accounts dept (Subhash) only.",
        )

    partner = db.query(OfficialPartner).filter(
        OfficialPartner.partner_code == partner_code.strip().upper(),
        OfficialPartner.category == 'VGK_TEAM',
    ).first()
    if not partner:
        raise HTTPException(status_code=404, detail=f"VGK member '{partner_code}' not found.")
    if partner.is_active and partner.is_paid_activation:
        raise HTTPException(status_code=400, detail="Member is already activated.")

    from app.services.vgk_commission import activate_vgk_member
    result = activate_vgk_member(db, partner.id, partner.company_id or 1, current_user.id)
    if not result:
        raise HTTPException(status_code=500, detail="Activation failed. Check server logs.")

    try:
        from app.api.v1.endpoints.staff_mnr_user_sidebar import log_staff_action
        log_staff_action(
            db, current_user.id, current_user.emp_code, partner_code,
            'VGK_MANUAL_ACTIVATE',
            f'DC-VGK-MANUAL-ACTIVATE-001: {partner_code} manually activated by {current_user.emp_code} — 50,000 pts credited',
            '/staff/vgk/members',
        )
    except Exception as _ae:
        logger.warning(f"[DC-VGK-MANUAL-ACTIVATE-001] Audit log failed (non-fatal): {_ae}")

    logger.info(f"[DC-VGK-MANUAL-ACTIVATE-001] {partner_code} activated by {current_user.emp_code}")
    return {
        "success": True,
        "partner_code": partner_code.strip().upper(),
        "message": f"{partner_code.strip().upper()} successfully activated — 50,000 VGK points credited (total 60,000 with registration bonus).",
    }


@router.post("/coupons/issue-loyal-coupon")
def vgk_issue_loyal_coupon(
    partner_code: str = Body(..., embed=True),
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """
    DC Protocol Mar 2026: Issue Loyal Coupon to a VGK member.
    Access: VGK Mentor staff only (vgk_role == 'VGK_MENTOR').
    Rules:
    - Member must be VGK_TEAM and not yet activated.
    - One-time only per member.
    - Credits 50,000 VGK Discount Credits (LOYAL_BONUS) → total 60,000 with registration bonus.
    - Commission on future deals: only L1 (self) and L2 (support) earn — L3 and L4 excluded.
    - Member counts as +1 in all team/awards/bonanza counts.
    """
    from app.api.v1.endpoints.staff_mnr_user_sidebar import check_mnr_user_access
    if not check_mnr_user_access(db, current_user, 'vgk_coupons', require_edit=True):
        raise HTTPException(status_code=403, detail="Access denied. Only authorised VGK staff can issue Loyal Coupons.")

    from app.services.vgk_commission import activate_loyal_coupon_member

    partner = db.query(OfficialPartner).filter(
        OfficialPartner.partner_code == partner_code.strip().upper(),
        OfficialPartner.category == 'VGK_TEAM'
    ).first()
    if not partner:
        raise HTTPException(status_code=404, detail="VGK member not found")

    if partner.is_loyal_coupon:
        raise HTTPException(
            status_code=400,
            detail="Loyal Coupon has already been issued to this member. One-time only."
        )

    if partner.is_active:
        raise HTTPException(
            status_code=400,
            detail="Member is already activated. Loyal Coupon can only be applied to inactive members."
        )

    result = activate_loyal_coupon_member(db, partner.id, partner.company_id or 1, current_user.id)
    if not result:
        raise HTTPException(status_code=500, detail="Loyal Coupon activation failed. Check server logs.")

    from app.api.v1.endpoints.staff_mnr_user_sidebar import log_staff_action
    log_staff_action(
        db, current_user.id, current_user.emp_code, partner_code,
        'VGK_LOYAL_COUPON',
        f'Loyal Coupon issued for {partner_code} by VGK Mentor {current_user.emp_code}, 50000 points credited (total 60,000)',
        '/staff/vgk/coupons/available'
    )

    logger.info(f"[VGK-LOYAL] Loyal Coupon issued for {partner_code} by VGK Mentor {current_user.emp_code}")
    return {
        "success": True,
        "message": f"Loyal Coupon issued. {partner_code} is now activated with 50,000 VGK Discount Credits (total 60,000).",
        "partner_code": partner_code,
        "points_credited": 50000,
    }


@router.get("/pin-requests")
def list_vgk_pin_requests(
    status_filter: str = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    from app.api.v1.endpoints.staff_mnr_user_sidebar import check_mnr_user_access
    if not check_mnr_user_access(db, current_user, 'vgk_coupons', require_edit=False):
        raise HTTPException(status_code=403, detail="Access denied")
    query = db.query(VGKPINPurchaseRequest)
    if status_filter:
        query = query.filter(VGKPINPurchaseRequest.status == status_filter.upper())
    total = query.count()
    requests = query.order_by(VGKPINPurchaseRequest.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

    items = []
    partner_ids = [r.partner_id for r in requests]
    partners = {p.id: p for p in db.query(OfficialPartner).filter(OfficialPartner.id.in_(partner_ids)).all()} if partner_ids else {}
    for r in requests:
        d = r.to_dict()
        p = partners.get(r.partner_id)
        d['partner_code'] = p.partner_code if p else None
        d['partner_name'] = p.partner_name if p else None
        d['partner_phone'] = p.phone if p else None
        d['is_active'] = p.is_active if p else None
        items.append(d)

    return {"success": True, "total": total, "page": page, "page_size": page_size, "data": items}


@router.post("/pin-requests/{request_id}/approve")
def approve_vgk_pin_request(
    request_id: int = Path(...),
    staff_notes: str = Body(None, embed=True),
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    from app.api.v1.endpoints.staff_mnr_user_sidebar import check_mnr_user_access, log_staff_action
    if not check_mnr_user_access(db, current_user, 'vgk_coupons', require_edit=True):
        raise HTTPException(status_code=403, detail="Access denied")
    pin_req = db.query(VGKPINPurchaseRequest).filter(VGKPINPurchaseRequest.id == request_id).first()
    if not pin_req:
        raise HTTPException(status_code=404, detail="PIN purchase request not found")
    if pin_req.status != 'PENDING':
        raise HTTPException(status_code=400, detail=f"Request is already {pin_req.status}")

    partner = db.query(OfficialPartner).filter(OfficialPartner.id == pin_req.partner_id).first()
    if not partner:
        raise HTTPException(status_code=404, detail="VGK member not found")
    if partner.is_active and partner.is_paid_activation:
        raise HTTPException(status_code=400, detail="Member is already paid-activated")

    from app.services.vgk_commission import activate_vgk_member
    activate_vgk_member(db, partner.id, partner.company_id or 1, current_user.id)

    pin_req.status = 'APPROVED'
    pin_req.approved_by = current_user.id
    pin_req.approved_at = get_indian_time()
    pin_req.staff_notes = staff_notes
    pin_req.updated_at = get_indian_time()
    db.commit()

    log_staff_action(db, current_user.id, current_user.emp_code, partner.partner_code,
                     'VGK_PIN_REQ_APPROVE', f'Approved PIN purchase request #{request_id} for {partner.partner_code}, 50000 points credited (total 60,000)',
                     '/staff/vgk/coupons/available')

    logger.info(f"[VGK-PIN-REQ] Request #{request_id} approved for {partner.partner_code} by {current_user.emp_code}")
    return {"success": True, "message": f"PIN request approved. {partner.partner_code} paid-activated — 50,000 points credited (total 60,000)."}


@router.post("/pin-requests/{request_id}/reject")
def reject_vgk_pin_request(
    request_id: int = Path(...),
    rejection_reason: str = Body(..., embed=True),
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    from app.api.v1.endpoints.staff_mnr_user_sidebar import check_mnr_user_access, log_staff_action
    if not check_mnr_user_access(db, current_user, 'vgk_coupons', require_edit=True):
        raise HTTPException(status_code=403, detail="Access denied")
    pin_req = db.query(VGKPINPurchaseRequest).filter(VGKPINPurchaseRequest.id == request_id).first()
    if not pin_req:
        raise HTTPException(status_code=404, detail="PIN purchase request not found")
    if pin_req.status != 'PENDING':
        raise HTTPException(status_code=400, detail=f"Request is already {pin_req.status}")

    partner = db.query(OfficialPartner).filter(OfficialPartner.id == pin_req.partner_id).first()
    pin_req.status = 'REJECTED'
    pin_req.rejection_reason = rejection_reason.strip()
    pin_req.approved_by = current_user.id
    pin_req.approved_at = get_indian_time()
    pin_req.updated_at = get_indian_time()
    db.commit()

    log_staff_action(db, current_user.id, current_user.emp_code,
                     partner.partner_code if partner else str(pin_req.partner_id),
                     'VGK_PIN_REQ_REJECT', f'Rejected PIN purchase request #{request_id}: {rejection_reason}',
                     '/staff/vgk/coupons/available')

    logger.info(f"[VGK-PIN-REQ] Request #{request_id} rejected by {current_user.emp_code}: {rejection_reason}")
    return {"success": True, "message": "PIN request rejected."}


# ═══════════════════════════════════════════════════════════════════════════════
# VGK PROMO CODES — Staff CRUD  (DC Protocol Apr 2026)
# ═══════════════════════════════════════════════════════════════════════════════

from app.models.staff_accounts import VGKPromoCode, VGKPromoRedemption


class PromoCodeCreate(BaseModel):
    code: str = Field(..., min_length=2, max_length=50)
    label: Optional[str] = None
    promo_type: str = Field('GENERAL')
    points_credit: float = Field(..., ge=0)
    tier_config: Optional[list] = None
    status: str = Field('ACTIVE')
    valid_from: Optional[str] = None
    valid_to: Optional[str] = None
    usage_limit: Optional[int] = None
    applicability_timing: Optional[str] = Field('BOTH')
    applicability_status: Optional[str] = Field('ALL')


class PromoCodeUpdate(BaseModel):
    label: Optional[str] = None
    promo_type: Optional[str] = None
    points_credit: Optional[float] = None
    tier_config: Optional[list] = None
    status: Optional[str] = None
    valid_from: Optional[str] = None
    valid_to: Optional[str] = None
    usage_limit: Optional[int] = None
    applicability_timing: Optional[str] = None
    applicability_status: Optional[str] = None


def _parse_dt(s):
    if not s:
        return None
    try:
        return datetime.fromisoformat(s)
    except Exception:
        return None


@router.get("/promo-codes")
def list_vgk_promo_codes(
    search: Optional[str] = Query(None),
    promo_type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db),
):
    company_id = _get_staff_company_id(current_user)
    q = db.query(VGKPromoCode).filter(VGKPromoCode.company_id == company_id)
    if search:
        q = q.filter(or_(
            VGKPromoCode.code.ilike(f'%{search}%'),
            VGKPromoCode.label.ilike(f'%{search}%'),
        ))
    if promo_type:
        q = q.filter(VGKPromoCode.promo_type == promo_type.upper())
    if status:
        q = q.filter(VGKPromoCode.status == status.upper())
    total = q.count()
    codes = q.order_by(VGKPromoCode.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return {
        "success": True,
        "total": total,
        "page": page,
        "page_size": page_size,
        "data": [c.to_dict() for c in codes],
    }


@router.post("/promo-codes")
def create_vgk_promo_code(
    body: PromoCodeCreate,
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db),
):
    company_id = _get_staff_company_id(current_user)
    promo_type = (body.promo_type or 'GENERAL').upper()
    if promo_type not in ('GENERAL', 'MNR_MEMBER', 'ETC_STUDENT'):
        raise HTTPException(status_code=400, detail="Invalid promo_type")
    status = (body.status or 'ACTIVE').upper()
    if status not in ('ACTIVE', 'PAUSED', 'INACTIVE'):
        raise HTTPException(status_code=400, detail="Invalid status")
    code_upper = body.code.strip().upper()
    existing = db.query(VGKPromoCode).filter(VGKPromoCode.code == code_upper).first()
    if existing:
        raise HTTPException(status_code=409, detail="A promo code with this code already exists")
    tier_cfg = body.tier_config if promo_type == 'ETC_STUDENT' else None
    appl_timing = (body.applicability_timing or 'BOTH').upper()
    if appl_timing not in ('EXISTING', 'NEW', 'BOTH'):
        raise HTTPException(status_code=400, detail="applicability_timing must be EXISTING, NEW, or BOTH")
    appl_status = (body.applicability_status or 'ALL').upper()
    if appl_status not in ('ACTIVATED', 'ALL'):
        raise HTTPException(status_code=400, detail="applicability_status must be ACTIVATED or ALL")
    pc = VGKPromoCode(
        code=code_upper,
        label=body.label,
        promo_type=promo_type,
        points_credit=body.points_credit,
        tier_config=tier_cfg,
        status=status,
        valid_from=_parse_dt(body.valid_from),
        valid_to=_parse_dt(body.valid_to),
        usage_limit=body.usage_limit,
        applicability_timing=appl_timing,
        applicability_status=appl_status,
        company_id=company_id,
        created_by=current_user.id,
    )
    db.add(pc)
    db.commit()
    db.refresh(pc)
    logger.info(f"[VGK-PROMO] Created code {code_upper} [{promo_type}] by {current_user.emp_code}")
    return {"success": True, "data": pc.to_dict()}


@router.put("/promo-codes/{code_id}")
def update_vgk_promo_code(
    code_id: int = Path(...),
    body: PromoCodeUpdate = Body(...),
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db),
):
    company_id = _get_staff_company_id(current_user)
    pc = db.query(VGKPromoCode).filter(VGKPromoCode.id == code_id, VGKPromoCode.company_id == company_id).first()
    if not pc:
        raise HTTPException(status_code=404, detail="Promo code not found")
    if body.label is not None:
        pc.label = body.label
    if body.promo_type is not None:
        pt = body.promo_type.upper()
        if pt not in ('GENERAL', 'MNR_MEMBER', 'ETC_STUDENT'):
            raise HTTPException(status_code=400, detail="Invalid promo_type")
        pc.promo_type = pt
    if body.points_credit is not None:
        pc.points_credit = body.points_credit
    if body.tier_config is not None:
        pc.tier_config = body.tier_config
    if body.status is not None:
        st = body.status.upper()
        if st not in ('ACTIVE', 'PAUSED', 'INACTIVE'):
            raise HTTPException(status_code=400, detail="Invalid status")
        pc.status = st
    if body.valid_from is not None:
        pc.valid_from = _parse_dt(body.valid_from)
    if body.valid_to is not None:
        pc.valid_to = _parse_dt(body.valid_to)
    if body.usage_limit is not None:
        pc.usage_limit = body.usage_limit
    if body.applicability_timing is not None:
        at = body.applicability_timing.upper()
        if at not in ('EXISTING', 'NEW', 'BOTH'):
            raise HTTPException(status_code=400, detail="applicability_timing must be EXISTING, NEW, or BOTH")
        pc.applicability_timing = at
    if body.applicability_status is not None:
        as_ = body.applicability_status.upper()
        if as_ not in ('ACTIVATED', 'ALL'):
            raise HTTPException(status_code=400, detail="applicability_status must be ACTIVATED or ALL")
        pc.applicability_status = as_
    pc.updated_at = get_indian_time()
    db.commit()
    db.refresh(pc)
    logger.info(f"[VGK-PROMO] Updated code #{code_id} by {current_user.emp_code}")
    return {"success": True, "data": pc.to_dict()}


@router.delete("/promo-codes/{code_id}")
def delete_vgk_promo_code(
    code_id: int = Path(...),
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db),
):
    company_id = _get_staff_company_id(current_user)
    pc = db.query(VGKPromoCode).filter(VGKPromoCode.id == code_id, VGKPromoCode.company_id == company_id).first()
    if not pc:
        raise HTTPException(status_code=404, detail="Promo code not found")
    if pc.times_used and pc.times_used > 0:
        raise HTTPException(status_code=409, detail=f"Cannot delete — code has been redeemed {pc.times_used} time(s). Pause or deactivate it instead.")
    db.delete(pc)
    db.commit()
    logger.info(f"[VGK-PROMO] Deleted code #{code_id} by {current_user.emp_code}")
    return {"success": True, "message": "Promo code deleted"}


@router.post("/promo-codes/{code_id}/set-status")
def set_vgk_promo_code_status(
    code_id: int = Path(...),
    new_status: str = Body(..., embed=True),
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db),
):
    company_id = _get_staff_company_id(current_user)
    pc = db.query(VGKPromoCode).filter(VGKPromoCode.id == code_id, VGKPromoCode.company_id == company_id).first()
    if not pc:
        raise HTTPException(status_code=404, detail="Promo code not found")
    st = new_status.upper()
    if st not in ('ACTIVE', 'PAUSED', 'INACTIVE'):
        raise HTTPException(status_code=400, detail="new_status must be ACTIVE, PAUSED, or INACTIVE")
    pc.status = st
    pc.updated_at = get_indian_time()
    db.commit()
    return {"success": True, "data": pc.to_dict()}


@router.get("/promo-codes/{code_id}/redemptions")
def list_promo_redemptions(
    code_id: int = Path(...),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db),
):
    company_id = _get_staff_company_id(current_user)
    pc = db.query(VGKPromoCode).filter(VGKPromoCode.id == code_id, VGKPromoCode.company_id == company_id).first()
    if not pc:
        raise HTTPException(status_code=404, detail="Promo code not found")
    q = db.query(VGKPromoRedemption, OfficialPartner).join(
        OfficialPartner, VGKPromoRedemption.partner_id == OfficialPartner.id
    ).filter(VGKPromoRedemption.promo_code_id == code_id)
    total = q.count()
    rows = q.order_by(VGKPromoRedemption.redeemed_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    result = []
    for r, p in rows:
        d = r.to_dict()
        d['partner_name'] = p.partner_name
        d['partner_code'] = p.partner_code
        result.append(d)
    return {"success": True, "total": total, "page": page, "data": result}


# ── DC-VGK-WA-SEND-001: Individual + Bulk WhatsApp Credential Sender ──────────

_vgk_wa_sent_today: dict = {}   # {member_id: datetime} — in-process 24h dedup


class VGKCredWASendPayload(BaseModel):
    template_id: Optional[int] = None
    custom_message: Optional[str] = None
    context: Optional[dict] = None


def _vgk_wa_build_message(name: str, code: str, points: float, password: Optional[str] = None) -> str:
    ref     = f"https://vgk4u.com/vgk/login?tab=signup&ref={code}"
    yt      = "https://www.youtube.com/@VGK4YOU"
    fp      = "https://vgk4u.com/vgk/forgot-password"
    bal     = f"{int(points):,}" if points == int(points) else f"{points:,.1f}"
    pwd_str = (password or "").strip() or code   # DC-VGK-WA-PWD-001: use actual password, not default code
    return (
        f"🎉 *Congratulations {name}! Welcome to VGK4U!* 🎉\n\n"
        f"Your VGK4U Partner account is *active and ready* to earn! 🚀\n\n"
        f"🔐 *Login Credentials:*\n"
        f"🌐 Portal: https://vgk4u.com/vgk/login\n"
        f"👤 Username: {code}\n"
        f"🔒 Password: {pwd_str}\n"
        f"📌 Your VGK4U ID: {code}\n\n"
        f"💰 *Your Points Balance: {bal} Points* 🎁\n\n"
        f"✨ *Ways to Earn & Grow:*\n"
        f"⚡ Solar Solutions  |  🛵 Electric Vehicles\n"
        f"🛡 Insurance  |  🏡 Real Estate & more\n\n"
        f"🔗 *Your Referral Link — Share & Earn:*\n{ref}\n\n"
        f"📖 *About VGK4U:* https://vgk4u.com/voffers\n\n"
        f"🔑 *Forgot Password?*\n{fp}\n\n"
        f"▶️ *Training & Income Strategies:*\n"
        f"{yt}\n"
        f"👉 Subscribe for updates, training & growth tips!\n\n"
        f"For support, contact MNR Team.\n"
        f"Best wishes from *Team VGK4U!* 🙏\n\n"
        f"📢 *Stay Connected — Join our WhatsApp Channels:*\n"
        f"💚 VGK4U: https://whatsapp.com/channel/0029Vb7Vb5f9cDDXf3zWtf0m\n"
        f"🔵 Myntreal: https://whatsapp.com/channel/0029VbCmSCh2kNFiA0RsHZ2r\n"
        f"☀️ Har Ghar Solar: https://whatsapp.com/channel/0029Vb7V0ImFCCoYg891FL3D"
    )


def _vgk_wa_can_send(member_id: int) -> bool:
    last = _vgk_wa_sent_today.get(member_id)
    if not last:
        return True
    return (datetime.utcnow() - last).total_seconds() > 86400


def _vgk_wa_find_template(db):
    """
    Look for a Meta-approved VGK-specific template for credential sends.
    Only returns VGK/welcome/credential/onboard templates — never a generic fallback,
    because sending with the wrong template causes Meta #132000 param-count errors.
    """
    try:
        from app.models.whatsapp import WhatsAppTemplate
        priority_keywords = ["vgk", "welcome", "credential", "onboard"]
        for kw in priority_keywords:
            t = db.query(WhatsAppTemplate).filter(
                WhatsAppTemplate.is_meta_approved == True,
                WhatsAppTemplate.is_active == True,
                WhatsAppTemplate.meta_template_name.ilike(f"%{kw}%"),
            ).first()
            if t:
                return t
        # No VGK template found — return None so caller falls back to free-form text
        return None
    except Exception:
        return None


@router.post("/members/{member_id}/send-credentials-wa")
def send_vgk_member_credentials_wa(
    member_id: int,
    payload: Optional[VGKCredWASendPayload] = None,
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db),
):
    """DC-VGK-WA-SEND-001: Send credentials message to a VGK member.
    Optional body: template_id, custom_message, context (variable values for template).
    Falls back to free-form credentials message when no body provided.
    """
    member = db.query(OfficialPartner).filter(OfficialPartner.id == member_id).first()
    if not member:
        raise HTTPException(status_code=404, detail="VGK member not found")

    phone = member.whatsapp_number or member.phone
    if not phone:
        raise HTTPException(status_code=400, detail="No phone number on this member record")

    if not _vgk_wa_can_send(member_id):
        return {
            "success": False,
            "reason": "already_sent_today",
            "message": "A credential message was already sent to this member in the last 24 hours.",
        }

    from app.services.whatsapp_auto_service import send_direct_whatsapp
    _name   = member.partner_name or "Partner"
    _code   = member.partner_code or ""
    _points = float(member.vgk_points_balance or 0)

    # Use custom message if provided, otherwise build credentials message
    if payload and payload.custom_message:
        msg = payload.custom_message
    else:
        msg = _vgk_wa_build_message(name=_name, code=_code, points=_points)

    # Build context — always include member vars so template variables resolve
    wa_context = {
        "name":      _name,
        "code":      _code,
        "points":    str(int(_points)),
        "login_url": "https://vgk4u.com/vgk/login",
    }
    if payload and payload.context:
        wa_context.update(payload.context)

    template_id = payload.template_id if payload else None

    result = send_direct_whatsapp(
        db=db, phone=phone, message=msg,
        staff_id=current_user.id,
        template_id=template_id,
        context=wa_context if template_id else None,
    )

    if result.get("success"):
        _vgk_wa_sent_today[member_id] = datetime.utcnow()
        return {
            "success": True,
            "message": f"WhatsApp sent to {_name} ({phone})",
            "wamid": result.get("wamid"),
        }

    reason = result.get("reason", "send_failed")
    reason_str = str(reason).lower()
    # True cold-outreach error: member hasn't messaged WA business number in 24h
    needs_template = any(kw in reason_str for kw in ["re-engagement", "131047", "131009"])
    return {
        "success": False,
        "reason": reason,
        "member_name": _name,
        "member_phone": phone,
        "needs_template": needs_template,
        "message": (
            f"{_name} ({phone}) is outside the 24h WhatsApp conversation window. "
            "They need to first message your WA business number, or use an approved Meta template."
            if needs_template else
            f"Could not send to {_name} ({phone}): {reason}"
        ),
    }


class BulkWASendRequest(BaseModel):
    target_filter: str = Field(..., description="all_active | never_logged_in | inactive_3_days | inactive_7_days | custom")
    member_ids: Optional[List[int]] = Field(None, description="Required when target_filter='custom'")


@router.post("/members/bulk-send-credentials-wa")
def bulk_send_vgk_credentials_wa(
    payload: BulkWASendRequest,
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db),
):
    """DC-VGK-WA-SEND-001: Bulk-send motivational credentials to filtered VGK members via Meta WA API."""
    from app.services.whatsapp_auto_service import send_direct_whatsapp
    from datetime import timedelta

    company_id = _get_staff_company_id(current_user)
    base_q = db.query(OfficialPartner).filter(
        OfficialPartner.company_id == company_id,
        OfficialPartner.is_active == True,
        (OfficialPartner.phone != None) | (OfficialPartner.whatsapp_number != None),
    )

    tf = payload.target_filter
    if tf == "all_active":
        members = base_q.all()
    elif tf == "never_logged_in":
        members = base_q.filter(
            (OfficialPartner.login_count == 0) | (OfficialPartner.login_count == None)
        ).all()
    elif tf == "inactive_3_days":
        cutoff = datetime.utcnow() - timedelta(days=3)
        members = base_q.filter(
            (OfficialPartner.last_login == None) | (OfficialPartner.last_login < cutoff)
        ).all()
    elif tf == "inactive_7_days":
        cutoff = datetime.utcnow() - timedelta(days=7)
        members = base_q.filter(
            (OfficialPartner.last_login == None) | (OfficialPartner.last_login < cutoff)
        ).all()
    elif tf == "custom":
        if not payload.member_ids:
            raise HTTPException(status_code=400, detail="member_ids required for custom filter")
        members = base_q.filter(OfficialPartner.id.in_(payload.member_ids)).all()
    else:
        raise HTTPException(status_code=400, detail="Unknown target_filter")

    # DC-VGK-WA-SEND-001: Resolve approved template once for the whole batch
    template = _vgk_wa_find_template(db)
    template_id = template.id if template else None
    using_template = bool(template_id)

    sent, failed, skipped, detail = 0, 0, 0, []
    for m in members:
        phone = m.whatsapp_number or m.phone
        if not phone:
            skipped += 1
            continue
        if not _vgk_wa_can_send(m.id):
            skipped += 1
            detail.append({"id": m.id, "code": m.partner_code, "status": "skipped_24h"})
            continue
        _bname   = m.partner_name or "Partner"
        _bcode   = m.partner_code or ""
        _bpoints = float(m.vgk_points_balance or 0)
        msg = _vgk_wa_build_message(name=_bname, code=_bcode, points=_bpoints)
        bulk_ctx = {
            "name":      _bname,
            "code":      _bcode,
            "points":    str(int(_bpoints)),
            "login_url": "https://vgk4u.com/vgk/login",
        }
        result = send_direct_whatsapp(db=db, phone=phone, message=msg, staff_id=current_user.id, template_id=template_id, context=bulk_ctx)
        if result.get("success"):
            _vgk_wa_sent_today[m.id] = datetime.utcnow()
            sent += 1
            detail.append({"id": m.id, "code": m.partner_code, "status": "submitted"})
        else:
            failed += 1
            detail.append({"id": m.id, "code": m.partner_code, "status": "failed", "reason": result.get("reason")})

    template_note = (
        f"✅ Used approved template '{template.meta_template_name}' for reliable delivery."
        if using_template else
        "⚠️ No approved Meta template found — messages sent as free-form text. "
        "These will only deliver to members who messaged your WA business number in the last 24 hours. "
        "For reliable outbound delivery, create a 'vgk_welcome' template in Meta Business Manager "
        "and mark it approved in your WA Config page."
    )

    return {
        "success": True,
        "submitted": sent,
        "failed": failed,
        "skipped": skipped,
        "total_matched": len(members),
        "using_template": using_template,
        "template_note": template_note,
        "detail": detail,
    }


# ─── DC-COMPANY-ROYALTY-001 / DC-COMPANY-PAYOUT-001 ──────────────────────────
# MR10001 and MR10025 exclusive: grant Company Side Royalty Points or record a
# gross paid earning (payout) for any VGK member.

_ROYALTY_ADMINS = {'MR10001', 'MR10025'}


class GrantRoyaltyPointsPayload(BaseModel):
    partner_id: int
    points: int = Field(..., gt=0, le=500000, description="Points to credit (1 pt = ₹1)")
    notes: str  = Field(..., min_length=1, max_length=500)


class RecordPayoutPayload(BaseModel):
    partner_id:  int
    gross_amount: float = Field(..., gt=0, description="Gross paid earning in ₹")
    notes:       str    = Field(..., min_length=1, max_length=500)


# Fixed deduction rates for company payouts (DC-COMPANY-PAYOUT-001)
_PAYOUT_ADMIN_PCT = Decimal('8')   # 8% admin charges
_PAYOUT_TDS_PCT   = Decimal('2')   # 2% TDS


@router.post("/staff/grant-royalty-points")
def grant_royalty_points(
    payload: GrantRoyaltyPointsPayload = Body(...),
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db),
):
    """
    [DC-COMPANY-ROYALTY-001] Grant Company Side Royalty Points to a VGK member.
    Restricted to MR10001 and MR10025 only.
    """
    if (current_user.emp_code or '').upper().strip() not in _ROYALTY_ADMINS:
        raise HTTPException(status_code=403, detail="Only MR10001 and MR10025 can grant Company Royalty Points")
    partner = db.query(OfficialPartner).filter(OfficialPartner.id == payload.partner_id).first()
    if not partner:
        raise HTTPException(status_code=404, detail="Member not found")
    from app.services.vgk_commission import add_vgk_points_entry
    entry = add_vgk_points_entry(
        db=db,
        partner_id=payload.partner_id,
        points_credit=Decimal(str(payload.points)),
        points_debit=Decimal('0'),
        reason_code='COMPANY_ROYALTY',
        notes=f"[Company Royalty] {payload.notes} | Granted by {(current_user.emp_code or '').upper()}",
        created_by=current_user.id,
    )
    db.commit()
    return {
        "success":       True,
        "message":       f"{payload.points:,} Company Royalty Points credited to {partner.partner_name}",
        "balance_after": float(entry.balance_after),
        "partner_code":  partner.partner_code,
    }


@router.post("/staff/record-payout")
def record_company_payout(
    payload: RecordPayoutPayload = Body(...),
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db),
):
    """
    [DC-COMPANY-PAYOUT-001] Record a gross paid earning (payout) for a VGK member.
    Fixed deductions: 8% admin charges + 2% TDS = 10% total. Net = gross x 90%.
    Creates COMPANY_PAYOUT wallet transaction and debits partner points by net amount.
    Restricted to MR10001 and MR10025 only.
    """
    import logging as _logging
    _log = _logging.getLogger(__name__)

    if (current_user.emp_code or '').upper().strip() not in _ROYALTY_ADMINS:
        raise HTTPException(status_code=403, detail="Only MR10001 and MR10025 can record Company Payouts")

    partner = db.query(OfficialPartner).filter(
        OfficialPartner.id == payload.partner_id
    ).with_for_update().first()
    if not partner:
        raise HTTPException(status_code=404, detail="Member not found")

    from app.models.staff_accounts import VGKCompanyPayout
    from app.models.vgk_wallet_transaction import VGKWalletTransaction

    gross         = Decimal(str(round(payload.gross_amount, 2)))
    admin_charges = (gross * _PAYOUT_ADMIN_PCT / Decimal('100')).quantize(Decimal('0.01'))
    tds_amount    = (gross * _PAYOUT_TDS_PCT   / Decimal('100')).quantize(Decimal('0.01'))
    net_amount    = (gross - admin_charges - tds_amount).quantize(Decimal('0.01'))
    now           = get_indian_time()

    # ── Save payout record (flush to get ID before wallet txn) ───────────
    payout = VGKCompanyPayout(
        company_id=partner.company_id,
        partner_id=partner.id,
        gross_amount=gross,
        admin_charges=admin_charges,
        tds_pct=_PAYOUT_TDS_PCT,
        tds_amount=tds_amount,
        net_amount=net_amount,
        notes=payload.notes,
        paid_by=current_user.id,
        paid_by_code=(current_user.emp_code or '').upper().strip(),
        created_at=now,
    )
    db.add(payout)
    db.flush()

    # ── Wallet: 2-transaction pattern (gross CR → deduction DR) ─────────────
    # This mirrors the solar-advance / slab-bonus pattern so that:
    #   • Total Earned Income (SUM of all CR txns) includes gross amount
    #   • Member wallet receives net (gross − admin − TDS)
    #   • COMPANY_PAYOUT_DEDUCT is hidden from the member's wallet view
    deductions     = admin_charges + tds_amount
    wallet_before  = partner.vgk_cash_wallet or Decimal('0')
    wallet_mid     = wallet_before  + gross      # after gross credit
    wallet_final   = wallet_mid     - deductions  # after deduction

    partner.vgk_cash_wallet = wallet_final
    partner.updated_at = now

    # CR: gross credited (visible — shows in wallet history as "Company Payout Credited")
    wt_cr = VGKWalletTransaction(
        company_id=partner.company_id,
        partner_id=partner.id,
        txn_type='COMPANY_PAYOUT',
        direction='CR',
        amount=gross,
        wallet_before=wallet_before,
        wallet_after=wallet_mid,
        ref_type='VGK_COMPANY_PAYOUT',
        ref_id=payout.id,
        description=(
            f"Company Payout — Gross \u20b9{float(gross):,.2f} | "
            f"Admin 8% \u2212\u20b9{float(admin_charges):,.2f} | "
            f"TDS 2% \u2212\u20b9{float(tds_amount):,.2f} | "
            f"Net \u20b9{float(net_amount):,.2f} | {payload.notes}"
        ),
        initiated_by_staff_id=current_user.id,
        created_at=now,
    )
    db.add(wt_cr)

    # DR: deductions (hidden — mirrors SOLAR_ADV_PAYOUT / SLAB_BONUS_PAYOUT pattern)
    wt_dr = VGKWalletTransaction(
        company_id=partner.company_id,
        partner_id=partner.id,
        txn_type='COMPANY_PAYOUT_DEDUCT',
        direction='DR',
        amount=deductions,
        wallet_before=wallet_mid,
        wallet_after=wallet_final,
        ref_type='VGK_COMPANY_PAYOUT',
        ref_id=payout.id,
        description=(
            f"Company Payout Deduction — Admin 8% \u20b9{float(admin_charges):,.2f} + "
            f"TDS 2% \u20b9{float(tds_amount):,.2f} = \u20b9{float(deductions):,.2f}"
        ),
        initiated_by_staff_id=current_user.id,
        created_at=now,
    )
    db.add(wt_dr)

    # ── Points: debit net from partner's VGK points (waived if insufficient) ─
    from app.services.vgk_commission import add_vgk_points_entry
    pts_available = partner.vgk_points_balance or Decimal('0')
    pts_to_debit  = min(net_amount, pts_available)
    if pts_to_debit > 0:
        try:
            add_vgk_points_entry(
                db, partner.id,
                points_debit=pts_to_debit,
                reason_code='COMMISSION_ADJUSTMENT',
                reference_type='VGK_COMPANY_PAYOUT',
                reference_id=payout.id,
                notes=f'Points debit for company payout \u20b9{float(net_amount):,.2f} net | {payload.notes}',
                created_by=current_user.id,
            )
        except Exception as _pe:
            _log.warning(f'[DC-PAYOUT] Points debit failed (waived): {_pe}')

    db.commit()
    db.refresh(payout)

    return {
        "success":      True,
        "message":      (
            f"Payout recorded: Gross \u20b9{float(gross):,.2f} \u2192 "
            f"Admin 8% \u2212\u20b9{float(admin_charges):,.2f} | TDS 2% \u2212\u20b9{float(tds_amount):,.2f} \u2192 "
            f"Net \u20b9{float(net_amount):,.2f} credited to {partner.partner_name}'s wallet"
        ),
        "data":         payout.to_dict(),
        "partner_code": partner.partner_code,
        "wallet_after": float(wallet_final),
    }


# ── DC-VGK-EXEC-DASH-001: Executive Dashboard (with period + date range filter) ─
@router.get("/dashboard/executive")
def vgk_executive_dashboard(
    period:    str           = Query("overall", description="overall|today|yesterday|week|mtd|custom"),
    date_from: Optional[str] = Query(None, description="ISO date YYYY-MM-DD for custom period"),
    date_to:   Optional[str] = Query(None, description="ISO date YYYY-MM-DD for custom period"),
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """Executive overview: member registration trend, lead pipeline, business generated.
    DC-VGK-EXEC-DASH-001-FILTER: period filter — overall, today, yesterday, week, mtd, custom.
    """
    from datetime import date, timedelta
    today = date.today()

    # ── compute date range ────────────────────────────────────────────────────
    def _get_range():
        if period == "today":
            return today.isoformat(), f"{today.isoformat()}T23:59:59"
        if period == "yesterday":
            y = today - timedelta(days=1)
            return y.isoformat(), f"{y.isoformat()}T23:59:59"
        if period == "week":
            mon = today - timedelta(days=today.weekday())
            return mon.isoformat(), f"{today.isoformat()}T23:59:59"
        if period == "mtd":
            return today.replace(day=1).isoformat(), f"{today.isoformat()}T23:59:59"
        if period == "custom" and date_from and date_to:
            return date_from, f"{date_to}T23:59:59"
        return None, None  # overall

    from_d, to_d = _get_range()
    is_filtered  = from_d is not None
    granularity  = "daily" if is_filtered else "monthly"

    # ── Registration trend ────────────────────────────────────────────────────
    try:
        if is_filtered:
            trend_rows = db.execute(text("""
                SELECT TO_CHAR(created_at AT TIME ZONE 'UTC' AT TIME ZONE 'Asia/Kolkata', 'YYYY-MM-DD') AS ym,
                       TO_CHAR(created_at AT TIME ZONE 'UTC' AT TIME ZONE 'Asia/Kolkata', 'DD Mon') AS label,
                       COUNT(*) AS cnt
                FROM official_partners
                WHERE category = 'VGK_TEAM'
                  AND created_at >= :from_d AND created_at <= :to_d
                GROUP BY ym, label ORDER BY ym
            """), {"from_d": from_d, "to_d": to_d}).fetchall()
        else:
            since_12m = date(today.year - 1 if today.month > 1 else today.year - 2,
                             today.month - 1 if today.month > 1 else 12, 1).isoformat()
            trend_rows = db.execute(text("""
                SELECT TO_CHAR(created_at AT TIME ZONE 'UTC' AT TIME ZONE 'Asia/Kolkata', 'YYYY-MM') AS ym,
                       TO_CHAR(created_at AT TIME ZONE 'UTC' AT TIME ZONE 'Asia/Kolkata', 'Mon YYYY') AS label,
                       COUNT(*) AS cnt
                FROM official_partners
                WHERE category = 'VGK_TEAM'
                  AND created_at >= :since
                GROUP BY ym, label ORDER BY ym
            """), {"since": since_12m}).fetchall()
        registration_trend = [{"ym": r[0], "label": r[1], "count": int(r[2])} for r in trend_rows]
    except Exception:
        registration_trend = []

    # ── Lead pipeline by status ───────────────────────────────────────────────
    try:
        if is_filtered:
            pipeline_rows = db.execute(text("""
                SELECT cl.status, COUNT(*) AS cnt
                FROM crm_leads cl
                JOIN official_partners op ON op.id = cl.associated_partner_id
                WHERE op.category = 'VGK_TEAM'
                  AND cl.created_at >= :from_d AND cl.created_at <= :to_d
                GROUP BY cl.status
            """), {"from_d": from_d, "to_d": to_d}).fetchall()
        else:
            pipeline_rows = db.execute(text("""
                SELECT cl.status, COUNT(*) AS cnt
                FROM crm_leads cl
                JOIN official_partners op ON op.id = cl.associated_partner_id
                WHERE op.category = 'VGK_TEAM'
                GROUP BY cl.status
            """)).fetchall()
        lead_by_status = {r[0]: int(r[1]) for r in pipeline_rows}
    except Exception:
        lead_by_status = {}

    total_leads     = sum(lead_by_status.values())
    won_leads       = lead_by_status.get('won', 0)
    pipeline_leads  = sum(v for k, v in lead_by_status.items() if k in ('won', 'order_placed', 'dispatched', 'delivered', 'installed') and k not in ('completed', 'cancelled', 'lost'))
    completed_leads = lead_by_status.get('completed', 0)
    lost_leads      = lead_by_status.get('lost', 0) + lead_by_status.get('cancelled', 0)
    active_leads    = sum(v for k, v in lead_by_status.items()
                          if k not in ('won', 'completed', 'lost', 'cancelled'))

    # ── Business generated trend ──────────────────────────────────────────────
    try:
        if is_filtered:
            biz_rows = db.execute(text("""
                SELECT TO_CHAR(cl.updated_at AT TIME ZONE 'UTC' AT TIME ZONE 'Asia/Kolkata', 'YYYY-MM-DD') AS ym,
                       TO_CHAR(cl.updated_at AT TIME ZONE 'UTC' AT TIME ZONE 'Asia/Kolkata', 'DD Mon') AS label,
                       COUNT(*) AS cnt
                FROM crm_leads cl
                JOIN official_partners op ON op.id = cl.associated_partner_id
                WHERE op.category = 'VGK_TEAM'
                  AND cl.status IN ('won', 'completed')
                  AND cl.updated_at >= :from_d AND cl.updated_at <= :to_d
                GROUP BY ym, label ORDER BY ym
            """), {"from_d": from_d, "to_d": to_d}).fetchall()
        else:
            since_12m = date(today.year - 1 if today.month > 1 else today.year - 2,
                             today.month - 1 if today.month > 1 else 12, 1).isoformat()
            biz_rows = db.execute(text("""
                SELECT TO_CHAR(cl.updated_at AT TIME ZONE 'UTC' AT TIME ZONE 'Asia/Kolkata', 'YYYY-MM') AS ym,
                       TO_CHAR(cl.updated_at AT TIME ZONE 'UTC' AT TIME ZONE 'Asia/Kolkata', 'Mon YYYY') AS label,
                       COUNT(*) AS cnt
                FROM crm_leads cl
                JOIN official_partners op ON op.id = cl.associated_partner_id
                WHERE op.category = 'VGK_TEAM'
                  AND cl.status IN ('won', 'completed')
                  AND cl.updated_at >= :since
                GROUP BY ym, label ORDER BY ym
            """), {"since": since_12m}).fetchall()
        business_trend = [{"ym": r[0], "label": r[1], "count": int(r[2])} for r in biz_rows]
    except Exception:
        business_trend = []

    # ── Member totals ─────────────────────────────────────────────────────────
    try:
        total_members  = db.execute(text("SELECT COUNT(*) FROM official_partners WHERE category='VGK_TEAM'")).scalar() or 0
        active_members = db.execute(text("SELECT COUNT(*) FROM official_partners WHERE category='VGK_TEAM' AND is_active=true")).scalar() or 0
        if is_filtered:
            new_in_period = db.execute(text(
                "SELECT COUNT(*) FROM official_partners WHERE category='VGK_TEAM'"
                " AND created_at >= :from_d AND created_at <= :to_d"
            ), {"from_d": from_d, "to_d": to_d}).scalar() or 0
        else:
            new_in_period = db.execute(text(
                "SELECT COUNT(*) FROM official_partners WHERE category='VGK_TEAM' AND created_at >= :start"
            ), {"start": today.replace(day=1).isoformat()}).scalar() or 0
    except Exception:
        total_members = active_members = new_in_period = 0

    period_labels = {
        "today": "New Today", "yesterday": "New Yesterday",
        "week":  "New This Week", "mtd": "New This Month",
        "custom": "New in Period", "overall": "New This Month",
    }

    # ── [DC-VGK-STAFF-REG-001] Employee-wise registration counts ─────────────
    try:
        if is_filtered:
            emp_reg_rows = db.execute(text("""
                SELECT op.registered_by_emp_code,
                       se.full_name,
                       COUNT(*) AS total,
                       COUNT(*) FILTER (WHERE op.is_active = true) AS active_count,
                       COUNT(*) FILTER (WHERE op.is_active = false) AS inactive_count
                FROM official_partners op
                LEFT JOIN staff_employees se ON se.emp_code = op.registered_by_emp_code
                WHERE op.category = 'VGK_TEAM'
                  AND op.registered_by_emp_code IS NOT NULL
                  AND op.created_at >= :from_d AND op.created_at <= :to_d
                GROUP BY op.registered_by_emp_code, se.full_name
                ORDER BY total DESC
            """), {"from_d": from_d, "to_d": to_d}).fetchall()
        else:
            emp_reg_rows = db.execute(text("""
                SELECT op.registered_by_emp_code,
                       se.full_name,
                       COUNT(*) AS total,
                       COUNT(*) FILTER (WHERE op.is_active = true) AS active_count,
                       COUNT(*) FILTER (WHERE op.is_active = false) AS inactive_count
                FROM official_partners op
                LEFT JOIN staff_employees se ON se.emp_code = op.registered_by_emp_code
                WHERE op.category = 'VGK_TEAM'
                  AND op.registered_by_emp_code IS NOT NULL
                GROUP BY op.registered_by_emp_code, se.full_name
                ORDER BY total DESC
            """)).fetchall()
        employee_registrations = [
            {
                "emp_code":    r[0],
                "emp_name":    r[1] or r[0],
                "total":       int(r[2]),
                "active":      int(r[3]),
                "inactive":    int(r[4]),
            }
            for r in emp_reg_rows
        ]
    except Exception:
        employee_registrations = []

    return {
        "success": True,
        "data": {
            "period":      period,
            "granularity": granularity,
            "new_label":   period_labels.get(period, "New This Month"),
            "summary": {
                "total_members":      int(total_members),
                "active_members":     int(active_members),
                "new_this_month":     int(new_in_period),
                "total_leads":        total_leads,
                "won_leads":          won_leads,
                "pipeline_leads":     pipeline_leads,
                "completed_leads":    completed_leads,
                "active_leads":       active_leads,
                "lost_leads":         lost_leads,
                "won_plus_completed": won_leads + completed_leads,
            },
            "registration_trend":    registration_trend,
            "business_trend":        business_trend,
            "lead_by_status":        lead_by_status,
            "employee_registrations": employee_registrations,
        }
    }


# ── DC-VGK-MEMBER-EARN-001: Member-wise earnings + points dashboard ────────────
@router.get("/dashboard/member-earnings")
def member_earnings_dashboard(
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=5, le=200),
    earners_only: bool = Query(True, description="Show only members with at least one non-cancelled income entry"),
    income_status: Optional[str] = Query(None, description="Filter by specific income entry status e.g. PAID, PENDING, DRAFT"),
    date_from: Optional[str] = Query(None, description="Filter income by date (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="Filter income by date (YYYY-MM-DD)"),
    registered_by_emp_code: Optional[str] = Query(None, description="Filter by registering staff emp code"),
    customer_search: Optional[str] = Query(None, description="Filter members by customer name or phone on their income entries"),
    sort_by: Optional[str] = Query("name", description="name|code|gross|received|pts_balance|pts_used|l1|l2|l3|l4|files"),
    sort_dir: Optional[str] = Query("asc", description="asc|desc"),
    category_id: Optional[int] = Query(None, description="Filter by signup category / segment"),
    level: Optional[int] = Query(None, description="Filter by income level 1-5"),
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """Per-member breakdown: points (total/used/balance) + income by status & level.
    DC-VGK-MEMBER-EARN-001 v2 — earners_only, date filters, sort, registered_by, customer_search filters.
    DC-VGK-EARN-DASH-001 — adds segment (category_id), level, and income_by_level breakdown.
    """
    from sqlalchemy import or_ as _or

    query = db.query(OfficialPartner).filter(OfficialPartner.category == 'VGK_TEAM')
    if search:
        term = f"%{search.strip()}%"
        query = query.filter(_or(
            OfficialPartner.partner_name.ilike(term),
            OfficialPartner.partner_code.ilike(term),
        ))

    # DC-VGK-CUST-SEARCH-001 (Jun 2026): filter members who have entries for leads matching customer name/phone
    if customer_search:
        _cs = customer_search.strip()
        try:
            _cs_ids = db.execute(text(
                "SELECT DISTINCT e.partner_id FROM vgk_cash_income_entries e "
                "JOIN crm_leads cl ON cl.id = e.source_lead_id "
                "WHERE cl.name ILIKE :cs OR cl.phone ILIKE :cs"
            ), {"cs": f"%{_cs}%"}).scalars().all()
        except Exception:
            _cs_ids = []
        query = query.filter(OfficialPartner.id.in_(_cs_ids))

    if registered_by_emp_code:
        rbe = registered_by_emp_code.strip().upper()
        query = query.filter(OfficialPartner.registered_by_emp_code == rbe)

    # Build date + status WHERE clauses for income SQL
    date_params: dict = {}
    date_clauses = []
    if date_from:
        date_clauses.append("AND e.created_at::date >= :df")
        date_params['df'] = date_from
    if date_to:
        date_clauses.append("AND e.created_at::date <= :dt")
        date_params['dt'] = date_to
    # DC-VGK-CUST-AGG-001: when customer_search is active, restrict aggregate SQL to matching leads
    cust_join_sql = ""
    if customer_search:
        _csk = customer_search.strip()
        cust_join_sql = "JOIN crm_leads _cl ON _cl.id = e.source_lead_id AND (_cl.name ILIKE :_cs OR _cl.phone ILIKE :_cs)"
        date_params['_cs'] = f"%{_csk}%"
    # DC-VGK-EARN-DASH-001: segment + level filters (threaded into all income SQL)
    if category_id:
        date_clauses.append("AND e.category_id = :cat_id")
        date_params['cat_id'] = category_id
    if level:
        date_clauses.append("AND e.level = :lv")
        date_params['lv'] = level
    date_sql = ' '.join(date_clauses)

    # income_status filter clause
    # DC-BRP-001 (Jun 2026): BALANCE_RECEIVED_PLUS = entries whose source CRM lead is at
    # balance_received / subsidy_pending / completed solar pipeline stage (grouped filter).
    status_val = income_status.strip().upper() if income_status else None
    IS_BRP = status_val == 'BALANCE_RECEIVED_PLUS'
    _BRP_SUBQ = (
        "AND e.source_lead_id IN ("
        "SELECT id FROM crm_leads "
        "WHERE solar_pipeline_status IN ('balance_received','subsidy_pending','completed'))"
    )
    if IS_BRP:
        status_sql = _BRP_SUBQ
    else:
        status_sql = "AND e.status = :ist" if status_val else ""
        if status_val:
            date_params['ist'] = status_val

    if earners_only or status_val:
        # Filter: status_val takes priority; otherwise exclude CANCELLED
        if IS_BRP:
            earner_sql = f"SELECT DISTINCT partner_id FROM vgk_cash_income_entries e WHERE 1=1 {_BRP_SUBQ} {date_sql}"
        elif status_val:
            earner_sql = f"SELECT DISTINCT partner_id FROM vgk_cash_income_entries e WHERE e.status = :ist {date_sql}"
        else:
            earner_sql = f"SELECT DISTINCT partner_id FROM vgk_cash_income_entries e WHERE e.status != 'CANCELLED' {date_sql}"
        try:
            earner_rows = db.execute(text(earner_sql), date_params).fetchall()
            earner_ids = [r[0] for r in earner_rows]
        except Exception:
            earner_ids = []
        if not earner_ids:
            return {"success": True, "total": 0, "page": page, "page_size": page_size, "data": []}
        query = query.filter(OfficialPartner.id.in_(earner_ids))

    # Fetch ALL matching members (needed for correct cross-page sort on computed fields)
    members = query.all()
    member_ids = [m.id for m in members]

    # Bulk: points credit + debit totals
    pts_map: dict = {}
    if member_ids:
        try:
            rows = db.execute(text(
                "SELECT partner_id, COALESCE(SUM(points_credit),0), COALESCE(SUM(points_debit),0) "
                "FROM vgk_points_ledger WHERE partner_id = ANY(:ids) GROUP BY partner_id"
            ), {"ids": member_ids}).fetchall()
            pts_map = {int(r[0]): {"credited": float(r[1]), "debited": float(r[2])} for r in rows}
        except Exception:
            pass

    # Bulk: income summary per member per status (with optional date + status filter)
    # DC-VGK-MEMBER-EARN-002 (Jun 2026): also fetch net_payout per status for Gross/Net Pending KPIs
    inc_map: dict = {}
    if member_ids:
        try:
            inc_sql = (
                "SELECT e.partner_id, e.status, COUNT(*), COALESCE(SUM(e.commission_amount),0), COALESCE(SUM(e.net_payout),0) "
                "FROM vgk_cash_income_entries e " + cust_join_sql +
                " WHERE e.partner_id = ANY(:ids) "
                + date_sql + (" " + status_sql if status_val else "") +
                " GROUP BY e.partner_id, e.status"
            )
            rows = db.execute(text(inc_sql), {"ids": member_ids, **date_params}).fetchall()
            for r in rows:
                pid = int(r[0])
                if pid not in inc_map:
                    inc_map[pid] = {}
                inc_map[pid][r[1]] = {"count": int(r[2]), "amount": float(r[3]), "net_amount": float(r[4])}
        except Exception:
            pass

    # DC-VGK-EARN-DASH-001: Bulk income by level for level-wise column breakdown
    # DC-DVR-LVL-CANCELLED-001 (Jul 2026): Exclude CANCELLED entries so l1_source/l2_senior/
    # l5_support totals are not inflated by cancelled-then-reissued entries.
    lvl_map: dict = {}
    if member_ids:
        try:
            lvl_sql_q = (
                "SELECT e.partner_id, e.level, COUNT(*), COALESCE(SUM(e.commission_amount),0), COALESCE(SUM(e.net_payout),0) "
                "FROM vgk_cash_income_entries e " + cust_join_sql +
                " WHERE e.partner_id = ANY(:ids) AND e.status != 'CANCELLED' "
                + date_sql + (" " + status_sql if status_val else "") +
                " GROUP BY e.partner_id, e.level"
            )
            rows = db.execute(text(lvl_sql_q), {"ids": member_ids, **date_params}).fetchall()
            for r in rows:
                pid = int(r[0])
                if pid not in lvl_map:
                    lvl_map[pid] = {}
                lvl_map[pid][int(r[1])] = {"count": int(r[2]), "amount": float(r[3]), "net_amount": float(r[4])}
        except Exception:
            pass

    # DC-VGK-EARN-DASH-001: Total files (non-cancelled entries) per member
    files_map: dict = {}
    if member_ids:
        try:
            f_sql = (
                "SELECT e.partner_id, COUNT(*) FROM vgk_cash_income_entries e " + cust_join_sql +
                " WHERE e.partner_id = ANY(:ids) AND e.status != 'CANCELLED' "
                + date_sql + (" " + status_sql if status_val else "") +
                " GROUP BY e.partner_id"
            )
            files_rows = db.execute(text(f_sql), {"ids": member_ids, **date_params}).fetchall()
            files_map = {int(r[0]): int(r[1]) for r in files_rows}
        except Exception:
            pass

    # DC-VGK-L1-FILES-001: Files where member is ground source (level=1 only, non-cancelled)
    l1_files_map: dict = {}
    if member_ids:
        try:
            l1f_sql = (
                "SELECT e.partner_id, COUNT(*) FROM vgk_cash_income_entries e " + cust_join_sql +
                " WHERE e.partner_id = ANY(:ids) AND e.level = 1 AND e.status != 'CANCELLED' "
                + date_sql + (" " + status_sql if status_val else "") +
                " GROUP BY e.partner_id"
            )
            l1f_rows = db.execute(text(l1f_sql), {"ids": member_ids, **date_params}).fetchall()
            l1_files_map = {int(r[0]): int(r[1]) for r in l1f_rows}
        except Exception:
            pass

    # Bulk: registered_by names
    emp_codes = list({m.registered_by_emp_code for m in members if m.registered_by_emp_code})
    emp_name_map: dict = {}
    if emp_codes:
        try:
            rows = db.execute(text(
                "SELECT emp_code, full_name FROM staff_employees WHERE emp_code = ANY(:codes)"
            ), {"codes": emp_codes}).fetchall()
            emp_name_map = {r[0]: r[1] for r in rows}
        except Exception:
            pass

    items = []
    for m in members:
        p = pts_map.get(m.id, {})
        pts_credited = p.get("credited", 0.0)
        pts_debited  = p.get("debited", 0.0)
        pts_balance  = float(m.vgk_points_balance or 0)
        inc = inc_map.get(m.id, {})
        gross    = sum(v["amount"] for st, v in inc.items() if st != "CANCELLED")
        received = sum(v["amount"] for st, v in inc.items() if st in ("RELEASED", "PAID"))
        _lvl = lvl_map.get(m.id, {})
        items.append({
            "id":                     m.id,
            "partner_code":           m.partner_code,
            "partner_name":           m.partner_name,
            "is_active":              m.is_active,
            "registered_by_emp_code": m.registered_by_emp_code,
            "registered_by_name":     emp_name_map.get(m.registered_by_emp_code),
            "points_credited":        pts_credited,
            "points_used":            pts_debited,
            "points_balance":         pts_balance,
            "gross_earned":           gross,
            "received":               received,
            "income_by_status":       inc,
            # DC-VGK-EARN-DASH-001: level-wise breakdown + new summary fields
            "income_by_level":        _lvl,
            "total_files":            files_map.get(m.id, 0),
            # DC-VGK-EARN-DASH-002 (Jul 2026): Level 6 entries (deep-chain commission) are folded
            # into the L1 Source column so they remain visible without adding a new column.
            "l1_source":              float(_lvl.get(1, {}).get("amount", 0)) + float(_lvl.get(6, {}).get("amount", 0)),
            "l2_senior":              float(_lvl.get(2, {}).get("amount", 0)),
            "l3_extended":            float(_lvl.get(3, {}).get("amount", 0)),
            "l4_core":                float(_lvl.get(4, {}).get("amount", 0)),
            "l5_support":             float(_lvl.get(5, {}).get("amount", 0)),
            "l0_bonus":               float(_lvl.get(0, {}).get("amount", 0)),
            "l1_files":               l1_files_map.get(m.id, 0),
        })

    # Python-level sort (supports computed columns like gross_earned, received)
    _sort_fns = {
        'name':        lambda x: (x['partner_name'] or '').lower(),
        'code':        lambda x: (x['partner_code'] or ''),
        'gross':       lambda x: x['gross_earned'],
        'received':    lambda x: x['received'],
        'pts_balance': lambda x: x['points_balance'],
        'pts_used':    lambda x: x['points_used'],
        # DC-VGK-EARN-DASH-001: level + files sort
        'l1':          lambda x: x['l1_source'],
        'l2':          lambda x: x['l2_senior'],
        'l3':          lambda x: x['l3_extended'],
        'l4':          lambda x: x['l4_core'],
        'l5':          lambda x: x['l5_support'],
        'l0':          lambda x: x['l0_bonus'],
        'total_files': lambda x: x['total_files'],
        'files':       lambda x: x['l1_files'],
    }
    _sfn = _sort_fns.get(sort_by or 'name', _sort_fns['name'])
    items.sort(key=_sfn, reverse=(sort_dir == 'desc'))

    total = len(items)
    start = (page - 1) * page_size
    paged_items = items[start:start + page_size]

    return {"success": True, "total": total, "page": page, "page_size": page_size, "data": paged_items}


@router.get("/dashboard/member-income-entries")
def member_income_entries_detail(
    partner_id: int = Query(..., description="OfficialPartner.id"),
    status: Optional[str] = Query(None, description="Filter by income entry status; BALANCE_RECEIVED_PLUS groups balance_received/subsidy_pending/completed CRM leads"),
    date_from: Optional[str] = Query(None, description="Filter entries from this date (YYYY-MM-DD, inclusive) based on created_at::date"),
    date_to: Optional[str] = Query(None, description="Filter entries up to this date (YYYY-MM-DD, inclusive) based on created_at::date"),
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """Date-wise income entry detail for one VGK member — used by the expand row.
    Queries vgk_cash_income_entries directly (no VGK_TEAM join restriction).
    Accepts optional status filter; BALANCE_RECEIVED_PLUS filters by CRM lead solar stage.
    Accepts optional date_from/date_to to restrict by entry created_at::date.
    """
    # DC-BRP-001: build optional status clause
    _status_val = status.strip().upper() if status else None
    _extra_where = ""
    _extra_params: dict = {"pid": partner_id}
    # DC-IE-DATE-FILTER-001: date range filter on created_at::date
    if date_from:
        _extra_where += " AND e.created_at::date >= CAST(:ie_date_from AS DATE)"
        _extra_params["ie_date_from"] = date_from
    if date_to:
        _extra_where += " AND e.created_at::date <= CAST(:ie_date_to AS DATE)"
        _extra_params["ie_date_to"] = date_to
    if _status_val == 'BALANCE_RECEIVED_PLUS':
        _extra_where = (
            " AND e.source_lead_id IN ("
            "SELECT id FROM crm_leads WHERE solar_pipeline_status "
            "IN ('balance_received','subsidy_pending','completed'))"
        )
    elif _status_val:
        _extra_where = " AND e.status = :st"
        _extra_params["st"] = _status_val
    try:
        rows = db.execute(text(
            "SELECT e.id, e.entry_number, e.status, e.kind, e.level, "
            "  e.created_at::date::text                    AS entry_date, "
            "  COALESCE(e.commission_pct, 0)::float        AS commission_pct, "
            "  COALESCE(e.commission_amount, 0)::float     AS commission_amount, "
            "  COALESCE(e.admin_charges, 0)::float         AS admin_charges, "
            "  COALESCE(e.tds_amount, 0)::float            AS tds_amount, "
            "  COALESCE(e.net_payout, 0)::float            AS net_payout, "
            "  e.source_lead_id, "
            "  e.category_id, "
            "  COALESCE(e.solar_value, 0)::float           AS solar_value_entry, "
            "  COALESCE(e.confirmed_final_value, 0)::float AS cfv_raw, "
            "  COALESCE(e.deal_value_total, 0)::float      AS dvt_raw "
            "FROM vgk_cash_income_entries e "
            f"WHERE e.partner_id = :pid{_extra_where} "
            "ORDER BY e.created_at DESC"
        ), _extra_params).fetchall()
    except Exception as exc:
        return {"success": False, "error": str(exc), "data": []}

    # DC-DVR-BREAKDOWN-001 (Jul 2026): Also fetch VSCA advances that have no VCI mirror.
    # vgk_solar_cibil_advances records (PENDING/RELEASED) that were not yet mirrored into
    # vgk_cash_income_entries appear here so partners can see all pending/released advances,
    # including DVR_ADVANCE entries created by the backfill or by the live advance flow
    # before DC-DVR-VCI-MIRROR-001 was deployed.  We exclude CANCELLED and any VSCA row
    # that already has a VCI mirror with the same kind (to prevent double-counting).
    vsca_rows = []
    try:
        _vsca_status_clause = ""
        _vsca_params: dict = {"pid": partner_id}
        if _status_val and _status_val not in ('BALANCE_RECEIVED_PLUS',):
            # Map VCI status names to VSCA status names where they overlap
            _vsca_status_clause = " AND a.status = :vsca_st"
            _vsca_params["vsca_st"] = _status_val
        # DC-IE-DATE-FILTER-001: apply same date range to VSCA rows
        if date_from:
            _vsca_status_clause += " AND COALESCE(a.released_at::date, a.created_at::date) >= CAST(:vsca_date_from AS DATE)"
            _vsca_params["vsca_date_from"] = date_from
        if date_to:
            _vsca_status_clause += " AND COALESCE(a.released_at::date, a.created_at::date) <= CAST(:vsca_date_to AS DATE)"
            _vsca_params["vsca_date_to"] = date_to
        vsca_rows = db.execute(text(
            "SELECT a.id, a.entry_number, a.status, a.kind, a.level, "
            "  COALESCE(a.released_at::date, a.created_at::date)::text AS entry_date, "
            "  0::float                AS commission_pct, "
            "  a.advance_amount::float AS commission_amount, "
            "  (a.advance_amount * 0.08)::float AS admin_charges, "
            "  (a.advance_amount * 0.02)::float AS tds_amount, "
            "  (a.advance_amount * 0.90)::float AS net_payout, "
            "  a.lead_id              AS source_lead_id, "
            "  NULL::integer          AS category_id, "
            "  0::float               AS solar_value_entry, "
            "  0::float               AS cfv_raw, "
            "  0::float               AS dvt_raw "
            "FROM vgk_solar_cibil_advances a "
            "WHERE a.partner_id = :pid "
            "  AND a.status IN ('PENDING','RELEASED') "
            + _vsca_status_clause +
            "  AND NOT EXISTS ( "
            "    SELECT 1 FROM vgk_cash_income_entries vci "
            "    WHERE vci.partner_id    = a.partner_id "
            "      AND vci.source_lead_id = a.lead_id "
            "      AND vci.level          = a.level "
            "      AND vci.kind           = a.kind "
            "      AND vci.status        != 'CANCELLED' "
            "  ) "
            "ORDER BY a.created_at DESC"
        ), _vsca_params).fetchall()
    except Exception:
        vsca_rows = []

    # Batch-resolve client names + mobile numbers from CRM in one query (VCI + VSCA)
    lead_ids = list({r.source_lead_id for r in list(rows) + list(vsca_rows) if r.source_lead_id})
    lead_info: dict = {}
    if lead_ids:
        try:
            lr = db.execute(text(
                "SELECT id, name, phone, COALESCE(deal_value_received, 0) AS deal_value_received, "
                "  submit_date::text AS submit_date, complete_date::text AS complete_date "
                "FROM crm_leads WHERE id = ANY(:ids)"
            ), {"ids": lead_ids}).fetchall()
            lead_info = {r.id: {
                "name": r.name, "mobile": r.phone,
                "dvr": float(r.deal_value_received or 0),
                "submit_date": r.submit_date,
                "complete_date": r.complete_date,
            } for r in lr}
        except Exception:
            pass

    result = []
    _lvl_labels_map = {0:'Comm', 1:'Source', 2:'Senior', 3:'Extended', 4:'Core', 5:'Support'}

    def _build_row(r, is_vsca: bool = False):
        _li    = lead_info.get(r.source_lead_id) if r.source_lead_id else None
        client = _li["name"]   if _li else None
        mobile = _li["mobile"] if _li else None
        _dvr  = _li["dvr"] if _li else 0.0
        _dt   = float(r.dvt_raw or 0)
        _pct  = float(r.commission_pct or 0)
        _kind = (r.kind or '').upper()
        # DC-SLAB-COMM-BASE-001: SLAB_BONUS is a flat amount unrelated to deal size.
        # commission_base = slab_amount itself; never fall through to lead deal_value_received.
        if _kind == 'SLAB_BONUS':
            commission_base = float(r.commission_amount)
        elif _pct > 0:
            commission_base = round(float(r.commission_amount) / _pct * 100, 2)
        else:
            commission_base = _dvr if _dvr > 0 else _dt
        _lvl_int = int(r.level) if r.level is not None else None
        return {
            "id":                int(r.id),
            "entry_number":      r.entry_number or f"INC-{r.id}",
            "status":            r.status,
            "kind":              r.kind or ("DVR_ADVANCE" if is_vsca else "COMMISSION"),
            "level":             _lvl_int,
            "level_label":       _lvl_labels_map.get(_lvl_int, f"L{_lvl_int}") if _lvl_int is not None else "—",
            "income_date":       r.entry_date,
            "deal_value":        commission_base,
            "commission_pct":    float(r.commission_pct),
            "commission_amount": float(r.commission_amount),
            "admin_charges":     float(r.admin_charges),
            "tds_amount":        float(r.tds_amount),
            "net_payout":        float(r.net_payout),
            "client_name":       client,
            "client_mobile":     mobile,
            "submit_date":       _li["submit_date"]   if _li else None,
            "complete_date":     _li["complete_date"]  if _li else None,
            "from_vsca":         is_vsca,
        }

    for r in rows:
        result.append(_build_row(r, is_vsca=False))
    for r in vsca_rows:
        result.append(_build_row(r, is_vsca=True))

    # Sort merged list by income_date descending then entry_number descending
    result.sort(key=lambda x: (x.get("income_date") or ""), reverse=True)

    return {"success": True, "data": result, "total": len(result)}


# ── DC-VGK-LEAD-VIEW-001: Lead-centric income dashboard (reverse of member view) ──
@router.get("/dashboard/lead-earnings")
def lead_earnings_dashboard(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=5, le=200),
    search: Optional[str] = Query(None, description="Customer name or phone search"),
    income_status: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    category_id: Optional[int] = Query(None),
    level: Optional[int] = Query(None),
    sort_by: Optional[str] = Query("gross", description="gross|name|date|members"),
    sort_dir: Optional[str] = Query("desc", description="asc|desc"),
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """Lead-centric income summary — groups vgk_cash_income_entries by source_lead_id.
    Returns per-lead level breakdown + status pills + member count.
    DC-VGK-LEAD-VIEW-001
    """
    where_clauses = ["e.source_lead_id IS NOT NULL"]
    params: dict = {}

    if search:
        where_clauses.append("(cl.name ILIKE :search OR cl.phone ILIKE :search)")
        params['search'] = f"%{search.strip()}%"
    if date_from:
        where_clauses.append("e.created_at::date >= :df")
        params['df'] = date_from
    if date_to:
        where_clauses.append("e.created_at::date <= :dt")
        params['dt'] = date_to
    if category_id:
        where_clauses.append("cl.category_id = :cat_id")
        params['cat_id'] = category_id
    if level is not None:
        where_clauses.append("e.level = :lv")
        params['lv'] = level

    status_val = income_status.strip().upper() if income_status else None
    if status_val == 'BALANCE_RECEIVED_PLUS':
        where_clauses.append("cl.solar_pipeline_status IN ('balance_received','subsidy_pending','completed')")
    elif status_val:
        where_clauses.append("e.status = :ist")
        params['ist'] = status_val

    where_sql = " AND ".join(where_clauses)

    try:
        agg_rows = db.execute(text(f"""
            SELECT
                e.source_lead_id,
                cl.name AS customer_name,
                cl.phone AS customer_phone,
                cl.submit_date::text  AS submit_date,
                cl.complete_date::text AS complete_date,
                cl.category_id,
                COALESCE(SUM(e.commission_amount) FILTER (WHERE e.status != 'CANCELLED'), 0)::float          AS gross_earned,
                COALESCE(SUM(e.commission_amount) FILTER (WHERE e.status IN ('RELEASED','PAID')), 0)::float  AS received,
                COALESCE(SUM(e.commission_amount) FILTER (WHERE e.status != 'CANCELLED' AND e.kind != 'EXTRA_COMMISSION' AND e.level = 0), 0)::float AS l0_bonus,
                COALESCE(SUM(e.commission_amount) FILTER (WHERE e.status != 'CANCELLED' AND e.kind != 'EXTRA_COMMISSION' AND e.level IN (1,6)), 0)::float AS l1_source,
                COALESCE(SUM(e.commission_amount) FILTER (WHERE e.status != 'CANCELLED' AND e.kind != 'EXTRA_COMMISSION' AND e.level = 2), 0)::float AS l2_senior,
                COALESCE(SUM(e.commission_amount) FILTER (WHERE e.status != 'CANCELLED' AND e.kind != 'EXTRA_COMMISSION' AND e.level = 3), 0)::float AS l3_extended,
                COALESCE(SUM(e.commission_amount) FILTER (WHERE e.status != 'CANCELLED' AND e.kind != 'EXTRA_COMMISSION' AND e.level = 4), 0)::float AS l4_core,
                COALESCE(SUM(e.commission_amount) FILTER (WHERE e.status != 'CANCELLED' AND e.kind != 'EXTRA_COMMISSION' AND e.level = 5), 0)::float AS l5_support,
                COALESCE(SUM(e.commission_amount) FILTER (WHERE e.status != 'CANCELLED' AND e.kind = 'EXTRA_COMMISSION'), 0)::float AS ec_bonus,
                COUNT(*)            FILTER (WHERE e.status != 'CANCELLED')::integer AS total_files,
                COUNT(DISTINCT e.partner_id) FILTER (WHERE e.status != 'CANCELLED')::integer AS member_count
            FROM vgk_cash_income_entries e
            JOIN crm_leads cl ON cl.id = e.source_lead_id
            WHERE {where_sql}
            GROUP BY e.source_lead_id, cl.name, cl.phone, cl.submit_date, cl.complete_date, cl.category_id
        """), params).fetchall()
    except Exception as exc:
        return {"success": False, "error": str(exc), "data": []}

    if not agg_rows:
        return {"success": True, "total": 0, "page": page, "page_size": page_size, "data": []}

    lead_ids = [int(r.source_lead_id) for r in agg_rows]

    # Status breakdown per lead (for pills)
    status_map: dict = {}
    try:
        _sp = {"ids": lead_ids}
        _sw = "e.source_lead_id = ANY(:ids)"
        if date_from: _sw += " AND e.created_at::date >= :df"; _sp['df'] = date_from
        if date_to:   _sw += " AND e.created_at::date <= :dt"; _sp['dt'] = date_to
        s_rows = db.execute(text(
            f"SELECT e.source_lead_id, e.status, COUNT(*), COALESCE(SUM(e.commission_amount),0)::float "
            f"FROM vgk_cash_income_entries e WHERE {_sw} GROUP BY e.source_lead_id, e.status"
        ), _sp).fetchall()
        for r in s_rows:
            lid = int(r[0])
            if lid not in status_map:
                status_map[lid] = {}
            status_map[lid][r[1]] = {"count": int(r[2]), "amount": float(r[3])}
    except Exception:
        pass

    # Category names
    cat_ids = list({r.category_id for r in agg_rows if r.category_id})
    cat_map: dict = {}
    if cat_ids:
        try:
            cr = db.execute(text(
                "SELECT id, name FROM crm_lead_categories WHERE id = ANY(:ids)"
            ), {"ids": cat_ids}).fetchall()
            cat_map = {int(r.id): r.name for r in cr}
        except Exception:
            pass

    items = []
    for r in agg_rows:
        items.append({
            "lead_id":          int(r.source_lead_id),
            "customer_name":    r.customer_name or "—",
            "customer_phone":   r.customer_phone or "",
            "submit_date":      r.submit_date,
            "complete_date":    r.complete_date,
            "category_id":      r.category_id,
            "category_name":    cat_map.get(r.category_id, "—") if r.category_id else "—",
            "total_files":      int(r.total_files),
            "member_count":     int(r.member_count),
            "l0_bonus":         float(r.l0_bonus),
            "l1_source":        float(r.l1_source),
            "l2_senior":        float(r.l2_senior),
            "l3_extended":      float(r.l3_extended),
            "l4_core":          float(r.l4_core),
            "l5_support":       float(r.l5_support),
            "ec_bonus":         float(r.ec_bonus),
            "gross_earned":     float(r.gross_earned),
            "received":         float(r.received),
            "income_by_status": status_map.get(int(r.source_lead_id), {}),
        })

    _sort_fns = {
        "gross":   lambda x: x["gross_earned"],
        "name":    lambda x: (x["customer_name"] or "").lower(),
        "date":    lambda x: (x["submit_date"] or ""),
        "members": lambda x: x["member_count"],
    }
    items.sort(key=_sort_fns.get(sort_by, _sort_fns["gross"]), reverse=(sort_dir == "desc"))

    total  = len(items)
    start  = (page - 1) * page_size
    return {"success": True, "total": total, "page": page, "page_size": page_size, "data": items[start:start + page_size]}


@router.get("/dashboard/lead-income-members")
def lead_income_members_detail(
    lead_id: int = Query(..., description="source_lead_id"),
    status: Optional[str] = Query(None),
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """Members who earned from a specific lead — expand-row detail for Lead View tab.
    DC-VGK-LEAD-VIEW-001
    """
    _extra = ""
    _p: dict = {"lid": lead_id}
    if status:
        sv = status.strip().upper()
        if sv not in ('BALANCE_RECEIVED_PLUS',):
            _extra = " AND e.status = :st"
            _p["st"] = sv
    try:
        rows = db.execute(text(
            "SELECT e.id, e.entry_number, e.status, e.kind, e.level, "
            "  e.created_at::date::text AS income_date, "
            "  COALESCE(e.commission_amount,0)::float AS commission_amount, "
            "  COALESCE(e.net_payout,0)::float        AS net_payout, "
            "  COALESCE(e.admin_charges,0)::float     AS admin_charges, "
            "  COALESCE(e.tds_amount,0)::float        AS tds_amount, "
            "  op.partner_code, op.partner_name "
            "FROM vgk_cash_income_entries e "
            "JOIN official_partners op ON op.id = e.partner_id "
            f"WHERE e.source_lead_id = :lid{_extra} "
            "ORDER BY e.level ASC, e.created_at DESC"
        ), _p).fetchall()
    except Exception as exc:
        return {"success": False, "error": str(exc), "data": []}

    return {"success": True, "total": len(rows), "data": [{
        "id":                int(r.id),
        "entry_number":      r.entry_number or f"INC-{r.id}",
        "status":            r.status,
        "kind":              r.kind or "COMMISSION",
        "level":             r.level,
        "income_date":       r.income_date,
        "commission_amount": float(r.commission_amount),
        "net_payout":        float(r.net_payout),
        "admin_charges":     float(r.admin_charges),
        "tds_amount":        float(r.tds_amount),
        "partner_code":      r.partner_code,
        "partner_name":      r.partner_name,
    } for r in rows]}


# ── [DC-VGK-STAFF-REG-001] My Registrations — staff-scoped list ──────────────
@router.get("/my-registrations")
def my_vgk_registrations(
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=5, le=100),
    is_active: Optional[bool] = Query(None),
    sort_by: Optional[str] = Query("registered", description="registered|name|code"),
    sort_dir: Optional[str] = Query("desc", description="asc|desc"),
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """Return VGK members registered by the calling staff employee."""
    emp_code = (getattr(current_user, 'emp_code', '') or '').strip().upper()
    if not emp_code:
        return {"success": True, "total": 0, "page": page, "page_size": page_size, "data": []}

    query = db.query(OfficialPartner).filter(
        OfficialPartner.category == 'VGK_TEAM',
        OfficialPartner.registered_by_emp_code == emp_code
    )
    if is_active is not None:
        query = query.filter(OfficialPartner.is_active == is_active)

    _sort_col = OfficialPartner.created_at
    if sort_by == 'name':
        _sort_col = OfficialPartner.partner_name
    elif sort_by == 'code':
        _sort_col = OfficialPartner.partner_code
    _order = _sort_col.asc() if sort_dir == 'asc' else _sort_col.desc()

    total   = query.count()
    members = query.order_by(_order).offset((page - 1) * page_size).limit(page_size).all()

    this_month_count = db.query(OfficialPartner).filter(
        OfficialPartner.category == 'VGK_TEAM',
        OfficialPartner.registered_by_emp_code == emp_code,
        OfficialPartner.created_at >= text("date_trunc('month', now())")
    ).count()

    return {
        "success": True,
        "total":   total,
        "page":    page,
        "page_size": page_size,
        "this_month": int(this_month_count),
        "data": [m.to_dict() for m in members],
    }


# ── DC-VGK-EXEC-DASH-002: Top Partners with period filter + comparison ────────
@router.get("/dashboard/top-partners")
def vgk_top_partners_filtered(
    period:    str           = Query("overall", description="overall|today|yesterday|week|mtd|custom"),
    date_from: Optional[str] = Query(None, description="ISO date YYYY-MM-DD for custom period"),
    date_to:   Optional[str] = Query(None, description="ISO date YYYY-MM-DD for custom period"),
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """Top VGK partners by leads with period filter, won value, and period-over-period comparison."""
    from datetime import date, timedelta
    import calendar

    today = date.today()

    def _get_range(p: str):
        """Returns (from_date, to_date, prev_from, prev_to, prev_label) for a period."""
        if p == "today":
            return (today, today,
                    today - timedelta(days=1), today - timedelta(days=1), "Yesterday")
        if p == "yesterday":
            y = today - timedelta(days=1)
            return (y, y,
                    y - timedelta(days=1), y - timedelta(days=1), "Day Before")
        if p == "week":
            mon = today - timedelta(days=today.weekday())
            prev_mon = mon - timedelta(days=7)
            return (mon, today,
                    prev_mon, prev_mon + timedelta(days=6), "Prev Week")
        if p == "mtd":
            first = today.replace(day=1)
            prev_last = first - timedelta(days=1)
            prev_first = prev_last.replace(day=1)
            return (first, today,
                    prev_first, prev_last, "Prev Month")
        if p == "custom" and date_from and date_to:
            try:
                from datetime import date as _date
                f = _date.fromisoformat(date_from)
                t = _date.fromisoformat(date_to)
                return (f, t, None, None, "")
            except Exception:
                pass
        return (None, None, None, None, "")  # overall — no filter

    cur_from, cur_to, prev_from, prev_to, prev_label = _get_range(period)

    def _build_where(from_d, to_d, alias="cl"):
        params: dict = {}
        clause = f"JOIN official_partners op ON op.id = {alias}.associated_partner_id WHERE op.category = 'VGK_TEAM'"
        if from_d:
            clause += f" AND {alias}.created_at >= :from_d AND {alias}.created_at <= :to_d_end"
            params["from_d"] = from_d.isoformat()
            params["to_d_end"] = f"{to_d.isoformat()}T23:59:59"
        return clause, params

    # ── current period top partners ───────────────────────────────────────────
    cur_where, cur_params = _build_where(cur_from, cur_to)
    try:
        cur_rows = db.execute(text(f"""
            SELECT op.id,
                   op.partner_name,
                   op.partner_code,
                   COUNT(*) AS total_leads,
                   COUNT(*) FILTER (WHERE cl.status = 'won') AS won_count,
                   COALESCE(SUM(cl.deal_value_total) FILTER (WHERE cl.status = 'won'), 0) AS won_value,
                   COUNT(*) FILTER (WHERE cl.status = 'completed') AS completed_count,
                   COALESCE(SUM(cl.deal_value_total) FILTER (WHERE cl.status = 'completed'), 0) AS completed_value
            FROM crm_leads cl
            {cur_where}
            GROUP BY op.id, op.partner_name, op.partner_code
            ORDER BY total_leads DESC
            LIMIT 20
        """), cur_params).fetchall()
        current_partners = [
            {"id": int(r[0]), "name": r[1], "code": r[2],
             "total_leads":     int(r[3]),
             "won_count":       int(r[4]),   "won_value":       float(r[5] or 0),
             "completed_count": int(r[6]),   "completed_value": float(r[7] or 0)}
            for r in cur_rows
        ]
    except Exception:
        current_partners = []

    # ── previous period (for comparison) ─────────────────────────────────────
    prev_map: dict = {}
    if prev_from:
        prev_where, prev_params = _build_where(prev_from, prev_to)
        try:
            prev_rows = db.execute(text(f"""
                SELECT op.id,
                       COUNT(*) AS total_leads,
                       COUNT(*) FILTER (WHERE cl.status = 'won') AS won_count,
                       COUNT(*) FILTER (WHERE cl.status = 'completed') AS completed_count
                FROM crm_leads cl
                {prev_where}
                GROUP BY op.id
            """), prev_params).fetchall()
            prev_map = {
                int(r[0]): {"total_leads": int(r[1]), "won_count": int(r[2]), "completed_count": int(r[3])}
                for r in prev_rows
            }
        except Exception:
            pass

    # ── attach comparison deltas ──────────────────────────────────────────────
    for p in current_partners:
        prev = prev_map.get(p["id"], {})
        p["prev_total"]     = prev.get("total_leads", 0)
        p["prev_won"]       = prev.get("won_count", 0)
        p["prev_completed"] = prev.get("completed_count", 0)
        p["delta_total"]    = p["total_leads"]     - p["prev_total"]
        p["delta_won"]      = p["won_count"]       - p["prev_won"]
        p["delta_completed"]= p["completed_count"] - p["prev_completed"]

    return {
        "success": True,
        "data": {
            "period":     period,
            "prev_label": prev_label,
            "partners":   current_partners,
        }
    }


# ── DC-VGK-BRAND-INCENTIVE-001: Brand incentive CRUD endpoints ───────────────────────────────────

class BrandCreate(BaseModel):
    company_id: int
    brand_name: str
    l1_amount: float = 0
    l2_amount: float = 0
    l5_amount: float = 0
    is_active: bool = True

class BrandUpdate(BaseModel):
    brand_name: Optional[str] = None
    l1_amount: Optional[float] = None
    l2_amount: Optional[float] = None
    l5_amount: Optional[float] = None
    is_active: Optional[bool] = None


@router.get("/brands")
async def list_brands(
    company_id: Optional[int] = None,
    active_only: bool = False,
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user),
):
    """List VGK incentive brands. Staff only."""
    from sqlalchemy import text as _bt
    where = []
    params: dict = {}
    if company_id:
        where.append("company_id = :cid")
        params['cid'] = company_id
    if active_only:
        where.append("is_active = TRUE")
    wc = ("WHERE " + " AND ".join(where)) if where else ""
    rows = db.execute(_bt(f"""
        SELECT id, company_id, brand_name, l1_amount, l2_amount, l5_amount, is_active,
               created_at, updated_at
        FROM vgk_incentive_brands {wc}
        ORDER BY brand_name ASC
    """), params).fetchall()
    return {
        "success": True,
        "brands": [
            {
                "id": r.id,
                "company_id": r.company_id,
                "brand_name": r.brand_name,
                "l1_amount": float(r.l1_amount or 0),
                "l2_amount": float(r.l2_amount or 0),
                "l5_amount": float(r.l5_amount or 0),
                "is_active": r.is_active,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "updated_at": r.updated_at.isoformat() if r.updated_at else None,
            }
            for r in rows
        ],
    }


@router.post("/brands")
async def create_brand(
    body: BrandCreate = Body(...),
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user),
):
    """Create a new VGK incentive brand. Staff only."""
    from sqlalchemy import text as _bt
    from app.models.base import get_indian_time
    now = get_indian_time()
    row = db.execute(_bt("""
        INSERT INTO vgk_incentive_brands
            (company_id, brand_name, l1_amount, l2_amount, l5_amount, is_active, created_at, updated_at)
        VALUES (:cid, :bn, :l1, :l2, :l5, :ia, :now, :now)
        RETURNING id
    """), {
        'cid': body.company_id,
        'bn':  body.brand_name.strip(),
        'l1':  body.l1_amount,
        'l2':  body.l2_amount,
        'l5':  body.l5_amount,
        'ia':  body.is_active,
        'now': now.replace(tzinfo=None),
    }).fetchone()
    db.commit()
    return {"success": True, "id": row.id}


@router.put("/brands/{brand_id}")
async def update_brand(
    brand_id: int,
    body: BrandUpdate = Body(...),
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user),
):
    """Update VGK incentive brand amounts or active flag. Staff only."""
    from sqlalchemy import text as _bt
    from app.models.base import get_indian_time
    updates = body.dict(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    now = get_indian_time()
    set_clauses = ", ".join(f"{k} = :{k}" for k in updates)
    updates['brand_id'] = brand_id
    updates['now'] = now.replace(tzinfo=None)
    result = db.execute(_bt(
        f"UPDATE vgk_incentive_brands SET {set_clauses}, updated_at = :now WHERE id = :brand_id"
    ), updates)
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Brand not found")
    db.commit()
    return {"success": True}


@router.delete("/brands/{brand_id}")
async def delete_brand(
    brand_id: int,
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user),
):
    """Soft-delete (deactivate) a VGK incentive brand. Staff only."""
    from sqlalchemy import text as _bt
    from app.models.base import get_indian_time
    now = get_indian_time()
    result = db.execute(_bt(
        "UPDATE vgk_incentive_brands SET is_active = FALSE, updated_at = :now WHERE id = :bid"
    ), {'bid': brand_id, 'now': now.replace(tzinfo=None)})
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Brand not found")
    db.commit()
    return {"success": True}


@router.get("/advance-cap/{partner_id}")
async def get_advance_cap_status(
    partner_id: int,
    company_id: int = 4,
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user),
):
    """Return the 50% advance cap status for a partner (DC-VGK-ADV-CAP-001)."""
    from app.services.vgk_advance_cap import get_cap_status
    info = get_cap_status(db, partner_id, company_id)
    return {"success": True, "cap_status": info}

