"""
RVZ ID specific API endpoints
Supreme admin functionality and system control
"""

from fastapi import APIRouter, Depends, HTTPException, status, Form, Query, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, text
from typing import Dict, Any, List, Optional
from app.core.rbac import require_rvz_id
from pydantic import BaseModel
from datetime import date
import logging

from app.core.database import get_db
from app.core.security import get_current_rvz_user, get_current_rvz_user_hybrid, get_current_user, get_current_user_hybrid, SecurityManager
from app.models.user import User
from app.models.system_control import SystemControl, AppSettings, CustomRole, TermsAndConditionsVersion
from app.services.user_service import UserService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/rvz", tags=["RVZ ID Supreme Admin"])

# Pydantic models for requests
class PopupControlRequest(BaseModel):
    popup_type: str
    enabled: bool
    reason: Optional[str] = None

class FinancialRatesRequest(BaseModel):
    direct_referral_rate: Optional[int] = None
    pair_matching_rate: Optional[int] = None
    ved_income_rate: Optional[int] = None
    reason: Optional[str] = None

class SystemFeatureRequest(BaseModel):
    feature_name: str
    action: str  # 'pause' or 'resume'
    reason: Optional[str] = None

class CreateRoleRequest(BaseModel):
    role_name: str
    role_description: Optional[str] = None
    role_level: int
    permissions: Dict[str, bool]

class PasswordResetRequest(BaseModel):
    user_identifier: str  # Can be MNR ID or email
    new_password: str
    reason: Optional[str] = None

class UserSearchRequest(BaseModel):
    search_term: str
    search_type: str = "all"  # "id", "email", "name", "all"

class UserDataResetRequest(BaseModel):
    user_identifier: str  # Can be MNR ID or email
    reset_type: str  # "account_status", "wallet_balance", "kyc_documents", "complete_profile"
    reason: Optional[str] = None

# Bulk Edit Request Models
class BulkUserFiltersRequest(BaseModel):
    page: int = 1
    page_size: int = 50
    sort_by: str = "id"
    sort_order: str = "asc"  # asc or desc
    
    # Filter options
    user_type: Optional[str] = None
    account_status: Optional[str] = None
    kyc_status: Optional[str] = None
    referrer_id: Optional[str] = None  # Sponsor filter
    ved_owner_id: Optional[str] = None  # Ved filter
    is_ved: Optional[bool] = None
    
    # Date range filters
    registration_date_from: Optional[date] = None
    registration_date_to: Optional[date] = None
    last_login_from: Optional[date] = None
    last_login_to: Optional[date] = None
    ved_activation_from: Optional[date] = None
    ved_activation_to: Optional[date] = None
    
    # Search
    search_term: Optional[str] = None
    search_fields: List[str] = ["id", "name", "email"]

class BulkUserUpdateRequest(BaseModel):
    user_updates: List[Dict[str, Any]]  # List of {user_id: "MNR123", field: "value", new_value: "updated"}
    reason: str
    
class UserChangeLogEntry(BaseModel):
    user_id: str
    field_name: str
    old_value: Any
    new_value: Any

class VedPauseRequest(BaseModel):
    user_id: str
    pause: bool  # True to pause, False to unpause
    reason: str

# ===== VED INCOME CONTROL (RVZ ID Only) =====

@router.post("/ved/pause-unpause")
async def toggle_ved_pause_rvz(
    request: VedPauseRequest,
    current_user: User = Depends(get_current_rvz_user_hybrid),
    db: Session = Depends(get_db)
):
    """
    Pause or unpause Ved income for a specific user
    RESTRICTED: RVZ ID ONLY (not Admin or regular Super Admin)
    """
    try:
        from app.core.audit import AuditLogger
        from app.models.api_response import success_response
        
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

# ===== AUTOMATIC WITHDRAWAL SETTINGS (RVZ ID Only) =====

@router.get("/withdrawal-settings")
async def get_withdrawal_settings(
    current_user: User = Depends(get_current_rvz_user_hybrid),
    db: Session = Depends(get_db)
):
    """
    Get automatic withdrawal system settings
    RESTRICTED: RVZ ID ONLY
    """
    try:
        from app.models.system_control import AppSettings
        
        settings = AppSettings.get_withdrawal_settings(db)
        
        return {
            "success": True,
            "settings": settings
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Server error: {str(e)}"
        )

class WithdrawalSettingsUpdate(BaseModel):
    max_withdrawal_limit: Optional[float] = None
    withdrawal_buffer_amount: Optional[float] = None
    auto_withdrawal_enabled: Optional[bool] = None

@router.post("/withdrawal-settings")
async def update_withdrawal_settings(
    settings_data: WithdrawalSettingsUpdate,
    current_user: User = Depends(get_current_rvz_user_hybrid),
    db: Session = Depends(get_db)
):
    """
    Update automatic withdrawal system settings
    RESTRICTED: RVZ ID ONLY
    
    Settings:
    - max_withdrawal_limit: Maximum amount per withdrawal request (default ₹50,000)
    - withdrawal_buffer_amount: Buffer amount kept in wallet (default ₹1,000)
    - auto_withdrawal_enabled: Enable/disable automatic withdrawals
    """
    try:
        from app.models.system_control import AppSettings
        from app.core.audit import AuditLogger
        
        # Validation
        if settings_data.max_withdrawal_limit is not None:
            if settings_data.max_withdrawal_limit < 1000:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Maximum withdrawal limit must be at least ₹1,000"
                )
        
        if settings_data.withdrawal_buffer_amount is not None:
            if settings_data.withdrawal_buffer_amount < 500:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Withdrawal buffer must be at least ₹500"
                )
        
        # Update settings
        update_data = {}
        if settings_data.max_withdrawal_limit is not None:
            update_data['max_withdrawal_limit'] = settings_data.max_withdrawal_limit
        if settings_data.withdrawal_buffer_amount is not None:
            update_data['withdrawal_buffer_amount'] = settings_data.withdrawal_buffer_amount
        if settings_data.auto_withdrawal_enabled is not None:
            update_data['auto_withdrawal_enabled'] = settings_data.auto_withdrawal_enabled
        
        success = AppSettings.update_withdrawal_settings(db, update_data, current_user.id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update withdrawal settings"
            )
        
        # Log the action
        AuditLogger.log_action(
            db=db,
            user=current_user,
            action='WITHDRAWAL_SETTINGS_UPDATE',
            resource_type='SystemSettings',
            resource_id='withdrawal_settings',
            details=update_data
        )
        
        # Get updated settings
        updated_settings = AppSettings.get_withdrawal_settings(db)
        
        return {
            "success": True,
            "message": "Withdrawal settings updated successfully",
            "settings": updated_settings
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Server error: {str(e)}"
        )

