"""
Promoter / Influencer Referral System — API Endpoints
DC Protocol Apr 2026: Additive only. Staff CRUD + Promoter auth + Referral tracking.
"""
from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional, List
from pydantic import BaseModel, Field
from app.core.database import get_db
from app.models.base import get_indian_time
from app.api.v1.endpoints.staff_auth import get_current_staff_user
from app.models.staff import StaffEmployee
import bcrypt, secrets, string
from datetime import timedelta

router = APIRouter()

# ─── Helpers ──────────────────────────────────────────────────────────────────

# Allowed role codes for INTERNAL promo management
_PROMO_ROLES = {"vgk4u", "ea", "rvz", "supervisor", "manager", "key_leadership", "leadership_role"}

def _hash_pw(pw: str) -> str:
    return bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()

def _verify_pw(pw: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(pw.encode(), hashed.encode())
    except Exception:
        return False

def _gen_code(name: str) -> str:
    base = ''.join(c.upper() for c in name if c.isalpha())[:6]
    suffix = ''.join(secrets.choice(string.digits) for _ in range(2))
    return f"{base}{suffix}" if base else f"PROMO{suffix}"

def _require_promo_access(current_user: StaffEmployee):
    """Raise 403 if staff member doesn't have promo management access."""
    role_code = (current_user.role.role_code if current_user.role else "").lower()
    if role_code not in _PROMO_ROLES:
        raise HTTPException(status_code=403, detail="Access restricted to VGK Mentor and EA roles")

def _auto_activate_check(db: Session, influencer_id: int, referral_code: str):
    """After a VGK referral event, check if promoter hits their target and auto-activate."""
    try:
        row = db.execute(text(
            "SELECT status, vgk_registration_target FROM promo_influencers WHERE id = :id"
        ), {"id": influencer_id}).fetchone()
        if not row or row[0] != "pending" or not row[1]:
            return
        count = db.execute(text(
            "SELECT COUNT(*) FROM promo_referral_events WHERE influencer_id = :id AND portal = 'vgk' AND event_type = 'registration'"
        ), {"id": influencer_id}).scalar() or 0
        if count >= row[1]:
            db.execute(text(
                "UPDATE promo_influencers SET status = 'active', updated_at = NOW() WHERE id = :id"
            ), {"id": influencer_id})
            db.commit()
            print(f"[DC-PROMO] Auto-activated influencer {influencer_id} — {count} VGK registrations >= target {row[1]}", flush=True)
    except Exception as e:
        print(f"[DC-PROMO] auto_activate_check error: {e}", flush=True)

# ─── Schemas ──────────────────────────────────────────────────────────────────

class CreateInfluencerRequest(BaseModel):
    name: str
    phone: str                              # mandatory
    email: Optional[str] = None
    platforms: Optional[str] = None        # comma-separated
    social_links: Optional[str] = None     # JSON string of platform→URL map
    referral_code: Optional[str] = None    # auto-generated if blank
    account_type: str = "unpaid"
    is_vgk_member: bool = False
    vgk_registration_target: Optional[int] = None
    notes: Optional[str] = None
    password: str                           # initial login password
    budget_range: Optional[str] = None     # monthly promotion budget range
    signup_bonus_points: Optional[int] = None  # bonus points awarded to new signups via this code

class UpdateInfluencerRequest(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    platforms: Optional[str] = None
    social_links: Optional[str] = None
    referral_code: Optional[str] = None
    status: Optional[str] = None
    account_type: Optional[str] = None
    is_vgk_member: Optional[bool] = None
    vgk_registration_target: Optional[int] = None
    notes: Optional[str] = None
    new_password: Optional[str] = None
    budget_range: Optional[str] = None
    signup_bonus_points: Optional[int] = None  # bonus points awarded to new signups via this code

class SelfRegisterRequest(BaseModel):
    name: str
    phone: str
    email: Optional[str] = None
    platforms: Optional[str] = None
    budget_range: Optional[str] = None
    password: str
    name_title: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    gender: Optional[str] = None

class TrackEventRequest(BaseModel):
    referral_code: str
    portal: str          # vgk, mnr_contact, partner, etc
    event_type: str      # registration, contact, signup
    source_ref_id: Optional[str] = None
    source_name: Optional[str] = None
    source_phone: Optional[str] = None

class PromoLoginRequest(BaseModel):
    login: str           # email or phone
    password: str

# ─── Staff: CRUD ──────────────────────────────────────────────────────────────

@router.get("/staff/list")
def list_influencers(
    status: Optional[str] = None,
    account_type: Optional[str] = None,
    search: Optional[str] = None,
    platform: Optional[str] = None,
    is_vgk_member: Optional[bool] = None,
    skip: int = 0, limit: int = 100,
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user),
):
    _require_promo_access(current_user)
    where = ["1=1"]
    params = {}
    if status:
        where.append("pi.status = :status"); params["status"] = status
    if account_type:
        where.append("pi.account_type = :account_type"); params["account_type"] = account_type
    if is_vgk_member is not None:
        where.append("pi.is_vgk_member = :ivm"); params["ivm"] = is_vgk_member
    if platform:
        where.append("pi.platforms ILIKE :plat"); params["plat"] = f"%{platform}%"
    if search:
        where.append("(pi.name ILIKE :s OR pi.phone ILIKE :s OR pi.referral_code ILIKE :s OR pi.email ILIKE :s)")
        params["s"] = f"%{search}%"
    where_clause = " AND ".join(where)
    rows = db.execute(text(f"""
        SELECT pi.id, pi.name, pi.email, pi.phone, pi.platforms, pi.referral_code,
               pi.status, pi.account_type, pi.is_vgk_member, pi.vgk_member_id,
               pi.vgk_registration_target, pi.notes, pi.created_at, pi.updated_at,
               COALESCE(pi.social_links, '') as social_links,
               COALESCE(pi.signup_bonus_points, 0) as signup_bonus_points,
               COALESCE(pi.signup_source,
                   CASE WHEN pi.created_by_staff_id IS NOT NULL THEN 'staff' ELSE 'direct' END
               ) as signup_source,
               (SELECT COUNT(*) FROM promo_referral_events r WHERE r.influencer_id = pi.id) as total_referrals,
               (SELECT COUNT(*) FROM promo_referral_events r WHERE r.influencer_id = pi.id AND r.portal = 'vgk' AND r.event_type = 'registration') as vgk_registrations,
               (SELECT COUNT(*) FROM promo_deals d WHERE d.influencer_id = pi.id) as deal_count,
               COALESCE((SELECT SUM(agreed_charge) FROM promo_deals d WHERE d.influencer_id = pi.id), 0) as deal_total,
               COALESCE((SELECT SUM(payment_amount) FROM promo_deals d WHERE d.influencer_id = pi.id AND d.payment_status = 'paid'), 0) as deal_paid,
               pia.last_login
        FROM promo_influencers pi
        LEFT JOIN promo_influencer_auth pia ON pia.influencer_id = pi.id
        WHERE {where_clause}
        ORDER BY pi.created_at DESC LIMIT :limit OFFSET :skip
    """), {**params, "limit": limit, "skip": skip}).fetchall()
    total = db.execute(text(f"SELECT COUNT(*) FROM promo_influencers pi WHERE {where_clause}"), params).scalar()
    return {"success": True, "total": total, "items": [dict(r._mapping) for r in rows]}


@router.post("/staff/create")
def create_influencer(
    body: CreateInfluencerRequest,
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user),
):
    _require_promo_access(current_user)
    if not body.phone or not body.phone.strip():
        raise HTTPException(status_code=400, detail="Mobile number is required")
    code = (body.referral_code or "").strip().upper() or _gen_code(body.name)
    existing = db.execute(text("SELECT id FROM promo_influencers WHERE referral_code = :c"), {"c": code}).fetchone()
    if existing:
        raise HTTPException(status_code=400, detail=f"Referral code '{code}' already exists")
    vgk_member_id = None
    if body.is_vgk_member:
        vgk_member_id = _create_vgk_member_silent(db, body.name, body.phone, body.email)
    row = db.execute(text("""
        INSERT INTO promo_influencers (name, email, phone, platforms, social_links, referral_code, status,
            account_type, is_vgk_member, vgk_member_id, vgk_registration_target, notes,
            budget_range, signup_bonus_points, signup_source, created_by_staff_id, created_at, updated_at)
        VALUES (:name, :email, :phone, :platforms, :social_links, :code, 'pending', :atype,
            :isvgk, :vgkid, :target, :notes, :budget_range, :signup_bonus, 'staff', :staff_id, NOW(), NOW())
        RETURNING id
    """), {
        "name": body.name, "email": body.email, "phone": body.phone.strip(),
        "platforms": body.platforms, "social_links": body.social_links,
        "code": code, "atype": body.account_type,
        "isvgk": body.is_vgk_member, "vgkid": vgk_member_id,
        "target": body.vgk_registration_target, "notes": body.notes,
        "budget_range": body.budget_range,
        "signup_bonus": max(5000, body.signup_bonus_points) if body.signup_bonus_points is not None else 5000,
        "staff_id": current_user.id,
    }).fetchone()
    inf_id = row[0]
    pw_hash = _hash_pw(body.password)
    db.execute(text("""
        INSERT INTO promo_influencer_auth (influencer_id, password_hash, created_at, updated_at)
        VALUES (:iid, :pw, NOW(), NOW())
    """), {"iid": inf_id, "pw": pw_hash})
    db.commit()
    return {"success": True, "id": inf_id, "referral_code": code, "vgk_member_id": vgk_member_id}


