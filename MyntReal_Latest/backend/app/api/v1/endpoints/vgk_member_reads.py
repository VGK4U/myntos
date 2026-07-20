"""
VGK4U Member Read Endpoints — Task #37 (Phase 1 follow-up)

Audience-aware read endpoints for the VGK4U Member pages registered in the
staff sidebar with Zero-Default Access. Each endpoint accepts an
``audience: Literal['mnr','vgk4u','both']='mnr'`` query parameter and
branches its query against the correct source tables.

Covers 10 of the 16 routes (the other 6 — birthdays x4 + top-performers +
ev-discount/my-coupons — already had audience branches in banners.py /
ev_discount.py and are extended here only where needed):

    /api/v1/awards/my-awards
    /api/v1/income/daywise
    /api/v1/income/summary
    /api/v1/income/level/{n}     (n=1..4 → Direct/Matching/Guru/Ved)
    /api/v1/ev/benefits
    /api/v1/franchise/earnings
    /api/v1/insurance/earnings
    /api/v1/training/my-courses
    /api/v1/vgk/coupon-ledger
    /api/v1/vgk/my-submissions

For ``audience='vgk4u'`` we hit the VGK source tables
(``official_partners``, ``vgk_team_income_entries`` with status='CONFIRMED',
``vgk_coupon_ledger``, ``vgk_feedback``, ``ev_coupon_claim``).
For ``audience='mnr'`` (the default) the response stays backward compatible
— we either delegate to the legacy MNR source where applicable or return
an empty rows envelope (the legacy MNR pages already have their own
dedicated endpoints elsewhere; these new staff-side paths are net-new
read endpoints whose MNR branch is intentionally a thin shell).
"""

from __future__ import annotations

import logging
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc, func, text as sa_text
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user_hybrid
from app.core.audience_resolver import (
    Audience, normalize_audience, audience_label,
    resolve_company_id_from_user,
    vgk4u_daywise_income, vgk4u_income_summary,
)
from app.models.staff import StaffEmployee
from app.models.staff_accounts import OfficialPartner, VGKTeamIncomeEntry

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────
def _aud(audience: Optional[str]) -> Audience:
    return normalize_audience(audience)


def _envelope(items: List[Dict[str, Any]], audience: Audience, **extra) -> Dict[str, Any]:
    out = {
        "success": True,
        "audience": audience,
        "audience_label": audience_label(audience),
        "items": items,
        "count": len(items),
    }
    out.update(extra)
    return out


def _resolve_partner_id(current_user, db: Session) -> Optional[int]:
    """If the caller is a VGK partner, return their numeric id (for 'my-*'
    style scoping). Staff/User callers get None — i.e. company-wide view."""
    if isinstance(current_user, OfficialPartner):
        return int(current_user.id)
    return None


def _guard_vgk4u_access(current_user, aud: Audience) -> None:
    """RBAC guard for the staff/partner member pages.

    These endpoints back the 16 VGK4U Member pages in the staff sidebar
    and read partner/company-wide data from both the VGK4U tables
    (vgk_team_income_entries, vgk_coupon_ledger, vgk_feedback) and the
    MNR tables (income_entries, ev_coupon_claim, training_claim, …).
    Both data families are staff- or partner-scoped business data, so we
    require a StaffEmployee or OfficialPartner identity for ANY audience
    value. Without this, a regular MNR ``User`` could call the same route
    with ``audience=mnr`` and receive unscoped company-wide financial
    rows because ``resolve_company_id_from_user`` returns None for MNR
    users — i.e. a data-leak. We reject MNR/User callers up-front.
    """
    if isinstance(current_user, (StaffEmployee, OfficialPartner)):
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="This endpoint is restricted to staff and VGK partner accounts.",
    )


# =====================================================================
# Routers (one per URL prefix used by the frontend pages)
# =====================================================================
awards_router    = APIRouter(prefix="/awards",    tags=["VGK4U Member Reads — Awards"])
income_router    = APIRouter(prefix="/income",    tags=["VGK4U Member Reads — Income"])
ev_router        = APIRouter(prefix="/ev",        tags=["VGK4U Member Reads — EV Benefits"])
franchise_router = APIRouter(prefix="/franchise", tags=["VGK4U Member Reads — Franchise"])
insurance_router = APIRouter(prefix="/insurance", tags=["VGK4U Member Reads — Insurance"])
training_router  = APIRouter(prefix="/training",  tags=["VGK4U Member Reads — Training"])
vgk_router       = APIRouter(prefix="/vgk",       tags=["VGK4U Member Reads — Coupon & Submissions"])