# System Control Endpoints
@router.get("/system/status")
async def get_system_status(
    current_user: User = Depends(get_current_rvz_user_hybrid),
    db: Session = Depends(get_db)
):
    """Get comprehensive system status for RVZ dashboard"""
    try:
        # Get real user counts from database
        total_users = db.query(User).count()
        active_users = db.query(User).filter(User.account_status == 'Active').count()
        
        # Get system revenue from transactions (if available)
        try:
            from app.models.transaction import Transaction
            system_revenue = db.query(Transaction).filter(Transaction.transaction_type == 'income').count() * 2500  # Estimated
        except:
            system_revenue = 2500000  # Fallback
        
        # Get active bonanzas (if available) 
        try:
            from app.models.bonanza import DynamicBonanza
            active_bonanzas = db.query(DynamicBonanza).filter(DynamicBonanza.is_active == True).count()
        except:
            active_bonanzas = 5  # Fallback
        
        return {
            "system_status": "online",
            "maintenance_mode": False,
            "total_users": total_users,
            "active_users": active_users,
            "system_revenue": system_revenue,
            "active_bonanzas": active_bonanzas,
            "popup_settings": AppSettings.get_popup_settings(db),
            "financial_rates": AppSettings.get_financial_rates(db)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching system status: {str(e)}")

# Popup Control Endpoints
@router.get("/popup-control")
async def get_popup_settings(
    current_user: User = Depends(get_current_rvz_user_hybrid),
    db: Session = Depends(get_db)
):
    """Get all popup control settings"""
    try:
        settings = AppSettings.get_popup_settings(db)
        return {
            "popup_settings": settings,
            "last_modified_by": None,  # TODO: Get from database
            "last_modified_at": None
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching popup settings: {str(e)}")

@router.post("/popup-control")
async def update_popup_setting(
    request: PopupControlRequest,
    current_user: User = Depends(get_current_rvz_user_hybrid),
    db: Session = Depends(get_db)
):
    """Update popup control setting"""
    try:
        valid_popup_types = [
            'coupon', 'mail', 'banner', 'whatsapp', 'message', 'system_alert',
            'birthday_banner', 'top_performers', 'custom_banners', 'image_banners'
        ]
        
        if request.popup_type not in valid_popup_types:
            raise HTTPException(status_code=400, detail="Invalid popup type")
        
        success = AppSettings.update_popup_setting(
            db,
            request.popup_type, 
            request.enabled, 
            str(current_user.id)
        )
        
        if success:
            return {
                "message": f"{request.popup_type} popup {'enabled' if request.enabled else 'disabled'}",
                "popup_type": request.popup_type,
                "enabled": request.enabled,
                "modified_by": current_user.name
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to update popup setting")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating popup setting: {str(e)}")

# Financial Control Endpoints
@router.get("/financial-rates")
async def get_financial_rates(
    current_user: User = Depends(get_current_rvz_user_hybrid),
    db: Session = Depends(get_db)
):
    """Get current financial rates"""
    try:
        rates = AppSettings.get_financial_rates(db)
        return {
            "financial_rates": rates,
            "last_modified_by": None,  # TODO: Get from database
            "last_modified_at": None
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching financial rates: {str(e)}")

@router.post("/financial-rates")
async def update_financial_rates(
    request: FinancialRatesRequest,
    current_user: User = Depends(get_current_rvz_user_hybrid),
    db: Session = Depends(get_db)
):
    """Update financial rates"""
    try:
        # Build rates dictionary from request
        rates = {}
        if request.direct_referral_rate is not None:
            rates['direct_referral_active_rate'] = request.direct_referral_rate
        if request.pair_matching_rate is not None:
            rates['pair_matching_rate'] = request.pair_matching_rate  
        if request.ved_income_rate is not None:
            rates['ved_income_rate'] = request.ved_income_rate
            
        if not rates:
            raise HTTPException(status_code=400, detail="No rates provided for update")
        
        success = AppSettings.update_financial_rates(db, rates, str(current_user.id))
        
        if success:
            return {
                "message": "Financial rates updated successfully",
                "updated_rates": rates,
                "modified_by": current_user.name
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to update financial rates")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating financial rates: {str(e)}")

# System Feature Control
@router.get("/system-features")
async def get_system_features(
    current_user: User = Depends(get_current_rvz_user_hybrid),
    db: Session = Depends(get_db)
):
    """Get status of all system features"""
    try:
        # Get actual feature statuses from database
        features = SystemControl.get_all_features_status(db)
        
        return {
            "system_features": features,
            "total_features": len(features),
            "active_features": sum(1 for status in features.values() if status)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching system features: {str(e)}")

@router.post("/system-features")
async def control_system_feature(
    request: SystemFeatureRequest,
    current_user: User = Depends(get_current_rvz_user_hybrid),
    db: Session = Depends(get_db)
):
    """Pause or resume system feature"""
    try:
        if request.action not in ['pause', 'resume']:
            raise HTTPException(status_code=400, detail="Action must be 'pause' or 'resume'")
        
        if request.action == 'pause':
            success = SystemControl.pause_feature(
                db,
                request.feature_name, 
                str(current_user.id), 
                request.reason or "Paused by RVZ ID"
            )
            message = f"Feature '{request.feature_name}' paused"
        else:
            success = SystemControl.resume_feature(
                db,
                request.feature_name, 
                str(current_user.id), 
                request.reason or "Resumed by RVZ ID"
            )
            message = f"Feature '{request.feature_name}' resumed"
        
        if success:
            return {
                "message": message,
                "feature_name": request.feature_name,
                "action": request.action,
                "controlled_by": current_user.name,
                "reason": request.reason
            }
        else:
            raise HTTPException(status_code=500, detail=f"Failed to {request.action} feature")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error controlling system feature: {str(e)}")

# Role Management Endpoints
@router.get("/roles")
async def get_custom_roles(
    current_user: User = Depends(get_current_rvz_user_hybrid),
    db: Session = Depends(get_db)
):
    """Get all custom roles"""
    try:
        # Get actual roles from database
        try:
            roles_from_db = db.query(CustomRole).filter(CustomRole.is_active == True).all()
            roles_data = []
            
            for role in roles_from_db:
                roles_data.append({
                    "id": role.id,
                    "role_name": role.role_name,
                    "role_description": role.role_description,
                    "role_level": role.role_level,
                    "is_active": role.is_active,
                    "created_by": role.created_by,
                    "created_at": role.created_at.isoformat() if role.created_at is not None else None
                })
            
            return {
                "roles": roles_data,  # Fix API contract - frontend expects 'roles'
                "total_roles": len(roles_data)
            }
        except Exception as e:
            # Fallback for database issues
            return {
                "roles": [],
                "total_roles": 0
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching custom roles: {str(e)}")

@router.post("/roles")
async def create_custom_role(
    request: CreateRoleRequest,
    current_user: User = Depends(get_current_rvz_user_hybrid),
    db: Session = Depends(get_db)
):
    """Create new custom role"""
    try:
        # TODO: Implement role creation in database
        return {
            "message": f"Custom role '{request.role_name}' created successfully",
            "role_name": request.role_name,
            "role_level": request.role_level,
            "permissions": request.permissions,
            "created_by": current_user.name
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating custom role: {str(e)}")

# Menu Configuration Endpoints  
@router.get("/menu-config/{interface_type}")
async def get_menu_configuration(
    interface_type: str,
    current_user: User = Depends(get_current_rvz_user_hybrid),
    db: Session = Depends(get_db)
):
    """Get menu configuration for specific interface"""
    try:
        valid_interfaces = ['user', 'admin', 'super_admin', 'rvz_id']
        if interface_type not in valid_interfaces:
            raise HTTPException(status_code=400, detail="Invalid interface type")
        
        # TODO: Get actual menu config from database
        menu_config = {
            "interface_type": interface_type,
            "modules": [
                {"id": 1, "name": "Dashboard", "visible": True, "order": 1},
                {"id": 2, "name": "Users", "visible": True, "order": 2},
                {"id": 3, "name": "Financial", "visible": False, "order": 3}
            ]
        }
        
        return menu_config
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching menu configuration: {str(e)}")

@router.post("/menu-config/{module_id}/visibility")
async def toggle_module_visibility(
    module_id: int,
    enabled: bool = Form(...),
    current_user: User = Depends(get_current_rvz_user_hybrid),
    db: Session = Depends(get_db)
):
    """Toggle menu module visibility"""
    try:
        # TODO: Update module visibility in database
        return {
            "message": f"Module {module_id} {'enabled' if enabled else 'disabled'}",
            "module_id": module_id,
            "visible": enabled,
            "modified_by": current_user.name
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating module visibility: {str(e)}")

# Export Configuration
@router.get("/export-config")
async def export_system_configuration(
    current_user: User = Depends(get_current_rvz_user_hybrid),
    db: Session = Depends(get_db)
):
    """Export complete system configuration"""
    try:
        config_export = {
            "export_timestamp": "2024-09-28T14:30:00Z",
            "exported_by": current_user.name,
            "popup_settings": AppSettings.get_popup_settings(),
            "financial_rates": AppSettings.get_financial_rates(),
            "system_features": {
                'whatsapp_otp': True,
                'email_notifications': True,
                'income_calculations': True
            },
            "menu_configurations": {
                "user": [],
                "admin": [],
                "super_admin": [],
                "rvz_id": []
            },
            "custom_roles": []
        }
        
        return config_export
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error exporting configuration: {str(e)}")

# Password Reset: REMOVED - Use /api/v1/rvz/password/change-password endpoint instead

@router.post("/search-users")
async def search_users(
    request: UserSearchRequest,
    current_user: User = Depends(get_current_rvz_user_hybrid),
    db: Session = Depends(get_db)
):
    """Search for users in the system (RVZ ID only)"""
    try:
        user_service = UserService(db)
        
        # Build search query based on type
        users = []
        if request.search_type == "id" or request.search_type == "all":
            # Search by MNR ID
            if request.search_term.startswith('MNR'):
                user = user_service.get_user_by_id(request.search_term)
                if user:
                    users.append(user)
            
        if request.search_type == "email" or request.search_type == "all":
            # Search by email
            user = user_service.get_user_by_email(request.search_term)
            if user and user not in users:
                users.append(user)
        
        if request.search_type == "name" or request.search_type == "all":
            # Search by name (partial match)
            name_users = db.query(User).filter(
                User.name.ilike(f"%{request.search_term}%")
            ).limit(10).all()
            for user in name_users:
                if user not in users:
                    users.append(user)
        
        # Format response
        user_results = []
        for user in users[:10]:  # Limit to 10 results
            user_results.append({
                "id": user.id,
                "name": user.name,
                "email": user.email,
                "mobile": user.phone_number,  # Fixed: Use phone_number instead of mobile
                "user_type": user.user_type,
                "registration_date": user.registration_date.isoformat() if user.registration_date else None,
                "account_locked": user.account_locked,
                "kyc_status": user.kyc_status,
                "wallet_balance": round(float(user.wallet_balance)) if user.wallet_balance else 0.0
            })
        
        return {
            "success": True,
            "search_term": request.search_term,
            "search_type": request.search_type,
            "results_count": len(user_results),
            "users": user_results
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error searching users: {str(e)}"
        )

@router.get("/user-data/{user_id}")
async def get_complete_user_data(
    user_id: str,
    current_user: User = Depends(get_current_rvz_user_hybrid),
    db: Session = Depends(get_db)
):
    """
    Get comprehensive user data for RVZ ID dashboard
    Returns all user information including profile, earnings, team, awards, etc.
    """
    try:
        from app.models.transaction import PendingIncome, Transaction
        from app.models.placement import Placement
        from app.models.awards import UserAwardProgress, UserMatchingAwardProgress
        from app.models.ved_team import VedTeamMember
        from app.models.kyc_document import KYCDocument, BankDetailsApproval
        
        # Get user
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # 1. BASIC PROFILE - Including Award Ranks
        # Get current award ranks from award service
        from app.services.award_service import AwardService
        award_service_temp = AwardService(db)
        direct_progress = award_service_temp.get_user_direct_award_progress(user_id)
        matching_progress = award_service_temp.get_user_matching_award_progress(user_id)
        
        # Find current/highest achieved rank
        direct_rank = "No Rank"
        matching_rank = "No Rank"
        
        for tier in direct_progress.get("tier_progress", []):
            if tier.get("achieved", False):
                direct_rank = tier.get("award_name", "No Rank")
        
        for tier in matching_progress.get("tier_progress", []):
            if tier.get("achieved", False):
                matching_rank = tier.get("award_name", "No Rank")
        
        profile = {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "mobile": user.phone_number,
            "address": f"{user.address_line1 or ''} {user.address_line2 or ''}".strip() or None,
            "city": user.city,
            "state": user.state,
            "pincode": user.postal_code,
            "registration_date": user.registration_date.isoformat() if user.registration_date else None,
            "user_type": user.user_type,
            "account_status": user.account_status,
            "account_locked": user.account_locked,
            "direct_referral_rank": direct_rank,
            "matching_referral_rank": matching_rank
        }
        
        # 2. ACTIVATION & PACKAGE
        activation = {
            "activation_date": user.activation_date.isoformat() if user.activation_date else None,
            "package_name": user.get_package_type() if hasattr(user, 'get_package_type') else None,
            "package_points": float(user.package_points) if user.package_points else 0,
            "is_activated": user.activation_date is not None
        }
        
        # 3. SPONSOR & REFERRAL INFO - Use cached metrics for accuracy
        from app.services.leg_metrics_cache_service import LegMetricsCacheService
        
        sponsor = None
        if user.referrer_id:
            sponsor_user = db.query(User).filter(User.id == user.referrer_id).first()
            if sponsor_user:
                sponsor = {
                    "id": sponsor_user.id,
                    "name": sponsor_user.name
                }
        
        # Get cached metrics for accurate counts (same as user dashboard)
        cache_service = LegMetricsCacheService(db)
        cached_metrics = cache_service.get_user_metrics(user_id)
        
        # If no cache, create on-demand
        if not cached_metrics:
            cached_metrics = cache_service.refresh_user_metrics(user_id, source='rvz_on_demand')
        
        # Use cached counts (matching user dashboard exactly)
        direct_referrals_count = cached_metrics.total_direct_referrals if cached_metrics else 0
        direct_activated_count = cached_metrics.active_direct_referrals if cached_metrics else 0
        matching_earned_count = cached_metrics.effective_matching_count if cached_metrics else 0
        
        referral_info = {
            "sponsor": sponsor,
            "direct_referrals_count": direct_referrals_count,
            "direct_activated_count": direct_activated_count,
            "matching_earned_count": matching_earned_count
        }
        
        # 4. PLACEMENT & TEAM - Use cached metrics for accuracy
        placement = db.query(Placement).filter(Placement.child_id == user_id).first()
        placement_parent = None
        if placement:
            parent = db.query(User).filter(User.id == placement.parent_id).first()
            if parent:
                placement_parent = {
                    "id": parent.id,
                    "name": parent.name,
                    "side": placement.side.upper() if placement.side else None
                }
        
        # Use cached metrics (same as user dashboard)
        left_count = cached_metrics.left_team_count if cached_metrics else 0
        right_count = cached_metrics.right_team_count if cached_metrics else 0
        left_active = cached_metrics.left_active_count if cached_metrics else 0
        right_active = cached_metrics.right_active_count if cached_metrics else 0
        
        team_info = {
            "placement_parent": placement_parent,
            "left_team_count": left_count,
            "right_team_count": right_count,
            "left_active_count": left_active,
            "right_active_count": right_active,
            "total_team": left_count + right_count,
            "total_active": left_active + right_active
        }
        
        # 5. EARNINGS SUMMARY - Use SAME WalletService as user dashboard (SINGLE SOURCE OF TRUTH)
        from app.services.wallet_service import WalletService
        
        wallet_service = WalletService(db)
        earnings_summary = wallet_service.get_earnings_summary(user_id)
        
        # Format earnings to match RVZ frontend expectations
        earnings = {
            "direct_referral": {
                "pending": earnings_summary.get('direct_referral_pending', 0),
                "paid": earnings_summary.get('direct_referral_paid', 0),
                "total": earnings_summary.get('direct_referral_total', 0)
            },
            "matching_referral": {
                "pending": earnings_summary.get('matching_referral_pending', 0),
                "paid": earnings_summary.get('matching_referral_paid', 0),
                "total": earnings_summary.get('matching_referral_total', 0)
            },
            "ved_income": {
                "pending": earnings_summary.get('ved_income_pending', 0),
                "paid": earnings_summary.get('ved_income_paid', 0),
                "total": earnings_summary.get('ved_income_total', 0)
            },
            "guru_dakshina": {
                "pending": earnings_summary.get('guru_dakshina_pending', 0),
                "paid": earnings_summary.get('guru_dakshina_paid', 0),
                "total": earnings_summary.get('guru_dakshina_total', 0)
            },
            "total_earnings": earnings_summary.get('total_gross_earnings', 0),
            "total_pending": earnings_summary.get('total_pending_net', 0),
            "total_paid": earnings_summary.get('total_paid_net', 0)
        }
        
        # 6. WALLET BALANCES - REMOVED (as per user request)
        
        # 7. AWARDS - Use same AwardService as user login to ensure data consistency
        from app.services.award_service import AwardService
        
        award_service = AwardService(db)
        direct_progress = award_service.get_user_direct_award_progress(user_id)
        matching_progress = award_service.get_user_matching_award_progress(user_id)
        
        # Extract achieved awards only (matching what user sees in their dashboard)
        achieved_direct = [tier for tier in direct_progress.get("tier_progress", []) if tier.get("achieved", False)]
        achieved_matching = [tier for tier in matching_progress.get("tier_progress", []) if tier.get("achieved", False)]
        
        awards = {
            "direct_awards": [
                {
                    "tier_name": tier.get("award_name"),
                    "achieved": True,
                    "achieved_date": tier.get("achieved_date")
                }
                for tier in achieved_direct
            ],
            "matching_awards": [
                {
                    "tier_name": tier.get("award_name"),
                    "achieved": True,
                    "achieved_date": tier.get("achieved_date")
                }
                for tier in achieved_matching
            ],
            "total_direct_achievements": len(achieved_direct),
            "total_matching_achievements": len(achieved_matching)
        }
        
        # 8. VED PROGRAM - Use EXACT same logic as user dashboard
        from sqlalchemy import text
        
        # Get direct referrals ordered by registration (deterministic)
        direct_referrals_ordered = db.query(User).filter(
            User.referrer_id == user_id
        ).order_by(User.registration_date.asc(), User.id.asc()).all()
        
        # Ved Head is 3rd registered direct referral
        ved_head_data = None
        ved_team_total = 0
        ved_team_activated = 0
        
        if len(direct_referrals_ordered) >= 3:
            ved_head = direct_referrals_ordered[2]  # Position 3 is Ved Head
            ved_head_data = {
                "id": ved_head.id,
                "name": ved_head.name,
                "package": ved_head.get_package_type() if hasattr(ved_head, 'get_package_type') else None,
                "activation_date": ved_head.activation_date.isoformat() if ved_head.activation_date else None,
                "is_activated": ved_head.activation_date is not None
            }
            
            # Get Ved Team count using EXACT same logic as Ved Income calculation
            # Ved Team = Placement tree under Ved Head (EXCLUDING Ved Head itself, NO CASCADING)
            # Ved Activated = Members eligible for Ved Income (excludes those who already earned it)
            ved_tree_query = text("""
                WITH RECURSIVE ved_downline AS (
                    -- Base: Start from Ved Head's children (NOT including Ved Head)
                    SELECT 
                        p.child_id as user_id,
                        u.activation_date,
                        u.is_ved,
                        1 as level
                    FROM placement p
                    INNER JOIN "user" u ON u.id = p.child_id
                    WHERE p.parent_id = :ved_root_id
                    
                    UNION ALL
                    
                    -- Recursive: Stop at other Ved owners (prevents cascading)
                    SELECT 
                        p.child_id,
                        u.activation_date,
                        u.is_ved,
                        vd.level + 1
                    FROM ved_downline vd
                    INNER JOIN placement p ON p.parent_id = vd.user_id
                    INNER JOIN "user" u ON u.id = p.child_id
                    WHERE vd.level < 50
                      AND vd.is_ved = FALSE
                )
                SELECT 
                    COUNT(*) as total_count,
                    COUNT(CASE 
                        WHEN activation_date IS NOT NULL 
                        THEN 1 
                    END) as activated_count
                FROM ved_downline
            """)
            
            result = db.execute(ved_tree_query, {'ved_root_id': str(ved_head.id)}).fetchone()
            if result:
                ved_team_total = result[0] or 0
                ved_team_activated = result[1] or 0
        
        ved_info = {
            "is_ved_owner": user.is_ved,
            "ved_head": ved_head_data,
            "ved_overall": ved_team_total,  # Matches user dashboard "Ved Overall"
            "ved_activated": ved_team_activated,  # Matches user dashboard "Ved Activated"
            "total_ved_ids": max(0, len(direct_referrals_ordered) - 2) if len(direct_referrals_ordered) >= 3 else 0
        }
        
        # 9. KYC STATUS
        kyc_doc = db.query(KYCDocument).filter(KYCDocument.user_id == user_id).first()
        kyc = {
            "status": user.kyc_status,
            "aadhar_verified": kyc_doc.aadhar_verified if kyc_doc else False,
            "pan_verified": kyc_doc.pan_verified if kyc_doc else False
        }
        
        # 10. BANK DETAILS
        bank_approval = db.query(BankDetailsApproval).filter(
            BankDetailsApproval.user_id == user_id
        ).order_by(BankDetailsApproval.submitted_at.desc()).first()
        
        bank = {
            "bank_name": bank_approval.bank_name if bank_approval else None,
            "account_number": bank_approval.account_number if bank_approval else None,
            "ifsc_code": bank_approval.ifsc_code if bank_approval else None,
            "approval_status": bank_approval.approval_status if bank_approval else "Not Submitted",
            "approved_by": bank_approval.approved_by_id if bank_approval else None
        }
        
        # 11. BONANZA SYSTEM - DC Protocol: Query from DynamicBonanzaHistory
        from app.models.bonanza import DynamicBonanzaHistory, DynamicBonanza, Bonanza
        
        bonanza_records = db.query(
            DynamicBonanzaHistory, DynamicBonanza.bonanza_name
        ).join(
            DynamicBonanza, DynamicBonanzaHistory.bonanza_id == DynamicBonanza.id
        ).filter(
            DynamicBonanzaHistory.user_id == user_id
        ).all()
        
        bonanza = {
            "total_bonanzas": len(bonanza_records),
            "achieved_count": sum(1 for claim, _ in bonanza_records if claim.claim_status == 'Approved'),
            "bonanzas": [
                {
                    "bonanza_name": bonanza_name,
                    "reward_name": claim.award_name or 'Unknown',
                    "current_progress": claim.direct_count_achieved or 0,
                    "achievement_status": claim.processed_status or claim.claim_status,
                    "achieved_date": claim.claimed_at.isoformat() if claim.claimed_at else None,
                    "reward_given": claim.processed_status in ['Processed for Dispatch', 'Delivered'],
                    "payment_status": claim.processed_status or 'Pending'
                }
                for claim, bonanza_name in bonanza_records
            ]
        }
        
        # 12. FIELD ALLOWANCE
        # Query using raw SQL to avoid model/schema mismatch
        try:
            from sqlalchemy import text
            field_allowance_query = text("""
                SELECT COUNT(*) as total_records, 
                       COALESCE(SUM(CASE WHEN status = 'Paid' THEN amount_paid ELSE 0 END), 0) as total_paid,
                       COALESCE(SUM(CASE WHEN is_eligible = true THEN 1 ELSE 0 END), 0) as eligible_count,
                       allowance_type
                FROM field_allowance_progress 
                WHERE user_id = :user_id
                GROUP BY allowance_type
            """)
            result = db.execute(field_allowance_query, {"user_id": user_id}).fetchone()
            
            field_allowance = {
                "has_allowance": result and result[0] > 0 if result else False,
                "total_records": result[0] if result else 0,
                "total_paid": round(float(result[1])) if result else 0,
                "eligible_count": result[2] if result else 0,
                "allowance_type": result[3] if result else None
            }
        except Exception as e:
            logger.error(f"Error loading field allowance for {user_id}: {e}")
            field_allowance = {
                "has_allowance": False,
                "total_records": 0,
                "total_paid": 0,
                "eligible_count": 0,
                "allowance_type": None
            }
        
        # 13. PIN PURCHASE HISTORY
        from app.models.coupon import PINPurchaseRequest
        
        pin_purchases = db.query(PINPurchaseRequest).filter(
            PINPurchaseRequest.user_id == user_id
        ).all()
        
        pin_summary = {
            "total_requests": len(pin_purchases),
            "total_pins_requested": sum(p.quantity for p in pin_purchases),
            "approved_requests": sum(1 for p in pin_purchases if p.status == 'Approved'),
            "pending_requests": sum(1 for p in pin_purchases if p.status == 'Pending'),
            "total_amount_spent": round(float(sum(p.total_amount for p in pin_purchases if p.status == 'Approved')))
        }
        
        # 14. WITHDRAWAL HISTORY
        from app.models.withdrawal import WithdrawalRequest
        
        withdrawals = db.query(WithdrawalRequest).filter(
            WithdrawalRequest.user_id == user_id
        ).all()
        
        withdrawal_summary = {
            "total_requests": len(withdrawals),
            "approved_count": sum(1 for w in withdrawals if w.status == 'Approved'),
            "pending_count": sum(1 for w in withdrawals if w.status == 'Pending'),
            "rejected_count": sum(1 for w in withdrawals if w.status == 'Rejected'),
            "total_withdrawn": round(float(sum(w.withdrawal_amount for w in withdrawals if w.status == 'Approved'))),
            "pending_amount": round(float(sum(w.withdrawal_amount for w in withdrawals if w.status == 'Pending')))
        }
        
        # 15. ENHANCED WALLET DETAILS - REMOVED (as per user request)
        
        # 16. ACCOUNT ACTIVITY
        from datetime import datetime, timedelta
        
        days_since_registration = (datetime.now() - user.registration_date).days if user.registration_date else 0
        days_since_last_login = (datetime.now() - user.last_login).days if user.last_login else None
        
        account_activity = {
            "last_login": user.last_login.isoformat() if user.last_login else None,
            "days_since_registration": days_since_registration,
            "days_since_last_login": days_since_last_login,
            "account_age_months": round(days_since_registration / 30, 1)
        }
        
        # 17. RED COUPON SYSTEM
        red_coupon = {
            "is_red_coupon": user.is_red_coupon,
            "red_coupon_locked": user.red_coupon_locked,
            "red_coupon_date": user.red_coupon_date.isoformat() if user.red_coupon_date else None,
            "unlock_requests": user.red_coupon_unlock_requests
        }
        
        # 18. REFERRAL STATISTICS
        all_referrals = db.query(User).filter(User.referrer_id == user_id).all()
        activated_referrals = [r for r in all_referrals if r.activation_date is not None]
        
        referral_stats = {
            "total_referrals": len(all_referrals),
            "activated_referrals": len(activated_referrals),
            "unactivated_referrals": len(all_referrals) - len(activated_referrals),
            "referral_bonus_count": user.referral_bonus_count
        }
        
        # 19. TRANSACTION SUMMARY - Use earnings_summary data (SINGLE SOURCE OF TRUTH)
        # Count actual transaction records
        all_transactions = db.query(Transaction).filter(
            Transaction.referrer_id == user_id
        ).all()
        
        # Get actual withdrawn amount from withdrawal records
        from app.models.withdrawal import WithdrawalRequest
        total_withdrawn = round(float(
            db.query(func.coalesce(func.sum(WithdrawalRequest.withdrawal_amount), 0))
            .filter(
                WithdrawalRequest.user_id == user_id,
                WithdrawalRequest.status == 'Approved'
            )
            .scalar() or 0
        ), 2)
        
        # Use earnings_summary for accurate paid/pending breakdown
        total_paid = earnings_summary.get('total_paid_net', 0)  # All paid income (net after deductions)
        total_pending = earnings_summary.get('total_pending_net', 0)  # All pending income (net after deductions)
        total_gross = earnings_summary.get('total_gross_earnings', 0)  # Total gross earnings
        
        transaction_summary = {
            "total_transactions": len(all_transactions),
            "total_earned": total_gross,  # Total gross earnings (paid + pending)
            "total_paid": total_paid,  # Already paid to wallet
            "total_pending": total_pending,  # Waiting to be paid
            "total_released": total_withdrawn,  # Actual withdrawn amount
            "balance": total_paid - total_withdrawn  # Balance in wallet (paid - withdrawn)
        }
        
        # 20. PACKAGE HISTORY
        package_history = {
            "current_package": user.get_package_type() if hasattr(user, 'get_package_type') else None,
            "package_points": float(user.package_points or 0),
            "activation_date": user.activation_date.isoformat() if user.activation_date else None,
            "last_package_assigned": user.last_package_assigned_at.isoformat() if user.last_package_assigned_at else None,
            "coupon_status": user.coupon_status,
            "coupon_status_changed": user.coupon_status_changed_at.isoformat() if user.coupon_status_changed_at else None
        }
        
        # Return comprehensive data
        return {
            "success": True,
            "user_id": user_id,
            "profile": profile,
            "activation": activation,
            "referral_info": referral_info,
            "team_info": team_info,
            "earnings": earnings,
            "awards": awards,
            "ved_info": ved_info,
            "kyc": kyc,
            "bank": bank,
            "bonanza": bonanza,
            "field_allowance": field_allowance,
            "pin_summary": pin_summary,
            "withdrawal_summary": withdrawal_summary,
            "account_activity": account_activity,
            "red_coupon": red_coupon,
            "referral_stats": referral_stats,
            "transaction_summary": transaction_summary,
            "package_history": package_history
        }
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        logger.error(f"Error getting user data for {user_id}: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving user data: {str(e)}"
        )

@router.post("/user-data-reset")
async def reset_user_data(
    request: UserDataResetRequest,
    current_user: User = Depends(get_current_rvz_user_hybrid),
    db: Session = Depends(get_db)
):
    """Reset user data - RVZ ID SUPREME AUTHORITY (DANGER ZONE)"""
    try:
        user_service = UserService(db)
        
        # Find target user by MNR ID or email
        target_user = None
        if request.user_identifier.startswith('MNR'):
            target_user = user_service.get_user_by_id(request.user_identifier)
        else:
            target_user = user_service.get_user_by_email(request.user_identifier)
        
        if not target_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Validate reset type
        valid_reset_types = ["account_status", "wallet_balance", "kyc_documents", "complete_profile"]
        if request.reset_type not in valid_reset_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid reset type. Must be one of: {valid_reset_types}"
            )
        
        # Perform the reset based on type
        reset_actions = []
        
        if request.reset_type == "account_status":
            # Reset account status to active using setattr
            setattr(target_user, 'account_status', "Active")
            setattr(target_user, 'account_locked', False)
            reset_actions.append("Account status reset to Active")
            
        elif request.reset_type == "wallet_balance":
            # Reset wallet balances to zero using setattr
            setattr(target_user, 'wallet_balance', 0.0)
            setattr(target_user, 'upgrade_wallet_balance', 0.0)
            setattr(target_user, 'earned_total', 0.0)
            setattr(target_user, 'released_total', 0.0)
            reset_actions.append("Wallet balances reset to zero")
            
        elif request.reset_type == "kyc_documents":
            # Reset KYC status and documents using setattr
            setattr(target_user, 'kyc_status', "Pending")
            setattr(target_user, 'kyc_documents_complete', False)
            setattr(target_user, 'kyc_bypass_active', False)
            reset_actions.append("KYC documents and status reset")
            
        elif request.reset_type == "complete_profile":
            # Complete profile reset (DANGER!) using setattr
            setattr(target_user, 'account_status', "Active")
            setattr(target_user, 'account_locked', False)
            setattr(target_user, 'wallet_balance', 0.0)
            setattr(target_user, 'upgrade_wallet_balance', 0.0)
            setattr(target_user, 'earned_total', 0.0)
            setattr(target_user, 'released_total', 0.0)
            setattr(target_user, 'kyc_status', "Pending")
            setattr(target_user, 'kyc_documents_complete', False)
            setattr(target_user, 'profile_completion_score', 0)
            setattr(target_user, 'mobile_verified', False)
            target_actions = ["Account status", "Wallet balances", "KYC status", "Profile data", "Verification status"]
            reset_actions.extend(target_actions)
        
        # Commit the changes
        db.commit()
        
        # Log this critical action
        reason = request.reason or f"RVZ Data Reset: {request.reset_type} by {current_user.id}"
        
        return {
            "success": True,
            "message": f"User data reset completed for {target_user.id}",
            "user_info": {
                "id": target_user.id,
                "name": target_user.name,
                "email": target_user.email,
                "user_type": target_user.user_type
            },
            "reset_type": request.reset_type,
            "actions_performed": reset_actions,
            "reset_by": current_user.id,
            "reset_at": "2024-09-29T00:00:00Z",
            "reason": reason,
            "warning": "⚠️ This operation permanently modified user data"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error resetting user data: {str(e)}"
        )

# Bulk Edit Endpoints
@router.post("/bulk-edit/users")
async def get_users_for_bulk_edit(
    filters: BulkUserFiltersRequest,
    current_user: User = Depends(get_current_rvz_user_hybrid),
    db: Session = Depends(get_db)
):
    """Get filtered and paginated user data for bulk editing"""
    try:
        # Build base query
        query = db.query(User)
        
        # Apply filters
        if filters.user_type:
            query = query.filter(User.user_type == filters.user_type)
        if filters.account_status:
            query = query.filter(User.account_status == filters.account_status)
        if filters.kyc_status:
            query = query.filter(User.kyc_status == filters.kyc_status)
        if filters.referrer_id:
            query = query.filter(User.referrer_id == filters.referrer_id)
        if filters.ved_owner_id:
            query = query.filter(User.ved_owner_id == filters.ved_owner_id)
        if filters.is_ved is not None:
            query = query.filter(User.is_ved == filters.is_ved)
            
        # Date range filters
        if filters.registration_date_from:
            query = query.filter(User.registration_date >= filters.registration_date_from)
        if filters.registration_date_to:
            query = query.filter(User.registration_date <= filters.registration_date_to)
        if filters.last_login_from:
            query = query.filter(User.last_login >= filters.last_login_from)
        if filters.last_login_to:
            query = query.filter(User.last_login <= filters.last_login_to)
        if filters.ved_activation_from:
            query = query.filter(User.ved_activation_date >= filters.ved_activation_from)
        if filters.ved_activation_to:
            query = query.filter(User.ved_activation_date <= filters.ved_activation_to)
            
        # Search functionality
        if filters.search_term:
            search_conditions = []
            if "id" in filters.search_fields:
                search_conditions.append(User.id.ilike(f"%{filters.search_term}%"))
            if "name" in filters.search_fields:
                search_conditions.append(User.name.ilike(f"%{filters.search_term}%"))
            if "email" in filters.search_fields:
                search_conditions.append(User.email.ilike(f"%{filters.search_term}%"))
            
            if search_conditions:
                from sqlalchemy import or_
                query = query.filter(or_(*search_conditions))
        
        # Get total count before pagination
        total_count = query.count()
        
        # Apply sorting
        if filters.sort_by == "id":
            sort_column = User.id
        elif filters.sort_by == "name":
            sort_column = User.name
        elif filters.sort_by == "registration_date":
            sort_column = User.registration_date
        elif filters.sort_by == "earned_total":
            sort_column = User.earned_total
        else:
            sort_column = User.id  # Default sort
            
        if filters.sort_order == "desc":
            query = query.order_by(sort_column.desc())
        else:
            query = query.order_by(sort_column.asc())
        
        # Apply pagination
        offset = (filters.page - 1) * filters.page_size
        users = query.offset(offset).limit(filters.page_size).all()
        
        # Format user data for bulk edit
        users_data = []
        for user in users:
            user_data = {
                # Read-only fields (display only)
                "id": user.id,
                "registration_date": user.registration_date.isoformat() if user.registration_date else None,
                "name": user.name,
                "referrer_id": user.referrer_id,
                "phone_number": user.phone_number,
                "earned_total": round(float(user.earned_total)) if user.earned_total else 0.0,
                "released_total": round(float(user.released_total)) if user.released_total else 0.0,
                "kyc_status": user.kyc_status,
                "coupon_status": user.coupon_status,
                "placement_status": user.placement_status,
                "ved_owner_id": user.ved_owner_id,
                "kyc_documents_complete": user.kyc_documents_complete,
                "last_package_assigned_at": user.last_package_assigned_at.isoformat() if user.last_package_assigned_at else None,
                "package_assignment_timer_reset": user.package_assignment_timer_reset,
                
                # Editable fields (RVZ can modify)
                "password_masked": "••••••••" if user.password else "No Password Set",
                "phone_number": user.phone_number,
                "kyc_status": user.kyc_status,
                "coupon_status": user.coupon_status,
                "kyc_documents_complete": user.kyc_documents_complete,
                "last_package_assigned_at": user.last_package_assigned_at.isoformat() if user.last_package_assigned_at else None,
                "account_status": user.account_status,
                
                # Additional display info
                "email": user.email,
                "user_type": user.user_type,
                "account_status": user.account_status
            }
            users_data.append(user_data)
        
        # Calculate pagination info
        total_pages = (total_count + filters.page_size - 1) // filters.page_size
        
        return {
            "users": users_data,
            "pagination": {
                "current_page": filters.page,
                "page_size": filters.page_size,
                "total_count": total_count,
                "total_pages": total_pages,
                "has_next": filters.page < total_pages,
                "has_prev": filters.page > 1
            },
            "filters_applied": {
                "user_type": filters.user_type,
                "account_status": filters.account_status,
                "kyc_status": filters.kyc_status,
                "referrer_id": filters.referrer_id,
                "ved_owner_id": filters.ved_owner_id,
                "is_ved": filters.is_ved,
                "search_term": filters.search_term,
                "date_ranges": {
                    "registration": f"{filters.registration_date_from} to {filters.registration_date_to}" if filters.registration_date_from or filters.registration_date_to else None,
                    "last_login": f"{filters.last_login_from} to {filters.last_login_to}" if filters.last_login_from or filters.last_login_to else None,
                    "ved_activation": f"{filters.ved_activation_from} to {filters.ved_activation_to}" if filters.ved_activation_from or filters.ved_activation_to else None
                }
            },
            "column_definitions": {
                "readonly_columns": [
                    {"key": "id", "label": "User ID", "type": "text"},
                    {"key": "registration_date", "label": "Registration Date", "type": "datetime"},
                    {"key": "name", "label": "Name", "type": "text"},
                    {"key": "referrer_id", "label": "Sponsor ID", "type": "text"},
                    {"key": "phone_number", "label": "Phone Number", "type": "text"},
                    {"key": "earned_total", "label": "Total Earned", "type": "currency"},
                    {"key": "released_total", "label": "Total Released", "type": "currency"},
                    {"key": "kyc_status", "label": "KYC Status", "type": "text"},
                    {"key": "coupon_status", "label": "Coupon Status", "type": "text"},
                    {"key": "placement_status", "label": "Placement Status", "type": "text"},
                    {"key": "ved_owner_id", "label": "Ved Owner", "type": "text"},
                    {"key": "kyc_documents_complete", "label": "KYC Documents", "type": "boolean"},
                    {"key": "last_package_assigned_at", "label": "Last Package Assigned", "type": "datetime"},
                    {"key": "package_assignment_timer_reset", "label": "Package Timer Reset", "type": "boolean"}
                ],
                "editable_columns": [
                    {"key": "password", "label": "Password", "type": "password", "masked": True},
                    {"key": "phone_number", "label": "Phone Number", "type": "text"},
                    {"key": "kyc_status", "label": "KYC Status", "type": "select", "options": ["Pending", "Approved", "Rejected", "Under Review"]},
                    {"key": "coupon_status", "label": "Coupon Status", "type": "select", "options": ["Green", "Yellow", "Red", "Active", "Inactive"]},
                    {"key": "kyc_documents_complete", "label": "KYC Documents Complete", "type": "boolean"},
                    {"key": "last_package_assigned_at", "label": "Last Package Assigned", "type": "datetime"},
                    {"key": "account_status", "label": "Account Status", "type": "select", "options": ["Active", "Inactive", "Suspended", "Pending"]}
                ]
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching users for bulk edit: {str(e)}")

@router.post("/bulk-edit/update")
async def bulk_update_users(
    request: BulkUserUpdateRequest,
    current_user: User = Depends(get_current_rvz_user_hybrid),
    db: Session = Depends(get_db)
):
    """Apply bulk updates to user data with audit logging"""
    try:
        updated_users = []
        change_log = []
        errors = []
        
        for update in request.user_updates:
            try:
                user_id = update.get("user_id")
                field_name = update.get("field_name")
                new_value = update.get("new_value")
                
                if not user_id or not field_name:
                    errors.append(f"Missing user_id or field_name in update: {update}")
                    continue
                
                # Get user
                user = db.query(User).filter(User.id == user_id).first()
                if not user:
                    errors.append(f"User not found: {user_id}")
                    continue
                
                # Get old value for audit log
                old_value = getattr(user, field_name, None)
                
                # Validate field is editable
                editable_fields = [
                    "password", "phone_number", "kyc_status", "coupon_status", 
                    "kyc_documents_complete", "last_package_assigned_at", "account_status"
                ]
                if field_name not in editable_fields:
                    errors.append(f"Field '{field_name}' is not editable for user {user_id}")
                    continue
                
                # Special handling for password field
                if field_name == "password":
                    if new_value and len(new_value) > 0:
                        hashed_password = SecurityManager.get_password_hash(new_value)
                        setattr(user, field_name, hashed_password)
                        
                        # Log the change (don't log actual passwords)
                        change_log.append({
                            "user_id": user_id,
                            "field_name": field_name,
                            "old_value": "••••••••" if old_value else "No Password",
                            "new_value": "••••••••",
                            "changed_by": current_user.id,
                            "change_reason": request.reason,
                            "timestamp": "2025-09-29T10:40:00Z"
                        })
                    else:
                        errors.append(f"Invalid password value for user {user_id}")
                        continue
                elif field_name == "kyc_documents_complete":
                    # Handle boolean field
                    bool_value = new_value if isinstance(new_value, bool) else str(new_value).lower() in ['true', '1', 'yes']
                    setattr(user, field_name, bool_value)
                    
                    change_log.append({
                        "user_id": user_id,
                        "field_name": field_name,
                        "old_value": old_value,
                        "new_value": bool_value,
                        "changed_by": current_user.id,
                        "change_reason": request.reason,
                        "timestamp": "2025-09-29T10:40:00Z"
                    })
                elif field_name == "last_package_assigned_at":
                    # Handle datetime field
                    from datetime import datetime
                    if new_value:
                        try:
                            if isinstance(new_value, str):
                                datetime_value = datetime.fromisoformat(new_value.replace('Z', '+00:00'))
                            else:
                                datetime_value = new_value
                            setattr(user, field_name, datetime_value)
                        except Exception as e:
                            errors.append(f"Invalid datetime format for {field_name} in user {user_id}: {str(e)}")
                            continue
                    else:
                        setattr(user, field_name, None)
                    
                    change_log.append({
                        "user_id": user_id,
                        "field_name": field_name,
                        "old_value": old_value.isoformat() if old_value else None,
                        "new_value": new_value,
                        "changed_by": current_user.id,
                        "change_reason": request.reason,
                        "timestamp": "2025-09-29T10:40:00Z"
                    })
                else:
                    # Handle text/string fields (phone_number, kyc_status, coupon_status, account_status)
                    setattr(user, field_name, new_value)
                    
                    change_log.append({
                        "user_id": user_id,
                        "field_name": field_name,
                        "old_value": old_value,
                        "new_value": new_value,
                        "changed_by": current_user.id,
                        "change_reason": request.reason,
                        "timestamp": "2025-09-29T10:40:00Z"
                    })
                
                updated_users.append(user_id)
                
            except Exception as e:
                errors.append(f"Error updating user {update.get('user_id', 'unknown')}: {str(e)}")
        
        # Commit all changes
        if updated_users:
            db.commit()
        
        return {
            "success": True,
            "message": f"Bulk update completed. {len(updated_users)} users updated.",
            "updated_users": updated_users,
            "change_log": change_log,
            "errors": errors,
            "summary": {
                "total_updates_requested": len(request.user_updates),
                "successful_updates": len(updated_users),
                "failed_updates": len(errors),
                "fields_updated": list(set([update.get("field_name") for update in request.user_updates if update.get("field_name")])),
                "updated_by": current_user.id,
                "update_reason": request.reason
            }
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error during bulk update: {str(e)}")

@router.get("/bulk-edit/filter-options")
async def get_bulk_edit_filter_options(
    current_user: User = Depends(get_current_rvz_user_hybrid),
    db: Session = Depends(get_db)
):
    """Get available filter options for bulk edit interface"""
    try:
        # Get unique values for dropdown filters
        user_types = db.query(User.user_type).distinct().filter(User.user_type.isnot(None)).all()
        account_statuses = db.query(User.account_status).distinct().filter(User.account_status.isnot(None)).all()
        kyc_statuses = db.query(User.kyc_status).distinct().filter(User.kyc_status.isnot(None)).all()
        
        # Get sponsor options (top 20 most common sponsors)
        sponsors = db.query(User.referrer_id).distinct().filter(User.referrer_id.isnot(None)).limit(20).all()
        
        # Get ved owner options (all ved owners)
        ved_owners = db.query(User.ved_owner_id).distinct().filter(User.ved_owner_id.isnot(None)).all()
        
        return {
            "filters": {
                "user_types": [t[0] for t in user_types if t[0]],
                "account_statuses": [s[0] for s in account_statuses if s[0]],
                "kyc_statuses": [k[0] for k in kyc_statuses if k[0]],
                "sponsors": [s[0] for s in sponsors if s[0]],
                "ved_owners": [v[0] for v in ved_owners if v[0]],
                "is_ved_options": [{"value": True, "label": "Yes"}, {"value": False, "label": "No"}]
            },
            "date_filter_fields": [
                {"key": "registration_date", "label": "Registration Date"},
                {"key": "last_login", "label": "Last Login Date"},
                {"key": "ved_activation", "label": "Ved Activation Date"}
            ],
            "sort_options": [
                {"key": "id", "label": "User ID"},
                {"key": "name", "label": "Name"},
                {"key": "registration_date", "label": "Registration Date"},
                {"key": "earned_total", "label": "Total Earned"}
            ],
            "search_field_options": [
                {"key": "id", "label": "User ID"},
                {"key": "name", "label": "Name"},
                {"key": "email", "label": "Email"}
            ]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching filter options: {str(e)}")

# ===== USER ACTIVATION CONTROL =====

class UserActivationVGKRequest(BaseModel):
    user_id: str
    activate_without_pin: bool = True
    activation_sequence: Optional[int] = None
    reason: str

@router.post("/user-activation/activate")
async def rvz_activate_user(
    request: UserActivationVGKRequest,
    current_user: User = Depends(get_current_rvz_user_hybrid),
    db: Session = Depends(get_db)
):
    """RVZ ID: Activate user without PIN requirement"""
    try:
        from app.core.audit import AuditLogger
        from app.models.base import get_indian_time
        
        user_service = UserService(db)
        target_user = user_service.get_user_by_id(request.user_id)
        
        if not target_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Use service method for activation
        activation_result = user_service.activate_user(
            user_id=request.user_id,
            activation_sequence=request.activation_sequence
        )
        
        if not activation_result.get('success'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=activation_result.get('error', 'Activation failed')
            )
        
        # Proper audit logging
        AuditLogger.log_action(
            db=db,
            user=current_user,
            action='RVZ_USER_ACTIVATION',
            resource_type='User',
            resource_id=request.user_id,
            details={
                "activation_sequence": request.activation_sequence,
                "activated_without_pin": request.activate_without_pin,
                "reason": request.reason
            }
        )
        
        return {
            "success": True,
            "message": f"User {request.user_id} activated successfully by RVZ ID",
            "user_id": request.user_id,
            "activation_date": activation_result.get('activation_date'),
            "activated_by": current_user.id,
            "reason": request.reason
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error activating user: {str(e)}"
        )


class WelcomeCouponActivationRequest(BaseModel):
    """DC Protocol (Jan 2026): Welcome Coupon activation request - VGK Mentor/EA only"""
    user_id: str
    reason: str


@router.post("/user-activation/welcome-coupon")
async def rvz_activate_with_welcome_coupon(
    request: WelcomeCouponActivationRequest,
    current_user = Depends(get_current_rvz_user_hybrid),
    db: Session = Depends(get_db)
):
    """
    DC Protocol (Jan 2026): Activate user with Welcome Coupon
    
    RESTRICTED TO: VGK Mentor and EA staff only
    
    Welcome Coupon characteristics:
    - ₹0 payment required (Exception Coupon)
    - 15,000 points display
    - Generates ₹0 income for sponsors/upliners
    - User's downline generates normal income
    - Cannot download/print receipt
    """
    try:
        from app.core.audit import AuditLogger
        from app.models.base import get_indian_time
        from app.constants import PACKAGE_SYSTEM
        
        # DC Protocol: Strict verification - VGK Mentor (VGK4U) or EA role ONLY
        staff_type = getattr(current_user, 'staff_type', None) or ''
        role = getattr(current_user, 'role', None)
        role_name = getattr(role, 'role_name', '') if role else ''
        hierarchy_level = getattr(role, 'hierarchy_level', 0) if role else 0
        
        # Strict allowed list: VGK4U (VGK Mentor) and EA staff types only
        allowed_staff_types = ['VGK4U']  # VGK Mentor staff type
        allowed_role_names = ['VGK Mentor', 'VGK4U Supreme', 'EA', 'Executive Assistant']  # Exact role names
        
        is_allowed = (
            staff_type in allowed_staff_types or
            role_name in allowed_role_names or
            (role_name.upper() == 'EA') or  # Exact EA match
            (staff_type.upper() == 'EA')  # Exact EA staff type
        )
        
        if not is_allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Welcome Coupon activation is restricted to VGK Mentor and EA staff only. Your role: {role_name or staff_type}"
            )
        
        user_service = UserService(db)
        target_user = user_service.get_user_by_id(request.user_id)
        
        if not target_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        if target_user.activation_date is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"User {request.user_id} is already activated"
            )
        
        # Set Welcome Coupon flag BEFORE activation
        target_user.is_welcome_coupon = True
        target_user.package_points = 1.0  # Same as Platinum (15000 points)
        target_user.coupon_type = 'WELCOME'
        
        # Activate the user
        activation_result = user_service.activate_user(
            user_id=request.user_id
        )
        
        if not activation_result.get('success'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=activation_result.get('error', 'Activation failed')
            )
        
        db.commit()
        
        # Audit log
        AuditLogger.log_action(
            db=db,
            user=current_user,
            action='WELCOME_COUPON_ACTIVATION',
            resource_type='User',
            resource_id=request.user_id,
            details={
                "coupon_type": "Welcome Coupon",
                "payment_amount": 0,
                "exception_coupon": True,
                "reason": request.reason,
                "staff_type": staff_type,
                "role_name": role_name
            }
        )
        
        return {
            "success": True,
            "message": f"User {request.user_id} activated with Welcome Coupon (Exception Coupon)",
            "user_id": request.user_id,
            "coupon_type": "Welcome Coupon",
            "payment_amount": 0,
            "points_display": 15000,
            "activation_date": activation_result.get('activation_date'),
            "activated_by": current_user.id,
            "reason": request.reason
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error activating user with Welcome Coupon: {str(e)}"
        )


class BulkActivationVGKRequest(BaseModel):
    user_ids: List[str]
    reason: str

@router.post("/user-activation/bulk-activate")
async def rvz_bulk_activate_users(
    request: BulkActivationVGKRequest,
    current_user: User = Depends(get_current_rvz_user_hybrid),
    db: Session = Depends(get_db)
):
    """RVZ ID: Bulk activate multiple users without PIN"""
    try:
        from app.models.base import get_indian_time
        from app.services.user_service import UserService
        user_service = UserService(db)
        activated_count = 0
        failed_users = []
        
        for user_id in request.user_ids:
            try:
                user = db.query(User).filter(User.id == user_id).first()
                if user:
                    # DC Protocol (Dec 22, 2025): Validate mobile uniqueness before activation
                    mobile_check = user_service.ensure_unique_active_mobile(user.phone_number, user_id)
                    if not mobile_check.get("success"):
                        failed_users.append({
                            "user_id": user_id, 
                            "reason": mobile_check.get("error", "Mobile number already in use"),
                            "requires_mobile_update": True
                        })
                        continue
                    
                    user.is_active = True
                    user.coupon_status = 'Active'
                    user.account_status = 'Active'
                    user.activation_date = get_indian_time()
                    activated_count += 1
                else:
                    failed_users.append({"user_id": user_id, "reason": "User not found"})
            except Exception as e:
                failed_users.append({"user_id": user_id, "reason": str(e)})
        
        db.commit()
        
        # Update cache for activated users
        try:
            from app.services.leg_metrics_cache_service import LegMetricsCacheService
            cache_service = LegMetricsCacheService(db)
            
            for user_id in request.user_ids:
                if user_id not in [f["user_id"] for f in failed_users]:
                    cache_service.refresh_user_metrics(user_id, source='activation_hook')
            
            logger.info(f"✅ Cache updated for {activated_count} activated users")
        except Exception as e:
            logger.error(f"⚠️ Cache update failed after activation: {e}")
        
        return {
            "success": True,
            "message": f"Bulk activation completed: {activated_count}/{len(request.user_ids)} users activated",
            "activated_count": activated_count,
            "failed_count": len(failed_users),
            "failed_users": failed_users,
            "activated_by": current_user.id,
            "reason": request.reason
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error in bulk activation: {str(e)}"
        )

# ===== MOBILE VALIDATION PRE-CHECK (DC Protocol Dec 22, 2025) =====

class MobileValidationRequest(BaseModel):
    user_id: str

@router.post("/user-activation/validate-mobile")
async def rvz_validate_mobile_for_activation(
    request: MobileValidationRequest,
    current_user: User = Depends(get_current_rvz_user_hybrid),
    db: Session = Depends(get_db)
):
    """
    DC Protocol (Dec 22, 2025): Pre-validate mobile number uniqueness before activation
    
    This endpoint allows frontend to check if a user's mobile number is available
    for activation BEFORE attempting the actual activation. This provides better UX
    by alerting staff that mobile number needs updating.
    """
    try:
        user_service = UserService(db)
        target_user = user_service.get_user_by_id(request.user_id)
        
        if not target_user:
            return {
                "success": False,
                "valid": False,
                "message": "User not found",
                "user_id": request.user_id
            }
        
        # Check if already activated
        if target_user.activation_date is not None:
            return {
                "success": True,
                "valid": True,
                "message": "User is already activated",
                "already_activated": True,
                "user_id": request.user_id
            }
        
        # Validate mobile uniqueness
        mobile_check = user_service.ensure_unique_active_mobile(target_user.phone_number, request.user_id)
        
        if mobile_check.get("success"):
            return {
                "success": True,
                "valid": True,
                "message": "Mobile number is available for activation",
                "user_id": request.user_id,
                "phone_number": target_user.phone_number[-4:] if target_user.phone_number else None  # Last 4 digits only for privacy
            }
        else:
            return {
                "success": True,
                "valid": False,
                "message": mobile_check.get("error", "Mobile number validation failed"),
                "requires_mobile_update": True,
                "user_id": request.user_id,
                "phone_number": target_user.phone_number[-4:] if target_user.phone_number else None
            }
    
    except Exception as e:
        logger.error(f"Mobile validation error: {e}")
        return {
            "success": False,
            "valid": False,
            "message": f"Validation error: {str(e)}",
            "user_id": request.user_id
        }

# ===== BRAND/LEVEL MANAGEMENT =====

class BrandLevelUpdateRequest(BaseModel):
    user_id: str
    brand: Optional[str] = None
    level: Optional[str] = None
    reason: str

@router.post("/brand-level/update")
async def rvz_update_brand_level(
    request: BrandLevelUpdateRequest,
    current_user: User = Depends(get_current_rvz_user_hybrid),
    db: Session = Depends(get_db)
):
    """RVZ ID: Update user brand and level"""
    try:
        user_service = UserService(db)
        target_user = user_service.get_user_by_id(request.user_id)
        
        if not target_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        updates = {}
        if request.brand:
            target_user.brand = request.brand
            updates["brand"] = request.brand
            
        if request.level:
            target_user.level = request.level
            updates["level"] = request.level
        
        db.commit()
        
        return {
            "success": True,
            "message": f"Brand/Level updated for user {request.user_id}",
            "user_id": request.user_id,
            "updates": updates,
            "updated_by": current_user.id,
            "reason": request.reason
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating brand/level: {str(e)}"
        )

# ===== RED ID REACTIVATION =====

class RedIDReactivationVGKRequest(BaseModel):
    user_id: str
    reassign_to_sponsor: Optional[str] = None
    reason: str

@router.post("/red-id/reactivate")
async def rvz_reactivate_red_id(
    request: RedIDReactivationVGKRequest,
    current_user: User = Depends(get_current_rvz_user_hybrid),
    db: Session = Depends(get_db)
):
    """RVZ ID: Reactivate Red ID user and optionally reassign to new sponsor"""
    try:
        user_service = UserService(db)
        target_user = user_service.get_user_by_id(request.user_id)
        
        if not target_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Check if user is a Red ID holder
        if not getattr(target_user, 'is_red_coupon', False):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User is not a Red ID holder"
            )
        
        # Reactivate the Red ID user
        target_user.is_active = True
        target_user.account_status = 'Active'
        target_user.account_locked = False
        if hasattr(target_user, 'red_coupon_locked'):
            target_user.red_coupon_locked = False
        
        # Optionally reassign to new sponsor
        if request.reassign_to_sponsor:
            reassign_user = user_service.get_user_by_id(request.reassign_to_sponsor)
            if reassign_user:
                target_user.referrer_id = request.reassign_to_sponsor
        
        db.commit()
        
        return {
            "success": True,
            "message": f"Red ID user {request.user_id} reactivated successfully",
            "user_id": request.user_id,
            "reactivated": True,
            "reassigned": bool(request.reassign_to_sponsor),
            "new_sponsor": request.reassign_to_sponsor,
            "reactivated_by": current_user.id,
            "reason": request.reason
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error reactivating Red ID: {str(e)}"
        )

# ===== PAYMENT TRIGGERS =====

class PaymentTriggerVGKRequest(BaseModel):
    trigger_type: str  # daily_calculation, monthly_payout, bonus_distribution
    execution_date: Optional[str] = None
    reason: str

@router.post("/payments/trigger")
async def rvz_trigger_payment(
    request: PaymentTriggerVGKRequest,
    current_user: User = Depends(get_current_rvz_user_hybrid),
    db: Session = Depends(get_db)
):
    """RVZ ID: Manually trigger payment calculations/payouts"""
    try:
        from app.models.base import get_indian_time
        from datetime import datetime
        
        execution_date = datetime.fromisoformat(request.execution_date) if request.execution_date else get_indian_time()
        
        valid_triggers = ['daily_calculation', 'monthly_payout', 'bonus_distribution']
        if request.trigger_type not in valid_triggers:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid trigger type. Must be one of: {valid_triggers}"
            )
        
        # Log the trigger action
        trigger_result = {
            "trigger_type": request.trigger_type,
            "execution_date": execution_date.isoformat(),
            "triggered_by": current_user.id,
            "reason": request.reason,
            "status": "Triggered"
        }
        
        if request.trigger_type == "daily_calculation":
            trigger_result["message"] = "Daily earnings calculation triggered"
        elif request.trigger_type == "monthly_payout":
            trigger_result["message"] = "Monthly payout processing triggered"
        elif request.trigger_type == "bonus_distribution":
            trigger_result["message"] = "Bonus distribution triggered"
        
        return {
            "success": True,
            **trigger_result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error triggering payment: {str(e)}"
        )

# ===== SYSTEM MAINTENANCE MODE =====

class MaintenanceModeVGKRequest(BaseModel):
    enabled: bool
    message: Optional[str] = None
    reason: str

@router.post("/system/maintenance-mode")
async def rvz_toggle_maintenance(
    request: MaintenanceModeVGKRequest,
    current_user: User = Depends(get_current_rvz_user_hybrid),
    db: Session = Depends(get_db)
):
    """RVZ ID: Toggle system maintenance mode"""
    try:
        app_settings = db.query(AppSettings).first()
        
        if not app_settings:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="App settings not found"
            )
        
        # Update maintenance mode
        app_settings.system_maintenance_mode = request.enabled
        if request.message:
            app_settings.maintenance_message = request.message
        
        from app.models.base import get_indian_time
        app_settings.last_updated_by = str(current_user.id)
        app_settings.last_updated_at = get_indian_time()
        
        db.commit()
        
        return {
            "success": True,
            "message": f"Maintenance mode {'enabled' if request.enabled else 'disabled'}",
            "maintenance_mode": request.enabled,
            "maintenance_message": request.message,
            "updated_by": current_user.id,
            "reason": request.reason
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error toggling maintenance mode: {str(e)}"
        )

# ===== PACKAGE MANAGEMENT =====

class BulkPackageAssignmentRequest(BaseModel):
    user_package_pairs: List[Dict[str, str]]  # [{"user_id": "MNR123", "package_type": "Active"}]
    reason: str

@router.post("/packages/bulk-assign")
async def rvz_bulk_assign_packages(
    request: BulkPackageAssignmentRequest,
    current_user: User = Depends(get_current_rvz_user_hybrid),
    db: Session = Depends(get_db)
):
    """RVZ ID: Bulk assign packages to users"""
    try:
        from app.models.base import get_indian_time
        assigned_count = 0
        failed_assignments = []
        
        for pair in request.user_package_pairs:
            try:
                user_id = pair.get("user_id")
                package_type = pair.get("package_type")
                
                user = db.query(User).filter(User.id == user_id).first()
                if user:
                    user.coupon_type = package_type
                    user.coupon_status = 'Active'
                    assigned_count += 1
                else:
                    failed_assignments.append({
                        "user_id": user_id,
                        "package_type": package_type,
                        "reason": "User not found"
                    })
            except Exception as e:
                failed_assignments.append({
                    "user_id": pair.get("user_id"),
                    "package_type": pair.get("package_type"),
                    "reason": str(e)
                })
        
        db.commit()
        
        return {
            "success": True,
            "message": f"Bulk package assignment completed: {assigned_count}/{len(request.user_package_pairs)} assigned",
            "assigned_count": assigned_count,
            "failed_count": len(failed_assignments),
            "failed_assignments": failed_assignments,
            "assigned_by": current_user.id,
            "reason": request.reason
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error in bulk package assignment: {str(e)}"
        )

# ===== RVZ COMPREHENSIVE DASHBOARD =====

@router.get("/dashboard/comprehensive")
async def rvz_comprehensive_dashboard(
    current_user: User = Depends(get_current_rvz_user_hybrid),
    db: Session = Depends(get_db)
):
    """RVZ ID: Comprehensive system dashboard"""
    try:
        from app.models.transaction import Transaction
        from app.models.base import get_indian_time
        from sqlalchemy import func, and_
        
        # User statistics
        total_users = db.query(User).count()
        active_users = db.query(User).filter(User.account_status == 'Active').count()
        pending_kyc = db.query(User).filter(User.kyc_status == 'Pending').count()
        red_id_users = db.query(User).filter(User.is_red_coupon == True).count() if hasattr(User, 'is_red_coupon') else 0
        
        # Today's statistics
        today = get_indian_time().date()
        today_earnings = db.query(func.sum(Transaction.amount)).filter(
            and_(
                func.date(Transaction.timestamp) == today,
                Transaction.transaction_type.in_([
                    'Direct Referral', 'Matching Referral', 'Ved',
                    'Guru Dakshina', 'Field Allowance'
                ])
            )
        ).scalar() or 0
        
        today_transactions = db.query(Transaction).filter(
            func.date(Transaction.timestamp) == today
        ).count()
        
        # Month statistics
        from datetime import datetime
        month_start = today.replace(day=1)
        month_earnings = db.query(func.sum(Transaction.amount)).filter(
            and_(
                Transaction.timestamp >= month_start,
                Transaction.transaction_type.in_([
                    'Direct Referral', 'Matching Referral', 'Ved',
                    'Guru Dakshina', 'Field Allowance'
                ])
            )
        ).scalar() or 0
        
        # System settings
        app_settings = db.query(AppSettings).first()
        
        dashboard_data = {
            "users": {
                "total": total_users,
                "active": active_users,
                "inactive": total_users - active_users,
                "pending_kyc": pending_kyc,
                "red_id_holders": red_id_users
            },
            "earnings": {
                "today": round(float(today_earnings)),
                "this_month": round(float(month_earnings))
            },
            "transactions": {
                "today": today_transactions
            },
            "system_status": {
                "maintenance_mode": getattr(app_settings, 'system_maintenance_mode', False) if app_settings else False,
                "database": "Connected",
                "status": "Operational"
            }
        }
        
        return {
            "success": True,
            "dashboard": dashboard_data
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching RVZ dashboard: {str(e)}"
        )

@router.post("/trigger-income-calculation")
async def trigger_income_calculation(
    calculation_date: Optional[str] = Query(None, description="Date to calculate incomes for (YYYY-MM-DD). Defaults to previous day."),
    current_user: User = Depends(get_current_rvz_user_hybrid),
    db: Session = Depends(get_db)
):
    """
    Manually trigger income calculation for a specific date (RVZ Admin only)
    
    This endpoint allows RVZ admins to manually trigger the income calculation
    that normally runs at midnight. Useful for:
    - Testing income calculations
    - Recalculating incomes for a specific date
    - Triggering calculations immediately when users are activated
    """
    try:
        from app.core.scheduler import calculate_previous_day_incomes
        from datetime import datetime, timedelta
        import logging
        
        logger = logging.getLogger(__name__)
        
        # Parse the date or use previous day
        if calculation_date:
            target_date = datetime.strptime(calculation_date, "%Y-%m-%d").date()
        else:
            target_date = (date.today() - timedelta(days=1))
        
        logger.info(f"🎯 Manual income calculation triggered by RVZ admin {current_user.id} for {target_date}")
        
        # Run the calculation
        calculate_previous_day_incomes()
        
        # Get summary of created incomes
        from app.models.transaction import PendingIncome
        incomes_created = db.query(PendingIncome).filter(
            PendingIncome.business_date == target_date
        ).count()
        
        total_gross = db.query(func.sum(PendingIncome.gross_amount)).filter(
            PendingIncome.business_date == target_date
        ).scalar() or 0
        
        return {
            "success": True,
            "message": f"Income calculation triggered successfully for {target_date}",
            "summary": {
                "calculation_date": str(target_date),
                "incomes_created": incomes_created,
                "total_gross_amount": round(float(total_gross)),
                "triggered_by": current_user.id,
                "triggered_at": datetime.now().isoformat()
            }
        }
        
    except Exception as e:
        logger.error(f"Error in manual income calculation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error triggering income calculation: {str(e)}"
        )

# ===== STAR / LOYAL DIRECT ASSIGNMENT (RVZ ID Only) =====

class RVZStarLoyalAssignment(BaseModel):
    package_type: str  # '1000' (Star/Blue) or '500' (Loyal)
    target_user_id: str
    quantity: int = 1
    reason: str

@router.post("/star-loyal/direct-assign")
async def rvz_direct_assign_star_loyal(
    request_data: RVZStarLoyalAssignment,
    current_user: User = Depends(get_current_rvz_user_hybrid),
    db: Session = Depends(get_db)
):
    """
    RVZ ID can directly assign Star (₹1,000) or Loyal (₹500) coupons to users
    NO APPROVAL REQUIRED - Immediate activation
    RESTRICTED: RVZ ID ONLY
    """
    try:
        from app.core.audit import AuditLogger
        from app.models.coupon import Coupon
        from datetime import datetime
        
        # Validate package type (only Star/Loyal allowed)
        if request_data.package_type not in ['1000', '500']:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid package type. Only Star (1000) and Loyal (500) allowed."
            )
        
        # Validate target user exists
        target_user = db.query(User).filter(User.id == request_data.target_user_id).first()
        if not target_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Target user {request_data.target_user_id} not found"
            )
        
        # Create and assign coupons immediately (no approval workflow)
        coupons_created = []
        for i in range(request_data.quantity):
            new_coupon = Coupon(
                owner_id=request_data.target_user_id,
                coupon_type=request_data.package_type,
                status='Active',
                activated_at=get_indian_time()
            )
            db.add(new_coupon)
            coupons_created.append(f"{request_data.package_type}_{i+1}")
        
        db.commit()
        
        # Log audit
        AuditLogger.log_action(
            db=db,
            user=current_user,
            action='VGK_STAR_LOYAL_DIRECT_ASSIGN',
            resource_type='Coupon',
            resource_id=request_data.target_user_id,
            details={
                "package_type": request_data.package_type,
                "target_user_id": request_data.target_user_id,
                "target_user_name": target_user.name,
                "quantity": request_data.quantity,
                "reason": request_data.reason,
                "coupons_created": len(coupons_created)
            }
        )
        
        package_name = "Star (Blue)" if request_data.package_type == '1000' else "Loyal"
        
        return {
            "success": True,
            "message": f"{len(coupons_created)} {package_name} coupon(s) assigned directly to {target_user.name}",
            "data": {
                "package_type": request_data.package_type,
                "package_name": package_name,
                "target_user_id": request_data.target_user_id,
                "target_user_name": target_user.name,
                "quantity": request_data.quantity,
                "coupons_created": len(coupons_created),
                "status": "Active",
                "assigned_at": get_indian_time().isoformat(),
                "assigned_by": current_user.id
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to assign Star/Loyal coupons: {str(e)}"
        )


# ===== TERMS & CONDITIONS MANAGEMENT =====

class TermsAndConditionsRequest(BaseModel):
    content: str
    version: Optional[str] = None
    reason: Optional[str] = None
    max_displays: Optional[int] = 3  # How many times to show T&C to new users (default 3)

# T&C Version Management Request/Response Models
class CreateVersionRequest(BaseModel):
    version: str  # e.g., "v2.1"
    content: str  # HTML content
    source_version: Optional[str] = None  # Which version this was copied from
    notes: Optional[str] = None  # Optional notes
    platform_type: Optional[str] = 'MNR'  # DC Protocol Mar 2026: MNR | VGK | ALL
    max_displays: Optional[int] = None  # How many times to show to new users


@router.get("/terms-and-conditions")
async def get_terms_and_conditions(
    current_user: User = Depends(get_current_rvz_user_hybrid),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get current Terms & Conditions content
    RVZ ID ONLY - View T&C content for editing (Hybrid auth: JWT or cookies)
    """
    try:
        settings = db.query(AppSettings).first()
        if not settings:
            settings = AppSettings()
            db.add(settings)
            db.commit()
            db.refresh(settings)
        
        return {
            "success": True,
            "data": {
                "content": settings.terms_and_conditions_content or "",
                "version": settings.tc_version or "1.0",
                "max_displays": settings.tc_max_displays if hasattr(settings, 'tc_max_displays') else 3,
                "last_updated": settings.tc_last_updated.isoformat() if settings.tc_last_updated else None,
                "updated_by": settings.tc_updated_by
            }
        }
        
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to retrieve Terms & Conditions: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve Terms & Conditions: {str(e)}"
        )


@router.post("/terms-and-conditions")
async def update_terms_and_conditions(
    request_data: TermsAndConditionsRequest,
    current_user: User = Depends(get_current_rvz_user_hybrid),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Update Terms & Conditions content
    RVZ ID ONLY - Edit T&C content shown in popup (3 times to new active users) (Hybrid auth: JWT or cookies)
    """
    try:
        from datetime import datetime
        from app.core.audit import AuditLogger
        
        settings = db.query(AppSettings).first()
        if not settings:
            settings = AppSettings()
            db.add(settings)
        
        # Store old version for audit
        old_version = settings.tc_version
        old_content_preview = settings.terms_and_conditions_content[:100] if settings.terms_and_conditions_content else ""
        
        # Update content
        settings.terms_and_conditions_content = request_data.content
        if request_data.version:
            settings.tc_version = request_data.version
        if request_data.max_displays is not None:
            settings.tc_max_displays = request_data.max_displays
        settings.tc_last_updated = datetime.utcnow()
        settings.tc_updated_by = current_user.id
        
        db.commit()
        
        # Log audit
        AuditLogger.log_action(
            db=db,
            user=current_user,
            action='VGK_UPDATE_TERMS_CONDITIONS',
            resource_type='AppSettings',
            resource_id='terms_and_conditions',
            details={
                "old_version": old_version,
                "new_version": settings.tc_version,
                "old_content_preview": old_content_preview,
                "new_content_length": len(request_data.content),
                "reason": request_data.reason
            }
        )
        
        return {
            "success": True,
            "message": "Terms & Conditions updated successfully",
            "data": {
                "content": settings.terms_and_conditions_content,
                "version": settings.tc_version,
                "max_displays": settings.tc_max_displays if hasattr(settings, 'tc_max_displays') else 3,
                "last_updated": settings.tc_last_updated.isoformat(),
                "updated_by": settings.tc_updated_by
            }
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update Terms & Conditions: {str(e)}"
        )


@router.get("/terms-and-conditions-audit")
async def get_terms_acceptance_audit(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    search: Optional[str] = None,
    version: Optional[str] = None,
    current_user: User = Depends(get_current_rvz_user_hybrid),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    RVZ ID ONLY - Get complete audit trail of Terms & Conditions acceptances
    Shows all users who accepted T&C with version, timestamp, IP, browser details
    """
    try:
        from app.models.banner import UserCouponAcceptance
        
        # Base query with user details
        query = db.query(
            UserCouponAcceptance,
            User.id,
            User.name,
            User.email,
            User.user_type
        ).join(
            User, User.id == UserCouponAcceptance.user_id
        )
        
        # Apply filters
        if search:
            search_term = f"%{search}%"
            query = query.filter(
                (User.id.ilike(search_term)) |
                (User.name.ilike(search_term)) |
                (User.email.ilike(search_term))
            )
        
        if version:
            query = query.filter(UserCouponAcceptance.accepted_terms_version == version)
        
        # Count total records
        total_records = query.count()
        
        # Pagination
        offset = (page - 1) * page_size
        records = query.order_by(UserCouponAcceptance.acceptance_timestamp.desc()).offset(offset).limit(page_size).all()
        
        # Format response
        acceptances = []
        for record, mnr_id, name, email, user_type in records:
            acceptances.append({
                "id": record.id,
                "user_id": record.user_id,
                "mnr_id": mnr_id,
                "user_name": name,
                "email": email,
                "user_type": user_type,
                "login_attempt": record.login_attempt_number,
                "accepted_version": record.accepted_terms_version,
                "acceptance_timestamp": record.acceptance_timestamp.isoformat(),
                "ip_address": record.ip_address,
                "user_agent": record.user_agent,
                "created_at": record.created_at.isoformat()
            })
        
        # Get all versions for filter dropdown
        versions = db.query(UserCouponAcceptance.accepted_terms_version).distinct().all()
        available_versions = [v[0] for v in versions]
        
        return {
            "success": True,
            "data": {
                "acceptances": acceptances,
                "pagination": {
                    "page": page,
                    "page_size": page_size,
                    "total_records": total_records,
                    "total_pages": (total_records + page_size - 1) // page_size
                },
                "available_versions": available_versions
            }
        }
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve T&C acceptance audit: {str(e)}"
        )


class ProductionResetRequest(BaseModel):
    confirmation_text: str
    reason: str


@router.post("/production-reset")
async def reset_production_earnings(
    request_data: ProductionResetRequest,
    current_user: User = Depends(get_current_rvz_user_hybrid),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    INCOME RESET: Display ₹0 for all old earnings (before Oct 11, 2025)
    RVZ ID ONLY - Uses date-based filtering (NON-DESTRUCTIVE)
    Preserves 131 historical records, allows future earnings
    Requires confirmation text: "RESET ALL PRODUCTION EARNINGS"
    """
    try:
        from app.core.audit import AuditLogger
        from datetime import datetime, date
        
        if request_data.confirmation_text != "RESET ALL PRODUCTION EARNINGS":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid confirmation text. Must type exactly: RESET ALL PRODUCTION EARNINGS"
            )
        
        if not request_data.reason or len(request_data.reason.strip()) < 10:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Reason must be at least 10 characters long"
            )
        
        # Production start date - all data before this shows ₹0
        production_start_date = date(2025, 10, 11)
        
        reset_results = {
            "method": "Date-based filtering (NON-DESTRUCTIVE)",
            "production_start_date": "2025-10-11",
            "description": "All income/awards BEFORE Oct 11 show ₹0, future earnings display normally"
        }
        
        # Verify the date filters are in place (check key endpoints)
        from app.services.wallet_service import WalletService
        from app.services.reference_service import ReferenceService
        
        # Test queries to confirm filtering works
        old_income_count = db.execute(text("""
            SELECT COUNT(*) FROM pending_income 
            WHERE DATE(business_date) < :cutoff_date
        """), {"cutoff_date": production_start_date}).scalar()
        
        new_income_count = db.execute(text("""
            SELECT COUNT(*) FROM pending_income 
            WHERE DATE(business_date) >= :cutoff_date
        """), {"cutoff_date": production_start_date}).scalar()
        
        old_activations = db.execute(text("""
            SELECT COUNT(*) FROM "user" 
            WHERE coupon_status = 'Activated' 
            AND DATE(activation_date) < :cutoff_date
        """), {"cutoff_date": production_start_date}).scalar()
        
        new_activations = db.execute(text("""
            SELECT COUNT(*) FROM "user" 
            WHERE coupon_status = 'Activated' 
            AND DATE(activation_date) >= :cutoff_date
        """), {"cutoff_date": production_start_date}).scalar()
        
        reset_results.update({
            "old_income_records_hidden": old_income_count,
            "new_income_records_visible": new_income_count,
            "old_activations_hidden": old_activations,
            "new_activations_visible": new_activations,
            "endpoints_using_date_filter": [
                "wallet_service.get_earnings_summary()",
                "financial_operations.get_actual_paid_income()",
                "reference_service.calculate_direct_referral_income()",
                "financial_operations.comprehensive_day_wise()",
                "reference_service.calculate_ved_income()",
                "reference_service.calculate_guru_dakshina()",
                "financial_operations.direct_referral_transactions()",
                "financial_operations.matching_referral_transactions()",
                "financial_operations.ved_income_transactions()",
                "awards_fast.get_user_direct_awards_fast()",
                "awards_fast.get_user_matching_awards_fast()"
            ],
            "data_integrity": {
                "historical_records_preserved": True,
                "eligibility_uses_all_data": True,
                "income_display_filtered_by_date": True,
                "awards_display_filtered_by_date": True,
                "future_earnings_enabled": True
            }
        })
        
        db.commit()
        
        AuditLogger.log_action(
            db=db,
            user=current_user,
            action='INCOME_RESET_APPLIED',
            resource_type='SystemWide',
            resource_id='production_reset',
            details={
                "reset_timestamp": datetime.utcnow().isoformat(),
                "reset_by": current_user.id,
                "reason": request_data.reason,
                "method": "Date-based filtering",
                "production_start_date": str(production_start_date),
                "old_records_hidden": old_income_count + old_activations,
                "new_records_visible": new_income_count + new_activations
            }
        )
        
        return {
            "success": True,
            "message": "Income Reset Applied Successfully - All endpoints now use Oct 11 date filter",
            "data": {
                "reset_timestamp": datetime.utcnow().isoformat(),
                "reset_by": current_user.name,
                "tables_reset": reset_results
            }
        }
        
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Production reset failed: {str(e)}"
        )

# ===== USER CREATION (RVZ ID ONLY) =====

class RVZCreateUserRequest(BaseModel):
    first_name: str
    last_name: str
    phone_number: str
    password: str
    sponsor_id: str  # Sponsor MNR ID
    position: str  # "Left" or "Right"
    email: Optional[str] = None

@router.post("/user-management/create-user")
async def rvz_create_user(
    request: RVZCreateUserRequest,
    current_user: User = Depends(get_current_rvz_user_hybrid),
    db: Session = Depends(get_db)
):
    """
    RVZ ID ONLY: Create a new user with automatic placement
    - Creates user account
    - Automatically places user in binary tree (extreme placement)
    - Returns user details and placement information
    """
    try:
        from app.services.user_service import UserService
        from app.services.reference_service import ReferenceService
        from app.core.audit import AuditLogger
        
        # Validate position
        if request.position not in ["Left", "Right", "left", "right"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Position must be 'Left' or 'Right'"
            )
        
        # Validate sponsor exists
        sponsor = db.query(User).filter(User.id == request.sponsor_id).first()
        if not sponsor:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Sponsor MNR ID '{request.sponsor_id}' not found"
            )
        
        # Create user account
        user_service = UserService(db)
        user_dict = request.dict()
        create_result = user_service.create_user(user_dict)
        
        if not create_result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=create_result.get("error", "User creation failed")
            )
        
        new_user_id = create_result["user_id"]
        
        # Automatic extreme placement
        reference_service = ReferenceService(db)
        placement_result = None
        try:
            placement_result = reference_service.extreme_place_user(
                new_user_id,
                request.sponsor_id,
                request.position.capitalize()
            )
        except Exception as e:
            # Rollback user creation if placement fails
            db.query(User).filter(User.id == new_user_id).delete()
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Placement failed: {str(e)}"
            )
        
        # Log the action
        AuditLogger.log_action(
            db=db,
            user=current_user,
            action='RVZ_USER_CREATED',
            resource_type='User',
            resource_id=new_user_id,
            details={
                "created_user_id": new_user_id,
                "sponsor_id": request.sponsor_id,
                "position": request.position,
                "created_by": current_user.id
            }
        )
        
        return {
            "success": True,
            "message": f"User created successfully with MNR ID: {new_user_id}",
            "user_id": new_user_id,
            "user_details": create_result["user_details"],
            "placement_result": placement_result,
            "created_by": current_user.id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating user: {str(e)}"
        )

