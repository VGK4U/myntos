"""
Staff Authentication API Endpoints (DC Protocol Compliant)
Separate authentication system for staff members
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request, Body
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import Optional
from pydantic import BaseModel, EmailStr, Field
import pyotp

from app.core.database import get_db
from app.core.security import SecurityManager
from app.core.config import settings
from app.models.staff import (
    StaffEmployee, StaffRole, StaffDepartment, StaffSetting, 
    StaffAuditLog, log_staff_audit, check_nda_acceptance, check_all_pending_agreements
)

router = APIRouter(prefix="/staff", tags=["Staff Auth"])


class StaffLoginRequest(BaseModel):
    employee_id: str = Field(..., min_length=1, description="Employee ID (e.g., MR10001)")
    password: str = Field(..., min_length=1)
    totp_code: Optional[str] = Field(None, min_length=6, max_length=6)


class StaffLoginResponse(BaseModel):
    success: bool
    message: str
    access_token: Optional[str] = None
    token_type: str = "bearer"
    expires_in: Optional[int] = None
    requires_2fa: bool = False
    employee: Optional[dict] = None
    nda_required: bool = False
    nda_version_id: Optional[int] = None
    nda_version_number: Optional[str] = None
    nda_data: Optional[dict] = None


class StaffProfileResponse(BaseModel):
    success: bool
    employee: dict


def get_staff_setting(db: Session, key: str, default=None):
    """Get staff setting value"""
    setting = db.query(StaffSetting).filter_by(setting_key=key, is_active=True).first()
    if setting:
        return setting.get_value()
    return default


def get_current_staff_user(request: Request, db: Session = Depends(get_db)) -> StaffEmployee:
    """
    Dependency to get current authenticated staff user from JWT token
    DC: Validates token and ensures staff user exists
    DC Protocol (Dec 05, 2025): NDA enforcement - blocks all access until NDA accepted
    """
    auth_header = request.headers.get("Authorization")
    
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid authorization header",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    token = auth_header.split(" ")[1]
    
    try:
        from jose import jwt, JWTError
        from jose.exceptions import ExpiredSignatureError
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        
        user_type = payload.get("user_type")
        if user_type != "staff":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type for staff access",
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        employee_id = payload.get("sub")
        if not employee_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload",
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        employee = db.query(StaffEmployee).filter_by(id=int(employee_id)).first()
        if not employee:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Staff user not found",
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        # DC Protocol: Detailed status blocking messages (Dec 2025)
        if employee.status == 'deactivated':
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account temporarily suspended. Please contact HR for reactivation."
            )
        
        if employee.status == 'resigned':
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account permanently deactivated. Access denied."
            )
        
        if employee.status != 'active':
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Staff account is {employee.status}. Access denied."
            )
        
        # DC Protocol (Dec 05, 2025): NDA Enforcement Middleware
        # Block ALL endpoints except NDA-related ones until NDA is accepted
        request_path = request.url.path.lower()
        
        # DC Protocol Fix (Dec 05, 2025): CIRCULAR DEPENDENCY FIX
        # ALL NDA management endpoints must be accessible regardless of acceptance status
        # This prevents the infinite loop where users need NDA acceptance to manage NDAs
        # 
        # ARCHITECTURAL PRINCIPLE (MANDATORY):
        # NDA enforcement must NOT block access to NDA management endpoints.
        # These are administrative functions that require access regardless of acceptance status.
        #
        # Uses PREFIX-based bypass for ALL /api/v1/staff/nda/ routes
        NDA_PREFIX_BYPASS = '/api/v1/staff/nda/'  # ALL NDA endpoints bypass enforcement
        
        # Additional non-NDA bypass paths
        ADDITIONAL_BYPASS_PATHS = [
            '/api/v1/staff/auth/logout',     # Allow logout always
        ]
        
        # Check if current path bypasses NDA enforcement:
        # 1. Any path under /api/v1/staff/nda/ (all NDA management)
        # 2. Specific additional paths (logout)
        is_nda_bypass = (
            request_path.startswith(NDA_PREFIX_BYPASS) or
            any(request_path.endswith(bypass_path.lower()) for bypass_path in ADDITIONAL_BYPASS_PATHS)
        )
        
        if not is_nda_bypass:
            # DC-AGREEMENT-TYPE-001: Sequential multi-agreement gate (NDA first, then EMPLOYMENT)
            staff_type = employee.staff_type or 'MN_STAFF'
            pending_agreement, agreement_type, active_version = check_all_pending_agreements(
                db, employee.id, staff_type
            )
            
            if pending_agreement:
                _agreement_labels = {
                    'NDA': 'Non-Disclosure Agreement',
                    'EMPLOYMENT': 'Employment Agreement'
                }
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="NDA_PENDING",
                    headers={
                        "X-NDA-Required": "true",
                        "X-NDA-Version-Id": str(active_version.id) if active_version else "",
                        "X-Agreement-Type": agreement_type or "NDA",
                        "X-Agreement-Label": _agreement_labels.get(
                            agreement_type or "NDA", "Non-Disclosure Agreement"
                        )
                    }
                )
        
        return employee
        
    except HTTPException:
        # Re-raise HTTP exceptions (including our NDA_PENDING)
        raise
    except ExpiredSignatureError:
        # DC Protocol: Specific error for expired tokens
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="TOKEN_EXPIRED",
            headers={"WWW-Authenticate": "Bearer", "X-Token-Expired": "true"}
        )
    except JWTError as e:
        # DC Protocol: Specific error for invalid JWT format
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token format",
            headers={"WWW-Authenticate": "Bearer"}
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"}
        )


def get_current_staff_user_hybrid(request: Request, db: Session = Depends(get_db)) -> dict:
    """
    Hybrid dependency that returns staff user as dict for sandbox endpoints.
    DC Protocol: Returns dict with staff_type for VGK4U access checking.
    """
    employee = get_current_staff_user(request, db)
    return {
        "id": employee.id,
        "emp_code": employee.emp_code,
        "full_name": employee.full_name,
        "email": employee.email,
        "staff_type": employee.staff_type,
        "role_id": employee.role_id,
        "role_name": employee.role.role_name if employee.role else None,
        "department_id": employee.department_id,
        "department_name": employee.department.name if employee.department else None,
        "status": employee.status
    }


def requires_staff_role(*allowed_roles):
    """
    Decorator factory to check staff role
    DC: Role-based access control
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            current_user = kwargs.get('current_user')
            if not current_user:
                raise HTTPException(status_code=403, detail="Authentication required")
            
            if current_user.role.role_code not in allowed_roles:
                raise HTTPException(
                    status_code=403, 
                    detail=f"Access denied. Required roles: {', '.join(allowed_roles)}"
                )
            return await func(*args, **kwargs)
        return wrapper
    return decorator