# ─────────────────────────────────────────────────────────────────────
# /awards/my-awards
# ─────────────────────────────────────────────────────────────────────
@awards_router.get("/my-awards")
def get_my_awards(
    audience: Optional[str] = Query(None, description="mnr|vgk4u|both (default mnr)"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid),
):
    aud = _aud(audience)
    _guard_vgk4u_access(current_user, aud)
    company_id = resolve_company_id_from_user(current_user, db)
    items: List[Dict[str, Any]] = []

    # MNR branch — only an MNR User caller has a personal awards feed.
    # The user_award_progress table is not linked to a company, so we
    # deliberately do NOT return company-wide awards to staff callers
    # here to avoid cross-company visibility; staff should consume MNR
    # awards through dedicated company-scoped reports instead.
    if aud in ("mnr", "both"):
        from app.models.user import User as _User
        from app.models.awards import UserAwardProgress, DirectAwardTier
        if isinstance(current_user, _User):
            try:
                rows = db.query(UserAwardProgress, DirectAwardTier).outerjoin(
                    DirectAwardTier, DirectAwardTier.id == UserAwardProgress.award_tier_id
                ).filter(
                    UserAwardProgress.user_id == str(current_user.id),
                    UserAwardProgress.is_legacy_pre_reset == False,  # noqa: E712
                ).order_by(desc(UserAwardProgress.created_at)).limit(200).all()
                for prog, tier in rows:
                    items.append({
                        "id": prog.id,
                        "title": (tier.award_name if tier else None) or "Award",
                        "award_name": tier.award_name if tier else None,
                        "user_id": prog.user_id,
                        "won_at": prog.achieved_at.isoformat() if prog.achieved_at else None,
                        "created_at": prog.created_at.isoformat() if prog.created_at else None,
                        "status": prog.status or prog.award_status,
                        "amount": float(prog.award_amount or 0),
                        "audience": "mnr",
                    })
            except Exception as e:
                logger.warning(f"[MNR-AWARDS] query failed: {e}")

    if aud in ("vgk4u", "both"):
        # No dedicated vgk_award table yet — surface the activation bonus
        # (level=0) and any milestone bonus rows from vgk_team_income_entries
        # as "awards" so the page shows real data when it exists.
        partner_id = _resolve_partner_id(current_user, db)
        q = db.query(VGKTeamIncomeEntry).filter(
            VGKTeamIncomeEntry.status == "CONFIRMED",
            VGKTeamIncomeEntry.bonus_amount > 0,
        )
        if partner_id:
            q = q.filter(VGKTeamIncomeEntry.partner_id == partner_id)
        if company_id:
            q = q.filter(VGKTeamIncomeEntry.company_id == company_id)
        rows = q.order_by(desc(VGKTeamIncomeEntry.created_at)).limit(200).all()
        for r in rows:
            label = "Activation Bonus" if r.level == 0 else f"Level {r.level} Bonus"
            items.append({
                "id": r.id,
                "title": label,
                "award_name": label,
                "won_at": r.confirmed_at.isoformat() if r.confirmed_at else (
                    r.created_at.isoformat() if r.created_at else None
                ),
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "status": r.status,
                "amount": float(r.bonus_amount or 0),
                "audience": "vgk4u",
            })

    return _envelope(items, aud, awards=items)


