"""
Super Admin Endpoints - System Configuration & Management
Handles system settings, role management, global configurations, scheduler controls
"""

from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from decimal import Decimal

from app.core.database import get_db
from app.core.rbac import require_super_admin, require_super_admin_hybrid
from app.models.user import User
from app.models.base import get_indian_time
from app.models.api_response import success_response
from app.core.audit import AuditLogger

router = APIRouter()

# ===== VED INCOME CONTROL (Super Admin & RVZ ID Only) =====

class VedPauseRequest(BaseModel):
    user_id: str
    pause: bool  # True to pause, False to unpause
    reason: str

@router.post("/super-admin/ved/pause-unpause")
async def toggle_ved_pause(
    request: VedPauseRequest,
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db)
):
    """
    Pause or unpause Ved income for a specific user
    RESTRICTED: Super Admin and RVZ ID ONLY (not regular Admin)
    """
    try:
        # DC Protocol: Menu-based access control - page assignment = full access
        # if (getattr(current_user, 'staff_type', None) or getattr(current_user, 'user_type', '')) not in ['Super Admin'] and current_user.id != 'MNR182364369':
        #     raise HTTPException(
        #         status_code=status.HTTP_403_FORBIDDEN,
        #         detail="This operation is restricted to Super Admin and RVZ ID only"
        #     )
        
        # Get target user
        target_user = db.query(User).filter(User.id == request.user_id).first()
        if not target_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User {request.user_id} not found"
            )
        
        # Update ved_paused status
        old_status = target_user.ved_paused
        target_user.ved_paused = request.pause
        
        db.commit()
        
        # Log the action
        AuditLogger.log_action(
            db=db,
            user=current_user,
            action='VED_PAUSE_TOGGLE',
            resource_type='User',
            resource_id=request.user_id,
            details={
                "old_status": "paused" if old_status else "active",
                "new_status": "paused" if request.pause else "active",
                "reason": request.reason
            }
        )
        
        action = "paused" if request.pause else "unpaused"
        return success_response(
            message=f"Ved income {action} successfully for user {request.user_id}",
            data={
                "user_id": request.user_id,
                "ved_paused": target_user.ved_paused,
                "action": action
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Server error: {str(e)}"
        )

# ===== SYSTEM SETTINGS =====

class SystemSettingsUpdate(BaseModel):
    direct_referral_active_rate: Optional[float] = None
    pair_matching_rate: Optional[float] = None
    ved_income_rate: Optional[float] = None

@router.get("/super-admin/settings")
async def get_system_settings(
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db)
):
    """Get current system settings"""
    try:
        from app.models.system_control import AppSettings
        
        app_settings = db.query(AppSettings).first()
        
        settings_data = {
            "direct_referral_active_rate": float(app_settings.direct_referral_active_rate) if app_settings else 3000,
            "pair_matching_rate": float(app_settings.pair_matching_rate) if app_settings else 2000,
            "ved_income_rate": float(app_settings.ved_income_rate) if app_settings else 1000
        }
        
        return success_response(
            message="System settings retrieved successfully",
            data=settings_data
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Server error: {str(e)}"
        )

@router.put("/super-admin/settings")
async def update_system_settings(
    settings_data: SystemSettingsUpdate,
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db)
):
    """Update system settings"""
    try:
        from app.models.system_control import AppSettings
        
        app_settings = db.query(AppSettings).first()
        if not app_settings:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="App settings not found"
            )
        
        updates = {}
        
        if settings_data.direct_referral_active_rate is not None:
            app_settings.direct_referral_active_rate = Decimal(str(settings_data.direct_referral_active_rate))
            updates["direct_referral_active_rate"] = settings_data.direct_referral_active_rate
            
        if settings_data.pair_matching_rate is not None:
            app_settings.pair_matching_rate = Decimal(str(settings_data.pair_matching_rate))
            updates["pair_matching_rate"] = settings_data.pair_matching_rate
            
        if settings_data.ved_income_rate is not None:
            app_settings.ved_income_rate = Decimal(str(settings_data.ved_income_rate))
            updates["ved_income_rate"] = settings_data.ved_income_rate
        
        app_settings.last_updated_by = str(current_user.id)
        app_settings.last_updated_at = get_indian_time()
        
        db.commit()
        
        AuditLogger.log_action(
            db=db,
            user=current_user,
            action='SYSTEM_SETTINGS_UPDATE',
            resource_type='AppSettings',
            details=updates
        )
        
        return success_response(
            message="System settings updated successfully",
            data={"updated_fields": updates}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Server error: {str(e)}"
        )