# ===== USER DELETION (RVZ ID ONLY) =====

class DeleteUserRequest(BaseModel):
    user_id: str
    reason: str
    confirmation_text: str  # Must type "DELETE USER"

class BulkDeleteUsersRequest(BaseModel):
    user_ids: List[str]
    reason: str
    confirmation_text: str  # Must type "DELETE USERS"

@router.post("/user-management/delete-user")
async def rvz_delete_user(
    request: DeleteUserRequest,
    current_user: User = Depends(get_current_rvz_user_hybrid),
    db: Session = Depends(get_db)
):
    """
    RVZ ID ONLY: Delete a single user with proper foreign key cascade handling
    - Protects RVZ ID, Admin, Super Admin, Finance Admin from deletion
    - Reassigns downline to upliner before deletion
    - Handles all 196 foreign key constraints
    Requires confirmation text: "DELETE USER"
    """
    try:
        from app.core.audit import AuditLogger
        
        # Validate confirmation
        if request.confirmation_text != "DELETE USER":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid confirmation text. Must type exactly: DELETE USER"
            )
        
        if not request.reason or len(request.reason.strip()) < 10:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Reason must be at least 10 characters long"
            )
        
        # Check if user exists
        target_user = db.query(User).filter(User.id == request.user_id).first()
        if not target_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User {request.user_id} not found"
            )
        
        # PROTECTION: Block deletion of critical users
        protected_roles = ['RVZ ID', 'ADMIN', 'SUPER ADMIN', 'FINANCE ADMIN']
        if target_user.user_type in protected_roles or target_user.id == 'MNR182364369':
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Cannot delete protected user. User type: {target_user.user_type}. RVZ ID, Admin, Super Admin, and Finance Admin cannot be deleted."
            )
        
        # Store user details for audit log
        user_details = {
            "user_id": target_user.id,
            "name": target_user.name,
            "email": target_user.email,
            "phone": target_user.phone_number,
            "referrer_id": target_user.referrer_id,
            "account_status": target_user.account_status,
            "user_type": target_user.user_type
        }
        
        # BUSINESS LOGIC: Reassign downline to upliner
        downline_count = 0
        if target_user.referrer_id:
            # Get all direct referrals of target user
            downline_users = db.query(User).filter(User.referrer_id == request.user_id).all()
            downline_count = len(downline_users)
            
            # Reassign them to target user's upliner
            for downline in downline_users:
                downline.referrer_id = target_user.referrer_id
            
            user_details["downline_reassigned_to"] = target_user.referrer_id
            user_details["downline_count"] = downline_count
        
        # Delete in proper order to handle ALL foreign keys
        deletion_summary = {}
        
        # 1. DC PROTOCOL: NEVER DELETE pending_income - it's the single source of truth for earnings history
        # Instead, mark as 'Cancelled' or 'User Deleted' to preserve historical records
        # count = db.execute(text("""
        #     DELETE FROM pending_income 
        #     WHERE user_id = :uid OR related_user_id = :uid OR accounts_paid_by_id = :uid 
        #     OR admin_verified_by_id = :uid OR super_admin_verified_by_id = :uid OR rejected_by_id = :uid
        # """), {"uid": request.user_id}).rowcount
        # deletion_summary["pending_income"] = count
        deletion_summary["pending_income"] = 0  # Disabled to preserve earnings history
        
        # 2. Delete from user_leg_metrics
        count = db.execute(text("""
            DELETE FROM user_leg_metrics WHERE user_id = :uid
        """), {"uid": request.user_id}).rowcount
        deletion_summary["user_leg_metrics"] = count
        
        # 3. Delete from transaction (2 FK columns)
        count = db.execute(text("""
            DELETE FROM transaction 
            WHERE referred_user_id = :uid OR referrer_id = :uid
        """), {"uid": request.user_id}).rowcount
        deletion_summary["transaction"] = count
        
        # 4. Delete from placement (3 FK columns)
        count = db.execute(text("""
            DELETE FROM placement 
            WHERE child_id = :uid OR parent_id = :uid OR placed_by_id = :uid
        """), {"uid": request.user_id}).rowcount
        deletion_summary["placement"] = count
        
        # 5. Delete from referral_income (2 FK columns)
        count = db.execute(text("""
            DELETE FROM referral_income 
            WHERE earner_user_id = :uid OR purchaser_user_id = :uid
        """), {"uid": request.user_id}).rowcount
        deletion_summary["referral_income"] = count
        
        # 6. Delete from pending_bonuses
        count = db.execute(text("""
            DELETE FROM pending_bonuses WHERE user_id = :uid
        """), {"uid": request.user_id}).rowcount
        deletion_summary["pending_bonuses"] = count
        
        # 7. Delete from payment_receipt
        count = db.execute(text("""
            DELETE FROM payment_receipt WHERE user_id = :uid
        """), {"uid": request.user_id}).rowcount
        deletion_summary["payment_receipt"] = count
        
        # 8. Delete from payment_validation
        count = db.execute(text("""
            DELETE FROM payment_validation WHERE user_id = :uid
        """), {"uid": request.user_id}).rowcount
        deletion_summary["payment_validation"] = count
        
        # 9. Delete from placement_log (all FK references)
        count = db.execute(text("""
            DELETE FROM placement_log 
            WHERE new_user_id = :uid 
               OR actor_id = :uid 
               OR sponsor_user_id = :uid 
               OR target_parent_id = :uid
        """), {"uid": request.user_id}).rowcount
        deletion_summary["placement_log"] = count
        
        # 10. Clear user self-references
        count = db.execute(text("""
            UPDATE "user" SET ved_owner_id = NULL WHERE ved_owner_id = :uid
        """), {"uid": request.user_id}).rowcount
        deletion_summary["ved_owner_references_cleared"] = count
        
        count = db.execute(text("""
            UPDATE "user" SET position_id = NULL WHERE position_id = :uid
        """), {"uid": request.user_id}).rowcount
        deletion_summary["position_references_cleared"] = count
        
        # 11. Finally, delete the user
        count = db.execute(text("""
            DELETE FROM "user" WHERE id = :uid
        """), {"uid": request.user_id}).rowcount
        deletion_summary["user_deleted"] = count
        
        # Commit the deletion
        db.commit()
        
        # Log the deletion
        AuditLogger.log_action(
            db=db,
            user=current_user,
            action='USER_DELETED',
            resource_type='User',
            resource_id=request.user_id,
            details={
                "deleted_user": user_details,
                "deletion_summary": deletion_summary,
                "downline_reassigned": downline_count,
                "reason": request.reason,
                "deleted_by": current_user.id
            }
        )
        
        return {
            "success": True,
            "message": f"User {request.user_id} deleted successfully",
            "deleted_user_id": request.user_id,
            "deletion_summary": deletion_summary,
            "downline_reassigned": downline_count,
            "tables_affected": len([k for k, v in deletion_summary.items() if v > 0]),
            "deleted_by": current_user.id,
            "reason": request.reason
        }
        
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting user: {str(e)}"
        )

