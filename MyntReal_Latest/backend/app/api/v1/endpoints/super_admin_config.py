from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Any
from app.core.rbac import require_super_admin
from app.core.database import get_db
from app.models.banner import PopupMessage

router = APIRouter(prefix="/api/v1/super-admin/config")

@router.get("/popups")
async def get_config_popups(
    current_user: Any = Depends(require_super_admin),
    db: Session = Depends(get_db)
):
    """
    Get all global popups configuration from live DB
    """
    try:
        popups_query = db.query(PopupMessage).all()
        
        popups_list = []
        active_count = 0
        
        for popup in popups_query:
            if popup.is_active:
                active_count += 1
                
            popups_list.append({
                "id": f"POP-{popup.id}",
                "title": popup.title,
                "target": popup.target_audience or "Global (All Users)",
                "type": popup.type or "Image + Text",
                "status": "ACTIVE" if popup.is_active else "INACTIVE",
                "views": popup.view_count or 0,
                "clicks": popup.click_count or 0
            })

        return {
            "success": True,
            "data": {
                "popups": popups_list,
                "metrics": {
                    "active_broadcasts": active_count,
                    "total_impressions": sum([p.view_count or 0 for p in popups_query]),
                    "avg_ctr": "Calculated via Analytics"
                }
            }
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }
