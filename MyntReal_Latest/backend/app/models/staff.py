"""
Staff System Models (DC Protocol Compliant)
Single source of truth for all staff-related data

Tables:
- staff_roles: Role definitions with hierarchy levels
- staff_departments: Organizational units
- staff_employees: Employee records with security features
- staff_employee_kyc: KYC submissions and approvals
- staff_employee_id_seq: Auto-generated employee ID sequence
- staff_settings: System configuration
- staff_audit_log: Immutable activity logging

Updated: Nov 26, 2025 - Added KYC, ID sequence, password change flag
"""

from sqlalchemy import (
    Column, Integer, String, DateTime, Date, Boolean, Text, 
    ForeignKey, CheckConstraint, Index, Sequence, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from datetime import datetime
import pytz

from app.models.base import Base

# Sequence for auto-generating employee IDs starting from 10007
staff_emp_id_seq = Sequence('staff_emp_id_seq', start=10007, increment=1)


def get_indian_time():
    """Get current time in Indian timezone (IST)"""
    ist = pytz.timezone('Asia/Kolkata')
    return datetime.now(ist).replace(tzinfo=None)


class StaffRole(Base):
    """
    Staff Role Definition
    DC: Single source of truth for role hierarchy
    """
    __tablename__ = 'staff_roles'
    
    id = Column(Integer, primary_key=True, index=True)
    role_code = Column(String(32), unique=True, nullable=False, index=True)
    role_name = Column(String(64), nullable=False)
    hierarchy_level = Column(Integer, nullable=False)
    description = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=get_indian_time)
    
    employees = relationship("StaffEmployee", back_populates="role")
    
    def to_dict(self):
        return {
            "id": self.id,
            "role_code": self.role_code,
            "role_name": self.role_name,
            "hierarchy_level": self.hierarchy_level,
            "description": self.description,
            "is_active": self.is_active
        }


class StaffDepartment(Base):
    """
    Staff Department
    DC: Organizational unit with optional head reference
    Extended Nov 29, 2025: Added multi-department support, role permissions, data assignments
    Extended Nov 29, 2025: Added is_freelancer_dept for MN Staff departments
    """
    __tablename__ = 'staff_departments'
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(128), unique=True, nullable=False)
    department_code = Column(String(20), unique=True, nullable=True, index=True)  # Auto-generated DEPT001, DEPT002 (or FLDEPT001 for freelancer)
    description = Column(Text)
    head_id = Column(Integer, ForeignKey('staff_employees.id', ondelete='SET NULL'), nullable=True)
    
    # MN Staff (Freelancer) Department Flag (Nov 29, 2025)
    is_freelancer_dept = Column(Boolean, default=False, nullable=False)  # TRUE = MN Staff department
    
    # Advanced Permissions (Nov 29, 2025)
    role_permissions = Column(JSONB, default=[])  # [50, 60, 70, 85] - hierarchy levels with access
    data_assignments = Column(JSONB, default={})  # {task_categories: [1,2], expense_categories: [3,4], staff_members: [101,102]}
    system_features = Column(JSONB, default=[])  # ["journey_tracking", "kra_management", "time_tracker"]
    
    is_active = Column(Boolean, default=True)
    created_by = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    updated_by = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    created_at = Column(DateTime, default=get_indian_time)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time)
    
    employees = relationship("StaffEmployee", back_populates="department", foreign_keys="[StaffEmployee.department_id]")
    head = relationship("StaffEmployee", foreign_keys=[head_id], post_update=True)
    employee_assignments = relationship("StaffEmployeeDepartment", back_populates="department", cascade="all, delete-orphan")
    custom_roles = relationship("StaffDepartmentRole", back_populates="department", cascade="all, delete-orphan")
    
    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "department_code": self.department_code,
            "description": self.description,
            "head_id": self.head_id,
            "head_name": self.head.full_name if self.head else None,
            "is_freelancer_dept": self.is_freelancer_dept,
            "role_permissions": self.role_permissions or [],
            "data_assignments": self.data_assignments or {},
            "system_features": self.system_features or [],
            "is_active": self.is_active,
            "employee_count": len(self.employees) if self.employees else 0,
            "multi_dept_count": len(self.employee_assignments) if self.employee_assignments else 0,
            "custom_roles_count": len(self.custom_roles) if self.custom_roles else 0,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


class StaffEmployee(Base):
    """
    Staff Employee
    DC: Single source of truth for all employee data
    - Single role_id field (no duplicate role system)
    - Single status field (no active boolean)
    - Single date_of_joining field (no doj)
    - Login via emp_code (not email)
    - Default password = emp_code (requires change on first login)
    Extended Nov 29, 2025: Added staff_type for MN Staff (freelancer) distinction
    Extended Dec 04, 2025: Expanded to 3 staff types - MN_STAFF, MN_EMPLOYEE, FREELANCER
    """
    __tablename__ = 'staff_employees'
    
    id = Column(Integer, primary_key=True, index=True)
    emp_code = Column(String(32), unique=True, nullable=False, index=True)
    
    # Staff Type (Dec 04, 2025) - Distinguishes employee categories
    # MN_STAFF = MN Staff (MN10001-49999) - Company staff with MN code
    # MN_EMPLOYEE = MN Employee (MN50001+) - Employees with MN code (separate range)
    # FREELANCER = Freelancer (FL10001+) - External contractors with FL code
    # MYNT_REAL = Legacy Mynt Real employee (MR10001+) - Kept for backward compatibility
    staff_type = Column(String(32), default='MN_STAFF', nullable=False, index=True)
    salutation = Column(String(10), nullable=True)  # Mr, Mrs, Ms, Dr, etc.
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    full_name = Column(String(256), nullable=False)
    email = Column(String(256), unique=True, nullable=True, index=True)  # Nullable - login uses emp_code
    phone = Column(String(32))
    department_id = Column(Integer, ForeignKey('staff_departments.id'), nullable=True)
    designation = Column(String(128))
    role_id = Column(Integer, ForeignKey('staff_roles.id'), nullable=False, index=True)
    status = Column(String(32), default='active', index=True)
    date_of_joining = Column(Date, nullable=False)
    password_hash = Column(String(256), nullable=False)
    
    # Status Change Tracking (Dec 2025) - DC Protocol: Audit trail for deactivation/resignation
    status_changed_at = Column(DateTime, nullable=True)  # When status was last changed
    status_changed_by = Column(Integer, ForeignKey('staff_employees.id', ondelete='SET NULL'), nullable=True)  # Who changed the status
    status_change_reason = Column(Text, nullable=True)  # Reason for deactivation/resignation
    
    # DC Protocol (Jan 2026): Last Working Date & Restart Date for status transitions
    # last_working_date: Set when status → paused/resigned/terminated/deactivated
    # restart_date: Set when status → active (reactivation)
    last_working_date = Column(Date, nullable=True)  # Final working day before pause/termination
    restart_date = Column(Date, nullable=True)  # Date when employee was reactivated
    
    # Password management
    requires_password_change = Column(Boolean, default=True)  # Force change on first login
    password_last_reset_by = Column(Integer, nullable=True)  # Admin who reset password
    password_last_reset_at = Column(DateTime, nullable=True)  # When password was last reset
    
    # Security
    failed_login_attempts = Column(Integer, default=0)
    locked_until = Column(DateTime, nullable=True)
    totp_secret = Column(Text, nullable=True)
    totp_enabled = Column(Boolean, default=False)
    last_password_change = Column(DateTime, nullable=True)
    last_login = Column(DateTime, nullable=True)
    
    # KYC Status
    kyc_status = Column(String(32), default='pending')  # pending, submitted, approved, rejected
    
    # Reporting Manager - DC: Links employee to their manager for team-based access
    reporting_manager_id = Column(Integer, ForeignKey('staff_employees.id', ondelete='SET NULL'), nullable=True, index=True)
    
    # DC Protocol (Dec 15, 2025): Multi-Company Assignment
    # base_company_id = Primary/home company for HR/ownership purposes
    # data_companies = JSONB array of company IDs where employee can access/work with data
    base_company_id = Column(Integer, ForeignKey('associated_companies.id', ondelete='SET NULL'), nullable=True, index=True)
    data_companies = Column(JSONB, default=[], nullable=False)  # [1, 2, 3] - company IDs for data access
    dialer_category_priority = Column(JSONB, default=[], nullable=True)  # [cat_id1, cat_id2] — preferred category order for AutoDialer queue

    # DC Protocol (Jan 2026): Is Experienced Flag - For Previous Experience Documents
    is_experienced = Column(Boolean, default=False, nullable=False)  # If True, experience docs are mandatory in KYC
    
    # DC Protocol (Feb 2026): Call Tracking Enabled - Quality test tracking
    # If True, staff's call history will be synced and tracked
    # If False, call log sync is skipped for this employee
    call_tracking_enabled = Column(Boolean, default=False, nullable=False, index=True)

    # DC Protocol (Mar 2026): Team Tag — groups employee into Team A/B/C for compliance and reporting
    # Values: team_a, team_b, team_c, None (unassigned)
    team_tag = Column(String(20), nullable=True, index=True)

    # [DC-PARTNER-CONTACTS-001] Showroom link for dual portal login
    # Sales/Service dept staff can log into partner portal and see this showroom's view
    linked_partner_id = Column(Integer, ForeignKey('official_partners.id', ondelete='SET NULL'), nullable=True, index=True)
    
    # DC Protocol (Jul 2026): Freelancer access mode for module restriction
    # Values: 'default', 'only_leads'
    freelancer_access_mode = Column(String(32), default='default', nullable=True)
    
    # DC Protocol (Jan 2026): Employment Type - Probation/Confirmed tracking
    employment_type = Column(String(32), default='probation', nullable=False, index=True)  # probation, confirmed, extended_probation
    probation_period_months = Column(Integer, default=6, nullable=True)  # Standard: 3, 6, 9, 12 months
    probation_start_date = Column(Date, nullable=True)  # Typically = date_of_joining
    probation_end_date = Column(Date, nullable=True)  # Calculated or manually set
    confirmation_date = Column(Date, nullable=True)  # When employee was confirmed
    probation_extended = Column(Boolean, default=False)  # Flag if probation was extended
    probation_extension_count = Column(Integer, default=0)  # How many times extended
    probation_notes = Column(Text, nullable=True)  # Reason for extension, confirmation notes
    
    created_by = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=get_indian_time)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time)
    
    # Soft Delete (Dec 2025) - DC Protocol compliant with restore capability
    is_deleted = Column(Boolean, default=False, index=True)
    deleted_at = Column(DateTime, nullable=True)
    deleted_by = Column(Integer, nullable=True)  # Employee ID who deleted
    
    __table_args__ = (
        CheckConstraint(
            "status IN ('active', 'inactive', 'suspended', 'terminated', 'deactivated', 'resigned')",
            name='staff_employees_status_check'
        ),
        CheckConstraint(
            "kyc_status IN ('pending', 'submitted', 'approved', 'rejected')",
            name='staff_employees_kyc_status_check'
        ),
        CheckConstraint(
            "employment_type IN ('probation', 'confirmed', 'extended_probation')",
            name='staff_employees_employment_type_check'
        ),
        Index('idx_staff_emp_role_status', 'role_id', 'status'),
        Index('idx_staff_emp_kyc_status', 'kyc_status'),
        Index('idx_staff_emp_employment_type', 'employment_type'),
    )
    
    department = relationship("StaffDepartment", back_populates="employees", foreign_keys=[department_id])
    role = relationship("StaffRole", back_populates="employees")
    kyc_records = relationship("StaffEmployeeKyc", back_populates="employee", foreign_keys="[StaffEmployeeKyc.employee_id]")
    reporting_manager = relationship("StaffEmployee", remote_side="StaffEmployee.id", foreign_keys=[reporting_manager_id])
    direct_reports = relationship("StaffEmployee", back_populates="reporting_manager", foreign_keys="[StaffEmployee.reporting_manager_id]")
    # DC Protocol (Dec 15, 2025): Base company relationship
    base_company = relationship("AssociatedCompany", foreign_keys=[base_company_id])
    # DC Protocol (Dec 21, 2025): Additional departments relationship (many-to-many)
    additional_departments = relationship("StaffEmployeeDepartment", foreign_keys="[StaffEmployeeDepartment.employee_id]", cascade="all, delete-orphan")
    
    def to_dict(self, include_sensitive=False):
        # DC_RBAC_API_STRUCTURE_001: Build complete role object for frontend access control
        role_data = None
        if self.role:
            role_data = {
                "id": self.role.id,
                "role_code": self.role.role_code,
                "role_name": self.role.role_name,
                "hierarchy_level": self.role.hierarchy_level,
                "description": self.role.description,
                "is_active": self.role.is_active
            }
        
        data = {
            "id": self.id,
            "emp_code": self.emp_code,
            "employee_code": self.emp_code,  # Alias for frontend compatibility
            "staff_type": self.staff_type,
            "is_mn_staff": self.staff_type == 'MN_STAFF',  # MN10001-49999 (Dec 04, 2025)
            "is_mn_employee": self.staff_type == 'MN_EMPLOYEE',  # MN50001+ (Dec 04, 2025)
            "is_freelancer": self.staff_type == 'FREELANCER',  # FL10001+ (Dec 04, 2025)
            "salutation": self.salutation,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "full_name": self.full_name,
            "email": self.email,
            "phone": self.phone,
            "department_id": self.department_id,
            "department_name": self.department.name if self.department else None,
            "is_freelancer_dept": self.department.is_freelancer_dept if self.department else False,
            "designation": self.designation,
            "role_id": self.role_id,
            "role_code": self.role.role_code if self.role else None,
            "role_name": self.role.role_name if self.role else None,
            "role": role_data,  # DC_RBAC_API_STRUCTURE_001: Complete role object for frontend RBAC
            "status": self.status,
            "is_active": self.status == 'active',  # Convenience field
            "is_deactivated": self.status == 'deactivated',  # Dec 2025
            "is_resigned": self.status == 'resigned',  # Dec 2025
            "status_changed_at": self.status_changed_at.isoformat() if self.status_changed_at else None,
            "status_change_reason": self.status_change_reason,
            # DC Protocol (Jan 2026): Status transition dates
            "last_working_date": self.last_working_date.isoformat() if self.last_working_date else None,
            "restart_date": self.restart_date.isoformat() if self.restart_date else None,
            "date_of_joining": self.date_of_joining.isoformat() if self.date_of_joining else None,
            "totp_enabled": self.totp_enabled,
            "is_2fa_enabled": self.totp_enabled,  # Alias for frontend
            "kyc_status": self.kyc_status,
            "requires_password_change": self.requires_password_change,
            "last_login": self.last_login.isoformat() if self.last_login else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "reporting_manager_id": self.reporting_manager_id,
            "reporting_manager_name": self.reporting_manager.full_name if self.reporting_manager else None,
            "reporting_manager_code": self.reporting_manager.emp_code if self.reporting_manager else None,
            # DC Protocol (Dec 15, 2025): Multi-Company Assignment
            "base_company_id": self.base_company_id,
            "base_company_name": self.base_company.company_name if self.base_company else None,
            "base_company_code": self.base_company.company_code if self.base_company else None,
            "data_companies": self._get_data_companies_info(),
            # DC Protocol (Dec 21, 2025): Additional Departments (multi-department support)
            "additional_departments": self._get_additional_departments_info(),
            # DC Protocol (Jan 2026): Employment Type - Probation/Confirmed tracking
            "employment_type": self.employment_type,
            "probation_period_months": self.probation_period_months,
            "probation_start_date": self.probation_start_date.isoformat() if self.probation_start_date else None,
            "probation_end_date": self.probation_end_date.isoformat() if self.probation_end_date else None,
            "confirmation_date": self.confirmation_date.isoformat() if self.confirmation_date else None,
            "probation_extended": self.probation_extended,
            "probation_extension_count": self.probation_extension_count,
            "probation_notes": self.probation_notes,
            "call_tracking_enabled": self.call_tracking_enabled,
            "team_tag": self.team_tag,
            # [DC-PARTNER-CONTACTS-001] Linked partner showroom for dual portal login
            "linked_partner_id": getattr(self, 'linked_partner_id', None),
            "freelancer_access_mode": getattr(self, 'freelancer_access_mode', 'default'),
        }
        
        if include_sensitive:
            data["failed_login_attempts"] = self.failed_login_attempts
            data["locked_until"] = self.locked_until.isoformat() if self.locked_until else None
            data["last_password_change"] = self.last_password_change.isoformat() if self.last_password_change else None
            data["password_last_reset_at"] = self.password_last_reset_at.isoformat() if self.password_last_reset_at else None
        
        return data
    
    def _get_data_companies_info(self):
        """Get data companies with names for display"""
        from sqlalchemy import inspect
        
        if not self.data_companies or len(self.data_companies) == 0:
            return []
        
        # Try to get company details if session is available
        try:
            session = inspect(self).session
            if session:
                from app.models.sfms import AssociatedCompany
                companies = session.query(AssociatedCompany).filter(
                    AssociatedCompany.id.in_(self.data_companies)
                ).all()
                return [
                    {"company_id": c.id, "company_name": c.company_name, "company_code": c.company_code}
                    for c in companies
                ]
        except Exception:
            pass
        
        # Fallback: return IDs only
        return [{"company_id": cid} for cid in self.data_companies]
    
    def _get_additional_departments_info(self):
        """DC Protocol (Dec 21, 2025): Get additional departments for multi-department display"""
        if not self.additional_departments:
            return []
        return [
            {
                "department_id": ad.department_id,
                "department_name": ad.department.name if ad.department else None,
                "department_code": ad.department.department_code if ad.department else None
            }
            for ad in self.additional_departments
        ]
    
    def is_locked(self):
        """Check if account is currently locked"""
        if self.locked_until and self.locked_until > datetime.utcnow():
            return True
        return False
    
    def has_permission(self, required_level):
        """Check if employee has required hierarchy level"""
        if self.role:
            return self.role.hierarchy_level >= required_level
        return False
    
    def can_manage(self, target_employee):
        """Check if this employee can manage another employee"""
        if not self.role or not target_employee.role:
            return False
        return self.role.hierarchy_level > target_employee.role.hierarchy_level