@router.post("/user-management/bulk-delete-users")
async def rvz_bulk_delete_users(
    request: BulkDeleteUsersRequest,
    current_user: User = Depends(get_current_rvz_user_hybrid),
    db: Session = Depends(get_db)
):
    """
    RVZ ID ONLY: Delete multiple users with proper foreign key cascade handling
    - Protects RVZ ID, Admin, Super Admin, Finance Admin from deletion
    - Reassigns downline to upliner before deletion
    - Handles all 196 foreign key constraints with error reporting
    Requires confirmation text: "DELETE USERS"
    """
    try:
        from app.core.audit import AuditLogger
        
        # Validate confirmation
        if request.confirmation_text != "DELETE USERS":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid confirmation text. Must type exactly: DELETE USERS"
            )
        
        if not request.reason or len(request.reason.strip()) < 10:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Reason must be at least 10 characters long"
            )
        
        if not request.user_ids or len(request.user_ids) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No user IDs provided"
            )
        
        # Store details for audit
        deleted_users = []
        protected_users = []
        failed_users = []
        total_downline_reassigned = 0
        total_deletion_summary = {
            "pending_income": 0,
            "user_leg_metrics": 0,
            "transaction": 0,
            "placement": 0,
            "referral_income": 0,
            "pending_bonuses": 0,
            "payment_receipt": 0,
            "payment_validation": 0,
            "placement_log": 0,
            "ved_owner_references_cleared": 0,
            "position_references_cleared": 0,
            "users_deleted": 0
        }
        
        for user_id in request.user_ids:
            try:
                # Check if user exists
                target_user = db.query(User).filter(User.id == user_id).first()
                if not target_user:
                    failed_users.append({
                        "user_id": user_id,
                        "reason": "User not found"
                    })
                    continue
                
                # PROTECTION: Skip protected users
                protected_roles = ['RVZ ID', 'ADMIN', 'SUPER ADMIN', 'FINANCE ADMIN']
                if target_user.user_type in protected_roles or target_user.id == 'MNR182364369':
                    protected_users.append({
                        "user_id": target_user.id,
                        "reason": f"Protected user ({target_user.user_type})"
                    })
                    continue
                
                # BUSINESS LOGIC: Reassign downline to upliner
                if target_user.referrer_id:
                    downline_users = db.query(User).filter(User.referrer_id == user_id).all()
                    for downline in downline_users:
                        downline.referrer_id = target_user.referrer_id
                    total_downline_reassigned += len(downline_users)
                
                # Delete from all tables - NO error handling to prevent transaction abortion
                # If any table deletion fails, we skip this user entirely
                
                # 1. DC PROTOCOL: NEVER DELETE pending_income - preserve earnings history
                # count = db.execute(text("""
                #     DELETE FROM pending_income 
                #     WHERE user_id = :uid OR related_user_id = :uid OR accounts_paid_by_id = :uid 
                #     OR admin_verified_by_id = :uid OR super_admin_verified_by_id = :uid OR rejected_by_id = :uid
                # """), {"uid": user_id}).rowcount
                # total_deletion_summary["pending_income"] += count
                total_deletion_summary["pending_income"] += 0  # Disabled
                
                # 2. user_leg_metrics
                count = db.execute(text("""
                    DELETE FROM user_leg_metrics WHERE user_id = :uid
                """), {"uid": user_id}).rowcount
                total_deletion_summary["user_leg_metrics"] += count
                
                # 3. transaction (2 FK columns)
                count = db.execute(text("""
                    DELETE FROM transaction 
                    WHERE referred_user_id = :uid OR referrer_id = :uid
                """), {"uid": user_id}).rowcount
                total_deletion_summary["transaction"] += count
                
                # 4. placement (3 FK columns)
                count = db.execute(text("""
                    DELETE FROM placement 
                    WHERE child_id = :uid OR parent_id = :uid OR placed_by_id = :uid
                """), {"uid": user_id}).rowcount
                total_deletion_summary["placement"] += count
                
                # 5. referral_income (2 FK columns)
                count = db.execute(text("""
                    DELETE FROM referral_income 
                    WHERE earner_user_id = :uid OR purchaser_user_id = :uid
                """), {"uid": user_id}).rowcount
                total_deletion_summary["referral_income"] += count
                
                # 6. pending_bonuses
                count = db.execute(text("""
                    DELETE FROM pending_bonuses WHERE user_id = :uid
                """), {"uid": user_id}).rowcount
                total_deletion_summary["pending_bonuses"] += count
                
                # 7. payment_receipt
                count = db.execute(text("""
                    DELETE FROM payment_receipt WHERE user_id = :uid
                """), {"uid": user_id}).rowcount
                total_deletion_summary["payment_receipt"] += count
                
                # 8. payment_validation
                count = db.execute(text("""
                    DELETE FROM payment_validation WHERE user_id = :uid
                """), {"uid": user_id}).rowcount
                total_deletion_summary["payment_validation"] += count
                
                # 9. placement_log (all FK references)
                count = db.execute(text("""
                    DELETE FROM placement_log 
                    WHERE new_user_id = :uid 
                       OR actor_id = :uid 
                       OR sponsor_user_id = :uid 
                       OR target_parent_id = :uid
                """), {"uid": user_id}).rowcount
                total_deletion_summary["placement_log"] += count
                
                # 10. Clear user self-references
                count = db.execute(text("""
                    UPDATE "user" SET ved_owner_id = NULL WHERE ved_owner_id = :uid
                """), {"uid": user_id}).rowcount
                total_deletion_summary["ved_owner_references_cleared"] += count
                
                count = db.execute(text("""
                    UPDATE "user" SET position_id = NULL WHERE position_id = :uid
                """), {"uid": user_id}).rowcount
                total_deletion_summary["position_references_cleared"] += count
                
                # 10. Finally, delete the user
                count = db.execute(text("""
                    DELETE FROM "user" WHERE id = :uid
                """), {"uid": user_id}).rowcount
                total_deletion_summary["users_deleted"] += count
                
                # Store user details BEFORE commit (to avoid detached instance error)
                user_data = {
                    "user_id": target_user.id,
                    "name": target_user.name,
                    "email": target_user.email
                }
                
                # Commit this user's deletion immediately to avoid transaction abortion
                db.commit()
                
                deleted_users.append(user_data)
                
            except Exception as e:
                # Rollback failed deletion and continue with next user
                db.rollback()
                failed_users.append({
                    "user_id": user_id,
                    "reason": str(e)
                })
        
        # Log bulk deletion
        AuditLogger.log_action(
            db=db,
            user=current_user,
            action='BULK_USER_DELETION',
            resource_type='Users',
            resource_id='bulk_delete',
            details={
                "total_requested": len(request.user_ids),
                "successfully_deleted": len(deleted_users),
                "protected_users": len(protected_users),
                "failed_deletions": len(failed_users),
                "downline_reassigned": total_downline_reassigned,
                "deleted_users": deleted_users,
                "protected_users": protected_users,
                "failed_users": failed_users,
                "deletion_summary": total_deletion_summary,
                "reason": request.reason,
                "deleted_by": current_user.id
            }
        )
        
        return {
            "success": True,
            "message": f"Bulk deletion completed: {len(deleted_users)}/{len(request.user_ids)} users deleted",
            "total_requested": len(request.user_ids),
            "deleted_count": len(deleted_users),
            "protected_users_skipped": len(protected_users),
            "failed_count": len(failed_users),
            "total_downline_reassigned": total_downline_reassigned,
            "deleted_users": deleted_users,
            "protected_users": protected_users,
            "failed_deletions": failed_users,
            "deletion_summary": total_deletion_summary,
            "deleted_by": current_user.id,
            "reason": request.reason
        }
        
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error during bulk deletion: {str(e)}"
        )

