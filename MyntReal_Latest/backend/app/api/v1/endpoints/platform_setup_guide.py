"""
DC_PLATFORM_GUIDE_001 (May 2026)

Endpoint that powers `/staff/platform-setup-guide`. Composes:
  • Curated walkthrough sections (from app.data.platform_setup_content)
  • Live platform inventory (DB-derived: companies, employees, sections,
    submenus, page count, env-var status)
  • Append-only changelog of platform changes

The endpoint is intentionally read-only and cheap — it should never error
because of missing optional integrations; environment status is reported
in the response body instead of as exceptions.
"""

import os
from datetime import datetime
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.data.platform_setup_content import (
    SETUP_SECTIONS,
    PLATFORM_CHANGELOG,
    ENV_VAR_REGISTRY,
)

router = APIRouter(prefix="/staff/platform-setup-guide", tags=["Platform Setup Guide"])


def _safe_count(db: Session, sql: str) -> int:
    """Return COUNT(*) or 0 if the table doesn't exist on this tenant yet."""
    try:
        return int(db.execute(text(sql)).scalar() or 0)
    except Exception:
        return 0


@router.get("")
def get_platform_setup_guide(db: Session = Depends(get_db)):
    # ---- Live DB inventory -------------------------------------------------
    company_rows = []
    try:
        rows = db.execute(text(
            "SELECT id, company_name, company_code, is_active "
            "FROM associated_companies ORDER BY company_name"
        )).fetchall()
        company_rows = [
            {"id": r[0], "name": r[1], "code": r[2], "active": bool(r[3])}
            for r in rows
        ]
    except Exception:
        pass

    section_rows = []
    try:
        rows = db.execute(text("""
            SELECT COALESCE(sidebar_section,'(unset)')          AS section,
                   COALESCE(sidebar_section_title, sidebar_section, '(unset)') AS title,
                   COALESCE(sidebar_section_order, 0)            AS sec_order,
                   COUNT(DISTINCT menu_code)                     AS menu_count
              FROM staff_menu_master
             WHERE is_active = TRUE
             GROUP BY 1, 2, 3
             ORDER BY 3, 2
        """)).fetchall()
        section_rows = [
            {"section": r[0], "title": r[1], "order": int(r[2]), "menu_count": int(r[3])}
            for r in rows
        ]
    except Exception:
        pass

    stats = {
        "companies_total":      len(company_rows),
        "companies_active":     sum(1 for c in company_rows if c["active"]),
        "employees_total":      _safe_count(db, "SELECT COUNT(*) FROM staff WHERE is_active = TRUE"),
        "departments_total":    _safe_count(db, "SELECT COUNT(*) FROM departments"),
        "menu_sections_total":  len(section_rows),
        "menu_pages_total":     _safe_count(db, "SELECT COUNT(DISTINCT menu_code) FROM staff_menu_master WHERE is_active = TRUE"),
        "audit_log_entries":    _safe_count(db, "SELECT COUNT(*) FROM staff_activity_logs"),
    }

    # ---- Env var status (no values exposed, only presence) ----------------
    env_status = []
    for spec in ENV_VAR_REGISTRY:
        env_status.append({
            "name":     spec["name"],
            "required": spec["required"],
            "purpose":  spec["purpose"],
            "present":  bool(os.environ.get(spec["name"])),
        })

    return {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "setup_sections": SETUP_SECTIONS,
        "changelog":      PLATFORM_CHANGELOG,
        "live_inventory": {
            "stats":     stats,
            "companies": company_rows,
            "sections":  section_rows,
            "env":       env_status,
        },
    }
