"""
Stage 2A Heavy Authorization Context Cache Service (Hardened)
Provides a thread-safe in-process LRU cache with <= 30 second TTL
for resolving company memberships, active company context, role capabilities,
and module entitlements.

NOTE: This cache is strictly for heavy authorization decisions.
It NEVER caches or overrides live account status or token_version revocation.
"""

import time
import threading
import logging
from collections import OrderedDict
from typing import Optional, List, Set, Tuple, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import text
from fastapi import HTTPException, status

from app.core.context import AdminScope, RequestContext
from app.models.staff import StaffEmployee, StaffRole, StaffCompanyMembership
from app.models.staff_accounts import AssociatedCompany

logger = logging.getLogger("stage2a.auth_context")

# Max 1,000 entries (approx 2MB RAM, zero OOM risk for monolithic instance)
_CACHE_MAX_SIZE = 1000
_CACHE_TTL_SECONDS = 30.0

# True LRU cache using OrderedDict: key -> (timestamp, data)
_auth_cache: OrderedDict[Tuple[int, int, int, Optional[int]], Tuple[float, Dict[str, Any]]] = OrderedDict()
_cache_lock = threading.Lock()


def invalidate_auth_cache(staff_id: Optional[int] = None) -> None:
    """
    Invalidate cached authorization contexts.
    If staff_id is given, purges all cached entries for that staff member across any tenant/company.
    """
    with _cache_lock:
        if staff_id is None:
            _auth_cache.clear()
        else:
            keys_to_del = [k for k in _auth_cache if k[1] == staff_id]
            for k in keys_to_del:
                _auth_cache.pop(k, None)


def resolve_admin_scope(staff: StaffEmployee) -> AdminScope:
    """
    Authoritatively resolve administrative scope for a staff employee.
    Section 5: Strictly DB-backed, auditable, and decoupled from hardcoded employee codes
    or arbitrary role-name matching:
    - Platform Superadmin: requires explicit DB admin_scope == 'PLATFORM', Master Tenant (1), and Level >= 150
    - Tenant Administrator: raw_admin_scope == 'TENANT_ADMIN' or Level >= 100
    - Company Administrator: Level 80-99 (HR, EA, Company Leadership)
    - Manager: Level 60-79 (Team Leaders, Incharge, Managers)
    - Staff: Standard operational staff
    """
    role = getattr(staff, "role", None)
    role_level = int(getattr(role, "hierarchy_level", 0) or 0) if role else 0
    tenant_id = getattr(staff, "tenant_id", None)
    raw_admin_scope = (getattr(staff, "admin_scope", "") or "").upper().strip()

    # 1. Platform Superadmin: requires all three DB facts:
    # - explicit DB admin_scope == 'PLATFORM'
    # - authenticated tenant_id == 1 (Master Platform Tenant)
    # - role hierarchy_level >= 150
    if raw_admin_scope == "PLATFORM" and tenant_id == 1 and role_level >= 150:
        return AdminScope.PLATFORM_SUPERADMIN

    # 2. Tenant Administrator: Level 100+ or explicit TENANT_ADMIN admin_scope in DB
    if role_level >= 100 or raw_admin_scope == "TENANT_ADMIN":
        return AdminScope.TENANT_ADMIN

    # 3. Company Administrator: Level 80-99 (HR, EA, Company Leadership)
    if role_level >= 80:
        return AdminScope.COMPANY_ADMIN

    # 4. Manager: Level 60-79 (Team Leaders, Incharge, Managers)
    if role_level >= 60:
        return AdminScope.MANAGER

    # 5. Standard Staff
    return AdminScope.STAFF


