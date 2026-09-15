"""
Stage 2A Canonical FastAPI Dependencies (Hardened)
Provides RequestContext injection, Tier 1 live DB security verification,
Tier 2 heavy authorization context hydration, capability-based guards,
and role hierarchy enforcement.
"""

import logging
from typing import Optional, Callable, Generator
from fastapi import Request, Depends, HTTPException, status, Query, Header
from sqlalchemy.orm import Session, joinedload
from jose import JWTError

from app.core.database import get_db
from app.core.config import settings
from app.core.security import SecurityManager
from app.core.context import (
    RequestContext, AdminScope,
    set_current_request_context, reset_current_request_context
)
from app.core.authorization import (
    assert_capability, assert_role, assert_platform_scope,
    assert_company_access, assert_resource_tenant, assert_module_entitlement,
    assert_parent_resource_ownership
)
from app.models.staff import StaffEmployee
from app.services.auth_context_service import get_heavy_authorization_context

logger = logging.getLogger("stage2a.deps")


def get_request_context(
    request: Request,
    db: Session = Depends(get_db)
) -> Generator[RequestContext, None, None]:
    """
    Canonical Stage 2A RequestContext dependency.
    1. Extracts Bearer token from Authorization header.
    2. Decodes JWT payload (identity + token_version + tenant_id).
    3. Executes TIER 1 LIVE CHECK on staff_employees (status == active, token_version match).
    4. Validates tenant claim against authoritative DB tenant (Section 8).
    5. Extracts requested company context (X-Company-ID header or company_id query).
    6. Resolves TIER 2 heavy authorization context (TTL <= 30s LRU cache).
    7. Hydrates immutable RequestContext without dangerous defaults.
    8. Binds RequestContext to task contextvars using safe generator yield/finally lifecycle (Section 11).
    """
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization header",
            headers={"WWW-Authenticate": "Bearer"}
        )

    # Strip Bearer prefix and quotes
    token = auth_header.strip()
    while token.lower().startswith("bearer "):
        token = token[7:].strip()
    token = token.strip('"').strip("'")

    if not token or token.lower() in ("null", "undefined", "none", ""):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"}
        )

    payload = SecurityManager.verify_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication credentials",
            headers={"WWW-Authenticate": "Bearer"}
        )

    sub = payload.get("sub")
    emp_code = payload.get("emp_code")
    token_version = payload.get("token_version")
    token_tenant_id = payload.get("tenant_id")

    if not sub and not emp_code:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"}
        )

    # ─────────────────────────────────────────────────────────────────────────
    # TIER 1: LIVE DB STATUS & TOKEN_VERSION CHECK (Zero 30s cache dependency)
    # ─────────────────────────────────────────────────────────────────────────
    emp_query = db.query(StaffEmployee).options(joinedload(StaffEmployee.role))
    employee = None
    if sub and str(sub).isdigit():
        employee = emp_query.filter(StaffEmployee.id == int(sub)).first()
    if not employee and emp_code:
        employee = emp_query.filter(StaffEmployee.emp_code == str(emp_code)).first()
    if not employee and sub:
        employee = emp_query.filter(StaffEmployee.emp_code == str(sub)).first()

    if not employee:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Staff user not found",
            headers={"WWW-Authenticate": "Bearer"}
        )

    # Section 6: Check active status live
    if employee.status != "active" or getattr(employee, "is_deleted", False):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Staff account is {employee.status}. Access denied.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    # Section 8: Authoritative Server-Side Tenant & Cross-Tenant Violation Check
    db_tenant_id = getattr(employee, "tenant_id", None)
    if db_tenant_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Staff employee has no associated tenant context."
        )

    if token_tenant_id is not None and int(token_tenant_id) != db_tenant_id:
        logger.warning(
            f"[TENANT-MISMATCH] Staff {employee.emp_code}: Token tenant {token_tenant_id} "
            f"!= DB tenant {db_tenant_id}. Cross-tenant token violation."
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Cross-tenant token violation.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    # Section 6 & 7: Check token_version revocation live
    db_token_version = getattr(employee, "token_version", 1) or 1
    if token_version is not None:
        if int(token_version) != db_token_version:
            logger.warning(
                f"[TOKEN-REVOKED] Staff {employee.emp_code}: Token version {token_version} "
                f"mismatches DB version {db_token_version}. Immediate revocation enforced."
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session has been revoked or expired. Please log in again.",
                headers={"WWW-Authenticate": "Bearer", "X-Token-Revoked": "true"}
            )
    else:
        # Section 7: Legacy token without token_version
        if db_token_version > 1:
            logger.warning(
                f"[TOKEN-REVOKED] Staff {employee.emp_code}: Legacy token rejected because "
                f"DB token_version is {db_token_version}."
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session has been revoked. Please log in again.",
                headers={"WWW-Authenticate": "Bearer", "X-Token-Revoked": "true"}
            )

    # ─────────────────────────────────────────────────────────────────────────
    # COMPANY CONTEXT RESOLUTION (Requested vs Default Primary)
    # Section 9: Client headers are REQUEST only, verified against memberships
    # ─────────────────────────────────────────────────────────────────────────
    requested_cid: Optional[int] = None
    header_cid = request.headers.get("X-Company-ID")
    if header_cid and header_cid.strip().isdigit():
        requested_cid = int(header_cid.strip())
    elif "company_id" in request.query_params and request.query_params["company_id"].isdigit():
        requested_cid = int(request.query_params["company_id"])

    # ─────────────────────────────────────────────────────────────────────────
    # TIER 2: HEAVY AUTHORIZATION RESOLUTION (Cached <= 30s)
    # ─────────────────────────────────────────────────────────────────────────
    auth_data = get_heavy_authorization_context(db, employee, requested_cid)

    # ─────────────────────────────────────────────────────────────────────────
    # HYDRATE CANONICAL REQUEST CONTEXT (Section 3: Mandatory explicit fields)
    # ─────────────────────────────────────────────────────────────────────────
    ctx = RequestContext(
        staff_id=employee.id,
        emp_code=employee.emp_code,
        tenant_id=auth_data["tenant_id"],
        active_company_id=auth_data["active_company_id"],
        email=employee.email,
        full_name=employee.full_name,
        base_company_id=employee.base_company_id,
        primary_company_id=auth_data["primary_company_id"],
        accessible_company_ids=auth_data["accessible_company_ids"],
        role_id=employee.role_id,
        role_code=employee.role.role_code if employee.role else "employee",
        hierarchy_level=int(employee.role.hierarchy_level if employee.role else 1),
        admin_scope=auth_data["admin_scope"],
        capabilities=auth_data["capabilities"],
        licensed_modules=auth_data["licensed_modules"],
        token_version=db_token_version,
        client_ip=request.client.host if request.client else None,
        user_agent=request.headers.get("User-Agent"),
        correlation_id=request.headers.get("X-Correlation-ID", "")
    )

    # Section 11: Bind to task contextvars and guarantee safe cleanup via yield/finally
    token_var = set_current_request_context(ctx)
    try:
        yield ctx
    finally:
        reset_current_request_context(token_var)


# Convenience alias for staff authentication
require_authenticated_staff = get_request_context


def require_capability(capability_name: str) -> Callable:
    """
    FastAPI route dependency factory for capability-based authorization.
    Usage:
        @router.get("/leads", dependencies=[Depends(require_capability("crm.leads.view"))])
        or
        def my_route(ctx: RequestContext = Depends(require_capability("crm.leads.view"))):
    """
    def _guard(ctx: RequestContext = Depends(get_request_context)) -> RequestContext:
        assert_capability(ctx, capability_name)
        return ctx
    return _guard


def require_role(min_hierarchy_level: int, role_description: str = "") -> Callable:
    """
    FastAPI route dependency factory for role hierarchy-based authorization.
    Usage:
        def my_route(ctx: RequestContext = Depends(require_role(80, "Company Admin"))):
    """
    def _guard(ctx: RequestContext = Depends(get_request_context)) -> RequestContext:
        assert_role(ctx, min_hierarchy_level, role_description)
        return ctx
    return _guard


def require_platform_scope(
    ctx: RequestContext = Depends(get_request_context)
) -> RequestContext:
    """
    FastAPI route dependency requiring Platform Superadmin scope.
    Usage:
        def my_admin_route(ctx: RequestContext = Depends(require_platform_scope)):
    """
    assert_platform_scope(ctx)
    return ctx


def require_module(module_code: str) -> Callable:
    """
    FastAPI route dependency requiring active module license for the company.
    Usage:
        def my_route(ctx: RequestContext = Depends(require_module("CRM_LEADS"))):
    """
    def _guard(ctx: RequestContext = Depends(get_request_context)) -> RequestContext:
        assert_module_entitlement(ctx, module_code)
        return ctx
    return _guard


def resolve_company_id(
    company_id: Optional[int] = Query(None),
    ctx: RequestContext = Depends(get_request_context)
) -> int:
    """
    FastAPI route dependency that resolves the authorized company_id for the current request.
    Uses RequestContext and validates active operational company membership.
    If company_id is omitted or 0, defaults to ctx.active_company_id.
    If an unauthorized company_id is provided, raises HTTP 403 Forbidden.
    """
    if company_id is not None and company_id > 0:
        if not ctx.can_access_company(company_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied to requested company #{company_id}. Not an active member."
            )
        return company_id
    return ctx.active_company_id


# Canonical re-export for route handlers
from app.api.v1.endpoints.staff_auth import resolve_tenant_company_for_request

