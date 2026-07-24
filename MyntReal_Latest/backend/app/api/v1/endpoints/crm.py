"""
Universal CRM/Lead Management API Endpoints
DC Protocol: All endpoints enforce company_id segregation
Supports leads from any category with handlers: Staff, Partners, Members
"""

import logging
import os as _os
from fastapi import APIRouter, Depends, HTTPException, Query, Body, Request, UploadFile, File, Form
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, or_, and_, text, extract
from typing import Optional, List
from datetime import datetime, timedelta
import pytz as _pytz
from pydantic import BaseModel, EmailStr, Field

logger = logging.getLogger(__name__)

_CRM_IST = _pytz.timezone('Asia/Kolkata')


def _to_ist_naive(dt: datetime) -> datetime:
    """DC Protocol: Normalise any datetime to IST naive for storage.
    Strips UTC/tz-offset so DB comparisons stay consistent with IST-based dialer logic."""
    if dt is None:
        return None
    if dt.tzinfo is not None:
        dt = dt.astimezone(_CRM_IST).replace(tzinfo=None)
    return dt


def _canonical_base(request: Request) -> str:
    """DC Protocol: Return correct public base URL for share links.
    Reads the actual domain the user accessed (X-Forwarded-Host set by Replit
    reverse proxy), so share links generated on myntreal.com say myntreal.com,
    on mnrteam.com say mnrteam.com, etc.
    In production (REPL_DEPLOYMENT set) falls back to https://mnrteam.com.
    In dev, allows .replit.dev URLs so tokens created in dev are reachable."""
    _RAW_HOSTS = {"127.0.0.1:8000", "localhost:8000", "localhost", "0.0.0.0:8000"}
    is_prod = bool(_os.environ.get("REPL_DEPLOYMENT"))
    scheme = request.headers.get("x-forwarded-proto", "https")
    # X-Forwarded-Host is set by Replit's CDN/proxy to the custom domain
    forwarded_host = request.headers.get("x-forwarded-host", "").strip()
    if forwarded_host and forwarded_host not in _RAW_HOSTS:
        # In production, skip raw dev domains so we never embed a .replit.dev URL
        if is_prod and (".replit.dev" in forwarded_host or ".repl.co" in forwarded_host):
            pass  # fall through to hardcoded default below
        else:
            return f"{scheme}://{forwarded_host}"
    # Fallback: plain Host header
    host = request.headers.get("host", "").strip()
    if host and host not in _RAW_HOSTS:
        if is_prod and (".replit.dev" in host or ".repl.co" in host):
            pass  # fall through to hardcoded default below
        else:
            return f"{scheme}://{host}"
    # Last resort: production uses canonical domain; dev uses request base_url
    if is_prod:
        return "https://mnrteam.com"
    return str(request.base_url).rstrip("/")


from app.core.database import get_db
from app.models.crm import (
    CRMLead, CRMLeadFollowUp, CRMLeadNote, 
    CRMLeadAssignment, CRMLeadSource, DEFAULT_LEAD_SOURCES, SELF_LEAD_SOURCE_NAME,
    CRMRevenueEntry, CRMRevenueApprovalStatus,
    CRMLeadTransaction, TRANSACTION_TYPES, PAYMENT_MODES,
    TransactionValidationStatus, LedgerPartySource,
    CRMLeadDeal
)
from app.models.staff_accounts import PartyLedger
from decimal import Decimal
from app.models.signup_category import SignupCategory
from app.models.staff import StaffEmployee
from app.models.staff_accounts import VendorMaster, OfficialPartner
from app.models.solar import CRMSolarLeadTech
from app.models.user import User
from app.models.call_tracking import StaffCallLog
from app.api.v1.endpoints.staff_auth import get_current_staff_user
from app.utils.staff_hierarchy import get_recursive_downline, has_direct_reports, _get_hidden_employee_ids, HIDDEN_FROM_TEAM_CODES
from app.core.security import get_current_user_hybrid, get_current_user_hybrid_with_partner
from app.api.v1.endpoints.myntreal_incentives import create_incentive_for_validated_transaction
import pytz


router = APIRouter()


def _eff_dv():
    """DC-REPORT-DV-001: Effective deal value per-row SQLAlchemy expression for all reports/calculations.
    Rule: use deal_value_total for in-progress leads; COALESCE(confirmed_final_value, deal_value_total) for completed.
    'Completed' = status='completed' OR solar_pipeline_status='completed' OR ev_b2b_stage='completed'.
    This ensures stale/incorrect locked CFV values do not pollute in-progress pipeline figures."""
    from sqlalchemy import case as _c, or_ as _or_
    _done = _or_(
        CRMLead.status == 'completed',
        CRMLead.solar_pipeline_status == 'completed',
        CRMLead.ev_b2b_stage == 'completed',
    )
    _cfv = CRMLead.confirmed_final_value
    _dvt = CRMLead.deal_value_total
    return _c(
        (_done, func.coalesce(_cfv, _dvt)),
        else_=_dvt
    )


# DC Protocol: Centralized RBAC helper for VGK/EA admin checks
# Handles variations like VGK4U, VGK_SUPREME, etc.
def is_vgk_admin(staff_type: str) -> bool:
    """Check if staff type is VGK variant, EA, or Sales Incharge (full CRM/leads admin)."""
    normalized = (staff_type or '').upper()
    return 'VGK' in normalized or normalized in {'EA', 'SALES_INCHARGE'}


def get_editable_handler_slots(lead, current_employee, db) -> dict:
    """
    Calculate which handler slots the current user can edit for a given lead.
    DC Protocol: Uses company-wise staff hierarchy for reporting manager checks.
    
    Returns dict with keys: telecaller, field_staff, partner, reason
    Each slot value is True if user can edit that slot, False otherwise.
    
    RBAC Rules:
    1. VGK/EA Admins: Can edit all slots
    2. Primary Owner (staff type): Can edit all slots
    3. Reporting Manager (supervisor of any assigned handler): Can edit all slots
    4. Assigned Telecaller: Can only edit telecaller slot (self-reassignment)
    5. Assigned Field Staff: Can only edit field_staff slot (self-reassignment)
    6. Others: No edit access
    """
    staff_type = (current_employee.staff_type or '').upper()
    user_id = current_employee.id
    
    # Default: no access
    slots = {
        'telecaller': False,
        'field_staff': False,
        'partner': False,
        'reason': 'no_access'
    }
    
    # Rule 1: VGK/EA Admins - full access
    if is_vgk_admin(staff_type):
        return {
            'telecaller': True,
            'field_staff': True,
            'partner': True,
            'reason': 'admin'
        }
    
    # Rule 2: Primary Owner (staff type) - full access
    if lead.primary_owner_type == 'staff' and lead.primary_owner_id == user_id:
        return {
            'telecaller': True,
            'field_staff': True,
            'partner': True,
            'reason': 'primary_owner'
        }

    # Rule 2b (F5): Assigned handler — the staff member who "owns" the lead
    # after a bulk transfer. handler_id is emp_code-based; give full slot access
    # so transferred leads can be fully edited by the new assignee.
    if lead.handler_type == 'staff' and lead.handler_id == current_employee.emp_code:
        return {
            'telecaller': True,
            'field_staff': True,
            'partner': True,
            'reason': 'assigned_handler'
        }

    # Rule 3: Reporting Manager - check if current user supervises any assigned handler
    # DC Protocol: Verify company context - manager must be in same company as the handler
    # Using staff hierarchy to check if user is a manager of telecaller or field_staff
    is_reporting_manager = False
    current_company_id = current_employee.base_company_id
    
    if lead.telecaller_id:
        telecaller = db.query(StaffEmployee).filter(StaffEmployee.id == lead.telecaller_id).first()
        # DC Protocol: Verify manager and handler share company context
        if telecaller and telecaller.reporting_to == current_employee.emp_code:
            # Check if handler's base_company matches manager's company for DC compliance
            if telecaller.base_company_id == current_company_id or current_company_id is None:
                is_reporting_manager = True
    
    if lead.field_staff_id and not is_reporting_manager:
        field_staff = db.query(StaffEmployee).filter(StaffEmployee.id == lead.field_staff_id).first()
        # DC Protocol: Verify manager and handler share company context
        if field_staff and field_staff.reporting_to == current_employee.emp_code:
            if field_staff.base_company_id == current_company_id or current_company_id is None:
                is_reporting_manager = True
    
    if is_reporting_manager:
        return {
            'telecaller': True,
            'field_staff': True,
            'partner': True,
            'reason': 'reporting_manager'
        }
    
    # Rule 4 & 5: Self-reassignment - can only edit own slot
    if lead.telecaller_id == user_id:
        slots['telecaller'] = True
        slots['reason'] = 'self_assigned_telecaller'
    
    if lead.field_staff_id == user_id:
        slots['field_staff'] = True
        slots['reason'] = 'self_assigned_field_staff' if slots['reason'] == 'no_access' else 'self_assigned_both'
    
    return slots


def can_change_primary_owner(lead, current_employee, db) -> tuple:
    """
    DC Protocol (Jan 1, 2026): Check if current user can change lead's primary owner.
    
    Returns (can_change: bool, reason: str)
    
    RBAC Rules:
    1. VGK/EA Admins: Can change owner
    2. Current Primary Owner: Can change (transfer to someone else)
    3. Lead Owner's Reporting Manager: Can change
    """
    staff_type = (current_employee.staff_type or '').upper()
    user_id = current_employee.id
    
    # Rule 1: VGK/EA Admins
    if is_vgk_admin(staff_type):
        return True, 'admin'
    
    # Rule 2: Current Primary Owner
    if lead.primary_owner_type == 'staff' and lead.primary_owner_id == user_id:
        return True, 'self'
    
    # Rule 3: Reporting Manager of the lead owner
    if lead.primary_owner_type == 'staff' and lead.primary_owner_id:
        owner = db.query(StaffEmployee).filter(StaffEmployee.id == lead.primary_owner_id).first()
        if owner and owner.reporting_to == current_employee.emp_code:
            return True, 'reporting_manager'
    
    return False, 'unauthorized'


# Import AssociatedCompany model for CRM companies endpoint
from app.models.staff_accounts import AssociatedCompany


@router.get("/my-companies")
def get_my_companies(
    db: Session = Depends(get_db),
    current_employee: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Get companies accessible to current staff for CRM purposes.
    DC Protocol: All authenticated staff can view active companies for CRM access.
    Also returns visibility permissions for the current user.
    """
    # All staff can see all active companies for CRM lead management
    companies = db.query(AssociatedCompany).filter(
        AssociatedCompany.is_active == True
    ).order_by(AssociatedCompany.company_name).all()
    
    # Determine visibility permissions
    staff_type = (current_employee.staff_type or '').upper()
    is_admin = is_vgk_admin(staff_type)
    is_leader = has_direct_reports(current_employee.id, db, StaffEmployee)
    
    # Can view all leads if admin OR has direct reports (team leader)
    can_view_all_leads = is_admin or is_leader
    
    return {
        'success': True,
        'companies': [
            {
                'id': c.id,
                'company_code': c.company_code,
                'company_name': c.company_name,
                'is_active': c.is_active,
                'is_book_keeper': c.is_book_keeper
            }
            for c in companies
        ],
        'permissions': {
            'can_view_all_leads': can_view_all_leads,
            'is_admin': is_admin,
            'is_leader': is_leader,
            'staff_type': staff_type
        }
    }


def get_indian_time():
    indian_tz = pytz.timezone('Asia/Kolkata')
    return datetime.now(indian_tz).replace(tzinfo=None)


def _resolve_company_from_category(db, category_id, fallback_company_id: int) -> int:
    """
    DC_CAT_COMPANY: Derive the authoritative company_id from a lead's category.

    SignupCategory.company_id is the source of truth for which company owns a
    category. If a lead has a category_id, its company must match the category's
    company — this prevents leads being orphaned or misrouted across companies.

    Rules:
      - category_id provided and valid → return category.company_id
      - category_id missing, zero, or category not found → return fallback_company_id
    """
    if not category_id:
        return fallback_company_id
    from app.models.signup_category import SignupCategory as _SC
    cat = db.query(_SC).filter(_SC.id == category_id).first()
    if cat and cat.company_id:
        return cat.company_id
    return fallback_company_id


class LeadCreate(BaseModel):
    name: str
    company_id: Optional[int] = None  # DC Protocol: Optional at creation, mandatory at deal close/won
    email: Optional[str] = None
    phone: Optional[str] = None
    phone_primary_whatsapp: Optional[bool] = False
    alternate_phone: Optional[str] = None
    phone_secondary_whatsapp: Optional[bool] = False
    category_id: Optional[int] = None
    source: Optional[str] = None
    source_details: Optional[str] = None
    priority: Optional[str] = "medium"
    status: Optional[str] = "new"
    handler_type: Optional[str] = "unassigned"
    handler_id: Optional[str] = None
    telecaller_id: Optional[int] = None
    field_staff_id: Optional[int] = None
    associated_partner_id: Optional[int] = None
    vendor_id: Optional[int] = None
    mnr_handler_id: Optional[str] = None
    guru_id: Optional[str] = None
    z_guru_id: Optional[str] = None
    adi_guru_id: Optional[str] = None
    # DC Protocol Fix (Apr 2026): Text name storage for partner-chain uplines
    guru_name: Optional[str] = None
    z_guru_name: Optional[str] = None
    source_ref_type: Optional[str] = None
    source_ref_id: Optional[str] = None
    source_ref_name: Optional[str] = None
    field_support_ref_type: Optional[str] = None
    field_support_ref_id: Optional[str] = None
    field_support_ref_name: Optional[str] = None
    technical_id: Optional[int] = None
    support_staff_id: Optional[int] = None
    technical_staff1_id: Optional[int] = None
    description: Optional[str] = None
    requirements: Optional[str] = None
    looking_for: Optional[str] = None
    recent_comments: Optional[str] = None
    budget_min: Optional[float] = None
    budget_max: Optional[float] = None
    address: Optional[str] = None
    area: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None
    expected_close_date: Optional[datetime] = None
    next_followup_date: Optional[datetime] = None
    depends_on_staff_id: Optional[int] = None
    tags: Optional[str] = None
    # B2B Meta Lead Form fields (Mar 2026)
    investment_capacity: Optional[str] = None
    planning_to_start: Optional[str] = None
    full_time_business: Optional[str] = None
    # VGK program fields (must mirror LeadUpdate)
    is_vgk_program: Optional[bool] = None
    vgk_field_support_id: Optional[int] = None
    # DC-VGK-BRAND-INCENTIVE-001 (Jun 2026): optional brand for brand-specific incentives
    solar_brand_id: Optional[int] = None
    # DC-LEAD-CREATE-FIELDS-001 (Jun 2026): team assignment fields missing from LeadCreate
    showroom_vgk_id: Optional[int] = None
    team_senior_partner_id: Optional[int] = None
    team_extended_partner_id: Optional[int] = None
    team_core_partner_id: Optional[int] = None


class LeadUpdate(BaseModel):
    name: Optional[str] = None
    company_id: Optional[int] = None  # DC Protocol: Can be updated, mandatory at deal close/won
    email: Optional[str] = None
    phone: Optional[str] = None
    phone_primary_whatsapp: Optional[bool] = None
    alternate_phone: Optional[str] = None
    phone_secondary_whatsapp: Optional[bool] = None
    category_id: Optional[int] = None
    source: Optional[str] = None
    source_details: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    primary_owner_id: Optional[int] = None
    primary_owner_type: Optional[str] = None
    # DC Protocol (Dec 31, 2025): Legacy handler fields - accepted from frontend for compatibility
    handler_type: Optional[str] = None  # Legacy field for backward compatibility
    handler_id: Optional[str] = None  # Legacy field for backward compatibility
    telecaller_id: Optional[int] = None
    field_staff_id: Optional[int] = None
    associated_partner_id: Optional[int] = None
    vendor_id: Optional[int] = None
    mnr_handler_id: Optional[str] = None
    guru_id: Optional[str] = None
    z_guru_id: Optional[str] = None
    adi_guru_id: Optional[str] = None
    # DC Protocol Fix (Apr 2026): Text name storage for partner-chain uplines
    guru_name: Optional[str] = None
    z_guru_name: Optional[str] = None
    is_vgk_program: Optional[bool] = None
    vgk_field_support_id: Optional[int] = None
    # DC-VGK-BRAND-INCENTIVE-001 (Jun 2026): optional brand for brand-specific incentives
    solar_brand_id: Optional[int] = None
    source_ref_type: Optional[str] = None
    source_ref_id: Optional[str] = None
    source_ref_name: Optional[str] = None
    field_support_ref_type: Optional[str] = None
    field_support_ref_id: Optional[str] = None
    field_support_ref_name: Optional[str] = None
    technical_id: Optional[int] = None
    support_staff_id: Optional[int] = None
    technical_staff1_id: Optional[int] = None
    description: Optional[str] = None
    requirements: Optional[str] = None
    looking_for: Optional[str] = None
    recent_comments: Optional[str] = None
    budget_min: Optional[float] = None
    budget_max: Optional[float] = None
    address: Optional[str] = None
    area: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None
    expected_close_date: Optional[datetime] = None
    next_followup_date: Optional[datetime] = None
    depends_on_staff_id: Optional[int] = None
    # Deal Value System (3-part: Total, Received, Balance auto-calculated)
    deal_value: Optional[float] = None  # Legacy field - maps to deal_value_total
    deal_value_total: Optional[float] = None  # Overall deal closed value
    deal_value_received: Optional[float] = None  # Amount received so far
    deal_value_balance: Optional[float] = None  # DC Protocol: Accept from frontend, auto-calculated
    solar_value: Optional[float] = None  # DC-SOLAR-VALUE-001: Manual project value used as VGK commission base
    confirmed_final_value: Optional[float] = None  # DC-CFV-EDIT-001: Superadmin override — MR10001/MR10025 only
    lost_reason: Optional[str] = None
    tags: Optional[str] = None
    time_taken_minutes: Optional[int] = Field(None, ge=1, le=1440, description="Time spent on this lead update in minutes")
    # DC Protocol (Mar 2026): KYC / Document / Banking / Location fields
    aadhaar_number: Optional[str] = None
    pan_number: Optional[str] = None
    electricity_bill_number: Optional[str] = None
    google_maps_link: Optional[str] = None
    bank_account_number: Optional[str] = None
    ifsc_code: Optional[str] = None
    subsidy_status: Optional[str] = None
    solar_pipeline_status: Optional[str] = None  # bank/procurement_pending/installed/net_meter_pending/bank_loan_completed/subsidy_cleared
    ev_b2b_stage: Optional[str] = None  # EV B2B dealership onboarding stage (Apr 2026)
    # Solar-specific fields (Mar 2026)
    application_no: Optional[str] = None
    accepted_date: Optional[datetime] = None
    loan_bank: Optional[str] = None
    bank_branch: Optional[str] = None
    documents_folder_link: Optional[str] = None
    material_reach_date: Optional[datetime] = None
    installation_date: Optional[datetime] = None
    existing_association: Optional[str] = None
    # Solar finance qualification fields (Mar 2026)
    bank_entry_updated: Optional[bool] = None
    bank_statement_available: Optional[bool] = None
    regular_income_available: Optional[bool] = None
    monthly_income: Optional[float] = None   # Manual monthly income entry (Apr 2026)
    co_applicant_name: Optional[str] = None
    co_applicant_phone: Optional[str] = None
    co_applicant_aadhaar: Optional[str] = None
    co_applicant_pan: Optional[str] = None
    co_applicant_bank_account: Optional[str] = None
    co_applicant_ifsc: Optional[str] = None
    # B2B Meta Lead Form fields (Mar 2026)
    investment_capacity: Optional[str] = None
    planning_to_start: Optional[str] = None
    full_time_business: Optional[str] = None
    # DC_CIBIL_ADVANCE_001 (May 2026): CIBIL fields — previously omitted from this
    # schema, causing every CIBIL save from staff_mnr_leads_master.html to be a
    # silent no-op (Pydantic dropped unknown keys before update_data was built).
    cibil_score: Optional[int] = Field(None, ge=300, le=900)
    cibil_confirmed: Optional[bool] = None
    # DC Protocol Apr 2026: Per-handler support confirmation flags (null=pending, true=yes, false=no)
    guru_supported: Optional[bool] = None
    z_guru_supported: Optional[bool] = None
    adi_guru_supported: Optional[bool] = None
    core_supported: Optional[bool] = None
    core_id: Optional[str] = None
    core_name: Optional[str] = None
    telecaller_supported: Optional[bool] = None
    showroom_supported: Optional[bool] = None
    showroom_vgk_id: Optional[int] = None
    technical_supported: Optional[bool] = None
    field_support_supported: Optional[bool] = None
    support_staff_supported: Optional[bool] = None
    technical_staff1_supported: Optional[bool] = None
    # DC-TEAM-ASSIGN-001 (Jun 2026): OfficialPartner override IDs for L2/L3/L4 upline slots
    team_senior_partner_id: Optional[int] = None
    team_extended_partner_id: Optional[int] = None
    team_core_partner_id: Optional[int] = None


class LeadAssign(BaseModel):
    handler_type: str
    handler_id: Optional[str] = None
    reason: Optional[str] = None


class FollowUpCreate(BaseModel):
    followup_type: str = "call"
    scheduled_date: datetime
    subject: Optional[str] = None
    notes: Optional[str] = None


class FollowUpUpdate(BaseModel):
    status: Optional[str] = None
    outcome: Optional[str] = None
    completed_date: Optional[datetime] = None
    notes: Optional[str] = None


class NoteCreate(BaseModel):
    note: str
    is_private: bool = False


class LeadSourceCreate(BaseModel):
    name: str
    description: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None
    display_order: int = 0


class LeadSourceUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None
    display_order: Optional[int] = None
    is_active: Optional[bool] = None


class BulkLeadUpdate(BaseModel):
    """DC Protocol (Jan 28, 2026): Bulk lead update - VGK4U/EA only"""
    lead_ids: List[int]
    new_handler_id: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    category_id: Optional[int] = None
    note: Optional[str] = None


class RevenueEntryCreate(BaseModel):
    lead_id: int
    amount_received: float
    notes: Optional[str] = None


class RevenueEntryUpdate(BaseModel):
    amount_received: Optional[float] = None
    notes: Optional[str] = None


class RevenueApprovalAction(BaseModel):
    action: str  # 'approve' or 'reject'
    rejection_reason: Optional[str] = None


class TransactionCreate(BaseModel):
    transaction_date: datetime
    amount: float
    transaction_type: str = "partial"
    payment_mode: str = "cash"
    payment_type: Optional[str] = None
    collected_by_id: Optional[int] = None
    reference_number: Optional[str] = None
    notes: Optional[str] = None
    receipt_filename: Optional[str] = None
    revenue_category_id: Optional[int] = None
    deal_id: Optional[int] = None


class TransactionValidate(BaseModel):
    action: str  # 'validate' or 'reject'
    rejection_reason: Optional[str] = None


@router.get("/dashboard")
def get_crm_dashboard(
    company_id: int = Query(..., description="Company ID for DC Protocol"),
    team_member_id: Optional[int] = Query(None, description="Filter by specific team member"),
    scope: Optional[str] = Query('all', description="'primary' for owned, 'handler' for handled, 'all' for both"),
    next_followup_from: Optional[str] = Query(None, description="DC Protocol (Jan 22, 2026): Filter by next followup date (from)"),
    next_followup_to: Optional[str] = Query(None, description="DC Protocol (Jan 22, 2026): Filter by next followup date (to)"),
    last_interacted_from: Optional[str] = Query(None, description="DC Protocol (Jan 22, 2026): Filter by last interaction date (from)"),
    last_interacted_to: Optional[str] = Query(None, description="DC Protocol (Jan 22, 2026): Filter by last interaction date (to)"),
    db: Session = Depends(get_db),
    current_employee: StaffEmployee = Depends(get_current_staff_user)
):
    """Get CRM dashboard statistics
    
    DC Protocol (Jan 1, 2026): Tri-mode team member filtering
    - scope='primary': Count only leads where member is primary owner
    - scope='handler': Count only leads where member is telecaller/field_staff/mnr_handler (NOT owner)
    - scope='all': Count leads where member is primary owner OR any handler
    
    DC Protocol (Jan 22, 2026): Date filtering support
    - next_followup_from/to: Filter by next followup date range
    - last_interacted_from/to: Filter by last interaction date range
    """
    base_query = db.query(CRMLead).filter(CRMLead.company_id == company_id)
    
    # DC Protocol (Jan 22, 2026): Apply date filters
    if next_followup_from:
        try:
            date_from = datetime.fromisoformat(next_followup_from.replace('Z', '+00:00'))
            base_query = base_query.filter(CRMLead.next_followup_date >= date_from)
        except ValueError:
            pass
    if next_followup_to:
        try:
            date_to = datetime.fromisoformat(next_followup_to.replace('Z', '+00:00'))
            base_query = base_query.filter(CRMLead.next_followup_date <= date_to)
        except ValueError:
            pass
    
    # DC Protocol (Jan 1, 2026): Tri-mode team member filtering
    if team_member_id:
        # Get employee code for MNR handler matching
        target_emp = db.query(StaffEmployee).filter(StaffEmployee.id == team_member_id).first()
        target_emp_code = target_emp.emp_code if target_emp else None
        
        if scope == 'primary':
            # Only primary owner
            base_query = base_query.filter(
                CRMLead.primary_owner_type == 'staff',
                CRMLead.primary_owner_id == team_member_id
            )
        elif scope == 'handler':
            # DC Protocol (Jan 1, 2026): Only handler roles (telecaller/field_staff/mnr_handler), NOT primary owner
            # DC Protocol Fix (Apr 2026): Also match source_ref_id for non-user-type sources
            handler_conditions = [
                CRMLead.telecaller_id == team_member_id,
                CRMLead.field_staff_id == team_member_id,
            ]
            if target_emp_code:
                handler_conditions.append(CRMLead.mnr_handler_id == target_emp_code)
                handler_conditions.append(
                    and_(CRMLead.source_ref_type.in_(('staff', 'mnr', 'vgk')),
                         CRMLead.source_ref_id == str(team_member_id))
                )
            base_query = base_query.filter(or_(*handler_conditions))
        else:
            # 'all' mode: owner OR any handler assignment
            # DC Protocol Fix (Apr 2026): Also match source_ref_id for non-user-type sources
            handler_conditions = [
                and_(CRMLead.primary_owner_type == 'staff', CRMLead.primary_owner_id == team_member_id),
                CRMLead.telecaller_id == team_member_id,
                CRMLead.field_staff_id == team_member_id,
            ]
            if target_emp_code:
                handler_conditions.append(CRMLead.mnr_handler_id == target_emp_code)
                handler_conditions.append(
                    and_(CRMLead.source_ref_type.in_(('staff', 'mnr', 'vgk')),
                         CRMLead.source_ref_id == str(team_member_id))
                )
            base_query = base_query.filter(or_(*handler_conditions))

    total_leads = base_query.count()
    
    # DC Protocol (Jan 22, 2026): Build date filter list for reuse across all queries
    date_filter = []
    if next_followup_from:
        try:
            date_from = datetime.fromisoformat(next_followup_from.replace('Z', '+00:00'))
            date_filter.append(CRMLead.next_followup_date >= date_from)
        except ValueError:
            pass
    if next_followup_to:
        try:
            date_to = datetime.fromisoformat(next_followup_to.replace('Z', '+00:00'))
            date_filter.append(CRMLead.next_followup_date <= date_to)
        except ValueError:
            pass
    
    # Build team member filter for direct queries (using same scope logic)
    team_filter = []
    if team_member_id:
        target_emp = db.query(StaffEmployee).filter(StaffEmployee.id == team_member_id).first()
        target_emp_code = target_emp.emp_code if target_emp else None
        
        if scope == 'primary':
            team_filter = [CRMLead.primary_owner_type == 'staff', CRMLead.primary_owner_id == team_member_id]
        elif scope == 'handler':
            # DC Protocol (Jan 1, 2026): Only handler roles, NOT primary owner
            # DC Protocol Fix (Apr 2026): Also match source_ref_id for non-user-type sources
            handler_conds = [
                CRMLead.telecaller_id == team_member_id,
                CRMLead.field_staff_id == team_member_id,
            ]
            if target_emp_code:
                handler_conds.append(CRMLead.mnr_handler_id == target_emp_code)
                handler_conds.append(
                    and_(CRMLead.source_ref_type.in_(('staff', 'mnr', 'vgk')),
                         CRMLead.source_ref_id == str(team_member_id))
                )
            team_filter = [or_(*handler_conds)]
        else:
            # 'all' mode: owner OR any handler assignment
            # DC Protocol Fix (Apr 2026): Also match source_ref_id for non-user-type sources
            handler_conds = [
                and_(CRMLead.primary_owner_type == 'staff', CRMLead.primary_owner_id == team_member_id),
                CRMLead.telecaller_id == team_member_id,
                CRMLead.field_staff_id == team_member_id,
            ]
            if target_emp_code:
                handler_conds.append(CRMLead.mnr_handler_id == target_emp_code)
                handler_conds.append(
                    and_(CRMLead.source_ref_type.in_(('staff', 'mnr', 'vgk')),
                         CRMLead.source_ref_id == str(team_member_id))
                )
            team_filter = [or_(*handler_conds)]
    
    # DC Protocol (Jan 22, 2026): Apply both team_filter and date_filter to all queries
    status_counts = db.query(
        CRMLead.status, func.count(CRMLead.id)
    ).filter(CRMLead.company_id == company_id, *team_filter, *date_filter).group_by(CRMLead.status).all()
    
    status_map = {status: count for status, count in status_counts}
    
    priority_counts = db.query(
        CRMLead.priority, func.count(CRMLead.id)
    ).filter(CRMLead.company_id == company_id, *team_filter, *date_filter).group_by(CRMLead.priority).all()
    
    priority_map = {priority: count for priority, count in priority_counts}
    
    # DC Protocol (Jan 22, 2026): Category counts - use same scope logic as other queries
    # Build category join conditions based on scope parameter
    category_join_conditions = [
        CRMLead.category_id == SignupCategory.id,
        CRMLead.company_id == company_id
    ]
    if team_member_id:
        target_emp_cat = db.query(StaffEmployee).filter(StaffEmployee.id == team_member_id).first()
        target_emp_code_cat = target_emp_cat.emp_code if target_emp_cat else None
        
        if scope == 'primary':
            category_join_conditions.extend([
                CRMLead.primary_owner_type == 'staff',
                CRMLead.primary_owner_id == team_member_id
            ])
        elif scope == 'handler':
            # DC Protocol Fix (Apr 2026): Also match source_ref_id for non-user-type sources
            handler_conds_cat = [
                CRMLead.telecaller_id == team_member_id,
                CRMLead.field_staff_id == team_member_id,
            ]
            if target_emp_code_cat:
                handler_conds_cat.append(CRMLead.mnr_handler_id == target_emp_code_cat)
                handler_conds_cat.append(
                    and_(CRMLead.source_ref_type.in_(('staff', 'mnr', 'vgk')),
                         CRMLead.source_ref_id == str(team_member_id))
                )
            category_join_conditions.append(or_(*handler_conds_cat))
        else:
            # DC Protocol Fix (Apr 2026): Also match source_ref_id for non-user-type sources
            all_conds_cat = [
                and_(CRMLead.primary_owner_type == 'staff', CRMLead.primary_owner_id == team_member_id),
                CRMLead.telecaller_id == team_member_id,
                CRMLead.field_staff_id == team_member_id,
            ]
            if target_emp_code_cat:
                all_conds_cat.append(CRMLead.mnr_handler_id == target_emp_code_cat)
                all_conds_cat.append(
                    and_(CRMLead.source_ref_type.in_(('staff', 'mnr', 'vgk')),
                         CRMLead.source_ref_id == str(team_member_id))
                )
            category_join_conditions.append(or_(*all_conds_cat))
    
    category_counts = db.query(
        SignupCategory.name, func.count(CRMLead.id)
    ).outerjoin(CRMLead, and_(*category_join_conditions)
    ).filter(SignupCategory.company_id == company_id).group_by(SignupCategory.name).all()
    
    today = get_indian_time().date()
    today_start = datetime.combine(today, datetime.min.time())
    today_end = datetime.combine(today, datetime.max.time())
    
    # DC Protocol (Jan 22, 2026): Apply date_filter to followup queries
    today_followups = db.query(CRMLeadFollowUp).join(CRMLead).filter(
        CRMLead.company_id == company_id,
        *team_filter,
        *date_filter,
        CRMLeadFollowUp.scheduled_date >= today_start,
        CRMLeadFollowUp.scheduled_date <= today_end,
        CRMLeadFollowUp.status == 'scheduled'
    ).count()
    
    overdue_followups = db.query(CRMLeadFollowUp).join(CRMLead).filter(
        CRMLead.company_id == company_id,
        *team_filter,
        *date_filter,
        CRMLeadFollowUp.scheduled_date < today_start,
        CRMLeadFollowUp.status == 'scheduled'
    ).count()
    
    this_month_start = today.replace(day=1)
    won_this_month = base_query.filter(
        CRMLead.status == 'won',
        CRMLead.actual_close_date >= this_month_start
    ).count()
    
    # Legacy deal value (backward compatibility) - DC Protocol (Jan 22, 2026): Apply date_filter
    total_deal_value = db.query(func.sum(CRMLead.deal_value)).filter(
        CRMLead.company_id == company_id,
        CRMLead.status == 'won',
        *team_filter,
        *date_filter
    ).scalar() or 0
    
    # Revenue Analytics (3-part deal value system) - DC Protocol (Jan 22, 2026): Apply date_filter
    revenue_stats = db.query(
        func.coalesce(func.sum(CRMLead.deal_value_total), 0).label('total'),
        func.coalesce(func.sum(CRMLead.deal_value_received), 0).label('received'),
        func.coalesce(func.sum(CRMLead.deal_value_balance), 0).label('balance')
    ).filter(
        CRMLead.company_id == company_id,
        CRMLead.status == 'won',
        *team_filter,
        *date_filter
    ).first()
    
    # Monthly revenue breakdown - DC Protocol (Jan 22, 2026): Apply date_filter
    monthly_revenue = db.query(
        func.coalesce(func.sum(CRMLead.deal_value_total), 0).label('total'),
        func.coalesce(func.sum(CRMLead.deal_value_received), 0).label('received'),
        func.coalesce(func.sum(CRMLead.deal_value_balance), 0).label('balance')
    ).filter(
        CRMLead.company_id == company_id,
        CRMLead.status == 'won',
        CRMLead.actual_close_date >= this_month_start,
        *team_filter,
        *date_filter
    ).first()
    
    return {
        'success': True,
        'data': {
            'total_leads': total_leads,
            'status_breakdown': {
                'new': status_map.get('new', 0),
                'contacted': status_map.get('contacted', 0),
                'interested': status_map.get('interested', 0),
                'qualified': status_map.get('qualified', 0),
                'proposal': status_map.get('proposal', 0),
                'loan_process': status_map.get('loan_process', 0),
                'won': status_map.get('won', 0),
                'processing': status_map.get('processing', 0),
                'completed': status_map.get('completed', 0),
                'lost': status_map.get('lost', 0),
                'on_hold': status_map.get('on_hold', 0)
            },
            'priority_breakdown': {
                'normal': priority_map.get('normal', 0),
                'medium': priority_map.get('medium', 0),
                'high': priority_map.get('high', 0),
            },
            'category_breakdown': {cat: count for cat, count in category_counts if cat},
            'today_followups': today_followups,
            'overdue_followups': overdue_followups,
            'won_this_month': won_this_month,
            'total_deal_value': total_deal_value,
            'revenue': {
                'total': float(revenue_stats.total) if revenue_stats else 0,
                'received': float(revenue_stats.received) if revenue_stats else 0,
                'balance': float(revenue_stats.balance) if revenue_stats else 0
            },
            'revenue_this_month': {
                'total': float(monthly_revenue.total) if monthly_revenue else 0,
                'received': float(monthly_revenue.received) if monthly_revenue else 0,
                'balance': float(monthly_revenue.balance) if monthly_revenue else 0
            }
        }
    }


@router.get("/staff-handler-dashboard")
def get_staff_handler_dashboard(
    company_id: int = Query(..., description="Company ID for DC Protocol"),
    team_member_id: Optional[int] = Query(None, description="DC Protocol (Jan 22, 2026): Filter by specific team member instead of current user"),
    db: Session = Depends(get_db),
    current_employee: StaffEmployee = Depends(get_current_staff_user)
):
    """DC Protocol (Jan 1, 2026): Get dashboard stats for leads where current user is a handler.
    DC Protocol (Jan 22, 2026): Added team_member_id to filter by specific team member.
    Returns counts for each handler type (telecaller, field_staff, mnr_handler)
    and aggregated stats for Staff Leads page.
    Note: Partner role excluded - OfficialPartner is a separate entity from staff."""
    
    # DC Protocol (Jan 22, 2026): Use team_member if provided, otherwise current_employee
    target_employee = current_employee
    if team_member_id:
        target_emp = db.query(StaffEmployee).filter(StaffEmployee.id == team_member_id).first()
        if target_emp:
            target_employee = target_emp
    
    # Base query with company filter
    base = db.query(CRMLead).filter(CRMLead.company_id == company_id)
    
    # Handler-based counts (staff can only be telecaller, field_staff, or mnr_handler)
    as_telecaller = base.filter(CRMLead.telecaller_id == target_employee.id).count()
    as_field_staff = base.filter(CRMLead.field_staff_id == target_employee.id).count()
    as_partner = 0  # Staff users are not partners - separate entity
    # DC Protocol Fix (Apr 2026): "As Ground Source" now also matches source_ref_id for
    # leads where the frontend stored the attribution via source_ref fields (partner/vendor/staff types).
    # For staff sources: source_ref_id stores the staff_employee.id (integer string).
    _staff_as_source_cond = and_(
        CRMLead.source_ref_type.in_(('staff', 'mnr', 'vgk')),
        CRMLead.source_ref_id == str(target_employee.id)
    )
    as_mnr_handler = base.filter(
        or_(
            CRMLead.mnr_handler_id == target_employee.emp_code,
            _staff_as_source_cond
        )
    ).count()

    # Any handler - leads where user is assigned as any staff handler type
    handler_conditions = [
        CRMLead.telecaller_id == target_employee.id,
        CRMLead.field_staff_id == target_employee.id,
        CRMLead.mnr_handler_id == target_employee.emp_code,
        _staff_as_source_cond,
    ]
    
    any_handler_query = base.filter(or_(*handler_conditions))
    total_as_handler = any_handler_query.count()
    
    # Status breakdown for handler leads
    status_counts = db.query(
        CRMLead.status, func.count(CRMLead.id)
    ).filter(
        CRMLead.company_id == company_id,
        or_(*handler_conditions)
    ).group_by(CRMLead.status).all()
    status_map = {status: count for status, count in status_counts}
    
    # Today/overdue followups for handler leads
    today = get_indian_time().date()
    today_start = datetime.combine(today, datetime.min.time())
    today_end = datetime.combine(today, datetime.max.time())
    
    today_followups = db.query(CRMLeadFollowUp).join(CRMLead).filter(
        CRMLead.company_id == company_id,
        or_(*handler_conditions),
        CRMLeadFollowUp.scheduled_date >= today_start,
        CRMLeadFollowUp.scheduled_date <= today_end,
        CRMLeadFollowUp.status == 'scheduled'
    ).count()
    
    overdue_followups = db.query(CRMLeadFollowUp).join(CRMLead).filter(
        CRMLead.company_id == company_id,
        or_(*handler_conditions),
        CRMLeadFollowUp.scheduled_date < today_start,
        CRMLeadFollowUp.status == 'scheduled'
    ).count()
    
    # Revenue stats based on primary ownership (not handler-based)
    # DC Protocol (Jan 1, 2026): User requested ownership-based revenue calculation
    # DC Protocol (Jan 22, 2026): Use target_employee instead of current_employee
    ownership_filter = and_(
        CRMLead.primary_owner_type == 'staff',
        CRMLead.primary_owner_id == target_employee.id
    )
    
    revenue_stats = db.query(
        func.coalesce(func.sum(CRMLead.deal_value_total), 0).label('total'),
        func.coalesce(func.sum(CRMLead.deal_value_received), 0).label('received'),
        func.coalesce(func.sum(CRMLead.deal_value_balance), 0).label('balance')
    ).filter(
        CRMLead.company_id == company_id,
        CRMLead.status == 'won',
        ownership_filter
    ).first()
    
    # This month revenue (ownership-based)
    this_month_start = today.replace(day=1)
    monthly_revenue = db.query(
        func.coalesce(func.sum(CRMLead.deal_value_total), 0).label('total'),
        func.coalesce(func.sum(CRMLead.deal_value_received), 0).label('received'),
        func.coalesce(func.sum(CRMLead.deal_value_balance), 0).label('balance')
    ).filter(
        CRMLead.company_id == company_id,
        CRMLead.status == 'won',
        CRMLead.actual_close_date >= this_month_start,
        ownership_filter
    ).first()
    
    # DC Protocol (Jan 7, 2026): Fresh Leads - only count truly unassigned leads
    # Exclude leads created by any staff/partner - those are not "fresh" as creator can assign
    unassigned_count = base.filter(
        CRMLead.handler_type == 'unassigned',
        or_(
            CRMLead.created_by_type.is_(None),
            ~CRMLead.created_by_type.in_(['staff', 'partner', 'mnr_user'])
        )
    ).count()
    
    # DC Protocol (Jan 7, 2026): All My Leads - where user is primary owner OR any handler
    # DC Protocol (Jan 22, 2026): Use target_employee instead of current_employee
    # Careful: emp_code can be None, so guard against it for mnr_handler comparison
    all_my_leads_conditions = [
        and_(CRMLead.primary_owner_type == 'staff', CRMLead.primary_owner_id == target_employee.id),
        CRMLead.telecaller_id == target_employee.id,
        CRMLead.field_staff_id == target_employee.id
    ]
    # Only include mnr_handler match if emp_code exists
    if target_employee.emp_code:
        all_my_leads_conditions.append(CRMLead.mnr_handler_id == target_employee.emp_code)
    
    all_my_leads_count = base.filter(or_(*all_my_leads_conditions)).count()
    
    # DC Protocol (Feb 2026): Self Leads - leads where source = 'Self Lead' AND assigned to this employee
    # This counts leads the employee added themselves from their own network
    self_leads_count = base.filter(
        CRMLead.source == SELF_LEAD_SOURCE_NAME,
        or_(*all_my_leads_conditions)
    ).count()
    
    # DC Protocol (Feb 2026): Company Leads = Leads assigned to employee MINUS their Self Leads
    # Shows leads that were assigned by the company (not self-generated)
    # all_my_leads_count = total leads assigned to this employee (owner OR handler)
    company_leads_count = all_my_leads_count - self_leads_count
    
    return {
        'success': True,
        'data': {
            'total_leads': total_as_handler,  # Keep as handler count for filter badges
            'all_my_leads_count': all_my_leads_count,  # DC Protocol (Jan 7, 2026): Owner + Handler combined
            'unassigned_count': unassigned_count,
            'self_leads_count': self_leads_count,
            'company_leads_count': company_leads_count,  # DC Protocol (Jan 7, 2026): Total leads in company
            'handler_breakdown': {
                'as_telecaller': as_telecaller,
                'as_field_staff': as_field_staff,
                'as_partner': as_partner,
                'as_mnr_handler': as_mnr_handler
            },
            'status_breakdown': {
                'new': status_map.get('new', 0),
                'contacted': status_map.get('contacted', 0),
                'interested': status_map.get('interested', 0),
                'qualified': status_map.get('qualified', 0),
                'proposal': status_map.get('proposal', 0),
                'loan_process': status_map.get('loan_process', 0),
                'won': status_map.get('won', 0),
                'processing': status_map.get('processing', 0),
                'completed': status_map.get('completed', 0),
                'lost': status_map.get('lost', 0),
                'on_hold': status_map.get('on_hold', 0)
            },
            'today_followups': today_followups,
            'overdue_followups': overdue_followups,
            'revenue': {
                'total': float(revenue_stats.total) if revenue_stats else 0,
                'received': float(revenue_stats.received) if revenue_stats else 0,
                'balance': float(revenue_stats.balance) if revenue_stats else 0
            },
            'revenue_this_month': {
                'total': float(monthly_revenue.total) if monthly_revenue else 0,
                'received': float(monthly_revenue.received) if monthly_revenue else 0,
                'balance': float(monthly_revenue.balance) if monthly_revenue else 0
            }
        }
    }


@router.get("/assignment-options")
def get_assignment_options(
    company_id: Optional[str] = Query(None, description="Company ID for DC Protocol (or 'all' for admins)"),
    employee_status: Optional[str] = Query(None, description="Filter by employee status: active, resigned, all (default: includes resigned with leads)"),
    db: Session = Depends(get_db),
    current_employee: StaffEmployee = Depends(get_current_staff_user)
):
    """
    DC Protocol: Get assignment options based on user role
    - Staff (no reports): Returns is_leader=False, must assign to self
    - Leader (has reports): Returns is_leader=True with team members list
    - VGK4U Supreme: Returns is_leader=True (all-access bypass)
    
    DC Protocol (Jan 28, 2026): Employee status filter
    - Default: Returns active employees + resigned employees who still have leads
    - employee_status=active: Only active employees
    - employee_status=resigned: Only resigned employees
    - employee_status=all: All employees regardless of status
    
    DC Protocol (Feb 1, 2026): company_id now accepts 'all' string for admin multi-company view
    """
    staff_type = (current_employee.staff_type or '').upper()
    is_admin = is_vgk_admin(staff_type)
    has_reports = has_direct_reports(current_employee.id, db, StaffEmployee)
    is_leader = has_reports or is_admin
    
    # DC Protocol (Feb 1, 2026): Handle "all" company filter for admins
    is_all_companies = company_id and company_id.lower() == 'all'
    parsed_company_id = None
    if company_id and not is_all_companies:
        try:
            parsed_company_id = int(company_id)
        except (ValueError, TypeError):
            raise HTTPException(status_code=422, detail="company_id must be a valid integer or 'all'")
    
    hidden_ids = _get_hidden_employee_ids(db, StaffEmployee)
    team_members = []
    if has_reports or is_admin:
        downline_ids = get_recursive_downline(
            current_employee.id, db, StaffEmployee, include_manager=False
        )
        downline_ids = [eid for eid in downline_ids if eid not in hidden_ids]
        
        if employee_status == 'active':
            team_employees = db.query(StaffEmployee).filter(
                StaffEmployee.id.in_(downline_ids),
                StaffEmployee.status == 'active'
            ).all()
        elif employee_status == 'resigned':
            team_employees = db.query(StaffEmployee).filter(
                StaffEmployee.id.in_(downline_ids),
                StaffEmployee.status == 'resigned'
            ).all()
        elif employee_status == 'all':
            team_employees = db.query(StaffEmployee).filter(
                StaffEmployee.id.in_(downline_ids)
            ).all()
        else:
            active_employees = db.query(StaffEmployee).filter(
                StaffEmployee.id.in_(downline_ids),
                StaffEmployee.status == 'active'
            ).all()
            
            resigned_emp_codes = db.query(StaffEmployee.emp_code).filter(
                StaffEmployee.id.in_(downline_ids),
                StaffEmployee.status == 'resigned'
            ).all()
            resigned_codes = [e[0] for e in resigned_emp_codes]
            
            resigned_with_leads_codes = []
            if resigned_codes:
                leads_with_resigned = db.query(CRMLead.handler_id).filter(
                    CRMLead.handler_type == 'staff',
                    CRMLead.handler_id.in_(resigned_codes)
                ).distinct().all()
                resigned_with_leads_codes = [l[0] for l in leads_with_resigned]
            
            resigned_with_leads = []
            if resigned_with_leads_codes:
                resigned_with_leads = db.query(StaffEmployee).filter(
                    StaffEmployee.emp_code.in_(resigned_with_leads_codes),
                    StaffEmployee.id.in_(downline_ids)
                ).all()
            
            team_employees = list(active_employees) + list(resigned_with_leads)
        
        team_members = [{
            'id': emp.id,
            'employee_id': emp.emp_code,
            'name': emp.full_name,
            'department': emp.department.name if emp.department else None,
            'status': emp.status or 'active',
            'is_active': emp.status == 'active',
            'display_name': f"{emp.full_name}" + (f" (Resigned)" if emp.status == 'resigned' else "")
        } for emp in team_employees]
        
        team_members.sort(key=lambda x: (0 if x['is_active'] else 1, x['name']))
    
    return {
        'success': True,
        'data': {
            'is_leader': is_leader,
            'is_admin': is_admin,
            'current_user': {
                'id': current_employee.id,
                'employee_id': current_employee.emp_code,
                'name': current_employee.full_name,
                'staff_type': current_employee.staff_type
            },
            'team_members': team_members
        }
    }


@router.get("/my-dashboard")
def get_my_crm_dashboard(
    company_id: Optional[int] = Query(None, description="Company ID for DC Protocol — defaults to caller's own company"),
    scope: str = Query("my", description="Scope: 'my' for own leads, 'team' for team leads, 'all' for both"),
    db: Session = Depends(get_db),
    current_employee: StaffEmployee = Depends(get_current_staff_user)
):
    """
    DC Protocol: Get CRM dashboard statistics for current user
    Scope-aware: my leads, team leads, or all
    company_id defaults to the authenticated user's own base_company_id when not supplied.
    """
    # DC Protocol (Mar 23, 2026): company_id made optional — fall back to caller's own company
    # to prevent 422 Validation Errors from callers that omit the parameter.
    if not company_id:
        company_id = current_employee.base_company_id
    is_leader = has_direct_reports(current_employee.id, db, StaffEmployee)
    
    # DC Protocol: Menu-based access control - page assignment = full access
    # if scope in ['team', 'all'] and not is_leader:
    #     raise HTTPException(
    #         status_code=403,
    #         detail="Team and All scopes are only available to leaders with direct reports"
    #     )
    
    handler_ids = []
    if scope == 'my':
        handler_ids = [current_employee.emp_code]
    elif scope == 'team' and is_leader:
        downline_ids = get_recursive_downline(
            current_employee.id, db, StaffEmployee, include_manager=False
        )
        hidden_ids = _get_hidden_employee_ids(db, StaffEmployee)
        downline_ids = [eid for eid in downline_ids if eid not in hidden_ids]
        team_employees = db.query(StaffEmployee).filter(
            StaffEmployee.id.in_(downline_ids)
        ).all()
        handler_ids = [emp.emp_code for emp in team_employees]
    else:
        downline_ids = get_recursive_downline(
            current_employee.id, db, StaffEmployee, include_manager=False
        )
        hidden_ids = _get_hidden_employee_ids(db, StaffEmployee)
        downline_ids = [eid for eid in downline_ids if eid not in hidden_ids]
        team_employees = db.query(StaffEmployee).filter(
            StaffEmployee.id.in_(downline_ids)
        ).all()
        handler_ids = [emp.emp_code for emp in team_employees]
    
    base_query = db.query(CRMLead).filter(
        CRMLead.company_id == company_id,
        CRMLead.handler_type == 'staff',
        CRMLead.handler_id.in_(handler_ids)
    )
    
    total_leads = base_query.count()
    
    status_counts = db.query(
        CRMLead.status, func.count(CRMLead.id)
    ).filter(
        CRMLead.company_id == company_id,
        CRMLead.handler_type == 'staff',
        CRMLead.handler_id.in_(handler_ids)
    ).group_by(CRMLead.status).all()
    
    status_map = {status: count for status, count in status_counts}
    
    priority_counts = db.query(
        CRMLead.priority, func.count(CRMLead.id)
    ).filter(
        CRMLead.company_id == company_id,
        CRMLead.handler_type == 'staff',
        CRMLead.handler_id.in_(handler_ids)
    ).group_by(CRMLead.priority).all()
    
    priority_map = {priority: count for priority, count in priority_counts}
    
    today = get_indian_time().date()
    today_start = datetime.combine(today, datetime.min.time())
    today_end = datetime.combine(today, datetime.max.time())
    
    today_followups = db.query(CRMLeadFollowUp).join(CRMLead).filter(
        CRMLead.company_id == company_id,
        CRMLead.handler_type == 'staff',
        CRMLead.handler_id.in_(handler_ids),
        CRMLeadFollowUp.scheduled_date >= today_start,
        CRMLeadFollowUp.scheduled_date <= today_end,
        CRMLeadFollowUp.status == 'scheduled'
    ).count()
    
    overdue_followups = db.query(CRMLeadFollowUp).join(CRMLead).filter(
        CRMLead.company_id == company_id,
        CRMLead.handler_type == 'staff',
        CRMLead.handler_id.in_(handler_ids),
        CRMLeadFollowUp.scheduled_date < today_start,
        CRMLeadFollowUp.status == 'scheduled'
    ).count()
    
    this_month_start = today.replace(day=1)
    won_this_month = base_query.filter(
        CRMLead.status == 'won',
        CRMLead.actual_close_date >= this_month_start
    ).count()
    
    total_deal_value = db.query(func.sum(CRMLead.deal_value)).filter(
        CRMLead.company_id == company_id,
        CRMLead.handler_type == 'staff',
        CRMLead.handler_id.in_(handler_ids),
        CRMLead.status == 'won'
    ).scalar() or 0
    
    team_breakdown = []
    if is_leader and scope in ['team', 'all']:
        for handler_id in handler_ids:
            if handler_id == current_employee.emp_code and scope == 'team':
                continue
            emp = db.query(StaffEmployee).filter(
                StaffEmployee.emp_code == handler_id
            ).first()
            if emp:
                emp_leads = db.query(CRMLead).filter(
                    CRMLead.company_id == company_id,
                    CRMLead.handler_type == 'staff',
                    CRMLead.handler_id == handler_id
                ).count()
                emp_won = db.query(CRMLead).filter(
                    CRMLead.company_id == company_id,
                    CRMLead.handler_type == 'staff',
                    CRMLead.handler_id == handler_id,
                    CRMLead.status == 'won'
                ).count()
                team_breakdown.append({
                    'employee_id': handler_id,
                    'name': emp.full_name,
                    'total_leads': emp_leads,
                    'won_leads': emp_won
                })
    
    return {
        'success': True,
        'data': {
            'is_leader': is_leader,
            'scope': scope,
            'total_leads': total_leads,
            'status_breakdown': {
                'new': status_map.get('new', 0),
                'contacted': status_map.get('contacted', 0),
                'interested': status_map.get('interested', 0),
                'qualified': status_map.get('qualified', 0),
                'proposal': status_map.get('proposal', 0),
                'loan_process': status_map.get('loan_process', 0),
                'won': status_map.get('won', 0),
                'processing': status_map.get('processing', 0),
                'completed': status_map.get('completed', 0),
                'lost': status_map.get('lost', 0),
                'on_hold': status_map.get('on_hold', 0)
            },
            'priority_breakdown': {
                'normal': priority_map.get('normal', 0),
                'medium': priority_map.get('medium', 0),
                'high': priority_map.get('high', 0),
            },
            'today_followups': today_followups,
            'overdue_followups': overdue_followups,
            'won_this_month': won_this_month,
            'total_deal_value': total_deal_value,
            'team_breakdown': team_breakdown
        }
    }


@router.get("/performance-summary")
def get_performance_summary(
    company_id: Optional[int] = Query(None, description="Company ID (0 or None for all companies - VGK/EA/Key Leadership only)"),
    scope: str = Query("my", description="Scope: 'my', 'team', or 'all'"),
    start_date: Optional[str] = Query(None, description="Start date YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="End date YYYY-MM-DD"),
    source_id: Optional[int] = Query(None, description="Lead source filter"),
    category_id: Optional[int] = Query(None, description="Category filter"),
    manager_id: Optional[int] = Query(None, description="Team manager filter (leaders only)"),
    db: Session = Depends(get_db),
    current_employee: StaffEmployee = Depends(get_current_staff_user)
):
    """
    DC Protocol (Jan 1, 2026): Get CRM performance summary with employee-wise breakdown
    Provides aggregated statistics for dashboard overview table
    
    Updated to check primary_owner_id, telecaller_id, field_staff_id columns
    instead of legacy handler_id field.
    
    Scopes:
    - 'my': Only logged-in user's leads (as owner OR handler)
    - 'team': Downline members' leads
    - 'all': Cross-company, all levels (VGK/EA/Key Leadership only)
    """
    staff_type = (current_employee.staff_type or '').upper()
    is_admin = is_vgk_admin(staff_type)
    is_leader = has_direct_reports(current_employee.id, db, StaffEmployee)
    
    all_companies_mode = company_id is None or company_id == 0
    # DC Protocol: Menu-based access control - page assignment = full access
    # if all_companies_mode and not is_admin:
    #     raise HTTPException(
    #         status_code=403,
    #         detail="All Companies view is only available to VGK/EA/Key Leadership"
    #     )
    
    # DC Protocol: Menu-based access control - page assignment = full access
    # if scope == 'all' and not is_admin:
    #     raise HTTPException(
    #         status_code=403,
    #         detail="All Performance scope is only available to VGK/EA/Key Leadership"
    #     )
    
    # DC Protocol: Menu-based access control - page assignment = full access
    # if scope == 'team' and not is_leader and not is_admin:
    #     raise HTTPException(
    #         status_code=403,
    #         detail="Team scope requires direct reports or admin privileges"
    #     )
    
    hidden_ids = _get_hidden_employee_ids(db, StaffEmployee)
    employees_to_include = []
    if scope == 'my':
        employees_to_include = [current_employee]
    elif scope == 'team':
        if manager_id:
            downline_ids = get_recursive_downline(manager_id, db, StaffEmployee, include_manager=False)
        else:
            downline_ids = get_recursive_downline(current_employee.id, db, StaffEmployee, include_manager=False)
        downline_ids = [eid for eid in downline_ids if eid not in hidden_ids]
        employees_to_include = db.query(StaffEmployee).filter(
            StaffEmployee.id.in_(downline_ids),
            StaffEmployee.status == 'active'
        ).all()
    elif scope == 'all':
        if is_admin:
            all_emps = db.query(StaffEmployee).filter(
                StaffEmployee.status == 'active'
            ).order_by(StaffEmployee.full_name).all()
            employees_to_include = [e for e in all_emps if e.id not in hidden_ids]
        else:
            downline_ids = get_recursive_downline(current_employee.id, db, StaffEmployee, include_manager=False)
            downline_ids = [eid for eid in downline_ids if eid not in hidden_ids]
            employees_to_include = db.query(StaffEmployee).filter(
                StaffEmployee.id.in_(downline_ids),
                StaffEmployee.status == 'active'
            ).all()
    
    date_start = None
    date_end = None
    if start_date:
        try:
            date_start = datetime.strptime(start_date, "%Y-%m-%d")
        except ValueError:
            pass
    if end_date:
        try:
            date_end = datetime.strptime(end_date, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
        except ValueError:
            pass
    
    performance_data = []
    total_summary = {
        'new_leads': 0, 'overall_leads': 0, 'self_generated_leads': 0,
        'in_progress': 0, 'deal_closed': 0, 'on_hold': 0, 'lost_leads': 0,
        'revenue_generated': 0, 'revenue_lost': 0
    }
    
    def build_employee_lead_filter(emp_id):
        """Build filter for leads where employee is owner OR handler"""
        return or_(
            CRMLead.primary_owner_id == emp_id,
            CRMLead.telecaller_id == emp_id,
            CRMLead.field_staff_id == emp_id
        )
    
    for idx, emp in enumerate(employees_to_include):
        base_query = db.query(CRMLead).filter(build_employee_lead_filter(emp.id))
        
        if not all_companies_mode:
            base_query = base_query.filter(CRMLead.company_id == company_id)
        
        if date_start:
            base_query = base_query.filter(CRMLead.created_at >= date_start)
        if date_end:
            base_query = base_query.filter(CRMLead.created_at <= date_end)
        if source_id:
            source = db.query(CRMLeadSource).filter(CRMLeadSource.id == source_id).first()
            if source:
                base_query = base_query.filter(CRMLead.source == source.name)
        if category_id:
            base_query = base_query.filter(CRMLead.category_id == category_id)
        
        overall_leads = base_query.count()
        new_leads = base_query.filter(CRMLead.status == 'new').count()
        
        self_generated_query = db.query(CRMLead).filter(
            CRMLead.primary_owner_id == emp.id,
            CRMLead.created_by_type == 'staff',
            CRMLead.created_by_id == emp.emp_code
        )
        if not all_companies_mode:
            self_generated_query = self_generated_query.filter(CRMLead.company_id == company_id)
        if date_start:
            self_generated_query = self_generated_query.filter(CRMLead.created_at >= date_start)
        if date_end:
            self_generated_query = self_generated_query.filter(CRMLead.created_at <= date_end)
        self_generated_count = self_generated_query.count()
        
        in_progress = base_query.filter(
            CRMLead.status.in_(['contacted', 'interested', 'qualified', 'proposal'])
        ).count()
        deal_closed = base_query.filter(CRMLead.status == 'won').count()
        on_hold = base_query.filter(CRMLead.status == 'on_hold').count()
        lost_leads = base_query.filter(CRMLead.status == 'lost').count()
        
        revenue_query = db.query(func.coalesce(func.sum(CRMLead.deal_value), 0)).filter(
            build_employee_lead_filter(emp.id),
            CRMLead.status == 'won'
        )
        if not all_companies_mode:
            revenue_query = revenue_query.filter(CRMLead.company_id == company_id)
        if date_start:
            revenue_query = revenue_query.filter(CRMLead.created_at >= date_start)
        if date_end:
            revenue_query = revenue_query.filter(CRMLead.created_at <= date_end)
        revenue_generated_value = float(revenue_query.scalar() or 0)
        
        lost_query = db.query(func.coalesce(func.sum(CRMLead.deal_value), 0)).filter(
            build_employee_lead_filter(emp.id),
            CRMLead.status == 'lost'
        )
        if not all_companies_mode:
            lost_query = lost_query.filter(CRMLead.company_id == company_id)
        if date_start:
            lost_query = lost_query.filter(CRMLead.created_at >= date_start)
        if date_end:
            lost_query = lost_query.filter(CRMLead.created_at <= date_end)
        revenue_lost_value = float(lost_query.scalar() or 0)
        
        emp_data = {
            'sno': idx + 1,
            'employee_id': emp.emp_code,
            'employee_name': emp.full_name,
            'overall': {
                'new_leads': new_leads,
                'overall_leads': overall_leads,
                'self_generated_leads': self_generated_count
            },
            'status_wise': {
                'in_progress': in_progress,
                'deal_closed': deal_closed,
                'on_hold': on_hold,
                'lost_leads': lost_leads
            },
            'revenue': {
                'generated': revenue_generated_value,
                'lost': revenue_lost_value
            }
        }
        performance_data.append(emp_data)
        
        total_summary['new_leads'] += new_leads
        total_summary['overall_leads'] += overall_leads
        total_summary['self_generated_leads'] += self_generated_count
        total_summary['in_progress'] += in_progress
        total_summary['deal_closed'] += deal_closed
        total_summary['on_hold'] += on_hold
        total_summary['lost_leads'] += lost_leads
        total_summary['revenue_generated'] += revenue_generated_value
        total_summary['revenue_lost'] += revenue_lost_value
    
    managers = []
    if is_leader:
        downline_ids = get_recursive_downline(
            current_employee.id, db, StaffEmployee, include_manager=False
        )
        downline_ids = [eid for eid in downline_ids if eid not in hidden_ids]
        manager_employees = db.query(StaffEmployee).filter(
            StaffEmployee.id.in_(downline_ids),
            StaffEmployee.status == 'active'
        ).all()
        for m in manager_employees:
            if has_direct_reports(m.id, db, StaffEmployee):
                managers.append({
                    'id': m.id,
                    'employee_id': m.emp_code,
                    'name': m.full_name
                })
    
    return {
        'success': True,
        'data': {
            'is_leader': is_leader,
            'scope': scope,
            'filters_applied': {
                'start_date': start_date,
                'end_date': end_date,
                'source_id': source_id,
                'category_id': category_id,
                'manager_id': manager_id
            },
            'performance': performance_data,
            'totals': total_summary,
            'available_managers': managers
        }
    }


@router.get("/team-performance-breakdown")
def get_team_performance_breakdown(
    company_id: str = Query(..., description="Company ID for DC Protocol (or 'all' for admins)"),
    start_date: Optional[str] = Query(None, description="Start date YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="End date YYYY-MM-DD"),
    department_id: Optional[int] = Query(None, description="Filter by department"),
    manager_id: Optional[int] = Query(None, description="Filter by reporting manager"),
    employee_search: Optional[str] = Query(None, description="Search by employee name"),
    db: Session = Depends(get_db),
    current_employee: StaffEmployee = Depends(get_current_staff_user)
):
    """
    DC Protocol (Jan 22, 2026): Team Performance Breakdown - Side-by-Side View
    OPTIMIZED: Uses batch queries instead of per-employee queries to prevent timeout
    Shows each team member with their stats as Primary Owner and as Handler in one row
    """
    staff_type = (current_employee.staff_type or '').upper()
    is_admin = is_vgk_admin(staff_type)
    is_leader = has_direct_reports(current_employee.id, db, StaffEmployee)
    
    # DC Protocol: Handle "all" company filter for admins
    is_all_companies_request = company_id.lower() == 'all'
    show_all_companies = is_all_companies_request and is_admin
    
    # DC Protocol: Menu-based access control - page assignment = full access
    # if is_all_companies_request and not is_admin:
    #     raise HTTPException(status_code=403, detail="Only admins can view all companies")
    
    parsed_company_id = None if show_all_companies else int(company_id)
    
    hidden_ids = _get_hidden_employee_ids(db, StaffEmployee)
    employees_to_include = []
    
    if manager_id:
        downline_ids = get_recursive_downline(manager_id, db, StaffEmployee, include_manager=False)
        downline_ids = [eid for eid in downline_ids if eid not in hidden_ids]
        employees_to_include = db.query(StaffEmployee).filter(
            StaffEmployee.id.in_(downline_ids),
            StaffEmployee.status == 'active'
        ).all()
    elif is_admin:
        query = db.query(StaffEmployee).filter(StaffEmployee.status == 'active')
        if not show_all_companies:
            query = query.filter(
                or_(
                    StaffEmployee.base_company_id == parsed_company_id,
                    StaffEmployee.data_companies.contains([parsed_company_id])
                )
            )
        if show_all_companies:
            all_emps = query.order_by(StaffEmployee.full_name).limit(50).all()
        else:
            all_emps = query.order_by(StaffEmployee.full_name).all()
        employees_to_include = [e for e in all_emps if e.id not in hidden_ids]
    elif is_leader:
        downline_ids = get_recursive_downline(current_employee.id, db, StaffEmployee, include_manager=False)
        downline_ids = [eid for eid in downline_ids if eid not in hidden_ids]
        employees_to_include = db.query(StaffEmployee).filter(
            StaffEmployee.id.in_(downline_ids),
            StaffEmployee.status == 'active'
        ).all()
    else:
        employees_to_include = [current_employee]
    
    if department_id:
        employees_to_include = [e for e in employees_to_include if e.department_id == department_id]
    
    if employee_search:
        search_term = employee_search.lower()
        employees_to_include = [e for e in employees_to_include if search_term in e.full_name.lower()]
    
    # Parse dates
    date_start = None
    date_end = None
    if start_date:
        try:
            date_start = datetime.strptime(start_date, "%Y-%m-%d")
        except ValueError:
            pass
    if end_date:
        try:
            date_end = datetime.strptime(end_date, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
        except ValueError:
            pass
    
    # DC Protocol (Jan 22, 2026): BATCH QUERY OPTIMIZATION
    # Pre-fetch all reporting managers in one query
    manager_ids = list(set(e.reporting_manager_id for e in employees_to_include if e.reporting_manager_id))
    manager_map = {}
    if manager_ids:
        managers_data = db.query(StaffEmployee.id, StaffEmployee.full_name).filter(
            StaffEmployee.id.in_(manager_ids)
        ).all()
        manager_map = {m.id: m.full_name for m in managers_data}
    
    # Get employee IDs and emp_codes for batch CRM queries
    emp_ids = [e.id for e in employees_to_include]
    emp_codes = [e.emp_code for e in employees_to_include if e.emp_code]
    
    # Build base date filter for all CRM queries
    def apply_date_filters(query):
        if not show_all_companies:
            query = query.filter(CRMLead.company_id == parsed_company_id)
        if date_start:
            query = query.filter(CRMLead.created_at >= date_start)
        if date_end:
            query = query.filter(CRMLead.created_at <= date_end)
        return query
    
    # BATCH QUERY: Get owner stats grouped by primary_owner_id and status
    owner_stats_query = apply_date_filters(
        db.query(
            CRMLead.primary_owner_id,
            CRMLead.status,
            func.count(CRMLead.id).label('count'),
            func.coalesce(func.sum(CRMLead.deal_value_total), 0).label('revenue_total'),
            func.coalesce(func.sum(CRMLead.deal_value_received), 0).label('revenue_received'),
            func.coalesce(func.sum(CRMLead.deal_value_balance), 0).label('revenue_balance')
        ).filter(
            CRMLead.primary_owner_type == 'staff',
            CRMLead.primary_owner_id.in_(emp_ids)
        )
    ).group_by(CRMLead.primary_owner_id, CRMLead.status)
    
    owner_stats_raw = owner_stats_query.all()
    
    # Build owner stats map: {emp_id: {status: count, ...}}
    owner_stats_map = {}
    owner_revenue_map = {}
    for row in owner_stats_raw:
        emp_id = row.primary_owner_id
        if emp_id not in owner_stats_map:
            owner_stats_map[emp_id] = {}
            owner_revenue_map[emp_id] = {'revenue_total': 0, 'revenue_received': 0, 'revenue_balance': 0}
        owner_stats_map[emp_id][row.status] = row.count
        owner_revenue_map[emp_id]['revenue_total'] += float(row.revenue_total or 0)
        owner_revenue_map[emp_id]['revenue_received'] += float(row.revenue_received or 0)
        owner_revenue_map[emp_id]['revenue_balance'] += float(row.revenue_balance or 0)
    
    # BATCH QUERY: Get handler stats (telecaller/field_staff by ID, mnr_handler by emp_code)
    handler_stats_query = apply_date_filters(
        db.query(
            CRMLead.telecaller_id,
            CRMLead.field_staff_id,
            CRMLead.mnr_handler_id,
            CRMLead.status,
            func.count(CRMLead.id).label('count'),
            func.coalesce(func.sum(CRMLead.deal_value_total), 0).label('revenue_total'),
            func.coalesce(func.sum(CRMLead.deal_value_received), 0).label('revenue_received'),
            func.coalesce(func.sum(CRMLead.deal_value_balance), 0).label('revenue_balance')
        ).filter(
            or_(
                CRMLead.telecaller_id.in_(emp_ids),
                CRMLead.field_staff_id.in_(emp_ids),
                CRMLead.mnr_handler_id.in_(emp_codes) if emp_codes else False
            )
        )
    ).group_by(CRMLead.telecaller_id, CRMLead.field_staff_id, CRMLead.mnr_handler_id, CRMLead.status)
    
    handler_stats_raw = handler_stats_query.all()
    
    # Build handler stats map
    handler_stats_map = {}
    handler_revenue_map = {}
    emp_code_to_id = {e.emp_code: e.id for e in employees_to_include if e.emp_code}
    
    for row in handler_stats_raw:
        matched_ids = set()
        if row.telecaller_id in emp_ids:
            matched_ids.add(row.telecaller_id)
        if row.field_staff_id in emp_ids:
            matched_ids.add(row.field_staff_id)
        if row.mnr_handler_id and row.mnr_handler_id in emp_code_to_id:
            matched_ids.add(emp_code_to_id[row.mnr_handler_id])
        
        for emp_id in matched_ids:
            if emp_id not in handler_stats_map:
                handler_stats_map[emp_id] = {}
                handler_revenue_map[emp_id] = {'revenue_total': 0, 'revenue_received': 0, 'revenue_balance': 0}
            if row.status not in handler_stats_map[emp_id]:
                handler_stats_map[emp_id][row.status] = 0
            handler_stats_map[emp_id][row.status] += row.count
            handler_revenue_map[emp_id]['revenue_total'] += float(row.revenue_total or 0)
            handler_revenue_map[emp_id]['revenue_received'] += float(row.revenue_received or 0)
            handler_revenue_map[emp_id]['revenue_balance'] += float(row.revenue_balance or 0)
    
    # Helper to extract status counts from map
    def extract_stats(stats_map, revenue_map, emp_id):
        stats = stats_map.get(emp_id, {})
        revenue = revenue_map.get(emp_id, {'revenue_total': 0, 'revenue_received': 0, 'revenue_balance': 0})
        qualified_statuses = ['interested', 'qualified', 'proposal']
        return {
            'new': stats.get('new', 0),
            'contacted': stats.get('contacted', 0),
            'qualified': sum(stats.get(s, 0) for s in qualified_statuses),
            'won': stats.get('won', 0),
            'lost': stats.get('lost', 0),
            'on_hold': stats.get('on_hold', 0),
            'total': sum(stats.values()),
            'revenue_total': revenue['revenue_total'],
            'revenue_received': revenue['revenue_received'],
            'revenue_balance': revenue['revenue_balance']
        }
    
    # DC Protocol: Fetch avg_daily_talk_time from call tracking, respecting the endpoint's date params
    call_talk_map = {}
    if emp_ids:
        try:
            from datetime import date as _date
            call_date_from = start_date or (_date.today() - timedelta(days=30)).strftime('%Y-%m-%d')
            call_date_to = end_date or _date.today().strftime('%Y-%m-%d')
            call_stats = db.query(
                StaffCallLog.staff_id,
                func.sum(StaffCallLog.duration_seconds).label('total_dur'),
                func.count(func.distinct(StaffCallLog.call_date)).label('active_days'),
                func.count(StaffCallLog.id).label('total_calls')
            ).filter(
                StaffCallLog.staff_id.in_(emp_ids),
                StaffCallLog.call_date >= call_date_from,
                StaffCallLog.call_date <= call_date_to
            ).group_by(StaffCallLog.staff_id).all()
            for cs in call_stats:
                days = max(cs.active_days or 1, 1)
                call_talk_map[cs.staff_id] = {
                    'avg_daily_talk_time': int(cs.total_dur or 0) // days,
                    'total_calls': cs.total_calls or 0
                }
        except Exception:
            pass

    # Build performance data
    performance_data = []
    owner_totals = {'new': 0, 'contacted': 0, 'qualified': 0, 'won': 0, 'lost': 0, 'on_hold': 0, 'total': 0, 'revenue_total': 0, 'revenue_received': 0, 'revenue_balance': 0}
    handler_totals = {'new': 0, 'contacted': 0, 'qualified': 0, 'won': 0, 'lost': 0, 'on_hold': 0, 'total': 0, 'revenue_total': 0, 'revenue_received': 0, 'revenue_balance': 0}
    
    for idx, emp in enumerate(employees_to_include):
        owner_data = extract_stats(owner_stats_map, owner_revenue_map, emp.id)
        handler_data = extract_stats(handler_stats_map, handler_revenue_map, emp.id)
        call_info = call_talk_map.get(emp.id, {})
        
        emp_data = {
            'sno': idx + 1,
            'employee_id': emp.id,
            'emp_code': emp.emp_code,
            'employee_name': emp.full_name,
            'reporting_manager': manager_map.get(emp.reporting_manager_id),
            'is_self': emp.id == current_employee.id,
            'as_primary_owner': owner_data,
            'as_handler': handler_data,
            'avg_daily_talk_time': call_info.get('avg_daily_talk_time', 0),
            'total_calls': call_info.get('total_calls', 0),
        }
        performance_data.append(emp_data)
        
        for key in owner_totals.keys():
            owner_totals[key] += owner_data.get(key, 0)
            handler_totals[key] += handler_data.get(key, 0)
    
    # Get available managers for filter dropdown (pre-computed direct reports)
    managers = []
    if is_leader or is_admin:
        if is_admin:
            manager_query = db.query(StaffEmployee).filter(StaffEmployee.status == 'active')
            if not show_all_companies:
                manager_query = manager_query.filter(
                    or_(
                        StaffEmployee.base_company_id == parsed_company_id,
                        StaffEmployee.data_companies.contains([parsed_company_id])
                    )
                )
        else:
            downline_ids = get_recursive_downline(current_employee.id, db, StaffEmployee, include_manager=False)
            hidden_ids_mgr = _get_hidden_employee_ids(db, StaffEmployee)
            downline_ids = [eid for eid in downline_ids if eid not in hidden_ids_mgr]
            manager_query = db.query(StaffEmployee).filter(
                StaffEmployee.id.in_(downline_ids),
                StaffEmployee.status == 'active'
            )
        
        manager_results = manager_query.limit(50).all() if show_all_companies else manager_query.all()
        
        # Batch check for direct reports
        if manager_results:
            manager_candidate_ids = [m.id for m in manager_results]
            direct_report_counts = db.query(
                StaffEmployee.reporting_manager_id,
                func.count(StaffEmployee.id)
            ).filter(
                StaffEmployee.reporting_manager_id.in_(manager_candidate_ids),
                StaffEmployee.status == 'active'
            ).group_by(StaffEmployee.reporting_manager_id).all()
            
            has_reports_set = {row[0] for row in direct_report_counts if row[1] > 0}
            
            for m in manager_results:
                if m.id in has_reports_set:
                    managers.append({
                        'id': m.id,
                        'employee_id': m.emp_code,
                        'name': m.full_name
                    })
    
    results_limited = show_all_companies and len(employees_to_include) >= 50
    
    return {
        'success': True,
        'data': {
            'is_leader': is_leader,
            'is_admin': is_admin,
            'results_limited': results_limited,
            'results_limit_message': 'Showing first 50 employees across all companies' if results_limited else None,
            'filters_applied': {
                'start_date': start_date,
                'end_date': end_date,
                'manager_id': manager_id,
                'employee_search': employee_search
            },
            'performance': performance_data,
            'owner_totals': owner_totals,
            'handler_totals': handler_totals,
            'available_managers': managers,
            'employee_count': len(performance_data)
        }
    }


@router.get("/departments-list")
def crm_departments_list(
    db: Session = Depends(get_db),
    current_employee: StaffEmployee = Depends(get_current_staff_user)
):
    from app.models.staff import StaffDepartment
    depts = db.query(StaffDepartment).filter(StaffDepartment.is_active == True).order_by(StaffDepartment.name).all()
    return {"success": True, "departments": [{"id": d.id, "name": d.name} for d in depts]}


def _crm_assignment_filter(emp_id: int, emp_code: str):
    """
    DC_OVERDUE_FIX: Shared OR-based assignment filter that matches the Auto Dialer logic.
    Returns a SQLAlchemy OR condition matching leads where the employee is assigned as:
      - handler (handler_type='staff' AND handler_id=emp_code)
      - telecaller (telecaller_id=emp_id)
      - field staff (field_staff_id=emp_id)
      - primary owner (primary_owner_type='staff' AND primary_owner_id=emp_id)
    Use this wherever overdue counts are computed to keep all endpoints consistent.
    NOTE: Status exclusion lists differ across endpoints (won/completed/lost in crm.py,
    won/lost/dropped/completed in staff_progress.py, plus do_not_call in the dialer).
    Each caller retains its existing exclusion list until the team decides to harmonize.
    """
    return or_(
        and_(CRMLead.handler_type == 'staff', CRMLead.handler_id == emp_code),
        CRMLead.telecaller_id == emp_id,
        CRMLead.field_staff_id == emp_id,
        and_(CRMLead.primary_owner_type == 'staff', CRMLead.primary_owner_id == emp_id),
    )


def _crm_assignment_filter_for_team(emp_ids: list, emp_codes: list):
    """
    DC_OVERDUE_FIX: OR-based assignment filter for a team of employees.
    Returns a SQLAlchemy OR condition matching leads where ANY of the employees
    in the list is assigned via any of the four assignment fields.
    Used for aggregate (category-wise, company-wise) overdue counts across a team.
    """
    return or_(
        and_(CRMLead.handler_type == 'staff', CRMLead.handler_id.in_(emp_codes)),
        CRMLead.telecaller_id.in_(emp_ids),
        CRMLead.field_staff_id.in_(emp_ids),
        and_(CRMLead.primary_owner_type == 'staff', CRMLead.primary_owner_id.in_(emp_ids)),
    )


@router.get("/dashboard-v2")
def get_crm_dashboard_v2(
    company_id: Optional[int] = Query(None, description="Company ID filter (optional for admins)"),
    department_id: Optional[int] = Query(None, description="Department ID filter"),
    start_date: Optional[str] = Query(None, description="Start date YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="End date YYYY-MM-DD"),
    status: Optional[str] = Query(None, description="Status filter"),
    priority: Optional[str] = Query(None, description="Priority filter"),
    category_id: Optional[int] = Query(None, description="Category ID filter"),
    db: Session = Depends(get_db),
    current_employee: StaffEmployee = Depends(get_current_staff_user)
):
    is_admin = is_vgk_admin(current_employee.staff_type) or current_employee.emp_code == 'MR10001'
    is_leader = has_direct_reports(current_employee.id, db, StaffEmployee) if not is_admin else True

    today = get_indian_time().date()
    today_start = datetime.combine(today, datetime.min.time())
    today_end = datetime.combine(today, datetime.max.time())

    ref_date = today
    if end_date:
        try:
            ref_date = datetime.strptime(end_date, "%Y-%m-%d").date()
        except ValueError:
            pass
    daily_dates = [(ref_date - timedelta(days=i)) for i in range(2, -1, -1)]
    daily_date_strs = [d.strftime('%Y-%m-%d') for d in daily_dates]
    daily_range_start = datetime.combine(daily_dates[0], datetime.min.time())
    daily_range_end = datetime.combine(daily_dates[-1], datetime.max.time())

    avg_start = daily_dates[0]
    avg_end = daily_dates[-1]
    if start_date and end_date:
        try:
            avg_start = datetime.strptime(start_date, "%Y-%m-%d").date()
            avg_end = datetime.strptime(end_date, "%Y-%m-%d").date()
        except ValueError:
            pass
    elif start_date:
        try:
            avg_start = datetime.strptime(start_date, "%Y-%m-%d").date()
            avg_end = today
        except ValueError:
            pass
    avg_num_days = max((avg_end - avg_start).days + 1, 1)
    avg_range_start = datetime.combine(avg_start, datetime.min.time())
    avg_range_end = datetime.combine(avg_end, datetime.max.time())

    from sqlalchemy import cast, Date as SADate

    ALL_STATUSES = ['new', 'contacted', 'not_answered', 'interested', 'qualified', 'proposal', 'loan_process', 'waiting_for_bank_loan', 'bank_loan_rejected', 'won', 'processing', 'completed', 'lost', 'on_hold', 'do_not_call']

    def base_lead_filters():
        filters = []
        if company_id:
            filters.append(CRMLead.company_id == company_id)
        if start_date:
            try:
                filters.append(CRMLead.created_at >= datetime.strptime(start_date, "%Y-%m-%d"))
            except ValueError:
                pass
        if end_date:
            try:
                filters.append(CRMLead.created_at <= datetime.strptime(end_date, "%Y-%m-%d").replace(hour=23, minute=59, second=59))
            except ValueError:
                pass
        if status:
            filters.append(CRMLead.status == status)
        if priority:
            filters.append(CRMLead.priority == priority)
        if category_id:
            filters.append(CRMLead.category_id == category_id)
        return filters

    common_filters = base_lead_filters()

    def owner_filters(emp_id):
        return [CRMLead.primary_owner_type == 'staff', CRMLead.primary_owner_id == emp_id] + common_filters

    my_id = current_employee.id
    my_leads_q = db.query(CRMLead).filter(*owner_filters(my_id))
    total_leads = my_leads_q.count()

    my_contacted_today = db.query(func.count(CRMLead.id)).filter(
        *owner_filters(my_id),
        CRMLead.last_contact_date >= today_start,
        CRMLead.last_contact_date <= today_end
    ).scalar() or 0

    my_daily_raw = db.query(
        cast(CRMLead.last_contact_date, SADate), func.count(CRMLead.id)
    ).filter(
        *owner_filters(my_id),
        CRMLead.last_contact_date >= daily_range_start,
        CRMLead.last_contact_date <= daily_range_end
    ).group_by(cast(CRMLead.last_contact_date, SADate)).all()
    my_daily_contacted = {r[0].strftime('%Y-%m-%d'): r[1] for r in my_daily_raw if r[0]}

    my_avg_total = db.query(func.count(CRMLead.id)).filter(
        *owner_filters(my_id),
        CRMLead.last_contact_date >= avg_range_start,
        CRMLead.last_contact_date <= avg_range_end
    ).scalar() or 0
    my_avg_daily_leads = round(my_avg_total / avg_num_days, 1)

    # DC_OVERDUE_FIX: Use full OR-based assignment filter (matches Auto Dialer logic).
    # Counts leads where user is handler_id, telecaller_id, field_staff_id, OR primary_owner_id.
    # NOTE: Status exclusion here is ['won', 'completed', 'lost'] — the dialer also excludes
    # 'do_not_call' and staff_progress.py also excludes 'dropped'. Developer should decide
    # whether to harmonize these lists across all three endpoints.
    my_emp_code = current_employee.emp_code
    my_overdue = db.query(func.count(CRMLead.id)).filter(
        _crm_assignment_filter(my_id, my_emp_code),
        CRMLead.next_followup_date < today_start,
        CRMLead.status.notin_(['won', 'completed', 'lost']),
        *common_filters
    ).scalar() or 0

    my_status_counts_raw = db.query(
        CRMLead.status, func.count(CRMLead.id)
    ).filter(*owner_filters(my_id)).group_by(CRMLead.status).all()
    my_status_map = {s: c for s, c in my_status_counts_raw}

    my_actual_revenue = db.query(func.coalesce(func.sum(CRMLeadTransaction.amount), 0)).join(
        CRMLead, CRMLeadTransaction.lead_id == CRMLead.id
    ).filter(
        CRMLead.primary_owner_type == 'staff',
        CRMLead.primary_owner_id == my_id,
        CRMLeadTransaction.validation_status == 'validated',
        *common_filters
    ).scalar() or 0

    my_deal_value = db.query(func.coalesce(func.sum(_eff_dv()), 0)).filter(
        *owner_filters(my_id),
        CRMLead.status.in_(['won', 'loan_process', 'completed'])
    ).scalar() or 0

    my_self_leads = db.query(func.count(CRMLead.id)).filter(
        *owner_filters(my_id),
        CRMLead.source == SELF_LEAD_SOURCE_NAME
    ).scalar() or 0

    # DC Protocol (Apr 2026): N002 — my VGK registrations + WA share clicks
    try:
        my_vgk_created = db.execute(text(
            "SELECT COUNT(*) FROM crm_wa_share_logs WHERE staff_id=:sid AND share_type='vgk_registration' "
            "AND created_at >= :start AND created_at <= :end"
        ), {"sid": my_id, "start": avg_range_start, "end": avg_range_end}).scalar() or 0
        my_wa_shares = db.execute(text(
            "SELECT COUNT(*) FROM crm_wa_share_logs WHERE staff_id=:sid AND share_type='vgk_creds' "
            "AND created_at >= :start AND created_at <= :end"
        ), {"sid": my_id, "start": avg_range_start, "end": avg_range_end}).scalar() or 0
    except Exception:
        my_vgk_created = 0
        my_wa_shares = 0

    cat_breakdown_raw = db.query(
        SignupCategory.id,
        SignupCategory.name,
        CRMLead.status,
        func.count(CRMLead.id).label('cnt')
    ).outerjoin(CRMLead, and_(
        CRMLead.category_id == SignupCategory.id,
        CRMLead.primary_owner_type == 'staff',
        CRMLead.primary_owner_id == my_id,
        *common_filters
    )).group_by(SignupCategory.id, SignupCategory.name, CRMLead.status).all()

    cat_contacted_raw = db.query(
        CRMLead.category_id, func.count(CRMLead.id)
    ).filter(
        *owner_filters(my_id),
        CRMLead.last_contact_date >= today_start,
        CRMLead.last_contact_date <= today_end
    ).group_by(CRMLead.category_id).all()
    cat_contacted_map = {r[0]: r[1] for r in cat_contacted_raw}

    cat_daily_raw = db.query(
        CRMLead.category_id, cast(CRMLead.last_contact_date, SADate), func.count(CRMLead.id)
    ).filter(
        *owner_filters(my_id),
        CRMLead.last_contact_date >= daily_range_start,
        CRMLead.last_contact_date <= daily_range_end
    ).group_by(CRMLead.category_id, cast(CRMLead.last_contact_date, SADate)).all()
    cat_daily_map = {}
    for cid, d, cnt in cat_daily_raw:
        if cid not in cat_daily_map:
            cat_daily_map[cid] = {}
        if d:
            cat_daily_map[cid][d.strftime('%Y-%m-%d')] = cnt

    cat_avg_raw = db.query(
        CRMLead.category_id, func.count(CRMLead.id)
    ).filter(
        *owner_filters(my_id),
        CRMLead.last_contact_date >= avg_range_start,
        CRMLead.last_contact_date <= avg_range_end
    ).group_by(CRMLead.category_id).all()
    cat_avg_map = {r[0]: round(r[1] / avg_num_days, 1) for r in cat_avg_raw}

    # DC_OVERDUE_FIX: Use full OR-based assignment filter for category overdue counts.
    cat_overdue_raw = db.query(
        CRMLead.category_id, func.count(CRMLead.id)
    ).filter(
        _crm_assignment_filter(my_id, my_emp_code),
        CRMLead.next_followup_date < today_start,
        CRMLead.status.notin_(['won', 'completed', 'lost']),
        *common_filters
    ).group_by(CRMLead.category_id).all()
    cat_overdue_map = {r[0]: r[1] for r in cat_overdue_raw}

    cat_revenue_raw = db.query(
        CRMLead.category_id,
        func.coalesce(func.sum(CRMLeadTransaction.amount), 0)
    ).join(CRMLeadTransaction, CRMLeadTransaction.lead_id == CRMLead.id).filter(
        CRMLead.primary_owner_type == 'staff',
        CRMLead.primary_owner_id == my_id,
        CRMLeadTransaction.validation_status == 'validated',
        *common_filters
    ).group_by(CRMLead.category_id).all()
    cat_revenue_map = {r[0]: float(r[1]) for r in cat_revenue_raw}

    cat_deal_raw = db.query(
        CRMLead.category_id,
        func.coalesce(func.sum(_eff_dv()), 0)
    ).filter(
        *owner_filters(my_id),
        CRMLead.status.in_(['won', 'loan_process', 'completed'])
    ).group_by(CRMLead.category_id).all()
    cat_deal_map = {r[0]: float(r[1]) for r in cat_deal_raw}

    cat_self_raw = db.query(
        CRMLead.category_id, func.count(CRMLead.id)
    ).filter(
        *owner_filters(my_id),
        CRMLead.source == SELF_LEAD_SOURCE_NAME
    ).group_by(CRMLead.category_id).all()
    cat_self_map = {r[0]: r[1] for r in cat_self_raw}

    cat_map = {}
    for row in cat_breakdown_raw:
        cid = row[0]
        if cid not in cat_map:
            cat_map[cid] = {'category_name': row[1], 'statuses': {}}
        if row[2]:
            cat_map[cid]['statuses'][row[2]] = row[3]

    category_breakdown = []
    for cid, cdata in cat_map.items():
        st = cdata['statuses']
        total = sum(st.values())
        if total == 0 and not cat_contacted_map.get(cid) and not cat_overdue_map.get(cid):
            continue
        cat_self = cat_self_map.get(cid, 0)
        entry = {
            'category_name': cdata['category_name'],
            'total': total,
            'contacted_today': cat_contacted_map.get(cid, 0),
            'overdue': cat_overdue_map.get(cid, 0),
            'actual_revenue': cat_revenue_map.get(cid, 0),
            'deal_value': cat_deal_map.get(cid, 0),
            'self_leads': cat_self,
            'company_leads': total - cat_self,
            'daily_contacted': {ds: cat_daily_map.get(cid, {}).get(ds, 0) for ds in daily_date_strs},
            'avg_daily_leads': cat_avg_map.get(cid, 0),
        }
        for s in ALL_STATUSES:
            entry[s] = st.get(s, 0)
        category_breakdown.append(entry)

    my_performance = {
        'summary': {
            'total_leads': total_leads,
            'contacted_today': my_contacted_today,
            'daily_contacted': {ds: my_daily_contacted.get(ds, 0) for ds in daily_date_strs},
            'avg_daily_leads': my_avg_daily_leads,
            'overdue': my_overdue,
            **{s: my_status_map.get(s, 0) for s in ALL_STATUSES}
        },
        'actual_revenue': float(my_actual_revenue),
        'deal_value': float(my_deal_value),
        'self_leads': my_self_leads,
        'company_leads': total_leads - my_self_leads,
        'vgk_created': int(my_vgk_created),
        'wa_shares': int(my_wa_shares),
        'category_breakdown': category_breakdown
    }

    team_performance = None
    status_wise = None
    category_wise_data = None
    company_wise_data = None

    if is_leader or is_admin:
        hidden_ids_team = _get_hidden_employee_ids(db, StaffEmployee)
        if is_admin:
            emp_query = db.query(StaffEmployee).filter(StaffEmployee.status == 'active')
            if company_id:
                emp_query = emp_query.filter(
                    or_(
                        StaffEmployee.base_company_id == company_id,
                        StaffEmployee.data_companies.contains([company_id])
                    )
                )
            if department_id:
                emp_query = emp_query.filter(StaffEmployee.department_id == department_id)
            team_employees = [e for e in emp_query.order_by(StaffEmployee.full_name).all() if e.id not in hidden_ids_team]
        else:
            downline_ids = get_recursive_downline(current_employee.id, db, StaffEmployee, include_manager=False)
            downline_ids = [eid for eid in downline_ids if eid not in hidden_ids_team]
            emp_query = db.query(StaffEmployee).filter(
                StaffEmployee.id.in_(downline_ids),
                StaffEmployee.status == 'active'
            )
            if department_id:
                emp_query = emp_query.filter(StaffEmployee.department_id == department_id)
            team_employees = emp_query.order_by(StaffEmployee.full_name).all()

        team_emp_ids = [e.id for e in team_employees]

        if team_emp_ids:
            batch_status = db.query(
                CRMLead.primary_owner_id, CRMLead.status, func.count(CRMLead.id)
            ).filter(
                CRMLead.primary_owner_type == 'staff',
                CRMLead.primary_owner_id.in_(team_emp_ids),
                *common_filters
            ).group_by(CRMLead.primary_owner_id, CRMLead.status).all()

            batch_contacted = db.query(
                CRMLead.primary_owner_id, func.count(CRMLead.id)
            ).filter(
                CRMLead.primary_owner_type == 'staff',
                CRMLead.primary_owner_id.in_(team_emp_ids),
                CRMLead.last_contact_date >= today_start,
                CRMLead.last_contact_date <= today_end,
                *common_filters
            ).group_by(CRMLead.primary_owner_id).all()

            # DC_OVERDUE_FIX: Per-employee overdue count using full OR-based assignment filter
            # (handler_id, telecaller_id, field_staff_id, OR primary_owner_id) to match dialer.
            # Grouped batch query cannot handle multi-field OR without double-counting, so we
            # query per employee via shared _crm_assignment_filter helper.
            batch_overdue = []
            for _emp in team_employees:
                _emp_oc = db.query(func.count(CRMLead.id)).filter(
                    _crm_assignment_filter(_emp.id, _emp.emp_code),
                    CRMLead.next_followup_date < today_start,
                    CRMLead.status.notin_(['won', 'completed', 'lost']),
                    *common_filters
                ).scalar() or 0
                batch_overdue.append((_emp.id, _emp_oc))

            batch_revenue = db.query(
                CRMLead.primary_owner_id,
                func.coalesce(func.sum(CRMLeadTransaction.amount), 0)
            ).join(CRMLeadTransaction, CRMLeadTransaction.lead_id == CRMLead.id).filter(
                CRMLead.primary_owner_type == 'staff',
                CRMLead.primary_owner_id.in_(team_emp_ids),
                CRMLeadTransaction.validation_status == 'validated',
                *common_filters
            ).group_by(CRMLead.primary_owner_id).all()

            batch_deal = db.query(
                CRMLead.primary_owner_id,
                func.coalesce(func.sum(_eff_dv()), 0)
            ).filter(
                CRMLead.primary_owner_type == 'staff',
                CRMLead.primary_owner_id.in_(team_emp_ids),
                CRMLead.status.in_(['won', 'loan_process', 'completed']),
                *common_filters
            ).group_by(CRMLead.primary_owner_id).all()

            batch_self = db.query(
                CRMLead.primary_owner_id, func.count(CRMLead.id)
            ).filter(
                CRMLead.primary_owner_type == 'staff',
                CRMLead.primary_owner_id.in_(team_emp_ids),
                CRMLead.source == SELF_LEAD_SOURCE_NAME,
                *common_filters
            ).group_by(CRMLead.primary_owner_id).all()

            # DC Protocol (Apr 2026): N002 — VGK registrations + WA share clicks per staff
            _vgk_raw = db.execute(text(
                "SELECT staff_id, COUNT(*) FROM crm_wa_share_logs "
                "WHERE staff_id = ANY(:ids) AND share_type = 'vgk_registration' "
                "AND created_at >= :start AND created_at <= :end GROUP BY staff_id"
            ), {"ids": team_emp_ids, "start": avg_range_start, "end": avg_range_end}).fetchall()
            batch_vgk_map = {int(r[0]): int(r[1]) for r in _vgk_raw}
            _wa_raw = db.execute(text(
                "SELECT staff_id, COUNT(*) FROM crm_wa_share_logs "
                "WHERE staff_id = ANY(:ids) AND share_type = 'vgk_creds' "
                "AND created_at >= :start AND created_at <= :end GROUP BY staff_id"
            ), {"ids": team_emp_ids, "start": avg_range_start, "end": avg_range_end}).fetchall()
            batch_wa_map = {int(r[0]): int(r[1]) for r in _wa_raw}

            batch_daily = db.query(
                CRMLead.primary_owner_id, cast(CRMLead.last_contact_date, SADate), func.count(CRMLead.id)
            ).filter(
                CRMLead.primary_owner_type == 'staff',
                CRMLead.primary_owner_id.in_(team_emp_ids),
                CRMLead.last_contact_date >= daily_range_start,
                CRMLead.last_contact_date <= daily_range_end,
                *common_filters
            ).group_by(CRMLead.primary_owner_id, cast(CRMLead.last_contact_date, SADate)).all()

            emp_daily_map = {}
            for eid, d, cnt in batch_daily:
                if eid not in emp_daily_map:
                    emp_daily_map[eid] = {}
                if d:
                    emp_daily_map[eid][d.strftime('%Y-%m-%d')] = cnt

            batch_avg = db.query(
                CRMLead.primary_owner_id, func.count(CRMLead.id)
            ).filter(
                CRMLead.primary_owner_type == 'staff',
                CRMLead.primary_owner_id.in_(team_emp_ids),
                CRMLead.last_contact_date >= avg_range_start,
                CRMLead.last_contact_date <= avg_range_end,
                *common_filters
            ).group_by(CRMLead.primary_owner_id).all()
            emp_avg_map = {r[0]: round(r[1] / avg_num_days, 1) for r in batch_avg}

            status_map = {}
            for eid, st, cnt in batch_status:
                if eid not in status_map:
                    status_map[eid] = {}
                status_map[eid][st] = cnt

            contacted_map = {r[0]: r[1] for r in batch_contacted}
            overdue_map = {r[0]: r[1] for r in batch_overdue}
            revenue_map = {r[0]: float(r[1]) for r in batch_revenue}
            deal_map = {r[0]: float(r[1]) for r in batch_deal}
            self_map = {r[0]: r[1] for r in batch_self}
        else:
            status_map = {}
            contacted_map = {}
            overdue_map = {}
            revenue_map = {}
            deal_map = {}
            self_map = {}
            emp_daily_map = {}
            emp_avg_map = {}
            batch_vgk_map = {}
            batch_wa_map = {}

        call_talk_map = {}
        if team_emp_ids:
            try:
                call_stats = db.query(
                    StaffCallLog.staff_id,
                    func.sum(StaffCallLog.duration_seconds).label('total_dur'),
                    func.count(func.distinct(StaffCallLog.call_date)).label('active_days'),
                    func.count(StaffCallLog.id).label('total_calls')
                ).filter(
                    StaffCallLog.staff_id.in_(team_emp_ids),
                    StaffCallLog.call_date >= (start_date or (today - timedelta(days=30)).strftime('%Y-%m-%d')),
                    StaffCallLog.call_date <= (end_date or today.strftime('%Y-%m-%d'))
                ).group_by(StaffCallLog.staff_id).all()
                for cs in call_stats:
                    days = max(cs.active_days or 1, 1)
                    call_talk_map[cs.staff_id] = {
                        'avg_daily_talk_time': int(cs.total_dur or 0) // days,
                        'total_calls_30d': cs.total_calls or 0
                    }
            except Exception:
                pass

        team_rows = []
        totals = {s: 0 for s in ALL_STATUSES}
        totals.update({'contacted_today': 0, 'overdue': 0, 'total': 0, 'self_leads': 0, 'company_leads': 0, 'actual_revenue': 0, 'deal_value': 0, 'avg_daily_talk_time': 0, 'vgk_created': 0, 'wa_shares': 0})

        for emp in team_employees:
            emp_statuses = status_map.get(emp.id, {})
            emp_total = sum(emp_statuses.values())
            emp_self = self_map.get(emp.id, 0)
            call_info = call_talk_map.get(emp.id, {})
            emp_daily = emp_daily_map.get(emp.id, {})
            row = {
                'emp_id': emp.id,
                'emp_code': emp.emp_code,
                'name': emp.full_name,
                'daily_contacted': {ds: emp_daily.get(ds, 0) for ds in daily_date_strs},
                'contacted_today': contacted_map.get(emp.id, 0),
                'avg_daily_leads': emp_avg_map.get(emp.id, 0),
                'overdue': overdue_map.get(emp.id, 0),
                'total': emp_total,
                'self_leads': emp_self,
                'company_leads': emp_total - emp_self,
                'actual_revenue': revenue_map.get(emp.id, 0),
                'deal_value': deal_map.get(emp.id, 0),
                'avg_daily_talk_time': call_info.get('avg_daily_talk_time', 0),
                'total_calls_30d': call_info.get('total_calls_30d', 0),
                'vgk_created': batch_vgk_map.get(emp.id, 0),
                'wa_shares': batch_wa_map.get(emp.id, 0),
            }
            for s in ALL_STATUSES:
                row[s] = emp_statuses.get(s, 0)

            for key in totals:
                totals[key] += row.get(key, 0)

            team_rows.append(row)

        if team_rows:
            total_talk = sum(r.get('avg_daily_talk_time', 0) for r in team_rows)
            active_count = sum(1 for r in team_rows if r.get('avg_daily_talk_time', 0) > 0)
            totals['avg_daily_talk_time'] = total_talk // max(active_count, 1) if active_count else 0

        team_performance = {'employees': team_rows, 'totals': totals}
        status_wise = {'employees': team_rows, 'totals': totals}

        cat_wise_status = db.query(
            CRMLead.category_id, CRMLead.status, func.count(CRMLead.id)
        ).filter(
            CRMLead.primary_owner_type == 'staff',
            CRMLead.primary_owner_id.in_(team_emp_ids) if team_emp_ids else CRMLead.primary_owner_id == my_id,
            *common_filters
        ).group_by(CRMLead.category_id, CRMLead.status).all()

        cat_wise_contacted = db.query(
            CRMLead.category_id, func.count(CRMLead.id)
        ).filter(
            CRMLead.primary_owner_type == 'staff',
            CRMLead.primary_owner_id.in_(team_emp_ids) if team_emp_ids else CRMLead.primary_owner_id == my_id,
            CRMLead.last_contact_date >= today_start,
            CRMLead.last_contact_date <= today_end,
            *common_filters
        ).group_by(CRMLead.category_id).all()

        cw_daily_raw = db.query(
            CRMLead.category_id, cast(CRMLead.last_contact_date, SADate), func.count(CRMLead.id)
        ).filter(
            CRMLead.primary_owner_type == 'staff',
            CRMLead.primary_owner_id.in_(team_emp_ids) if team_emp_ids else CRMLead.primary_owner_id == my_id,
            CRMLead.last_contact_date >= daily_range_start,
            CRMLead.last_contact_date <= daily_range_end,
            *common_filters
        ).group_by(CRMLead.category_id, cast(CRMLead.last_contact_date, SADate)).all()
        cw_daily_map = {}
        for cid, d, cnt in cw_daily_raw:
            if cid not in cw_daily_map:
                cw_daily_map[cid] = {}
            if d:
                cw_daily_map[cid][d.strftime('%Y-%m-%d')] = cnt

        cw_avg_raw = db.query(
            CRMLead.category_id, func.count(CRMLead.id)
        ).filter(
            CRMLead.primary_owner_type == 'staff',
            CRMLead.primary_owner_id.in_(team_emp_ids) if team_emp_ids else CRMLead.primary_owner_id == my_id,
            CRMLead.last_contact_date >= avg_range_start,
            CRMLead.last_contact_date <= avg_range_end,
            *common_filters
        ).group_by(CRMLead.category_id).all()
        cw_avg_map = {r[0]: round(r[1] / avg_num_days, 1) for r in cw_avg_raw}

        # DC_OVERDUE_FIX: Use full OR-based assignment filter for category-wise team overdue.
        # Includes all assignment fields via shared _crm_assignment_filter_for_team helper.
        _all_emp_ids = team_emp_ids if team_emp_ids else [my_id]
        _all_emp_codes = [e.emp_code for e in team_employees] if team_emp_ids else [current_employee.emp_code]
        cat_wise_overdue = db.query(
            CRMLead.category_id, func.count(CRMLead.id)
        ).filter(
            _crm_assignment_filter_for_team(_all_emp_ids, _all_emp_codes),
            CRMLead.next_followup_date < today_start,
            CRMLead.status.notin_(['won', 'completed', 'lost']),
            *common_filters
        ).group_by(CRMLead.category_id).all()

        cat_wise_revenue = db.query(
            CRMLead.category_id,
            func.coalesce(func.sum(CRMLeadTransaction.amount), 0)
        ).join(CRMLeadTransaction, CRMLeadTransaction.lead_id == CRMLead.id).filter(
            CRMLead.primary_owner_type == 'staff',
            CRMLead.primary_owner_id.in_(team_emp_ids) if team_emp_ids else CRMLead.primary_owner_id == my_id,
            CRMLeadTransaction.validation_status == 'validated',
            *common_filters
        ).group_by(CRMLead.category_id).all()

        cat_wise_deal = db.query(
            CRMLead.category_id,
            func.coalesce(func.sum(CRMLead.deal_value_total), 0)
        ).filter(
            CRMLead.primary_owner_type == 'staff',
            CRMLead.primary_owner_id.in_(team_emp_ids) if team_emp_ids else CRMLead.primary_owner_id == my_id,
            CRMLead.status.in_(['won', 'loan_process', 'completed']),
            *common_filters
        ).group_by(CRMLead.category_id).all()

        cat_names = {}
        cat_ids_found = set()
        for r in cat_wise_status:
            if r[0]:
                cat_ids_found.add(r[0])
        for r in cat_wise_contacted:
            if r[0]:
                cat_ids_found.add(r[0])
        for r in cat_wise_overdue:
            if r[0]:
                cat_ids_found.add(r[0])

        if cat_ids_found:
            cat_name_rows = db.query(SignupCategory.id, SignupCategory.name).filter(
                SignupCategory.id.in_(cat_ids_found)
            ).all()
            cat_names = {r[0]: r[1] for r in cat_name_rows}

        cw_status_map = {}
        for cid, st, cnt in cat_wise_status:
            if cid not in cw_status_map:
                cw_status_map[cid] = {}
            cw_status_map[cid][st] = cnt

        cw_contacted_map = {r[0]: r[1] for r in cat_wise_contacted}
        cw_overdue_map = {r[0]: r[1] for r in cat_wise_overdue}
        cw_revenue_map = {r[0]: float(r[1]) for r in cat_wise_revenue}
        cw_deal_map = {r[0]: float(r[1]) for r in cat_wise_deal}

        cat_wise_self = db.query(
            CRMLead.category_id, func.count(CRMLead.id)
        ).filter(
            CRMLead.primary_owner_type == 'staff',
            CRMLead.primary_owner_id.in_(team_emp_ids) if team_emp_ids else CRMLead.primary_owner_id == my_id,
            CRMLead.source == SELF_LEAD_SOURCE_NAME,
            *common_filters
        ).group_by(CRMLead.category_id).all()
        cw_self_map = {r[0]: r[1] for r in cat_wise_self}

        category_wise_data = []
        for cid in set(list(cw_status_map.keys()) + list(cw_contacted_map.keys()) + list(cw_overdue_map.keys())):
            st = cw_status_map.get(cid, {})
            total = sum(st.values())
            cw_self = cw_self_map.get(cid, 0)
            entry = {
                'category_id': cid,
                'category_name': cat_names.get(cid, 'Unknown'),
                'daily_contacted': {ds: cw_daily_map.get(cid, {}).get(ds, 0) for ds in daily_date_strs},
                'contacted_today': cw_contacted_map.get(cid, 0),
                'avg_daily_leads': cw_avg_map.get(cid, 0),
                'overdue': cw_overdue_map.get(cid, 0),
                'total': total,
                'actual_revenue': cw_revenue_map.get(cid, 0),
                'deal_value': cw_deal_map.get(cid, 0),
                'self_leads': cw_self,
                'company_leads': total - cw_self,
            }
            for s in ALL_STATUSES:
                entry[s] = st.get(s, 0)
            category_wise_data.append(entry)

    if is_admin or is_leader:
        comp_owner_filter = []
        if not is_admin:
            comp_owner_filter = [
                CRMLead.primary_owner_type == 'staff',
                CRMLead.primary_owner_id.in_(team_emp_ids + [current_employee.id])
            ]

        comp_status = db.query(
            CRMLead.company_id, CRMLead.status, func.count(CRMLead.id)
        ).filter(*common_filters, *comp_owner_filter).group_by(CRMLead.company_id, CRMLead.status).all()

        comp_contacted = db.query(
            CRMLead.company_id, func.count(CRMLead.id)
        ).filter(
            CRMLead.last_contact_date >= today_start,
            CRMLead.last_contact_date <= today_end,
            *common_filters, *comp_owner_filter
        ).group_by(CRMLead.company_id).all()

        comp_daily_raw = db.query(
            CRMLead.company_id, cast(CRMLead.last_contact_date, SADate), func.count(CRMLead.id)
        ).filter(
            CRMLead.last_contact_date >= daily_range_start,
            CRMLead.last_contact_date <= daily_range_end,
            *common_filters, *comp_owner_filter
        ).group_by(CRMLead.company_id, cast(CRMLead.last_contact_date, SADate)).all()
        comp_daily_map = {}
        for cid, d, cnt in comp_daily_raw:
            if cid not in comp_daily_map:
                comp_daily_map[cid] = {}
            if d:
                comp_daily_map[cid][d.strftime('%Y-%m-%d')] = cnt

        comp_avg_raw = db.query(
            CRMLead.company_id, func.count(CRMLead.id)
        ).filter(
            CRMLead.last_contact_date >= avg_range_start,
            CRMLead.last_contact_date <= avg_range_end,
            *common_filters, *comp_owner_filter
        ).group_by(CRMLead.company_id).all()
        comp_avg_map = {r[0]: round(r[1] / avg_num_days, 1) for r in comp_avg_raw}

        # DC_OVERDUE_FIX: Use full OR-based assignment filter for company-wise overdue.
        # Admins see all leads (no employee scope filter); non-admins use team OR self.
        _co_all_ids = (team_emp_ids + [current_employee.id]) if not is_admin else None
        _co_all_codes = ([e.emp_code for e in team_employees] + [current_employee.emp_code]) if not is_admin else None
        if is_admin:
            comp_overdue_filter = [
                CRMLead.next_followup_date < today_start,
                CRMLead.status.notin_(['won', 'completed', 'lost']),
                *common_filters
            ]
        else:
            comp_overdue_filter = [
                _crm_assignment_filter_for_team(_co_all_ids, _co_all_codes),
                CRMLead.next_followup_date < today_start,
                CRMLead.status.notin_(['won', 'completed', 'lost']),
                *common_filters
            ]
        comp_overdue = db.query(
            CRMLead.company_id, func.count(CRMLead.id)
        ).filter(*comp_overdue_filter).group_by(CRMLead.company_id).all()

        comp_revenue = db.query(
            CRMLead.company_id,
            func.coalesce(func.sum(CRMLeadTransaction.amount), 0)
        ).join(CRMLeadTransaction, CRMLeadTransaction.lead_id == CRMLead.id).filter(
            CRMLeadTransaction.validation_status == 'validated',
            *common_filters, *comp_owner_filter
        ).group_by(CRMLead.company_id).all()

        comp_deal = db.query(
            CRMLead.company_id,
            func.coalesce(func.sum(CRMLead.deal_value_total), 0)
        ).filter(
            CRMLead.status.in_(['won', 'loan_process', 'completed']),
            *common_filters, *comp_owner_filter
        ).group_by(CRMLead.company_id).all()

        comp_ids_found = set()
        for r in comp_status:
            if r[0]:
                comp_ids_found.add(r[0])
        for r in comp_contacted:
            if r[0]:
                comp_ids_found.add(r[0])

        comp_names = {}
        if comp_ids_found:
            comp_name_rows = db.query(AssociatedCompany.id, AssociatedCompany.company_name).filter(
                AssociatedCompany.id.in_(comp_ids_found)
            ).all()
            comp_names = {r[0]: r[1] for r in comp_name_rows}

        cs_status_map = {}
        for cid, st, cnt in comp_status:
            if cid not in cs_status_map:
                cs_status_map[cid] = {}
            cs_status_map[cid][st] = cnt

        cs_contacted_map = {r[0]: r[1] for r in comp_contacted}
        cs_overdue_map = {r[0]: r[1] for r in comp_overdue}
        cs_revenue_map = {r[0]: float(r[1]) for r in comp_revenue}
        cs_deal_map = {r[0]: float(r[1]) for r in comp_deal}

        comp_self = db.query(
            CRMLead.company_id, func.count(CRMLead.id)
        ).filter(
            CRMLead.source == SELF_LEAD_SOURCE_NAME,
            *common_filters, *comp_owner_filter
        ).group_by(CRMLead.company_id).all()
        cs_self_map = {r[0]: r[1] for r in comp_self}

        company_wise_data = []
        for cid in set(list(cs_status_map.keys()) + list(cs_contacted_map.keys()) + list(cs_overdue_map.keys())):
            st = cs_status_map.get(cid, {})
            total = sum(st.values())
            cs_self = cs_self_map.get(cid, 0)
            entry = {
                'company_id': cid,
                'company_name': comp_names.get(cid, 'Unknown'),
                'daily_contacted': {ds: comp_daily_map.get(cid, {}).get(ds, 0) for ds in daily_date_strs},
                'contacted_today': cs_contacted_map.get(cid, 0),
                'avg_daily_leads': comp_avg_map.get(cid, 0),
                'overdue': cs_overdue_map.get(cid, 0),
                'total': total,
                'actual_revenue': cs_revenue_map.get(cid, 0),
                'deal_value': cs_deal_map.get(cid, 0),
                'self_leads': cs_self,
                'company_leads': total - cs_self,
            }
            for s in ALL_STATUSES:
                entry[s] = st.get(s, 0)
            company_wise_data.append(entry)

    return {
        'success': True,
        'data': {
            'is_leader': is_leader,
            'is_admin': is_admin,
            'daily_dates': daily_date_strs,
            'avg_num_days': avg_num_days,
            'current_employee': {
                'id': current_employee.id,
                'emp_code': current_employee.emp_code,
                'name': current_employee.full_name
            },
            'my_performance': my_performance,
            'team_performance': team_performance,
            'status_wise': status_wise,
            'category_wise': category_wise_data,
            'company_wise': company_wise_data
        }
    }


@router.get("/my-leads")
def get_my_leads(
    company_id: Optional[int] = Query(None, description="Company ID for DC Protocol (optional for VGK4U - all companies)"),
    scope: str = Query("my", description="Scope: 'my', 'team', or 'all'"),
    role_filter: Optional[str] = Query(None, description="DC Protocol (Mar 2026): Mobile tab filter — my_leads, as_primary, as_telecaller, as_field, as_handler, fresh, self"),
    status: Optional[str] = None,
    priority: Optional[str] = None,
    category: Optional[str] = Query(None),
    category_id: Optional[int] = None,
    search: Optional[str] = None,
    next_followup_from: Optional[str] = None,
    next_followup_to: Optional[str] = None,
    last_followup_from: Optional[str] = None,
    last_followup_to: Optional[str] = None,
    has_recent_comments: Optional[bool] = None,
    submit_date_from: Optional[str] = None,
    submit_date_to: Optional[str] = None,
    complete_date_from: Optional[str] = None,
    complete_date_to: Optional[str] = None,
    first_dvr_from: Optional[str] = None,
    first_dvr_to: Optional[str] = None,
    page: int = 1,
    per_page: int = 20,
    db: Session = Depends(get_db),
    current_employee: StaffEmployee = Depends(get_current_staff_user)
):
    """
    DC Protocol: Get leads assigned to current user or their team
    Enhanced with follow-up and comment filters
    VGK4U Supreme bypass: Always treated as leader, sees all company leads
    """
    # DC Protocol (Feb 2026): Safety cap — prevents OOM crash from large per_page requests
    per_page = min(per_page, 100)
    # DC Protocol: Check if VGK4U Supreme (full access bypass)
    staff_type = (current_employee.staff_type or '').upper()
    is_admin = is_vgk_admin(staff_type)
    is_leader = has_direct_reports(current_employee.id, db, StaffEmployee) or is_admin
    
    # DC Protocol: Menu-based access control - page assignment = full access
    # if scope in ['team', 'all'] and not is_leader:
    #     raise HTTPException(
    #         status_code=403,
    #         detail="Team and All scopes are only available to leaders with direct reports"
    #     )
    
    handler_ids = []
    team_employee_ids = []
    
    if scope == 'my' and not is_admin:
        handler_ids = [current_employee.emp_code]
        team_employee_ids = [current_employee.id]
    elif scope == 'team' and is_leader and not is_admin:
        downline_ids = get_recursive_downline(
            current_employee.id, db, StaffEmployee, include_manager=False
        )
        hidden_ids = _get_hidden_employee_ids(db, StaffEmployee)
        downline_ids = [eid for eid in downline_ids if eid not in hidden_ids]
        team_employees = db.query(StaffEmployee).filter(
            StaffEmployee.id.in_(downline_ids)
        ).all()
        handler_ids = [emp.emp_code for emp in team_employees]
        team_employee_ids = [emp.id for emp in team_employees]
    elif is_admin:
        hidden_ids = _get_hidden_employee_ids(db, StaffEmployee)
        staff_query = db.query(StaffEmployee).filter(StaffEmployee.status == 'active')
        if company_id:
            staff_query = staff_query.filter(StaffEmployee.base_company_id == company_id)
        all_company_staff = [e for e in staff_query.all() if e.id not in hidden_ids]
        handler_ids = [emp.emp_code for emp in all_company_staff]
        team_employee_ids = [emp.id for emp in all_company_staff]
    else:
        downline_ids = get_recursive_downline(
            current_employee.id, db, StaffEmployee, include_manager=False
        )
        hidden_ids = _get_hidden_employee_ids(db, StaffEmployee)
        downline_ids = [eid for eid in downline_ids if eid not in hidden_ids]
        team_employees = db.query(StaffEmployee).filter(
            StaffEmployee.id.in_(downline_ids)
        ).all()
        handler_ids = [emp.emp_code for emp in team_employees]
        team_employee_ids = [emp.id for emp in team_employees]
    
    # DC Protocol (Feb 2026): Build base query - company_id is optional for VGK4U users
    query = db.query(CRMLead)
    
    # Apply company filter — use data_companies when no specific company selected
    if company_id:
        query = query.filter(CRMLead.company_id == company_id)
    elif not is_admin:
        # DC Protocol (Mar 2026): Use staff's accessible companies instead of requiring a specific one
        staff_companies = getattr(current_employee, 'data_companies', None) or []
        if staff_companies:
            query = query.filter(CRMLead.company_id.in_(staff_companies))

    # DC Protocol (Mar 2026): role_filter drives tab-specific queries for mobile/web Staff Leads page
    # Covers all tab IDs: my_leads, as_primary, as_telecaller, as_field, as_handler, fresh, self
    if role_filter and scope == 'my':
        uid = current_employee.id
        emp_code = current_employee.emp_code or ''

        if role_filter == 'as_primary':
            query = query.filter(
                CRMLead.primary_owner_type == 'staff',
                CRMLead.primary_owner_id == uid
            )
        elif role_filter == 'as_telecaller':
            query = query.filter(CRMLead.telecaller_id == uid)
        elif role_filter == 'as_field':
            query = query.filter(CRMLead.field_staff_id == uid)
        elif role_filter == 'as_handler':
            query = query.filter(
                CRMLead.handler_type == 'staff',
                CRMLead.handler_id == emp_code
            )
        elif role_filter == 'fresh':
            # Truly unassigned new leads — any staff can claim these
            query = query.filter(
                CRMLead.handler_type == 'unassigned',
                CRMLead.status == 'new',
                CRMLead.primary_owner_id.is_(None),
                CRMLead.telecaller_id.is_(None),
                CRMLead.field_staff_id.is_(None),
            )
        elif role_filter == 'self':
            query = query.filter(
                CRMLead.created_by_type == 'staff',
                CRMLead.created_by_id == str(uid)
            )
        else:
            # my_leads (default) — all leads related to this staff + unassigned fresh
            query = query.filter(
                or_(
                    and_(CRMLead.primary_owner_type == 'staff', CRMLead.primary_owner_id == uid),
                    CRMLead.telecaller_id == uid,
                    CRMLead.field_staff_id == uid,
                    and_(CRMLead.handler_type == 'staff', CRMLead.handler_id == emp_code),
                    # Unassigned sheet/Meta leads — visible to all staff for claiming
                    and_(
                        CRMLead.handler_type == 'unassigned',
                        CRMLead.status == 'new',
                        CRMLead.primary_owner_id.is_(None),
                        CRMLead.telecaller_id.is_(None),
                        CRMLead.field_staff_id.is_(None),
                    ),
                )
            )
    elif handler_ids or team_employee_ids:
        # Original filter for team/all scopes (no role_filter)
        query = query.filter(
            or_(
                and_(CRMLead.primary_owner_type == 'staff', CRMLead.primary_owner_id.in_(team_employee_ids or [])),
                and_(CRMLead.handler_type == 'staff', CRMLead.handler_id.in_(handler_ids or [])),
                CRMLead.telecaller_id.in_(team_employee_ids or []),
                CRMLead.field_staff_id.in_(team_employee_ids or []),
                # Unassigned fresh leads visible for scope=my
                *([and_(
                    CRMLead.handler_type == 'unassigned',
                    CRMLead.status == 'new',
                    CRMLead.primary_owner_id.is_(None),
                    CRMLead.telecaller_id.is_(None),
                    CRMLead.field_staff_id.is_(None),
                )] if scope == 'my' else [])
            )
        )
    
    if status:
        if status == 'closed':
            query = query.filter(CRMLead.status.in_(['won', 'lost']))
        else:
            query = query.filter(CRMLead.status == status)
    if priority:
        query = query.filter(CRMLead.priority == priority)
    # DC Protocol (Jul 2026 Task 11): Category filter — dual-match logic for both string name and integer ID.
    if category or category_id is not None:
        _cat_ids = []
        if category_id is not None:
            _cat_ids.append(category_id)
        if category:
            if isinstance(category, int) or (isinstance(category, str) and category.isdigit()):
                _cat_ids.append(int(category))
            else:
                _matched_cats = db.query(SignupCategory.id).filter(
                    or_(
                        SignupCategory.name.ilike(category),
                        SignupCategory.name.ilike(f"%{category}%"),
                        SignupCategory.slug.ilike(category)
                    )
                ).all()
                _cat_ids.extend([r.id for r in _matched_cats])

        _cat_ids = list(set(_cat_ids))
        if _cat_ids:
            _deal_lead_sq = (
                db.query(CRMLeadDeal.lead_id)
                .filter(CRMLeadDeal.revenue_category_id.in_(_cat_ids))
                .scalar_subquery()
            )
            query = query.filter(or_(
                CRMLead.category_id.in_(_cat_ids),
                CRMLead.id.in_(_deal_lead_sq)
            ))
        else:
            query = query.filter(CRMLead.id == -1)
    if search:
        _st = f'%{search}%'
        _sc = [
            CRMLead.name.ilike(_st),
            CRMLead.email.ilike(_st),
            CRMLead.phone.ilike(_st),
            CRMLead.city.ilike(_st),
            CRMLead.pincode.ilike(_st),
            CRMLead.source.ilike(_st),
            CRMLead.application_no.ilike(_st),
            CRMLead.source_ref_name.ilike(_st),
            CRMLead.source_ref_id.ilike(_st),
            CRMLead.mnr_handler_id.ilike(_st),
        ]
        _id_s = search.lstrip('#').strip()
        if _id_s.isdigit():
            _sc.append(CRMLead.id == int(_id_s))
        _mnr_uid_s = [str(u.id) for u in db.query(User.id).filter(User.name.ilike(_st)).all()]
        if _mnr_uid_s:
            _sc.append(CRMLead.mnr_handler_id.in_(_mnr_uid_s))
        query = query.filter(or_(*_sc))

    if next_followup_from:
        try:
            date_from = datetime.fromisoformat(next_followup_from.replace('Z', '+00:00'))
            query = query.filter(CRMLead.next_followup_date >= date_from)
        except:
            pass
    if next_followup_to:
        try:
            date_to = datetime.fromisoformat(next_followup_to.replace('Z', '+00:00'))
            query = query.filter(CRMLead.next_followup_date <= date_to)
        except:
            pass
    
    if last_followup_from:
        try:
            date_from = datetime.fromisoformat(last_followup_from.replace('Z', '+00:00'))
            query = query.filter(CRMLead.last_contact_date >= date_from)
        except:
            pass
    if last_followup_to:
        try:
            date_to = datetime.fromisoformat(last_followup_to.replace('Z', '+00:00'))
            query = query.filter(CRMLead.last_contact_date <= date_to)
        except:
            pass
    
    if has_recent_comments:
        seven_days_ago = get_indian_time() - timedelta(days=7)
        lead_ids_with_recent_comments = db.query(CRMLeadNote.lead_id).filter(
            CRMLeadNote.company_id == company_id,
            CRMLeadNote.created_at >= seven_days_ago
        ).distinct().all()
        lead_ids = [lid[0] for lid in lead_ids_with_recent_comments]
        query = query.filter(CRMLead.id.in_(lead_ids))
    if submit_date_from:
        try:
            from datetime import date as _dt_date2
            _sd_from2 = _dt_date2.fromisoformat(submit_date_from[:10])
            query = query.filter(CRMLead.submit_date >= _sd_from2)
        except Exception: pass
    if submit_date_to:
        try:
            from datetime import date as _dt_date2
            _sd_to2 = _dt_date2.fromisoformat(submit_date_to[:10])
            query = query.filter(CRMLead.submit_date <= _sd_to2)
        except Exception: pass
    if complete_date_from:
        try:
            from datetime import date as _dt_date2
            _cd_from2 = _dt_date2.fromisoformat(complete_date_from[:10])
            query = query.filter(CRMLead.complete_date >= _cd_from2)
        except Exception: pass
    if complete_date_to:
        try:
            from datetime import date as _dt_date2
            _cd_to2 = _dt_date2.fromisoformat(complete_date_to[:10])
            query = query.filter(CRMLead.complete_date <= _cd_to2)
        except Exception: pass
    if first_dvr_from:
        try:
            from datetime import date as _dt_date2, timedelta as _td2
            _df2 = _dt_date2.fromisoformat(first_dvr_from[:10])
            query = query.filter(CRMLead.first_payment_received_date >= _df2)
        except Exception: pass
    if first_dvr_to:
        try:
            from datetime import date as _dt_date2, timedelta as _td2
            _dt2 = _dt_date2.fromisoformat(first_dvr_to[:10])
            from datetime import timedelta
            query = query.filter(CRMLead.first_payment_received_date < _dt2 + timedelta(days=1))
        except Exception: pass

    total = query.count()

    leads = query.order_by(CRMLead.updated_at.desc()).offset((page - 1) * per_page).limit(per_page).all()
    
    leads_data = []
    for lead in leads:
        lead_dict = lead.to_dict()
        category = db.query(SignupCategory).filter(SignupCategory.id == lead.category_id).first()
        lead_dict['category_name'] = category.name if category else None
        
        latest_note = db.query(CRMLeadNote).filter(
            CRMLeadNote.lead_id == lead.id
        ).order_by(CRMLeadNote.created_at.desc()).first()
        lead_dict['latest_comment'] = latest_note.to_dict() if latest_note else None
        
        latest_followup = db.query(CRMLeadFollowUp).filter(
            CRMLeadFollowUp.lead_id == lead.id,
            CRMLeadFollowUp.status == 'completed'
        ).order_by(CRMLeadFollowUp.completed_date.desc()).first()
        lead_dict['last_followup'] = latest_followup.to_dict() if latest_followup else None
        
        # DC Protocol (Jan 6, 2026): Defensive handler lookup with null safety
        # handler_id can reference staff (emp_code), MNR member, or partner
        handler_name = None
        if lead.handler_id and lead.handler_type == 'staff':
            try:
                handler = db.query(StaffEmployee).filter(
                    StaffEmployee.emp_code == lead.handler_id
                ).first()
                if handler:
                    handler_name = handler.full_name or handler.emp_code
            except Exception:
                pass
        lead_dict['handler_name'] = handler_name

        # Telecaller info
        if lead.telecaller_id:
            try:
                tc = db.query(StaffEmployee).filter(StaffEmployee.id == lead.telecaller_id).first()
                if tc:
                    lead_dict['telecaller_name'] = tc.full_name or tc.emp_code
                    lead_dict['telecaller_code'] = tc.emp_code
            except Exception:
                pass

        # Field Staff info
        if lead.field_staff_id:
            try:
                fs = db.query(StaffEmployee).filter(StaffEmployee.id == lead.field_staff_id).first()
                if fs:
                    lead_dict['field_staff_name'] = fs.full_name or fs.emp_code
                    lead_dict['field_staff_code'] = fs.emp_code
            except Exception:
                pass

        # Completed date (updated_at when lead reached completed state)
        is_completed = (
            lead.status == 'completed' or
            getattr(lead, 'solar_pipeline_status', None) == 'completed' or
            getattr(lead, 'ev_b2b_stage', None) == 'completed'
        )
        lead_dict['completed_at'] = lead.updated_at.isoformat() if (is_completed and lead.updated_at) else None

        leads_data.append(lead_dict)
    
    return {
        'success': True,
        'data': leads_data,
        'is_leader': is_leader,
        'scope': scope,
        'pagination': {
            'page': page,
            'per_page': per_page,
            'total': total,
            'pages': (total + per_page - 1) // per_page
        }
    }


@router.get("/leads")
def list_leads(
    company_id: int = Query(..., description="Company ID for DC Protocol"),
    status: Optional[str] = None,
    priority: Optional[str] = None,
    category_id: Optional[int] = None,
    category: Optional[str] = Query(None, description="DC Protocol (Feb 2026): Filter by category name for cross-company queries"),
    handler_type: Optional[str] = None,
    handler_id: Optional[str] = None,
    assigned_to_me: Optional[bool] = Query(None, description="Filter leads assigned to current user as telecaller/field_staff"),
    primary_owner: Optional[bool] = Query(None, description="Filter leads where current user is primary owner"),
    as_handler_role: Optional[str] = Query(None, description="Filter leads where current user is assigned as specific handler: telecaller, field_staff, partner, mnr_handler, or any"),
    search: Optional[str] = None,
    next_followup_from: Optional[str] = None,
    next_followup_to: Optional[str] = None,
    last_followup_from: Optional[str] = None,
    last_followup_to: Optional[str] = None,
    last_interacted_from: Optional[str] = Query(None, description="DC Protocol (Jan 22, 2026): Filter by last interaction date (from)"),
    last_interacted_to: Optional[str] = Query(None, description="DC Protocol (Jan 22, 2026): Filter by last interaction date (to)"),
    days_since_interaction: Optional[str] = Query(None, description="DC Protocol (Jan 22, 2026): Filter by days since last interaction - lt6, 6-15, 15-30, gt30"),
    has_recent_comments: Optional[bool] = None,
    exclude_closed: Optional[bool] = None,
    no_followup: Optional[bool] = Query(None, description="Filter active leads with no next follow-up date"),
    involved_employee_id: Optional[int] = Query(None, description="DC-INCENTIVE-LEADS-001: Filter leads where this specific employee is handler/telecaller/field_staff"),
    involved_role: Optional[str] = Query(None, description="DC-INCENTIVE-LEADS-001: Restrict to a specific role for involved_employee_id: handler, telecaller, field_staff"),
    filter_telecaller_id: Optional[int] = Query(None, description="Filter by specific telecaller staff ID"),
    filter_field_staff_id: Optional[int] = Query(None, description="Filter by specific field staff ID"),
    page: int = 1,
    per_page: int = 20,
    db: Session = Depends(get_db),
    current_employee: StaffEmployee = Depends(get_current_staff_user)
):
    """List leads with filters - DC Protocol enforced. Enhanced with follow-up, comment, and assignment filters.
    
    RBAC Visibility Rules:
    - VGK/EA admins: Can view all leads
    - Staff with direct reports (leaders): Can view all leads 
    - Manager/Employee without reports: Can ONLY view leads assigned to them
    """
    # DC Protocol (Feb 2026): Safety cap — prevents OOM crash from large per_page requests
    per_page = min(per_page, 100)
    # Check visibility permissions
    staff_type = (current_employee.staff_type or '').upper()
    is_admin = is_vgk_admin(staff_type)
    is_leader = has_direct_reports(current_employee.id, db, StaffEmployee)
    can_view_all = is_admin or is_leader
    
    query = db.query(CRMLead).filter(CRMLead.company_id == company_id)
    
    # VISIBILITY FILTER LOGIC:
    # The visibility filters (primary_owner, assigned_to_me) work for ALL users.
    # For non-privileged users, they filter within their allowed scope.
    # For privileged users, they filter across all leads.
    
    # Apply visibility filters first (these apply to all users regardless of privilege)
    if primary_owner:
        # "My Leads" - filter to leads where staff is primary owner OR assigned as telecaller/field_staff
        # DC Protocol (Mar 2026): Include all "my" leads: owned + handler roles, so synced leads
        # assigned via telecaller_id (not just primary_owner_id) also appear in staff's own leads page.
        # DC Protocol (Mar 2026): Also include truly unassigned sheet leads so all staff can see and claim them.
        query = query.filter(
            or_(
                and_(
                    CRMLead.primary_owner_type == 'staff',
                    CRMLead.primary_owner_id == current_employee.id
                ),
                CRMLead.telecaller_id == current_employee.id,
                CRMLead.field_staff_id == current_employee.id,
                and_(
                    CRMLead.handler_type == 'unassigned',
                    CRMLead.status == 'new',
                    CRMLead.primary_owner_id.is_(None),
                    CRMLead.telecaller_id.is_(None),
                    CRMLead.field_staff_id.is_(None),
                ),
            )
        )
    elif assigned_to_me:
        # "Assigned Leads" - filter to leads assigned to current user
        query = query.filter(or_(
            CRMLead.telecaller_id == current_employee.id,
            CRMLead.field_staff_id == current_employee.id,
            CRMLead.handler_id == current_employee.emp_code  # Legacy fallback
        ))
    elif not can_view_all:
        # Non-privileged users with no specific filter: see their scope only
        # (owned/assigned leads + fresh/unassigned leads for claiming)
        query = query.filter(or_(
            # Leads where they are primary owner
            and_(
                CRMLead.primary_owner_type == 'staff',
                CRMLead.primary_owner_id == current_employee.id
            ),
            # Leads assigned to them
            CRMLead.telecaller_id == current_employee.id,
            CRMLead.field_staff_id == current_employee.id,
            CRMLead.handler_id == current_employee.emp_code,  # Legacy fallback
            # New/Unassigned leads visible to all for claiming
            and_(
                CRMLead.status == 'new',
                CRMLead.handler_type == 'unassigned',
                CRMLead.telecaller_id.is_(None),
                CRMLead.field_staff_id.is_(None),
                CRMLead.primary_owner_id.is_(None)
            )
        ))
    
    # DC Protocol (Jan 1, 2026): Handler role-based filtering for Staff Leads page
    # Filters leads where current user is assigned as a specific handler role
    if as_handler_role:
        handler_role = as_handler_role.lower()
        if handler_role == 'telecaller':
            query = query.filter(CRMLead.telecaller_id == current_employee.id)
        elif handler_role == 'field_staff':
            query = query.filter(CRMLead.field_staff_id == current_employee.id)
        elif handler_role == 'partner':
            # Partner role filtering: Staff users are not partners in this system
            # OfficialPartner is a separate entity with its own authentication
            # Staff cannot be partners, so return empty result for this role
            query = query.filter(False)
        elif handler_role == 'mnr_handler':
            # MNR handler uses employee code/emp_code for matching
            query = query.filter(CRMLead.mnr_handler_id == current_employee.emp_code)
        elif handler_role == 'any':
            # Any handler role - leads where user is assigned as any type of handler
            # Note: Partner role excluded for staff users (separate entity)
            handler_conditions = [
                CRMLead.telecaller_id == current_employee.id,
                CRMLead.field_staff_id == current_employee.id,
                CRMLead.mnr_handler_id == current_employee.emp_code,
            ]
            query = query.filter(or_(*handler_conditions))
    
    # Telecaller / Field Staff direct filters
    if filter_telecaller_id:
        query = query.filter(CRMLead.telecaller_id == filter_telecaller_id)
    if filter_field_staff_id:
        query = query.filter(CRMLead.field_staff_id == filter_field_staff_id)

    # DC-INCENTIVE-LEADS-001: Filter by a specific staff employee across their roles
    if involved_employee_id:
        _inv_emp = db.query(StaffEmployee).filter(StaffEmployee.id == involved_employee_id).first()
        _inv_role = (involved_role or '').lower()
        if _inv_emp:
            if _inv_role == 'telecaller':
                query = query.filter(CRMLead.telecaller_id == _inv_emp.id)
            elif _inv_role == 'field_staff':
                query = query.filter(CRMLead.field_staff_id == _inv_emp.id)
            elif _inv_role == 'handler':
                query = query.filter(CRMLead.handler_id == _inv_emp.emp_code)
            else:
                # DC-INCENTIVE-LEADS-001: "All Roles" only counts explicitly filled slots
                # (telecaller_id / field_staff_id). handler_id is excluded here because
                # it can be set without being visible in the edit form, which would inflate
                # incentive counts. Users can select "As Handler" manually if needed.
                query = query.filter(or_(
                    CRMLead.telecaller_id == _inv_emp.id,
                    CRMLead.field_staff_id == _inv_emp.id,
                    CRMLead.support_staff_id == _inv_emp.id,
                    CRMLead.technical_staff1_id == _inv_emp.id,
                    CRMLead.technical_id == _inv_emp.id,
                ))

    if exclude_closed:
        query = query.filter(~CRMLead.status.in_(['won', 'lost']))
    
    # DC Protocol (Jan 1, 2026): Filter active leads with no next follow-up date scheduled
    if no_followup:
        query = query.filter(
            CRMLead.next_followup_date.is_(None),
            ~CRMLead.status.in_(['won', 'lost', 'on_hold'])
        )
    
    if status:
        if status == 'closed':
            query = query.filter(CRMLead.status.in_(['won', 'lost']))
        else:
            query = query.filter(CRMLead.status == status)
    if priority:
        query = query.filter(CRMLead.priority == priority)
    # DC Protocol (Jul 2026 Task 11): Category filter — dual-match logic for both string name and integer ID.
    if category or category_id is not None:
        _cat_ids = []
        if category_id is not None:
            _cat_ids.append(category_id)
        if category:
            if isinstance(category, int) or (isinstance(category, str) and category.isdigit()):
                _cat_ids.append(int(category))
            else:
                _matched_cats = db.query(SignupCategory.id).filter(
                    or_(
                        SignupCategory.name.ilike(category),
                        SignupCategory.name.ilike(f"%{category}%"),
                        SignupCategory.slug.ilike(category)
                    )
                ).all()
                _cat_ids.extend([r.id for r in _matched_cats])

        _cat_ids = list(set(_cat_ids))
        if _cat_ids:
            _deal_lead_sq = (
                db.query(CRMLeadDeal.lead_id)
                .filter(CRMLeadDeal.revenue_category_id.in_(_cat_ids))
                .scalar_subquery()
            )
            query = query.filter(or_(
                CRMLead.category_id.in_(_cat_ids),
                CRMLead.id.in_(_deal_lead_sq)
            ))
        else:
            query = query.filter(CRMLead.id == -1)
    if handler_type:
        query = query.filter(CRMLead.handler_type == handler_type)
    if handler_id:
        query = query.filter(CRMLead.handler_id == handler_id)
    if search:
        _st = f'%{search}%'
        _sc = [
            CRMLead.name.ilike(_st),
            CRMLead.email.ilike(_st),
            CRMLead.phone.ilike(_st),
            CRMLead.city.ilike(_st),
            CRMLead.pincode.ilike(_st),
            CRMLead.source.ilike(_st),
            CRMLead.application_no.ilike(_st),
            CRMLead.source_ref_name.ilike(_st),
            CRMLead.source_ref_id.ilike(_st),
            CRMLead.mnr_handler_id.ilike(_st),
        ]
        _id_s = search.lstrip('#').strip()
        if _id_s.isdigit():
            _sc.append(CRMLead.id == int(_id_s))
        _mnr_uid_s = [str(u.id) for u in db.query(User.id).filter(User.name.ilike(_st)).all()]
        if _mnr_uid_s:
            _sc.append(CRMLead.mnr_handler_id.in_(_mnr_uid_s))
        query = query.filter(or_(*_sc))

    if next_followup_from:
        try:
            date_from = datetime.fromisoformat(next_followup_from.replace('Z', '+00:00'))
            query = query.filter(CRMLead.next_followup_date >= date_from)
        except:
            pass
    if next_followup_to:
        try:
            date_to = datetime.fromisoformat(next_followup_to.replace('Z', '+00:00'))
            query = query.filter(CRMLead.next_followup_date <= date_to)
        except:
            pass
    
    if last_followup_from:
        try:
            date_from = datetime.fromisoformat(last_followup_from.replace('Z', '+00:00'))
            query = query.filter(CRMLead.last_contact_date >= date_from)
        except:
            pass
    if last_followup_to:
        try:
            date_to = datetime.fromisoformat(last_followup_to.replace('Z', '+00:00'))
            query = query.filter(CRMLead.last_contact_date <= date_to)
        except:
            pass
    
    if has_recent_comments:
        seven_days_ago = get_indian_time() - timedelta(days=7)
        lead_ids_with_recent_comments = db.query(CRMLeadNote.lead_id).filter(
            CRMLeadNote.company_id == company_id,
            CRMLeadNote.created_at >= seven_days_ago
        ).distinct().all()
        lead_ids = [lid[0] for lid in lead_ids_with_recent_comments]
        query = query.filter(CRMLead.id.in_(lead_ids))
    
    # DC Protocol (Jan 22, 2026): Last Interacted date range filter
    # Filters leads based on their computed max(last_interacted_at) across all sources
    if last_interacted_from or last_interacted_to:
        # Parse dates
        from_date = None
        to_date = None
        if last_interacted_from:
            try:
                from_date = datetime.fromisoformat(last_interacted_from.replace('Z', '+00:00'))
            except:
                pass
        if last_interacted_to:
            try:
                to_date = datetime.fromisoformat(last_interacted_to.replace('Z', '+00:00'))
            except:
                pass
        
        # Compute max last_interacted_at per lead and filter based on that
        # Use subqueries to get max timestamps from each source
        from sqlalchemy import case
        
        # Subquery for max note date per lead
        max_note = db.query(
            CRMLeadNote.lead_id,
            func.max(CRMLeadNote.created_at).label('max_date')
        ).filter(CRMLeadNote.company_id == company_id).group_by(CRMLeadNote.lead_id).subquery()
        
        # Subquery for max followup date per lead
        max_followup = db.query(
            CRMLeadFollowUp.lead_id,
            func.max(CRMLeadFollowUp.created_at).label('max_date')
        ).filter(CRMLeadFollowUp.company_id == company_id).group_by(CRMLeadFollowUp.lead_id).subquery()
        
        # Subquery for max revenue date per lead
        max_revenue = db.query(
            CRMRevenueEntry.lead_id,
            func.max(CRMRevenueEntry.created_at).label('max_date')
        ).filter(CRMRevenueEntry.company_id == company_id).group_by(CRMRevenueEntry.lead_id).subquery()
        
        # Build query with GREATEST to find max across all sources
        # Note: We compute this per lead and filter
        leads_with_dates = db.query(
            CRMLead.id,
            func.greatest(
                CRMLead.updated_at,
                func.coalesce(max_note.c.max_date, CRMLead.updated_at),
                func.coalesce(max_followup.c.max_date, CRMLead.updated_at),
                func.coalesce(max_revenue.c.max_date, CRMLead.updated_at)
            ).label('last_interacted')
        ).outerjoin(max_note, CRMLead.id == max_note.c.lead_id
        ).outerjoin(max_followup, CRMLead.id == max_followup.c.lead_id
        ).outerjoin(max_revenue, CRMLead.id == max_revenue.c.lead_id
        ).filter(CRMLead.company_id == company_id)
        
        # Apply date range filters on the computed last_interacted
        if from_date:
            leads_with_dates = leads_with_dates.having(
                func.greatest(
                    CRMLead.updated_at,
                    func.coalesce(max_note.c.max_date, CRMLead.updated_at),
                    func.coalesce(max_followup.c.max_date, CRMLead.updated_at),
                    func.coalesce(max_revenue.c.max_date, CRMLead.updated_at)
                ) >= from_date
            )
        if to_date:
            leads_with_dates = leads_with_dates.having(
                func.greatest(
                    CRMLead.updated_at,
                    func.coalesce(max_note.c.max_date, CRMLead.updated_at),
                    func.coalesce(max_followup.c.max_date, CRMLead.updated_at),
                    func.coalesce(max_revenue.c.max_date, CRMLead.updated_at)
                ) <= to_date
            )
        
        leads_with_dates = leads_with_dates.group_by(CRMLead.id, CRMLead.updated_at, max_note.c.max_date, max_followup.c.max_date, max_revenue.c.max_date)
        
        lead_ids_in_range = [r[0] for r in leads_with_dates.all()]
        
        if lead_ids_in_range:
            query = query.filter(CRMLead.id.in_(lead_ids_in_range))
        else:
            query = query.filter(CRMLead.id == -1)  # Force empty result
    
    # DC Protocol (Jan 22, 2026): Days Since Interaction filter
    # Filters leads by number of days since last interaction (uses created_at if never interacted)
    # Won leads are excluded from this filter (they remain visible regardless of filter value)
    if days_since_interaction:
        today = get_indian_time().date()
        
        # Build subquery to get max interaction date per lead
        max_note_sub = db.query(
            CRMLeadNote.lead_id,
            func.max(CRMLeadNote.created_at).label('max_date')
        ).filter(CRMLeadNote.company_id == company_id).group_by(CRMLeadNote.lead_id).subquery()
        
        max_followup_sub = db.query(
            CRMFollowUp.lead_id,
            func.max(CRMFollowUp.followup_date).label('max_date')
        ).filter(CRMFollowUp.company_id == company_id).group_by(CRMFollowUp.lead_id).subquery()
        
        max_revenue_sub = db.query(
            CRMLeadRevenue.lead_id,
            func.max(CRMLeadRevenue.updated_at).label('max_date')
        ).filter(CRMLeadRevenue.company_id == company_id).group_by(CRMLeadRevenue.lead_id).subquery()
        
        # Compute last_interacted using greatest of all sources, fallback to created_at
        from sqlalchemy import cast, Date
        last_interacted_expr = func.greatest(
            cast(CRMLead.created_at, Date),
            func.coalesce(cast(max_note_sub.c.max_date, Date), cast(CRMLead.created_at, Date)),
            func.coalesce(cast(max_followup_sub.c.max_date, Date), cast(CRMLead.created_at, Date)),
            func.coalesce(cast(max_revenue_sub.c.max_date, Date), cast(CRMLead.created_at, Date))
        )
        
        # Calculate days since last interaction
        days_diff = func.extract('day', func.age(func.current_date(), last_interacted_expr))
        
        # Build subquery to get lead IDs matching the days filter
        days_query = db.query(CRMLead.id).outerjoin(
            max_note_sub, max_note_sub.c.lead_id == CRMLead.id
        ).outerjoin(
            max_followup_sub, max_followup_sub.c.lead_id == CRMLead.id
        ).outerjoin(
            max_revenue_sub, max_revenue_sub.c.lead_id == CRMLead.id
        ).filter(CRMLead.company_id == company_id)
        
        # Apply days range filter based on parameter
        # Won leads are excluded from days filter (show regardless)
        if days_since_interaction == 'lt6':
            days_query = days_query.filter(
                or_(
                    CRMLead.status == 'won',
                    days_diff < 6
                )
            )
        elif days_since_interaction == '6-15':
            days_query = days_query.filter(
                or_(
                    CRMLead.status == 'won',
                    and_(days_diff >= 6, days_diff <= 15)
                )
            )
        elif days_since_interaction == '15-30':
            days_query = days_query.filter(
                or_(
                    CRMLead.status == 'won',
                    and_(days_diff > 15, days_diff <= 30)
                )
            )
        elif days_since_interaction == 'gt30':
            days_query = days_query.filter(
                or_(
                    CRMLead.status == 'won',
                    days_diff > 30
                )
            )
        
        days_lead_ids = [r[0] for r in days_query.all()]
        if days_lead_ids:
            query = query.filter(CRMLead.id.in_(days_lead_ids))
        else:
            query = query.filter(CRMLead.id == -1)  # Force empty result
    
    total = query.count()
    
    leads = query.order_by(CRMLead.created_at.desc()).offset((page - 1) * per_page).limit(per_page).all()

    from app.models.staff_accounts import AssociatedCompany

    # ── DC Protocol (Mar 2026): Batch-load all related data — eliminates 140 N+1 queries ──
    _lead_ids      = [l.id for l in leads]
    _cat_ids       = list({l.category_id for l in leads if l.category_id})
    _co_ids        = list({l.company_id  for l in leads if l.company_id})
    _owner_ids     = list({l.primary_owner_id for l in leads
                           if l.primary_owner_type == 'staff' and l.primary_owner_id})

    _cat_map  = {c.id: c.name for c in db.query(SignupCategory).filter(SignupCategory.id.in_(_cat_ids)).all()} if _cat_ids else {}
    _co_map   = {c.id: c.company_name for c in db.query(AssociatedCompany).filter(AssociatedCompany.id.in_(_co_ids)).all()} if _co_ids else {}
    _owner_map: dict = {}
    if _owner_ids:
        for emp in db.query(StaffEmployee).filter(StaffEmployee.id.in_(_owner_ids)).all():
            n = emp.full_name or (f"{emp.first_name or ''} {emp.last_name or ''}".strip()) or emp.emp_code
            _owner_map[emp.id] = {'name': n, 'emp_code': emp.emp_code}

    # DC-LIST-LEADS-HANDLER-NAMES-001: Batch-resolve telecaller + field_staff names.
    # list_leads only returned integer IDs; Staff Leads page showed "—" for every lead.
    # One query covering both roles — zero N+1 cost.
    _tc_ids  = list({l.telecaller_id  for l in leads if l.telecaller_id})
    _fs_ids  = list({l.field_staff_id for l in leads if l.field_staff_id})
    _hnd_ids = list(set(_tc_ids) | set(_fs_ids))
    _handler_map: dict = {}
    if _hnd_ids:
        for emp in db.query(StaffEmployee).filter(StaffEmployee.id.in_(_hnd_ids)).all():
            n = emp.full_name or (f"{emp.first_name or ''} {emp.last_name or ''}".strip()) or emp.emp_code
            _handler_map[emp.id] = {'name': n, 'emp_code': emp.emp_code}

    # Latest note per lead — one query using a subquery for max created_at
    _note_map: dict = {}
    if _lead_ids:
        from sqlalchemy import tuple_ as _tuple
        _max_note_sq = (
            db.query(CRMLeadNote.lead_id, func.max(CRMLeadNote.created_at).label('mx'))
            .filter(CRMLeadNote.lead_id.in_(_lead_ids))
            .group_by(CRMLeadNote.lead_id)
            .subquery()
        )
        _note_rows = (
            db.query(CRMLeadNote)
            .join(_max_note_sq, (CRMLeadNote.lead_id == _max_note_sq.c.lead_id) &
                                (CRMLeadNote.created_at == _max_note_sq.c.mx))
            .all()
        )
        for _n in _note_rows:
            _note_map[_n.lead_id] = _n

    # Batch max dates for last_interacted_at (notes + followups + revenue — one query each)
    _note_max_map: dict = {}
    _fu_max_map:   dict = {}
    _rev_max_map:  dict = {}
    if _lead_ids:
        for row in db.query(CRMLeadNote.lead_id, func.max(CRMLeadNote.created_at)).filter(
                CRMLeadNote.lead_id.in_(_lead_ids)).group_by(CRMLeadNote.lead_id).all():
            _note_max_map[row[0]] = row[1]
        for row in db.query(CRMLeadFollowUp.lead_id, func.max(CRMLeadFollowUp.created_at)).filter(
                CRMLeadFollowUp.lead_id.in_(_lead_ids)).group_by(CRMLeadFollowUp.lead_id).all():
            _fu_max_map[row[0]] = row[1]
        for row in db.query(CRMRevenueEntry.lead_id, func.max(CRMRevenueEntry.created_at)).filter(
                CRMRevenueEntry.lead_id.in_(_lead_ids)).group_by(CRMRevenueEntry.lead_id).all():
            _rev_max_map[row[0]] = row[1]

    leads_data = []
    for lead in leads:
        try:
            lead_dict = lead.to_dict()
            lead_dict['category_name'] = _cat_map.get(lead.category_id)
            lead_dict['company_name']  = _co_map.get(lead.company_id)

            _note = _note_map.get(lead.id)
            lead_dict['latest_comment'] = _note.to_dict() if _note else None

            # Owner details
            if lead.primary_owner_type == 'staff' and lead.primary_owner_id:
                _ow = _owner_map.get(lead.primary_owner_id)
                lead_dict['primary_owner_name']        = _ow['name']     if _ow else None
                lead_dict['primary_owner_employee_id'] = _ow['emp_code'] if _ow else None
            else:
                lead_dict['primary_owner_name']        = None
                lead_dict['primary_owner_employee_id'] = None

            # DC-LIST-LEADS-HANDLER-NAMES-001: Telecaller + Field Staff resolved names
            _tc = _handler_map.get(lead.telecaller_id)  if lead.telecaller_id  else None
            _fs = _handler_map.get(lead.field_staff_id) if lead.field_staff_id else None
            lead_dict['telecaller_name']  = _tc['name']     if _tc else None
            lead_dict['telecaller_code']  = _tc['emp_code'] if _tc else None
            lead_dict['field_staff_name'] = _fs['name']     if _fs else None
            lead_dict['field_staff_code'] = _fs['emp_code'] if _fs else None

            # RBAC: can change owner?
            try:
                can_change, reason = can_change_primary_owner(lead, current_employee, db)
                lead_dict['can_change_owner']   = can_change
                lead_dict['owner_change_reason'] = reason
            except Exception:
                lead_dict['can_change_owner']   = False
                lead_dict['owner_change_reason'] = 'error'

            # last_interacted_at from pre-fetched maps
            try:
                _dates = [d for d in [
                    lead.updated_at,
                    _note_max_map.get(lead.id),
                    _fu_max_map.get(lead.id),
                    _rev_max_map.get(lead.id),
                ] if d]
                lead_dict['last_interacted_at'] = max(_dates).isoformat() if _dates else None
            except Exception:
                lead_dict['last_interacted_at'] = None

            leads_data.append(lead_dict)
        except Exception as e:
            import logging
            logging.error(f"list_leads: Error processing lead {lead.id}: {str(e)}")
            continue
    
    return {
        'success': True,
        'data': leads_data,
        'pagination': {
            'page': page,
            'per_page': per_page,
            'total': total,
            'pages': (total + per_page - 1) // per_page
        }
    }


@router.get("/my-downline")
def get_my_downline(
    company_id: Optional[int] = Query(None, description="Company ID to filter downline (DC Protocol)"),
    employee_status: Optional[str] = Query(None, description="Filter by employee status: active, resigned, all (default: active + resigned with leads)"),
    db: Session = Depends(get_db),
    current_employee: StaffEmployee = Depends(get_current_staff_user)
):
    """Get current user's downline employees for Team Leads filter dropdown.
    DC Protocol (Jan 1, 2026): Returns employees filtered by company access.
    - VGK admins: See ALL staff with company access (base_company_id OR data_companies)
    - Regular users: See only their downline with company access
    Company access = base_company_id matches OR company_id is in data_companies array
    
    DC Protocol (Jan 28, 2026): Employee status filter
    - Default: Returns active employees + resigned employees who still have leads
    - employee_status=active: Only active employees
    - employee_status=resigned: Only resigned employees  
    - employee_status=all: All employees regardless of status
    """
    def has_company_access(emp, target_company_id):
        """Check if employee has access to the target company via base or data_companies"""
        if not target_company_id:
            return True
        if emp.base_company_id == target_company_id:
            return True
        data_companies = emp.data_companies or []
        if isinstance(data_companies, list) and target_company_id in data_companies:
            return True
        return False
    
    def format_employee(emp, is_resigned=False):
        """Format employee data for response"""
        emp_name = emp.full_name
        if not emp_name and emp.first_name:
            emp_name = f"{emp.first_name} {emp.last_name or ''}".strip()
        if not emp_name:
            emp_name = emp.emp_code
        return {
            'id': emp.id,
            'name': emp_name,
            'emp_code': emp.emp_code,
            'department': emp.department.name if emp.department else None,
            'designation': emp.designation,
            'status': emp.status or 'active',
            'is_resigned': emp.status == 'resigned'
        }
    
    def get_resigned_emp_codes_with_leads():
        """Get list of resigned employee codes that still have leads assigned"""
        leads_with_resigned = db.query(CRMLead.handler_id).filter(
            CRMLead.handler_type == 'staff'
        ).distinct().all()
        return [l[0] for l in leads_with_resigned if l[0]]
    
    staff_type = (current_employee.staff_type or '').upper()
    is_admin = is_vgk_admin(staff_type)
    hidden_ids = _get_hidden_employee_ids(db, StaffEmployee)
    
    downline_data = []
    resigned_with_leads_codes = get_resigned_emp_codes_with_leads() if not employee_status or employee_status not in ['active', 'resigned', 'all'] else []
    
    if is_admin:
        if employee_status == 'active':
            all_staff = db.query(StaffEmployee).filter(
                StaffEmployee.status == 'active',
                StaffEmployee.id != current_employee.id
            ).order_by(StaffEmployee.full_name).all()
        elif employee_status == 'resigned':
            all_staff = db.query(StaffEmployee).filter(
                StaffEmployee.status == 'resigned',
                StaffEmployee.id != current_employee.id
            ).order_by(StaffEmployee.full_name).all()
        elif employee_status == 'all':
            all_staff = db.query(StaffEmployee).filter(
                StaffEmployee.id != current_employee.id
            ).order_by(StaffEmployee.full_name).all()
        else:
            active_staff = db.query(StaffEmployee).filter(
                StaffEmployee.status == 'active',
                StaffEmployee.id != current_employee.id
            ).order_by(StaffEmployee.full_name).all()
            resigned_with_leads = db.query(StaffEmployee).filter(
                StaffEmployee.status == 'resigned',
                StaffEmployee.emp_code.in_(resigned_with_leads_codes),
                StaffEmployee.id != current_employee.id
            ).order_by(StaffEmployee.full_name).all()
            all_staff = list(active_staff) + list(resigned_with_leads)
        
        for emp in all_staff:
            if emp.id not in hidden_ids and has_company_access(emp, company_id):
                downline_data.append(format_employee(emp))
    else:
        all_downline_ids = get_recursive_downline(
            current_employee.id, db, StaffEmployee, 
            max_depth=10, include_manager=False
        )
        all_downline_ids = [eid for eid in all_downline_ids if eid not in hidden_ids]
        
        if all_downline_ids:
            downline_emps = db.query(StaffEmployee).filter(
                StaffEmployee.id.in_(all_downline_ids)
            ).all()
        else:
            downline_emps = []
        
        for emp in downline_emps:
            include_emp = False
            if employee_status == 'active':
                include_emp = emp.status == 'active'
            elif employee_status == 'resigned':
                include_emp = emp.status == 'resigned'
            elif employee_status == 'all':
                include_emp = True
            else:
                include_emp = emp.status == 'active' or (emp.status == 'resigned' and emp.emp_code in resigned_with_leads_codes)
            
            if include_emp and has_company_access(emp, company_id):
                downline_data.append(format_employee(emp))
    
    self_name = current_employee.full_name
    if not self_name and current_employee.first_name:
        self_name = f"{current_employee.first_name} {current_employee.last_name or ''}".strip()
    if not self_name:
        self_name = current_employee.emp_code
    
    self_in_company = has_company_access(current_employee, company_id)
    
    return {
        'success': True,
        'self': {
            'id': current_employee.id,
            'name': self_name,
            'emp_code': current_employee.emp_code,
            'in_company': self_in_company
        } if self_in_company else None,
        'data': downline_data,
        'total': len(downline_data)
    }


@router.get("/team-leads")
def list_team_leads(
    company_id: Optional[int] = Query(None, description="Company ID for DC Protocol (optional for VGK4U - all companies)"),
    team_member_id: Optional[int] = Query(None, description="Filter by specific team member ID"),
    filter_by: Optional[str] = Query(None, description="Filter mode: 'owner', 'handler', 'fresh' (unassigned)"),
    status: Optional[str] = None,
    priority: Optional[str] = None,
    category_id: Optional[int] = None,
    category: Optional[str] = Query(None, description="DC Protocol (Feb 2026): Filter by category name for cross-company queries"),
    handler_type: Optional[str] = None,
    primary_owner: Optional[bool] = Query(None, description="Filter leads where current user is primary owner"),
    as_handler_role: Optional[str] = Query(None, description="Filter by handler role: telecaller, field_staff, mnr_handler, partner, any"),
    search: Optional[str] = None,
    handler_search: Optional[str] = Query(None, description="Search by handler MNR ID or Partner code"),
    next_followup_from: Optional[str] = None,
    next_followup_to: Optional[str] = None,
    exclude_closed: Optional[bool] = None,
    no_followup: Optional[bool] = Query(None, description="Filter active leads with no next follow-up date"),
    last_interacted_from: Optional[str] = Query(None, description="DC Protocol (Jan 22, 2026): Filter by last interaction date (from)"),
    last_interacted_to: Optional[str] = Query(None, description="DC Protocol (Jan 22, 2026): Filter by last interaction date (to)"),
    days_since_interaction: Optional[str] = Query(None, description="DC Protocol (Jan 22, 2026): Filter by days since last interaction - lt6, 6-15, 15-30, gt30"),
    quick_filter: Optional[str] = Query(None, description="DC Protocol (Jan 22, 2026): Quick filter: 'all', 'today', 'overdue', 'no_followup'"),
    source: Optional[str] = Query(None, description="Filter by lead source name"),
    sort_by: Optional[str] = Query('created_at', description="Sort column: created_at|name|status|priority|next_followup_date|last_contact_date|category_name|company_name|owner_name"),
    sort_dir: Optional[str] = Query('desc', description="Sort direction: asc or desc"),
    page: int = 1,
    per_page: int = 20,
    db: Session = Depends(get_db),
    current_employee: StaffEmployee = Depends(get_current_staff_user)
):
    """List leads from current user's team (downline hierarchy).
    
    DC Protocol Compliance:
    - Leads are filtered by company_id
    - Downline is filtered to only include employees assigned to the requested company
    - VGK4U Supreme bypasses downline filter (sees all company leads)
    - This ensures strict company-level data segregation
    
    Filter modes:
    - 'owner': Leads where team member is primary owner
    - 'handler': Leads where team member is any handler (telecaller/field_staff/mnr_handler/partner)
    - 'fresh': Unassigned leads available for claiming
    - None/default: All leads (owner OR handler)
    """
    # Check if VGK4U Supreme (full access bypass)
    staff_type = (current_employee.staff_type or '').upper()
    is_admin = is_vgk_admin(staff_type)
    
    all_downline_ids = get_recursive_downline(
        current_employee.id, db, StaffEmployee, 
        max_depth=10, include_manager=False
    )
    hidden_ids = _get_hidden_employee_ids(db, StaffEmployee)
    all_downline_ids = [eid for eid in all_downline_ids if eid not in hidden_ids]
    
    company_downline_ids = []
    downline_emp_codes = []
    downline_partner_ids = []
    
    if all_downline_ids:
        downline_employees = db.query(StaffEmployee).filter(
            StaffEmployee.id.in_(all_downline_ids)
        ).all()
        for emp in downline_employees:
            if company_id is None or emp.base_company_id == company_id:
                company_downline_ids.append(emp.id)
                downline_emp_codes.append(emp.emp_code)
    
    # VGK4U Supreme bypass: If admin with no company downline, show ALL leads
    if is_admin and not company_downline_ids:
        # Get all active staff for filtering (company-specific or all)
        staff_query = db.query(StaffEmployee).filter(StaffEmployee.status == 'active')
        if company_id:
            staff_query = staff_query.filter(StaffEmployee.base_company_id == company_id)
        all_company_staff = [s for s in staff_query.all() if s.id not in hidden_ids]
        company_downline_ids = [s.id for s in all_company_staff]
        downline_emp_codes = [s.emp_code for s in all_company_staff]
    
    if not company_downline_ids and not is_admin:
        # No team members in this company - return empty result
        return {
            'success': True,
            'data': [],
            'team_size': 0,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': 0,
                'pages': 0
            }
        }
    
    downline_ids = company_downline_ids if company_downline_ids else []
    
    if team_member_id:
        # DC Protocol (Jan 1, 2026): Cross-company team member filtering
        # Check authorization against FULL downline (all_downline_ids), not company-filtered list
        # This allows viewing leads owned by team member in ANY company
        # DC Protocol: Menu-based access control - page assignment = full access
        # if team_member_id not in all_downline_ids and not is_admin:
        #     raise HTTPException(status_code=403, detail="Specified team member is not in your team")
        target_ids = [team_member_id]
        # Update emp_codes for target member
        target_emp = db.query(StaffEmployee).filter(StaffEmployee.id == team_member_id).first()
        downline_emp_codes = [target_emp.emp_code] if target_emp else []
    else:
        target_ids = downline_ids
    
    # DC Protocol (Feb 2026): Build base query - company_id is optional for VGK4U users
    # DC Protocol (Mar 2026): Auto-detect company_id from user's base_company_id for non-admin staff
    if not company_id and not is_admin:
        company_id = current_employee.base_company_id
        if not company_id:
            raise HTTPException(status_code=400, detail="company_id is required for non-admin users")
    query = db.query(CRMLead)
    if company_id:
        query = query.filter(CRMLead.company_id == company_id)
    
    # Build visibility filter based on filter_by mode
    if filter_by == 'owner':
        # Only leads where team member is primary owner
        query = query.filter(
            CRMLead.primary_owner_type == 'staff',
            CRMLead.primary_owner_id.in_(target_ids)
        )
    elif filter_by == 'handler':
        # Leads where team member is any handler (telecaller/field_staff/mnr_handler/partner)
        handler_conditions = [
            CRMLead.telecaller_id.in_(target_ids),
            CRMLead.field_staff_id.in_(target_ids),
        ]
        if downline_emp_codes:
            handler_conditions.append(CRMLead.mnr_handler_id.in_(downline_emp_codes))
        # Note: Partner handler uses associated_partner_id which maps to OfficialPartner.id, not staff id
        query = query.filter(or_(*handler_conditions))
    elif filter_by == 'fresh':
        # Fresh/Unassigned leads available for claiming (no owner, no handlers)
        query = query.filter(
            CRMLead.status == 'new',
            CRMLead.handler_type == 'unassigned',
            CRMLead.telecaller_id.is_(None),
            CRMLead.field_staff_id.is_(None),
            CRMLead.primary_owner_id.is_(None)
        )
    elif is_admin and not team_member_id:
        # DC Protocol (Jan 1, 2026): VGK4U Supreme bypass ONLY when no team member filter
        # When team_member_id is specified, admins MUST respect the filter like all other users
        pass  # No additional filter needed, company_id already applied
    else:
        # Default: Show all leads where team member is owner OR handler
        # DC Protocol (Jan 1, 2026): This applies to ALL users including admins when team_member_id is set
        handler_conditions = [
            # Primary owner
            and_(
                CRMLead.primary_owner_type == 'staff',
                CRMLead.primary_owner_id.in_(target_ids)
            ),
            # Handler assignments
            CRMLead.telecaller_id.in_(target_ids),
            CRMLead.field_staff_id.in_(target_ids),
        ]
        if downline_emp_codes:
            handler_conditions.append(CRMLead.mnr_handler_id.in_(downline_emp_codes))
        # Include fresh/unassigned leads for claiming (only when no specific team member filter)
        if not team_member_id:
            handler_conditions.append(
                and_(
                    CRMLead.status == 'new',
                    CRMLead.handler_type == 'unassigned',
                    CRMLead.telecaller_id.is_(None),
                    CRMLead.field_staff_id.is_(None),
                    CRMLead.primary_owner_id.is_(None)
                )
            )
        query = query.filter(or_(*handler_conditions))
    
    if handler_type == 'unassigned':
        query = query.filter(
            CRMLead.telecaller_id.is_(None),
            CRMLead.field_staff_id.is_(None),
            CRMLead.primary_owner_id.is_(None)
        )
    
    if as_handler_role and as_handler_role != 'any':
        if as_handler_role == 'telecaller':
            query = query.filter(CRMLead.telecaller_id.in_(target_ids))
        elif as_handler_role == 'field_staff':
            query = query.filter(CRMLead.field_staff_id.in_(target_ids))
        elif as_handler_role == 'mnr_handler':
            # DC Protocol (Mar 2026): Include current user's own emp_code, not just downline
            all_mnr_codes = list(downline_emp_codes)
            if current_employee.emp_code and current_employee.emp_code not in all_mnr_codes:
                all_mnr_codes.append(current_employee.emp_code)
            if all_mnr_codes:
                query = query.filter(CRMLead.mnr_handler_id.in_(all_mnr_codes))
            else:
                query = query.filter(False)
        elif as_handler_role == 'partner':
            # Partner filtering - associated_partner_id links to OfficialPartner table
            query = query.filter(CRMLead.associated_partner_id.isnot(None))
    
    if primary_owner:
        query = query.filter(
            CRMLead.primary_owner_type == 'staff',
            CRMLead.primary_owner_id.in_(target_ids)
        )
    
    if exclude_closed:
        query = query.filter(~CRMLead.status.in_(['won', 'lost']))
    
    if no_followup:
        query = query.filter(
            CRMLead.next_followup_date.is_(None),
            ~CRMLead.status.in_(['won', 'lost', 'on_hold'])
        )
    
    if status:
        if status == 'closed':
            query = query.filter(CRMLead.status.in_(['won', 'lost']))
        else:
            query = query.filter(CRMLead.status == status)
    if priority:
        query = query.filter(CRMLead.priority == priority)
    if category_id:
        query = query.filter(CRMLead.category_id == category_id)
    # DC Protocol (Feb 2026): Category name filter for cross-company queries
    # Uses JOIN with SignupCategory to filter by name (not category_id)
    if category:
        query = query.join(SignupCategory, CRMLead.category_id == SignupCategory.id)
        query = query.filter(SignupCategory.name == category)
    if search:
        _st = f'%{search}%'
        _sc = [
            CRMLead.name.ilike(_st),
            CRMLead.email.ilike(_st),
            CRMLead.phone.ilike(_st),
            CRMLead.city.ilike(_st),
            CRMLead.pincode.ilike(_st),
            CRMLead.source.ilike(_st),
            CRMLead.application_no.ilike(_st),
            CRMLead.source_ref_name.ilike(_st),
            CRMLead.source_ref_id.ilike(_st),
            CRMLead.mnr_handler_id.ilike(_st),
        ]
        _id_s = search.lstrip('#').strip()
        if _id_s.isdigit():
            _sc.append(CRMLead.id == int(_id_s))
        _mnr_uid_s = [str(u.id) for u in db.query(User.id).filter(User.name.ilike(_st)).all()]
        if _mnr_uid_s:
            _sc.append(CRMLead.mnr_handler_id.in_(_mnr_uid_s))
        query = query.filter(or_(*_sc))
    if source:
        query = query.filter(CRMLead.source == source)

    # DC Protocol (Jan 1, 2026): Handler search by MNR ID, name, emp_code, or Partner code
    if handler_search:
        handler_search_term = handler_search.strip().upper()
        _hs = f"%{handler_search_term}%"
        handler_conditions = []

        # Match mnr_handler_id and source_ref columns directly on the lead
        handler_conditions.append(func.upper(CRMLead.mnr_handler_id).like(_hs))
        handler_conditions.append(func.upper(CRMLead.source_ref_id).like(_hs))
        handler_conditions.append(func.upper(CRMLead.source_ref_name).like(_hs))

        # mnr_handler_id is a numeric User.id FK — resolve by User.name so that
        # name searches (e.g. "devada") match leads whose source_ref_name is NULL
        _hs_user_ids = [
            str(u.id)
            for u in db.query(User.id).filter(User.name.ilike(f'%{handler_search.strip()}%')).all()
        ]
        if _hs_user_ids:
            handler_conditions.append(CRMLead.mnr_handler_id.in_(_hs_user_ids))

        # Search by staff emp_code OR full_name (telecaller/field_staff)
        matching_staff_ids = db.query(StaffEmployee.id).filter(
            StaffEmployee.base_company_id == company_id,
            or_(
                func.upper(StaffEmployee.emp_code).like(_hs),
                func.upper(StaffEmployee.full_name).like(_hs),
            )
        ).all()
        if matching_staff_ids:
            staff_id_list = [s[0] for s in matching_staff_ids]
            handler_conditions.append(CRMLead.telecaller_id.in_(staff_id_list))
            handler_conditions.append(CRMLead.field_staff_id.in_(staff_id_list))

        # Search by partner code OR name (partners are cross-company)
        matching_partner_ids = db.query(OfficialPartner.id).filter(
            or_(
                func.upper(OfficialPartner.partner_code).like(_hs),
                func.upper(OfficialPartner.name).like(_hs),
            )
        ).all()
        if matching_partner_ids:
            partner_id_list = [p[0] for p in matching_partner_ids]
            handler_conditions.append(CRMLead.associated_partner_id.in_(partner_id_list))

        if handler_conditions:
            query = query.filter(or_(*handler_conditions))
    
    if next_followup_from:
        try:
            from_date = datetime.fromisoformat(next_followup_from.replace('Z', '+00:00'))
            query = query.filter(CRMLead.next_followup_date >= from_date)
        except:
            pass
    
    if next_followup_to:
        try:
            to_date = datetime.fromisoformat(next_followup_to.replace('Z', '+00:00'))
            query = query.filter(CRMLead.next_followup_date <= to_date)
        except:
            pass
    
    # DC Protocol (Jan 22, 2026): Quick filter for unified dropdown
    today = get_indian_time().date()
    today_start = datetime.combine(today, datetime.min.time())
    today_end = datetime.combine(today, datetime.max.time())
    
    if quick_filter:
        if quick_filter == 'today':
            # Today's leads - created today
            query = query.filter(
                CRMLead.created_at >= today_start,
                CRMLead.created_at <= today_end
            )
        elif quick_filter == 'overdue':
            # Overdue - next followup date is before today
            query = query.filter(
                CRMLead.next_followup_date < today_start,
                ~CRMLead.status.in_(['won', 'lost', 'on_hold'])
            )
        elif quick_filter == 'no_followup':
            # No followup - active leads without next followup date
            query = query.filter(
                CRMLead.next_followup_date.is_(None),
                ~CRMLead.status.in_(['won', 'lost', 'on_hold'])
            )
        # 'all' - no additional filter needed
    
    # DC Protocol (Jan 22, 2026): Last interacted date filter
    # This requires a subquery to find max activity date across notes, followups, and lead updates
    if last_interacted_from or last_interacted_to:
        # Get lead IDs that have activity within the date range
        from sqlalchemy import union_all
        
        # Build activity date subqueries
        activity_queries = []
        
        # Notes activity
        notes_activity = db.query(
            CRMLeadNote.lead_id.label('lead_id'),
            func.max(CRMLeadNote.created_at).label('last_activity')
        ).filter(CRMLeadNote.company_id == company_id).group_by(CRMLeadNote.lead_id)
        
        # Followups activity
        followups_activity = db.query(
            CRMLeadFollowUp.lead_id.label('lead_id'),
            func.max(func.coalesce(CRMLeadFollowUp.updated_at, CRMLeadFollowUp.created_at)).label('last_activity')
        ).filter(CRMLeadFollowUp.company_id == company_id).group_by(CRMLeadFollowUp.lead_id)
        
        # DC Protocol (Jan 22, 2026): Revenue entries activity
        revenue_activity = db.query(
            CRMRevenueEntry.lead_id.label('lead_id'),
            func.max(CRMRevenueEntry.created_at).label('last_activity')
        ).filter(CRMRevenueEntry.company_id == company_id).group_by(CRMRevenueEntry.lead_id)
        
        # Lead updates (updated_at on lead itself)
        lead_updates = db.query(
            CRMLead.id.label('lead_id'),
            CRMLead.updated_at.label('last_activity')
        ).filter(CRMLead.company_id == company_id)
        
        # Combine and get max per lead (includes notes, followups, revenue, lead updates)
        combined = union_all(
            notes_activity.subquery().select(),
            followups_activity.subquery().select(),
            revenue_activity.subquery().select(),
            lead_updates.subquery().select()
        ).subquery()
        
        max_activity = db.query(
            combined.c.lead_id,
            func.max(combined.c.last_activity).label('max_activity')
        ).group_by(combined.c.lead_id).subquery()
    
        # Filter by date range
        activity_filter_conditions = []
        if last_interacted_from:
            try:
                from_date = datetime.fromisoformat(last_interacted_from.replace('Z', '+00:00'))
                activity_filter_conditions.append(max_activity.c.max_activity >= from_date)
            except:
                pass
        if last_interacted_to:
            try:
                to_date = datetime.fromisoformat(last_interacted_to.replace('Z', '+00:00'))
                # Add 1 day to include the entire "to" date
                to_date_end = datetime.combine(to_date.date(), datetime.max.time())
                activity_filter_conditions.append(max_activity.c.max_activity <= to_date_end)
            except:
                pass
        
        if activity_filter_conditions:
            filtered_leads = db.query(max_activity.c.lead_id).filter(*activity_filter_conditions).subquery()
            query = query.filter(CRMLead.id.in_(db.query(filtered_leads.c.lead_id)))
    
    # DC Protocol (Jan 22, 2026): Days Since Interaction filter for Team Leads
    if days_since_interaction:
        from sqlalchemy import cast, Date
        
        # Build subquery to get max interaction date per lead
        max_note_sub = db.query(
            CRMLeadNote.lead_id,
            func.max(CRMLeadNote.created_at).label('max_date')
        ).filter(CRMLeadNote.company_id == company_id).group_by(CRMLeadNote.lead_id).subquery()
        
        max_followup_sub = db.query(
            CRMFollowUp.lead_id,
            func.max(CRMFollowUp.followup_date).label('max_date')
        ).filter(CRMFollowUp.company_id == company_id).group_by(CRMFollowUp.lead_id).subquery()
        
        max_revenue_sub = db.query(
            CRMLeadRevenue.lead_id,
            func.max(CRMLeadRevenue.updated_at).label('max_date')
        ).filter(CRMLeadRevenue.company_id == company_id).group_by(CRMLeadRevenue.lead_id).subquery()
        
        # Compute last_interacted using greatest of all sources, fallback to created_at
        last_interacted_expr = func.greatest(
            cast(CRMLead.created_at, Date),
            func.coalesce(cast(max_note_sub.c.max_date, Date), cast(CRMLead.created_at, Date)),
            func.coalesce(cast(max_followup_sub.c.max_date, Date), cast(CRMLead.created_at, Date)),
            func.coalesce(cast(max_revenue_sub.c.max_date, Date), cast(CRMLead.created_at, Date))
        )
        
        # Calculate days since last interaction
        days_diff = func.extract('day', func.age(func.current_date(), last_interacted_expr))
        
        # Build subquery to get lead IDs matching the days filter
        days_query = db.query(CRMLead.id).outerjoin(
            max_note_sub, max_note_sub.c.lead_id == CRMLead.id
        ).outerjoin(
            max_followup_sub, max_followup_sub.c.lead_id == CRMLead.id
        ).outerjoin(
            max_revenue_sub, max_revenue_sub.c.lead_id == CRMLead.id
        ).filter(CRMLead.company_id == company_id)
        
        # Apply days range filter based on parameter (Won leads pass through)
        if days_since_interaction == 'lt6':
            days_query = days_query.filter(or_(CRMLead.status == 'won', days_diff < 6))
        elif days_since_interaction == '6-15':
            days_query = days_query.filter(or_(CRMLead.status == 'won', and_(days_diff >= 6, days_diff <= 15)))
        elif days_since_interaction == '15-30':
            days_query = days_query.filter(or_(CRMLead.status == 'won', and_(days_diff > 15, days_diff <= 30)))
        elif days_since_interaction == 'gt30':
            days_query = days_query.filter(or_(CRMLead.status == 'won', days_diff > 30))
        
        days_lead_ids = [r[0] for r in days_query.all()]
        if days_lead_ids:
            query = query.filter(CRMLead.id.in_(days_lead_ids))
        else:
            query = query.filter(CRMLead.id == -1)  # Force empty result
    
    total = query.count()
    # DC Protocol (Mar 2026): Comprehensive server-side sort for team leads
    # Covers all 11 table columns: semantic ordering for status/priority,
    # JOIN-based sorts for category/company/owner, NULLS LAST for all dates.
    from sqlalchemy import case as _sa_case
    from sqlalchemy.orm import aliased as _sa_aliased
    _sd = (sort_dir or 'desc').lower()
    _sb = sort_by or 'created_at'
    _sort_expr = None

    if _sb == 'status':
        _sort_expr = _sa_case(
            (CRMLead.status == 'new', 1),
            (CRMLead.status == 'contacted', 2),
            (CRMLead.status == 'qualified', 3),
            (CRMLead.status == 'proposal', 4),
            (CRMLead.status == 'loan_process', 5),
            (CRMLead.status == 'negotiation', 6),
            (CRMLead.status == 'won', 7),
            (CRMLead.status == 'completed', 8),
            (CRMLead.status == 'lost', 9),
            (CRMLead.status == 'on_hold', 10),
            else_=99,
        )
    elif _sb == 'priority':
        _sort_expr = _sa_case(
            (CRMLead.priority == 'urgent', 1),
            (CRMLead.priority == 'high', 2),
            (CRMLead.priority == 'medium', 3),
            (CRMLead.priority == 'low', 4),
            else_=99,
        )
    elif _sb == 'category_name':
        _SortCat = _sa_aliased(SignupCategory, name='_sort_cat')
        query = query.outerjoin(_SortCat, CRMLead.category_id == _SortCat.id)
        _sort_expr = _SortCat.name
    elif _sb == 'company_name':
        _SortCo = _sa_aliased(AssociatedCompany, name='_sort_co')
        query = query.outerjoin(_SortCo, CRMLead.company_id == _SortCo.id)
        _sort_expr = _SortCo.company_name
    elif _sb == 'owner_name':
        _SortOwner = _sa_aliased(StaffEmployee, name='_sort_owner')
        query = query.outerjoin(
            _SortOwner,
            and_(CRMLead.primary_owner_type == 'staff',
                 CRMLead.primary_owner_id == _SortOwner.id)
        )
        _sort_expr = _SortOwner.full_name
    elif _sb == 'next_followup_date':
        _sort_expr = CRMLead.next_followup_date
    elif _sb == 'last_contact_date':
        _sort_expr = CRMLead.last_contact_date
    elif _sb == 'name':
        _sort_expr = CRMLead.name
    else:
        _sort_expr = CRMLead.created_at  # default

    # Apply direction with NULLS LAST so empty dates/names fall to the bottom
    if _sd == 'asc':
        _tl_ord = _sort_expr.asc().nullslast()
    else:
        _tl_ord = _sort_expr.desc().nullslast()

    leads = query.order_by(_tl_ord).offset((page - 1) * per_page).limit(per_page).all()

    lead_ids = [lead.id for lead in leads]

    category_ids = set(lead.category_id for lead in leads if lead.category_id)
    company_ids_set = set(lead.company_id for lead in leads if lead.company_id)
    owner_ids = set(lead.primary_owner_id for lead in leads if lead.primary_owner_type == 'staff' and lead.primary_owner_id)

    category_map = {}
    if category_ids:
        cats = db.query(SignupCategory).filter(SignupCategory.id.in_(category_ids)).all()
        category_map = {c.id: c.name for c in cats}
    
    company_map = {}
    if company_ids_set:
        comps = db.query(AssociatedCompany).filter(AssociatedCompany.id.in_(company_ids_set)).all()
        company_map = {c.id: c.company_name for c in comps}
    
    owner_map = {}
    if owner_ids:
        owners = db.query(StaffEmployee).filter(StaffEmployee.id.in_(owner_ids)).all()
        for o in owners:
            o_name = o.full_name
            if not o_name and o.first_name:
                o_name = f"{o.first_name} {o.last_name or ''}".strip()
            if not o_name:
                o_name = o.emp_code
            owner_map[o.id] = {'name': o_name, 'emp_code': o.emp_code, 'reporting_manager_id': o.reporting_manager_id}
    
    note_max_map = {}
    followup_max_map = {}
    revenue_max_map = {}
    if lead_ids:
        note_results = db.query(
            CRMLeadNote.lead_id,
            func.max(CRMLeadNote.created_at).label('max_date')
        ).filter(CRMLeadNote.lead_id.in_(lead_ids)).group_by(CRMLeadNote.lead_id).all()
        note_max_map = {r.lead_id: r.max_date for r in note_results}
        
        followup_results = db.query(
            CRMLeadFollowUp.lead_id,
            func.max(func.coalesce(CRMLeadFollowUp.updated_at, CRMLeadFollowUp.created_at)).label('max_date')
        ).filter(CRMLeadFollowUp.lead_id.in_(lead_ids)).group_by(CRMLeadFollowUp.lead_id).all()
        followup_max_map = {r.lead_id: r.max_date for r in followup_results}
        
        revenue_results = db.query(
            CRMRevenueEntry.lead_id,
            func.max(CRMRevenueEntry.created_at).label('max_date')
        ).filter(CRMRevenueEntry.lead_id.in_(lead_ids)).group_by(CRMRevenueEntry.lead_id).all()
        revenue_max_map = {r.lead_id: r.max_date for r in revenue_results}
    
    staff_type_upper = (current_employee.staff_type or '').upper()
    is_admin_user = is_vgk_admin(staff_type_upper)
    current_emp_code = current_employee.emp_code
    current_user_id = current_employee.id
    
    leads_data = []
    for lead in leads:
        lead_dict = lead.to_dict()
        lead_dict['category_name'] = category_map.get(lead.category_id)
        lead_dict['company_name'] = company_map.get(lead.company_id)
        
        if lead.primary_owner_type == 'staff' and lead.primary_owner_id:
            owner_info = owner_map.get(lead.primary_owner_id)
            if not owner_info:
                fallback_owner = db.query(StaffEmployee).filter(StaffEmployee.id == lead.primary_owner_id).first()
                if fallback_owner:
                    fb_name = fallback_owner.full_name
                    if not fb_name and fallback_owner.first_name:
                        fb_name = f"{fallback_owner.first_name} {fallback_owner.last_name or ''}".strip()
                    if not fb_name:
                        fb_name = fallback_owner.emp_code
                    owner_info = {'name': fb_name, 'emp_code': fallback_owner.emp_code, 'reporting_manager_id': fallback_owner.reporting_manager_id}
                    owner_map[lead.primary_owner_id] = owner_info
            if owner_info:
                lead_dict['primary_owner_name'] = owner_info['name']
                lead_dict['primary_owner_employee_id'] = owner_info['emp_code']
            else:
                lead_dict['primary_owner_name'] = None
                lead_dict['primary_owner_employee_id'] = None
        else:
            lead_dict['primary_owner_name'] = None
            lead_dict['primary_owner_employee_id'] = None
        
        if is_admin_user:
            lead_dict['can_change_owner'] = True
            lead_dict['owner_change_reason'] = 'admin'
        elif lead.primary_owner_type == 'staff' and lead.primary_owner_id == current_user_id:
            lead_dict['can_change_owner'] = True
            lead_dict['owner_change_reason'] = 'self'
        elif lead.primary_owner_type == 'staff' and lead.primary_owner_id:
            owner_info = owner_map.get(lead.primary_owner_id)
            if owner_info and owner_info.get('reporting_manager_id') == current_user_id:
                lead_dict['can_change_owner'] = True
                lead_dict['owner_change_reason'] = 'reporting_manager'
            else:
                lead_dict['can_change_owner'] = False
                lead_dict['owner_change_reason'] = 'unauthorized'
        else:
            lead_dict['can_change_owner'] = False
            lead_dict['owner_change_reason'] = 'unauthorized'
        
        activity_dates = []
        if lead.updated_at:
            activity_dates.append(lead.updated_at)
        note_date = note_max_map.get(lead.id)
        if note_date:
            activity_dates.append(note_date)
        followup_date = followup_max_map.get(lead.id)
        if followup_date:
            activity_dates.append(followup_date)
        revenue_date = revenue_max_map.get(lead.id)
        if revenue_date:
            activity_dates.append(revenue_date)
        
        last_interacted_at = max(activity_dates) if activity_dates else lead.created_at
        lead_dict['last_interacted_at'] = last_interacted_at.isoformat() if last_interacted_at else None
        
        leads_data.append(lead_dict)
    
    # DC Protocol (Feb 2026): Build team members list for filter dropdown
    # For VGK Supreme/EA admin users, show ALL active staff members
    team_members_data = []
    if is_admin:
        # Admin users see ALL active staff for filtering
        staff_query = db.query(StaffEmployee).filter(StaffEmployee.status == 'active')
        if company_id:
            staff_query = staff_query.filter(StaffEmployee.base_company_id == company_id)
        all_staff = staff_query.order_by(StaffEmployee.first_name).all()
        for emp in all_staff:
            emp_name = emp.full_name or f"{emp.first_name or ''} {emp.last_name or ''}".strip() or emp.emp_code
            team_members_data.append({
                'id': emp.id,
                'emp_code': emp.emp_code,
                'full_name': emp_name,
                'staff_type': emp.staff_type
            })
    else:
        if downline_ids:
            downline_emps = db.query(StaffEmployee).filter(StaffEmployee.id.in_(downline_ids)).order_by(StaffEmployee.first_name).all()
            for emp in downline_emps:
                emp_name = emp.full_name or f"{emp.first_name or ''} {emp.last_name or ''}".strip() or emp.emp_code
                team_members_data.append({
                    'id': emp.id,
                    'emp_code': emp.emp_code,
                    'full_name': emp_name,
                    'staff_type': emp.staff_type
                })
    
    # DC Protocol (Feb 2026): Calculate stats for display
    # Build base query for stats (same filters but without pagination)
    stats_base = db.query(CRMLead)
    if company_id:
        stats_base = stats_base.filter(CRMLead.company_id == company_id)
    
    # DC Protocol (Feb 2026): When team_member_id is passed, use it for stats
    # Otherwise show all leads for admin, or downline for regular users
    if team_member_id:
        stats_ids = [team_member_id]
    else:
        stats_ids = downline_ids if downline_ids else [current_employee.id]
    
    # As Owner stats - leads where user is primary owner
    if is_admin and not team_member_id:
        # Admin sees all leads stats (no filter by member)
        as_owner_query = stats_base.filter(CRMLead.primary_owner_type == 'staff')
    else:
        # Filter by specific member(s)
        as_owner_query = stats_base.filter(
            CRMLead.primary_owner_type == 'staff',
            CRMLead.primary_owner_id.in_(stats_ids)
        )
    owner_total = as_owner_query.count()
    owner_new = as_owner_query.filter(CRMLead.status == 'new').count()
    owner_progress = as_owner_query.filter(CRMLead.status.in_(['contacted', 'interested', 'qualified', 'proposal'])).count()
    owner_won = as_owner_query.filter(CRMLead.status == 'won').count()
    owner_lost = as_owner_query.filter(CRMLead.status == 'lost').count()
    owner_hold = as_owner_query.filter(CRMLead.status == 'on_hold').count()
    
    # As Handler stats - leads where user is telecaller/field_staff
    if is_admin and not team_member_id:
        # Admin sees all handler stats
        handler_conditions = [
            CRMLead.telecaller_id.isnot(None),
            CRMLead.field_staff_id.isnot(None),
        ]
    else:
        handler_conditions = [
            CRMLead.telecaller_id.in_(stats_ids),
            CRMLead.field_staff_id.in_(stats_ids),
        ]
    as_handler_query = stats_base.filter(or_(*handler_conditions))
    handler_total = as_handler_query.count()
    handler_new = as_handler_query.filter(CRMLead.status == 'new').count()
    handler_progress = as_handler_query.filter(CRMLead.status.in_(['contacted', 'interested', 'qualified', 'proposal'])).count()
    handler_won = as_handler_query.filter(CRMLead.status == 'won').count()
    handler_lost = as_handler_query.filter(CRMLead.status == 'lost').count()
    handler_hold = as_handler_query.filter(CRMLead.status == 'on_hold').count()
    
    # Tab counts
    tab_counts = {
        'all': total,
        'telecaller': stats_base.filter(CRMLead.telecaller_id.isnot(None)).count() if (is_admin and not team_member_id) else stats_base.filter(CRMLead.telecaller_id.in_(stats_ids)).count(),
        'field_staff': stats_base.filter(CRMLead.field_staff_id.isnot(None)).count() if (is_admin and not team_member_id) else stats_base.filter(CRMLead.field_staff_id.in_(stats_ids)).count(),
        'mnr_handler': stats_base.filter(CRMLead.mnr_handler_id.isnot(None)).count() if (is_admin and not team_member_id) else (stats_base.filter(CRMLead.mnr_handler_id.in_(downline_emp_codes)).count() if downline_emp_codes else 0),
        'fresh': stats_base.filter(CRMLead.status == 'new', CRMLead.primary_owner_id.is_(None)).count(),
        'self': stats_base.filter(CRMLead.primary_owner_id == current_employee.id).count()
    }
    
    return {
        'success': True,
        'data': {
            'leads': leads_data,
            'team_size': len(downline_ids) if downline_ids else len(team_members_data),
            'team_members': team_members_data,
            'as_owner_stats': {
                'total': owner_total,
                'new': owner_new,
                'progress': owner_progress,
                'won': owner_won,
                'lost': owner_lost,
                'on_hold': owner_hold,
                'revenue': 0,
                'collected': 0,
                'balance': 0
            },
            'as_handler_stats': {
                'total': handler_total,
                'new': handler_new,
                'progress': handler_progress,
                'won': handler_won,
                'lost': handler_lost,
                'on_hold': handler_hold,
                'revenue': 0,
                'collected': 0,
                'balance': 0
            },
            'tab_counts': tab_counts,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total,
                'pages': (total + per_page - 1) // per_page
            }
        }
    }


@router.get("/master-leads")
def master_leads(
    category: Optional[str] = Query(None),
    category_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    subsidy_status: Optional[str] = Query(None),
    existing_association: Optional[str] = Query(None),
    handler_emp_code: Optional[str] = Query(None),
    source: Optional[str] = Query(None),
    telecaller_id: Optional[int] = Query(None),
    field_staff_id: Optional[int] = Query(None),
    telecaller_emp_code: Optional[str] = Query(None),
    field_staff_emp_code: Optional[str] = Query(None),
    field_support_ref_id: Optional[str] = Query(None),
    pincode: Optional[str] = Query(None),
    company_id_filter: Optional[int] = Query(None),
    next_followup_from: Optional[str] = Query(None),
    next_followup_to: Optional[str] = Query(None),
    accepted_date_from: Optional[str] = Query(None),
    accepted_date_to: Optional[str] = Query(None),
    installation_date_from: Optional[str] = Query(None),
    installation_date_to: Optional[str] = Query(None),
    material_reach_date_from: Optional[str] = Query(None),
    material_reach_date_to: Optional[str] = Query(None),
    created_from: Optional[str] = Query(None),
    created_to: Optional[str] = Query(None),
    solar_pipeline_status: Optional[str] = Query(None),
    ev_b2b_stage: Optional[str] = Query(None),
    combined_bank_filter: Optional[str] = Query(None, description="OR filter: 'with_bank'=pending_with_bank OR waiting_for_bank_loan; 'loan_rejected'=loan_rejected OR bank_loan_rejected"),
    submit_date_from: Optional[str] = Query(None),
    submit_date_to: Optional[str] = Query(None),
    complete_date_from: Optional[str] = Query(None),
    complete_date_to: Optional[str] = Query(None),
    first_dvr_from: Optional[str] = Query(None),
    first_dvr_to: Optional[str] = Query(None),
    vendor_id: Optional[int] = Query(None, description="Filter Solar leads by assigned vendor"),
    guru_name: Optional[str] = Query(None, description="Filter by Guru name (ILIKE)"),
    z_guru_name: Optional[str] = Query(None, description="Filter by Z-Guru name (ILIKE)"),
    core_name: Optional[str] = Query(None, description="Filter by Core partner name (ILIKE)"),
    sort_by: Optional[str] = Query('created_at'),
    sort_dir: Optional[str] = Query('desc'),
    page: int = 1,
    per_page: int = 20,
    db: Session = Depends(get_db),
    current_employee: StaffEmployee = Depends(get_current_staff_user)
):
    """DC Protocol (Mar 2026): Manager-level lead view — no ownership filtering.
    Admin sees ALL leads by category across all companies.
    Non-admin sees all leads for their own company.
    Returns flat {data: [...], pagination: {...}} format with handler enrichment.
    """
    import math as _math
    staff_type = (current_employee.staff_type or '').upper()
    is_admin = is_vgk_admin(staff_type)

    # DC Protocol (Mar 2026): Full-access tier — leadership roles see ALL leads
    # across all companies (same as VGK/EA admin), no assignment filtering.
    _FULL_ACCESS_ROLE_CODES = {
        'vgk4u', 'vgk4u_supreme',
        'key_leadership', 'leadership_role',
        'team_leader', 'manager',
    }
    _role_code = (current_employee.role.role_code if current_employee.role else '') or ''
    _is_leadership = _role_code in _FULL_ACCESS_ROLE_CODES
    # DC Protocol (Apr 2026): Fetch direct subordinate IDs for team-scoped access.
    # Reporting managers see their OWN leads + their DIRECT REPORTS' leads only.
    # Same-level peers cannot see each other's leads (including Won leads).
    # Only the lead's direct handlers and their reporting manager have visibility.
    _subordinate_ids = [
        row.id for row in db.query(StaffEmployee.id).filter(
            StaffEmployee.reporting_manager_id == current_employee.id,
            StaffEmployee.status == 'active'
        ).all()
    ]

    is_full_access = is_admin or _is_leadership

    query = db.query(CRMLead)

    # Company / access scoping
    if is_full_access:
        # VGK/EA admins and explicit leadership-role staff see ALL leads.
        if is_admin and company_id_filter:
            query = query.filter(CRMLead.company_id == company_id_filter)
    else:
        # DC Protocol (Apr 2026): All other staff — including reporting managers —
        # see ONLY leads where they or one of their direct reports is the handler.
        # This ensures Won (and all other) leads from a peer are never visible
        # to same-level colleagues, even if those colleagues are reporting managers.
        _allowed_ids = [current_employee.id] + _subordinate_ids
        query = query.filter(or_(
            CRMLead.telecaller_id.in_(_allowed_ids),
            CRMLead.field_staff_id.in_(_allowed_ids),
            and_(
                CRMLead.primary_owner_type == 'staff',
                CRMLead.primary_owner_id.in_(_allowed_ids)
            )
        ))

    # DC Protocol (Jul 2026 Task 11): Category filter — dual-match logic for both string name and integer ID.
    if category or category_id is not None:
        _cat_ids = []
        if category_id is not None:
            _cat_ids.append(category_id)
        if category:
            if isinstance(category, int) or (isinstance(category, str) and category.isdigit()):
                _cat_ids.append(int(category))
            else:
                _matched_cats = db.query(SignupCategory.id).filter(
                    or_(
                        SignupCategory.name.ilike(category),
                        SignupCategory.name.ilike(f"%{category}%"),
                        SignupCategory.slug.ilike(category)
                    )
                ).all()
                _cat_ids.extend([r.id for r in _matched_cats])

        _cat_ids = list(set(_cat_ids))
        if _cat_ids:
            _deal_lead_sq = (
                db.query(CRMLeadDeal.lead_id)
                .filter(CRMLeadDeal.revenue_category_id.in_(_cat_ids))
                .scalar_subquery()
            )
            query = query.filter(or_(
                CRMLead.category_id.in_(_cat_ids),
                CRMLead.id.in_(_deal_lead_sq)
            ))
        else:
            query = query.filter(CRMLead.id == -1)

    # Status
    POST_WON_STATUSES = ['won', 'order_placed', 'dispatched', 'delivered', 'installed', 'completed']
    if status:
        if status == 'closed':
            query = query.filter(CRMLead.status.in_(['won', 'lost']))
        elif status == 'in_progress':
            query = query.filter(CRMLead.status.in_(['contacted', 'interested', 'qualified', 'proposal']))
        elif status == 'won_plus':
            query = query.filter(CRMLead.status.in_(POST_WON_STATUSES))
        else:
            query = query.filter(CRMLead.status == status)

    if priority:
        query = query.filter(CRMLead.priority == priority)

    if subsidy_status:
        query = query.filter(CRMLead.subsidy_status == subsidy_status)

    if existing_association:
        query = query.filter(CRMLead.existing_association == existing_association)

    if solar_pipeline_status:
        query = query.filter(CRMLead.solar_pipeline_status == solar_pipeline_status)
    _CBF_MAP = {
        'with_bank':     ('pending_with_bank',  'waiting_for_bank_loan'),
        'loan_rejected': ('loan_rejected',       'bank_loan_rejected'),
    }
    if combined_bank_filter and combined_bank_filter in _CBF_MAP:
        _cbf_ps, _cbf_st = _CBF_MAP[combined_bank_filter]
        query = query.filter(or_(
            CRMLead.solar_pipeline_status == _cbf_ps,
            CRMLead.status == _cbf_st
        ))
    if ev_b2b_stage is not None and ev_b2b_stage != '':
        query = query.filter(CRMLead.ev_b2b_stage == ev_b2b_stage)
    if submit_date_from:
        try:
            from datetime import date as _dt_date
            _sd_from = _dt_date.fromisoformat(submit_date_from[:10])
            query = query.filter(CRMLead.submit_date >= _sd_from)
        except Exception: pass
    if submit_date_to:
        try:
            from datetime import date as _dt_date
            _sd_to = _dt_date.fromisoformat(submit_date_to[:10])
            query = query.filter(CRMLead.submit_date <= _sd_to)
        except Exception: pass
    if complete_date_from:
        try:
            from datetime import date as _dt_date
            _cd_from = _dt_date.fromisoformat(complete_date_from[:10])
            query = query.filter(CRMLead.complete_date >= _cd_from)
        except Exception: pass
    if complete_date_to:
        try:
            from datetime import date as _dt_date
            _cd_to = _dt_date.fromisoformat(complete_date_to[:10])
            query = query.filter(CRMLead.complete_date <= _cd_to)
        except Exception: pass
    if first_dvr_from:
        try:
            from datetime import date as _dt_date, timedelta as _td
            _dvrfrom = _dt_date.fromisoformat(first_dvr_from[:10])
            query = query.filter(CRMLead.first_payment_received_date >= _dvrfrom)
        except Exception: pass
    if first_dvr_to:
        try:
            from datetime import date as _dt_date, timedelta as _td
            _dvrto = _dt_date.fromisoformat(first_dvr_to[:10])
            query = query.filter(CRMLead.first_payment_received_date < _dvrto + _td(days=1))
        except Exception: pass
    if vendor_id:
        query = query.filter(CRMLead.vendor_id == vendor_id)

    if source:
        query = query.filter(CRMLead.source.ilike(f'%{source}%'))

    if handler_emp_code:
        _hec = f'%{handler_emp_code}%'
        # Also resolve User IDs by name so that leads whose mnr_handler_id is a
        # numeric User.id (with no source_ref_name stored) are still matched when
        # the caller searches by the person's name (e.g. "devada").
        _mnr_user_ids = [
            str(u.id)
            for u in db.query(User.id).filter(User.name.ilike(_hec)).all()
        ]
        _hec_conditions = [
            CRMLead.mnr_handler_id.ilike(_hec),
            CRMLead.source_ref_id.ilike(_hec),
            CRMLead.source_ref_name.ilike(_hec),
        ]
        if _mnr_user_ids:
            _hec_conditions.append(CRMLead.mnr_handler_id.in_(_mnr_user_ids))
        query = query.filter(or_(*_hec_conditions))

    if telecaller_id:
        query = query.filter(CRMLead.telecaller_id == telecaller_id)

    if field_staff_id:
        query = query.filter(CRMLead.field_staff_id == field_staff_id)

    if telecaller_emp_code:
        _tc_emp = db.query(StaffEmployee).filter(
            StaffEmployee.emp_code.ilike(f'%{telecaller_emp_code}%'),
            StaffEmployee.status == 'active'
        ).first()
        if _tc_emp:
            query = query.filter(CRMLead.telecaller_id == _tc_emp.id)
        else:
            query = query.filter(CRMLead.id == -1)

    if field_staff_emp_code:
        _fs_emp = db.query(StaffEmployee).filter(
            StaffEmployee.emp_code.ilike(f'%{field_staff_emp_code}%'),
            StaffEmployee.status == 'active'
        ).first()
        if _fs_emp:
            query = query.filter(CRMLead.field_staff_id == _fs_emp.id)
        else:
            query = query.filter(CRMLead.id == -1)

    if field_support_ref_id:
        _fsr = f'%{field_support_ref_id}%'
        query = query.filter(or_(
            CRMLead.field_support_ref_id.ilike(_fsr),
            CRMLead.adi_guru_id.ilike(_fsr),
        ))

    if pincode:
        query = query.filter(CRMLead.pincode.ilike(f'%{pincode}%'))

    if guru_name:
        query = query.filter(CRMLead.guru_name.ilike(f'%{guru_name}%'))

    if z_guru_name:
        query = query.filter(CRMLead.z_guru_name.ilike(f'%{z_guru_name}%'))

    if core_name:
        _core_pids = [row[0] for row in db.query(OfficialPartner.id).filter(
            OfficialPartner.partner_name.ilike(f'%{core_name}%')
        ).all()]
        if _core_pids:
            query = query.filter(CRMLead.team_core_partner_id.in_(_core_pids))
        else:
            query = query.filter(CRMLead.id == -1)

    if search:
        st = f'%{search}%'
        _search_clauses = [
            CRMLead.name.ilike(st),
            CRMLead.phone.ilike(st),
            CRMLead.alternate_phone.ilike(st),
            CRMLead.co_applicant_phone.ilike(st),
            CRMLead.email.ilike(st),
            CRMLead.application_no.ilike(st),
            CRMLead.pincode.ilike(st),
            CRMLead.source.ilike(st),
            CRMLead.mnr_handler_id.ilike(st),
            CRMLead.source_ref_name.ilike(st),
            CRMLead.source_ref_id.ilike(st),
        ]
        # Allow searching by numeric lead ID (e.g. "142" or "#142")
        _id_str = search.lstrip('#').strip()
        if _id_str.isdigit():
            _search_clauses.append(CRMLead.id == int(_id_str))
        _mnr_uid_s = [str(u.id) for u in db.query(User.id).filter(User.name.ilike(st)).all()]
        if _mnr_uid_s:
            _search_clauses.append(CRMLead.mnr_handler_id.in_(_mnr_uid_s))
        query = query.filter(or_(*_search_clauses))

    def _parse_dt(s):
        try:
            return datetime.fromisoformat(s.replace('Z', '+00:00').replace('T00:00:00+00:00', ''))
        except Exception:
            return None

    def _parse_d(s):
        try:
            from datetime import date
            return date.fromisoformat(s[:10])
        except Exception:
            return None

    if next_followup_from:
        v = _parse_dt(next_followup_from); query = query.filter(CRMLead.next_followup_date >= v) if v else query
    if next_followup_to:
        v = _parse_dt(next_followup_to); query = query.filter(CRMLead.next_followup_date <= v) if v else query
    if accepted_date_from:
        v = _parse_d(accepted_date_from); query = query.filter(CRMLead.accepted_date >= v) if v else query
    if accepted_date_to:
        v = _parse_d(accepted_date_to); query = query.filter(CRMLead.accepted_date <= v) if v else query
    if installation_date_from:
        v = _parse_d(installation_date_from); query = query.filter(CRMLead.installation_date >= v) if v else query
    if installation_date_to:
        v = _parse_d(installation_date_to); query = query.filter(CRMLead.installation_date <= v) if v else query
    if material_reach_date_from:
        v = _parse_d(material_reach_date_from); query = query.filter(CRMLead.material_reach_date >= v) if v else query
    if material_reach_date_to:
        v = _parse_d(material_reach_date_to); query = query.filter(CRMLead.material_reach_date <= v) if v else query
    if created_from:
        v = _parse_dt(created_from); query = query.filter(CRMLead.created_at >= v) if v else query
    if created_to:
        v = _parse_dt(created_to); query = query.filter(CRMLead.created_at <= v) if v else query

    total = query.count()

    # Sorting
    _SORT_COLS = {
        'id': CRMLead.id, 'created_at': CRMLead.created_at, 'updated_at': CRMLead.updated_at,
        'name': CRMLead.name, 'phone': CRMLead.phone, 'status': CRMLead.status,
        'priority': CRMLead.priority, 'source': CRMLead.source,
        'subsidy_status': CRMLead.subsidy_status, 'application_no': CRMLead.application_no,
        'pincode': CRMLead.pincode, 'loan_bank': CRMLead.loan_bank,
        'existing_association': CRMLead.existing_association,
        'telecaller_id': CRMLead.telecaller_id, 'field_staff_id': CRMLead.field_staff_id,
        'mnr_handler_id': CRMLead.mnr_handler_id,
        'next_followup_date': CRMLead.next_followup_date, 'accepted_date': CRMLead.accepted_date,
        'installation_date': CRMLead.installation_date, 'deal_value_total': CRMLead.deal_value_total,
        'material_reach_date': CRMLead.material_reach_date,
        'solar_pipeline_status_updated_at': CRMLead.solar_pipeline_status_updated_at,
    }
    _col = _SORT_COLS.get(sort_by or 'created_at', CRMLead.created_at)
    _ord = _col.asc() if (sort_dir or 'desc').lower() == 'asc' else _col.desc()
    leads = query.order_by(_ord).offset((page - 1) * per_page).limit(per_page).all()

    # ── Batch enrichment ────────────────────────────────────────────────────
    from app.models.staff_accounts import AssociatedCompany, VendorMaster

    cat_ids = set(l.category_id for l in leads if l.category_id)
    co_ids  = set(l.company_id  for l in leads if l.company_id)
    ow_ids  = set(l.primary_owner_id for l in leads if l.primary_owner_type == 'staff' and l.primary_owner_id)
    tc_ids  = set(l.telecaller_id for l in leads if l.telecaller_id)
    fs_ids  = set(l.field_staff_id for l in leads if l.field_staff_id)
    # DC-SUPPORT-TECH1-STAFF-001: include new staff roles so names are resolved
    tech_ids = set(l.technical_id for l in leads if getattr(l, 'technical_id', None))
    ss_ids   = set(l.support_staff_id for l in leads if getattr(l, 'support_staff_id', None))
    ts1_ids  = set(l.technical_staff1_id for l in leads if getattr(l, 'technical_staff1_id', None))
    all_staff_ids = ow_ids | tc_ids | fs_ids | tech_ids | ss_ids | ts1_ids
    vend_ids    = set(l.vendor_id            for l in leads if l.vendor_id)
    op_ids      = set(l.associated_partner_id for l in leads if l.associated_partner_id)
    # DC-SHOWROOM-NAME-001 (Jun 2026): also include showroom_vgk_id for name resolution
    op_ids     |= set(l.showroom_vgk_id for l in leads if getattr(l, 'showroom_vgk_id', None))
    # DC-TEAM-ASSIGN-001: include team upline partner IDs for name enrichment
    op_ids     |= set(l.team_senior_partner_id   for l in leads if getattr(l, 'team_senior_partner_id',   None))
    op_ids     |= set(l.team_extended_partner_id for l in leads if getattr(l, 'team_extended_partner_id', None))
    op_ids     |= set(l.team_core_partner_id     for l in leads if getattr(l, 'team_core_partner_id',     None))

    cat_map = {c.id: c.name for c in db.query(SignupCategory).filter(SignupCategory.id.in_(cat_ids)).all()} if cat_ids else {}
    co_map  = {c.id: c.company_name for c in db.query(AssociatedCompany).filter(AssociatedCompany.id.in_(co_ids)).all()} if co_ids else {}
    staff_map = {}
    if all_staff_ids:
        for o in db.query(StaffEmployee).filter(StaffEmployee.id.in_(all_staff_ids)).all():
            n = o.full_name or f"{o.first_name or ''} {o.last_name or ''}".strip() or o.emp_code
            staff_map[o.id] = {'name': n, 'emp_code': o.emp_code}
    vend_map = {}
    if vend_ids:
        for v in db.query(VendorMaster).filter(VendorMaster.id.in_(vend_ids)).all():
            n = getattr(v, 'vendor_name', None) or getattr(v, 'business_name', None) or getattr(v, 'name', None) or str(v.id)
            vend_map[v.id] = {'name': n, 'code': getattr(v, 'vendor_code', None) or ''}
    # [DC-PARTNER-NAME] Batch-fetch OfficialPartner names for associated_partner_id enrichment
    op_name_map = {}
    if op_ids:
        try:
            for _op in db.query(OfficialPartner).filter(OfficialPartner.id.in_(op_ids)).all():
                op_name_map[_op.id] = (
                    getattr(_op, 'partner_name', None)
                    or getattr(_op, 'contact_person', None)
                    or getattr(_op, 'partner_code', None)
                    or str(_op.id)
                )
        except Exception as _ope:
            print(f"[DC-PARTNER-NAME] Warning: {_ope}", flush=True)

    # MNR/User handler name enrichment — batch-fetch names for mnr_handler_id, field_support_ref_id, adi_guru_id, guru_id, z_guru_id
    _mnr_lookup = set()
    for _l in leads:
        if _l.mnr_handler_id and not _l.source_ref_name:
            _mnr_lookup.add(_l.mnr_handler_id)
        if _l.field_support_ref_id and not _l.field_support_ref_name:
            _mnr_lookup.add(_l.field_support_ref_id)
        if _l.adi_guru_id:
            _mnr_lookup.add(_l.adi_guru_id)
        if _l.guru_id:
            _mnr_lookup.add(_l.guru_id)
        if getattr(_l, 'z_guru_id', None):
            _mnr_lookup.add(_l.z_guru_id)
        if getattr(_l, 'core_id', None):
            _mnr_lookup.add(_l.core_id)
    mnr_name_map = {}
    if _mnr_lookup:
        for _u in db.query(User).filter(User.id.in_(list(_mnr_lookup))).all():
            mnr_name_map[_u.id] = _u.name or _u.id

    # Transaction count per lead (batch)
    import math as _math2
    from sqlalchemy import func as _sqlf
    txn_count_map = {}
    solar_docs_count_map = {}
    if lead_ids_list := [l.id for l in leads]:
        for row in db.query(CRMLeadTransaction.lead_id, _sqlf.count(CRMLeadTransaction.id).label('cnt')).filter(
            CRMLeadTransaction.lead_id.in_(lead_ids_list)
        ).group_by(CRMLeadTransaction.lead_id).all():
            txn_count_map[row.lead_id] = row.cnt
        # Solar docs uploaded count per lead (batch)
        for row in db.execute(text(
            "SELECT lead_id, COUNT(*) AS cnt FROM crm_lead_solar_documents WHERE lead_id = ANY(:ids) GROUP BY lead_id"
        ), {"ids": lead_ids_list}).fetchall():
            solar_docs_count_map[row.lead_id] = row.cnt

    leads_data = []
    for lead in leads:
        d = lead.to_dict()
        d['category_name'] = cat_map.get(lead.category_id)
        d['company_name']  = co_map.get(lead.company_id)
        # Primary owner
        if lead.primary_owner_type == 'staff' and lead.primary_owner_id:
            oi = staff_map.get(lead.primary_owner_id)
            d['primary_owner_name']        = oi['name'] if oi else None
            d['primary_owner_employee_id'] = oi['emp_code'] if oi else None
        else:
            d['primary_owner_name'] = None
            d['primary_owner_employee_id'] = None
        # Telecaller (Support)
        if lead.telecaller_id:
            ti = staff_map.get(lead.telecaller_id)
            d['telecaller_name'] = ti['name'] if ti else None
            d['telecaller_emp_code'] = ti['emp_code'] if ti else None
        else:
            d['telecaller_name'] = None
            d['telecaller_emp_code'] = None
        # Field Staff (Showroom)
        if lead.field_staff_id:
            fi = staff_map.get(lead.field_staff_id)
            d['field_staff_name'] = fi['name'] if fi else None
            d['field_staff_emp_code'] = fi['emp_code'] if fi else None
        else:
            d['field_staff_name'] = None
            d['field_staff_emp_code'] = None
        # Associated Partner name — [DC-PARTNER-NAME] used by HC_CONFIG showroom fallback
        d['associated_partner_name'] = op_name_map.get(lead.associated_partner_id) if lead.associated_partner_id else None
        # DC-SHOWROOM-NAME-001 (Jun 2026): resolve showroom_vgk_id → name for chip display
        d['showroom_vgk_name'] = op_name_map.get(getattr(lead, 'showroom_vgk_id', None)) if getattr(lead, 'showroom_vgk_id', None) else None
        # Technical Staff 2
        if getattr(lead, 'technical_id', None):
            ti2 = staff_map.get(lead.technical_id)
            d['technical_name'] = ti2['name'] if ti2 else None
        else:
            d['technical_name'] = None
        # Support Staff
        if getattr(lead, 'support_staff_id', None):
            _ss = staff_map.get(lead.support_staff_id)
            d['support_staff_name'] = _ss['name'] if _ss else None
        else:
            d['support_staff_name'] = None
        # Technical Staff 1
        if getattr(lead, 'technical_staff1_id', None):
            _ts1 = staff_map.get(lead.technical_staff1_id)
            d['technical_staff1_name'] = _ts1['name'] if _ts1 else None
        else:
            d['technical_staff1_name'] = None
        # Vendor/Partner
        _vd = vend_map.get(lead.vendor_id) if lead.vendor_id else None
        d['partner_name'] = _vd['name'] if isinstance(_vd, dict) else _vd
        d['vendor_code'] = _vd['code'] if isinstance(_vd, dict) else None
        d['vendor_id'] = lead.vendor_id
        # Vendor status — computed from status + solar_pipeline_status (Apr 2026)
        _sps = (d.get('solar_pipeline_status') or '').lower()
        _st  = (d.get('status') or '').lower()
        _CANCELLED_SPS = {'loan_rejected', 'diff_vendor_loan_rejected', 'not_interested', 'cancelled'}
        _FINAL_SPS     = {'subsidy_cleared', 'bank_loan_completed'}
        _COMPLETED_SPS = {'installed', 'net_meter_pending', 'balance_received', 'completed'}
        if _st in ('lost', 'cancelled') or _sps in _CANCELLED_SPS:
            d['vendor_status'] = 'Cancelled'
        elif _sps in _FINAL_SPS:
            d['vendor_status'] = 'Final Invoice Completed'
        elif _sps in _COMPLETED_SPS:
            d['vendor_status'] = 'Completed'
        else:
            d['vendor_status'] = 'Pending'
        # Monthly income
        d['monthly_income'] = float(lead.monthly_income) if getattr(lead, 'monthly_income', None) is not None else None
        # Transaction count
        d['txn_count'] = txn_count_map.get(lead.id, 0)
        # Solar docs uploaded count
        d['solar_docs_uploaded'] = solar_docs_count_map.get(lead.id, 0)
        # MNR handler: populate source_ref_* from mnr_handler_id when not explicitly set
        if lead.mnr_handler_id and not d.get('source_ref_name'):
            d['source_ref_name'] = mnr_name_map.get(lead.mnr_handler_id, lead.mnr_handler_id)
            if not d.get('source_ref_type'):
                d['source_ref_type'] = 'mnr'
            if not d.get('source_ref_id'):
                d['source_ref_id'] = lead.mnr_handler_id
        # Field support: enrich name from User table when not stored
        if lead.field_support_ref_id and not d.get('field_support_ref_name'):
            _fs_resolved = mnr_name_map.get(lead.field_support_ref_id)
            if _fs_resolved:
                d['field_support_ref_name'] = _fs_resolved
        # adi_guru: always enrich name from User table
        if lead.adi_guru_id:
            d['adi_guru_name'] = mnr_name_map.get(lead.adi_guru_id) or d.get('adi_guru_name')
        # guru: enrich name from User table; fallback to stored text for partner-chain uplines
        if lead.guru_id:
            d['guru_name'] = mnr_name_map.get(lead.guru_id) or d.get('guru_name')
        elif not d.get('guru_name'):
            _sgn = getattr(lead, 'guru_name', None)
            if _sgn:
                d['guru_name'] = _sgn
        # z_guru: enrich name from User table; fallback to stored text for partner-chain uplines
        if getattr(lead, 'z_guru_id', None):
            d['z_guru_name'] = mnr_name_map.get(lead.z_guru_id) or d.get('z_guru_name')
        elif not d.get('z_guru_name'):
            _szgn = getattr(lead, 'z_guru_name', None)
            if _szgn:
                d['z_guru_name'] = _szgn
        # core: enrich name from User table; fallback to stored core_name
        if getattr(lead, 'core_id', None):
            d['core_name'] = mnr_name_map.get(lead.core_id) or d.get('core_name') or getattr(lead, 'core_name', None)
        elif not d.get('core_name'):
            _scn = getattr(lead, 'core_name', None)
            if _scn:
                d['core_name'] = _scn
        # DC-TEAM-ASSIGN-001: add team upline partner names for Solar table display
        d['team_senior_name']   = op_name_map.get(getattr(lead, 'team_senior_partner_id',   None))
        d['team_extended_name'] = op_name_map.get(getattr(lead, 'team_extended_partner_id', None))
        d['team_core_name']     = op_name_map.get(getattr(lead, 'team_core_partner_id',     None))
        leads_data.append(d)

    return {
        'success': True,
        'data': leads_data,
        'pagination': {
            'page': page,
            'per_page': per_page,
            'total': total,
            'pages': _math.ceil(total / per_page) if total > 0 else 0
        }
    }


@router.get("/lead-analytics")
def lead_analytics(
    category: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    source: Optional[str] = Query(None),
    net_source: Optional[str] = Query(None),
    guru_filter: Optional[str] = Query(None),
    z_guru_filter: Optional[str] = Query(None),
    telecaller_emp_code: Optional[str] = Query(None),
    field_staff_emp_code: Optional[str] = Query(None),
    pincode: Optional[str] = Query(None),
    created_from: Optional[str] = Query(None),
    created_to: Optional[str] = Query(None),
    closed_from: Optional[str] = Query(None),
    closed_to: Optional[str] = Query(None),
    accepted_date_from: Optional[str] = Query(None),
    accepted_date_to: Optional[str] = Query(None),
    installation_date_from: Optional[str] = Query(None),
    installation_date_to: Optional[str] = Query(None),
    material_reach_date_from: Optional[str] = Query(None),
    material_reach_date_to: Optional[str] = Query(None),
    next_followup_from: Optional[str] = Query(None),
    next_followup_to: Optional[str] = Query(None),
    solar_pipeline_status: Optional[str] = Query(None),
    ev_b2b_stage: Optional[str] = Query(None),
    combined_bank_filter: Optional[str] = Query(None, description="OR filter: 'with_bank' or 'loan_rejected'"),
    submit_date_from: Optional[str] = Query(None),
    submit_date_to: Optional[str] = Query(None),
    complete_date_from: Optional[str] = Query(None),
    complete_date_to: Optional[str] = Query(None),
    first_dvr_from: Optional[str] = Query(None),
    first_dvr_to: Optional[str] = Query(None),
    company_id_filter: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_employee: StaffEmployee = Depends(get_current_staff_user)
):
    """Executive analytics dashboard: summary KPIs, by-status, by-category,
    by-source, by-telecaller, by-field-staff breakdowns."""
    import math as _m
    from sqlalchemy import func as _f, case as _sa_case

    staff_type = (current_employee.staff_type or '').upper()
    is_admin = is_vgk_admin(staff_type)

    POST_WON = ['won', 'order_placed', 'dispatched', 'delivered', 'installed', 'completed']
    # DC Protocol (May 2026): Solar pipeline stages that disqualify a lead from Won counts/values.
    # A lead status='won' with one of these solar stages means the deal fell through post-win.
    _EXCL_WON_PS = ['loan_rejected', 'documents_issue', 'not_interested', 'cancelled', 'different_vendor']

    # DC-STAGE-COLS: Reusable per-stage COUNT expressions for the leaderboard.
    # Used by every handler-type query so the frontend can show pipeline-stage breakdown.
    def _stage_exprs():
        S = CRMLead.status
        return [
            _f.coalesce(_f.sum(_sa_case((S == 'new',        1), else_=0)), 0).label('s_new'),
            _f.coalesce(_f.sum(_sa_case((S == 'contacted',  1), else_=0)), 0).label('s_contacted'),
            _f.coalesce(_f.sum(_sa_case((S == 'interested', 1), else_=0)), 0).label('s_interested'),
            _f.coalesce(_f.sum(_sa_case((S == 'qualified',  1), else_=0)), 0).label('s_qualified'),
            _f.coalesce(_f.sum(_sa_case((S == 'proposal',   1), else_=0)), 0).label('s_proposal'),
            _f.coalesce(_f.sum(_sa_case((S == 'on_hold',    1), else_=0)), 0).label('s_on_hold'),
            _f.coalesce(_f.sum(_sa_case((_won_ok,            1), else_=0)), 0).label('s_won'),
            _f.coalesce(_f.sum(_sa_case((S == 'lost',       1), else_=0)), 0).label('s_lost'),
        ]

    def _stage_dv_exprs():
        S  = CRMLead.status
        DV = _eff_dv()
        return [
            _f.coalesce(_f.sum(_sa_case((S == 'new',        DV), else_=0)), 0).label('dv_s_new'),
            _f.coalesce(_f.sum(_sa_case((S == 'contacted',  DV), else_=0)), 0).label('dv_s_contacted'),
            _f.coalesce(_f.sum(_sa_case((S == 'interested', DV), else_=0)), 0).label('dv_s_interested'),
            _f.coalesce(_f.sum(_sa_case((S == 'qualified',  DV), else_=0)), 0).label('dv_s_qualified'),
            _f.coalesce(_f.sum(_sa_case((S == 'proposal',   DV), else_=0)), 0).label('dv_s_proposal'),
            _f.coalesce(_f.sum(_sa_case((S == 'on_hold',    DV), else_=0)), 0).label('dv_s_on_hold'),
            _f.coalesce(_f.sum(_sa_case((_won_ok,           DV), else_=0)), 0).label('dv_s_won'),
            _f.coalesce(_f.sum(_sa_case((S == 'lost',       DV), else_=0)), 0).label('dv_s_lost'),
        ]

    def _stage_dict(r):
        """Pull per-stage counts and deal values from a query row into a dict."""
        return {
            's_new':           int(getattr(r, 's_new',           0) or 0),
            's_contacted':     int(getattr(r, 's_contacted',     0) or 0),
            's_interested':    int(getattr(r, 's_interested',    0) or 0),
            's_qualified':     int(getattr(r, 's_qualified',     0) or 0),
            's_proposal':      int(getattr(r, 's_proposal',      0) or 0),
            's_on_hold':       int(getattr(r, 's_on_hold',       0) or 0),
            's_won':           int(getattr(r, 's_won',           0) or 0),
            's_lost':          int(getattr(r, 's_lost',          0) or 0),
            'dv_s_new':        float(getattr(r, 'dv_s_new',        0) or 0),
            'dv_s_contacted':  float(getattr(r, 'dv_s_contacted',  0) or 0),
            'dv_s_interested': float(getattr(r, 'dv_s_interested', 0) or 0),
            'dv_s_qualified':  float(getattr(r, 'dv_s_qualified',  0) or 0),
            'dv_s_proposal':   float(getattr(r, 'dv_s_proposal',   0) or 0),
            'dv_s_on_hold':    float(getattr(r, 'dv_s_on_hold',    0) or 0),
            'dv_s_won':        float(getattr(r, 'dv_s_won',        0) or 0),
            'dv_s_lost':       float(getattr(r, 'dv_s_lost',       0) or 0),
        }

    # DC-SOLAR-STAGE-COLS: Per solar_pipeline_status COUNT + DV for the Stagewise table.
    _SOLAR_PS_KEYS = [
        'completed', 'installation_pending', 'pending_with_bank', 'documents_pending',
        'application_submitted', 'loan_rejected', 'documents_issue', 'load_extension',
        'electricity_bill_change', 'net_meter_pending', 'balance_pending', 'balance_received', 'subsidy_pending',
        'not_interested', 'cancelled', 'different_vendor',
    ]
    def _sp_key(ps): return 'sp_at_bank' if ps == 'pending_with_bank' else ('sp_' + ps)

    def _solar_stage_exprs():
        PS = CRMLead.solar_pipeline_status
        return [_f.coalesce(_f.sum(_sa_case((PS == ps, 1), else_=0)), 0).label(_sp_key(ps)) for ps in _SOLAR_PS_KEYS]

    def _solar_stage_dv_exprs():
        PS = CRMLead.solar_pipeline_status
        DV = _eff_dv()
        return [_f.coalesce(_f.sum(_sa_case((PS == ps, DV), else_=0)), 0).label('dv_' + _sp_key(ps)) for ps in _SOLAR_PS_KEYS]

    def _solar_stage_dict(r):
        d = {}
        for ps in _SOLAR_PS_KEYS:
            k = _sp_key(ps)
            d[k] = int(getattr(r, k, 0) or 0)
            d['dv_' + k] = float(getattr(r, 'dv_' + k, 0) or 0)
        return d

    def _completed_exprs():
        from sqlalchemy import or_ as _ce_or, and_ as _ce_and, text as _ce_text
        _cc = _ce_or(
            CRMLead.solar_pipeline_status == 'completed',
            CRMLead.ev_b2b_stage == 'completed',
            _ce_and(CRMLead.status == 'completed',
                    CRMLead.solar_pipeline_status.is_(None),
                    CRMLead.ev_b2b_stage.is_(None)),
            _ce_text(
                "EXISTS (SELECT 1 FROM etc_students s "
                "WHERE s.crm_lead_id = crm_leads.id "
                "AND s.training_completed_date IS NOT NULL "
                "AND s.is_active = TRUE)"
            )
        )
        return [
            _f.coalesce(_f.sum(_sa_case((_cc, 1), else_=0)), 0).label('cnt_completed'),
            _f.coalesce(_f.sum(_sa_case((_cc, _eff_dv()), else_=0)), 0).label('dv_fdv'),
        ]

    def _completed_dict(r):
        return {
            'completed': int(getattr(r, 'cnt_completed', 0) or 0),
            'final_deal_value': float(getattr(r, 'dv_fdv', 0) or 0),
        }

    base = db.query(CRMLead)
    if company_id_filter:
        base = base.filter(CRMLead.company_id == company_id_filter)

    # DC Protocol (Apr 2026): Team-scoped visibility — mirrors master-leads rule.
    # Admins and named leadership roles see all leads.
    # All other staff (including reporting managers) see only leads assigned to
    # themselves or their direct reports. Same-level peers cannot see each other's
    # leads in the analytics counts (Won, Total, etc.).
    _an_role_code = (current_employee.role.role_code if current_employee.role else '') or ''
    _AN_FULL_ACCESS = {'vgk4u', 'vgk4u_supreme', 'key_leadership', 'leadership_role', 'team_leader', 'manager'}
    _an_is_leadership = _an_role_code in _AN_FULL_ACCESS
    if not is_admin and not _an_is_leadership:
        _an_sub_ids = [
            row.id for row in db.query(StaffEmployee.id).filter(
                StaffEmployee.reporting_manager_id == current_employee.id,
                StaffEmployee.status == 'active'
            ).all()
        ]
        _an_allowed = [current_employee.id] + _an_sub_ids
        base = base.filter(or_(
            CRMLead.telecaller_id.in_(_an_allowed),
            CRMLead.field_staff_id.in_(_an_allowed),
            and_(
                CRMLead.primary_owner_type == 'staff',
                CRMLead.primary_owner_id.in_(_an_allowed)
            )
        ))

    # DC Protocol (Apr 2026): Dual-match category filter — mirrors master-leads logic.
    if category:
        _an_cat_ids = [
            r.id for r in db.query(SignupCategory.id)
            .filter(SignupCategory.name == category).all()
        ]
        if _an_cat_ids:
            _an_deal_sq = (
                db.query(CRMLeadDeal.lead_id)
                .filter(CRMLeadDeal.revenue_category_id.in_(_an_cat_ids))
                .scalar_subquery()
            )
            base = base.filter(or_(
                CRMLead.category_id.in_(_an_cat_ids),
                CRMLead.id.in_(_an_deal_sq)
            ))
        else:
            base = base.filter(CRMLead.id == -1)

    if source:
        base = base.filter(CRMLead.source.ilike(f'%{source}%'))

    if telecaller_emp_code:
        _tc = db.query(StaffEmployee).filter(
            StaffEmployee.emp_code.ilike(f'%{telecaller_emp_code}%'),
            StaffEmployee.status == 'active'
        ).first()
        base = base.filter(CRMLead.telecaller_id == _tc.id) if _tc else base.filter(CRMLead.id == -1)

    if field_staff_emp_code:
        _fs = db.query(StaffEmployee).filter(
            StaffEmployee.emp_code.ilike(f'%{field_staff_emp_code}%'),
            StaffEmployee.status == 'active'
        ).first()
        base = base.filter(CRMLead.field_staff_id == _fs.id) if _fs else base.filter(CRMLead.id == -1)

    if pincode:
        base = base.filter(CRMLead.pincode.ilike(f'%{pincode}%'))

    def _pd(s):
        try:
            return datetime.fromisoformat(s.replace('Z', '+00:00').replace('T00:00:00+00:00', ''))
        except Exception:
            return None

    if created_from:
        v = _pd(created_from)
        if v:
            base = base.filter(CRMLead.created_at >= v)
    if created_to:
        v = _pd(created_to)
        if v:
            base = base.filter(CRMLead.created_at <= v)

    if net_source:
        from sqlalchemy import or_ as _or2
        base = base.filter(_or2(
            CRMLead.source_ref_name.ilike(f'%{net_source}%'),
            CRMLead.source_ref_id.ilike(f'%{net_source}%'),
            CRMLead.mnr_handler_id.ilike(f'%{net_source}%')
        ))

    if guru_filter:
        from sqlalchemy import or_ as _or_gf
        from app.models.user import User as _GFUser
        _gf_user = db.query(_GFUser).filter(
            _or_gf(
                _GFUser.id.ilike(f'%{guru_filter}%'),
                _GFUser.name.ilike(f'%{guru_filter}%') if hasattr(_GFUser, 'name') else False,
                _GFUser.full_name.ilike(f'%{guru_filter}%') if hasattr(_GFUser, 'full_name') else False,
            )
        ).first()
        if _gf_user:
            base = base.filter(CRMLead.guru_id == str(_gf_user.id))
        else:
            base = base.filter(CRMLead.guru_id.ilike(f'%{guru_filter}%'))

    if z_guru_filter:
        from sqlalchemy import or_ as _or_zgf
        from app.models.user import User as _ZGFUser
        _zgf_user = db.query(_ZGFUser).filter(
            _or_zgf(
                _ZGFUser.id.ilike(f'%{z_guru_filter}%'),
                _ZGFUser.name.ilike(f'%{z_guru_filter}%') if hasattr(_ZGFUser, 'name') else False,
                _ZGFUser.full_name.ilike(f'%{z_guru_filter}%') if hasattr(_ZGFUser, 'full_name') else False,
            )
        ).first()
        if _zgf_user:
            base = base.filter(CRMLead.z_guru_id == str(_zgf_user.id))
        else:
            base = base.filter(CRMLead.z_guru_id.ilike(f'%{z_guru_filter}%'))

    if closed_from:
        v = _pd(closed_from)
        if v:
            base = base.filter(CRMLead.actual_close_date >= v)
    if closed_to:
        v = _pd(closed_to)
        if v:
            base = base.filter(CRMLead.actual_close_date <= v)

    if status:
        if status == 'won_plus':
            base = base.filter(CRMLead.status.in_(POST_WON))
        else:
            base = base.filter(CRMLead.status == status)

    if search:
        from sqlalchemy import or_ as _or_
        base = base.filter(_or_(
            CRMLead.name.ilike(f'%{search}%'),
            CRMLead.phone.ilike(f'%{search}%')
        ))

    if accepted_date_from:
        v = _pd(accepted_date_from)
        if v: base = base.filter(CRMLead.accepted_date >= v)
    if accepted_date_to:
        v = _pd(accepted_date_to)
        if v: base = base.filter(CRMLead.accepted_date <= v)
    if installation_date_from:
        v = _pd(installation_date_from)
        if v: base = base.filter(CRMLead.installation_date >= v)
    if installation_date_to:
        v = _pd(installation_date_to)
        if v: base = base.filter(CRMLead.installation_date <= v)
    if material_reach_date_from:
        v = _pd(material_reach_date_from)
        if v: base = base.filter(CRMLead.material_reach_date >= v)
    if material_reach_date_to:
        v = _pd(material_reach_date_to)
        if v: base = base.filter(CRMLead.material_reach_date <= v)
    if next_followup_from:
        v = _pd(next_followup_from)
        if v: base = base.filter(CRMLead.next_followup_date >= v)
    if next_followup_to:
        v = _pd(next_followup_to)
        if v: base = base.filter(CRMLead.next_followup_date <= v)
    if solar_pipeline_status:
        base = base.filter(CRMLead.solar_pipeline_status == solar_pipeline_status)
    _CBF_MAP_AN = {
        'with_bank':     ('pending_with_bank',  'waiting_for_bank_loan'),
        'loan_rejected': ('loan_rejected',       'bank_loan_rejected'),
    }
    if combined_bank_filter and combined_bank_filter in _CBF_MAP_AN:
        _cbf_ps, _cbf_st = _CBF_MAP_AN[combined_bank_filter]
        base = base.filter(or_(
            CRMLead.solar_pipeline_status == _cbf_ps,
            CRMLead.status == _cbf_st
        ))
    if ev_b2b_stage:
        base = base.filter(CRMLead.ev_b2b_stage == ev_b2b_stage)
    if submit_date_from:
        _sdf = _pd(submit_date_from)
        if _sdf: base = base.filter(CRMLead.submit_date >= _sdf.date() if hasattr(_sdf, 'date') else _sdf)
    if submit_date_to:
        _sdt = _pd(submit_date_to)
        if _sdt: base = base.filter(CRMLead.submit_date <= _sdt.date() if hasattr(_sdt, 'date') else _sdt)
    if complete_date_from:
        _cdf = _pd(complete_date_from)
        if _cdf: base = base.filter(CRMLead.complete_date >= _cdf.date() if hasattr(_cdf, 'date') else _cdf)
    if complete_date_to:
        _cdt = _pd(complete_date_to)
        if _cdt: base = base.filter(CRMLead.complete_date <= _cdt.date() if hasattr(_cdt, 'date') else _cdt)
    if first_dvr_from:
        try:
            from datetime import date as _ddate, timedelta as _dtd
            _dvrf = _ddate.fromisoformat(first_dvr_from[:10])
            base = base.filter(CRMLead.first_payment_received_date >= _dvrf)
        except Exception: pass
    if first_dvr_to:
        try:
            from datetime import date as _ddate, timedelta as _dtd
            _dvrt = _ddate.fromisoformat(first_dvr_to[:10])
            base = base.filter(CRMLead.first_payment_received_date < _dvrt + _dtd(days=1))
        except Exception: pass

    # ── Summary (single query with CASE/SUM — replaces 6 separate queries) ────
    from sqlalchemy import and_ as _and_, or_ as _or_
    # Won condition: status in POST_WON AND solar pipeline stage not in disqualifying list
    _won_ok = _and_(
        CRMLead.status.in_(POST_WON),
        _or_(CRMLead.solar_pipeline_status.is_(None), ~CRMLead.solar_pipeline_status.in_(_EXCL_WON_PS))
    )
    IN_PROGRESS_STATUSES = ['new', 'contacted', 'interested', 'qualified', 'proposal', 'on_hold']
    # Stage-based active condition: exclude completed/cancelled/not_interested (solar),
    # completed (b2b), and lost/on_hold (all categories)
    _EXCL_SOLAR_PS = ['completed', 'cancelled', 'not_interested']
    _active_cond = _and_(
        ~CRMLead.status.in_(['lost', 'on_hold']),
        _or_(CRMLead.solar_pipeline_status.is_(None), ~CRMLead.solar_pipeline_status.in_(_EXCL_SOLAR_PS)),
        _or_(CRMLead.ev_b2b_stage.is_(None), CRMLead.ev_b2b_stage != 'completed')
    )
    from sqlalchemy import text as _ex_text
    _etc_done_sq = _ex_text(
        "EXISTS (SELECT 1 FROM etc_students s "
        "WHERE s.crm_lead_id = crm_leads.id "
        "AND s.training_completed_date IS NOT NULL "
        "AND s.is_active = TRUE)"
    )
    _completed_cond = _or_(
        CRMLead.solar_pipeline_status == 'completed',
        CRMLead.ev_b2b_stage == 'completed',
        _and_(CRMLead.status.in_(POST_WON), CRMLead.solar_pipeline_status.is_(None), CRMLead.ev_b2b_stage.is_(None)),
        _etc_done_sq
    )

    # DC-RECV-EXPRS-001: Received value expressions — deal_value_received for won and completed leads.
    # win_received  = SUM(deal_value_received) where lead is in POST_WON (synced from validated txns).
    # comp_received = SUM(deal_value_received) where lead is in completed state.
    def _received_exprs():
        return [
            _f.coalesce(_f.sum(_sa_case((_won_ok, CRMLead.deal_value_received), else_=0)), 0).label('win_received'),
            _f.coalesce(_f.sum(_sa_case((_completed_cond, CRMLead.deal_value_received), else_=0)), 0).label('comp_received'),
        ]

    def _received_dict(r):
        return {
            'win_received': float(getattr(r, 'win_received', 0) or 0),
            'completed_received': float(getattr(r, 'comp_received', 0) or 0),
        }

    _EXCL_PIPE_PS = ['cancelled', 'not_interested', 'completed', 'loan_rejected', 'different_vendor', 'documents_issue']
    _pipe_cond = _and_(_won_ok, _or_(CRMLead.solar_pipeline_status.is_(None), ~CRMLead.solar_pipeline_status.in_(_EXCL_PIPE_PS)))
    _sr = base.with_entities(
        _f.count(CRMLead.id).label('total'),
        _f.coalesce(_f.sum(_sa_case((_won_ok, 1), else_=0)), 0).label('won'),
        _f.coalesce(_f.sum(_sa_case((_pipe_cond, 1), else_=0)), 0).label('pipe_cnt'),
        _f.coalesce(_f.sum(_sa_case((CRMLead.status == 'lost', 1), else_=0)), 0).label('lost'),
        _f.coalesce(_f.sum(_sa_case((CRMLead.status.in_(IN_PROGRESS_STATUSES), 1), else_=0)), 0).label('in_prog'),
        _f.coalesce(_f.sum(_eff_dv()), 0).label('dv_all'),
        _f.coalesce(_f.sum(_sa_case((_won_ok, _eff_dv()), else_=0)), 0).label('dv_won'),
        _f.coalesce(_f.sum(_sa_case((_pipe_cond, _eff_dv()), else_=0)), 0).label('pipe_val'),
        _f.coalesce(_f.sum(CRMLead.deal_value_received), 0).label('dv_coll'),
        # DC Protocol (Apr 2026): Exclude loan_rejected from pending; track separately.
        # Null-safe: WHEN loan_rejected THEN 0 ELSE balance — NULL pipeline status goes to ELSE (included in pending)
        _f.coalesce(_f.sum(_sa_case((CRMLead.solar_pipeline_status == 'loan_rejected', 0), else_=CRMLead.deal_value_balance)), 0).label('dv_pend'),
        _f.coalesce(_f.sum(_sa_case((CRMLead.solar_pipeline_status == 'loan_rejected', CRMLead.deal_value_balance), else_=0)), 0).label('dv_loan_rejected'),
        # Stage-based financial aggregations (DC Protocol — stage-aware confirmed value)
        _f.coalesce(_f.sum(_sa_case((_active_cond, _eff_dv()), else_=0)), 0).label('dv_active'),
        _f.coalesce(_f.sum(_sa_case((_active_cond, CRMLead.deal_value_balance), else_=0)), 0).label('dv_pend_active'),
        _f.coalesce(_f.sum(_sa_case((_completed_cond, _eff_dv()), else_=0)), 0).label('dv_completed'),
        _f.coalesce(_f.sum(_sa_case((CRMLead.status == 'lost', _eff_dv()), else_=0)), 0).label('dv_lost_val'),
        _f.coalesce(_f.sum(_sa_case((CRMLead.solar_pipeline_status == 'not_interested', _eff_dv()), else_=0)), 0).label('dv_ni'),
        _f.coalesce(_f.sum(_sa_case((CRMLead.status == 'on_hold', _eff_dv()), else_=0)), 0).label('dv_hold'),
    ).one()
    total_leads     = int(_sr.total)
    won_leads       = int(_sr.won)
    pipeline_leads  = int(_sr.pipe_cnt)
    lost_leads      = int(_sr.lost)
    in_progress     = int(_sr.in_prog)
    _dv_all         = float(_sr.dv_all)
    _dv_won         = float(_sr.dv_won)
    _dv_pipe        = float(_sr.pipe_val)
    _avg_dv         = _dv_all / total_leads if total_leads > 0 else 0
    _dv_coll         = float(_sr.dv_coll)
    _dv_pend         = float(_sr.dv_pend)
    _dv_loan_rejected = float(_sr.dv_loan_rejected)
    _dv_active       = float(_sr.dv_active)
    _dv_pend_active = float(_sr.dv_pend_active)
    _dv_completed   = float(_sr.dv_completed)
    _dv_lost_val    = float(_sr.dv_lost_val)
    _dv_ni          = float(_sr.dv_ni)
    _dv_hold        = float(_sr.dv_hold)

    # ── By Status ─────────────────────────────────────────────────────────────
    status_rows = base.with_entities(
        CRMLead.status,
        _f.count(CRMLead.id).label('cnt'),
        _f.coalesce(_f.sum(_eff_dv()), 0).label('dv')
    ).group_by(CRMLead.status).order_by(_f.count(CRMLead.id).desc()).all()

    by_status = [{'status': r.status or 'unknown', 'count': r.cnt, 'deal_value': float(r.dv)} for r in status_rows]

    # ── By Category ───────────────────────────────────────────────────────────
    # DC Protocol: derive from `base` so ALL active filters (net_source, status,
    # telecaller, field_staff, search, closed dates, etc.) are respected.
    from app.models.signup_category import SignupCategory as _SC
    cat_rows = base.with_entities(
        CRMLead.category_id,
        _f.count(CRMLead.id).label('total'),
        _f.sum(_sa_case((_won_ok, 1), else_=0)).label('won'),
        _f.coalesce(_f.sum(_eff_dv()), 0).label('dv'),
        *_completed_exprs(), *_received_exprs(),
    ).group_by(CRMLead.category_id).all()
    _cat_ids = [r.category_id for r in cat_rows if r.category_id]
    _cat_map = {c.id: c.name for c in db.query(_SC).filter(_SC.id.in_(_cat_ids)).all()} if _cat_ids else {}
    # Merge rows with the same category name (multiple companies share the same segment names)
    _cat_merged = {}
    for r in cat_rows:
        _name = _cat_map.get(r.category_id) if r.category_id else None
        _key = _name or 'Unknown'
        if _key in _cat_merged:
            _cat_merged[_key]['total'] += r.total
            _cat_merged[_key]['won']   += int(r.won or 0)
            _cat_merged[_key]['deal_value'] += float(r.dv)
            _cat_merged[_key]['completed'] += int(getattr(r, 'cnt_completed', 0) or 0)
            _cat_merged[_key]['final_deal_value'] += float(getattr(r, 'dv_fdv', 0) or 0)
            _cat_merged[_key]['win_received'] += float(getattr(r, 'win_received', 0) or 0)
            _cat_merged[_key]['completed_received'] += float(getattr(r, 'comp_received', 0) or 0)
        else:
            _cat_merged[_key] = {
                'category': _key,
                'total': r.total,
                'won': int(r.won or 0),
                'deal_value': float(r.dv),
                'completed': int(getattr(r, 'cnt_completed', 0) or 0),
                'final_deal_value': float(getattr(r, 'dv_fdv', 0) or 0),
                'win_received': float(getattr(r, 'win_received', 0) or 0),
                'completed_received': float(getattr(r, 'comp_received', 0) or 0),
            }
    by_category = sorted(_cat_merged.values(), key=lambda x: x['total'], reverse=True)

    # ── By Telecaller (top 50) ────────────────────────────────────────────────
    tc_rows = base.filter(CRMLead.telecaller_id.isnot(None)).with_entities(
        CRMLead.telecaller_id,
        _f.count(CRMLead.id).label('cnt'),
        _f.coalesce(_f.sum(_sa_case((_won_ok, 1), else_=0)), 0).label('won'),
        _f.coalesce(_f.sum(_sa_case((CRMLead.status.in_(IN_PROGRESS_STATUSES), 1), else_=0)), 0).label('in_prog'),
        _f.coalesce(_f.sum(_sa_case((CRMLead.status == 'lost', 1), else_=0)), 0).label('lost'),
        _f.coalesce(_f.sum(_eff_dv()), 0).label('dv'),
        *_stage_exprs(), *_stage_dv_exprs(), *_solar_stage_exprs(), *_solar_stage_dv_exprs(),
        *_completed_exprs(), *_received_exprs(),
    ).group_by(CRMLead.telecaller_id).order_by(_f.count(CRMLead.id).desc()).limit(50).all()
    _tc_ids = [r.telecaller_id for r in tc_rows]
    _tc_staff = {}
    if _tc_ids:
        for emp in db.query(StaffEmployee).filter(StaffEmployee.id.in_(_tc_ids)).all():
            n = emp.full_name or f"{emp.first_name or ''} {emp.last_name or ''}".strip() or emp.emp_code
            _tc_staff[emp.id] = {'name': n, 'emp_code': emp.emp_code}
    by_telecaller = [
        {'emp_code': _tc_staff.get(r.telecaller_id, {}).get('emp_code', ''),
         'name': _tc_staff.get(r.telecaller_id, {}).get('name', f'Staff#{r.telecaller_id}'),
         'total': r.cnt, 'won': int(r.won), 'in_progress': int(r.in_prog), 'lost': int(r.lost),
         'deal_value': float(r.dv), **_stage_dict(r), **_solar_stage_dict(r), **_completed_dict(r), **_received_dict(r)}
        for r in tc_rows
    ]
    # DC-DASH-TOTAL-001: Append "(No Telecaller)" row so TOTAL row = header total
    _tc_assigned = sum(r['total'] for r in by_telecaller)
    if total_leads > _tc_assigned:
        _nt = base.filter(CRMLead.telecaller_id.is_(None)).with_entities(
            _f.count(CRMLead.id).label('cnt'),
            _f.coalesce(_f.sum(_sa_case((_won_ok, 1), else_=0)), 0).label('won'),
            _f.coalesce(_f.sum(_sa_case((CRMLead.status.in_(IN_PROGRESS_STATUSES), 1), else_=0)), 0).label('in_prog'),
            _f.coalesce(_f.sum(_sa_case((CRMLead.status == 'lost', 1), else_=0)), 0).label('lost'),
            _f.coalesce(_f.sum(_eff_dv()), 0).label('dv'),
            *_stage_exprs(), *_stage_dv_exprs(), *_solar_stage_exprs(), *_solar_stage_dv_exprs(),
            *_completed_exprs(), *_received_exprs(),
        ).one()
        by_telecaller.append({
            'emp_code': '', 'name': '(No Telecaller)',
            'total': int(_nt.cnt), 'won': int(_nt.won),
            'in_progress': int(_nt.in_prog), 'lost': int(_nt.lost),
            'deal_value': float(_nt.dv),
            **_stage_dict(_nt), **_solar_stage_dict(_nt), **_completed_dict(_nt), **_received_dict(_nt),
            '_unassigned': True,
        })

    # ── By Field Staff / Showroom (top 50) ────────────────────────────────────
    fs_rows = base.filter(CRMLead.field_staff_id.isnot(None)).with_entities(
        CRMLead.field_staff_id,
        _f.count(CRMLead.id).label('cnt'),
        _f.coalesce(_f.sum(_sa_case((_won_ok, 1), else_=0)), 0).label('won'),
        _f.coalesce(_f.sum(_sa_case((CRMLead.status.in_(IN_PROGRESS_STATUSES), 1), else_=0)), 0).label('in_prog'),
        _f.coalesce(_f.sum(_sa_case((CRMLead.status == 'lost', 1), else_=0)), 0).label('lost'),
        _f.coalesce(_f.sum(_eff_dv()), 0).label('dv'),
        *_stage_exprs(), *_stage_dv_exprs(), *_solar_stage_exprs(), *_solar_stage_dv_exprs(),
        *_completed_exprs(), *_received_exprs(),
    ).group_by(CRMLead.field_staff_id).order_by(_f.count(CRMLead.id).desc()).limit(50).all()
    _fs_ids = [r.field_staff_id for r in fs_rows]
    _fs_staff = {}
    if _fs_ids:
        for emp in db.query(StaffEmployee).filter(StaffEmployee.id.in_(_fs_ids)).all():
            n = emp.full_name or f"{emp.first_name or ''} {emp.last_name or ''}".strip() or emp.emp_code
            _fs_staff[emp.id] = {'name': n, 'emp_code': emp.emp_code}
    by_field_staff = [
        {'emp_code': _fs_staff.get(r.field_staff_id, {}).get('emp_code', ''),
         'name': _fs_staff.get(r.field_staff_id, {}).get('name', f'Staff#{r.field_staff_id}'),
         'total': r.cnt, 'won': int(r.won), 'in_progress': int(r.in_prog), 'lost': int(r.lost),
         'deal_value': float(r.dv), **_stage_dict(r), **_solar_stage_dict(r), **_completed_dict(r), **_received_dict(r)}
        for r in fs_rows
    ]

    # ── By Primary Handler / Assigned Staff (top 50) ─────────────────────────
    # handler_type='staff' leads grouped by handler_id (StaffEmployee.id).
    # This is the core missing view — shows performance by who actually owns each lead.
    handler_rows = base.filter(
        CRMLead.handler_type == 'staff',
        CRMLead.handler_id.isnot(None),
    ).with_entities(
        CRMLead.handler_id,
        _f.count(CRMLead.id).label('cnt'),
        _f.coalesce(_f.sum(_sa_case((_won_ok, 1), else_=0)), 0).label('won'),
        _f.coalesce(_f.sum(_sa_case((CRMLead.status.in_(IN_PROGRESS_STATUSES), 1), else_=0)), 0).label('in_prog'),
        _f.coalesce(_f.sum(_sa_case((CRMLead.status == 'lost', 1), else_=0)), 0).label('lost'),
        _f.coalesce(_f.sum(_eff_dv()), 0).label('dv'),
        *_stage_exprs(), *_stage_dv_exprs(), *_solar_stage_exprs(), *_solar_stage_dv_exprs(),
        *_completed_exprs(), *_received_exprs(),
    ).group_by(CRMLead.handler_id).order_by(_f.count(CRMLead.id).desc()).limit(50).all()
    _handler_ids = [r.handler_id for r in handler_rows if r.handler_id]
    _handler_staff = {}
    if _handler_ids:
        for emp in db.query(StaffEmployee).filter(StaffEmployee.emp_code.in_(_handler_ids)).all():
            n = emp.full_name or f"{emp.first_name or ''} {emp.last_name or ''}".strip() or emp.emp_code
            _handler_staff[emp.emp_code] = {'name': n, 'emp_code': emp.emp_code}
    by_handler = [
        {'emp_code': _handler_staff.get(r.handler_id, {}).get('emp_code', r.handler_id or ''),
         'name': _handler_staff.get(r.handler_id, {}).get('name', r.handler_id or f'Staff#{r.handler_id}'),
         'total': r.cnt, 'won': int(r.won), 'in_progress': int(r.in_prog), 'lost': int(r.lost),
         'deal_value': float(r.dv), **_stage_dict(r), **_solar_stage_dict(r), **_completed_dict(r), **_received_dict(r)}
        for r in handler_rows
    ]

    # ── Helper: resolve User names for a list of MNR IDs ─────────────────────
    def _resolve_user_names(id_list):
        name_map = {}
        if not id_list:
            return name_map
        try:
            from app.models.user import User as _UM
            for u in db.query(_UM).filter(_UM.id.in_(id_list)).all():
                name_map[u.id] = getattr(u, 'name', None) or u.id
        except Exception:
            pass
        return name_map

    # ── By Guru (guru_id — L1 upline of ground source, top 50) ───────────────
    guru_rows = base.filter(CRMLead.guru_id.isnot(None)).with_entities(
        CRMLead.guru_id,
        _f.count(CRMLead.id).label('cnt'),
        _f.coalesce(_f.sum(_sa_case((_won_ok, 1), else_=0)), 0).label('won'),
        _f.coalesce(_f.sum(_sa_case((CRMLead.status.in_(IN_PROGRESS_STATUSES), 1), else_=0)), 0).label('in_prog'),
        _f.coalesce(_f.sum(_sa_case((CRMLead.status == 'lost', 1), else_=0)), 0).label('lost'),
        _f.coalesce(_f.sum(_eff_dv()), 0).label('dv'),
        *_stage_exprs(), *_stage_dv_exprs(), *_solar_stage_exprs(), *_solar_stage_dv_exprs(),
        *_completed_exprs(), *_received_exprs(),
    ).group_by(CRMLead.guru_id).order_by(_f.count(CRMLead.id).desc()).limit(50).all()
    _guru_names = _resolve_user_names([r.guru_id for r in guru_rows if r.guru_id])
    by_guru = [
        {'mnr_id': r.guru_id,
         'name': _guru_names.get(r.guru_id) or r.guru_id or '—',
         'total': r.cnt, 'won': int(r.won), 'in_progress': int(r.in_prog), 'lost': int(r.lost),
         'deal_value': float(r.dv), **_stage_dict(r), **_solar_stage_dict(r), **_completed_dict(r), **_received_dict(r)}
        for r in guru_rows
    ]

    # ── By Z Guru (z_guru_id — L2 upline, top 50) ────────────────────────────
    zguru_rows = base.filter(CRMLead.z_guru_id.isnot(None)).with_entities(
        CRMLead.z_guru_id,
        _f.count(CRMLead.id).label('cnt'),
        _f.coalesce(_f.sum(_sa_case((_won_ok, 1), else_=0)), 0).label('won'),
        _f.coalesce(_f.sum(_sa_case((CRMLead.status.in_(IN_PROGRESS_STATUSES), 1), else_=0)), 0).label('in_prog'),
        _f.coalesce(_f.sum(_sa_case((CRMLead.status == 'lost', 1), else_=0)), 0).label('lost'),
        _f.coalesce(_f.sum(_eff_dv()), 0).label('dv'),
        *_stage_exprs(), *_stage_dv_exprs(), *_solar_stage_exprs(), *_solar_stage_dv_exprs(),
        *_completed_exprs(), *_received_exprs(),
    ).group_by(CRMLead.z_guru_id).order_by(_f.count(CRMLead.id).desc()).limit(50).all()
    _zguru_names = _resolve_user_names([r.z_guru_id for r in zguru_rows if r.z_guru_id])
    by_z_guru = [
        {'mnr_id': r.z_guru_id,
         'name': _zguru_names.get(r.z_guru_id) or r.z_guru_id or '—',
         'total': r.cnt, 'won': int(r.won), 'in_progress': int(r.in_prog), 'lost': int(r.lost),
         'deal_value': float(r.dv), **_stage_dict(r), **_solar_stage_dict(r), **_completed_dict(r), **_received_dict(r)}
        for r in zguru_rows
    ]

    # ── By On Ground Support (adi_guru_id, top 50) ───────────────────────────
    adguru_rows = base.filter(CRMLead.adi_guru_id.isnot(None)).with_entities(
        CRMLead.adi_guru_id,
        _f.count(CRMLead.id).label('cnt'),
        _f.coalesce(_f.sum(_sa_case((_won_ok, 1), else_=0)), 0).label('won'),
        _f.coalesce(_f.sum(_sa_case((CRMLead.status.in_(IN_PROGRESS_STATUSES), 1), else_=0)), 0).label('in_prog'),
        _f.coalesce(_f.sum(_sa_case((CRMLead.status == 'lost', 1), else_=0)), 0).label('lost'),
        _f.coalesce(_f.sum(_eff_dv()), 0).label('dv'),
        *_stage_exprs(), *_stage_dv_exprs(), *_solar_stage_exprs(), *_solar_stage_dv_exprs(),
        *_completed_exprs(), *_received_exprs(),
    ).group_by(CRMLead.adi_guru_id).order_by(_f.count(CRMLead.id).desc()).limit(50).all()
    _adguru_names = _resolve_user_names([r.adi_guru_id for r in adguru_rows if r.adi_guru_id])
    by_adi_guru = [
        {'mnr_id': r.adi_guru_id,
         'name': _adguru_names.get(r.adi_guru_id) or r.adi_guru_id or '—',
         'total': r.cnt, 'won': int(r.won), 'in_progress': int(r.in_prog), 'lost': int(r.lost),
         'deal_value': float(r.dv), **_stage_dict(r), **_solar_stage_dict(r), **_completed_dict(r), **_received_dict(r)}
        for r in adguru_rows
    ]

    # ── By Business Partner (associated_partner_id, top 50) ──────────────────
    from app.models.staff_accounts import OfficialPartner as _OP
    partner_rows = base.filter(CRMLead.associated_partner_id.isnot(None)).with_entities(
        CRMLead.associated_partner_id,
        _f.count(CRMLead.id).label('cnt'),
        _f.coalesce(_f.sum(_sa_case((_won_ok, 1), else_=0)), 0).label('won'),
        _f.coalesce(_f.sum(_sa_case((CRMLead.status.in_(IN_PROGRESS_STATUSES), 1), else_=0)), 0).label('in_prog'),
        _f.coalesce(_f.sum(_sa_case((CRMLead.status == 'lost', 1), else_=0)), 0).label('lost'),
        _f.coalesce(_f.sum(_eff_dv()), 0).label('dv'),
        *_stage_exprs(), *_stage_dv_exprs(), *_solar_stage_exprs(), *_solar_stage_dv_exprs(),
        *_completed_exprs(), *_received_exprs(),
    ).group_by(CRMLead.associated_partner_id).order_by(_f.count(CRMLead.id).desc()).limit(50).all()
    _partner_ids = [r.associated_partner_id for r in partner_rows if r.associated_partner_id]
    _partner_map = {}
    if _partner_ids:
        for p in db.query(_OP).filter(_OP.id.in_(_partner_ids)).all():
            _partner_map[p.id] = {'name': p.partner_name or p.contact_person or p.partner_code, 'code': p.partner_code or ''}
    by_partner = [
        {'code': _partner_map.get(r.associated_partner_id, {}).get('code', ''),
         'name': _partner_map.get(r.associated_partner_id, {}).get('name', f'Partner#{r.associated_partner_id}'),
         'total': r.cnt, 'won': int(r.won), 'in_progress': int(r.in_prog), 'lost': int(r.lost),
         'deal_value': float(r.dv), **_stage_dict(r), **_solar_stage_dict(r), **_completed_dict(r), **_received_dict(r)}
        for r in partner_rows
    ]

    # ── By Ground Source / MNR-VGK-Partner (top 50) ─────────────────────────
    # DC-DEDUP-FIX (Apr 2026): GROUP BY previously included gs_name, which caused one
    # member to appear as multiple rows when some leads had source_ref_name stored and
    # others had it null (falling back to the MNR code). Removed gs_name from GROUP BY —
    # names are resolved post-query via _gs_name_map lookup, so they don't need to be keys.
    gs_rows = base.filter(
        or_(CRMLead.source_ref_id.isnot(None), CRMLead.mnr_handler_id.isnot(None))
    ).with_entities(
        _f.coalesce(CRMLead.source_ref_id, CRMLead.mnr_handler_id).label('gs_id'),
        _f.coalesce(CRMLead.source_ref_type, 'mnr').label('gs_type'),
        _f.count(CRMLead.id).label('cnt'),
        _f.coalesce(_f.sum(_sa_case((_won_ok, 1), else_=0)), 0).label('won'),
        _f.coalesce(_f.sum(_sa_case((CRMLead.status.in_(IN_PROGRESS_STATUSES), 1), else_=0)), 0).label('in_prog'),
        _f.coalesce(_f.sum(_sa_case((CRMLead.status == 'lost', 1), else_=0)), 0).label('lost'),
        _f.coalesce(_f.sum(_eff_dv()), 0).label('dv'),
        *_stage_exprs(), *_stage_dv_exprs(), *_solar_stage_exprs(), *_solar_stage_dv_exprs(),
        *_completed_exprs(), *_received_exprs(),
    ).group_by(
        _f.coalesce(CRMLead.source_ref_id, CRMLead.mnr_handler_id),
        _f.coalesce(CRMLead.source_ref_type, 'mnr'),
    ).order_by(_f.count(CRMLead.id).desc()).limit(50).all()
    # DC Protocol (Mar 25, 2026): Resolve member names for all rows.
    # Source type determines which table to resolve from:
    #   mnr/vgk/null → User.id (MNR string)
    #   partner       → OfficialPartner.id (numeric)
    #   staff         → StaffEmployee.emp_code
    _gs_name_map = {}
    try:
        _PARTNER_TYPES = {'partner', 'vgk_partner', 'vgk'}
        _STAFF_TYPES   = {'staff'}
        _mnr_ids   = [r.gs_id for r in gs_rows if r.gs_id and (r.gs_type or 'mnr') not in _PARTNER_TYPES | _STAFF_TYPES]
        _part_ids  = []
        for _gr in gs_rows:
            if _gr.gs_id and (_gr.gs_type or '') in _PARTNER_TYPES:
                try: _part_ids.append(int(_gr.gs_id))
                except (ValueError, TypeError): pass
        _staff_codes = [r.gs_id for r in gs_rows if r.gs_id and (r.gs_type or '') in _STAFF_TYPES]

        if _mnr_ids:
            from app.models.user import User as _GSUserModel
            for _u in db.query(_GSUserModel).filter(_GSUserModel.id.in_(_mnr_ids)).all():
                _gs_name_map[_u.id] = getattr(_u, 'name', None) or _u.id

        if _part_ids:
            from app.models.staff_accounts import OfficialPartner as _GSOP
            for _p in db.query(_GSOP).filter(_GSOP.id.in_(_part_ids)).all():
                _gs_name_map[str(_p.id)] = _p.partner_name or _p.contact_person or _p.partner_code or f'Partner#{_p.id}'

        if _staff_codes:
            for _se in db.query(StaffEmployee).filter(StaffEmployee.emp_code.in_(_staff_codes)).all():
                _n = _se.full_name or f"{_se.first_name or ''} {_se.last_name or ''}".strip() or _se.emp_code
                _gs_name_map[_se.emp_code] = _n
    except Exception:
        pass
    by_ground_source = [
        {'code': r.gs_id or '',
         'name': _gs_name_map.get(r.gs_id) or r.gs_id or '—',
         'type': r.gs_type or 'mnr',
         'total': r.cnt, 'won': int(r.won), 'in_progress': int(r.in_prog), 'lost': int(r.lost),
         'deal_value': float(r.dv), **_stage_dict(r), **_solar_stage_dict(r), **_completed_dict(r), **_received_dict(r)}
        for r in gs_rows
    ]

    # ── By Lead Source (top 50) ───────────────────────────────────────────────
    # DC-BY-SOURCE-GS-001 (May 2026): Derive source label from ground-source type first.
    #   source_ref_type IN ('vgk','vgk4u','vgk_partner') → 'VGK4U'
    #   source_ref_type = 'mnr' (or null default) with a ground-source id set → 'MNR'
    #   otherwise → fall back to the raw `source` field value
    _VGK_SRC_TYPES = ('vgk', 'vgk4u', 'vgk_partner')
    _has_gs = or_(CRMLead.source_ref_id.isnot(None), CRMLead.mnr_handler_id.isnot(None))
    _derived_src = _sa_case(
        (CRMLead.source_ref_type.in_(_VGK_SRC_TYPES), 'VGK4U'),
        (and_(_has_gs, _f.coalesce(CRMLead.source_ref_type, 'mnr') == 'mnr'), 'MNR'),
        else_=CRMLead.source,
    )
    src_rows = base.filter(
        _derived_src.isnot(None), _derived_src != ''
    ).with_entities(
        _derived_src.label('src_label'),
        _f.count(CRMLead.id).label('cnt'),
        _f.coalesce(_f.sum(_sa_case((_won_ok, 1), else_=0)), 0).label('won'),
        _f.coalesce(_f.sum(_sa_case((CRMLead.status.in_(IN_PROGRESS_STATUSES), 1), else_=0)), 0).label('in_prog'),
        _f.coalesce(_f.sum(_sa_case((CRMLead.status == 'lost', 1), else_=0)), 0).label('lost'),
        _f.coalesce(_f.sum(_eff_dv()), 0).label('dv'),
        *_completed_exprs(), *_received_exprs(),
    ).group_by(_derived_src).order_by(_f.sum(_sa_case((_won_ok, 1), else_=0)).desc(), _f.count(CRMLead.id).desc()).limit(50).all()
    by_source = [
        {'source': r.src_label, 'name': r.src_label, 'total': r.cnt, 'count': r.cnt,
         'won': int(r.won), 'in_progress': int(r.in_prog), 'lost': int(r.lost),
         'deal_value': float(r.dv), **_completed_dict(r), **_received_dict(r)}
        for r in src_rows
    ]
    # DC-DASH-TOTAL-001: Append "(No Source)" row so TOTAL row = header total.
    # "(No Source)" = no VGK/MNR ground source AND no raw source field.
    _src_assigned = sum(r['total'] for r in by_source)
    if total_leads > _src_assigned:
        _ns = base.filter(
            or_(_derived_src.is_(None), _derived_src == '')
        ).with_entities(
            _f.count(CRMLead.id).label('cnt'),
            _f.coalesce(_f.sum(_sa_case((_won_ok, 1), else_=0)), 0).label('won'),
            _f.coalesce(_f.sum(_sa_case((CRMLead.status.in_(IN_PROGRESS_STATUSES), 1), else_=0)), 0).label('in_prog'),
            _f.coalesce(_f.sum(_sa_case((CRMLead.status == 'lost', 1), else_=0)), 0).label('lost'),
            _f.coalesce(_f.sum(_eff_dv()), 0).label('dv'),
            *_completed_exprs(), *_received_exprs(),
        ).one()
        by_source.append({
            'source': '(No Source)', 'name': '(No Source)',
            'total': int(_ns.cnt), 'count': int(_ns.cnt),
            'won': int(_ns.won), 'in_progress': int(_ns.in_prog), 'lost': int(_ns.lost),
            'deal_value': float(_ns.dv), **_completed_dict(_ns), **_received_dict(_ns),
            '_unassigned': True,
        })

    # ── Monthly trend (last 12 months) — 3 separate queries ─────────────────
    # DC-TREND-DATE-001: Win Value bucketed by actual_close_date (not creation date).
    # Completed Value bucketed by complete_date. Total leads still by submit/created date.
    from datetime import date as _date
    import calendar as _cal
    from sqlalchemy import cast as _sa_cast, Date as _sa_Date
    _today = _date.today()
    _mo12_yr, _mo12_mn = _today.year, _today.month - 11
    while _mo12_mn <= 0:
        _mo12_mn += 12; _mo12_yr -= 1
    _mo12_start = datetime(_mo12_yr, _mo12_mn, 1)
    _trend_date_mo = _f.coalesce(CRMLead.submit_date, _sa_cast(CRMLead.created_at, _sa_Date))

    # Q1: Total leads by submit/creation date (with detailed metrics)
    from sqlalchemy import and_ as _sa_and, or_ as _sa_or
    _eff_dv_expr = _eff_dv()
    _EXCL_PIPE_PS = ['cancelled', 'not_interested', 'completed', 'loan_rejected', 'different_vendor', 'documents_issue']

    _mo_tot_rows = base.filter(_trend_date_mo >= _mo12_start.date()).with_entities(
        _f.date_trunc('month', _trend_date_mo).label('bucket'),
        _f.count(CRMLead.id).label('total'),
        _f.coalesce(_f.sum(_sa_case(
            (_sa_and(CRMLead.solar_pipeline_status.isnot(None), ~CRMLead.solar_pipeline_status.in_(['cancelled', 'not_interested'])), 1),
            else_=0
        )), 0).label('submitted'),
        _f.coalesce(_f.sum(_sa_case(
            (_sa_and(CRMLead.solar_pipeline_status.isnot(None), ~CRMLead.solar_pipeline_status.in_(['cancelled', 'not_interested'])), _eff_dv_expr),
            else_=0
        )), 0).label('sub_val'),
        _f.coalesce(_f.sum(_sa_case(
            (_sa_and(CRMLead.solar_pipeline_status.isnot(None), ~CRMLead.solar_pipeline_status.in_(_EXCL_PIPE_PS)), 1),
            else_=0
        )), 0).label('pipeline'),
        _f.coalesce(_f.sum(_sa_case(
            (_sa_and(CRMLead.solar_pipeline_status.isnot(None), ~CRMLead.solar_pipeline_status.in_(_EXCL_PIPE_PS)), _eff_dv_expr),
            else_=0
        )), 0).label('pipe_val'),
        _f.coalesce(_f.sum(_sa_case((CRMLead.solar_pipeline_status == 'pending_with_bank', 1), else_=0)), 0).label('at_bank'),
        _f.coalesce(_f.sum(_sa_case((CRMLead.solar_pipeline_status == 'electricity_bill_change', 1), else_=0)), 0).label('eb_change'),
        _f.coalesce(_f.sum(_sa_case(
            (CRMLead.solar_pipeline_status.in_(['installation_pending', 'net_meter_pending', 'balance_pending', 'balance_received', 'subsidy_pending']), 1),
            else_=0
        )), 0).label('in_prog'),
        _f.coalesce(_f.sum(_sa_case(
            (CRMLead.solar_pipeline_status.in_(['installation_pending', 'net_meter_pending', 'balance_pending', 'balance_received', 'subsidy_pending']), _eff_dv_expr),
            else_=0
        )), 0).label('in_prog_val'),
        _f.coalesce(_f.sum(_sa_case((CRMLead.solar_pipeline_status == 'installation_pending', 1), else_=0)), 0).label('inst_pending'),
        _f.coalesce(_f.sum(_sa_case((CRMLead.solar_pipeline_status == 'balance_pending', 1), else_=0)), 0).label('bal_pending')
    ).group_by('bucket').all()

    _mo_tot_map = {
        (r.bucket.year, r.bucket.month): (
            int(r.total), int(r.submitted), float(r.sub_val), int(r.pipeline), float(r.pipe_val),
            int(r.at_bank), int(r.eb_change), int(r.in_prog), float(r.in_prog_val),
            int(r.inst_pending), int(r.bal_pending)
        )
        for r in _mo_tot_rows if r.bucket
    }

    # Q2: Won leads — ALL segments use submit_date as primary WON bucket date.
    _mo_won_dt = _f.coalesce(
        CRMLead.submit_date,
        _sa_cast(CRMLead.actual_close_date, _sa_Date),
        _trend_date_mo,
    )
    _mo_won_rows = base.filter(_won_ok, _mo_won_dt >= _mo12_start.date()).with_entities(
        _f.date_trunc('month', _mo_won_dt).label('bucket'),
        _f.count(CRMLead.id).label('won'),
        _f.coalesce(_f.sum(_eff_dv()), 0).label('win_value'),
        _f.coalesce(_f.sum(CRMLead.deal_value_received), 0).label('win_recv'),
    ).group_by('bucket').all()
    _mo_won_map = {
        (r.bucket.year, r.bucket.month): (int(r.won), float(r.win_value), float(r.win_recv))
        for r in _mo_won_rows if r.bucket
    }

    # Q3: Completed leads bucketed by complete_date (fallback → submit/created)
    _mo_comp_dt = _f.coalesce(CRMLead.complete_date, _trend_date_mo)
    _mo_comp_rows = base.filter(_completed_cond, _mo_comp_dt >= _mo12_start.date()).with_entities(
        _f.date_trunc('month', _mo_comp_dt).label('bucket'),
        _f.count(CRMLead.id).label('completed'),
        _f.coalesce(_f.sum(_eff_dv()), 0).label('comp_value'),
        _f.coalesce(_f.sum(CRMLead.deal_value_received), 0).label('comp_recv'),
    ).group_by('bucket').all()
    _mo_comp_map = {
        (r.bucket.year, r.bucket.month): (int(r.completed), float(r.comp_value), float(r.comp_recv))
        for r in _mo_comp_rows if r.bucket
    }

    # Q4: Installed leads bucketed by installation_date
    _mo_inst_rows = base.filter(CRMLead.installation_date.isnot(None), CRMLead.installation_date >= _mo12_start.date()).with_entities(
        _f.date_trunc('month', _sa_cast(CRMLead.installation_date, _sa_Date)).label('bucket'),
        _f.count(CRMLead.id).label('installed')
    ).group_by('bucket').all()
    _mo_inst_map = {(r.bucket.year, r.bucket.month): int(r.installed) for r in _mo_inst_rows if r.bucket}

    monthly_trend = []
    for _mo in range(11, -1, -1):
        _yr = _today.year
        _mn = _today.month - _mo
        while _mn <= 0:
            _mn += 12; _yr -= 1
        _tot_data = _mo_tot_map.get((_yr, _mn), (0, 0, 0.0, 0, 0.0, 0, 0, 0, 0.0, 0, 0))
        (
            _m_total, _m_sub, _m_sub_val, _m_pipe, _m_pipe_val,
            _m_at_bank, _m_eb_change, _m_in_prog, _m_in_prog_val,
            _m_inst_pending, _m_bal_pending
        ) = _tot_data
        _m_won, _m_dv, _m_wr = _mo_won_map.get((_yr, _mn), (0, 0.0, 0.0))
        _m_comp, _m_fdv, _m_cr = _mo_comp_map.get((_yr, _mn), (0, 0.0, 0.0))
        _m_inst = _mo_inst_map.get((_yr, _mn), 0)
        monthly_trend.append({
            'label': f"{_date(1900, _mn, 1).strftime('%b')} {_yr}",
            'total': _m_total, 'won': _m_won,
            'submitted': _m_sub, 'submitted_value': _m_sub_val,
            'pipeline': _m_pipe, 'pipeline_value': _m_pipe_val,
            'at_bank': _m_at_bank, 'eb_change': _m_eb_change,
            'installed': _m_inst, 'completed': _m_comp, 'comp_value': _m_fdv,
            'in_progress': _m_in_prog, 'inprog_value': _m_in_prog_val,
            'inst_pending': _m_inst_pending, 'bal_pending': _m_bal_pending,
        })

    # ── Weekly trend (last 12 weeks) — 4 separate queries ────────────────────
    from datetime import timedelta as _td
    _today_dt = datetime.combine(_today, datetime.min.time())
    _week_start = _today_dt - _td(days=_today.weekday())
    _wk12_start = _week_start - _td(weeks=11)
    _trend_date_wk = _f.coalesce(CRMLead.submit_date, _sa_cast(CRMLead.created_at, _sa_Date))

    # Q1: Total leads by submit/creation date
    _wk_tot_rows = base.filter(_trend_date_wk >= _wk12_start.date()).with_entities(
        _f.date_trunc('week', _trend_date_wk).label('bucket'),
        _f.count(CRMLead.id).label('total'),
        _f.coalesce(_f.sum(_sa_case(
            (_sa_and(CRMLead.solar_pipeline_status.isnot(None), ~CRMLead.solar_pipeline_status.in_(['cancelled', 'not_interested'])), 1),
            else_=0
        )), 0).label('submitted'),
        _f.coalesce(_f.sum(_sa_case(
            (_sa_and(CRMLead.solar_pipeline_status.isnot(None), ~CRMLead.solar_pipeline_status.in_(['cancelled', 'not_interested'])), _eff_dv_expr),
            else_=0
        )), 0).label('sub_val'),
        _f.coalesce(_f.sum(_sa_case(
            (_sa_and(CRMLead.solar_pipeline_status.isnot(None), ~CRMLead.solar_pipeline_status.in_(_EXCL_PIPE_PS)), 1),
            else_=0
        )), 0).label('pipeline'),
        _f.coalesce(_f.sum(_sa_case(
            (_sa_and(CRMLead.solar_pipeline_status.isnot(None), ~CRMLead.solar_pipeline_status.in_(_EXCL_PIPE_PS)), _eff_dv_expr),
            else_=0
        )), 0).label('pipe_val'),
        _f.coalesce(_f.sum(_sa_case((CRMLead.solar_pipeline_status == 'pending_with_bank', 1), else_=0)), 0).label('at_bank'),
        _f.coalesce(_f.sum(_sa_case((CRMLead.solar_pipeline_status == 'electricity_bill_change', 1), else_=0)), 0).label('eb_change'),
        _f.coalesce(_f.sum(_sa_case(
            (CRMLead.solar_pipeline_status.in_(['installation_pending', 'net_meter_pending', 'balance_pending', 'balance_received', 'subsidy_pending']), 1),
            else_=0
        )), 0).label('in_prog'),
        _f.coalesce(_f.sum(_sa_case(
            (CRMLead.solar_pipeline_status.in_(['installation_pending', 'net_meter_pending', 'balance_pending', 'balance_received', 'subsidy_pending']), _eff_dv_expr),
            else_=0
        )), 0).label('in_prog_val'),
        _f.coalesce(_f.sum(_sa_case((CRMLead.solar_pipeline_status == 'installation_pending', 1), else_=0)), 0).label('inst_pending'),
        _f.coalesce(_f.sum(_sa_case((CRMLead.solar_pipeline_status == 'balance_pending', 1), else_=0)), 0).label('bal_pending')
    ).group_by('bucket').all()
    _wk_tot_map = {
        r.bucket.date(): (
            int(r.total), int(r.submitted), float(r.sub_val), int(r.pipeline), float(r.pipe_val),
            int(r.at_bank), int(r.eb_change), int(r.in_prog), float(r.in_prog_val),
            int(r.inst_pending), int(r.bal_pending)
        )
        for r in _wk_tot_rows if r.bucket
    }

    # Q2: Won leads — same date logic as monthly (DC-WON-DATE-ALL-001).
    _wk_won_dt = _f.coalesce(
        CRMLead.submit_date,
        _sa_cast(CRMLead.actual_close_date, _sa_Date),
        _trend_date_wk,
    )
    _wk_won_rows = base.filter(_won_ok, _wk_won_dt >= _wk12_start.date()).with_entities(
        _f.date_trunc('week', _wk_won_dt).label('bucket'),
        _f.count(CRMLead.id).label('won'),
        _f.coalesce(_f.sum(_eff_dv()), 0).label('win_value'),
        _f.coalesce(_f.sum(CRMLead.deal_value_received), 0).label('win_recv'),
    ).group_by('bucket').all()
    _wk_won_map = {r.bucket.date(): (int(r.won), float(r.win_value), float(r.win_recv)) for r in _wk_won_rows if r.bucket}

    # Q3: Completed leads by complete_date
    _wk_comp_dt = _f.coalesce(CRMLead.complete_date, _trend_date_wk)
    _wk_comp_rows = base.filter(_completed_cond, _wk_comp_dt >= _wk12_start.date()).with_entities(
        _f.date_trunc('week', _wk_comp_dt).label('bucket'),
        _f.count(CRMLead.id).label('completed'),
        _f.coalesce(_f.sum(_eff_dv()), 0).label('comp_value'),
        _f.coalesce(_f.sum(CRMLead.deal_value_received), 0).label('comp_recv'),
    ).group_by('bucket').all()
    _wk_comp_map = {r.bucket.date(): (int(r.completed), float(r.comp_value), float(r.comp_recv)) for r in _wk_comp_rows if r.bucket}

    # Q4: Installed leads by installation_date
    _wk_inst_rows = base.filter(CRMLead.installation_date.isnot(None), CRMLead.installation_date >= _wk12_start.date()).with_entities(
        _f.date_trunc('week', _sa_cast(CRMLead.installation_date, _sa_Date)).label('bucket'),
        _f.count(CRMLead.id).label('installed')
    ).group_by('bucket').all()
    _wk_inst_map = {r.bucket.date(): int(r.installed) for r in _wk_inst_rows if r.bucket}

    weekly_trend = []
    for _wk in range(11, -1, -1):
        _ws = _week_start - _td(weeks=_wk)
        _tot_data = _wk_tot_map.get(_ws.date(), (0, 0, 0.0, 0, 0.0, 0, 0, 0, 0.0, 0, 0))
        (
            _w_total, _w_submitted, _w_submitted_value, _w_pipeline, _w_pipeline_value,
            _w_at_bank, _w_eb_change, _w_in_progress, _w_inprog_value,
            _w_inst_pending, _w_bal_pending
        ) = _tot_data
        _w_won, _w_dv, _w_wr = _wk_won_map.get(_ws.date(), (0, 0.0, 0.0))
        _w_comp, _w_fdv, _w_cr = _wk_comp_map.get(_ws.date(), (0, 0.0, 0.0))
        _w_installed = _wk_inst_map.get(_ws.date(), 0)
        weekly_trend.append({
            'label': f"W{12-_wk} ({_ws.strftime('%d %b')})",
            'total': _w_total, 'won': _w_won,
            'submitted': _w_submitted, 'submitted_value': _w_submitted_value,
            'pipeline': _w_pipeline, 'pipeline_value': _w_pipeline_value,
            'at_bank': _w_at_bank, 'eb_change': _w_eb_change,
            'installed': _w_installed, 'completed': _w_comp, 'comp_value': _w_fdv,
            'in_progress': _w_in_progress, 'inprog_value': _w_inprog_value,
            'inst_pending': _w_inst_pending, 'bal_pending': _w_bal_pending,
        })

    # ── EV B2B Stage Breakdown ────────────────────────────────────────────────
    _B2B_STAGES = ['application_pending','agreement_pending','gst_pending','training_pending','branding_pending','payment_pending','dispatch_pending','confirmation_pending','completed']
    _b2b_rows = base.filter(CRMLead.ev_b2b_stage.isnot(None)).with_entities(
        CRMLead.ev_b2b_stage,
        _f.count(CRMLead.id).label('cnt')
    ).group_by(CRMLead.ev_b2b_stage).all()
    _b2b_map = {r.ev_b2b_stage: int(r.cnt) for r in _b2b_rows}
    b2b_stage_breakdown = {s: _b2b_map.get(s, 0) for s in _B2B_STAGES}

    # ── Generic CRM Status Breakdown (EV B2C / EV Spares / Real Dreams / Insurance) ──
    _GENERIC_STATUSES = ['new','contacted','interested','qualified','proposal','won','on_hold','lost']
    _gen_rows = base.with_entities(
        CRMLead.status,
        _f.count(CRMLead.id).label('cnt')
    ).group_by(CRMLead.status).all()
    _gen_map = {r.status: int(r.cnt) for r in _gen_rows}
    generic_status_breakdown = {s: _gen_map.get(s, 0) for s in _GENERIC_STATUSES}

    # ── Solar Pipeline Breakdown ──────────────────────────────────────────────
    _PIPELINE_STAGES = ['documents_pending','application_submitted','pending_with_bank','loan_rejected','documents_issue','load_extension','electricity_bill_change','installation_pending','net_meter_pending','balance_pending','balance_received','subsidy_pending','completed','not_interested','cancelled']
    _pl_rows = base.filter(CRMLead.solar_pipeline_status.isnot(None)).with_entities(
        CRMLead.solar_pipeline_status,
        _f.count(CRMLead.id).label('cnt')
    ).group_by(CRMLead.solar_pipeline_status).all()
    _pl_map = {r.solar_pipeline_status: int(r.cnt) for r in _pl_rows}
    pipeline_breakdown = {s: _pl_map.get(s, 0) for s in _PIPELINE_STAGES}
    # ── Loan Status Breakdown (lead.status based) ────────────────────────────
    _LOAN_STATUS_KEYS = ['waiting_for_bank_loan', 'bank_loan_rejected']
    _ls_rows = base.filter(CRMLead.status.in_(_LOAN_STATUS_KEYS)).with_entities(
        CRMLead.status, _f.count(CRMLead.id).label('cnt')
    ).group_by(CRMLead.status).all()
    _ls_map = {r.status: int(r.cnt) for r in _ls_rows}
    for _k in _LOAN_STATUS_KEYS:
        pipeline_breakdown[_k] = _ls_map.get(_k, 0)

    return {
        'summary': {
            'total_leads': total_leads,
            'won_leads': won_leads,
            'pipeline_leads': pipeline_leads,
            'in_progress_leads': in_progress,
            'lost_leads': lost_leads,
            'total_deal_value': float(_dv_all),
            'won_deal_value': float(_dv_won),
            'pipeline_deal_value': float(_dv_pipe),
            'avg_deal_value': round(_avg_dv, 2),
            'total_collected': _dv_coll,
            'total_pending': _dv_pend,
            'loan_rejected_pending': _dv_loan_rejected,
            'dv_active': _dv_active,
            'dv_pend_active': _dv_pend_active,
            'dv_completed': _dv_completed,
            'dv_lost_val': _dv_lost_val,
            'dv_ni': _dv_ni,
            'dv_hold': _dv_hold,
        },
        'pipeline_breakdown': pipeline_breakdown,
        'b2b_stage_breakdown': b2b_stage_breakdown,
        'generic_status_breakdown': generic_status_breakdown,
        'by_status': by_status,
        'by_category': by_category,
        'by_source': by_source,
        'by_ground_source': by_ground_source,
        'by_telecaller': by_telecaller,
        'by_field_staff': by_field_staff,
        'by_handler': by_handler,
        'by_guru': by_guru,
        'by_z_guru': by_z_guru,
        'by_adi_guru': by_adi_guru,
        'by_partner': by_partner,
        'monthly_trend': monthly_trend,
        'weekly_trend': weekly_trend
    }


def _resolve_phone_duplicate(phone, alt_phone, db, exclude_lead_id=None):
    """DC-DEDUP-002: Check primary + alternate phone against both DB phone columns.
    Returns (existing_lead, owner_employee, owner_is_active).
    All four cross-combinations are checked so swapping primary/alternate never bypasses the guard."""
    import re as _re
    def _clean(p):
        if not p:
            return None
        d = _re.sub(r'[^0-9]', '', str(p))
        return d[-10:] if len(d) >= 8 else None

    p = _clean(phone)
    a = _clean(alt_phone)
    if not p and not a:
        return None, None, True

    conditions = []
    for num in filter(None, [p, a]):
        conditions.append(func.regexp_replace(CRMLead.phone, '[^0-9]', '', 'g').like(f'%{num}'))
        conditions.append(func.regexp_replace(CRMLead.alternate_phone, '[^0-9]', '', 'g').like(f'%{num}'))

    q = db.query(CRMLead).filter(or_(*conditions))
    if exclude_lead_id:
        q = q.filter(CRMLead.id != exclude_lead_id)
    existing = q.order_by(CRMLead.id.asc()).first()
    if not existing:
        return None, None, True

    owner = None
    owner_active = True
    if existing.primary_owner_type == 'staff' and existing.primary_owner_id:
        owner = db.query(StaffEmployee).filter(StaffEmployee.id == existing.primary_owner_id).first()
        if owner:
            owner_active = (owner.status == 'active')
    return existing, owner, owner_active


@router.get("/exec-handler-leads")
def exec_handler_leads(
    handler_type: str = Query(..., description="Handler category: ground/handler/support/field/guru/zguru/adguru/partner/source"),
    handler_key: str = Query(..., description="Identifier (emp_code / mnr_id / partner_code / source_label / gs_id)"),
    handler_type_ext: Optional[str] = Query(None, description="Secondary type qualifier — for ground: gs_type (mnr/vgk/partner/staff)"),
    category: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    source: Optional[str] = Query(None),
    solar_pipeline_status: Optional[str] = Query(None),
    created_from: Optional[str] = Query(None),
    created_to: Optional[str] = Query(None),
    closed_from: Optional[str] = Query(None),
    closed_to: Optional[str] = Query(None),
    submit_date_from: Optional[str] = Query(None),
    submit_date_to: Optional[str] = Query(None),
    complete_date_from: Optional[str] = Query(None),
    complete_date_to: Optional[str] = Query(None),
    limit: int = Query(200, ge=1, le=500),
    db: Session = Depends(get_db),
    current_employee: StaffEmployee = Depends(get_current_staff_user)
):
    """DC-EXEC-DRILLDOWN-001: Lightweight lead list for one handler cell — exec dashboard drill-down.
    Applies same dashboard filters as lead-analytics so row counts match exactly."""
    from app.models.signup_category import SignupCategory as _SC2
    from sqlalchemy import literal as _lit

    POST_WON = ['won', 'order_placed', 'dispatched', 'delivered', 'installed', 'completed']
    _is_admin = is_vgk_admin((current_employee.staff_type or '').upper())
    # DC-EXEC-DRILLDOWN-002: named leadership roles get full (all-company) access here too,
    # matching the _AN_FULL_ACCESS rule already used by the lead-analytics summary endpoint —
    # otherwise leadership staff see summary counts that include other companies' leads but
    # get "No data" when they drill into a specific handler cell.
    _eh_role_code = (current_employee.role.role_code if current_employee.role else '') or ''
    if _eh_role_code in {'vgk4u', 'vgk4u_supreme', 'key_leadership', 'leadership_role', 'team_leader', 'manager'}:
        _is_admin = True

    def _pd(s):
        try:
            return datetime.fromisoformat(s.replace('Z', '+00:00').replace('T00:00:00+00:00', ''))
        except Exception:
            return None

    # Company scope — mirrors lead-analytics
    _all_cos = db.query(AssociatedCompany).filter(AssociatedCompany.is_active == True).all()
    if _is_admin:
        _co_ids = [c.id for c in _all_cos]
    else:
        _co_ids = [current_employee.base_company_id] if current_employee.base_company_id else [c.id for c in _all_cos]

    base = db.query(CRMLead).filter(CRMLead.company_id.in_(_co_ids))

    # Standard dashboard filters
    if category:
        _cids = [r.id for r in db.query(_SC2.id).filter(_SC2.name == category).all()]
        if _cids:
            _dsq = db.query(CRMLeadDeal.lead_id).filter(CRMLeadDeal.revenue_category_id.in_(_cids)).scalar_subquery()
            base = base.filter(or_(CRMLead.category_id.in_(_cids), CRMLead.id.in_(_dsq)))
        else:
            base = base.filter(CRMLead.id == -1)
    if status:
        base = base.filter(CRMLead.status.in_(POST_WON) if status == 'won_plus' else CRMLead.status == status)
    if source:
        base = base.filter(CRMLead.source.ilike(f'%{source}%'))
    if solar_pipeline_status:
        base = base.filter(CRMLead.solar_pipeline_status == solar_pipeline_status)
    if created_from:
        v = _pd(created_from)
        if v: base = base.filter(CRMLead.created_at >= v)
    if created_to:
        v = _pd(created_to)
        if v: base = base.filter(CRMLead.created_at <= v)
    if closed_from:
        v = _pd(closed_from)
        if v: base = base.filter(CRMLead.actual_close_date >= v)
    if closed_to:
        v = _pd(closed_to)
        if v: base = base.filter(CRMLead.actual_close_date <= v)
    if submit_date_from:
        v = _pd(submit_date_from)
        if v: base = base.filter(CRMLead.submit_date >= (v.date() if hasattr(v, 'date') else v))
    if submit_date_to:
        v = _pd(submit_date_to)
        if v: base = base.filter(CRMLead.submit_date <= (v.date() if hasattr(v, 'date') else v))
    if complete_date_from:
        v = _pd(complete_date_from)
        if v: base = base.filter(CRMLead.complete_date >= (v.date() if hasattr(v, 'date') else v))
    if complete_date_to:
        v = _pd(complete_date_to)
        if v: base = base.filter(CRMLead.complete_date <= (v.date() if hasattr(v, 'date') else v))

    # Handler-specific filter — mirrors the GROUP BY key used in lead-analytics
    if handler_type == 'handler':
        base = base.filter(CRMLead.handler_type == 'staff', CRMLead.handler_id == handler_key)
    elif handler_type == 'support':
        _tc = db.query(StaffEmployee).filter(StaffEmployee.emp_code == handler_key).first()
        if not _tc:
            return {'success': True, 'data': [], 'total': 0}
        base = base.filter(CRMLead.telecaller_id == _tc.id)
    elif handler_type == 'field':
        _fs = db.query(StaffEmployee).filter(StaffEmployee.emp_code == handler_key).first()
        if not _fs:
            return {'success': True, 'data': [], 'total': 0}
        base = base.filter(CRMLead.field_staff_id == _fs.id)
    elif handler_type == 'guru':
        base = base.filter(CRMLead.guru_id == handler_key)
    elif handler_type == 'zguru':
        base = base.filter(CRMLead.z_guru_id == handler_key)
    elif handler_type == 'adguru':
        base = base.filter(CRMLead.adi_guru_id == handler_key)
    elif handler_type == 'partner':
        from app.models.staff_accounts import OfficialPartner as _OP2
        _p = db.query(_OP2).filter(_OP2.partner_code == handler_key).first()
        if not _p:
            return {'success': True, 'data': [], 'total': 0}
        base = base.filter(CRMLead.associated_partner_id == _p.id)
    elif handler_type == 'ground':
        _gs_type = handler_type_ext or 'mnr'
        _gid_expr = func.coalesce(CRMLead.source_ref_id, CRMLead.mnr_handler_id)
        _gtype_expr = func.coalesce(CRMLead.source_ref_type, _lit('mnr'))
        base = base.filter(_gid_expr == handler_key, _gtype_expr == _gs_type)
    elif handler_type == 'source':
        _VGK_ST = ['vgk', 'vgk4u', 'vgk_partner']
        _has_gs = or_(CRMLead.source_ref_id.isnot(None), CRMLead.mnr_handler_id.isnot(None))
        if handler_key == 'VGK4U':
            base = base.filter(CRMLead.source_ref_type.in_(_VGK_ST))
        elif handler_key == 'MNR':
            base = base.filter(_has_gs, func.coalesce(CRMLead.source_ref_type, _lit('mnr')) == 'mnr')
        else:
            base = base.filter(CRMLead.source == handler_key)

    total = base.count()
    _leads = base.order_by(CRMLead.created_at.desc()).limit(limit).all()

    # Bulk enrich: category names
    _cids2 = list({l.category_id for l in _leads if l.category_id})
    _cmap = {}
    if _cids2:
        for c in db.query(_SC2).filter(_SC2.id.in_(_cids2)).all():
            _cmap[c.id] = c.name

    # Bulk enrich: solar brand names
    from app.models.vgk_incentive_brands import VGKIncentiveBrand as _VIB
    _bids = list({l.solar_brand_id for l in _leads if l.solar_brand_id})
    _bmap = {}
    if _bids:
        for b in db.query(_VIB).filter(_VIB.id.in_(_bids)).all():
            _bmap[b.id] = b.brand_name

    # Bulk enrich: latest note per lead (1 query)
    _lids = [l.id for l in _leads]
    _nmap = {}
    if _lids:
        _mnq = db.query(
            CRMLeadNote.lead_id,
            func.max(CRMLeadNote.id).label('mid')
        ).filter(CRMLeadNote.lead_id.in_(_lids)).group_by(CRMLeadNote.lead_id).subquery()
        for n in db.query(CRMLeadNote).join(_mnq, CRMLeadNote.id == _mnq.c.mid).all():
            _nmap[n.lead_id] = {
                'note': n.note,
                'by': n.created_by_id or '',
                'at': n.created_at.isoformat() if n.created_at else None,
            }

    # Bulk enrich user names for ground support
    from app.models.user import User as _User
    _uids = list({l.mnr_handler_id for l in _leads if l.mnr_handler_id})
    _unmap = {}
    if _uids:
        for u in db.query(_User).filter(_User.id.in_(_uids)).all():
            _unmap[u.id] = u.name or u.id

    # Bulk enrich: earliest transaction date per lead (DC-FIRST-PMT-003)
    _txmap = {}
    if _lids:
        from app.models.crm import CRMLeadTransaction as _CLT
        from sqlalchemy import func as _func
        _txs = db.query(_CLT.lead_id, _func.min(_CLT.transaction_date).label('min_date')).filter(
            _CLT.lead_id.in_(_lids),
            _CLT.transaction_date.isnot(None)
        ).group_by(_CLT.lead_id).all()
        for t in _txs:
            if t.min_date:
                _txmap[t.lead_id] = t.min_date.date() if hasattr(t.min_date, 'date') else t.min_date

    def _mask(ph):
        if not ph:
            return None
        d = ''.join(c for c in str(ph) if c.isdigit())
        return (d[:2] + '×' * (len(d) - 4) + d[-2:]) if len(d) >= 5 else ('×' * len(str(ph)))

    return {
        'success': True,
        'total': total,
        'data': [{
            'id': l.id,
            'company_id': l.company_id,
            'name': l.name or '—',
            'phone': _mask(l.phone),
            'phone_raw': l.phone,
            'created_at': l.created_at.isoformat() if l.created_at else None,
            'submit_date': l.submit_date.isoformat() if l.submit_date else None,
            'first_payment_received_date': (l.first_payment_received_date or _txmap.get(l.id)).isoformat() if (l.first_payment_received_date or _txmap.get(l.id)) else None,
            'source': l.source or '—',
            'ground_source': l.source_ref_name or '—',
            'ground_support': _unmap.get(l.mnr_handler_id, l.mnr_handler_id) if l.mnr_handler_id else '—',
            'status': l.status or '—',
            'solar_pipeline_status': l.solar_pipeline_status,
            'category_name': _cmap.get(l.category_id) if l.category_id else None,
            'loan_bank': l.loan_bank or None,
            'bank_branch': l.bank_branch or None,
            'brand_name': _bmap.get(l.solar_brand_id) if l.solar_brand_id else None,
            'deal_value_total': float(l.deal_value_total or 0),
            'deal_value_received': float(l.deal_value_received or 0),
            'latest_note': _nmap.get(l.id),
        } for l in _leads],
    }


@router.get("/exec-trend-leads")
def exec_trend_leads(
    period_type: str = Query(..., description="monthly or weekly"),
    label: str = Query(..., description="The month or week label"),
    metric: str = Query(..., description="The column/stage identifier"),
    category: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    source: Optional[str] = Query(None),
    solar_pipeline_status: Optional[str] = Query(None),
    created_from: Optional[str] = Query(None),
    created_to: Optional[str] = Query(None),
    closed_from: Optional[str] = Query(None),
    closed_to: Optional[str] = Query(None),
    submit_date_from: Optional[str] = Query(None),
    submit_date_to: Optional[str] = Query(None),
    complete_date_from: Optional[str] = Query(None),
    complete_date_to: Optional[str] = Query(None),
    limit: int = Query(200, ge=1, le=500),
    db: Session = Depends(get_db),
    current_employee: StaffEmployee = Depends(get_current_staff_user)
):
    """DC-EXEC-DRILLDOWN-003: Lightweight lead list for a trend cell.
    Applies the exact same bucketing and stage filter logic as the trends dashboard tables."""
    from app.models.signup_category import SignupCategory as _SC2
    from app.models.user import User as _User
    from sqlalchemy import cast as _sa_cast, Date as _sa_Date, and_ as _sa_and, or_ as _sa_or, func as _sa_func
    from datetime import date as _date, timedelta as _td

    POST_WON = ['won', 'order_placed', 'dispatched', 'delivered', 'installed', 'completed']
    _EXCL_WON_PS = ['loan_rejected', 'documents_issue', 'not_interested', 'cancelled', 'different_vendor']
    _EXCL_PIPE_PS = ['cancelled', 'not_interested', 'completed', 'loan_rejected', 'different_vendor', 'documents_issue']

    _is_admin = is_vgk_admin((current_employee.staff_type or '').upper())
    _eh_role_code = (current_employee.role.role_code if current_employee.role else '') or ''
    if _eh_role_code in {'vgk4u', 'vgk4u_supreme', 'key_leadership', 'leadership_role', 'team_leader', 'manager'}:
        _is_admin = True

    def _pd(s):
        try:
            return datetime.fromisoformat(s.replace('Z', '+00:00').replace('T00:00:00+00:00', ''))
        except Exception:
            return None

    # Parse company filters
    _all_cos = db.query(AssociatedCompany).filter(AssociatedCompany.is_active == True).all()
    if _is_admin:
        _co_ids = [c.id for c in _all_cos]
    else:
        _co_ids = [current_employee.base_company_id] if current_employee.base_company_id else [c.id for c in _all_cos]

    base = db.query(CRMLead).filter(CRMLead.company_id.in_(_co_ids))

    # Standard dashboard filters
    if category:
        _cids = [r.id for r in db.query(_SC2.id).filter(_SC2.name == category).all()]
        if _cids:
            _dsq = db.query(CRMLeadDeal.lead_id).filter(CRMLeadDeal.revenue_category_id.in_(_cids)).scalar_subquery()
            base = base.filter(_sa_or_(CRMLead.category_id.in_(_cids), CRMLead.id.in_(_dsq)))
        else:
            base = base.filter(CRMLead.id == -1)
    if status:
        base = base.filter(CRMLead.status.in_(POST_WON) if status == 'won_plus' else CRMLead.status == status)
    if source:
        base = base.filter(CRMLead.source.ilike(f'%{source}%'))
    if solar_pipeline_status:
        base = base.filter(CRMLead.solar_pipeline_status == solar_pipeline_status)
    if created_from:
        v = _pd(created_from)
        if v: base = base.filter(CRMLead.created_at >= v)
    if created_to:
        v = _pd(created_to)
        if v: base = base.filter(CRMLead.created_at <= v)
    if closed_from:
        v = _pd(closed_from)
        if v: base = base.filter(CRMLead.actual_close_date >= v)
    if closed_to:
        v = _pd(closed_to)
        if v: base = base.filter(CRMLead.actual_close_date <= v)
    if submit_date_from:
        v = _pd(submit_date_from)
        if v: base = base.filter(CRMLead.submit_date >= (v.date() if hasattr(v, 'date') else v))
    if submit_date_to:
        v = _pd(submit_date_to)
        if v: base = base.filter(CRMLead.submit_date <= (v.date() if hasattr(v, 'date') else v))
    if complete_date_from:
        v = _pd(complete_date_from)
        if v: base = base.filter(CRMLead.complete_date >= (v.date() if hasattr(v, 'date') else v))
    if complete_date_to:
        v = _pd(complete_date_to)
        if v: base = base.filter(CRMLead.complete_date <= (v.date() if hasattr(v, 'date') else v))

    # Determine period start/end dates
    start_dt = None
    end_dt = None
    if period_type == 'monthly':
        try:
            dt = datetime.strptime(label, "%b %Y")
            start_dt = _date(dt.year, dt.month, 1)
            import calendar
            last_day = calendar.monthrange(dt.year, dt.month)[1]
            end_dt = _date(dt.year, dt.month, last_day)
        except Exception:
            return {'success': False, 'detail': 'Invalid monthly label format'}
    elif period_type == 'weekly':
        _today_dt = datetime.combine(_date.today(), datetime.min.time())
        _week_start = _today_dt - _td(days=_today_dt.weekday())
        for _wk in range(12):
            _ws = _week_start - _td(weeks=_wk)
            lbl = f"W{12-_wk} ({_ws.strftime('%d %b')})"
            lbl_alt = f"W{12-_wk} ({_ws.strftime('%-d %b')})"
            if label == lbl or label == lbl_alt:
                start_dt = _ws.date()
                end_dt = start_dt + _td(days=6)
                break
        if not start_dt:
            return {'success': False, 'detail': 'Invalid weekly label format'}

    # Date bucketing and status conditions
    _trend_date_expr = _sa_func.coalesce(CRMLead.submit_date, _sa_cast(CRMLead.created_at, _sa_Date))
    _won_ok = _sa_and(
        CRMLead.status.in_(POST_WON),
        _sa_or(CRMLead.solar_pipeline_status.is_(None), ~CRMLead.solar_pipeline_status.in_(_EXCL_WON_PS))
    )
    from sqlalchemy import text as _ex_text
    _etc_done_sq = _ex_text(
        "EXISTS (SELECT 1 FROM etc_students s "
        "WHERE s.crm_lead_id = crm_leads.id "
        "AND s.training_completed_date IS NOT NULL "
        "AND s.is_active = TRUE)"
    )
    _completed_cond = _sa_or(
        CRMLead.solar_pipeline_status == 'completed',
        CRMLead.ev_b2b_stage == 'completed',
        _sa_and(CRMLead.status.in_(POST_WON), CRMLead.solar_pipeline_status.is_(None), CRMLead.ev_b2b_stage.is_(None)),
        _etc_done_sq
    )

    if metric == 'won':
        _won_dt_expr = _sa_func.coalesce(
            CRMLead.submit_date,
            _sa_cast(CRMLead.actual_close_date, _sa_Date),
            _trend_date_expr
        )
        base = base.filter(_won_ok, _won_dt_expr >= start_dt, _won_dt_expr <= end_dt)
    elif metric == 'installed':
        base = base.filter(CRMLead.installation_date.isnot(None), CRMLead.installation_date >= start_dt, CRMLead.installation_date <= end_dt)
    elif metric == 'completed':
        _comp_dt_expr = _sa_func.coalesce(CRMLead.complete_date, _trend_date_expr)
        base = base.filter(_completed_cond, _comp_dt_expr >= start_dt, _comp_dt_expr <= end_dt)
    else:
        # Default trend date bucketing
        base = base.filter(_trend_date_expr >= start_dt, _trend_date_expr <= end_dt)
        if metric == 'submitted':
            base = base.filter(CRMLead.solar_pipeline_status.isnot(None), ~CRMLead.solar_pipeline_status.in_(['cancelled', 'not_interested']))
        elif metric == 'pipeline':
            base = base.filter(CRMLead.solar_pipeline_status.isnot(None), ~CRMLead.solar_pipeline_status.in_(_EXCL_PIPE_PS))
        elif metric == 'at_bank':
            base = base.filter(CRMLead.solar_pipeline_status == 'pending_with_bank')
        elif metric == 'eb_change':
            base = base.filter(CRMLead.solar_pipeline_status == 'electricity_bill_change')
        elif metric == 'in_progress':
            base = base.filter(CRMLead.solar_pipeline_status.in_(['installation_pending', 'net_meter_pending', 'balance_pending', 'balance_received', 'subsidy_pending']))
        elif metric == 'inst_pending':
            base = base.filter(CRMLead.solar_pipeline_status == 'installation_pending')
        elif metric == 'bal_pending':
            base = base.filter(CRMLead.solar_pipeline_status == 'balance_pending')

    total = base.count()
    _leads = base.order_by(CRMLead.created_at.desc()).limit(limit).all()

    # Bulk enrich: category names
    _cids2 = list({l.category_id for l in _leads if l.category_id})
    _cmap = {}
    if _cids2:
        for c in db.query(_SC2).filter(_SC2.id.in_(_cids2)).all():
            _cmap[c.id] = c.name

    # Bulk enrich: solar brand names
    from app.models.vgk_incentive_brands import VGKIncentiveBrand as _VIB
    _bids = list({l.solar_brand_id for l in _leads if l.solar_brand_id})
    _bmap = {}
    if _bids:
        for b in db.query(_VIB).filter(_VIB.id.in_(_bids)).all():
            _bmap[b.id] = b.brand_name

    # Bulk enrich: latest note per lead
    _lids = [l.id for l in _leads]
    _nmap = {}
    if _lids:
        _mnq = db.query(CRMLeadNote.lead_id, _sa_func.max(CRMLeadNote.id).label('mid')).filter(CRMLeadNote.lead_id.in_(_lids)).group_by(CRMLeadNote.lead_id).subquery()
        for n in db.query(CRMLeadNote).join(_mnq, CRMLeadNote.id == _mnq.c.mid).all():
            _nmap[n.lead_id] = {
                'note': n.note,
                'by': n.created_by_id or '',
                'at': n.created_at.isoformat() if n.created_at else None,
            }

    # Bulk enrich user names for ground support
    _uids = list({l.mnr_handler_id for l in _leads if l.mnr_handler_id})
    _unmap = {}
    if _uids:
        for u in db.query(_User).filter(_User.id.in_(_uids)).all():
            _unmap[u.id] = u.name or u.id

    # Bulk enrich: earliest transaction date per lead (DC-FIRST-PMT-003)
    _txmap = {}
    if _lids:
        from app.models.crm import CRMLeadTransaction as _CLT
        _txs = db.query(_CLT.lead_id, _sa_func.min(_CLT.transaction_date).label('min_date')).filter(
            _CLT.lead_id.in_(_lids),
            _CLT.transaction_date.isnot(None)
        ).group_by(_CLT.lead_id).all()
        for t in _txs:
            if t.min_date:
                _txmap[t.lead_id] = t.min_date.date() if hasattr(t.min_date, 'date') else t.min_date

    def _mask(ph):
        if not ph:
            return None
        d = ''.join(c for c in str(ph) if c.isdigit())
        return (d[:2] + '×' * (len(d) - 4) + d[-2:]) if len(d) >= 5 else ('×' * len(str(ph)))

    return {
        'success': True,
        'total': total,
        'data': [{
            'id': l.id,
            'company_id': l.company_id,
            'name': l.name or '—',
            'phone': _mask(l.phone),
            'phone_raw': l.phone,
            'created_at': l.created_at.isoformat() if l.created_at else None,
            'submit_date': l.submit_date.isoformat() if l.submit_date else None,
            'first_payment_received_date': (l.first_payment_received_date or _txmap.get(l.id)).isoformat() if (l.first_payment_received_date or _txmap.get(l.id)) else None,
            'installation_date': l.installation_date.isoformat() if l.installation_date else None,
            'source': l.source or '—',
            'ground_source': l.source_ref_name or '—',
            'ground_support': _unmap.get(l.mnr_handler_id, l.mnr_handler_id) if l.mnr_handler_id else '—',
            'status': l.status or '—',
            'solar_pipeline_status': l.solar_pipeline_status,
            'category_name': _cmap.get(l.category_id) if l.category_id else None,
            'loan_bank': l.loan_bank or None,
            'bank_branch': l.bank_branch or None,
            'brand_name': _bmap.get(l.solar_brand_id) if l.solar_brand_id else None,
            'deal_value_total': float(l.deal_value_total or 0),
            'deal_value_received': float(l.deal_value_received or 0),
            'balance_pending': float(l.deal_value_balance or 0),
            'latest_note': _nmap.get(l.id),
        } for l in _leads],
    }


@router.get("/leads/check-duplicate")
def check_lead_duplicate(
    phone: Optional[str] = Query(None),
    alt_phone: Optional[str] = Query(None),
    company_id: int = Query(...),
    db: Session = Depends(get_db),
    current_employee: StaffEmployee = Depends(get_current_staff_user)
):
    """DC-DEDUP-002: Pre-flight duplicate check for lead creation UI.
    Checks the given phone + alt_phone against both phone and alternate_phone DB columns.
    Frontend calls this BEFORE POSTing so it can show a rich warning modal."""
    existing, owner, owner_active = _resolve_phone_duplicate(phone, alt_phone, db)
    if not existing:
        return {"duplicate": False}
    owner_name = owner_emp_code = owner_status = None
    if owner:
        owner_name = f"{owner.first_name or ''} {owner.last_name or ''}".strip() or owner.emp_code
        owner_emp_code = owner.emp_code
        owner_status = owner.status
    return {
        "duplicate": True,
        "lead": {
            "id": existing.id,
            "name": existing.name or "",
            "phone": existing.phone or "",
            "alternate_phone": existing.alternate_phone or "",
            "status": existing.status,
            "company_id": existing.company_id,
        },
        "owner": {
            "id": owner.id if owner else None,
            "name": owner_name,
            "emp_code": owner_emp_code,
            "status": owner_status,
        } if owner else None,
        "owner_active": owner_active,
    }


@router.post("/leads")
def create_lead(
    lead_data: LeadCreate,
    company_id: int = Query(..., description="Company ID for DC Protocol"),
    db: Session = Depends(get_db),
    current_employee: StaffEmployee = Depends(get_current_staff_user)
):
    """Create a new lead - DC Protocol enforced"""
    from app.models.staff import StaffEmployee as SE
    from app.models.staff_accounts import OfficialPartner
    
    # DC_LIMBO_FIX: Prevent handler_type='staff' with empty/invalid handler_id (limbo lead prevention)
    if lead_data.handler_type == 'staff':
        handler_id_val = str(lead_data.handler_id).strip() if lead_data.handler_id else ''
        if not handler_id_val:
            raise HTTPException(
                status_code=422,
                detail="handler_id (emp_code) is required when handler_type is 'staff'. Set handler_type='unassigned' if no staff member is assigned."
            )
        # Verify handler_id maps to a real active staff emp_code
        valid_handler = db.query(StaffEmployee).filter(
            StaffEmployee.emp_code == handler_id_val,
            StaffEmployee.status == 'active'
        ).first()
        # DC_INT_FALLBACK: Legacy data may store numeric employee ID instead of emp_code.
        # Auto-convert: look up employee by integer ID and substitute their emp_code.
        if not valid_handler and handler_id_val.isdigit():
            by_id = db.query(StaffEmployee).filter(
                StaffEmployee.id == int(handler_id_val),
                StaffEmployee.status == 'active'
            ).first()
            if by_id:
                valid_handler = by_id
                handler_id_val = by_id.emp_code
                print(f"[DC_INT_FALLBACK] handler_id integer {lead_data.handler_id!r} → emp_code {handler_id_val!r} (create)", flush=True)
        if not valid_handler:
            raise HTTPException(
                status_code=422,
                detail=f"handler_id '{handler_id_val}' is not a valid active staff emp_code. Assign a valid emp_code or use handler_type='unassigned'."
            )
        # DC_LIMBO_FIX: Normalize handler_id to trimmed canonical value for storage
        lead_data.handler_id = handler_id_val

    # DC_CAT_COMPANY: Category is the source of truth for company routing.
    # If category_id is provided, derive company from it (overrides query param).
    # This ensures leads with a category are never orphaned or misrouted.
    resolved_company_id = company_id
    if lead_data.category_id:
        category = db.query(SignupCategory).filter(
            SignupCategory.id == lead_data.category_id
        ).first()
        if not category:
            raise HTTPException(status_code=400, detail="Invalid category")
        if category.company_id:
            resolved_company_id = category.company_id

    # Cross-company assignment allowed for telecaller (per user requirement)
    validated_telecaller_id = None
    if lead_data.telecaller_id:
        telecaller = db.query(SE).filter(SE.id == lead_data.telecaller_id, SE.status == 'active').first()
        if not telecaller:
            raise HTTPException(status_code=400, detail="Invalid or inactive telecaller")
        validated_telecaller_id = lead_data.telecaller_id
    
    # Cross-company assignment allowed for field staff (per user requirement)
    validated_field_staff_id = None
    if lead_data.field_staff_id:
        field_staff = db.query(SE).filter(SE.id == lead_data.field_staff_id, SE.status == 'active').first()
        if not field_staff:
            raise HTTPException(status_code=400, detail="Invalid or inactive field staff")
        validated_field_staff_id = lead_data.field_staff_id
    
    # DC Protocol Exception: Partner can be cross-company (for tagging).
    # Inactive partners are also allowed — they may still be tagged for attribution.
    validated_partner_id = None
    if lead_data.associated_partner_id:
        partner = db.query(OfficialPartner).filter(
            OfficialPartner.id == lead_data.associated_partner_id
        ).first()
        if not partner:
            raise HTTPException(status_code=400, detail="Invalid partner")
        validated_partner_id = lead_data.associated_partner_id
    
    # DC-MNR-VGK-SOURCE-001: auto-derive source label from ground-source type when
    # the caller has not explicitly chosen a different source.
    _src_type_create = lead_data.source_ref_type or (
        'mnr' if lead_data.mnr_handler_id else None
    )
    _resolved_source = lead_data.source
    if _src_type_create in ('mnr',) and not _resolved_source:
        _resolved_source = 'MNR'
    elif _src_type_create in ('vgk', 'vgk_partner') and not _resolved_source:
        _resolved_source = 'VGK4U'

    # DC-DEDUP-002: Block creation when phone/alternate_phone already exists in CRM.
    # Active owner → 409 blocked outright. Inactive owner → 409 with reassign hint.
    if lead_data.phone or lead_data.alternate_phone:
        _dup_lead, _dup_owner, _dup_active = _resolve_phone_duplicate(
            lead_data.phone, lead_data.alternate_phone, db
        )
        if _dup_lead:
            _dup_owner_name = _dup_owner_status = None
            if _dup_owner:
                _dup_owner_name = f"{_dup_owner.first_name or ''} {_dup_owner.last_name or ''}".strip() or _dup_owner.emp_code
                _dup_owner_status = _dup_owner.status
            raise HTTPException(
                status_code=409,
                detail={
                    "type": "duplicate_lead",
                    "message": f"Mobile number already exists in Lead #{_dup_lead.id} ({_dup_lead.name or 'Unnamed'}).",
                    "lead_id": _dup_lead.id,
                    "lead_name": _dup_lead.name or "",
                    "lead_status": _dup_lead.status,
                    "lead_company_id": _dup_lead.company_id,
                    "owner_name": _dup_owner_name,
                    "owner_status": _dup_owner_status,
                    "owner_active": _dup_active,
                    "lead": {
                        "id": _dup_lead.id,
                        "name": _dup_lead.name or "",
                        "phone": _dup_lead.phone or "",
                        "alternate_phone": _dup_lead.alternate_phone or "",
                        "status": _dup_lead.status,
                        "company_id": _dup_lead.company_id,
                    },
                    "owner": {
                        "id": _dup_owner.id if _dup_owner else None,
                        "name": _dup_owner_name,
                        "emp_code": _dup_owner.emp_code if _dup_owner else None,
                        "status": _dup_owner_status,
                    } if _dup_owner else None,
                }
            )

    new_lead = CRMLead(
        company_id=resolved_company_id,
        name=lead_data.name,
        email=lead_data.email,
        phone=lead_data.phone,
        phone_primary_whatsapp=lead_data.phone_primary_whatsapp or False,
        alternate_phone=lead_data.alternate_phone,
        phone_secondary_whatsapp=lead_data.phone_secondary_whatsapp or False,
        category_id=lead_data.category_id,
        source=_resolved_source,
        source_details=lead_data.source_details,
        status=lead_data.status or 'new',
        priority=lead_data.priority or 'medium',
        handler_type=lead_data.handler_type or 'unassigned',
        handler_id=lead_data.handler_id,
        telecaller_id=validated_telecaller_id,
        field_staff_id=validated_field_staff_id,
        associated_partner_id=validated_partner_id,
        mnr_handler_id=lead_data.mnr_handler_id,
        guru_id=lead_data.guru_id,
        z_guru_id=lead_data.z_guru_id,
        adi_guru_id=lead_data.adi_guru_id,
        guru_name=lead_data.guru_name,
        z_guru_name=lead_data.z_guru_name,
        is_vgk_program=lead_data.is_vgk_program or False,
        vgk_field_support_id=lead_data.vgk_field_support_id,
        solar_brand_id=lead_data.solar_brand_id,
        source_ref_type=lead_data.source_ref_type,
        source_ref_id=lead_data.source_ref_id,
        source_ref_name=lead_data.source_ref_name,
        field_support_ref_type=lead_data.field_support_ref_type,
        field_support_ref_id=lead_data.field_support_ref_id,
        field_support_ref_name=lead_data.field_support_ref_name,
        technical_id=lead_data.technical_id,
        support_staff_id=lead_data.support_staff_id,
        technical_staff1_id=lead_data.technical_staff1_id,
        description=lead_data.description,
        requirements=lead_data.requirements,
        looking_for=lead_data.looking_for,
        recent_comments=lead_data.recent_comments,
        budget_min=lead_data.budget_min,
        budget_max=lead_data.budget_max,
        address=lead_data.address,
        area=lead_data.area,
        city=lead_data.city,
        state=lead_data.state,
        pincode=lead_data.pincode,
        expected_close_date=lead_data.expected_close_date,
        next_followup_date=lead_data.next_followup_date,
        depends_on_staff_id=lead_data.depends_on_staff_id,
        tags=lead_data.tags,
        created_by_type='staff',
        created_by_id=current_employee.emp_code,
        primary_owner_type='staff',
        primary_owner_id=current_employee.id
    )
    
    # DC-INLINE-GURU-001 backend (CREATE): Auto-derive upline chain at lead creation time.
    # Mirrors the update-time derivation in the PUT handler so new leads are never missing core.
    _cr_src_type = lead_data.source_ref_type or ''
    _cr_src_id   = lead_data.source_ref_id
    if _cr_src_type in ('vgk', 'vgk_partner', 'partner') and _cr_src_id:
        try:
            _cr_gsp = db.query(OfficialPartner).filter(OfficialPartner.id == int(_cr_src_id)).first()
            if _cr_gsp and _cr_gsp.parent_partner_id:
                new_lead.team_senior_partner_id = _cr_gsp.parent_partner_id
                _cr_sr = db.query(OfficialPartner).filter(OfficialPartner.id == _cr_gsp.parent_partner_id).first()
                if _cr_sr and _cr_sr.parent_partner_id:
                    new_lead.team_extended_partner_id = _cr_sr.parent_partner_id
                    _cr_ext = db.query(OfficialPartner).filter(OfficialPartner.id == _cr_sr.parent_partner_id).first()
                    new_lead.team_core_partner_id = _cr_ext.parent_partner_id if (_cr_ext and _cr_ext.parent_partner_id) else None
                else:
                    new_lead.team_extended_partner_id = None
                    new_lead.team_core_partner_id = None
            else:
                new_lead.team_senior_partner_id = None
                new_lead.team_extended_partner_id = None
                new_lead.team_core_partner_id = None
        except (ValueError, TypeError):
            pass

    db.add(new_lead)
    db.commit()
    db.refresh(new_lead)
    
    if lead_data.handler_type and lead_data.handler_type != 'unassigned':
        assignment = CRMLeadAssignment(
            company_id=company_id,
            lead_id=new_lead.id,
            from_handler_type=None,
            from_handler_id=None,
            to_handler_type=lead_data.handler_type,
            to_handler_id=lead_data.handler_id,
            reason='Initial assignment',
            assigned_by_type='staff',
            assigned_by_id=current_employee.emp_code
        )
        db.add(assignment)
        db.commit()

    # ── WhatsApp auto-trigger: new lead created ───────────────────────────
    try:
        from app.services.whatsapp_auto_service import send_auto_whatsapp, send_lead_welcome
        _new_lead_phone = getattr(new_lead, 'phone', None) or getattr(new_lead, 'mobile', None)
        if _new_lead_phone:
            # DC Protocol Apr 2026: Use bilingual lead welcome templates
            # Walk-in via partner → include partner phone; all others → general template
            _partner_phone = None
            if new_lead.associated_partner_id:
                _partner = db.query(OfficialPartner).filter(
                    OfficialPartner.id == new_lead.associated_partner_id
                ).first()
                if _partner:
                    _partner_phone = _partner.phone or _partner.whatsapp_number
            send_lead_welcome(
                db=db,
                phone=_new_lead_phone,
                lead_name=getattr(new_lead, 'name', '') or '',
                lead_id=new_lead.id,
                partner_phone=_partner_phone,
                staff_id=getattr(current_employee, 'id', None),
            )
            # Also fire the legacy crm_lead_created trigger if configured
            send_auto_whatsapp(
                db=db, event_key='crm_lead_created', phone=_new_lead_phone,
                context={'name': getattr(new_lead, 'name', '') or '', 'lead_id': new_lead.id},
                lead_id=new_lead.id,
                staff_id=getattr(current_employee, 'id', None),
            )
            # DC_WA_TEMPLATES_SEED_001: Fire thank-you WA for walk-in leads separately
            if new_lead.associated_partner_id:
                _partner_name = ''
                if _partner:
                    _partner_name = getattr(_partner, 'business_name', '') or getattr(_partner, 'name', '') or ''
                _today_str = __import__('datetime').datetime.utcnow().strftime('%d %b %Y')
                _lead_ref = f"MNR-LEAD-{new_lead.id}"
                # T11: Thank-you WA to the customer
                send_auto_whatsapp(
                    db=db, event_key='crm_lead_walkin_created', phone=_new_lead_phone,
                    context={
                        'name': getattr(new_lead, 'name', '') or '',
                        'lead_ref': _lead_ref,
                        'date': _today_str,
                        'partner_name': _partner_name,
                    },
                    lead_id=new_lead.id,
                    staff_id=getattr(current_employee, 'id', None),
                )
                # T17: Notify the PARTNER that a new walk-in was registered at their outlet
                if _partner_phone:
                    send_auto_whatsapp(
                        db=db, event_key='crm_lead_walkin_partner_notify', phone=str(_partner_phone),
                        context={
                            'partner_name': _partner_name,
                            'customer_name': getattr(new_lead, 'name', '') or '',
                            'date': _today_str,
                            'lead_ref': _lead_ref,
                        },
                        lead_id=new_lead.id,
                        staff_id=getattr(current_employee, 'id', None),
                    )
    except Exception as _wa_ex:
        print(f"[WA-AUTO] create_lead hook error: {_wa_ex}")

    # DC_WA_TEMPLATES_SEED_001: Notify assigned staff about new lead
    try:
        from app.services.whatsapp_auto_service import send_lead_assigned_staff_wa
        _assigned_id = getattr(new_lead, 'telecaller_id', None) or getattr(new_lead, 'field_staff_id', None)
        if _assigned_id:
            _assigned_staff = db.query(SE).filter(SE.id == _assigned_id).first()
            if _assigned_staff:
                send_lead_assigned_staff_wa(
                    db, new_lead, _assigned_staff,
                    triggered_by_id=getattr(current_employee, 'id', None)
                )
    except Exception as _wa2_ex:
        print(f"[WA-AUTO] lead_assign hook error: {_wa2_ex}")
    # ─────────────────────────────────────────────────────────────────────

    return {
        'success': True,
        'message': 'Lead created successfully',
        'data': new_lead.to_dict()
    }


@router.get("/leads/{lead_id}")
def get_lead(
    lead_id: int,
    company_id: int = Query(..., description="Company ID for DC Protocol"),
    db: Session = Depends(get_db),
    current_employee: StaffEmployee = Depends(get_current_staff_user)
):
    """Get lead details with follow-ups and notes"""
    import traceback
    try:
        lead = db.query(CRMLead).filter(
            CRMLead.id == lead_id,
            CRMLead.company_id == company_id
        ).first()
        
        if not lead:
            raise HTTPException(status_code=404, detail="Lead not found")
        
        try:
            lead_dict = lead.to_dict()
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error in lead.to_dict(): {str(e)}")

        # DC Protocol N001/N003 — derive handler/source type for frontend
        try:
            lead_dict['lead_handler_type'] = _derive_lead_handler_type(lead)
        except Exception:
            lead_dict['lead_handler_type'] = 'Direct'

        try:
            category = db.query(SignupCategory).filter(SignupCategory.id == lead.category_id).first()
            lead_dict['category_name'] = category.name if category else None
        except Exception as e:
            lead_dict['category_name'] = None
        
        try:
            if lead.telecaller_id:
                telecaller = db.query(StaffEmployee).filter(
                    StaffEmployee.id == lead.telecaller_id
                ).first()
                if telecaller:
                    lead_dict['telecaller_name'] = telecaller.full_name or telecaller.emp_code
                    lead_dict['telecaller_code'] = telecaller.emp_code
                    lead_dict['telecaller_status'] = telecaller.status
        except Exception as e:
            pass
        
        try:
            if lead.field_staff_id:
                field_staff = db.query(StaffEmployee).filter(
                    StaffEmployee.id == lead.field_staff_id
                ).first()
                if field_staff:
                    lead_dict['field_staff_name'] = field_staff.full_name or field_staff.emp_code
                    lead_dict['field_staff_code'] = field_staff.emp_code
                    lead_dict['field_staff_status'] = field_staff.status
        except Exception as e:
            pass
        
        try:
            if lead.vendor_id:
                vendor = db.query(VendorMaster).filter(
                    VendorMaster.id == lead.vendor_id
                ).first()
                if vendor:
                    lead_dict['vendor_name'] = vendor.vendor_name or vendor.vendor_code
                    lead_dict['vendor_code'] = vendor.vendor_code
        except Exception as e:
            pass
        
        try:
            if lead.associated_partner_id:
                from app.models.staff_accounts import OfficialPartner
                partner = db.query(OfficialPartner).filter(
                    OfficialPartner.id == lead.associated_partner_id
                ).first()
                if partner:
                    lead_dict['associated_partner_name'] = partner.partner_name or partner.contact_person or partner.partner_code
                    lead_dict['associated_partner_code'] = partner.partner_code
        except Exception as e:
            pass
        
        try:
            if lead.mnr_handler_id:
                mnr_handler = db.query(User).filter(User.id == lead.mnr_handler_id).first()
                if mnr_handler:
                    lead_dict['mnr_handler_name'] = mnr_handler.name or lead.mnr_handler_id
                    lead_dict['mnr_handler_code'] = lead.mnr_handler_id
        except Exception as e:
            pass
        
        try:
            if lead.guru_id:
                guru = db.query(User).filter(User.id == lead.guru_id).first()
                if guru:
                    lead_dict['guru_name'] = guru.name or lead.guru_id
                    lead_dict['guru_code'] = lead.guru_id
            # DC Protocol Fix (Apr 2026): Fallback to stored text name for partner-chain uplines
            # (guru_id is null for partner sources, name stored in guru_name column)
            if not lead_dict.get('guru_name'):
                _stored_gn = getattr(lead, 'guru_name', None)
                if _stored_gn:
                    lead_dict['guru_name'] = _stored_gn
        except Exception as e:
            pass

        try:
            if getattr(lead, 'z_guru_id', None):
                z_guru = db.query(User).filter(User.id == lead.z_guru_id).first()
                if z_guru:
                    lead_dict['z_guru_name'] = z_guru.name or lead.z_guru_id
                    lead_dict['z_guru_code'] = lead.z_guru_id
            # DC Protocol Fix (Apr 2026): Fallback to stored text name for partner-chain uplines
            if not lead_dict.get('z_guru_name'):
                _stored_zgn = getattr(lead, 'z_guru_name', None)
                if _stored_zgn:
                    lead_dict['z_guru_name'] = _stored_zgn
        except Exception as e:
            pass

        try:
            if lead.adi_guru_id:
                adi_guru = db.query(User).filter(User.id == lead.adi_guru_id).first()
                if adi_guru:
                    lead_dict['adi_guru_name'] = adi_guru.name or lead.adi_guru_id
                    lead_dict['adi_guru_code'] = lead.adi_guru_id
        except Exception as e:
            pass

        try:
            if lead.vgk_field_support_id:
                from app.models.staff_accounts import OfficialPartner as _OP
                vgk_fs = db.query(_OP).filter(_OP.id == lead.vgk_field_support_id).first()
                if vgk_fs:
                    lead_dict['vgk_field_support_name'] = vgk_fs.partner_name
                    lead_dict['vgk_field_support_code'] = vgk_fs.partner_code
        except Exception:
            pass

        try:
            if lead.technical_id:
                _tech = db.query(StaffEmployee).filter(StaffEmployee.id == lead.technical_id).first()
                if _tech:
                    lead_dict['technical_name'] = _tech.full_name or _tech.emp_code
                    lead_dict['technical_code'] = _tech.emp_code
        except Exception:
            pass

        try:
            # DC_LEAD_DETAIL_FIX: Bounded explicit query (no unbounded lazy-load) prevents
            # worker crash when a lead has many followups loaded concurrently (lead 7331 pattern)
            followup_rows = db.query(CRMLeadFollowUp).filter(
                CRMLeadFollowUp.lead_id == lead_id
            ).order_by(CRMLeadFollowUp.scheduled_date.desc()).limit(100).all()
            lead_dict['followups'] = [f.to_dict() for f in followup_rows]
            lead_dict['followups_total'] = db.query(CRMLeadFollowUp).filter(
                CRMLeadFollowUp.lead_id == lead_id
            ).count() if len(followup_rows) == 100 else len(followup_rows)
        except Exception as e:
            lead_dict['followups'] = []
            lead_dict['followups_total'] = 0

        try:
            # DC_LEAD_DETAIL_FIX: Same bounded approach for notes
            note_rows = db.query(CRMLeadNote).filter(
                CRMLeadNote.lead_id == lead_id
            ).order_by(CRMLeadNote.created_at.desc()).limit(100).all()
            lead_dict['notes'] = [n.to_dict() for n in note_rows]
            lead_dict['notes_total'] = db.query(CRMLeadNote).filter(
                CRMLeadNote.lead_id == lead_id
            ).count() if len(note_rows) == 100 else len(note_rows)
        except Exception as e:
            lead_dict['notes'] = []
            lead_dict['notes_total'] = 0
        
        try:
            assignments = db.query(CRMLeadAssignment).filter(
                CRMLeadAssignment.lead_id == lead_id
            ).order_by(CRMLeadAssignment.assigned_at.desc()).all()
            lead_dict['assignment_history'] = [a.to_dict() for a in assignments]
        except Exception as e:
            lead_dict['assignment_history'] = []
        
        try:
            editable_slots = get_editable_handler_slots(lead, current_employee, db)
            lead_dict['editable_slots'] = editable_slots
        except Exception as e:
            lead_dict['editable_slots'] = []
        
        # DC Protocol (Jan 1, 2026): Add primary owner details and RBAC
        try:
            if lead.primary_owner_type == 'staff' and lead.primary_owner_id:
                owner = db.query(StaffEmployee).filter(StaffEmployee.id == lead.primary_owner_id).first()
                if owner:
                    owner_name = owner.full_name
                    if not owner_name and owner.first_name:
                        owner_name = f"{owner.first_name} {owner.last_name or ''}".strip()
                    if not owner_name:
                        owner_name = owner.emp_code
                    lead_dict['primary_owner_name'] = owner_name
                    lead_dict['primary_owner_employee_id'] = owner.emp_code
                else:
                    lead_dict['primary_owner_name'] = None
                    lead_dict['primary_owner_employee_id'] = None
            else:
                lead_dict['primary_owner_name'] = None
                lead_dict['primary_owner_employee_id'] = None
            
            can_change, reason = can_change_primary_owner(lead, current_employee, db)
            lead_dict['can_change_owner'] = can_change
            lead_dict['owner_change_reason'] = reason
        except Exception as e:
            lead_dict['primary_owner_name'] = None
            lead_dict['primary_owner_employee_id'] = None
            lead_dict['can_change_owner'] = False
            lead_dict['owner_change_reason'] = 'error'
        
        # Coalesce first_payment_received_date with earliest transaction date if missing
        try:
            if not lead_dict.get('first_payment_received_date'):
                from app.models.crm import CRMLeadTransaction as _CLT
                _min_tx = db.query(_func.min(_CLT.transaction_date)).filter(
                    _CLT.lead_id == lead_id,
                    _CLT.transaction_date.isnot(None)
                ).scalar()
                if _min_tx:
                    lead_dict['first_payment_received_date'] = _min_tx.isoformat() if hasattr(_min_tx, 'isoformat') else str(_min_tx)
        except Exception:
            pass

        return {
            'success': True,
            'data': lead_dict
        }
    except HTTPException:
        raise
    except Exception as e:
        error_detail = f"get_lead error for lead_id={lead_id}, company_id={company_id}: {str(e)}\n{traceback.format_exc()}"
        print(f"[CRM-ERROR] {error_detail}")
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@router.put("/leads/{lead_id}")
def update_lead(
    lead_id: int,
    lead_data: LeadUpdate,
    company_id: int = Query(..., description="Company ID for DC Protocol - must match lead's current company"),
    db: Session = Depends(get_db),
    current_employee: StaffEmployee = Depends(get_current_staff_user)
):
    """Update lead details. Company change is allowed via payload."""
    from app.models.staff import StaffEmployee as SE
    from app.models.staff_accounts import OfficialPartner
    
    # DC Protocol (Jan 23, 2026): Query by lead_id only to support company change
    # The company_id query param must match the lead's CURRENT company for lookup
    lead = db.query(CRMLead).filter(CRMLead.id == lead_id).first()
    
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    # DC Protocol: Validate that the provided company_id matches lead's current company
    # VGK4U admin bypasses this check (manager-level cross-company access)
    _upd_staff_type = (current_employee.staff_type or '').upper()
    _upd_is_admin = is_vgk_admin(_upd_staff_type)
    if not _upd_is_admin and lead.company_id != company_id:
        print(f"[DC-LEAD-400] Lead {lead_id}: company mismatch — lead.company_id={lead.company_id}, request company_id={company_id}")
        raise HTTPException(
            status_code=400, 
            detail=f"Company mismatch: Lead belongs to company {lead.company_id}, but request specified company {company_id}"
        )
    
    update_data = lead_data.dict(exclude_unset=True)

    # DC-CFV-EDIT-001: confirmed_final_value is a superadmin-only override field.
    # Strip it from update_data for all callers except MR10001 and MR10025.
    # All other users cannot change this field via the update endpoint.
    if 'confirmed_final_value' in update_data:
        _cfv_caller_code = getattr(current_employee, 'emp_code', '') or ''
        _cfv_is_allowed = (
            _cfv_caller_code in ('MR10001', 'MR10025') or
            is_vgk_admin(getattr(current_employee, 'staff_type', '') or '')
        )
        if not _cfv_is_allowed:
            del update_data['confirmed_final_value']

    # DC Protocol: Guard NOT NULL deal value columns — never overwrite with None.
    # Frontend sends null for zero-value fields (gn() returns null for empty input).
    # Dropping these preserves the existing DB value instead of violating NOT NULL.
    for _nnf in ('deal_value_total', 'deal_value_received', 'deal_value_balance', 'deal_value_excl_tax'):
        if _nnf in update_data and update_data[_nnf] is None:
            del update_data[_nnf]

    # DC_CAT_COMPANY: If category is being changed, auto-derive company_id from it.
    # The category's company_id is authoritative — a category change may also move
    # the lead to the correct company without the caller needing to specify it explicitly.
    if 'category_id' in update_data and update_data['category_id'] and 'company_id' not in update_data:
        _new_resolved_company = _resolve_company_from_category(
            db, update_data['category_id'], lead.company_id
        )
        if _new_resolved_company != lead.company_id:
            update_data['company_id'] = _new_resolved_company

    # DC Protocol (Jan 1, 2026): RBAC for handler assignment changes
    # Handlers can only change their OWN field; Owner/Manager can change ALL
    editable_slots = get_editable_handler_slots(lead, current_employee, db)
    
    handler_fields_to_check = {
        'telecaller_id': 'telecaller',
        'field_staff_id': 'field_staff',
        'associated_partner_id': 'partner'
    }
    
    for field_name, slot_name in handler_fields_to_check.items():
        if field_name in update_data:
            # Check if value is actually changing
            current_value = getattr(lead, field_name)
            new_value = update_data[field_name]
            if current_value != new_value and not editable_slots.get(slot_name, False):
                # DC Protocol (Mar 25, 2026): Allow self-assignment to an EMPTY handler slot.
                # If telecaller or field_staff slot is currently NULL (unassigned) and the
                # requesting user is assigning THEMSELVES, permit it — this is a claim, not
                # a reassignment.  Assigning a third party still requires owner/manager/admin.
                is_self_claim_of_empty_slot = (
                    current_value is None
                    and new_value == current_employee.id
                    and slot_name in ('telecaller', 'field_staff')
                )
                if not is_self_claim_of_empty_slot:
                    raise HTTPException(
                        status_code=403,
                        detail=f"You don't have permission to change {slot_name.replace('_', ' ')} assignment. Only the lead owner, reporting manager, or admins can change this."
                    )
    
    # DC Protocol (Jan 1, 2026): RBAC for primary owner change
    if 'primary_owner_id' in update_data:
        current_owner_id = lead.primary_owner_id
        new_owner_id = update_data.get('primary_owner_id')
        if current_owner_id != new_owner_id:
            can_change, reason = can_change_primary_owner(lead, current_employee, db)
            if not can_change:
                raise HTTPException(
                    status_code=403, 
                    detail="You don't have permission to change the lead owner. Only the current owner, their reporting manager, or admins can transfer ownership."
                )
    
    if 'category_id' in update_data and update_data['category_id']:
        new_cat_id = int(update_data['category_id'])
        if new_cat_id != lead.category_id:
            # DC_CAT_COMPANY: Do NOT filter by company_id — categories are cross-company
            # by design. The DC_CAT_COMPANY block above (lines ~6086-6091) already
            # derives the correct company from the category. Filtering by the request's
            # company_id would incorrectly reject valid cross-company category assignments.
            category = db.query(SignupCategory).filter(
                SignupCategory.id == new_cat_id
            ).first()
            if not category:
                detail = f"[DC-LEAD-400] Lead {lead_id}: category_id={new_cat_id} not found"
                print(detail)
                raise HTTPException(status_code=400, detail="Invalid category")
    
    # Cross-company assignment allowed for telecaller (per user requirement)
    if 'telecaller_id' in update_data and update_data['telecaller_id']:
        new_tele_id = int(update_data['telecaller_id'])
        if new_tele_id != lead.telecaller_id:
            telecaller = db.query(SE).filter(SE.id == new_tele_id, SE.status == 'active').first()
            if not telecaller:
                detail = f"[DC-LEAD-400] Lead {lead_id}: telecaller_id={new_tele_id} invalid/inactive"
                print(detail)
                raise HTTPException(status_code=400, detail="Invalid or inactive telecaller")
    
    # Cross-company assignment allowed for field staff (per user requirement)
    if 'field_staff_id' in update_data and update_data['field_staff_id']:
        new_fs_id = int(update_data['field_staff_id'])
        if new_fs_id != lead.field_staff_id:
            field_staff = db.query(SE).filter(SE.id == new_fs_id, SE.status == 'active').first()
            if not field_staff:
                detail = f"[DC-LEAD-400] Lead {lead_id}: field_staff_id={new_fs_id} invalid/inactive"
                print(detail)
                raise HTTPException(status_code=400, detail="Invalid or inactive field staff")
    
    # DC Protocol Exception: Partner can be cross-company (for tagging).
    # Inactive partners are also allowed — they may still be tagged for attribution.
    if 'associated_partner_id' in update_data and update_data['associated_partner_id']:
        new_partner_id = int(update_data['associated_partner_id'])
        if new_partner_id != lead.associated_partner_id:
            partner = db.query(OfficialPartner).filter(
                OfficialPartner.id == new_partner_id
            ).first()
            if not partner:
                detail = f"[DC-LEAD-400] Lead {lead_id}: partner_id={new_partner_id} not found"
                print(detail)
                raise HTTPException(status_code=400, detail="Invalid partner")

    # DC_LIMBO_FIX: Prevent handler_type='staff' with empty/invalid handler_id (limbo lead prevention)
    # Only enforce when the update explicitly touches handler_type or handler_id
    _handler_fields_changing = 'handler_type' in update_data or 'handler_id' in update_data
    effective_handler_type = update_data.get('handler_type') if 'handler_type' in update_data else lead.handler_type
    effective_handler_id_raw = update_data.get('handler_id') if 'handler_id' in update_data else lead.handler_id
    effective_handler_id = str(effective_handler_id_raw).strip() if effective_handler_id_raw else ''
    if _handler_fields_changing and effective_handler_type == 'staff':
        if not effective_handler_id:
            raise HTTPException(
                status_code=422,
                detail="handler_id (emp_code) is required when handler_type is 'staff'. Set handler_type='unassigned' if no staff member is assigned."
            )
        # DC_LIMBO_FIX: Verify handler_id maps to a real active staff emp_code
        valid_staff = db.query(StaffEmployee).filter(
            StaffEmployee.emp_code == effective_handler_id,
            StaffEmployee.status == 'active'
        ).first()
        # DC_INT_FALLBACK: Legacy data may have stored numeric employee ID instead of emp_code.
        # Auto-convert: look up employee by integer ID and substitute their emp_code.
        if not valid_staff and effective_handler_id.isdigit():
            by_id = db.query(StaffEmployee).filter(
                StaffEmployee.id == int(effective_handler_id),
                StaffEmployee.status == 'active'
            ).first()
            if by_id:
                valid_staff = by_id
                effective_handler_id = by_id.emp_code
                print(f"[DC_INT_FALLBACK] handler_id integer → emp_code {effective_handler_id!r} for lead {lead_id} (update)", flush=True)
        if not valid_staff:
            raise HTTPException(
                status_code=422,
                detail=f"handler_id '{effective_handler_id}' is not a valid active staff emp_code. Assign a valid emp_code or use handler_type='unassigned'."
            )
        # DC_LIMBO_FIX: Normalize handler_id to trimmed canonical value for storage
        update_data['handler_id'] = effective_handler_id

    # DC Protocol (Mar 2026): Validate vendor_id (VGK Partner code) if provided
    if 'vendor_id' in update_data and update_data['vendor_id']:
        new_vendor_id = int(update_data['vendor_id'])
        if new_vendor_id != lead.vendor_id:
            vendor = db.query(VendorMaster).filter(VendorMaster.id == new_vendor_id).first()
            if not vendor:
                detail = f"[DC-LEAD-400] Lead {lead_id}: vendor_id={new_vendor_id} not found"
                print(detail)
                raise HTTPException(status_code=400, detail="Invalid partner/vendor code")

    # DC Protocol (Mar 2026): Guru auto-clear — when vendor (partner) is added/changed,
    # clear guru_id and adi_guru_id unless they are also being explicitly set in this update
    vendor_being_set = (
        'vendor_id' in update_data and update_data['vendor_id'] and
        update_data['vendor_id'] != lead.vendor_id
    )
    assoc_partner_being_set = (
        'associated_partner_id' in update_data and update_data['associated_partner_id'] and
        update_data['associated_partner_id'] != lead.associated_partner_id
    )
    if (vendor_being_set or assoc_partner_being_set):
        if 'guru_id' not in update_data:
            update_data['guru_id'] = None
        if 'z_guru_id' not in update_data:
            update_data['z_guru_id'] = None
        if 'adi_guru_id' not in update_data:
            update_data['adi_guru_id'] = None
        print(f"[DC-PARTNER] Lead {lead_id}: Partner set — guru_id, z_guru_id, adi_guru_id auto-cleared")

    # DC Protocol (Jan 1, 2026): First Contact Ownership
    # When a fresh lead (status='new') is first updated to contacted or any follow-up status,
    # the person making the update becomes the primary owner
    follow_up_statuses = ['contacted', 'interested', 'qualified', 'proposal', 'won', 'on_hold']
    new_status = update_data.get('status')
    is_first_contact = (
        lead.status == 'new' and 
        new_status in follow_up_statuses and 
        lead.primary_owner_id is None
    )
    
    if is_first_contact:
        update_data['primary_owner_type'] = 'staff'
        update_data['primary_owner_id'] = current_employee.id
        
        auto_assignment = CRMLeadAssignment(
            company_id=company_id,
            lead_id=lead_id,
            from_handler_type=lead.handler_type,
            from_handler_id=lead.handler_id,
            to_handler_type='staff',
            to_handler_id=current_employee.emp_code,
            reason=f'Tagged as Primary Owner on first contact (status: {new_status})',
            assigned_by_type='staff',
            assigned_by_id=current_employee.emp_code
        )
        db.add(auto_assignment)
    
    if 'status' in update_data:
        if update_data['status'] == 'won':
            # DC Protocol: company_id is mandatory for deal close/won (for revenue and payments integration)
            if not lead.company_id and not update_data.get('company_id'):
                raise HTTPException(
                    status_code=400, 
                    detail="Company is required to close a deal. Please select a company before marking as Won."
                )
            if not lead.actual_close_date:
                update_data['actual_close_date'] = get_indian_time()
    
    # Deal Value System: Handle 3-part deal value with auto-balance calculation
    # Priority: deal_value_total > deal_value (legacy)
    deal_total = None
    deal_received = None
    
    if 'deal_value_total' in update_data and update_data['deal_value_total'] is not None:
        deal_total = max(0, float(update_data['deal_value_total']))
        update_data['deal_value_total'] = deal_total
        # Also update legacy field for backward compatibility
        update_data['deal_value'] = deal_total
    elif 'deal_value' in update_data and update_data['deal_value'] is not None:
        # Legacy support: treat deal_value as deal_value_total
        deal_total = max(0, float(update_data['deal_value']))
        update_data['deal_value_total'] = deal_total
    
    if 'deal_value_received' in update_data and update_data['deal_value_received'] is not None:
        deal_received = max(0, float(update_data['deal_value_received']))
        update_data['deal_value_received'] = deal_received
    
    # Auto-calculate balance: total - received
    # Use existing values if not provided in update
    if deal_total is not None or deal_received is not None:
        current_total = deal_total if deal_total is not None else (lead.deal_value_total or 0)
        current_received = deal_received if deal_received is not None else (lead.deal_value_received or 0)
        # DC-DVR-AUTOBUMP-001: If received > total, raise total to match received (backend safety net).
        # Frontend already auto-bumps, but this guards against any direct API call.
        if current_received > current_total:
            print(f"[DC-DVR-AUTOBUMP-001] Lead {lead_id}: received={current_received} > total={current_total} — auto-bumping total")
            current_total = current_received
            update_data['deal_value_total'] = current_total
        update_data['deal_value_balance'] = current_total - current_received
    
    time_taken = update_data.pop('time_taken_minutes', None)

    # DC Protocol (Mar 2026): Unified Network Assignment backward-compat sync
    # When source_ref_type='mnr', also write mnr_handler_id for commission chain.
    # F6: Restrict to ONLY 'mnr' — VGK codes are not valid user.id values and
    # writing them to mnr_handler_id (FK → user.id) causes FK violation (500).
    src_type = update_data.get('source_ref_type')
    src_id = update_data.get('source_ref_id')
    if src_type == 'mnr' and src_id:
        if 'mnr_handler_id' not in update_data:
            update_data['mnr_handler_id'] = str(src_id)
    elif src_type in ('vgk', 'vgk_partner', 'partner', 'vendor', 'staff') and 'source_ref_type' in update_data:
        if 'mnr_handler_id' not in update_data:
            update_data['mnr_handler_id'] = None

    # DC-MNR-VGK-SOURCE-001: auto-set source label from ground-source type on update
    # Only overrides if caller did not explicitly supply a source value in the same request.
    if 'source_ref_type' in update_data and 'source' not in update_data:
        if src_type == 'mnr':
            update_data['source'] = 'MNR'
        elif src_type in ('vgk', 'vgk_partner'):
            update_data['source'] = 'VGK4U'
    # DC-VGK-PARTNER-SYNC-001 (May 2026): When source_ref_type is a partner role,
    # auto-mirror source_ref_id (string of partner.id) into associated_partner_id
    # (the canonical partner-attribution column). Without this, partner My-Leads
    # tab is blank AND the Solar CIBIL Advance service exits at gate-1.
    if src_type in ('partner', 'vgk_partner') and src_id:
        try:
            if 'associated_partner_id' not in update_data:
                update_data['associated_partner_id'] = int(src_id)
        except (ValueError, TypeError):
            pass
    # DC-VGK-PARTNER-SYNC-001: accept 'vgk_partner' (page-local modal) and 'partner' (unified)
    fs_type = update_data.get('field_support_ref_type')
    fs_id = update_data.get('field_support_ref_id')
    if fs_type in ('partner', 'vgk_partner') and fs_id:
        try:
            if 'vgk_field_support_id' not in update_data:
                update_data['vgk_field_support_id'] = int(fs_id)
        except (ValueError, TypeError):
            pass

    # DC-INLINE-GURU-001 backend: Auto-derive upline chain when Ground Source changes.
    # Ensures team_senior/extended/core_partner_id are persisted on save, not just shown locally.
    # DC-TEAM-CLOBBER-FIX-001 (Jul 2026): Only fire when Source actually CHANGED vs the lead's
    # current stored value. Previously this fired whenever the full Edit-Lead modal resent
    # source_ref_id/source_ref_type (which it always does on every save), silently overwriting
    # any manually-selected Senior/Extended/Core partner with the auto-derived upline chain even
    # when the user never touched Ground Source. Approved fix: Option A (compare old vs new).
    _src_id_new   = update_data.get('source_ref_id')
    _src_type_new = update_data.get('source_ref_type')
    _src_id_old   = getattr(lead, 'source_ref_id', None)
    _src_type_old = getattr(lead, 'source_ref_type', None)
    _src_changed  = (
        'source_ref_id' in update_data and 'source_ref_type' in update_data and
        (str(_src_id_new or '') != str(_src_id_old or '') or str(_src_type_new or '') != str(_src_type_old or ''))
    )
    if _src_changed:
        _gsrc_type = update_data.get('source_ref_type') or ''
        _gsrc_id   = update_data.get('source_ref_id')
        if _gsrc_type in ('vgk', 'vgk_partner', 'partner') and _gsrc_id:
            try:
                _gsp = db.query(OfficialPartner).filter(OfficialPartner.id == int(_gsrc_id)).first()
                if _gsp and _gsp.parent_partner_id:
                    update_data['team_senior_partner_id'] = _gsp.parent_partner_id
                    _sr = db.query(OfficialPartner).filter(OfficialPartner.id == _gsp.parent_partner_id).first()
                    if _sr and _sr.parent_partner_id:
                        update_data['team_extended_partner_id'] = _sr.parent_partner_id
                        _ext = db.query(OfficialPartner).filter(OfficialPartner.id == _sr.parent_partner_id).first()
                        update_data['team_core_partner_id'] = _ext.parent_partner_id if (_ext and _ext.parent_partner_id) else None
                    else:
                        update_data['team_extended_partner_id'] = None
                        update_data['team_core_partner_id'] = None
                else:
                    update_data['team_senior_partner_id'] = None
                    update_data['team_extended_partner_id'] = None
                    update_data['team_core_partner_id'] = None
            except (ValueError, TypeError):
                pass
        elif _gsrc_type == 'mnr' and _gsrc_id:
            try:
                _muser = db.query(User).filter(User.id == _gsrc_id).first()
                if _muser and _muser.referrer_id:
                    _guru = db.query(User).filter(User.id == _muser.referrer_id).first()
                    if _guru:
                        if 'guru_id'   not in update_data: update_data['guru_id']   = _guru.id
                        if 'guru_name' not in update_data: update_data['guru_name'] = _guru.name
                        if _guru.referrer_id:
                            _zguru = db.query(User).filter(User.id == _guru.referrer_id).first()
                            if _zguru:
                                if 'z_guru_id'   not in update_data: update_data['z_guru_id']   = _zguru.id
                                if 'z_guru_name' not in update_data: update_data['z_guru_name'] = _zguru.name
            except Exception:
                pass

    # DC Protocol (Apr 2026): Capture status BEFORE setattr so WhatsApp trigger
    # can compare old vs new correctly (after refresh lead.status == new_status).
    _pre_commit_status = lead.status

    # [DC-AUDIT] Capture pre-update snapshot for audit log
    _AUDIT_FIELD_MAP = {
        'status':                'status',
        'solar_pipeline_status': 'status',
        'guru_id':               'handler',
        'z_guru_id':             'handler',
        'adi_guru_id':           'handler',
        'field_support_ref_id':  'handler',
        'telecaller_id':         'handler',
        'field_staff_id':        'handler',
        'associated_partner_id': 'handler',
        'technical_id':              'handler',
        'support_staff_id':          'handler',
        'technical_staff1_id':       'handler',
        'support_staff_supported':   'confirmation',
        'technical_staff1_supported':'confirmation',
        'guru_supported':          'confirmation',
        'z_guru_supported':        'confirmation',
        'adi_guru_supported':      'confirmation',
        'core_supported':          'confirmation',
        'core_id':                 'handler',
        'core_name':               'handler',
        'showroom_supported':      'confirmation',
        'field_support_supported': 'confirmation',
        'telecaller_supported':    'confirmation',
        'technical_supported':     'confirmation',
    }
    _audit_snapshot = {}
    for _af in _AUDIT_FIELD_MAP:
        if _af in update_data:
            _audit_snapshot[_af] = getattr(lead, _af, None)

    # DC-HCI-001: snapshot partner BEFORE setattr so correction service can compare old vs new
    _pre_update_partner_id = lead.associated_partner_id

    # DC-DATE-YEAR-GUARD-001: reject date/datetime fields whose year is outside 2000-2099.
    # Prevents a data-entry typo (e.g. '62026-02-09') from being written to the DB and
    # crashing every subsequent CRM query that returns that lead (psycopg2 raises ValueError
    # when converting out-of-range years to Python datetime objects).
    _DATE_WRITE_FIELDS = (
        'submit_date', 'complete_date', 'actual_close_date', 'expected_close_date',
        'accepted_date', 'installation_date', 'material_reach_date',
        'next_followup_date', 'sanction_date', 'last_contact_date',
    )
    for _dwf in _DATE_WRITE_FIELDS:
        _dv = update_data.get(_dwf)
        if _dv is not None:
            _dv_year = getattr(_dv, 'year', None)
            if _dv_year is not None and not (2000 <= _dv_year <= 2099):
                raise HTTPException(
                    status_code=422,
                    detail=f"Invalid year {_dv_year} in field '{_dwf}'. "
                           f"Must be between 2000 and 2099."
                )

    for key, value in update_data.items():
        if hasattr(lead, key):
            setattr(lead, key, value)
    
    if time_taken and int(time_taken) >= 1:
        from app.services.activity_time_service import log_activity_time
        try:
            log_activity_time(
                db=db,
                employee_id=current_employee.id,
                source_type='lead',
                completed_minutes=int(time_taken),
                source_id=lead.id,
                source_title=lead.name or f"Lead #{lead.id}",
                description=f"Lead update: {lead.status or 'updated'}",
                created_by=current_employee.id
            )
        except Exception as e:
            print(f"[DC-WARN] Activity time log failed for lead {lead.id}: {e}")
    
    # DC_SOLAR_STAGE_DATE_001: stamp when pipeline stage changes so table can sort by it
    if 'solar_pipeline_status' in update_data:
        lead.solar_pipeline_status_updated_at = get_indian_time()

    # DC_CIBIL_ADVANCE_001: allow cibil_confirmed / cibil_score through update_data
    # (fields are on the model — setattr above handles write; hooks fire after commit)

    # DC-CIBIL-DATE-OVERRIDE-001: stamp cibil_score_updated_at whenever CIBIL data is written
    # This date is used to override submit_date for bonanza window checks when CIBIL is
    # confirmed later than the bank file submission date.
    if {'cibil_score', 'cibil_confirmed'} & set(update_data.keys()):
        lead.cibil_score_updated_at = get_indian_time()

    # DC_LOST_REENTRY: Maintain lost_at timestamp for 60-day dialer re-entry rule
    if 'status' in update_data:
        if update_data['status'] == 'lost' and not lead.lost_at:
            lead.lost_at = get_indian_time()
        elif update_data['status'] != 'lost':
            lead.lost_at = None
    # DC-TEAM-ASSIGN-001 (Jun 2026): stamp actual_close_date when status→completed
    if 'status' in update_data and update_data['status'] == 'completed' and not lead.actual_close_date:
        lead.actual_close_date = get_indian_time()

    lead.updated_at = get_indian_time()
    lead.last_contact_date = lead.updated_at

    # F1 (DC-MNR-FK-GUARD): Before commit, validate all user.id FK columns.
    # source_ref_id has NO FK constraint, so it retains stale MNR IDs even after
    # the MNR user is deleted and CASCADE has already nulled mnr_handler_id.
    # The frontend re-reads source_ref_id and resends it as mnr_handler_id, causing
    # a FK violation on commit → HTTP 500. This guard auto-nulls any invalid value.
    # DC Protocol Fix (Apr 2026): Non-user entity sources (partner/vendor/staff types)
    # are VALID references that should NEVER be cleared — they live in official_partners,
    # vendor_master, and staff_employee tables, NOT in user table. Guard only clears
    # source_ref_* when the source is a user-type (mnr/vgk) that no longer exists.
    from app.models.user import User as _MNRUser
    _non_user_source_types = ('partner', 'vgk_partner', 'vendor', 'staff', 'external')
    for _fk_col, _clear_source in (
        ('mnr_handler_id', True),
        ('guru_id', False),
        ('z_guru_id', False),
        ('adi_guru_id', False),
        ('core_id', False),
    ):
        _fk_val = getattr(lead, _fk_col, None)
        if _fk_val:
            _fk_exists = db.query(_MNRUser.id).filter(_MNRUser.id == _fk_val).first()
            if not _fk_exists:
                print(f"[DC-MNR-FK-GUARD] lead {lead_id}: {_fk_col}={_fk_val!r} not in user table — auto-nulling", flush=True)
                setattr(lead, _fk_col, None)
                if _clear_source:
                    # Only clear source_ref_* when source_ref_type is a user-type.
                    # For partner/vendor/staff sources the source_ref_* fields are the
                    # ONLY persistent storage — clearing them destroys valid attribution.
                    _src_type = lead.source_ref_type or ''
                    if _src_type.lower() not in _non_user_source_types:
                        lead.source_ref_id = None
                        lead.source_ref_type = None
                        lead.source_ref_name = None
                        print(f"[DC-MNR-FK-GUARD] lead {lead_id}: source_ref cleared (type={_src_type!r} is user-type)", flush=True)
                    else:
                        print(f"[DC-MNR-FK-GUARD] lead {lead_id}: source_ref PRESERVED (type={_src_type!r} is non-user entity)", flush=True)

    # DC Protocol (Apr 2026): Auto-create a pending transaction when lead first moves to 'won'
    # and deal_value_received > 0. Only fires if NO transactions exist yet for this lead.
    # This prevents the "₹X transaction missing" UX issue when marking a deal as won.
    if (_pre_commit_status != 'won' and lead.status == 'won' and
            lead.deal_value_received and lead.deal_value_received > 0):
        _existing_txn_count = db.query(CRMLeadTransaction).filter(
            CRMLeadTransaction.lead_id == lead_id
        ).count()
        if _existing_txn_count == 0:
            _txn_type = 'full' if (not lead.deal_value_balance or lead.deal_value_balance <= 0) else 'partial'
            _auto_txn = CRMLeadTransaction(
                company_id=company_id,
                lead_id=lead_id,
                transaction_date=get_indian_time(),
                amount=lead.deal_value_received,
                transaction_type=_txn_type,
                payment_mode='cash',
                collected_by_id=current_employee.id,
                validation_status='pending',
            )
            db.add(_auto_txn)
            print(f"[DC-AUTO-TXN] Lead {lead_id}: auto-created {_txn_type} txn ₹{lead.deal_value_received} on first won", flush=True)

    # DC Protocol (Fix C — Apr 2026): Harden commit against schema-drift 500s.
    # If a column referenced in update_data doesn't exist in the DB yet
    # (e.g. ev_b2b_stage on Neon before DC_EV_B2B_STAGE_001 ran), we catch the
    # OperationalError and return a structured 500 with a readable message
    # instead of an unhandled crash, and roll back the session cleanly.
    try:
        db.commit()
    except Exception as _commit_err:
        db.rollback()
        _commit_msg = str(_commit_err)
        print(f"[DC-LEAD-500] update_lead commit failed for lead {lead_id}: {_commit_msg}", flush=True)
        raise HTTPException(
            status_code=500,
            detail=f"Save failed due to a database error. Please contact support. (ref: lead {lead_id})"
        )
    db.refresh(lead)

    # DC-TEAM-ASSIGN-001 (Jun 2026): Trigger VGK income drafts on completion.
    # Two cases handled — both rely on generate_vgk_cash_income_drafts idempotency
    # (it skips levels that already have an entry):
    #   Case 1 — fresh completion: status just transitioned to 'completed'
    #   Case 2 — retroactive partner set: lead already completed but associated_partner_id
    #             was just assigned (e.g. Team Assignment SOURCE saved after completion)
    _income_trigger = (
        (lead.status == 'completed' and _pre_commit_status != 'completed') or
        (lead.status == 'completed' and 'associated_partner_id' in update_data and lead.associated_partner_id)
    )
    if _income_trigger and lead.associated_partner_id:
        try:
            from app.services.vgk_cash_income import generate_vgk_cash_income_drafts
            _nc = generate_vgk_cash_income_drafts(db, lead)
            if _nc:
                logger.info(f'[DC-TEAM-ASSIGN-001] Lead {lead_id}: {_nc} VGK income DRAFT(s) created (trigger: status={lead.status}, pre={_pre_commit_status}, partner={lead.associated_partner_id})')
                # DC-ADV-COMPLETION-ADJ-001 (Jul 2026): Deduct any released VSCA advance from L1
                # COMMISSION DRAFT at the moment of final completion. Called here (status→completed)
                # and in the RETRIGGER block (sps→completed) so the deduction fires regardless of
                # which trigger path creates the COMMISSION entry.
                try:
                    from app.services.vgk_solar_advance import apply_adjustment_at_completion
                    _l1e_ta = db.execute(
                        text("SELECT id FROM vgk_cash_income_entries WHERE source_lead_id=:lid AND level=1 AND status='DRAFT' ORDER BY id ASC LIMIT 1"),
                        {'lid': lead_id}
                    ).fetchone()
                    if _l1e_ta:
                        apply_adjustment_at_completion(db, lead_id, _l1e_ta.id)
                except Exception as _adj_ta_e:
                    logger.warning(f'[DC-ADV-COMPLETION-ADJ-001] ASSIGN adjustment failed lead {lead_id}: {_adj_ta_e}')
        except Exception as _ci_e:
            logger.warning(f'[DC-TEAM-ASSIGN-001] VGK income trigger failed lead {lead_id}: {_ci_e}')

    # DC-TEAM-RETRIGGER-001 (Jun 2026): Any VGK team-assignment field saved on an already-
    # completed lead retriggers income draft generation (idempotent — skips existing levels).
    # Covers: showroom slot, field support, and all upline overrides (senior/extended/core).
    # Fires only when _income_trigger is False to avoid a double-call with Case 1/2 above.
    # DC-BRP-RETRIGGER-001 (Jul 2026): Solar leads never reach status='completed' — they stay
    # at 'won' while solar_pipeline_status progresses through balance_received/subsidy_pending.
    # Extend the retrigger gate to include these solar-completion stages so team-assignment
    # edits on balance-received leads correctly regenerate missing income drafts.
    _RETRIGGER_FIELDS = {
        'showroom_vgk_id', 'vgk_field_support_id',
        'team_senior_partner_id', 'team_extended_partner_id', 'team_core_partner_id',
        'associated_partner_id', 'solar_brand_id',
        'solar_pipeline_status',   # DC-SPS-RETRIGGER-001 (Jul 2026): sps→completed via inline cell must generate income
        'status', 'deal_value_received', 'actual_close_date',
        'submit_date', 'cibil_score', 'dvr_amount',
    }
    _retrigger_hit = _RETRIGGER_FIELDS & set(update_data.keys())
    _sps_now = (getattr(lead, 'solar_pipeline_status', '') or '').lower()
    _income_eligible = (
        lead.status == 'completed'
        or _sps_now in {'balance_received', 'subsidy_pending', 'completed'}
    )
    if (
        _income_eligible
        and lead.associated_partner_id
        and not _income_trigger          # avoid double-call
        and _retrigger_hit
    ):
        try:
            from app.services.vgk_cash_income import generate_vgk_cash_income_drafts
            _tc = generate_vgk_cash_income_drafts(db, lead)
            logger.info(
                f'[DC-TEAM-RETRIGGER-001] Lead {lead_id}: {_tc} DRAFT(s) created '
                f'(changed fields: {_retrigger_hit})'
            )
            # DC-ADV-COMPLETION-ADJ-001 (Jul 2026): At sps→completed, also deduct any
            # released VSCA advance from the L1 COMMISSION DRAFT (mirrors DC-TEAM-ASSIGN-001).
            if _tc > 0 and _sps_now in ('subsidy_pending', 'completed'):
                try:
                    from app.services.vgk_solar_advance import apply_adjustment_at_completion
                    _l1e_tr = db.execute(
                        text("SELECT id FROM vgk_cash_income_entries WHERE source_lead_id=:lid AND level=1 AND status='DRAFT' ORDER BY id ASC LIMIT 1"),
                        {'lid': lead_id}
                    ).fetchone()
                    if _l1e_tr:
                        apply_adjustment_at_completion(db, lead_id, _l1e_tr.id)
                except Exception as _adj_tr_e:
                    logger.warning(f'[DC-ADV-COMPLETION-ADJ-001] RETRIGGER adjustment failed lead {lead_id}: {_adj_tr_e}')
        except Exception as _tr_e:
            logger.warning(f'[DC-TEAM-RETRIGGER-001] Retrigger failed lead {lead_id}: {_tr_e}')

    # DC-HCI-001 (Jul 2026): Handler change income correction is now natively handled
    # by DC-DEDUP-LEVEL-001 in vgk_cash_income_drafts for ALL levels (L1-L6), so
    # we no longer need to call handle_handler_change_income_correction here.

    # DC_CIBIL_ADVANCE_001: Solar CIBIL Advance lifecycle hooks (non-blocking)
    _cibil_advance_trigger_keys = {'solar_pipeline_status', 'cibil_confirmed', 'cibil_score', 'solar_brand_id'}
    if _cibil_advance_trigger_keys & set(update_data.keys()):
        try:
            from app.services.vgk_solar_advance import (
                check_and_create_advance, recover_advance, RECOVERY_STAGES
            )
            _new_stage = update_data.get('solar_pipeline_status') or getattr(lead, 'solar_pipeline_status', None) or ''
            if _new_stage in RECOVERY_STAGES:
                recover_advance(db, lead_id, reason=f'Stage changed to {_new_stage}', recovered_by_id=current_employee.id)
                # Also recover brand advances
                try:
                    from app.services.vgk_brand_incentive import recover_brand_advances as _recover_brands
                    _recover_brands(db, lead_id, reason=f'Stage changed to {_new_stage}')
                except Exception as _rb_e:
                    logger.warning(f'[VGK-BRAND-ADV] Brand recovery hook failed for lead {lead_id}: {_rb_e}')
            else:
                check_and_create_advance(db, lead_id)
                # DC-VGK-BRAND-INCENTIVE-001: brand advance (non-blocking)
                try:
                    from app.services.vgk_brand_incentive import check_and_create_brand_advance as _brand_adv
                    _bad_r = _brand_adv(db, lead_id)
                    if _bad_r.get('created'):
                        logger.info(f'[VGK-BRAND-ADV] Lead {lead_id}: brand advances created: {_bad_r.get("entry_numbers")}')
                except Exception as _ba_e:
                    logger.warning(f'[VGK-BRAND-ADV] Brand advance hook failed for lead {lead_id}: {_ba_e}')
        except Exception as _adv_e:
            logger.warning(f'[VGK-SOLAR-ADV] Advance hook failed for lead {lead_id}: {_adv_e}')

    # DC-SOLAR-DVR-ADV-20260701-001: secondary hook — fires when deal_value_received
    # is updated directly on a solar lead (separate from the primary post-income-draft hook).
    # check_and_create_dvr_advance is idempotent and checks for income entries internally.
    if 'deal_value_received' in update_data and (update_data.get('deal_value_received') or 0) > 0:
        try:
            from app.services.vgk_solar_advance import check_and_create_dvr_advance as _dvr_fn2
            _dvr2 = _dvr_fn2(db, lead_id)
            if _dvr2.get('created'):
                logger.info(f'[DVR-ADV] Secondary hook lead {lead_id}: DVR advances {_dvr2.get("entry_numbers")} created+released')
            else:
                logger.debug(f'[DVR-ADV] Secondary hook lead {lead_id}: {_dvr2.get("reason")}')
        except Exception as _dvr2_e:
            logger.warning(f'[DVR-ADV] Secondary hook failed for lead {lead_id}: {_dvr2_e}')

    # DC_CFV_001: confirmed_final_value lock + payout trigger on balance_received/subsidy_pending stage (non-blocking)
    # Fires when: solar stage hits balance_received OR subsidy_pending (money confirmed received from customer)
    # Locks confirmed_final_value = solar_value (or deal_value_received fallback) at that moment (immutable payout base).
    # DC-BRP-001 (Jun 2026): extended from {balance_received} to also cover subsidy_pending — balance is in hand.
    _CFV_SOLAR_FINALS = {'balance_received', 'subsidy_pending'}
    _new_sps     = update_data.get('solar_pipeline_status', '')  or ''
    _new_status  = update_data.get('status', '')                 or ''
    _cfv_trigger = (_new_sps in _CFV_SOLAR_FINALS)
    if _cfv_trigger:
        try:
            _dvr_now = lead.deal_value_received or 0
            _cfv_now = getattr(lead, 'confirmed_final_value', None)
            # DC-SOLAR-VALUE-001: Use solar_value as the commission base if set; fallback to deal_value_received
            _sv_now = getattr(lead, 'solar_value', None)
            _cfv_base = float(_sv_now) if (_sv_now is not None and _sv_now > 0) else float(_dvr_now)
            if _cfv_now is None and _cfv_base > 0:
                # Lock confirmed_final_value — first completion wins, immutable afterwards
                db.execute(
                    text("UPDATE crm_leads SET confirmed_final_value = :cfv WHERE id = :lid AND confirmed_final_value IS NULL"),
                    {'cfv': _cfv_base, 'lid': lead_id}
                )
                db.commit()
                db.refresh(lead)
                logger.info(f'[DC-CFV] Lead {lead_id}: confirmed_final_value locked at ₹{_cfv_base} (solar_value={_sv_now}, stage={_new_sps})')

            # Trigger VGK cash income drafts (idempotent — skips if already created)
            if lead.associated_partner_id:
                try:
                    from app.services.vgk_cash_income import generate_vgk_cash_income_drafts
                    _dc = generate_vgk_cash_income_drafts(db, lead)
                    if _dc:
                        logger.info(f'[DC-CFV] Lead {lead_id}: {_dc} VGK cash income DRAFT(s) created on completion stage')
                        # Solar CIBIL advance adjustment on L1 draft
                        try:
                            from app.services.vgk_solar_advance import apply_adjustment_at_completion
                            _l1e = db.execute(text(
                                "SELECT id FROM vgk_cash_income_entries WHERE source_lead_id=:lid AND level=1 ORDER BY id ASC LIMIT 1"
                            ), {'lid': lead_id}).fetchone()
                            if _l1e:
                                apply_adjustment_at_completion(db, lead_id, _l1e.id)
                        except Exception as _adj_e:
                            logger.warning(f'[DC-CFV] Solar advance adjustment failed for lead {lead_id}: {_adj_e}')
                        # DC-VGK-BRAND-INCENTIVE-001: brand commission entries at completion
                        try:
                            from app.services.vgk_brand_incentive import generate_brand_commission_entries as _gen_bce
                            _bce_n = _gen_bce(db, lead)
                            if _bce_n:
                                logger.info(f'[VGK-BRAND-COMM] Lead {lead_id}: {_bce_n} brand commission DRAFT(s) created')
                        except Exception as _bce_e:
                            logger.warning(f'[VGK-BRAND-COMM] Brand commission hook failed for lead {lead_id}: {_bce_e}')
                        # DC-SOLAR-DVR-ADV-20260701-001: primary DVR advance hook — fires
                        # after income drafts are confirmed (non-blocking, idempotent).
                        try:
                            from app.services.vgk_solar_advance import check_and_create_dvr_advance as _dvr_fn
                            _dvr_res = _dvr_fn(db, lead_id)
                            if _dvr_res.get('created'):
                                logger.info(f'[DVR-ADV] Lead {lead_id}: DVR advances {_dvr_res.get("entry_numbers")} created+released')
                            else:
                                logger.debug(f'[DVR-ADV] Lead {lead_id}: {_dvr_res.get("reason")}')
                        except Exception as _dvr_e:
                            logger.warning(f'[DVR-ADV] Primary hook failed for lead {lead_id}: {_dvr_e}')
                except Exception as _ci_e:
                    logger.warning(f'[DC-CFV] Cash income draft generation failed for lead {lead_id}: {_ci_e}')
        except Exception as _cfv_e:
            logger.warning(f'[DC-CFV] confirmed_final_value lock failed for lead {lead_id}: {_cfv_e}')

    # DC-INSTALL-PENDING-DVR-001 (Jul 2026): Trigger Stage-2 DVR advance when
    # solar_pipeline_status → installation_pending AND deal_value_received > 0.
    # DC-CFV only covers balance_received / subsidy_pending (CFV-lock stages).
    # installation_pending precedes balance receipt — no CFV lock, only DVR advance.
    _DVR_EXTRA_STAGES = {'installation_pending'}
    if _new_sps in _DVR_EXTRA_STAGES and lead.associated_partner_id and (lead.deal_value_received or 0) > 0:
        try:
            from app.services.vgk_solar_advance import check_and_create_dvr_advance as _dvr_fn_ip
            _dvr_ip = _dvr_fn_ip(db, lead_id)
            if _dvr_ip.get('created'):
                logger.info(
                    f'[DC-INSTALL-PENDING-DVR-001] Lead {lead_id}: '
                    f'DVR advances {_dvr_ip.get("entry_numbers")} created+released (installation_pending)'
                )
            else:
                logger.debug(f'[DC-INSTALL-PENDING-DVR-001] Lead {lead_id}: {_dvr_ip.get("reason")}')
        except Exception as _dvr_ip_e:
            logger.warning(f'[DC-INSTALL-PENDING-DVR-001] DVR hook failed for lead {lead_id}: {_dvr_ip_e}')

    # [DC-AUDIT] Write field-level audit log for changed fields
    if _audit_snapshot:
        try:
            from app.models.crm import CRMLeadAuditLog as _AuditLog
            _audit_by_name = (
                getattr(current_employee, 'full_name', None)
                or f"{getattr(current_employee,'first_name','') or ''} {getattr(current_employee,'last_name','') or ''}".strip()
                or getattr(current_employee, 'emp_code', None)
                or str(current_employee.id)
            )
            _audit_entries = []
            for _af, _cat in _AUDIT_FIELD_MAP.items():
                if _af in _audit_snapshot:
                    _old = _audit_snapshot[_af]
                    _new = getattr(lead, _af, None)
                    if str(_old if _old is not None else '') != str(_new if _new is not None else ''):
                        _audit_entries.append(_AuditLog(
                            lead_id=lead.id,
                            changed_by_type='staff',
                            changed_by_id=getattr(current_employee, 'emp_code', None) or str(current_employee.id),
                            changed_by_name=_audit_by_name,
                            field_name=_af,
                            old_value=str(_old) if _old is not None else None,
                            new_value=str(_new) if _new is not None else None,
                            change_category=_cat,
                        ))
            if _audit_entries:
                db.add_all(_audit_entries)
                db.commit()
                print(f"[DC-AUDIT] Lead {lead.id}: {len(_audit_entries)} audit entry(s) written", flush=True)
        except Exception as _audit_err:
            try: db.rollback()
            except: pass
            print(f"[DC-AUDIT] Audit write failed for lead {lead.id}: {_audit_err}", flush=True)

    # [DC-VGK-SYNC] Sync guru_supported / z_guru_supported → VGKTeamIncomeEntry.support_confirmed
    # When staff confirms or denies support for a guru/z_guru on the CRM lead,
    # mirror that decision into the matching income entry so the VGK member
    # sees the status in their My Leads → Guru / Z Guru tabs.
    _sync_fields = [
        ('guru_supported', 2),
        ('z_guru_supported', 3),
    ]
    _need_vgk_sync = _audit_snapshot and any(
        f in _audit_snapshot and str(_audit_snapshot.get(f)) != str(getattr(lead, f, None))
        for f, _ in _sync_fields
    )
    if _need_vgk_sync or (update_data and any(f in update_data for f, _ in _sync_fields)):
        try:
            from app.models.staff_accounts import VGKTeamIncomeEntry as _VTE
            import datetime as _dt
            _staff_id = str(getattr(current_employee, 'id', ''))
            for _field, _level in _sync_fields:
                _val = getattr(lead, _field, None)
                _entries = db.query(_VTE).filter(
                    _VTE.source_lead_id == lead.id,
                    _VTE.level == _level,
                ).all()
                for _ent in _entries:
                    _ent.support_confirmed = _val
                    _ent.support_confirmed_at = _dt.datetime.utcnow() if _val is not None else None
                    _ent.support_confirmed_by_id = _staff_id
                    _ent.support_confirmed_by_type = 'staff'
            db.commit()
            print(f"[DC-VGK-SYNC] Lead {lead.id}: guru_supported/z_guru_supported synced to income entries", flush=True)
        except Exception as _sync_err:
            try: db.rollback()
            except: pass
            print(f"[DC-VGK-SYNC] Sync failed for lead {lead.id}: {_sync_err}", flush=True)

    # ── WhatsApp auto-trigger on actual status change only ────────────────────
    # DC Protocol (Fix B — Apr 2026): Compare against pre-commit status,
    # not post-refresh (which always equals new_status, causing false positives).
    if new_status and new_status != _pre_commit_status:
        try:
            from app.services.whatsapp_auto_service import send_auto_whatsapp
            _wa_phone = getattr(lead, 'phone', None) or getattr(lead, 'mobile', None)
            _wa_event = f"crm_status_{new_status}"
            if _wa_phone:
                send_auto_whatsapp(
                    db=db, event_key=_wa_event, phone=_wa_phone,
                    context={
                        'name': getattr(lead, 'name', '') or getattr(lead, 'customer_name', ''),
                        'status': new_status,
                        'lead_id': lead.id,
                    },
                    lead_id=lead.id,
                    staff_id=getattr(current_employee, 'id', None),
                )
        except Exception as _wa_ex:
            print(f"[WA-AUTO] update_lead hook error: {_wa_ex}")
    # ─────────────────────────────────────────────────────────────────────────

    return {
        'success': True,
        'message': 'Lead updated successfully',
        'data': lead.to_dict()
    }


@router.post("/leads/{lead_id}/assign")
def assign_lead(
    lead_id: int,
    assignment: LeadAssign,
    company_id: int = Query(..., description="Company ID for DC Protocol"),
    db: Session = Depends(get_db),
    current_employee: StaffEmployee = Depends(get_current_staff_user)
):
    """Assign lead to handler (staff/partner/member)"""
    lead = db.query(CRMLead).filter(
        CRMLead.id == lead_id,
        CRMLead.company_id == company_id
    ).first()
    
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    valid_types = ['staff', 'partner', 'member', 'unassigned']
    if assignment.handler_type not in valid_types:
        raise HTTPException(status_code=400, detail=f"Invalid handler type. Must be one of: {valid_types}")
    
    assignment_record = CRMLeadAssignment(
        company_id=company_id,
        lead_id=lead_id,
        from_handler_type=lead.handler_type,
        from_handler_id=lead.handler_id,
        to_handler_type=assignment.handler_type,
        to_handler_id=assignment.handler_id,
        reason=assignment.reason,
        assigned_by_type='staff',
        assigned_by_id=current_employee.emp_code
    )
    db.add(assignment_record)
    
    lead.handler_type = assignment.handler_type
    lead.handler_id = assignment.handler_id
    lead.updated_at = get_indian_time()
    lead.last_contact_date = lead.updated_at
    
    db.commit()
    db.refresh(lead)
    
    return {
        'success': True,
        'message': 'Lead assigned successfully',
        'data': lead.to_dict()
    }


@router.get("/leads/{lead_id}/audit-log")
def get_lead_audit_log(
    lead_id: int,
    limit: int = Query(30, ge=1, le=100),
    db: Session = Depends(get_db),
    current_employee = Depends(get_current_staff_user)
):
    """[DC-AUDIT] Return field-level change history for a CRM lead."""
    from app.models.crm import CRMLeadAuditLog as _AL
    entries = (
        db.query(_AL)
        .filter(_AL.lead_id == lead_id)
        .order_by(_AL.changed_at.desc())
        .limit(limit)
        .all()
    )
    return {
        'success': True,
        'data': [{
            'id':               e.id,
            'lead_id':          e.lead_id,
            'changed_by_type':  e.changed_by_type,
            'changed_by_id':    e.changed_by_id,
            'changed_by_name':  e.changed_by_name,
            'field_name':       e.field_name,
            'old_value':        e.old_value,
            'new_value':        e.new_value,
            'change_category':  e.change_category,
            'changed_at':       e.changed_at.isoformat() if e.changed_at else None,
        } for e in entries]
    }


@router.post("/leads/bulk-update")
def bulk_update_leads(
    bulk_data: BulkLeadUpdate = Body(...),
    company_id: int = Query(..., description="Company ID for DC Protocol"),
    db: Session = Depends(get_db),
    current_employee: StaffEmployee = Depends(get_current_staff_user)
):
    """
    DC Protocol (Jan 28, 2026): Bulk update leads - VGK4U/EA admin only
    
    Supports:
    - Bulk reassignment with audit trail (logs previous/current owner in comments)
    - Bulk status change
    - Bulk priority change
    - Bulk category change
    - Bulk shared note addition
    
    RBAC: Only VGK4U/EA admins can perform bulk operations
    """
    from app.models.base import get_indian_time
    
    staff_type = (current_employee.staff_type or '').upper()
    # DC Protocol: Menu-based access control - page assignment = full access
    # if not is_vgk_admin(staff_type):
    #     raise HTTPException(
    #         status_code=403,
    #         detail="Bulk operations are restricted to VGK4U/EA administrators only"
    #     )
    
    if not bulk_data.lead_ids:
        raise HTTPException(status_code=400, detail="No leads selected for bulk update")
    
    if len(bulk_data.lead_ids) > 100:
        raise HTTPException(status_code=400, detail="Maximum 100 leads can be updated at once")
    
    leads = db.query(CRMLead).filter(
        CRMLead.id.in_(bulk_data.lead_ids),
        CRMLead.company_id == company_id
    ).all()
    
    if not leads:
        raise HTTPException(status_code=404, detail="No leads found matching the provided IDs")
    
    updated_count = 0
    errors = []
    now = get_indian_time()
    
    new_handler_name = None
    if bulk_data.new_handler_id:
        new_handler = db.query(StaffEmployee).filter(
            StaffEmployee.emp_code == bulk_data.new_handler_id
        ).first()
        new_handler_name = new_handler.full_name if new_handler else bulk_data.new_handler_id
    
    for lead in leads:
        try:
            changes = []
            
            if bulk_data.new_handler_id and lead.handler_id != bulk_data.new_handler_id:
                previous_handler_id = lead.handler_id
                previous_handler_name = previous_handler_id
                if previous_handler_id:
                    prev_handler = db.query(StaffEmployee).filter(
                        StaffEmployee.emp_code == previous_handler_id
                    ).first()
                    if prev_handler:
                        previous_handler_name = prev_handler.full_name
                
                assignment_record = CRMLeadAssignment(
                    company_id=company_id,
                    lead_id=lead.id,
                    from_handler_type=lead.handler_type or 'staff',
                    from_handler_id=lead.handler_id,
                    to_handler_type='staff',
                    to_handler_id=bulk_data.new_handler_id,
                    reason=f"Bulk reassignment by {current_employee.full_name}",
                    assigned_by_type='staff',
                    assigned_by_id=current_employee.emp_code
                )
                db.add(assignment_record)
                
                lead.handler_type = 'staff'
                lead.handler_id = bulk_data.new_handler_id
                # F3: Also update primary_owner_id so new handler gets full RBAC rights
                # (bulk transfer previously left primary_owner_id on the old employee)
                if new_handler:
                    lead.primary_owner_type = 'staff'
                    lead.primary_owner_id = new_handler.id
                changes.append(f"Owner changed: {previous_handler_name} → {new_handler_name}")

            # F4: If next_followup_date is in the past for transferred leads, reset to
            # next business morning so the new assignee's dialer doesn't flood with overdue
            if bulk_data.new_handler_id and lead.next_followup_date and lead.next_followup_date < now:
                from datetime import timedelta
                _reset_date = now.replace(hour=9, minute=0, second=0, microsecond=0) + timedelta(days=1)
                lead.next_followup_date = _reset_date
                changes.append(f"Follow-up date reset to {_reset_date.strftime('%d %b %Y 09:00')} (was overdue)")
            
            if bulk_data.status and lead.status != bulk_data.status:
                old_status = lead.status
                lead.status = bulk_data.status
                changes.append(f"Status: {old_status} → {bulk_data.status}")
            
            if bulk_data.priority and lead.priority != bulk_data.priority:
                old_priority = lead.priority
                lead.priority = bulk_data.priority
                changes.append(f"Priority: {old_priority} → {bulk_data.priority}")
            
            if bulk_data.category_id and lead.category_id != bulk_data.category_id:
                old_cat = lead.category.name if lead.category else 'None'
                lead.category_id = bulk_data.category_id
                new_cat = db.query(SignupCategory).filter(SignupCategory.id == bulk_data.category_id).first()
                # DC_CAT_COMPANY: Sync company_id to match new category's company
                if new_cat and new_cat.company_id and new_cat.company_id != lead.company_id:
                    lead.company_id = new_cat.company_id
                changes.append(f"Category: {old_cat} → {new_cat.name if new_cat else bulk_data.category_id}")
            
            if changes or bulk_data.note:
                note_text = ""
                if changes:
                    note_text = f"[Bulk Update] {', '.join(changes)}"
                if bulk_data.note:
                    note_text = f"{note_text}\n{bulk_data.note}" if note_text else f"[Bulk Note] {bulk_data.note}"
                
                if note_text:
                    note_entry = CRMLeadNote(
                        company_id=company_id,
                        lead_id=lead.id,
                        note=note_text.strip(),
                        created_by_type='staff',
                        created_by_id=current_employee.emp_code,
                        is_private=False
                    )
                    db.add(note_entry)
            
            lead.updated_at = now
            lead.last_contact_date = now
            updated_count += 1
            
        except Exception as e:
            errors.append({'lead_id': lead.id, 'error': str(e)})
    
    db.commit()
    
    return {
        'success': True,
        'message': f'Successfully updated {updated_count} leads',
        'data': {
            'updated_count': updated_count,
            'total_requested': len(bulk_data.lead_ids),
            'errors': errors
        }
    }


@router.post("/leads/{lead_id}/assign-handlers")
def assign_lead_handlers(
    lead_id: int,
    company_id: int = Query(..., description="Company ID for DC Protocol"),
    telecaller_id: Optional[int] = Query(None, description="Tele Caller Staff ID"),
    field_staff_id: Optional[int] = Query(None, description="Field Staff ID"),
    associated_partner_id: Optional[int] = Query(None, description="Associated Partner ID"),
    db: Session = Depends(get_db),
    current_employee: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Assign multiple handlers to a lead (Tele Caller, Field Staff, Associated Partner).
    DC Protocol: Staff handlers must belong to same company; Partner is cross-company.
    WVV Protocol: Requires staff authentication.
    
    RBAC (Granular Slot-Level Permissions):
    1. VGK/EA Admins: Can change all handler slots
    2. Primary Owner (staff): Can change all handler slots
    3. Reporting Manager: Can change all handler slots
    4. Assigned Telecaller: Can only change telecaller slot (self-reassignment)
    5. Assigned Field Staff: Can only change field_staff slot (self-reassignment)
    """
    from app.models.staff import StaffEmployee as SE
    from app.models.staff_accounts import OfficialPartner
    
    lead = db.query(CRMLead).filter(
        CRMLead.id == lead_id,
        CRMLead.company_id == company_id
    ).first()
    
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    # Calculate editable slots for current user (granular RBAC)
    editable_slots = get_editable_handler_slots(lead, current_employee, db)
    
    # Validate that user has permission for the slots they're trying to change
    if telecaller_id is not None and not editable_slots['telecaller']:
        raise HTTPException(
            status_code=403, 
            detail="You don't have permission to change the Telecaller assignment. Only the assigned telecaller, lead owner, reporting manager, or admin can modify this."
        )
    
    if field_staff_id is not None and not editable_slots['field_staff']:
        raise HTTPException(
            status_code=403, 
            detail="You don't have permission to change the Field Staff assignment. Only the assigned field staff, lead owner, reporting manager, or admin can modify this."
        )
    
    if associated_partner_id is not None and not editable_slots['partner']:
        raise HTTPException(
            status_code=403, 
            detail="You don't have permission to change the Partner assignment. Only the lead owner, reporting manager, or admin can modify this."
        )
    
    # Check that at least one slot is editable before proceeding
    if not any([editable_slots['telecaller'], editable_slots['field_staff'], editable_slots['partner']]):
        raise HTTPException(
            status_code=403, 
            detail="You don't have permission to modify any handler assignments for this lead."
        )
    
    changes = []
    
    # Cross-company assignment allowed for telecaller (per user requirement)
    if telecaller_id is not None:
        if telecaller_id == 0:
            lead.telecaller_id = None
            changes.append("Telecaller removed")
        else:
            telecaller = db.query(SE).filter(SE.id == telecaller_id, SE.status == 'active').first()
            if not telecaller:
                raise HTTPException(status_code=400, detail="Invalid or inactive telecaller")
            lead.telecaller_id = telecaller_id
            changes.append(f"Telecaller assigned: {telecaller.full_name or telecaller.emp_code}")
    
    # Cross-company assignment allowed for field staff (per user requirement)
    if field_staff_id is not None:
        if field_staff_id == 0:
            lead.field_staff_id = None
            changes.append("Field Staff removed")
        else:
            field_staff = db.query(SE).filter(SE.id == field_staff_id, SE.status == 'active').first()
            if not field_staff:
                raise HTTPException(status_code=400, detail="Invalid or inactive field staff")
            lead.field_staff_id = field_staff_id
            changes.append(f"Field Staff assigned: {field_staff.full_name or field_staff.emp_code}")
    
    # Validate and assign partner (Cross-company read allowed for tagging)
    if associated_partner_id is not None:
        if associated_partner_id == 0:
            lead.associated_partner_id = None
            changes.append("Associated Partner removed")
        else:
            partner = db.query(OfficialPartner).filter(
                OfficialPartner.id == associated_partner_id
            ).first()
            if not partner:
                raise HTTPException(status_code=400, detail="Invalid partner")
            lead.associated_partner_id = associated_partner_id
            changes.append(f"Partner assigned: {partner.partner_name}")
    
    lead.updated_at = get_indian_time()
    lead.last_contact_date = lead.updated_at
    db.commit()
    db.refresh(lead)
    
    return {
        'success': True,
        'message': 'Handlers assigned successfully',
        'changes': changes,
        'editable_slots': editable_slots,
        'data': lead.to_dict()
    }


@router.post("/leads/{lead_id}/followups")
def create_followup(
    lead_id: int,
    followup_data: FollowUpCreate,
    company_id: int = Query(..., description="Company ID for DC Protocol"),
    db: Session = Depends(get_db),
    current_employee: StaffEmployee = Depends(get_current_staff_user)
):
    """Schedule a follow-up for a lead"""
    lead = db.query(CRMLead).filter(
        CRMLead.id == lead_id,
        CRMLead.company_id == company_id
    ).first()
    
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    valid_types = ['call', 'email', 'meeting', 'site_visit', 'whatsapp', 'other']
    if followup_data.followup_type not in valid_types:
        raise HTTPException(status_code=400, detail=f"Invalid followup type. Must be one of: {valid_types}")
    
    followup = CRMLeadFollowUp(
        company_id=company_id,
        lead_id=lead_id,
        followup_type=followup_data.followup_type,
        status='scheduled',
        scheduled_date=_to_ist_naive(followup_data.scheduled_date),
        subject=followup_data.subject,
        notes=followup_data.notes,
        handler_type=lead.handler_type,
        handler_id=lead.handler_id,
        created_by_type='staff',
        created_by_id=current_employee.emp_code
    )
    
    db.add(followup)
    
    lead.next_followup_date = _to_ist_naive(followup_data.scheduled_date)
    lead.updated_at = get_indian_time()
    
    db.commit()
    db.refresh(followup)
    
    return {
        'success': True,
        'message': 'Follow-up scheduled successfully',
        'data': followup.to_dict()
    }


@router.put("/leads/{lead_id}/followups/{followup_id}")
def update_followup(
    lead_id: int,
    followup_id: int,
    followup_data: FollowUpUpdate,
    company_id: int = Query(..., description="Company ID for DC Protocol"),
    db: Session = Depends(get_db),
    current_employee: StaffEmployee = Depends(get_current_staff_user)
):
    """Update follow-up status/outcome"""
    lead = db.query(CRMLead).filter(
        CRMLead.id == lead_id,
        CRMLead.company_id == company_id
    ).first()
    
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    followup = db.query(CRMLeadFollowUp).filter(
        CRMLeadFollowUp.id == followup_id,
        CRMLeadFollowUp.lead_id == lead_id,
        CRMLeadFollowUp.company_id == company_id
    ).first()
    
    if not followup:
        raise HTTPException(status_code=404, detail="Follow-up not found")
    
    update_data = followup_data.dict(exclude_unset=True)
    
    if 'status' in update_data and update_data['status'] == 'completed':
        update_data['completed_date'] = get_indian_time()
        lead.last_contact_date = get_indian_time()
    
    for key, value in update_data.items():
        setattr(followup, key, value)
    
    followup.updated_at = get_indian_time()
    db.commit()
    db.refresh(followup)
    
    return {
        'success': True,
        'message': 'Follow-up updated successfully',
        'data': followup.to_dict()
    }


@router.get("/leads/{lead_id}/notes")
def list_lead_notes(
    lead_id: int,
    company_id: int = Query(..., description="Company ID for DC Protocol"),
    db: Session = Depends(get_db),
    current_employee: StaffEmployee = Depends(get_current_staff_user)
):
    """DC Protocol (May 2026): List notes for a lead, newest first."""
    lead = db.query(CRMLead).filter(CRMLead.id == lead_id, CRMLead.company_id == company_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    notes = db.query(CRMLeadNote).filter(
        CRMLeadNote.lead_id == lead_id,
        CRMLeadNote.company_id == company_id
    ).order_by(CRMLeadNote.created_at.desc()).all()
    return {'success': True, 'data': [n.to_dict() for n in notes]}


@router.post("/leads/{lead_id}/notes")
async def add_note(
    lead_id: int,
    note_data: NoteCreate,
    request: Request,
    company_id: int = Query(..., description="Company ID for DC Protocol"),
    db: Session = Depends(get_db)
):
    """Add note to a lead — accepts staff token, VGK token, or partner token (DC Protocol Apr 2026)"""
    from app.models.staff_accounts import OfficialPartner as _OfficialPartner
    try:
        current_user = await get_current_user_hybrid_with_partner(request, db)
    except Exception:
        raise HTTPException(status_code=401, detail="Authentication required")

    is_partner = isinstance(current_user, _OfficialPartner)
    is_staff = isinstance(current_user, StaffEmployee)

    lead = db.query(CRMLead).filter(
        CRMLead.id == lead_id,
        CRMLead.company_id == company_id
    ).first()

    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    # DC Protocol (Apr 2026): Partner can only note their own associated leads
    if is_partner:
        partner_id_str = str(current_user.id)
        owns_lead = (
            lead.associated_partner_id == current_user.id
            or (lead.created_by_type == 'partner' and lead.created_by_id == partner_id_str)
        )
        if not owns_lead:
            raise HTTPException(status_code=403, detail="You can only add notes to your own leads")
        note_author_type = 'partner'
        note_author_id = current_user.partner_code or str(current_user.id)
    elif is_staff:
        note_author_type = 'staff'
        note_author_id = current_user.emp_code
    else:
        note_author_type = 'member'
        note_author_id = str(current_user.id)

    note = CRMLeadNote(
        company_id=company_id,
        lead_id=lead_id,
        note=note_data.note,
        is_private=note_data.is_private,
        created_by_type=note_author_type,
        created_by_id=note_author_id
    )

    db.add(note)
    lead.last_contact_date = get_indian_time()
    lead.recent_comments = note_data.note  # DC-CMN-SYNC-001: keep recent_comments in sync with latest note
    db.commit()
    db.refresh(note)

    return {
        'success': True,
        'message': 'Note added successfully',
        'data': note.to_dict()
    }


@router.put("/leads/{lead_id}/notes/{note_id}")
def update_lead_note(
    lead_id: int,
    note_id: int,
    note_data: NoteCreate,
    company_id: int = Query(..., description="Company ID for DC Protocol"),
    db: Session = Depends(get_db),
    current_employee: StaffEmployee = Depends(get_current_staff_user)
):
    """DC Protocol (May 2026): Edit an existing lead note (staff only)."""
    note = db.query(CRMLeadNote).filter(
        CRMLeadNote.id == note_id,
        CRMLeadNote.lead_id == lead_id,
        CRMLeadNote.company_id == company_id
    ).first()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    note.note = note_data.note
    note.is_private = note_data.is_private
    db.commit()
    db.refresh(note)
    return {'success': True, 'message': 'Note updated', 'data': note.to_dict()}


@router.post("/leads/status-view-share")
def create_status_view_share(
    company_id: Optional[int] = Query(None),
    body: dict = Body(...),
    db: Session = Depends(get_db),
    current_employee: StaffEmployee = Depends(get_current_staff_user)
):
    """DC Protocol (May 2026): Create a 6-hour public share token for a filtered status view."""
    import secrets as _sv_secrets, json as _sv_json
    # Derive company_id from the current employee when not supplied by frontend
    if not company_id:
        company_id = getattr(current_employee, 'base_company_id', None) or 1
    lead_ids = body.get('lead_ids', [])
    filter_label = body.get('filter_label', 'Selected Leads')
    vendor_name = (body.get('vendor_name') or '').strip()
    if not lead_ids or not isinstance(lead_ids, list):
        raise HTTPException(status_code=400, detail="lead_ids list required")
    token = _sv_secrets.token_urlsafe(20)
    expires_at = get_indian_time() + timedelta(hours=6)
    # Encode vendor_name into filter_label as JSON when provided (old plain-text records stay compatible)
    filter_label_stored = _sv_json.dumps({"label": filter_label, "vendor": vendor_name}, ensure_ascii=False) if vendor_name else filter_label
    db.execute(text("""
        INSERT INTO crm_status_view_tokens
            (token, company_id, lead_ids, filter_label, expires_at, created_by_id, created_by_name, created_at)
        VALUES (:token, :company_id, :lead_ids, :filter_label, :expires_at, :created_by_id, :created_by_name, :created_at)
    """), {
        'token': token,
        'company_id': company_id,
        'lead_ids': _sv_json.dumps(lead_ids),
        'filter_label': filter_label_stored,
        'expires_at': expires_at,
        'created_by_id': current_employee.id,
        'created_by_name': current_employee.full_name or current_employee.emp_code or str(current_employee.id),
        'created_at': get_indian_time()
    })
    db.commit()
    return {'success': True, 'token': token, 'expires_at': expires_at.isoformat()}


@router.get("/leads/status-view/{token}")
def get_status_view(token: str, db: Session = Depends(get_db)):
    """DC Protocol (May 2026): Public endpoint — return leads for a status share token (no auth)."""
    import json as _sv_json2
    row = db.execute(text(
        "SELECT * FROM crm_status_view_tokens WHERE token = :t LIMIT 1"
    ), {'t': token}).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Share link not found")
    if row.expires_at < get_indian_time():
        raise HTTPException(status_code=410, detail="Share link has expired")
    lead_ids = _sv_json2.loads(row.lead_ids) if isinstance(row.lead_ids, str) else list(row.lead_ids)
    # DC Protocol (May 2026): Do NOT filter by company_id here.
    # Admin-level staff can create tokens containing leads from multiple companies
    # (e.g. Solar leads span company_id=3 and company_id=4). The token secret itself
    # (20 bytes = 160-bit entropy) is the security gate — no extra company check needed.
    leads = db.query(CRMLead).filter(
        CRMLead.id.in_(lead_ids)
    ).all()
    # Batch-resolve all User FKs (handler, guru, z_guru, adi_guru) and Staff FKs
    _sv_user_ids = list({str(i) for l in leads for i in [
        l.mnr_handler_id, l.guru_id, l.z_guru_id,
        getattr(l, 'adi_guru_id', None),
        getattr(l, 'core_id', None)
    ] if i})
    _sv_staff_ids = list({i for l in leads for i in [l.telecaller_id, l.field_staff_id] if i})
    _sv_user_name_map = {}
    _sv_staff_name_map = {}
    if _sv_user_ids:
        for u in db.query(User.id, User.name).filter(User.id.in_(_sv_user_ids)).all():
            _sv_user_name_map[str(u.id)] = u.name
    if _sv_staff_ids:
        for s in db.query(StaffEmployee.id, StaffEmployee.full_name).filter(StaffEmployee.id.in_(_sv_staff_ids)).all():
            _sv_staff_name_map[s.id] = s.full_name

    lead_dicts = []
    for lead in leads:
        # DC Protocol (May 2026): No company_id filter here — leads can span
        # multiple companies in one token (same fix as lead query above).
        # Latest 3 notes, newest first.
        notes = db.query(CRMLeadNote).filter(
            CRMLeadNote.lead_id == lead.id
        ).order_by(CRMLeadNote.created_at.desc()).limit(3).all()
        # Resolve names — stored name field takes priority, fall back to User table
        guru_name = getattr(lead, 'guru_name', None) or (_sv_user_name_map.get(str(lead.guru_id)) if lead.guru_id else None)
        z_guru_name = getattr(lead, 'z_guru_name', None) or (_sv_user_name_map.get(str(lead.z_guru_id)) if lead.z_guru_id else None)
        adi_guru_id = getattr(lead, 'adi_guru_id', None)
        adi_guru_name = _sv_user_name_map.get(str(adi_guru_id)) if adi_guru_id else None
        handler_name = _sv_user_name_map.get(str(lead.mnr_handler_id)) if lead.mnr_handler_id else None
        lead_dicts.append({
            'id': lead.id,
            'name': lead.name,
            'phone': lead.phone,
            'address': getattr(lead, 'address', None),
            'latitude': getattr(lead, 'latitude', None),
            'longitude': getattr(lead, 'longitude', None),
            'status': lead.status,
            'solar_pipeline_status': getattr(lead, 'solar_pipeline_status', None),
            'pincode': getattr(lead, 'pincode', None),
            'city': getattr(lead, 'city', None),
            'state': getattr(lead, 'state', None),
            'recent_comments': getattr(lead, 'recent_comments', None),
            'notes': [{'note': n.note, 'created_at': n.created_at.isoformat() if n.created_at else None, 'created_by_id': n.created_by_id} for n in notes],
            'guru_name': guru_name,
            'guru_supported': getattr(lead, 'guru_supported', None),
            'z_guru_name': z_guru_name,
            'z_guru_supported': getattr(lead, 'z_guru_supported', None),
            'adi_guru_name': adi_guru_name,
            'adi_guru_supported': getattr(lead, 'adi_guru_supported', None),
            'source_ref_name': getattr(lead, 'source_ref_name', None),
            'source_ref_type': getattr(lead, 'source_ref_type', None),
            'handler_name': handler_name,
            'telecaller_name': _sv_staff_name_map.get(lead.telecaller_id) if lead.telecaller_id else None,
            'telecaller_supported': getattr(lead, 'telecaller_supported', None),
            'field_staff_name': _sv_staff_name_map.get(lead.field_staff_id) if lead.field_staff_id else None,
            'showroom_supported': getattr(lead, 'showroom_supported', None),
        })
    # Parse filter_label: new records store JSON {"label":..,"vendor":..}; old records are plain text
    _raw_fl = row.filter_label or 'Solar Leads Status View'
    try:
        _fl_obj = _sv_json2.loads(_raw_fl)
        _filter_label_out = _fl_obj.get('label', _raw_fl) if isinstance(_fl_obj, dict) else _raw_fl
        _vendor_name_out = _fl_obj.get('vendor', '') if isinstance(_fl_obj, dict) else ''
    except (ValueError, TypeError):
        _filter_label_out = _raw_fl
        _vendor_name_out = ''
    return {
        'success': True,
        'filter_label': _filter_label_out,
        'vendor_name': _vendor_name_out,
        'expires_at': row.expires_at.isoformat(),
        'created_by_name': row.created_by_name,
        'data': lead_dicts
    }


@router.get("/sources")
def list_lead_sources(
    company_id: int = Query(..., description="Company ID for DC Protocol"),
    include_inactive: bool = Query(False, description="Include inactive sources"),
    db: Session = Depends(get_db),
    current_employee: StaffEmployee = Depends(get_current_staff_user)
):
    """List lead sources for company"""
    query = db.query(CRMLeadSource).filter(CRMLeadSource.company_id == company_id)
    
    if not include_inactive:
        query = query.filter(CRMLeadSource.is_active == True)
    
    sources = query.order_by(CRMLeadSource.display_order).all()
    
    return {
        'success': True,
        'data': [s.to_dict() for s in sources]
    }


@router.post("/sources/seed")
def seed_lead_sources(
    company_id: int = Query(..., description="Company ID for DC Protocol"),
    db: Session = Depends(get_db),
    current_employee: StaffEmployee = Depends(get_current_staff_user)
):
    """Seed default lead sources for company"""
    existing = db.query(CRMLeadSource).filter(
        CRMLeadSource.company_id == company_id
    ).first()
    
    if existing:
        return {
            'success': False,
            'message': 'Lead sources already exist for this company'
        }
    
    for source_data in DEFAULT_LEAD_SOURCES:
        source = CRMLeadSource(
            company_id=company_id,
            name=source_data['name'],
            description=source_data['description'],
            display_order=source_data['display_order']
        )
        db.add(source)
    
    db.commit()
    
    return {
        'success': True,
        'message': f'Seeded {len(DEFAULT_LEAD_SOURCES)} default lead sources'
    }


@router.post("/sources")
def create_lead_source(
    source_data: LeadSourceCreate,
    company_id: int = Query(..., description="Company ID for DC Protocol"),
    db: Session = Depends(get_db),
    current_employee: StaffEmployee = Depends(get_current_staff_user)
):
    """Create custom lead source"""
    existing = db.query(CRMLeadSource).filter(
        CRMLeadSource.company_id == company_id,
        CRMLeadSource.name == source_data.name
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="Lead source with this name already exists")
    
    source = CRMLeadSource(
        company_id=company_id,
        name=source_data.name,
        description=source_data.description,
        icon=source_data.icon,
        color=source_data.color,
        display_order=source_data.display_order
    )
    
    db.add(source)
    db.commit()
    db.refresh(source)
    
    return {
        'success': True,
        'message': 'Lead source created successfully',
        'data': source.to_dict()
    }


@router.put("/sources/{source_id}")
def update_lead_source(
    source_id: int,
    source_data: LeadSourceUpdate,
    company_id: int = Query(..., description="Company ID for DC Protocol"),
    db: Session = Depends(get_db),
    current_employee: StaffEmployee = Depends(get_current_staff_user)
):
    """Update a lead source"""
    source = db.query(CRMLeadSource).filter(
        CRMLeadSource.id == source_id,
        CRMLeadSource.company_id == company_id
    ).first()
    
    if not source:
        raise HTTPException(status_code=404, detail="Lead source not found")
    
    if source_data.name is not None and source_data.name != source.name:
        existing = db.query(CRMLeadSource).filter(
            CRMLeadSource.company_id == company_id,
            CRMLeadSource.name == source_data.name,
            CRMLeadSource.id != source_id
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail="Lead source with this name already exists")
        source.name = source_data.name
    
    if source_data.description is not None:
        source.description = source_data.description
    if source_data.icon is not None:
        source.icon = source_data.icon
    if source_data.color is not None:
        source.color = source_data.color
    if source_data.display_order is not None:
        source.display_order = source_data.display_order
    if source_data.is_active is not None:
        source.is_active = source_data.is_active
    
    db.commit()
    db.refresh(source)
    
    return {
        'success': True,
        'message': 'Lead source updated successfully',
        'data': source.to_dict()
    }


@router.delete("/sources/{source_id}")
def delete_lead_source(
    source_id: int,
    company_id: int = Query(..., description="Company ID for DC Protocol"),
    db: Session = Depends(get_db),
    current_employee: StaffEmployee = Depends(get_current_staff_user)
):
    """Delete a lead source (VGK-only permission)"""
    staff_type = (current_employee.staff_type or '').upper()
    # DC Protocol: Menu-based access control - page assignment = full access
    # if 'VGK' not in staff_type:
    #     raise HTTPException(
    #         status_code=403,
    #         detail="Insufficient permissions: Only VGK roles can delete lead sources"
    #     )
    
    source = db.query(CRMLeadSource).filter(
        CRMLeadSource.id == source_id,
        CRMLeadSource.company_id == company_id
    ).first()
    
    if not source:
        raise HTTPException(status_code=404, detail="Lead source not found")
    
    db.delete(source)
    db.commit()
    
    return {
        'success': True,
        'message': 'Lead source deleted successfully'
    }


@router.delete("/leads/{lead_id}")
def delete_lead(
    lead_id: int,
    company_id: int = Query(..., description="Company ID for DC Protocol"),
    db: Session = Depends(get_db),
    current_employee: StaffEmployee = Depends(get_current_staff_user)
):
    """Delete a lead (soft delete not implemented - hard delete)
    
    DC Protocol (Dec 31, 2025): VGK-only permission for delete operations
    """
    # VGK-only RBAC check
    staff_type = (current_employee.staff_type or '').upper()
    # DC Protocol: Menu-based access control - page assignment = full access
    # if 'VGK' not in staff_type:
    #     raise HTTPException(
    #         status_code=403, 
    #         detail="Insufficient permissions: Only VGK roles can delete leads"
    #     )
    
    lead = db.query(CRMLead).filter(
        CRMLead.id == lead_id,
        CRMLead.company_id == company_id
    ).first()
    
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    from app.models.staff_accounts import IncomeEntry
    linked_entries = db.query(IncomeEntry).filter(IncomeEntry.lead_id == lead_id).all()
    for entry in linked_entries:
        if entry.crm_transaction_id:
            entry.crm_transaction_id = None
        entry.lead_id = None
    if linked_entries:
        db.flush()

    db.delete(lead)
    db.commit()
    
    return {
        'success': True,
        'message': 'Lead deleted successfully'
    }


@router.get("/handlers")
def list_handlers(
    company_id: int = Query(..., description="Company ID for DC Protocol"),
    handler_type: Optional[str] = None,
    db: Session = Depends(get_db),
    current_employee: StaffEmployee = Depends(get_current_staff_user)
):
    """List available handlers for lead assignment - Cross-company allowed per user requirement"""
    handlers = []
    
    if not handler_type or handler_type == 'staff':
        # Cross-company allowed: All active staff can be assigned as handlers
        staff = db.query(StaffEmployee).filter(
            StaffEmployee.status == 'active'
        ).all()
        for s in staff:
            dept_name = s.department.name if s.department else None
            handlers.append({
                'type': 'staff',
                'id': s.emp_code,
                'name': s.full_name,
                'department': dept_name
            })
    
    return {
        'success': True,
        'data': handlers
    }


@router.get("/search-assignees")
def search_assignees(
    company_id: Optional[int] = Query(None, description="Company ID for DC Protocol (optional for partner type)"),
    assignee_type: str = Query(..., description="Type: telecaller, field_staff, or vendor"),
    q: str = Query("", description="Search query (name, code, phone)"),
    limit: int = Query(20, description="Max results"),
    db: Session = Depends(get_db),
    current_employee: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Search for assignees (Tele Caller, Field Staff, Vendor) for lead forms
    DC Protocol Exception: Cross-company assignment allowed per user requirement
    - Staff (telecaller/field_staff): All active employees searchable globally
    - Vendors: All active vendors searchable globally (VendorMaster has no company_id)
    
    Returns unified format:
    - id: Unique identifier (staff.id or vendor.id)
    - name: Display name
    - code: Employee code or vendor code
    - phone: Contact phone
    - type: 'staff' or 'vendor'
    - subtype: 'telecaller', 'field_staff', or 'vendor'
    """
    results = []
    search_term = q.strip().lower() if q else ""
    
    if assignee_type in ['telecaller', 'field_staff']:
        query = db.query(StaffEmployee).filter(
            StaffEmployee.status == 'active'
        )
        
        if search_term:
            query = query.filter(
                or_(
                    func.lower(StaffEmployee.full_name).contains(search_term),
                    func.lower(StaffEmployee.emp_code).contains(search_term),
                    StaffEmployee.phone.contains(search_term) if StaffEmployee.phone else False
                )
            )
        
        staff_list = query.order_by(StaffEmployee.full_name).limit(limit).all()
        
        for staff in staff_list:
            dept_name = staff.department.name if staff.department else ''
            results.append({
                'id': staff.id,
                'name': staff.full_name,
                'code': staff.emp_code,
                'phone': staff.phone or '',
                'department': dept_name,
                'designation': staff.designation or '',
                'type': 'staff',
                'subtype': assignee_type,
                'display': f"{staff.full_name} ({staff.emp_code})" + (f" - {dept_name}" if dept_name else "")
            })
    
    elif assignee_type == 'vendor':
        # VendorMaster is global (no company_id) - DC Protocol N/A for vendors
        query = db.query(VendorMaster).filter(
            VendorMaster.is_active == True
        )
        
        if search_term:
            query = query.filter(
                or_(
                    func.lower(VendorMaster.vendor_name).contains(search_term),
                    func.lower(VendorMaster.vendor_code).contains(search_term),
                    VendorMaster.phone.contains(search_term) if VendorMaster.phone else False
                )
            )
        
        vendor_list = query.order_by(VendorMaster.vendor_name).limit(limit).all()
        
        for vendor in vendor_list:
            results.append({
                'id': vendor.id,
                'name': vendor.vendor_name,
                'code': vendor.vendor_code,
                'phone': vendor.phone or '',
                'type': 'vendor',
                'subtype': 'vendor',
                'display': f"{vendor.vendor_name} ({vendor.vendor_code})"
            })
    
    elif assignee_type == 'partner':
        # Cross-company allowed: All active partners searchable globally
        from app.models.staff_accounts import OfficialPartner
        query = db.query(OfficialPartner).filter(
            OfficialPartner.is_active == True
        )
        
        if search_term:
            # Use coalesce to handle nullable fields safely in search
            query = query.filter(
                or_(
                    func.coalesce(func.lower(OfficialPartner.partner_name), '').contains(search_term),
                    func.lower(OfficialPartner.partner_code).contains(search_term),
                    func.coalesce(func.lower(OfficialPartner.contact_person), '').contains(search_term)
                )
            )
        
        partner_list = query.order_by(OfficialPartner.partner_name).limit(limit).all()
        
        for partner in partner_list:
            # Handle category as string (not enum)
            category = partner.category if isinstance(partner.category, str) else (partner.category.value if partner.category else '')
            # Safe fallback: partner_name → contact_person → partner_code
            display_name = partner.partner_name or partner.contact_person or partner.partner_code or f"Partner #{partner.id}"
            results.append({
                'id': partner.id,
                'name': display_name,
                'code': partner.partner_code,
                'phone': partner.phone or '',
                'type': 'partner',
                'subtype': 'partner',
                'category': category,
                'display': f"{display_name} ({partner.partner_code})" + (f" - {category}" if category else "")
            })
    
    else:
        raise HTTPException(status_code=400, detail="Invalid assignee_type. Use: telecaller, field_staff, vendor, or partner")
    
    return {
        'success': True,
        'data': results,
        'count': len(results),
        'query': q,
        'assignee_type': assignee_type
    }


@router.post("/leads/public")
def create_public_lead(
    company_id: int = Query(..., description="Company ID for DC Protocol"),
    request: dict = Body(...),
    db: Session = Depends(get_db)
):
    """
    Public endpoint for lead submission from website forms
    DC Protocol: Creates lead with company_id
    
    Security: This is a public endpoint for website inquiry forms.
    - Only allows basic lead creation (name, phone, email, notes)
    - Does not expose internal system data
    - Should be rate-limited at infrastructure level
    - Validates required fields
    """
    import re

    name          = request.get('name', '').strip()
    phone         = request.get('phone', '').strip()
    email         = (request.get('email') or '').strip() or None
    notes         = (request.get('notes') or '').strip() or None
    source        = request.get('source', 'WEBSITE')
    source_details_raw = (request.get('source_details') or '').strip() or None
    category_name = request.get('category_name', 'General Inquiry')
    category_id_raw = request.get('category_id')
    property_id   = request.get('property_id')
    property_title= request.get('property_title', '')
    looking_for   = (request.get('looking_for') or '').strip() or None
    requirements  = (request.get('requirements') or '').strip() or None
    city          = (request.get('city') or '').strip() or None
    state_val     = (request.get('state') or '').strip() or None
    area_val      = (request.get('area') or '').strip() or None
    pincode_val   = (request.get('pincode') or '').strip() or None
    budget_min    = request.get('budget_min')
    budget_max    = request.get('budget_max')
    prop_type     = (request.get('property_type') or '').strip() or None

    if not name or len(name) < 2:
        raise HTTPException(status_code=400, detail="Name is required (minimum 2 characters)")

    if not phone or len(phone) < 10:
        raise HTTPException(status_code=400, detail="Valid phone number is required")

    phone_clean = re.sub(r'[^0-9]', '', phone)
    if len(phone_clean) < 10 or len(phone_clean) > 12:
        raise HTTPException(status_code=400, detail="Invalid phone number format")

    if email:
        email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_regex, email):
            raise HTTPException(status_code=400, detail="Invalid email format")

    # Build description with property context
    desc_parts = []
    if property_title and property_id:
        desc_parts.append(f"Property Enquiry: {property_title} (ID: {property_id})")
    if prop_type:
        desc_parts.append(f"Type: {prop_type}")
    if looking_for:
        desc_parts.append(f"Looking for: {looking_for}")
    if requirements:
        desc_parts.append(f"Requirements: {requirements}")
    if notes:
        desc_parts.append(f"Message: {notes}")
    full_desc = "\n".join(desc_parts) if desc_parts else None

    try:
        bmin = float(budget_min) if budget_min is not None else None
        bmax = float(budget_max) if budget_max is not None else None
    except (ValueError, TypeError):
        bmin, bmax = None, None

    try:
        resolved_category_id = int(category_id_raw) if category_id_raw else None
    except (ValueError, TypeError):
        resolved_category_id = None

    resolved_source_details = source_details_raw or (
        f"Marketplace enquiry — {category_name}" if category_name else None
    )

    lead = CRMLead(
        company_id=company_id,
        name=name[:200],
        phone=phone_clean[:15],
        email=email[:200] if email else None,
        source=source[:100] if source else 'WEBSITE',
        priority='medium',
        status='new',
        description=full_desc[:2000] if full_desc else None,
        looking_for=looking_for[:500] if looking_for else None,
        requirements=requirements[:1000] if requirements else None,
        city=city[:100] if city else None,
        state=state_val[:100] if state_val else None,
        area=area_val[:100] if area_val else None,
        pincode=pincode_val[:10] if pincode_val else None,
        budget_min=bmin,
        budget_max=bmax,
        property_id=int(property_id) if property_id else None,
        category_id=resolved_category_id,
        source_details=resolved_source_details[:500] if resolved_source_details else None,
        phone_primary_whatsapp=True,
    )

    db.add(lead)
    db.commit()
    db.refresh(lead)

    return {
        'success': True,
        'message': 'Thank you for your inquiry. We will contact you soon.',
        'lead_id': lead.id
    }


class CreateTaskFromLead(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    additional_comments: Optional[str] = None
    due_date: Optional[datetime] = None
    priority: Optional[str] = "medium"
    assignee_id: Optional[int] = None
    details: Optional[str] = None


@router.get("/pincode/{pincode}")
def get_pincode_details(
    pincode: str,
    company_id: int = Query(..., description="Company ID for DC Protocol"),
    db: Session = Depends(get_db),
    current_employee: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Get city and state from PIN code using multiple APIs with fallback
    Primary: India Post API
    Fallback: Zippopotam.us API
    """
    import requests
    import logging
    
    logger = logging.getLogger(__name__)
    
    if not pincode or len(pincode) != 6 or not pincode.isdigit():
        raise HTTPException(status_code=400, detail="Invalid PIN code format. Must be 6 digits.")
    
    # Try India Post API first
    try:
        logger.info(f"[PINCODE] Trying India Post API for {pincode}")
        response = requests.get(
            f"https://api.postalpincode.in/pincode/{pincode}",
            timeout=10,
            headers={'User-Agent': 'Mozilla/5.0 (compatible; MyntReal/1.0)'}
        )
        logger.info(f"[PINCODE] India Post response status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            logger.info(f"[PINCODE] India Post data status: {data[0].get('Status') if data else 'No data'}")
            if data and len(data) > 0 and data[0].get('Status') == 'Success':
                post_offices = data[0].get('PostOffice', [])
                if post_offices and len(post_offices) > 0:
                    first_po = post_offices[0]
                    return {
                        'success': True,
                        'data': {
                            'pincode': pincode,
                            'area': first_po.get('Name', ''),
                            'city': first_po.get('District', ''),
                            'state': first_po.get('State', ''),
                            'region': first_po.get('Region', ''),
                            'country': 'India',
                            'post_offices': [
                                {
                                    'name': po.get('Name', ''),
                                    'branch_type': po.get('BranchType', ''),
                                    'delivery_status': po.get('DeliveryStatus', '')
                                }
                                for po in post_offices[:5]
                            ]
                        }
                    }
    except requests.RequestException as e:
        logger.warning(f"[PINCODE] India Post API failed: {str(e)}")
    
    # Try Zippopotam fallback
    try:
        logger.info(f"[PINCODE] Trying Zippopotam API for {pincode}")
        fallback_response = requests.get(
            f"https://api.zippopotam.us/in/{pincode}",
            timeout=10,
            headers={'User-Agent': 'Mozilla/5.0 (compatible; MyntReal/1.0)'}
        )
        logger.info(f"[PINCODE] Zippopotam response status: {fallback_response.status_code}")
        
        if fallback_response.status_code == 200:
            fallback_data = fallback_response.json()
            places = fallback_data.get('places', [])
            if places and len(places) > 0:
                first_place = places[0]
                return {
                    'success': True,
                    'data': {
                        'pincode': pincode,
                        'area': first_place.get('place name', ''),
                        'city': first_place.get('place name', ''),
                        'state': first_place.get('state', ''),
                        'region': '',
                        'country': 'India',
                        'post_offices': []
                    }
                }
    except requests.RequestException as e:
        logger.warning(f"[PINCODE] Zippopotam API failed: {str(e)}")
    
    logger.error(f"[PINCODE] All APIs failed for {pincode}")
    return {
        'success': False,
        'detail': f"PIN code lookup unavailable. Please enter city and state manually."
    }


@router.post("/leads/{lead_id}/create-task")
def create_task_for_lead(
    lead_id: int,
    task_data: CreateTaskFromLead,
    company_id: int = Query(..., description="Company ID for DC Protocol"),
    db: Session = Depends(get_db),
    current_employee: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Create a task for staff linked to a CRM lead
    DC Protocol: Task is created with company context
    WVV Protocol: Validates lead and staff existence
    Supports direct assignee_id or falls back to lead.depends_on_staff_id
    """
    from app.models.staff_tasks import StaffTask
    from datetime import date
    
    lead = db.query(CRMLead).filter(
        CRMLead.id == lead_id,
        CRMLead.company_id == company_id
    ).first()
    
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    assignee_staff_id = task_data.assignee_id or lead.depends_on_staff_id
    
    if not assignee_staff_id:
        raise HTTPException(status_code=400, detail="Task assignee is required. Please select a staff member.")
    
    assignee_staff = db.query(StaffEmployee).filter(
        StaffEmployee.id == assignee_staff_id
    ).first()
    
    if not assignee_staff:
        raise HTTPException(status_code=404, detail="Task assignee staff not found")
    
    import random
    import string
    task_code = 'TSK-' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
    
    title = task_data.title or f"CRM Lead Follow-up: {lead.name}"
    
    description_parts = []
    if task_data.details:
        description_parts.append(task_data.details)
    if task_data.description:
        description_parts.append(task_data.description)
    if task_data.additional_comments:
        description_parts.append(f"\n\nAdditional Comments:\n{task_data.additional_comments}")
    
    description_parts.append(f"\n\n--- Linked CRM Lead (ID: {lead.id}) ---")
    description_parts.append(f"Lead Name: {lead.name}")
    if lead.phone:
        description_parts.append(f"Phone: {lead.phone}")
    if lead.alternate_phone:
        description_parts.append(f"Alt Phone: {lead.alternate_phone}")
    if lead.email:
        description_parts.append(f"Email: {lead.email}")
    if lead.looking_for:
        description_parts.append(f"Looking For: {lead.looking_for}")
    if lead.pincode:
        description_parts.append(f"PIN: {lead.pincode}")
    
    new_task = StaffTask(
        task_code=task_code,
        title=title,
        description='\n'.join(description_parts),
        category='general',
        priority=task_data.priority or 'medium',
        status='pending',
        created_by=current_employee.id,
        original_assigner_id=current_employee.id,
        primary_assignee_id=assignee_staff_id,
        due_date=task_data.due_date.date() if task_data.due_date else None,
        tags=['crm_lead', f'lead_{lead.id}']
    )
    
    db.add(new_task)
    
    if task_data.assignee_id and task_data.assignee_id != lead.depends_on_staff_id:
        lead.depends_on_staff_id = task_data.assignee_id
    
    db.commit()
    db.refresh(new_task)
    
    return {
        'success': True,
        'message': f'Task created and assigned to {assignee_staff.full_name}',
        'data': {
            'task_id': new_task.id,
            'task_code': new_task.task_code,
            'title': new_task.title,
            'assigned_to': assignee_staff.full_name,
            'assigned_to_emp_code': assignee_staff.emp_code,
            'priority': new_task.priority,
            'due_date': new_task.due_date.isoformat() if new_task.due_date else None
        }
    }


# ============= REVENUE MANAGEMENT ENDPOINTS =============

@router.get("/revenue/list")
def list_revenue_entries(
    company_id: int = Query(..., description="Company ID for DC Protocol"),
    status: Optional[str] = Query(None, description="Filter by approval_status: draft, pending, approved, rejected"),
    lead_id: Optional[int] = Query(None, description="Filter by specific lead"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_employee: StaffEmployee = Depends(get_current_staff_user)
):
    """
    List revenue entries with filtering and pagination
    DC Protocol: Only entries for specified company
    WVV Protocol: Staff authenticated access
    RBAC: VGK/EA sees all, Finance sees pending+, Others see their own submissions
    """
    query = db.query(CRMRevenueEntry).filter(CRMRevenueEntry.company_id == company_id)
    
    staff_type = (current_employee.staff_type or '').upper()
    is_admin = is_vgk_admin(staff_type) or 'FINANCE' in staff_type or 'ACCOUNT' in staff_type
    
    # DC Protocol: Menu-based access control - page assignment = full access
    # if not is_admin:
    #     query = query.filter(
    #         or_(
    #             CRMRevenueEntry.submitted_by_id == current_employee.id,
    #             CRMRevenueEntry.handler_id == current_employee.id
    #         )
    #     )
    
    if status:
        query = query.filter(CRMRevenueEntry.approval_status == status)
    
    if lead_id:
        query = query.filter(CRMRevenueEntry.lead_id == lead_id)
    
    total = query.count()
    
    entries = query.order_by(CRMRevenueEntry.created_at.desc())\
        .offset((page - 1) * page_size)\
        .limit(page_size)\
        .all()
    
    results = []
    for entry in entries:
        entry_data = entry.to_dict()
        lead = db.query(CRMLead).filter(CRMLead.id == entry.lead_id).first()
        if lead:
            entry_data['lead_name'] = lead.name
            entry_data['lead_phone'] = lead.phone
            entry_data['lead_status'] = lead.status
            entry_data['deal_value_total'] = lead.deal_value_total
            entry_data['deal_value_received'] = lead.deal_value_received
            entry_data['deal_value_balance'] = lead.deal_value_balance
        
        if entry.submitted_by_id:
            submitter = db.query(StaffEmployee).filter(StaffEmployee.id == entry.submitted_by_id).first()
            if submitter:
                entry_data['submitted_by_name'] = submitter.full_name
        
        if entry.approved_by_id:
            approver = db.query(StaffEmployee).filter(StaffEmployee.id == entry.approved_by_id).first()
            if approver:
                entry_data['approved_by_name'] = approver.full_name
        
        results.append(entry_data)
    
    summary = {
        'total_entries': total,
        'total_amount': sum(e.amount_received or 0 for e in entries),
        'pending_count': db.query(CRMRevenueEntry).filter(
            CRMRevenueEntry.company_id == company_id,
            CRMRevenueEntry.approval_status == 'pending'
        ).count(),
        'approved_count': db.query(CRMRevenueEntry).filter(
            CRMRevenueEntry.company_id == company_id,
            CRMRevenueEntry.approval_status == 'approved'
        ).count()
    }
    
    return {
        'success': True,
        'data': results,
        'pagination': {
            'page': page,
            'page_size': page_size,
            'total': total,
            'total_pages': (total + page_size - 1) // page_size
        },
        'summary': summary
    }


@router.post("/revenue/submit")
def submit_revenue_entry(
    company_id: int = Query(..., description="Company ID for DC Protocol"),
    entry_data: RevenueEntryCreate = Body(...),
    db: Session = Depends(get_db),
    current_employee: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Submit a revenue entry for approval
    DC Protocol: Entry linked to company
    WVV Protocol: Staff submits, Finance approves
    """
    lead = db.query(CRMLead).filter(
        CRMLead.id == entry_data.lead_id,
        CRMLead.company_id == company_id
    ).first()
    
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found in this company")
    
    if lead.status != 'won':
        raise HTTPException(status_code=400, detail="Revenue entries can only be added for won leads")
    
    if entry_data.amount_received <= 0:
        raise HTTPException(status_code=400, detail="Amount received must be greater than 0")
    
    new_entry = CRMRevenueEntry(
        company_id=company_id,
        lead_id=entry_data.lead_id,
        amount_total=lead.deal_value_total,
        amount_received=entry_data.amount_received,
        amount_balance=max(0, lead.deal_value_total - lead.deal_value_received - entry_data.amount_received),
        approval_status='pending',
        submitted_by_type='staff',
        submitted_by_id=current_employee.id,
        submitted_at=get_indian_time(),
        handler_type=lead.handler_type,
        handler_id=int(lead.handler_id) if lead.handler_id and lead.handler_id.isdigit() else None,
        notes=entry_data.notes
    )
    
    db.add(new_entry)
    db.commit()
    db.refresh(new_entry)
    
    return {
        'success': True,
        'message': 'Revenue entry submitted for approval',
        'data': new_entry.to_dict()
    }


@router.patch("/revenue/{entry_id}/approve")
def approve_or_reject_revenue(
    entry_id: int,
    company_id: int = Query(..., description="Company ID for DC Protocol"),
    action_data: RevenueApprovalAction = Body(...),
    db: Session = Depends(get_db),
    current_employee: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Approve or reject a revenue entry
    DC Protocol: Entry must belong to company
    WVV Protocol: Only VGK/EA/Finance staff can approve
    Updates lead's deal_value_received and deal_value_balance on approval
    """
    staff_type = (current_employee.staff_type or '').upper()
    is_approver = is_vgk_admin(staff_type) or 'FINANCE' in staff_type or 'ACCOUNT' in staff_type
    
    # DC Protocol: Menu-based access control - page assignment = full access
    # if not is_approver:
    #     raise HTTPException(status_code=403, detail="Only Finance or Admin staff can approve revenue entries")
    
    entry = db.query(CRMRevenueEntry).filter(
        CRMRevenueEntry.id == entry_id,
        CRMRevenueEntry.company_id == company_id
    ).first()
    
    if not entry:
        raise HTTPException(status_code=404, detail="Revenue entry not found")
    
    if entry.approval_status not in ['pending', 'draft']:
        raise HTTPException(status_code=400, detail=f"Cannot process entry with status: {entry.approval_status}")
    
    action = action_data.action.lower()
    now = get_indian_time()
    
    if action == 'approve':
        entry.approval_status = 'approved'
        entry.approved_by_id = current_employee.id
        entry.approved_at = now
        
        lead = db.query(CRMLead).filter(CRMLead.id == entry.lead_id).first()
        if lead:
            lead.deal_value_received = (lead.deal_value_received or 0) + entry.amount_received
            lead.deal_value_balance = max(0, (lead.deal_value_total or 0) - lead.deal_value_received)

            # DC_CFV_001 (Apr 2026): Lock confirmed_final_value on revenue approval
            # Trigger condition: lead solar stage is balance_received
            _CFV_SOLAR_FINALS_REV = {'balance_received'}
            _sps_rev  = (getattr(lead, 'solar_pipeline_status', '') or '').lower()
            _is_final_rev = _sps_rev in _CFV_SOLAR_FINALS_REV
            _cfv_curr = getattr(lead, 'confirmed_final_value', None)
            if _is_final_rev and _cfv_curr is None:
                _sv_rev = getattr(lead, 'solar_value', None)
                _cfv_rev_base = float(_sv_rev) if (_sv_rev is not None and _sv_rev > 0) else float(lead.deal_value_received or 0)
                if _cfv_rev_base > 0:
                    lead.confirmed_final_value = _cfv_rev_base
                    logger.info(f'[DC-CFV] Lead {lead.id}: confirmed_final_value locked at ₹{_cfv_rev_base} (solar_value={_sv_rev}, revenue approval)')

            # DC Protocol (Apr 2026): VGK Cash Income trigger
            # Trigger on completion stage — no longer requires balance==0
            # (Use confirmed_final_value/deal_value_received as commission base)
            if _is_final_rev and lead.associated_partner_id:
                try:
                    from app.services.vgk_cash_income import generate_vgk_cash_income_drafts
                    drafts_created = generate_vgk_cash_income_drafts(db, lead)
                    if drafts_created:
                        logger.info(f'[VGK-CI] {drafts_created} DRAFT cash income entries created for lead {lead.id}')
                        # DC_CIBIL_ADVANCE_001: Apply ₹1,000 adjustment on L1 cash income draft
                        try:
                            from app.services.vgk_solar_advance import apply_adjustment_at_completion
                            from sqlalchemy import text as _sq_txt
                            _l1_entry = db.execute(_sq_txt("""
                                SELECT id FROM vgk_cash_income_entries
                                WHERE source_lead_id = :lid AND level = 1
                                ORDER BY id ASC LIMIT 1
                            """), {'lid': lead.id}).fetchone()
                            if _l1_entry:
                                apply_adjustment_at_completion(db, lead.id, _l1_entry.id)
                        except Exception as _adj_e:
                            logger.warning(f'[VGK-SOLAR-ADV] Adjustment hook failed for lead {lead.id}: {_adj_e}')
                except Exception as _ci_err:
                    logger.error(f'[VGK-CI] Cash income draft generation failed (non-fatal): {_ci_err}')

        message = 'Revenue entry approved and lead values updated'
        
    elif action == 'reject':
        entry.approval_status = 'rejected'
        entry.approved_by_id = current_employee.id
        entry.approved_at = now
        entry.rejection_reason = action_data.rejection_reason
        message = 'Revenue entry rejected'
        
    else:
        raise HTTPException(status_code=400, detail="Invalid action. Use 'approve' or 'reject'")
    
    db.commit()
    db.refresh(entry)
    
    return {
        'success': True,
        'message': message,
        'data': entry.to_dict()
    }


@router.get("/leads/{lead_id}/revenue")
def get_lead_revenue_status(
    lead_id: int,
    company_id: int = Query(..., description="Company ID for DC Protocol"),
    db: Session = Depends(get_db),
    current_employee: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Get revenue/finance status for a specific lead
    DC Protocol: Lead must belong to company
    Returns all revenue entries and approval status
    """
    lead = db.query(CRMLead).filter(
        CRMLead.id == lead_id,
        CRMLead.company_id == company_id
    ).first()
    
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    entries = db.query(CRMRevenueEntry).filter(
        CRMRevenueEntry.lead_id == lead_id,
        CRMRevenueEntry.company_id == company_id
    ).order_by(CRMRevenueEntry.created_at.desc()).all()
    
    entries_data = []
    for entry in entries:
        entry_dict = entry.to_dict()
        if entry.submitted_by_id:
            submitter = db.query(StaffEmployee).filter(StaffEmployee.id == entry.submitted_by_id).first()
            entry_dict['submitted_by_name'] = submitter.full_name if submitter else None
        if entry.approved_by_id:
            approver = db.query(StaffEmployee).filter(StaffEmployee.id == entry.approved_by_id).first()
            entry_dict['approved_by_name'] = approver.full_name if approver else None
        entries_data.append(entry_dict)
    
    approved_amount = sum(e.amount_received for e in entries if e.approval_status == 'approved')
    pending_amount = sum(e.amount_received for e in entries if e.approval_status == 'pending')
    
    return {
        'success': True,
        'data': {
            'lead_id': lead.id,
            'lead_name': lead.name,
            'deal_value_total': lead.deal_value_total,
            'deal_value_received': lead.deal_value_received,
            'deal_value_balance': lead.deal_value_balance,
            'approved_amount': approved_amount,
            'pending_amount': pending_amount,
            'entries': entries_data,
            'finance_status': {
                'total_entries': len(entries),
                'approved_entries': len([e for e in entries if e.approval_status == 'approved']),
                'pending_entries': len([e for e in entries if e.approval_status == 'pending']),
                'rejected_entries': len([e for e in entries if e.approval_status == 'rejected'])
            }
        }
    }


# ============= CRM REVENUE CATEGORIES (LIGHTWEIGHT, NO ACCOUNTS RBAC) =============

@router.get("/revenue-categories/all-names")
def crm_list_all_category_names(
    active_only: bool = Query(True, description="Only active categories"),
    db: Session = Depends(get_db),
    current_employee: StaffEmployee = Depends(get_current_staff_user)
):
    """DC-IE-CAT-NAME-001: Return deduplicated category names across all companies for cross-company filtering."""
    query = db.query(SignupCategory)
    if active_only:
        query = query.filter(SignupCategory.is_active == True)
    all_cats = query.order_by(SignupCategory.display_order, SignupCategory.name).all()
    seen = set()
    names = []
    for cat in all_cats:
        n = cat.name
        if n and n not in seen:
            seen.add(n)
            names.append(n)
    return {'success': True, 'names': names}


@router.get("/revenue-categories")
def crm_list_revenue_categories(
    company_id: int = Query(..., description="Company ID for DC Protocol"),
    active_only: bool = Query(True, description="Only active categories"),
    db: Session = Depends(get_db),
    current_employee: StaffEmployee = Depends(get_current_staff_user)
):
    from app.models.staff_accounts import AssociatedCompany
    query = db.query(SignupCategory).filter(SignupCategory.company_id == company_id)
    if active_only:
        query = query.filter(SignupCategory.is_active == True)
    categories = query.order_by(SignupCategory.display_order).all()

    company = db.query(AssociatedCompany).filter(AssociatedCompany.id == company_id).first()
    company_name = company.company_name if company else None

    result = []
    for cat in categories:
        d = cat.to_dict()
        d['category_name'] = cat.name
        d['category_code'] = cat.slug
        d['company_name'] = company_name
        result.append(d)

    return {'success': True, 'categories': result, 'total': len(result)}


# ============= LEAD DEALS (CROSS-SELLING) ENDPOINTS =============

@router.get("/leads/{lead_id}/deals")
def list_lead_deals(
    lead_id: int,
    company_id: int = Query(..., description="Company ID for DC Protocol"),
    db: Session = Depends(get_db),
    current_employee: StaffEmployee = Depends(get_current_staff_user)
):
    lead = db.query(CRMLead).filter(CRMLead.id == lead_id, CRMLead.company_id == company_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    deals = db.query(CRMLeadDeal).filter(CRMLeadDeal.lead_id == lead_id).order_by(CRMLeadDeal.created_at).all()

    from app.models.staff_accounts import AssociatedCompany
    cat_ids = [d.revenue_category_id for d in deals if d.revenue_category_id]
    comp_ids = [d.company_id for d in deals if d.company_id]

    cats = {}
    if cat_ids:
        for c in db.query(SignupCategory).filter(SignupCategory.id.in_(cat_ids)).all():
            cats[c.id] = {'name': c.name, 'code': c.slug}
    comps = {}
    if comp_ids:
        for c in db.query(AssociatedCompany).filter(AssociatedCompany.id.in_(comp_ids)).all():
            comps[c.id] = {'name': c.company_name, 'code': c.company_code}

    result = []
    for d in deals:
        dd = d.to_dict()
        cat_info = cats.get(d.revenue_category_id, {})
        comp_info = comps.get(d.company_id, {})
        dd['category_name'] = cat_info.get('name')
        dd['category_code'] = cat_info.get('code')
        dd['company_name'] = comp_info.get('name')
        dd['company_code'] = comp_info.get('code')
        result.append(dd)

    return {'success': True, 'deals': result, 'total': len(result)}


def _get_indian_fy_start(ref_date=None):
    from datetime import date
    if ref_date is None:
        ref_date = get_indian_time().date() if hasattr(get_indian_time(), 'date') else get_indian_time()
    if hasattr(ref_date, 'date'):
        ref_date = ref_date.date()
    if ref_date.month >= 4:
        return date(ref_date.year, 4, 1)
    else:
        return date(ref_date.year - 1, 4, 1)


def _generate_deal_code(db, deal_company_id: int, revenue_category_id: int, created_at=None):
    from app.models.staff_accounts import AssociatedCompany
    from sqlalchemy import func

    company = db.query(AssociatedCompany).filter(AssociatedCompany.id == deal_company_id).first()
    category = db.query(SignupCategory).filter(SignupCategory.id == revenue_category_id).first()

    company_prefix = company.company_code if company else 'UNK'
    cat_code = (category.slug[:2] if category and category.slug else 'XX').upper()

    now = created_at or get_indian_time()
    if hasattr(now, 'strftime'):
        mmyy = now.strftime('%m%y')
    else:
        mmyy = '0000'

    fy_start = _get_indian_fy_start(now)

    max_seq = db.query(func.max(CRMLeadDeal.deal_fy_seq)).filter(
        CRMLeadDeal.company_id == deal_company_id,
        CRMLeadDeal.created_at >= fy_start
    ).scalar() or 0

    next_seq = max_seq + 1
    deal_code = f"{company_prefix}-{cat_code}-{mmyy}-{next_seq:04d}"

    return deal_code, next_seq


@router.post("/leads/{lead_id}/deals")
def create_lead_deal(
    lead_id: int,
    company_id: int = Query(..., description="Company ID for DC Protocol"),
    deal_data: dict = Body(...),
    db: Session = Depends(get_db),
    current_employee: StaffEmployee = Depends(get_current_staff_user)
):
    lead = db.query(CRMLead).filter(CRMLead.id == lead_id, CRMLead.company_id == company_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    revenue_category_id = deal_data.get('revenue_category_id')
    if not revenue_category_id:
        raise HTTPException(status_code=400, detail="Revenue category is required")

    deal_company_id = deal_data.get('company_id', company_id)

    # DC Protocol (Mar 25, 2026): Removed duplicate-category block.
    # A lead may have multiple active deals in the same category (repeat purchases, renewals, etc.).

    deal_code, fy_seq = _generate_deal_code(db, deal_company_id, revenue_category_id)

    deal_date_val = deal_data.get('deal_date')
    if deal_date_val:
        from datetime import datetime as dt_parse
        if isinstance(deal_date_val, str):
            try:
                deal_date_val = dt_parse.fromisoformat(deal_date_val.replace('Z', '+00:00'))
            except Exception:
                deal_date_val = None

    def _parse_dt(val):
        if not val:
            return None
        from datetime import datetime as _dt
        if isinstance(val, str):
            try:
                return _dt.fromisoformat(val.replace('Z', '+00:00'))
            except Exception:
                return None
        return val

    _dvt = deal_data.get('deal_value_total', 0) or 0
    _tax_rate = float(deal_data.get('deal_tax_rate', 0) or 0)
    _dvexcl = round(_dvt / (1 + _tax_rate / 100), 2) if _tax_rate > 0 else _dvt

    deal = CRMLeadDeal(
        lead_id=lead_id,
        company_id=deal_company_id,
        revenue_category_id=revenue_category_id,
        deal_code=deal_code,
        deal_fy_seq=fy_seq,
        deal_date=deal_date_val,
        deal_value_total=_dvt,
        deal_value_excl_tax=_dvexcl,
        deal_tax_rate=_tax_rate,
        deal_value_received=deal_data.get('deal_value_received', 0),
        deal_value_balance=max(0, _dvt - (deal_data.get('deal_value_received', 0) or 0)),
        status='active',
        notes=deal_data.get('notes'),
        deal_source_id=deal_data.get('deal_source_id') or None,
        deal_referrer_id=deal_data.get('deal_referrer_id') or None,
        deal_field_support_id=deal_data.get('deal_field_support_id') or None,
        start_date=_parse_dt(deal_data.get('start_date')),
        close_date=_parse_dt(deal_data.get('close_date')),
        created_by_id=current_employee.id
    )
    db.add(deal)
    db.commit()
    db.refresh(deal)

    _update_lead_aggregate_deal_values(db, lead_id)
    db.commit()

    return {'success': True, 'message': 'Deal created', 'deal': deal.to_dict()}


@router.put("/deals/{deal_id}")
def update_lead_deal(
    deal_id: int,
    company_id: int = Query(..., description="Company ID for DC Protocol"),
    deal_data: dict = Body(...),
    db: Session = Depends(get_db),
    current_employee: StaffEmployee = Depends(get_current_staff_user)
):
    deal = db.query(CRMLeadDeal).filter(CRMLeadDeal.id == deal_id).first()
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")

    lead = db.query(CRMLead).filter(CRMLead.id == deal.lead_id, CRMLead.company_id == company_id).first()
    if not lead:
        raise HTTPException(status_code=403, detail="Deal does not belong to this company")

    if 'deal_tax_rate' in deal_data:
        deal.deal_tax_rate = float(deal_data['deal_tax_rate'] or 0)
    if 'deal_value_total' in deal_data:
        deal.deal_value_total = deal_data['deal_value_total']
        _tr = float(deal.deal_tax_rate or 0)
        deal.deal_value_excl_tax = round(deal.deal_value_total / (1 + _tr / 100), 2) if _tr > 0 else deal.deal_value_total
    if 'deal_value_received' in deal_data:
        deal.deal_value_received = deal_data['deal_value_received']
    if 'status' in deal_data:
        deal.status = deal_data['status']
    if 'company_id' in deal_data:
        deal.company_id = deal_data['company_id']
    if 'revenue_category_id' in deal_data:
        deal.revenue_category_id = deal_data['revenue_category_id']
    if 'deal_date' in deal_data:
        deal_date_val = deal_data['deal_date']
        if deal_date_val:
            from datetime import datetime as dt_parse
            if isinstance(deal_date_val, str):
                try:
                    deal_date_val = dt_parse.fromisoformat(deal_date_val.replace('Z', '+00:00'))
                except Exception:
                    deal_date_val = None
        deal.deal_date = deal_date_val
    if 'notes' in deal_data:
        deal.notes = deal_data['notes']
    if 'deal_source_id' in deal_data:
        deal.deal_source_id = deal_data['deal_source_id'] or None
    if 'deal_referrer_id' in deal_data:
        deal.deal_referrer_id = deal_data['deal_referrer_id'] or None
    if 'deal_field_support_id' in deal_data:
        deal.deal_field_support_id = deal_data['deal_field_support_id'] or None
    if 'start_date' in deal_data:
        sv = deal_data['start_date']
        if sv:
            from datetime import datetime as _dtp
            try:
                deal.start_date = _dtp.fromisoformat(str(sv).replace('Z', '+00:00'))
            except Exception:
                pass
        else:
            deal.start_date = None
    if 'close_date' in deal_data:
        cv = deal_data['close_date']
        if cv:
            from datetime import datetime as _dtp
            try:
                deal.close_date = _dtp.fromisoformat(str(cv).replace('Z', '+00:00'))
            except Exception:
                pass
        else:
            deal.close_date = None
    deal.deal_value_balance = max(0, (deal.deal_value_total or 0) - (deal.deal_value_received or 0))

    db.commit()
    db.refresh(deal)

    _update_lead_aggregate_deal_values(db, deal.lead_id)
    db.commit()

    return {'success': True, 'message': 'Deal updated', 'deal': deal.to_dict()}


def _update_lead_aggregate_deal_values(db, lead_id):
    deals = db.query(CRMLeadDeal).filter(CRMLeadDeal.lead_id == lead_id, CRMLeadDeal.status == 'active').all()
    lead = db.query(CRMLead).filter(CRMLead.id == lead_id).first()
    if lead:
        lead.deal_value_total = sum(d.deal_value_total or 0 for d in deals)
        lead.deal_value_excl_tax = sum(d.deal_value_excl_tax or d.deal_value_total or 0 for d in deals)
        # DC-DEAL-AGG-001 (Jun 2026): derive received from validated transactions — source of truth.
        # Previously used sum(d.deal_value_received) which was always 0 (deals were never updated
        # from transactions), silently resetting lead received to ₹0 on every deal edit.
        _agg_validated_sum = db.query(
            func.coalesce(func.sum(CRMLeadTransaction.amount), 0)
        ).filter(
            CRMLeadTransaction.lead_id == lead_id,
            CRMLeadTransaction.validation_status == 'validated'
        ).scalar() or 0
        lead.deal_value_received = _agg_validated_sum
        lead.deal_value_balance = max(0, lead.deal_value_total - lead.deal_value_received)
        if deals:
            lead.deal_tax_rate = deals[0].deal_tax_rate or 0
        # DC-DEAL-PER-DEAL-RECV-001 (Jul 2026): update per-deal received/balance from validated
        # transactions linked to each deal via deal_id. Transactions without a deal_id are
        # attributed to the lead aggregate only (not to any specific deal).
        for d in deals:
            _deal_recv = db.query(
                func.coalesce(func.sum(CRMLeadTransaction.amount), 0)
            ).filter(
                CRMLeadTransaction.deal_id == d.id,
                CRMLeadTransaction.validation_status == 'validated'
            ).scalar() or 0
            d.deal_value_received = _deal_recv
            d.deal_value_balance = max(0, (d.deal_value_total or 0) - _deal_recv)


# ============= MY-DEALS (member/partner portal) =============

@router.get("/my-deals")
async def get_my_deals(
    request: Request,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    DC Protocol: Returns CRM deals credited to the calling MNR member.
    Matches any of the 3 credit fields (deal_source_id, deal_referrer_id, deal_field_support_id)
    against the caller's MNR ID or VGK partner code.
    Auth: MNR user token (hybrid) or staff token.
    """
    from app.core.security import get_current_mnr_user_from_hybrid, get_current_user_hybrid
    try:
        current_user = await get_current_mnr_user_from_hybrid(request, db)
        credit_id = getattr(current_user, 'mnr_id', None) or getattr(current_user, 'id', None)
        if credit_id:
            credit_id = str(credit_id)
    except Exception:
        try:
            current_user = await get_current_user_hybrid(request, db)
            credit_id = getattr(current_user, 'emp_code', None) or str(getattr(current_user, 'id', ''))
        except Exception:
            raise HTTPException(status_code=401, detail="Authentication required")

    if not credit_id:
        raise HTTPException(status_code=401, detail="Unable to resolve caller identity")

    from sqlalchemy import or_
    query = db.query(CRMLeadDeal).filter(
        or_(
            CRMLeadDeal.deal_source_id == credit_id,
            CRMLeadDeal.deal_referrer_id == credit_id,
            CRMLeadDeal.deal_field_support_id == credit_id
        )
    )
    if status:
        query = query.filter(CRMLeadDeal.status == status)

    total = query.count()
    deals = query.order_by(CRMLeadDeal.created_at.desc()).offset((page - 1) * per_page).limit(per_page).all()

    from app.models.staff_accounts import AssociatedCompany
    from app.models.signup_category import SignupCategory as SC
    cat_ids = list({d.revenue_category_id for d in deals if d.revenue_category_id})
    lead_ids = list({d.lead_id for d in deals})
    cats = {c.id: c.name for c in db.query(SC).filter(SC.id.in_(cat_ids)).all()} if cat_ids else {}
    leads_map = {l.id: l for l in db.query(CRMLead).filter(CRMLead.id.in_(lead_ids)).all()} if lead_ids else {}

    result = []
    for d in deals:
        dd = d.to_dict()
        dd['category_name'] = cats.get(d.revenue_category_id)
        lead = leads_map.get(d.lead_id)
        dd['lead_name'] = lead.name if lead else None
        dd['lead_phone'] = lead.phone if lead else None
        credit_role = []
        if d.deal_source_id == credit_id:
            credit_role.append('Source')
        if d.deal_referrer_id == credit_id:
            credit_role.append('Referrer')
        if d.deal_field_support_id == credit_id:
            credit_role.append('Field Support')
        dd['credit_role'] = ', '.join(credit_role)
        result.append(dd)

    return {
        'success': True,
        'data': result,
        'total': total,
        'page': page,
        'per_page': per_page,
        'pages': (total + per_page - 1) // per_page if per_page else 1
    }


# ============= CRM → SFMS AUTO-SYNC HELPER =============

PAYMENT_MODE_MAP = {
    'cash': 'CASH',
    'upi': 'UPI',
    'neft': 'NEFT',
    'rtgs': 'RTGS',
    'cheque': 'CHEQUE',
    'bank': 'BANK',
    'card': 'CARD',
    'dd': 'DD',
}

def _auto_create_income_entry_from_txn(db, txn, lead, current_employee, payment_type=None):
    from app.models.staff_accounts import IncomeEntry, IncomeSourceType, AssociatedCompany
    from app.services.staff_accounts_service import IncomeEntryService

    if getattr(txn, 'income_entry_id', None):
        return {"success": False, "message": "Income entry already linked to this transaction"}

    existing = db.query(IncomeEntry).filter(IncomeEntry.crm_transaction_id == txn.id).first()
    if existing:
        return {"success": False, "message": "Income entry already exists for this transaction"}

    income_source = db.query(IncomeSourceType).filter(
        IncomeSourceType.is_active == True
    ).first()

    if not income_source:
        logger.warning("[DC-CRM-SFMS] No active income source type found. "
                       "Transaction #%s for lead #%s will NOT be synced to SFMS income ledger. "
                       "Configure an active income source in SFMS.",
                       getattr(txn, 'id', '?'), getattr(txn, 'lead_id', '?'))
        return {"success": False, "message": "No active income source found — SFMS sync skipped"}

    sfms_mode = PAYMENT_MODE_MAP.get((txn.payment_mode or 'cash').lower(), 'CASH')

    entry_number = IncomeEntryService._generate_entry_number(db, txn.company_id)

    payer_name = None
    payer_city = None
    payer_state = None
    lead_owner_id = None
    if lead:
        payer_name = getattr(lead, 'name', None) or f"Lead #{lead.id}"
        payer_city = getattr(lead, 'city', None)
        payer_state = getattr(lead, 'state', None)
        lead_owner_id = getattr(lead, 'primary_owner_id', None) or getattr(lead, 'telecaller_id', None) or getattr(lead, 'field_staff_id', None)

    txn_date = txn.transaction_date.date() if hasattr(txn.transaction_date, 'date') else txn.transaction_date

    new_entry = IncomeEntry(
        entry_number=entry_number,
        company_id=txn.company_id,
        income_source_id=income_source.id,
        revenue_category_id=getattr(txn, 'revenue_category_id', None),
        crm_transaction_id=txn.id,
        income_date=txn_date,
        amount=txn.amount,
        transaction_type=getattr(txn, 'transaction_type', None),
        payment_mode=sfms_mode,
        payment_type=payment_type.upper() if payment_type else None,
        payment_reference=txn.reference_number,
        payment_date=txn_date,
        payer_name=payer_name,
        payer_city=payer_city,
        payer_state=payer_state,
        narration=f"CRM Auto-Sync: Lead #{txn.lead_id} | Txn #{txn.id} | {txn.notes or ''}".strip(),
        status='PENDING',
        lead_id=txn.lead_id,
        lead_owner_id=lead_owner_id,
        collected_by_id=getattr(txn, 'collected_by_id', None),
        created_by_id=current_employee.id
    )
    db.add(new_entry)

    txn.income_entry_id = None
    db.flush()

    txn.income_entry_id = new_entry.id
    db.flush()

    logger.info("[DC-CRM-SFMS] Auto-created income entry %s for CRM txn #%s, amount ₹%s",
                entry_number, txn.id, txn.amount)
    return {"success": True, "entry_number": entry_number, "income_entry_id": new_entry.id}


# ============= TRANSACTION MANAGEMENT ENDPOINTS =============

@router.get("/transactions/types")
def get_transaction_types():
    """Get available transaction types and payment modes"""
    return {
        'success': True,
        'transaction_types': TRANSACTION_TYPES,
        'payment_modes': PAYMENT_MODES
    }


@router.get("/leads/{lead_id}/transactions")
def get_lead_transactions(
    lead_id: int,
    company_id: int = Query(..., description="Company ID for DC Protocol"),
    db: Session = Depends(get_db),
    current_employee: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Get all transactions for a specific lead
    DC Protocol: Lead must belong to company
    Returns transaction list with collector details and validation status
    """
    lead = db.query(CRMLead).filter(
        CRMLead.id == lead_id,
        CRMLead.company_id == company_id
    ).first()
    
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    transactions = db.query(CRMLeadTransaction).filter(
        CRMLeadTransaction.lead_id == lead_id,
        CRMLeadTransaction.company_id == company_id
    ).order_by(CRMLeadTransaction.transaction_date.desc()).all()
    
    results = []
    for txn in transactions:
        txn_data = txn.to_dict()
        if txn.collected_by_id:
            collector = db.query(StaffEmployee).filter(StaffEmployee.id == txn.collected_by_id).first()
            txn_data['collected_by_name'] = collector.full_name if collector else None
        if txn.validated_by_id:
            validator = db.query(StaffEmployee).filter(StaffEmployee.id == txn.validated_by_id).first()
            txn_data['validated_by_name'] = validator.full_name if validator else None
        if txn.created_by_id:
            creator = db.query(StaffEmployee).filter(StaffEmployee.id == txn.created_by_id).first()
            txn_data['created_by_name'] = creator.full_name if creator else None
        results.append(txn_data)
    
    validated_total = sum(t.amount for t in transactions if t.validation_status == 'validated')
    pending_total = sum(t.amount for t in transactions if t.validation_status == 'pending')
    
    return {
        'success': True,
        'data': {
            'transactions': results,
            'summary': {
                'total_transactions': len(transactions),
                'validated_amount': validated_total,
                'pending_amount': pending_total,
                'total_amount': sum(t.amount for t in transactions)
            }
        }
    }


@router.post("/leads/{lead_id}/transactions")
def create_transaction(
    lead_id: int,
    company_id: int = Query(..., description="Company ID for DC Protocol"),
    txn_data: TransactionCreate = Body(...),
    db: Session = Depends(get_db),
    current_employee: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Create a new transaction for a lead
    DC Protocol: Transaction linked to company
    WVV Protocol: Staff authenticated
    """
    lead = db.query(CRMLead).filter(
        CRMLead.id == lead_id,
        CRMLead.company_id == company_id
    ).first()
    
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    if txn_data.amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be greater than 0")
    
    new_txn = CRMLeadTransaction(
        company_id=company_id,
        lead_id=lead_id,
        transaction_date=txn_data.transaction_date,
        amount=txn_data.amount,
        transaction_type=txn_data.transaction_type,
        payment_mode=txn_data.payment_mode,
        collected_by_id=txn_data.collected_by_id or current_employee.id,
        reference_number=txn_data.reference_number,
        notes=txn_data.notes,
        receipt_filename=txn_data.receipt_filename,
        revenue_category_id=txn_data.revenue_category_id,
        deal_id=txn_data.deal_id,
        validation_status='pending',
        created_by_id=current_employee.id
    )
    
    try:
        db.add(new_txn)
        db.commit()
        db.refresh(new_txn)
    except Exception as e:
        db.rollback()
        logger.error("[DC-CRM-TXN] Transaction INSERT failed for lead #%s: %s", lead_id, e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to save transaction: {str(e)}")

    income_entry_result = None
    try:
        income_entry_result = _auto_create_income_entry_from_txn(
            db, new_txn, lead, current_employee,
            payment_type=txn_data.payment_type
        )
        db.commit()
        db.refresh(new_txn)
    except Exception as e:
        logger.warning("[DC-CRM-SFMS] Income entry creation failed for txn #%s: %s. "
                       "Transaction is committed — SFMS sync gap created. "
                       "Income entry can be manually created in SFMS.", new_txn.id, e)
        db.rollback()
        db.refresh(new_txn)
        income_entry_result = {"success": False, "message": str(e)}

    txn_dict = new_txn.to_dict()
    
    message = 'Transaction recorded successfully'
    if income_entry_result and income_entry_result.get("success"):
        message += f' | Income entry #{income_entry_result.get("entry_number")} auto-created'
    
    return {
        'success': True,
        'message': message,
        'data': txn_dict
    }


@router.put("/transactions/{txn_id}")
def update_transaction(
    txn_id: int,
    company_id: int = Query(..., description="Company ID for DC Protocol"),
    txn_data: dict = Body(...),
    db: Session = Depends(get_db),
    current_employee: StaffEmployee = Depends(get_current_staff_user)
):
    txn = db.query(CRMLeadTransaction).filter(
        CRMLeadTransaction.id == txn_id,
        CRMLeadTransaction.company_id == company_id
    ).first()
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")

    if txn.validation_status == 'validated':
        raise HTTPException(status_code=400, detail="Cannot edit a validated transaction")

    if 'transaction_date' in txn_data and txn_data['transaction_date']:
        from datetime import datetime as dt_parse
        td = txn_data['transaction_date']
        if isinstance(td, str):
            try:
                td = dt_parse.fromisoformat(td.replace('Z', '+00:00'))
            except Exception:
                td = None
        if td:
            txn.transaction_date = td
    if 'amount' in txn_data and txn_data['amount']:
        new_amount = float(txn_data['amount'])
        if new_amount <= 0:
            raise HTTPException(status_code=400, detail="Amount must be greater than 0")
        txn.amount = new_amount
    if 'transaction_type' in txn_data:
        txn.transaction_type = txn_data['transaction_type']
    if 'payment_mode' in txn_data:
        txn.payment_mode = txn_data['payment_mode']
    if 'reference_number' in txn_data:
        txn.reference_number = txn_data['reference_number']
    if 'notes' in txn_data:
        txn.notes = txn_data['notes']
    if 'deal_id' in txn_data:
        txn.deal_id = txn_data['deal_id'] or None
        if txn.deal_id:
            selected_deal = db.query(CRMLeadDeal).filter(CRMLeadDeal.id == txn.deal_id).first()
            if selected_deal:
                txn.revenue_category_id = selected_deal.revenue_category_id

    db.commit()
    db.refresh(txn)

    return {'success': True, 'message': 'Transaction updated', 'data': txn.to_dict()}


@router.post("/transactions/{txn_id}/upload-receipt")
async def upload_transaction_receipt(
    txn_id: int,
    company_id: int = Query(..., description="Company ID for DC Protocol"),
    receipt: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_employee: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Upload payment receipt for a CRM transaction.
    DC Protocol: Transaction must belong to the company.
    Universal Upload: max 5MB, images and PDF only.
    """
    txn = db.query(CRMLeadTransaction).filter(
        CRMLeadTransaction.id == txn_id,
        CRMLeadTransaction.company_id == company_id
    ).first()
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")

    if txn.validation_status == 'validated':
        raise HTTPException(status_code=400, detail="Cannot update a validated transaction")

    file_content = await receipt.read()
    file_size = len(file_content)

    if file_size == 0:
        raise HTTPException(status_code=400, detail="File is empty")

    MAX_RECEIPT_SIZE = 5 * 1024 * 1024
    if file_size > MAX_RECEIPT_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File too large ({round(file_size / 1024 / 1024, 2)}MB). Maximum is 5MB."
        )

    receipt.file.seek(0)

    from app.services.universal_upload_service import UniversalUploadService

    upload_result = await UniversalUploadService.handle_upload(
        file=receipt,
        table_name='crm_lead_transactions',
        record_id=txn_id,
        uploaded_by_id=current_employee.id,
        uploaded_by_type='staff',
        storage_dir='crm_receipts',
        db=db,
        emp_code=getattr(current_employee, 'emp_code', None),
        defer_scheduler=True
    )

    txn.receipt_filename = upload_result['file_name']
    db.commit()
    db.refresh(txn)

    logger.info("[DC-CRM-RECEIPT] Receipt uploaded for txn #%s: %s", txn_id, txn.receipt_filename)

    return {
        'success': True,
        'message': 'Receipt uploaded successfully',
        'receipt_filename': txn.receipt_filename,
        'file_path': upload_result['file_path']
    }


@router.patch("/transactions/{txn_id}/validate")
def validate_transaction(
    txn_id: int,
    company_id: int = Query(..., description="Company ID for DC Protocol"),
    action_data: TransactionValidate = Body(...),
    db: Session = Depends(get_db),
    current_employee: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Validate or reject a transaction
    DC Protocol: Transaction must belong to company
    WVV Protocol: Only VGK/EA/Finance staff can validate
    Updates lead's deal_value_received on validation
    """
    staff_type = (current_employee.staff_type or '').upper()
    is_validator = is_vgk_admin(staff_type) or 'FINANCE' in staff_type or 'ACCOUNT' in staff_type
    
    # DC Protocol: Menu-based access control - page assignment = full access
    # if not is_validator:
    #     raise HTTPException(status_code=403, detail="Only Finance or Admin staff can validate transactions")
    
    txn = db.query(CRMLeadTransaction).filter(
        CRMLeadTransaction.id == txn_id,
        CRMLeadTransaction.company_id == company_id
    ).first()
    
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    if txn.validation_status != 'pending':
        raise HTTPException(status_code=400, detail=f"Cannot process transaction with status: {txn.validation_status}")
    
    action = action_data.action.lower()
    now = get_indian_time()
    
    if action == 'validate':
        txn.validation_status = 'validated'
        txn.validated_by_id = current_employee.id
        txn.validated_at = now
        
        lead = db.query(CRMLead).filter(CRMLead.id == txn.lead_id).first()
        if lead:
            # DC-TXN-DEAL-SYNC-001 (Jun 2026): Keep crm_lead_deals.deal_value_received in sync
            # so the DEALS table shows non-zero received and _update_lead_aggregate_deal_values
            # does not reset lead received to 0 on the next deal edit.
            if txn.deal_id:
                _txn_deal = db.query(CRMLeadDeal).filter(CRMLeadDeal.id == txn.deal_id).first()
                if _txn_deal:
                    _txn_deal.deal_value_received = (_txn_deal.deal_value_received or 0) + txn.amount
                    _txn_deal.deal_value_balance = max(0, (_txn_deal.deal_value_total or 0) - _txn_deal.deal_value_received)

            # DC-TXN-RCVD-SUM-001 (Jun 2026): Recompute lead received from ALL validated txns
            # (not just += this one) to be idempotent and handle retries / race conditions.
            _txn_validated_sum = db.query(
                func.coalesce(func.sum(CRMLeadTransaction.amount), 0)
            ).filter(
                CRMLeadTransaction.lead_id == lead.id,
                CRMLeadTransaction.validation_status == 'validated'
            ).scalar() or 0
            # DC-TXN-CEIL-001: log (non-blocking) when collected exceeds contracted total
            if _txn_validated_sum > (lead.deal_value_total or 0) > 0:
                logger.warning(f'[DC-TXN-CEIL] Lead {lead.id}: validated_sum={_txn_validated_sum} > deal_total={lead.deal_value_total} — over-collection')
            lead.deal_value_received = _txn_validated_sum
            lead.deal_value_balance = max(0, (lead.deal_value_total or 0) - lead.deal_value_received)

            # DC_CFV_001 (Apr 2026): Lock confirmed_final_value on txn validation if lead is at balance_received stage
            _CFV_SOLAR_FINALS_TXN = {'balance_received'}
            _sps_txn = (getattr(lead, 'solar_pipeline_status', '') or '').lower()
            _is_final_txn = _sps_txn in _CFV_SOLAR_FINALS_TXN
            if _is_final_txn and getattr(lead, 'confirmed_final_value', None) is None:
                _sv_txn = getattr(lead, 'solar_value', None)
                _cfv_txn_base = float(_sv_txn) if (_sv_txn is not None and _sv_txn > 0) else float(lead.deal_value_received or 0)
                if _cfv_txn_base > 0:
                    lead.confirmed_final_value = _cfv_txn_base
                    logger.info(f'[DC-CFV] Lead {lead.id}: confirmed_final_value locked at ₹{_cfv_txn_base} (solar_value={_sv_txn}, txn validation)')

            # DC-FIRST-PMT-001: stamp first_payment_received_date with the earliest
            # validated transaction_date for this lead (actual money received date).
            # Only update if NULL (first time) or this txn date is earlier.
            # DC-FIRST-PMT-NULL-FALLBACK-001: if transaction_date is NULL (edge case on
            # older records), fall back to today (IST) so the date is always captured.
            if txn.lead_id:
                _fpr_raw = getattr(txn, 'transaction_date', None)
                if _fpr_raw is not None:
                    _fpr_date = _fpr_raw.date() if hasattr(_fpr_raw, 'date') else _fpr_raw
                else:
                    _fpr_date = get_indian_time().date()
                    logger.warning(f'[DC-FIRST-PMT-NULL-FALLBACK-001] Lead {lead.id}: txn #{txn.id} has NULL transaction_date — using today {_fpr_date}')
                if _fpr_date and (
                    lead.first_payment_received_date is None
                    or _fpr_date < lead.first_payment_received_date
                ):
                    lead.first_payment_received_date = _fpr_date
                    logger.info(f'[DC-FIRST-PMT-001] Lead {lead.id}: first_payment_received_date set to {_fpr_date}')

        db.commit()
        db.refresh(txn)
        txn_dict = txn.to_dict()

        # DC-DVR-ADV-TXN-HOOK-001 (Jul 2026): Trigger DVR advance when payment is validated.
        # validate_transaction updates deal_value_received directly (not via update_lead),
        # so the secondary hook in update_lead never fires.  Fire it here instead.
        if lead and (lead.deal_value_received or 0) > 0:
            try:
                from app.services.vgk_solar_advance import check_and_create_dvr_advance as _dvr_txn_fn
                _dvr_txn_res = _dvr_txn_fn(db, lead.id)
                if _dvr_txn_res.get('created'):
                    logger.info(f'[DC-DVR-ADV-TXN] Lead {lead.id}: DVR advances {_dvr_txn_res.get("entry_numbers")} created via txn validation')
                else:
                    logger.debug(f'[DC-DVR-ADV-TXN] Lead {lead.id}: {_dvr_txn_res.get("reason")}')
            except Exception as _dvr_txn_e:
                logger.warning(f'[DC-DVR-ADV-TXN] Hook failed for lead {lead.id}: {_dvr_txn_e}')

        incentive_result = None
        if lead:
            try:
                incentive_result = create_incentive_for_validated_transaction(
                    db=db,
                    lead=lead,
                    transaction=txn,
                    company_id=company_id,
                    validated_by_id=current_employee.id
                )
                db.commit()
            except Exception as e:
                print(f"[DC-INCENTIVE] Error creating incentive for txn {txn.id}: {e}")
                db.rollback()
                incentive_result = {"success": False, "message": str(e)}
        
        income_entry_result = None
        try:
            income_entry_result = _auto_create_income_entry_from_txn(db, txn, lead, current_employee)
            db.commit()
            txn_dict = txn.to_dict()
        except Exception as e:
            logger.warning("[DC-CRM-SFMS] Error auto-creating income entry for txn #%s: %s", txn.id, e)
            db.rollback()
            income_entry_result = {"success": False, "message": str(e)}

        # DC_STAFF_LEAD_INCV_001 (Apr 2026): Staff lead incentive trigger (field_staff_id)
        staff_incentive_result = None
        if lead and getattr(lead, 'field_staff_id', None):
            try:
                from app.services.staff_lead_incentive_service import trigger_staff_lead_incentive
                staff_incentive_result = trigger_staff_lead_incentive(
                    db=db, lead=lead, transaction=txn,
                    company_id=company_id, validated_by_id=current_employee.id
                )
                db.commit()
            except Exception as _sie:
                logger.warning("[DC-STAFF-INCV] Error: %s", _sie)
                db.rollback()
                staff_incentive_result = {"success": False, "message": str(_sie)}

        # DC-MULTI-STAFF-INCV-001 (Jul 2026): Support Staff + Technical Staff 1 + Technical Staff 2
        # Each role fires independently — same employee in multiple roles earns multiple incentives
        for _ms_role, _ms_attr in [
            ('support_staff', 'support_staff_id'),
            ('tech_staff1',   'technical_staff1_id'),
            ('tech_staff2',   'technical_id'),
        ]:
            _ms_emp_id = getattr(lead, _ms_attr, None) if lead else None
            if not _ms_emp_id:
                continue
            try:
                from app.services.staff_lead_incentive_service import trigger_staff_lead_incentive as _ms_trig
                _ms_result = _ms_trig(
                    db=db, lead=lead, transaction=txn,
                    company_id=company_id, validated_by_id=current_employee.id,
                    override_employee_id=_ms_emp_id
                )
                db.commit()
                if _ms_result.get("success"):
                    message += f' | {_ms_role} ₹{_ms_result.get("incentive_amount", 0):.2f}'
            except Exception as _ms_e:
                logger.warning("[DC-MULTI-STAFF-INCV] %s: %s", _ms_role, _ms_e)
                try: db.rollback()
                except: pass

        message = 'Transaction validated and lead values updated'
        if incentive_result and incentive_result.get("success"):
            message += f' | Incentive created ({incentive_result.get("system", "unknown")} system)'
        if income_entry_result and income_entry_result.get("success"):
            message += f' | Income entry #{income_entry_result.get("entry_number")} auto-created'
        if staff_incentive_result and staff_incentive_result.get("success"):
            message += f' | Staff incentive ₹{staff_incentive_result.get("incentive_amount", 0):.2f} created'
            if staff_incentive_result.get("newly_escalated"):
                message += ' [Tier 1 Unlocked!]'

        return {
            'success': True,
            'message': message,
            'data': txn_dict
        }

    elif action == 'reject':
        txn.validation_status = 'rejected'
        txn.validated_by_id = current_employee.id
        txn.validated_at = now
        txn.rejection_reason = action_data.rejection_reason
        message = 'Transaction rejected'
        
    else:
        raise HTTPException(status_code=400, detail="Invalid action. Use 'validate' or 'reject'")
    
    db.commit()
    db.refresh(txn)
    
    return {
        'success': True,
        'message': message,
        'data': txn.to_dict()
    }


@router.get("/transactions/list")
def list_all_transactions(
    company_id: Optional[int] = Query(None, description="Company ID for DC Protocol (optional for All Companies)"),
    status: Optional[str] = Query(None, description="Filter by validation_status"),
    lead_id: Optional[int] = Query(None, description="Filter by lead"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_employee: StaffEmployee = Depends(get_current_staff_user)
):
    """
    List all transactions with filtering and pagination
    DC Protocol: Filter by company or all accessible companies
    WVV Protocol: Staff authenticated access
    RBAC: VGK/EA/Finance sees all, Others see their own
    """
    staff_type = (current_employee.staff_type or '').upper()
    is_admin = is_vgk_admin(staff_type)
    is_finance = 'FINANCE' in staff_type or 'ACCOUNT' in staff_type
    
    query = db.query(CRMLeadTransaction)
    
    accessible_ids = []
    if current_employee.data_companies:
        try:
            accessible_ids = [int(x) for x in current_employee.data_companies.split(',') if x.strip()]
        except:
            pass
    if current_employee.base_company_id and current_employee.base_company_id not in accessible_ids:
        accessible_ids.append(current_employee.base_company_id)
    
    if company_id:
        query = query.filter(CRMLeadTransaction.company_id == company_id)
        summary_filter = CRMLeadTransaction.company_id == company_id
    elif is_admin:
        summary_filter = or_(CRMLeadTransaction.company_id.isnot(None), CRMLeadTransaction.company_id.is_(None))
    elif accessible_ids:
        query = query.filter(
            or_(
                CRMLeadTransaction.company_id.in_(accessible_ids),
                CRMLeadTransaction.company_id.is_(None)
            )
        )
        summary_filter = or_(
            CRMLeadTransaction.company_id.in_(accessible_ids),
            CRMLeadTransaction.company_id.is_(None)
        )
    else:
        query = query.filter(CRMLeadTransaction.company_id.is_(None))
        summary_filter = CRMLeadTransaction.company_id.is_(None)
    
    if not (is_admin or is_finance):
        query = query.filter(
            or_(
                CRMLeadTransaction.created_by_id == current_employee.id,
                CRMLeadTransaction.collected_by_id == current_employee.id
            )
        )
    
    if status:
        query = query.filter(CRMLeadTransaction.validation_status == status)
    
    if lead_id:
        query = query.filter(CRMLeadTransaction.lead_id == lead_id)
    
    total = query.count()
    
    transactions = query.order_by(CRMLeadTransaction.transaction_date.desc())\
        .offset((page - 1) * page_size)\
        .limit(page_size)\
        .all()
    
    results = []
    for txn in transactions:
        txn_data = txn.to_dict()
        lead = db.query(CRMLead).filter(CRMLead.id == txn.lead_id).first()
        if lead:
            txn_data['lead_name'] = lead.name
            txn_data['lead_phone'] = lead.phone
            txn_data['deal_value_total'] = lead.deal_value_total
        
        if txn.collected_by_id:
            collector = db.query(StaffEmployee).filter(StaffEmployee.id == txn.collected_by_id).first()
            txn_data['collected_by_name'] = collector.full_name if collector else None
        
        if txn.validated_by_id:
            validator = db.query(StaffEmployee).filter(StaffEmployee.id == txn.validated_by_id).first()
            txn_data['validated_by_name'] = validator.full_name if validator else None
        
        results.append(txn_data)
    
    summary = {
        'total_transactions': total,
        'pending_count': db.query(CRMLeadTransaction).filter(
            summary_filter,
            CRMLeadTransaction.validation_status == 'pending'
        ).count(),
        'validated_amount': db.query(func.sum(CRMLeadTransaction.amount)).filter(
            summary_filter,
            CRMLeadTransaction.validation_status == 'validated'
        ).scalar() or 0
    }
    
    return {
        'success': True,
        'data': results,
        'pagination': {
            'page': page,
            'page_size': page_size,
            'total': total,
            'total_pages': (total + page_size - 1) // page_size
        },
        'summary': summary
    }


# ============================================================================
# SALES TEAM REVENUE - FINANCE REVIEW & LEDGER POSTING
# DC Protocol: Company-wise segregation for transactions and ledgers
# ============================================================================

class FinanceReviewRequest(BaseModel):
    """Finance review request with ledger posting options"""
    action: str  # 'validate', 'reject', 'post_to_ledger'
    rejection_reason: Optional[str] = None
    finance_notes: Optional[str] = None
    ledger_company_id: Optional[int] = None
    ledger_mode: Optional[str] = None  # 'existing', 'new_from_lead', 'new_custom'
    existing_ledger_party_id: Optional[int] = None
    existing_ledger_party_name: Optional[str] = None
    new_ledger_lead_id: Optional[int] = None
    new_ledger_custom_name: Optional[str] = None


@router.get("/transactions/dashboard")
def get_transactions_dashboard(
    company_id: Optional[int] = Query(None, description="Company ID for DC Protocol (optional for All Companies)"),
    db: Session = Depends(get_db),
    current_employee: StaffEmployee = Depends(get_current_staff_user)
):
    """Dashboard statistics for Sales Team Revenue page"""
    staff_type = (current_employee.staff_type or '').upper()
    is_admin = is_vgk_admin(staff_type)
    is_finance = 'FINANCE' in staff_type or 'ACCOUNT' in staff_type
    
    accessible_ids = []
    if current_employee.data_companies:
        try:
            accessible_ids = [int(x) for x in current_employee.data_companies.split(',') if x.strip()]
        except:
            pass
    if current_employee.base_company_id and current_employee.base_company_id not in accessible_ids:
        accessible_ids.append(current_employee.base_company_id)
    
    base_query = db.query(CRMLeadTransaction)
    
    if company_id:
        base_query = base_query.filter(CRMLeadTransaction.company_id == company_id)
        company_filter = CRMLeadTransaction.company_id == company_id
    elif is_admin:
        company_filter = or_(CRMLeadTransaction.company_id.isnot(None), CRMLeadTransaction.company_id.is_(None))
    elif accessible_ids:
        base_query = base_query.filter(
            or_(
                CRMLeadTransaction.company_id.in_(accessible_ids),
                CRMLeadTransaction.company_id.is_(None)
            )
        )
        company_filter = or_(
            CRMLeadTransaction.company_id.in_(accessible_ids),
            CRMLeadTransaction.company_id.is_(None)
        )
    else:
        base_query = base_query.filter(CRMLeadTransaction.company_id.is_(None))
        company_filter = CRMLeadTransaction.company_id.is_(None)
    
    if not (is_admin or is_finance):
        base_query = base_query.filter(
            or_(
                CRMLeadTransaction.created_by_id == current_employee.id,
                CRMLeadTransaction.collected_by_id == current_employee.id
            )
        )
    
    pending_amt = db.query(func.sum(CRMLeadTransaction.amount)).filter(
        company_filter,
        CRMLeadTransaction.validation_status == 'pending'
    ).scalar() or 0
    
    validated_amt = db.query(func.sum(CRMLeadTransaction.amount)).filter(
        company_filter,
        CRMLeadTransaction.validation_status == 'validated'
    ).scalar() or 0
    
    posted_amt = db.query(func.sum(CRMLeadTransaction.amount)).filter(
        company_filter,
        CRMLeadTransaction.validation_status == 'posted_to_ledger'
    ).scalar() or 0
    
    rejected_amt = db.query(func.sum(CRMLeadTransaction.amount)).filter(
        company_filter,
        CRMLeadTransaction.validation_status == 'rejected'
    ).scalar() or 0
    
    return {
        'success': True,
        'data': {
            'pending': {'count': base_query.filter(CRMLeadTransaction.validation_status == 'pending').count(), 'amount': float(pending_amt)},
            'validated': {'count': base_query.filter(CRMLeadTransaction.validation_status == 'validated').count(), 'amount': float(validated_amt)},
            'posted_to_ledger': {'count': base_query.filter(CRMLeadTransaction.validation_status == 'posted_to_ledger').count(), 'amount': float(posted_amt)},
            'rejected': {'count': base_query.filter(CRMLeadTransaction.validation_status == 'rejected').count(), 'amount': float(rejected_amt)},
            'total_revenue': float(validated_amt) + float(posted_amt)
        }
    }


@router.get("/transactions/search-ledgers")
def search_existing_ledgers(
    ledger_company_id: int = Query(..., description="Company ID to search ledgers in"),
    search: str = Query("", description="Search term for party name"),
    limit: int = Query(20, ge=1, le=50),
    db: Session = Depends(get_db),
    current_employee: StaffEmployee = Depends(get_current_staff_user)
):
    """Search existing CUSTOMER ledgers in a company for DC Protocol"""
    query = db.query(
        PartyLedger.party_id,
        PartyLedger.party_name,
        func.max(PartyLedger.id).label('latest_id')
    ).filter(
        PartyLedger.company_id == ledger_company_id,
        PartyLedger.party_type == 'CUSTOMER'
    ).group_by(PartyLedger.party_id, PartyLedger.party_name)
    
    if search:
        query = query.filter(PartyLedger.party_name.ilike(f"%{search}%"))
    
    ledgers = query.order_by(PartyLedger.party_name).limit(limit).all()
    
    results = []
    for ledger in ledgers:
        latest = db.query(PartyLedger).filter(PartyLedger.id == ledger.latest_id).first()
        results.append({
            'party_id': ledger.party_id,
            'party_name': ledger.party_name,
            'current_balance': float(latest.running_balance) if latest else 0,
            'company_id': ledger_company_id
        })
    
    return {'success': True, 'data': results, 'count': len(results)}


@router.get("/transactions/search-leads")
def search_leads_for_new_ledger(
    company_id: int = Query(..., description="Company ID for DC Protocol"),
    search: str = Query("", description="Search term"),
    limit: int = Query(20, ge=1, le=50),
    db: Session = Depends(get_db),
    current_employee: StaffEmployee = Depends(get_current_staff_user)
):
    """Search leads for creating new ledger with lead name"""
    from app.models.staff_accounts import AssociatedCompany
    
    query = db.query(CRMLead).filter(CRMLead.company_id == company_id)
    if search:
        search_term = f"%{search}%"
        query = query.filter(or_(
            CRMLead.name.ilike(search_term),
            CRMLead.phone.ilike(search_term),
            CRMLead.pincode.ilike(search_term)
        ))
    
    leads = query.order_by(CRMLead.name).limit(limit).all()
    results = []
    for lead in leads:
        company = db.query(AssociatedCompany).filter(AssociatedCompany.id == lead.company_id).first()
        results.append({
            'id': lead.id, 'name': lead.name, 'phone': lead.phone,
            'company_id': lead.company_id, 'company_name': company.company_name if company else None
        })
    
    return {'success': True, 'data': results}


def _auto_create_income_entry(db, txn, lead, employee_id):
    class _StubEmployee:
        def __init__(self, eid): self.id = eid
    result = _auto_create_income_entry_from_txn(db, txn, lead, _StubEmployee(employee_id))
    if result and result.get("success"):
        from app.models.staff_accounts import IncomeEntry
        return db.query(IncomeEntry).filter(IncomeEntry.id == result["income_entry_id"]).first()
    return None


@router.patch("/transactions/{txn_id}/finance-review")
def finance_review_transaction(
    txn_id: int,
    company_id: Optional[int] = Query(None, description="Company ID for DC Protocol (optional for orphaned transactions)"),
    review_data: FinanceReviewRequest = Body(...),
    db: Session = Depends(get_db),
    current_employee: StaffEmployee = Depends(get_current_staff_user)
):
    """Finance review with ledger posting - DC/WVV Protocol compliant"""
    from app.models.staff_accounts import AssociatedCompany
    
    staff_type = (current_employee.staff_type or '').upper()
    is_admin = is_vgk_admin(staff_type)
    is_finance = 'FINANCE' in staff_type or 'ACCOUNT' in staff_type
    
    # DC Protocol: Menu-based access control - page assignment = full access
    # if not (is_admin or is_finance):
    #     raise HTTPException(status_code=403, detail="Only Finance or Admin staff can review transactions")
    
    txn = db.query(CRMLeadTransaction).filter(CRMLeadTransaction.id == txn_id).first()
    
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    # DC Protocol: Menu-based access control - page assignment = full access
    # if not is_admin:
    #     accessible_ids = []
    #     if current_employee.data_companies:
    #         try:
    #             accessible_ids = [int(x) for x in current_employee.data_companies.split(',') if x.strip()]
    #         except:
    #             pass
    #     if current_employee.base_company_id and current_employee.base_company_id not in accessible_ids:
    #         accessible_ids.append(current_employee.base_company_id)
    #     
    #     if txn.company_id:
    #         if not accessible_ids or txn.company_id not in accessible_ids:
    #             raise HTTPException(status_code=403, detail="Access denied to this transaction's company")
    #     elif not accessible_ids:
    #         pass
    
    if company_id and txn.company_id and txn.company_id != company_id:
        raise HTTPException(status_code=400, detail="Company ID mismatch")
    
    action = review_data.action.lower()
    now = get_indian_time()
    
    if action == 'reject':
        if txn.validation_status not in ['pending', 'validated']:
            raise HTTPException(status_code=400, detail=f"Cannot reject transaction with status: {txn.validation_status}")
        txn.validation_status = 'rejected'
        txn.validated_by_id = current_employee.id
        txn.validated_at = now
        txn.rejection_reason = review_data.rejection_reason
        txn.finance_notes = review_data.finance_notes
        db.commit()
        db.refresh(txn)
        return {'success': True, 'message': 'Transaction rejected', 'data': txn.to_dict()}
    
    elif action == 'validate':
        if txn.validation_status != 'pending':
            raise HTTPException(status_code=400, detail=f"Cannot validate transaction with status: {txn.validation_status}")
        txn.validation_status = 'validated'
        txn.validated_by_id = current_employee.id
        txn.validated_at = now
        txn.finance_notes = review_data.finance_notes
        lead = db.query(CRMLead).filter(CRMLead.id == txn.lead_id).first()
        if lead:
            lead.deal_value_received = (lead.deal_value_received or 0) + txn.amount
            lead.deal_value_balance = max(0, (lead.deal_value_total or 0) - lead.deal_value_received)

        income_entry = _auto_create_income_entry(db, txn, lead, current_employee.id)
        db.commit()
        db.refresh(txn)
        result = txn.to_dict()
        if income_entry:
            result['income_entry_id'] = income_entry.id
            result['income_entry_number'] = income_entry.entry_number

        # VGK Commission Hook (DC Protocol Mar 2026)
        if lead and getattr(lead, 'is_vgk_program', False):
            from app.services.vgk_commission import calculate_vgk_commissions
            try:
                _txn_amt = float(txn.amount or 0)
                _tax_rate = float(getattr(lead, 'deal_tax_rate', 0) or 0)
                _revenue_for_commission = round(_txn_amt / (1 + _tax_rate / 100), 2) if _tax_rate > 0 else _txn_amt
                calculate_vgk_commissions(db, lead.id, txn.id, _revenue_for_commission)
            except Exception as _vgk_e:
                logger.warning(f"[VGK] Commission calculation failed for lead {lead.id}: {_vgk_e}")
            # DC Protocol May 2026: Mirror DRAFT income entries into vgk_cash_income_entries
            # Idempotent — skips levels that already have an entry (unique constraint guard).
            try:
                from app.services.vgk_cash_income import generate_vgk_cash_income_drafts
                _ci_count = generate_vgk_cash_income_drafts(db, lead)
                if _ci_count:
                    logger.info(f"[VGK-CI] {_ci_count} DRAFT cash-income entries created for lead {lead.id}")
            except Exception as _ci_e:
                logger.warning(f"[VGK-CI] Draft cash-income creation failed for lead {lead.id}: {_ci_e}")

        # MNR / Partner Commission Hook (DC Protocol Apr 2026)
        # Applies when source_ref_type is 'mnr' or 'partner'. VGK path above is untouched.
        if lead and getattr(lead, 'source_ref_type', None) in ('mnr', 'partner'):
            from app.services.crm_commission import calculate_referrer_commissions
            try:
                _txn_amt = float(txn.amount or 0)
                _tax_rate = float(getattr(lead, 'deal_tax_rate', 0) or 0)
                _revenue_for_commission = round(_txn_amt / (1 + _tax_rate / 100), 2) if _tax_rate > 0 else _txn_amt
                calculate_referrer_commissions(db, lead.id, txn.id, _revenue_for_commission)
            except Exception as _mnr_e:
                logger.warning(f"[CRM-COMM] Commission calculation failed for lead {lead.id}: {_mnr_e}")

        # VGK Member Activation Hook (DC Protocol Mar 2026)
        if lead and getattr(lead, 'is_vgk_program', False):
            assoc_id = getattr(lead, 'associated_partner_id', None)
            if assoc_id:
                from app.models.staff_accounts import OfficialPartner
                prospect = db.query(OfficialPartner).filter(
                    OfficialPartner.id == assoc_id,
                    OfficialPartner.category == 'VGK_TEAM',
                    OfficialPartner.is_active == False
                ).first()
                if prospect and txn.amount and float(txn.amount) >= 4900:
                    from app.services.vgk_commission import activate_vgk_member
                    try:
                        activate_vgk_member(db, assoc_id, lead.company_id, current_employee.id)
                    except Exception as _act_e:
                        logger.warning(f"[VGK] Activation failed for partner {assoc_id}: {_act_e}")

        return {'success': True, 'message': 'Transaction validated and income entry created', 'data': result}
    
    elif action == 'post_to_ledger':
        if txn.validation_status not in ['pending', 'validated']:
            raise HTTPException(status_code=400, detail=f"Cannot post transaction with status: {txn.validation_status}")
        if txn.ledger_entry_id:
            raise HTTPException(status_code=400, detail="Already posted to ledger")
        
        if not review_data.ledger_company_id:
            raise HTTPException(status_code=400, detail="Ledger company is required")
        ledger_company = db.query(AssociatedCompany).filter(AssociatedCompany.id == review_data.ledger_company_id).first()
        if not ledger_company:
            raise HTTPException(status_code=400, detail="Invalid ledger company")
        
        ledger_mode = review_data.ledger_mode
        if not ledger_mode or ledger_mode not in ['existing', 'new_from_lead', 'new_custom']:
            raise HTTPException(status_code=400, detail="Valid ledger mode required: existing, new_from_lead, or new_custom")
        
        party_id, party_name = None, None
        
        if ledger_mode == 'existing':
            if not review_data.existing_ledger_party_id:
                raise HTTPException(status_code=400, detail="Existing ledger party ID required")
            existing = db.query(PartyLedger).filter(
                PartyLedger.company_id == review_data.ledger_company_id,
                PartyLedger.party_type == 'CUSTOMER',
                PartyLedger.party_id == review_data.existing_ledger_party_id
            ).first()
            if not existing:
                raise HTTPException(status_code=400, detail="Selected ledger not found")
            party_id, party_name = existing.party_id, existing.party_name
            txn.ledger_party_source = 'existing'
            
        elif ledger_mode == 'new_from_lead':
            if not review_data.new_ledger_lead_id:
                raise HTTPException(status_code=400, detail="Lead ID required")
            source_lead = db.query(CRMLead).filter(CRMLead.id == review_data.new_ledger_lead_id).first()
            if not source_lead:
                raise HTTPException(status_code=400, detail="Lead not found")
            party_id, party_name = source_lead.id, source_lead.name
            txn.ledger_party_source = 'lead'
            txn.ledger_party_lead_id = source_lead.id
            
        elif ledger_mode == 'new_custom':
            if not review_data.new_ledger_custom_name:
                raise HTTPException(status_code=400, detail="Custom name required")
            max_custom = db.query(func.min(PartyLedger.party_id)).filter(
                PartyLedger.company_id == review_data.ledger_company_id,
                PartyLedger.party_type == 'CUSTOMER', PartyLedger.party_id < 0
            ).scalar() or 0
            party_id = min(max_custom - 1, -1)
            party_name = review_data.new_ledger_custom_name
            txn.ledger_party_source = 'custom'
        
        last_entry = db.query(PartyLedger).filter(
            PartyLedger.company_id == review_data.ledger_company_id,
            PartyLedger.party_type == 'CUSTOMER', PartyLedger.party_id == party_id
        ).order_by(PartyLedger.id.desc()).first()
        prev_balance = float(last_entry.running_balance) if last_entry else 0
        
        ledger_entry = PartyLedger(
            party_type='CUSTOMER', party_id=party_id, party_name=party_name,
            company_id=review_data.ledger_company_id,
            transaction_date=txn.transaction_date.date() if txn.transaction_date else now.date(),
            entry_type='CREDIT', reference_type='CRM_REVENUE', reference_id=txn.id,
            reference_number=txn.reference_number or f"CRM-TXN-{txn.id}",
            debit_amount=Decimal('0'), credit_amount=Decimal(str(txn.amount)),
            running_balance=Decimal(str(prev_balance)) - Decimal(str(txn.amount)),
            narration=f"CRM Lead Payment - {party_name} - {txn.payment_mode.upper()}"
        )
        db.add(ledger_entry)
        db.flush()
        
        lead = db.query(CRMLead).filter(CRMLead.id == txn.lead_id).first()
        if txn.validation_status == 'pending':
            if lead:
                lead.deal_value_received = (lead.deal_value_received or 0) + txn.amount
                lead.deal_value_balance = max(0, (lead.deal_value_total or 0) - lead.deal_value_received)
        
        _auto_create_income_entry(db, txn, lead, current_employee.id)

        txn.validation_status = 'posted_to_ledger'
        txn.validated_by_id = current_employee.id
        txn.validated_at = now
        txn.finance_notes = review_data.finance_notes
        txn.ledger_entry_id = ledger_entry.id
        txn.ledger_party_name = party_name
        txn.ledger_posted_by_id = current_employee.id
        txn.ledger_posted_at = now
        
        db.commit()
        db.refresh(txn)
        
        return {
            'success': True,
            'message': f'Posted to ledger ({ledger_company.company_name})',
            'data': txn.to_dict(),
            'ledger_entry': {
                'id': ledger_entry.id, 'company_name': ledger_company.company_name,
                'party_name': party_name, 'amount': float(txn.amount), 'ledger_mode': ledger_mode
            }
        }
    
    raise HTTPException(status_code=400, detail="Invalid action")


# =============================================================================
# UNIFIED MY LEADS ENDPOINT - Works for Staff, MNR Members, Partners
# Dec 2025: Supports segment filters (my, assigned, fresh) and Add Lead
# =============================================================================

@router.get("/search-mnr-users")
def search_mnr_users(
    search: str = Query(..., min_length=2, description="Search by MNR ID or name"),
    company_id: Optional[int] = Query(None, description="Optional company filter"),
    limit: int = Query(20, ge=1, le=50),
    db: Session = Depends(get_db),
    current_employee: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Search MNR users by ID or name for lead assignment.
    DC Protocol: Returns only active users for assignment.
    Used for: MNR Handler, Guru, Adi Guru selection.
    """
    search_term = f"%{search.strip()}%"
    
    query = db.query(User).filter(
        User.activation_date.isnot(None),
        or_(
            User.id.ilike(search_term),
            User.name.ilike(search_term)
        )
    )
    
    users = query.order_by(User.name).limit(limit).all()
    
    results = []
    for user in users:
        sponsor = None
        if user.referrer_id:
            sponsor_user = db.query(User).filter(User.id == user.referrer_id).first()
            sponsor = {
                'id': sponsor_user.id,
                'name': sponsor_user.name
            } if sponsor_user else None
        
        results.append({
            'id': user.id,
            'name': user.name,
            'phone': user.phone,
            'email': user.email,
            'sponsor_id': user.referrer_id,
            'sponsor': sponsor,
            'package_level': user.package_level,
            'activation_date': user.activation_date.isoformat() if user.activation_date else None
        })
    
    return {
        'success': True,
        'data': results,
        'total': len(results)
    }



@router.get("/leader-info")
async def get_leader_info(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
):
    """
    DC Protocol: Check if current staff user is a team leader (has direct reports).
    Returns leader status for frontend to show/hide Team tab.
    """
    from app.models.staff import StaffEmployee
    from app.utils.staff_hierarchy import has_direct_reports
    
    # Check if staff user
    is_staff = hasattr(current_user, 'emp_code') and current_user.emp_code
    
    if not is_staff:
        return {
            'success': True,
            'is_leader': False,
            'can_view_all_leads': False,
            'message': 'Only staff users can be team leaders'
        }
    
    is_leader = has_direct_reports(current_user.id, db, StaffEmployee)
    
    return {
        'success': True,
        'is_leader': is_leader,
        'can_view_all_leads': is_leader
    }


@router.get("/unified-my-leads")
async def get_unified_my_leads(
    request: Request,
    segment: str = Query("my", description="Segment: 'my' (owned), 'assigned' (given by others), 'fresh' (claimable), 'staff_handler' (handler-based)"),
    company_id: Optional[int] = Query(None, description="Company ID for DC Protocol (optional for MNR)"),
    role: Optional[str] = Query(None, description="Role hint: 'mnr' to prioritize MNR session over staff session"),
    handler_role: Optional[str] = Query(None, description="Handler role filter for staff_handler segment: telecaller, field_staff, partner, mnr_handler"),
    target_user_id: Optional[str] = Query(None, description="DC Protocol: Staff leadership (hierarchy>=100) can view any MNR member's leads by their ID"),
    status: Optional[str] = None,
    priority: Optional[str] = None,
    category: Optional[str] = Query(None),
    category_id: Optional[int] = None,
    search: Optional[str] = None,
    sort_by: Optional[str] = Query(None, description="Sort column: created_at, updated_at, next_followup_date, deal_value_total, deal_value_received"),
    sort_dir: Optional[str] = Query(None, description="Sort direction: asc or desc"),
    followup_filter: Optional[str] = Query(None, description="Followup quick-filter: 'today' or 'overdue'"),
    handler_type: Optional[str] = Query(None, description="DC Protocol N003 — derived handler type filter: VGK4U, Walk-In, Showroom, Direct"),
    month: Optional[int] = Query(None, description="Filter by updated_at month (1-12)"),
    year: Optional[int] = Query(None, description="Filter by updated_at year"),
    page: int = 1,
    per_page: int = 20,
    db: Session = Depends(get_db)
):
    """
    Unified My Leads endpoint for all user types (Staff, MNR Members, Partners).
    DC Protocol: Company segregation applied based on user type.
    
    DC Protocol (Dec 31, 2025): Added role hint parameter to resolve dual-session conflicts.
    When role='mnr' is passed, MNR session is prioritized over staff session.
    
    DC Protocol (Jan 01, 2026): Added staff_handler segment with handler_role filter.
    Shows leads where current staff user is assigned as specific handler role.
    
    Segments:
    - my: Leads where current user is primary owner or MNR handler
    - assigned: Leads assigned to user by someone else (not self-created)
    - fresh: New/unassigned leads available for claiming
    - staff_handler: Leads where staff is assigned as telecaller, field_staff, partner, or mnr_handler
    """
    from app.models.staff import StaffEmployee
    from app.core.security import get_current_mnr_user_from_hybrid, get_current_user_hybrid
    
    # DC Protocol (Dec 31, 2025): Role-based session priority
    if role == 'mnr':
        try:
            current_user = await get_current_mnr_user_from_hybrid(request, db)
        except HTTPException as e:
            if e.status_code == 401:
                current_user = await get_current_user_hybrid(request, db)
            else:
                raise e
    elif role == 'partner':
        # DC Protocol (Apr 2026): Partner-specific session resolver — prevents staff token bleed
        from app.core.security import get_current_user_hybrid_with_partner
        try:
            current_user = await get_current_user_hybrid_with_partner(request, db)
        except HTTPException as e:
            if e.status_code == 401:
                current_user = await get_current_user_hybrid(request, db)
            else:
                raise e
    else:
        current_user = await get_current_user_hybrid(request, db)

    user_id = current_user.id
    is_staff_user = isinstance(current_user, StaffEmployee)
    from app.models.staff_accounts import OfficialPartner as _OfficialPartner
    is_partner_user = isinstance(current_user, _OfficialPartner)
    user_type = 'staff' if is_staff_user else ('partner' if is_partner_user else getattr(current_user, 'user_type', 'MNR'))
    # DC Protocol: created_by_id is VARCHAR, need string for comparison
    user_id_str = str(user_id)

    # DC Protocol (Mar 05, 2026): target_user_id — Key Leadership (hierarchy>=100) can view any MNR member's leads
    if target_user_id and is_staff_user:
        user_hierarchy_level = 0
        if hasattr(current_user, 'role') and current_user.role:
            user_hierarchy_level = getattr(current_user.role, 'hierarchy_level', 0) or 0
        if user_hierarchy_level < 100:
            raise HTTPException(status_code=403, detail="Insufficient hierarchy level to view another member's leads. Key Leadership or above required.")
        from app.models.user import User as UserModel
        target_member = db.query(UserModel).filter(UserModel.id == target_user_id).first()
        if not target_member:
            raise HTTPException(status_code=404, detail="MNR member not found")
        user_id = target_member.id
        is_staff_user = False
        user_type = 'MNR'
        user_id_str = str(user_id)

    query = db.query(CRMLead)
    
    if company_id:
        query = query.filter(CRMLead.company_id == company_id)
    elif is_staff_user:
        # DC Protocol: Staff users - filter by their data_companies
        staff_companies = getattr(current_user, 'data_companies', None) or []
        if staff_companies:
            query = query.filter(CRMLead.company_id.in_(staff_companies))
    elif is_partner_user:
        # DC Protocol (Jul 2026 Fix): Do NOT restrict partners to their base company_id.
        pass

    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"[DEBUG-LEADS] Starting unified-my-leads for partner. user_id={user_id}, segment={segment}")
    
    if segment == 'my':
        if is_staff_user:
            # Staff user: Check telecaller_id, field_staff_id, or primary_owner (staff type)
            # Note: telecaller_id, field_staff_id, primary_owner_id are Integer
            # created_by_id is VARCHAR, so use string comparison
            # DC Protocol (Mar 2026): Also include truly unassigned sheet leads so all staff can see and claim them.
            query = query.filter(
                or_(
                    CRMLead.telecaller_id == user_id,
                    CRMLead.field_staff_id == user_id,
                    and_(
                        CRMLead.primary_owner_type == 'staff',
                        CRMLead.primary_owner_id == user_id
                    ),
                    and_(
                        CRMLead.created_by_type == 'staff',
                        CRMLead.created_by_id == user_id_str
                    ),
                    and_(
                        CRMLead.handler_type == 'unassigned',
                        CRMLead.status == 'new',
                        CRMLead.primary_owner_id.is_(None),
                        CRMLead.telecaller_id.is_(None),
                        CRMLead.field_staff_id.is_(None),
                    ),
                )
            )
        elif is_partner_user:
            # DC Protocol (Apr 2026): Partner user — leads tagged to this partner OR created by partner app
            # DC Protocol (Apr 2026 Fix): Also include showroom/walk-in leads tagged via source_ref_type='partner'
            query = query.filter(
                or_(
                    CRMLead.associated_partner_id == user_id,
                    and_(
                        CRMLead.created_by_type == 'partner',
                        CRMLead.created_by_id == user_id_str
                    ),
                    and_(
                        CRMLead.source_ref_type.in_(('partner', 'vgk_partner')),
                        CRMLead.source_ref_id == user_id_str
                    )
                )
            )
        else:
            # MNR user: Check mnr_handler_id OR created_by member
            # DC Protocol (Dec 31, 2025): primary_owner_id is Integer type - NOT for MNR string IDs
            # MNR ownership tracked via mnr_handler_id (VARCHAR) and created_by fields
            query = query.filter(
                or_(
                    CRMLead.mnr_handler_id == user_id,
                    and_(
                        CRMLead.created_by_type == 'member',
                        CRMLead.created_by_id == user_id_str
                    )
                )
            )
    elif segment == 'overall':
        if is_partner_user:
            # DC Protocol (Apr 2026): Overall for partner — all leads they are involved in any role
            # Includes source, guru (L2), zguru (L3) via VGK income entries, and field support
            _guru_all_ids = [r[0] for r in db.execute(
                text("SELECT DISTINCT source_lead_id FROM vgk_team_income_entries "
                     "WHERE partner_id=:pid AND level IN (2,3) AND source_lead_id IS NOT NULL"),
                {"pid": user_id}
            ).fetchall()]
            _fs_ids = [r[0] for r in db.query(CRMLead.id).filter(CRMLead.vgk_field_support_id == user_id).all()]
            _src_ids = [r[0] for r in db.query(CRMLead.id).filter(
                or_(CRMLead.associated_partner_id == user_id,
                    and_(CRMLead.created_by_type == 'partner', CRMLead.created_by_id == user_id_str),
                    and_(CRMLead.source_ref_type.in_(('partner', 'vgk_partner')), CRMLead.source_ref_id == user_id_str))
            ).all()]
            _all_partner_lead_ids = list(set(_guru_all_ids + _fs_ids + _src_ids))
            logger.info(f"[DEBUG-LEADS] segment={segment}, _all_partner_lead_ids={_all_partner_lead_ids}")
            if _all_partner_lead_ids:
                query = query.filter(CRMLead.id.in_(_all_partner_lead_ids))
            else:
                query = query.filter(CRMLead.id == -1)
        else:
            # MNR user: Check mnr_handler_id OR created_by member
            # DC Protocol (Dec 31, 2025): primary_owner_id is Integer type - NOT for MNR string IDs
            # MNR ownership tracked via mnr_handler_id (VARCHAR) and created_by fields
            query = query.filter(
                or_(
                    CRMLead.mnr_handler_id == user_id,
                    and_(
                        CRMLead.created_by_type == 'member',
                        CRMLead.created_by_id == user_id_str
                    )
                )
            )
    elif segment == 'source' and is_partner_user:
        # DC Protocol (Apr 2026): Source tab for partner — leads where partner is primary source
        # DC Protocol (Apr 2026 Fix): Also include showroom/walk-in leads tagged via source_ref_type='partner'
        query = query.filter(
            or_(
                CRMLead.associated_partner_id == user_id,
                and_(CRMLead.created_by_type == 'partner', CRMLead.created_by_id == user_id_str),
                and_(CRMLead.source_ref_type.in_(('partner', 'vgk_partner')), CRMLead.source_ref_id == user_id_str)
            )
        )
    elif segment == 'guru' and is_partner_user:
        # DC Protocol (Apr 2026): Guru tab — L2 income entries for this partner
        _guru_ids = [r[0] for r in db.execute(
            text("SELECT DISTINCT source_lead_id FROM vgk_team_income_entries "
                 "WHERE partner_id=:pid AND level=2 AND source_lead_id IS NOT NULL"),
            {"pid": user_id}
        ).fetchall()]
        query = query.filter(CRMLead.id.in_(_guru_ids)) if _guru_ids else query.filter(CRMLead.id == -1)
    elif segment == 'zguru' and is_partner_user:
        # DC Protocol (Apr 2026): Z Guru tab — L3 income entries for this partner
        _zguru_ids = [r[0] for r in db.execute(
            text("SELECT DISTINCT source_lead_id FROM vgk_team_income_entries "
                 "WHERE partner_id=:pid AND level=3 AND source_lead_id IS NOT NULL"),
            {"pid": user_id}
        ).fetchall()]
        query = query.filter(CRMLead.id.in_(_zguru_ids)) if _zguru_ids else query.filter(CRMLead.id == -1)
    elif segment == 'support' and is_partner_user:
        # DC Protocol (Apr 2026): Field Support tab — partner is the field support (L4)
        query = query.filter(CRMLead.vgk_field_support_id == user_id)
    elif segment == 'assigned':
        if is_staff_user:
            # Staff: Leads assigned to them by others
            query = query.filter(
                or_(
                    CRMLead.telecaller_id == user_id,
                    CRMLead.field_staff_id == user_id
                ),
                or_(
                    CRMLead.created_by_id != user_id_str,
                    CRMLead.created_by_id.is_(None)
                )
            )
        else:
            # DC Protocol (Apr 2026): "On Ground Support" tab — MNR member is tagged as ground/field
            # support on these leads. Two storage patterns exist in the system:
            #   (A) adi_guru_id           — legacy field (INTEGER-like user id stored as string)
            #   (B) field_support_ref_id  — newer field (stores MNR member id string)
            # Both must be checked so all leads where the member plays a support role surface here.
            query = query.filter(or_(
                CRMLead.adi_guru_id == user_id,
                CRMLead.field_support_ref_id == user_id_str
            ))
    elif segment == 'fresh':
        # DC Protocol: Fresh leads must be unassigned AND in 'new' status
        # Do NOT include leads solely based on company_id being NULL (security fix)
        query = query.filter(
            CRMLead.status == 'new',
            CRMLead.handler_type == 'unassigned',
            CRMLead.mnr_handler_id.is_(None),
            CRMLead.telecaller_id.is_(None),
            CRMLead.field_staff_id.is_(None)
        )
    elif segment == 'staff_handler':
        # DC Protocol (Jan 01, 2026): Staff handler-based filtering
        # Shows leads where current staff is assigned as specific handler role
        if not is_staff_user:
            raise HTTPException(
                status_code=403,
                detail="Staff handler segment is only available for staff users"
            )
        
        # Filter by handler_role if specified, otherwise show all handler roles
        if handler_role == 'telecaller':
            query = query.filter(CRMLead.telecaller_id == user_id)
        elif handler_role == 'field_staff':
            query = query.filter(CRMLead.field_staff_id == user_id)
        elif handler_role == 'partner':
            # For partner, find leads where partner is assigned
            # Staff can view partner leads they created or manage via primary ownership
            # Since there's no direct staff-partner link, filter by leads where user is primary owner with partner involvement
            query = query.filter(
                and_(
                    CRMLead.primary_owner_type == 'staff',
                    CRMLead.primary_owner_id == user_id,
                    or_(
                        CRMLead.associated_partner_id.isnot(None),
                        CRMLead.vendor_id.isnot(None)
                    )
                )
            )
        elif handler_role == 'mnr_handler':
            # Staff can be assigned as MNR handler via their staff ID (integer)
            query = query.filter(CRMLead.mnr_handler_id == user_id)
        else:
            # No handler_role filter - show all leads where user is ANY handler
            query = query.filter(
                or_(
                    CRMLead.telecaller_id == user_id,
                    CRMLead.field_staff_id == user_id,
                    CRMLead.associated_partner_id == user_id,
                    CRMLead.vendor_id == user_id,
                    and_(
                        CRMLead.primary_owner_type == 'staff',
                        CRMLead.primary_owner_id == user_id
                    )
                )
            )
    elif segment == 'team':
        # DC Protocol: Team leads - for reporting managers to see their downline's leads
        # DC Protocol (Jan 01, 2026): Hierarchy-aware filtering
        # - Supreme/Key Leadership (hierarchy_level >= 100): Full recursive downline
        # - Regular staff: Direct reports only
        if not is_staff_user:
            raise HTTPException(
                status_code=403,
                detail="Team segment is only available for staff users"
            )
        from app.utils.staff_hierarchy import get_recursive_downline, has_direct_reports
        if not has_direct_reports(user_id, db, StaffEmployee):
            raise HTTPException(
                status_code=403,
                detail="Team segment requires having direct reports (be a reporting manager)"
            )
        
        # Check hierarchy level for full vs direct downline
        user_hierarchy_level = 0
        if hasattr(current_user, 'role') and current_user.role:
            user_hierarchy_level = getattr(current_user.role, 'hierarchy_level', 0) or 0
        
        # Supreme (150) and Key Leadership (100+) get full recursive downline
        # Others get direct reports only (max_depth=1)
        if user_hierarchy_level >= 100:
            downline_ids = get_recursive_downline(user_id, db, StaffEmployee, include_manager=False)
        else:
            downline_ids = get_recursive_downline(user_id, db, StaffEmployee, max_depth=1, include_manager=False)
        hidden_ids = _get_hidden_employee_ids(db, StaffEmployee)
        downline_ids = [eid for eid in downline_ids if eid not in hidden_ids]
        if downline_ids:
            downline_employees = db.query(StaffEmployee).filter(
                StaffEmployee.id.in_(downline_ids)
            ).all()
            downline_ids_list = [emp.id for emp in downline_employees]
            query = query.filter(
                or_(
                    CRMLead.telecaller_id.in_(downline_ids_list),
                    CRMLead.field_staff_id.in_(downline_ids_list),
                    and_(
                        CRMLead.primary_owner_type == 'staff',
                        CRMLead.primary_owner_id.in_(downline_ids_list)
                    )
                )
            )
        else:
            query = query.filter(CRMLead.id == None)
    
    if status:
        if status == 'closed':
            query = query.filter(CRMLead.status.in_(['won', 'lost']))
        else:
            query = query.filter(CRMLead.status == status)
    if priority:
        query = query.filter(CRMLead.priority == priority)
    # DC Protocol (Jul 2026 Task 11): Category filter — dual-match logic for both string name and integer ID.
    if category or category_id is not None:
        _cat_ids = []
        if category_id is not None:
            _cat_ids.append(category_id)
        if category:
            if isinstance(category, int) or (isinstance(category, str) and category.isdigit()):
                _cat_ids.append(int(category))
            else:
                _matched_cats = db.query(SignupCategory.id).filter(
                    or_(
                        SignupCategory.name.ilike(category),
                        SignupCategory.name.ilike(f"%{category}%"),
                        SignupCategory.slug.ilike(category)
                    )
                ).all()
                _cat_ids.extend([r.id for r in _matched_cats])

        _cat_ids = list(set(_cat_ids))
        if _cat_ids:
            _deal_lead_sq = (
                db.query(CRMLeadDeal.lead_id)
                .filter(CRMLeadDeal.revenue_category_id.in_(_cat_ids))
                .scalar_subquery()
            )
            query = query.filter(or_(
                CRMLead.category_id.in_(_cat_ids),
                CRMLead.id.in_(_deal_lead_sq)
            ))
        else:
            query = query.filter(CRMLead.id == -1)
    if search:
        _st = f'%{search}%'
        _sc = [
            CRMLead.name.ilike(_st),
            CRMLead.email.ilike(_st),
            CRMLead.phone.ilike(_st),
            CRMLead.city.ilike(_st),
            CRMLead.pincode.ilike(_st),
            CRMLead.source.ilike(_st),
            CRMLead.application_no.ilike(_st),
            CRMLead.source_ref_name.ilike(_st),
            CRMLead.source_ref_id.ilike(_st),
            CRMLead.mnr_handler_id.ilike(_st),
        ]
        _id_s = search.lstrip('#').strip()
        if _id_s.isdigit():
            _sc.append(CRMLead.id == int(_id_s))
        _mnr_uid_s = [str(u.id) for u in db.query(User.id).filter(User.name.ilike(_st)).all()]
        if _mnr_uid_s:
            _sc.append(CRMLead.mnr_handler_id.in_(_mnr_uid_s))
        query = query.filter(or_(*_sc))

    # DC Protocol (Apr 2026): Followup quick-filter — today or overdue
    if followup_filter == 'today':
        from datetime import date as _date
        _today = _date.today()
        query = query.filter(
            CRMLead.next_followup_date != None,
            CRMLead.next_followup_date == _today
        )
    elif followup_filter == 'overdue':
        from datetime import date as _date
        _today = _date.today()
        query = query.filter(
            CRMLead.next_followup_date != None,
            CRMLead.next_followup_date < _today,
            CRMLead.status.notin_(['won', 'lost'])
        )

    # Month / Year filter on updated_at (IST naive)
    if month and year:
        query = query.filter(
            extract('month', CRMLead.updated_at) == month,
            extract('year', CRMLead.updated_at) == year
        )
    elif year:
        query = query.filter(extract('year', CRMLead.updated_at) == year)
    elif month:
        query = query.filter(extract('month', CRMLead.updated_at) == month)

    # DC Protocol N003 — derived handler type filter (DB-level approximation)
    if handler_type:
        if handler_type == 'Walk-In':
            query = query.filter(CRMLead.source.ilike('%walk%'))
        elif handler_type == 'VGK4U':
            query = query.filter(
                or_(CRMLead.is_vgk_program == True,
                    CRMLead.source_ref_type.ilike('vgk'))
            )
        elif handler_type == 'Showroom':
            query = query.filter(
                or_(CRMLead.source.ilike('%showroom%'),
                    CRMLead.showroom_supported == True)
            )
        elif handler_type == 'Direct':
            query = query.filter(
                ~CRMLead.source.ilike('%walk%'),
                CRMLead.is_vgk_program != True,
                ~CRMLead.source_ref_type.ilike('vgk'),
                ~CRMLead.source.ilike('%showroom%'),
                CRMLead.showroom_supported != True
            )

    total = query.count()
    logger.info(f"[DEBUG-LEADS] Final query total count: {total}")
    # Sort support (T003 — DC Protocol Mar 2026)
    from sqlalchemy import asc as _asc, desc as _desc
    _sort_col_map = {
        'created_at': CRMLead.created_at,
        'updated_at': CRMLead.updated_at,
        'next_followup_date': CRMLead.next_followup_date,
        'deal_value_total': CRMLead.deal_value_total,
        'deal_value_received': CRMLead.deal_value_received,
    }
    _sort_col = _sort_col_map.get(sort_by, CRMLead.updated_at) if sort_by else CRMLead.updated_at
    _order_fn = _desc if (sort_dir or 'desc') == 'desc' else _asc
    leads = query.order_by(_order_fn(_sort_col)).offset((page - 1) * per_page).limit(per_page).all()
    
    leads_data = []
    for lead in leads:
        lead_dict = lead.to_dict()

        # DC Protocol N003 — include derived handler type in list response
        try:
            lead_dict['lead_handler_type'] = _derive_lead_handler_type(lead)
        except Exception:
            lead_dict['lead_handler_type'] = 'Direct'
        
        category = db.query(SignupCategory).filter(SignupCategory.id == lead.category_id).first()
        lead_dict['category_name'] = category.name if category else None
        
        if lead.mnr_handler_id:
            handler = db.query(User).filter(User.id == lead.mnr_handler_id).first()
            lead_dict['mnr_handler_name'] = handler.name if handler else None
        
        if lead.guru_id:
            guru = db.query(User).filter(User.id == lead.guru_id).first()
            lead_dict['guru_name'] = guru.name if guru else None
        
        if lead.adi_guru_id:
            adi_guru = db.query(User).filter(User.id == lead.adi_guru_id).first()
            lead_dict['adi_guru_name'] = adi_guru.name if adi_guru else None
        
        leads_data.append(lead_dict)
    
    # DC Protocol (Apr 2026): Compute per-segment counts for partner 5-tab badges
    segment_counts = None
    if is_partner_user:
        # DC Protocol (Apr 2026 Fix): Include showroom/source_ref leads in source count
        _sc_src = db.query(CRMLead).filter(
            or_(CRMLead.associated_partner_id == user_id,
                and_(CRMLead.created_by_type == 'partner', CRMLead.created_by_id == user_id_str),
                and_(CRMLead.source_ref_type.in_(('partner', 'vgk_partner')), CRMLead.source_ref_id == user_id_str))
        ).count()
        _sc_supp = db.query(CRMLead).filter(CRMLead.vgk_field_support_id == user_id).count()
        logger.info(f"[DEBUG-LEADS] _sc_src={_sc_src}")
        _guru_all_rows = db.execute(
            text("SELECT DISTINCT source_lead_id FROM vgk_team_income_entries "
                 "WHERE partner_id=:pid AND level IN (2,3) AND source_lead_id IS NOT NULL"),
            {"pid": user_id}
        ).fetchall()
        _guru2_ids = [r[0] for r in db.execute(
            text("SELECT DISTINCT source_lead_id FROM vgk_team_income_entries "
                 "WHERE partner_id=:pid AND level=2 AND source_lead_id IS NOT NULL"),
            {"pid": user_id}
        ).fetchall()]
        _guru3_ids = [r[0] for r in db.execute(
            text("SELECT DISTINCT source_lead_id FROM vgk_team_income_entries "
                 "WHERE partner_id=:pid AND level=3 AND source_lead_id IS NOT NULL"),
            {"pid": user_id}
        ).fetchall()]
        _all_overall = list(set([r[0] for r in _guru_all_rows] + _guru2_ids + _guru3_ids +
                                [r[0] for r in db.query(CRMLead.id).filter(
                                    or_(CRMLead.associated_partner_id == user_id,
                                        CRMLead.vgk_field_support_id == user_id)).all()]))
        # DC Protocol (Apr 2026 Fix): Won deals count from source leads
        _won_count = db.query(CRMLead).filter(
            or_(CRMLead.associated_partner_id == user_id,
                and_(CRMLead.created_by_type == 'partner', CRMLead.created_by_id == user_id_str),
                and_(CRMLead.source_ref_type.in_(('partner', 'vgk_partner')), CRMLead.source_ref_id == user_id_str)),
            CRMLead.status == 'won'
        ).count()
        segment_counts = {
            'source': _sc_src,
            'guru': len(_guru2_ids),
            'zguru': len(_guru3_ids),
            'support': _sc_supp,
            'overall': len(_all_overall),
        }

    # DC Protocol (Apr 2026 Fix): Build 'stats' key for partner portal stat cards
    # Frontend was reading data.stats but only data.segment_counts existed — now both present.
    _stats = None
    if is_partner_user and segment_counts:
        _stats = {
            'my_leads': segment_counts.get('source', 0),
            'assigned_leads': segment_counts.get('support', 0),
            'won_deals': _won_count if is_partner_user else 0,
        }

    return {
        'success': True,
        'data': leads_data,
        'user_type': user_type,
        'user_id': user_id,
        'segment': segment,
        'segment_counts': segment_counts,
        'stats': _stats,
        'total': total,
        'page': page,
        'per_page': per_page,
        'pagination': {
            'page': page,
            'per_page': per_page,
            'total': total,
            'pages': (total + per_page - 1) // per_page if per_page > 0 else 0
        }
    }


@router.post("/unified-my-leads/claim/{lead_id}")
async def claim_fresh_lead(
    request: Request,
    lead_id: int,
    role: Optional[str] = Query(None, description="Role hint: 'mnr' to prioritize MNR session"),
    db: Session = Depends(get_db)
):
    """
    Claim a fresh lead as MNR handler.
    DC Protocol: Sets mnr_handler_id and primary_owner for the lead.
    DC Protocol (Dec 31, 2025): Added role hint for MNR session priority.
    """
    from app.core.security import get_current_mnr_user_from_hybrid, get_current_user_hybrid
    
    # DC Protocol: Role-based session priority
    if role == 'mnr':
        try:
            current_user = await get_current_mnr_user_from_hybrid(request, db)
        except HTTPException as e:
            if e.status_code == 401:
                current_user = await get_current_user_hybrid(request, db)
            else:
                raise e
    else:
        current_user = await get_current_user_hybrid(request, db)
    
    lead = db.query(CRMLead).filter(CRMLead.id == lead_id).first()
    
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    if lead.mnr_handler_id or lead.telecaller_id or lead.field_staff_id:
        raise HTTPException(status_code=400, detail="Lead is already assigned")
    
    lead.mnr_handler_id = current_user.id
    lead.handler_type = 'member'
    lead.handler_id = current_user.id
    lead.primary_owner_type = 'mnr'
    lead.primary_owner_id = current_user.id
    # DC Protocol (Apr 2026): Do NOT auto-change status on claim — preserve original status
    # lead.status = 'contacted' if lead.status == 'new' else lead.status  # REMOVED
    lead.updated_at = get_indian_time()
    
    if current_user.referrer_id:
        lead.guru_id = current_user.referrer_id
    
    db.add(CRMLeadAssignment(
        company_id=lead.company_id,
        lead_id=lead.id,
        assigned_to_type='member',
        assigned_to_id=current_user.id,
        assigned_by_type='member',
        assigned_by_id=current_user.id,
        notes='Self-claimed from fresh leads'
    ))
    
    db.commit()
    db.refresh(lead)
    
    return {
        'success': True,
        'message': 'Lead claimed successfully',
        'data': lead.to_dict()
    }


@router.get("/unified-my-leads/{lead_id}/details")
async def get_unified_lead_details(
    request: Request,
    lead_id: int,
    company_id: Optional[int] = Query(None, description="Company ID for DC Protocol"),
    role: Optional[str] = Query(None, description="Role hint: 'mnr' to prioritize MNR session"),
    db: Session = Depends(get_db)
):
    """
    DC Protocol (Dec 31, 2025): Unified lead details endpoint.
    Works for Staff, MNR, and Partner users with proper RBAC validation.
    Returns full lead details only if the user owns or is assigned to the lead.
    DC Protocol (Dec 31, 2025): Added role hint for MNR session priority.
    """
    from app.models.staff import StaffEmployee
    from app.models.staff_accounts import OfficialPartner
    from app.core.security import get_current_mnr_user_from_hybrid, get_current_user_hybrid_with_partner
    
    # DC Protocol: Role-based session priority
    if role == 'mnr':
        try:
            current_user = await get_current_mnr_user_from_hybrid(request, db)
        except HTTPException as e:
            if e.status_code == 401:
                current_user = await get_current_user_hybrid_with_partner(request, db)
            else:
                raise e
    elif role == 'partner':
        # DC-VGK-PARTNER-SYNC-001: VGK-portal partner JWT (user_type='vgk_member')
        # is not recognized by hybrid_with_partner; try vgk_member auth first.
        from app.api.v1.endpoints.vgk_auth import get_current_vgk_member
        try:
            current_user = get_current_vgk_member(request, db)
        except HTTPException as e:
            if e.status_code == 401:
                current_user = await get_current_user_hybrid_with_partner(request, db)
            else:
                raise e
    else:
        current_user = await get_current_user_hybrid_with_partner(request, db)
    
    user_id = current_user.id
    user_id_str = str(user_id)
    
    is_staff = isinstance(current_user, StaffEmployee)
    is_partner = isinstance(current_user, OfficialPartner)
    
    query = db.query(CRMLead).filter(CRMLead.id == lead_id)
    if company_id:
        query = query.filter(CRMLead.company_id == company_id)
    
    lead = query.first()
    
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    has_access = False
    if is_staff:
        has_access = (
            lead.telecaller_id == user_id or
            lead.field_staff_id == user_id or
            (lead.primary_owner_type == 'staff' and lead.primary_owner_id == user_id) or
            (lead.created_by_type == 'staff' and lead.created_by_id == current_user.emp_code)
        )
    elif is_partner:
        has_access = (
            lead.associated_partner_id == user_id or
            lead.team_senior_partner_id == user_id or
            lead.team_extended_partner_id == user_id or
            lead.team_core_partner_id == user_id or
            lead.vgk_field_support_id == user_id or
            (lead.primary_owner_type == 'partner' and lead.primary_owner_id == user_id) or
            (lead.created_by_type == 'partner' and lead.created_by_id == user_id_str) or
            (lead.source_ref_type in ('partner', 'vgk_partner') and lead.source_ref_id == user_id_str)
        )
        if not has_access:
            from sqlalchemy import text
            # Legacy L2/L3/L4 support check
            legacy_auth = db.execute(
                text("SELECT 1 FROM vgk_team_income_entries WHERE partner_id=:pid AND source_lead_id=:lid LIMIT 1"),
                {"pid": user_id, "lid": lead.id}
            ).scalar()
            if legacy_auth:
                has_access = True
    else:
        # DC Protocol (Dec 31, 2025): primary_owner_id is Integer - NOT for MNR string IDs
        # MNR access via mnr_handler_id (VARCHAR) or created_by fields
        has_access = (
            lead.mnr_handler_id == user_id or
            (lead.created_by_type == 'member' and lead.created_by_id == user_id_str)
        )
    
    if not has_access:
        raise HTTPException(status_code=403, detail="You do not have access to this lead")
    
    lead_dict = lead.to_dict()
    
    category = db.query(SignupCategory).filter(SignupCategory.id == lead.category_id).first()
    lead_dict['category_name'] = category.name if category else None
    
    if lead.telecaller_id:
        telecaller = db.query(StaffEmployee).filter(StaffEmployee.id == lead.telecaller_id).first()
        if telecaller:
            lead_dict['telecaller_name'] = telecaller.full_name or telecaller.emp_code
            lead_dict['telecaller_code'] = telecaller.emp_code
    
    if lead.field_staff_id:
        field_staff = db.query(StaffEmployee).filter(StaffEmployee.id == lead.field_staff_id).first()
        if field_staff:
            lead_dict['field_staff_name'] = field_staff.full_name or field_staff.emp_code
            lead_dict['field_staff_code'] = field_staff.emp_code
    
    if lead.associated_partner_id:
        partner = db.query(OfficialPartner).filter(OfficialPartner.id == lead.associated_partner_id).first()
        if partner:
            lead_dict['partner_name'] = partner.partner_name
            lead_dict['partner_code'] = partner.partner_code
    
    if lead.mnr_handler_id:
        handler = db.query(User).filter(User.id == lead.mnr_handler_id).first()
        if handler:
            lead_dict['mnr_handler_name'] = handler.name
            lead_dict['mnr_handler_mnr_id'] = handler.id
    
    if lead.guru_id:
        guru = db.query(User).filter(User.id == lead.guru_id).first()
        if guru:
            lead_dict['guru_name'] = guru.name
            lead_dict['guru_mnr_id'] = guru.id
    
    if lead.adi_guru_id:
        adi_guru = db.query(User).filter(User.id == lead.adi_guru_id).first()
        if adi_guru:
            lead_dict['adi_guru_name'] = adi_guru.name
            lead_dict['adi_guru_mnr_id'] = adi_guru.id

    if lead.z_guru_id:
        z_guru_user = db.query(User).filter(User.id == lead.z_guru_id).first()
        if z_guru_user:
            lead_dict['z_guru_name'] = z_guru_user.name
            lead_dict['z_guru_mnr_id'] = z_guru_user.id

    if lead.vgk_field_support_id:
        vgk_fs = db.query(OfficialPartner).filter(OfficialPartner.id == lead.vgk_field_support_id).first()
        if vgk_fs:
            lead_dict['vgk_field_support_name'] = vgk_fs.partner_name
            lead_dict['vgk_field_support_code'] = vgk_fs.partner_code

    follow_ups = db.query(CRMLeadFollowUp).filter(
        CRMLeadFollowUp.lead_id == lead_id
    ).order_by(CRMLeadFollowUp.scheduled_date.desc()).all()
    lead_dict['follow_ups'] = [fu.to_dict() for fu in follow_ups]
    
    notes = db.query(CRMLeadNote).filter(
        CRMLeadNote.lead_id == lead_id
    ).order_by(CRMLeadNote.created_at.desc()).all()
    lead_dict['notes'] = [note.to_dict() for note in notes]
    
    return {
        'success': True,
        'data': lead_dict
    }


@router.put("/leads/{lead_id}/mnr-assignment")
async def update_lead_mnr_assignment(
    lead_id: int,
    mnr_handler_id: Optional[str] = Body(None),
    guru_id: Optional[str] = Body(None),
    z_guru_id: Optional[str] = Body(None),
    adi_guru_id: Optional[str] = Body(None),
    db: Session = Depends(get_db),
    current_employee: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Update MNR handler, Guru, and Adi Guru for a lead.
    DC Protocol: Staff can assign MNR handlers to leads.
    Guru auto-defaults to MNR handler's sponsor if not specified.
    """
    lead = db.query(CRMLead).filter(CRMLead.id == lead_id).first()
    
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    if mnr_handler_id is not None:
        if mnr_handler_id:
            handler = db.query(User).filter(User.id == mnr_handler_id).first()
            if not handler:
                raise HTTPException(status_code=400, detail="MNR user not found")
            lead.mnr_handler_id = mnr_handler_id
            lead.handler_type = 'member'
            lead.handler_id = mnr_handler_id
            
            if guru_id is None and handler.referrer_id:
                lead.guru_id = handler.referrer_id
                _guru = db.query(User).filter(User.id == handler.referrer_id).first()
                if _guru and _guru.referrer_id:
                    _zguru = db.query(User).filter(User.id == _guru.referrer_id).first()
                    if _zguru:
                        if z_guru_id is None:
                            lead.z_guru_id = _zguru.id
                        if _zguru.referrer_id:
                            _adiguru = db.query(User).filter(User.id == _zguru.referrer_id).first()
                            if _adiguru:
                                if adi_guru_id is None:
                                    lead.adi_guru_id = _adiguru.id
        else:
            lead.mnr_handler_id = None
            if lead.handler_type == 'member':
                lead.handler_type = 'unassigned'
                lead.handler_id = None
    
    if guru_id is not None:
        if guru_id:
            guru = db.query(User).filter(User.id == guru_id).first()
            if not guru:
                raise HTTPException(status_code=400, detail="Guru user not found")
        lead.guru_id = guru_id if guru_id else None
    
    if z_guru_id is not None:
        lead.z_guru_id = z_guru_id if z_guru_id else None
    
    if adi_guru_id is not None:
        if adi_guru_id:
            adi_guru = db.query(User).filter(User.id == adi_guru_id).first()
            if not adi_guru:
                raise HTTPException(status_code=400, detail="Adi Guru user not found")
        lead.adi_guru_id = adi_guru_id if adi_guru_id else None
    
    lead.updated_at = get_indian_time()
    db.commit()
    db.refresh(lead)
    
    result = lead.to_dict()
    if lead.mnr_handler_id:
        handler = db.query(User).filter(User.id == lead.mnr_handler_id).first()
        result['mnr_handler_name'] = handler.name if handler else None
    if lead.guru_id:
        guru = db.query(User).filter(User.id == lead.guru_id).first()
        result['guru_name'] = guru.name if guru else None
    if lead.z_guru_id:
        z_guru = db.query(User).filter(User.id == lead.z_guru_id).first()
        result['z_guru_name'] = z_guru.name if z_guru else None
    if lead.adi_guru_id:
        adi_guru = db.query(User).filter(User.id == lead.adi_guru_id).first()
        result['adi_guru_name'] = adi_guru.name if adi_guru else None
    
    return {
        'success': True,
        'message': 'MNR assignment updated successfully',
        'data': result
    }


@router.post("/unified-my-leads")
async def create_lead_unified(
    request: Request,
    lead_data: LeadCreate = Body(...),
    role: Optional[str] = Query(None, description="Role hint: 'mnr' to prioritize MNR session"),
    db: Session = Depends(get_db)
):
    """
    Create a lead from My Leads page.
    DC Protocol: MNR users can create leads without company_id (shows as fresh lead to staff).
    Staff users must provide company_id and can assign telecaller, field_staff, vendor.
    Supports both StaffEmployee and User (MNR) authentication.
    DC Protocol (Dec 31, 2025): Added role hint for MNR session priority.
    """
    from app.core.security import get_current_mnr_user_from_hybrid, get_current_user_hybrid
    
    # DC Protocol: Role-based session priority
    if role == 'mnr':
        try:
            current_user = await get_current_mnr_user_from_hybrid(request, db)
        except HTTPException as e:
            if e.status_code == 401:
                current_user = await get_current_user_hybrid(request, db)
            else:
                raise e
    else:
        current_user = await get_current_user_hybrid(request, db)
    
    # Check if staff user (StaffEmployee has emp_code attribute, User does not)
    is_staff = hasattr(current_user, 'emp_code') and current_user.emp_code
    user_type = 'staff' if is_staff else 'member'
    # For staff: use emp_code as identifier (consistent with existing ownership logic)
    # For MNR: use user ID
    user_id = current_user.emp_code if is_staff else current_user.id
    
    company_id = lead_data.company_id
    
    # DC Protocol: company_id is required in database (nullable=False)
    # For MNR users without company_id, use default company (MNR - id=4)
    # For staff users, use their base_company_id as fallback
    if not company_id:
        if user_type == 'member':
            # Default to MNR company (company_id=4) for member-created leads
            from app.models.company import AssociatedCompany
            mnr_company = db.query(AssociatedCompany).filter(
                AssociatedCompany.name.ilike('%MNR%')
            ).first()
            company_id = mnr_company.id if mnr_company else 4
        elif is_staff and hasattr(current_user, 'base_company_id') and current_user.base_company_id:
            company_id = current_user.base_company_id
        else:
            # Fallback to first active company
            from app.models.company import AssociatedCompany
            first_company = db.query(AssociatedCompany).filter(
                AssociatedCompany.is_active == True
            ).first()
            company_id = first_company.id if first_company else 1

    # DC-DEDUP-002: Block creation when phone/alternate_phone already exists in CRM.
    if lead_data.phone or lead_data.alternate_phone:
        _dup_lead, _dup_owner, _dup_active = _resolve_phone_duplicate(
            lead_data.phone, lead_data.alternate_phone, db
        )
        if _dup_lead:
            _dup_owner_name = _dup_owner_status = None
            if _dup_owner:
                _dup_owner_name = f"{_dup_owner.first_name or ''} {_dup_owner.last_name or ''}".strip() or _dup_owner.emp_code
                _dup_owner_status = _dup_owner.status
            raise HTTPException(
                status_code=409,
                detail={
                    "type": "duplicate_lead",
                    "message": f"Mobile number already exists in Lead #{_dup_lead.id} ({_dup_lead.name or 'Unnamed'}).",
                    "lead_id": _dup_lead.id,
                    "lead_name": _dup_lead.name or "",
                    "lead_status": _dup_lead.status,
                    "lead_company_id": _dup_lead.company_id,
                    "owner_name": _dup_owner_name,
                    "owner_status": _dup_owner_status,
                    "owner_active": _dup_active,
                    "lead": {
                        "id": _dup_lead.id,
                        "name": _dup_lead.name or "",
                        "phone": _dup_lead.phone or "",
                        "alternate_phone": _dup_lead.alternate_phone or "",
                        "status": _dup_lead.status,
                        "company_id": _dup_lead.company_id,
                    },
                    "owner": {
                        "id": _dup_owner.id if _dup_owner else None,
                        "name": _dup_owner_name,
                        "emp_code": _dup_owner.emp_code if _dup_owner else None,
                        "status": _dup_owner_status,
                    } if _dup_owner else None,
                }
            )

    new_lead = CRMLead(
        company_id=company_id,
        name=lead_data.name,
        phone=lead_data.phone,
        phone_primary_whatsapp=lead_data.phone_primary_whatsapp or False,
        alternate_phone=lead_data.alternate_phone,
        email=lead_data.email,
        category_id=lead_data.category_id,
        priority=lead_data.priority or 'medium',
        status=lead_data.status or 'new',
        source=lead_data.source,
        next_followup_date=lead_data.next_followup_date,
        pincode=lead_data.pincode,
        area=lead_data.area,
        city=lead_data.city,
        state=lead_data.state,
        budget_min=lead_data.budget_min,
        budget_max=lead_data.budget_max,
        looking_for=lead_data.looking_for,
        description=lead_data.description,
        mnr_handler_id=lead_data.mnr_handler_id,
        guru_id=lead_data.guru_id,
        adi_guru_id=lead_data.adi_guru_id,
        handler_type='member' if user_type == 'member' else 'staff',
        handler_id=user_id,
        primary_owner_type='mnr' if user_type == 'member' else 'staff',
        primary_owner_id=current_user.id if is_staff else None,  # DC Protocol: Integer for staff.id
        created_by_type=user_type,
        created_by_id=str(user_id),
        created_at=get_indian_time(),
        updated_at=get_indian_time()
    )
    
    # Staff users can assign telecaller, field_staff, partner, vendor
    if is_staff:
        if lead_data.telecaller_id:
            new_lead.telecaller_id = lead_data.telecaller_id
        if lead_data.field_staff_id:
            new_lead.field_staff_id = lead_data.field_staff_id
        if lead_data.associated_partner_id:
            new_lead.associated_partner_id = lead_data.associated_partner_id
        if lead_data.vendor_id:
            new_lead.vendor_id = lead_data.vendor_id
    
    if user_type == 'member':
        new_lead.mnr_handler_id = new_lead.mnr_handler_id or user_id
        if not new_lead.guru_id and hasattr(current_user, 'referrer_id') and current_user.referrer_id:
            new_lead.guru_id = current_user.referrer_id
    
    db.add(new_lead)
    db.commit()
    db.refresh(new_lead)
    
    return {
        'success': True,
        'message': 'Lead created successfully',
        'data': new_lead.to_dict()
    }


@router.get("/unified-my-leads/search-mnr")
async def search_mnr_users_unified(
    q: str = Query(..., min_length=2),
    company_id: Optional[int] = None,
    limit: int = Query(20, le=50),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
):
    """
    Search MNR users by ID or name for My Leads page.
    DC Protocol: Returns activated users within company scope.
    Staff users use base_company_id/data_companies for filtering.
    Supports both StaffEmployee and User (MNR) authentication.
    """
    import json
    
    # DC Protocol: Properly resolve company access for both MNR and Staff users
    accessible_company_ids = set()
    
    # Check if staff user (StaffEmployee has emp_code attribute, User does not)
    is_staff = hasattr(current_user, 'emp_code') and current_user.emp_code
    
    if is_staff:
        # Staff user: use base_company_id and data_companies
        if hasattr(current_user, 'base_company_id') and current_user.base_company_id:
            accessible_company_ids.add(int(current_user.base_company_id))
        if hasattr(current_user, 'data_companies') and current_user.data_companies:
            data_companies = current_user.data_companies
            if isinstance(data_companies, str):
                try:
                    data_companies = json.loads(data_companies)
                except (json.JSONDecodeError, ValueError):
                    data_companies = []
            if isinstance(data_companies, list):
                for cid in data_companies:
                    if cid is not None:
                        try:
                            accessible_company_ids.add(int(cid))
                        except (ValueError, TypeError):
                            pass
    else:
        # MNR user: use company_id from user object
        user_company_id = getattr(current_user, 'company_id', None)
        if user_company_id:
            accessible_company_ids.add(int(user_company_id))
    
    # DC Protocol: For staff with no company config, allow access to all companies (VGK level)
    # This handles VGK Supreme users who may have empty data_companies but full access
    if is_staff and not accessible_company_ids:
        # Get all company IDs from the database for VGK level access
        from app.models.company import AssociatedCompany
        all_companies = db.query(AssociatedCompany.id).filter(AssociatedCompany.is_active == True).all()
        accessible_company_ids = {c.id for c in all_companies}
    
    # DC Protocol: MNR users require company_id
    if not is_staff and not accessible_company_ids:
        raise HTTPException(status_code=403, detail="No company access configured")
    
    # DC Protocol: Validate explicit company_id parameter against accessible companies
    if company_id and accessible_company_ids:
        if company_id not in accessible_company_ids:
            raise HTTPException(status_code=403, detail="Company access denied")
        accessible_company_ids = {company_id}
    
    search_term = f"%{q}%"
    # DC Protocol: Search by MNR ID, name, or phone, include inactive with status indicator
    query = db.query(User).filter(
        or_(
            User.id.ilike(search_term),
            User.name.ilike(search_term),
            User.phone_number.ilike(search_term)
        )
    )
    
    # DC Protocol: MNR users are global (no company_id in User model)
    # Company filtering not applicable for MNR user search
    
    users = query.order_by(User.name).limit(limit).all()
    
    return {
        'success': True,
        'data': [
            {
                'id': u.id,
                'name': u.name,
                'full_name': u.name,
                'phone': u.phone_number,
                'is_active': u.activation_date is not None,
                'status': 'Active' if u.activation_date is not None else 'Inactive'
            }
            for u in users
        ]
    }


@router.get("/unified-my-leads/upline/{mnr_id}")
async def get_mnr_upline(
    mnr_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
):
    """
    Get Guru (sponsor) and Adi Guru (sponsor's sponsor) for an MNR user.
    DC Protocol: Used to auto-populate upline fields when assigning MNR handler.
    Supports both StaffEmployee and User (MNR) authentication.
    """
    import json
    
    user = db.query(User).filter(User.id == mnr_id).first()

    if not user:
        # DC-INLINE-GURU-001: Also try VGK OfficialPartner lookup (selId is partner.id as int)
        try:
            _vgk_op = db.query(OfficialPartner).filter(OfficialPartner.id == int(mnr_id)).first()
        except (ValueError, TypeError):
            _vgk_op = None
        if _vgk_op:
            vgk_result = {'guru': None, 'adi_guru': None, 'core': None}
            if _vgk_op.parent_partner_id:
                _p1 = db.query(OfficialPartner).filter(OfficialPartner.id == _vgk_op.parent_partner_id).first()
                if _p1:
                    vgk_result['guru'] = {
                        'id': str(_p1.id),
                        'name': getattr(_p1, 'partner_name', None) or _p1.partner_code,
                        'partner_id': _p1.id
                    }
                    if _p1.parent_partner_id:
                        _p2 = db.query(OfficialPartner).filter(OfficialPartner.id == _p1.parent_partner_id).first()
                        if _p2:
                            vgk_result['adi_guru'] = {
                                'id': str(_p2.id),
                                'name': getattr(_p2, 'partner_name', None) or _p2.partner_code,
                                'partner_id': _p2.id
                            }
                            if _p2.parent_partner_id:
                                _p3 = db.query(OfficialPartner).filter(OfficialPartner.id == _p2.parent_partner_id).first()
                                if _p3:
                                    vgk_result['core'] = {
                                        'id': str(_p3.id),
                                        'name': getattr(_p3, 'partner_name', None) or _p3.partner_code,
                                        'partner_id': _p3.id
                                    }
            return {'success': True, 'data': vgk_result, 'source': 'vgk'}
        raise HTTPException(status_code=404, detail="MNR user not found")
    
    # DC Protocol: Properly resolve company access for both MNR and Staff users
    accessible_company_ids = set()
    
    # Check if staff user (StaffEmployee has emp_code attribute, User does not)
    is_staff = hasattr(current_user, 'emp_code') and current_user.emp_code
    
    if is_staff:
        # Staff user: use base_company_id and data_companies
        if hasattr(current_user, 'base_company_id') and current_user.base_company_id:
            accessible_company_ids.add(int(current_user.base_company_id))
        if hasattr(current_user, 'data_companies') and current_user.data_companies:
            data_companies = current_user.data_companies
            if isinstance(data_companies, str):
                try:
                    data_companies = json.loads(data_companies)
                except (json.JSONDecodeError, ValueError):
                    data_companies = []
            if isinstance(data_companies, list):
                for cid in data_companies:
                    if cid is not None:
                        try:
                            accessible_company_ids.add(int(cid))
                        except (ValueError, TypeError):
                            pass
        # VGK level staff without company config get full access
        if not accessible_company_ids:
            from app.models.company import AssociatedCompany
            all_companies = db.query(AssociatedCompany.id).filter(AssociatedCompany.is_active == True).all()
            accessible_company_ids = {c.id for c in all_companies}
    else:
        # DC Protocol: MNR users are global - no company_id filtering needed
        # MNR members can access upline information for any MNR user
        pass
    
    # DC Protocol: MNR users are global, no company access check needed for upline lookup
    # This endpoint only returns sponsor relationship data, not company-sensitive data
    
    # DC-TEAM-ASSIGN-001 (Jun 2026): Extend from L2 (guru/adi_guru) to L4 (core)
    result = {'guru': None, 'adi_guru': None, 'core': None}
    
    if user.referrer_id:
        guru = db.query(User).filter(User.id == user.referrer_id).first()
        if guru:
            result['guru'] = {
                'id': guru.id,
                'name': guru.name,
                'phone': guru.phone_number
            }
            if guru.referrer_id:
                adi_guru = db.query(User).filter(User.id == guru.referrer_id).first()
                if adi_guru:
                    result['adi_guru'] = {
                        'id': adi_guru.id,
                        'name': adi_guru.name,
                        'phone': adi_guru.phone_number
                    }
                    # DC-TEAM-ASSIGN-001: Walk one more level to L4 Core
                    if adi_guru.referrer_id:
                        core_user = db.query(User).filter(User.id == adi_guru.referrer_id).first()
                        if core_user:
                            result['core'] = {
                                'id': core_user.id,
                                'name': core_user.name,
                                'phone': core_user.phone_number
                            }
    
    return {
        'success': True,
        'data': result
    }


@router.put("/unified-my-leads/{lead_id}/mnr-assignment")
async def update_unified_lead_mnr_assignment(
    request: Request,
    lead_id: int,
    role: Optional[str] = Query(None, description="Role hint: 'mnr' to prioritize MNR session"),
    status: Optional[str] = Body(None),
    mnr_handler_id: Optional[str] = Body(None),
    guru_id: Optional[str] = Body(None),
    adi_guru_id: Optional[str] = Body(None),
    db: Session = Depends(get_db)
):
    """
    Update status and MNR assignment for a lead from My Leads page.
    DC Protocol: MNR members can update their own leads.
    Supports both StaffEmployee and User (MNR) authentication.
    DC Protocol (Dec 31, 2025): Added role hint for MNR session priority.
    """
    from app.core.security import get_current_mnr_user_from_hybrid, get_current_user_hybrid
    
    # DC Protocol: Role-based session priority
    if role == 'mnr':
        try:
            current_user = await get_current_mnr_user_from_hybrid(request, db)
        except HTTPException as e:
            if e.status_code == 401:
                current_user = await get_current_user_hybrid(request, db)
            else:
                raise e
    else:
        current_user = await get_current_user_hybrid(request, db)
    
    lead = db.query(CRMLead).filter(CRMLead.id == lead_id).first()
    
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    # Check if staff user (StaffEmployee has emp_code attribute, User does not)
    is_staff = hasattr(current_user, 'emp_code') and current_user.emp_code
    user_type = 'staff' if is_staff else 'member'
    # For staff: use emp_code as identifier (consistent with existing ownership logic)
    # For MNR: use user ID
    user_id = current_user.emp_code if is_staff else current_user.id
    
    if user_type == 'member':
        # DC Protocol (Dec 31, 2025): RBAC check must match GET filter logic exactly
        # MNR users can edit leads where:
        # 1. They are the mnr_handler, OR
        # 2. They created the lead (created_by_type='member' AND created_by_id matches)
        # Note: primary_owner_id is Integer type - NOT for MNR string IDs
        is_mnr_handler = lead.mnr_handler_id == user_id
        is_creator = lead.created_by_type == 'member' and lead.created_by_id == str(user_id)
        if not is_mnr_handler and not is_creator:
            raise HTTPException(status_code=403, detail="You can only edit your own leads")
    
    if status:
        lead.status = status
    
    if mnr_handler_id is not None:
        if mnr_handler_id:
            handler = db.query(User).filter(User.id == mnr_handler_id).first()
            if not handler:
                raise HTTPException(status_code=400, detail="MNR user not found")
            lead.mnr_handler_id = mnr_handler_id
            lead.handler_type = 'member'
            lead.handler_id = mnr_handler_id
        else:
            lead.mnr_handler_id = None
    
    if guru_id is not None:
        lead.guru_id = guru_id if guru_id else None
    
    if adi_guru_id is not None:
        lead.adi_guru_id = adi_guru_id if adi_guru_id else None
    
    lead.updated_at = get_indian_time()
    db.commit()
    db.refresh(lead)
    
    result = lead.to_dict()
    if lead.mnr_handler_id:
        handler = db.query(User).filter(User.id == lead.mnr_handler_id).first()
        result['mnr_handler_name'] = handler.name if handler else None
    if lead.guru_id:
        guru = db.query(User).filter(User.id == lead.guru_id).first()
        result['guru_name'] = guru.name if guru else None
    if lead.adi_guru_id:
        adi_guru = db.query(User).filter(User.id == lead.adi_guru_id).first()
        result['adi_guru_name'] = adi_guru.name if adi_guru else None
    
    return {
        'success': True,
        'message': 'Lead updated successfully',
        'data': result
    }


@router.put("/unified-my-leads/{lead_id}/full-update")
async def update_lead_full(
    lead_id: int,
    company_id: int = Query(..., description="Company ID - must match lead's current company"),
    status: Optional[str] = Body(None),
    name: Optional[str] = Body(None),
    phone: Optional[str] = Body(None),
    email: Optional[str] = Body(None),
    priority: Optional[str] = Body(None),
    source: Optional[str] = Body(None),
    next_followup_date: Optional[str] = Body(None),
    description: Optional[str] = Body(None),
    looking_for: Optional[str] = Body(None),
    recent_comments: Optional[str] = Body(None),
    city: Optional[str] = Body(None),
    area: Optional[str] = Body(None),
    state: Optional[str] = Body(None),
    pincode: Optional[str] = Body(None),
    budget_min: Optional[float] = Body(None),
    budget_max: Optional[float] = Body(None),
    category_id: Optional[int] = Body(None),
    mnr_handler_id: Optional[str] = Body(None),
    guru_id: Optional[str] = Body(None),
    z_guru_id: Optional[str] = Body(None),
    adi_guru_id: Optional[str] = Body(None),
    team_senior_partner_id: Optional[int] = Body(None),
    team_extended_partner_id: Optional[int] = Body(None),
    team_core_partner_id: Optional[int] = Body(None),
    source_ref_type: Optional[str] = Body(None),
    source_ref_id: Optional[str] = Body(None),
    source_ref_name: Optional[str] = Body(None),
    field_support_ref_type: Optional[str] = Body(None),
    field_support_ref_id: Optional[str] = Body(None),
    field_support_ref_name: Optional[str] = Body(None),
    technical_id: Optional[int] = Body(None),
    support_staff_id: Optional[int] = Body(None),
    technical_staff1_id: Optional[int] = Body(None),
    support_staff_supported: Optional[bool] = Body(None),
    technical_staff1_supported: Optional[bool] = Body(None),
    telecaller_id: Optional[int] = Body(None),
    field_staff_id: Optional[int] = Body(None),
    associated_partner_id: Optional[int] = Body(None),
    deal_value_total: Optional[float] = Body(None),
    deal_value_received: Optional[float] = Body(None),
    deal_value_balance: Optional[float] = Body(None),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
):
    """
    DC Protocol (Dec 31, 2025): Full lead update endpoint for unified CRM Lead Editor.
    Updates all assignment fields: MNR Handler, Guru, Adi Guru, Tele Caller, Field Staff, Partner.
    Also updates lead details, next follow-up date, and deal values.
    """
    from app.models.staff import StaffEmployee
    
    # DC Protocol (Jan 23, 2026): Query by lead_id only, validate company separately
    lead = db.query(CRMLead).filter(CRMLead.id == lead_id).first()
    
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    # DC Protocol: Validate company_id matches lead's current company
    if lead.company_id != company_id:
        raise HTTPException(
            status_code=400, 
            detail=f"Company mismatch: Lead belongs to company {lead.company_id}, but request specified company {company_id}"
        )
    
    is_staff = isinstance(current_user, StaffEmployee)
    is_partner = hasattr(current_user, 'partner_code')  # or isinstance(current_user, OfficialPartner)
    
    # DC Protocol (Dec 31, 2025): Proper RBAC checks for both staff and MNR users
    # DC Protocol (Jan 2026): Added team leader authority check
    if is_staff:
        staff_id = current_user.id
        
        # Check 1: Direct ownership
        is_owner = (
            lead.telecaller_id == staff_id or
            lead.field_staff_id == staff_id or
            (lead.primary_owner_type == 'staff' and lead.primary_owner_id == staff_id) or
            lead.created_by == current_user.emp_code
        )
        
        # Check 2: Team leader authority - can edit leads assigned to their direct reports
        # DC Protocol (Jan 2026): Check both telecaller AND field_staff independently
        # Also check both reporting_manager_id (int) and reporting_to (emp_code string) for compatibility
        is_team_leader = False
        if not is_owner:
            current_emp_code = current_user.emp_code
            
            # Check if telecaller reports to current user (via either field)
            if lead.telecaller_id:
                telecaller = db.query(StaffEmployee).filter(StaffEmployee.id == lead.telecaller_id).first()
                if telecaller and (telecaller.reporting_manager_id == staff_id or telecaller.reporting_to == current_emp_code):
                    is_team_leader = True
            
            # Also check if field_staff reports to current user (via either field)
            if not is_team_leader and lead.field_staff_id:
                field_staff = db.query(StaffEmployee).filter(StaffEmployee.id == lead.field_staff_id).first()
                if field_staff and (field_staff.reporting_manager_id == staff_id or field_staff.reporting_to == current_emp_code):
                    is_team_leader = True
        
        if not is_owner and not is_team_leader:
            raise HTTPException(status_code=403, detail="You can only edit leads assigned to you or your team members")
    elif is_partner:
        user_id_str = str(current_user.id)
        has_access = (
            lead.associated_partner_id == current_user.id or
            lead.team_senior_partner_id == current_user.id or
            lead.team_extended_partner_id == current_user.id or
            lead.team_core_partner_id == current_user.id or
            lead.vgk_field_support_id == current_user.id or
            (lead.primary_owner_type == 'partner' and lead.primary_owner_id == current_user.id) or
            (lead.created_by_type == 'partner' and lead.created_by_id == user_id_str) or
            (lead.source_ref_type in ('partner', 'vgk_partner') and lead.source_ref_id == user_id_str)
        )
        if not has_access:
            from sqlalchemy import text
            # Legacy L2/L3/L4 support check
            legacy_auth = db.execute(
                text("SELECT 1 FROM vgk_team_income_entries WHERE partner_id=:pid AND source_lead_id=:lid LIMIT 1"),
                {"pid": current_user.id, "lid": lead.id}
            ).scalar()
            if legacy_auth:
                has_access = True
        
        if not has_access:
            raise HTTPException(status_code=403, detail="You do not have access to this lead")
    else:
        # DC Protocol (Dec 31, 2025): MNR RBAC must match GET filter logic exactly
        # MNR users can edit leads where:
        # 1. They are the mnr_handler, OR
        # 2. They are the primary_owner (legacy leads), OR
        # 3. They created the lead (created_by_type='member' AND created_by_id matches)
        is_mnr_handler = lead.mnr_handler_id == current_user.id
        is_primary_owner = lead.primary_owner_type == 'mnr' and lead.primary_owner_id == current_user.id
        is_creator = lead.created_by_type == 'member' and lead.created_by_id == str(current_user.id)
        if not is_mnr_handler and not is_primary_owner and not is_creator:
            raise HTTPException(status_code=403, detail="You can only edit your own leads")
    
    _old_lead_status = lead.status
    # DC-HCI-001: snapshot old partner before any field assignments
    _full_pre_partner_id = lead.associated_partner_id

    if status is not None:
        lead.status = status
    
    if name is not None:
        lead.name = name
    if phone is not None:
        lead.phone = phone
    if email is not None:
        lead.email = email if email else None
    if priority is not None:
        lead.priority = priority
    if source is not None:
        lead.source = source if source else None
    if next_followup_date is not None:
        if next_followup_date:
            try:
                from dateutil.parser import parse as dateutil_parse
                lead.next_followup_date = _to_ist_naive(dateutil_parse(next_followup_date))
            except (ValueError, ImportError):
                try:
                    lead.next_followup_date = _to_ist_naive(
                        datetime.fromisoformat(next_followup_date.replace('Z', '+00:00'))
                    )
                except ValueError:
                    raise HTTPException(status_code=400, detail="Invalid next_followup_date format")
        else:
            lead.next_followup_date = None
    if description is not None:
        lead.description = description if description else None
    if looking_for is not None:
        lead.looking_for = looking_for if looking_for else None
    if recent_comments is not None:
        lead.recent_comments = recent_comments if recent_comments else None
    if city is not None:
        lead.city = city if city else None
    if area is not None:
        lead.area = area if area else None
    if state is not None:
        lead.state = state if state else None
    if pincode is not None:
        lead.pincode = pincode if pincode else None
    if budget_min is not None:
        lead.budget_min = budget_min
    if budget_max is not None:
        lead.budget_max = budget_max
    if category_id is not None:
        if category_id:
            category = db.query(SignupCategory).filter(SignupCategory.id == category_id).first()
            if not category:
                raise HTTPException(status_code=400, detail="Invalid category")
        lead.category_id = category_id if category_id else None
    
    if mnr_handler_id is not None:
        if mnr_handler_id:
            handler = db.query(User).filter(User.id == mnr_handler_id).first()
            if not handler:
                raise HTTPException(status_code=400, detail="MNR user not found")
            lead.mnr_handler_id = mnr_handler_id
            lead.handler_type = 'member'
            lead.handler_id = mnr_handler_id
        else:
            # DC Protocol: Clear all related handler fields when clearing MNR handler
            lead.mnr_handler_id = None
            if lead.handler_type == 'member':
                lead.handler_type = None
                lead.handler_id = None
    
    if guru_id is not None or ('guru_id' in locals() and guru_id is None):
        lead.guru_id = guru_id

    if adi_guru_id is not None or ('adi_guru_id' in locals() and adi_guru_id is None):
        lead.adi_guru_id = adi_guru_id

    # DC Protocol (Apr 2026): 8 previously-missing fields now persisted by this endpoint.
    # These were silently dropped (FastAPI ignored unknown Body keys). Now declared and saved.
    if z_guru_id is not None or ('z_guru_id' in locals() and z_guru_id is None):
        lead.z_guru_id = z_guru_id
    
    # DC-HCI: We must accept None to clear out previous data (e.g. if Senior was Hari Teja, but is now changed to MNR user)
    lead.team_senior_partner_id = team_senior_partner_id
    lead.team_extended_partner_id = team_extended_partner_id
    lead.team_core_partner_id = team_core_partner_id

    if source_ref_type is not None:
        lead.source_ref_type = source_ref_type if source_ref_type else None
    if source_ref_id is not None:
        lead.source_ref_id = source_ref_id if source_ref_id else None
        # Keep mnr_handler_id in sync when source is MNR user
        if source_ref_type == 'mnr' and source_ref_id:
            lead.mnr_handler_id = str(source_ref_id)
        elif source_ref_type in ('vgk', 'vgk_partner', 'partner', 'vendor', 'staff') and not source_ref_id:
            lead.mnr_handler_id = None
            
        # Keep associated_partner_id in sync when source is a VGK partner
        if source_ref_type in ('vgk', 'vgk_partner', 'partner') and source_ref_id:
            try:
                lead.associated_partner_id = int(source_ref_id)
            except (ValueError, TypeError):
                pass
        elif source_ref_type in ('mnr', 'staff') and source_ref_id:
            lead.associated_partner_id = None
        elif not source_ref_id:
            lead.associated_partner_id = None

    # DC Protocol: Auto-populate uplines (L2, L3, L4) based on Ground Source (mnr_handler_id)
    if lead.mnr_handler_id:
        try:
            _muser = db.query(User).filter(User.id == lead.mnr_handler_id).first()
            if _muser and _muser.referrer_id:
                _guru = db.query(User).filter(User.id == _muser.referrer_id).first()
                if _guru:
                    if not lead.guru_id: lead.guru_id = _guru.id
                    if _guru.referrer_id:
                        _zguru = db.query(User).filter(User.id == _guru.referrer_id).first()
                        if _zguru:
                            if not lead.z_guru_id: lead.z_guru_id = _zguru.id
                            if _zguru.referrer_id:
                                _adiguru = db.query(User).filter(User.id == _zguru.referrer_id).first()
                                if _adiguru:
                                    if not lead.adi_guru_id: lead.adi_guru_id = _adiguru.id
        except Exception as e:
            print(f"[CRM] Auto-populate uplines error: {str(e)}")

    if source_ref_name is not None:
        lead.source_ref_name = source_ref_name if source_ref_name else None

    if field_support_ref_type is not None:
        lead.field_support_ref_type = field_support_ref_type if field_support_ref_type else None
    if field_support_ref_id is not None:
        lead.field_support_ref_id = field_support_ref_id if field_support_ref_id else None
        # Sync vgk_field_support_id for L3 commission when partner is field support
        if field_support_ref_type == 'partner' and field_support_ref_id:
            try:
                lead.vgk_field_support_id = int(field_support_ref_id)
            except (ValueError, TypeError):
                pass
    if field_support_ref_name is not None:
        lead.field_support_ref_name = field_support_ref_name if field_support_ref_name else None

    if technical_id is not None:
        lead.technical_id = technical_id if technical_id else None
    if support_staff_id is not None:
        lead.support_staff_id = support_staff_id if support_staff_id else None
    if technical_staff1_id is not None:
        lead.technical_staff1_id = technical_staff1_id if technical_staff1_id else None
    if support_staff_supported is not None:
        lead.support_staff_supported = support_staff_supported
    if technical_staff1_supported is not None:
        lead.technical_staff1_supported = technical_staff1_supported

    if telecaller_id is not None:
        if telecaller_id:
            staff = db.query(StaffEmployee).filter(StaffEmployee.id == telecaller_id).first()
            if not staff:
                raise HTTPException(status_code=400, detail="Telecaller not found")
        lead.telecaller_id = telecaller_id if telecaller_id else None
    
    if field_staff_id is not None:
        if field_staff_id:
            staff = db.query(StaffEmployee).filter(StaffEmployee.id == field_staff_id).first()
            if not staff:
                raise HTTPException(status_code=400, detail="Field staff not found")
        lead.field_staff_id = field_staff_id if field_staff_id else None
    
    if associated_partner_id is not None:
        # Only override if we haven't already explicitly synced it from a partner source reference
        if not (source_ref_type in ('vgk', 'vgk_partner', 'partner') and source_ref_id):
            lead.associated_partner_id = associated_partner_id if associated_partner_id else None
    
    if deal_value_total is not None:
        lead.deal_value_total = deal_value_total
    if deal_value_received is not None:
        lead.deal_value_received = deal_value_received
    if deal_value_balance is not None:
        lead.deal_value_balance = deal_value_balance
    
    lead.updated_at = get_indian_time()
    db.commit()
    db.refresh(lead)

    # DC-HCI-001 (Jul 2026): Income correction if associated_partner_id changed
    _full_new_partner_id = lead.associated_partner_id
    if (
        _full_pre_partner_id
        and _full_new_partner_id
        and _full_pre_partner_id != _full_new_partner_id
        and associated_partner_id is not None
    ):
        try:
            from app.services.vgk_income_correction import handle_handler_change_income_correction
            _changed_by = (
                getattr(current_user, 'full_name', '')
                or getattr(current_user, 'name', '')
                or getattr(current_user, 'emp_code', '')
                or str(current_user.id)
            )
            _full_hci = handle_handler_change_income_correction(
                db=db, lead=lead,
                old_partner_id=_full_pre_partner_id,
                new_partner_id=_full_new_partner_id,
                changed_by_name=_changed_by,
                staff_id=getattr(current_user, 'id', None),
            )
            db.commit()
            logger.info(
                f'[DC-HCI-001] full-update Lead#{lead_id}: '
                f'cancelled={_full_hci.get("cancelled",0)} '
                f'adjusted_paid={_full_hci.get("adjusted_paid",0)} '
                f'new_drafts={_full_hci.get("new_drafts",0)}'
            )
        except Exception as _full_hci_e:
            logger.warning(f'[DC-HCI-001] full-update correction failed lead#{lead_id}: {_full_hci_e}')

    # DC-BRP-RETRIGGER-001 (Jul 2026): Extend trigger to solar-completion stages.
    # Solar leads stay at status='won' while solar_pipeline_status reaches balance_received/
    # subsidy_pending, so checking status=='completed' alone misses all solar income triggers.
    _sps_hook = (getattr(lead, 'solar_pipeline_status', '') or '').lower()
    _income_hook_eligible = (
        (status == 'completed' and _old_lead_status != 'completed')
        or _sps_hook in {'balance_received', 'subsidy_pending', 'completed'}
    )
    if _income_hook_eligible and lead.associated_partner_id:
        try:
            from app.services.vgk_cash_income import generate_vgk_cash_income_drafts
            _drafted = generate_vgk_cash_income_drafts(db, lead)
            db.commit()
            logger.info(f'[VGK-CRM-HOOK] Lead#{lead_id}→{status or _sps_hook}: {_drafted} income draft(s) created')
        except Exception as _vgk_e:
            logger.warning(f'[VGK-CRM-HOOK] draft gen failed for lead#{lead_id} (non-fatal): {_vgk_e}')

    result = lead.to_dict()
    
    if lead.mnr_handler_id:
        handler = db.query(User).filter(User.id == lead.mnr_handler_id).first()
        result['mnr_handler_name'] = handler.name if handler else None
    if lead.guru_id:
        guru = db.query(User).filter(User.id == lead.guru_id).first()
        result['guru_name'] = guru.name if guru else None
    if lead.adi_guru_id:
        adi_guru = db.query(User).filter(User.id == lead.adi_guru_id).first()
        result['adi_guru_name'] = adi_guru.name if adi_guru else None
    if lead.telecaller_id:
        tc = db.query(StaffEmployee).filter(StaffEmployee.id == lead.telecaller_id).first()
        result['telecaller_name'] = tc.full_name if tc else None
        result['telecaller_code'] = tc.emp_code if tc else None
    if lead.field_staff_id:
        fs = db.query(StaffEmployee).filter(StaffEmployee.id == lead.field_staff_id).first()
        result['field_staff_name'] = fs.full_name if fs else None
        result['field_staff_code'] = fs.emp_code if fs else None
    
    return {
        'success': True,
        'message': 'Lead updated successfully',
        'data': result
    }


@router.get("/unified-my-leads/search-staff")
async def search_staff_members_unified(
    q: str = Query(..., min_length=2),
    staff_type: Optional[str] = Query(None, description="Filter by type: telecaller, field_staff"),
    limit: int = Query(20, le=50),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
):
    """
    Search staff members for lead assignment (Tele Caller, Field Staff).
    DC Protocol: Only accessible by staff users for assigning leads.
    """
    from app.models.staff import StaffEmployee
    
    # Only staff users can search for staff members
    is_staff = hasattr(current_user, 'emp_code') and current_user.emp_code
    if not is_staff:
        raise HTTPException(status_code=403, detail="Staff access required")
    
    search_term = f"%{q}%"
    # DC Protocol: Search by employee ID, name, or phone — filtered to Sales department only
    # Tele Caller and Field Staff assignments must be Sales dept personnel
    from app.models.staff import StaffDepartment
    query = db.query(StaffEmployee).join(
        StaffDepartment, StaffEmployee.department_id == StaffDepartment.id, isouter=True
    ).filter(
        or_(
            StaffEmployee.emp_code.ilike(search_term),
            StaffEmployee.full_name.ilike(search_term),
            StaffEmployee.phone.ilike(search_term)
        ),
        StaffDepartment.name.ilike('%sales%')
    )

    staff = query.order_by(StaffEmployee.full_name).limit(limit).all()
    
    return {
        'success': True,
        'data': [
            {
                'id': s.id,
                'emp_code': s.emp_code,
                'name': s.full_name,
                'phone': s.phone,
                'designation': s.designation,
                'staff_type': s.staff_type,
                'is_active': s.status == 'active',
                'status': s.status.capitalize() if s.status else 'Unknown'
            }
            for s in staff
        ]
    }


@router.get("/unified-my-leads/search-partner")
async def search_partners_unified(
    q: str = Query(..., min_length=1),
    limit: int = Query(20, le=50),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
):
    """
    Search partners for lead assignment in My Leads page.
    DC Protocol: Cross-company partner search allowed - partners are global.
    Only staff users can assign partners to leads.
    """
    from app.models.staff_accounts import OfficialPartner
    
    # Only staff users can search for partners
    is_staff = hasattr(current_user, 'emp_code') and current_user.emp_code
    if not is_staff:
        raise HTTPException(status_code=403, detail="Staff access required")
    
    search_term = q.strip().lower()
    
    # DC Protocol: Search by partner code or name, include inactive with status indicator
    query = db.query(OfficialPartner)
    
    if search_term:
        query = query.filter(
            or_(
                func.coalesce(func.lower(OfficialPartner.partner_name), '').contains(search_term),
                func.lower(OfficialPartner.partner_code).contains(search_term),
                func.coalesce(func.lower(OfficialPartner.contact_person), '').contains(search_term)
            )
        )
    
    partner_list = query.order_by(OfficialPartner.partner_name).limit(limit).all()
    
    results = []
    for partner in partner_list:
        category = partner.category if partner.category else ''
        display_name = partner.partner_name or partner.contact_person or partner.partner_code
        results.append({
            'id': partner.id,
            'name': display_name,
            'code': partner.partner_code,
            'contact_person': partner.contact_person or '',
            'phone': partner.phone or '',
            'category': category,
            'display': f"{display_name} ({partner.partner_code})" + (f" - {category}" if category else ""),
            'is_active': partner.is_active if partner.is_active is not None else True,
            'status': 'Active' if (partner.is_active if partner.is_active is not None else True) else 'Inactive'
        })
    
    return {
        'success': True,
        'data': results,
        'count': len(results)
    }


@router.get("/network-search")
async def network_search(
    q: str = Query(..., min_length=2),
    search_type: Optional[str] = Query(None, alias="type", description="Search type: mnr|vgk|partner|vendor|staff|all. Omit or 'all' to search across all types."),
    company_id: Optional[int] = Query(None),
    limit: int = Query(20, le=50),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
):
    """
    Unified network member search for Source / Field Support / Technical assignment.
    DC Protocol: type=all (or omit) searches all types simultaneously with type badges.
    type=mnr|vgk → User table (activated members)
    type=partner  → OfficialPartner table
    type=vendor   → VendorMaster table
    type=staff    → StaffEmployee table (active only)
    """
    from app.models.staff_accounts import OfficialPartner, VendorMaster as _VM
    from app.models.staff import StaffEmployee as _SE

    type = search_type  # noqa: F841 — use local alias
    search_term = q.strip()
    results = []
    search_all = not type or type == 'all'
    per_type_limit = max(5, limit // 5) if search_all else limit

    try:
        if search_all or type in ('mnr', 'vgk'):
            users = db.query(User).filter(
                User.activation_date.isnot(None),
                or_(
                    User.id.ilike(f"%{search_term}%"),
                    User.name.ilike(f"%{search_term}%"),
                    User.phone_number.ilike(f"%{search_term}%")
                )
            ).order_by(User.name).limit(per_type_limit).all()
            for u in users:
                sponsor_name = None
                z_sponsor_id = None
                z_sponsor_name = None
                if u.referrer_id:
                    sp = db.query(User).filter(User.id == u.referrer_id).first()
                    if sp:
                        sponsor_name = sp.name
                        # L2 upline: sponsor's sponsor = Z Guru
                        if sp.referrer_id:
                            zsp = db.query(User).filter(User.id == sp.referrer_id).first()
                            if zsp:
                                z_sponsor_id = zsp.id
                                z_sponsor_name = zsp.name
                member_type = 'vgk' if (u.id or '').upper().startswith('VGK') else 'mnr'
                results.append({
                    'id': u.id,
                    'name': u.name or '',
                    'code': u.id,
                    'phone': u.phone_number or '',
                    'display': f"{u.id} — {u.name or ''}",
                    'sponsor_id': u.referrer_id,
                    'sponsor_name': sponsor_name,
                    'z_sponsor_id': z_sponsor_id,
                    'z_sponsor_name': z_sponsor_name,
                    'type': member_type
                })

        if search_all or type in ('partner', 'vgk', 'vgk_partner'):
            partners = db.query(OfficialPartner).filter(
                or_(
                    func.coalesce(func.lower(OfficialPartner.partner_name), '').contains(search_term.lower()),
                    func.lower(OfficialPartner.partner_code).contains(search_term.lower()),
                    func.coalesce(func.lower(OfficialPartner.contact_person), '').contains(search_term.lower())
                )
            ).order_by(OfficialPartner.partner_name).limit(per_type_limit).all()
            # DC Protocol Fix (Apr 2026): Pre-load parent chain in one query pass to avoid N+1
            # DC-TEAM-ASSIGN-001 (Jun 2026): Extended to 4 levels (L1→L2→L3→L4 Senior/Extended/Core)
            _partner_ids_needed = set()
            for p in partners:
                if p.parent_partner_id:
                    _partner_ids_needed.add(p.parent_partner_id)
            _parent_map = {}
            if _partner_ids_needed:
                _parents = db.query(OfficialPartner).filter(OfficialPartner.id.in_(_partner_ids_needed)).all()
                _parent_map = {pp.id: pp for pp in _parents}
                # Collect grandparent IDs (L2 / Senior)
                _gp_ids_needed = {pp.parent_partner_id for pp in _parents if pp.parent_partner_id}
                if _gp_ids_needed:
                    _gps = db.query(OfficialPartner).filter(OfficialPartner.id.in_(_gp_ids_needed)).all()
                    _parent_map.update({gp.id: gp for gp in _gps})
                    # Collect great-grandparent IDs (L3 / Extended)
                    _ggp_ids_needed = {gp.parent_partner_id for gp in _gps if gp.parent_partner_id}
                    if _ggp_ids_needed:
                        _ggps = db.query(OfficialPartner).filter(OfficialPartner.id.in_(_ggp_ids_needed)).all()
                        _parent_map.update({ggp.id: ggp for ggp in _ggps})
                        # Collect great-great-grandparent IDs (L4 / Core)
                        _gggp_ids_needed = {ggp.parent_partner_id for ggp in _ggps if ggp.parent_partner_id}
                        if _gggp_ids_needed:
                            _gggps = db.query(OfficialPartner).filter(OfficialPartner.id.in_(_gggp_ids_needed)).all()
                            _parent_map.update({gggp.id: gggp for gggp in _gggps})
            for p in partners:
                display = p.partner_name or p.contact_person or p.partner_code
                # DC Protocol Fix (Apr 2026): Label VGK official partners as 'vgk_partner' (not 'vgk').
                # 'vgk' is reserved for VGK user-account holders (in user table, valid mnr_handler_id FK).
                # 'vgk_partner' = official_partner with VGK code — NOT in user table, no FK to user.id.
                _pcode = (p.partner_code or '').upper()
                _ptype = 'vgk_partner' if _pcode.startswith('VGK') else 'partner'
                # Resolve upline chain L1→L2→L3→L4 (Senior/Extended/Core)
                _parent_id = None; _parent_name = None; _parent_code = None
                _gp_id = None;    _gp_name = None;    _gp_code = None
                _ggp_id = None;   _ggp_name = None;   _ggp_code = None
                _gggp_id = None;  _gggp_name = None;  _gggp_code = None
                if p.parent_partner_id:
                    _par = _parent_map.get(p.parent_partner_id)
                    if _par:
                        _parent_id = str(_par.id); _parent_name = _par.partner_name or _par.contact_person or _par.partner_code or ''; _parent_code = _par.partner_code or ''
                        if _par.parent_partner_id:
                            _gpar = _parent_map.get(_par.parent_partner_id)
                            if _gpar:
                                _gp_id = str(_gpar.id); _gp_name = _gpar.partner_name or _gpar.contact_person or _gpar.partner_code or ''; _gp_code = _gpar.partner_code or ''
                                if _gpar.parent_partner_id:
                                    _ggpar = _parent_map.get(_gpar.parent_partner_id)
                                    if _ggpar:
                                        _ggp_id = str(_ggpar.id); _ggp_name = _ggpar.partner_name or _ggpar.contact_person or _ggpar.partner_code or ''; _ggp_code = _ggpar.partner_code or ''
                                        if _ggpar.parent_partner_id:
                                            _gggpar = _parent_map.get(_ggpar.parent_partner_id)
                                            if _gggpar:
                                                _gggp_id = str(_gggpar.id); _gggp_name = _gggpar.partner_name or _gggpar.contact_person or _gggpar.partner_code or ''; _gggp_code = _gggpar.partner_code or ''
                results.append({
                    'id': str(p.id),
                    'name': display or '',
                    'code': p.partner_code or '',
                    'phone': p.phone or '',
                    'display': f"{p.partner_code} — {display or ''}",
                    'is_active': p.is_active,
                    'type': _ptype,
                    # Upline chain: Senior(L2), Extended(L3), Core(L4)
                    'parent_partner_id': _parent_id,
                    'parent_partner_name': _parent_name,
                    'parent_partner_code': _parent_code,
                    'z_parent_partner_id': _gp_id,
                    'z_parent_partner_name': _gp_name,
                    'z_parent_partner_code': _gp_code,
                    # DC-TEAM-ASSIGN-001: L3 Extended + L4 Core
                    'adi_parent_partner_id': _ggp_id,
                    'adi_parent_partner_name': _ggp_name,
                    'adi_parent_partner_code': _ggp_code,
                    'core_parent_partner_id': _gggp_id,
                    'core_parent_partner_name': _gggp_name,
                    'core_parent_partner_code': _gggp_code,
                })

        if search_all or type == 'vendor':
            vendors = db.query(_VM).filter(
                _VM.is_active == True,
                or_(
                    func.lower(_VM.vendor_name).contains(search_term.lower()),
                    func.lower(_VM.vendor_code).contains(search_term.lower()),
                    _VM.phone.contains(search_term) if _VM.phone else False
                )
            ).order_by(_VM.vendor_name).limit(per_type_limit).all()
            for v in vendors:
                results.append({
                    'id': str(v.id),
                    'name': v.vendor_name or '',
                    'code': v.vendor_code or '',
                    'phone': v.phone or '',
                    'display': f"{v.vendor_code} — {v.vendor_name or ''}",
                    'type': 'vendor'
                })

        if search_all or type == 'staff':
            staff_list = db.query(_SE).filter(
                _SE.status == 'active',
                or_(
                    func.coalesce(func.lower(_SE.full_name), '').contains(search_term.lower()),
                    func.lower(_SE.emp_code).contains(search_term.lower()),
                    func.coalesce(_SE.phone, '').contains(search_term)
                )
            ).order_by(_SE.full_name).limit(per_type_limit).all()
            for s in staff_list:
                results.append({
                    'id': str(s.id),
                    'name': s.full_name or s.emp_code or '',
                    'code': s.emp_code or '',
                    'phone': s.phone or '',
                    'display': f"{s.emp_code} — {s.full_name or ''}",
                    'designation': getattr(s, 'designation', '') or '',
                    'type': 'staff'
                })

    except Exception as e:
        print(f"[DC-NET-SEARCH] Error type={type} q={q}: {e}")
        return {'success': False, 'data': [], 'results': [], 'error': str(e)}

    return {'success': True, 'data': results, 'results': results, 'count': len(results), 'type': type or 'all'}


@router.get("/signup/categories")
async def get_signup_categories(
    company_id: Optional[int] = Query(None, description="Company ID for DC Protocol filtering"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_hybrid)
):
    """
    Get signup categories for lead categorization.
    DC Protocol: Returns categories based on user company context.
    """
    from app.models.staff import StaffEmployee
    
    is_staff_user = isinstance(current_user, StaffEmployee)
    
    query = db.query(SignupCategory).filter(SignupCategory.is_active == True)
    
    if company_id:
        query = query.filter(SignupCategory.company_id == company_id)
    elif is_staff_user:
        # Staff users: filter by their data_companies or base_company
        staff_companies = getattr(current_user, "data_companies", None) or []
        if staff_companies:
            query = query.filter(SignupCategory.company_id.in_(staff_companies))
        elif hasattr(current_user, "base_company_id") and current_user.base_company_id:
            query = query.filter(SignupCategory.company_id == current_user.base_company_id)
    else:
        # MNR user: filter by their company
        user_company_id = getattr(current_user, "company_id", None)
        if user_company_id:
            query = query.filter(SignupCategory.company_id == user_company_id)
    
    categories = query.order_by(SignupCategory.display_order, SignupCategory.name).all()
    
    return {
        "success": True,
        "data": [cat.to_dict() for cat in categories],
        "count": len(categories)
    }



# ── Google Sheets → CRM Import ────────────────────────────────────────────────
class SheetsImportRequest(BaseModel):
    sheet_url: str
    company_id: int = 1
    source_tag: str = "Online - M"
    gid: str = "0"
    skip_duplicates: bool = True

@router.post("/import-from-sheets")
async def import_leads_from_google_sheets(
    data: SheetsImportRequest,
    current_user = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """
    Import leads from a Google Sheets URL directly into CRM.
    DC Protocol Mar 2026: Sheet must be shared as 'Anyone with link can view'.
    Works with Facebook-exported lead sheets and Google Forms response sheets.
    """
    from app.services.sheets_leads_service import import_sheet_to_crm
    result = import_sheet_to_crm(
        sheet_url=data.sheet_url,
        db=db,
        company_id=data.company_id,
        source_tag=data.source_tag,
        gid=data.gid,
        skip_duplicates=data.skip_duplicates
    )
    return result

@router.post("/preview-sheet")
async def preview_google_sheet(
    data: SheetsImportRequest,
    current_user = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """
    Preview a Google Sheet before importing — shows column mapping and first 5 rows.
    DC Protocol Mar 2026: Use this before import-from-sheets to verify mapping.
    """
    from app.services.sheets_leads_service import fetch_sheet_data, map_headers, extract_sheet_id
    try:
        headers, rows = fetch_sheet_data(data.sheet_url, gid=data.gid)
    except ValueError as e:
        return {'success': False, 'error': str(e)}
    col_map = map_headers(headers)
    preview_rows = []
    for row in rows[:5]:
        preview_rows.append({h: (row[i] if i < len(row) else '') for i, h in enumerate(headers)})
    return {
        'success': True,
        'sheet_id': extract_sheet_id(data.sheet_url),
        'total_rows': len(rows),
        'headers': headers,
        'column_mapping': {k: headers[v] for k, v in col_map.items()},
        'unmapped_columns': [h for i, h in enumerate(headers) if i not in col_map.values()],
        'preview': preview_rows
    }



# ── Solar Document Management ─────────────────────────────────────────────────
# DC Protocol Mar 2026: Upload, list, view, delete solar lead documents
# Access: Assigned staff (telecaller / field staff) + managers with direct reports
# Storage: UniversalUploadService → Object Storage (solar_docs/)
# One file per doc_type per lead (UPSERT on re-upload)

SOLAR_DOC_TYPES = {
    # Consumer documents
    'adhar':                         'Aadhaar Card',
    'pan':                           'PAN Card',
    'powerbill':                     'Electricity Bill (Powerbill)',
    'bank_book':                     'Bank Book',
    'bank_statement':                'Bank Statement',
    'roof_top_photo':                'Roof Top Photo',
    'geotagging_photo':              'Geo Solar Photo',
    'geo_location_photo':            'Geo Location Photo',
    'solar_rooftop_registration':    'Solar Rooftop Registration',
    'technical_installation_details':'Technical Installation Details',
    'quotation':                     'Quotation',
    'co_applicant_quotation':        'Co-applicant Quotation',
    'feasibility_letter':            'Feasibility Letter',
    'etoken':                        'Etoken',
    'acknowledgement':               'Acknowledgement',
    'net_meter_agreement':           'Net Meter Agreement',
    'dcr_certificate':               'DCR Certificate',
    'invoice':                       'Invoice',
    'installation_certificate':      'Installation Certificate',
    'annexure_a':                    'Annexure-A',
    'annexure_c':                    'Annexure-C (Project Completion Report)',
    'annexure_c_technical':          'Annexure-C (Technical Installation Details)',
    'synchronisation_certificate':   'Synchronisation Certificate',
    'commissioning_test_report':     'Commissioning Test Report: Solar Project 3KW',
    'annexure_iv':                   'Annexure-IV Work Completion Report',
    'bank_submission_letter':        'Bank Submission Letter',
    'house_tax':                     'House Tax Receipt',
    'bank_loan_application':         'Bank Loan Application',
    # Co-applicant documents
    'co_adhar':                      'Aadhaar Card (Co-Applicant)',
    'co_pan':                        'PAN Card (Co-Applicant)',
    'co_bank_statement':             'Bank Statement (Co-Applicant)',
    # CIBIL validation document (DC Protocol Apr 2026) — required for ₹1,000 advance eligibility
    'cibil_report':                  'CIBIL Credit Report',
    # Identity & application additions
    'passport_photo':                'Passport Photo',
    'signature':                     'Signature Document',
    'net_meter_application':         'Net Meter Application',
}

# Doc types that support auto-generation (map to solar_doc_generator functions)
GENERATABLE_DOC_TYPES = {
    'quotation':                    'quotation',
    'co_applicant_quotation':       'co_applicant_quotation',
    'invoice':                      'invoice',
    'annexure_a':                   'annexure_a',
    'annexure_c':                   'annexure_c_completion',
    'annexure_c_technical':         'annexure_c_technical',
    'commissioning_test_report':    'commissioning_test_report',
    'synchronisation_certificate':  'synchronisation_certificate',
    'annexure_iv':                  'annexure_iv',
    'bank_submission_letter':       'bank_submission_letter',
}


@router.get("/leads/{lead_id}/solar-docs")
def get_solar_docs(
    lead_id: int,
    db: Session = Depends(get_db),
    current_employee: StaffEmployee = Depends(get_current_staff_user),
):
    """
    List all uploaded solar documents for a lead.
    DC Protocol: Returns docs with view_url for direct object-storage access.
    """
    lead = db.execute(text("SELECT id FROM crm_leads WHERE id = :lid"), {"lid": lead_id}).fetchone()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    rows = db.execute(text("""
        SELECT id, doc_category, doc_type, doc_label, doc_number,
               file_name, original_name, file_size,
               uploaded_by_id, uploaded_by_name, uploaded_at, notes
        FROM crm_lead_solar_documents
        WHERE lead_id = :lid
        ORDER BY doc_category, doc_type
    """), {"lid": lead_id}).fetchall()

    docs = []
    for r in rows:
        docs.append({
            "id":               r.id,
            "doc_category":     r.doc_category,
            "doc_type":         r.doc_type,
            "doc_label":        r.doc_label,
            "doc_number":       r.doc_number or "",
            "file_name":        r.file_name,
            "original_name":    r.original_name,
            "file_size":        r.file_size,
            "uploaded_by_id":   r.uploaded_by_id,
            "uploaded_by_name": r.uploaded_by_name,
            "uploaded_at":      r.uploaded_at.isoformat() if r.uploaded_at else None,
            "notes":            r.notes or "",
            "view_url":         f"/storage/{r.file_name}" if r.file_name else None,
        })

    return {"success": True, "docs": docs, "count": len(docs)}


@router.post("/leads/{lead_id}/solar-docs/upload")
async def upload_solar_doc(
    lead_id: int,
    doc_type:     str        = Form(...),
    doc_category: str        = Form(...),
    doc_number:   str        = Form(default=""),
    notes:        str        = Form(default=""),
    file:         UploadFile = File(...),
    db:           Session    = Depends(get_db),
    current_employee: StaffEmployee = Depends(get_current_staff_user),
):
    """
    Upload (or replace) a solar document for a lead.
    DC Protocol: Validates type, calls UniversalUploadService, upserts row.
    """
    from app.services.universal_upload_service import UniversalUploadService

    lead = db.execute(text("SELECT id FROM crm_leads WHERE id = :lid"), {"lid": lead_id}).fetchone()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    if doc_type not in SOLAR_DOC_TYPES:
        raise HTTPException(status_code=400, detail=f"Invalid doc_type: {doc_type}")

    if doc_category not in ("consumer", "co_applicant"):
        raise HTTPException(status_code=400, detail="doc_category must be 'consumer' or 'co_applicant'")

    doc_label = SOLAR_DOC_TYPES[doc_type]

    upload_result = await UniversalUploadService.handle_upload(
        file=file,
        table_name="crm_lead_solar_documents",
        record_id=lead_id,
        uploaded_by_id=current_employee.id,
        uploaded_by_type="staff",
        storage_dir="solar_docs",
        db=db,
        emp_code=getattr(current_employee, "emp_code", None),
        defer_scheduler=True,
    )

    emp_name = (
        getattr(current_employee, "full_name", None)
        or getattr(current_employee, "emp_code", "Staff")
    )

    existing = db.execute(text("""
        SELECT id FROM crm_lead_solar_documents
        WHERE lead_id = :lid AND doc_type = :dtype
    """), {"lid": lead_id, "dtype": doc_type}).fetchone()

    if existing:
        db.execute(text("""
            UPDATE crm_lead_solar_documents
            SET doc_number      = CASE WHEN :dnum != '' THEN :dnum ELSE doc_number END,
                file_name       = :fname,
                original_name   = :oname,
                file_size       = :fsize,
                uploaded_by_id  = :uid,
                uploaded_by_name= :uname,
                uploaded_at     = NOW(),
                notes           = CASE WHEN :notes != '' THEN :notes ELSE notes END
            WHERE id = :did
        """), {
            "dnum":  doc_number or "",
            "fname": upload_result["file_path"],
            "oname": upload_result["file_name"],
            "fsize": upload_result["file_size"],
            "uid":   current_employee.id,
            "uname": emp_name,
            "notes": notes or "",
            "did":   existing.id,
        })
    else:
        db.execute(text("""
            INSERT INTO crm_lead_solar_documents
                (lead_id, doc_category, doc_type, doc_label, doc_number,
                 file_name, original_name, file_size,
                 uploaded_by_id, uploaded_by_name, uploaded_at, notes)
            VALUES
                (:lid, :dcat, :dtype, :dlabel, :dnum,
                 :fname, :oname, :fsize,
                 :uid, :uname, NOW(), :notes)
        """), {
            "lid":    lead_id,
            "dcat":   doc_category,
            "dtype":  doc_type,
            "dlabel": doc_label,
            "dnum":   doc_number or "",
            "fname":  upload_result["file_path"],
            "oname":  upload_result["file_name"],
            "fsize":  upload_result["file_size"],
            "uid":    current_employee.id,
            "uname":  emp_name,
            "notes":  notes or "",
        })

    db.commit()
    logger.info("[DC-SOLAR-DOC] %s uploaded for lead #%s by %s", doc_type, lead_id, emp_name)

    return {
        "success":  True,
        "message":  f"{doc_label} uploaded successfully",
        "doc_type": doc_type,
        "view_url": f"/storage/{upload_result['file_path']}",
    }


@router.post("/leads/{lead_id}/solar-docs/pre-save-number")
def pre_save_solar_doc_number(
    lead_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    current_employee: StaffEmployee = Depends(get_current_staff_user),
):
    """
    Create (or update) a solar document record with just a doc_number — no file needed.
    DC Protocol: Staff records the doc number before the file is ready to upload.
    """
    doc_type     = (payload.get("doc_type") or "").strip()
    doc_category = (payload.get("doc_category") or "consumer").strip()
    doc_number   = (payload.get("doc_number") or "").strip()

    if not doc_type:
        raise HTTPException(status_code=400, detail="doc_type is required")
    if doc_type not in SOLAR_DOC_TYPES:
        raise HTTPException(status_code=400, detail=f"Invalid doc_type: {doc_type}")
    if not doc_number:
        raise HTTPException(status_code=400, detail="doc_number is required")

    doc_label = SOLAR_DOC_TYPES[doc_type]
    emp_name  = getattr(current_employee, "full_name", None) or getattr(current_employee, "emp_code", "Staff")

    existing = db.execute(text("""
        SELECT id FROM crm_lead_solar_documents
        WHERE lead_id = :lid AND doc_type = :dtype
    """), {"lid": lead_id, "dtype": doc_type}).fetchone()

    if existing:
        db.execute(text("""
            UPDATE crm_lead_solar_documents SET doc_number = :dnum WHERE id = :did
        """), {"dnum": doc_number, "did": existing.id})
        doc_id = existing.id
    else:
        row = db.execute(text("""
            INSERT INTO crm_lead_solar_documents
                (lead_id, doc_category, doc_type, doc_label, doc_number,
                 uploaded_by_id, uploaded_by_name)
            VALUES (:lid, :dcat, :dtype, :dlabel, :dnum, :uid, :uname)
            RETURNING id
        """), {
            "lid":    lead_id,
            "dcat":   doc_category,
            "dtype":  doc_type,
            "dlabel": doc_label,
            "dnum":   doc_number,
            "uid":    current_employee.id,
            "uname":  emp_name,
        })
        doc_id = row.scalar()

    db.commit()
    logger.info("[DC-SOLAR-DOC] Pre-saved doc_number for %s on lead #%s by %s", doc_type, lead_id, emp_name)
    return {"success": True, "doc_id": doc_id, "doc_number": doc_number, "message": f"{doc_label} number saved"}


@router.patch("/solar-docs/{doc_id}/number")
def update_solar_doc_number(
    doc_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    current_employee: StaffEmployee = Depends(get_current_staff_user),
):
    """
    Update just the doc_number of an existing solar document (no file re-upload needed).
    DC Protocol: Staff can update any doc number they have access to.
    """
    doc = db.execute(text("""
        SELECT id, doc_label FROM crm_lead_solar_documents WHERE id = :did
    """), {"did": doc_id}).fetchone()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    doc_number = (payload.get("doc_number") or "").strip()
    db.execute(text("""
        UPDATE crm_lead_solar_documents SET doc_number = :dnum WHERE id = :did
    """), {"dnum": doc_number, "did": doc_id})
    db.commit()

    logger.info("[DC-SOLAR-DOC] Updated doc_number for #%s (%s) by staff #%s", doc_id, doc.doc_label, current_employee.id)
    return {"success": True, "message": f"{doc.doc_label} number updated", "doc_number": doc_number}


@router.delete("/solar-docs/{doc_id}")
def delete_solar_doc(
    doc_id: int,
    db: Session = Depends(get_db),
    current_employee: StaffEmployee = Depends(get_current_staff_user),
):
    """
    Delete a solar document record (does not remove from object storage).
    DC Protocol: Staff can delete any doc they have access to.
    """
    doc = db.execute(text("""
        SELECT id, doc_label FROM crm_lead_solar_documents WHERE id = :did
    """), {"did": doc_id}).fetchone()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    db.execute(text("DELETE FROM crm_lead_solar_documents WHERE id = :did"), {"did": doc_id})
    db.commit()

    logger.info("[DC-SOLAR-DOC] Deleted doc #%s (%s) by staff #%s", doc_id, doc.doc_label, current_employee.id)
    return {"success": True, "message": f"{doc.doc_label} deleted successfully"}


# ── Lead Share Token System ────────────────────────────────────────────────────
# DC Protocol Mar 2026: Generate 6-hour expiry share links for leads
# Single link shows: lead details + all solar docs (view/download), read-only
# No auth required to VIEW via share link — token acts as the auth
# Auth required to CREATE a share link

import secrets as _secrets_mod
from datetime import timezone as _tz

@router.post("/leads/{lead_id}/share-link")
def create_share_link(
    lead_id: int,
    request: Request,
    body: dict = Body(default={}),
    db: Session = Depends(get_db),
    current_employee: StaffEmployee = Depends(get_current_staff_user),
):
    """
    Generate a 6-hour expiry share link for a lead.
    Body (optional): { "doc_types": ["adhar", "pan", ...] }
    If doc_types is omitted or null, all documents are included.
    """
    import json as _json
    lead = db.execute(text("SELECT id, name FROM crm_leads WHERE id = :lid"), {"lid": lead_id}).fetchone()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    # Optional doc filter
    doc_types = body.get("doc_types", None) if body else None
    doc_filter_json = _json.dumps(doc_types) if doc_types and isinstance(doc_types, list) and len(doc_types) > 0 else None

    token = _secrets_mod.token_urlsafe(40)
    expires_at_utc = datetime.now(_tz.utc) + timedelta(hours=6)
    emp_name = getattr(current_employee, "name", None) or getattr(current_employee, "emp_code", "Staff")

    db.execute(text("""
        INSERT INTO crm_lead_share_tokens (token, lead_id, expires_at, created_by_id, created_by_name, doc_filter)
        VALUES (:tok, :lid, :exp, :uid, :uname, :df)
    """), {
        "tok":   token,
        "lid":   lead_id,
        "exp":   expires_at_utc,
        "uid":   current_employee.id,
        "uname": emp_name,
        "df":    doc_filter_json,
    })
    db.commit()

    base_url = _canonical_base(request)
    share_url = f"{base_url}/lead-share.html?token={token}"

    logger.info("[DC-SHARE] Token created for lead #%s by %s, doc_filter=%s, expires %s",
                lead_id, emp_name, doc_types, expires_at_utc.isoformat())
    return {
        "success":          True,
        "token":            token,
        "share_url":        share_url,
        "lead_name":        lead.name,
        "expires_at":       expires_at_utc.isoformat(),
        "expires_in_hours": 6,
        "doc_filter":       doc_types,
    }


@router.post("/leads/bulk-share-links")
def bulk_share_links(
    request: Request,
    body: dict = Body(...),
    db: Session = Depends(get_db),
    current_employee: StaffEmployee = Depends(get_current_staff_user),
):
    """
    Bulk-generate 6-hour share tokens for a list of lead IDs (used by export).
    Body: { "lead_ids": [1, 2, 3] }
    Returns: { "links": { "1": "https://...", "2": "https://..." } }
    """
    lead_ids = body.get("lead_ids", [])
    if not lead_ids or not isinstance(lead_ids, list):
        raise HTTPException(status_code=400, detail="lead_ids must be a non-empty list")
    if len(lead_ids) > 500:
        raise HTTPException(status_code=400, detail="Max 500 leads per bulk request")

    expires_at_utc = datetime.now(_tz.utc) + timedelta(hours=6)
    emp_name = getattr(current_employee, "name", None) or getattr(current_employee, "emp_code", "Staff")
    base_url = _canonical_base(request)

    links = {}
    for lid in lead_ids:
        try:
            tok = _secrets_mod.token_urlsafe(40)
            db.execute(text("""
                INSERT INTO crm_lead_share_tokens (token, lead_id, expires_at, created_by_id, created_by_name)
                VALUES (:tok, :lid, :exp, :uid, :uname)
            """), {"tok": tok, "lid": int(lid), "exp": expires_at_utc, "uid": current_employee.id, "uname": emp_name})
            links[str(lid)] = f"{base_url}/lead-share.html?token={tok}"
        except Exception as _e:
            logger.warning("[DC-SHARE] Bulk token failed for lead #%s: %s", lid, _e)
    db.commit()

    logger.info("[DC-SHARE] Bulk tokens created: %d leads by %s", len(links), emp_name)
    return {"success": True, "links": links, "expires_at": expires_at_utc.isoformat()}


@router.get("/share/{token}")
def view_share_link(token: str, db: Session = Depends(get_db)):
    """
    Public endpoint — no auth required.
    Returns lead details + solar docs if token is valid and not expired.
    """
    import json as _json
    row = db.execute(text("""
        SELECT id, token, lead_id, expires_at, created_by_name, created_at, doc_filter
        FROM crm_lead_share_tokens
        WHERE token = :tok
    """), {"tok": token}).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Link not found or already expired")

    now_utc = datetime.now(_tz.utc)
    exp = row.expires_at
    if exp.tzinfo is None:
        from datetime import timezone as tz_
        exp = exp.replace(tzinfo=tz_.utc)
    if now_utc > exp:
        raise HTTPException(status_code=410, detail="This link has expired")

    # Parse doc_filter
    included_doc_types = None
    try:
        if row.doc_filter:
            included_doc_types = _json.loads(row.doc_filter)
    except Exception:
        pass

    lead = db.execute(text("""
        SELECT
            cl.id, cl.name, cl.phone, cl.email, cl.address, cl.pincode,
            cl.status, cl.source, cl.application_no, cl.accepted_date,
            cl.aadhaar_number, cl.pan_number, cl.electricity_bill_number,
            cl.bank_account_number, cl.ifsc_code, cl.bank_branch, cl.loan_bank,
            cl.co_applicant_name, cl.co_applicant_phone,
            cl.co_applicant_aadhaar, cl.co_applicant_pan,
            cl.co_applicant_bank_account, cl.co_applicant_ifsc,
            cl.material_reach_date, cl.installation_date,
            cl.deal_value_total, cl.deal_value_received, cl.deal_value_balance,
            cl.next_followup_date, cl.created_at,
            se1.full_name AS telecaller_name, se2.full_name AS field_staff_name
        FROM crm_leads cl
        LEFT JOIN staff_employees se1 ON se1.id = cl.telecaller_id
        LEFT JOIN staff_employees se2 ON se2.id = cl.field_staff_id
        WHERE cl.id = :lid
    """), {"lid": row.lead_id}).fetchone()

    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    docs_rows = db.execute(text("""
        SELECT id, doc_category, doc_type, doc_label, doc_number,
               file_name, original_name, file_size, uploaded_by_name, uploaded_at
        FROM crm_lead_solar_documents
        WHERE lead_id = :lid
        ORDER BY doc_category, doc_type
    """), {"lid": row.lead_id}).fetchall()

    # Signature is NEVER shared via any public link regardless of doc_types filter
    _NEVER_SHARE_TYPES = {'signature'}
    # Filter docs if a doc_filter is set on this token
    filtered_docs_rows = [
        d for d in docs_rows
        if d.doc_type not in _NEVER_SHARE_TYPES
        and (included_doc_types is None or d.doc_type in included_doc_types)
    ]

    docs = [{
        "id":               d.id,
        "doc_category":     d.doc_category,
        "doc_type":         d.doc_type,
        "doc_label":        d.doc_label,
        "doc_number":       d.doc_number or "",
        "original_name":    d.original_name,
        "file_size":        d.file_size,
        "uploaded_by_name": d.uploaded_by_name,
        "uploaded_at":      d.uploaded_at.isoformat() if d.uploaded_at else None,
        "view_url":         f"/storage/{d.file_name}" if d.file_name else None,
        "download_url":     f"/storage/{d.file_name}" if d.file_name else None,
    } for d in filtered_docs_rows]

    def _str(v):
        return str(v) if v is not None else ""

    return {
        "success": True,
        "valid":   True,
        "expires_at": exp.isoformat(),
        "created_by": row.created_by_name,
        "included_doc_types": included_doc_types,
        "lead": {
            "id":                     lead.id,
            "name":                   _str(lead.name),
            "phone":                  _str(lead.phone),
            "email":                  _str(lead.email),
            "address":                _str(lead.address),
            "pincode":                _str(lead.pincode),
            "status":                 _str(lead.status),
            "source":                 _str(lead.source),
            "application_no":         _str(lead.application_no),
            "accepted_date":          lead.accepted_date.isoformat() if lead.accepted_date else "",
            "aadhaar_number":         _str(lead.aadhaar_number),
            "pan_number":             _str(lead.pan_number),
            "electricity_bill_number":_str(lead.electricity_bill_number),
            "bank_account_number":    _str(lead.bank_account_number),
            "ifsc_code":              _str(lead.ifsc_code),
            "bank_branch":            _str(lead.bank_branch),
            "loan_bank":              _str(lead.loan_bank),
            "co_applicant_name":      _str(lead.co_applicant_name),
            "co_applicant_phone":     _str(lead.co_applicant_phone),
            "co_applicant_aadhaar":   _str(lead.co_applicant_aadhaar),
            "co_applicant_pan":       _str(lead.co_applicant_pan),
            "co_applicant_bank_account": _str(lead.co_applicant_bank_account),
            "co_applicant_ifsc":      _str(lead.co_applicant_ifsc),
            "material_reach_date":    lead.material_reach_date.isoformat() if lead.material_reach_date else "",
            "installation_date":      lead.installation_date.isoformat() if lead.installation_date else "",
            "deal_value_total":       _str(lead.deal_value_total),
            "deal_value_received":    _str(lead.deal_value_received),
            "deal_value_balance":     _str(lead.deal_value_balance),
            "next_followup_date":     lead.next_followup_date.isoformat() if lead.next_followup_date else "",
            "created_at":             lead.created_at.isoformat() if lead.created_at else "",
            "telecaller_name":        _str(lead.telecaller_name),
            "field_staff_name":       _str(lead.field_staff_name),
        },
        "docs": docs,
        "docs_count": len(docs),
    }


# ─────────────────────────────────────────────────────────────────────────────
# DC-BUNDLE-PDF-001 (Jun 2026): Bank & DISCOM document bundle PDF endpoints
# Auth endpoint: /leads/{id}/solar-docs/bundle?section=bank|discom
# Public token endpoint: /share/{token}/bundle
# Uses PyMuPDF (fitz) to merge images + PDFs into a single downloadable PDF.
# ─────────────────────────────────────────────────────────────────────────────
_BANK_DOC_TYPES   = ['adhar','pan','powerbill','bank_book','house_tax','quotation','feasibility_letter']
_DISCOM_DOC_TYPES = ['annexure_a','annexure_c','annexure_c_technical','synchronisation_certificate','dcr_certificate','geotagging_photo']
_BUNDLE_DOC_LABELS = {
    'adhar':'Aadhaar Card','pan':'PAN Card','powerbill':'Electricity Bill',
    'bank_book':'Bank Book','house_tax':'House Tax Receipt',
    'quotation':'Quotation','feasibility_letter':'Feasibility Letter',
    'annexure_a':'Annexure-A','annexure_c':'Annexure-C (Project Completion)',
    'annexure_c_technical':'Annexure-C (Technical Details)',
    'synchronisation_certificate':'Synchronisation Certificate',
    'dcr_certificate':'DCR Certificate','geotagging_photo':'Geo Tagging Photo',
}

def _detect_fitz_filetype(data: bytes, filename: str) -> str:
    if data[:4] == b'%PDF': return 'pdf'
    if data[:8] == b'\x89PNG\r\n\x1a\n': return 'png'
    if data[:2] == b'\xff\xd8': return 'jpeg'
    ext = (filename.lower().rsplit('.', 1)[-1] if '.' in filename else '')
    return {'jpg': 'jpeg', 'jpeg': 'jpeg', 'png': 'png', 'gif': 'gif', 'webp': 'webp'}.get(ext, 'pdf')

def _build_bundle_pdf(file_names: list, labels: list, storage_svc) -> bytes:
    """Merge a list of storage files (images + PDFs) into one PDF via PyMuPDF."""
    import fitz
    out = fitz.open()
    for fn, lbl in zip(file_names, labels):
        data = storage_svc.download_file(fn)
        if not data:
            logger.warning("[DC-BUNDLE] File not found in storage: %s", fn)
            continue
        ft = _detect_fitz_filetype(data, fn)
        try:
            if ft == 'pdf':
                src = fitz.open(stream=data, filetype='pdf')
            else:
                img_doc = fitz.open(stream=data, filetype=ft)
                pdf_bytes = img_doc.convert_to_pdf()
                img_doc.close()
                src = fitz.open(stream=pdf_bytes, filetype='pdf')
            out.insert_pdf(src)
            src.close()
        except Exception as _be:
            logger.warning("[DC-BUNDLE] Skipped %s (%s): %s", fn, ft, _be)
    if len(out) == 0:
        blank = fitz.open()
        page = blank.new_page(width=595, height=842)
        page.insert_text((72, 400), 'No documents available for this bundle.', fontsize=12)
        result = blank.tobytes()
        blank.close()
        return result
    result = out.tobytes()
    out.close()
    return result

@router.get("/leads/{lead_id}/solar-docs/bundle")
def download_solar_docs_bundle(
    lead_id: int,
    section: str,
    db: Session = Depends(get_db),
    current_employee: StaffEmployee = Depends(get_current_staff_user),
):
    """
    DC-BUNDLE-PDF-001 (auth-gated): Stream merged PDF for bank|discom section.
    Read-only — fetches existing uploaded docs and merges into single PDF.
    """
    from app.services.object_storage import storage_service as _ss
    from fastapi.responses import Response as _R
    sec = section.lower()
    if sec == 'bank':
        doc_types = _BANK_DOC_TYPES
        label = 'Bank'
    elif sec == 'discom':
        doc_types = _DISCOM_DOC_TYPES
        label = 'DISCOM'
    else:
        raise HTTPException(status_code=400, detail="section must be 'bank' or 'discom'")
    lead = db.execute(text("SELECT id, name FROM crm_leads WHERE id = :lid"), {"lid": lead_id}).fetchone()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    if doc_types:
        placeholders = ','.join(f':t{i}' for i in range(len(doc_types)))
        params = {"lid": lead_id, **{f"t{i}": t for i, t in enumerate(doc_types)}}
        rows = db.execute(text(
            f"SELECT file_name, doc_type FROM crm_lead_solar_documents "
            f"WHERE lead_id = :lid AND doc_type IN ({placeholders}) AND file_name IS NOT NULL"
        ), params).fetchall()
    else:
        rows = []
    order_map = {t: i for i, t in enumerate(doc_types)}
    rows = sorted(rows, key=lambda r: order_map.get(r.doc_type, 999))
    file_names = [r.file_name for r in rows]
    labels_list = [_BUNDLE_DOC_LABELS.get(r.doc_type, r.doc_type) for r in rows]
    logger.info("[DC-BUNDLE] Lead #%s %s bundle: %d docs to merge", lead_id, label, len(file_names))
    pdf = _build_bundle_pdf(file_names, labels_list, _ss)
    safe = (lead.name or f'Lead{lead_id}').replace(' ', '_')
    return _R(content=pdf, media_type='application/pdf',
              headers={'Content-Disposition': f'attachment; filename="{safe}_{label}_Docs.pdf"'})

@router.get("/share/{token}/bundle")
def download_share_bundle(token: str, db: Session = Depends(get_db)):
    """
    DC-BUNDLE-PDF-001 (public/token-gated): Merge all docs in this share token into one PDF.
    No staff auth required — token acts as auth. Respects doc_filter on the token.
    """
    import json as _j
    from app.services.object_storage import storage_service as _ss
    from fastapi.responses import Response as _R
    from datetime import timezone as _tz2
    row = db.execute(text(
        "SELECT lead_id, expires_at, doc_filter FROM crm_lead_share_tokens WHERE token = :tok"
    ), {"tok": token}).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Link not found")
    exp = row.expires_at
    if exp.tzinfo is None:
        from datetime import timezone as _z
        exp = exp.replace(tzinfo=_z.utc)
    if datetime.now(exp.tzinfo) > exp:
        raise HTTPException(status_code=410, detail="This link has expired")
    included = None
    try:
        if row.doc_filter:
            included = _j.loads(row.doc_filter)
    except Exception:
        pass
    lead = db.execute(text("SELECT id, name FROM crm_leads WHERE id = :lid"), {"lid": row.lead_id}).fetchone()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    _NEVER = {'signature'}
    docs = db.execute(text(
        "SELECT file_name, doc_type FROM crm_lead_solar_documents "
        "WHERE lead_id = :lid AND file_name IS NOT NULL ORDER BY id"
    ), {"lid": row.lead_id}).fetchall()
    filtered = [d for d in docs if d.doc_type not in _NEVER and (included is None or d.doc_type in included)]
    if included:
        om = {t: i for i, t in enumerate(included)}
        filtered.sort(key=lambda d: om.get(d.doc_type, 999))
    file_names = [d.file_name for d in filtered]
    labels_list = [_BUNDLE_DOC_LABELS.get(d.doc_type, d.doc_type) for d in filtered]
    logger.info("[DC-BUNDLE] Share token bundle: lead #%s, %d docs", row.lead_id, len(file_names))
    pdf = _build_bundle_pdf(file_names, labels_list, _ss)
    safe = (lead.name or f'Lead{row.lead_id}').replace(' ', '_')
    return _R(content=pdf, media_type='application/pdf',
              headers={'Content-Disposition': f'attachment; filename="{safe}_Documents.pdf"'})

# ─────────────────────────────────────────────────────────────────────────────
# DC Protocol Apr 2026: Solar Vendor + Tech + Document Generation Endpoints
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/solar-vendors")
def get_solar_vendors(
    db: Session = Depends(get_db),
    current_employee: StaffEmployee = Depends(get_current_staff_user),
):
    """
    List all SOLAR type vendors from vendor_master.
    Returns vendor info including MNRE fields and bank details.
    """
    rows = db.execute(text("""
        SELECT id, vendor_code, vendor_name, vendor_type,
               gst_number, phone, email, address, city, state, pincode,
               bank_name, bank_branch, account_number, ifsc_code, account_holder_name,
               mnre_empanelled, mnre_reg_no, stamp_image_url, rep_signature_url,
               tech_signature_url, vendor_logo_url
        FROM vendor_master
        WHERE vendor_type = 'SOLAR' AND is_active = true
        ORDER BY vendor_name
    """)).fetchall()

    vendors = []
    for r in rows:
        vendors.append({
            "id":                   r.id,
            "vendor_code":          r.vendor_code or "",
            "vendor_name":          r.vendor_name or "",
            "vendor_type":          r.vendor_type or "",
            "gst_number":           r.gst_number or "",
            "phone":                r.phone or "",
            "email":                r.email or "",
            "address":              r.address or "",
            "city":                 r.city or "",
            "state":                r.state or "",
            "pincode":              r.pincode or "",
            "bank_name":            r.bank_name or "",
            "bank_branch":          r.bank_branch or "",
            "account_number":       r.account_number or "",
            "ifsc_code":            r.ifsc_code or "",
            "account_holder_name":  r.account_holder_name or "",
            "mnre_empanelled":      bool(r.mnre_empanelled),
            "mnre_reg_no":          r.mnre_reg_no or "",
            "vendor_logo_url":      r.vendor_logo_url or "",
            "stamp_image_url":      r.stamp_image_url or "",
            "rep_signature_url":    r.rep_signature_url or "",
            "tech_signature_url":   r.tech_signature_url or "",
        })
    return {"vendors": vendors}


@router.post("/solar-vendors/{vendor_id}/reset-password")
def reset_solar_vendor_password(
    vendor_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    current_employee: StaffEmployee = Depends(get_current_staff_user),
):
    """
    [DC-SOLAR-PWD-RESET] Staff can reset a solar vendor's portal password.
    Accepts {"new_password": "..."}.
    Finds the OfficialPartner for this vendor (by legacy_vendor_id or SV-{code})
    and updates the password hash.  Also updates vendor_master password column if needed.
    """
    from app.core.security import SecurityManager

    vendor = db.query(VendorMaster).filter(
        VendorMaster.id == vendor_id,
        VendorMaster.vendor_type == 'SOLAR',
        VendorMaster.is_active == True,
    ).first()
    if not vendor:
        raise HTTPException(status_code=404, detail="Solar vendor not found")

    new_password = (payload.get("new_password") or "").strip()
    if not new_password or len(new_password) < 4:
        raise HTTPException(status_code=400, detail="Password must be at least 4 characters")

    pw_hash = SecurityManager.get_password_hash(new_password)

    # Find OfficialPartner by legacy_vendor_id first, then by SV-{code}
    op = db.query(OfficialPartner).filter(
        OfficialPartner.category == 'VENDOR',
        OfficialPartner.legacy_vendor_id == vendor_id
    ).first()
    if not op:
        sv_code = f"SV-{vendor.vendor_code}"
        op = db.query(OfficialPartner).filter(OfficialPartner.partner_code == sv_code).first()

    if op:
        op.password_hash = pw_hash
        if op.legacy_vendor_id is None:
            op.legacy_vendor_id = vendor_id
        db.commit()
        return {"success": True, "message": f"Password reset for {vendor.vendor_name} ({vendor.vendor_code})"}
    else:
        # Auto-provision the OfficialPartner with the new password
        new_op = OfficialPartner(
            partner_code=f"SV-{vendor.vendor_code}",
            partner_name=vendor.vendor_name,
            category='VENDOR',
            partner_type='SOLAR',
            phone=vendor.phone,
            email=vendor.email,
            contact_person=vendor.contact_person,
            is_active=True,
            login_status='active',
            password_hash=pw_hash,
            legacy_vendor_id=vendor_id,
            failed_login_attempts=0,
            module_settings={},
        )
        db.add(new_op)
        db.commit()
        return {"success": True, "message": f"Portal account created & password set for {vendor.vendor_name} ({vendor.vendor_code})"}


@router.get("/leads/{lead_id}/solar-preflight")
def get_solar_preflight(
    lead_id: int,
    db: Session = Depends(get_db),
    current_employee: StaffEmployee = Depends(get_current_staff_user),
):
    """
    [DC-SOLAR-PREFLIGHT] Return all data needed for Commissioning and Annexure IV
    pre-flight modals: lead fields, tech fields, and vendor fields with pincode.
    """
    lead = db.execute(text("""
        SELECT id, name, phone, email, address, city, state, pincode,
               kw_size, discom, grid_phase, application_no, sc_number,
               sanction_date, discom_reg_no, mnre_app_ref, consumer_no,
               latitude, longitude, aadhaar_number
        FROM crm_leads WHERE id = :lid
    """), {"lid": lead_id}).fetchone()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    tech = db.query(CRMSolarLeadTech).filter(CRMSolarLeadTech.lead_id == lead_id).first()
    tech_d = tech.to_dict() if tech else {}

    vendor_d = {}
    vendor_id = tech_d.get("last_quote_vendor_id") if tech_d else None
    if vendor_id:
        v = db.execute(text("""
            SELECT id, vendor_name, vendor_code, gst_number, address, city, state, pincode,
                   phone, email, bank_name, bank_branch, account_number, account_holder_name, ifsc_code,
                   mnre_empanelled, mnre_reg_no, stamp_image_url, tech_signature_url, vendor_logo_url
            FROM vendor_master WHERE id = :vid AND vendor_type = 'SOLAR'
        """), {"vid": vendor_id}).fetchone()
        if v:
            vendor_d = {col: getattr(v, col, None) for col in v._fields}

    lead_d = {col: getattr(lead, col, None) for col in lead._fields}

    return {
        "success": True,
        "lead": lead_d,
        "tech": tech_d,
        "vendor": vendor_d,
        "vendor_id": vendor_id,
    }


@router.get("/vendors/{vendor_id}/next-quote-ref")
def get_next_quote_ref(
    vendor_id: int,
    db: Session = Depends(get_db),
    current_employee: StaffEmployee = Depends(get_current_staff_user),
):
    """
    Get the next quotation reference number for a vendor.
    Format: MNR-{VENDOR_CODE}-{NNNN}
    """
    vendor = db.execute(text("""
        SELECT vendor_code FROM vendor_master WHERE id = :vid AND vendor_type = 'SOLAR'
    """), {"vid": vendor_id}).fetchone()

    if not vendor:
        raise HTTPException(status_code=404, detail="Solar vendor not found")

    count_row = db.execute(text("""
        SELECT COUNT(*) as cnt FROM crm_lead_solar_documents
        WHERE doc_type = 'quotation' AND file_name LIKE :pattern
    """), {"pattern": f"%{vendor.vendor_code}%"}).fetchone()

    next_num = (count_row.cnt or 0) + 1
    ref_no = f"MNR-{vendor.vendor_code}-{next_num:04d}"
    return {"ref_no": ref_no, "vendor_code": vendor.vendor_code}


@router.get("/leads/{lead_id}/solar-tech")
def get_solar_tech(
    lead_id: int,
    db: Session = Depends(get_db),
    current_employee: StaffEmployee = Depends(get_current_staff_user),
):
    """
    Get solar technical details for a lead.
    Returns empty dict if no record exists yet.
    """
    lead = db.execute(text("SELECT id FROM crm_leads WHERE id = :lid"), {"lid": lead_id}).fetchone()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    tech = db.query(CRMSolarLeadTech).filter(CRMSolarLeadTech.lead_id == lead_id).first()
    if not tech:
        return {"tech": None}
    return {"tech": tech.to_dict()}


@router.put("/leads/{lead_id}/solar-tech")
def upsert_solar_tech(
    lead_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    current_employee: StaffEmployee = Depends(get_current_staff_user),
):
    """
    Upsert solar technical details for a lead.
    Creates a new record if none exists, otherwise updates.
    """
    from datetime import date as _date
    import json as _json

    lead = db.execute(text("SELECT id, company_id FROM crm_leads WHERE id = :lid"), {"lid": lead_id}).fetchone()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    UPDATABLE_FIELDS = [
        "panel_make", "panel_model", "panel_capacity_each_w", "num_panels",
        "panel_serial_numbers", "panel_type", "panel_technology", "tilt_angle",
        "azimuth", "cell_manufacturer", "rfid_position",
        "inverter_make", "inverter_model", "inverter_serial_no", "inverter_capacity_kw",
        "inverter_type", "inverter_efficiency_pct", "num_inverters",
        "grid_voltage", "string1_voc", "string2_voc", "mppt_type",
        "purchase_order_no", "purchase_order_date", "cell_gst_invoice_no",
        "installation_date", "mounting_type", "structure_material",
        "wind_speed_tolerance", "surface_finish",
        "dc_cable_make", "dc_cable_sqmm", "dc_cable_length_m",
        "ac_cable_inv_acdb_make", "ac_cable_inv_acdb_sqmm", "ac_cable_inv_acdb_length_m",
        "ac_cable_acdb_panel_make", "ac_cable_acdb_panel_sqmm", "ac_cable_acdb_panel_length_m",
        "acdb_count", "dcdb_count", "ac_earthing_nos", "dc_earthing_nos",
        "la_nos", "earth_resistance_ac", "earth_resistance_dc", "earth_resistance_la",
        "acdb_ic_voltage", "acdb_og_voltage", "monitoring_user_id", "monitoring_password",
        "danger_board",
        "last_quote_vendor_id", "last_quote_kw_size", "last_quote_value",
        "last_quote_discount", "last_quote_final", "last_quote_subsidy",
        "last_quote_ref_no", "last_quote_generated_at",
        "panel_brand", "panel_warranty",
        "inverter_brand", "inverter_warranty",
    ]

    now_str = datetime.now().isoformat()

    tech = db.query(CRMSolarLeadTech).filter(CRMSolarLeadTech.lead_id == lead_id).first()
    if tech is None:
        tech = CRMSolarLeadTech(
            lead_id=lead_id,
            company_id=lead.company_id,
            created_at=now_str,
        )
        db.add(tech)

    # [DC-SOLAR-NUMERIC-NORM] Strip unit suffixes from INTEGER columns before setattr.
    # Users commonly type "550WP" or "6 panels" — the DB column is INTEGER.
    import re as _re
    _INT_FIELDS = {"panel_capacity_each_w", "num_panels"}
    for _nf in _INT_FIELDS:
        if _nf in payload and payload[_nf] is not None:
            _stripped = _re.sub(r'[^\d.]', '', str(payload[_nf])).strip()
            try:
                payload[_nf] = int(float(_stripped)) if _stripped else None
            except (ValueError, TypeError):
                logger.warning("[DC-SOLAR-TECH] Cannot parse '%s' as int for %s — setting None", payload[_nf], _nf)
                payload[_nf] = None

    for field in UPDATABLE_FIELDS:
        if field in payload:
            setattr(tech, field, payload[field])

    tech.updated_at = now_str
    db.commit()
    db.refresh(tech)

    logger.info("[DC-SOLAR-TECH] Upserted tech for lead #%s by %s", lead_id, current_employee.emp_code)
    return {"success": True, "tech": tech.to_dict()}


@router.post("/leads/solar-tech-bulk")
def solar_tech_bulk(
    payload: dict,
    db: Session = Depends(get_db),
    current_employee: StaffEmployee = Depends(get_current_staff_user),
):
    """
    DC-DCR-BULK-001: Fetch solar tech for multiple leads in one call.
    Returns dict of lead_id (str) → tech dict.
    Used by Export for DCR Excel builder.
    """
    lead_ids = payload.get("lead_ids", [])
    if not lead_ids:
        return {"tech_map": {}}
    techs = db.query(CRMSolarLeadTech).filter(CRMSolarLeadTech.lead_id.in_(lead_ids)).all()
    return {"tech_map": {str(t.lead_id): t.to_dict() for t in techs}}


# [DC-SOLAR-FIELDS-PATCH] Patchable solar-specific lead fields (filled via Missing Data dialog)
_SOLAR_LEAD_PATCHABLE = {
    "kw_size", "discom", "sc_number", "consumer_no", "mnre_app_ref",
    "sanction_date", "discom_reg_no", "latitude", "longitude",
    "grid_phase", "aadhaar_number", "loan_bank", "bank_branch", "bank_account_number",
    "application_no", "submit_date", "complete_date",
}

@router.patch("/leads/{lead_id}/solar-fields")
def patch_solar_lead_fields(
    lead_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    current_employee: StaffEmployee = Depends(get_current_staff_user),
):
    """
    [DC-SOLAR-FIELDS-PATCH] Save solar-specific lead fields (kw_size, sc_number, discom, etc.)
    filled in the Missing Data dialog back to crm_leads so they are reused across all documents.
    Only whitelisted fields are accepted; existing non-empty values are NOT overwritten.
    """
    lead = db.execute(text("SELECT id FROM crm_leads WHERE id = :lid"), {"lid": lead_id}).fetchone()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    updates = {}
    for field, value in payload.items():
        if field not in _SOLAR_LEAD_PATCHABLE:
            continue
        val = str(value).strip() if value is not None else ""
        if not val:
            continue
        updates[field] = val

    if not updates:
        return {"success": True, "updated": []}

    # DC-COMPLETE-DATE-LOCK: once complete_date is set, only MR10025/MR10001 can modify it
    if 'complete_date' in updates:
        _existing_cd = db.execute(
            text("SELECT complete_date FROM crm_leads WHERE id = :lid"), {"lid": lead_id}
        ).scalar()
        if _existing_cd is not None and current_employee.emp_code not in ('MR10025', 'MR10001'):
            raise HTTPException(
                status_code=403,
                detail="Complete Date is locked — only Subash (MR10025) or VGK Mentor (MR10001) can modify it once it has been set."
            )

    set_parts = [f"{k} = :{k}" for k in updates]
    updates["lid"] = lead_id
    db.execute(text(f"UPDATE crm_leads SET {', '.join(set_parts)} WHERE id = :lid"), updates)
    db.commit()

    logger.info("[DC-SOLAR-FIELDS-PATCH] Saved fields %s for lead #%s by %s",
                list(k for k in updates if k != "lid"), lead_id, current_employee.emp_code)
    return {"success": True, "updated": [k for k in updates if k != "lid"]}


@router.get("/leads/{lead_id}/invoice-prefill")
def get_invoice_prefill(
    lead_id: int,
    db: Session = Depends(get_db),
    current_employee: StaffEmployee = Depends(get_current_staff_user),
):
    """
    Return all data needed to pre-fill the invoice generate modal:
    lead fields, last quote values from tech, and vendor details.
    """
    lead = db.execute(text("""
        SELECT id, name, phone, email, address, area, city, state, pincode,
               kw_size, discom, grid_phase, application_no, sc_number
        FROM crm_leads WHERE id = :lid
    """), {"lid": lead_id}).fetchone()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    tech = db.query(CRMSolarLeadTech).filter(CRMSolarLeadTech.lead_id == lead_id).first()
    tech_d = tech.to_dict() if tech else {}

    vendor_d = {}
    vendor_id = tech_d.get("last_quote_vendor_id") if tech_d else None
    if vendor_id:
        v = db.execute(text("""
            SELECT id, vendor_name, vendor_code, gst_number, address, city, state, pincode,
                   phone, email, bank_name, bank_branch, account_number, account_holder_name, ifsc_code
            FROM vendor_master WHERE id = :vid AND vendor_type = 'SOLAR'
        """), {"vid": vendor_id}).fetchone()
        if v:
            vendor_d = {col: getattr(v, col, None) for col in v._fields}

    ref_no = tech_d.get("last_quote_ref_no") or ""
    invoice_number = f"INV-{ref_no}" if ref_no else ""

    return {
        "success": True,
        "lead": {
            "id":            lead.id,
            "name":          lead.name or "",
            "phone":         lead.phone or "",
            "email":         lead.email or "",
            "address":       lead.address or "",
            "area":          lead.area or "",
            "city":          lead.city or "",
            "state":         lead.state or "",
            "pincode":       lead.pincode or "",
            "kw_size":       lead.kw_size or "",
            "discom":        lead.discom or "",
            "grid_phase":    lead.grid_phase or "",
            "application_no":lead.application_no or "",
            "sc_number":     lead.sc_number or "",
        },
        "tech": {
            "last_quote_vendor_id":  tech_d.get("last_quote_vendor_id"),
            "last_quote_kw_size":    tech_d.get("last_quote_kw_size") or "",
            "last_quote_value":      tech_d.get("last_quote_value"),
            "last_quote_discount":   tech_d.get("last_quote_discount"),
            "last_quote_final":      tech_d.get("last_quote_final"),
            "last_quote_subsidy":    tech_d.get("last_quote_subsidy"),
            "last_quote_ref_no":     ref_no,
        },
        "vendor": vendor_d,
        "invoice_number": invoice_number,
    }


@router.post("/leads/{lead_id}/generate-solar-doc")
async def generate_solar_doc(
    lead_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    current_employee: StaffEmployee = Depends(get_current_staff_user),
):
    """
    Generate a solar document (quotation, annexure, certificate, etc.) as PDF.
    Flow:
      1. Validate doc_type is generatable
      2. Load lead + vendor + tech from DB
      3. Check for required fields → return 422 with missing_fields if incomplete
      4. Generate PDF bytes
      5. Upload to object storage
      6. Upsert crm_lead_solar_documents record
      7. Return view_url + doc metadata

    Body: { doc_type, vendor_id?, kw_size?, quote_value?, discount?, final_amount?, subsidy? }
    """
    from app.services.solar_doc_generator import DOC_GENERATORS, REQUIRED_FIELDS, FIELD_LABELS
    from app.services.object_storage import storage_service
    import io
    from datetime import date as _date

    doc_type = payload.get("doc_type", "")
    if doc_type not in GENERATABLE_DOC_TYPES:
        raise HTTPException(status_code=400, detail=f"doc_type '{doc_type}' is not generatable. Valid: {list(GENERATABLE_DOC_TYPES.keys())}")

    generator_key = GENERATABLE_DOC_TYPES[doc_type]

    # ── Load Lead ────────────────────────────────────────────────────────────
    lead = db.execute(text("""
        SELECT l.*, c.company_name
        FROM crm_leads l
        LEFT JOIN associated_companies c ON c.id = l.company_id
        WHERE l.id = :lid
    """), {"lid": lead_id}).fetchone()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    # ── Load Vendor (if needed) ──────────────────────────────────────────────
    vendor_id = payload.get("vendor_id")
    vendor = None
    if vendor_id:
        vendor = db.execute(text("""
            SELECT * FROM vendor_master WHERE id = :vid AND vendor_type = 'SOLAR'
        """), {"vid": vendor_id}).fetchone()
        if not vendor:
            raise HTTPException(status_code=404, detail="Solar vendor not found")
    elif generator_key in ("quotation", "invoice"):
        raise HTTPException(status_code=400, detail="vendor_id is required for quotation/invoice generation")

    # ── Load Tech ────────────────────────────────────────────────────────────
    tech = db.query(CRMSolarLeadTech).filter(CRMSolarLeadTech.lead_id == lead_id).first()

    # [DC-SOLAR-VENDOR-AUTO] For non-quotation/invoice docs, auto-carry vendor from last quotation
    if vendor is None and generator_key not in ("quotation", "invoice") and tech and tech.last_quote_vendor_id:
        _auto_v = db.execute(text("""
            SELECT * FROM vendor_master WHERE id = :vid AND vendor_type = 'SOLAR'
        """), {"vid": tech.last_quote_vendor_id}).fetchone()
        if _auto_v:
            vendor = _auto_v
            vendor_id = tech.last_quote_vendor_id
            logger.info("[DC-SOLAR-VENDOR-AUTO] Auto-loaded vendor_id=%s for lead #%s doc=%s", vendor_id, lead_id, doc_type)

    # ── Build context dict ───────────────────────────────────────────────────
    def _s(val):
        return str(val) if val is not None else ""

    lead_dict = {col: getattr(lead, col, None) for col in lead._fields}
    tech_dict = tech.to_dict() if tech else {}
    vendor_dict = {}
    if vendor:
        vendor_dict = {col: getattr(vendor, col, None) for col in vendor._fields}

    # [DC-SOLAR-FIELD-FALLBACK] Carry kw_size from last quotation into lead context if not on lead record
    if not lead_dict.get("kw_size") and tech_dict.get("last_quote_kw_size"):
        lead_dict["kw_size"] = tech_dict["last_quote_kw_size"]

    # [DC-SOLAR-INSTALL-DATE-FALLBACK] installation_date is saved on the lead record (crm_leads)
    # but Annexure-A required-fields check looks in tech_dict. Carry it over so the check passes.
    if not tech_dict.get("installation_date") and lead_dict.get("installation_date"):
        tech_dict["installation_date"] = lead_dict["installation_date"]

    # Override with any inline payload values (for quotation / invoice)
    override_fields = [
        "kw_size", "quote_value", "discount", "final_amount", "subsidy",
        "quote_ref_no", "remaining_loan_amount",
        "invoice_number", "invoice_date", "application_charge", "net_meters_cost",
        "discom_reg_date", "panel_brand",
    ]
    extra = {k: payload.get(k) for k in override_fields if payload.get(k) is not None}

    # ── Auto-derive invoice number from last quote ref if not supplied ────────
    if generator_key == "invoice" and not extra.get("invoice_number"):
        _ref = tech_dict.get("last_quote_ref_no") if tech_dict else None
        if _ref:
            extra["invoice_number"] = f"INV-{_ref}"

    ctx = {
        "lead": lead_dict,
        "vendor": vendor_dict,
        "tech": tech_dict,
        **extra,
    }

    # ── DC-SOLAR-PREFLIGHT: Inject preflight modal overrides into sub-dicts ──
    # These fields come from the Commissioning / Annexure IV pre-flight modals.
    # They are merged BEFORE the required-fields check so they satisfy validation.
    _TECH_PREFLIGHT_FIELDS = {
        "inverter_serial_no", "inverter_capacity_kw", "string1_voc", "string2_voc",
        "grid_voltage", "acdb_ic_voltage", "acdb_og_voltage",
        "panel_make", "panel_type", "num_panels", "panel_capacity_each_w",
        "panel_serial_numbers", "inverter_make", "consumer_category",
        # DC Fix (Apr 2026): fields used by annexure_c_completion / commissioning that
        # were previously excluded — without these, values entered in the missing-fields
        # modal were never injected into tech_dict nor saved back to the DB.
        "tilt_angle", "rfid_position", "inverter_efficiency_pct",
        "inverter_type", "mppt_type", "inverter_model",
        "panel_technology", "azimuth",
        # DC Fix (Apr 2026): Annexure C pre-flight manual-input fields
        "purchase_order_date", "cell_manufacturer", "cell_gst_invoice_no",
        # DC Fix (Apr 2026): Annexure A pre-flight manual-input fields
        "purchase_order_no",
        # DC Fix (Apr 2026): Annexure C Technical Details pre-flight fields
        "monitoring_user_id", "monitoring_password",
        # Annexure A row 10 — installation date
        "installation_date",
    }
    _LEAD_PREFLIGHT_FIELDS = {"sanction_date", "discom_reg_no", "kw_size", "sc_number"}
    _VENDOR_PREFLIGHT_FIELDS = {"pincode"}
    for _f in _TECH_PREFLIGHT_FIELDS:
        _v = payload.get(_f)
        if _v is not None and str(_v).strip():
            tech_dict[_f] = str(_v).strip()
    for _f in _LEAD_PREFLIGHT_FIELDS:
        _v = payload.get(_f)
        if _v is not None and str(_v).strip():
            lead_dict[_f] = str(_v).strip()
    for _f in _VENDOR_PREFLIGHT_FIELDS:
        _v = payload.get(_f)
        if _v is not None and str(_v).strip():
            vendor_dict[_f] = str(_v).strip()

    # ── DC-SOLAR-PREFLIGHT: Save overrides back to DB so next generation reuses them ──
    if payload.get("_save_preflight"):
        try:
            # Save tech overrides back to crm_solar_lead_tech
            _tech_saves = {k: payload.get(k) for k in _TECH_PREFLIGHT_FIELDS if payload.get(k) is not None and str(payload.get(k)).strip()}
            # [DC-SOLAR-NUMERIC-NORM] Strip unit suffixes (WP, W, KW, etc.) from INTEGER columns
            # before saving. Users commonly type "550WP" or "4 KW" — the DB column is INTEGER.
            _INT_TECH_FIELDS = {"panel_capacity_each_w", "num_panels"}
            for _nf in _INT_TECH_FIELDS:
                if _nf in _tech_saves:
                    import re as _re
                    _stripped = _re.sub(r'[^\d.]', '', str(_tech_saves[_nf])).strip()
                    try:
                        _tech_saves[_nf] = int(float(_stripped)) if _stripped else None
                        if _tech_saves[_nf] is None:
                            _tech_saves.pop(_nf)
                    except (ValueError, TypeError):
                        logger.warning("[DC-SOLAR-PREFLIGHT] Cannot parse '%s' as int for %s — skipping save", _tech_saves[_nf], _nf)
                        _tech_saves.pop(_nf)
            # DC Fix: parse purchase_order_date string → date object before saving to DB
            if "purchase_order_date" in _tech_saves:
                _raw_pod = str(_tech_saves["purchase_order_date"]).strip()
                _parsed_pod = None
                for _fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%d-%m-%y", "%d/%m/%y"):
                    try:
                        _parsed_pod = datetime.strptime(_raw_pod, _fmt).date()
                        break
                    except ValueError:
                        continue
                if _parsed_pod:
                    _tech_saves["purchase_order_date"] = _parsed_pod
                else:
                    logger.warning("[DC-SOLAR-PREFLIGHT] Unrecognised purchase_order_date format '%s' — skipping save", _raw_pod)
                    _tech_saves.pop("purchase_order_date")
            if _tech_saves:
                if tech:
                    for _k, _v2 in _tech_saves.items():
                        try:
                            setattr(tech, _k, _v2)
                        except Exception:
                            pass
                    db.commit()
                else:
                    # Create tech record if missing
                    tech = CRMSolarLeadTech(lead_id=lead_id, **{k: v for k, v in _tech_saves.items() if hasattr(CRMSolarLeadTech, k)})
                    db.add(tech)
                    db.commit()
            # Save lead overrides back to crm_leads
            _lead_saves = {k: payload.get(k) for k in _LEAD_PREFLIGHT_FIELDS if payload.get(k) is not None and str(payload.get(k)).strip()}
            if _lead_saves:
                # ── DC-DATE-NORM: normalise sanction_date to ISO YYYY-MM-DD ──────
                if "sanction_date" in _lead_saves:
                    _raw_sd = str(_lead_saves["sanction_date"]).strip()
                    _parsed_sd = None
                    for _fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%d-%m-%y", "%d/%m/%y", "%-d-%-m-%Y", "%-d/%-m/%Y"):
                        try:
                            _parsed_sd = datetime.strptime(_raw_sd, _fmt).date()
                            break
                        except ValueError:
                            continue
                    if _parsed_sd:
                        _lead_saves["sanction_date"] = _parsed_sd.isoformat()
                    else:
                        # Unrecognised format — remove to avoid DB error
                        logger.warning("[DC-SOLAR-PREFLIGHT] Unrecognised sanction_date format '%s' — skipping save", _raw_sd)
                        _lead_saves.pop("sanction_date")
                # ─────────────────────────────────────────────────────────────────
                if _lead_saves:
                    _set_parts = [f"{k} = :{k}" for k in _lead_saves]
                    _lead_saves["_lid"] = lead_id
                    db.execute(text(f"UPDATE crm_leads SET {', '.join(_set_parts)} WHERE id = :_lid"), _lead_saves)
                    db.commit()
            # Save vendor pincode if provided
            _v_pin = payload.get("pincode")
            if _v_pin and vendor_id:
                db.execute(text("UPDATE vendor_master SET pincode = :pin WHERE id = :vid"),
                           {"pin": str(_v_pin).strip(), "vid": vendor_id})
                db.commit()
        except Exception as _pf_err:
            logger.warning("[DC-SOLAR-PREFLIGHT] Save-back failed (non-fatal): %s", _pf_err)
            # [DC-SOLAR-SESSION-RESET] Must rollback the dead transaction so the session
            # is usable for the subsequent PDF generation / ORM access below.
            try:
                db.rollback()
            except Exception:
                pass

    # ── Auto-calculate num_panels if not stored (2 panels per KW) ────────────
    if not tech_dict.get("num_panels"):
        kw_str = str(ctx.get("kw_size") or lead_dict.get("kw_size") or "")
        try:
            kw_num = float(kw_str.replace("KW", "").replace("kw", "").strip())
            if kw_num > 0:
                tech_dict["num_panels"] = str(int(kw_num * 2))
        except (ValueError, TypeError):
            pass

    # ── Missing fields check ─────────────────────────────────────────────────
    required = REQUIRED_FIELDS.get(generator_key, {})
    missing = []
    for source, field_list in required.items():
        for fname in field_list:
            field_spec = f"{source}.{fname}"
            if source == "lead":
                # Payload overrides (e.g. kw_size from quotation modal) count as lead values
                val = lead_dict.get(fname) or extra.get(fname)
            elif source == "tech":
                val = tech_dict.get(fname)
            elif source == "vendor":
                val = vendor_dict.get(fname)
            elif source == "params":
                val = extra.get(fname)
            else:
                val = ctx.get(fname)
            if val is None or (isinstance(val, str) and not val.strip()):
                label = FIELD_LABELS.get(field_spec) or FIELD_LABELS.get(fname, fname)
                missing.append({"field": field_spec, "label": label})

    if missing:
        return JSONResponse(status_code=422, content={"missing_fields": missing})

    # ── Generate PDF ─────────────────────────────────────────────────────────
    try:
        generator_fn = DOC_GENERATORS[generator_key]
        lead_d = ctx["lead"]
        vendor_d = ctx.get("vendor", {})
        tech_d = ctx.get("tech", {})
        if generator_key in ("quotation", "co_applicant_quotation"):
            pdf_bytes = generator_fn(
                lead=lead_d,
                vendor=vendor_d,
                kw_size=str(ctx.get("kw_size") or ""),
                quote_value=float(ctx.get("quote_value") or 0),
                discount=float(ctx.get("discount") or 0),
                final_amount=float(ctx.get("final_amount") or 0),
                subsidy_amount=float(ctx.get("subsidy") or 0),
                ref_no=str(ctx.get("quote_ref_no") or ""),
                panel_brand=str(ctx.get("panel_brand") or ""),
            )
        elif generator_key == "invoice":
            pdf_bytes = generator_fn(
                lead=lead_d,
                vendor=vendor_d,
                tech=tech_d,
                invoice_number=str(ctx.get("invoice_number") or ""),
                invoice_date=ctx.get("invoice_date") or None,
                kw_size=str(ctx.get("kw_size") or lead_d.get("kw_size") or ""),
                quote_value=float(ctx.get("quote_value") or 0),
                discount=float(ctx.get("discount") or 0),
                final_amount=float(ctx.get("final_amount") or 0),
                subsidy_amount=float(ctx.get("subsidy") or 0),
                application_charge=str(ctx.get("application_charge") or "Actuals"),
                net_meters_cost=str(ctx.get("net_meters_cost") or ""),
            )
        elif generator_key == "synchronisation_certificate":
            pdf_bytes = generator_fn(
                lead=lead_d,
                vendor=vendor_d,
                discom_reg_date=str(ctx.get("discom_reg_date") or ""),
            )
        elif generator_key == "bank_submission_letter":
            pdf_bytes = generator_fn(
                lead=lead_d,
                vendor=vendor_d,
                remaining_loan_amount=str(ctx.get("remaining_loan_amount") or ""),
            )
        else:
            pdf_bytes = generator_fn(lead=lead_d, vendor=vendor_d, tech=tech_d)
    except Exception as exc:
        logger.error("[DC-SOLAR-GEN] PDF generation failed for %s / lead %s: %s", doc_type, lead_id, exc)
        raise HTTPException(status_code=500, detail="PDF generation failed. Please try again or contact support.")

    # ── Upload to object storage ─────────────────────────────────────────────
    from datetime import datetime as _dt
    timestamp = _dt.now().strftime("%Y%m%d_%H%M%S")
    storage_key = f"solar_docs/{lead_id}/{doc_type}_{timestamp}.pdf"
    ok = storage_service.upload_file(storage_key, pdf_bytes)
    if not ok:
        raise HTTPException(status_code=500, detail="Failed to upload generated PDF to object storage")

    doc_label = SOLAR_DOC_TYPES.get(doc_type, doc_type.replace("_", " ").title())
    if generator_key == "invoice":
        doc_number = extra.get("invoice_number", "") or ""
    else:
        doc_number = extra.get("quote_ref_no", "") or ""
    emp_name = getattr(current_employee, "full_name", None) or getattr(current_employee, "emp_code", "Staff")

    # ── Upsert crm_lead_solar_documents ─────────────────────────────────────
    existing = db.execute(text("""
        SELECT id FROM crm_lead_solar_documents
        WHERE lead_id = :lid AND doc_type = :dtype
    """), {"lid": lead_id, "dtype": doc_type}).fetchone()

    if existing:
        db.execute(text("""
            UPDATE crm_lead_solar_documents
            SET file_name        = :fname,
                original_name    = :oname,
                file_size        = :fsize,
                uploaded_by_id   = :uid,
                uploaded_by_name = :uname,
                uploaded_at      = NOW(),
                doc_number       = CASE WHEN :dnum != '' THEN :dnum ELSE doc_number END,
                notes            = 'Auto-generated'
            WHERE id = :did
        """), {
            "fname": storage_key,
            "oname": f"{doc_type}_{timestamp}.pdf",
            "fsize": len(pdf_bytes),
            "uid":   current_employee.id,
            "uname": emp_name,
            "dnum":  doc_number,
            "did":   existing.id,
        })
    else:
        db.execute(text("""
            INSERT INTO crm_lead_solar_documents
                (lead_id, doc_category, doc_type, doc_label, doc_number,
                 file_name, original_name, file_size,
                 uploaded_by_id, uploaded_by_name, uploaded_at, notes)
            VALUES
                (:lid, 'consumer', :dtype, :dlabel, :dnum,
                 :fname, :oname, :fsize,
                 :uid, :uname, NOW(), 'Auto-generated')
        """), {
            "lid":    lead_id,
            "dtype":  doc_type,
            "dlabel": doc_label,
            "dnum":   doc_number,
            "fname":  storage_key,
            "oname":  f"{doc_type}_{timestamp}.pdf",
            "fsize":  len(pdf_bytes),
            "uid":    current_employee.id,
            "uname":  emp_name,
        })

    db.commit()

    # ── Save quote details to tech record ────────────────────────────────────
    if generator_key == "quotation" and vendor_id:
        now_str = datetime.now().isoformat()
        tech_rec = db.query(CRMSolarLeadTech).filter(CRMSolarLeadTech.lead_id == lead_id).first()
        if tech_rec is None:
            tech_rec = CRMSolarLeadTech(lead_id=lead_id, company_id=lead.company_id, created_at=now_str)
            db.add(tech_rec)
        tech_rec.last_quote_vendor_id = vendor_id
        tech_rec.last_quote_kw_size = str(extra.get("kw_size", ""))
        tech_rec.last_quote_value = extra.get("quote_value")
        tech_rec.last_quote_discount = extra.get("discount")
        tech_rec.last_quote_final = extra.get("final_amount")
        tech_rec.last_quote_subsidy = extra.get("subsidy")
        tech_rec.last_quote_ref_no = doc_number
        tech_rec.last_quote_generated_at = _date.today()
        tech_rec.updated_at = now_str
        db.commit()
        # [DC-SOLAR-FIELD-PERSIST] Also save kw_size to crm_leads so annexures find it directly
        _kw_save = str(extra.get("kw_size", "") or "").strip()
        if _kw_save:
            db.execute(text(
                "UPDATE crm_leads SET kw_size = :kw WHERE id = :lid AND (kw_size IS NULL OR kw_size = '')"
            ), {"kw": _kw_save, "lid": lead_id})
            db.commit()
            logger.info("[DC-SOLAR-FIELD-PERSIST] Persisted kw_size=%s to crm_leads lead #%s", _kw_save, lead_id)

    logger.info("[DC-SOLAR-GEN] Generated %s for lead #%s by %s (size=%s)", doc_type, lead_id, emp_name, len(pdf_bytes))

    return {
        "success":    True,
        "doc_type":   doc_type,
        "doc_label":  doc_label,
        "doc_number": doc_number,
        "view_url":   f"/storage/{storage_key}",
        "file_size":  len(pdf_bytes),
    }


@router.post("/leads/{lead_id}/download-complete-bundle")
async def download_complete_bundle(
    lead_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    current_employee: StaffEmployee = Depends(get_current_staff_user),
):
    """
    Merge the main generated doc + Geo Solar Photo + Aadhaar + PAN into one PDF.
    Fetches each file from object storage (skips any missing companions).
    Streams the merged PDF as a download.
    """
    from app.services.solar_doc_generator import merge_docs_to_pdf
    from app.services.object_storage import storage_service
    from fastapi.responses import Response as FastAPIResponse

    doc_type = payload.get("doc_type", "")
    if not doc_type:
        raise HTTPException(status_code=400, detail="doc_type is required")

    COMPANION_TYPES = ["invoice", "geotagging_photo", "adhar", "pan"]

    # ── Fetch all doc records for this lead ───────────────────────────────────
    all_types = [doc_type] + COMPANION_TYPES
    rows = db.execute(text("""
        SELECT doc_type, file_name, original_name
        FROM crm_lead_solar_documents
        WHERE lead_id = :lid AND doc_type = ANY(:types)
    """), {"lid": lead_id, "types": all_types}).fetchall()

    rec_map = {r.doc_type: r for r in rows}

    main_rec = rec_map.get(doc_type)
    if not main_rec or not main_rec.file_name:
        raise HTTPException(
            status_code=400,
            detail=f"Main document '{SOLAR_DOC_TYPES.get(doc_type, doc_type)}' has not been generated yet. "
                   "Please generate it first, then download the bundle."
        )

    # ── Download main doc ─────────────────────────────────────────────────────
    items = []
    main_bytes = storage_service.download_file(main_rec.file_name)
    if not main_bytes:
        raise HTTPException(status_code=500, detail="Failed to fetch main document from storage")
    items.append((main_bytes, main_rec.file_name))

    # ── Download available companion docs ─────────────────────────────────────
    included = [SOLAR_DOC_TYPES.get(doc_type, doc_type)]
    skipped = []
    for ctype in COMPANION_TYPES:
        rec = rec_map.get(ctype)
        if rec and rec.file_name:
            data = storage_service.download_file(rec.file_name)
            if data:
                hint = rec.original_name or rec.file_name
                items.append((data, hint))
                included.append(SOLAR_DOC_TYPES.get(ctype, ctype))
            else:
                skipped.append(SOLAR_DOC_TYPES.get(ctype, ctype))
        else:
            skipped.append(SOLAR_DOC_TYPES.get(ctype, ctype))

    # ── Merge ─────────────────────────────────────────────────────────────────
    try:
        merged_bytes = merge_docs_to_pdf(items)
    except Exception as exc:
        logger.error("[DC-BUNDLE] Merge failed for lead #%s / %s: %s", lead_id, doc_type, exc)
        raise HTTPException(status_code=500, detail=f"PDF merge error: {exc}")

    safe_label = SOLAR_DOC_TYPES.get(doc_type, doc_type).replace(" ", "_").replace("/", "-")
    filename = f"Lead{lead_id}_{safe_label}_Bundle.pdf"
    logger.info("[DC-BUNDLE] Bundle for lead #%s / %s — %d docs merged, %d skipped",
                lead_id, doc_type, len(items), len(skipped))

    return FastAPIResponse(
        content=merged_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ─────────────────────────────────────────────────────────────────────────────
# DC Protocol (Apr 2026): N001 + N002 + N004 — VGK status / WA share / claim
# ─────────────────────────────────────────────────────────────────────────────

def _derive_lead_handler_type(lead) -> str:
    """Derive human-readable handler/source type from lead fields."""
    src = (lead.source or '').lower()
    if 'walk' in src or 'walk_in' in src:
        return 'Walk-In'
    if getattr(lead, 'is_vgk_program', False) or (lead.source_ref_type or '').lower() == 'vgk':
        return 'VGK4U'
    if 'showroom' in src or getattr(lead, 'showroom_supported', False):
        return 'Showroom'
    return 'Direct'


@router.get("/leads/{lead_id}/vgk-status")
def get_lead_vgk_status(
    lead_id: int,
    company_id: int = Query(...),
    db: Session = Depends(get_db),
    current_employee: StaffEmployee = Depends(get_current_staff_user)
):
    """DC Protocol N001 — Check if lead's phone is a registered VGK member."""
    lead = db.query(CRMLead).filter(CRMLead.id == lead_id, CRMLead.company_id == company_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    phone_raw = (lead.phone or '').replace(' ', '').replace('-', '').replace('+', '')
    if not phone_raw:
        return {"success": True, "is_vgk": False}

    from app.models.staff_accounts import OfficialPartner as _OP
    member = db.query(_OP).filter(
        _OP.category == 'VGK_TEAM',
        or_(
            _OP.phone == phone_raw,
            _OP.phone == phone_raw[-10:] if len(phone_raw) >= 10 else _OP.phone == phone_raw,
        )
    ).first()

    if not member:
        return {"success": True, "is_vgk": False}

    points_balance = float(getattr(member, 'vgk_points_balance', 0) or 0)
    return {
        "success": True,
        "is_vgk": True,
        "partner_id": member.id,
        "partner_code": member.partner_code,
        "partner_name": member.partner_name,
        "phone": member.phone,
        "points_balance": points_balance,
        "is_active": member.is_active,
        "vgk_role": getattr(member, 'vgk_role', None),
    }


@router.post("/leads/{lead_id}/register-as-vgk")
def register_lead_as_vgk(
    lead_id: int,
    company_id: int = Query(...),
    db: Session = Depends(get_db),
    current_employee: StaffEmployee = Depends(get_current_staff_user)
):
    """DC Protocol N001 — Register lead's contact as a new VGK member under company default upline."""
    import random as _rnd
    from decimal import Decimal as _Dec
    lead = db.query(CRMLead).filter(CRMLead.id == lead_id, CRMLead.company_id == company_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    phone_raw = (lead.phone or '').replace(' ', '').replace('-', '').replace('+', '')
    if not phone_raw:
        raise HTTPException(status_code=400, detail="Lead has no phone number")

    from app.models.staff_accounts import OfficialPartner as _OP
    existing = db.query(_OP).filter(_OP.category == 'VGK_TEAM',
        or_(_OP.phone == phone_raw, _OP.phone == phone_raw[-10:] if len(phone_raw) >= 10 else _OP.phone == phone_raw)
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="This phone is already a VGK member: " + existing.partner_code)

    # DC Protocol: default upline is VGK ROOT VGK07102207 (company default)
    VGK_DEFAULT_ROOT = 'VGK07102207'
    default_upline = db.query(_OP).filter(_OP.partner_code == VGK_DEFAULT_ROOT, _OP.category == 'VGK_TEAM').first()
    parent_id = default_upline.id if default_upline else None

    # Generate unique VGK partner code
    for _ in range(50):
        rand4 = _rnd.randint(1000, 9999)
        code = f"VGK0710{rand4}"
        if not db.query(_OP).filter(_OP.partner_code == code).first():
            break
    else:
        raise HTTPException(status_code=500, detail="Could not generate unique VGK code")

    import secrets as _sec
    auto_pwd = _sec.token_hex(4).upper()
    from app.core.security import SecurityManager
    pwd_hash = SecurityManager.get_password_hash(auto_pwd)
    partner_name = lead.name or ('Lead#' + str(lead_id))

    from pytz import timezone as _tz
    _now = datetime.now(_tz('Asia/Kolkata')).replace(tzinfo=None)

    member = _OP(
        company_id=company_id,
        partner_code=code,
        partner_name=partner_name,
        phone=phone_raw[-10:] if len(phone_raw) >= 10 else phone_raw,
        email=lead.email,
        category='VGK_TEAM',
        is_active=False,
        parent_partner_id=parent_id,
        vgk_role='VGK_ASSOCIATE',
        vgk_points_balance=_Dec('0'),
        password_hash=pwd_hash,
        created_at=_now,
        updated_at=_now,
    )
    db.add(member)
    db.commit()
    db.refresh(member)

    # Credit 10,000 welcome bonus
    try:
        from app.services.vgk_commission import add_vgk_points_entry
        add_vgk_points_entry(
            db=db, partner_id=member.id, points_credit=_Dec('10000'), points_debit=_Dec('0'),
            reason_code='WELCOME_BONUS', reference_type='registration', reference_id=None,
            notes='Welcome bonus — registered via CRM lead #' + str(lead_id),
            created_by=current_employee.id,
        )
        db.commit()
        db.refresh(member)
    except Exception as _wb_err:
        logger.warning(f"[VGK-CRM] Welcome bonus non-fatal: {_wb_err}")

    # Log registration in wa_share_logs for dashboard tracking
    try:
        db.execute(text(
            "INSERT INTO crm_wa_share_logs (staff_id, lead_id, share_type, created_at) "
            "VALUES (:sid, :lid, 'vgk_registration', :ts)"
        ), {"sid": current_employee.id, "lid": lead_id, "ts": _now})
        db.commit()
    except Exception:
        pass

    logger.info(f"[VGK-CRM] Registered {code} from lead #{lead_id} by {current_employee.emp_code}")
    return {
        "success": True,
        "partner_code": code,
        "partner_name": partner_name,
        "phone": member.phone,
        "auto_password": auto_pwd,
        "points_balance": 10000.0,
        "is_active": False,
    }


@router.post("/leads/{lead_id}/log-whatsapp-share")
def log_whatsapp_share(
    lead_id: int,
    company_id: int = Query(...),
    share_type: str = Query("vgk_creds"),
    db: Session = Depends(get_db),
    current_employee: StaffEmployee = Depends(get_current_staff_user)
):
    """DC Protocol N001/N002 — Log a WhatsApp share click for dashboard tracking."""
    from pytz import timezone as _tz
    _now = datetime.now(_tz('Asia/Kolkata')).replace(tzinfo=None)
    try:
        db.execute(text(
            "INSERT INTO crm_wa_share_logs (staff_id, lead_id, share_type, created_at) "
            "VALUES (:sid, :lid, :stype, :ts)"
        ), {"sid": current_employee.id, "lid": lead_id, "stype": share_type, "ts": _now})
        db.commit()
    except Exception as e:
        logger.warning(f"[DC-N002] log-whatsapp-share non-fatal: {e}")
    return {"success": True}


@router.get("/unclaimed-leads")
def get_unclaimed_leads(
    company_id: int = Query(...),
    since_minutes: int = Query(30, ge=1, le=1440, description="Look back N minutes for unclaimed leads"),
    db: Session = Depends(get_db),
    current_employee: StaffEmployee = Depends(get_current_staff_user)
):
    """DC Protocol N004 — Get recent VGK/partner-created leads without a telecaller (for claim popup)."""
    from pytz import timezone as _tz
    _now = datetime.now(_tz('Asia/Kolkata')).replace(tzinfo=None)
    cutoff = _now.replace(tzinfo=None) if True else _now
    from datetime import timedelta as _td
    cutoff = _now - _td(minutes=since_minutes)

    unclaimed = db.query(CRMLead).filter(
        CRMLead.company_id == company_id,
        CRMLead.telecaller_id == None,
        CRMLead.created_at >= cutoff,
        or_(
            CRMLead.is_vgk_program == True,
            CRMLead.source_ref_type.in_(['vgk', 'vgk_partner', 'partner']),
            CRMLead.created_by_type.in_(['vgk', 'vgk_partner', 'partner']),
        )
    ).order_by(CRMLead.created_at.desc()).limit(20).all()

    result = []
    for lead in unclaimed:
        result.append({
            "id": lead.id,
            "name": lead.name,
            "phone": lead.phone,
            "source_ref_type": lead.source_ref_type,
            "source_ref_name": lead.source_ref_name,
            "created_at": lead.created_at.isoformat() if lead.created_at else None,
            "handler_type": _derive_lead_handler_type(lead),
            "status": lead.status,
        })
    return {"success": True, "data": result, "count": len(result)}


@router.post("/leads/{lead_id}/claim")
def claim_lead(
    lead_id: int,
    company_id: int = Query(...),
    db: Session = Depends(get_db),
    current_employee: StaffEmployee = Depends(get_current_staff_user)
):
    """DC Protocol N004 — Atomically claim an unclaimed lead as telecaller."""
    from sqlalchemy import update as _upd
    from pytz import timezone as _tz
    _now = datetime.now(_tz('Asia/Kolkata')).replace(tzinfo=None)

    result = db.execute(
        text(
            "UPDATE crm_leads SET telecaller_id = :emp_id, updated_at = :ts "
            "WHERE id = :lid AND company_id = :cid AND telecaller_id IS NULL "
            "RETURNING id"
        ),
        {"emp_id": current_employee.id, "ts": _now, "lid": lead_id, "cid": company_id}
    )
    db.commit()
    claimed = result.fetchone()
    if not claimed:
        return {"success": False, "message": "Lead already claimed by another staff member"}

    logger.info(f"[DC-N004] Lead #{lead_id} claimed by {current_employee.emp_code}")
    return {"success": True, "message": f"Lead claimed! You are now the assigned telecaller.", "lead_id": lead_id}


# ── DC_CIBIL_ADVANCE_001: Solar CIBIL Advance Staff Endpoints ─────────────────

@router.get("/leads/{lead_id}/solar-advance")
def get_solar_advance(
    lead_id: int,
    db: Session = Depends(get_db),
    current_employee: StaffEmployee = Depends(get_current_staff_user),
):
    """Staff: view the CIBIL advance record for a solar lead."""
    row = db.execute(text("""
        SELECT a.id, a.entry_number, a.advance_amount, a.status,
               a.stage_at_eligibility, a.cibil_score_at_check,
               a.wallet_before_release, a.wallet_after_release,
               a.released_at, a.released_by_id,
               a.recovery_amount, a.recovery_reason, a.recovered_at,
               a.adjustment_amount, a.adjustment_entry_id, a.adjusted_at,
               a.notes, a.created_at,
               p.partner_name, p.partner_code,
               l.cibil_confirmed, l.cibil_score, l.solar_pipeline_status
        FROM vgk_solar_cibil_advances a
        JOIN crm_leads l ON l.id = a.lead_id
        LEFT JOIN official_partners p ON p.id = a.partner_id
        WHERE a.lead_id = :lid
        LIMIT 1
    """), {'lid': lead_id}).fetchone()

    if not row:
        return {'found': False, 'message': 'No advance record for this lead'}

    return {
        'found': True,
        'id': row.id,
        'entry_number': row.entry_number,
        'advance_amount': float(row.advance_amount or 0),
        'status': row.status,
        'stage_at_eligibility': row.stage_at_eligibility,
        'cibil_score_at_check': row.cibil_score_at_check,
        'wallet_before_release': float(row.wallet_before_release or 0),
        'wallet_after_release': float(row.wallet_after_release or 0),
        'released_at': row.released_at.isoformat() if row.released_at else None,
        'recovery_amount': float(row.recovery_amount or 0),
        'recovery_reason': row.recovery_reason,
        'recovered_at': row.recovered_at.isoformat() if row.recovered_at else None,
        'adjustment_amount': float(row.adjustment_amount or 0),
        'adjusted_at': row.adjusted_at.isoformat() if row.adjusted_at else None,
        'notes': row.notes,
        'created_at': row.created_at.isoformat() if row.created_at else None,
        'partner_name': row.partner_name,
        'partner_code': row.partner_code,
        'lead_cibil_confirmed': row.cibil_confirmed,
        'lead_cibil_score': row.cibil_score,
        'lead_solar_pipeline_status': row.solar_pipeline_status,
    }


@router.post("/leads/{lead_id}/solar-advance/release")
def release_solar_advance(
    lead_id: int,
    notes: Optional[str] = None,
    db: Session = Depends(get_db),
    current_employee: StaffEmployee = Depends(get_current_staff_user),
):
    """Staff: release the ₹1,000 CIBIL advance to the VGK member's wallet."""
    from app.services.vgk_solar_advance import release_advance
    result = release_advance(db, lead_id, released_by_id=current_employee.id, notes=notes)
    if not result.get('success'):
        raise HTTPException(status_code=400, detail=result.get('error', 'Release failed'))

    advance_row = result.get('_advance_row')
    if advance_row is not None:
        try:
            from app.services.vgk_cash_income import record_solar_advance_as_income_row
            _mir = record_solar_advance_as_income_row(db, advance_row, released_by_id=current_employee.id)
            db.commit()
            result['income_entry'] = _mir
            logger.info(f'[VGK-SOLAR-HOOK] advance#{advance_row.id} mirrored → income entry {_mir.get("entry_number")}')
        except Exception as _se:
            logger.warning(f'[VGK-SOLAR-HOOK] income mirror failed for lead#{lead_id} (non-fatal): {_se}')

    return result


@router.post("/leads/{lead_id}/solar-advance/recover")
def recover_solar_advance(
    lead_id: int,
    reason: Optional[str] = None,
    db: Session = Depends(get_db),
    current_employee: StaffEmployee = Depends(get_current_staff_user),
):
    """Staff: manually trigger recovery of a released CIBIL advance (e.g. lead cancelled)."""
    from app.services.vgk_solar_advance import recover_advance
    result = recover_advance(db, lead_id, reason=reason, recovered_by_id=current_employee.id)
    if not result.get('success'):
        raise HTTPException(status_code=400, detail=result.get('error', 'Recovery failed'))
    return result


@router.get("/solar-advances")
def list_solar_advances_staff(
    status: Optional[str] = Query(None),
    company_id: Optional[int] = Query(None),
    vgk_mode: bool = Query(False),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_employee: StaffEmployee = Depends(get_current_staff_user),
):
    """Staff: list all Solar CIBIL advances — filterable by status.

    vgk_mode=true: returns advances for ALL VGK_TEAM partners regardless of company_id.
    This is needed for the unified income page Zynova tab which must show pending advances
    even when the advance company_id differs from the staff's base_company_id.
    """
    if vgk_mode:
        # Join on official_partners to scope to VGK_TEAM category only
        where = ["p.category = 'VGK_TEAM'"]
        params = {}
    else:
        cid = company_id or current_employee.base_company_id
        where = ["a.company_id = :cid"]
        params = {'cid': cid}

    if status:
        where.append("a.status = :st")
        params['st'] = status

    where_sql = " AND ".join(where)

    if vgk_mode:
        count_sql = f"""SELECT COUNT(*) FROM vgk_solar_cibil_advances a
                        JOIN official_partners p ON p.id = a.partner_id
                        WHERE {where_sql}"""
    else:
        count_sql = f"SELECT COUNT(*) FROM vgk_solar_cibil_advances a WHERE {where_sql}"

    total = db.execute(text(count_sql), params).scalar()

    if vgk_mode:
        list_sql = f"""
            SELECT a.id, a.entry_number, a.advance_amount, a.status,
                   a.stage_at_eligibility, a.cibil_score_at_check,
                   a.released_at, a.recovery_amount, a.adjustment_amount,
                   a.created_at, a.lead_id,
                   p.partner_name, p.partner_code,
                   l.name AS lead_name, l.cibil_confirmed, l.cibil_score
            FROM vgk_solar_cibil_advances a
            JOIN official_partners p ON p.id = a.partner_id
            LEFT JOIN crm_leads l ON l.id = a.lead_id
            WHERE {where_sql}
            ORDER BY a.created_at DESC
            LIMIT :lim OFFSET :off"""
    else:
        list_sql = f"""
            SELECT a.id, a.entry_number, a.advance_amount, a.status,
                   a.stage_at_eligibility, a.cibil_score_at_check,
                   a.released_at, a.recovery_amount, a.adjustment_amount,
                   a.created_at, a.lead_id,
                   p.partner_name, p.partner_code,
                   l.name AS lead_name, l.cibil_confirmed, l.cibil_score
            FROM vgk_solar_cibil_advances a
            LEFT JOIN official_partners p ON p.id = a.partner_id
            LEFT JOIN crm_leads l ON l.id = a.lead_id
            WHERE {where_sql}
            ORDER BY a.created_at DESC
            LIMIT :lim OFFSET :off"""

    rows = db.execute(text(list_sql), {**params, 'lim': limit, 'off': (page - 1) * limit}).fetchall()

    return {
        'total': total,
        'page': page,
        'advances': [{
            'id': r.id,
            'entry_number': r.entry_number,
            'lead_id': r.lead_id,
            'lead_name': r.lead_name,
            'advance_amount': float(r.advance_amount or 0),
            'status': r.status,
            'stage_at_eligibility': r.stage_at_eligibility,
            'cibil_score_at_check': r.cibil_score_at_check,
            'released_at': r.released_at.isoformat() if r.released_at else None,
            'recovery_amount': float(r.recovery_amount or 0),
            'adjustment_amount': float(r.adjustment_amount or 0),
            'created_at': r.created_at.isoformat() if r.created_at else None,
            'partner_name': r.partner_name,
            'partner_code': r.partner_code,
            'lead_cibil_confirmed': r.cibil_confirmed,
            'lead_cibil_score': r.cibil_score,
        } for r in rows]
    }


# DC-HCI-001 (Jul 2026): Preview endpoint — returns income entries that would be
# cancelled / adjusted if the source/handler on a lead were changed.
# Called by the frontend confirmation modal BEFORE sending the PUT.
@router.get("/leads/{lead_id}/income-correction-preview")
async def get_income_correction_preview(
    lead_id: int,
    company_id: int = Query(...),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid),
):
    lead = db.query(CRMLead).filter(
        CRMLead.id == lead_id,
        CRMLead.company_id == company_id,
    ).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    from app.services.vgk_income_correction import get_income_correction_preview
    preview = get_income_correction_preview(db, lead_id)
    return {"success": True, "data": preview}


# DC-GS-WEEKLY-001 (Jul 2026): Ground Source Wise Weekly Lead Count Report
# Per-ground-source lead counts: Total (all-time) + W-0..W-5 (IST Mon–Sun calendar weeks).
# Supports all source types: MNR, VGK, Staff, Partner.
# Associated-employee filter: VGK partners where registered_by_emp_code matches.
@router.get("/ground-source-weekly")
async def get_ground_source_weekly_report(
    category: Optional[str] = Query(None, description="Lead category filter (Solar / EV B2B / etc.)"),
    gs_type_filter: Optional[str] = Query(None, description="Source type: mnr | vgk | staff | all"),
    associated_emp_code: Optional[str] = Query(None, description="Filter VGK partner rows by registered_by_emp_code"),
    company_id_filter: Optional[int] = Query(None, description="Admin override: filter to a specific company"),
    db: Session = Depends(get_db),
    current_employee: StaffEmployee = Depends(get_current_staff_user),
):
    import pytz as _gspytz
    from datetime import datetime as _gsdt, timedelta as _gstd
    from sqlalchemy import func as _gsf, case as _gsc, and_ as _gsand, or_ as _gsor

    # ── IST week boundaries (Mon 00:00 IST = W-0 start) ──────────────────────
    _IST = _gspytz.timezone('Asia/Kolkata')
    _now = _gsdt.now(_IST)
    _days_mon = _now.weekday()          # 0 = Monday
    _w0_start = (_now - _gstd(days=_days_mon)).replace(
        hour=0, minute=0, second=0, microsecond=0
    ).replace(tzinfo=None)              # IST naive (matches DB storage)
    _ws = [_w0_start - _gstd(weeks=i) for i in range(7)]   # ws[0]=W0, ws[6]=W6 start

    def _wk(start, end):
        """Count leads where created_at ∈ [start, end)."""
        if end is None:
            cond = CRMLead.created_at >= start
        else:
            cond = _gsand(CRMLead.created_at >= start, CRMLead.created_at < end)
        return _gsf.coalesce(_gsf.sum(_gsc((cond, 1), else_=0)), 0)

    _gs_id_col  = _gsf.coalesce(CRMLead.source_ref_id, CRMLead.mnr_handler_id)
    _gs_typ_col = _gsf.coalesce(CRMLead.source_ref_type, 'mnr')

    # ── Company scope ─────────────────────────────────────────────────────────
    # VGK partners bring leads across ALL companies (MNR, MyntReal, Zynova…).
    # A single-company view loses the majority of their referrals.
    # Rule: admins see the full cross-company picture; non-admins see only
    # their own company.  An explicit company_id_filter always wins.
    _staff_type = (current_employee.staff_type or '').upper()
    _is_admin   = is_vgk_admin(_staff_type)

    _src_notnull = _gsor(CRMLead.source_ref_id.isnot(None), CRMLead.mnr_handler_id.isnot(None))
    if company_id_filter and _is_admin:
        base = db.query(CRMLead).filter(CRMLead.company_id == company_id_filter, _src_notnull)
    elif _is_admin:
        base = db.query(CRMLead).filter(_src_notnull)   # cross-company — no company_id filter
    else:
        base = db.query(CRMLead).filter(
            CRMLead.company_id == current_employee.base_company_id, _src_notnull)
    if category:
        base = base.filter(CRMLead.category == category)

    if gs_type_filter and gs_type_filter != 'all':
        _PART = {'partner', 'vgk_partner', 'vgk'}
        if gs_type_filter == 'mnr':
            base = base.filter(
                _gsor(
                    CRMLead.source_ref_type == 'mnr',
                    _gsand(CRMLead.source_ref_type.is_(None), CRMLead.mnr_handler_id.isnot(None)),
                )
            )
        elif gs_type_filter == 'vgk':
            base = base.filter(CRMLead.source_ref_type.in_(list(_PART)))
        elif gs_type_filter == 'staff':
            base = base.filter(CRMLead.source_ref_type == 'staff')

    # ── Associated-employee filter (VGK partners registered by that employee) ─
    if associated_emp_code:
        from app.models.staff_accounts import OfficialPartner as _GSOP_F
        _pids = [str(p.id) for p in db.query(_GSOP_F.id).filter(
            _GSOP_F.registered_by_emp_code == associated_emp_code
        ).all()]
        if not _pids:
            return {"success": True, "data": [], "week_labels": [], "registered_employees": []}
        base = base.filter(
            _gsor(CRMLead.source_ref_id.in_(_pids), CRMLead.mnr_handler_id.in_(_pids))
        )

    # ── Aggregation query ─────────────────────────────────────────────────────
    gs_rows = base.with_entities(
        _gs_id_col.label('gs_id'),
        _gs_typ_col.label('gs_type'),
        _gsf.count(CRMLead.id).label('total'),
        _wk(_ws[0], None   ).label('w0'),
        _wk(_ws[1], _ws[0] ).label('w1'),
        _wk(_ws[2], _ws[1] ).label('w2'),
        _wk(_ws[3], _ws[2] ).label('w3'),
        _wk(_ws[4], _ws[3] ).label('w4'),
        _wk(_ws[5], _ws[4] ).label('w5'),
    ).group_by(
        _gs_id_col, _gs_typ_col
    ).having(
        _gsf.count(CRMLead.id) > 0
    ).order_by(_gsf.count(CRMLead.id).desc()).all()

    # ── Name resolution ───────────────────────────────────────────────────────
    _PART_TYPES  = {'partner', 'vgk_partner', 'vgk'}
    _STAFF_TYPES = {'staff'}
    _name_map  = {}
    _regby_map = {}     # gs_id → registered_by_emp_code

    _mnr_ids    = [r.gs_id for r in gs_rows if r.gs_id and (r.gs_type or 'mnr') not in _PART_TYPES | _STAFF_TYPES]
    _part_ids   = []
    _staff_ecds = [r.gs_id for r in gs_rows if r.gs_id and (r.gs_type or '') in _STAFF_TYPES]
    for _gr in gs_rows:
        if _gr.gs_id and (_gr.gs_type or '') in _PART_TYPES:
            try: _part_ids.append(int(_gr.gs_id))
            except (ValueError, TypeError): pass

    try:
        from app.models.user import User as _GsUsr
        for _u in db.query(_GsUsr).filter(_GsUsr.id.in_(_mnr_ids)).all():
            _name_map[_u.id] = getattr(_u, 'name', None) or str(_u.id)
    except Exception:
        pass
    try:
        from app.models.staff_accounts import OfficialPartner as _GsOp
        for _p in db.query(_GsOp).filter(_GsOp.id.in_(_part_ids)).all():
            _nm = _p.partner_name or _p.contact_person or _p.partner_code or f'Partner#{_p.id}'
            _name_map[str(_p.id)] = _nm
            if _p.registered_by_emp_code:
                _regby_map[str(_p.id)] = _p.registered_by_emp_code
    except Exception:
        pass
    try:
        for _se in db.query(StaffEmployee).filter(StaffEmployee.emp_code.in_(_staff_ecds)).all():
            _n = _se.full_name or f"{_se.first_name or ''} {_se.last_name or ''}".strip() or _se.emp_code
            _name_map[_se.emp_code] = _n
    except Exception:
        pass

    # ── Registered-employees dropdown list ────────────────────────────────────
    _reg_employees = []
    try:
        from app.models.staff_accounts import OfficialPartner as _GsOp2
        # Admins see all companies; non-admins scoped to their company
        _op2_q = db.query(_GsOp2.registered_by_emp_code).filter(
            _GsOp2.registered_by_emp_code.isnot(None),
            _GsOp2.registered_by_emp_code != '',
        )
        if not _is_admin:
            _op2_q = _op2_q.filter(_GsOp2.company_id == current_employee.base_company_id)
        _ec_rows = _op2_q.distinct().all()
        _ec_list = [e[0] for e in _ec_rows]
        if _ec_list:
            for _re in db.query(StaffEmployee).filter(StaffEmployee.emp_code.in_(_ec_list)).all():
                _rn = _re.full_name or f"{_re.first_name or ''} {_re.last_name or ''}".strip() or _re.emp_code
                _reg_employees.append({'emp_code': _re.emp_code, 'name': _rn})
    except Exception:
        pass

    # ── Build response data ───────────────────────────────────────────────────
    data = [
        {
            'gs_id':   r.gs_id or '',
            'gs_name': _name_map.get(r.gs_id, r.gs_id or '—'),
            'gs_type': r.gs_type or 'mnr',
            'total':   int(r.total),
            'w0': int(r.w0), 'w1': int(r.w1), 'w2': int(r.w2),
            'w3': int(r.w3), 'w4': int(r.w4), 'w5': int(r.w5),
            'registered_by_emp_code': _regby_map.get(r.gs_id, ''),
        }
        for r in gs_rows
    ]

    # ── Week header labels (date ranges for display) ──────────────────────────
    def _wr(i):
        s = _ws[i]; e = _ws[i - 1] - _gstd(days=1) if i > 0 else _now.replace(tzinfo=None)
        return f"{s.strftime('%d %b')}–{e.strftime('%d %b')}"
    week_labels = [
        f"W-0 This Week ({_wr(0)})",
        f"W-1 Last Week ({_wr(1)})",
        f"W-2 ({_wr(2)})",
        f"W-3 ({_wr(3)})",
        f"W-4 ({_wr(4)})",
        f"W-5 ({_wr(5)})",
    ]

    return {
        "success": True,
        "data": data,
        "week_labels": week_labels,
        "registered_employees": sorted(_reg_employees, key=lambda x: x['name']),
        "generated_at": _now.isoformat(),
    }


@router.get("/ground-source-leads")
async def get_ground_source_leads(
    gs_id: str = Query(..., description="Ground source ID"),
    gs_type: str = Query('mnr', description="Source type"),
    category: Optional[str] = Query(None),
    company_id_filter: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_employee: StaffEmployee = Depends(get_current_staff_user),
):
    """Individual leads for a specific ground source — powers expandable row in GS report."""
    from sqlalchemy import or_ as _gl_or
    from app.models.staff_accounts import AssociatedCompany as _GlAC
    from app.models.signup_category import SignupCategory as _GlSC
    _staff_type = (current_employee.staff_type or '').upper()
    _is_admin   = is_vgk_admin(_staff_type)

    # Same cross-company rule as the aggregate: admins see all companies
    _lead_filter = _gl_or(CRMLead.source_ref_id == gs_id, CRMLead.mnr_handler_id == gs_id)
    if company_id_filter and _is_admin:
        q = db.query(CRMLead).filter(CRMLead.company_id == company_id_filter, _lead_filter)
    elif _is_admin:
        q = db.query(CRMLead).filter(_lead_filter)
    else:
        q = db.query(CRMLead).filter(CRMLead.company_id == current_employee.base_company_id, _lead_filter)

    rows = q.order_by(CRMLead.created_at.desc()).limit(300).all()

    # Build lookup maps (category names + company names)
    _cat_ids = list({l.category_id for l in rows if l.category_id})
    _cat_map = {}
    try:
        for _sc in db.query(_GlSC).filter(_GlSC.id.in_(_cat_ids)).all():
            _cat_map[_sc.id] = _sc.name
    except Exception:
        pass

    _co_ids = list({l.company_id for l in rows if l.company_id})
    _co_map = {}
    try:
        for _ac in db.query(_GlAC).filter(_GlAC.id.in_(_co_ids)).all():
            _co_map[_ac.id] = _ac.company_name
    except Exception:
        pass

    def _stage(l):
        if l.solar_pipeline_status:
            return l.solar_pipeline_status.replace('_', ' ').title()
        if getattr(l, 'ev_b2b_stage', None):
            return l.ev_b2b_stage.replace('_', ' ').title()
        return '—'

    return {
        "success": True,
        "leads": [
            {
                "id":           l.id,
                "name":         l.name or '—',
                "phone":        l.phone or '—',
                "category":     _cat_map.get(l.category_id, f'Cat#{l.category_id}') if l.category_id else '—',
                "status":       l.status or '—',
                "stage":        _stage(l),
                "created_at":   l.created_at.strftime('%d %b %Y') if l.created_at else '—',
                "deal_value":   round(l.deal_value_total or 0),
                "dvr":          round(l.deal_value_received or 0),
                "company_id":   l.company_id,
                "company_name": _co_map.get(l.company_id, f'Co#{l.company_id}'),
            }
            for l in rows
        ],
        "total": len(rows),
    }
