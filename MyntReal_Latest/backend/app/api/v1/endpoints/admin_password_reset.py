"""
Admin/Super Admin Password Reset API
Allows Admin and Super Admin to reset regular user passwords
Restricted to User type only (cannot change admin passwords)
"""

from typing import Dict, Any, Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from pydantic import BaseModel, validator
from datetime import datetime
import pytz

from app.core.database import get_db
from app.core.security import get_current_user_hybrid, HybridUserContext
from app.core.security import SecurityManager as _SM_APR
from app.models.user import User
from app.models.system_log import DataChangeLog

router = APIRouter()

# Pydantic models
class PasswordResetRequest(BaseModel):
    target_user_id: str
    new_password: str
    reason: Optional[str] = "Admin password reset"
    
    @validator('new_password')
    def validate_password(cls, v):
        if len(v) < 6:
            raise ValueError('Password must be at least 6 characters long')
        return v

class UserSearchRequest(BaseModel):
    search_term: str

@router.get("/stats")
async def get_password_reset_stats(
    current_user: User = Depends(get_current_user_hybrid),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get statistics for Admin password reset page
    Admin and Super Admin ONLY
    """
    # Verify Admin or Super Admin access using HybridUserContext
    ctx = HybridUserContext(current_user)
    if not ctx.has_admin_access():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Admin or Super Admin privileges required."
        )
    
    # Get statistics (regular users and members - NOT admins)
    total_users = db.query(func.count(User.id)).filter(
        User.user_type == 'Member'  # Updated: User type migrated to Member
    ).scalar() or 0
    
    active_users = db.query(func.count(User.id)).filter(
        User.user_type == 'Member',  # Updated: User type migrated to Member
        User.account_status == 'Active'
    ).scalar() or 0
    
    inactive_users = db.query(func.count(User.id)).filter(
        User.user_type == 'Member',  # Updated: User type migrated to Member
        User.account_status == 'Inactive'
    ).scalar() or 0
    
    return {
        "success": True,
        "stats": {
            "total_users": total_users,
            "active_users": active_users,
            "inactive_users": inactive_users
        }
    }

@router.post("/search-users")
async def search_users(
    search_request: UserSearchRequest,
    current_user: User = Depends(get_current_user_hybrid),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Search for regular users by MNR ID or name
    Admin and Super Admin ONLY
    Returns regular users only (User type)
    """
    # Verify Admin or Super Admin access using HybridUserContext
    ctx = HybridUserContext(current_user)
    if not ctx.has_admin_access():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Admin or Super Admin privileges required."
        )
    
    search_term = search_request.search_term.strip()
    
    if not search_term:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Search term cannot be empty"
        )
    
    # Search by exact User ID or partial name match (MEMBERS - NOT ADMINS)
    users = db.query(User).filter(
        User.user_type == 'Member',  # Updated: User type migrated to Member
        or_(
            User.id == search_term.upper(),
            User.name.ilike(f'%{search_term}%')
        )
    ).limit(50).all()
    
    return {
        "success": True,
        "search_term": search_term,
        "results": [
            {
                "user_id": user.id,
                "name": user.name,
                "email": user.email,
                "account_status": user.account_status,
                "registration_date": user.registration_date.isoformat() if user.registration_date else None,
                "activation_date": user.activation_date.isoformat() if user.activation_date else None
            }
            for user in users
        ],
        "count": len(users)
    }

@router.get("/recent-users")
async def get_recent_users(
    current_user: User = Depends(get_current_user_hybrid),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get recently registered regular users for quick access
    Admin and Super Admin ONLY
    """
    # Verify Admin or Super Admin access using HybridUserContext
    ctx = HybridUserContext(current_user)
    if not ctx.has_admin_access():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Admin or Super Admin privileges required."
        )
    
    # Get 20 most recent members (NOT admins)
    recent_users = db.query(User).filter(
        User.user_type == 'Member'  # Updated: User type migrated to Member
    ).order_by(
        User.registration_date.desc()
    ).limit(20).all()
    
    return {
        "success": True,
        "users": [
            {
                "user_id": user.id,
                "name": user.name,
                "email": user.email,
                "account_status": user.account_status,
                "registration_date": user.registration_date.isoformat() if user.registration_date else None
            }
            for user in recent_users
        ]
    }

@router.post("/password-reset")
async def reset_user_password(
    reset_request: PasswordResetRequest,
    current_user: User = Depends(get_current_user_hybrid),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Reset a regular user's password
    Admin and Super Admin ONLY
    Cannot reset admin user passwords - only regular users
    """
    # Verify Admin or Super Admin access using HybridUserContext
    ctx = HybridUserContext(current_user)
    if not ctx.has_admin_access():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Admin or Super Admin privileges required."
        )
    
    # Find target user
    target_user = db.query(User).filter(User.id == reset_request.target_user_id).first()
    
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {reset_request.target_user_id} not found"
        )
    
    # CRITICAL: Verify target is a regular user or member (not admin)
    if target_user.user_type not in ['User', 'Member']:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Cannot reset password for {target_user.user_type} accounts. Only User and Member passwords can be reset."
        )
    
    # DC Protocol (Apr 21, 2026): Route through SecurityManager — consistent pbkdf2:sha256
    hashed_password = _SM_APR.get_password_hash(reset_request.new_password)
    
    # Update password
    old_password_hash = target_user.password
    target_user.password = hashed_password
    
    # Create audit log with Indian timezone
    ist = pytz.timezone('Asia/Kolkata')
    current_time_ist = datetime.now(ist)
    
    audit_log = DataChangeLog(
        table_name='user',
        record_id=target_user.id,
        operation='PASSWORD_RESET',
        changed_by_id=ctx.user_id,
        changed_by_role=ctx.user_type,
        changed_at=current_time_ist,
        field_name='password',
        old_value='[HIDDEN]',
        new_value='[HIDDEN]',
        change_reason=reset_request.reason
    )
    
    try:
        db.add(audit_log)
        db.commit()
        db.refresh(target_user)
        
        return {
            "success": True,
            "message": f"Password successfully reset for user {target_user.id}",
            "user": {
                "user_id": target_user.id,
                "name": target_user.name,
                "email": target_user.email
            },
            "changed_by": {
                "admin_id": ctx.user_id,
                "admin_name": ctx.user_name,
                "admin_type": ctx.user_type
            },
            "timestamp": audit_log.changed_at.isoformat()
        }
    
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reset password: {str(e)}"
        )

@router.get("/audit-logs")
async def get_password_reset_audit_logs(
    limit: int = 50,
    current_user: User = Depends(get_current_user_hybrid),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get recent password reset audit logs
    Admin and Super Admin ONLY
    """
    # Verify Admin or Super Admin access using HybridUserContext
    ctx = HybridUserContext(current_user)
    if not ctx.has_admin_access():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Admin or Super Admin privileges required."
        )
    
    # Get recent password reset logs
    logs = db.query(DataChangeLog).filter(
        DataChangeLog.operation == 'PASSWORD_RESET'
    ).order_by(
        DataChangeLog.changed_at.desc()
    ).limit(limit).all()
    
    return {
        "success": True,
        "logs": [
            {
                "user_id": log.record_id,
                "changed_by": log.changed_by_id,
                "reason": log.change_reason,
                "timestamp": log.changed_at.isoformat() if log.changed_at else None
            }
            for log in logs
        ],
        "count": len(logs)
    }
