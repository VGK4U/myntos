"""
Staff Attendance Sheet Model (DC Protocol Compliant)
Bulk marking system for HR/EA/VGK - separate from clock-in/out

Features:
- HR marks attendance (Present/Half/Leave/Absent)
- EA/VGK approves hours (can differ from marked)
- Reconciliation with timesheet (break time excluded)
- Monthly reporting with net days calculation
- Immutable audit trail (WVV Protocol)

Created: Dec 01, 2025
"""

from sqlalchemy import (
    Column, Integer, String, Date, DateTime, Numeric, Text, Boolean,
    ForeignKey, CheckConstraint, Index, UniqueConstraint, Enum as SQLEnum
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from datetime import datetime
import pytz
import enum

from app.models.base import Base


def get_indian_time():
    """Get current time in Indian timezone (IST)"""
    ist = pytz.timezone('Asia/Kolkata')
    return datetime.now(ist).replace(tzinfo=None)


class AttendanceStatus(str, enum.Enum):
    """HR marking status"""
    PRESENT = "present"
    HALF_DAY = "half_day"
    ABSENT = "absent"
    SICK_LEAVE = "sick_leave"
    APPROVED_LEAVE = "approved_leave"
    CASUAL_LEAVE = "casual_leave"
    UNPAID_LEAVE = "unpaid_leave"
    HOLIDAY = "holiday"
    WEEKEND = "weekend"


class ApprovalStatus(str, enum.Enum):
    """EA/VGK approval status"""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    ON_HOLD = "on_hold"


class ReconciliationStatus(str, enum.Enum):
    """Comparison with employee timesheet"""
    MATCHED = "matched"  # Marked hours ≈ timesheet hours (±0.5 hrs)
    MISMATCH_WARNING = "mismatch_warning"  # Significant difference
    MANUAL_OVERRIDE = "manual_override"  # Marked but no timesheet entry
    NO_ENTRY = "no_entry"  # Employee didn't clock in


class ExceptionBypassType(str, enum.Enum):
    """DC Protocol (Jan 01, 2026): Types of exception bypasses"""
    NO_TIMESHEET = "no_timesheet"  # Approved without timesheet entry
    MISMATCH_OVERRIDE = "mismatch_override"  # Approved despite hours mismatch
    MANUAL_ADJUSTMENT = "manual_adjustment"  # Manual hours adjustment


class StaffAttendanceSheet(Base):
    """
    Bulk Attendance Marking for HR/EA/VGK
    DC: Single source of truth for HR-marked attendance
    WVV: One record per employee per date
    """
    __tablename__ = 'staff_attendance_sheets'
    
    id = Column(Integer, primary_key=True, index=True)
    
    # DC Protocol (Task #53, May 2026): Company scope for the DAR.
    # Backfilled at startup from staff_employees.base_company_id. Nullable for legacy
    # rows that pre-date company tagging — the DAR query treats NULL as "not in scope".
    company_id = Column(Integer, ForeignKey('associated_companies.id', ondelete='SET NULL'), nullable=True, index=True)
    
    # Basic Info
    date = Column(Date, nullable=False, index=True)
    employee_id = Column(Integer, ForeignKey('staff_employees.id', ondelete='CASCADE'), nullable=False, index=True)
    
    # HR Marking (Initial)
    attendance_status = Column(SQLEnum(AttendanceStatus), nullable=False)
    marked_hours = Column(Numeric(5, 2), nullable=False, default=0)  # 0, 4 (half), 8 (full), based on status
    marked_by_id = Column(Integer, ForeignKey('staff_employees.id', ondelete='SET NULL'), nullable=True)
    marked_at = Column(DateTime, default=get_indian_time, nullable=False)
    
    # EA/VGK Approval (Final)
    approved_hours = Column(Numeric(5, 2), nullable=True)  # Can differ from marked (e.g., 7 if late)
    approved_by_id = Column(Integer, ForeignKey('staff_employees.id', ondelete='SET NULL'), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    approval_status = Column(SQLEnum(ApprovalStatus), default=ApprovalStatus.PENDING, nullable=False)
    approval_reason = Column(Text, nullable=True)  # Why approved different from marked
    
    # Reconciliation (Auto-calculated)
    employee_actual_hours = Column(Numeric(5, 2), nullable=True)  # From employee timesheet (breaks excluded)
    reconciliation_status = Column(SQLEnum(ReconciliationStatus), nullable=False)
    reconciliation_notes = Column(Text, nullable=True)
    
    # Net Days Calculation (For Display)
    net_days = Column(Numeric(4, 2), default=0, nullable=False)  # approved_hours / 8
    
    # DC Protocol (Jan 01, 2026): Exception Bypass Fields for EA/VGK
    exception_bypass = Column(Boolean, default=False, nullable=False)  # False=no bypass, True=bypassed
    exception_reason = Column(Text, nullable=True)  # Mandatory reason when bypass=1
    exception_approved_at = Column(DateTime, nullable=True)
    exception_approved_by_id = Column(Integer, ForeignKey('staff_employees.id', ondelete='SET NULL'), nullable=True)
    
    # Metadata
    notes = Column(Text, nullable=True)  # HR notes
    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time)
    
    __table_args__ = (
        UniqueConstraint('date', 'employee_id', name='uq_attendance_sheet_date_emp'),
        Index('idx_attendance_sheet_date', 'date'),
        Index('idx_attendance_sheet_employee', 'employee_id'),
        Index('idx_attendance_sheet_approval', 'approval_status'),
        CheckConstraint(
            "marked_hours >= 0 AND marked_hours <= 24",
            name='check_marked_hours_range'
        ),
        CheckConstraint(
            "approved_hours IS NULL OR (approved_hours >= 0 AND approved_hours <= 24)",
            name='check_approved_hours_range'
        ),
    )
    
    # Relationships
    employee = relationship("StaffEmployee", foreign_keys=[employee_id])
    marked_by = relationship("StaffEmployee", foreign_keys=[marked_by_id])
    approved_by = relationship("StaffEmployee", foreign_keys=[approved_by_id])
    exception_approved_by = relationship("StaffEmployee", foreign_keys=[exception_approved_by_id])
    audit_logs = relationship("StaffAttendanceSheetAudit", back_populates="attendance_sheet", cascade="all, delete-orphan")


class StaffAttendanceSheetAudit(Base):
    """
    Immutable audit trail for attendance sheet changes
    DC Protocol: All changes logged with who/what/when
    WVV: Validates every change
    """
    __tablename__ = 'staff_attendance_sheet_audits'
    
    id = Column(Integer, primary_key=True, index=True)
    
    attendance_sheet_id = Column(Integer, ForeignKey('staff_attendance_sheets.id', ondelete='CASCADE'), nullable=False, index=True)
    
    # Who made the change
    changed_by_id = Column(Integer, ForeignKey('staff_employees.id', ondelete='SET NULL'), nullable=True)
    changed_by_role = Column(String(32), nullable=False)  # hr, ea, vgk4u, etc
    
    # What changed
    change_type = Column(String(32), nullable=False)  # marked, approved, rejected, updated
    field_changed = Column(String(100), nullable=True)  # which field changed
    old_value = Column(JSONB, nullable=True)
    new_value = Column(JSONB, nullable=True)
    
    # Why it changed
    reason = Column(Text, nullable=True)
    
    # When
    changed_at = Column(DateTime, default=get_indian_time, nullable=False)
    
    __table_args__ = (
        Index('idx_audit_attendance_sheet', 'attendance_sheet_id'),
        Index('idx_audit_changed_by', 'changed_by_id'),
        Index('idx_audit_changed_at', 'changed_at'),
    )
    
    attendance_sheet = relationship("StaffAttendanceSheet", back_populates="audit_logs")
    changed_by = relationship("StaffEmployee", foreign_keys=[changed_by_id])


class StaffAttendanceException(Base):
    """
    DC Protocol (Jan 01, 2026): Exception Approval Records
    Tracks all EA/VGK bypass approvals for audit trail
    WVV: Immutable record of exception grants
    """
    __tablename__ = 'staff_attendance_exceptions'
    
    id = Column(Integer, primary_key=True, index=True)
    
    # DC Protocol: Company-wise segregation
    company_id = Column(Integer, ForeignKey('associated_companies.id', ondelete='CASCADE'), nullable=False, index=True)
    
    # Link to attendance sheet
    attendance_sheet_id = Column(Integer, ForeignKey('staff_attendance_sheets.id', ondelete='CASCADE'), nullable=False, index=True)
    
    # Employee info (denormalized for quick queries)
    employee_id = Column(Integer, ForeignKey('staff_employees.id', ondelete='CASCADE'), nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)
    
    # Exception details
    bypass_type = Column(SQLEnum(ExceptionBypassType), nullable=False)
    exception_reason = Column(Text, nullable=False)  # Mandatory reason
    
    # Approver info
    approver_id = Column(Integer, ForeignKey('staff_employees.id', ondelete='SET NULL'), nullable=True, index=True)
    approver_role = Column(String(32), nullable=False)  # ea, vgk4u
    
    # Reconciliation snapshot for audit (stores original state)
    reconciliation_snapshot = Column(JSONB, nullable=True)
    # Example: { "marked_hours": 8, "timesheet_hours": null, "reconciliation_status": "no_entry" }
    
    # Approved hours at time of exception
    approved_hours = Column(Numeric(5, 2), nullable=False)
    
    # Timestamp
    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    
    __table_args__ = (
        Index('idx_exception_company', 'company_id'),
        Index('idx_exception_employee', 'employee_id'),
        Index('idx_exception_date', 'date'),
        Index('idx_exception_approver', 'approver_id'),
        Index('idx_exception_created', 'created_at'),
    )
    
    # Relationships
    company = relationship("AssociatedCompany", foreign_keys=[company_id])
    attendance_sheet = relationship("StaffAttendanceSheet", foreign_keys=[attendance_sheet_id])
    employee = relationship("StaffEmployee", foreign_keys=[employee_id])
    approver = relationship("StaffEmployee", foreign_keys=[approver_id])


# ============================================================================
# LEAVE MANAGEMENT SYSTEM (Jan 2026)
# DC Protocol Compliant - Company-wise segregation
# WVV Protocol Compliant - Role-based visibility, immutable audit trail
# ============================================================================

class LeaveRequestStatus(str, enum.Enum):
    """Leave request workflow status"""
    DRAFT = "draft"  # Saved but not submitted
    PENDING_MANAGER = "pending_manager"  # Awaiting manager approval
    PENDING_HR = "pending_hr"  # Manager approved, awaiting HR
    APPROVED = "approved"  # HR approved, leave granted
    REJECTED_MANAGER = "rejected_manager"  # Manager rejected
    REJECTED_HR = "rejected_hr"  # HR rejected
    CANCELLED = "cancelled"  # Employee cancelled


class HalfDayType(str, enum.Enum):
    """Half day timing options"""
    FIRST_HALF = "first_half"  # Morning half
    SECOND_HALF = "second_half"  # Afternoon half


class StaffLeaveType(Base):
    """
    Master table for leave types
    DC Protocol: Company-specific leave policies possible
    """
    __tablename__ = 'staff_leave_types'
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Leave type identification
    code = Column(String(32), nullable=False, unique=True, index=True)  # casual_leave, sick_leave, etc.
    name = Column(String(100), nullable=False)  # Display name
    description = Column(Text, nullable=True)
    
    # Accrual rules
    monthly_accrual = Column(Numeric(4, 2), default=0, nullable=False)  # Days accrued per month
    monthly_accrual_partial = Column(Numeric(4, 2), default=0, nullable=False)  # For joining after 10th
    is_accumulative = Column(Boolean, default=True, nullable=False)  # Carries forward to next month
    max_accumulation = Column(Numeric(5, 2), nullable=True)  # Max days that can accumulate (null = unlimited)
    
    # Leave rules
    requires_document = Column(Boolean, default=False, nullable=False)  # Medical certificate for sick leave
    allow_half_day = Column(Boolean, default=True, nullable=False)
    max_consecutive_days = Column(Integer, nullable=True)  # Max days in single request
    min_advance_days = Column(Integer, default=0, nullable=False)  # Min days before leave starts
    
    # Attendance status mapping
    attendance_status = Column(SQLEnum(AttendanceStatus), nullable=False)  # Maps to attendance sheet status
    
    # Display order
    display_order = Column(Integer, default=0, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Metadata
    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time)
    
    __table_args__ = (
        Index('idx_leave_type_code', 'code'),
        Index('idx_leave_type_active', 'is_active'),
    )


class StaffLeaveBalance(Base):
    """
    Per-employee leave balance tracking (yearly)
    DC Protocol: Company-wise segregation
    WVV Protocol: Balance calculated from accrual - usage
    """
    __tablename__ = 'staff_leave_balances'
    
    id = Column(Integer, primary_key=True, index=True)
    
    # DC Protocol: Company segregation
    company_id = Column(Integer, ForeignKey('associated_companies.id', ondelete='CASCADE'), nullable=False, index=True)
    
    # Employee and leave type
    employee_id = Column(Integer, ForeignKey('staff_employees.id', ondelete='CASCADE'), nullable=False, index=True)
    leave_type_id = Column(Integer, ForeignKey('staff_leave_types.id', ondelete='CASCADE'), nullable=False, index=True)
    
    # Year tracking
    year = Column(Integer, nullable=False, index=True)  # e.g., 2026
    
    # Balance components
    opening_balance = Column(Numeric(5, 2), default=0, nullable=False)  # Carried from previous year
    accrued = Column(Numeric(5, 2), default=0, nullable=False)  # Total accrued this year
    used = Column(Numeric(5, 2), default=0, nullable=False)  # Total used this year
    
    # Calculated balance (opening + accrued - used)
    balance = Column(Numeric(5, 2), default=0, nullable=False)
    
    # Last accrual tracking
    last_accrual_month = Column(Integer, nullable=True)  # 1-12, last month accrued
    last_accrual_date = Column(DateTime, nullable=True)
    
    # Metadata
    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time)
    
    __table_args__ = (
        UniqueConstraint('employee_id', 'leave_type_id', 'year', name='uq_leave_balance_emp_type_year'),
        Index('idx_leave_balance_company', 'company_id'),
        Index('idx_leave_balance_employee', 'employee_id'),
        Index('idx_leave_balance_year', 'year'),
    )
    
    # Relationships
    company = relationship("AssociatedCompany", foreign_keys=[company_id])
    employee = relationship("StaffEmployee", foreign_keys=[employee_id])
    leave_type = relationship("StaffLeaveType", foreign_keys=[leave_type_id])


