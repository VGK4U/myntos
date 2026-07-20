"""
DC Protocol: Staff System Validation API
Serves dynamic validation/enforcement data from StaffMenuRegistry + validation content.
Covers UI validation, workflow integrity, backend enforcement, and risk matrix.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.staff import StaffMenuRegistry
from app.data.staff_validation_content import (
    STAFF_VALIDATION_CONTENT, VALIDATION_SECTION_DESCRIPTIONS,
    VALIDATION_SECTION_ORDER, GLOBAL_ENFORCEMENT_RULES,
    WORKFLOW_VALIDATIONS, RISK_DEFINITIONS
)
from app.data.guide_content import MNR_EXCLUDED_SECTIONS

router = APIRouter(prefix="/staff/validation", tags=["Staff Validation"])


@router.get("/pages")
async def get_validation_pages(db: Session = Depends(get_db)):
    pages = db.query(StaffMenuRegistry).filter(
        StaffMenuRegistry.is_active == True,
        StaffMenuRegistry.sidebar_section.isnot(None),
        StaffMenuRegistry.sidebar_section != '',
        StaffMenuRegistry.sidebar_section.notin_(MNR_EXCLUDED_SECTIONS),
        StaffMenuRegistry.sidebar_section_order < 100
    ).order_by(
        StaffMenuRegistry.sidebar_section_order,
        StaffMenuRegistry.display_order
    ).all()

    section_map = {}
    for page in pages:
        sec_id = page.sidebar_section
        if sec_id not in section_map:
            sec_desc = VALIDATION_SECTION_DESCRIPTIONS.get(sec_id, {})
            section_map[sec_id] = {
                "id": sec_id,
                "title": page.sidebar_section_title or sec_id.replace("-", " ").title(),
                "order": page.sidebar_section_order or 0,
                "description": sec_desc.get("description", ""),
                "icon": sec_desc.get("icon", page.menu_icon or "fas fa-folder"),
                "risk_level": sec_desc.get("risk_level", "medium"),
                "pages": []
            }

        val = STAFF_VALIDATION_CONTENT.get(page.menu_code, {})
        section_map[sec_id]["pages"].append({
            "menu_code": page.menu_code,
            "menu_name": page.menu_name,
            "route_path": page.route_path,
            "menu_icon": page.menu_icon or "fas fa-file",
            "description": page.menu_description or "",
            "validation": {
                "risk_level": val.get("risk_level", "low"),
                "ui_components": val.get("ui_components", []),
                "field_rules": val.get("field_rules", []),
                "button_validations": val.get("button_validations", []),
                "backend_checks": val.get("backend_checks", []),
                "mobile_parity": val.get("mobile_parity", []),
                "risks": val.get("risks", [])
            }
        })

    ordered = []
    seen = set()
    for sec_id in VALIDATION_SECTION_ORDER:
        if sec_id in section_map:
            ordered.append(section_map[sec_id])
            seen.add(sec_id)
    for sec_id, sec_data in section_map.items():
        if sec_id not in seen:
            ordered.append(sec_data)

    total_risks = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    for sec in ordered:
        for pg in sec["pages"]:
            for r in pg["validation"].get("risks", []):
                lvl = r.get("level", "low")
                if lvl in total_risks:
                    total_risks[lvl] += 1

    return {
        "total_sections": len(ordered),
        "total_pages": sum(len(s["pages"]) for s in ordered),
        "risk_summary": total_risks,
        "risk_definitions": RISK_DEFINITIONS,
        "global_enforcement": GLOBAL_ENFORCEMENT_RULES,
        "workflow_validations": WORKFLOW_VALIDATIONS,
        "sections": ordered
    }
