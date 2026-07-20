"""
MyOperator Logs Sync Service
DC Protocol: Periodic background sync to catch calls missed by webhook.
Polls MyOperator Logs API for answered and missed calls.
API token stored in MYOPERATOR_API_TOKEN env var.
Created: Mar 2026
"""

import os
import re
import json
import logging
import requests
from datetime import datetime, timedelta
from typing import Optional
import pytz
from sqlalchemy.orm import Session
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError

from app.core.database import SessionLocal
from app.models.operator_calls import OperatorCall
from app.models.crm import CRMLead, CRMLeadFollowUp

logger = logging.getLogger(__name__)

IST = pytz.timezone('Asia/Kolkata')
MYOPERATOR_API_TOKEN = os.getenv('MYOPERATOR_API_TOKEN', '')

# ── Last sync result cache (in-process) ──────────────────────────────────────
_last_sync: dict = {
    'ran_at': None,
    'synced': 0,
    'created': 0,
    'updated': 0,
    'skipped': 0,
    'followups_created': 0,
    'error': None,
    'token_configured': bool(os.getenv('MYOPERATOR_API_TOKEN', '')),
}


MYOPERATOR_X_API_KEY = os.getenv('MYOPERATOR_X_API_KEY', '')
MYOPERATOR_API_COMPANY_ID = os.getenv('MYOPERATOR_API_COMPANY_ID', '')
MYOPERATOR_COMPANY_ID = int(os.getenv('MYOPERATOR_COMPANY_ID', '1'))
MYOPERATOR_BASE_URL = 'https://developers.myoperator.co'


def get_last_sync_status() -> dict:
    return dict(_last_sync)


def get_ist_now():
    return datetime.now(IST).replace(tzinfo=None)


def normalize_phone(phone: str) -> Optional[str]:
    if not phone:
        return None
    digits = re.sub(r'[^\d]', '', str(phone))
    if len(digits) > 10:
        digits = digits[-10:]
    return digits if len(digits) == 10 else None


def _match_lead(db: Session, phone: str) -> Optional[CRMLead]:
    norm = normalize_phone(phone)
    if not norm:
        return None
    return db.query(CRMLead).filter(
        or_(
            CRMLead.phone.like(f'%{norm}'),
            CRMLead.alternate_phone.like(f'%{norm}')
        ),
        CRMLead.company_id == MYOPERATOR_COMPANY_ID
    ).order_by(CRMLead.created_at.desc()).first()


def _ensure_followup(db: Session, call: OperatorCall) -> None:
    if call.followup_created or not call.crm_lead_id:
        return
    lead = db.query(CRMLead).filter(CRMLead.id == call.crm_lead_id).first()
    if not lead:
        return
    now = get_ist_now()
    scheduled = now + timedelta(hours=2)
    fu = CRMLeadFollowUp(
        company_id=lead.company_id,
        lead_id=lead.id,
        followup_type='call',
        status='scheduled',
        scheduled_date=scheduled,
        subject=f'Missed call from {call.caller_number}',
        notes=f'Auto-created by MyOperator sync. Call ID: {call.call_id}.',
        handler_type=lead.handler_type,
        handler_id=lead.handler_id,
        created_by_type='system',
        created_by_id='operator_sync',
    )
    db.add(fu)
    db.flush()
    call.followup_created = True
    call.followup_id = fu.id


def _parse_duration_seconds(duration_str: str) -> int:
    """Convert 'HH:MM:SS' duration string to seconds."""
    try:
        parts = str(duration_str).strip().split(':')
        if len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
        if len(parts) == 2:
            return int(parts[0]) * 60 + int(parts[1])
    except Exception:
        pass
    try:
        return int(duration_str)
    except Exception:
        return 0


def _extract_additional_param(params_list: list, key: str) -> str:
    """Extract value from MyOperator additional_parameters list [{ky, vl}]."""
    for item in (params_list or []):
        if item.get('ky') == key:
            return str(item.get('vl', ''))
    return ''


