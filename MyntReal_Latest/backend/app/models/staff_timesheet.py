"""
Staff Timesheet Entry Models (DC Protocol Compliant)
Single source of truth for manual time tracking entries

Tables:
- staff_timesheet_entries: Manual time entries linked to Task/KRA/Others
- staff_timesheet_approval_history: Approval/rejection audit trail

Key Features:
- Multiple entries per day allowed (different time slots)
- Auto-link to Tasks or KRAs
- Entry type: task / kra / others
- Total time validation (must not exceed daily working hours)
- Approval workflow: submitted → approved/rejected → resubmitted
- Complete audit trail (DC Protocol)

Created: Dec 01, 2025
DC Protocol: Write-Verify-Validate at all levels
WVV Protocol: All GPS and timestamp data validated
"""

from sqlalchemy import (
    Column, Integer, String, DateTime, Date, Time, Boolean, Text, 
    ForeignKey, CheckConstraint, Index, Numeric, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from datetime import datetime, time
import pytz
import uuid

from app.models.base import Base


def get_indian_time():
    """Get current time in Indian timezone (IST)"""
    ist = pytz.timezone('Asia/Kolkata')
    return datetime.now(ist).replace(tzinfo=None)


def get_indian_date():
    """Get current date in Indian timezone (IST)"""
    ist = pytz.timezone('Asia/Kolkata')
    return datetime.now(ist).date()


def generate_timesheet_audit_id():
    """Generate unique audit ID for DC Protocol tracking"""
    return f"TS-{datetime.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:8].upper()}"


def generate_entry_group_id():
    """
    Generate unique group ID for multi-lead entries (DC Protocol Jan 22, 2026)
    When multiple leads are selected, each entry shares the same group ID
    Time calculations use this to avoid double-counting
    """
    return f"EG-{datetime.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:8].upper()}"


class StaffTimesheetEntry(Base):
    """
    Manual Time Entry Record
    DC: Single source of truth for manual time tracking
    WVV: Multiple entries per day allowed (different time slots)
    
    Constraint: Total time in entries <= daily working hours from attendance
    """
    __tablename__ = 'staff_timesheet_entries'
    
    id = Column(Integer, primary_key=True, index=True)
    
    employee_id = Column(Integer, ForeignKey('staff_employees.id', ondelete='CASCADE'), nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)
    
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    duration_minutes = Column(Integer, nullable=False, default=0)
    
    # Break Time Tracking (DC: Exclude breaks from billable time)
    break_start_time = Column(Time, nullable=True)
    break_end_time = Column(Time, nullable=True)
    break_duration_minutes = Column(Integer, nullable=False, default=0)
    break_type = Column(String(20), nullable=True)  # lunch, tea, personal, other
    
    # Billable Time = duration_minutes - break_duration_minutes
    billable_minutes = Column(Integer, nullable=False, default=0)
    
    entry_type = Column(String(20), nullable=False, default='others')
    task_id = Column(Integer, ForeignKey('staff_tasks.id', ondelete='SET NULL'), nullable=True, index=True)
    kra_id = Column(Integer, ForeignKey('staff_kra_assignments.id', ondelete='SET NULL'), nullable=True, index=True)
    lead_id = Column(Integer, ForeignKey('crm_leads.id', ondelete='SET NULL'), nullable=True, index=True)
    journey_id = Column(Integer, ForeignKey('staff_journeys.id', ondelete='SET NULL'), nullable=True, index=True)
    
    comments = Column(Text, nullable=True)
    
    status = Column(String(32), nullable=False, default='submitted', index=True)
    
    approved_by = Column(Integer, ForeignKey('staff_employees.id', ondelete='SET NULL'), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    approved_minutes = Column(Integer, nullable=True)
    rejection_reason = Column(Text, nullable=True)
    
    is_locked = Column(Boolean, default=False)

    # DC Protocol (Mar 2026): Auto-entry source — 'kra' | 'day_plan' | None (manual)
    # Entries with auto_source cannot be edited or deleted by employee
    auto_source = Column(String(20), nullable=True, index=True)

    # DC Protocol (Jan 22, 2026): Multi-lead entry grouping
    # When multiple leads are selected, each gets its own entry with same entry_group_id
    # Time calculations use entry_group_id to avoid double-counting
    entry_group_id = Column(String(64), nullable=True, index=True)
    
    device_id = Column(String(255), nullable=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    audit_log_id = Column(String(64), nullable=True)
    
    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    created_by = Column(Integer, ForeignKey('staff_employees.id', ondelete='SET NULL'), nullable=False)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time)
    updated_by = Column(Integer, ForeignKey('staff_employees.id', ondelete='SET NULL'), nullable=True)
    
    edit_history = Column(JSONB, default=list)
    
    __table_args__ = (
        UniqueConstraint('employee_id', 'date', 'start_time', name='uq_employee_date_start_time'),
        Index('idx_timesheet_emp_date', 'employee_id', 'date'),
        Index('idx_timesheet_status', 'status'),
        Index('idx_timesheet_task', 'task_id'),
        Index('idx_timesheet_kra', 'kra_id'),
        Index('idx_timesheet_lead', 'lead_id'),
        Index('idx_timesheet_journey', 'journey_id'),
        CheckConstraint(
            "entry_type IN ('task', 'kra', 'lead', 'journey', 'others')",
            name='staff_timesheet_entry_type_check_v3'
        ),
        CheckConstraint(
            "status IN ('submitted', 'approved', 'rejected', 'resubmitted', 'pending_edit')",
            name='staff_timesheet_status_check'
        ),
        CheckConstraint(
            "end_time > start_time",
            name='staff_timesheet_time_order_check'
        ),
        CheckConstraint(
            "duration_minutes > 0",
            name='staff_timesheet_duration_positive_check'
        ),
    )
    
    def to_dict(self):
        """Convert to dictionary for API response"""
        return {
            "id": self.id,
            "employee_id": self.employee_id,
            "date": str(self.date) if self.date else None,
            "start_time": str(self.start_time) if self.start_time else None,
            "end_time": str(self.end_time) if self.end_time else None,
            "duration_minutes": self.duration_minutes,
            "break_start_time": str(self.break_start_time) if self.break_start_time else None,
            "break_end_time": str(self.break_end_time) if self.break_end_time else None,
            "break_duration_minutes": self.break_duration_minutes,
            "break_type": self.break_type,
            "billable_minutes": self.billable_minutes,
            "entry_type": self.entry_type,
            "task_id": self.task_id,
            "kra_id": self.kra_id,
            "lead_id": self.lead_id,
            "journey_id": self.journey_id,
            "comments": self.comments,
            "status": self.status,
            "approved_by": self.approved_by,
            "approved_at": self.approved_at.isoformat() if self.approved_at else None,
            "approved_minutes": self.approved_minutes,
            "rejection_reason": self.rejection_reason,
            "is_locked": self.is_locked,
            "auto_source": self.auto_source,
            "entry_group_id": self.entry_group_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "edit_history": self.edit_history or []
        }


class StaffTimesheetApprovalHistory(Base):
    """
    Approval History Record
    DC: Complete audit trail for all approval/rejection actions
    """
    __tablename__ = 'staff_timesheet_approval_history'
    
    id = Column(Integer, primary_key=True, index=True)
    
    timesheet_entry_id = Column(Integer, ForeignKey('staff_timesheet_entries.id', ondelete='CASCADE'), nullable=False, index=True)
    
    action = Column(String(32), nullable=False)
    action_by = Column(Integer, ForeignKey('staff_employees.id', ondelete='SET NULL'), nullable=False, index=True)
    action_at = Column(DateTime, default=get_indian_time, nullable=False)
    
    previous_status = Column(String(32), nullable=True)
    new_status = Column(String(32), nullable=False)
    
    comments = Column(Text, nullable=True)
    
    device_id = Column(String(255), nullable=True)
    ip_address = Column(String(45), nullable=True)
    
    __table_args__ = (
        Index('idx_approval_history_entry', 'timesheet_entry_id'),
        CheckConstraint(
            "action IN ('created', 'updated', 'submitted', 'approved', 'rejected', 'resubmitted', 'locked')",
            name='staff_timesheet_history_action_check'
        ),
    )
    
    def to_dict(self):
        """Convert to dictionary for API response"""
        return {
            "id": self.id,
            "timesheet_entry_id": self.timesheet_entry_id,
            "action": self.action,
            "action_by": self.action_by,
            "action_at": self.action_at.isoformat() if self.action_at else None,
            "previous_status": self.previous_status,
            "new_status": self.new_status,
            "comments": self.comments
        }


def log_timesheet_activity(db, entry_id: int, action: str, user_id: int, 
                           previous_status: str = None, new_status: str = None,
                           comments: str = None, device_id: str = None, 
                           ip_address: str = None):
    """
    Log timesheet approval/activity history
    DC Protocol: Complete audit trail for all actions
    """
    history = StaffTimesheetApprovalHistory(
        timesheet_entry_id=entry_id,
        action=action,
        action_by=user_id,
        previous_status=previous_status,
        new_status=new_status,
        comments=comments,
        device_id=device_id,
        ip_address=ip_address
    )
    db.add(history)
    return history


ATTENDANCE_RULES = {
    "absent": {"min_hours": 0, "max_hours": 2},
    "half_day": {"min_hours": 2, "max_hours": 6},
    "full_day": {"min_hours": 6, "max_hours": 8},
    "overtime": {"min_hours": 8, "max_hours": 24}
}


def compute_attendance_status(total_hours: float) -> dict:
    """
    Compute attendance status based on total hours worked
    
    Rules (Updated):
    - < 2 hrs: ABSENT
    - 2-6 hrs: HALF DAY
    - 6-8 hrs: FULL DAY
    - > 8 hrs: FULL DAY + OT (extra hours beyond 8)
    
    Returns dict with status, ot_hours, classification
    """
    if total_hours < 2:
        return {
            "status": "absent",
            "classification": "ABSENT",
            "ot_hours": 0,
            "effective_hours": 0
        }
    elif total_hours < 6:
        return {
            "status": "half_day",
            "classification": "HALF DAY",
            "ot_hours": 0,
            "effective_hours": total_hours
        }
    elif total_hours <= 8:
        return {
            "status": "full_day",
            "classification": "FULL DAY",
            "ot_hours": 0,
            "effective_hours": total_hours
        }
    else:
        ot_hours = total_hours - 8
        return {
            "status": "full_day_ot",
            "classification": "FULL DAY + OT",
            "ot_hours": round(ot_hours, 2),
            "effective_hours": 8,
            "total_hours": total_hours
        }
