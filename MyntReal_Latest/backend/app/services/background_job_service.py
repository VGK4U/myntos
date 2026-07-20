"""
Background Job Service - Enterprise-grade async job queue
DC Protocol: Complete audit trail, employee attribution, immutable logging
WVV Protocol: Status validation, retry management, error handling

Reusable for ALL background processing:
- Image compression
- Video processing  
- PDF generation
- Email notifications
- Report generation
"""

import json
import logging
import traceback
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.models.background_jobs import BackgroundJob

logger = logging.getLogger(__name__)


class BackgroundJobService:
    """
    Generic background job queue service
    WVV: All operations logged and validated
    DC: Complete audit trail maintained
    """
    
    # Job type constants (extend as needed)
    JOB_TYPE_IMAGE_COMPRESSION = 'image_compression'
    JOB_TYPE_VIDEO_PROCESSING = 'video_processing'
    JOB_TYPE_PDF_GENERATION = 'pdf_generation'
    JOB_TYPE_EMAIL_NOTIFICATION = 'email_notification'
    
    # Status constants
    STATUS_PENDING = 'pending'
    STATUS_PROCESSING = 'processing'
    STATUS_COMPLETED = 'completed'
    STATUS_FAILED = 'failed'
    STATUS_RETRYING = 'retrying'
    
    # Default configuration
    DEFAULT_MAX_ATTEMPTS = 3
    DEFAULT_PRIORITY = 5
    
    # DC Protocol: Job Handler Registry (maps job_type → handler metadata)
    # Used by Retry Dispatcher for generalized retry support
    # ONLY include job types with IMPLEMENTED handlers
    JOB_HANDLER_REGISTRY = {
        # Current Universal Upload System (implemented)
        'universal_media_compression': {
            'module': 'app.services.job_handlers.universal_compression_handler',
            'function': 'process_universal_compression_job'
        },
        # Legacy job types (exist in production database, use same handler)
        'image_compression': {
            'module': 'app.services.job_handlers.universal_compression_handler',
            'function': 'process_universal_compression_job'
        },
        'video_processing': {
            'module': 'app.services.job_handlers.universal_compression_handler',
            'function': 'process_universal_compression_job'
        }
        # Add new job types here ONLY after implementing their handlers
        # Example:
        # 'pdf_generation': {
        #     'module': 'app.services.job_handlers.pdf_handler',
        #     'function': 'process_pdf_generation_job'
        # }
    }
    
    @classmethod
    def enqueue_job(
        cls,
        db: Session,
        job_type: str,
        job_key: str,
        job_data: Dict[str, Any],
        created_by: Optional[int] = None,
        created_ip: Optional[str] = None,
        priority: int = DEFAULT_PRIORITY,
        scheduled_for: Optional[datetime] = None,
        max_attempts: int = DEFAULT_MAX_ATTEMPTS
    ) -> BackgroundJob:
        """
        Enqueue a new background job
        DC: Complete attribution and audit trail
        WVV: Validation and logging
        
        Args:
            db: Database session
            job_type: Type of job (use constants: JOB_TYPE_*)
            job_key: Unique job identifier (e.g., 'compress_attachment_123')
            job_data: Job parameters as dictionary
            created_by: Employee ID who created the job
            created_ip: IP address of creator
            priority: Job priority (1=highest, 10=lowest)
            scheduled_for: Delayed execution time (None = immediate)
            max_attempts: Maximum retry attempts
        
        Returns:
            BackgroundJob: Created job record
        
        Raises:
            ValueError: If job_key already exists in pending/processing state
        """
        logger.info(f"[JOB ENQUEUE] Type: {job_type}, Key: {job_key}, Priority: {priority}")
        
        # WVV: Check for duplicate job
        existing = db.query(BackgroundJob).filter(
            BackgroundJob.job_key == job_key,
            BackgroundJob.status.in_([cls.STATUS_PENDING, cls.STATUS_PROCESSING, cls.STATUS_RETRYING])
        ).first()
        
        if existing:
            logger.warning(f"[JOB DUPLICATE] Job {job_key} already exists with status {existing.status}")
            return existing  # Return existing job (idempotent)
        
        # DC Protocol: Auto-populate job handler metadata from registry
        handler_info = cls.JOB_HANDLER_REGISTRY.get(job_type)
        job_handler_module = handler_info['module'] if handler_info else None
        job_handler_function = handler_info['function'] if handler_info else None
        
        if not handler_info:
            logger.warning(
                f"[JOB ENQUEUE] Job type '{job_type}' not in handler registry. "
                f"Retry dispatcher will skip this job if scheduling fails."
            )
        
        # Create job record
        job = BackgroundJob(
            job_type=job_type,
            job_key=job_key,
            job_data=job_data,
            created_by=created_by,
            created_ip=created_ip,
            priority=priority,
            scheduled_for=scheduled_for,
            max_attempts=max_attempts,
            status=cls.STATUS_PENDING,
            attempts=0,
            # DC Protocol: Handler metadata for generalized retry
            job_handler_module=job_handler_module,
            job_handler_function=job_handler_function
        )
        
        db.add(job)
        db.flush()  # DC Protocol Fix: flush only — let caller's transaction commit atomically
        
        logger.info(
            f"[JOB CREATED] ID: {job.id}, Type: {job_type}, Key: {job_key}, "
            f"Handler: {job_handler_module}.{job_handler_function if job_handler_function else 'None'}"
        )
        
        return job
    
    @classmethod
    def get_next_pending_job(
        cls,
        db: Session,
        job_type: Optional[str] = None
    ) -> Optional[BackgroundJob]:
        """
        Get next pending job for processing
        WVV: Priority-based selection
        
        Args:
            db: Database session
            job_type: Filter by job type (None = all types)
        
        Returns:
            BackgroundJob or None
        """
        query = db.query(BackgroundJob).filter(
            BackgroundJob.status == cls.STATUS_PENDING,
            # Only process jobs scheduled for now or earlier
            and_(
                or_(
                    BackgroundJob.scheduled_for.is_(None),
                    BackgroundJob.scheduled_for <= datetime.now(timezone.utc)
                )
            )
        )
        
        if job_type:
            query = query.filter(BackgroundJob.job_type == job_type)
        
        # Order by priority (1=highest) and creation time
        job = query.order_by(
            BackgroundJob.priority.asc(),
            BackgroundJob.created_at.asc()
        ).first()
        
        return job
    
    @classmethod
    def mark_job_processing(
        cls,
        db: Session,
        job_id: int
    ) -> Optional[BackgroundJob]:
        """
        Mark job as processing
        WVV: Atomic status transition
        
        Args:
            db: Database session
            job_id: Job ID
        
        Returns:
            Updated job or None if not found
        """
        job = db.query(BackgroundJob).filter(BackgroundJob.id == job_id).first()
        
        if not job:
            logger.error(f"[JOB NOT FOUND] ID: {job_id}")
            return None
        
        job.status = cls.STATUS_PROCESSING
        job.started_at = datetime.now(timezone.utc)
        job.attempts += 1
        
        db.commit()
        db.refresh(job)
        
        logger.info(f"[JOB PROCESSING] ID: {job_id}, Attempt: {job.attempts}/{job.max_attempts}")
        
        return job
    
    @classmethod
    def mark_job_completed(
        cls,
        db: Session,
        job_id: int,
        result: Dict[str, Any]
    ) -> Optional[BackgroundJob]:
        """
        Mark job as completed successfully
        DC: Store result data for audit trail
        
        Args:
            db: Database session
            job_id: Job ID
            result: Success result data
        
        Returns:
            Updated job or None if not found
        """
        job = db.query(BackgroundJob).filter(BackgroundJob.id == job_id).first()
        
        if not job:
            logger.error(f"[JOB NOT FOUND] ID: {job_id}")
            return None
        
        completed_at = datetime.now(timezone.utc)
        
        # Calculate processing duration
        if job.started_at:
            duration = (completed_at - job.started_at).total_seconds() * 1000
            job.processing_duration_ms = int(duration)
        
        job.status = cls.STATUS_COMPLETED
        job.completed_at = completed_at
        job.result = result
        job.error_message = None  # Clear any previous errors
        job.error_traceback = None
        
        db.commit()
        db.refresh(job)
        
        logger.info(f"[JOB COMPLETED] ID: {job_id}, Duration: {job.processing_duration_ms}ms")
        
        return job
    
    @classmethod
    def mark_job_failed(
        cls,
        db: Session,
        job_id: int,
        error_message: str,
        error_traceback: Optional[str] = None
    ) -> Optional[BackgroundJob]:
        """
        Mark job as failed
        WVV: Automatic retry logic
        DC: Complete error logging
        
        Args:
            db: Database session
            job_id: Job ID
            error_message: User-friendly error message
            error_traceback: Full Python traceback
        
        Returns:
            Updated job or None if not found
        """
        job = db.query(BackgroundJob).filter(BackgroundJob.id == job_id).first()
        
        if not job:
            logger.error(f"[JOB NOT FOUND] ID: {job_id}")
            return None
        
        job.error_message = error_message
        job.error_traceback = error_traceback
        
        # WVV: Check if we should retry
        if job.attempts < job.max_attempts:
            job.status = cls.STATUS_RETRYING
            logger.warning(f"[JOB RETRYING] ID: {job_id}, Attempt: {job.attempts}/{job.max_attempts}, Error: {error_message}")
        else:
            job.status = cls.STATUS_FAILED
            job.completed_at = datetime.now(timezone.utc)
            logger.error(f"[JOB FAILED] ID: {job_id}, Max attempts reached, Error: {error_message}")
        
        db.commit()
        db.refresh(job)
        
        return job
    
    @classmethod
    def get_job_by_id(cls, db: Session, job_id: int) -> Optional[BackgroundJob]:
        """Get job by ID"""
        return db.query(BackgroundJob).filter(BackgroundJob.id == job_id).first()
    
    @classmethod
    def get_job_by_key(cls, db: Session, job_key: str) -> Optional[BackgroundJob]:
        """Get job by unique key"""
        return db.query(BackgroundJob).filter(BackgroundJob.job_key == job_key).first()
    
    @classmethod
    def get_jobs_by_type(
        cls,
        db: Session,
        job_type: str,
        status: Optional[str] = None,
        limit: int = 100
    ) -> List[BackgroundJob]:
        """
        Get jobs by type and optional status
        
        Args:
            db: Database session
            job_type: Job type filter
            status: Optional status filter
            limit: Maximum results
        
        Returns:
            List of jobs
        """
        query = db.query(BackgroundJob).filter(BackgroundJob.job_type == job_type)
        
        if status:
            query = query.filter(BackgroundJob.status == status)
        
        return query.order_by(BackgroundJob.created_at.desc()).limit(limit).all()
    
    @classmethod
    def get_job_stats(cls, db: Session, job_type: Optional[str] = None) -> Dict[str, int]:
        """
        Get job statistics
        WVV: Monitoring and observability
        
        Args:
            db: Database session
            job_type: Optional job type filter
        
        Returns:
            Dictionary with status counts
        """
        from sqlalchemy import func
        
        query = db.query(
            BackgroundJob.status,
            func.count(BackgroundJob.id).label('count')
        )
        
        if job_type:
            query = query.filter(BackgroundJob.job_type == job_type)
        
        results = query.group_by(BackgroundJob.status).all()
        
        stats = {
            'pending': 0,
            'processing': 0,
            'completed': 0,
            'failed': 0,
            'retrying': 0,
            'total': 0
        }
        
        for status, count in results:
            stats[status] = count
            stats['total'] += count
        
        return stats
    
    @classmethod
    def cleanup_old_jobs(
        cls,
        db: Session,
        days: int = 30,
        keep_failed: bool = True
    ) -> int:
        """
        Cleanup old completed jobs
        DC: Archive strategy (delete completed, keep failed for debugging)
        
        Args:
            db: Database session
            days: Delete jobs older than N days
            keep_failed: Keep failed jobs for analysis
        
        Returns:
            Number of jobs deleted
        """
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        
        query = db.query(BackgroundJob).filter(
            BackgroundJob.created_at < cutoff,
            BackgroundJob.status == cls.STATUS_COMPLETED
        )
        
        if not keep_failed:
            query = query.or_(BackgroundJob.status == cls.STATUS_FAILED)
        
        count = query.count()
        query.delete(synchronize_session=False)
        db.commit()
        
        logger.info(f"[JOB CLEANUP] Deleted {count} old jobs (older than {days} days)")
        
        return count


# Import fix for circular dependency
from sqlalchemy import or_
