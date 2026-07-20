"""
Staff Payroll System Models (DC Protocol Compliant)
Comprehensive payroll management with salary calculation, deductions, and SFMS integration

Tables Created:
- staff_payroll_profile: Employee payroll configuration (CTC, components, statutory details)
- staff_payroll_statutory_config: PF/ESI/PT/TDS rate configuration per company
- staff_payroll_cycle: Monthly payroll processing cycle per company
- staff_payroll_run: Per-employee salary calculation per cycle
- staff_payroll_deduction: Individual deduction line items
- staff_consultant_invoice: Offrole/consultant billing
- staff_payroll_document: Offer letters and payslips

Created: Jan 07, 2026
DC Protocol: company_id on all tables for data segregation
WVV Protocol: Role-based visibility (Employee own, HR/Accounts all)
"""

from sqlalchemy import (
    Column, Integer, String, DateTime, Date, Boolean, Text,
    ForeignKey, CheckConstraint, Index, Numeric, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from decimal import Decimal
import enum

from app.models.base import Base, BaseModel, get_indian_time


class EmploymentType(str, enum.Enum):
    """Employee type for payroll processing"""
    ONROLE = "ONROLE"
    OFFROLE = "OFFROLE"


class TaxRegime(str, enum.Enum):
    """Income tax regime for TDS calculation"""
    OLD = "OLD"
    NEW = "NEW"


class PayrollCycleStatus(str, enum.Enum):
    """Payroll cycle processing status"""
    DRAFT = "DRAFT"
    ATTENDANCE_LOCKED = "ATTENDANCE_LOCKED"
    GENERATED = "GENERATED"
    VALIDATED = "VALIDATED"
    APPROVED = "APPROVED"
    PAID = "PAID"
    CANCELLED = "CANCELLED"


class PayrollRunStatus(str, enum.Enum):
    """Individual payroll run status"""
    PENDING = "PENDING"
    CALCULATED = "CALCULATED"
    VALIDATED = "VALIDATED"
    APPROVED = "APPROVED"
    PAID = "PAID"
    ON_HOLD = "ON_HOLD"
    CANCELLED = "CANCELLED"


class PaymentStatus(str, enum.Enum):
    """Payment status for salary disbursement"""
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    PAID = "PAID"
    FAILED = "FAILED"


class ConsultantInvoiceStatus(str, enum.Enum):
    """Consultant invoice processing status"""
    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED"
    VALIDATED = "VALIDATED"
    APPROVED = "APPROVED"
    PAID = "PAID"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"


class ConsultantInvoiceSource(str, enum.Enum):
    """Source of consultant invoice entry"""
    SYSTEM = "SYSTEM"
    MANUAL = "MANUAL"


class PayrollDocumentType(str, enum.Enum):
    """Type of payroll document"""
    OFFER_LETTER = "OFFER_LETTER"
    PAYSLIP = "PAYSLIP"
    SALARY_CERTIFICATE = "SALARY_CERTIFICATE"
    FORM_16 = "FORM_16"


class DeductionType(str, enum.Enum):
    """Types of salary deductions"""
    PF_EMPLOYEE = "PF_EMPLOYEE"
    PF_EMPLOYER = "PF_EMPLOYER"
    ESI_EMPLOYEE = "ESI_EMPLOYEE"
    ESI_EMPLOYER = "ESI_EMPLOYER"
    TDS = "TDS"
    PROFESSIONAL_TAX = "PROFESSIONAL_TAX"
    LOAN_RECOVERY = "LOAN_RECOVERY"
    ADVANCE_RECOVERY = "ADVANCE_RECOVERY"
    OTHER = "OTHER"


class StatutoryConfigType(str, enum.Enum):
    """Types of statutory configuration"""
    PF = "PF"
    ESI = "ESI"
    PROFESSIONAL_TAX = "PROFESSIONAL_TAX"
    TDS_SLAB = "TDS_SLAB"


class StaffPayrollProfile(BaseModel):
    """
    Employee Payroll Profile
    DC Protocol: company_id for data segregation
    Stores salary structure, statutory details, and payroll configuration per employee
    """
    __tablename__ = 'staff_payroll_profile'
    
    id = Column(Integer, primary_key=True, index=True)
    
    employee_id = Column(Integer, ForeignKey('staff_employees.id', ondelete='CASCADE'), nullable=False, index=True)
    company_id = Column(Integer, ForeignKey('associated_companies.id', ondelete='CASCADE'), nullable=False, index=True)
    
    employment_type = Column(String(20), nullable=False, default='ONROLE')
    
    pan_number = Column(String(15), nullable=True)
    uan_number = Column(String(20), nullable=True)
    esi_ip_number = Column(String(20), nullable=True)
    pt_state = Column(String(50), nullable=True, default='KARNATAKA')
    tax_regime = Column(String(10), nullable=False, default='NEW')
    
    ctc_monthly = Column(Numeric(15, 2), nullable=False, default=0)
    ctc_annual = Column(Numeric(15, 2), nullable=False, default=0)
    
    basic_pct = Column(Numeric(5, 2), nullable=False, default=40.00)
    hra_pct = Column(Numeric(5, 2), nullable=False, default=20.00)
    special_allowance = Column(Numeric(15, 2), nullable=True, default=0)
    other_components = Column(JSONB, nullable=True, default={})
    
    pf_applicable = Column(Boolean, default=True, nullable=False)
    esi_applicable = Column(Boolean, default=False, nullable=False)
    pt_applicable = Column(Boolean, default=True, nullable=False)
    tds_applicable = Column(Boolean, default=True, nullable=False)
    
    deductions_enabled = Column(Boolean, default=True, nullable=False)
    
    bank_account_number = Column(String(30), nullable=True)
    bank_ifsc_code = Column(String(15), nullable=True)
    bank_name = Column(String(200), nullable=True)
    bank_branch = Column(String(200), nullable=True)
    bank_account_holder = Column(String(200), nullable=True)
    bank_verified = Column(Boolean, default=False, nullable=False)
    
    effective_from = Column(Date, nullable=False)
    effective_to = Column(Date, nullable=True)
    
    is_active = Column(Boolean, default=True, nullable=False)
    
    created_by_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    updated_by_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time, nullable=False)
    
    employee = relationship("StaffEmployee", foreign_keys=[employee_id])
    company = relationship("AssociatedCompany", foreign_keys=[company_id])
    
    __table_args__ = (
        CheckConstraint(
            "employment_type IN ('ONROLE', 'OFFROLE')",
            name='payroll_profile_employment_type_check'
        ),
        CheckConstraint(
            "tax_regime IN ('OLD', 'NEW')",
            name='payroll_profile_tax_regime_check'
        ),
        CheckConstraint(
            "basic_pct >= 0 AND basic_pct <= 100",
            name='payroll_profile_basic_pct_check'
        ),
        CheckConstraint(
            "hra_pct >= 0 AND hra_pct <= 100",
            name='payroll_profile_hra_pct_check'
        ),
        UniqueConstraint('employee_id', 'company_id', 'effective_from', name='uq_payroll_profile_emp_company_effective'),
        Index('idx_payroll_profile_employee', 'employee_id'),
        Index('idx_payroll_profile_company', 'company_id'),
        Index('idx_payroll_profile_active', 'is_active'),
    )
    
    def __repr__(self):
        return f'<StaffPayrollProfile Employee:{self.employee_id} CTC:₹{self.ctc_monthly}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'employee_id': self.employee_id,
            'company_id': self.company_id,
            'employment_type': self.employment_type,
            'pan_number': self.pan_number,
            'uan_number': self.uan_number,
            'esi_ip_number': self.esi_ip_number,
            'pt_state': self.pt_state,
            'tax_regime': self.tax_regime,
            'ctc_monthly': float(self.ctc_monthly) if self.ctc_monthly else 0,
            'ctc_annual': float(self.ctc_annual) if self.ctc_annual else 0,
            'basic_pct': float(self.basic_pct) if self.basic_pct else 40,
            'hra_pct': float(self.hra_pct) if self.hra_pct else 20,
            'special_allowance': float(self.special_allowance) if self.special_allowance else 0,
            'other_components': self.other_components or {},
            'pf_applicable': self.pf_applicable,
            'esi_applicable': self.esi_applicable,
            'pt_applicable': self.pt_applicable,
            'tds_applicable': self.tds_applicable,
            'deductions_enabled': self.deductions_enabled,
            'bank_account_number': self.bank_account_number,
            'bank_ifsc_code': self.bank_ifsc_code,
            'bank_name': self.bank_name,
            'bank_branch': self.bank_branch,
            'bank_account_holder': self.bank_account_holder,
            'bank_verified': self.bank_verified,
            'effective_from': self.effective_from.isoformat() if self.effective_from else None,
            'effective_to': self.effective_to.isoformat() if self.effective_to else None,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class StaffPayrollStatutoryConfig(BaseModel):
    """
    Statutory Rate Configuration
    DC Protocol: company_id for company-specific rates
    Stores PF, ESI, PT rates and TDS slabs per company
    """
    __tablename__ = 'staff_payroll_statutory_config'
    
    id = Column(Integer, primary_key=True, index=True)
    
    company_id = Column(Integer, ForeignKey('associated_companies.id', ondelete='CASCADE'), nullable=False, index=True)
    
    config_type = Column(String(30), nullable=False)
    config_code = Column(String(50), nullable=False)
    config_name = Column(String(200), nullable=False)
    
    rate_value = Column(Numeric(10, 4), nullable=True)
    amount_value = Column(Numeric(15, 2), nullable=True)
    ceiling_amount = Column(Numeric(15, 2), nullable=True)
    floor_amount = Column(Numeric(15, 2), nullable=True)
    
    slab_from = Column(Numeric(15, 2), nullable=True)
    slab_to = Column(Numeric(15, 2), nullable=True)
    
    config_details = Column(JSONB, nullable=True, default={})
    
    effective_from = Column(Date, nullable=False)
    effective_to = Column(Date, nullable=True)
    
    is_active = Column(Boolean, default=True, nullable=False)
    
    created_by_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    updated_by_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time, nullable=False)
    
    company = relationship("AssociatedCompany", foreign_keys=[company_id])
    
    __table_args__ = (
        CheckConstraint(
            "config_type IN ('PF', 'ESI', 'PROFESSIONAL_TAX', 'TDS_SLAB')",
            name='statutory_config_type_check'
        ),
        UniqueConstraint('company_id', 'config_type', 'config_code', 'effective_from', name='uq_statutory_config'),
        Index('idx_statutory_config_company', 'company_id'),
        Index('idx_statutory_config_type', 'config_type'),
    )
    
    def __repr__(self):
        return f'<StaffPayrollStatutoryConfig {self.config_type}:{self.config_code}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'company_id': self.company_id,
            'config_type': self.config_type,
            'config_code': self.config_code,
            'config_name': self.config_name,
            'rate_value': float(self.rate_value) if self.rate_value else None,
            'amount_value': float(self.amount_value) if self.amount_value else None,
            'ceiling_amount': float(self.ceiling_amount) if self.ceiling_amount else None,
            'floor_amount': float(self.floor_amount) if self.floor_amount else None,
            'slab_from': float(self.slab_from) if self.slab_from else None,
            'slab_to': float(self.slab_to) if self.slab_to else None,
            'config_details': self.config_details or {},
            'effective_from': self.effective_from.isoformat() if self.effective_from else None,
            'effective_to': self.effective_to.isoformat() if self.effective_to else None,
            'is_active': self.is_active
        }


