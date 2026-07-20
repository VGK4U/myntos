"""
Staff MNR User Sidebar API
DC Protocol: Staff Portal access to view/manage MNR member data
Created: Jan 08, 2026

Purpose: Allow authorized staff (VGK Supreme, EA, Accounts + Menu Access) to view
and perform actions on behalf of any MNR member. Full audit trail maintained.

Features:
- Complete mirror of MNR user sidebar functionality
- MNR ID search and validation on every request
- End-to-end view and action capabilities
- Comprehensive audit logging for compliance
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Body, Form, File, UploadFile
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_, func, desc
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from datetime import datetime, date
import logging

from app.core.database import get_db
from app.api.v1.endpoints.staff_auth import get_current_staff_user
from app.utils.media import normalize_media_path
from app.models.staff import (
    StaffEmployee, StaffMenuMaster, StaffEmployeeMenuSettings,
    get_indian_time
)
from app.models.user import User
from app.models.placement import Placement
from app.models.base import get_indian_time
from app.services.reference_service import ReferenceService
from app.services.user_service import UserService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/staff/mnr-user", tags=["Staff MNR User Sidebar"])


def map_package_points_to_name(points: float) -> str:
    """Map numeric package_points to human-readable package type name
    DC Protocol: 0 points = Eligible (not activated), not Loyal
    """
    if points is None or points == 0:
        return "Eligible"
    if points >= 1.0:
        return "Platinum"
    if points >= 0.5:
        return "Diamond"
    if points >= 0.25:
        return "Star"
    if points > 0:
        return "Loyal"
    return "Eligible"


def check_menu_access(db: Session, employee_id: int, menu_code: str, require_edit: bool = False) -> bool:
    """Check if employee has access to a menu item via Menu Access settings"""
    menu = db.query(StaffMenuMaster).filter(
        StaffMenuMaster.menu_code == menu_code,
        StaffMenuMaster.is_active == True
    ).first()
    
    if not menu:
        return False
    
    settings = db.query(StaffEmployeeMenuSettings).filter(
        StaffEmployeeMenuSettings.employee_id == employee_id,
        StaffEmployeeMenuSettings.menu_id == menu.id
    ).first()
    
    if settings:
        if require_edit:
            return settings.can_edit
        return settings.can_view
    
    if require_edit:
        return menu.is_default_accessible
    return menu.is_default_visible


def check_mnr_user_access(
    db: Session, 
    current_user: StaffEmployee, 
    menu_code: str,
    require_edit: bool = False
) -> bool:
    """
    DC Protocol: Menu-based access control - any authenticated staff has full access.
    Page assignment = full access. No additional role checks needed.
    """
    # DC Protocol: Menu-based access control - page assignment = full access
    # default_roles = ['VGK_SUPREME', 'VGK4U', 'VGK4U Supreme', 'Executive Assistant', 'Accounts']
    # 
    # if current_user.staff_type in default_roles:
    #     return True
    # 
    # return check_menu_access(db, current_user.id, menu_code, require_edit)
    return True


def validate_mnr_id(db: Session, mnr_id: str) -> User:
    """Validate MNR ID and return user object"""
    import re
    if not mnr_id:
        raise HTTPException(status_code=400, detail="MNR ID is required")
    
    mnr_id = mnr_id.strip().upper()
    
    # DC Protocol: Sanitize input - only allow alphanumeric chars to prevent URL/path injection
    mnr_id = re.sub(r'[^A-Z0-9]', '', mnr_id)
    
    if not mnr_id.startswith('MNR'):
        raise HTTPException(status_code=400, detail="Invalid MNR ID format. Must start with 'MNR'")
    
    # Validate MNR ID format (MNR followed by 1-17 digits, max 20 chars total)
    if not re.match(r'^MNR\d{1,17}$', mnr_id):
        raise HTTPException(status_code=400, detail="Invalid MNR ID format. Expected format: MNR followed by numbers (e.g., MNR123456)")
    
    user = db.query(User).filter(User.id == mnr_id).first()
    
    if not user:
        raise HTTPException(status_code=404, detail=f"MNR member {mnr_id} not found")
    
    return user


def validate_member_id(db: Session, member_id: str) -> dict:
    """Validate either an MNR member ID or a VGK partner code and return member info dict.
    DC Protocol (Apr 2026): Unified member lookup supporting both MNR and VGK IDs
    for the announcements staff tool.

    Returns:
        dict with keys: member_id (str), name (str), member_type ('mnr'|'vgk'), status (str)
    """
    import re
    from app.models.staff_accounts import OfficialPartner

    if not member_id:
        raise HTTPException(status_code=400, detail="Member ID is required")

    member_id = re.sub(r'[^A-Z0-9]', '', member_id.strip().upper())

    if member_id.startswith('MNR'):
        if not re.match(r'^MNR\d{1,17}$', member_id):
            raise HTTPException(status_code=400, detail="Invalid MNR ID format. Expected: MNR followed by numbers")
        user = db.query(User).filter(User.id == member_id).first()
        if not user:
            raise HTTPException(status_code=404, detail=f"MNR member {member_id} not found")
        return {
            "member_id": member_id,
            "name": getattr(user, 'name', member_id),
            "member_type": "mnr",
            "status": str(getattr(user, 'account_status', 'active') or 'active'),
        }

    if member_id.startswith('VGK'):
        if not re.match(r'^VGK\w{4,}$', member_id):
            raise HTTPException(status_code=400, detail="Invalid VGK ID format. Expected: VGK followed by alphanumeric characters")
        partner = db.query(OfficialPartner).filter(OfficialPartner.partner_code == member_id).first()
        if not partner:
            raise HTTPException(status_code=404, detail=f"VGK member {member_id} not found")
        return {
            "member_id": member_id,
            "name": partner.partner_name or member_id,
            "member_type": "vgk",
            "status": "active" if partner.is_active else "inactive",
        }

    raise HTTPException(status_code=400, detail="Invalid member ID. Must start with 'MNR' or 'VGK'")


def log_staff_action(
    db: Session,
    staff_id: int,
    staff_emp_code: str,
    mnr_id: str,
    action_type: str,
    action_details: str,
    page_accessed: str,
    ip_address: str = None
):
    """
    DC Protocol: Log all staff actions on MNR member data for audit compliance.
    Creates entry in StaffMnrUserAuditLog table.
    """
    from app.models.staff import StaffMnrUserAuditLog
    
    try:
        audit_log = StaffMnrUserAuditLog(
            staff_employee_id=staff_id,
            staff_emp_code=staff_emp_code,
            mnr_user_id=mnr_id,
            action_type=action_type,
            action_details=action_details,
            page_accessed=page_accessed,
            ip_address=ip_address,
            created_at=get_indian_time()
        )
        db.add(audit_log)
        db.commit()
        logger.info(f"[DC-MNR-USER-AUDIT] Staff {staff_emp_code} - {action_type} on {mnr_id}: {action_details}")
    except Exception as e:
        logger.error(f"[DC-MNR-USER-AUDIT] Failed to log action: {e}")
        db.rollback()


class MnrIdRequest(BaseModel):
    mnr_id: str = Field(..., description="MNR ID to search")


class MnrUserResponse(BaseModel):
    success: bool
    mnr_id: str
    member_info: Dict[str, Any]
    data: Dict[str, Any]


@router.get("/validate/{mnr_id}")
async def validate_mnr_member(
    mnr_id: str,
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Validate MNR ID and return basic member info.
    Used by all pages for MNR ID search functionality.
    """
    if not check_mnr_user_access(db, current_user, "staff_mnr_user_dashboard"):
        raise HTTPException(status_code=403, detail="Access denied to MNR User Sidebar")
    
    user = validate_mnr_id(db, mnr_id)
    
    log_staff_action(
        db=db,
        staff_id=current_user.id,
        staff_emp_code=current_user.emp_code,
        mnr_id=mnr_id,
        action_type="VIEW",
        action_details="Validated MNR ID",
        page_accessed="validate"
    )
    
    return {
        "success": True,
        "mnr_id": user.id,
        "member_info": {
            "name": user.name,
            "mobile": user.phone_number,
            "email": user.email,
            "package_type": getattr(user, 'current_package_type', 'none'),
            "status": user.account_status,
            "city": getattr(user, 'city', None),
            "state": getattr(user, 'state', None),
            "referrer_id": user.referrer_id,
            "activated_at": user.activation_date.isoformat() if user.activation_date else None,
            "created_at": user.registration_date.isoformat() if user.registration_date else None
        }
    }