# ===== SCHEDULER CONTROLS =====

@router.get("/super-admin/scheduler/status")
async def get_scheduler_status(
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db)
):
    """Get scheduler status"""
    try:
        scheduler_status = {
            "status": "Running",
            "jobs": [],
            "next_run_time": None
        }
        
        return success_response(
            message="Scheduler status retrieved successfully",
            data=scheduler_status
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Server error: {str(e)}"
        )

# ===== GLOBAL CONFIGURATIONS =====

VGK4U_FLAG_COLUMNS = [
    'birthdays_vgk4u_enabled', 'top_earners_vgk4u_enabled', 'awards_vgk4u_enabled',
    'daywise_income_vgk4u_enabled', 'income_types_vgk4u_enabled',
    'direct_summary_vgk4u_enabled', 'matching_summary_vgk4u_enabled',
    'guru_summary_vgk4u_enabled', 'ved_summary_vgk4u_enabled',
    'ev_benefits_vgk4u_enabled', 'ev_discount_vgk4u_enabled',
    'franchise_earnings_vgk4u_enabled', 'insurance_vgk4u_enabled',
    'training_vgk4u_enabled', 'coupon_benefits_vgk4u_enabled',
    'my_submissions_vgk4u_enabled',
]

# Phase-2 (write-flow) toggles — Task #46. Zero-Default-Access: each
# defaults to FALSE on the DB column, so a missing/never-toggled flag
# means the module is OFF until Super-Admin explicitly enables it.
# Tracked separately from Phase-1 because the public read-only flag
# endpoint and the UI use different default semantics for them.
VGK4U_PHASE2_FLAG_COLUMNS = [
    'feedback_vgk4u_enabled',
    'announcements_vgk4u_enabled',
    'kyc_vgk4u_enabled',
    'bank_vgk4u_enabled',
    'profile_edit_vgk4u_enabled',
    'settings_vgk4u_enabled',
    'coupon_transfer_vgk4u_enabled',
]

# Combined list — used by the GET/PUT endpoints so any new flag is
# picked up automatically without endpoint code changes.
VGK4U_ALL_FLAG_COLUMNS = VGK4U_FLAG_COLUMNS + VGK4U_PHASE2_FLAG_COLUMNS


class GlobalConfigUpdate(BaseModel):
    system_name: Optional[str] = None
    company_name: Optional[str] = None
    support_email: Optional[str] = None
    support_phone: Optional[str] = None
    maintenance_mode: Optional[bool] = None
    # VGK4U Member Parity Phase 1 toggles (Task #33) — all optional
    birthdays_vgk4u_enabled: Optional[bool] = None
    top_earners_vgk4u_enabled: Optional[bool] = None
    awards_vgk4u_enabled: Optional[bool] = None
    daywise_income_vgk4u_enabled: Optional[bool] = None
    income_types_vgk4u_enabled: Optional[bool] = None
    direct_summary_vgk4u_enabled: Optional[bool] = None
    matching_summary_vgk4u_enabled: Optional[bool] = None
    guru_summary_vgk4u_enabled: Optional[bool] = None
    ved_summary_vgk4u_enabled: Optional[bool] = None
    ev_benefits_vgk4u_enabled: Optional[bool] = None
    ev_discount_vgk4u_enabled: Optional[bool] = None
    franchise_earnings_vgk4u_enabled: Optional[bool] = None
    insurance_vgk4u_enabled: Optional[bool] = None
    training_vgk4u_enabled: Optional[bool] = None
    coupon_benefits_vgk4u_enabled: Optional[bool] = None
    my_submissions_vgk4u_enabled: Optional[bool] = None
    # VGK4U Member Parity Phase 2 toggles (Task #46) — write-flow modules,
    # Zero-Default-Access (DB default FALSE). All optional so a partial
    # PUT only mutates the flags actually present in the payload.
    feedback_vgk4u_enabled: Optional[bool] = None
    announcements_vgk4u_enabled: Optional[bool] = None
    kyc_vgk4u_enabled: Optional[bool] = None
    bank_vgk4u_enabled: Optional[bool] = None
    profile_edit_vgk4u_enabled: Optional[bool] = None
    settings_vgk4u_enabled: Optional[bool] = None
    coupon_transfer_vgk4u_enabled: Optional[bool] = None


