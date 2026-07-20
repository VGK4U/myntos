"""
DC Protocol: Staff System Guide API
Serves dynamic guide content from StaffMenuRegistry + guide_content data.
Pages auto-appear when added to the registry. MNR sections excluded.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.staff import StaffMenuRegistry
from app.data.guide_content import (
    GUIDE_CONTENT, SECTION_DESCRIPTIONS, SECTION_ORDER, MNR_EXCLUDED_SECTIONS
)

router = APIRouter(prefix="/staff/guide", tags=["Staff Guide"])


@router.get("/pages")
async def get_guide_pages(db: Session = Depends(get_db)):
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
            sec_desc = SECTION_DESCRIPTIONS.get(sec_id, {})
            section_map[sec_id] = {
                "id": sec_id,
                "title": page.sidebar_section_title or sec_id.replace("-", " ").title(),
                "order": page.sidebar_section_order or 0,
                "description": sec_desc.get("description", ""),
                "icon": sec_desc.get("icon", page.menu_icon or "fas fa-folder"),
                "pages": []
            }

        guide = GUIDE_CONTENT.get(page.menu_code, {})
        section_map[sec_id]["pages"].append({
            "menu_code": page.menu_code,
            "menu_name": page.menu_name,
            "route_path": page.route_path,
            "menu_icon": page.menu_icon or "fas fa-file",
            "description": page.menu_description or "",
            "guide": {
                "purpose": guide.get("purpose", ""),
                "who_can_access": guide.get("who_can_access", ""),
                "main_sections": guide.get("main_sections", []),
                "usage_flow": guide.get("usage_flow", []),
                "fields": guide.get("fields", []),
                "statuses": guide.get("statuses", []),
                "tips": guide.get("tips", []),
                "common_mistakes": guide.get("common_mistakes", [])
            }
        })

    ordered = []
    seen = set()
    for sec_id in SECTION_ORDER:
        if sec_id in section_map:
            ordered.append(section_map[sec_id])
            seen.add(sec_id)
    for sec_id, sec_data in section_map.items():
        if sec_id not in seen:
            ordered.append(sec_data)

    return {
        "total_sections": len(ordered),
        "total_pages": sum(len(s["pages"]) for s in ordered),
        "sections": ordered
    }
