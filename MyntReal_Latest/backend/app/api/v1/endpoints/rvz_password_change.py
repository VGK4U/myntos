"""
RVZ Password Change API Endpoints
Allows RVZ ID to change ANY user's password with secondary password verification
"""

from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request, Body
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from pydantic import BaseModel
from datetime import datetime

from app.core.database import get_db
from app.core.security import SecurityManager, get_current_user, get_current_user_hybrid
from app.models.user import User
from app.models.system_log import DataChangeLog
from app.core import rvz_protection

router = APIRouter()

# Pydantic models
class PasswordChangeRequest(BaseModel):
    target_user_id: str
    new_password: str
    reason: Optional[str] = "RVZ ID admin password reset"

class UserSearchRequest(BaseModel):
    search_term: str

@router.get("/stats")
async def get_password_change_stats(
    current_user: User = Depends(get_current_user_hybrid),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get statistics for RVZ password change page
    RVZ ID and Super Admin (skip-level manager pattern - Dec 24, 2025)
    """
    # DC Protocol: Menu-based access control - page assignment = full access
    # if (getattr(current_user, 'staff_type', None) or (getattr(current_user, 'staff_type', None) or getattr(current_user, 'user_type', ''))) not in ['RVZ ID', 'Super Admin']:
    #     raise HTTPException(
    #         status_code=status.HTTP_403_FORBIDDEN,
    #         detail="Access denied. RVZ ID or Super Admin privileges required."
    #     )
    
    # Get statistics
    total_users = db.query(func.count(User.id)).scalar() or 0
    admin_users = db.query(func.count(User.id)).filter(
        User.user_type.in_(['Admin', 'Super Admin', 'Finance Admin', 'RVZ ID'])
    ).scalar() or 0
    regular_users = db.query(func.count(User.id)).filter(
        User.user_type == 'Member'  # Updated: User type migrated to Member
    ).scalar() or 0
    active_users = db.query(func.count(User.id)).filter(
        User.account_status == 'Active'
    ).scalar() or 0
    
    return {
        "success": True,
        "stats": {
            "total_users": total_users,
            "admin_users": admin_users,
            "regular_users": regular_users,
            "active_users": active_users
        }
    }

@router.post("/search-users")
async def search_users(
    search_request: UserSearchRequest,
    current_user: User = Depends(get_current_user_hybrid),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Search for users by User ID or name
    RVZ ID and Super Admin (skip-level manager pattern - Dec 24, 2025)
    """
    # DC Protocol: Menu-based access control - page assignment = full access
    # if (getattr(current_user, 'staff_type', None) or (getattr(current_user, 'staff_type', None) or getattr(current_user, 'user_type', ''))) not in ['RVZ ID', 'Super Admin']:
    #     raise HTTPException(
    #         status_code=status.HTTP_403_FORBIDDEN,
    #         detail="Access denied. RVZ ID or Super Admin privileges required."
    #     )
    
    search_term = search_request.search_term.strip()
    
    if not search_term:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Search term cannot be empty"
        )
    
    # Search by exact User ID or partial name match
    users = db.query(User).filter(
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
                "user_type": user.user_type,
                "account_status": user.account_status,
                "registration_date": user.registration_date.isoformat() if user.registration_date else None
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
    Get recently registered users for quick access
    RVZ ID and Super Admin (skip-level manager pattern - Dec 24, 2025)
    """
    # DC Protocol: Menu-based access control - page assignment = full access
    # if (getattr(current_user, 'staff_type', None) or (getattr(current_user, 'staff_type', None) or getattr(current_user, 'user_type', ''))) not in ['RVZ ID', 'Super Admin']:
    #     raise HTTPException(
    #         status_code=status.HTTP_403_FORBIDDEN,
    #         detail="Access denied. RVZ ID or Super Admin privileges required."
    #     )
    
    # Get 20 most recent users
    recent_users = db.query(User).order_by(
        User.registration_date.desc()
    ).limit(20).all()
    
    return {
        "success": True,
        "users": [
            {
                "user_id": user.id,
                "name": user.name,
                "user_type": user.user_type,
                "registration_date": user.registration_date.isoformat() if user.registration_date else None
            }
            for user in recent_users
        ]
    }

@router.post("/change-password")
async def change_user_password(
    password_change: PasswordChangeRequest = Body(...),
    request: Request = None,
    current_user: User = Depends(get_current_user_hybrid),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Change any user's password
    RVZ ID and Super Admin (skip-level manager pattern - Dec 24, 2025)
    CRITICAL: All password changes are logged for audit
    """
    # DC Protocol: Menu-based access control - page assignment = full access
    # if (getattr(current_user, 'staff_type', None) or (getattr(current_user, 'staff_type', None) or getattr(current_user, 'user_type', ''))) not in ['RVZ ID', 'Super Admin']:
    #     raise HTTPException(
    #         status_code=status.HTTP_403_FORBIDDEN,
    #         detail="Access denied. RVZ ID or Super Admin privileges required."
    #     )
    
    # Find target user
    target_user = db.query(User).filter(
        User.id == password_change.target_user_id
    ).first()
    
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {password_change.target_user_id} not found"
        )
    
    # Validate new password
    if len(password_change.new_password) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 6 characters long"
        )
    
    # Hash new password
    new_password_hash = SecurityManager.get_password_hash(password_change.new_password)
    
    # Store old password hash for audit
    old_password_hash = target_user.password
    
    # Update password
    target_user.password = new_password_hash
    
    # Get client IP
    client_ip = request.client.host if hasattr(request, 'client') else 'unknown'
    
    # LAYER 2: Create audit log using DataChangeLog
    audit_entry = DataChangeLog(
        table_name='user',
        record_id=target_user.id,
        operation='UPDATE',
        changed_by_id=current_user.id,
        changed_by_role=(getattr(current_user, 'staff_type', None) or getattr(current_user, 'user_type', '')),
        changed_at=datetime.utcnow(),
        field_name='password',
        old_value='[REDACTED FOR SECURITY]',
        new_value='[REDACTED FOR SECURITY]',
        change_reason=password_change.reason,
        change_context={
            'target_user_id': target_user.id,
            'target_user_name': target_user.name,
            'target_user_type': target_user.user_type,
            'changed_by': current_user.id,
            'ip_address': client_ip,
            'operation': 'RVZ_PASSWORD_RESET',
            'timestamp': datetime.utcnow().isoformat()
        }
    )
    
    try:
        db.add(audit_entry)
        db.commit()
        
        return {
            "success": True,
            "message": f"Password changed successfully for {target_user.id} ({target_user.name})",
            "target_user": {
                "user_id": target_user.id,
                "name": target_user.name,
                "user_type": target_user.user_type
            },
            "audit_log_id": audit_entry.id if hasattr(audit_entry, 'id') else None
        }
    
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to change password: {str(e)}"
        )