def _normalize_source_record(source: dict) -> dict:
    """
    Convert a MyOperator _source record to normalized internal format.
    API returns: allcaller_id, caller_number, start_time, end_time,
                 duration, event (1=incoming, 2=outgoing), status (1=answered, 2=missed, 3=voicemail),
                 fileurl (recording), department_name, additional_parameters
    For outgoing calls: caller_number = company virtual number, customer number is in additional_parameters.
    """
    params_list = source.get('additional_parameters') or []

    # Try multiple keys for call_id
    unique_id = (
        _extract_additional_param(params_list, 'unique_id')
        or _extract_additional_param(params_list, 'call_id')
        or _extract_additional_param(params_list, 'uuid')
    )
    call_id = unique_id or source.get('allcaller_id') or source.get('user_id') or ''

    event = source.get('event', 1)
    call_type = 'inbound' if int(event) == 1 else 'outbound'

    # VERIFIED from raw payload: for BOTH inbound and outbound calls,
    # caller_number_raw = the customer's phone number (10 digits, no country code)
    # caller_number = same but with +91 prefix
    # For outbound, the company's virtual number is in log_details[0]._did
    caller_raw = source.get('caller_number_raw') or ''
    caller_e164 = source.get('caller_number') or ''

    # Normalize customer number to 10 digits
    raw_digits = re.sub(r'[^\d]', '', caller_raw)
    if len(raw_digits) > 10:
        raw_digits = raw_digits[-10:]

    if not raw_digits or len(raw_digits) < 10:
        # Fallback: strip +91 from E164
        e164_digits = re.sub(r'[^\d]', '', re.sub(r'^\+?91', '', caller_e164))
        if len(e164_digits) > 10:
            e164_digits = e164_digits[-10:]
        raw_digits = e164_digits

    caller = raw_digits  # Customer's number (same for inbound & outbound)

    # Virtual number: for outbound try log_details[0]._did, else additional_params
    log_details = source.get('log_details') or []
    did_from_log = ''
    if log_details and isinstance(log_details, list):
        first_log = log_details[0] if log_details else {}
        did_raw = first_log.get('_did', '') or ''
        did_digits = re.sub(r'[^\d]', '', re.sub(r'^\+?91', '', did_raw))
        if len(did_digits) > 10:
            did_digits = did_digits[-10:]
        did_from_log = did_digits

    called = (
        did_from_log
        or _extract_additional_param(params_list, 'virtual_number')
        or _extract_additional_param(params_list, 'called_number')
        or source.get('virtual_number', '')
    )

    duration_str = source.get('duration') or '0'
    dur_secs = _parse_duration_seconds(duration_str)

    # CRITICAL: status field from MyOperator API
    # status: 1 = answered/connected, 2 = missed/not answered, 3 = voicemail
    status_code = source.get('status', 2)
    try:
        status_code = int(status_code)
    except (TypeError, ValueError):
        status_code = 2

    if status_code == 1:
        status = 'answered'
    elif status_code == 3:
        status = 'voicemail'
    else:
        # status_code 2 (or unknown) = missed
        status = 'missed'

    start_ts = source.get('start_time') or 0
    end_ts = source.get('end_time') or 0
    started_at = datetime.utcfromtimestamp(int(start_ts)) if start_ts else None
    ended_at = datetime.utcfromtimestamp(int(end_ts)) if end_ts else None

    # Recording URL
    recording_url = source.get('fileurl') or source.get('recording_url') or None
    if recording_url and not recording_url.startswith('http'):
        recording_url = None

    # Operator/department name (which virtual number / department received the call)
    operator_name = (
        source.get('department_name')
        or _extract_additional_param(params_list, 'agent_name')
        or _extract_additional_param(params_list, 'operator_name')
        or ''
    )

    # Extract agent who handled the call and how it ended
    # log_details contains per-agent leg details
    log_details = source.get('log_details') or []
    handled_by = ''
    miss_reason = ''
    if log_details and isinstance(log_details, list):
        # Find the leg where the call was actually received/answered first
        answered_leg = next((l for l in log_details if l.get('action') in ('received', 'answered')), None)
        primary_leg = answered_leg or log_details[0]
        # Agent name from received_by list
        received_by = primary_leg.get('received_by') or []
        if received_by and isinstance(received_by, list):
            # Combine all agent names who were on the call
            names = [a.get('name', '') for a in received_by if a.get('name')]
            handled_by = ', '.join(names) if names else ''
        # How the call ended — _ds field: ANSWER, CANCEL, NOANSWER, BUSY
        raw_ds = (primary_leg.get('_ds') or '').upper().strip()
        miss_reason_map = {
            'CANCEL': 'Caller Hung Up',
            'NOANSWER': 'No Answer',
            'BUSY': 'Busy',
            'ANSWER': 'Connected',
            'REJECT': 'Rejected',
            'VOICEMAIL': 'Voicemail',
        }
        miss_reason = miss_reason_map.get(raw_ds, raw_ds) if raw_ds else ''

    # Log raw data for discovery (debug only)
    logger.debug('[OPERATOR_SYNC] Raw source keys: %s | event=%s status=%s caller=%s handled_by=%s',
                 list(source.keys()), event, status_code, caller, handled_by)

    return {
        'call_id': call_id,
        'caller_number': caller,
        'called_number': called,
        'call_type': call_type,
        'status': status,
        'duration_seconds': dur_secs,
        'started_at': started_at,
        'ended_at': ended_at,
        'recording_url': recording_url,
        'operator_name': operator_name,
        'handled_by': handled_by,
        'miss_reason': miss_reason,
        '_raw': source,
    }


