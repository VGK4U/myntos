"""
Security module for FastAPI Backend  
JWT Authentication replacing Flask-Login while preserving User ID system
"""

import os
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

_sec_logger = logging.getLogger("dc.security")
from jose import JWTError, jwt
from passlib.context import CryptContext
from werkzeug.security import check_password_hash, generate_password_hash
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.models.user import User

# Password hashing context (compatible with Flask Werkzeug + supports bcrypt for new passwords)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class HybridUserContext:
    """
    DC Protocol: Unified user context for hybrid authentication endpoints.
    Safely provides common attributes from either User or StaffEmployee objects.
    
    Usage:
        ctx = HybridUserContext(current_user)
        user_id = ctx.user_id        # MNR ID or emp_code
        user_name = ctx.user_name    # name or full_name
        user_type = ctx.user_type    # user_type or 'staff'
        display_id = ctx.display_id  # Primary identifier for display
    """
    
    def __init__(self, current_user):
        from app.models.staff import StaffEmployee
        self._user = current_user
        self._is_staff = isinstance(current_user, StaffEmployee)
    
    @property
    def is_staff(self) -> bool:
        """Check if current user is a Staff Employee"""
        return self._is_staff
    
    @property
    def is_mnr_user(self) -> bool:
        """Check if current user is an MNR User"""
        return not self._is_staff
    
    @property
    def user_id(self) -> str:
        """Get user identifier (MNR ID for users, emp_code for staff)"""
        if self._is_staff:
            return getattr(self._user, 'emp_code', str(self._user.id))
        return str(self._user.id)
    
    @property
    def display_id(self) -> str:
        """Get display ID (emp_code for staff, MNR ID for users)"""
        if self._is_staff:
            return getattr(self._user, 'emp_code', '') or str(self._user.id)
        return str(self._user.id)
    
    @property
    def numeric_id(self) -> int:
        """Get numeric database ID (for staff) or None for MNR users"""
        if self._is_staff:
            return self._user.id
        return None
    
    @property
    def user_name(self) -> str:
        """Get user's display name"""
        if self._is_staff:
            return getattr(self._user, 'full_name', '') or 'Staff User'
        return getattr(self._user, 'name', '') or 'User'
    
    @property
    def user_type(self) -> str:
        """Get user type/role (returns 'staff' for StaffEmployee)"""
        if self._is_staff:
            return 'staff'
        return getattr(self._user, 'user_type', 'Unknown')
    
    @property
    def role_name(self) -> str:
        """Get detailed role name for display"""
        if self._is_staff:
            role = getattr(self._user, 'role', None)
            if role:
                return getattr(role, 'role_name', 'Staff')
            return 'Staff'
        return getattr(self._user, 'user_type', 'Member')
    
    @property
    def email(self) -> Optional[str]:
        """Get user email"""
        return getattr(self._user, 'email', None)
    
    def has_admin_access(self) -> bool:
        """DC Protocol: Admin access is staff-only. MNR users never have admin access.
        Uses role_code exact match — substring matching on role_name must never be used
        (e.g. 'Senior Executive' contains 'executive' but must NOT qualify).
        VGK_MENTOR vgk_role is treated as equivalent to VGK4U admin access."""
        if self._is_staff:
            vgk_role = (getattr(self._user, 'vgk_role', '') or '').upper().strip()
            if vgk_role == 'VGK_MENTOR':
                return True
            role = getattr(self._user, 'role', None)
            if role:
                role_code = (getattr(role, 'role_code', '') or '').lower().strip()
                _admin_codes = {'vgk4u', 'vgk4u_supreme', 'key_leadership', 'leadership_role',
                                'hr', 'hr_manager', 'ea', 'executive_admin'}
                return role_code in _admin_codes or 'vgk4u' in role_code
            return False
        return False

    def has_rvz_access(self) -> bool:
        """DC Protocol: RVZ access is staff-only. MNR users never have RVZ access.
        Uses role_code exact match."""
        if self._is_staff:
            role = getattr(self._user, 'role', None)
            if role:
                role_code = (getattr(role, 'role_code', '') or '').lower().strip()
                _rvz_codes = {'vgk4u', 'vgk4u_supreme'}
                return role_code in _rvz_codes or 'vgk4u' in role_code
            return False
        return False

    def has_finance_access(self) -> bool:
        """DC Protocol: Finance access is staff-only. MNR users never have finance access.
        Uses role_code exact match."""
        if self._is_staff:
            role = getattr(self._user, 'role', None)
            if role:
                role_code = (getattr(role, 'role_code', '') or '').lower().strip()
                _finance_codes = {'vgk4u', 'vgk4u_supreme', 'key_leadership', 'leadership_role',
                                  'hr', 'hr_manager', 'ea', 'executive_admin', 'accounts', 'finance'}
                return role_code in _finance_codes or 'vgk4u' in role_code
            return False
        return False
    
    def is_allowed_role(self, allowed_roles: list) -> bool:
        """Check if user's role is in the allowed roles list"""
        return self.user_type in allowed_roles


