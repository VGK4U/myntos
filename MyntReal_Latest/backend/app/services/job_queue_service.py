"""
Durable PostgreSQL Job Queue Service (Release 1A Queue Layer)
Global Multi-Tenant Worker implementing FOR UPDATE SKIP LOCKED.
Includes stale lock recovery sweeper, exponential backoff, DLQ, and non-blocking job handlers.
"""

import logging
import asyncio
import signal
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.core.config import settings

logger = logging.getLogger(__name__)


def enqueue_system_job(
    db: Session,
    company_id: int,
    job_type: str,
    payload: Dict[str, Any],
    idempotency_key: str,
    correlation_id: Optional[str] = None,
    max_attempts: int = 5
) -> Optional[int]:
    """
    Enqueue a background job with explicit non-null company_id and idempotency key.
    Safe to call concurrently — returns existing job ID if idempotency key exists.
    """
    if not company_id:
        raise ValueError("Job creation requires an explicit, non-null company_id")
    if not idempotency_key:
        raise ValueError("Job creation requires an explicit idempotency_key")

    try:
        # Check idempotency
        existing = db.execute(
            text("SELECT id FROM system_jobs WHERE idempotency_key = :ikey LIMIT 1"),
            {"ikey": idempotency_key}
        ).fetchone()
        if existing:
            return existing[0]

        import json
        res = db.execute(
            text("""
                INSERT INTO system_jobs 
                    (company_id, job_type, payload, status, attempts, max_attempts, 
                     next_attempt_at, idempotency_key, correlation_id, created_at)
                VALUES 
                    (:cid, :jtype, :payload, 'QUEUED', 0, :max_att, 
                     NOW(), :ikey, :corrid, NOW())
                RETURNING id
            """),
            {
                "cid": company_id,
                "jtype": job_type,
                "payload": json.dumps(payload),
                "max_att": max_attempts,
                "ikey": idempotency_key,
                "corrid": correlation_id
            }
        ).fetchone()
        db.commit()
        return res[0] if res else None
    except Exception as e:
        db.rollback()
        logger.error(f"[QUEUE-ENQUEUE-ERROR] Failed to enqueue job {idempotency_key}: {e}")
        return None


def recover_stale_jobs(db: Session) -> int:
    """
    Stale Lock Sweeper: Finds jobs stuck in 'PROCESSING' where locked_until < NOW().
    Resets status to 'QUEUED' without consuming the business attempts retry budget.
    """
    try:
        res = db.execute(text("""
            UPDATE system_jobs 
            SET status = 'QUEUED', locked_by = NULL, locked_until = NULL
            WHERE status = 'PROCESSING' AND locked_until < NOW()
        """))
        db.commit()
        recovered_count = res.rowcount
        if recovered_count > 0:
            logger.info(f"[QUEUE-SWEEPER] Recovered {recovered_count} stale locked jobs back to QUEUED")
        return recovered_count
    except Exception as e:
        db.rollback()
        logger.error(f"[QUEUE-SWEEPER-ERROR] Stale job recovery failed: {e}")
        return 0


def claim_next_job(db: Session, worker_id: str = "global_worker_1") -> Optional[Dict[str, Any]]:
    """
    Claim next queued job using FOR UPDATE SKIP LOCKED.
    Global Multi-Tenant: Claims queued jobs across any company, resolving tenant context explicitly.
    """
    try:
        row = db.execute(text("""
            SELECT id, company_id, job_type, payload, attempts, max_attempts
            FROM system_jobs
            WHERE status = 'QUEUED' AND next_attempt_at <= NOW()
            ORDER BY next_attempt_at ASC, id ASC
            FOR UPDATE SKIP LOCKED
            LIMIT 1
        """)).fetchone()

        if not row:
            return None

        job_id, company_id, job_type, payload_str, attempts, max_attempts = row
        import json
        payload = json.loads(payload_str) if isinstance(payload_str, str) else payload_str

        # Acquire 5-minute lease lock
        db.execute(text("""
            UPDATE system_jobs
            SET status = 'PROCESSING', locked_by = :wid, locked_until = NOW() + INTERVAL '5 minutes'
            WHERE id = :jid
        """), {"wid": worker_id, "jid": job_id})
        db.commit()

        return {
            "id": job_id,
            "company_id": company_id,
            "job_type": job_type,
            "payload": payload,
            "attempts": attempts,
            "max_attempts": max_attempts,
        }
    except Exception as e:
        db.rollback()
        logger.error(f"[QUEUE-CLAIM-ERROR] Claim job failed: {e}")
        return None


def complete_job(db: Session, job_id: int):
    """Mark job completed."""
    try:
        db.execute(text("""
            UPDATE system_jobs
            SET status = 'COMPLETED', locked_by = NULL, locked_until = NULL, processed_at = NOW()
            WHERE id = :jid
        """), {"jid": job_id})
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"[QUEUE-COMPLETE-ERROR] Complete job {job_id} failed: {e}")


def fail_job(db: Session, job_id: int, attempts: int, max_attempts: int, error_msg: str):
    """
    Handle business/API failure:
    - If attempts + 1 >= max_attempts -> status = FAILED_DLQ
    - Otherwise -> status = QUEUED, apply exponential backoff (30 * 2^attempts seconds)
    """
    new_attempts = attempts + 1
    if new_attempts >= max_attempts:
        status = 'FAILED_DLQ'
        next_attempt = datetime.utcnow()
    else:
        status = 'QUEUED'
        delay_seconds = 30 * (2 ** attempts)
        next_attempt = datetime.utcnow() + timedelta(seconds=delay_seconds)

    try:
        db.execute(text("""
            UPDATE system_jobs
            SET status = :st, attempts = :att, next_attempt_at = :next_att,
                locked_by = NULL, locked_until = NULL, error_log = :err
            WHERE id = :jid
        """), {
            "st": status,
            "att": new_attempts,
            "next_att": next_attempt,
            "err": error_msg[:2000],
            "jid": job_id
        })
        db.commit()
        if status == 'FAILED_DLQ':
            logger.error(f"[QUEUE-DLQ] Job {job_id} failed permanently after {new_attempts} attempts: {error_msg}")
    except Exception as e:
        db.rollback()
        logger.error(f"[QUEUE-FAIL-ERROR] Fail job {job_id} handling error: {e}")


def process_single_job(db: Session, job: Dict[str, Any]):
    """Execute job handler within explicit company_id tenant context."""
    job_id = job["id"]
    company_id = job["company_id"]
    job_type = job["job_type"]
    payload = job["payload"]
    attempts = job["attempts"]
    max_attempts = job["max_attempts"]

    logger.info(f"[JOB-EXEC] Processing job {job_id} ({job_type}) for company {company_id}")

    try:
        if job_type == "WA_AUDIT_LOG":
            # Handled non-disruptively by audit handler
            from app.models.wa_audit import WAConversation, WAMessage
            conv_id = payload.get("conversation_id")
            lead_id = payload.get("lead_id")
            wamid = payload.get("wamid")
            body = payload.get("body_text", "")
            direction = payload.get("direction", "INBOUND")
            sender = payload.get("sender_type", "CUSTOMER")

            if conv_id and lead_id:
                existing_msg = db.query(WAMessage).filter_by(wamid=wamid).first() if wamid else None
                if not existing_msg:
                    wa_msg = WAMessage(
                        company_id=company_id,
                        conversation_id=conv_id,
                        lead_id=lead_id,
                        wamid=wamid,
                        direction=direction,
                        sender_type=sender,
                        body_text=body[:2000],
                        delivery_status="DELIVERED" if direction == "INBOUND" else "SENT",
                        sent_at=datetime.utcnow()
                    )
                    db.add(wa_msg)
                    db.commit()

        elif job_type == "META_DAILY_INSIGHTS_SYNC":
            from app.services.meta_insights_service import sync_meta_insights_for_company
            sync_meta_insights_for_company(db, company_id)

        complete_job(db, job_id)
    except Exception as e:
        error_str = str(e)
        logger.error(f"[JOB-EXEC-FAILED] Job {job_id} error: {error_str}")
        fail_job(db, job_id, attempts, max_attempts, error_str)