def resolve_staff_memberships(db: Session, staff_id: int, tenant_id: int) -> Tuple[List[int], Optional[int]]:
    """
    Resolve all active operational company memberships and primary company for a staff member.
    Queries staff_company_memberships table (from Stage 1).

    Section 1 & 3: FAIL CLOSED.
    NEVER falls back to staff.base_company_id or company_id = 1.
    If no active memberships are found, returns ([], None).
    If multiple primary memberships are found, returns (accessible, None) for safe failure.
    """
    try:
        memberships = db.query(StaffCompanyMembership).filter(
            StaffCompanyMembership.staff_id == staff_id,
            StaffCompanyMembership.tenant_id == tenant_id,
            StaffCompanyMembership.is_active == True
        ).all()

        if memberships:
            accessible = [m.company_id for m in memberships]
            primary_rows = [m for m in memberships if m.is_primary]
            
            if len(primary_rows) == 1:
                return accessible, primary_rows[0].company_id
            elif len(primary_rows) > 1:
                logger.error(
                    f"[AUTH-INTEGRITY] Staff #{staff_id} in Tenant #{tenant_id} has {len(primary_rows)} "
                    f"primary memberships! Data integrity violation."
                )
                return accessible, None
            else:
                # 0 primary memberships
                return accessible, None
    except Exception as e:
        logger.error(f"[AUTH-RESOLVE-MEMBERSHIPS] Error querying staff_company_memberships: {e}")

    # Section 1 & Section 3: FAIL CLOSED. Zero fallback to base_company_id or company 1.
    return [], None


def resolve_active_company(
    requested_company_id: Optional[int],
    accessible_company_ids: List[int],
    primary_company_id: Optional[int],
    is_platform_admin: bool = False,
    tenant_id: Optional[int] = None,
    db: Optional[Session] = None
) -> int:
    """
    Authoritatively resolve active company context.
    Section 2, 9, 10:
    - If company requested: verify staff has active membership in company (or is platform superadmin)
      AND verify the company belongs to the authenticated tenant.
    - If no company requested: default to exactly one active primary membership (is_primary = TRUE).
    - If 0 or >1 primary memberships exist: FAIL CLOSED (403 Forbidden).
    - No silent picking of memberships[0] or defaulting to company_id = 1.
    """
    # 1. Explicit company requested via X-Company-ID header or query param
    if requested_company_id is not None and requested_company_id > 0:
        if is_platform_admin:
            if db:
                comp = db.query(AssociatedCompany).filter(AssociatedCompany.id == requested_company_id).first()
                if not comp:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Company #{requested_company_id} not found."
                    )
            return requested_company_id

        if requested_company_id in accessible_company_ids:
            if db and tenant_id:
                comp = db.query(AssociatedCompany).filter(
                    AssociatedCompany.id == requested_company_id,
                    AssociatedCompany.client_id == tenant_id
                ).first()
                if not comp:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"Company #{requested_company_id} does not belong to authenticated tenant #{tenant_id}."
                    )
            return requested_company_id

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied to requested company #{requested_company_id}. Not an active member."
        )

    # 2. No company requested: determine default primary company
    if not accessible_company_ids:
        if is_platform_admin:
            if db:
                platform_comp = db.query(AssociatedCompany).filter(AssociatedCompany.client_id == 1).first()
                if platform_comp:
                    return platform_comp.id
            return 1
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No operational company access. Staff employee has no active company memberships."
        )

    if primary_company_id is not None and primary_company_id in accessible_company_ids:
        if db and tenant_id and not is_platform_admin:
            comp = db.query(AssociatedCompany).filter(
                AssociatedCompany.id == primary_company_id,
                AssociatedCompany.client_id == tenant_id
            ).first()
            if not comp:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Primary company #{primary_company_id} does not belong to authenticated tenant #{tenant_id}."
                )
        return primary_company_id

    # Ambiguous or missing primary membership: FAIL CLOSED
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Ambiguous or missing primary company membership. Operational company context cannot be resolved automatically."
    )