class StaffEmployeeKyc(Base):
    """
    Staff Employee KYC Records
    DC: KYC submission and approval workflow (matching MNR user profile structure)
    - Employees submit their own KYC documents
    - Key Leadership / Leadership Role can approve/reject
    """
    __tablename__ = 'staff_employee_kyc'
    
    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey('staff_employees.id', ondelete='CASCADE'), nullable=False, index=True)
    
    # Profile Photo
    profile_photo = Column(String(512))  # URL/path to profile photo
    
    # Personal Details
    father_name = Column(String(256))
    mother_name = Column(String(256))
    spouse_name = Column(String(256))  # For married employees
    date_of_birth = Column(Date)
    gender = Column(String(16))
    blood_group = Column(String(8))
    marital_status = Column(String(32))
    nationality = Column(String(64), default='Indian')
    religion = Column(String(64))
    
    # Educational Qualification
    highest_qualification = Column(String(128))  # e.g., B.Tech, MBA, etc.
    specialization = Column(String(128))  # e.g., Computer Science
    institution_name = Column(String(256))
    year_of_passing = Column(Integer)
    
    # Previous Employment
    previous_company = Column(String(256))
    previous_designation = Column(String(128))
    previous_experience_years = Column(Integer)
    
    # Address - Permanent
    permanent_address_line1 = Column(Text)
    permanent_address_line2 = Column(Text)
    permanent_city = Column(String(128))
    permanent_state = Column(String(128))
    permanent_pincode = Column(String(16))
    permanent_country = Column(String(64), default='India')
    
    # Address - Current
    current_address_line1 = Column(Text)
    current_address_line2 = Column(Text)
    current_city = Column(String(128))
    current_state = Column(String(128))
    current_pincode = Column(String(16))
    current_country = Column(String(64), default='India')
    same_as_permanent = Column(Boolean, default=False)
    
    # Legacy address fields (backward compatibility)
    permanent_address = Column(Text)
    current_address = Column(Text)
    city = Column(String(128))
    state = Column(String(128))
    pincode = Column(String(16))
    
    # Identity Documents
    aadhar_number = Column(String(16))
    pan_number = Column(String(16))
    passport_number = Column(String(32))
    passport_expiry = Column(Date)
    driving_license = Column(String(32))
    dl_expiry = Column(Date)
    voter_id = Column(String(32))
    
    # Bank Details
    bank_account_holder = Column(String(256))  # Account holder name
    bank_name = Column(String(128))
    bank_branch = Column(String(128))
    account_number = Column(String(32))
    ifsc_code = Column(String(16))
    account_type = Column(String(32))  # Savings, Current
    upi_id = Column(String(128))  # UPI ID for payments
    
    # Emergency Contact
    emergency_contact_name = Column(String(256))
    emergency_contact_phone = Column(String(32))
    emergency_contact_relation = Column(String(64))
    emergency_contact_address = Column(Text)
    
    # Nominee Details
    nominee_name = Column(String(256))
    nominee_relationship = Column(String(64))
    nominee_dob = Column(Date)
    nominee_phone = Column(String(32))
    nominee_address = Column(Text)
    
    # Document Uploads (stored as paths/URLs)
    documents = Column(JSONB, default={})  # {"aadhar_front": "path", "aadhar_back": "path", "pan": "path", etc.}
    
    # Workflow
    status = Column(String(32), default='draft')  # draft, submitted, approved, rejected
    submitted_at = Column(DateTime, nullable=True)
    reviewed_by = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    rejection_reason = Column(Text, nullable=True)
    
    # DC Protocol: Semantic file naming (Nov 29, 2025)
    download_filename = Column(String(255), nullable=True)  # Semantic download filename
    uses_new_naming = Column(Boolean, default=False, nullable=False)  # Flag for new naming convention
    
    # DC Protocol (Jan 2026): Previous Experience Documents
    # Bank Statements (Last 3 Months)
    bank_statement_1_url = Column(String(512), nullable=True)  # Month 1 bank statement
    bank_statement_2_url = Column(String(512), nullable=True)  # Month 2 bank statement
    bank_statement_3_url = Column(String(512), nullable=True)  # Month 3 bank statement
    # Offer Letter from Previous Company
    offer_letter_url = Column(String(512), nullable=True)  # Previous company offer letter
    # Pay Slips (Last 3 Months)
    pay_slip_1_url = Column(String(512), nullable=True)  # Month 1 pay slip
    pay_slip_2_url = Column(String(512), nullable=True)  # Month 2 pay slip
    pay_slip_3_url = Column(String(512), nullable=True)  # Month 3 pay slip
    # Experience Documents Workflow
    experience_docs_status = Column(String(32), default='pending', nullable=False)  # pending, submitted, verified
    experience_docs_reviewed_by = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    experience_docs_reviewed_at = Column(DateTime, nullable=True)
    experience_docs_remarks = Column(Text, nullable=True)  # Reviewer comments
    
    created_at = Column(DateTime, default=get_indian_time)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time)
    
    __table_args__ = (
        CheckConstraint(
            "status IN ('draft', 'submitted', 'approved', 'rejected')",
            name='staff_kyc_status_check'
        ),
        Index('idx_staff_kyc_status', 'status'),
    )
    
    employee = relationship("StaffEmployee", back_populates="kyc_records", foreign_keys="[StaffEmployeeKyc.employee_id]")
    reviewer = relationship("StaffEmployee", foreign_keys="[StaffEmployeeKyc.reviewed_by]")
    
    def to_dict(self):
        return {
            "id": self.id,
            "employee_id": self.employee_id,
            "employee_name": self.employee.full_name if self.employee else None,
            "employee_code": self.employee.emp_code if self.employee else None,
            
            # Profile Photo
            "profile_photo": self.profile_photo,
            
            # Personal Details
            "father_name": self.father_name,
            "mother_name": self.mother_name,
            "spouse_name": self.spouse_name,
            "date_of_birth": self.date_of_birth.isoformat() if self.date_of_birth else None,
            "gender": self.gender,
            "blood_group": self.blood_group,
            "marital_status": self.marital_status,
            "nationality": self.nationality,
            "religion": self.religion,
            
            # Educational Qualification
            "highest_qualification": self.highest_qualification,
            "specialization": self.specialization,
            "institution_name": self.institution_name,
            "year_of_passing": self.year_of_passing,
            
            # Previous Employment
            "previous_company": self.previous_company,
            "previous_designation": self.previous_designation,
            "previous_experience_years": self.previous_experience_years,
            
            # Address - Permanent
            "permanent_address_line1": self.permanent_address_line1,
            "permanent_address_line2": self.permanent_address_line2,
            "permanent_city": self.permanent_city,
            "permanent_state": self.permanent_state,
            "permanent_pincode": self.permanent_pincode,
            "permanent_country": self.permanent_country,
            
            # Address - Current
            "current_address_line1": self.current_address_line1,
            "current_address_line2": self.current_address_line2,
            "current_city": self.current_city,
            "current_state": self.current_state,
            "current_pincode": self.current_pincode,
            "current_country": self.current_country,
            "same_as_permanent": self.same_as_permanent,
            
            # Legacy address (backward compatibility)
            "permanent_address": self.permanent_address,
            "current_address": self.current_address,
            "city": self.city,
            "state": self.state,
            "pincode": self.pincode,
            
            # Identity Documents
            "aadhar_number": self.aadhar_number,
            "pan_number": self.pan_number,
            "passport_number": self.passport_number,
            "passport_expiry": self.passport_expiry.isoformat() if self.passport_expiry else None,
            "driving_license": self.driving_license,
            "dl_expiry": self.dl_expiry.isoformat() if self.dl_expiry else None,
            "voter_id": self.voter_id,
            
            # Bank Details
            "bank_account_holder": self.bank_account_holder,
            "bank_name": self.bank_name,
            "bank_branch": self.bank_branch,
            "account_number": self.account_number,
            "ifsc_code": self.ifsc_code,
            "account_type": self.account_type,
            "upi_id": self.upi_id,
            
            # Emergency Contact
            "emergency_contact_name": self.emergency_contact_name,
            "emergency_contact_phone": self.emergency_contact_phone,
            "emergency_contact_relation": self.emergency_contact_relation,
            "emergency_contact_address": self.emergency_contact_address,
            
            # Nominee Details
            "nominee_name": self.nominee_name,
            "nominee_relationship": self.nominee_relationship,
            "nominee_dob": self.nominee_dob.isoformat() if self.nominee_dob else None,
            "nominee_phone": self.nominee_phone,
            "nominee_address": self.nominee_address,
            
            # Documents
            "documents": self.documents,
            
            # Workflow
            "status": self.status,
            "submitted_at": self.submitted_at.isoformat() if self.submitted_at else None,
            "reviewed_by": self.reviewed_by,
            "reviewer_name": self.reviewer.full_name if self.reviewer else None,
            "reviewed_at": self.reviewed_at.isoformat() if self.reviewed_at else None,
            "rejection_reason": self.rejection_reason,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            
            # DC Protocol (Jan 2026): Previous Experience Documents
            "bank_statement_1_url": self.bank_statement_1_url,
            "bank_statement_2_url": self.bank_statement_2_url,
            "bank_statement_3_url": self.bank_statement_3_url,
            "offer_letter_url": self.offer_letter_url,
            "pay_slip_1_url": self.pay_slip_1_url,
            "pay_slip_2_url": self.pay_slip_2_url,
            "pay_slip_3_url": self.pay_slip_3_url,
            "experience_docs_status": self.experience_docs_status,
            "experience_docs_reviewed_by": self.experience_docs_reviewed_by,
            "experience_docs_reviewed_at": self.experience_docs_reviewed_at.isoformat() if self.experience_docs_reviewed_at else None,
            "experience_docs_remarks": self.experience_docs_remarks
        }


class StaffSetting(Base):
    """
    Staff System Settings
    DC: Centralized configuration with access control
    """
    __tablename__ = 'staff_settings'
    
    id = Column(Integer, primary_key=True, index=True)
    setting_key = Column(String(128), unique=True, nullable=False, index=True)
    setting_value = Column(Text, nullable=False)
    setting_type = Column(String(32), default='string')
    description = Column(Text)
    editable_by = Column(String(32), default='vgk4u')
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=get_indian_time)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time)
    
    __table_args__ = (
        CheckConstraint(
            "setting_type IN ('string', 'number', 'boolean', 'json')",
            name='staff_settings_type_check'
        ),
    )
    
    def get_value(self):
        """Get typed value based on setting_type"""
        if self.setting_type == 'number':
            try:
                return int(self.setting_value)
            except ValueError:
                return float(self.setting_value)
        elif self.setting_type == 'boolean':
            return self.setting_value.lower() in ('true', '1', 'yes')
        elif self.setting_type == 'json':
            import json
            return json.loads(self.setting_value)
        return self.setting_value
    
    def to_dict(self):
        return {
            "id": self.id,
            "setting_key": self.setting_key,
            "setting_value": self.setting_value,
            "typed_value": self.get_value(),
            "setting_type": self.setting_type,
            "description": self.description,
            "editable_by": self.editable_by,
            "is_active": self.is_active
        }


class StaffAuditLog(Base):
    """
    Staff Audit Log (Immutable)
    DC: Complete audit trail for all staff operations
    """
    __tablename__ = 'staff_audit_log'
    
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=get_indian_time, nullable=False, index=True)
    employee_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    action = Column(String(64), nullable=False, index=True)
    resource_type = Column(String(64), nullable=False, index=True)
    resource_id = Column(Integer, nullable=True)
    old_data = Column(JSONB, nullable=True)
    new_data = Column(JSONB, nullable=True)
    ip_address = Column(String(64), nullable=True)
    user_agent = Column(Text, nullable=True)
    
    employee = relationship("StaffEmployee", foreign_keys=[employee_id])
    
    def to_dict(self):
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "employee_id": self.employee_id,
            "employee_name": self.employee.full_name if self.employee else "System",
            "action": self.action,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "old_data": self.old_data,
            "new_data": self.new_data,
            "ip_address": self.ip_address
        }


def log_staff_audit(db, employee_id, action, resource_type, resource_id=None, 
                    old_data=None, new_data=None, ip_address=None, user_agent=None):
    """
    Helper function to create audit log entries
    DC: Ensures consistent audit logging across all operations
    """
    audit = StaffAuditLog(
        employee_id=employee_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        old_data=old_data,
        new_data=new_data,
        ip_address=ip_address,
        user_agent=user_agent
    )
    db.add(audit)
    return audit


def generate_employee_code(db, staff_type: str = 'MN_STAFF'):
    """
    Generate unique employee code based on staff type.
    DC: Atomic sequence generation to prevent duplicates
    Uses database sequence for thread safety
    
    Staff Types (Dec 04, 2025 - Expanded to 3 active + 1 legacy):
    - MN_STAFF: MN Staff (MN10001-49999) - Company staff with MN prefix
    - MN_EMPLOYEE: MN Employee (MN50001+) - Employees with MN prefix (separate range)
    - FREELANCER: Freelancer (FL10001+) - External contractors with FL prefix
    - MYNT_REAL: Legacy Mynt Real (MR10001+) - Backward compatibility
    
    Nov 29, 2025: Extended to support MN Staff (freelancer) IDs
    Dec 04, 2025: Expanded to 3 active staff types + 1 legacy type
                  MN_STAFF and MN_EMPLOYEE share MN prefix with range separation
    """
    from sqlalchemy import text
    
    # DC Protocol: Staff type configuration with range-based separation
    # MN_STAFF and MN_EMPLOYEE share MN prefix but have separate ranges
    STAFF_TYPE_CONFIG = {
        'MN_STAFF': {
            'prefix': 'MN',
            'sequence_name': 'staff_mn_staff_id_seq',
            'start_value': 10001,
            'max_value': 49999,  # MN Staff uses 10001-49999
            'range_filter': lambda x: 10001 <= x <= 49999
        },
        'MN_EMPLOYEE': {
            'prefix': 'MN',
            'sequence_name': 'staff_mn_employee_id_seq',
            'start_value': 50001,
            'max_value': None,  # MN Employee uses 50001+
            'range_filter': lambda x: x >= 50001
        },
        'FREELANCER': {
            'prefix': 'FL',
            'sequence_name': 'staff_fl_emp_id_seq',
            'start_value': 10001,
            'max_value': None,
            'range_filter': lambda x: x >= 10001
        },
        'MYNT_REAL': {
            'prefix': 'MR',
            'sequence_name': 'staff_emp_id_seq',
            'start_value': 10007,
            'max_value': None,
            'range_filter': lambda x: x >= 10007
        }
    }
    
    # Default to MN_STAFF if invalid type provided
    if staff_type not in STAFF_TYPE_CONFIG:
        staff_type = 'MN_STAFF'
    
    config = STAFF_TYPE_CONFIG[staff_type]
    prefix = config['prefix']
    sequence_name = config['sequence_name']
    start_value = config['start_value']
    range_filter = config['range_filter']
    
    try:
        # Try to get next value from sequence
        result = db.execute(text(f"SELECT nextval('{sequence_name}')"))
        next_id = result.scalar()
        
        # Ensure the sequence value is within valid range for this type
        if not range_filter(next_id):
            next_id = start_value
            # Reset sequence to start_value
            db.execute(text(f"SELECT setval('{sequence_name}', {start_value}, false)"))
            result = db.execute(text(f"SELECT nextval('{sequence_name}')"))
            next_id = result.scalar()
    except:
        # Sequence doesn't exist, find max existing code for this specific type's range
        search_pattern = f"{prefix}%"
        
        all_codes = db.query(StaffEmployee).filter(
            StaffEmployee.emp_code.like(search_pattern)
        ).all()
        
        valid_codes = []
        for emp in all_codes:
            try:
                code_str = emp.emp_code
                if code_str.startswith(prefix):
                    numeric_part = code_str[len(prefix):]
                    code_num = int(numeric_part)
                    # Only include codes within this type's valid range
                    if range_filter(code_num):
                        valid_codes.append(code_num)
            except (ValueError, AttributeError):
                pass
        
        if valid_codes:
            next_id = max(valid_codes) + 1
        else:
            next_id = start_value
        
        # Create sequence for future use starting from next value
        try:
            db.execute(text(f"CREATE SEQUENCE IF NOT EXISTS {sequence_name} START WITH {next_id}"))
            db.commit()
            # Get the first value from new sequence
            result = db.execute(text(f"SELECT nextval('{sequence_name}')"))
            next_id = result.scalar()
        except:
            pass  # Sequence might already exist
    
    return f"{prefix}{next_id}"


# Default data for seeding
DEFAULT_ROLES = [
    {"role_code": "vgk4u", "role_name": "VGK Mentor", "hierarchy_level": 150, 
     "description": "VGK Mentor with ultimate authority over all operations."},
    {"role_code": "key_leadership", "role_name": "Key Leadership", "hierarchy_level": 100, 
     "description": "Ultimate decision-making authority. Can view all employees and approve KYC."},
    {"role_code": "leadership_role", "role_name": "Leadership Role", "hierarchy_level": 90,
     "description": "Senior leadership. Can view their direct reports."},
    {"role_code": "hr", "role_name": "HR", "hierarchy_level": 85,
     "description": "Human Resources. Can add, view, and edit all employees."},
    {"role_code": "team_leader", "role_name": "Team Leader", "hierarchy_level": 70,
     "description": "Leads teams. Can view their direct reports."},
    {"role_code": "service_head", "role_name": "Service Head", "hierarchy_level": 65,
     "description": "Head of the Service module. Full visibility over all service tickets, can assign, force-close, and manage the entire service department."},
    {"role_code": "service_incharge", "role_name": "Service Incharge", "hierarchy_level": 65,
     "description": "Service Incharge: Full visibility over all service tickets, can assign, force-close, manage the service department, and access all service admin pages."},
    {"role_code": "manager", "role_name": "Manager", "hierarchy_level": 60,
     "description": "Manages department operations. Can view their direct reports."},
    {"role_code": "senior_executive", "role_name": "Senior Executive", "hierarchy_level": 40,
     "description": "Experienced staff member with basic access."},
    {"role_code": "junior_executive", "role_name": "Junior Executive", "hierarchy_level": 20,
     "description": "Entry-level employee role with basic access."}
]

DEFAULT_DEPARTMENTS = [
    {"name": "Management", "description": "Executive management and strategic planning"},
    {"name": "Admin & HR", "description": "Administrative operations and human resources"},
    {"name": "Sales", "description": "Sales and business development"},
    {"name": "Procurement", "description": "Purchasing and vendor management"},
    {"name": "Production", "description": "Manufacturing and production operations"},
    {"name": "Service", "description": "Customer service and support"},
    {"name": "R&D", "description": "Research and development"}
]


def seed_staff_defaults(db):
    """
    Seed default roles and departments
    DC: Safe to run multiple times (checks for existing data)
    """
    from app.core.security import SecurityManager
    
    changes_made = {"roles": 0, "departments": 0, "admin": False}
    
    # Seed roles
    for role_data in DEFAULT_ROLES:
        existing = db.query(StaffRole).filter_by(role_code=role_data["role_code"]).first()
        if not existing:
            role = StaffRole(**role_data)
            db.add(role)
            changes_made["roles"] += 1
    
    # Seed departments
    for dept_data in DEFAULT_DEPARTMENTS:
        existing = db.query(StaffDepartment).filter_by(name=dept_data["name"]).first()
        if not existing:
            dept = StaffDepartment(**dept_data)
            db.add(dept)
            changes_made["departments"] += 1
    
    db.commit()
    
    # Create default admin if no employees exist
    admin_exists = db.query(StaffEmployee).filter_by(emp_code='MR10001').first()
    if not admin_exists:
        key_leadership_role = db.query(StaffRole).filter_by(role_code='key_leadership').first()
        mgmt_dept = db.query(StaffDepartment).filter_by(name='Management').first()
        
        if key_leadership_role:
            admin = StaffEmployee(
                emp_code='MR10001',
                full_name='System Administrator',
                email='admin@myntreal.com',
                phone='0000000000',
                department_id=mgmt_dept.id if mgmt_dept else None,
                designation='Chief Administrator',
                role_id=key_leadership_role.id,
                status='active',
                date_of_joining=datetime.now().date(),
                password_hash=SecurityManager.get_password_hash('MR10001'),  # Default password = emp_code
                requires_password_change=True,
                kyc_status='pending'
            )
            db.add(admin)
            db.commit()
            changes_made["admin"] = True
    
    return changes_made


# ============================================================================
# NDA System Models (DC Protocol Compliant)
# ============================================================================

class StaffNdaVersion(Base):
    """
    Staff NDA Version Management
    DC: Single source of truth for NDA document versions
    - Only one version can be active at a time per staff type combination
    - New version activation requires all applicable staff to re-accept
    - Supports copy workflow for creating new versions from existing
    - Staff type filtering: NDA shown only to applicable staff types
    
    Updated Dec 04, 2025: Added applicable_staff_types for staff type-based NDA assignment
    """
    __tablename__ = 'staff_nda_versions'
    
    id = Column(Integer, primary_key=True, index=True)
    version_number = Column(String(16), nullable=False)  # e.g., "1.0", "1.1", "2.0"
    title = Column(String(256), nullable=False)  # e.g., "NDA v1.0 - Leadership Confidentiality Agreement"
    content_html = Column(Text, nullable=False)  # Full NDA content in HTML
    
    # Document type: 'NDA' = Non-Disclosure Agreement, 'EMPLOYMENT' = Employment Agreement
    # DC-AGREEMENT-TYPE-001 (Jun 2026): Multi-agreement support
    document_type = Column(String(50), nullable=False, default='NDA', server_default='NDA')
    
    # Staff Type Assignment (Dec 04, 2025 - DC Protocol)
    # Stores list of applicable staff types: ["MN_STAFF", "MN_EMPLOYEE", "FREELANCER", "MYNT_REAL"]
    # Empty array [] = applies to ALL staff types (backward compatibility)
    # NDA shown only to staff matching these types on login
    applicable_staff_types = Column(JSONB, default=[], nullable=False)
    
    # Status management
    status = Column(String(32), default='draft', index=True)  # draft, active, inactive
    effective_from = Column(DateTime, nullable=True)  # When version becomes effective
    
    # Creation tracking
    created_by = Column(Integer, ForeignKey('staff_employees.id'), nullable=False)
    created_at = Column(DateTime, default=get_indian_time)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time)
    updated_by = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    
    # Copy tracking
    source_version_id = Column(Integer, ForeignKey('staff_nda_versions.id'), nullable=True)
    
    # Activation tracking
    activation_timestamp = Column(DateTime, nullable=True)
    activated_by = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    deactivated_at = Column(DateTime, nullable=True)
    deactivated_by = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    
    # Admin notes
    notes = Column(Text, nullable=True)
    
    __table_args__ = (
        CheckConstraint(
            "status IN ('draft', 'active', 'inactive')",
            name='staff_nda_version_status_check'
        ),
        Index('idx_staff_nda_status', 'status'),
        Index('idx_staff_nda_version', 'version_number'),
        Index('idx_staff_nda_staff_types', 'applicable_staff_types', postgresql_using='gin'),
    )
    
    # Relationships
    creator = relationship("StaffEmployee", foreign_keys=[created_by])
    updater = relationship("StaffEmployee", foreign_keys=[updated_by])
    activator = relationship("StaffEmployee", foreign_keys=[activated_by])
    deactivator = relationship("StaffEmployee", foreign_keys=[deactivated_by])
    source_version = relationship("StaffNdaVersion", remote_side=[id], foreign_keys=[source_version_id])
    acceptances = relationship("StaffNdaAcceptance", back_populates="nda_version")
    
    def to_dict(self, include_content=False):
        # DC Protocol: Canonical staff types for display
        STAFF_TYPE_LABELS = {
            'MN_STAFF': 'MN Staff',
            'MN_EMPLOYEE': 'MN Employee',
            'FREELANCER': 'Freelancer',
            'MYNT_REAL': 'Mynt Real'
        }
        
        # Format applicable staff types for display
        staff_types = self.applicable_staff_types or []
        staff_type_labels = [STAFF_TYPE_LABELS.get(st, st) for st in staff_types]
        
        data = {
            "id": self.id,
            "version_number": self.version_number,
            "title": self.title,
            "status": self.status,
            "document_type": self.document_type or 'NDA',
            "applicable_staff_types": staff_types,
            "applicable_staff_types_display": staff_type_labels if staff_types else ["All Staff Types"],
            "effective_from": self.effective_from.isoformat() if self.effective_from else None,
            "created_by": self.created_by,
            "creator_name": self.creator.full_name if self.creator else None,
            "creator_code": self.creator.emp_code if self.creator else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "updated_by": self.updated_by,
            "updater_name": self.updater.full_name if self.updater else None,
            "source_version_id": self.source_version_id,
            "source_version_number": self.source_version.version_number if self.source_version else None,
            "activation_timestamp": self.activation_timestamp.isoformat() if self.activation_timestamp else None,
            "activated_by": self.activated_by,
            "activator_name": self.activator.full_name if self.activator else None,
            "deactivated_at": self.deactivated_at.isoformat() if self.deactivated_at else None,
            "deactivated_by": self.deactivated_by,
            "deactivator_name": self.deactivator.full_name if self.deactivator else None,
            "notes": self.notes,
            "acceptance_count": len(self.acceptances) if self.acceptances else 0
        }
        if include_content:
            data["content_html"] = self.content_html
        return data


