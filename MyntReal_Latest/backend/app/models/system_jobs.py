"""
System Jobs Model (Release 1A Durable Queue Layer)
PostgreSQL FOR UPDATE SKIP LOCKED background job queue table.
"""

from sqlalchemy import Column, Integer, BigInteger, String, DateTime, Text, JSON, Index, ForeignKey
from datetime import datetime
from app.models.base import Base


class SystemJob(Base):
    """
    Durable System Job model for background processing.
    Supports atomic locking via SKIP LOCKED, lease timeouts, retries, and DLQ.
    """
    __tablename__ = 'system_jobs'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    company_id = Column(Integer, ForeignKey('associated_companies.id', ondelete='RESTRICT'), nullable=False, index=True)
    
    job_type = Column(String(50), nullable=False, index=True)  # WA_AUDIT_LOG, META_DAILY_INSIGHTS_SYNC, CAPI_DISPATCH, etc.
    payload = Column(JSON, nullable=False, default=dict)
    
    status = Column(String(20), nullable=False, default='QUEUED', index=True)  # QUEUED, PROCESSING, COMPLETED, FAILED_DLQ
    attempts = Column(Integer, nullable=False, default=0)
    max_attempts = Column(Integer, nullable=False, default=5)
    
    next_attempt_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    locked_by = Column(String(100), nullable=True)
    locked_until = Column(DateTime, nullable=True)
    
    idempotency_key = Column(String(150), unique=True, nullable=False, index=True)
    correlation_id = Column(String(100), nullable=True)
    error_log = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    processed_at = Column(DateTime, nullable=True)

    def __repr__(self):
        return f'<SystemJob id={self.id} type={self.job_type} status={self.status} attempts={self.attempts}>'