@router.put("/staff/{influencer_id}")
def update_influencer(
    influencer_id: int,
    body: UpdateInfluencerRequest,
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user),
):
    _require_promo_access(current_user)
    inf = db.execute(text("SELECT id FROM promo_influencers WHERE id = :id"), {"id": influencer_id}).fetchone()
    if not inf:
        raise HTTPException(status_code=404, detail="Influencer not found")
    sets, params = [], {"id": influencer_id}
    if body.name is not None: sets.append("name=:name"); params["name"] = body.name
    if body.email is not None: sets.append("email=:email"); params["email"] = body.email
    if body.phone is not None: sets.append("phone=:phone"); params["phone"] = body.phone
    if body.platforms is not None: sets.append("platforms=:platforms"); params["platforms"] = body.platforms
    if body.social_links is not None: sets.append("social_links=:social_links"); params["social_links"] = body.social_links
    if body.referral_code is not None: sets.append("referral_code=:code"); params["code"] = body.referral_code.upper()
    if body.status is not None: sets.append("status=:status"); params["status"] = body.status
    if body.account_type is not None: sets.append("account_type=:atype"); params["atype"] = body.account_type
    if body.is_vgk_member is not None: sets.append("is_vgk_member=:isvgk"); params["isvgk"] = body.is_vgk_member
    if body.vgk_registration_target is not None: sets.append("vgk_registration_target=:target"); params["target"] = body.vgk_registration_target
    if body.notes is not None: sets.append("notes=:notes"); params["notes"] = body.notes
    if body.budget_range is not None: sets.append("budget_range=:budget_range"); params["budget_range"] = body.budget_range
    if body.signup_bonus_points is not None: sets.append("signup_bonus_points=:signup_bonus"); params["signup_bonus"] = max(5000, body.signup_bonus_points)
    if sets:
        sets.append("updated_at=NOW()")
        db.execute(text(f"UPDATE promo_influencers SET {','.join(sets)} WHERE id=:id"), params)
    if body.new_password:
        pw_hash = _hash_pw(body.new_password)
        db.execute(text("""
            INSERT INTO promo_influencer_auth (influencer_id, password_hash, created_at, updated_at)
            VALUES (:iid, :pw, NOW(), NOW())
            ON CONFLICT (influencer_id) DO UPDATE SET password_hash=:pw, updated_at=NOW()
        """), {"iid": influencer_id, "pw": pw_hash})
    db.commit()
    return {"success": True}


@router.get("/staff/stats")
def get_dashboard_stats(
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user),
):
    _require_promo_access(current_user)
    totals = db.execute(text("""
        SELECT
            COUNT(*) AS total,
            COUNT(*) FILTER (WHERE status='active') AS active,
            COUNT(*) FILTER (WHERE status='pending') AS pending,
            COUNT(*) FILTER (WHERE status='paused') AS paused,
            COUNT(*) FILTER (WHERE status='inactive') AS inactive,
            COUNT(*) FILTER (WHERE account_type='paid') AS paid,
            COUNT(*) FILTER (WHERE is_vgk_member=true) AS vgk_members
        FROM promo_influencers
    """)).fetchone()
    events = db.execute(text("""
        SELECT
            COUNT(*) AS total_events,
            COUNT(*) FILTER (WHERE created_at >= NOW() - INTERVAL '30 days') AS last_30d,
            COUNT(*) FILTER (WHERE created_at >= NOW() - INTERVAL '7 days') AS last_7d
        FROM promo_referral_events
    """)).fetchone()
    by_portal = db.execute(text("""
        SELECT portal, COUNT(*) as cnt FROM promo_referral_events GROUP BY portal ORDER BY cnt DESC
    """)).fetchall()
    top_influencers = db.execute(text("""
        SELECT pi.name, pi.referral_code, pi.status, pi.platforms,
               COUNT(r.id) as referrals
        FROM promo_influencers pi
        LEFT JOIN promo_referral_events r ON r.influencer_id = pi.id
        GROUP BY pi.id, pi.name, pi.referral_code, pi.status, pi.platforms
        ORDER BY referrals DESC LIMIT 10
    """)).fetchall()
    by_time = db.execute(text("""
        SELECT DATE_TRUNC('day', created_at)::date::text as day, COUNT(*) as cnt
        FROM promo_referral_events
        WHERE created_at >= NOW() - INTERVAL '30 days'
        GROUP BY 1 ORDER BY 1
    """)).fetchall()
    by_platform = db.execute(text("""
        SELECT platforms, COUNT(*) as cnt FROM promo_influencers
        WHERE platforms IS NOT NULL GROUP BY platforms
    """)).fetchall()
    recent = db.execute(text("""
        SELECT r.portal, r.event_type, r.source_name, r.source_phone, r.referral_code,
               pi.name as influencer_name, r.created_at
        FROM promo_referral_events r
        JOIN promo_influencers pi ON pi.id = r.influencer_id
        ORDER BY r.created_at DESC LIMIT 20
    """)).fetchall()
    deals_agg = db.execute(text("""
        SELECT
            COUNT(*) AS total_deals,
            COALESCE(SUM(agreed_charge), 0) AS total_agreed,
            COALESCE(SUM(CASE WHEN payment_status='paid' THEN payment_amount ELSE 0 END), 0) AS total_paid,
            COALESCE(SUM(CASE WHEN payment_status='pending' THEN agreed_charge ELSE 0 END), 0) AS total_pending_amount,
            COUNT(*) FILTER (WHERE payment_status='paid') AS deals_paid,
            COUNT(*) FILTER (WHERE payment_status='pending') AS deals_pending,
            COUNT(*) FILTER (WHERE payment_status='cancelled') AS deals_cancelled
        FROM promo_deals
    """)).fetchone()
    top_by_deals = db.execute(text("""
        SELECT pi.name, pi.referral_code,
               COUNT(d.id) AS deal_count,
               COALESCE(SUM(d.agreed_charge), 0) AS deal_total,
               COALESCE(SUM(CASE WHEN d.payment_status='paid' THEN d.payment_amount ELSE 0 END), 0) AS deal_paid
        FROM promo_influencers pi
        INNER JOIN promo_deals d ON d.influencer_id = pi.id
        GROUP BY pi.id, pi.name, pi.referral_code
        ORDER BY deal_total DESC LIMIT 8
    """)).fetchall()
    by_reg_source = db.execute(text("""
        SELECT
            COALESCE(signup_source,
                CASE WHEN created_by_staff_id IS NOT NULL THEN 'staff' ELSE 'direct' END
            ) as source,
            COUNT(*) as cnt
        FROM promo_influencers
        GROUP BY source
    """)).fetchall()
    return {
        "success": True,
        "totals": dict(totals._mapping),
        "events": dict(events._mapping),
        "by_portal": [dict(r._mapping) for r in by_portal],
        "top_influencers": [dict(r._mapping) for r in top_influencers],
        "by_time": [dict(r._mapping) for r in by_time],
        "by_platform": [dict(r._mapping) for r in by_platform],
        "recent_events": [dict(r._mapping) for r in recent],
        "deals_agg": dict(deals_agg._mapping),
        "top_by_deals": [dict(r._mapping) for r in top_by_deals],
        "by_reg_source": [dict(r._mapping) for r in by_reg_source],
    }


# ─── Staff: Award Campaign Points to VGK Member via Promoter ──────────────────

class CampaignPointsRequest(BaseModel):
    influencer_id: int
    points: int = Field(..., ge=1, le=10000, description="Points to award — max 10,000 per campaign")
    campaign_name: str = Field(..., min_length=1, max_length=200)
    notes: Optional[str] = None

@router.post("/staff/campaign-points")
def award_campaign_points(
    body: CampaignPointsRequest,
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user),
):
    """
    Award up to 10,000 VGK campaign bonus points to a promoter's linked VGK account.
    Staff only. Points are written to vgk_points_ledger as CAMPAIGN_BONUS.
    """
    _require_promo_access(current_user)
    row = db.execute(text("""
        SELECT pi.id, pi.name, pi.vgk_member_id, pi.is_vgk_member,
               op.id AS vgk_db_id, op.vgk_points_balance
        FROM promo_influencers pi
        JOIN official_partners op ON op.partner_code = pi.vgk_member_id AND op.category = 'VGK_TEAM'
        WHERE pi.id = :iid
    """), {"iid": body.influencer_id}).fetchone()
    if not row:
        raise HTTPException(
            status_code=404,
            detail="Promoter not found or no linked VGK account. Cannot award campaign points."
        )
    _, inf_name, vgk_code, is_vgk, vgk_db_id, current_bal = row
    if not is_vgk or not vgk_code:
        raise HTTPException(status_code=400, detail="This promoter does not have a linked VGK account.")

    from decimal import Decimal as _Dec
    pts = _Dec(str(body.points))
    new_bal = (_Dec(str(current_bal or 0))) + pts
    note_text = f"Campaign: {body.campaign_name}"
    if body.notes:
        note_text += f" — {body.notes}"
    note_text += f" (awarded by {current_user.name or current_user.employee_id})"

    db.execute(text("""
        INSERT INTO vgk_points_ledger
            (partner_id, points_credit, points_debit, balance_after, reason_code, reference_type, notes, created_at)
        VALUES (:pid, :cr, 0, :bal, 'CAMPAIGN_BONUS', 'campaign', :notes, NOW())
    """), {"pid": vgk_db_id, "cr": pts, "bal": new_bal, "notes": note_text})
    db.execute(text(
        "UPDATE official_partners SET vgk_points_balance = :bal WHERE id = :pid"
    ), {"bal": new_bal, "pid": vgk_db_id})
    db.commit()
    print(f"[DC-PROMO] Campaign points: {body.points} awarded to {vgk_code} ({inf_name}) for '{body.campaign_name}' by {current_user.employee_id}", flush=True)
    return {
        "success": True,
        "vgk_member_id": vgk_code,
        "points_awarded": body.points,
        "new_balance": float(new_bal),
        "campaign_name": body.campaign_name,
    }


# ─── Public: Track Referral Event ─────────────────────────────────────────────

@router.post("/track")
def track_referral_event(body: TrackEventRequest, db: Session = Depends(get_db)):
    code = body.referral_code.strip().upper()
    inf = db.execute(text(
        "SELECT id, status, COALESCE(signup_bonus_points,0) as signup_bonus_points FROM promo_influencers WHERE referral_code = :c"
    ), {"c": code}).fetchone()
    if not inf:
        return {"success": False, "detail": "Code not found"}
    db.execute(text("""
        INSERT INTO promo_referral_events (influencer_id, referral_code, portal, event_type,
            source_ref_id, source_name, source_phone, created_at)
        VALUES (:iid, :code, :portal, :etype, :sref, :sname, :sphone, NOW())
    """), {
        "iid": inf[0], "code": code, "portal": body.portal, "etype": body.event_type,
        "sref": body.source_ref_id, "sname": body.source_name, "sphone": body.source_phone
    })
    db.commit()
    if body.portal == "vgk" and body.event_type == "registration":
        _auto_activate_check(db, inf[0], code)
        # Award signup bonus points to the new member if configured
        bonus_pts = int(inf[2] or 0)
        if bonus_pts > 0 and body.source_ref_id:
            try:
                from decimal import Decimal as _Dec
                from app.services.vgk_commission import add_vgk_points_entry
                member = db.execute(text(
                    "SELECT id FROM official_partners WHERE partner_code = :pc AND category = 'VGK_TEAM'"
                ), {"pc": body.source_ref_id}).fetchone()
                if member:
                    add_vgk_points_entry(
                        db=db,
                        partner_id=member[0],
                        points_credit=_Dec(str(bonus_pts)),
                        points_debit=_Dec('0'),
                        reason_code='CAMPAIGN_BONUS',
                        reference_type='referral',
                        reference_id=None,
                        notes=f"Referral signup bonus via promoter code {code}",
                        created_by=None,
                    )
                    db.commit()
                    print(f"[DC-PROMO] ✅ Signup bonus {bonus_pts} pts credited to {body.source_ref_id} via promoter code {code}", flush=True)
            except Exception as _be:
                print(f"[DC-PROMO] ⚠️ Signup bonus award failed for {body.source_ref_id}: {_be}", flush=True)
    return {"success": True}