# ─────────────────────────────────────────────────────────────────────
# /income/summary, /income/daywise, /income/level/{n}
# ─────────────────────────────────────────────────────────────────────
@income_router.get("/summary")
def income_summary(
    audience: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid),
):
    aud = _aud(audience)
    _guard_vgk4u_access(current_user, aud)
    summary: Dict[str, Any] = {}
    if aud in ("mnr", "both"):
        # MNR branch — aggregate income_entries by income_source_types.
        company_id = resolve_company_id_from_user(current_user, db)
        try:
            sql = """
                SELECT COALESCE(ist.source_name, 'OTHER') AS bucket,
                       COALESCE(SUM(i.amount), 0) AS total,
                       COUNT(*) AS entries
                  FROM income_entries i
                  LEFT JOIN income_source_types ist ON ist.id = i.income_source_id
                 WHERE i.status IN ('CONFIRMED','TALLY_DONE')
                   AND COALESCE(i.is_deleted, false) = false
                   {cid}
                 GROUP BY COALESCE(ist.source_name, 'OTHER')
                 ORDER BY total DESC
            """.format(cid="AND i.company_id = :cid" if company_id else "")
            params = {"cid": company_id} if company_id else {}
            rows = db.execute(sa_text(sql), params).fetchall()
            for r in rows:
                summary[r[0]] = {"amount": float(r[1] or 0), "entries": int(r[2] or 0)}
        except Exception as e:
            logger.warning(f"[MNR-INCOME-SUMMARY] query failed: {e}")
    if aud in ("vgk4u", "both"):
        partner_id = _resolve_partner_id(current_user, db)
        company_id = resolve_company_id_from_user(current_user, db)
        vgk_summary = vgk4u_income_summary(db, partner_id=partner_id, company_id=company_id)
        if aud == "both":
            # Always merge VGK4U buckets alongside MNR buckets — never skip.
            summary = {**summary, **{f"VGK4U_{k}": v for k, v in vgk_summary.items()}}
        else:
            summary = vgk_summary
    return {
        "success": True,
        "audience": aud,
        "audience_label": audience_label(aud),
        "summary": summary,
        "income_types": summary,
    }


@income_router.get("/daywise")
def income_daywise(
    audience: Optional[str] = Query(None),
    days: int = 30,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid),
):
    aud = _aud(audience)
    _guard_vgk4u_access(current_user, aud)
    items: List[Dict[str, Any]] = []
    if aud in ("mnr", "both"):
        company_id = resolve_company_id_from_user(current_user, db)
        try:
            sql = """
                SELECT i.income_date::date AS d,
                       COUNT(*) AS entries,
                       COALESCE(SUM(i.amount), 0) AS amount
                  FROM income_entries i
                 WHERE i.status IN ('CONFIRMED','TALLY_DONE')
                   AND COALESCE(i.is_deleted, false) = false
                   AND i.income_date >= (CURRENT_DATE - (:days || ' days')::interval)
                   {cid}
                 GROUP BY i.income_date::date
                 ORDER BY d DESC
            """.format(cid="AND i.company_id = :cid" if company_id else "")
            params: Dict[str, Any] = {"days": int(days)}
            if company_id:
                params["cid"] = company_id
            rows = db.execute(sa_text(sql), params).fetchall()
            for r in rows:
                items.append({
                    "date": r[0].isoformat() if r[0] else None,
                    "entries": int(r[1] or 0),
                    "amount": float(r[2] or 0),
                    "audience": "mnr",
                })
        except Exception as e:
            logger.warning(f"[MNR-INCOME-DAYWISE] query failed: {e}")
    if aud in ("vgk4u", "both"):
        partner_id = _resolve_partner_id(current_user, db)
        company_id = resolve_company_id_from_user(current_user, db)
        vgk_items = vgk4u_daywise_income(
            db, partner_id=partner_id, company_id=company_id, days=days,
        )
        # Tag every vgk4u row so the audience field is consistent regardless
        # of the request mode (single-tab or 'both').
        tagged_vgk = [{**dict(it), "audience": "vgk4u"} for it in vgk_items]
        if aud == "both":
            items.extend(tagged_vgk)
            # Keep the merged stream in chronological order (newest first)
            # so the UI never shows interleaved/mixed-order rows.
            items.sort(key=lambda r: (r.get("date") or ""), reverse=True)
        else:
            items = tagged_vgk
    return _envelope(items, aud, daywise=items, days=days)