def _fetch_myoperator_logs(ts_from: int, ts_to: int) -> list:
    """
    Fetch call logs from MyOperator Search API.
    URL: POST https://developers.myoperator.co/search
    Auth: token= in POST body (user-specific API token).
    Pagination: log_from (offset), page_size (max 100).
    Returns list of normalized call records or empty list on failure.
    """
    if not MYOPERATOR_API_TOKEN:
        logger.warning('[OPERATOR_SYNC] MYOPERATOR_API_TOKEN not set — skipping API fetch')
        return []

    url = f'{MYOPERATOR_BASE_URL}/search'
    page_size = 100
    all_records = []
    log_from = 0
    max_iterations = 20

    for _ in range(max_iterations):
        payload = {
            'token': MYOPERATOR_API_TOKEN,
            'from': ts_from,
            'to': ts_to,
            'page_size': page_size,
            'log_from': log_from,
        }
        try:
            resp = requests.post(url, data=payload, timeout=20)
            try:
                body = resp.json()
            except Exception:
                logger.warning('[OPERATOR_SYNC] Non-JSON response: %s', resp.text[:200])
                break
            if body.get('status') != 'success':
                logger.warning('[OPERATOR_SYNC] API error: %s', body.get('message', body)[:300])
                break
            hits = (body.get('data') or {}).get('hits') or []
            if not hits:
                break
            for hit in hits:
                source = hit.get('_source') or {}
                if source:
                    all_records.append(_normalize_source_record(source))
            log_from += len(hits)
            total = (body.get('data') or {}).get('total') or 0
            if log_from >= total or len(hits) < page_size:
                break
        except Exception as e:
            logger.error('[OPERATOR_SYNC] Request failed: %s', e)
            break

    logger.info('[OPERATOR_SYNC] Fetched %d records (ts_from=%d, ts_to=%d)', len(all_records), ts_from, ts_to)
    return all_records


