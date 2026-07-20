"""
B2B SaaS Layer — Phase 1 Admin API (Task #39, Shadow Mode)

Auth model (per code-review guidance):
- /status                           → require_b2b_admin       (any active staff)
- everything else (cross-client)    → require_b2b_super_admin (super admins only)

A "b2b super admin" is a staff member whose role meets ANY of:
  • role_code in {'SUPER_ADMIN', 'B2B_SUPER_ADMIN', 'CEO', 'CTO', 'FOUNDER'}
  • role.hierarchy_level >= 90

DC: every write goes through _audit() to platform_audit_log with
actor_staff_id, before/after JSON, IST timestamps.
"""

from __future__ import annotations

import logging
from datetime import date
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Query, Body, status
from sqlalchemy import text
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from app.core.database import get_db
from app.api.v1.endpoints.staff_auth import get_current_staff_user
from app.models.staff import StaffEmployee
from app.models.base import get_indian_time
from app.models.platform_b2b import (
    PlatformClient, PlatformModule, PlatformPlan, PlatformPlanModule,
    PlatformSubscription, PlatformSubscriptionModule, PlatformModulePricing,
    PlatformClientModulePricingOverride, PlatformAuditLog, B2BShadowLog,
    PlatformModuleDependency,
)
from app.services.b2b_shadow import (
    is_module_entitled, resolve_client_id_for_staff, enforce_enabled,
)
from app.services.b2b_enforce import preview_entitlement, filter_menu_by_entitlement

router = APIRouter()
logger = logging.getLogger(__name__)

_SUPER_ADMIN_ROLE_CODES = {"SUPER_ADMIN", "B2B_SUPER_ADMIN", "CEO", "CTO", "FOUNDER"}
_SUPER_ADMIN_MIN_LEVEL = 90


# ─────────────────────────────────────────────────────────────────────────────
# Auth deps
# ─────────────────────────────────────────────────────────────────────────────
def require_b2b_admin(staff: StaffEmployee = Depends(get_current_staff_user)) -> StaffEmployee:
    """Any active authenticated staff user. Used only for /status."""
    return staff


def require_b2b_super_admin(staff: StaffEmployee = Depends(get_current_staff_user)) -> StaffEmployee:
    role = getattr(staff, "role", None)
    role_code = (getattr(role, "role_code", "") or "").upper()
    level = int(getattr(role, "hierarchy_level", 0) or 0)
    if role_code in _SUPER_ADMIN_ROLE_CODES or level >= _SUPER_ADMIN_MIN_LEVEL:
        return staff
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="B2B super-admin role required for cross-client operations",
    )


# ─────────────────────────────────────────────────────────────────────────────
def _audit(db: Session, *, actor_staff_id: Optional[int], client_id: Optional[int],
           entity: str, action: str, entity_id: Optional[int],
           before: Optional[dict] = None, after: Optional[dict] = None) -> None:
    try:
        db.add(PlatformAuditLog(
            actor_staff_id=actor_staff_id,
            client_id=client_id,
            entity=entity, action=action, entity_id=entity_id,
            before_json=before, after_json=after,
            created_at=get_indian_time(),
        ))
        db.commit()
    except Exception as exc:
        try:
            db.rollback()
        except Exception:
            pass
        logger.warning("[DC-B2B-AUDIT] failed to write audit row: %s", exc)


def _model_to_dict(obj) -> dict:
    out = {}
    for c in obj.__table__.columns:
        v = getattr(obj, c.name, None)
        if hasattr(v, "isoformat"):
            v = v.isoformat()
        out[c.name] = v
    return out


# ─────────────────────────────────────────────────────────────────────────────
# /status — Phase 1 visibility for ANY staff
# ─────────────────────────────────────────────────────────────────────────────
@router.get("/status")
def b2b_status(
    db: Session = Depends(get_db),
    _staff: StaffEmployee = Depends(require_b2b_super_admin),
):
    enforce = False
    try:
        import os
        enforce = (os.environ.get("B2B_ENFORCE", "false").lower() == "true")
    except Exception:
        pass

    # Defense-in-depth: count via SQLAlchemy ORM models so no string
    # interpolation of identifiers ever reaches the SQL engine (P0 hardening
    # from code review — the previous f"SELECT COUNT(*) FROM {tbl}" pattern
    # was safe today but unsafe by example).
    _COUNT_MAP = {
        "platform_clients":       PlatformClient,
        "platform_modules":       PlatformModule,
        "platform_plans":         PlatformPlan,
        "platform_subscriptions": PlatformSubscription,
        "b2b_shadow_log":         B2BShadowLog,
    }
    counts: Dict[str, int] = {}
    for label, Model in _COUNT_MAP.items():
        try:
            counts[label] = int(db.query(Model).count() or 0)
        except Exception:
            counts[label] = -1

    return {
        "phase": 1,
        "shadow_mode": True,
        "enforce_flag": enforce,
        "counts": counts,
    }


# ─────────────────────────────────────────────────────────────────────────────
# CLIENTS
# ─────────────────────────────────────────────────────────────────────────────
class ClientIn(BaseModel):
    client_code: str = Field(..., min_length=2, max_length=64)
    client_name: str = Field(..., min_length=2, max_length=200)
    contact_name: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    billing_currency: str = "INR"
    billing_address: Optional[str] = None
    notes: Optional[str] = None
    status: str = "active"
    # Phase 3a.0 — Tally/Zoho parity (legal-entity pointer + GST identity)
    primary_legal_entity_id: Optional[int] = None
    gstin: Optional[str] = Field(None, max_length=20)
    state_for_gst: Optional[str] = Field(None, max_length=80)
    pan_number: Optional[str] = Field(None, max_length=20)


@router.get("/clients")
def list_clients(
    db: Session = Depends(get_db),
    _staff: StaffEmployee = Depends(require_b2b_super_admin),
):
    rows = db.query(PlatformClient).order_by(PlatformClient.id.asc()).all()
    out = [_model_to_dict(r) for r in rows]
    # Phase 3a.1 — attach umbrella companies (associated_companies.client_id FK)
    # so the operator sees "this tenant -> these legal entities (self + others)".
    ac_rows = db.execute(text(
        "SELECT id, client_id, company_code, company_name, gst_number, state, is_active "
        "FROM associated_companies WHERE client_id IS NOT NULL "
        "ORDER BY client_id ASC, id ASC"
    )).fetchall()
    by_client: Dict[int, List[Dict[str, Any]]] = {}
    for ac in ac_rows:
        by_client.setdefault(ac[1], []).append({
            "id": ac[0], "company_code": ac[2], "company_name": ac[3],
            "gst_number": ac[4], "state": ac[5], "is_active": ac[6],
        })
    for c in out:
        umbrella = by_client.get(c["id"], [])
        primary_id = c.get("primary_legal_entity_id")
        for u in umbrella:
            u["is_primary"] = (u["id"] == primary_id)
        c["umbrella_companies"] = umbrella
    return {"clients": out}


@router.get("/legal-entities")
def list_legal_entities(
    db: Session = Depends(get_db),
    _staff: StaffEmployee = Depends(require_b2b_super_admin),
):
    """Phase 3a.1 — list active associated_companies for the
    'primary issuing legal entity' dropdown on the client edit modal.
    Reuses the existing AssociatedCompany table; no new schema."""
    rows = db.execute(text(
        "SELECT id, company_code, company_name, gst_number, state "
        "FROM associated_companies "
        "WHERE COALESCE(is_active, TRUE) = TRUE "
        "ORDER BY id ASC"
    )).fetchall()
    return {"legal_entities": [
        {"id": r[0], "company_code": r[1], "company_name": r[2],
         "gst_number": r[3], "state": r[4]} for r in rows
    ]}


