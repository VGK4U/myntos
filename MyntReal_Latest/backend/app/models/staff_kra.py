"""
Staff KRA (Key Responsibility Areas) Performance Management System
DC Protocol Compliant - Single source of truth for all KRA data

Tables:
- staff_kra_templates: Master KRA definitions with approval workflow
- staff_kra_assignments: Links staff to KRAs with SPOC and Manager tracking
- staff_kra_daily_instances: Daily task instances (auto-generated)
- staff_kra_performance_summary: Pre-calculated performance metrics
- staff_kra_audit_log: Immutable audit trail

Flow:
1. KRA LIST: Key Leadership creates templates → VGK4U approves
2. EMPLOYEE ADDITION: Staff members exist in system
3. KRA ASSIGNMENT: Assign approved KRAs to employees with SPOC/Manager
4. PERFORMANCE TRACKING: Monitor daily completion with dynamic date filters

Created: Nov 26, 2025
DC Protocol: Write-Verify-Validate at all levels
"""

from sqlalchemy import (
    Column, Integer, String, DateTime, Date, Boolean, Text, Time,
    ForeignKey, CheckConstraint, Index, Numeric, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from datetime import datetime
import pytz

from app.models.base import Base


def get_indian_time_aware():
    """
    Get current time in Indian timezone (IST) - timezone-aware
    For TIMESTAMPTZ columns (Phase 1 DC-hardening requirement)
    """
    ist = pytz.timezone('Asia/Kolkata')
    return datetime.now(ist)  # Returns timezone-aware datetime


class StaffKRATemplate(Base):
    """
    Master KRA Definitions with Approval Workflow
    DC: Single source of truth for KRA templates
    WVV: All fields validated before insert/update
    
    Approval Flow: draft → pending_approval → approved/rejected (VGK4U only)
    """
    __tablename__ = 'staff_kra_templates'
    
    id = Column(Integer, primary_key=True, index=True)
    kra_code = Column(String(32), unique=True, nullable=False, index=True)
    title = Column(String(256), nullable=False)
    description = Column(Text, nullable=True)
    
    # Applicability
    applicable_to_role = Column(String(64), nullable=True, index=True)
    applicable_to_designation = Column(String(128), nullable=True)
    
    # Frequency Configuration
    frequency = Column(String(32), nullable=False, default='daily')
    frequency_config = Column(JSONB, nullable=True)
    
    estimated_time_minutes = Column(Integer, nullable=True)
    target_time = Column(Time, nullable=True)
    is_mandatory = Column(Boolean, nullable=False, default=True)
    
    # Approval Workflow - DC: FK to staff_employees for approval tracking
    approval_status = Column(String(32), nullable=False, default='draft', index=True)
    created_by_employee_id = Column(Integer, ForeignKey('staff_employees.id', ondelete='SET NULL'), nullable=False)
    approved_by_employee_id = Column(Integer, ForeignKey('staff_employees.id', ondelete='SET NULL'), nullable=True)
    approval_date = Column(DateTime(timezone=True), nullable=True)
    rejection_reason = Column(Text, nullable=True)
    
    # Status
    status = Column(String(32), nullable=False, default='active', index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=get_indian_time_aware)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=get_indian_time_aware, onupdate=get_indian_time_aware)
    
    # Relationships
    assignments = relationship("StaffKRAAssignment", back_populates="kra_template", cascade="all, delete-orphan", passive_deletes=True)
    daily_instances = relationship("StaffKRADailyInstance", back_populates="kra_template", cascade="all, delete-orphan", passive_deletes=True)


