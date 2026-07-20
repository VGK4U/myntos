"""
Scheduler Retry Dispatcher
DC Protocol: Durable retry mechanism for failed APScheduler enqueue attempts
WVV: Ensures dual-evidence guarantees are eventually met

Purpose:
- Periodically scans for background_jobs with scheduler_status='failed'
- Retries APScheduler enqueue for those jobs
- Updates scheduler_status to 'scheduled' on success
- Provides guaranteed eventual consistency for DC Protocol compliance
"""
from app.core.database import SessionLocal
from app.models.background_jobs import BackgroundJob
from app.core.scheduler import enqueue_background_job
import logging
import importlib
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


def retry_failed_scheduler_jobs():
    """
    Periodic task: Retry APScheduler enqueue for jobs with scheduler_status='failed'
    DC Protocol: Durable retry ensures dual-evidence guarantees
    
    Runs every 5 minutes to retry failed scheduler enqueue attempts
    """
    # DC Protocol (Mar 23, 2026): Guard SessionLocal() acquisition — if the DB pool is
    # momentarily exhausted (e.g. at startup under burst load), skip this run gracefully
    # rather than raising a Fatal error.  The scheduler will retry in 5 minutes.
    try:
        db = SessionLocal()
    except Exception as e:
        logger.warning(
            f"[RETRY-DISPATCHER] Could not acquire DB session (pool may be saturated), "
            f"skipping this run — will retry in 5 minutes. Error: {e}"
        )
        return
    try:
        # DC: Find all jobs that failed to enqueue in APScheduler
        # Only retry jobs created in last 24 hours (prevent infinite retry of old jobs)
        cutoff_time = datetime.utcnow() - timedelta(hours=24)
        
        failed_jobs = db.query(BackgroundJob).filter(
            BackgroundJob.scheduler_status == 'failed',
            BackgroundJob.created_at >= cutoff_time,
            BackgroundJob.status.in_(['pending', 'retrying'])  # Don't retry completed/failed jobs
        ).order_by(BackgroundJob.created_at.asc()).limit(50).all()  # Process max 50 per run
        
        if not failed_jobs:
            logger.debug("[RETRY-DISPATCHER] No failed scheduler jobs to retry")
            return
        
        logger.info(f"[RETRY-DISPATCHER] Found {len(failed_jobs)} job(s) with scheduler_status='failed', attempting retry")
        
        retry_success_count = 0
        retry_failure_count = 0
        
        for job in failed_jobs:
            try:
                # DC: Use job handler metadata (generalized for ALL job types)
                if not job.job_handler_module or not job.job_handler_function:
                    logger.warning(
                        f"[RETRY-DISPATCHER] Job {job.id} missing handler metadata "
                        f"(job_handler_module/function), skipping"
                    )
                    continue
                
                # DC: Dynamically import job function from stored metadata
                module = importlib.import_module(job.job_handler_module)
                job_func = getattr(module, job.job_handler_function)
                
                # DC: Generate new scheduler job ID for this retry attempt
                scheduler_job_id = f'retry_{job.job_type}_{job.id}_{int(datetime.utcnow().timestamp())}'
                
                # DC: Retry APScheduler enqueue
                enqueue_background_job(
                    job_func=job_func,
                    job_id=scheduler_job_id,
                    args=[job.id]
                )
                
                # DC: Persist success status + scheduler metadata (atomic update)
                job.scheduler_status = 'scheduled'
                job.error_message = None  # Clear error message on success
                job.scheduler_job_id = scheduler_job_id  # Audit trail
                job.last_scheduler_attempt = datetime.utcnow()  # Retry timestamp
                db.commit()
                
                retry_success_count += 1
                logger.info(f"[RETRY-DISPATCHER] ✅ Retried job {job.id} successfully (scheduler_job_id: {scheduler_job_id})")
                
            except Exception as e:
                # DC: Retry failed again - persist failure status for next retry
                retry_failure_count += 1
                logger.error(f"[RETRY-DISPATCHER] ❌ Retry failed for job {job.id}: {e}")
                
                try:
                    # DC: Update error message + retry attempt metadata
                    job.error_message = f"Scheduler retry failed: {str(e)} (last attempt: {datetime.utcnow().isoformat()})"
                    job.last_scheduler_attempt = datetime.utcnow()  # Track failed attempt
                    db.commit()
                except Exception as persist_error:
                    logger.error(f"[RETRY-DISPATCHER] Failed to persist retry failure for job {job.id}: {persist_error}")
                    db.rollback()
        
        logger.info(
            f"[RETRY-DISPATCHER] Completed: {retry_success_count} succeeded, "
            f"{retry_failure_count} failed (will retry again)"
        )
        
    except Exception as e:
        logger.error(f"[RETRY-DISPATCHER] Fatal error in retry dispatcher: {e}")
        db.rollback()
    finally:
        db.close()


def init_retry_dispatcher_schedule(scheduler):
    """
    Initialize the retry dispatcher as a periodic scheduled task
    DC Protocol: Must be called during scheduler initialization
    
    Args:
        scheduler: APScheduler instance
    """
    # Run every 5 minutes
    scheduler.add_job(
        func=retry_failed_scheduler_jobs,
        trigger='interval',
        minutes=5,
        id='scheduler_retry_dispatcher',
        name='Scheduler Retry Dispatcher (DC Protocol)',
        replace_existing=True,
        max_instances=1,  # Prevent concurrent runs
        misfire_grace_time=300  # 5 minutes grace period
    )
    
    logger.info("[RETRY-DISPATCHER] Scheduled retry dispatcher task (runs every 5 minutes)")
