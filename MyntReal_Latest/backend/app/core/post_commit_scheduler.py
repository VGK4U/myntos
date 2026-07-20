"""
Post-Commit Scheduler Dispatcher
DC Protocol: Guarantees APScheduler jobs are enqueued ONLY after successful DB commit
WVV: Durable retry mechanism for scheduler failures

Architecture:
- Stores deferred jobs in session.info during transaction
- Executes jobs via after_commit event hook
- Implements retry queue for scheduler failures
- Ensures dual-evidence guarantees are never violated
"""
from sqlalchemy import event
from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional
import logging
import importlib
from datetime import datetime

logger = logging.getLogger(__name__)


class PostCommitScheduler:
    """
    DC Protocol: Post-commit job scheduler with durable retry
    Ensures APScheduler jobs are only enqueued after successful DB commit
    """
    
    @staticmethod
    def register_deferred_job(session: Session, job_params: Dict[str, Any]) -> None:
        """
        Register a job to be scheduled AFTER commit
        
        Args:
            session: SQLAlchemy session (current transaction)
            job_params: Serializable job parameters
                {
                    'job_func_module': str,
                    'job_func_name': str,
                    'scheduler_job_id': str,
                    'background_job_id': int
                }
        
        DC Protocol: Jobs stored in session.info, executed only after commit
        """
        if not hasattr(session, 'info'):
            session.info = {}
        
        if 'deferred_jobs' not in session.info:
            session.info['deferred_jobs'] = []
        
        session.info['deferred_jobs'].append({
            **job_params,
            'registered_at': datetime.utcnow().isoformat()
        })
        
        logger.info(f"[POST-COMMIT] Registered deferred job: {job_params.get('scheduler_job_id')}")
    
    @staticmethod
    def execute_deferred_jobs(session: Session) -> None:
        """
        Execute all deferred jobs AFTER commit
        DC Protocol: Called by after_commit event hook
        Persists scheduler status for durable retry
        
        Args:
            session: SQLAlchemy session (transaction already committed)
        """
        if not hasattr(session, 'info') or 'deferred_jobs' not in session.info:
            return
        
        deferred_jobs: List[Dict[str, Any]] = session.info.pop('deferred_jobs', [])
        
        if not deferred_jobs:
            return
        
        logger.info(f"[POST-COMMIT] Executing {len(deferred_jobs)} deferred job(s)")
        
        from app.core.scheduler import enqueue_background_job
        from app.core.database import SessionLocal
        from app.models.background_jobs import BackgroundJob
        
        # DC: Use NEW session for persisting scheduler status (old session committed)
        db = SessionLocal()
        
        # DC: Batch processing - collect all results before persisting (transactional safety)
        job_updates = []  # List of (background_job_id, status, scheduler_job_id, error_message)
        
        for job_params in deferred_jobs:
            scheduler_job_id = job_params['scheduler_job_id']
            background_job_id = job_params['background_job_id']
            
            try:
                # DC: Dynamically import job function (JSON-safe)
                module = importlib.import_module(job_params['job_func_module'])
                job_func = getattr(module, job_params['job_func_name'])
                
                # DC: Enqueue in APScheduler (outside transaction, after commit)
                enqueue_background_job(
                    job_func=job_func,
                    job_id=scheduler_job_id,
                    args=[background_job_id]
                )
                
                # DC: Collect successful schedule for batch update
                job_updates.append((background_job_id, 'scheduled', scheduler_job_id, None))
                logger.info(f"[POST-COMMIT] ✅ Scheduled job: {scheduler_job_id}")
                
            except Exception as e:
                # DC: Collect failed schedule for batch update
                error_msg = f"Scheduler enqueue failed: {str(e)}"
                job_updates.append((background_job_id, 'failed', scheduler_job_id, error_msg))
                logger.error(
                    f"[DC VIOLATION] Failed to schedule job {scheduler_job_id} "
                    f"after commit: {e}. Will mark for retry."
                )
        
        # DC: Persist ALL status updates in SINGLE transaction (atomic durability)
        try:
            for bg_job_id, status, sched_job_id, error_msg in job_updates:
                job = db.query(BackgroundJob).filter(
                    BackgroundJob.id == bg_job_id
                ).first()
                if job:
                    job.scheduler_status = status
                    job.scheduler_job_id = sched_job_id
                    job.last_scheduler_attempt = datetime.utcnow()
                    if status == 'scheduled':
                        job.error_message = None  # Clear error on success
                    else:
                        job.error_message = error_msg
            
            # DC: Single commit for ALL job status updates (transactional safety)
            db.commit()
            logger.info(f"[POST-COMMIT] Persisted status updates for {len(job_updates)} job(s)")
            
        except Exception as persist_error:
            # DC: Transaction failure - rollback ALL updates, jobs will retry next cycle
            logger.error(f"[CRITICAL] Failed to persist scheduler status updates: {persist_error}")
            db.rollback()
        finally:
            db.close()
    
    @staticmethod
    def clear_deferred_jobs(session: Session) -> None:
        """
        Clear deferred jobs from session (on rollback or close)
        DC Protocol: Prevents phantom job scheduling after transaction failure
        
        Args:
            session: SQLAlchemy session
        """
        if hasattr(session, 'info') and 'deferred_jobs' in session.info:
            cleared_count = len(session.info['deferred_jobs'])
            session.info.pop('deferred_jobs', None)
            if cleared_count > 0:
                logger.warning(f"[POST-COMMIT] Cleared {cleared_count} deferred job(s) due to rollback/close")
    
    @staticmethod
    def setup_event_hooks(engine) -> None:
        """
        Setup SQLAlchemy event hooks for post-commit scheduling
        DC Protocol: Must be called ONCE during app initialization
        
        Args:
            engine: SQLAlchemy engine
        """
        # DC: Guard against duplicate registration (prevent multiple listeners)
        if hasattr(PostCommitScheduler, '_hooks_registered'):
            logger.warning("[POST-COMMIT] Event hooks already registered, skipping")
            return
        
        @event.listens_for(Session, "after_commit")
        def after_commit_handler(session):
            """
            SQLAlchemy event: Execute deferred jobs after successful commit
            DC Protocol: Guarantees jobs only run if transaction succeeded
            """
            try:
                PostCommitScheduler.execute_deferred_jobs(session)
            except Exception as e:
                logger.error(f"[POST-COMMIT] Error executing deferred jobs: {e}")
        
        @event.listens_for(Session, "after_rollback")
        def after_rollback_handler(session):
            """
            SQLAlchemy event: Clear deferred jobs after transaction rollback
            DC Protocol: Prevents phantom job scheduling for rolled-back records
            """
            PostCommitScheduler.clear_deferred_jobs(session)
        
        @event.listens_for(Session, "after_soft_rollback")
        def after_soft_rollback_handler(session, previous_transaction):
            """
            SQLAlchemy event: Clear deferred jobs after soft rollback (nested transactions)
            DC Protocol: Handles savepoint rollbacks
            """
            PostCommitScheduler.clear_deferred_jobs(session)
        
        # Mark as registered
        PostCommitScheduler._hooks_registered = True
        
        logger.info("[POST-COMMIT] Event hooks registered: after_commit, after_rollback, after_soft_rollback")


# Global instance for easy access
post_commit_scheduler = PostCommitScheduler()