class StaffPayrollCycle(BaseModel):
    """
    Monthly Payroll Processing Cycle
    DC Protocol: company_id for company-wise payroll processing
    Tracks the complete payroll workflow from attendance lock to payment
    """
    __tablename__ = 'staff_payroll_cycle'
    
    id = Column(Integer, primary_key=True, index=True)
    
    cycle_code = Column(String(30), unique=True, nullable=False, index=True)
    
    company_id = Column(Integer, ForeignKey('associated_companies.id', ondelete='CASCADE'), nullable=False, index=True)
    
    cycle_month = Column(Integer, nullable=False)
    cycle_year = Column(Integer, nullable=False)
    
    period_start = Column(Date, nullable=False)
    period_end = Column(Date, nullable=False)
    
    status = Column(String(30), nullable=False, default='DRAFT')
    
    total_employees = Column(Integer, nullable=False, default=0)
    total_gross_salary = Column(Numeric(15, 2), nullable=False, default=0)
    total_deductions = Column(Numeric(15, 2), nullable=False, default=0)
    total_net_salary = Column(Numeric(15, 2), nullable=False, default=0)
    
    attendance_locked_at = Column(DateTime, nullable=True)
    attendance_locked_by = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    
    generated_at = Column(DateTime, nullable=True)
    generated_by = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    
    validated_at = Column(DateTime, nullable=True)
    validated_by = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    validation_remarks = Column(Text, nullable=True)
    
    approved_at = Column(DateTime, nullable=True)
    approved_by = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    approval_remarks = Column(Text, nullable=True)
    
    paid_at = Column(DateTime, nullable=True)
    paid_by = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    payment_reference = Column(String(100), nullable=True)
    payment_remarks = Column(Text, nullable=True)
    
    sfms_posted = Column(Boolean, default=False, nullable=False)
    sfms_posted_at = Column(DateTime, nullable=True)
    sfms_journal_id = Column(Integer, nullable=True)
    
    notes = Column(Text, nullable=True)
    
    created_by_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    updated_by_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time, nullable=False)
    
    company = relationship("AssociatedCompany", foreign_keys=[company_id])
    payroll_runs = relationship("StaffPayrollRun", back_populates="cycle", cascade="all, delete-orphan")
    
    __table_args__ = (
        CheckConstraint(
            "status IN ('DRAFT', 'ATTENDANCE_LOCKED', 'GENERATED', 'VALIDATED', 'APPROVED', 'PAID', 'CANCELLED')",
            name='payroll_cycle_status_check'
        ),
        CheckConstraint(
            "cycle_month >= 1 AND cycle_month <= 12",
            name='payroll_cycle_month_check'
        ),
        UniqueConstraint('company_id', 'cycle_month', 'cycle_year', name='uq_payroll_cycle_company_month_year'),
        Index('idx_payroll_cycle_company', 'company_id'),
        Index('idx_payroll_cycle_period', 'cycle_year', 'cycle_month'),
        Index('idx_payroll_cycle_status', 'status'),
    )
    
    def __repr__(self):
        return f'<StaffPayrollCycle {self.cycle_code} {self.cycle_month}/{self.cycle_year}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'cycle_code': self.cycle_code,
            'company_id': self.company_id,
            'cycle_month': self.cycle_month,
            'cycle_year': self.cycle_year,
            'period_start': self.period_start.isoformat() if self.period_start else None,
            'period_end': self.period_end.isoformat() if self.period_end else None,
            'status': self.status,
            'total_employees': self.total_employees,
            'total_gross_salary': float(self.total_gross_salary) if self.total_gross_salary else 0,
            'total_deductions': float(self.total_deductions) if self.total_deductions else 0,
            'total_net_salary': float(self.total_net_salary) if self.total_net_salary else 0,
            'attendance_locked_at': self.attendance_locked_at.isoformat() if self.attendance_locked_at else None,
            'generated_at': self.generated_at.isoformat() if self.generated_at else None,
            'validated_at': self.validated_at.isoformat() if self.validated_at else None,
            'approved_at': self.approved_at.isoformat() if self.approved_at else None,
            'paid_at': self.paid_at.isoformat() if self.paid_at else None,
            'sfms_posted': self.sfms_posted,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class StaffPayrollRun(BaseModel):
    """
    Per-Employee Payroll Calculation
    DC Protocol: company_id for data segregation
    Stores calculated salary, deductions, and net pay per employee per cycle
    """
    __tablename__ = 'staff_payroll_run'
    
    id = Column(Integer, primary_key=True, index=True)
    
    run_code = Column(String(50), unique=True, nullable=False, index=True)
    
    cycle_id = Column(Integer, ForeignKey('staff_payroll_cycle.id', ondelete='CASCADE'), nullable=False, index=True)
    employee_id = Column(Integer, ForeignKey('staff_employees.id', ondelete='CASCADE'), nullable=False, index=True)
    company_id = Column(Integer, ForeignKey('associated_companies.id', ondelete='CASCADE'), nullable=False, index=True)
    profile_id = Column(Integer, ForeignKey('staff_payroll_profile.id'), nullable=True)
    
    eligible_days = Column(Numeric(5, 2), nullable=False, default=0)
    present_days = Column(Numeric(5, 2), nullable=False, default=0)
    lop_days = Column(Numeric(5, 2), nullable=False, default=0)
    leave_days = Column(Numeric(5, 2), nullable=False, default=0)
    
    ctc_monthly = Column(Numeric(15, 2), nullable=False, default=0)
    
    gross_salary = Column(Numeric(15, 2), nullable=False, default=0)
    basic_amount = Column(Numeric(15, 2), nullable=False, default=0)
    hra_amount = Column(Numeric(15, 2), nullable=False, default=0)
    special_allowance = Column(Numeric(15, 2), nullable=False, default=0)
    other_earnings = Column(JSONB, nullable=True, default={})
    
    pf_employee = Column(Numeric(15, 2), nullable=False, default=0)
    pf_employer = Column(Numeric(15, 2), nullable=False, default=0)
    esi_employee = Column(Numeric(15, 2), nullable=False, default=0)
    esi_employer = Column(Numeric(15, 2), nullable=False, default=0)
    tds_amount = Column(Numeric(15, 2), nullable=False, default=0)
    pt_amount = Column(Numeric(15, 2), nullable=False, default=0)
    other_deductions = Column(JSONB, nullable=True, default={})
    
    total_earnings = Column(Numeric(15, 2), nullable=False, default=0)
    total_deductions = Column(Numeric(15, 2), nullable=False, default=0)
    net_salary = Column(Numeric(15, 2), nullable=False, default=0)
    
    employer_contributions = Column(Numeric(15, 2), nullable=False, default=0)
    ctc_cost = Column(Numeric(15, 2), nullable=False, default=0)
    
    status = Column(String(20), nullable=False, default='PENDING')
    
    payment_status = Column(String(20), nullable=False, default='PENDING')
    payment_date = Column(Date, nullable=True)
    payment_reference = Column(String(100), nullable=True)
    payment_mode = Column(String(20), nullable=True)
    bank_reference = Column(String(100), nullable=True)
    
    payslip_generated = Column(Boolean, default=False, nullable=False)
    payslip_path = Column(String(500), nullable=True)
    
    on_hold = Column(Boolean, default=False, nullable=False)
    hold_reason = Column(Text, nullable=True)
    hold_by = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    
    calculation_details = Column(JSONB, nullable=True, default={})
    
    notes = Column(Text, nullable=True)
    
    created_by_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    updated_by_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time, nullable=False)
    
    cycle = relationship("StaffPayrollCycle", back_populates="payroll_runs")
    employee = relationship("StaffEmployee", foreign_keys=[employee_id])
    company = relationship("AssociatedCompany", foreign_keys=[company_id])
    profile = relationship("StaffPayrollProfile", foreign_keys=[profile_id])
    deductions = relationship("StaffPayrollDeduction", back_populates="payroll_run", cascade="all, delete-orphan")
    
    __table_args__ = (
        CheckConstraint(
            "status IN ('PENDING', 'CALCULATED', 'VALIDATED', 'APPROVED', 'REJECTED', 'PAID', 'ON_HOLD', 'CANCELLED')",
            name='payroll_run_status_check'
        ),
        CheckConstraint(
            "payment_status IN ('PENDING', 'PROCESSING', 'PAID', 'FAILED')",
            name='payroll_run_payment_status_check'
        ),
        UniqueConstraint('cycle_id', 'employee_id', name='uq_payroll_run_cycle_employee'),
        Index('idx_payroll_run_cycle', 'cycle_id'),
        Index('idx_payroll_run_employee', 'employee_id'),
        Index('idx_payroll_run_company', 'company_id'),
        Index('idx_payroll_run_status', 'status'),
    )
    
    def __repr__(self):
        return f'<StaffPayrollRun {self.run_code} Net:₹{self.net_salary}>'
    
    def to_dict(self, include_employee=False):
        data = {
            'id': self.id,
            'run_code': self.run_code,
            'cycle_id': self.cycle_id,
            'employee_id': self.employee_id,
            'company_id': self.company_id,
            'eligible_days': float(self.eligible_days) if self.eligible_days else 0,
            'present_days': float(self.present_days) if self.present_days else 0,
            'lop_days': float(self.lop_days) if self.lop_days else 0,
            'leave_days': float(self.leave_days) if self.leave_days else 0,
            'ctc_monthly': float(self.ctc_monthly) if self.ctc_monthly else 0,
            'gross_salary': float(self.gross_salary) if self.gross_salary else 0,
            'basic_amount': float(self.basic_amount) if self.basic_amount else 0,
            'hra_amount': float(self.hra_amount) if self.hra_amount else 0,
            'special_allowance': float(self.special_allowance) if self.special_allowance else 0,
            'other_earnings': self.other_earnings or {},
            'pf_employee': float(self.pf_employee) if self.pf_employee else 0,
            'pf_employer': float(self.pf_employer) if self.pf_employer else 0,
            'esi_employee': float(self.esi_employee) if self.esi_employee else 0,
            'esi_employer': float(self.esi_employer) if self.esi_employer else 0,
            'tds_amount': float(self.tds_amount) if self.tds_amount else 0,
            'pt_amount': float(self.pt_amount) if self.pt_amount else 0,
            'other_deductions': self.other_deductions or {},
            'total_earnings': float(self.total_earnings) if self.total_earnings else 0,
            'total_deductions': float(self.total_deductions) if self.total_deductions else 0,
            'net_salary': float(self.net_salary) if self.net_salary else 0,
            'employer_contributions': float(self.employer_contributions) if self.employer_contributions else 0,
            'ctc_cost': float(self.ctc_cost) if self.ctc_cost else 0,
            'status': self.status,
            'payment_status': self.payment_status,
            'payment_date': self.payment_date.isoformat() if self.payment_date else None,
            'payment_reference': self.payment_reference,
            'payslip_generated': self.payslip_generated,
            'on_hold': self.on_hold,
            'hold_reason': self.hold_reason,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
        if include_employee and self.employee:
            data['employee_name'] = self.employee.full_name
            data['employee_code'] = self.employee.emp_code
            data['department_name'] = self.employee.department.name if self.employee.department else None
        return data


class StaffPayrollDeduction(BaseModel):
    """
    Individual Deduction Line Items
    DC Protocol: company_id for data segregation
    Detailed breakdown of each deduction type per payroll run
    """
    __tablename__ = 'staff_payroll_deduction'
    
    id = Column(Integer, primary_key=True, index=True)
    
    payroll_run_id = Column(Integer, ForeignKey('staff_payroll_run.id', ondelete='CASCADE'), nullable=False, index=True)
    company_id = Column(Integer, ForeignKey('associated_companies.id', ondelete='CASCADE'), nullable=False, index=True)
    
    deduction_type = Column(String(30), nullable=False)
    deduction_code = Column(String(50), nullable=False)
    deduction_name = Column(String(200), nullable=False)
    
    base_amount = Column(Numeric(15, 2), nullable=False, default=0)
    rate_applied = Column(Numeric(10, 4), nullable=True)
    calculated_amount = Column(Numeric(15, 2), nullable=False, default=0)
    
    is_employee_contribution = Column(Boolean, default=True, nullable=False)
    is_employer_contribution = Column(Boolean, default=False, nullable=False)
    
    remarks = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    
    payroll_run = relationship("StaffPayrollRun", back_populates="deductions")
    company = relationship("AssociatedCompany", foreign_keys=[company_id])
    
    __table_args__ = (
        CheckConstraint(
            "deduction_type IN ('PF_EMPLOYEE', 'PF_EMPLOYER', 'ESI_EMPLOYEE', 'ESI_EMPLOYER', 'TDS', 'PROFESSIONAL_TAX', 'LOAN_RECOVERY', 'ADVANCE_RECOVERY', 'OTHER')",
            name='payroll_deduction_type_check'
        ),
        Index('idx_payroll_deduction_run', 'payroll_run_id'),
        Index('idx_payroll_deduction_type', 'deduction_type'),
    )
    
    def __repr__(self):
        return f'<StaffPayrollDeduction {self.deduction_type}: ₹{self.calculated_amount}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'payroll_run_id': self.payroll_run_id,
            'deduction_type': self.deduction_type,
            'deduction_code': self.deduction_code,
            'deduction_name': self.deduction_name,
            'base_amount': float(self.base_amount) if self.base_amount else 0,
            'rate_applied': float(self.rate_applied) if self.rate_applied else None,
            'calculated_amount': float(self.calculated_amount) if self.calculated_amount else 0,
            'is_employee_contribution': self.is_employee_contribution,
            'is_employer_contribution': self.is_employer_contribution,
            'remarks': self.remarks
        }


