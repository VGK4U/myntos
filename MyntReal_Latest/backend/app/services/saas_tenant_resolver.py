"""
SaaS Tenant Entitlement & Menu Resolver Service (P0 Architecture)

Authoritative separation of dimensions:
1. TENANT SUBSCRIPTION: What modules the client purchased (platform_subscription_modules)
2. COMPANY LICENSED MODULES: What modules are enabled for the associated company
3. USER MODULE ASSIGNMENT: What modules are assigned to the individual user
4. ROLE / PERMISSION: Tenant Admin vs Tenant Staff
5. MENU VISIBILITY: Exact allowed menu tree & routes
6. ROUTE / API AUTHORIZATION: Explicit 403 Forbidden enforcement on unauthorized modules

Zero Magic Company IDs:
Context is resolved dynamically via PlatformClient, AssociatedCompany, and StaffEmployee models.
"""

from typing import List, Optional, Set, Tuple, Dict, Any
from dataclasses import dataclass, field
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.models.staff import StaffEmployee
from app.models.staff_accounts import AssociatedCompany
from app.models.platform_b2b import (
    PlatformClient,
    PlatformSubscription,
    PlatformSubscriptionModule,
    PlatformModule
)
from app.services.b2b_shadow import resolve_client_id_for_staff


MODULE_ALIASES: Dict[str, Set[str]] = {
    'CRM_LEADS': {'CRM_LEADS', 'CRM', 'CRM & LEADS'},
    'SOLAR_EV': {'SOLAR_EV', 'SOLAR', 'SOLAR & EV', 'WORKFLOWS'},
    'ACCOUNTS_GST': {'ACCOUNTS_GST', 'ACCOUNTS', 'ACCOUNTS_FINANCE'},
    'SERVICE_TICKETS': {'SERVICE_TICKETS', 'SERVICE', 'SERVICE DESK', 'SERVICE_DESK'},
    'INVENTORY_STOCK': {'INVENTORY_STOCK', 'INVENTORY', 'STOCK'},
    'STAFF_HRMS': {'STAFF_HRMS', 'HRMS', 'HR', 'STAFF_HR'},
    'TELEPHONY_SOFTPHONE': {'TELEPHONY_SOFTPHONE', 'TELEPHONY', 'SOFTPHONE'},
    'MARKETPLACE': {'MARKETPLACE', 'REAL_ESTATE', 'ZYNOVA'},
    'DIGITAL_CATALOG': {'DIGITAL_CATALOG', 'CATALOG'}
}


@dataclass
class TenantContext:
    is_saas_tenant: bool
    is_tenant_admin: bool
    client: Optional[PlatformClient] = None
    company: Optional[AssociatedCompany] = None
    entitled_subscription_modules: List[str] = field(default_factory=list)
    company_licensed_modules: List[str] = field(default_factory=list)
    user_assigned_modules: List[str] = field(default_factory=list)
    effective_modules: List[str] = field(default_factory=list)

    def has_module(self, module_code: str) -> bool:
        if not self.is_saas_tenant:
            # Internal platform users are not restricted by SaaS subscription modules
            return True
        
        target = module_code.upper().strip()
        aliases = MODULE_ALIASES.get(target, {target})
        return any(m in self.effective_modules for m in aliases)

    def require_module(self, module_code: str):
        if self.is_saas_tenant and not self.has_module(module_code):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied: Module '{module_code}' is not licensed or entitled for this tenant."
            )


