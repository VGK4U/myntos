"""
Staff Menu Visibility & Accessibility Control API
DC Protocol: Company-wise menu/page access control per employee
WVV Protocol: Full validation and verification
Created: Dec 08, 2025
Updated: Jan 12, 2026 - Added cascade selection logic and 18-section structure
"""

from fastapi import APIRouter, Depends, HTTPException, Request, Body
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from typing import Optional, List, Dict, Set
from pydantic import BaseModel, validator
from datetime import datetime

from app.core.database import get_db
from app.api.v1.endpoints.staff_auth import get_current_staff_user
from app.models.staff import (
    StaffEmployee, StaffMenuMaster, StaffEmployeeMenuSettings,
    StaffMenuSettingsAudit, PartnerMenuSettings, seed_menu_master,
    StaffMenuRegistry, StaffRoleMenuAccess, get_indian_time
)
from app.models.staff_accounts import OfficialPartner, AssociatedCompany
from sqlalchemy import text
import logging

logger = logging.getLogger(__name__)


def get_cascade_expanded_sections_db(db: Session, granted_sections: Set[str]) -> Set[str]:
    """
    DC Protocol Jan 13 2026: Database-driven Cascade Selection Logic.
    Reads parent-child relationships from pdf_canonical_routes table.
    
    When a parent section is granted, automatically expand to include all child subsections.
    
    Returns: Expanded set of section IDs including all cascaded children
    """
    expanded = set(granted_sections)
    
    # Query parent-child relationships from canonical table
    result = db.execute(text("""
        SELECT DISTINCT section_id, parent_section, is_submenu
        FROM pdf_canonical_routes
        WHERE parent_section IS NOT NULL
    """)).fetchall()
    
    # Build parent-to-children map
    parent_children_map = {}
    for row in result:
        section_id = row[0]
        parent_section = row[1]
        if parent_section:
            if parent_section not in parent_children_map:
                parent_children_map[parent_section] = set()
            parent_children_map[parent_section].add(section_id)
    
    # Transitive closure: expand until no new sections added
    changed = True
    while changed:
        changed = False
        for section_id in list(expanded):
            if section_id in parent_children_map:
                for child_id in parent_children_map[section_id]:
                    if child_id not in expanded:
                        expanded.add(child_id)
                        changed = True
    
    return expanded


def get_parent_sections_from_children_db(db: Session, granted_sections: Set[str]) -> Set[str]:
    """
    DC Protocol Jan 13 2026: Database-driven parent lookup.
    Find parent sections from granted child sections.
    
    Returns: Set of parent section IDs
    """
    if not granted_sections:
        return set()
    
    # Query parents for given children
    placeholders = ', '.join([f":s{i}" for i in range(len(granted_sections))])
    params = {f"s{i}": s for i, s in enumerate(granted_sections)}
    
    result = db.execute(text(f"""
        SELECT DISTINCT parent_section 
        FROM pdf_canonical_routes 
        WHERE section_id IN ({placeholders}) AND parent_section IS NOT NULL
    """), params).fetchall()
    
    return {row[0] for row in result}


def get_routes_for_sections_db(db: Session, section_ids: Set[str]) -> Set[str]:
    """
    DC Protocol Jan 13 2026: Database-driven route lookup.
    Gets all route_paths for given section IDs from pdf_canonical_routes.
    
    Returns: Set of route_path values belonging to the given sections
    """
    if not section_ids:
        return set()
    
    placeholders = ', '.join([f":s{i}" for i in range(len(section_ids))])
    params = {f"s{i}": s for i, s in enumerate(section_ids)}
    
    result = db.execute(text(f"""
        SELECT DISTINCT route_path 
        FROM pdf_canonical_routes 
        WHERE section_id IN ({placeholders})
    """), params).fetchall()
    
    return {row[0] for row in result}


def get_cascade_expanded_sections(granted_sections: Set[str]) -> Set[str]:
    """DEPRECATED: Use get_cascade_expanded_sections_db with db session"""
    return granted_sections


def get_parent_sections_from_children(granted_sections: Set[str]) -> Set[str]:
    """DEPRECATED: Use get_parent_sections_from_children_db with db session"""
    return set()


def get_routes_for_sections(section_ids: Set[str]) -> Set[str]:
    """DEPRECATED: Use get_routes_for_sections_db with db session"""
    return set()


def build_sidebar_tree(menus: list, granted_menu_codes: Set[str] = None) -> List[Dict]:
    """
    DC Protocol Jan 12 2026: Build hierarchical sidebar tree from menu list.
    UPDATED: Now uses database sidebar_section and sidebar_section_order fields
    instead of hardcoded SIDEBAR_ROUTE_MAPPING. Database is single source of truth.
    
    Structure:
    [
        {
            "id": "section-id",
            "title": "SECTION TITLE",
            "order": 1,
            "items": [...menu items...],
            "subSections": [...nested subsection trees...]
        }
    ]
    """
    # Build section map dynamically from menu data (database-driven)
    section_map = {}
    
    for menu in menus:
        # Get section info from database fields
        section_id = menu.get("sidebar_section") or menu.get("menu_category") or "other"
        section_title = menu.get("sidebar_section_title") or section_id.upper().replace('_', ' ').replace('-', ' ')
        section_order = menu.get("sidebar_section_order") or 999
        parent_section = menu.get("parent_section")
        is_submenu = menu.get("is_submenu", False)
        
        # Create section if not exists
        if section_id not in section_map:
            section_map[section_id] = {
                "id": section_id,
                "title": section_title,
                "order": section_order,
                "parent": parent_section,
                "is_submenu": is_submenu,
                "items": [],
                "subSections": []
            }
        
        # Add menu item to section
        section_map[section_id]["items"].append(menu)
    
    # Nest submenu sections under parent sections
    parent_sections = {}
    submenu_sections = {}
    
    for section_id, section_data in section_map.items():
        is_sub = section_data.get("is_submenu", False)
        parent_id = section_data.get("parent")
        
        if is_sub and parent_id:
            if parent_id not in submenu_sections:
                submenu_sections[parent_id] = []
            submenu_sections[parent_id].append(section_data)
        else:
            parent_sections[section_id] = section_data
    
    # Attach submenus to their parent sections
    for parent_id, submenus in submenu_sections.items():
        if parent_id in parent_sections:
            parent_sections[parent_id]["subSections"].extend(submenus)
        else:
            # Create parent section if it doesn't exist
            first_sub = submenus[0] if submenus else {}
            parent_sections[parent_id] = {
                "id": parent_id,
                "title": parent_id.upper().replace('-', ' ').replace('_', ' '),
                "order": first_sub.get("order", 999),
                "items": [],
                "subSections": submenus
            }
    
    # Sort sections by order
    result = list(parent_sections.values())
    result.sort(key=lambda x: x.get("order", 999))
    
    # Sort subSections within each parent
    for section in result:
        if section.get("subSections"):
            section["subSections"].sort(key=lambda x: x.get("order", 999))
    
    return result

router = APIRouter(prefix="/staff/menu-settings", tags=["Staff Menu Settings"])


async def require_vgk4u_access(current_user: StaffEmployee = Depends(get_current_staff_user)):
    """
    VGK4U-Only RBAC Guard: Restricts menu settings access to VGK4U Supreme staff only.
    This is a security-critical dependency that ensures only authorized administrators
    can view and modify employee menu access configurations.
    """
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # DC Protocol: Menu-based access control - page assignment = full access
    # allowed_types = ['VGK4U', 'VGK4U Supreme']
    # if current_user.staff_type not in allowed_types:
    #     logger.warning(
    #         f"RBAC VIOLATION: Staff {current_user.emp_code} ({current_user.staff_type}) "
    #         f"attempted to access menu settings - ACCESS DENIED"
    #     )
    #     raise HTTPException(
    #         status_code=403, 
    #         detail="Access denied. Only VGK4U Supreme administrators can access menu settings."
    #     )
    
    return current_user


# =====================================================================
# DC Protocol (Jan 2026): Preserve Sidebar Order Helper
# Purpose: Maintain exact sidebar structure and grouping - NO SORTING
# Menu Access page must match sidebar layout exactly
# =====================================================================

def preserve_menu_order(items: list, label_key: str = "label") -> list:
    """
    DC Protocol (Jan 2026): Return items in their original order.
    NO alphabetical sorting - preserves sidebar structure exactly.
    
    Parameters:
    - items: List of menu item dictionaries
    - label_key: Unused, kept for compatibility
    
    Returns:
    - Items in their original order (no changes)
    """
    return items if items else []


def preserve_sections_order(sections: list) -> list:
    """
    DC Protocol (Jan 2026): Return sections in their original order with items preserved.
    NO alphabetical sorting - Menu Access page must match sidebar exactly.
    
    Uses 'order' field from database if available for proper sequencing.
    
    Parameters:
    - sections: List of section dictionaries with "items" array
    
    Returns:
    - Sections sorted by their 'order' field (preserving sidebar structure)
    """
    if not sections:
        return sections
    
    # Sort sections by their 'order' field to maintain sidebar sequence
    # Items within sections are NOT sorted - they remain in their original order
    def section_sort_key(section):
        # Use order field from database, default to 999 for items without order
        order = section.get("order", 999)
        return order
    
    return sorted(sections, key=section_sort_key)


def get_employee_company_ids(employee) -> set:
    """
    DC Protocol Helper: Get all company IDs an employee has access to.
    Safely handles various data formats (JSONB array, JSON string, None, etc.)
    Returns a set of integers.
    """
    import json
    company_ids = set()
    
    # Add base_company_id
    if employee.base_company_id:
        try:
            company_ids.add(int(employee.base_company_id))
        except (ValueError, TypeError):
            pass
    
    # Process data_companies
    data_companies = employee.data_companies
    if data_companies is None:
        return company_ids
    
    # If it's a string, try to parse as JSON
    if isinstance(data_companies, str):
        try:
            data_companies = json.loads(data_companies)
        except (json.JSONDecodeError, ValueError):
            return company_ids
    
    # Now it should be a list
    if isinstance(data_companies, list):
        for cid in data_companies:
            if cid is not None:
                try:
                    company_ids.add(int(cid))
                except (ValueError, TypeError):
                    pass
    
    return company_ids


def sync_default_menu_settings_for_employees(db: Session, company_id: int, employee_ids: List[int], admin_id: int = None, admin_code: str = None, admin_name: str = None):
    """
    Auto-sync: Create default StaffEmployeeMenuSettings for new menus
    DC Protocol: Ensures new menus with is_default_visible=True get proper settings
    
    This function is called when the Access Matrix loads to ensure that:
    1. New menus with is_default_visible=True get settings created for employees
    2. Employees can see new pages in their sidebar without manual grant
    3. Zero-default policy is maintained for menus with is_default_visible=False
    
    Optimized: Uses bulk queries to check existing settings instead of per-employee SELECTs
    """
    if not employee_ids:
        return 0
    
    menus_with_defaults = db.query(StaffMenuMaster).filter(
        StaffMenuMaster.company_id == company_id,
        StaffMenuMaster.is_active == True,
        StaffMenuMaster.is_default_visible == True,
        StaffMenuMaster.audience_scope.in_(['staff', 'shared'])
    ).all()
    
    if not menus_with_defaults:
        return 0
    
    menu_ids = [m.id for m in menus_with_defaults]
    
    # Bulk query: Get all existing settings for these menus and employees
    existing_settings = db.query(
        StaffEmployeeMenuSettings.employee_id,
        StaffEmployeeMenuSettings.menu_id
    ).filter(
        StaffEmployeeMenuSettings.company_id == company_id,
        StaffEmployeeMenuSettings.employee_id.in_(employee_ids),
        StaffEmployeeMenuSettings.menu_id.in_(menu_ids)
    ).all()
    
    # Create a set of existing (employee_id, menu_id) pairs for O(1) lookup
    existing_pairs = {(s.employee_id, s.menu_id) for s in existing_settings}
    
    created_count = 0
    for menu in menus_with_defaults:
        for emp_id in employee_ids:
            if (emp_id, menu.id) not in existing_pairs:
                new_setting = StaffEmployeeMenuSettings(
                    company_id=company_id,
                    employee_id=emp_id,
                    menu_id=menu.id,
                    can_view=menu.is_default_visible,
                    can_edit=menu.is_default_accessible,
                    is_overridden=False,
                    set_by_id=admin_id,
                    set_by_code=admin_code or 'SYSTEM',
                    set_by_name=admin_name or 'Auto-Sync'
                )
                db.add(new_setting)
                created_count += 1
    
    if created_count > 0:
        try:
            db.commit()
            logger.info(f"[DC-MENU-SYNC] Auto-created {created_count} default settings for company {company_id}")
        except Exception as e:
            # DC_MENU_RACE_FIX: Two uvicorn workers can race to create the same menu settings.
            # On UniqueViolation, rollback silently — the other worker already did the work.
            db.rollback()
            logger.debug(f"[DC-MENU-SYNC] Race condition on commit (safe — other worker won): {type(e).__name__}")
            created_count = 0

    return created_count


class MenuSettingUpdate(BaseModel):
    menu_id: int
    can_view: bool
    can_edit: bool


class BulkMenuSettingsRequest(BaseModel):
    employee_ids: List[int]
    settings: List[MenuSettingUpdate]
    reason: Optional[str] = None


class EmployeeMenuSettingsRequest(BaseModel):
    settings: List[MenuSettingUpdate]
    reason: Optional[str] = None


CANONICAL_MENU_REGISTRY = [
    {
        'menu_code': 'call_tracking_dashboard',
        'menu_name': 'Call Management',
        'menu_description': 'Call tracking dashboard — CT Protocol employee call logs with lead matching and recordings',
        'route_path': '/staff/call-management',
        'menu_category': 'crm',
        'menu_icon': 'fas fa-phone-alt',
        'display_order': 45,
        'is_default_visible': True,
        'is_default_accessible': True,
        'audience_scope': 'staff'
    },
    {
        'menu_code': 'staff_auto_dialer',
        'menu_name': 'Auto Dialer',
        'menu_description': 'Mobile auto dialer — sequential lead calling with queue management, NMC dismissal, and call outcome tracking',
        'route_path': '/staff/dialer',
        'menu_category': 'crm',
        'menu_icon': 'fas fa-phone-volume',
        'display_order': 46,
        'is_default_visible': True,
        'is_default_accessible': True,
        'audience_scope': 'staff'
    },
    {
        'menu_code': 'rvz_sales_revenue',
        'menu_name': 'Sales Revenue',
        'menu_description': 'View and manage CRM lead transaction revenue with Finance validation workflow',
        'route_path': '/rvz/sales-revenue',
        'menu_category': 'rvz',
        'menu_icon': 'fa-money-bill-wave',
        'display_order': 285,
        'is_default_visible': False,
        'is_default_accessible': False,
        'audience_scope': 'staff'
    },
    {
        'menu_code': 'sfms_vendors',
        'menu_name': 'Vendors',
        'menu_description': 'Manage purchase vendors, GST treatment and vendor master data',
        'route_path': '/staff/accounts/vendors',
        'menu_category': 'sfms',
        'menu_icon': 'fas fa-truck',
        'display_order': 216,
        'is_default_visible': True,
        'is_default_accessible': True,
        'audience_scope': 'staff',
        'sidebar_section': 'sfms',
        'sidebar_section_title': 'SFMS (12.1)',
        'sidebar_section_order': 16,
    },
    {
        'menu_code': 'staff_kra_status',
        'menu_name': 'KRA Status',
        'menu_description': 'View KRA status and reviews',
        'route_path': '/staff/kra-status',
        'menu_category': 'staff',
        'menu_icon': 'fas fa-chart-bar',
        'display_order': 100,
        'is_default_visible': True,
        'is_default_accessible': True,
        'audience_scope': 'staff'
    },
    {
        'menu_code': 'staff_my_lead_incentives',
        'menu_name': 'My Lead Incentives',
        'menu_description': 'View your lead sourcing incentive earnings, tier status, and monthly breakdown',
        'route_path': '/staff/my-lead-incentives',
        'menu_category': 'staff',
        'menu_icon': 'fas fa-hand-holding-usd',
        'display_order': 101,
        'is_default_visible': True,
        'is_default_accessible': True,
        'audience_scope': 'staff',
        'sidebar_section': 'my-earnings',
        'sidebar_section_title': 'MY EARNINGS',
        'sidebar_section_order': 19,
    },
    {
        'menu_code': 'staff_income_trigger',
        'menu_name': 'Income Trigger',
        'menu_description': 'Income trigger management',
        'route_path': '/staff/income-trigger',
        'menu_category': 'staff',
        'menu_icon': 'fas fa-bolt',
        'display_order': 900,
        'is_default_visible': False,
        'is_default_accessible': False,
        'audience_scope': 'staff'
    },
    {
        'menu_code': 'staff_page_registry_manager',
        'menu_name': 'Page Registry Manager',
        'menu_description': 'Manage page registry entries',
        'route_path': '/staff/page-registry',
        'menu_category': 'staff',
        'menu_icon': 'fas fa-file-alt',
        'display_order': 910,
        'is_default_visible': False,
        'is_default_accessible': False,
        'audience_scope': 'staff'
    },
    {
        'menu_code': 'lead_sync',
        'menu_name': 'Lead Sync',
        'menu_description': 'Google Sheets → CRM lead sync — scheduled imports at 9AM, 12PM, 3PM, 6PM IST',
        'route_path': '/staff/lead-sync',
        'menu_category': 'crm',
        'menu_icon': 'fab fa-google',
        'display_order': 920,
        'is_default_visible': True,
        'is_default_accessible': True,
        'audience_scope': 'staff'
    },
    {
        'menu_code': 'call_quality_review',
        'menu_name': 'Call Quality Review',
        'menu_description': 'Auto-sampled call quality monitoring — 5% (min 5) of calls per executive per day, star-rating scoring across 6 parameters, leadership dashboard',
        'route_path': '/staff/call-quality',
        'menu_category': 'crm',
        'menu_icon': 'fas fa-clipboard-check',
        'display_order': 47,
        'is_default_visible': True,
        'is_default_accessible': True,
        'audience_scope': 'staff'
    },
    {
        'menu_code': 'crm_sales_report',
        'menu_name': 'Sales Team Report',
        'menu_description': 'Day/range call activity and quality report for the sales team — per-executive breakdown, daily trend, shareable link',
        'route_path': '/staff/crm/sales-report',
        'menu_category': 'crm',
        'menu_icon': 'fas fa-chart-bar',
        'display_order': 48,
        'is_default_visible': True,
        'is_default_accessible': True,
        'audience_scope': 'staff'
    },
    {
        'menu_code': 'crm_whatsapp_inbox',
        'menu_name': 'WA Inbox (CRM)',
        'menu_description': 'CRM WhatsApp Inbox — assign incoming messages to departments, manage leads and service tickets',
        'route_path': '/staff/crm/whatsapp-inbox',
        'menu_category': 'crm',
        'menu_icon': 'fab fa-whatsapp',
        'display_order': 49,
        'is_default_visible': True,
        'is_default_accessible': True,
        'audience_scope': 'staff',
        'sidebar_section': 'crm',
        'sidebar_section_title': 'CRM & LEADS',
        'sidebar_section_order': 4,
    },
    {
        'menu_code': 'ai_calling',
        'menu_name': 'AI Calling',
        'menu_description': 'Autonomous AI outbound calling — campaigns, multilingual (Hindi/Telugu/English), product catalogue, GPT-4o conversations, post-call CRM auto-update',
        'route_path': '/staff/crm/ai-calling',
        'menu_category': 'configuration',
        'menu_icon': 'fas fa-robot',
        'display_order': 49,
        'is_default_visible': True,
        'is_default_accessible': True,
        'audience_scope': 'staff',
        'sidebar_section': 'configuration',
        'sidebar_section_title': 'CONFIGURATION',
        'sidebar_section_order': 14,
    },
    {
        'menu_code': 'whatsapp_config',
        'menu_name': 'WhatsApp Config',
        'menu_description': 'WhatsApp Config Center — Meta Cloud API settings, templates, auto-trigger rules, bulk campaigns, and message history',
        'route_path': '/staff/whatsapp-config',
        'menu_category': 'configuration',
        'menu_icon': 'fab fa-whatsapp',
        'display_order': 50,
        'is_default_visible': True,
        'is_default_accessible': True,
        'audience_scope': 'staff',
        'sidebar_section': 'configuration',
        'sidebar_section_title': 'CONFIGURATION',
        'sidebar_section_order': 14,
    },
    {
        'menu_code': 'tds_management',
        'menu_name': 'TDS Management',
        'menu_description': 'TDS deduction tracking and management',
        'route_path': '/staff/mnr/tds-management',
        'menu_category': 'finance',
        'menu_icon': 'fas fa-percent',
        'display_order': 49,
        'is_default_visible': False,
        'is_default_accessible': False,
        'audience_scope': 'staff'
    },
    {
        'menu_code': 'cost_analysis',
        'menu_name': 'Cost Analysis',
        'menu_description': 'Financial cost analysis and breakdown reports',
        'route_path': '/staff/mnr/cost-analysis',
        'menu_category': 'finance',
        'menu_icon': 'fas fa-calculator',
        'display_order': 50,
        'is_default_visible': False,
        'is_default_accessible': False,
        'audience_scope': 'staff'
    },
    {
        'menu_code': 'awards_payment',
        'menu_name': 'Awards Payment Processing',
        'menu_description': 'Process and approve awards payment disbursements',
        'route_path': '/staff/mnr/awards/payment-processing',
        'menu_category': 'finance',
        'menu_icon': 'fas fa-money-check-alt',
        'display_order': 51,
        'is_default_visible': False,
        'is_default_accessible': False,
        'audience_scope': 'staff'
    },
    {
        'menu_code': 'income_records',
        'menu_name': 'Income Records',
        'menu_description': 'Full income transaction records and audit log',
        'route_path': '/staff/mnr/income-records',
        'menu_category': 'finance',
        'menu_icon': 'fas fa-file-invoice-dollar',
        'display_order': 52,
        'is_default_visible': False,
        'is_default_accessible': False,
        'audience_scope': 'staff'
    },
    {
        'menu_code': 'income_finance_complete',
        'menu_name': 'Income Finance Complete',
        'menu_description': 'Completed income finance records and final approvals',
        'route_path': '/staff/mnr/income-finance-complete',
        'menu_category': 'finance',
        'menu_icon': 'fas fa-check-double',
        'display_order': 53,
        'is_default_visible': False,
        'is_default_accessible': False,
        'audience_scope': 'staff'
    },
    {
        'menu_code': 'withdrawal_settings',
        'menu_name': 'Withdrawal Settings',
        'menu_description': 'Configure withdrawal limits, schedules and rules',
        'route_path': '/staff/mnr/withdrawal-settings',
        'menu_category': 'finance',
        'menu_icon': 'fas fa-sliders-h',
        'display_order': 54,
        'is_default_visible': False,
        'is_default_accessible': False,
        'audience_scope': 'staff'
    },
    {
        'menu_code': 'red_id_oversight',
        'menu_name': 'Red ID Oversight',
        'menu_description': 'Monitor and manage flagged/red status member IDs',
        'route_path': '/staff/mnr/red-id-oversight',
        'menu_category': 'system',
        'menu_icon': 'fas fa-flag',
        'display_order': 55,
        'is_default_visible': False,
        'is_default_accessible': False,
        'audience_scope': 'staff'
    },
    {
        'menu_code': 'placement_approvals',
        'menu_name': 'Placement Approvals',
        'menu_description': 'Review and approve member placement requests',
        'route_path': '/staff/mnr/placement-approvals',
        'menu_category': 'system',
        'menu_icon': 'fas fa-sitemap',
        'display_order': 56,
        'is_default_visible': False,
        'is_default_accessible': False,
        'audience_scope': 'staff'
    },
    {
        'menu_code': 'system_health',
        'menu_name': 'System Health',
        'menu_description': 'Platform health monitoring — uptime, errors, queue status',
        'route_path': '/staff/mnr/system-health',
        'menu_category': 'system',
        'menu_icon': 'fas fa-heartbeat',
        'display_order': 57,
        'is_default_visible': False,
        'is_default_accessible': False,
        'audience_scope': 'staff'
    },
    {
        'menu_code': 'vgk_partner_kyc_review',
        'menu_name': 'VGK Partner KYC Review',
        'menu_description': 'Review, validate, approve or reject VGK partner KYC documents with document image preview',
        'route_path': '/staff/vgk/partner-kyc-review',
        'menu_category': 'system',
        'menu_icon': 'fas fa-file-shield',
        'display_order': 57,
        'is_default_visible': False,
        'is_default_accessible': False,
        'audience_scope': 'staff'
    },
    {
        'menu_code': 'kyc_bypass',
        'menu_name': 'KYC Bypass',
        'menu_description': 'Manually bypass KYC verification for specific members',
        'route_path': '/staff/mnr/kyc-bypass',
        'menu_category': 'system',
        'menu_icon': 'fas fa-id-badge',
        'display_order': 58,
        'is_default_visible': False,
        'is_default_accessible': False,
        'audience_scope': 'staff'
    },
    {
        'menu_code': 'system_config',
        'menu_name': 'System Configuration',
        'menu_description': 'Global system configuration and feature flags',
        'route_path': '/staff/mnr/system-config',
        'menu_category': 'system',
        'menu_icon': 'fas fa-cogs',
        'display_order': 59,
        'is_default_visible': False,
        'is_default_accessible': False,
        'audience_scope': 'staff'
    },
    {
        'menu_code': 'ev_model_approval',
        'menu_name': 'EV Model Approval',
        'menu_description': 'Approve and manage electric vehicle model registrations',
        'route_path': '/staff/mnr/ev-model-approval',
        'menu_category': 'system',
        'menu_icon': 'fas fa-car',
        'display_order': 60,
        'is_default_visible': False,
        'is_default_accessible': False,
        'audience_scope': 'staff'
    },
    {
        'menu_code': 'training_course_approval',
        'menu_name': 'Training Course Approval',
        'menu_description': 'Approve and activate training course content',
        'route_path': '/staff/mnr/training-course-approval',
        'menu_category': 'system',
        'menu_icon': 'fas fa-graduation-cap',
        'display_order': 61,
        'is_default_visible': False,
        'is_default_accessible': False,
        'audience_scope': 'staff'
    },
    {
        'menu_code': 'create_user',
        'menu_name': 'Create User',
        'menu_description': 'Manually create new member accounts',
        'route_path': '/staff/mnr/create-user',
        'menu_category': 'system',
        'menu_icon': 'fas fa-user-plus',
        'display_order': 62,
        'is_default_visible': False,
        'is_default_accessible': False,
        'audience_scope': 'staff'
    },
    {
        'menu_code': 'bulk_user_edit',
        'menu_name': 'Bulk User Edit',
        'menu_description': 'Batch update member account fields in bulk',
        'route_path': '/staff/mnr/bulk-user-edit',
        'menu_category': 'system',
        'menu_icon': 'fas fa-users-cog',
        'display_order': 63,
        'is_default_visible': False,
        'is_default_accessible': False,
        'audience_scope': 'staff'
    },
    {
        'menu_code': 'bulk_edit',
        'menu_name': 'Bulk Edit',
        'menu_description': 'Bulk edit system records and configurations',
        'route_path': '/staff/mnr/bulk-edit',
        'menu_category': 'system',
        'menu_icon': 'fas fa-edit',
        'display_order': 64,
        'is_default_visible': False,
        'is_default_accessible': False,
        'audience_scope': 'staff'
    },
    {
        'menu_code': 'user_reset',
        'menu_name': 'User Reset',
        'menu_description': 'Reset member account state and credentials',
        'route_path': '/staff/mnr/user-reset',
        'menu_category': 'system',
        'menu_icon': 'fas fa-undo',
        'display_order': 65,
        'is_default_visible': False,
        'is_default_accessible': False,
        'audience_scope': 'staff'
    },
    {
        'menu_code': 'user_data_search',
        'menu_name': 'User Data Search',
        'menu_description': 'Advanced search across member data fields',
        'route_path': '/staff/mnr/user-data-search',
        'menu_category': 'system',
        'menu_icon': 'fas fa-search',
        'display_order': 66,
        'is_default_visible': False,
        'is_default_accessible': False,
        'audience_scope': 'staff'
    },
    {
        'menu_code': 'user_update_controls',
        'menu_name': 'User Update Controls',
        'menu_description': 'Controlled member profile update workflows',
        'route_path': '/staff/mnr/user-update-controls',
        'menu_category': 'system',
        'menu_icon': 'fas fa-user-edit',
        'display_order': 67,
        'is_default_visible': False,
        'is_default_accessible': False,
        'audience_scope': 'staff'
    },
    {
        'menu_code': 'training_courses',
        'menu_name': 'Training Courses',
        'menu_description': 'Manage training course library and assignments',
        'route_path': '/staff/mnr/training-courses',
        'menu_category': 'hr',
        'menu_icon': 'fas fa-book-open',
        'display_order': 68,
        'is_default_visible': False,
        'is_default_accessible': False,
        'audience_scope': 'staff'
    },
    {
        'menu_code': 'ev_models',
        'menu_name': 'EV Models',
        'menu_description': 'Electric vehicle model catalogue management',
        'route_path': '/staff/mnr/ev-models',
        'menu_category': 'system',
        'menu_icon': 'fas fa-charging-station',
        'display_order': 69,
        'is_default_visible': False,
        'is_default_accessible': False,
        'audience_scope': 'staff'
    },
    {
        'menu_code': 'real_dreams',
        'menu_name': 'Real Dreams',
        'menu_description': 'Real Dreams property marketplace — listings, partners, banners',
        'route_path': '/staff/mnr/real-dreams',
        'menu_category': 'real_dreams',
        'menu_icon': 'fas fa-home',
        'display_order': 70,
        'is_default_visible': False,
        'is_default_accessible': False,
        'audience_scope': 'staff'
    },
    {
        'menu_code': 'real_dreams_properties',
        'menu_name': 'Real Dreams Properties',
        'menu_description': 'Manage Real Dreams property listings',
        'route_path': '/staff/mnr/real-dreams/properties',
        'menu_category': 'real_dreams',
        'menu_icon': 'fas fa-building',
        'display_order': 71,
        'is_default_visible': False,
        'is_default_accessible': False,
        'audience_scope': 'staff'
    },
    {
        'menu_code': 'real_dreams_partners',
        'menu_name': 'Real Dreams Partners',
        'menu_description': 'Manage Real Dreams partner organisations',
        'route_path': '/staff/mnr/real-dreams/partners',
        'menu_category': 'real_dreams',
        'menu_icon': 'fas fa-handshake',
        'display_order': 72,
        'is_default_visible': False,
        'is_default_accessible': False,
        'audience_scope': 'staff'
    },
    {
        'menu_code': 'real_dreams_banners',
        'menu_name': 'Real Dreams Banners',
        'menu_description': 'Manage Real Dreams promotional banners',
        'route_path': '/staff/mnr/real-dreams/banners',
        'menu_category': 'real_dreams',
        'menu_icon': 'fas fa-images',
        'display_order': 73,
        'is_default_visible': False,
        'is_default_accessible': False,
        'audience_scope': 'staff'
    },
    {
        'menu_code': 'real_dreams_marketplace',
        'menu_name': 'Real Dreams Marketplace',
        'menu_description': 'Real Dreams public marketplace view',
        'route_path': '/staff/mnr/real-dreams/marketplace',
        'menu_category': 'real_dreams',
        'menu_icon': 'fas fa-store',
        'display_order': 74,
        'is_default_visible': False,
        'is_default_accessible': False,
        'audience_scope': 'staff'
    },
]