class StaffNdaAcceptance(Base):
    """
    Staff NDA Acceptance Records
    DC: Immutable record of each employee's NDA acceptance
    - Stores acceptance snapshot for audit purposes
    - Captures IP address and user agent for security
    """
    __tablename__ = 'staff_nda_acceptances'
    
    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey('staff_employees.id', ondelete='CASCADE'), nullable=False, index=True)
    nda_version_id = Column(Integer, ForeignKey('staff_nda_versions.id', ondelete='CASCADE'), nullable=False, index=True)
    
    # Acceptance details
    accepted_at = Column(DateTime, default=get_indian_time, nullable=False)
    acceptance_ip = Column(String(64), nullable=True)
    acceptance_user_agent = Column(Text, nullable=True)
    
    # Snapshot of NDA content at acceptance time (immutable audit trail)
    acceptance_snapshot = Column(JSONB, nullable=True)  # {version, title, content_html}
    
    # DC-AGREEMENT-TYPE-001 (Jun 2026): Document type for multi-agreement tracking
    # Nullable for legacy NDA records (treated as 'NDA' if NULL)
    document_type = Column(String(50), nullable=True, index=True)
    
    # Employee details at acceptance time (for historical accuracy)
    employee_name_at_acceptance = Column(String(256), nullable=True)
    employee_code_at_acceptance = Column(String(32), nullable=True)
    employee_designation_at_acceptance = Column(String(128), nullable=True)
    employee_role_at_acceptance = Column(String(64), nullable=True)
    
    __table_args__ = (
        Index('idx_staff_nda_acceptance_emp', 'employee_id'),
        Index('idx_staff_nda_acceptance_version', 'nda_version_id'),
        Index('idx_staff_nda_acceptance_date', 'accepted_at'),
    )
    
    # Relationships
    employee = relationship("StaffEmployee", foreign_keys=[employee_id])
    nda_version = relationship("StaffNdaVersion", back_populates="acceptances")
    
    def to_dict(self):
        return {
            "id": self.id,
            "employee_id": self.employee_id,
            "employee_name": self.employee.full_name if self.employee else self.employee_name_at_acceptance,
            "employee_code": self.employee.emp_code if self.employee else self.employee_code_at_acceptance,
            "employee_designation": self.employee.designation if self.employee else self.employee_designation_at_acceptance,
            "employee_role": self.employee.role.role_name if self.employee and self.employee.role else self.employee_role_at_acceptance,
            "department_name": self.employee.department.name if self.employee and self.employee.department else None,
            "reporting_manager": self.employee.reporting_manager.full_name if self.employee and self.employee.reporting_manager else None,
            "nda_version_id": self.nda_version_id,
            "nda_version_number": self.nda_version.version_number if self.nda_version else None,
            "nda_title": self.nda_version.title if self.nda_version else None,
            "document_type": self.document_type or (self.nda_version.document_type if self.nda_version else 'NDA'),
            "accepted_at": self.accepted_at.isoformat() if self.accepted_at else None,
            "acceptance_ip": self.acceptance_ip,
            "employee_name_at_acceptance": self.employee_name_at_acceptance,
            "employee_code_at_acceptance": self.employee_code_at_acceptance,
            "employee_designation_at_acceptance": self.employee_designation_at_acceptance,
            "employee_role_at_acceptance": self.employee_role_at_acceptance
        }


class StaffNdaAudit(Base):
    """
    Staff NDA Audit Log (Immutable)
    DC: Complete audit trail for all NDA management operations
    - Tracks version creation, updates, activation, deactivation
    - Separate from acceptance records for admin action tracking
    """
    __tablename__ = 'staff_nda_audit'
    
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=get_indian_time, nullable=False, index=True)
    
    # Action details
    action = Column(String(64), nullable=False, index=True)  # created, updated, activated, deactivated, copied, deleted
    actor_emp_code = Column(String(32), nullable=False)
    actor_name = Column(String(256), nullable=False)
    
    # Target version
    target_version_id = Column(Integer, ForeignKey('staff_nda_versions.id', ondelete='SET NULL'), nullable=True)
    target_version_number = Column(String(16), nullable=True)
    
    # Change details
    old_value = Column(JSONB, nullable=True)
    new_value = Column(JSONB, nullable=True)
    description = Column(Text, nullable=True)
    
    # Request info
    ip_address = Column(String(64), nullable=True)
    user_agent = Column(Text, nullable=True)
    
    __table_args__ = (
        Index('idx_staff_nda_audit_action', 'action'),
        Index('idx_staff_nda_audit_actor', 'actor_emp_code'),
        Index('idx_staff_nda_audit_timestamp', 'timestamp'),
    )
    
    # Relationships
    target_version = relationship("StaffNdaVersion", foreign_keys=[target_version_id])
    
    def to_dict(self):
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "action": self.action,
            "actor_emp_code": self.actor_emp_code,
            "actor_name": self.actor_name,
            "target_version_id": self.target_version_id,
            "target_version_number": self.target_version_number or (self.target_version.version_number if self.target_version else None),
            "old_value": self.old_value,
            "new_value": self.new_value,
            "description": self.description,
            "ip_address": self.ip_address
        }


class StaffEmployeeDepartment(Base):
    """
    Staff Employee-Department Junction Table (Many-to-Many)
    DC: Allows employees to belong to multiple departments
    Created: Nov 29, 2025
    """
    __tablename__ = 'staff_employee_departments'
    
    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey('staff_employees.id', ondelete='CASCADE'), nullable=False, index=True)
    department_id = Column(Integer, ForeignKey('staff_departments.id', ondelete='CASCADE'), nullable=False, index=True)
    assigned_by = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    assigned_at = Column(DateTime, default=get_indian_time)
    
    __table_args__ = (
        Index('idx_emp_dept_unique', 'employee_id', 'department_id', unique=True),
    )
    
    employee = relationship("StaffEmployee", foreign_keys=[employee_id], overlaps="additional_departments")
    department = relationship("StaffDepartment", back_populates="employee_assignments")
    assigner = relationship("StaffEmployee", foreign_keys=[assigned_by], overlaps="additional_departments")
    
    def to_dict(self):
        return {
            "id": self.id,
            "employee_id": self.employee_id,
            "employee_name": self.employee.full_name if self.employee else None,
            "employee_code": self.employee.emp_code if self.employee else None,
            "department_id": self.department_id,
            "department_name": self.department.name if self.department else None,
            "department_code": self.department.department_code if self.department else None,
            "assigned_by": self.assigned_by,
            "assigned_by_name": self.assigner.full_name if self.assigner else None,
            "assigned_at": self.assigned_at.isoformat() if self.assigned_at else None
        }