@router.post("/auth/login", response_model=StaffLoginResponse)
async def staff_login(
    login_data: StaffLoginRequest = Body(...),
    request: Request = None,
    db: Session = Depends(get_db)
):
    """
    Staff login endpoint
    DC: Separate from MNR user authentication
    - Employee ID-based authentication (MR10001 format)
    - Account lockout protection
    - 2FA support
    - Default password = Employee ID (requires change on first login)
    """
    # Normalize employee ID (uppercase)
    emp_id = login_data.employee_id.upper().strip()
    
    # Search by employee code — emp_id already uppercased above, use exact match for index performance
    employee = db.query(StaffEmployee).filter(
        StaffEmployee.emp_code == emp_id
    ).first()
    
    if not employee:
        log_staff_audit(db, None, "LOGIN_FAILED", "auth", 
                       new_data={"employee_id": emp_id, "reason": "user_not_found"},
                       ip_address=request.client.host if request.client else None)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Employee ID or password"
        )
    
    # DC Protocol: Block login for deactivated/resigned employees (Dec 2025)
    if employee.status == 'deactivated':
        log_staff_audit(db, employee.id, "LOGIN_BLOCKED", "auth",
                       new_data={"emp_code": emp_id, "reason": "account_deactivated", "status": employee.status},
                       ip_address=request.client.host if request.client else None)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account temporarily suspended"
        )
    
    if employee.status == 'resigned':
        log_staff_audit(db, employee.id, "LOGIN_BLOCKED", "auth",
                       new_data={"emp_code": emp_id, "reason": "account_resigned", "status": employee.status},
                       ip_address=request.client.host if request.client else None)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account permanently deactivated"
        )
    
    # Block inactive/suspended/terminated statuses as well
    if employee.status not in ('active',):
        log_staff_audit(db, employee.id, "LOGIN_BLOCKED", "auth",
                       new_data={"emp_code": emp_id, "reason": f"account_{employee.status}", "status": employee.status},
                       ip_address=request.client.host if request.client else None)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Account is {employee.status}. Please contact administrator."
        )
    
    if employee.is_locked():
        remaining = (employee.locked_until - datetime.utcnow()).seconds // 60
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Account locked. Try again in {remaining} minutes."
        )
    
    if not SecurityManager.verify_password(login_data.password, employee.password_hash):
        employee.failed_login_attempts += 1
        max_attempts = get_staff_setting(db, 'max_login_attempts', 5)
        lockout_minutes = get_staff_setting(db, 'lockout_duration_minutes', 15)
        
        if employee.failed_login_attempts >= max_attempts:
            employee.locked_until = datetime.utcnow() + timedelta(minutes=lockout_minutes)
            log_staff_audit(db, employee.id, "ACCOUNT_LOCKED", "auth",
                           new_data={"attempts": employee.failed_login_attempts},
                           ip_address=request.client.host if request.client else None)
        
        db.commit()
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Employee ID or password"
        )
    
    if employee.totp_enabled and employee.totp_secret:
        if not login_data.totp_code:
            return StaffLoginResponse(
                success=False,
                message="2FA code required",
                requires_2fa=True
            )
        
        totp = pyotp.TOTP(employee.totp_secret)
        if not totp.verify(login_data.totp_code, valid_window=1):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid 2FA code"
            )
    
    employee.failed_login_attempts = 0
    employee.locked_until = None
    employee.last_login = datetime.utcnow()
    
    session_hours = get_staff_setting(db, 'session_timeout_hours', 24)
    token = SecurityManager.create_access_token(
        data={
            "sub": str(employee.id),
            "emp_code": employee.emp_code,
            "email": employee.email,
            "role": employee.role.role_code if employee.role else "junior_executive",
            "user_type": "staff"
        },
        expires_delta=timedelta(hours=session_hours)
    )
    
    log_staff_audit(db, employee.id, "LOGIN_SUCCESS", "auth",
                   new_data={"emp_code": employee.emp_code, "requires_password_change": employee.requires_password_change},
                   ip_address=request.client.host if request.client else None)
    db.commit()
    
    # DC Protocol (Dec 20, 2025): Auto-sync menu settings on login
    # Ensures employee has baseline menu settings even if bulk repair missed them
    try:
        from app.api.v1.endpoints.staff_menu_settings import sync_default_menu_settings_for_employees, get_employee_company_ids
        employee_companies = get_employee_company_ids(employee)
        sync_count = 0
        for company_id in employee_companies:
            created = sync_default_menu_settings_for_employees(
                db, company_id, [employee.id],
                admin_id=None,
                admin_code='SYSTEM',
                admin_name='Auto-Sync on Login'
            )
            sync_count += created
        if sync_count > 0:
            import logging
            logging.getLogger(__name__).info(f"[DC-LOGIN-SYNC] Created {sync_count} menu settings for {employee.emp_code} on login")
    except Exception as sync_err:
        import logging
        logging.getLogger(__name__).warning(f"[DC-LOGIN-SYNC] Menu sync failed for {employee.emp_code}: {sync_err}")
    
    # Build response with password change flag
    employee_data = employee.to_dict()
    
    # DC-AGREEMENT-TYPE-001: Check all pending agreements sequentially on login
    staff_type = employee.staff_type or 'MN_STAFF'
    
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"[DC-NDA-CHECK] Employee: {employee.emp_code}, Staff Type: {staff_type}")
    
    nda_required, first_pending_type, active_nda = check_all_pending_agreements(
        db, employee.id, staff_type
    )
    
    logger.info(f"[DC-NDA-CHECK] Result: nda_required={nda_required}, type={first_pending_type}, version_id={active_nda.id if active_nda else None}")
    
    _agreement_labels = {'NDA': 'Non-Disclosure Agreement', 'EMPLOYMENT': 'Employment Agreement'}
    
    message = "Login successful"
    if employee.requires_password_change:
        message = "Login successful. Password change required."
    elif nda_required:
        _lbl = _agreement_labels.get(first_pending_type or 'NDA', 'Agreement')
        message = f"Login successful. {_lbl} acceptance required."
    
    # Build agreement data if required
    nda_data = None
    if nda_required and active_nda:
        nda_data = {
            "id": active_nda.id,
            "version_number": active_nda.version_number,
            "title": active_nda.title,
            "content_html": active_nda.content_html,
            "applicable_staff_types": active_nda.applicable_staff_types or [],
            "document_type": active_nda.document_type or 'NDA',
            "agreement_type": first_pending_type or 'NDA',
            "agreement_label": _agreement_labels.get(first_pending_type or 'NDA', 'Non-Disclosure Agreement')
        }
        logger.info(f"[DC-NDA-CHECK] Agreement data built: type={first_pending_type}, content present: {bool(nda_data.get('content_html'))}")
    
    return StaffLoginResponse(
        success=True,
        message=message,
        access_token=token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        employee=employee_data,
        nda_required=nda_required,
        nda_version_id=active_nda.id if active_nda and nda_required else None,
        nda_version_number=active_nda.version_number if active_nda and nda_required else None,
        nda_data=nda_data
    )