# ─── Public Self-Registration ─────────────────────────────────────────────────

@router.post("/self-register")
def promo_self_register(body: SelfRegisterRequest, db: Session = Depends(get_db)):
    phone = (body.phone or "").strip()
    if not phone:
        raise HTTPException(status_code=400, detail="Mobile number is required")
    if not body.name or not body.name.strip():
        raise HTTPException(status_code=400, detail="Full name is required")
    if not body.password or len(body.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
    existing = db.execute(text(
        "SELECT id FROM promo_influencers WHERE phone = :phone OR (email IS NOT NULL AND email = :email)"
    ), {"phone": phone, "email": body.email or ""}).fetchone()
    if existing:
        raise HTTPException(status_code=400, detail="An account with this phone or email already exists. Please log in.")
    code = _gen_code(body.name)
    row = db.execute(text("""
        INSERT INTO promo_influencers (name, email, phone, platforms, referral_code, status,
            account_type, is_vgk_member, budget_range, signup_source, name_title, first_name, last_name, gender,
            created_at, updated_at)
        VALUES (:name, :email, :phone, :platforms, :code, 'pending',
            'unpaid', false, :budget_range, 'direct', :name_title, :first_name, :last_name, :gender,
            NOW(), NOW())
        RETURNING id
    """), {
        "name": body.name.strip(), "email": body.email,
        "phone": phone, "platforms": body.platforms,
        "code": code, "budget_range": body.budget_range,
        "name_title": (body.name_title or "").strip() or None,
        "first_name": (body.first_name or "").strip() or None,
        "last_name": (body.last_name or "").strip() or None,
        "gender": (body.gender or "").strip() or None,
    }).fetchone()
    inf_id = row[0]
    pw_hash = _hash_pw(body.password)
    db.execute(text("""
        INSERT INTO promo_influencer_auth (influencer_id, password_hash, created_at, updated_at)
        VALUES (:iid, :pw, NOW(), NOW())
    """), {"iid": inf_id, "pw": pw_hash})
    db.commit()
    return {
        "success": True,
        "message": "Registration submitted! Your account is pending approval by our team. You will be notified once activated.",
        "referral_code": code
    }


# ─── Promoter Auth ────────────────────────────────────────────────────────────

@router.post("/login")
def promo_login(body: PromoLoginRequest, db: Session = Depends(get_db)):
    login = body.login.strip()
    inf = db.execute(text("""
        SELECT pi.id, pi.name, pi.email, pi.phone, pi.referral_code, pi.status,
               pi.account_type, pi.is_vgk_member, pi.vgk_member_id,
               pi.vgk_registration_target, pi.platforms,
               a.password_hash, COALESCE(pi.signup_bonus_points, 0) as signup_bonus_points
        FROM promo_influencers pi
        JOIN promo_influencer_auth a ON a.influencer_id = pi.id
        WHERE pi.email = :login OR pi.phone = :login
        LIMIT 1
    """), {"login": login}).fetchone()
    if not inf:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if inf[5] == "inactive":
        raise HTTPException(status_code=403, detail="Account is inactive. Contact your VGK Mentor.")
    if not _verify_pw(body.password, inf[11]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = secrets.token_urlsafe(32)
    db.execute(text("""
        UPDATE promo_influencer_auth SET last_login = NOW(), session_token = :tok WHERE influencer_id = :iid
    """), {"iid": inf[0], "tok": token})
    db.commit()
    # VGK target progress
    vgk_reg_count = 0
    if inf[7]:
        vgk_reg_count = db.execute(text("""
            SELECT COUNT(*) FROM promo_referral_events
            WHERE influencer_id = :iid AND portal='vgk' AND event_type='registration'
        """), {"iid": inf[0]}).scalar() or 0
    return {
        "success": True,
        "token": token,
        "influencer": {
            "id": inf[0], "name": inf[1], "email": inf[2], "phone": inf[3],
            "referral_code": inf[4], "status": inf[5], "account_type": inf[6],
            "is_vgk_member": inf[7], "vgk_member_id": inf[8],
            "vgk_registration_target": inf[9], "platforms": inf[10],
            "vgk_reg_count": vgk_reg_count,
            "signup_bonus_points": int(inf[12] or 0)
        }
    }

class MyProfileUpdateRequest(BaseModel):
    email: Optional[str] = None
    social_links: Optional[str] = None   # JSON string with per-platform {url, followers}
    # [DC-NAME-GENDER] Apr 2026 — split name fields
    name_title: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    gender: Optional[str] = None

@router.get("/my/profile")
def my_profile(influencer_id: int = Query(...), db: Session = Depends(get_db)):
    row = db.execute(text("""
        SELECT id, name, email, phone, referral_code, status, account_type,
               is_vgk_member, vgk_member_id, vgk_registration_target,
               platforms, notes, social_links, created_at,
               COALESCE(signup_bonus_points, 0) as signup_bonus_points,
               name_title, first_name, last_name, gender
        FROM promo_influencers WHERE id = :iid
    """), {"iid": influencer_id}).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Profile not found")
    return {"success": True, "profile": dict(row._mapping)}

@router.put("/my/profile")
def update_my_profile(
    influencer_id: int = Query(...),
    body: MyProfileUpdateRequest = ...,
    db: Session = Depends(get_db),
):
    inf = db.execute(text("SELECT id FROM promo_influencers WHERE id = :iid"), {"iid": influencer_id}).fetchone()
    if not inf:
        raise HTTPException(status_code=404, detail="Profile not found")
    sets, params = [], {"iid": influencer_id}
    if body.email is not None:
        sets.append("email=:email"); params["email"] = body.email.strip() or None
    if body.social_links is not None:
        sets.append("social_links=:sl"); params["sl"] = body.social_links
    # [DC-NAME-GENDER] Save split name fields
    if body.name_title is not None:
        sets.append("name_title=:name_title"); params["name_title"] = body.name_title.strip() or None
    if body.first_name is not None:
        sets.append("first_name=:first_name"); params["first_name"] = body.first_name.strip() or None
    if body.last_name is not None:
        sets.append("last_name=:last_name"); params["last_name"] = body.last_name.strip() or None
    if body.gender is not None:
        sets.append("gender=:gender"); params["gender"] = body.gender.strip() or None
    # Rebuild display name when both first+last are set
    _fn = (body.first_name or '').strip()
    _ln = (body.last_name  or '').strip()
    if _fn and _ln:
        _t  = (body.name_title or '').strip()
        _full = ' '.join(p for p in [_t, _fn, _ln] if p)
        sets.append("name=:full_name"); params["full_name"] = _full
    if sets:
        sets.append("updated_at=NOW()")
        db.execute(text(f"UPDATE promo_influencers SET {','.join(sets)} WHERE id=:iid"), params)
        db.commit()
    return {"success": True}

@router.get("/my/stats")
def my_stats(influencer_id: int = Query(...), db: Session = Depends(get_db)):
    by_portal = db.execute(text("""
        SELECT portal, event_type, COUNT(*) as cnt
        FROM promo_referral_events WHERE influencer_id = :iid
        GROUP BY portal, event_type ORDER BY cnt DESC
    """), {"iid": influencer_id}).fetchall()
    recent = db.execute(text("""
        SELECT portal, event_type, source_name, source_phone, created_at
        FROM promo_referral_events WHERE influencer_id = :iid
        ORDER BY created_at DESC LIMIT 20
    """), {"iid": influencer_id}).fetchall()
    total = db.execute(text(
        "SELECT COUNT(*) FROM promo_referral_events WHERE influencer_id = :iid"
    ), {"iid": influencer_id}).scalar() or 0
    return {
        "success": True,
        "total": total,
        "by_portal": [dict(r._mapping) for r in by_portal],
        "recent": [dict(r._mapping) for r in recent],
    }

@router.get("/my/referral-members")
def my_referral_members(influencer_id: int = Query(...), db: Session = Depends(get_db)):
    """VGK members who signed up using this promoter's referral code, with their points balance."""
    rows = db.execute(text("""
        SELECT
            pre.source_name,
            pre.source_phone,
            pre.created_at AS joined_at,
            COALESCE(op.vgk_points_balance, 0) AS points_balance,
            COALESCE(op.is_active, false) AS is_active,
            op.partner_code
        FROM promo_referral_events pre
        LEFT JOIN official_partners op ON op.id::text = pre.source_ref_id
        WHERE pre.influencer_id = :iid
          AND pre.portal = 'vgk'
          AND pre.event_type = 'registration'
        ORDER BY pre.created_at DESC
    """), {"iid": influencer_id}).fetchall()
    members = []
    for r in rows:
        m = dict(r._mapping)
        if m.get("joined_at") and hasattr(m["joined_at"], "isoformat"):
            m["joined_at"] = m["joined_at"].isoformat()
        m["points_balance"] = float(m["points_balance"] or 0)
        m["is_active"] = bool(m.get("is_active") or False)
        members.append(m)
    return {"success": True, "members": members}

@router.get("/my/deals")
def my_deals(influencer_id: int = Query(...), db: Session = Depends(get_db)):
    """Promoter self-view of their own promotion deals (read-only)."""
    inf = db.execute(text("SELECT id FROM promo_influencers WHERE id = :iid"), {"iid": influencer_id}).fetchone()
    if not inf:
        raise HTTPException(status_code=404, detail="Promoter not found")
    rows = db.execute(text("""
        SELECT id, deal_date, promotion_name, platform, follower_count,
               agreed_charge, payment_amount, payment_status,
               payment_details, payment_date, notes
        FROM promo_deals
        WHERE influencer_id = :iid
        ORDER BY deal_date DESC NULLS LAST, id DESC
    """), {"iid": influencer_id}).fetchall()
    TDS_RATE = 0.02
    items = []
    for r in rows:
        d = dict(r._mapping)
        for k in ("deal_date", "payment_date"):
            if d.get(k) and hasattr(d[k], "isoformat"):
                d[k] = d[k].isoformat()
        agreed = float(d.get("agreed_charge") or 0)
        d["agreed_charge"] = agreed
        d["payment_amount"] = float(d.get("payment_amount") or 0)
        d["tds_amount"] = round(agreed * TDS_RATE, 2)
        d["net_payable"] = round(agreed * (1 - TDS_RATE), 2)
        items.append(d)
    total_agreed = sum(i["agreed_charge"] for i in items)
    total_tds = round(total_agreed * TDS_RATE, 2)
    total_net = round(total_agreed * (1 - TDS_RATE), 2)
    total_received = sum(i["payment_amount"] for i in items if i["payment_status"] == "paid")
    return {
        "success": True,
        "items": items,
        "summary": {
            "total_deals": len(items),
            "total_agreed": total_agreed,
            "total_tds": total_tds,
            "total_net_payable": total_net,
            "total_received": total_received,
        }
    }

@router.post("/my/change-password")
def change_my_password(
    influencer_id: int = Query(...),
    body: dict = Body(...),
    db: Session = Depends(get_db),
):
    current_pw = (body.get("current_password") or "").strip()
    new_pw = (body.get("new_password") or "").strip()
    if not current_pw or not new_pw:
        raise HTTPException(status_code=400, detail="Both current and new password are required.")
    if len(new_pw) < 6:
        raise HTTPException(status_code=400, detail="New password must be at least 6 characters.")
    auth = db.execute(text(
        "SELECT password_hash FROM promo_influencer_auth WHERE influencer_id = :iid"
    ), {"iid": influencer_id}).fetchone()
    if not auth:
        raise HTTPException(status_code=400, detail="No password set for this account. Contact your mentor.")
    if not _verify_pw(current_pw, auth[0]):
        raise HTTPException(status_code=401, detail="Current password is incorrect.")
    new_hash = _hash_pw(new_pw)
    db.execute(text("""
        UPDATE promo_influencer_auth SET password_hash=:pw, updated_at=NOW() WHERE influencer_id=:iid
    """), {"pw": new_hash, "iid": influencer_id})
    db.commit()
    return {"success": True, "message": "Password changed successfully."}

# ─── VGK Member Silent Creation Helper ────────────────────────────────────────

def _create_vgk_member_silent(db: Session, name: str, phone: Optional[str], email: Optional[str],
                               welcome_pts: int = 15000, source: str = "promoter portal") -> Optional[str]:
    """Silently create a VGK loyalty member and return their member ID.
    welcome_pts: 15000 for promoters (10k welcome + 5k promo bonus), 10000 for partners/standard."""
    import random as _rnd
    from app.core.security import SecurityManager
    VGK_DEFAULT_ROOT = 'VGK07102207'
    if not phone:
        return None
    try:
        existing = db.execute(text(
            "SELECT partner_code FROM official_partners WHERE phone = :p AND category = 'VGK_TEAM' LIMIT 1"
        ), {"p": phone}).fetchone()
        if existing:
            return existing[0]
        referrer = db.execute(text(
            "SELECT id FROM official_partners WHERE partner_code = :c AND category = 'VGK_TEAM' LIMIT 1"
        ), {"c": VGK_DEFAULT_ROOT}).fetchone()
        parent_id = referrer[0] if referrer else None
        partner_code = None
        for _ in range(50):
            rand4 = _rnd.randint(1000, 9999)
            code = f"VGK0710{rand4}"
            if not db.execute(text("SELECT 1 FROM official_partners WHERE partner_code = :c"), {"c": code}).fetchone():
                partner_code = code
                break
        if not partner_code:
            return None
        company_id = db.execute(text("SELECT MIN(id) FROM associated_companies")).scalar() or 4
        pw_hash = SecurityManager.get_password_hash("VGK" + (phone[-4:] if len(phone) >= 4 else "1234"))
        if welcome_pts == 15000:
            ledger_note = f"Welcome bonus + Promoter bonus — registered via {source} (10,000 + 5,000 VGK Discount Credits)"
        else:
            ledger_note = f"Welcome bonus — registered via {source} ({welcome_pts:,} VGK Discount Credits)"
        db.execute(text("""
            INSERT INTO official_partners (company_id, partner_code, partner_name, phone, email,
                category, is_active, parent_partner_id, vgk_role, vgk_points_balance, password_hash, created_at, updated_at)
            VALUES (:cid, :code, :name, :phone, :email, 'VGK_TEAM', false, :parent,
                'VGK_ASSOCIATE', :pts, :pw, NOW(), NOW())
        """), {
            "cid": company_id, "code": partner_code, "name": name,
            "phone": phone, "email": email, "parent": parent_id, "pw": pw_hash,
            "pts": welcome_pts
        })
        # Get the new member's DB id to write the ledger entry
        new_id = db.execute(text(
            "SELECT id FROM official_partners WHERE partner_code = :c LIMIT 1"
        ), {"c": partner_code}).scalar()
        if new_id:
            db.execute(text("""
                INSERT INTO vgk_points_ledger
                    (partner_id, points_credit, points_debit, balance_after, reason_code, reference_type, notes, created_at)
                VALUES (:pid, :cr, 0, :bal, 'WELCOME_BONUS', 'signup', :note, NOW())
            """), {"pid": new_id, "cr": welcome_pts, "bal": welcome_pts, "note": ledger_note})
        db.commit()
        print(f"[DC-PROMO] VGK member created silently: {partner_code} for {source} — {name} ({welcome_pts} pts)", flush=True)
        return partner_code
    except Exception as e:
        print(f"[DC-PROMO] VGK silent create error (non-fatal): {e}", flush=True)
        db.rollback()
        return None


# ─── Promotion Deals CRUD ─────────────────────────────────────────────────────

class CreateDealRequest(BaseModel):
    influencer_id: int
    deal_date: Optional[str] = None          # ISO date string YYYY-MM-DD
    promotion_name: Optional[str] = None
    platform: Optional[str] = None
    follower_count: Optional[int] = 0
    agreed_charge: Optional[float] = 0
    payment_amount: Optional[float] = 0
    payment_status: str = "pending"          # paid | pending | cancelled
    payment_details: Optional[str] = None
    payment_date: Optional[str] = None
    notes: Optional[str] = None

class UpdateDealRequest(BaseModel):
    deal_date: Optional[str] = None
    promotion_name: Optional[str] = None
    platform: Optional[str] = None
    follower_count: Optional[int] = None
    agreed_charge: Optional[float] = None
    payment_amount: Optional[float] = None
    payment_status: Optional[str] = None
    payment_details: Optional[str] = None
    payment_date: Optional[str] = None
    notes: Optional[str] = None


@router.get("/staff/deals")
def list_deals(
    influencer_id: int = Query(...),
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user),
):
    _require_promo_access(current_user)
    rows = db.execute(text("""
        SELECT id, influencer_id, deal_date, promotion_name, platform,
               follower_count, agreed_charge, payment_amount, payment_status,
               payment_details, payment_date, notes, created_at, updated_at
        FROM promo_deals
        WHERE influencer_id = :iid
        ORDER BY deal_date DESC NULLS LAST, created_at DESC
    """), {"iid": influencer_id}).fetchall()
    items = []
    for r in rows:
        d = dict(r._mapping)
        # Serialize dates to strings for JSON
        for key in ("deal_date", "payment_date", "created_at", "updated_at"):
            if d.get(key) and hasattr(d[key], "isoformat"):
                d[key] = d[key].isoformat()
        for key in ("agreed_charge", "payment_amount"):
            if d.get(key) is not None:
                d[key] = float(d[key])
        items.append(d)
    return {"success": True, "items": items}


@router.post("/staff/deals")
def create_deal(
    body: CreateDealRequest,
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user),
):
    _require_promo_access(current_user)
    inf = db.execute(text("SELECT id FROM promo_influencers WHERE id = :id"), {"id": body.influencer_id}).fetchone()
    if not inf:
        raise HTTPException(status_code=404, detail="Influencer not found")
    row = db.execute(text("""
        INSERT INTO promo_deals (influencer_id, deal_date, promotion_name, platform,
            follower_count, agreed_charge, payment_amount, payment_status,
            payment_details, payment_date, notes, created_by_staff_id, created_at, updated_at)
        VALUES (:iid, :dd, :name, :platform, :fc, :charge, :paid, :pstatus,
                :pdetails, :pdate, :notes, :staff, NOW(), NOW())
        RETURNING id
    """), {
        "iid": body.influencer_id,
        "dd": body.deal_date or None,
        "name": body.promotion_name,
        "platform": body.platform,
        "fc": body.follower_count or 0,
        "charge": body.agreed_charge or 0,
        "paid": body.payment_amount or 0,
        "pstatus": body.payment_status,
        "pdetails": body.payment_details,
        "pdate": body.payment_date or None,
        "notes": body.notes,
        "staff": current_user.id,
    }).fetchone()
    db.commit()
    return {"success": True, "id": row[0]}


