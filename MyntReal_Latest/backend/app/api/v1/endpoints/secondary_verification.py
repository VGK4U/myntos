from fastapi import APIRouter, Depends, HTTPException, Request, status, Body
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, timedelta
import secrets

from app.core.database import get_db
from app.core.security import get_current_user, get_current_user_hybrid
from app.models.user import User
from app.models.super_admin_session import SuperAdminSession

router = APIRouter()

class SetupSecondaryPasswordRequest(BaseModel):
    current_password: str = Field(..., min_length=1)
    secondary_password: str = Field(..., min_length=6)

class VerifySecondaryRequest(BaseModel):
    secondary_password: str = Field(..., min_length=1)
    operation_type: str = Field(..., min_length=1)

def generate_session_token() -> str:
    """Generate a secure random session token"""
    return secrets.token_urlsafe(32)

@router.post('/setup-secondary-password')
def setup_secondary_password(
    data: SetupSecondaryPasswordRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_hybrid)
):
    """
    Setup or update secondary password for Super Admin and RVZ ID
    Requires current password verification
    """
    # DC Protocol: Menu-based access control - page assignment = full access
    # if (getattr(current_user, 'staff_type', None) or (getattr(current_user, 'staff_type', None) or getattr(current_user, 'user_type', ''))) not in ['Super Admin', 'RVZ ID']:
    #     raise HTTPException(
    #         status_code=status.HTTP_403_FORBIDDEN,
    #         detail='Only Super Admin and RVZ ID can setup secondary password'
    #     )
    
    # Verify current password
    from werkzeug.security import check_password_hash
    if not check_password_hash(current_user.password, data.current_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Current password is incorrect'
        )
    
    # Set secondary password
    current_user.set_secondary_password(data.secondary_password)
    db.commit()
    
    return {
        'success': True,
        'message': 'Secondary password setup successfully'
    }

@router.post('/verify-secondary')
def verify_secondary_password(
    data: VerifySecondaryRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_hybrid)
):
    """
    Verify secondary password and create authentication session
    Returns session token for dangerous operations
    """
    # DC Protocol: Menu-based access control - page assignment = full access
    # if (getattr(current_user, 'staff_type', None) or (getattr(current_user, 'staff_type', None) or getattr(current_user, 'user_type', ''))) not in ['Super Admin', 'RVZ ID']:
    #     raise HTTPException(
    #         status_code=status.HTTP_403_FORBIDDEN,
    #         detail='Only Super Admin and RVZ ID can use secondary verification'
    #     )
    
    # Check if secondary password is set
    if not current_user.has_secondary_password():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Secondary password not set. Please setup secondary password first'
        )
    
    # Verify secondary password
    if not current_user.check_secondary_password(data.secondary_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Secondary password is incorrect'
        )
    
    # Clean up expired sessions
    db.query(SuperAdminSession).filter_by(admin_id=current_user.id).filter(
        SuperAdminSession.expires_at < datetime.utcnow()
    ).delete(synchronize_session=False)
    
    # Create new session token
    session_token = generate_session_token()
    expires_at = datetime.utcnow() + timedelta(minutes=30)
    
    admin_session = SuperAdminSession(
        admin_id=current_user.id,
        session_token=session_token,
        operation_type=data.operation_type,
        is_verified=True,
        verified_at=datetime.utcnow(),
        expires_at=expires_at,
        ip_address=request.client.host if request.client else None
    )
    
    db.add(admin_session)
    db.commit()
    
    return {
        'success': True,
        'message': 'Secondary verification successful',
        'session_token': session_token,
        'expires_at': expires_at.isoformat(),
        'operation_type': data.operation_type
    }

@router.get('/check-secondary-status')
def check_secondary_status(
    current_user: User = Depends(get_current_user_hybrid)
):
    """
    Check if Super Admin or RVZ ID has secondary password configured
    """
    # DC Protocol: Menu-based access control - page assignment = full access
    # if (getattr(current_user, 'staff_type', None) or (getattr(current_user, 'staff_type', None) or getattr(current_user, 'user_type', ''))) not in ['Super Admin', 'RVZ ID']:
    #     raise HTTPException(
    #         status_code=status.HTTP_403_FORBIDDEN,
    #         detail='Only Super Admin and RVZ ID can check secondary status'
    #     )
    
    return {
        'success': True,
        'has_secondary_password': current_user.has_secondary_password()
    }
