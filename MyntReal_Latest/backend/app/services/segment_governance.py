"""
Segment Governance & Change Scope Architecture Service (DC_SAAS_SEGMENT_001)
Governs:
- Segment A: Internal / Group Companies
- Segment B: Independent Multi-Tenant SaaS Clients
- Inheritance hierarchy: PLATFORM -> SEGMENT DEFAULT -> CLIENT-SPECIFIC OVERRIDE
- Change Scope Recording & Audit Logging
"""

import logging
from typing import Optional, Dict, Any, List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import desc, or_

from app.models.staff_accounts import AssociatedCompany, PlatformChangeScopeLog, SegmentGovernanceConfig
from app.models.staff import StaffEmployee
from app.models.base import get_indian_time

logger = logging.getLogger(__name__)

# Canonical module identifiers available to Segment B (SaaS Clients)
SAAS_GLOBAL_MODULE_CATALOG = {
    "CRM_LEADS": {
        "name": "CRM & Leads",
        "description": "Lead management, sales pipeline, call tracking, and WhatsApp integration",
        "default_for_saas": True,
    },
    "SERVICE_TICKETS": {
        "name": "Service Desk & Tickets",
        "description": "Customer complaints, service tickets, and field technician dispatch",
        "default_for_saas": True,
    },
    "SOLAR_EV": {
        "name": "Solar / EV Mobility",
        "description": "EV vehicle sales, solar installations, battery tracking, and warranties",
        "default_for_saas": False,
    },
    "ACCOUNTS_GST": {
        "name": "Accounts & GST Invoicing",
        "description": "Multi-company ledgers, GST invoices, purchase registers, and cash accounts",
        "default_for_saas": False,
    },
    "INVENTORY": {
        "name": "Inventory & Warehouses",
        "description": "Stock management, stock ledger, transfers, and barcode tracking",
        "default_for_saas": False,
    },
    "STAFF_HRMS": {
        "name": "Staff HRMS & Attendance",
        "description": "Employee directory, GPS clock-in, attendance tracking, and manager approvals",
        "default_for_saas": False,
    }
}