@router.put("/staff/deals/{deal_id}")
def update_deal(
    deal_id: int,
    body: UpdateDealRequest,
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user),
):
    _require_promo_access(current_user)
    existing = db.execute(text("SELECT id FROM promo_deals WHERE id = :id"), {"id": deal_id}).fetchone()
    if not existing:
        raise HTTPException(status_code=404, detail="Deal not found")
    sets, params = [], {"id": deal_id}
    if body.deal_date is not None: sets.append("deal_date=:dd"); params["dd"] = body.deal_date or None
    if body.promotion_name is not None: sets.append("promotion_name=:name"); params["name"] = body.promotion_name
    if body.platform is not None: sets.append("platform=:platform"); params["platform"] = body.platform
    if body.follower_count is not None: sets.append("follower_count=:fc"); params["fc"] = body.follower_count
    if body.agreed_charge is not None: sets.append("agreed_charge=:charge"); params["charge"] = body.agreed_charge
    if body.payment_amount is not None: sets.append("payment_amount=:paid"); params["paid"] = body.payment_amount
    if body.payment_status is not None: sets.append("payment_status=:pstatus"); params["pstatus"] = body.payment_status
    if body.payment_details is not None: sets.append("payment_details=:pdetails"); params["pdetails"] = body.payment_details
    if body.payment_date is not None: sets.append("payment_date=:pdate"); params["pdate"] = body.payment_date or None
    if body.notes is not None: sets.append("notes=:notes"); params["notes"] = body.notes
    if sets:
        sets.append("updated_at=NOW()")
        db.execute(text(f"UPDATE promo_deals SET {','.join(sets)} WHERE id=:id"), params)
    db.commit()
    return {"success": True}


@router.delete("/staff/deals/{deal_id}")
def delete_deal(
    deal_id: int,
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user),
):
    _require_promo_access(current_user)
    existing = db.execute(text("SELECT id FROM promo_deals WHERE id = :id"), {"id": deal_id}).fetchone()
    if not existing:
        raise HTTPException(status_code=404, detail="Deal not found")
    db.execute(text("DELETE FROM promo_deals WHERE id = :id"), {"id": deal_id})
    db.commit()
    return {"success": True}


# ═══════════════════════════════════════════════════════════════════════════════
# MARKETPLACE PRODUCTS — DC Protocol Apr 2026
# ═══════════════════════════════════════════════════════════════════════════════