def sync_myoperator_logs(db: Optional[Session] = None, days_back: Optional[int] = None) -> dict:
    """
    Sync MyOperator call logs.
    days_back=None → last 2 hours (routine); days_back=N → last N days (backfill).
    Can be called with an existing db session or will create its own.
    """
    close_db = False
    if db is None:
        db = SessionLocal()
        close_db = True

    now = get_ist_now()
    now_utc = datetime.utcnow()
    ts_to = int(now_utc.timestamp())
    if days_back and days_back > 0:
        ts_from = int((now_utc - timedelta(days=days_back)).timestamp())
        logger.info('[OPERATOR_SYNC] Backfill mode: last %d days', days_back)
    else:
        ts_from = int((now_utc - timedelta(hours=2)).timestamp())

    synced = 0
    created = 0
    updated = 0
    skipped = 0
    followups_created = 0

    try:
        records = _fetch_myoperator_logs(ts_from, ts_to)

        for rec in records:
            call_id = rec.get('call_id') or ''
            if not call_id:
                continue

            status = rec.get('status', 'missed')
            caller = rec.get('caller_number') or ''
            called = rec.get('called_number') or ''
            duration = rec.get('duration_seconds') or 0
            recording_url = rec.get('recording_url') or None
            call_type = rec.get('call_type') or 'inbound'
            op_name = rec.get('operator_name') or ''
            handled_by = rec.get('handled_by') or ''
            miss_reason = rec.get('miss_reason') or ''
            started_at = rec.get('started_at') or now
            ended_at = rec.get('ended_at') or None

            existing = db.query(OperatorCall).filter(
                OperatorCall.company_id == MYOPERATOR_COMPANY_ID,
                OperatorCall.call_id == str(call_id)
            ).first()
            if existing:
                existing.status = status
                if caller and not existing.caller_number:
                    existing.caller_number = caller
                if called and not existing.called_number:
                    existing.called_number = called
                if op_name and not existing.operator_name:
                    existing.operator_name = op_name
                if handled_by:
                    existing.handled_by = handled_by
                if miss_reason:
                    existing.miss_reason = miss_reason
                if status == 'answered' and not existing.answered_at:
                    existing.answered_at = ended_at or now
                if not existing.ended_at and ended_at:
                    existing.ended_at = ended_at
                if duration:
                    existing.duration_seconds = duration
                if recording_url:
                    existing.recording_url = recording_url
                if not existing.lead_matched and caller:
                    lead = _match_lead(db, caller)
                    if lead:
                        existing.crm_lead_id = lead.id
                        existing.lead_matched = True
                existing.updated_at = now
                if status == 'missed':
                    _ensure_followup(db, existing)
                    if existing.followup_created:
                        followups_created += 1
                updated += 1
            else:
                lead = _match_lead(db, caller) if caller else None
                raw_src = rec.get('_raw') or rec
                call = OperatorCall(
                    call_id=str(call_id),
                    company_id=MYOPERATOR_COMPANY_ID,
                    caller_number=caller,
                    called_number=called,
                    operator_name=op_name,
                    operator_number='',
                    handled_by=handled_by,
                    miss_reason=miss_reason,
                    missed_status='pending' if status == 'missed' else None,
                    call_type=call_type,
                    status=status,
                    started_at=started_at,
                    ended_at=ended_at,
                    answered_at=ended_at if status == 'answered' else None,
                    duration_seconds=duration,
                    recording_url=recording_url,
                    crm_lead_id=lead.id if lead else None,
                    lead_matched=bool(lead),
                    raw_payload=json.dumps(raw_src)[:4000],
                )
                try:
                    db.add(call)
                    db.flush()
                    if status == 'missed':
                        _ensure_followup(db, call)
                        if call.followup_created:
                            followups_created += 1
                    created += 1
                except IntegrityError:
                    db.rollback()
                    skipped += 1

            synced += 1

        # ── Cross-call staff propagation ─────────────────────────────────────
        # For each caller_number that has a known handled_by, propagate to all
        # other calls from the same number that don't have a staff assigned yet.
        try:
            from sqlalchemy import text as sa_text
            db.execute(sa_text("""
                UPDATE operator_calls dest
                SET handled_by = src.handled_by
                FROM (
                    SELECT DISTINCT ON (caller_number) caller_number, handled_by
                    FROM operator_calls
                    WHERE handled_by IS NOT NULL AND handled_by != ''
                      AND caller_number IS NOT NULL AND caller_number != ''
                    ORDER BY caller_number, started_at DESC
                ) src
                WHERE dest.caller_number = src.caller_number
                  AND (dest.handled_by IS NULL OR dest.handled_by = '')
            """))
            logger.info('[OPERATOR_SYNC] Cross-call staff propagation done')
        except Exception as prop_err:
            logger.warning('[OPERATOR_SYNC] Staff propagation error: %s', prop_err)

        db.commit()
        logger.info('[OPERATOR_SYNC] Sync complete: %d total, %d created, %d updated, %d skipped, %d followups', synced, created, updated, skipped, followups_created)
        result = {
            'synced': synced,
            'created': created,
            'updated': updated,
            'skipped': skipped,
            'followups_created': followups_created,
        }
        _last_sync.update({
            'ran_at': get_ist_now().isoformat(),
            'error': None,
            **result,
        })
        return result

    except Exception as e:
        try:
            db.rollback()
        except Exception:
            pass
        logger.error('[OPERATOR_SYNC] Sync failed: %s', e, exc_info=True)
        _last_sync.update({
            'ran_at': get_ist_now().isoformat(),
            'error': str(e),
            'synced': 0,
        })
        return {'error': str(e), 'synced': 0}

    finally:
        if close_db:
            db.close()


def run_operator_call_sync_job():
    """APScheduler job entry point — creates its own DB session (last 2 hours)."""
    logger.info('[OPERATOR_SYNC] Scheduled sync started (last 2 hours)')
    sync_myoperator_logs()


def run_operator_call_daily_backfill_job():
    """
    APScheduler daily backfill entry point — syncs last 30 days to fill all gaps.
    Runs at 9 AM IST daily via CronTrigger in scheduler.py.
    """
    logger.info('[OPERATOR_SYNC] Daily backfill started (last 30 days)')
    result = sync_myoperator_logs(days_back=30)
    logger.info('[OPERATOR_SYNC] Daily backfill done: %s', result)
