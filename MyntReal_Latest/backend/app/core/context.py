"""
Stage 2A Canonical RequestContext & AdminScope
Single backend representation of authenticated request identity, tenant boundary,
active company context, authorized company memberships, and capability grants.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List, Set, Any, Dict
from contextvars import ContextVar, Token


class AdminScope(str, Enum):
    """
    Administrative scope boundaries for MyntOS SaaS platform.
    Decoupled from hardcoded employee codes (e.g. MR10001, MR10025).
    """
    PLATFORM_SUPERADMIN = "PLATFORM_SUPERADMIN"  # Level 150+ within Master Platform Tenant (1)
    TENANT_ADMIN = "TENANT_ADMIN"                # Level 100+ or tenant_admin within any tenant
    COMPANY_ADMIN = "COMPANY_ADMIN"              # Level 80-99 (HR, EA, Company Leadership)
    MANAGER = "MANAGER"                          # Level 60-79 (Team Leaders, Incharge, Managers)
    STAFF = "STAFF"                              # Level 1-59 (Junior/Senior Executives, Agents)
    CLIENT_SPECIFIC = "CLIENT_SPECIFIC"          # Legacy compatibility
    NONE = "NONE"


@dataclass(frozen=True)
class RequestContext:
    """
    Immutable request context carried across coroutines/threads via contextvars.
    Authoritative server-side identity, tenant boundary, and capability state.
    """
    # 1. Identity & Authoritative Boundaries (Mandatory - No Defaults)
    staff_id: int
    emp_code: str
    tenant_id: int                               # Authoritative server-side tenant
    active_company_id: int                       # Resolved operational company context
    
    # 2. Identity Details
    email: Optional[str] = None
    full_name: Optional[str] = None
    
    # 3. Company Context
    base_company_id: Optional[int] = None        # Staff HR Home Company
    primary_company_id: Optional[int] = None     # Primary Operational Company (is_primary = TRUE)
    accessible_company_ids: List[int] = field(default_factory=list)  # Active memberships
    
    # 4. Role & Hierarchy Context
    role_id: Optional[int] = None
    role_code: str = "employee"
    hierarchy_level: int = 1
    admin_scope: AdminScope = AdminScope.STAFF
    
    # 5. Authorization & Entitlements
    capabilities: Set[str] = field(default_factory=set)        # Granular evaluated capabilities
    licensed_modules: Set[str] = field(default_factory=set)    # Modules licensed for active company/tenant
    
    # 6. Security State
    token_version: int = 1
    
    # 7. Audit & Diagnostics
    client_ip: Optional[str] = None
    user_agent: Optional[str] = None
    correlation_id: str = ""

    def has_capability(self, capability: str) -> bool:
        """Check if staff holds the specified granular capability or is platform superadmin."""
        if self.admin_scope == AdminScope.PLATFORM_SUPERADMIN:
            return True
        return capability in self.capabilities

    def has_any_capability(self, *caps: str) -> bool:
        """Check if staff holds any of the specified capabilities."""
        if self.admin_scope == AdminScope.PLATFORM_SUPERADMIN:
            return True
        return any(c in self.capabilities for c in caps)

    def has_all_capabilities(self, *caps: str) -> bool:
        """Check if staff holds all of the specified capabilities."""
        if self.admin_scope == AdminScope.PLATFORM_SUPERADMIN:
            return True
        return all(c in self.capabilities for c in caps)

    def can_access_company(self, company_id: int) -> bool:
        """Check if staff has active membership in the target company or has platform superadmin scope."""
        if self.admin_scope == AdminScope.PLATFORM_SUPERADMIN:
            return True
        return company_id in self.accessible_company_ids

    def is_platform_admin(self) -> bool:
        """Convenience check for platform superadmin scope."""
        return self.admin_scope == AdminScope.PLATFORM_SUPERADMIN

    def is_tenant_admin(self) -> bool:
        """Convenience check for tenant admin scope or higher."""
        return self.admin_scope in (AdminScope.PLATFORM_SUPERADMIN, AdminScope.TENANT_ADMIN)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize context for logging or responses."""
        return {
            "staff_id": self.staff_id,
            "emp_code": self.emp_code,
            "email": self.email,
            "full_name": self.full_name,
            "tenant_id": self.tenant_id,
            "base_company_id": self.base_company_id,
            "primary_company_id": self.primary_company_id,
            "active_company_id": self.active_company_id,
            "accessible_company_ids": list(self.accessible_company_ids),
            "role_id": self.role_id,
            "role_code": self.role_code,
            "hierarchy_level": self.hierarchy_level,
            "admin_scope": self.admin_scope.value,
            "capabilities": list(self.capabilities),
            "licensed_modules": list(self.licensed_modules),
            "token_version": self.token_version,
            "correlation_id": self.correlation_id,
        }


# Global thread-safe / coroutine-safe context variable
_current_request_context: ContextVar[Optional[RequestContext]] = ContextVar(
    "current_request_context", default=None
)


def get_current_request_context() -> Optional[RequestContext]:
    """Retrieve the RequestContext bound to the current async task or thread."""
    return _current_request_context.get()


def set_current_request_context(ctx: RequestContext) -> Token:
    """Bind a RequestContext to the current async task or thread."""
    return _current_request_context.set(ctx)


def reset_current_request_context(token: Optional[Token] = None) -> None:
    """Reset the RequestContext back to its previous state (or None)."""
    if token is not None:
        try:
            _current_request_context.reset(token)
            return
        except ValueError:
            pass
    _current_request_context.set(None)
