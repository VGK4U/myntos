"""
Staff Authentication API Endpoints (DC Protocol Compliant)
Separate authentication system for staff members
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request, Body
from sqlalchemy.orm import Session, joinedload
from datetime import datetime, timedelta
from typing import Optional, Any, List, Dict, Union
from pydantic import BaseModel, EmailStr, Field
import pyotp

import secrets
import hashlib

from app.core.database import get_db, SessionLocal
from app.core.security import SecurityManager
from app.core.config import settings
from app.models.staff import (
    StaffEmployee, StaffRole, StaffDepartment, StaffSetting, 
    StaffAuditLog, log_staff_audit, check_nda_acceptance, check_all_pending_agreements
)
from app.models.staff_accounts import AssociatedCompany
from app.models.mobile_device_session import MobileDeviceSession
from app.models.mobile_device_push_token import MobileDevicePushToken
from app.core.timezone import get_indian_time

router = APIRouter(prefix="/staff", tags=["Staff Auth"])


class StaffLoginRequest(BaseModel):
    employee_id: str = Field(..., min_length=1, description="Employee ID (e.g., MR10001)")
    password: str = Field(..., min_length=1)
    totp_code: Optional[str] = Field(None, min_length=6, max_length=6)
    device_id: Optional[str] = Field(None, description="Mobile device unique hardware UUID")
    platform: Optional[str] = Field(None, description="'android' | 'ios' | 'web'")
    device_name: Optional[str] = None
    app_version: Optional[str] = None


class StaffLoginResponse(BaseModel):
    success: bool
    message: str
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    expires_in: Optional[int] = None
    requires_2fa: bool = False
    employee: Optional[dict] = None
    nda_required: bool = False
    nda_version_id: Optional[int] = None
    nda_version_number: Optional[str] = None
    nda_data: Optional[dict] = None


class StaffMobileRefreshRequest(BaseModel):
    refresh_token: str = Field(..., min_length=16, description="Mobile rotating refresh token")
    device_id: str = Field(..., min_length=1, description="Device UUID")


class StaffMobileRevokeRequest(BaseModel):
    refresh_token: Optional[str] = None
    device_id: Optional[str] = None
    revoke_all_devices: bool = False


class StaffProfileResponse(BaseModel):
    success: bool
    employee: dict


_SETTINGS_CACHE = {}
_SETTINGS_CACHE_TTL = 300  # 5 minutes

def get_staff_setting(db: Session, key: str, default=None):
    """Get staff setting value with in-memory TTL caching"""
    import time
    now = time.time()
    cached = _SETTINGS_CACHE.get(key)
    if cached and (now - cached[0]) < _SETTINGS_CACHE_TTL:
        return cached[1]
    
    try:
        setting = db.query(StaffSetting).filter_by(setting_key=key, is_active=True).first()
        if setting:
            val = setting.get_value()
            _SETTINGS_CACHE[key] = (now, val)
            return val
    except Exception:
        pass
        
    _SETTINGS_CACHE[key] = (now, default)
    return default


def get_current_staff_user(request: Request, db: Session = Depends(get_db)) -> StaffEmployee:
    """
    Dependency to get current authenticated staff user from JWT token
    DC: Validates token and ensures staff user exists
    DC Protocol (Dec 05, 2025): NDA enforcement - blocks all access until NDA accepted
    """
    auth_header = request.headers.get("Authorization")
    
    if not auth_header or not auth_header.strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization header",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    # Strip all leading 'Bearer ' prefixes (handles duplicate 'Bearer Bearer ...') and extra quotes
    token = auth_header.strip()
    while token.lower().startswith("bearer "):
        token = token[7:].strip()
    token = token.strip('"').strip("'")
    
    if not token or token.lower() in ("null", "undefined", "none", "[object object]", ""):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    try:
        from jose import jwt, JWTError
        from jose.exceptions import ExpiredSignatureError
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        
        employee_id = payload.get("sub") or payload.get("employee_id") or payload.get("user_id")
        emp_code = payload.get("emp_code")
        
        if not employee_id and not emp_code:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload",
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        employee = None
        emp_query = db.query(StaffEmployee).options(
            joinedload(StaffEmployee.role),
            joinedload(StaffEmployee.department),
            joinedload(StaffEmployee.base_company)
        )
        if employee_id and str(employee_id).isdigit():
            employee = emp_query.filter_by(id=int(employee_id)).first()
        if not employee and emp_code:
            employee = emp_query.filter_by(emp_code=str(emp_code)).first()
        if not employee and employee_id:
            employee = emp_query.filter_by(emp_code=str(employee_id)).first()
            
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
        
        # Stage 2A: Live token_version revocation verification
        tok_ver = payload.get("token_version")
        db_tok_ver = getattr(employee, "token_version", 1) or 1
        if tok_ver is not None and int(tok_ver) != db_tok_ver:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session has been revoked or expired. Please log in again.",
                headers={"WWW-Authenticate": "Bearer", "X-Token-Revoked": "true"}
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
        
        # DC Protocol (ARCHITECTURAL FIX - Sep 2026):
        # Deterministically end read transaction before returning to downstream route.
        # This guarantees AccessShareLock on staff_employees is NOT held while downstream route handlers
        # perform serialization, network transfers, or CPU calculations.
        try:
            db.rollback()
        except Exception:
            pass

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
        import logging
        from sqlalchemy.exc import SQLAlchemyError
        if isinstance(e, SQLAlchemyError) or "connection" in str(e).lower() or "timeout" in str(e).lower() or "operationalerror" in str(e).lower():
            logging.getLogger(__name__).error(f"[STAFF-AUTH-DB] Database dependency unavailable during authentication: {e}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Authentication database service temporarily unavailable. Please try again."
            )
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


def resolve_tenant_company_for_request(
    current_user: Any,
    requested_company_id: Optional[int] = None,
    db: Optional[Session] = None
) -> int:
    """
    Authoritatively resolve target company_id for an authenticated staff request (Stage 2B).
    
    Architecture Standards:
    - Never uses base_company_id as operational authorization (Rule #4).
    - Uses RequestContext and active staff_company_memberships (ctx.accessible_company_ids).
    - Permits active secondary memberships if caller requested that company.
    - Defaults to the primary operational membership when no company is requested.
    - Multiple primary memberships fail safely with HTTP 403 unless explicitly selected.
    - Inactive or non-existent memberships are denied with HTTP 403.
    - Cross-tenant company requests are strictly denied with HTTP 403.
    - Platform Superadmin is allowed cross-company / cross-tenant scope with DB existence check.
    """
    from app.core.context import RequestContext, AdminScope, get_current_request_context
    from app.services.auth_context_service import resolve_admin_scope
    from app.models.staff import StaffCompanyMembership
    from app.models.staff_accounts import AssociatedCompany

    # Normalize requested_company_id (sanitize 0, negative, empty string)
    req_cid: Optional[int] = None
    if requested_company_id is not None:
        try:
            val = int(requested_company_id)
            if val > 0:
                req_cid = val
        except (ValueError, TypeError):
            pass

    # 1. Check if current_user is already a RequestContext
    if isinstance(current_user, RequestContext):
        ctx = current_user
        if req_cid is not None:
            if ctx.is_platform_admin():
                return req_cid
            if req_cid in ctx.accessible_company_ids:
                return req_cid
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied to company #{req_cid}. Not an active member or cross-tenant company."
            )
        # Default when no company explicitly requested
        return ctx.active_company_id

    # 2. Check if a RequestContext is bound in the current async task ContextVar
    bound_ctx = get_current_request_context()
    if bound_ctx is not None and (
        getattr(current_user, "id", None) == bound_ctx.staff_id or
        getattr(current_user, "emp_code", None) == bound_ctx.emp_code
    ):
        if req_cid is not None:
            if bound_ctx.is_platform_admin():
                return req_cid
            if req_cid in bound_ctx.accessible_company_ids:
                return req_cid
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied to company #{req_cid}. Not an active member or cross-tenant company."
            )
        return bound_ctx.active_company_id

    # 3. Direct DB-backed resolution (fallback for background tasks / direct model calls)
    tenant_id = getattr(current_user, "tenant_id", None)
    if tenant_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Staff employee has no associated tenant context."
        )

    # Verify active account status
    staff_status = getattr(current_user, "status", "active")
    if staff_status != "active" or getattr(current_user, "is_deleted", False):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Staff account is {staff_status}. Access denied."
        )

    if db is None:
        from sqlalchemy.orm import object_session
        db = object_session(current_user)
    if db is None:
        from app.core.database import SessionLocal
        local_db = SessionLocal()
        try:
            return resolve_tenant_company_for_request(current_user, requested_company_id, db=local_db)
        finally:
            local_db.close()

    admin_scope = resolve_admin_scope(current_user)
    is_platform_super = (admin_scope == AdminScope.PLATFORM_SUPERADMIN)

    # Query active operational memberships in staff_company_memberships
    active_memberships = db.query(StaffCompanyMembership).filter(
        StaffCompanyMembership.staff_id == current_user.id,
        StaffCompanyMembership.tenant_id == tenant_id,
        StaffCompanyMembership.is_active == True
    ).all()

    accessible_cids = [m.company_id for m in active_memberships]

    # Explicit company requested
    if req_cid is not None:
        if is_platform_super:
            comp = db.query(AssociatedCompany).filter(AssociatedCompany.id == req_cid).first()
            if not comp:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Company #{req_cid} not found.")
            return req_cid

        if req_cid in accessible_cids:
            # Verify company belongs to authenticated tenant (anti-cross-tenant check)
            comp = db.query(AssociatedCompany).filter(
                AssociatedCompany.id == req_cid,
                AssociatedCompany.client_id == tenant_id
            ).first()
            if not comp:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Cross-tenant access forbidden. Company #{req_cid} does not belong to tenant #{tenant_id}."
                )
            return req_cid

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied to company #{req_cid}. No active operational membership."
        )

    # No company explicitly requested: default to single active primary membership
    if not accessible_cids:
        if is_platform_super:
            platform_comp = db.query(AssociatedCompany).filter(AssociatedCompany.client_id == 1).first()
            return platform_comp.id if platform_comp else 1
        # Rule #4: base_company_id alone cannot grant access
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No operational company access. Staff employee has no active company memberships."
        )

    primary_memberships = [m for m in active_memberships if m.is_primary]
    if len(primary_memberships) == 1:
        prim_cid = primary_memberships[0].company_id
        if not is_platform_super:
            comp = db.query(AssociatedCompany).filter(
                AssociatedCompany.id == prim_cid,
                AssociatedCompany.client_id == tenant_id
            ).first()
            if not comp:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Primary company #{prim_cid} does not belong to tenant #{tenant_id}."
                )
        return prim_cid

    if len(primary_memberships) > 1:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Multiple primary company memberships found. Ambiguous primary company context."
        )

    # 0 primary memberships
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="No primary company membership resolved. Explicit company selection required."
    )


def require_module_entitlement(module_code: str):
    """
    FastAPI route dependency that validates the authenticated staff's tenant subscription
    has active entitlement for the specified module_code.
    """
    def _entitlement_guard(
        request: Request,
        db: Session = Depends(get_db),
        current_user: StaffEmployee = Depends(get_current_staff_user)
    ) -> StaffEmployee:
        from app.services.b2b_shadow import resolve_client_id_for_staff, is_module_entitled
        role_code = (current_user.role.role_code.lower() if current_user.role and current_user.role.role_code else "")
        is_super = getattr(current_user, "is_super_admin", False) or role_code in {"super_admin", "vgk4u", "vgk4u_supreme"} or (current_user.role and getattr(current_user.role, "hierarchy_level", 0) >= 90)
        if is_super:
            return current_user

        client_id = resolve_client_id_for_staff(db, current_user)
        if not client_id:
            raise HTTPException(status_code=403, detail="Service not enabled for this tenant.")

        if not is_module_entitled(db, client_id, module_code, user_id=current_user.id, user_type="staff", route=str(request.url.path), strict=True):
            raise HTTPException(status_code=403, detail="Service not enabled for this tenant.")

        return current_user

    return _entitlement_guard



@router.post("/auth/login", response_model=StaffLoginResponse)
def staff_login(
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
    import time, re
    t0 = time.time()
    # Normalize employee ID / login identifier
    raw_ident = (login_data.employee_id or "").strip()
    emp_id = raw_ident.upper()
    employee = None
    
    t_lookup_start = time.time()
    
    def _do_lookup(session):
        from sqlalchemy import text
        try:
            session.execute(text("SET LOCAL statement_timeout = '15000ms'"))
        except Exception:
            pass

        # 1. Exact Employee Code / Username Match (e.g. MR10001, ZMP18080088, TECO_ADMIN)
        emp = session.query(StaffEmployee).options(
            joinedload(StaffEmployee.role),
            joinedload(StaffEmployee.department),
            joinedload(StaffEmployee.base_company),
            joinedload(StaffEmployee.reporting_manager)
        ).filter(
            StaffEmployee.is_deleted == False,
            StaffEmployee.emp_code == emp_id
        ).first()

        # 1b. Email Match if raw_ident looks like email
        if not emp and "@" in raw_ident:
            emp = session.query(StaffEmployee).options(
                joinedload(StaffEmployee.role),
                joinedload(StaffEmployee.department),
                joinedload(StaffEmployee.base_company),
                joinedload(StaffEmployee.reporting_manager)
            ).filter(
                StaffEmployee.is_deleted == False,
                StaffEmployee.email.ilike(raw_ident)
            ).first()

        # 2. Company ID Login Pattern (e.g., ZMP18080088, ZMP18080092... ZMP1808XXXX)
        if not emp:
            company_id_match = re.match(r"^ZMP1808(\d{4})$", emp_id)
            if company_id_match:
                target_company_id = int(company_id_match.group(1))
                # Company 88 / SaaS Segment Administrator
                if target_company_id == 88:
                    emp = session.query(StaffEmployee).options(joinedload(StaffEmployee.role)).filter(
                        StaffEmployee.is_deleted == False,
                        StaffEmployee.base_company_id == 88,
                        StaffEmployee.staff_type == 'SAAS_SEGMENT_ADMIN',
                        StaffEmployee.status == 'active'
                    ).first()
                if not emp:
                    base_emps = session.query(StaffEmployee).options(joinedload(StaffEmployee.role)).filter(
                        StaffEmployee.is_deleted == False,
                        StaffEmployee.base_company_id == target_company_id,
                        StaffEmployee.status == 'active'
                    ).order_by(StaffEmployee.id).all()
                    ta_emps = [e for e in base_emps if (e.role_id == 17 or getattr(e, 'role', None) and e.role.role_code in ['tenant_admin', 'saas_segment_admin'] or getattr(e, 'staff_type', '') in ['TENANT_ADMIN', 'SAAS_SEGMENT_ADMIN', 'SAAS_CLIENT'] or any(k in ((getattr(e, 'designation', '') or '') + (e.role.role_name if e.role else '')).upper() for k in ['ADMIN', 'MANAGER', 'LEAD', 'DIRECTOR', 'HEAD']))]
                    if ta_emps:
                        emp = ta_emps[0]
                    elif base_emps:
                        emp = base_emps[0]

        # 3. Mobile Number Login (e.g. 10 digits or with country code +91)
        if not emp:
            clean_phone = re.sub(r"\D", "", raw_ident)
            if len(clean_phone) >= 10:
                last10 = clean_phone[-10:]
                emp = session.query(StaffEmployee).options(joinedload(StaffEmployee.role)).filter(
                    StaffEmployee.is_deleted == False,
                    StaffEmployee.phone.like(f"%{last10}")
                ).first()

        # 4. Fallback Code / Email Login
        if not emp:
            emp = session.query(StaffEmployee).options(
                joinedload(StaffEmployee.role)
            ).filter(
                (StaffEmployee.emp_code == emp_id) | (StaffEmployee.email.ilike(raw_ident))
            ).first()
        return emp

    try:
        employee = _do_lookup(db)
    except Exception as db_exc:
        # Retry once on a fresh session if initial checkout had a dropped/stale socket
        try:
            try: db.rollback()
            except Exception: pass
            fresh_db = SessionLocal()
            try:
                employee = _do_lookup(fresh_db)
                db = fresh_db
            except Exception:
                try: fresh_db.close()
                except Exception: pass
                raise
        except Exception as retry_exc:
            import logging
            logging.getLogger(__name__).error(f"[STAFF-AUTH-DB] Database connection error during login (after retry): {retry_exc}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Authentication service temporarily unavailable. Please try again in a moment."
            )
    t_lookup_ms = (time.time() - t_lookup_start) * 1000
    
    if not employee:
        log_staff_audit(db, None, "LOGIN_FAILED", "auth", 
                       new_data={"employee_id": raw_ident, "reason": "user_not_found"},
                       ip_address=request.client.host if request.client else None)
        try:
            db.commit()
        except Exception:
            db.rollback()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Company ID, Mobile Number, or password"
        )
    
    # DC Protocol: Block login for deactivated/resigned employees (Dec 2025)
    if employee.status == 'deactivated':
        log_staff_audit(db, employee.id, "LOGIN_BLOCKED", "auth",
                       new_data={"emp_code": emp_id, "reason": "account_deactivated", "status": employee.status},
                       ip_address=request.client.host if request.client else None)
        try:
            db.commit()
        except Exception:
            db.rollback()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account temporarily suspended"
        )
    
    if employee.status == 'resigned':
        log_staff_audit(db, employee.id, "LOGIN_BLOCKED", "auth",
                       new_data={"emp_code": emp_id, "reason": "account_resigned", "status": employee.status},
                       ip_address=request.client.host if request.client else None)
        try:
            db.commit()
        except Exception:
            db.rollback()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account permanently deactivated"
        )
    
    # Block inactive/suspended/terminated statuses as well
    if employee.status not in ('active',):
        log_staff_audit(db, employee.id, "LOGIN_BLOCKED", "auth",
                       new_data={"emp_code": emp_id, "reason": f"account_{employee.status}", "status": employee.status},
                       ip_address=request.client.host if request.client else None)
        try:
            db.commit()
        except Exception:
            db.rollback()
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
    
    # DC Protocol (ARCHITECTURAL FIX - Sep 2026):
    # Release lookup read transaction before CPU-intensive bcrypt password verification.
    # DB connection remains idle without holding AccessShareLock on staff_employees during bcrypt.
    try:
        db.rollback()
    except Exception:
        pass

    t_pw_start = time.time()
    raw_pw = login_data.password or ""
    clean_pw = raw_pw.strip()
    pw_ok = SecurityManager.verify_password(raw_pw, employee.password_hash) or (clean_pw != raw_pw and SecurityManager.verify_password(clean_pw, employee.password_hash))
    t_pw_ms = (time.time() - t_pw_start) * 1000
    
    if not pw_ok:
        employee.failed_login_attempts += 1
        max_attempts = get_staff_setting(db, 'max_login_attempts', 5)
        lockout_minutes = get_staff_setting(db, 'lockout_duration_minutes', 15)
        
        if employee.failed_login_attempts >= max_attempts:
            employee.locked_until = datetime.utcnow() + timedelta(minutes=lockout_minutes)
            log_staff_audit(db, employee.id, "ACCOUNT_LOCKED", "auth",
                           new_data={"attempts": employee.failed_login_attempts},
                           ip_address=request.client.host if request and request.client else None)
        
        try:
            db.commit()
        except Exception:
            db.rollback()
        
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
    
    t_token_start = time.time()
    # 365-Day Persistent Session for Mobile & Staff Logins (prevents premature auto-logouts)
    session_hours = get_staff_setting(db, 'session_timeout_hours', 8760)
    token = SecurityManager.create_access_token(
        data={
            "sub": str(employee.id),
            "emp_code": employee.emp_code,
            "email": employee.email,
            "role": employee.role.role_code if employee.role else "junior_executive",
            "staff_type": getattr(employee, "staff_type", "MN_STAFF"),
            "admin_scope": getattr(employee, "admin_scope", "CLIENT_SPECIFIC"),
            "base_company_id": employee.base_company_id,
            "tenant_id": getattr(employee, "tenant_id", 1) or 1,
            "token_version": getattr(employee, "token_version", 1) or 1,
            "team_tag": employee.team_tag,
            "user_type": "staff"
        },
        expires_delta=timedelta(hours=session_hours)
    )
    t_token_ms = (time.time() - t_token_start) * 1000
    
    log_staff_audit(db, employee.id, "LOGIN_SUCCESS", "auth",
                   new_data={"emp_code": employee.emp_code, "requires_password_change": employee.requires_password_change},
                   ip_address=request.client.host if request.client else None)
    try:
        db.commit()
    except Exception:
        db.rollback()
    
    # Extract employee data dictionary safely
    employee_data = employee.to_dict()
    try:
        from app.services.auth_context_service import resolve_staff_memberships
        acc_cids, prim_cid = resolve_staff_memberships(db, employee.id, getattr(employee, "tenant_id", 1) or 1)
        employee_data["accessible_company_ids"] = acc_cids
        employee_data["primary_company_id"] = prim_cid
    except Exception:
        pass
    try:
        from app.services.telephony.flow_interpreter import CallFlowInterpreter
        employee_data["extension"] = CallFlowInterpreter.get_staff_configured_extension(
            db, employee.base_company_id or 1, employee.id
        )
    except Exception:
        employee_data["extension"] = None
    
    # P0 LOGIN REMEDIATION: Dynamic Menu Sync removed from authentication request path.
    # Menu provisioning is an administrative/seed event, not an authentication prerequisite.
    t_sync_ms = 0.0
    
    # DC-AGREEMENT-TYPE-001: Check all pending agreements sequentially on login
    staff_type = employee.staff_type or 'MN_STAFF'
    t_nda_start = time.time()
    nda_required, first_pending_type, active_nda = check_all_pending_agreements(
        db, employee.id, staff_type
    )
    t_nda_ms = (time.time() - t_nda_start) * 1000
    
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
    
    total_ms = (time.time() - t0) * 1000
    print(f"[LOGIN TRACE] Total: {total_ms:.1f}ms (lookup: {t_lookup_ms:.1f}ms, pw: {t_pw_ms:.1f}ms, token: {t_token_ms:.1f}ms, sync: {t_sync_ms:.1f}ms, nda: {t_nda_ms:.1f}ms)", flush=True)
    
    # DC Protocol: Mobile Persistent Device Session (Rotating Refresh Token)
    mobile_refresh_token = None
    if getattr(login_data, 'device_id', None):
        try:
            mobile_refresh_token = secrets.token_hex(32)
            h = hashlib.sha256(mobile_refresh_token.encode()).hexdigest()
            now_ist = get_indian_time()
            expires_ist = now_ist + timedelta(days=180)
            existing_sess = db.query(MobileDeviceSession).filter_by(
                staff_id=employee.id,
                device_id=login_data.device_id
            ).with_for_update().first()
            if existing_sess:
                existing_sess.refresh_token_hash = h
                existing_sess.platform = login_data.platform or existing_sess.platform or 'android'
                existing_sess.device_name = login_data.device_name or existing_sess.device_name
                existing_sess.app_version = login_data.app_version or existing_sess.app_version
                existing_sess.token_version = getattr(employee, "token_version", 1) or 1
                existing_sess.is_revoked = False
                existing_sess.expires_at = expires_ist
                existing_sess.last_used_at = now_ist
            else:
                new_sess = MobileDeviceSession(
                    staff_id=employee.id,
                    device_id=login_data.device_id,
                    platform=login_data.platform or 'android',
                    refresh_token_hash=h,
                    device_name=login_data.device_name,
                    app_version=login_data.app_version,
                    token_version=getattr(employee, "token_version", 1) or 1,
                    is_revoked=False,
                    expires_at=expires_ist,
                    last_used_at=now_ist,
                    created_at=now_ist
                )
                db.add(new_sess)
            db.commit()
        except Exception as _e:
            print(f"[LOGIN MOBILE SESS ERROR] {_e}", flush=True)
            db.rollback()

    # DC Protocol (ARCHITECTURAL FIX - Sep 2026):
    # Deterministically end session transaction before returning response.
    # Ensures zero locks are held while FastAPI serializes JSON or sends response over network.
    try:
        db.rollback()
    except Exception:
        pass

    return StaffLoginResponse(
        success=True,
        message=message,
        access_token=token,
        refresh_token=mobile_refresh_token,
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
    DC: Returns complete profile with role information, direct reports, and active tenant entitlements
    """
    from app.utils.staff_hierarchy import has_direct_reports
    from app.services.b2b_shadow import resolve_client_id_for_staff
    from app.models.platform_b2b import PlatformSubscription, PlatformSubscriptionModule, PlatformModule, PlatformClient

    employee_data = current_user.to_dict()
    employee_data["has_direct_reports"] = has_direct_reports(current_user.id, db, StaffEmployee)
    try:
        from app.services.telephony.flow_interpreter import CallFlowInterpreter
        employee_data["extension"] = CallFlowInterpreter.get_staff_configured_extension(
            db, current_user.base_company_id or 1, current_user.id
        )
    except Exception:
        employee_data["extension"] = None

    # Resolve tenant & active entitlements
    cid = resolve_client_id_for_staff(db, current_user)
    employee_data["client_id"] = cid
    entitled_codes = []
    client_code = None

    if cid:
        client_obj = db.query(PlatformClient).filter_by(id=cid).first()
        if client_obj:
            client_code = client_obj.client_code
        
        sub_ids = [s.id for s in db.query(PlatformSubscription).filter(
            PlatformSubscription.client_id == cid,
            PlatformSubscription.status.in_(["active", "trial"])
        ).all()]
        if sub_ids:
            psm_rows = db.query(PlatformSubscriptionModule, PlatformModule).join(
                PlatformModule, PlatformSubscriptionModule.module_id == PlatformModule.id
            ).filter(
                PlatformSubscriptionModule.subscription_id.in_(sub_ids),
                PlatformSubscriptionModule.enabled == True
            ).all()
            for _psm, pm in psm_rows:
                entitled_codes.append(pm.module_code)

    employee_data["client_code"] = client_code
    employee_data["entitled_modules"] = list(set(entitled_codes))

    role_code = (getattr(current_user.role, "role_code", "") or "").upper()
    role_level = int(getattr(current_user.role, "hierarchy_level", 0) or 0)
    employee_data["is_super_admin"] = bool(
        role_level >= 90 or role_code in {"SUPER_ADMIN", "B2B_SUPER_ADMIN", "CEO", "CTO", "FOUNDER"}
    )
    employee_data["is_tenant_admin"] = bool(
        role_code == "TENANT_ADMIN" or role_level == 85
    )

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
    # Stage 2A: Bump token_version to immediately revoke all existing JWTs
    current_user.token_version = (getattr(current_user, "token_version", 1) or 1) + 1
    
    from app.services.auth_context_service import invalidate_auth_cache
    invalidate_auth_cache(current_user.id)
    
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
                "team_tag": employee.team_tag,
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


@router.post("/auth/mobile/refresh")
async def refresh_staff_mobile_session(
    payload: StaffMobileRefreshRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Rotating Refresh Token Endpoint for MyntOS Mobile App.
    - Validates hardware-stored refresh token and device UUID.
    - Rotates the refresh token (one-time use, replacing with new random 64-byte hex token).
    - Checks staff active status, lock state, and token_version.
    - Invalidates session if employee token_version has been bumped (password changed or logged out).
    - Extends 180-day sliding window.
    - Returns fresh 30-minute access token and new rotated refresh token.
    """
    clean_token = (payload.refresh_token or "").strip()
    clean_device = (payload.device_id or "").strip()
    if not clean_token or not clean_device:
        raise HTTPException(status_code=400, detail="refresh_token and device_id are required")

    h = hashlib.sha256(clean_token.encode()).hexdigest()
    session = db.query(MobileDeviceSession).filter_by(
        refresh_token_hash=h,
        device_id=clean_device
    ).with_for_update().first()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or unrecognized mobile session. Please login again.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    if session.is_revoked:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session has been revoked. Please login again.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    now_ist = get_indian_time()
    if session.expires_at <= now_ist:
        session.is_revoked = True
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Mobile session expired. Please login again.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    employee = db.query(StaffEmployee).filter_by(id=session.staff_id).first()
    if not employee:
        session.is_revoked = True
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Staff employee record not found.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    if employee.status != 'active':
        session.is_revoked = True
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Account is {employee.status}. Access denied.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    is_locked = employee.is_locked() if callable(getattr(employee, 'is_locked', None)) else bool(getattr(employee, 'is_locked', False))
    if is_locked:
        session.is_revoked = True
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account is locked. Access denied.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    db_token_version = getattr(employee, "token_version", 1) or 1
    if session.token_version < db_token_version:
        session.is_revoked = True
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session revoked due to password change or security update. Please login again.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    # 1. Rotate refresh token (One-time use)
    new_refresh_token = secrets.token_hex(32)
    new_h = hashlib.sha256(new_refresh_token.encode()).hexdigest()

    session.refresh_token_hash = new_h
    session.token_version = db_token_version
    session.last_used_at = now_ist
    session.expires_at = now_ist + timedelta(days=180)  # 180-day sliding window renewal

    # 2. Issue fresh JWT access token (30 min)
    new_jwt = SecurityManager.create_access_token(
        data={
            "sub": str(employee.id),
            "emp_code": employee.emp_code,
            "email": employee.email,
            "role": employee.role.role_code if employee.role else "junior_executive",
            "staff_type": getattr(employee, "staff_type", "MN_STAFF"),
            "admin_scope": getattr(employee, "admin_scope", "CLIENT_SPECIFIC"),
            "base_company_id": employee.base_company_id,
            "tenant_id": getattr(employee, "tenant_id", 1) or 1,
            "token_version": db_token_version,
            "team_tag": employee.team_tag,
            "user_type": "staff"
        },
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )

    employee_data = employee.to_dict()
    try:
        from app.services.auth_context_service import resolve_staff_memberships
        acc_cids, prim_cid = resolve_staff_memberships(db, employee.id, getattr(employee, "tenant_id", 1) or 1)
        employee_data["accessible_company_ids"] = acc_cids
        employee_data["primary_company_id"] = prim_cid
    except Exception:
        pass
    try:
        from app.services.telephony.flow_interpreter import CallFlowInterpreter
        employee_data["extension"] = CallFlowInterpreter.get_staff_configured_extension(
            db, employee.base_company_id or 1, employee.id
        )
    except Exception:
        employee_data["extension"] = None

    db.commit()

    return {
        "success": True,
        "access_token": new_jwt,
        "refresh_token": new_refresh_token,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "employee": employee_data
    }


@router.post("/auth/mobile/revoke")
async def revoke_staff_mobile_session(
    payload: StaffMobileRevokeRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Revokes mobile device session(s).
    Called upon explicit mobile logout or remote session termination.
    """
    clean_token = (payload.refresh_token or "").strip()
    clean_device = (payload.device_id or "").strip()

    if payload.revoke_all_devices:
        staff_id_to_revoke = None
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            tok_payload = SecurityManager.verify_token(auth_header[7:])
            if tok_payload and "sub" in tok_payload:
                try:
                    staff_id_to_revoke = int(tok_payload["sub"])
                except (ValueError, TypeError):
                    pass
        if not staff_id_to_revoke and clean_token:
            h = hashlib.sha256(clean_token.encode()).hexdigest()
            sess = db.query(MobileDeviceSession).filter_by(refresh_token_hash=h).first()
            if sess:
                staff_id_to_revoke = sess.staff_id
        if staff_id_to_revoke:
            db.query(MobileDeviceSession).filter_by(
                staff_id=staff_id_to_revoke
            ).update({"is_revoked": True})
            db.query(MobileDevicePushToken).filter_by(
                staff_id=staff_id_to_revoke
            ).update({"is_active": False})
    elif clean_token:
        h = hashlib.sha256(clean_token.encode()).hexdigest()
        sess = db.query(MobileDeviceSession).filter_by(refresh_token_hash=h).first()
        if sess:
            db.query(MobileDevicePushToken).filter_by(
                staff_id=sess.staff_id, device_id=sess.device_id
            ).update({"is_active": False})
        db.query(MobileDeviceSession).filter_by(refresh_token_hash=h).update({"is_revoked": True})
    elif clean_device:
        db.query(MobileDeviceSession).filter_by(device_id=clean_device).update({"is_revoked": True})
        db.query(MobileDevicePushToken).filter_by(device_id=clean_device).update({"is_active": False})

    db.commit()
    return {"success": True, "message": "Mobile session revoked successfully."}


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
    # Stage 2A: Bump token_version to immediately revoke all existing sessions
    current_user.token_version = (getattr(current_user, "token_version", 1) or 1) + 1
    
    from app.services.auth_context_service import invalidate_auth_cache
    invalidate_auth_cache(current_user.id)
    
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