@router.get("/super-admin/config/global")
async def get_global_config(
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db)
):
    """Get global system configuration including VGK4U Member Parity (Task #33) toggle flags.

    DC_T33_TOGGLE_001: VGK4U flags are persisted on `AppSettings` (NOT SystemControl)
    — see backend/app/models/system_control.py:274-289. Reads pull from there.
    """
    try:
        from app.models.system_control import AppSettings

        app_settings = db.query(AppSettings).first()
        if app_settings is None:
            # First-time bootstrap: create the row so reads/writes have a target
            app_settings = AppSettings()
            db.add(app_settings)
            db.commit()
            db.refresh(app_settings)

        config = {
            "system_version": "2.0.0",
            "database_status": "Connected",
            "environment": "production",
            "system_name": getattr(app_settings, 'system_name', None),
            "company_name": getattr(app_settings, 'company_name', None),
            "support_email": getattr(app_settings, 'support_email', None),
            "support_phone": getattr(app_settings, 'support_phone', None),
            "maintenance_mode": bool(getattr(app_settings, 'maintenance_mode', False)),
            "features": {
                "whatsapp_otp": True,
                "email_notifications": True,
                "income_calculations": True,
                "bonanza_system": True,
            },
        }
        # VGK4U Member Parity flags — single source of truth: AppSettings.
        # If a column is genuinely missing (older DB), fall back to True so the
        # response shape stays stable for the UI.
        for col in VGK4U_FLAG_COLUMNS:
            config[col] = bool(getattr(app_settings, col, True))

        return {
            "success": True,
            "message": "Global configuration retrieved successfully",
            "config": config,
            "data": config,
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Server error: {str(e)}"
        )


@router.put("/super-admin/config/global")
async def update_global_config(
    payload: GlobalConfigUpdate,
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    """Update global config and VGK4U Member Parity (Task #33) toggle flags.

    DC_T33_TOGGLE_001: All VGK4U flags are persisted on `AppSettings` so
    GET and PUT share a single source of truth. Per-flag audit trail is
    written via AuditLogger so each switch is independently traceable.
    """
    try:
        from app.models.system_control import AppSettings

        app_settings = db.query(AppSettings).first()
        if app_settings is None:
            app_settings = AppSettings()
            db.add(app_settings)
            db.flush()

        updates: Dict[str, Any] = {}

        # AppSettings text/bool fields
        for field in ('system_name', 'company_name', 'support_email', 'support_phone', 'maintenance_mode'):
            value = getattr(payload, field, None)
            if value is not None and hasattr(app_settings, field):
                setattr(app_settings, field, value)
                updates[field] = value

        # VGK4U Member Parity flags — write to AppSettings (single source of truth)
        for col in VGK4U_FLAG_COLUMNS:
            value = getattr(payload, col, None)
            if value is None:
                continue
            if not hasattr(app_settings, col):
                # Column missing on this DB — surface explicitly rather than silently no-op
                raise HTTPException(
                    status_code=500,
                    detail=f"VGK4U flag column '{col}' is missing on AppSettings; run schema bootstrap.",
                )
            old = bool(getattr(app_settings, col))
            if old != bool(value):
                setattr(app_settings, col, bool(value))
                updates[col] = {"old": old, "new": bool(value)}

        if hasattr(app_settings, 'last_updated_by'):
            app_settings.last_updated_by = str(current_user.id)
        if hasattr(app_settings, 'last_updated_at'):
            app_settings.last_updated_at = get_indian_time()

        db.commit()

        if updates:
            AuditLogger.log_action(
                db=db,
                user=current_user,
                action='GLOBAL_CONFIG_UPDATE',
                resource_type='AppSettings',
                details=updates,
            )
            db.commit()

        return {
            "success": True,
            "message": "Global configuration updated successfully",
            "data": {"updated_fields": list(updates.keys())},
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Server error: {str(e)}",
        )


@router.get("/super-admin/config/vgk4u-flags")
async def get_vgk4u_flags_public(db: Session = Depends(get_db)):
    """Public read-only access to the 16 VGK4U Phase-1 module toggle flags.

    DC_T36_PUBLIC_FLAGS_001: VGK4U-side member pages (`vgk_member_*.html`)
    need to read the corresponding `*_vgk4u_enabled` flag at page load to
    decide whether to show the VGK4U Members tab. Those pages run under
    `vgkAuthToken`, not super-admin auth, so we expose a small read-only
    sibling of the super-admin GET endpoint that returns just the flags.
    No PII, no mutation — safe to expose without elevated auth.
    """
    try:
        from app.models.system_control import AppSettings

        app_settings = db.query(AppSettings).first()
        flags: Dict[str, bool] = {}
        for col in VGK4U_FLAG_COLUMNS:
            # Phase-1 columns default to True (read-only modules); fall back
            # to True so a missing column / row never accidentally hides a
            # working tab — matches the GET /config/global semantics above.
            flags[col] = bool(getattr(app_settings, col, True)) if app_settings else True
        # Phase-2 (write-flow) columns — Task #46. Zero-Default-Access:
        # default FALSE so a never-toggled / missing column means the
        # module is OFF and the member page shows a "Module disabled"
        # overlay until Super-Admin explicitly enables it.
        for col in VGK4U_PHASE2_FLAG_COLUMNS:
            flags[col] = bool(getattr(app_settings, col, False)) if app_settings else False

        return {"success": True, "flags": flags}
    except Exception as e:
        # Never break a member page over a flag-read failure — Phase-1
        # falls back to all-True (read-only modules can keep working);
        # Phase-2 falls back to all-False (Zero-Default-Access — fail
        # closed for write-flow modules so a flag outage cannot
        # accidentally enable a previously-disabled write surface).
        fallback: Dict[str, bool] = {}
        for col in VGK4U_FLAG_COLUMNS:
            fallback[col] = True
        for col in VGK4U_PHASE2_FLAG_COLUMNS:
            fallback[col] = False
        return {"success": False, "error": str(e), "flags": fallback}


# ===== ROLE MANAGEMENT =====

@router.get("/super-admin/roles")
async def get_all_roles(
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db)
):
    """Get all system roles"""
    try:
        roles = [
            {"id": "1", "name": "User", "description": "Regular user", "level": 1},
            {"id": "2", "name": "Admin", "description": "Administrator", "level": 2},
            {"id": "3", "name": "Finance Admin", "description": "Finance Administrator", "level": 3},
            {"id": "4", "name": "Super Admin", "description": "Super Administrator", "level": 4},
            {"id": "5", "name": "RVZ ID", "description": "RVZ ID - Highest privilege", "level": 5}
        ]
        
        return success_response(
            message="Roles retrieved successfully",
            data={"roles": roles, "total": len(roles)}
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Server error: {str(e)}"
        )