def resolve_tenant_context(db: Session, staff: StaffEmployee) -> TenantContext:
    """
    Authoritatively resolves tenant, company, subscription, and user assignment context.
    Zero magic company IDs.
    """
    if not staff:
        return TenantContext(is_saas_tenant=False, is_tenant_admin=False)

    company: Optional[AssociatedCompany] = None
    if staff.base_company_id:
        company = db.query(AssociatedCompany).filter_by(id=staff.base_company_id).first()

    client_id = resolve_client_id_for_staff(db, staff)
    client: Optional[PlatformClient] = None
    if client_id:
        client = db.query(PlatformClient).filter_by(id=client_id).first()

    # Authoritative determination of SaaS tenant vs Internal Platform
    is_saas = False
    if client and not client.is_internal:
        is_saas = True
    elif company and (company.company_segment == "SEGMENT_B_SAAS" or company.company_type == "SAAS_CLIENT"):
        is_saas = True
    elif staff.role and staff.role.role_code and staff.role.role_code.startswith("tenant_"):
        is_saas = True
    elif staff.staff_type in ("TENANT_ADMIN", "SAAS_CLIENT", "SAAS_TENANT"):
        is_saas = True

    role_code = (staff.role.role_code.lower() if staff.role and staff.role.role_code else '')
    is_admin = (
        role_code == "tenant_admin" or
        staff.staff_type in ("TENANT_ADMIN", "SAAS_CLIENT") or
        getattr(staff, "admin_scope", "") == "CLIENT_SPECIFIC"
    )

    if not is_saas:
        return TenantContext(
            is_saas_tenant=False,
            is_tenant_admin=is_admin,
            client=client,
            company=company
        )

    # 1. Tenant Subscription Entitlements
    entitled_modules: List[str] = []
    if client:
        sub = db.query(PlatformSubscription).filter(
            PlatformSubscription.client_id == client.id,
            PlatformSubscription.status.in_(['active', 'trial'])
        ).first()
        if sub:
            mods = db.query(PlatformSubscriptionModule, PlatformModule).join(
                PlatformModule, PlatformSubscriptionModule.module_id == PlatformModule.id
            ).filter(
                PlatformSubscriptionModule.subscription_id == sub.id,
                PlatformSubscriptionModule.enabled == True
            ).all()
            entitled_modules = [pm.module_code.upper() for _, pm in mods if pm and pm.module_code]

    if not entitled_modules:
        raw_sub = (client.subscribed_modules if client and client.subscribed_modules else None) or \
                  (company.licensed_modules if company and company.licensed_modules else []) or []
        entitled_modules = [str(m).upper() for m in raw_sub]
    elif company and company.licensed_modules:
        entitled_modules = list(set(entitled_modules + [str(m).upper() for m in company.licensed_modules]))

    # 2. Company Licensed Modules
    company_licensed = [str(m).upper() for m in (company.licensed_modules or [])] if company else []
    if company_licensed:
        allowed_company = [m for m in entitled_modules if m in company_licensed]
    else:
        allowed_company = entitled_modules

    # 3. User Assigned Modules
    user_assigned = [str(m).upper() for m in (staff.assigned_modules or [])]

    # 4. Effective Modules
    if is_admin:
        effective = allowed_company
    else:
        if user_assigned:
            effective = [m for m in allowed_company if m in user_assigned]
        else:
            effective = allowed_company

    return TenantContext(
        is_saas_tenant=True,
        is_tenant_admin=is_admin,
        client=client,
        company=company,
        entitled_subscription_modules=entitled_modules,
        company_licensed_modules=company_licensed,
        user_assigned_modules=user_assigned,
        effective_modules=effective
    )