class StaffConsultantInvoice(BaseModel):
    """
    Consultant/Offrole Invoice Management
    DC Protocol: company_id for data segregation
    Handles both system-generated and manual invoice entry for consultants
    """
    __tablename__ = 'staff_consultant_invoice'
    
    id = Column(Integer, primary_key=True, index=True)
    
    invoice_number = Column(String(50), unique=True, nullable=False, index=True)
    
    employee_id = Column(Integer, ForeignKey('staff_employees.id', ondelete='CASCADE'), nullable=False, index=True)
    company_id = Column(Integer, ForeignKey('associated_companies.id', ondelete='CASCADE'), nullable=False, index=True)
    cycle_id = Column(Integer, ForeignKey('staff_payroll_cycle.id'), nullable=True)
    
    invoice_date = Column(Date, nullable=False)
    service_period_from = Column(Date, nullable=False)
    service_period_to = Column(Date, nullable=False)
    
    service_description = Column(Text, nullable=True)
    
    invoice_amount = Column(Numeric(15, 2), nullable=False)
    
    gst_applicable = Column(Boolean, default=False, nullable=False)
    gst_rate = Column(Numeric(5, 2), nullable=True, default=18.00)
    gst_amount = Column(Numeric(15, 2), nullable=False, default=0)
    
    tds_applicable = Column(Boolean, default=True, nullable=False)
    tds_section = Column(String(20), nullable=True, default='194J')
    tds_rate = Column(Numeric(5, 2), nullable=False, default=10.00)
    tds_amount = Column(Numeric(15, 2), nullable=False, default=0)
    
    total_amount = Column(Numeric(15, 2), nullable=False, default=0)
    net_payable = Column(Numeric(15, 2), nullable=False, default=0)
    
    source = Column(String(20), nullable=False, default='SYSTEM')
    
    invoice_path = Column(String(500), nullable=True)
    
    status = Column(String(20), nullable=False, default='DRAFT')
    
    submitted_at = Column(DateTime, nullable=True)
    
    validated_by = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    validated_at = Column(DateTime, nullable=True)
    validation_remarks = Column(Text, nullable=True)
    
    approved_by = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    approval_remarks = Column(Text, nullable=True)
    
    paid_at = Column(DateTime, nullable=True)
    paid_by = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    payment_reference = Column(String(100), nullable=True)
    payment_mode = Column(String(20), nullable=True)
    
    rejected_by = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    rejected_at = Column(DateTime, nullable=True)
    rejection_reason = Column(Text, nullable=True)
    
    sfms_posted = Column(Boolean, default=False, nullable=False)
    sfms_entry_id = Column(Integer, nullable=True)
    
    created_by_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    updated_by_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time, nullable=False)
    
    employee = relationship("StaffEmployee", foreign_keys=[employee_id])
    company = relationship("AssociatedCompany", foreign_keys=[company_id])
    cycle = relationship("StaffPayrollCycle", foreign_keys=[cycle_id])
    
    __table_args__ = (
        CheckConstraint(
            "status IN ('DRAFT', 'SUBMITTED', 'VALIDATED', 'APPROVED', 'PAID', 'REJECTED', 'CANCELLED')",
            name='consultant_invoice_status_check'
        ),
        CheckConstraint(
            "source IN ('SYSTEM', 'MANUAL')",
            name='consultant_invoice_source_check'
        ),
        Index('idx_consultant_invoice_employee', 'employee_id'),
        Index('idx_consultant_invoice_company', 'company_id'),
        Index('idx_consultant_invoice_status', 'status'),
        Index('idx_consultant_invoice_date', 'invoice_date'),
    )
    
    def __repr__(self):
        return f'<StaffConsultantInvoice {self.invoice_number}: ₹{self.net_payable}>'
    
    def to_dict(self, include_employee=False):
        data = {
            'id': self.id,
            'invoice_number': self.invoice_number,
            'employee_id': self.employee_id,
            'company_id': self.company_id,
            'cycle_id': self.cycle_id,
            'invoice_date': self.invoice_date.isoformat() if self.invoice_date else None,
            'service_period_from': self.service_period_from.isoformat() if self.service_period_from else None,
            'service_period_to': self.service_period_to.isoformat() if self.service_period_to else None,
            'service_description': self.service_description,
            'invoice_amount': float(self.invoice_amount) if self.invoice_amount else 0,
            'gst_applicable': self.gst_applicable,
            'gst_rate': float(self.gst_rate) if self.gst_rate else 0,
            'gst_amount': float(self.gst_amount) if self.gst_amount else 0,
            'tds_applicable': self.tds_applicable,
            'tds_section': self.tds_section,
            'tds_rate': float(self.tds_rate) if self.tds_rate else 0,
            'tds_amount': float(self.tds_amount) if self.tds_amount else 0,
            'total_amount': float(self.total_amount) if self.total_amount else 0,
            'net_payable': float(self.net_payable) if self.net_payable else 0,
            'source': self.source,
            'invoice_path': self.invoice_path,
            'status': self.status,
            'submitted_at': self.submitted_at.isoformat() if self.submitted_at else None,
            'validated_at': self.validated_at.isoformat() if self.validated_at else None,
            'approved_at': self.approved_at.isoformat() if self.approved_at else None,
            'paid_at': self.paid_at.isoformat() if self.paid_at else None,
            'payment_reference': self.payment_reference,
            'sfms_posted': self.sfms_posted,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
        if include_employee and self.employee:
            data['employee_name'] = self.employee.full_name
            data['employee_code'] = self.employee.emp_code
        return data


class StaffPayrollDocument(BaseModel):
    """
    Payroll Document Management
    DC Protocol: company_id for data segregation
    WVV Protocol: Role-based download access (HR/Accounts/VGK only)
    Stores offer letters, payslips, Form 16, salary certificates
    """
    __tablename__ = 'staff_payroll_document'
    
    id = Column(Integer, primary_key=True, index=True)
    
    document_code = Column(String(50), unique=True, nullable=False, index=True)
    
    employee_id = Column(Integer, ForeignKey('staff_employees.id', ondelete='CASCADE'), nullable=False, index=True)
    company_id = Column(Integer, ForeignKey('associated_companies.id', ondelete='CASCADE'), nullable=False, index=True)
    cycle_id = Column(Integer, ForeignKey('staff_payroll_cycle.id'), nullable=True)
    payroll_run_id = Column(Integer, ForeignKey('staff_payroll_run.id'), nullable=True)
    
    document_type = Column(String(30), nullable=False)
    document_title = Column(String(200), nullable=False)
    
    file_path = Column(String(500), nullable=False)
    file_name = Column(String(200), nullable=False)
    file_size = Column(Integer, nullable=True)
    
    document_date = Column(Date, nullable=False)
    
    is_template = Column(Boolean, default=False, nullable=False)
    template_data = Column(JSONB, nullable=True)
    
    generated_at = Column(DateTime, default=get_indian_time, nullable=False)
    generated_by = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    
    download_count = Column(Integer, default=0, nullable=False)
    last_downloaded_at = Column(DateTime, nullable=True)
    last_downloaded_by = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    
    is_active = Column(Boolean, default=True, nullable=False)
    
    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time, nullable=False)
    
    employee = relationship("StaffEmployee", foreign_keys=[employee_id])
    company = relationship("AssociatedCompany", foreign_keys=[company_id])
    
    __table_args__ = (
        CheckConstraint(
            "document_type IN ('OFFER_LETTER', 'PAYSLIP', 'SALARY_CERTIFICATE', 'FORM_16')",
            name='payroll_document_type_check'
        ),
        Index('idx_payroll_document_employee', 'employee_id'),
        Index('idx_payroll_document_company', 'company_id'),
        Index('idx_payroll_document_type', 'document_type'),
        Index('idx_payroll_document_cycle', 'cycle_id'),
    )
    
    def __repr__(self):
        return f'<StaffPayrollDocument {self.document_type}: {self.document_title}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'document_code': self.document_code,
            'employee_id': self.employee_id,
            'company_id': self.company_id,
            'cycle_id': self.cycle_id,
            'payroll_run_id': self.payroll_run_id,
            'document_type': self.document_type,
            'document_title': self.document_title,
            'file_path': self.file_path,
            'file_name': self.file_name,
            'file_size': self.file_size,
            'document_date': self.document_date.isoformat() if self.document_date else None,
            'is_template': self.is_template,
            'generated_at': self.generated_at.isoformat() if self.generated_at else None,
            'download_count': self.download_count,
            'is_active': self.is_active
        }