import json as _json
from fastapi.responses import RedirectResponse

class MarketplaceProductRequest(BaseModel):
    title: str
    category: Optional[str] = None
    description: Optional[str] = None
    specifications: Optional[dict] = {}
    image_urls: Optional[list] = []
    video_url: Optional[str] = None
    product_link: str
    sample_link: Optional[str] = None
    is_active: bool = True
    notes: Optional[str] = None


def _row_to_product(r: dict) -> dict:
    """Serialize a marketplace product row to a JSON-safe dict."""
    d = dict(r)
    for k in ("created_at", "updated_at"):
        if d.get(k) and hasattr(d[k], "isoformat"):
            d[k] = d[k].isoformat()
    for k in ("specifications", "image_urls"):
        v = d.get(k)
        if isinstance(v, str):
            try:
                d[k] = _json.loads(v)
            except Exception:
                d[k] = {} if k == "specifications" else []
        elif v is None:
            d[k] = {} if k == "specifications" else []
    return d


@router.get("/staff/marketplace-products")
def staff_list_products(
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user),
):
    _require_promo_access(current_user)
    rows = db.execute(text("""
        SELECT p.*, COALESCE(c.clicks,0) AS click_count
        FROM promo_marketplace_products p
        LEFT JOIN (
            SELECT product_id, COUNT(*) AS clicks FROM promo_product_clicks GROUP BY product_id
        ) c ON c.product_id = p.id
        ORDER BY p.is_active DESC, p.created_at DESC
    """)).fetchall()
    return {"success": True, "items": [_row_to_product(dict(r._mapping)) for r in rows]}


@router.post("/staff/marketplace-products")
def staff_create_product(
    body: MarketplaceProductRequest,
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user),
):
    _require_promo_access(current_user)
    row = db.execute(text("""
        INSERT INTO promo_marketplace_products
            (title, category, description, specifications, image_urls, video_url,
             product_link, sample_link, is_active, notes, created_by_staff_id)
        VALUES (:title,:category,:description,:specs,:imgs,:video,
                :plink,:slink,:active,:notes,:staff_id)
        RETURNING id
    """), {
        "title": body.title.strip(),
        "category": (body.category or "").strip() or None,
        "description": (body.description or "").strip() or None,
        "specs": _json.dumps(body.specifications or {}),
        "imgs": _json.dumps(body.image_urls or []),
        "video": (body.video_url or "").strip() or None,
        "plink": body.product_link.strip(),
        "slink": (body.sample_link or "").strip() or None,
        "active": body.is_active,
        "notes": (body.notes or "").strip() or None,
        "staff_id": current_user.id,
    }).fetchone()
    db.commit()
    return {"success": True, "id": row[0]}


@router.put("/staff/marketplace-products/{product_id}")
def staff_update_product(
    product_id: int,
    body: MarketplaceProductRequest,
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user),
):
    _require_promo_access(current_user)
    existing = db.execute(text("SELECT id FROM promo_marketplace_products WHERE id=:id"), {"id": product_id}).fetchone()
    if not existing:
        raise HTTPException(status_code=404, detail="Product not found")
    db.execute(text("""
        UPDATE promo_marketplace_products SET
            title=:title, category=:category, description=:description,
            specifications=:specs, image_urls=:imgs, video_url=:video,
            product_link=:plink, sample_link=:slink,
            is_active=:active, notes=:notes, updated_at=NOW()
        WHERE id=:id
    """), {
        "id": product_id,
        "title": body.title.strip(),
        "category": (body.category or "").strip() or None,
        "description": (body.description or "").strip() or None,
        "specs": _json.dumps(body.specifications or {}),
        "imgs": _json.dumps(body.image_urls or []),
        "video": (body.video_url or "").strip() or None,
        "plink": body.product_link.strip(),
        "slink": (body.sample_link or "").strip() or None,
        "active": body.is_active,
        "notes": (body.notes or "").strip() or None,
    })
    db.commit()
    return {"success": True}


@router.delete("/staff/marketplace-products/{product_id}")
def staff_delete_product(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user),
):
    _require_promo_access(current_user)
    existing = db.execute(text("SELECT id FROM promo_marketplace_products WHERE id=:id"), {"id": product_id}).fetchone()
    if not existing:
        raise HTTPException(status_code=404, detail="Product not found")
    db.execute(text("DELETE FROM promo_marketplace_products WHERE id=:id"), {"id": product_id})
    db.commit()
    return {"success": True}


@router.get("/my/marketplace-products")
def my_marketplace_products(influencer_id: int = Query(...), db: Session = Depends(get_db)):
    """Promoter self-view: only active products with personal tracked redirect link."""
    inf = db.execute(
        text("SELECT id, referral_code FROM promo_influencers WHERE id=:iid"),
        {"iid": influencer_id}
    ).fetchone()
    if not inf:
        raise HTTPException(status_code=404, detail="Promoter not found")
    ref_code = inf[1]
    rows = db.execute(text("""
        SELECT p.id, p.title, p.category, p.description, p.specifications,
               p.image_urls, p.video_url, p.product_link, p.sample_link
        FROM promo_marketplace_products p
        WHERE p.is_active = TRUE
        ORDER BY p.category NULLS LAST, p.title
    """)).fetchall()
    items = []
    for r in rows:
        d = _row_to_product(dict(r._mapping))
        d["tracked_link"] = f"/r/{d['id']}/{ref_code}"
        items.append(d)
    categories = sorted({i["category"] for i in items if i.get("category")})
    return {"success": True, "items": items, "categories": categories}


@router.get("/r/{product_id}/{referral_code}")
def product_redirect(
    product_id: int,
    referral_code: str,
    request: Request,
    db: Session = Depends(get_db),
):
    """Public tracked redirect: logs click then redirects to product URL."""
    prod = db.execute(
        text("SELECT id, product_link FROM promo_marketplace_products WHERE id=:id AND is_active=TRUE"),
        {"id": product_id}
    ).fetchone()
    if not prod:
        raise HTTPException(status_code=404, detail="Product not found or inactive")
    inf = db.execute(
        text("SELECT id FROM promo_influencers WHERE referral_code=:code"),
        {"code": referral_code}
    ).fetchone()
    inf_id = inf[0] if inf else None
    # Log click
    ip = request.headers.get("x-forwarded-for", request.client.host if request.client else None)
    db.execute(text("""
        INSERT INTO promo_product_clicks (product_id, influencer_id, referral_code, ip_address)
        VALUES (:pid, :iid, :code, :ip)
    """), {"pid": product_id, "iid": inf_id, "code": referral_code, "ip": ip})
    db.commit()
    # Build destination URL (append ref param)
    dest = prod[1]
    sep = "&" if "?" in dest else "?"
    return RedirectResponse(url=f"{dest}{sep}ref={referral_code}", status_code=302)


# ─── Staff: Promoter TDS Summary (for Accounts / TDS page) ───────────────────

@router.get("/staff/promoter-tds-summary")
def staff_promoter_tds_summary(
    status: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user),
):
    _require_promo_access(current_user)
    filters = ["1=1"]
    params: dict = {}
    if status:
        filters.append("d.payment_status = :status")
        params["status"] = status
    if date_from:
        filters.append("d.payment_date >= :date_from")
        params["date_from"] = date_from
    if date_to:
        filters.append("d.payment_date <= :date_to")
        params["date_to"] = date_to
    where = " AND ".join(filters)
    rows = db.execute(text(f"""
        SELECT i.name AS promoter_name, i.referral_code,
               d.id AS deal_id, d.promotion_name, d.platform,
               d.agreed_charge, d.payment_amount, d.payment_status,
               d.payment_date, d.deal_date, d.payment_details,
               ROUND(d.agreed_charge * 0.02, 2) AS tds_amount
        FROM promo_deals d
        JOIN promo_influencers i ON i.id = d.influencer_id
        WHERE {where}
        ORDER BY d.payment_date DESC NULLS LAST, d.created_at DESC
    """), params).fetchall()
    items = []
    for r in rows:
        d = dict(r._mapping)
        for k in ("payment_date", "deal_date"):
            if d.get(k) and hasattr(d[k], "isoformat"):
                d[k] = d[k].isoformat()
        for k in ("agreed_charge", "payment_amount", "tds_amount"):
            d[k] = float(d.get(k) or 0)
        items.append(d)
    # Summary — TDS on PAID deals is government-payable liability
    tds_on_paid = sum(i["tds_amount"] for i in items if i["payment_status"] == "paid")
    tds_on_pending = sum(i["tds_amount"] for i in items if i["payment_status"] == "pending")
    total_tds = sum(i["tds_amount"] for i in items)
    return {
        "success": True,
        "items": items,
        "summary": {
            "total_deals": len(items),
            "total_tds": total_tds,
            "tds_payable": tds_on_paid,
            "tds_pending_liability": tds_on_pending,
            "tds_cancelled": total_tds - tds_on_paid - tds_on_pending,
        }
    }


# ─── Cross-Auth Toggle: Promoter ↔ VGK Portal ───────────────────────────────

class _CrossAuthGenerateRequest(BaseModel):
    influencer_id: int
    promo_token: str

class _CrossAuthRedeemRequest(BaseModel):
    cross_token: str

def _issue_cross_token(db: Session, influencer_id: Optional[int], vgk_partner_code: Optional[str], direction: str) -> str:
    from datetime import datetime as _dt
    tok = secrets.token_urlsafe(48)
    expires = _dt.utcnow() + timedelta(minutes=2)
    db.execute(text("""
        INSERT INTO promo_cross_auth_tokens (token, influencer_id, vgk_partner_code, direction, expires_at)
        VALUES (:tok, :iid, :code, :dir, :exp)
    """), {"tok": tok, "iid": influencer_id, "code": vgk_partner_code, "dir": direction, "exp": expires})
    db.commit()
    return tok

@router.get("/cross-auth/check-promo-link")
def check_promo_link(partner_code: str = Query(...), db: Session = Depends(get_db)):
    """Check if a VGK partner code has a linked promoter account."""
    row = db.execute(text("""
        SELECT id, name FROM promo_influencers
        WHERE vgk_member_id = :code AND is_vgk_member = true LIMIT 1
    """), {"code": partner_code}).fetchone()
    if row:
        return {"success": True, "linked": True, "promoter_name": row[1]}
    return {"success": True, "linked": False}