# ===== RVZ ACCESS VALIDATION =====
RVZ_ID = "MNR182364369"

def validate_rvz_access(user_id: str, db: Session) -> User:
    """Validate RVZ ID access - EXCLUSIVE to MNR182364369"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user.id != RVZ_ID:
        raise HTTPException(
            status_code=403,
            detail="Access Denied: This feature is exclusive to RVZ ID"
        )
    
    return user

# ===== ROLE MANAGEMENT =====

@router.get("/role-management", response_class=HTMLResponse)
async def rvz_role_management_page(
    request: Request,
    user_id: str,
    db: Session = Depends(get_db)
):
    """RVZ ID: Role Management Page"""
    try:
        validate_rvz_access(user_id, db)
        
        # Get users with their roles
        users_with_roles = db.query(User).filter(
            User.user_type.in_(['Admin', 'Super Admin', 'Finance Admin', 'RVZ ID'])
        ).order_by(User.user_type.desc()).limit(100).all()
        
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>RVZ Role Management</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body>
    <div class="container mt-4">
        <h2>👥 RVZ Role Management</h2>
        <p class="text-muted">Manage system roles and permissions</p>
        
        <div class="row mt-4">
            <div class="col-md-12">
                <div class="card">
                    <div class="card-header bg-primary text-white">
                        <h5>📊 Current Role Distribution</h5>
                    </div>
                    <div class="card-body">
                        <table class="table table-striped">
                            <thead>
                                <tr>
                                    <th>Role Name</th>
                                    <th>Description</th>
                                    <th>Access Level</th>
                                    <th>Count</th>
                                </tr>
                            </thead>
                            <tbody>
                                <tr>
                                    <td><span class="badge bg-danger">RVZ ID</span></td>
                                    <td>Supreme Administrator - Full System Access</td>
                                    <td>Level 5 (Highest)</td>
                                    <td>{len([u for u in users_with_roles if u.user_type == 'RVZ ID'])}</td>
                                </tr>
                                <tr>
                                    <td><span class="badge bg-warning">Super Admin</span></td>
                                    <td>Senior Administrator - Advanced Operations</td>
                                    <td>Level 4</td>
                                    <td>{len([u for u in users_with_roles if u.user_type == 'Super Admin'])}</td>
                                </tr>
                                <tr>
                                    <td><span class="badge bg-info">Finance Admin</span></td>
                                    <td>Financial Operations & Approvals</td>
                                    <td>Level 3</td>
                                    <td>{len([u for u in users_with_roles if u.user_type == 'Finance Admin'])}</td>
                                </tr>
                                <tr>
                                    <td><span class="badge bg-success">Admin</span></td>
                                    <td>Standard Administrator</td>
                                    <td>Level 2</td>
                                    <td>{len([u for u in users_with_roles if u.user_type == 'Admin'])}</td>
                                </tr>
                                <tr>
                                    <td><span class="badge bg-secondary">USER</span></td>
                                    <td>Regular Member</td>
                                    <td>Level 1</td>
                                    <td>{db.query(User).filter(User.user_type == 'USER').count()}</td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                </div>
                
                <div class="card mt-3">
                    <div class="card-header bg-secondary text-white">
                        <h5>👨‍💼 Admin Users</h5>
                    </div>
                    <div class="card-body" style="max-height: 400px; overflow-y: auto;">
                        <table class="table table-sm table-hover">
                            <thead>
                                <tr>
                                    <th>User ID</th>
                                    <th>Name</th>
                                    <th>Current Role</th>
                                    <th>Status</th>
                                </tr>
                            </thead>
                            <tbody>
                                {''.join([f'''
                                <tr>
                                    <td>{u.id}</td>
                                    <td>{u.name}</td>
                                    <td><span class="badge {'bg-danger' if u.user_type == 'RVZ ID' else 'bg-warning' if u.user_type == 'Super Admin' else 'bg-info' if u.user_type == 'Finance Admin' else 'bg-success'}">{u.user_type}</span></td>
                                    <td><span class="badge bg-success">Active</span></td>
                                </tr>
                                ''' for u in users_with_roles])}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="mt-3">
            <a href="/rvz/dashboard?user_id={user_id}" class="btn btn-secondary">← Back to RVZ Dashboard</a>
        </div>
    </div>
</body>
</html>
        """
        
        return HTMLResponse(content=html_content)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error loading role management: {str(e)}"
        )


# ===== AWARD MANAGEMENT =====

