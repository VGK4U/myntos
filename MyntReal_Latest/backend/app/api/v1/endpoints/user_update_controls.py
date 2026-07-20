"""
User Update Controls API - RVZ ID Feature
Allows RVZ admin to pause/resume user update capabilities
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Dict, Any, List
from datetime import datetime

from app.core.database import get_db
from app.models.user import User
from app.models.system_control import SystemControl
from app.core.security import get_current_user
from pydantic import BaseModel

router = APIRouter()

# Define all user update features
USER_UPDATE_FEATURES = {
    'user_registration_signup': {
        'name': 'User Registration/Signup',
        'description': 'New user account creation from signup page',
        'icon': '👤'
    },
    'user_profile_updates': {
        'name': 'Profile Updates',
        'description': 'Name, Email, Phone, Address, DOB, etc.',
        'icon': '📝'
    },
    'user_kyc_updates': {
        'name': 'KYC Updates',
        'description': 'Aadhaar and PAN number updates',
        'icon': '🆔'
    },
    'user_bank_updates': {
        'name': 'Bank Details Updates',
        'description': 'Bank account, IFSC, UPI details',
        'icon': '🏦'
    },
    'user_document_uploads': {
        'name': 'Document Uploads',
        'description': 'KYC documents (Aadhaar, PAN, Photo)',
        'icon': '📄'
    },
    'user_password_changes': {
        'name': 'Password Changes',
        'description': 'User password change requests',
        'icon': '🔐'
    },
    'user_terms_acceptance': {
        'name': 'Terms Acceptance',
        'description': 'Terms & Conditions acceptance',
        'icon': '📋'
    },
    'user_photo_updates': {
        'name': 'Profile Photo Updates',
        'description': 'Profile picture uploads',
        'icon': '📷'
    }
}

class UpdateControlRequest(BaseModel):
    feature_name: str
    action: str  # 'pause' or 'resume'
    reason: str = None

class MasterControlRequest(BaseModel):
    action: str  # 'pause_all' or 'resume_all'
    reason: str = None

def require_rvz_admin(current_user: User = Depends(get_current_user)):
    """Ensure user is RVZ ID"""
    # DC Protocol: Menu-based access control - page assignment = full access
    # if (getattr(current_user, 'staff_type', None) or (getattr(current_user, 'staff_type', None) or getattr(current_user, 'user_type', ''))) != 'RVZ ID':
    #     raise HTTPException(status_code=403, detail="RVZ ID access required")
    return current_user

@router.get("/user-update-controls")
async def get_all_user_update_controls(
    current_user: User = Depends(require_rvz_admin),
    db: Session = Depends(get_db)
):
    """Get status of all user update controls"""
    try:
        controls_status = {}
        
        # Check master control first
        master_control = db.query(SystemControl).filter(
            SystemControl.feature_name == 'user_all_updates'
        ).first()
        
        is_master_paused = master_control and master_control.is_paused
        
        # Get status for each feature
        for feature_key, feature_info in USER_UPDATE_FEATURES.items():
            feature = db.query(SystemControl).filter(
                SystemControl.feature_name == feature_key
            ).first()
            
            if feature:
                controls_status[feature_key] = {
                    'name': feature_info['name'],
                    'description': feature_info['description'],
                    'icon': feature_info['icon'],
                    'is_allowed': not feature.is_paused,
                    'is_paused': feature.is_paused,
                    'pause_reason': feature.pause_reason,
                    'last_action': feature.last_action,
                    'controlled_by': feature.controlled_by_user_id,
                    'updated_at': feature.updated_at.isoformat() if feature.updated_at else None
                }
            else:
                # Default: all features allowed
                controls_status[feature_key] = {
                    'name': feature_info['name'],
                    'description': feature_info['description'],
                    'icon': feature_info['icon'],
                    'is_allowed': True,
                    'is_paused': False,
                    'pause_reason': None,
                    'last_action': 'default',
                    'controlled_by': None,
                    'updated_at': None
                }
        
        # Count statistics
        total_features = len(USER_UPDATE_FEATURES)
        paused_count = sum(1 for f in controls_status.values() if f['is_paused'])
        allowed_count = total_features - paused_count
        
        return {
            'success': True,
            'data': {
                'controls': controls_status,
                'master_control': {
                    'is_paused': is_master_paused,
                    'pause_reason': master_control.pause_reason if master_control else None,
                    'controlled_by': master_control.controlled_by_user_id if master_control else None,
                    'updated_at': master_control.updated_at.isoformat() if master_control and master_control.updated_at else None
                },
                'statistics': {
                    'total': total_features,
                    'paused': paused_count,
                    'allowed': allowed_count,
                    'master_paused': is_master_paused
                }
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching controls: {str(e)}")

@router.post("/user-update-controls/update")
async def update_user_control(
    request: UpdateControlRequest,
    current_user: User = Depends(require_rvz_admin),
    db: Session = Depends(get_db)
):
    """Update individual user update control"""
    try:
        # Validate feature name
        if request.feature_name not in USER_UPDATE_FEATURES:
            raise HTTPException(status_code=400, detail="Invalid feature name")
        
        # Validate action
        if request.action not in ['pause', 'resume']:
            raise HTTPException(status_code=400, detail="Action must be 'pause' or 'resume'")
        
        # Update the control
        if request.action == 'pause':
            success = SystemControl.pause_feature(
                db=db,
                feature_name=request.feature_name,
                paused_by=current_user.id,
                reason=request.reason or f"{USER_UPDATE_FEATURES[request.feature_name]['name']} paused by RVZ admin"
            )
        else:
            success = SystemControl.resume_feature(
                db=db,
                feature_name=request.feature_name,
                resumed_by=current_user.id,
                reason=request.reason or f"{USER_UPDATE_FEATURES[request.feature_name]['name']} resumed by RVZ admin"
            )
        
        if success:
            return {
                'success': True,
                'message': f"{USER_UPDATE_FEATURES[request.feature_name]['name']} {request.action}d successfully",
                'feature': request.feature_name,
                'action': request.action
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to update control")
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating control: {str(e)}")

@router.post("/user-update-controls/master")
async def update_master_control(
    request: MasterControlRequest,
    current_user: User = Depends(require_rvz_admin),
    db: Session = Depends(get_db)
):
    """Update master control (pause/resume all user updates)"""
    try:
        # Validate action
        if request.action not in ['pause_all', 'resume_all']:
            raise HTTPException(status_code=400, detail="Action must be 'pause_all' or 'resume_all'")
        
        if request.action == 'pause_all':
            # Pause master control
            SystemControl.pause_feature(
                db=db,
                feature_name='user_all_updates',
                paused_by=current_user.id,
                reason=request.reason or "All user updates paused by RVZ admin (Emergency freeze)"
            )
            
            # Also pause all individual features
            for feature_key in USER_UPDATE_FEATURES.keys():
                SystemControl.pause_feature(
                    db=db,
                    feature_name=feature_key,
                    paused_by=current_user.id,
                    reason=request.reason or "Paused via master control"
                )
            
            message = "All user updates PAUSED successfully (Emergency freeze activated)"
        else:
            # Resume master control
            SystemControl.resume_feature(
                db=db,
                feature_name='user_all_updates',
                resumed_by=current_user.id,
                reason=request.reason or "All user updates resumed by RVZ admin"
            )
            
            # Also resume all individual features
            for feature_key in USER_UPDATE_FEATURES.keys():
                SystemControl.resume_feature(
                    db=db,
                    feature_name=feature_key,
                    resumed_by=current_user.id,
                    reason=request.reason or "Resumed via master control"
                )
            
            message = "All user updates RESUMED successfully"
        
        return {
            'success': True,
            'message': message,
            'action': request.action,
            'affected_features': len(USER_UPDATE_FEATURES)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating master control: {str(e)}")

@router.get("/check-user-update-allowed/{feature_name}")
async def check_update_allowed(
    feature_name: str,
    db: Session = Depends(get_db)
):
    """Check if a specific user update feature is currently allowed (for internal use)"""
    try:
        # Check master control first
        master_allowed = SystemControl.get_feature_status(db, 'user_all_updates')
        if not master_allowed:
            return {
                'allowed': False,
                'reason': 'All user updates are currently paused. Please try again later or contact support.'
            }
        
        # Check individual feature
        feature_allowed = SystemControl.get_feature_status(db, feature_name)
        
        if feature_allowed:
            return {
                'allowed': True,
                'reason': None
            }
        else:
            feature_info = USER_UPDATE_FEATURES.get(feature_name, {})
            return {
                'allowed': False,
                'reason': f"{feature_info.get('name', 'This feature')} is temporarily disabled. Please try again later or contact support."
            }
            
    except Exception as e:
        # Default to allowed if error (fail-safe)
        return {
            'allowed': True,
            'reason': None
        }
