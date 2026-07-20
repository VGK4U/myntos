"""
User Update Guard Middleware
Checks if user-initiated updates are allowed based on RVZ controls
"""

from fastapi import HTTPException
from sqlalchemy.orm import Session
from app.models.system_control import SystemControl

def check_user_update_allowed(db: Session, feature_name: str):
    """
    Check if a user update feature is currently allowed
    Raises HTTPException if paused
    """
    # Check master control first
    master_allowed = SystemControl.get_feature_status(db, 'user_all_updates')
    if not master_allowed:
        raise HTTPException(
            status_code=423,  # 423 Locked
            detail="All user updates are currently paused. Please try again later or contact support."
        )
    
    # Check individual feature
    feature_allowed = SystemControl.get_feature_status(db, feature_name)
    if not feature_allowed:
        raise HTTPException(
            status_code=423,  # 423 Locked
            detail="This update is temporarily disabled. Please try again later or contact support."
        )
    
    return True