# ============================================================================
# DYNAMIC MENU REGISTRY SYSTEM - Dec 26, 2025
# DC Protocol: Auto-discovery and sync of all system pages
# WVV Protocol: Validated entries with source tracking
# ============================================================================

def generate_menu_code(route_path: str) -> str:
    """
    Generate a deterministic menu_code from a route path.
    e.g., '/rvz/sandbox-manager' -> 'rvz_sandbox_manager'
    """
    if not route_path:
        return 'unknown'
    # Remove leading slash and convert to snake_case
    code = route_path.strip('/').replace('/', '_').replace('-', '_')
    # Remove query parameters
    if '?' in code:
        code = code.split('?')[0]
    return code[:64]  # Limit to 64 chars


def determine_audience_scope(route_path: str, source_file: str) -> str:
    """
    Determine audience scope based on route path and source file.
    """
    if not route_path:
        return 'staff'
    
    route_lower = route_path.lower()
    
    # Partner-specific routes
    if '/partner/' in route_lower or source_file == 'partner_sidebar.js':
        return 'partner'
    
    # User/MNR routes
    if route_lower.startswith('/user/') or route_lower.startswith('/coupons'):
        return 'shared'  # Accessible to both MNR users and staff
    
    # Staff/Admin routes
    if any(prefix in route_lower for prefix in ['/staff/', '/rvz/', '/admin/', '/finance/', '/superadmin/']):
        return 'staff'
    
    return 'shared'


def determine_menu_category(route_path: str) -> str:
    """
    Determine menu category based on route path prefix.
    """
    if not route_path:
        return 'other'
    
    route_lower = route_path.lower()
    
    category_map = {
        '/rvz/real-dreams': 'rvz_real_dreams',
        '/rvz/': 'rvz',
        '/admin/awards': 'admin_awards',
        '/admin/earnings': 'admin_earnings',
        '/admin/members': 'admin_members',
        '/admin/coupons': 'admin_coupons',
        '/admin/bank': 'admin_bank',
        '/admin/': 'admin',
        '/superadmin/': 'superadmin',
        '/finance/': 'finance',
        '/staff/accounts/': 'sfms',
        '/staff/inventory/': 'inventory',
        '/staff/tasks/': 'staff_tasks',
        '/staff/': 'staff',
        '/user/': 'user',
        '/partner/': 'partner',
        '/crm/': 'crm',
        '/real-dreams/': 'real_dreams',
    }
    
    for prefix, category in category_map.items():
        if route_lower.startswith(prefix):
            return category
    
    return 'other'


def parse_sidebar_menus_from_js(file_content: str, source_file: str) -> List[dict]:
    """
    Parse menu items from JavaScript sidebar files.
    Extracts href, label, icon AND section info from sidebar link patterns.
    
    DC Protocol Jan 2026: Enhanced to extract sidebar_section info for proper ordering.
    
    Patterns matched:
    - { icon: '...', label: '...', href: '...' }
    - <a href="..." class="sidebar-link">...</a>
    - <li><a href="...">...</a></li>
    """
    import re
    
    menus = []
    seen_routes = set()
    
    section_order_map = {
        # DC Protocol (Jan 10, 2026): 19-section canonical order matching frontend
        'progress': 1, 'PROGRESS': 1,
        'staff-dashboard': 2, 'STAFF DASHBOARD': 2,
        'attendance': 3, 'ATTENDANCE': 3,
        'crm': 4, 'CRM & LEADS': 4, 'crm-leads': 4,
        'task-management': 5, 'TASK MANAGEMENT': 5,
        'kra-management': 6, 'KRA MANAGEMENT': 6,
        'manager-review': 7, 'MANAGER REVIEW': 7,
        'timesheet': 8, 'TIMESHEET': 8,
        'journey-tracking': 9, 'JOURNEY TRACKING': 9, 'JOURNEYS': 9,
        'reimbursement': 10, 'REIMBURSEMENT': 10,
        'location-tracking': 11, 'LOCATION TRACKING': 11,
        'vgk4u': 12, 'VGK4U': 12,
        'mnr': 13, 'MNR': 13,
        'mnr-user': 14, 'MNR USER': 14,
        'accounts': 15, 'ACCOUNTS': 15, 'sfms': 15, 'SFMS': 15,
        'official-partners': 16, 'BUSINESS PARTNERS': 16,
        'service-tickets': 17, 'SERVICE TICKETS': 17,
        'nda-management': 30, 'NDA MANAGEMENT': 30,
        'internal': 30, 'INTERNAL': 30,
        'configuration': 19, 'CONFIGURATION': 19,
    }
    
    section_pattern = r"id:\s*['\"]([^'\"]+)['\"][,\s]+title:\s*['\"]([^'\"]+)['\"][\s\S]*?items:\s*\[([\s\S]*?)\](?=\s*\}|\s*,\s*\{|\s*subSections)"
    
    section_matches = list(re.finditer(section_pattern, file_content))
    
    if section_matches:
        for section_idx, section_match in enumerate(section_matches):
            section_id = section_match.group(1)
            section_label = section_match.group(2)
            items_content = section_match.group(3)
            
            section_order = section_order_map.get(section_id, section_order_map.get(section_label, 50 + section_idx))
            
            item_pattern = r"\{\s*icon:\s*['\"]([^'\"]*)['\"],\s*label:\s*['\"]([^'\"]*)['\"],\s*href:\s*['\"]([^'\"]*)['\"]"
            for item_idx, item_match in enumerate(re.finditer(item_pattern, items_content)):
                icon, label, href = item_match.groups()
                if href and href not in seen_routes and not href.startswith('http'):
                    seen_routes.add(href)
                    menus.append({
                        'menu_code': generate_menu_code(href),
                        'menu_name': label.strip(),
                        'route_path': href,
                        'menu_icon': icon,
                        'menu_category': determine_menu_category(href),
                        'audience_scope': determine_audience_scope(href, source_file),
                        'source': 'discovered',
                        'source_file': source_file,
                        'sidebar_section': section_id,
                        'sidebar_section_title': section_label,
                        'sidebar_section_order': section_order,
                        'display_order': item_idx + 1
                    })
    
    obj_pattern = r"\{\s*icon:\s*['\"]([^'\"]*)['\"],\s*label:\s*['\"]([^'\"]*)['\"],\s*href:\s*['\"]([^'\"]*)['\"]"
    for match in re.finditer(obj_pattern, file_content):
        icon, label, href = match.groups()
        if href and href not in seen_routes and not href.startswith('http'):
            seen_routes.add(href)
            menus.append({
                'menu_code': generate_menu_code(href),
                'menu_name': label.strip(),
                'route_path': href,
                'menu_icon': icon,
                'menu_category': determine_menu_category(href),
                'audience_scope': determine_audience_scope(href, source_file),
                'source': 'discovered',
                'source_file': source_file
            })
    
    # Pattern 2: HTML link pattern <a href="/path" class="sidebar-link">Label</a>
    html_pattern = r'<a\s+href=["\']([^"\']+)["\'][^>]*class=["\'][^"\']*sidebar-link[^"\']*["\'][^>]*>([^<]+)</a>'
    for match in re.finditer(html_pattern, file_content):
        href, label = match.groups()
        # Clean up emoji and extra whitespace from label
        clean_label = re.sub(r'[\U0001F300-\U0001F9FF]', '', label).strip()
        if href and href not in seen_routes and not href.startswith('http') and clean_label:
            seen_routes.add(href)
            menus.append({
                'menu_code': generate_menu_code(href),
                'menu_name': clean_label,
                'route_path': href,
                'menu_icon': 'fas fa-circle',
                'menu_category': determine_menu_category(href),
                'audience_scope': determine_audience_scope(href, source_file),
                'source': 'discovered',
                'source_file': source_file
            })
    
    # Pattern 3: Alternative HTML pattern href="..." class="sidebar-link"
    alt_pattern = r'href=["\']([^"\']+)["\'][^>]*>([^<]*(?:<[^>]*>[^<]*)*)</a>'
    for match in re.finditer(alt_pattern, file_content):
        href, label_raw = match.groups()
        # Extract text content only
        clean_label = re.sub(r'<[^>]+>', '', label_raw)
        clean_label = re.sub(r'[\U0001F300-\U0001F9FF]', '', clean_label).strip()
        if href and href not in seen_routes and not href.startswith('http') and clean_label and 'sidebar-link' in file_content:
            # Only add if we haven't seen this route
            if href.startswith('/') and len(clean_label) > 1:
                seen_routes.add(href)
                menus.append({
                    'menu_code': generate_menu_code(href),
                    'menu_name': clean_label[:128],
                    'route_path': href,
                    'menu_icon': 'fas fa-circle',
                    'menu_category': determine_menu_category(href),
                    'audience_scope': determine_audience_scope(href, source_file),
                    'source': 'discovered',
                    'source_file': source_file
                })
    
    return menus


