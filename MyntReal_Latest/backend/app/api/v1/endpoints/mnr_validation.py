"""
DC Protocol: MNR System Validation API
Serves dynamic validation/enforcement data for MNR pages from StaffMenuRegistry + MNR validation content.
Covers financial correctness, approval chains, status transitions, and enterprise risk.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.staff import StaffMenuRegistry
from app.data.guide_content import MNR_EXCLUDED_SECTIONS
from app.data.mnr_validation_content import (
    MNR_VALIDATION_CONTENT, MNR_VALIDATION_SECTION_DESCRIPTIONS,
    MNR_VALIDATION_SECTION_ORDER, MNR_GLOBAL_ENFORCEMENT_RULES,
    MNR_WORKFLOW_VALIDATIONS, MNR_RISK_DEFINITIONS
)

router = APIRouter(prefix="/mnr/validation", tags=["MNR Validation"])


@router.get("/pages")
async def get_mnr_validation_pages(db: Session = Depends(get_db)):
    pages = db.query(StaffMenuRegistry).filter(
        StaffMenuRegistry.is_active == True,
        StaffMenuRegistry.sidebar_section.isnot(None),
        StaffMenuRegistry.sidebar_section != '',
        StaffMenuRegistry.sidebar_section.in_(MNR_EXCLUDED_SECTIONS),
    ).order_by(
        StaffMenuRegistry.sidebar_section_order,
        StaffMenuRegistry.display_order
    ).all()

    section_map = {}
    for page in pages:
        sec_id = page.sidebar_section
        if sec_id not in section_map:
            sec_desc = MNR_VALIDATION_SECTION_DESCRIPTIONS.get(sec_id, {})
            section_map[sec_id] = {
                "id": sec_id,
                "title": page.sidebar_section_title or sec_id.replace("-", " ").replace("_", " ").title(),
                "order": page.sidebar_section_order or 0,
                "description": sec_desc.get("description", ""),
                "icon": sec_desc.get("icon", page.menu_icon or "fas fa-folder"),
                "risk_level": sec_desc.get("risk_level", "moderate"),
                "pages": []
            }

        val = MNR_VALIDATION_CONTENT.get(page.menu_code, {})
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
    for sec_id in MNR_VALIDATION_SECTION_ORDER:
        if sec_id in section_map:
            ordered.append(section_map[sec_id])
            seen.add(sec_id)
    for sec_id, sec_data in section_map.items():
        if sec_id not in seen:
            ordered.append(sec_data)

    total_risks = {"critical": 0, "major": 0, "moderate": 0, "low": 0}
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
        "risk_definitions": MNR_RISK_DEFINITIONS,
        "global_enforcement": MNR_GLOBAL_ENFORCEMENT_RULES,
        "workflow_validations": MNR_WORKFLOW_VALIDATIONS,
        "sections": ordered
    }
