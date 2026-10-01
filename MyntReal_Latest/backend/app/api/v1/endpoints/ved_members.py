"""
VED Member (Tenant Referral Partner) Endpoints
DC Protocol (Sep 2026):
- Strictly scoped to active tenant company_id
- Dual Commission Structure (% vs ₹)
- Executive Dashboard with 7 Time Filters (Today, Yesterday, This Week, Last Week, This Month, Indian FY, Overall)
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Path, Body, status
from sqlalchemy.orm import Session
from sqlalchemy import text, or_, and_, func
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta, timezone, date
from decimal import Decimal
import logging

from app.core.database import get_db
from app.models.staff import StaffEmployee
from app.models.staff_accounts import OfficialPartner, AssociatedCompany
from app.models.crm import CRMLead
from app.core.security import get_current_user
from app.utils.phone_otp import normalize_phone_10
from app.utils.name_formatter import format_proper_name

logger = logging.getLogger(__name__)

router = APIRouter()

IST = timezone(timedelta(hours=5, minutes=30))


def _get_company_id(current_user: StaffEmployee) -> int:
    company_id = getattr(current_user, 'base_company_id', None) or getattr(current_user, 'company_id', None)
    if not company_id:
        raise HTTPException(status_code=400, detail="Tenant context missing for user.")
    return company_id


def _get_time_range(time_filter: str) -> tuple[Optional[datetime], Optional[datetime]]:
    now_ist = datetime.now(IST)
    today_start = datetime(now_ist.year, now_ist.month, now_ist.day, 0, 0, 0)
    today_end = datetime(now_ist.year, now_ist.month, now_ist.day, 23, 59, 59)

    tf = (time_filter or 'overall').lower().strip()

    if tf == 'today':
        return today_start, today_end
    elif tf == 'yesterday':
        yest = today_start - timedelta(days=1)
        yest_end = datetime(yest.year, yest.month, yest.day, 23, 59, 59)
        return yest, yest_end
    elif tf == 'this_week':
        # Start of week (Monday)
        start_week = today_start - timedelta(days=today_start.weekday())
        return start_week, today_end
    elif tf == 'last_week':
        start_this_week = today_start - timedelta(days=today_start.weekday())
        start_last_week = start_this_week - timedelta(days=7)
        end_last_week = start_this_week - timedelta(seconds=1)
        return start_last_week, end_last_week
    elif tf == 'this_month':
        start_month = datetime(now_ist.year, now_ist.month, 1, 0, 0, 0)
        return start_month, today_end
    elif tf == 'this_fy':
        # Indian Financial Year: April 1 to March 31
        if now_ist.month >= 4:
            fy_start_year = now_ist.year
        else:
            fy_start_year = now_ist.year - 1
        fy_start = datetime(fy_start_year, 4, 1, 0, 0, 0)
        return fy_start, today_end
    else:  # 'overall'
        return None, None


def _next_ved_member_code(db: Session) -> str:
    """Generate sequential VED Member / Freelancer code FL08180001, FL08180002..."""
    prefix = "FL0818"
    latest = db.query(OfficialPartner.partner_code).filter(
        OfficialPartner.partner_code.like(f"{prefix}%")
    ).order_by(OfficialPartner.partner_code.desc()).first()

    if latest and latest[0] and len(latest[0]) >= 10 and latest[0][len(prefix):].isdigit():
        num = int(latest[0][len(prefix):]) + 1
    else:
        num = 1

    return f"{prefix}{num:04d}"


@router.get("/ved-members")
def list_ved_members(
    search: Optional[str] = Query(None),
    status_filter: Optional[str] = Query("all"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: StaffEmployee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List VED Members for active tenant (company_id).
    STRICT INVARIANT: Filters strictly by current_user.company_id to isolate tenant data.
    """
    company_id = _get_company_id(current_user)

    query = db.query(OfficialPartner).filter(
        OfficialPartner.company_id == company_id,
        OfficialPartner.partner_type == 'FREELANCER'
    )

    if status_filter == 'active':
        query = query.filter(OfficialPartner.is_active == True)
    elif status_filter == 'inactive':
        query = query.filter(OfficialPartner.is_active == False)

    if search:
        s = f"%{search.strip()}%"
        query = query.filter(
            or_(
                OfficialPartner.partner_code.ilike(s),
                OfficialPartner.partner_name.ilike(s),
                OfficialPartner.phone.ilike(s),
                OfficialPartner.email.ilike(s),
                OfficialPartner.city.ilike(s)
            )
        )

    total_count = query.count()
    members = query.order_by(OfficialPartner.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

    items = []
    for m in members:
        # Leads count for this member
        lead_stats = db.query(
            func.count(CRMLead.id).label('lead_count'),
            func.coalesce(func.sum(CRMLead.deal_value_total), 0).label('revenue')
        ).filter(
            CRMLead.company_id == company_id,
            or_(
                and_(CRMLead.source_ref_type.in_(['ved_member', 'freelancer']), CRMLead.source_ref_id == str(m.id)),
                CRMLead.associated_partner_id == m.id
            )
        ).first()

        lead_count = lead_stats.lead_count if lead_stats else 0
        revenue = float(lead_stats.revenue) if lead_stats else 0.0

        comm_type = getattr(m, 'commission_type', 'PERCENTAGE') or 'PERCENTAGE'
        comm_val = float(getattr(m, 'commission_value', 0.0) or 0.0)

        items.append({
            "id": m.id,
            "partner_code": m.partner_code,
            "partner_name": m.partner_name,
            "phone": m.phone,
            "alternate_phone": m.alternate_phone,
            "email": m.email,
            "area": m.area,
            "city": m.city,
            "district": m.district,
            "state": m.state,
            "address": m.address,
            "pincode": m.pincode,
            "commission_type": comm_type,
            "commission_value": comm_val,
            "is_active": m.is_active,
            "freelancer_classification": m.freelancer_classification,
            "created_at": m.created_at.isoformat() if m.created_at else None,
            "total_leads_referred": lead_count,
            "total_revenue_generated": revenue
        })

    return {
        "success": True,
        "total": total_count,
        "page": page,
        "page_size": page_size,
        "data": items
    }


@router.post("/ved-members", status_code=201)
def create_ved_member(
    payload: Dict[str, Any] = Body(...),
    current_user: StaffEmployee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create VED Member for active tenant.
    Auto-populates company_id to enforce tenant data isolation.
    """
    company_id = _get_company_id(current_user)

    name = (payload.get('partner_name') or '').strip()
    if not name or len(name) < 2:
        raise HTTPException(status_code=400, detail="Partner name must be at least 2 characters.")

    raw_phone = (payload.get('phone') or '').strip()
    phone = normalize_phone_10(raw_phone) or raw_phone
    if not phone or len(phone) < 10:
        raise HTTPException(status_code=400, detail="Valid 10-digit phone number is required.")

    # Phone uniqueness check within company
    existing = db.query(OfficialPartner).filter(
        OfficialPartner.company_id == company_id,
        or_(OfficialPartner.phone == phone, OfficialPartner.phone == raw_phone)
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Phone number already registered with VED Member {existing.partner_code} ({existing.partner_name}).")

    code = _next_ved_member_code(db)
    comm_type = (payload.get('commission_type') or 'PERCENTAGE').strip().upper()
    if comm_type not in ('PERCENTAGE', 'FLAT_VALUE'):
        comm_type = 'PERCENTAGE'
    
    try:
        comm_val = float(payload.get('commission_value') or 0.0)
    except (ValueError, TypeError):
        comm_val = 0.0

    member = OfficialPartner(
        company_id=company_id,
        partner_code=code,
        partner_name=format_proper_name(name),
        phone=phone,
        alternate_phone=(payload.get('alternate_phone') or '').strip() or None,
        email=(payload.get('email') or '').strip() or None,
        category='VGK_TEAM',
        partner_type='FREELANCER',
        freelancer_classification=(payload.get('freelancer_classification') or 'WITH_COMMUNICATION').strip().upper(),
        area=(payload.get('area') or '').strip() or None,
        city=(payload.get('city') or '').strip() or None,
        district=(payload.get('district') or '').strip() or None,
        state=(payload.get('state') or '').strip() or None,
        address=(payload.get('address') or '').strip() or None,
        pincode=(payload.get('pincode') or '').strip() or None,
        commission_type=comm_type,
        commission_value=Decimal(str(comm_val)),
        is_active=True,
        created_by_id=current_user.id,
        created_at=datetime.now(IST)
    )

    db.add(member)
    db.commit()
    db.refresh(member)

    return {
        "success": True,
        "message": f"VED Member {member.partner_code} created successfully",
        "data": {
            "id": member.id,
            "partner_code": member.partner_code,
            "partner_name": member.partner_name,
            "phone": member.phone,
            "alternate_phone": member.alternate_phone,
            "email": member.email,
            "commission_type": member.commission_type,
            "commission_value": float(member.commission_value),
            "is_active": member.is_active,
            "created_at": member.created_at.isoformat() if member.created_at else None
        }
    }


@router.patch("/ved-members/{member_id}")
def update_ved_member(
    member_id: int = Path(...),
    payload: Dict[str, Any] = Body(...),
    current_user: StaffEmployee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update VED Member profile & commission structure (% vs ₹).
    """
    company_id = _get_company_id(current_user)

    member = db.query(OfficialPartner).filter(
        OfficialPartner.id == member_id,
        OfficialPartner.company_id == company_id,
        OfficialPartner.partner_type == 'FREELANCER'
    ).first()

    if not member:
        raise HTTPException(status_code=404, detail="VED Member not found or access denied.")

    if 'partner_name' in payload and payload['partner_name']:
        member.partner_name = format_proper_name(payload['partner_name'].strip())

    if 'phone' in payload and payload['phone']:
        raw = payload['phone'].strip()
        ph = normalize_phone_10(raw) or raw
        member.phone = ph

    if 'alternate_phone' in payload:
        raw_alt = (payload['alternate_phone'] or '').strip()
        member.alternate_phone = normalize_phone_10(raw_alt) or raw_alt if raw_alt else None

    if 'email' in payload:
        member.email = (payload['email'] or '').strip() or None

    for field in ('area', 'city', 'district', 'state', 'address', 'pincode'):
        if field in payload:
            setattr(member, field, (payload[field] or '').strip() or None)

    if 'commission_type' in payload and payload['commission_type']:
        ct = payload['commission_type'].strip().upper()
        if ct in ('PERCENTAGE', 'FLAT_VALUE'):
            member.commission_type = ct

    if 'commission_value' in payload and payload['commission_value'] is not None:
        try:
            member.commission_value = Decimal(str(payload['commission_value']))
        except Exception:
            pass

    if 'is_active' in payload and payload['is_active'] is not None:
        member.is_active = bool(payload['is_active'])

    db.commit()
    db.refresh(member)

    return {
        "success": True,
        "message": f"VED Member {member.partner_code} updated successfully",
        "data": {
            "id": member.id,
            "partner_code": member.partner_code,
            "partner_name": member.partner_name,
            "phone": member.phone,
            "commission_type": member.commission_type,
            "commission_value": float(member.commission_value),
            "is_active": member.is_active
        }
    }


@router.get("/ved-members/dashboard")
def veda_member_executive_dashboard(
    time_filter: str = Query("overall", description="today, yesterday, this_week, last_week, this_month, this_fy, overall"),
    current_user: StaffEmployee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Executive Summary Dashboard for VED Members.
    Calculates referred leads, revenue, and top performers filtered by Indian Financial Year & time filters.
    """
    company_id = _get_company_id(current_user)
    start_dt, end_dt = _get_time_range(time_filter)

    # 1. Total active VED members
    total_ved_members = db.query(func.count(OfficialPartner.id)).filter(
        OfficialPartner.company_id == company_id,
        OfficialPartner.partner_type == 'FREELANCER',
        OfficialPartner.is_active == True
    ).scalar() or 0

    # 2. Base Lead Query for tenant
    lead_query = db.query(CRMLead).filter(
        CRMLead.company_id == company_id,
        or_(
            CRMLead.source_ref_type.in_(['ved_member', 'freelancer']),
            CRMLead.associated_partner_id.isnot(None)
        )
    )

    if start_dt:
        lead_query = lead_query.filter(CRMLead.created_at >= start_dt)
    if end_dt:
        lead_query = lead_query.filter(CRMLead.created_at <= end_dt)

    total_leads_referred = lead_query.count()

    total_revenue = db.query(func.coalesce(func.sum(CRMLead.deal_value_total), 0)).filter(
        CRMLead.company_id == company_id,
        or_(
            CRMLead.source_ref_type.in_(['ved_member', 'freelancer']),
            CRMLead.associated_partner_id.isnot(None)
        ),
        *( [CRMLead.created_at >= start_dt] if start_dt else [] ),
        *( [CRMLead.created_at <= end_dt] if end_dt else [] )
    ).scalar() or 0.0

    # 3. Top Performers Ranking
    all_members = db.query(OfficialPartner).filter(
        OfficialPartner.company_id == company_id,
        OfficialPartner.partner_type == 'FREELANCER'
    ).all()

    leaderboard = []
    for m in all_members:
        m_lead_q = db.query(
            func.count(CRMLead.id).label('l_cnt'),
            func.coalesce(func.sum(CRMLead.deal_value_total), 0).label('revenue')
        ).filter(
            CRMLead.company_id == company_id,
            or_(
                and_(CRMLead.source_ref_type.in_(['ved_member', 'freelancer']), CRMLead.source_ref_id == str(m.id)),
                CRMLead.associated_partner_id == m.id
            )
        )

        if start_dt:
            m_lead_q = m_lead_q.filter(CRMLead.created_at >= start_dt)
        if end_dt:
            m_lead_q = m_lead_q.filter(CRMLead.created_at <= end_dt)

        res = m_lead_q.first()
        l_cnt = res.l_cnt if res else 0
        rev = float(res.revenue) if res else 0.0

        comm_type = getattr(m, 'commission_type', 'PERCENTAGE') or 'PERCENTAGE'
        comm_val = float(getattr(m, 'commission_value', 0.0) or 0.0)

        if comm_type == 'FLAT_VALUE':
            est_comm = l_cnt * comm_val
        else:
            est_comm = round(rev * (comm_val / 100.0), 2)

        if l_cnt > 0 or rev > 0:
            leaderboard.append({
                "partner_id": m.id,
                "partner_code": m.partner_code,
                "partner_name": m.partner_name,
                "phone": m.phone,
                "city": m.city,
                "commission_type": comm_type,
                "commission_value": comm_val,
                "leads_referred": l_cnt,
                "revenue_generated": rev,
                "estimated_commission": est_comm
            })

    # Sort leaderboard by revenue generated desc, then leads_referred desc
    leaderboard.sort(key=lambda x: (x['revenue_generated'], x['leads_referred']), reverse=True)

    return {
        "success": True,
        "time_filter": time_filter,
        "period": {
            "start": start_dt.isoformat() if start_dt else None,
            "end": end_dt.isoformat() if end_dt else None
        },
        "metrics": {
            "total_ved_members": total_ved_members,
            "total_leads_referred": total_leads_referred,
            "total_revenue_generated": float(total_revenue),
        },
        "top_performers": leaderboard[:10]
    }
