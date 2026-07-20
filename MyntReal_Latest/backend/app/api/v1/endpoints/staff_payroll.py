"""
Staff Payroll Management API Endpoints (DC Protocol Compliant)
Complete payroll management with salary configuration, statutory deductions, and SFMS integration

Key Features:
- Payroll profile CRUD (salary structure, statutory details)
- Cycle management (create, lock attendance, generate)
- Salary calculation engine (earnings, deductions, net)
- Three-tier approval workflow (VGK_SUPREME → Director → HR/Accounts)
- Consultant invoice management
- Document generation (offer letter, payslip)
- SFMS ledger integration

Created: Jan 07, 2026
DC Protocol: company_id on all tables for data segregation
WVV Protocol: Role-based visibility (Employee own, HR/Accounts all)
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Body
from pydantic import BaseModel, Field, validator
from sqlalchemy.orm import Session
from sqlalchemy import and_, func, desc, or_
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from decimal import Decimal
import pytz
import logging
import calendar

from app.core.database import get_db
from app.models.staff import StaffEmployee, StaffDepartment, StaffMenuMaster, StaffEmployeeMenuSettings
from app.models.staff_accounts import AssociatedCompany
from app.models.staff_attendance_sheet import StaffAttendanceSheet, AttendanceStatus
from app.models.staff_payroll import (
    StaffPayrollProfile, StaffPayrollStatutoryConfig, StaffPayrollCycle, StaffPayrollRun,
    StaffPayrollDeduction, StaffConsultantInvoice, StaffPayrollDocument, StaffPayrollAuditLog,
    StaffPayrollAllowanceCatalog,
    EmploymentType, TaxRegime, PayrollCycleStatus, PayrollRunStatus, PaymentStatus,
    ConsultantInvoiceStatus, ConsultantInvoiceSource, PayrollDocumentType, DeductionType,
    StatutoryConfigType, DEFAULT_STATUTORY_CONFIG,
    generate_payroll_cycle_code, generate_payroll_run_code, generate_consultant_invoice_number,
    generate_payroll_document_code
)
from app.api.v1.endpoints.staff_auth import get_current_staff_user

logger = logging.getLogger(__name__)

def get_user_attr(current_user, attr_name: str, default=None):
    """Helper to get attribute from current_user (handles both object and dict)"""
    if hasattr(current_user, '__dict__') and not isinstance(current_user, dict):
        attr_map = {
            'employee_id': 'id',
            'company_id': 'base_company_id',
        }
        mapped_attr = attr_map.get(attr_name, attr_name)
        return getattr(current_user, mapped_attr, default)
    elif isinstance(current_user, dict):
        return current_user.get(attr_name, default)
    return default

PAYROLL_PROFILE_MENU_CODE = "payroll-profile"
PAYROLL_CYCLE_MENU_CODE = "payroll-cycle"
PAYROLL_APPROVALS_MENU_CODE = "payroll-approvals"

def check_menu_access(db: Session, employee_id: int, menu_code: str, require_edit: bool = False) -> bool:
    """Check if employee has access to a menu item"""
    menu = db.query(StaffMenuMaster).filter(
        StaffMenuMaster.menu_code == menu_code,
        StaffMenuMaster.is_active == True
    ).first()
    
    if not menu:
        logger.warning(f"[DC-PAYROLL] Menu code '{menu_code}' not found in StaffMenuMaster")
        return False
    
    settings = db.query(StaffEmployeeMenuSettings).filter(
        StaffEmployeeMenuSettings.employee_id == employee_id,
        StaffEmployeeMenuSettings.menu_id == menu.id
    ).first()
    
    if settings:
        if require_edit:
            return settings.can_edit
        return settings.can_view
    
    if require_edit:
        return menu.is_default_accessible
    return menu.is_default_visible


router = APIRouter()


def get_indian_date():
    ist = pytz.timezone('Asia/Kolkata')
    return datetime.now(ist).date()


def get_indian_datetime():
    ist = pytz.timezone('Asia/Kolkata')
    return datetime.now(ist)


def get_user_accessible_companies(db: Session, employee_id: int, base_company_id: int) -> List[int]:
    """
    DC Protocol: Get list of company IDs the user has access to.
    Returns base company + any companies in data_companies array.
    VGK_SUPREME, Director, HR/Accounts may have multi-company access.
    """
    employee = db.query(StaffEmployee).filter(StaffEmployee.id == employee_id).first()
    if not employee:
        return [base_company_id] if base_company_id else []
    
    accessible = [base_company_id] if base_company_id else []
    if employee.base_company_id and employee.base_company_id not in accessible:
        accessible.append(employee.base_company_id)
    
    if employee.data_companies:
        for cid in employee.data_companies:
            if cid not in accessible:
                accessible.append(cid)
    
    return accessible


def check_company_access(db: Session, current_user: dict, target_company_id: int) -> bool:
    """
    DC Protocol: Verify user has access to the target company.
    Returns True if user can access data for target_company_id.
    """
    user_id = get_user_attr(current_user, 'employee_id')
    user_company_id = get_user_attr(current_user, 'company_id')
    
    if not target_company_id:
        return False
    
    accessible_companies = get_user_accessible_companies(db, user_id, user_company_id)
    return target_company_id in accessible_companies


class PayrollProfileCreate(BaseModel):
    employee_id: int
    company_id: int
    employment_type: str = Field(default='ONROLE', pattern='^(ONROLE|OFFROLE)$')
    pan_number: Optional[str] = None
    uan_number: Optional[str] = None
    esi_ip_number: Optional[str] = None
    pt_state: str = 'KARNATAKA'
    tax_regime: str = Field(default='NEW', pattern='^(OLD|NEW)$')
    ctc_monthly: float = Field(..., gt=0)
    basic_pct: float = Field(default=40.0, ge=0, le=100)
    hra_pct: float = Field(default=20.0, ge=0, le=100)
    special_allowance: Optional[float] = 0
    other_components: Optional[Dict[str, float]] = None
    pf_applicable: bool = True
    esi_applicable: bool = False
    pt_applicable: bool = True
    tds_applicable: bool = True
    bank_account_number: Optional[str] = None
    bank_ifsc_code: Optional[str] = None
    bank_name: Optional[str] = None
    bank_branch: Optional[str] = None
    bank_account_holder: Optional[str] = None
    effective_from: date

    @validator('ctc_monthly')
    def validate_ctc(cls, v):
        if v <= 0:
            raise ValueError('CTC must be greater than 0')
        return v


class PayrollProfileUpdate(BaseModel):
    employment_type: Optional[str] = Field(None, pattern='^(ONROLE|OFFROLE)$')
    pan_number: Optional[str] = None
    uan_number: Optional[str] = None
    esi_ip_number: Optional[str] = None
    pt_state: Optional[str] = None
    tax_regime: Optional[str] = Field(None, pattern='^(OLD|NEW)$')
    ctc_monthly: Optional[float] = Field(None, gt=0)
    basic_pct: Optional[float] = Field(None, ge=0, le=100)
    hra_pct: Optional[float] = Field(None, ge=0, le=100)
    special_allowance: Optional[float] = None
    other_components: Optional[Dict[str, float]] = None
    pf_applicable: Optional[bool] = None
    esi_applicable: Optional[bool] = None
    pt_applicable: Optional[bool] = None
    tds_applicable: Optional[bool] = None
    deductions_enabled: Optional[bool] = None
    bank_account_number: Optional[str] = None
    bank_ifsc_code: Optional[str] = None
    bank_name: Optional[str] = None
    bank_branch: Optional[str] = None
    bank_account_holder: Optional[str] = None
    effective_to: Optional[date] = None


class PayrollProfileResponse(BaseModel):
    id: int
    employee_id: int
    employee_name: str
    employee_code: str
    company_id: int
    company_name: str
    employment_type: str
    pan_number: Optional[str]
    uan_number: Optional[str]
    esi_ip_number: Optional[str]
    pt_state: Optional[str]
    tax_regime: str
    ctc_monthly: float
    ctc_annual: float
    basic_pct: float
    hra_pct: float
    special_allowance: float
    other_components: Optional[Dict[str, float]]
    basic_amount: float
    hra_amount: float
    pf_applicable: bool
    esi_applicable: bool
    pt_applicable: bool
    tds_applicable: bool
    deductions_enabled: bool
    bank_account_number: Optional[str]
    bank_ifsc_code: Optional[str]
    bank_name: Optional[str]
    bank_branch: Optional[str]
    bank_account_holder: Optional[str]
    bank_verified: bool
    effective_from: date
    effective_to: Optional[date]
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class StatutoryConfigResponse(BaseModel):
    id: int
    company_id: int
    company_name: str
    config_type: str
    config_name: str
    rate_employee: Optional[float]
    rate_employer: Optional[float]
    threshold_min: Optional[float]
    threshold_max: Optional[float]
    fixed_amount: Optional[float]
    slab_config: Optional[Dict]
    effective_from: date
    effective_to: Optional[date]
    is_active: bool

    class Config:
        from_attributes = True


@router.get("/staff/payroll/companies", tags=["Staff Payroll"])
async def list_payroll_companies(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_staff_user)
):
    """
    List companies accessible to the current user for payroll dropdowns.
    DC Protocol: Returns only companies the user has access to.
    """
    try:
        user_id = get_user_attr(current_user, 'employee_id')
        user_company_id = get_user_attr(current_user, 'company_id')
        
        accessible_company_ids = get_user_accessible_companies(db, user_id, user_company_id)
        
        companies = db.query(AssociatedCompany).filter(
            AssociatedCompany.id.in_(accessible_company_ids),
            AssociatedCompany.is_active == True
        ).order_by(AssociatedCompany.company_name).all()
        
        return {
            'success': True,
            'companies': [
                {
                    'id': c.id,
                    'name': c.company_name,
                    'company_name': c.company_name
                }
                for c in companies
            ],
            'total': len(companies)
        }
    except Exception as e:
        logger.error(f"[DC-PAYROLL] Error listing companies: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/staff/payroll/employees/list", tags=["Staff Payroll"])
async def list_payroll_employees(
    company_id: Optional[int] = Query(None, description="Filter by company"),
    search: Optional[str] = Query(None, description="Search by name or employee code"),
    limit: int = Query(500, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_staff_user)
):
    """
    List active employees for payroll profile assignment.
    DC Protocol: Returns employees from accessible companies only.
    """
    try:
        user_id = get_user_attr(current_user, 'employee_id')
        user_company_id = get_user_attr(current_user, 'company_id')
        
        accessible_company_ids = get_user_accessible_companies(db, user_id, user_company_id)
        
        query = db.query(StaffEmployee).filter(
            StaffEmployee.status == 'active'
        )
        
        if company_id:
            if company_id not in accessible_company_ids:
                raise HTTPException(status_code=403, detail="Access denied to this company")
            query = query.filter(StaffEmployee.base_company_id == company_id)
        else:
            query = query.filter(StaffEmployee.base_company_id.in_(accessible_company_ids))
        
        if search:
            search_term = f"%{search.lower()}%"
            query = query.filter(
                or_(
                    func.lower(StaffEmployee.full_name).like(search_term),
                    func.lower(StaffEmployee.emp_code).like(search_term)
                )
            )
        
        total_count = query.count()
        employees = query.order_by(StaffEmployee.full_name).limit(limit).all()
        
        return {
            'success': True,
            'data': [
                {
                    'id': emp.id,
                    'employee_code': emp.emp_code,
                    'emp_code': emp.emp_code,
                    'full_name': emp.full_name or f"{emp.first_name or ''} {emp.last_name or ''}".strip(),
                    'designation': emp.designation,
                    'department': emp.department.name if emp.department else None,
                    'company_id': emp.base_company_id
                }
                for emp in employees
            ],
            'total': len(employees),
            'total_available': total_count,
            'has_more': total_count > len(employees)
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[DC-PAYROLL] Error listing employees: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/staff/payroll/profiles", tags=["Staff Payroll"])
async def list_payroll_profiles(
    company_id: Optional[int] = Query(None, description="Filter by company"),
    employee_id: Optional[int] = Query(None, description="Filter by employee"),
    employment_type: Optional[str] = Query(None, description="Filter by ONROLE/OFFROLE"),
    is_active: bool = Query(True, description="Filter active profiles only"),
    search: Optional[str] = Query(None, description="Search by employee name/code"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_staff_user)
):
    """List all payroll profiles with DC Protocol filtering (company-scoped)"""
    try:
        user_id = get_user_attr(current_user, 'employee_id')
        user_company_id = get_user_attr(current_user, 'company_id')
        
        accessible_companies = get_user_accessible_companies(db, user_id, user_company_id)
        
        if company_id:
            if company_id not in accessible_companies:
                logger.warning(f"[DC-PAYROLL] Access denied: User {user_id} tried to list profiles for company {company_id}")
                raise HTTPException(status_code=403, detail="Access denied: You cannot view profiles for this company")
        
        query = db.query(StaffPayrollProfile).filter(
            StaffPayrollProfile.is_active == is_active,
            StaffPayrollProfile.company_id.in_(accessible_companies)
        )
        
        if company_id:
            query = query.filter(StaffPayrollProfile.company_id == company_id)
        
        if employee_id:
            query = query.filter(StaffPayrollProfile.employee_id == employee_id)
        
        if employment_type:
            query = query.filter(StaffPayrollProfile.employment_type == employment_type.upper())
        
        if search:
            query = query.join(StaffEmployee, StaffPayrollProfile.employee_id == StaffEmployee.id)
            search_term = f"%{search}%"
            query = query.filter(
                or_(
                    StaffEmployee.full_name.ilike(search_term),
                    StaffEmployee.emp_code.ilike(search_term)
                )
            )
        
        total = query.count()
        
        profiles = query.order_by(desc(StaffPayrollProfile.created_at)).offset((page - 1) * limit).limit(limit).all()
        
        result = []
        for profile in profiles:
            employee = db.query(StaffEmployee).filter(StaffEmployee.id == profile.employee_id).first()
            company = db.query(AssociatedCompany).filter(AssociatedCompany.id == profile.company_id).first()
            
            ctc = float(profile.ctc_monthly) if profile.ctc_monthly else 0
            basic_pct = float(profile.basic_pct) if profile.basic_pct else 40
            hra_pct = float(profile.hra_pct) if profile.hra_pct else 20
            
            result.append({
                'id': profile.id,
                'employee_id': profile.employee_id,
                'employee_name': employee.full_name if employee else 'Unknown',
                'employee_code': employee.emp_code if employee else 'N/A',
                'company_id': profile.company_id,
                'company_name': company.company_name if company else 'Unknown',
                'employment_type': profile.employment_type,
                'pan_number': profile.pan_number,
                'uan_number': profile.uan_number,
                'esi_ip_number': profile.esi_ip_number,
                'pt_state': profile.pt_state,
                'tax_regime': profile.tax_regime,
                'ctc_monthly': ctc,
                'ctc_annual': ctc * 12,
                'basic_pct': basic_pct,
                'hra_pct': hra_pct,
                'special_allowance': float(profile.special_allowance) if profile.special_allowance else 0,
                'other_components': profile.other_components or {},
                'basic_amount': round(ctc * basic_pct / 100, 2),
                'hra_amount': round(ctc * hra_pct / 100, 2),
                'pf_applicable': profile.pf_applicable,
                'esi_applicable': profile.esi_applicable,
                'pt_applicable': profile.pt_applicable,
                'tds_applicable': profile.tds_applicable,
                'deductions_enabled': profile.deductions_enabled,
                'bank_account_number': profile.bank_account_number,
                'bank_ifsc_code': profile.bank_ifsc_code,
                'bank_name': profile.bank_name,
                'bank_branch': profile.bank_branch,
                'bank_account_holder': profile.bank_account_holder,
                'bank_verified': profile.bank_verified,
                'effective_from': profile.effective_from.isoformat() if profile.effective_from else None,
                'effective_to': profile.effective_to.isoformat() if profile.effective_to else None,
                'is_active': profile.is_active,
                'created_at': profile.created_at.isoformat() if profile.created_at else None,
                'updated_at': profile.updated_at.isoformat() if profile.updated_at else None
            })
        
        return {
            'success': True,
            'data': result,
            'pagination': {
                'page': page,
                'limit': limit,
                'total': total,
                'pages': (total + limit - 1) // limit
            }
        }
    except Exception as e:
        logger.error(f"[DC-PAYROLL] Error listing profiles: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/staff/payroll/profiles/{profile_id}", tags=["Staff Payroll"])
async def get_payroll_profile(
    profile_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_staff_user)
):
    """Get a single payroll profile by ID (DC Protocol enforced)"""
    try:
        profile = db.query(StaffPayrollProfile).filter(StaffPayrollProfile.id == profile_id).first()
        
        if not profile:
            raise HTTPException(status_code=404, detail="Payroll profile not found")
        
        if not check_company_access(db, current_user, profile.company_id):
            logger.warning(f"[DC-PAYROLL] Access denied: User {get_user_attr(current_user, 'employee_id')} tried to access profile {profile_id} in company {profile.company_id}")
            raise HTTPException(status_code=403, detail="Access denied: You do not have permission to view this profile")
        
        employee = db.query(StaffEmployee).filter(StaffEmployee.id == profile.employee_id).first()
        company = db.query(AssociatedCompany).filter(AssociatedCompany.id == profile.company_id).first()
        
        ctc = float(profile.ctc_monthly) if profile.ctc_monthly else 0
        basic_pct = float(profile.basic_pct) if profile.basic_pct else 40
        hra_pct = float(profile.hra_pct) if profile.hra_pct else 20
        
        return {
            'success': True,
            'data': {
                'id': profile.id,
                'employee_id': profile.employee_id,
                'employee_name': employee.full_name if employee else 'Unknown',
                'employee_code': employee.emp_code if employee else 'N/A',
                'department': employee.department.name if employee and employee.department else None,
                'designation': employee.designation if employee else None,
                'company_id': profile.company_id,
                'company_name': company.company_name if company else 'Unknown',
                'company_full_name': company.company_name if company else 'Unknown',
                'employment_type': profile.employment_type,
                'pan_number': profile.pan_number,
                'uan_number': profile.uan_number,
                'esi_ip_number': profile.esi_ip_number,
                'pt_state': profile.pt_state,
                'tax_regime': profile.tax_regime,
                'ctc_monthly': ctc,
                'ctc_annual': ctc * 12,
                'basic_pct': basic_pct,
                'hra_pct': hra_pct,
                'special_allowance': float(profile.special_allowance) if profile.special_allowance else 0,
                'other_components': profile.other_components or {},
                'basic_amount': round(ctc * basic_pct / 100, 2),
                'hra_amount': round(ctc * hra_pct / 100, 2),
                'pf_applicable': profile.pf_applicable,
                'esi_applicable': profile.esi_applicable,
                'pt_applicable': profile.pt_applicable,
                'tds_applicable': profile.tds_applicable,
                'deductions_enabled': profile.deductions_enabled,
                'bank_account_number': profile.bank_account_number,
                'bank_ifsc_code': profile.bank_ifsc_code,
                'bank_name': profile.bank_name,
                'bank_branch': profile.bank_branch,
                'bank_account_holder': profile.bank_account_holder,
                'bank_verified': profile.bank_verified,
                'effective_from': profile.effective_from.isoformat() if profile.effective_from else None,
                'effective_to': profile.effective_to.isoformat() if profile.effective_to else None,
                'is_active': profile.is_active,
                'created_at': profile.created_at.isoformat() if profile.created_at else None,
                'updated_at': profile.updated_at.isoformat() if profile.updated_at else None
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[DC-PAYROLL] Error getting profile: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/staff/payroll/profiles", tags=["Staff Payroll"])
async def create_payroll_profile(
    data: PayrollProfileCreate = Body(...),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_staff_user)
):
    """Create a new payroll profile for an employee (DC Protocol enforced)"""
    try:
        user_id = get_user_attr(current_user, 'employee_id')
        
        if not check_company_access(db, current_user, data.company_id):
            logger.warning(f"[DC-PAYROLL] Access denied: User {user_id} tried to create profile in company {data.company_id}")
            raise HTTPException(status_code=403, detail="Access denied: You do not have permission to create profiles in this company")
        
        employee = db.query(StaffEmployee).filter(StaffEmployee.id == data.employee_id).first()
        if not employee:
            raise HTTPException(status_code=404, detail="Employee not found")
        
        company = db.query(AssociatedCompany).filter(AssociatedCompany.id == data.company_id).first()
        if not company:
            raise HTTPException(status_code=404, detail="Company not found")
        
        existing = db.query(StaffPayrollProfile).filter(
            StaffPayrollProfile.employee_id == data.employee_id,
            StaffPayrollProfile.company_id == data.company_id,
            StaffPayrollProfile.is_active == True,
            StaffPayrollProfile.effective_to == None
        ).first()
        
        if existing:
            raise HTTPException(
                status_code=400,
                detail=f"Active payroll profile already exists for this employee in {company.company_name}"
            )
        
        ctc_monthly = Decimal(str(data.ctc_monthly))
        ctc_annual = ctc_monthly * 12
        
        profile = StaffPayrollProfile(
            employee_id=data.employee_id,
            company_id=data.company_id,
            employment_type=data.employment_type.upper(),
            pan_number=data.pan_number,
            uan_number=data.uan_number,
            esi_ip_number=data.esi_ip_number,
            pt_state=data.pt_state,
            tax_regime=data.tax_regime.upper(),
            ctc_monthly=ctc_monthly,
            ctc_annual=ctc_annual,
            basic_pct=Decimal(str(data.basic_pct)),
            hra_pct=Decimal(str(data.hra_pct)),
            special_allowance=Decimal(str(data.special_allowance or 0)),
            other_components=data.other_components or {},
            pf_applicable=data.pf_applicable,
            esi_applicable=data.esi_applicable,
            pt_applicable=data.pt_applicable,
            tds_applicable=data.tds_applicable,
            bank_account_number=data.bank_account_number,
            bank_ifsc_code=data.bank_ifsc_code,
            bank_name=data.bank_name,
            bank_branch=data.bank_branch,
            bank_account_holder=data.bank_account_holder,
            effective_from=data.effective_from,
            is_active=True,
            created_by_id=user_id,
            updated_by_id=user_id
        )
        
        db.add(profile)
        db.commit()
        db.refresh(profile)
        
        audit = StaffPayrollAuditLog(
            entity_type='PROFILE',
            entity_id=profile.id,
            company_id=data.company_id,
            action='CREATE',
            performed_by=user_id,
            new_values={
                'employee_id': data.employee_id,
                'ctc_monthly': float(ctc_monthly),
                'employment_type': data.employment_type
            }
        )
        db.add(audit)
        db.commit()
        
        logger.info(f"[DC-PAYROLL] Created profile {profile.id} for employee {data.employee_id}")
        
        return {
            'success': True,
            'message': f'Payroll profile created for {employee.full_name}',
            'data': {
                'id': profile.id,
                'employee_id': profile.employee_id,
                'employee_name': employee.full_name,
                'company_id': profile.company_id,
                'company_name': company.company_name,
                'ctc_monthly': float(profile.ctc_monthly),
                'ctc_annual': float(profile.ctc_annual),
                'employment_type': profile.employment_type
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"[DC-PAYROLL] Error creating profile: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/staff/payroll/profiles/{profile_id}", tags=["Staff Payroll"])
async def update_payroll_profile(
    profile_id: int,
    data: PayrollProfileUpdate = Body(...),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_staff_user)
):
    """Update an existing payroll profile (DC Protocol enforced)"""
    try:
        user_id = get_user_attr(current_user, 'employee_id')
        
        profile = db.query(StaffPayrollProfile).filter(StaffPayrollProfile.id == profile_id).first()
        if not profile:
            raise HTTPException(status_code=404, detail="Payroll profile not found")
        
        if not check_company_access(db, current_user, profile.company_id):
            logger.warning(f"[DC-PAYROLL] Access denied: User {user_id} tried to update profile {profile_id} in company {profile.company_id}")
            raise HTTPException(status_code=403, detail="Access denied: You do not have permission to update this profile")
        
        old_values = profile.to_dict()
        
        if data.employment_type is not None:
            profile.employment_type = data.employment_type.upper()
        if data.pan_number is not None:
            profile.pan_number = data.pan_number
        if data.uan_number is not None:
            profile.uan_number = data.uan_number
        if data.esi_ip_number is not None:
            profile.esi_ip_number = data.esi_ip_number
        if data.pt_state is not None:
            profile.pt_state = data.pt_state
        if data.tax_regime is not None:
            profile.tax_regime = data.tax_regime.upper()
        if data.ctc_monthly is not None:
            profile.ctc_monthly = Decimal(str(data.ctc_monthly))
            profile.ctc_annual = profile.ctc_monthly * 12
        if data.basic_pct is not None:
            profile.basic_pct = Decimal(str(data.basic_pct))
        if data.hra_pct is not None:
            profile.hra_pct = Decimal(str(data.hra_pct))
        if data.special_allowance is not None:
            profile.special_allowance = Decimal(str(data.special_allowance))
        if data.other_components is not None:
            profile.other_components = data.other_components
        if data.pf_applicable is not None:
            profile.pf_applicable = data.pf_applicable
        if data.esi_applicable is not None:
            profile.esi_applicable = data.esi_applicable
        if data.pt_applicable is not None:
            profile.pt_applicable = data.pt_applicable
        if data.tds_applicable is not None:
            profile.tds_applicable = data.tds_applicable
        if data.deductions_enabled is not None:
            profile.deductions_enabled = data.deductions_enabled
        if data.bank_account_number is not None:
            profile.bank_account_number = data.bank_account_number
        if data.bank_ifsc_code is not None:
            profile.bank_ifsc_code = data.bank_ifsc_code
        if data.bank_name is not None:
            profile.bank_name = data.bank_name
        if data.bank_branch is not None:
            profile.bank_branch = data.bank_branch
        if data.bank_account_holder is not None:
            profile.bank_account_holder = data.bank_account_holder
        if data.effective_to is not None:
            profile.effective_to = data.effective_to
        
        profile.updated_by_id = user_id
        profile.updated_at = get_indian_datetime()
        
        db.commit()
        
        new_vals = profile.to_dict()
        audit = StaffPayrollAuditLog(
            entity_type='PROFILE',
            entity_id=profile.id,
            company_id=profile.company_id,
            action='UPDATE',
            performed_by=user_id,
            old_values=old_values,
            new_values=new_vals
        )
        db.add(audit)
        db.commit()
        
        employee = db.query(StaffEmployee).filter(StaffEmployee.id == profile.employee_id).first()
        
        logger.info(f"[DC-PAYROLL] Updated profile {profile_id}")
        
        return {
            'success': True,
            'message': f'Payroll profile updated for {employee.full_name if employee else "employee"}',
            'data': {
                'id': profile.id,
                'ctc_monthly': float(profile.ctc_monthly),
                'ctc_annual': float(profile.ctc_annual)
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"[DC-PAYROLL] Error updating profile: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/staff/payroll/profiles/{profile_id}", tags=["Staff Payroll"])
async def deactivate_payroll_profile(
    profile_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_staff_user)
):
    """Deactivate a payroll profile (soft delete, DC Protocol enforced)"""
    try:
        user_id = get_user_attr(current_user, 'employee_id')
        
        profile = db.query(StaffPayrollProfile).filter(StaffPayrollProfile.id == profile_id).first()
        if not profile:
            raise HTTPException(status_code=404, detail="Payroll profile not found")
        
        if not check_company_access(db, current_user, profile.company_id):
            logger.warning(f"[DC-PAYROLL] Access denied: User {user_id} tried to delete profile {profile_id} in company {profile.company_id}")
            raise HTTPException(status_code=403, detail="Access denied: You do not have permission to deactivate this profile")
        
        if not profile.is_active:
            raise HTTPException(status_code=400, detail="Profile is already deactivated")
        
        profile.is_active = False
        profile.effective_to = get_indian_date()
        profile.updated_by_id = user_id
        profile.updated_at = get_indian_datetime()
        
        db.commit()
        
        audit = StaffPayrollAuditLog(
            entity_type='PROFILE',
            entity_id=profile.id,
            company_id=profile.company_id,
            action='DEACTIVATE',
            performed_by=user_id
        )
        db.add(audit)
        db.commit()
        
        logger.info(f"[DC-PAYROLL] Deactivated profile {profile_id}")
        
        return {
            'success': True,
            'message': 'Payroll profile deactivated'
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"[DC-PAYROLL] Error deactivating profile: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/staff/payroll/statutory-config", tags=["Staff Payroll"])
async def list_statutory_configs(
    company_id: Optional[int] = Query(None, description="Filter by company"),
    config_type: Optional[str] = Query(None, description="Filter by PF/ESI/PT/TDS"),
    is_active: bool = Query(True),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_staff_user)
):
    """List all statutory configuration for payroll deductions (DC Protocol enforced)"""
    try:
        user_id = get_user_attr(current_user, 'employee_id')
        user_company_id = get_user_attr(current_user, 'company_id')
        
        accessible_companies = get_user_accessible_companies(db, user_id, user_company_id)
        
        query = db.query(StaffPayrollStatutoryConfig).filter(
            StaffPayrollStatutoryConfig.is_active == is_active,
            StaffPayrollStatutoryConfig.company_id.in_(accessible_companies)
        )
        
        if company_id:
            if company_id not in accessible_companies:
                raise HTTPException(status_code=403, detail="Access denied: You cannot view statutory config for this company")
            query = query.filter(StaffPayrollStatutoryConfig.company_id == company_id)
        
        if config_type:
            query = query.filter(StaffPayrollStatutoryConfig.config_type == config_type.upper())
        
        configs = query.order_by(StaffPayrollStatutoryConfig.config_type, StaffPayrollStatutoryConfig.company_id).all()
        
        result = []
        for config in configs:
            company = db.query(AssociatedCompany).filter(AssociatedCompany.id == config.company_id).first()
            result.append({
                'id': config.id,
                'company_id': config.company_id,
                'company_name': company.company_name if company else 'Unknown',
                'config_type': config.config_type,
                'config_name': config.config_name,
                'rate_employee': float(config.rate_employee) if config.rate_employee else None,
                'rate_employer': float(config.rate_employer) if config.rate_employer else None,
                'threshold_min': float(config.threshold_min) if config.threshold_min else None,
                'threshold_max': float(config.threshold_max) if config.threshold_max else None,
                'fixed_amount': float(config.fixed_amount) if config.fixed_amount else None,
                'slab_config': config.slab_config,
                'effective_from': config.effective_from.isoformat() if config.effective_from else None,
                'effective_to': config.effective_to.isoformat() if config.effective_to else None,
                'is_active': config.is_active
            })
        
        return {
            'success': True,
            'data': result,
            'count': len(result)
        }
    except Exception as e:
        logger.error(f"[DC-PAYROLL] Error listing statutory config: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/staff/payroll/statutory-config/initialize", tags=["Staff Payroll"])
async def initialize_statutory_config(
    company_id: int = Query(..., description="Company ID to initialize config for"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_staff_user)
):
    """Initialize default statutory configuration for a company (DC Protocol enforced)"""
    try:
        user_id = get_user_attr(current_user, 'employee_id')
        
        if not check_company_access(db, current_user, company_id):
            logger.warning(f"[DC-PAYROLL] Access denied: User {user_id} tried to initialize statutory config for company {company_id}")
            raise HTTPException(status_code=403, detail="Access denied: You do not have permission to initialize config for this company")
        
        company = db.query(AssociatedCompany).filter(AssociatedCompany.id == company_id).first()
        if not company:
            raise HTTPException(status_code=404, detail="Company not found")
        
        existing = db.query(StaffPayrollStatutoryConfig).filter(
            StaffPayrollStatutoryConfig.company_id == company_id,
            StaffPayrollStatutoryConfig.is_active == True
        ).first()
        
        if existing:
            raise HTTPException(
                status_code=400,
                detail=f"Statutory configuration already exists for {company.company_name}"
            )
        
        today = get_indian_date()
        created_configs = []
        
        for config_data in DEFAULT_STATUTORY_CONFIG:
            config = StaffPayrollStatutoryConfig(
                company_id=company_id,
                config_type=config_data['config_type'],
                config_name=config_data['config_name'],
                rate_employee=Decimal(str(config_data.get('rate_employee', 0))) if config_data.get('rate_employee') else None,
                rate_employer=Decimal(str(config_data.get('rate_employer', 0))) if config_data.get('rate_employer') else None,
                threshold_min=Decimal(str(config_data.get('threshold_min', 0))) if config_data.get('threshold_min') else None,
                threshold_max=Decimal(str(config_data.get('threshold_max', 0))) if config_data.get('threshold_max') else None,
                fixed_amount=Decimal(str(config_data.get('fixed_amount', 0))) if config_data.get('fixed_amount') else None,
                slab_config=config_data.get('slab_config'),
                effective_from=today,
                is_active=True,
                created_by_id=user_id,
                updated_by_id=user_id
            )
            db.add(config)
            created_configs.append(config_data['config_type'])
        
        db.commit()
        
        audit = StaffPayrollAuditLog(
            entity_type='STATUTORY_CONFIG',
            entity_id=company_id,
            company_id=company_id,
            action='INITIALIZE',
            performed_by=user_id,
            new_values={'configs': created_configs}
        )
        db.add(audit)
        db.commit()
        
        logger.info(f"[DC-PAYROLL] Initialized statutory config for company {company_id}")
        
        return {
            'success': True,
            'message': f'Initialized {len(created_configs)} statutory configurations for {company.company_name}',
            'data': {
                'company_id': company_id,
                'company_name': company.company_name,
                'configs_created': created_configs
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"[DC-PAYROLL] Error initializing statutory config: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/staff/payroll/employees-without-profile", tags=["Staff Payroll"])
async def list_employees_without_profile(
    company_id: Optional[int] = Query(None, description="Filter by company"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_staff_user)
):
    """List employees who don't have a payroll profile yet (DC Protocol enforced)"""
    try:
        user_id = get_user_attr(current_user, 'employee_id')
        user_company_id = get_user_attr(current_user, 'company_id')
        
        accessible_companies = get_user_accessible_companies(db, user_id, user_company_id)
        
        target_company = company_id or user_company_id
        
        if target_company and target_company not in accessible_companies:
            logger.warning(f"[DC-PAYROLL] Access denied: User {user_id} tried to list employees for company {target_company}")
            raise HTTPException(status_code=403, detail="Access denied: You cannot view employees for this company")
        
        employees_with_profile = db.query(StaffPayrollProfile.employee_id).filter(
            StaffPayrollProfile.is_active == True
        )
        if target_company:
            employees_with_profile = employees_with_profile.filter(
                StaffPayrollProfile.company_id == target_company
            )
        employees_with_profile = employees_with_profile.subquery()
        
        query = db.query(StaffEmployee).filter(
            StaffEmployee.status == 'active',
            StaffEmployee.base_company_id.in_(accessible_companies),
            ~StaffEmployee.id.in_(db.query(employees_with_profile.c.employee_id))
        )
        
        if target_company:
            query = query.filter(StaffEmployee.base_company_id == target_company)
        
        employees = query.order_by(StaffEmployee.full_name).all()
        
        result = []
        for emp in employees:
            result.append({
                'id': emp.id,
                'employee_id': emp.employee_id,
                'full_name': emp.full_name,
                'email': emp.email,
                'designation': emp.designation,
                'department': emp.department.name if emp.department else None,
                'company_id': emp.base_company_id
            })
        
        return {
            'success': True,
            'data': result,
            'count': len(result)
        }
    except Exception as e:
        logger.error(f"[DC-PAYROLL] Error listing employees without profile: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/staff/payroll/salary-breakdown/{profile_id}", tags=["Staff Payroll"])
