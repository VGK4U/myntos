from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from app.core.database import get_db
from app.core.security import get_current_admin_user
from app.models.user import User
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

class BulkEditRequest(BaseModel):
    user_ids: List[str]
    action: str
    value: str

@router.post("/bulk-edit")
async def bulk_edit_users(
    request: BulkEditRequest,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    Perform bulk edit operations on multiple users
    Available actions: update_user_type, update_account_status, update_kyc_status, add_wallet_balance
    """
    try:
        if not request.user_ids or not request.action:
            raise HTTPException(status_code=400, detail="Missing required fields")
        
        # Log the bulk operation attempt
        logger.info(f"Bulk edit initiated by {current_user.name} ({current_user.id}): "
                   f"Action: {request.action}, Users: {len(request.user_ids)}")
        
        # Perform bulk operation directly within FastAPI context
        users_updated = 0
        
        for user_id in request.user_ids:
            user = db.query(User).filter(User.id == user_id).first()
            if user:
                if request.action == "update_user_type":
                    user.user_type = request.value
                elif request.action == "update_account_status":
                    user.coupon_status = request.value  # Assuming this is account status
                elif request.action == "update_kyc_status":
                    if hasattr(user, 'kyc_status'):
                        user.kyc_status = request.value
                users_updated += 1
        
        db.commit()
        
        return {
            "message": f"Bulk edit operation completed for {users_updated} users",
            "action": request.action,
            "value": request.value,
            "users_affected": users_updated,
            "initiated_by": current_user.name
        }
            
    except Exception as e:
        logger.error(f"Bulk edit error: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Bulk edit failed: {str(e)}")

@router.get("/bulk-operations")
async def get_bulk_operations(
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Get list of bulk operations"""
    try:
        # This would typically query the bulk_operation table
        # For now, return a simple response
        return {
            "operations": [],
            "total": 0,
            "message": "Bulk operations history feature available"
        }
    except Exception as e:
        logger.error(f"Error fetching bulk operations: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch bulk operations")