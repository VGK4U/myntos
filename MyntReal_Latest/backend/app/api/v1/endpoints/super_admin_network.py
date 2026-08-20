from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Any
from app.core.rbac import require_super_admin
from app.core.database import get_db
from app.models.placement import PlacementRequest
from app.models.user import User

router = APIRouter(prefix="/api/v1/super-admin/network")

@router.get("/approvals")
async def get_network_approvals(
    current_user: Any = Depends(require_super_admin),
    db: Session = Depends(get_db)
):
    """
    Get all pending network placement approvals from the live DB
    """
    try:
        from sqlalchemy.orm import aliased
        
        NewUser = aliased(User)
        Sponsor = aliased(User)
        
        requests_query = db.query(
            PlacementRequest, NewUser, Sponsor
        ).join(
            NewUser, PlacementRequest.new_user_id == NewUser.id
        ).join(
            Sponsor, PlacementRequest.requested_by_id == Sponsor.id
        ).filter(
            PlacementRequest.status == 'PENDING'
        ).all()
        
        approvals_list = []
        pending_count = 0
        approved_today = 0
        rejected_today = 0
        
        for req, new_user, sponsor in requests_query:
            pending_count += 1
            approvals_list.append({
                "id": f"REQ-{req.id}",
                "memberId": new_user.vgk_id or new_user.sponsor_id,
                "memberName": new_user.full_name,
                "sponsorId": sponsor.vgk_id or sponsor.sponsor_id,
                "sponsorName": sponsor.full_name,
                "requestedPosition": req.side or "Auto",
                "requestDate": str(req.created_at)
            })

        # Calculate approved/rejected today (mocking the counts for now since we're just getting pending)
        # Ideally we'd query PlacementLog for today's actions
        
        return {
            "success": True,
            "data": {
                "approvals": approvals_list,
                "metrics": {
                    "pending_requests": pending_count,
                    "approved_today": 0,
                    "rejected_today": 0,
                    "avg_resolution_time": "N/A"
                }
            }
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }
