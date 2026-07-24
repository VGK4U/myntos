"""
Staff Employee Management API Endpoints (DC Protocol Compliant)
CRUD operations with RBAC
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request, Query, UploadFile, File, Form, Body
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import or_
from datetime import datetime, date
from typing import Optional, List
import pytz
from pydantic import BaseModel, EmailStr, Field, field_validator
from pathlib import Path
import shutil
import os
import uuid
import json

from app.core.database import get_db
from app.core.security import SecurityManager
from app.models.staff import (
    StaffEmployee, StaffRole, StaffDepartment, StaffSetting,
    StaffAuditLog, log_staff_audit, generate_employee_code, StaffEmployeeKyc,
    StaffEmployeeStatusHistory, log_staff_status_change,
    StaffModuleMaster, StaffEmployeeModule, log_employee_module_change,
    StaffEmployeeDepartment  # DC Protocol (Dec 21, 2025): Multi-department support
)
from app.models.staff_accounts import AssociatedCompany
from app.api.v1.endpoints.staff_auth import get_current_staff_user

# ============= DOCUMENT UPLOAD CONSTANTS (MNR Standard) =============
STAFF_KYC_UPLOAD_DIR = Path("uploaded_files/staff_kyc")
STAFF_KYC_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# File size limits (matching MNR user profile)
PROFILE_PHOTO_MAX_SIZE = 500 * 1024  # 500 KB
KYC_DOCUMENT_MAX_SIZE = 1024 * 1024  # 1 MB

# Allowed formats
IMAGE_FORMATS = {'jpg', 'jpeg', 'png'}
DOCUMENT_FORMATS = {'jpg', 'jpeg', 'png', 'pdf'}

# Valid document types for staff KYC
VALID_DOCUMENT_TYPES = [
    'profile_photo',
    'aadhaar_front',
    'aadhaar_back',
    'pan_card',
    'passport_photo',
    'driving_license',
    'voter_id',
    'bank_passbook',
    'cancelled_cheque',
    # DC Protocol (Jan 2026): Previous Experience Documents
    'bank_statement_1',
    'bank_statement_2',
    'bank_statement_3',
    'offer_letter',
    'pay_slip_1',
    'pay_slip_2',
    'pay_slip_3'
]

# Experience document types for validation
EXPERIENCE_DOCUMENT_TYPES = [
    'bank_statement_1', 'bank_statement_2', 'bank_statement_3',
    'offer_letter',
    'pay_slip_1', 'pay_slip_2', 'pay_slip_3'
]

# DC Protocol: Indian Standard Time helper
def get_indian_time():
    """Get current time in Indian timezone (IST)"""
    ist = pytz.timezone('Asia/Kolkata')
    return datetime.now(ist).replace(tzinfo=None)

router = APIRouter(prefix="/staff", tags=["Staff Employees"])


class EmployeeCreateRequest(BaseModel):
    salutation: Optional[str] = None  # Mr, Mrs, Ms, Dr
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    full_name: str = Field(..., min_length=1, max_length=256)
    email: Optional[str] = None  # Optional - login uses emp_code
    phone: Optional[str] = None
    department_id: Optional[int] = None
    designation: Optional[str] = None
    role_id: int
    date_of_joining: date
    reporting_manager_id: Optional[int] = None  # DC: Links to manager for team visibility
    staff_type: str = 'MN_STAFF'  # DC: Staff type - Default MN_STAFF (Dec 04, 2025)
    # emp_code and password are auto-generated
    
    # DC Protocol (Dec 06, 2025): Module Assignment - List of module IDs to assign to employee
    module_ids: Optional[List[int]] = None  # List of module IDs from staff_module_master
    
    # DC Protocol (Dec 15, 2025): Multi-Company Assignment
    base_company_id: Optional[int] = None  # Primary/home company for HR/ownership
    data_companies: Optional[List[int]] = None  # Company IDs where employee can access data
    
    # DC Protocol (Dec 21, 2025): Multi-Department Assignment
    additional_departments: Optional[List[int]] = None  # Additional department IDs (multi-department support)
    
    # DC Protocol (Jan 2026): Is Experienced Flag
    is_experienced: bool = False  # If True, previous experience documents are mandatory in KYC
    
    # DC Protocol (Feb 2026): Call Tracking Enabled
    call_tracking_enabled: bool = False  # If True, quality test call tracking is enabled for this employee

    # DC Protocol (Mar 2026): Team Tag — Team A/B/C grouping for compliance reporting
    team_tag: Optional[str] = None  # team_a, team_b, team_c, or None

    # DC Protocol (Jul 2026): Freelancer access mode for module restriction (default vs only_leads)
    freelancer_access_mode: Optional[str] = 'default'

    @field_validator('email', mode='before')
    @classmethod
    def empty_str_to_none(cls, v):
        if v == '' or v is None:
            return None
        return v
    
    @field_validator('staff_type', mode='before')
    @classmethod
    def validate_staff_type(cls, v):
        # DC Protocol (Dec 04, 2025): Valid staff types with prefixes
        # Active types (shown in UI):
        # - MN_STAFF = MN Staff (MN10001+) - MN prefix (default)
        # - FREELANCER = Freelancer (FL10001+) - FL prefix
        # - MYNT_REAL = Mynt Staff (MR10001+) - MR prefix
        # Legacy type (hidden from UI but valid for existing records):
        # - MN_EMPLOYEE = Legacy MN Employee (MN50001+) - kept for backward compatibility
        valid_types = ['MN_STAFF', 'FREELANCER', 'MYNT_REAL', 'MN_EMPLOYEE']
        if v not in valid_types:
            raise ValueError(f"staff_type must be one of {valid_types}")
        return v


# DC: Role-based access control constants
SUPREME_ROLES = ["vgk4u"]  # VGK4U Supreme has ALL access
ADD_EDIT_ROLES = ["vgk4u", "hr", "ea"]  # Roles that can add/edit employees (VGK4U + HR + EA)
VIEW_ALL_ROLES = ["vgk4u", "key_leadership", "hr", "ea"]  # Roles that can view all employees
VIEW_REPORTS_ROLES = ["leadership_role", "team_leader", "manager"]  # Roles that can view direct reports
KYC_APPROVAL_ROLES = ["vgk4u", "key_leadership", "leadership_role", "hr", "ea"]  # Roles that can approve/reject KYC
PASSWORD_RESET_ROLES = ["vgk4u", "key_leadership", "hr", "ea"]  # DC: Roles that can reset employee passwords
STATUS_CHANGE_ROLES = ["vgk4u", "key_leadership", "hr", "ea"]  # DC: Roles that can deactivate/reactivate employees
PROTECTED_EMPLOYEE_CODES = ["MR10001"]  # DC: Protected employees that cannot be deactivated/resigned


class EmployeeUpdateRequest(BaseModel):
    salutation: Optional[str] = None  # Mr, Mrs, Ms, Dr
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    full_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    department_id: Optional[int] = None
    designation: Optional[str] = None
    role_id: Optional[int] = None
    status: Optional[str] = None
    reporting_manager_id: Optional[int] = None  # DC: Links to manager for team visibility
    
    # DC Protocol (Jan 2026): emp_code editing for VGK4U Supreme only
    emp_code: Optional[str] = None  # Employee ID - only VGK4U can edit
    staff_type: Optional[str] = None  # MN_STAFF, MN_EMPLOYEE, FREELANCER, MYNT_REAL
    
    # DC Protocol (Dec 06, 2025): Module Assignment - List of module IDs to assign to employee
    module_ids: Optional[List[int]] = None  # List of module IDs from staff_module_master (replaces current assignments)
    
    # DC Protocol (Dec 15, 2025): Multi-Company Assignment
    base_company_id: Optional[int] = None  # Primary/home company for HR/ownership
    data_companies: Optional[List[int]] = None  # Company IDs where employee can access data
    
    # DC Protocol (Dec 21, 2025): Multi-Department Assignment
    additional_departments: Optional[List[int]] = None  # Additional department IDs (multi-department support)
    
    # DC Protocol (Jan 2026): Employment Type - Probation/Confirmed tracking
    employment_type: Optional[str] = None  # probation, confirmed, extended_probation
    probation_period_months: Optional[int] = None  # 3, 6, 9, 12 months
    probation_start_date: Optional[date] = None
    probation_end_date: Optional[date] = None
    confirmation_date: Optional[date] = None
    probation_extended: Optional[bool] = None
    probation_extension_count: Optional[int] = None
    probation_notes: Optional[str] = None
    
    # DC Protocol (Feb 2026): Call Tracking Enabled
    call_tracking_enabled: Optional[bool] = None  # If True, quality test call tracking is enabled

    # DC Protocol (Mar 2026): Team Tag — Team A/B/C grouping for compliance reporting
    team_tag: Optional[str] = None  # team_a, team_b, team_c, or None (clears tag)

    # [DC-PARTNER-CONTACTS-001] Link to partner showroom for dual portal login
    linked_partner_id: Optional[int] = None  # FK → official_partners.id; None = no link

    # DC Protocol (Jul 2026): Freelancer access mode for module restriction
    freelancer_access_mode: Optional[str] = None


class DepartmentCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    description: Optional[str] = None
    head_id: Optional[int] = None


class DepartmentUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    head_id: Optional[int] = None
    is_active: Optional[bool] = None


# DC Protocol: Status change request models (Dec 2025)
class EmployeeStatusChangeRequest(BaseModel):
    """Request model for deactivate/resigned/reactivate operations"""
    reason: str = Field(..., min_length=10, max_length=1000, description="Mandatory reason for status change")
    notes: Optional[str] = Field(None, max_length=2000, description="Optional additional notes")
    confirm_text: str = Field(..., description="Must be 'CONFIRM' to proceed")
    last_working_date: Optional[str] = Field(None, description="Last working date (YYYY-MM-DD) for deactivation/resignation")
    restart_date: Optional[str] = Field(None, description="Restart/rejoin date (YYYY-MM-DD) for reactivation")


def check_permission(current_user: StaffEmployee, required_level: int, action: str = "perform this action"):
    """
    Check if user has required permission level
    DC: Centralized permission checking
    """
    if not current_user.role or current_user.role.hierarchy_level < required_level:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Insufficient permissions to {action}. Required level: {required_level}"
        )


@router.get("/employees/subordinates", summary="Get subordinates for KRA assignment")
async def get_subordinates(
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """
    Get employees that current user can assign KRAs to
    DC: Managers see their direct reports, VGK4U/HR see all active employees
    """
    role_code = current_user.role.role_code.lower() if current_user.role and current_user.role.role_code else None
    
    query = db.query(StaffEmployee).filter(StaffEmployee.status == 'active')
    
    if role_code in VIEW_ALL_ROLES:
        pass
    elif role_code in VIEW_REPORTS_ROLES:
        query = query.filter(StaffEmployee.reporting_manager_id == current_user.id)
    else:
        return {"success": True, "employees": []}
    
    employees = query.order_by(StaffEmployee.full_name).all()
    
    return {
        "success": True,
        "employees": [
            {
                "id": e.id,
                "employee_id": e.emp_code,
                "first_name": e.full_name.split()[0] if e.full_name else "",
                "last_name": " ".join(e.full_name.split()[1:]) if e.full_name and len(e.full_name.split()) > 1 else "",
                "full_name": e.full_name,
                "emp_code": e.emp_code,
                "department": e.department.name if e.department else None,
                "role": e.role.role_name if e.role else None
            }
            for e in employees
        ]
    }


@router.get("/employees/team", summary="Get team members for manager view")
async def get_team_members(
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """
    Get team members for manager to filter journeys
    DC: Returns direct reports for managers, all employees for admins
    WVV: Role-based access control
    """
    role_code = current_user.role.role_code.lower() if current_user.role and current_user.role.role_code else None
    hierarchy_level = current_user.role.hierarchy_level if current_user.role else 0
    
    if hierarchy_level >= 150 or role_code in VIEW_ALL_ROLES:
        employees = db.query(StaffEmployee).filter(
            StaffEmployee.status == 'active'
        ).order_by(StaffEmployee.full_name).all()
    elif hierarchy_level <= 5 or role_code in VIEW_REPORTS_ROLES:
        employees = db.query(StaffEmployee).filter(
            StaffEmployee.reporting_manager_id == current_user.id,
            StaffEmployee.status == 'active'
        ).order_by(StaffEmployee.full_name).all()
    else:
        return {"success": True, "employees": []}
    
    return {
        "success": True,
        "employees": [
            {
                "id": e.id,
                "emp_code": e.emp_code,
                "full_name": e.full_name,
                "department": e.department.name if e.department else None,
                "role": e.role.role_name if e.role else None,
                "designation": e.designation
            }
            for e in employees
        ]
    }


@router.get("/employees")
async def list_employees(
    request: Request,
    status_filter: Optional[str] = Query(None, alias="status"),
    department_id: Optional[int] = None,
    role_id: Optional[int] = None,
    staff_type: Optional[str] = None,
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """
    List employees with filtering and pagination
    DC: Role-based data access (Updated RBAC)
    DC_STAFF_TYPE_FILTER_001 (Dec 05, 2025): Added staff_type filter
    - Key Leadership / HR: All employees
    - Leadership Role / Team Leader / Manager: Direct reports only (based on reporting_manager_id)
    - Senior/Junior Executive: No access to Employees menu (should not reach here)
    """
    query = db.query(StaffEmployee)
    
    role_code = current_user.role.role_code.lower() if current_user.role and current_user.role.role_code else None
    
    # DC: Apply role-based visibility filtering
    if role_code in VIEW_ALL_ROLES:
        # Key Leadership and HR can see all employees
        pass
    elif role_code in VIEW_REPORTS_ROLES:
        # Leadership Role, Team Leader, Manager: Can only see direct reports
        query = query.filter(StaffEmployee.reporting_manager_id == current_user.id)
    else:
        # Senior/Junior Executive: No access to employee list (return empty)
        return {
            "success": True,
            "employees": [],
            "pagination": {"page": page, "limit": limit, "total": 0, "pages": 0},
            "message": "Access denied. Your role does not have access to employee list."
        }
    
    if status_filter:
        query = query.filter(StaffEmployee.status == status_filter)
    
    if department_id:
        query = query.filter(StaffEmployee.department_id == department_id)
    
    if role_id:
        query = query.filter(StaffEmployee.role_id == role_id)
    
    # DC_STAFF_TYPE_FILTER_001: Filter by staff type
    if staff_type and staff_type.upper() in ['MN_STAFF', 'MN_EMPLOYEE', 'FREELANCER', 'MYNT_REAL']:
        query = query.filter(StaffEmployee.staff_type == staff_type.upper())
    
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            or_(
                StaffEmployee.full_name.ilike(search_term),
                StaffEmployee.email.ilike(search_term),
                StaffEmployee.emp_code.ilike(search_term)
            )
        )
    
    total = query.count()
    
    employees = query.order_by(StaffEmployee.created_at.desc())\
                     .offset((page - 1) * limit)\
                     .limit(limit)\
                     .all()
    
    # DC Protocol (Dec 21, 2025): Resolve data_companies to include company names
    # Build a lookup of all company IDs referenced across employees
    all_company_ids = set()
    for emp in employees:
        if emp.data_companies:
            all_company_ids.update(emp.data_companies)
    
    # Fetch company details in single query
    company_lookup = {}
    if all_company_ids:
        companies = db.query(AssociatedCompany).filter(
            AssociatedCompany.id.in_(all_company_ids)
        ).all()
        company_lookup = {c.id: {"company_id": c.id, "company_name": c.company_name, "company_code": c.company_code} for c in companies}
    
    # Convert employees to dict and resolve data_companies
    employee_list = []
    for emp in employees:
        emp_dict = emp.to_dict()
        # Resolve data_companies IDs to full objects with names
        if emp.data_companies:
            emp_dict["data_companies"] = [
                company_lookup.get(cid, {"company_id": cid, "company_name": f"ID: {cid}"})
                for cid in emp.data_companies
            ]
        else:
            emp_dict["data_companies"] = []
        employee_list.append(emp_dict)
    
    return {
        "success": True,
        "employees": employee_list,
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total,
            "pages": (total + limit - 1) // limit
        }
    }


# NOTE: /employees/directory MUST be defined BEFORE /employees/{employee_id} due to FastAPI route ordering
@router.get("/employees/directory")
async def get_employees_directory(
    department_id: Optional[int] = Query(None),
    role_id: Optional[int] = Query(None),
    kyc_status: Optional[str] = Query(None),
    staff_type: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """
    Get employee directory with KYC status
    DC: VGK4U Supreme, Key Leadership, Admin, and HR roles only
    DC_STAFF_TYPE_FILTER_001 (Dec 05, 2025): Added staff_type filter
    """
    # DC Protocol: Menu-based access control - page assignment = full access
    role_code = current_user.role.role_code.lower() if current_user.role and current_user.role.role_code else None
    # if role_code not in KYC_APPROVAL_ROLES:
    #     raise HTTPException(
    #         status_code=status.HTTP_403_FORBIDDEN,
    #         detail="Only VGK4U Supreme, Key Leadership, Admin, or HR can access employee directory"
    #     )
    
    query = db.query(StaffEmployee).filter(StaffEmployee.status == 'active')
    
    # Apply filters
    if department_id:
        query = query.filter(StaffEmployee.department_id == department_id)
    
    if role_id:
        query = query.filter(StaffEmployee.role_id == role_id)
    
    if kyc_status:
        query = query.filter(StaffEmployee.kyc_status == kyc_status)
    
    # DC_STAFF_TYPE_FILTER_001: Filter by staff type
    if staff_type and staff_type.upper() in ['MN_STAFF', 'MN_EMPLOYEE', 'FREELANCER', 'MYNT_REAL']:
        query = query.filter(StaffEmployee.staff_type == staff_type.upper())
    
    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            (StaffEmployee.full_name.ilike(search_pattern)) |
            (StaffEmployee.emp_code.ilike(search_pattern)) |
            (StaffEmployee.email.ilike(search_pattern))
        )
    
    # Get totals for stats
    total = query.count()
    total_approved = db.query(StaffEmployee).filter(
        StaffEmployee.status == 'active',
        StaffEmployee.kyc_status == 'approved'
    ).count()
    total_pending = db.query(StaffEmployee).filter(
        StaffEmployee.status == 'active',
        StaffEmployee.kyc_status.in_(['pending', 'submitted'])
    ).count()
    total_rejected = db.query(StaffEmployee).filter(
        StaffEmployee.status == 'active',
        StaffEmployee.kyc_status == 'rejected'
    ).count()
    
    # Get employees with pagination
    employees = query.order_by(StaffEmployee.emp_code)\
                     .offset((page - 1) * limit)\
                     .limit(limit)\
                     .all()
    
    # Get KYC data for employees
    employee_ids = [e.id for e in employees]
    kyc_records = db.query(StaffEmployeeKyc).filter(
        StaffEmployeeKyc.employee_id.in_(employee_ids)
    ).all()
    kyc_map = {k.employee_id: k for k in kyc_records}
    
    # Get departments for dropdown
    departments = db.query(StaffDepartment).filter(StaffDepartment.is_active == True).all()
    
    # Get roles for dropdown
    roles = db.query(StaffRole).filter(StaffRole.is_active == True).all()
    
    # Build response
    employee_list = []
    for emp in employees:
        kyc = kyc_map.get(emp.id)
        emp_data = emp.to_dict()
        emp_data['kyc'] = {
            'status': kyc.status if kyc else 'not_started',
            'submitted_at': str(kyc.submitted_at) if kyc and kyc.submitted_at else None,
            'reviewed_at': str(kyc.reviewed_at) if kyc and kyc.reviewed_at else None,
            'has_documents': bool(kyc.documents) if kyc else False
        }
        employee_list.append(emp_data)
    
    return {
        "success": True,
        "employees": employee_list,
        "stats": {
            "total": db.query(StaffEmployee).filter(StaffEmployee.status == 'active').count(),
            "approved": total_approved,
            "pending": total_pending,
            "rejected": total_rejected
        },
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total,
            "pages": (total + limit - 1) // limit
        },
        "filters": {
            "departments": [{"id": d.id, "name": d.name} for d in departments],
            "roles": [{"id": r.id, "name": r.role_name, "code": r.role_code} for r in roles]
        }
    }


@router.get("/employees/managers", summary="Get managers for filter dropdown")
async def list_managers(
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """
    List all employees who are managers (have direct reports)
    DC Protocol: For filter dropdowns in attendance sheet and other pages
    """
    manager_ids = db.query(StaffEmployee.reporting_manager_id).filter(
        StaffEmployee.status == 'active',
        StaffEmployee.reporting_manager_id.isnot(None)
    ).distinct().all()
    
    manager_id_list = [m[0] for m in manager_ids if m[0]]
    
    if not manager_id_list:
        return {"success": True, "managers": []}
    
    managers = db.query(StaffEmployee).filter(
        StaffEmployee.id.in_(manager_id_list),
        StaffEmployee.status == 'active'
    ).order_by(StaffEmployee.full_name).all()
    
    return {
        "success": True,
        "managers": [{
            "id": mgr.id,
            "full_name": mgr.full_name,
            "emp_code": mgr.emp_code,
            "department": mgr.department.name if mgr.department else None
        } for mgr in managers]
    }


@router.get("/employees/{employee_id}")
async def get_employee(
    employee_id: int,
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """
    Get single employee details
    DC: Access control based on role
    """
    employee = db.query(StaffEmployee).filter_by(id=employee_id).first()
    
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee not found"
        )
    
    role_code = current_user.role.role_code if current_user.role else "employee"
    
    # DC Protocol: Menu-based access control - page assignment = full access
    # if role_code == "employee" and employee.id != current_user.id:
    #     raise HTTPException(
    #         status_code=status.HTTP_403_FORBIDDEN,
    #         detail="Access denied"
    #     )
    
    # if role_code == "supervisor" and employee.department_id != current_user.department_id:
    #     raise HTTPException(
    #         status_code=status.HTTP_403_FORBIDDEN,
    #         detail="Access denied. Employee not in your department."
    #     )
    
    include_sensitive = role_code in ["vgk4u", "hr"]
    
    return {
        "success": True,
        "employee": employee.to_dict(include_sensitive=include_sensitive)
    }


# ============= MODULE MANAGEMENT ENDPOINTS (Dec 06, 2025) =============

@router.get("/modules/master", summary="Get module master catalog")
async def get_module_master(
    category: Optional[str] = None,
    include_inactive: bool = False,
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """
    Get the master catalog of all available system modules
    DC Protocol (Dec 06, 2025): Module Assignment Feature
    
    Returns all modules that can be assigned to employees.
    Only VGK4U/HR/EA can access this endpoint (for employee management).
    """
    role_code = current_user.role.role_code if current_user.role else None
    
    # DC Protocol: Menu-based access control - page assignment = full access
    # if role_code not in ADD_EDIT_ROLES:
    #     raise HTTPException(
    #         status_code=status.HTTP_403_FORBIDDEN,
    #         detail="Only VGK4U Supreme, HR, or EA can access module catalog"
    #     )
    
    query = db.query(StaffModuleMaster)
    
    if not include_inactive:
        query = query.filter(StaffModuleMaster.is_active == True)
    
    if category:
        query = query.filter(StaffModuleMaster.module_category == category)
    
    modules = query.order_by(StaffModuleMaster.display_order, StaffModuleMaster.module_name).all()
    
    # Group by category for easier UI consumption
    categories = {}
    for module in modules:
        cat = module.module_category or 'uncategorized'
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(module.to_dict())
    
    return {
        "success": True,
        "modules": [m.to_dict() for m in modules],
        "categories": categories,
        "total": len(modules)
    }


@router.get("/employees/{employee_id}/modules", summary="Get employee's assigned modules")
async def get_employee_modules(
    employee_id: int,
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """
    Get modules assigned to a specific employee
    DC Protocol (Dec 06, 2025): Module Assignment Feature
    
    VGK4U/HR/EA can view any employee's modules.
    Employees can view their own modules.
    """
    employee = db.query(StaffEmployee).filter_by(id=employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    role_code = current_user.role.role_code.lower() if current_user.role and current_user.role.role_code else None
    
    # DC Protocol: Menu-based access control - page assignment = full access
    # Any authenticated staff can view other staff members' modules
    
    assignments = db.query(StaffEmployeeModule).filter(
        StaffEmployeeModule.employee_id == employee_id,
        StaffEmployeeModule.is_active == True
    ).all()
    
    return {
        "success": True,
        "employee_id": employee_id,
        "employee_code": employee.emp_code,
        "employee_name": employee.full_name,
        "assigned_modules": [a.to_dict() for a in assignments],
        "module_ids": [a.module_id for a in assignments],
        "module_keys": [a.module.module_key for a in assignments if a.module],
        "total": len(assignments)
    }


class ModuleAssignmentRequest(BaseModel):
    """Request model for updating employee module assignments"""
    module_ids: List[int] = Field(..., description="List of module IDs to assign (replaces current assignments)")
    reason: Optional[str] = Field(None, max_length=500, description="Optional reason for the change")


@router.put("/employees/{employee_id}/modules", summary="Update employee's assigned modules")
async def update_employee_modules(
    employee_id: int,
    data: ModuleAssignmentRequest = Body(...),
    request: Request = None,
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """
    Update modules assigned to an employee
    DC Protocol (Dec 06, 2025): Module Assignment Feature
    
    This replaces all current module assignments with the new list.
    Only VGK4U/HR/EA can modify module assignments.
    """
    role_code = current_user.role.role_code if current_user.role else None
    
    # DC Protocol: Menu-based access control - page assignment = full access
    # if role_code not in ADD_EDIT_ROLES:
    #     raise HTTPException(status_code=403, detail="Only VGK4U Supreme, HR, or EA can modify module assignments")
    
    employee = db.query(StaffEmployee).filter_by(id=employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    # Get current assignments
    current_assignments = db.query(StaffEmployeeModule).filter(
        StaffEmployeeModule.employee_id == employee_id,
        StaffEmployeeModule.is_active == True
    ).all()
    current_module_ids = {a.module_id for a in current_assignments}
    new_module_ids = set(data.module_ids) if data.module_ids else set()
    
    # Validate new module IDs (only if non-empty)
    valid_new_module_ids = set()
    module_id_to_key = {}
    if data.module_ids:
        valid_new_modules = db.query(StaffModuleMaster).filter(
            StaffModuleMaster.id.in_(data.module_ids),
            StaffModuleMaster.is_active == True
        ).all()
        valid_new_module_ids = {m.id for m in valid_new_modules}
        module_id_to_key = {m.id: m.module_key for m in valid_new_modules}
        
        # Check for invalid module IDs
        invalid_ids = new_module_ids - valid_new_module_ids
        if invalid_ids:
            raise HTTPException(status_code=400, detail=f"Invalid or inactive module IDs: {list(invalid_ids)}")
    
    module_changes = {"added": [], "removed": []}
    
    # Modules to add
    modules_to_add = valid_new_module_ids - current_module_ids
    # Modules to remove
    modules_to_remove = current_module_ids - new_module_ids
    
    # Add new assignments
    for module_id in modules_to_add:
        emp_module = StaffEmployeeModule(
            employee_id=employee.id,
            module_id=module_id,
            assigned_by=current_user.id,
            is_active=True
        )
        db.add(emp_module)
        module_changes["added"].append(module_id_to_key.get(module_id))
    
    # Remove old assignments (soft delete)
    for assignment in current_assignments:
        if assignment.module_id in modules_to_remove:
            assignment.is_active = False
            assignment.updated_by = current_user.id
            module_key = assignment.module.module_key if assignment.module else str(assignment.module_id)
            module_changes["removed"].append(module_key)
    
    # Log module changes
    if module_changes["added"]:
        log_employee_module_change(
            db, employee, "BULK_ASSIGN", module_changes["added"], current_user,
            reason=data.reason or "Module assignment update",
            ip_address=request.client.host if request.client else None
        )
    if module_changes["removed"]:
        log_employee_module_change(
            db, employee, "BULK_REMOVE", module_changes["removed"], current_user,
            reason=data.reason or "Module assignment update",
            ip_address=request.client.host if request.client else None
        )
    
    log_staff_audit(
        db, current_user.id, "UPDATE_MODULES", "employee",
        resource_id=employee.id,
        new_data={
            "module_ids": list(valid_new_module_ids),
            "added": module_changes["added"],
            "removed": module_changes["removed"]
        },
        ip_address=request.client.host if request.client else None
    )
    
    db.commit()
    
    # Get updated assignments
    updated_assignments = db.query(StaffEmployeeModule).filter(
        StaffEmployeeModule.employee_id == employee_id,
        StaffEmployeeModule.is_active == True
    ).all()
    
    return {
        "success": True,
        "message": f"Module assignments updated. Added: {len(module_changes['added'])}, Removed: {len(module_changes['removed'])}",
        "employee_id": employee_id,
        "module_changes": module_changes,
        "current_modules": [a.to_dict() for a in updated_assignments],
        "total_modules": len(updated_assignments)
    }


@router.post("/employees")
async def create_employee(
    data: EmployeeCreateRequest = Body(...),
    request: Request = None,
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """
    Create new employee
    DC: HR ONLY - Central employee management authority
    - Employee ID: Auto-generated based on staff_type
      - MN_STAFF: MN10001-49999 (MN Staff - DEFAULT)
      - MN_EMPLOYEE: MN50001+ (MN Employee - separate range)
      - FREELANCER: FL10001+ (Freelancer with FL prefix)
      - MYNT_REAL: MR10007+ (Legacy Mynt Real Staff)
    - Password: Default = Employee ID (requires change on first login)
    
    Nov 29, 2025: Extended to support MN Staff (freelancer) creation
    Dec 04, 2025: Expanded to 3 staff types - MN_STAFF, MN_EMPLOYEE, FREELANCER
    """
    role_code = current_user.role.role_code if current_user.role else None
    
    # DC Protocol: Menu-based access control - page assignment = full access
    # if role_code not in ADD_EDIT_ROLES:
    #     raise HTTPException(
    #         status_code=status.HTTP_403_FORBIDDEN,
    #         detail="Only VGK4U Supreme or HR can add new employees"
    #     )
    
    # Check email uniqueness if provided
    if data.email:
        existing_email = db.query(StaffEmployee).filter_by(email=data.email.lower()).first()
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already exists"
            )
    
    # Validate role
    role = db.query(StaffRole).filter_by(id=data.role_id, is_active=True).first()
    if not role:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid role"
        )
    
    # DC Protocol: Menu-based access control - page assignment = full access
    # if role.role_code == "key_leadership" and current_user.role.role_code not in ["vgk4u", "key_leadership"]:
    #     raise HTTPException(
    #         status_code=status.HTTP_403_FORBIDDEN,
    #         detail="Only VGK4U Supreme or Key Leadership can create Key Leadership accounts"
    #     )
    
    # Validate department if provided
    if data.department_id:
        dept = db.query(StaffDepartment).filter_by(id=data.department_id, is_active=True).first()
        if not dept:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid department"
            )
    
    # DC: Validate reporting manager if provided
    if data.reporting_manager_id:
        manager = db.query(StaffEmployee).filter_by(id=data.reporting_manager_id, status='active').first()
        if not manager:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid reporting manager"
            )
    
    # DC: Validate FREELANCER department assignment (Dec 04, 2025)
    # FREELANCER should ideally be assigned to freelancer departments
    if data.staff_type == 'FREELANCER' and data.department_id:
        dept = db.query(StaffDepartment).filter_by(id=data.department_id).first()
        if dept and not dept.is_freelancer_dept:
            # Log warning but allow - admin might have valid reason
            import logging
            logging.warning(f"Freelancer being assigned to non-freelancer department: {dept.name}")
    
    # Auto-generate employee code based on staff_type (Dec 04, 2025)
    # MN_STAFF: MN10001-49999 | MN_EMPLOYEE: MN50001+ | FREELANCER: FL10001+ | MYNT_REAL: MR10007+
    emp_code = generate_employee_code(db, staff_type=data.staff_type)
    
    # DC Protocol (Dec 15, 2025): Validate base_company_id if provided
    if data.base_company_id:
        from app.models.staff_accounts import AssociatedCompany
        base_company = db.query(AssociatedCompany).filter_by(id=data.base_company_id, is_active=True).first()
        if not base_company:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid base company"
            )
    
    # DC Protocol (Dec 15, 2025): Validate data_companies if provided
    validated_data_companies = []
    if data.data_companies and len(data.data_companies) > 0:
        from app.models.staff_accounts import AssociatedCompany
        valid_companies = db.query(AssociatedCompany).filter(
            AssociatedCompany.id.in_(data.data_companies),
            AssociatedCompany.is_active == True
        ).all()
        validated_data_companies = [c.id for c in valid_companies]
        invalid_company_ids = set(data.data_companies) - set(validated_data_companies)
        if invalid_company_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid data company IDs: {list(invalid_company_ids)}"
            )

    # DC Protocol (Mar 2026): Auto-apply Sales department dialer defaults.
    # Any new staff assigned to Sales (dept 13) automatically gets call tracking
    # enabled and access to all active companies, matching the established pattern
    # used by Bhoolakshmi (MN10003) and other active Sales telecallers.
    SALES_DEPT_ID = 13
    if data.department_id == SALES_DEPT_ID:
        if not data.call_tracking_enabled:
            data.call_tracking_enabled = True
        if not validated_data_companies:
            from app.models.staff_accounts import AssociatedCompany
            all_active_cos = db.query(AssociatedCompany).filter(
                AssociatedCompany.is_active == True
            ).all()
            validated_data_companies = [c.id for c in all_active_cos]

    # Create employee with default password = employee code
    employee = StaffEmployee(
        emp_code=emp_code,
        staff_type=data.staff_type,  # DC: Store staff type (Nov 29, 2025)
        salutation=data.salutation,
        first_name=data.first_name,
        last_name=data.last_name,
        full_name=data.full_name,
        email=data.email.lower() if data.email else None,
        phone=data.phone,
        department_id=data.department_id,
        designation=data.designation,
        role_id=data.role_id,
        date_of_joining=data.date_of_joining,
        reporting_manager_id=data.reporting_manager_id,  # DC: Link to manager
        base_company_id=data.base_company_id,  # DC Protocol (Dec 15, 2025): Base company
        data_companies=validated_data_companies,  # DC Protocol (Dec 15, 2025): Data companies
        is_experienced=data.is_experienced,  # DC Protocol (Jan 2026): Is Experienced flag
        call_tracking_enabled=data.call_tracking_enabled,  # DC Protocol (Feb 2026): Call tracking
        team_tag=data.team_tag,  # DC Protocol (Mar 2026): Team A/B/C tag
        freelancer_access_mode=data.freelancer_access_mode,  # DC Protocol (Jul 2026): Freelancer access mode
        password_hash=SecurityManager.get_password_hash(emp_code),  # Default password = emp_code
        requires_password_change=True,  # Force password change on first login
        kyc_status='pending',
        created_by=current_user.id
    )
    
    db.add(employee)
    db.flush()
    
    # DC Protocol (Dec 06, 2025): Handle module assignment
    # Only assign modules if explicitly provided - do NOT auto-assign defaults
    assigned_modules = []
    if data.module_ids is not None and len(data.module_ids) > 0:
        # Validate module IDs - reject if any are invalid/inactive
        valid_modules = db.query(StaffModuleMaster).filter(
            StaffModuleMaster.id.in_(data.module_ids),
            StaffModuleMaster.is_active == True
        ).all()
        valid_module_ids = {m.id for m in valid_modules}
        requested_module_ids = set(data.module_ids)
        
        # DC Protocol: Reject invalid module IDs (parity with update_employee_modules)
        invalid_ids = requested_module_ids - valid_module_ids
        if invalid_ids:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid or inactive module IDs: {list(invalid_ids)}"
            )
        
        for module in valid_modules:
            emp_module = StaffEmployeeModule(
                employee_id=employee.id,
                module_id=module.id,
                assigned_by=current_user.id,
                is_active=True
            )
            db.add(emp_module)
            assigned_modules.append(module.module_key)
        
        if assigned_modules:
            log_employee_module_change(
                db, employee, "BULK_ASSIGN", assigned_modules, current_user,
                reason="Initial module assignment during employee creation",
                ip_address=request.client.host if request.client else None
            )
    # If module_ids is None or empty list, no modules are assigned (employee starts with no modules)
    
    # DC Protocol (Dec 21, 2025): Handle additional department assignment
    assigned_departments = []
    if data.additional_departments and len(data.additional_departments) > 0:
        valid_depts = db.query(StaffDepartment).filter(
            StaffDepartment.id.in_(data.additional_departments),
            StaffDepartment.is_active == True
        ).all()
        valid_dept_ids = {d.id for d in valid_depts}
        
        for dept in valid_depts:
            emp_dept = StaffEmployeeDepartment(
                employee_id=employee.id,
                department_id=dept.id,
                assigned_by=current_user.id
            )
            db.add(emp_dept)
            assigned_departments.append(dept.name)
    
    log_staff_audit(
        db, current_user.id, "CREATE", "employee",
        resource_id=employee.id,
        new_data={
            "emp_code": employee.emp_code,
            "staff_type": employee.staff_type,
            "full_name": employee.full_name,
            "role": role.role_name,
            "default_password": "Set to Employee ID",
            "assigned_modules": assigned_modules,
            "assigned_departments": assigned_departments
        },
        ip_address=request.client.host if request.client else None
    )
    
    db.commit()
    
    # DC: Staff type labels (Dec 04, 2025 - Expanded to 3 active types)
    STAFF_TYPE_LABELS = {
        'MN_STAFF': 'MN Staff',
        'MN_EMPLOYEE': 'MN Employee',
        'FREELANCER': 'Freelancer',
        'MYNT_REAL': 'Mynt Real Staff'
    }
    staff_type_label = STAFF_TYPE_LABELS.get(data.staff_type, 'Staff')
    
    return {
        "success": True,
        "message": f"{staff_type_label} created successfully. Employee ID: {emp_code}. Default password is the Employee ID.",
        "employee": employee.to_dict(),
        "credentials": {
            "employee_id": emp_code,
            "staff_type": data.staff_type,
            "staff_type_label": staff_type_label,
            "default_password": emp_code,
            "note": "Password change required on first login"
        }
    }


@router.put("/employees/{employee_id}")
async def update_employee(
    employee_id: int,
    data: EmployeeUpdateRequest = Body(...),
    request: Request = None,
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """
    Update employee
    DC: VGK4U Supreme and HR can edit employees
    """
    role_code = current_user.role.role_code if current_user.role else None
    
    # DC Protocol: Menu-based access control - page assignment = full access
    # if role_code not in ADD_EDIT_ROLES:
    #     raise HTTPException(
    #         status_code=status.HTTP_403_FORBIDDEN,
    #         detail="Only VGK4U Supreme or HR can edit employees"
    #     )
    
    employee = db.query(StaffEmployee).filter_by(id=employee_id).first()
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee not found"
        )
    
    # DC: Prevent self-demotion or role escalation
    if employee.id == current_user.id and data.role_id and data.role_id != employee.role_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot change your own role"
        )
    
    old_data = employee.to_dict()
    
    if data.salutation is not None:
        employee.salutation = data.salutation
    
    if data.first_name is not None:
        employee.first_name = data.first_name
    
    if data.last_name is not None:
        employee.last_name = data.last_name
    
    if data.full_name is not None:
        employee.full_name = data.full_name
    
    if data.email is not None:
        employee.email = data.email.lower() if data.email else None
    
    if data.phone is not None:
        employee.phone = data.phone
    
    if data.department_id is not None:
        if data.department_id > 0:
            dept = db.query(StaffDepartment).filter_by(id=data.department_id, is_active=True).first()
            if not dept:
                raise HTTPException(status_code=400, detail="Invalid department")
            employee.department_id = data.department_id
        else:
            employee.department_id = None
    
    if data.designation is not None:
        employee.designation = data.designation
    
    if data.role_id is not None:
        role = db.query(StaffRole).filter_by(id=data.role_id, is_active=True).first()
        if not role:
            raise HTTPException(status_code=400, detail="Invalid role")
        
        if role.role_code == "vgk4u" and current_user.role.role_code != "vgk4u":
            raise HTTPException(status_code=403, detail="Only VGK4U can assign VGK4U role")
        
        employee.role_id = data.role_id
    
    if data.status is not None:
        if data.status not in ['active', 'inactive', 'suspended', 'terminated']:
            raise HTTPException(status_code=400, detail="Invalid status")
        employee.status = data.status
    
    # DC: Handle reporting manager update
    if data.reporting_manager_id is not None:
        if data.reporting_manager_id > 0:
            # Cannot set self as reporting manager
            if data.reporting_manager_id == employee.id:
                raise HTTPException(status_code=400, detail="Employee cannot be their own reporting manager")
            manager = db.query(StaffEmployee).filter_by(id=data.reporting_manager_id, status='active').first()
            if not manager:
                raise HTTPException(status_code=400, detail="Invalid reporting manager")
            employee.reporting_manager_id = data.reporting_manager_id
        else:
            employee.reporting_manager_id = None
    
    # DC Protocol (Jan 2026): Handle emp_code and staff_type update (VGK4U Supreme only)
    # Only block if value is actually being changed, not just re-submitted unchanged
    _staff_type_changing = data.staff_type is not None and data.staff_type != employee.staff_type
    _emp_code_changing = data.emp_code is not None and data.emp_code.upper().strip() != (employee.emp_code or '').upper().strip()
    if (_staff_type_changing or _emp_code_changing) and role_code != 'vgk4u':
        raise HTTPException(
            status_code=403,
            detail="Only VGK4U Supreme can change Employee ID or Staff Type"
        )
    if data.emp_code is not None or data.staff_type is not None:
        
        # Handle staff_type change
        if data.staff_type is not None:
            valid_staff_types = ['MN_STAFF', 'MN_EMPLOYEE', 'FREELANCER', 'MYNT_REAL']
            if data.staff_type not in valid_staff_types:
                raise HTTPException(status_code=400, detail=f"Invalid staff type. Must be one of: {valid_staff_types}")
            employee.staff_type = data.staff_type
        
        # Handle emp_code change
        if data.emp_code is not None:
            new_emp_code = data.emp_code.upper().strip()
            
            # Validate format based on staff type
            current_staff_type = data.staff_type or employee.staff_type
            expected_prefix = {
                'MN_STAFF': 'MN',
                'MN_EMPLOYEE': 'MN',
                'FREELANCER': 'FL',
                'MYNT_REAL': 'MR'
            }.get(current_staff_type, 'MN')
            
            if not new_emp_code.startswith(expected_prefix):
                raise HTTPException(
                    status_code=400, 
                    detail=f"Employee ID must start with '{expected_prefix}' for staff type '{current_staff_type}'"
                )
            
            # Check uniqueness
            existing = db.query(StaffEmployee).filter(
                StaffEmployee.emp_code == new_emp_code,
                StaffEmployee.id != employee.id
            ).first()
            if existing:
                raise HTTPException(status_code=400, detail=f"Employee ID '{new_emp_code}' already exists")
            
            # Protected account check
            if employee.emp_code in PROTECTED_EMPLOYEE_CODES:
                raise HTTPException(status_code=403, detail="Cannot change Employee ID of protected accounts")
            
            employee.emp_code = new_emp_code
    
    # DC Protocol (Jan 2026): Handle Employment Type fields
    if data.employment_type is not None:
        valid_employment_types = ['probation', 'confirmed', 'extended_probation']
        if data.employment_type not in valid_employment_types:
            raise HTTPException(status_code=400, detail=f"Invalid employment type. Must be one of: {valid_employment_types}")
        employee.employment_type = data.employment_type
        
        # Auto-set confirmation date if confirmed
        if data.employment_type == 'confirmed' and not employee.confirmation_date:
            employee.confirmation_date = date.today()
    
    if data.probation_period_months is not None:
        if data.probation_period_months not in [3, 6, 9, 12]:
            raise HTTPException(status_code=400, detail="Probation period must be 3, 6, 9, or 12 months")
        employee.probation_period_months = data.probation_period_months
    
    if data.probation_start_date is not None:
        employee.probation_start_date = data.probation_start_date
    
    if data.probation_end_date is not None:
        employee.probation_end_date = data.probation_end_date
    
    if data.confirmation_date is not None:
        employee.confirmation_date = data.confirmation_date
    
    if data.probation_extended is not None:
        employee.probation_extended = data.probation_extended
        if data.probation_extended:
            employee.employment_type = 'extended_probation'
            employee.probation_extension_count = (employee.probation_extension_count or 0) + 1
    
    if data.probation_extension_count is not None:
        employee.probation_extension_count = data.probation_extension_count
    
    if data.probation_notes is not None:
        employee.probation_notes = data.probation_notes
    
    if data.call_tracking_enabled is not None:
        employee.call_tracking_enabled = data.call_tracking_enabled

    # DC Protocol (Mar 2026): Handle team tag update
    if data.team_tag is not None:
        valid_tags = ['team_a', 'team_b', 'team_c', '']
        if data.team_tag not in valid_tags:
            raise HTTPException(status_code=400, detail="Invalid team_tag. Must be team_a, team_b, team_c, or empty")
        employee.team_tag = data.team_tag if data.team_tag else None

    # [DC-PARTNER-CONTACTS-001] Handle linked partner showroom update
    if 'linked_partner_id' in data.dict(exclude_unset=True):
        _lp_id = data.linked_partner_id
        try:
            setattr(employee, 'linked_partner_id', _lp_id if _lp_id else None)
        except Exception:
            pass  # Column may not exist yet (bootstrap pending)

    # DC Protocol (Jul 2026): Handle freelancer access mode update
    if data.freelancer_access_mode is not None:
        valid_modes = ['default', 'only_leads']
        if data.freelancer_access_mode not in valid_modes:
            raise HTTPException(status_code=400, detail="Invalid freelancer_access_mode. Must be default or only_leads")
        employee.freelancer_access_mode = data.freelancer_access_mode

    # DC Protocol (Dec 15, 2025): Handle base company update
    if data.base_company_id is not None:
        if data.base_company_id > 0:
            from app.models.staff_accounts import AssociatedCompany
            base_company = db.query(AssociatedCompany).filter_by(id=data.base_company_id, is_active=True).first()
            if not base_company:
                raise HTTPException(status_code=400, detail="Invalid base company")
            employee.base_company_id = data.base_company_id
        else:
            employee.base_company_id = None
    
    # DC Protocol (Dec 15, 2025): Handle data companies update
    if data.data_companies is not None:
        if len(data.data_companies) > 0:
            from app.models.staff_accounts import AssociatedCompany
            valid_companies = db.query(AssociatedCompany).filter(
                AssociatedCompany.id.in_(data.data_companies),
                AssociatedCompany.is_active == True
            ).all()
            validated_data_companies = [c.id for c in valid_companies]
            invalid_company_ids = set(data.data_companies) - set(validated_data_companies)
            if invalid_company_ids:
                raise HTTPException(status_code=400, detail=f"Invalid data company IDs: {list(invalid_company_ids)}")
            employee.data_companies = validated_data_companies
        else:
            employee.data_companies = []
    
    # DC Protocol (Dec 06, 2025): Handle module assignment update
    # module_ids = None: No change to modules
    # module_ids = []: Clear all modules (employee has no access)
    # module_ids = [1,2,3]: Replace with these modules
    module_changes = {"added": [], "removed": []}
    if data.module_ids is not None:
        # Get current assigned modules
        current_assignments = db.query(StaffEmployeeModule).filter(
            StaffEmployeeModule.employee_id == employee.id,
            StaffEmployeeModule.is_active == True
        ).all()
        current_module_ids = {a.module_id for a in current_assignments}
        new_module_ids = set(data.module_ids) if data.module_ids else set()
        
        # Validate new module IDs (only if non-empty)
        valid_new_module_ids = set()
        module_id_to_key = {}
        if data.module_ids:
            valid_new_modules = db.query(StaffModuleMaster).filter(
                StaffModuleMaster.id.in_(data.module_ids),
                StaffModuleMaster.is_active == True
            ).all()
            valid_new_module_ids = {m.id for m in valid_new_modules}
            module_id_to_key = {m.id: m.module_key for m in valid_new_modules}
        
        # Modules to add
        modules_to_add = valid_new_module_ids - current_module_ids
        # Modules to remove
        modules_to_remove = current_module_ids - new_module_ids
        
        # Add new assignments
        for module_id in modules_to_add:
            emp_module = StaffEmployeeModule(
                employee_id=employee.id,
                module_id=module_id,
                assigned_by=current_user.id,
                is_active=True
            )
            db.add(emp_module)
            module_changes["added"].append(module_id_to_key.get(module_id))
        
        # Remove old assignments (soft delete)
        for assignment in current_assignments:
            if assignment.module_id in modules_to_remove:
                assignment.is_active = False
                assignment.updated_by = current_user.id
                module_key = assignment.module.module_key if assignment.module else str(assignment.module_id)
                module_changes["removed"].append(module_key)
        
        # Log module changes
        if module_changes["added"]:
            log_employee_module_change(
                db, employee, "BULK_ASSIGN", module_changes["added"], current_user,
                reason="Module assignment update",
                ip_address=request.client.host if request.client else None
            )
        if module_changes["removed"]:
            log_employee_module_change(
                db, employee, "BULK_REMOVE", module_changes["removed"], current_user,
                reason="Module assignment update",
                ip_address=request.client.host if request.client else None
            )
    
    # DC Protocol (Dec 21, 2025): Handle additional departments update
    dept_changes = {"added": [], "removed": []}
    if data.additional_departments is not None:
        # Get current assigned departments
        current_dept_assignments = db.query(StaffEmployeeDepartment).filter(
            StaffEmployeeDepartment.employee_id == employee.id
        ).all()
        current_dept_ids = {a.department_id for a in current_dept_assignments}
        new_dept_ids = set(data.additional_departments) if data.additional_departments else set()
        
        # Validate new department IDs (only if non-empty)
        valid_new_dept_ids = set()
        dept_id_to_name = {}
        if data.additional_departments:
            valid_new_depts = db.query(StaffDepartment).filter(
                StaffDepartment.id.in_(data.additional_departments),
                StaffDepartment.is_active == True
            ).all()
            valid_new_dept_ids = {d.id for d in valid_new_depts}
            dept_id_to_name = {d.id: d.name for d in valid_new_depts}
        
        # Departments to add
        depts_to_add = valid_new_dept_ids - current_dept_ids
        # Departments to remove
        depts_to_remove = current_dept_ids - new_dept_ids
        
        # Add new department assignments
        for dept_id in depts_to_add:
            emp_dept = StaffEmployeeDepartment(
                employee_id=employee.id,
                department_id=dept_id,
                assigned_by=current_user.id
            )
            db.add(emp_dept)
            dept_changes["added"].append(dept_id_to_name.get(dept_id))
        
        # Remove old department assignments (hard delete for junction table)
        for assignment in current_dept_assignments:
            if assignment.department_id in depts_to_remove:
                db.delete(assignment)
                dept_name = assignment.department.name if assignment.department else str(assignment.department_id)
                dept_changes["removed"].append(dept_name)
    
    employee.updated_at = datetime.utcnow()
    
    log_staff_audit(
        db, current_user.id, "UPDATE", "employee",
        resource_id=employee.id,
        old_data=old_data,
        new_data=employee.to_dict(),
        ip_address=request.client.host if request.client else None
    )
    
    db.commit()
    
    return {
        "success": True,
        "message": "Employee updated successfully",
        "employee": employee.to_dict(),
        "module_changes": module_changes if data.module_ids is not None else None
    }


@router.delete("/employees/{employee_id}")
async def delete_employee(
    request: Request,
    employee_id: int,
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """
    Delete employee (VGK4U ONLY)
    DC: Supreme admin only operation, cannot be delegated
    """
    if current_user.role.role_code != "vgk4u":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only VGK4U can delete employees"
        )
    
    employee = db.query(StaffEmployee).filter_by(id=employee_id).first()
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee not found"
        )
    
    if employee.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete yourself"
        )
    
    old_data = employee.to_dict()
    
    log_staff_audit(
        db, current_user.id, "DELETE", "employee",
        resource_id=employee.id,
        old_data=old_data,
        ip_address=request.client.host if request.client else None
    )
    
    db.delete(employee)
    db.commit()
    
    return {
        "success": True,
        "message": "Employee deleted successfully"
    }


@router.post("/employees/{employee_id}/reset-password")
async def reset_employee_password(
    request: Request,
    employee_id: int,
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """
    Reset employee password (VGK4U, Key Leadership, HR, EA)
    DC Protocol: Atomic password reset with guaranteed account unlock
    WVV Protocol: Complete audit trail and verification
    
    Features:
    - Password reset to Employee ID (e.g., MR10007)
    - Forces password change on next login
    - AUTOMATICALLY UNLOCKS account (default behavior)
    - Self-reset allowed for own password
    """
    role_code = current_user.role.role_code if current_user.role else None
    
    is_self_reset = (employee_id == current_user.id)
    
    # DC Protocol: Menu-based access control - page assignment = full access
    # if not is_self_reset and role_code not in PASSWORD_RESET_ROLES:
    #     raise HTTPException(
    #         status_code=status.HTTP_403_FORBIDDEN,
    #         detail="Only VGK4U, Key Leadership, HR, or EA can reset employee passwords"
    #     )
    
    employee = db.query(StaffEmployee).filter_by(id=employee_id).first()
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee not found"
        )
    
    if not is_self_reset and not current_user.can_manage(employee):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot reset password for an employee with equal or higher role"
        )
    
    new_password = employee.emp_code
    
    was_locked = employee.locked_until is not None
    previous_attempts = employee.failed_login_attempts
    
    try:
        new_password_hash = SecurityManager.get_password_hash(new_password)
        
        if not SecurityManager.verify_password(new_password, new_password_hash):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Password hash generation failed. Please try again."
            )
        
        employee.password_hash = new_password_hash
        employee.last_password_change = datetime.utcnow()
        employee.password_last_reset_by = current_user.id
        employee.password_last_reset_at = datetime.utcnow()
        employee.requires_password_change = True
        employee.failed_login_attempts = 0
        employee.locked_until = None
        
        log_staff_audit(
            db, current_user.id, "PASSWORD_RESET", "employee",
            resource_id=employee.id,
            new_data={
                "reset_by": current_user.emp_code,
                "reset_by_id": current_user.id,
                "target_emp_code": employee.emp_code,
                "new_password": "Reset to Employee ID",
                "requires_change": True,
                "account_unlocked": True,
                "was_locked": was_locked,
                "previous_failed_attempts": previous_attempts,
                "is_self_reset": is_self_reset
            },
            ip_address=request.client.host if request.client else None
        )
        
        db.flush()
        
        db.refresh(employee)
        
        if employee.failed_login_attempts != 0:
            raise ValueError("Account unlock failed - failed_login_attempts not cleared")
        if employee.locked_until is not None:
            raise ValueError("Account unlock failed - locked_until not cleared")
        if not SecurityManager.verify_password(new_password, employee.password_hash):
            raise ValueError("Password hash verification failed after flush")
        
        db.commit()
        
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        log_staff_audit(
            db, current_user.id, "PASSWORD_RESET_FAILED", "employee",
            resource_id=employee.id,
            new_data={
                "error": str(e),
                "reset_by": current_user.emp_code,
                "target_emp_code": employee.emp_code
            },
            ip_address=request.client.host if request.client else None
        )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Password reset failed: {str(e)}. Please contact administrator."
        )
    
    return {
        "success": True,
        "message": f"Password reset to Employee ID ({employee.emp_code}). Account unlocked. Change required on next login.",
        "credentials": {
            "employee_id": employee.emp_code,
            "new_password": employee.emp_code,
            "requires_change": True
        },
        "account_status": {
            "unlocked": True,
            "was_previously_locked": was_locked,
            "failed_attempts_cleared": previous_attempts
        }
    }


@router.get("/departments")
async def list_departments(
    include_inactive: bool = False,
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """
    List all departments
    DC: Available to all authenticated staff
    """
    query = db.query(StaffDepartment)
    
    if not include_inactive:
        query = query.filter_by(is_active=True)
    
    departments = query.order_by(StaffDepartment.name).all()
    
    return {
        "success": True,
        "departments": [dept.to_dict() for dept in departments]
    }


@router.post("/departments")
async def create_department(
    data: DepartmentCreateRequest = Body(...),
    request: Request = None,
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """
    Create new department
    DC: VGK4U/HR only
    """
    check_permission(current_user, 3, "create departments")
    
    existing = db.query(StaffDepartment).filter_by(name=data.name).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Department name already exists"
        )
    
    if data.head_id:
        head = db.query(StaffEmployee).filter_by(id=data.head_id, status='active').first()
        if not head:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid department head"
            )
    
    department = StaffDepartment(
        name=data.name,
        description=data.description,
        head_id=data.head_id
    )
    
    db.add(department)
    db.flush()
    
    log_staff_audit(
        db, current_user.id, "CREATE", "department",
        resource_id=department.id,
        new_data=department.to_dict(),
        ip_address=request.client.host if request.client else None
    )
    
    db.commit()
    
    return {
        "success": True,
        "message": "Department created successfully",
        "department": department.to_dict()
    }


@router.put("/departments/{department_id}")
async def update_department(
    department_id: int,
    data: DepartmentUpdateRequest = Body(...),
    request: Request = None,
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """
    Update department
    DC: VGK4U/HR only
    """
    check_permission(current_user, 3, "update departments")
    
    department = db.query(StaffDepartment).filter_by(id=department_id).first()
    if not department:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Department not found"
        )
    
    old_data = department.to_dict()
    
    if data.name is not None:
        existing = db.query(StaffDepartment).filter(
            StaffDepartment.name == data.name,
            StaffDepartment.id != department_id
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail="Department name already exists")
        department.name = data.name
    
    if data.description is not None:
        department.description = data.description
    
    if data.head_id is not None:
        if data.head_id > 0:
            head = db.query(StaffEmployee).filter_by(id=data.head_id, status='active').first()
            if not head:
                raise HTTPException(status_code=400, detail="Invalid department head")
            department.head_id = data.head_id
        else:
            department.head_id = None
    
    if data.is_active is not None:
        department.is_active = data.is_active
    
    department.updated_at = datetime.utcnow()
    
    log_staff_audit(
        db, current_user.id, "UPDATE", "department",
        resource_id=department.id,
        old_data=old_data,
        new_data=department.to_dict(),
        ip_address=request.client.host if request.client else None
    )
    
    db.commit()
    
    return {
        "success": True,
        "message": "Department updated successfully",
        "department": department.to_dict()
    }


@router.post("/departments/{department_id}/apply-dialer-defaults")
async def apply_department_dialer_defaults(
    department_id: int,
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """
    DC Protocol (Mar 2026): One-shot admin endpoint that brings all active staff in a
    department up to the standard dialer baseline (call_tracking_enabled=True,
    data_companies = all active companies).  Idempotent — re-running is safe.
    Matches the Bhoolakshmi / Anusha pattern used for Sales telecallers.
    VGK4U-only.
    """
    check_permission(current_user, 3, "apply dialer defaults")

    from app.models.staff_accounts import AssociatedCompany

    dept = db.query(StaffDepartment).filter_by(id=department_id, is_active=True).first()
    if not dept:
        raise HTTPException(status_code=404, detail="Department not found")

    all_active_co_ids = sorted([
        c.id for c in db.query(AssociatedCompany).filter(AssociatedCompany.is_active == True).all()
    ])
    all_active_co_set = set(all_active_co_ids)

    staff_in_dept = db.query(StaffEmployee).filter(
        StaffEmployee.department_id == department_id,
        StaffEmployee.status == 'active'
    ).all()

    updated = []
    already_ok = []

    for emp in staff_in_dept:
        needs_update = False
        changes = {}

        if not emp.call_tracking_enabled:
            emp.call_tracking_enabled = True
            changes["call_tracking_enabled"] = True
            needs_update = True

        current_cos = set(emp.data_companies or [])
        missing = all_active_co_set - current_cos
        if missing:
            emp.data_companies = all_active_co_ids
            changes["data_companies"] = all_active_co_ids
            needs_update = True

        if needs_update:
            updated.append({"emp_code": emp.emp_code, "name": emp.full_name, "changes": changes})
        else:
            already_ok.append({"emp_code": emp.emp_code, "name": emp.full_name})

    db.commit()

    return {
        "success": True,
        "department": dept.name,
        "active_companies": all_active_co_ids,
        "total_staff": len(staff_in_dept),
        "updated": updated,
        "already_ok": already_ok,
        "message": f"Applied dialer defaults to {len(updated)} staff member(s) in {dept.name}."
    }


@router.get("/roles")
async def list_roles(
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """
    List all roles
    DC: Reference data for dropdowns
    """
    roles = db.query(StaffRole).filter_by(is_active=True)\
              .order_by(StaffRole.hierarchy_level.desc()).all()
    
    return {
        "success": True,
        "roles": [role.to_dict() for role in roles]
    }


@router.get("/settings")
async def list_settings(
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """
    List all settings
    DC: VGK4U only for full access
    """
    if current_user.role.role_code != "vgk4u":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only VGK4U can view all settings"
        )
    
    settings = db.query(StaffSetting).filter_by(is_active=True).all()
    
    return {
        "success": True,
        "settings": [s.to_dict() for s in settings]
    }


@router.put("/settings/{setting_key}")
async def update_setting(
    request: Request,
    setting_key: str,
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """
    Update setting
    DC: VGK4U only
    """
    if current_user.role.role_code != "vgk4u":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only VGK4U can modify settings"
        )
    
    setting = db.query(StaffSetting).filter_by(setting_key=setting_key).first()
    if not setting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Setting not found"
        )
    
    body = await request.json()
    new_value = body.get("value")
    
    if new_value is None:
        raise HTTPException(status_code=400, detail="Value is required")
    
    old_data = setting.to_dict()
    setting.setting_value = str(new_value)
    setting.updated_at = datetime.utcnow()
    
    log_staff_audit(
        db, current_user.id, "UPDATE", "setting",
        resource_id=setting.id,
        old_data=old_data,
        new_data=setting.to_dict(),
        ip_address=request.client.host if request.client else None
    )
    
    db.commit()
    
    return {
        "success": True,
        "message": "Setting updated successfully",
        "setting": setting.to_dict()
    }


@router.get("/audit-logs")
async def list_audit_logs(
    resource_type: Optional[str] = None,
    action: Optional[str] = None,
    employee_id: Optional[int] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """
    List audit logs
    DC: Key Leadership/VGK4U only - immutable audit trail
    """
    allowed_roles = ["vgk4u", "key_leadership"]
    if current_user.role.role_code not in allowed_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only VGK4U Supreme or Key Leadership can view audit logs"
        )
    
    query = db.query(StaffAuditLog)
    
    if resource_type:
        query = query.filter(StaffAuditLog.resource_type == resource_type)
    
    if action:
        query = query.filter(StaffAuditLog.action == action)
    
    if employee_id:
        query = query.filter(StaffAuditLog.employee_id == employee_id)
    
    if start_date:
        query = query.filter(StaffAuditLog.timestamp >= datetime.combine(start_date, datetime.min.time()))
    
    if end_date:
        query = query.filter(StaffAuditLog.timestamp <= datetime.combine(end_date, datetime.max.time()))
    
    total = query.count()
    
    logs = query.order_by(StaffAuditLog.timestamp.desc())\
                .offset((page - 1) * limit)\
                .limit(limit)\
                .all()
    
    return {
        "success": True,
        "logs": [log.to_dict() for log in logs],
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total,
            "pages": (total + limit - 1) // limit
        }
    }


# ============= KYC API ENDPOINTS =============

class KYCSubmitRequest(BaseModel):
    """KYC submission request - matches MNR user profile structure"""
    # Profile Photo
    profile_photo: Optional[str] = None
    
    # Personal Details
    father_name: Optional[str] = None
    mother_name: Optional[str] = None
    spouse_name: Optional[str] = None
    date_of_birth: Optional[date] = None
    gender: Optional[str] = None
    blood_group: Optional[str] = None
    marital_status: Optional[str] = None
    nationality: Optional[str] = None
    religion: Optional[str] = None
    
    # Educational Qualification
    highest_qualification: Optional[str] = None
    specialization: Optional[str] = None
    institution_name: Optional[str] = None
    year_of_passing: Optional[int] = None
    
    # Previous Employment
    previous_company: Optional[str] = None
    previous_designation: Optional[str] = None
    previous_experience_years: Optional[int] = None
    
    # Address - Permanent
    permanent_address_line1: Optional[str] = None
    permanent_address_line2: Optional[str] = None
    permanent_city: Optional[str] = None
    permanent_state: Optional[str] = None
    permanent_pincode: Optional[str] = None
    permanent_country: Optional[str] = None
    
    # Address - Current
    current_address_line1: Optional[str] = None
    current_address_line2: Optional[str] = None
    current_city: Optional[str] = None
    current_state: Optional[str] = None
    current_pincode: Optional[str] = None
    current_country: Optional[str] = None
    same_as_permanent: Optional[bool] = None
    
    # Legacy address (backward compatibility)
    permanent_address: Optional[str] = None
    current_address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None
    
    # Identity Documents
    aadhar_number: Optional[str] = None
    pan_number: Optional[str] = None
    passport_number: Optional[str] = None
    passport_expiry: Optional[date] = None
    driving_license: Optional[str] = None
    dl_expiry: Optional[date] = None
    voter_id: Optional[str] = None
    
    # Bank Details
    bank_account_holder: Optional[str] = None
    bank_name: Optional[str] = None
    bank_branch: Optional[str] = None
    account_number: Optional[str] = None
    ifsc_code: Optional[str] = None
    account_type: Optional[str] = None
    upi_id: Optional[str] = None
    
    # Emergency Contact
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    emergency_contact_relation: Optional[str] = None
    emergency_contact_address: Optional[str] = None
    
    # Nominee Details
    nominee_name: Optional[str] = None
    nominee_relationship: Optional[str] = None
    nominee_dob: Optional[date] = None
    nominee_phone: Optional[str] = None
    nominee_address: Optional[str] = None


@router.get("/kyc/my")
async def get_my_kyc(
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """
    Get current employee's KYC record
    DC: Self-service KYC access
    """
    kyc = db.query(StaffEmployeeKyc).filter_by(employee_id=current_user.id).first()
    
    return {
        "success": True,
        "kyc": kyc.to_dict() if kyc else None,
        "employee": {
            "id": current_user.id,
            "emp_code": current_user.emp_code,
            "full_name": current_user.full_name,
            "email": current_user.email,
            "phone": current_user.phone,
            "kyc_status": current_user.kyc_status,
            "is_experienced": current_user.is_experienced  # DC Protocol (Jan 2026)
        }
    }


@router.post("/kyc/my")
async def submit_my_kyc(
    data: KYCSubmitRequest = Body(...),
    request: Request = None,
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """
    Submit or update own KYC
    DC: Self-service KYC submission
    ENHANCED: Allows editing approved KYC - triggers re-approval workflow
    """
    # Check if KYC already exists
    kyc = db.query(StaffEmployeeKyc).filter_by(employee_id=current_user.id).first()
    
    is_resubmission = False
    old_data = None
    
    # Track if this is a resubmission of approved KYC
    if kyc and kyc.status == 'approved':
        is_resubmission = True
        old_data = {
            "previous_status": kyc.status,
            "approved_by": kyc.reviewed_by,
            "approved_at": str(kyc.reviewed_at) if kyc.reviewed_at else None
        }
    
    if not kyc:
        kyc = StaffEmployeeKyc(employee_id=current_user.id)
        db.add(kyc)
    
    # Update KYC fields
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(kyc, field, value)
    
    # Reset status to 'submitted' for approval (resubmit flow)
    kyc.status = 'submitted'
    kyc.submitted_at = datetime.utcnow()
    kyc.rejection_reason = None  # Clear previous rejection
    
    # Clear previous approval info on resubmission
    if is_resubmission:
        kyc.reviewed_by = None
        kyc.reviewed_at = None
    
    # Update employee's kyc_status
    current_user.kyc_status = 'submitted'
    
    # Audit log with resubmission tracking
    action = "KYC_RESUBMIT" if is_resubmission else "KYC_SUBMIT"
    log_staff_audit(
        db, current_user.id, action, "kyc",
        resource_id=kyc.id if kyc.id else None,
        old_data=old_data,
        new_data={"status": "submitted", "is_resubmission": is_resubmission},
        ip_address=request.client.host if request.client else None
    )
    
    db.commit()
    db.refresh(kyc)
    
    message = "KYC resubmitted successfully. Pending re-approval." if is_resubmission else "KYC submitted successfully. Pending approval."
    
    return {
        "success": True,
        "message": message,
        "kyc": kyc.to_dict()
    }


# NOTE: KYC_APPROVAL_ROLES is defined at the top of this file (includes vgk4u)


@router.get("/kyc/pending")
async def list_pending_kyc(
    status_filter: Optional[str] = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """
    List KYC records pending approval
    DC: VGK4U Supreme, Key Leadership, Leadership (Admin), and HR roles
    """
    # DC Protocol: Menu-based access control - page assignment = full access
    role_code = current_user.role.role_code.lower() if current_user.role and current_user.role.role_code else None
    # if role_code not in KYC_APPROVAL_ROLES:
    #     raise HTTPException(
    #         status_code=status.HTTP_403_FORBIDDEN,
    #         detail="Only VGK4U Supreme, Key Leadership, Admin, or HR can access KYC approvals"
    #     )
    
    query = db.query(StaffEmployeeKyc)
    
    # Handle status filter - filter by specific status if provided, otherwise show all
    if status_filter and status_filter.strip():
        query = query.filter(StaffEmployeeKyc.status == status_filter)
    # If no status parameter (None) or empty string "", show all records (no filter applied)
    
    total = query.count()
    
    records = query.order_by(StaffEmployeeKyc.submitted_at.desc())\
                   .offset((page - 1) * limit)\
                   .limit(limit)\
                   .all()
    
    return {
        "success": True,
        "kyc_records": [r.to_dict() for r in records],
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total,
            "pages": (total + limit - 1) // limit
        },
        "stats": {
            "pending": db.query(StaffEmployeeKyc).filter_by(status='submitted').count(),
            "approved": db.query(StaffEmployeeKyc).filter_by(status='approved').count(),
            "rejected": db.query(StaffEmployeeKyc).filter_by(status='rejected').count()
        }
    }


@router.get("/kyc/documents")
async def get_my_kyc_documents(
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """
    Get list of uploaded KYC documents for current user
    DC: Self-service document listing
    IMPORTANT: This route must be defined before /kyc/{kyc_id} to avoid path parameter matching
    """
    kyc = db.query(StaffEmployeeKyc).filter_by(employee_id=current_user.id).first()
    
    if not kyc or not kyc.documents:
        return {
            "success": True,
            "documents": [],
            "kyc_status": current_user.kyc_status
        }
    
    # Build document list with URLs
    documents = []
    for doc_type, doc_info in kyc.documents.items():
        documents.append({
            "type": doc_type,
            "label": doc_type.replace('_', ' ').title(),
            "file_name": doc_info.get('file_name'),
            "original_name": doc_info.get('original_name'),
            "file_size": doc_info.get('file_size'),
            "file_format": doc_info.get('file_format'),
            "uploaded_at": doc_info.get('uploaded_at'),
            "url": f"/api/v1/staff/kyc/document/{current_user.emp_code}/{doc_info.get('file_name')}"
        })
    
    return {
        "success": True,
        "documents": documents,
        "kyc_status": current_user.kyc_status,
        "document_requirements": {
            "profile_photo": {"max_size_kb": 500, "formats": ["JPG", "PNG"]},
            "kyc_documents": {"max_size_kb": 1024, "formats": ["JPG", "PNG", "PDF"]}
        }
    }


@router.get("/kyc/{kyc_id}")
async def get_kyc_details(
    kyc_id: int,
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """
    Get KYC record details
    DC: Own record or VGK4U/Key Leadership access
    """
    kyc = db.query(StaffEmployeeKyc).filter_by(id=kyc_id).first()
    
    if not kyc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="KYC record not found"
        )
    
    # Check access - own record or approver role (includes VGK4U Supreme)
    is_own = kyc.employee_id == current_user.id
    role_code = current_user.role.role_code.lower() if current_user.role and current_user.role.role_code else None
    is_approver = role_code in KYC_APPROVAL_ROLES
    
    if not is_own and not is_approver:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    # Include employee details
    employee = db.query(StaffEmployee).filter_by(id=kyc.employee_id).first()
    
    return {
        "success": True,
        "kyc": kyc.to_dict(),
        "employee": employee.to_dict() if employee else None
    }


@router.post("/kyc/{kyc_id}/approve")
async def approve_kyc(
    request: Request,
    kyc_id: int,
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """
    Approve KYC submission
    DC: VGK4U Supreme, Key Leadership, Admin, and HR roles
    """
    role_code = current_user.role.role_code.lower() if current_user.role and current_user.role.role_code else None
    # DC Protocol: Menu-based access control - page assignment = full access
    # if role_code not in KYC_APPROVAL_ROLES:
    #     raise HTTPException(
    #         status_code=status.HTTP_403_FORBIDDEN,
    #         detail="Only VGK4U Supreme, Key Leadership, Admin, or HR can approve KYC"
    #     )
    
    kyc = db.query(StaffEmployeeKyc).filter_by(id=kyc_id).first()
    
    if not kyc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="KYC record not found"
        )
    
    if kyc.status != 'submitted':
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot approve KYC with status: {kyc.status}"
        )
    
    old_status = kyc.status
    kyc.status = 'approved'
    kyc.reviewed_by = current_user.id
    kyc.reviewed_at = datetime.utcnow()
    kyc.rejection_reason = None
    
    # Update employee's kyc_status
    employee = db.query(StaffEmployee).filter_by(id=kyc.employee_id).first()
    if employee:
        employee.kyc_status = 'approved'
    
    log_staff_audit(
        db, current_user.id, "KYC_APPROVE", "kyc",
        resource_id=kyc.id,
        old_data={"status": old_status},
        new_data={"status": "approved"},
        ip_address=request.client.host if request.client else None
    )
    
    db.commit()
    
    return {
        "success": True,
        "message": f"KYC approved for {employee.full_name if employee else 'employee'}",
        "kyc": kyc.to_dict()
    }


@router.post("/kyc/{kyc_id}/reject")
async def reject_kyc(
    request: Request,
    kyc_id: int,
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """
    Reject KYC submission
    DC: VGK4U Supreme, Key Leadership, Admin, and HR roles
    """
    role_code = current_user.role.role_code.lower() if current_user.role and current_user.role.role_code else None
    # DC Protocol: Menu-based access control - page assignment = full access
    # if role_code not in KYC_APPROVAL_ROLES:
    #     raise HTTPException(
    #         status_code=status.HTTP_403_FORBIDDEN,
    #         detail="Only VGK4U Supreme, Key Leadership, Admin, or HR can reject KYC"
    #     )
    
    kyc = db.query(StaffEmployeeKyc).filter_by(id=kyc_id).first()
    
    if not kyc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="KYC record not found"
        )
    
    if kyc.status not in ['submitted', 'approved']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot reject KYC with status: {kyc.status}"
        )
    
    # Get rejection reason from request body
    body = await request.json()
    reason = body.get("reason", "No reason provided")
    
    old_status = kyc.status
    kyc.status = 'rejected'
    kyc.reviewed_by = current_user.id
    kyc.reviewed_at = datetime.utcnow()
    kyc.rejection_reason = reason
    
    # Update employee's kyc_status
    employee = db.query(StaffEmployee).filter_by(id=kyc.employee_id).first()
    if employee:
        employee.kyc_status = 'rejected'
    
    log_staff_audit(
        db, current_user.id, "KYC_REJECT", "kyc",
        resource_id=kyc.id,
        old_data={"status": old_status},
        new_data={"status": "rejected", "reason": reason},
        ip_address=request.client.host if request.client else None
    )
    
    db.commit()
    
    return {
        "success": True,
        "message": f"KYC rejected for {employee.full_name if employee else 'employee'}",
        "kyc": kyc.to_dict()
    }


# ============= KYC DOCUMENT UPLOAD ENDPOINTS (MNR Standard) =============

def validate_file_size(file: UploadFile, max_size: int, file_type: str):
    """Validate file size - MNR standard"""
    file.file.seek(0, 2)
    file_size = file.file.tell()
    file.file.seek(0)
    
    if file_size > max_size:
        max_kb = max_size / 1024
        raise HTTPException(
            status_code=400,
            detail=f"{file_type} exceeds maximum size of {max_kb:.0f} KB"
        )
    return file_size


def validate_file_format(filename: str, allowed_formats: set) -> str:
    """Validate file format - MNR standard"""
    ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
    
    if ext not in allowed_formats:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file format. Allowed: {', '.join(allowed_formats).upper()}"
        )
    return ext


@router.post("/kyc/upload-document")
async def upload_kyc_document(
    request: Request,
    document_type: str = Form(...),
    file: UploadFile = File(...),
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """
    Upload KYC document
    DC: Self-service document upload with size/format validation
    
    File Size Limits (MNR Standard):
    - Profile Photo: Max 500 KB, Formats: JPG, PNG
    - KYC Documents: Max 1 MB, Formats: JPG, PNG, PDF
    
    Document Types:
    - profile_photo, aadhaar_front, aadhaar_back, pan_card
    - passport, driving_license, voter_id
    - bank_passbook, cancelled_cheque
    """
    # Validate document type
    if document_type not in VALID_DOCUMENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid document type. Valid types: {', '.join(VALID_DOCUMENT_TYPES)}"
        )
    
    # Get or create KYC record
    kyc = db.query(StaffEmployeeKyc).filter_by(employee_id=current_user.id).first()
    
    # Track if this is a modification of approved KYC (for auto-resubmission)
    is_approved_edit = kyc and kyc.status == 'approved'
    old_approval_data = None
    if is_approved_edit:
        old_approval_data = {
            "previous_status": kyc.status,
            "approved_by": kyc.reviewed_by,
            "approved_at": str(kyc.reviewed_at) if kyc.reviewed_at else None
        }
    
    if not kyc:
        kyc = StaffEmployeeKyc(employee_id=current_user.id)
        db.add(kyc)
        db.flush()
    
    # Set file restrictions based on document type
    # DC: Profile photo and passport photo are formal photos - 500KB max, images only
    if document_type in ['profile_photo', 'passport_photo']:
        max_size = PROFILE_PHOTO_MAX_SIZE
        allowed_formats = IMAGE_FORMATS
        file_type_label = "Photo"
    else:
        max_size = KYC_DOCUMENT_MAX_SIZE
        allowed_formats = DOCUMENT_FORMATS
        file_type_label = "Document"
    
    # DC Protocol: Validate file size BEFORE creating DB records (prevent orphan records)
    file_content = await file.read()
    actual_file_size = len(file_content)
    file.file.seek(0)  # Reset for UniversalUploadService (synchronous seek for SpooledTemporaryFile)
    
    if actual_file_size == 0:
        raise HTTPException(status_code=400, detail="File is empty")
    
    # Universal Upload System: 5MB limit for images/documents
    MAX_UPLOAD_SIZE = 5000000  # 5MB (will be auto-compressed)
    if actual_file_size > MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File size ({round(actual_file_size/1024, 2)}KB) exceeds maximum allowed size (5MB). File will be automatically compressed after upload."
        )
    
    # Validate format (keep existing validation)
    ext = validate_file_format(file.filename, allowed_formats)
    
    # Universal Upload System: DC Protocol atomic transaction
    from app.services.universal_upload_service import UniversalUploadService
    
    upload_result = None
    try:
        # Upload file using Universal Upload System
        # DC Protocol: defer_scheduler=True ensures compression job only scheduled AFTER db.commit()
        upload_result = await UniversalUploadService.handle_upload(
            file=file,
            table_name='staff_employee_kyc',
            record_id=kyc.id,
            uploaded_by_id=current_user.id,
            uploaded_by_type='staff',
            storage_dir=f'staff_kyc/{current_user.emp_code}',
            db=db,
            mnr_id=None,  # Staff system doesn't use MNR IDs
            defer_scheduler=True  # DC: Transaction safety - schedule job AFTER commit
        )
        
        # Update documents JSON (maintain backward compatibility)
        if not kyc.documents:
            kyc.documents = {}
        
        kyc.documents[document_type] = {
            'file_path': upload_result['file_path'],
            'file_name': upload_result['file_name'],
            'original_name': file.filename,
            'file_size': actual_file_size,
            'file_format': ext,
            'uploaded_at': datetime.utcnow().isoformat()
        }
        
        # DC PROTOCOL: Generate semantic download filename (NEW - Nov 29, 2025)
        try:
            import pytz
            
            ist_tz = pytz.timezone('Asia/Kolkata')
            uploaded_at_ist = datetime.now(ist_tz)
            
            download_name = UniversalUploadService.generate_download_filename(
                segment_key='staff_kyc',
                entity_type='staff',
                entity_id=current_user.id,
                attachment_id=kyc.id,
                uploader_code=current_user.emp_code,
                original_filename=file.filename,
                uploaded_at=uploaded_at_ist
            )
            
            kyc.download_filename = download_name
            kyc.uses_new_naming = True
        except HTTPException:
            raise
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Failed to generate download filename for staff KYC {kyc.id}: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Failed to generate semantic filename: {str(e)}")
        
        # Special handling for profile_photo - also update the profile_photo column
        if document_type == 'profile_photo':
            # Use the uploaded file path (will serve compressed version)
            kyc.profile_photo = f"/api/v1/staff/kyc/document/{current_user.emp_code}/{upload_result['file_name']}"
        
        # DC Protocol (Jan 2026): Handle Previous Experience Documents
        # Store in dedicated URL columns for easy validation
        experience_doc_url = f"/api/v1/staff/kyc/document/{current_user.emp_code}/{upload_result['file_name']}"
        if document_type == 'bank_statement_1':
            kyc.bank_statement_1_url = experience_doc_url
        elif document_type == 'bank_statement_2':
            kyc.bank_statement_2_url = experience_doc_url
        elif document_type == 'bank_statement_3':
            kyc.bank_statement_3_url = experience_doc_url
        elif document_type == 'offer_letter':
            kyc.offer_letter_url = experience_doc_url
        elif document_type == 'pay_slip_1':
            kyc.pay_slip_1_url = experience_doc_url
        elif document_type == 'pay_slip_2':
            kyc.pay_slip_2_url = experience_doc_url
        elif document_type == 'pay_slip_3':
            kyc.pay_slip_3_url = experience_doc_url
        
        # Auto-update experience_docs_status when all 7 docs are uploaded
        if document_type in EXPERIENCE_DOCUMENT_TYPES:
            all_experience_docs = [
                kyc.bank_statement_1_url, kyc.bank_statement_2_url, kyc.bank_statement_3_url,
                kyc.offer_letter_url,
                kyc.pay_slip_1_url, kyc.pay_slip_2_url, kyc.pay_slip_3_url
            ]
            if all(doc for doc in all_experience_docs):
                kyc.experience_docs_status = 'submitted'
        
    except HTTPException as e:
        raise e
    except Exception as upload_error:
        # DC Protocol: If upload fails, transaction will rollback
        raise HTTPException(
            status_code=400,
            detail=f"Failed to upload document: {str(upload_error)}"
        )
    
    # Mark documents as modified (for SQLAlchemy to detect change)
    from sqlalchemy.orm.attributes import flag_modified
    flag_modified(kyc, 'documents')
    
    # DC: Auto-resubmission for approved KYC edits
    # When approved KYC is modified, reset status to 'submitted' for re-approval
    resubmission_message = ""
    if is_approved_edit:
        kyc.status = 'submitted'
        kyc.submitted_at = datetime.utcnow()
        kyc.reviewed_by = None
        kyc.reviewed_at = None
        kyc.rejection_reason = None
        resubmission_message = " KYC has been resubmitted for approval."
        
        # Update employee's kyc_status
        current_user.kyc_status = 'submitted'
        
        log_staff_audit(
            db, current_user.id, "KYC_RESUBMIT", "kyc",
            resource_id=kyc.id,
            old_data=old_approval_data,
            new_data={"document_type": document_type, "action": "document_upload_resubmit"},
            ip_address=request.client.host if request.client else None
        )
    
    # DC Protocol: Log audit in SAME transaction
    log_staff_audit(
        db, current_user.id, "KYC_UPLOAD", "kyc_document",
        resource_id=kyc.id,
        new_data={"document_type": document_type, "file_name": upload_result['file_name']},
        ip_address=request.client.host if request.client else None
    )
    
    # DC Protocol: Single commit for ALL changes (atomic operation)
    # PostCommitScheduler will automatically enqueue deferred jobs AFTER this commit
    db.commit()
    
    return {
        "success": True,
        "message": f"{document_type.replace('_', ' ').title()} uploaded successfully.{resubmission_message}",
        "document": {
            "type": document_type,
            "file_name": upload_result['file_name'],
            "file_size": actual_file_size,
            "file_format": ext,
            "url": f"/api/v1/staff/kyc/document/{current_user.emp_code}/{upload_result['file_name']}"
        }
    }


@router.get("/kyc/document/{emp_code}/{filename}")
async def get_kyc_document(
    emp_code: str,
    filename: str,
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """
    Serve KYC document file
    DC: Access control - own documents or VGK4U/Key Leadership/HR
    """
    # Check access permissions (VGK4U Supreme has access to all documents)
    is_own = current_user.emp_code == emp_code
    role_code = current_user.role.role_code.lower() if current_user.role and current_user.role.role_code else None
    is_approver = role_code in KYC_APPROVAL_ROLES
    
    if not is_own and not is_approver:
        raise HTTPException(
            status_code=403,
            detail="Access denied. You can only view your own documents."
        )
    
    # Build file path
    file_path = STAFF_KYC_UPLOAD_DIR / emp_code / filename
    
    if not file_path.exists():
        raise HTTPException(
            status_code=404,
            detail="Document not found"
        )
    
    # Determine content type
    ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
    content_types = {
        'jpg': 'image/jpeg',
        'jpeg': 'image/jpeg',
        'png': 'image/png',
        'pdf': 'application/pdf'
    }
    media_type = content_types.get(ext, 'application/octet-stream')
    
    return FileResponse(
        path=str(file_path),
        media_type=media_type,
        filename=filename
    )


@router.delete("/kyc/document/{document_type}")
async def delete_kyc_document(
    request: Request,
    document_type: str,
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """
    Delete KYC document
    DC: Self-service document deletion (before approval)
    """
    if document_type not in VALID_DOCUMENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid document type"
        )
    
    kyc = db.query(StaffEmployeeKyc).filter_by(employee_id=current_user.id).first()
    
    if not kyc:
        raise HTTPException(
            status_code=404,
            detail="KYC record not found"
        )
    
    # Track if this is a modification of approved KYC (for auto-resubmission)
    is_approved_edit = kyc.status == 'approved'
    old_approval_data = None
    if is_approved_edit:
        old_approval_data = {
            "previous_status": kyc.status,
            "approved_by": kyc.reviewed_by,
            "approved_at": str(kyc.reviewed_at) if kyc.reviewed_at else None
        }
    
    if not kyc.documents or document_type not in kyc.documents:
        raise HTTPException(
            status_code=404,
            detail="Document not found"
        )
    
    # Delete physical file
    doc_info = kyc.documents[document_type]
    file_path = doc_info.get('file_path')
    if file_path and os.path.exists(file_path):
        try:
            os.remove(file_path)
        except:
            pass
    
    # Remove from documents JSON
    del kyc.documents[document_type]
    
    # Clear profile_photo if that was deleted
    if document_type == 'profile_photo':
        kyc.profile_photo = None
    
    from sqlalchemy.orm.attributes import flag_modified
    flag_modified(kyc, 'documents')
    
    # DC: Auto-resubmission for approved KYC edits
    resubmission_message = ""
    if is_approved_edit:
        kyc.status = 'submitted'
        kyc.submitted_at = datetime.utcnow()
        kyc.reviewed_by = None
        kyc.reviewed_at = None
        kyc.rejection_reason = None
        resubmission_message = " KYC has been resubmitted for approval."
        
        # Update employee's kyc_status
        current_user.kyc_status = 'submitted'
        
        log_staff_audit(
            db, current_user.id, "KYC_RESUBMIT", "kyc",
            resource_id=kyc.id,
            old_data=old_approval_data,
            new_data={"document_type": document_type, "action": "document_delete_resubmit"},
            ip_address=request.client.host if request.client else None
        )
    
    log_staff_audit(
        db, current_user.id, "KYC_DELETE_DOC", "kyc_document",
        resource_id=kyc.id,
        old_data={"document_type": document_type},
        ip_address=request.client.host if request.client else None
    )
    
    db.commit()
    
    return {
        "success": True,
        "message": f"{document_type.replace('_', ' ').title()} deleted successfully.{resubmission_message}"
    }


# ============================================================================
# SOFT DELETE & RESTORE ENDPOINTS (Dec 2025)
# DC Protocol: VGK Supreme only - with restore capability
# ============================================================================

# Roles that can delete employees (VGK4U Supreme only)
DELETE_ROLES = ["vgk4u"]

@router.delete("/employees/{employee_id}/soft")
async def soft_delete_employee(
    employee_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    DC Protocol: Soft delete employee with cascade (VGK Supreme only)
    - Marks employee as deleted (is_deleted=True)
    - Related records remain but filtered out in queries
    - Can be restored via restore endpoint
    - Protected account MR10001 cannot be deleted
    - URL: DELETE /api/v1/staff/employees/{id}/soft
    """
    role_code = current_user.role.role_code.lower() if current_user.role else ""
    
    if role_code not in DELETE_ROLES:
        raise HTTPException(
            status_code=403,
            detail="Only VGK4U Supreme can delete employees"
        )
    
    # Find employee
    employee = db.query(StaffEmployee).filter(
        StaffEmployee.id == employee_id,
        StaffEmployee.is_deleted.isnot(True)
    ).first()
    
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    # Protect MR10001 (VGK4U Admin)
    if employee.emp_code == "MR10001":
        raise HTTPException(
            status_code=403,
            detail="Protected account MR10001 cannot be deleted"
        )
    
    # Cannot delete yourself
    if employee.id == current_user.id:
        raise HTTPException(
            status_code=403,
            detail="You cannot delete your own account"
        )
    
    try:
        # Get counts of related records for audit
        # DC Protocol: Import from correct model files
        from app.models.staff_attendance import (
            StaffAttendance, StaffAttendanceBreak, StaffAttendanceEvidence
        )
        from app.models.staff_tasks import StaffTask
        from app.models.staff_journey import StaffJourney
        from app.models.staff import StaffEmployeeKyc, StaffAuditLog
        
        attendance_count = db.query(StaffAttendance).filter(
            StaffAttendance.employee_id == employee_id
        ).count()
        
        task_count = db.query(StaffTask).filter(
            StaffTask.created_by == employee_id
        ).count()
        
        journey_count = db.query(StaffJourney).filter(
            StaffJourney.employee_id == employee_id
        ).count()
        
        kyc_count = db.query(StaffEmployeeKyc).filter(
            StaffEmployeeKyc.employee_id == employee_id
        ).count()
        
        # Perform soft delete
        now = get_indian_time()
        employee.is_deleted = True
        employee.deleted_at = now
        employee.deleted_by = current_user.id
        employee.status = 'terminated'  # Also mark as terminated
        
        # Log the deletion
        log_staff_audit(
            db, current_user.id, "EMPLOYEE_SOFT_DELETE", "staff_employees",
            resource_id=employee_id,
            old_data={
                "emp_code": employee.emp_code,
                "full_name": employee.full_name,
                "status": "active"
            },
            new_data={
                "is_deleted": True,
                "deleted_at": str(now),
                "deleted_by": current_user.id,
                "related_counts": {
                    "attendance": attendance_count,
                    "tasks": task_count,
                    "journeys": journey_count,
                    "kyc": kyc_count
                }
            },
            ip_address=request.client.host if request.client else None
        )
        
        db.commit()
        
        return {
            "success": True,
            "message": f"Employee {employee.emp_code} ({employee.full_name}) deleted successfully",
            "deleted_id": employee_id,
            "related_records": {
                "attendance": attendance_count,
                "tasks": task_count,
                "journeys": journey_count,
                "kyc": kyc_count
            }
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete employee: {str(e)}"
        )


