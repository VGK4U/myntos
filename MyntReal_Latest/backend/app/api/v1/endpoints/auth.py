"""
Authentication endpoints for FastAPI
Preserves Flask login system with JWT tokens
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request, Query, Body
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta
from typing import Optional, List

from app.core.database import get_db
from app.core.security import SecurityManager, get_current_user, get_current_user_hybrid
from app.core.config import settings
from app.models.user import User
from app.schemas.auth import LoginRequest, LoginResponse

router = APIRouter()

@router.get("/public/terms-and-conditions")
async def get_public_terms_and_conditions(
    db: Session = Depends(get_db)
):
    """
    PUBLIC endpoint - Get current Terms & Conditions content for user login popup
    No authentication required - accessible during login
    DC Protocol Feb 2026: Read from terms_and_conditions_versions table (single source of truth)
    """
    try:
        from app.models.system_control import TermsAndConditionsVersion
        
        # DC Protocol Feb 2026/Mar 2026: Use terms_and_conditions_versions table filtered to MNR or ALL platforms
        from sqlalchemy import or_ as _sa_or
        active_version = db.query(TermsAndConditionsVersion).filter(
            TermsAndConditionsVersion.is_active == True,
            _sa_or(
                TermsAndConditionsVersion.platform_type == 'MNR',
                TermsAndConditionsVersion.platform_type == 'ALL',
            )
        ).first()
        
        if not active_version:
            # Return default T&C if no active version exists
            return {
                "success": True,
                "data": {
                    "content": """
<h4>Terms & Conditions</h4>
<p>Welcome to our MNR platform. Please read these terms carefully.</p>
<ol>
    <li>By using this platform, you agree to comply with all applicable laws and regulations.</li>
    <li>All package purchases are final and non-refundable.</li>
    <li>Income calculations are based on your team's performance and package activation.</li>
    <li>KYC verification is mandatory for withdrawals.</li>
    <li>The company reserves the right to modify these terms at any time.</li>
</ol>
<p>For support, please contact your upline or admin.</p>
                    """,
                    "version": "1.0",
                    "max_displays": 3
                }
            }
        
        return {
            "success": True,
            "data": {
                "content": active_version.content or "",
                "version": active_version.version or "1.0",
                "max_displays": active_version.max_displays if hasattr(active_version, 'max_displays') else 3
            }
        }
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve Terms & Conditions: {str(e)}"
        )

@router.post("/login", response_model=LoginResponse)
async def login(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    User login endpoint - MNR ID ONLY authentication
    Accepts both JSON and form data (preserves Flask compatibility)
    Returns JWT tokens for authentication
    """
    # Detect content type and extract credentials
    content_type = request.headers.get("content-type", "")
    
    if "application/json" in content_type:
        json_body = await request.json()
        username = json_body.get("user_id") or json_body.get("username", "")
        password = json_body.get("password", "")
    else:
        form_data = await request.form()
        username = str(form_data.get("user_id") or form_data.get("username", ""))
        password = str(form_data.get("password", ""))
    
    if not username or not password:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Username and password are required"
        )
    
    # Validate MNR ID format first
    from app.core.security import SecurityManager
    if not SecurityManager.is_valid_mnr_id(str(username)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid MNR ID format. Please enter your MNR ID (e.g., MNR182364369)",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Authenticate user with MNR ID only
    user = SecurityManager.authenticate_user(db, username, password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect MNR ID or password. Please check your credentials and try again.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Check account status (preserves Flask account checks)
    account_status = str(getattr(user, 'account_status', 'Inactive'))
    if account_status != 'Active':
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail=f"Account is {account_status}. Please contact support for assistance."
        )
    
    # DC Protocol Feb 2026/Mar 2026: Get active T&C version for MNR platform
    from app.models.system_control import TermsAndConditionsVersion, AppSettings
    from sqlalchemy import or_ as _sa_or
    active_tc = db.query(TermsAndConditionsVersion).filter(
        TermsAndConditionsVersion.is_active == True,
        _sa_or(
            TermsAndConditionsVersion.platform_type == 'MNR',
            TermsAndConditionsVersion.platform_type == 'ALL',
        )
    ).first()
    current_tc_version = active_tc.version if active_tc else "1.0"
    
    # AUTO-ACCEPT TERMS FOR ADMIN USERS
    admin_types = ['RVZ ID', 'VGK ID', 'Admin', 'Super Admin', 'Finance Admin']
    if user.user_type in admin_types:
        if user.accepted_terms_version != current_tc_version:
            from datetime import datetime
            user.accepted_terms_version = current_tc_version
            user.acceptance_timestamp = datetime.now()
            db.commit()
            db.refresh(user)
    
    # Create access token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = SecurityManager.create_access_token(
        data={"sub": str(user.id), "email": user.email, "user_type": user.user_type},
        expires_delta=access_token_expires
    )

    # DC Protocol Mar 2026: Record MNR login session for analytics (non-blocking)
    try:
        from app.api.v1.endpoints.session_analytics import insert_session_log
        insert_session_log(
            db=db,
            user_type="mnr",
            user_id=str(user.id),
            user_identifier=str(user.id),
            display_name=user.name or "",
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            token_expiry_minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES,
        )
    except Exception:
        pass

    # Create refresh token
    user_id_str = str(getattr(user, 'id', ''))
    refresh_token = SecurityManager.create_refresh_token(user_id_str)
    
    # Determine T&C max displays based on registration date
    from datetime import date as dt_date
    cutoff_date = dt_date(2025, 10, 23)
    user_reg_date = user.registration_date.date() if user.registration_date else dt_date.today()
    tc_max_displays = 3 if user_reg_date >= cutoff_date else 10
    
    # DC Protocol Feb 2026: Get T&C content from terms_and_conditions_versions (not AppSettings)
    tc_content = active_tc.content if active_tc else ""
    tc_version = current_tc_version
    tc_max_displays_from_db = active_tc.max_displays if active_tc and hasattr(active_tc, 'max_displays') and active_tc.max_displays else tc_max_displays
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "user": {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "user_type": user.user_type,
            "wallet_balance": float(getattr(user, 'wallet_balance', 0.0)),
            "kyc_status": user.kyc_status,
            "coupon_status": user.coupon_status
        },
        "terms_and_conditions": {
            "content": tc_content,
            "version": tc_version,
            "max_displays": tc_max_displays_from_db,
            "user_accepted_version": user.accepted_terms_version
        }
    }

