"""
Role-Based Access Control (RBAC) System
DC Protocol: MNR admin types removed permanently.
Only MNR Members and Staff users. All admin operations are staff-only.
"""

from typing import List, Optional
from fastapi import Depends, HTTPException, status
from app.core.security import get_current_user, get_current_user_hybrid
from app.models.user import User

# Permission Matrix - MNR member types only, admin operations are staff-only
PERMISSION_MATRIX = {
    'Member': {
        'level': 2,
        'capabilities': [
            'view_profile', 'edit_profile', 'view_earnings', 'view_wallet',
            'view_team', 'manage_pins', 'manage_coupons', 'create_tickets',
            'view_awards', 'view_field_allowances', 'kyc_submission',
            'referral', 'team_view', 'basic_earnings'
        ]
    },
    'User': {
        'level': 1,
        'capabilities': [
            'view_profile', 'edit_profile', 'view_earnings', 'view_wallet',
            'view_team', 'manage_pins', 'manage_coupons', 'create_tickets',
            'view_awards', 'view_field_allowances', 'kyc_submission'
        ]
    }
}

# Role hierarchy - MNR member types only, admin operations handled by Staff
ROLE_LEVELS = {
    'User': 1,
    'Member': 2
}

# Staff Role Mappings - kept for internal staff hierarchy management
STAFF_ROLE_MAPPINGS = {
    'vgk4u': 'vgk4u_supreme',
    'key_leadership': 'key_leadership',
    'leadership_role': 'leadership',
    'hr': 'hr',
    'ea': 'ea',
    'accounts': 'accounts',
    'service_head': 'service_head',
    'manager': 'manager',
    'team_leader': 'team_leader',
    'senior_executive': 'senior_executive',
    'supervisor': 'supervisor',
    'junior_executive': 'junior_executive',
    'employee': 'employee',
    'freelancer_manager': 'freelancer_manager',
}

def normalize_role(role: str) -> str:
    """Normalize role to standard format (case-insensitive) - MNR member types only"""
    if not role:
        return 'User'
    
    role_lower = role.lower()
    
    for standard_role, config in PERMISSION_MATRIX.items():
        if role_lower == standard_role.lower():
            return standard_role
        aliases = config.get('aliases', [])
        if any(role_lower == alias.lower() for alias in aliases):
            return standard_role
    
    return role

def get_role_level(role: str) -> int:
    """Get numeric level for a role (case-insensitive)"""
    normalized = normalize_role(role)
    return ROLE_LEVELS.get(normalized, 0)

def has_capability(user_role: str, capability: str) -> bool:
    """Check if a role has a specific capability - MNR member types only"""
    normalized_role = normalize_role(user_role)
    role_config = PERMISSION_MATRIX.get(normalized_role, {})
    capabilities = role_config.get('capabilities', [])
    return capability in capabilities

def _require_staff_only():
    """DC Protocol: Staff-only dependency - rejects all MNR users"""
    async def staff_checker(current_user = Depends(get_current_user_hybrid)):
        from app.models.staff import StaffEmployee
        if not isinstance(current_user, StaffEmployee):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Staff access required"
            )
        return current_user
    return staff_checker

VALID_MNR_ROLES = {'User', 'Member'}

def require_roles(allowed_roles: List[str]):
    """
    Dependency to require specific MNR member roles.
    For admin operations, use staff-only dependencies instead.
    DC Protocol: If allowed_roles contains any non-MNR role (removed admin types),
    MNR users are rejected outright - only staff can pass.
    """
    async def role_checker(current_user = Depends(get_current_user_hybrid)):
        from app.models.staff import StaffEmployee
        if isinstance(current_user, StaffEmployee):
            return current_user
        
        mnr_allowed = [r for r in allowed_roles if normalize_role(r) in VALID_MNR_ROLES]
        if not mnr_allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Staff access required"
            )
        
        user_role = str(getattr(current_user, 'user_type', 'User'))
        normalized_role = normalize_role(user_role)
        normalized_allowed = [normalize_role(r) for r in mnr_allowed]
        
        if normalized_role not in normalized_allowed:
            user_level = get_role_level(normalized_role)
            min_required_level = min([get_role_level(r) for r in normalized_allowed])
            
            if user_level < min_required_level:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Access denied. Required roles: {', '.join(allowed_roles)}"
                )
        
        return current_user
    
    return role_checker

def require_capability(capability: str):
    """
    Dependency to require specific capability - MNR member types only.
    Staff users always have all capabilities.
    """
    async def capability_checker(current_user = Depends(get_current_user_hybrid)):
        from app.models.staff import StaffEmployee
        if isinstance(current_user, StaffEmployee):
            return current_user
        
        user_role = str(getattr(current_user, 'user_type', 'User'))
        if not has_capability(user_role, capability):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required capability: {capability}"
            )
        return current_user
    
    return capability_checker

def require_min_level(min_level: int):
    """
    Dependency to require minimum role level.
    Staff users always pass.
    """
    async def level_checker(current_user = Depends(get_current_user_hybrid)):
        from app.models.staff import StaffEmployee
        if isinstance(current_user, StaffEmployee):
            return current_user
        
        user_role = str(getattr(current_user, 'user_type', 'User'))
        user_level = get_role_level(user_role)
        
        if user_level < min_level:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Minimum role level {min_level} required."
            )
        return current_user
    
    return level_checker

def require_roles_hybrid(allowed_roles: List[str]):
    """
    DC Protocol: Staff-only for admin roles, MNR member check for member roles.
    Staff users always pass. If allowed_roles contains only removed admin types,
    MNR users are rejected - effectively staff-only.
    """
    async def role_checker(current_user = Depends(get_current_user_hybrid)):
        from app.models.staff import StaffEmployee
        if isinstance(current_user, StaffEmployee):
            return current_user
        
        mnr_allowed = [r for r in allowed_roles if normalize_role(r) in VALID_MNR_ROLES]
        if not mnr_allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Staff access required"
            )
        
        user_role = str(getattr(current_user, 'user_type', 'User'))
        normalized_role = normalize_role(user_role)
        normalized_allowed = [normalize_role(r) for r in mnr_allowed]
        
        if normalized_role not in normalized_allowed:
            user_level = get_role_level(normalized_role)
            min_required_level = min([get_role_level(r) for r in normalized_allowed])
            
            if user_level < min_required_level:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Staff access required"
                )
        
        return current_user
    
    return role_checker

# DC Protocol: MNR member role dependencies
require_user = require_roles(['User', 'Member'])
require_member = require_roles(['Member'])

# DC Protocol: Staff-only admin dependencies - MNR admin types removed permanently
require_admin = _require_staff_only()
require_finance_admin = _require_staff_only()
require_super_admin = _require_staff_only()
require_rvz_id = _require_staff_only()

# DC Protocol: Staff-only hybrid dependencies - MNR admin types removed permanently
require_user_hybrid = require_roles(['User', 'Member'])
require_admin_hybrid = _require_staff_only()
require_finance_admin_hybrid = _require_staff_only()
require_super_admin_hybrid = _require_staff_only()
require_rvz_id_hybrid = _require_staff_only()

# Capability-based dependencies (staff always passes, MNR members checked)
require_kyc_review = require_capability('kyc_review')
require_pin_approval = require_capability('pin_approvals')
require_ticket_management = require_capability('ticket_management')
require_financial_control = require_capability('financial_control')
require_system_config = require_capability('system_config')
