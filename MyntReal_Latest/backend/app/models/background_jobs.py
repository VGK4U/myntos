"""
Background Jobs Model - Generic async job queue
DC Protocol: Complete audit trail for all background processing
WVV Protocol: Status tracking, retry management, error logging

Usage:
- Image compression
- Video processing
- PDF generation
- Email notifications
- Report generation
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Index, CheckConstraint, JSON
from sqlalchemy.orm import relationship
from app.core.database import Base
from datetime import datetime, timezone


def get_utc_time():
    """Get current UTC time"""
    return datetime.now(timezone.utc)


class BackgroundJob(Base):
    """
    Generic background job queue for APScheduler
    DC: Complete audit trail with employee attribution
    WVV: Lifecycle tracking with retry management
    """
    __tablename__ = 'background_jobs'
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Job Identification
    job_type = Column(String(50), nullable=False, index=True)  # 'image_compression', 'video_processing', etc.
    job_key = Column(String(100), nullable=False)  # Unique identifier (e.g., 'compress_attachment_123')
    
    # Job Data (DC: Store all parameters for replay)
    job_data = Column(JSON, nullable=False)  # All job parameters
    
    # Status Tracking (WVV: Lifecycle validation)
    status = Column(String(20), nullable=False, default='pending', index=True)
    attempts = Column(Integer, nullable=False, default=0)
    max_attempts = Column(Integer, nullable=False, default=3)
    
    # Results (DC: Audit trail)
    result = Column(JSON, nullable=True)  # Success result data
    error_message = Column(Text, nullable=True)  # User-friendly error
    error_traceback = Column(Text, nullable=True)  # Full stack trace
    
    # Timing (WVV: Performance monitoring)
    created_at = Column(DateTime(timezone=True), nullable=False, default=get_utc_time, index=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    processing_duration_ms = Column(Integer, nullable=True)
    
    # DC: Employee Attribution
    created_by = Column(Integer, ForeignKey('staff_employees.id', ondelete='SET NULL'), nullable=True)
    created_ip = Column(String(45), nullable=True)
    
    # Scheduling
    scheduled_for = Column(DateTime(timezone=True), nullable=True)
    priority = Column(Integer, nullable=False, default=5)  # 1=highest, 10=lowest
    
    # DC Protocol: APScheduler Enqueue Status (durable retry tracking)
    scheduler_status = Column(String(20), nullable=False, default='pending', index=True)
    # Values: 'pending' (job created, not yet scheduled), 'scheduled' (enqueued in APScheduler), 'failed' (enqueue failed, needs retry)
    
    # DC Protocol: Job Handler Metadata (enables dynamic retry for any job type)
    job_handler_module = Column(String(255), nullable=True)  # e.g., 'app.services.job_handlers.universal_compression_handler'
    job_handler_function = Column(String(100), nullable=True)  # e.g., 'process_universal_compression_job'
    scheduler_job_id = Column(String(150), nullable=True)  # Last APScheduler job ID (for audit trail)
    last_scheduler_attempt = Column(DateTime(timezone=True), nullable=True)  # Last retry timestamp
    
    # DC: Immutable Timestamps
    updated_at = Column(DateTime(timezone=True), nullable=False, default=get_utc_time, onupdate=get_utc_time)
    
    __table_args__ = (
        CheckConstraint("status IN ('pending', 'processing', 'completed', 'failed', 'retrying')", name='background_jobs_status_check'),
        CheckConstraint("scheduler_status IN ('pending', 'scheduled', 'failed')", name='background_jobs_scheduler_status_check'),
        CheckConstraint("priority >= 1 AND priority <= 10", name='background_jobs_priority_check'),
        CheckConstraint("attempts >= 0 AND attempts <= max_attempts", name='background_jobs_attempts_check'),
        Index('idx_background_jobs_pending', 'status', 'priority', 'created_at'),
        Index('idx_background_jobs_scheduler_retry', 'scheduler_status', 'created_at'),  # For retry dispatcher
    )
    
    creator = relationship("StaffEmployee", foreign_keys=[created_by])
    
    def to_dict(self):
        """Convert to dictionary (WVV: API response)"""
        return {
            "id": self.id,
            "job_type": self.job_type,
            "job_key": self.job_key,
            "status": self.status,
            "attempts": self.attempts,
            "max_attempts": self.max_attempts,
            "result": self.result,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "processing_duration_ms": self.processing_duration_ms,
            "created_by": self.created_by,
            "priority": self.priority
        }
    
    @property
    def is_terminal(self):
        """Check if job is in terminal state (completed or failed)"""
        return self.status in ('completed', 'failed')
    
    @property
    def can_retry(self):
        """Check if job can be retried"""
        return self.status == 'failed' and self.attempts < self.max_attempts
