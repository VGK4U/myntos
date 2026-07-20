"""
Audience Resolver — DC_AUDIENCE_001

Centralised helper for the **audience-aware endpoint pattern** introduced
during the Mobile↔Web Parity programme (audit task #35, build phase A1)
and extended by Task #33 (VGK4U Member Parity Phase 1 — Read-Only Modules).

Rules (DC Protocol):
- Every member-facing endpoint that needs to serve both MNR (User table) and
  VGK4U (OfficialPartner table where category='VGK_TEAM') accepts an optional
  ``audience`` query parameter.
- ``audience`` defaults to ``'mnr'`` so every existing caller that does not
  pass the parameter gets identical behaviour to today (zero regression).
- Allowed values: ``'mnr'`` | ``'vgk4u'`` | ``'both'``.
- ``'both'`` is reserved for staff admin pages that explicitly want a merged
  view; member portals must pass ``'mnr'`` or ``'vgk4u'``, never ``'both'``.
- The resolver does **not** check JWT identity — that remains the
  responsibility of the endpoint's auth dependency (``get_current_user_hybrid``,
  ``get_current_vgk_member``, etc.).  This file only normalises the query
  parameter and offers small query-builder helpers.
- Response shape is identical regardless of audience (only the data source
  changes). VGK4U queries are scoped by category='VGK_TEAM' and (when
  applicable) company_id.
- Birthdays use OfficialPartner.dob_actual (default) or dob_document.
- Top Earners use vgk_team_income_entries.gross_amount (latest day) — separate
  from MNR pending_income ledger.

This module is **additive** — it introduces zero schema changes and does
not import anything beyond what is already in the runtime.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Dict, List, Literal, Optional, Tuple

from fastapi import Query
from sqlalchemy import and_, desc, extract, func
from sqlalchemy.orm import Session

Audience = Literal["mnr", "vgk4u", "both"]

VALID_AUDIENCES: Tuple[str, ...] = ("mnr", "vgk4u", "both")
DEFAULT_AUDIENCE: Audience = "mnr"

VGK_TEAM_CATEGORY = "VGK_TEAM"


def normalize_audience(value: Optional[str]) -> Audience:
    """
    Normalise an incoming ``audience`` query parameter.

    Returns ``'mnr'`` if the value is missing, empty, or unrecognised.
    Recognised values (case-insensitive): ``mnr``, ``vgk4u``, ``both``.

    Backward compatibility: any caller that does not pass ``audience`` (or
    passes a junk value) gets exactly the same response as the pre-A1 code.
    """
    if not value:
        return DEFAULT_AUDIENCE
    v = value.strip().lower()
    if v in VALID_AUDIENCES:
        return v  # type: ignore[return-value]
    return DEFAULT_AUDIENCE


def is_mnr(audience: Audience) -> bool:
    return audience in ("mnr", "both")


def is_vgk4u(audience: Audience) -> bool:
    return audience in ("vgk4u", "both")


def audience_label(audience: Audience) -> str:
    """Human-readable label for response payloads (echo back to client)."""
    return {
        "mnr": "MNR Members",
        "vgk4u": "VGK4U Members",
        "both": "All Members",
    }.get(audience, "MNR Members")


VGK4U_FEATURE_NAME = "vgk4u_enabled"


def is_vgk4u_enabled(db) -> bool:
    """
    Check the global VGK4U master switch.

    Wraps ``SystemControl.get_feature_status('vgk4u_enabled')``.  When the
    feature row does not exist it is auto-created in active state, mirroring
    the existing system-controls pattern.  Any DB error fails **closed**
    (returns False) so a corrupt/missing flag never accidentally exposes VGK
    data to MNR-only deployments.

    The Super Admin can flip this via the existing
    ``POST /api/v1/rvz/system-controls/toggle`` endpoint with
    ``feature_name='vgk4u_enabled'``.
    """
    try:
        # Local import keeps this module additive and avoids any startup
        # ordering issues with model registration.
        from app.models.system_control import SystemControl  # noqa: WPS433
        return bool(SystemControl.get_feature_status(db, VGK4U_FEATURE_NAME))
    except Exception:
        return False



def audience_query() -> Audience:
    """FastAPI dependency factory — accepts ?audience=mnr|vgk4u|both (default mnr)."""
    return Query(
        "mnr",
        description=(
            "Audience scope: 'mnr' = MNR User table (default, backward-compatible), "
            "'vgk4u' = OfficialPartner where category=VGK_TEAM, "
            "'both' = combined results."
        ),
        pattern="^(mnr|vgk4u|both)$",
    )


# ----------------------------------------------------------------------------
# Birthday queries (Task #33 Phase 1)
# ----------------------------------------------------------------------------

def _vgk4u_company_filter(query, company_id: Optional[int]):
    """DC_VGK4U_SEC_001 — multi-company isolation for VGK4U partners.

    OfficialPartner ↔ company is many-to-many via PartnerCompanySegment.
    When `company_id` is supplied, restrict the result set to partners that
    have at least one segment row for that company. When None, the caller
    is explicitly opting out of company scoping (e.g. RVZ ID global view).
    """
    if not company_id:
        return query
    from app.models.staff_accounts import OfficialPartner, PartnerCompanySegment

    return query.filter(
        OfficialPartner.id.in_(
            db_session_for_query(query).query(PartnerCompanySegment.partner_id).filter(
                PartnerCompanySegment.company_id == company_id
            )
        )
    )


def db_session_for_query(query):
    """Helper: extract the Session from a SQLAlchemy Query object."""
    return query.session


def resolve_company_id_from_user(current_user, db: Session) -> Optional[int]:
    """DC_VGK4U_SEC_001 — derive the active company_id for a request.

    Resolution order:
      1. If `current_user` already exposes a `company_id` attribute (StaffEmployee,
         OfficialPartner, etc.), use it.
      2. If it is an MNR `User` with no company concept, return None
         (super admin / global view — caller may further restrict if needed).
      3. Otherwise, attempt to look up the OfficialPartner row by user.id and
         return its `company_id`. Returns None if no partner row is found.

    Returning None means "no company filter" — appropriate for global super-admin
    contexts. All caller sites pass the result straight to the resolver, which
    short-circuits on None.
    """
    if current_user is None:
        return None

    # Direct attribute (StaffEmployee, OfficialPartner)
    cid = getattr(current_user, 'company_id', None)
    if cid:
        try:
            return int(cid)
        except (TypeError, ValueError):
            pass

    base_cid = getattr(current_user, 'base_company_id', None)
    if base_cid:
        try:
            return int(base_cid)
        except (TypeError, ValueError):
            pass

    # MNR Users have an `id` like 'MNR…'; try to find a paired OfficialPartner
    user_id = getattr(current_user, 'id', None)
    if user_id and isinstance(user_id, str):
        try:
            from app.models.staff_accounts import OfficialPartner
            partner = db.query(OfficialPartner).filter(
                OfficialPartner.partner_code == user_id
            ).first()
            if partner and getattr(partner, 'company_id', None):
                return int(partner.company_id)
        except Exception:
            pass

    return None


def vgk4u_birthday_users(
    db: Session,
    on_date: date,
    dob_field: str = "dob_actual",
    company_id: Optional[int] = None,
):
    """Return VGK4U partners whose dob_actual / dob_document falls on the given date.

    DC_VGK4U_SEC_001: When `company_id` is provided, results are restricted to
    partners associated with that company via PartnerCompanySegment.
    """
    from app.models.staff_accounts import OfficialPartner

    col = OfficialPartner.dob_actual if dob_field == "dob_actual" else OfficialPartner.dob_document
    q = db.query(OfficialPartner).filter(
        OfficialPartner.category == VGK_TEAM_CATEGORY,
        OfficialPartner.is_active == True,  # noqa: E712
        col.isnot(None),
        extract("month", col) == on_date.month,
        extract("day", col) == on_date.day,
    )
    q = _vgk4u_company_filter(q, company_id)
    return q.all()


def vgk4u_birthday_users_for_month(
    db: Session,
    month: int,
    dob_field: str = "dob_actual",
    company_id: Optional[int] = None,
):
    """Return VGK4U partners whose DOB month matches `month`.

    DC_VGK4U_SEC_001: company_id-scoped via PartnerCompanySegment when provided.
    """
    from app.models.staff_accounts import OfficialPartner

    col = OfficialPartner.dob_actual if dob_field == "dob_actual" else OfficialPartner.dob_document
    q = db.query(OfficialPartner).filter(
        OfficialPartner.category == VGK_TEAM_CATEGORY,
        OfficialPartner.is_active == True,  # noqa: E712
        col.isnot(None),
        extract("month", col) == month,
    )
    q = _vgk4u_company_filter(q, company_id)
    return q.all()


def vgk4u_partner_to_birthday_dict(partner, on_date: Optional[date] = None) -> Dict[str, Any]:
    """Mirror the MNR User birthday-card payload shape for a VGK4U partner."""
    dob = partner.dob_actual or partner.dob_document
    name = partner.partner_name or " ".join(filter(None, [partner.first_name, partner.last_name])) or partner.partner_code
    return {
        "user_id": partner.partner_code,
        "name": name,
        "email": partner.email,
        "phone": partner.phone,
        "location": f"{partner.city or 'Unknown'}, {partner.state or 'IN'}",
        "dob": dob.isoformat() if dob else None,
        "birthday_date": dob.isoformat() if dob else None,
        "has_photo": bool(getattr(partner, "logo_path", None)),
        "audience": "vgk4u",
    }


# ----------------------------------------------------------------------------
# VGK4U income / earnings queries (Task #33 Phase 1)
# ----------------------------------------------------------------------------

def vgk4u_top_earners(
    db: Session,
    limit: int = 7,
    company_id: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """
    Calculate VGK4U top earners based on the LATEST CONFIRMED income day in
    vgk_team_income_entries. Mirrors MNR `BannerService.calculate_top_earners`
    badge tier logic (Bronze/Silver/Gold/Platinum/Diamond).
    """
    from app.models.staff_accounts import OfficialPartner, VGKTeamIncomeEntry

    base = db.query(
        func.date(VGKTeamIncomeEntry.created_at).label("earning_date"),
        VGKTeamIncomeEntry.partner_id,
        func.sum(VGKTeamIncomeEntry.commission_amount + VGKTeamIncomeEntry.bonus_amount).label("gross"),
    ).filter(VGKTeamIncomeEntry.status == "CONFIRMED")

    if company_id:
        base = base.filter(VGKTeamIncomeEntry.company_id == company_id)

    latest = base.group_by(
        func.date(VGKTeamIncomeEntry.created_at),
        VGKTeamIncomeEntry.partner_id,
    ).having(
        func.sum(VGKTeamIncomeEntry.commission_amount + VGKTeamIncomeEntry.bonus_amount) > 1000
    ).order_by(desc(func.date(VGKTeamIncomeEntry.created_at))).limit(1).first()

    if not latest:
        return []

    latest_date = latest[0]

    earnings_q = db.query(
        VGKTeamIncomeEntry.partner_id,
        func.sum(VGKTeamIncomeEntry.commission_amount + VGKTeamIncomeEntry.bonus_amount).label("total_earnings"),
    ).filter(
        VGKTeamIncomeEntry.status == "CONFIRMED",
        func.date(VGKTeamIncomeEntry.created_at) == latest_date,
    )
    if company_id:
        earnings_q = earnings_q.filter(VGKTeamIncomeEntry.company_id == company_id)

    rows = earnings_q.group_by(VGKTeamIncomeEntry.partner_id).having(
        func.sum(VGKTeamIncomeEntry.commission_amount + VGKTeamIncomeEntry.bonus_amount) > 1000
    ).order_by(desc("total_earnings")).limit(limit).all()

    out: List[Dict[str, Any]] = []
    for rank, (partner_id, total) in enumerate(rows, start=1):
        partner = db.query(OfficialPartner).filter(
            OfficialPartner.id == partner_id,
            OfficialPartner.category == VGK_TEAM_CATEGORY,
            OfficialPartner.is_active == True,  # noqa: E712
        ).first()
        if not partner:
            continue
        amt = float(total or 0)
        if amt >= 50000:
            badge = "🏆 Diamond"
        elif amt >= 25000:
            badge = "💎 Platinum"
        elif amt >= 10000:
            badge = "🥇 Gold"
        elif amt >= 5000:
            badge = "🥈 Silver"
        else:
            badge = "🥉 Bronze"
        out.append({
            "user_id": partner.partner_code,
            "name": partner.partner_name,
            "total_earnings": amt,
            "rank": rank,
            "photo_url": partner.logo_path,
            "badge": badge,
            "latest_earning_date": latest_date.isoformat() if latest_date else None,
            "audience": "vgk4u",
        })
    return out


def vgk4u_income_summary(
    db: Session,
    partner_id: Optional[int] = None,
    company_id: Optional[int] = None,
) -> Dict[str, Any]:
    """Aggregate VGK4U income totals per level (mirrors MNR direct/matching/ved/guru shape)."""
    from app.models.staff_accounts import VGKTeamIncomeEntry

    q = db.query(
        VGKTeamIncomeEntry.level,
        func.coalesce(func.sum(VGKTeamIncomeEntry.commission_amount), 0).label("commission"),
        func.coalesce(func.sum(VGKTeamIncomeEntry.bonus_amount), 0).label("bonus"),
        func.count(VGKTeamIncomeEntry.id).label("entries"),
    ).filter(VGKTeamIncomeEntry.status == "CONFIRMED")
    if partner_id:
        q = q.filter(VGKTeamIncomeEntry.partner_id == partner_id)
    if company_id:
        q = q.filter(VGKTeamIncomeEntry.company_id == company_id)
    rows = q.group_by(VGKTeamIncomeEntry.level).all()

    by_level = {0: "Activation Bonus", 1: "Direct Referral",
                2: "Matching Referral", 3: "Guru Dakshina", 4: "Ved / Field Allowance"}
    summary: Dict[str, Any] = {}
    grand_total = 0.0
    for level, commission, bonus, entries in rows:
        key = by_level.get(int(level), f"Level {level}")
        amount = float(commission or 0) + float(bonus or 0)
        grand_total += amount
        summary[key] = {
            "level": int(level),
            "commission": float(commission or 0),
            "bonus": float(bonus or 0),
            "amount": amount,
            "entries": int(entries or 0),
        }
    summary["__grand_total__"] = grand_total
    return summary


def vgk4u_daywise_income(
    db: Session,
    partner_id: Optional[int] = None,
    company_id: Optional[int] = None,
    days: int = 30,
) -> List[Dict[str, Any]]:
    """Day-wise totals for VGK4U income (last N days)."""
    from app.models.staff_accounts import VGKTeamIncomeEntry

    q = db.query(
        func.date(VGKTeamIncomeEntry.created_at).label("d"),
        func.coalesce(func.sum(VGKTeamIncomeEntry.commission_amount + VGKTeamIncomeEntry.bonus_amount), 0).label("amount"),
        func.count(VGKTeamIncomeEntry.id).label("entries"),
    ).filter(VGKTeamIncomeEntry.status == "CONFIRMED")
    if partner_id:
        q = q.filter(VGKTeamIncomeEntry.partner_id == partner_id)
    if company_id:
        q = q.filter(VGKTeamIncomeEntry.company_id == company_id)
    rows = q.group_by("d").order_by(desc("d")).limit(days).all()
    return [
        {
            "date": d.isoformat() if d else None,
            "amount": float(amt or 0),
            "entries": int(n or 0),
        }
        for d, amt, n in rows
    ]


# ----------------------------------------------------------------------------
# Profile lookup (Task #33 Phase 1)
# ----------------------------------------------------------------------------

def vgk4u_profile_dict(partner) -> Dict[str, Any]:
    """Compact public-safe profile dict for a VGK4U partner."""
    name = partner.partner_name or " ".join(filter(None, [partner.first_name, partner.last_name])) or partner.partner_code
    return {
        "id": partner.id,
        "user_id": partner.partner_code,
        "partner_code": partner.partner_code,
        "name": name,
        "email": partner.email,
        "phone": partner.phone,
        "city": partner.city,
        "state": partner.state,
        "vgk_role": partner.vgk_role,
        "is_active": bool(partner.is_active),
        "is_paid_activation": bool(getattr(partner, "is_paid_activation", False)),
        "audience": "vgk4u",
    }


__all__ = [
    "Audience",
    "VALID_AUDIENCES",
    "DEFAULT_AUDIENCE",
    "VGK_TEAM_CATEGORY",
    "VGK4U_FEATURE_NAME",
    "normalize_audience",
    "is_mnr",
    "is_vgk4u",
    "is_vgk4u_enabled",
    "audience_label",
    "audience_query",
    "vgk4u_birthday_users",
    "vgk4u_birthday_users_for_month",
    "vgk4u_partner_to_birthday_dict",
    "vgk4u_top_earners",
    "vgk4u_income_summary",
    "vgk4u_daywise_income",
    "vgk4u_profile_dict",
]
