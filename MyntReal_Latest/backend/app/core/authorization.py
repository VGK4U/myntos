"""
Stage 2A Reusable Authorization Primitives & Policy Engine
Centralized authorization checks and assertions for capability-based RBAC,
tenant isolation, company boundaries, and platform superadmin evaluation.
"""

import logging
from typing import Optional, List, Set, Union, Any
from fastapi import HTTPException, status

from app.core.context import RequestContext, AdminScope

logger = logging.getLogger("stage2a.authorization")


def is_platform_superadmin(ctx: RequestContext) -> bool:
    """Check if authenticated context holds Platform Superadmin scope."""
    return ctx.admin_scope == AdminScope.PLATFORM_SUPERADMIN


def is_tenant_admin(ctx: RequestContext) -> bool:
    """Check if authenticated context holds Tenant Administrator scope or higher."""
    return ctx.admin_scope in (AdminScope.PLATFORM_SUPERADMIN, AdminScope.TENANT_ADMIN)


def check_capability(ctx: RequestContext, capability: str) -> bool:
    """Return True if context holds the capability, False otherwise."""
    return ctx.has_capability(capability)


def check_role(ctx: RequestContext, min_level: int) -> bool:
    """Return True if context hierarchy_level >= min_level or is platform superadmin."""
    if is_platform_superadmin(ctx):
        return True
    return ctx.hierarchy_level >= min_level


def check_company_access(ctx: RequestContext, company_id: int) -> bool:
    """Return True if context has operational access to company_id."""
    return ctx.can_access_company(company_id)


def check_tenant_access(ctx: RequestContext, resource_tenant_id: int) -> bool:
    """Return True if context tenant matches resource tenant or is platform superadmin."""
    if is_platform_superadmin(ctx):
        return True
    return ctx.tenant_id == resource_tenant_id


# ─────────────────────────────────────────────────────────────────────────────
# Assertions (Fail-Closed Enforcement Primitives)
# ─────────────────────────────────────────────────────────────────────────────

def assert_capability(ctx: RequestContext, capability: str) -> None:
    """Fail closed (403 Forbidden) if staff lacks required capability."""
    if not check_capability(ctx, capability):
        logger.warning(
            f"[AUTHZ-DENIED] Staff {ctx.emp_code} (Role: {ctx.role_code}) denied capability: {capability}"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Operation not permitted. Missing required capability: {capability}"
        )


def assert_role(ctx: RequestContext, min_level: int, role_description: str = "") -> None:
    """Fail closed (403 Forbidden) if staff hierarchy level is below threshold."""
    if not check_role(ctx, min_level):
        desc = f" ({role_description})" if role_description else ""
        logger.warning(
            f"[AUTHZ-DENIED] Staff {ctx.emp_code} (Level: {ctx.hierarchy_level}) requires level {min_level}{desc}"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Insufficient role permissions. Required level: {min_level}{desc}"
        )


def assert_platform_scope(ctx: RequestContext) -> None:
    """Fail closed (403 Forbidden) if staff does not hold platform superadmin scope."""
    if not is_platform_superadmin(ctx):
        logger.warning(f"[AUTHZ-DENIED] Staff {ctx.emp_code} attempted platform superadmin operation")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Platform administrative scope required."
        )


def assert_company_access(ctx: RequestContext, company_id: int) -> None:
    """Fail closed (403 Forbidden) if staff lacks active membership in target company."""
    if not check_company_access(ctx, company_id):
        logger.warning(
            f"[AUTHZ-DENIED] Staff {ctx.emp_code} unauthorized for company #{company_id}. "
            f"Authorized companies: {ctx.accessible_company_ids}"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied to company #{company_id}. No active membership."
        )


def assert_resource_tenant(ctx: RequestContext, resource_tenant_id: int, entity_name: str = "Resource") -> None:
    """
    Fail closed with 404 Not Found if resource belongs to another tenant.
    (Using 404 prevents cross-tenant entity enumeration/discovery).
    """
    if not check_tenant_access(ctx, resource_tenant_id):
        logger.warning(
            f"[AUTHZ-TENANT-VIOLATION] Staff {ctx.emp_code} (Tenant: {ctx.tenant_id}) "
            f"attempted to access {entity_name} belonging to Tenant: {resource_tenant_id}"
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{entity_name} not found"
        )


def assert_module_entitlement(ctx: RequestContext, module_code: str) -> None:
    """Fail closed (403 Forbidden) if active company does not have module enabled in license."""
    if is_platform_superadmin(ctx):
        return
    if module_code not in ctx.licensed_modules:
        logger.warning(
            f"[AUTHZ-MODULE-DENIED] Module {module_code} not licensed for Company #{ctx.active_company_id}"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Module {module_code} is not licensed for this company organization."
        )


def assert_parent_resource_ownership(
    ctx: RequestContext,
    parent_resource: Any,
    entity_name: str = "Parent Resource",
    check_company: bool = True
) -> None:
    """
    Parent-Gating Rule (Stage 2B / Safety Rule #7):
    A child foreign key is NOT authorization.
    Validates that a child entity's parent belongs to the authenticated tenant
    and that the actor has operational access to the parent's company.
    Fails closed with 404 (preventing cross-tenant enumeration) if tenant mismatch,
    or 403 if operational company membership is missing.
    """
    if parent_resource is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{entity_name} not found"
        )
    parent_tenant = getattr(parent_resource, "tenant_id", None)
    if parent_tenant is not None:
        assert_resource_tenant(ctx, parent_tenant, entity_name)

    if check_company and not is_platform_superadmin(ctx):
        parent_company = getattr(parent_resource, "company_id", None)
        if parent_company is not None and not ctx.can_access_company(parent_company):
            logger.warning(
                f"[AUTHZ-PARENT-DENIED] Staff {ctx.emp_code} attempted to access child of "
                f"{entity_name} in unauthorized company #{parent_company}. "
                f"Accessible companies: {ctx.accessible_company_ids}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied to {entity_name} company #{parent_company}. No active membership."
            )