def get_hybrid_user_context(current_user) -> HybridUserContext:
    """
    Create a HybridUserContext from a hybrid authentication user object.
    Use this in endpoints that use get_current_user_hybrid.
    """
    return HybridUserContext(current_user)


def resolve_hybrid_role(current_user) -> str:
    """
    DC Protocol: Resolve the user's role for permission checks.
    For StaffEmployee: Returns staff_type
    For MNR User: Returns user_type (only 'User' or 'Member')
    Admin operations must use isinstance(current_user, StaffEmployee) check.
    """
    from app.models.staff import StaffEmployee
    if isinstance(current_user, StaffEmployee):
        return getattr(current_user, 'staff_type', 'staff')
    return getattr(current_user, 'user_type', 'User')



# JWT Security scheme
security = HTTPBearer()

class SecurityManager:
    """
    Security manager preserving Flask app authentication logic
    Handles User ID-based authentication with JWT tokens
    """
    
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify password against hash (compatible with Flask Werkzeug + direct bcrypt + scrypt).
        DC Protocol (Apr 2026): All exceptions are logged — no silent failures.
        """
        if not hashed_password:
            return False

        # 1. Werkzeug hash verification — handles pbkdf2:sha256 natively.
        #    Scrypt is attempted here too; if Werkzeug's scrypt support throws
        #    (missing OpenSSL 1.1+ / cryptography package) we fall through to path 1b.
        try:
            if check_password_hash(hashed_password, plain_password):
                return True
        except Exception as _we:
            _sec_logger.warning("[DC-VERIFY-001] Werkzeug check_password_hash raised: %s — falling through", _we)

        # 1b. DC Protocol (Apr 24, 2026): Direct scrypt fallback for hashes stored
        #     before the Apr 21 pbkdf2 enforcement, when Werkzeug 3.x defaulted to
        #     scrypt. Format: scrypt:N:r:p$salt$hash (Werkzeug encoding).
        if hashed_password.startswith('scrypt:'):
            try:
                import hashlib as _hl
                import hmac as _hmac
                import base64 as _b64
                # Werkzeug scrypt format: "scrypt:N:r:p$salt_b64$hash_b64"
                _meta, _salt_b64, _hash_b64 = hashed_password.split('$', 2)
                _, _N, _r, _p = _meta.split(':')
                _salt = _b64.b64decode(_salt_b64 + '==')
                _expected = _b64.b64decode(_hash_b64 + '==')
                _derived = _hl.scrypt(
                    plain_password.encode('utf-8'),
                    salt=_salt,
                    n=int(_N), r=int(_r), p=int(_p),
                    dklen=len(_expected)
                )
                result = _hmac.compare_digest(_derived, _expected)
                if result:
                    return True
            except Exception as _se:
                _sec_logger.warning("[DC-VERIFY-001b] Scrypt direct verify raised: %s", _se)

        # 2. DC Protocol (Apr 21, 2026): Direct bcrypt for $2b$/$2a$ legacy hashes.
        #    passlib's CryptContext bcrypt backend is broken with bcrypt 5.x
        #    (missing __about__ attribute). Use bcrypt.checkpw() directly.
        if hashed_password.startswith(('$2b$', '$2a$', '$2y$')):
            try:
                import bcrypt as _bcrypt
                return _bcrypt.checkpw(
                    plain_password.encode('utf-8'),
                    hashed_password.encode('utf-8')
                )
            except Exception as _be:
                _sec_logger.warning("[DC-VERIFY-002] bcrypt.checkpw raised: %s", _be)

        # 3. Last-resort passlib fallback (handles any other schemes)
        try:
            return pwd_context.verify(plain_password, hashed_password)
        except Exception as _pe:
            _sec_logger.warning("[DC-VERIFY-003] passlib verify raised: %s — returning False", _pe)
            return False
    
    @staticmethod
    def get_password_hash(password: str) -> str:
        """Hash password (compatible with Flask Werkzeug for consistency)"""
        # DC Protocol (Apr 21, 2026): Force pbkdf2:sha256 — werkzeug 3.x defaults to scrypt
        # which conflicts with the passlib/bcrypt setup and breaks verify_password().
        return generate_password_hash(password, method='pbkdf2:sha256')
    
    @staticmethod
    def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
        """Create JWT access token with User ID"""
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
        return encoded_jwt
    
    @staticmethod
    def create_refresh_token(user_id: str) -> str:
        """Create JWT refresh token"""
        expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        to_encode = {"sub": user_id, "exp": expire, "type": "refresh"}
        encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
        return encoded_jwt
    
    @staticmethod
    def create_extended_session_token(
        original_payload: Dict[str, Any],
        extend_minutes: int = 30
    ) -> str:
        """
        DC_SESSION_EXTEND_001: Create extended session token for active clock-in/journey
        Used to prevent session expiry during active work periods.
        
        Args:
            original_payload: The original JWT payload (from current token)
            extend_minutes: How many minutes to extend the session (default: 30)
        
        Returns:
            New JWT token with extended expiry
        """
        to_encode = original_payload.copy()
        # Remove old expiry and set new one
        to_encode.pop("exp", None)
        expire = datetime.utcnow() + timedelta(minutes=extend_minutes)
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
        return encoded_jwt
    
    @staticmethod
    def verify_token(token: str) -> Optional[Dict[str, Any]]:
        """Verify JWT token and return payload"""
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            return payload
        except JWTError:
            return None
    
    @staticmethod
    def authenticate_user(db: Session, user_id: str, password: str) -> Optional[User]:
        """
        Authenticate user with MNR ID and password
        SECURITY: Accepts both MNR ID formats (10 & 12 character), rejects email logins
        DC Protocol Feb 2026: Dual-password support - checks both original and temp password
        """
        if not SecurityManager.is_valid_mnr_id(user_id):
            return None
        
        user = db.query(User).filter(User.id == user_id).first()
        
        if not user:
            return None
        
        stored_password = str(getattr(user, 'password', ''))
        
        try:
            werkzeug_result = check_password_hash(stored_password, password)
        except Exception:
            werkzeug_result = False
        
        try:
            bcrypt_result = pwd_context.verify(password, stored_password)
        except Exception:
            bcrypt_result = False
        
        password_valid = werkzeug_result or bcrypt_result
        
        if not password_valid:
            from datetime import datetime
            temp_password_hash = getattr(user, 'temp_password', None)
            temp_expires = getattr(user, 'temp_password_expires_at', None)
            if temp_password_hash and temp_expires:
                if datetime.utcnow() <= temp_expires:
                    password_valid = SecurityManager.verify_password(password, str(temp_password_hash))
                else:
                    user.temp_password = None
                    user.temp_password_expires_at = None
        
        if not password_valid:
            return None
        from datetime import datetime
        setattr(user, 'last_login', datetime.utcnow())
        db.commit()
        
        return user
    
    @staticmethod
    def is_valid_mnr_id(user_id: str) -> bool:
        """
        Validate MNR ID format with backward compatibility
        Supports multiple formats:
        - Original format: MNR1823XXXXX (MNR1823 + 5 digits = 12 chars)
        - Legacy formats: MNR + 7-9 digits (10-12 chars for old users)
        
        New users receive MNR1823XXXXX format (e.g., MNR182345678)
        """
        if not user_id or not isinstance(user_id, str):
            return False
        
        # Must start with "MNR"
        if not user_id.startswith('MNR'):
            return False
        
        # Length must be 10-12 characters (backward compatibility)
        length = len(user_id)
        if length < 10 or length > 12:
            return False
        
        # Everything after "MNR" must be digits
        import re
        suffix = user_id[3:]
        if not re.match(r'^\d+$', suffix):
            return False
        
        return True
    
    @staticmethod
    def get_user_by_id(db: Session, user_id: str) -> Optional[User]:
        """Get user by MNR ID (preserves Flask User.query.get logic)"""
        return db.query(User).filter(User.id == user_id).first()

# Dependency functions for FastAPI routes

async def get_current_user_token(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Dict[str, Any]:
    """Extract and verify JWT token from request"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        token = credentials.credentials
        payload = SecurityManager.verify_token(token)
        
        if payload is None:
            raise credentials_exception
        
        user_id = payload.get("sub")
        if user_id is None or not isinstance(user_id, str):
            raise credentials_exception
            
        return payload
        
    except JWTError:
        raise credentials_exception