@income_router.get("/level/{level}")
def income_by_level(
    level: int,
    audience: Optional[str] = Query(None),
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid),
):
    aud = _aud(audience)
    _guard_vgk4u_access(current_user, aud)
    items: List[Dict[str, Any]] = []

    if aud in ("mnr", "both"):
        # MNR has no concept of "level" on income_entries; surface most
        # recent confirmed entries scoped to the company instead so the
        # MNR tab still shows real rows.
        company_id = resolve_company_id_from_user(current_user, db)
        try:
            sql = """
                SELECT i.id, i.entry_number, i.income_date, i.amount,
                       i.status, i.payer_name, i.narration
                  FROM income_entries i
                 WHERE i.status IN ('CONFIRMED','TALLY_DONE')
                   AND COALESCE(i.is_deleted, false) = false
                   {cid}
                 ORDER BY i.income_date DESC, i.id DESC
                 LIMIT :lim
            """.format(cid="AND i.company_id = :cid" if company_id else "")
            params: Dict[str, Any] = {"lim": max(1, min(int(limit), 500))}
            if company_id:
                params["cid"] = company_id
            rows = db.execute(sa_text(sql), params).fetchall()
            for r in rows:
                items.append({
                    "id": r[0],
                    "entry_number": r[1],
                    "level": level,
                    "source_lead_id": None,
                    "commission_amount": float(r[3] or 0),
                    "bonus_amount": 0.0,
                    "revenue_amount": float(r[3] or 0),
                    "status": r[4],
                    "payer_name": r[5],
                    "narration": r[6],
                    "created_at": r[2].isoformat() if r[2] else None,
                    "audience": "mnr",
                })
        except Exception as e:
            logger.warning(f"[MNR-INCOME-LEVEL] query failed: {e}")

    if aud in ("vgk4u", "both") and 0 <= level <= 4:
        partner_id = _resolve_partner_id(current_user, db)
        company_id = resolve_company_id_from_user(current_user, db)
        q = db.query(VGKTeamIncomeEntry).filter(
            VGKTeamIncomeEntry.level == level,
            VGKTeamIncomeEntry.status == "CONFIRMED",
        )
        if partner_id:
            q = q.filter(VGKTeamIncomeEntry.partner_id == partner_id)
        if company_id:
            q = q.filter(VGKTeamIncomeEntry.company_id == company_id)
        rows = q.order_by(desc(VGKTeamIncomeEntry.created_at)).limit(max(1, min(limit, 500))).all()
        vgk_items = [{
            "id": r.id,
            "entry_number": r.entry_number,
            "level": r.level,
            "source_lead_id": r.source_lead_id,
            "commission_amount": float(r.commission_amount or 0),
            "bonus_amount": float(r.bonus_amount or 0),
            "revenue_amount": float(r.revenue_amount or 0),
            "status": r.status,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "confirmed_at": r.confirmed_at.isoformat() if r.confirmed_at else None,
            "audience": "vgk4u",
        } for r in rows]
        if aud == "both":
            # Merge with the MNR rows already collected — keep newest first.
            items.extend(vgk_items)
            items.sort(key=lambda r: (r.get("created_at") or ""), reverse=True)
        else:
            items = vgk_items

    return _envelope(items, aud, entries=items, level=level)