async def get_salary_breakdown(
    profile_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_staff_user)
):
    """Get detailed salary breakdown for a payroll profile (DC Protocol enforced)"""
    try:
        profile = db.query(StaffPayrollProfile).filter(StaffPayrollProfile.id == profile_id).first()
        if not profile:
            raise HTTPException(status_code=404, detail="Payroll profile not found")
        
        if not check_company_access(db, current_user, profile.company_id):
            logger.warning(f"[DC-PAYROLL] Access denied: User {get_user_attr(current_user, 'employee_id')} tried to view salary breakdown for profile {profile_id} in company {profile.company_id}")
            raise HTTPException(status_code=403, detail="Access denied: You do not have permission to view this salary breakdown")
        
        ctc = float(profile.ctc_monthly) if profile.ctc_monthly else 0
        basic_pct = float(profile.basic_pct) if profile.basic_pct else 40
        hra_pct = float(profile.hra_pct) if profile.hra_pct else 20
        special_allowance = float(profile.special_allowance) if profile.special_allowance else 0
        
        basic = round(ctc * basic_pct / 100, 2)
        hra = round(ctc * hra_pct / 100, 2)
        
        remaining = ctc - basic - hra - special_allowance
        other_components = profile.other_components or {}
        other_total = sum(other_components.values()) if other_components else 0
        
        if other_total == 0 and remaining > 0:
            other_components = {'Flexible Benefits': remaining}
            other_total = remaining
        
        gross = basic + hra + special_allowance + other_total
        
        pf_employee = 0
        pf_employer = 0
        esi_employee = 0
        esi_employer = 0
        pt = 0
        
        if profile.pf_applicable:
            pf_basic = min(basic, 15000)
            pf_employee = round(pf_basic * 0.12, 2)
            pf_employer = round(pf_basic * 0.12, 2)
        
        if profile.esi_applicable and gross <= 21000:
            esi_employee = round(gross * 0.0075, 2)
            esi_employer = round(gross * 0.0325, 2)
        
        if profile.pt_applicable:
            if profile.pt_state == 'KARNATAKA' and gross >= 15000:
                pt = 200
        
        total_employee_deductions = pf_employee + esi_employee + pt
        net_salary = round(gross - total_employee_deductions, 2)
        ctc_with_employer = round(gross + pf_employer + esi_employer, 2)
        
        employee = db.query(StaffEmployee).filter(StaffEmployee.id == profile.employee_id).first()
        
        return {
            'success': True,
            'data': {
                'profile_id': profile.id,
                'employee_name': employee.full_name if employee else 'Unknown',
                'employment_type': profile.employment_type,
                'earnings': {
                    'basic': basic,
                    'basic_pct': basic_pct,
                    'hra': hra,
                    'hra_pct': hra_pct,
                    'special_allowance': special_allowance,
                    'other_components': other_components,
                    'gross_salary': round(gross, 2)
                },
                'deductions': {
                    'pf_employee': pf_employee,
                    'pf_employer': pf_employer,
                    'esi_employee': esi_employee,
                    'esi_employer': esi_employer,
                    'professional_tax': pt,
                    'tds': 0,
                    'total_employee': round(total_employee_deductions, 2),
                    'total_employer': round(pf_employer + esi_employer, 2)
                },
                'summary': {
                    'ctc_monthly': ctc,
                    'ctc_annual': round(ctc * 12, 2),
                    'gross_salary': round(gross, 2),
                    'net_salary': net_salary,
                    'ctc_with_employer_contributions': ctc_with_employer,
                    'take_home_annual': round(net_salary * 12, 2)
                },
                'statutory_flags': {
                    'pf_applicable': profile.pf_applicable,
                    'esi_applicable': profile.esi_applicable,
                    'pt_applicable': profile.pt_applicable,
                    'tds_applicable': profile.tds_applicable
                }
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[DC-PAYROLL] Error getting salary breakdown: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# PHASE 3: PAYROLL CYCLE MANAGEMENT ENDPOINTS
# ============================================================================

class PayrollCycleCreate(BaseModel):
    company_id: int
    cycle_month: int = Field(..., ge=1, le=12, description="Month (1-12)")
    cycle_year: int = Field(..., ge=2020, le=2100, description="Year")
    period_start: date
    period_end: date
    notes: Optional[str] = None

class PayrollCycleUpdate(BaseModel):
    period_start: Optional[date] = None
    period_end: Optional[date] = None
    notes: Optional[str] = None


@router.get("/staff/payroll/cycles", tags=["Staff Payroll Cycles"])
async def list_payroll_cycles(
    company_id: Optional[int] = Query(None, description="Filter by company"),
    cycle_year: Optional[int] = Query(None, description="Filter by year"),
    status: Optional[str] = Query(None, description="Filter by status (DRAFT/LOCKED/PROCESSING/COMPLETED/CANCELLED)"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_staff_user)
):
    """List payroll cycles with DC Protocol filtering (company-scoped)"""
    try:
        user_id = get_user_attr(current_user, 'employee_id')
        user_company_id = get_user_attr(current_user, 'company_id')
        
        if not check_menu_access(db, user_id, PAYROLL_CYCLE_MENU_CODE, require_edit=False):
            raise HTTPException(status_code=403, detail="Access denied: You do not have permission to view payroll cycles")
        
        accessible_companies = get_user_accessible_companies(db, user_id, user_company_id)
        
        if company_id:
            if company_id not in accessible_companies:
                logger.warning(f"[DC-PAYROLL] Access denied: User {user_id} tried to list cycles for company {company_id}")
                raise HTTPException(status_code=403, detail="Access denied: You cannot view cycles for this company")
        
        query = db.query(StaffPayrollCycle).filter(
            StaffPayrollCycle.company_id.in_(accessible_companies)
        )
        
        if company_id:
            query = query.filter(StaffPayrollCycle.company_id == company_id)
        
        if cycle_year:
            query = query.filter(StaffPayrollCycle.cycle_year == cycle_year)
        
        if status:
            query = query.filter(StaffPayrollCycle.status == status.upper())
        
        total = query.count()
        
        cycles = query.order_by(
            desc(StaffPayrollCycle.cycle_year),
            desc(StaffPayrollCycle.cycle_month)
        ).offset((page - 1) * limit).limit(limit).all()
        
        result = []
        for cycle in cycles:
            company = db.query(AssociatedCompany).filter(AssociatedCompany.id == cycle.company_id).first()
            
            runs = db.query(StaffPayrollRun).filter(
                StaffPayrollRun.cycle_id == cycle.id
            ).all()
            runs_count = len(runs)
            total_net_salary = sum(float(r.net_salary or 0) for r in runs)
            
            result.append({
                'id': cycle.id,
                'cycle_code': cycle.cycle_code or f"CYC-{cycle.id}",
                'company_id': cycle.company_id,
                'company_name': company.company_name if company else 'Unknown',
                'cycle_month': cycle.cycle_month,
                'cycle_year': cycle.cycle_year,
                'cycle_name': f"{calendar.month_name[cycle.cycle_month]} {cycle.cycle_year}",
                'period_start': cycle.period_start.isoformat() if cycle.period_start else None,
                'period_end': cycle.period_end.isoformat() if cycle.period_end else None,
                'payment_date': cycle.paid_at.date().isoformat() if cycle.paid_at else None,
                'status': cycle.status,
                'runs_count': runs_count,
                'total_net_salary': total_net_salary,
                'locked_at': cycle.attendance_locked_at.isoformat() if cycle.attendance_locked_at else None,
                'locked_by': cycle.attendance_locked_by,
                'created_at': cycle.created_at.isoformat() if cycle.created_at else None
            })
        
        return {
            'success': True,
            'data': result,
            'pagination': {
                'total': total,
                'page': page,
                'limit': limit,
                'pages': (total + limit - 1) // limit
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[DC-PAYROLL] Error listing cycles: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/staff/payroll/cycles/{cycle_id}", tags=["Staff Payroll Cycles"])
async def get_payroll_cycle(
    cycle_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_staff_user)
):
    """Get payroll cycle details (DC Protocol enforced)"""
    try:
        user_id = get_user_attr(current_user, 'employee_id')
        
        if not check_menu_access(db, user_id, PAYROLL_CYCLE_MENU_CODE, require_edit=False):
            raise HTTPException(status_code=403, detail="Access denied: You do not have permission to view payroll cycles")
        
        cycle = db.query(StaffPayrollCycle).filter(StaffPayrollCycle.id == cycle_id).first()
        if not cycle:
            raise HTTPException(status_code=404, detail="Payroll cycle not found")
        
        if not check_company_access(db, current_user, cycle.company_id):
            logger.warning(f"[DC-PAYROLL] Access denied: User {get_user_attr(current_user, 'employee_id')} tried to view cycle {cycle_id}")
            raise HTTPException(status_code=403, detail="Access denied: You do not have permission to view this cycle")
        
        company = db.query(AssociatedCompany).filter(AssociatedCompany.id == cycle.company_id).first()
        
        runs = db.query(StaffPayrollRun).filter(StaffPayrollRun.cycle_id == cycle.id).all()
        
        runs_summary = {
            'total': len(runs),
            'pending': sum(1 for r in runs if r.status == 'PENDING'),
            'approved': sum(1 for r in runs if r.status == 'APPROVED'),
            'paid': sum(1 for r in runs if r.status == 'PAID'),
            'rejected': sum(1 for r in runs if r.status == 'REJECTED')
        }
        
        total_gross = sum(float(r.gross_salary or 0) for r in runs)
        total_net = sum(float(r.net_salary or 0) for r in runs)
        total_deductions = sum(float(r.total_deductions or 0) for r in runs)
        
        return {
            'success': True,
            'data': {
                'id': cycle.id,
                'cycle_code': cycle.cycle_code,
                'company_id': cycle.company_id,
                'company_name': company.company_name if company else 'Unknown',
                'cycle_month': cycle.cycle_month,
                'cycle_year': cycle.cycle_year,
                'cycle_name': f"{calendar.month_name[cycle.cycle_month]} {cycle.cycle_year}",
                'period_start': cycle.period_start.isoformat() if cycle.period_start else None,
                'period_end': cycle.period_end.isoformat() if cycle.period_end else None,
                'payment_date': cycle.paid_at.date().isoformat() if cycle.paid_at else None,
                'status': cycle.status,
                'locked_at': cycle.attendance_locked_at.isoformat() if cycle.attendance_locked_at else None,
                'locked_by': cycle.attendance_locked_by,
                'notes': cycle.notes,
                'runs_summary': runs_summary,
                'financials': {
                    'total_gross': round(total_gross, 2),
                    'total_deductions': round(total_deductions, 2),
                    'total_net': round(total_net, 2)
                },
                'created_at': cycle.created_at.isoformat() if cycle.created_at else None,
                'updated_at': cycle.updated_at.isoformat() if cycle.updated_at else None
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[DC-PAYROLL] Error getting cycle: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/staff/payroll/cycles", tags=["Staff Payroll Cycles"])
async def create_payroll_cycle(
    cycle_data: PayrollCycleCreate = Body(...),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_staff_user)
):
    """Create a new payroll cycle (DC Protocol enforced)"""
    try:
        user_id = get_user_attr(current_user, 'employee_id')
        
        if not check_menu_access(db, user_id, PAYROLL_CYCLE_MENU_CODE, require_edit=True):
            raise HTTPException(status_code=403, detail="Access denied: You do not have permission to create payroll cycles")
        
        if not check_company_access(db, current_user, cycle_data.company_id):
            logger.warning(f"[DC-PAYROLL] Access denied: User {get_user_attr(current_user, 'employee_id')} tried to create cycle for company {cycle_data.company_id}")
            raise HTTPException(status_code=403, detail="Access denied: You cannot create cycles for this company")
        
        existing = db.query(StaffPayrollCycle).filter(
            StaffPayrollCycle.company_id == cycle_data.company_id,
            StaffPayrollCycle.cycle_month == cycle_data.cycle_month,
            StaffPayrollCycle.cycle_year == cycle_data.cycle_year,
            StaffPayrollCycle.status != 'CANCELLED'
        ).first()
        
        if existing:
            raise HTTPException(
                status_code=400,
                detail=f"Payroll cycle for {calendar.month_name[cycle_data.cycle_month]} {cycle_data.cycle_year} already exists"
            )
        
        if cycle_data.period_end < cycle_data.period_start:
            raise HTTPException(status_code=400, detail="Period end date cannot be before period start date")
        
        cycle_code = generate_payroll_cycle_code(cycle_data.company_id, cycle_data.cycle_month, cycle_data.cycle_year)
        
        cycle = StaffPayrollCycle(
            cycle_code=cycle_code,
            company_id=cycle_data.company_id,
            cycle_month=cycle_data.cycle_month,
            cycle_year=cycle_data.cycle_year,
            period_start=cycle_data.period_start,
            period_end=cycle_data.period_end,
            status='DRAFT',
            notes=cycle_data.notes,
            created_by_id=get_user_attr(current_user, 'employee_id')
        )
        
        db.add(cycle)
        db.commit()
        db.refresh(cycle)
        
        logger.info(f"[DC-PAYROLL] Cycle created: {cycle.id} for company {cycle.company_id} by user {get_user_attr(current_user, 'employee_id')}")
        
        return {
            'success': True,
            'message': f"Payroll cycle for {calendar.month_name[cycle.cycle_month]} {cycle.cycle_year} created successfully",
            'data': {
                'id': cycle.id,
                'company_id': cycle.company_id,
                'cycle_month': cycle.cycle_month,
                'cycle_year': cycle.cycle_year,
                'status': cycle.status
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"[DC-PAYROLL] Error creating cycle: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/staff/payroll/cycles/{cycle_id}", tags=["Staff Payroll Cycles"])
async def update_payroll_cycle(
    cycle_id: int,
    cycle_data: PayrollCycleUpdate = Body(...),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_staff_user)
):
    """Update a payroll cycle (DC Protocol enforced, DRAFT only)"""
    try:
        user_id = get_user_attr(current_user, 'employee_id')
        
        if not check_menu_access(db, user_id, PAYROLL_CYCLE_MENU_CODE, require_edit=True):
            raise HTTPException(status_code=403, detail="Access denied: You do not have permission to update payroll cycles")
        
        cycle = db.query(StaffPayrollCycle).filter(StaffPayrollCycle.id == cycle_id).first()
        if not cycle:
            raise HTTPException(status_code=404, detail="Payroll cycle not found")
        
        if not check_company_access(db, current_user, cycle.company_id):
            logger.warning(f"[DC-PAYROLL] Access denied: User {get_user_attr(current_user, 'employee_id')} tried to update cycle {cycle_id}")
            raise HTTPException(status_code=403, detail="Access denied: You do not have permission to update this cycle")
        
        if cycle.status != 'DRAFT':
            raise HTTPException(status_code=400, detail=f"Cannot update cycle in {cycle.status} status. Only DRAFT cycles can be modified.")
        
        if cycle_data.period_start:
            cycle.period_start = cycle_data.period_start
        if cycle_data.period_end:
            cycle.period_end = cycle_data.period_end
        if cycle_data.notes is not None:
            cycle.notes = cycle_data.notes
        
        if cycle.period_end and cycle.period_start and cycle.period_end < cycle.period_start:
            raise HTTPException(status_code=400, detail="Period end date cannot be before period start date")
        
        cycle.updated_at = datetime.utcnow()
        db.commit()
        
        return {
            'success': True,
            'message': "Payroll cycle updated successfully",
            'data': {
                'id': cycle.id,
                'period_start': cycle.period_start.isoformat() if cycle.period_start else None,
                'period_end': cycle.period_end.isoformat() if cycle.period_end else None,
                'status': cycle.status
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"[DC-PAYROLL] Error updating cycle: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/staff/payroll/cycles/{cycle_id}/process", tags=["Staff Payroll Cycles"])
async def process_payroll_cycle(
    cycle_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_staff_user)
):
    """Process a payroll cycle - generates payroll runs for all eligible employees (DC Protocol enforced)"""
    try:
        user_id = get_user_attr(current_user, 'employee_id')
        
        if not check_menu_access(db, user_id, PAYROLL_CYCLE_MENU_CODE, require_edit=True):
            raise HTTPException(status_code=403, detail="Access denied: You do not have permission to process payroll cycles")
        
        cycle = db.query(StaffPayrollCycle).filter(StaffPayrollCycle.id == cycle_id).first()
        if not cycle:
            raise HTTPException(status_code=404, detail="Payroll cycle not found")
        
        if not check_company_access(db, current_user, cycle.company_id):
            logger.warning(f"[DC-PAYROLL] Access denied: User {user_id} tried to process cycle {cycle_id}")
            raise HTTPException(status_code=403, detail="Access denied: You do not have permission to process this cycle")
        
        if cycle.status != 'DRAFT':
            raise HTTPException(status_code=400, detail=f"Cannot process cycle in {cycle.status} status. Only DRAFT cycles can be processed.")
        
        profiles = db.query(StaffPayrollProfile).filter(
            StaffPayrollProfile.company_id == cycle.company_id,
            StaffPayrollProfile.is_active == True
        ).all()
        
        if not profiles:
            raise HTTPException(status_code=400, detail="No active salary profiles found for this company")
        
        runs_created = 0
        for profile in profiles:
            existing_run = db.query(StaffPayrollRun).filter(
                StaffPayrollRun.cycle_id == cycle.id,
                StaffPayrollRun.employee_id == profile.employee_id
            ).first()
            
            if existing_run:
                continue
            
            run_code = generate_payroll_run_code(cycle.id, profile.employee_id)
            
            ctc_monthly = float(profile.ctc_monthly or 0)
            basic_pct = float(profile.basic_pct or 40) / 100
            hra_pct = float(profile.hra_pct or 20) / 100
            
            basic_salary = round(ctc_monthly * basic_pct, 2)
            hra = round(ctc_monthly * hra_pct, 2)
            special_allowance = float(profile.special_allowance or 0)
            gross_salary = basic_salary + hra + special_allowance
            
            pf_deduction = round(basic_salary * 0.12, 2) if profile.pf_applicable else 0
            esi_deduction = round(gross_salary * 0.0075, 2) if profile.esi_applicable and gross_salary <= 21000 else 0
            pt_deduction = 200 if profile.pt_applicable else 0
            tds_deduction = 0
            
            total_deductions = pf_deduction + esi_deduction + pt_deduction + tds_deduction
            net_salary = gross_salary - total_deductions
            
            run = StaffPayrollRun(
                run_code=run_code,
                cycle_id=cycle.id,
                employee_id=profile.employee_id,
                company_id=cycle.company_id,
                profile_id=profile.id,
                ctc_monthly=ctc_monthly,
                basic_amount=basic_salary,
                hra_amount=hra,
                special_allowance=special_allowance,
                gross_salary=gross_salary,
                total_earnings=gross_salary,
                pf_employee=pf_deduction,
                esi_employee=esi_deduction,
                pt_amount=pt_deduction,
                tds_amount=tds_deduction,
                total_deductions=total_deductions,
                net_salary=net_salary,
                status='PENDING',
                created_by_id=user_id
            )
            
            db.add(run)
            runs_created += 1
        
        db.flush()
        
        all_runs = db.query(StaffPayrollRun).filter(StaffPayrollRun.cycle_id == cycle.id).all()
        total_employees = len(all_runs)
        total_gross = sum(float(r.gross_salary or 0) for r in all_runs)
        total_deductions = sum(float(r.total_deductions or 0) for r in all_runs)
        total_net = sum(float(r.net_salary or 0) for r in all_runs)
        
        cycle.total_employees = total_employees
        cycle.total_gross_salary = total_gross
        cycle.total_deductions = total_deductions
        cycle.total_net_salary = total_net
        cycle.generated_at = datetime.utcnow()
        cycle.generated_by = user_id
        cycle.status = 'GENERATED'
        cycle.updated_at = datetime.utcnow()
        
        db.commit()
        
        logger.info(f"[DC-PAYROLL] Cycle {cycle_id} processed: {runs_created} new runs, {total_employees} total employees by user {user_id}")
        
        return {
            'success': True,
            'message': f"Payroll cycle processed successfully. {runs_created} new runs generated, {total_employees} total employees.",
            'data': {
                'id': cycle.id,
                'status': cycle.status,
                'runs_created': runs_created,
                'total_employees': total_employees,
                'total_gross_salary': total_gross,
                'total_deductions': total_deductions,
                'total_net_salary': total_net,
                'generated_at': cycle.generated_at.isoformat()
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"[DC-PAYROLL] Error processing cycle: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/staff/payroll/cycles/{cycle_id}/lock", tags=["Staff Payroll Cycles"])
async def lock_payroll_cycle(
    cycle_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_staff_user)
):
    """Lock a payroll cycle for processing (DC Protocol enforced)"""
    try:
        user_id = get_user_attr(current_user, 'employee_id')
        
        if not check_menu_access(db, user_id, PAYROLL_CYCLE_MENU_CODE, require_edit=True):
            raise HTTPException(status_code=403, detail="Access denied: You do not have permission to lock payroll cycles")
        
        cycle = db.query(StaffPayrollCycle).filter(StaffPayrollCycle.id == cycle_id).first()
        if not cycle:
            raise HTTPException(status_code=404, detail="Payroll cycle not found")
        
        if not check_company_access(db, current_user, cycle.company_id):
            logger.warning(f"[DC-PAYROLL] Access denied: User {get_user_attr(current_user, 'employee_id')} tried to lock cycle {cycle_id}")
            raise HTTPException(status_code=403, detail="Access denied: You do not have permission to lock this cycle")
        
        if cycle.status != 'DRAFT':
            raise HTTPException(status_code=400, detail=f"Cannot lock cycle in {cycle.status} status. Only DRAFT cycles can be locked.")
        
        runs_count = db.query(StaffPayrollRun).filter(StaffPayrollRun.cycle_id == cycle.id).count()
        if runs_count == 0:
            raise HTTPException(status_code=400, detail="Cannot lock cycle without any payroll runs. Generate runs first.")
        
        cycle.status = 'LOCKED'
        cycle.attendance_locked_at = datetime.utcnow()
        cycle.attendance_locked_by = get_user_attr(current_user, 'employee_id')
        cycle.updated_at = datetime.utcnow()
        
        db.commit()
        
        logger.info(f"[DC-PAYROLL] Cycle {cycle_id} locked by user {get_user_attr(current_user, 'employee_id')}")
        
        return {
            'success': True,
            'message': f"Payroll cycle for {calendar.month_name[cycle.cycle_month]} {cycle.cycle_year} locked successfully",
            'data': {
                'id': cycle.id,
                'status': cycle.status,
                'locked_at': cycle.attendance_locked_at.isoformat(),
                'locked_by': cycle.attendance_locked_by,
                'runs_count': runs_count
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"[DC-PAYROLL] Error locking cycle: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/staff/payroll/cycles/{cycle_id}/generate-runs", tags=["Staff Payroll Cycles"])
async def generate_payroll_runs(
    cycle_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_staff_user)
):
    """Generate payroll runs for all active employees with profiles (DC Protocol enforced)"""
    try:
        user_id = get_user_attr(current_user, 'employee_id')
        
        if not check_menu_access(db, user_id, PAYROLL_CYCLE_MENU_CODE, require_edit=True):
            raise HTTPException(status_code=403, detail="Access denied: You do not have permission to generate payroll runs")
        
        cycle = db.query(StaffPayrollCycle).filter(StaffPayrollCycle.id == cycle_id).first()
        if not cycle:
            raise HTTPException(status_code=404, detail="Payroll cycle not found")
        
        if not check_company_access(db, current_user, cycle.company_id):
            logger.warning(f"[DC-PAYROLL] Access denied: User {get_user_attr(current_user, 'employee_id')} tried to generate runs for cycle {cycle_id}")
            raise HTTPException(status_code=403, detail="Access denied: You do not have permission to generate runs for this cycle")
        
        if cycle.status != 'DRAFT':
            raise HTTPException(status_code=400, detail=f"Cannot generate runs for cycle in {cycle.status} status. Only DRAFT cycles can have runs generated.")
        
        profiles = db.query(StaffPayrollProfile).filter(
            StaffPayrollProfile.company_id == cycle.company_id,
            StaffPayrollProfile.is_active == True,
            StaffPayrollProfile.employment_type == 'ONROLE'
        ).all()
        
        if not profiles:
            raise HTTPException(status_code=400, detail="No active ONROLE payroll profiles found for this company")
        
        existing_runs = db.query(StaffPayrollRun).filter(StaffPayrollRun.cycle_id == cycle.id).all()
        existing_employee_ids = {r.employee_id for r in existing_runs}
        
        eligible_days = 30
        if cycle.period_start and cycle.period_end:
            eligible_days = (cycle.period_end - cycle.period_start).days + 1
        
        employee_ids = [p.employee_id for p in profiles if p.employee_id not in existing_employee_ids]
        attendance_map = {}
        
        if employee_ids and cycle.period_start and cycle.period_end:
            attendance_records = db.query(
                StaffAttendanceSheet.employee_id,
                StaffAttendanceSheet.attendance_status
            ).filter(
                StaffAttendanceSheet.employee_id.in_(employee_ids),
                StaffAttendanceSheet.date >= cycle.period_start,
                StaffAttendanceSheet.date <= cycle.period_end,
                StaffAttendanceSheet.company_id == cycle.company_id
            ).all()
            
            for emp_id in employee_ids:
                attendance_map[emp_id] = {'present': 0, 'half_day': 0, 'leave': 0}
            
            for record in attendance_records:
                if record.employee_id in attendance_map:
                    if record.attendance_status == AttendanceStatus.PRESENT:
                        attendance_map[record.employee_id]['present'] += 1
                    elif record.attendance_status == AttendanceStatus.HALF_DAY:
                        attendance_map[record.employee_id]['half_day'] += 1
                    elif record.attendance_status in [AttendanceStatus.APPROVED_LEAVE, AttendanceStatus.SICK_LEAVE]:
                        attendance_map[record.employee_id]['leave'] += 1
        
        logger.info(f"[DC-PAYROLL-ATTENDANCE] Eligible days: {eligible_days}, Attendance records for {len(attendance_map)} employees")
        
        created_count = 0
        skipped_count = 0
        
        for profile in profiles:
            if profile.employee_id in existing_employee_ids:
                skipped_count += 1
                continue
            
            emp_attendance = attendance_map.get(profile.employee_id, {'present': 0, 'half_day': 0, 'leave': 0})
            present_days = emp_attendance['present'] + (emp_attendance['half_day'] * 0.5) + emp_attendance['leave']
            
            if present_days == 0:
                present_days = eligible_days
            
            lop_days = max(0, eligible_days - present_days)
            
            proration_factor = present_days / eligible_days if eligible_days > 0 else 1
            
            ctc = float(profile.ctc_monthly) if profile.ctc_monthly else 0
            basic_pct = float(profile.basic_pct) if profile.basic_pct else 40
            hra_pct = float(profile.hra_pct) if profile.hra_pct else 20
            special_allowance = float(profile.special_allowance) if profile.special_allowance else 0
            
            basic = round(ctc * basic_pct / 100 * proration_factor, 2)
            hra = round(ctc * hra_pct / 100 * proration_factor, 2)
            other_components = dict(profile.other_components) if profile.other_components else {}
            other_total_orig = sum(other_components.values()) if other_components else 0
            
            remaining = round(ctc - (ctc * basic_pct / 100) - (ctc * hra_pct / 100) - special_allowance - other_total_orig, 2)
            if remaining > 0:
                other_components['Flexible Benefits'] = remaining
                other_total_orig += remaining
            
            other_components_prorated = {k: round(v * proration_factor, 2) for k, v in other_components.items()}
            other_total = sum(other_components_prorated.values())
            special_allowance_prorated = round(special_allowance * proration_factor, 2)
            
            gross = basic + hra + special_allowance_prorated + other_total
            
            pf_employee = round(basic * 0.12, 2) if profile.pf_applicable else 0
            esi_employee = round(gross * 0.0075, 2) if profile.esi_applicable and gross <= 21000 else 0
            pt = 200 if profile.pt_applicable else 0
            
            total_deductions = pf_employee + esi_employee + pt
            net_salary = round(gross - total_deductions, 2)
            
            pf_employer = round(basic * 0.12, 2) if profile.pf_applicable else 0
            esi_employer = round(gross * 0.0325, 2) if profile.esi_applicable and gross <= 21000 else 0
            
            employer_contributions = pf_employer + esi_employer
            ctc_cost = gross + employer_contributions
            
            run = StaffPayrollRun(
                run_code=generate_payroll_run_code(cycle.id, profile.employee_id),
                cycle_id=cycle.id,
                employee_id=profile.employee_id,
                company_id=cycle.company_id,
                profile_id=profile.id,
                eligible_days=eligible_days,
                present_days=present_days,
                lop_days=lop_days,
                leave_days=emp_attendance['leave'],
                ctc_monthly=ctc,
                basic_amount=basic,
                hra_amount=hra,
                special_allowance=special_allowance_prorated,
                other_earnings=other_components_prorated,
                gross_salary=gross,
                total_earnings=gross,
                pf_employee=pf_employee,
                pf_employer=pf_employer,
                esi_employee=esi_employee,
                esi_employer=esi_employer,
                pt_amount=pt,
                tds_amount=0,
                other_deductions={},
                total_deductions=total_deductions,
                net_salary=net_salary,
                employer_contributions=employer_contributions,
                ctc_cost=ctc_cost,
                status='PENDING',
                created_by_id=get_user_attr(current_user, 'employee_id')
            )
            
            db.add(run)
            created_count += 1
        
        db.commit()
        
        logger.info(f"[DC-PAYROLL] Generated {created_count} runs for cycle {cycle_id}, skipped {skipped_count}")
        
        return {
            'success': True,
            'message': f"Generated {created_count} payroll runs for {calendar.month_name[cycle.cycle_month]} {cycle.cycle_year}",
            'data': {
                'cycle_id': cycle.id,
                'runs_created': created_count,
                'runs_skipped': skipped_count,
                'total_profiles': len(profiles)
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"[DC-PAYROLL] Error generating runs: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/staff/payroll/cycles/{cycle_id}", tags=["Staff Payroll Cycles"])
async def cancel_payroll_cycle(
    cycle_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_staff_user)
):
    """Cancel a payroll cycle (DC Protocol enforced, DRAFT only)"""
    try:
        user_id = get_user_attr(current_user, 'employee_id')
        
        if not check_menu_access(db, user_id, PAYROLL_CYCLE_MENU_CODE, require_edit=True):
            raise HTTPException(status_code=403, detail="Access denied: You do not have permission to cancel payroll cycles")
        
        cycle = db.query(StaffPayrollCycle).filter(StaffPayrollCycle.id == cycle_id).first()
        if not cycle:
            raise HTTPException(status_code=404, detail="Payroll cycle not found")
        
        if not check_company_access(db, current_user, cycle.company_id):
            logger.warning(f"[DC-PAYROLL] Access denied: User {get_user_attr(current_user, 'employee_id')} tried to cancel cycle {cycle_id}")
            raise HTTPException(status_code=403, detail="Access denied: You do not have permission to cancel this cycle")
        
        if cycle.status not in ['DRAFT', 'LOCKED']:
            raise HTTPException(status_code=400, detail=f"Cannot cancel cycle in {cycle.status} status. Only DRAFT or LOCKED cycles can be cancelled.")
        
        db.query(StaffPayrollRun).filter(StaffPayrollRun.cycle_id == cycle.id).update({'status': 'CANCELLED'})
        
        cycle.status = 'CANCELLED'
        cycle.updated_at = datetime.utcnow()
        
        db.commit()
        
        logger.info(f"[DC-PAYROLL] Cycle {cycle_id} cancelled by user {get_user_attr(current_user, 'employee_id')}")
        
        return {
            'success': True,
            'message': f"Payroll cycle for {calendar.month_name[cycle.cycle_month]} {cycle.cycle_year} cancelled"
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"[DC-PAYROLL] Error cancelling cycle: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# PHASE 4: SALARY CALCULATION ENGINE
# ============================================================================

OLD_REGIME_TDS_SLABS = [
    (250000, 0),
    (500000, 0.05),
    (1000000, 0.20),
    (float('inf'), 0.30)
]

NEW_REGIME_TDS_SLABS = [
    (300000, 0),
    (700000, 0.05),
    (1000000, 0.10),
    (1200000, 0.15),
    (1500000, 0.20),
    (float('inf'), 0.30)
]


def calculate_annual_tds(annual_taxable_income: float, tax_regime: str = 'NEW') -> float:
    """Calculate annual TDS based on tax regime slabs"""
    slabs = NEW_REGIME_TDS_SLABS if tax_regime == 'NEW' else OLD_REGIME_TDS_SLABS
    
    tax = 0
    prev_limit = 0
    
    for limit, rate in slabs:
        if annual_taxable_income <= prev_limit:
            break
        taxable_in_slab = min(annual_taxable_income, limit) - prev_limit
        tax += taxable_in_slab * rate
        prev_limit = limit
    
    cess = tax * 0.04
    total_tax = tax + cess
    
    return round(total_tax, 2)


def calculate_monthly_tds(annual_taxable_income: float, tax_regime: str = 'NEW', months_remaining: int = 12) -> float:
    """Calculate monthly TDS based on annual taxable income and months remaining"""
    annual_tds = calculate_annual_tds(annual_taxable_income, tax_regime)
    monthly_tds = annual_tds / months_remaining if months_remaining > 0 else 0
    return round(monthly_tds, 2)


def calculate_salary_components(
    ctc_monthly: float,
    basic_pct: float = 40,
    hra_pct: float = 20,
    special_allowance: float = 0,
    other_components: dict = None,
    pf_applicable: bool = True,
    esi_applicable: bool = True,
    pt_applicable: bool = True,
    tds_applicable: bool = True,
    tax_regime: str = 'NEW',
    days_in_month: int = 30,
    days_worked: int = 30,
    months_remaining: int = 12
) -> dict:
    """Calculate complete salary breakdown with all components"""
    
    proration_factor = days_worked / days_in_month if days_in_month > 0 else 1
    
    basic = round(ctc_monthly * basic_pct / 100 * proration_factor, 2)
    hra = round(ctc_monthly * hra_pct / 100 * proration_factor, 2)
    special_allow = round(special_allowance * proration_factor, 2)
    
    other_comp_original = dict(other_components) if other_components else {}
    other_total_original = sum(other_comp_original.values()) if other_comp_original else 0
    
    remaining = round(ctc_monthly - (ctc_monthly * basic_pct / 100) - (ctc_monthly * hra_pct / 100) - special_allowance - other_total_original, 2)
    
    other_comp = {k: round(v * proration_factor, 2) for k, v in other_comp_original.items()}
    
    if remaining > 0:
        other_comp['Flexible Benefits'] = round(remaining * proration_factor, 2)
    
    other_total = sum(other_comp.values())
    
    gross = round(basic + hra + special_allow + other_total, 2)
    
    pf_employee = round(basic * 0.12, 2) if pf_applicable else 0
    pf_employer = round(basic * 0.12, 2) if pf_applicable else 0
    
    esi_employee = round(gross * 0.0075, 2) if esi_applicable and gross <= 21000 else 0
    esi_employer = round(gross * 0.0325, 2) if esi_applicable and gross <= 21000 else 0
    
    pt = 200 if pt_applicable else 0
    
    annual_gross = gross * 12 / proration_factor if proration_factor > 0 else 0
    annual_pf_employee = pf_employee * 12 / proration_factor if proration_factor > 0 else 0
    standard_deduction = 50000
    taxable_income = max(0, annual_gross - annual_pf_employee - standard_deduction)
    
    tds = calculate_monthly_tds(taxable_income, tax_regime, months_remaining) if tds_applicable else 0
    
    total_employee_deductions = round(pf_employee + esi_employee + pt + tds, 2)
    total_employer_contributions = round(pf_employer + esi_employer, 2)
    net_salary = round(gross - total_employee_deductions, 2)
    
    return {
        'earnings': {
            'basic': basic,
            'hra': hra,
            'special_allowance': special_allow,
            'other_components': other_comp,
            'gross_salary': gross
        },
        'deductions': {
            'pf_employee': pf_employee,
            'pf_employer': pf_employer,
            'esi_employee': esi_employee,
            'esi_employer': esi_employer,
            'professional_tax': pt,
            'tds': tds,
            'total_employee': total_employee_deductions,
            'total_employer': total_employer_contributions
        },
        'summary': {
            'gross_salary': gross,
            'total_deductions': total_employee_deductions,
            'net_salary': net_salary,
            'ctc_with_employer': round(gross + total_employer_contributions, 2)
        },
        'proration': {
            'days_in_month': days_in_month,
            'days_worked': days_worked,
            'factor': round(proration_factor, 4)
        },
        'tax_info': {
            'regime': tax_regime,
            'annual_taxable': round(taxable_income, 2),
            'annual_tds': calculate_annual_tds(taxable_income, tax_regime),
            'monthly_tds': tds
        }
    }


class PayrollRunUpdate(BaseModel):
    days_worked: Optional[int] = Field(None, ge=0, le=31)
    days_present: Optional[int] = Field(None, ge=0, le=31)
    leaves_taken: Optional[int] = Field(None, ge=0, le=31)
    other_earnings: Optional[Dict[str, float]] = None
    other_deductions: Optional[Dict[str, float]] = None
    notes: Optional[str] = None


@router.get("/staff/payroll/runs", tags=["Staff Payroll Runs"])
async def list_payroll_runs(
    cycle_id: Optional[int] = Query(None, description="Filter by cycle"),
    employee_id: Optional[int] = Query(None, description="Filter by employee"),
    status: Optional[str] = Query(None, description="Filter by status"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_staff_user)
):
    """List payroll runs with DC Protocol filtering"""
    try:
        user_id = get_user_attr(current_user, 'employee_id')
        user_company_id = get_user_attr(current_user, 'company_id')
        
        if not check_menu_access(db, user_id, PAYROLL_CYCLE_MENU_CODE, require_edit=False):
            raise HTTPException(status_code=403, detail="Access denied: You do not have permission to view payroll runs")
        
        accessible_companies = get_user_accessible_companies(db, user_id, user_company_id)
        
        query = db.query(StaffPayrollRun).join(
            StaffPayrollCycle, StaffPayrollRun.cycle_id == StaffPayrollCycle.id
        ).filter(
            StaffPayrollCycle.company_id.in_(accessible_companies)
        )
        
        if cycle_id:
            query = query.filter(StaffPayrollRun.cycle_id == cycle_id)
        
        if employee_id:
            query = query.filter(StaffPayrollRun.employee_id == employee_id)
        
        if status:
            query = query.filter(StaffPayrollRun.status == status.upper())
        
        total = query.count()
        
        runs = query.order_by(desc(StaffPayrollRun.created_at)).offset((page - 1) * limit).limit(limit).all()
        
        result = []
        for run in runs:
            employee = db.query(StaffEmployee).filter(StaffEmployee.id == run.employee_id).first()
            cycle = db.query(StaffPayrollCycle).filter(StaffPayrollCycle.id == run.cycle_id).first()
            
            result.append({
                'id': run.id,
                'run_code': run.run_code or f"RUN-{run.id}",
                'cycle_id': run.cycle_id,
                'cycle_name': f"{calendar.month_name[cycle.cycle_month]} {cycle.cycle_year}" if cycle else 'Unknown',
                'company_id': run.company_id,
                'employee_id': run.employee_id,
                'employee_name': employee.full_name if employee else 'Unknown',
                'employee_code': employee.emp_code if employee else 'N/A',
                'eligible_days': int(run.eligible_days) if run.eligible_days else 0,
                'days_worked': int(run.present_days) if run.present_days else 0,
                'days_present': int(run.present_days) if run.present_days else 0,
                'leave_days': int(run.leave_days) if run.leave_days else 0,
                'lop_days': int(run.lop_days) if run.lop_days else 0,
                'ctc_monthly': float(run.ctc_monthly) if run.ctc_monthly else 0,
                'basic_amount': float(run.basic_amount) if run.basic_amount else 0,
                'hra_amount': float(run.hra_amount) if run.hra_amount else 0,
                'special_allowance': float(run.special_allowance) if run.special_allowance else 0,
                'gross_salary': float(run.gross_salary) if run.gross_salary else 0,
                'total_earnings': float(run.total_earnings) if run.total_earnings else 0,
                'pf_employee': float(run.pf_employee) if run.pf_employee else 0,
                'esi_employee': float(run.esi_employee) if run.esi_employee else 0,
                'pt_amount': float(run.pt_amount) if run.pt_amount else 0,
                'tds_amount': float(run.tds_amount) if run.tds_amount else 0,
                'total_deductions': float(run.total_deductions) if run.total_deductions else 0,
                'net_salary': float(run.net_salary) if run.net_salary else 0,
                'status': run.status,
                'created_at': run.created_at.isoformat() if run.created_at else None
            })
        
        return {
            'success': True,
            'data': result,
            'pagination': {
                'total': total,
                'page': page,
                'limit': limit,
                'pages': (total + limit - 1) // limit
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[DC-PAYROLL] Error listing runs: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/staff/payroll/runs/{run_id}", tags=["Staff Payroll Runs"])
async def get_payroll_run(
    run_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_staff_user)
):
    """Get detailed payroll run information (DC Protocol enforced)"""
    try:
        user_id = get_user_attr(current_user, 'employee_id')
        
        if not check_menu_access(db, user_id, PAYROLL_CYCLE_MENU_CODE, require_edit=False):
            raise HTTPException(status_code=403, detail="Access denied: You do not have permission to view payroll runs")
        
        run = db.query(StaffPayrollRun).filter(StaffPayrollRun.id == run_id).first()
        if not run:
            raise HTTPException(status_code=404, detail="Payroll run not found")
        
        cycle = db.query(StaffPayrollCycle).filter(StaffPayrollCycle.id == run.cycle_id).first()
        if not cycle:
            raise HTTPException(status_code=404, detail="Associated cycle not found")
        
        if not check_company_access(db, current_user, cycle.company_id):
            logger.warning(f"[DC-PAYROLL] Access denied: User {user_id} tried to view run {run_id}")
            raise HTTPException(status_code=403, detail="Access denied: You do not have permission to view this run")
        
        employee = db.query(StaffEmployee).filter(StaffEmployee.id == run.employee_id).first()
        profile = db.query(StaffPayrollProfile).filter(StaffPayrollProfile.id == run.profile_id).first()
        company = db.query(AssociatedCompany).filter(AssociatedCompany.id == cycle.company_id).first()
        
        return {
            'success': True,
            'data': {
                'id': run.id,
                'cycle': {
                    'id': cycle.id,
                    'name': f"{calendar.month_name[cycle.cycle_month]} {cycle.cycle_year}",
                    'period_start': cycle.period_start.isoformat() if cycle.period_start else None,
                    'period_end': cycle.period_end.isoformat() if cycle.period_end else None,
                    'status': cycle.status
                },
                'employee': {
                    'id': run.employee_id,
                    'name': employee.full_name if employee else 'Unknown',
                    'code': employee.emp_code if employee else 'N/A',
                    'designation': employee.designation if employee else None
                },
                'company': {
                    'id': cycle.company_id,
                    'name': company.company_name if company else 'Unknown'
                },
                'attendance': {
                    'days_worked': int(run.present_days) if run.present_days else 0,
                    'days_present': int(run.present_days) if run.present_days else 0,
                    'leaves_taken': int(run.leave_days) if run.leave_days else 0
                },
                'earnings': {
                    'basic_salary': float(run.basic_amount) if run.basic_amount else 0,
                    'hra': float(run.hra_amount) if run.hra_amount else 0,
                    'special_allowance': float(run.special_allowance) if run.special_allowance else 0,
                    'other_earnings': run.other_earnings or {},
                    'gross_salary': float(run.gross_salary) if run.gross_salary else 0
                },
                'deductions': {
                    'pf_employee': float(run.pf_employee) if run.pf_employee else 0,
                    'pf_employer': float(run.pf_employer) if run.pf_employer else 0,
                    'esi_employee': float(run.esi_employee) if run.esi_employee else 0,
                    'esi_employer': float(run.esi_employer) if run.esi_employer else 0,
                    'professional_tax': float(run.pt_amount) if run.pt_amount else 0,
                    'tds': float(run.tds_amount) if run.tds_amount else 0,
                    'other_deductions': run.other_deductions or {},
                    'total_deductions': float(run.total_deductions) if run.total_deductions else 0
                },
                'summary': {
                    'gross_salary': float(run.gross_salary) if run.gross_salary else 0,
                    'total_deductions': float(run.total_deductions) if run.total_deductions else 0,
                    'net_salary': float(run.net_salary) if run.net_salary else 0
                },
                'status': run.status,
                'payment_status': run.payment_status,
                'payment_date': run.payment_date.isoformat() if run.payment_date else None,
                'payment_reference': run.payment_reference,
                'notes': run.notes,
                'created_at': run.created_at.isoformat() if run.created_at else None,
                'updated_at': run.updated_at.isoformat() if run.updated_at else None
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[DC-PAYROLL] Error getting run: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/staff/payroll/runs/{run_id}", tags=["Staff Payroll Runs"])
async def update_payroll_run(
    run_id: int,
    run_data: PayrollRunUpdate = Body(...),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_staff_user)
):
    """Update payroll run attendance/adjustments (DC Protocol enforced, PENDING only)"""
    try:
        user_id = get_user_attr(current_user, 'employee_id')
        
        if not check_menu_access(db, user_id, PAYROLL_CYCLE_MENU_CODE, require_edit=True):
            raise HTTPException(status_code=403, detail="Access denied: You do not have permission to update payroll runs")
        
        run = db.query(StaffPayrollRun).filter(StaffPayrollRun.id == run_id).first()
        if not run:
            raise HTTPException(status_code=404, detail="Payroll run not found")
        
        cycle = db.query(StaffPayrollCycle).filter(StaffPayrollCycle.id == run.cycle_id).first()
        if not cycle:
            raise HTTPException(status_code=404, detail="Associated cycle not found")
        
        if not check_company_access(db, current_user, cycle.company_id):
            logger.warning(f"[DC-PAYROLL] Access denied: User {user_id} tried to update run {run_id}")
            raise HTTPException(status_code=403, detail="Access denied: You do not have permission to update this run")
        
        if run.status not in ['PENDING', 'REJECTED']:
            raise HTTPException(status_code=400, detail=f"Cannot update run in {run.status} status. Only PENDING or REJECTED runs can be modified.")
        
        if run_data.days_worked is not None:
            run.present_days = run_data.days_worked
        if run_data.days_present is not None:
            run.present_days = run_data.days_present
        if run_data.leaves_taken is not None:
            run.leave_days = run_data.leaves_taken
        if run_data.other_earnings is not None:
            existing = run.other_earnings or {}
            existing.update(run_data.other_earnings)
            run.other_earnings = existing
        if run_data.other_deductions is not None:
            existing = run.other_deductions or {}
            existing.update(run_data.other_deductions)
            run.other_deductions = existing
        if run_data.notes is not None:
            run.notes = run_data.notes
        
        run.updated_at = datetime.utcnow()
        db.commit()
        
        return {
            'success': True,
            'message': "Payroll run updated successfully",
            'data': {
                'id': run.id,
                'days_worked': int(run.present_days) if run.present_days else 0,
                'days_present': int(run.present_days) if run.present_days else 0,
                'leaves_taken': int(run.leave_days) if run.leave_days else 0,
                'status': run.status
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"[DC-PAYROLL] Error updating run: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/staff/payroll/runs/{run_id}/recalculate", tags=["Staff Payroll Runs"])
async def recalculate_payroll_run(
    run_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_staff_user)
):
    """Recalculate salary for a payroll run based on current profile and attendance (DC Protocol enforced)"""
    try:
        user_id = get_user_attr(current_user, 'employee_id')
        
        if not check_menu_access(db, user_id, PAYROLL_CYCLE_MENU_CODE, require_edit=True):
            raise HTTPException(status_code=403, detail="Access denied: You do not have permission to recalculate payroll runs")
        
        run = db.query(StaffPayrollRun).filter(StaffPayrollRun.id == run_id).first()
        if not run:
            raise HTTPException(status_code=404, detail="Payroll run not found")
        
        cycle = db.query(StaffPayrollCycle).filter(StaffPayrollCycle.id == run.cycle_id).first()
        if not cycle:
            raise HTTPException(status_code=404, detail="Associated cycle not found")
        
        if not check_company_access(db, current_user, cycle.company_id):
            logger.warning(f"[DC-PAYROLL] Access denied: User {user_id} tried to recalculate run {run_id}")
            raise HTTPException(status_code=403, detail="Access denied: You do not have permission to recalculate this run")
        
        if run.status not in ['PENDING', 'REJECTED']:
            raise HTTPException(status_code=400, detail=f"Cannot recalculate run in {run.status} status. Only PENDING or REJECTED runs can be recalculated.")
        
        profile = db.query(StaffPayrollProfile).filter(StaffPayrollProfile.id == run.profile_id).first()
        if not profile:
            raise HTTPException(status_code=404, detail="Payroll profile not found")
        
        days_in_month = 30
        if cycle.period_start and cycle.period_end:
            days_in_month = (cycle.period_end - cycle.period_start).days + 1
        
        days_worked = int(run.present_days) if run.present_days is not None else days_in_month
        
        months_remaining = 12 - cycle.cycle_month + 1
        
        calc = calculate_salary_components(
            ctc_monthly=float(profile.ctc_monthly) if profile.ctc_monthly else 0,
            basic_pct=float(profile.basic_pct) if profile.basic_pct else 40,
            hra_pct=float(profile.hra_pct) if profile.hra_pct else 20,
            special_allowance=float(profile.special_allowance) if profile.special_allowance else 0,
            other_components=profile.other_components,
            pf_applicable=profile.pf_applicable,
            esi_applicable=profile.esi_applicable,
            pt_applicable=profile.pt_applicable,
            tds_applicable=profile.tds_applicable,
            tax_regime=profile.tax_regime or 'NEW',
            days_in_month=days_in_month,
            days_worked=days_worked,
            months_remaining=months_remaining
        )
        
        run.basic_amount = calc['earnings']['basic']
        run.hra_amount = calc['earnings']['hra']
        run.special_allowance = calc['earnings']['special_allowance']
        run.other_earnings = calc['earnings']['other_components']
        run.gross_salary = calc['earnings']['gross_salary']
        
        run.pf_employee = calc['deductions']['pf_employee']
        run.pf_employer = calc['deductions']['pf_employer']
        run.esi_employee = calc['deductions']['esi_employee']
        run.esi_employer = calc['deductions']['esi_employer']
        run.pt_amount = calc['deductions']['professional_tax']
        run.tds_amount = calc['deductions']['tds']
        
        other_ded_total = sum((run.other_deductions or {}).values())
        run.total_deductions = calc['deductions']['total_employee'] + other_ded_total
        run.net_salary = round(calc['earnings']['gross_salary'] - run.total_deductions, 2)
        
        run.updated_at = datetime.utcnow()
        db.commit()
        
        logger.info(f"[DC-PAYROLL] Run {run_id} recalculated by user {user_id}")
        
        return {
            'success': True,
            'message': "Payroll run recalculated successfully",
            'data': {
                'id': run.id,
                'gross_salary': float(run.gross_salary),
                'total_deductions': float(run.total_deductions),
                'net_salary': float(run.net_salary),
                'calculation_details': calc
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"[DC-PAYROLL] Error recalculating run: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/staff/payroll/calculate-preview", tags=["Staff Payroll Runs"])
async def preview_salary_calculation(
    ctc_monthly: float = Query(..., description="Monthly CTC"),
    basic_pct: float = Query(40, description="Basic percentage"),
    hra_pct: float = Query(20, description="HRA percentage"),
    special_allowance: float = Query(0, description="Special allowance amount"),
    pf_applicable: bool = Query(True, description="PF applicable"),
    esi_applicable: bool = Query(True, description="ESI applicable"),
    pt_applicable: bool = Query(True, description="PT applicable"),
    tds_applicable: bool = Query(True, description="TDS applicable"),
    tax_regime: str = Query("NEW", description="Tax regime (OLD/NEW)"),
    days_in_month: int = Query(30, description="Days in month"),
    days_worked: int = Query(30, description="Days worked"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_staff_user)
):
    """Preview salary calculation without creating a run"""
    try:
        user_id = get_user_attr(current_user, 'employee_id')
        
        if not check_menu_access(db, user_id, PAYROLL_PROFILE_MENU_CODE, require_edit=False):
            raise HTTPException(status_code=403, detail="Access denied: You do not have permission to preview salary calculations")
        
        calc = calculate_salary_components(
            ctc_monthly=ctc_monthly,
            basic_pct=basic_pct,
            hra_pct=hra_pct,
            special_allowance=special_allowance,
            pf_applicable=pf_applicable,
            esi_applicable=esi_applicable,
            pt_applicable=pt_applicable,
            tds_applicable=tds_applicable,
            tax_regime=tax_regime.upper(),
            days_in_month=days_in_month,
            days_worked=days_worked
        )
        
        return {
            'success': True,
            'data': calc
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[DC-PAYROLL] Error in salary preview: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# CUSTOMIZED ALLOWANCE SEGMENTS (Special Allowance, Travel Allowance, etc.)
# ============================================================================

DEFAULT_ALLOWANCE_TYPES = [
    {'code': 'SPECIAL_ALLOWANCE', 'name': 'Special Allowance', 'description': 'Special allowance component', 'taxable': True, 'is_percentage': False},
    {'code': 'TRAVEL_ALLOWANCE', 'name': 'Travel Allowance', 'description': 'Travel/conveyance reimbursement', 'taxable': True, 'is_percentage': False},
    {'code': 'CONVEYANCE_ALLOWANCE', 'name': 'Conveyance Allowance', 'description': 'Daily conveyance allowance', 'taxable': True, 'is_percentage': False},
    {'code': 'MEDICAL_ALLOWANCE', 'name': 'Medical Allowance', 'description': 'Medical expense allowance', 'taxable': True, 'is_percentage': False},
    {'code': 'TELEPHONE_ALLOWANCE', 'name': 'Telephone Allowance', 'description': 'Telephone/mobile reimbursement', 'taxable': True, 'is_percentage': False},
    {'code': 'LTA', 'name': 'Leave Travel Allowance', 'description': 'Leave travel allowance (LTA/LTC)', 'taxable': False, 'is_percentage': False},
    {'code': 'FOOD_ALLOWANCE', 'name': 'Food Allowance', 'description': 'Food/meal allowance', 'taxable': True, 'is_percentage': False},
    {'code': 'EDUCATION_ALLOWANCE', 'name': 'Education Allowance', 'description': 'Children education allowance', 'taxable': False, 'is_percentage': False},
    {'code': 'UNIFORM_ALLOWANCE', 'name': 'Uniform Allowance', 'description': 'Uniform/dress allowance', 'taxable': True, 'is_percentage': False},
    {'code': 'HOUSE_RENT_ALLOWANCE', 'name': 'House Rent Allowance', 'description': 'Additional HRA component', 'taxable': False, 'is_percentage': True},
    {'code': 'DEARNESS_ALLOWANCE', 'name': 'Dearness Allowance', 'description': 'Dearness allowance (DA)', 'taxable': True, 'is_percentage': True},
    {'code': 'CITY_COMPENSATORY_ALLOWANCE', 'name': 'City Compensatory Allowance', 'description': 'Metro/city allowance', 'taxable': True, 'is_percentage': False},
    {'code': 'PERFORMANCE_BONUS', 'name': 'Performance Bonus', 'description': 'Monthly performance incentive', 'taxable': True, 'is_percentage': False},
    {'code': 'INCENTIVE', 'name': 'Incentive', 'description': 'Sales/target incentive', 'taxable': True, 'is_percentage': False},
    {'code': 'OVERTIME', 'name': 'Overtime Pay', 'description': 'Overtime compensation', 'taxable': True, 'is_percentage': False},
    {'code': 'FLEXIBLE_BENEFITS', 'name': 'Flexible Benefits', 'description': 'Auto-calculated remaining CTC', 'taxable': True, 'is_percentage': False},
    {'code': 'OTHER', 'name': 'Other Allowance', 'description': 'Miscellaneous allowance', 'taxable': True, 'is_percentage': False},
]

DEFAULT_DEDUCTION_TYPES = [
    {'code': 'PF_EMPLOYEE', 'name': 'PF (Employee)', 'description': 'Provident Fund employee contribution', 'is_percentage': True, 'default_rate': 12.0},
    {'code': 'ESI_EMPLOYEE', 'name': 'ESI (Employee)', 'description': 'ESI employee contribution', 'is_percentage': True, 'default_rate': 0.75},
    {'code': 'PROFESSIONAL_TAX', 'name': 'Professional Tax', 'description': 'State professional tax', 'is_percentage': False, 'default_rate': 200},
    {'code': 'TDS', 'name': 'TDS', 'description': 'Tax Deducted at Source', 'is_percentage': True, 'default_rate': None},
    {'code': 'LOAN_RECOVERY', 'name': 'Loan Recovery', 'description': 'Employee loan EMI deduction', 'is_percentage': False, 'default_rate': None},
    {'code': 'SALARY_ADVANCE', 'name': 'Salary Advance', 'description': 'Salary advance recovery', 'is_percentage': False, 'default_rate': None},
    {'code': 'LEAVE_DEDUCTION', 'name': 'Leave Without Pay', 'description': 'LWP deduction', 'is_percentage': False, 'default_rate': None},
    {'code': 'OTHER_DEDUCTION', 'name': 'Other Deduction', 'description': 'Miscellaneous deduction', 'is_percentage': False, 'default_rate': None},
]


class CustomAllowanceCreate(BaseModel):
    code: str = Field(..., min_length=2, max_length=50, description="Unique code for allowance")
    name: str = Field(..., min_length=2, max_length=100, description="Display name")
    description: Optional[str] = None
    taxable: bool = True
    is_percentage: bool = False


class AllowanceComponentAdd(BaseModel):
    allowance_code: str = Field(..., description="Allowance type code")
    amount: float = Field(..., ge=0, description="Amount or percentage value")
    is_percentage: bool = Field(False, description="If true, amount is treated as percentage of CTC")


@router.get("/staff/payroll/allowance-types", tags=["Staff Payroll Allowances"])
async def list_allowance_types(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_staff_user)
):
    """Get list of available allowance types (default + custom)"""
    try:
        user_id = get_user_attr(current_user, 'employee_id')
        
        if not check_menu_access(db, user_id, PAYROLL_PROFILE_MENU_CODE, require_edit=False):
            raise HTTPException(status_code=403, detail="Access denied: You do not have permission to view allowance types")
        
        return {
            'success': True,
            'data': {
                'allowances': DEFAULT_ALLOWANCE_TYPES,
                'deductions': DEFAULT_DEDUCTION_TYPES
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[DC-PAYROLL] Error listing allowance types: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/staff/payroll/profiles/{profile_id}/allowances", tags=["Staff Payroll Allowances"])
async def update_profile_allowances(
    profile_id: int,
    allowances: List[AllowanceComponentAdd] = Body(..., description="List of allowance components to set"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_staff_user)
):
    """Update custom allowance components for a payroll profile (DC Protocol enforced)"""
    try:
        user_id = get_user_attr(current_user, 'employee_id')
        
        if not check_menu_access(db, user_id, PAYROLL_PROFILE_MENU_CODE, require_edit=True):
            raise HTTPException(status_code=403, detail="Access denied: You do not have permission to update allowances")
        
        profile = db.query(StaffPayrollProfile).filter(StaffPayrollProfile.id == profile_id).first()
        if not profile:
            raise HTTPException(status_code=404, detail="Payroll profile not found")
        
        if not check_company_access(db, current_user, profile.company_id):
            logger.warning(f"[DC-PAYROLL] Access denied: User {user_id} tried to update allowances for profile {profile_id}")
            raise HTTPException(status_code=403, detail="Access denied: You do not have permission to update this profile")
        
        ctc = float(profile.ctc_monthly) if profile.ctc_monthly else 0
        basic_pct = float(profile.basic_pct) if profile.basic_pct else 40
        hra_pct = float(profile.hra_pct) if profile.hra_pct else 20
        special_allowance = float(profile.special_allowance) if profile.special_allowance else 0
        
        basic_amount = ctc * basic_pct / 100
        hra_amount = ctc * hra_pct / 100
        fixed_components = basic_amount + hra_amount + special_allowance
        
        other_components = {}
        total_allowances = 0
        
        for allowance in allowances:
            if allowance.is_percentage:
                amount = round(ctc * allowance.amount / 100, 2)
            else:
                amount = round(allowance.amount, 2)
            
            allowance_name = allowance.allowance_code.replace('_', ' ').title()
            for default in DEFAULT_ALLOWANCE_TYPES:
                if default['code'] == allowance.allowance_code:
                    allowance_name = default['name']
                    break
            
            other_components[allowance_name] = amount
            total_allowances += amount
        
        total_configured = fixed_components + total_allowances
        if total_configured > ctc:
            raise HTTPException(
                status_code=400, 
                detail=f"CTC budget exceeded: Total configured amount (₹{total_configured:.2f}) exceeds CTC (₹{ctc:.2f}). "
                       f"Available budget after Basic+HRA+Special: ₹{max(0, ctc - fixed_components):.2f}"
            )
        
        profile.other_components = other_components
        profile.updated_at = datetime.utcnow()
        db.commit()
        
        logger.info(f"[DC-PAYROLL] Updated allowances for profile {profile_id} by user {user_id}")
        
        return {
            'success': True,
            'message': f"Updated {len(allowances)} allowance components",
            'data': {
                'profile_id': profile_id,
                'other_components': other_components,
                'total_custom_allowances': round(total_allowances, 2)
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"[DC-PAYROLL] Error updating allowances: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/staff/payroll/profiles/{profile_id}/allowances/add", tags=["Staff Payroll Allowances"])
async def add_profile_allowance(
    profile_id: int,
    allowance: AllowanceComponentAdd = Body(...),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_staff_user)
):
    """Add a single allowance component to a payroll profile (DC Protocol enforced)"""
    try:
        user_id = get_user_attr(current_user, 'employee_id')
        
        if not check_menu_access(db, user_id, PAYROLL_PROFILE_MENU_CODE, require_edit=True):
            raise HTTPException(status_code=403, detail="Access denied: You do not have permission to add allowances")
        
        profile = db.query(StaffPayrollProfile).filter(StaffPayrollProfile.id == profile_id).first()
        if not profile:
            raise HTTPException(status_code=404, detail="Payroll profile not found")
        
        if not check_company_access(db, current_user, profile.company_id):
            logger.warning(f"[DC-PAYROLL] Access denied: User {user_id} tried to add allowance to profile {profile_id}")
            raise HTTPException(status_code=403, detail="Access denied: You do not have permission to update this profile")
        
        ctc = float(profile.ctc_monthly) if profile.ctc_monthly else 0
        basic_pct = float(profile.basic_pct) if profile.basic_pct else 40
        hra_pct = float(profile.hra_pct) if profile.hra_pct else 20
        special_allowance_val = float(profile.special_allowance) if profile.special_allowance else 0
        
        if allowance.is_percentage:
            amount = round(ctc * allowance.amount / 100, 2)
        else:
            amount = round(allowance.amount, 2)
        
        allowance_name = allowance.allowance_code.replace('_', ' ').title()
        for default in DEFAULT_ALLOWANCE_TYPES:
            if default['code'] == allowance.allowance_code:
                allowance_name = default['name']
                break
        
        other_components = dict(profile.other_components) if profile.other_components else {}
        
        basic_amount = ctc * basic_pct / 100
        hra_amount = ctc * hra_pct / 100
        fixed_components = basic_amount + hra_amount + special_allowance_val
        existing_allowances = sum(other_components.values())
        
        new_total = fixed_components + existing_allowances + amount
        if allowance_name in other_components:
            new_total = new_total - other_components[allowance_name]
        
        if new_total > ctc:
            raise HTTPException(
                status_code=400, 
                detail=f"CTC budget exceeded: Adding this allowance would result in ₹{new_total:.2f} which exceeds CTC (₹{ctc:.2f}). "
                       f"Available budget: ₹{max(0, ctc - fixed_components - existing_allowances):.2f}"
            )
        
        other_components[allowance_name] = amount
        
        profile.other_components = other_components
        profile.updated_at = datetime.utcnow()
        db.commit()
        
        return {
            'success': True,
            'message': f"Added {allowance_name}: {amount}",
            'data': {
                'profile_id': profile_id,
                'allowance_name': allowance_name,
                'amount': amount,
                'other_components': other_components
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"[DC-PAYROLL] Error adding allowance: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/staff/payroll/profiles/{profile_id}/allowances/{allowance_name}", tags=["Staff Payroll Allowances"])
async def remove_profile_allowance(
    profile_id: int,
    allowance_name: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_staff_user)
):
    """Remove an allowance component from a payroll profile (DC Protocol enforced)"""
    try:
        user_id = get_user_attr(current_user, 'employee_id')
        
        if not check_menu_access(db, user_id, PAYROLL_PROFILE_MENU_CODE, require_edit=True):
            raise HTTPException(status_code=403, detail="Access denied: You do not have permission to remove allowances")
        
        profile = db.query(StaffPayrollProfile).filter(StaffPayrollProfile.id == profile_id).first()
        if not profile:
            raise HTTPException(status_code=404, detail="Payroll profile not found")
        
        if not check_company_access(db, current_user, profile.company_id):
            logger.warning(f"[DC-PAYROLL] Access denied: User {user_id} tried to remove allowance from profile {profile_id}")
            raise HTTPException(status_code=403, detail="Access denied: You do not have permission to update this profile")
        
        other_components = dict(profile.other_components) if profile.other_components else {}
        
        decoded_name = allowance_name.replace('%20', ' ').replace('+', ' ')
        
        if decoded_name not in other_components:
            raise HTTPException(status_code=404, detail=f"Allowance '{decoded_name}' not found in profile")
        
        removed_amount = other_components.pop(decoded_name)
        
        profile.other_components = other_components
        profile.updated_at = datetime.utcnow()
        db.commit()
        
        return {
            'success': True,
            'message': f"Removed {decoded_name}",
            'data': {
                'profile_id': profile_id,
                'removed_allowance': decoded_name,
                'removed_amount': removed_amount,
                'other_components': other_components
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"[DC-PAYROLL] Error removing allowance: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


class AllowanceCatalogCreate(BaseModel):
    allowance_code: str = Field(..., min_length=2, max_length=50)
    allowance_name: str = Field(..., min_length=2, max_length=200)
    allowance_description: Optional[str] = None
    is_taxable: bool = Field(True)
    is_percentage: bool = Field(False)
    default_value: Optional[float] = None
    max_limit: Optional[float] = None
    applicable_employment_types: Optional[List[str]] = Field(default=['ONROLE', 'OFFROLE'])
    display_order: int = Field(100, ge=1)


class AllowanceCatalogUpdate(BaseModel):
    allowance_name: Optional[str] = Field(None, min_length=2, max_length=200)
    allowance_description: Optional[str] = None
    is_taxable: Optional[bool] = None
    is_percentage: Optional[bool] = None
    default_value: Optional[float] = None
    max_limit: Optional[float] = None
    applicable_employment_types: Optional[List[str]] = None
    display_order: Optional[int] = Field(None, ge=1)
    is_active: Optional[bool] = None


@router.get("/staff/payroll/allowance-catalog", tags=["Staff Payroll Allowance Catalog"])
async def list_allowance_catalog(
    company_id: Optional[int] = Query(None, description="Filter by company"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_staff_user)
):
    """List custom allowance catalog entries with DC Protocol filtering"""
    try:
        user_id = get_user_attr(current_user, 'employee_id')
        user_company_id = get_user_attr(current_user, 'company_id')
        
        if not check_menu_access(db, user_id, PAYROLL_PROFILE_MENU_CODE, require_edit=False):
            raise HTTPException(status_code=403, detail="Access denied: You do not have permission to view allowance catalog")
        
        accessible_companies = get_user_accessible_companies(db, user_id, user_company_id)
        
        query = db.query(StaffPayrollAllowanceCatalog).filter(
            StaffPayrollAllowanceCatalog.company_id.in_(accessible_companies)
        )
        
        if company_id:
            if company_id not in accessible_companies:
                raise HTTPException(status_code=403, detail="Access denied: You do not have access to this company")
            query = query.filter(StaffPayrollAllowanceCatalog.company_id == company_id)
        
        if is_active is not None:
            query = query.filter(StaffPayrollAllowanceCatalog.is_active == is_active)
        
        total = query.count()
        
        entries = query.order_by(
            StaffPayrollAllowanceCatalog.display_order,
            StaffPayrollAllowanceCatalog.allowance_name
        ).offset((page - 1) * limit).limit(limit).all()
        
        combined_list = list(DEFAULT_ALLOWANCE_TYPES) + [e.to_dict() for e in entries]
        
        return {
            'success': True,
            'data': [e.to_dict() for e in entries],
            'default_types': DEFAULT_ALLOWANCE_TYPES,
            'pagination': {
                'total': total,
                'page': page,
                'limit': limit,
                'pages': (total + limit - 1) // limit if limit > 0 else 0
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[DC-PAYROLL] Error listing allowance catalog: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/staff/payroll/allowance-catalog", tags=["Staff Payroll Allowance Catalog"])
async def create_allowance_catalog_entry(
    company_id: int = Query(..., description="Company ID for the allowance"),
    data: AllowanceCatalogCreate = Body(...),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_staff_user)
):
    """Create a new custom allowance type for a company (DC Protocol enforced)"""
    try:
        user_id = get_user_attr(current_user, 'employee_id')
        
        if not check_menu_access(db, user_id, PAYROLL_PROFILE_MENU_CODE, require_edit=True):
            raise HTTPException(status_code=403, detail="Access denied: You do not have permission to create allowance types")
        
        if not check_company_access(db, current_user, company_id):
            raise HTTPException(status_code=403, detail="Access denied: You do not have access to this company")
        
        existing = db.query(StaffPayrollAllowanceCatalog).filter(
            StaffPayrollAllowanceCatalog.company_id == company_id,
            StaffPayrollAllowanceCatalog.allowance_code == data.allowance_code.upper()
        ).first()
        
        if existing:
            raise HTTPException(status_code=400, detail=f"Allowance code '{data.allowance_code}' already exists for this company")
        
        for default in DEFAULT_ALLOWANCE_TYPES:
            if default['code'] == data.allowance_code.upper():
                raise HTTPException(status_code=400, detail=f"Allowance code '{data.allowance_code}' is a predefined system type")
        
        entry = StaffPayrollAllowanceCatalog(
            company_id=company_id,
            allowance_code=data.allowance_code.upper(),
            allowance_name=data.allowance_name,
            allowance_description=data.allowance_description,
            is_taxable=data.is_taxable,
            is_percentage=data.is_percentage,
            default_value=data.default_value,
            max_limit=data.max_limit,
            applicable_employment_types=data.applicable_employment_types,
            display_order=data.display_order,
            is_active=True,
            created_by_id=user_id
        )
        
        db.add(entry)
        db.commit()
        db.refresh(entry)
        
        logger.info(f"[DC-PAYROLL] Created allowance catalog entry {entry.id} by user {user_id}")
        
        return {
            'success': True,
            'message': f"Created allowance type '{data.allowance_name}'",
            'data': entry.to_dict()
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"[DC-PAYROLL] Error creating allowance catalog: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/staff/payroll/allowance-catalog/{entry_id}", tags=["Staff Payroll Allowance Catalog"])
async def get_allowance_catalog_entry(
    entry_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_staff_user)
):
    """Get a specific allowance catalog entry (DC Protocol enforced)"""
    try:
        user_id = get_user_attr(current_user, 'employee_id')
        
        if not check_menu_access(db, user_id, PAYROLL_PROFILE_MENU_CODE, require_edit=False):
            raise HTTPException(status_code=403, detail="Access denied")
        
        entry = db.query(StaffPayrollAllowanceCatalog).filter(
            StaffPayrollAllowanceCatalog.id == entry_id
        ).first()
        
        if not entry:
            raise HTTPException(status_code=404, detail="Allowance catalog entry not found")
        
        if not check_company_access(db, current_user, entry.company_id):
            raise HTTPException(status_code=403, detail="Access denied: You do not have access to this company")
        
        return {
            'success': True,
            'data': entry.to_dict()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[DC-PAYROLL] Error getting allowance catalog entry: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/staff/payroll/allowance-catalog/{entry_id}", tags=["Staff Payroll Allowance Catalog"])
async def update_allowance_catalog_entry(
    entry_id: int,
    data: AllowanceCatalogUpdate = Body(...),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_staff_user)
):
    """Update an allowance catalog entry (DC Protocol enforced)"""
    try:
        user_id = get_user_attr(current_user, 'employee_id')
        
        if not check_menu_access(db, user_id, PAYROLL_PROFILE_MENU_CODE, require_edit=True):
            raise HTTPException(status_code=403, detail="Access denied")
        
        entry = db.query(StaffPayrollAllowanceCatalog).filter(
            StaffPayrollAllowanceCatalog.id == entry_id
        ).first()
        
        if not entry:
            raise HTTPException(status_code=404, detail="Allowance catalog entry not found")
        
        if not check_company_access(db, current_user, entry.company_id):
            raise HTTPException(status_code=403, detail="Access denied: You do not have access to this company")
        
        if data.allowance_name is not None:
            entry.allowance_name = data.allowance_name
        if data.allowance_description is not None:
            entry.allowance_description = data.allowance_description
        if data.is_taxable is not None:
            entry.is_taxable = data.is_taxable
        if data.is_percentage is not None:
            entry.is_percentage = data.is_percentage
        if data.default_value is not None:
            entry.default_value = data.default_value
        if data.max_limit is not None:
            entry.max_limit = data.max_limit
        if data.applicable_employment_types is not None:
            entry.applicable_employment_types = data.applicable_employment_types
        if data.display_order is not None:
            entry.display_order = data.display_order
        if data.is_active is not None:
            entry.is_active = data.is_active
        
        entry.updated_by_id = user_id
        entry.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(entry)
        
        logger.info(f"[DC-PAYROLL] Updated allowance catalog entry {entry_id} by user {user_id}")
        
        return {
            'success': True,
            'message': f"Updated allowance type '{entry.allowance_name}'",
            'data': entry.to_dict()
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"[DC-PAYROLL] Error updating allowance catalog: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/staff/payroll/allowance-catalog/{entry_id}", tags=["Staff Payroll Allowance Catalog"])
async def delete_allowance_catalog_entry(
    entry_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_staff_user)
):
    """Soft-delete an allowance catalog entry (DC Protocol enforced)"""
    try:
        user_id = get_user_attr(current_user, 'employee_id')
        
        if not check_menu_access(db, user_id, PAYROLL_PROFILE_MENU_CODE, require_edit=True):
            raise HTTPException(status_code=403, detail="Access denied")
        
        entry = db.query(StaffPayrollAllowanceCatalog).filter(
            StaffPayrollAllowanceCatalog.id == entry_id
        ).first()
        
        if not entry:
            raise HTTPException(status_code=404, detail="Allowance catalog entry not found")
        
        if not check_company_access(db, current_user, entry.company_id):
            raise HTTPException(status_code=403, detail="Access denied: You do not have access to this company")
        
        entry.is_active = False
        entry.updated_by_id = user_id
        entry.updated_at = datetime.utcnow()
        
        db.commit()
        
        logger.info(f"[DC-PAYROLL] Deleted allowance catalog entry {entry_id} by user {user_id}")
        
        return {
            'success': True,
            'message': f"Deleted allowance type '{entry.allowance_name}'"
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"[DC-PAYROLL] Error deleting allowance catalog: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


class ConsultantInvoiceCreate(BaseModel):
    employee_id: int
    company_id: int
    invoice_date: date
    service_period_from: date
    service_period_to: date
    service_description: Optional[str] = None
    invoice_amount: float = Field(..., gt=0)
    gst_applicable: bool = Field(False)
    gst_rate: float = Field(18.0, ge=0, le=100)
    tds_applicable: bool = Field(True)
    tds_section: str = Field('194J')
    tds_rate: float = Field(10.0, ge=0, le=100)
    source: str = Field('MANUAL')


class ConsultantInvoiceUpdate(BaseModel):
    service_description: Optional[str] = None
    invoice_amount: Optional[float] = Field(None, gt=0)
    gst_applicable: Optional[bool] = None
    gst_rate: Optional[float] = Field(None, ge=0, le=100)
    tds_applicable: Optional[bool] = None
    tds_rate: Optional[float] = Field(None, ge=0, le=100)


@router.get("/staff/payroll/consultant-invoices", tags=["Staff Payroll Consultant Invoices"])
async def list_consultant_invoices(
    company_id: Optional[int] = Query(None, description="Filter by company"),
    employee_id: Optional[int] = Query(None, description="Filter by employee"),
    status: Optional[str] = Query(None, description="Filter by status"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_staff_user)
):
    """List consultant invoices with DC Protocol filtering"""
    try:
        user_id = get_user_attr(current_user, 'employee_id')
        user_company_id = get_user_attr(current_user, 'company_id')
        
        if not check_menu_access(db, user_id, PAYROLL_CYCLE_MENU_CODE, require_edit=False):
            raise HTTPException(status_code=403, detail="Access denied")
        
        accessible_companies = get_user_accessible_companies(db, user_id, user_company_id)
        
        query = db.query(StaffConsultantInvoice).filter(
            StaffConsultantInvoice.company_id.in_(accessible_companies)
        )
        
        if company_id:
            if company_id not in accessible_companies:
                raise HTTPException(status_code=403, detail="Access denied: You do not have access to this company")
            query = query.filter(StaffConsultantInvoice.company_id == company_id)
        
        if employee_id:
            query = query.filter(StaffConsultantInvoice.employee_id == employee_id)
        
        if status:
            query = query.filter(StaffConsultantInvoice.status == status)
        
        total = query.count()
        
        invoices = query.order_by(
            desc(StaffConsultantInvoice.invoice_date)
        ).offset((page - 1) * limit).limit(limit).all()
        
        return {
            'success': True,
            'data': [inv.to_dict(include_employee=True) for inv in invoices],
            'pagination': {
                'total': total,
                'page': page,
                'limit': limit,
                'pages': (total + limit - 1) // limit if limit > 0 else 0
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[DC-PAYROLL] Error listing consultant invoices: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/staff/payroll/consultant-invoices", tags=["Staff Payroll Consultant Invoices"])
async def create_consultant_invoice(
    data: ConsultantInvoiceCreate = Body(...),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_staff_user)
):
    """Create a consultant invoice (DC Protocol enforced)"""
    try:
        user_id = get_user_attr(current_user, 'employee_id')
        
        if not check_menu_access(db, user_id, PAYROLL_CYCLE_MENU_CODE, require_edit=True):
            raise HTTPException(status_code=403, detail="Access denied")
        
        if not check_company_access(db, current_user, data.company_id):
            raise HTTPException(status_code=403, detail="Access denied: You do not have access to this company")
        
        employee = db.query(StaffEmployee).filter(StaffEmployee.id == data.employee_id).first()
        if not employee:
            raise HTTPException(status_code=404, detail="Employee not found")
        
        profile = db.query(StaffPayrollProfile).filter(
            StaffPayrollProfile.employee_id == data.employee_id,
            StaffPayrollProfile.company_id == data.company_id,
            StaffPayrollProfile.is_active == True
        ).first()
        
        if profile and profile.employment_type != 'OFFROLE':
            raise HTTPException(status_code=400, detail="Consultant invoices are only for OFFROLE employees")
        
        year = data.invoice_date.year
        prefix = f"CI-{data.company_id}-{year}-"
        existing_invoices = db.query(StaffConsultantInvoice.invoice_number).filter(
            StaffConsultantInvoice.company_id == data.company_id,
            StaffConsultantInvoice.invoice_number.like(f"{prefix}%")
        ).all()
        
        max_seq = 0
        for (inv_num,) in existing_invoices:
            if inv_num and inv_num.startswith(prefix):
                try:
                    seq_str = inv_num[len(prefix):]
                    seq = int(seq_str)
                    max_seq = max(max_seq, seq)
                except (ValueError, IndexError):
                    pass
        
        invoice_number = generate_consultant_invoice_number(data.company_id, year, max_seq + 1)
        
        gst_amount = round(data.invoice_amount * data.gst_rate / 100, 2) if data.gst_applicable else 0
        total_amount = round(data.invoice_amount + gst_amount, 2)
        tds_amount = round(data.invoice_amount * data.tds_rate / 100, 2) if data.tds_applicable else 0
        net_payable = round(total_amount - tds_amount, 2)
        
        invoice = StaffConsultantInvoice(
            invoice_number=invoice_number,
            employee_id=data.employee_id,
            company_id=data.company_id,
            invoice_date=data.invoice_date,
            service_period_from=data.service_period_from,
            service_period_to=data.service_period_to,
            service_description=data.service_description,
            invoice_amount=data.invoice_amount,
            gst_applicable=data.gst_applicable,
            gst_rate=data.gst_rate,
            gst_amount=gst_amount,
            tds_applicable=data.tds_applicable,
            tds_section=data.tds_section,
            tds_rate=data.tds_rate,
            tds_amount=tds_amount,
            total_amount=total_amount,
            net_payable=net_payable,
            source=data.source,
            status='DRAFT',
            created_by_id=user_id
        )
        
        db.add(invoice)
        db.commit()
        db.refresh(invoice)
        
        logger.info(f"[DC-PAYROLL] Created consultant invoice {invoice.id} by user {user_id}")
        
        return {
            'success': True,
            'message': f"Created invoice {invoice_number}",
            'data': invoice.to_dict()
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"[DC-PAYROLL] Error creating consultant invoice: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/staff/payroll/consultant-invoices/{invoice_id}", tags=["Staff Payroll Consultant Invoices"])
async def get_consultant_invoice(
    invoice_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_staff_user)
):
    """Get a consultant invoice (DC Protocol enforced)"""
    try:
        user_id = get_user_attr(current_user, 'employee_id')
        
        if not check_menu_access(db, user_id, PAYROLL_CYCLE_MENU_CODE, require_edit=False):
            raise HTTPException(status_code=403, detail="Access denied")
        
        invoice = db.query(StaffConsultantInvoice).filter(
            StaffConsultantInvoice.id == invoice_id
        ).first()
        
        if not invoice:
            raise HTTPException(status_code=404, detail="Invoice not found")
        
        if not check_company_access(db, current_user, invoice.company_id):
            raise HTTPException(status_code=403, detail="Access denied")
        
        return {
            'success': True,
            'data': invoice.to_dict(include_employee=True)
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[DC-PAYROLL] Error getting consultant invoice: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/staff/payroll/consultant-invoices/{invoice_id}", tags=["Staff Payroll Consultant Invoices"])
async def update_consultant_invoice(
    invoice_id: int,
    data: ConsultantInvoiceUpdate = Body(...),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_staff_user)
):
    """Update a consultant invoice (DC Protocol enforced, only DRAFT status)"""
    try:
        user_id = get_user_attr(current_user, 'employee_id')
        
        if not check_menu_access(db, user_id, PAYROLL_CYCLE_MENU_CODE, require_edit=True):
            raise HTTPException(status_code=403, detail="Access denied")
        
        invoice = db.query(StaffConsultantInvoice).filter(
            StaffConsultantInvoice.id == invoice_id
        ).first()
        
        if not invoice:
            raise HTTPException(status_code=404, detail="Invoice not found")
        
        if not check_company_access(db, current_user, invoice.company_id):
            raise HTTPException(status_code=403, detail="Access denied")
        
        if invoice.status != 'DRAFT':
            raise HTTPException(status_code=400, detail=f"Cannot update invoice in {invoice.status} status")
        
        if data.invoice_amount is not None:
            invoice.invoice_amount = data.invoice_amount
        if data.service_description is not None:
            invoice.service_description = data.service_description
        if data.gst_applicable is not None:
            invoice.gst_applicable = data.gst_applicable
        if data.gst_rate is not None:
            invoice.gst_rate = data.gst_rate
        if data.tds_applicable is not None:
            invoice.tds_applicable = data.tds_applicable
        if data.tds_rate is not None:
            invoice.tds_rate = data.tds_rate
        
        gst_amount = round(float(invoice.invoice_amount) * float(invoice.gst_rate) / 100, 2) if invoice.gst_applicable else 0
        total_amount = round(float(invoice.invoice_amount) + gst_amount, 2)
        tds_amount = round(float(invoice.invoice_amount) * float(invoice.tds_rate) / 100, 2) if invoice.tds_applicable else 0
        net_payable = round(total_amount - tds_amount, 2)
        
        invoice.gst_amount = gst_amount
        invoice.total_amount = total_amount
        invoice.tds_amount = tds_amount
        invoice.net_payable = net_payable
        invoice.updated_by_id = user_id
        invoice.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(invoice)
        
        return {
            'success': True,
            'message': "Invoice updated",
            'data': invoice.to_dict()
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"[DC-PAYROLL] Error updating consultant invoice: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/staff/payroll/consultant-invoices/{invoice_id}/submit", tags=["Staff Payroll Consultant Invoices"])
async def submit_consultant_invoice(
    invoice_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_staff_user)
):
    """Submit a consultant invoice for approval (DC Protocol enforced)"""
    try:
        user_id = get_user_attr(current_user, 'employee_id')
        
        if not check_menu_access(db, user_id, PAYROLL_CYCLE_MENU_CODE, require_edit=True):
            raise HTTPException(status_code=403, detail="Access denied")
        
        invoice = db.query(StaffConsultantInvoice).filter(
            StaffConsultantInvoice.id == invoice_id
        ).first()
        
        if not invoice:
            raise HTTPException(status_code=404, detail="Invoice not found")
        
        if not check_company_access(db, current_user, invoice.company_id):
            raise HTTPException(status_code=403, detail="Access denied")
        
        if invoice.status != 'DRAFT':
            raise HTTPException(status_code=400, detail=f"Cannot submit invoice in {invoice.status} status")
        
        invoice.status = 'SUBMITTED'
        invoice.submitted_at = datetime.utcnow()
        invoice.updated_by_id = user_id
        
        db.commit()
        
        return {
            'success': True,
            'message': f"Invoice {invoice.invoice_number} submitted for approval"
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"[DC-PAYROLL] Error submitting consultant invoice: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/staff/payroll/consultant-invoices/{invoice_id}/approve", tags=["Staff Payroll Consultant Invoices"])
async def approve_consultant_invoice(
    invoice_id: int,
    remarks: Optional[str] = Body(None, embed=True),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_staff_user)
):
    """Approve a consultant invoice (DC Protocol enforced, requires approvals menu access)"""
    try:
        user_id = get_user_attr(current_user, 'employee_id')
        
        if not check_menu_access(db, user_id, PAYROLL_APPROVALS_MENU_CODE, require_edit=True):
            raise HTTPException(status_code=403, detail="Access denied: You do not have approval permission")
        
        invoice = db.query(StaffConsultantInvoice).filter(
            StaffConsultantInvoice.id == invoice_id
        ).first()
        
        if not invoice:
            raise HTTPException(status_code=404, detail="Invoice not found")
        
        if not check_company_access(db, current_user, invoice.company_id):
            raise HTTPException(status_code=403, detail="Access denied")
        
        if invoice.status not in ['SUBMITTED', 'VALIDATED']:
            raise HTTPException(status_code=400, detail=f"Cannot approve invoice in {invoice.status} status")
        
        invoice.status = 'APPROVED'
        invoice.approved_by = user_id
        invoice.approved_at = datetime.utcnow()
        invoice.approval_remarks = remarks
        invoice.updated_by_id = user_id
        
        db.commit()
        
        return {
            'success': True,
            'message': f"Invoice {invoice.invoice_number} approved"
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"[DC-PAYROLL] Error approving consultant invoice: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


PAYROLL_DOCUMENTS_MENU_CODE = "payroll-documents"

@router.get("/staff/payroll/documents", tags=["Staff Payroll Documents"])
async def list_payroll_documents(
    company_id: Optional[int] = Query(None),
    employee_id: Optional[int] = Query(None),
    document_type: Optional[str] = Query(None),
    cycle_id: Optional[int] = Query(None),
    search: Optional[str] = Query(None, description="Search by employee name, code, or document code"),
    date_from: Optional[str] = Query(None, description="Filter by date from (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="Filter by date to (YYYY-MM-DD)"),
    month: Optional[int] = Query(None, ge=1, le=12, description="Filter by month"),
    year: Optional[int] = Query(None, ge=2020, le=2030, description="Filter by year"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_staff_user)
):
    """List payroll documents with DC Protocol enforcement and comprehensive filters"""
    try:
        user_id = get_user_attr(current_user, 'employee_id')
        base_company_id = get_user_attr(current_user, 'base_company_id')
        
        if not check_menu_access(db, user_id, PAYROLL_DOCUMENTS_MENU_CODE):
            raise HTTPException(status_code=403, detail="Access denied")
        
        accessible_companies = get_user_accessible_companies(db, user_id, base_company_id)
        
        query = db.query(StaffPayrollDocument).filter(
            StaffPayrollDocument.is_active == True
        )
        
        if company_id:
            if company_id not in accessible_companies:
                raise HTTPException(status_code=403, detail="Access denied to this company")
            query = query.filter(StaffPayrollDocument.company_id == company_id)
        else:
            query = query.filter(StaffPayrollDocument.company_id.in_(accessible_companies))
        
        if employee_id:
            query = query.filter(StaffPayrollDocument.employee_id == employee_id)
        
        if document_type:
            query = query.filter(StaffPayrollDocument.document_type == document_type)
        
        if cycle_id:
            query = query.filter(StaffPayrollDocument.cycle_id == cycle_id)
        
        if search:
            search_term = f"%{search}%"
            query = query.join(StaffEmployee, StaffPayrollDocument.employee_id == StaffEmployee.id).filter(
                or_(
                    StaffPayrollDocument.document_code.ilike(search_term),
                    StaffEmployee.full_name.ilike(search_term),
                    StaffEmployee.first_name.ilike(search_term),
                    StaffEmployee.last_name.ilike(search_term),
                    StaffEmployee.emp_code.ilike(search_term)
                )
            )
        
        if date_from:
            try:
                from_date = datetime.strptime(date_from, '%Y-%m-%d').date()
                query = query.filter(StaffPayrollDocument.document_date >= from_date)
            except ValueError:
                pass
        
        if date_to:
            try:
                to_date = datetime.strptime(date_to, '%Y-%m-%d').date()
                query = query.filter(StaffPayrollDocument.document_date <= to_date)
            except ValueError:
                pass
        
        if month or year:
            query = query.join(StaffPayrollCycle, StaffPayrollDocument.cycle_id == StaffPayrollCycle.id, isouter=True)
            if month:
                query = query.filter(StaffPayrollCycle.cycle_month == month)
            if year:
                query = query.filter(StaffPayrollCycle.cycle_year == year)
        
        total = query.count()
        documents = query.order_by(desc(StaffPayrollDocument.created_at)).offset(skip).limit(limit).all()
        
        result = []
        for doc in documents:
            doc_data = doc.to_dict()
            if doc.employee:
                doc_data['employee_name'] = doc.employee.full_name or f"{doc.employee.first_name} {doc.employee.last_name}"
                doc_data['employee_code'] = doc.employee.emp_code
                doc_data['department'] = doc.employee.department.name if doc.employee.department else None
                doc_data['designation'] = doc.employee.designation
            if doc.company:
                doc_data['company_name'] = doc.company.company_name
            result.append(doc_data)
        
        return {
            'success': True,
            'data': result,
            'total': total,
            'skip': skip,
            'limit': limit
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[DC-PAYROLL] Error listing documents: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/staff/payroll/runs/{run_id}/generate-payslip", tags=["Staff Payroll Documents"])
async def generate_payslip(
    run_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_staff_user)
):
    """Generate payslip PDF for a payroll run (DC Protocol enforced)"""
    try:
        user_id = get_user_attr(current_user, 'employee_id')
        
        if not check_menu_access(db, user_id, PAYROLL_CYCLE_MENU_CODE, require_edit=True):
            raise HTTPException(status_code=403, detail="Access denied")
        
        run = db.query(StaffPayrollRun).filter(StaffPayrollRun.id == run_id).first()
        if not run:
            raise HTTPException(status_code=404, detail="Payroll run not found")
        
        if not check_company_access(db, current_user, run.company_id):
            raise HTTPException(status_code=403, detail="Access denied to this company")
        
        if run.status not in ['APPROVED', 'PAID']:
            raise HTTPException(status_code=400, detail="Can only generate payslip for approved/paid runs")
        
        existing = db.query(StaffPayrollDocument).filter(
            StaffPayrollDocument.payroll_run_id == run_id,
            StaffPayrollDocument.document_type == 'PAYSLIP',
            StaffPayrollDocument.is_active == True
        ).first()
        
        if existing:
            return {
                'success': True,
                'message': 'Payslip already exists',
                'document': existing.to_dict()
            }
        
        cycle = db.query(StaffPayrollCycle).filter(StaffPayrollCycle.id == run.cycle_id).first()
        employee = db.query(StaffEmployee).filter(StaffEmployee.id == run.employee_id).first()
        
        month_name = calendar.month_name[cycle.month] if cycle else "Unknown"
        year = cycle.year if cycle else datetime.now().year
        
        doc_code = generate_payroll_document_code(db, run.company_id, 'PAYSLIP')
        file_name = f"payslip_{employee.emp_code}_{month_name}_{year}.pdf"
        file_path = f"payroll/payslips/{run.company_id}/{year}/{run.employee_id}/{file_name}"
        
        document = StaffPayrollDocument(
            document_code=doc_code,
            employee_id=run.employee_id,
            company_id=run.company_id,
            cycle_id=run.cycle_id,
            payroll_run_id=run_id,
            document_type='PAYSLIP',
            document_title=f"Payslip - {month_name} {year}",
            file_path=file_path,
            file_name=file_name,
            document_date=get_indian_date(),
            template_data={
                'employee_name': employee.full_name if employee else 'N/A',
                'employee_code': employee.emp_code if employee else 'N/A',
                'month': month_name,
                'year': year,
                'basic_pay': float(run.basic_pay) if run.basic_pay else 0,
                'hra': float(run.hra) if run.hra else 0,
                'special_allowance': float(run.special_allowance) if run.special_allowance else 0,
                'other_allowances': run.other_components if run.other_components else {},
                'gross_earnings': float(run.gross_earnings) if run.gross_earnings else 0,
                'pf_deduction': float(run.pf_employee) if run.pf_employee else 0,
                'esi_deduction': float(run.esi_employee) if run.esi_employee else 0,
                'pt_deduction': float(run.professional_tax) if run.professional_tax else 0,
                'tds_deduction': float(run.tds_deduction) if run.tds_deduction else 0,
                'total_deductions': float(run.total_deductions) if run.total_deductions else 0,
                'net_pay': float(run.net_pay) if run.net_pay else 0,
                'days_in_month': int(run.eligible_days) if run.eligible_days else 0,
                'days_worked': int(run.present_days) if run.present_days else 0,
                'lop_days': int(run.lop_days) if run.lop_days else 0
            },
            generated_by=user_id,
            is_active=True
        )
        
        db.add(document)
        
        run.payslip_generated = True
        run.payslip_path = file_path
        
        db.commit()
        db.refresh(document)
        
        logger.info(f"[DC-PAYROLL] Generated payslip {doc_code} for run {run_id}")
        
        return {
            'success': True,
            'message': f"Payslip generated successfully",
            'document': document.to_dict()
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"[DC-PAYROLL] Error generating payslip: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/staff/payroll/profiles/{profile_id}/generate-offer-letter", tags=["Staff Payroll Documents"])
async def generate_offer_letter(
    profile_id: int,
    joining_date: date = Body(...),
    offer_date: Optional[date] = Body(None),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_staff_user)
):
    """Generate offer letter PDF for a payroll profile (DC Protocol enforced)"""
    try:
        user_id = get_user_attr(current_user, 'employee_id')
        
        if not check_menu_access(db, user_id, PAYROLL_PROFILE_MENU_CODE, require_edit=True):
            raise HTTPException(status_code=403, detail="Access denied")
        
        profile = db.query(StaffPayrollProfile).filter(StaffPayrollProfile.id == profile_id).first()
        if not profile:
            raise HTTPException(status_code=404, detail="Payroll profile not found")
        
        if not check_company_access(db, current_user, profile.company_id):
            raise HTTPException(status_code=403, detail="Access denied to this company")
        
        employee = db.query(StaffEmployee).filter(StaffEmployee.id == profile.employee_id).first()
        company = db.query(AssociatedCompany).filter(AssociatedCompany.id == profile.company_id).first()
        
        doc_code = generate_payroll_document_code(db, profile.company_id, 'OFFER_LETTER')
        file_name = f"offer_letter_{employee.emp_code}_{joining_date.strftime('%Y%m%d')}.pdf"
        file_path = f"payroll/offer_letters/{profile.company_id}/{employee.emp_code}/{file_name}"
        
        actual_offer_date = offer_date or get_indian_date()
        
        document = StaffPayrollDocument(
            document_code=doc_code,
            employee_id=profile.employee_id,
            company_id=profile.company_id,
            document_type='OFFER_LETTER',
            document_title=f"Offer Letter - {employee.full_name if employee else 'N/A'}",
            file_path=file_path,
            file_name=file_name,
            document_date=actual_offer_date,
            template_data={
                'employee_name': employee.full_name if employee else 'N/A',
                'employee_code': employee.emp_code if employee else 'N/A',
                'company_name': company.company_name if company else 'N/A',
                'designation': employee.designation if employee else 'N/A',
                'department': employee.department.name if employee and employee.department else 'N/A',
                'joining_date': joining_date.isoformat(),
                'offer_date': actual_offer_date.isoformat(),
                'employment_type': profile.employment_type,
                'ctc': float(profile.ctc) if profile.ctc else 0,
                'basic_pay': float(profile.basic_pay) if profile.basic_pay else 0,
                'hra': float(profile.hra) if profile.hra else 0,
                'special_allowance': float(profile.special_allowance) if profile.special_allowance else 0,
                'pf_applicable': profile.pf_applicable,
                'esi_applicable': profile.esi_applicable
            },
            generated_by=user_id,
            is_active=True
        )
        
        db.add(document)
        db.commit()
        db.refresh(document)
        
        logger.info(f"[DC-PAYROLL] Generated offer letter {doc_code} for profile {profile_id}")
        
        return {
            'success': True,
            'message': f"Offer letter generated successfully",
            'document': document.to_dict()
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"[DC-PAYROLL] Error generating offer letter: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/staff/payroll/documents/{document_id}", tags=["Staff Payroll Documents"])
async def get_payroll_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_staff_user)
):
    """Get payroll document details with enriched data (DC Protocol enforced)"""
    from app.utils.amount_to_words import amount_to_words_indian, format_indian_currency
    
    try:
        user_id = get_user_attr(current_user, 'employee_id')
        
        if not check_menu_access(db, user_id, PAYROLL_DOCUMENTS_MENU_CODE):
            raise HTTPException(status_code=403, detail="Access denied")
        
        document = db.query(StaffPayrollDocument).filter(
            StaffPayrollDocument.id == document_id,
            StaffPayrollDocument.is_active == True
        ).first()
        
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        if not check_company_access(db, current_user, document.company_id):
            raise HTTPException(status_code=403, detail="Access denied to this company")
        
        doc_data = document.to_dict()
        
        company = document.company
        if company:
            doc_data['company'] = {
                'id': company.id,
                'name': company.company_name,
                'code': company.company_code,
                'logo_url': f"/api/v1/uploads/company-logos/{company.logo_path}" if company.logo_path else None,
                'address': company.address,
                'city': company.city,
                'state': company.state,
                'pincode': company.pincode,
                'gst_number': company.gst_number,
                'pan_number': company.pan_number
            }
        
        employee = document.employee
        if employee:
            doc_data['employee_name'] = employee.full_name or f"{employee.first_name} {employee.last_name}"
            doc_data['employee_code'] = employee.emp_code
            
            kyc = None
            if employee.kyc_records:
                kyc = next((k for k in employee.kyc_records if k.status == 'approved'), None)
                if not kyc:
                    kyc = employee.kyc_records[0] if employee.kyc_records else None
            
            payroll_profile = db.query(StaffPayrollProfile).filter(
                StaffPayrollProfile.employee_id == employee.id,
                StaffPayrollProfile.is_active == True
            ).first()
            
            pan_number = kyc.pan_number if kyc else (payroll_profile.pan_number if payroll_profile else None)
            bank_name = kyc.bank_name if kyc else None
            account_number = kyc.account_number if kyc else None
            uan_number = payroll_profile.uan_number if payroll_profile else None
            
            doc_data['employee'] = {
                'id': employee.id,
                'name': employee.full_name or f"{employee.first_name} {employee.last_name}",
                'code': employee.emp_code,
                'department': employee.department.name if employee.department else None,
                'designation': employee.designation,
                'pan_number': pan_number,
                'bank_name': bank_name,
                'account_number': account_number[-4:] if account_number else None,
                'uan_number': uan_number,
                'esi_number': None
            }
        
        if document.document_type == 'PAYSLIP' and document.payroll_run_id:
            run = db.query(StaffPayrollRun).filter(
                StaffPayrollRun.id == document.payroll_run_id
            ).first()
            
            if run:
                cycle = run.cycle
                net_pay = float(run.net_salary or 0)
                
                doc_data['payroll'] = {
                    'period': {
                        'start_date': cycle.period_start.isoformat() if cycle and cycle.period_start else None,
                        'end_date': cycle.period_end.isoformat() if cycle and cycle.period_end else None,
                        'pay_date': (cycle.paid_at.isoformat() if cycle.paid_at else (cycle.period_end.isoformat() if cycle.period_end else None)) if cycle else None,
                        'month': cycle.cycle_month if cycle else None,
                        'year': cycle.cycle_year if cycle else None,
                        'cycle_code': cycle.cycle_code if cycle else None
                    },
                    'attendance': {
                        'eligible_days': float(run.eligible_days or 0),
                        'present_days': float(run.present_days or 0),
                        'lop_days': float(run.lop_days or 0),
                        'leave_days': float(run.leave_days or 0),
                        'paid_days': float(run.present_days or 0) + float(run.leave_days or 0)
                    },
                    'earnings': {
                        'basic': float(run.basic_amount or 0),
                        'hra': float(run.hra_amount or 0),
                        'special_allowance': float(run.special_allowance or 0),
                        'other_earnings': run.other_earnings or {},
                        'gross': float(run.total_earnings or run.gross_salary or 0)
                    },
                    'deductions': {
                        'pf': float(run.pf_employee or 0),
                        'esi': float(run.esi_employee or 0),
                        'pt': float(run.pt_amount or 0),
                        'tds': float(run.tds_amount or 0),
                        'other_deductions': run.other_deductions or {},
                        'total': float(run.total_deductions or 0)
                    },
                    'employer_contributions': {
                        'pf': float(run.pf_employer or 0),
                        'esi': float(run.esi_employer or 0),
                        'total': float(run.employer_contributions or 0)
                    },
                    'summary': {
                        'gross_pay': float(run.total_earnings or run.gross_salary or 0),
                        'total_deductions': float(run.total_deductions or 0),
                        'net_pay': net_pay,
                        'net_pay_formatted': format_indian_currency(net_pay),
                        'net_pay_words': amount_to_words_indian(net_pay),
                        'ctc_monthly': float(run.ctc_monthly or 0),
                        'ctc_cost': float(run.ctc_cost or 0)
                    }
                }
        
        return {
            'success': True,
            'data': doc_data
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[DC-PAYROLL] Error getting document: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/staff/payroll/documents/{document_id}/download", tags=["Staff Payroll Documents"])
async def record_document_download(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_staff_user)
):
    """Record document download and return file path (DC Protocol enforced)"""
    try:
        user_id = get_user_attr(current_user, 'employee_id')
        
        if not check_menu_access(db, user_id, PAYROLL_DOCUMENTS_MENU_CODE):
            raise HTTPException(status_code=403, detail="Access denied")
        
        document = db.query(StaffPayrollDocument).filter(
            StaffPayrollDocument.id == document_id,
            StaffPayrollDocument.is_active == True
        ).first()
        
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        if not check_company_access(db, current_user, document.company_id):
            raise HTTPException(status_code=403, detail="Access denied to this company")
        
        document.download_count += 1
        document.last_downloaded_at = get_indian_datetime()
        document.last_downloaded_by = user_id
        
        db.commit()
        
        return {
            'success': True,
            'file_path': document.file_path,
            'file_name': document.file_name,
            'download_count': document.download_count
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"[DC-PAYROLL] Error recording download: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/staff/payroll/runs/{run_id}/approve", tags=["Staff Payroll Approvals"])
async def approve_payroll_run(
    run_id: int,
    action: str = Body(..., embed=True),
    remarks: Optional[str] = Body(None, embed=True),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_staff_user)
):
    """
    Multi-level approval workflow for payroll runs
    Workflow: PENDING → LEVEL1_APPROVED (VGK_SUPREME) → LEVEL2_APPROVED (Director) → APPROVED (HR/Accounts)
    DC Protocol enforced
    """
    try:
        user_id = get_user_attr(current_user, 'employee_id')
        user_role = get_user_attr(current_user, 'staff_type', '')
        
        if not check_menu_access(db, user_id, PAYROLL_APPROVALS_MENU_CODE, require_edit=True):
            raise HTTPException(status_code=403, detail="Access denied: You do not have approval permission")
        
        run = db.query(StaffPayrollRun).filter(StaffPayrollRun.id == run_id).first()
        if not run:
            raise HTTPException(status_code=404, detail="Payroll run not found")
        
        if not check_company_access(db, current_user, run.company_id):
            raise HTTPException(status_code=403, detail="Access denied to this company")
        
        if action not in ['approve', 'reject']:
            raise HTTPException(status_code=400, detail="Invalid action. Use 'approve' or 'reject'")
        
        if action == 'reject':
            run.status = 'REJECTED'
            run.approved_by = user_id
            run.approved_at = get_indian_datetime()
            run.approval_remarks = remarks or "Rejected"
            
            audit = StaffPayrollAuditLog(
                company_id=run.company_id,
                entity_type='PAYROLL_RUN',
                entity_id=run_id,
                action='REJECTED',
                action_details={'remarks': remarks, 'approver_role': user_role},
                performed_by=user_id
            )
            db.add(audit)
            db.commit()
            
            return {
                'success': True,
                'message': f"Payroll run rejected"
            }
        
        current_status = run.status
        new_status = None
        
        if current_status == 'PENDING':
            new_status = 'APPROVED'
            run.approved_by = user_id
            run.approved_at = get_indian_datetime()
            run.approval_remarks = remarks
        elif current_status == 'APPROVED':
            raise HTTPException(status_code=400, detail="Payroll run already approved")
        else:
            raise HTTPException(status_code=400, detail=f"Cannot approve run in {current_status} status")
        
        run.status = new_status
        
        audit = StaffPayrollAuditLog(
            company_id=run.company_id,
            entity_type='PAYROLL_RUN',
            entity_id=run_id,
            action='APPROVED',
            action_details={
                'previous_status': current_status,
                'new_status': new_status,
                'approver_role': user_role,
                'remarks': remarks
            },
            performed_by=user_id
        )
        db.add(audit)
        db.commit()
        
        return {
            'success': True,
            'message': f"Payroll run approved successfully",
            'new_status': new_status
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"[DC-PAYROLL] Error in payroll approval: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/staff/payroll/runs/{run_id}/post-to-sfms", tags=["Staff Payroll SFMS Integration"])
async def post_payroll_run_to_sfms(
    run_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_staff_user)
):
    """
    Post approved payroll run to SFMS ledger with proper Indian double-entry accounting.
    
    Creates:
    1. ExpenseEntry for salary expense (CTC Cost = Gross + Employer Contributions)
    2. PartyLedger entries for all payables:
       - Salary Payable (Net Pay to employee)
       - PF Payable - Employee/Employer shares
       - ESI Payable - Employee/Employer shares
       - Professional Tax Payable
       - TDS Payable (Section 192)
    
    DC Protocol enforced - company_id segregation throughout.
    """
    try:
        from app.services.payroll_accounting_service import PayrollAccountingService
        
        user_id = get_user_attr(current_user, 'employee_id')
        
        if not check_menu_access(db, user_id, PAYROLL_APPROVALS_MENU_CODE, require_edit=True):
            raise HTTPException(status_code=403, detail="Access denied")
        
        run = db.query(StaffPayrollRun).filter(StaffPayrollRun.id == run_id).first()
        if not run:
            raise HTTPException(status_code=404, detail="Payroll run not found")
        
        if not check_company_access(db, current_user, run.company_id):
            raise HTTPException(status_code=403, detail="Access denied to this company")
        
        if run.status != 'APPROVED':
            raise HTTPException(status_code=400, detail="Can only post approved payroll runs to SFMS")
        
        if run.sfms_posted:
            return {
                'success': True,
                'message': 'Already posted to SFMS',
                'sfms_reference': run.sfms_reference
            }
        
        accounting_service = PayrollAccountingService(db)
        result = accounting_service.post_payroll_run_to_sfms(run, user_id)
        
        if not result.get('success'):
            raise HTTPException(status_code=400, detail=result.get('error', 'Failed to post to SFMS'))
        
        db.commit()
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"[DC-PAYROLL] Error posting to SFMS: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/staff/payroll/cycles/{cycle_id}/batch-approve", tags=["Staff Payroll Approvals"])
async def batch_approve_payroll_runs(
    cycle_id: int,
    action: str = Body(..., embed=True),
    remarks: Optional[str] = Body(None, embed=True),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_staff_user)
):
    """Batch approve all pending payroll runs in a cycle (DC Protocol enforced)"""
    try:
        user_id = get_user_attr(current_user, 'employee_id')
        user_role = get_user_attr(current_user, 'staff_type', '')
        
        if not check_menu_access(db, user_id, PAYROLL_APPROVALS_MENU_CODE, require_edit=True):
            raise HTTPException(status_code=403, detail="Access denied")
        
        cycle = db.query(StaffPayrollCycle).filter(StaffPayrollCycle.id == cycle_id).first()
        if not cycle:
            raise HTTPException(status_code=404, detail="Payroll cycle not found")
        
        if not check_company_access(db, current_user, cycle.company_id):
            raise HTTPException(status_code=403, detail="Access denied to this company")
        
        if action not in ['approve', 'reject']:
            raise HTTPException(status_code=400, detail="Invalid action")
        
        pending_runs = db.query(StaffPayrollRun).filter(
            StaffPayrollRun.cycle_id == cycle_id,
            StaffPayrollRun.status == 'PENDING'
        ).all()
        
        if not pending_runs:
            return {
                'success': True,
                'message': 'No pending runs to process',
                'processed': 0
            }
        
        new_status = 'APPROVED' if action == 'approve' else 'REJECTED'
        processed = 0
        
        for run in pending_runs:
            run.status = new_status
            run.approved_by = user_id
            run.approved_at = get_indian_datetime()
            run.approval_remarks = remarks
            
            audit = StaffPayrollAuditLog(
                company_id=run.company_id,
                entity_type='PAYROLL_RUN',
                entity_id=run.id,
                action=new_status,
                action_details={
                    'batch_operation': True,
                    'cycle_id': cycle_id,
                    'approver_role': user_role
                },
                performed_by=user_id
            )
            db.add(audit)
            processed += 1
        
        db.commit()
        
        return {
            'success': True,
            'message': f"Batch {action} completed for {processed} runs",
            'processed': processed
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"[DC-PAYROLL] Error in batch approval: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/staff/payroll/cycles/{cycle_id}/batch-post-sfms", tags=["Staff Payroll SFMS Integration"])
async def batch_post_payroll_to_sfms(
    cycle_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_staff_user)
):
    """
    Batch post all approved runs in a cycle to SFMS with proper Indian double-entry accounting.
    
    For each run, creates:
    1. ExpenseEntry for salary expense (CTC Cost)
    2. PartyLedger entries for all payables (Salary, PF, ESI, PT, TDS)
    
    DC Protocol enforced - company_id segregation throughout.
    """
    try:
        from app.services.payroll_accounting_service import PayrollAccountingService
        
        user_id = get_user_attr(current_user, 'employee_id')
        
        if not check_menu_access(db, user_id, PAYROLL_APPROVALS_MENU_CODE, require_edit=True):
            raise HTTPException(status_code=403, detail="Access denied")
        
        cycle = db.query(StaffPayrollCycle).filter(StaffPayrollCycle.id == cycle_id).first()
        if not cycle:
            raise HTTPException(status_code=404, detail="Payroll cycle not found")
        
        if not check_company_access(db, current_user, cycle.company_id):
            raise HTTPException(status_code=403, detail="Access denied to this company")
        
        accounting_service = PayrollAccountingService(db)
        result = accounting_service.batch_post_payroll_cycle_to_sfms(cycle, user_id)
        
        db.commit()
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"[DC-PAYROLL] Error in batch SFMS posting: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/staff/payroll/documents/{document_id}/pdf", tags=["Staff Payroll Documents"])
async def download_document_pdf(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_staff_user)
):
    """
    Download document as professional PDF file using ReportLab
    Includes company branding, employee details, attendance, amounts in words
    DC Protocol enforced, updates download counter
    """
    from fastapi.responses import StreamingResponse
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib import colors
    from reportlab.lib.units import inch
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    from app.utils.amount_to_words import amount_to_words_indian, format_indian_currency
    import io
    import os
    
    try:
        user_id = get_user_attr(current_user, 'employee_id')
        
        if not check_menu_access(db, user_id, PAYROLL_DOCUMENTS_MENU_CODE):
            raise HTTPException(status_code=403, detail="Access denied")
        
        document = db.query(StaffPayrollDocument).filter(
            StaffPayrollDocument.id == document_id,
            StaffPayrollDocument.is_active == True
        ).first()
        
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        if not check_company_access(db, current_user, document.company_id):
            raise HTTPException(status_code=403, detail="Access denied to this company")
        
        template_data = document.template_data or {}
        company = document.company
        employee = document.employee
        
        run = None
        cycle = None
        if document.payroll_run_id:
            run = db.query(StaffPayrollRun).filter(StaffPayrollRun.id == document.payroll_run_id).first()
            if run:
                cycle = run.cycle
        
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
        
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle('Title', parent=styles['Heading1'], fontSize=16, alignment=TA_CENTER, spaceAfter=5, textColor=colors.HexColor('#667eea'))
        company_style = ParagraphStyle('Company', parent=styles['Heading1'], fontSize=14, alignment=TA_CENTER, spaceAfter=3, fontName='Helvetica-Bold')
        subtitle_style = ParagraphStyle('Subtitle', parent=styles['Normal'], fontSize=10, alignment=TA_CENTER, spaceAfter=10, textColor=colors.grey)
        heading_style = ParagraphStyle('Heading', parent=styles['Heading2'], fontSize=11, spaceAfter=5, fontName='Helvetica-Bold', textColor=colors.HexColor('#333333'))
        normal_style = styles['Normal']
        small_style = ParagraphStyle('Small', parent=styles['Normal'], fontSize=8, textColor=colors.grey)
        disclaimer_style = ParagraphStyle('Disclaimer', parent=styles['Normal'], fontSize=8, alignment=TA_CENTER, textColor=colors.grey, spaceBefore=20)
        net_pay_words_style = ParagraphStyle('NetPayWords', parent=styles['Normal'], fontSize=9, alignment=TA_CENTER, textColor=colors.HexColor('#333333'))
        
        elements = []
        
        if document.document_type == 'PAYSLIP':
            company_name = company.company_name if company else template_data.get('company_name', 'Company')
            company_addr_parts = []
            if company:
                if company.address:
                    company_addr_parts.append(company.address)
                if company.city:
                    company_addr_parts.append(company.city)
                if company.state:
                    company_addr_parts.append(company.state)
                if company.pincode:
                    company_addr_parts.append(company.pincode)
            company_address = ', '.join(company_addr_parts)
            
            elements.append(Paragraph(company_name, company_style))
            if company_address:
                elements.append(Paragraph(company_address, subtitle_style))
            if company and company.gst_number:
                elements.append(Paragraph(f"GSTIN: {company.gst_number}", small_style))
            elements.append(Spacer(1, 10))
            
            month_num = cycle.cycle_month if cycle else template_data.get('month_num', '')
            year = cycle.cycle_year if cycle else template_data.get('year', '')
            months = ['', 'January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']
            month_name = months[month_num] if month_num and 1 <= month_num <= 12 else template_data.get('month', '')
            
            elements.append(Paragraph(f"PAYSLIP - {month_name} {year}", title_style))
            elements.append(Spacer(1, 15))
            
            emp_name = employee.full_name or f"{employee.first_name} {employee.last_name}" if employee else template_data.get('employee_name', 'N/A')
            emp_code = employee.emp_code if employee else template_data.get('employee_code', 'N/A')
            emp_dept = (employee.department.name if employee.department else 'N/A') if employee else template_data.get('department', 'N/A')
            emp_desg = employee.designation if employee else template_data.get('designation', 'N/A')
            
            emp_pan = None
            emp_uan = None
            if employee:
                kyc = None
                if employee.kyc_records:
                    kyc = next((k for k in employee.kyc_records if k.status == 'approved'), None)
                    if not kyc:
                        kyc = employee.kyc_records[0] if employee.kyc_records else None
                
                payroll_profile = db.query(StaffPayrollProfile).filter(
                    StaffPayrollProfile.employee_id == employee.id,
                    StaffPayrollProfile.is_active == True
                ).first()
                
                emp_pan = kyc.pan_number if kyc else (payroll_profile.pan_number if payroll_profile else None)
                emp_uan = payroll_profile.uan_number if payroll_profile else None
            
            eligible_days = float(run.eligible_days) if run else template_data.get('days_in_month', 0)
            present_days = float(run.present_days) if run else template_data.get('days_worked', 0)
            lop_days = float(run.lop_days) if run else 0
            leave_days = float(run.leave_days) if run else 0
            paid_days = present_days + leave_days
            
            period_start = cycle.period_start.strftime('%d-%b-%Y') if cycle and cycle.period_start else 'N/A'
            period_end = cycle.period_end.strftime('%d-%b-%Y') if cycle and cycle.period_end else 'N/A'
            pay_date = (cycle.paid_at.strftime('%d-%b-%Y') if cycle.paid_at else (cycle.period_end.strftime('%d-%b-%Y') if cycle.period_end else 'N/A')) if cycle else 'N/A'
            
            emp_attendance_data = [
                ['EMPLOYEE DETAILS', '', 'ATTENDANCE & PERIOD', ''],
                ['Name', emp_name, 'Pay Period', f"{period_start} to {period_end}"],
                ['Employee Code', emp_code, 'Pay Date', pay_date],
                ['Department', emp_dept, 'Days in Month', str(int(eligible_days))],
                ['Designation', emp_desg, 'Days Present', str(int(present_days))],
            ]
            if emp_pan:
                emp_attendance_data.append(['PAN Number', emp_pan, 'Leave Days', str(int(leave_days))])
            if emp_uan:
                emp_attendance_data.append(['UAN Number', emp_uan, 'LOP Days', str(int(lop_days))])
            emp_attendance_data.append(['', '', 'Paid Days', f"{int(paid_days)}"])
            
            emp_att_table = Table(emp_attendance_data, colWidths=[1.3*inch, 1.8*inch, 1.3*inch, 1.6*inch])
            emp_att_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (1, 0), colors.HexColor('#667eea')),
                ('BACKGROUND', (2, 0), (3, 0), colors.HexColor('#28a745')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('SPAN', (0, 0), (1, 0)),
                ('SPAN', (2, 0), (3, 0)),
                ('BACKGROUND', (0, 1), (0, -1), colors.HexColor('#f8f9fa')),
                ('BACKGROUND', (2, 1), (2, -1), colors.HexColor('#f8f9fa')),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#dee2e6')),
                ('PADDING', (0, 0), (-1, -1), 6),
                ('FONTSIZE', (0, 1), (-1, -1), 9),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]))
            elements.append(emp_att_table)
            elements.append(Spacer(1, 15))
            
            basic = float(run.basic_amount) if run else template_data.get('basic_pay', 0)
            hra = float(run.hra_amount) if run else template_data.get('hra', 0)
            special = float(run.special_allowance) if run else template_data.get('special_allowance', 0)
            gross = float(run.total_earnings or run.gross_salary) if run else template_data.get('gross_earnings', 0)
            
            pf = float(run.pf_employee) if run else template_data.get('pf_deduction', 0)
            esi = float(run.esi_employee) if run else template_data.get('esi_deduction', 0)
            pt = float(run.pt_amount) if run else template_data.get('pt_deduction', 0)
            tds = float(run.tds_amount) if run else template_data.get('tds_deduction', 0)
            total_ded = float(run.total_deductions) if run else template_data.get('total_deductions', 0)
            net_pay = float(run.net_salary) if run else template_data.get('net_pay', 0)
            
            salary_data = [
                ['EARNINGS', 'Amount (Rs.)', 'DEDUCTIONS', 'Amount (Rs.)'],
                ['Basic Pay', format_indian_currency(basic), 'Provident Fund (PF)', format_indian_currency(pf)],
                ['House Rent Allowance', format_indian_currency(hra), 'Employee State Insurance', format_indian_currency(esi)],
                ['Special Allowance', format_indian_currency(special), 'Professional Tax', format_indian_currency(pt)],
                ['', '', 'Tax Deducted at Source', format_indian_currency(tds)],
                ['Gross Earnings', format_indian_currency(gross), 'Total Deductions', format_indian_currency(total_ded)],
            ]
            
            salary_table = Table(salary_data, colWidths=[1.7*inch, 1.3*inch, 1.7*inch, 1.3*inch])
            salary_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (1, 0), colors.HexColor('#28a745')),
                ('BACKGROUND', (2, 0), (3, 0), colors.HexColor('#dc3545')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BACKGROUND', (0, -1), (1, -1), colors.HexColor('#d4edda')),
                ('BACKGROUND', (2, -1), (3, -1), colors.HexColor('#f8d7da')),
                ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#dee2e6')),
                ('PADDING', (0, 0), (-1, -1), 6),
                ('FONTSIZE', (0, 1), (-1, -1), 9),
                ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
                ('ALIGN', (3, 0), (3, -1), 'RIGHT'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]))
            elements.append(salary_table)
            elements.append(Spacer(1, 20))
            
            net_pay_table_data = [['NET PAY', f"Rs. {format_indian_currency(net_pay)}"]]
            net_pay_table = Table(net_pay_table_data, colWidths=[3*inch, 3*inch])
            net_pay_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#667eea')),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.white),
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 14),
                ('ALIGN', (0, 0), (0, 0), 'LEFT'),
                ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
                ('PADDING', (0, 0), (-1, -1), 12),
            ]))
            elements.append(net_pay_table)
            
            net_pay_words = amount_to_words_indian(net_pay)
            elements.append(Spacer(1, 5))
            elements.append(Paragraph(f"({net_pay_words})", net_pay_words_style))
            
            kyc_bank_name = None
            kyc_account_number = None
            if employee and employee.kyc_records:
                emp_kyc = next((k for k in employee.kyc_records if k.status == 'approved'), None)
                if not emp_kyc:
                    emp_kyc = employee.kyc_records[0] if employee.kyc_records else None
                if emp_kyc:
                    kyc_bank_name = emp_kyc.bank_name
                    kyc_account_number = emp_kyc.account_number
            
            if kyc_bank_name:
                elements.append(Spacer(1, 15))
                bank_info = f"Payment credited to: {kyc_bank_name}"
                if kyc_account_number:
                    bank_info += f" (A/c ending {kyc_account_number[-4:]})"
                elements.append(Paragraph(bank_info, small_style))
            
        elif document.document_type == 'OFFER_LETTER':
            elements.append(Paragraph(template_data.get('company_name', 'Company'), company_style))
            elements.append(Paragraph("OFFER LETTER", title_style))
            elements.append(Spacer(1, 20))
            
            elements.append(Paragraph(f"Date: {template_data.get('offer_date', 'N/A')}", normal_style))
            elements.append(Spacer(1, 20))
            
            elements.append(Paragraph(f"Dear {template_data.get('employee_name', 'Candidate')},", normal_style))
            elements.append(Spacer(1, 10))
            elements.append(Paragraph(f"We are pleased to offer you the position of <b>{template_data.get('designation', 'Employee')}</b> in the <b>{template_data.get('department', 'Department')}</b> department.", normal_style))
            elements.append(Spacer(1, 20))
            
            elements.append(Paragraph("Employment Details", heading_style))
            emp_details = [
                ['Position', template_data.get('designation', 'N/A')],
                ['Department', template_data.get('department', 'N/A')],
                ['Employment Type', template_data.get('employment_type', 'N/A')],
                ['Joining Date', template_data.get('joining_date', 'N/A')]
            ]
            emp_det_table = Table(emp_details, colWidths=[2.5*inch, 2.5*inch])
            emp_det_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('PADDING', (0, 0), (-1, -1), 8),
            ]))
            elements.append(emp_det_table)
            elements.append(Spacer(1, 20))
            
            elements.append(Paragraph("Compensation", heading_style))
            comp_data = [
                ['Annual CTC', f"Rs. {template_data.get('ctc', 0):,.2f}"],
                ['Basic Pay (Monthly)', f"Rs. {template_data.get('basic_pay', 0):,.2f}"],
                ['HRA (Monthly)', f"Rs. {template_data.get('hra', 0):,.2f}"],
                ['Special Allowance (Monthly)', f"Rs. {template_data.get('special_allowance', 0):,.2f}"]
            ]
            comp_table = Table(comp_data, colWidths=[2.5*inch, 2.5*inch])
            comp_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('PADDING', (0, 0), (-1, -1), 8),
                ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ]))
            elements.append(comp_table)
            
        elements.append(Spacer(1, 25))
        elements.append(Paragraph("This is a computer-generated document and does not require a signature.", disclaimer_style))
        elements.append(Paragraph(f"Document Code: {document.document_code} | Generated: {document.generated_at.strftime('%d-%b-%Y %H:%M') if document.generated_at else 'N/A'}", disclaimer_style))
        
        doc.build(elements)
        
        document.download_count += 1
        document.last_downloaded_at = get_indian_datetime()
        document.last_downloaded_by = user_id
        db.commit()
        
        buffer.seek(0)
        
        return StreamingResponse(
            buffer,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename={document.file_name}"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[DC-PAYROLL] Error generating PDF: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