# ─────────────────────────────────────────────────────────────────────────────
# COMPANIES (associated_companies management — Phase 3a.1)
# Reuses the existing table. Lets super-admin: list, attach to a tenant,
# detach, and toggle is_active. No new schema.
# ─────────────────────────────────────────────────────────────────────────────
@router.get("/companies")
def list_companies(
    db: Session = Depends(get_db),
    _staff: StaffEmployee = Depends(require_b2b_super_admin),
    unassigned_only: bool = Query(False),
    client_id: Optional[int] = Query(None),
):
    """List associated_companies with their tenant linkage.
    - unassigned_only=true → companies with client_id IS NULL (for attach picker)
    - client_id=N         → only companies under that tenant umbrella
    Without filters, returns all companies."""
    sql = ("SELECT ac.id, ac.client_id, pc.client_code, ac.company_code, "
           "ac.company_name, ac.gst_number, ac.state, ac.is_active "
           "FROM associated_companies ac "
           "LEFT JOIN platform_clients pc ON pc.id = ac.client_id ")
    params: Dict[str, Any] = {}
    where = []
    if unassigned_only:
        where.append("ac.client_id IS NULL")
    if client_id is not None:
        where.append("ac.client_id = :cid"); params["cid"] = client_id
    if where:
        sql += "WHERE " + " AND ".join(where) + " "
    sql += "ORDER BY ac.client_id NULLS FIRST, ac.id ASC"
    rows = db.execute(text(sql), params).fetchall()
    return {"companies": [
        {"id": r[0], "client_id": r[1], "client_code": r[2],
         "company_code": r[3], "company_name": r[4],
         "gst_number": r[5], "state": r[6], "is_active": r[7]}
        for r in rows
    ]}


@router.patch("/companies/{company_id}")
def update_company(
    company_id: int,
    payload: Dict[str, Any] = Body(...),
    db: Session = Depends(get_db),
    staff: StaffEmployee = Depends(require_b2b_super_admin),
):
    """Update tenant assignment and/or active status on an associated_company.
    Body keys honored: client_id (int|null), is_active (bool).
    Used by the Edit Client modal to attach / detach / activate / deactivate
    companies under a tenant umbrella."""
    row = db.execute(text(
        "SELECT id, client_id, company_code, company_name, is_active "
        "FROM associated_companies WHERE id = :i"
    ), {"i": company_id}).first()
    if not row:
        raise HTTPException(404, "company not found")
    before = {"id": row[0], "client_id": row[1], "company_code": row[2],
              "company_name": row[3], "is_active": row[4]}

    updates: Dict[str, Any] = {}
    if "client_id" in payload:
        cid = payload["client_id"]
        if cid is not None:
            cid = int(cid)
            ok = db.execute(text("SELECT 1 FROM platform_clients WHERE id=:i"),
                            {"i": cid}).first()
            if not ok:
                raise HTTPException(400, f"client_id={cid} does not exist")
        updates["client_id"] = cid
        # Phase 3a.1 — primary linkage invariant (defense-in-depth, UI also blocks):
        # if this AC is currently the primary_legal_entity_id of its current client,
        # do NOT allow detach (client_id=None) or cross-tenant move. Force the
        # operator to first change the issuing entity on the client itself.
        cur_client_id = before["client_id"]
        if cur_client_id is not None:
            primary = db.execute(text(
                "SELECT primary_legal_entity_id FROM platform_clients WHERE id=:i"
            ), {"i": cur_client_id}).first()
            if primary and primary[0] == company_id and cid != cur_client_id:
                raise HTTPException(
                    400,
                    f"company {company_id} is the primary issuing entity of client {cur_client_id}; "
                    "change 'Issuing entity (default)' on that client first, then detach/move."
                )
    if "is_active" in payload:
        updates["is_active"] = bool(payload["is_active"])
    if not updates:
        raise HTTPException(400, "no recognized fields to update (client_id, is_active)")

    set_sql = ", ".join(f"{k} = :{k}" for k in updates.keys())
    params = dict(updates); params["i"] = company_id; params["now"] = get_indian_time()
    db.execute(text(f"UPDATE associated_companies SET {set_sql}, updated_at=:now WHERE id=:i"),
               params)
    db.commit()

    after_row = db.execute(text(
        "SELECT id, client_id, company_code, company_name, is_active "
        "FROM associated_companies WHERE id = :i"
    ), {"i": company_id}).first()
    after = {"id": after_row[0], "client_id": after_row[1],
             "company_code": after_row[2], "company_name": after_row[3],
             "is_active": after_row[4]}

    # Audit under the impacted tenant (before OR after) so the audit-log filter works
    audit_client = after["client_id"] or before["client_id"]
    _audit(db, actor_staff_id=staff.id, client_id=audit_client,
           entity="B2B-COMPANY", action="UPDATE", entity_id=company_id,
           before=before, after=after)
    return after


@router.post("/clients")
def create_client(
    payload: ClientIn,
    db: Session = Depends(get_db),
    staff: StaffEmployee = Depends(require_b2b_super_admin),
):
    if db.query(PlatformClient).filter_by(client_code=payload.client_code).first():
        raise HTTPException(409, f"client_code {payload.client_code!r} already exists")
    # Phase 3a.1 — validate FK to associated_companies (active only)
    if payload.primary_legal_entity_id is not None:
        ok = db.execute(text(
            "SELECT 1 FROM associated_companies WHERE id=:i AND COALESCE(is_active, TRUE)=TRUE"
        ), {"i": payload.primary_legal_entity_id}).first()
        if not ok:
            raise HTTPException(400, f"primary_legal_entity_id={payload.primary_legal_entity_id} is not an active associated_company")
    row = PlatformClient(**payload.model_dump())
    db.add(row); db.commit(); db.refresh(row)
    _audit(db, actor_staff_id=staff.id, client_id=row.id, entity="B2B-CLIENT",
           action="CREATE", entity_id=row.id, after=_model_to_dict(row))
    return _model_to_dict(row)


@router.patch("/clients/{client_id}")
def update_client(
    client_id: int,
    payload: Dict[str, Any] = Body(...),
    db: Session = Depends(get_db),
    staff: StaffEmployee = Depends(require_b2b_super_admin),
):
    row = db.query(PlatformClient).filter_by(id=client_id).first()
    if not row:
        raise HTTPException(404, "client not found")
    before = _model_to_dict(row)
    allowed = {"client_name", "contact_name", "contact_email", "contact_phone",
               "billing_currency", "billing_address", "notes", "status",
               # Phase 3a.0 — Tally/Zoho parity
               "primary_legal_entity_id", "gstin", "state_for_gst", "pan_number"}
    # Phase 3a.1 — validate FK to associated_companies (active only) if being changed
    if "primary_legal_entity_id" in payload and payload["primary_legal_entity_id"] is not None:
        ok = db.execute(text(
            "SELECT 1 FROM associated_companies WHERE id=:i AND COALESCE(is_active, TRUE)=TRUE"
        ), {"i": payload["primary_legal_entity_id"]}).first()
        if not ok:
            raise HTTPException(400, f"primary_legal_entity_id={payload['primary_legal_entity_id']} is not an active associated_company")
    for k, v in payload.items():
        if k in allowed:
            setattr(row, k, v)
    row.updated_at = get_indian_time()
    db.commit(); db.refresh(row)
    _audit(db, actor_staff_id=staff.id, client_id=row.id, entity="B2B-CLIENT",
           action="UPDATE", entity_id=row.id, before=before, after=_model_to_dict(row))
    return _model_to_dict(row)


# ─────────────────────────────────────────────────────────────────────────────
# MODULES
# ─────────────────────────────────────────────────────────────────────────────
@router.get("/modules")
def list_modules(
    db: Session = Depends(get_db),
    _staff: StaffEmployee = Depends(require_b2b_super_admin),
    include_internal: bool = Query(True),
):
    q = db.query(PlatformModule)
    if not include_internal:
        q = q.filter(PlatformModule.internal_only.is_(False))
    return {"modules": [_model_to_dict(r) for r in q.order_by(PlatformModule.id.asc()).all()]}


@router.patch("/modules/{module_id}")
def update_module(
    module_id: int,
    payload: Dict[str, Any] = Body(...),
    db: Session = Depends(get_db),
    staff: StaffEmployee = Depends(require_b2b_super_admin),
):
    row = db.query(PlatformModule).filter_by(id=module_id).first()
    if not row:
        raise HTTPException(404, "module not found")
    before = _model_to_dict(row)
    allowed = {"module_name", "category", "description", "internal_only", "is_active", "custom_overrides",
               # Phase 3a.0 — Tally/Zoho parity
               "hsn_sac_code", "unit_of_measure", "default_tax_rate_pct"}
    # Phase 3a.1 — bounds-check GST rate (0..100) before letting it hit Numeric(5,2)
    if "default_tax_rate_pct" in payload and payload["default_tax_rate_pct"] is not None:
        try:
            r = float(payload["default_tax_rate_pct"])
        except (TypeError, ValueError):
            raise HTTPException(400, "default_tax_rate_pct must be a number")
        if r < 0 or r > 100:
            raise HTTPException(400, "default_tax_rate_pct must be between 0 and 100")
    for k, v in payload.items():
        if k in allowed:
            setattr(row, k, v)
    row.updated_at = get_indian_time()
    db.commit(); db.refresh(row)
    _audit(db, actor_staff_id=staff.id, client_id=None, entity="B2B-MODULE",
           action="UPDATE", entity_id=row.id, before=before, after=_model_to_dict(row))
    return _model_to_dict(row)