class StaffLeaveRequest(Base):
    """
    Main leave request record
    DC Protocol: Company-wise segregation
    WVV Protocol: Manager sees team, HR sees all
    """
    __tablename__ = 'staff_leave_requests'
    
    id = Column(Integer, primary_key=True, index=True)
    
    # DC Protocol: Company segregation
    company_id = Column(Integer, ForeignKey('associated_companies.id', ondelete='CASCADE'), nullable=False, index=True)
    
    # Employee details
    employee_id = Column(Integer, ForeignKey('staff_employees.id', ondelete='CASCADE'), nullable=False, index=True)
    
    # Leave details
    leave_type_id = Column(Integer, ForeignKey('staff_leave_types.id', ondelete='CASCADE'), nullable=False, index=True)
    start_date = Column(Date, nullable=False, index=True)
    end_date = Column(Date, nullable=False, index=True)
    
    # Half day options
    is_half_day = Column(Boolean, default=False, nullable=False)
    half_day_type = Column(SQLEnum(HalfDayType), nullable=True)  # Only if is_half_day=True
    
    # Total days calculation
    total_days = Column(Numeric(4, 2), nullable=False)  # 0.5 for half day, integer for full days
    
    # Request details
    reason = Column(Text, nullable=False)
    
    # Workflow status
    status = Column(SQLEnum(LeaveRequestStatus), default=LeaveRequestStatus.PENDING_MANAGER, nullable=False, index=True)
    
    # Manager approval
    manager_id = Column(Integer, ForeignKey('staff_employees.id', ondelete='SET NULL'), nullable=True, index=True)
    manager_decision_at = Column(DateTime, nullable=True)
    manager_comments = Column(Text, nullable=True)
    
    # HR approval
    hr_id = Column(Integer, ForeignKey('staff_employees.id', ondelete='SET NULL'), nullable=True, index=True)
    hr_decision_at = Column(DateTime, nullable=True)
    hr_comments = Column(Text, nullable=True)
    
    # Conflict handling
    has_attendance_conflict = Column(Boolean, default=False, nullable=False)
    conflict_resolution = Column(String(32), nullable=True)  # 'skip' or 'replace'
    conflicting_dates = Column(JSONB, nullable=True)  # Array of dates with existing attendance
    
    # Loss of Pay indicator (when balance is 0)
    is_lop = Column(Boolean, default=False, nullable=False)  # True if marked as Loss of Pay due to 0 balance
    
    # Metadata
    submitted_at = Column(DateTime, default=get_indian_time, nullable=False)
    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time)
    
    __table_args__ = (
        Index('idx_leave_request_company', 'company_id'),
        Index('idx_leave_request_employee', 'employee_id'),
        Index('idx_leave_request_status', 'status'),
        Index('idx_leave_request_dates', 'start_date', 'end_date'),
        Index('idx_leave_request_manager', 'manager_id'),
        CheckConstraint('end_date >= start_date', name='check_leave_dates_valid'),
    )
    
    # Relationships
    company = relationship("AssociatedCompany", foreign_keys=[company_id])
    employee = relationship("StaffEmployee", foreign_keys=[employee_id])
    leave_type = relationship("StaffLeaveType", foreign_keys=[leave_type_id])
    manager = relationship("StaffEmployee", foreign_keys=[manager_id])
    hr_approver = relationship("StaffEmployee", foreign_keys=[hr_id])


