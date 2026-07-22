"""
RVZ ID Exclusive: System Controls Management
Allows RVZ ID to toggle critical system features ON/OFF
"""

from fastapi import APIRouter, Depends, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.orm import Session
from typing import Dict, Any
from datetime import datetime

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.system_control import SystemControl
from app.models.user import User

router = APIRouter()

RVZ_ID = "MNR182364369"

@router.get("/rvz/system-controls", response_class=HTMLResponse)
async def system_controls_landing(user_id: str, db: Session = Depends(get_db)):
    """System Controls Landing Page - RVZ ID ONLY"""
    html_content = """
    <div class="container-fluid">
        <h2 class="mb-4">⚙️ System Controls Hub</h2>
        <p class="lead">Central control panel for critical system operations</p>
        <div class="row g-4">
            <div class="col-md-6 col-lg-4">
                <div class="card h-100">
                    <div class="card-body">
                        <h5 class="card-title">🔧 Rate Configuration</h5>
                        <p class="card-text">Manage system-wide rates and percentages</p>
                        <a href="/rvz/rate-configuration" class="btn btn-primary">Configure Rates</a>
                    </div>
                </div>
            </div>
            <div class="col-md-6 col-lg-4">
                <div class="card h-100">
                    <div class="card-body">
                        <h5 class="card-title">🚨 Emergency Wallet</h5>
                        <p class="card-text">Emergency wallet management controls</p>
                        <a href="/rvz/emergency-wallet" class="btn btn-warning">Emergency Access</a>
                    </div>
                </div>
            </div>
            <div class="col-md-6 col-lg-4">
                <div class="card h-100">
                    <div class="card-body">
                        <h5 class="card-title">💰 Daily Ceiling</h5>
                        <p class="card-text">Set and monitor daily transaction limits</p>
                        <a href="/rvz/daily-ceiling" class="btn btn-info">Manage Ceiling</a>
                    </div>
                </div>
            </div>
        </div>
    </div>
    """
    return HTMLResponse(content=html_content)

def validate_rvz_access(user: User) -> User:
    """Validate RVZ ID access - EXCLUSIVE to MNR182364369"""
    # DC Protocol: Menu-based access control - page assignment = full access
    # if user.id != RVZ_ID:
    #     raise HTTPException(
    #         status_code=403,
    #         detail="Access Denied: System Controls are exclusive to RVZ ID"
    #     )
    
    return user

@router.post("/rvz/system-controls/toggle")
async def toggle_system_feature(
    
    feature_name: str = Form(...),
    action: str = Form(...),
    reason: str = Form(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Toggle system feature ON/OFF - RVZ ID ONLY"""
    try:
        user = validate_rvz_access(current_user)
        
        if feature_name not in ['kyc_processing', 'income_calculations', 'payout_system']:
            return JSONResponse(
                status_code=400,
                content={"success": False, "message": "Invalid feature name"}
            )
        
        if action == "pause":
            success = SystemControl.pause_feature(
                db, 
                feature_name, 
                user.id, 
                reason or f"Paused by RVZ ID for maintenance"
            )
            action_text = "paused"
        elif action == "resume":
            success = SystemControl.resume_feature(
                db, 
                feature_name, 
                user.id, 
                reason or f"Resumed by RVZ ID"
            )
            action_text = "activated"
        else:
            return JSONResponse(
                status_code=400,
                content={"success": False, "message": "Invalid action"}
            )
        
        if success:
            return JSONResponse(content={
                "success": True,
                "message": f"Feature '{feature_name.replace('_', ' ').title()}' successfully {action_text}"
            })
        else:
            return JSONResponse(
                status_code=500,
                content={"success": False, "message": "Failed to update feature status"}
            )
            
    except HTTPException as he:
        return JSONResponse(status_code=he.status_code, content={"success": False, "message": he.detail})
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "message": str(e)})

@router.get("/rvz/system-controls/status")
async def get_system_status(
    user_id: str,
    db: Session = Depends(get_db)
):
    """Get current status of all system features - RVZ ID ONLY"""
    try:
        current_user = db.query(User).filter(User.mnr_id == user_id).first()
        if current_user:
            validate_rvz_access(current_user)
        
        feature_status = SystemControl.get_all_features_status(db)
        
        return JSONResponse(content={
            "success": True,
            "features": {
                'kyc_processing': feature_status.get('kyc_processing', True),
                'income_calculations': feature_status.get('income_calculations', True),
                'payout_system': feature_status.get('payout_system', True)
            }
        })
        
    except HTTPException as he:
        return JSONResponse(status_code=he.status_code, content={"success": False, "message": he.detail})
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "message": str(e)})

# ========== KYC/BANKING SKIP CONTROLS (DC Protocol) ==========

@router.get("/rvz/system-controls/kyc-skip")
async def get_kyc_skip_settings(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current KYC and Banking skip settings - RVZ ID ONLY"""
    try:
        validate_rvz_access(current_user)
        
        from app.models.system_control import AppSettings
        skip_settings = AppSettings.get_kyc_skip_settings(db)
        
        return JSONResponse(content={
            "success": True,
            "settings": {
                "skip_kyc_requirement": skip_settings.get('skip_kyc_requirement', False),
                "skip_bank_requirement": skip_settings.get('skip_bank_requirement', False)
            }
        })
        
    except HTTPException as he:
        return JSONResponse(status_code=he.status_code, content={"success": False, "message": he.detail})
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "message": str(e)})