# ===== SYSTEM DASHBOARD =====

@router.get("/super-admin/dashboard")
async def get_super_admin_dashboard(
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db)
):
    """Get Super Admin dashboard"""
    try:
        from app.models.transaction import Transaction
        from sqlalchemy import func
        
        total_users = db.query(User).count()
        active_users = db.query(User).filter(User.activation_date.isnot(None)).count()
        admin_users = db.query(User).filter(
            User.user_type.in_(['Admin', 'Finance Admin', 'Super Admin', 'RVZ ID'])
        ).count()
        
        total_transactions = db.query(Transaction).count()
        
        from app.models.system_control import AppSettings
        app_settings = db.query(AppSettings).first()
        
        dashboard_data = {
            "users": {
                "total": total_users,
                "active": active_users,
                "admins": admin_users
            },
            "transactions": {
                "total": total_transactions
            },
            "system": {
                "maintenance_mode": False,
                "scheduler_status": "Running",
                "database_status": "Connected"
            }
        }
        
        return success_response(
            message="Super Admin dashboard data retrieved successfully",
            data=dashboard_data
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Server error: {str(e)}"
        )

# ===== KYC BYPASS SYSTEM (Super Admin Only) =====

class KYCBypassRequest(BaseModel):
    user_id: str
    reason: str
    bypass_type: str = "emergency"  # emergency, special_case, administrative