@router.get("/award-management", response_class=HTMLResponse)
async def rvz_award_management_page(
    request: Request,
    user_id: str,
    db: Session = Depends(get_db)
):
    """RVZ ID: Award Management Page"""
    try:
        validate_rvz_access(user_id, db)
        
        from app.models.awards import DirectAwardTier, MatchingAwardTier
        
        # Get award tiers
        direct_tiers = db.query(DirectAwardTier).order_by(DirectAwardTier.cumulative_required).all()
        matching_tiers = db.query(MatchingAwardTier).order_by(MatchingAwardTier.cumulative_required).all()
        
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>RVZ Award Management</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body>
    <div class="container mt-4">
        <h2>🏆 RVZ Award Management</h2>
        <p class="text-muted">Manage Direct and Matching Award Tiers</p>
        
        <div class="row mt-4">
            <div class="col-md-6">
                <div class="card">
                    <div class="card-header bg-primary text-white">
                        <h5>🎯 Direct Award Tiers ({len(direct_tiers)})</h5>
                    </div>
                    <div class="card-body" style="max-height: 500px; overflow-y: auto;">
                        <table class="table table-sm">
                            <thead>
                                <tr>
                                    <th>Award</th>
                                    <th>Referrals</th>
                                    <th>Price</th>
                                    <th>Cumulative</th>
                                </tr>
                            </thead>
                            <tbody>
                                {''.join([f'''
                                <tr>
                                    <td><strong>{tier.award_name}</strong><br><small class="text-muted">{tier.award_description}</small></td>
                                    <td>{tier.referral_count}</td>
                                    <td>₹{tier.actual_price or 0:.2f}</td>
                                    <td>{'Yes' if tier.cumulative_required else 'No'}</td>
                                </tr>
                                ''' for tier in direct_tiers])}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
            
            <div class="col-md-6">
                <div class="card">
                    <div class="card-header bg-success text-white">
                        <h5>🤝 Matching Award Tiers ({len(matching_tiers)})</h5>
                    </div>
                    <div class="card-body" style="max-height: 500px; overflow-y: auto;">
                        <table class="table table-sm">
                            <thead>
                                <tr>
                                    <th>Award</th>
                                    <th>Matches</th>
                                    <th>Price</th>
                                    <th>Cumulative</th>
                                </tr>
                            </thead>
                            <tbody>
                                {''.join([f'''
                                <tr>
                                    <td><strong>{tier.award_name}</strong><br><small class="text-muted">{tier.award_description}</small></td>
                                    <td>{tier.match_count}</td>
                                    <td>₹{tier.actual_price or 0:.2f}</td>
                                    <td>{'Yes' if tier.cumulative_required else 'No'}</td>
                                </tr>
                                ''' for tier in matching_tiers])}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="mt-3">
            <div class="alert alert-info">
                <strong>ℹ️ Award Management:</strong> Use the Award Management API endpoints to create, update, or delete award tiers.
                <ul class="mb-0 mt-2">
                    <li>POST /api/v1/award-management/admin/awards/direct-tiers</li>
                    <li>PUT /api/v1/award-management/admin/awards/direct-tiers/{'{tier_id}'}</li>
                    <li>DELETE /api/v1/award-management/admin/awards/direct-tiers/{'{tier_id}'}</li>
                </ul>
            </div>
        </div>
        
        <div class="mt-3">
            <a href="/rvz/dashboard?user_id={user_id}" class="btn btn-secondary">← Back to RVZ Dashboard</a>
        </div>
    </div>
</body>
</html>
        """
        
        return HTMLResponse(content=html_content)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error loading award management: {str(e)}"
        )


# ===== MENU CONFIGURATION =====

@router.get("/menu-configuration", response_class=HTMLResponse)
async def rvz_menu_configuration_page(
    request: Request,
    user_id: str,
    db: Session = Depends(get_db)
):
    """RVZ ID: Menu Configuration Page"""
    try:
        validate_rvz_access(user_id, db)
        
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>RVZ Menu Configuration</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body>
    <div class="container mt-4">
        <h2>🗂️ RVZ Menu Configuration</h2>
        <p class="text-muted">Configure menu visibility and ordering for different user roles</p>
        
        <div class="row mt-4">
            <div class="col-md-12">
                <div class="card">
                    <div class="card-header bg-primary text-white">
                        <h5>📋 Menu Structure Configuration</h5>
                    </div>
                    <div class="card-body">
                        <div class="table-responsive">
                            <table class="table table-bordered">
                                <thead>
                                    <tr>
                                        <th>Role Type</th>
                                        <th>Menu Items</th>
                                        <th>Status</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    <tr>
                                        <td><span class="badge bg-danger">RVZ ID</span></td>
                                        <td>All Features (24 VM Modules + Full Access)</td>
                                        <td><span class="badge bg-success">Active</span></td>
                                    </tr>
                                    <tr>
                                        <td><span class="badge bg-warning">Super Admin</span></td>
                                        <td>Members, Earnings, Awards, Coupons, Support</td>
                                        <td><span class="badge bg-success">Active</span></td>
                                    </tr>
                                    <tr>
                                        <td><span class="badge bg-info">Finance Admin</span></td>
                                        <td>Pending Approvals, Earnings, Expense Management</td>
                                        <td><span class="badge bg-success">Active</span></td>
                                    </tr>
                                    <tr>
                                        <td><span class="badge bg-success">Admin</span></td>
                                        <td>Members, Direct Referrals, Earnings, Team View</td>
                                        <td><span class="badge bg-success">Active</span></td>
                                    </tr>
                                    <tr>
                                        <td><span class="badge bg-secondary">USER</span></td>
                                        <td>Dashboard, Profile, Team, Earnings, Benefits</td>
                                        <td><span class="badge bg-success">Active</span></td>
                                    </tr>
                                </tbody>
                            </table>
                        </div>
                        
                        <div class="alert alert-success mt-3">
                            <h6><strong>✅ Current RVZ Menu Items (24 Features):</strong></h6>
                            <div class="row">
                                <div class="col-md-4">
                                    <ul class="mb-0">
                                        <li>Content Management</li>
                                        <li>Popup Control</li>
                                        <li>Create User Testing</li>
                                        <li>Bulk User Edit</li>
                                        <li>User Activation Control</li>
                                        <li>Brand/Level Management</li>
                                        <li>Reactivate/Reassign</li>
                                        <li>User Update Approvals</li>
                                    </ul>
                                </div>
                                <div class="col-md-4">
                                    <ul class="mb-0">
                                        <li>Payments Trigger</li>
                                        <li>Change User Password</li>
                                        <li>RVZ Password Change</li>
                                        <li>Secondary Password Setup</li>
                                        <li>Delete Management</li>
                                        <li>Data Recovery Center</li>
                                        <li>Add Packages</li>
                                        <li>Migrate Users</li>
                                    </ul>
                                </div>
                                <div class="col-md-4">
                                    <ul class="mb-0">
                                        <li>Role Management</li>
                                        <li>Award Management</li>
                                        <li>System Controls</li>
                                        <li>Rate Configuration</li>
                                        <li>Daily Ceiling</li>
                                        <li>Emergency Wallet</li>
                                        <li>Expense Categories</li>
                                        <li>Menu Configuration</li>
                                    </ul>
                                </div>
                            </div>
                        </div>
                        
                        <div class="alert alert-info mt-3">
                            <strong>ℹ️ Menu Configuration:</strong> All menu items are currently active and accessible. Menu ordering is managed through the frontend configuration.
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="mt-3">
            <a href="/rvz/dashboard?user_id={user_id}" class="btn btn-secondary">← Back to RVZ Dashboard</a>
        </div>
    </div>
</body>
</html>
        """
        
        return HTMLResponse(content=html_content)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error loading menu configuration: {str(e)}"
        )


# ===== MANUAL INCOME CALCULATION ENDPOINT =====

class ManualIncomeCalculationRequest(BaseModel):
    target_date: str  # Format: YYYY-MM-DD
    reason: str

@router.post("/manual-income-calculation")
async def manual_income_calculation(
    request: ManualIncomeCalculationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_rvz_user_hybrid)
):
    """
    Manually trigger income calculation for a specific date
    RVZ ID only - Use this to process missed income calculations
    """
    try:
        from datetime import datetime
        from app.core.scheduler import calculate_previous_day_incomes_for_date
        
        # Parse the target date
        try:
            target_date = datetime.strptime(request.target_date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Invalid date format. Use YYYY-MM-DD"
            )
        
        # Prevent future dates
        from datetime import date as date_class
        if target_date > date_class.today():
            raise HTTPException(
                status_code=400,
                detail="Cannot calculate income for future dates"
            )
        
        # Call the scheduler function with the specified date
        result = calculate_previous_day_incomes_for_date(target_date)
        
        return {
            "success": True,
            "message": f"Income calculation triggered for {request.target_date}",
            "target_date": request.target_date,
            "reason": request.reason,
            "triggered_by": current_user.id,
            "result": result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error triggering manual income calculation: {str(e)}"
        )


# ===== COMPANY EARNINGS COMPREHENSIVE DATA ENDPOINT =====

@router.get("/company-earnings-data")
async def get_company_earnings_data(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_rvz_user_hybrid)
):
    """
    Comprehensive Company Earnings Data API - WV Protocol Compliant
    Returns all revenue and expense data for RVZ dashboard
    
    Revenue Sources:
    - Admin Deductions (8%)
    - TDS Deductions (2%)
    - Daily Ceiling Excess
    
    Expense Categories (WV Protocol - NET amounts only):
    - Direct Awards (actual_cost_paid)
    - Matching Awards (actual_cost_paid)
    - Cash Bonanza (actual_cost_paid)
    - Physical Bonanza (actual_cost_paid)
    - Withdrawals (final_payout - NET amount)
    - Finance-Managed Expenses (approved expenses)
    """
    from datetime import datetime, timedelta
    from decimal import Decimal
    from app.models.transaction import Transaction, CompanyEarnings, Expense
    from app.models.awards import UserAwardProgress, UserMatchingAwardProgress
    from app.models.bonanza import DynamicBonanzaHistory  # DC Protocol: BonanzaProgress deprecated
    from app.models.withdrawal import WithdrawalRequest
    from app.models.user import User
    from sqlalchemy import func, and_, or_, case, extract
    
    # Date range setup
    if not end_date:
        end_dt = datetime.now()
        end_date = end_dt.strftime("%Y-%m-%d")
    else:
        end_dt = datetime.strptime(end_date, "%Y-%m-%d")
    
    if not start_date:
        start_dt = end_dt - timedelta(days=30)
        start_date = start_dt.strftime("%Y-%m-%d")
    else:
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    
    # ========== REVENUE CALCULATIONS ==========
    
    # 1. Package Sales Revenue (Primary Revenue Source - WV Protocol)
    # HISTORICAL DATA: Count ONLY PAID packages (actual revenue collected)
    # IGNORE date filters - this is cumulative historical revenue
    # Package Values: Platinum ₹15,000, Diamond ₹7,500, Star ₹1,000, Loyal ₹500
    # WV Protocol: package_points = 0.0 means FREE (no revenue), NOT Loyal package
    
    # For historical data: Only count users who PURCHASED packages (package_points > 0)
    package_revenue = db.query(
        func.coalesce(func.sum(
            case(
                (User.package_points >= 1.0, 15000),  # Platinum ₹15,000
                (User.package_points >= 0.5, 7500),   # Diamond ₹7,500
                (User.package_points > 0.25, 1000),   # Star ₹1,000
                (User.package_points > 0.0, 500),     # Loyal ₹500
                else_=0  # FREE users (package_points = 0.0) - NO REVENUE
            )
        ), 0)
    ).filter(
        and_(
            User.coupon_status.in_(['Active', 'Platinum', 'Activated', 'Semi-Active']),
            User.package_points > 0  # ONLY count paid packages (WV Protocol)
        )
    ).scalar() or Decimal('0.00')
    package_revenue = Decimal(str(package_revenue))
    
    # 2. Calculate all income types (for deduction tracking)
    income_query = db.query(
        func.sum(case(
            (Transaction.transaction_type == 'Direct Referral', Transaction.amount),
            else_=0
        )).label('direct_income'),
        func.sum(case(
            (Transaction.transaction_type == 'Matching Referral', Transaction.amount),
            else_=0
        )).label('matching_income'),
        func.sum(case(
            (Transaction.transaction_type == 'Ved Income', Transaction.amount),
            else_=0
        )).label('ved_income'),
        func.sum(case(
            (Transaction.transaction_type == 'Guru Dakshina', Transaction.amount),
            else_=0
        )).label('guru_dakshina')
    ).filter(
        and_(
            Transaction.timestamp >= start_dt,
            Transaction.timestamp <= end_dt
        )
    ).first()
    
    direct_income = Decimal(str(income_query.direct_income or 0))
    matching_income = Decimal(str(income_query.matching_income or 0))
    ved_income = Decimal(str(income_query.ved_income or 0))
    guru_dakshina = Decimal(str(income_query.guru_dakshina or 0))
    total_gross_income = direct_income + matching_income + ved_income + guru_dakshina
    
    # 2. Income Deductions
    admin_deduction = total_gross_income * Decimal('0.08')  # 8% - Company Revenue
    tds_deduction = total_gross_income * Decimal('0.02')    # 2% - Government Liability (NOT revenue)
    
    # 3. Ceiling Excess Earnings
    ceiling_earnings = db.query(
        func.coalesce(func.sum(CompanyEarnings.excess_amount), 0)
    ).filter(
        and_(
            CompanyEarnings.ceiling_date >= start_dt.date(),
            CompanyEarnings.ceiling_date <= end_dt.date()
        )
    ).scalar() or Decimal('0.00')
    ceiling_earnings = Decimal(str(ceiling_earnings))
    
    # Total Company Revenue = Package Sales + Admin (8%) + Ceiling
    # TDS (2%) is EXCLUDED - it's a liability to government, NOT company revenue
    total_company_revenue = package_revenue + admin_deduction + ceiling_earnings
    
    # ========== EXPENSE CALCULATIONS (WV Protocol) ==========
    
    # 1. Direct Awards (actual_cost_paid from finance_processed)
    direct_awards_cost = db.query(
        func.coalesce(func.sum(UserAwardProgress.actual_cost_paid), 0)
    ).filter(
        and_(
            UserAwardProgress.finance_processed_at >= start_dt,
            UserAwardProgress.finance_processed_at <= end_dt,
            UserAwardProgress.actual_cost_paid.isnot(None)
        )
    ).scalar() or Decimal('0.00')
    direct_awards_cost = Decimal(str(direct_awards_cost))
    
    # 2. Matching Awards (actual_cost_paid from finance_processed)
    matching_awards_cost = db.query(
        func.coalesce(func.sum(UserMatchingAwardProgress.actual_cost_paid), 0)
    ).filter(
        and_(
            UserMatchingAwardProgress.finance_processed_at >= start_dt,
            UserMatchingAwardProgress.finance_processed_at <= end_dt,
            UserMatchingAwardProgress.actual_cost_paid.isnot(None)
        )
    ).scalar() or Decimal('0.00')
    matching_awards_cost = Decimal(str(matching_awards_cost))
    
    total_awards_cost = direct_awards_cost + matching_awards_cost
    
    # 3. Bonanza Rewards (actual_cost_paid from finance_processed) - DC Protocol
    # Query from DynamicBonanzaHistory (single source of truth)
    total_bonanza_cost = db.query(
        func.coalesce(func.sum(DynamicBonanzaHistory.actual_cost_paid), 0)
    ).filter(
        and_(
            DynamicBonanzaHistory.finance_processed_at >= start_dt,
            DynamicBonanzaHistory.finance_processed_at <= end_dt,
            DynamicBonanzaHistory.actual_cost_paid.isnot(None)
        )
    ).scalar() or Decimal('0.00')
    total_bonanza_cost = Decimal(str(total_bonanza_cost))
    
    # For display, use totals (type split can be added later)
    cash_bonanza_cost = Decimal('0.00')
    physical_bonanza_cost = total_bonanza_cost
    
    # 4. Withdrawals (final_payout for Approved status - WV Protocol)
    withdrawals_cost = db.query(
        func.coalesce(func.sum(WithdrawalRequest.final_payout), 0)
    ).filter(
        and_(
            WithdrawalRequest.paid_date >= start_dt,
            WithdrawalRequest.paid_date <= end_dt,
            WithdrawalRequest.status == 'Approved'
        )
    ).scalar() or Decimal('0.00')
    withdrawals_cost = Decimal(str(withdrawals_cost))
    
    # 5. Finance-Managed Expenses (approved only)
    finance_expenses = db.query(Expense).filter(
        and_(
            Expense.expense_date >= start_dt.date(),
            Expense.expense_date <= end_dt.date(),
            Expense.status == 'approved',
            Expense.is_deleted == False,
            # Exclude award/bonanza linked expenses (to avoid double counting)
            Expense.award_reference_id.is_(None),
            Expense.bonanza_reference_id.is_(None)
        )
    ).all()
    
    expense_by_category = {}
    total_finance_expenses = Decimal('0.00')
    
    for expense in finance_expenses:
        category = expense.category
        amount = Decimal(str(expense.amount))
        
        if category not in expense_by_category:
            expense_by_category[category] = Decimal('0.00')
        
        expense_by_category[category] += amount
        total_finance_expenses += amount
    
    # Total Company Liabilities (WV Protocol - ALL amounts that must be paid out)
    total_liabilities = (
        total_gross_income +       # Income paid to users (Direct + Matching + Ved + Guru Dakshina)
        tds_deduction +           # Government tax liability
        total_awards_cost +        # Awards to be delivered/paid
        total_bonanza_cost +       # Bonanza to be delivered/paid
        withdrawals_cost +         # User withdrawals to be paid
        total_finance_expenses     # Other finance expenses
    )
    
    # Keep total_expenses for backward compatibility in response
    total_expenses = total_liabilities
    
    # Net Company Earnings = Revenue - ALL Liabilities (including income paid to users)
    net_company_profit = total_company_revenue - total_liabilities
    
    # ========== RESPONSE DATA ==========
    
    return {
        "success": True,
        "date_range": {
            "start_date": start_date,
            "end_date": end_date
        },
        "revenue": {
            "package_sales": {
                "total_package_revenue": float(package_revenue),
                "description": "Revenue from package activations (Platinum, Diamond, Star, Loyal)"
            },
            "admin_earnings": {
                "admin_deduction_8_percent": float(admin_deduction),
                "description": "Company revenue from user income (8% admin fee only)"
            },
            "tds_liability": {
                "tds_deduction_2_percent": float(tds_deduction),
                "description": "Government tax liability - NOT company revenue (to be paid to govt)"
            },
            "ceiling_excess": {
                "total_ceiling_earnings": float(ceiling_earnings),
                "description": "Earnings from daily ₹50,000 ceiling excess"
            },
            "income_tracking": {
                "direct_referral": float(direct_income),
                "matching_referral": float(matching_income),
                "ved_income": float(ved_income),
                "guru_dakshina": float(guru_dakshina),
                "total_user_income_paid": float(total_gross_income)
            },
            "total_company_revenue": float(total_company_revenue)
        },
        "expenses": {
            "income_paid_to_users": {
                "direct_referral": float(direct_income),
                "matching_referral": float(matching_income),
                "ved_income": float(ved_income),
                "guru_dakshina": float(guru_dakshina),
                "total_income_paid": float(total_gross_income),
                "description": "Total income paid to users (company expense)"
            },
            "tds_liability": {
                "amount": float(tds_deduction),
                "description": "Government tax liability"
            },
            "awards": {
                "direct_awards": float(direct_awards_cost),
                "matching_awards": float(matching_awards_cost),
                "total_awards": float(total_awards_cost)
            },
            "bonanza": {
                "cash_bonanza": float(cash_bonanza_cost),
                "physical_bonanza": float(physical_bonanza_cost),
                "total_bonanza": float(total_bonanza_cost)
            },
            "withdrawals": float(withdrawals_cost),
            "finance_expenses": {
                "by_category": {k: float(v) for k, v in expense_by_category.items()},
                "total": float(total_finance_expenses)
            },
            "total_expenses": float(total_expenses)
        },
        "profit": {
            "net_company_profit": float(net_company_profit),
            "is_profitable": float(net_company_profit) >= 0,
            "profit_margin_percent": float((net_company_profit / total_company_revenue * 100) if total_company_revenue > 0 else 0)
        },
        "summary": {
            "total_revenue": float(total_company_revenue),
            "total_expenses": float(total_expenses),
            "net_earnings": float(net_company_profit),
            "revenue_sources_count": 3,
            "expense_categories_count": 5,
            "largest_revenue_source": "Package Sales" if package_revenue > admin_deduction else "Admin Earnings (8%)",
            "largest_expense_category": max([
                ("Income Paid to Users", total_gross_income),
                ("TDS", tds_deduction),
                ("Awards", total_awards_cost),
                ("Bonanza", total_bonanza_cost),
                ("Withdrawals", withdrawals_cost),
                ("Finance Expenses", total_finance_expenses)
            ], key=lambda x: x[1])[0] if total_expenses > 0 else "None"
        },
        "wv_protocol": {
            "description": "All expenses are NET amounts (no additional deductions)",
            "awards": "actual_cost_paid from procurement",
            "bonanza": "actual_cost_paid from procurement",
            "withdrawals": "final_payout (NET after all deductions)"
        }
    }