class StaffPayrollAuditLog(BaseModel):
    """
    Payroll Audit Trail
    DC Protocol: Immutable audit log for all payroll actions
    """
    __tablename__ = 'staff_payroll_audit_log'
    
    id = Column(Integer, primary_key=True, index=True)
    
    company_id = Column(Integer, ForeignKey('associated_companies.id'), nullable=False, index=True)
    
    entity_type = Column(String(50), nullable=False)
    entity_id = Column(Integer, nullable=False)
    
    action = Column(String(50), nullable=False)
    action_details = Column(JSONB, nullable=True)
    
    old_values = Column(JSONB, nullable=True)
    new_values = Column(JSONB, nullable=True)
    
    performed_by = Column(Integer, ForeignKey('staff_employees.id'), nullable=False)
    performed_at = Column(DateTime, default=get_indian_time, nullable=False)
    
    ip_address = Column(String(50), nullable=True)
    user_agent = Column(Text, nullable=True)
    
    __table_args__ = (
        Index('idx_payroll_audit_entity', 'entity_type', 'entity_id'),
        Index('idx_payroll_audit_action', 'action'),
        Index('idx_payroll_audit_performed_at', 'performed_at'),
    )
    
    def __repr__(self):
        return f'<StaffPayrollAuditLog {self.entity_type}:{self.entity_id} {self.action}>'


class StaffPayrollAllowanceCatalog(BaseModel):
    """
    Custom Allowance Type Catalog
    DC Protocol: company_id for company-specific allowance definitions
    Stores company-defined allowance types beyond the default 17 predefined types
    """
    __tablename__ = 'staff_payroll_allowance_catalog'
    
    id = Column(Integer, primary_key=True, index=True)
    
    company_id = Column(Integer, ForeignKey('associated_companies.id', ondelete='CASCADE'), nullable=False, index=True)
    
    allowance_code = Column(String(50), nullable=False)
    allowance_name = Column(String(200), nullable=False)
    allowance_description = Column(Text, nullable=True)
    
    is_taxable = Column(Boolean, default=True, nullable=False)
    is_percentage = Column(Boolean, default=False, nullable=False)
    default_value = Column(Numeric(15, 2), nullable=True)
    max_limit = Column(Numeric(15, 2), nullable=True)
    
    applicable_employment_types = Column(JSONB, nullable=True, default=['ONROLE', 'OFFROLE'])
    
    display_order = Column(Integer, nullable=False, default=100)
    is_active = Column(Boolean, default=True, nullable=False)
    
    created_by_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    updated_by_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time, nullable=False)
    
    company = relationship("AssociatedCompany", foreign_keys=[company_id])
    
    __table_args__ = (
        UniqueConstraint('company_id', 'allowance_code', name='uq_allowance_catalog_company_code'),
        Index('idx_allowance_catalog_company', 'company_id'),
        Index('idx_allowance_catalog_active', 'is_active'),
    )
    
    def __repr__(self):
        return f'<StaffPayrollAllowanceCatalog {self.allowance_code}: {self.allowance_name}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'company_id': self.company_id,
            'allowance_code': self.allowance_code,
            'allowance_name': self.allowance_name,
            'allowance_description': self.allowance_description,
            'is_taxable': self.is_taxable,
            'is_percentage': self.is_percentage,
            'default_value': float(self.default_value) if self.default_value else None,
            'max_limit': float(self.max_limit) if self.max_limit else None,
            'applicable_employment_types': self.applicable_employment_types,
            'display_order': self.display_order,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