@router.get("/me")
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """
    Get current user information (replaces Flask current_user)
    JWT Token authentication ONLY
    DC Protocol Feb 2026: Handle Staff users that don't have MNR-specific fields
    """
    from app.models.staff import StaffEmployee
    from app.models.kyc_document import KYCDocument
    
    # DC Protocol Feb 2026: Staff users have different fields
    if isinstance(current_user, StaffEmployee):
        return {
            "id": current_user.id,
            "emp_code": current_user.emp_code,
            "name": current_user.full_name,
            "email": current_user.email,
            "user_type": "staff",
            "department": current_user.department,
            "designation": current_user.designation,
            "status": current_user.status,
            "is_active": current_user.status == 'active',
            "last_login": current_user.last_login,
            "coupon_status": None,
            "activation_date": None
        }
    
    return {
        "id": current_user.id,
        "name": current_user.name,
        "email": current_user.email,
        "mnr_id": current_user.id,
        "user_type": (getattr(current_user, "staff_type", None) or getattr(current_user, "user_type", "")),
        "wallet_balance": float(getattr(current_user, 'wallet_balance', 0.0)),
        "upgrade_wallet_balance": float(getattr(current_user, 'upgrade_wallet_balance', 0.0)),
        "kyc_status": current_user.kyc_status,
        "coupon_status": current_user.coupon_status,
        "account_status": current_user.account_status,
        "registration_date": current_user.registration_date,
        "activation_date": getattr(current_user, 'activation_date', None).isoformat() if getattr(current_user, 'activation_date', None) else None,
        "last_login": current_user.last_login,
        "is_ved": current_user.is_ved,
        "is_red_coupon": current_user.is_red_coupon,
        "profile_completion_score": current_user.profile_completion_score,
        "accepted_terms_version": current_user.accepted_terms_version
    }

