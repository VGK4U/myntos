"""
Comprehensive User Management API Endpoints for FastAPI
Handles user profiles, authentication, registration, and administrative functions
"""

from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr

from app.core.database import get_db
from app.core.security import get_current_user, get_current_user_hybrid, require_admin, SecurityManager
from app.core.user_update_guard import check_user_update_allowed
from app.models.user import User
from app.services.user_service import UserService
from app.services.reference_service import ReferenceService

router = APIRouter()

# Pydantic models for request validation
class UserRegistrationRequest(BaseModel):
    # Accept both formats for backward compatibility
    name: Optional[str] = None  # Full name - will be split into first_name and last_name
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[EmailStr] = None  # Made optional - collected during KYC
    phone_number: Optional[str] = None  # Backend standard
    mobile: Optional[str] = None  # Frontend sends this
    password: str
    sponsor_id: str  # MANDATORY: Sponsor MNR ID (referrer)
    position: str  # MANDATORY: "Left" or "Right" placement side preference
    
    # Optional fields from frontend
    city: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None
    # [DC-PHONE-OTP-001] Phone verification token (required)
    phone_verified_token: Optional[str] = None

class UserProfileUpdateRequest(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    mobile: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None
    pan_number: Optional[str] = None
    aadhar_number: Optional[str] = None
    bank_account_number: Optional[str] = None
    bank_ifsc_code: Optional[str] = None
    bank_name: Optional[str] = None
    account_holder_name: Optional[str] = None

class PasswordChangeRequest(BaseModel):
    old_password: str
    new_password: str

@router.get("/{user_id}/basic-info")
async def get_user_basic_info(
    user_id: str,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get basic user info for referrer lookup (public endpoint)
    Returns only safe, non-sensitive information
    """
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        return {
            "success": False,
            "message": f"User with MNR ID {user_id} not found"
        }
    
    return {
        "success": True,
        "data": {
            "mnr_id": user.id,
            "name": user.name,
            "account_status": user.account_status
        }
    }

@router.post("/send-otp")
async def mnr_send_otp(
    req: dict,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """[DC-PHONE-OTP-001] Send WhatsApp OTP to phone for MNR new member registration."""
    phone = (req.get("phone") or "").strip().replace(" ", "")
    if not phone or len(phone) < 10 or not phone.isdigit():
        raise HTTPException(status_code=400, detail="Please provide a valid 10-digit mobile number.")
    from app.utils.phone_otp import generate_and_send_otp
    return generate_and_send_otp(phone=phone, purpose='mnr_register', db=db)


@router.post("/verify-otp")
async def mnr_verify_otp(
    req: dict,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """[DC-PHONE-OTP-001] Verify OTP and issue phone_verified_token for MNR new member registration."""
    phone = (req.get("phone") or "").strip().replace(" ", "")
    otp_code = (req.get("otp_code") or "").strip()
    if not phone or not otp_code:
        raise HTTPException(status_code=400, detail="Phone and OTP code are required.")
    from app.utils.phone_otp import verify_otp_and_issue_token
    token = verify_otp_and_issue_token(phone=phone, otp_code=otp_code, purpose='mnr_register', db=db)
    return {"success": True, "phone_verified_token": token, "message": "Phone verified successfully."}


@router.post("/register")
async def register_new_user(
    user_data: UserRegistrationRequest,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Register a new user in the Reference system with AUTOMATIC EXTREME PLACEMENT
    REQUIRES: sponsor_id and position (Left/Right preference)
    System automatically finds extreme left or extreme right position under sponsor
    """
    # [DC-PHONE-OTP-001] Validate phone verification token before account creation
    _phone = (user_data.mobile or user_data.phone_number or '').strip().replace(" ", "")
    if not _phone:
        raise HTTPException(status_code=400, detail="Mobile number is required.")
    if not user_data.phone_verified_token:
        raise HTTPException(
            status_code=400,
            detail="Phone verification required. Please verify your WhatsApp number with OTP before registering."
        )
    from app.utils.phone_otp import validate_and_consume_token
    validate_and_consume_token(phone=_phone, token=user_data.phone_verified_token, purpose='mnr_register', db=db)

    # Check if user registration is allowed
    check_user_update_allowed(db, 'user_registration_signup')
    
    user_service = UserService(db)
    reference_service = ReferenceService(db)
    
    # Validate position value (must be "Left" or "Right")
    if user_data.position not in ["Left", "Right", "left", "right"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Position must be 'Left' or 'Right'. Please contact company representative for assistance."
        )
    
    # Validate sponsor exists
    sponsor = db.query(User).filter(User.id == user_data.sponsor_id).first()
    if not sponsor:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Sponsor MNR ID '{user_data.sponsor_id}' not found. Please contact company representative for assistance."
        )
    
    # Create user account
    user_dict = user_data.dict()
    
    # Handle mobile vs phone_number field mismatch
    if user_dict.get('mobile') and not user_dict.get('phone_number'):
        user_dict['phone_number'] = user_dict['mobile']
    
    # Handle name splitting if first_name/last_name not provided
    if not user_dict.get('first_name') and not user_dict.get('last_name'):
        full_name = (user_dict.get('name') or '').strip()
        if full_name:
            name_parts = full_name.split(' ', 1)
            user_dict['first_name'] = name_parts[0] if len(name_parts) > 0 else full_name
            user_dict['last_name'] = name_parts[1] if len(name_parts) > 1 else ''
    
    # Validate that we have required name fields
    if not user_dict.get('first_name'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="First name is required. Please provide either 'name' or 'first_name' field."
        )
    
    # NEW REQUIREMENT: Both first name and last name are mandatory for all new users
    if not user_dict.get('last_name') or not user_dict.get('last_name').strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Both first name and last name are required. Please provide a full name with at least two names (e.g., 'John Doe')."
        )
    
    create_result = user_service.create_user(user_dict)
    
    if not create_result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=create_result.get("error", "User creation failed")
        )
    
    new_user_id = create_result["user_id"]
    
    # AUTOMATIC EXTREME PLACEMENT - find extreme position based on user's preference
    placement_result = None
    try:
        placement_result = reference_service.extreme_place_user(
            new_user_id, 
            user_data.sponsor_id,
            user_data.position.capitalize()  # Ensure "Left" or "Right" format
        )
    except Exception as e:
        # Rollback user creation if placement fails
        db.query(User).filter(User.id == new_user_id).delete()
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Placement failed: {str(e)}. Please contact company representative for assistance."
        )
    
    return {
        "success": True,
        "user_details": create_result["user_details"],
        "placement_result": placement_result,
        "message": "User registered successfully with automatic extreme placement"
    }

@router.get("/profile/{user_id}")
async def get_user_profile(
    user_id: str,
    current_user = Depends(get_current_user_hybrid),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get comprehensive user profile information
    Preserves Flask profile display functionality
    """
    # DC Protocol: Menu-based access control - page assignment = full access
    if current_user.id != user_id and not hasattr(current_user, 'emp_code'):
        raise HTTPException(
            status_code=403,
            detail="Access denied"
        )
    
    user_service = UserService(db)
    
    # Get user profile
    user = user_service.get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found."
        )
    
    # Format profile data (excluding sensitive information)
    profile_data = {
        "user_id": user.id,
        "personal_info": {
            "name": user.name,
            "email": user.email,
            "mobile": user.phone_number,
            "registration_date": user.registration_date.isoformat() if user.registration_date else None
        },
        "address_info": {
            "address": getattr(user, 'address', None),
            "city": getattr(user, 'city', None),
            "state": getattr(user, 'state', None),
            "pincode": getattr(user, 'pincode', None)
        },
        "verification_info": {
            "pan_number": getattr(user, 'pan_number', None),
            "aadhar_number": getattr(user, 'aadhar_number', None),
            "kyc_status": getattr(user, 'kyc_verified', False)
        },
        "banking_info": {
            "bank_name": getattr(user, 'bank_name', None),
            "account_number": getattr(user, 'bank_account_number', None),
            "ifsc_code": getattr(user, 'bank_ifsc_code', None),
            "account_holder_name": getattr(user, 'account_holder_name', None)
        },
        "account_status": {
            "user_type": user.user_type,
            "is_active": user.activation_date is not None,
            "account_locked": getattr(user, 'account_locked', False),
            "is_red_coupon": getattr(user, 'is_red_coupon', False),
            "referrer_id": user.referrer_id
        }
    }
    
    return {
        "success": True,
        "profile": profile_data,
        "access_level": "owner" if current_user.id == user_id else "admin"
    }

@router.put("/profile/{user_id}")
async def update_user_profile(
    user_id: str,
    profile_update: UserProfileUpdateRequest,
    current_user = Depends(get_current_user_hybrid),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Update user profile information
    Preserves Flask profile update functionality
    """
    # DC Protocol: Menu-based access control - page assignment = full access
    if current_user.id != user_id and not hasattr(current_user, 'emp_code'):
        raise HTTPException(
            status_code=403,
            detail="Access denied"
        )
    
    user_service = UserService(db)
    
    # Filter out None values from update data
    update_data = {k: v for k, v in profile_update.dict().items() if v is not None}
    
    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No update data provided."
        )
    
    # Update profile
    update_result = user_service.update_user_profile(user_id, update_data)
    
    if not update_result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=update_result.get("error", "Profile update failed")
        )
    
    return {
        "success": True,
        "message": update_result["message"],
        "updated_fields": update_result["updated_fields"],
        "updated_by": current_user.id
    }