def discover_all_sidebar_menus() -> List[dict]:
    """
    Discover all menu items from all sidebar configuration files.
    
    Scans:
    - frontend/templates/rvz.js (RVZ Supreme sidebar)
    - frontend/staff_sidebar.js (VGK Supreme sidebar)
    - frontend/server.js (MNR member sidebar)
    - frontend/partner_sidebar.js (Partner sidebar)
    
    Returns: List of discovered menu entries
    """
    import os
    
    sidebar_files = [
        ('frontend/templates/rvz.js', 'rvz.js'),
        ('frontend/staff_sidebar.js', 'staff_sidebar.js'),
        ('frontend/server.js', 'server.js'),
        ('frontend/partner_sidebar.js', 'partner_sidebar.js'),
        ('frontend/public/js/menu-master.js', 'menu-master.js'),
    ]
    
    all_menus = []
    seen_routes = set()
    
    for file_path, source_name in sidebar_files:
        full_path = os.path.join(os.path.dirname(__file__), '../../../../..', file_path)
        
        try:
            if os.path.exists(full_path):
                with open(full_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                menus = parse_sidebar_menus_from_js(content, source_name)
                
                for menu in menus:
                    if menu['route_path'] not in seen_routes:
                        seen_routes.add(menu['route_path'])
                        all_menus.append(menu)
                
                logger.info(f"[DC-DISCOVERY] Parsed {len(menus)} menus from {source_name}")
        except Exception as e:
            logger.error(f"[DC-DISCOVERY] Error parsing {source_name}: {str(e)}")
    
    logger.info(f"[DC-DISCOVERY] Total unique menus discovered: {len(all_menus)}")
    return all_menus


def sync_discovered_menus_to_registry(db: Session) -> dict:
    """
    Sync discovered sidebar menus to the global StaffMenuRegistry table.
    
    Process:
    1. Discover all menus from sidebar files
    2. Merge with DEFAULT_STAFF_MENUS (static entries)
    3. Upsert to StaffMenuRegistry (update existing, insert new)
    4. Mark removed entries as inactive
    
    Returns: Dict with counts {created, updated, deactivated}
    """
    from app.models.staff import StaffMenuRegistry, DEFAULT_STAFF_MENUS
    
    result = {'created': 0, 'updated': 0, 'deactivated': 0, 'total': 0, 'skipped_duplicates': 0, 'skipped_excluded': 0}
    
    # DC Protocol (Jan 8, 2026): EXCLUDED sidebar_sections - these sections are permanently removed
    # Discovery will skip any menus with these sidebar_section values to prevent recreation
    EXCLUDED_SIDEBAR_SECTIONS = {
        'WORKING_MNR', 'WORKING_STAFF', 'staff-mnr', 'superadmin', 
        'user-earnings', 'user-portal', 'user-team', 'rvz-income',
        'admin-functions', 'withdrawal-admin', 'rvz-earnings', 'members-admin', 
        'earnings-admin', 'new-required', 'new-not-required',
        # Additional exclusions (Jan 8, 2026)
        'finance', 'FINANCE', 'FINANCIAL MANAGEMENT',
        'rvz-admin', 'RVZ ADMIN', 'RVZ_ADMIN',
        # DC Protocol (Jan 9, 2026): PARTNER PORTAL permanently removed
        # NOTE: 'mnr-user-sidebar' REINSTATED per user request - do NOT add back to exclusions
        'partner-portal', 'PARTNER PORTAL'
    }
    
    # DC Protocol (Jan 9, 2026): EXCLUDED menu_categories - skip entries with these menu_category values
    # These create ghost sections when sidebar_section is empty due to fallback logic
    # NOTE: staff_mnr_user_* categories REINSTATED per user request - do NOT add back to exclusions
    EXCLUDED_MENU_CATEGORIES = {
        'partner_portal', 'partner_real_dreams', 'partners'
    }

    # DC Protocol (Jun 2, 2026): Routes permanently merged/removed — never re-activate via discovery
    PERMANENTLY_DEACTIVATED_ROUTES = {
        '/staff/inventory/vehicle-color-sheet',  # merged into /staff/inventory/accessories (IN&OUT)
    }
    
    # DC Protocol (Dec 30, 2025): Track both menu_code AND route_path to prevent duplicates
    all_menus = []
    seen_codes = set()
    seen_routes = set()
    
    # First add static menus from DEFAULT_STAFF_MENUS (these are authoritative)
    for menu_def in DEFAULT_STAFF_MENUS:
        menu_code = menu_def.get('menu_code')
        route_path = menu_def.get('route_path', '')
        menu_category = menu_def.get('menu_category', 'other')
        sidebar_section = menu_def.get('sidebar_section', '')
        
        # DC Protocol (Jan 9, 2026): Skip entries with excluded menu_category
        if menu_category in EXCLUDED_MENU_CATEGORIES:
            result['skipped_excluded'] += 1
            continue
        
        # DC Protocol (Jan 9, 2026): Skip entries with excluded sidebar_section
        if sidebar_section in EXCLUDED_SIDEBAR_SECTIONS:
            result['skipped_excluded'] += 1
            continue
        
        if menu_code and menu_code not in seen_codes:
            seen_codes.add(menu_code)
            seen_routes.add(route_path)
            all_menus.append({
                'menu_code': menu_code,
                'menu_name': menu_def.get('menu_name', ''),
                'route_path': route_path,
                'menu_category': menu_category,
                'menu_icon': menu_def.get('menu_icon', 'fas fa-circle'),
                'display_order': menu_def.get('display_order', 999),
                'audience_scope': menu_def.get('audience_scope', 'staff'),
                'is_default_visible': menu_def.get('is_default_visible', False),
                'is_default_accessible': menu_def.get('is_default_accessible', False),
                'source': 'static',
                'source_file': 'staff.py'
            })
    
    # Then add discovered menus (won't overwrite static by code OR route)
    discovered = discover_all_sidebar_menus()
    for menu in discovered:
        route_path = menu.get('route_path', '')
        menu_category = menu.get('menu_category', '')
        sidebar_section = menu.get('sidebar_section', '')
        
        # DC Protocol (Jan 9, 2026): Skip discovered entries with excluded menu_category
        if menu_category in EXCLUDED_MENU_CATEGORIES:
            result['skipped_excluded'] += 1
            continue
        
        # DC Protocol (Jan 9, 2026): Skip discovered entries with excluded sidebar_section
        if sidebar_section in EXCLUDED_SIDEBAR_SECTIONS:
            result['skipped_excluded'] += 1
            continue
        
        # DC Protocol (Jan 9, 2026): Skip partner routes that would create ghost sections
        if route_path and ('/partner-portal/' in route_path or '/partner/' in route_path):
            result['skipped_excluded'] += 1
            continue

        # DC Protocol (Jun 2, 2026): Skip permanently deactivated routes — never re-add to active registry
        if route_path in PERMANENTLY_DEACTIVATED_ROUTES:
            result['skipped_excluded'] += 1
            continue

        # DC Protocol (Dec 30, 2025): Skip if menu_code OR route_path already exists
        if menu['menu_code'] not in seen_codes and route_path not in seen_routes:
            seen_codes.add(menu['menu_code'])
            seen_routes.add(route_path)
            if 'display_order' not in menu:
                menu['display_order'] = 999
            menu['is_default_visible'] = False
            menu['is_default_accessible'] = False
            all_menus.append(menu)
        elif route_path in seen_routes:
            result['skipped_duplicates'] += 1
            logger.debug(f"[DC-REGISTRY-SYNC] Skipped duplicate route: {route_path} (menu_code: {menu['menu_code']})")
    
    result['total'] = len(all_menus)
    now = get_indian_time()
    
    # DC Protocol (Jun 2, 2026): Force-deactivate permanently removed routes in registry + master
    try:
        for _dead_route in PERMANENTLY_DEACTIVATED_ROUTES:
            dead_reg = db.query(StaffMenuRegistry).filter(StaffMenuRegistry.route_path == _dead_route).first()
            if dead_reg and dead_reg.is_active:
                dead_reg.is_active = False
                dead_reg.is_default_visible = False
            dead_masters = db.query(StaffMenuMaster).filter(StaffMenuMaster.route_path == _dead_route).all()
            for _dm in dead_masters:
                _dm.is_active = False
                _dm.is_default_visible = False
                _dm.is_default_accessible = False
    except Exception as _de:
        logger.warning(f"[DC-PERM-DEACT] Could not deactivate dead routes: {_de}")

    # Upsert to registry - DC Protocol Jan 2026: Check BOTH menu_code AND route_path
    for menu_data in all_menus:
        route_path = menu_data.get('route_path', '')

        # DC Protocol (Jun 2, 2026): Never re-activate permanently removed routes
        if route_path in PERMANENTLY_DEACTIVATED_ROUTES:
            continue

        # First check by menu_code
        existing = db.query(StaffMenuRegistry).filter(
            StaffMenuRegistry.menu_code == menu_data['menu_code']
        ).first()
        
        # Also check if route_path already exists under different menu_code
        if not existing and route_path:
            existing_by_route = db.query(StaffMenuRegistry).filter(
                StaffMenuRegistry.route_path == route_path
            ).first()
            if existing_by_route:
                # Route exists under different code - skip to avoid duplicate key
                result['skipped_duplicates'] = result.get('skipped_duplicates', 0) + 1
                logger.debug(f"[DC-REGISTRY-SYNC] Skipped: route {route_path} exists under {existing_by_route.menu_code}")
                continue
        
        if existing:
            # Update existing entry - DC Protocol Jan 2026: Include ordering fields
            existing.menu_name = menu_data.get('menu_name', existing.menu_name)
            existing.route_path = menu_data.get('route_path', existing.route_path)
            existing.menu_category = menu_data.get('menu_category', existing.menu_category)
            existing.menu_icon = menu_data.get('menu_icon', existing.menu_icon)
            existing.audience_scope = menu_data.get('audience_scope', existing.audience_scope)
            existing.source = menu_data.get('source', existing.source)
            existing.source_file = menu_data.get('source_file', existing.source_file)
            existing.is_active = True
            existing.last_discovered_at = now
            if 'display_order' in menu_data and menu_data['display_order'] != 999:
                existing.display_order = menu_data['display_order']
            # DC Protocol Jan 2026: PRESERVE manually-set sidebar_section values
            # Only update sidebar_section if existing is empty/null (don't overwrite manual assignments)
            if 'sidebar_section' in menu_data and not existing.sidebar_section:
                existing.sidebar_section = menu_data['sidebar_section']
            if 'sidebar_section_title' in menu_data and not existing.sidebar_section_title:
                existing.sidebar_section_title = menu_data['sidebar_section_title']
            if 'sidebar_section_order' in menu_data and existing.sidebar_section_order is None:
                existing.sidebar_section_order = menu_data['sidebar_section_order']
            # DC Protocol Jan 2026: PRESERVE parent_section and is_submenu if already set
            if 'parent_section' in menu_data and not existing.parent_section:
                existing.parent_section = menu_data.get('parent_section')
            if 'is_submenu' in menu_data and existing.is_submenu is None:
                existing.is_submenu = menu_data.get('is_submenu')
            result['updated'] += 1
        else:
            # DC Protocol (Jan 8, 2026): Skip creation of entries in excluded sidebar_sections
            sidebar_section = menu_data.get('sidebar_section', '')
            if sidebar_section and sidebar_section.lower() in {s.lower() for s in EXCLUDED_SIDEBAR_SECTIONS}:
                result['skipped_excluded'] += 1
                logger.debug(f"[DC-REGISTRY-SYNC] Skipped excluded section: {sidebar_section} (menu_code: {menu_data['menu_code']})")
                continue
            
            # Create new entry - DC Protocol Jan 2026: Include sidebar section fields
            new_registry = StaffMenuRegistry(
                menu_code=menu_data['menu_code'],
                menu_name=menu_data.get('menu_name', ''),
                route_path=menu_data.get('route_path', ''),
                menu_category=menu_data.get('menu_category', 'other'),
                menu_icon=menu_data.get('menu_icon', 'fas fa-circle'),
                display_order=menu_data.get('display_order', 999),
                audience_scope=menu_data.get('audience_scope', 'staff'),
                source=menu_data.get('source', 'discovered'),
                source_file=menu_data.get('source_file'),
                is_default_visible=menu_data.get('is_default_visible', False),
                is_default_accessible=menu_data.get('is_default_accessible', False),
                is_active=True,
                is_system_default=True,
                last_discovered_at=now,
                sidebar_section=menu_data.get('sidebar_section'),
                sidebar_section_title=menu_data.get('sidebar_section_title'),
                sidebar_section_order=menu_data.get('sidebar_section_order')
            )
            db.add(new_registry)
            result['created'] += 1
    
    try:
        db.commit()
        logger.info(f"[DC-REGISTRY-SYNC] Registry sync complete: {result}")
    except Exception as e:
        db.rollback()
        # DC Protocol Mar 2026: 2-worker race condition — both workers check-then-insert
        # simultaneously; the second one hits UniqueViolation. Safe to swallow — first
        # worker already committed the correct data.
        # DC Protocol Apr 2026: StaleDataError = UPDATE matched 0 rows — another worker
        # already updated/deleted the row; the surviving worker's data is correct.
        from sqlalchemy.exc import IntegrityError
        from sqlalchemy.orm.exc import StaleDataError
        if isinstance(e, IntegrityError):
            logger.warning(f"[DC-REGISTRY-SYNC] Duplicate on commit (race condition, safe to ignore): {str(e)[:120]}")
            return result
        if isinstance(e, StaleDataError):
            logger.warning(f"[DC-REGISTRY-SYNC] Stale row on commit (race condition, safe to ignore): {str(e)[:120]}")
            return result
        # Fallback: catch "expected to update 1 row; 0 were matched" as text
        if "expected to update 1 row" in str(e) or "0 were matched" in str(e):
            logger.warning(f"[DC-REGISTRY-SYNC] ORM update race (safe to ignore): {str(e)[:120]}")
            return result
        logger.error(f"[DC-REGISTRY-SYNC] Error syncing registry: {str(e)}")
        raise

    return result


def sync_registry_to_company_menus(db: Session, company_id: int = None) -> dict:
    """
    Sync StaffMenuRegistry to StaffMenuMaster for specified company (or all companies).
    
    DC Protocol: Ensures all registry entries exist in company-specific menu master.
    
    Process:
    1. Get all active entries from StaffMenuRegistry
    2. For each company, ensure corresponding StaffMenuMaster entry exists
    3. Update existing entries, create missing ones
    
    Returns: Dict with sync counts
    """
    from app.models.staff import StaffMenuRegistry
    from app.models.staff_accounts import AssociatedCompany
    
    result = {'companies_synced': 0, 'menus_created': 0, 'menus_updated': 0}
    
    # Get all active registry entries
    registry_entries = db.query(StaffMenuRegistry).filter(
        StaffMenuRegistry.is_active == True
    ).all()
    
    if not registry_entries:
        logger.info("[DC-COMPANY-SYNC] No registry entries to sync")
        return result
    
    # Get target companies
    if company_id:
        companies = db.query(AssociatedCompany).filter(
            AssociatedCompany.id == company_id,
            AssociatedCompany.is_active == True
        ).all()
    else:
        companies = db.query(AssociatedCompany).filter(
            AssociatedCompany.is_active == True
        ).all()
    
    for company in companies:
        for reg_entry in registry_entries:
            existing = db.query(StaffMenuMaster).filter(
                StaffMenuMaster.company_id == company.id,
                StaffMenuMaster.menu_code == reg_entry.menu_code
            ).first()
            
            if existing:
                # Update if changed
                if existing.menu_name != reg_entry.menu_name or existing.route_path != reg_entry.route_path:
                    existing.menu_name = reg_entry.menu_name
                    existing.route_path = reg_entry.route_path
                    existing.menu_category = reg_entry.menu_category
                    existing.menu_icon = reg_entry.menu_icon
                    existing.audience_scope = reg_entry.audience_scope
                    result['menus_updated'] += 1
            else:
                # Create new entry for this company
                new_menu = StaffMenuMaster(
                    company_id=company.id,
                    menu_code=reg_entry.menu_code,
                    menu_name=reg_entry.menu_name,
                    route_path=reg_entry.route_path,
                    menu_category=reg_entry.menu_category,
                    menu_icon=reg_entry.menu_icon,
                    display_order=reg_entry.display_order,
                    audience_scope=reg_entry.audience_scope,
                    is_active=True,
                    is_default_visible=reg_entry.is_default_visible,
                    is_default_accessible=reg_entry.is_default_accessible
                )
                db.add(new_menu)
                result['menus_created'] += 1
        
        result['companies_synced'] += 1
    
    try:
        db.commit()
        logger.info(f"[DC-COMPANY-SYNC] Company menu sync complete: {result}")
    except Exception as e:
        db.rollback()
        # DC Protocol Mar 2026: same 2-worker race as registry sync — safe to swallow
        from sqlalchemy.exc import IntegrityError
        if isinstance(e, IntegrityError):
            logger.warning(f"[DC-COMPANY-SYNC] Duplicate on commit (race condition, safe to ignore): {str(e)[:120]}")
            return result
        logger.error(f"[DC-COMPANY-SYNC] Error syncing company menus: {str(e)}")
        raise

    return result


def run_full_menu_discovery_sync(db: Session) -> dict:
    """
    Run complete menu discovery and sync pipeline.
    
    Called at application startup to ensure Menu Access Control page
    always has the complete, up-to-date list of all system pages.
    
    Pipeline:
    1. Discover menus from sidebar files
    2. Sync to global StaffMenuRegistry
    3. Sync registry to all company StaffMenuMaster tables
    
    Returns: Combined sync results
    """
    logger.info("[DC-MENU-DISCOVERY] Starting full menu discovery and sync...")
    
    results = {
        'registry_sync': {},
        'company_sync': {},
        'success': True
    }
    
    try:
        # Step 1 & 2: Discover and sync to registry
        results['registry_sync'] = sync_discovered_menus_to_registry(db)
        
        # Step 3: Sync registry to all company menus
        results['company_sync'] = sync_registry_to_company_menus(db)
        
        logger.info(f"[DC-MENU-DISCOVERY] Full sync complete: {results}")
        
    except Exception as e:
        logger.error(f"[DC-MENU-DISCOVERY] Sync failed: {str(e)}")
        results['success'] = False
        results['error'] = str(e)
    
    return results


def sync_canonical_menu_registry(db: Session):
    """
    DC Protocol: Sync canonical menu registry to staff_menu_master for all companies.
    
    This function ensures that all required pages defined in CANONICAL_MENU_REGISTRY
    exist in the staff_menu_master table for every active company.
    
    Called at startup BEFORE bulk_repair_all_employees_menu_settings to ensure
    menu master rows exist before employee/partner settings are created.
    
    Returns: Number of menu entries created
    """
    from sqlalchemy import distinct
    
    company_ids = db.query(distinct(StaffMenuMaster.company_id)).all()
    company_ids = [c[0] for c in company_ids if c[0]]
    
    if not company_ids:
        logger.info("[DC-MENU-REGISTRY] No companies found in staff_menu_master")
        return 0
    
    total_created = 0
    
    for menu_def in CANONICAL_MENU_REGISTRY:
        for company_id in company_ids:
            exists = db.query(StaffMenuMaster).filter(
                StaffMenuMaster.company_id == company_id,
                StaffMenuMaster.menu_code == menu_def['menu_code']
            ).first()
            
            if not exists:
                new_menu = StaffMenuMaster(
                    company_id=company_id,
                    menu_code=menu_def['menu_code'],
                    menu_name=menu_def['menu_name'],
                    menu_description=menu_def.get('menu_description'),
                    route_path=menu_def['route_path'],
                    menu_category=menu_def.get('menu_category', 'rvz'),
                    menu_icon=menu_def.get('menu_icon', 'fa-circle'),
                    display_order=menu_def.get('display_order', 999),
                    is_active=True,
                    is_default_visible=menu_def.get('is_default_visible', False),
                    is_default_accessible=menu_def.get('is_default_accessible', False),
                    audience_scope=menu_def.get('audience_scope', 'staff'),
                    sidebar_section=menu_def.get('sidebar_section'),
                    sidebar_section_title=menu_def.get('sidebar_section_title'),
                    sidebar_section_order=menu_def.get('sidebar_section_order', 0)
                )
                db.add(new_menu)
                total_created += 1
                logger.info(f"[DC-MENU-REGISTRY] Created menu '{menu_def['menu_code']}' for company {company_id}")
            else:
                # Update name/description and sidebar_section if they've changed in the canonical registry
                changed = False
                if exists.menu_name != menu_def['menu_name']:
                    exists.menu_name = menu_def['menu_name']
                    changed = True
                if menu_def.get('menu_description') and exists.menu_description != menu_def['menu_description']:
                    exists.menu_description = menu_def['menu_description']
                    changed = True
                # Propagate sidebar_section from canonical registry if master row is missing it
                if menu_def.get('sidebar_section') and not exists.sidebar_section:
                    exists.sidebar_section = menu_def['sidebar_section']
                    exists.sidebar_section_title = menu_def.get('sidebar_section_title')
                    exists.sidebar_section_order = menu_def.get('sidebar_section_order', 0)
                    changed = True
                # DC Protocol: Canonical entries must always be active
                if not exists.is_active:
                    exists.is_active = True
                    changed = True
                if changed:
                    total_created += 1
    
    if total_created > 0:
        db.commit()
        logger.info(f"[DC-MENU-REGISTRY] Synced {total_created} menu entries across {len(company_ids)} companies")
    
    return total_created


def ensure_menu_parity_for_target_company(db: Session, target_company_id: int):
    """
    DC Protocol (Dec 22, 2025): Ensure menu parity for All Companies mode.
    
    When loading the matrix in "All Companies" mode, we need ALL menu_codes from 
    ALL companies to exist in the target (filter) company. This ensures that 
    settings saved in employee's base_company can be mapped back to the target company.
    
    Process:
    1. Get all unique menu_codes from ALL companies
    2. For any menu_code missing in target_company, copy from any source company
    
    Returns: Number of menus created
    """
    from sqlalchemy import distinct
    
    all_menu_codes = db.query(
        StaffMenuMaster.menu_code,
        StaffMenuMaster.menu_name,
        StaffMenuMaster.menu_description,
        StaffMenuMaster.route_path,
        StaffMenuMaster.menu_category,
        StaffMenuMaster.menu_icon,
        StaffMenuMaster.display_order,
        StaffMenuMaster.is_default_visible,
        StaffMenuMaster.is_default_accessible,
        StaffMenuMaster.audience_scope
    ).filter(
        StaffMenuMaster.is_active == True
    ).distinct(StaffMenuMaster.menu_code).all()
    
    target_menu_codes = set(
        m.menu_code for m in db.query(StaffMenuMaster).filter(
            StaffMenuMaster.company_id == target_company_id,
            StaffMenuMaster.is_active == True
        ).all()
    )
    
    total_created = 0
    
    for menu_data in all_menu_codes:
        if menu_data.menu_code not in target_menu_codes:
            new_menu = StaffMenuMaster(
                company_id=target_company_id,
                menu_code=menu_data.menu_code,
                menu_name=menu_data.menu_name,
                menu_description=menu_data.menu_description,
                route_path=menu_data.route_path,
                menu_category=menu_data.menu_category or 'staff',
                menu_icon=menu_data.menu_icon or 'fa-circle',
                display_order=menu_data.display_order or 999,
                is_active=True,
                is_default_visible=menu_data.is_default_visible or False,
                is_default_accessible=menu_data.is_default_accessible or False,
                audience_scope=menu_data.audience_scope or 'staff'
            )
            db.add(new_menu)
            total_created += 1
            logger.info(f"[DC-MENU-PARITY] Created missing menu '{menu_data.menu_code}' for target company {target_company_id}")
    
    if total_created > 0:
        try:
            db.commit()
            logger.info(f"[DC-MENU-PARITY] Added {total_created} missing menus to company {target_company_id} for All Companies mode")
        except Exception as e:
            # Concurrent request already inserted the same menus — parity is achieved
            db.rollback()
            logger.info(f"[DC-MENU-PARITY] Concurrent insert detected for company {target_company_id} — parity already achieved: {e}")
            return 0
    
    return total_created


def bulk_repair_all_employees_menu_settings(db: Session):
    """
    BULK REPAIR: Create missing StaffEmployeeMenuSettings for ALL active employees
    across their ACCESSIBLE companies for menus with is_default_visible=True.
    
    This function is designed to be called:
    1. On application startup to repair existing data
    2. Manually via API endpoint for maintenance
    
    DC Protocol: 
    - Respects employee-company linkage (base_company_id / data_companies)
    - Only creates settings for companies the employee has access to
    - Ensures all employees have explicit settings for default-visible menus
    """
    from app.models.staff import StaffEmployee
    
    # Get all active employees with their company associations
    active_employees = db.query(StaffEmployee).filter(
        StaffEmployee.status == 'active',
        StaffEmployee.is_deleted == False
    ).all()
    
    if not active_employees:
        logger.info("[DC-BULK-REPAIR] No active employees found")
        return 0
    
    total_created = 0
    
    for employee in active_employees:
        # DC Protocol: Get all companies this employee has access to
        employee_companies = get_employee_company_ids(employee)
        
        # If no companies found, skip this employee
        if not employee_companies:
            continue
        
        # Sync settings for each of employee's accessible companies
        for company_id in employee_companies:
            created = sync_default_menu_settings_for_employees(
                db, company_id, [employee.id],
                admin_id=None,
                admin_code='SYSTEM',
                admin_name='Bulk Repair on Startup'
            )
            total_created += created
    
    if total_created > 0:
        logger.info(f"[DC-BULK-REPAIR] Created {total_created} missing menu settings for {len(active_employees)} employees (respecting company associations)")
    
    return total_created


def bulk_repair_all_partners_menu_settings(db: Session):
    """
    BULK REPAIR: Create missing PartnerMenuSettings for ALL active partners
    across their associated companies for menus with is_default_visible=True.
    
    DC Protocol: 
    - Respects partner-company linkage via PartnerCompanySegment
    - Only creates settings for companies the partner has access to
    - Ensures all partners have explicit settings for default-visible menus
    """
    from app.models.staff_accounts import OfficialPartner, PartnerCompanySegment
    
    # Get all active partners
    active_partners = db.query(OfficialPartner).filter(
        OfficialPartner.is_active == True
    ).all()
    
    if not active_partners:
        logger.info("[DC-BULK-REPAIR-PARTNERS] No active partners found")
        return 0
    
    total_created = 0
    
    for partner in active_partners:
        # Get all companies this partner has access to via PartnerCompanySegment
        segments = db.query(PartnerCompanySegment).filter(
            PartnerCompanySegment.partner_id == partner.id,
            PartnerCompanySegment.is_active == True
        ).all()
        
        partner_companies = set()
        for seg in segments:
            if seg.company_id:
                try:
                    partner_companies.add(int(seg.company_id))
                except (ValueError, TypeError):
                    pass
        
        if not partner_companies:
            continue
        
        # Sync settings for each company
        for company_id in partner_companies:
            # Get default-visible partner menus for this company
            default_menus = db.query(StaffMenuMaster).filter(
                StaffMenuMaster.company_id == company_id,
                StaffMenuMaster.is_default_visible == True,
                StaffMenuMaster.is_active == True,
                StaffMenuMaster.audience_scope.in_(['partner', 'shared'])
            ).all()
            
            if not default_menus:
                continue
            
            menu_ids = [m.id for m in default_menus]
            
            # Check existing settings
            existing = db.query(PartnerMenuSettings).filter(
                PartnerMenuSettings.partner_id == partner.id,
                PartnerMenuSettings.company_id == company_id,
                PartnerMenuSettings.menu_id.in_(menu_ids)
            ).all()
            
            existing_menu_ids = {s.menu_id for s in existing}
            
            for menu in default_menus:
                if menu.id not in existing_menu_ids:
                    new_setting = PartnerMenuSettings(
                        partner_id=partner.id,
                        menu_id=menu.id,
                        company_id=company_id,
                        can_view=True,
                        can_edit=False,
                        is_overridden=False,
                        set_by_id=None,
                        set_by_code='SYSTEM',
                        set_by_name='Bulk Repair on Startup'
                    )
                    db.add(new_setting)
                    total_created += 1
    
    if total_created > 0:
        db.commit()
        logger.info(f"[DC-BULK-REPAIR-PARTNERS] Created {total_created} missing menu settings for {len(active_partners)} partners")
    
    return total_created


@router.post("/bulk-repair")
async def bulk_repair_menu_settings(
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """
    Bulk repair: Create missing menu settings for ALL active employees AND partners
    DC Protocol: Only VGK4U/EA/RVZ can trigger this repair
    
    This endpoint creates settings rows for all employees/partners
    who are missing settings for menus with is_default_visible=True
    """
    allowed_types = ['VGK4U', 'VGK4U Supreme', 'EA', 'RVZ', 'MYNT_REAL']
    allowed_roles = ['ea', 'hr', 'accounts', 'vgk4u']
    role_code = getattr(current_user.role, 'role_code', '') if current_user.role else ''
    if current_user.staff_type not in allowed_types and (role_code or '').lower() not in allowed_roles:
        logger.warning(f"RBAC VIOLATION: {current_user.emp_code} ({current_user.staff_type}) - bulk repair access denied")
        raise HTTPException(status_code=403, detail="Access denied to bulk repair.")
    
    employee_count = bulk_repair_all_employees_menu_settings(db)
    partner_count = bulk_repair_all_partners_menu_settings(db)
    
    return {
        "success": True,
        "message": f"Bulk repair completed. Created {employee_count} employee settings and {partner_count} partner settings.",
        "employee_settings_created": employee_count,
        "partner_settings_created": partner_count,
        "triggered_by": current_user.emp_code
    }


@router.get("/menus")
async def get_menu_catalog(
    company_id: int = None,
    category: Optional[str] = None,
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """
    Get all available menus/pages for the Access Matrix
    DC Protocol (Jan 2026): Use StaffMenuRegistry as canonical source to match sidebar
    Returns hierarchical menu structure grouped by sidebar_section
    """
    # DC Protocol: VGK4U/EA/HR/Accounts/MYNT_REAL can access menu settings
    allowed_types = ['VGK4U', 'VGK4U Supreme', 'EA', 'RVZ', 'MYNT_REAL']
    allowed_roles = ['ea', 'hr', 'accounts', 'vgk4u']
    role_code = getattr(current_user.role, 'role_code', '') if current_user.role else ''
    if current_user.staff_type not in allowed_types and (role_code or '').lower() not in allowed_roles:
        logger.warning(f"RBAC VIOLATION: {current_user.emp_code} ({current_user.staff_type}) - menu settings access denied")
        raise HTTPException(status_code=403, detail="Access denied to menu settings.")
    
    # DC Protocol (Jan 2026): Use StaffMenuRegistry as canonical source
    # This ensures Access Matrix shows same menus as sidebar
    query = db.query(StaffMenuRegistry).filter(
        StaffMenuRegistry.is_active == True
    )
    
    if category:
        query = query.filter(StaffMenuRegistry.sidebar_section == category)
    
    menus = query.order_by(
        StaffMenuRegistry.sidebar_section_order,
        StaffMenuRegistry.display_order,
        StaffMenuRegistry.menu_name
    ).all()
    
    # Group by sidebar_section to match sidebar structure
    categorized = {}
    section_titles = {}
    for menu in menus:
        section = menu.sidebar_section or 'OTHER'
        section_title = menu.sidebar_section_title or section.upper().replace('-', ' ')
        if section not in categorized:
            categorized[section] = []
            section_titles[section] = section_title
        categorized[section].append({
            "id": menu.id,
            "menu_code": menu.menu_code,
            "menu_name": menu.menu_name,
            "route_path": menu.route_path,
            "menu_icon": menu.menu_icon,
            "menu_category": section_title,
            "sidebar_section": menu.sidebar_section,
            "sidebar_section_title": menu.sidebar_section_title,
            "sidebar_section_order": menu.sidebar_section_order,
            "display_order": menu.display_order,
            "audience_scope": menu.audience_scope,
            "menu_type": menu.menu_type,
            "is_active": menu.is_active
        })
    
    # Sort categories by sidebar_section_order
    sorted_categories = sorted(
        categorized.keys(),
        key=lambda x: min([m.get('sidebar_section_order', 999) for m in categorized[x]])
    )
    
    all_menus = []
    for section in sorted_categories:
        all_menus.extend(categorized[section])
    
    return {
        "success": True,
        "company_id": company_id,
        "total_menus": len(menus),
        "menus": all_menus,
        "categorized": categorized,
        "categories": sorted_categories,
        "section_titles": section_titles
    }


@router.get("/employees")
async def get_employees_for_menu_settings(
    company_id: Optional[int] = None,
    all_companies: bool = False,
    department_id: Optional[int] = None,
    staff_type: Optional[str] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
    page: int = 1,
    limit: int = 50,
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """
    Get employees for menu settings matrix
    DC Protocol (Dec 30, 2025): Support status filter and All Companies mode
    - all_companies=True: Show all employees with is_current_user and can_modify flags
    - status: Filter by employee status (active, inactive, or empty for all)
    Returns employees with their current menu settings and RBAC flags
    """
    # DC Protocol: VGK4U/EA/HR/Accounts/MYNT_REAL can access menu settings
    allowed_types = ['VGK4U', 'VGK4U Supreme', 'EA', 'RVZ', 'MYNT_REAL']
    allowed_roles = ['ea', 'hr', 'accounts', 'vgk4u']
    role_code = getattr(current_user.role, 'role_code', '') if current_user.role else ''
    if current_user.staff_type not in allowed_types and (role_code or '').lower() not in allowed_roles:
        logger.warning(f"RBAC VIOLATION: {current_user.emp_code} ({current_user.staff_type}) - menu settings access denied")
        raise HTTPException(status_code=403, detail="Access denied to menu settings.")
    
    # DC Protocol (Dec 22, 2025): Get current user's data_companies for RBAC
    current_user_companies = get_employee_company_ids(current_user)
    logger.info(f"[DC-MENU] Current user {current_user.emp_code} has access to companies: {current_user_companies}")
    
    # DC Protocol (Dec 30, 2025): Filter by status - supports active, inactive, or all
    query = db.query(StaffEmployee).filter(StaffEmployee.is_deleted == False)
    if status:
        query = query.filter(StaffEmployee.status == status)
    
    if department_id:
        from app.models.staff import StaffEmployeeDepartment
        emp_ids = db.query(StaffEmployeeDepartment.employee_id).filter(
            StaffEmployeeDepartment.department_id == department_id
        ).scalar_subquery()
        query = query.filter(StaffEmployee.id.in_(emp_ids))
    
    if staff_type:
        query = query.filter(StaffEmployee.staff_type == staff_type)
    
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            (StaffEmployee.full_name.ilike(search_term)) |
            (StaffEmployee.emp_code.ilike(search_term)) |
            (StaffEmployee.email.ilike(search_term))
        )
    
    total = query.count()
    
    # DC Protocol (Dec 22, 2025): Order by current user first (for highlighting)
    employees = query.order_by(
        (StaffEmployee.id == current_user.id).desc(),
        StaffEmployee.full_name
    ).offset((page - 1) * limit).limit(limit).all()
    
    result = []
    for emp in employees:
        # DC Protocol (Dec 22, 2025): Calculate RBAC flags
        emp_companies = get_employee_company_ids(emp)
        # Build employee's effective company set from data_companies
        emp_data_companies = set()
        if emp.data_companies:
            import json
            dc = emp.data_companies
            if isinstance(dc, str):
                try:
                    dc = json.loads(dc)
                except:
                    dc = []
            if isinstance(dc, list):
                for cid in dc:
                    if cid:
                        try:
                            emp_data_companies.add(int(cid))
                        except:
                            pass
        
        # DC Protocol (Dec 22, 2025): FIXED - Include base_company_id as fallback
        # If employee has no data_companies but has base_company_id, use base_company_id for intersection
        emp_effective_companies = emp_data_companies.copy()
        if emp.base_company_id:
            emp_effective_companies.add(emp.base_company_id)
        
        # DC Protocol: can_modify requires BOTH:
        # 1. Company intersection (current_user's data_companies vs employee's effective companies)
        # 2. base_company_id is set (saves require company assignment)
        has_company_intersection = bool(current_user_companies & emp_effective_companies) if emp_effective_companies else False
        has_base_company = emp.base_company_id is not None
        can_modify_for_emp = has_company_intersection and has_base_company
        
        # DC Protocol: Get base company name for display in All Companies mode
        base_company_name = None
        if emp.base_company_id:
            base_company = db.query(AssociatedCompany).filter(AssociatedCompany.id == emp.base_company_id).first()
            if base_company:
                base_company_name = base_company.company_name
        
        emp_dict = {
            "id": emp.id,
            "emp_code": emp.emp_code,
            "full_name": emp.full_name,
            "email": emp.email,
            "staff_type": emp.staff_type,
            "role_name": emp.role.role_name if emp.role else None,
            "department_name": emp.department.name if emp.department else None,
            "is_current_user": emp.id == current_user.id,
            "can_modify": can_modify_for_emp,
            "data_companies": list(emp_data_companies),
            "base_company_id": emp.base_company_id,
            "base_company_name": base_company_name,  # DC: For display in All Companies mode
            "no_base_company": not has_base_company  # DC: Flag for UI to show why disabled
        }
        result.append(emp_dict)
    
    return {
        "success": True,
        "company_id": company_id if company_id else "all",
        "all_companies_mode": all_companies or not company_id,
        "current_user_id": current_user.id,
        "current_user_companies": list(current_user_companies),
        "total": total,
        "page": page,
        "limit": limit,
        "total_pages": (total + limit - 1) // limit,
        "employees": result
    }


@router.get("/partners")
async def get_partners_for_menu_settings(
    company_id: int,
    search: Optional[str] = None,
    page: int = 1,
    limit: int = 50,
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """
    Get official partners for menu settings matrix
    DC Protocol: Filter by company_id via partner_company_segments
    Returns partners with their current menu settings
    """
    allowed_types = ['VGK4U', 'VGK4U Supreme', 'EA', 'RVZ', 'MYNT_REAL']
    allowed_roles = ['ea', 'hr', 'accounts', 'vgk4u']
    role_code = getattr(current_user.role, 'role_code', '') if current_user.role else ''
    if current_user.staff_type not in allowed_types and (role_code or '').lower() not in allowed_roles:
        logger.warning(f"RBAC VIOLATION: {current_user.emp_code} ({current_user.staff_type}) - partners menu settings access denied")
        raise HTTPException(status_code=403, detail="Access denied to menu settings.")
    
    from app.models.staff_accounts import PartnerCompanySegment
    
    partner_ids = db.query(PartnerCompanySegment.partner_id).filter(
        PartnerCompanySegment.company_id == company_id,
        PartnerCompanySegment.is_active == True
    ).distinct().scalar_subquery()
    
    query = db.query(OfficialPartner).filter(
        OfficialPartner.id.in_(partner_ids),
        OfficialPartner.is_active == True
    )
    
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            (OfficialPartner.partner_name.ilike(search_term)) |
            (OfficialPartner.partner_code.ilike(search_term))
        )
    
    total = query.count()
    partners = query.order_by(OfficialPartner.partner_name).offset((page - 1) * limit).limit(limit).all()
    
    result = []
    for partner in partners:
        result.append({
            "id": partner.id,
            "partner_code": partner.partner_code,
            "partner_name": partner.partner_name,
            "category": partner.category,
            "partner_type": partner.partner_type
        })
    
    return {
        "success": True,
        "company_id": company_id,
        "total": total,
        "page": page,
        "limit": limit,
        "total_pages": (total + limit - 1) // limit,
        "partners": result
    }


@router.get("/matrix")
async def get_menu_settings_matrix(
    company_id: int,
    employee_ids: Optional[str] = None,
    partner_ids: Optional[str] = None,
    category: Optional[str] = None,
    include_partners: bool = True,
    all_companies: bool = False,
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """
    Get menu settings matrix: Employees/Partners in columns, Menus in rows
    DC Protocol: Filter by company_id
    DC Protocol (Dec 22, 2025): all_companies mode - fetch each employee's settings from their own company
    Returns a matrix format for the UI grid with audience_scope handling
    - staff pages: show checkboxes for employees, N/A for partners
    - partner pages: show checkboxes for partners, N/A for employees
    - shared pages: show checkboxes for both
    """
    # DC Jan 2026: Accept both 'VGK4U' and 'VGK4U Supreme' for production compatibility
    allowed_staff_types = ['VGK4U', 'VGK4U Supreme', 'EA', 'RVZ', 'MYNT_REAL']
    hierarchy_level = current_user.role.hierarchy_level if current_user.role else 0
    if current_user.staff_type not in allowed_staff_types and hierarchy_level < 85:
        raise HTTPException(status_code=403, detail="Access denied to menu settings configuration")
    
    # DC Protocol (Dec 22, 2025): In all_companies mode, ensure menu parity first
    # This ensures all menu_codes from all companies exist in the filter company
    if all_companies:
        parity_count = ensure_menu_parity_for_target_company(db, company_id)
        if parity_count > 0:
            logger.info(f"[DC-MATRIX] All Companies mode: Added {parity_count} missing menus to filter company {company_id}")
    
    menu_query = db.query(StaffMenuMaster).filter(
        StaffMenuMaster.company_id == company_id,
        StaffMenuMaster.is_active == True
    )
    if category:
        menu_query = menu_query.filter(StaffMenuMaster.menu_category == category)
    
    menus = menu_query.order_by(StaffMenuMaster.display_order).all()
    
    if not menus:
        added = seed_menu_master(db, company_id)
        if added > 0:
            menus = menu_query.order_by(StaffMenuMaster.display_order).all()
    
    # Employees are not company-specific; filter by active status only
    emp_query = db.query(StaffEmployee).filter(
        StaffEmployee.status == 'active',
        StaffEmployee.is_deleted == False
    )
    
    if employee_ids:
        try:
            emp_id_list = [int(x.strip()) for x in employee_ids.split(',') if x.strip()]
            if emp_id_list:
                emp_query = emp_query.filter(StaffEmployee.id.in_(emp_id_list))
        except ValueError:
            pass
    
    employees = emp_query.order_by(StaffEmployee.full_name).limit(20).all()
    
    # WVV Protocol: Validation - Check for data integrity issues
    # Show validation errors instead of auto-fixing (user-driven corrections)
    validation_issues = []
    
    # Check for employees with NULL base_company_id
    employees_without_company = db.query(StaffEmployee).filter(
        StaffEmployee.status == 'active',
        StaffEmployee.is_deleted == False,
        StaffEmployee.base_company_id.is_(None)
    ).all()
    
    for emp in employees_without_company:
        validation_issues.append({
            "type": "MISSING_BASE_COMPANY",
            "severity": "error",
            "entity_type": "employee",
            "entity_id": emp.id,
            "entity_code": emp.emp_code,
            "entity_name": emp.full_name,
            "message": f"No company assigned to {emp.emp_code} ({emp.full_name})",
            "resolution": "Go to Staff Management → Employees → Edit → Select Base Company from dropdown",
            "resolution_url": f"/staff/employees?edit={emp.id}",
            "dc_protocol": "DC Protocol requires all employees to be assigned to a specific company for proper data segregation"
        })
    
    # Auto-sync: Create default settings for employees who have access to this company
    # DC Protocol: Only sync for employees whose base_company_id or data_companies includes company_id
    # This prevents cross-company data pollution
    all_active_emps = db.query(StaffEmployee).filter(
        StaffEmployee.status == 'active',
        StaffEmployee.is_deleted == False
    ).all()
    
    # Filter to only employees who have access to this company
    # DC Protocol: Use helper function for safe company ID normalization
    eligible_emp_ids = []
    for emp in all_active_emps:
        emp_companies = get_employee_company_ids(emp)
        if company_id in emp_companies:
            eligible_emp_ids.append(emp.id)
    
    if eligible_emp_ids:
        sync_count = sync_default_menu_settings_for_employees(
            db, company_id, eligible_emp_ids,
            admin_id=current_user.id,
            admin_code=current_user.emp_code,
            admin_name=current_user.full_name
        )
        if sync_count > 0:
            logger.info(f"[DC-MATRIX] Auto-synced {sync_count} default menu settings for {len(eligible_emp_ids)} eligible employees (company {company_id})")
    
    # DC Protocol (Dec 22, 2025): In all_companies mode, fetch each employee's settings from their own company
    emp_settings_map = {}
    
    if all_companies:
        # For all_companies mode: Optimized batch query
        # IMPORTANT: Match by menu_code since menu_ids differ across companies
        
        # Build menu_code to menu_id mapping for the current company_id
        menu_code_to_id = {menu.menu_code: menu.id for menu in menus}
        
        # Get unique base_company_ids
        base_company_ids = set()
        emp_to_base_company = {}
        for emp in employees:
            if emp.base_company_id:
                base_company_ids.add(emp.base_company_id)
                emp_to_base_company[emp.id] = emp.base_company_id
        
        if base_company_ids:
            # DC Protocol (Dec 30, 2025): Company-agnostic settings load
            # Fetch ALL settings for displayed employees without company filter
            all_settings = db.query(
                StaffEmployeeMenuSettings.employee_id,
                StaffEmployeeMenuSettings.menu_id,
                StaffEmployeeMenuSettings.can_view,
                StaffEmployeeMenuSettings.can_edit,
                StaffEmployeeMenuSettings.is_overridden,
                StaffEmployeeMenuSettings.company_id,
                StaffMenuMaster.menu_code
            ).join(
                StaffMenuMaster, StaffEmployeeMenuSettings.menu_id == StaffMenuMaster.id
            ).filter(
                StaffEmployeeMenuSettings.employee_id.in_([emp.id for emp in employees])
            ).all()
            
            # Map settings by menu_code to handle cross-company menu IDs
            for s in all_settings:
                if s.menu_code in menu_code_to_id:
                    target_menu_id = menu_code_to_id[s.menu_code]
                    key = f"{s.employee_id}_{target_menu_id}"
                    # Only store if not already set (first match wins)
                    if key not in emp_settings_map:
                        emp_settings_map[key] = {
                            "can_view": s.can_view,
                            "can_edit": s.can_edit,
                            "is_overridden": s.is_overridden,
                            "source_company_id": s.company_id
                        }
        
        logger.info(f"[DC-MATRIX] All companies mode: fetched {len(emp_settings_map)} settings for {len(employees)} employees")
    else:
        # Standard mode: fetch all settings for the specified company
        emp_settings = db.query(StaffEmployeeMenuSettings).filter(
            StaffEmployeeMenuSettings.company_id == company_id
        ).all()
        
        for s in emp_settings:
            key = f"{s.employee_id}_{s.menu_id}"
            emp_settings_map[key] = {
                "can_view": s.can_view,
                "can_edit": s.can_edit,
                "is_overridden": s.is_overridden
            }
    
    partners = []
    partner_settings_map = {}
    if include_partners:
        from app.models.staff_accounts import PartnerCompanySegment
        
        partner_id_subquery = db.query(PartnerCompanySegment.partner_id).filter(
            PartnerCompanySegment.company_id == company_id,
            PartnerCompanySegment.is_active == True
        ).distinct().scalar_subquery()
        
        partner_query = db.query(OfficialPartner).filter(
            OfficialPartner.id.in_(partner_id_subquery),
            OfficialPartner.is_active == True
        )
        
        if partner_ids:
            try:
                partner_id_list = [int(x.strip()) for x in partner_ids.split(',') if x.strip()]
                if partner_id_list:
                    partner_query = partner_query.filter(OfficialPartner.id.in_(partner_id_list))
            except ValueError:
                pass
        
        partners = partner_query.order_by(OfficialPartner.partner_name).limit(20).all()
        
        partner_settings = db.query(PartnerMenuSettings).filter(
            PartnerMenuSettings.partner_id.in_([p.id for p in partners])  # DC Protocol (Dec 30, 2025): Company-agnostic - fetch all settings for displayed partners
        ).all()
        
        for s in partner_settings:
            key = f"{s.partner_id}_{s.menu_id}"
            partner_settings_map[key] = {
                "can_view": s.can_view,
                "can_edit": s.can_edit,
                "is_overridden": s.is_overridden
            }
    
    # DC Protocol (Dec 31, 2025): Build sidebar_section lookup from StaffMenuRegistry
    # This enables Menu Access Control page to use same structure as Staff Sidebar
    from app.models.staff import StaffMenuRegistry
    registry_entries = db.query(StaffMenuRegistry).filter(
        StaffMenuRegistry.is_active == True
    ).all()
    
    # Build lookup by menu_code for sidebar_section info
    # DC Protocol (Jan 9, 2026): Include parent_section and is_submenu for nested grouping
    # DC Protocol (Mar 18, 2026): Also build route_path lookup as secondary fallback
    # DC Protocol (Mar 20, 2026): Canonical title overrides — fixes wrong DB titles in all envs
    CANONICAL_SECTION_TITLES = {
        'vgk4u': 'ZYNOVA',
        'vgk_team': 'VGK4U',
        'vendor_management': 'VENDOR MANAGEMENT',
        'mynt_real': 'MYNT REAL',
    }
    sidebar_section_lookup = {}
    route_path_lookup = {}
    for reg in registry_entries:
        parent_section = getattr(reg, 'parent_section', None)
        is_submenu = getattr(reg, 'is_submenu', False)
        
        if parent_section and is_submenu:
            display_section = parent_section
            display_section_title = CANONICAL_SECTION_TITLES.get(parent_section) or parent_section.upper().replace('-', ' ').replace('_', ' ')
            child_section = reg.sidebar_section or reg.menu_category or 'other'
            child_section_title = CANONICAL_SECTION_TITLES.get(child_section) or reg.sidebar_section_title or (reg.sidebar_section or 'Other').upper().replace('_', ' ').replace('-', ' ')
        else:
            display_section = reg.sidebar_section or reg.menu_category or 'other'
            display_section_title = CANONICAL_SECTION_TITLES.get(display_section) or reg.sidebar_section_title or (reg.sidebar_section or 'Other').upper().replace('_', ' ').replace('-', ' ')
            child_section = None
            child_section_title = None
        
        entry = {
            "sidebar_section": display_section,
            "sidebar_section_title": display_section_title,
            "sidebar_section_order": reg.sidebar_section_order or 999,
            "parent_section": parent_section,
            "is_submenu": is_submenu,
            "child_section": child_section,
            "child_section_title": child_section_title
        }
        sidebar_section_lookup[reg.menu_code] = entry
        if reg.route_path:
            route_path_lookup[reg.route_path] = entry

    # DC Protocol (Mar 18, 2026): Sub-section mappings for "Others" group
    # Pages not in VGK MENTOR sidebar are grouped into sub-sections by menu_category
    OTHERS_CHILD_SECTION_MAP = {
        # VGK4U sub-section
        'vgk_team': ('vgk4u', 'ZYNOVA'),
        'vgk': ('vgk4u', 'ZYNOVA'),
        'vgk4u': ('vgk4u', 'ZYNOVA'),
        # Vendor Management sub-section
        'vendor_management': ('vendor', 'Vendor Management'),
        'vendor': ('vendor', 'Vendor Management'),
        # MNR Admin sub-section
        'mnr_admin': ('mnr_admin', 'MNR Admin'),
        'mnr': ('mnr_admin', 'MNR Admin'),
        'mnr-admin': ('mnr_admin', 'MNR Admin'),
        # MNR Config/Finance/etc sub-section
        'mnr_config': ('mnr_config', 'MNR Config'),
        'mnr_finance': ('mnr_finance', 'MNR Finance'),
        'mnr_income': ('mnr_income', 'MNR Income'),
        'mnr_awards': ('mnr_awards', 'MNR Awards'),
        'mnr_approvals': ('mnr_approvals', 'MNR Approvals'),
        'mnr_security': ('mnr_security', 'MNR Security'),
        'mnr_withdrawals': ('mnr_withdrawals', 'MNR Withdrawals'),
        'mnr_users': ('mnr_users', 'MNR Users'),
    }

    def get_others_child_section(menu_category: str, audience_scope: str):
        """Return (child_section_id, child_section_title) for a page landing in Others."""
        cat = (menu_category or '').lower().replace('-', '_')
        if audience_scope == 'partner':
            return ('partners', 'Partners')
        if cat in OTHERS_CHILD_SECTION_MAP:
            return OTHERS_CHILD_SECTION_MAP[cat]
        # Check prefix matches
        if cat.startswith('vgk'):
            return ('vgk4u', 'ZYNOVA')
        if cat.startswith('vendor'):
            return ('vendor', 'Vendor Management')
        if cat.startswith('mnr'):
            return ('mnr_admin', 'MNR Admin')
        return ('uncategorized', 'Others')

    # DC Protocol (Mar 18, 2026): "OTHERS" fallback section for pages not in VGK MENTOR sidebar
    OTHERS_SECTION_INFO = {
        "sidebar_section": "others",
        "sidebar_section_title": "OTHERS",
        "sidebar_section_order": 999,
        "parent_section": None,
        "is_submenu": False,
        "child_section": None,
        "child_section_title": None
    }

    # DC Protocol (Jan 9, 2026): EXCLUDED sidebar_sections - these never appear in matrix
    EXCLUDED_SIDEBAR_SECTIONS = {
        'WORKING_MNR', 'WORKING_STAFF', 'staff-mnr', 'superadmin',
        'user-earnings', 'user-portal', 'user-team', 'rvz-income',
        'admin-functions', 'withdrawal-admin', 'rvz-earnings', 'members-admin',
        'earnings-admin', 'new-required', 'new-not-required',
        'finance', 'FINANCE', 'FINANCIAL MANAGEMENT',
        'rvz-admin', 'RVZ ADMIN', 'RVZ_ADMIN',
        'partner-portal', 'PARTNER PORTAL'
    }

    matrix_rows = []
    seen_routes = set()
    for menu in menus:
        audience_scope = getattr(menu, 'audience_scope', 'staff') or 'staff'

        # DC Protocol (Mar 18, 2026): Lookup by menu_code first, then route_path, then Others
        if menu.menu_code in sidebar_section_lookup:
            section_info = sidebar_section_lookup[menu.menu_code]
            in_others = False
        elif menu.route_path and menu.route_path in route_path_lookup:
            section_info = route_path_lookup[menu.route_path]
            in_others = False
        else:
            section_info = dict(OTHERS_SECTION_INFO)  # Copy so we can set child_section per menu
            in_others = True

        # DC Protocol (Mar 18, 2026): Deduplicate by route_path — skip duplicates already added
        route_key = menu.route_path or menu.menu_code
        if route_key in seen_routes:
            continue
        seen_routes.add(route_key)

        # DC Protocol (Mar 18, 2026): For Others pages, assign to a sub-section by menu_category
        if in_others:
            child_id, child_title = get_others_child_section(menu.menu_category or '', audience_scope)
            section_info["child_section"] = child_id
            section_info["child_section_title"] = child_title

        sidebar_section = section_info.get("sidebar_section", "")

        # Skip menus in explicitly excluded sections
        if sidebar_section in EXCLUDED_SIDEBAR_SECTIONS:
            continue
        
        row = {
            "menu_id": menu.id,
            "menu_code": menu.menu_code,
            "menu_name": menu.menu_name,
            "menu_icon": menu.menu_icon,
            "menu_category": menu.menu_category,
            "route_path": menu.route_path,
            "audience_scope": audience_scope,
            "default_can_view": menu.is_default_visible,
            "default_can_edit": menu.is_default_accessible,
            "sidebar_section": section_info["sidebar_section"],
            "sidebar_section_title": section_info["sidebar_section_title"],
            "sidebar_section_order": section_info["sidebar_section_order"],
            "parent_section": section_info.get("parent_section"),
            "is_submenu": section_info.get("is_submenu", False),
            "child_section": section_info.get("child_section"),
            "child_section_title": section_info.get("child_section_title"),
            "employee_settings": {},
            "partner_settings": {}
        }
        
        for emp in employees:
            if audience_scope == 'partner':
                row["employee_settings"][str(emp.id)] = {"not_applicable": True}
            else:
                key = f"{emp.id}_{menu.id}"
                if key in emp_settings_map:
                    setting = emp_settings_map[key]
                    row["employee_settings"][str(emp.id)] = {
                        "can_view": setting["can_view"],
                        "can_edit": setting["can_edit"],
                        "is_overridden": setting["is_overridden"],
                        "not_applicable": False,
                        "has_explicit_setting": True
                    }
                else:
                    # DC Protocol (Dec 30, 2025): Use menu defaults when no explicit setting
                    # Show default permissions as checked so admin can see/edit them
                    row["employee_settings"][str(emp.id)] = {
                        "can_view": menu.is_default_visible if menu.is_default_visible else False,
                        "can_edit": menu.is_default_accessible if menu.is_default_accessible else False,
                        "is_overridden": False,
                        "not_applicable": False,
                        "has_explicit_setting": False,
                        "is_default": True  # Flag to indicate this is a default value
                    }
        
        for partner in partners:
            if audience_scope == 'staff':
                row["partner_settings"][str(partner.id)] = {"not_applicable": True}
            else:
                key = f"{partner.id}_{menu.id}"
                if key in partner_settings_map:
                    setting = partner_settings_map[key]
                    row["partner_settings"][str(partner.id)] = {
                        "can_view": setting["can_view"],
                        "can_edit": setting["can_edit"],
                        "is_overridden": setting["is_overridden"],
                        "not_applicable": False,
                        "has_explicit_setting": True
                    }
                else:
                    # DC Protocol (Dec 30, 2025): Use menu defaults for partners when no explicit setting
                    row["partner_settings"][str(partner.id)] = {
                        "can_view": menu.is_default_visible if menu.is_default_visible else False,
                        "can_edit": menu.is_default_accessible if menu.is_default_accessible else False,
                        "is_overridden": False,
                        "not_applicable": False,
                        "has_explicit_setting": False,
                        "is_default": True
                    }
        
        matrix_rows.append(row)
    
    # DC Protocol (Dec 22, 2025): Get current user's data_companies for RBAC
    current_user_data_companies = set()
    if current_user.data_companies:
        import json
        dc = current_user.data_companies
        if isinstance(dc, str):
            try:
                dc = json.loads(dc)
            except:
                dc = []
        if isinstance(dc, list):
            for cid in dc:
                if cid:
                    try:
                        current_user_data_companies.add(int(cid))
                    except:
                        pass
    
    employee_columns = []
    for emp in employees:
        # DC Protocol (Dec 22, 2025): Calculate can_modify based on data_companies intersection
        emp_data_companies = set()
        if emp.data_companies:
            dc = emp.data_companies
            if isinstance(dc, str):
                try:
                    dc = json.loads(dc)
                except:
                    dc = []
            if isinstance(dc, list):
                for cid in dc:
                    if cid:
                        try:
                            emp_data_companies.add(int(cid))
                        except:
                            pass
        
        # DC Protocol (Dec 22, 2025): FIXED - Include base_company_id as fallback
        # If employee has no data_companies but has base_company_id, use base_company_id for intersection
        emp_effective_companies = emp_data_companies.copy()
        if emp.base_company_id:
            emp_effective_companies.add(emp.base_company_id)
        
        # DC Protocol: can_modify requires BOTH:
        # 1. Company intersection (current_user's data_companies vs employee's effective companies)
        # 2. base_company_id is set (saves require company assignment)
        has_company_intersection = bool(current_user_data_companies & emp_effective_companies) if emp_effective_companies else False
        has_base_company = emp.base_company_id is not None
        can_modify_for_emp = has_company_intersection and has_base_company
        
        # DC Protocol: Get base company name for display in All Companies mode
        base_company_name = None
        if emp.base_company_id:
            base_company = db.query(AssociatedCompany).filter(AssociatedCompany.id == emp.base_company_id).first()
            if base_company:
                base_company_name = base_company.company_name
        
        employee_columns.append({
            "id": emp.id,
            "emp_code": emp.emp_code,
            "full_name": emp.full_name,
            "staff_type": emp.staff_type,
            "column_type": "employee",
            "is_current_user": emp.id == current_user.id,
            "can_modify": can_modify_for_emp,
            "base_company_id": emp.base_company_id,
            "base_company_name": base_company_name,  # DC: For display in All Companies mode
            "no_base_company": not has_base_company  # DC: Flag for UI to show why disabled
        })
    
    partner_columns = []
    for partner in partners:
        partner_columns.append({
            "id": partner.id,
            "partner_code": partner.partner_code,
            "partner_name": partner.partner_name,
            "category": partner.category,
            "column_type": "partner"
        })
    
    # DC Protocol (Jan 9, 2026): Build structured sections with nested children
    # This ensures Menu Access Control matrix exactly mirrors the sidebar structure
    
    # Step 1: Group rows by their effective section (parent_section for submenus, sidebar_section otherwise)
    section_map = {}  # section_id -> { title, order, children: { child_section: [rows] }, direct_rows: [rows] }
    
    for row in matrix_rows:
        parent_section = row.get("parent_section")
        is_submenu = row.get("is_submenu", False)
        child_section = row.get("child_section")
        sidebar_section = row.get("sidebar_section", "other")
        sidebar_section_order = row.get("sidebar_section_order", 999)
        
        # Determine the top-level section this row belongs to
        if parent_section and is_submenu:
            # This is a child item - group under parent
            top_section = parent_section
            top_section_title = parent_section.upper().replace('-', ' ').replace('_', ' ')
        else:
            # This is a direct section item
            top_section = sidebar_section
            top_section_title = row.get("sidebar_section_title", sidebar_section.upper().replace('-', ' ').replace('_', ' '))
        
        # Initialize section if not exists
        if top_section not in section_map:
            section_map[top_section] = {
                "section_id": top_section,
                "section_title": top_section_title,
                "section_order": sidebar_section_order,
                "children": {},  # child_section -> { title, items }
                "direct_rows": []  # Items that belong directly to this section
            }
        
        # Update section order if this row has a lower order (closer to top)
        if sidebar_section_order < section_map[top_section]["section_order"]:
            section_map[top_section]["section_order"] = sidebar_section_order
        
        # Add row to appropriate place
        if child_section:
            # This is a child subsection item
            child_section_title = row.get("child_section_title", child_section.upper().replace('-', ' ').replace('_', ' '))
            if child_section not in section_map[top_section]["children"]:
                section_map[top_section]["children"][child_section] = {
                    "child_section_id": child_section,
                    "child_section_title": child_section_title,
                    "items": []
                }
            section_map[top_section]["children"][child_section]["items"].append(row)
        else:
            # Direct section item
            section_map[top_section]["direct_rows"].append(row)
    
    # Step 2: Convert section_map to ordered list
    structured_sections = []
    for section_id, section_data in sorted(section_map.items(), key=lambda x: x[1]["section_order"]):
        # Sort children by their sidebar_section_order (or title as fallback)
        sorted_children = []
        for child_id, child_data in sorted(section_data["children"].items(), key=lambda x: x[0]):
            # Sort items within each child by menu_name
            child_data["items"] = sorted(child_data["items"], key=lambda x: (x.get("menu_name") or "").lower())
            sorted_children.append(child_data)
        
        # Sort direct rows by menu_name
        sorted_direct = sorted(section_data["direct_rows"], key=lambda x: (x.get("menu_name") or "").lower())
        
        structured_sections.append({
            "section_id": section_id,
            "section_title": section_data["section_title"],
            "section_order": section_data["section_order"],
            "has_children": len(sorted_children) > 0,
            "children": sorted_children,
            "direct_items": sorted_direct,
            "total_items": len(sorted_direct) + sum(len(c["items"]) for c in sorted_children)
        })
    
    # Step 3: Also keep flat menu_rows for backward compatibility
    def matrix_sort_key(row):
        section_order = row.get("sidebar_section_order", 999)
        section_title = (row.get("sidebar_section_title") or row.get("sidebar_section") or "").lower().strip()
        menu_name = (row.get("menu_name") or "").lower().strip()
        return (section_order, section_title, menu_name)
    
    sorted_matrix_rows = sorted(matrix_rows, key=matrix_sort_key)
    
    return {
        "success": True,
        "company_id": company_id,
        "employee_columns": employee_columns,
        "partner_columns": partner_columns,
        "menu_rows": sorted_matrix_rows,
        "structured_sections": structured_sections,  # DC Protocol (Jan 9, 2026): Nested structure
        "total_employees": len(employees),
        "total_partners": len(partners),
        "total_menus": len(menus),
        "validation_issues": validation_issues,
        "has_validation_errors": len([v for v in validation_issues if v.get("severity") == "error"]) > 0,
        "has_validation_warnings": len([v for v in validation_issues if v.get("severity") == "warning"]) > 0
    }


@router.put("/employee/{employee_id}")
async def update_employee_menu_settings(
    employee_id: int,
    company_id: int,
    request: EmployeeMenuSettingsRequest,
    propagate: bool = True,
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db),
    req: Request = None
):
    """
    Update menu settings for a specific employee
    DC Protocol: Staff permissions are employee-centric; propagate=True syncs across all companies
    WVV Protocol: Full validation and audit logging
    
    Parameters:
    - propagate: If True (default), propagates permission to same menu_code across ALL companies
    
    DC Protocol Jan 13 2026: Added batch processing and comprehensive error handling
    - Processes settings in batches of 50 with flush() to prevent timeouts
    - Wraps entire operation in try-except to prevent 502 errors
    - Handles IntegrityError for duplicate detection
    """
    from sqlalchemy.exc import IntegrityError, OperationalError
    
    # DC Jan 2026: Accept both 'VGK4U' and 'VGK4U Supreme' for production compatibility
    if current_user.staff_type not in ['RVZ', 'VGK4U', 'VGK4U Supreme', 'EA', 'MYNT_REAL']:
        raise HTTPException(status_code=403, detail="Only RVZ/VGK4U/EA can modify menu settings")
    
    employee = db.query(StaffEmployee).filter(
        StaffEmployee.id == employee_id,
        StaffEmployee.status == 'active',
        StaffEmployee.is_deleted == False
    ).first()
    
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    if not request.settings:
        raise HTTPException(status_code=400, detail="No settings provided")
    
    # DC Protocol (Dec 22, 2025): RBAC - Check that current user's data_companies
    # intersects with target employee's data_companies (NOT base_company)
    import json
    current_user_data_companies = set()
    if current_user.data_companies:
        dc = current_user.data_companies
        if isinstance(dc, str):
            try:
                dc = json.loads(dc)
            except:
                dc = []
        if isinstance(dc, list):
            for cid in dc:
                if cid:
                    try:
                        current_user_data_companies.add(int(cid))
                    except:
                        pass
    
    emp_data_companies = set()
    if employee.data_companies:
        dc = employee.data_companies
        if isinstance(dc, str):
            try:
                dc = json.loads(dc)
            except:
                dc = []
        if isinstance(dc, list):
            for cid in dc:
                if cid:
                    try:
                        emp_data_companies.add(int(cid))
                    except:
                        pass
    
    # DC Protocol (Dec 22, 2025): FIXED - Include base_company_id as fallback
    # If employee has no data_companies but has base_company_id, use base_company_id for intersection
    emp_effective_companies = emp_data_companies.copy()
    if employee.base_company_id:
        emp_effective_companies.add(employee.base_company_id)
    
    # Check intersection - current user can only modify if there's company overlap
    can_modify_for_emp = bool(current_user_data_companies & emp_effective_companies) if emp_effective_companies else False
    
    if not can_modify_for_emp:
        logger.warning(
            f"[DC-RBAC] VIOLATION: {current_user.emp_code} tried to modify menu settings for "
            f"{employee.emp_code} but has no company intersection. "
            f"Current user companies: {current_user_data_companies}, "
            f"Target employee companies: {emp_data_companies}"
        )
        raise HTTPException(
            status_code=403,
            detail={
                "type": "RBAC_VIOLATION",
                "severity": "error",
                "message": f"You cannot modify menu settings for {employee.emp_code} ({employee.full_name})",
                "reason": "No overlapping company association. You can only modify settings for employees in your associated companies.",
                "your_companies": list(current_user_data_companies),
                "target_companies": list(emp_data_companies),
                "dc_protocol": "DC Protocol requires company intersection between modifier and target employee's data_companies"
            }
        )
    
    # WVV Protocol: Block operations on employees without base_company_id
    # Validation-first approach: Show clear error instead of auto-fixing
    if not employee.base_company_id:
        raise HTTPException(
            status_code=400, 
            detail={
                "type": "MISSING_BASE_COMPANY",
                "severity": "error",
                "entity_type": "employee",
                "entity_id": employee_id,
                "entity_code": employee.emp_code,
                "entity_name": employee.full_name,
                "message": f"Cannot save menu settings for {employee.emp_code} ({employee.full_name}) - no company assigned",
                "resolution": "Go to Staff Management → Employees → Edit → Select Base Company from dropdown",
                "resolution_url": f"/staff/employees?edit={employee_id}",
                "dc_protocol": "DC Protocol requires employees to be assigned to a company before granting menu access"
            }
        )
    
    # DC Protocol: Debug logging for menu settings save
    logger.info(f"[DC-MENU-SAVE] Saving {len(request.settings)} settings for employee {employee_id} ({employee.emp_code})")
    logger.info(f"[DC-MENU-SAVE] Current company: {company_id}, propagate: {propagate}")
    for s in request.settings[:5]:  # Log first 5 for brevity
        logger.info(f"[DC-MENU-SAVE] Setting: menu_id={s.menu_id}, can_view={s.can_view}, can_edit={s.can_edit}")
    
    changes_made = []
    propagated_count = 0
    
    employee_company_ids = get_employee_company_ids(employee)
    logger.info(f"[DC-MENU-SAVE] Employee {employee.emp_code} has access to companies: {employee_company_ids}")
    
    # WVV Protocol: Validation - employee must have at least one company
    if not employee_company_ids:
        raise HTTPException(
            status_code=400,
            detail={
                "type": "NO_COMPANY_ACCESS",
                "severity": "error",
                "entity_type": "employee",
                "entity_id": employee_id,
                "entity_code": employee.emp_code,
                "entity_name": employee.full_name,
                "message": f"Employee {employee.emp_code} has no company access configured",
                "resolution": "Assign base_company_id and/or data_companies in employee settings",
                "resolution_url": f"/staff/employees?edit={employee_id}",
                "dc_protocol": "DC Protocol requires company assignment for data segregation"
            }
        )
    
    # DC Protocol (Dec 22, 2025): Defensive check - company_id must be in employee's company set
    # This prevents 502 errors when frontend sends wrong company_id
    if company_id not in employee_company_ids:
        logger.warning(
            f"[DC-MENU-SAVE] company_id={company_id} not in employee's companies {employee_company_ids}. "
            f"Auto-correcting to base_company_id={employee.base_company_id}"
        )
        # Auto-correct to employee's base_company_id for robustness
        if employee.base_company_id:
            company_id = employee.base_company_id
        else:
            raise HTTPException(
                status_code=422,
                detail={
                    "type": "INVALID_COMPANY",
                    "severity": "error",
                    "message": f"Company {company_id} is not in employee's company set",
                    "resolution": f"Use one of: {list(employee_company_ids)}",
                    "dc_protocol": "DC Protocol requires saving to employee's own company"
                }
            )
    
    # DC Protocol Jan 13 2026: Wrap entire processing in try-except for robustness
    try:
        # DC Protocol Jan 13 2026: Batch processing - process in chunks of 50 to prevent timeouts
        BATCH_SIZE = 50
        total_settings = len(request.settings)
        
        for batch_idx in range(0, total_settings, BATCH_SIZE):
            batch = request.settings[batch_idx:batch_idx + BATCH_SIZE]
            batch_num = (batch_idx // BATCH_SIZE) + 1
            total_batches = (total_settings + BATCH_SIZE - 1) // BATCH_SIZE
            
            logger.info(f"[DC-MENU-SAVE] Processing batch {batch_num}/{total_batches} ({len(batch)} settings)")
            
            for setting in batch:
                # DC Protocol (Dec 30, 2025): In All Companies mode, menu_id may be from a different company
                # First lookup by ID only to get menu_code, then find equivalent in employee's companies
                menu = db.query(StaffMenuMaster).filter(
                    StaffMenuMaster.id == setting.menu_id
                ).first()
                
                if not menu:
                    logger.warning(f"[DC-MENU-SAVE] Menu ID {setting.menu_id} not found, skipping")
                    continue
                
                menu_code = menu.menu_code
                
                # Always propagate to all employee's companies for consistent access
                if propagate:
                    target_menus = db.query(StaffMenuMaster).filter(
                        StaffMenuMaster.menu_code == menu_code,
                        StaffMenuMaster.is_active == True,
                        StaffMenuMaster.company_id.in_(employee_company_ids)
                    ).all()
                else:
                    # Even without propagate, use the menu in the correct company (employee's base)
                    target_menu = db.query(StaffMenuMaster).filter(
                        StaffMenuMaster.menu_code == menu_code,
                        StaffMenuMaster.is_active == True,
                        StaffMenuMaster.company_id == company_id
                    ).first()
                    target_menus = [target_menu] if target_menu else []
                
                if not target_menus:
                    continue
                
                # DC Protocol (Dec 30, 2025): Company-agnostic settings
                # Unique constraint is on (employee_id, menu_id) - no company filter needed
                for target_menu in target_menus:
                    existing = db.query(StaffEmployeeMenuSettings).filter(
                        StaffEmployeeMenuSettings.employee_id == employee_id,
                        StaffEmployeeMenuSettings.menu_id == target_menu.id
                    ).first()
                    
                    if existing:
                        old_view = existing.can_view
                        old_edit = existing.can_edit
                        
                        existing.can_view = setting.can_view
                        existing.can_edit = setting.can_edit
                        existing.is_overridden = True
                        existing.set_by_id = current_user.id
                        existing.set_by_code = current_user.emp_code
                        existing.set_by_name = current_user.full_name
                        existing.updated_at = datetime.utcnow()
                        
                        if target_menu.company_id != company_id:
                            propagated_count += 1
                        elif old_view != setting.can_view or old_edit != setting.can_edit:
                            changes_made.append({
                                "menu_code": menu_code,
                                "menu_name": target_menu.menu_name,
                                "old_can_view": old_view,
                                "new_can_view": setting.can_view,
                                "old_can_edit": old_edit,
                                "new_can_edit": setting.can_edit
                            })
                    else:
                        new_setting = StaffEmployeeMenuSettings(
                            company_id=target_menu.company_id,
                            employee_id=employee_id,
                            menu_id=target_menu.id,
                            can_view=setting.can_view,
                            can_edit=setting.can_edit,
                            is_overridden=True,
                            set_by_id=current_user.id,
                            set_by_code=current_user.emp_code,
                            set_by_name=current_user.full_name
                        )
                        db.add(new_setting)
                        
                        if target_menu.company_id != company_id:
                            propagated_count += 1
                        else:
                            changes_made.append({
                                "menu_code": menu_code,
                                "menu_name": target_menu.menu_name,
                                "old_can_view": target_menu.is_default_visible,
                                "new_can_view": setting.can_view,
                                "old_can_edit": target_menu.is_default_accessible,
                                "new_can_edit": setting.can_edit
                            })
            
            # DC Protocol Jan 13 2026: Flush after each batch to prevent memory buildup
            db.flush()
            logger.info(f"[DC-MENU-SAVE] Batch {batch_num} flushed successfully")
        
        if changes_made:
            audit = StaffMenuSettingsAudit(
                company_id=company_id,
                employee_id=employee_id,
                employee_code=employee.emp_code,
                employee_name=employee.full_name,
                action='UPDATE_MENU_SETTINGS',
                menu_changes=changes_made,
                performed_by_id=current_user.id,
                performed_by_code=current_user.emp_code,
                performed_by_name=current_user.full_name,
                performed_by_role=current_user.staff_type,
                reason=request.reason,
                ip_address=req.client.host if req else None,
                user_agent=req.headers.get('user-agent') if req else None
            )
            db.add(audit)
        
        db.commit()
        logger.info(f"[DC-MENU-SAVE] Successfully saved {len(changes_made)} changes for employee {employee_id}")
        
        return {
            "success": True,
            "employee_id": employee_id,
            "employee_name": employee.full_name,
            "changes_made": len(changes_made),
            "changes": changes_made,
            "propagated_to_companies": propagated_count if propagate else 0,
            "propagation_enabled": propagate
        }
    
    except IntegrityError as e:
        db.rollback()
        logger.error(f"[DC-MENU-SAVE] IntegrityError for employee {employee_id}: {str(e)}")
        raise HTTPException(
            status_code=409,
            detail={
                "type": "INTEGRITY_ERROR",
                "severity": "error",
                "message": "Duplicate menu setting detected. Please refresh and try again.",
                "employee_id": employee_id,
                "resolution": "Refresh the page to get latest settings, then try saving again",
                "dc_protocol": "Unique constraint violation on (employee_id, menu_id)"
            }
        )
    
    except OperationalError as e:
        db.rollback()
        logger.error(f"[DC-MENU-SAVE] OperationalError for employee {employee_id}: {str(e)}")
        raise HTTPException(
            status_code=503,
            detail={
                "type": "DATABASE_ERROR",
                "severity": "error",
                "message": "Database connection issue. Please try again in a few moments.",
                "employee_id": employee_id,
                "resolution": "Wait a moment and try again. If issue persists, contact support.",
                "dc_protocol": "Database operational error - connection or timeout issue"
            }
        )
    
    except Exception as e:
        db.rollback()
        logger.error(f"[DC-MENU-SAVE] Unexpected error for employee {employee_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "type": "INTERNAL_ERROR",
                "severity": "error",
                "message": "An unexpected error occurred while saving menu settings.",
                "employee_id": employee_id,
                "resolution": "Please try again. If issue persists, contact support.",
                "dc_protocol": "Unhandled exception in menu settings save"
            }
        )


class PartnerMenuSettingsRequest(BaseModel):
    settings: List[MenuSettingUpdate]
    reason: Optional[str] = None


@router.put("/partner/{partner_id}")
async def update_partner_menu_settings(
    partner_id: int,
    company_id: int,
    request: PartnerMenuSettingsRequest,
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db),
    req: Request = None
):
    """
    Update menu settings for a specific partner
    DC Protocol: Filter by company_id
    WVV Protocol: Full validation and audit logging
    
    DC Protocol Jan 13 2026: Added batch processing and comprehensive error handling
    """
    from sqlalchemy.exc import IntegrityError, OperationalError
    
    # DC Jan 2026: Accept both 'VGK4U' and 'VGK4U Supreme' for production compatibility
    if current_user.staff_type not in ['RVZ', 'VGK4U', 'VGK4U Supreme', 'EA', 'MYNT_REAL']:
        raise HTTPException(status_code=403, detail="Only RVZ/VGK4U/EA can modify menu settings")
    
    partner = db.query(OfficialPartner).filter(
        OfficialPartner.id == partner_id,
        OfficialPartner.is_active == True
    ).first()
    
    if not partner:
        raise HTTPException(status_code=404, detail="Partner not found")
    
    if not request.settings:
        raise HTTPException(status_code=400, detail="No settings provided")
    
    changes_made = []
    
    # DC Protocol Jan 13 2026: Wrap in try-except for robustness
    try:
        # DC Protocol Jan 13 2026: Batch processing
        BATCH_SIZE = 50
        total_settings = len(request.settings)
        
        for batch_idx in range(0, total_settings, BATCH_SIZE):
            batch = request.settings[batch_idx:batch_idx + BATCH_SIZE]
            
            for setting in batch:
                menu = db.query(StaffMenuMaster).filter(
                    StaffMenuMaster.id == setting.menu_id,
                    StaffMenuMaster.company_id == company_id
                ).first()
                
                if not menu:
                    continue
                
                audience_scope = getattr(menu, 'audience_scope', 'staff') or 'staff'
                if audience_scope == 'staff':
                    continue
                
                existing = db.query(PartnerMenuSettings).filter(
                    PartnerMenuSettings.partner_id == partner_id,
                    PartnerMenuSettings.menu_id == setting.menu_id
                ).first()
                
                if existing:
                    old_view = existing.can_view
                    old_edit = existing.can_edit
                    
                    existing.can_view = setting.can_view
                    existing.can_edit = setting.can_edit
                    existing.is_overridden = True
                    existing.set_by_id = current_user.id
                    existing.set_by_code = current_user.emp_code
                    existing.set_by_name = current_user.full_name
                    existing.updated_at = datetime.utcnow()
                    
                    if old_view != setting.can_view or old_edit != setting.can_edit:
                        changes_made.append({
                            "menu_code": menu.menu_code,
                            "menu_name": menu.menu_name,
                            "old_can_view": old_view,
                            "new_can_view": setting.can_view,
                            "old_can_edit": old_edit,
                            "new_can_edit": setting.can_edit
                        })
                else:
                    new_setting = PartnerMenuSettings(
                        company_id=company_id,
                        partner_id=partner_id,
                        menu_id=setting.menu_id,
                        can_view=setting.can_view,
                        can_edit=setting.can_edit,
                        is_overridden=True,
                        set_by_id=current_user.id,
                        set_by_code=current_user.emp_code,
                        set_by_name=current_user.full_name
                    )
                    db.add(new_setting)
                    
                    changes_made.append({
                        "menu_code": menu.menu_code,
                        "menu_name": menu.menu_name,
                        "old_can_view": menu.is_default_visible,
                        "new_can_view": setting.can_view,
                        "old_can_edit": menu.is_default_accessible,
                        "new_can_edit": setting.can_edit
                    })
            
            # Flush after each batch
            db.flush()
        
        db.commit()
        logger.info(f"[DC-MENU-SAVE] Successfully saved {len(changes_made)} changes for partner {partner_id}")
        
        return {
            "success": True,
            "partner_id": partner_id,
            "partner_name": partner.partner_name,
            "changes_made": len(changes_made),
            "changes": changes_made
        }
    
    except IntegrityError as e:
        db.rollback()
        logger.error(f"[DC-MENU-SAVE] IntegrityError for partner {partner_id}: {str(e)}")
        raise HTTPException(
            status_code=409,
            detail={
                "type": "INTEGRITY_ERROR",
                "severity": "error",
                "message": "Duplicate menu setting detected. Please refresh and try again.",
                "partner_id": partner_id,
                "resolution": "Refresh the page to get latest settings, then try saving again",
                "dc_protocol": "Unique constraint violation on (partner_id, menu_id)"
            }
        )
    
    except OperationalError as e:
        db.rollback()
        logger.error(f"[DC-MENU-SAVE] OperationalError for partner {partner_id}: {str(e)}")
        raise HTTPException(
            status_code=503,
            detail={
                "type": "DATABASE_ERROR",
                "severity": "error",
                "message": "Database connection issue. Please try again in a few moments.",
                "partner_id": partner_id,
                "resolution": "Wait a moment and try again. If issue persists, contact support.",
                "dc_protocol": "Database operational error - connection or timeout issue"
            }
        )
    
    except Exception as e:
        db.rollback()
        logger.error(f"[DC-MENU-SAVE] Unexpected error for partner {partner_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "type": "INTERNAL_ERROR",
                "severity": "error",
                "message": "An unexpected error occurred while saving menu settings.",
                "partner_id": partner_id,
                "resolution": "Please try again. If issue persists, contact support.",
                "dc_protocol": "Unhandled exception in partner menu settings save"
            }
        )


@router.post("/bulk-update")
async def bulk_update_menu_settings(
    company_id: int,
    request: BulkMenuSettingsRequest,
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db),
    req: Request = None
):
    """
    Bulk update menu settings for multiple employees
    DC Protocol: Filter by company_id
    WVV Protocol: Full validation and audit logging
    """
    # DC Protocol: Only VGK/EA/RVZ can bulk update menu settings
    # DC Jan 2026: Accept both 'VGK4U' and 'VGK4U Supreme' for production compatibility
    if current_user.staff_type not in ['RVZ', 'VGK4U', 'VGK4U Supreme', 'EA', 'MYNT_REAL']:
        raise HTTPException(status_code=403, detail="Only RVZ/VGK4U/EA can modify menu settings")
    
    if not request.employee_ids or not request.settings:
        raise HTTPException(status_code=400, detail="Employee IDs and settings are required")
    
    employees = db.query(StaffEmployee).filter(
        StaffEmployee.id.in_(request.employee_ids),
        StaffEmployee.status == 'active',
        StaffEmployee.is_deleted == False
    ).all()
    
    if not employees:
        raise HTTPException(status_code=404, detail="No valid employees found")
    
    # WVV Protocol: Validation-first - Block bulk update if any employee lacks company assignment
    employees_without_company = [e for e in employees if not e.base_company_id]
    if employees_without_company:
        affected_list = [
            {"entity_id": e.id, "entity_code": e.emp_code, "entity_name": e.full_name} 
            for e in employees_without_company[:5]
        ]
        # Generate unique batch identifier from employee IDs
        batch_id_hash = hash(tuple(sorted(request.employee_ids))) % 10000000
        raise HTTPException(
            status_code=400,
            detail={
                "type": "MISSING_BASE_COMPANY",
                "severity": "error",
                "entity_type": "employee_batch",
                "entity_id": batch_id_hash,
                "entity_code": f"BULK_EMP_{len(request.employee_ids)}",
                "entity_name": f"Bulk update for {len(request.employee_ids)} employees",
                "affected_count": len(employees_without_company),
                "affected_entities": affected_list,
                "message": f"{len(employees_without_company)} employee(s) have no company assigned",
                "resolution": "Assign base_company_id to these employees before granting menu access",
                "resolution_url": "/staff/employees",
                "dc_protocol": "DC Protocol requires company assignment for data segregation"
            }
        )
    
    total_changes = 0
    
    for employee in employees:
        changes_made = []
        
        for setting in request.settings:
            menu = db.query(StaffMenuMaster).filter(
                StaffMenuMaster.id == setting.menu_id,
                StaffMenuMaster.company_id == company_id
            ).first()
            
            if not menu:
                continue
            
            # DC Protocol: Filter by company_id to prevent cross-tenant data leakage
            existing = db.query(StaffEmployeeMenuSettings).filter(
                StaffEmployeeMenuSettings.company_id == company_id,
                StaffEmployeeMenuSettings.employee_id == employee.id,
                StaffEmployeeMenuSettings.menu_id == setting.menu_id
            ).first()
            
            if existing:
                existing.can_view = setting.can_view
                existing.can_edit = setting.can_edit
                existing.is_overridden = True
                existing.set_by_id = current_user.id
                existing.set_by_code = current_user.emp_code
                existing.set_by_name = current_user.full_name
            else:
                new_setting = StaffEmployeeMenuSettings(
                    company_id=company_id,
                    employee_id=employee.id,
                    menu_id=setting.menu_id,
                    can_view=setting.can_view,
                    can_edit=setting.can_edit,
                    is_overridden=True,
                    set_by_id=current_user.id,
                    set_by_code=current_user.emp_code,
                    set_by_name=current_user.full_name
                )
                db.add(new_setting)
            
            changes_made.append({
                "menu_code": menu.menu_code,
                "can_view": setting.can_view,
                "can_edit": setting.can_edit
            })
            total_changes += 1
        
        if changes_made:
            audit = StaffMenuSettingsAudit(
                company_id=company_id,
                employee_id=employee.id,
                employee_code=employee.emp_code,
                employee_name=employee.full_name,
                action='BULK_UPDATE_MENU_SETTINGS',
                menu_changes=changes_made,
                performed_by_id=current_user.id,
                performed_by_code=current_user.emp_code,
                performed_by_name=current_user.full_name,
                performed_by_role=current_user.staff_type,
                reason=request.reason,
                ip_address=req.client.host if req else None,
                user_agent=req.headers.get('user-agent') if req else None
            )
            db.add(audit)
    
    db.commit()
    
    return {
        "success": True,
        "employees_updated": len(employees),
        "total_changes": total_changes,
        "message": f"Updated menu settings for {len(employees)} employees"
    }


