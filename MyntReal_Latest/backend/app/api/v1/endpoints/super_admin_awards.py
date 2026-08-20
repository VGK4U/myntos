from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Any
from app.core.rbac import require_super_admin
from app.core.database import get_db
from app.models.awards import UserAwardProgress
from app.models.user import User

router = APIRouter(prefix="/api/v1/super-admin/awards")

@router.get("/")
async def get_awards_procurement(
    current_user: Any = Depends(require_super_admin),
    db: Session = Depends(get_db)
):
    """
    Get all pending awards for procurement from the live DB
    """
    try:
        awards_query = db.query(UserAwardProgress, User).join(
            User, UserAwardProgress.user_id == User.id
        ).all()
        
        awards_list = []
        pending_count = 0
        ready_count = 0
        delivered_count = 0
        total_cost = 0.0

        for progress, user in awards_query:
            status = progress.claim_status or 'PENDING_PROCUREMENT'
            
            if status == 'PENDING_PROCUREMENT':
                pending_count += 1
            elif status == 'READY_FOR_DELIVERY':
                ready_count += 1
            elif status == 'DELIVERED':
                delivered_count += 1
                
            awards_list.append({
                "id": f"AWD-{progress.id}",
                "memberId": user.vgk_id or user.sponsor_id,
                "memberName": user.full_name,
                "awardType": "Dynamic Award", # Fallback for now until tier join is added
                "requirement": "Met",
                "status": status,
                "requestDate": str(progress.claim_date) if progress.claim_date else str(progress.created_at)
            })

        return {
            "success": True,
            "data": {
                "awards": awards_list,
                "metrics": {
                    "pending": pending_count,
                    "ready": ready_count,
                    "delivered": delivered_count,
                    "total_cost": "Calculated via Ledger"
                }
            }
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }
