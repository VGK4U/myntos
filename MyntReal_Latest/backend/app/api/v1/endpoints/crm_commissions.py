"""
DC Protocol Apr 2026: CRM Commission Endpoints — MNR / Partner referral chain.

Endpoints:
  GET /api/v1/mnr/my-commissions       — MNR member views own entries (JWT-gated)
  GET /api/v1/partner/commissions      — Partner views own entries (partner auth)
  GET /api/v1/staff/crm/commissions    — Staff view all entries (staff auth)
  PATCH /api/v1/staff/crm/commissions/{entry_id}/status — Staff update status
"""

import logging
from typing import Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session
from sqlalchemy import text, desc

from app.core.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter()


# ── helpers ──────────────────────────────────────────────────────────────────

def _safe_float(val):
    if val is None:
        return 0.0
    try:
        return float(val)
    except Exception:
        return 0.0


def _paginated_query(
    db: Session,
    referrer_id: Optional[str],
    referrer_type: Optional[str],
    status: Optional[str],
    level: Optional[str],
    company_id: Optional[int],
    page: int,
    per_page: int,
):
    filters = ["1=1"]
    params: dict = {}

    if referrer_id is not None:
        filters.append("ce.referrer_id = :rid")
        params["rid"] = referrer_id

    if referrer_type is not None:
        filters.append("ce.referrer_type = :rtype")
        params["rtype"] = referrer_type

    if status is not None:
        filters.append("ce.status = :status")
        params["status"] = status

    if level is not None:
        filters.append("ce.level = :level")
        params["level"] = level

    if company_id is not None:
        filters.append("ce.company_id = :cid")
        params["cid"] = company_id

    where = " AND ".join(filters)
    count_sql = f"SELECT COUNT(*) FROM crm_commission_entries ce WHERE {where}"
    total = db.execute(text(count_sql), params).scalar() or 0

    offset = (page - 1) * per_page
    params["limit"] = per_page
    params["offset"] = offset

    rows = db.execute(
        text(
            f"""
            SELECT ce.id, ce.entry_number, ce.company_id,
                   ce.referrer_type, ce.referrer_id, ce.referrer_name,
                   ce.level,
                   ce.source_lead_id, ce.source_transaction_id,
                   ce.category_id, ce.category_name,
                   ce.revenue_amount, ce.commission_pct, ce.commission_amount,
                   ce.status, ce.notes,
                   ce.confirmed_at, ce.confirmed_by_id,
                   ce.created_at, ce.updated_at,
                   cl.name AS lead_customer_name,
                   cl.phone AS lead_phone
            FROM crm_commission_entries ce
            LEFT JOIN crm_leads cl ON cl.id = ce.source_lead_id
            WHERE {where}
            ORDER BY ce.created_at DESC
            LIMIT :limit OFFSET :offset
            """
        ),
        params,
    ).fetchall()

    entries = []
    for r in rows:
        entries.append(
            {
                "id": r.id,
                "entry_number": r.entry_number,
                "company_id": r.company_id,
                "referrer_type": r.referrer_type,
                "referrer_id": r.referrer_id,
                "referrer_name": r.referrer_name,
                "level": r.level,
                "source_lead_id": r.source_lead_id,
                "source_transaction_id": r.source_transaction_id,
                "category_id": r.category_id,
                "category_name": r.category_name,
                "revenue_amount": _safe_float(r.revenue_amount),
                "commission_pct": _safe_float(r.commission_pct),
                "commission_amount": _safe_float(r.commission_amount),
                "status": r.status,
                "notes": r.notes,
                "confirmed_at": r.confirmed_at.isoformat() if r.confirmed_at else None,
                "confirmed_by_id": r.confirmed_by_id,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "updated_at": r.updated_at.isoformat() if r.updated_at else None,
                "lead_customer_name": r.lead_customer_name,
                "lead_phone": r.lead_phone,
            }
        )

    return {
        "entries": entries,
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": (total + per_page - 1) // per_page if per_page > 0 else 1,
    }


# ── MNR member: own commissions ───────────────────────────────────────────────