async def get_current_user(
    token_payload: Dict[str, Any] = Depends(get_current_user_token),
    db: Session = Depends(get_db)
) -> User:
    """
    Get current authenticated user from JWT token
    Preserves Flask current_user functionality with User ID system
    """
    user_id = token_payload.get("sub")
    
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials"
        )
    
    user = SecurityManager.get_user_by_id(db, user_id)
    
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    # Check if account is locked (preserves Flask security logic)
    if getattr(user, 'account_locked', False):
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail="Account is locked"
        )
    
    # Check Red Coupon status (preserves Flask Red Coupon system) 
    is_red_coupon = getattr(user, 'is_red_coupon', False)
    red_coupon_locked = getattr(user, 'red_coupon_locked', False)
    if is_red_coupon and red_coupon_locked:
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail="Account locked due to Red Coupon status"
        )
    
    return user

async def get_current_user_hybrid(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Hybrid authentication: Accept BOTH JWT tokens AND session cookies.
    Supports both MNR users and Staff users for unified endpoints.
    Returns either User or StaffEmployee object.
    
    DC Protocol: Staff tokens have sub=numeric_id (as string), user_type=staff, emp_code
    MNR tokens have sub=MNR_ID (string)
    """
    from app.models.staff import StaffEmployee
    import logging
    logger = logging.getLogger(__name__)
    
    def resolve_staff_employee(payload: dict) -> StaffEmployee:
        """Helper to resolve StaffEmployee from token payload"""
        employee_id = payload.get("sub")
        if not employee_id:
            return None
            
        staff = None
        # Try numeric ID first (sub is stored as str(employee.id))
        try:
            numeric_id = int(employee_id)
            staff = db.query(StaffEmployee).filter(StaffEmployee.id == numeric_id).first()
        except (ValueError, TypeError):
            # Not a numeric ID - try emp_code lookup
            staff = db.query(StaffEmployee).filter(StaffEmployee.emp_code == employee_id).first()
        
        # Also try emp_code from payload if sub lookup failed
        if not staff and payload.get("emp_code"):
            staff = db.query(StaffEmployee).filter(
                StaffEmployee.emp_code == payload.get("emp_code")
            ).first()
        
        # DC Protocol: StaffEmployee uses 'status' column, not 'is_active'
        if staff and staff.status == 'active':
            return staff
        return None
    
    # DC Protocol (Feb 2026): Authorization header FIRST - explicit auth takes precedence
    # Fix: When MNR client sends Authorization: Bearer MNR_TOKEN, it must resolve to MNR user
    # even if a staff_token cookie exists from a previous Staff Portal session.
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
        try:
            payload = SecurityManager.verify_token(token)
            if payload and payload.get("sub"):
                if payload.get("user_type") == "staff" or payload.get("emp_code"):
                    staff = resolve_staff_employee(payload)
                    if staff:
                        return staff
                else:
                    user = SecurityManager.get_user_by_id(db, payload["sub"])
                    if user:
                        return user
        except Exception as e:
            logger.debug(f"Authorization header token verification failed: {e}")
    
    # Try staff_token cookie (Staff users authenticated via VGK login)
    staff_token = request.cookies.get("staff_token")
    if staff_token:
        try:
            payload = SecurityManager.verify_token(staff_token)
            if payload and (payload.get("user_type") == "staff" or payload.get("emp_code")):
                staff = resolve_staff_employee(payload)
                if staff:
                    return staff
        except Exception as e:
            logger.debug(f"Staff token cookie verification failed: {e}")
    
    # Fall back to session cookie (support both session_token and session for compatibility)
    session_token = request.cookies.get("session_token") or request.cookies.get("session")
    if session_token:
        try:
            payload = SecurityManager.verify_token(session_token)
            if payload and payload.get("sub"):
                user = SecurityManager.get_user_by_id(db, payload["sub"])
                if user:
                    # Same security checks as get_current_user
                    if getattr(user, 'account_locked', False):
                        raise HTTPException(
                            status_code=status.HTTP_423_LOCKED,
                            detail="Account is locked"
                        )
                    is_red_coupon = getattr(user, 'is_red_coupon', False)
                    red_coupon_locked = getattr(user, 'red_coupon_locked', False)
                    if is_red_coupon and red_coupon_locked:
                        raise HTTPException(
                            status_code=status.HTTP_423_LOCKED,
                            detail="Account locked due to Red Coupon status"
                        )
                    return user
        except:
            pass
    
    # No valid authentication found
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated"
    )


async def get_current_vgk_partner_any(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    DC Protocol: Partner-aware auth that accepts BOTH activated AND registered (non-activated) VGK partners.
    Used exclusively by read-only/view endpoints (e.g. /my-bonanzas) where registered members
    should still see content.  The caller MUST check partner.is_active to determine what to show.
    For write/claim endpoints, use get_current_user_hybrid_with_partner which enforces is_active=True.
    """
    from app.models.staff_accounts import OfficialPartner
    import logging
    logger = logging.getLogger(__name__)

    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
        try:
            payload = SecurityManager.verify_token(token)
            if payload and payload.get("sub"):
                if payload.get("user_type") == "partner" or payload.get("partner_code"):
                    partner = None
                    partner_id = payload.get("sub") or payload.get("partner_id")
                    partner_code = payload.get("partner_code")
                    if partner_id:
                        try:
                            numeric_id = int(partner_id)
                            partner = db.query(OfficialPartner).filter(
                                OfficialPartner.id == numeric_id
                            ).first()
                        except (ValueError, TypeError):
                            partner = db.query(OfficialPartner).filter(
                                OfficialPartner.partner_code == partner_id
                            ).first()
                    if not partner and partner_code:
                        partner = db.query(OfficialPartner).filter(
                            OfficialPartner.partner_code == partner_code
                        ).first()
                    # DC Protocol: Accept partner regardless of is_active status
                    if partner:
                        return partner
        except Exception as e:
            logger.debug(f"VGK partner (any) token check failed: {e}")

    # Fall back to standard hybrid auth for Staff/MNR users
    return await get_current_user_hybrid(request, db)


async def get_current_user_hybrid_with_partner(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    DC Protocol (Dec 31, 2025): Partner-aware hybrid authentication.
    Extends get_current_user_hybrid to also support OfficialPartner users.
    Returns StaffEmployee, User, or OfficialPartner based on token type.
    
    Used by unified endpoints that need to serve all three user types.
    """
    from app.models.staff import StaffEmployee
    from app.models.staff_accounts import OfficialPartner
    import logging
    logger = logging.getLogger(__name__)
    
    # Try partner token from Authorization header first
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
        try:
            payload = SecurityManager.verify_token(token)
            if payload and payload.get("sub"):
                # Check if this is a partner token
                if payload.get("user_type") == "partner" or payload.get("partner_code"):
                    partner = None
                    partner_id = payload.get("sub") or payload.get("partner_id")
                    partner_code = payload.get("partner_code")
                    
                    # Try numeric ID lookup first
                    if partner_id:
                        try:
                            numeric_id = int(partner_id)
                            partner = db.query(OfficialPartner).filter(
                                OfficialPartner.id == numeric_id
                            ).first()
                        except (ValueError, TypeError):
                            # sub might be partner_code string (e.g., "PRT0001")
                            partner = db.query(OfficialPartner).filter(
                                OfficialPartner.partner_code == partner_id
                            ).first()
                    
                    # Fallback to partner_code from payload
                    if not partner and partner_code:
                        partner = db.query(OfficialPartner).filter(
                            OfficialPartner.partner_code == partner_code
                        ).first()
                    
                    if partner and partner.is_active:
                        return partner
        except Exception as e:
            logger.debug(f"Partner token check failed: {e}")
    
    # Fall back to standard hybrid auth for Staff/MNR users
    return await get_current_user_hybrid(request, db)


async def get_current_mnr_user_from_hybrid(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    MNR-ONLY authentication from hybrid session.
    DC Protocol: For MNR-specific pages (withdrawals, earnings), this function
    extracts the MNR user even when staff is also logged in.
    
    Priority: MNR session_token > JWT Authorization header (MNR only) > staff_token (ignored)
    
    Use Case: When both staff (MR10001) and MNR user (MNR1800145) are logged in,
    this returns the MNR user for MNR-specific operations.
    """
    import logging
    logger = logging.getLogger(__name__)
    
    # Priority 1: Try MNR session cookie first (session_token)
    session_token = request.cookies.get("session_token") or request.cookies.get("session")
    if session_token:
        try:
            payload = SecurityManager.verify_token(session_token)
            if payload and payload.get("sub"):
                user_id = str(payload["sub"])
                if user_id.startswith("MNR"):
                    user = SecurityManager.get_user_by_id(db, user_id)
                    if user:
                        if getattr(user, 'account_locked', False):
                            raise HTTPException(
                                status_code=status.HTTP_423_LOCKED,
                                detail="Account is locked"
                            )
                        is_red_coupon = getattr(user, 'is_red_coupon', False)
                        red_coupon_locked = getattr(user, 'red_coupon_locked', False)
                        if is_red_coupon and red_coupon_locked:
                            raise HTTPException(
                                status_code=status.HTTP_423_LOCKED,
                                detail="Account locked due to Red Coupon status"
                            )
                        return user
        except HTTPException:
            raise
        except Exception as e:
            logger.debug(f"MNR session token verification failed: {e}")
    
    # Priority 2: Try JWT from Authorization header (MNR tokens only)
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
        try:
            payload = SecurityManager.verify_token(token)
            if payload and payload.get("sub"):
                user_id = str(payload["sub"])
                if payload.get("user_type") != "staff" and not payload.get("emp_code"):
                    if user_id.startswith("MNR"):
                        user = SecurityManager.get_user_by_id(db, user_id)
                        if user:
                            return user
        except Exception as e:
            logger.debug(f"MNR JWT verification failed: {e}")
    
    # No MNR user found - return 401
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="MNR user authentication required. Please log in with your MNR ID."
    )

async def get_current_user_any(
    current_user = Depends(get_current_user_hybrid)
):
    """
    DC Protocol: Accept any authenticated user (staff OR MNR user).
    Wrapper around get_current_user_hybrid that works for both user types.
    Use for endpoints that must be accessible to both staff and regular users.
    """
    return current_user


async def get_current_admin_user(
    current_user = Depends(get_current_user_hybrid)
):
    """
    DC Protocol: Staff-only admin access.
    MNR admin types removed - only Staff users can perform admin operations.
    """
    from app.models.staff import StaffEmployee
    if not isinstance(current_user, StaffEmployee):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Staff access required"
        )
    return current_user

