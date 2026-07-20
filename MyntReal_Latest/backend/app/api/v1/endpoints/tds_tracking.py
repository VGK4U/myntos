"""
TDS Tracking API - DC Protocol
Tracks TDS payable to government on behalf of MNR members
Access: All Staff can view, VGK Mentor (MR10001) + Accounts can update status

User-wise view: Aggregates PendingIncome per user showing gross/admin/tds/guru/net
Date-wise detail: Shows date-by-date breakup for a specific user
Reset date: 12 Feb 2026 — only records from this date onwards are shown
TDS User Status: Pending / Completed / Exception (user-level, tracked in tds_user_status)
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, cast, Date, case
from pydantic import BaseModel as PydanticBase
from typing import Optional
from datetime import datetime
import logging

from app.core.database import get_db
from app.core.security import get_current_user_hybrid
from app.models.tds_tracking import TDSTracking, TDSUserStatus
from app.models.transaction import PendingIncome
from app.models.user import User
from app.models.withdrawal import WithdrawalRequest
from app.models.staff import StaffEmployee

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tds-tracking")

RESET_DATE = datetime(2026, 2, 12)

ALLOWED_TDS_UPDATE_ROLES = ['VGK Mentor', 'VGK4U Supreme', 'Accounts', 'Finance Admin', 'Super Admin', 'RVZ ID']


def _resolve_actor_id(current_user) -> str:
    if isinstance(current_user, StaffEmployee):
        return str(current_user.emp_code or current_user.id)
    return str(current_user.id)


def _safe_float(val):
    try:
        return float(val) if val else 0.0
    except (TypeError, ValueError):
        return 0.0


def _has_tds_action_access(staff) -> bool:
    staff_type = getattr(staff, 'staff_type', '') or ''
    emp_code = getattr(staff, 'emp_code', '') or ''
    dept_name = ''
    if hasattr(staff, 'department') and staff.department:
        dept_name = getattr(staff.department, 'name', '') or ''
    return (
        emp_code == 'MR10001' or
        staff_type in ALLOWED_TDS_UPDATE_ROLES or
        dept_name in ['Accounts', 'Finance']
    )


def _build_date_filter(from_date, to_date):
    filters = [PendingIncome.business_date >= RESET_DATE, PendingIncome.verification_status != 'Rejected']
    if from_date:
        try:
            fd = datetime.strptime(from_date, '%Y-%m-%d')
            if fd >= RESET_DATE:
                filters.append(PendingIncome.business_date >= fd)
        except ValueError:
            pass
    if to_date:
        try:
            filters.append(PendingIncome.business_date <= datetime.strptime(to_date, '%Y-%m-%d').replace(hour=23, minute=59, second=59))
        except ValueError:
            pass
    return filters


class TDSStatusUpdate(PydanticBase):
    payment_status: str
    government_reference: Optional[str] = None
    notes: Optional[str] = None


class TDSUserStatusUpdate(PydanticBase):
    status: str
    notes: Optional[str] = None


@router.get("/summary")
async def tds_summary(
    from_date: Optional[str] = Query(None),
    to_date: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_hybrid)
):
    if not isinstance(current_user, StaffEmployee):
        raise HTTPException(status_code=403, detail="Staff access required")

    base_filter = _build_date_filter(from_date, to_date)

    total_users = db.query(func.count(func.distinct(PendingIncome.user_id))).filter(
        *base_filter
    ).scalar() or 0

    agg = db.query(
        func.coalesce(func.sum(PendingIncome.gross_amount), 0),
        func.coalesce(func.sum(PendingIncome.admin_deduction), 0),
        func.coalesce(func.sum(PendingIncome.tds_deduction), 0),
        func.coalesce(func.sum(PendingIncome.gurudakshina_deduction), 0),
        func.coalesce(func.sum(PendingIncome.net_amount), 0),
    ).filter(
        *base_filter
    ).first()

    total_gross = _safe_float(agg[0])
    total_admin = _safe_float(agg[1])
    total_tds = _safe_float(agg[2])
    total_guru = _safe_float(agg[3])
    total_net = _safe_float(agg[4])

    active_user_ids_q = db.query(func.distinct(PendingIncome.user_id)).filter(
        *base_filter
    ).subquery()
    active_user_select = db.query(active_user_ids_q.c[0])

    status_counts = db.query(
        TDSUserStatus.status,
        func.count(TDSUserStatus.id)
    ).filter(
        TDSUserStatus.user_id.in_(active_user_select)
    ).group_by(TDSUserStatus.status).all()
    status_map = {s: c for s, c in status_counts}

    tds_completed = status_map.get('Completed', 0)
    tds_exception = status_map.get('Exception', 0)
    tds_pending = total_users - tds_completed - tds_exception
    if tds_pending < 0:
        tds_pending = 0

    tds_by_status = db.query(
        TDSUserStatus.status,
        func.coalesce(func.sum(PendingIncome.tds_deduction), 0)
    ).join(
        PendingIncome, PendingIncome.user_id == TDSUserStatus.user_id
    ).filter(
        *base_filter,
        TDSUserStatus.user_id.in_(active_user_select)
    ).group_by(TDSUserStatus.status).all()
    tds_amt_map = {s: _safe_float(a) for s, a in tds_by_status}

    tds_amt_completed = tds_amt_map.get('Completed', 0)
    tds_amt_exception = tds_amt_map.get('Exception', 0)
    tds_amt_pending = total_tds - tds_amt_completed - tds_amt_exception
    if tds_amt_pending < 0:
        tds_amt_pending = 0

    return {
        "success": True,
        "summary": {
            "total_users": total_users,
            "total_gross": total_gross,
            "total_admin": total_admin,
            "total_tds": total_tds,
            "total_guru": total_guru,
            "total_net": total_net,
            "tds_completed": tds_completed,
            "tds_exception": tds_exception,
            "tds_pending": tds_pending,
            "tds_amt_completed": tds_amt_completed,
            "tds_amt_exception": tds_amt_exception,
            "tds_amt_pending": tds_amt_pending
        }
    }


@router.get("/user-summary")
async def tds_user_summary(
    search: Optional[str] = Query(None),
    from_date: Optional[str] = Query(None),
    to_date: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_hybrid)
):
    if not isinstance(current_user, StaffEmployee):
        raise HTTPException(status_code=403, detail="Staff access required")

    base_filter = _build_date_filter(from_date, to_date)

    query = db.query(
        PendingIncome.user_id,
        func.coalesce(func.sum(PendingIncome.gross_amount), 0).label('total_gross'),
        func.coalesce(func.sum(PendingIncome.admin_deduction), 0).label('total_admin'),
        func.coalesce(func.sum(PendingIncome.tds_deduction), 0).label('total_tds'),
        func.coalesce(func.sum(PendingIncome.gurudakshina_deduction), 0).label('total_guru'),
        func.coalesce(func.sum(PendingIncome.net_amount), 0).label('total_net'),
        func.count(PendingIncome.id).label('record_count'),
    ).filter(
        *base_filter
    ).group_by(PendingIncome.user_id)

    if search:
        search_term = f"%{search}%"
        matching_user_ids = db.query(User.id).filter(
            (User.id.ilike(search_term)) |
            (User.name.ilike(search_term))
        ).all()
        matching_ids = [uid[0] for uid in matching_user_ids]
        if matching_ids:
            query = query.filter(PendingIncome.user_id.in_(matching_ids))
        else:
            return {
                "success": True,
                "users": [],
                "total": 0,
                "page": page,
                "per_page": per_page,
                "total_pages": 0
            }

    if status_filter and status_filter != 'All':
        status_user_ids = db.query(TDSUserStatus.user_id).filter(
            TDSUserStatus.status == status_filter
        ).subquery()
        if status_filter == 'Pending':
            completed_exception_ids = db.query(TDSUserStatus.user_id).filter(
                TDSUserStatus.status.in_(['Completed', 'Exception'])
            ).subquery()
            query = query.filter(~PendingIncome.user_id.in_(completed_exception_ids))
        else:
            query = query.filter(PendingIncome.user_id.in_(status_user_ids))

    count_query = query.subquery()
    total = db.query(func.count()).select_from(count_query).scalar() or 0

    results = query.order_by(desc('total_gross')).offset(
        (page - 1) * per_page
    ).limit(per_page).all()

    user_ids = [r[0] for r in results]
    users_map = {}
    status_map = {}
    if user_ids:
        users = db.query(User.id, User.name).filter(User.id.in_(user_ids)).all()
        users_map = {u.id: u.name for u in users}

        statuses = db.query(TDSUserStatus.user_id, TDSUserStatus.status).filter(
            TDSUserStatus.user_id.in_(user_ids)
        ).all()
        status_map = {s.user_id: s.status for s in statuses}

    records = []
    for r in results:
        user_id = r[0]
        user_status = status_map.get(user_id, 'Pending')

        records.append({
            "user_id": user_id,
            "user_name": users_map.get(user_id, "-"),
            "total_gross": _safe_float(r[1]),
            "total_admin": _safe_float(r[2]),
            "total_tds": _safe_float(r[3]),
            "total_guru": _safe_float(r[4]),
            "total_net": _safe_float(r[5]),
            "record_count": r[6],
            "tds_status": user_status,
        })

    return {
        "success": True,
        "users": records,
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": (total + per_page - 1) // per_page if total > 0 else 0
    }


@router.get("/user-detail/{user_id}")
async def tds_user_detail(
    user_id: str,
    from_date: Optional[str] = Query(None),
    to_date: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_hybrid)
):
    if not isinstance(current_user, StaffEmployee):
        raise HTTPException(status_code=403, detail="Staff access required")

    user = db.query(User.id, User.name).filter(User.id == user_id).first()
    user_name = user.name if user else "-"

    base_filter = [PendingIncome.user_id == user_id] + _build_date_filter(from_date, to_date)

    date_wise = db.query(
        cast(PendingIncome.business_date, Date).label('biz_date'),
        func.coalesce(func.sum(PendingIncome.gross_amount), 0),
        func.coalesce(func.sum(PendingIncome.admin_deduction), 0),
        func.coalesce(func.sum(PendingIncome.tds_deduction), 0),
        func.coalesce(func.sum(PendingIncome.gurudakshina_deduction), 0),
        func.coalesce(func.sum(PendingIncome.net_amount), 0),
        func.count(PendingIncome.id),
    ).filter(
        *base_filter
    ).group_by('biz_date').order_by(desc('biz_date')).all()

    records = []
    for row in date_wise:
        records.append({
            "date": row[0].strftime('%Y-%m-%d') if row[0] else "-",
            "gross": _safe_float(row[1]),
            "admin": _safe_float(row[2]),
            "tds": _safe_float(row[3]),
            "guru": _safe_float(row[4]),
            "net": _safe_float(row[5]),
            "txn_count": row[6],
        })

    totals = db.query(
        func.coalesce(func.sum(PendingIncome.gross_amount), 0),
        func.coalesce(func.sum(PendingIncome.admin_deduction), 0),
        func.coalesce(func.sum(PendingIncome.tds_deduction), 0),
        func.coalesce(func.sum(PendingIncome.gurudakshina_deduction), 0),
        func.coalesce(func.sum(PendingIncome.net_amount), 0),
    ).filter(
        *base_filter
    ).first()

    user_status_rec = db.query(TDSUserStatus).filter(TDSUserStatus.user_id == user_id).first()
    tds_status = user_status_rec.status if user_status_rec else 'Pending'
    tds_notes = user_status_rec.notes if user_status_rec else None
    tds_marked_by = user_status_rec.marked_by if user_status_rec else None
    tds_marked_at = user_status_rec.marked_at.isoformat() if user_status_rec and user_status_rec.marked_at else None

    can_action = _has_tds_action_access(current_user)

    return {
        "success": True,
        "user_id": user_id,
        "user_name": user_name,
        "records": records,
        "totals": {
            "gross": _safe_float(totals[0]),
            "admin": _safe_float(totals[1]),
            "tds": _safe_float(totals[2]),
            "guru": _safe_float(totals[3]),
            "net": _safe_float(totals[4]),
        },
        "tds_status": tds_status,
        "tds_notes": tds_notes,
        "tds_marked_by": tds_marked_by,
        "tds_marked_at": tds_marked_at,
        "can_action": can_action
    }


@router.put("/mark-status/{user_id}")
async def mark_tds_user_status(
    user_id: str,
    data: TDSUserStatusUpdate = Body(...),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_hybrid)
):
    if not isinstance(current_user, StaffEmployee):
        raise HTTPException(status_code=403, detail="Staff access required")

    # DC Protocol: Menu-based access control - page assignment = full access
    # if not _has_tds_action_access(current_user):
    #     raise HTTPException(
    #         status_code=403,
    #         detail="Only MR10001 (VGK4U Supreme) or Accounts department can update TDS status"
    #     )

    if data.status not in ['Pending', 'Completed', 'Exception']:
        raise HTTPException(status_code=400, detail="Status must be 'Pending', 'Completed', or 'Exception'")

    user = db.query(User.id).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    from app.models.base import get_indian_time

    existing = db.query(TDSUserStatus).filter(TDSUserStatus.user_id == user_id).first()
    actor_id = _resolve_actor_id(current_user)

    if existing:
        existing.status = data.status
        existing.marked_by = actor_id
        existing.marked_at = get_indian_time()
        existing.notes = data.notes or existing.notes
    else:
        new_status = TDSUserStatus(
            user_id=user_id,
            status=data.status,
            marked_by=actor_id,
            marked_at=get_indian_time(),
            notes=data.notes
        )
        db.add(new_status)

    db.commit()

    return {
        "success": True,
        "message": f"TDS status for {user_id} marked as {data.status}",
        "user_id": user_id,
        "status": data.status
    }


@router.get("/list")
async def tds_list(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    status_filter: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_hybrid)
):
    if not isinstance(current_user, StaffEmployee):
        raise HTTPException(status_code=403, detail="Staff access required")

    query = db.query(TDSTracking, User).outerjoin(
        User, TDSTracking.user_id == User.id
    )

    if status_filter and status_filter != 'All':
        query = query.filter(TDSTracking.payment_status == status_filter)

    if search:
        search_term = f"%{search}%"
        query = query.filter(
            (User.name.ilike(search_term)) |
            (TDSTracking.mnr_id.ilike(search_term))
        )

    if date_from:
        try:
            df = datetime.strptime(date_from, '%Y-%m-%d')
            query = query.filter(TDSTracking.created_at >= df)
        except ValueError:
            pass

    if date_to:
        try:
            dt = datetime.strptime(date_to, '%Y-%m-%d')
            dt = dt.replace(hour=23, minute=59, second=59)
            query = query.filter(TDSTracking.created_at <= dt)
        except ValueError:
            pass

    total = query.count()
    results = query.order_by(desc(TDSTracking.created_at)).offset(
        (page - 1) * per_page
    ).limit(per_page).all()

    records = []
    for tds, user in results:
        records.append({
            "id": tds.id,
            "withdrawal_request_id": tds.withdrawal_request_id,
            "user_id": tds.user_id,
            "user_name": user.name if user else "-",
            "mnr_id": tds.mnr_id or "-",
            "tds_amount": float(tds.tds_amount),
            "withdrawal_amount": float(tds.withdrawal_amount),
            "payment_status": tds.payment_status,
            "paid_at": tds.paid_at.isoformat() if tds.paid_at else None,
            "paid_by": tds.paid_by,
            "government_reference": tds.government_reference,
            "notes": tds.notes,
            "created_at": tds.created_at.isoformat() if tds.created_at else None
        })

    return {
        "success": True,
        "records": records,
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": (total + per_page - 1) // per_page
    }


@router.put("/{tds_id}/update-status")
async def update_tds_status(
    tds_id: int,
    data: TDSStatusUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_hybrid)
):
    if not isinstance(current_user, StaffEmployee):
        raise HTTPException(status_code=403, detail="Staff access required")

    # DC Protocol: Menu-based access control - page assignment = full access
    # if not _has_tds_action_access(current_user):
    #     raise HTTPException(
    #         status_code=403,
    #         detail="Only VGK Supreme, Accounts, or Finance staff can update TDS status"
    #     )

    if data.payment_status not in ['Pending', 'Paid']:
        raise HTTPException(status_code=400, detail="Status must be 'Pending' or 'Paid'")

    tds = db.query(TDSTracking).filter(TDSTracking.id == tds_id).first()
    if not tds:
        raise HTTPException(status_code=404, detail="TDS record not found")

    tds.payment_status = data.payment_status
    if data.government_reference:
        tds.government_reference = data.government_reference
    if data.notes:
        tds.notes = data.notes
    if data.payment_status == 'Paid':
        from app.models.base import get_indian_time
        tds.paid_at = get_indian_time()
        tds.paid_by = _resolve_actor_id(current_user)
    elif data.payment_status == 'Pending':
        tds.paid_at = None
        tds.paid_by = None

    db.commit()
    db.refresh(tds)

    return {
        "success": True,
        "message": f"TDS record #{tds_id} marked as {data.payment_status}",
        "record": {
            "id": tds.id,
            "payment_status": tds.payment_status,
            "paid_at": tds.paid_at.isoformat() if tds.paid_at else None,
            "paid_by": tds.paid_by,
            "government_reference": tds.government_reference
        }
    }