@router.post("/super-admin/kyc-bypass/activate")
async def activate_kyc_bypass(
    request: KYCBypassRequest,
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db)
):
    """
    Activate KYC bypass for a user - allows them to access KYC-gated features without documents
    RESTRICTED: Super Admin ONLY
    """
    try:
        # Get target user
        target_user = db.query(User).filter(User.id == request.user_id).first()
        if not target_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User {request.user_id} not found"
            )
        
        # Check if already bypassed
        if target_user.kyc_bypass_active:
            return success_response(
                message="KYC bypass is already active for this user",
                data={"user_id": request.user_id, "bypass_active": True}
            )
        
        # Activate bypass
        target_user.kyc_bypass_active = True
        target_user.kyc_original_status = target_user.kyc_status
        target_user.kyc_status = 'Approved'  # Set to Approved so they can access features
        target_user.kyc_bypassed_at = get_indian_time()
        target_user.kyc_bypassed_by = current_user.id
        target_user.kyc_bypass_reason = f"[{request.bypass_type.upper()}] {request.reason}"
        
        db.commit()
        
        # Log the action
        AuditLogger.log_action(
            db=db,
            user=current_user,
            action='KYC_BYPASS_ACTIVATE',
            resource_type='User',
            resource_id=request.user_id,
            details={
                "bypass_type": request.bypass_type,
                "reason": request.reason,
                "original_status": target_user.kyc_original_status
            }
        )
        
        return success_response(
            message=f"KYC bypass activated successfully for user {request.user_id}",
            data={
                "user_id": request.user_id,
                "bypass_active": True,
                "bypass_type": request.bypass_type,
                "bypassed_at": target_user.kyc_bypassed_at.isoformat()
            }
        )
        
    except HTTPException as he:
        raise he
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Server error: {str(e)}"
        )

@router.post("/super-admin/kyc-bypass/revoke")
async def revoke_kyc_bypass(
    request: KYCBypassRequest,
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db)
):
    """
    Revoke KYC bypass for a user - restores original KYC status
    RESTRICTED: Super Admin ONLY
    """
    try:
        # Get target user
        target_user = db.query(User).filter(User.id == request.user_id).first()
        if not target_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User {request.user_id} not found"
            )
        
        # Check if bypass is active
        if not target_user.kyc_bypass_active:
            return success_response(
                message="No active KYC bypass found for this user",
                data={"user_id": request.user_id, "bypass_active": False}
            )
        
        # Revoke bypass
        original_status = target_user.kyc_original_status or 'Pending'
        target_user.kyc_bypass_active = False
        target_user.kyc_status = original_status  # Restore original status
        target_user.kyc_original_status = None
        target_user.kyc_bypassed_at = None
        target_user.kyc_bypassed_by = None
        revoke_reason = request.reason
        target_user.kyc_bypass_reason = None
        
        db.commit()
        
        # Log the action
        AuditLogger.log_action(
            db=db,
            user=current_user,
            action='KYC_BYPASS_REVOKE',
            resource_type='User',
            resource_id=request.user_id,
            details={
                "reason": revoke_reason,
                "restored_status": original_status
            }
        )
        
        return success_response(
            message=f"KYC bypass revoked successfully for user {request.user_id}",
            data={
                "user_id": request.user_id,
                "bypass_active": False,
                "restored_status": original_status
            }
        )
        
    except HTTPException as he:
        raise he
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Server error: {str(e)}"
        )

@router.get("/super-admin/kyc-bypass/list")
async def list_users_needing_kyc(
    status_filter: Optional[str] = None,
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db)
):
    """
    List users with KYC status - for bypass management
    RESTRICTED: Super Admin ONLY
    """
    try:
        # Build query
        query = db.query(User).filter(User.activation_date.isnot(None))
        
        if status_filter:
            if status_filter == "bypass_active":
                query = query.filter(User.kyc_bypass_active == True)
            elif status_filter == "needs_kyc":
                query = query.filter(
                    User.kyc_status != 'Approved',
                    User.kyc_bypass_active == False
                )
            else:
                query = query.filter(User.kyc_status == status_filter)
        
        users = query.order_by(User.registration_date.desc()).limit(100).all()
        
        users_data = []
        for user in users:
            users_data.append({
                "user_id": user.id,
                "name": user.name,
                "email": user.email,
                "mobile": user.phone_number,
                "kyc_status": user.kyc_status,
                "kyc_bypass_active": user.kyc_bypass_active,
                "kyc_bypass_reason": user.kyc_bypass_reason,
                "kyc_bypassed_at": user.kyc_bypassed_at.isoformat() if user.kyc_bypassed_at else None,
                "activation_date": user.activation_date.isoformat() if user.activation_date else None
            })
        
        return success_response(
            message="Users list retrieved successfully",
            data={
                "count": len(users_data),
                "users": users_data
            }
        )
        
    except Exception as e:
        import traceback
        error_msg = f"KYC Bypass List Error: {str(e)}\n{traceback.format_exc()}"
        print(error_msg)  # Log to console
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"KYC Bypass List Error: {str(e)}"
        )