# ─────────────────────────────────────────────────────────────────────
# /ev/benefits
# ─────────────────────────────────────────────────────────────────────
@ev_router.get("/benefits")
def ev_benefits(
    audience: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid),
):
    aud = _aud(audience)
    _guard_vgk4u_access(current_user, aud)
    items: List[Dict[str, Any]] = []

    if aud in ("mnr", "both"):
        # MNR branch — only return data for an MNR ``User`` caller scoped
        # to their own claims. ev_coupon_claim has no company_id column,
        # so we deliberately do NOT surface a company-wide list for staff
        # callers here to avoid cross-company visibility in a multi-tenant
        # setup. Staff should consume MNR EV-claim data through dedicated
        # company-scoped reports instead.
        from app.models.user import User as _User
        if isinstance(current_user, _User):
            try:
                sql = """
                    SELECT c.id, c.created_at, c.discount_amount, c.claim_status,
                           e.model_name, c.customer_name
                      FROM ev_coupon_claim c
                      LEFT JOIN ev_model e ON e.id = c.ev_model_id
                     WHERE c.user_id = :uid
                     ORDER BY c.created_at DESC
                     LIMIT 200
                """
                rows = db.execute(sa_text(sql), {"uid": str(current_user.id)}).fetchall()
                for r in rows:
                    items.append({
                        "id": r[0],
                        "created_at": r[1].isoformat() if r[1] else None,
                        "date": r[1].isoformat() if r[1] else None,
                        "model": r[4],
                        "scooter_model": r[4],
                        "benefit": float(r[2] or 0),
                        "amount": float(r[2] or 0),
                        "status": r[3],
                        "customer_name": r[5],
                        "audience": "mnr",
                    })
            except Exception as e:
                logger.warning(f"[MNR-EV-BENEFITS] query failed: {e}")

    if aud in ("vgk4u", "both"):
        # VGK4U EV benefits are tracked as level-2 bonuses on
        # vgk_team_income_entries when the source lead is in the EV category.
        # In the absence of a dedicated VGK EV-benefits table, surface
        # bonus rows whose notes mention 'EV' or whose category_id maps
        # to the EV signup_category. Keep it best-effort — empty if none.
        partner_id = _resolve_partner_id(current_user, db)
        company_id = resolve_company_id_from_user(current_user, db)
        try:
            sql = """
                SELECT v.id, v.created_at, v.confirmed_at, v.bonus_amount, v.commission_amount,
                       v.status, v.notes, sc.category_name
                  FROM vgk_team_income_entries v
                  LEFT JOIN signup_categories sc ON sc.id = v.category_id
                 WHERE v.status = 'CONFIRMED'
                   AND COALESCE(sc.category_name,'') ILIKE '%EV%'
                   {pid}
                   {cid}
                 ORDER BY v.created_at DESC
                 LIMIT 200
            """.format(
                pid="AND v.partner_id = :pid" if partner_id else "",
                cid="AND v.company_id = :cid" if company_id else "",
            )
            params = {}
            if partner_id:
                params["pid"] = partner_id
            if company_id:
                params["cid"] = company_id
            rows = db.execute(sa_text(sql), params).fetchall()
            for r in rows:
                items.append({
                    "id": r[0],
                    "created_at": r[1].isoformat() if r[1] else None,
                    "date": r[1].isoformat() if r[1] else None,
                    "model": r[7] or "EV",
                    "scooter_model": r[7],
                    "benefit": float(r[3] or 0) + float(r[4] or 0),
                    "amount": float(r[3] or 0) + float(r[4] or 0),
                    "status": r[5],
                    "notes": r[6],
                    "audience": "vgk4u",
                })
        except Exception as e:
            logger.warning(f"[VGK4U-EV] benefits query failed: {e}")

    return _envelope(items, aud, benefits=items, claims=items)


# ─────────────────────────────────────────────────────────────────────
# /franchise/earnings
# ─────────────────────────────────────────────────────────────────────
@franchise_router.get("/earnings")
def franchise_earnings(
    audience: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid),
):
    aud = _aud(audience)
    _guard_vgk4u_access(current_user, aud)
    items: List[Dict[str, Any]] = []

    if aud in ("mnr", "both"):
        # MNR franchise earnings — recent CONFIRMED income_entries whose
        # signup_category matches franchise. Scoped to the caller's company.
        company_id = resolve_company_id_from_user(current_user, db)
        try:
            sql = """
                SELECT i.id, i.income_date, i.amount, i.status, i.payer_name,
                       sc.category_name
                  FROM income_entries i
                  LEFT JOIN signup_categories sc ON sc.id = i.revenue_category_id
                 WHERE i.status = 'CONFIRMED'
                   AND COALESCE(sc.category_name,'') ILIKE '%franchise%'
                   {cid}
                 ORDER BY i.income_date DESC
                 LIMIT 200
            """.format(cid="AND i.company_id = :cid" if company_id else "")
            params = {"cid": company_id} if company_id else {}
            rows = db.execute(sa_text(sql), params).fetchall()
            for r in rows:
                items.append({
                    "id": r[0],
                    "created_at": r[1].isoformat() if r[1] else None,
                    "date": r[1].isoformat() if r[1] else None,
                    "amount": float(r[2] or 0),
                    "status": r[3],
                    "partner_name": r[4],
                    "franchise_name": r[5],
                    "audience": "mnr",
                })
        except Exception as e:
            logger.warning(f"[MNR-FRANCHISE] earnings query failed: {e}")

    if aud in ("vgk4u", "both"):
        partner_id = _resolve_partner_id(current_user, db)
        company_id = resolve_company_id_from_user(current_user, db)
        try:
            sql = """
                SELECT v.id, v.created_at, v.commission_amount, v.bonus_amount, v.status,
                       p.partner_name, sc.category_name
                  FROM vgk_team_income_entries v
                  LEFT JOIN official_partners p ON p.id = v.partner_id
                  LEFT JOIN signup_categories sc ON sc.id = v.category_id
                 WHERE v.status = 'CONFIRMED'
                   AND COALESCE(sc.category_name,'') ILIKE '%franchise%'
                   {pid}
                   {cid}
                 ORDER BY v.created_at DESC
                 LIMIT 200
            """.format(
                pid="AND v.partner_id = :pid" if partner_id else "",
                cid="AND v.company_id = :cid" if company_id else "",
            )
            params = {}
            if partner_id:
                params["pid"] = partner_id
            if company_id:
                params["cid"] = company_id
            rows = db.execute(sa_text(sql), params).fetchall()
            for r in rows:
                items.append({
                    "id": r[0],
                    "created_at": r[1].isoformat() if r[1] else None,
                    "date": r[1].isoformat() if r[1] else None,
                    "amount": float(r[2] or 0) + float(r[3] or 0),
                    "status": r[4],
                    "partner_name": r[5],
                    "franchise_name": r[6],
                    "audience": "vgk4u",
                })
        except Exception as e:
            logger.warning(f"[VGK4U-FRANCHISE] earnings query failed: {e}")

    return _envelope(items, aud, earnings=items)


