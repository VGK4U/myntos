"""
B2B SaaS Layer — Entitlement Hook (Tasks #39 + #41)

Public API:
- is_module_entitled(db, client_id, module_code, *, user_id=None,
                     user_type=None, route=None) -> bool
- resolve_client_id_for_staff(db, staff) -> Optional[int]

Behaviour:
- Phase 1 (shadow mode, B2B_ENFORCE=false, default):
    Always returns True. Logs the would-have decision to b2b_shadow_log.
- Phase 3 (enforcement, B2B_ENFORCE=true):
    Returns the real decision (False on WOULD_BLOCK / suspended client).
    Still logs to b2b_shadow_log for visibility.

DC: failures are swallowed (fail-open in shadow, fail-open in enforce too —
    we never want a metering bug to take down the app).
"""

from __future__ import annotations

import logging
import os
from typing import Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# Default tenant — every existing user maps here until per-user client_id is wired.
INTERNAL_CLIENT_CODE = "MNR-INTERNAL"


def enforce_enabled() -> bool:
    """Honour the runtime B2B_ENFORCE flag (default false, safe)."""
    return os.environ.get("B2B_ENFORCE", "false").strip().lower() in ("1", "true", "yes", "on")


def resolve_client_id_for_staff(db: Session, staff) -> Optional[int]:
    """
    Map a staff principal to a platform_clients.id.

    For now: every staff user belongs to the internal MNR tenant. Phase 5 will
    add a real per-user client_id (likely on staff_employees or via a join
    table). Until then this is a single SELECT and is cached by callers.
    """
    if staff is None:
        return None
    # Optional staff.client_id support if the column exists in a future phase
    cid = getattr(staff, "client_id", None)
    if cid:
        return int(cid)
    try:
        row = db.execute(
            text("SELECT id FROM platform_clients WHERE client_code = :c LIMIT 1"),
            {"c": INTERNAL_CLIENT_CODE},
        ).first()
        return int(row[0]) if row else None
    except Exception as exc:
        logger.debug("[DC-B2B] resolve_client_id_for_staff failed: %s", exc)
        return None


def _client_status(db: Session, client_id: Optional[int]) -> Optional[str]:
    if client_id is None:
        return None
    try:
        row = db.execute(
            text("SELECT status FROM platform_clients WHERE id = :i"),
            {"i": client_id},
        ).first()
        return row[0] if row else None
    except Exception:
        return None


def is_module_entitled(
    db: Session,
    client_id: Optional[int],
    module_code: Optional[str],
    *,
    user_id: Optional[int] = None,
    user_type: Optional[str] = None,
    route: Optional[str] = None,
) -> bool:
    """
    Compute & log entitlement decision. In shadow mode (default) always
    returns True. In enforcement mode (B2B_ENFORCE=true) returns the
    real decision.
    """
    enforcing = enforce_enabled()
    decision = "ALLOW"
    reason: Optional[str] = None

    try:
        # 1) Per-client kill-switch (suspended/archived → deny everything)
        cstatus = _client_status(db, client_id)
        if cstatus in ("suspended", "archived"):
            decision = "WOULD_BLOCK"
            reason = f"client status = {cstatus}"
        elif module_code:
            # 2) Module entitlement via active/trial subscription
            row = db.execute(
                text("""
                    SELECT psm.enabled
                      FROM platform_subscription_modules psm
                      JOIN platform_subscriptions ps  ON ps.id = psm.subscription_id
                      JOIN platform_modules       pm  ON pm.id = psm.module_id
                     WHERE ps.client_id   = :cid
                       AND pm.module_code = :mc
                       AND ps.status      IN ('trial', 'active')
                     LIMIT 1
                """),
                {"cid": client_id, "mc": module_code},
            ).first()
            if row is None:
                decision = "WOULD_BLOCK"
                reason = "no active subscription module match"
            elif not row[0]:
                decision = "WOULD_BLOCK"
                reason = "subscription module disabled"
    except Exception as exc:
        logger.debug("[DC-B2B] decision lookup failed: %s", exc)
        decision = "ALLOW"
        reason = "lookup-failed-fail-open"

    # Log every decision (shadow OR enforce) for full visibility.
    try:
        db.execute(
            text("""
                INSERT INTO b2b_shadow_log
                    (client_id, user_id, user_type, module_code, route, decision, reason)
                VALUES (:cid, :uid, :ut, :mc, :rt, :dec, :rsn)
            """),
            {
                "cid": client_id, "uid": user_id, "ut": user_type,
                "mc": module_code, "rt": route, "dec": decision, "rsn": reason,
            },
        )
        db.commit()
    except Exception as exc:
        try: db.rollback()
        except Exception: pass
        logger.debug("[DC-B2B] shadow-log insert failed: %s", exc)

    if not enforcing:
        return True
    return decision == "ALLOW"
