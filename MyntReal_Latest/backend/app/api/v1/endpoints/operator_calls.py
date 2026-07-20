"""
MyOperator Call Dashboard API Endpoints
DC Protocol: company_id scoped; staff-access only (menu-based).
Webhook: POST /api/v1/operator-calls/webhook  (no auth — MyOperator pushes events here)
Read:    GET  /api/v1/operator-calls/          (list with filters)
Detail:  GET  /api/v1/operator-calls/{call_id}/detail  (full detail + lead/followup info)
History: GET  /api/v1/operator-calls/caller-history/{phone}  (all calls for a phone number)
Actions: POST /api/v1/operator-calls/{call_id}/convert-lead
         POST /api/v1/operator-calls/{call_id}/create-followup
         POST /api/v1/operator-calls/{call_id}/match-lead   (manual lead match)
         POST /api/v1/operator-calls/{call_id}/add-note      (add note to linked lead)
         POST /api/v1/operator-calls/bulk-match              (bulk match unmatched calls)
Created: Mar 2026
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Body, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, or_, and_, text, case, literal_column
from typing import Optional, List
from datetime import datetime, timedelta
import pytz
import os
import re
import json
import hmac
import hashlib
import logging

from app.core.database import get_db
from app.core.security import get_current_user_hybrid
from app.models.operator_calls import OperatorCall
from app.models.crm import CRMLead, CRMLeadFollowUp, CRMLeadNote
from app.models.staff import StaffEmployee

logger = logging.getLogger(__name__)
router = APIRouter()

IST = pytz.timezone('Asia/Kolkata')

MYOPERATOR_COMPANY_ID = int(os.getenv('MYOPERATOR_COMPANY_ID', '1'))
MYOPERATOR_X_API_KEY = os.getenv('MYOPERATOR_X_API_KEY', '')
MYOPERATOR_API_COMPANY_ID = os.getenv('MYOPERATOR_API_COMPANY_ID', '')


def get_ist_now():
    return datetime.now(IST).replace(tzinfo=None)


def _get_staff_company_id(current_user) -> int:
    cid = getattr(current_user, 'base_company_id', None) or getattr(current_user, 'company_id', None)
    return int(cid) if cid else MYOPERATOR_COMPANY_ID


def _get_accessible_company_ids(current_user) -> list:
    """Returns all company IDs the user has access to (data_companies list)."""
    data_cos = getattr(current_user, 'data_companies', None)
    if data_cos and isinstance(data_cos, list):
        ids = [int(c) for c in data_cos if c]
        if ids:
            return ids
    cid = getattr(current_user, 'base_company_id', None) or getattr(current_user, 'company_id', None)
    return [int(cid)] if cid else [MYOPERATOR_COMPANY_ID]


def normalize_phone(phone: str) -> Optional[str]:
    if not phone:
        return None
    digits = re.sub(r'[^\d]', '', str(phone))
    if len(digits) > 10:
        digits = digits[-10:]
    return digits if len(digits) == 10 else None


def _match_lead(db: Session, phone: str, company_id: int = None) -> Optional[CRMLead]:
    norm = normalize_phone(phone)
    if not norm:
        return None
    cid = company_id or MYOPERATOR_COMPANY_ID
    lead = db.query(CRMLead).filter(
        or_(
            CRMLead.phone.like(f'%{norm}'),
            CRMLead.alternate_phone.like(f'%{norm}')
        ),
        CRMLead.company_id == cid
    ).order_by(CRMLead.created_at.desc()).first()
    return lead


def _lead_summary(db: Session, lead_id: int, company_id: int = None) -> Optional[dict]:
    q = db.query(CRMLead).filter(CRMLead.id == lead_id)
    if company_id:
        q = q.filter(CRMLead.company_id == company_id)
    lead = q.first()
    if not lead:
        return None
    d = lead.to_dict()
    followups = db.query(CRMLeadFollowUp).filter(
        CRMLeadFollowUp.lead_id == lead_id
    ).order_by(CRMLeadFollowUp.scheduled_date.desc()).limit(10).all()
    d['followups'] = [fu.to_dict() for fu in followups]
    notes = db.query(CRMLeadNote).filter(
        CRMLeadNote.lead_id == lead_id
    ).order_by(CRMLeadNote.created_at.desc()).limit(10).all()
    d['notes'] = [n.to_dict() for n in notes]
    return d


def _upsert_call(db: Session, call_id: str, payload: dict) -> OperatorCall:
    call = db.query(OperatorCall).filter(
        OperatorCall.company_id == MYOPERATOR_COMPANY_ID,
        OperatorCall.call_id == call_id
    ).first()
    now = get_ist_now()

    status_map = {
        'ringing': 'ringing',
        'ring': 'ringing',
        'answered': 'answered',
        'answer': 'answered',
        'missed': 'missed',
        'miss': 'missed',
        'hangup': 'ended',
        'ended': 'ended',
        'active': 'active',
    }

    raw_status = (payload.get('status') or payload.get('call_status') or 'ringing').lower()
    status = status_map.get(raw_status, raw_status)

    caller = payload.get('caller_id') or payload.get('caller') or payload.get('from') or ''
    called = payload.get('did') or payload.get('called') or payload.get('to') or ''
    op_name = payload.get('agent_name') or payload.get('operator_name') or ''
    op_number = payload.get('agent_number') or payload.get('operator_number') or ''
    duration = int(payload.get('duration') or payload.get('call_duration') or 0)
    recording_url = payload.get('recording_url') or payload.get('call_recording_url') or None
    call_type = (payload.get('call_type') or 'inbound').lower()

    recording_expires_at = None
    rec_exp_raw = payload.get('recording_expires_at') or payload.get('recording_expiry')
    if rec_exp_raw:
        try:
            recording_expires_at = datetime.fromisoformat(str(rec_exp_raw).replace('Z', '+00:00')).replace(tzinfo=None)
        except (ValueError, TypeError):
            pass
    # Do NOT guess expiry — MyOperator URLs need their session, not a timer.
    # We keep recording_url permanently in the DB; the Open Recording button handles auth.

    if not call:
        lead = _match_lead(db, caller)
        call = OperatorCall(
            call_id=call_id,
            company_id=MYOPERATOR_COMPANY_ID,
            caller_number=caller,
            called_number=called,
            operator_name=op_name,
            operator_number=op_number,
            call_type=call_type,
            status=status,
            started_at=now,
            crm_lead_id=lead.id if lead else None,
            lead_matched=bool(lead),
            recording_url=recording_url,
            recording_expires_at=recording_expires_at,
            raw_payload=json.dumps(payload)[:4000],
        )
        db.add(call)
    else:
        if not (call.answered_at and status in ('ended', 'hangup')):
            call.status = status
        call.duration_seconds = duration or call.duration_seconds
        call.operator_name = op_name or call.operator_name
        call.operator_number = op_number or call.operator_number
        if recording_url:
            call.recording_url = recording_url
            call.recording_expires_at = recording_expires_at
        if not call.lead_matched:
            lead = _match_lead(db, caller)
            if lead:
                call.crm_lead_id = lead.id
                call.lead_matched = True

    if status == 'answered' and not call.answered_at:
        call.answered_at = now
        call.status = 'answered'
    if status in ('ended', 'missed') and not call.ended_at:
        call.ended_at = now
        if duration:
            call.duration_seconds = duration
        if call.answered_at and status == 'ended':
            call.status = 'answered'
        elif status == 'missed':
            call.status = 'missed'
            if not call.missed_status:
                call.missed_status = 'pending'

    call.updated_at = now
    db.flush()
    return call


def _add_call_note_to_lead(db: Session, call: OperatorCall) -> bool:
    """
    DC-OPCALL-CALLNOTE-001: Post a [Call] comment to the matched lead's notes whenever
    an operator call reaches a terminal state (answered/ended/missed).
    Idempotent — guarded by call_note_posted flag (mirrors followup_created pattern).
    """
    if call.call_note_posted:
        return False
    if not call.crm_lead_id:
        return False

    lead = db.query(CRMLead).filter(
        CRMLead.id == call.crm_lead_id,
        CRMLead.company_id == call.company_id
    ).first()
    if not lead:
        return False

    status_label = call.status or 'call'
    parts = [f"[Call] {call.call_type or 'inbound'} {status_label}"]
    if call.operator_name:
        parts.append(f"— {call.operator_name}")
    if call.duration_seconds and call.duration_seconds > 0:
        parts.append(f"({call.duration_seconds}s)")

    note_obj = CRMLeadNote(
        company_id=lead.company_id,
        lead_id=lead.id,
        note=" ".join(parts),
        is_private=False,
        created_by_type='system',
        created_by_id='operator_webhook',
    )
    db.add(note_obj)
    db.flush()

    call.call_note_posted = True
    return True


def _create_auto_followup(db: Session, call: OperatorCall) -> Optional[CRMLeadFollowUp]:
    if call.followup_created:
        return None

    if not call.crm_lead_id:
        logger.info("[OPERATOR_WEBHOOK] Missed call %s from %s — no matching lead (unmatched)", call.call_id, call.caller_number)
        return None

    lead = db.query(CRMLead).filter(CRMLead.id == call.crm_lead_id, CRMLead.company_id == call.company_id).first()
    if not lead:
        return None

    now = get_ist_now()
    scheduled = now.replace(hour=10, minute=0, second=0, microsecond=0)
    if scheduled <= now:
        scheduled = now + timedelta(hours=2)

    fu = CRMLeadFollowUp(
        company_id=lead.company_id,
        lead_id=lead.id,
        followup_type='call',
        status='scheduled',
        scheduled_date=scheduled,
        subject=f'Missed call from {call.caller_number}',
        notes=f'Auto-created from missed operator call {call.call_id}. Caller: {call.caller_number}.',
        handler_type=lead.handler_type,
        handler_id=lead.handler_id,
        created_by_type='system',
        created_by_id='operator_webhook',
    )
    db.add(fu)
    db.flush()

    call.followup_created = True
    call.followup_id = fu.id
    return fu


# ── Webhook ────────────────────────────────────────────────────────────────────

def _verify_webhook_auth(request: Request, raw_body: bytes, payload: dict) -> bool:
    """
    Multi-layer webhook auth for MyOperator.
    MyOperator may send: body token, x-api-key header, or HMAC signature.
    Any ONE matching layer is sufficient to accept the request.
    Returns True if accepted, raises HTTPException if rejected.
    """
    webhook_secret = os.environ.get('MYOPERATOR_WEBHOOK_SECRET', '')
    api_token = os.environ.get('MYOPERATOR_API_TOKEN', '')
    x_api_key = os.environ.get('MYOPERATOR_X_API_KEY', '')

    any_auth_configured = bool(webhook_secret or api_token or x_api_key)

    if not any_auth_configured:
        logger.warning("[OPERATOR_WEBHOOK] No auth env vars configured — accepting (open mode)")
        return True

    # Layer 1: HMAC signature check (if secret configured AND header present)
    if webhook_secret:
        sig_header = (
            request.headers.get('X-MyOperator-Signature', '')
            or request.headers.get('x-webhook-signature', '')
            or request.headers.get('x-signature', '')
        ).strip()
        if sig_header:
            try:
                expected = hmac.new(webhook_secret.encode(), raw_body, hashlib.sha256).hexdigest()
                if hmac.compare_digest(sig_header, expected):
                    logger.debug("[OPERATOR_WEBHOOK] ✅ Auth via HMAC signature")
                    return True
            except Exception as _he:
                logger.warning("[OPERATOR_WEBHOOK] HMAC check error: %s", _he)

    # Layer 2: x-api-key header (MyOperator sends this for some account configs)
    if x_api_key:
        req_key = (
            request.headers.get('X-Api-Key', '')
            or request.headers.get('x-api-key', '')
        ).strip()
        if req_key and req_key == x_api_key:
            logger.debug("[OPERATOR_WEBHOOK] ✅ Auth via x-api-key header")
            return True

    # Layer 3: body `token` field (most common MyOperator webhook pattern)
    if api_token or x_api_key:
        body_token = str(payload.get('token', '') or payload.get('api_token', '')).strip()
        if body_token and body_token in (api_token, x_api_key):
            logger.debug("[OPERATOR_WEBHOOK] ✅ Auth via body token")
            return True

    # Layer 4: Authorization / x-api-token header
    if api_token:
        auth_header = (
            request.headers.get('Authorization', '')
            or request.headers.get('x-api-token', '')
        ).strip()
        if auth_header:
            if auth_header.replace('Bearer ', '').strip() == api_token:
                logger.debug("[OPERATOR_WEBHOOK] ✅ Auth via Authorization header")
                return True

    # All layers failed — log received headers for diagnosis (no secrets printed)
    recv_headers = {k: ('***' if any(s in k.lower() for s in ('auth', 'token', 'key', 'secret')) else v)
                    for k, v in request.headers.items()}
    logger.warning("[OPERATOR_WEBHOOK] ❌ Auth failed. Headers received: %s", recv_headers)
    raise HTTPException(status_code=403, detail="Webhook authentication failed")


@router.post("/webhook")
async def operator_call_webhook(
    request: Request,
    db: Session = Depends(get_db)
):
    raw_body = await request.body()

    # Parse body first so we can check body token in auth
    try:
        payload = json.loads(raw_body)
    except Exception:
        try:
            from urllib.parse import parse_qs
            qs = parse_qs(raw_body.decode('utf-8', errors='replace'))
            payload = {k: v[0] if len(v) == 1 else v for k, v in qs.items()}
        except Exception:
            payload = {}

    _verify_webhook_auth(request, raw_body, payload)

    if not payload:
        return {"success": False, "detail": "Empty payload"}

    call_id = (
        payload.get('call_id') or
        payload.get('uuid') or
        payload.get('session_id') or
        payload.get('call_uuid')
    )

    if not call_id:
        logger.warning("[OPERATOR_WEBHOOK] Missing call_id in payload: %s", json.dumps(payload)[:500])
        return {"success": False, "detail": "Missing call_id"}

    try:
        call = _upsert_call(db, str(call_id), payload)

        followup = None
        if call.status == 'missed':
            followup = _create_auto_followup(db, call)

        # DC-OPCALL-CALLNOTE-001: Post call record to lead comments on terminal states
        if call.status in ('answered', 'ended', 'missed') and call.crm_lead_id:
            _add_call_note_to_lead(db, call)

        db.commit()

        result = {
            "success": True,
            "call_id": call.call_id,
            "status": call.status,
            "db_id": call.id,
            "lead_matched": call.lead_matched,
        }
        if followup:
            result["followup_created"] = True
            result["followup_id"] = followup.id
        return result

    except Exception as e:
        try:
            db.rollback()
        except Exception:
            pass
        logger.error("[OPERATOR_WEBHOOK] Error processing webhook: %s", e, exc_info=True)
        return {"success": False, "detail": str(e)[:200]}


# ── List calls ─────────────────────────────────────────────────────────────────

@router.get("/")
async def list_operator_calls(
    status: Optional[str] = Query(None, description="Filter: active|answered|missed|ringing|ended"),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    caller: Optional[str] = Query(None, description="Partial phone number search"),
    operator: Optional[str] = Query(None, description="Filter by operator name or number"),
    call_type: Optional[str] = Query(None, description="Filter: inbound|outbound"),
    handled_by: Optional[str] = Query(None, description="Filter by staff/agent who handled the call"),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_hybrid)
):
    if not hasattr(current_user, 'emp_code'):
        raise HTTPException(status_code=403, detail="Staff access required")

    company_ids = _get_accessible_company_ids(current_user)

    query = db.query(OperatorCall).filter(
        OperatorCall.company_id.in_(company_ids)
    )

    if status:
        if status == 'active':
            query = query.filter(OperatorCall.status.in_(['ringing', 'active']))
        else:
            query = query.filter(OperatorCall.status == status)

    if call_type and call_type in ('inbound', 'outbound'):
        query = query.filter(OperatorCall.call_type == call_type)

    if operator:
        if operator == '__none__':
            query = query.filter(
                or_(OperatorCall.operator_name.is_(None), OperatorCall.operator_name == '')
            )
        else:
            query = query.filter(
                or_(
                    OperatorCall.operator_name.ilike(f'%{operator}%'),
                    OperatorCall.operator_number.like(f'%{operator}%')
                )
            )

    if caller:
        norm = normalize_phone(caller)
        search = norm or caller
        query = query.filter(
            or_(
                OperatorCall.caller_number.like(f'%{search}%'),
                OperatorCall.called_number.like(f'%{search}%'),
                OperatorCall.operator_name.ilike(f'%{search}%')
            )
        )

    if handled_by:
        if handled_by == '__none__':
            query = query.filter(
                or_(OperatorCall.handled_by.is_(None), OperatorCall.handled_by == '')
            )
        else:
            query = query.filter(OperatorCall.handled_by.ilike(f'%{handled_by}%'))

    if date_from:
        try:
            df = datetime.strptime(date_from, '%Y-%m-%d')
            query = query.filter(OperatorCall.started_at >= df)
        except ValueError:
            pass

    if date_to:
        try:
            dt = datetime.strptime(date_to, '%Y-%m-%d') + timedelta(days=1)
            query = query.filter(OperatorCall.started_at < dt)
        except ValueError:
            pass

    total = query.count()
    calls = query.order_by(OperatorCall.started_at.desc()).offset((page - 1) * per_page).limit(per_page).all()

    active_count = db.query(func.count(OperatorCall.id)).filter(
        OperatorCall.company_id.in_(company_ids),
        OperatorCall.status.in_(['ringing', 'active'])
    ).scalar() or 0

    answered_count = db.query(func.count(OperatorCall.id)).filter(
        OperatorCall.company_id.in_(company_ids),
        OperatorCall.status == 'answered'
    ).scalar() or 0

    missed_count = db.query(func.count(OperatorCall.id)).filter(
        OperatorCall.company_id.in_(company_ids),
        OperatorCall.status == 'missed'
    ).scalar() or 0

    voicemail_count = db.query(func.count(OperatorCall.id)).filter(
        OperatorCall.company_id.in_(company_ids),
        OperatorCall.status == 'voicemail'
    ).scalar() or 0

    pending_count = db.query(func.count(OperatorCall.id)).filter(
        OperatorCall.company_id.in_(company_ids),
        OperatorCall.status == 'missed',
        OperatorCall.missed_status == 'pending'
    ).scalar() or 0

    disposed_count = db.query(func.count(OperatorCall.id)).filter(
        OperatorCall.company_id.in_(company_ids),
        OperatorCall.status == 'missed',
        OperatorCall.missed_status == 'disposed'
    ).scalar() or 0

    # Collect all caller phones for batch existing_in lookup
    caller_phones = list({c.caller_number for c in calls if c.caller_number})
    existing_in_map: dict = {}
    if caller_phones:
        try:
            for raw_phone in caller_phones:
                digits = re.sub(r'[^\d]', '', str(raw_phone))
                last10 = digits[-10:] if len(digits) >= 10 else digits
                if not last10:
                    existing_in_map[raw_phone] = [{"type": "new", "label": "New"}]
                    continue
                p10 = f"%{last10}"
                presence = []
                resolved_name = None

                # CRM lead
                crm = db.execute(text("""
                    SELECT cl.id, cl.name, cl.status, cl.handler_type, cl.handler_id,
                           TRIM(COALESCE(se.first_name,'') || ' ' || COALESCE(se.last_name,'')) AS owner
                    FROM crm_leads cl
                    LEFT JOIN staff_employees se ON se.emp_code = cl.handler_id AND cl.handler_type = 'staff'
                    WHERE cl.phone LIKE :p OR cl.alternate_phone LIKE :p
                    ORDER BY cl.id DESC LIMIT 1
                """), {"p": p10}).fetchone()
                if crm:
                    resolved_name = crm[1]
                    with_whom = (crm[5] or "").strip() or crm[4] or None
                    presence.append({"type": "crm", "label": "CRM", "id": crm[0], "status": crm[2], "with_whom": with_whom})

                # Walk-in
                wi = db.execute(text("""
                    SELECT id, customer_name, assigned_to, status
                    FROM partner_walkins
                    WHERE customer_phone LIKE :p OR alternate_phone LIKE :p
                    ORDER BY id DESC LIMIT 1
                """), {"p": p10}).fetchone()
                if wi:
                    if not resolved_name:
                        resolved_name = wi[1]
                    presence.append({"type": "walkin", "label": "Walk-in", "id": wi[0], "status": wi[3], "with_whom": wi[2]})

                # Service ticket
                st = db.execute(text("""
                    SELECT st.id, st.status, st.ticket_id,
                           TRIM(COALESCE(se.first_name,'') || ' ' || COALESCE(se.last_name,'')) AS tech
                    FROM service_ticket st
                    LEFT JOIN staff_employees se ON se.id = st.service_technician_id
                    WHERE st.customer_phone LIKE :p
                    ORDER BY st.id DESC LIMIT 1
                """), {"p": p10}).fetchone()
                if st:
                    presence.append({"type": "service", "label": "Service", "id": st[0], "ticket_ref": st[2], "status": st[1], "with_whom": (st[3] or "").strip() or None})

                # Staff contacts
                sc = db.execute(text("""
                    SELECT scl.contact_name,
                           TRIM(COALESCE(se.first_name,'') || ' ' || COALESCE(se.last_name,'')) AS staff_name
                    FROM staff_call_logs scl
                    LEFT JOIN staff_employees se ON se.id = scl.staff_id
                    WHERE scl.phone_number LIKE :p AND scl.contact_name IS NOT NULL
                    ORDER BY scl.id DESC LIMIT 1
                """), {"p": p10}).fetchone()
                if sc:
                    if not resolved_name:
                        resolved_name = sc[0]
                    presence.append({"type": "contacts", "label": "Contacts", "contact_name": sc[0], "with_whom": (sc[1] or "").strip() or None})

                if not presence:
                    presence.append({"type": "new", "label": "New"})

                existing_in_map[raw_phone] = presence
                if resolved_name:
                    existing_in_map[raw_phone + "__name"] = resolved_name
        except Exception as _eie:
            logger.warning("existing_in batch lookup error: %s", _eie)

    call_data = []
    for c in calls:
        d = c.to_dict()
        if c.crm_lead_id:
            lead = db.query(CRMLead).filter(CRMLead.id == c.crm_lead_id, CRMLead.company_id.in_(company_ids)).first()
            if lead:
                d['lead_name'] = lead.name
                d['lead_status'] = lead.status
                d['lead_phone'] = lead.phone
                d['lead_source'] = lead.source
                # Resolve lead owner name from handler
                lead_owner = None
                if lead.handler_type == 'staff' and lead.handler_id:
                    staff = db.query(StaffEmployee).filter(StaffEmployee.emp_code == lead.handler_id).first()
                    if staff:
                        lead_owner = staff.full_name
                    else:
                        lead_owner = lead.handler_id
                elif lead.handler_type and lead.handler_type != 'unassigned':
                    lead_owner = lead.handler_id or lead.handler_type
                d['lead_owner'] = lead_owner
        # Attach existing_in presence chips
        cp = c.caller_number or ""
        d['existing_in'] = existing_in_map.get(cp, [{"type": "new", "label": "New"}])
        d['caller_resolved_name'] = existing_in_map.get(cp + "__name")
        call_data.append(d)

    return {
        "success": True,
        "data": call_data,
        "stats": {
            "active": active_count,
            "answered": answered_count,
            "missed": missed_count,
            "voicemail": voicemail_count,
            "total": answered_count + missed_count + voicemail_count + active_count,
            "pending": pending_count,
            "disposed": disposed_count,
        },
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total": total,
            "pages": (total + per_page - 1) // per_page if total > 0 else 0,
        }
    }


# ── Staff List (for salesperson assignment dropdown) ──────────────────────────

@router.get("/staff-list")
async def get_staff_list(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_hybrid)
):
    if not hasattr(current_user, 'emp_code'):
        raise HTTPException(status_code=403, detail="Staff access required")

    company_ids = _get_accessible_company_ids(current_user)

    employees = db.query(StaffEmployee).filter(
        StaffEmployee.base_company_id.in_(company_ids),
        StaffEmployee.status == 'active'
    ).order_by(StaffEmployee.full_name).all()

    return {
        "success": True,
        "data": [
            {
                "id": e.id,
                "emp_code": e.emp_code,
                "name": e.full_name,
                "designation": e.role.role_name if getattr(e, 'role', None) else None,
                "department": e.department.name if getattr(e, 'department', None) else None,
            }
            for e in employees
        ]
    }


# ── Handled-By List (unique agent names who handled calls — for filter dropdown) ─

@router.get("/handled-by-list")
async def get_handled_by_list(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_hybrid)
):
    if not hasattr(current_user, 'emp_code'):
        raise HTTPException(status_code=403, detail="Staff access required")

    company_ids = _get_accessible_company_ids(current_user)

    rows = db.query(OperatorCall.handled_by).filter(
        OperatorCall.company_id.in_(company_ids),
        OperatorCall.handled_by.isnot(None),
        OperatorCall.handled_by != ''
    ).distinct().order_by(OperatorCall.handled_by).all()

    agents = sorted(set(r.handled_by for r in rows if r.handled_by))
    return {"success": True, "data": agents}


# ── Dispose / Un-dispose missed call ──────────────────────────────────────────

@router.patch("/{call_id}/missed-status")
async def update_missed_status(
    call_id: str,
    body: dict,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_hybrid)
):
    if not hasattr(current_user, 'emp_code'):
        raise HTTPException(status_code=403, detail="Staff access required")

    new_status = (body.get('missed_status') or '').strip().lower()
    if new_status not in ('pending', 'disposed'):
        raise HTTPException(status_code=400, detail="missed_status must be 'pending' or 'disposed'")

    company_ids = _get_accessible_company_ids(current_user)
    call = db.query(OperatorCall).filter(
        OperatorCall.call_id == call_id,
        OperatorCall.company_id.in_(company_ids),
        OperatorCall.status == 'missed'
    ).first()
    if not call:
        raise HTTPException(status_code=404, detail="Missed call not found")

    call.missed_status = new_status
    db.commit()
    return {"success": True, "call_id": call_id, "missed_status": new_status}


# ── Recording Proxy (bypasses CORS; streams audio from MyOperator) ────────────
# DC_REC_PROXY: MyOperator recordings require a valid web session.
# The proxy uses MYOPERATOR_WEB_SESSION env var (cookie string from a logged-in
# browser session) to fetch recordings server-side.
# How to set up: Log into in.app.myoperator.com, open DevTools > Application >
# Cookies > in.app.myoperator.com, copy ALL cookies as a semicolon-separated
# string, set as MYOPERATOR_WEB_SESSION env var.

@router.get("/{call_id}/recording-proxy")
async def recording_proxy(
    call_id: str,
    token: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_hybrid)
):
    import httpx
    import os as _os
    myop_session = _os.getenv('MYOPERATOR_WEB_SESSION', '')

    company_ids = _get_accessible_company_ids(current_user)
    call = db.query(OperatorCall).filter(
        OperatorCall.call_id == call_id,
        OperatorCall.company_id.in_(company_ids)
    ).first()
    if not call or not call.recording_url:
        raise HTTPException(status_code=404, detail="Recording not found")

    recording_url = call.recording_url
    # Convert app.myoperator.com → in.app.myoperator.com (correct subdomain)
    recording_url = recording_url.replace('https://app.myoperator.com/', 'https://in.app.myoperator.com/')

    request_headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        "Accept": "audio/webm,audio/ogg,audio/wav,audio/*;q=0.9,application/ogg;q=0.7,video/*;q=0.6,*/*;q=0.5",
        "Referer": "https://in.app.myoperator.com/",
        "Origin": "https://in.app.myoperator.com",
    }
    if myop_session:
        request_headers["Cookie"] = myop_session

    try:
        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            resp = await client.get(recording_url, headers=request_headers)

            content_type = resp.headers.get("content-type", "")
            # Detect login-page redirect (HTML response instead of audio)
            if resp.status_code not in (200, 206) or "text/html" in content_type:
                if not myop_session:
                    raise HTTPException(
                        status_code=503,
                        detail="RECORDING_SESSION_REQUIRED: Set MYOPERATOR_WEB_SESSION env var. Log into in.app.myoperator.com, copy all cookies from DevTools, paste as semicolon-separated string."
                    )
                raise HTTPException(
                    status_code=503,
                    detail="RECORDING_SESSION_EXPIRED: MyOperator session cookie has expired. Refresh MYOPERATOR_WEB_SESSION env var."
                )

            content = resp.content
            if not content_type:
                content_type = "audio/mpeg"

        async def audio_stream():
            yield content

        return StreamingResponse(
            audio_stream(),
            media_type=content_type,
            headers={
                "Content-Length": str(len(content)),
                "Accept-Ranges": "bytes",
                "Cache-Control": "private, max-age=3600",
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("[RECORDING_PROXY] Error fetching recording: %s", e)
        raise HTTPException(status_code=502, detail="Failed to fetch recording")


# ── Follow-up List (all follow-ups created from operator calls) ───────────────

@router.get("/followups")
async def list_call_followups(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    fu_status: Optional[str] = Query(None, alias="status"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_hybrid)
):
    if not hasattr(current_user, 'emp_code'):
        raise HTTPException(status_code=403, detail="Staff access required")

    company_ids = _get_accessible_company_ids(current_user)

    query = db.query(OperatorCall).filter(
        OperatorCall.company_id.in_(company_ids),
        OperatorCall.followup_id.isnot(None)
    )

    total = query.count()
    calls = query.order_by(OperatorCall.created_at.desc()).offset((page - 1) * per_page).limit(per_page).all()

    result = []
    for c in calls:
        fu = db.query(CRMLeadFollowUp).filter(CRMLeadFollowUp.id == c.followup_id).first()
        if fu:
            if fu_status and fu.status != fu_status:
                continue
            d = c.to_dict()
            d['followup'] = fu.to_dict()
            if c.crm_lead_id:
                lead = db.query(CRMLead).filter(CRMLead.id == c.crm_lead_id).first()
                if lead:
                    d['lead_name'] = lead.name
            result.append(d)

    return {
        "success": True,
        "data": result,
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total": total,
            "pages": (total + per_page - 1) // per_page if total > 0 else 0,
        }
    }


# ── Call Detail (full view with lead info, followups, notes) ──────────────────

@router.get("/{call_id}/detail")
async def get_call_detail(
    call_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_hybrid)
):
    if not hasattr(current_user, 'emp_code'):
        raise HTTPException(status_code=403, detail="Staff access required")

    company_ids = _get_accessible_company_ids(current_user)

    call = db.query(OperatorCall).filter(
        OperatorCall.company_id.in_(company_ids),
        OperatorCall.call_id == call_id
    ).first()
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")

    d = call.to_dict()

    if call.recording_url and call.recording_expires_at:
        now = get_ist_now()
        if call.recording_expires_at < now:
            d['recording_expired'] = True
        else:
            d['recording_expired'] = False
            d['recording_expires_in_seconds'] = int((call.recording_expires_at - now).total_seconds())
    elif call.recording_url:
        d['recording_expired'] = False

    caller_history = db.query(OperatorCall).filter(
        OperatorCall.company_id.in_(company_ids),
        or_(
            OperatorCall.caller_number == call.caller_number,
            OperatorCall.called_number == call.caller_number
        ),
        OperatorCall.call_id != call.call_id
    ).order_by(OperatorCall.created_at.desc()).limit(20).all()

    d['caller_history'] = [h.to_dict() for h in caller_history]
    d['caller_total_calls'] = len(caller_history) + 1

    caller_stats = {
        'total_calls': len(caller_history) + 1,
        'answered': sum(1 for h in caller_history if h.status == 'answered') + (1 if call.status == 'answered' else 0),
        'missed': sum(1 for h in caller_history if h.status == 'missed') + (1 if call.status == 'missed' else 0),
        'total_duration': sum(h.duration_seconds or 0 for h in caller_history) + (call.duration_seconds or 0),
    }
    d['caller_stats'] = caller_stats

    if call.crm_lead_id:
        d['lead'] = _lead_summary(db, call.crm_lead_id, company_id=company_ids[0] if company_ids else MYOPERATOR_COMPANY_ID)
    else:
        lead = _match_lead(db, call.caller_number, company_id=company_ids[0] if company_ids else MYOPERATOR_COMPANY_ID)
        if lead:
            d['potential_lead'] = {
                'id': lead.id,
                'name': lead.name,
                'phone': lead.phone,
                'status': lead.status,
                'source': lead.source,
            }

    if call.followup_id:
        fu = db.query(CRMLeadFollowUp).filter(CRMLeadFollowUp.id == call.followup_id).first()
        if fu:
            d['followup'] = fu.to_dict()

    return {
        "success": True,
        "data": d
    }


# ── Caller History (all calls from/to a phone number) ────────────────────────

@router.get("/caller-history/{phone}")
async def caller_history(
    phone: str,
    page: int = Query(1, ge=1),
    per_page: int = Query(30, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_hybrid)
):
    if not hasattr(current_user, 'emp_code'):
        raise HTTPException(status_code=403, detail="Staff access required")

    company_ids = _get_accessible_company_ids(current_user)
    # DC-CALLHIST-SCOPE-001: Always include MYOPERATOR_COMPANY_ID so staff from any
    # sub-company can see operator call history regardless of their base_company_id.
    if MYOPERATOR_COMPANY_ID not in company_ids:
        company_ids = list(company_ids) + [MYOPERATOR_COMPANY_ID]

    norm = normalize_phone(phone)
    search = norm or phone

    query = db.query(OperatorCall).filter(
        OperatorCall.company_id.in_(company_ids),
        or_(
            OperatorCall.caller_number.like(f'%{search}%'),
            OperatorCall.called_number.like(f'%{search}%')
        )
    )

    total = query.count()
    calls = query.order_by(OperatorCall.created_at.desc()).offset((page - 1) * per_page).limit(per_page).all()

    stats = {
        'total': total,
        'answered': sum(1 for c in calls if c.status == 'answered'),
        'missed': sum(1 for c in calls if c.status == 'missed'),
        'total_duration': sum(c.duration_seconds or 0 for c in calls),
        'first_call': calls[-1].created_at.isoformat() if calls else None,
        'last_call': calls[0].created_at.isoformat() if calls else None,
    }

    lead = _match_lead(db, phone, company_id=company_ids[0] if company_ids else MYOPERATOR_COMPANY_ID)
    lead_info = None
    if lead:
        lead_info = {
            'id': lead.id,
            'name': lead.name,
            'phone': lead.phone,
            'status': lead.status,
            'source': lead.source,
            'priority': getattr(lead, 'priority', None),
            'handler_type': lead.handler_type,
        }

    return {
        "success": True,
        "phone": phone,
        "data": [c.to_dict() for c in calls],
        "stats": stats,
        "lead": lead_info,
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total": total,
            "pages": (total + per_page - 1) // per_page if total > 0 else 0,
        }
    }


# ── Convert call to CRM Lead ───────────────────────────────────────────────────

@router.post("/{call_id}/convert-lead")
async def convert_to_lead(
    call_id: str,
    body: dict = Body(default={}),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_hybrid)
):
    if not hasattr(current_user, 'emp_code'):
        raise HTTPException(status_code=403, detail="Staff access required")

    company_ids = _get_accessible_company_ids(current_user)

    call = db.query(OperatorCall).filter(
        OperatorCall.company_id.in_(company_ids),
        OperatorCall.call_id == call_id
    ).first()
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")

    if call.crm_lead_id:
        existing = db.query(CRMLead).filter(CRMLead.id == call.crm_lead_id, CRMLead.company_id.in_(company_ids)).first()
        if existing:
            return {
                "success": True,
                "lead_id": existing.id,
                "message": "Lead already linked",
                "lead": existing.to_dict()
            }

    name = body.get('name') or f'Caller {call.caller_number}'
    handler_id = body.get('handler_id')
    handler_type = 'staff' if handler_id else 'unassigned'
    lead = CRMLead(
        company_id=call.company_id,
        name=name,
        phone=call.caller_number,
        source='Operator Call',
        source_details=f'Converted from operator call {call.call_id}',
        status='new',
        priority='medium',
        handler_type=handler_type,
        handler_id=int(handler_id) if handler_id else None,
        created_by_type='staff',
        created_by_id=str(current_user.id),
    )
    db.add(lead)
    db.flush()

    call.crm_lead_id = lead.id
    call.lead_matched = True

    if call.recording_url:
        note = CRMLeadNote(
            company_id=lead.company_id,
            lead_id=lead.id,
            note=f'Operator call recording: {call.recording_url}',
            created_by_type='system',
            created_by_id='operator_calls',
        )
        db.add(note)

    db.commit()
    db.refresh(lead)

    return {
        "success": True,
        "lead_id": lead.id,
        "message": "Lead created successfully",
        "lead": lead.to_dict()
    }


# ── Manual lead match ─────────────────────────────────────────────────────────

@router.post("/{call_id}/match-lead")
async def match_lead_to_call(
    call_id: str,
    body: dict = Body(default={}),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_hybrid)
):
    if not hasattr(current_user, 'emp_code'):
        raise HTTPException(status_code=403, detail="Staff access required")

    company_ids = _get_accessible_company_ids(current_user)

    call = db.query(OperatorCall).filter(
        OperatorCall.company_id.in_(company_ids),
        OperatorCall.call_id == call_id
    ).first()
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")

    lead_id = body.get('lead_id')
    if lead_id:
        lead = db.query(CRMLead).filter(
            CRMLead.id == int(lead_id),
            CRMLead.company_id.in_(company_ids)
        ).first()
    else:
        lead = _match_lead(db, call.caller_number, company_id=company_ids[0] if company_ids else MYOPERATOR_COMPANY_ID)

    if not lead:
        return {
            "success": False,
            "detail": "No matching lead found for this phone number"
        }

    call.crm_lead_id = lead.id
    call.lead_matched = True
    call.updated_at = get_ist_now()
    db.commit()

    return {
        "success": True,
        "lead_id": lead.id,
        "lead_name": lead.name,
        "message": f"Call linked to lead: {lead.name}"
    }


# ── Add note to linked lead ──────────────────────────────────────────────────

@router.post("/{call_id}/add-note")
async def add_note_to_call_lead(
    call_id: str,
    body: dict = Body(default={}),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_hybrid)
):
    if not hasattr(current_user, 'emp_code'):
        raise HTTPException(status_code=403, detail="Staff access required")

    company_ids = _get_accessible_company_ids(current_user)

    call = db.query(OperatorCall).filter(
        OperatorCall.company_id.in_(company_ids),
        OperatorCall.call_id == call_id
    ).first()
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")

    if not call.crm_lead_id:
        raise HTTPException(status_code=400, detail="No CRM lead linked to this call")

    note_text = body.get('note', '').strip()
    if not note_text:
        raise HTTPException(status_code=400, detail="Note text is required")

    note = CRMLeadNote(
        company_id=call.company_id,
        lead_id=call.crm_lead_id,
        note=note_text,
        created_by_type='staff',
        created_by_id=str(current_user.id),
    )
    db.add(note)
    db.commit()
    db.refresh(note)

    return {
        "success": True,
        "note_id": note.id,
        "message": "Note added to lead"
    }


# ── Create follow-up manually ──────────────────────────────────────────────────

@router.post("/{call_id}/create-followup")
async def create_followup(
    call_id: str,
    body: dict = Body(default={}),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_hybrid)
):
    if not hasattr(current_user, 'emp_code'):
        raise HTTPException(status_code=403, detail="Staff access required")

    company_ids = _get_accessible_company_ids(current_user)

    call = db.query(OperatorCall).filter(
        OperatorCall.company_id.in_(company_ids),
        OperatorCall.call_id == call_id
    ).first()
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")

    if not call.crm_lead_id:
        lead = _match_lead(db, call.caller_number, company_id=company_ids[0] if company_ids else MYOPERATOR_COMPANY_ID)
        if lead:
            call.crm_lead_id = lead.id
            call.lead_matched = True
        else:
            name = body.get('lead_name') or f'Caller {call.caller_number}'
            lead = CRMLead(
                company_id=call.company_id,
                name=name,
                phone=call.caller_number,
                source='Operator Call',
                source_details=f'Auto-created for follow-up from call {call.call_id}',
                status='new',
                priority='medium',
                handler_type='unassigned',
                created_by_type='staff',
                created_by_id=str(current_user.id),
            )
            db.add(lead)
            db.flush()
            call.crm_lead_id = lead.id
            call.lead_matched = True

    lead = db.query(CRMLead).filter(CRMLead.id == call.crm_lead_id, CRMLead.company_id.in_(company_ids)).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Linked lead not found")

    now = get_ist_now()
    scheduled_raw = body.get('scheduled_date')
    if scheduled_raw:
        try:
            scheduled = datetime.fromisoformat(str(scheduled_raw).replace('Z', '+00:00'))
            if scheduled.tzinfo:
                scheduled = scheduled.astimezone(IST).replace(tzinfo=None)
        except Exception:
            scheduled = now + timedelta(hours=2)
    else:
        scheduled = now + timedelta(hours=2)

    fu = CRMLeadFollowUp(
        company_id=lead.company_id,
        lead_id=lead.id,
        followup_type='call',
        status='scheduled',
        scheduled_date=scheduled,
        subject=body.get('subject') or f'Follow up on call from {call.caller_number}',
        notes=body.get('notes') or f'Operator call {call.call_id}. Caller: {call.caller_number}.',
        handler_type=lead.handler_type,
        handler_id=lead.handler_id,
        created_by_type='staff',
        created_by_id=str(current_user.id),
    )
    db.add(fu)
    db.flush()

    call.followup_created = True
    call.followup_id = fu.id

    db.commit()
    db.refresh(fu)

    return {
        "success": True,
        "followup_id": fu.id,
        "lead_id": lead.id,
        "message": "Follow-up created successfully",
        "followup": fu.to_dict()
    }


# ── Bulk match unmatched calls to CRM leads ──────────────────────────────────

@router.post("/bulk-match")
async def bulk_match_leads(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_hybrid)
):
    if not hasattr(current_user, 'emp_code'):
        raise HTTPException(status_code=403, detail="Staff access required")

    company_ids = _get_accessible_company_ids(current_user)

    unmatched = db.query(OperatorCall).filter(
        OperatorCall.company_id.in_(company_ids),
        OperatorCall.lead_matched == False,
        OperatorCall.caller_number.isnot(None),
        OperatorCall.caller_number != ''
    ).all()

    matched = 0
    for call in unmatched:
        lead = _match_lead(db, call.caller_number, company_id=company_ids[0] if company_ids else MYOPERATOR_COMPANY_ID)
        if lead:
            call.crm_lead_id = lead.id
            call.lead_matched = True
            call.updated_at = get_ist_now()
            matched += 1

    db.commit()

    return {
        "success": True,
        "total_unmatched": len(unmatched),
        "matched": matched,
        "still_unmatched": len(unmatched) - matched,
        "message": f"Matched {matched} calls to CRM leads"
    }


# ── Department-wise Report ────────────────────────────────────────────────────

@router.get("/reports/department-wise")
async def department_wise_report(
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_hybrid)
):
    if not hasattr(current_user, 'emp_code'):
        raise HTTPException(status_code=403, detail="Staff access required")

    company_ids = _get_accessible_company_ids(current_user)

    query = db.query(OperatorCall).filter(
        OperatorCall.company_id.in_(company_ids)
    )
    if date_from:
        try:
            from datetime import date as _date
            df = datetime.strptime(date_from, '%Y-%m-%d')
            query = query.filter(OperatorCall.started_at >= df)
        except Exception:
            pass
    if date_to:
        try:
            dt = datetime.strptime(date_to, '%Y-%m-%d') + timedelta(days=1)
            query = query.filter(OperatorCall.started_at < dt)
        except Exception:
            pass

    calls = query.all()

    groups: dict = {}
    for c in calls:
        key = (c.operator_name or '').strip() or '(Unknown Department)'
        if key not in groups:
            groups[key] = {'department': key, 'total': 0, 'answered': 0, 'missed': 0, 'voicemail': 0, 'total_duration': 0}
        g = groups[key]
        g['total'] += 1
        if c.status == 'answered':
            g['answered'] += 1
            g['total_duration'] += c.duration_seconds or 0
        elif c.status == 'missed':
            g['missed'] += 1
        elif c.status == 'voicemail':
            g['voicemail'] += 1

    rows = []
    for g in sorted(groups.values(), key=lambda x: -x['total']):
        answered = g['answered'] or 0
        g['avg_duration'] = round(g['total_duration'] / answered) if answered else 0
        rows.append(g)

    totals = {
        'total': sum(r['total'] for r in rows),
        'answered': sum(r['answered'] for r in rows),
        'missed': sum(r['missed'] for r in rows),
        'voicemail': sum(r['voicemail'] for r in rows),
        'total_duration': sum(r['total_duration'] for r in rows),
    }
    totals['avg_duration'] = round(totals['total_duration'] / totals['answered']) if totals['answered'] else 0

    return {"success": True, "data": rows, "totals": totals}


# ── Person-wise Report ────────────────────────────────────────────────────────

@router.get("/reports/person-wise")
async def person_wise_report(
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_hybrid)
):
    if not hasattr(current_user, 'emp_code'):
        raise HTTPException(status_code=403, detail="Staff access required")

    company_ids = _get_accessible_company_ids(current_user)

    query = db.query(OperatorCall).filter(
        OperatorCall.company_id.in_(company_ids)
    )
    if date_from:
        try:
            df = datetime.strptime(date_from, '%Y-%m-%d')
            query = query.filter(OperatorCall.started_at >= df)
        except Exception:
            pass
    if date_to:
        try:
            dt = datetime.strptime(date_to, '%Y-%m-%d') + timedelta(days=1)
            query = query.filter(OperatorCall.started_at < dt)
        except Exception:
            pass

    calls = query.all()

    groups: dict = {}
    for c in calls:
        key = (c.handled_by or '').strip() or '(Unhandled)'
        if key not in groups:
            groups[key] = {'person': key, 'total': 0, 'answered': 0, 'missed': 0, 'voicemail': 0, 'total_duration': 0}
        g = groups[key]
        g['total'] += 1
        if c.status == 'answered':
            g['answered'] += 1
            g['total_duration'] += c.duration_seconds or 0
        elif c.status == 'missed':
            g['missed'] += 1
        elif c.status == 'voicemail':
            g['voicemail'] += 1

    rows = []
    for g in sorted(groups.values(), key=lambda x: -x['total']):
        answered = g['answered'] or 0
        g['avg_duration'] = round(g['total_duration'] / answered) if answered else 0
        rows.append(g)

    totals = {
        'total': sum(r['total'] for r in rows),
        'answered': sum(r['answered'] for r in rows),
        'missed': sum(r['missed'] for r in rows),
        'voicemail': sum(r['voicemail'] for r in rows),
        'total_duration': sum(r['total_duration'] for r in rows),
    }
    totals['avg_duration'] = round(totals['total_duration'] / totals['answered']) if totals['answered'] else 0

    return {"success": True, "data": rows, "totals": totals}


# ── Sync status ────────────────────────────────────────────────────────────────

@router.get("/sync-status")
async def get_sync_status(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_hybrid)
):
    if not hasattr(current_user, 'emp_code'):
        raise HTTPException(status_code=403, detail="Staff access required")
    from app.services.operator_call_sync import get_last_sync_status
    status = get_last_sync_status()
    return {"success": True, "sync_status": status}


# ── Manual sync trigger (admin) ────────────────────────────────────────────────

@router.post("/sync")
async def trigger_manual_sync(
    days_back: int = Query(0, ge=0, le=30, description="Hours to look back (0=default 2h, 1-30=days)"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_hybrid)
):
    if not hasattr(current_user, 'emp_code'):
        raise HTTPException(status_code=403, detail="Staff access required")

    try:
        from app.services.operator_call_sync import sync_myoperator_logs
        result = sync_myoperator_logs(db, days_back=days_back if days_back > 0 else None)
        return {"success": True, "result": result}
    except Exception as e:
        logger.error("[OPERATOR_SYNC] Manual sync error: %s", e, exc_info=True)
        return {"success": False, "detail": str(e)[:300]}