# ─────────────────────────────────────────────────────────────────────
# /insurance/earnings
# ─────────────────────────────────────────────────────────────────────
@insurance_router.get("/earnings")
def insurance_earnings(
    audience: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid),
):
    aud = _aud(audience)
    _guard_vgk4u_access(current_user, aud)
    items: List[Dict[str, Any]] = []

    if aud in ("mnr", "both"):
        # MNR insurance earnings — CONFIRMED income_entries with
        # signup_category matching insurance, scoped to caller's company.
        company_id = resolve_company_id_from_user(current_user, db)
        try:
            sql = """
                SELECT i.id, i.entry_number, i.income_date, i.amount,
                       i.status, sc.category_name, i.payer_name
                  FROM income_entries i
                  LEFT JOIN signup_categories sc ON sc.id = i.revenue_category_id
                 WHERE i.status = 'CONFIRMED'
                   AND COALESCE(sc.category_name,'') ILIKE '%insurance%'
                   {cid}
                 ORDER BY i.income_date DESC
                 LIMIT 200
            """.format(cid="AND i.company_id = :cid" if company_id else "")
            params = {"cid": company_id} if company_id else {}
            rows = db.execute(sa_text(sql), params).fetchall()
            for r in rows:
                items.append({
                    "id": r[0],
                    "policy_no": r[1],
                    "policy_number": r[1],
                    "created_at": r[2].isoformat() if r[2] else None,
                    "premium": float(r[3] or 0),
                    "earnings": float(r[3] or 0),
                    "commission": float(r[3] or 0),
                    "status": r[4],
                    "category": r[5],
                    "payer_name": r[6],
                    "audience": "mnr",
                })
        except Exception as e:
            logger.warning(f"[MNR-INSURANCE] earnings query failed: {e}")

    if aud in ("vgk4u", "both"):
        partner_id = _resolve_partner_id(current_user, db)
        company_id = resolve_company_id_from_user(current_user, db)
        try:
            sql = """
                SELECT v.id, v.entry_number, v.created_at,
                       v.revenue_amount, v.commission_amount, v.status,
                       sc.category_name
                  FROM vgk_team_income_entries v
                  LEFT JOIN signup_categories sc ON sc.id = v.category_id
                 WHERE v.status = 'CONFIRMED'
                   AND COALESCE(sc.category_name,'') ILIKE '%insurance%'
                   {pid}
                   {cid}
                 ORDER BY v.created_at DESC
                 LIMIT 200
            """.format(
                pid="AND v.partner_id = :pid" if partner_id else "",
                cid="AND v.company_id = :cid" if company_id else "",
            )
            params = {}
            if partner_id:
                params["pid"] = partner_id
            if company_id:
                params["cid"] = company_id
            rows = db.execute(sa_text(sql), params).fetchall()
            for r in rows:
                items.append({
                    "id": r[0],
                    "policy_no": r[1],
                    "policy_number": r[1],
                    "created_at": r[2].isoformat() if r[2] else None,
                    "premium": float(r[3] or 0),
                    "earnings": float(r[4] or 0),
                    "commission": float(r[4] or 0),
                    "status": r[5],
                    "category": r[6],
                    "audience": "vgk4u",
                })
        except Exception as e:
            logger.warning(f"[VGK4U-INSURANCE] earnings query failed: {e}")

    return _envelope(items, aud, policies=items)