async def get_current_admin_user_hybrid(
    current_user = Depends(get_current_user_hybrid)
):
    """
    DC Protocol: Staff-only admin access (hybrid auth).
    MNR admin types removed - only Staff users can perform admin operations.
    """
    from app.models.staff import StaffEmployee
    if not isinstance(current_user, StaffEmployee):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Staff access required"
        )
    return current_user

async def get_current_super_admin_user(
    current_user = Depends(get_current_user_hybrid)
):
    """
    DC Protocol: Staff-only super admin access.
    MNR admin types removed - only Staff users can perform admin operations.
    """
    from app.models.staff import StaffEmployee
    if not isinstance(current_user, StaffEmployee):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Staff access required"
        )
    return current_user

# Role-based access control functions (preserve Flask RBAC)

def require_user_access(target_user_id: str, current_user) -> bool:
    """
    Validate user access to prevent IDOR attacks
    DC Protocol: Staff users can access any user data, MNR members only their own
    """
    from app.models.staff import StaffEmployee
    if isinstance(current_user, StaffEmployee):
        return True
    return str(getattr(current_user, 'id', '')) == target_user_id

class RoleChecker:
    """
    Role-based access control checker
    DC Protocol: Staff-only for admin operations, MNR members for member operations.
    MNR admin types removed permanently.
    """
    
    def __init__(self, allowed_roles: list, staff_only: bool = False):
        self.allowed_roles = allowed_roles
        self.staff_only = staff_only
    
    def __call__(self, current_user = Depends(get_current_user_hybrid)):
        from app.models.staff import StaffEmployee
        
        if self.staff_only:
            if not isinstance(current_user, StaffEmployee):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Staff access required"
                )
            return current_user
        
        if isinstance(current_user, StaffEmployee):
            return current_user
        
        user_type = getattr(current_user, 'user_type', None)
        if user_type not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required roles: {', '.join(self.allowed_roles)}"
            )
        return current_user