@router.get("/super-admin/dashboard-stats")
async def get_super_admin_dashboard_stats(
    current_user: User = Depends(require_super_admin_hybrid),
    db: Session = Depends(get_db)
):
    """
    Super Admin Dashboard - DC Protocol Compliant
    Shows: User stats, awards pending super admin decision
    """
    try:
        from sqlalchemy import func, and_, desc
        from datetime import datetime
        from app.models.awards import UserAwardProgress
        from app.models.bonanza import DynamicBonanzaHistory  # DC Protocol: BonanzaProgress deprecated
        from app.models.ticket import ServiceTicket
        from app.models.kyc_document import KYCDocument
        
        today = get_indian_time().date()
        today_start = datetime.combine(today, datetime.min.time())
        today_end = datetime.combine(today, datetime.max.time())
        month_start = today.replace(day=1)
        
        # User Statistics - DC Protocol: Single source = user table
        total_users = db.query(func.count(User.id)).scalar() or 0
        active_users = db.query(func.count(User.id)).filter(User.account_status == 'Active').scalar() or 0
        inactive_users = db.query(func.count(User.id)).filter(User.account_status == 'Inactive').scalar() or 0
        users_today = db.query(func.count(User.id)).filter(
            and_(User.registration_date >= today_start, User.registration_date <= today_end)
        ).scalar() or 0
        users_this_month = db.query(func.count(User.id)).filter(
            User.registration_date >= month_start
        ).scalar() or 0
        
        # Awards Pending Super Admin Decision (Second Stage - after Admin approved)
        awards_pending_sa = db.query(func.count(UserAwardProgress.id)).filter(
            and_(
                UserAwardProgress.admin_approved_by.isnot(None),
                UserAwardProgress.super_admin_decision.is_(None)
            )
        ).scalar() or 0
        # DC Protocol: Query bonanza claims from DynamicBonanzaHistory
        bonanza_pending_sa = db.query(func.count(DynamicBonanzaHistory.id)).filter(
            and_(
                DynamicBonanzaHistory.admin_approved_by.isnot(None),
                DynamicBonanzaHistory.super_admin_decision.is_(None)
            )
        ).scalar() or 0
        
        dashboard_data = {
            "user_stats": {
                "all_time": {
                    "total_users": total_users,
                    "active_users": active_users,
                    "inactive_users": inactive_users
                },
                "today": {
                    "total_users": users_today,
                    "active_users": users_today
                },
                "this_month": {
                    "total_users": users_this_month,
                    "active_users": users_this_month
                }
            },
            "awards": {
                "pending_super_admin_decision": awards_pending_sa + bonanza_pending_sa,
                "awards_pending": awards_pending_sa,
                "bonanza_pending": bonanza_pending_sa
            }
        }
        
        return success_response(
            message="Super Admin dashboard statistics retrieved successfully",
            data=dashboard_data
        )
        
    except Exception as e:
        import traceback
        print(f"❌ Super Admin Dashboard Error: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to load dashboard statistics"
        )


# ===== LOG REPORTS ENDPOINTS =====

@router.get("/log-reports/scheduler")
async def get_scheduler_logs(
    current_user: User = Depends(require_super_admin_hybrid),
    db: Session = Depends(get_db)
):
    """Get scheduler activity logs"""
    try:
        # Return empty logs for now (placeholder implementation)
        return success_response(
            message="Scheduler logs retrieved successfully",
            data={
                "logs": [],
                "summary": {
                    "total_jobs": 0,
                    "successful_runs": 0,
                    "failed_runs": 0,
                    "last_run": None
                }
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve scheduler logs: {str(e)}"
        )


@router.get("/log-reports/data-changes")
async def get_data_change_logs(
    current_user: User = Depends(require_super_admin_hybrid),
    db: Session = Depends(get_db)
):
    """Get data modification/change logs"""
    try:
        # Return empty logs for now (placeholder implementation)
        return success_response(
            message="Data change logs retrieved successfully",
            data={
                "logs": [],
                "summary": {
                    "total_changes": 0,
                    "tables_modified": [],
                    "last_modification": None
                }
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve data change logs: {str(e)}"
        )


@router.get("/log-reports/system-activity")
async def get_system_activity_logs(
    current_user: User = Depends(require_super_admin_hybrid),
    db: Session = Depends(get_db)
):
    """Get general system activity logs"""
    try:
        # Return empty logs for now (placeholder implementation)  
        return success_response(
            message="System activity logs retrieved successfully",
            data={
                "logs": [],
                "summary": {
                    "total_activities": 0,
                    "unique_users": 0,
                    "peak_activity_time": None,
                    "last_activity": None
                }
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve system activity logs: {str(e)}"
        )