@router.get("/mnr/my-commissions", tags=["CRM Commissions"])
async def mnr_my_commissions(
    request: Request,
    status: Optional[str] = Query(None),
    level: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    from app.core.security import get_current_mnr_user_from_hybrid
    current_user = await get_current_mnr_user_from_hybrid(request, db)
    mnr_id = getattr(current_user, 'id', None) or getattr(current_user, 'mnr_id', None)
    if not mnr_id:
        raise HTTPException(status_code=401, detail="MNR identity could not be resolved")

    result = _paginated_query(
        db=db,
        referrer_id=str(mnr_id),
        referrer_type='mnr',
        status=status,
        level=level,
        company_id=None,
        page=page,
        per_page=per_page,
    )

    # Summary totals for this member
    summary = db.execute(
        text(
            """
            SELECT
                SUM(commission_amount) FILTER (WHERE status != 'CANCELLED') AS total_gross,
                SUM(commission_amount) FILTER (WHERE status = 'CONFIRMED') AS total_confirmed,
                SUM(commission_amount) FILTER (WHERE status = 'PENDING') AS total_pending,
                COUNT(*) FILTER (WHERE status = 'PENDING') AS pending_count
            FROM crm_commission_entries
            WHERE referrer_id = :rid AND referrer_type = 'mnr'
            """
        ),
        {"rid": str(mnr_id)},
    ).fetchone()

    result["summary"] = {
        "total_gross": _safe_float(summary.total_gross if summary else 0),
        "total_confirmed": _safe_float(summary.total_confirmed if summary else 0),
        "total_pending": _safe_float(summary.total_pending if summary else 0),
        "pending_count": int(summary.pending_count or 0) if summary else 0,
    }
    return result


# ── Partner: own commissions ──────────────────────────────────────────────────

@router.get("/partner/commissions", tags=["CRM Commissions"])
async def partner_commissions(
    request: Request,
    status: Optional[str] = Query(None),
    level: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    from app.core.security import get_current_user_hybrid_with_partner
    current_user = await get_current_user_hybrid_with_partner(request, db)

    partner_ref_id = None
    from app.models.staff_accounts import OfficialPartner
    if isinstance(current_user, OfficialPartner):
        partner_ref_id = getattr(current_user, 'partner_code', None) or str(current_user.id)
    else:
        raise HTTPException(status_code=403, detail="Partner access only")

    result = _paginated_query(
        db=db,
        referrer_id=str(partner_ref_id),
        referrer_type='partner',
        status=status,
        level=level,
        company_id=None,
        page=page,
        per_page=per_page,
    )

    summary = db.execute(
        text(
            """
            SELECT
                SUM(commission_amount) FILTER (WHERE status != 'CANCELLED') AS total_gross,
                SUM(commission_amount) FILTER (WHERE status = 'CONFIRMED') AS total_confirmed,
                SUM(commission_amount) FILTER (WHERE status = 'PENDING') AS total_pending,
                COUNT(*) FILTER (WHERE status = 'PENDING') AS pending_count
            FROM crm_commission_entries
            WHERE referrer_id = :rid AND referrer_type = 'partner'
            """
        ),
        {"rid": str(partner_ref_id)},
    ).fetchone()

    result["summary"] = {
        "total_gross": _safe_float(summary.total_gross if summary else 0),
        "total_confirmed": _safe_float(summary.total_confirmed if summary else 0),
        "total_pending": _safe_float(summary.total_pending if summary else 0),
        "pending_count": int(summary.pending_count or 0) if summary else 0,
    }
    return result


# ── Staff: all commissions ─────────────────────────────────────────────────────

@router.get("/staff/crm/commissions", tags=["CRM Commissions"])
async def staff_crm_commissions(
    request: Request,
    referrer_id: Optional[str] = Query(None),
    referrer_type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    level: Optional[str] = Query(None),
    company_id: Optional[int] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    from app.core.security import get_current_user_hybrid
    current_user = await get_current_user_hybrid(request, db)
    from app.models.staff import StaffEmployee
    if not isinstance(current_user, StaffEmployee):
        raise HTTPException(status_code=403, detail="Staff access only")

    return _paginated_query(
        db=db,
        referrer_id=referrer_id,
        referrer_type=referrer_type,
        status=status,
        level=level,
        company_id=company_id,
        page=page,
        per_page=per_page,
    )


# ── Staff: update commission status ───────────────────────────────────────────

@router.patch("/staff/crm/commissions/{entry_id}/status", tags=["CRM Commissions"])
async def staff_update_commission_status(
    entry_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    from app.core.security import get_current_user_hybrid
    current_user = await get_current_user_hybrid(request, db)
    from app.models.staff import StaffEmployee
    if not isinstance(current_user, StaffEmployee):
        raise HTTPException(status_code=403, detail="Staff access only")

    body = await request.json()
    new_status = body.get("status")
    notes = body.get("notes")

    if new_status not in ("CONFIRMED", "CANCELLED", "PENDING"):
        raise HTTPException(status_code=400, detail="status must be CONFIRMED, CANCELLED, or PENDING")

    row = db.execute(
        text("SELECT id, status FROM crm_commission_entries WHERE id=:eid LIMIT 1"),
        {"eid": entry_id},
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Commission entry not found")

    update_fields = ["status=:new_status", "updated_at=NOW()"]
    params: dict = {"new_status": new_status, "eid": entry_id}

    if new_status == "CONFIRMED":
        update_fields.append("confirmed_at=NOW()")
        update_fields.append("confirmed_by_id=:staff_id")
        params["staff_id"] = current_user.id

    if notes is not None:
        update_fields.append("notes=:notes")
        params["notes"] = notes

    db.execute(
        text(
            f"UPDATE crm_commission_entries SET {', '.join(update_fields)} WHERE id=:eid"
        ),
        params,
    )
    db.commit()

    return {"success": True, "message": f"Commission entry #{entry_id} updated to {new_status}"}