class StaffLeaveRequestDay(Base):
    """
    Per-day breakdown for multi-day leave requests
    Links to attendance sheet after HR approval
    """
    __tablename__ = 'staff_leave_request_days'
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Link to main request
    leave_request_id = Column(Integer, ForeignKey('staff_leave_requests.id', ondelete='CASCADE'), nullable=False, index=True)
    
    # Day details
    date = Column(Date, nullable=False, index=True)
    is_half_day = Column(Boolean, default=False, nullable=False)
    half_day_type = Column(SQLEnum(HalfDayType), nullable=True)
    day_value = Column(Numeric(3, 2), nullable=False)  # 1.0 or 0.5
    
    # Attendance sheet link (populated after HR approval)
    attendance_sheet_id = Column(Integer, ForeignKey('staff_attendance_sheets.id', ondelete='SET NULL'), nullable=True, index=True)
    
    # Status tracking
    is_processed = Column(Boolean, default=False, nullable=False)  # True after marked in attendance
    processed_at = Column(DateTime, nullable=True)
    
    # Conflict info
    had_existing_attendance = Column(Boolean, default=False, nullable=False)
    previous_status = Column(String(32), nullable=True)  # What was there before (if replaced)
    
    __table_args__ = (
        UniqueConstraint('leave_request_id', 'date', name='uq_leave_request_day'),
        Index('idx_leave_day_request', 'leave_request_id'),
        Index('idx_leave_day_date', 'date'),
    )
    
    # Relationships
    leave_request = relationship("StaffLeaveRequest", foreign_keys=[leave_request_id], backref="days")
    attendance_sheet = relationship("StaffAttendanceSheet", foreign_keys=[attendance_sheet_id])