class StaffKRAAssignment(Base):
    """
    Links Staff Members to KRAs with SPOC and Manager Tracking
    DC: Single source of truth for KRA assignments - All employee_ids are Integer FKs
    Prevents overlapping assignments via trigger
    Fixed: Nov 28, 2025 - Changed employee_id fields from String to Integer FK (DC Protocol)
    """
    __tablename__ = 'staff_kra_assignments'
    
    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey('staff_employees.id', ondelete='CASCADE'), nullable=False, index=True)
    kra_template_id = Column(Integer, ForeignKey('staff_kra_templates.id', ondelete='CASCADE'), nullable=False, index=True)
    
    # Assignment Metadata - DC: All linked to staff_employees via FK
    primary_spoc_employee_id = Column(Integer, ForeignKey('staff_employees.id', ondelete='SET NULL'), nullable=False, index=True)
    reporting_manager_id = Column(Integer, ForeignKey('staff_employees.id', ondelete='SET NULL'), nullable=True, index=True)
    assigned_by_employee_id = Column(Integer, ForeignKey('staff_employees.id', ondelete='SET NULL'), nullable=False)
    
    assigned_date = Column(Date, nullable=False)
    effective_from = Column(Date, nullable=False, index=True)
    effective_until = Column(Date, nullable=True, index=True)
    
    status = Column(String(32), nullable=False, default='active', index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=get_indian_time_aware)
    
    # Table constraints
    __table_args__ = (
        UniqueConstraint('employee_id', 'kra_template_id', 'effective_from', name='uq_employee_kra_effective'),
    )
    
    # Relationships
    kra_template = relationship("StaffKRATemplate", back_populates="assignments")
    daily_instances = relationship("StaffKRADailyInstance", back_populates="assignment", cascade="all, delete-orphan", passive_deletes=True)


class StaffKRADailyInstance(Base):
    """
    Daily KRA Task Instances
    DC: Auto-generated by scheduler based on frequency
    Single source of truth for daily task completion
    Fixed: Nov 28, 2025 - Changed employee_id from String to Integer FK (DC Protocol)
    """
    __tablename__ = 'staff_kra_daily_instances'
    
    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey('staff_employees.id', ondelete='CASCADE'), nullable=False, index=True)
    kra_assignment_id = Column(Integer, ForeignKey('staff_kra_assignments.id', ondelete='CASCADE'), nullable=False, index=True)
    kra_template_id = Column(Integer, ForeignKey('staff_kra_templates.id', ondelete='CASCADE'), nullable=False, index=True)
    
    instance_date = Column(Date, nullable=False, index=True)
    due_date = Column(Date, nullable=True, index=True)
    completion_status = Column(String(32), nullable=False, default='pending', index=True)
    completion_percentage = Column(Integer, nullable=False, default=0)
    time_spent_minutes = Column(Integer, nullable=False, default=0)
    time_source = Column(String(32), nullable=True)
    staff_notes = Column(Text, nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    self_rating = Column(Integer, nullable=True)
    self_remarks = Column(Text, nullable=True)
    submitted_at = Column(DateTime(timezone=True), nullable=True)
    
    # Manager Review System - DC: FK to staff_employees
    manager_rating = Column(Integer, nullable=True)
    manager_remarks = Column(Text, nullable=True)
    manager_review_status = Column(String(32), nullable=False, default='pending_review', index=True)
    manager_reviewed_by_employee_id = Column(Integer, ForeignKey('staff_employees.id', ondelete='SET NULL'), nullable=True, index=True)
    manager_review_date = Column(DateTime(timezone=True), nullable=True)
    manager_edit_notes = Column(Text, nullable=True)
    rejection_reason = Column(Text, nullable=True)
    original_values = Column(JSONB, nullable=True)
    
    created_at = Column(DateTime(timezone=True), nullable=False, default=get_indian_time_aware)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=get_indian_time_aware, onupdate=get_indian_time_aware)
    
    # Table constraints
    __table_args__ = (
        UniqueConstraint('employee_id', 'kra_template_id', 'instance_date', name='uq_employee_kra_date'),
        CheckConstraint('completion_percentage >= 0 AND completion_percentage <= 100', name='check_completion_pct'),
        CheckConstraint("completion_status IN ('pending', 'in_progress', 'completed', 'partial', 'skipped', 'na')", name='check_completion_status'),
    )
    
    # Relationships
    assignment = relationship("StaffKRAAssignment", back_populates="daily_instances")
    kra_template = relationship("StaffKRATemplate", back_populates="daily_instances")
    employee = relationship("StaffEmployee", foreign_keys=[employee_id])
    manager_reviewer = relationship("StaffEmployee", foreign_keys=[manager_reviewed_by_employee_id])


