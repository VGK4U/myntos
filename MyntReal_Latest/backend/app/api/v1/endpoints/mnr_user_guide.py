"""
DC Protocol: MNR Member Portal User Guide API
Dynamic guide for MNR member-facing pages, pulled from StaffMenuRegistry.
Accessible to authenticated MNR members.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.staff import StaffMenuRegistry
from app.data.mnr_guide_content import MNR_GUIDE_CONTENT

router = APIRouter(prefix="/mnr/user-guide", tags=["MNR User Guide"])

MNR_USER_PORTAL_SECTIONS = ["mnr-user"]

USER_SECTION_META = {
    "mnr-user": {
        "description": "Complete reference for your MNR Member Portal — income, wallets, withdrawals, benefits, profile, and more.",
        "icon": "fas fa-user-circle"
    }
}


@router.get("/pages")
async def get_mnr_user_guide_pages(db: Session = Depends(get_db)):
    pages = db.query(StaffMenuRegistry).filter(
        StaffMenuRegistry.is_active == True,
        StaffMenuRegistry.sidebar_section.isnot(None),
        StaffMenuRegistry.sidebar_section != '',
        StaffMenuRegistry.sidebar_section.in_(MNR_USER_PORTAL_SECTIONS),
    ).order_by(
        StaffMenuRegistry.sidebar_section_order,
        StaffMenuRegistry.display_order
    ).all()

    section_map = {}
    for page in pages:
        sec_id = page.sidebar_section
        if sec_id not in section_map:
            meta = USER_SECTION_META.get(sec_id, {})
            section_map[sec_id] = {
                "id": sec_id,
                "title": page.sidebar_section_title or "Member Portal",
                "description": meta.get("description", ""),
                "icon": meta.get("icon", "fas fa-folder"),
                "pages": []
            }

        guide = MNR_GUIDE_CONTENT.get(page.menu_code, {})
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

    sections = list(section_map.values())

    return {
        "total_sections": len(sections),
        "total_pages": sum(len(s["pages"]) for s in sections),
        "sections": sections
    }