@router.get("/cross-auth/check-partner-link")
def check_partner_link(partner_code: str = Query(...), db: Session = Depends(get_db)):
    """Check if a VGK member (by their partner_code) has a separate non-VGK partner account (matched by phone)."""
    vgk_phone = db.execute(text(
        "SELECT phone FROM official_partners WHERE partner_code = :code AND category = 'VGK_TEAM' LIMIT 1"
    ), {"code": partner_code}).scalar()
    if not vgk_phone:
        return {"success": True, "linked": False}
    partner = db.execute(text("""
        SELECT id, partner_code, partner_name FROM official_partners
        WHERE phone = :phone AND category != 'VGK_TEAM' AND is_active = true LIMIT 1
    """), {"phone": vgk_phone}).fetchone()
    if partner:
        return {"success": True, "linked": True, "partner_name": partner[2]}
    return {"success": True, "linked": False}


# DC Protocol (Apr 2026): T008 — Validate promoter referral code (no event creation, no auth required)
@router.get("/validate-code")
def validate_referral_code(code: str = Query(...), db: Session = Depends(get_db)):
    """Check if a promoter referral code is valid (active influencer) — used on signup form blur."""
    code_val = code.strip().upper()
    inf = db.execute(text(
        "SELECT id, name, status FROM promo_influencers WHERE referral_code = :c AND status = 'active'"
    ), {"c": code_val}).fetchone()
    if inf:
        return {"valid": True, "name": inf[1]}
    return {"valid": False}


@router.get("/cross-auth/check-vgk-link")
def check_vgk_link(partner_code: str = Query(...), db: Session = Depends(get_db)):
    """Check if a partner (by their partner_code) has a linked VGK account (matched by phone)."""
    partner_phone = db.execute(text(
        "SELECT phone FROM official_partners WHERE partner_code = :code AND category != 'VGK_TEAM' LIMIT 1"
    ), {"code": partner_code}).scalar()
    if not partner_phone:
        return {"success": True, "linked": False}
    vgk = db.execute(text("""
        SELECT id, partner_code, partner_name FROM official_partners
        WHERE phone = :phone AND category = 'VGK_TEAM' AND is_active = true LIMIT 1
    """), {"phone": partner_phone}).fetchone()
    if vgk:
        return {"success": True, "linked": True, "vgk_name": vgk[2]}
    return {"success": True, "linked": False}

@router.post("/cross-auth/auto-link-vgk")
def cross_auth_auto_link_vgk(body: _CrossAuthGenerateRequest, db: Session = Depends(get_db)):
    """Auto-create a VGK4U account for a promoter (if not already linked) using their stored details,
    then issue a cross-auth token — no manual registration required."""
    row = db.execute(text("""
        SELECT pa.session_token, pi.vgk_member_id, pi.is_vgk_member, pi.name, pi.phone, pi.email
        FROM promo_influencer_auth pa
        JOIN promo_influencers pi ON pi.id = pa.influencer_id
        WHERE pa.influencer_id = :iid
    """), {"iid": body.influencer_id}).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Promoter not found")
    if not row[0] or row[0] != body.promo_token:
        raise HTTPException(status_code=401, detail="Invalid or expired session")

    session_token, vgk_member_id, is_vgk, name, phone, email = row
    created = False

    # Already linked — just issue the token
    if is_vgk and vgk_member_id:
        tok = _issue_cross_token(db, body.influencer_id, vgk_member_id, "promo_to_vgk")
        return {"success": True, "cross_token": tok, "expires_in": 120, "created": False, "vgk_member_id": vgk_member_id}

    # Not linked — silently create VGK account using existing promoter details
    if not phone:
        raise HTTPException(status_code=400, detail="Phone number required to auto-create VGK account. Please update your profile.")
    new_vgk_id = _create_vgk_member_silent(db, name, phone, email)
    if not new_vgk_id:
        raise HTTPException(status_code=500, detail="Could not auto-create VGK account. Please contact support.")

    # Link the VGK account to this promoter
    db.execute(text("""
        UPDATE promo_influencers
        SET is_vgk_member = true, vgk_member_id = :vid, updated_at = NOW()
        WHERE id = :iid
    """), {"vid": new_vgk_id, "iid": body.influencer_id})
    db.commit()
    created = True

    tok = _issue_cross_token(db, body.influencer_id, new_vgk_id, "promo_to_vgk")
    return {"success": True, "cross_token": tok, "expires_in": 120, "created": created, "vgk_member_id": new_vgk_id}


@router.post("/cross-auth/generate-promo-to-vgk")
def cross_auth_generate_promo_to_vgk(body: _CrossAuthGenerateRequest, db: Session = Depends(get_db)):
    """Promoter side: verify session and issue a 2-min one-time cross-auth token for VGK login."""
    row = db.execute(text("""
        SELECT pa.session_token, pi.vgk_member_id, pi.is_vgk_member, pi.name
        FROM promo_influencer_auth pa
        JOIN promo_influencers pi ON pi.id = pa.influencer_id
        WHERE pa.influencer_id = :iid
    """), {"iid": body.influencer_id}).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Promoter not found")
    if not row[0] or row[0] != body.promo_token:
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    if not row[2] or not row[1]:
        raise HTTPException(status_code=400, detail="No VGK account linked to this promoter")
    tok = _issue_cross_token(db, body.influencer_id, row[1], "promo_to_vgk")
    return {"success": True, "cross_token": tok, "expires_in": 120}

@router.post("/cross-auth/redeem-to-vgk")
def cross_auth_redeem_to_vgk(body: _CrossAuthRedeemRequest, db: Session = Depends(get_db)):
    """Redeem a promo→vgk or partner→vgk cross-auth token and return a VGK JWT."""
    from datetime import datetime as _dt
    row = db.execute(text("""
        SELECT id, vgk_partner_code, expires_at, used_at
        FROM promo_cross_auth_tokens
        WHERE token = :tok AND direction IN ('promo_to_vgk', 'partner_to_vgk')
    """), {"tok": body.cross_token}).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Invalid cross-auth token")
    if row[3] is not None:
        raise HTTPException(status_code=410, detail="Token already used")
    if row[2] < _dt.utcnow():
        raise HTTPException(status_code=410, detail="Token expired")
    partner_code = row[1]
    partner = db.execute(text("""
        SELECT id, partner_code, partner_name, category, email, phone, login_status
        FROM official_partners WHERE partner_code = :code AND category = 'VGK_TEAM'
    """), {"code": partner_code}).fetchone()
    if not partner:
        raise HTTPException(status_code=404, detail="VGK account not found")
    company_rows = db.execute(text("""
        SELECT company_id, is_primary FROM partner_company_segments
        WHERE partner_id = :pid AND is_active = true
    """), {"pid": partner[0]}).fetchall()
    company_ids = [r[0] for r in company_rows]
    primary_company_id = next((r[0] for r in company_rows if r[1]), company_ids[0] if company_ids else None)
    db.execute(text("UPDATE promo_cross_auth_tokens SET used_at = NOW() WHERE id = :id"), {"id": row[0]})
    db.commit()
    vgk_role = db.execute(text(
        "SELECT vgk_role FROM official_partners WHERE id = :pid"
    ), {"pid": partner[0]}).scalar() or "VGK_ASSOCIATE"
    from jose import jwt as _jwt
    from app.core.config import settings as _settings
    token_data = {
        "sub": str(partner[0]),
        "user_type": "vgk_member",
        "partner_code": partner[1],
        "partner_name": partner[2],
        "category": partner[3],
        "vgk_role": vgk_role,
        "company_id": primary_company_id,
        "company_ids": company_ids,
        "primary_company_id": primary_company_id,
        "exp": _dt.utcnow() + timedelta(hours=24)
    }
    access_token = _jwt.encode(token_data, _settings.SECRET_KEY, algorithm=_settings.ALGORITHM)
    return {
        "success": True,
        "access_token": access_token,
        "partner": {
            "id": partner[0], "partner_code": partner[1], "partner_name": partner[2],
            "category": partner[3], "email": partner[4], "phone": partner[5],
            "company_ids": company_ids, "primary_company_id": primary_company_id,
            "login_status": partner[6] or "active"
        }
    }

@router.post("/cross-auth/generate-vgk-to-promo")
def cross_auth_generate_vgk_to_promo(request: Request, db: Session = Depends(get_db)):
    """VGK side: verify VGK JWT and issue a 2-min cross-auth token for promoter login."""
    from datetime import datetime as _dt
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing VGK authorization")
    vgk_token = auth_header.split(" ", 1)[1]
    try:
        from jose import jwt as _jwt, JWTError
        from app.core.config import settings as _settings
        payload = _jwt.decode(vgk_token, _settings.SECRET_KEY, algorithms=[_settings.ALGORITHM])
        user_type = payload.get("user_type")
        if user_type not in ("vgk_member", "partner"):
            raise HTTPException(status_code=401, detail="Invalid token type — VGK token required")
        partner_code = payload.get("partner_code")
        if not partner_code:
            raise HTTPException(status_code=401, detail="Token missing partner_code")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired VGK token")
    inf = db.execute(text("""
        SELECT id FROM promo_influencers WHERE vgk_member_id = :code AND is_vgk_member = true
    """), {"code": partner_code}).fetchone()
    if not inf:
        raise HTTPException(status_code=404, detail="No Promoter account linked to this VGK member")
    tok = _issue_cross_token(db, inf[0], partner_code, "vgk_to_promo")
    return {"success": True, "cross_token": tok, "expires_in": 120}

@router.post("/cross-auth/redeem-to-promo")
def cross_auth_redeem_to_promo(body: _CrossAuthRedeemRequest, db: Session = Depends(get_db)):
    """Redeem a vgk→promo cross-auth token and return a new promoter session."""
    from datetime import datetime as _dt
    row = db.execute(text("""
        SELECT id, influencer_id, expires_at, used_at
        FROM promo_cross_auth_tokens
        WHERE token = :tok AND direction = 'vgk_to_promo'
    """), {"tok": body.cross_token}).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Invalid cross-auth token")
    if row[3] is not None:
        raise HTTPException(status_code=410, detail="Token already used")
    if row[2] < _dt.utcnow():
        raise HTTPException(status_code=410, detail="Token expired")
    inf_id = row[1]
    inf = db.execute(text("""
        SELECT pi.id, pi.name, pi.email, pi.phone, pi.referral_code, pi.status,
               pi.account_type, pi.is_vgk_member, pi.vgk_member_id,
               pi.vgk_registration_target, pi.platforms
        FROM promo_influencers pi WHERE pi.id = :iid
    """), {"iid": inf_id}).fetchone()
    if not inf:
        raise HTTPException(status_code=404, detail="Promoter not found")
    new_token = secrets.token_urlsafe(32)
    db.execute(text("""
        UPDATE promo_cross_auth_tokens SET used_at = NOW() WHERE id = :id
    """), {"id": row[0]})
    db.execute(text("""
        UPDATE promo_influencer_auth SET last_login = NOW(), session_token = :tok WHERE influencer_id = :iid
    """), {"iid": inf_id, "tok": new_token})
    db.commit()
    return {
        "success": True,
        "token": new_token,
        "influencer": {
            "id": inf[0], "name": inf[1], "email": inf[2], "phone": inf[3],
            "referral_code": inf[4], "status": inf[5], "account_type": inf[6],
            "is_vgk_member": inf[7], "vgk_member_id": inf[8],
            "vgk_registration_target": inf[9], "platforms": inf[10],
            "vgk_reg_count": 0
        }
    }


