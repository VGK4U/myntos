"""
B2B SaaS Layer — Phase 3 Enforcement helpers (Task #41).

Provides:
- b2b_required(module_code) FastAPI dependency that 403s if not entitled
  (only when B2B_ENFORCE=true; otherwise just logs via shadow hook).
- filter_menu_by_entitlement(rows, db, client_id) for sidebar filtering.
- preview_entitlement(db, client_id) for super-admin "what would happen" preview.

The default B2B_ENFORCE=false → no behavior change for existing users.
"""

from __future__ import annotations

import logging
from typing import List, Dict, Any, Optional, Iterable

from fastapi import Depends, HTTPException, Request
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.v1.endpoints.staff_auth import get_current_staff_user
from app.models.staff import StaffEmployee
from app.services.b2b_shadow import (
    is_module_entitled, resolve_client_id_for_staff, enforce_enabled,
)

logger = logging.getLogger(__name__)


def b2b_required(module_code: str):
    """
    Endpoint dependency:
        @router.get("/foo", dependencies=[Depends(b2b_required("menu:foo"))])
    Always logs the decision; only raises 403 when B2B_ENFORCE=true.
    """
    def _dep(
        request: Request,
        db: Session = Depends(get_db),
        staff: StaffEmployee = Depends(get_current_staff_user),
    ) -> bool:
        cid = resolve_client_id_for_staff(db, staff)
        ok = is_module_entitled(
            db, cid, module_code,
            user_id=getattr(staff, "id", None),
            user_type="staff",
            route=str(request.url.path),
        )
        if not ok and enforce_enabled():
            raise HTTPException(
                status_code=403,
                detail=f"module '{module_code}' is not entitled for your organisation",
            )
        return True
    return _dep


def filter_menu_by_entitlement(
    rows: Iterable[Dict[str, Any]],
    db: Session,
    client_id: Optional[int],
    *,
    user_id: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """
    Filter a list of sidebar/menu dicts by current entitlement. Each row must
    contain a 'menu_code' or 'route_path' key. When B2B_ENFORCE=false this is
    a passthrough (every row kept) — same as Phase 1.
    """
    rows = list(rows)
    if not enforce_enabled() or client_id is None:
        return rows
    out: List[Dict[str, Any]] = []
    for r in rows:
        code = r.get("menu_code") or r.get("module_code")
        if not code and r.get("route_path"):
            # menu codes ingested in Phase 1 are 'menu:<route_path>'
            code = f"menu:{r['route_path']}"
        if code is None:
            out.append(r)
            continue
        if is_module_entitled(db, client_id, code, user_id=user_id, user_type="staff"):
            out.append(r)
    return out


def preview_entitlement(db: Session, client_id: int) -> Dict[str, Any]:
    """
    Return the 'what would change if we flipped enforcement on' preview for a
    client: the count of modules they currently see (sidebar entries) vs how
    many would survive the entitlement filter.
    """
    rows = db.execute(text("""
        SELECT pm.id, pm.module_code, pm.module_name,
               (psm.id IS NOT NULL AND psm.enabled = TRUE) AS entitled
          FROM platform_modules pm
     LEFT JOIN platform_subscriptions ps
                ON ps.client_id = :cid
               AND ps.status IN ('trial','active')
     LEFT JOIN platform_subscription_modules psm
                ON psm.subscription_id = ps.id
               AND psm.module_id       = pm.id
         WHERE pm.is_active = TRUE
    """), {"cid": client_id}).mappings().all()

    total = len(rows)
    entitled = sum(1 for r in rows if r["entitled"])
    blocked = total - entitled
    sample = [
        {"module_code": r["module_code"], "module_name": r["module_name"]}
        for r in rows if not r["entitled"]
    ][:50]
    return {
        "client_id": client_id,
        "total_modules": total,
        "entitled_modules": entitled,
        "would_block_modules": blocked,
        "sample_blocked": sample,
        "currently_enforcing": enforce_enabled(),
    }