# ─────────────────────────────────────────────────────────────────────
# /training/my-courses
# ─────────────────────────────────────────────────────────────────────
@training_router.get("/my-courses")
def training_my_courses(
    audience: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid),
):
    aud = _aud(audience)
    _guard_vgk4u_access(current_user, aud)
    items: List[Dict[str, Any]] = []

    if aud in ("mnr", "both"):
        # MNR branch — only an MNR ``User`` caller has a personal training
        # feed. training_claim has no company_id column, so we deliberately
        # do NOT surface a company-wide list to staff callers here to avoid
        # cross-company visibility. Staff should consume MNR training data
        # through dedicated company-scoped reports instead.
        from app.models.user import User as _User
        if isinstance(current_user, _User):
            try:
                sql = """
                    SELECT t.id, t.created_at, t.approved_at, t.completed_at,
                           t.claim_status, c.course_name
                      FROM training_claim t
                      LEFT JOIN training_course c ON c.id = t.training_course_id
                     WHERE t.user_id = :uid
                     ORDER BY t.created_at DESC
                     LIMIT 200
                """
                rows = db.execute(sa_text(sql), {"uid": str(current_user.id)}).fetchall()
                for r in rows:
                    completed = r[3] is not None
                    items.append({
                        "id": r[0],
                        "course_name": r[5] or "Training",
                        "title": r[5] or "Training",
                        "started_at": r[1].isoformat() if r[1] else None,
                        "created_at": r[1].isoformat() if r[1] else None,
                        "completed_at": r[3].isoformat() if r[3] else None,
                        "completion_percent": 100 if completed else (50 if r[2] else 0),
                        "progress": 100 if completed else (50 if r[2] else 0),
                        "status": r[4],
                        "audience": "mnr",
                    })
            except Exception as e:
                logger.warning(f"[MNR-TRAINING] query failed: {e}")

    if aud in ("vgk4u", "both"):
        partner_id = _resolve_partner_id(current_user, db)
        company_id = resolve_company_id_from_user(current_user, db)
        try:
            sql = """
                SELECT v.id, v.entry_number, v.created_at, v.confirmed_at, v.status,
                       sc.category_name
                  FROM vgk_team_income_entries v
                  LEFT JOIN signup_categories sc ON sc.id = v.category_id
                 WHERE COALESCE(sc.category_name,'') ILIKE '%training%'
                   {pid}
                   {cid}
                 ORDER BY v.created_at DESC
                 LIMIT 200
            """.format(
                pid="AND v.partner_id = :pid" if partner_id else "",
                cid="AND v.company_id = :cid" if company_id else "",
            )
            params = {}
            if partner_id:
                params["pid"] = partner_id
            if company_id:
                params["cid"] = company_id
            rows = db.execute(sa_text(sql), params).fetchall()
            for r in rows:
                started = r[2].isoformat() if r[2] else None
                completed = r[3] is not None
                items.append({
                    "id": r[0],
                    "course_name": r[5] or r[1] or "Training",
                    "title": r[5] or r[1] or "Training",
                    "started_at": started,
                    "created_at": started,
                    "completion_percent": 100 if completed else 0,
                    "progress": 100 if completed else 0,
                    "status": r[4],
                    "audience": "vgk4u",
                })
        except Exception as e:
            logger.warning(f"[VGK4U-TRAINING] my-courses query failed: {e}")

    return _envelope(items, aud, courses=items)