def get_saas_menu_tree(ctx: TenantContext) -> Tuple[List[Dict[str, Any]], Set[str], Dict[str, List[Dict[str, Any]]]]:
    """
    Constructs the authoritative SaaS menu tree and route list based on tenant context.
    Strictly adheres to:
    - NON-NEGOTIABLE SAAS CORE: /staff/my-tenant and /staff/tenant-users ONLY.
    - Entitled business modules: 1:1 mapped strictly from effective_modules.
    - ZERO corporate HRMS, Telephony Studio, or Marketplace leaks.
    """
    menus: List[Dict[str, Any]] = []
    allowed_routes: Set[str] = set()
    categorized: Dict[str, List[Dict[str, Any]]] = {}

    def add_menu(item: Dict[str, Any], category: str):
        menus.append(item)
        if item.get('route_path'):
            allowed_routes.add(item['route_path'])
            # Also allow clean path without trailing slash
            allowed_routes.add(item['route_path'].rstrip('/'))
        categorized.setdefault(category, []).append(item)

    # 1. CORE WORKSPACE (Mandatory for SaaS Tenants)
    add_menu({
        'id': 99001,
        'menu_code': 'TENANT_COMPANY_PROFILE',
        'menu_name': 'Company Profile',
        'menu_description': 'Tenant overview, branding and subscription profile',
        'route_path': '/staff/my-tenant',
        'menu_category': 'CORE WORKSPACE',
        'menu_icon': 'fas fa-building',
        'display_order': 1,
        'sidebar_section': 'core_workspace',
        'sidebar_section_title': 'CORE WORKSPACE',
        'sidebar_section_order': 0,
        'parent_section': None,
        'is_submenu': False,
        'audience_scope': 'staff',
        'can_view': True,
        'can_edit': True
    }, 'CORE WORKSPACE')

    if ctx.is_tenant_admin:
        add_menu({
            'id': 99002,
            'menu_code': 'TENANT_STAFF_MANAGEMENT',
            'menu_name': 'Staff & Users',
            'menu_description': 'Manage tenant team members, roles and module access',
            'route_path': '/staff/tenant-users',
            'menu_category': 'CORE WORKSPACE',
            'menu_icon': 'fas fa-users-gear',
            'display_order': 2,
            'sidebar_section': 'core_workspace',
            'sidebar_section_title': 'CORE WORKSPACE',
            'sidebar_section_order': 0,
            'parent_section': None,
            'is_submenu': False,
            'audience_scope': 'staff',
            'can_view': True,
            'can_edit': True
        }, 'CORE WORKSPACE')
        allowed_routes.add('/staff/my-tenant/users')

    # 2. CRM & LEADS
    if ctx.has_module('CRM_LEADS'):
        crm_items = [
            {
                'id': 99101,
                'menu_code': 'CRM_DASHBOARD',
                'menu_name': 'CRM Dashboard',
                'menu_description': 'Overview of lead performance, pipeline funnel, and conversion rates',
                'route_path': '/staff/crm/dashboard',
                'menu_category': 'CRM & LEADS',
                'menu_icon': 'fas fa-chart-line',
                'display_order': 1,
                'sidebar_section': 'crm_leads',
                'sidebar_section_title': 'CRM & LEADS',
                'sidebar_section_order': 1,
                'parent_section': None,
                'is_submenu': False,
                'audience_scope': 'staff',
                'can_view': True,
                'can_edit': True
            },
            {
                'id': 99102,
                'menu_code': 'CRM_MY_LEADS',
                'menu_name': 'My Leads',
                'menu_description': 'Leads assigned directly to your handler profile',
                'route_path': '/staff/my-leads',
                'menu_category': 'CRM & LEADS',
                'menu_icon': 'fas fa-user-check',
                'display_order': 2,
                'sidebar_section': 'crm_leads',
                'sidebar_section_title': 'CRM & LEADS',
                'sidebar_section_order': 1,
                'parent_section': None,
                'is_submenu': False,
                'audience_scope': 'staff',
                'can_view': True,
                'can_edit': True
            },
            {
                'id': 99103,
                'menu_code': 'CRM_STAFF_LEADS',
                'menu_name': 'Staff Leads',
                'menu_description': 'Team-wide lead assignment and handler performance view',
                'route_path': '/staff/leads',
                'menu_category': 'CRM & LEADS',
                'menu_icon': 'fas fa-users',
                'display_order': 3,
                'sidebar_section': 'crm_leads',
                'sidebar_section_title': 'CRM & LEADS',
                'sidebar_section_order': 1,
                'parent_section': None,
                'is_submenu': False,
                'audience_scope': 'staff',
                'can_view': True,
                'can_edit': True
            }
        ]
        if ctx.is_tenant_admin:
            crm_items.append({
                'id': 99104,
                'menu_code': 'TENANT_CRM_WORKFLOW_SETUP',
                'menu_name': 'CRM / Workflow Setup',
                'menu_description': 'Manage company branches, business segments, and staff routing',
                'route_path': '/staff/saas-crm-settings',
                'menu_category': 'CRM & LEADS',
                'menu_icon': 'fas fa-sliders',
                'display_order': 4,
                'sidebar_section': 'crm_leads',
                'sidebar_section_title': 'CRM & LEADS',
                'sidebar_section_order': 1,
                'parent_section': None,
                'is_submenu': False,
                'audience_scope': 'staff',
                'can_view': True,
                'can_edit': True
            })
            allowed_routes.add('/staff/saas-crm-settings')
            allowed_routes.add('/staff/my-tenant/crm-setup')

        for it in crm_items:
            add_menu(it, 'CRM & LEADS')

        # Allow /staff/crm/leads and other utility routes for direct access/drilldown
        allowed_routes.add('/staff/crm/leads')
        allowed_routes.add('/staff/crm/quotations')
        allowed_routes.add('/staff/crm/followups')
        allowed_routes.add('/staff/whatsapp-center')

    # 3. WORKFLOWS (Product Display: WORKFLOWS, module code: SOLAR_EV)
    if ctx.has_module('SOLAR_EV'):
        workflow_items = [
            {
                'id': 99201,
                'menu_code': 'WORKFLOW_EXEC_DASHBOARD',
                'menu_name': 'Executive Dashboard',
                'menu_description': 'Executive metrics, stage progression, and handler leaderboard',
                'route_path': '/staff/executive-dashboard',
                'menu_category': 'WORKFLOWS',
                'menu_icon': 'fas fa-chart-pie',
                'display_order': 1,
                'sidebar_section': 'workflows',
                'sidebar_section_title': 'WORKFLOWS',
                'sidebar_section_order': 2,
                'parent_section': None,
                'is_submenu': False,
                'audience_scope': 'staff',
                'can_view': True,
                'can_edit': True
            },
            {
                'id': 99202,
                'menu_code': 'WORKFLOW_CATEGORY_LEADS',
                'menu_name': 'Category-wise Leads',
                'menu_description': 'Segment-wise operational pipelines and document stages',
                'route_path': '/staff/mnr-leads',
                'menu_category': 'WORKFLOWS',
                'menu_icon': 'fas fa-layer-group',
                'display_order': 2,
                'sidebar_section': 'workflows',
                'sidebar_section_title': 'WORKFLOWS',
                'sidebar_section_order': 2,
                'parent_section': None,
                'is_submenu': False,
                'audience_scope': 'staff',
                'can_view': True,
                'can_edit': True
            }
        ]
        if ctx.is_tenant_admin and not ctx.has_module('CRM_LEADS'):
            workflow_items.append({
                'id': 99203,
                'menu_code': 'TENANT_CRM_WORKFLOW_SETUP',
                'menu_name': 'CRM / Workflow Setup',
                'menu_description': 'Manage company branches, business segments, and staff routing',
                'route_path': '/staff/saas-crm-settings',
                'menu_category': 'WORKFLOWS',
                'menu_icon': 'fas fa-sliders',
                'display_order': 3,
                'sidebar_section': 'workflows',
                'sidebar_section_title': 'WORKFLOWS',
                'sidebar_section_order': 2,
                'parent_section': None,
                'is_submenu': False,
                'audience_scope': 'staff',
                'can_view': True,
                'can_edit': True
            })
            allowed_routes.add('/staff/saas-crm-settings')
            allowed_routes.add('/staff/my-tenant/crm-setup')

        for it in workflow_items:
            add_menu(it, 'WORKFLOWS')

        # Allow category lead aliases for direct access
        allowed_routes.add('/staff/category-leads')
        allowed_routes.add('/staff/workflow-leads')


    # 4. SERVICE (Product Display: SERVICE, module code: SERVICE_TICKETS)
    if ctx.has_module('SERVICE_TICKETS'):
        service_items = [
            {
                'id': 99301,
                'menu_code': 'SERVICE_DASHBOARD',
                'menu_name': 'Service Dashboard',
                'menu_description': 'Overview of tickets, SLA timers, and repair statuses',
                'route_path': '/staff/service-tickets/dashboard',
                'menu_category': 'SERVICE',
                'menu_icon': 'fas fa-chart-line',
                'display_order': 1,
                'sidebar_section': 'service_tickets',
                'sidebar_section_title': 'SERVICE',
                'sidebar_section_order': 3,
                'parent_section': None,
                'is_submenu': False,
                'audience_scope': 'staff',
                'can_view': True,
                'can_edit': True
            },
            {
                'id': 99302,
                'menu_code': 'SERVICE_QUEUE',
                'menu_name': 'Service Queue',
                'menu_description': 'Active tickets, diagnosis, parts requests, and completion',
                'route_path': '/staff/service-tickets/queue',
                'menu_category': 'SERVICE',
                'menu_icon': 'fas fa-list-check',
                'display_order': 2,
                'sidebar_section': 'service_tickets',
                'sidebar_section_title': 'SERVICE',
                'sidebar_section_order': 3,
                'parent_section': None,
                'is_submenu': False,
                'audience_scope': 'staff',
                'can_view': True,
                'can_edit': True
            },
            {
                'id': 99303,
                'menu_code': 'SERVICE_RAISE_TICKET',
                'menu_name': 'Raise Ticket',
                'menu_description': 'Log a new customer service request or complaint',
                'route_path': '/staff/service-tickets/raise',
                'menu_category': 'SERVICE',
                'menu_icon': 'fas fa-plus-circle',
                'display_order': 3,
                'sidebar_section': 'service_tickets',
                'sidebar_section_title': 'SERVICE',
                'sidebar_section_order': 3,
                'parent_section': None,
                'is_submenu': False,
                'audience_scope': 'staff',
                'can_view': True,
                'can_edit': True
            },
            {
                'id': 99304,
                'menu_code': 'SERVICE_REPORTS',
                'menu_name': 'Service Reports',
                'menu_description': 'Service analytics, turnaround times, and resolution rates',
                'route_path': '/staff/service-tickets/reports',
                'menu_category': 'SERVICE',
                'menu_icon': 'fas fa-file-invoice',
                'display_order': 4,
                'sidebar_section': 'service_tickets',
                'sidebar_section_title': 'SERVICE',
                'sidebar_section_order': 3,
                'parent_section': None,
                'is_submenu': False,
                'audience_scope': 'staff',
                'can_view': True,
                'can_edit': True
            }
        ]
        for it in service_items:
            add_menu(it, 'SERVICE')

        # Canonical routes
        allowed_routes.add('/staff/service-tickets/dashboard')
        allowed_routes.add('/staff/service-tickets/queue')
        allowed_routes.add('/staff/service-tickets/raise')
        allowed_routes.add('/staff/service-tickets/reports')
        allowed_routes.add('/staff/service-tickets/procurement-queue')
        allowed_routes.add('/staff/service-tickets/procurement')
        # Route aliases
        allowed_routes.add('/staff/service-dashboard')
        allowed_routes.add('/staff/service-queue')
        allowed_routes.add('/staff/service-tickets')
        allowed_routes.add('/staff/service-raise-ticket')
        allowed_routes.add('/staff/service-reports')
        allowed_routes.add('/staff/service-procurement')

    # 5. ACCOUNTS & GST
    if ctx.has_module('ACCOUNTS_GST'):
        accounts_items = [
            {
                'id': 99401,
                'menu_code': 'SFMS_EXPENSE_ENTRIES',
                'menu_name': 'Expense Entries',
                'menu_description': 'Company operational expenses and vouchers',
                'route_path': '/staff/accounts/expense-entries',
                'menu_category': 'ACCOUNTS & GST',
                'menu_icon': 'fas fa-receipt',
                'display_order': 1,
                'sidebar_section': 'accounts',
                'sidebar_section_title': 'ACCOUNTS & GST',
                'sidebar_section_order': 4,
                'parent_section': None,
                'is_submenu': False,
                'audience_scope': 'staff',
                'can_view': True,
                'can_edit': True
            }
        ]
        for it in accounts_items:
            add_menu(it, 'ACCOUNTS & GST')

    # 6. TELEPHONY ADD-ON (Only if explicitly entitled)
    if ctx.has_module('TELEPHONY_SOFTPHONE'):
        telephony_items = [
            {
                'id': 99501,
                'menu_code': 'STAFF_AUTO_DIALER',
                'menu_name': 'Auto Dialer',
                'menu_description': 'Outbound campaign dialer',
                'route_path': '/staff/dialer',
                'menu_category': 'TELEPHONY',
                'menu_icon': 'fas fa-phone-volume',
                'display_order': 1,
                'sidebar_section': 'telephony',
                'sidebar_section_title': 'TELEPHONY',
                'sidebar_section_order': 5,
                'parent_section': None,
                'is_submenu': False,
                'audience_scope': 'staff',
                'can_view': True,
                'can_edit': True
            },
            {
                'id': 99502,
                'menu_code': 'STAFF_SOFTPHONE_CENTER',
                'menu_name': 'Calling & Softphone',
                'menu_description': 'WebRTC softphone dialer and session controls',
                'route_path': '/staff/softphone-center',
                'menu_category': 'TELEPHONY',
                'menu_icon': 'fas fa-headset',
                'display_order': 2,
                'sidebar_section': 'telephony',
                'sidebar_section_title': 'TELEPHONY',
                'sidebar_section_order': 5,
                'parent_section': None,
                'is_submenu': False,
                'audience_scope': 'staff',
                'can_view': True,
                'can_edit': True
            },
            {
                'id': 99503,
                'menu_code': 'STAFF_OPERATOR_CALLS',
                'menu_name': 'Operator Calls',
                'menu_description': 'Active call queues and logs',
                'route_path': '/staff/operator-calls',
                'menu_category': 'TELEPHONY',
                'menu_icon': 'fas fa-phone',
                'display_order': 3,
                'sidebar_section': 'telephony',
                'sidebar_section_title': 'TELEPHONY',
                'sidebar_section_order': 5,
                'parent_section': None,
                'is_submenu': False,
                'audience_scope': 'staff',
                'can_view': True,
                'can_edit': True
            }
        ]
        for it in telephony_items:
            add_menu(it, 'TELEPHONY')

    # 7. HRMS (Product Display: HRMS, module code: STAFF_HRMS)
    if ctx.has_module('STAFF_HRMS'):
        hrms_items = [
            # Employee Management
            {
                'id': 99599,
                'menu_code': 'HRMS_EMPLOYEES',
                'menu_name': 'Employees',
                'menu_description': 'Manage organization employees, designations, and status',
                'route_path': '/staff/employees',
                'menu_category': 'HRMS',
                'menu_icon': 'fas fa-users',
                'display_order': 1,
                'sidebar_section': 'staff_hrms',
                'sidebar_section_title': 'HRMS',
                'sidebar_section_order': 6,
                'parent_section': None,
                'is_submenu': False,
                'audience_scope': 'staff',
                'can_view': True,
                'can_edit': True
            },
            {
                'id': 99600,
                'menu_code': 'HRMS_EMPLOYEE_PROFILE',
                'menu_name': 'Employee Profile',
                'menu_description': 'Employee details, reporting manager, and contact information',
                'route_path': '/staff/employees?view=profile',
                'menu_category': 'HRMS',
                'menu_icon': 'fas fa-id-card',
                'display_order': 2,
                'sidebar_section': 'staff_hrms',
                'sidebar_section_title': 'HRMS',
                'sidebar_section_order': 6,
                'parent_section': None,
                'is_submenu': False,
                'audience_scope': 'staff',
                'can_view': True,
                'can_edit': True
            },
            # Attendance & Leaves
            {
                'id': 99601,
                'menu_code': 'HRMS_ATTENDANCE_SHEET',
                'menu_name': 'Attendance Sheet',
                'menu_description': 'Monthly employee attendance sheet, punch logs, and monthly summary',
                'route_path': '/staff/attendance-sheet',
                'menu_category': 'HRMS',
                'menu_icon': 'fas fa-calendar-check',
                'display_order': 3,
                'sidebar_section': 'staff_hrms',
                'sidebar_section_title': 'HRMS',
                'sidebar_section_order': 6,
                'parent_section': None,
                'is_submenu': False,
                'audience_scope': 'staff',
                'can_view': True,
                'can_edit': True
            },
            {
                'id': 99602,
                'menu_code': 'HRMS_MY_LEAVES',
                'menu_name': 'Leave Requests',
                'menu_description': 'Submit leave applications and check leave balances',
                'route_path': '/staff/my-leaves',
                'menu_category': 'HRMS',
                'menu_icon': 'fas fa-calendar-minus',
                'display_order': 2,
                'sidebar_section': 'staff_hrms',
                'sidebar_section_title': 'HRMS',
                'sidebar_section_order': 6,
                'parent_section': None,
                'is_submenu': False,
                'audience_scope': 'staff',
                'can_view': True,
                'can_edit': True
            },
            {
                'id': 99603,
                'menu_code': 'HRMS_LEAVE_APPROVALS',
                'menu_name': 'Leave Approvals',
                'menu_description': 'Review and approve subordinate leave requests',
                'route_path': '/staff/leave-approvals',
                'menu_category': 'HRMS',
                'menu_icon': 'fas fa-user-check',
                'display_order': 3,
                'sidebar_section': 'staff_hrms',
                'sidebar_section_title': 'HRMS',
                'sidebar_section_order': 6,
                'parent_section': None,
                'is_submenu': False,
                'audience_scope': 'staff',
                'can_view': True,
                'can_edit': True
            },
            {
                'id': 99604,
                'menu_code': 'HRMS_TEAM_ATTENDANCE_SUMMARY',
                'menu_name': 'Attendance Summary',
                'menu_description': 'Team attendance statistics and daily presence overview',
                'route_path': '/staff/team-attendance-summary',
                'menu_category': 'HRMS',
                'menu_icon': 'fas fa-clipboard-user',
                'display_order': 4,
                'sidebar_section': 'staff_hrms',
                'sidebar_section_title': 'HRMS',
                'sidebar_section_order': 6,
                'parent_section': None,
                'is_submenu': False,
                'audience_scope': 'staff',
                'can_view': True,
                'can_edit': True
            },
            # Field Mobility & Journeys
            {
                'id': 99605,
                'menu_code': 'HRMS_TEAM_JOURNEYS',
                'menu_name': 'Team Journeys',
                'menu_description': 'Live field journeys and team travel tracking',
                'route_path': '/staff/team-journeys',
                'menu_category': 'HRMS',
                'menu_icon': 'fas fa-route',
                'display_order': 5,
                'sidebar_section': 'staff_hrms',
                'sidebar_section_title': 'HRMS',
                'sidebar_section_order': 6,
                'parent_section': None,
                'is_submenu': False,
                'audience_scope': 'staff',
                'can_view': True,
                'can_edit': True
            },
            {
                'id': 99606,
                'menu_code': 'HRMS_MY_JOURNEYS',
                'menu_name': 'My Journeys',
                'menu_description': 'Personal travel history, kilometer logging, and field visits',
                'route_path': '/staff/my-journeys',
                'menu_category': 'HRMS',
                'menu_icon': 'fas fa-map-location-dot',
                'display_order': 6,
                'sidebar_section': 'staff_hrms',
                'sidebar_section_title': 'HRMS',
                'sidebar_section_order': 6,
                'parent_section': None,
                'is_submenu': False,
                'audience_scope': 'staff',
                'can_view': True,
                'can_edit': True
            },
            {
                'id': 99607,
                'menu_code': 'HRMS_ALL_JOURNEYS',
                'menu_name': 'All Journeys',
                'menu_description': 'Comprehensive organization travel and mobility tracking',
                'route_path': '/staff/all-journeys',
                'menu_category': 'HRMS',
                'menu_icon': 'fas fa-globe',
                'display_order': 7,
                'sidebar_section': 'staff_hrms',
                'sidebar_section_title': 'HRMS',
                'sidebar_section_order': 6,
                'parent_section': None,
                'is_submenu': False,
                'audience_scope': 'staff',
                'can_view': True,
                'can_edit': True
            },
            # Tasks, Day Planner, KRA & Timesheets
            {
                'id': 99608,
                'menu_code': 'HRMS_TASKS_TRACKER',
                'menu_name': 'Tasks Tracker',
                'menu_description': 'Manage team tasks, assignments, and due dates',
                'route_path': '/staff/tasks/tracker',
                'menu_category': 'HRMS',
                'menu_icon': 'fas fa-tasks',
                'display_order': 8,
                'sidebar_section': 'staff_hrms',
                'sidebar_section_title': 'HRMS',
                'sidebar_section_order': 6,
                'parent_section': None,
                'is_submenu': False,
                'audience_scope': 'staff',
                'can_view': True,
                'can_edit': True
            },
            {
                'id': 99609,
                'menu_code': 'HRMS_DAY_PLANNER',
                'menu_name': 'Day Planner',
                'menu_description': 'Plan day activities, client visits, and priorities',
                'route_path': '/staff/tasks/day-planner',
                'menu_category': 'HRMS',
                'menu_icon': 'fas fa-calendar-day',
                'display_order': 9,
                'sidebar_section': 'staff_hrms',
                'sidebar_section_title': 'HRMS',
                'sidebar_section_order': 6,
                'parent_section': None,
                'is_submenu': False,
                'audience_scope': 'staff',
                'can_view': True,
                'can_edit': True
            },
            {
                'id': 99610,
                'menu_code': 'HRMS_MY_KRAS',
                'menu_name': 'My KRAs',
                'menu_description': 'Key result areas, targets, and performance scorecards',
                'route_path': '/staff/my-kras',
                'menu_category': 'HRMS',
                'menu_icon': 'fas fa-bullseye',
                'display_order': 10,
                'sidebar_section': 'staff_hrms',
                'sidebar_section_title': 'HRMS',
                'sidebar_section_order': 6,
                'parent_section': None,
                'is_submenu': False,
                'audience_scope': 'staff',
                'can_view': True,
                'can_edit': True
            },
            {
                'id': 99611,
                'menu_code': 'HRMS_TIMESHEET',
                'menu_name': 'Timesheet',
                'menu_description': 'Daily time logs and project/task hour approvals',
                'route_path': '/staff/timesheet',
                'menu_category': 'HRMS',
                'menu_icon': 'fas fa-clock',
                'display_order': 11,
                'sidebar_section': 'staff_hrms',
                'sidebar_section_title': 'HRMS',
                'sidebar_section_order': 6,
                'parent_section': None,
                'is_submenu': False,
                'audience_scope': 'staff',
                'can_view': True,
                'can_edit': True
            }
        ]
        for it in hrms_items:
            add_menu(it, 'HRMS')

        # Canonical routes and route aliases for HRMS
        allowed_routes.update([
            '/staff/attendance-sheet',
            '/staff/attendance/sheet',
            '/staff/my-attendance',
            '/staff/my-leaves',
            '/staff/leave-management',
            '/staff/leave-approvals',
            '/staff/team-attendance',
            '/staff/team-attendance-summary',
            '/staff/attendance/summary',
            '/staff/attendance-reports',
            '/staff/attendance-exceptions',
            '/staff/attendance-computation',
            '/staff/my-journeys',
            '/staff/journeys/my',
            '/staff/team-journeys',
            '/staff/journeys/team',
            '/staff/all-journeys',
            '/staff/journeys/all',
            '/staff/all-location-tracker',
            '/staff/all-location-history',
            '/staff/team-live-tracker',
            '/staff/team-location-tracker',
            '/staff/my-location-history',
            '/staff/tasks/tracker',
            '/staff/tasks/day-planner',
            '/staff/tasks/assigned-to-me',
            '/staff/tasks/assigned-by-me',
            '/staff/tasks/assigned-by-me-v2',
            '/staff/tasks/team-activities',
            '/staff/tasks/task-reviews',
            '/staff/task-review',
            '/staff/my-kras',
            '/staff/kra/my',
            '/staff/kra-status',
            '/staff/kra-templates',
            '/staff/kra-tracking-sheet',
            '/staff/timesheet',
            '/staff/my-timesheet',
            '/staff/timesheet-approval',
            '/staff/employees',
            '/staff/employee-directory',
            '/staff/employee-hierarchy',
        ])

    return menus, allowed_routes, categorized