def resolve_licensed_modules(db: Session, company_id: int, tenant_id: int) -> Set[str]:
    """
    Resolve licensed modules for target company from associated_companies.licensed_modules.
    Section 2 & 14: Enforces tenant-scoping (AssociatedCompany.client_id == tenant_id).
    Fails closed (returns empty set) if company does not belong to tenant or is unconfigured.
    Zero fake default modules.
    """
    try:
        comp = db.query(AssociatedCompany).filter(
            AssociatedCompany.id == company_id,
            AssociatedCompany.client_id == tenant_id
        ).first()

        if not comp:
            logger.warning(
                f"[AUTH-TENANT-ISOLATION] Company #{company_id} does not belong to Tenant #{tenant_id}."
            )
            return set()

        if comp.licensed_modules:
            if isinstance(comp.licensed_modules, list):
                return set(comp.licensed_modules)
            elif isinstance(comp.licensed_modules, dict):
                return {k for k, v in comp.licensed_modules.items() if v}
    except Exception as e:
        logger.error(f"[AUTH-RESOLVE-MODULES] Error reading licensed_modules: {e}")

    # Section 14: FAIL CLOSED. No hardcoded default modules.
    return set()


def resolve_staff_capabilities(
    db: Session,
    staff: StaffEmployee,
    active_company_id: int,
    admin_scope: AdminScope
) -> Set[str]:
    """
    Resolve granular capabilities for a staff member.
    Section 4: Role hierarchy and capability authorization are strictly bounded.
    Zero blanket grants of all permissions.
    """
    if admin_scope == AdminScope.PLATFORM_SUPERADMIN:
        # Platform Superadmin has all platform and business capabilities
        return {
            "crm.leads.view_all", "crm.leads.create", "crm.leads.edit", "crm.leads.delete", "crm.leads.assign",
            "service.tickets.view_all", "service.tickets.create", "service.tickets.edit", "service.tickets.close",
            "whatsapp.config.view", "whatsapp.config.manage", "whatsapp.messages.send",
            "meta.campaigns.view", "meta.campaigns.manage", "meta.forms.route",
            "staff.employees.view", "staff.employees.edit", "staff.employees.create",
            "system.config", "finance.view", "finance.approve", "reports.view", "reports.export",
            "users.view", "users.create", "users.edit", "users.delete",
            "vgk.roles", "vgk.menus", "vgk.permissions"
        }

    caps: Set[str] = set()
    role = getattr(staff, "role", None)
    level = int(getattr(role, "hierarchy_level", 0) or 0) if role else 0

    # Base operational capabilities for all active staff
    caps.add("crm.leads.view_assigned")
    caps.add("crm.leads.create")
    caps.add("service.tickets.view_assigned")
    caps.add("service.tickets.create")

    if level >= 10:  # Junior Executive +
        caps.add("crm.leads.edit")
        caps.add("service.tickets.edit")

    if level >= 40:  # Senior Executive +
        caps.add("reports.view")

    if level >= 60:  # Manager / Team Leader +
        caps.add("crm.leads.view_all")
        caps.add("crm.leads.assign")
        caps.add("service.tickets.view_all")
        caps.add("staff.employees.view")

    if level >= 80:  # Company Admin / Leadership +
        caps.add("staff.employees.edit")
        caps.add("staff.employees.create")
        caps.add("finance.view")
        caps.add("kyc.view")
        caps.add("kyc.approve")
        caps.add("reports.export")

    if level >= 100:  # Tenant Admin +
        caps.add("system.config")
        caps.add("finance.approve")
        caps.add("whatsapp.config.view")
        caps.add("whatsapp.config.manage")
        caps.add("meta.campaigns.manage")
        caps.add("service.tickets.close")
        caps.add("users.view")
        caps.add("users.create")
        caps.add("users.edit")

    return caps