def generate_payroll_cycle_code(company_id: int, month: int, year: int) -> str:
    """Generate unique payroll cycle code"""
    return f"PC-{company_id}-{year}{month:02d}"


def generate_payroll_run_code(cycle_id: int, employee_id: int) -> str:
    """Generate unique payroll run code"""
    return f"PR-{cycle_id}-{employee_id}"


def generate_consultant_invoice_number(company_id: int, year: int, sequence: int) -> str:
    """Generate unique consultant invoice number"""
    return f"CI-{company_id}-{year}-{sequence:04d}"


def generate_payroll_document_code(doc_type: str, employee_id: int, year: int, month: int) -> str:
    """Generate unique payroll document code"""
    type_prefix = {
        'OFFER_LETTER': 'OL',
        'PAYSLIP': 'PS',
        'SALARY_CERTIFICATE': 'SC',
        'FORM_16': 'F16'
    }
    prefix = type_prefix.get(doc_type, 'DOC')
    return f"{prefix}-{employee_id}-{year}{month:02d}"


TDS_SLABS_NEW_REGIME = [
    {'slab_from': 0, 'slab_to': 300000, 'rate': 0},
    {'slab_from': 300001, 'slab_to': 700000, 'rate': 5},
    {'slab_from': 700001, 'slab_to': 1000000, 'rate': 10},
    {'slab_from': 1000001, 'slab_to': 1200000, 'rate': 15},
    {'slab_from': 1200001, 'slab_to': 1500000, 'rate': 20},
    {'slab_from': 1500001, 'slab_to': 999999999, 'rate': 30}
]

TDS_SLABS_OLD_REGIME = [
    {'slab_from': 0, 'slab_to': 250000, 'rate': 0},
    {'slab_from': 250001, 'slab_to': 500000, 'rate': 5},
    {'slab_from': 500001, 'slab_to': 1000000, 'rate': 20},
    {'slab_from': 1000001, 'slab_to': 999999999, 'rate': 30}
]

DEFAULT_STATUTORY_CONFIG = {
    'PF_EMPLOYEE_RATE': 12.00,
    'PF_EMPLOYER_RATE': 12.00,
    'ESI_EMPLOYEE_RATE': 0.75,
    'ESI_EMPLOYER_RATE': 3.25,
    'ESI_CEILING': 21000,
    'PT_AMOUNT': 200,
    'BASIC_PCT': 40,
    'HRA_PCT': 20
}