# ─────────────────────────────────────────────────────────────────────────────
# PLANS
# ─────────────────────────────────────────────────────────────────────────────
class PlanIn(BaseModel):
    plan_code: str = Field(..., min_length=2, max_length=64)
    plan_name: str = Field(..., min_length=2, max_length=200)
    description: Optional[str] = None
    is_active: bool = True


def _plan_rollup_rows(db: Session) -> Dict[int, Dict[str, Any]]:
    """Phase 3a.2 — single-pass rollup per plan_id.

    Aggregates across ACTIVE subscriptions:
      • active_subscription_count, total_seats, module_count
      • monthly_billing_value (INR; per_seat × seats, per_company × 1, flat × 1)
      • annual_billing_value  (annual subs use 12 - free_months factor; monthly subs × 12)
      • cleared_amount  (sum of paid invoices)
      • pending_amount  (sum of open + partial + overdue invoices)

    Currency note: pricing column used is INR. The rollup is a *display* aid;
    the authoritative invoice amount remains whatever was captured at issue
    time (and that uses the sub's own currency).
    """
    sql = text("""
    WITH active_subs AS (
        SELECT id, client_id, plan_id, billing_cycle, seat_count,
               COALESCE(annual_free_months, 2) AS annual_free_months
          FROM platform_subscriptions
         WHERE status = 'active' AND plan_id IS NOT NULL
    ),
    sub_module_value AS (
        SELECT s.id          AS sub_id,
               s.plan_id     AS plan_id,
               s.billing_cycle,
               s.seat_count,
               s.annual_free_months,
               COALESCE(ovr.price_inr,    pmp.price_inr,    0)             AS price_inr,
               COALESCE(ovr.pricing_unit, pmp.pricing_unit, 'per_company') AS pricing_unit
          FROM active_subs s
          JOIN platform_subscription_modules psm
                ON psm.subscription_id = s.id AND psm.enabled = TRUE
          LEFT JOIN platform_module_pricing pmp
                ON pmp.module_id = psm.module_id
          LEFT JOIN platform_client_module_pricing_override ovr
                ON ovr.client_id = s.client_id AND ovr.module_id = psm.module_id
    ),
    sub_monthly AS (
        SELECT sub_id, plan_id, billing_cycle, seat_count, annual_free_months,
               SUM(CASE WHEN pricing_unit = 'per_seat'
                        THEN price_inr * seat_count
                        ELSE price_inr END) AS monthly_inr
          FROM sub_module_value
         GROUP BY sub_id, plan_id, billing_cycle, seat_count, annual_free_months
    ),
    plan_rollup AS (
        SELECT plan_id,
               COUNT(*)                                            AS active_subscription_count,
               COALESCE(SUM(seat_count), 0)                        AS total_seats,
               COALESCE(SUM(monthly_inr), 0)                       AS monthly_billing_value,
               COALESCE(SUM(CASE WHEN billing_cycle = 'annual'
                                 THEN monthly_inr * GREATEST(0, 12 - annual_free_months)
                                 ELSE monthly_inr * 12 END), 0)    AS annual_billing_value
          FROM sub_monthly
         GROUP BY plan_id
    ),
    plan_inv AS (
        SELECT s.plan_id,
               COALESCE(SUM(CASE WHEN i.status = 'paid'
                                 THEN COALESCE(i.grand_total, i.total, 0)
                                 ELSE 0 END), 0) AS cleared_amount,
               COALESCE(SUM(CASE WHEN i.status IN ('open','partial','overdue')
                                 THEN COALESCE(i.grand_total, i.total, 0)
                                 ELSE 0 END), 0) AS pending_amount
          FROM platform_invoices i
          JOIN platform_subscriptions s ON s.id = i.subscription_id
         WHERE s.plan_id IS NOT NULL
         GROUP BY s.plan_id
    ),
    plan_modules_count AS (
        SELECT plan_id, COUNT(*) AS module_count
          FROM platform_plan_modules
         GROUP BY plan_id
    )
    SELECT p.id AS plan_id,
           COALESCE(pmc.module_count, 0)              AS module_count,
           COALESCE(pr.active_subscription_count, 0)  AS active_subscription_count,
           COALESCE(pr.total_seats, 0)                AS total_seats,
           COALESCE(pr.monthly_billing_value, 0)      AS monthly_billing_value,
           COALESCE(pr.annual_billing_value, 0)       AS annual_billing_value,
           COALESCE(pi.cleared_amount, 0)             AS cleared_amount,
           COALESCE(pi.pending_amount, 0)             AS pending_amount
      FROM platform_plans p
      LEFT JOIN plan_rollup pr        ON pr.plan_id  = p.id
      LEFT JOIN plan_inv pi           ON pi.plan_id  = p.id
      LEFT JOIN plan_modules_count pmc ON pmc.plan_id = p.id
    """)
    return {
        int(r["plan_id"]): {
            "module_count":              int(r["module_count"]),
            "active_subscription_count": int(r["active_subscription_count"]),
            "total_seats":               int(r["total_seats"]),
            "monthly_billing_value":     float(r["monthly_billing_value"] or 0),
            "annual_billing_value":      float(r["annual_billing_value"] or 0),
            "cleared_amount":            float(r["cleared_amount"] or 0),
            "pending_amount":            float(r["pending_amount"] or 0),
        }
        for r in db.execute(sql).mappings().all()
    }


@router.get("/plans")
def list_plans(
    db: Session = Depends(get_db),
    _staff: StaffEmployee = Depends(require_b2b_super_admin),
):
    rows = db.query(PlatformPlan).order_by(PlatformPlan.id.asc()).all()
    rollup = _plan_rollup_rows(db)
    # Phase 3a.2 — fetch all plan_modules in ONE query, group in Python (avoid N+1).
    pm_by_plan: Dict[int, List[int]] = {}
    for pm in db.query(PlatformPlanModule).all():
        pm_by_plan.setdefault(pm.plan_id, []).append(pm.module_id)
    out = []
    for p in rows:
        d = _model_to_dict(p)
        d["module_ids"] = pm_by_plan.get(p.id, [])
        d.update(rollup.get(p.id, {
            "module_count": len(d["module_ids"]),
            "active_subscription_count": 0, "total_seats": 0,
            "monthly_billing_value": 0.0, "annual_billing_value": 0.0,
            "cleared_amount": 0.0, "pending_amount": 0.0,
        }))
        out.append(d)
    return {"plans": out}


@router.post("/plans")
def create_plan(
    payload: PlanIn,
    db: Session = Depends(get_db),
    staff: StaffEmployee = Depends(require_b2b_super_admin),
):
    if db.query(PlatformPlan).filter_by(plan_code=payload.plan_code).first():
        raise HTTPException(409, f"plan_code {payload.plan_code!r} already exists")
    row = PlatformPlan(**payload.model_dump())
    db.add(row); db.commit(); db.refresh(row)
    _audit(db, actor_staff_id=staff.id, client_id=None, entity="B2B-PLAN",
           action="CREATE", entity_id=row.id, after=_model_to_dict(row))
    return _model_to_dict(row)


# ─────────────────────────────────────────────────────────────────────────────
# SUBSCRIPTIONS
# ─────────────────────────────────────────────────────────────────────────────
class SubscriptionIn(BaseModel):
    client_id: int
    plan_id: Optional[int] = None
    display_plan_name: Optional[str] = None
    billing_currency: str = "INR"
    billing_cycle: str = "monthly"
    is_trial: bool = False
    status: str = "active"
    starts_on: Optional[date] = None
    ends_on: Optional[date] = None
    trial_ends_on: Optional[date] = None
    # Phase 3a.2 — seat = staff login count for the tenant
    seat_count: int = Field(default=1, ge=1)