class StaffDepartmentRole(Base):
    """
    Custom Roles within Departments
    DC: Department-specific role definitions with hierarchy permissions
    Created: Nov 29, 2025
    """
    __tablename__ = 'staff_department_roles'
    
    id = Column(Integer, primary_key=True, index=True)
    department_id = Column(Integer, ForeignKey('staff_departments.id', ondelete='CASCADE'), nullable=False, index=True)
    role_name = Column(String(100), nullable=False)
    role_description = Column(Text)
    hierarchy_permissions = Column(JSONB, default=[])  # [50, 60, 70] - which hierarchy levels can have this role
    created_by = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    created_at = Column(DateTime, default=get_indian_time)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time)
    
    __table_args__ = (
        Index('idx_dept_role_unique', 'department_id', 'role_name', unique=True),
    )
    
    department = relationship("StaffDepartment", back_populates="custom_roles")
    creator = relationship("StaffEmployee", foreign_keys=[created_by])
    
    def to_dict(self):
        return {
            "id": self.id,
            "department_id": self.department_id,
            "department_name": self.department.name if self.department else None,
            "role_name": self.role_name,
            "role_description": self.role_description,
            "hierarchy_permissions": self.hierarchy_permissions or [],
            "created_by": self.created_by,
            "created_by_name": self.creator.full_name if self.creator else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


def log_nda_audit(db, actor_emp_code, actor_name, action, target_version_id=None, 
                   target_version_number=None, old_value=None, new_value=None, 
                   description=None, ip_address=None, user_agent=None):
    """
    Helper function to create NDA audit log entries
    DC: Ensures consistent audit logging for all NDA operations
    """
    audit = StaffNdaAudit(
        actor_emp_code=actor_emp_code,
        actor_name=actor_name,
        action=action,
        target_version_id=target_version_id,
        target_version_number=target_version_number,
        old_value=old_value,
        new_value=new_value,
        description=description,
        ip_address=ip_address,
        user_agent=user_agent
    )
    db.add(audit)
    return audit


def get_active_nda_version(db):
    """
    Get the currently active NDA version (any type)
    DC: Legacy function - returns first active NDA regardless of staff type
    For staff type filtering, use get_active_nda_for_staff_type instead
    """
    return db.query(StaffNdaVersion).filter(
        StaffNdaVersion.status == 'active'
    ).first()


def get_active_nda_for_staff_type(db, staff_type: str, document_type: str = 'NDA'):
    """
    Get the currently active agreement version applicable to a specific staff type and document type.
    DC Protocol: Staff type-based NDA assignment (Dec 04, 2025)
    DC-AGREEMENT-TYPE-001 (Jun 2026): document_type filter added for multi-agreement support
    
    Logic (Priority Order):
    1. First, try to find version where staff_type is explicitly in applicable_staff_types
    2. If not found, fall back to version with empty [] (applies to all)
    3. Also handles NULL as equivalent to [] (backward compatibility)
    
    Args:
        db: Database session
        staff_type: Staff type to check (MN_STAFF, MN_EMPLOYEE, FREELANCER, MYNT_REAL)
        document_type: 'NDA' or 'EMPLOYMENT' (default 'NDA')
    
    Returns:
        StaffNdaVersion or None
    """
    from sqlalchemy import or_, desc
    
    # Valid staff types for validation (Dec 19, 2025)
    VALID_STAFF_TYPES = [
        'MN_STAFF', 'FREELANCER', 'MYNT_REAL', 'MN_EMPLOYEE',
        'VGK4U', 'EA', 'RVZ', 'ACCOUNTS', 'HR', 'SALES'
    ]
    
    if staff_type not in VALID_STAFF_TYPES:
        staff_type = 'MN_STAFF'
    
    # Priority 1: explicit staff type match for this document_type
    explicit_match = db.query(StaffNdaVersion).filter(
        StaffNdaVersion.status == 'active',
        StaffNdaVersion.document_type == document_type,
        StaffNdaVersion.applicable_staff_types.isnot(None),
        StaffNdaVersion.applicable_staff_types.contains([staff_type])
    ).order_by(desc(StaffNdaVersion.id)).first()
    
    if explicit_match:
        return explicit_match
    
    # Priority 2: global version of this document_type (empty/NULL = applies to all)
    global_version = db.query(StaffNdaVersion).filter(
        StaffNdaVersion.status == 'active',
        StaffNdaVersion.document_type == document_type,
        or_(
            StaffNdaVersion.applicable_staff_types == [],
            StaffNdaVersion.applicable_staff_types.is_(None)
        )
    ).order_by(desc(StaffNdaVersion.id)).first()
    
    return global_version


def check_nda_acceptance(db, employee_id, staff_type: str = None, document_type: str = 'NDA'):
    """
    Check if employee has accepted the latest active agreement of a given type.
    DC Protocol: Staff type-based NDA acceptance check (Dec 04, 2025)
    DC-AGREEMENT-TYPE-001 (Jun 2026): document_type param added
    
    Args:
        db: Database session
        employee_id: Employee ID to check
        staff_type: Optional staff type override. If None, fetches from employee record.
        document_type: 'NDA' or 'EMPLOYMENT' (default 'NDA')
    
    Returns:
        tuple (needs_acceptance: bool, version: StaffNdaVersion or None)
    """
    if staff_type is None:
        employee = db.query(StaffEmployee).filter(
            StaffEmployee.id == employee_id
        ).first()
        if employee:
            staff_type = employee.staff_type or 'MN_STAFF'
        else:
            staff_type = 'MN_STAFF'
    
    active_version = get_active_nda_for_staff_type(db, staff_type, document_type)
    
    if not active_version:
        return (False, None)
    
    acceptance = db.query(StaffNdaAcceptance).filter(
        StaffNdaAcceptance.employee_id == employee_id,
        StaffNdaAcceptance.nda_version_id == active_version.id
    ).first()
    
    if acceptance:
        return (False, active_version)
    else:
        return (True, active_version)


def check_all_pending_agreements(db, employee_id: int, staff_type: str = None):
    """
    Check all pending agreement types in priority order: NDA first, then Employment Agreement.
    DC-AGREEMENT-TYPE-001 (Jun 2026): Sequential multi-agreement gate.
    
    Returns first pending agreement so the gate can show them one at a time.
    
    Args:
        db: Database session
        employee_id: Employee ID to check
        staff_type: Optional staff type override
    
    Returns:
        tuple (needs_acceptance: bool, agreement_type: str or None, version: StaffNdaVersion or None)
    """
    if staff_type is None:
        employee = db.query(StaffEmployee).filter(StaffEmployee.id == employee_id).first()
        staff_type = (employee.staff_type or 'MN_STAFF') if employee else 'MN_STAFF'
    
    # Check NDA first, then Employment Agreement (sequential order)
    for doc_type in ['NDA', 'EMPLOYMENT']:
        needs, version = check_nda_acceptance(db, employee_id, staff_type, document_type=doc_type)
        if needs:
            return (True, doc_type, version)
    
    return (False, None, None)


def is_nda_applicable_to_staff_type(nda_version: StaffNdaVersion, staff_type: str) -> bool:
    """
    Check if an NDA version applies to a specific staff type.
    DC Protocol: Helper for staff type-based NDA filtering
    
    Args:
        nda_version: NDA version to check
        staff_type: Staff type to validate against
    
    Returns:
        bool: True if NDA applies to the staff type
    """
    applicable_types = nda_version.applicable_staff_types or []
    
    # Empty array means applies to all staff types (backward compatibility)
    if not applicable_types:
        return True
    
    return staff_type in applicable_types


class StaffEmployeeStatusHistory(Base):
    """
    Staff Employee Status Change History (Dec 2025)
    DC Protocol: WVV-compliant immutable audit trail for all status transitions
    - Tracks every status change (active, deactivated, resigned, etc.)
    - Records who made the change, when, and why
    - Cannot be modified or deleted (immutable audit log)
    """
    __tablename__ = 'staff_employee_status_history'
    
    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey('staff_employees.id', ondelete='CASCADE'), nullable=False, index=True)
    
    # Status transition details
    previous_status = Column(String(32), nullable=False)  # Status before change
    new_status = Column(String(32), nullable=False)       # Status after change
    
    # Actor details (who made the change)
    changed_by_id = Column(Integer, ForeignKey('staff_employees.id', ondelete='SET NULL'), nullable=True)
    changed_by_code = Column(String(32), nullable=False)  # Denormalized for audit integrity
    changed_by_name = Column(String(256), nullable=False)  # Denormalized for audit integrity
    changed_by_role = Column(String(64), nullable=True)   # Role at time of action
    
    # Reason and notes
    reason = Column(Text, nullable=False)  # Mandatory reason for status change
    notes = Column(Text, nullable=True)    # Optional additional notes
    
    # Metadata
    ip_address = Column(String(64), nullable=True)
    user_agent = Column(Text, nullable=True)
    
    # Timestamp (immutable)
    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    
    __table_args__ = (
        CheckConstraint(
            "previous_status IN ('active', 'inactive', 'suspended', 'terminated', 'deactivated', 'resigned')",
            name='staff_status_history_prev_check'
        ),
        CheckConstraint(
            "new_status IN ('active', 'inactive', 'suspended', 'terminated', 'deactivated', 'resigned')",
            name='staff_status_history_new_check'
        ),
        Index('idx_staff_status_history_emp', 'employee_id', 'created_at'),
    )
    
    employee = relationship("StaffEmployee", foreign_keys=[employee_id])
    changed_by = relationship("StaffEmployee", foreign_keys=[changed_by_id])
    
    def to_dict(self):
        return {
            "id": self.id,
            "employee_id": self.employee_id,
            "employee_code": self.employee.emp_code if self.employee else None,
            "employee_name": self.employee.full_name if self.employee else None,
            "previous_status": self.previous_status,
            "new_status": self.new_status,
            "changed_by_id": self.changed_by_id,
            "changed_by_code": self.changed_by_code,
            "changed_by_name": self.changed_by_name,
            "changed_by_role": self.changed_by_role,
            "reason": self.reason,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


def log_staff_status_change(db, employee, new_status, changed_by, reason, notes=None, ip_address=None, user_agent=None):
    """
    Helper function to log staff status changes
    DC Protocol: Creates immutable audit entry for status transitions
    
    Args:
        db: Database session
        employee: StaffEmployee object being changed
        new_status: New status value
        changed_by: StaffEmployee who made the change
        reason: Mandatory reason for the change
        notes: Optional additional notes
        ip_address: Request IP address
        user_agent: Request user agent
    
    Returns:
        StaffEmployeeStatusHistory entry
    """
    history = StaffEmployeeStatusHistory(
        employee_id=employee.id,
        previous_status=employee.status,
        new_status=new_status,
        changed_by_id=changed_by.id,
        changed_by_code=changed_by.emp_code,
        changed_by_name=changed_by.full_name,
        changed_by_role=changed_by.role.role_name if changed_by.role else None,
        reason=reason,
        notes=notes,
        ip_address=ip_address,
        user_agent=user_agent
    )
    db.add(history)
    return history


class StaffModuleMaster(Base):
    """
    Staff Module Master Catalog
    DC Protocol: Single source of truth for all available system modules
    Created: Dec 06, 2025 - Employee Module Assignment Feature
    
    Modules define accessible features/sections in the staff portal.
    Each module has a unique key and can be assigned to employees individually.
    """
    __tablename__ = 'staff_module_master'
    
    id = Column(Integer, primary_key=True, index=True)
    module_key = Column(String(64), unique=True, nullable=False, index=True)  # e.g., 'dashboard', 'attendance', 'journey_tracking'
    module_name = Column(String(128), nullable=False)  # Display name
    module_description = Column(Text, nullable=True)
    module_category = Column(String(64), nullable=True)  # e.g., 'core', 'hr', 'accounts', 'partners'
    module_icon = Column(String(64), nullable=True)  # Font Awesome icon class
    display_order = Column(Integer, default=0)  # Sort order in UI
    
    is_active = Column(Boolean, default=True)
    is_default = Column(Boolean, default=False)  # If true, assigned to all new employees by default
    
    created_at = Column(DateTime, default=get_indian_time)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time)
    
    __table_args__ = (
        Index('idx_staff_module_category', 'module_category'),
        Index('idx_staff_module_active', 'is_active'),
    )
    
    employee_assignments = relationship("StaffEmployeeModule", back_populates="module", cascade="all, delete-orphan")
    
    def to_dict(self):
        return {
            "id": self.id,
            "module_key": self.module_key,
            "module_name": self.module_name,
            "module_description": self.module_description,
            "module_category": self.module_category,
            "module_icon": self.module_icon,
            "display_order": self.display_order,
            "is_active": self.is_active,
            "is_default": self.is_default,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


class StaffEmployeeModule(Base):
    """
    Staff Employee-Module Junction Table (Many-to-Many)
    DC Protocol: Assigns individual modules to employees for granular access control
    Created: Dec 06, 2025 - Employee Module Assignment Feature
    
    This table tracks which modules are assigned to which employees.
    Includes full audit trail for compliance.
    """
    __tablename__ = 'staff_employee_modules'
    
    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey('staff_employees.id', ondelete='CASCADE'), nullable=False, index=True)
    module_id = Column(Integer, ForeignKey('staff_module_master.id', ondelete='CASCADE'), nullable=False, index=True)
    
    is_active = Column(Boolean, default=True)  # Soft delete capability
    
    assigned_by = Column(Integer, ForeignKey('staff_employees.id', ondelete='SET NULL'), nullable=True)
    assigned_at = Column(DateTime, default=get_indian_time)
    updated_by = Column(Integer, ForeignKey('staff_employees.id', ondelete='SET NULL'), nullable=True)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time)
    
    __table_args__ = (
        Index('idx_emp_module_unique', 'employee_id', 'module_id', unique=True),
        Index('idx_emp_module_active', 'employee_id', 'is_active'),
    )
    
    employee = relationship("StaffEmployee", foreign_keys=[employee_id], backref="assigned_modules")
    module = relationship("StaffModuleMaster", back_populates="employee_assignments")
    assigner = relationship("StaffEmployee", foreign_keys=[assigned_by])
    updater = relationship("StaffEmployee", foreign_keys=[updated_by])
    
    def to_dict(self):
        return {
            "id": self.id,
            "employee_id": self.employee_id,
            "employee_name": self.employee.full_name if self.employee else None,
            "employee_code": self.employee.emp_code if self.employee else None,
            "module_id": self.module_id,
            "module_key": self.module.module_key if self.module else None,
            "module_name": self.module.module_name if self.module else None,
            "is_active": self.is_active,
            "assigned_by": self.assigned_by,
            "assigned_by_name": self.assigner.full_name if self.assigner else None,
            "assigned_at": self.assigned_at.isoformat() if self.assigned_at else None,
            "updated_by": self.updated_by,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


class StaffEmployeeModuleAudit(Base):
    """
    Staff Employee Module Assignment Audit Log
    DC Protocol: Immutable audit trail for module assignment changes
    Created: Dec 06, 2025 - Employee Module Assignment Feature
    
    Tracks all module assignment/removal actions for compliance and audit.
    """
    __tablename__ = 'staff_employee_module_audit'
    
    id = Column(Integer, primary_key=True, index=True)
    
    employee_id = Column(Integer, ForeignKey('staff_employees.id', ondelete='SET NULL'), nullable=True, index=True)
    employee_code = Column(String(32), nullable=False)  # Denormalized for audit integrity
    employee_name = Column(String(256), nullable=False)  # Denormalized for audit integrity
    
    action = Column(String(32), nullable=False)  # 'ASSIGN', 'REMOVE', 'BULK_ASSIGN', 'BULK_REMOVE'
    module_keys = Column(JSONB, default=[])  # List of module keys affected
    
    performed_by_id = Column(Integer, ForeignKey('staff_employees.id', ondelete='SET NULL'), nullable=True)
    performed_by_code = Column(String(32), nullable=False)
    performed_by_name = Column(String(256), nullable=False)
    performed_by_role = Column(String(64), nullable=True)
    
    reason = Column(Text, nullable=True)  # Optional reason for change
    ip_address = Column(String(64), nullable=True)
    user_agent = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    
    __table_args__ = (
        Index('idx_emp_module_audit_employee', 'employee_id', 'created_at'),
        Index('idx_emp_module_audit_action', 'action'),
        Index('idx_emp_module_audit_performer', 'performed_by_id'),
    )
    
    def to_dict(self):
        return {
            "id": self.id,
            "employee_id": self.employee_id,
            "employee_code": self.employee_code,
            "employee_name": self.employee_name,
            "action": self.action,
            "module_keys": self.module_keys,
            "performed_by_id": self.performed_by_id,
            "performed_by_code": self.performed_by_code,
            "performed_by_name": self.performed_by_name,
            "performed_by_role": self.performed_by_role,
            "reason": self.reason,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


def log_employee_module_change(db, employee, action, module_keys, performed_by, reason=None, ip_address=None, user_agent=None):
    """
    Helper function to log employee module assignment changes
    DC Protocol: Creates immutable audit entry for module assignment changes
    
    Args:
        db: Database session
        employee: StaffEmployee object being changed
        action: Action type ('ASSIGN', 'REMOVE', 'BULK_ASSIGN', 'BULK_REMOVE')
        module_keys: List of module keys affected
        performed_by: StaffEmployee who made the change
        reason: Optional reason for the change
        ip_address: Request IP address
        user_agent: Request user agent
    
    Returns:
        StaffEmployeeModuleAudit entry
    """
    audit = StaffEmployeeModuleAudit(
        employee_id=employee.id,
        employee_code=employee.emp_code,
        employee_name=employee.full_name,
        action=action,
        module_keys=module_keys,
        performed_by_id=performed_by.id,
        performed_by_code=performed_by.emp_code,
        performed_by_name=performed_by.full_name,
        performed_by_role=performed_by.role.role_name if performed_by.role else None,
        reason=reason,
        ip_address=ip_address,
        user_agent=user_agent
    )
    db.add(audit)
    return audit


# Default Module Catalog (Dec 06, 2025)
# Used to seed the staff_module_master table
DEFAULT_STAFF_MODULES = [
    {"module_key": "dashboard", "module_name": "Dashboard", "module_category": "core", "module_icon": "fas fa-tachometer-alt", "display_order": 1, "is_default": True},
    {"module_key": "attendance", "module_name": "Attendance", "module_category": "hr", "module_icon": "fas fa-clock", "display_order": 10, "is_default": True},
    {"module_key": "my_attendance", "module_name": "My Attendance", "module_category": "hr", "module_icon": "fas fa-user-clock", "display_order": 11, "is_default": True},
    {"module_key": "team_attendance", "module_name": "Team Attendance", "module_category": "hr", "module_icon": "fas fa-users-clock", "display_order": 12, "is_default": False},
    {"module_key": "journey_tracking", "module_name": "Journey Tracking", "module_category": "hr", "module_icon": "fas fa-route", "display_order": 20, "is_default": False},
    {"module_key": "my_journeys", "module_name": "My Journeys", "module_category": "hr", "module_icon": "fas fa-map-marked-alt", "display_order": 21, "is_default": True},
    {"module_key": "team_journeys", "module_name": "Team Journeys", "module_category": "hr", "module_icon": "fas fa-map", "display_order": 22, "is_default": False},
    {"module_key": "location_tracking", "module_name": "Location Tracking", "module_category": "hr", "module_icon": "fas fa-map-marker-alt", "display_order": 25, "is_default": False},
    {"module_key": "kra_management", "module_name": "KRA Management", "module_category": "hr", "module_icon": "fas fa-bullseye", "display_order": 30, "is_default": False},
    {"module_key": "my_kras", "module_name": "My KRAs", "module_category": "hr", "module_icon": "fas fa-tasks", "display_order": 31, "is_default": True},
    {"module_key": "kra_review", "module_name": "KRA Review", "module_category": "hr", "module_icon": "fas fa-clipboard-check", "display_order": 32, "is_default": False},
    {"module_key": "task_management", "module_name": "Task Management", "module_category": "hr", "module_icon": "fas fa-list-check", "display_order": 40, "is_default": True},
    {"module_key": "tasks_assigned_by_me", "module_name": "Tasks Assigned By Me", "module_category": "hr", "module_icon": "fas fa-paper-plane", "display_order": 41, "is_default": True},
    {"module_key": "tasks_assigned_to_me", "module_name": "Tasks Assigned To Me", "module_category": "hr", "module_icon": "fas fa-inbox", "display_order": 42, "is_default": True},
    {"module_key": "timesheet", "module_name": "Timesheet", "module_category": "hr", "module_icon": "fas fa-calendar-alt", "display_order": 50, "is_default": True},
    {"module_key": "timesheet_approval", "module_name": "Timesheet Approval", "module_category": "hr", "module_icon": "fas fa-calendar-check", "display_order": 51, "is_default": False},
    {"module_key": "employee_directory", "module_name": "Employee Directory", "module_category": "hr", "module_icon": "fas fa-address-book", "display_order": 60, "is_default": False},
    {"module_key": "employee_management", "module_name": "Employee Management", "module_category": "admin", "module_icon": "fas fa-users-cog", "display_order": 70, "is_default": False},
    {"module_key": "department_management", "module_name": "Department Management", "module_category": "admin", "module_icon": "fas fa-sitemap", "display_order": 71, "is_default": False},
    {"module_key": "kyc_approvals", "module_name": "KYC Approvals", "module_category": "admin", "module_icon": "fas fa-id-card", "display_order": 72, "is_default": False},
    {"module_key": "nda_management", "module_name": "NDA Management", "module_category": "admin", "module_icon": "fas fa-file-signature", "display_order": 73, "is_default": False},
    {"module_key": "accounts", "module_name": "Accounts", "module_category": "accounts", "module_icon": "fas fa-calculator", "display_order": 100, "is_default": False},
    {"module_key": "companies", "module_name": "Companies", "module_category": "accounts", "module_icon": "fas fa-building", "display_order": 101, "is_default": False},
    {"module_key": "vendors", "module_name": "Vendors", "module_category": "accounts", "module_icon": "fas fa-truck", "display_order": 102, "is_default": False},
    {"module_key": "stock_items", "module_name": "Stock Items", "module_category": "inventory", "module_icon": "fas fa-boxes", "display_order": 116, "is_default": False},
    {"module_key": "stock_ledger", "module_name": "Stock Ledger", "module_category": "inventory", "module_icon": "fas fa-clipboard-list", "display_order": 117, "is_default": False},
    {"module_key": "stock_transfers", "module_name": "Stock Transfers", "module_category": "inventory", "module_icon": "fas fa-exchange-alt", "display_order": 118, "is_default": False},
    {"module_key": "segments", "module_name": "Segments", "module_category": "accounts", "module_icon": "fas fa-layer-group", "display_order": 104, "is_default": False},
    {"module_key": "pricing", "module_name": "Pricing", "module_category": "accounts", "module_icon": "fas fa-tags", "display_order": 105, "is_default": False},
    {"module_key": "income_entries", "module_name": "Income Entries", "module_category": "accounts", "module_icon": "fas fa-arrow-down", "display_order": 110, "is_default": False},
    {"module_key": "expense_entries", "module_name": "Expense Entries", "module_category": "accounts", "module_icon": "fas fa-arrow-up", "display_order": 111, "is_default": False},
    {"module_key": "fund_allocations", "module_name": "Fund Allocations", "module_category": "accounts", "module_icon": "fas fa-coins", "display_order": 112, "is_default": False},
    {"module_key": "payables", "module_name": "Payables", "module_category": "accounts", "module_icon": "fas fa-file-invoice-dollar", "display_order": 113, "is_default": False},
    {"module_key": "receivables", "module_name": "Receivables", "module_category": "accounts", "module_icon": "fas fa-hand-holding-usd", "display_order": 114, "is_default": False},
    {"module_key": "balance_sheet", "module_name": "Balance Sheet", "module_category": "accounts", "module_icon": "fas fa-balance-scale", "display_order": 115, "is_default": False},
    {"module_key": "bom", "module_name": "Bill of Materials", "module_category": "inventory", "module_icon": "fas fa-clipboard-list", "display_order": 120, "is_default": False},
    {"module_key": "manufacturing", "module_name": "Manufacturing", "module_category": "inventory", "module_icon": "fas fa-industry", "display_order": 121, "is_default": False},
    {"module_key": "partner_master", "module_name": "Partner Master", "module_category": "partners", "module_icon": "fas fa-handshake", "display_order": 130, "is_default": False},
    {"module_key": "partner_orders", "module_name": "Partner Orders", "module_category": "partners", "module_icon": "fas fa-file-invoice", "display_order": 131, "is_default": False},
    {"module_key": "partner_pricing", "module_name": "Partner Pricing", "module_category": "partners", "module_icon": "fas fa-tags", "display_order": 132, "is_default": False},
    {"module_key": "partner_approval", "module_name": "Order Approval", "module_category": "partners", "module_icon": "fas fa-clipboard-check", "display_order": 133, "is_default": False},
    {"module_key": "partner_routing", "module_name": "Order Routing", "module_category": "partners", "module_icon": "fas fa-route", "display_order": 134, "is_default": False},
    {"module_key": "partner_dispatch", "module_name": "Dispatch Management", "module_category": "partners", "module_icon": "fas fa-truck-loading", "display_order": 135, "is_default": False},
    {"module_key": "partner_invoices", "module_name": "Partner Invoices", "module_category": "partners", "module_icon": "fas fa-file-alt", "display_order": 136, "is_default": False},
    {"module_key": "partner_payments", "module_name": "Payment Verification", "module_category": "partners", "module_icon": "fas fa-credit-card", "display_order": 137, "is_default": False},
    {"module_key": "announcements", "module_name": "Announcements", "module_category": "core", "module_icon": "fas fa-bullhorn", "display_order": 200, "is_default": True},
    {"module_key": "settings", "module_name": "Settings", "module_category": "core", "module_icon": "fas fa-cog", "display_order": 250, "is_default": True},
    {"module_key": "audit_logs", "module_name": "Audit Logs", "module_category": "admin", "module_icon": "fas fa-history", "display_order": 260, "is_default": False},
    {"module_key": "reports", "module_name": "Reports", "module_category": "core", "module_icon": "fas fa-chart-bar", "display_order": 270, "is_default": False},
]


def seed_module_master(db):
    """
    Seed the staff_module_master table with default modules
    DC Protocol: Ensures consistent module catalog across environments
    
    This function should be called during database initialization or migration.
    It will only add modules that don't already exist (safe for re-runs).
    """
    from sqlalchemy.exc import IntegrityError
    
    added_count = 0
    for module_data in DEFAULT_STAFF_MODULES:
        existing = db.query(StaffModuleMaster).filter_by(module_key=module_data['module_key']).first()
        if not existing:
            module = StaffModuleMaster(
                module_key=module_data['module_key'],
                module_name=module_data['module_name'],
                module_category=module_data.get('module_category'),
                module_icon=module_data.get('module_icon'),
                display_order=module_data.get('display_order', 0),
                is_default=module_data.get('is_default', False),
                is_active=True
            )
            db.add(module)
            added_count += 1
    
    try:
        db.commit()
        return added_count
    except IntegrityError:
        db.rollback()
        return 0


# ============================================================================
# RVZ MENU VISIBILITY & ACCESSIBILITY CONTROL SYSTEM
# DC Protocol: Company-wise menu/page access control per employee
# Created: Dec 08, 2025 - Phase 7 Enhancement
# Updated: Dec 26, 2025 - Dynamic Menu Registry System
# ============================================================================


class StaffMenuRegistry(Base):
    """
    Global Menu Registry - System Default Source of Truth
    DC Protocol: Canonical registry of ALL system pages (company-agnostic)
    WVV Protocol: Validated entries with discovery tracking
    
    This table is the SINGLE SOURCE OF TRUTH for all pages in the system.
    - Automatically populated by sidebar discovery service on startup
    - When a new page is added to any sidebar, it gets auto-discovered here
    - StaffMenuMaster per-company entries are synced FROM this registry
    
    source values:
    - 'static': Defined in DEFAULT_STAFF_MENUS (legacy entries)
    - 'discovered': Auto-discovered from sidebar configurations
    - 'manual': Manually added via admin interface
    """
    __tablename__ = 'staff_menu_registry'
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Unique identifier for the menu item
    menu_code = Column(String(64), nullable=False, unique=True, index=True)
    menu_name = Column(String(128), nullable=False)
    menu_description = Column(Text, nullable=True)
    route_path = Column(String(256), nullable=False, index=True)
    
    # Categorization
    menu_category = Column(String(64), nullable=True, index=True)
    menu_icon = Column(String(64), nullable=True)
    display_order = Column(Integer, default=0)
    
    # Sidebar Section Grouping (DC Protocol: Dynamic Menu Registry)
    sidebar_section = Column(String(64), nullable=True, index=True)  # e.g., 'supreme-admin', 'configuration'
    sidebar_section_title = Column(String(128), nullable=True)  # e.g., 'SUPREME ADMIN', 'CONFIGURATION'
    sidebar_section_order = Column(Integer, default=0)  # Order of section in sidebar
    
    # DC Jan 2026: Menu nesting support for ZYNOVA/MNR hierarchical menus
    menu_type = Column(String(32), default='STAFF', nullable=True)  # 'STAFF' or 'MNR'
    parent_section = Column(String(64), nullable=True, index=True)  # e.g., 'zynova', 'mnr' for nested submenus
    is_submenu = Column(Boolean, default=False, nullable=True)  # True if this section nests under parent_section
    
    # Audience scope: 'staff', 'partner', 'shared', 'user' (MNR members)
    audience_scope = Column(String(20), default='staff', nullable=False, index=True)
    
    # Discovery source tracking
    source = Column(String(20), default='static', nullable=False)
    source_file = Column(String(256), nullable=True)  # e.g., 'rvz.js', 'staff_sidebar.js'
    
    # Default visibility flags (applied when syncing to companies)
    is_default_visible = Column(Boolean, default=False)
    is_default_accessible = Column(Boolean, default=False)
    
    # Status
    is_active = Column(Boolean, default=True, index=True)
    is_system_default = Column(Boolean, default=True)  # Protects system pages from deletion
    
    # Audit
    created_at = Column(DateTime, default=get_indian_time)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time)
    last_discovered_at = Column(DateTime, nullable=True)  # Last time discovery found this entry
    
    __table_args__ = (
        Index('idx_menu_registry_route', 'route_path'),
        Index('idx_menu_registry_category', 'menu_category'),
        Index('idx_menu_registry_source', 'source'),
        Index('idx_menu_registry_active', 'is_active'),
    )
    
    def to_dict(self):
        return {
            "id": self.id,
            "menu_code": self.menu_code,
            "menu_name": self.menu_name,
            "menu_description": self.menu_description,
            "route_path": self.route_path,
            "menu_category": self.menu_category,
            "menu_icon": self.menu_icon,
            "display_order": self.display_order,
            "sidebar_section": self.sidebar_section,
            "sidebar_section_title": self.sidebar_section_title,
            "sidebar_section_order": self.sidebar_section_order,
            "menu_type": self.menu_type,
            "parent_section": self.parent_section,
            "is_submenu": self.is_submenu,
            "audience_scope": self.audience_scope,
            "source": self.source,
            "source_file": self.source_file,
            "is_default_visible": self.is_default_visible,
            "is_default_accessible": self.is_default_accessible,
            "is_active": self.is_active,
            "is_system_default": self.is_system_default,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "last_discovered_at": self.last_discovered_at.isoformat() if self.last_discovered_at else None
        }


class StaffRoleMenuAccess(Base):
    """
    Internal Section Role-Based Menu Access Control
    DC Protocol: VGK Mentor controls which Internal section pages EA role can access.
    - Only applies to sidebar_section = 'internal'
    - VGK Mentor (vgk4u) always sees all internal pages via supreme access
    - EA (ea) sees only pages explicitly enabled by VGK Mentor here
    - All other roles never see the internal section
    """
    __tablename__ = 'staff_role_menu_access'

    id = Column(Integer, primary_key=True, index=True)
    role_code = Column(String(64), nullable=False)
    route_path = Column(String(256), nullable=False)
    is_enabled = Column(Boolean, default=False, nullable=False)
    updated_by_emp_code = Column(String(32), nullable=True)
    updated_by_name = Column(String(256), nullable=True)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time)

    __table_args__ = (
        UniqueConstraint('role_code', 'route_path', name='uq_role_menu_access'),
    )