@router.post("/rvz/system-controls/kyc-skip/update")
async def update_kyc_skip_settings(
    skip_kyc: str = Form(None),
    skip_bank: str = Form(None),
    reason: str = Form(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update KYC and Banking skip settings - RVZ ID ONLY (DC Protocol)"""
    try:
        user = validate_rvz_access(current_user)
        
        from app.models.system_control import AppSettings
        from app.core.audit import AuditLogger
        
        # Convert string to boolean
        skip_kyc_bool = skip_kyc == 'true' if skip_kyc is not None else None
        skip_bank_bool = skip_bank == 'true' if skip_bank is not None else None
        
        # Get current settings for audit trail
        current_settings = AppSettings.get_kyc_skip_settings(db)
        
        # Update settings (DC Protocol - AppSettings is single source of truth)
        success = AppSettings.update_kyc_skip_settings(
            db, 
            skip_kyc=skip_kyc_bool, 
            skip_bank=skip_bank_bool, 
            modified_by=user.id
        )
        
        if not success:
            return JSONResponse(
                status_code=500,
                content={"success": False, "message": "Failed to update KYC skip settings"}
            )
        
        # Get updated settings
        new_settings = AppSettings.get_kyc_skip_settings(db)
        
        # Audit logging (DC Protocol requirement)
        changes = {}
        if skip_kyc_bool is not None:
            changes['skip_kyc_requirement'] = {
                'old': current_settings.get('skip_kyc_requirement'),
                'new': new_settings.get('skip_kyc_requirement')
            }
        if skip_bank_bool is not None:
            changes['skip_bank_requirement'] = {
                'old': current_settings.get('skip_bank_requirement'),
                'new': new_settings.get('skip_bank_requirement')
            }
        
        AuditLogger.log_action(
            db=db,
            user=user,
            action='KYC_SKIP_SETTINGS_UPDATE',
            resource_type='SystemSettings',
            resource_id='kyc_banking_skip',
            details={
                'changes': changes,
                'reason': reason or 'RVZ ID system control update'
            }
        )
        
        return JSONResponse(content={
            "success": True,
            "message": "KYC/Banking skip settings updated successfully",
            "settings": new_settings
        })
        
    except HTTPException as he:
        return JSONResponse(status_code=he.status_code, content={"success": False, "message": he.detail})
    except Exception as e:
        db.rollback()
        return JSONResponse(status_code=500, content={"success": False, "message": str(e)})