@router.get("/subscriptions")
def list_subscriptions(
    db: Session = Depends(get_db),
    _staff: StaffEmployee = Depends(require_b2b_super_admin),
    client_id: Optional[int] = Query(None),
):
    q = db.query(PlatformSubscription)
    if client_id is not None:
        q = q.filter(PlatformSubscription.client_id == client_id)
    return {"subscriptions": [_model_to_dict(r) for r in q.order_by(PlatformSubscription.id.asc()).all()]}


@router.post("/subscriptions")
def create_subscription(
    payload: SubscriptionIn,
    db: Session = Depends(get_db),
    staff: StaffEmployee = Depends(require_b2b_super_admin),
):
    if not db.query(PlatformClient).filter_by(id=payload.client_id).first():
        raise HTTPException(404, "client not found")
    row = PlatformSubscription(**payload.model_dump())
    db.add(row); db.commit(); db.refresh(row)
    _audit(db, actor_staff_id=staff.id, client_id=row.client_id, entity="B2B-SUB",
           action="CREATE", entity_id=row.id, after=_model_to_dict(row))
    return _model_to_dict(row)


# ─────────────────────────────────────────────────────────────────────────────
# PRICING (global)
# ─────────────────────────────────────────────────────────────────────────────
class PricingIn(BaseModel):
    module_id: int
    price_inr: float = 0
    price_usd: float = 0
    pricing_unit: str = "per_company"


@router.get("/pricing")
def list_pricing(
    db: Session = Depends(get_db),
    _staff: StaffEmployee = Depends(require_b2b_super_admin),
):
    return {"pricing": [_model_to_dict(r) for r in db.query(PlatformModulePricing).all()]}


@router.put("/pricing")
def upsert_pricing(
    payload: PricingIn,
    db: Session = Depends(get_db),
    staff: StaffEmployee = Depends(require_b2b_super_admin),
):
    row = db.query(PlatformModulePricing).filter_by(module_id=payload.module_id).first()
    before = _model_to_dict(row) if row else None
    if row:
        row.price_inr = payload.price_inr
        row.price_usd = payload.price_usd
        row.pricing_unit = payload.pricing_unit
        row.updated_at = get_indian_time()
    else:
        row = PlatformModulePricing(**payload.model_dump())
        db.add(row)
    db.commit(); db.refresh(row)
    _audit(db, actor_staff_id=staff.id, client_id=None, entity="B2B-PRICE",
           action="UPDATE" if before else "CREATE",
           entity_id=row.id, before=before, after=_model_to_dict(row))
    return _model_to_dict(row)


# ─────────────────────────────────────────────────────────────────────────────
# PRICING OVERRIDES (per-client)
# ─────────────────────────────────────────────────────────────────────────────
@router.get("/pricing-overrides")
def list_pricing_overrides(
    db: Session = Depends(get_db),
    _staff: StaffEmployee = Depends(require_b2b_super_admin),
    client_id: Optional[int] = Query(None),
):
    q = db.query(PlatformClientModulePricingOverride)
    if client_id is not None:
        q = q.filter(PlatformClientModulePricingOverride.client_id == client_id)
    return {"overrides": [_model_to_dict(r) for r in q.all()]}


# ─────────────────────────────────────────────────────────────────────────────
# AUDIT
# ─────────────────────────────────────────────────────────────────────────────
@router.get("/audit")
def list_audit(
    db: Session = Depends(get_db),
    _staff: StaffEmployee = Depends(require_b2b_super_admin),
    limit: int = Query(200, le=1000),
    entity: Optional[str] = Query(None),
    client_id: Optional[int] = Query(None),
):
    q = db.query(PlatformAuditLog)
    if entity:
        q = q.filter(PlatformAuditLog.entity == entity)
    if client_id is not None:
        q = q.filter(PlatformAuditLog.client_id == client_id)
    rows = q.order_by(PlatformAuditLog.id.desc()).limit(limit).all()
    return {"audit": [_model_to_dict(r) for r in rows]}


# ─────────────────────────────────────────────────────────────────────────────
# SHADOW LOG
# ─────────────────────────────────────────────────────────────────────────────
@router.get("/shadow-log")
def list_shadow_log(
    db: Session = Depends(get_db),
    _staff: StaffEmployee = Depends(require_b2b_super_admin),
    limit: int = Query(200, le=1000),
    decision: Optional[str] = Query(None),
):
    q = db.query(B2BShadowLog)
    if decision:
        q = q.filter(B2BShadowLog.decision == decision)
    rows = q.order_by(B2BShadowLog.id.desc()).limit(limit).all()
    return {"shadow_log": [_model_to_dict(r) for r in rows]}


# =============================================================================
# Task #40 — Phase 2 (Admin UX & Pricing CRUD)
# =============================================================================

# ─────────────────────────────────────────────────────────────────────────────
# CLIENTS — detail + soft-delete
# ─────────────────────────────────────────────────────────────────────────────
@router.get("/clients/{client_id}")
def get_client(
    client_id: int,
    db: Session = Depends(get_db),
    _staff: StaffEmployee = Depends(require_b2b_super_admin),
):
    row = db.query(PlatformClient).filter_by(id=client_id).first()
    if not row:
        raise HTTPException(404, "client not found")
    out = _model_to_dict(row)
    out["subscriptions"] = [
        _model_to_dict(s) for s in
        db.query(PlatformSubscription).filter_by(client_id=client_id).all()
    ]
    out["overrides"] = [
        _model_to_dict(o) for o in
        db.query(PlatformClientModulePricingOverride).filter_by(client_id=client_id).all()
    ]
    return out


@router.delete("/clients/{client_id}")
def archive_client(
    client_id: int,
    db: Session = Depends(get_db),
    staff: StaffEmployee = Depends(require_b2b_super_admin),
):
    row = db.query(PlatformClient).filter_by(id=client_id).first()
    if not row:
        raise HTTPException(404, "client not found")
    if row.is_internal:
        raise HTTPException(400, "cannot archive the internal client")
    before = _model_to_dict(row)
    row.status = "archived"
    row.updated_at = get_indian_time()
    db.commit()
    _audit(db, actor_staff_id=staff.id, client_id=row.id, entity="B2B-CLIENT",
           action="UPDATE", entity_id=row.id, before=before, after=_model_to_dict(row))
    return {"ok": True, "id": row.id, "status": "archived"}


# ─────────────────────────────────────────────────────────────────────────────
# MODULES — dependencies CRUD
# ─────────────────────────────────────────────────────────────────────────────
class DependencyIn(BaseModel):
    depends_on_module_id: int


@router.get("/modules/{module_id}/dependencies")
def list_module_dependencies(
    module_id: int,
    db: Session = Depends(get_db),
    _staff: StaffEmployee = Depends(require_b2b_super_admin),
):
    rows = db.query(PlatformModuleDependency).filter_by(module_id=module_id).all()
    return {"dependencies": [_model_to_dict(r) for r in rows]}


@router.post("/modules/{module_id}/dependencies")
def add_module_dependency(
    module_id: int,
    payload: DependencyIn,
    db: Session = Depends(get_db),
    staff: StaffEmployee = Depends(require_b2b_super_admin),
):
    if module_id == payload.depends_on_module_id:
        raise HTTPException(400, "module cannot depend on itself")
    if not db.query(PlatformModule).filter_by(id=module_id).first():
        raise HTTPException(404, "module not found")
    if not db.query(PlatformModule).filter_by(id=payload.depends_on_module_id).first():
        raise HTTPException(404, "dependency module not found")
    existing = db.query(PlatformModuleDependency).filter_by(
        module_id=module_id, depends_on_module_id=payload.depends_on_module_id,
    ).first()
    if existing:
        return _model_to_dict(existing)
    row = PlatformModuleDependency(
        module_id=module_id, depends_on_module_id=payload.depends_on_module_id,
    )
    db.add(row); db.commit(); db.refresh(row)
    _audit(db, actor_staff_id=staff.id, client_id=None, entity="B2B-MODULE",
           action="UPDATE", entity_id=module_id,
           after={"added_dependency_on": payload.depends_on_module_id})
    return _model_to_dict(row)


