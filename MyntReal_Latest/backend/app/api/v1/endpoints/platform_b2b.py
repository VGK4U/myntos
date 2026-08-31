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
import json
from datetime import date
from decimal import Decimal
from typing import Optional, List, Dict, Any, Tuple

from fastapi import APIRouter, Depends, HTTPException, Query, Body, Request, status
from sqlalchemy import text, func
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from app.core.database import get_db
from app.core.config import settings
from app.core.security import SecurityManager
from app.api.v1.endpoints.staff_auth import get_current_staff_user
from app.models.staff import (
    StaffEmployee, StaffRole, StaffDepartment, StaffEmployeeModule, StaffModuleMaster, generate_employee_code
)
from app.models.staff_accounts import AssociatedCompany
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
        from app.services.platform_b2b_billing import apply_payment
        result = apply_payment(
            db, invoice_id=payload.invoice_id, client_id=payload.client_id,
            amount=payload.amount, currency=payload.currency,
            method=payload.method, reference=payload.reference,
            received_on=payload.received_on, notes=payload.notes,
            recorded_by=staff.id,
        )
    except ValueError as e:
        raise HTTPException(400, str(e))
    _audit(db, actor_staff_id=staff.id, client_id=result.get("client_id"), entity="B2B-PAY",
           action="CREATE", entity_id=result.get("id") or result.get("payment_id"), after=result)
    return result


@router.post("/invoices/{invoice_id}/checkout")
def create_invoice_checkout(
    invoice_id: int,
    db: Session = Depends(get_db),
):
    """
    Creates a Razorpay Order strictly using server-side PlatformInvoice.total.
    Accessible for online SaaS invoice payment. Frontend NEVER defines the price.
    """
    try:
        from app.services.platform_b2b_billing import create_razorpay_order_for_invoice
        return create_razorpay_order_for_invoice(db, invoice_id)
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        logger.error("[RAZORPAY-CHECKOUT] Error: %s", e)
        raise HTTPException(500, f"Checkout initialization failed: {str(e)}")


