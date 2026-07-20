"""
System Log Models
Tracks all system operations: scheduler runs, data changes, admin actions
"""

from sqlalchemy import Column, Integer, String, DateTime, Text, JSON, Enum as SQLEnum
from sqlalchemy.orm import relationship
from app.models.base import BaseModel, get_indian_time
import enum

class LogType(str, enum.Enum):
    SCHEDULER = "Scheduler"
    DATA_CHANGE = "Data Change"
    ADMIN_ACTION = "Admin Action"
    SYSTEM_EVENT = "System Event"

class LogStatus(str, enum.Enum):
    SUCCESS = "Success"
    FAILED = "Failed"
    PARTIAL = "Partial"
    RUNNING = "Running"

class SystemLog(BaseModel):
    """
    Comprehensive system log tracking
    Records scheduler runs, data changes, and admin actions
    """
    __tablename__ = 'system_log'
    
    id = Column(Integer, primary_key=True)
    log_type = Column(SQLEnum(LogType), nullable=False, index=True)
    log_category = Column(String(100), nullable=False, index=True)  # e.g., "Income Scheduler", "User Update"
    status = Column(SQLEnum(LogStatus), nullable=False, default=LogStatus.RUNNING)
    
    # Execution details
    started_at = Column(DateTime, nullable=False, default=get_indian_time)
    completed_at = Column(DateTime, nullable=True)
    
    # Actor (who/what triggered this)
    actor_id = Column(String(12), nullable=True)  # User ID or "SYSTEM"
    actor_role = Column(String(50), nullable=True)
    
    # Operation details
    operation_name = Column(String(200), nullable=False)
    operation_description = Column(Text, nullable=True)
    
    # Results
    records_affected = Column(Integer, default=0)
    records_success = Column(Integer, default=0)
    records_failed = Column(Integer, default=0)
    
    # Additional data (JSON format)
    log_metadata = Column(JSON, nullable=True)  # Store detailed info, error messages, etc.
    
    # Error tracking
    error_message = Column(Text, nullable=True)
    error_details = Column(JSON, nullable=True)
    
    def __repr__(self):
        return f'<SystemLog {self.id} - {self.log_category}: {self.operation_name}>'
    
    @property
    def duration_seconds(self):
        """Calculate duration in seconds"""
        if self.completed_at and self.started_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None
    
    @property
    def success_rate(self):
        """Calculate success rate percentage"""
        if self.records_affected > 0:
            return (self.records_success / self.records_affected) * 100
        return 0.0


class SchedulerLog(BaseModel):
    """
    Simple scheduler execution tracking
    Shows whether income triggered and completion status
    """
    __tablename__ = 'scheduler_log'
    
    id = Column(Integer, primary_key=True)
    job_id = Column(String(100), nullable=False, index=True)
    job_name = Column(String(200), nullable=False)
    
    # Execution time
    scheduled_date = Column(DateTime, nullable=False, index=True)
    triggered_at = Column(DateTime, nullable=False, default=get_indian_time)
    completed_at = Column(DateTime, nullable=True)
    
    # Simple status tracking
    income_triggered = Column(String(100), default="Yes")
    direct_referral_status = Column(String(100), default="Pending")
    matching_status = Column(String(100), default="Pending")
    ved_income_status = Column(String(100), default="Pending")
    awards_status = Column(String(100), default="Pending")
    guru_dakshina_status = Column(String(100), default="Pending")
    field_allowance_status = Column(String(100), default="Pending")
    bonanza_status = Column(String(100), default="Pending")
    wallet_sync_status = Column(String(100), default="Pending")
    withdrawal_status = Column(String(100), default="Pending")
    
    # Simple counts
    total_incomes_created = Column(Integer, default=0)
    total_users_affected = Column(Integer, default=0)
    
    # Overall status
    overall_status = Column(String(100), default="Running")
    error_message = Column(Text, nullable=True)
    
    def __repr__(self):
        return f'<SchedulerLog {self.id} - {self.scheduled_date.date()}>'


class DataChangeLog(BaseModel):
    """
    Track all data modifications
    Audit trail for administrative changes
    """
    __tablename__ = 'data_change_log'
    
    id = Column(Integer, primary_key=True)
    
    # What changed
    table_name = Column(String(100), nullable=False, index=True)
    record_id = Column(String(50), nullable=False, index=True)
    operation = Column(String(20), nullable=False)  # INSERT, UPDATE, DELETE
    
    # Who changed it
    changed_by_id = Column(String(12), nullable=False)
    changed_by_role = Column(String(50), nullable=False)
    changed_at = Column(DateTime, nullable=False, default=get_indian_time, index=True)
    
    # What was changed
    field_name = Column(String(100), nullable=True)
    old_value = Column(Text, nullable=True)
    new_value = Column(Text, nullable=True)
    
    # Context
    change_reason = Column(Text, nullable=True)
    change_context = Column(JSON, nullable=True)  # Additional context data
    
    # Link to system log
    system_log_id = Column(Integer, nullable=True)
    
    def __repr__(self):
        return f'<DataChangeLog {self.id} - {self.operation} on {self.table_name}.{self.record_id}>'