@router.delete("/modules/{module_id}/dependencies/{dep_id}")
def remove_module_dependency(
    module_id: int, dep_id: int,
    db: Session = Depends(get_db),
    staff: StaffEmployee = Depends(require_b2b_super_admin),
):
    row = db.query(PlatformModuleDependency).filter_by(
        id=dep_id, module_id=module_id
    ).first()
    if not row:
        raise HTTPException(404, "dependency not found")
    before = _model_to_dict(row)
    db.delete(row); db.commit()
    _audit(db, actor_staff_id=staff.id, client_id=None, entity="B2B-MODULE",
           action="UPDATE", entity_id=module_id, before=before)
    return {"ok": True, "deleted": dep_id}


# ─────────────────────────────────────────────────────────────────────────────
# PLANS — detail + update + module attach/detach + deactivate
# ─────────────────────────────────────────────────────────────────────────────
class PlanModuleIn(BaseModel):
    module_id: int


@router.get("/plans/{plan_id}")
def get_plan(
    plan_id: int,
    db: Session = Depends(get_db),
    _staff: StaffEmployee = Depends(require_b2b_super_admin),
):
    row = db.query(PlatformPlan).filter_by(id=plan_id).first()
    if not row:
        raise HTTPException(404, "plan not found")
    d = _model_to_dict(row)
    d["module_ids"] = [m.module_id for m in
                       db.query(PlatformPlanModule).filter_by(plan_id=plan_id).all()]
    # Phase 3a.2 — rollup so the Edit modal can show "this many subs will be touched"
    d.update(_plan_rollup_rows(db).get(plan_id, {
        "module_count": len(d["module_ids"]),
        "active_subscription_count": 0, "total_seats": 0,
        "monthly_billing_value": 0.0, "annual_billing_value": 0.0,
        "cleared_amount": 0.0, "pending_amount": 0.0,
    }))
    return d


@router.post("/plans/{plan_id}/modules/sync")
def sync_plan_modules(
    plan_id: int,
    payload: Dict[str, Any] = Body(...),
    db: Session = Depends(get_db),
    staff: StaffEmployee = Depends(require_b2b_super_admin),
):
    """
    Phase 3a.2 — replace the plan's module set with the given module_ids,
    optionally propagate the delta to every active subscription on this
    plan and emit a pro-rata adjustment invoice per affected subscription.

    Body: {"module_ids": [int], "propagate": true}
    """
    plan = db.query(PlatformPlan).filter_by(id=plan_id).first()
    if not plan:
        raise HTTPException(404, "plan not found")
    raw_ids = payload.get("module_ids")
    if not isinstance(raw_ids, list):
        raise HTTPException(400, "module_ids must be a list of integers")
    try:
        target_ids = sorted({int(x) for x in raw_ids})
    except (TypeError, ValueError):
        raise HTTPException(400, "module_ids must be integers")
    propagate = bool(payload.get("propagate", True))

    # Validate every target id exists.
    if target_ids:
        found = {r[0] for r in db.execute(
            text("SELECT id FROM platform_modules WHERE id = ANY(:ids)"),
            {"ids": target_ids},
        ).all()}
        missing = sorted(set(target_ids) - found)
        if missing:
            raise HTTPException(400, f"unknown module_ids: {missing}")

    # Compute delta vs current plan.
    current_ids = {
        m.module_id for m in
        db.query(PlatformPlanModule).filter_by(plan_id=plan_id).all()
    }
    target_set = set(target_ids)
    plan_added = sorted(target_set - current_ids)
    plan_removed = sorted(current_ids - target_set)

    # 1) Mutate plan_modules.
    for mid in plan_added:
        db.add(PlatformPlanModule(plan_id=plan_id, module_id=mid))
    if plan_removed:
        db.execute(
            text("DELETE FROM platform_plan_modules "
                 "WHERE plan_id=:pid AND module_id = ANY(:ids)"),
            {"pid": plan_id, "ids": plan_removed},
        )
    db.flush()

    _audit(db, actor_staff_id=staff.id, client_id=None, entity="B2B-PLAN",
           action="UPDATE", entity_id=plan_id,
           before={"module_ids": sorted(current_ids)},
           after={"module_ids": target_ids,
                  "added": plan_added, "removed": plan_removed,
                  "propagate": propagate})
    db.commit()

    sub_results: List[Dict[str, Any]] = []
    if propagate and (plan_added or plan_removed):
        # Lazy import to avoid any circular at module load.
        from app.services.platform_b2b_billing import apply_subscription_module_delta

        active_subs = db.query(PlatformSubscription).filter_by(
            plan_id=plan_id, status="active").all()
        for sub in active_subs:
            try:
                res = apply_subscription_module_delta(
                    db, sub.id,
                    add_module_ids=plan_added,
                    remove_module_ids=plan_removed,
                    actor_staff_id=staff.id,
                )
                sub_results.append(res)
                _audit(db, actor_staff_id=staff.id, client_id=sub.client_id,
                       entity="B2B-SUB", action="UPDATE", entity_id=sub.id,
                       after={"plan_sync_invoice_id": res.get("invoice_id"),
                              "added": res.get("added"),
                              "removed": res.get("removed"),
                              "charged": res.get("charged"),
                              "credited": res.get("credited"),
                              "skipped_reason": res.get("skipped_reason")})
            except Exception as e:
                logger.exception("plan-sync propagation failed for sub#%s", sub.id)
                sub_results.append({"sub_id": sub.id, "error": str(e)})
        db.commit()

    return {
        "plan_id": plan_id,
        "module_ids": target_ids,
        "added": plan_added,
        "removed": plan_removed,
        "propagated": propagate,
        "sub_results": sub_results,
    }


@router.patch("/plans/{plan_id}")
def update_plan(
    plan_id: int,
    payload: Dict[str, Any] = Body(...),
    db: Session = Depends(get_db),
    staff: StaffEmployee = Depends(require_b2b_super_admin),
):
    row = db.query(PlatformPlan).filter_by(id=plan_id).first()
    if not row:
        raise HTTPException(404, "plan not found")
    before = _model_to_dict(row)
    allowed = {"plan_name", "description", "is_active"}
    for k, v in payload.items():
        if k in allowed:
            setattr(row, k, v)
    row.updated_at = get_indian_time()
    db.commit(); db.refresh(row)
    _audit(db, actor_staff_id=staff.id, client_id=None, entity="B2B-PLAN",
           action="UPDATE", entity_id=row.id, before=before, after=_model_to_dict(row))
    return _model_to_dict(row)


@router.delete("/plans/{plan_id}")
def deactivate_plan(
    plan_id: int,
    db: Session = Depends(get_db),
    staff: StaffEmployee = Depends(require_b2b_super_admin),
):
    row = db.query(PlatformPlan).filter_by(id=plan_id).first()
    if not row:
        raise HTTPException(404, "plan not found")
    if row.plan_code == "INTERNAL_FULL":
        raise HTTPException(400, "cannot deactivate the internal full plan")
    before = _model_to_dict(row)
    row.is_active = False
    row.updated_at = get_indian_time()
    db.commit()
    _audit(db, actor_staff_id=staff.id, client_id=None, entity="B2B-PLAN",
           action="UPDATE", entity_id=row.id, before=before, after=_model_to_dict(row))
    return {"ok": True, "id": plan_id, "is_active": False}


@router.post("/plans/{plan_id}/modules")
def attach_plan_module(
    plan_id: int,
    payload: PlanModuleIn,
    db: Session = Depends(get_db),
    staff: StaffEmployee = Depends(require_b2b_super_admin),
):
    if not db.query(PlatformPlan).filter_by(id=plan_id).first():
        raise HTTPException(404, "plan not found")
    if not db.query(PlatformModule).filter_by(id=payload.module_id).first():
        raise HTTPException(404, "module not found")
    existing = db.query(PlatformPlanModule).filter_by(
        plan_id=plan_id, module_id=payload.module_id
    ).first()
    if existing:
        return _model_to_dict(existing)
    row = PlatformPlanModule(plan_id=plan_id, module_id=payload.module_id)
    db.add(row); db.commit(); db.refresh(row)
    _audit(db, actor_staff_id=staff.id, client_id=None, entity="B2B-PLAN",
           action="UPDATE", entity_id=plan_id,
           after={"added_module_id": payload.module_id})
    return _model_to_dict(row)


