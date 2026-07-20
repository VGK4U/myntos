"""
Staff Work Interval Models (DC Protocol Compliant)
Time-Activity linkage for KRA and Task status updates

Tables:
- staff_work_intervals: Time intervals linked to KRAs or Tasks
- staff_work_interval_log: Immutable audit trail

Key Features:
- Time intervals linked to specific KRAs or Tasks
- Bidirectional status updates
- Non-overlapping interval enforcement
- Manager approval workflow

Created: Nov 27, 2025
DC Protocol: Write-Verify-Validate at all levels
"""

from sqlalchemy import (
    Column, Integer, String, DateTime, Boolean, Text,
    ForeignKey, CheckConstraint, Index, Numeric
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from datetime import datetime
import pytz

from app.models.base import Base


def get_indian_time():
    """Get current time in Indian timezone (IST)"""
    ist = pytz.timezone('Asia/Kolkata')
    return datetime.now(ist).replace(tzinfo=None)


class StaffWorkInterval(Base):
    """
    Work Interval linked to KRA or Task
    DC: Time intervals with activity linkage
    WVV: Non-overlapping intervals per attendance
    """
    __tablename__ = 'staff_work_intervals'
    
    id = Column(Integer, primary_key=True, index=True)
    attendance_id = Column(Integer, ForeignKey('staff_attendance.id', ondelete='CASCADE'), nullable=False, index=True)
    employee_id = Column(Integer, ForeignKey('staff_employees.id', ondelete='CASCADE'), nullable=False, index=True)
    
    interval_start = Column(DateTime, nullable=False)
    interval_end = Column(DateTime, nullable=True)
    duration_minutes = Column(Integer, default=0)
    
    activity_type = Column(String(32), nullable=False, default='general')
    
    kra_entry_id = Column(Integer, nullable=True)
    task_id = Column(Integer, nullable=True)
    
    activity_title = Column(String(256), nullable=True)
    activity_notes = Column(Text, nullable=True)
    
    status = Column(String(32), default='in_progress')
    status_before = Column(String(32), nullable=True)
    status_after = Column(String(32), nullable=True)
    
    is_billable = Column(Boolean, default=True)
    
    approval_status = Column(String(32), default='pending')
    approved_by = Column(Integer, ForeignKey('staff_employees.id', ondelete='SET NULL'), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time)
    
    __table_args__ = (
        CheckConstraint(
            "activity_type IN ('kra', 'task', 'meeting', 'training', 'general', 'break', 'other')",
            name='staff_interval_activity_type_check'
        ),
        CheckConstraint(
            "status IN ('pending', 'in_progress', 'completed', 'paused', 'cancelled')",
            name='staff_interval_status_check'
        ),
        CheckConstraint(
            "approval_status IN ('pending', 'approved', 'rejected', 'auto_approved')",
            name='staff_interval_approval_check'
        ),
        Index('idx_work_interval_attendance', 'attendance_id'),
        Index('idx_work_interval_employee', 'employee_id'),
        Index('idx_work_interval_kra', 'kra_entry_id'),
        Index('idx_work_interval_task', 'task_id'),
        Index('idx_work_interval_type', 'activity_type'),
    )
    
    employee = relationship("StaffEmployee", foreign_keys=[employee_id])
    approver = relationship("StaffEmployee", foreign_keys=[approved_by])
    
    def calculate_duration(self):
        """Calculate interval duration in minutes"""
        if self.interval_start and self.interval_end:
            delta = self.interval_end - self.interval_start
            return int(delta.total_seconds() / 60)
        return 0
    
    def to_dict(self):
        return {
            "id": self.id,
            "attendance_id": self.attendance_id,
            "employee_id": self.employee_id,
            "employee_name": self.employee.full_name if self.employee else None,
            "interval_start": self.interval_start.isoformat() if self.interval_start else None,
            "interval_end": self.interval_end.isoformat() if self.interval_end else None,
            "interval_start_time": self.interval_start.strftime("%H:%M") if self.interval_start else None,
            "interval_end_time": self.interval_end.strftime("%H:%M") if self.interval_end else None,
            "duration_minutes": self.duration_minutes or self.calculate_duration(),
            "duration_hours": round((self.duration_minutes or 0) / 60, 2),
            "activity_type": self.activity_type,
            "activity_type_display": self.activity_type.upper() if self.activity_type else None,
            "kra_entry_id": self.kra_entry_id,
            "task_id": self.task_id,
            "activity_title": self.activity_title,
            "activity_notes": self.activity_notes,
            "status": self.status,
            "status_before": self.status_before,
            "status_after": self.status_after,
            "is_billable": self.is_billable,
            "approval_status": self.approval_status,
            "approved_by": self.approved_by,
            "approver_name": self.approver.full_name if self.approver else None,
            "approved_at": self.approved_at.isoformat() if self.approved_at else None,
            "is_active": self.interval_start is not None and self.interval_end is None,
            "is_complete": self.interval_start is not None and self.interval_end is not None,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class StaffWorkIntervalLog(Base):
    """
    Work Interval Activity Audit Trail (Immutable)
    DC: Complete history of all interval actions
    """
    __tablename__ = 'staff_work_interval_log'
    
    id = Column(Integer, primary_key=True, index=True)
    interval_id = Column(Integer, ForeignKey('staff_work_intervals.id', ondelete='CASCADE'), nullable=False, index=True)
    employee_id = Column(Integer, ForeignKey('staff_employees.id', ondelete='SET NULL'), nullable=True)
    
    action = Column(String(64), nullable=False, index=True)
    details = Column(JSONB, nullable=True)
    previous_value = Column(JSONB, nullable=True)
    new_value = Column(JSONB, nullable=True)
    
    ip_address = Column(String(64), nullable=True)
    device_info = Column(JSONB, nullable=True)
    
    created_at = Column(DateTime, default=get_indian_time, nullable=False, index=True)
    
    __table_args__ = (
        CheckConstraint(
            "action IN ('created', 'updated', 'status_changed', 'kra_linked', 'task_linked', 'approved', 'rejected', 'deleted')",
            name='staff_interval_log_action_check'
        ),
    )
    
    interval = relationship("StaffWorkInterval", foreign_keys=[interval_id])
    employee = relationship("StaffEmployee", foreign_keys=[employee_id])
    
    def to_dict(self):
        return {
            "id": self.id,
            "interval_id": self.interval_id,
            "employee_id": self.employee_id,
            "employee_name": self.employee.full_name if self.employee else "System",
            "action": self.action,
            "action_display": self.action.replace('_', ' ').title(),
            "details": self.details,
            "previous_value": self.previous_value,
            "new_value": self.new_value,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


def log_interval_activity(db, interval_id, employee_id, action, details=None,
                          previous_value=None, new_value=None, ip_address=None, device_info=None):
    """
    Helper function to create interval activity log entries
    DC: Ensures consistent audit logging across all interval operations
    """
    log = StaffWorkIntervalLog(
        interval_id=interval_id,
        employee_id=employee_id,
        action=action,
        details=details,
        previous_value=previous_value,
        new_value=new_value,
        ip_address=ip_address,
        device_info=device_info
    )
    db.add(log)
    return log