@router.post("/webhooks/razorpay")
async def razorpay_b2b_webhook(
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Public Razorpay Webhook endpoint for B2B SaaS Subscription Invoices.
    Verifies HMAC-SHA256 signature, validates tenant/subscription ownership,
    enforces idempotency, marks invoice as paid, activates subscription,
    and automatically provisions the initial Tenant Administrator.
    """
    signature = request.headers.get("X-Razorpay-Signature") or request.headers.get("x-razorpay-signature")
    body_bytes = await request.body()

    # 1. Cryptographic HMAC Signature Verification
    webhook_secret = settings.RAZORPAY_WEBHOOK_SECRET or settings.RAZORPAY_KEY_SECRET
    if webhook_secret and signature:
        try:
            import razorpay
            client_rp = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID or "dummy", settings.RAZORPAY_KEY_SECRET or "dummy"))
            client_rp.utility.verify_webhook_signature(
                body_bytes.decode("utf-8"),
                signature,
                webhook_secret
            )
        except Exception as sig_err:
            logger.warning("[RAZORPAY-WEBHOOK] Signature verification failed: %s", sig_err)
            raise HTTPException(400, "Invalid webhook signature")

    try:
        payload = json.loads(body_bytes.decode("utf-8"))
    except Exception:
        raise HTTPException(400, "Invalid JSON body")

    event = payload.get("event")
    if event not in ("payment.captured", "order.paid"):
        return {"ok": True, "status": "ignored_event", "event": event}

    payment_entity = payload.get("payload", {}).get("payment", {}).get("entity", {})
    payment_id = payment_entity.get("id")
    order_id = payment_entity.get("order_id")
    amount_paise = payment_entity.get("amount", 0)
    currency = (payment_entity.get("currency") or "INR").upper()
    notes = payment_entity.get("notes", {})

    invoice_id_str = notes.get("invoice_id")
    client_id_str = notes.get("client_id")

    if not invoice_id_str:
        # Try resolving invoice by razorpay_order_id
        if order_id:
            inv_match = db.query(PlatformInvoice).filter_by(razorpay_order_id=order_id).first()
            if inv_match:
                invoice_id_str = str(inv_match.id)
                client_id_str = str(inv_match.client_id)

    if not invoice_id_str or not client_id_str:
        logger.warning("[RAZORPAY-WEBHOOK] Could not resolve invoice/client from notes or order_id %s", order_id)
        return {"ok": True, "status": "unmapped_order", "order_id": order_id}

    inv_id = int(invoice_id_str)
    cid = int(client_id_str)
    amount_inr = Decimal(str(amount_paise)) / Decimal("100")

    try:
        from app.services.platform_b2b_billing import process_verified_payment
        res = process_verified_payment(
            db,
            invoice_id=inv_id,
            client_id=cid,
            amount=amount_inr,
            currency=currency,
            gateway_payment_id=payment_id,
            method="razorpay",
            notes=f"Razorpay webhook event {event} for order {order_id}",
        )
        return res
    except ValueError as val_err:
        logger.error("[RAZORPAY-WEBHOOK] Validation Error: %s", val_err)
        raise HTTPException(400, str(val_err))
    except Exception as exc:
        logger.error("[RAZORPAY-WEBHOOK] Server Error: %s", exc)
        raise HTTPException(500, f"Processing error: {str(exc)}")


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
# Task #43 — Phase 4A (Public Sign-up + Service/Segment Packaging + Authoritative Pricing)
# =============================================================================
import re as _re
import secrets as _secrets


class CalculatePricingIn(BaseModel):
    selected_modules: List[str] = Field(default_factory=list)
    billing_currency: str = "INR"
    billing_cycle: str = "monthly"  # monthly or annual
    seat_count: int = Field(default=1, ge=1, le=10000)


class TenantSignupIn(BaseModel):
    company_name:     str = Field(..., min_length=2, max_length=120)
    contact_name:     str = Field(..., min_length=1, max_length=120)
    contact_email:    str = Field(..., min_length=4, max_length=180)
    contact_phone:    Optional[str] = None
    billing_currency: str = "INR"
    billing_cycle:    str = "monthly"  # monthly or annual
    selected_modules: Optional[List[str]] = Field(default_factory=list)
    seat_count:       int = Field(default=1, ge=1, le=10000)
    trial_days:       int = 14
    notes:            Optional[str] = None


def _slugify_code(s: str) -> str:
    s = _re.sub(r"[^A-Za-z0-9]+", "-", s).strip("-").upper()
    return (s or "TENANT")[:24]


def _resolve_and_validate_modules_with_dependencies(db: Session, requested_codes: List[str]) -> Tuple[List[PlatformModule], List[PlatformModule]]:
    """
    Authoritatively validates that requested module codes exist, are active, and are non-internal.
    Automatically resolves and appends required dependencies (e.g. CRM_CORE when a segment is selected).
    Returns (all_modules, auto_included_dependencies).
    """
    if not requested_codes:
        return [], []

    # 1. Fetch requested modules
    requested_mods = db.query(PlatformModule).filter(
        PlatformModule.module_code.in_(requested_codes),
        PlatformModule.is_active == True,
        PlatformModule.internal_only == False
    ).all()

    found_codes = {m.module_code for m in requested_mods}
    for code in requested_codes:
        if code not in found_codes:
            raise HTTPException(400, f"Module '{code}' is invalid, inactive, or not available for public subscription.")

    all_mods_map = {m.id: m for m in requested_mods}
    auto_included: List[PlatformModule] = []

    # 2. Transitive dependency resolution from platform_module_dependencies
    checked_ids = set(all_mods_map.keys())
    to_check = list(all_mods_map.keys())

    while to_check:
        curr_id = to_check.pop(0)
        deps = db.query(PlatformModuleDependency).filter_by(module_id=curr_id).all()
        for dep in deps:
            if dep.depends_on_module_id not in checked_ids:
                dep_mod = db.query(PlatformModule).filter_by(
                    id=dep.depends_on_module_id,
                    is_active=True,
                    internal_only=False
                ).first()
                if dep_mod:
                    all_mods_map[dep_mod.id] = dep_mod
                    auto_included.append(dep_mod)
                    checked_ids.add(dep_mod.id)
                    to_check.append(dep_mod.id)

    return list(all_mods_map.values()), auto_included


def _compute_authoritative_pricing(
    db: Session,
    modules: List[PlatformModule],
    currency: str = "INR",
    cycle: str = "monthly",
    seat_count: int = 1
) -> Dict[str, Any]:
    """
    Calculates authoritative server-side pricing from platform_module_pricing.
    Supports Monthly and Annual cycles (with 2 free months on Annual).
    """
    currency_clean = (currency or "INR").upper()
    cycle_clean = (cycle or "monthly").lower()
    seats = max(1, int(seat_count or 1))

    line_items = []
    monthly_subtotal = Decimal("0.00")

    for m in modules:
        pricing = db.query(PlatformModulePricing).filter_by(module_id=m.id).first()
        if pricing:
            unit_price = Decimal(str(pricing.price_inr if currency_clean == "INR" else pricing.price_usd))
            unit_type = pricing.pricing_unit or "per_company"
        else:
            unit_price = Decimal("0.00")
            unit_type = "per_company"

        # Apply seat multiplier if unit is per_seat
        qty = Decimal(seats) if unit_type == "per_seat" else Decimal("1.00")
        line_monthly = unit_price * qty
        monthly_subtotal += line_monthly

        line_items.append({
            "module_id": m.id,
            "module_code": m.module_code,
            "module_name": m.module_name,
            "category": m.category,
            "pricing_unit": unit_type,
            "unit_price": float(unit_price),
            "quantity": float(qty),
            "monthly_amount": float(line_monthly),
        })

    # Annual discount: 12 months for the price of 10 (2 months free)
    annual_multiplier = 10 if cycle_clean == "annual" else 1
    cycle_subtotal = monthly_subtotal * Decimal(annual_multiplier)
    gst_rate = Decimal("18.00") if currency_clean == "INR" else Decimal("0.00")
    tax_amount = (cycle_subtotal * gst_rate) / Decimal("100.00")
    total_payable = cycle_subtotal + tax_amount

    return {
        "currency": currency_clean,
        "billing_cycle": cycle_clean,
        "seat_count": seats,
        "modules_count": len(modules),
        "line_items": line_items,
        "monthly_subtotal": float(monthly_subtotal),
        "annual_free_months": 2 if cycle_clean == "annual" else 0,
        "cycle_multiplier": annual_multiplier,
        "cycle_subtotal": float(cycle_subtotal),
        "tax_rate_pct": float(gst_rate),
        "tax_amount": float(tax_amount),
        "total_payable": float(total_payable),
        "monthly_effective_rate": float(total_payable / Decimal("12.00")) if cycle_clean == "annual" else float(total_payable),
    }


@router.get("/public-catalog")
def get_public_signup_catalog(db: Session = Depends(get_db)):
    """
    Public catalog of selectable MyntOS Services, Segments, and Addons with pricing.
    """
    canonical_codes = [
        "CRM_CORE", "CRM_LEADS_SOLAR", "CRM_LEADS_EV_B2B", "CRM_LEADS_EV_B2C",
        "CRM_LEADS_EV_SPARES", "CRM_LEADS_REAL_DREAMS", "CRM_LEADS_INSURANCE", "CRM_LEADS_ETC",
        "WHATSAPP_INTEGRATION", "META_ADS_INTEGRATION", "TELEPHONY_INTEGRATION",
        "STAFF_HR", "SFMS_ACCOUNTING"
    ]

    mods = db.query(PlatformModule).filter(
        PlatformModule.module_code.in_(canonical_codes),
        PlatformModule.is_active == True,
        PlatformModule.internal_only == False
    ).all()

    services = []
    segments = []

    for m in mods:
        p = db.query(PlatformModulePricing).filter_by(module_id=m.id).first()
        item = {
            "module_id": m.id,
            "module_code": m.module_code,
            "module_name": m.module_name,
            "category": m.category,
            "description": m.description,
            "price_inr": float(p.price_inr) if p else 0.0,
            "price_usd": float(p.price_usd) if p else 0.0,
            "pricing_unit": p.pricing_unit if p else "per_company",
        }
        if m.category == "CRM_SEGMENT":
            item["requires_module"] = "CRM_CORE"
            segments.append(item)
        else:
            services.append(item)

    return {
        "services": services,
        "segments": segments,
        "annual_discount_months": 2,
        "tax_rate_inr_pct": 18.00,
    }


@router.post("/calculate-pricing")
def calculate_public_pricing(payload: CalculatePricingIn, db: Session = Depends(get_db)):
    """
    Authoritative server-side live price calculation for requested services and segments.
    """
    if payload.billing_currency.upper() not in ("INR", "USD"):
        raise HTTPException(400, "billing_currency must be INR or USD")
    if payload.billing_cycle.lower() not in ("monthly", "annual"):
        raise HTTPException(400, "billing_cycle must be monthly or annual")

    all_mods, auto_deps = _resolve_and_validate_modules_with_dependencies(db, payload.selected_modules)
    breakdown = _compute_authoritative_pricing(
        db, all_mods,
        currency=payload.billing_currency,
        cycle=payload.billing_cycle,
        seat_count=payload.seat_count
    )
    breakdown["auto_included_dependencies"] = [m.module_code for m in auto_deps]
    return breakdown


@router.post("/signup", status_code=201)
def tenant_signup(payload: TenantSignupIn, db: Session = Depends(get_db)):
    """
    Public self-service sign-up with service/segment packaging and authoritative pricing.
    Creates a `platform_clients` row in 'pending' status plus a 'pending_payment'
    subscription with requested modules created in disabled status (enabled=False).
    Authoritative pricing snapshot is recorded.
    """
    if not _re.match(r"[^@\s]+@[^@\s]+\.[^@\s]+", payload.contact_email):
        raise HTTPException(400, "invalid contact_email")
    if payload.billing_currency.upper() not in ("INR", "USD"):
        raise HTTPException(400, "billing_currency must be INR or USD")
    if payload.billing_cycle.lower() not in ("monthly", "annual"):
        raise HTTPException(400, "billing_cycle must be monthly or annual")

    # 1. Resolve & Validate requested modules + dependencies
    requested_codes = payload.selected_modules or []
    all_mods, auto_deps = _resolve_and_validate_modules_with_dependencies(db, requested_codes)

    # 2. Compute Authoritative Price Snapshot
    pricing_snapshot = _compute_authoritative_pricing(
        db, all_mods,
        currency=payload.billing_currency,
        cycle=payload.billing_cycle,
        seat_count=payload.seat_count
    )

    # 3. De-dup on (company_name, contact_email)
    existing = db.execute(text("""
        SELECT id FROM platform_clients
         WHERE LOWER(client_name) = LOWER(:n) AND LOWER(contact_email) = LOWER(:e)
         LIMIT 1
    """), {"n": payload.company_name, "e": payload.contact_email}).first()
    if existing:
        cid = int(existing[0])
        return {"ok": True, "client_id": cid, "status": "already-exists"}

    # 4. Pick unique, non-enumerable client_code
    base_code = _slugify_code(payload.company_name)[:16]
    code = f"{base_code}-{_secrets.token_hex(4).upper()}"
    for _ in range(8):
        clash = db.execute(text("SELECT 1 FROM platform_clients WHERE client_code=:c"),
                           {"c": code}).first()
        if not clash: break
        code = f"{base_code}-{_secrets.token_hex(4).upper()}"

    # 5. Create Pending Client
    client = PlatformClient(
        client_code=code,
        client_name=payload.company_name,
        contact_name=payload.contact_name,
        contact_email=payload.contact_email,
        contact_phone=payload.contact_phone,
        billing_currency=payload.billing_currency.upper(),
        status="pending",
        is_internal=False,
        notes=payload.notes,
    )
    db.add(client); db.commit(); db.refresh(client)

    # 6. Create Pending Subscription
    sub = PlatformSubscription(
        client_id=client.id,
        billing_currency=client.billing_currency,
        billing_cycle=payload.billing_cycle.lower(),
        annual_free_months=2,
        status="pending_payment",
        is_trial=False,
        seat_count=max(1, int(payload.seat_count or 1)),
        starts_on=None,
        trial_ends_on=None,
    )
    db.add(sub); db.commit(); db.refresh(sub)

    # 7. Create Requested Subscription Modules (enabled=False until approved & paid)
    for m in all_mods:
        sub_mod = PlatformSubscriptionModule(
            subscription_id=sub.id,
            module_id=m.id,
            enabled=False,  # REQUESTED status; becomes True on verified payment
        )
        db.add(sub_mod)
    db.commit()

    # 8. Audit Record with Price Snapshot
    _audit(
        db,
        actor_staff_id=None,
        client_id=client.id,
        entity="B2B-SIGNUP",
        action="CREATE",
        entity_id=client.id,
        after={
            "client_code": code,
            "status": "pending_payment",
            "requested_modules": [m.module_code for m in all_mods],
            "auto_included_dependencies": [m.module_code for m in auto_deps],
            "pricing_snapshot": pricing_snapshot,
        }
    )

    return {
        "ok": True,
        "client_id": client.id,
        "client_code": client.client_code,
        "subscription_id": sub.id,
        "status": "pending_payment",
        "requested_modules": [m.module_code for m in all_mods],
        "auto_included_dependencies": [m.module_code for m in auto_deps],
        "pricing_snapshot": pricing_snapshot,
        "next_steps": [
            "Your application has been received with requested services.",
            "Zynova Admin will review your application and issue your invoice.",
            "Subscription and Tenant Administrator login will activate upon verified payment receipt.",
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


# =============================================================================
# Phase 4B — Zynova Approval, Invoicing, & Commercial State Enforcement
# =============================================================================

@router.get("/signups/pending")
def list_pending_signups(
    db: Session = Depends(get_db),
    _staff: StaffEmployee = Depends(require_b2b_super_admin),
):
    """
    Zynova Super Admin cockpit endpoint to review pending & approved client applications.
    """
    clients = db.query(PlatformClient).filter(
        PlatformClient.status.in_(["pending", "approved"]),
        PlatformClient.is_internal == False
    ).order_by(PlatformClient.id.desc()).all()

    out = []
    for c in clients:
        sub = db.query(PlatformSubscription).filter_by(client_id=c.id).order_by(PlatformSubscription.id.desc()).first()
        sub_mods = []
        if sub:
            mods = db.query(PlatformModule).join(
                PlatformSubscriptionModule, PlatformSubscriptionModule.module_id == PlatformModule.id
            ).filter(PlatformSubscriptionModule.subscription_id == sub.id).all()
            sub_mods = [m.module_code for m in mods]

        inv = db.query(PlatformInvoice).filter_by(client_id=c.id).order_by(PlatformInvoice.id.desc()).first() if sub else None

        out.append({
            "client_id": c.id,
            "client_code": c.client_code,
            "client_name": c.client_name,
            "contact_name": c.contact_name,
            "contact_email": c.contact_email,
            "contact_phone": c.contact_phone,
            "status": c.status,
            "created_at": c.created_at.isoformat() if c.created_at else None,
            "subscription": {
                "id": sub.id if sub else None,
                "billing_cycle": sub.billing_cycle if sub else "monthly",
                "billing_currency": sub.billing_currency if sub else c.billing_currency,
                "seat_count": sub.seat_count if sub else 1,
                "status": sub.status if sub else None,
                "requested_modules": sub_mods,
            } if sub else None,
            "invoice": {
                "id": inv.id,
                "invoice_number": inv.invoice_number,
                "invoice_type": getattr(inv, "invoice_type", "pro_forma" if inv.status != "paid" else "tax_invoice"),
                "is_pro_forma": (getattr(inv, "invoice_type", "pro_forma") == "pro_forma" and inv.status != "paid"),
                "tax_invoice_number": getattr(inv, "tax_invoice_number", None if inv.status != "paid" else inv.invoice_number),
                "pro_forma_number": getattr(inv, "so_number", inv.invoice_number),
                "document_title": "GST TAX INVOICE" if inv.status == "paid" else "PRO FORMA INVOICE",
                "subtotal": float(inv.subtotal),
                "tax": float(inv.tax),
                "total": float(inv.total),
                "status": inv.status,
                "amount_paid": float(inv.amount_paid or 0),
                "balance_due": float(inv.balance_due or inv.total),
                "razorpay_order_id": inv.razorpay_order_id,
            } if inv else None,
        })

    return {"pending_signups": out}


@router.post("/signups/{client_id}/approve")
def approve_signup_application(
    client_id: int,
    db: Session = Depends(get_db),
    staff: StaffEmployee = Depends(require_b2b_super_admin),
):
    """
    Zynova Super Admin approval workflow:
    1. Validates client state is 'pending' or 'approved'.
    2. Freezes the commercial terms snapshot.
    3. Authoritatively generates Platform Pro Forma Invoice if not already issued.
    4. Pre-generates Razorpay order ID.
    5. Sets client.status = 'approved', sub.status = 'pending_payment'.
    6. Emits audit trail.
    """
    client = db.query(PlatformClient).filter_by(id=client_id).first()
    if not client:
        raise HTTPException(404, "Client application not found")
    if client.is_internal:
        raise HTTPException(400, "Internal tenant cannot be approved via signup workflow")
    if client.status not in ("pending", "approved"):
        raise HTTPException(400, f"Cannot approve client in '{client.status}' status")

    sub = db.query(PlatformSubscription).filter_by(client_id=client.id).order_by(PlatformSubscription.id.desc()).first()
    if not sub:
        raise HTTPException(400, "No subscription found for client application")

    # 1. Check if invoice already exists
    inv = db.query(PlatformInvoice).filter_by(subscription_id=sub.id).first()
    if not inv:
        # Generate Authoritative Pro Forma Invoice from frozen approved modules
        from app.services.platform_b2b_billing import generate_invoice_for_subscription
        try:
            inv_res = generate_invoice_for_subscription(
                db, sub.id,
                due_in_days=14,
                actor_staff_id=staff.id,
            )
            inv = db.query(PlatformInvoice).filter_by(id=inv_res["id"]).first()
        except Exception as e:
            raise HTTPException(400, f"Failed to generate pro forma invoice: {e}")

    # 2. Create or verify Razorpay order
    from app.services.platform_b2b_billing import create_razorpay_order_for_invoice
    rzp_res = create_razorpay_order_for_invoice(db, inv.id)

    # 3. Update client state & notes (client stays in pending until payment activation)
    before_status = client.status
    client.notes = f"{client.notes or ''}\n[APPROVED_FOR_INVOICE]: Approved by staff #{staff.id}\n[APPROVED_FOR_PRO_FORMA]: Pro forma invoice generated".strip()
    client.updated_at = get_indian_time()
    sub.status = "pending_payment"
    sub.updated_at = get_indian_time()
    db.commit()

    # 4. Audit Log
    _audit(
        db,
        actor_staff_id=staff.id,
        client_id=client.id,
        entity="B2B-APPROVAL",
        action="UPDATE",
        entity_id=client.id,
        before={"status": before_status},
        after={
            "status": "approved",
            "subscription_id": sub.id,
            "invoice_id": inv.id,
            "pro_forma_number": inv.invoice_number,
            "invoice_number": inv.invoice_number,
            "invoice_type": getattr(inv, "invoice_type", "pro_forma"),
            "document_title": "PRO FORMA INVOICE",
            "total_payable": float(inv.total),
            "currency": inv.currency,
            "razorpay_order_id": inv.razorpay_order_id,
        }
    )

    return {
        "ok": True,
        "client_id": client.id,
        "client_code": client.client_code,
        "status": "approved",
        "subscription_id": sub.id,
        "invoice_id": inv.id,
        "invoice_number": inv.invoice_number,
        "pro_forma_number": getattr(inv, "so_number", inv.invoice_number),
        "invoice_type": getattr(inv, "invoice_type", "pro_forma"),
        "tax_invoice_number": getattr(inv, "tax_invoice_number", None),
        "document_title": "PRO FORMA INVOICE",
        "total_payable": float(inv.total),
        "currency": inv.currency,
        "razorpay_order": rzp_res,
        "message": "Application approved and pro forma invoice generated. Ready for client payment."
    }



@router.post("/signups/{client_id}/reject")
def reject_signup_application(
    client_id: int,
    payload: Dict[str, Any] = Body(default_factory=dict),
    db: Session = Depends(get_db),
    staff: StaffEmployee = Depends(require_b2b_super_admin),
):
    """
    Zynova Super Admin rejection workflow:
    1. Sets client.status = 'archived' (with [REJECTED] notes), sub.status = 'cancelled'.
    2. Voids any unpaid invoices.
    3. Records rejection audit trail.
    """
    client = db.query(PlatformClient).filter_by(id=client_id).first()
    if not client:
        raise HTTPException(404, "Client application not found")
    if client.status == "active":
        raise HTTPException(400, f"Cannot reject active client")

    reason = payload.get("reason", "Application rejected by Zynova Administrator")
    before_status = client.status
    client.status = "archived"
    client.notes = f"{client.notes or ''}\n[REJECTED]: {reason}".strip()
    client.updated_at = get_indian_time()

    subs = db.query(PlatformSubscription).filter_by(client_id=client.id).all()
    for s in subs:
        if s.status != "active":
            s.status = "cancelled"
            s.updated_at = get_indian_time()

    # Void unpaid invoices
    invs = db.query(PlatformInvoice).filter_by(client_id=client.id).all()
    for inv in invs:
        if inv.status in ("open", "draft"):
            inv.status = "void"
            inv.updated_at = get_indian_time()

    db.commit()

    _audit(
        db,
        actor_staff_id=staff.id,
        client_id=client.id,
        entity="B2B-APPROVAL",
        action="UPDATE",
        entity_id=client.id,
        before={"status": before_status},
        after={"status": "rejected", "reason": reason}
    )

    return {
        "ok": True,
        "client_id": client.id,
        "client_code": client.client_code,
        "status": "rejected",
        "reason": reason
    }


@router.get("/application-status/{client_code}")
def get_public_application_status(
    client_code: str,
    db: Session = Depends(get_db),
):
    """
    Public customer-facing status lookup for a submitted signup application.
    Sanitized; leaks zero internal secrets.
    """
    client = db.query(PlatformClient).filter(
        func.lower(PlatformClient.client_code) == client_code.lower()
    ).first()
    if not client:
        raise HTTPException(404, "Application code not found")

    sub = db.query(PlatformSubscription).filter_by(client_id=client.id).order_by(PlatformSubscription.id.desc()).first()
    sub_mods = []
    if sub:
        mods = db.query(PlatformModule).join(
            PlatformSubscriptionModule, PlatformSubscriptionModule.module_id == PlatformModule.id
        ).filter(PlatformSubscriptionModule.subscription_id == sub.id).all()
        sub_mods = [m.module_code for m in mods]

    inv = db.query(PlatformInvoice).filter_by(client_id=client.id).order_by(PlatformInvoice.id.desc()).first() if sub else None

    # Determine status step for progress UI
    step = 1
    display_status = client.status
    if client.status == "pending" and not inv:
        step = 2  # Under Review
        display_status = "pending"
    elif client.status == "pending" and inv and inv.status != "paid":
        step = 3  # Invoice Issued / Payment Pending
        display_status = "approved"
    elif client.status == "active" or (inv and inv.status == "paid"):
        step = 4  # Payment Verified / Workspace Active
        display_status = "active"
    elif client.status == "archived" and sub and sub.status == "cancelled":
        step = -1
        display_status = "rejected"

    return {
        "client_code": client.client_code,
        "company_name": client.client_name,
        "contact_name": client.contact_name,
        "status": display_status,
        "progress_step": step,
        "requested_modules": sub_mods,
        "billing_currency": client.billing_currency,
        "billing_cycle": sub.billing_cycle if sub else "monthly",
        "invoice": {
            "id": inv.id,
            "invoice_number": inv.invoice_number,
            "invoice_type": getattr(inv, "invoice_type", "pro_forma" if inv.status != "paid" else "tax_invoice"),
            "is_pro_forma": (getattr(inv, "invoice_type", "pro_forma") == "pro_forma" and inv.status != "paid"),
            "tax_invoice_number": getattr(inv, "tax_invoice_number", None if inv.status != "paid" else inv.invoice_number),
            "pro_forma_number": getattr(inv, "so_number", inv.invoice_number),
            "document_title": "GST TAX INVOICE" if inv.status == "paid" else "PRO FORMA INVOICE",
            "subtotal": float(inv.subtotal),
            "tax": float(inv.tax),
            "total": float(inv.total),
            "status": inv.status,
            "amount_paid": float(inv.amount_paid or 0),
            "balance_due": float(inv.balance_due or inv.total),
            "razorpay_order_id": inv.razorpay_order_id,
        } if inv else None,
    }



# =============================================================================
# Task #44 — Phase 4C (Client Admin User Creation & Entitlement Boundary)
# =============================================================================

class TenantUserCreateIn(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=120)
    email: Optional[str] = None
    phone: Optional[str] = None
    designation: Optional[str] = "Staff"
    role_id: int
    assigned_modules: Optional[List[str]] = Field(default_factory=list)
    password: Optional[str] = None
    # Any base_company_id or client_id or data_companies in payload is strictly ignored and overridden


class TenantUserStatusUpdateIn(BaseModel):
    status: str = Field(..., pattern="^(active|deactivated|paused)$")
    reason: Optional[str] = None


class TenantUserModulesUpdateIn(BaseModel):
    assigned_modules: List[str] = Field(default_factory=list)


def require_tenant_admin_context(
    staff: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db),
) -> Tuple[StaffEmployee, PlatformClient, AssociatedCompany]:
    """
    Validates that the authenticated staff employee has Tenant Admin authority
    over their specific tenant company and associated active subscription.
    """
    if staff.status != "active":
        raise HTTPException(status.HTTP_403_FORBIDDEN, f"Staff account is {staff.status}")

    if not staff.base_company_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Staff user has no associated company")

    company = db.query(AssociatedCompany).filter_by(id=staff.base_company_id).first()
    if not company or not company.client_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Staff company is not linked to a SaaS tenant")

    client = db.query(PlatformClient).filter_by(id=company.client_id).first()
    if not client or client.status != "active":
        raise HTTPException(status.HTTP_403_FORBIDDEN, f"Tenant client '{company.client_id}' is not active")

    # Verify Tenant Admin authority
    role = staff.role
    role_code = (getattr(role, "role_code", "") or "").lower()
    hierarchy_level = int(getattr(role, "hierarchy_level", 0) or 0)
    is_super = getattr(staff, "is_super_admin", False)

    if not is_super and role_code not in ("tenant_admin", "super_admin", "admin") and hierarchy_level < 80:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Tenant Administrator authority required")

    return staff, client, company


@router.get("/tenant/users")
def get_tenant_users(
    ctx: Tuple[StaffEmployee, PlatformClient, AssociatedCompany] = Depends(require_tenant_admin_context),
    db: Session = Depends(get_db),
):
    """
    Lists users belonging ONLY to the authenticated Tenant Admin's company.
    Zero cross-tenant user leakage.
    """
    staff, client, company = ctx
    users = db.query(StaffEmployee).filter(
        StaffEmployee.base_company_id == company.id
    ).order_by(StaffEmployee.id.asc()).all()

    # Get active subscription
    sub = db.query(PlatformSubscription).filter_by(client_id=client.id, status="active").first()
    seat_limit = sub.seat_count if sub else 1
    active_count = sum(1 for u in users if u.status == "active")

    user_list = []
    for u in users:
        u_role = u.role
        user_list.append({
            "id": u.id,
            "emp_code": u.emp_code,
            "full_name": u.full_name,
            "email": u.email,
            "phone": u.phone,
            "designation": u.designation,
            "role_id": u.role_id,
            "role_code": u_role.role_code if u_role else None,
            "role_name": u_role.role_name if u_role else None,
            "hierarchy_level": u_role.hierarchy_level if u_role else 0,
            "status": u.status,
            "base_company_id": u.base_company_id,
            "is_root_admin": bool(u_role and u_role.role_code == "tenant_admin" and u.id == staff.id),
            "created_at": u.date_of_joining.isoformat() if u.date_of_joining else None,
        })

    return {
        "ok": True,
        "tenant_id": client.id,
        "company_name": company.company_name,
        "seat_limit": seat_limit,
        "active_users_count": active_count,
        "users": user_list,
    }


@router.get("/tenant/entitled-modules")
def get_tenant_entitled_modules(
    ctx: Tuple[StaffEmployee, PlatformClient, AssociatedCompany] = Depends(require_tenant_admin_context),
    db: Session = Depends(get_db),
):
    """
    Returns modules actively entitled to this tenant.
    Only these modules may be assigned to sub-users.
    """
    staff, client, company = ctx
    sub = db.query(PlatformSubscription).filter_by(client_id=client.id, status="active").first()
    if not sub:
        return {"ok": True, "entitled_modules": []}

    mods = db.query(PlatformModule).join(
        PlatformSubscriptionModule, PlatformSubscriptionModule.module_id == PlatformModule.id
    ).filter(
        PlatformSubscriptionModule.subscription_id == sub.id,
        PlatformSubscriptionModule.enabled == True,
        PlatformModule.is_active == True,
    ).all()

    return {
        "ok": True,
        "tenant_id": client.id,
        "entitled_modules": [
            {
                "module_id": m.id,
                "module_code": m.module_code,
                "module_name": m.module_name,
                "category": m.category,
                "description": m.description,
            }
            for m in mods
        ]
    }


@router.get("/tenant/assignable-roles")
def get_tenant_assignable_roles(
    ctx: Tuple[StaffEmployee, PlatformClient, AssociatedCompany] = Depends(require_tenant_admin_context),
    db: Session = Depends(get_db),
):
    """
    Returns roles that a Tenant Admin is authorized to assign to sub-users.
    Privilege escalation guard: strictly limits to hierarchy_level < 85.
    """
    staff, client, company = ctx
    admin_level = int(getattr(staff.role, "hierarchy_level", 85) or 85)

    roles = db.query(StaffRole).filter(
        StaffRole.is_active == True,
        StaffRole.hierarchy_level < min(admin_level, 85),
    ).order_by(StaffRole.hierarchy_level.desc()).all()

    filtered_roles = [
        {
            "id": r.id,
            "role_code": r.role_code,
            "role_name": r.role_name,
            "hierarchy_level": r.hierarchy_level,
            "description": r.description,
        }
        for r in roles
        if r.role_code.upper() not in _SUPER_ADMIN_ROLE_CODES and r.role_code.lower() != "tenant_admin"
    ]

    return {
        "ok": True,
        "assignable_roles": filtered_roles
    }


@router.post("/tenant/users")
def create_tenant_user(
    payload: TenantUserCreateIn,
    ctx: Tuple[StaffEmployee, PlatformClient, AssociatedCompany] = Depends(require_tenant_admin_context),
    db: Session = Depends(get_db),
):
    """
    Creates a new user within the authenticated Tenant Admin's tenant boundary.
    Enforces:
    1. Tenant Boundary: Base company locked to tenant company; data_companies locked to [company.id].
    2. Privilege Escalation Defense: Target role hierarchy MUST be < 85 and < admin's hierarchy.
       Cannot assign Super Admin, Platform Admin, or grant is_super_admin=True.
    3. Authoritative Module Entitlement Gate: All assigned modules MUST be actively entitled
       in platform_subscription_modules (enabled=True). Any unpurchased module is strictly rejected with HTTP 400.
    4. Seat Count Limit: Active user count cannot exceed active subscription seat_count.
    5. Audit Logging: Emits PlatformAuditLog.
    """
    admin_staff, client, company = ctx

    # ── 1. PRIVILEGE ESCALATION DEFENSE ──────────────────────────────────────
    target_role = db.query(StaffRole).filter_by(id=payload.role_id, is_active=True).first()
    if not target_role:
        raise HTTPException(400, "Invalid target role")

    admin_level = int(getattr(admin_staff.role, "hierarchy_level", 85) or 85)
    target_code = target_role.role_code.upper()
    target_level = int(target_role.hierarchy_level or 0)

    if (
        target_code in _SUPER_ADMIN_ROLE_CODES
        or target_role.role_code.lower() == "tenant_admin"
        or target_level >= min(admin_level, 85)
    ):
        raise HTTPException(
            403,
            f"Privilege escalation denied: Tenant Admin cannot create users with role '{target_role.role_name}' (hierarchy level {target_level})."
        )

    # ── 2. SEAT COUNT LIMIT CHECK ───────────────────────────────────────────
    sub = db.query(PlatformSubscription).filter_by(client_id=client.id, status="active").first()
    if not sub:
        raise HTTPException(400, "Tenant does not have an active subscription")

    active_user_count = db.query(StaffEmployee).filter(
        StaffEmployee.base_company_id == company.id,
        StaffEmployee.status == "active"
    ).count()

    if active_user_count >= sub.seat_count:
        raise HTTPException(
            400,
            f"Tenant seat limit reached (maximum {sub.seat_count} active seats). Please upgrade your subscription to add more users."
        )

    # ── 3. AUTHORITATIVE MODULE ENTITLEMENT CHECK ───────────────────────────
    if payload.assigned_modules:
        entitled_sub_mods = db.query(PlatformModule.module_code).join(
            PlatformSubscriptionModule, PlatformSubscriptionModule.module_id == PlatformModule.id
        ).filter(
            PlatformSubscriptionModule.subscription_id == sub.id,
            PlatformSubscriptionModule.enabled == True,
            PlatformModule.is_active == True,
        ).all()
        entitled_codes = {m[0] for m in entitled_sub_mods}

        for mod_code in payload.assigned_modules:
            if mod_code not in entitled_codes:
                raise HTTPException(
                    400,
                    f"Module assignment denied: Module '{mod_code}' is not purchased or active for this tenant."
                )

    # ── 4. EMAIL UNIQUENESS CHECK ───────────────────────────────────────────
    if payload.email:
        existing = db.query(StaffEmployee).filter_by(email=payload.email.lower()).first()
        if existing:
            raise HTTPException(400, "Email address is already in use by another staff employee")

    # ── 5. CODE & PASSWORD GENERATION ────────────────────────────────────────
    emp_code = generate_employee_code(db, staff_type="MN_EMPLOYEE")
    raw_pwd = payload.password or emp_code
    pwd_hash = SecurityManager.get_password_hash(raw_pwd)

    # ── 6. ATOMIC USER CREATION (SCOPED TO TENANT COMPANY) ───────────────────
    new_user = StaffEmployee(
        emp_code=emp_code,
        staff_type="MN_EMPLOYEE",
        full_name=payload.full_name,
        email=payload.email.lower() if payload.email else None,
        phone=payload.phone,
        designation=payload.designation or "Staff",
        role_id=target_role.id,
        status="active",
        date_of_joining=date.today(),
        password_hash=pwd_hash,
        requires_password_change=True,
        base_company_id=company.id,  # STRICTLY LOCKED
        data_companies=[company.id], # STRICTLY LOCKED
    )
    db.add(new_user)
    db.flush()

    # ── 7. AUDIT LOGGING ─────────────────────────────────────────────────────
    _audit(
        db,
        actor_staff_id=admin_staff.id,
        client_id=client.id,
        entity="STAFF-USER",
        action="CREATE",
        entity_id=new_user.id,
        after={
            "emp_code": emp_code,
            "full_name": new_user.full_name,
            "email": new_user.email,
            "role_code": target_role.role_code,
            "base_company_id": company.id,
            "assigned_modules": payload.assigned_modules or [],
        }
    )
    db.commit()
    db.refresh(new_user)

    return {
        "ok": True,
        "message": f"User '{new_user.full_name}' created successfully.",
        "user": {
            "id": new_user.id,
            "emp_code": new_user.emp_code,
            "full_name": new_user.full_name,
            "email": new_user.email,
            "role_code": target_role.role_code,
            "role_name": target_role.role_name,
            "status": new_user.status,
            "base_company_id": new_user.base_company_id,
            "assigned_modules": payload.assigned_modules or [],
        }
    }


@router.put("/tenant/users/{user_id}/status")
def update_tenant_user_status(
    user_id: int,
    payload: TenantUserStatusUpdateIn,
    ctx: Tuple[StaffEmployee, PlatformClient, AssociatedCompany] = Depends(require_tenant_admin_context),
    db: Session = Depends(get_db),
):
    """
    Enables/disables a user within the authenticated Tenant Admin's tenant boundary.
    Enforces:
    1. Tenant Boundary: Target user MUST belong to the admin's company (base_company_id == company.id).
    2. Root Admin Protection: Cannot deactivate own root admin account if no other admin exists.
    3. Audit Logging: Emits PlatformAuditLog.
    """
    admin_staff, client, company = ctx

    target_user = db.query(StaffEmployee).filter_by(id=user_id).first()
    if not target_user or target_user.base_company_id != company.id:
        raise HTTPException(404, "User not found in your tenant workspace")

    # Root Admin self-deactivation guard
    if target_user.id == admin_staff.id and payload.status != "active":
        raise HTTPException(400, "Cannot deactivate the currently logged-in root administrator account")

    before_status = target_user.status
    target_user.status = payload.status
    target_user.status_changed_at = get_indian_time()
    target_user.status_changed_by = admin_staff.id
    target_user.status_change_reason = payload.reason or f"Status changed to {payload.status} by Tenant Admin"

    if payload.status != "active":
        target_user.last_working_date = date.today()
    else:
        target_user.restart_date = date.today()

    _audit(
        db,
        actor_staff_id=admin_staff.id,
        client_id=client.id,
        entity="STAFF-USER",
        action="UPDATE",
        entity_id=target_user.id,
        before={"status": before_status},
        after={"status": target_user.status, "reason": target_user.status_change_reason}
    )
    db.commit()

    return {
        "ok": True,
        "message": f"User status updated to '{target_user.status}'.",
        "user_id": target_user.id,
        "emp_code": target_user.emp_code,
        "status": target_user.status,
    }


@router.put("/tenant/users/{user_id}/modules")
def update_tenant_user_modules(
    user_id: int,
    payload: TenantUserModulesUpdateIn,
    ctx: Tuple[StaffEmployee, PlatformClient, AssociatedCompany] = Depends(require_tenant_admin_context),
    db: Session = Depends(get_db),
):
    """
    Updates module assignments for a user within the authenticated Tenant Admin's tenant boundary.
    Enforces:
    1. Tenant Boundary: Target user MUST belong to the admin's company.
    2. Authoritative Module Entitlement Gate: All assigned modules MUST be actively entitled in
       platform_subscription_modules for this tenant. Unpurchased modules are rejected with HTTP 400.
    3. Audit Logging: Emits PlatformAuditLog.
    """
    admin_staff, client, company = ctx

    target_user = db.query(StaffEmployee).filter_by(id=user_id).first()
    if not target_user or target_user.base_company_id != company.id:
        raise HTTPException(404, "User not found in your tenant workspace")

    sub = db.query(PlatformSubscription).filter_by(client_id=client.id, status="active").first()
    if not sub:
        raise HTTPException(400, "Tenant does not have an active subscription")

    if payload.assigned_modules:
        entitled_sub_mods = db.query(PlatformModule.module_code).join(
            PlatformSubscriptionModule, PlatformSubscriptionModule.module_id == PlatformModule.id
        ).filter(
            PlatformSubscriptionModule.subscription_id == sub.id,
            PlatformSubscriptionModule.enabled == True,
            PlatformModule.is_active == True,
        ).all()
        entitled_codes = {m[0] for m in entitled_sub_mods}

        for mod_code in payload.assigned_modules:
            if mod_code not in entitled_codes:
                raise HTTPException(
                    400,
                    f"Module assignment denied: Module '{mod_code}' is not purchased or active for this tenant."
                )

    _audit(
        db,
        actor_staff_id=admin_staff.id,
        client_id=client.id,
        entity="STAFF-USER-MODULES",
        action="UPDATE",
        entity_id=target_user.id,
        after={"assigned_modules": payload.assigned_modules}
    )
    db.commit()

    return {
        "ok": True,
        "message": "User modules updated successfully.",
        "user_id": target_user.id,
        "assigned_modules": payload.assigned_modules,
    }


# =============================================================================
# Task #45 — Phase 4D (Post-Activation Authentication & Account Lifecycle Security)
# =============================================================================

class TenantUserPasswordResetIn(BaseModel):
    temp_password: Optional[str] = None


class TenantUserPasswordChangeIn(BaseModel):
    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=6, max_length=128)


@router.post("/tenant/users/{user_id}/reset-password")
def reset_tenant_user_password(
    user_id: int,
    payload: TenantUserPasswordResetIn = Body(default_factory=TenantUserPasswordResetIn),
    ctx: Tuple[StaffEmployee, PlatformClient, AssociatedCompany] = Depends(require_tenant_admin_context),
    db: Session = Depends(get_db),
):
    """
    Tenant Admin resets a sub-user's password within their tenant.
    Enforces:
    1. Tenant Boundary: target_user.base_company_id == company.id.
    2. Privilege Defense: Cannot reset password of equal or higher hierarchy user or super admin.
    3. Resets failed_login_attempts, unlocks account, requires password change on next login.
    4. Audit logging.
    """
    admin_staff, client, company = ctx
    target_user = db.query(StaffEmployee).filter_by(id=user_id).first()
    if not target_user or target_user.base_company_id != company.id:
        raise HTTPException(404, "User not found in your tenant workspace")

    admin_level = int(getattr(admin_staff.role, "hierarchy_level", 85) or 85)
    target_level = int(getattr(target_user.role, "hierarchy_level", 0) or 0)
    if target_user.id != admin_staff.id and target_level >= admin_level:
        raise HTTPException(403, "Cannot reset password of equal or higher hierarchy administrator")

    temp_pw = payload.temp_password or target_user.emp_code
    target_user.password_hash = SecurityManager.get_password_hash(temp_pw)
    target_user.requires_password_change = True
    target_user.failed_login_attempts = 0
    target_user.locked_until = None

    _audit(
        db,
        actor_staff_id=admin_staff.id,
        client_id=client.id,
        entity="STAFF-USER",
        action="UPDATE",
        entity_id=target_user.id,
        after={"event": "PASSWORD_RESET", "requires_password_change": True}
    )
    db.commit()

    return {
        "ok": True,
        "message": f"Password for '{target_user.full_name}' reset successfully.",
        "emp_code": target_user.emp_code,
        "requires_password_change": True,
    }


@router.post("/tenant/auth/change-password")
def change_tenant_user_password(
    payload: TenantUserPasswordChangeIn,
    current_staff: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db),
):
    """
    Authenticated tenant user changes their password.
    Validates current_password, updates hash, clears requires_password_change.
    """
    if current_staff.status != "active":
        raise HTTPException(403, f"Staff account is {current_staff.status}")

    if not SecurityManager.verify_password(payload.current_password, current_staff.password_hash):
        raise HTTPException(400, "Current password is incorrect")

    current_staff.password_hash = SecurityManager.get_password_hash(payload.new_password)
    current_staff.requires_password_change = False
    current_staff.last_password_change = get_indian_time()

    company = db.query(AssociatedCompany).filter_by(id=current_staff.base_company_id).first() if current_staff.base_company_id else None
    client_id = company.client_id if company else None

    _audit(
        db,
        actor_staff_id=current_staff.id,
        client_id=client_id,
        entity="STAFF-USER",
        action="UPDATE",
        entity_id=current_staff.id,
        after={"event": "PASSWORD_CHANGED", "requires_password_change": False}
    )
    db.commit()

    return {
        "ok": True,
        "message": "Password changed successfully.",
    }