class StaffMenuMaster(Base):
    """
    Staff Menu Master Catalog
    DC Protocol: Centralized registry of all pages/menus with company-wise segregation
    
    This table holds the master list of all pages/menus in the system.
    RVZ can control visibility and accessibility per employee and partner.
    
    audience_scope values:
    - 'staff': Pages only for staff employees (partners see N/A)
    - 'partner': Pages only for official partners (staff see N/A)
    - 'shared': Pages for both staff and partners
    """
    __tablename__ = 'staff_menu_master'
    
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey('associated_companies.id', ondelete='CASCADE'), nullable=False, index=True)
    
    menu_code = Column(String(64), nullable=False, index=True)
    menu_name = Column(String(128), nullable=False)
    menu_description = Column(Text, nullable=True)
    route_path = Column(String(256), nullable=True)
    
    parent_id = Column(Integer, ForeignKey('staff_menu_master.id', ondelete='SET NULL'), nullable=True)
    menu_category = Column(String(64), nullable=True)
    menu_icon = Column(String(64), nullable=True)
    display_order = Column(Integer, default=0)
    
    # DC Protocol: Audience scope for staff vs partner page separation
    # Values: 'staff', 'partner', 'shared'
    audience_scope = Column(String(20), default='staff', nullable=False, index=True)
    
    is_active = Column(Boolean, default=True)
    # Zero-Default Access Policy: New menus are hidden by default until EA/VGK grants explicit access
    is_default_visible = Column(Boolean, default=False)
    is_default_accessible = Column(Boolean, default=False)

    # DC Protocol: Sidebar grouping — mirrors StaffMenuRegistry sidebar_section columns
    sidebar_section = Column(String(64), nullable=True, index=True)
    sidebar_section_title = Column(String(128), nullable=True)
    sidebar_section_order = Column(Integer, default=0)

    created_at = Column(DateTime, default=get_indian_time)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time)
    
    __table_args__ = (
        Index('idx_staff_menu_company', 'company_id'),
        Index('idx_staff_menu_code_company', 'menu_code', 'company_id', unique=True),
        Index('idx_staff_menu_parent', 'parent_id'),
        Index('idx_staff_menu_category', 'menu_category'),
    )
    
    parent = relationship("StaffMenuMaster", remote_side=[id], backref="children")
    employee_settings = relationship("StaffEmployeeMenuSettings", back_populates="menu", cascade="all, delete-orphan")
    
    def to_dict(self):
        return {
            "id": self.id,
            "company_id": self.company_id,
            "menu_code": self.menu_code,
            "menu_name": self.menu_name,
            "menu_description": self.menu_description,
            "route_path": self.route_path,
            "parent_id": self.parent_id,
            "parent_name": self.parent.menu_name if self.parent else None,
            "menu_category": self.menu_category,
            "menu_icon": self.menu_icon,
            "display_order": self.display_order,
            "audience_scope": self.audience_scope,
            "is_active": self.is_active,
            "default_can_view": self.is_default_visible,
            "default_can_edit": self.is_default_accessible,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


class StaffEmployeeMenuSettings(Base):
    """
    Staff Employee Menu Settings
    DC Protocol: Per-employee View/Edit permissions for menus/pages
    
    This table stores individual employee settings for each menu.
    - can_view: Controls whether the employee can view/access the page (read-only)
    - can_edit: Controls whether the employee can make changes (create/update/delete)
    """
    __tablename__ = 'staff_employee_menu_settings'
    
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey('associated_companies.id', ondelete='CASCADE'), nullable=False, index=True)
    
    employee_id = Column(Integer, ForeignKey('staff_employees.id', ondelete='CASCADE'), nullable=False, index=True)
    menu_id = Column(Integer, ForeignKey('staff_menu_master.id', ondelete='CASCADE'), nullable=False, index=True)
    
    can_view = Column(Boolean, default=True)
    can_edit = Column(Boolean, default=False)
    is_overridden = Column(Boolean, default=False)
    
    set_by_id = Column(Integer, ForeignKey('staff_employees.id', ondelete='SET NULL'), nullable=True)
    set_by_code = Column(String(32), nullable=True)
    set_by_name = Column(String(256), nullable=True)
    
    created_at = Column(DateTime, default=get_indian_time)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time)
    
    __table_args__ = (
        Index('idx_emp_menu_settings_company', 'company_id'),
        Index('idx_emp_menu_settings_employee', 'employee_id'),
        Index('idx_emp_menu_settings_unique', 'employee_id', 'menu_id', unique=True),
    )
    
    employee = relationship("StaffEmployee", foreign_keys=[employee_id], backref="menu_settings")
    menu = relationship("StaffMenuMaster", back_populates="employee_settings")
    set_by = relationship("StaffEmployee", foreign_keys=[set_by_id])
    
    def to_dict(self):
        return {
            "id": self.id,
            "company_id": self.company_id,
            "employee_id": self.employee_id,
            "employee_code": self.employee.emp_code if self.employee else None,
            "employee_name": self.employee.full_name if self.employee else None,
            "menu_id": self.menu_id,
            "menu_code": self.menu.menu_code if self.menu else None,
            "menu_name": self.menu.menu_name if self.menu else None,
            "can_view": self.can_view,
            "can_edit": self.can_edit,
            "is_overridden": self.is_overridden,
            "set_by_id": self.set_by_id,
            "set_by_code": self.set_by_code,
            "set_by_name": self.set_by_name,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


class PartnerMenuSettings(Base):
    """
    Official Partner Menu Settings
    DC Protocol: Per-partner View/Edit permissions for menus/pages
    
    This table stores individual partner settings for each menu.
    - can_view: Controls whether the partner can view/access the page (read-only)
    - can_edit: Controls whether the partner can make changes (create/update/delete)
    
    Partners are separated from staff employees to maintain DC Protocol segregation.
    """
    __tablename__ = 'partner_menu_settings'
    
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey('associated_companies.id', ondelete='CASCADE'), nullable=False, index=True)
    
    partner_id = Column(Integer, ForeignKey('official_partners.id', ondelete='CASCADE'), nullable=False, index=True)
    menu_id = Column(Integer, ForeignKey('staff_menu_master.id', ondelete='CASCADE'), nullable=False, index=True)
    
    can_view = Column(Boolean, default=True)
    can_edit = Column(Boolean, default=False)
    is_overridden = Column(Boolean, default=False)
    
    set_by_id = Column(Integer, ForeignKey('staff_employees.id', ondelete='SET NULL'), nullable=True)
    set_by_code = Column(String(32), nullable=True)
    set_by_name = Column(String(256), nullable=True)
    
    created_at = Column(DateTime, default=get_indian_time)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time)
    
    __table_args__ = (
        Index('idx_partner_menu_settings_company', 'company_id'),
        Index('idx_partner_menu_settings_partner', 'partner_id'),
        Index('idx_partner_menu_settings_unique', 'partner_id', 'menu_id', unique=True)  # DC Protocol (Dec 30, 2025): Company-agnostic like StaffEmployeeMenuSettings,
    )
    
    menu = relationship("StaffMenuMaster")
    set_by = relationship("StaffEmployee", foreign_keys=[set_by_id])
    
    def to_dict(self):
        return {
            "id": self.id,
            "company_id": self.company_id,
            "partner_id": self.partner_id,
            "menu_id": self.menu_id,
            "menu_code": self.menu.menu_code if self.menu else None,
            "menu_name": self.menu.menu_name if self.menu else None,
            "can_view": self.can_view,
            "can_edit": self.can_edit,
            "is_overridden": self.is_overridden,
            "set_by_id": self.set_by_id,
            "set_by_code": self.set_by_code,
            "set_by_name": self.set_by_name,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


class StaffMenuSettingsAudit(Base):
    """
    Staff Menu Settings Audit Log
    DC Protocol: Immutable audit trail for menu visibility/accessibility changes
    
    Tracks all changes to employee menu settings for compliance and audit.
    """
    __tablename__ = 'staff_menu_settings_audit'
    
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey('associated_companies.id', ondelete='SET NULL'), nullable=True, index=True)
    
    employee_id = Column(Integer, ForeignKey('staff_employees.id', ondelete='SET NULL'), nullable=True, index=True)
    employee_code = Column(String(32), nullable=False)
    employee_name = Column(String(256), nullable=False)
    
    action = Column(String(32), nullable=False)
    menu_changes = Column(JSONB, default=[])
    
    performed_by_id = Column(Integer, ForeignKey('staff_employees.id', ondelete='SET NULL'), nullable=True)
    performed_by_code = Column(String(32), nullable=False)
    performed_by_name = Column(String(256), nullable=False)
    performed_by_role = Column(String(64), nullable=True)
    
    reason = Column(Text, nullable=True)
    ip_address = Column(String(64), nullable=True)
    user_agent = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    
    __table_args__ = (
        Index('idx_menu_audit_company', 'company_id'),
        Index('idx_menu_audit_employee', 'employee_id', 'created_at'),
        Index('idx_menu_audit_action', 'action'),
        Index('idx_menu_audit_performer', 'performed_by_id'),
    )
    
    def to_dict(self):
        return {
            "id": self.id,
            "company_id": self.company_id,
            "employee_id": self.employee_id,
            "employee_code": self.employee_code,
            "employee_name": self.employee_name,
            "action": self.action,
            "menu_changes": self.menu_changes,
            "performed_by_id": self.performed_by_id,
            "performed_by_code": self.performed_by_code,
            "performed_by_name": self.performed_by_name,
            "performed_by_role": self.performed_by_role,
            "reason": self.reason,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class StaffMnrUserAuditLog(Base):
    """
    Staff MNR User Sidebar Audit Log
    DC Protocol: Immutable audit trail for all staff actions on MNR member data
    Created: Jan 08, 2026
    
    Tracks all access and actions by staff on MNR member accounts for compliance.
    """
    __tablename__ = 'staff_mnr_user_audit_log'
    
    id = Column(Integer, primary_key=True, index=True)
    
    staff_employee_id = Column(Integer, ForeignKey('staff_employees.id', ondelete='SET NULL'), nullable=True, index=True)
    staff_emp_code = Column(String(32), nullable=False)
    
    mnr_user_id = Column(String(20), nullable=False, index=True)
    
    action_type = Column(String(50), nullable=False)
    action_details = Column(Text, nullable=True)
    page_accessed = Column(String(100), nullable=True)
    
    request_data = Column(JSONB, default={})
    response_summary = Column(Text, nullable=True)
    
    ip_address = Column(String(64), nullable=True)
    user_agent = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=get_indian_time, nullable=False, index=True)
    
    staff_employee = relationship("StaffEmployee", foreign_keys=[staff_employee_id])
    
    __table_args__ = (
        Index('idx_mnr_audit_staff', 'staff_employee_id', 'created_at'),
        Index('idx_mnr_audit_member', 'mnr_user_id', 'created_at'),
        Index('idx_mnr_audit_action', 'action_type', 'created_at'),
    )
    
    def to_dict(self):
        return {
            "id": self.id,
            "staff_employee_id": self.staff_employee_id,
            "staff_emp_code": self.staff_emp_code,
            "mnr_user_id": self.mnr_user_id,
            "action_type": self.action_type,
            "action_details": self.action_details,
            "page_accessed": self.page_accessed,
            "ip_address": self.ip_address,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


DEFAULT_STAFF_MENUS = [
    # ===================== RVZ SUPREME ADMIN (1-49) =====================
    {"menu_code": "rvz_dashboard", "menu_name": "RVZ Dashboard", "menu_category": "rvz", "menu_icon": "fas fa-tachometer-alt", "route_path": "/rvz/dashboard", "display_order": 1},
    {"menu_code": "rvz_menu_access", "menu_name": "Menu Access Control", "menu_category": "rvz", "menu_icon": "fas fa-shield-alt", "route_path": "/rvz/menu-access-config", "display_order": 2},
    {"menu_code": "rvz_department_management", "menu_name": "Department Management", "menu_category": "rvz", "menu_icon": "fas fa-sitemap", "route_path": "/rvz/department-management", "display_order": 3},
    {"menu_code": "rvz_signup_categories", "menu_name": "Signup Categories", "menu_category": "rvz", "menu_icon": "fas fa-layer-group", "route_path": "/staff/signup-categories", "display_order": 4},
    {"menu_code": "rvz_banners_management", "menu_name": "Banners Management", "menu_category": "rvz", "menu_icon": "fas fa-images", "route_path": "/rvz/banners-management", "display_order": 5},
    {"menu_code": "rvz_crm_leads", "menu_name": "CRM Leads", "menu_category": "rvz", "menu_icon": "fas fa-funnel-dollar", "route_path": "/rvz/crm-leads", "display_order": 7},
    # Real Dreams RVZ Pages
    {"menu_code": "rvz_real_dreams_dashboard", "menu_name": "Real Dreams Dashboard", "menu_category": "rvz_real_dreams", "menu_icon": "fas fa-home", "route_path": "/rvz/real-dreams-dashboard", "display_order": 10},
    {"menu_code": "rvz_real_dreams_partners", "menu_name": "Real Dreams Partners", "menu_category": "rvz_real_dreams", "menu_icon": "fas fa-handshake", "route_path": "/rvz/real-dreams-partners", "display_order": 11},
    {"menu_code": "rvz_real_dreams_properties", "menu_name": "Real Dreams Properties", "menu_category": "rvz_real_dreams", "menu_icon": "fas fa-building", "route_path": "/rvz/real-dreams-properties", "display_order": 12},
    
    # ===================== ADMIN PAGES (50-99) =====================
    {"menu_code": "admin_dashboard", "menu_name": "Admin Dashboard", "menu_category": "admin", "menu_icon": "fas fa-tachometer-alt", "route_path": "/admin/dashboard", "display_order": 50},
    {"menu_code": "admin_users", "menu_name": "User Management", "menu_category": "admin", "menu_icon": "fas fa-users", "route_path": "/admin/users", "display_order": 51},
    {"menu_code": "admin_members_all", "menu_name": "All Members", "menu_category": "admin_members", "menu_icon": "fas fa-users", "route_path": "/admin/members-all", "display_order": 52},
    {"menu_code": "admin_members_search", "menu_name": "Member Search", "menu_category": "admin_members", "menu_icon": "fas fa-search", "route_path": "/admin/members-search", "display_order": 53},
    {"menu_code": "admin_members_direct", "menu_name": "Direct Members", "menu_category": "admin_members", "menu_icon": "fas fa-user-friends", "route_path": "/admin/members-direct", "display_order": 54},
    {"menu_code": "admin_members_ved", "menu_name": "Ved Members", "menu_category": "admin_members", "menu_icon": "fas fa-users-cog", "route_path": "/admin/members-ved", "display_order": 55},
    {"menu_code": "admin_members_picture", "menu_name": "Member Pictures", "menu_category": "admin_members", "menu_icon": "fas fa-images", "route_path": "/admin/members-picture", "display_order": 56},
    {"menu_code": "admin_kyc_management", "menu_name": "KYC Management", "menu_category": "admin", "menu_icon": "fas fa-id-card", "route_path": "/admin/kyc-management", "display_order": 57},
    {"menu_code": "admin_bank_pending", "menu_name": "Bank Pending", "menu_category": "admin_bank", "menu_icon": "fas fa-clock", "route_path": "/admin/bank-pending", "display_order": 58},
    {"menu_code": "admin_bank_all", "menu_name": "All Bank Details", "menu_category": "admin_bank", "menu_icon": "fas fa-university", "route_path": "/admin/bank-all", "display_order": 59},
    {"menu_code": "admin_user_status", "menu_name": "User Status", "menu_category": "admin", "menu_icon": "fas fa-user-check", "route_path": "/admin/user-status", "display_order": 60},
    {"menu_code": "admin_password_reset", "menu_name": "Password Reset", "menu_category": "admin", "menu_icon": "fas fa-key", "route_path": "/admin/password-reset", "display_order": 61},
    {"menu_code": "admin_delete_management", "menu_name": "Delete Management", "menu_category": "admin", "menu_icon": "fas fa-trash-alt", "route_path": "/admin/delete-management", "display_order": 62},
    # Admin Awards
    {"menu_code": "admin_awards", "menu_name": "Awards Overview", "menu_category": "admin_awards", "menu_icon": "fas fa-trophy", "route_path": "/admin/awards", "display_order": 63},
    {"menu_code": "admin_awards_all", "menu_name": "All Awards", "menu_category": "admin_awards", "menu_icon": "fas fa-list", "route_path": "/admin/awards-all", "display_order": 64},
    {"menu_code": "admin_awards_userwise", "menu_name": "Awards by User", "menu_category": "admin_awards", "menu_icon": "fas fa-user-tag", "route_path": "/admin/awards-userwise", "display_order": 65},
    {"menu_code": "admin_awards_awardwise", "menu_name": "Awards by Type", "menu_category": "admin_awards", "menu_icon": "fas fa-medal", "route_path": "/admin/awards-awardwise", "display_order": 66},
    {"menu_code": "admin_awards_bonanza", "menu_name": "Bonanza Awards", "menu_category": "admin_awards", "menu_icon": "fas fa-gift", "route_path": "/admin/awards-bonanza", "display_order": 67},
    {"menu_code": "admin_bonanza_claims", "menu_name": "Bonanza Claims", "menu_category": "admin_awards", "menu_icon": "fas fa-hand-holding-heart", "route_path": "/admin/bonanza-claims", "display_order": 68},
    # Admin Earnings
    {"menu_code": "admin_earnings_summary", "menu_name": "Earnings Summary", "menu_category": "admin_earnings", "menu_icon": "fas fa-chart-line", "route_path": "/admin/earnings-summary", "display_order": 70},
    {"menu_code": "admin_earnings_direct", "menu_name": "Direct Earnings", "menu_category": "admin_earnings", "menu_icon": "fas fa-arrow-right", "route_path": "/admin/earnings-direct", "display_order": 71},
    {"menu_code": "admin_earnings_matching", "menu_name": "Matching Earnings", "menu_category": "admin_earnings", "menu_icon": "fas fa-arrows-alt-h", "route_path": "/admin/earnings-matching", "display_order": 72},
    {"menu_code": "admin_earnings_ved", "menu_name": "Ved Earnings", "menu_category": "admin_earnings", "menu_icon": "fas fa-layer-group", "route_path": "/admin/earnings-ved", "display_order": 73},
    {"menu_code": "admin_earnings_gurudakshina", "menu_name": "Guru Dakshina", "menu_category": "admin_earnings", "menu_icon": "fas fa-praying-hands", "route_path": "/admin/earnings-gurudakshina", "display_order": 74},
    {"menu_code": "admin_earnings_withdrawals", "menu_name": "Withdrawals", "menu_category": "admin_earnings", "menu_icon": "fas fa-money-bill-wave", "route_path": "/admin/earnings-withdrawals", "display_order": 75},
    {"menu_code": "admin_field_allowances", "menu_name": "Field Allowances", "menu_category": "admin_earnings", "menu_icon": "fas fa-car", "route_path": "/admin/field-allowances", "display_order": 76},
    # Admin Coupons
    {"menu_code": "admin_coupons_status", "menu_name": "Coupon Status", "menu_category": "admin_coupons", "menu_icon": "fas fa-ticket-alt", "route_path": "/admin/coupons-status", "display_order": 77},
    {"menu_code": "admin_coupons_activate", "menu_name": "Activate Coupons", "menu_category": "admin_coupons", "menu_icon": "fas fa-check-circle", "route_path": "/admin/coupons-activate", "display_order": 78},
    {"menu_code": "admin_coupons_transfer", "menu_name": "Transfer Coupons", "menu_category": "admin_coupons", "menu_icon": "fas fa-exchange-alt", "route_path": "/admin/coupons-transfer", "display_order": 79},
    {"menu_code": "admin_coupons_buy", "menu_name": "Buy Coupons", "menu_category": "admin_coupons", "menu_icon": "fas fa-shopping-cart", "route_path": "/admin/coupons-buy", "display_order": 80},
    {"menu_code": "admin_coupons_progress", "menu_name": "Coupon Progress", "menu_category": "admin_coupons", "menu_icon": "fas fa-tasks", "route_path": "/admin/coupons-progress", "display_order": 81},
    # Admin Other
    {"menu_code": "admin_tickets_management", "menu_name": "Tickets Management", "menu_category": "admin", "menu_icon": "fas fa-headset", "route_path": "/admin/tickets-management", "display_order": 82},
    {"menu_code": "admin_tickets_assigned", "menu_name": "Assigned Tickets", "menu_category": "admin", "menu_icon": "fas fa-user-clock", "route_path": "/admin/tickets-assigned", "display_order": 83},
    {"menu_code": "admin_banners_management", "menu_name": "Banners Management", "menu_category": "admin", "menu_icon": "fas fa-images", "route_path": "/admin/banners-management", "display_order": 84},
    {"menu_code": "admin_popups", "menu_name": "Popups", "menu_category": "admin", "menu_icon": "fas fa-window-restore", "route_path": "/admin/popups", "display_order": 85},
    {"menu_code": "admin_birthdays", "menu_name": "Birthdays", "menu_category": "admin", "menu_icon": "fas fa-birthday-cake", "route_path": "/admin/birthdays", "display_order": 86},
    {"menu_code": "admin_reports", "menu_name": "Reports", "menu_category": "admin", "menu_icon": "fas fa-chart-bar", "route_path": "/admin/reports", "display_order": 87},
    {"menu_code": "admin_income_pending", "menu_name": "Income Pending", "menu_category": "admin", "menu_icon": "fas fa-hourglass-half", "route_path": "/admin/income-pending", "display_order": 88},
    {"menu_code": "admin_income_verified", "menu_name": "Income Verified", "menu_category": "admin", "menu_icon": "fas fa-check-double", "route_path": "/admin/income-verified", "display_order": 89},
    {"menu_code": "admin_feedback_pending", "menu_name": "Pending Announcements", "menu_category": "admin", "menu_icon": "fas fa-comment-dots", "route_path": "/admin/feedback-pending", "display_order": 90},
    {"menu_code": "admin_view_announcements", "menu_name": "View Announcements", "menu_category": "admin", "menu_icon": "fas fa-bullhorn", "route_path": "/admin/view-announcements", "display_order": 91},
    {"menu_code": "admin_expense_categories", "menu_name": "Expense Categories", "menu_category": "admin", "menu_icon": "fas fa-folder", "route_path": "/admin/expense-categories", "display_order": 92},
    {"menu_code": "admin_emergency_wallet", "menu_name": "Emergency Wallet", "menu_category": "admin", "menu_icon": "fas fa-ambulance", "route_path": "/admin/emergency-wallet", "display_order": 93},
    {"menu_code": "admin_data_recovery", "menu_name": "Data Recovery", "menu_category": "admin", "menu_icon": "fas fa-database", "route_path": "/admin/data-recovery", "display_order": 94},
    {"menu_code": "admin_ev_benefit_analytics", "menu_name": "EV Benefit Analytics", "menu_category": "admin", "menu_icon": "fas fa-car-battery", "route_path": "/admin/ev-benefit-analytics", "display_order": 95},
    
    # ===================== SUPER ADMIN PAGES (100-119) =====================
    {"menu_code": "superadmin_dashboard", "menu_name": "Super Admin Dashboard", "menu_category": "superadmin", "menu_icon": "fas fa-crown", "route_path": "/superadmin/dashboard", "display_order": 100},
    {"menu_code": "superadmin_global_config", "menu_name": "Global Configuration", "menu_category": "superadmin", "menu_icon": "fas fa-cogs", "route_path": "/superadmin/global-config", "display_order": 101},
    {"menu_code": "superadmin_system_health", "menu_name": "System Health", "menu_category": "superadmin", "menu_icon": "fas fa-heartbeat", "route_path": "/superadmin/system-health", "display_order": 102},
    {"menu_code": "superadmin_awards_approval", "menu_name": "Awards Approval", "menu_category": "superadmin", "menu_icon": "fas fa-stamp", "route_path": "/superadmin/awards-approval", "display_order": 103},
    {"menu_code": "superadmin_password_reset", "menu_name": "Password Reset", "menu_category": "superadmin", "menu_icon": "fas fa-key", "route_path": "/superadmin/password-reset", "display_order": 104},
    {"menu_code": "superadmin_placement_approvals", "menu_name": "Placement Approvals", "menu_category": "superadmin", "menu_icon": "fas fa-user-check", "route_path": "/superadmin/placement-approvals", "display_order": 105},
    {"menu_code": "superadmin_red_id_oversight", "menu_name": "Red ID Oversight", "menu_category": "superadmin", "menu_icon": "fas fa-exclamation-triangle", "route_path": "/superadmin/red-id-oversight", "display_order": 106},
    
    # ===================== FINANCE ADMIN PAGES (120-139) =====================
    {"menu_code": "finance_dashboard", "menu_name": "Finance Dashboard", "menu_category": "finance", "menu_icon": "fas fa-chart-pie", "route_path": "/finance/dashboard", "display_order": 120},
    {"menu_code": "finance_admin_pins", "menu_name": "PIN Approvals", "menu_category": "finance", "menu_icon": "fas fa-thumbtack", "route_path": "/finance/admin-pins", "display_order": 121},
    {"menu_code": "finance_awards_payment", "menu_name": "Awards Payment", "menu_category": "finance", "menu_icon": "fas fa-hand-holding-usd", "route_path": "/finance/awards-payment", "display_order": 122},
    {"menu_code": "finance_compliance", "menu_name": "Compliance", "menu_category": "finance", "menu_icon": "fas fa-gavel", "route_path": "/finance/compliance", "display_order": 123},
    {"menu_code": "finance_cost_analysis", "menu_name": "Cost Analysis", "menu_category": "finance", "menu_icon": "fas fa-calculator", "route_path": "/finance/cost-analysis", "display_order": 124},
    {"menu_code": "finance_tds_management", "menu_name": "TDS Management", "menu_category": "finance", "menu_icon": "fas fa-percent", "route_path": "/finance/tds-management", "display_order": 125},
    
    # ===================== STAFF PAGES (140-199) =====================
    {"menu_code": "staff_dashboard", "menu_name": "Staff Dashboard", "menu_category": "staff", "menu_icon": "fas fa-tachometer-alt", "route_path": "/staff/dashboard", "display_order": 140},
    {"menu_code": "staff_my_attendance", "menu_name": "My Attendance", "menu_category": "staff_attendance", "menu_icon": "fas fa-clock", "route_path": "/staff/my-attendance", "display_order": 141},
    {"menu_code": "staff_attendance_sheet", "menu_name": "Attendance Records", "menu_category": "staff_attendance", "menu_icon": "fas fa-calendar-check", "route_path": "/staff/attendance-sheet", "display_order": 142},
    {"menu_code": "staff_attendance_reports", "menu_name": "Attendance Dashboard", "menu_category": "staff_attendance", "menu_icon": "fas fa-file-alt", "route_path": "/staff/attendance-reports", "display_order": 143},
    {"menu_code": "staff_attendance_computation", "menu_name": "Attendance Computation", "menu_category": "staff_attendance", "menu_icon": "fas fa-calculator", "route_path": "/staff/attendance-computation", "display_order": 144},
    {"menu_code": "staff_team_attendance", "menu_name": "Team Attendance", "menu_category": "staff_attendance", "menu_icon": "fas fa-users-cog", "route_path": "/staff/team-attendance", "display_order": 145},
    {"menu_code": "staff_team_attendance_summary", "menu_name": "Team Attendance Summary", "menu_category": "staff_attendance", "menu_icon": "fas fa-chart-bar", "route_path": "/staff/team-attendance-summary", "display_order": 146},
    # Staff Tasks
    {"menu_code": "staff_task_tracker", "menu_name": "Task Dashboard", "menu_category": "staff_tasks", "menu_icon": "fas fa-tasks", "route_path": "/staff/tasks/tracker", "display_order": 150},
    {"menu_code": "staff_tasks_assigned_to_me", "menu_name": "Tasks Assigned to Me", "menu_category": "staff_tasks", "menu_icon": "fas fa-inbox", "route_path": "/staff/tasks/assigned-to-me", "display_order": 151},
    {"menu_code": "staff_tasks_assigned_by_me", "menu_name": "Tasks Assigned by Me", "menu_category": "staff_tasks", "menu_icon": "fas fa-paper-plane", "route_path": "/staff/tasks/assigned-by-me-v2", "display_order": 152},
    {"menu_code": "staff_task_review", "menu_name": "Task Review", "menu_category": "staff_tasks", "menu_icon": "fas fa-clipboard-check", "route_path": "/staff/task-review", "display_order": 153},
    {"menu_code": "staff_day_planner", "menu_name": "Task Planner", "menu_category": "staff_tasks", "menu_icon": "fas fa-calendar-day", "route_path": "/staff/tasks/day-planner", "display_order": 154},
    # Staff Journey & Location
    {"menu_code": "staff_my_journeys", "menu_name": "My Journeys", "menu_category": "staff_journey", "menu_icon": "fas fa-route", "route_path": "/staff/my-journeys", "display_order": 155},
    {"menu_code": "staff_all_journeys", "menu_name": "All Journeys", "menu_category": "staff_journey", "menu_icon": "fas fa-map", "route_path": "/staff/all-journeys", "display_order": 156},
    {"menu_code": "staff_team_journeys", "menu_name": "Team Journeys", "menu_category": "staff_journey", "menu_icon": "fas fa-users", "route_path": "/staff/team-journeys", "display_order": 157},
    {"menu_code": "staff_vgk4u_journeys", "menu_name": "VGK4U Journeys", "menu_category": "staff_journey", "menu_icon": "fas fa-car", "route_path": "/staff/vgk4u-journeys", "display_order": 158},
    {"menu_code": "staff_my_location_history", "menu_name": "My Location History", "menu_category": "staff_journey", "menu_icon": "fas fa-map-marker-alt", "route_path": "/staff/my-location-history", "display_order": 159},
    {"menu_code": "staff_team_location_tracker", "menu_name": "Team Location Tracker", "menu_category": "staff_journey", "menu_icon": "fas fa-map-marked", "route_path": "/staff/team-location-tracker", "display_order": 160},
    # Staff Timesheet & KRA
    {"menu_code": "staff_my_timesheet", "menu_name": "My Timesheet", "menu_category": "staff_timesheet", "menu_icon": "fas fa-calendar-alt", "route_path": "/staff/my-timesheet", "display_order": 165},
    {"menu_code": "staff_timesheet_approval", "menu_name": "Timesheet Approval", "menu_category": "staff_timesheet", "menu_icon": "fas fa-check-circle", "route_path": "/staff/timesheet-approval", "display_order": 166},
    {"menu_code": "staff_timesheet", "menu_name": "Time Sheet", "menu_category": "staff_timesheet", "menu_icon": "fas fa-clock", "route_path": "/staff/timesheet", "display_order": 163, "is_default_visible": True, "is_default_accessible": True},
    {"menu_code": "staff_kra_status", "menu_name": "KRA Status", "menu_category": "staff_kra", "menu_icon": "fas fa-chart-bar", "route_path": "/staff/kra-status", "display_order": 164, "is_default_visible": True, "is_default_accessible": True},
    {"menu_code": "staff_my_kras", "menu_name": "My KRAs", "menu_category": "staff_kra", "menu_icon": "fas fa-chart-line", "route_path": "/staff/my-kras", "display_order": 167},
    {"menu_code": "staff_kra_tracking_sheet", "menu_name": "KRA Tracking Sheet", "menu_category": "staff_kra", "menu_icon": "fas fa-table", "route_path": "/staff/kra-tracking-sheet", "display_order": 168},
    {"menu_code": "staff_kra_review", "menu_name": "KRA Review", "menu_category": "staff_kra", "menu_icon": "fas fa-clipboard-list", "route_path": "/staff/kra-review", "display_order": 169},
    {"menu_code": "staff_kra_templates", "menu_name": "KRA Templates", "menu_category": "staff_kra", "menu_icon": "fas fa-file-alt", "route_path": "/staff/kra-templates", "display_order": 170},
    # Staff Management
    {"menu_code": "staff_employees", "menu_name": "Employees", "menu_category": "staff_management", "menu_icon": "fas fa-users", "route_path": "/staff/employees", "display_order": 175},
    {"menu_code": "staff_employee_directory", "menu_name": "Employee Directory", "menu_category": "staff_management", "menu_icon": "fas fa-address-book", "route_path": "/staff/employee-directory", "display_order": 176},
    {"menu_code": "staff_departments", "menu_name": "Departments", "menu_category": "staff_management", "menu_icon": "fas fa-sitemap", "route_path": "/staff/departments", "display_order": 177},
    {"menu_code": "staff_manager_review", "menu_name": "Manager Review", "menu_category": "staff_management", "menu_icon": "fas fa-user-tie", "route_path": "/staff/manager-review", "display_order": 178},
    {"menu_code": "staff_team_activities", "menu_name": "Team Activities", "menu_category": "staff_management", "menu_icon": "fas fa-list-ul", "route_path": "/staff/team-activities", "display_order": 179},
    # Staff NDA
    {"menu_code": "staff_nda_versions", "menu_name": "NDA Versions", "menu_category": "staff_nda", "menu_icon": "fas fa-file-contract", "route_path": "/staff/nda-versions", "display_order": 180},
    {"menu_code": "staff_nda_editor", "menu_name": "NDA Editor", "menu_category": "staff_nda", "menu_icon": "fas fa-edit", "route_path": "/staff/nda-editor", "display_order": 181},
    {"menu_code": "staff_nda_pending", "menu_name": "NDA Pending", "menu_category": "staff_nda", "menu_icon": "fas fa-hourglass-half", "route_path": "/staff/nda-pending", "display_order": 182},
    {"menu_code": "staff_nda_acceptance_audit", "menu_name": "NDA Acceptance Audit", "menu_category": "staff_nda", "menu_icon": "fas fa-history", "route_path": "/staff/nda-acceptance-audit", "display_order": 183},
    # Staff Settings
    {"menu_code": "staff_settings", "menu_name": "Settings", "menu_category": "staff", "menu_icon": "fas fa-cog", "route_path": "/staff/settings", "display_order": 185},
    {"menu_code": "staff_change_password", "menu_name": "Change Password", "menu_category": "staff", "menu_icon": "fas fa-key", "route_path": "/staff/change-password", "display_order": 186},
    {"menu_code": "staff_2fa_settings", "menu_name": "2FA Settings", "menu_category": "staff", "menu_icon": "fas fa-lock", "route_path": "/staff/2fa-settings", "display_order": 187},
    {"menu_code": "staff_my_kyc", "menu_name": "My KYC", "menu_category": "staff", "menu_icon": "fas fa-id-badge", "route_path": "/staff/my-kyc", "display_order": 188},
    {"menu_code": "staff_kyc_approvals", "menu_name": "KYC Approvals", "menu_category": "staff", "menu_icon": "fas fa-user-check", "route_path": "/staff/kyc-approvals", "display_order": 189},
    {"menu_code": "staff_audit_logs", "menu_name": "Audit Logs", "menu_category": "staff", "menu_icon": "fas fa-history", "route_path": "/staff/audit-logs", "display_order": 190},
    
    # ===================== SFMS - ACCOUNTS PAGES (200-249) =====================
    # DC_ACCOUNTS_DEFAULT_ACCESS_001: Default access granted only to staff with accounts department
    # is_default_visible=False here — access is granted via bootstrap to accounts dept employees only
    # Future additions/removals controlled via Menu Access page
    {"menu_code": "sfms_companies", "menu_name": "Companies", "menu_category": "sfms", "menu_icon": "fas fa-building", "route_path": "/staff/accounts/companies", "display_order": 200},
    {"menu_code": "sfms_segments", "menu_name": "Segments", "menu_category": "sfms", "menu_icon": "fas fa-puzzle-piece", "route_path": "/staff/accounts/segments", "display_order": 201},
    {"menu_code": "sfms_income_entries", "menu_name": "Income Entries", "menu_category": "sfms", "menu_icon": "fas fa-arrow-up", "route_path": "/staff/accounts/income-entries", "display_order": 202},
    {"menu_code": "sfms_expense_entries", "menu_name": "Expense Entries", "menu_category": "sfms", "menu_icon": "fas fa-arrow-down", "route_path": "/staff/accounts/expense-entries", "display_order": 203},
    {"menu_code": "sfms_party_ledger", "menu_name": "Party Ledger", "menu_category": "sfms", "menu_icon": "fas fa-book", "route_path": "/staff/accounts/party-ledger", "display_order": 204},
    {"menu_code": "sfms_general_ledger", "menu_name": "General Ledger", "menu_category": "sfms", "menu_icon": "fas fa-book-open", "route_path": "/staff/accounts/general-ledger", "display_order": 205},
    {"menu_code": "sfms_journal_voucher", "menu_name": "Entries", "menu_category": "sfms", "menu_icon": "fas fa-file-alt", "route_path": "/staff/accounts/journal-voucher", "display_order": 207},
    {"menu_code": "sfms_receivables", "menu_name": "Receivables", "menu_category": "sfms", "menu_icon": "fas fa-hand-holding-usd", "route_path": "/staff/accounts/receivables", "display_order": 208},
    {"menu_code": "sfms_payables", "menu_name": "Payables", "menu_category": "sfms", "menu_icon": "fas fa-credit-card", "route_path": "/staff/accounts/payables", "display_order": 209},
    {"menu_code": "sfms_capital_account", "menu_name": "Capital Account", "menu_category": "sfms", "menu_icon": "fas fa-coins", "route_path": "/staff/accounts/capital", "display_order": 2094},
    {"menu_code": "sfms_duties_taxes", "menu_name": "Duties & Taxes", "menu_category": "sfms", "menu_icon": "fas fa-percent", "route_path": "/staff/accounts/duties-taxes", "display_order": 2095},
    {"menu_code": "sfms_fund_allocations", "menu_name": "Fund Allocations", "menu_category": "sfms", "menu_icon": "fas fa-piggy-bank", "route_path": "/staff/accounts/fund-allocations", "display_order": 210},
    {"menu_code": "sfms_balance_sheet", "menu_name": "Balance Sheet", "menu_category": "sfms", "menu_icon": "fas fa-balance-scale", "route_path": "/staff/accounts/balance-sheet", "display_order": 211},
    {"menu_code": "sfms_reports", "menu_name": "Financial Reports", "menu_category": "sfms", "menu_icon": "fas fa-chart-area", "route_path": "/staff/accounts/reports", "display_order": 212},
    # SFMS Inventory
    {"menu_code": "sfms_hsn", "menu_name": "HSN Master", "menu_category": "sfms_inventory", "menu_icon": "fas fa-barcode", "route_path": "/staff/accounts/hsn", "display_order": 215},
    {"menu_code": "sfms_vendors", "menu_name": "Vendors", "menu_category": "sfms_inventory", "menu_icon": "fas fa-truck", "route_path": "/staff/accounts/vendors", "display_order": 216, "is_default_visible": True, "is_default_accessible": True},
    {"menu_code": "sfms_stock_items", "menu_name": "Stock Items", "menu_category": "sfms_inventory", "menu_icon": "fas fa-boxes", "route_path": "/staff/accounts/stock-items", "display_order": 217},
    {"menu_code": "sfms_pricing", "menu_name": "Pricing", "menu_category": "sfms_inventory", "menu_icon": "fas fa-tags", "route_path": "/staff/accounts/pricing", "display_order": 218},
    {"menu_code": "sfms_purchase_invoices", "menu_name": "Purchase Invoices", "menu_category": "sfms_inventory", "menu_icon": "fas fa-file-invoice-dollar", "route_path": "/staff/accounts/purchase-invoices", "display_order": 220},
    {"menu_code": "sfms_sales_invoices", "menu_name": "Sales Invoices", "menu_category": "sfms_inventory", "menu_icon": "fas fa-file-invoice", "route_path": "/staff/accounts/sales-invoices", "display_order": 220},
    {"menu_code": "sfms_stock_ledger", "menu_name": "Stock Ledger", "menu_category": "inventory", "menu_icon": "fas fa-clipboard-list", "route_path": "/staff/inventory/stock-ledger", "display_order": 221},
    {"menu_code": "sfms_stock_transfers", "menu_name": "Stock Transfers", "menu_category": "inventory", "menu_icon": "fas fa-exchange-alt", "route_path": "/staff/inventory/stock-transfers", "display_order": 222},
    # SFMS Manufacturing
    {"menu_code": "sfms_bom", "menu_name": "Bill of Materials", "menu_category": "sfms_manufacturing", "menu_icon": "fas fa-sitemap", "route_path": "/staff/accounts/bom", "display_order": 225},
    {"menu_code": "sfms_manufacturing", "menu_name": "Manufacturing", "menu_category": "sfms_manufacturing", "menu_icon": "fas fa-industry", "route_path": "/staff/accounts/manufacturing", "display_order": 226},
    {"menu_code": "sfms_procurement", "menu_name": "Procurement Planning", "menu_category": "sfms_manufacturing", "menu_icon": "fas fa-shopping-basket", "route_path": "/staff/accounts/procurement", "display_order": 227},
    # SFMS Reimbursements
    {"menu_code": "sfms_my_reimbursements", "menu_name": "My Reimbursement Claims", "menu_category": "sfms_reimbursements", "menu_icon": "fas fa-receipt", "route_path": "/staff/accounts/my-reimbursements", "display_order": 230},
    {"menu_code": "sfms_reimbursement_approvals", "menu_name": "Reimbursement Approvals", "menu_category": "sfms_reimbursements", "menu_icon": "fas fa-check-double", "route_path": "/staff/accounts/reimbursement-approvals", "display_order": 231},
    
    # ===================== PARTNER STAFF PAGES (250-269) =====================
    # These are staff pages for managing partners (audience_scope: staff)
    {"menu_code": "partner_orders", "menu_name": "Partner Orders", "menu_category": "partners", "menu_icon": "fas fa-shopping-cart", "route_path": "/partner/orders", "display_order": 250, "audience_scope": "staff"},
    {"menu_code": "partner_master", "menu_name": "Partner Master", "menu_category": "partners", "menu_icon": "fas fa-id-card", "route_path": "/partner/master", "display_order": 251, "audience_scope": "staff"},
    {"menu_code": "partner_order_approval", "menu_name": "Order Approval", "menu_category": "partners", "menu_icon": "fas fa-check-circle", "route_path": "/partner/order-approval", "display_order": 252, "audience_scope": "staff"},
    {"menu_code": "partner_order_routing", "menu_name": "Order Routing", "menu_category": "partners", "menu_icon": "fas fa-route", "route_path": "/partner/order-routing", "display_order": 253, "audience_scope": "staff"},
    {"menu_code": "partner_dispatch", "menu_name": "Partner Dispatch", "menu_category": "partners", "menu_icon": "fas fa-shipping-fast", "route_path": "/partner/dispatch", "display_order": 254, "audience_scope": "staff"},
    {"menu_code": "partner_invoices", "menu_name": "Partner Invoices", "menu_category": "partners", "menu_icon": "fas fa-file-invoice", "route_path": "/partner/invoices", "display_order": 255, "audience_scope": "staff"},
    {"menu_code": "partner_payments", "menu_name": "Partner Payments", "menu_category": "partners", "menu_icon": "fas fa-money-check", "route_path": "/partner/payments", "display_order": 256, "audience_scope": "staff"},
    {"menu_code": "partner_pricing", "menu_name": "Partner Pricing", "menu_category": "partners", "menu_icon": "fas fa-tags", "route_path": "/partner/pricing", "display_order": 257, "audience_scope": "staff"},
    {"menu_code": "order_fulfillment_dashboard", "menu_name": "Order Fulfillment", "menu_category": "partners", "menu_icon": "fas fa-clipboard-check", "route_path": "/order-fulfillment-dashboard", "display_order": 258, "audience_scope": "staff"},
    {"menu_code": "partner_walkins", "menu_name": "Partner Walk-ins", "menu_category": "partners", "menu_icon": "fas fa-walking", "route_path": "/staff/partners/walkins", "display_order": 259, "audience_scope": "staff"},

    # ===================== PARTNER PORTAL PAGES (320-339) =====================
    # These are pages FOR partners to access (audience_scope: partner)
    {"menu_code": "partner_portal_dashboard", "menu_name": "Partner Dashboard", "menu_category": "partner_portal", "menu_icon": "fas fa-tachometer-alt", "route_path": "/partner-portal/dashboard", "display_order": 320, "audience_scope": "partner"},
    {"menu_code": "partner_portal_orders", "menu_name": "My Orders", "menu_category": "partner_portal", "menu_icon": "fas fa-shopping-cart", "route_path": "/partner-portal/orders", "display_order": 321, "audience_scope": "partner"},
    {"menu_code": "partner_portal_invoices", "menu_name": "My Invoices", "menu_category": "partner_portal", "menu_icon": "fas fa-file-invoice", "route_path": "/partner-portal/invoices", "display_order": 322, "audience_scope": "partner"},
    {"menu_code": "partner_portal_payments", "menu_name": "My Payments", "menu_category": "partner_portal", "menu_icon": "fas fa-money-check", "route_path": "/partner-portal/payments", "display_order": 323, "audience_scope": "partner"},
    {"menu_code": "partner_portal_products", "menu_name": "Product Catalog", "menu_category": "partner_portal", "menu_icon": "fas fa-boxes", "route_path": "/partner-portal/products", "display_order": 324, "audience_scope": "partner"},
    {"menu_code": "partner_portal_profile", "menu_name": "My Profile", "menu_category": "partner_portal", "menu_icon": "fas fa-user-circle", "route_path": "/partner-portal/profile", "display_order": 325, "audience_scope": "partner"},
    {"menu_code": "partner_portal_reports", "menu_name": "Reports", "menu_category": "partner_portal", "menu_icon": "fas fa-chart-bar", "route_path": "/partner-portal/reports", "display_order": 326, "audience_scope": "partner"},
    {"menu_code": "partner_portal_support", "menu_name": "Support", "menu_category": "partner_portal", "menu_icon": "fas fa-headset", "route_path": "/partner-portal/support", "display_order": 327, "audience_scope": "partner"},
    # Real Dreams Partner Pages
    {"menu_code": "partner_rd_dashboard", "menu_name": "Real Dreams Dashboard", "menu_category": "partner_real_dreams", "menu_icon": "fas fa-home", "route_path": "/partner/real-dreams/dashboard", "display_order": 330, "audience_scope": "partner"},
    {"menu_code": "partner_rd_properties", "menu_name": "My Properties", "menu_category": "partner_real_dreams", "menu_icon": "fas fa-building", "route_path": "/partner/real-dreams/properties", "display_order": 331, "audience_scope": "partner"},
    {"menu_code": "partner_rd_leads", "menu_name": "My Leads", "menu_category": "partner_real_dreams", "menu_icon": "fas fa-funnel-dollar", "route_path": "/partner/real-dreams/leads", "display_order": 332, "audience_scope": "partner"},
    {"menu_code": "partner_rd_commissions", "menu_name": "Commissions", "menu_category": "partner_real_dreams", "menu_icon": "fas fa-money-bill-wave", "route_path": "/partner/real-dreams/commissions", "display_order": 333, "audience_scope": "partner"},
    
    # ===================== REAL DREAMS PUBLIC (270-279) =====================
    {"menu_code": "real_dreams_marketplace", "menu_name": "Property Marketplace", "menu_category": "real_dreams", "menu_icon": "fas fa-store", "route_path": "/real-dreams/marketplace", "display_order": 270},
    {"menu_code": "real_dreams_property_detail", "menu_name": "Property Details", "menu_category": "real_dreams", "menu_icon": "fas fa-home", "route_path": "/real-dreams/property", "display_order": 271},
    {"menu_code": "real_dreams_compare", "menu_name": "Property Comparison", "menu_category": "real_dreams", "menu_icon": "fas fa-balance-scale", "route_path": "/real-dreams/compare", "display_order": 272},
    
    # ===================== CRM PAGES (280-289) =====================
    # DC Protocol (Jan 01, 2026): Updated CRM menu structure for staff portal
    {"menu_code": "crm_whatsapp_inbox", "menu_name": "WA Inbox (CRM)", "menu_category": "crm", "menu_icon": "fab fa-whatsapp", "route_path": "/staff/crm/whatsapp-inbox", "display_order": 279, "is_default_visible": True, "is_default_accessible": True, "audience_scope": "staff", "sidebar_section": "crm", "sidebar_section_title": "CRM & LEADS", "sidebar_section_order": 4},
    {"menu_code": "staff_crm_dashboard", "menu_name": "My CRM Dashboard", "menu_category": "crm", "menu_icon": "fas fa-chart-line", "route_path": "/staff/crm/dashboard", "display_order": 280},
    {"menu_code": "staff_leads", "menu_name": "Staff Leads", "menu_category": "crm", "menu_icon": "fas fa-briefcase", "route_path": "/staff/leads", "display_order": 281},
    {"menu_code": "staff_team_leads", "menu_name": "Team Leads", "menu_category": "crm", "menu_icon": "fas fa-users", "route_path": "/staff/crm/team-leads", "display_order": 282},
    {"menu_code": "staff_my_leads", "menu_name": "My Leads", "menu_category": "crm", "menu_icon": "fas fa-user-friends", "route_path": "/staff/my-leads", "display_order": 283},
    {"menu_code": "staff_lead_sources", "menu_name": "Lead Sources", "menu_category": "crm", "menu_icon": "fas fa-tags", "route_path": "/staff/crm/lead-sources", "display_order": 284},
    {"menu_code": "call_tracking_dashboard", "menu_name": "Call Tracking", "menu_category": "crm", "menu_icon": "fas fa-phone-alt", "route_path": "/staff/call-management", "display_order": 285},
    {"menu_code": "staff_auto_dialer", "menu_name": "Auto Dialer", "menu_category": "crm", "menu_icon": "fas fa-phone-volume", "route_path": "/staff/dialer", "display_order": 286, "is_default_visible": True, "is_default_accessible": True},
    {"menu_code": "call_quality_review", "menu_name": "Call Quality Review", "menu_category": "crm", "menu_icon": "fas fa-clipboard-check", "route_path": "/staff/call-quality", "display_order": 287},
    {"menu_code": "sales_team_report", "menu_name": "Sales Team Report", "menu_category": "crm", "menu_icon": "fas fa-chart-bar", "route_path": "/staff/crm/sales-report", "display_order": 288},

    # ===================== USER PAGES (290-309) =====================
    {"menu_code": "user_announcements", "menu_name": "Announcements", "menu_category": "user", "menu_icon": "fas fa-bullhorn", "route_path": "/user/announcements", "display_order": 290},
    {"menu_code": "user_daywise_income", "menu_name": "Daywise Income", "menu_category": "user", "menu_icon": "fas fa-calendar-day", "route_path": "/user/daywise-income", "display_order": 291},
    {"menu_code": "user_direct_referral", "menu_name": "Direct Referral", "menu_category": "user", "menu_icon": "fas fa-users", "route_path": "/user/direct-referral", "display_order": 292},
    {"menu_code": "user_matching_referral", "menu_name": "Matching Referral", "menu_category": "user", "menu_icon": "fas fa-arrows-alt-h", "route_path": "/user/matching-referral", "display_order": 293},
    {"menu_code": "user_guru_dakshina", "menu_name": "Guru Dakshina", "menu_category": "user", "menu_icon": "fas fa-praying-hands", "route_path": "/user/guru-dakshina", "display_order": 294},
    {"menu_code": "user_ev_benefits", "menu_name": "EV Benefits", "menu_category": "user", "menu_icon": "fas fa-car", "route_path": "/user/ev-benefits", "display_order": 295},
    {"menu_code": "user_ev_discount", "menu_name": "EV Discount", "menu_category": "user", "menu_icon": "fas fa-percent", "route_path": "/user/ev-discount", "display_order": 296},
    {"menu_code": "user_feedback_submit", "menu_name": "Submit Feedback", "menu_category": "user", "menu_icon": "fas fa-comment", "route_path": "/user/feedback-submit", "display_order": 297},
    {"menu_code": "user_change_password", "menu_name": "Change Password", "menu_category": "user", "menu_icon": "fas fa-key", "route_path": "/user/change-password", "display_order": 298},
    
    # ===================== VGK ADMIN PAGES (310-319) =====================
    {"menu_code": "admin_vgk_all_benefits", "menu_name": "VGK All Benefits", "menu_category": "vgk", "menu_icon": "fas fa-gift", "route_path": "/admin/vgk/all-benefits", "display_order": 310},
    {"menu_code": "admin_vgk_ev_discount_training", "menu_name": "VGK EV & Training", "menu_category": "vgk", "menu_icon": "fas fa-graduation-cap", "route_path": "/admin/vgk/ev-discount-training", "display_order": 311},
    {"menu_code": "admin_vgk_fleet_orders", "menu_name": "VGK Fleet Orders", "menu_category": "vgk", "menu_icon": "fas fa-truck-loading", "route_path": "/admin/vgk/fleet-orders", "display_order": 312},
    {"menu_code": "admin_vgk_franchise_earnings", "menu_name": "VGK Franchise Earnings", "menu_category": "vgk", "menu_icon": "fas fa-store-alt", "route_path": "/admin/vgk/franchise-earnings", "display_order": 313},
    {"menu_code": "admin_vgk_insurance_earnings", "menu_name": "VGK Insurance Earnings", "menu_category": "vgk", "menu_icon": "fas fa-shield-alt", "route_path": "/admin/vgk/insurance-earnings", "display_order": 314},
    {"menu_code": "admin_vgk_referral_income", "menu_name": "VGK Referral Income", "menu_category": "vgk", "menu_icon": "fas fa-hand-holding-usd", "route_path": "/admin/vgk/referral-income", "display_order": 315},

    # ===================== STAFF MNR PAGES (400-471) - DC Protocol Dec 28, 2025 =====================
    # NEW MNR - DC Protocol Dec 29, 2025 (Dashboard moved here, MNR DASHBOARD menu removed)
    # Note: menu_code preserved for backward compatibility with existing StaffEmployeeMenuSettings
    {"menu_code": "staff_mnr_dashboard", "menu_name": "RVZ Dashboard", "menu_category": "staff_new_mnr", "menu_icon": "fas fa-tachometer-alt", "route_path": "/staff/mnr/dashboard", "display_order": 397},
    {"menu_code": "staff_new_mnr_users", "menu_name": "All Users", "menu_category": "staff_new_mnr", "menu_icon": "fas fa-users", "route_path": "/staff/mnr/users", "display_order": 398},
    # User Management
    {"menu_code": "staff_mnr_user_data_search", "menu_name": "User Data Search", "menu_category": "staff_mnr_user_mgmt", "menu_icon": "fas fa-search", "route_path": "/staff/mnr/user-data-search", "display_order": 402, "sidebar_section": "mnr-user-sidebar", "sidebar_section_title": "MNR USER SIDEBAR", "sidebar_section_order": 11},
    {"menu_code": "staff_mnr_user_activation", "menu_name": "User Activation Control", "menu_category": "staff_mnr_user_mgmt", "menu_icon": "fas fa-user-check", "route_path": "/staff/mnr/user-activation-control", "display_order": 403, "sidebar_section": "mnr-user-sidebar", "sidebar_section_title": "MNR USER SIDEBAR", "sidebar_section_order": 11},
    {"menu_code": "staff_mnr_bulk_edit", "menu_name": "Bulk User Edit", "menu_category": "staff_mnr_user_mgmt", "menu_icon": "fas fa-edit", "route_path": "/staff/mnr/bulk-user-edit", "display_order": 404},
    {"menu_code": "staff_mnr_user_update_controls", "menu_name": "User Update Controls", "menu_category": "staff_mnr_user_mgmt", "menu_icon": "fas fa-user-cog", "route_path": "/staff/mnr/user-update-controls", "display_order": 405, "sidebar_section": "mnr-user-sidebar", "sidebar_section_title": "MNR USER SIDEBAR", "sidebar_section_order": 11},
    {"menu_code": "staff_mnr_reactivate", "menu_name": "Reactivate/Reassign", "menu_category": "staff_mnr_user_mgmt", "menu_icon": "fas fa-sync-alt", "route_path": "/staff/mnr/reactivate-reassign", "display_order": 406},
    {"menu_code": "staff_mnr_update_approvals", "menu_name": "User Update Approvals", "menu_category": "staff_mnr_user_mgmt", "menu_icon": "fas fa-user-clock", "route_path": "/staff/mnr/user-update-approvals", "display_order": 407},
    {"menu_code": "staff_mnr_birthdays", "menu_name": "Birthday Details", "menu_category": "staff_mnr_user_mgmt", "menu_icon": "fas fa-birthday-cake", "route_path": "/staff/mnr/birthdays", "display_order": 408},
    {"menu_code": "staff_mnr_field_allowances", "menu_name": "Allowances", "menu_category": "staff_mnr_user_mgmt", "menu_icon": "fas fa-car", "route_path": "/staff/mnr/field-allowances", "display_order": 409},
    # Withdrawals
    {"menu_code": "staff_mnr_withdrawal_dashboard", "menu_name": "Withdrawal Dashboard", "menu_category": "staff_mnr_withdrawals", "menu_icon": "fas fa-chart-line", "route_path": "/staff/mnr/withdrawal/dashboard", "display_order": 410},
    {"menu_code": "staff_mnr_withdrawal_approvals", "menu_name": "Withdrawal Approvals", "menu_category": "staff_mnr_withdrawals", "menu_icon": "fas fa-money-check-alt", "route_path": "/staff/mnr/withdrawal/approvals", "display_order": 411},
    {"menu_code": "staff_mnr_withdrawal_history", "menu_name": "Withdrawal History", "menu_category": "staff_mnr_withdrawals", "menu_icon": "fas fa-history", "route_path": "/staff/mnr/withdrawal/history", "display_order": 412},
    {"menu_code": "staff_mnr_withdrawal_supreme", "menu_name": "Withdrawal Supreme", "menu_category": "staff_mnr_withdrawals", "menu_icon": "fas fa-crown", "route_path": "/staff/mnr/withdrawal-supreme", "display_order": 413},
    # KYC & Bank
    {"menu_code": "staff_mnr_kyc", "menu_name": "KYC Management", "menu_category": "staff_mnr_kyc_bank", "menu_icon": "fas fa-id-card", "route_path": "/staff/mnr/kyc-management", "display_order": 420},
    {"menu_code": "staff_mnr_bank_pending", "menu_name": "Bank Pending", "menu_category": "staff_mnr_kyc_bank", "menu_icon": "fas fa-university", "route_path": "/staff/mnr/bank-pending", "display_order": 421},
    {"menu_code": "staff_mnr_bank_all", "menu_name": "All Bank Details", "menu_category": "staff_mnr_kyc_bank", "menu_icon": "fas fa-landmark", "route_path": "/staff/mnr/bank-all", "display_order": 422},
    # Income & Finance
    {"menu_code": "staff_mnr_income_supreme", "menu_name": "Supreme Income Monitor", "menu_category": "staff_mnr_income", "menu_icon": "fas fa-crown", "route_path": "/staff/mnr/income-supreme", "display_order": 430},
    {"menu_code": "staff_mnr_income_records", "menu_name": "Income Records", "menu_category": "staff_mnr_income", "menu_icon": "fas fa-clipboard-list", "route_path": "/staff/mnr/income-records", "display_order": 431},
    {"menu_code": "staff_mnr_finance_complete", "menu_name": "Finance Completion", "menu_category": "staff_mnr_income", "menu_icon": "fas fa-check-double", "route_path": "/staff/mnr/income-finance-complete", "display_order": 432},
    {"menu_code": "staff_mnr_finance_supreme", "menu_name": "Finance Supreme", "menu_category": "staff_mnr_income", "menu_icon": "fas fa-university", "route_path": "/staff/mnr/finance-supreme", "display_order": 433},
    {"menu_code": "staff_mnr_income_unified", "menu_name": "Income Management", "menu_category": "staff_mnr_income", "menu_icon": "fas fa-chart-line", "route_path": "/staff/mnr/income-unified", "display_order": 434},
    # Awards & Bonanza
    {"menu_code": "staff_mnr_awards_all", "menu_name": "All Awards", "menu_category": "staff_mnr_awards", "menu_icon": "fas fa-trophy", "route_path": "/staff/mnr/awards-all", "display_order": 440},
    {"menu_code": "staff_mnr_awards_approval", "menu_name": "Awards Approval Queue", "menu_category": "staff_mnr_awards", "menu_icon": "fas fa-check-circle", "route_path": "/staff/mnr/awards-approval-queue", "display_order": 441},
    {"menu_code": "staff_mnr_procurement", "menu_name": "Procurement Queue", "menu_category": "staff_mnr_awards", "menu_icon": "fas fa-shopping-cart", "route_path": "/staff/mnr/procurement-queue", "display_order": 442},
    {"menu_code": "staff_mnr_gift_status", "menu_name": "Gift-Wise Status", "menu_category": "staff_mnr_awards", "menu_icon": "fas fa-gift", "route_path": "/staff/mnr/gift-wise-status", "display_order": 443},
    {"menu_code": "staff_mnr_award_config", "menu_name": "Awards Configuration", "menu_category": "staff_mnr_awards", "menu_icon": "fas fa-cog", "route_path": "/staff/mnr/award-management", "display_order": 444},
    {"menu_code": "staff_mnr_bonanza", "menu_name": "Bonanza Management", "menu_category": "staff_mnr_awards", "menu_icon": "fas fa-gift", "route_path": "/staff/mnr/bonanza-management", "display_order": 445},
    {"menu_code": "staff_mnr_bonanza_claims", "menu_name": "Bonanza Claims", "menu_category": "staff_mnr_awards", "menu_icon": "fas fa-bullseye", "route_path": "/staff/mnr/bonanza-claims", "display_order": 446},
    {"menu_code": "staff_mnr_awards_management", "menu_name": "Awards Management", "menu_category": "staff_mnr_awards", "menu_icon": "fas fa-trophy", "route_path": "/staff/mnr/awards-management", "display_order": 447},
    # Compliance
    {"menu_code": "staff_mnr_compliance", "menu_name": "Compliance Dashboard", "menu_category": "staff_mnr_compliance", "menu_icon": "fas fa-chart-pie", "route_path": "/staff/mnr/compliance", "display_order": 450},
    {"menu_code": "staff_mnr_company_earnings", "menu_name": "Company Earnings", "menu_category": "staff_mnr_compliance", "menu_icon": "fas fa-coins", "route_path": "/staff/mnr/company-earnings", "display_order": 451},
    {"menu_code": "staff_mnr_revenue", "menu_name": "Revenue Details", "menu_category": "staff_mnr_compliance", "menu_icon": "fas fa-dollar-sign", "route_path": "/staff/mnr/revenue-details", "display_order": 452},
    {"menu_code": "staff_mnr_payout", "menu_name": "Payout Details", "menu_category": "staff_mnr_compliance", "menu_icon": "fas fa-hand-holding-usd", "route_path": "/staff/mnr/payout-details", "display_order": 453},
    {"menu_code": "staff_mnr_expense", "menu_name": "Expense Details", "menu_category": "staff_mnr_compliance", "menu_icon": "fas fa-receipt", "route_path": "/staff/mnr/expense-details", "display_order": 454},
    {"menu_code": "staff_mnr_expense_mgmt", "menu_name": "Expenses Management", "menu_category": "staff_mnr_compliance", "menu_icon": "fas fa-file-invoice-dollar", "route_path": "/staff/mnr/expenses-management", "display_order": 455},
    {"menu_code": "staff_mnr_expense_categories", "menu_name": "Expense Categories", "menu_category": "staff_mnr_compliance", "menu_icon": "fas fa-tags", "route_path": "/staff/mnr/expense-categories", "display_order": 456},
    {"menu_code": "staff_mnr_expense_overview", "menu_name": "Expense Overview", "menu_category": "staff_mnr_compliance", "menu_icon": "fas fa-chart-area", "route_path": "/staff/mnr/expense-overview", "display_order": 457},
    # Announcements
    {"menu_code": "staff_mnr_announcements", "menu_name": "Announcements", "menu_category": "staff_mnr_announcements", "menu_icon": "fas fa-bullhorn", "route_path": "/staff/mnr/announcements/view", "display_order": 460},
    {"menu_code": "staff_mnr_feedback", "menu_name": "Pending Announcements", "menu_category": "staff_mnr_announcements", "menu_icon": "fas fa-comment-dots", "route_path": "/staff/mnr/feedback/pending", "display_order": 461},
    {"menu_code": "staff_mnr_banners", "menu_name": "Banners Management", "menu_category": "staff_mnr_announcements", "menu_icon": "fas fa-images", "route_path": "/staff/mnr/banners-management", "display_order": 462},
    {"menu_code": "staff_mnr_popups", "menu_name": "Popup Control", "menu_category": "staff_mnr_announcements", "menu_icon": "fas fa-window-restore", "route_path": "/staff/mnr/popups", "display_order": 464},
    # System Configuration
    {"menu_code": "staff_mnr_system_controls", "menu_name": "System Controls", "menu_category": "staff_mnr_system", "menu_icon": "fas fa-cogs", "route_path": "/staff/mnr/system-controls", "display_order": 470},
    {"menu_code": "staff_mnr_menu_config", "menu_name": "Menu Configuration", "menu_category": "staff_mnr_system", "menu_icon": "fas fa-bars", "route_path": "/staff/mnr/menu-configuration", "display_order": 471},
    {"menu_code": "staff_mnr_terms_versions", "menu_name": "T&C Versions", "menu_category": "staff_mnr_system", "menu_icon": "fas fa-file-contract", "route_path": "/staff/mnr/terms-versions", "display_order": 472},
    {"menu_code": "staff_mnr_terms_editor", "menu_name": "T&C Editor", "menu_category": "staff_mnr_system", "menu_icon": "fas fa-edit", "route_path": "/staff/mnr/terms-editor", "display_order": 473},
    {"menu_code": "staff_mnr_terms_audit", "menu_name": "T&C Audit", "menu_category": "staff_mnr_system", "menu_icon": "fas fa-history", "route_path": "/staff/mnr/terms-audit", "display_order": 474},

    # ===================== MYNT REAL LEAD PAGES (480-488) - DC Protocol Mar 2026 =====================
    {"menu_code": "mnr_executive_dashboard", "menu_name": "Executive Dashboard", "menu_category": "mynt_real", "menu_icon": "fas fa-chart-line", "route_path": "/staff/executive-dashboard", "display_order": 480, "sidebar_section": "mynt_real", "sidebar_section_title": "MYNT REAL", "sidebar_section_order": 23},
    {"menu_code": "mnr_category_leads", "menu_name": "Category Lead Master", "menu_category": "mynt_real", "menu_icon": "fas fa-layer-group", "route_path": "/staff/mnr-leads", "display_order": 481, "sidebar_section": "mynt_real", "sidebar_section_title": "MYNT REAL", "sidebar_section_order": 23},
    {"menu_code": "mnr_solar_leads", "menu_name": "Solar Leads", "menu_category": "mynt_real", "menu_icon": "fas fa-solar-panel", "route_path": "/staff/solar-leads", "display_order": 482, "sidebar_section": "mynt_real", "sidebar_section_title": "MYNT REAL", "sidebar_section_order": 23},
    {"menu_code": "mnr_ev_b2b_leads", "menu_name": "EV B2B Leads", "menu_category": "mynt_real", "menu_icon": "fas fa-truck", "route_path": "/staff/ev-b2b-leads", "display_order": 483, "sidebar_section": "mynt_real", "sidebar_section_title": "MYNT REAL", "sidebar_section_order": 23},
    {"menu_code": "mnr_ev_b2c_leads", "menu_name": "EV B2C Leads", "menu_category": "mynt_real", "menu_icon": "fas fa-car", "route_path": "/staff/ev-b2c-leads", "display_order": 484, "sidebar_section": "mynt_real", "sidebar_section_title": "MYNT REAL", "sidebar_section_order": 23},
    {"menu_code": "mnr_ev_spares_leads", "menu_name": "EV Spares Leads", "menu_category": "mynt_real", "menu_icon": "fas fa-cogs", "route_path": "/staff/ev-spares-leads", "display_order": 485, "sidebar_section": "mynt_real", "sidebar_section_title": "MYNT REAL", "sidebar_section_order": 23},
    {"menu_code": "mnr_real_dreams_leads", "menu_name": "Real Dreams Leads", "menu_category": "mynt_real", "menu_icon": "fas fa-home", "route_path": "/staff/real-dreams-leads", "display_order": 486, "sidebar_section": "mynt_real", "sidebar_section_title": "MYNT REAL", "sidebar_section_order": 23},
    {"menu_code": "mnr_insurance_leads", "menu_name": "Insurance Leads", "menu_category": "mynt_real", "menu_icon": "fas fa-shield-alt", "route_path": "/staff/insurance-leads", "display_order": 487, "sidebar_section": "mynt_real", "sidebar_section_title": "MYNT REAL", "sidebar_section_order": 23},
    {"menu_code": "mnr_etc_leads", "menu_name": "ETC Training Students", "menu_category": "mynt_real", "menu_icon": "fas fa-graduation-cap", "route_path": "/staff/etc-leads", "display_order": 488, "sidebar_section": "mynt_real", "sidebar_section_title": "MYNT REAL", "sidebar_section_order": 23},

    # ===================== MNR USER SIDEBAR (500-599) - Staff View of Member Data =====================
    # Dashboard & Profile
    {"menu_code": "staff_mnr_user_dashboard", "menu_name": "Member Dashboard", "menu_category": "staff_mnr_user_dashboard", "menu_icon": "fas fa-tachometer-alt", "route_path": "/staff/mnr-user/dashboard", "display_order": 500, "sidebar_section": "mnr-user-sidebar", "sidebar_section_title": "MNR USER SIDEBAR", "sidebar_section_order": 11},
    {"menu_code": "staff_mnr_user_profile", "menu_name": "Member Profile", "menu_category": "staff_mnr_user_dashboard", "menu_icon": "fas fa-user", "route_path": "/staff/mnr-user/profile", "display_order": 501, "sidebar_section": "mnr-user-sidebar", "sidebar_section_title": "MNR USER SIDEBAR", "sidebar_section_order": 11},
    {"menu_code": "staff_mnr_user_create", "menu_name": "Create Member", "menu_category": "staff_mnr_user_dashboard", "menu_icon": "fas fa-user-plus", "route_path": "/staff/mnr-user/create-member", "display_order": 502, "sidebar_section": "mnr-user-sidebar", "sidebar_section_title": "MNR USER SIDEBAR", "sidebar_section_order": 11},
    # Announcements Submenu
    {"menu_code": "staff_mnr_user_announcements", "menu_name": "Announcements", "menu_category": "staff_mnr_user_announcements", "menu_icon": "fas fa-bullhorn", "route_path": "/staff/mnr-user/announcements", "display_order": 510, "sidebar_section": "mnr-user-sidebar", "sidebar_section_title": "MNR USER SIDEBAR", "sidebar_section_order": 11},
    {"menu_code": "staff_mnr_user_announcements_create", "menu_name": "Create Announcement", "menu_category": "staff_mnr_user_announcements", "menu_icon": "fas fa-plus-circle", "route_path": "/staff/mnr-user/announcements/create", "display_order": 511, "sidebar_section": "mnr-user-sidebar", "sidebar_section_title": "MNR USER SIDEBAR", "sidebar_section_order": 11},
    {"menu_code": "staff_mnr_user_announcements_pending", "menu_name": "Pending Approvals", "menu_category": "staff_mnr_user_announcements", "menu_icon": "fas fa-clock", "route_path": "/staff/mnr-user/announcements/pending", "display_order": 512, "sidebar_section": "mnr-user-sidebar", "sidebar_section_title": "MNR USER SIDEBAR", "sidebar_section_order": 11},
    {"menu_code": "staff_mnr_user_announcements_history", "menu_name": "History", "menu_category": "staff_mnr_user_announcements", "menu_icon": "fas fa-history", "route_path": "/staff/mnr-user/announcements/history", "display_order": 513, "sidebar_section": "mnr-user-sidebar", "sidebar_section_title": "MNR USER SIDEBAR", "sidebar_section_order": 11},
    {"menu_code": "staff_mnr_user_popups", "menu_name": "Popups & Banners", "menu_category": "staff_mnr_user_announcements", "menu_icon": "fas fa-window-restore", "route_path": "/staff/mnr-user/popups", "display_order": 514, "sidebar_section": "mnr-user-sidebar", "sidebar_section_title": "MNR USER SIDEBAR", "sidebar_section_order": 11},
    # Coupon Modules Submenu
    {"menu_code": "staff_mnr_user_coupons_red", "menu_name": "Red Coupons", "menu_category": "staff_mnr_user_coupons", "menu_icon": "fas fa-ticket-alt", "route_path": "/staff/mnr-user/coupons/red", "display_order": 520, "sidebar_section": "mnr-user-sidebar", "sidebar_section_title": "MNR USER SIDEBAR", "sidebar_section_order": 11},
    {"menu_code": "staff_mnr_user_coupons_green", "menu_name": "Green Coupons", "menu_category": "staff_mnr_user_coupons", "menu_icon": "fas fa-ticket-alt", "route_path": "/staff/mnr-user/coupons/green", "display_order": 521, "sidebar_section": "mnr-user-sidebar", "sidebar_section_title": "MNR USER SIDEBAR", "sidebar_section_order": 11},
    {"menu_code": "staff_mnr_user_coupons_transfer", "menu_name": "Transfer Coupons", "menu_category": "staff_mnr_user_coupons", "menu_icon": "fas fa-exchange-alt", "route_path": "/staff/mnr-user/coupons/transfer", "display_order": 522, "sidebar_section": "mnr-user-sidebar", "sidebar_section_title": "MNR USER SIDEBAR", "sidebar_section_order": 11},
    {"menu_code": "staff_mnr_user_coupons_ev", "menu_name": "EV Discount Coupons", "menu_category": "staff_mnr_user_coupons", "menu_icon": "fas fa-bolt", "route_path": "/staff/mnr-user/coupons/ev", "display_order": 523, "sidebar_section": "mnr-user-sidebar", "sidebar_section_title": "MNR USER SIDEBAR", "sidebar_section_order": 11},
    {"menu_code": "staff_mnr_user_coupons_history", "menu_name": "Coupon History", "menu_category": "staff_mnr_user_coupons", "menu_icon": "fas fa-history", "route_path": "/staff/mnr-user/coupons/history", "display_order": 524, "sidebar_section": "mnr-user-sidebar", "sidebar_section_title": "MNR USER SIDEBAR", "sidebar_section_order": 11},
    # Members Submenu
    {"menu_code": "staff_mnr_user_members_all", "menu_name": "All Members", "menu_category": "staff_mnr_user_members", "menu_icon": "fas fa-users", "route_path": "/staff/mnr-user/members/all", "display_order": 530, "sidebar_section": "mnr-user-sidebar", "sidebar_section_title": "MNR USER SIDEBAR", "sidebar_section_order": 11},
    {"menu_code": "staff_mnr_user_members_direct", "menu_name": "Direct Referrals", "menu_category": "staff_mnr_user_members", "menu_icon": "fas fa-user-friends", "route_path": "/staff/mnr-user/members/direct", "display_order": 531, "sidebar_section": "mnr-user-sidebar", "sidebar_section_title": "MNR USER SIDEBAR", "sidebar_section_order": 11},
    {"menu_code": "staff_mnr_user_members_picture", "menu_name": "Binary Tree View", "menu_category": "staff_mnr_user_members", "menu_icon": "fas fa-project-diagram", "route_path": "/staff/mnr-user/members/picture", "display_order": 532, "sidebar_section": "mnr-user-sidebar", "sidebar_section_title": "MNR USER SIDEBAR", "sidebar_section_order": 11},
    {"menu_code": "staff_mnr_user_members_ved", "menu_name": "Ved Team", "menu_category": "staff_mnr_user_members", "menu_icon": "fas fa-users-cog", "route_path": "/staff/mnr-user/members/ved", "display_order": 533, "sidebar_section": "mnr-user-sidebar", "sidebar_section_title": "MNR USER SIDEBAR", "sidebar_section_order": 11},
    # MNR Submenu (Earnings & Withdrawals)
    {"menu_code": "staff_mnr_user_mnr_earnings", "menu_name": "Earnings Summary", "menu_category": "staff_mnr_user_mnr", "menu_icon": "fas fa-chart-line", "route_path": "/staff/mnr-user/mnr/earnings", "display_order": 540, "sidebar_section": "mnr-user-sidebar", "sidebar_section_title": "MNR USER SIDEBAR", "sidebar_section_order": 11},
    {"menu_code": "staff_mnr_user_mnr_direct", "menu_name": "Direct Income", "menu_category": "staff_mnr_user_mnr", "menu_icon": "fas fa-arrow-right", "route_path": "/staff/mnr-user/mnr/direct", "display_order": 541, "sidebar_section": "mnr-user-sidebar", "sidebar_section_title": "MNR USER SIDEBAR", "sidebar_section_order": 11},
    {"menu_code": "staff_mnr_user_mnr_matching", "menu_name": "Matching Income", "menu_category": "staff_mnr_user_mnr", "menu_icon": "fas fa-arrows-alt-h", "route_path": "/staff/mnr-user/mnr/matching", "display_order": 542, "sidebar_section": "mnr-user-sidebar", "sidebar_section_title": "MNR USER SIDEBAR", "sidebar_section_order": 11},
    {"menu_code": "staff_mnr_user_mnr_ved", "menu_name": "Ved Income", "menu_category": "staff_mnr_user_mnr", "menu_icon": "fas fa-layer-group", "route_path": "/staff/mnr-user/mnr/ved", "display_order": 543, "sidebar_section": "mnr-user-sidebar", "sidebar_section_title": "MNR USER SIDEBAR", "sidebar_section_order": 11},
    {"menu_code": "staff_mnr_user_mnr_guru", "menu_name": "Guru Dakshina", "menu_category": "staff_mnr_user_mnr", "menu_icon": "fas fa-praying-hands", "route_path": "/staff/mnr-user/mnr/guru", "display_order": 544, "sidebar_section": "mnr-user-sidebar", "sidebar_section_title": "MNR USER SIDEBAR", "sidebar_section_order": 11},
    {"menu_code": "staff_mnr_user_mnr_withdrawals", "menu_name": "Withdrawals", "menu_category": "staff_mnr_user_mnr", "menu_icon": "fas fa-money-bill-wave", "route_path": "/staff/mnr-user/mnr/withdrawals", "display_order": 545, "sidebar_section": "mnr-user-sidebar", "sidebar_section_title": "MNR USER SIDEBAR", "sidebar_section_order": 11},
    {"menu_code": "staff_mnr_user_mnr_points", "menu_name": "MNR Points", "menu_category": "staff_mnr_user_mnr", "menu_icon": "fas fa-coins", "route_path": "/staff/mnr-user/mnr/points", "display_order": 546, "sidebar_section": "mnr-user-sidebar", "sidebar_section_title": "MNR USER SIDEBAR", "sidebar_section_order": 11},
    {"menu_code": "staff_mnr_user_mnr_benefits", "menu_name": "EV Benefits", "menu_category": "staff_mnr_user_mnr", "menu_icon": "fas fa-bolt", "route_path": "/staff/mnr-user/mnr/benefits", "display_order": 547, "sidebar_section": "mnr-user-sidebar", "sidebar_section_title": "MNR USER SIDEBAR", "sidebar_section_order": 11},
    {"menu_code": "staff_mnr_user_mnr_wallet", "menu_name": "Wallet Overview", "menu_category": "staff_mnr_user_mnr", "menu_icon": "fas fa-wallet", "route_path": "/staff/mnr-user/mnr/wallet", "display_order": 548, "sidebar_section": "mnr-user-sidebar", "sidebar_section_title": "MNR USER SIDEBAR", "sidebar_section_order": 11},
    # MyntReal Submenu
    {"menu_code": "staff_mnr_user_myntreal_leads", "menu_name": "My Leads", "menu_category": "staff_mnr_user_myntreal", "menu_icon": "fas fa-funnel-dollar", "route_path": "/staff/mnr-user/myntreal/leads", "display_order": 550, "sidebar_section": "mnr-user-sidebar", "sidebar_section_title": "MNR USER SIDEBAR", "sidebar_section_order": 11},
    {"menu_code": "staff_mnr_user_myntreal_franchise", "menu_name": "Franchise Status", "menu_category": "staff_mnr_user_myntreal", "menu_icon": "fas fa-store", "route_path": "/staff/mnr-user/myntreal/franchise", "display_order": 551, "sidebar_section": "mnr-user-sidebar", "sidebar_section_title": "MNR USER SIDEBAR", "sidebar_section_order": 11},
    # VGK4U Submenu
    {"menu_code": "staff_mnr_user_zynova_realestate", "menu_name": "Real Estate", "menu_category": "staff_mnr_user_vgk4u", "menu_icon": "fas fa-building", "route_path": "/staff/mnr-user/vgk4u/real-estate", "display_order": 560, "sidebar_section": "mnr-user-sidebar", "sidebar_section_title": "MNR USER SIDEBAR", "sidebar_section_order": 11},
    {"menu_code": "staff_mnr_user_zynova_insurance", "menu_name": "Insurance", "menu_category": "staff_mnr_user_vgk4u", "menu_icon": "fas fa-shield-alt", "route_path": "/staff/mnr-user/vgk4u/insurance", "display_order": 561, "sidebar_section": "mnr-user-sidebar", "sidebar_section_title": "MNR USER SIDEBAR", "sidebar_section_order": 11},
    {"menu_code": "staff_mnr_user_zynova_training", "menu_name": "Training", "menu_category": "staff_mnr_user_vgk4u", "menu_icon": "fas fa-graduation-cap", "route_path": "/staff/mnr-user/vgk4u/training", "display_order": 562, "sidebar_section": "mnr-user-sidebar", "sidebar_section_title": "MNR USER SIDEBAR", "sidebar_section_order": 11},
    # Awards & Bonanza Submenu
    {"menu_code": "staff_mnr_user_awards_all", "menu_name": "All Awards", "menu_category": "staff_mnr_user_awards", "menu_icon": "fas fa-trophy", "route_path": "/staff/mnr-user/awards/all", "display_order": 570, "sidebar_section": "mnr-user-sidebar", "sidebar_section_title": "MNR USER SIDEBAR", "sidebar_section_order": 11},
    {"menu_code": "staff_mnr_user_awards_bonanza", "menu_name": "Bonanza Status", "menu_category": "staff_mnr_user_awards", "menu_icon": "fas fa-gift", "route_path": "/staff/mnr-user/awards/bonanza", "display_order": 571, "sidebar_section": "mnr-user-sidebar", "sidebar_section_title": "MNR USER SIDEBAR", "sidebar_section_order": 11},
    # Audit Log (VGK Supreme Only)
    {"menu_code": "staff_mnr_user_audit_log", "menu_name": "Audit Log", "menu_category": "staff_mnr_user_system", "menu_icon": "fas fa-clipboard-list", "route_path": "/staff/mnr-user/audit-log", "display_order": 590, "sidebar_section": "mnr-user-sidebar", "sidebar_section_title": "MNR USER SIDEBAR", "sidebar_section_order": 11},
    # Zynova Mobility EV — pages added to registry so they appear in the Access Matrix
    {"menu_code": "staff_zynova_ev_po", "menu_name": "EV Spares PO Management", "menu_category": "zynova", "menu_icon": "fas fa-shopping-cart", "route_path": "/staff/zynova/purchase-orders", "display_order": 600},
    {"menu_code": "staff_marketplace_config", "menu_name": "Marketplace Config", "menu_category": "zynova", "menu_icon": "fas fa-cog", "route_path": "/staff/marketplace-config", "display_order": 601},
    {"menu_code": "staff_zynova_etc_students", "menu_name": "ETC Student Master", "menu_category": "zynova", "menu_icon": "fas fa-user-graduate", "route_path": "/staff/zynova/etc-students", "display_order": 602},
    # VGK Team Module (DC Protocol Mar 2026)
    {"menu_code": "VGK_TEAM_MEMBERS", "menu_name": "VGK Members", "menu_category": "vgk_team", "menu_icon": "fas fa-users", "route_path": "/staff/vgk/members", "display_order": 700},
    {"menu_code": "VGK_COMMISSION_CONFIG", "menu_name": "Commission Config", "menu_category": "vgk_team", "menu_icon": "fas fa-sliders-h", "route_path": "/staff/vgk/config", "display_order": 701},
    {"menu_code": "VGK_INCOME_MANAGEMENT", "menu_name": "Income Management", "menu_category": "vgk_team", "menu_icon": "fas fa-hand-holding-usd", "route_path": "/staff/vgk/income-unified", "display_order": 702},
    {"menu_code": "VGK_COUPONS", "menu_name": "VGK Coupons", "menu_category": "vgk_team", "menu_icon": "fas fa-ticket-alt", "route_path": "/staff/vgk/coupons/available", "display_order": 703},
    {"menu_code": "VGK_BONANZA_MANAGEMENT", "menu_name": "Bonanza Campaigns", "menu_category": "vgk_team", "menu_icon": "fas fa-trophy", "route_path": "/staff/vgk/bonanza-management", "display_order": 704},
    {"menu_code": "VGK_BONANZA_CLAIMS", "menu_name": "Bonanza Claims", "menu_category": "vgk_team", "menu_icon": "fas fa-clipboard-check", "route_path": "/staff/vgk/bonanza-claims", "display_order": 705},
    {"menu_code": "VGK_PROMO_CODES", "menu_name": "VGK Promo Codes", "menu_category": "vgk_team", "menu_icon": "fas fa-tags", "route_path": "/staff/vgk/promo-codes", "display_order": 706},
    # DC-VGK-PARTNER-SYNC-001: VGK Admin sub-section for partner KYC review
    {"menu_code": "VGK_PARTNER_KYC_REVIEW", "menu_name": "Partner KYC Review", "menu_category": "vgk_team", "menu_icon": "fas fa-id-card-alt", "route_path": "/staff/vgk/partner-kyc-review", "display_order": 707, "is_default_visible": True, "is_default_accessible": True},

]


def seed_menu_master(db, company_id: int):
    """
    Seed the staff_menu_master table with default menus for a company
    DC Protocol: Company-specific menu catalog initialization
    
    This function should be called during company setup or migration.
    It will only add menus that don't already exist for the company.
    
    audience_scope values:
    - 'staff': Staff-only pages (partners see N/A)
    - 'partner': Partner-only pages (staff see N/A)
    - 'shared': Pages for both staff and partners
    """
    from sqlalchemy.exc import IntegrityError
    
    added_count = 0
    for menu_data in DEFAULT_STAFF_MENUS:
        existing = db.query(StaffMenuMaster).filter_by(
            company_id=company_id,
            menu_code=menu_data['menu_code']
        ).first()
        if not existing:
            menu = StaffMenuMaster(
                company_id=company_id,
                menu_code=menu_data['menu_code'],
                menu_name=menu_data['menu_name'],
                menu_category=menu_data.get('menu_category'),
                menu_icon=menu_data.get('menu_icon'),
                route_path=menu_data.get('route_path'),
                display_order=menu_data.get('display_order', 0),
                audience_scope=menu_data.get('audience_scope', 'staff'),
                is_active=True,
                is_default_visible=menu_data.get('is_default_visible', False),
                is_default_accessible=menu_data.get('is_default_accessible', False)
            )
            db.add(menu)
            added_count += 1
        else:
            changed = False
            if hasattr(existing, 'audience_scope') and menu_data.get('audience_scope'):
                if existing.audience_scope != menu_data.get('audience_scope'):
                    existing.audience_scope = menu_data.get('audience_scope', 'staff')
                    changed = True
            if menu_data.get('menu_category') and existing.menu_category != menu_data.get('menu_category'):
                existing.menu_category = menu_data['menu_category']
                changed = True
            if menu_data.get('menu_icon') and existing.menu_icon != menu_data.get('menu_icon'):
                existing.menu_icon = menu_data['menu_icon']
                changed = True
            if not existing.is_active:
                existing.is_active = True
                changed = True
            # DC_ACCOUNTS_DEFAULT_ACCESS_001: Sync is_default_visible from definition when definition says True
            if menu_data.get('is_default_visible') and not existing.is_default_visible:
                existing.is_default_visible = True
                changed = True
            if menu_data.get('is_default_accessible') and not existing.is_default_accessible:
                existing.is_default_accessible = True
                changed = True
    
    try:
        db.commit()
        return added_count
    except IntegrityError:
        db.rollback()
        return 0