@router.delete("/plans/{plan_id}/modules/{module_id}")
def detach_plan_module(
    plan_id: int, module_id: int,
    db: Session = Depends(get_db),
    staff: StaffEmployee = Depends(require_b2b_super_admin),
):
    row = db.query(PlatformPlanModule).filter_by(
        plan_id=plan_id, module_id=module_id
    ).first()
    if not row:
        raise HTTPException(404, "plan-module link not found")
    before = _model_to_dict(row)
    db.delete(row); db.commit()
    _audit(db, actor_staff_id=staff.id, client_id=None, entity="B2B-PLAN",
           action="UPDATE", entity_id=plan_id, before=before)
    return {"ok": True}


# ─────────────────────────────────────────────────────────────────────────────
# SUBSCRIPTIONS — detail + update + module attach/detach
# ─────────────────────────────────────────────────────────────────────────────
class SubModuleIn(BaseModel):
    module_id: int
    enabled: bool = True


@router.get("/subscriptions/{sub_id}")
def get_subscription(
    sub_id: int,
    db: Session = Depends(get_db),
    _staff: StaffEmployee = Depends(require_b2b_super_admin),
):
    row = db.query(PlatformSubscription).filter_by(id=sub_id).first()
    if not row:
        raise HTTPException(404, "subscription not found")
    d = _model_to_dict(row)
    d["modules"] = [
        _model_to_dict(m) for m in
        db.query(PlatformSubscriptionModule).filter_by(subscription_id=sub_id).all()
    ]
    return d


@router.patch("/subscriptions/{sub_id}")
def update_subscription(
    sub_id: int,
    payload: Dict[str, Any] = Body(...),
    db: Session = Depends(get_db),
    staff: StaffEmployee = Depends(require_b2b_super_admin),
):
    row = db.query(PlatformSubscription).filter_by(id=sub_id).first()
    if not row:
        raise HTTPException(404, "subscription not found")
    before = _model_to_dict(row)
    allowed = {"plan_id", "display_plan_name", "billing_currency", "billing_cycle",
               "annual_free_months", "is_trial", "status",
               "starts_on", "ends_on", "trial_ends_on",
               "seat_count"}  # Phase 3a.2
    for k, v in payload.items():
        if k in allowed:
            if k == "seat_count":
                try:
                    v = int(v)
                except (TypeError, ValueError):
                    raise HTTPException(400, "seat_count must be an integer")
                if v < 1:
                    raise HTTPException(400, "seat_count must be >= 1")
            setattr(row, k, v)
    row.updated_at = get_indian_time()
    db.commit(); db.refresh(row)
    _audit(db, actor_staff_id=staff.id, client_id=row.client_id, entity="B2B-SUB",
           action="UPDATE", entity_id=row.id, before=before, after=_model_to_dict(row))
    return _model_to_dict(row)


@router.post("/subscriptions/{sub_id}/modules")
def attach_subscription_module(
    sub_id: int,
    payload: SubModuleIn,
    db: Session = Depends(get_db),
    staff: StaffEmployee = Depends(require_b2b_super_admin),
):
    sub = db.query(PlatformSubscription).filter_by(id=sub_id).first()
    if not sub:
        raise HTTPException(404, "subscription not found")
    if not db.query(PlatformModule).filter_by(id=payload.module_id).first():
        raise HTTPException(404, "module not found")
    existing = db.query(PlatformSubscriptionModule).filter_by(
        subscription_id=sub_id, module_id=payload.module_id
    ).first()
    if existing:
        existing.enabled = payload.enabled
        existing.updated_at = get_indian_time()
        db.commit(); db.refresh(existing)
        return _model_to_dict(existing)
    row = PlatformSubscriptionModule(
        subscription_id=sub_id, module_id=payload.module_id, enabled=payload.enabled,
    )
    db.add(row); db.commit(); db.refresh(row)
    _audit(db, actor_staff_id=staff.id, client_id=sub.client_id, entity="B2B-SUB",
           action="UPDATE", entity_id=sub_id,
           after={"added_module_id": payload.module_id, "enabled": payload.enabled})
    return _model_to_dict(row)


@router.delete("/subscriptions/{sub_id}/modules/{module_id}")
def detach_subscription_module(
    sub_id: int, module_id: int,
    db: Session = Depends(get_db),
    staff: StaffEmployee = Depends(require_b2b_super_admin),
):
    sub = db.query(PlatformSubscription).filter_by(id=sub_id).first()
    if not sub:
        raise HTTPException(404, "subscription not found")
    row = db.query(PlatformSubscriptionModule).filter_by(
        subscription_id=sub_id, module_id=module_id
    ).first()
    if not row:
        raise HTTPException(404, "subscription-module link not found")
    before = _model_to_dict(row)
    db.delete(row); db.commit()
    _audit(db, actor_staff_id=staff.id, client_id=sub.client_id, entity="B2B-SUB",
           action="UPDATE", entity_id=sub_id, before=before)
    return {"ok": True}


# ─────────────────────────────────────────────────────────────────────────────
# PRICING OVERRIDES — upsert / delete
# ─────────────────────────────────────────────────────────────────────────────
class PricingOverrideIn(BaseModel):
    client_id: int
    module_id: int
    price_inr: Optional[float] = None
    price_usd: Optional[float] = None
    pricing_unit: Optional[str] = None
    notes: Optional[str] = None


@router.put("/pricing-overrides")
def upsert_pricing_override(
    payload: PricingOverrideIn,
    db: Session = Depends(get_db),
    staff: StaffEmployee = Depends(require_b2b_super_admin),
):
    if not db.query(PlatformClient).filter_by(id=payload.client_id).first():
        raise HTTPException(404, "client not found")
    if not db.query(PlatformModule).filter_by(id=payload.module_id).first():
        raise HTTPException(404, "module not found")
    row = db.query(PlatformClientModulePricingOverride).filter_by(
        client_id=payload.client_id, module_id=payload.module_id
    ).first()
    before = _model_to_dict(row) if row else None
    if row:
        row.price_inr = payload.price_inr
        row.price_usd = payload.price_usd
        row.pricing_unit = payload.pricing_unit
        row.notes = payload.notes
        row.updated_at = get_indian_time()
    else:
        row = PlatformClientModulePricingOverride(**payload.model_dump())
        db.add(row)
    db.commit(); db.refresh(row)
    _audit(db, actor_staff_id=staff.id, client_id=payload.client_id, entity="B2B-PRICE",
           action="UPDATE" if before else "CREATE",
           entity_id=row.id, before=before, after=_model_to_dict(row))
    return _model_to_dict(row)


@router.delete("/pricing-overrides/{override_id}")
def delete_pricing_override(
    override_id: int,
    db: Session = Depends(get_db),
    staff: StaffEmployee = Depends(require_b2b_super_admin),
):
    row = db.query(PlatformClientModulePricingOverride).filter_by(id=override_id).first()
    if not row:
        raise HTTPException(404, "override not found")
    before = _model_to_dict(row)
    cid = row.client_id
    db.delete(row); db.commit()
    _audit(db, actor_staff_id=staff.id, client_id=cid, entity="B2B-PRICE",
           action="DELETE", entity_id=override_id, before=before)
    return {"ok": True}