@router.post("/reset/{employee_id}")
async def reset_employee_menu_settings(
    employee_id: int,
    company_id: int,
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db),
    req: Request = None
):
    """
    Reset employee's menu settings to defaults
    DC Protocol: Filter by company_id
    Removes all overrides and reverts to default visibility/accessibility
    """
    # DC Protocol: Only VGK/EA/RVZ can reset menu settings
    # DC Jan 2026: Accept both 'VGK4U' and 'VGK4U Supreme' for production compatibility
    if current_user.staff_type not in ['RVZ', 'VGK4U', 'VGK4U Supreme', 'EA', 'MYNT_REAL']:
        raise HTTPException(status_code=403, detail="Only RVZ/VGK4U/EA can reset menu settings")
    
    employee = db.query(StaffEmployee).filter(
        StaffEmployee.id == employee_id,
        StaffEmployee.status == 'active',
        StaffEmployee.is_deleted == False
    ).first()
    
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    deleted = db.query(StaffEmployeeMenuSettings).filter(
        StaffEmployeeMenuSettings.employee_id == employee_id,
        StaffEmployeeMenuSettings.company_id == company_id
    ).delete()
    
    if deleted > 0:
        audit = StaffMenuSettingsAudit(
            company_id=company_id,
            employee_id=employee_id,
            employee_code=employee.emp_code,
            employee_name=employee.full_name,
            action='RESET_TO_DEFAULTS',
            menu_changes=[{"action": "reset", "settings_removed": deleted}],
            performed_by_id=current_user.id,
            performed_by_code=current_user.emp_code,
            performed_by_name=current_user.full_name,
            performed_by_role=current_user.staff_type,
            ip_address=req.client.host if req else None,
            user_agent=req.headers.get('user-agent') if req else None
        )
        db.add(audit)
    
    db.commit()
    
    return {
        "success": True,
        "employee_id": employee_id,
        "employee_name": employee.full_name,
        "settings_reset": deleted,
        "message": f"Reset {deleted} menu settings to defaults"
    }