@router.post("/cross-auth/generate-vgk-to-partner")
def cross_auth_generate_vgk_to_partner(request: Request, db: Session = Depends(get_db)):
    """VGK side: verify VGK JWT, look up linked non-VGK partner account by phone, issue cross-auth token."""
    from datetime import datetime as _dt
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing VGK authorization")
    vgk_token = auth_header.split(" ", 1)[1]
    try:
        from jose import jwt as _jwt, JWTError
        from app.core.config import settings as _settings
        payload = _jwt.decode(vgk_token, _settings.SECRET_KEY, algorithms=[_settings.ALGORITHM])
        user_type = payload.get("user_type")
        if user_type not in ("vgk_member", "partner"):
            raise HTTPException(status_code=401, detail="Invalid token type — VGK token required")
        vgk_code = payload.get("partner_code")
        if not vgk_code:
            raise HTTPException(status_code=401, detail="Token missing partner_code")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired VGK token")
    # Look up the VGK member's phone, then find their non-VGK partner account
    vgk_phone = db.execute(text(
        "SELECT phone FROM official_partners WHERE partner_code = :code AND category = 'VGK_TEAM' LIMIT 1"
    ), {"code": vgk_code}).scalar()
    if not vgk_phone:
        raise HTTPException(status_code=404, detail="VGK member not found")
    partner = db.execute(text("""
        SELECT partner_code FROM official_partners
        WHERE phone = :phone AND category != 'VGK_TEAM' AND is_active = true LIMIT 1
    """), {"phone": vgk_phone}).fetchone()
    if not partner:
        raise HTTPException(status_code=404, detail="No Partner account linked to this VGK member")
    tok = _issue_cross_token(db, None, partner[0], "vgk_to_partner")
    return {"success": True, "cross_token": tok, "expires_in": 120}


@router.post("/cross-auth/redeem-to-partner")
def cross_auth_redeem_to_partner(body: _CrossAuthRedeemRequest, db: Session = Depends(get_db)):
    """Redeem a vgk→partner cross-auth token and return a partner portal JWT."""
    from datetime import datetime as _dt
    row = db.execute(text("""
        SELECT id, vgk_partner_code, expires_at, used_at
        FROM promo_cross_auth_tokens
        WHERE token = :tok AND direction = 'vgk_to_partner'
    """), {"tok": body.cross_token}).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Invalid cross-auth token")
    if row[3] is not None:
        raise HTTPException(status_code=410, detail="Token already used")
    if row[2] < _dt.utcnow():
        raise HTTPException(status_code=410, detail="Token expired")
    partner_code = row[1]
    partner = db.execute(text("""
        SELECT id, partner_code, partner_name, category, email, phone, company_id
        FROM official_partners WHERE partner_code = :code
    """), {"code": partner_code}).fetchone()
    if not partner:
        raise HTTPException(status_code=404, detail="Partner account not found")
    company_rows = db.execute(text("""
        SELECT company_id, is_primary FROM partner_company_segments
        WHERE partner_id = :pid AND is_active = true
    """), {"pid": partner[0]}).fetchall()
    company_ids = [r[0] for r in company_rows]
    primary_company_id = next((r[0] for r in company_rows if r[1]), company_ids[0] if company_ids else partner[6])
    db.execute(text("UPDATE promo_cross_auth_tokens SET used_at = NOW() WHERE id = :id"), {"id": row[0]})
    db.commit()
    from jose import jwt as _jwt
    from app.core.config import settings as _settings
    token_data = {
        "sub": str(partner[0]),
        "user_type": "partner",
        "partner_code": partner[1],
        "category": partner[3],
        "company_ids": company_ids,
        "primary_company_id": primary_company_id,
        "exp": _dt.utcnow() + timedelta(hours=24)
    }
    access_token = _jwt.encode(token_data, _settings.SECRET_KEY, algorithm=_settings.ALGORITHM)
    return {
        "success": True,
        "access_token": access_token,
        "partner": {
            "id": partner[0], "partner_code": partner[1], "partner_name": partner[2],
            "category": partner[3], "email": partner[4], "phone": partner[5],
            "company_ids": company_ids, "primary_company_id": primary_company_id
        }
    }


@router.post("/cross-auth/generate-partner-to-vgk")
def cross_auth_generate_partner_to_vgk(request: Request, db: Session = Depends(get_db)):
    """Partner side: verify partner JWT and issue a 2-min cross-auth token for VGK portal login.
    Looks up VGK account by matching phone number (category=VGK_TEAM)."""
    from datetime import datetime as _dt
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing partner authorization")
    partner_token = auth_header.split(" ", 1)[1]
    try:
        from jose import jwt as _jwt, JWTError
        from app.core.config import settings as _settings
        payload = _jwt.decode(partner_token, _settings.SECRET_KEY, algorithms=[_settings.ALGORITHM])
        user_type = payload.get("user_type")
        if user_type not in ("partner", "vgk_member"):
            raise HTTPException(status_code=401, detail="Invalid token type — partner token required")
        partner_id = payload.get("sub")
        partner_code = payload.get("partner_code")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired partner token")
    # Look up the partner record by partner_code (always in JWT, most reliable key)
    partner_record = db.execute(text(
        "SELECT id, phone, partner_name, email FROM official_partners WHERE partner_code = :code AND category != 'VGK_TEAM' LIMIT 1"
    ), {"code": partner_code}).fetchone()
    if not partner_record:
        raise HTTPException(status_code=404, detail="Partner account not found")
    partner_phone = partner_record[1]
    partner_name  = partner_record[2]
    partner_email = partner_record[3]
    if not partner_phone:
        raise HTTPException(status_code=400, detail="Mobile number not set on your partner profile. Please update your profile before accessing VGK4U.")
    # Check if VGK account already linked by phone
    vgk_member = db.execute(text("""
        SELECT id, partner_code FROM official_partners
        WHERE phone = :phone AND category = 'VGK_TEAM' LIMIT 1
    """), {"phone": partner_phone}).fetchone()
    if vgk_member:
        tok = _issue_cross_token(db, None, vgk_member[1], "partner_to_vgk")
        return {"success": True, "cross_token": tok, "expires_in": 120, "created": False}
    # No VGK account — auto-create using partner details (DC Protocol Apr 2026); partners get 10,000 welcome points
    new_vgk_code = _create_vgk_member_silent(db, partner_name, partner_phone, partner_email,
                                              welcome_pts=10000, source="partner portal")
    if not new_vgk_code:
        raise HTTPException(status_code=500, detail="Could not auto-create VGK4U account. Please contact support.")
    print(f"[DC-PARTNER-VGK] Auto-created VGK account {new_vgk_code} for partner {partner_code}", flush=True)
    tok = _issue_cross_token(db, None, new_vgk_code, "partner_to_vgk")
    return {"success": True, "cross_token": tok, "expires_in": 120, "created": True}


# ═══════════════════════════════════════════════════════════════════════════════
# PROMOTER NDA / TERMS SYSTEM — DC Protocol Apr 2026
# ═══════════════════════════════════════════════════════════════════════════════

_NDA_EDIT_ROLES = {"vgk4u", "ea"}          # Can create / edit / activate NDA
_NDA_VIEW_ROLES = {"vgk4u", "ea", "hr", "key_leadership", "rvz"}  # Can view audit

def _check_nda_edit(user: StaffEmployee):
    code = user.role.role_code if user.role else ""
    if code not in _NDA_EDIT_ROLES:
        raise HTTPException(status_code=403, detail="Only VGK Mentor or EA can manage Promoter NDA versions")

def _check_nda_view(user: StaffEmployee):
    code = user.role.role_code if user.role else ""
    if code not in _NDA_VIEW_ROLES:
        raise HTTPException(status_code=403, detail="Access denied. Insufficient role for NDA audit.")

def _get_promo_by_token(influencer_id: int, promo_token: str, db: Session):
    """Verify promoter session token and return influencer row or raise 401."""
    row = db.execute(text("""
        SELECT pi.id, pi.name, pi.referral_code
        FROM promo_influencers pi
        JOIN promo_influencer_auth pa ON pa.influencer_id = pi.id
        WHERE pi.id = :iid AND pa.session_token = :tok
    """), {"iid": influencer_id, "tok": promo_token}).fetchone()
    if not row:
        raise HTTPException(status_code=401, detail="Invalid or expired promoter session")
    return row

def _get_client_ip_promo(request: Request) -> str:
    xff = request.headers.get("X-Forwarded-For", "")
    return xff.split(",")[0].strip() if xff else request.client.host if request.client else "unknown"


# ── Promoter-facing NDA endpoints ────────────────────────────────────────────

@router.get("/nda/active")
def promo_nda_get_active(
    influencer_id: int = Query(...),
    promo_token: str = Query(...),
    db: Session = Depends(get_db)
):
    """Return active NDA content. No content if no active version."""
    _get_promo_by_token(influencer_id, promo_token, db)
    row = db.execute(text("""
        SELECT id, version_number, title, content_html, activated_at
        FROM promo_nda_versions WHERE status = 'active' LIMIT 1
    """)).fetchone()
    if not row:
        return {"has_active": False}
    return {
        "has_active": True,
        "id": row[0], "version_number": row[1], "title": row[2],
        "content_html": row[3], "activated_at": str(row[4]) if row[4] else None
    }


@router.get("/nda/my-status")
def promo_nda_my_status(
    influencer_id: int = Query(...),
    promo_token: str = Query(...),
    db: Session = Depends(get_db)
):
    """
    Returns whether the promoter must see/accept the NDA.
    Rules:
    - First-time promoters (0 prior acceptances across all versions): need 3 acceptances for current version.
    - Returning promoters (accepted a prior version at least once): need 1 acceptance for current version.
    - No active NDA: must_show = False.
    """
    _get_promo_by_token(influencer_id, promo_token, db)
    active = db.execute(text("""
        SELECT id, version_number, title FROM promo_nda_versions WHERE status='active' LIMIT 1
    """)).fetchone()
    if not active:
        return {"must_show": False, "reason": "no_active_nda"}

    version_id = active[0]
    # Acceptances for current active version
    current_count = db.execute(text("""
        SELECT COUNT(*) FROM promo_nda_acceptances
        WHERE influencer_id = :iid AND nda_version_id = :vid
    """), {"iid": influencer_id, "vid": version_id}).scalar() or 0

    # Total acceptances ever (for any version) — determines first-time vs returning
    total_ever = db.execute(text("""
        SELECT COUNT(*) FROM promo_nda_acceptances WHERE influencer_id = :iid
    """), {"iid": influencer_id}).scalar() or 0

    required = 3 if total_ever == current_count else 1  # first-time: 3; returning on new version: 1

    must_show = current_count < required
    return {
        "must_show": must_show,
        "version_id": version_id,
        "version_number": active[1],
        "nda_title": active[2],
        "current_count": current_count,
        "required": required,
        "reason": "first_time" if (total_ever == current_count and total_ever < 3) else ("new_version" if must_show else "complete")
    }