class StaffLeaveApproval(Base):
    """
    Immutable audit trail for leave approvals
    WVV Protocol: Every approval/rejection logged
    """
    __tablename__ = 'staff_leave_approvals'
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Link to request
    leave_request_id = Column(Integer, ForeignKey('staff_leave_requests.id', ondelete='CASCADE'), nullable=False, index=True)
    
    # Approver details
    approver_id = Column(Integer, ForeignKey('staff_employees.id', ondelete='SET NULL'), nullable=False, index=True)
    approver_role = Column(String(32), nullable=False)  # 'manager', 'hr', 'ea', 'vgk4u'
    
    # Decision
    action = Column(String(32), nullable=False)  # 'approved', 'rejected', 'cancelled'
    previous_status = Column(SQLEnum(LeaveRequestStatus), nullable=False)  # Status before this action
    new_status = Column(SQLEnum(LeaveRequestStatus), nullable=False)  # Status after this action
    
    # Comments
    comments = Column(Text, nullable=True)
    
    # Timestamp (immutable)
    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    
    __table_args__ = (
        Index('idx_leave_approval_request', 'leave_request_id'),
        Index('idx_leave_approval_approver', 'approver_id'),
        Index('idx_leave_approval_created', 'created_at'),
    )
    
    # Relationships
    leave_request = relationship("StaffLeaveRequest", foreign_keys=[leave_request_id], backref="approvals")
    approver = relationship("StaffEmployee", foreign_keys=[approver_id])
