"""
B2B SaaS Layer Phase 1 — Idempotent Seeder + DDL Apply
Task #39 (May 03, 2026)

Responsibilities (all idempotent, safe on every startup):
1. apply_platform_b2b_ddl()       — runs add_platform_b2b_20260503.sql once
                                     via the existing dc_migrations key registry.
2. ensure_internal_client()       — creates MNR-INTERNAL platform_clients row.
3. backfill_associated_companies()— links every existing associated_companies
                                     row to the internal client (NULL → internal).
4. ingest_module_catalog()        — mirrors staff_menu_registry into
                                     platform_modules at menu/page granularity.
5. seed_default_plan()            — creates 'INTERNAL_FULL' plan and entitles
                                     the internal client to every module.

DC: Additive only. No DELETE / no DROP. No runtime ALTER TABLE — all DDL is
applied via the .sql file in backend/migrations/.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models.base import get_indian_time

logger = logging.getLogger(__name__)

_MIGRATION_KEY = "platform_b2b_phase1_20260503"
_MIGRATION_FILE = "add_platform_b2b_20260503.sql"
_PHASE4_MIGRATION_KEY  = "platform_b2b_phase4_20260503"
_PHASE4_MIGRATION_FILE = "add_platform_b2b_phase4_billing_20260503.sql"
_INTERNAL_CLIENT_CODE = "MNR-INTERNAL"
_INTERNAL_PLAN_CODE = "INTERNAL_FULL"


# ─────────────────────────────────────────────────────────────────────────────
def _migrations_dir() -> Path:
    # backend/app/services/platform_b2b_seed.py  →  backend/migrations/
    return Path(__file__).resolve().parents[2] / "migrations"


def apply_platform_b2b_ddl(db: Session) -> bool:
    """
    Apply 11-table DDL exactly once, recording success in `dc_migrations`.

    Returns True if DDL was applied this call, False if already applied.
    Raises on SQL error so the caller can surface it.
    """
    # Defensive: ensure dc_migrations registry exists (mirrors main.py pattern).
    db.execute(text("""
        CREATE TABLE IF NOT EXISTS dc_migrations (
            key VARCHAR(128) PRIMARY KEY,
            applied_at TIMESTAMP NOT NULL DEFAULT (NOW() AT TIME ZONE 'Asia/Kolkata')
        )
    """))
    db.commit()

    already = db.execute(
        text("SELECT 1 FROM dc_migrations WHERE key = :k"), {"k": _MIGRATION_KEY}
    ).first()
    if already:
        logger.info("[DC-B2B-DDL] Migration %s already applied — skipping", _MIGRATION_KEY)
        return False

    sql_path = _migrations_dir() / _MIGRATION_FILE
    if not sql_path.exists():
        raise FileNotFoundError(f"[DC-B2B-DDL] Migration file missing: {sql_path}")

    sql = sql_path.read_text(encoding="utf-8")

    # psycopg supports multi-statement strings via execute(text(...)); run inside
    # a single transaction so partial failures roll back cleanly.
    raw = db.connection().connection  # underlying DBAPI connection
    cur = raw.cursor()
    try:
        cur.execute(sql)
        raw.commit()
    except Exception:
        raw.rollback()
        raise
    finally:
        cur.close()

    db.execute(
        text("INSERT INTO dc_migrations (key) VALUES (:k) ON CONFLICT DO NOTHING"),
        {"k": _MIGRATION_KEY},
    )
    db.commit()
    logger.info("[DC-B2B-DDL] ✅ Applied %s (11 tables + associated_companies.client_id)", _MIGRATION_FILE)
    return True


def apply_platform_b2b_phase4_ddl(db: Session) -> bool:
    """Apply Phase-4 billing DDL (invoices, invoice_lines, payments) idempotently."""
    already = db.execute(
        text("SELECT 1 FROM dc_migrations WHERE key = :k"), {"k": _PHASE4_MIGRATION_KEY}
    ).first()
    if already:
        return False
    sql_path = _migrations_dir() / _PHASE4_MIGRATION_FILE
    if not sql_path.exists():
        raise FileNotFoundError(f"[DC-B2B-DDL] Phase-4 migration file missing: {sql_path}")
    sql = sql_path.read_text(encoding="utf-8")
    raw = db.connection().connection
    cur = raw.cursor()
    try:
        cur.execute(sql); raw.commit()
    except Exception:
        raw.rollback(); raise
    finally:
        cur.close()
    db.execute(
        text("INSERT INTO dc_migrations (key) VALUES (:k) ON CONFLICT DO NOTHING"),
        {"k": _PHASE4_MIGRATION_KEY},
    )
    db.commit()
    logger.info("[DC-B2B-DDL] ✅ Applied %s (3 billing tables)", _PHASE4_MIGRATION_FILE)
    return True


# ─────────────────────────────────────────────────────────────────────────────
def ensure_associated_companies_client_id_column(db: Session) -> None:
    """
    Defensive existence check ONLY (per code-review guidance).

    The column is created by the .sql migration above — this helper just
    verifies it exists and logs a warning if not. It deliberately does NOT
    issue a runtime ALTER TABLE.
    """
    row = db.execute(text("""
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'associated_companies' AND column_name = 'client_id'
    """)).first()
    if row is None:
        logger.warning(
            "[DC-B2B-DDL] associated_companies.client_id is missing — "
            "expected migration %s to add it. Run apply_platform_b2b_ddl() first.",
            _MIGRATION_FILE,
        )


# ─────────────────────────────────────────────────────────────────────────────
def ensure_internal_client(db: Session) -> int:
    """Create or return the internal MNR-INTERNAL client. Returns its id."""
    from app.models.platform_b2b import PlatformClient

    existing = db.query(PlatformClient).filter_by(client_code=_INTERNAL_CLIENT_CODE).first()
    if existing:
        return existing.id

    row = PlatformClient(
        client_code=_INTERNAL_CLIENT_CODE,
        client_name="MyntReal Internal (auto-seeded)",
        is_internal=True,
        status="active",
        billing_currency="INR",
        notes="Auto-created by Task #39 Phase 1 seeder. Owns every existing associated_companies row.",
        created_at=get_indian_time(),
        updated_at=get_indian_time(),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    logger.info("[DC-B2B-SEED] ✅ Internal client created: %s (id=%s)", _INTERNAL_CLIENT_CODE, row.id)
    return row.id


def backfill_associated_companies(db: Session, internal_client_id: int) -> int:
    """Link every associated_companies row with NULL client_id to the internal client."""
    res = db.execute(
        text("UPDATE associated_companies SET client_id = :cid WHERE client_id IS NULL"),
        {"cid": internal_client_id},
    )
    db.commit()
    n = res.rowcount or 0
    if n:
        logger.info("[DC-B2B-SEED] ✅ Back-filled %d associated_companies → client_id=%s", n, internal_client_id)
    return n


# ─────────────────────────────────────────────────────────────────────────────
def ingest_module_catalog(db: Session) -> int:
    """
    Mirror staff_menu_registry rows into platform_modules at menu granularity.
    Idempotent: insert only when module_code is missing.

    module_code := 'menu:' || menu_code  (stable, prefix avoids collision).
    """
    rows = db.execute(text("""
        SELECT menu_code, menu_name, sidebar_section, sidebar_section_title
        FROM staff_menu_registry
        WHERE menu_code IS NOT NULL AND menu_code <> ''
    """)).fetchall()

    if not rows:
        logger.info("[DC-B2B-SEED] staff_menu_registry empty — module catalog ingestion skipped")
        return 0

    inserted = 0
    for r in rows:
        menu_code = r[0]
        menu_name = r[1] or menu_code
        sidebar_section = r[2]
        section_title = r[3]
        module_code = f"menu:{menu_code}"

        existing = db.execute(
            text("SELECT 1 FROM platform_modules WHERE module_code = :c"),
            {"c": module_code},
        ).first()
        if existing:
            continue

        db.execute(text("""
            INSERT INTO platform_modules
                (module_code, module_name, category, description, menu_code, sidebar_section,
                 internal_only, is_active, created_at, updated_at)
            VALUES
                (:code, :name, :cat, :desc, :menu, :sec,
                 FALSE, TRUE, :now, :now)
        """), {
            "code": module_code,
            "name": menu_name,
            "cat": section_title or sidebar_section,
            "desc": f"Auto-ingested from staff_menu_registry.{menu_code}",
            "menu": menu_code,
            "sec": sidebar_section,
            "now": get_indian_time(),
        })
        inserted += 1

    if inserted:
        db.commit()
        logger.info("[DC-B2B-SEED] ✅ Ingested %d new modules from staff_menu_registry", inserted)

    # Mark internal-only modules per Q6 follow-up.
    db.execute(text("""
        UPDATE platform_modules
           SET internal_only = TRUE
         WHERE internal_only = FALSE
           AND lower(menu_code) IN ('wallet','awards','bonanza','member_tree')
    """))
    db.commit()
    return inserted


# ─────────────────────────────────────────────────────────────────────────────
def seed_default_plan(db: Session, internal_client_id: int) -> Optional[int]:
    """
    Create INTERNAL_FULL plan + a subscription for the internal client that
    entitles every module. Idempotent.
    """
    from app.models.platform_b2b import (
        PlatformPlan, PlatformPlanModule, PlatformSubscription,
        PlatformSubscriptionModule, PlatformModule,
    )

    plan = db.query(PlatformPlan).filter_by(plan_code=_INTERNAL_PLAN_CODE).first()
    if not plan:
        plan = PlatformPlan(
            plan_code=_INTERNAL_PLAN_CODE,
            plan_name="MNR Internal — Full Access",
            description="Auto-seeded plan for the internal tenant. Includes every module.",
            is_active=True,
        )
        db.add(plan)
        db.commit()
        db.refresh(plan)
        logger.info("[DC-B2B-SEED] ✅ Plan %s created (id=%s)", _INTERNAL_PLAN_CODE, plan.id)

    # Plan ↔ all modules
    module_ids = [m_id for (m_id,) in db.execute(text("SELECT id FROM platform_modules")).all()]
    existing_pm = {
        row[0] for row in db.execute(
            text("SELECT module_id FROM platform_plan_modules WHERE plan_id = :p"),
            {"p": plan.id},
        ).all()
    }
    for mid in module_ids:
        if mid not in existing_pm:
            db.add(PlatformPlanModule(plan_id=plan.id, module_id=mid))
    db.commit()

    # Subscription for internal client
    sub = db.query(PlatformSubscription).filter_by(
        client_id=internal_client_id, plan_id=plan.id
    ).first()
    if not sub:
        sub = PlatformSubscription(
            client_id=internal_client_id,
            plan_id=plan.id,
            display_plan_name="Internal (full access)",
            billing_currency="INR",
            billing_cycle="monthly",
            is_trial=False,
            status="active",
        )
        db.add(sub)
        db.commit()
        db.refresh(sub)
        logger.info("[DC-B2B-SEED] ✅ Internal subscription created (id=%s)", sub.id)

    existing_sm = {
        row[0] for row in db.execute(
            text("SELECT module_id FROM platform_subscription_modules WHERE subscription_id = :s"),
            {"s": sub.id},
        ).all()
    }
    for mid in module_ids:
        if mid not in existing_sm:
            db.add(PlatformSubscriptionModule(subscription_id=sub.id, module_id=mid, enabled=True))
    db.commit()
    return sub.id


# ─────────────────────────────────────────────────────────────────────────────
def run_full_b2b_phase1_seed(db: Session) -> dict:
    """Top-level entry point — call from main.py startup. All steps idempotent."""
    summary: dict = {"ddl_applied": False, "internal_client_id": None,
                     "backfilled_companies": 0, "modules_ingested": 0, "subscription_id": None}
    try:
        summary["ddl_applied"] = apply_platform_b2b_ddl(db)
        summary["phase4_ddl_applied"] = apply_platform_b2b_phase4_ddl(db)
        ensure_associated_companies_client_id_column(db)
        cid = ensure_internal_client(db)
        summary["internal_client_id"] = cid
        summary["backfilled_companies"] = backfill_associated_companies(db, cid)
        summary["modules_ingested"] = ingest_module_catalog(db)
        summary["subscription_id"] = seed_default_plan(db, cid)
        logger.info("[DC-B2B-SEED] ✅ Phase 1 seed complete: %s", summary)
    except Exception as exc:
        logger.exception("[DC-B2B-SEED] ❌ Phase 1 seed failed (non-fatal): %s", exc)
    return summary