# Role hierarchy levels - MNR member types only, admin operations are staff-only
ROLE_LEVELS = {
    'User': 1,
    'Member': 2
}

async def get_current_rvz_user(
    current_user = Depends(get_current_user_hybrid)
):
    """
    DC Protocol: Staff-only RVZ-level access.
    MNR admin types removed - only Staff users can perform RVZ operations.
    """
    from app.models.staff import StaffEmployee
    if not isinstance(current_user, StaffEmployee):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Staff access required"
        )
    return current_user

async def get_current_rvz_user_hybrid(
    current_user = Depends(get_current_user_hybrid)
):
    """
    DC Protocol: Staff-only RVZ-level access (hybrid auth).
    MNR admin types removed - only Staff users can perform RVZ operations.
    Uses hierarchy_level for granular staff access control.
    """
    from app.models.staff import StaffEmployee
    
    if not isinstance(current_user, StaffEmployee):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Staff access required"
        )
    
    staff_type = str(getattr(current_user, 'staff_type', '') or '').lower().strip()
    role = getattr(current_user, 'role', None)
    hierarchy_level = getattr(role, 'hierarchy_level', 0) if role else 0
    
    if staff_type == 'vgk4u':
        return current_user
    
    RVZ_STAFF_MIN_HIERARCHY = 50
    if hierarchy_level >= RVZ_STAFF_MIN_HIERARCHY:
        return current_user
    
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=f"Staff access requires hierarchy level {RVZ_STAFF_MIN_HIERARCHY}+ (current: {hierarchy_level})"
    )