@router.post("/nda/accept")
def promo_nda_accept(
    request: Request,
    influencer_id: int = Query(...),
    promo_token: str = Query(...),
    db: Session = Depends(get_db)
):
    """Record a promoter's acceptance of the active NDA."""
    inf = _get_promo_by_token(influencer_id, promo_token, db)
    active = db.execute(text("""
        SELECT id FROM promo_nda_versions WHERE status='active' LIMIT 1
    """)).fetchone()
    if not active:
        raise HTTPException(status_code=404, detail="No active NDA version to accept")
    version_id = active[0]
    current_count = db.execute(text("""
        SELECT COUNT(*) FROM promo_nda_acceptances
        WHERE influencer_id = :iid AND nda_version_id = :vid
    """), {"iid": influencer_id, "vid": version_id}).scalar() or 0
    session_number = current_count + 1
    ip = _get_client_ip_promo(request)
    ua = request.headers.get("User-Agent", "")[:500]
    db.execute(text("""
        INSERT INTO promo_nda_acceptances
            (influencer_id, nda_version_id, accepted_at, acceptance_ip, acceptance_user_agent,
             session_number, promoter_name_snapshot, promoter_code_snapshot)
        VALUES (:iid, :vid, NOW(), :ip, :ua, :sn, :name, :code)
    """), {"iid": influencer_id, "vid": version_id, "ip": ip, "ua": ua,
           "sn": session_number, "name": inf[1], "code": inf[2]})
    db.commit()
    return {"success": True, "session_number": session_number, "message": f"Acceptance #{session_number} recorded"}


# ── Staff NDA Management endpoints ───────────────────────────────────────────

@router.get("/staff/promo/nda/versions")
def staff_promo_nda_list_versions(
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    _check_nda_view(current_user)
    rows = db.execute(text("""
        SELECT id, version_number, title, status, notes, created_at, activated_at,
               created_by_staff_id, activated_by_staff_id
        FROM promo_nda_versions ORDER BY created_at DESC
    """)).fetchall()
    return {"versions": [
        {"id": r[0], "version_number": r[1], "title": r[2], "status": r[3],
         "notes": r[4], "created_at": str(r[5]) if r[5] else None,
         "activated_at": str(r[6]) if r[6] else None,
         "created_by_staff_id": r[7], "activated_by_staff_id": r[8]}
        for r in rows
    ]}


@router.get("/staff/promo/nda/summary")
def staff_promo_nda_summary(
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """Per-promoter summary: how many times they've accepted current active NDA."""
    _check_nda_view(current_user)
    active = db.execute(text("SELECT id, version_number FROM promo_nda_versions WHERE status='active' LIMIT 1")).fetchone()
    if not active:
        return {"active_version": None, "promoters": []}
    rows = db.execute(text("""
        SELECT pi.id, pi.name, pi.referral_code, pi.status,
               COUNT(a.id) AS accept_count,
               MAX(a.accepted_at) AS last_accepted
        FROM promo_influencers pi
        LEFT JOIN promo_nda_acceptances a
            ON a.influencer_id = pi.id AND a.nda_version_id = :vid
        GROUP BY pi.id, pi.name, pi.referral_code, pi.status
        ORDER BY pi.name
    """), {"vid": active[0]}).fetchall()
    return {
        "active_version": active[1],
        "promoters": [
            {"id": r[0], "name": r[1], "referral_code": r[2], "status": r[3],
             "accept_count": r[4], "last_accepted": str(r[5]) if r[5] else None}
            for r in rows
        ]
    }


@router.get("/staff/promo/nda/{version_id}")
def staff_promo_nda_get_version(
    version_id: int,
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    _check_nda_view(current_user)
    row = db.execute(text("""
        SELECT id, version_number, title, status, notes, content_html,
               created_at, activated_at, created_by_staff_id, activated_by_staff_id
        FROM promo_nda_versions WHERE id=:id LIMIT 1
    """), {"id": version_id}).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Version not found")
    return {
        "id": row[0], "version_number": row[1], "title": row[2], "status": row[3],
        "notes": row[4], "content_html": row[5],
        "created_at": str(row[6]) if row[6] else None,
        "activated_at": str(row[7]) if row[7] else None,
        "created_by_staff_id": row[8], "activated_by_staff_id": row[9]
    }


@router.post("/staff/promo/nda/draft")
def staff_promo_nda_create_draft(
    body: dict = Body(...),
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    _check_nda_edit(current_user)
    title = (body.get("title") or "").strip()
    content = (body.get("content_html") or "").strip()
    version = (body.get("version_number") or "").strip()
    notes = (body.get("notes") or "").strip()
    if not title or not content or not version:
        raise HTTPException(status_code=400, detail="title, content_html, and version_number are required")
    existing = db.execute(text("SELECT id FROM promo_nda_versions WHERE version_number=:v"), {"v": version}).fetchone()
    if existing:
        raise HTTPException(status_code=409, detail=f"Version {version} already exists")
    row = db.execute(text("""
        INSERT INTO promo_nda_versions (version_number, title, content_html, status, notes, created_by_staff_id, created_at, updated_at)
        VALUES (:v, :t, :c, 'draft', :n, :sid, NOW(), NOW()) RETURNING id
    """), {"v": version, "t": title, "c": content, "n": notes, "sid": current_user.id}).fetchone()
    db.commit()
    return {"success": True, "id": row[0], "version_number": version}


@router.put("/staff/promo/nda/{version_id}")
def staff_promo_nda_update_draft(
    version_id: int,
    body: dict = Body(...),
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    _check_nda_edit(current_user)
    ver = db.execute(text("SELECT id, status FROM promo_nda_versions WHERE id=:id"), {"id": version_id}).fetchone()
    if not ver:
        raise HTTPException(status_code=404, detail="NDA version not found")
    if ver[1] != "draft":
        raise HTTPException(status_code=400, detail="Only draft versions can be edited")
    sets, params = [], {"id": version_id}
    if body.get("title"): sets.append("title=:title"); params["title"] = body["title"].strip()
    if body.get("content_html"): sets.append("content_html=:content"); params["content"] = body["content_html"].strip()
    if body.get("notes") is not None: sets.append("notes=:notes"); params["notes"] = body.get("notes","").strip()
    if not sets:
        raise HTTPException(status_code=400, detail="No fields to update")
    sets.append("updated_at=NOW()")
    db.execute(text(f"UPDATE promo_nda_versions SET {', '.join(sets)} WHERE id=:id"), params)
    db.commit()
    return {"success": True}


@router.post("/staff/promo/nda/{version_id}/activate")
def staff_promo_nda_activate(
    version_id: int,
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    _check_nda_edit(current_user)
    ver = db.execute(text("SELECT id, status, version_number FROM promo_nda_versions WHERE id=:id"), {"id": version_id}).fetchone()
    if not ver:
        raise HTTPException(status_code=404, detail="NDA version not found")
    if ver[1] == "active":
        raise HTTPException(status_code=400, detail="This version is already active")
    # Deactivate any currently active version
    db.execute(text("""
        UPDATE promo_nda_versions SET status='inactive', deactivated_at=NOW()
        WHERE status='active'
    """))
    # Activate this version
    db.execute(text("""
        UPDATE promo_nda_versions SET status='active', activated_at=NOW(), activated_by_staff_id=:sid, updated_at=NOW()
        WHERE id=:id
    """), {"id": version_id, "sid": current_user.id})
    db.commit()
    return {"success": True, "activated_version": ver[2], "message": f"NDA v{ver[2]} is now active. All promoters will be required to re-accept on next login."}


@router.get("/staff/promo/nda/acceptances")
def staff_promo_nda_acceptances(
    version_id: Optional[int] = Query(None),
    influencer_id: Optional[int] = Query(None),
    limit: int = Query(100),
    offset: int = Query(0),
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    _check_nda_view(current_user)
    where = []
    params: dict = {"lim": limit, "off": offset}
    if version_id:
        where.append("a.nda_version_id = :vid"); params["vid"] = version_id
    if influencer_id:
        where.append("a.influencer_id = :iid"); params["iid"] = influencer_id
    clause = "WHERE " + " AND ".join(where) if where else ""
    rows = db.execute(text(f"""
        SELECT a.id, a.influencer_id, a.nda_version_id, a.accepted_at, a.acceptance_ip,
               a.session_number, a.promoter_name_snapshot, a.promoter_code_snapshot,
               v.version_number, v.title
        FROM promo_nda_acceptances a
        JOIN promo_nda_versions v ON v.id = a.nda_version_id
        {clause}
        ORDER BY a.accepted_at DESC
        LIMIT :lim OFFSET :off
    """), params).fetchall()
    total = db.execute(text(f"""
        SELECT COUNT(*) FROM promo_nda_acceptances a {clause}
    """), {k: v for k, v in params.items() if k not in ("lim","off")}).scalar()
    return {
        "total": total, "items": [
            {"id": r[0], "influencer_id": r[1], "nda_version_id": r[2],
             "accepted_at": str(r[3]), "acceptance_ip": r[4], "session_number": r[5],
             "promoter_name": r[6], "promoter_code": r[7],
             "version_number": r[8], "version_title": r[9]}
            for r in rows
        ]
    }


@router.get("/staff/promo/nda/promoter/{inf_id}/history")
def staff_promo_nda_promoter_history(
    inf_id: int,
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    _check_nda_view(current_user)
    rows = db.execute(text("""
        SELECT a.id, a.nda_version_id, a.accepted_at, a.acceptance_ip, a.session_number,
               v.version_number, v.title
        FROM promo_nda_acceptances a
        JOIN promo_nda_versions v ON v.id = a.nda_version_id
        WHERE a.influencer_id = :iid
        ORDER BY a.accepted_at DESC
    """), {"iid": inf_id}).fetchall()
    return {"influencer_id": inf_id, "history": [
        {"id": r[0], "nda_version_id": r[1], "accepted_at": str(r[2]),
         "acceptance_ip": r[3], "session_number": r[4],
         "version_number": r[5], "version_title": r[6]}
        for r in rows
    ]}