class StaffKRAPerformanceSummary(Base):
    """
    Pre-calculated Performance Metrics
    DC: Single source for aggregated performance data
    Dynamic filters: daily, weekly, monthly based on date range
    Fixed: Dec 2, 2025 - Changed employee_id from String(32) to Integer FK (DC Protocol)
    """
    __tablename__ = 'staff_kra_performance_summary'
    
    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=False, index=True)
    summary_period = Column(String(32), nullable=False, index=True)
    period_start_date = Column(Date, nullable=False, index=True)
    period_end_date = Column(Date, nullable=False, index=True)
    
    total_kras_assigned = Column(Integer, nullable=False, default=0)
    total_kras_completed = Column(Integer, nullable=False, default=0)
    total_kras_partial = Column(Integer, nullable=False, default=0)
    total_kras_pending = Column(Integer, nullable=False, default=0)
    
    achievement_percentage = Column(Numeric(5, 2), nullable=False, default=0.00)
    total_time_spent_minutes = Column(Integer, nullable=False, default=0)
    total_work_time_minutes = Column(Integer, nullable=False, default=0)
    time_utilization_percentage = Column(Numeric(5, 2), nullable=False, default=0.00)
    performance_score = Column(Numeric(5, 2), nullable=False, default=0.00)
    
    created_at = Column(DateTime(timezone=True), nullable=False, default=get_indian_time_aware)
    
    # Table constraints
    __table_args__ = (
        UniqueConstraint('employee_id', 'summary_period', 'period_start_date', name='uq_employee_period_start'),
        CheckConstraint('period_start_date <= period_end_date', name='check_period_dates_order'),
    )


class StaffConfigurableStatus(Base):
    """
    System-Wide Configurable Statuses for KRA and Task Completion
    DC: Admin-configurable status values with performance impact flags
    """
    __tablename__ = 'staff_configurable_statuses'
    
    id = Column(Integer, primary_key=True, index=True)
    category = Column(String(32), nullable=False, index=True)
    status_code = Column(String(32), nullable=False)
    status_label = Column(String(100), nullable=False)
    status_color = Column(String(20), nullable=True)
    counts_for_performance = Column(Boolean, nullable=False, default=True)
    is_system_default = Column(Boolean, nullable=False, default=False)
    display_order = Column(Integer, nullable=False, default=0)
    status = Column(String(20), nullable=False, default='active', index=True)
    
    created_by_employee_id = Column(Integer, ForeignKey('staff_employees.id', ondelete='SET NULL'), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=get_indian_time_aware)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=get_indian_time_aware, onupdate=get_indian_time_aware)
    
    # Table constraints
    __table_args__ = (
        UniqueConstraint('category', 'status_code', name='uq_category_status_code'),
    )


class StaffKRAAuditLog(Base):
    """
    Immutable Audit Trail for KRA System
    DC: All changes tracked, no updates/deletes allowed
    Trigger prevents modification
    Fixed: Dec 2, 2025 - Changed changed_by_employee_id from String(32) to Integer FK (DC Protocol)
    """
    __tablename__ = 'staff_kra_audit_log'
    
    id = Column(Integer, primary_key=True, index=True)
    record_type = Column(String(64), nullable=False, index=True)
    record_id = Column(Integer, nullable=False, index=True)
    action = Column(String(64), nullable=False)
    old_data = Column(JSONB, nullable=True)
    new_data = Column(JSONB, nullable=True)
    changed_by_employee_id = Column(Integer, ForeignKey('staff_employees.id', ondelete='SET NULL'), nullable=True, index=True)
    ip_address = Column(String(64), nullable=True)
    user_agent = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=get_indian_time_aware, index=True)