@router.post("/employees/{employee_id}/restore")
async def restore_employee(
    employee_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    DC Protocol: Restore soft-deleted employee (VGK Supreme only)
    """
    role_code = current_user.role.role_code.lower() if current_user.role else ""
    
    if role_code not in DELETE_ROLES:
        raise HTTPException(
            status_code=403,
            detail="Only VGK4U Supreme can restore employees"
        )
    
    # Find deleted employee
    employee = db.query(StaffEmployee).filter(
        StaffEmployee.id == employee_id,
        StaffEmployee.is_deleted == True
    ).first()
    
    if not employee:
        raise HTTPException(status_code=404, detail="Deleted employee not found")
    
    try:
        # Restore employee
        old_deleted_at = employee.deleted_at
        old_deleted_by = employee.deleted_by
        
        employee.is_deleted = False
        employee.deleted_at = None
        employee.deleted_by = None
        employee.status = 'active'
        
        # Log the restoration
        log_staff_audit(
            db, current_user.id, "EMPLOYEE_RESTORE", "staff_employees",
            resource_id=employee_id,
            old_data={
                "is_deleted": True,
                "deleted_at": str(old_deleted_at),
                "deleted_by": old_deleted_by
            },
            new_data={
                "is_deleted": False,
                "status": "active"
            },
            ip_address=request.client.host if request.client else None
        )
        
        db.commit()
        
        return {
            "success": True,
            "message": f"Employee {employee.emp_code} ({employee.full_name}) restored successfully",
            "restored_id": employee_id
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to restore employee: {str(e)}"
        )


@router.get("/employees/deleted")
async def list_deleted_employees(
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    DC Protocol: List all soft-deleted employees (VGK Supreme only)
    """
    role_code = current_user.role.role_code.lower() if current_user.role else ""
    
    if role_code not in DELETE_ROLES:
        raise HTTPException(
            status_code=403,
            detail="Only VGK4U Supreme can view deleted employees"
        )
    
    deleted_employees = db.query(StaffEmployee).filter(
        StaffEmployee.is_deleted == True
    ).order_by(StaffEmployee.deleted_at.desc()).all()
    
    return {
        "success": True,
        "count": len(deleted_employees),
        "employees": [
            {
                "id": emp.id,
                "emp_code": emp.emp_code,
                "full_name": emp.full_name,
                "designation": emp.designation,
                "deleted_at": emp.deleted_at.isoformat() if emp.deleted_at else None,
                "deleted_by": emp.deleted_by
            }
            for emp in deleted_employees
        ]
    }


@router.delete("/employees/{employee_id}/hard")
async def hard_delete_employee(
    employee_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    DC Protocol: HARD DELETE employee (VGK Supreme only)
    - PERMANENTLY removes employee and ALL related records
    - CANNOT be restored - use with caution
    - Protected account MR10001 cannot be deleted
    """
    role_code = current_user.role.role_code.lower() if current_user.role else ""
    
    if role_code not in DELETE_ROLES:
        raise HTTPException(
            status_code=403,
            detail="Only VGK4U Supreme can permanently delete employees"
        )
    
    # Find employee (including soft-deleted ones)
    employee = db.query(StaffEmployee).filter(
        StaffEmployee.id == employee_id
    ).first()
    
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    # Protect MR10001 (VGK4U Admin)
    if employee.emp_code == "MR10001":
        raise HTTPException(
            status_code=403,
            detail="Protected account MR10001 cannot be deleted"
        )
    
    # Cannot delete yourself
    if employee.id == current_user.id:
        raise HTTPException(
            status_code=403,
            detail="You cannot delete your own account"
        )
    
    try:
        # DC Protocol: Import from correct model files
        from app.models.staff_attendance import (
            StaffAttendance, StaffAttendanceBreak, StaffAttendanceEvidence
        )
        from app.models.staff_tasks import (
            StaffTask, StaffTaskAttachment, StaffTaskAttachmentAudit,
            StaffTaskComment, StaffTaskTimeEntry
        )
        from app.models.staff_journey import StaffJourney
        from app.models.staff_kra import StaffKRAAssignment, StaffKRATemplate
        from app.models.staff import (
            StaffEmployeeKyc, StaffAuditLog, StaffEmployeeDepartment, StaffNdaAcceptance
        )
        
        # DC Protocol: PRE-DELETE GUARDS - Block deletion if NOT NULL FK references exist
        # These tables have ON DELETE SET NULL but NOT NULL constraint = would cause 500 error
        blocking_dependencies = []
        
        # Check tasks created by this employee (staff_tasks.created_by is NOT NULL)
        tasks_created = db.query(StaffTask).filter(StaffTask.created_by == employee_id).count()
        if tasks_created > 0:
            blocking_dependencies.append(f"Created {tasks_created} task(s)")
        
        # Check tasks where this employee is primary assignee (staff_tasks.primary_assignee_id is NOT NULL)
        tasks_assigned = db.query(StaffTask).filter(StaffTask.primary_assignee_id == employee_id).count()
        if tasks_assigned > 0:
            blocking_dependencies.append(f"Primary assignee on {tasks_assigned} task(s)")
        
        # Check KRA assignments where this employee is primary SPOC
        kra_spoc = db.query(StaffKRAAssignment).filter(
            StaffKRAAssignment.primary_spoc_employee_id == employee_id
        ).count()
        if kra_spoc > 0:
            blocking_dependencies.append(f"Primary SPOC on {kra_spoc} KRA assignment(s)")
        
        # Check KRA assignments where this employee assigned them
        kra_assigned_by = db.query(StaffKRAAssignment).filter(
            StaffKRAAssignment.assigned_by_employee_id == employee_id
        ).count()
        if kra_assigned_by > 0:
            blocking_dependencies.append(f"Assigned {kra_assigned_by} KRA assignment(s)")
        
        # Check KRA templates created by this employee
        kra_templates = db.query(StaffKRATemplate).filter(
            StaffKRATemplate.created_by_employee_id == employee_id
        ).count()
        if kra_templates > 0:
            blocking_dependencies.append(f"Created {kra_templates} KRA template(s)")
        
        # Check task attachments uploaded by this employee
        attachments = db.query(StaffTaskAttachment).filter(
            StaffTaskAttachment.uploaded_by == employee_id
        ).count()
        if attachments > 0:
            blocking_dependencies.append(f"Uploaded {attachments} task attachment(s)")
        
        # Check task attachment audits by this employee
        attachment_audits = db.query(StaffTaskAttachmentAudit).filter(
            StaffTaskAttachmentAudit.uploaded_by == employee_id
        ).count()
        if attachment_audits > 0:
            blocking_dependencies.append(f"Has {attachment_audits} attachment audit record(s)")
        
        # Check task comments by this employee
        comments = db.query(StaffTaskComment).filter(
            StaffTaskComment.employee_id == employee_id
        ).count()
        if comments > 0:
            blocking_dependencies.append(f"Created {comments} task comment(s)")
        
        # Check task time entries by this employee
        time_entries = db.query(StaffTaskTimeEntry).filter(
            StaffTaskTimeEntry.employee_id == employee_id
        ).count()
        if time_entries > 0:
            blocking_dependencies.append(f"Has {time_entries} time tracking entry(ies)")

        # DC Protocol (Feb 2026): Check financial/HR records — these cannot be auto-deleted
        # Confirmed via DB schema inspection: these tables have NOT NULL FKs to staff_employees
        from sqlalchemy import text as _sqla_text
        _eid_p = {"id": employee_id}

        _inv = db.execute(_sqla_text("SELECT COUNT(*) FROM staff_consultant_invoice WHERE employee_id = :id"), _eid_p).scalar() or 0
        if _inv > 0:
            blocking_dependencies.append(f"Has {_inv} consultant invoice(s) — reassign or archive first")

        _lb = db.execute(_sqla_text("SELECT COUNT(*) FROM staff_leave_balances WHERE employee_id = :id"), _eid_p).scalar() or 0
        if _lb > 0:
            blocking_dependencies.append(f"Has leave balance records ({_lb}) — clear balances first")

        _lr = db.execute(_sqla_text("SELECT COUNT(*) FROM staff_leave_requests WHERE employee_id = :id"), _eid_p).scalar() or 0
        if _lr > 0:
            blocking_dependencies.append(f"Has {_lr} leave request(s) — reassign first")

        _pd = db.execute(_sqla_text("SELECT COUNT(*) FROM staff_payroll_document WHERE employee_id = :id"), _eid_p).scalar() or 0
        if _pd > 0:
            blocking_dependencies.append(f"Has {_pd} payroll document(s) — archive first")

        # If blocking dependencies exist, return informative error
        if blocking_dependencies:
            raise HTTPException(
                status_code=400,
                detail={
                    "message": f"Cannot hard delete employee {employee.emp_code}. Reassign or delete the following records first:",
                    "blocking_dependencies": blocking_dependencies,
                    "recommendation": "Use soft delete (deactivate/resigned) instead, or reassign these records to another employee"
                }
            )
        
        # Store info for audit before deletion
        emp_code = employee.emp_code
        full_name = employee.full_name
        
        # Count related records (non-blocking, can be auto-deleted)
        counts = {
            "attendance": db.query(StaffAttendance).filter(StaffAttendance.employee_id == employee_id).count(),
            "journeys": db.query(StaffJourney).filter(StaffJourney.employee_id == employee_id).count(),
            "kyc": db.query(StaffEmployeeKyc).filter(StaffEmployeeKyc.employee_id == employee_id).count()
        }
        
        # Log the deletion BEFORE deleting (so we have audit trail)
        log_staff_audit(
            db, current_user.id, "EMPLOYEE_HARD_DELETE", "staff_employees",
            resource_id=employee_id,
            old_data={
                "emp_code": emp_code,
                "full_name": full_name,
                "action": "PERMANENT_DELETE"
            },
            new_data={
                "deleted_records": counts
            },
            ip_address=request.client.host if request.client else None
        )
        db.commit()
        
        # Delete related records in correct order (children first)
        # DC Protocol (Jan 2026): Comprehensive cascade delete for all FK references
        
        # Import all required models for cascade delete
        from app.models.staff_journey import StaffJourney, StaffJourneyTrackPoint
        from app.models.staff_timesheet import StaffTimesheetEntry, StaffTimesheetApprovalHistory
        from app.models.staff_payroll import StaffPayrollProfile, StaffPayrollRun
        from app.models.staff import (
            StaffEmployeeModule, StaffEmployeeModuleAudit, 
            StaffEmployeeMenuSettings, StaffMenuSettingsAudit,
            StaffEmployeeStatusHistory
        )
        
        # 1. Delete attendance breaks and evidence
        db.query(StaffAttendanceBreak).filter(
            StaffAttendanceBreak.attendance_id.in_(
                db.query(StaffAttendance.id).filter(StaffAttendance.employee_id == employee_id)
            )
        ).delete(synchronize_session=False)
        
        db.query(StaffAttendanceEvidence).filter(
            StaffAttendanceEvidence.attendance_id.in_(
                db.query(StaffAttendance.id).filter(StaffAttendance.employee_id == employee_id)
            )
        ).delete(synchronize_session=False)
        
        # 2. Delete attendance records
        db.query(StaffAttendance).filter(StaffAttendance.employee_id == employee_id).delete()
        
        # 3. Delete journey track points first, then journeys
        journey_ids = db.query(StaffJourney.id).filter(StaffJourney.employee_id == employee_id).all()
        journey_id_list = [j[0] for j in journey_ids]
        if journey_id_list:
            db.query(StaffJourneyTrackPoint).filter(StaffJourneyTrackPoint.journey_id.in_(journey_id_list)).delete(synchronize_session=False)
        db.query(StaffJourney).filter(StaffJourney.employee_id == employee_id).delete()
        
        # 4. Delete timesheet approval history first, then timesheet entries
        timesheet_ids = db.query(StaffTimesheetEntry.id).filter(StaffTimesheetEntry.employee_id == employee_id).all()
        timesheet_id_list = [t[0] for t in timesheet_ids]
        if timesheet_id_list:
            db.query(StaffTimesheetApprovalHistory).filter(StaffTimesheetApprovalHistory.timesheet_entry_id.in_(timesheet_id_list)).delete(synchronize_session=False)
        db.query(StaffTimesheetEntry).filter(StaffTimesheetEntry.employee_id == employee_id).delete()
        
        # 5. Delete payroll records (profiles, runs)
        db.query(StaffPayrollProfile).filter(StaffPayrollProfile.employee_id == employee_id).delete()
        db.query(StaffPayrollRun).filter(StaffPayrollRun.employee_id == employee_id).delete()
        
        # 6. Delete KYC records
        db.query(StaffEmployeeKyc).filter(StaffEmployeeKyc.employee_id == employee_id).delete()
        
        # 7. Delete department assignments
        db.query(StaffEmployeeDepartment).filter(StaffEmployeeDepartment.employee_id == employee_id).delete()
        
        # 8. Delete NDA acceptances
        db.query(StaffNdaAcceptance).filter(StaffNdaAcceptance.employee_id == employee_id).delete()
        
        # 9. Delete KRA assignments
        db.query(StaffKRAAssignment).filter(StaffKRAAssignment.employee_id == employee_id).delete()
        
        # 10. Delete module assignments and audits
        db.query(StaffEmployeeModuleAudit).filter(StaffEmployeeModuleAudit.employee_id == employee_id).delete()
        db.query(StaffEmployeeModule).filter(StaffEmployeeModule.employee_id == employee_id).delete()
        
        # 11. Delete menu settings and audits
        db.query(StaffMenuSettingsAudit).filter(StaffMenuSettingsAudit.employee_id == employee_id).delete()
        db.query(StaffEmployeeMenuSettings).filter(StaffEmployeeMenuSettings.employee_id == employee_id).delete()
        
        # 12. Delete status history
        db.query(StaffEmployeeStatusHistory).filter(StaffEmployeeStatusHistory.employee_id == employee_id).delete()
        
        # 13. Nullify self-referencing FKs (reporting manager references)
        db.query(StaffEmployee).filter(StaffEmployee.reporting_manager_id == employee_id).update(
            {"reporting_manager_id": None}, synchronize_session=False
        )

        # DC Protocol (Feb 2026): Delete remaining NOT NULL FK references confirmed via DB schema
        # These are operational/tracking tables safe to cascade-delete with the employee
        from sqlalchemy import text as _sqla_text
        _eid_p = {"id": employee_id}
        db.execute(_sqla_text("DELETE FROM staff_activity_time_log WHERE employee_id = :id"), _eid_p)
        db.execute(_sqla_text("DELETE FROM staff_attendance_approvals WHERE employee_id = :id"), _eid_p)
        db.execute(_sqla_text("DELETE FROM staff_attendance_exceptions WHERE employee_id = :id"), _eid_p)
        db.execute(_sqla_text("DELETE FROM staff_attendance_sheets WHERE employee_id = :id"), _eid_p)
        db.execute(_sqla_text("DELETE FROM staff_day_plans WHERE employee_id = :id"), _eid_p)
        db.execute(_sqla_text("DELETE FROM staff_field_work_sessions WHERE employee_id = :id"), _eid_p)
        db.execute(_sqla_text("DELETE FROM staff_kra_daily_instances WHERE employee_id = :id"), _eid_p)
        db.execute(_sqla_text("DELETE FROM staff_kra_performance_summary WHERE employee_id = :id"), _eid_p)
        db.execute(_sqla_text("DELETE FROM staff_location_drift_events WHERE employee_id = :id"), _eid_p)
        db.execute(_sqla_text("DELETE FROM staff_realtime_locations WHERE employee_id = :id"), _eid_p)
        db.execute(_sqla_text("DELETE FROM staff_task_assignees WHERE employee_id = :id"), _eid_p)
        db.execute(_sqla_text("DELETE FROM staff_work_intervals WHERE employee_id = :id"), _eid_p)

        # 14. Finally delete the employee
        db.delete(employee)
        db.commit()
        
        return {
            "success": True,
            "message": f"Employee {emp_code} ({full_name}) permanently deleted",
            "deleted_id": employee_id,
            "can_restore": False,
            "deleted_records": counts
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to hard delete employee: {str(e)}"
        )


# ============= EMPLOYEE STATUS CHANGE ENDPOINTS (Dec 2025) =============
# DC Protocol: Deactivate, Resigned, and Reactivate with full audit trail

@router.patch("/employees/{employee_id}/deactivate")
async def deactivate_employee(
    employee_id: int,
    request_data: EmployeeStatusChangeRequest = Body(...),
    request: Request = None,
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Deactivate an employee (temporary suspension)
    DC Protocol: Blocks login, pauses all trackers, retains data for reactivation
    
    Access: VGK4U Supreme, Key Leadership, HR, EA
    Protected: MR10001 cannot be deactivated
    Hierarchy: Can only deactivate employees with lower hierarchy level
    """
    # Validate confirmation text
    if request_data.confirm_text != "CONFIRM":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please type 'CONFIRM' to proceed with deactivation"
        )
    
    # DC Protocol: Menu-based access control - page assignment = full access
    # if current_user.role.role_code not in STATUS_CHANGE_ROLES:
    #     raise HTTPException(
    #         status_code=status.HTTP_403_FORBIDDEN,
    #         detail=f"Access denied. Required roles: {', '.join(STATUS_CHANGE_ROLES)}"
    #     )
    
    # Find employee
    employee = db.query(StaffEmployee).filter(StaffEmployee.id == employee_id).first()
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee not found"
        )
    
    # Check protected employee
    if employee.emp_code in PROTECTED_EMPLOYEE_CODES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Cannot deactivate protected employee {employee.emp_code}"
        )
    
    # Check hierarchy (cannot deactivate same or higher level)
    if current_user.role.hierarchy_level <= employee.role.hierarchy_level and current_user.id != employee.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot deactivate employee with same or higher hierarchy level"
        )
    
    # Cannot self-deactivate
    if current_user.id == employee_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot deactivate your own account"
        )
    
    # Check current status
    if employee.status == 'deactivated':
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Employee is already deactivated"
        )
    
    if employee.status == 'resigned':
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot deactivate a resigned employee. Status is permanent."
        )
    
    try:
        previous_status = employee.status
        
        # Log status change in history table (before updating employee)
        log_staff_status_change(
            db=db,
            employee=employee,
            new_status='deactivated',
            changed_by=current_user,
            reason=request_data.reason,
            notes=request_data.notes,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get('user-agent')
        )
        
        # Update employee status
        employee.status = 'deactivated'
        employee.status_changed_at = get_indian_time()
        employee.status_changed_by = current_user.id
        employee.status_change_reason = request_data.reason
        
        # DC Protocol (Jan 2026): Set last_working_date from request or default to today
        if request_data.last_working_date:
            from datetime import datetime as dt
            employee.last_working_date = dt.strptime(request_data.last_working_date, '%Y-%m-%d').date()
        else:
            employee.last_working_date = get_indian_time().date()
        
        # Log in audit trail
        log_staff_audit(
            db, current_user.id, "EMPLOYEE_DEACTIVATED", "staff_employees",
            resource_id=employee_id,
            old_data={"status": previous_status},
            new_data={
                "status": "deactivated",
                "reason": request_data.reason,
                "notes": request_data.notes,
                "deactivated_by": current_user.emp_code,
                "last_working_date": str(employee.last_working_date)
            },
            ip_address=request.client.host if request.client else None
        )
        
        db.commit()
        
        return {
            "success": True,
            "message": f"Employee {employee.emp_code} ({employee.full_name}) has been deactivated",
            "employee_id": employee.id,
            "employee_code": employee.emp_code,
            "previous_status": previous_status,
            "new_status": "deactivated",
            "can_reactivate": True,
            "deactivated_by": current_user.emp_code,
            "deactivated_at": employee.status_changed_at.isoformat() if employee.status_changed_at else None,
            "last_working_date": str(employee.last_working_date) if employee.last_working_date else None
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to deactivate employee: {str(e)}"
        )