@router.get("/me-hybrid")
async def get_current_user_info_hybrid(
    request: Request,
    role: Optional[str] = Query(None, description="Role hint: 'mnr', 'staff', or 'partner'"),
    db: Session = Depends(get_db)
):
    """
    Get current user information - HYBRID AUTH
    Accepts BOTH JWT tokens AND session cookies
    Used by admin panels that use cookie-based authentication
    Supports both MNR users (User) and Staff users (StaffEmployee)
    
    DC Protocol (Dec 28, 2025): Added role hint to resolve dual-session conflicts
    When role='mnr' is passed, MNR session is prioritized over staff session
    
    Response envelope: {"success": true, "data": {...}} for legacy compatibility
    """
    from app.models.staff import StaffEmployee
    from app.models.kyc_document import KYCDocument
    from app.core.security import get_current_mnr_user_from_hybrid, get_current_user_hybrid
    
    current_user = None
    
    if role == 'mnr':
        try:
            current_user = await get_current_mnr_user_from_hybrid(request, db)
        except HTTPException as e:
            if e.status_code == 401:
                current_user = await get_current_user_hybrid(request, db)
            else:
                raise e
    else:
        current_user = await get_current_user_hybrid(request, db)
    
    if isinstance(current_user, StaffEmployee):
        payload = {
            "id": current_user.id,
            "emp_code": current_user.emp_code,
            "name": current_user.full_name,
            "email": current_user.email,
            "user_type": "staff",
            "department": current_user.department,
            "designation": current_user.designation,
            "status": current_user.status,
            "is_active": current_user.status == 'active',
            "last_login": current_user.last_login,
            "authorization_level": "staff"
        }
        return {"success": True, "data": payload}
    
    # DC Protocol Feb 2026: Debug log for activation fields
    import logging
    logger = logging.getLogger(__name__)
    activation_val = getattr(current_user, 'activation_date', None)
    coupon_val = getattr(current_user, 'coupon_status', None)
    logger.info(f"[DC-ME-HYBRID] User {current_user.id}: activation_date={activation_val}, coupon_status={coupon_val}")
    
    # DC Protocol Feb 2026: Include profile fields for profile-view page
    actual_dob = getattr(current_user, 'actual_date_of_birth', None)
    cert_dob = getattr(current_user, 'certificate_date_of_birth', None)
    
    # DC Protocol Feb 2026: Get KYC documents for profile-view page
    kyc_docs = db.query(KYCDocument).filter(
        KYCDocument.owner_id == current_user.id
    ).all()
    db_to_frontend_map = {
        'aadhar_front': 'aadhaar_front',
        'aadhar_back': 'aadhaar_back',
        'pan_card': 'pan_card',
        'passport_photo': 'passport_photo'
    }
    kyc_doc_status = {}
    for doc in kyc_docs:
        frontend_key = db_to_frontend_map.get(doc.document_type, doc.document_type)
        kyc_doc_status[frontend_key] = {
            "status": doc.status,
            "uploaded_at": doc.uploaded_at.isoformat() if doc.uploaded_at else None,
            "rejection_reason": doc.rejection_reason
        }
    
    payload = {
        "id": current_user.id,
        "name": current_user.name,
        "email": current_user.email,
        "mnr_id": current_user.id,
        "user_type": (getattr(current_user, "staff_type", None) or getattr(current_user, "user_type", "")),
        "wallet_balance": float(getattr(current_user, 'wallet_balance', 0.0)),
        "upgrade_wallet_balance": float(getattr(current_user, 'upgrade_wallet_balance', 0.0)),
        "kyc_status": current_user.kyc_status,
        "coupon_status": coupon_val,
        "account_status": current_user.account_status,
        "registration_date": current_user.registration_date,
        "activation_date": activation_val.isoformat() if activation_val else None,
        "last_login": current_user.last_login,
        "is_ved": current_user.is_ved,
        "is_red_coupon": current_user.is_red_coupon,
        "profile_completion_score": current_user.profile_completion_score,
        "authorization_level": getattr(current_user, 'authorization_level', getattr(current_user, 'staff_type', None) or getattr(current_user, 'user_type', '')),
        "mobile_number": getattr(current_user, 'phone_number', None),
        "gender": getattr(current_user, 'gender', None),
        "actual_date_of_birth": actual_dob.isoformat() if actual_dob else None,
        "certificate_date_of_birth": cert_dob.isoformat() if cert_dob else None,
        "aadhaar_number": getattr(current_user, 'aadhaar_number', None),
        "pan_number": getattr(current_user, 'pan_number', None),
        "address": {
            "line1": getattr(current_user, 'address_line1', None),
            "line2": getattr(current_user, 'address_line2', None),
            "city": getattr(current_user, 'city', None),
            "state": getattr(current_user, 'state', None),
            "postal_code": getattr(current_user, 'postal_code', None)
        },
        "accepted_terms_version": current_user.accepted_terms_version,
        "bank_details_status": getattr(current_user, 'bank_details_status', 'Not Submitted'),
        "kyc_documents": kyc_doc_status,
        "bank_details": {
            "account_number": getattr(current_user, 'bank_account_number', None),
            "ifsc_code": getattr(current_user, 'bank_ifsc_code', None),
            "account_holder": getattr(current_user, 'bank_account_holder', None),
            "bank_name": getattr(current_user, 'bank_name', None),
            "branch": getattr(current_user, 'bank_branch_name', None),
            "upi_id": getattr(current_user, 'upi_id', None)
        }
    }
    
    # DC Protocol Feb 2026: Add eligibility status for dashboard banner
    from app.core.scheduler import get_user_eligibility_status
    from app.services.sql_utils import check_key_eligibility
    try:
        eligibility = get_user_eligibility_status(db, current_user)
        key_elig = check_key_eligibility(db, current_user.id)
        payload["eligibility_status"] = {
            "is_eligible": eligibility['is_eligible'],
            "is_fully_eligible": eligibility['is_fully_eligible'],
            "group_a_points": eligibility['group_a_points'],
            "group_b_points": eligibility['group_b_points'],
            "has_both_groups": eligibility['has_both_groups'],
            "has_first_matching": eligibility['has_first_matching'],
            "banner_message": eligibility['banner_message'],
            "blocking_reasons": eligibility['blocking_reasons'],
            "kyc_status": eligibility.get('kyc_status', 'pending'),
            "is_activated": eligibility.get('is_activated', False),
            "program_utilisation_completed": eligibility.get('program_utilisation_completed', False),
            "is_key_eligible": key_elig["is_key_eligible"],
            "key_eligibility_message": key_elig["message"],
            "post_cutoff_referral_count": key_elig["post_cutoff_referral_count"]
        }
    except Exception as e:
        logger.error(f"[DC-ME-HYBRID] Eligibility check failed: {e}")
        payload["eligibility_status"] = None
    
    return {"success": True, "data": payload}