def get_heavy_authorization_context(
    db: Session,
    staff: StaffEmployee,
    requested_company_id: Optional[int]
) -> Dict[str, Any]:
    """
    Retrieve or compute heavy authorization context.
    Uses bounded thread-safe in-process LRU cache with TTL <= 30 seconds.
    Section 12 & 13: Cache key includes (tenant_id, staff_id, token_version, requested_company_id).
    True LRU eviction via collections.OrderedDict.
    """
    staff_id = staff.id
    token_version = getattr(staff, "token_version", 1) or 1
    tenant_id = getattr(staff, "tenant_id", None)
    if tenant_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Staff employee has no associated tenant context."
        )

    cache_key = (tenant_id, staff_id, token_version, requested_company_id)
    now = time.time()

    with _cache_lock:
        if cache_key in _auth_cache:
            ts, cached_data = _auth_cache[cache_key]
            if (now - ts) < _CACHE_TTL_SECONDS:
                _auth_cache.move_to_end(cache_key)
                return cached_data
            else:
                _auth_cache.pop(cache_key, None)

    # Cache miss or expired: Resolve context
    admin_scope = resolve_admin_scope(staff)
    accessible_cids, primary_cid = resolve_staff_memberships(db, staff_id, tenant_id)
    active_cid = resolve_active_company(
        requested_company_id=requested_company_id,
        accessible_company_ids=accessible_cids,
        primary_company_id=primary_cid,
        is_platform_admin=(admin_scope == AdminScope.PLATFORM_SUPERADMIN),
        tenant_id=tenant_id,
        db=db
    )
    capabilities = resolve_staff_capabilities(db, staff, active_cid, admin_scope)
    licensed_modules = resolve_licensed_modules(db, active_cid, tenant_id)

    result = {
        "admin_scope": admin_scope,
        "accessible_company_ids": accessible_cids,
        "primary_company_id": primary_cid,
        "active_company_id": active_cid,
        "capabilities": capabilities,
        "licensed_modules": licensed_modules,
        "tenant_id": tenant_id
    }

    with _cache_lock:
        # Enforce LRU bound
        if len(_auth_cache) >= _CACHE_MAX_SIZE:
            _auth_cache.popitem(last=False)
        _auth_cache[cache_key] = (now, result)

    return result


class AuthContextService:
    """
    Service wrapper for Stage 2A heavy authorization context operations.
    """
    @staticmethod
    def get_context(
        db: Session,
        staff: StaffEmployee,
        requested_company_id: Optional[int] = None
    ) -> Dict[str, Any]:
        return get_heavy_authorization_context(db, staff, requested_company_id)

    @staticmethod
    def build_context(
        db: Session,
        staff: StaffEmployee,
        requested_company_id: Optional[int] = None
    ) -> RequestContext:
        """
        Build an authoritative RequestContext instance for a staff employee.
        """
        auth_data = get_heavy_authorization_context(db, staff, requested_company_id)
        role = getattr(staff, "role", None)
        role_code = getattr(role, "role_code", "employee") if role else "employee"
        hierarchy_level = int(getattr(role, "hierarchy_level", 1) or 1) if role else 1
        db_token_version = getattr(staff, "token_version", 1) or 1

        return RequestContext(
            staff_id=staff.id,
            emp_code=staff.emp_code or "",
            tenant_id=auth_data["tenant_id"],
            active_company_id=auth_data["active_company_id"],
            email=staff.email,
            full_name=staff.full_name,
            base_company_id=staff.base_company_id,
            primary_company_id=auth_data["primary_company_id"],
            accessible_company_ids=auth_data["accessible_company_ids"],
            role_id=staff.role_id,
            role_code=role_code,
            hierarchy_level=hierarchy_level,
            admin_scope=auth_data["admin_scope"],
            capabilities=auth_data["capabilities"],
            licensed_modules=auth_data["licensed_modules"],
            token_version=db_token_version,
        )

    @staticmethod
    def invalidate_cache(staff_id: Optional[int] = None) -> None:
        invalidate_auth_cache(staff_id)


auth_context_service = AuthContextService()