@router.patch("/employees/{employee_id}/resigned")
async def mark_employee_resigned(
    employee_id: int,
    request_data: EmployeeStatusChangeRequest = Body(...),
    request: Request = None,
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Mark an employee as resigned (permanent deactivation)
    DC Protocol: Permanently blocks login, stops all trackers, cannot be reversed
    
    Access: VGK4U Supreme, Key Leadership, HR, EA
    Protected: MR10001 cannot be marked resigned
    Hierarchy: Can only mark resignation for employees with lower hierarchy level
    WARNING: This action is PERMANENT and cannot be reversed
    """
    # Validate confirmation text
    if request_data.confirm_text != "CONFIRM":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please type 'CONFIRM' to proceed with resignation marking"
        )
    
    # DC Protocol: Menu-based access control - page assignment = full access
    # if current_user.role.role_code not in STATUS_CHANGE_ROLES:
    #     raise HTTPException(
    #         status_code=status.HTTP_403_FORBIDDEN,
    #         detail=f"Access denied. Required roles: {', '.join(STATUS_CHANGE_ROLES)}"
    #     )
    
    # Find employee
    employee = db.query(StaffEmployee).filter(StaffEmployee.id == employee_id).first()
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee not found"
        )
    
    # Check protected employee
    if employee.emp_code in PROTECTED_EMPLOYEE_CODES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Cannot mark protected employee {employee.emp_code} as resigned"
        )
    
    # Check hierarchy (cannot mark same or higher level as resigned)
    if current_user.role.hierarchy_level <= employee.role.hierarchy_level and current_user.id != employee.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot mark employee with same or higher hierarchy level as resigned"
        )
    
    # Cannot mark self as resigned
    if current_user.id == employee_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot mark your own account as resigned"
        )
    
    # Check current status
    if employee.status == 'resigned':
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Employee is already marked as resigned"
        )
    
    try:
        previous_status = employee.status
        
        # Log status change in history table (before updating employee)
        log_staff_status_change(
            db=db,
            employee=employee,
            new_status='resigned',
            changed_by=current_user,
            reason=request_data.reason,
            notes=request_data.notes,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get('user-agent')
        )
        
        # Update employee status
        employee.status = 'resigned'
        employee.status_changed_at = get_indian_time()
        employee.status_changed_by = current_user.id
        employee.status_change_reason = request_data.reason
        
        # DC Protocol (Jan 2026): Set last_working_date from request or default to today
        if request_data.last_working_date:
            from datetime import datetime as dt
            employee.last_working_date = dt.strptime(request_data.last_working_date, '%Y-%m-%d').date()
        else:
            employee.last_working_date = get_indian_time().date()
        
        # Log in audit trail
        log_staff_audit(
            db, current_user.id, "EMPLOYEE_RESIGNED", "staff_employees",
            resource_id=employee_id,
            old_data={"status": previous_status},
            new_data={
                "status": "resigned",
                "reason": request_data.reason,
                "notes": request_data.notes,
                "marked_by": current_user.emp_code,
                "is_permanent": True,
                "last_working_date": str(employee.last_working_date)
            },
            ip_address=request.client.host if request.client else None
        )
        
        db.commit()
        
        return {
            "success": True,
            "message": f"Employee {employee.emp_code} ({employee.full_name}) has been marked as RESIGNED (permanent)",
            "employee_id": employee.id,
            "employee_code": employee.emp_code,
            "previous_status": previous_status,
            "new_status": "resigned",
            "can_reactivate": False,
            "is_permanent": True,
            "marked_by": current_user.emp_code,
            "marked_at": employee.status_changed_at.isoformat() if employee.status_changed_at else None,
            "last_working_date": str(employee.last_working_date) if employee.last_working_date else None
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to mark employee as resigned: {str(e)}"
        )


@router.patch("/employees/{employee_id}/reactivate")
async def reactivate_employee(
    employee_id: int,
    request_data: EmployeeStatusChangeRequest = Body(...),
    request: Request = None,
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Reactivate a deactivated employee
    DC Protocol: Restores login access and all trackers
    
    Access: VGK4U Supreme, Key Leadership, HR, EA
    Restriction: CANNOT reactivate resigned employees (permanent status)
    """
    # Validate confirmation text
    if request_data.confirm_text != "CONFIRM":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please type 'CONFIRM' to proceed with reactivation"
        )
    
    # DC Protocol: Menu-based access control - page assignment = full access
    # if current_user.role.role_code not in STATUS_CHANGE_ROLES:
    #     raise HTTPException(
    #         status_code=status.HTTP_403_FORBIDDEN,
    #         detail=f"Access denied. Required roles: {', '.join(STATUS_CHANGE_ROLES)}"
    #     )
    
    # Find employee
    employee = db.query(StaffEmployee).filter(StaffEmployee.id == employee_id).first()
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee not found"
        )
    
    # Check current status - only allow reactivation from deactivated, inactive, suspended
    if employee.status == 'active':
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Employee is already active"
        )
    
    if employee.status == 'resigned':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot reactivate a resigned employee. Resignation is PERMANENT and cannot be reversed."
        )
    
    if employee.status == 'terminated':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot reactivate a terminated employee. Please contact system administrator."
        )
    
    try:
        previous_status = employee.status
        
        # Log status change in history table (before updating employee)
        log_staff_status_change(
            db=db,
            employee=employee,
            new_status='active',
            changed_by=current_user,
            reason=request_data.reason,
            notes=request_data.notes,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get('user-agent')
        )
        
        # Update employee status
        employee.status = 'active'
        employee.status_changed_at = get_indian_time()
        employee.status_changed_by = current_user.id
        employee.status_change_reason = request_data.reason
        
        # DC Protocol (Jan 2026): Set restart_date from request or default to today
        if request_data.restart_date:
            from datetime import datetime as dt
            employee.restart_date = dt.strptime(request_data.restart_date, '%Y-%m-%d').date()
        else:
            employee.restart_date = get_indian_time().date()
        
        # Log in audit trail
        log_staff_audit(
            db, current_user.id, "EMPLOYEE_REACTIVATED", "staff_employees",
            resource_id=employee_id,
            old_data={"status": previous_status, "last_working_date": str(employee.last_working_date) if employee.last_working_date else None},
            new_data={
                "status": "active",
                "reason": request_data.reason,
                "notes": request_data.notes,
                "reactivated_by": current_user.emp_code,
                "restart_date": str(employee.restart_date)
            },
            ip_address=request.client.host if request.client else None
        )
        
        db.commit()
        
        return {
            "success": True,
            "message": f"Employee {employee.emp_code} ({employee.full_name}) has been reactivated",
            "employee_id": employee.id,
            "employee_code": employee.emp_code,
            "previous_status": previous_status,
            "new_status": "active",
            "reactivated_by": current_user.emp_code,
            "reactivated_at": employee.status_changed_at.isoformat() if employee.status_changed_at else None,
            "restart_date": str(employee.restart_date) if employee.restart_date else None
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reactivate employee: {str(e)}"
        )


@router.get("/employees/{employee_id}/status-history")
async def get_employee_status_history(
    employee_id: int,
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Get status change history for an employee
    DC Protocol: Complete audit trail of all status transitions
    """
    # DC Protocol: Menu-based access control - page assignment = full access
    role_code = current_user.role.role_code.lower() if current_user.role and current_user.role.role_code else None
    # Any authenticated staff can view status history
    
    # Find employee
    employee = db.query(StaffEmployee).filter(StaffEmployee.id == employee_id).first()
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee not found"
        )
    
    # Get status history
    history = db.query(StaffEmployeeStatusHistory).filter(
        StaffEmployeeStatusHistory.employee_id == employee_id
    ).order_by(StaffEmployeeStatusHistory.created_at.desc()).all()
    
    return {
        "success": True,
        "employee_id": employee_id,
        "employee_code": employee.emp_code,
        "employee_name": employee.full_name,
        "current_status": employee.status,
        "total_changes": len(history),
        "history": [h.to_dict() for h in history]
    }