# ─────────────────────────────────────────────────────────────────────
# /vgk/coupon-ledger
# ─────────────────────────────────────────────────────────────────────
@vgk_router.get("/coupon-ledger")
def vgk_coupon_ledger(
    audience: Optional[str] = Query(None),
    limit: int = 200,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid),
):
    aud = _aud(audience)
    _guard_vgk4u_access(current_user, aud)
    items: List[Dict[str, Any]] = []

    if aud in ("vgk4u", "both"):
        partner_id = _resolve_partner_id(current_user, db)
        # DC_VGK4U_SEC_001: staff callers (no partner_id) MUST be scoped
        # to their own company so they don't see other companies' coupon
        # ledgers. vgk_coupon_ledger has no company_id, so we filter via
        # official_partners.company_id.
        staff_company_id: Optional[int] = None
        if partner_id is None and isinstance(current_user, StaffEmployee):
            staff_company_id = getattr(current_user, "company_id", None)
        try:
            base_sql = """
                SELECT l.id, l.partner_id, l.transaction_type, l.quantity,
                       l.related_partner_id, l.notes, l.created_at,
                       p.partner_name
                  FROM vgk_coupon_ledger l
                  LEFT JOIN official_partners p ON p.id = l.partner_id
                 WHERE 1=1
                   {pid}
                   {cid}
                 ORDER BY l.created_at DESC
                 LIMIT :lim
            """
            sql = base_sql.format(
                pid="AND l.partner_id = :pid" if partner_id else "",
                cid="AND p.company_id = :cid" if staff_company_id else "",
            )
            params: Dict[str, Any] = {"lim": max(1, min(int(limit), 500))}
            if partner_id:
                params["pid"] = partner_id
            if staff_company_id:
                params["cid"] = staff_company_id
            rows = db.execute(sa_text(sql), params).fetchall()
            for r in rows:
                items.append({
                    "id": r[0],
                    "partner_id": r[1],
                    "transaction_type": r[2],
                    "coupons": int(r[3] or 0),
                    "amount": int(r[3] or 0),
                    "quantity": int(r[3] or 0),
                    "related_partner_id": r[4],
                    "reason": r[5],
                    "reason_code": r[2],
                    "notes": r[5],
                    "created_at": r[6].isoformat() if r[6] else None,
                    "partner_name": r[7],
                    "audience": "vgk4u",
                })
        except Exception as e:
            logger.warning(f"[VGK4U-COUPON-LEDGER] query failed: {e}")

    return _envelope(items, aud, ledger=items)


# ─────────────────────────────────────────────────────────────────────
# /vgk/my-submissions
# ─────────────────────────────────────────────────────────────────────
@vgk_router.get("/my-submissions")
def vgk_my_submissions(
    audience: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid),
):
    aud = _aud(audience)
    _guard_vgk4u_access(current_user, aud)
    items: List[Dict[str, Any]] = []

    if aud in ("vgk4u", "both"):
        partner_id = _resolve_partner_id(current_user, db)
        # DC_VGK4U_SEC_001: staff callers (no partner_id) MUST be scoped
        # to their own company so they don't see other companies'
        # submissions. vgk_feedback has a native company_id column.
        staff_company_id: Optional[int] = None
        if partner_id is None and isinstance(current_user, StaffEmployee):
            staff_company_id = getattr(current_user, "company_id", None)
        try:
            sql = """
                SELECT id, partner_id, title, description, submission_type, status,
                       submitted_at, approved_at
                  FROM vgk_feedback
                 WHERE COALESCE(is_deleted, false) = false
                   {pid}
                   {cid}
                 ORDER BY submitted_at DESC
                 LIMIT 200
            """.format(
                pid="AND partner_id = :pid" if partner_id else "",
                cid="AND company_id = :cid" if staff_company_id else "",
            )
            params: Dict[str, Any] = {}
            if partner_id:
                params["pid"] = partner_id
            if staff_company_id:
                params["cid"] = staff_company_id
            rows = db.execute(sa_text(sql), params).fetchall()
            for r in rows:
                items.append({
                    "id": r[0],
                    "partner_id": r[1],
                    "title": r[2],
                    "description": r[3],
                    "type": r[4],
                    "submission_type": r[4],
                    "status": r[5],
                    "submitted_at": r[6].isoformat() if r[6] else None,
                    "created_at": r[6].isoformat() if r[6] else None,
                    "approved_at": r[7].isoformat() if r[7] else None,
                    "reference": f"VGK-FB-{r[0]}",
                    "reference_number": f"VGK-FB-{r[0]}",
                    "audience": "vgk4u",
                })
        except Exception as e:
            logger.warning(f"[VGK4U-MY-SUBMISSIONS] query failed: {e}")

    return _envelope(items, aud, submissions=items)


__all__ = [
    "awards_router", "income_router", "ev_router", "franchise_router",
    "insurance_router", "training_router", "vgk_router",
]