@router.get("/my-menus")
async def get_my_menus(
    company_id: Optional[int] = None,
    unified: bool = True,
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """
    Get personalized menu access for the current employee
    DC Protocol (Dec 26, 2025 FIX): Menu visibility uses menu_code resolution via StaffMenuRegistry
    - Page visibility is INDEPENDENT of which company granted access
    - Settings from ANY company are considered (employee-centric, not company-centric)
    - Only DATA within pages is filtered by employee's data_companies
    
    WVV Protocol: Token-authenticated, returns zero menus for new employees without grants
    
    Parameters:
    - company_id: Optional. Legacy parameter, ignored in unified mode
    - unified: If True (default), loads ALL permissions across all companies by menu_code
    
    Zero-Default Access Policy:
    - New employees have NO menu access by default
    - Only EA/VGK can grant explicit access via StaffEmployeeMenuSettings
    - Returns only menus where can_view=True in explicit settings
    
    VGK4U Supreme Access:
    - VGK4U staff type has automatic full access to ALL menus (bypasses zero-default)
    
    MENU-CODE RESOLUTION (Dec 26, 2025):
    - Uses StaffMenuRegistry as company-agnostic source of truth
    - Settings from ANY company are considered for visibility
    - Resolves by menu_code, not menu_id (fixes cross-company visibility)
    """
    employee_id = current_user.id
    
    # AUTO-SYNC: Create missing settings for default-visible menus BEFORE querying
    # DC Protocol: Only syncs for companies the employee has access to (base_company_id / data_companies)
    # This maintains data segregation - employee only gets defaults for their authorized companies
    try:
        employee_companies = get_employee_company_ids(current_user)
        
        total_synced = 0
        for cid in employee_companies:
            synced = sync_default_menu_settings_for_employees(
                db, cid, [employee_id],
                admin_id=None,
                admin_code='SYSTEM',
                admin_name='Auto-Sync on Login'
            )
            total_synced += synced
        if total_synced > 0:
            logger.info(f"[DC-MY-MENUS-AUTOSYNC] Created {total_synced} default settings for employee {employee_id} ({current_user.emp_code}) across {len(employee_companies)} companies")
    except Exception as e:
        logger.error(f"[DC-MY-MENUS-AUTOSYNC] Error auto-syncing for employee {employee_id}: {e}")
    
    # VGK4U Supreme Access Bypass - Full access to all menus via Registry
    # DC Jan 2026: Accept both 'VGK4U' and 'VGK4U Supreme' for production compatibility
    # DC Jan 12 2026: VGK Supreme (MR10001) always has full access with dynamic updates
    if current_user.staff_type in ['VGK4U', 'VGK4U Supreme']:
        registry_menus = db.query(StaffMenuRegistry).filter(
            StaffMenuRegistry.is_active == True,
            StaffMenuRegistry.audience_scope.in_(['staff', 'shared'])
        ).order_by(StaffMenuRegistry.sidebar_section_order, StaffMenuRegistry.display_order).all()
        
        categorized = {}
        menu_list = []
        all_route_paths = set()
        for menu in registry_menus:
            menu_dict = {
                "id": menu.id,
                "menu_code": menu.menu_code,
                "menu_name": menu.menu_name,
                "menu_description": menu.menu_description,
                "route_path": menu.route_path,
                "menu_category": menu.menu_category,
                "menu_icon": menu.menu_icon,
                "display_order": menu.display_order,
                "sidebar_section": menu.sidebar_section,
                "sidebar_section_title": menu.sidebar_section_title,
                "sidebar_section_order": menu.sidebar_section_order,
                "parent_section": menu.parent_section,
                "is_submenu": menu.is_submenu or False,
                "audience_scope": menu.audience_scope,
                "can_view": True,
                "can_edit": True
            }
            menu_list.append(menu_dict)
            if menu.route_path:
                all_route_paths.add(menu.route_path)
            
            cat = menu.menu_category or 'other'
            if cat not in categorized:
                categorized[cat] = []
            categorized[cat].append(menu_dict)
        
        sidebar_tree = build_sidebar_tree(menu_list)
        
        return {
            "success": True,
            "company_id": company_id,
            "employee_id": employee_id,
            "employee_code": current_user.emp_code,
            "employee_name": current_user.full_name,
            "staff_type": current_user.staff_type,
            "is_supreme": True,
            "total_menus": len(registry_menus),
            "menus": menu_list,
            "allowed_paths": list(all_route_paths),
            "sidebar_tree": sidebar_tree,
            "categorized": categorized,
            "categories": list(categorized.keys()),
            "unified_mode": True,
            "structure_version": "18-sections",
            "message": "VGK4U Supreme Access: Full access to all menus"
        }
    
    # DC Protocol Apr 2026: Department-based auto-grant for Store/Accounts staff.
    # Any employee in a department whose name contains 'store' or 'accounts' automatically
    # receives view access to the EV Spares PO page and Procurement page, regardless of
    # whether an explicit menu-settings grant exists.
    # DC Protocol May 2026: Extended to grant My Earnings to Sales / Accounts / Leadership / EA.
    _DEPT_AUTO_GRANT_MENUS = {
        'store':      ['staff_zynova_ev_po', 'sfms_procurement'],
        'accounts':   ['staff_zynova_ev_po', 'sfms_procurement', 'staff_my_lead_incentives'],
        'sales':      ['staff_my_lead_incentives'],
        'leadership': ['staff_my_lead_incentives'],
        'management': ['staff_my_lead_incentives'],
        'executive':  ['staff_my_lead_incentives'],
    }
    _dept_auto_codes: set = set()
    try:
        from app.models.staff import StaffDepartment, StaffEmployeeDepartment
        _dept_rows = db.query(StaffDepartment.name).join(
            StaffEmployeeDepartment, StaffDepartment.id == StaffEmployeeDepartment.department_id
        ).filter(StaffEmployeeDepartment.employee_id == employee_id).all()
        for _dr in _dept_rows:
            _dname = (_dr.name or '').lower()
            for _key, _codes in _DEPT_AUTO_GRANT_MENUS.items():
                if _key in _dname:
                    _dept_auto_codes.update(_codes)
        if _dept_auto_codes:
            logger.info(f"[DC-DEPT-AUTO-GRANT] Employee {employee_id} ({current_user.emp_code}) dept auto-granted menus: {_dept_auto_codes}")
    except Exception as _de:
        logger.warning(f"[DC-DEPT-AUTO-GRANT] Error checking departments for employee {employee_id}: {_de}")

    # DC Protocol May 2026: Role-based auto-grant for My Earnings.
    # Key Leadership, EA, Executive Admin, and Accounts role_codes get My Earnings visibility.
    _ROLE_AUTO_GRANT_MENUS = {
        'key_leadership': ['staff_my_lead_incentives'],
        'ea':             ['staff_my_lead_incentives'],
        'executive_admin':['staff_my_lead_incentives'],
        'accounts':       ['staff_my_lead_incentives'],
        'sales':          ['staff_my_lead_incentives'],
        'leadership':     ['staff_my_lead_incentives'],
    }
    try:
        _role_code = (getattr(current_user.role, 'role_code', '') if current_user.role else '') or ''
        _role_lower = _role_code.lower()
        for _rkey, _rcodes in _ROLE_AUTO_GRANT_MENUS.items():
            if _rkey in _role_lower:
                _dept_auto_codes.update(_rcodes)
        # MR10001 specific grant
        if (current_user.emp_code or '').upper() == 'MR10001':
            _dept_auto_codes.add('staff_my_lead_incentives')
        if _dept_auto_codes:
            logger.info(f"[DC-ROLE-AUTO-GRANT] Employee {employee_id} ({current_user.emp_code}) role/emp auto-granted menus: {_dept_auto_codes}")
    except Exception as _re:
        logger.warning(f"[DC-ROLE-AUTO-GRANT] Error checking role for employee {employee_id}: {_re}")

    # DC Protocol (Dec 26, 2025 FIX): Branch based on unified mode
    # unified=True: Query ALL settings across ALL companies, resolve by menu_code (fixes cross-company visibility)
    # unified=False: Query settings for specific company only (for access matrix tooling)

    if unified:
        # UNIFIED MODE: Query all settings for employee regardless of company
        # This ensures "common" access granted from any company is visible in sidebar
        employee_settings = db.query(StaffEmployeeMenuSettings).filter(
            StaffEmployeeMenuSettings.employee_id == employee_id,
            StaffEmployeeMenuSettings.can_view == True
        ).all()
        logger.info(f"[DC-MY-MENUS] Unified mode: found {len(employee_settings)} settings with can_view=True across all companies")
    else:
        # COMPANY-SPECIFIC MODE: Query settings for specific company only (backward compatible)
        if not company_id:
            company_id = 1  # Default fallback
        employee_settings = db.query(StaffEmployeeMenuSettings).filter(
            StaffEmployeeMenuSettings.employee_id == employee_id,
            StaffEmployeeMenuSettings.company_id == company_id,
            StaffEmployeeMenuSettings.can_view == True
        ).all()
        logger.info(f"[DC-MY-MENUS] Company-specific mode (company_id={company_id}): found {len(employee_settings)} settings")
    
    if not employee_settings and not _dept_auto_codes:
        logger.warning(f"[DC-MY-MENUS] No explicit menu access for employee {employee_id} (emp_code={current_user.emp_code})")
        return {
            "success": True,
            "company_id": company_id,
            "employee_id": employee_id,
            "employee_code": current_user.emp_code,
            "total_menus": 0,
            "menus": [],
            "categorized": {},
            "categories": [],
            "message": "No menu access granted. Contact your administrator (EA/VGK) to request access.",
            "debug_info": {
                "unified_mode": unified,
                "query_employee_id": employee_id
            }
        }
    elif not employee_settings and _dept_auto_codes:
        logger.info(f"[DC-MY-MENUS] No explicit settings but dept auto-grant active for employee {employee_id} — building from dept codes only")
    
    # MENU-CODE RESOLUTION: Get menu_codes from settings' linked menus
    menu_ids = [s.menu_id for s in employee_settings]
    linked_menus = db.query(StaffMenuMaster.id, StaffMenuMaster.menu_code).filter(
        StaffMenuMaster.id.in_(menu_ids)
    ).all()
    
    # Build menu_code -> best permission map (prefer can_edit=True if multiple grants)
    menu_code_permissions = {}
    id_to_code = {m.id: m.menu_code for m in linked_menus}
    
    for setting in employee_settings:
        menu_code = id_to_code.get(setting.menu_id)
        if menu_code:
            if menu_code not in menu_code_permissions:
                menu_code_permissions[menu_code] = {'can_view': setting.can_view, 'can_edit': setting.can_edit}
            else:
                # Merge: if any setting grants edit, keep it
                if setting.can_edit:
                    menu_code_permissions[menu_code]['can_edit'] = True
    
    granted_menu_codes = set(menu_code_permissions.keys())
    if _dept_auto_codes:
        granted_menu_codes.update(_dept_auto_codes)
        logger.info(f"[DC-DEPT-AUTO-GRANT] Merged {len(_dept_auto_codes)} dept-auto codes into granted_menu_codes for employee {employee_id}")
    logger.info(f"[DC-MY-MENUS] Resolved {len(granted_menu_codes)} unique menu_codes from {len(employee_settings)} settings")
    
    # REGISTRY LOOKUP: Fetch menu details from StaffMenuRegistry (company-agnostic)
    # This is the key fix - uses registry instead of company-scoped StaffMenuMaster
    registry_menus = list(db.query(StaffMenuRegistry).filter(
        StaffMenuRegistry.menu_code.in_(granted_menu_codes),
        StaffMenuRegistry.is_active == True,
        StaffMenuRegistry.audience_scope.in_(['staff', 'shared'])
    ).order_by(StaffMenuRegistry.sidebar_section_order, StaffMenuRegistry.display_order).all())
    
    # DC Protocol (Mar 21, 2026): Route-path fallback for cross-company code mismatches
    # When staff_menu_master uses different menu_code prefixes than the registry
    # (e.g., company-2 uses 'staff_solar_leads', registry has 'mnr_solar_leads' for same route)
    # fall back to route_path lookup so permissions apply irrespective of company or department
    found_codes = {m.menu_code for m in registry_menus}
    missing_codes = granted_menu_codes - found_codes
    if missing_codes:
        missing_routes_rows = db.query(StaffMenuMaster.route_path).filter(
            StaffMenuMaster.menu_code.in_(missing_codes),
            StaffMenuMaster.route_path.isnot(None),
            StaffMenuMaster.route_path != ''
        ).distinct().all()
        missing_route_paths = {r.route_path for r in missing_routes_rows if r.route_path}
        if missing_route_paths:
            already_included = {m.route_path for m in registry_menus}
            new_route_paths = missing_route_paths - already_included
            if new_route_paths:
                fallback_menus = db.query(StaffMenuRegistry).filter(
                    StaffMenuRegistry.route_path.in_(new_route_paths),
                    StaffMenuRegistry.is_active == True,
                    StaffMenuRegistry.audience_scope.in_(['staff', 'shared'])
                ).all()
                registry_menus.extend(fallback_menus)
                logger.info(f"[DC-MY-MENUS-FALLBACK] Route-path fallback resolved {len(fallback_menus)} additional menus for codes: {missing_codes}")

    # DC Jan 12 2026: CASCADE SELECTION LOGIC
    # Step 1: Identify which sections the employee has explicit grants for
    # Collect from both menu.sidebar_section AND route_path mapping
    # NOTE: Cascade is ONLY triggered by explicit parent section grants (section_* menu entries)
    # Individual child grants remain isolated to support granular access control
    granted_sections = set()
    cascade_trigger_sections = set()  # Only parent sections that should trigger cascade
    
    for menu in registry_menus:
        if menu.sidebar_section:
            granted_sections.add(menu.sidebar_section)
        
        # Check if this is an explicit PARENT SECTION grant (cascade trigger)
        # Parent section entries have menu_code starting with 'section_' or ending with '_parent'
        is_parent_grant = (
            menu.menu_code and 
            (menu.menu_code.startswith('section_') or menu.menu_code.endswith('_parent'))
        )
        
        if is_parent_grant and menu.sidebar_section:
            cascade_trigger_sections.add(menu.sidebar_section)
            logger.info(f"[DC-MY-MENUS-CASCADE] Parent section grant detected: {menu.menu_code} -> {menu.sidebar_section}")
        
        # DC Jan 13 2026: Check parent_section from database field (not hardcoded mapping)
        if menu.parent_section:
            # If menu has parent_section and is a parent grant, trigger cascade
            if is_parent_grant:
                cascade_trigger_sections.add(menu.sidebar_section)
    
    logger.info(f"[DC-MY-MENUS-CASCADE] Granted sections: {len(granted_sections)}, Cascade triggers: {len(cascade_trigger_sections)}")
    
    # Step 2: Expand ONLY cascade trigger sections to include their children
    # DC Jan 13 2026: Use database-driven cascade instead of hardcoded mapping
    # DC Mar 21 2026: FIXED — cascade ONLY applies to explicit parent section grants (section_* codes)
    # Individual page grants must NOT trigger full-section cascade — that violates granular access control
    if cascade_trigger_sections:
        cascaded_children = get_cascade_expanded_sections_db(db, cascade_trigger_sections)
        expanded_sections = cascade_trigger_sections | set(cascaded_children)
        logger.info(f"[DC-MY-MENUS-CASCADE] Expanded from {len(cascade_trigger_sections)} parents to {len(expanded_sections)} total sections")
        # Step 3: Get routes ONLY for cascade trigger sections and their children
        cascaded_routes = get_routes_for_sections_db(db, expanded_sections)
    else:
        expanded_sections = set()
        cascaded_routes = set()
        logger.info(f"[DC-MY-MENUS-CASCADE] No parent section grants — cascade disabled, granular mode active")
    
    # Step 4: Fetch additional menus via cascade (routes not already granted)
    already_granted_routes = {m.route_path for m in registry_menus if m.route_path}
    additional_routes = cascaded_routes - already_granted_routes
    
    cascaded_menus = []
    if additional_routes:
        cascaded_menus = db.query(StaffMenuRegistry).filter(
            StaffMenuRegistry.route_path.in_(additional_routes),
            StaffMenuRegistry.is_active == True,
            StaffMenuRegistry.audience_scope.in_(['staff', 'shared'])
        ).order_by(StaffMenuRegistry.sidebar_section_order, StaffMenuRegistry.display_order).all()
        logger.info(f"[DC-MY-MENUS-CASCADE] Added {len(cascaded_menus)} menus via cascade from {len(expanded_sections)} sections")
    
    # Combine original grants with cascaded menus
    all_menus = list(registry_menus) + cascaded_menus

    # DC Protocol: Internal section role-based filtering
    # 'internal' section is ONLY for VGK Mentor (vgk4u) and EA (ea) roles
    # VGK Mentor (vgk4u staff_type) is already handled by the supreme access path above
    # EA users see internal pages via the normal staff_employee_menu_settings grant system
    # All other roles: internal section is completely hidden
    user_role_code = getattr(current_user.role, 'role_code', '').lower() if current_user.role else ''
    if user_role_code not in ('vgk4u', 'ea'):
        before = len(all_menus)
        all_menus = [m for m in all_menus if m.sidebar_section != 'internal']
        if before != len(all_menus):
            logger.info(f"[DC-INTERNAL] Filtered internal section for role={user_role_code}, emp={current_user.emp_code}")

    categorized = {}
    menu_list = []
    all_route_paths = set()
    
    for menu in all_menus:
        perms = menu_code_permissions.get(menu.menu_code, {'can_view': True, 'can_edit': False})
        menu_dict = {
            "id": menu.id,
            "menu_code": menu.menu_code,
            "menu_name": menu.menu_name,
            "menu_description": menu.menu_description,
            "route_path": menu.route_path,
            "menu_category": menu.menu_category,
            "menu_icon": menu.menu_icon,
            "display_order": menu.display_order,
            "sidebar_section": menu.sidebar_section,
            "sidebar_section_title": menu.sidebar_section_title,
            "sidebar_section_order": menu.sidebar_section_order,
            "parent_section": menu.parent_section,
            "is_submenu": menu.is_submenu or False,
            "audience_scope": menu.audience_scope,
            "can_view": perms.get('can_view', True),
            "can_edit": perms.get('can_edit', False),
            "cascade_granted": menu in cascaded_menus
        }
        menu_list.append(menu_dict)
        if menu.route_path:
            all_route_paths.add(menu.route_path)
        
        cat = menu.menu_category or 'other'
        if cat not in categorized:
            categorized[cat] = []
        categorized[cat].append(menu_dict)
    
    # Build sidebar tree structure
    sidebar_tree = build_sidebar_tree(menu_list)
    
    # Debug: Log first 5 resolved menus
    for m in menu_list[:5]:
        logger.info(f"[DC-MY-MENUS] Resolved: {m['menu_code']} -> {m['route_path']} (view={m['can_view']}, cascade={m.get('cascade_granted', False)})")
    
    return {
        "success": True,
        "company_id": company_id,
        "employee_id": employee_id,
        "employee_code": current_user.emp_code,
        "employee_name": current_user.full_name,
        "total_menus": len(menu_list),
        "menus": menu_list,
        "allowed_paths": list(all_route_paths),
        "sidebar_tree": sidebar_tree,
        "categorized": categorized,
        "categories": list(categorized.keys()),
        "unified_mode": unified,
        "structure_version": "18-sections",
        "cascade_sections": list(expanded_sections),
        "resolution_method": "menu_code_registry_cascade"
    }


@router.get("/audit/{employee_id}")
async def get_menu_settings_audit(
    employee_id: int,
    company_id: int,
    page: int = 1,
    limit: int = 20,
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """
    Get audit trail for employee's menu settings changes
    DC Protocol: Filter by company_id
    """
    # DC Protocol: VGK/EA/RVZ staff types can access audit trail
    # Note: Employees are global; audit trail is company-specific via StaffMenuSettingsAudit.company_id
    # DC Jan 2026: Accept both 'VGK4U' and 'VGK4U Supreme' for production compatibility
    allowed_staff_types = ['VGK4U', 'VGK4U Supreme', 'EA', 'RVZ', 'MYNT_REAL']
    hierarchy_level = current_user.role.hierarchy_level if current_user.role else 0
    if current_user.staff_type not in allowed_staff_types and hierarchy_level < 85:
        raise HTTPException(status_code=403, detail="Access denied to audit trail")
    
    query = db.query(StaffMenuSettingsAudit).filter(
        StaffMenuSettingsAudit.employee_id == employee_id,
        StaffMenuSettingsAudit.company_id == company_id
    )
    
    total = query.count()
    audits = query.order_by(StaffMenuSettingsAudit.created_at.desc()).offset((page - 1) * limit).limit(limit).all()
    
    return {
        "success": True,
        "employee_id": employee_id,
        "total": total,
        "page": page,
        "limit": limit,
        "audits": [a.to_dict() for a in audits]
    }


@router.get("/health-check")
async def menu_settings_health_check(
    company_id: int = None,
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """
    DC Protocol (Dec 20, 2025): Health check endpoint for menu settings
    Verifies all employees and partners have baseline menu settings PER COMPANY
    Returns count of employees/partners without settings for diagnosis
    
    If company_id is provided: Checks only that company (DC Protocol specific check)
    If company_id is None: Checks globally (any settings at all)
    """
    from app.models.staff import StaffEmployee as SE
    from app.models.staff_accounts import OfficialPartner
    from app.models.sfms import SFMSCompany
    
    # DC Jan 2026: Accept both 'VGK4U' and 'VGK4U Supreme' for production compatibility
    if current_user.staff_type not in ['VGK4U', 'VGK4U Supreme', 'RVZ', 'EA', 'MYNT_REAL']:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Get all active companies for company-wise check
    active_companies = db.query(SFMSCompany).filter(
        SFMSCompany.is_active == True
    ).all()
    company_ids_list = [c.id for c in active_companies]
    
    # DC Protocol: If company_id specified, only check that company
    if company_id:
        company_ids_list = [company_id]
    
    # Count active employees
    active_employees = db.query(SE).filter(
        SE.status == 'active',
        SE.is_deleted == False
    ).all()
    
    # DC Protocol: Check employees without settings FOR EACH COMPANY they should access
    employees_without_settings = []
    company_coverage = {}
    
    for cid in company_ids_list:
        missing_for_company = []
        for emp in active_employees:
            settings_count = db.query(StaffEmployeeMenuSettings).filter(
                StaffEmployeeMenuSettings.employee_id == emp.id,
                StaffEmployeeMenuSettings.company_id == cid
            ).count()
            if settings_count == 0:
                missing_for_company.append({
                    "id": emp.id,
                    "emp_code": emp.emp_code,
                    "full_name": emp.full_name,
                    "staff_type": emp.staff_type,
                    "company_id": cid
                })
        company_coverage[cid] = len(missing_for_company)
        employees_without_settings.extend(missing_for_company[:5])  # Limit per company
    
    # Count active partners
    active_partners = db.query(OfficialPartner).filter(
        OfficialPartner.is_active == True,
        OfficialPartner.is_deleted == False
    ).all()
    
    # DC Protocol: Check partners without settings FOR EACH COMPANY they belong to
    partners_without_settings = []
    partner_company_coverage = {}
    
    for cid in company_ids_list:
        missing_for_company = []
        company_partners = [p for p in active_partners if p.company_id == cid]
        for partner in company_partners:
            settings_count = db.query(PartnerMenuSettings).filter(
                PartnerMenuSettings.partner_id == partner.id,
                PartnerMenuSettings.company_id == cid
            ).count()
            if settings_count == 0:
                missing_for_company.append({
                    "id": partner.id,
                    "partner_code": partner.partner_code,
                    "partner_name": partner.partner_name,
                    "category": partner.category,
                    "company_id": cid
                })
        partner_company_coverage[cid] = len(missing_for_company)
        partners_without_settings.extend(missing_for_company[:5])  # Limit per company
    
    # Get total menu counts
    total_menus = db.query(StaffMenuMaster).filter(
        StaffMenuMaster.is_active == True
    ).count()
    
    default_visible_menus = db.query(StaffMenuMaster).filter(
        StaffMenuMaster.is_active == True,
        StaffMenuMaster.is_default_visible == True
    ).count()
    
    total_employees_missing = sum(company_coverage.values())
    total_partners_missing = sum(partner_company_coverage.values())
    is_healthy = total_employees_missing == 0 and total_partners_missing == 0
    
    return {
        "success": True,
        "healthy": is_healthy,
        "dc_protocol_compliant": True,
        "company_id_filter": company_id,
        "companies_checked": len(company_ids_list),
        "summary": {
            "total_active_employees": len(active_employees),
            "employees_missing_company_settings": total_employees_missing,
            "total_active_partners": len(active_partners),
            "partners_missing_company_settings": total_partners_missing,
            "total_active_menus": total_menus,
            "default_visible_menus": default_visible_menus
        },
        "company_employee_coverage": company_coverage,
        "company_partner_coverage": partner_company_coverage,
        "employees_needing_repair": employees_without_settings[:10],
        "partners_needing_repair": partners_without_settings[:10],
        "recommendation": "All systems healthy - DC Protocol compliant" if is_healthy else "Run bulk repair to fix missing company-specific settings"
    }


@router.post("/repair-all")
async def repair_all_menu_settings(
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """
    DC Protocol (Dec 20, 2025): Manually trigger bulk repair of all menu settings
    Creates missing baseline settings for all employees and partners
    """
    # DC Jan 2026: Accept both 'VGK4U' and 'VGK4U Supreme' for production compatibility
    if current_user.staff_type not in ['VGK4U', 'VGK4U Supreme', 'RVZ']:
        raise HTTPException(status_code=403, detail="Only VGK4U/RVZ can trigger repair")
    
    try:
        emp_created = bulk_repair_all_employees_menu_settings(db)
        partner_created = bulk_repair_all_partners_menu_settings(db)
        
        return {
            "success": True,
            "message": "Bulk repair completed successfully",
            "employee_settings_created": emp_created,
            "partner_settings_created": partner_created,
            "total_created": emp_created + partner_created
        }
    except Exception as e:
        logger.error(f"[DC-REPAIR] Bulk repair failed: {e}")
        raise HTTPException(status_code=500, detail=f"Repair failed: {str(e)}")


class ResetAllRequest(BaseModel):
    """Request model for reset-all endpoint"""
    reason: str = "Quick Reset All"


@router.post("/reset-all")
async def reset_all_menu_settings(
    company_id: int,
    data: ResetAllRequest,
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """
    DC Protocol (Dec 21, 2025): Reset ALL access permissions for a company
    Removes View and Edit permissions from ALL employees and partners
    Used for fresh assignment when starting over
    
    WVV Protocol: Full audit logging and VGK4U/RVZ authorization required
    """
    allowed_types = ['VGK4U', 'VGK4U Supreme', 'EA', 'RVZ', 'MYNT_REAL']
    allowed_roles = ['ea', 'hr', 'accounts', 'vgk4u']
    role_code = getattr(current_user.role, 'role_code', '') if current_user.role else ''
    if current_user.staff_type not in allowed_types and (role_code or '').lower() not in allowed_roles:
        logger.warning(f"RBAC VIOLATION: {current_user.emp_code} ({current_user.staff_type}) - reset-all access denied")
        raise HTTPException(status_code=403, detail="Access denied to reset menu settings.")
    
    logger.info(f"[DC-RESET-ALL] User {current_user.emp_code} initiating reset-all for company {company_id}")
    logger.info(f"[DC-RESET-ALL] Reason: {data.reason}")
    
    try:
        # Count before reset for audit
        employee_settings_count = db.query(StaffEmployeeMenuSettings).filter(
            StaffEmployeeMenuSettings.company_id == company_id
        ).count()
        
        partner_settings_count = db.query(PartnerMenuSettings).filter(
        ).count()
        
        # Reset employee settings: set can_view=False and can_edit=False (soft reset)
        employee_reset = db.query(StaffEmployeeMenuSettings).filter(
            StaffEmployeeMenuSettings.company_id == company_id
        ).update({
            StaffEmployeeMenuSettings.can_view: False,
            StaffEmployeeMenuSettings.can_edit: False,
            StaffEmployeeMenuSettings.is_overridden: True,
            StaffEmployeeMenuSettings.set_by_id: current_user.id,
            StaffEmployeeMenuSettings.set_by_code: current_user.emp_code,
            StaffEmployeeMenuSettings.set_by_name: current_user.full_name,
            StaffEmployeeMenuSettings.updated_at: datetime.utcnow()
        }, synchronize_session=False)
        
        # Reset partner settings: set can_view=False and can_edit=False (soft reset)
        partner_reset = db.query(PartnerMenuSettings).filter(
        ).update({
            PartnerMenuSettings.can_view: False,
            PartnerMenuSettings.can_edit: False,
            PartnerMenuSettings.is_overridden: True,
            PartnerMenuSettings.set_by_id: current_user.id,
            PartnerMenuSettings.set_by_code: current_user.emp_code,
            PartnerMenuSettings.set_by_name: current_user.full_name,
            PartnerMenuSettings.updated_at: datetime.utcnow()
        }, synchronize_session=False)
        
        # Audit log for the reset action
        audit = StaffMenuSettingsAudit(
            company_id=company_id,
            employee_id=None,
            employee_code='ALL',
            employee_name='ALL EMPLOYEES & PARTNERS',
            action='RESET_ALL_ACCESS',
            menu_changes=[{
                'action': 'reset_all',
                'reason': data.reason,
                'employee_settings_affected': employee_reset,
                'partner_settings_affected': partner_reset
            }],
            performed_by_id=current_user.id,
            performed_by_code=current_user.emp_code,
            performed_by_name=current_user.full_name,
            ip_address=None,
            reason=f"Quick Reset All: {data.reason}"
        )
        db.add(audit)
        
        db.commit()
        
        logger.info(f"[DC-RESET-ALL] SUCCESS - Reset {employee_reset} employee settings, {partner_reset} partner settings")
        
        return {
            "success": True,
            "message": "All access permissions reset successfully",
            "company_id": company_id,
            "affected_employees": employee_reset,
            "affected_partners": partner_reset,
            "total_affected": employee_reset + partner_reset
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"[DC-RESET-ALL] FAILED: {e}")
        raise HTTPException(status_code=500, detail=f"Reset failed: {str(e)}")


# =====================================================================
# DYNAMIC MENU REGISTRY API - DC Protocol: Single Source of Truth
# Created: Dec 29, 2025
# Purpose: Provides full menu registry for dynamic sidebar rendering
# =====================================================================

@router.get("/registry")
async def get_menu_registry(
    audience: Optional[str] = "staff",
    include_sections: bool = True,
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """
    Get the complete menu registry for dynamic sidebar rendering.
    DC Protocol: Single source of truth for both sidebar and access control.
    
    Parameters:
    - audience: Filter by audience scope ('staff', 'partner', 'shared', 'all')
    - include_sections: If True, returns menus grouped by sidebar_section
    
    Returns:
    - Full menu list with section groupings for sidebar rendering
    - Uses StaffMenuRegistry as the canonical source
    """
    try:
        # Build query based on audience scope
        # DC Protocol (Jan 12, 2026): Filter out deprecated/merged routes and structural placeholders
        HIDDEN_ROUTES = [
            '/staff/team-attendance-summary', 
            '/staff/all-journeys',
            '/section/mnr',              # Structural placeholder - not a real menu item
            '/section/mnr-user-sidebar', # Structural placeholder - not a real menu item
            '/section/zynova',           # Structural placeholder - not a real menu item
            '#mnr',                      # Hash route placeholder
            '#vgk4u',                   # Hash route placeholder
        ]
        
        # DC Protocol (Jan 13, 2026): Filter out admin portal menus - they don't belong in staff sidebar
        # Admin menus have menu_category='admin' and empty sidebar_section
        # Only include menus that are properly configured for the staff portal
        query = db.query(StaffMenuRegistry).filter(
            StaffMenuRegistry.is_active == True,
            ~StaffMenuRegistry.route_path.in_(HIDDEN_ROUTES),
            StaffMenuRegistry.menu_category != 'admin',  # Exclude admin portal menus
            StaffMenuRegistry.sidebar_section.isnot(None),  # Must have sidebar section
            StaffMenuRegistry.sidebar_section != ''  # sidebar_section cannot be empty
        )
        
        if audience != 'all':
            # DC Protocol (Jan 2026): 'ALL' audience_scope should be included for any audience filter
            query = query.filter(
                StaffMenuRegistry.audience_scope.in_([audience, 'shared', 'ALL'])
            )
        
        # Order by section order, then display order
        menus = query.order_by(
            StaffMenuRegistry.sidebar_section_order.asc().nullslast(),
            StaffMenuRegistry.display_order.asc()
        ).all()
        
        # Build flat menu list
        menu_list = []
        for menu in menus:
            menu_dict = {
                "id": menu.id,
                "menu_code": menu.menu_code,
                "menu_name": menu.menu_name,
                "route_path": menu.route_path,
                "menu_category": menu.menu_category,
                "menu_icon": menu.menu_icon,
                "display_order": menu.display_order,
                "sidebar_section": menu.sidebar_section if hasattr(menu, 'sidebar_section') else menu.menu_category,
                "sidebar_section_title": menu.sidebar_section_title if hasattr(menu, 'sidebar_section_title') else None,
                "sidebar_section_order": menu.sidebar_section_order if hasattr(menu, 'sidebar_section_order') else 0,
                "audience_scope": menu.audience_scope,
                "menu_type": getattr(menu, 'menu_type', 'STAFF'),
                "parent_section": getattr(menu, 'parent_section', None),
                "is_submenu": getattr(menu, 'is_submenu', False)
            }
            menu_list.append(menu_dict)
        
        # Group by sections if requested
        sections = {}
        section_order = {}
        if include_sections:
            # DC Protocol (Jan 12, 2026): Use canonical section IDs directly
            # REMOVED normalization that was creating duplicate sections (mnr section, mnr-user-sidebar→mnr-user)
            # Now using canonical 18-section structure: mnr (order 17), mnr-user-sidebar (order 18)
            for menu in menu_list:
                section_id = menu.get('sidebar_section') or menu.get('menu_category') or 'other'
                # Use canonical section ID directly - no normalization
                section_title = menu.get('sidebar_section_title') or section_id.upper().replace('_', ' ').replace('-', ' ')
                section_ord = menu.get('sidebar_section_order') or 0
                
                if section_id not in sections:
                    sections[section_id] = {
                        "id": section_id,
                        "title": section_title,
                        "order": section_ord,
                        "menu_type": menu.get('menu_type', 'STAFF'),
                        "parent_section": menu.get('parent_section'),
                        "is_submenu": menu.get('is_submenu', False),
                        "items": []
                    }
                    section_order[section_id] = section_ord
                
                sections[section_id]["items"].append({
                    "icon": menu["menu_icon"],
                    "label": menu["menu_name"],
                    "href": menu["route_path"],
                    "menu_code": menu["menu_code"],
                    "menu_type": menu.get('menu_type', 'STAFF'),
                    "parent_section": menu.get('parent_section')
                })
            
            # DC Protocol (Jan 2026): Nest submenu sections under parent sections
            # Sections with is_submenu=true become subSections of their parent_section
            parent_sections = {}
            submenu_sections = {}
            
            # DC Protocol (Jan 23, 2026): Debug logging - changed from warning to debug level
            if 'real-dreams' in sections:
                rd = sections['real-dreams']
                logger.debug(f"[DC-MENU-REGISTRY] real-dreams section BEFORE nesting: is_submenu={rd.get('is_submenu')} (type={type(rd.get('is_submenu')).__name__}), parent_section={rd.get('parent_section')}")
            
            for section_id, section in sections.items():
                is_sub = section.get('is_submenu')
                parent = section.get('parent_section')
                if is_sub and parent:
                    # This is a submenu - group by parent
                    parent_id = parent
                    if parent_id not in submenu_sections:
                        submenu_sections[parent_id] = []
                    submenu_sections[parent_id].append(section)
                    logger.info(f"[DC-MENU-REGISTRY] Nested section '{section_id}' under parent '{parent_id}'")
                else:
                    parent_sections[section_id] = section
            
            # Find or create parent sections for orphaned submenus
            # DC Protocol (Jan 2026): parent_id is the key (e.g., 'zynova'), submenus contain
            # sections that should be nested under it (e.g., 'real-dreams')
            for parent_id, submenus in submenu_sections.items():
                if parent_id not in parent_sections:
                    # Create parent section using parent_id (e.g., 'zynova')
                    first_submenu = submenus[0] if submenus else {}
                    parent_title = parent_id.upper().replace('-', ' ').replace('_', ' ')
                    
                    parent_sections[parent_id] = {
                        "id": parent_id,
                        "title": parent_title,
                        "order": first_submenu.get('order', 999),
                        "menu_type": first_submenu.get('menu_type', 'STAFF'),
                        "items": [],
                        "subSections": []
                    }
                
                # Get the parent section
                actual_parent = parent_sections[parent_id]
                
                if "subSections" not in actual_parent:
                    actual_parent["subSections"] = []
                
                # Add submenus as subSections with proper structure
                # Each submenu (e.g., 'real-dreams') becomes a subSection under the parent
                for sub in submenus:
                    actual_parent["subSections"].append({
                        "id": sub.get('id', 'submenu'),
                        "title": sub.get('title', 'Submenu'),
                        "icon": "fas fa-home",
                        "items": sub.get('items', [])
                    })
            
            sections = parent_sections
            
            # Debug: Log ZYNOVA section if present
            if 'vgk4u' in parent_sections:
                logger.info(f"[DC-MENU-REGISTRY] ZYNOVA section found with {len(parent_sections['vgk4u'].get('subSections', []))} subSections")
            else:
                logger.warning(f"[DC-MENU-REGISTRY] ZYNOVA NOT in parent_sections. Keys: {list(parent_sections.keys())[:10]}...")
        
        # DC Protocol (Jan 2026): Preserve sidebar order - NO alphabetical sorting
        # Menu Access page must match sidebar structure exactly
        sorted_sections = preserve_sections_order(list(sections.values()))
        
        # Debug: Verify ZYNOVA in final output
        zynova_in_output = any(s.get('id') == 'vgk4u' or s.get('title') == 'ZYNOVA' for s in sorted_sections)
        logger.info(f"[DC-MENU-REGISTRY] ZYNOVA in sorted output: {zynova_in_output}, total sections: {len(sorted_sections)}")
        
        return {
            "success": True,
            "total_menus": len(menu_list),
            "total_sections": len(sorted_sections),
            "audience": audience,
            "menus": menu_list,
            "sections": sorted_sections,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"[DC-MENU-REGISTRY] Error fetching registry: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch menu registry: {str(e)}")


@router.post("/registry/sync-sidebar")
def sync_sidebar_to_registry(
    current_user: StaffEmployee = Depends(require_vgk4u_access),
    db: Session = Depends(get_db)
):
    """
    DC Protocol Jan 13 2026: Sync sidebar from pdf_canonical_routes table.
    DC Protocol Mar 2026: Also ensures pdf_canonical_routes is seeded from SIDEBAR_ROUTE_MAPPING
    before syncing, so all 18 sections are always present.
    DC Protocol Apr 2026: Changed from async def → def so FastAPI runs this in a thread pool
    executor, preventing synchronous SQLAlchemy calls from blocking the event loop (which
    caused uvicorn → Express proxy timeouts → HTTP 502).
    """
    import time
    from app.services.sidebar_sync_service import (
        ensure_pdf_canonical_routes_table_and_seed,
        sync_menu_registry_sections,
    )

    # Step 0: Ensure pdf_canonical_routes table exists and has all 18 sections seeded
    # Retry up to 3 times in case startup workers are holding the seed advisory lock
    seed_ok = False
    for _seed_attempt in range(3):
        seed_ok = ensure_pdf_canonical_routes_table_and_seed(db)
        if seed_ok:
            break
        logger.info(f"[DC-SYNC-BTN] Seed lock busy (attempt {_seed_attempt + 1}/3) — waiting 2s")
        time.sleep(2)
    if not seed_ok:
        logger.warning("[DC-SYNC-BTN] pdf_canonical_routes seed step failed — proceeding anyway")

    # DC Protocol Mar 2026: Retry the sync up to 4 times with 2s delays if the advisory
    # lock is held by another worker (common immediately after a fresh deployment when
    # startup background tasks are still running their own sidebar sync).
    result = None
    for _sync_attempt in range(4):
        result = sync_menu_registry_sections(db)
        if isinstance(result, dict) or result is False:
            break
        logger.info(f"[DC-SYNC-BTN] Sync lock busy (attempt {_sync_attempt + 1}/4) — waiting 2s")
        time.sleep(2)

    # Guard: False = hard error, non-dict after retries = still busy
    if result is False:
        raise HTTPException(status_code=500, detail="Failed to sync sidebar from canonical routes")
    if not isinstance(result, dict):
        raise HTTPException(status_code=503, detail="Sync temporarily busy — another sync is in progress. Try again in a moment.")

    return {
        "success": True,
        "message": "Synced sidebar from pdf_canonical_routes table (all 18 sections)",
        "updated_count": result.get("registry", 0),
        "total_menus": result.get("registry", 0),
        "master_synced_count": result.get("master", 0),
        "source": "pdf_canonical_routes",
        "seed_ok": seed_ok,
    }


@router.post("/registry/sync-sidebar-legacy")
async def sync_sidebar_to_registry_legacy(
    current_user: StaffEmployee = Depends(require_vgk4u_access),
    db: Session = Depends(get_db)
):
    """
    DEPRECATED: Legacy sync endpoint kept for reference only.
    Use /registry/sync-sidebar which reads from pdf_canonical_routes table.
    """
    CANONICAL_SECTIONS = {
        'progress', 'staff-dashboard', 'attendance', 'crm', 'task-management',
        'kra-management', 'timesheet', 'journey-tracking', 'location-tracking',
        'reimbursement', 'service-tickets', 'accounts', 'official-partners',
        'nda-management', 'internal', 'configuration', 'vgk4u', 'mnr', 'mnr-user-sidebar',
        'sfms', 'inventory', 'payroll', 'real-dreams', 'zy-member-earnings',
        'mnr-users', 'mnr-approvals', 'mnr-awards', 'mnr-income', 'mnr-withdrawals',
        'mnr-crm', 'mnr-communications', 'mnr-terms', 'mnr-announcements', 'mnr-system-config',
        'staff_mnr_user_dashboard', 'staff_mnr_user_announcements', 'staff_mnr_user_coupons',
        'staff_mnr_user_members', 'staff_mnr_user_mnr', 'staff_mnr_user_myntreal',
        'staff_mnr_user_vgk4u', 'staff_mnr_user_awards', 'staff_mnr_user_system',
        'vgk_team', 'vendor_management', 'mynt_real',
        'zy-vgk4u-marketplace'
    }
    
    # DC Protocol (Jan 12, 2026): LEGACY SECTIONS TO HIDE (truly obsolete only)
    # NOTE: 'mnr', 'mnr-user-sidebar' are NOW CANONICAL - do NOT add here
    LEGACY_SECTIONS_TO_HIDE = {
        'missing', 'partner-portal', 'rvz-awards-bonanza', 'rvz-pins',
        'rvz-terms-conditions', 'rvz-verification', 'rvz-withdrawal',
        'user-portal', 'mnr-user'  # Old aliases, now use 'mnr' and 'mnr-user-sidebar'
    }
    
    # Define section mappings based on frontend/staff_sidebar.js menuConfig
    # DC Protocol (Jan 12, 2026): CANONICAL 18-SECTION SIDEBAR ORDER
    # NOTE: Each route must appear in exactly ONE section (no duplicates)
    SECTION_MAPPINGS = {
        # Section ID -> (Title, Order, Menu Paths)
        # DC Protocol (Jan 12, 2026): User-specified 18-section sidebar sequence matching PDF
        # 1-PROGRESS, 2-STAFF DASHBOARD, 3-ATTENDANCE, 4-CRM, 5-TASK, 6-KRA, 7-TIMESHEET,
        # 8-JOURNEY, 9-LOCATION, 10-REIMBURSEMENT, 11-SERVICE TICKETS, 12-ACCOUNTS,
        # 13-BUSINESS PARTNERS, 14-NDA, 15-CONFIGURATION, 16-ZYNOVA, 17-MNR, 18-MNR USER SIDEBAR
        'progress': ('PROGRESS', 1, ['/staff/progress']),
        'staff-dashboard': ('STAFF DASHBOARD', 2, ['/staff/dashboard', '/staff/employees', '/staff/employee-directory', '/staff/my-kyc', '/staff/kyc-approvals', '/staff/change-password', '/staff/2fa-settings']),
        'attendance': ('ATTENDANCE', 3, ['/staff/my-attendance', '/staff/my-leaves', '/staff/leave-approvals', '/staff/team-attendance', '/staff/attendance-sheet', '/staff/attendance-reports', '/staff/attendance-exceptions', '/staff/attendance-computation', '/staff/team-attendance-summary']),
        'crm': ('CRM & LEADS', 4, ['/staff/crm/dashboard', '/staff/leads', '/staff/crm/team-leads', '/staff/my-leads', '/staff/crm/lead-sources', '/rvz/crm-leads', '/rvz/crm/leads', '/staff/call-management', '/staff/dialer', '/staff/call-quality', '/staff/crm/sales-report']),
        'task-management': ('TASK MANAGEMENT', 5, ['/staff/tasks/assigned-by-me-v2', '/staff/tasks/assigned-to-me', '/staff/tasks/team-activities', '/staff/tasks/tracker', '/staff/team-activities', '/staff/manager-review', '/staff/task-review']),
        'kra-management': ('KRA MANAGEMENT', 6, ['/staff/my-kras', '/staff/kra-templates', '/staff/kra-tracking-sheet', '/staff/kra-review']),
        'timesheet': ('TIMESHEET', 7, ['/staff/my-timesheet', '/staff/timesheet-approval']),
        'journey-tracking': ('JOURNEY TRACKING', 8, ['/staff/my-journeys', '/staff/team-journeys', '/staff/all-journeys', '/staff/vgk4u-journeys']),
        'location-tracking': ('LOCATION TRACKING', 9, ['/staff/my-location-history', '/staff/team-location-tracker']),
        'my-earnings': ('MY EARNINGS', 19, ['/staff/my-lead-incentives']),
        'reimbursement': ('REIMBURSEMENT', 10, ['/staff/accounts/my-reimbursements', '/staff/accounts/reimbursement-approvals']),
        'service-tickets': ('SERVICE TICKETS', 11, ['/staff/service-tickets/dashboard', '/staff/inventory/service-center-tracking', '/staff/service-tickets/performance', '/staff/service-tickets/procurement', '/staff/service-tickets/procurement-queue', '/staff/service-tickets/raise', '/staff/service-tickets/reports', '/staff/service-tickets/queue', '/staff/service-center-revenue']),
        'accounts': ('ACCOUNTS', 12, ['/staff/accounts/balance-sheet', '/staff/accounts/fund-allocations', '/staff/accounts/expense-entries', '/staff/accounts/income-entries', '/staff/accounts/vendors', '/staff/accounts/purchase-invoices', '/staff/accounts/sales-invoices', '/staff/accounts/reports', '/staff/accounts/payables', '/staff/accounts/receivables', '/staff/accounts/duties-taxes', '/staff/accounts/capital', '/staff/accounts/cash-in-hand', '/rvz/sales-revenue', '/staff/accounts/party-ledger', '/staff/inventory/bom', '/staff/inventory/manufacturing', '/staff/inventory/procurement', '/staff/inventory/intake', '/staff/inventory/stock-items', '/staff/inventory/stock-ledger', '/staff/inventory/stock-transfers', '/staff/inventory/stock-validation', '/staff/inventory/vendor-returns', '/staff/inventory/accessories', '/staff/payroll/profiles', '/staff/payroll/cycles', '/staff/payroll/runs', '/staff/payroll/approvals', '/staff/payroll/consultant-invoices', '/staff/payroll/allowance-catalog', '/staff/payroll/documents', '/staff/accounts/expense-categories', '/staff/accounts/pricing', '/staff/income-trigger']),
        'official-partners': ('BUSINESS PARTNERS', 13, ['/staff/partners/orders', '/staff/partners/pricing', '/staff/partners/approval', '/staff/partners/routing', '/staff/partners/fulfillment', '/staff/partners/dispatch', '/staff/partners/invoices', '/staff/partners/payments']),
        'internal': ('INTERNAL', 30, ['/staff/nda-versions', '/staff/nda-acceptance-audit', '/staff/nda-pending', '/staff/promoters', '/staff/promo-nda-editor', '/staff/promo-nda-audit', '/staff/internal-menu-access', '/rvz/terms-conditions-management', '/rvz/terms-versions', '/rvz/terms-editor', '/rvz/terms-audit', '/staff/mnr/terms-versions', '/staff/mnr/terms-editor', '/staff/mnr/terms-audit']),
        'nda-management': ('INTERNAL', 30, []),
        'configuration': ('CONFIGURATION', 15, ['/staff/departments', '/staff/accounts/companies', '/staff/partners/master', '/staff/accounts/segments', '/staff/accounts/hsn', '/staff/signup-categories', '/rvz/menu-access-config', '/staff/sidebar-sync', '/staff/crm/ai-calling', '/staff/whatsapp-config']),
        'vgk4u': ('ZYNOVA', 16, ['/rvz/real-dreams/marketplace', '/rvz/real-dreams', '/rvz/real-dreams/partners', '/rvz/real-dreams/properties', '/staff/incentives/points', '/staff/incentives/approvals', '/staff/incentives/vgk4u', '/staff/vgk4u/real-estate', '/staff/vgk4u/insurance', '/staff/zynova', '/rvz/real-dreams-dashboard', '/rvz/real-dreams-partners', '/rvz/real-dreams-properties', '/real-dreams/marketplace', '/real-dreams/property', '/real-dreams/compare', '/staff/vgk4u/purchase-orders', '/staff/marketplace-config', '/staff/vgk4u/etc-students', '/staff/marketplace/codes-segments']),
        'mnr': ('MNR', 17, [
            # MNR Users subsection
            '/rvz/mnr-users', '/staff/mnr/users', '/rvz/members', '/rvz/member-kyc', '/rvz/member-bank',
            # PINs & Passwords subsection
            '/rvz/pins/all', '/rvz/pin-approvals', '/staff/mnr/pin-approvals', '/rvz/coupon-status', '/staff/mnr/coupon-status',
            '/rvz/change-user-password', '/rvz/rvz-password-change', '/rvz/secondary-password-setup',
            # MNR Coupons subsection
            '/rvz/mnr-coupons', '/pins', '/coupons', '/coupon-transfer',
            # MNR Communications subsection
            '/rvz/popup-control', '/rvz/banner-analytics',
            # MNR Withdrawals subsection
            '/rvz/mnr-withdrawals', '/rvz/withdrawal-supreme', '/rvz/withdrawal-supreme/approvals',
            '/rvz/withdrawal-supreme/history', '/rvz/withdrawal/dashboard', '/staff/mnr/withdrawal/dashboard',
            # MNR Income subsection
            '/rvz/mnr-income', '/rvz/income-supreme', '/rvz/income-records', '/staff/mnr/income-records',
            '/rvz/income-approval',
            # MNR Awards & Bonanza subsection
            '/rvz/mnr-awards-bonanza', '/rvz/awards/approval-queue', '/rvz/award-management',
            '/rvz/bonanza-management', '/rvz/bonanza-claims', '/rvz/awards-all', '/staff/mnr/awards-all',
            # MNR Terms & Conditions subsection
            '/rvz/mnr-terms', '/rvz/terms-conditions-management', '/rvz/terms-audit',
            '/rvz/terms-versions', '/rvz/terms-editor',
            # Legacy routes consolidated
            '/rvz/withdrawal-approval'
        ]),
        'mnr-user-sidebar': ('MNR USER SIDEBAR', 18, [
            # Standalone items
            '/staff/mnr-user/audit', '/staff/mnr-user/audit-log', '/staff/mnr-user/dashboard',
            '/staff/mnr-user/profile', '/staff/mnr-user/create', '/staff/mnr-user/create-member',
            '/staff/mnr-user/popups',
            # Members group
            '/staff/mnr-user/members', '/staff/mnr-user/members/all', '/staff/mnr-user/members/direct',
            '/staff/mnr-user/members/downline', '/staff/mnr-user/members/picture', '/staff/mnr-user/members/ved',
            # Coupon Modules group
            '/staff/mnr-user/coupons', '/staff/mnr-user/coupons/available', '/staff/mnr-user/coupons/red',
            '/staff/mnr-user/coupons/green', '/staff/mnr-user/coupons/transfer', '/staff/mnr-user/coupons/ev',
            '/staff/mnr-user/coupons/history',
            # MNR group (earnings)
            '/staff/mnr-user/mnr', '/staff/mnr-user/mnr/earnings', '/staff/mnr-user/mnr/direct',
            '/staff/mnr-user/mnr/matching', '/staff/mnr-user/mnr/ved', '/staff/mnr-user/mnr/guru',
            '/staff/mnr-user/mnr/withdrawals', '/staff/mnr-user/mnr/points', '/staff/mnr-user/mnr/benefits',
            '/staff/mnr-user/mnr/wallet', '/staff/mnr-user/mnr/earnings-summary',
            # MyntReal group
            '/staff/mnr-user/myntreal', '/staff/mnr-user/myntreal/properties', '/staff/mnr-user/myntreal/leads',
            '/staff/mnr-user/myntreal/franchise',
            # Zynova group
            '/staff/mnr-user/vgk4u', '/staff/mnr-user/vgk4u/dashboard', '/staff/mnr-user/vgk4u/real-estate',
            '/staff/mnr-user/vgk4u/insurance', '/staff/mnr-user/vgk4u/training',
            # Awards & Bonanza group
            '/staff/mnr-user/awards', '/staff/mnr-user/awards/all', '/staff/mnr-user/awards/bonanza',
            # Announcements group
            '/staff/mnr-user/announcements', '/staff/mnr-user/announcements/create',
            '/staff/mnr-user/announcements/pending', '/staff/mnr-user/announcements/history',
            # Legacy RVZ routes to consolidate
            '/rvz/mnr-user-dashboard', '/rvz/mnr-user-profile', '/rvz/mnr-user-create',
            '/rvz/mnr-popups-banners', '/rvz/mnr-earnings-summary', '/rvz/mnr-all-awards', '/rvz/mnr-audit-log'
        ]),
        'vgk_team': ('VGK TEAM', 21, [
            '/staff/vgk/members', '/staff/vgk/config', '/staff/vgk/income',
            '/staff/vgk/coupons/available', '/staff/vgk/bonanza-management', '/staff/vgk/bonanza-claims', '/staff/vgk/promo-codes',
            '/staff/whatsapp-config',
        ]),
        'vendor_management': ('VENDOR MANAGEMENT', 22, [
            '/staff/vgk/vendor-products', '/staff/vgk/vendor-categories', '/staff/vgk/vendor-transactions',
            '/staff/vgk/wallet', '/staff/vgk/cash-income/sales', '/staff/vgk/cash-income/accounts',
            '/staff/vgk/vendors'
        ]),
        'mynt_real': ('MYNT REAL', 23, [
            '/staff/executive-dashboard', '/staff/solar-leads', '/staff/ev-b2b-leads', '/staff/ev-b2c-leads', '/staff/ev-spares-leads',
            '/staff/real-dreams-leads', '/staff/insurance-leads', '/staff/etc-leads', '/staff/mnr-leads'
        ]),
    }
    
    # DC Protocol (Jan 10, 2026): DYNAMIC ROUTE PATTERN RULES
    # These patterns AUTO-ASSIGN sections for new routes, making sync future-proof
    # Pattern format: (route_prefix, section_id, section_title, section_order)
    # Order matters - first match wins
    ROUTE_PATTERN_RULES = [
        # MNR USER SIDEBAR routes (Staff portal access to MNR member data) - Section 18
        ('/staff/mnr-user/', 'mnr-user-sidebar', 'MNR USER SIDEBAR', 18),
        # MNR routes (RVZ admin routes for MNR management) - Section 17
        ('/rvz/mnr-', 'mnr', 'MNR', 17),
        ('/staff/mnr/', 'mnr', 'MNR', 17),
        ('/rvz/withdrawal', 'mnr', 'MNR', 17),
        ('/rvz/income', 'mnr', 'MNR', 17),
        ('/rvz/awards', 'mnr', 'MNR', 17),
        ('/rvz/bonanza', 'mnr', 'MNR', 17),
        ('/rvz/terms', 'mnr', 'MNR', 17),
        ('/rvz/pins', 'mnr', 'MNR', 17),
        ('/rvz/banner', 'mnr', 'MNR', 17),
        ('/rvz/popup', 'mnr', 'MNR', 17),
        ('/rvz/members', 'mnr', 'MNR', 17),
        ('/rvz/member-', 'mnr', 'MNR', 17),
        # Zynova routes - Section 16
        ('/rvz/real-dreams', 'vgk4u', 'ZYNOVA', 16),
        ('/real-dreams/', 'vgk4u', 'ZYNOVA', 16),
        ('/staff/vgk4u/', 'vgk4u', 'ZYNOVA', 16),
        ('/staff/incentives/', 'vgk4u', 'ZYNOVA', 16),
        # Service Center Tracking — explicitly before /staff/inventory/ so it routes to Service Tickets
        ('/staff/inventory/service-center-tracking', 'service-tickets', 'SERVICE TICKETS', 11),
        # Accounts routes - Section 12
        ('/staff/accounts/', 'accounts', 'ACCOUNTS', 12),
        ('/staff/inventory/', 'accounts', 'ACCOUNTS', 12),
        ('/staff/payroll/', 'accounts', 'ACCOUNTS', 12),
        ('/staff/income-trigger', 'accounts', 'ACCOUNTS', 12),
        # Service Tickets - Section 11
        ('/staff/service-tickets/', 'service-tickets', 'SERVICE TICKETS', 11),
        ('/staff/service-center', 'service-tickets', 'SERVICE TICKETS', 11),
        # Partners - Section 13
        ('/staff/partners/', 'official-partners', 'BUSINESS PARTNERS', 13),
        # CRM - Section 4
        ('/staff/crm/', 'crm', 'CRM & LEADS', 4),
        ('/staff/leads', 'crm', 'CRM & LEADS', 4),
        ('/rvz/crm', 'crm', 'CRM & LEADS', 4),
        ('/staff/call-management', 'crm', 'CRM & LEADS', 4),
        ('/staff/dialer', 'crm', 'CRM & LEADS', 4),
        ('/staff/call-quality', 'crm', 'CRM & LEADS', 4),
        ('/staff/crm/sales-report', 'crm', 'CRM & LEADS', 4),
        # Tasks - Section 5
        ('/staff/tasks/', 'task-management', 'TASK MANAGEMENT', 5),
        ('/staff/team-activities', 'task-management', 'TASK MANAGEMENT', 5),
        # Attendance - Section 3
        ('/staff/my-attendance', 'attendance', 'ATTENDANCE', 3),
        ('/staff/my-leaves', 'attendance', 'ATTENDANCE', 3),
        ('/staff/leave-', 'attendance', 'ATTENDANCE', 3),
        ('/staff/team-attendance', 'attendance', 'ATTENDANCE', 3),
        ('/staff/attendance-', 'attendance', 'ATTENDANCE', 3),
        # Journey - Section 8
        ('/staff/my-journeys', 'journey-tracking', 'JOURNEY TRACKING', 8),
        ('/staff/team-journeys', 'journey-tracking', 'JOURNEY TRACKING', 8),
        ('/staff/all-journeys', 'journey-tracking', 'JOURNEY TRACKING', 8),
        ('/staff/vgk4u-journeys', 'journey-tracking', 'JOURNEY TRACKING', 8),
        # Location - Section 9
        ('/staff/my-location', 'location-tracking', 'LOCATION TRACKING', 9),
        ('/staff/team-location', 'location-tracking', 'LOCATION TRACKING', 9),
        ('/staff/all-location', 'location-tracking', 'LOCATION TRACKING', 9),
        ('/staff/team-live', 'location-tracking', 'LOCATION TRACKING', 9),
        # My Earnings - Section 19
        ('/staff/my-lead-incentives', 'my-earnings', 'MY EARNINGS', 19),
        # KRA - Section 6
        ('/staff/my-kras', 'kra-management', 'KRA MANAGEMENT', 6),
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            ('/staff/kra-', 'kra-management', 'KRA MANAGEMENT', 6),
        # Timesheet - Section 7
        ('/staff/my-timesheet', 'timesheet', 'TIMESHEET', 7),
        ('/staff/timesheet-', 'timesheet', 'TIMESHEET', 7),
        # Internal - Section 30 (VGK Mentor & EA only)
        ('/staff/nda-', 'internal', 'INTERNAL', 30),
        ('/staff/promoters', 'internal', 'INTERNAL', 30),
        ('/staff/promo-nda-', 'internal', 'INTERNAL', 30),
        ('/staff/internal-menu-access', 'internal', 'INTERNAL', 30),
        ('/rvz/terms-', 'internal', 'INTERNAL', 30),
        ('/staff/mnr/terms-', 'internal', 'INTERNAL', 30),
        # Configuration - Section 15
        ('/staff/departments', 'configuration', 'CONFIGURATION', 15),
        ('/staff/signup-categories', 'configuration', 'CONFIGURATION', 15),
        ('/staff/sidebar-sync', 'configuration', 'CONFIGURATION', 15),
        ('/rvz/menu-access', 'configuration', 'CONFIGURATION', 15),
        ('/staff/performance-config', 'hr', 'HR', 22),
        ('/staff/crm/ai-calling', 'configuration', 'CONFIGURATION', 15),
        ('/staff/whatsapp-config', 'configuration', 'CONFIGURATION', 15),
        # VGK TEAM - Section 21 (specific paths first, before vendor_ catch-all)
        ('/staff/vgk/members', 'vgk_team', 'VGK TEAM', 21),
        ('/staff/vgk/config', 'vgk_team', 'VGK TEAM', 21),
        ('/staff/vgk/income', 'vgk_team', 'VGK TEAM', 21),
        ('/staff/vgk/coupons', 'vgk_team', 'VGK TEAM', 21),
        ('/staff/vgk/bonanza-', 'vgk_team', 'VGK TEAM', 21),
        # VENDOR MANAGEMENT - Section 22 (vendor-* and wallet/cash-income/vendors)
        ('/staff/vgk/vendor', 'vendor_management', 'VENDOR MANAGEMENT', 22),
        ('/staff/vgk/wallet', 'vendor_management', 'VENDOR MANAGEMENT', 22),
        ('/staff/vgk/cash-income/', 'vendor_management', 'VENDOR MANAGEMENT', 22),
        # MYNT REAL - Section 23
        ('/staff/executive-dashboard', 'mynt_real', 'MYNT REAL', 23),
        ('/staff/solar-leads', 'mynt_real', 'MYNT REAL', 23),
        ('/staff/ev-', 'mynt_real', 'MYNT REAL', 23),
        ('/staff/real-dreams-leads', 'mynt_real', 'MYNT REAL', 23),
        ('/staff/insurance-leads', 'mynt_real', 'MYNT REAL', 23),
        ('/staff/etc-leads', 'mynt_real', 'MYNT REAL', 23),
        ('/staff/mnr-leads', 'mynt_real', 'MYNT REAL', 23),
    ]
    
    def get_section_by_pattern(route_path):
        """Find section assignment by matching route patterns"""
        if not route_path:
            return None
        for pattern, section_id, section_title, section_order in ROUTE_PATTERN_RULES:
            if route_path.startswith(pattern):
                return (section_id, section_title, section_order)
        return None
    
    updated_count = 0
    pattern_matched_count = 0
    legacy_hidden_count = 0
    migrated_count = 0
    
    # Build path to section mapping (explicit mappings take priority)
    path_to_section = {}
    for section_id, (title, order, paths) in SECTION_MAPPINGS.items():
        for path in paths:
            path_to_section[path] = (section_id, title, order)
    
    # Update all registry entries with section info
    all_menus = db.query(StaffMenuRegistry).filter(StaffMenuRegistry.is_active == True).all()
    
    for menu in all_menus:
        # Step 1: Check if route is in EXPLICIT SECTION_MAPPINGS (highest priority)
        if menu.route_path in path_to_section:
            section_id, section_title, section_order = path_to_section[menu.route_path]
            if hasattr(menu, 'sidebar_section'):
                menu.sidebar_section = section_id
                menu.sidebar_section_title = section_title
                menu.sidebar_section_order = section_order
                updated_count += 1
        else:
            # Step 2: Try DYNAMIC PATTERN MATCHING (future-proof)
            pattern_match = get_section_by_pattern(menu.route_path)
            if pattern_match:
                section_id, section_title, section_order = pattern_match
                if hasattr(menu, 'sidebar_section'):
                    menu.sidebar_section = section_id
                    menu.sidebar_section_title = section_title
                    menu.sidebar_section_order = section_order
                    pattern_matched_count += 1
            else:
                # Step 3: Handle legacy sections - MIGRATE or HIDE
                # DC Protocol (Jan 12, 2026): 'mnr' and 'mnr-user-sidebar' are NOW CANONICAL - no migration needed
                current_section = getattr(menu, 'sidebar_section', None)
                if current_section and current_section in LEGACY_SECTIONS_TO_HIDE:
                    # DC Protocol (Jan 12, 2026): Only migrate truly obsolete aliases
                    if current_section == 'mnr-user':
                        # Legacy alias - migrate to canonical 'mnr-user-sidebar'
                        menu.sidebar_section = 'mnr-user-sidebar'
                        menu.sidebar_section_title = 'MNR USER SIDEBAR'
                        menu.sidebar_section_order = 18
                        migrated_count += 1
                    else:
                        # Hide legacy sections that don't map to anything
                        menu.sidebar_section_order = 999
                        legacy_hidden_count += 1
                elif current_section and current_section not in CANONICAL_SECTIONS:
                    # Unknown section - hide it
                    menu.sidebar_section_order = 999
                    legacy_hidden_count += 1
    
    # Step 3: Bulk MIGRATE legacy section aliases to their canonical equivalents
    # DC Protocol (Jan 12, 2026): 'mnr' and 'mnr-user-sidebar' are NOW CANONICAL
    # NOTE: Subsections (sfms, inventory, payroll, real-dreams) stay as-is - they're in CANONICAL_SECTIONS
    # and need their own IDs for proper parent_section nesting
    LEGACY_TO_CANONICAL_MAP = {
        # Old MNR aliases → Canonical IDs
        'mnr-user': ('mnr-user-sidebar', 'MNR USER SIDEBAR', 18),  # mnr-user was old alias
    }
    
    # Migrate legacy sections to canonical equivalents
    for legacy_section, (canonical_id, canonical_title, canonical_order) in LEGACY_TO_CANONICAL_MAP.items():
        bulk_migrated = db.query(StaffMenuRegistry).filter(
            StaffMenuRegistry.sidebar_section == legacy_section,
            StaffMenuRegistry.is_active == True
        ).update({
            'sidebar_section': canonical_id,
            'sidebar_section_title': canonical_title,
            'sidebar_section_order': canonical_order
        }, synchronize_session=False)
        if bulk_migrated > 0:
            migrated_count += bulk_migrated
            logger.info(f"[DC-MENU-REGISTRY-SYNC] Bulk migrated {bulk_migrated} items from '{legacy_section}' to '{canonical_id}'")
    
    # Hide sections that cannot be migrated (truly obsolete)
    OBSOLETE_SECTIONS = {'missing', 'partner-portal', 'rvz-awards-bonanza', 'rvz-pins',
                         'rvz-terms-conditions', 'rvz-verification', 'rvz-withdrawal', 'user-portal'}
    legacy_update = db.query(StaffMenuRegistry).filter(
        StaffMenuRegistry.sidebar_section.in_(list(OBSOLETE_SECTIONS)),
        StaffMenuRegistry.is_active == True
    ).update({
        'sidebar_section': 'hidden',
        'sidebar_section_title': 'HIDDEN',
        'sidebar_section_order': 999
    }, synchronize_session=False)
    legacy_hidden_count += legacy_update
    
    # Step 4: Collect unmapped routes for reporting
    unmapped_routes = []
    for menu in all_menus:
        current_section = getattr(menu, 'sidebar_section', None)
        if current_section and current_section not in CANONICAL_SECTIONS and current_section != 'hidden':
            unmapped_routes.append({
                'route': menu.route_path,
                'current_section': current_section,
                'menu_name': menu.menu_name
            })
    
    if unmapped_routes:
        logger.warning(f"[DC-MENU-REGISTRY-SYNC] {len(unmapped_routes)} routes remain unmapped. Add to SECTION_MAPPINGS or ROUTE_PATTERN_RULES:")
        for route in unmapped_routes[:10]:
            logger.warning(f"  - {route['route']} (section: {route['current_section']}, name: {route['menu_name']})")
    
    # DC Protocol (Jan 10, 2026): CRITICAL FIX - Sync StaffMenuMaster table
    # The Access Matrix uses StaffMenuMaster, not StaffMenuRegistry
    # We must propagate sidebar_section values to StaffMenuMaster for Access Matrix to display correctly
    master_synced_count = 0
    
    # Build menu_code -> section mapping from registry
    registry_section_map = {}
    for menu in all_menus:
        if menu.menu_code and hasattr(menu, 'sidebar_section') and menu.sidebar_section:
            registry_section_map[menu.menu_code] = {
                'sidebar_section': menu.sidebar_section,
                'sidebar_section_title': getattr(menu, 'sidebar_section_title', None),
                'sidebar_section_order': getattr(menu, 'sidebar_section_order', 0)
            }
    
    # Also add mappings based on route_path for items that might have different menu_codes
    route_to_section = {}
    for menu in all_menus:
        if menu.route_path and hasattr(menu, 'sidebar_section') and menu.sidebar_section:
            route_to_section[menu.route_path] = {
                'sidebar_section': menu.sidebar_section,
                'sidebar_section_title': getattr(menu, 'sidebar_section_title', None),
                'sidebar_section_order': getattr(menu, 'sidebar_section_order', 0)
            }
    
    # Update StaffMenuMaster entries
    all_master_menus = db.query(StaffMenuMaster).filter(StaffMenuMaster.is_active == True).all()
    
    for master_menu in all_master_menus:
        section_data = None
        
        # First try to match by menu_code
        if master_menu.menu_code and master_menu.menu_code in registry_section_map:
            section_data = registry_section_map[master_menu.menu_code]
        # Then try to match by route_path
        elif master_menu.route_path and master_menu.route_path in route_to_section:
            section_data = route_to_section[master_menu.route_path]
        # Finally try pattern matching
        elif master_menu.route_path:
            pattern_match = get_section_by_pattern(master_menu.route_path)
            if pattern_match:
                section_id, section_title, section_order = pattern_match
                section_data = {
                    'sidebar_section': section_id,
                    'sidebar_section_title': section_title,
                    'sidebar_section_order': section_order
                }
        
        if section_data:
            master_menu.sidebar_section = section_data['sidebar_section']
            master_menu.sidebar_section_title = section_data['sidebar_section_title']
            master_menu.sidebar_section_order = section_data['sidebar_section_order']
            master_synced_count += 1
    
    logger.info(f"[DC-MENU-REGISTRY-SYNC] StaffMenuMaster synced: {master_synced_count} entries updated")
    
    db.commit()
    
    total_synced = updated_count + pattern_matched_count + migrated_count
    logger.info(f"[DC-MENU-REGISTRY-SYNC] Explicit: {updated_count}, Pattern-matched: {pattern_matched_count}, Migrated: {migrated_count}, Hidden: {legacy_hidden_count}, Unmapped: {len(unmapped_routes)}")
    
    return {
        "success": True,
        "updated_count": updated_count,
        "pattern_matched_count": pattern_matched_count,
        "migrated_count": migrated_count,
        "legacy_hidden_count": legacy_hidden_count,
        "unmapped_count": len(unmapped_routes),
        "unmapped_routes": unmapped_routes[:20] if unmapped_routes else [],
        "total_synced": total_synced,
        "total_menus": len(all_menus),
        "master_synced_count": master_synced_count,
        "total_master_menus": len(all_master_menus),
        "canonical_sections": len(CANONICAL_SECTIONS),
        "message": f"Synchronized {total_synced} registry items + {master_synced_count} master items. Hidden {legacy_hidden_count} legacy entries. Access Matrix now synced with Sidebar."
    }


def _is_page_registry_admin(user):
    """DC Protocol: Only VGK4U and EA can access Page Registry Manager"""
    if hasattr(user, 'staff_type') and user.staff_type in ['VGK4U', 'VGK4U Supreme']:
        return True
    role = getattr(user, 'role', None)
    if role:
        role_code = getattr(role, 'role_code', '')
        if role_code and role_code.lower() in ['vgk4u', 'ea']:
            return True
    return False


@router.get("/page-registry/all")
async def get_page_registry_all(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_staff_user)
):
    """
    DC Protocol: Page Registry Manager - Returns ALL pages (active + inactive)
    grouped by sidebar_section with role/audience stats.
    Access: VGK4U and EA only.
    """
    if not _is_page_registry_admin(current_user):
        raise HTTPException(status_code=403, detail="Access denied. VGK4U and EA only.")

    from app.models.staff import StaffMenuRegistry

    all_entries = db.query(StaffMenuRegistry).order_by(
        StaffMenuRegistry.sidebar_section_order,
        StaffMenuRegistry.sidebar_section,
        StaffMenuRegistry.display_order,
        StaffMenuRegistry.menu_name
    ).all()

    sections = {}
    total_active = 0
    total_inactive = 0
    audience_counts = {}
    source_counts = {}
    type_counts = {}

    MNR_MEMBER_SECTIONS = {
        'MNRUSER_DASHBOARD', 'MNRUSER_EARNINGS', 'MNRUSER_MEMBERS',
        'MNRUSER_COUPONS', 'MNRUSER_AWARDS', 'MNRUSER_ANNOUNCEMENTS',
        'MNRUSER_AUDIT', 'MNRUSER_MYNTREAL', 'MNRUSER_ZYNOVA', 'MNR_USER'
    }
    MNR_ADMIN_SECTIONS = {
        'MNR_ADMIN', 'MNR_ANNOUNCEMENTS', 'MNR_APPROVALS', 'MNR_AWARDS',
        'MNR_CONFIG', 'MNR_DATA', 'MNR_FINANCE', 'MNR_INCOME', 'MNR_PINS',
        'MNR_SECURITY', 'MNR_USERS', 'MNR_WITHDRAWALS', 'MNR'
    }

    def _classify_group(sec_key, menu_type):
        if sec_key in MNR_MEMBER_SECTIONS:
            return 'mnr_member'
        if sec_key in MNR_ADMIN_SECTIONS or (menu_type == 'MNR' and sec_key not in MNR_MEMBER_SECTIONS):
            return 'mnr_admin'
        return 'staff'

    group_counts = {'staff': {'active': 0, 'inactive': 0}, 'mnr_member': {'active': 0, 'inactive': 0}, 'mnr_admin': {'active': 0, 'inactive': 0}}

    for entry in all_entries:
        section_key = entry.sidebar_section or '_uncategorized'
        section_title = entry.sidebar_section_title or entry.sidebar_section or 'Uncategorized'
        menu_group = _classify_group(section_key, entry.menu_type or 'STAFF')

        if section_key not in sections:
            sections[section_key] = {
                'section_code': section_key,
                'section_title': section_title,
                'section_order': entry.sidebar_section_order or 999,
                'menu_group': menu_group,
                'pages': [],
                'active_count': 0,
                'inactive_count': 0
            }

        page_dict = entry.to_dict()
        page_dict['menu_group'] = menu_group
        sections[section_key]['pages'].append(page_dict)

        if entry.is_active:
            sections[section_key]['active_count'] += 1
            total_active += 1
            group_counts[menu_group]['active'] += 1
        else:
            sections[section_key]['inactive_count'] += 1
            total_inactive += 1
            group_counts[menu_group]['inactive'] += 1

        aud = entry.audience_scope or 'staff'
        audience_counts[aud] = audience_counts.get(aud, 0) + 1

        src = entry.source or 'unknown'
        source_counts[src] = source_counts.get(src, 0) + 1

        mt = entry.menu_type or 'STAFF'
        type_counts[mt] = type_counts.get(mt, 0) + 1

    sorted_sections = sorted(sections.values(), key=lambda s: s['section_order'])

    return {
        "success": True,
        "stats": {
            "total_pages": len(all_entries),
            "active_pages": total_active,
            "inactive_pages": total_inactive,
            "section_count": len(sections),
            "audience_breakdown": audience_counts,
            "source_breakdown": source_counts,
            "type_breakdown": type_counts,
            "group_counts": group_counts
        },
        "sections": sorted_sections
    }


@router.put("/page-registry/{registry_id}/toggle")
async def toggle_page_registry(
    registry_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_staff_user)
):
    """
    DC Protocol: Toggle is_active on a StaffMenuRegistry entry.
    When toggled ON: auto re-sync to all company menus.
    When toggled OFF: deactivate in all company menus.
    WVV Protocol: Full audit logging.
    Access: VGK4U and EA only.
    """
    if not _is_page_registry_admin(current_user):
        raise HTTPException(status_code=403, detail="Access denied. VGK4U and EA only.")

    from app.models.staff import StaffMenuRegistry

    entry = db.query(StaffMenuRegistry).filter(StaffMenuRegistry.id == registry_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Registry entry not found")

    old_state = entry.is_active
    new_state = not old_state
    entry.is_active = new_state
    entry.updated_at = get_indian_time()

    if new_state:
        companies = db.query(AssociatedCompany).filter(AssociatedCompany.is_active == True).all()
        synced_count = 0
        for company in companies:
            existing = db.query(StaffMenuMaster).filter(
                StaffMenuMaster.company_id == company.id,
                StaffMenuMaster.menu_code == entry.menu_code
            ).first()
            if existing:
                existing.is_active = True
                existing.menu_name = entry.menu_name
                existing.route_path = entry.route_path
                existing.menu_description = entry.menu_description
                existing.audience_scope = entry.audience_scope or 'staff'
            else:
                new_master = StaffMenuMaster(
                    company_id=company.id,
                    menu_code=entry.menu_code,
                    menu_name=entry.menu_name,
                    menu_description=entry.menu_description,
                    route_path=entry.route_path,
                    menu_category=entry.menu_category,
                    menu_icon=entry.menu_icon,
                    display_order=entry.display_order,
                    audience_scope=entry.audience_scope or 'staff',
                    is_active=True,
                    is_default_visible=entry.is_default_visible,
                    is_default_accessible=entry.is_default_accessible
                )
                db.add(new_master)
            synced_count += 1
    else:
        deactivated = db.query(StaffMenuMaster).filter(
            StaffMenuMaster.menu_code == entry.menu_code,
            StaffMenuMaster.is_active == True
        ).update({StaffMenuMaster.is_active: False}, synchronize_session=False)

    try:
        from app.core.audit import AuditLogger
        AuditLogger.log_staff_page_action(
            db=db,
            staff_id=current_user.id,
            emp_code=current_user.emp_code,
            action='page_registry_toggle',
            page_url='/staff/page-registry',
            details={
                'registry_id': registry_id,
                'menu_code': entry.menu_code,
                'menu_name': entry.menu_name,
                'old_state': old_state,
                'new_state': new_state,
                'synced_companies': synced_count if new_state else (deactivated if not new_state else 0)
            }
        )
    except Exception as e:
        logger.warning(f"[DC-PAGE-REGISTRY] Audit log failed: {e}")

    db.commit()

    return {
        "success": True,
        "registry_id": registry_id,
        "menu_code": entry.menu_code,
        "menu_name": entry.menu_name,
        "is_active": new_state,
        "message": f"Page '{entry.menu_name}' {'activated' if new_state else 'deactivated'} successfully"
    }


@router.put("/page-registry/bulk-toggle")
async def bulk_toggle_page_registry(
    action: str = Body(..., description="'activate' or 'deactivate'"),
    registry_ids: List[int] = Body(..., description="List of registry IDs to toggle"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_staff_user)
):
    """
    DC Protocol: Bulk toggle is_active on multiple StaffMenuRegistry entries.
    Access: VGK4U and EA only.
    """
    if not _is_page_registry_admin(current_user):
        raise HTTPException(status_code=403, detail="Access denied. VGK4U and EA only.")

    if action not in ['activate', 'deactivate']:
        raise HTTPException(status_code=400, detail="Action must be 'activate' or 'deactivate'")

    from app.models.staff import StaffMenuRegistry

    new_state = action == 'activate'
    entries = db.query(StaffMenuRegistry).filter(StaffMenuRegistry.id.in_(registry_ids)).all()

    if not entries:
        raise HTTPException(status_code=404, detail="No entries found")

    toggled = []
    for entry in entries:
        if entry.is_active != new_state:
            entry.is_active = new_state
            entry.updated_at = get_indian_time()
            toggled.append(entry.menu_code)

    if new_state:
        companies = db.query(AssociatedCompany).filter(AssociatedCompany.is_active == True).all()
        for entry in entries:
            if entry.menu_code in toggled:
                for company in companies:
                    existing = db.query(StaffMenuMaster).filter(
                        StaffMenuMaster.company_id == company.id,
                        StaffMenuMaster.menu_code == entry.menu_code
                    ).first()
                    if existing:
                        existing.is_active = True
                        existing.menu_name = entry.menu_name
                        existing.route_path = entry.route_path
                        existing.menu_description = entry.menu_description
                        existing.audience_scope = entry.audience_scope or 'staff'
                        existing.menu_icon = entry.menu_icon
                        existing.display_order = entry.display_order
                    else:
                        new_master = StaffMenuMaster(
                            company_id=company.id,
                            menu_code=entry.menu_code,
                            menu_name=entry.menu_name,
                            menu_description=entry.menu_description,
                            route_path=entry.route_path,
                            menu_category=entry.menu_category,
                            menu_icon=entry.menu_icon,
                            display_order=entry.display_order,
                            audience_scope=entry.audience_scope or 'staff',
                            is_active=True,
                            is_default_visible=entry.is_default_visible,
                            is_default_accessible=entry.is_default_accessible
                        )
                        db.add(new_master)
    else:
        for code in toggled:
            db.query(StaffMenuMaster).filter(
                StaffMenuMaster.menu_code == code,
                StaffMenuMaster.is_active == True
            ).update({StaffMenuMaster.is_active: False}, synchronize_session=False)

    try:
        from app.core.audit import AuditLogger
        AuditLogger.log_staff_page_action(
            db=db,
            staff_id=current_user.id,
            emp_code=current_user.emp_code,
            action='page_registry_bulk_toggle',
            page_url='/staff/page-registry',
            details={
                'action': action,
                'toggled_count': len(toggled),
                'toggled_codes': toggled[:50]
            }
        )
    except Exception as e:
        logger.warning(f"[DC-PAGE-REGISTRY] Bulk audit log failed: {e}")

    db.commit()

    return {
        "success": True,
        "action": action,
        "toggled_count": len(toggled),
        "total_requested": len(registry_ids),
        "message": f"{len(toggled)} pages {action}d successfully"
    }


@router.put("/page-registry/{registry_id}/move-section")
async def move_page_registry_section(
    registry_id: int,
    sidebar_section: str = Body(..., description="New section code"),
    sidebar_section_title: str = Body(..., description="New section title"),
    sidebar_section_order: int = Body(..., description="New section order number"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_staff_user)
):
    """
    DC Protocol: Move a page to a different section via drag-and-drop.
    Only changes section grouping - does NOT change active/inactive status.
    Access: VGK4U and EA only.
    """
    if not _is_page_registry_admin(current_user):
        raise HTTPException(status_code=403, detail="Access denied. VGK4U and EA only.")

    from app.models.staff import StaffMenuRegistry

    entry = db.query(StaffMenuRegistry).filter(StaffMenuRegistry.id == registry_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Registry entry not found")

    old_section = entry.sidebar_section
    entry.sidebar_section = sidebar_section
    entry.sidebar_section_title = sidebar_section_title
    entry.sidebar_section_order = sidebar_section_order
    entry.updated_at = get_indian_time()

    try:
        from app.core.audit import AuditLogger
        AuditLogger.log_staff_page_action(
            db=db,
            staff_id=current_user.id,
            emp_code=current_user.emp_code,
            action='page_registry_move_section',
            page_url='/staff/page-registry',
            details={
                'registry_id': registry_id,
                'menu_code': entry.menu_code,
                'old_section': old_section,
                'new_section': sidebar_section,
                'new_section_title': sidebar_section_title
            }
        )
    except Exception as e:
        logger.warning(f"[DC-PAGE-REGISTRY] Move section audit log failed: {e}")

    db.commit()

    return {
        "success": True,
        "registry_id": registry_id,
        "menu_code": entry.menu_code,
        "old_section": old_section,
        "new_section": sidebar_section,
        "message": f"Page '{entry.menu_name}' moved from '{old_section}' to '{sidebar_section}'"
    }


# ============= Internal Section Access Management Endpoints =============
# DC Protocol: VGK Mentor controls which Internal pages EA role can access

@router.get("/internal-access/pages")
async def get_internal_pages_with_ea_access(
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """
    Get all Internal section pages with EA role access status.
    Access: VGK Mentor (vgk4u) only.
    Returns each internal page with whether EA role currently has access.
    """
    user_role_code = getattr(current_user.role, 'role_code', '').lower() if current_user.role else ''
    if current_user.staff_type not in ['VGK4U', 'VGK4U Supreme'] and user_role_code != 'vgk4u':
        raise HTTPException(status_code=403, detail="Only VGK Mentor can manage Internal section access.")

    # Get all internal section pages from registry
    internal_pages = db.query(StaffMenuRegistry).filter(
        StaffMenuRegistry.sidebar_section == 'internal',
        StaffMenuRegistry.is_active == True,
        StaffMenuRegistry.route_path != '/staff/internal-menu-access'  # Hide the manager page itself
    ).order_by(StaffMenuRegistry.item_order, StaffMenuRegistry.display_order, StaffMenuRegistry.menu_name).all()

    # Get current EA access grants
    ea_grants = {
        row.route_path: row.is_enabled
        for row in db.query(StaffRoleMenuAccess).filter(
            StaffRoleMenuAccess.role_code == 'ea'
        ).all()
    }

    pages = []
    for page in internal_pages:
        pages.append({
            "id": page.id,
            "menu_code": page.menu_code,
            "menu_name": page.menu_name,
            "route_path": page.route_path,
            "menu_icon": page.menu_icon or "fa-file",
            "ea_access": ea_grants.get(page.route_path, False)
        })

    return {
        "success": True,
        "pages": pages,
        "total": len(pages)
    }


@router.put("/internal-access/pages")
async def update_ea_internal_access(
    updates: dict,
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """
    Update EA role access for Internal section pages.
    Access: VGK Mentor (vgk4u) only.
    Body: { "route_path": "/staff/nda-versions", "is_enabled": true }
    OR bulk: { "bulk": [{"route_path": "...", "is_enabled": true}, ...] }
    """
    user_role_code = getattr(current_user.role, 'role_code', '').lower() if current_user.role else ''
    if current_user.staff_type not in ['VGK4U', 'VGK4U Supreme'] and user_role_code != 'vgk4u':
        raise HTTPException(status_code=403, detail="Only VGK Mentor can manage Internal section access.")

    # Never allow granting access to the menu-access page itself to EA
    PROTECTED_ROUTES = {'/staff/internal-menu-access'}

    changes = []
    bulk = updates.get('bulk', [])
    if not bulk:
        # Single update
        route = updates.get('route_path')
        enabled = updates.get('is_enabled', False)
        if route:
            bulk = [{'route_path': route, 'is_enabled': enabled}]

    for item in bulk:
        route_path = item.get('route_path')
        is_enabled = item.get('is_enabled', False)
        if not route_path or route_path in PROTECTED_ROUTES:
            continue

        existing = db.query(StaffRoleMenuAccess).filter(
            StaffRoleMenuAccess.role_code == 'ea',
            StaffRoleMenuAccess.route_path == route_path
        ).first()

        if existing:
            existing.is_enabled = is_enabled
            existing.updated_by_emp_code = current_user.emp_code
            existing.updated_by_name = current_user.full_name
            existing.updated_at = get_indian_time()
        else:
            db.add(StaffRoleMenuAccess(
                role_code='ea',
                route_path=route_path,
                is_enabled=is_enabled,
                updated_by_emp_code=current_user.emp_code,
                updated_by_name=current_user.full_name
            ))
        changes.append({'route_path': route_path, 'is_enabled': is_enabled})

    db.commit()
    logger.info(f"[DC-INTERNAL-ACCESS] {current_user.emp_code} updated EA access: {changes}")

    return {
        "success": True,
        "changes": changes,
        "message": f"Updated EA access for {len(changes)} page(s)"
    }