# ─────────────────────────────────────────────────────────────────────────────
# EFFECTIVE PRICING — compute per-client final pricing (global ⊕ override)
# ─────────────────────────────────────────────────────────────────────────────
@router.get("/clients/{client_id}/effective-pricing")
def client_effective_pricing(
    client_id: int,
    db: Session = Depends(get_db),
    _staff: StaffEmployee = Depends(require_b2b_super_admin),
):
    """
    Computes effective per-module pricing for a client by joining global pricing
    with any per-client override. Restricted to modules currently entitled via
    the client's active subscription(s).
    """
    client = db.query(PlatformClient).filter_by(id=client_id).first()
    if not client:
        raise HTTPException(404, "client not found")

    rows = db.execute(text("""
        SELECT
            pm.id AS module_id, pm.module_code, pm.module_name,
            COALESCE(ovr.price_inr,    pmp.price_inr,    0) AS effective_price_inr,
            COALESCE(ovr.price_usd,    pmp.price_usd,    0) AS effective_price_usd,
            COALESCE(ovr.pricing_unit, pmp.pricing_unit, 'per_company') AS effective_unit,
            pmp.price_inr     AS global_price_inr,
            pmp.price_usd     AS global_price_usd,
            ovr.price_inr     AS override_price_inr,
            ovr.price_usd     AS override_price_usd,
            (ovr.id IS NOT NULL) AS has_override,
            psm.enabled       AS module_enabled,
            ps.id             AS subscription_id
          FROM platform_subscription_modules psm
          JOIN platform_subscriptions ps ON ps.id = psm.subscription_id
          JOIN platform_modules pm       ON pm.id = psm.module_id
     LEFT JOIN platform_module_pricing pmp                ON pmp.module_id = pm.id
     LEFT JOIN platform_client_module_pricing_override ovr
                ON ovr.client_id = ps.client_id AND ovr.module_id = pm.id
         WHERE ps.client_id = :cid
           AND ps.status IN ('active','trial')
         ORDER BY pm.module_code ASC
    """), {"cid": client_id}).mappings().all()

    cur = (client.billing_currency or "INR").upper()
    items: List[Dict[str, Any]] = []
    total = 0.0
    for r in rows:
        eff = float(r["effective_price_inr"] if cur == "INR" else r["effective_price_usd"]) or 0.0
        items.append({
            "module_id":          r["module_id"],
            "module_code":        r["module_code"],
            "module_name":        r["module_name"],
            "effective_price":    eff,
            "currency":           cur,
            "pricing_unit":       r["effective_unit"],
            "has_override":       bool(r["has_override"]),
            "global_price_inr":   float(r["global_price_inr"] or 0),
            "global_price_usd":   float(r["global_price_usd"] or 0),
            "override_price_inr": (float(r["override_price_inr"]) if r["override_price_inr"] is not None else None),
            "override_price_usd": (float(r["override_price_usd"]) if r["override_price_usd"] is not None else None),
            "module_enabled":     bool(r["module_enabled"]),
            "subscription_id":    r["subscription_id"],
        })
        if r["module_enabled"]:
            total += eff
    return {
        "client_id":     client_id,
        "currency":      cur,
        "module_count":  len(items),
        "subtotal":      total,
        "items":         items,
    }


# =============================================================================
# Task #41 — Phase 3 (Enforcement, Sidebar Filter, B2B_ENFORCE)
# =============================================================================

@router.get("/my-menu")
def my_filtered_menu(
    db: Session = Depends(get_db),
    staff: StaffEmployee = Depends(get_current_staff_user),
):
    """
    Returns the staff sidebar entries the *current user* is entitled to see.
    When B2B_ENFORCE=false (default) every visible-flagged menu row is returned
    untouched. When B2B_ENFORCE=true the rows are filtered by entitlement.
    """
    cid = resolve_client_id_for_staff(db, staff)
    rows = db.execute(text("""
        SELECT menu_code, menu_name, route_path, sidebar_section,
               sidebar_section_title, display_order, parent_section,
               is_submenu, audience_scope
          FROM staff_menu_registry
         WHERE COALESCE(is_active, TRUE) = TRUE
         ORDER BY COALESCE(sidebar_section_order, 999), COALESCE(display_order, 999), id
    """)).mappings().all()
    items = [dict(r) for r in rows]
    filtered = filter_menu_by_entitlement(items, db, cid, user_id=staff.id)
    return {
        "client_id":     cid,
        "enforcing":     enforce_enabled(),
        "total_visible": len(items),
        "after_filter":  len(filtered),
        "items":         filtered,
    }


@router.get("/clients/{client_id}/preview-enforcement")
def preview_client_enforcement(
    client_id: int,
    db: Session = Depends(get_db),
    _staff: StaffEmployee = Depends(require_b2b_super_admin),
):
    """Preview what would change for a client if B2B_ENFORCE flipped to true."""
    if not db.query(PlatformClient).filter_by(id=client_id).first():
        raise HTTPException(404, "client not found")
    return preview_entitlement(db, client_id)


class CheckEntitlementIn(BaseModel):
    module_code: str
    client_id: Optional[int] = None


@router.post("/check-entitlement")
def check_entitlement(
    payload: CheckEntitlementIn,
    db: Session = Depends(get_db),
    staff: StaffEmployee = Depends(get_current_staff_user),
):
    """Decision for current staff (or given client, super-admin only)."""
    if payload.client_id is not None:
        require_b2b_super_admin(staff)  # raises if caller isn't super-admin
        cid = payload.client_id
    else:
        cid = resolve_client_id_for_staff(db, staff)
    allowed = is_module_entitled(
        db, cid, payload.module_code,
        user_id=staff.id, user_type="staff", route="/check-entitlement",
    )
    return {"client_id": cid, "module_code": payload.module_code,
            "allowed": allowed, "enforcing": enforce_enabled()}


# =============================================================================
# Task #42 — Phase 4 (Billing & Invoicing) endpoints
# =============================================================================
from datetime import date as _date
from app.models.platform_b2b_billing import (
    PlatformInvoice, PlatformInvoiceLine, PlatformPayment,
)
from app.services.platform_b2b_billing import (
    generate_invoice_for_subscription, apply_payment, run_dunning,
)


class GenerateInvoiceIn(BaseModel):
    subscription_id: int
    period_start: Optional[_date] = None
    period_end:   Optional[_date] = None
    due_in_days:  int = 14


class PaymentIn(BaseModel):
    invoice_id:  Optional[int] = None
    client_id:   Optional[int] = None
    amount:      float
    currency:    str = "INR"
    method:      Optional[str] = None
    reference:   Optional[str] = None
    received_on: Optional[_date] = None
    notes:       Optional[str] = None


class DunningIn(BaseModel):
    grace_days: int = 10
    dry_run:    bool = False


@router.get("/invoices")
def list_invoices(
    db: Session = Depends(get_db),
    _staff: StaffEmployee = Depends(require_b2b_super_admin),
    client_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(200, le=1000),
):
    q = db.query(PlatformInvoice)
    if client_id is not None:
        q = q.filter(PlatformInvoice.client_id == client_id)
    if status:
        q = q.filter(PlatformInvoice.status == status)
    rows = q.order_by(PlatformInvoice.id.desc()).limit(limit).all()
    return {"invoices": [_model_to_dict(r) for r in rows]}


@router.get("/invoices/{invoice_id}")
def get_invoice(
    invoice_id: int,
    db: Session = Depends(get_db),
    _staff: StaffEmployee = Depends(require_b2b_super_admin),
):
    inv = db.query(PlatformInvoice).filter_by(id=invoice_id).first()
    if not inv:
        raise HTTPException(404, "invoice not found")
    out = _model_to_dict(inv)
    out["lines"] = [
        _model_to_dict(l)
        for l in db.query(PlatformInvoiceLine).filter_by(invoice_id=invoice_id).all()
    ]
    out["payments"] = [
        _model_to_dict(p)
        for p in db.query(PlatformPayment).filter_by(invoice_id=invoice_id).all()
    ]
    return out


@router.post("/invoices/generate")
def generate_invoice(
    payload: GenerateInvoiceIn,
    db: Session = Depends(get_db),
    staff: StaffEmployee = Depends(require_b2b_super_admin),
):
    try:
        result = generate_invoice_for_subscription(
            db, payload.subscription_id,
            period_start=payload.period_start, period_end=payload.period_end,
            due_in_days=payload.due_in_days, actor_staff_id=staff.id,
        )
    except ValueError as e:
        raise HTTPException(400, str(e))
    _audit(db, actor_staff_id=staff.id, client_id=result["client_id"], entity="B2B-INV",
           action="CREATE", entity_id=result["id"], after=result)
    return result


@router.delete("/invoices/{invoice_id}")
def void_invoice(
    invoice_id: int,
    db: Session = Depends(get_db),
    staff: StaffEmployee = Depends(require_b2b_super_admin),
):
    inv = db.query(PlatformInvoice).filter_by(id=invoice_id).first()
    if not inv:
        raise HTTPException(404, "invoice not found")
    if inv.status == "paid":
        raise HTTPException(400, "paid invoices cannot be voided; record a refund instead")
    before = _model_to_dict(inv)
    inv.status = "void"
    inv.updated_at = get_indian_time()
    db.commit()
    _audit(db, actor_staff_id=staff.id, client_id=inv.client_id, entity="B2B-INV",
           action="UPDATE", entity_id=inv.id, before=before, after=_model_to_dict(inv))
    return {"ok": True, "id": invoice_id, "status": "void"}


