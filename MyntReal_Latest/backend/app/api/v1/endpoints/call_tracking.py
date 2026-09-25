"""
Staff Call Tracking System API Endpoints
DC Protocol: Menu-based access control - page assignment = full access
Created: Feb 2026

Features:
- Sync call logs from mobile devices (native call history)
- Auto-match phone numbers with CRM leads
- Per-lead call history retrieval
- Staff call analytics dashboard
- Management overview with per-staff stats
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Body, UploadFile, File, Form, Request
from fastapi.responses import FileResponse, StreamingResponse, RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, text, and_, or_, case, distinct
from app.core.database import get_db
from app.core.security import get_current_user_hybrid
from app.models.call_tracking import StaffCallLog, StaffCallSyncLog, StaffCallRecording
from app.models.crm import CRMLead, CRMLeadNote
from app.models.signup_category import SignupCategory
from app.models.staff import StaffEmployee, StaffDepartment
from app.models.staff_attendance import StaffAttendance, StaffActivityTimeLog
from app.models.staff_kra import StaffKRADailyInstance
from app.utils.staff_hierarchy import get_team_member_ids
from app.api.v1.endpoints.crm_dialer import _resolve_phones_batch

# CT Protocol: Roles with full org visibility in call tracking (not limited to their downline)
CT_FULL_ACCESS = {
    'vgk4u', 'key_leadership', 'leadership_role', 'ea', 'hr', 'accounts',
    'super_admin', 'admin', 'management', 'director'
}


def is_ct_full_access(user) -> bool:
    """Determine if user has unrestricted organization-wide visibility in call tracking."""
    if not user:
        return False
    if getattr(user, 'emp_code', '') == 'MR10001':
        return True
    staff_type = (getattr(user, 'staff_type', '') or '').upper()
    if staff_type in {'VGK4U', 'ADMIN', 'SUPERADMIN', 'SUPER_ADMIN', 'CHIEF_EXECUTIVE', 'EXECUTIVE_DIRECTOR', 'DIRECTOR', 'LEADERSHIP', 'HR', 'ACCOUNTS', 'MANAGEMENT'}:
        return True
    if getattr(user, 'admin_scope', None) in ('PLATFORM', 'GLOBAL_SUPERADMIN', 'COMPANY_ADMIN'):
        return True
    ct_role = user.role.role_code.lower() if hasattr(user, 'role') and user.role and getattr(user.role, 'role_code', None) else None
    if ct_role in CT_FULL_ACCESS:
        return True
    return False


def resolve_call_tracking_scope(db: Session, current_user):
    """
    Multi-tenant isolation for call tracking.
    Returns (is_saas: bool, allowed_staff_ids: list[int], allowed_company_ids: list[int]).
    - If user belongs to SaaS tenant:
        - Scopes staff to only tenant staff.
        - If tenant_admin, allowed_staff_ids = all active tenant staff IDs.
        - If non-admin staff, allowed_staff_ids = downline intersected with tenant staff IDs (or [current_user.id]).
        - Scopes companies to only tenant company IDs.
    - If internal platform user:
        - Returns (False, [], []).
    """
    from app.services.saas_tenant_resolver import resolve_tenant_context
    from app.models.staff_accounts import AssociatedCompany

    staff = current_user if isinstance(current_user, StaffEmployee) else db.query(StaffEmployee).filter(StaffEmployee.id == current_user.id).first()
    if not staff:
        return False, [], []

    tenant_ctx = resolve_tenant_context(db, staff)
    if not tenant_ctx.is_saas_tenant:
        return False, [], []

    # Enforce CRM & Leads module entitlement for SaaS tenant
    tenant_ctx.require_module('CRM_LEADS')

    # SaaS Tenant scoping
    company_ids = []
    if tenant_ctx.client:
        tenant_cos = db.query(AssociatedCompany.id).filter(AssociatedCompany.client_id == tenant_ctx.client.id).all()
        company_ids = [c[0] for c in tenant_cos]
    if tenant_ctx.company and tenant_ctx.company.id not in company_ids:
        company_ids.append(tenant_ctx.company.id)
    if not company_ids and staff.base_company_id:
        company_ids.append(staff.base_company_id)

    # Resolve all staff belonging to this tenant
    staff_q = db.query(StaffEmployee.id).filter(
        StaffEmployee.status == 'active',
        StaffEmployee.is_deleted == False,
        or_(
            StaffEmployee.tenant_id == (tenant_ctx.client.id if tenant_ctx.client else -1),
            StaffEmployee.base_company_id.in_(company_ids)
        )
    )
    all_tenant_staff_ids = [r[0] for r in staff_q.all()]
    if staff.id not in all_tenant_staff_ids:
        all_tenant_staff_ids.append(staff.id)

    is_admin = tenant_ctx.is_tenant_admin or (hasattr(staff, 'role') and staff.role and getattr(staff.role, 'role_code', '').lower() in {'tenant_admin', 'admin', 'super_admin'})
    if is_admin:
        allowed_staff_ids = all_tenant_staff_ids
    else:
        # Non-admin tenant staff: check reporting downline
        downline = get_team_member_ids(staff, db, StaffEmployee) or [staff.id]
        allowed_staff_ids = [sid for sid in downline if sid in set(all_tenant_staff_ids)]
        if not allowed_staff_ids:
            allowed_staff_ids = [staff.id]

    return True, allowed_staff_ids, company_ids
from datetime import datetime, timedelta, date
from typing import Optional
import pytz
import re
import os
import uuid
import mimetypes

router = APIRouter()


def get_indian_time():
    indian_tz = pytz.timezone('Asia/Kolkata')
    return datetime.now(indian_tz).replace(tzinfo=None)


def normalize_phone(phone):
    if not phone:
        return None
    digits = re.sub(r'[^\d]', '', str(phone))
    if len(digits) > 10:
        digits = digits[-10:]
    return digits if len(digits) == 10 else None


def resolve_call_from(
    source: Optional[str],
    device_call_id: Optional[str] = None,
    call_type: Optional[str] = None,
    dialed_page: Optional[str] = None,
    matched_lead_id: Optional[int] = None
) -> str:
    if dialed_page and str(dialed_page).strip():
        page_val = str(dialed_page).strip()
        low = page_val.lower()
        if 'my lead' in low:
            return 'My Leads'
        elif 'staff lead' in low:
            return 'Staff Leads'
        elif 'dialer' in low or 'auto' in low:
            return 'Auto Dialer'
        elif 'crm dashboard' in low or 'dashboard' in low:
            return 'CRM Dashboard'
        elif 'softphone' in low:
            return 'Softphone Center'
        elif 'operator' in low:
            return 'Operator Calls'
        elif 'whatsapp' in low:
            return 'WhatsApp Center'
        elif 'planner' in low:
            return 'Day Planner'
        elif 'task' in low:
            return 'Tasks'
        elif 'master' in low:
            return 'Master Leads'
        elif 'bank' in low:
            return 'Bank Wise Leads'
        elif 'inbound' in low or 'did' in low:
            return 'Inbound DID'
        elif 'sim' in low or 'native' in low:
            return 'Native SIM'
        return page_val

    src = (source or '').lower().strip()
    dev_id = (device_call_id or '').lower().strip()
    call_tp = (call_type or '').upper().strip()

    if src == 'dialer' or call_tp == 'DIALER' or (dev_id and 'cda_' in dev_id):
        return 'Auto Dialer'
    elif call_tp in ('INCOMING', 'INBOUND') or (dev_id and 'did_' in dev_id):
        return 'Inbound DID'
    elif src in ('native', 'direct_sim', 'normal') and not (dev_id.startswith('vcs_') or dev_id.startswith('plivo_')):
        return 'Native SIM'
    elif matched_lead_id:
        return 'My Leads'
    elif src == 'softphone' or dev_id.startswith('vcs_') or dev_id.startswith('plivo_'):
        return 'Softphone Center'
    return src.capitalize() if src else 'My Leads'


@router.post("/record-dial-page")
async def record_dial_page(
    payload: dict = Body(...),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_hybrid)
):
    """
    DC Protocol: Records the specific frontend page where a call was dialed from.
    Updates VoIPCallSession metadata and StaffCallLog dialed_page for exact Call From tracking.
    """
    session_id = (payload.get("call_session_id") or "").strip()
    dialed_page = (payload.get("dialed_page") or "").strip()
    if not session_id or not dialed_page:
        return {"success": False, "message": "Missing call_session_id or dialed_page"}

    page_clean = dialed_page
    low = page_clean.lower()
    if 'my lead' in low:
        page_clean = 'My Leads'
    elif 'staff lead' in low:
        page_clean = 'Staff Leads'
    elif 'dialer' in low or 'auto' in low:
        page_clean = 'Auto Dialer'
    elif 'crm dashboard' in low or 'dashboard' in low:
        page_clean = 'CRM Dashboard'
    elif 'softphone' in low:
        page_clean = 'Softphone Center'
    elif 'operator' in low:
        page_clean = 'Operator Calls'
    elif 'whatsapp' in low:
        page_clean = 'WhatsApp Center'
    elif 'planner' in low:
        page_clean = 'Day Planner'
    elif 'task' in low:
        page_clean = 'Tasks'
    elif 'master' in low:
        page_clean = 'Master Leads'
    elif 'bank' in low:
        page_clean = 'Bank Wise Leads'

    # 1. Update VoIPCallSession metadata_json if exists
    try:
        from app.models.voip_call_session import VoIPCallSession
        vcs = db.query(VoIPCallSession).filter(VoIPCallSession.call_session_id == session_id).first()
        if vcs:
            import json
            meta = {}
            if vcs.metadata_json:
                try:
                    meta = json.loads(vcs.metadata_json)
                except Exception:
                    meta = {}
            meta['dialed_page'] = page_clean
            vcs.metadata_json = json.dumps(meta)
    except Exception as e:
        logger.warning(f"[RECORD-DIAL-PAGE] VoIPCallSession update notice: {e}")

    # 2. Update StaffCallLog dialed_page if already created
    try:
        from app.models.call_tracking import StaffCallLog
        scl = db.query(StaffCallLog).filter(StaffCallLog.device_call_id == session_id).first()
        if scl:
            scl.dialed_page = page_clean
    except Exception as e:
        logger.warning(f"[RECORD-DIAL-PAGE] StaffCallLog update notice: {e}")

    try:
        db.commit()
    except Exception:
        db.rollback()

    return {"success": True, "call_session_id": session_id, "dialed_page": page_clean}


@router.post("/sync")
async def sync_call_logs(
    call_logs: list = Body(..., description="List of call log entries from device"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_hybrid)
):
    # DC Protocol: Only staff can sync
    if not hasattr(current_user, 'emp_code'):
        raise HTTPException(status_code=403, detail="Staff access required")

    staff = db.query(StaffEmployee).filter(StaffEmployee.id == current_user.id).first()
    if not staff:
        raise HTTPException(status_code=404, detail="Staff record not found")

    # CT Protocol: FULL_ACCESS roles (VGK4U Supreme, Key Leadership, EA, HR, Accounts)
    # bypass the call_tracking_enabled gate — they can always sync their calls
    if not staff.call_tracking_enabled and not is_ct_full_access(staff):
        return {
            "success": False,
            "message": "Call tracking is not enabled for your account. Contact your manager to enable Quality Test tracking.",
            "records_synced": 0,
            "records_matched": 0,
            "records_skipped": 0
        }

    # DC_CT_PAYLOAD_CAP: Reject oversized payloads to prevent backend overload
    if len(call_logs) > 500:
        raise HTTPException(
            status_code=400,
            detail=f"Too many call logs in one sync ({len(call_logs)}). Maximum is 500 per request. Split into batches."
        )

    company_id = staff.base_company_id
    staff_id = staff.id

    sync_log = StaffCallSyncLog(
        company_id=company_id,
        staff_id=staff_id,
        sync_started_at=get_indian_time(),
        status='in_progress'
    )
    db.add(sync_log)
    db.flush()

    try:
        records_synced = 0
        records_matched = 0
        records_skipped = 0
        last_call_dt = None
        _ct_notes: list = []

        # DC_CT_DEDUP_BULK: Pre-fetch all known device_call_ids for this staff in ONE query
        # This eliminates the N+1 pattern (was: one DB query per call log entry).
        existing_device_ids: set = set()
        rows = db.query(StaffCallLog.device_call_id).filter(
            StaffCallLog.staff_id == staff_id,
            StaffCallLog.device_call_id != None
        ).all()
        for row in rows:
            existing_device_ids.add(str(row[0]))

        # DC_CT_DEDUP_BULK: Pre-fetch fallback-dedup rows (no device_call_id) in ONE query.
        # Build a set of (phone, call_type, minute-bucket) tuples for ±60s window matching.
        existing_fallback: set = set()
        fallback_rows = db.query(
            StaffCallLog.phone_number,
            StaffCallLog.call_type,
            StaffCallLog.call_datetime
        ).filter(
            StaffCallLog.staff_id == staff_id,
            StaffCallLog.device_call_id == None
        ).all()
        for fb in fallback_rows:
            if fb.call_datetime:
                existing_fallback.add((fb.phone_number, fb.call_type, fb.call_datetime))

        # DC_CT_BATCH_PREPARE: Pre-collect raw phones to resolve recognized system entities in bulk
        batch_raw_phones = [
            str(entry.get('number') or entry.get('phone_number') or '').strip()
            for entry in call_logs
            if (entry.get('number') or entry.get('phone_number'))
        ]
        system_matches = _resolve_phones_batch(db, batch_raw_phones) if batch_raw_phones else {}
        records_personal_dropped = 0

        # DC_CT_CRM_LOOKUP: Also check CRM leads in accessible companies
        all_lead_phones = {}
        leads = db.query(CRMLead.id, CRMLead.phone, CRMLead.alternate_phone).filter(
            CRMLead.company_id == company_id
        ).all()
        for lead in leads:
            for ph in [lead.phone, lead.alternate_phone]:
                norm = normalize_phone(ph)
                if norm:
                    all_lead_phones[norm] = lead.id

        for entry in call_logs:
            phone = str(entry.get('number') or entry.get('phone_number', '')).strip()
            raw_type = entry.get('call_type') or entry.get('type') or 'OUTGOING'
            call_type = str(raw_type).upper()
            duration = int(entry.get('duration') or entry.get('duration_seconds', 0))
            if duration < 0 or duration > 14400:
                duration = 0
            call_ts = entry.get('date') or entry.get('call_datetime')
            device_id = entry.get('device_call_id') or entry.get('id', '')

            if not phone or not call_ts:
                continue

            norm_phone = normalize_phone(phone)
            if not norm_phone:
                continue

            # ── STRICT GATE: ONLY SYNC CALLS FOR SYSTEM NUMBERS ─────────────────
            # Filter strictly to CRM Leads, VGK Members, MNR Members, Official Partners, and Vendors.
            # All personal / unknown calls are dropped and NEVER persisted in staff_call_logs.
            sys_info = system_matches.get(norm_phone)
            matched_lead_id = sys_info.get("id") if (sys_info and sys_info.get("source") == "lead") else all_lead_phones.get(norm_phone)

            if not sys_info and not matched_lead_id:
                records_personal_dropped += 1
                continue

            if isinstance(call_ts, (int, float)):
                if call_ts > 1e12:
                    call_ts = call_ts / 1000
                call_dt = datetime.fromtimestamp(call_ts, tz=pytz.timezone('Asia/Kolkata')).replace(tzinfo=None)
            elif isinstance(call_ts, str):
                try:
                    dt_parsed = datetime.fromisoformat(call_ts.replace('Z', '+00:00'))
                    if dt_parsed.tzinfo is not None:
                        call_dt = dt_parsed.astimezone(pytz.timezone('Asia/Kolkata')).replace(tzinfo=None)
                    else:
                        call_dt = dt_parsed
                except (ValueError, TypeError):
                    continue
            else:
                continue

            call_date_str = call_dt.strftime('%Y-%m-%d')

            # DC_CT_DEDUP_BULK: All dedup is now in-memory (O(1) set lookup), zero extra DB queries
            if device_id:
                device_id_str = str(device_id)
                if device_id_str in existing_device_ids:
                    records_skipped += 1
                    continue
                existing_device_ids.add(device_id_str)
            else:
                # Fallback: check if any existing row has the same phone+type within ±60s
                is_dup = any(
                    fb_phone == phone and fb_type == call_type and
                    abs((fb_dt - call_dt).total_seconds()) <= 60
                    for fb_phone, fb_type, fb_dt in existing_fallback
                )
                if is_dup:
                    records_skipped += 1
                    continue
                existing_fallback.add((phone, call_type, call_dt))

            raw_contact = entry.get('contact_name') or entry.get('name') or entry.get('cachedName') or None
            resolved_name = sys_info.get("name") if sys_info else None
            contact_name_val = resolved_name or (str(raw_contact).strip() if raw_contact and str(raw_contact).strip() else None)

            call_log = StaffCallLog(
                company_id=company_id,
                staff_id=staff_id,
                phone_number=phone,
                contact_name=contact_name_val,
                call_type=call_type,
                call_datetime=call_dt,
                call_date=call_date_str,
                duration_seconds=duration,
                source='native',
                device_call_id=str(device_id) if device_id else None,
                matched_lead_id=matched_lead_id,
                matched_at=get_indian_time() if matched_lead_id else None,
                synced_at=get_indian_time()
            )
            db.add(call_log)
            records_synced += 1

            if matched_lead_id:
                records_matched += 1
                # Sync lead last contact date and handler for real-time Auto Dialer & CRM parity
                lead_obj = db.query(CRMLead).filter(CRMLead.id == matched_lead_id).first()
                if lead_obj:
                    if not lead_obj.last_contact_date or call_dt > lead_obj.last_contact_date:
                        lead_obj.last_contact_date = call_dt
                        lead_obj.last_contact_by = staff_id

                # DC-CT-CALLNOTE-001: Auto-post [SIM Call] note for recent matched calls only
                # Gate: call must have happened within last 24 hours (skips historical backfills)
                if (get_indian_time() - call_dt).total_seconds() < 86400:
                    _dur_str = f' {duration}s' if duration > 0 else ''
                    _ct_label = call_type.capitalize() if call_type else 'Unknown'
                    _ct_notes.append({
                        'lead_id': matched_lead_id,
                        'company_id': company_id,
                        'created_by_id': staff_id,
                        'note': f'[SIM Call] {_ct_label}{_dur_str}'
                    })

            if not last_call_dt or call_dt > last_call_dt:
                last_call_dt = call_dt

        sync_log.sync_completed_at = get_indian_time()
        sync_log.records_synced = records_synced
        sync_log.records_matched = records_matched
        sync_log.records_duplicates_skipped = records_skipped
        sync_log.last_call_datetime = last_call_dt
        sync_log.status = 'completed'

        db.commit()

        # DC-CT-CALLNOTE-001: Post queued notes in a separate transaction (non-fatal)
        if _ct_notes:
            try:
                for _nd in _ct_notes:
                    db.add(CRMLeadNote(**_nd))
                db.commit()
            except Exception:
                db.rollback()

        return {
            "success": True,
            "records_synced": records_synced,
            "records_matched": records_matched,
            "records_skipped": records_skipped,
            "records_personal_dropped": records_personal_dropped,
            "sync_id": sync_log.id
        }

    except HTTPException:
        raise
    except Exception as e:
        # DC_CT_SAFE_ROLLBACK: Catch all DB/processing errors so the uvicorn worker
        # never crashes mid-request (was: socket hang up on backend crash).
        try:
            db.rollback()
            sync_log.status = 'failed'
            sync_log.error_message = str(e)[:500]
            sync_log.sync_completed_at = get_indian_time()
            db.add(sync_log)
            db.commit()
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=f"Sync failed — please retry: {str(e)[:200]}")


@router.get("/lead/{lead_id}/calls")
async def get_lead_call_history(
    lead_id: int,
    company_id: int = Query(None),
    staff_id: int = Query(None, description="Filter calls by specific staff/handler"),
    call_type: str = Query(None, description="Filter by call type: INCOMING, OUTGOING, MISSED"),
    page: int = Query(1, ge=1),
    per_page: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_hybrid)
):
    # DC Protocol: Staff see all, members see own leads only
    lead = db.query(CRMLead).filter(CRMLead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    if not hasattr(current_user, 'emp_code'):
        raise HTTPException(status_code=403, detail="Staff access required")

    # Multi-tenant isolation for call history
    is_saas, saas_staff_ids, saas_company_ids = resolve_call_tracking_scope(db, current_user)
    if is_saas:
        if lead.company_id and saas_company_ids and lead.company_id not in set(saas_company_ids):
            raise HTTPException(status_code=403, detail="Lead not found in your tenant")

    norm_phone = normalize_phone(lead.phone)
    norm_alt = normalize_phone(lead.alternate_phone)

    phone_conditions = []
    if lead.phone:
        phone_conditions.append(StaffCallLog.phone_number.like(f'%{norm_phone}%') if norm_phone else None)
    if lead.alternate_phone:
        phone_conditions.append(StaffCallLog.phone_number.like(f'%{norm_alt}%') if norm_alt else None)

    base_filter = or_(
        StaffCallLog.matched_lead_id == lead_id,
        *[c for c in phone_conditions if c is not None]
    )

    query = db.query(StaffCallLog).filter(base_filter)
    if is_saas:
        if saas_company_ids:
            query = query.filter(StaffCallLog.company_id.in_(saas_company_ids))
        if saas_staff_ids:
            query = query.filter(StaffCallLog.staff_id.in_(saas_staff_ids))
    if staff_id:
        if is_saas and staff_id not in set(saas_staff_ids):
            raise HTTPException(status_code=403, detail="Staff member not in your tenant")
        query = query.filter(StaffCallLog.staff_id == staff_id)
    if call_type:
        query = query.filter(StaffCallLog.call_type == call_type.upper())

    query = query.order_by(StaffCallLog.call_datetime.desc())

    total = query.count()
    calls = query.offset((page - 1) * per_page).limit(per_page).all()

    all_staff_ids_q = db.query(distinct(StaffCallLog.staff_id)).filter(base_filter).all()
    all_staff_ids = [r[0] for r in all_staff_ids_q]
    staff_names = {}
    if all_staff_ids:
        staff_rows = db.query(StaffEmployee.id, StaffEmployee.full_name, StaffEmployee.emp_code).filter(
            StaffEmployee.id.in_(all_staff_ids)
        ).all()
        staff_names = {s.id: s.full_name for s in staff_rows}

    safe_dur = case(
        (and_(StaffCallLog.duration_seconds >= 0, StaffCallLog.duration_seconds <= 14400), StaffCallLog.duration_seconds),
        else_=0
    )

    summary_query = db.query(
        func.count(StaffCallLog.id).label('total_calls'),
        func.sum(safe_dur).label('total_duration'),
        func.sum(case((StaffCallLog.call_type == 'INCOMING', 1), else_=0)).label('incoming'),
        func.sum(case((StaffCallLog.call_type == 'OUTGOING', 1), else_=0)).label('outgoing'),
        func.sum(case((StaffCallLog.call_type == 'MISSED', 1), else_=0)).label('missed'),
        func.count(distinct(StaffCallLog.staff_id)).label('staff_count'),
    ).filter(base_filter).first()

    per_staff_stats = db.query(
        StaffCallLog.staff_id,
        func.count(StaffCallLog.id).label('total_calls'),
        func.sum(safe_dur).label('total_duration'),
        func.sum(case((StaffCallLog.call_type == 'INCOMING', 1), else_=0)).label('incoming'),
        func.sum(case((StaffCallLog.call_type == 'OUTGOING', 1), else_=0)).label('outgoing'),
        func.sum(case((StaffCallLog.call_type == 'MISSED', 1), else_=0)).label('missed'),
    ).filter(base_filter).group_by(StaffCallLog.staff_id).all()

    staff_breakdown = []
    for ps in per_staff_stats:
        staff_rows_info = db.query(StaffEmployee.emp_code).filter(StaffEmployee.id == ps.staff_id).first()
        staff_breakdown.append({
            'staff_id': ps.staff_id,
            'staff_name': staff_names.get(ps.staff_id, 'Unknown'),
            'emp_code': staff_rows_info.emp_code if staff_rows_info else '',
            'total_calls': ps.total_calls or 0,
            'total_duration': int(ps.total_duration or 0),
            'incoming': ps.incoming or 0,
            'outgoing': ps.outgoing or 0,
            'missed': ps.missed or 0,
        })

    # DC-CT-DIALER-UNION-001: Also include CRM auto-dialer attempts for this lead
    try:
        dialer_rows = db.execute(text("""
            SELECT a.id, a.dialed_at, a.call_outcome, a.user_ref,
                   e.full_name AS staff_name, l.phone AS lead_phone, l.name AS lead_name
            FROM crm_dialer_attempts a
            JOIN crm_leads l ON a.lead_id = l.id
            LEFT JOIN staff_employees e ON e.id::text = a.user_ref
            WHERE a.lead_id = :lead_id AND a.call_outcome != 'skip'
            ORDER BY a.dialed_at DESC
            LIMIT 50
        """), {"lead_id": lead_id}).fetchall()
    except Exception:
        dialer_rows = []

    dialer_entries = []
    for dr in dialer_rows:
        dialer_entries.append({
            'id': f'dialer_{dr[0]}',
            'source': 'dialer',
            'staff_id': None,
            'staff_name': dr[4] or 'Auto Dialer',
            'phone_number': dr[5] or '',
            'contact_name': dr[6] or '',
            'call_type': 'DIALER',
            'call_datetime': dr[1].isoformat() if dr[1] else None,
            'duration_seconds': 0,
            'call_outcome': dr[2] or '',
            'matched_lead_id': lead_id,
            'device_call_id': None,
            'has_recording': False,
        })

    # DC-OPERATOR-CALLS-UNION: Include Operator / MyOperator calls for this lead
    op_entries = []
    try:
        from app.models.operator_calls import OperatorCall
        op_phone_conditions = []
        if norm_phone:
            op_phone_conditions.append(OperatorCall.caller_number.like(f'%{norm_phone}%'))
            op_phone_conditions.append(OperatorCall.called_number.like(f'%{norm_phone}%'))
        if norm_alt:
            op_phone_conditions.append(OperatorCall.caller_number.like(f'%{norm_alt}%'))
            op_phone_conditions.append(OperatorCall.called_number.like(f'%{norm_alt}%'))

        op_filter = or_(
            OperatorCall.crm_lead_id == lead_id,
            *[c for c in op_phone_conditions if c is not None]
        ) if op_phone_conditions else (OperatorCall.crm_lead_id == lead_id)

        op_rows = db.query(OperatorCall).filter(op_filter).order_by(OperatorCall.created_at.desc()).limit(100).all()
        for op in op_rows:
            ct = 'MISSED' if (op.status or '').lower() == 'missed' else (op.call_type or 'INBOUND').upper()
            st_name = op.handled_by or op.operator_name or 'Central IVR'
            op_entries.append({
                'id': f'operator_{op.id}',
                'source': 'operator',
                'staff_id': None,
                'staff_name': f"{st_name} (IVR)" if st_name != 'Central IVR' else 'Central IVR',
                'phone_number': op.caller_number if op.call_type == 'inbound' else op.called_number,
                'contact_name': lead.name,
                'call_type': ct,
                'call_datetime': OperatorCall._fmt_dt(op.started_at or op.created_at),
                'duration_seconds': op.duration_seconds or 0,
                'call_outcome': op.status or '',
                'matched_lead_id': lead_id,
                'recording_url': op.recording_url,
                'has_recording': bool(op.recording_url),
            })
    except Exception as _ope:
        print(f"[CALL-TRACKING] Operator calls merge error: {_ope}")
        op_entries = []

    cat_obj = db.query(SignupCategory.name).filter(SignupCategory.id == lead.category_id).first() if lead.category_id else None
    cat_name = cat_obj[0] if cat_obj else 'General'

    native_data = [{
        **c.to_dict(),
        'staff_name': staff_names.get(c.staff_id, 'Unknown'),
        'source': getattr(c, 'source', 'native'),
        'category_name': cat_name,
        'call_from': resolve_call_from(
            getattr(c, 'source', 'native'),
            getattr(c, 'device_call_id', None),
            c.call_type,
            dialed_page=getattr(c, 'dialed_page', None),
            matched_lead_id=c.matched_lead_id
        ),
    } for c in calls]

    for de in dialer_entries:
        de['category_name'] = cat_name
        de['call_from'] = 'Auto Dialer'

    for oe in op_entries:
        oe['category_name'] = cat_name
        oe['call_from'] = 'Auto Dialer'

    all_data = sorted(
        native_data + dialer_entries + op_entries,
        key=lambda x: x.get('call_datetime') or '',
        reverse=True
    )

    total_with_op = total + len(dialer_entries) + len(op_entries)

    return {
        "success": True,
        "data": all_data,
        "summary": {
            "total_calls": (summary_query.total_calls or 0) + len(dialer_entries) + len(op_entries),
            "total_duration_seconds": int(summary_query.total_duration or 0) + sum(e['duration_seconds'] for e in op_entries),
            "incoming": (summary_query.incoming or 0) + sum(1 for e in op_entries if e['call_type'] == 'INBOUND'),
            "outgoing": (summary_query.outgoing or 0) + sum(1 for e in op_entries if e['call_type'] == 'OUTBOUND') + len(dialer_entries),
            "missed": (summary_query.missed or 0) + sum(1 for e in op_entries if e['call_type'] == 'MISSED'),
            "staff_involved": summary_query.staff_count or 0,
        },
        "staff_breakdown": staff_breakdown,
        "staff_list": [{'id': sid, 'name': staff_names.get(sid, 'Unknown')} for sid in all_staff_ids],
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total": total_with_op,
            "pages": (total_with_op + per_page - 1) // per_page if total_with_op > 0 else 0
        }
    }


@router.get("/my-stats")
async def get_my_call_stats(
    date_from: str = Query(None),
    date_to: str = Query(None),
    quick_range: str = Query(None),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_hybrid)
):
    if not hasattr(current_user, 'emp_code'):
        raise HTTPException(status_code=403, detail="Staff access required")

    staff = db.query(StaffEmployee).filter(StaffEmployee.id == current_user.id).first()
    if not staff:
        raise HTTPException(status_code=404, detail="Staff not found")

    now = get_indian_time()
    today = now.date()

    if quick_range and not date_from and not date_to:
        if quick_range == 'today':
            date_from = today.strftime('%Y-%m-%d')
            date_to = today.strftime('%Y-%m-%d')
        elif quick_range == 'yesterday':
            yd = today - timedelta(days=1)
            date_from = yd.strftime('%Y-%m-%d')
            date_to = yd.strftime('%Y-%m-%d')
        elif quick_range == 'this_week':
            start = today - timedelta(days=today.weekday())
            date_from = start.strftime('%Y-%m-%d')
            date_to = today.strftime('%Y-%m-%d')
        elif quick_range == 'last_week':
            end = today - timedelta(days=today.weekday() + 1)
            start = end - timedelta(days=6)
            date_from = start.strftime('%Y-%m-%d')
            date_to = end.strftime('%Y-%m-%d')
        elif quick_range == 'this_month':
            date_from = today.replace(day=1).strftime('%Y-%m-%d')
            date_to = today.strftime('%Y-%m-%d')
        elif quick_range == 'last_month':
            first_this = today.replace(day=1)
            end = first_this - timedelta(days=1)
            start = end.replace(day=1)
            date_from = start.strftime('%Y-%m-%d')
            date_to = end.strftime('%Y-%m-%d')
        elif quick_range == 'last_3':
            date_from = (today - timedelta(days=2)).strftime('%Y-%m-%d')
            date_to = today.strftime('%Y-%m-%d')
        elif quick_range == 'last_7':
            date_from = (today - timedelta(days=6)).strftime('%Y-%m-%d')
            date_to = today.strftime('%Y-%m-%d')
        elif quick_range == 'last_30':
            date_from = (today - timedelta(days=29)).strftime('%Y-%m-%d')
            date_to = today.strftime('%Y-%m-%d')

    if not date_from:
        date_from = (now - timedelta(days=2)).strftime('%Y-%m-%d')
    if not date_to:
        date_to = now.strftime('%Y-%m-%d')

    base = db.query(StaffCallLog).filter(
        StaffCallLog.staff_id == staff.id,
        StaffCallLog.call_date >= date_from,
        StaffCallLog.call_date <= date_to
    )

    safe_dur = case(
        (and_(StaffCallLog.duration_seconds >= 0, StaffCallLog.duration_seconds <= 14400), StaffCallLog.duration_seconds),
        else_=0
    )

    stats = base.with_entities(
        func.count(StaffCallLog.id).label('total_calls'),
        func.sum(safe_dur).label('total_duration'),
        func.sum(case((StaffCallLog.call_type == 'INCOMING', 1), else_=0)).label('incoming'),
        func.sum(case((StaffCallLog.call_type == 'OUTGOING', 1), else_=0)).label('outgoing'),
        func.sum(case((StaffCallLog.call_type == 'MISSED', 1), else_=0)).label('missed'),
        func.sum(case((StaffCallLog.call_type == 'REJECTED', 1), else_=0)).label('rejected'),
        func.count(distinct(StaffCallLog.phone_number)).label('unique_numbers'),
        func.sum(case((StaffCallLog.matched_lead_id.isnot(None), 1), else_=0)).label('crm_matched'),
    ).first()

    daily = base.with_entities(
        StaffCallLog.call_date,
        func.count(StaffCallLog.id).label('calls'),
        func.sum(safe_dur).label('duration'),
        func.sum(case((StaffCallLog.call_type == 'MISSED', 1), else_=0)).label('missed'),
    ).group_by(StaffCallLog.call_date).order_by(StaffCallLog.call_date.desc()).limit(30).all()

    last_sync = db.query(StaffCallSyncLog).filter(
        StaffCallSyncLog.staff_id == staff.id,
        StaffCallSyncLog.status == 'completed'
    ).order_by(StaffCallSyncLog.sync_completed_at.desc()).first()

    # DC Protocol (Apr 2026): Fetch VGK registered + WA sent counts for the same date range
    vgk_created_count = 0
    wa_sent_count = 0
    try:
        ct_df = f"{date_from} 00:00:00"
        ct_dt = f"{date_to} 23:59:59"
        vgk_row = db.execute(text(
            "SELECT COUNT(*) FROM crm_wa_share_logs "
            "WHERE staff_id = :sid AND share_type = 'vgk_registration' "
            "AND created_at BETWEEN :df AND :dt"
        ), {"sid": staff.id, "df": ct_df, "dt": ct_dt}).scalar()
        wa_row = db.execute(text(
            "SELECT COUNT(*) FROM crm_wa_share_logs "
            "WHERE staff_id = :sid AND share_type = 'vgk_creds' "
            "AND created_at BETWEEN :df AND :dt"
        ), {"sid": staff.id, "df": ct_df, "dt": ct_dt}).scalar()
        vgk_created_count = int(vgk_row or 0)
        wa_sent_count = int(wa_row or 0)
    except Exception:
        pass

    return {
        "success": True,
        "stats": {
            "total_calls": stats.total_calls or 0,
            "total_duration_seconds": int(stats.total_duration or 0),
            "incoming": stats.incoming or 0,
            "outgoing": stats.outgoing or 0,
            "missed": stats.missed or 0,
            "rejected": stats.rejected or 0,
            "unique_numbers": stats.unique_numbers or 0,
            "crm_matched": stats.crm_matched or 0,
            "vgk_created": vgk_created_count,
            "wa_sent": wa_sent_count,
        },
        "daily": [{
            'date': d.call_date,
            'calls': d.calls,
            'duration': int(d.duration or 0),
            'missed': d.missed or 0,
        } for d in daily],
        "last_sync": last_sync.to_dict() if last_sync else None,
        "date_range": {"from": date_from, "to": date_to},
        "call_tracking_enabled": bool(staff.call_tracking_enabled)
    }


@router.get("/management/overview")
async def get_call_management_overview(
    company_id: Optional[int] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    staff_id: Optional[int] = Query(None),
    department_id: Optional[int] = Query(None, description="Filter by department"),
    reporting_manager_id: Optional[int] = Query(None, description="Filter by reporting manager"),
    call_type: Optional[str] = Query(None, description="Filter by call type: INCOMING, OUTGOING, MISSED"),
    phone_number: Optional[str] = Query(None, description="Filter by phone number (partial match)"),
    quick_range: Optional[str] = Query(None, description="Quick range: today, yesterday, this_week, last_week, this_month, last_month, last_7, last_30"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_hybrid)
):
    # DC Protocol: Menu-based access control - page assignment = full access
    if not hasattr(current_user, 'emp_code'):
        raise HTTPException(status_code=403, detail="Staff access required")

    staff = db.query(StaffEmployee).filter(StaffEmployee.id == current_user.id).first()
    if not staff:
        raise HTTPException(status_code=404, detail="Staff not found")

    # Sanitize filter parameters to prevent Query object leakage or non-integer values
    if not isinstance(department_id, int):
        try:
            department_id = int(department_id) if department_id and str(department_id).isdigit() else None
        except Exception:
            department_id = None
    if not isinstance(reporting_manager_id, int):
        try:
            reporting_manager_id = int(reporting_manager_id) if reporting_manager_id and str(reporting_manager_id).isdigit() else None
        except Exception:
            reporting_manager_id = None
    if not isinstance(staff_id, int):
        try:
            staff_id = int(staff_id) if staff_id and str(staff_id).isdigit() else None
        except Exception:
            staff_id = None
    if not isinstance(company_id, int):
        try:
            company_id = int(company_id) if company_id and str(company_id).isdigit() else None
        except Exception:
            company_id = None
    if not isinstance(call_type, str):
        call_type = None
    if not isinstance(phone_number, str):
        phone_number = None

    # CT Protocol: company_id removed from call log filtering — employee-based scoping only
    now = get_indian_time()
    today = now.date()

    if quick_range:
        if quick_range == 'today':
            date_from = today.strftime('%Y-%m-%d')
            date_to = today.strftime('%Y-%m-%d')
        elif quick_range == 'yesterday':
            yd = today - timedelta(days=1)
            date_from = yd.strftime('%Y-%m-%d')
            date_to = yd.strftime('%Y-%m-%d')
        elif quick_range == 'this_week':
            start = today - timedelta(days=today.weekday())
            date_from = start.strftime('%Y-%m-%d')
            date_to = today.strftime('%Y-%m-%d')
        elif quick_range == 'last_week':
            end = today - timedelta(days=today.weekday() + 1)
            start = end - timedelta(days=6)
            date_from = start.strftime('%Y-%m-%d')
            date_to = end.strftime('%Y-%m-%d')
        elif quick_range == 'this_month':
            date_from = today.replace(day=1).strftime('%Y-%m-%d')
            date_to = today.strftime('%Y-%m-%d')
        elif quick_range == 'last_month':
            first_this = today.replace(day=1)
            end = first_this - timedelta(days=1)
            start = end.replace(day=1)
            date_from = start.strftime('%Y-%m-%d')
            date_to = end.strftime('%Y-%m-%d')
        elif quick_range == 'last_7':
            date_from = (today - timedelta(days=6)).strftime('%Y-%m-%d')
            date_to = today.strftime('%Y-%m-%d')
        elif quick_range == 'last_30':
            date_from = (today - timedelta(days=29)).strftime('%Y-%m-%d')
            date_to = today.strftime('%Y-%m-%d')

    if not date_from:
        date_from = (now - timedelta(days=30)).strftime('%Y-%m-%d')
    if not date_to:
        date_to = now.strftime('%Y-%m-%d')

    # CT Protocol: Role-based team scoping
    # Multi-tenant isolation for call tracking
    is_saas, saas_staff_ids, saas_company_ids = resolve_call_tracking_scope(db, staff)
    if is_saas:
        if not saas_staff_ids or not saas_company_ids:
            return {
                "success": True,
                "overview": {"total_calls":0,"total_duration_seconds":0,"incoming":0,"outgoing":0,"missed":0,"unique_numbers":0,"crm_matched":0,"active_staff":0,"avg_daily_talk_time":0},
                "per_staff": [], "daily_trend": [], "staff_list": [], "departments": [], "managers": [],
                "date_range": {"from": date_from, "to": date_to},
                "filters_applied": {"department_id": department_id, "reporting_manager_id": reporting_manager_id, "call_type": call_type, "staff_id": staff_id, "phone_number": phone_number}
            }
        team_scope_ids = saas_staff_ids
        is_full_access = False
    else:
        is_full_access = is_ct_full_access(current_user)
        team_scope_ids = None  # None = unrestricted (FULL_ACCESS)
        if not is_full_access:
            team_scope_ids = get_team_member_ids(current_user, db, StaffEmployee)
            if not team_scope_ids:
                return {
                    "success": True,
                    "overview": {"total_calls":0,"total_duration_seconds":0,"incoming":0,"outgoing":0,"missed":0,"unique_numbers":0,"crm_matched":0,"active_staff":0,"avg_daily_talk_time":0},
                    "per_staff": [], "daily_trend": [], "staff_list": [], "departments": [], "managers": [],
                    "date_range": {"from": date_from, "to": date_to},
                    "filters_applied": {"department_id": department_id, "reporting_manager_id": reporting_manager_id, "call_type": call_type, "staff_id": staff_id, "phone_number": phone_number}
                }

    filtered_staff_ids = None
    if department_id or reporting_manager_id:
        staff_q = db.query(StaffEmployee.id).filter(
            StaffEmployee.status == 'active'
        )
        if is_saas:
            staff_q = staff_q.filter(StaffEmployee.id.in_(saas_staff_ids))
        if department_id:
            staff_q = staff_q.filter(StaffEmployee.department_id == department_id)
        if reporting_manager_id:
            staff_q = staff_q.filter(StaffEmployee.reporting_manager_id == reporting_manager_id)
        filtered_staff_ids = [r.id for r in staff_q.all()]
        # Intersect with team scope so managers cannot filter outside their downline
        if team_scope_ids is not None:
            _scope_set = set(team_scope_ids)
            filtered_staff_ids = [sid for sid in filtered_staff_ids if sid in _scope_set]
    elif team_scope_ids is not None:
        filtered_staff_ids = team_scope_ids

    base = db.query(StaffCallLog).filter(
        StaffCallLog.call_date >= date_from,
        StaffCallLog.call_date <= date_to
    )
    if is_saas:
        base = base.filter(
            StaffCallLog.staff_id.in_(saas_staff_ids),
            StaffCallLog.company_id.in_(saas_company_ids)
        )
    if staff_id:
        # Prevent non-FULL_ACCESS managers from viewing staff outside their team
        if is_saas and staff_id not in set(saas_staff_ids):
            raise HTTPException(status_code=403, detail="Access denied: staff member not in your tenant")
        elif team_scope_ids is not None and staff_id not in set(team_scope_ids):
            raise HTTPException(status_code=403, detail="Access denied: staff member not in your team")
        base = base.filter(StaffCallLog.staff_id == staff_id)
    elif filtered_staff_ids is not None:
        if not filtered_staff_ids:
            return {
                "success": True,
                "overview": {"total_calls":0,"total_duration_seconds":0,"incoming":0,"outgoing":0,"missed":0,"unique_numbers":0,"crm_matched":0,"active_staff":0,"avg_daily_talk_time":0},
                "per_staff": [], "daily_trend": [], "staff_list": [], "departments": [], "managers": [],
                "date_range": {"from": date_from, "to": date_to}, "filters_applied": {"department_id": department_id, "reporting_manager_id": reporting_manager_id, "call_type": call_type, "staff_id": staff_id}
            }
        base = base.filter(StaffCallLog.staff_id.in_(filtered_staff_ids))

    if call_type:
        base = base.filter(StaffCallLog.call_type == call_type.upper())

    if phone_number:
        clean_phone = re.sub(r'[^0-9]', '', phone_number)
        if clean_phone:
            base = base.filter(StaffCallLog.phone_number.like(f'%{clean_phone}%'))

    safe_dur = case(
        (and_(StaffCallLog.duration_seconds >= 0, StaffCallLog.duration_seconds <= 14400), StaffCallLog.duration_seconds),
        else_=0
    )

    overall = base.with_entities(
        func.count(StaffCallLog.id).label('total_calls'),
        func.sum(safe_dur).label('total_duration'),
        func.sum(case((StaffCallLog.call_type == 'INCOMING', 1), else_=0)).label('incoming'),
        func.sum(case((StaffCallLog.call_type == 'OUTGOING', 1), else_=0)).label('outgoing'),
        func.sum(case((StaffCallLog.call_type == 'MISSED', 1), else_=0)).label('missed'),
        func.count(distinct(StaffCallLog.phone_number)).label('unique_numbers'),
        func.sum(case((StaffCallLog.matched_lead_id.isnot(None), 1), else_=0)).label('crm_matched'),
        func.count(distinct(StaffCallLog.staff_id)).label('active_staff'),
        func.count(distinct(StaffCallLog.call_date)).label('active_days'),
        func.sum(case((StaffCallLog.source.in_(['dialer', 'autodialer', 'auto_dialer']), safe_dur), else_=0)).label('autodialer_duration'),
        func.sum(case((StaffCallLog.source.in_(['softphone', 'plivo', 'webrtc', 'voip']), safe_dur), else_=0)).label('softphone_duration'),
        func.sum(case((~StaffCallLog.source.in_(['dialer', 'autodialer', 'auto_dialer', 'softphone', 'plivo', 'webrtc', 'voip']), safe_dur), else_=0)).label('other_duration'),
    ).first()

    total_dur = int(overall.total_duration or 0)
    active_days = overall.active_days or 1
    avg_daily = total_dur // active_days if active_days else 0

    per_staff = base.with_entities(
        StaffCallLog.staff_id,
        func.count(StaffCallLog.id).label('total_calls'),
        func.sum(safe_dur).label('total_duration'),
        func.sum(case((StaffCallLog.call_type == 'OUTGOING', 1), else_=0)).label('outgoing'),
        func.sum(case((StaffCallLog.call_type == 'INCOMING', 1), else_=0)).label('incoming'),
        func.sum(case((StaffCallLog.call_type == 'MISSED', 1), else_=0)).label('missed'),
        func.count(distinct(StaffCallLog.phone_number)).label('unique_numbers'),
        func.sum(case((StaffCallLog.matched_lead_id.isnot(None), 1), else_=0)).label('crm_matched'),
        func.count(distinct(StaffCallLog.call_date)).label('active_days'),
        func.sum(case((StaffCallLog.source.in_(['dialer', 'autodialer', 'auto_dialer']), safe_dur), else_=0)).label('autodialer_duration'),
        func.sum(case((StaffCallLog.source.in_(['softphone', 'plivo', 'webrtc', 'voip']), safe_dur), else_=0)).label('softphone_duration'),
        func.sum(case((~StaffCallLog.source.in_(['dialer', 'autodialer', 'auto_dialer', 'softphone', 'plivo', 'webrtc', 'voip']), safe_dur), else_=0)).label('other_duration'),
    ).group_by(StaffCallLog.staff_id).order_by(func.count(StaffCallLog.id).desc()).all()

    staff_ids = [s.staff_id for s in per_staff]
    staff_map = {}
    sync_map = {}
    if staff_ids:
        dept_cache = {}
        staff_filter = [
            StaffEmployee.id.in_(staff_ids),
            StaffEmployee.status == 'active',
            StaffEmployee.is_deleted == False,
        ]
        if not is_saas:
            staff_filter.extend([
                StaffEmployee.emp_code != 'MR10001',
                ~StaffEmployee.emp_code.like('EMP_TEST_%'),
                or_(StaffEmployee.staff_type.is_(None), ~StaffEmployee.staff_type.in_(['SAAS_CLIENT', 'TENANT_ADMIN', 'SAAS_SEGMENT_ADMIN']))
            ])
        rows = db.query(
            StaffEmployee.id, StaffEmployee.full_name, StaffEmployee.emp_code,
            StaffEmployee.department_id, StaffEmployee.reporting_manager_id,
            StaffEmployee.call_tracking_enabled
        ).filter(*staff_filter).all()
        dept_ids = list({r.department_id for r in rows if r.department_id})
        if dept_ids:
            depts = db.query(StaffDepartment.id, StaffDepartment.name).filter(StaffDepartment.id.in_(dept_ids)).all()
            dept_cache = {d.id: d.name for d in depts}
        staff_map = {
            r.id: {
                'name': r.full_name,
                'staff_name': r.full_name,
                'emp_code': r.emp_code,
                'dept_id': r.department_id,
                'department': dept_cache.get(r.department_id, ''),
                'mgr_id': r.reporting_manager_id,
                'call_tracking_enabled': r.call_tracking_enabled
            } for r in rows
        }
        sync_rows = db.query(
            StaffCallSyncLog.staff_id,
            func.max(StaffCallSyncLog.sync_completed_at).label('last_synced_at')
        ).filter(
            StaffCallSyncLog.staff_id.in_(staff_ids),
            StaffCallSyncLog.status == 'completed'
        ).group_by(StaffCallSyncLog.staff_id).all()
        sync_map = {r.staff_id: r.last_synced_at for r in sync_rows}

        # DC Protocol: Fetch active time, worked time, KRA time, and Task/Solar time from StaffAttendance & StaffActivityTimeLog
        attendance_map = {}
        activity_time_map = {}
        kra_inst_map = {}
        try:
            d_from = date.fromisoformat(date_from) if isinstance(date_from, str) else date_from
            d_to = date.fromisoformat(date_to) if isinstance(date_to, str) else date_to
            att_rows = db.query(
                StaffAttendance.employee_id,
                func.coalesce(func.sum(StaffAttendance.active_minutes), 0).label('active_min'),
                func.coalesce(func.sum(StaffAttendance.activity_minutes_total), 0).label('activity_min'),
                func.coalesce(func.sum(StaffAttendance.worked_minutes), 0).label('worked_min'),
                func.coalesce(func.sum(StaffAttendance.kra_minutes), 0).label('kra_min'),
                func.coalesce(func.sum(StaffAttendance.task_minutes), 0).label('task_min'),
                func.coalesce(func.sum(StaffAttendance.dayplan_minutes), 0).label('dayplan_min'),
                func.coalesce(func.sum(StaffAttendance.journey_minutes), 0).label('journey_min'),
                func.coalesce(func.sum(StaffAttendance.custom_minutes), 0).label('custom_min'),
            ).filter(
                StaffAttendance.employee_id.in_(staff_ids),
                StaffAttendance.date >= d_from,
                StaffAttendance.date <= d_to
            ).group_by(StaffAttendance.employee_id).all()
            
            for r in att_rows:
                attendance_map[r.employee_id] = {
                    'active_minutes': max(int(r.active_min or 0), int(r.activity_min or 0)),
                    'worked_minutes': int(r.worked_min or 0),
                    'kra_minutes': int(r.kra_min or 0),
                    'task_minutes': int(r.task_min or 0) + int(r.dayplan_min or 0) + int(r.journey_min or 0) + int(r.custom_min or 0),
                    'activity_total': int(r.activity_min or 0),
                }

            # Query staff_activity_time_log for detailed KRA and Solar/tasks
            act_rows = db.query(
                StaffActivityTimeLog.employee_id,
                func.coalesce(func.sum(StaffActivityTimeLog.completed_minutes), 0).label('total_min'),
                func.coalesce(func.sum(case((StaffActivityTimeLog.source_type == 'kra', StaffActivityTimeLog.completed_minutes), else_=0)), 0).label('kra_min'),
                func.coalesce(func.sum(case((StaffActivityTimeLog.source_type != 'kra', StaffActivityTimeLog.completed_minutes), else_=0)), 0).label('task_min'),
            ).filter(
                StaffActivityTimeLog.employee_id.in_(staff_ids),
                StaffActivityTimeLog.date >= d_from,
                StaffActivityTimeLog.date <= d_to
            ).group_by(StaffActivityTimeLog.employee_id).all()

            for ar in act_rows:
                activity_time_map[ar.employee_id] = {
                    'total_min': int(ar.total_min or 0),
                    'kra_min': int(ar.kra_min or 0),
                    'task_min': int(ar.task_min or 0),
                }

            # Query daily KRA instances if any
            kra_inst_rows = db.query(
                StaffKRADailyInstance.employee_id,
                func.coalesce(func.sum(StaffKRADailyInstance.time_spent_minutes), 0).label('kra_inst_min')
            ).filter(
                StaffKRADailyInstance.employee_id.in_(staff_ids),
                StaffKRADailyInstance.instance_date >= d_from,
                StaffKRADailyInstance.instance_date <= d_to
            ).group_by(StaffKRADailyInstance.employee_id).all()
            kra_inst_map = {kr.employee_id: int(kr.kra_inst_min or 0) for kr in kra_inst_rows}
        except Exception as att_err:
            try:
                db.rollback()
            except Exception:
                pass
            print(f"[CT_OVERVIEW] Error fetching attendance active time: {att_err}")

    # Fix A — DC Protocol: Sync status for zero-data scenarios
    # When per_staff is empty, return sync context so frontend can show a meaningful banner
    sync_status = None
    if not per_staff:
        if staff_id:
            # Specific staff filtered but no call data — check their sync history
            sync_row = db.query(
                func.max(StaffCallSyncLog.sync_completed_at).label('last_synced_at'),
                func.coalesce(func.sum(StaffCallSyncLog.records_synced), 0).label('total_records_synced')
            ).filter(
                StaffCallSyncLog.staff_id == staff_id,
                StaffCallSyncLog.status == 'completed'
            ).first()
            staff_info = db.query(
                StaffEmployee.full_name, StaffEmployee.emp_code
            ).filter(StaffEmployee.id == staff_id).first()
            sync_status = {
                "type": "specific_staff",
                "staff_id": staff_id,
                "staff_name": staff_info.full_name if staff_info else "Unknown",
                "emp_code": staff_info.emp_code if staff_info else "",
                "last_synced_at": sync_row.last_synced_at.isoformat() if (sync_row and sync_row.last_synced_at) else None,
                "total_records_synced": int(sync_row.total_records_synced or 0) if sync_row else 0,
            }
        else:
            # All-staff / scope-wide — check how many in scope have ever synced
            scope_ids = filtered_staff_ids if filtered_staff_ids is not None else (team_scope_ids if team_scope_ids is not None else None)
            sync_q = db.query(
                func.count(distinct(StaffCallSyncLog.staff_id)).label('synced_count')
            ).filter(StaffCallSyncLog.status == 'completed')
            if scope_ids is not None:
                sync_q = sync_q.filter(StaffCallSyncLog.staff_id.in_(scope_ids))
            sync_count_row = sync_q.first()
            sync_status = {
                "type": "all_staff",
                "synced_staff_count": int(sync_count_row.synced_count or 0) if sync_count_row else 0,
            }

    daily = base.with_entities(
        StaffCallLog.call_date,
        func.count(StaffCallLog.id).label('calls'),
        func.sum(safe_dur).label('duration'),
        func.sum(case((StaffCallLog.call_type == 'MISSED', 1), else_=0)).label('missed'),
        func.sum(case((StaffCallLog.call_type == 'OUTGOING', 1), else_=0)).label('outgoing'),
        func.sum(case((StaffCallLog.call_type == 'INCOMING', 1), else_=0)).label('incoming'),
    ).group_by(StaffCallLog.call_date).order_by(StaffCallLog.call_date.desc()).limit(60).all()

    if is_saas:
        staff_list_q = db.query(
            StaffEmployee.id, StaffEmployee.full_name, StaffEmployee.emp_code, StaffEmployee.call_tracking_enabled
        ).filter(
            StaffEmployee.status == 'active',
            StaffEmployee.is_deleted == False,
            StaffEmployee.id.in_(saas_staff_ids)
        )
        staff_list = staff_list_q.order_by(StaffEmployee.full_name).all()
        departments = []
        managers = db.query(StaffEmployee.id, StaffEmployee.full_name, StaffEmployee.emp_code).filter(
            StaffEmployee.status == 'active',
            StaffEmployee.is_deleted == False,
            StaffEmployee.id.in_(saas_staff_ids)
        ).order_by(StaffEmployee.full_name).all()
    else:
        staff_list_q = db.query(
            StaffEmployee.id, StaffEmployee.full_name, StaffEmployee.emp_code, StaffEmployee.call_tracking_enabled
        ).filter(
            StaffEmployee.status == 'active',
            StaffEmployee.is_deleted == False,
            StaffEmployee.emp_code != 'MR10001',
            ~StaffEmployee.emp_code.like('EMP_TEST_%'),
            or_(StaffEmployee.staff_type.is_(None), ~StaffEmployee.staff_type.in_(['SAAS_CLIENT', 'TENANT_ADMIN', 'SAAS_SEGMENT_ADMIN']))
        )
        if team_scope_ids is not None:
            staff_list_q = staff_list_q.filter(StaffEmployee.id.in_(team_scope_ids))
        staff_list = staff_list_q.order_by(StaffEmployee.full_name).all()

        departments = db.query(StaffDepartment.id, StaffDepartment.name).filter(
            StaffDepartment.is_active == True
        ).order_by(StaffDepartment.name).all()

        managers = db.query(StaffEmployee.id, StaffEmployee.full_name, StaffEmployee.emp_code).filter(
            StaffEmployee.status == 'active',
            StaffEmployee.is_deleted == False,
            StaffEmployee.emp_code != 'MR10001',
            ~StaffEmployee.emp_code.like('EMP_TEST_%'),
            or_(StaffEmployee.staff_type.is_(None), ~StaffEmployee.staff_type.in_(['SAAS_CLIENT', 'TENANT_ADMIN', 'SAAS_SEGMENT_ADMIN'])),
            StaffEmployee.id.in_(
                db.query(distinct(StaffEmployee.reporting_manager_id)).filter(
                    StaffEmployee.reporting_manager_id.isnot(None)
                )
            )
        ).order_by(StaffEmployee.full_name).all()

    # DC Protocol (Apr 2026): Batch-fetch VGK Created + WA Shares per staff for same date range
    vgk_map_ct: dict = {}
    wa_map_ct: dict = {}
    try:
        if staff_ids:
            ct_df = f"{date_from} 00:00:00" if date_from else "2000-01-01 00:00:00"
            ct_dt = f"{date_to} 23:59:59" if date_to else "2099-12-31 23:59:59"
            vgk_ct_rows = db.execute(text(
                "SELECT staff_id, COUNT(*) FROM crm_wa_share_logs "
                "WHERE staff_id = ANY(:ids) AND share_type='vgk_registration' "
                "AND created_at BETWEEN :df AND :dt GROUP BY staff_id"
            ), {"ids": staff_ids, "df": ct_df, "dt": ct_dt}).fetchall()
            wa_ct_rows = db.execute(text(
                "SELECT staff_id, COUNT(*) FROM crm_wa_share_logs "
                "WHERE staff_id = ANY(:ids) AND share_type='vgk_creds' "
                "AND created_at BETWEEN :df AND :dt GROUP BY staff_id"
            ), {"ids": staff_ids, "df": ct_df, "dt": ct_dt}).fetchall()
            vgk_map_ct = {r[0]: int(r[1]) for r in vgk_ct_rows}
            wa_map_ct = {r[0]: int(r[1]) for r in wa_ct_rows}
    except Exception:
        pass

    # DC Protocol: Batch-fetch Auto Dialer durations per staff from crm_dialer_attempts
    dialer_map_ct: dict = {}
    try:
        if staff_ids:
            ct_df = f"{date_from} 00:00:00" if date_from else "2000-01-01 00:00:00"
            ct_dt = f"{date_to} 23:59:59" if date_to else "2099-12-31 23:59:59"
            str_staff_ids = [str(sid) for sid in staff_ids]
            dialer_rows = db.execute(text(
                "SELECT user_ref, COALESCE(SUM(duration_seconds), 0) "
                "FROM crm_dialer_attempts "
                "WHERE user_ref = ANY(:ids) AND created_at BETWEEN :df AND :dt "
                "AND duration_seconds BETWEEN 0 AND 14400 GROUP BY user_ref"
            ), {"ids": str_staff_ids, "df": ct_df, "dt": ct_dt}).fetchall()
            dialer_map_ct = {int(r[0]): int(r[1]) for r in dialer_rows if str(r[0]).isdigit()}
    except Exception as d_err:
        print(f"[CT_OVERVIEW] Error fetching dialer attempts: {d_err}")

    # Calculate channel durations for each staff member
    staff_channel_durations = {}
    for s in per_staff:
        tot_staff_dur = int(s.total_duration or 0)
        direct_dialer = int(getattr(s, 'autodialer_duration', 0) or 0)
        att_dialer = dialer_map_ct.get(s.staff_id, 0)
        autodialer_sec = min(tot_staff_dur, max(direct_dialer, att_dialer))

        raw_softphone = int(getattr(s, 'softphone_duration', 0) or 0)
        raw_other = int(getattr(s, 'other_duration', 0) or 0)

        if raw_softphone >= autodialer_sec:
            softphone_sec = raw_softphone - autodialer_sec
            other_call_sec = raw_other
        else:
            softphone_sec = max(0, tot_staff_dur - autodialer_sec - raw_other)
            other_call_sec = raw_other

        att_item = attendance_map.get(s.staff_id, {})
        act_item = activity_time_map.get(s.staff_id, {})
        k_inst_min = kra_inst_map.get(s.staff_id, 0)

        emp_kra_min = max(att_item.get('kra_minutes', 0), act_item.get('kra_min', 0), k_inst_min)
        emp_task_min = max(att_item.get('task_minutes', 0), act_item.get('task_min', 0))
        emp_other_act_min = max(att_item.get('activity_total', 0), emp_kra_min + emp_task_min, act_item.get('total_min', 0))
        emp_other_act_sec = emp_other_act_min * 60

        other_sec = other_call_sec + emp_other_act_sec
        breakdown_str = f"KRA: {round(emp_kra_min / 60, 2):.2f} hrs | Tasks & Solar: {round(emp_task_min / 60, 2):.2f} hrs" if (emp_kra_min or emp_task_min) else "0.00 hrs"

        staff_channel_durations[s.staff_id] = {
            'autodialer_sec': autodialer_sec,
            'softphone_sec': softphone_sec,
            'other_sec': other_sec,
            'kra_min': emp_kra_min,
            'task_min': emp_task_min,
            'other_breakdown': breakdown_str
        }

    ov_autodialer_sec = sum(ch['autodialer_sec'] for ch in staff_channel_durations.values())
    ov_softphone_sec = sum(ch['softphone_sec'] for ch in staff_channel_durations.values())
    ov_other_sec = sum(ch['other_sec'] for ch in staff_channel_durations.values())

    return {
        "success": True,
        "overview": {
            "total_calls": overall.total_calls or 0,
            "total_duration_seconds": total_dur,
            "incoming": overall.incoming or 0,
            "outgoing": overall.outgoing or 0,
            "missed": overall.missed or 0,
            "unique_numbers": overall.unique_numbers or 0,
            "crm_matched": overall.crm_matched or 0,
            "active_staff": overall.active_staff or 0,
            "avg_daily_talk_time": avg_daily,
            "autodialer_duration_seconds": ov_autodialer_sec,
            "autodialer_hours": f"{round(ov_autodialer_sec / 3600, 2):.2f} hrs",
            "softphone_duration_seconds": ov_softphone_sec,
            "softphone_hours": f"{round(ov_softphone_sec / 3600, 2):.2f} hrs",
            "other_duration_seconds": ov_other_sec,
            "other_hours": f"{round(ov_other_sec / 3600, 2):.2f} hrs",
        },
        "per_staff": [{
            'staff_id': s.staff_id,
            'name': staff_map.get(s.staff_id, {}).get('name', 'Unknown'),
            'staff_name': staff_map.get(s.staff_id, {}).get('name', 'Unknown'),
            'emp_code': staff_map.get(s.staff_id, {}).get('emp_code', ''),
            'dept_id': staff_map.get(s.staff_id, {}).get('dept_id'),
            'department': staff_map.get(s.staff_id, {}).get('department', ''),
            'mgr_id': staff_map.get(s.staff_id, {}).get('mgr_id'),
            'call_tracking_enabled': staff_map.get(s.staff_id, {}).get('call_tracking_enabled', False),
            'total_calls': s.total_calls,
            'total_duration': int(s.total_duration or 0),
            'total_duration_seconds': int(s.total_duration or 0),
            'outgoing': s.outgoing or 0,
            'incoming': s.incoming or 0,
            'missed': s.missed or 0,
            'unique_numbers': s.unique_numbers or 0,
            'crm_matched': s.crm_matched or 0,
            'avg_daily_talk_time': int(s.total_duration or 0) // max(s.active_days or 1, 1),
            'autodialer_duration_seconds': staff_channel_durations.get(s.staff_id, {}).get('autodialer_sec', 0),
            'autodialer_hours': f"{round(staff_channel_durations.get(s.staff_id, {}).get('autodialer_sec', 0) / 3600, 2):.2f} hrs",
            'softphone_duration_seconds': staff_channel_durations.get(s.staff_id, {}).get('softphone_sec', 0),
            'softphone_hours': f"{round(staff_channel_durations.get(s.staff_id, {}).get('softphone_sec', 0) / 3600, 2):.2f} hrs",
            'other_duration_seconds': staff_channel_durations.get(s.staff_id, {}).get('other_sec', 0),
            'other_hours': f"{round(staff_channel_durations.get(s.staff_id, {}).get('other_sec', 0) / 3600, 2):.2f} hrs",
            'other_kra_minutes': staff_channel_durations.get(s.staff_id, {}).get('kra_min', 0),
            'other_task_minutes': staff_channel_durations.get(s.staff_id, {}).get('task_min', 0),
            'other_breakdown': staff_channel_durations.get(s.staff_id, {}).get('other_breakdown', '0.00 hrs'),
            'active_time_minutes': attendance_map.get(s.staff_id, {}).get('active_minutes', 0),
            'active_time_hours': f"{round(attendance_map.get(s.staff_id, {}).get('active_minutes', 0) / 60, 2):.2f} hrs",
            'worked_hours': f"{round(attendance_map.get(s.staff_id, {}).get('worked_minutes', 0) / 60, 2):.2f} hrs",
            'active_percentage': min(100, round((attendance_map.get(s.staff_id, {}).get('active_minutes', 0) / max(attendance_map.get(s.staff_id, {}).get('worked_minutes', 1), 1)) * 100)) if attendance_map.get(s.staff_id, {}).get('worked_minutes', 0) > 0 else 0,
            'last_synced_at': sync_map[s.staff_id].isoformat() if sync_map.get(s.staff_id) else None,
            'vgk_created': vgk_map_ct.get(s.staff_id, 0),
            'wa_shares': wa_map_ct.get(s.staff_id, 0),
        } for s in per_staff if s.staff_id in staff_map and staff_map[s.staff_id].get('emp_code') != 'MR10001'],
        "daily_trend": [{
            'date': d.call_date,
            'calls': d.calls,
            'duration': int(d.duration or 0),
            'missed': d.missed or 0,
            'outgoing': d.outgoing or 0,
            'incoming': d.incoming or 0,
        } for d in daily],
        "staff_list": [{'id': s.id, 'name': s.full_name, 'emp_code': s.emp_code, 'call_tracking_enabled': s.call_tracking_enabled} for s in staff_list if s.emp_code != 'MR10001'],
        "departments": [{'id': d.id, 'name': d.name} for d in departments],
        "managers": [{'id': m.id, 'name': m.full_name, 'emp_code': m.emp_code} for m in managers],
        "date_range": {"from": date_from, "to": date_to},
        "filters_applied": {
            "department_id": department_id,
            "reporting_manager_id": reporting_manager_id,
            "call_type": call_type,
            "staff_id": staff_id,
            "phone_number": phone_number,
        },
        "sync_status": sync_status,
    }


@router.get("/management/slot-breakdown")
async def get_call_slot_breakdown(
    date_from: str = Query(None),
    date_to: str = Query(None),
    quick_range: str = Query(None, description="today, yesterday, this_week, last_week, this_month, last_month, last_7, last_30"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_hybrid)
):
    """
    CT Protocol: 2-hour slot call activity breakdown per staff member.
    Slots: 09:30-11:30, 11:30-13:30, 13:30-15:30, 15:30-17:30, 17:30-19:30, Other.
    Multi-day ranges return raw totals; frontend divides by day_count for averages.
    Access: CT_FULL_ACCESS = full org | has downline = own team | individual = self only.
    """
    if not hasattr(current_user, 'emp_code'):
        raise HTTPException(status_code=403, detail="Staff access required")

    staff = db.query(StaffEmployee).filter(StaffEmployee.id == current_user.id).first()
    if not staff:
        raise HTTPException(status_code=404, detail="Staff not found")

    now = get_indian_time()
    today = now.date()

    if quick_range:
        if quick_range == 'today':
            date_from = today.strftime('%Y-%m-%d')
            date_to = today.strftime('%Y-%m-%d')
        elif quick_range == 'yesterday':
            yd = today - timedelta(days=1)
            date_from = yd.strftime('%Y-%m-%d')
            date_to = yd.strftime('%Y-%m-%d')
        elif quick_range == 'this_week':
            start = today - timedelta(days=today.weekday())
            date_from = start.strftime('%Y-%m-%d')
            date_to = today.strftime('%Y-%m-%d')
        elif quick_range == 'last_week':
            end = today - timedelta(days=today.weekday() + 1)
            start = end - timedelta(days=6)
            date_from = start.strftime('%Y-%m-%d')
            date_to = end.strftime('%Y-%m-%d')
        elif quick_range == 'this_month':
            date_from = today.replace(day=1).strftime('%Y-%m-%d')
            date_to = today.strftime('%Y-%m-%d')
        elif quick_range == 'last_month':
            first_this = today.replace(day=1)
            end_lm = first_this - timedelta(days=1)
            start_lm = end_lm.replace(day=1)
            date_from = start_lm.strftime('%Y-%m-%d')
            date_to = end_lm.strftime('%Y-%m-%d')
        elif quick_range == 'last_7':
            date_from = (today - timedelta(days=6)).strftime('%Y-%m-%d')
            date_to = today.strftime('%Y-%m-%d')
        elif quick_range == 'last_30':
            date_from = (today - timedelta(days=29)).strftime('%Y-%m-%d')
            date_to = today.strftime('%Y-%m-%d')

    if not date_from:
        date_from = today.strftime('%Y-%m-%d')
    if not date_to:
        date_to = today.strftime('%Y-%m-%d')

    # CT Protocol: Role-based team scoping — mirrors management/overview exactly
    is_saas, saas_staff_ids, saas_company_ids = resolve_call_tracking_scope(db, staff)
    if is_saas:
        if not saas_staff_ids or not saas_company_ids:
            return {"success": True, "slot_summary": {}, "per_staff_slots": [], "date_range": {"from": date_from, "to": date_to}}
        team_scope_ids = saas_staff_ids
        is_full_access = False
    else:
        is_full_access = is_ct_full_access(current_user)
        team_scope_ids = None

        if not is_full_access:
            team_scope_ids = get_team_member_ids(current_user, db, StaffEmployee)
            if not team_scope_ids:
                team_scope_ids = [current_user.id]

    from datetime import date as _date_cls
    try:
        d_from = _date_cls.fromisoformat(date_from)
        d_to = _date_cls.fromisoformat(date_to)
    except ValueError:
        d_from = d_to = today
        date_from = date_to = today.strftime('%Y-%m-%d')
    day_count = max((d_to - d_from).days + 1, 1)
    is_multi_day = day_count > 1

    q = db.query(
        StaffCallLog.staff_id,
        StaffCallLog.call_datetime,
        StaffCallLog.call_type,
        StaffCallLog.duration_seconds,
        StaffCallLog.matched_lead_id,
    ).filter(
        StaffCallLog.call_date >= date_from,
        StaffCallLog.call_date <= date_to,
    )
    if is_saas:
        q = q.filter(
            StaffCallLog.staff_id.in_(saas_staff_ids),
            StaffCallLog.company_id.in_(saas_company_ids)
        )
    elif team_scope_ids is not None:
        q = q.filter(StaffCallLog.staff_id.in_(team_scope_ids))
    logs = q.all()

    SLOT_DEFS = [
        ('slot_1', 570, 690, '09:30\u201311:30'),
        ('slot_2', 690, 810, '11:30\u201313:30'),
        ('slot_3', 810, 930, '13:30\u201315:30'),
        ('slot_4', 930, 1050, '15:30\u201317:30'),
        ('slot_5', 1050, 1170, '17:30\u201319:30'),
    ]

    def _slot_key(dt):
        if dt is None:
            return 'other'
        mins = dt.hour * 60 + dt.minute
        for key, s, e, _ in SLOT_DEFS:
            if s <= mins < e:
                return key
        return 'other'

    def _empty():
        return {'calls': 0, 'answered': 0, 'incoming': 0, 'outgoing': 0, 'missed': 0, 'duration_seconds': 0, 'crm_matched': 0}

    ALL_SLOT_KEYS = ['slot_1', 'slot_2', 'slot_3', 'slot_4', 'slot_5', 'other']

    staff_data = {}
    for log in logs:
        sid = log.staff_id
        if sid not in staff_data:
            staff_data[sid] = {k: _empty() for k in ALL_SLOT_KEYS}
        sk = _slot_key(log.call_datetime)
        s = staff_data[sid][sk]
        safe_dur = log.duration_seconds or 0
        if safe_dur < 0 or safe_dur > 14400:
            safe_dur = 0
        s['calls'] += 1
        s['duration_seconds'] += safe_dur
        ctype = (log.call_type or '').upper()
        if ctype == 'OUTGOING':
            s['outgoing'] += 1
        elif ctype == 'INCOMING':
            s['incoming'] += 1
        elif ctype == 'MISSED':
            s['missed'] += 1
        if safe_dur > 0:
            s['answered'] += 1
        if log.matched_lead_id:
            s['crm_matched'] += 1

    def _total(slots_dict):
        t = _empty()
        for s in slots_dict.values():
            for k in t:
                t[k] += s[k]
        return t

    staff_ids = list(staff_data.keys())
    staff_info_map = {}
    attendance_map = {}
    dialer_map_ct = {}
    if staff_ids:
        dept_cache = {}
        rows = db.query(
            StaffEmployee.id, StaffEmployee.full_name, StaffEmployee.emp_code,
            StaffEmployee.department_id, StaffEmployee.call_tracking_enabled
        ).filter(
            StaffEmployee.id.in_(staff_ids),
            StaffEmployee.status == 'active',
            StaffEmployee.is_deleted == False,
            StaffEmployee.emp_code != 'MR10001',
            ~StaffEmployee.emp_code.like('EMP_TEST_%'),
            or_(StaffEmployee.staff_type.is_(None), ~StaffEmployee.staff_type.in_(['SAAS_CLIENT', 'TENANT_ADMIN', 'SAAS_SEGMENT_ADMIN']))
        ).all()
        dept_ids = list({r.department_id for r in rows if r.department_id})
        if dept_ids:
            depts = db.query(StaffDepartment.id, StaffDepartment.name).filter(StaffDepartment.id.in_(dept_ids)).all()
            dept_cache = {d.id: d.name for d in depts}
        for r in rows:
            staff_info_map[r.id] = {
                'name': r.full_name or '',
                'emp_code': r.emp_code or '',
                'department': dept_cache.get(r.department_id, ''),
                'call_tracking_enabled': bool(r.call_tracking_enabled),
            }

        # DC Protocol: Fetch active time, worked time, KRA time, and Task/Solar time from StaffAttendance & StaffActivityTimeLog
        activity_time_map = {}
        kra_inst_map = {}
        try:
            att_rows = db.query(
                StaffAttendance.employee_id,
                func.coalesce(func.sum(StaffAttendance.active_minutes), 0).label('active_min'),
                func.coalesce(func.sum(StaffAttendance.activity_minutes_total), 0).label('activity_min'),
                func.coalesce(func.sum(StaffAttendance.worked_minutes), 0).label('worked_min'),
                func.coalesce(func.sum(StaffAttendance.kra_minutes), 0).label('kra_min'),
                func.coalesce(func.sum(StaffAttendance.task_minutes), 0).label('task_min'),
                func.coalesce(func.sum(StaffAttendance.dayplan_minutes), 0).label('dayplan_min'),
                func.coalesce(func.sum(StaffAttendance.journey_minutes), 0).label('journey_min'),
                func.coalesce(func.sum(StaffAttendance.custom_minutes), 0).label('custom_min'),
            ).filter(
                StaffAttendance.employee_id.in_(staff_ids),
                StaffAttendance.date >= d_from,
                StaffAttendance.date <= d_to
            ).group_by(StaffAttendance.employee_id).all()
            for r in att_rows:
                attendance_map[r.employee_id] = {
                    'active_minutes': max(int(r.active_min or 0), int(r.activity_min or 0)),
                    'worked_minutes': int(r.worked_min or 0),
                    'kra_minutes': int(r.kra_min or 0),
                    'task_minutes': int(r.task_min or 0) + int(r.dayplan_min or 0) + int(r.journey_min or 0) + int(r.custom_min or 0),
                    'activity_total': int(r.activity_min or 0),
                }

            # Query staff_activity_time_log for detailed KRA and Solar/tasks
            act_rows = db.query(
                StaffActivityTimeLog.employee_id,
                func.coalesce(func.sum(StaffActivityTimeLog.completed_minutes), 0).label('total_min'),
                func.coalesce(func.sum(case((StaffActivityTimeLog.source_type == 'kra', StaffActivityTimeLog.completed_minutes), else_=0)), 0).label('kra_min'),
                func.coalesce(func.sum(case((StaffActivityTimeLog.source_type != 'kra', StaffActivityTimeLog.completed_minutes), else_=0)), 0).label('task_min'),
            ).filter(
                StaffActivityTimeLog.employee_id.in_(staff_ids),
                StaffActivityTimeLog.date >= d_from,
                StaffActivityTimeLog.date <= d_to
            ).group_by(StaffActivityTimeLog.employee_id).all()

            for ar in act_rows:
                activity_time_map[ar.employee_id] = {
                    'total_min': int(ar.total_min or 0),
                    'kra_min': int(ar.kra_min or 0),
                    'task_min': int(ar.task_min or 0),
                }

            # Query daily KRA instances if any
            kra_inst_rows = db.query(
                StaffKRADailyInstance.employee_id,
                func.coalesce(func.sum(StaffKRADailyInstance.time_spent_minutes), 0).label('kra_inst_min')
            ).filter(
                StaffKRADailyInstance.employee_id.in_(staff_ids),
                StaffKRADailyInstance.instance_date >= d_from,
                StaffKRADailyInstance.instance_date <= d_to
            ).group_by(StaffKRADailyInstance.employee_id).all()
            kra_inst_map = {kr.employee_id: int(kr.kra_inst_min or 0) for kr in kra_inst_rows}
        except Exception as att_err:
            try:
                db.rollback()
            except Exception:
                pass
            print(f"[CT_SLOTS] Attendance fetch error: {att_err}")

        # DC Protocol: Fetch Auto Dialer duration from crm_dialer_attempts
        try:
            ct_df = f"{date_from} 00:00:00" if date_from else "2000-01-01 00:00:00"
            ct_dt = f"{date_to} 23:59:59" if date_to else "2099-12-31 23:59:59"
            str_staff_ids = [str(sid) for sid in staff_ids]
            dialer_rows = db.execute(text(
                "SELECT user_ref, COALESCE(SUM(duration_seconds), 0) "
                "FROM crm_dialer_attempts "
                "WHERE user_ref = ANY(:ids) AND created_at BETWEEN :df AND :dt "
                "AND duration_seconds BETWEEN 0 AND 14400 GROUP BY user_ref"
            ), {"ids": str_staff_ids, "df": ct_df, "dt": ct_dt}).fetchall()
            dialer_map_ct = {int(r[0]): int(r[1]) for r in dialer_rows if str(r[0]).isdigit()}
        except Exception as d_err:
            print(f"[CT_SLOTS] Dialer fetch error: {d_err}")

    org_slots = {k: _empty() for k in ALL_SLOT_KEYS}
    per_staff_result = []
    for sid, slots in sorted(staff_data.items(), key=lambda x: -_total(x[1])['calls']):
        info = staff_info_map.get(sid)
        if not info:
            continue
        total = _total(slots)
        for sk in ALL_SLOT_KEYS:
            for metric in org_slots[sk]:
                org_slots[sk][metric] += slots[sk][metric]
            s_item = slots[sk]
            s_dur = s_item['duration_seconds']
            s_calls = s_item['calls']
            s_hrs_num = round(s_dur / 3600, 2)
            s_item['duration_hours'] = f"{s_hrs_num:.2f} hrs"
            s_item['formatted'] = f"{s_hrs_num:.2f} hrs / {s_calls}"

        tot_dur = total['duration_seconds']
        tot_calls = total['calls']
        tot_hrs_num = round(tot_dur / 3600, 2)
        total['duration_hours'] = f"{tot_hrs_num:.2f} hrs"
        total['formatted'] = f"{tot_hrs_num:.2f} hrs / {tot_calls}"

        autodialer_sec = min(tot_dur, dialer_map_ct.get(sid, 0))
        softphone_sec = max(0, tot_dur - autodialer_sec)

        att_info = attendance_map.get(sid, {})
        act_info = activity_time_map.get(sid, {})
        k_inst_min = kra_inst_map.get(sid, 0)

        emp_kra_min = max(att_info.get('kra_minutes', 0), act_info.get('kra_min', 0), k_inst_min)
        emp_task_min = max(att_info.get('task_minutes', 0), act_info.get('task_min', 0))
        emp_other_act_min = max(att_info.get('activity_total', 0), emp_kra_min + emp_task_min, act_info.get('total_min', 0))
        emp_other_act_sec = emp_other_act_min * 60

        other_sec = emp_other_act_sec
        breakdown_str = f"KRA: {round(emp_kra_min / 60, 2):.2f} hrs | Tasks & Solar: {round(emp_task_min / 60, 2):.2f} hrs" if (emp_kra_min or emp_task_min) else "0.00 hrs"

        act_min = att_info.get('active_minutes', 0)
        wrk_min = att_info.get('worked_minutes', 0)
        act_pct = min(100, round((act_min / max(wrk_min, 1)) * 100)) if wrk_min > 0 else 0

        per_staff_result.append({
            'staff_id': sid,
            'name': info['name'],
            'emp_code': info['emp_code'],
            'department': info['department'],
            'call_tracking_enabled': info['call_tracking_enabled'],
            'active_time_minutes': act_min,
            'active_time_hours': f"{round(act_min / 60, 2):.2f} hrs",
            'worked_hours': f"{round(wrk_min / 60, 2):.2f} hrs",
            'active_percentage': act_pct,
            'autodialer_duration_seconds': autodialer_sec,
            'autodialer_hours': f"{round(autodialer_sec / 3600, 2):.2f} hrs",
            'softphone_duration_seconds': softphone_sec,
            'softphone_hours': f"{round(softphone_sec / 3600, 2):.2f} hrs",
            'other_duration_seconds': other_sec,
            'other_hours': f"{round(other_sec / 3600, 2):.2f} hrs",
            'other_kra_minutes': emp_kra_min,
            'other_task_minutes': emp_task_min,
            'other_breakdown': breakdown_str,
            'slots': slots,
            'total': total,
        })

    org_total = _total(org_slots)
    for sk in ALL_SLOT_KEYS:
        os_item = org_slots[sk]
        os_hrs = round(os_item['duration_seconds'] / 3600, 2)
        os_item['duration_hours'] = f"{os_hrs:.2f} hrs"
        os_item['formatted'] = f"{os_hrs:.2f} hrs / {os_item['calls']}"

    ot_hrs = round(org_total['duration_seconds'] / 3600, 2)
    org_total['duration_hours'] = f"{ot_hrs:.2f} hrs"
    org_total['formatted'] = f"{ot_hrs:.2f} hrs / {org_total['calls']}"
    org_total['autodialer_duration_seconds'] = sum(r.get('autodialer_duration_seconds', 0) for r in per_staff_result)
    org_total['autodialer_hours'] = f"{round(org_total['autodialer_duration_seconds'] / 3600, 2):.2f} hrs"
    org_total['softphone_duration_seconds'] = sum(r.get('softphone_duration_seconds', 0) for r in per_staff_result)
    org_total['softphone_hours'] = f"{round(org_total['softphone_duration_seconds'] / 3600, 2):.2f} hrs"
    org_total['other_duration_seconds'] = sum(r.get('other_duration_seconds', 0) for r in per_staff_result)
    org_total['other_hours'] = f"{round(org_total['other_duration_seconds'] / 3600, 2):.2f} hrs"

    return {
        "success": True,
        "is_multi_day": is_multi_day,
        "day_count": day_count,
        "date_range": {"from": date_from, "to": date_to},
        "slot_labels": {
            'slot_1': '09:30\u201311:30', 'slot_2': '11:30\u201313:30', 'slot_3': '13:30\u201315:30',
            'slot_4': '15:30\u201317:30', 'slot_5': '17:30\u201319:30', 'other': 'Other',
        },
        "per_staff": per_staff_result,
        "org_totals": {"slots": org_slots, "total": org_total},
        "is_full_access": is_full_access,
        "viewer_staff_id": current_user.id,
    }


@router.get("/staff/{target_staff_id}/calls")
async def get_staff_call_details(
    target_staff_id: int,
    date_from: str = Query(None),
    date_to: str = Query(None),
    call_type: str = Query(None),
    phone_number: str = Query(None),
    quick_range: str = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(200, ge=1, le=2000),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_hybrid)
):
    # DC Protocol: Menu-based access control
    if not hasattr(current_user, 'emp_code'):
        raise HTTPException(status_code=403, detail="Staff access required")

    viewer = db.query(StaffEmployee).filter(StaffEmployee.id == current_user.id).first()
    if not viewer:
        raise HTTPException(status_code=404, detail="Staff record not found")

    # CT Protocol: scope check — CT_FULL_ACCESS see any staff; others only their downline or self
    is_saas, saas_staff_ids, saas_company_ids = resolve_call_tracking_scope(db, viewer)
    if is_saas:
        if target_staff_id not in set(saas_staff_ids):
            raise HTTPException(status_code=403, detail="Access denied: staff member not in your tenant")
    elif not is_ct_full_access(viewer) and target_staff_id != current_user.id:
        allowed_ids = get_team_member_ids(current_user, db, StaffEmployee)
        if not allowed_ids or target_staff_id not in set(allowed_ids):
            raise HTTPException(status_code=403, detail="Access denied: staff member not in your team")

    now = get_indian_time()
    today = now.date()

    if quick_range:
        if quick_range == 'today':
            date_from = today.strftime('%Y-%m-%d')
            date_to = today.strftime('%Y-%m-%d')
        elif quick_range == 'yesterday':
            yd = today - timedelta(days=1)
            date_from = yd.strftime('%Y-%m-%d')
            date_to = yd.strftime('%Y-%m-%d')
        elif quick_range == 'this_week':
            start = today - timedelta(days=today.weekday())
            date_from = start.strftime('%Y-%m-%d')
            date_to = today.strftime('%Y-%m-%d')
        elif quick_range == 'last_week':
            end = today - timedelta(days=today.weekday() + 1)
            start = end - timedelta(days=6)
            date_from = start.strftime('%Y-%m-%d')
            date_to = end.strftime('%Y-%m-%d')
        elif quick_range == 'this_month':
            date_from = today.replace(day=1).strftime('%Y-%m-%d')
            date_to = today.strftime('%Y-%m-%d')
        elif quick_range == 'last_month':
            first_this = today.replace(day=1)
            end = first_this - timedelta(days=1)
            start = end.replace(day=1)
            date_from = start.strftime('%Y-%m-%d')
            date_to = end.strftime('%Y-%m-%d')
        elif quick_range == 'last_3':
            date_from = (today - timedelta(days=2)).strftime('%Y-%m-%d')
            date_to = today.strftime('%Y-%m-%d')
        elif quick_range == 'last_7':
            date_from = (today - timedelta(days=6)).strftime('%Y-%m-%d')
            date_to = today.strftime('%Y-%m-%d')
        elif quick_range == 'last_30':
            date_from = (today - timedelta(days=29)).strftime('%Y-%m-%d')
            date_to = today.strftime('%Y-%m-%d')

    if not date_from:
        date_from = (now - timedelta(days=2)).strftime('%Y-%m-%d')
    if not date_to:
        date_to = now.strftime('%Y-%m-%d')

    # CT Protocol: employee-based scoping — no company_id filter on call logs
    query = db.query(StaffCallLog).filter(
        StaffCallLog.staff_id == target_staff_id,
        StaffCallLog.call_date >= date_from,
        StaffCallLog.call_date <= date_to
    )
    if is_saas and saas_company_ids:
        query = query.filter(StaffCallLog.company_id.in_(saas_company_ids))
    if call_type:
        query = query.filter(StaffCallLog.call_type == call_type.upper())
    if phone_number:
        clean_phone = re.sub(r'[^0-9]', '', phone_number)
        if clean_phone:
            query = query.filter(StaffCallLog.phone_number.like(f'%{clean_phone}%'))

    total = query.count()
    calls = query.order_by(StaffCallLog.call_datetime.desc()).offset((page - 1) * per_page).limit(per_page).all()

    lead_ids = [c.matched_lead_id for c in calls if c.matched_lead_id]
    lead_info = {}
    if lead_ids:
        lrows = db.query(CRMLead.id, CRMLead.name, CRMLead.status, CRMLead.phone, CRMLead.category_id).filter(CRMLead.id.in_(lead_ids)).all()
        lead_info = {l.id: {'name': l.name, 'status': l.status, 'phone': l.phone, 'category_id': l.category_id} for l in lrows}

    all_phones = list(set(normalize_phone(c.phone_number) for c in calls if c.phone_number))
    contact_map = {}
    if all_phones:
        for lrow in db.query(CRMLead.phone, CRMLead.name, CRMLead.status, CRMLead.id, CRMLead.category_id).filter(
            func.right(func.regexp_replace(CRMLead.phone, r'[^\d]', '', 'g'), 10).in_(all_phones)
        ).all():
            norm = normalize_phone(lrow.phone)
            if norm and norm not in contact_map:
                contact_map[norm] = {'name': lrow.name, 'status': lrow.status, 'lead_id': lrow.id, 'category_id': lrow.category_id}

    cat_rows = db.query(SignupCategory.id, SignupCategory.name).all()
    cat_map = {c.id: c.name for c in cat_rows}

    target = db.query(StaffEmployee.full_name, StaffEmployee.emp_code).filter(
        StaffEmployee.id == target_staff_id
    ).first()

    vcs_map = {}
    vcs_session_ids = [c.device_call_id for c in calls if c.device_call_id and c.device_call_id.startswith('vcs_')]
    if vcs_session_ids:
        try:
            import json
            from app.models.voip_call_session import VoIPCallSession
            v_rows = db.query(VoIPCallSession.call_session_id, VoIPCallSession.metadata_json).filter(
                VoIPCallSession.call_session_id.in_(vcs_session_ids)
            ).all()
            for cs_id, m_json in v_rows:
                if m_json:
                    try:
                        m_data = json.loads(m_json)
                        if m_data.get('dialed_page'):
                            vcs_map[cs_id] = m_data.get('dialed_page')
                    except Exception:
                        pass
        except Exception as e:
            logger.warning(f"[CALL-TRACKING] vcs_map error: {e}")

    def enrich_call(c):
        d = c.to_dict()
        li = lead_info.get(c.matched_lead_id) if c.matched_lead_id else None
        d['matched_lead_name'] = li['name'] if li else None
        d['matched_lead_status'] = li['status'] if li else None
        norm_ph = normalize_phone(c.phone_number)
        ci = contact_map.get(norm_ph)
        d['contact_name_crm'] = ci['name'] if ci else None
        d['contact_lead_id'] = ci['lead_id'] if ci else None
        d['contact_lead_status'] = ci['status'] if ci else None

        lead_cat_id = (li and li.get('category_id')) or (ci and ci.get('category_id'))
        d['category_id'] = lead_cat_id
        d['category_name'] = cat_map.get(lead_cat_id) if lead_cat_id else 'General'
        dial_pg = getattr(c, 'dialed_page', None) or vcs_map.get(c.device_call_id)
        d['dialed_page'] = dial_pg
        d['call_from'] = resolve_call_from(
            source=c.source,
            device_call_id=c.device_call_id,
            call_type=c.call_type,
            dialed_page=dial_pg,
            matched_lead_id=c.matched_lead_id
        )
        return d

    return {
        "success": True,
        "data": {
            "calls": [enrich_call(c) for c in calls],
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": total,
                "pages": (total + per_page - 1) // per_page if total > 0 else 0
            },
            "staff_info": {
                "id": target_staff_id,
                "name": target.full_name if target else "Unknown",
                "emp_code": target.emp_code if target else "",
            }
        }
    }


@router.put("/staff/{target_staff_id}/toggle-tracking")
async def toggle_call_tracking_for_staff(
    target_staff_id: int,
    payload: dict = Body(...),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_hybrid)
):
    """Manager endpoint: enable or disable call tracking for a staff member."""
    if not hasattr(current_user, 'emp_code'):
        raise HTTPException(status_code=403, detail="Staff access required")

    manager = db.query(StaffEmployee).filter(StaffEmployee.id == current_user.id).first()
    if not manager:
        raise HTTPException(status_code=404, detail="Manager record not found")

    target = db.query(StaffEmployee).filter(
        StaffEmployee.id == target_staff_id
    ).first()
    if not target:
        raise HTTPException(status_code=404, detail="Staff member not found")

    enabled = bool(payload.get("enabled", False))
    target.call_tracking_enabled = enabled
    db.commit()
    db.refresh(target)

    return {
        "success": True,
        "staff_id": target_staff_id,
        "staff_name": target.full_name,
        "call_tracking_enabled": target.call_tracking_enabled,
        "message": f"Call tracking {'enabled' if enabled else 'disabled'} for {target.full_name}"
    }


@router.post("/rematch-leads")
async def rematch_call_logs_to_leads(
    company_id: int = Query(None),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_hybrid)
):
    if not hasattr(current_user, 'emp_code'):
        raise HTTPException(status_code=403, detail="Staff access required")

    staff = db.query(StaffEmployee).filter(StaffEmployee.id == current_user.id).first()
    if not staff:
        raise HTTPException(status_code=404, detail="Staff not found")

    all_lead_phones = {}
    leads = db.query(CRMLead.id, CRMLead.phone, CRMLead.alternate_phone).all()
    for lead in leads:
        for ph in [lead.phone, lead.alternate_phone]:
            norm = normalize_phone(ph)
            if norm:
                all_lead_phones[norm] = lead.id

    unmatched = db.query(StaffCallLog).filter(
        StaffCallLog.matched_lead_id.is_(None)
    ).all()

    matched_count = 0
    for call in unmatched:
        norm = normalize_phone(call.phone_number)
        if norm and norm in all_lead_phones:
            call.matched_lead_id = all_lead_phones[norm]
            call.matched_at = get_indian_time()
            matched_count += 1

    db.commit()

    return {
        "success": True,
        "total_unmatched_checked": len(unmatched),
        "newly_matched": matched_count
    }


ALLOWED_AUDIO_EXTENSIONS = {'.mp3', '.m4a', '.amr', '.wav', '.3gp', '.ogg', '.aac', '.wma', '.opus'}
ALLOWED_AUDIO_MIMES = {
    'audio/mpeg', 'audio/mp4', 'audio/amr', 'audio/wav', 'audio/x-wav',
    'audio/3gpp', 'audio/ogg', 'audio/aac', 'audio/x-ms-wma', 'audio/opus',
    'application/octet-stream'
}
MAX_RECORDING_SIZE = 50 * 1024 * 1024
RECORDINGS_BASE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))), 'uploads', 'call_recordings')


@router.post("/recordings/upload")
async def upload_call_recording(
    file: UploadFile = File(...),
    call_log_id: int = Form(None),
    device_call_id: str = Form(None),
    phone_number: str = Form(None),
    call_datetime: str = Form(None),
    device_recording_id: str = Form(None),
    source_device: str = Form(None),
    recorded_at: str = Form(None),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_hybrid)
):
    if not hasattr(current_user, 'emp_code'):
        raise HTTPException(status_code=403, detail="Staff access required")

    staff = db.query(StaffEmployee).filter(StaffEmployee.id == current_user.id).first()
    if not staff:
        raise HTTPException(status_code=404, detail="Staff not found")

    if not staff.call_tracking_enabled and not is_ct_full_access(staff):
        raise HTTPException(status_code=403, detail="Call tracking not enabled for your account")

    company_id = staff.base_company_id
    staff_id = staff.id

    original_filename = file.filename or 'recording.mp3'
    ext = os.path.splitext(original_filename)[1].lower()
    if ext not in ALLOWED_AUDIO_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Invalid audio format. Allowed: {', '.join(ALLOWED_AUDIO_EXTENSIONS)}")

    if device_recording_id:
        existing = db.query(StaffCallRecording.id).filter(
            StaffCallRecording.staff_id == staff_id,
            StaffCallRecording.device_recording_id == device_recording_id
        ).first()
        if existing:
            return {"success": True, "message": "Recording already uploaded", "recording_id": existing.id, "duplicate": True}

    file_content = await file.read()
    file_size = len(file_content)

    if file_size > MAX_RECORDING_SIZE:
        raise HTTPException(status_code=400, detail=f"File too large. Maximum size: {MAX_RECORDING_SIZE // (1024*1024)}MB")

    if file_size == 0:
        raise HTTPException(status_code=400, detail="Empty file")

    now = get_indian_time()
    date_folder = now.strftime('%Y-%m-%d')
    # S3 relative path
    relative_path = f"staff_call_recordings/{company_id}/{staff_id}/{date_folder}/{uuid.uuid4().hex[:12]}_{now.strftime('%H%M%S')}{ext}"

    from app.services.object_storage import storage_service
    storage_service.upload_file(relative_path, file_content)

    content_type = file.content_type or mimetypes.guess_type(original_filename)[0] or 'audio/mpeg'
    # Use relative_path as the storage path so it can be retrieved from S3
    storage_path = relative_path

    parsed_recorded_at = None
    if recorded_at:
        try:
            if isinstance(recorded_at, str):
                parsed_recorded_at = datetime.fromisoformat(recorded_at.replace('Z', '+00:00')).replace(tzinfo=None)
        except (ValueError, TypeError):
            pass

    recording = StaffCallRecording(
        company_id=company_id,
        staff_id=staff_id,
        original_filename=original_filename,
        storage_path=storage_path,
        file_size=file_size,
        mime_type=content_type,
        recorded_at=parsed_recorded_at,
        device_recording_id=device_recording_id,
        source_device=source_device,
        uploaded_at=now
    )
    db.add(recording)
    db.flush()

    matched_call_log = None

    if call_log_id:
        matched_call_log = db.query(StaffCallLog).filter(
            StaffCallLog.id == call_log_id,
            StaffCallLog.staff_id == staff_id
        ).first()
    elif device_call_id:
        matched_call_log = db.query(StaffCallLog).filter(
            StaffCallLog.staff_id == staff_id,
            StaffCallLog.device_call_id == device_call_id
        ).first()
    elif phone_number and call_datetime:
        norm_phone = normalize_phone(phone_number)
        if norm_phone:
            try:
                if isinstance(call_datetime, str):
                    target_dt = datetime.fromisoformat(call_datetime.replace('Z', '+00:00')).replace(tzinfo=None)
                else:
                    target_dt = datetime.fromtimestamp(float(call_datetime))
                time_window = timedelta(minutes=3)
                matched_call_log = db.query(StaffCallLog).filter(
                    StaffCallLog.staff_id == staff_id,
                    StaffCallLog.phone_number.like(f'%{norm_phone}%'),
                    StaffCallLog.call_datetime >= target_dt - time_window,
                    StaffCallLog.call_datetime <= target_dt + time_window
                ).order_by(func.abs(func.extract('epoch', StaffCallLog.call_datetime) - func.extract('epoch', text(f"'{target_dt.isoformat()}'::timestamp")))).first()
            except (ValueError, TypeError):
                pass

    if matched_call_log:
        recording.call_log_id = matched_call_log.id
        matched_call_log.has_recording = True
        matched_call_log.recording_id = recording.id

    db.commit()

    return {
        "success": True,
        "recording_id": recording.id,
        "call_log_id": matched_call_log.id if matched_call_log else None,
        "file_size": file_size,
        "matched": matched_call_log is not None,
        "duplicate": False
    }


@router.get("/recordings/{recording_id}/stream")
async def stream_call_recording(
    recording_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_hybrid)
):
    if not hasattr(current_user, 'emp_code'):
        raise HTTPException(status_code=403, detail="Staff access required")

    staff = db.query(StaffEmployee).filter(StaffEmployee.id == current_user.id).first()
    if not staff:
        raise HTTPException(status_code=404, detail="Staff not found")

    recording = db.query(StaffCallRecording).filter(StaffCallRecording.id == recording_id).first()
    if not recording:
        raise HTTPException(status_code=404, detail="Recording not found")

    is_saas, saas_staff_ids, saas_company_ids = resolve_call_tracking_scope(db, staff)
    if is_saas:
        recording_in_tenant = (
            (recording.staff_id and recording.staff_id in set(saas_staff_ids)) or
            (recording.company_id and recording.company_id in set(saas_company_ids))
        )
        if not recording_in_tenant:
            raise HTTPException(status_code=403, detail="Not authorized to access this recording")
    else:
        is_admin = False
        try:
            from app.core.security import HybridUserContext
            is_admin = HybridUserContext(current_user).has_admin_access()
        except Exception:
            pass

        allowed = (
            is_admin
            or recording.company_id is None
            or staff.base_company_id is None
            or recording.company_id == staff.base_company_id
            or recording.staff_id == staff.id
        )
        if not allowed:
            has_log = db.query(StaffCallLog.id).filter(StaffCallLog.recording_id == recording_id).first()
            if not has_log:
                raise HTTPException(status_code=403, detail="Not authorized to access this recording")

    s3_key = (recording.storage_path or "").replace('\\', '/')
    if s3_key.startswith("http://") or s3_key.startswith("https://"):
        if "plivo.com" in s3_key:
            import requests as _requests
            from app.core.config import settings
            from app.api.v1.endpoints.call_flow_api import _serve_audio_bytes
            plivo_auth_id = getattr(settings, 'PLIVO_AUTH_ID', None)
            plivo_auth_token = getattr(settings, 'PLIVO_AUTH_TOKEN', None)
            auth = (plivo_auth_id, plivo_auth_token) if plivo_auth_id and plivo_auth_token else None
            try:
                p_resp = _requests.get(s3_key, auth=auth, timeout=15)
                if p_resp.status_code == 200 and len(p_resp.content) > 50:
                    media_type = "audio/mpeg" if ".mp3" in s3_key.lower() else "audio/wav"
                    return _serve_audio_bytes(request, p_resp.content, media_type=media_type)
            except Exception as pe:
                import logging
                logging.getLogger("dc.call_tracking").warning(f"[RECORDING-STREAM] Proxying Plivo recording {s3_key} failed: {pe}")
        return RedirectResponse(url=s3_key)

    if "uploads/" in s3_key:
        s3_key = s3_key.split("uploads/")[-1].lstrip("/")
    elif "call_recordings/" in s3_key:
        s3_key = s3_key[s3_key.find("call_recordings/"):]
        
    from app.services.object_storage import storage_service
    file_url = storage_service.get_file_url(s3_key)
    return RedirectResponse(url=file_url)


@router.get("/recordings/{recording_id}/metadata")
async def get_recording_metadata(
    recording_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_hybrid)
):
    if not hasattr(current_user, 'emp_code'):
        raise HTTPException(status_code=403, detail="Staff access required")

    staff = db.query(StaffEmployee).filter(StaffEmployee.id == current_user.id).first()
    if not staff:
        raise HTTPException(status_code=404, detail="Staff not found")

    recording = db.query(StaffCallRecording).filter(StaffCallRecording.id == recording_id).first()
    if not recording:
        raise HTTPException(status_code=404, detail="Recording not found")

    is_saas, saas_staff_ids, saas_company_ids = resolve_call_tracking_scope(db, staff)
    if is_saas:
        recording_in_tenant = (
            (recording.staff_id and recording.staff_id in set(saas_staff_ids)) or
            (recording.company_id and recording.company_id in set(saas_company_ids))
        )
        if not recording_in_tenant:
            raise HTTPException(status_code=403, detail="Not authorized to access this recording")
    else:
        is_admin = False
        try:
            from app.core.security import HybridUserContext
            is_admin = HybridUserContext(current_user).has_admin_access()
        except Exception:
            pass

        allowed = (
            is_admin
            or recording.company_id is None
            or staff.base_company_id is None
            or recording.company_id == staff.base_company_id
            or recording.staff_id == staff.id
        )
        if not allowed:
            has_log = db.query(StaffCallLog.id).filter(StaffCallLog.recording_id == recording_id).first()
            if not has_log:
                raise HTTPException(status_code=403, detail="Not authorized to access this recording")

    staff_info = db.query(StaffEmployee.full_name, StaffEmployee.emp_code).filter(
        StaffEmployee.id == recording.staff_id
    ).first()

    return {
        "success": True,
        "recording": {
            **recording.to_dict(),
            'staff_name': staff_info.full_name if staff_info else 'Unknown',
            'emp_code': staff_info.emp_code if staff_info else '',
            'file_exists': os.path.exists(recording.storage_path)
        }
    }


@router.post("/recordings/bulk-upload")
async def bulk_upload_recordings(
    recordings: list = Body(..., description="List of recording metadata to match with call logs"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_hybrid)
):
    if not hasattr(current_user, 'emp_code'):
        raise HTTPException(status_code=403, detail="Staff access required")

    staff = db.query(StaffEmployee).filter(StaffEmployee.id == current_user.id).first()
    if not staff:
        raise HTTPException(status_code=404, detail="Staff not found")

    pending = []
    skipped = 0
    for rec in recordings:
        device_id = rec.get('device_recording_id')
        if device_id:
            existing = db.query(StaffCallRecording.id).filter(
                StaffCallRecording.staff_id == staff.id,
                StaffCallRecording.device_recording_id == device_id
            ).first()
            if existing:
                skipped += 1
                continue

        pending.append({
            'filename': rec.get('filename', ''),
            'phone_number': rec.get('phone_number', ''),
            'call_datetime': rec.get('call_datetime', ''),
            'device_recording_id': device_id,
            'file_size': rec.get('file_size', 0),
            'duration_seconds': rec.get('duration_seconds'),
        })

    return {
        "success": True,
        "pending_uploads": pending,
        "already_uploaded": skipped,
        "total_checked": len(recordings)
    }