@router.post("/refresh")
async def refresh_token(
    refresh_token: str,
    db: Session = Depends(get_db)
):
    """
    Refresh access token using refresh token
    """
    payload = SecurityManager.verify_token(refresh_token)
    
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
    
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token payload"
        )
    user = SecurityManager.get_user_by_id(db, str(user_id))
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    # Create new access token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = SecurityManager.create_access_token(
        data={"sub": user.id, "email": user.email, "user_type": user.user_type},
        expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    }

@router.post("/logout")
async def logout(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    DC Protocol (Dec 31, 2025): MNR user logout endpoint
    Invalidates the current session and clears any server-side session data
    Frontend handles token/localStorage cleanup
    """
    try:
        # Get authorization header if present
        auth_header = request.headers.get("Authorization", "")
        
        # Log the logout attempt for audit purposes
        user_id = None
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
            try:
                payload = SecurityManager.verify_token(token)
                if payload:
                    user_id = payload.get("sub")
            except:
                pass  # Token may be expired, still allow logout
        
        # In a stateless JWT system, server-side logout is a no-op
        # The actual session invalidation happens on the client side

        # DC Protocol Mar 2026: Close MNR session record for analytics (non-blocking)
        if user_id:
            try:
                from app.api.v1.endpoints.session_analytics import close_session_log
                close_session_log(db=db, user_type="mnr", user_id=str(user_id))
            except Exception:
                pass

        return {
            "success": True,
            "message": "Logged out successfully",
            "user_id": user_id
        }
    except Exception as e:
        # Even if something fails, we want logout to succeed
        return {
            "success": True,
            "message": "Logged out"
        }

@router.get("/debug-activation/{user_id}")
async def debug_user_activation(
    user_id: str,
    db: Session = Depends(get_db)
):
    """
    DC Protocol Feb 2026: Debug endpoint to verify activation data
    Returns raw activation status for any user (for debugging only)
    """
    from app.models.user import User
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return {"error": "User not found", "user_id": user_id}
    
    return {
        "user_id": user.id,
        "name": user.name,
        "coupon_status": user.coupon_status,
        "coupon_status_type": type(user.coupon_status).__name__,
        "activation_date": user.activation_date.isoformat() if user.activation_date else None,
        "activation_date_type": type(user.activation_date).__name__ if user.activation_date else "NoneType",
        "should_show_menus": bool(user.activation_date or user.coupon_status == 'Activated')
    }


@router.post("/key-eligibility-bulk")
async def check_key_eligibility_bulk_endpoint(
    user_ids: List[str] = Body(..., embed=True),
    current_user = Depends(get_current_user_hybrid),
    db: Session = Depends(get_db)
):
    """
    DC Protocol Feb 2026: Bulk key eligibility check for staff admin pages.
    Returns map of user_id -> is_key_eligible
    """
    from app.services.sql_utils import check_key_eligibility_bulk
    if not hasattr(current_user, 'emp_code'):
        raise HTTPException(status_code=403, detail="Staff access only")
    result = check_key_eligibility_bulk(db, user_ids[:500])
    return {"success": True, "data": result}