class SegmentGovernanceService:
    """Service governing company segments, configuration inheritance, and scope control."""

    @staticmethod
    def record_change_scope(
        db: Session,
        change_title: str,
        scope_type: str,
        change_category: str = "CONFIG",
        target_tenant_id: Optional[int] = None,
        target_module: Optional[str] = None,
        old_value: Optional[Dict[str, Any]] = None,
        new_value: Optional[Dict[str, Any]] = None,
        operator: Optional[StaffEmployee] = None,
        notes: Optional[str] = None
    ) -> PlatformChangeScopeLog:
        """
        Record any platform/segment/client configuration change with mandatory explicit scope.
        scope_type must be one of:
        - SEGMENT_A: Internal only
        - SEGMENT_B: All SaaS Clients
        - CLIENT_SPECIFIC: Specific SaaS Client (target_tenant_id required)
        - BOTH_SEGMENTS: Explicitly applies to both Segment A & Segment B
        """
        valid_scopes = ["SEGMENT_A", "SEGMENT_B", "CLIENT_SPECIFIC", "BOTH_SEGMENTS"]
        scope_upper = (scope_type or "").upper().strip()
        if scope_upper not in valid_scopes:
            raise ValueError(f"Invalid scope_type '{scope_type}'. Must be one of: {valid_scopes}")
        
        if scope_upper == "CLIENT_SPECIFIC" and not target_tenant_id:
            raise ValueError("target_tenant_id is required when scope_type is CLIENT_SPECIFIC")

        log = PlatformChangeScopeLog(
            change_title=change_title,
            change_category=change_category,
            scope_type=scope_upper,
            target_tenant_id=target_tenant_id,
            target_module=target_module,
            old_value=old_value,
            new_value=new_value,
            created_by_id=operator.id if operator else None,
            created_by_name=getattr(operator, 'full_name', None) or getattr(operator, 'emp_code', 'SYSTEM'),
            notes=notes,
            created_at=get_indian_time()
        )
        db.add(log)
        db.commit()
        db.refresh(log)
        logger.info(f"[DC-SCOPE-GOVERNANCE] Recorded change '{change_title}' with scope={scope_upper}, target={target_tenant_id}")
        return log

    @staticmethod
    def get_effective_config(
        db: Session,
        config_key: str,
        tenant_id: Optional[int] = None,
        segment: str = "SEGMENT_B_SAAS",
        default_val: Any = None
    ) -> Any:
        """
        Resolves effective config following the inheritance model:
        1. CLIENT-SPECIFIC OVERRIDE (if tenant_id supplied and override exists)
        2. SEGMENT DEFAULT (SEGMENT_A or SEGMENT_B)
        3. PLATFORM DEFAULT
        4. default_val fallback
        """
        # 1. Check Client-Specific Override
        if tenant_id:
            client_override = db.query(SegmentGovernanceConfig).filter(
                SegmentGovernanceConfig.scope_type == "CLIENT_SPECIFIC",
                SegmentGovernanceConfig.tenant_id == tenant_id,
                SegmentGovernanceConfig.config_key == config_key,
                SegmentGovernanceConfig.is_active == True
            ).first()
            if client_override and client_override.config_value is not None:
                return client_override.config_value.get("value", client_override.config_value)

        # 2. Check Segment Default
        seg_scope = "SEGMENT_B" if "B" in segment.upper() or "SAAS" in segment.upper() else "SEGMENT_A"
        segment_def = db.query(SegmentGovernanceConfig).filter(
            SegmentGovernanceConfig.scope_type == seg_scope,
            SegmentGovernanceConfig.config_key == config_key,
            SegmentGovernanceConfig.is_active == True
        ).first()
        if segment_def and segment_def.config_value is not None:
            return segment_def.config_value.get("value", segment_def.config_value)

        # 3. Check Platform Global Default
        platform_def = db.query(SegmentGovernanceConfig).filter(
            SegmentGovernanceConfig.scope_type == "PLATFORM",
            SegmentGovernanceConfig.config_key == config_key,
            SegmentGovernanceConfig.is_active == True
        ).first()
        if platform_def and platform_def.config_value is not None:
            return platform_def.config_value.get("value", platform_def.config_value)

        return default_val

    @staticmethod
    def is_module_licensed_for_tenant(
        db: Session,
        module_key: str,
        tenant_id: int
    ) -> bool:
        """
        Determines whether a module is active for a given tenant:
        - Must be an active company
        - If Segment A (Internal): all internal modules accessible per role
        - If Segment B (SaaS): must be in tenant's licensed_modules AND not overridden/disabled
        """
        company = db.query(AssociatedCompany).filter_by(id=tenant_id).first()
        if not company or not company.is_active:
            return False

        # Segment A (Internal): Full operational access per role
        if company.company_segment == "SEGMENT_A_INTERNAL" or company.company_type != "SAAS_CLIENT":
            return True

        # Segment B (SaaS Client): Check licensed_modules
        tenant_modules = company.licensed_modules or []
        tenant_modules_upper = [str(m).upper() for m in tenant_modules]
        
        # Canonical normalization
        mod_norm = module_key.upper().strip()
        is_licensed = (mod_norm in tenant_modules_upper) or any(mod_norm in m or m in mod_norm for m in tenant_modules_upper)
        
        # Check if explicitly disabled via client override
        override_val = SegmentGovernanceService.get_effective_config(
            db=db,
            config_key=f"module_enabled_{mod_norm}",
            tenant_id=tenant_id,
            segment=company.company_segment,
            default_val=None
        )
        if override_val is not None:
            return bool(override_val)

        return is_licensed

    @staticmethod
    def list_change_logs(
        db: Session,
        page: int = 1,
        page_size: int = 50,
        scope_filter: Optional[str] = None
    ) -> Tuple[List[PlatformChangeScopeLog], int]:
        """List change scope governance audit records."""
        query = db.query(PlatformChangeScopeLog)
        if scope_filter and scope_filter.upper() != "ALL":
            query = query.filter(PlatformChangeScopeLog.scope_type == scope_filter.upper())
        
        total = query.count()
        logs = query.order_by(desc(PlatformChangeScopeLog.created_at)).offset((page - 1) * page_size).limit(page_size).all()
        return logs, total

    @staticmethod
    def resolve_admin_scope(employee: StaffEmployee) -> str:
        """
        Determines the effective administrative scope of an authenticated user:
        - 'PLATFORM': VGK4U Supreme / Platform Admin (e.g. MR10001, vgk4u role)
        - 'SEGMENT_B': SaaS Segment Administrator (e.g. ZMP18080088, saas_segment_admin role)
        - 'SEGMENT_A': Internal Group Staff
        - 'CLIENT_SPECIFIC': Dedicated Tenant Admin or Client Staff (e.g. TECO_ADMIN, ZYLOG_ADMIN, AIS_ADMIN)
        """
        if not employee:
            return "CLIENT_SPECIFIC"

        # Explicit admin_scope on user record
        scope_attr = getattr(employee, "admin_scope", None)
        if scope_attr and scope_attr.upper() in ["PLATFORM", "SEGMENT_A", "SEGMENT_B", "CLIENT_SPECIFIC"]:
            return scope_attr.upper()

        role_code = employee.role.role_code if employee.role else ""
        staff_type = getattr(employee, "staff_type", "") or ""

        # Level 1: Platform Supreme
        if employee.id == 1 or employee.emp_code == "MR10001" or role_code in ["vgk4u", "super_admin"] or staff_type in ["VGK4U", "VGK4U Supreme"]:
            return "PLATFORM"

        # Level 2: SaaS Segment Administrator
        if role_code == "saas_segment_admin" or staff_type == "SAAS_SEGMENT_ADMIN" or employee.emp_code == "ZMP18080088":
            return "SEGMENT_B"

        # Level 3: Tenant Administrator or SaaS Client Staff
        if role_code == "tenant_admin" or staff_type in ["TENANT_ADMIN", "SAAS_CLIENT"]:
            return "CLIENT_SPECIFIC"

        # Default internal staff
        return "SEGMENT_A"

    @staticmethod
    def get_allowed_company_ids_for_user(db: Session, employee: StaffEmployee) -> Optional[List[int]]:
        """
        Resolves the list of authorized company IDs for an employee based on scope.
        Returns:
        - None: Full unrestricted platform access across all companies (Platform Supreme)
        - List[int]: Explicit subset of allowed company IDs
        """
        if not employee:
            return []

        scope = SegmentGovernanceService.resolve_admin_scope(employee)

        if scope == "PLATFORM":
            # Level 1: Supreme Platform Administrator sees all entities
            return None

        if scope == "SEGMENT_B":
            # Level 2: SaaS Segment Administrator dynamically sees all Segment B SaaS companies
            comps = db.query(AssociatedCompany.id).filter(
                AssociatedCompany.company_segment == "SEGMENT_B_SAAS",
                AssociatedCompany.is_active == True
            ).all()
            return [c[0] for c in comps]

        if scope == "SEGMENT_A":
            # Segment A: Internal staff sees assigned internal companies
            assigned = getattr(employee, "data_companies", []) or []
            assigned_ids = []
            if isinstance(assigned, list):
                for item in assigned:
                    if isinstance(item, int):
                        assigned_ids.append(item)
                    elif isinstance(item, dict) and "company_id" in item:
                        assigned_ids.append(item["company_id"])
            if employee.base_company_id and employee.base_company_id not in assigned_ids:
                assigned_ids.append(employee.base_company_id)

            if not assigned_ids:
                assigned_ids = [employee.base_company_id] if employee.base_company_id else []

            # Filter to Segment A companies only
            if assigned_ids:
                seg_a_comps = db.query(AssociatedCompany.id).filter(
                    AssociatedCompany.id.in_(assigned_ids),
                    AssociatedCompany.company_segment == "SEGMENT_A_INTERNAL"
                ).all()
                return [c[0] for c in seg_a_comps]
            return []

        # Level 3: CLIENT_SPECIFIC (Tenant Admin or Tenant Employee)
        if employee.base_company_id:
            return [employee.base_company_id]
        return []

    @staticmethod
    def authorize_company_access(db: Session, employee: StaffEmployee, company_id: int) -> bool:
        """
        Validates whether the employee has authorization to access the specified company.
        Server-side security check.
        """
        if not employee or not company_id:
            return False

        scope = SegmentGovernanceService.resolve_admin_scope(employee)
        if scope == "PLATFORM":
            return True

        allowed_ids = SegmentGovernanceService.get_allowed_company_ids_for_user(db, employee)
        if allowed_ids is None:
            return True

        return company_id in allowed_ids

    @staticmethod
    def authorize_segment_access(db: Session, employee: StaffEmployee, segment: str) -> bool:
        """
        Validates whether the employee has authorization to access a segment.
        """
        if not employee or not segment:
            return False

        scope = SegmentGovernanceService.resolve_admin_scope(employee)
        if scope == "PLATFORM":
            return True

        seg_norm = segment.upper().strip()
        if "B" in seg_norm or "SAAS" in seg_norm:
            return scope in ["SEGMENT_B", "PLATFORM", "CLIENT_SPECIFIC"]
        else:
            return scope in ["SEGMENT_A", "PLATFORM"]