@router.post("/change-password/{user_id}")
async def change_user_password(
    user_id: str,
    password_data: PasswordChangeRequest,
    current_user = Depends(get_current_user_hybrid),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Change user password with validation
    Preserves Flask password change security
    """
    # Validate access - only user themselves can change password
    if current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only change your own password."
        )
    
    # Check if password changes are allowed
    check_user_update_allowed(db, 'user_password_changes')
    
    user_service = UserService(db)
    
    # Change password
    change_result = user_service.change_password(
        user_id, 
        password_data.old_password, 
        password_data.new_password
    )
    
    if not change_result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=change_result.get("error", "Password change failed")
        )
    
    return {
        "success": True,
        "message": change_result["message"]
    }

@router.get("/search")
async def search_users(
    query: str = Query(..., min_length=2, description="Search query"),
    user_type: Optional[str] = Query(default=None, description="Filter by user type"),
    limit: int = Query(default=20, ge=1, le=100, description="Maximum results"),
    current_user = Depends(get_current_user_hybrid),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Search for users by various criteria
    Preserves Flask user search functionality
    """
    user_service = UserService(db)
    
    # Perform search
    search_results = user_service.search_users(query, user_type, limit)
    
    return {
        "success": True,
        "search_data": {
            "query": query,
            "user_type_filter": user_type,
            "results": search_results,
            "result_count": len(search_results)
        }
    }

@router.get("/admin/user-list")
async def get_admin_user_list(
    page: int = Query(default=1, ge=1, description="Page number"),
    per_page: int = Query(default=50, ge=1, le=200, description="Users per page"),
    user_type: Optional[str] = Query(default=None, description="Filter by user type"),
    status: Optional[str] = Query(default=None, description="Filter by status"),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get paginated user list for admin panel
    Admin-only functionality
    """
    from sqlalchemy import and_, or_
    
    # Build query filters
    query = db.query(User)
    
    if user_type:
        query = query.filter(User.user_type == user_type)
    
    if status == "active":
        query = query.filter(User.activation_date.isnot(None))
    elif status == "inactive":
        query = query.filter(User.activation_date.is_(None))
    elif status == "locked":
        query = query.filter(getattr(User, 'account_locked', False) == True)
    
    # Get total count
    total_users = query.count()
    
    # Apply pagination
    offset = (page - 1) * per_page
    users = query.offset(offset).limit(per_page).all()
    
    # Format user list
    user_list = []
    for user in users:
        user_list.append({
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "mobile": user.phone_number,
            "user_type": user.user_type,
            "registration_date": user.registration_date.isoformat() if user.registration_date else None,
            "is_active": user.activation_date is not None,
            "account_locked": getattr(user, 'account_locked', False),
            "is_red_coupon": getattr(user, 'is_red_coupon', False),
            "referrer_id": user.referrer_id,
            "ved_owner_id": user.ved_owner_id
        })
    
    # Calculate pagination info
    total_pages = (total_users + per_page - 1) // per_page
    
    return {
        "success": True,
        "user_list": {
            "users": user_list,
            "pagination": {
                "current_page": page,
                "per_page": per_page,
                "total_users": total_users,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_prev": page > 1
            },
            "filters": {
                "user_type": user_type,
                "status": status
            }
        }
    }

@router.get("/admin/user-analytics")
async def get_admin_user_analytics(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get comprehensive user analytics for admin dashboard
    Admin-only functionality
    """
    from datetime import datetime, timedelta
    from sqlalchemy import func, and_
    
    # Get user statistics
    total_users = db.query(User).count()
    active_users = db.query(User).filter(User.activation_date.isnot(None)).count()
    locked_users = db.query(User).filter(getattr(User, 'account_locked', False) == True).count()
    
    # Get registration analytics
    thirty_days_ago = datetime.now() - timedelta(days=30)
    seven_days_ago = datetime.now() - timedelta(days=7)
    
    monthly_registrations = db.query(User).filter(
        User.registration_date >= thirty_days_ago
    ).count()
    
    weekly_registrations = db.query(User).filter(
        User.registration_date >= seven_days_ago
    ).count()
    
    # Get user type distribution
    user_type_distribution = db.query(
        User.user_type,
        func.count(User.id).label('count')
    ).group_by(User.user_type).all()
    
    type_distribution = {}
    for distribution in user_type_distribution:
        type_distribution[distribution.user_type] = distribution.count
    
    return {
        "success": True,
        "user_analytics": {
            "overview": {
                "total_users": total_users,
                "active_users": active_users,
                "inactive_users": total_users - active_users,
                "locked_users": locked_users,
                "activation_rate": (active_users / total_users * 100) if total_users > 0 else 0
            },
            "growth": {
                "monthly_registrations": monthly_registrations,
                "weekly_registrations": weekly_registrations,
                "daily_average": monthly_registrations / 30 if monthly_registrations > 0 else 0
            },
            "user_type_distribution": type_distribution
        }
    }

@router.post("/admin/user/{user_id}/lock")
async def lock_user_account(
    user_id: str,
    reason: str = Query(..., description="Reason for locking account"),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Lock a user account (admin only)
    Preserves Flask admin control functionality
    """
    user_service = UserService(db)
    
    # Get target user
    target_user = user_service.get_user_by_id(user_id)
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found."
        )
    
    # Prevent locking admin accounts
    if target_user.user_type in ['Admin', 'Super Admin']:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot lock admin accounts."
        )
    
    # Lock the account
    target_user.account_locked = True
    target_user.last_updated = user_service.get_indian_time()
    
    db.commit()
    
    return {
        "success": True,
        "message": f"User account {user_id} has been locked.",
        "reason": reason,
        "locked_by": current_user.id,
        "locked_at": datetime.now().isoformat()
    }

@router.post("/admin/user/{user_id}/unlock")
async def unlock_user_account(
    user_id: str,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Unlock a user account (admin only)
    Preserves Flask admin control functionality
    """
    user_service = UserService(db)
    
    # Get target user
    target_user = user_service.get_user_by_id(user_id)
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found."
        )
    
    # Unlock the account
    target_user.account_locked = False
    target_user.last_updated = user_service.get_indian_time()
    
    db.commit()
    
    return {
        "success": True,
        "message": f"User account {user_id} has been unlocked.",
        "unlocked_by": current_user.id,
        "unlocked_at": datetime.now().isoformat()
    }

@router.get("/me")
async def get_current_user_profile(
    current_user = Depends(get_current_user_hybrid),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get current authenticated user's profile
    Convenient endpoint for frontend
    """
    user_service = UserService(db)
    
    # Get comprehensive dashboard data
    dashboard_data = user_service.get_user_dashboard_data(current_user.id)
    
    return {
        "success": True,
        "current_user": dashboard_data
    }