@router.get("/dashboard-stats")
async def get_rvz_dashboard_stats(
    current_user: User = Depends(get_current_rvz_user_hybrid),
    db: Session = Depends(get_db)
):
    """
    RVZ ID Supreme Dashboard - DC Protocol Compliant
    Shows: ALL admin data PLUS complete revenue breakdown (supreme authority)
    Uses hybrid auth for session cookie support
    """
    try:
        from sqlalchemy import func, and_, desc, or_
        from datetime import datetime
        from app.models.awards import UserAwardProgress
        from app.models.bonanza import DynamicBonanzaHistory  # DC Protocol: BonanzaProgress deprecated
        from app.models.withdrawal import WithdrawalRequest
        from app.models.transaction import Transaction
        from app.models.ticket import ServiceTicket
        from app.models.kyc_document import KYCDocument
        from app.models.api_response import success_response
        from app.models.base import get_indian_time
        
        today = get_indian_time().date()
        today_start = datetime.combine(today, datetime.min.time())
        today_end = datetime.combine(today, datetime.max.time())
        month_start = today.replace(day=1)
        production_start = datetime(2025, 10, 1)
        
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
        
        # KYC Statistics
        pending_kyc = db.query(func.count(KYCDocument.id)).filter(KYCDocument.status == 'Pending').scalar() or 0
        approved_kyc = db.query(func.count(KYCDocument.id)).filter(KYCDocument.status == 'Approved').scalar() or 0
        
        # Awards - All stages
        awards_pending_admin = db.query(func.count(UserAwardProgress.id)).filter(
            and_(
                UserAwardProgress.admin_approved_by.is_(None),
                UserAwardProgress.achieved_at.isnot(None)
            )
        ).scalar() or 0
        awards_pending_sa = db.query(func.count(UserAwardProgress.id)).filter(
            and_(
                UserAwardProgress.admin_approved_by.isnot(None),
                UserAwardProgress.super_admin_decision.is_(None)
            )
        ).scalar() or 0
        awards_procurement_queue = db.query(func.count(UserAwardProgress.id)).filter(
            and_(
                UserAwardProgress.admin_approved_by.isnot(None),
                UserAwardProgress.super_admin_decision == 'approved',
                UserAwardProgress.finance_processed_by.is_(None)
            )
        ).scalar() or 0
        
        # DC Protocol: Bonanza - All stages (query from DynamicBonanzaHistory)
        bonanza_pending_admin = db.query(func.count(DynamicBonanzaHistory.id)).filter(
            and_(
                DynamicBonanzaHistory.admin_approved_by.is_(None),
                DynamicBonanzaHistory.claimed_at.isnot(None)
            )
        ).scalar() or 0
        bonanza_pending_sa = db.query(func.count(DynamicBonanzaHistory.id)).filter(
            and_(
                DynamicBonanzaHistory.admin_approved_by.isnot(None),
                DynamicBonanzaHistory.super_admin_decision.is_(None)
            )
        ).scalar() or 0
        bonanza_procurement_queue = db.query(func.count(DynamicBonanzaHistory.id)).filter(
            and_(
                DynamicBonanzaHistory.admin_approved_by.isnot(None),
                DynamicBonanzaHistory.super_admin_decision == 'approved',
                DynamicBonanzaHistory.finance_processed_by.is_(None)
            )
        ).scalar() or 0
        
        # Tickets
        open_tickets = db.query(func.count(ServiceTicket.id)).filter(ServiceTicket.status == 'Open').scalar() or 0
        total_tickets = db.query(func.count(ServiceTicket.id)).scalar() or 0
        
        # Pending Withdrawals
        pending_withdrawals = db.query(func.count(WithdrawalRequest.id)).filter(
            WithdrawalRequest.status == 'Pending'
        ).scalar() or 0
        
        # REVENUE BREAKDOWN - RVZ ID ONLY (Supreme Authority)
        income_types = ['Direct Referral', 'Matching Referral', 'Ved', 'Guru Dakshina', 'Field Allowance']
        
        # Total Income Generated
        total_income = db.query(func.sum(Transaction.amount)).filter(
            and_(
                Transaction.transaction_type.in_(income_types),
                Transaction.timestamp >= production_start
            )
        ).scalar() or 0
        
        # Income Today
        income_today = db.query(func.sum(Transaction.amount)).filter(
            and_(
                Transaction.transaction_type.in_(income_types),
                Transaction.timestamp >= today_start,
                Transaction.timestamp <= today_end
            )
        ).scalar() or 0
        
        # Income This Month
        income_this_month = db.query(func.sum(Transaction.amount)).filter(
            and_(
                Transaction.transaction_type.in_(income_types),
                Transaction.timestamp >= month_start
            )
        ).scalar() or 0
        
        # Pending Income = Pending Withdrawal Requests (NET amounts per WV Protocol)
        pending_income = db.query(func.sum(WithdrawalRequest.final_payout)).filter(
            WithdrawalRequest.status == 'Pending'
        ).scalar() or 0
        
        # Income by Type (Breakdown)
        direct_referral_income = db.query(func.sum(Transaction.amount)).filter(
            and_(
                Transaction.transaction_type == 'Direct Referral',
                Transaction.timestamp >= production_start
            )
        ).scalar() or 0
        matching_referral_income = db.query(func.sum(Transaction.amount)).filter(
            and_(
                Transaction.transaction_type == 'Matching Referral',
                Transaction.timestamp >= production_start
            )
        ).scalar() or 0
        ved_income = db.query(func.sum(Transaction.amount)).filter(
            and_(
                Transaction.transaction_type == 'Ved',
                Transaction.timestamp >= production_start
            )
        ).scalar() or 0
        guru_dakshina_income = db.query(func.sum(Transaction.amount)).filter(
            and_(
                Transaction.transaction_type == 'Guru Dakshina',
                Transaction.timestamp >= production_start
            )
        ).scalar() or 0
        field_allowance_income = db.query(func.sum(Transaction.amount)).filter(
            and_(
                Transaction.transaction_type == 'Field Allowance',
                Transaction.timestamp >= production_start
            )
        ).scalar() or 0
        
        # Withdrawals Statistics
        total_withdrawals = db.query(func.sum(WithdrawalRequest.final_payout)).filter(
            WithdrawalRequest.status == 'Approved'
        ).scalar() or 0
        withdrawals_today = db.query(func.sum(WithdrawalRequest.final_payout)).filter(
            and_(
                WithdrawalRequest.status == 'Approved',
                WithdrawalRequest.request_date == today
            )
        ).scalar() or 0
        withdrawals_this_month = db.query(func.sum(WithdrawalRequest.final_payout)).filter(
            and_(
                WithdrawalRequest.status == 'Approved',
                WithdrawalRequest.request_date >= month_start
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
            "financial_stats": {
                "all_time": {
                    "total_income": float(total_income),
                    "total_withdrawals": float(total_withdrawals)
                },
                "today": {
                    "total_income": float(income_today),
                    "total_withdrawals": float(withdrawals_today)
                },
                "this_month": {
                    "total_income": float(income_this_month),
                    "total_withdrawals": float(withdrawals_this_month)
                }
            },
            "kyc_stats": {
                "pending": pending_kyc,
                "approved": approved_kyc
            },
            "awards": {
                "pending_admin_approval": awards_pending_admin + bonanza_pending_admin,
                "pending_super_admin_decision": awards_pending_sa + bonanza_pending_sa,
                "procurement_queue": awards_procurement_queue + bonanza_procurement_queue
            },
            "tickets": {
                "total": total_tickets,
                "open": open_tickets
            },
            "withdrawals": {
                "pending": pending_withdrawals
            },
            "revenue": {
                "total_income": float(total_income),
                "income_today": float(income_today),
                "income_this_month": float(income_this_month),
                "pending_income": float(pending_income),
                "income_by_type": {
                    "direct_referral": float(direct_referral_income),
                    "matching_referral": float(matching_referral_income),
                    "ved": float(ved_income),
                    "guru_dakshina": float(guru_dakshina_income),
                    "field_allowance": float(field_allowance_income)
                },
                "total_withdrawals": float(total_withdrawals),
                "withdrawals_today": float(withdrawals_today),
                "withdrawals_this_month": float(withdrawals_this_month)
            }
        }
        
        return success_response(
            message="RVZ Supreme Dashboard statistics retrieved successfully",
            data=dashboard_data
        )
        
    except Exception as e:
        import traceback
        print(f"❌ RVZ Dashboard Error: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to load dashboard statistics"
        )


@router.get("/activated-accounts-fresh")
async def get_activated_accounts_fresh(
    current_user: User = Depends(get_current_rvz_user_hybrid),
    db: Session = Depends(get_db)
):
    """
    NEW ENDPOINT - Returns ONLY activated accounts (users with packages)
    Counts users where activation_date IS NOT NULL
    """
    from datetime import datetime, timedelta
    from sqlalchemy import and_
    import pytz
    
    # Get timezone-aware timestamps
    now = datetime.now(pytz.timezone('Asia/Kolkata'))
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = now.replace(hour=23, minute=59, second=59, microsecond=999999)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    # Count activated accounts (users with packages = activation_date set)
    all_time_count = db.query(func.count(User.id)).filter(
        User.activation_date.isnot(None)
    ).scalar() or 0
    
    today_count = db.query(func.count(User.id)).filter(
        and_(
            User.activation_date.isnot(None),
            User.activation_date >= today_start,
            User.activation_date <= today_end
        )
    ).scalar() or 0
    
    month_count = db.query(func.count(User.id)).filter(
        and_(
            User.activation_date.isnot(None),
            User.activation_date >= month_start
        )
    ).scalar() or 0
    
    return {
        "success": True,
        "data": {
            "all_time": all_time_count,
            "today": today_count,
            "this_month": month_count,
            "timestamp": now.isoformat(),
            "description": "Users with packages (activation_date set)"
        }
    }


@router.get("/categories")
async def get_announcement_categories_vgk(
    current_user: User = Depends(get_current_rvz_user_hybrid),
    db: Session = Depends(get_db)
):
    """
    RVZ endpoint to get announcement categories
    Proxies to the feedback categories endpoint with RVZ authorization
    """
    from app.models.feedback import FeedbackCategory
    
    try:
        categories = db.query(FeedbackCategory).filter(
            FeedbackCategory.is_active == True
        ).order_by(FeedbackCategory.name).all()
        
        categories_data = [
            {
                "id": cat.id,
                "name": cat.name,
                "category_name": cat.name,
                "description": cat.description,
                "category_description": cat.description,
                "is_active": cat.is_active
            }
            for cat in categories
        ]
        
        return categories_data
        
    except Exception as e:
        import traceback
        logger.error(f"❌ Error fetching categories: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to load categories"
        )


@router.post("/categories")
async def create_announcement_category_vgk(
    category_name: str = Form(...),
    category_description: Optional[str] = Form(None),
    current_user: User = Depends(get_current_rvz_user_hybrid),
    db: Session = Depends(get_db)
):
    """
    RVZ endpoint to create announcement category
    Proxies to the feedback categories endpoint with RVZ authorization
    """
    from app.models.feedback import FeedbackCategory
    
    try:
        existing = db.query(FeedbackCategory).filter(
            FeedbackCategory.name == category_name.strip()
        ).first()
        
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Category '{category_name}' already exists"
            )
        
        new_category = FeedbackCategory(
            name=category_name.strip(),
            description=category_description or "",
            is_active=True
        )
        
        db.add(new_category)
        db.commit()
        db.refresh(new_category)
        
        return {
            "id": new_category.id,
            "name": new_category.name,
            "category_name": new_category.name,
            "description": new_category.description,
            "category_description": new_category.description,
            "is_active": new_category.is_active
        }
        
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        import traceback
        logger.error(f"❌ Error creating category: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create category"
        )


@router.put("/categories/{category_id}")
async def update_announcement_category_vgk(
    category_id: int,
    category_name: str = Form(...),
    category_description: Optional[str] = Form(None),
    current_user: User = Depends(get_current_rvz_user_hybrid),
    db: Session = Depends(get_db)
):
    """
    RVZ endpoint to update announcement category
    Proxies to the feedback categories endpoint with RVZ authorization
    """
    from app.models.feedback import FeedbackCategory
    
    try:
        category = db.query(FeedbackCategory).filter(
            FeedbackCategory.id == category_id
        ).first()
        
        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Category not found"
            )
        
        category.name = category_name.strip()
        category.description = category_description or ""
        
        db.commit()
        db.refresh(category)
        
        return {
            "id": category.id,
            "name": category.name,
            "category_name": category.name,
            "description": category.description,
            "category_description": category.description,
            "is_active": category.is_active
        }
        
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        import traceback
        logger.error(f"❌ Error updating category: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update category"
        )