@router.get("/payments")
def list_payments(
    db: Session = Depends(get_db),
    _staff: StaffEmployee = Depends(require_b2b_super_admin),
    client_id: Optional[int] = Query(None),
    invoice_id: Optional[int] = Query(None),
    limit: int = Query(200, le=1000),
):
    q = db.query(PlatformPayment)
    if client_id is not None:
        q = q.filter(PlatformPayment.client_id == client_id)
    if invoice_id is not None:
        q = q.filter(PlatformPayment.invoice_id == invoice_id)
    rows = q.order_by(PlatformPayment.id.desc()).limit(limit).all()
    return {"payments": [_model_to_dict(r) for r in rows]}


@router.post("/payments")
def record_payment(
    payload: PaymentIn,
    db: Session = Depends(get_db),
    staff: StaffEmployee = Depends(require_b2b_super_admin),
):
    try:
        result = apply_payment(
            db, invoice_id=payload.invoice_id, client_id=payload.client_id,
            amount=payload.amount, currency=payload.currency,
            method=payload.method, reference=payload.reference,
            received_on=payload.received_on, notes=payload.notes,
            recorded_by=staff.id,
        )
    except ValueError as e:
        raise HTTPException(400, str(e))
    _audit(db, actor_staff_id=staff.id, client_id=result["client_id"], entity="B2B-PAY",
           action="CREATE", entity_id=result["id"], after=result)
    return result


@router.post("/dunning/run")
def dunning_run(
    payload: DunningIn,
    db: Session = Depends(get_db),
    staff: StaffEmployee = Depends(require_b2b_super_admin),
):
    result = run_dunning(db, grace_days=payload.grace_days, dry_run=payload.dry_run)
    _audit(db, actor_staff_id=staff.id, client_id=None, entity="B2B-DUN",
           action="RUN", entity_id=None, after=result)
    return result


@router.get("/billing/summary")
def billing_summary(
    db: Session = Depends(get_db),
    _staff: StaffEmployee = Depends(require_b2b_super_admin),
):
    """Aggregate counts/totals for the billing dashboard."""
    by_status = db.execute(text("""
        SELECT status, COUNT(*) AS n, COALESCE(SUM(total),0) AS total,
               COALESCE(SUM(amount_paid),0) AS paid
          FROM platform_invoices GROUP BY status
    """)).mappings().all()
    overdue = db.execute(text("""
        SELECT COUNT(*) AS n FROM platform_invoices
         WHERE status IN ('open','partial','overdue') AND due_date < CURRENT_DATE
    """)).scalar()
    pay_total = db.execute(text("SELECT COALESCE(SUM(amount),0) FROM platform_payments")).scalar()
    return {
        "by_status": [dict(r) for r in by_status],
        "overdue_count": int(overdue or 0),
        "lifetime_payments": float(pay_total or 0),
    }


# =============================================================================
# Task #43 — Phase 5 (Self-Service Sign-up + Tenant Portal)
# =============================================================================
import re as _re
import secrets as _secrets


class TenantSignupIn(BaseModel):
    company_name:  str = Field(..., min_length=2, max_length=120)
    contact_name:  str = Field(..., min_length=1, max_length=120)
    contact_email: str = Field(..., min_length=4, max_length=180)
    contact_phone: Optional[str] = None
    billing_currency: str = "INR"
    trial_days:    int = 14
    notes:         Optional[str] = None


def _slugify_code(s: str) -> str:
    s = _re.sub(r"[^A-Za-z0-9]+", "-", s).strip("-").upper()
    return (s or "TENANT")[:24]


@router.post("/signup", status_code=201)
def tenant_signup(payload: TenantSignupIn, db: Session = Depends(get_db)):
    """
    Public self-service sign-up. Creates a `platform_clients` row in 'trial'
    status plus a 'trial' subscription with NO modules attached. A super-admin
    must subsequently attach modules / pick a plan.

    Anti-abuse: minimal — uses email+company_name uniqueness. Production
    deployment should add CAPTCHA/rate-limit; that is documented as Phase 5b.
    """
    if not _re.match(r"[^@\s]+@[^@\s]+\.[^@\s]+", payload.contact_email):
        raise HTTPException(400, "invalid contact_email")
    if payload.billing_currency.upper() not in ("INR", "USD"):
        raise HTTPException(400, "billing_currency must be INR or USD")
    trial_days = max(1, min(int(payload.trial_days or 14), 90))

    # de-dup on (company_name, contact_email) — return existing if present
    existing = db.execute(text("""
        SELECT id FROM platform_clients
         WHERE LOWER(client_name) = LOWER(:n) AND LOWER(contact_email) = LOWER(:e)
         LIMIT 1
    """), {"n": payload.company_name, "e": payload.contact_email}).first()
    if existing:
        cid = int(existing[0])
        return {"ok": True, "client_id": cid, "status": "already-exists"}

    # Pick a unique client_code
    base_code = _slugify_code(payload.company_name)
    code = base_code
    for _ in range(8):
        clash = db.execute(text("SELECT 1 FROM platform_clients WHERE client_code=:c"),
                           {"c": code}).first()
        if not clash: break
        code = f"{base_code}-{_secrets.token_hex(2).upper()}"

    client = PlatformClient(
        client_code=code,
        client_name=payload.company_name,
        contact_name=payload.contact_name,
        contact_email=payload.contact_email,
        contact_phone=payload.contact_phone,
        billing_currency=payload.billing_currency.upper(),
        status="trial",
        is_internal=False,
        notes=payload.notes,
    )
    db.add(client); db.commit(); db.refresh(client)

    today = date.today()
    sub = PlatformSubscription(
        client_id=client.id,
        billing_currency=client.billing_currency,
        billing_cycle="monthly",
        status="trial",
        is_trial=True,
        starts_on=today,
        trial_ends_on=today + __import__("datetime").timedelta(days=trial_days),
    )
    db.add(sub); db.commit(); db.refresh(sub)

    _audit(db, actor_staff_id=None, client_id=client.id, entity="B2B-SIGNUP",
           action="CREATE", entity_id=client.id,
           after={"client_code": code, "trial_days": trial_days})

    return {
        "ok": True, "client_id": client.id, "client_code": client.client_code,
        "subscription_id": sub.id, "trial_ends_on": sub.trial_ends_on.isoformat(),
        "status": "created",
        "next_steps": [
            "A super-admin must attach modules to your subscription before access is granted.",
            "Use /staff/my-tenant after login to view your tenant status.",
        ],
    }


@router.get("/me/tenant")
def my_tenant_self(
    db: Session = Depends(get_db),
    staff: StaffEmployee = Depends(get_current_staff_user),
):
    """
    Returns the *current user's* tenant: client + active subscription(s) +
    invoice/payment summary + entitled-module count. Tenant-scoped; does NOT
    expose other tenants' data.
    """
    cid = resolve_client_id_for_staff(db, staff)
    if cid is None:
        raise HTTPException(404, "no tenant resolved for this user")
    client = db.query(PlatformClient).filter_by(id=cid).first()
    if not client:
        raise HTTPException(404, "tenant not found")
    subs = db.query(PlatformSubscription).filter_by(client_id=cid).all()
    invs = db.execute(text("""
        SELECT status, COUNT(*) AS n, COALESCE(SUM(total),0) AS total,
               COALESCE(SUM(amount_paid),0) AS paid
          FROM platform_invoices WHERE client_id=:c GROUP BY status
    """), {"c": cid}).mappings().all()
    entitled = db.execute(text("""
        SELECT COUNT(*) FROM platform_subscription_modules psm
          JOIN platform_subscriptions ps ON ps.id = psm.subscription_id
         WHERE ps.client_id = :c AND ps.status IN ('trial','active')
           AND psm.enabled = TRUE
    """), {"c": cid}).scalar()
    return {
        "client": _model_to_dict(client),
        "subscriptions": [_model_to_dict(s) for s in subs],
        "invoice_summary": [dict(r) for r in invs],
        "entitled_module_count": int(entitled or 0),
        "enforcing": enforce_enabled(),
    }