def has_role_level(user_type: str, required_level: int) -> bool:
    """Check if user role meets minimum level requirement"""
    user_level = ROLE_LEVELS.get(user_type, 0)
    return user_level >= required_level


async def require_activated_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    DC Protocol Feb 2026: Require user to be activated (has activation_date)
    Used for Facilitation & Recognition features that require activated membership
    Non-activated users receive 403 Forbidden with clear message
    """
    activation_date = getattr(current_user, 'activation_date', None)
    if activation_date is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This feature requires an activated membership. Please activate your account first."
        )
    return current_user


async def require_activated_user_hybrid(
    current_user: User = Depends(get_current_user_hybrid)
) -> User:
    """
    DC Protocol Feb 2026: Hybrid auth version of require_activated_user
    Accepts BOTH JWT tokens AND session cookies
    Used for frontend pages with cookie-based authentication
    """
    from app.models.staff import StaffEmployee
    
    if isinstance(current_user, StaffEmployee):
        return current_user
    
    activation_date = getattr(current_user, 'activation_date', None)
    if activation_date is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This feature requires an activated membership. Please activate your account first."
        )
    return current_user


def get_current_staff_user_from_hybrid(current_user, db: Session) -> Optional['StaffEmployee']:
    """
    DC Protocol Jan 2026: Extract StaffEmployee from hybrid auth user
    Returns StaffEmployee if current_user is staff, None otherwise
    Used for service ticket workflows that require staff context
    """
    from app.models.staff import StaffEmployee
    
    if isinstance(current_user, StaffEmployee):
        return current_user
    
    staff_id = getattr(current_user, '_staff_id', None)
    if staff_id:
        return db.query(StaffEmployee).filter(StaffEmployee.id == staff_id).first()
    
    return None

def can_access_user_data(current_user, target_user_id: str) -> bool:
    """
    DC Protocol: Staff can access all user data, MNR members only their own.
    MNR admin types removed permanently.
    """
    from app.models.staff import StaffEmployee
    if isinstance(current_user, StaffEmployee):
        return True
    return str(getattr(current_user, 'id', '')) == target_user_id

# DC Protocol: Staff-only admin role checkers - MNR admin types removed permanently
require_admin = RoleChecker([], staff_only=True)
require_finance_admin = RoleChecker([], staff_only=True)
require_super_admin = RoleChecker([], staff_only=True)
require_rvz_id = RoleChecker([], staff_only=True)
require_member = RoleChecker(["Member", "User"])


# ===== DC PROTOCOL FEB 2026: Staff-Only Approval System =====

async def require_staff_accounts_or_vgk(
    current_user = Depends(get_current_user_hybrid),
    db: Session = Depends(get_db)
):
    """
    DC Protocol Feb 2026: Require MR10001 VGK Mentor OR Accounts Department Staff
    
    Used for final approval in 2-step Staff workflow (income approval, KYC approval)
    Access granted if:
    1. Staff with emp_code MR10001 (VGK Mentor), OR
    2. Staff in Accounts department (primary or additional)
    
    Raises HTTPException 403 if not authorized
    """
    from app.models.staff import StaffEmployee
    
    if not isinstance(current_user, StaffEmployee):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Staff access required. Final approval requires VGK Mentor (MR10001) or Accounts department staff."
        )
    
    # Check 1: MR10001 VGK Mentor
    emp_code = getattr(current_user, 'emp_code', '') or ''
    if emp_code == 'MR10001':
        return current_user
    
    # Check 2: Primary department is Accounts
    dept = getattr(current_user, 'department', None)
    if dept:
        dept_name = getattr(dept, 'name', '').lower()
        if 'accounts' in dept_name or 'finance' in dept_name:
            return current_user
    
    # Check 3: Additional departments include Accounts
    additional_depts = getattr(current_user, 'additional_departments', [])
    for ad in additional_depts:
        ad_dept = getattr(ad, 'department', None)
        if ad_dept:
            ad_name = getattr(ad_dept, 'name', '').lower()
            if 'accounts' in ad_name or 'finance' in ad_name:
                return current_user
    
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Access denied. Final approval requires VGK Mentor (MR10001) or Accounts department membership."
    )


async def require_staff_with_page_access(
    current_user = Depends(get_current_user_hybrid)
):
    """
    DC Protocol Feb 2026: Require any Staff user with page access
    
    Used for validation step in 2-step Staff workflow.
    Page-level menu access controls who sees the page.
    This function just ensures the user is a Staff employee.
    
    Returns StaffEmployee or raises HTTPException 403
    """
    from app.models.staff import StaffEmployee
    
    if not isinstance(current_user, StaffEmployee):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Staff access required. You must be logged in as Staff to perform this action."
        )
    
    return current_user


def require_kyc_approval(user: User, db: Session = None) -> None:
    """
    KYC Validation Helper (DC Protocol - Single Source of Truth)
    
    Validates that user has completed KYC and bank details approval
    before allowing final processing (withdrawals, awards, bonanza claims)
    
    DC Protocol: 
    - Uses user table as single source of truth for KYC status
    - Respects RVZ ID global settings to skip KYC/Banking requirements
    - Single source of truth: app_settings table controls skip behavior
    
    Raises HTTPException if validation fails
    """
    # DC PROTOCOL: Check RVZ ID global skip settings FIRST (single source of truth)
    if db:
        from app.models.system_control import AppSettings
        skip_settings = AppSettings.get_kyc_skip_settings(db)
        
        # If RVZ ID has globally disabled KYC/Banking requirements, skip all checks
        if skip_settings.get('skip_kyc_requirement') and skip_settings.get('skip_bank_requirement'):
            return  # ✅ RVZ ID has disabled all KYC/Banking requirements
    
    kyc_status = getattr(user, 'kyc_status', 'Pending')
    bank_status = getattr(user, 'bank_details_status', 'Not Submitted')
    
    # Check KYC requirement (if not skipped by RVZ ID)
    if db:
        skip_settings = AppSettings.get_kyc_skip_settings(db)
        if not skip_settings.get('skip_kyc_requirement'):
            if kyc_status != 'Approved':
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={
                        "error": "KYC_APPROVAL_REQUIRED",
                        "message": "KYC verification required. Please complete your KYC to proceed.",
                        "kyc_status": kyc_status,
                        "action_required": "Complete KYC verification at /profile-edit?section=kyc"
                    }
                )
    
    # Check Bank requirement (if not skipped by RVZ ID)
    if db:
        skip_settings = AppSettings.get_kyc_skip_settings(db)
        if not skip_settings.get('skip_bank_requirement'):
            if bank_status != 'Approved':
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={
                        "error": "BANK_APPROVAL_REQUIRED",
                        "message": "Bank details approval required. Please submit your bank details for verification.",
                        "bank_details_status": bank_status,
                        "action_required": "Complete bank details at /profile-edit?section=bank"
                    }
                )


def check_kyc_status(user: User) -> Dict[str, Any]:
    """
    Check KYC status without raising exceptions (DC Protocol)
    Returns status dictionary for display purposes
    """
    kyc_status = getattr(user, 'kyc_status', 'Pending')
    bank_status = getattr(user, 'bank_details_status', 'Not Submitted')
    
    return {
        "kyc_status": kyc_status,
        "bank_details_status": bank_status,
        "kyc_approved": kyc_status == 'Approved',
        "bank_approved": bank_status == 'Approved',
        "can_withdraw": kyc_status == 'Approved' and bank_status == 'Approved',
        "can_claim_awards": kyc_status == 'Approved' and bank_status == 'Approved',
        "pending_action": "kyc" if kyc_status != 'Approved' else ("bank" if bank_status != 'Approved' else None)
    }
# ===== BANNER MANAGEMENT AUTH =====
async def get_banner_creator_user(
    current_user = Depends(get_current_user_hybrid)
):
    """
    DC Protocol: Staff-only banner creation.
    MNR admin types removed permanently.
    """
    from app.models.staff import StaffEmployee
    if not isinstance(current_user, StaffEmployee):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Staff access required for banner creation"
        )
    return current_user

async def get_banner_creator_user_hybrid(
    current_user = Depends(get_current_user_hybrid)
):
    """
    DC Protocol: Staff-only banner creation (hybrid auth).
    MNR admin types removed permanently.
    """
    from app.models.staff import StaffEmployee
    if not isinstance(current_user, StaffEmployee):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Staff access required for banner creation"
        )
    return current_user