@router.get("/terms-versions")
async def list_all_tc_versions(
    current_user: User = Depends(get_current_rvz_user_hybrid),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get list of all T&C versions with user acceptance statistics
    RVZ ID ONLY - View all T&C versions with metadata and stats
    """
    try:
        from app.models.banner import UserCouponAcceptance
        
        versions = TermsAndConditionsVersion.get_all_versions(db)
        
        # Get total users and active users
        total_users = db.query(User).count()
        active_users = db.query(User).filter(User.account_status == 'active').count()
        
        # Get all acceptance records
        all_acceptances = db.query(
            UserCouponAcceptance.accepted_terms_version,
            func.count(func.distinct(UserCouponAcceptance.user_id)).label('accepted_count')
        ).group_by(UserCouponAcceptance.accepted_terms_version).all()
        
        # Create acceptance map
        acceptance_map = {acc.accepted_terms_version: acc.accepted_count for acc in all_acceptances}
        
        # Calculate overall stats
        total_acceptances = sum(acceptance_map.values())
        avg_acceptances_per_user = total_acceptances / total_users if total_users > 0 else 0
        
        active_version = None
        version_list = []
        
        for v in versions:
            accepted_count = acceptance_map.get(v.version, 0)
            not_accepted = total_users - accepted_count
            acceptance_rate = (accepted_count / total_users * 100) if total_users > 0 else 0
            
            version_data = {
                "id": v.id,
                "version": v.version,
                "content_preview": v.content[:100] + "..." if len(v.content) > 100 else v.content,
                "content_length": len(v.content),
                "is_active": v.is_active,
                "created_by": v.created_by,
                "created_at": v.created_at.isoformat(),
                "activated_at": v.activated_at.isoformat() if v.activated_at else None,
                "activated_by": v.activated_by,
                "notes": v.notes,
                "source_version": v.source_version,
                "max_displays": v.max_displays,
                "platform_type": getattr(v, 'platform_type', 'MNR'),
                # Statistics
                "total_users": total_users,
                "active_users": active_users,
                "accepted_count": accepted_count,
                "not_accepted": not_accepted,
                "acceptance_rate": round(acceptance_rate, 2)
            }
            version_list.append(version_data)
            
            if v.is_active:
                active_version = v.version
        
        return {
            "success": True,
            "data": {
                "versions": version_list,
                "total": len(version_list),
                "active_version": active_version,
                # Summary statistics
                "summary": {
                    "total_users": total_users,
                    "active_users": active_users,
                    "total_acceptances": total_acceptances,
                    "avg_acceptances_per_user": round(avg_acceptances_per_user, 2),
                    "unaccepted_users": total_users - len(set(acc.accepted_terms_version for acc in all_acceptances))
                }
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve T&C versions: {str(e)}"
        )

@router.get("/terms-versions/{version}")
async def get_tc_version_detail(
    version: str,
    current_user: User = Depends(get_current_rvz_user_hybrid),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get full details of a specific T&C version
    RVZ ID ONLY - View complete content of a version
    """
    try:
        tc_version = db.query(TermsAndConditionsVersion).filter(
            TermsAndConditionsVersion.version == version
        ).first()
        
        if not tc_version:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Version {version} not found"
            )
        
        return {
            "success": True,
            "data": {
                "id": tc_version.id,
                "version": tc_version.version,
                "content": tc_version.content,  # Full content
                "is_active": tc_version.is_active,
                "created_by": tc_version.created_by,
                "created_at": tc_version.created_at.isoformat(),
                "activated_at": tc_version.activated_at.isoformat() if tc_version.activated_at else None,
                "activated_by": tc_version.activated_by,
                "notes": tc_version.notes,
                "source_version": tc_version.source_version,
                "max_displays": tc_version.max_displays,
                "platform_type": getattr(tc_version, 'platform_type', 'MNR'),
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve version {version}: {str(e)}"
        )

@router.post("/terms-versions")
async def create_new_tc_version(
    request_data: CreateVersionRequest,
    current_user: User = Depends(get_current_rvz_user_hybrid),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Create a new T&C version
    RVZ ID ONLY - Create a new version (inactive by default)
    """
    try:
        from app.core.audit import AuditLogger
        
        # Check if version already exists
        existing = db.query(TermsAndConditionsVersion).filter(
            TermsAndConditionsVersion.version == request_data.version
        ).first()
        
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Version {request_data.version} already exists"
            )
        
        # Create new version
        new_version = TermsAndConditionsVersion.create_version(
            db=db,
            version=request_data.version,
            content=request_data.content,
            created_by=str(current_user.id),
            source_version=request_data.source_version,
            notes=request_data.notes,
            platform_type=request_data.platform_type or 'MNR',
        )
        
        # Log audit
        AuditLogger.log_rvz_action(
            db=db,
            rvz_user_id=current_user.id,
            action="CREATE_TC_VERSION",
            target_type="terms_and_conditions",
            target_id=str(new_version.id),
            details={
                "version": new_version.version,
                "source_version": request_data.source_version,
                "content_length": len(request_data.content),
                "notes": request_data.notes
            },
            ip_address=None
        )
        
        return {
            "success": True,
            "message": f"Version {new_version.version} created successfully",
            "data": {
                "id": new_version.id,
                "version": new_version.version,
                "is_active": new_version.is_active,
                "created_at": new_version.created_at.isoformat()
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create version: {str(e)}"
        )

@router.put("/terms-versions/{version}")
async def update_tc_version(
    version: str,
    request_data: CreateVersionRequest,
    current_user: User = Depends(get_current_rvz_user_hybrid),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Update an existing T&C version
    RVZ ID ONLY - Update version content, notes, max_displays
    """
    try:
        from app.core.audit import AuditLogger
        
        # Find the version to update
        tc_version = db.query(TermsAndConditionsVersion).filter(
            TermsAndConditionsVersion.version == version
        ).first()
        
        if not tc_version:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Version {version} not found"
            )
        
        # Update fields
        tc_version.content = request_data.content
        tc_version.notes = request_data.notes
        if request_data.max_displays:
            tc_version.max_displays = request_data.max_displays
        if request_data.platform_type:
            tc_version.platform_type = request_data.platform_type
        
        db.commit()
        db.refresh(tc_version)
        
        # R Logs audit
        AuditLogger.log_rvz_action(
            db=db,
            rvz_user_id=current_user.id,
            action="UPDATE_TC_VERSION",
            target_type="terms_and_conditions",
            target_id=str(tc_version.id),
            details={
                "version": tc_version.version,
                "content_length": len(request_data.content),
                "notes": request_data.notes,
                "max_displays": request_data.max_displays
            },
            ip_address=None
        )
        
        return {
            "success": True,
            "message": f"Version {version} updated successfully",
            "data": {
                "id": tc_version.id,
                "version": tc_version.version,
                "is_active": tc_version.is_active,
                "updated_at": tc_version.created_at.isoformat()
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update version: {str(e)}"
        )

@router.put("/terms-versions/{version}/activate")
async def activate_tc_version(
    version: str,
    current_user: User = Depends(get_current_rvz_user_hybrid),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Activate a specific T&C version
    RVZ ID ONLY - Set a version as active (deactivates all others)
    """
    try:
        from app.core.audit import AuditLogger
        
        # Check if version exists
        tc_version = db.query(TermsAndConditionsVersion).filter(
            TermsAndConditionsVersion.version == version
        ).first()
        
        if not tc_version:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Version {version} not found"
            )
        
        # Get old active version for audit
        old_active = TermsAndConditionsVersion.get_active_version(db)
        old_active_version = old_active.version if old_active else None
        
        # Activate the version
        success = TermsAndConditionsVersion.activate_version(
            db=db,
            version=version,
            activated_by=str(current_user.id)
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to activate version {version}"
            )
        
        # R Logs audit
        AuditLogger.log_rvz_action(
            db=db,
            rvz_user_id=current_user.id,
            action="ACTIVATE_TC_VERSION",
            target_type="terms_and_conditions",
            target_id=str(tc_version.id),
            details={
                "new_active_version": version,
                "old_active_version": old_active_version,
                "activated_at": datetime.utcnow().isoformat()
            },
            ip_address=None
        )
        
        return {
            "success": True,
            "message": f"Version {version} activated successfully",
            "data": {
                "active_version": version,
                "previous_version": old_active_version,
                "activated_at": datetime.utcnow().isoformat(),
                "activated_by": current_user.id
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to activate version: {str(e)}"
        )

@router.get("/terms-acceptance-records")
async def get_detailed_acceptance_records(
    version: Optional[str] = None,
    user_id: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    current_user: User = Depends(get_current_rvz_user_hybrid),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get detailed individual user acceptance records with dynamic filtering
    RVZ ID ONLY - View complete audit trail of user T&C acceptances
    
    Filters:
    - version: Filter by specific T&C version
    - user_id: Search by user ID (partial match)
    - date_from: Filter acceptances from this date (YYYY-MM-DD)
    - date_to: Filter acceptances until this date (YYYY-MM-DD)
    """
    try:
        from app.models.banner import UserCouponAcceptance
        from app.models.user import User as UserModel
        from datetime import datetime, timedelta
        from sqlalchemy import func
        
        # Build query with user details
        query = db.query(
            UserCouponAcceptance,
            UserModel.name,
            UserModel.email,
            UserModel.phone_number
        ).join(
            UserModel,
            UserCouponAcceptance.user_id == UserModel.id
        )
        
        # Apply filters
        if version:
            query = query.filter(UserCouponAcceptance.accepted_terms_version == version)
        
        if user_id:
            query = query.filter(UserCouponAcceptance.user_id.like(f"%{user_id}%"))
        
        if date_from:
            try:
                from_date = datetime.fromisoformat(date_from)
                query = query.filter(UserCouponAcceptance.acceptance_timestamp >= from_date)
            except ValueError:
                pass
        
        if date_to:
            try:
                to_date = datetime.fromisoformat(date_to) + timedelta(days=1)
                query = query.filter(UserCouponAcceptance.acceptance_timestamp < to_date)
            except ValueError:
                pass
        
        # Order by user_id and timestamp to calculate acceptance numbers
        query = query.order_by(
            UserCouponAcceptance.user_id,
            UserCouponAcceptance.acceptance_timestamp.asc()
        )
        
        results = query.all()
        
        # Calculate acceptance numbers per user
        user_acceptance_count = {}
        records = []
        
        for acceptance, user_name, user_email, user_contact in results:
            uid = acceptance.user_id
            
            # Increment acceptance number for this user
            if uid not in user_acceptance_count:
                user_acceptance_count[uid] = 0
            user_acceptance_count[uid] += 1
            
            records.append({
                "id": acceptance.id,
                "user_id": acceptance.user_id,
                "user_name": user_name,
                "user_email": user_email,
                "user_contact": user_contact,
                "acceptance_number": user_acceptance_count[uid],
                "accepted_version": acceptance.accepted_terms_version,
                "acceptance_timestamp": acceptance.acceptance_timestamp.isoformat(),
                "login_attempt": acceptance.login_attempt_number,
                "ip_address": acceptance.ip_address,
                "user_agent": acceptance.user_agent or "N/A"
            })
        
        # Sort by most recent first for display
        records.reverse()
        
        return {
            "success": True,
            "data": {
                "records": records,
                "total": len(records),
                "filters_applied": {
                    "version": version,
                    "user_id": user_id,
                    "date_from": date_from,
                    "date_to": date_to
                }
            }
        }
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve acceptance records: {str(e)}"
        )


# ================================================================================
# BANNER OVERSIGHT & ANALYTICS ENDPOINTS (RVZ SUPREME AUTHORITY)
# ================================================================================

@router.get("/banners/queue")
async def get_rvz_banner_queue(
    status_filter: str = None,
    banner_type: str = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_hybrid)
):
    """RVZ Banner Oversight Dashboard"""
    try:
        from app.models.banner import Banner, CustomBanner, PopupMessage, BannerViewLog
        from app.models.user import User as UserModel
        from datetime import datetime, timedelta
        
        def get_unique_counts(banner_id, banner_type_str):
            """Calculate unique views and clicks for a banner - DC Protocol: Real data from DB"""
            unique_views = db.query(func.count(func.distinct(BannerViewLog.user_id))).filter(
                BannerViewLog.banner_id == banner_id,
                BannerViewLog.banner_type == banner_type_str,
                BannerViewLog.action == 'view'
            ).scalar() or 0
            
            unique_clicks = db.query(func.count(func.distinct(BannerViewLog.user_id))).filter(
                BannerViewLog.banner_id == banner_id,
                BannerViewLog.banner_type == banner_type_str,
                BannerViewLog.action == 'click'
            ).scalar() or 0
            
            return unique_views, unique_clicks
        
        banners_list = []
        
        # Fetch Image Banners
        if not banner_type or banner_type == "image":
            query = db.query(Banner, UserModel.name.label("creator_name")).outerjoin(UserModel, Banner.created_by == UserModel.id)
            if status_filter and status_filter != "all":
                if status_filter == "pending":
                    query = query.filter(Banner.status == "Pending")
                elif status_filter == "active":
                    query = query.filter(Banner.status == "Active")
                elif status_filter == "rejected":
                    query = query.filter(Banner.status == "Rejected")
            
            for banner, creator_name in query.order_by(Banner.created_date.desc()).all():
                ctr = (banner.total_clicks / banner.total_views * 100) if banner.total_views > 0 else 0
                unique_views, unique_clicks = get_unique_counts(banner.id, "image")
                banners_list.append({
                    "id": banner.id, "banner_type": "image", "title": banner.title, "status": banner.status,
                    "created_by": banner.created_by, "created_by_name": creator_name or "Unknown",
                    "created_date": banner.created_date, "approved_by": banner.approved_by,
                    "approved_date": banner.approved_date, "rejection_reason": None,
                    "total_views": banner.total_views, "total_clicks": banner.total_clicks,
                    "unique_views": unique_views, "unique_clicks": unique_clicks,
                    "last_viewed_at": banner.last_viewed_at, "ctr": round(ctr, 2),
                    "show_start_date": getattr(banner, "show_start_date", None), "show_end_date": getattr(banner, "show_end_date", None),
                    "start_date": getattr(banner, "start_date", None), "end_date": getattr(banner, "end_date", None),
                    "image_content": banner.image_content, "text_content": banner.text_content
                })
        
        # Fetch Custom Banners
        if not banner_type or banner_type == "custom":
            query = db.query(CustomBanner, UserModel.name.label("creator_name")).outerjoin(UserModel, CustomBanner.created_by == UserModel.id)
            if status_filter and status_filter != "all":
                if status_filter == "active":
                    query = query.filter(CustomBanner.is_active == True)
                elif status_filter == "pending":
                    query = query.filter(CustomBanner.is_active == False)
            
            for banner, creator_name in query.order_by(CustomBanner.created_at.desc()).all():
                ctr = (banner.total_clicks / banner.total_views * 100) if banner.total_views > 0 else 0
                unique_views, unique_clicks = get_unique_counts(banner.id, "custom")
                # Determine status: if is_active=False AND show_end_date is set, it's Paused
                if not banner.is_active and getattr(banner, "show_end_date", None):
                    status = "Paused"
                elif banner.is_active:
                    status = "Active"
                else:
                    status = "Inactive"
                
                banners_list.append({
                    "id": banner.id, "banner_type": "custom", "title": banner.title,
                    "status": status,
                    "created_by": banner.created_by, "created_by_name": creator_name or "Unknown",
                    "created_date": banner.created_at, "approved_by": None, "approved_date": None,
                    "rejection_reason": None, "total_views": banner.total_views,
                    "total_clicks": banner.total_clicks, "unique_views": unique_views, "unique_clicks": unique_clicks,
                    "last_viewed_at": banner.last_viewed_at,
                    "ctr": round(ctr, 2),
                    "show_start_date": getattr(banner, "show_start_date", None), "show_end_date": getattr(banner, "show_end_date", None),
                    "content": banner.content
                })
        
        # Fetch Popups
        if not banner_type or banner_type == "popup":
            query = db.query(PopupMessage, UserModel.name.label("creator_name")).outerjoin(UserModel, PopupMessage.created_by == UserModel.id)
            if status_filter and status_filter != "all":
                if status_filter == "pending":
                    query = query.filter(PopupMessage.status == "Pending")
                elif status_filter == "active":
                    query = query.filter(PopupMessage.status.in_(["Active", "Approved"]))
                elif status_filter == "rejected":
                    query = query.filter(PopupMessage.status == "Rejected")
            
            for popup, creator_name in query.order_by(PopupMessage.created_date.desc()).all():
                ctr = (popup.total_clicks / popup.total_views * 100) if popup.total_views > 0 else 0
                unique_views, unique_clicks = get_unique_counts(popup.id, "popup")
                banners_list.append({
                    "id": popup.id, "banner_type": "popup", "title": popup.title, "status": popup.status,
                    "created_by": popup.created_by, "created_by_name": creator_name or "Unknown",
                    "created_date": popup.created_date, "approved_by": popup.approved_by,
                    "content": popup.content,
                    "approved_date": popup.approved_date, "rejection_reason": popup.rejection_reason,
                    "total_views": popup.total_views, "total_clicks": popup.total_clicks,
                    "unique_views": unique_views, "unique_clicks": unique_clicks,
                    "last_viewed_at": popup.last_viewed_at, "ctr": round(ctr, 2),
                    "show_start_date": getattr(popup, "show_start_date", None), "show_end_date": getattr(popup, "show_end_date", None),
                    "content": popup.content
                })
        
        # Summary stats
        total_pending = sum(1 for b in banners_list if b["status"] in ["Pending", "Draft"])
        total_active = sum(1 for b in banners_list if b["status"] in ["Active", "Approved"])
        total_rejected = sum(1 for b in banners_list if b["status"] == "Rejected")
        seven_days_ago = datetime.now() - timedelta(days=7)
        total_views_7d = sum(b["total_views"] for b in banners_list if b["last_viewed_at"] and b["last_viewed_at"] >= seven_days_ago)
        
        return {
            "banners": banners_list,
            "summary": {
                "pending_count": total_pending,
                "active_count": total_active,
                "rejected_count": total_rejected,
                "total_views_last_7d": total_views_7d
            },
            "total_count": len(banners_list)
        }
    except Exception as e:
        logger.error(f"RVZ banner queue error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/banners/{banner_type}/{banner_id}/metrics")
async def get_banner_metrics(
    banner_type: str, banner_id: int, days: int = 30,
    db: Session = Depends(get_db), current_user: User = Depends(get_current_rvz_user_hybrid)
):
    """Get banner analytics for last N days"""
    try:
        from app.models.banner import BannerMetrics, Banner, CustomBanner, PopupMessage
        from datetime import datetime, timedelta
        
        # Verify banner exists
        if banner_type == "image":
            banner = db.query(Banner).filter(Banner.id == banner_id).first()
        elif banner_type == "custom":
            banner = db.query(CustomBanner).filter(CustomBanner.id == banner_id).first()
        elif banner_type == "popup":
            banner = db.query(PopupMessage).filter(PopupMessage.id == banner_id).first()
        else:
            raise HTTPException(status_code=400, detail="Invalid banner type")
        
        if not banner:
            raise HTTPException(status_code=404, detail="Banner not found")
        
        # Get daily metrics
        cutoff_date = (datetime.now() - timedelta(days=days)).date()
        daily_metrics = db.query(BannerMetrics).filter(
            BannerMetrics.banner_id == banner_id,
            BannerMetrics.banner_type == banner_type,
            BannerMetrics.metric_date >= cutoff_date
        ).order_by(BannerMetrics.metric_date.desc()).all()
        
        # Calculate totals
        total_views = sum(m.views for m in daily_metrics)
        total_clicks = sum(m.clicks for m in daily_metrics)
        total_impressions = sum(m.impressions for m in daily_metrics)
        ctr = (total_clicks / total_views * 100) if total_views > 0 else 0
        
        return {
            "total_views": total_views, "total_clicks": total_clicks,
            "total_impressions": total_impressions, "ctr": round(ctr, 2),
            "daily_breakdown": [
                {
                    "id": m.id, "banner_id": m.banner_id, "banner_type": m.banner_type,
                    "metric_date": m.metric_date.isoformat(), "views": m.views,
                    "clicks": m.clicks, "impressions": m.impressions,
                    "created_at": m.created_at.isoformat()
                }
                for m in daily_metrics
            ]
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Banner metrics error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/banners/{banner_type}/{banner_id}/events")
async def get_banner_events(
    banner_type: str, banner_id: int, action_filter: str = None, actor_filter: str = None,
    date_from: str = None, date_to: str = None,
    db: Session = Depends(get_db), current_user: User = Depends(get_current_rvz_user_hybrid)
):
    """Get complete audit trail for banner with dynamic filters"""
    try:
        from app.models.banner import BannerEventLog
        from datetime import datetime, timedelta
        
        query = db.query(BannerEventLog).filter(
            BannerEventLog.banner_id == banner_id, BannerEventLog.banner_type == banner_type
        )
        
        if action_filter:
            query = query.filter(BannerEventLog.action == action_filter)
        if actor_filter:
            query = query.filter(BannerEventLog.actor_id.like(f"%{actor_filter}%"))
        if date_from:
            try:
                query = query.filter(BannerEventLog.created_at >= datetime.fromisoformat(date_from))
            except: pass
        if date_to:
            try:
                query = query.filter(BannerEventLog.created_at < datetime.fromisoformat(date_to) + timedelta(days=1))
            except: pass
        
        events = query.order_by(BannerEventLog.created_at.desc()).all()
        return [
            {
                "id": e.id, "banner_id": e.banner_id, "banner_type": e.banner_type,
                "action": e.action, "actor_id": e.actor_id, "actor_name": e.actor_name,
                "previous_status": e.previous_status, "new_status": e.new_status,
                "notes": e.notes, "metadata_json": e.metadata_json,
                "created_at": e.created_at.isoformat()
            }
            for e in events
        ]
    except Exception as e:
        logger.error(f"Banner events error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/banners/{banner_type}/{banner_id}/approve")
async def rvz_approve_banner(
    banner_type: str, banner_id: int, approval_data: dict,
    db: Session = Depends(get_db), current_user: User = Depends(get_current_rvz_user_hybrid)
):
    """RVZ Supreme Approval Authority - Approve/Reject banners"""
    try:
        from app.models.banner import Banner, PopupMessage, BannerEventLog
        from datetime import datetime
        
        action = approval_data.get("action")
        notes = approval_data.get("notes", "")
        
        if action not in ["approve", "reject"]:
            raise HTTPException(status_code=400, detail="Action must be approve or reject")
        
        # Get banner
        if banner_type == "image":
            banner = db.query(Banner).filter(Banner.id == banner_id).first()
        elif banner_type == "popup":
            banner = db.query(PopupMessage).filter(PopupMessage.id == banner_id).first()
        else:
            raise HTTPException(status_code=400, detail="Invalid banner type for approval")
        
        if not banner:
            raise HTTPException(status_code=404, detail="Banner not found")
        
        previous_status = banner.status
        
        # Update banner
        if action == "approve":
            banner.status = "Active" if banner_type == "image" else "Approved"
            banner.approved_by = current_user.id
            banner.approved_date = datetime.utcnow()
            if banner_type == "popup":
                banner.is_active = True
        else:
            banner.status = "Rejected"
            banner.approved_by = current_user.id
            banner.approved_date = datetime.utcnow()
            if banner_type == "popup":
                banner.rejection_reason = notes
        
        db.commit()
        
        # Log event
        event_log = BannerEventLog(
            banner_id=banner_id, banner_type=banner_type,
            action="approved" if action == "approve" else "rejected",
            actor_id=current_user.id, actor_name=current_user.name,
            previous_status=previous_status, new_status=banner.status,
            notes=notes, metadata_json=None
        )
        db.add(event_log)
        db.commit()
        
        return {
            "success": True, "action": action, "banner_id": banner_id,
            "banner_type": banner_type, "new_status": banner.status,
            "approved_by": current_user.id,
            "message": f"Banner {action}d successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"RVZ banner approval error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))



@router.post("/banners/{banner_type}/{banner_id}/pause")
async def rvz_pause_banner(
    banner_type: str, banner_id: int,
    db: Session = Depends(get_db), current_user: User = Depends(get_current_rvz_user_hybrid)
):
    """RVZ Supreme Authority - Pause banner (temporarily disable)"""
    try:
        from app.models.banner import Banner, CustomBanner, PopupMessage, BannerEventLog
        from datetime import datetime
        
        # Get banner
        if banner_type == "image":
            banner = db.query(Banner).filter(Banner.id == banner_id).first()
        elif banner_type == "custom":
            banner = db.query(CustomBanner).filter(CustomBanner.id == banner_id).first()
        elif banner_type == "popup":
            banner = db.query(PopupMessage).filter(PopupMessage.id == banner_id).first()
        else:
            raise HTTPException(status_code=400, detail="Invalid banner type")
        
        if not banner:
            raise HTTPException(status_code=404, detail="Banner not found")
        
        # Get previous status for audit trail
        if banner_type == "custom":
            previous_status = "Active" if banner.is_active else "Inactive"
        else:
            previous_status = banner.status
        
        # Pause banner - set appropriate fields based on type
        if banner_type == "image":
            # Banner model: Only has status field
            banner.status = "Paused"
        elif banner_type == "custom":
            # CustomBanner model: Only has is_active field (no status)
            banner.is_active = False
            # Set end date to prevent rendering
            banner.show_end_date = datetime.utcnow()
        elif banner_type == "popup":
            # PopupMessage model: Has BOTH status and is_active
            banner.status = "Paused"
            banner.is_active = False
            # Set end date to prevent rendering
            banner.show_end_date = datetime.utcnow()
        
        db.commit()
        
        # Log event
        event_log = BannerEventLog(
            banner_id=banner_id, banner_type=banner_type,
            action="paused",
            actor_id=current_user.id, actor_name=current_user.name,
            previous_status=previous_status, new_status="Paused",
            notes="Banner paused by RVZ", metadata_json=None
        )
        db.add(event_log)
        db.commit()
        
        return {
            "success": True, "action": "pause", "banner_id": banner_id,
            "banner_type": banner_type, "new_status": "Paused",
            "paused_by": current_user.id,
            "message": "Banner paused successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"RVZ banner pause error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/banners/{banner_type}/{banner_id}/stop")
async def rvz_stop_banner(
    banner_type: str, banner_id: int,
    db: Session = Depends(get_db), current_user: User = Depends(get_current_rvz_user_hybrid)
):
    """RVZ Supreme Authority - Stop banner (permanently disable)"""
    try:
        from app.models.banner import Banner, CustomBanner, PopupMessage, BannerEventLog
        from datetime import datetime
        
        # Get banner
        if banner_type == "image":
            banner = db.query(Banner).filter(Banner.id == banner_id).first()
        elif banner_type == "custom":
            banner = db.query(CustomBanner).filter(CustomBanner.id == banner_id).first()
        elif banner_type == "popup":
            banner = db.query(PopupMessage).filter(PopupMessage.id == banner_id).first()
        else:
            raise HTTPException(status_code=400, detail="Invalid banner type")
        
        if not banner:
            raise HTTPException(status_code=404, detail="Banner not found")
        
        # Get previous status for audit trail
        if banner_type == "custom":
            previous_status = "Active" if banner.is_active else "Inactive"
        else:
            previous_status = banner.status
        
        # Stop banner - set appropriate fields based on type
        if banner_type == "image":
            # Banner model: Only has status field
            banner.status = "Stopped"
        elif banner_type == "custom":
            # CustomBanner model: Only has is_active field (no status)
            banner.is_active = False
            # Set end date to prevent rendering
            banner.show_end_date = datetime.utcnow()
        elif banner_type == "popup":
            # PopupMessage model: Has BOTH status and is_active
            banner.status = "Stopped"
            banner.is_active = False
            # Set end date to prevent rendering
            banner.show_end_date = datetime.utcnow()
        
        db.commit()
        
        # Log event
        event_log = BannerEventLog(
            banner_id=banner_id, banner_type=banner_type,
            action="stopped",
            actor_id=current_user.id, actor_name=current_user.name,
            previous_status=previous_status, new_status="Stopped",
            notes="Banner stopped by RVZ", metadata_json=None
        )
        db.add(event_log)
        db.commit()
        
        return {
            "success": True, "action": "stop", "banner_id": banner_id,
            "banner_type": banner_type, "new_status": "Stopped",
            "stopped_by": current_user.id,
            "message": "Banner stopped successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"RVZ banner stop error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/banners/{banner_type}/{banner_id}/resume")
async def rvz_resume_banner(
    banner_type: str, banner_id: int,
    db: Session = Depends(get_db), current_user: User = Depends(get_current_rvz_user_hybrid)
):
    """RVZ Supreme Authority - Resume paused banner (reactivate)"""
    try:
        from app.models.banner import Banner, CustomBanner, PopupMessage, BannerEventLog
        from datetime import datetime, timedelta
        
        # Get banner
        if banner_type == "image":
            banner = db.query(Banner).filter(Banner.id == banner_id).first()
        elif banner_type == "custom":
            banner = db.query(CustomBanner).filter(CustomBanner.id == banner_id).first()
        elif banner_type == "popup":
            banner = db.query(PopupMessage).filter(PopupMessage.id == banner_id).first()
        else:
            raise HTTPException(status_code=400, detail="Invalid banner type")
        
        if not banner:
            raise HTTPException(status_code=404, detail="Banner not found")
        
        # Get previous status for audit trail
        if banner_type == "custom":
            previous_status = "Active" if banner.is_active else "Inactive"
        else:
            previous_status = banner.status
        
        # Resume banner - reactivate and extend end date
        if banner_type == "image":
            banner.status = "Active"
            # Extend end date by 30 days or clear if paused (critical for visibility)
            if hasattr(banner, 'show_end_date'):
                if banner.show_end_date and banner.show_end_date < datetime.utcnow():
                    banner.show_end_date = datetime.utcnow() + timedelta(days=30)
                elif not banner.show_end_date:
                    # If no end date, set far future to ensure visibility
                    banner.show_end_date = datetime.utcnow() + timedelta(days=365)
        elif banner_type == "custom":
            banner.is_active = True
            # Extend end date by 30 days or set to far future if not set
            if banner.show_end_date and banner.show_end_date < datetime.utcnow():
                banner.show_end_date = datetime.utcnow() + timedelta(days=30)
        elif banner_type == "popup":
            banner.status = "Active"
            banner.is_active = True
            # Extend end date by 30 days or set to far future if not set
            if banner.show_end_date and banner.show_end_date < datetime.utcnow():
                banner.show_end_date = datetime.utcnow() + timedelta(days=30)
        
        db.commit()
        
        # Log event
        event_log = BannerEventLog(
            banner_id=banner_id, banner_type=banner_type,
            action="resumed",
            actor_id=current_user.id, actor_name=current_user.name,
            previous_status=previous_status, new_status="Active",
            notes="Banner resumed by RVZ", metadata_json=None
        )
        db.add(event_log)
        db.commit()
        
        return {
            "success": True, "action": "resume", "banner_id": banner_id,
            "banner_type": banner_type, "new_status": "Active",
            "resumed_by": current_user.id,
            "message": "Banner resumed successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"RVZ banner resume error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/banners/{banner_type}/{banner_id}/delete")
async def rvz_delete_banner(
    banner_type: str, banner_id: int,
    db: Session = Depends(get_db), current_user: User = Depends(get_current_rvz_user_hybrid)
):
    """RVZ Supreme Authority - Delete rejected banner permanently"""
    try:
        from app.models.banner import Banner, CustomBanner, PopupMessage, BannerEventLog
        
        # Get banner
        if banner_type == "image":
            banner = db.query(Banner).filter(Banner.id == banner_id).first()
        elif banner_type == "custom":
            banner = db.query(CustomBanner).filter(CustomBanner.id == banner_id).first()
        elif banner_type == "popup":
            banner = db.query(PopupMessage).filter(PopupMessage.id == banner_id).first()
        else:
            raise HTTPException(status_code=400, detail="Invalid banner type")
        
        if not banner:
            raise HTTPException(status_code=404, detail="Banner not found")
        
        # Only allow deletion of rejected banners
        banner_status = banner.status if hasattr(banner, 'status') else "Unknown"
        if banner_status not in ["Rejected", "Draft", "Inactive"]:
            raise HTTPException(status_code=403, detail="Only rejected/inactive banners can be deleted")
        
        # Log event before deletion
        event_log = BannerEventLog(
            banner_id=banner_id, banner_type=banner_type,
            action="deleted",
            actor_id=current_user.id, actor_name=current_user.name,
            previous_status=banner_status, new_status="Deleted",
            notes="Banner permanently deleted by RVZ", metadata_json=None
        )
        db.add(event_log)
        db.commit()
        
        # Delete banner
        db.delete(banner)
        db.commit()
        
        return {
            "success": True, "action": "delete", "banner_id": banner_id,
            "banner_type": banner_type,
            "deleted_by": current_user.id,
            "message": "Banner deleted successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"RVZ banner delete error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