@router.get("/dashboard/{mnr_id}")
async def get_member_dashboard(
    mnr_id: str,
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get MNR member dashboard data - same as user sees on /user-home
    """
    menu_code = "staff_mnr_user_dashboard"
    if not check_mnr_user_access(db, current_user, menu_code):
        raise HTTPException(status_code=403, detail="Access denied")
    
    user = validate_mnr_id(db, mnr_id)
    reference_service = ReferenceService(db)
    
    from app.services.leg_metrics_cache_service import LegMetricsCacheService
    cache_service = LegMetricsCacheService(db)
    cached_metrics = cache_service.get_user_metrics(mnr_id)
    
    if not cached_metrics:
        cached_metrics = cache_service.refresh_user_metrics(mnr_id, source='on_demand')
    
    team_counts = {
        "left_count": cached_metrics.left_team_count if cached_metrics else 0,
        "right_count": cached_metrics.right_team_count if cached_metrics else 0,
        "total_count": (cached_metrics.left_team_count + cached_metrics.right_team_count) if cached_metrics else 0
    }
    
    direct_referrals = db.query(User).filter(User.referrer_id == mnr_id).count()
    
    from app.models.withdrawal import WithdrawalRequest
    total_withdrawn_result = db.query(func.sum(WithdrawalRequest.final_payout)).filter(
        WithdrawalRequest.user_id == mnr_id,
        WithdrawalRequest.status.in_(['Paid', 'Completed'])
    ).scalar() or 0
    
    wallet_info = {
        "earning_wallet": float(user.earning_wallet or 0),
        "withdrawable_wallet": float(user.withdrawable_wallet or 0),
        "upgrade_wallet": float(user.upgrade_wallet_balance or 0),
        "total_withdrawn": float(total_withdrawn_result)
    }
    
    log_staff_action(
        db=db,
        staff_id=current_user.id,
        staff_emp_code=current_user.emp_code,
        mnr_id=mnr_id,
        action_type="VIEW",
        action_details="Viewed member dashboard",
        page_accessed="dashboard"
    )
    
    return {
        "success": True,
        "mnr_id": mnr_id,
        "member_info": {
            "name": user.name,
            "mobile": user.phone_number,
            "package_type": getattr(user, 'current_package_type', 'none'),
            "status": user.account_status
        },
        "data": {
            "team_counts": team_counts,
            "direct_referrals": direct_referrals,
            "wallet": wallet_info
        }
    }


@router.get("/profile/{mnr_id}")
async def get_member_profile(
    mnr_id: str,
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get MNR member profile data - same as /profile-view
    """
    menu_code = "staff_mnr_user_profile"
    if not check_mnr_user_access(db, current_user, menu_code):
        raise HTTPException(status_code=403, detail="Access denied")
    
    user = validate_mnr_id(db, mnr_id)
    
    log_staff_action(
        db=db,
        staff_id=current_user.id,
        staff_emp_code=current_user.emp_code,
        mnr_id=mnr_id,
        action_type="VIEW",
        action_details="Viewed member profile",
        page_accessed="profile"
    )
    
    from app.models.kyc_document import KYCDocument, BankDetailsApproval
    
    kyc_docs = db.query(KYCDocument).filter(KYCDocument.owner_id == mnr_id).all()
    bank = db.query(BankDetailsApproval).filter(BankDetailsApproval.user_id == mnr_id).first()
    
    return {
        "success": True,
        "mnr_id": mnr_id,
        "member_info": {
            "name": user.name,
            "mobile": user.phone_number,
            "package_type": getattr(user, 'current_package_type', 'none'),
            "status": user.account_status
        },
        "data": {
            "profile": {
                "id": user.id,
                "name": user.name,
                "email": user.email,
                "mobile": user.phone_number,
                "dob": user.actual_date_of_birth.isoformat() if user.actual_date_of_birth else None,
                "gender": getattr(user, 'gender', None),
                "address": getattr(user, 'address', None),
                "city": getattr(user, 'city', None),
                "state": getattr(user, 'state', None),
                "pincode": getattr(user, 'pincode', None),
                "referrer_id": user.referrer_id,
                "status": user.account_status,
                "package_type": getattr(user, 'current_package_type', 'none'),
                "activated_at": user.activation_date.isoformat() if user.activation_date else None,
                "created_at": user.registration_date.isoformat() if user.registration_date else None
            },
            "kyc": {
                "documents": [{
                    "document_type": doc.document_type,
                    "status": doc.status,
                    "uploaded_at": doc.uploaded_at.isoformat() if doc.uploaded_at else None
                } for doc in kyc_docs],
                "kyc_status": user.kyc_status,
                "total_documents": len(kyc_docs)
            },
            "bank": {
                "account_holder_name": bank.bank_account_holder if bank else None,
                "bank_name": bank.bank_name if bank else None,
                "account_number": bank.bank_account_number if bank else None,
                "ifsc_code": bank.bank_ifsc_code if bank else None,
                "branch": bank.bank_branch_name if bank else None,
                "status": bank.status if bank else 'pending'
            } if bank else None
        }
    }


@router.get("/members/{mnr_id}")
async def get_members_unified(
    mnr_id: str,
    view: str = Query("picture", description="View type: picture, direct, downline, all"),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    levels: int = Query(3, ge=1, le=10),
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Unified members endpoint - supports all view types via query param
    Returns data wrapped in 'data' key for frontend compatibility
    """
    menu_code_map = {
        "picture": "staff_mnr_user_members_picture",
        "direct": "staff_mnr_user_members_direct",
        "downline": "staff_mnr_user_members_all",
        "all": "staff_mnr_user_members_all"
    }
    menu_code = menu_code_map.get(view, "staff_mnr_user_members_picture")
    
    if not check_mnr_user_access(db, current_user, menu_code):
        raise HTTPException(status_code=403, detail="Access denied")
    
    user = validate_mnr_id(db, mnr_id)
    reference_service = ReferenceService(db)
    
    # Defensive cache handling
    from app.services.leg_metrics_cache_service import LegMetricsCacheService
    cache_service = LegMetricsCacheService(db)
    try:
        cached_metrics = cache_service.get_user_metrics(mnr_id)
        if not cached_metrics:
            cached_metrics = cache_service.refresh_user_metrics(mnr_id, source='on_demand')
    except Exception as e:
        print(f"[DC-MEMBERS] Cache service error for {mnr_id}: {e}")
        cached_metrics = None
    
    direct_refs = db.query(User).filter(User.referrer_id == mnr_id).all()
    
    # Safe fallback counts
    left_count = cached_metrics.left_team_count if cached_metrics else 0
    right_count = cached_metrics.right_team_count if cached_metrics else 0
    
    counts = {
        "total": left_count + right_count,
        "left": left_count,
        "right": right_count,
        "direct": len(direct_refs)
    }
    
    member_info = {
        "name": user.name,
        "package_type": map_package_points_to_name(user.package_points),
        "status": user.account_status.lower() if user.account_status else 'inactive'
    }
    
    data_payload = {
        "member_info": member_info,
        "counts": counts
    }
    
    if view == "picture":
        team_tree = reference_service.get_team_tree(mnr_id, levels)
        data_payload["tree"] = team_tree
    elif view == "direct":
        members = []
        for member in direct_refs:
            placement = db.query(Placement).filter(Placement.child_id == member.id).first()
            members.append({
                "id": member.id,
                "mnr_id": member.id,
                "name": member.name,
                "mobile": member.phone_number,
                "status": member.account_status.lower() if member.account_status else 'inactive',
                "side": placement.side if placement else None,
                "package_type": map_package_points_to_name(member.package_points),
                "registration_date": member.registration_date.isoformat() if member.registration_date else None,
                "activated_at": member.activation_date.isoformat() if member.activation_date else None
            })
        data_payload["members"] = members
    else:
        from app.services.sql_utils import get_binary_downline_sql
        downline_result = get_binary_downline_sql(db, mnr_id, max_depth=20)
        downline_by_id = {row['id']: row for row in downline_result} if downline_result else {}
        all_downline = list(downline_by_id.keys())
        total = len(all_downline)
        start = (page - 1) * per_page
        end = start + per_page
        paginated = all_downline[start:end]
        
        members = []
        for member_id in paginated:
            member = db.query(User).filter(User.id == member_id).first()
            if member:
                row_data = downline_by_id.get(member_id, {})
                members.append({
                    "id": member.id,
                    "mnr_id": member.id,
                    "name": member.name,
                    "mobile": member.phone_number,
                    "status": member.account_status.lower() if member.account_status else 'inactive',
                    "side": row_data.get('side'),
                    "package_type": map_package_points_to_name(row_data.get('package_points', 0)),
                    "referrer_id": member.referrer_id,
                    "level": row_data.get('level', 0),
                    "registration_date": row_data.get('registration_date').isoformat() if row_data.get('registration_date') else (member.registration_date.isoformat() if member.registration_date else None),
                    "activated_at": member.activation_date.isoformat() if member.activation_date else None
                })
        data_payload["members"] = members
        data_payload["pagination"] = {
            "page": page,
            "per_page": per_page,
            "total": total,
            "total_pages": (total + per_page - 1) // per_page
        }
    
    log_staff_action(
        db=db,
        staff_id=current_user.id,
        staff_emp_code=current_user.emp_code,
        mnr_id=mnr_id,
        action_type="VIEW",
        action_details=f"Viewed members ({view} view)",
        page_accessed=f"members/{view}"
    )
    
    return {
        "success": True,
        "mnr_id": mnr_id,
        "data": data_payload
    }


@router.get("/members/all/{mnr_id}")
async def get_all_members(
    mnr_id: str,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get all team members for MNR user - same as /team
    """
    menu_code = "staff_mnr_user_members_all"
    if not check_mnr_user_access(db, current_user, menu_code):
        raise HTTPException(status_code=403, detail="Access denied")
    
    user = validate_mnr_id(db, mnr_id)
    reference_service = ReferenceService(db)
    
    all_downline = reference_service.get_full_downline(mnr_id)
    
    total = len(all_downline)
    start = (page - 1) * per_page
    end = start + per_page
    paginated = all_downline[start:end]
    
    members = []
    for member_id in paginated:
        member = db.query(User).filter(User.id == member_id).first()
        if member:
            members.append({
                "id": member.id,
                "name": member.name,
                "mobile": member.phone_number,
                "status": member.account_status,
                "package_type": map_package_points_to_name(member.package_points),
                "referrer_id": member.referrer_id,
                "side": getattr(member, 'placement_position', None),
                "registration_date": member.registration_date.isoformat() if member.registration_date else None,
                "activated_at": member.activation_date.isoformat() if member.activation_date else None
            })
    
    log_staff_action(
        db=db,
        staff_id=current_user.id,
        staff_emp_code=current_user.emp_code,
        mnr_id=mnr_id,
        action_type="VIEW",
        action_details=f"Viewed all members (page {page})",
        page_accessed="members/all"
    )
    
    return {
        "success": True,
        "mnr_id": mnr_id,
        "member_info": {
            "name": user.name,
            "package_type": getattr(user, 'current_package_type', 'none'),
            "status": user.account_status
        },
        "data": {
            "members": members,
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": total,
                "total_pages": (total + per_page - 1) // per_page
            }
        }
    }


@router.get("/members/direct/{mnr_id}")
async def get_direct_referrals(
    mnr_id: str,
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get direct referrals for MNR user - same as /team?filter=direct
    """
    menu_code = "staff_mnr_user_members_direct"
    if not check_mnr_user_access(db, current_user, menu_code):
        raise HTTPException(status_code=403, detail="Access denied")
    
    user = validate_mnr_id(db, mnr_id)
    
    direct_refs = db.query(User).filter(User.referrer_id == mnr_id).all()
    
    members = []
    for member in direct_refs:
        members.append({
            "id": member.id,
            "name": member.name,
            "mobile": member.phone_number,
            "status": member.account_status,
            "package_type": map_package_points_to_name(member.package_points),
            "registration_date": member.registration_date.isoformat() if member.registration_date else None,
            "activated_at": member.activation_date.isoformat() if member.activation_date else None
        })
    
    log_staff_action(
        db=db,
        staff_id=current_user.id,
        staff_emp_code=current_user.emp_code,
        mnr_id=mnr_id,
        action_type="VIEW",
        action_details="Viewed direct referrals",
        page_accessed="members/direct"
    )
    
    return {
        "success": True,
        "mnr_id": mnr_id,
        "member_info": {
            "name": user.name,
            "package_type": getattr(user, 'current_package_type', 'none'),
            "status": user.account_status
        },
        "data": {
            "members": members,
            "total": len(members)
        }
    }


@router.get("/members/picture/{mnr_id}")
async def get_picture_view(
    mnr_id: str,
    levels: int = Query(3, ge=1, le=10),
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get binary tree picture view - same as /team-picture (3 levels default)
    """
    menu_code = "staff_mnr_user_members_picture"
    if not check_mnr_user_access(db, current_user, menu_code):
        raise HTTPException(status_code=403, detail="Access denied")
    
    user = validate_mnr_id(db, mnr_id)
    reference_service = ReferenceService(db)
    
    team_tree = reference_service.get_team_tree(mnr_id, levels)
    
    from app.services.leg_metrics_cache_service import LegMetricsCacheService
    cache_service = LegMetricsCacheService(db)
    cached_metrics = cache_service.get_user_metrics(mnr_id)
    
    if not cached_metrics:
        cached_metrics = cache_service.refresh_user_metrics(mnr_id, source='on_demand')
    
    team_counts = {
        "left_count": cached_metrics.left_team_count if cached_metrics else 0,
        "right_count": cached_metrics.right_team_count if cached_metrics else 0,
        "total_count": (cached_metrics.left_team_count + cached_metrics.right_team_count) if cached_metrics else 0
    }
    
    log_staff_action(
        db=db,
        staff_id=current_user.id,
        staff_emp_code=current_user.emp_code,
        mnr_id=mnr_id,
        action_type="VIEW",
        action_details=f"Viewed picture view ({levels} levels)",
        page_accessed="members/picture"
    )
    
    return {
        "success": True,
        "mnr_id": mnr_id,
        "member_info": {
            "name": user.name,
            "package_type": getattr(user, 'current_package_type', 'none'),
            "status": user.account_status
        },
        "data": {
            "tree": team_tree,
            "team_statistics": team_counts,
            "levels": levels
        }
    }


@router.get("/members/ved/{mnr_id}")
async def get_ved_team(
    mnr_id: str,
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get Ved team members - same as /team?filter=ved
    """
    menu_code = "staff_mnr_user_members_ved"
    if not check_mnr_user_access(db, current_user, menu_code):
        raise HTTPException(status_code=403, detail="Access denied")
    
    user = validate_mnr_id(db, mnr_id)
    
    from app.models.ved_team import VedTeamMember
    ved_members = db.query(VedTeamMember).filter(
        VedTeamMember.ved_head_id == mnr_id
    ).all()
    
    members = []
    for vm in ved_members:
        member = db.query(User).filter(User.id == vm.member_id).first()
        if member:
            placement = db.query(Placement).filter(Placement.child_id == member.id).first()
            members.append({
                "id": member.id,
                "name": member.name,
                "mobile": member.phone_number,
                "status": member.account_status,
                "side": placement.side if placement else None,
                "package_type": map_package_points_to_name(member.package_points),
                "ved_status": "Active" if vm.is_active else "Inactive",
                "registration_date": member.registration_date.isoformat() if member.registration_date else None,
                "activated_at": member.activation_date.isoformat() if member.activation_date else None
            })
    
    log_staff_action(
        db=db,
        staff_id=current_user.id,
        staff_emp_code=current_user.emp_code,
        mnr_id=mnr_id,
        action_type="VIEW",
        action_details="Viewed Ved team",
        page_accessed="members/ved"
    )
    
    return {
        "success": True,
        "mnr_id": mnr_id,
        "member_info": {
            "name": user.name,
            "package_type": getattr(user, 'current_package_type', 'none'),
            "status": user.account_status
        },
        "data": {
            "members": members,
            "total": len(members)
        }
    }


@router.get("/mnr/earnings-summary/{mnr_id}")
async def get_earnings_summary(
    mnr_id: str,
    income_type: Optional[str] = Query(None, description="Filter by income type: direct, matching, ved, guru"),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get earnings summary or filtered income transactions.
    Without income_type: Returns summary of all earnings.
    With income_type (direct/matching/ved/guru): Returns paginated transaction list.
    """
    menu_code = "staff_mnr_user_mnr_earnings"
    if not check_mnr_user_access(db, current_user, menu_code):
        raise HTTPException(status_code=403, detail="Access denied")
    
    user = validate_mnr_id(db, mnr_id)
    
    from app.models.transaction import PendingIncome
    
    if income_type:
        return await get_income_transactions(
            mnr_id=mnr_id,
            income_type=income_type,
            page=page,
            per_page=per_page,
            current_user=current_user,
            db=db
        )
    
    direct_income = db.query(func.coalesce(func.sum(PendingIncome.net_amount), 0)).filter(
        PendingIncome.user_id == mnr_id,
        PendingIncome.income_type == 'Direct Referral',
        PendingIncome.verification_status == 'Completed'
    ).scalar() or 0
    
    matching_income = db.query(func.coalesce(func.sum(PendingIncome.net_amount), 0)).filter(
        PendingIncome.user_id == mnr_id,
        PendingIncome.income_type == 'Matching Referral',
        PendingIncome.verification_status == 'Completed'
    ).scalar() or 0
    
    ved_income = db.query(func.coalesce(func.sum(PendingIncome.net_amount), 0)).filter(
        PendingIncome.user_id == mnr_id,
        PendingIncome.income_type == 'Ved Income',
        PendingIncome.verification_status == 'Completed'
    ).scalar() or 0
    
    guru_income = db.query(func.coalesce(func.sum(PendingIncome.net_amount), 0)).filter(
        PendingIncome.user_id == mnr_id,
        PendingIncome.income_type == 'Guru Dakshina',
        PendingIncome.verification_status == 'Completed'
    ).scalar() or 0
    
    log_staff_action(
        db=db,
        staff_id=current_user.id,
        staff_emp_code=current_user.emp_code,
        mnr_id=mnr_id,
        action_type="VIEW",
        action_details="Viewed earnings summary",
        page_accessed="mnr/earnings-summary"
    )
    
    return {
        "success": True,
        "mnr_id": mnr_id,
        "member_info": {
            "name": user.name,
            "package_type": getattr(user, 'current_package_type', 'none'),
            "status": user.account_status
        },
        "data": {
            "earnings": {
                "direct_referral": float(direct_income),
                "matching_referral": float(matching_income),
                "ved_income": float(ved_income),
                "guru_dakshina": float(guru_income),
                "total": float(direct_income + matching_income + ved_income + guru_income)
            },
            "wallet": {
                "earning_wallet": float(user.earning_wallet or 0),
                "withdrawable_wallet": float(user.withdrawable_wallet or 0),
                "upgrade_wallet": float(user.upgrade_wallet_balance or 0),
                "total_withdrawn": float(getattr(user, 'total_withdrawn', 0) or 0)
            }
        }
    }


@router.get("/mnr/withdrawals/{mnr_id}")
async def get_withdrawals(
    mnr_id: str,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get withdrawal history - same as /user/withdrawals
    """
    menu_code = "staff_mnr_user_mnr_withdrawals"
    if not check_mnr_user_access(db, current_user, menu_code):
        raise HTTPException(status_code=403, detail="Access denied")
    
    user = validate_mnr_id(db, mnr_id)
    
    from app.models.withdrawal import WithdrawalRequest
    
    query = db.query(WithdrawalRequest).filter(
        WithdrawalRequest.user_id == mnr_id
    ).order_by(desc(WithdrawalRequest.created_at))
    
    total = query.count()
    withdrawals = query.offset((page - 1) * per_page).limit(per_page).all()
    
    withdrawal_list = []
    for w in withdrawals:
        withdrawal_list.append({
            "id": w.id,
            "amount": float(w.withdrawal_amount or 0),
            "status": w.status,
            "request_date": w.request_date.isoformat() if w.request_date else (w.created_at.isoformat() if w.created_at else None),
            "approved_date": w.processed_at.isoformat() if w.processed_at else None,
            "deduction": float((w.admin_charges or 0) + (w.tds_amount or 0)),
            "net_amount": float(w.final_payout or 0)
        })
    
    log_staff_action(
        db=db,
        staff_id=current_user.id,
        staff_emp_code=current_user.emp_code,
        mnr_id=mnr_id,
        action_type="VIEW",
        action_details=f"Viewed withdrawals (page {page})",
        page_accessed="mnr/withdrawals"
    )
    
    return {
        "success": True,
        "mnr_id": mnr_id,
        "member_info": {
            "name": user.name,
            "package_type": getattr(user, 'current_package_type', 'none'),
            "status": user.account_status
        },
        "data": {
            "withdrawals": withdrawal_list,
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": total,
                "total_pages": (total + per_page - 1) // per_page
            }
        }
    }


async def get_income_transactions(
    mnr_id: str,
    income_type: str,
    page: int,
    per_page: int,
    current_user: StaffEmployee,
    db: Session
) -> Dict[str, Any]:
    """
    Get income transactions filtered by type (direct, matching, ved, guru)
    """
    income_type_map = {
        "direct": "Direct Referral",
        "matching": "Matching Referral",
        "ved": "Ved Income",
        "guru": "Guru Dakshina"
    }
    
    db_income_type = income_type_map.get(income_type, "Direct Referral")
    user = validate_mnr_id(db, mnr_id)
    
    from app.models.transaction import PendingIncome
    
    query = db.query(PendingIncome).filter(
        PendingIncome.user_id == mnr_id,
        PendingIncome.income_type == db_income_type
    ).order_by(desc(PendingIncome.created_at))
    
    total = query.count()
    transactions = query.offset((page - 1) * per_page).limit(per_page).all()
    
    total_earned = db.query(func.coalesce(func.sum(PendingIncome.net_amount), 0)).filter(
        PendingIncome.user_id == mnr_id,
        PendingIncome.income_type == db_income_type,
        PendingIncome.verification_status == 'Completed'
    ).scalar() or 0
    
    transaction_list = []
    for t in transactions:
        from_user_name = None
        if t.related_user_id:
            from app.models.user import User
            related_user = db.query(User).filter(User.id == t.related_user_id).first()
            from_user_name = related_user.name if related_user else None
        
        transaction_list.append({
            "id": t.id,
            "amount": float(t.net_amount or 0),
            "gross_amount": float(t.gross_amount or 0),
            "status": t.verification_status,
            "from_user": t.related_user_id,
            "from_user_name": from_user_name,
            "description": t.notes,
            "created_at": t.created_at.isoformat() if t.created_at else None,
            "verified_at": t.admin_verified_at.isoformat() if t.admin_verified_at else None
        })
    
    log_staff_action(
        db=db,
        staff_id=current_user.id,
        staff_emp_code=current_user.emp_code,
        mnr_id=mnr_id,
        action_type="VIEW",
        action_details=f"Viewed {income_type} income (page {page})",
        page_accessed=f"mnr/{income_type}"
    )
    
    return {
        "success": True,
        "mnr_id": mnr_id,
        "member_info": {
            "name": user.name,
            "package_type": getattr(user, 'current_package_type', 'none'),
            "status": user.account_status
        },
        "data": {
            "income_type": income_type,
            "income_type_label": db_income_type,
            "total_earned": float(total_earned),
            "transactions": transaction_list,
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": total,
                "total_pages": (total + per_page - 1) // per_page
            }
        }
    }


@router.get("/awards/all/{mnr_id}")
async def get_awards(
    mnr_id: str,
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get all awards - same as /user/awards
    """
    menu_code = "staff_mnr_user_awards_all"
    if not check_mnr_user_access(db, current_user, menu_code):
        raise HTTPException(status_code=403, detail="Access denied")
    
    user = validate_mnr_id(db, mnr_id)
    
    from app.models.awards import UserAwardProgress, UserMatchingAwardProgress
    
    direct_awards = db.query(UserAwardProgress).filter(
        UserAwardProgress.user_id == mnr_id
    ).all()
    
    matching_awards = db.query(UserMatchingAwardProgress).filter(
        UserMatchingAwardProgress.user_id == mnr_id
    ).all()
    
    direct_list = [{
        "id": a.id,
        "award_name": getattr(a, 'tier_name', 'Direct Award'),
        "status": getattr(a, 'status', 'active'),
        "awarded_at": a.created_at.isoformat() if a.created_at else None
    } for a in direct_awards]
    
    matching_list = [{
        "id": a.id,
        "award_name": getattr(a, 'tier_name', 'Matching Award'),
        "status": getattr(a, 'status', 'active'),
        "awarded_at": a.created_at.isoformat() if a.created_at else None
    } for a in matching_awards]
    
    log_staff_action(
        db=db,
        staff_id=current_user.id,
        staff_emp_code=current_user.emp_code,
        mnr_id=mnr_id,
        action_type="VIEW",
        action_details="Viewed awards",
        page_accessed="awards/all"
    )
    
    return {
        "success": True,
        "mnr_id": mnr_id,
        "member_info": {
            "name": user.name,
            "package_type": getattr(user, 'current_package_type', 'none'),
            "status": user.account_status
        },
        "data": {
            "direct_awards": direct_list,
            "matching_awards": matching_list,
            "total_direct": len(direct_list),
            "total_matching": len(matching_list)
        }
    }


@router.get("/audit-log")
async def get_audit_log(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    mnr_id: Optional[str] = Query(None),
    staff_emp_code: Optional[str] = Query(None),
    action_type: Optional[str] = Query(None),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get audit log of all staff actions on MNR member data.
    Only VGK Mentor can access full audit log.
    """
    allowed_roles = ['VGK_SUPREME', 'VGK4U', 'VGK4U Supreme']
    if current_user.staff_type not in allowed_roles:
        raise HTTPException(status_code=403, detail="Only VGK Mentor can access audit log")
    
    from app.models.staff import StaffMnrUserAuditLog
    
    query = db.query(StaffMnrUserAuditLog)
    
    if mnr_id:
        query = query.filter(StaffMnrUserAuditLog.mnr_user_id == mnr_id.upper())
    
    if staff_emp_code:
        query = query.filter(StaffMnrUserAuditLog.staff_emp_code.ilike(f"%{staff_emp_code}%"))
    
    if action_type:
        query = query.filter(StaffMnrUserAuditLog.action_type == action_type)
    
    if date_from:
        query = query.filter(func.date(StaffMnrUserAuditLog.created_at) >= date_from)
    
    if date_to:
        query = query.filter(func.date(StaffMnrUserAuditLog.created_at) <= date_to)
    
    query = query.order_by(desc(StaffMnrUserAuditLog.created_at))
    
    total = query.count()
    logs = query.offset((page - 1) * per_page).limit(per_page).all()
    
    log_list = [{
        "id": log.id,
        "staff_emp_code": log.staff_emp_code,
        "mnr_user_id": log.mnr_user_id,
        "action_type": log.action_type,
        "action_details": log.action_details,
        "page_accessed": log.page_accessed,
        "ip_address": log.ip_address,
        "created_at": log.created_at.isoformat() if log.created_at else None
    } for log in logs]
    
    return {
        "success": True,
        "data": {
            "logs": log_list,
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": total,
                "total_pages": (total + per_page - 1) // per_page
            }
        }
    }


# DC Protocol (Jan 24, 2026): IMPORTANT - This route MUST be defined BEFORE /announcements/{mnr_id}
# to avoid FastAPI route collision (specific routes before parameterized routes)
@router.get("/announcements/all")
async def get_all_announcements_staff(
    category_id: Optional[int] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    city: Optional[str] = None,
    user_id: Optional[str] = None,
    user_name: Optional[str] = None,
    status: Optional[str] = None,
    include_hidden: bool = False,
    include_deleted: bool = False,
    include_all_statuses: bool = False,
    limit: Optional[int] = None,
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
) -> List[Dict[str, Any]]:
    """Get all announcements for staff with menu access (not admin-only)
    DC Protocol (Jan 24, 2026): Staff view announcements with proper menu access check
    Replaces admin-only /feedback/announcements/staff for staff portal users
    """
    menu_code = "staff_mnr_user_announcements"
    if not check_mnr_user_access(db, current_user, menu_code):
        raise HTTPException(status_code=403, detail="Access denied to announcements")
    
    from app.models.feedback import FeedbackSubmission, SubmissionStatus, FeedbackCategory, FeedbackMedia, AnnouncementRating
    from sqlalchemy import func as sql_func
    
    query = db.query(
        FeedbackSubmission,
        User.name.label('user_name'),
        User.city.label('city'),
        sql_func.coalesce(sql_func.avg(AnnouncementRating.rating), 0).label('average_rating'),
        sql_func.count(AnnouncementRating.id).label('total_ratings')
    ).outerjoin(
        User, FeedbackSubmission.user_id == User.id
    ).outerjoin(
        AnnouncementRating, FeedbackSubmission.id == AnnouncementRating.submission_id
    ).group_by(
        FeedbackSubmission.id,
        User.name,
        User.city
    )
    
    # Status filter
    if status:
        status_upper = status.upper()
        if status_upper == 'HIDDEN':
            query = query.filter(
                FeedbackSubmission.is_visible == False,
                FeedbackSubmission.is_deleted == False
            )
        elif status_upper == 'DELETED':
            query = query.filter(FeedbackSubmission.is_deleted == True)
        elif status_upper == 'APPROVED':
            query = query.filter(
                FeedbackSubmission.status == SubmissionStatus.APPROVED,
                FeedbackSubmission.is_visible == True,
                FeedbackSubmission.is_deleted == False
            )
        elif status_upper == 'PENDING':
            query = query.filter(
                FeedbackSubmission.status == SubmissionStatus.PENDING,
                FeedbackSubmission.is_deleted == False
            )
        elif status_upper == 'REJECTED':
            query = query.filter(
                FeedbackSubmission.status == SubmissionStatus.REJECTED,
                FeedbackSubmission.is_deleted == False
            )
        elif status_upper == 'UNDER_REVIEW':
            query = query.filter(
                FeedbackSubmission.status == SubmissionStatus.UNDER_REVIEW,
                FeedbackSubmission.is_deleted == False
            )
        elif status_upper == 'PARTIALLY_APPROVED':
            query = query.filter(
                FeedbackSubmission.status == SubmissionStatus.PARTIALLY_APPROVED,
                FeedbackSubmission.is_deleted == False
            )
    else:
        # Default: show approved/visible unless include flags set
        if include_all_statuses:
            if not include_deleted:
                query = query.filter(FeedbackSubmission.is_deleted == False)
        elif include_hidden and include_deleted:
            pass
        elif include_hidden:
            query = query.filter(FeedbackSubmission.is_deleted == False)
        elif include_deleted:
            query = query.filter(FeedbackSubmission.is_visible == True)
        else:
            query = query.filter(
                FeedbackSubmission.status == SubmissionStatus.APPROVED,
                FeedbackSubmission.is_visible == True,
                FeedbackSubmission.is_deleted == False
            )
    
    # Category filter
    if category_id:
        query = query.filter(FeedbackSubmission.category_id == category_id)
    
    # Date range filter
    if start_date:
        query = query.filter(FeedbackSubmission.submitted_at >= start_date)
    if end_date:
        from datetime import datetime, timedelta
        end_datetime = datetime.combine(end_date, datetime.max.time())
        query = query.filter(FeedbackSubmission.submitted_at <= end_datetime)
    
    # City filter
    if city:
        query = query.filter(User.city.ilike(f"%{city}%"))
    
    # User filters
    if user_id:
        query = query.filter(FeedbackSubmission.user_id == user_id)
    if user_name:
        query = query.filter(User.name.ilike(f"%{user_name}%"))
    
    # Order and limit
    query = query.order_by(desc(FeedbackSubmission.submitted_at))
    if limit:
        query = query.limit(limit)
    
    results = query.all()
    
    response_list = []
    for row in results:
        submission = row[0]
        submitter_name = row[1]
        submitter_city = row[2]
        avg_rating = float(row[3]) if row[3] else 0
        rating_count = row[4] or 0
        
        # Get media
        media_list = db.query(FeedbackMedia).filter(
            FeedbackMedia.submission_id == submission.id
        ).all()
        
        # DC Protocol: Match frontend expected schema (category object, media_type field)
        response_list.append({
            "id": submission.id,
            "title": submission.title,
            "description": submission.description,
            "category_id": submission.category_id,
            "category": {
                "id": submission.category.id if submission.category else None,
                "category_name": submission.category.name if submission.category else "General"
            } if submission.category else {"id": None, "category_name": "General"},
            "submission_type": submission.submission_type.value if submission.submission_type else None,
            "status": submission.status.value if submission.status else None,
            "is_visible": submission.is_visible,
            "is_deleted": submission.is_deleted,
            "submitted_at": submission.submitted_at.isoformat() if submission.submitted_at else None,
            "approved_at": submission.approved_at.isoformat() if submission.approved_at else None,
            "user_id": submission.user_id,
            "user_name": submitter_name if submitter_name else submission.user_id,
            "city": submitter_city or "",
            "average_rating": round(avg_rating, 1),
            "total_ratings": rating_count,
            "visible_to": getattr(submission, 'visible_to', 'both') or 'both',
            "media": [{
                "id": m.id,
                "file_path": normalize_media_path(m.file_path),
                "file_type": m.file_type,
                "media_type": "video" if m.file_type and m.file_type.startswith("video/") else "image",
                "original_filename": m.original_filename
            } for m in media_list]
        })
    
    log_staff_action(
        db=db,
        staff_id=current_user.id,
        staff_emp_code=current_user.emp_code,
        mnr_id="SYSTEM",
        action_type="VIEW",
        action_details=f"Viewed all announcements (filters: status={status}, category={category_id})",
        page_accessed="announcements_view"
    )
    
    return response_list


@router.get("/announcements/{mnr_id}")
async def get_announcements(
    mnr_id: str,
    type: str = Query("all", description="Filter type: all, events, offers, news, my"),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Get announcements for member - same as user sees
    DC Protocol (Jan 10, 2026): Uses FeedbackSubmission model - approved submissions are announcements
    """
    menu_code = "staff_mnr_user_announcements"
    if not check_mnr_user_access(db, current_user, menu_code):
        raise HTTPException(status_code=403, detail="Access denied")
    
    member = validate_member_id(db, mnr_id)
    resolved_member_id = member["member_id"]
    
    from app.models.feedback import FeedbackSubmission, SubmissionStatus, FeedbackCategory
    
    query = db.query(FeedbackSubmission).filter(
        FeedbackSubmission.status == SubmissionStatus.APPROVED,
        FeedbackSubmission.is_visible == True
    )
    
    if type == "my":
        query = query.filter(FeedbackSubmission.user_id == resolved_member_id)
    elif type != "all":
        type_to_category_map = {
            "events": "event",
            "offers": "promotion",
            "news": "general meeting",
        }
        search_name = type_to_category_map.get(type.lower(), type.lower())
        category = db.query(FeedbackCategory).filter(
            func.lower(FeedbackCategory.name) == search_name
        ).first()
        if category:
            query = query.filter(FeedbackSubmission.category_id == category.id)
    
    query = query.order_by(desc(FeedbackSubmission.approved_at))
    
    total = query.count()
    announcements = query.offset((page - 1) * per_page).limit(per_page).all()
    
    announcement_list = [{
        "id": a.id,
        "title": a.title,
        "content": a.description or "",
        "type": (a.category.name.lower() if a.category else "general"),
        "status": a.status.value if a.status else "approved",
        "category": a.category.name if a.category else None,
        "submission_type": a.submission_type.value if a.submission_type else None,
        "views_count": getattr(a, 'views_count', 0),
        "shares_count": getattr(a, 'shares_count', 0),
        "submitted_by": a.user_id,
        "approved_at": a.approved_at.isoformat() if a.approved_at else None,
        "created_at": a.submitted_at.isoformat() if a.submitted_at else None,
        "visible_to": getattr(a, 'visible_to', 'both') or 'both'
    } for a in announcements]
    
    log_staff_action(
        db=db,
        staff_id=current_user.id,
        staff_emp_code=current_user.emp_code,
        mnr_id=mnr_id,
        action_type="VIEW",
        action_details=f"Viewed announcements (type={type})",
        page_accessed="announcements"
    )
    
    return {
        "success": True,
        "mnr_id": resolved_member_id,
        "member_info": {"name": member["name"], "status": member["status"], "member_type": member["member_type"]},
        "data": announcement_list,
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total": total,
            "total_pages": (total + per_page - 1) // per_page
        }
    }


def get_video_duration_seconds(file_path: str) -> float:
    """Get video duration in seconds using ffprobe (sync function)
    DC Protocol (Jan 24, 2026): Video duration validation for announcements
    """
    import subprocess
    try:
        result = subprocess.run(
            ['ffprobe', '-v', 'error', '-show_entries', 'format=duration', 
             '-of', 'default=noprint_wrappers=1:nokey=1', file_path],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0 and result.stdout.strip():
            return float(result.stdout.strip())
    except Exception as e:
        logger.warning(f"[DC-VIDEO-DURATION] Failed to get duration: {e}")
    return 0.0


def is_video_file(filename: str) -> bool:
    """Check if file is a video based on extension"""
    video_extensions = {'.mp4', '.mov', '.avi', '.mkv', '.webm', '.m4v', '.3gp'}
    import os
    ext = os.path.splitext(filename.lower())[1]
    return ext in video_extensions


def is_image_file(filename: str) -> bool:
    """Check if file is an image based on extension"""
    image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.heic', '.heif'}
    import os
    ext = os.path.splitext(filename.lower())[1]
    return ext in image_extensions


@router.post("/announcements/submit")
async def submit_announcement_for_user(
    user_id: str = Form(...),
    category_id: int = Form(...),
    submission_type: str = Form("mixed"),
    title: str = Form(...),
    description: str = Form(None),
    visible_to: str = Form("both"),
    files: List[UploadFile] = File(default=None),
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Submit announcement on behalf of MNR or VGK member - auto-approved for staff submissions
    DC Protocol (Jan 24, 2026): Enhanced mixed media support
    DC Protocol (Apr 2026): Extended to support VGK member IDs (VGK...) in addition to MNR IDs
    - Minimum 3 media files (any combination of photos + videos)
    - Photos: up to 10 images
    - Videos: max 3 minutes duration each
    - Staff submissions auto-approved
    """
    menu_code = "staff_mnr_user_announcements"
    if not check_mnr_user_access(db, current_user, menu_code):
        raise HTTPException(status_code=403, detail="Access denied")
    
    member = validate_member_id(db, user_id)
    resolved_user_id = member["member_id"]
    
    from app.models.feedback import FeedbackSubmission, FeedbackMedia, SubmissionStatus, SubmissionType, FeedbackCategory, MediaStatus
    from datetime import datetime
    import os
    import uuid
    import tempfile
    
    category = db.query(FeedbackCategory).filter(FeedbackCategory.id == category_id).first()
    if not category:
        raise HTTPException(status_code=400, detail="Invalid category")
    
    try:
        sub_type = SubmissionType(submission_type)
    except ValueError:
        sub_type = SubmissionType.MIXED
    
    valid_files = [f for f in (files or []) if f and f.filename]
    media_count = len(valid_files)
    
    image_files = [f for f in valid_files if is_image_file(f.filename)]
    video_files = [f for f in valid_files if is_video_file(f.filename)]
    image_count = len(image_files)
    video_count = len(video_files)
    
    if sub_type == SubmissionType.MIXED or media_count > 0:
        if media_count < 3:
            raise HTTPException(status_code=400, detail="Minimum 3 media files required (photos and/or videos)")
        if image_count > 10:
            raise HTTPException(status_code=400, detail="Maximum 10 photos allowed")
        
        for vf in video_files:
            temp_path = None
            try:
                with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(vf.filename)[1]) as tmp:
                    content = await vf.read()
                    tmp.write(content)
                    temp_path = tmp.name
                await vf.seek(0)
                
                duration = get_video_duration_seconds(temp_path)
                if duration > 180:
                    raise HTTPException(status_code=400, detail=f"Video '{vf.filename}' exceeds 3 minute limit ({int(duration)}s)")
            finally:
                if temp_path and os.path.exists(temp_path):
                    os.unlink(temp_path)
    
    if image_count > 0 and video_count > 0:
        sub_type = SubmissionType.MIXED
    elif video_count > 0:
        sub_type = SubmissionType.VIDEO
    elif image_count > 0:
        sub_type = SubmissionType.PHOTO
    else:
        sub_type = SubmissionType.TEXT
    
    # DC Protocol: Reset all file pointers before database operations
    for f in valid_files:
        try:
            await f.seek(0)
        except Exception as seek_err:
            logger.warning(f"[DC-STAFF-ANNOUNCE] Could not reset file pointer for {f.filename}: {seek_err}")
    
    try:
        # Validate and normalise visible_to
        _valid_visible = ('mnr', 'vgk', 'both')
        _visible_to = (visible_to or 'both').strip().lower()
        if _visible_to not in _valid_visible:
            _visible_to = 'both'

        new_submission = FeedbackSubmission(
            user_id=resolved_user_id,
            category_id=category_id,
            submission_type=sub_type,
            title=title,
            description=description or "",
            status=SubmissionStatus.APPROVED,
            is_visible=True,
            submitted_at=datetime.utcnow(),
            approved_at=datetime.utcnow(),
            approved_by=None,
            approved_media_count=media_count,
            visible_to=_visible_to
        )
        
        db.add(new_submission)
        db.commit()
        db.refresh(new_submission)
    except Exception as db_err:
        logger.error(f"[DC-STAFF-ANNOUNCE] Database error creating submission: {db_err}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(db_err)}")
    
    if valid_files:
        from app.services.universal_upload_service import UniversalUploadService
        from app.services.object_storage import storage_service
        
        for file in valid_files:
            try:
                # Reset file pointer before each upload
                await file.seek(0)
                
                upload_result = await UniversalUploadService.handle_upload(
                    file=file,
                    table_name='feedback_media',
                    record_id=new_submission.id,
                    uploaded_by_id=current_user.id,
                    uploaded_by_type='staff',
                    storage_dir='feedback_media',
                    db=db,
                    emp_code=current_user.emp_code,
                    allow_videos=True
                )
                
                media_record = FeedbackMedia(
                    submission_id=new_submission.id,
                    file_path=upload_result['file_path'],
                    file_type=upload_result['file_type'],
                    file_size=upload_result['file_size'],
                    original_filename=upload_result['original_filename'],
                    uploaded_by_emp_code=current_user.emp_code,
                    media_status=MediaStatus.APPROVED,
                    processing_status='completed',
                    original_checksum=upload_result.get('original_checksum'),
                    original_storage_type=upload_result.get('storage_type'),
                    original_storage_key=upload_result.get('storage_key')
                )
                db.add(media_record)
            except HTTPException:
                raise
            except Exception as upload_err:
                logger.error(f"[DC-STAFF-ANNOUNCE] Upload failed for {file.filename}: {upload_err}", exc_info=True)
                raise HTTPException(status_code=500, detail=f"File upload failed for {file.filename}: {str(upload_err)}")
        
        try:
            db.commit()
        except Exception as commit_err:
            logger.error(f"[DC-STAFF-ANNOUNCE] Commit failed after uploads: {commit_err}")
            db.rollback()
            raise HTTPException(status_code=500, detail=f"Database commit failed: {str(commit_err)}")
    
    log_staff_action(
        db=db,
        staff_id=current_user.id,
        staff_emp_code=current_user.emp_code,
        mnr_id=resolved_user_id,
        action_type="CREATE",
        action_details=f"Submitted announcement '{title}' with {image_count} photos and {video_count} videos (auto-approved)",
        page_accessed="announcements"
    )
    
    return {
        "success": True,
        "message": "Announcement submitted and approved successfully",
        "data": {
            "id": new_submission.id,
            "title": new_submission.title,
            "status": "approved",
            "media_count": media_count,
            "image_count": image_count,
            "video_count": video_count,
            "created_at": new_submission.submitted_at.isoformat()
        }
    }


@router.put("/announcements/{announcement_id}/edit")
async def edit_announcement(
    announcement_id: int,
    title: str = Form(None),
    description: str = Form(None),
    visible_to: str = Form(None),
    category_id: Optional[int] = Form(None),
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Edit announcement title, description, audience targeting (visible_to), and category.
    DC Protocol (Jan 24, 2026): Edit by original submitter or staff with menu access
    DC Protocol (Mar 2026): Added visible_to audience targeting field
    DC Protocol (Apr 2026): Added category_id editing support
    """
    menu_code = "staff_mnr_user_announcements"
    if not check_mnr_user_access(db, current_user, menu_code):
        raise HTTPException(status_code=403, detail="Access denied")

    from app.models.feedback import FeedbackSubmission, FeedbackCategory

    submission = db.query(FeedbackSubmission).filter(FeedbackSubmission.id == announcement_id).first()
    if not submission:
        raise HTTPException(status_code=404, detail="Announcement not found")

    updated_fields = []
    if title is not None and title.strip():
        submission.title = title.strip()
        updated_fields.append("title")
    if description is not None:
        submission.description = description.strip()
        updated_fields.append("description")
    if visible_to is not None:
        _v = visible_to.strip().lower()
        if _v in ('mnr', 'vgk', 'both'):
            submission.visible_to = _v
            updated_fields.append("visible_to")
    if category_id is not None:
        category = db.query(FeedbackCategory).filter(
            FeedbackCategory.id == category_id,
            FeedbackCategory.is_active == True
        ).first()
        if not category:
            raise HTTPException(status_code=400, detail="Invalid category")
        submission.category_id = category_id
        updated_fields.append("category")

    if not updated_fields:
        raise HTTPException(status_code=400, detail="No fields to update")

    db.commit()
    db.refresh(submission)

    log_staff_action(
        db=db,
        staff_id=current_user.id,
        staff_emp_code=current_user.emp_code,
        mnr_id=submission.user_id,
        action_type="UPDATE",
        action_details=f"Edited announcement #{announcement_id}: {', '.join(updated_fields)}",
        page_accessed="announcements"
    )

    return {
        "success": True,
        "message": "Announcement updated successfully",
        "data": {
            "id": submission.id,
            "title": submission.title,
            "description": submission.description,
            "visible_to": submission.visible_to,
            "category_id": submission.category_id,
            "category_name": submission.category.name if submission.category else None
        }
    }


@router.delete("/announcements/{announcement_id}/media/{media_id}")
async def delete_announcement_media(
    announcement_id: int,
    media_id: int,
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Delete individual media from announcement
    DC Protocol (Jan 24, 2026): Maintains minimum 3 media requirement
    """
    menu_code = "staff_mnr_user_announcements"
    if not check_mnr_user_access(db, current_user, menu_code):
        raise HTTPException(status_code=403, detail="Access denied")
    
    from app.models.feedback import FeedbackSubmission, FeedbackMedia
    
    submission = db.query(FeedbackSubmission).filter(FeedbackSubmission.id == announcement_id).first()
    if not submission:
        raise HTTPException(status_code=404, detail="Announcement not found")
    
    media = db.query(FeedbackMedia).filter(
        FeedbackMedia.id == media_id,
        FeedbackMedia.submission_id == announcement_id
    ).first()
    if not media:
        raise HTTPException(status_code=404, detail="Media not found")
    
    current_media_count = db.query(FeedbackMedia).filter(
        FeedbackMedia.submission_id == announcement_id
    ).count()
    
    if current_media_count <= 3:
        raise HTTPException(status_code=400, detail="Cannot delete - minimum 3 media files required")
    
    db.delete(media)
    submission.approved_media_count = max(0, (submission.approved_media_count or 0) - 1)
    db.commit()
    
    log_staff_action(
        db=db,
        staff_id=current_user.id,
        staff_emp_code=current_user.emp_code,
        mnr_id=submission.user_id,
        action_type="DELETE",
        action_details=f"Deleted media #{media_id} from announcement #{announcement_id}",
        page_accessed="announcements"
    )
    
    return {
        "success": True,
        "message": "Media deleted successfully",
        "remaining_media": current_media_count - 1
    }


@router.post("/announcements/{announcement_id}/media")
async def add_announcement_media(
    announcement_id: int,
    files: List[UploadFile] = File(...),
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Add more media to existing announcement
    DC Protocol (Jan 24, 2026): Validates photo limit (10) and video duration (3min)
    """
    menu_code = "staff_mnr_user_announcements"
    if not check_mnr_user_access(db, current_user, menu_code):
        raise HTTPException(status_code=403, detail="Access denied")
    
    from app.models.feedback import FeedbackSubmission, FeedbackMedia, MediaStatus, SubmissionType
    from app.services.universal_upload_service import UniversalUploadService
    import os
    import tempfile
    
    submission = db.query(FeedbackSubmission).filter(FeedbackSubmission.id == announcement_id).first()
    if not submission:
        raise HTTPException(status_code=404, detail="Announcement not found")
    
    valid_files = [f for f in files if f and f.filename]
    if not valid_files:
        raise HTTPException(status_code=400, detail="No valid files provided")
    
    existing_media = db.query(FeedbackMedia).filter(FeedbackMedia.submission_id == announcement_id).all()
    existing_image_count = sum(1 for m in existing_media if m.file_type and m.file_type.startswith('image'))
    
    new_image_files = [f for f in valid_files if is_image_file(f.filename)]
    new_video_files = [f for f in valid_files if is_video_file(f.filename)]
    
    if existing_image_count + len(new_image_files) > 10:
        raise HTTPException(status_code=400, detail=f"Cannot add {len(new_image_files)} images - maximum 10 photos allowed (currently {existing_image_count})")
    
    # DC Protocol: Enforce minimum 3 media after addition for legacy records
    existing_count = len(existing_media)
    if existing_count < 3 and existing_count + len(valid_files) < 3:
        raise HTTPException(status_code=400, detail=f"Minimum 3 media files required. Currently {existing_count}, adding {len(valid_files)}")
    
    for vf in new_video_files:
        temp_path = None
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(vf.filename)[1]) as tmp:
                content = await vf.read()
                tmp.write(content)
                temp_path = tmp.name
            await vf.seek(0)
            
            duration = get_video_duration_seconds(temp_path)
            if duration > 180:
                raise HTTPException(status_code=400, detail=f"Video '{vf.filename}' exceeds 3 minute limit ({int(duration)}s)")
        finally:
            if temp_path and os.path.exists(temp_path):
                os.unlink(temp_path)
    
    added_count = 0
    for file in valid_files:
        try:
            upload_result = await UniversalUploadService.handle_upload(
                file=file,
                table_name='feedback_media',
                record_id=submission.id,
                uploaded_by_id=current_user.id,
                uploaded_by_type='staff',
                storage_dir='feedback_media',
                db=db,
                emp_code=current_user.emp_code,
                allow_videos=True
            )
            
            media_record = FeedbackMedia(
                submission_id=submission.id,
                file_path=upload_result['file_path'],
                file_type=upload_result['file_type'],
                file_size=upload_result['file_size'],
                original_filename=upload_result['original_filename'],
                uploaded_by_emp_code=current_user.emp_code,
                media_status=MediaStatus.APPROVED,
                processing_status='completed',
                original_checksum=upload_result.get('original_checksum'),
                original_storage_type=upload_result.get('storage_type'),
                original_storage_key=upload_result.get('storage_key')
            )
            db.add(media_record)
            added_count += 1
        except Exception as upload_err:
            logger.error(f"[DC-ADD-MEDIA] Upload failed for {file.filename}: {upload_err}")
            raise HTTPException(status_code=500, detail=f"File upload failed: {str(upload_err)}")
    
    submission.approved_media_count = (submission.approved_media_count or 0) + added_count
    
    all_media = db.query(FeedbackMedia).filter(FeedbackMedia.submission_id == announcement_id).all()
    has_images = any(m.file_type and m.file_type.startswith('image') for m in all_media)
    has_videos = any(m.file_type and m.file_type.startswith('video') for m in all_media)
    if has_images and has_videos:
        submission.submission_type = SubmissionType.MIXED
    elif has_videos:
        submission.submission_type = SubmissionType.VIDEO
    elif has_images:
        submission.submission_type = SubmissionType.PHOTO
    
    db.commit()
    
    log_staff_action(
        db=db,
        staff_id=current_user.id,
        staff_emp_code=current_user.emp_code,
        mnr_id=submission.user_id,
        action_type="UPDATE",
        action_details=f"Added {added_count} media files to announcement #{announcement_id}",
        page_accessed="announcements"
    )
    
    return {
        "success": True,
        "message": f"Added {added_count} media files successfully",
        "data": {
            "added_count": added_count,
            "total_media": submission.approved_media_count
        }
    }


@router.get("/allowances/{mnr_id}")
async def get_field_allowances(
    mnr_id: str,
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Get field allowances for member - matches MNR user login view
    DC Protocol (Jan 10, 2026): Uses FieldAllowanceService as single source of truth
    Returns both Standard and Car allowance eligibility, progress, and payment history
    """
    menu_code = "staff_mnr_user_allowances"
    if not check_mnr_user_access(db, current_user, menu_code):
        raise HTTPException(status_code=403, detail="Access denied")
    
    user = validate_mnr_id(db, mnr_id)
    
    from app.services.field_allowance_service import FieldAllowanceService
    from app.models.field_allowance import FieldAllowanceEligibility, CarAllowanceEligibility
    from app.models.transaction import Transaction
    
    allowance_service = FieldAllowanceService()
    status_result = allowance_service.get_user_allowance_status(user.id, db)
    
    field_allowance_payments = db.query(Transaction).filter(
        Transaction.referrer_id == str(user.id),
        Transaction.transaction_type == 'Field Allowance'
    ).order_by(Transaction.timestamp.desc()).limit(50).all()
    
    payment_history = [{
        "id": str(getattr(fa, 'id', '')),
        "amount": float(getattr(fa, 'amount', 0) or 0),
        "timestamp": getattr(fa, 'timestamp', None).isoformat() if getattr(fa, 'timestamp', None) else None,
        "description": str(getattr(fa, 'description', ''))
    } for fa in field_allowance_payments]
    
    total_paid = sum(p['amount'] for p in payment_history)
    
    log_staff_action(
        db=db,
        staff_id=current_user.id,
        staff_emp_code=current_user.emp_code,
        mnr_id=mnr_id,
        action_type="VIEW",
        action_details="Viewed field allowances",
        page_accessed="allowances"
    )
    
    return {
        "success": True,
        "mnr_id": mnr_id,
        "member_info": {"name": user.name, "status": user.account_status},
        "data": {
            "allowance_status": status_result.get("data", {}),
            "payment_history": payment_history,
            "total_paid": total_paid
        }
    }


@router.get("/coupons/red/{mnr_id}")
async def get_red_coupons(
    mnr_id: str,
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Get red coupons for member"""
    menu_code = "staff_mnr_user_coupons_red"
    if not check_mnr_user_access(db, current_user, menu_code):
        raise HTTPException(status_code=403, detail="Access denied")
    
    user = validate_mnr_id(db, mnr_id)
    
    from app.models.red_coupon import RedCouponApproval
    
    coupons = db.query(RedCouponApproval).filter(RedCouponApproval.user_id == mnr_id).all()
    
    coupon_list = [{
        "id": c.id,
        "coupon_code": getattr(c, 'coupon_code', f"RC-{c.id}"),
        "status": c.status,
        "value": float(getattr(c, 'amount', 0)),
        "created_at": c.created_at.isoformat() if c.created_at else None
    } for c in coupons]
    
    log_staff_action(
        db=db,
        staff_id=current_user.id,
        staff_emp_code=current_user.emp_code,
        mnr_id=mnr_id,
        action_type="VIEW",
        action_details="Viewed red coupons",
        page_accessed="coupons/red"
    )
    
    return {
        "success": True,
        "mnr_id": mnr_id,
        "member_info": {"name": user.name, "status": user.account_status},
        "data": {"coupons": coupon_list, "total": len(coupon_list)}
    }


@router.get("/coupons/green/{mnr_id}")
async def get_green_coupons(
    mnr_id: str,
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Get green coupons for member"""
    menu_code = "staff_mnr_user_coupons_green"
    if not check_mnr_user_access(db, current_user, menu_code):
        raise HTTPException(status_code=403, detail="Access denied")
    
    user = validate_mnr_id(db, mnr_id)
    
    from app.models.coupon import EnhancedCoupon
    
    coupons = db.query(EnhancedCoupon).filter(EnhancedCoupon.owner_id == mnr_id).all()
    
    coupon_list = [{
        "id": c.id,
        "coupon_code": getattr(c, 'coupon_code', f"GC-{c.id}"),
        "status": c.status,
        "value": float(getattr(c, 'package_points', 0)),
        "created_at": c.created_at.isoformat() if c.created_at else None
    } for c in coupons]
    
    log_staff_action(
        db=db,
        staff_id=current_user.id,
        staff_emp_code=current_user.emp_code,
        mnr_id=mnr_id,
        action_type="VIEW",
        action_details="Viewed green coupons",
        page_accessed="coupons/green"
    )
    
    return {
        "success": True,
        "mnr_id": mnr_id,
        "member_info": {"name": user.name, "status": user.account_status},
        "data": {"coupons": coupon_list, "total": len(coupon_list)}
    }


@router.get("/coupons/ev/{mnr_id}")
async def get_ev_coupons(
    mnr_id: str,
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Get EV discount coupons for member"""
    menu_code = "staff_mnr_user_coupons_ev"
    if not check_mnr_user_access(db, current_user, menu_code):
        raise HTTPException(status_code=403, detail="Access denied")
    
    user = validate_mnr_id(db, mnr_id)
    
    from app.models.ev_coupon_claim import EVCouponClaim
    
    coupons = db.query(EVCouponClaim).filter(EVCouponClaim.user_id == mnr_id).all()
    
    coupon_list = [{
        "id": c.id,
        "coupon_code": getattr(c, 'coupon_code', f"EV-{c.id}"),
        "status": c.status,
        "discount_percentage": float(getattr(c, 'discount_percentage', 0)),
        "benefit_type": getattr(c, 'benefit_type', None),
        "created_at": c.created_at.isoformat() if c.created_at else None
    } for c in coupons]
    
    log_staff_action(
        db=db,
        staff_id=current_user.id,
        staff_emp_code=current_user.emp_code,
        mnr_id=mnr_id,
        action_type="VIEW",
        action_details="Viewed EV discount coupons",
        page_accessed="coupons/ev"
    )
    
    return {
        "success": True,
        "mnr_id": mnr_id,
        "member_info": {"name": user.name, "status": user.account_status},
        "data": {"coupons": coupon_list, "total": len(coupon_list)}
    }


@router.get("/mnr/points/{mnr_id}")
async def get_mnr_points(
    mnr_id: str,
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Get MNR points for member - queries MNRPointsBalance for 15000 point allocations"""
    menu_code = "staff_mnr_user_mnr_points"
    if not check_mnr_user_access(db, current_user, menu_code):
        raise HTTPException(status_code=403, detail="Access denied")
    
    user = validate_mnr_id(db, mnr_id)
    
    from app.models.myntreal_incentive import MNRPointsBalance
    
    balance = db.query(MNRPointsBalance).filter(
        MNRPointsBalance.user_id == mnr_id
    ).first()
    
    total_points = float(balance.initial_points) if balance else 0
    used_points = float(balance.total_consumed) if balance else 0
    available_points = float(balance.current_balance) if balance else 0
    
    log_staff_action(
        db=db,
        staff_id=current_user.id,
        staff_emp_code=current_user.emp_code,
        mnr_id=mnr_id,
        action_type="VIEW",
        action_details="Viewed MNR points",
        page_accessed="mnr/points"
    )
    
    return {
        "success": True,
        "mnr_id": mnr_id,
        "member_info": {"name": user.name, "status": user.account_status},
        "data": {
            "total_points": total_points,
            "used_points": used_points,
            "available_points": available_points,
            "receipt_no": balance.receipt_no if balance else None,
            "expiry_date": balance.expiry_date.isoformat() if balance and balance.expiry_date else None
        }
    }


@router.get("/mnr/benefits/{mnr_id}")
async def get_ev_benefits(
    mnr_id: str,
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Get EV benefits for member"""
    menu_code = "staff_mnr_user_mnr_benefits"
    if not check_mnr_user_access(db, current_user, menu_code):
        raise HTTPException(status_code=403, detail="Access denied")
    
    user = validate_mnr_id(db, mnr_id)
    
    from app.models.ev_discount import CouponBenefit
    
    claims = db.query(CouponBenefit).filter(
        CouponBenefit.user_id == mnr_id
    ).order_by(desc(CouponBenefit.applied_date)).all()
    
    claims_list = [{
        "id": c.id,
        "benefit_type": c.benefit_type,
        "benefit_number": c.ev_coupon_id,
        "amount": float(c.discount_amount or c.cashback_amount or 0),
        "status": c.status,
        "created_at": c.applied_date.isoformat() if c.applied_date else None
    } for c in claims]
    
    log_staff_action(
        db=db,
        staff_id=current_user.id,
        staff_emp_code=current_user.emp_code,
        mnr_id=mnr_id,
        action_type="VIEW",
        action_details="Viewed EV benefits",
        page_accessed="mnr/benefits"
    )
    
    return {
        "success": True,
        "mnr_id": mnr_id,
        "member_info": {"name": user.name, "status": user.account_status},
        "data": {"claims": claims_list, "total": len(claims_list)}
    }


@router.get("/mnr/wallet/{mnr_id}")
async def get_wallet_overview(
    mnr_id: str,
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Get complete wallet overview for member"""
    menu_code = "staff_mnr_user_mnr_wallet"
    if not check_mnr_user_access(db, current_user, menu_code):
        raise HTTPException(status_code=403, detail="Access denied")
    
    user = validate_mnr_id(db, mnr_id)
    
    from app.models.withdrawal import WithdrawalRequest
    from app.models.transaction import PendingIncome
    
    total_withdrawn_result = db.query(func.sum(WithdrawalRequest.final_payout)).filter(
        WithdrawalRequest.user_id == mnr_id,
        WithdrawalRequest.status.in_(['Paid', 'Completed'])
    ).scalar() or 0
    
    recent_withdrawals = db.query(WithdrawalRequest).filter(
        WithdrawalRequest.user_id == mnr_id
    ).order_by(desc(WithdrawalRequest.created_at)).limit(25).all()
    
    recent_earnings = db.query(PendingIncome).filter(
        PendingIncome.user_id == mnr_id,
        PendingIncome.verification_status == 'Completed'
    ).order_by(desc(PendingIncome.created_at)).limit(25).all()
    
    transactions_list = []
    for w in recent_withdrawals:
        transactions_list.append({
            "id": w.id,
            "transaction_type": "withdrawal",
            "wallet_type": "withdrawable",
            "amount": float(w.withdrawal_amount or 0),
            "final_payout": float(w.final_payout or 0),
            "status": w.status,
            "created_at": w.created_at.isoformat() if w.created_at else None
        })
    for e in recent_earnings:
        transactions_list.append({
            "id": e.id,
            "transaction_type": "credit",
            "wallet_type": "earning",
            "income_type": e.income_type,
            "amount": float(e.net_amount or 0),
            "status": e.verification_status,
            "created_at": e.created_at.isoformat() if e.created_at else None
        })
    transactions_list.sort(key=lambda x: x.get('created_at') or '', reverse=True)
    transactions_list = transactions_list[:50]
    
    log_staff_action(
        db=db,
        staff_id=current_user.id,
        staff_emp_code=current_user.emp_code,
        mnr_id=mnr_id,
        action_type="VIEW",
        action_details="Viewed wallet overview",
        page_accessed="mnr/wallet"
    )
    
    return {
        "success": True,
        "mnr_id": mnr_id,
        "member_info": {"name": user.name, "status": user.account_status},
        "data": {
            "wallet": {
                "earning_wallet": float(user.earning_wallet or 0),
                "withdrawable_wallet": float(user.withdrawable_wallet or 0),
                "upgrade_wallet": float(user.upgrade_wallet_balance or 0),
                "total_withdrawn": float(total_withdrawn_result)
            },
            "recent_transactions": transactions_list
        }
    }


@router.get("/myntreal/leads/{mnr_id}")
async def get_myntreal_leads(
    mnr_id: str,
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Get MyntReal leads for member"""
    menu_code = "staff_mnr_user_myntreal_leads"
    if not check_mnr_user_access(db, current_user, menu_code):
        raise HTTPException(status_code=403, detail="Access denied")
    
    user = validate_mnr_id(db, mnr_id)
    
    from app.models.crm import CRMLead
    
    # DC Protocol (Jan 10, 2026): Fixed - use mnr_handler_id instead of non-existent referred_by
    leads = db.query(CRMLead).filter(
        CRMLead.mnr_handler_id == mnr_id
    ).order_by(desc(CRMLead.created_at)).all()
    
    leads_list = [{
        "id": l.id,
        "lead_name": getattr(l, 'name', None),
        "mobile": getattr(l, 'mobile', None),
        "category": getattr(l, 'category', None),
        "status": l.status,
        "created_at": l.created_at.isoformat() if l.created_at else None
    } for l in leads]
    
    log_staff_action(
        db=db,
        staff_id=current_user.id,
        staff_emp_code=current_user.emp_code,
        mnr_id=mnr_id,
        action_type="VIEW",
        action_details="Viewed MyntReal leads",
        page_accessed="myntreal/leads"
    )
    
    return {
        "success": True,
        "mnr_id": mnr_id,
        "member_info": {"name": user.name, "status": user.account_status},
        "data": {"leads": leads_list, "total": len(leads_list)}
    }


@router.get("/myntreal/franchise/{mnr_id}")
async def get_franchise_status(
    mnr_id: str,
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Get franchise status for member"""
    menu_code = "staff_mnr_user_myntreal_franchise"
    if not check_mnr_user_access(db, current_user, menu_code):
        raise HTTPException(status_code=403, detail="Access denied")
    
    user = validate_mnr_id(db, mnr_id)
    
    franchise_status = {
        "is_franchise": getattr(user, 'is_franchise', False),
        "franchise_type": getattr(user, 'franchise_type', None),
        "franchise_since": getattr(user, 'franchise_since', None),
        "franchise_zone": getattr(user, 'franchise_zone', None)
    }
    
    log_staff_action(
        db=db,
        staff_id=current_user.id,
        staff_emp_code=current_user.emp_code,
        mnr_id=mnr_id,
        action_type="VIEW",
        action_details="Viewed franchise status",
        page_accessed="myntreal/franchise"
    )
    
    return {
        "success": True,
        "mnr_id": mnr_id,
        "member_info": {"name": user.name, "status": user.account_status},
        "data": {"franchise": franchise_status}
    }


@router.get("/zynova/real-estate/{mnr_id}")
async def get_zynova_real_estate(
    mnr_id: str,
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Get VGK4U Real Estate segment status for member"""
    menu_code = "staff_mnr_user_zynova_realestate"
    if not check_mnr_user_access(db, current_user, menu_code):
        raise HTTPException(status_code=403, detail="Access denied")
    
    user = validate_mnr_id(db, mnr_id)
    
    from app.models.myntreal_incentive import ZynovaRealEstateProfile
    
    profile = db.query(ZynovaRealEstateProfile).filter(
        ZynovaRealEstateProfile.user_id == mnr_id
    ).first()
    
    profile_data = None
    if profile:
        profile_data = {
            "id": profile.id,
            "status": profile.status,
            "tier": getattr(profile, 'tier', None),
            "properties_count": getattr(profile, 'properties_count', 0),
            "total_commission": float(getattr(profile, 'total_commission', 0)),
            "created_at": profile.created_at.isoformat() if profile.created_at else None
        }
    
    log_staff_action(
        db=db,
        staff_id=current_user.id,
        staff_emp_code=current_user.emp_code,
        mnr_id=mnr_id,
        action_type="VIEW",
        action_details="Viewed VGK4U Real Estate status",
        page_accessed="zynova/real-estate"
    )
    
    return {
        "success": True,
        "mnr_id": mnr_id,
        "member_info": {"name": user.name, "status": user.account_status},
        "data": {"real_estate": profile_data}
    }


@router.get("/zynova/insurance/{mnr_id}")
async def get_zynova_insurance(
    mnr_id: str,
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Get VGK4U Insurance segment status for member"""
    menu_code = "staff_mnr_user_zynova_insurance"
    if not check_mnr_user_access(db, current_user, menu_code):
        raise HTTPException(status_code=403, detail="Access denied")
    
    user = validate_mnr_id(db, mnr_id)
    
    from app.models.myntreal_incentive import ZynovaInsuranceProfile
    
    profile = db.query(ZynovaInsuranceProfile).filter(
        ZynovaInsuranceProfile.user_id == mnr_id
    ).first()
    
    profile_data = None
    if profile:
        profile_data = {
            "id": profile.id,
            "status": profile.status,
            "tier": getattr(profile, 'tier', None),
            "policies_count": getattr(profile, 'policies_count', 0),
            "total_commission": float(getattr(profile, 'total_commission', 0)),
            "created_at": profile.created_at.isoformat() if profile.created_at else None
        }
    
    log_staff_action(
        db=db,
        staff_id=current_user.id,
        staff_emp_code=current_user.emp_code,
        mnr_id=mnr_id,
        action_type="VIEW",
        action_details="Viewed VGK4U Insurance status",
        page_accessed="zynova/insurance"
    )
    
    return {
        "success": True,
        "mnr_id": mnr_id,
        "member_info": {"name": user.name, "status": user.account_status},
        "data": {"insurance": profile_data}
    }


@router.get("/zynova/training/{mnr_id}")
async def get_zynova_training(
    mnr_id: str,
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Get VGK4U Training status for member"""
    menu_code = "staff_mnr_user_zynova_training"
    if not check_mnr_user_access(db, current_user, menu_code):
        raise HTTPException(status_code=403, detail="Access denied")
    
    user = validate_mnr_id(db, mnr_id)
    
    from app.models.training import TrainingEnrollment
    
    enrollments = db.query(TrainingEnrollment).filter(
        TrainingEnrollment.user_id == mnr_id
    ).order_by(desc(TrainingEnrollment.created_at)).all()
    
    training_list = [{
        "id": e.id,
        "course_name": getattr(e, 'course_name', None),
        "status": e.status,
        "completion_percentage": float(getattr(e, 'completion_percentage', 0)),
        "enrolled_at": e.created_at.isoformat() if e.created_at else None
    } for e in enrollments]
    
    log_staff_action(
        db=db,
        staff_id=current_user.id,
        staff_emp_code=current_user.emp_code,
        mnr_id=mnr_id,
        action_type="VIEW",
        action_details="Viewed VGK4U Training status",
        page_accessed="zynova/training"
    )
    
    return {
        "success": True,
        "mnr_id": mnr_id,
        "member_info": {"name": user.name, "status": user.account_status},
        "data": {"trainings": training_list, "total": len(training_list)}
    }


@router.get("/awards/bonanza/{mnr_id}")
async def get_bonanza_status(
    mnr_id: str,
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Get bonanza status for member"""
    menu_code = "staff_mnr_user_awards_bonanza"
    if not check_mnr_user_access(db, current_user, menu_code):
        raise HTTPException(status_code=403, detail="Access denied")
    
    user = validate_mnr_id(db, mnr_id)
    
    from app.models.bonanza import BonanzaProgress, DynamicBonanza
    
    progress_records = db.query(BonanzaProgress).filter(
        BonanzaProgress.user_id == mnr_id
    ).order_by(desc(BonanzaProgress.created_at)).all()
    
    qual_list = [{
        "id": p.id,
        "bonanza_name": getattr(p, 'bonanza_name', 'Bonanza'),
        "qualified_at": p.created_at.isoformat() if p.created_at else None,
        "progress_percentage": float(getattr(p, 'progress_percentage', 0))
    } for p in progress_records]
    
    claims_list = [{
        "id": p.id,
        "bonanza_name": getattr(p, 'bonanza_name', 'Bonanza'),
        "status": getattr(p, 'status', 'in_progress'),
        "claimed_at": p.updated_at.isoformat() if getattr(p, 'updated_at', None) else None
    } for p in progress_records if getattr(p, 'status', '') == 'claimed']
    
    log_staff_action(
        db=db,
        staff_id=current_user.id,
        staff_emp_code=current_user.emp_code,
        mnr_id=mnr_id,
        action_type="VIEW",
        action_details="Viewed bonanza status",
        page_accessed="awards/bonanza"
    )
    
    return {
        "success": True,
        "mnr_id": mnr_id,
        "member_info": {"name": user.name, "status": user.account_status},
        "data": {
            "qualifications": qual_list,
            "claims": claims_list,
            "total_qualifications": len(qual_list),
            "total_claims": len(claims_list)
        }
    }


# DC Protocol (Jan 10, 2026): Removed duplicate @router.get("/awards/{mnr_id}") - get_awards_unified
# The comprehensive endpoint get_member_awards at line ~2993 handles all tabs: direct, matching, bonanza


@router.get("/coupons/{mnr_id}")
async def get_coupons_unified(
    mnr_id: str,
    tab: str = Query("purchased", description="Tab: purchased, usage, transfers, activate, buy"),
    status_filter: Optional[str] = Query(None, description="Filter by status"),
    package_filter: Optional[str] = Query(None, description="Filter by package type"),
    direction_filter: Optional[str] = Query(None, description="Filter transfers: in, out, all"),
    date_from: Optional[str] = Query(None, description="Date filter from (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="Date filter to (YYYY-MM-DD)"),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Unified coupons endpoint - DC Protocol (Jan 10, 2026)
    Tabs: purchased, usage, transfers, activate, buy (matches regular user format)
    """
    if tab == "purchased":
        return await get_purchased_coupons(
            mnr_id=mnr_id, status_filter=status_filter, package_filter=package_filter,
            date_from=date_from, date_to=date_to, page=page, per_page=per_page,
            current_user=current_user, db=db
        )
    elif tab == "usage":
        return await get_coupon_usage_status(
            mnr_id=mnr_id, status_filter=status_filter, package_filter=package_filter,
            date_from=date_from, date_to=date_to, page=page, per_page=per_page,
            current_user=current_user, db=db
        )
    elif tab == "transfers":
        return await get_coupon_transfers(
            mnr_id=mnr_id, direction_filter=direction_filter, status_filter=status_filter,
            package_filter=package_filter, date_from=date_from, date_to=date_to,
            page=page, per_page=per_page, current_user=current_user, db=db
        )
    elif tab == "activate":
        return await get_activate_coupon_data(
            mnr_id=mnr_id, current_user=current_user, db=db
        )
    elif tab == "buy":
        return await get_buy_coupon_data(
            mnr_id=mnr_id, current_user=current_user, db=db
        )
    elif tab == "green":
        return await get_green_coupons(mnr_id=mnr_id, current_user=current_user, db=db)
    elif tab == "ev":
        return await get_ev_coupons(mnr_id=mnr_id, current_user=current_user, db=db)
    return await get_red_coupons(mnr_id=mnr_id, current_user=current_user, db=db)


@router.get("/mnr/{mnr_id}")
async def get_mnr_unified(
    mnr_id: str,
    tab: str = Query("earnings", description="Tab: earnings, direct, matching, ved, guru, withdrawals, points, benefits, wallet"),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Unified MNR endpoint - routes to appropriate sub-endpoint based on tab"""
    if tab == "withdrawals":
        return await get_withdrawals(mnr_id=mnr_id, page=page, per_page=per_page, current_user=current_user, db=db)
    elif tab == "points":
        return await get_mnr_points(mnr_id=mnr_id, current_user=current_user, db=db)
    elif tab == "benefits":
        return await get_ev_benefits(mnr_id=mnr_id, current_user=current_user, db=db)
    elif tab == "wallet":
        return await get_wallet_overview(mnr_id=mnr_id, current_user=current_user, db=db)
    elif tab in ("direct", "matching", "ved", "guru"):
        return await get_income_transactions(mnr_id=mnr_id, income_type=tab, page=page, per_page=per_page, current_user=current_user, db=db)
    return await get_earnings_summary(mnr_id=mnr_id, current_user=current_user, db=db)


@router.get("/myntreal/{mnr_id}")
async def get_myntreal_unified(
    mnr_id: str,
    tab: str = Query("properties", description="Tab: properties, earnings, leads, franchise"),
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Unified MyntReal endpoint - routes to appropriate data based on tab
    DC Protocol (Jan 10, 2026): Consolidated MNR User MyntReal page
    - properties: Real estate property referrals from CRM leads
    - earnings: Incentive earnings from MNRIncentive table
    - leads: CRM leads (legacy)
    - franchise: Franchise status (legacy)
    """
    menu_code = "staff_mnr_user_myntreal"
    if not check_mnr_user_access(db, current_user, menu_code):
        raise HTTPException(status_code=403, detail="Access denied")
    
    user = validate_mnr_id(db, mnr_id)
    
    if tab == "properties":
        # Get property referrals from CRM leads (real estate category)
        # DC Protocol (Jan 10, 2026): Fixed - use mnr_handler_id instead of non-existent referred_by
        from app.models.crm import CRMLead
        from app.models.signup_category import SignupCategory
        from app.utils.category_slug_monitor import get_real_estate_slugs
        
        # Get real estate category IDs using centralized slug list
        re_categories = db.query(SignupCategory.id).filter(
            SignupCategory.slug.in_(get_real_estate_slugs())
        ).all()
        re_category_ids = [c.id for c in re_categories]
        
        property_leads = db.query(CRMLead).filter(
            CRMLead.mnr_handler_id == mnr_id,
            CRMLead.category_id.in_(re_category_ids) if re_category_ids else True
        ).order_by(desc(CRMLead.created_at)).all()
        
        properties = [{
            "id": l.id,
            "name": getattr(l, 'name', 'N/A'),
            "mobile": getattr(l, 'mobile', None),
            "category": getattr(l, 'category', None),
            "status": l.status,
            "created_at": l.created_at.isoformat() if l.created_at else None
        } for l in property_leads]
        
        log_staff_action(
            db=db, staff_id=current_user.id, staff_emp_code=current_user.emp_code,
            mnr_id=mnr_id, action_type="VIEW", action_details="Viewed MyntReal properties",
            page_accessed="myntreal/properties"
        )
        
        return {
            "success": True,
            "mnr_id": mnr_id,
            "member_info": {"name": user.name, "status": user.account_status},
            "data": {"properties": properties, "total": len(properties)}
        }
    
    elif tab == "earnings":
        # Get earnings from MyntRealIncentive table
        # DC Protocol (Jan 10, 2026): Fixed - correct import name MyntRealIncentive
        from app.models.myntreal_incentive import MyntRealIncentive
        
        incentives = db.query(MyntRealIncentive).filter(
            MyntRealIncentive.mnr_id == mnr_id
        ).order_by(desc(MyntRealIncentive.created_at)).all()
        
        total_earnings = sum(float(i.mnr_amount or 0) for i in incentives if i.status == 'approved')
        pending_earnings = sum(float(i.mnr_amount or 0) for i in incentives if i.status in ('pending', 'draft'))
        
        earnings_list = [{
            "id": i.id,
            "lead_id": i.lead_id,
            "revenue_amount": float(i.revenue_amount or 0),
            "mnr_amount": float(i.mnr_amount or 0),
            "status": i.status,
            "created_at": i.created_at.isoformat() if i.created_at else None,
            "approved_at": i.approved_at.isoformat() if i.approved_at else None
        } for i in incentives]
        
        log_staff_action(
            db=db, staff_id=current_user.id, staff_emp_code=current_user.emp_code,
            mnr_id=mnr_id, action_type="VIEW", action_details="Viewed MyntReal earnings",
            page_accessed="myntreal/earnings"
        )
        
        return {
            "success": True,
            "mnr_id": mnr_id,
            "member_info": {"name": user.name, "status": user.account_status},
            "data": {
                "earnings": earnings_list,
                "total_earnings": total_earnings,
                "pending_earnings": pending_earnings,
                "total_records": len(earnings_list)
            }
        }
    
    elif tab == "franchise":
        return await get_franchise_status(mnr_id=mnr_id, current_user=current_user, db=db)
    
    # Default: leads
    return await get_myntreal_leads(mnr_id=mnr_id, current_user=current_user, db=db)


# ==================== NEW COUPONS ENDPOINTS (DC Protocol Jan 10, 2026) ====================

class StaffCouponTransferRequest(BaseModel):
    """Request schema for staff-initiated coupon transfer"""
    to_user_id: str = Field(..., description="Target MNR ID to transfer coupon to")
    coupon_id: int = Field(..., description="Coupon ID to transfer")
    transfer_reason: str = Field(..., min_length=5, description="Reason for transfer (required)")


class StaffCouponPurchaseRequest(BaseModel):
    """
    Request schema for staff-initiated coupon purchase on behalf of MNR user
    DC Protocol (Jan 10, 2026)
    """
    package_type: str = Field(..., description="Package: PLATINUM, DIAMOND, BLUE, LOYAL, WELCOME")
    quantity: int = Field(1, ge=1, le=10, description="Quantity (1-10)")
    funding_source: str = Field(..., description="wallet, offline, or welcome")
    payment_method: Optional[str] = Field(None, description="Payment method (for offline)")
    transaction_id: Optional[str] = Field(None, description="Transaction reference (for offline)")
    amount_paid: Optional[float] = Field(None, description="Amount paid (for offline)")
    remarks: Optional[str] = Field(None, description="Staff remarks/notes")


class StaffCouponActivateRequest(BaseModel):
    """
    Request schema for staff-initiated coupon activation
    DC Protocol (Jan 10, 2026) - Matches regular user module format
    Enhanced: Added new_phone_number for staff to update mobile before activation
    """
    coupon_id: int = Field(..., description="Coupon ID to activate (BigInteger in database)")
    target_user_id: Optional[str] = Field(None, description="Target MNR ID (if activating for another user)")
    new_phone_number: Optional[str] = Field(None, description="New phone number to update before activation (solves mobile uniqueness conflicts)")


async def get_purchased_coupons(
    mnr_id: str,
    status_filter: Optional[str],
    package_filter: Optional[str],
    date_from: Optional[str],
    date_to: Optional[str],
    page: int,
    per_page: int,
    current_user: StaffEmployee,
    db: Session
) -> Dict[str, Any]:
    """
    Tab 1: Purchased Coupons - Get coupons purchased by user via PINPurchaseRequest
    DC Protocol (Jan 10, 2026)
    """
    menu_code = "staff_mnr_user_coupons"
    if not check_mnr_user_access(db, current_user, menu_code):
        raise HTTPException(status_code=403, detail="Access denied")
    
    user = validate_mnr_id(db, mnr_id)
    
    from app.models.coupon import PINPurchaseRequest
    
    query = db.query(PINPurchaseRequest).filter(PINPurchaseRequest.user_id == mnr_id)
    
    # Apply filters
    if status_filter:
        query = query.filter(PINPurchaseRequest.status == status_filter)
    if package_filter:
        query = query.filter(PINPurchaseRequest.package_type == package_filter)
    if date_from:
        try:
            from_date = datetime.strptime(date_from, "%Y-%m-%d")
            query = query.filter(PINPurchaseRequest.request_date >= from_date)
        except ValueError:
            pass
    if date_to:
        try:
            to_date = datetime.strptime(date_to, "%Y-%m-%d")
            query = query.filter(PINPurchaseRequest.request_date <= to_date)
        except ValueError:
            pass
    
    total = query.count()
    purchases = query.order_by(desc(PINPurchaseRequest.request_date)).offset((page - 1) * per_page).limit(per_page).all()
    
    purchase_list = [{
        "id": p.id,
        "package_type": p.package_type,
        "package_value": float(p.package_value) if p.package_value else 0,
        "quantity": p.quantity,
        "total_amount": float(p.total_amount) if p.total_amount else 0,
        "payment_method": p.payment_method,
        "transaction_id": p.transaction_id,
        "status": p.status,
        "request_date": p.request_date.isoformat() if p.request_date else None,
        "superadmin_approved_date": p.superadmin_approved_date.isoformat() if p.superadmin_approved_date else None,
        "finance_validated_date": p.finance_validated_date.isoformat() if p.finance_validated_date else None,
        "completed_date": p.completed_date.isoformat() if p.completed_date else None,
        "rejection_reason": p.rejection_reason,
        "superadmin_approved_by": p.superadmin_approved_by,
        "finance_validated_by": p.finance_validated_by,
        "payment_details": p.payment_details,
        "superadmin_notes": p.superadmin_notes,
    } for p in purchases]
    
    # Summary stats
    all_purchases = db.query(PINPurchaseRequest).filter(PINPurchaseRequest.user_id == mnr_id).all()
    summary = {
        "total_requests": len(all_purchases),
        "pending": len([p for p in all_purchases if p.status == 'Pending']),
        "approved": len([p for p in all_purchases if p.status == 'Approved']),
        "fulfilled": len([p for p in all_purchases if p.status == 'Fulfilled']),
        "rejected": len([p for p in all_purchases if p.status == 'Rejected']),
        "total_value": sum(float(p.total_amount or 0) for p in all_purchases if p.status == 'Fulfilled')
    }
    
    log_staff_action(
        db=db, staff_id=current_user.id, staff_emp_code=current_user.emp_code,
        mnr_id=mnr_id, action_type="VIEW", action_details="Viewed purchased coupons",
        page_accessed="coupons/purchased"
    )
    
    return {
        "success": True,
        "mnr_id": mnr_id,
        "member_info": {"name": user.name, "status": user.account_status},
        "summary": summary,
        "data": {
            "purchases": purchase_list,
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": total,
                "total_pages": (total + per_page - 1) // per_page
            }
        }
    }


async def get_coupon_usage_status(
    mnr_id: str,
    status_filter: Optional[str],
    package_filter: Optional[str],
    date_from: Optional[str],
    date_to: Optional[str],
    page: int,
    per_page: int,
    current_user: StaffEmployee,
    db: Session
) -> Dict[str, Any]:
    """
    Tab 2: Usage Status - Get coupon usage status with "used by whom" information
    DC Protocol (Jan 10, 2026)
    Shows which downline member received each coupon for activation
    """
    menu_code = "staff_mnr_user_coupons"
    if not check_mnr_user_access(db, current_user, menu_code):
        raise HTTPException(status_code=403, detail="Access denied")
    
    user = validate_mnr_id(db, mnr_id)
    
    from app.models.coupon import Coupon
    from app.models.user import User
    
    query = db.query(Coupon).filter(Coupon.owner_id == mnr_id)
    
    if status_filter:
        query = query.filter(Coupon.status == status_filter)
    if package_filter:
        query = query.filter(Coupon.coupon_type == package_filter)
    if date_from:
        try:
            from_date = datetime.strptime(date_from, "%Y-%m-%d")
            query = query.filter(Coupon.activated_at >= from_date)
        except ValueError:
            pass
    if date_to:
        try:
            to_date = datetime.strptime(date_to, "%Y-%m-%d")
            query = query.filter(Coupon.activated_at <= to_date)
        except ValueError:
            pass
    
    total = query.count()
    from sqlalchemy import case, func as sa_func
    sort_date = case(
        (Coupon.assignment_status_changed_at.isnot(None), Coupon.assignment_status_changed_at),
        else_=Coupon.activated_at
    )
    coupons = query.order_by(desc(sort_date), desc(Coupon.id)).offset((page - 1) * per_page).limit(per_page).all()
    
    used_by_ids = [c.used_by for c in coupons if c.used_by]
    used_by_users = {}
    if used_by_ids:
        users_list = db.query(User.id, User.name, User.activation_date).filter(User.id.in_(used_by_ids)).all()
        used_by_users = {u.id: {"mnr_id": u.id, "name": u.name, "activation_date": u.activation_date.isoformat() if u.activation_date else None} for u in users_list}
    
    # Look up staff activation logs for coupons in this batch
    coupon_ids_on_page = [c.id for c in coupons]
    from app.models.staff import StaffMnrUserAuditLog
    activation_logs = db.query(StaffMnrUserAuditLog).filter(
        StaffMnrUserAuditLog.mnr_user_id == mnr_id,
        StaffMnrUserAuditLog.action_type == 'ACTIVATION'
    ).all()
    # Build map: coupon_id -> {staff_emp_code, created_at}
    coupon_activation_staff = {}
    for log in activation_logs:
        details = log.action_details or ''
        for cid in coupon_ids_on_page:
            if str(cid) in details and cid not in coupon_activation_staff:
                coupon_activation_staff[cid] = {
                    "staff_emp_code": log.staff_emp_code,
                    "activated_on": log.created_at.isoformat() if log.created_at else None
                }

    coupon_list = []
    for c in coupons:
        used_by_data = used_by_users.get(c.used_by) if c.used_by else None
        gen_date = c.assignment_status_changed_at or c.activated_at
        coupon_list.append({
            "id": c.id,
            "coupon_type": c.coupon_type,
            "status": c.status,
            "assignment_status": c.assignment_status,
            "activated_at": c.activated_at.isoformat() if c.activated_at else None,
            "generation_date": gen_date.isoformat() if gen_date else None,
            "used_by": used_by_data,
            "activated_by_staff": coupon_activation_staff.get(c.id)
        })
    
    # Summary stats
    all_coupons = db.query(Coupon).filter(Coupon.owner_id == mnr_id).all()
    summary = {
        "total_coupons": len(all_coupons),
        "available": len([c for c in all_coupons if c.status in ('Available', 'Unused', 'Active')]),
        "used": len([c for c in all_coupons if c.status in ('Used', 'Activated')]),
        "transferred": len([c for c in all_coupons if c.status == 'Transferred']),
        "expired": len([c for c in all_coupons if c.status == 'Expired'])
    }
    
    log_staff_action(
        db=db, staff_id=current_user.id, staff_emp_code=current_user.emp_code,
        mnr_id=mnr_id, action_type="VIEW", action_details="Viewed coupon usage status",
        page_accessed="coupons/usage"
    )
    
    return {
        "success": True,
        "mnr_id": mnr_id,
        "member_info": {"name": user.name, "status": user.account_status},
        "summary": summary,
        "data": {
            "coupons": coupon_list,
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": total,
                "total_pages": (total + per_page - 1) // per_page
            }
        }
    }


async def get_coupon_transfers(
    mnr_id: str,
    direction_filter: Optional[str],
    status_filter: Optional[str],
    package_filter: Optional[str],
    date_from: Optional[str],
    date_to: Optional[str],
    page: int,
    per_page: int,
    current_user: StaffEmployee,
    db: Session
) -> Dict[str, Any]:
    """
    Tab 3: Transfers - Get incoming/outgoing transfer history
    DC Protocol (Jan 10, 2026)
    """
    menu_code = "staff_mnr_user_coupons"
    if not check_mnr_user_access(db, current_user, menu_code):
        raise HTTPException(status_code=403, detail="Access denied")
    
    user = validate_mnr_id(db, mnr_id)
    
    from app.models.coupon_transfer import CouponTransfer
    from app.models.coupon import Coupon
    
    # Build query based on direction
    if direction_filter == "in":
        query = db.query(CouponTransfer).filter(CouponTransfer.to_user_id == mnr_id)
    elif direction_filter == "out":
        query = db.query(CouponTransfer).filter(CouponTransfer.from_user_id == mnr_id)
    else:  # all
        query = db.query(CouponTransfer).filter(
            or_(CouponTransfer.from_user_id == mnr_id, CouponTransfer.to_user_id == mnr_id)
        )
    
    # Apply filters
    if status_filter:
        query = query.filter(CouponTransfer.status == status_filter)
    if package_filter:
        query = query.filter(CouponTransfer.package_type == package_filter)
    if date_from:
        try:
            from_date = datetime.strptime(date_from, "%Y-%m-%d")
            query = query.filter(CouponTransfer.transfer_date >= from_date)
        except ValueError:
            pass
    if date_to:
        try:
            to_date = datetime.strptime(date_to, "%Y-%m-%d")
            query = query.filter(CouponTransfer.transfer_date <= to_date)
        except ValueError:
            pass
    
    total = query.count()
    transfers = query.order_by(desc(CouponTransfer.transfer_date)).offset((page - 1) * per_page).limit(per_page).all()
    
    transfer_list = []
    for t in transfers:
        # Get user names
        from_user = db.query(User).filter(User.id == t.from_user_id).first()
        to_user = db.query(User).filter(User.id == t.to_user_id).first()
        initiated_by = db.query(User).filter(User.id == t.initiated_by_id).first() if t.initiated_by_id else None
        
        transfer_list.append({
            "id": t.id,
            "direction": "in" if t.to_user_id == mnr_id else "out",
            "from_user": {"mnr_id": t.from_user_id, "name": from_user.name if from_user else "Unknown"},
            "to_user": {"mnr_id": t.to_user_id, "name": to_user.name if to_user else "Unknown"},
            "package_type": t.package_type,
            "coupon_id": t.coupon_id or t.enhanced_coupon_id,
            "transfer_type": t.transfer_type,
            "status": t.status,
            "transfer_date": t.transfer_date.isoformat() if t.transfer_date else None,
            "completed_at": t.completed_at.isoformat() if t.completed_at else None,
            "transfer_reason": t.transfer_reason,
            "initiated_by": {"id": t.initiated_by_id, "name": initiated_by.name if initiated_by else "System"} if t.initiated_by_id else None,
            "rejection_reason": t.rejection_reason
        })
    
    # Get available coupons for transfer action
    available_coupons = db.query(Coupon).filter(
        Coupon.owner_id == mnr_id,
        or_(Coupon.status == 'Active', Coupon.status == 'Unused', Coupon.status == 'Available')
    ).all()
    
    available_for_transfer = [{
        "id": c.id,
        "coupon_type": c.coupon_type,
        "status": c.status
    } for c in available_coupons]
    
    # Summary stats
    all_incoming = db.query(CouponTransfer).filter(CouponTransfer.to_user_id == mnr_id).count()
    all_outgoing = db.query(CouponTransfer).filter(CouponTransfer.from_user_id == mnr_id).count()
    
    summary = {
        "total_incoming": all_incoming,
        "total_outgoing": all_outgoing,
        "available_for_transfer": len(available_for_transfer)
    }
    
    log_staff_action(
        db=db, staff_id=current_user.id, staff_emp_code=current_user.emp_code,
        mnr_id=mnr_id, action_type="VIEW", action_details="Viewed coupon transfers",
        page_accessed="coupons/transfers"
    )
    
    return {
        "success": True,
        "mnr_id": mnr_id,
        "member_info": {"name": user.name, "status": user.account_status},
        "summary": summary,
        "data": {
            "transfers": transfer_list,
            "available_for_transfer": available_for_transfer,
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": total,
                "total_pages": (total + per_page - 1) // per_page
            }
        }
    }


async def get_activate_coupon_data(
    mnr_id: str,
    current_user: StaffEmployee,
    db: Session
) -> Dict[str, Any]:
    """
    Get data for Activate Coupon tab - DC Protocol (Jan 10, 2026)
    Matches regular user module format
    Returns: available coupons owned by user + inactive downline eligible for activation
    """
    menu_code = "staff_mnr_user_coupons"
    if not check_mnr_user_access(db, current_user, menu_code):
        raise HTTPException(status_code=403, detail="Access denied")
    
    user = validate_mnr_id(db, mnr_id)
    
    from app.models.coupon import Coupon
    from app.constants import COUPON_PACKAGE_MAP
    
    # Get available coupons owned by this user (can be used to activate)
    available_coupons = db.query(Coupon).filter(
        Coupon.owner_id == mnr_id,
        Coupon.status == 'Active'
    ).all()
    
    coupons_list = [{
        "id": str(c.id),
        "coupon_type": c.coupon_type,
        "package_name": COUPON_PACKAGE_MAP.get(str(c.coupon_type), c.coupon_type),
        "status": c.status,
        "assignment_status": getattr(c, 'assignment_status', None)
    } for c in available_coupons]
    
    # DC Protocol (Jan 10, 2026): Get ALL inactive MNR members eligible for activation
    # Enhanced: Not limited to downline - staff can activate any inactive member
    all_inactive_members = db.query(User).filter(
        User.coupon_status == 'Inactive',
        User.account_status == 'Active'
    ).order_by(User.registration_date.desc()).limit(100).all()
    
    eligible_members = [{
        "mnr_id": u.id,
        "name": u.name,
        "phone": u.phone_number,
        "referrer_id": u.referrer_id,
        "registration_date": u.registration_date.isoformat() if u.registration_date else None
    } for u in all_inactive_members]
    
    # Recent activations performed by this user (coupons used)
    recent_used = db.query(Coupon).filter(
        Coupon.owner_id == mnr_id,
        Coupon.status == 'Used'
    ).order_by(desc(Coupon.activated_at)).limit(10).all()
    
    recent_activations = [{
        "coupon_id": str(c.id),
        "coupon_type": c.coupon_type,
        "package_name": COUPON_PACKAGE_MAP.get(str(c.coupon_type), c.coupon_type),
        "used_by": c.used_by if c.used_by else None,
        "activation_date": c.activation_date.isoformat() if c.activation_date else None
    } for c in recent_used]
    
    summary = {
        "total_available": len(coupons_list),
        "eligible_downline": len(eligible_members),
        "recent_activations": len(recent_activations)
    }
    
    log_staff_action(
        db=db, staff_id=current_user.id, staff_emp_code=current_user.emp_code,
        mnr_id=mnr_id, action_type="VIEW", action_details="Viewed coupon activation data",
        page_accessed="coupons/activate"
    )
    
    return {
        "success": True,
        "mnr_id": mnr_id,
        "member_info": {"name": user.name, "status": user.account_status},
        "summary": summary,
        "data": {
            "available_coupons": coupons_list,
            "eligible_members": eligible_members,
            "recent_activations": recent_activations
        }
    }


def _is_accounts_or_vgk_supreme(current_user, db) -> bool:
    """Check if staff is Accounts department (primary or additional) or MR10001 VGK Supreme"""
    emp_code = getattr(current_user, 'emp_code', '') or ''
    if emp_code == 'MR10001':
        return True
    dept = getattr(current_user, 'department', None)
    if dept:
        dept_name = (getattr(dept, 'name', '') or '').lower()
        if 'accounts' in dept_name or 'finance' in dept_name:
            return True
    additional_depts = getattr(current_user, 'additional_departments', [])
    for ad in additional_depts:
        ad_dept = getattr(ad, 'department', None)
        if ad_dept:
            ad_name = (getattr(ad_dept, 'name', '') or '').lower()
            if 'accounts' in ad_name or 'finance' in ad_name:
                return True
    return False


async def get_buy_coupon_data(
    mnr_id: str,
    current_user: StaffEmployee,
    db: Session
) -> Dict[str, Any]:
    """
    Get data for Buy Coupon tab - DC Protocol (Jan 10, 2026)
    Returns: package options + wallet balance for staff-initiated purchases
    Restricted to Accounts department + MR10001 VGK Supreme only
    """
    if not _is_accounts_or_vgk_supreme(current_user, db):
        raise HTTPException(status_code=403, detail="Buy Coupon access restricted to Accounts department and VGK Supreme (MR10001) only")
    menu_code = "staff_mnr_user_coupons"
    if not check_mnr_user_access(db, current_user, menu_code):
        raise HTTPException(status_code=403, detail="Access denied")
    
    user = validate_mnr_id(db, mnr_id)
    
    from app.constants import PACKAGE_SYSTEM
    
    # Package options matching regular user format
    packages = []
    for name, config in PACKAGE_SYSTEM.items():
        packages.append({
            "name": name,
            "display_name": name.capitalize(),
            "price": config['price'],
            "points": config['points']
        })
    
    # User wallet balance
    wallet_balance = float(getattr(user, 'upgrade_wallet_balance', 0) or 0)
    
    log_staff_action(
        db=db, staff_id=current_user.id, staff_emp_code=current_user.emp_code,
        mnr_id=mnr_id, action_type="VIEW", action_details="Viewed buy coupon form",
        page_accessed="coupons/buy"
    )
    
    return {
        "success": True,
        "mnr_id": mnr_id,
        "member_info": {"name": user.name, "status": user.account_status},
        "data": {
            "packages": packages,
            "wallet_balance": wallet_balance
        }
    }


@router.get("/coupons/{mnr_id}/search-inactive-members")
async def search_inactive_members(
    mnr_id: str,
    q: str = Query(..., min_length=1, description="Search query (MNR ID, name, or phone)"),
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    DC Protocol (Jan 10, 2026): Search inactive MNR members for activation
    Staff can search by MNR ID, name, or phone number
    Returns up to 20 matching inactive members
    """
    menu_code = "staff_mnr_user_coupons"
    if not check_mnr_user_access(db, current_user, menu_code):
        raise HTTPException(status_code=403, detail="Access denied")
    
    validate_mnr_id(db, mnr_id)
    
    search_term = q.strip().upper()
    
    results = db.query(User).filter(
        User.coupon_status == 'Inactive',
        User.account_status == 'Active',
        or_(
            User.id.ilike(f"%{search_term}%"),
            User.name.ilike(f"%{search_term}%"),
            User.phone_number.ilike(f"%{search_term}%")
        )
    ).order_by(User.registration_date.desc()).limit(20).all()
    
    members = [{
        "mnr_id": u.id,
        "name": u.name,
        "phone": u.phone_number,
        "referrer_id": u.referrer_id,
        "registration_date": u.registration_date.isoformat() if u.registration_date else None
    } for u in results]
    
    log_staff_action(
        db=db, staff_id=current_user.id, staff_emp_code=current_user.emp_code,
        mnr_id=mnr_id, action_type="VIEW", action_details=f"Searched inactive members: {q}",
        page_accessed="coupons/activate/search"
    )
    
    return {
        "success": True,
        "query": q,
        "count": len(members),
        "members": members
    }


@router.post("/coupons/{mnr_id}/transfer")
async def staff_initiate_coupon_transfer(
    mnr_id: str,
    request: StaffCouponTransferRequest = Body(...),
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Staff-initiated coupon transfer on behalf of MNR user
    DC Protocol (Jan 10, 2026)
    Requires EDIT permission (VGK Supreme/Accounts only)
    Full audit trail maintained with staff identity
    """
    menu_code = "staff_mnr_user_coupons"
    # DC Protocol: Require EDIT permission for transfer action (not just view)
    if not check_mnr_user_access(db, current_user, menu_code, require_edit=True):
        raise HTTPException(status_code=403, detail="Transfer action requires edit permission")
    
    # Validate source user
    from_user = validate_mnr_id(db, mnr_id)
    
    # Validate target user
    to_user = db.query(User).filter(User.id == request.to_user_id).first()
    if not to_user:
        raise HTTPException(status_code=404, detail=f"Target user {request.to_user_id} not found")
    if to_user.account_status != 'Active':
        raise HTTPException(status_code=400, detail=f"Target user {request.to_user_id} is not active")
    
    # Cannot transfer to self
    if mnr_id == request.to_user_id:
        raise HTTPException(status_code=400, detail="Cannot transfer coupon to the same user")
    
    # Validate coupon ownership and availability
    from app.models.coupon import Coupon
    from app.models.coupon_transfer import CouponTransfer
    
    coupon = db.query(Coupon).filter(
        Coupon.id == request.coupon_id,
        Coupon.owner_id == mnr_id
    ).first()
    
    if not coupon:
        raise HTTPException(status_code=404, detail="Coupon not found or not owned by user")
    
    if coupon.status not in ('Active', 'Unused', 'Available'):
        raise HTTPException(status_code=400, detail=f"Coupon is not available for transfer (status: {coupon.status})")
    
    # Create transfer record
    # DC Protocol: initiated_by_id set to None for staff-initiated transfers
    # Staff identity captured in admin_notes for full audit trail
    transfer = CouponTransfer(
        from_user_id=mnr_id,
        to_user_id=request.to_user_id,
        coupon_id=request.coupon_id,
        package_type=coupon.coupon_type or 'Unknown',
        transfer_type='admin_transfer',
        initiated_by_id=None,  # DC Protocol: Null for staff-initiated (staff logged in admin_notes)
        status='Completed',
        requires_approval=False,
        transfer_date=get_indian_time(),
        completed_at=get_indian_time(),
        transfer_reason=request.transfer_reason,
        admin_notes=f"Staff-initiated transfer by {current_user.emp_code} (Staff ID: {current_user.id})"
    )
    db.add(transfer)
    
    # Update coupon ownership
    # DC Protocol: Use 'Assigned' (valid CHECK value) - transfer tracked in CouponTransfer table + admin_notes
    coupon.owner_id = request.to_user_id
    coupon.status = 'Active'
    coupon.assignment_status = 'Assigned'
    coupon.assignment_status_changed_at = get_indian_time()
    
    db.commit()
    
    # Comprehensive audit logging
    log_staff_action(
        db=db,
        staff_id=current_user.id,
        staff_emp_code=current_user.emp_code,
        mnr_id=mnr_id,
        action_type="TRANSFER",
        action_details=f"Transferred coupon {request.coupon_id} ({coupon.coupon_type}) from {mnr_id} to {request.to_user_id}. Reason: {request.transfer_reason}",
        page_accessed="coupons/transfer"
    )
    
    return {
        "success": True,
        "message": f"Coupon successfully transferred to {request.to_user_id}",
        "transfer": {
            "id": transfer.id,
            "from_user": mnr_id,
            "to_user": request.to_user_id,
            "coupon_id": request.coupon_id,
            "package_type": coupon.coupon_type,
            "status": "Completed",
            "transfer_date": transfer.transfer_date.isoformat() if transfer.transfer_date else None
        }
    }


@router.post("/coupons/{mnr_id}/purchase")
async def staff_initiate_coupon_purchase(
    mnr_id: str,
    request: StaffCouponPurchaseRequest = Body(...),
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Staff-initiated coupon purchase on behalf of MNR user
    DC Protocol (Jan 10, 2026)
    Follows regular MNR user purchase process
    Auto-approved since staff initiated
    Restricted to Accounts department + MR10001 VGK Supreme only
    """
    if not _is_accounts_or_vgk_supreme(current_user, db):
        raise HTTPException(status_code=403, detail="Coupon purchase restricted to Accounts department and VGK Supreme (MR10001) only")
    menu_code = "staff_mnr_user_coupons"
    if not check_mnr_user_access(db, current_user, menu_code, require_edit=True):
        raise HTTPException(status_code=403, detail="Purchase action requires edit permission")
    
    user = validate_mnr_id(db, mnr_id)
    
    from app.models.coupon import PINPurchaseRequest, Coupon
    from app.constants import PACKAGE_SYSTEM, COUPON_PACKAGE_MAP
    from decimal import Decimal
    import random
    
    package_upper = request.package_type.upper()
    if package_upper not in PACKAGE_SYSTEM:
        raise HTTPException(status_code=400, detail=f"Invalid package type: {request.package_type}. Valid: PLATINUM, DIAMOND, BLUE, LOYAL, WELCOME")
    
    package_config = PACKAGE_SYSTEM[package_upper]
    package_price = Decimal(str(package_config['price']))
    total_amount = package_price * request.quantity
    
    # DC Protocol: Use numeric string for package_type (matches regular user format)
    # Database CHECK constraint expects: '15000', '7500', '1000', '500', '0'
    package_type_numeric = str(int(package_price))
    
    is_welcome = package_upper == 'WELCOME'
    
    if is_welcome:
        staff_type = (current_user.staff_type or '').upper()
        role_name = (getattr(current_user, 'role_name', '') or '').upper()
        is_allowed = staff_type == 'VGK4U' or 'VGK4U SUPREME' in role_name or role_name == 'EA' or role_name == 'EXECUTIVE ASSISTANT'
        if not is_allowed:
            raise HTTPException(status_code=403, detail="Only VGK Supreme and EA staff can issue Welcome Coupons")
        if request.funding_source != 'welcome':
            raise HTTPException(status_code=400, detail="Welcome Coupons must use 'welcome' funding source")
        payment_details = f"Welcome Coupon issued by {current_user.emp_code} (Staff Type: {staff_type}). Package: WELCOME, Qty: {request.quantity}, Amount: ₹0"
        payment_method = "Welcome Coupon"
        transaction_id = f"WELCOME-{current_user.emp_code}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    elif request.funding_source == 'wallet':
        user_wallet = getattr(user, 'upgrade_wallet_balance', 0) or 0
        if Decimal(str(user_wallet)) < total_amount:
            raise HTTPException(
                status_code=400, 
                detail=f"Insufficient wallet balance. Required: ₹{total_amount}, Available: ₹{user_wallet}"
            )
        
        user.upgrade_wallet_balance = float(Decimal(str(user_wallet)) - total_amount)
        payment_details = f"Staff purchase from wallet by {current_user.emp_code}. Package: {package_upper}, Qty: {request.quantity}, Amount: ₹{total_amount}"
        payment_method = "Wallet Deduction"
        transaction_id = f"STAFF-WALLET-{current_user.emp_code}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    elif request.funding_source == 'offline':
        if not request.payment_method:
            raise HTTPException(status_code=400, detail="Payment method required for offline funding")
        if not request.transaction_id:
            raise HTTPException(status_code=400, detail="Transaction ID required for offline funding")
        if not request.amount_paid or request.amount_paid < float(total_amount):
            raise HTTPException(status_code=400, detail=f"Amount paid must be at least ₹{total_amount}")
        
        payment_details = f"Staff offline purchase by {current_user.emp_code}. Method: {request.payment_method}, TxnID: {request.transaction_id}, Amount: ₹{request.amount_paid}"
        payment_method = request.payment_method
        transaction_id = request.transaction_id
    
    else:
        raise HTTPException(status_code=400, detail="Invalid funding source. Use 'wallet', 'offline', or 'welcome'")
    
    if request.remarks:
        payment_details += f". Remarks: {request.remarks}"
    
    new_request = PINPurchaseRequest(
        user_id=mnr_id,
        package_type=package_type_numeric,
        package_value=int(package_price),
        quantity=request.quantity,
        total_amount=total_amount,
        payment_method=payment_method,
        transaction_id=transaction_id,
        payment_amount=Decimal(str(request.amount_paid)) if request.amount_paid else total_amount,
        payment_details=payment_details,
        request_date=get_indian_time(),
        status='Approved',
        superadmin_approved_by=None,
        superadmin_approved_date=get_indian_time(),
        finance_validated_by=None,
        finance_validated_date=get_indian_time(),
        superadmin_notes=f"Staff auto-approved purchase by {current_user.emp_code} (Staff ID: {current_user.id}) via Menu Access Control"
    )
    db.add(new_request)
    db.flush()
    
    coupons_created = []
    for i in range(request.quantity):
        random_digits = ''.join([str(random.randint(0, 9)) for _ in range(12)])
        coupon_id = int(f"99{random_digits}")
        
        new_coupon = Coupon(
            id=coupon_id,
            owner_id=mnr_id,
            coupon_type=package_type_numeric,
            status='Active',
            assignment_status='Assigned',
            assignment_status_changed_at=get_indian_time()
        )
        db.add(new_coupon)
        coupons_created.append(coupon_id)
    
    new_request.status = 'Fulfilled'
    new_request.completed_date = get_indian_time()
    
    db.commit()
    
    log_staff_action(
        db=db,
        staff_id=current_user.id,
        staff_emp_code=current_user.emp_code,
        mnr_id=mnr_id,
        action_type="PURCHASE",
        action_details=f"Purchased {request.quantity}x {package_upper} coupons for {mnr_id}. Funding: {request.funding_source}. Total: ₹{total_amount}. Coupons: {coupons_created}",
        page_accessed="coupons/purchase"
    )
    
    return {
        "success": True,
        "message": f"Successfully purchased {request.quantity}x {package_upper} coupon(s) for {mnr_id}",
        "purchase": {
            "request_id": new_request.id,
            "mnr_id": mnr_id,
            "package_type": package_upper,
            "quantity": request.quantity,
            "total_amount": float(total_amount),
            "funding_source": request.funding_source,
            "status": "Fulfilled",
            "coupons_created": coupons_created,
            "created_at": new_request.request_date.isoformat() if new_request.request_date else None
        }
    }


@router.post("/coupons/{mnr_id}/activate")
async def staff_activate_coupon(
    mnr_id: str,
    request: StaffCouponActivateRequest = Body(...),
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Staff-initiated coupon activation on behalf of MNR user
    DC Protocol (Jan 10, 2026) - Matches regular user module format (users.py lines 2815-3050)
    Includes: mobile uniqueness check, income calculations (Direct Referral, Ved, Guru Dakshina)
    """
    menu_code = "staff_mnr_user_coupons"
    if not check_mnr_user_access(db, current_user, menu_code, require_edit=True):
        raise HTTPException(status_code=403, detail="Activation action requires edit permission")
    
    owner = validate_mnr_id(db, mnr_id)
    
    from app.models.coupon import Coupon
    from app.constants import COUPON_PACKAGE_MAP, PACKAGE_SYSTEM
    from datetime import date
    # DC Protocol (Feb 2026): Scheduler imports removed - no real-time income at activation
    
    # Determine target user (owner or specified user)
    target_user_id = request.target_user_id if request.target_user_id else mnr_id
    target_member = db.query(User).filter(User.id == target_user_id).first()
    
    if not target_member:
        raise HTTPException(status_code=404, detail=f"Target user {target_user_id} not found")
    
    # Check if target user is inactive
    if target_member.coupon_status != 'Inactive':
        raise HTTPException(status_code=400, detail=f"User {target_user_id} is already {target_member.coupon_status}")
    
    # DC Protocol (Jan 10, 2026): Handle phone number update before activation
    # Staff can provide new_phone_number to resolve mobile uniqueness conflicts
    original_phone = target_member.phone_number
    phone_to_validate = original_phone
    if request.new_phone_number and request.new_phone_number.strip():
        new_phone = request.new_phone_number.strip()
        # Validate format (10 digits)
        if not new_phone.isdigit() or len(new_phone) != 10:
            raise HTTPException(status_code=400, detail="Invalid phone number format. Must be 10 digits.")
        phone_to_validate = new_phone
    
    # DC Protocol: Validate mobile uniqueness BEFORE applying phone update
    from app.services.user_service import UserService
    user_service = UserService(db)
    mobile_check = user_service.ensure_unique_active_mobile(phone_to_validate, target_user_id)
    if not mobile_check.get("success"):
        raise HTTPException(status_code=400, detail=mobile_check.get("error", "Mobile number validation failed"))
    
    # Only update phone after validation passes
    if phone_to_validate != original_phone:
        target_member.phone_number = phone_to_validate
    
    # Find the coupon
    coupon = db.query(Coupon).filter(
        Coupon.id == request.coupon_id,
        Coupon.owner_id == mnr_id,
        Coupon.status == 'Active'
    ).first()
    
    if not coupon:
        raise HTTPException(status_code=404, detail="Coupon not found or not available for activation")
    
    # Get package configuration
    package_type_str = str(coupon.coupon_type)
    package_name = COUPON_PACKAGE_MAP.get(package_type_str)
    
    if not package_name or package_name not in PACKAGE_SYSTEM:
        raise HTTPException(status_code=400, detail=f"Invalid package type: {package_type_str}")
    
    config = PACKAGE_SYSTEM[package_name]
    
    # Update target member package_points
    target_member.package_points = config['points']
    
    # CRITICAL: Set activation_date on user
    activation_time = get_indian_time()
    target_member.activation_date = activation_time
    target_member.coupon_status = 'Activated'
    
    # DC Protocol: Flag Welcome Coupon users for income/award exclusion
    if package_type_str in ('0', 'WELCOME'):
        target_member.is_welcome_coupon = True
    
    # Mark coupon as used
    coupon.status = 'Used'
    coupon.activation_date = activation_time
    coupon.used_by = target_user_id
    
    # DC Protocol (Feb 2026): ALL income (Direct Referral, Guru Dakshina, Ved Income)
    # is generated by midnight scheduler ONLY. No real-time income creation at activation.
    # The midnight scheduler will pick up this activation via activation_date check.
    income_generated = []
    
    db.commit()
    
    log_staff_action(
        db=db,
        staff_id=current_user.id,
        staff_emp_code=current_user.emp_code,
        mnr_id=mnr_id,
        action_type="ACTIVATION",
        action_details=f"Activated coupon {request.coupon_id} for {target_user_id}. Package: {package_name}, Points: {config['points']}. Income generated: {len(income_generated)} records",
        page_accessed="coupons/activate"
    )
    
    return {
        "success": True,
        "message": f"Successfully activated coupon for {target_user_id}",
        "activation": {
            "coupon_id": request.coupon_id,
            "target_user": target_user_id,
            "package": package_name,
            "points_assigned": config['points'],
            "activation_date": activation_time.isoformat(),
            "income_generated": income_generated
        }
    }


@router.get("/zynova/{mnr_id}")
async def get_zynova_unified(
    mnr_id: str,
    tab: str = Query("real-estate", description="Tab: real-estate, insurance, training"),
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Unified VGK4U endpoint - routes to appropriate sub-endpoint based on tab"""
    if tab == "insurance":
        return await get_zynova_insurance(mnr_id=mnr_id, current_user=current_user, db=db)
    elif tab == "training":
        return await get_zynova_training(mnr_id=mnr_id, current_user=current_user, db=db)
    return await get_zynova_real_estate(mnr_id=mnr_id, current_user=current_user, db=db)


@router.get("/awards/{mnr_id}")
async def get_member_awards(
    mnr_id: str,
    tab: str = Query("direct", description="Tab: direct, matching, bonanza"),
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    DC Protocol: Get member awards data for Staff MNR User Awards page
    Mirrors user-facing award pages with complete lifecycle data
    """
    from app.models.awards import (
        UserAwardProgress, UserMatchingAwardProgress, 
        DirectAwardTier, MatchingAwardTier, AwardAuditLog
    )
    from app.models.bonanza import DynamicBonanzaHistory, DynamicBonanza, BonanzaProgress
    from app.constants.award_statuses import AwardStatus, normalize_status
    from app.services.award_actions_service import AwardActionsService
    
    member = validate_mnr_id(db, mnr_id)
    mnr_id = member.id
    
    if not check_mnr_user_access(db, current_user, 'staff_mnr_user_awards'):
        raise HTTPException(status_code=403, detail="Access denied to MNR User Awards")
    
    log_staff_action(
        db=db,
        staff_id=current_user.id,
        staff_emp_code=current_user.emp_code,
        mnr_id=mnr_id,
        action_type="VIEW",
        action_details=f"Viewed awards tab: {tab}",
        page_accessed="awards"
    )
    
    member_info = {
        "mnr_id": member.id,
        "name": member.name,
        "package": map_package_points_to_name(member.package_points),
        "status": member.coupon_status
    }
    
    staff_role = current_user.staff_type or 'Staff'
    can_update = staff_role in ['VGK Supreme', 'Accounts', 'Executive Assistant']
    
    if tab == "direct":
        # DC Protocol: Staff view - SHOW ALL TIERS like user page (awards_fast.py pattern)
        from sqlalchemy import asc, func
        from app.services.award_service import AwardService
        from datetime import date
        
        tiers = db.query(DirectAwardTier).order_by(asc(DirectAwardTier.cumulative_required)).all()
        progress_records = db.query(UserAwardProgress).filter(
            UserAwardProgress.user_id == mnr_id
        ).all()
        
        # Get bonanza deductions for display
        award_service = AwardService(db)
        bonanza_data = award_service.get_bonanza_deduction(mnr_id, 'direct')
        total_bonanza = bonanza_data.get('total_deduction', 0)
        
        # Get current referral stats
        total_points = db.query(func.sum(User.package_points)).filter(
            User.referrer_id == mnr_id,
            User.coupon_status == 'Activated'
        ).scalar() or 0
        
        awards = []
        previous_cumulative = 0
        
        for tier in tiers:
            progress = next((p for p in progress_records if p.award_tier_id == tier.id), None)
            tier_requirement = tier.cumulative_required - previous_cumulative
            effective_points = max(0, total_points - total_bonanza)
            current_tier_points = max(0, effective_points - previous_cumulative)
            
            # Calculate progress for this tier
            if tier_requirement > 0:
                progress_pct = min(100.0, (current_tier_points / tier_requirement) * 100)
                display_progress = int((progress_pct / 100.0) * tier.referral_count)
            else:
                progress_pct = 0
                display_progress = 0
            
            # Determine achievement status
            achieved = effective_points >= tier.cumulative_required
            if progress and progress.achievement_date:
                achieved = True
            
            # Calculate remaining
            remaining = max(0, tier.referral_count - display_progress)
            
            award_entry = {
                "id": progress.id if progress else None,
                "tier_id": tier.id,
                "type": "direct",
                "rank_name": tier.award_name,
                "award_item": tier.award_description,
                "required_referrals": tier.referral_count,
                "current_referrals": display_progress,
                "bonanza_claimed": int(total_bonanza / tier_requirement) if tier_requirement > 0 else 0,
                "remaining": remaining,
                "progress_percentage": progress_pct,
                "achieved": achieved,
                "achieved_date": (progress.achieved_at or progress.achievement_date).isoformat() if progress and (progress.achieved_at or progress.achievement_date) else None,
                "processed_status": progress.processed_status if progress else None,
                "status_display": AwardActionsService.get_status_display_label(progress.processed_status) if progress and progress.processed_status else ("Pending Approval" if achieved else None),
                "status_color": AwardActionsService.get_status_badge_color(progress.processed_status) if progress and progress.processed_status else ("warning" if achieved else None),
                "actual_price": float(tier.actual_price) if tier.actual_price else 0,
                "dispatch_date": progress.dispatch_date.isoformat() if progress and progress.dispatch_date else None,
                "received_date": progress.received_date.isoformat() if progress and progress.received_date else None,
                "process_date": progress.processed_date.isoformat() if progress and progress.processed_date else None,
                "last_updated_by": progress.processed_by if progress else None,
                "can_update": can_update and achieved and progress is not None,
                "available_actions": AwardActionsService.get_available_actions(progress.processed_status, staff_role, 'direct') if can_update and progress else [],
                "is_legacy": progress.is_legacy_pre_reset if progress else False
            }
            awards.append(award_entry)
            previous_cumulative = tier.cumulative_required
        
        summary = {
            "total": len([a for a in awards if a['achieved']]),
            "achieved": len([a for a in awards if a['achieved']]),
            "pending": len([a for a in awards if a['achieved'] and a['processed_status'] != 'Delivered']),
            "total_value": sum(a['actual_price'] for a in awards if a['achieved'])
        }
        
        return {"success": True, "member_info": member_info, "tab": "direct", "awards": awards, "summary": summary}
    
    elif tab == "matching":
        # DC Protocol: Staff view - SHOW ALL TIERS like user page
        from sqlalchemy import asc
        from app.services.award_service import AwardService
        from app.services.sql_utils import get_matching_pairs_with_reset_logic_sql
        
        tiers = db.query(MatchingAwardTier).order_by(asc(MatchingAwardTier.cumulative_required)).all()
        progress_records = db.query(UserMatchingAwardProgress).filter(
            UserMatchingAwardProgress.user_id == mnr_id
        ).all()
        
        # Get current matching pairs count - function returns dict with 'matching_pairs' key
        matching_result = get_matching_pairs_with_reset_logic_sql(db, mnr_id, member.activation_date)
        matching_pairs = matching_result.get('matching_pairs', 0) if isinstance(matching_result, dict) else 0
        
        # Get bonanza deductions
        award_service = AwardService(db)
        bonanza_data = award_service.get_bonanza_deduction(mnr_id, 'matching')
        total_bonanza = bonanza_data.get('total_deduction', 0)
        
        awards = []
        previous_cumulative = 0
        effective_pairs = max(0, matching_pairs - total_bonanza)
        
        for tier in tiers:
            progress = next((p for p in progress_records if p.matching_award_tier_id == tier.id), None)
            tier_requirement = tier.cumulative_required - previous_cumulative
            current_tier_pairs = max(0, effective_pairs - previous_cumulative)
            
            # Calculate progress for this tier
            if tier_requirement > 0:
                progress_pct = min(100.0, (current_tier_pairs / tier_requirement) * 100)
                display_progress = int((progress_pct / 100.0) * tier.match_count)
            else:
                progress_pct = 0
                display_progress = 0
            
            # Determine achievement status
            achieved = effective_pairs >= tier.cumulative_required
            if progress and progress.achievement_date:
                achieved = True
            
            remaining = max(0, tier.match_count - display_progress)
            
            award_entry = {
                "id": progress.id if progress else None,
                "tier_id": tier.id,
                "type": "matching",
                "rank_name": tier.award_name,
                "award_item": tier.award_description,
                "required_matches": tier.match_count,
                "current_matches": display_progress,
                "bonanza_claimed": int(total_bonanza),
                "remaining": remaining,
                "progress_percentage": progress_pct,
                "achieved": achieved,
                "achieved_date": progress.achievement_date.isoformat() if progress and progress.achievement_date else None,
                "processed_status": progress.processed_status if progress else None,
                "status_display": AwardActionsService.get_status_display_label(progress.processed_status) if progress and progress.processed_status else ("Pending Approval" if achieved else None),
                "status_color": AwardActionsService.get_status_badge_color(progress.processed_status) if progress and progress.processed_status else ("warning" if achieved else None),
                "actual_price": float(tier.actual_price) if tier.actual_price else 0,
                "dispatch_date": progress.dispatch_date.isoformat() if progress and progress.dispatch_date else None,
                "received_date": progress.received_date.isoformat() if progress and progress.received_date else None,
                "process_date": progress.updated_at.isoformat() if progress and progress.updated_at else None,
                "last_updated_by": progress.processed_by if progress else None,
                "can_update": can_update and achieved and progress is not None,
                "available_actions": AwardActionsService.get_available_actions(progress.processed_status, staff_role, 'matching') if can_update and progress else [],
                "is_legacy": progress.is_legacy_pre_reset if progress else False
            }
            awards.append(award_entry)
            previous_cumulative = tier.cumulative_required
        
        summary = {
            "total": len([a for a in awards if a['achieved']]),
            "achieved": len([a for a in awards if a['achieved']]),
            "pending": len([a for a in awards if a['achieved'] and a['processed_status'] != 'Delivered']),
            "total_value": sum(a['actual_price'] for a in awards if a['achieved'])
        }
        
        return {"success": True, "member_info": member_info, "tab": "matching", "awards": awards, "summary": summary}
    
    elif tab == "bonanza":
        bonanza_query = db.query(DynamicBonanzaHistory, DynamicBonanza).outerjoin(
            DynamicBonanza, DynamicBonanzaHistory.bonanza_id == DynamicBonanza.id
        ).filter(
            DynamicBonanzaHistory.user_id == mnr_id
        ).order_by(desc(DynamicBonanzaHistory.claimed_at)).all()
        
        awards = []
        for history, bonanza in bonanza_query:
            awards.append({
                "id": history.id,
                "type": "bonanza",
                "bonanza_name": bonanza.bonanza_name if bonanza else "Bonanza",
                "reward_name": history.award_name or (bonanza.award_name if bonanza else "Cash Reward"),
                "reward_value": float(history.reward_value_claimed) if history.reward_value_claimed else 0,
                "claimed_date": history.claimed_at.isoformat() if history.claimed_at else None,
                "processed_status": history.processed_status or "Pending",
                "status_display": AwardActionsService.get_status_display_label(history.processed_status) if history.processed_status else "Pending",
                "status_color": AwardActionsService.get_status_badge_color(history.processed_status) if history.processed_status else "secondary",
                "dispatch_date": history.dispatch_date.isoformat() if history.dispatch_date else None,
                "received_date": history.received_date.isoformat() if history.received_date else None,
                "last_updated_by": history.processed_by if hasattr(history, 'processed_by') else None,
                "can_update": can_update,
                "available_actions": AwardActionsService.get_available_actions(history.processed_status, staff_role, 'bonanza') if can_update else []
            })
        
        summary = {
            "total": len(awards),
            "claimed": len(awards),
            "total_value": sum(a['reward_value'] for a in awards)
        }
        
        return {"success": True, "member_info": member_info, "tab": "bonanza", "awards": awards, "summary": summary}
    
    return {"success": False, "message": f"Unknown tab: {tab}"}


class AwardStatusUpdateRequest(BaseModel):
    award_id: int = Field(..., description="ID of the award record")
    award_type: str = Field(..., description="Type: direct, matching, bonanza")
    new_status: str = Field(..., description="New status value")
    notes: Optional[str] = Field(None, description="Optional notes")


@router.put("/awards/{mnr_id}/status")
async def update_award_status(
    mnr_id: str,
    request: AwardStatusUpdateRequest = Body(...),
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    DC Protocol: Update award status with VGK re-change restriction
    - VGK, Accounts, EA can update status
    - Once changed, only VGK can change again
    - Complete audit trail maintained
    """
    from app.models.awards import (
        UserAwardProgress, UserMatchingAwardProgress, AwardAuditLog
    )
    from app.models.bonanza import DynamicBonanzaHistory
    from app.constants.award_statuses import AwardStatus, normalize_status
    
    member = validate_mnr_id(db, mnr_id)
    mnr_id = member.id
    
    if not check_mnr_user_access(db, current_user, 'staff_mnr_user_awards', require_edit=True):
        raise HTTPException(status_code=403, detail="Access denied to update MNR User Awards")
    
    staff_role = current_user.staff_type or 'Staff'
    
    if staff_role not in ['VGK Supreme', 'Accounts', 'Executive Assistant']:
        raise HTTPException(
            status_code=403, 
            detail="Only VGK Supreme, Accounts, or Executive Assistant can update award status"
        )
    
    award = None
    entity_type = None
    old_status = None
    last_changed_by = None
    
    if request.award_type == "direct":
        award = db.query(UserAwardProgress).filter(
            UserAwardProgress.id == request.award_id,
            UserAwardProgress.user_id == mnr_id
        ).first()
        entity_type = "direct_award"
        if award:
            old_status = award.processed_status
            last_changed_by = award.processed_by
    elif request.award_type == "matching":
        award = db.query(UserMatchingAwardProgress).filter(
            UserMatchingAwardProgress.id == request.award_id,
            UserMatchingAwardProgress.user_id == mnr_id
        ).first()
        entity_type = "matching_award"
        if award:
            old_status = award.processed_status
            last_changed_by = award.processed_by
    elif request.award_type == "bonanza":
        award = db.query(DynamicBonanzaHistory).filter(
            DynamicBonanzaHistory.id == request.award_id,
            DynamicBonanzaHistory.user_id == mnr_id
        ).first()
        entity_type = "bonanza_award"
        if award:
            old_status = award.processed_status
            last_changed_by = getattr(award, 'processed_by', None)
    
    if not award:
        raise HTTPException(status_code=404, detail="Award not found")
    
    if last_changed_by and staff_role != 'VGK Supreme':
        last_updater = db.query(StaffEmployee).filter(
            StaffEmployee.id == last_changed_by
        ).first()
        if last_updater:
            raise HTTPException(
                status_code=403,
                detail=f"This award was previously updated by {last_updater.name}. Only VGK Supreme can make further changes."
            )
    
    new_status = normalize_status(request.new_status)
    award.processed_status = new_status
    from app.models.staff import StaffEmployee
    award.processed_by = str(current_user.emp_code or current_user.id) if isinstance(current_user, StaffEmployee) else str(current_user.id)
    award.processed_date = get_indian_time()
    
    if request.notes:
        if hasattr(award, 'admin_notes'):
            award.admin_notes = request.notes
        elif hasattr(award, 'notes'):
            award.notes = request.notes
    
    audit_log = AwardAuditLog(
        entity_type=entity_type,
        entity_id=request.award_id,
        action=f"status_update_by_{staff_role.lower().replace(' ', '_')}",
        old_status=old_status,
        new_status=new_status,
        actor_role=staff_role,
        actor_id=str(current_user.id),
        notes=request.notes,
        audit_metadata={
            "mnr_id": mnr_id,
            "staff_emp_code": current_user.emp_code,
            "staff_name": current_user.name,
            "updated_via": "staff_mnr_user_awards"
        },
        timestamp=get_indian_time()
    )
    db.add(audit_log)
    
    db.commit()
    
    log_staff_action(
        db=db,
        staff_id=current_user.id,
        staff_emp_code=current_user.emp_code,
        mnr_id=mnr_id,
        action_type="UPDATE",
        action_details=f"Updated {request.award_type} award #{request.award_id} status: {old_status} -> {new_status}",
        page_accessed="awards/status"
    )
    
    return {
        "success": True,
        "message": f"Award status updated to {new_status}",
        "award_id": request.award_id,
        "award_type": request.award_type,
        "old_status": old_status,
        "new_status": new_status,
        "updated_by": current_user.name,
        "updated_at": get_indian_time().isoformat()
    }
