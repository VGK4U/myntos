"""
Automation Tracking & Lifecycle Service
Manages authoritative execution tracking, granular dispatch recording,
and target configurations across all automation jobs.
Architecture:
Automation Job -> AutomationExecution -> AutomationDispatch -> Queue/MessageLog -> Provider
"""

import uuid
import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.automation import AutomationExecution, AutomationDispatch, AutomationTargetConfig

logger = logging.getLogger(__name__)


def generate_execution_id(job_id: str) -> str:
    utc_now = datetime.now(timezone.utc)
    ts = utc_now.strftime("%Y%m%d_%H%M%S")
    rnd = uuid.uuid4().hex[:6]
    return f"{job_id}_{ts}_{rnd}"


def create_execution(
    db: Session,
    job_id: str,
    job_name: str,
    trigger_type: str = "SCHEDULED",
    triggered_by: str = "System Cron",
    staff_id: Optional[int] = None,
    company_id: int = 1,
    target_summary: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> AutomationExecution:
    eid = generate_execution_id(job_id)
    now_utc = datetime.utcnow()
    execution = AutomationExecution(
        id=eid,
        job_id=job_id,
        job_name=job_name,
        trigger_type=trigger_type,
        triggered_by=triggered_by,
        triggered_by_staff_id=staff_id,
        company_id=company_id,
        status="RUNNING",
        target_summary=target_summary,
        total_targets=0,
        sent_count=0,
        uncertain_count=0,
        failed_count=0,
        skipped_count=0,
        started_at=now_utc,
        is_legacy=False,
        execution_metadata=metadata or {}
    )
    db.add(execution)
    db.commit()
    db.refresh(execution)
    return execution


def record_dispatch(
    db: Session,
    execution_id: Any,
    job_id: str,
    recipient_type: str,
    recipient_identifier: str,
    recipient_name: Optional[str] = None,
    target_entity_type: Optional[str] = None,
    target_entity_id: Optional[int] = None,
    queue_id: Optional[int] = None,
    message_log_id: Optional[int] = None,
    provider: str = "META_WHATSAPP",
    provider_message_id: Optional[str] = None,
    status: str = "PENDING",
    sent_at: Optional[datetime] = None,
    error_code: Optional[str] = None,
    error_message: Optional[str] = None,
    payload_snapshot: Optional[Dict[str, Any]] = None,
    company_id: int = 1,
    **kwargs
) -> AutomationDispatch:
    exec_id_str = getattr(execution_id, 'id', str(execution_id))
    clean_status = status.upper()
    if clean_status not in ("PENDING", "QUEUED", "PROCESSING", "SENT", "UNCERTAIN", "FAILED", "SKIPPED"):
        clean_status = "SENT" if clean_status in ("SUCCESS", "COMPLETED") else "FAILED"

    now_utc = datetime.utcnow()
    dispatch = AutomationDispatch(
        execution_id=exec_id_str,
        job_id=job_id,
        recipient_type=recipient_type,
        recipient_identifier=str(recipient_identifier),
        recipient_name=recipient_name or str(recipient_identifier),
        target_entity_type=target_entity_type,
        target_entity_id=target_entity_id,
        queue_id=queue_id,
        message_log_id=message_log_id,
        provider=provider,
        provider_message_id=provider_message_id,
        status=clean_status,
        sent_at=sent_at or (now_utc if clean_status == "SENT" else None),
        failed_at=now_utc if clean_status == "FAILED" else None,
        error_code=error_code,
        error_message=error_message,
        payload_snapshot=payload_snapshot
    )
    db.add(dispatch)
    db.commit()
    db.refresh(dispatch)
    return dispatch


def finalize_execution(
    db: Session,
    execution_id: Any,
    overall_error: Optional[str] = None
) -> AutomationExecution:
    exec_id_str = getattr(execution_id, 'id', str(execution_id))
    execution = db.query(AutomationExecution).filter(AutomationExecution.id == exec_id_str).first()
    if not execution:
        logger.error(f"Execution {exec_id_str} not found for finalization")
        return None

    # Derive aggregates strictly from child dispatch rows
    dispatches = db.query(AutomationDispatch).filter(AutomationDispatch.execution_id == exec_id_str).all()
    total_cnt = len(dispatches)
    sent_cnt = sum(1 for d in dispatches if d.status == "SENT")
    uncertain_cnt = sum(1 for d in dispatches if d.status in ("UNCERTAIN", "DISPATCH_UNCERTAIN"))
    failed_cnt = sum(1 for d in dispatches if d.status in ("FAILED", "ERROR"))
    skipped_cnt = sum(1 for d in dispatches if d.status == "SKIPPED")

    if uncertain_cnt > 0:
        eff_status = "UNCERTAIN"
    elif failed_cnt > 0 and sent_cnt == 0 and total_cnt > skipped_cnt:
        eff_status = "FAILED"
    elif sent_cnt > 0 and failed_cnt > 0:
        eff_status = "PARTIAL_SUCCESS"
    elif sent_cnt > 0:
        eff_status = "SUCCESS"
    elif total_cnt > 0 and skipped_cnt == total_cnt:
        eff_status = "SKIPPED"
    elif total_cnt == 0:
        eff_status = "SKIPPED" if not overall_error else "FAILED"
    else:
        eff_status = "SUCCESS"

    execution.total_targets = total_cnt
    execution.sent_count = sent_cnt
    execution.uncertain_count = uncertain_cnt
    execution.failed_count = failed_cnt
    execution.skipped_count = skipped_cnt
    execution.status = eff_status
    execution.completed_at = datetime.utcnow()
    if overall_error:
        execution.error_message = overall_error
    elif failed_cnt > 0 or uncertain_cnt > 0:
        err_msg = next((d.error_message for d in dispatches if d.error_message), None)
        if err_msg:
            execution.error_message = err_msg
        elif uncertain_cnt > 0:
            execution.error_message = f"{uncertain_cnt} dispatches uncertain"
        else:
            execution.error_message = f"{failed_cnt} dispatches failed"

    db.commit()
    db.refresh(execution)
    return execution


def get_job_targets(db: Session, job_id: str, company_id: int = 1, active_only: bool = True) -> List[AutomationTargetConfig]:
    q = db.query(AutomationTargetConfig).filter(
        AutomationTargetConfig.job_id == job_id,
        AutomationTargetConfig.company_id == company_id
    )
    if active_only:
        q = q.filter(AutomationTargetConfig.is_active == True)
    return q.order_by(AutomationTargetConfig.id.asc()).all()


def add_job_target(
    db: Session,
    job_id: str,
    name: Optional[str] = None,
    identifier: Optional[str] = None,
    target_type: str = "group",
    staff_id: Optional[int] = None,
    company_id: int = 1,
    recipient_type: Optional[str] = None,
    recipient_identifier: Optional[str] = None,
    recipient_name: Optional[str] = None,
    target_role: str = "PRIMARY",
    **kwargs
) -> AutomationTargetConfig:
    resolved_name = (recipient_name or name or "").strip()
    resolved_identifier = (recipient_identifier or identifier or "").strip()
    resolved_type = (recipient_type or target_type or "group").strip()
    resolved_role = (target_role or "PRIMARY").strip()

    row = AutomationTargetConfig(
        job_id=job_id,
        company_id=company_id,
        target_type=resolved_type,
        name=resolved_name,
        identifier=resolved_identifier,
        target_role=resolved_role,
        is_active=True,
        created_by_staff_id=staff_id
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def remove_job_target(db: Session, target_id: int, company_id: int = 1) -> bool:
    row = db.query(AutomationTargetConfig).filter(
        AutomationTargetConfig.id == target_id,
        AutomationTargetConfig.company_id == company_id
    ).first()
    if row:
        db.delete(row)
        db.commit()
        return True
    return False