@router.get("/auth/me", response_model=StaffProfileResponse)
async def get_staff_profile(
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """
    Get current staff user profile
    DC: Returns complete profile with role information + has_direct_reports flag
    """
    from app.utils.staff_hierarchy import has_direct_reports
    
    employee_data = current_user.to_dict()
    employee_data["has_direct_reports"] = has_direct_reports(current_user.id, db, StaffEmployee)
    
    return StaffProfileResponse(
        success=True,
        employee=employee_data
    )


@router.post("/auth/logout")
async def staff_logout(
    request: Request,
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """
    Staff logout endpoint
    DC: Logs logout action for audit trail
    """
    log_staff_audit(db, current_user.id, "LOGOUT", "auth",
                   ip_address=request.client.host if request.client else None)
    db.commit()
    
    return {
        "success": True,
        "message": "Logged out successfully"
    }


@router.post("/auth/refresh")
async def refresh_staff_token(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Refresh staff access token
    DC Protocol: Extends session without re-login
    - Validates current token (even if expired within grace period)
    - Issues new token with fresh expiry
    - Maintains audit trail
    """
    from jose import jwt, JWTError
    from jose.exceptions import ExpiredSignatureError
    
    auth_header = request.headers.get("Authorization")
    
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization header",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    token = auth_header.split(" ")[1]
    
    try:
        # DC Protocol: Allow refresh for tokens expired within 24-hour grace period
        # This enables session extension even if token just expired
        payload = jwt.decode(
            token, 
            settings.SECRET_KEY, 
            algorithms=[settings.ALGORITHM],
            options={"verify_exp": False}  # Allow expired tokens for refresh
        )
        
        # Validate token structure
        user_type = payload.get("user_type")
        if user_type != "staff":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type",
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        employee_id = payload.get("sub")
        if not employee_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload",
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        # Check token expiry - allow refresh within 24-hour grace period
        exp = payload.get("exp")
        if exp:
            exp_datetime = datetime.utcfromtimestamp(exp)
            grace_period = timedelta(hours=24)
            if datetime.utcnow() > exp_datetime + grace_period:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token expired beyond refresh window. Please login again.",
                    headers={"WWW-Authenticate": "Bearer"}
                )
        
        # Verify employee still exists and is active
        employee = db.query(StaffEmployee).filter_by(id=int(employee_id)).first()
        if not employee:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Employee not found",
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        if employee.status != 'active':
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Account is {employee.status}. Cannot refresh session."
            )
        
        if employee.is_locked():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is locked. Cannot refresh session."
            )
        
        # Generate new token with fresh expiry
        session_hours = get_staff_setting(db, 'session_timeout_hours', 24)
        new_token = SecurityManager.create_access_token(
            data={
                "sub": str(employee.id),
                "emp_code": employee.emp_code,
                "email": employee.email,
                "role": employee.role.role_code if employee.role else "junior_executive",
                "user_type": "staff"
            },
            expires_delta=timedelta(hours=session_hours)
        )
        
        # Log refresh for audit
        log_staff_audit(db, employee.id, "TOKEN_REFRESHED", "auth",
                       ip_address=request.client.host if request.client else None)
        db.commit()
        
        return {
            "success": True,
            "message": "Token refreshed successfully",
            "access_token": new_token,
            "token_type": "bearer",
            "expires_in_hours": session_hours
        }
        
    except HTTPException:
        raise
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token format. Please login again.",
            headers={"WWW-Authenticate": "Bearer"}
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not refresh token. Please login again.",
            headers={"WWW-Authenticate": "Bearer"}
        )


@router.get("/auth/roles")
async def get_staff_roles(db: Session = Depends(get_db)):
    """
    Get all staff roles (public for login page role display)
    DC: Reference data endpoint
    """
    roles = db.query(StaffRole).filter_by(is_active=True).order_by(StaffRole.hierarchy_level.desc()).all()
    return {
        "success": True,
        "roles": [role.to_dict() for role in roles]
    }


@router.post("/auth/change-password")
async def change_staff_password(
    request: Request,
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """
    Change staff password
    DC: Password change with audit logging
    """
    body = await request.json()
    current_password = body.get("current_password")
    new_password = body.get("new_password")
    
    if not current_password or not new_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current and new password are required"
        )
    
    if not SecurityManager.verify_password(current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Current password is incorrect"
        )
    
    min_length = get_staff_setting(db, 'password_min_length', 12)
    if len(new_password) < min_length:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Password must be at least {min_length} characters"
        )
    
    current_user.password_hash = SecurityManager.get_password_hash(new_password)
    current_user.last_password_change = datetime.utcnow()
    
    log_staff_audit(db, current_user.id, "PASSWORD_CHANGED", "employee", 
                   resource_id=current_user.id,
                   ip_address=request.client.host if request.client else None)
    db.commit()
    
    return {
        "success": True,
        "message": "Password changed successfully"
    }


@router.post("/auth/setup-2fa")
async def setup_staff_2fa(
    request: Request,
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """
    Setup 2FA for staff account
    DC: Generates TOTP secret and QR code
    """
    if current_user.totp_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="2FA is already enabled"
        )
    
    secret = pyotp.random_base32()
    current_user.totp_secret = secret
    
    totp = pyotp.TOTP(secret)
    provisioning_uri = totp.provisioning_uri(
        name=current_user.email,
        issuer_name="MNR Staff Portal"
    )
    
    db.commit()
    
    return {
        "success": True,
        "secret": secret,
        "provisioning_uri": provisioning_uri,
        "message": "Scan the QR code with your authenticator app, then verify"
    }


@router.post("/auth/verify-2fa")
async def verify_staff_2fa(
    request: Request,
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """
    Verify and enable 2FA
    DC: Completes 2FA setup after verification
    """
    body = await request.json()
    totp_code = body.get("totp_code")
    
    if not totp_code or not current_user.totp_secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid request. Setup 2FA first."
        )
    
    totp = pyotp.TOTP(current_user.totp_secret)
    if not totp.verify(totp_code, valid_window=1):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid 2FA code"
        )
    
    current_user.totp_enabled = True
    
    log_staff_audit(db, current_user.id, "2FA_ENABLED", "employee",
                   resource_id=current_user.id,
                   ip_address=request.client.host if request.client else None)
    db.commit()
    
    return {
        "success": True,
        "message": "2FA enabled successfully"
    }


@router.post("/auth/disable-2fa")
async def disable_staff_2fa(
    request: Request,
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """
    Disable 2FA (requires current password)
    DC: Removes 2FA with password verification
    """
    body = await request.json()
    password = body.get("password")
    
    if not password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password is required to disable 2FA"
        )
    
    if not SecurityManager.verify_password(password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid password"
        )
    
    current_user.totp_enabled = False
    current_user.totp_secret = None
    
    log_staff_audit(db, current_user.id, "2FA_DISABLED", "employee",
                   resource_id=current_user.id,
                   ip_address=request.client.host if request.client else None)
    db.commit()
    
    return {
        "success": True,
        "message": "2FA disabled successfully"
    }


# ==================== SIDEBAR ENDPOINT ====================

@router.get("/sidebar", summary="Get staff sidebar context (DC Protocol)")
def get_sidebar(
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """
    Get current staff user's sidebar context
    DC Protocol: Single source of truth for user context
    WVV Protocol: Immutable context for audit trails
    """
    return {
        "success": True,
        "user_id": current_user.id,
        "user_name": current_user.full_name,
        "user_role": current_user.role.role_name if current_user.role else "Unknown",
        "user_role_code": current_user.role.role_code if current_user.role else "unknown",
        "department": current_user.department.name if current_user.department else "N/A",
        "team_manager": current_user.reporting_manager.full_name if current_user.reporting_manager else "N/A",
        "hierarchy_level": current_user.role.hierarchy_level if current_user.role else 0
    }


# DC_APP_VERSION_001 (Jan 28, 2026): Mobile app version check endpoint
@router.get("/app/version-check", summary="Check if app version is supported")
def check_app_version(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Check if the current app version is supported.
    Returns update requirements and latest version info.
    
    Mobile apps should call this on startup to determine if force update is needed.
    """
    # Get version from headers
    current_version = request.headers.get("X-App-Version", "0.0.0")
    app_platform = request.headers.get("X-App-Platform", "unknown")
    
    # Configuration - can be moved to database settings later
    MIN_SUPPORTED_VERSION = "1.0.0"
    LATEST_VERSION = "1.0.0"
    FORCE_UPDATE_BELOW = "0.9.0"  # Force update for versions below this
    
    def parse_version(v: str) -> tuple:
        """Parse version string into comparable tuple"""
        try:
            parts = v.split('+')[0].split('.')  # Remove build number suffix
            return tuple(int(p) for p in parts[:3])
        except:
            return (0, 0, 0)
    
    current = parse_version(current_version)
    min_supported = parse_version(MIN_SUPPORTED_VERSION)
    force_below = parse_version(FORCE_UPDATE_BELOW)
    
    is_supported = current >= min_supported
    force_update = current < force_below
    
    return {
        "success": True,
        "current_version": current_version,
        "platform": app_platform,
        "latest_version": LATEST_VERSION,
        "min_supported_version": MIN_SUPPORTED_VERSION,
        "is_supported": is_supported,
        "force_update_required": force_update,
        "update_message": "Please update to the latest version for best experience" if not is_supported else None,
        "download_url": "https://mnrteam.com/app/download" if force_update else None
    }


@router.get("/app/team-versions", summary="Get app versions used by team members")
def get_team_app_versions(
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Get app versions used by team members (for managers to track adoption).
    Shows which version each team member is using based on their last GPS submission.
    """
    from app.models.staff_attendance import StaffRealtimeLocation
    from sqlalchemy import func, and_
    from app.utils.staff_hierarchy import get_accessible_employee_ids
    
    # Get accessible employee IDs
    accessible_ids = get_accessible_employee_ids(current_user, db, StaffEmployee)
    
    if not accessible_ids:
        return {
            "success": True,
            "team_versions": [],
            "summary": {"total": 0}
        }
    
    # Get latest location with app version for each employee
    latest_subq = db.query(
        StaffRealtimeLocation.employee_id,
        func.max(StaffRealtimeLocation.captured_at).label('max_captured')
    ).filter(
        StaffRealtimeLocation.employee_id.in_(accessible_ids),
        StaffRealtimeLocation.app_version.isnot(None)
    ).group_by(StaffRealtimeLocation.employee_id).subquery()
    
    latest_locs = db.query(StaffRealtimeLocation).join(
        latest_subq,
        and_(
            StaffRealtimeLocation.employee_id == latest_subq.c.employee_id,
            StaffRealtimeLocation.captured_at == latest_subq.c.max_captured
        )
    ).all()
    
    # Build response
    team_versions = []
    version_counts = {}
    
    for loc in latest_locs:
        emp = db.query(StaffEmployee).filter(StaffEmployee.id == loc.employee_id).first()
        if emp:
            version = loc.app_version or "Unknown"
            team_versions.append({
                "employee_id": emp.id,
                "emp_code": emp.emp_code,
                "full_name": emp.full_name,
                "app_version": version,
                "app_platform": loc.app_platform,
                "last_seen": loc.captured_at.isoformat() if loc.captured_at else None
            })
            version_counts[version] = version_counts.get(version, 0) + 1
    
    # Add employees without app version data
    employees_with_data = {v["employee_id"] for v in team_versions}
    for emp_id in accessible_ids:
        if emp_id not in employees_with_data:
            emp = db.query(StaffEmployee).filter(StaffEmployee.id == emp_id).first()
            if emp and emp.status == 'active':
                team_versions.append({
                    "employee_id": emp.id,
                    "emp_code": emp.emp_code,
                    "full_name": emp.full_name,
                    "app_version": None,
                    "app_platform": None,
                    "last_seen": None
                })
                version_counts["No Data"] = version_counts.get("No Data", 0) + 1
    
    return {
        "success": True,
        "team_versions": team_versions,
        "version_summary": version_counts,
        "total_team": len(team_versions)
    }
