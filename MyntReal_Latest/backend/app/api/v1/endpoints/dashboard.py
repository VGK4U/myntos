"""
Dashboard endpoints for FastAPI
Preserves Flask dashboard functionality with real-time data
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User

router = APIRouter()

@router.get("/overview")
async def get_dashboard_overview(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get dashboard overview data (replaces Flask user_dashboard route)
    """
    return {
        "user": {
            "id": current_user.id,
            "name": current_user.name,
            "wallet_balance": float(getattr(current_user, 'wallet_balance', 0.0)),
            "kyc_status": current_user.kyc_status,
            "coupon_status": current_user.coupon_status
        },
        "message": "Dashboard data - more endpoints coming in migration"
    }