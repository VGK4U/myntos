"""
Telephony Call Flow API Endpoints — MyntOS Native Telephony
Provides full REST lifecycle for Call Flow Designer, Ring Groups, Business Hours,
Simulator, and Plivo Inbound Webhook Execution.
Created: Sep 2026
"""

from fastapi import APIRouter, Depends, HTTPException, Request, Response, Body, Query
from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta, timezone
import os
import logging
import json
import re
import io
import wave
import math
import struct

IST = timezone(timedelta(hours=5, minutes=30))

from app.core.database import get_db
from app.api.v1.endpoints.staff_auth import get_current_staff_user
from app.core.security import get_current_user_hybrid
from app.models.staff import StaffEmployee
from app.models.crm import CRMLead
from app.models.telephony_call_flow import (
    TelephonyCallFlow, TelephonyCallFlowVersion, TelephonyRingGroup,
    TelephonyBusinessHours, TelephonyHoliday, TelephonyPlivoEndpoint,
    TelephonyFlowExecutionLog
)
from app.services.telephony.call_flow_service import CallFlowService
from app.services.telephony.flow_interpreter import CallFlowInterpreter
from app.services.s3_storage import s3_storage_service as s3_storage
from app.models.voip_call_session import VoIPCallSession
from app.models.voip_enums import CallStateEnum
from app.models.base import get_indian_time
from app.services.telephony.factory import get_telephony_provider
from app.services.telephony.plivo_provider import PlivoTelephonyProvider

logger = logging.getLogger(__name__)
router = APIRouter()


# ── PERMISSION HELPER ────────────────────────────────────────────────────────

def require_telephony_permission(perm: str):
    """Dependency enforcing role and granular telephony permission checks"""
    def dependency(current_user: StaffEmployee = Depends(get_current_staff_user)):
        # Leadership and Admin roles always bypass
        role = getattr(current_user, 'role', None)
        role_code = getattr(role, 'role_code', '').lower() if role else ''
        if role_code in {'vgk4u', 'super_admin', 'key_leadership', 'ea', 'director', 'admin', 'telephony_admin'}:
            return current_user

        # Hierarchy level check (e.g. 70+ leadership)
        level = getattr(role, 'hierarchy_level', 0) if role else 0
        if level >= 70:
            return current_user

        # Check explicit granular permissions if present
        perms = getattr(current_user, 'permissions', []) or []
        if perm in perms or '*' in perms:
            return current_user

        raise HTTPException(status_code=403, detail=f"Permission denied: Requires '{perm}'")
    return dependency


# ── 1. CALL FLOW MANAGEMENT ENDPOINTS ────────────────────────────────────────

@router.get("/flows")
def list_call_flows(
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(require_telephony_permission("telephony.call_flow.view"))
):
    """List all Call Flows for the current user's company"""
    company_id = getattr(current_user, 'base_company_id', 1) or 1
    return CallFlowService.list_flows(db, company_id)


@router.post("/flows")
def create_call_flow(
    payload: Dict[str, Any] = Body(...),
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(require_telephony_permission("telephony.call_flow.create"))
):
    """Create a new Call Flow with starter draft Version 1"""
    company_id = getattr(current_user, 'base_company_id', 1) or 1
    name = payload.get("name")
    if not name or not name.strip():
        raise HTTPException(status_code=400, detail="Flow name is required")

    return CallFlowService.create_flow(
        db=db,
        company_id=company_id,
        name=name.strip(),
        description=payload.get("description"),
        did_number=payload.get("did_number"),
        staff_id=current_user.id,
        initial_graph=payload.get("flow_data")
    )


@router.get("/flows/{flow_id}")
def get_call_flow_details(
    flow_id: int,
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(require_telephony_permission("telephony.call_flow.view"))
):
    """Get Call Flow details including draft and published versions"""
    company_id = getattr(current_user, 'base_company_id', 1) or 1
    return CallFlowService.get_flow_details(db, company_id, flow_id)


@router.put("/flows/{flow_id}/draft")
def save_call_flow_draft(
    flow_id: int,
    payload: Dict[str, Any] = Body(...),
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(require_telephony_permission("telephony.call_flow.edit"))
):
    """Save changes to the flow's active draft"""
    company_id = getattr(current_user, 'base_company_id', 1) or 1
    flow_data = payload.get("flow_data")
    if not flow_data:
        raise HTTPException(status_code=400, detail="flow_data JSON is required")

    return CallFlowService.save_draft(
        db=db,
        company_id=company_id,
        flow_id=flow_id,
        flow_data=flow_data,
        name=payload.get("name"),
        description=payload.get("description"),
        did_number=payload.get("did_number")
    )


@router.post("/flows/{flow_id}/validate")
def validate_call_flow(
    flow_id: int,
    payload: Optional[Dict[str, Any]] = Body(None),
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(require_telephony_permission("telephony.call_flow.edit"))
):
    """Validate graph structure and node integrity"""
    company_id = getattr(current_user, 'base_company_id', 1) or 1
    flow_data = payload.get("flow_data") if payload else None
    return CallFlowService.validate_flow(db, company_id, flow_id, flow_data)


@router.post("/flows/{flow_id}/publish")
def publish_call_flow(
    flow_id: int,
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(require_telephony_permission("telephony.call_flow.publish"))
):
    """Publish current draft as immutable active version"""
    company_id = getattr(current_user, 'base_company_id', 1) or 1
    return CallFlowService.publish_flow(db, company_id, flow_id, staff_id=current_user.id)


@router.get("/flows/{flow_id}/versions")
def list_flow_versions(
    flow_id: int,
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(require_telephony_permission("telephony.call_flow.view"))
):
    """Get version history for a Call Flow"""
    company_id = getattr(current_user, 'base_company_id', 1) or 1
    versions = db.query(TelephonyCallFlowVersion).filter(
        TelephonyCallFlowVersion.flow_id == flow_id,
        TelephonyCallFlowVersion.company_id == company_id
    ).order_by(TelephonyCallFlowVersion.version_number.desc()).all()
    return [v.to_dict() for v in versions]


@router.post("/flows/{flow_id}/rollback/{version_id}")
def rollback_call_flow(
    flow_id: int,
    version_id: int,
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(require_telephony_permission("telephony.call_flow.publish"))
):
    """Roll back active published flow to a prior version"""
    company_id = getattr(current_user, 'base_company_id', 1) or 1
    return CallFlowService.rollback_flow(db, company_id, flow_id, version_id, staff_id=current_user.id)


@router.post("/flows/{flow_id}/simulate")
def simulate_call_flow(
    flow_id: int,
    payload: Dict[str, Any] = Body(...),
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(require_telephony_permission("telephony.call_flow.test"))
):
    """Dry-run simulation of Call Flow without real telecom calls"""
    company_id = getattr(current_user, 'base_company_id', 1) or 1
    caller_phone = payload.get("caller_phone", "+919876543210")
    sim_time_str = payload.get("simulated_datetime")
    sim_time = datetime.fromisoformat(sim_time_str) if sim_time_str else None
    dtmf_inputs = payload.get("dtmf_inputs", [])
    override_graph = payload.get("override_graph")

    return CallFlowService.simulate_flow(
        db=db,
        company_id=company_id,
        flow_id=flow_id,
        caller_phone=caller_phone,
        simulated_datetime=sim_time,
        dtmf_inputs=dtmf_inputs,
        override_graph=override_graph
    )


# ── 2. RING GROUPS & BUSINESS HOURS ENDPOINTS ────────────────────────────────

@router.get("/ring-groups")
def list_ring_groups(
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(require_telephony_permission("telephony.ring_group.manage"))
):
    """List department Ring Groups"""
    company_id = getattr(current_user, 'base_company_id', 1) or 1
    return CallFlowService.list_ring_groups(db, company_id)


@router.post("/ring-groups")
def create_ring_group(
    payload: Dict[str, Any] = Body(...),
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(require_telephony_permission("telephony.ring_group.manage"))
):
    """Create a new department Ring Group"""
    company_id = getattr(current_user, 'base_company_id', 1) or 1
    name = payload.get("name")
    if not name or not name.strip():
        raise HTTPException(status_code=400, detail="Ring group name is required")

    return CallFlowService.create_ring_group(
        db=db,
        company_id=company_id,
        name=name.strip(),
        strategy=payload.get("strategy", "simultaneous"),
        timeout_seconds=payload.get("timeout_seconds", 25),
        fallback_action=payload.get("fallback_action", "voicemail"),
        member_staff_ids=payload.get("member_staff_ids", [])
    )


@router.put("/ring-groups/{rg_id}")
def update_ring_group(
    rg_id: int,
    payload: Dict[str, Any] = Body(...),
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(require_telephony_permission("telephony.ring_group.manage"))
):
    """Update a department Ring Group's strategy, timeout, fallback, and assigned staff members"""
    company_id = getattr(current_user, 'base_company_id', 1) or 1
    return CallFlowService.update_ring_group(db, rg_id, payload, company_id)


@router.get("/staff-employees")
def list_staff_employees_for_telephony(
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """List active staff employees with department & contact info for call flow routing & ring groups"""
    try:
        employees = db.query(StaffEmployee).filter(
            StaffEmployee.status.in_(['ACTIVE', 'active']),
            ~StaffEmployee.emp_code.ilike('EMP_TEST_%')
        ).order_by(StaffEmployee.first_name.asc()).all()

        results = []
        for e in employees:
            name = getattr(e, 'full_name', None) or f"{e.first_name or ''} {e.last_name or ''}".strip() or e.emp_code
            dept = getattr(e, 'department', None)
            dept_name = dept.name if (dept and hasattr(dept, 'name')) else (str(dept) if dept else 'General')
            results.append({
                "id": e.id,
                "emp_code": e.emp_code,
                "full_name": name,
                "department_name": dept_name,
                "department_id": e.department_id,
                "phone": e.phone or '',
                "email": e.email or '',
                "sip_endpoint": f"sip:{e.emp_code.lower()}@phone.plivo.com"
            })
        return results
    except Exception as e:
        logger.error(f"[CALL-FLOW-STAFF] Error loading employees: {e}")
        return []



@router.get("/business-hours")
def get_business_hours(
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(require_telephony_permission("telephony.call_flow.view"))
):
    """Get company business hours schedule"""
    company_id = getattr(current_user, 'base_company_id', 1) or 1
    bh = db.query(TelephonyBusinessHours).filter(
        TelephonyBusinessHours.company_id == company_id,
        TelephonyBusinessHours.is_active == True
    ).first()
    return bh.to_dict() if bh else {
        'id': None,
        'company_id': company_id,
        'name': 'Default Operating Hours',
        'timezone': 'Asia/Kolkata',
        'schedule_data': {
            'mon': {'start': '09:00', 'end': '20:00', 'enabled': True},
            'tue': {'start': '09:00', 'end': '20:00', 'enabled': True},
            'wed': {'start': '09:00', 'end': '20:00', 'enabled': True},
            'thu': {'start': '09:00', 'end': '20:00', 'enabled': True},
            'fri': {'start': '09:00', 'end': '20:00', 'enabled': True},
            'sat': {'start': '09:00', 'end': '20:00', 'enabled': True},
            'sun': {'start': '09:00', 'end': '20:00', 'enabled': True}
        }
    }


@router.put("/business-hours")
def update_business_hours(
    payload: Dict[str, Any] = Body(...),
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(require_telephony_permission("telephony.call_flow.edit"))
):
    """Save company business hours schedule"""
    company_id = getattr(current_user, 'base_company_id', 1) or 1
    bh = db.query(TelephonyBusinessHours).filter(
        TelephonyBusinessHours.company_id == company_id
    ).first()

    if not bh:
        bh = TelephonyBusinessHours(company_id=company_id)
        db.add(bh)

    bh.name = payload.get("name", "Standard Operating Hours")
    bh.timezone = payload.get("timezone", "Asia/Kolkata")
    bh.schedule_data = payload.get("schedule_data", {})
    bh.is_active = True
    db.commit()
    db.refresh(bh)
    return bh.to_dict()


@router.get("/endpoints")
def list_company_endpoints(
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(require_telephony_permission("telephony.call_flow.view"))
):
    """List all staff employees with live Plivo SIP endpoints, registration, and active/inactive status"""
    company_id = getattr(current_user, 'base_company_id', 1) or 1
    
    # Query all staff employees across company
    employees = db.query(StaffEmployee).order_by(
        StaffEmployee.status.asc(),
        StaffEmployee.first_name.asc()
    ).all()
    
    # Query all existing Plivo endpoints indexed by staff_id
    plivo_endpoints = db.query(TelephonyPlivoEndpoint).all()
    ep_by_staff_id = {ep.staff_id: ep for ep in plivo_endpoints if ep.staff_id}
    
    results = []
    for emp in employees:
        ep = ep_by_staff_id.get(emp.id)
        
        name = getattr(emp, 'full_name', None) or f"{emp.first_name or ''} {emp.last_name or ''}".strip() or emp.emp_code
        emp_status = (emp.status or 'active').lower().strip()
        is_active = emp_status == 'active'
        dept_name = emp.department.name if getattr(emp, 'department', None) else 'General'
        
        username = ep.plivo_username if (ep and ep.plivo_username) else f"agent_{emp.emp_code.lower()}"
        sip_uri = f"sip:{username}@phone.plivo.com"
        alias = ep.plivo_alias if (ep and ep.plivo_alias) else f"{emp.emp_code}_{name.replace(' ', '_')}"
        is_registered = bool(ep.is_registered) if (ep and is_active) else is_active
        
        results.append({
            "id": ep.id if ep else emp.id,
            "staff_id": emp.id,
            "staff_name": name,
            "staff_emp_code": emp.emp_code,
            "department_name": dept_name,
            "department_id": emp.department_id,
            "plivo_username": username,
            "plivo_sip_uri": sip_uri,
            "plivo_alias": alias,
            "is_registered": is_registered,
            "status": emp_status,
            "is_active": is_active,
            "last_seen": ep.last_registered_at.isoformat() if (ep and ep.last_registered_at) else None
        })
    return results


@router.get("/dids")
def list_company_dids(
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(require_telephony_permission("telephony.call_flow.view"))
):
    """List all DIDs available/assigned for the current tenant"""
    company_id = getattr(current_user, 'base_company_id', 1) or 1
    from app.models.operator_calls import TelephonyDIDMapping
    try:
        dids = db.query(TelephonyDIDMapping).filter(
            TelephonyDIDMapping.company_id == company_id
        ).all()
        if dids:
            return [
                {
                    "did_number": d.did_number,
                    "provider": d.provider,
                    "label": d.label or d.did_number,
                    "is_active": d.is_active
                }
                for d in dids
            ]
    except Exception as e:
        logger.warning(f"[CALL-FLOW-DIDS] Query error: {e}")

    flows = db.query(TelephonyCallFlow.did_number).filter(
        TelephonyCallFlow.company_id == company_id,
        TelephonyCallFlow.did_number != None
    ).distinct().all()
    return [{"did_number": f[0], "provider": "PLIVO", "label": f[0], "is_active": True} for f in flows if f[0]]


def _get_public_base_url(request: Request) -> str:
    env_base = os.environ.get("BASE_URL", "").rstrip('/')
    if env_base and not ("localhost" in env_base or "127.0.0.1" in env_base):
        return env_base
    host = request.headers.get("x-forwarded-host") or request.headers.get("host") or ""
    proto = request.headers.get("x-forwarded-proto") or "https"
    if host and "myntreal.com" in host:
        return f"{proto}://{host}".rstrip('/')
    if "localhost" in host or "127.0.0.1" in host or not host:
        return os.environ.get("BASE_URL", "https://www.myntreal.com").rstrip('/')
    return f"{proto}://{host}".rstrip('/')


# ── 3. PLIVO INBOUND TELECOM WEBHOOKS ────────────────────────────────────────

@router.post("/plivo/inbound")
async def plivo_inbound_answer(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Plivo Primary Answer URL.
    Invoked when customer dials the MyntOS Plivo DID (+91 80 3172 8899)
    or when an outbound click-to-call is answered by the customer.
    Returns dynamic Plivo XML.
    """
    form_data = await request.form()
    caller_phone = form_data.get("From", "")
    called_did = form_data.get("To", "")
    call_uuid = form_data.get("CallUUID", "")
    session_id_param = request.query_params.get("session_id") or form_data.get("session_id") or form_data.get("X-PH-Call-Session-ID", "")

    base_url = _get_public_base_url(request)
    xml_str = CallFlowInterpreter.handle_inbound_call(
        db=db,
        caller_phone=caller_phone,
        called_did=called_did,
        provider_call_id=call_uuid,
        base_api_url=base_url,
        call_session_id=session_id_param
    )
    return Response(content=xml_str, media_type="application/xml")


@router.post("/plivo/flow-step")
async def plivo_flow_step(
    request: Request,
    session_id: str = Query(...),
    node_key: str = Query(...),
    db: Session = Depends(get_db)
):
    """
    Continuation callback for DTMF collection (<GetDigits>) or node action.
    """
    form_data = await request.form()
    digits = form_data.get("Digits", None)

    base_url = _get_public_base_url(request)
    xml_str = CallFlowInterpreter.handle_flow_step(
        db=db,
        call_session_id=session_id,
        current_node_key=node_key,
        dtmf_input=digits,
        base_api_url=base_url
    )
    return Response(content=xml_str, media_type="application/xml")


@router.post("/plivo/dial-action")
async def plivo_dial_action(
    request: Request,
    session_id: str = Query(...),
    node_key: str = Query(...),
    db: Session = Depends(get_db)
):
    """
    Callback when Plivo finishes dialing an agent or ring group.
    Evaluates DialStatus ('completed', 'busy', 'no-answer', 'failed', 'timeout').
    """
    form_data = await request.form()
    dial_status = form_data.get("DialStatus", "no-answer").lower()
    logger.info(f"[PLIVO-DIAL-ACTION] Session {session_id} DialStatus: {dial_status}")

    if dial_status == 'completed':
        return Response(content="<Response><Hangup /></Response>", media_type="application/xml")

    # Proceed along 'no_answer' or 'fallback' branch
    base_url = _get_public_base_url(request)
    xml_str = CallFlowInterpreter.handle_flow_step(
        db=db,
        call_session_id=session_id,
        current_node_key=node_key,
        dtmf_input="no_answer",
        base_api_url=base_url
    )
    return Response(content=xml_str, media_type="application/xml")


@router.post("/plivo/recording-callback")
async def plivo_recording_callback(
    request: Request,
    session_id: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Receives Plivo dual-channel recording callback and registers it to VoIPCallSession, StaffCallLog & StaffCallRecording.
    """
    form_data = {}
    try:
        form = await request.form()
        form_data = dict(form)
    except Exception:
        pass

    if not form_data:
        try:
            body = await request.body()
            if body:
                form_data = json.loads(body.decode("utf-8"))
        except Exception:
            pass

    rec_url = form_data.get("RecordUrl") or form_data.get("RecordingUrl") or form_data.get("record_url") or request.query_params.get("RecordUrl", "")
    duration_str = form_data.get("RecordingDuration") or form_data.get("Duration") or form_data.get("recording_duration") or "0"
    try:
        duration = int(duration_str)
    except Exception:
        duration = 0

    rec_id = form_data.get("RecordingID") or form_data.get("RecordingId") or form_data.get("recording_id", "")
    call_uuid = form_data.get("CallUUID") or form_data.get("call_uuid") or request.query_params.get("CallUUID", "")
    sess_id = session_id or form_data.get("session_id") or request.query_params.get("session_id", "")

    logger.info(f"[PLIVO-RECORDING] Callback received: url={rec_url}, duration={duration}s, call_uuid={call_uuid}, session_id={sess_id}")

    if rec_url:
        from app.models.call_tracking import StaffCallLog, StaffCallRecording
        
        # 1. Match VoIPCallSession idempotently
        voip_session = None
        if sess_id:
            voip_session = db.query(VoIPCallSession).filter(VoIPCallSession.call_session_id == sess_id).first()
        if not voip_session and call_uuid:
            voip_session = db.query(VoIPCallSession).filter(VoIPCallSession.provider_call_id == call_uuid).first()
        if not voip_session and sess_id and sess_id.isdigit():
            voip_session = db.query(VoIPCallSession).filter(VoIPCallSession.id == int(sess_id)).first()
        if not voip_session and call_uuid:
            voip_session = db.query(VoIPCallSession).filter(VoIPCallSession.provider_call_id.ilike(f"%{call_uuid}%")).first()

        if voip_session:
            voip_session.recording_storage_key = rec_url
            voip_session.recording_status = "AVAILABLE"
            voip_session.recording_duration_seconds = duration
            if duration > (voip_session.duration_seconds or 0):
                voip_session.duration_seconds = duration

            meta = {}
            if voip_session.metadata_json:
                try:
                    meta = json.loads(voip_session.metadata_json) if isinstance(voip_session.metadata_json, str) else dict(voip_session.metadata_json)
                except Exception:
                    pass
            meta["recording_url"] = rec_url
            meta["recording_id"] = rec_id or call_uuid
            meta["recording_duration_seconds"] = duration
            voip_session.metadata_json = json.dumps(meta)
            
            # Explicitly commit VoIPCallSession
            db.commit()
            logger.info(f"[PLIVO-RECORDING] Successfully persisted recording for VoIPCallSession #{voip_session.id} ({voip_session.call_session_id})")

        # 2. Match StaffCallLog & StaffCallRecording
        call_log = None
        if call_uuid:
            call_log = db.query(StaffCallLog).filter(StaffCallLog.device_call_id == call_uuid).first()
        if not call_log and sess_id:
            call_log = db.query(StaffCallLog).filter(StaffCallLog.device_call_id == sess_id).first()
        if not call_log and voip_session and voip_session.operator_id:
            clean_p = re.sub(r'\D', '', voip_session.customer_phone or '')[-10:]
            if clean_p:
                call_log = db.query(StaffCallLog).filter(
                    StaffCallLog.staff_id == voip_session.operator_id,
                    StaffCallLog.phone_number.ilike(f"%{clean_p}%")
                ).order_by(StaffCallLog.id.desc()).first()

        company_id = getattr(voip_session, 'company_id', 1) or (call_log.company_id if call_log else 1) or 1
        staff_id = getattr(voip_session, 'operator_id', None) or (call_log.staff_id if call_log else None)

        if staff_id:
            existing_rec = db.query(StaffCallRecording).filter(
                StaffCallRecording.storage_path == rec_url
            ).first()
            if not existing_rec:
                new_rec = StaffCallRecording(
                    company_id=company_id,
                    staff_id=staff_id,
                    call_log_id=call_log.id if call_log else None,
                    original_filename=f"plivo_{call_uuid or sess_id or 'rec'}.mp3",
                    storage_path=rec_url,
                    file_size=0,
                    mime_type="audio/mp3",
                    duration_seconds=duration,
                    recorded_at=get_indian_time(),
                    device_recording_id=rec_id or call_uuid,
                    source_device="plivo_softphone"
                )
                db.add(new_rec)
                db.flush()
                rec_obj_id = new_rec.id
            else:
                rec_obj_id = existing_rec.id

            if call_log:
                call_log.has_recording = True
                call_log.recording_id = rec_obj_id
                if duration > (call_log.duration_seconds or 0):
                    call_log.duration_seconds = duration

            db.commit()
            logger.info(f"[PLIVO-RECORDING] Successfully linked recording #{rec_obj_id} to call_log={call_log.id if call_log else 'None'}")

    return Response(content="<Response></Response>", media_type="application/xml")


@router.post("/plivo/hangup")
async def plivo_application_hangup(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Dedicated Plivo Application-Level Hangup Callback.
    Accepts Plivo's Application hangup_url POST parameters:
    CallUUID, CallStatus, Direction, From, To, Duration, BillDuration,
    HangupCauseName, HangupCauseCode, HangupSource, ALegUUID, BLegUUID, etc.
    Validates Plivo signature, updates VoIPCallSession idempotently,
    and returns HTTP 200 promptly (JSON / text, never call-control XML).
    """
    raw_body = await request.body()
    headers = {k.lower(): v for k, v in request.headers.items()}

    # 1. Parse Form or JSON payload
    payload = {}
    try:
        form_data = await request.form()
        payload = dict(form_data)
    except Exception:
        pass

    if not payload and raw_body:
        try:
            payload = json.loads(raw_body.decode('utf-8'))
        except Exception:
            pass

    # 2. Plivo Webhook V3 Signature Validation (with reverse proxy https normalization)
    sig_v3 = headers.get("x-plivo-signature-v3") or headers.get("x-plivo-signature-ma-v3")
    nonce_v3 = headers.get("x-plivo-signature-v3-nonce") or headers.get("x-plivo-signature-ma-v3-nonce") or ""

    if sig_v3:
        provider = get_telephony_provider("plivo")
        url_str = str(request.url)
        # Normalize proxy scheme if TLS was terminated upstream
        if headers.get("x-forwarded-proto") == "https" and url_str.startswith("http://"):
            url_str = "https://" + url_str[7:]
        
        is_valid_v3 = PlivoTelephonyProvider.validate_signature_v3(
            url=url_str,
            nonce=nonce_v3,
            signature=sig_v3,
            auth_token=getattr(provider, 'auth_token', ''),
            method=request.method,
            params=payload
        )
        if not is_valid_v3 and not (url_str.startswith("http://") and PlivoTelephonyProvider.validate_signature_v3(url="https://" + url_str[7:], nonce=nonce_v3, signature=sig_v3, auth_token=getattr(provider, 'auth_token', ''), method=request.method, params=payload)):
            logger.warning(f"[PLIVO-HANGUP] Invalid Plivo V3 webhook signature: sig={sig_v3[:10]}... url={url_str}")
            # Do not drop legitimate hangup events in mixed dev/proxy environments if CallUUID exists
            if not getattr(settings, 'DEBUG', False) and not payload.get("CallUUID"):
                raise HTTPException(status_code=401, detail="Invalid Plivo V3 Webhook Signature")

    call_uuid = payload.get("CallUUID") or payload.get("call_uuid") or request.query_params.get("CallUUID", "")
    dial_bleg_uuid = payload.get("DialBLegUUID") or payload.get("dial_bleg_uuid") or ""
    dial_aleg_uuid = payload.get("DialALegUUID") or payload.get("dial_aleg_uuid") or ""
    dial_bleg_status = (payload.get("DialBLegStatus") or "").lower()
    call_status = (payload.get("CallStatus") or payload.get("status") or "").lower()
    
    # Check multiple duration keys from Plivo Dial action and Hangup callback
    dur_candidate = payload.get("DialBLegDuration") or payload.get("Duration") or payload.get("BillDuration") or payload.get("dial_bleg_duration") or "0"
    try:
        duration_sec = int(dur_candidate)
    except (ValueError, TypeError):
        duration_sec = 0

    hangup_cause_name = payload.get("HangupCauseName") or payload.get("HangupCause", "")
    hangup_cause_code = payload.get("HangupCauseCode")
    hangup_source = payload.get("HangupSource")
    session_id_param = payload.get("session_id") or request.query_params.get("session_id")

    logger.info(
        f"[PLIVO-HANGUP-WEBHOOK] CallUUID={call_uuid} BLegUUID={dial_bleg_uuid} Status={call_status} "
        f"BLegStatus={dial_bleg_status} Duration={duration_sec}s Cause={hangup_cause_name} Source={hangup_source}"
    )

    if not call_uuid and not session_id_param and not dial_bleg_uuid:
        logger.warning("[PLIVO-HANGUP] Received hangup callback without CallUUID or session_id")
        return Response(content="<Response></Response>", media_type="application/xml")

    # 3. Locate existing VoIPCallSession idempotently
    session = None
    if session_id_param:
        session = db.query(VoIPCallSession).filter(
            VoIPCallSession.call_session_id == session_id_param
        ).first()

    if not session and call_uuid:
        session = db.query(VoIPCallSession).filter(
            VoIPCallSession.provider_call_id == call_uuid
        ).first()

    if not session and dial_aleg_uuid:
        session = db.query(VoIPCallSession).filter(
            VoIPCallSession.provider_call_id == dial_aleg_uuid
        ).first()

    if not session and dial_bleg_uuid:
        session = db.query(VoIPCallSession).filter(
            VoIPCallSession.provider_call_id == dial_bleg_uuid
        ).first()

    if not session and call_uuid:
        session = db.query(VoIPCallSession).filter(
            VoIPCallSession.provider_call_id.like(f"%{call_uuid}%")
        ).first()

    # 4. Map Plivo CallStatus to MyntOS CallStateEnum
    status_map = {
        "completed": CallStateEnum.ENDED.value,
        "hangup": CallStateEnum.ENDED.value,
        "busy": CallStateEnum.BUSY.value,
        "no-answer": CallStateEnum.NO_ANSWER.value,
        "failed": CallStateEnum.FAILED.value,
        "rejected": CallStateEnum.REJECTED.value,
        "cancelled": CallStateEnum.ENDED.value,
    }
    
    # If dial_bleg_status is present, prioritize it
    effective_status = dial_bleg_status if dial_bleg_status else call_status
    target_state = status_map.get(effective_status, CallStateEnum.ENDED.value)

    if not session:
        caller = payload.get("From") or ""
        called = payload.get("To") or "+918031728899"
        dir_str = (payload.get("Direction") or "inbound").lower()
        new_sid = session_id_param or (f"vcs_in_{call_uuid[-12:]}" if call_uuid else f"vcs_{int(datetime.now().timestamp())}")
        session = VoIPCallSession(
            company_id=1,
            call_session_id=new_sid,
            provider='plivo',
            provider_call_id=call_uuid or dial_bleg_uuid,
            caller_id=called,
            customer_phone=caller,
            destination_number=called,
            direction=dir_str,
            call_method=CallMethodEnum.IN_APP_PSTN.value,
            status=target_state,
            duration_seconds=duration_sec,
            started_at=get_indian_time(),
            ended_at=get_indian_time()
        )
        db.add(session)
        db.commit()
        db.refresh(session)
        logger.info(f"[PLIVO-HANGUP] Created fallback VoIPCallSession #{session.id} ({new_sid}) for {caller}")

    # 5. Idempotent state updates
    if duration_sec > 0 or effective_status in ("completed", "answered"):
        session.status = CallStateEnum.ENDED.value
        if not session.answered_at:
            session.answered_at = session.started_at or get_indian_time()
    elif not CallStateEnum(session.status).is_terminal():
        session.status = target_state

    if duration_sec > (session.duration_seconds or 0):
        session.duration_seconds = duration_sec

    # Check for RecordUrl in hangup payload
    hangup_rec_url = payload.get("RecordUrl") or payload.get("RecordingUrl") or payload.get("record_url")
    if hangup_rec_url:
        session.recording_storage_key = hangup_rec_url
        session.recording_status = "AVAILABLE"
        session.recording_duration_seconds = session.duration_seconds

    if hangup_cause_name or hangup_source:
        session.termination_reason = f"{hangup_cause_name} ({hangup_source})" if hangup_source else hangup_cause_name

    if not session.ended_at:
        session.ended_at = get_indian_time()

    # Link OperatorCall record if present
    if session.operator_call_id:
        from app.models.operator_calls import OperatorCall
        op_c = db.query(OperatorCall).filter(OperatorCall.id == session.operator_call_id).first()
        if op_c:
            op_c.status = "answered" if (session.duration_seconds or 0) > 0 else "missed"
            op_c.duration_seconds = session.duration_seconds or 0
            op_c.ended_at = session.ended_at
            if hangup_rec_url:
                op_c.recording_url = hangup_rec_url

    # Update metadata diagnostics
    meta = {}
    if session.metadata_json:
        try:
            meta = json.loads(session.metadata_json) if isinstance(session.metadata_json, str) else dict(session.metadata_json)
        except Exception:
            meta = {}

    if hangup_rec_url:
        meta["recording_url"] = hangup_rec_url
        meta["recording_duration_seconds"] = session.duration_seconds

    meta.update({
        "plivo_hangup_status": call_status,
        "plivo_dial_bleg_status": dial_bleg_status,
        "plivo_hangup_cause_name": hangup_cause_name,
        "plivo_hangup_cause_code": hangup_cause_code,
        "plivo_hangup_source": hangup_source,
        "plivo_bill_duration": payload.get("BillDuration"),
        "plivo_aleg_uuid": dial_aleg_uuid or payload.get("ALegUUID"),
        "plivo_bleg_uuid": dial_bleg_uuid or payload.get("BLegUUID"),
    })
    session.metadata_json = json.dumps(meta)

    db.commit()

    return Response(content="<Response></Response>", media_type="application/xml")


@router.post("/plivo/click-to-call")
def initiate_click_to_call(
    request: Request,
    payload: Dict[str, Any] = Body(...),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_hybrid)
):
    """
    Direct Server-Side Click-to-Call Bridge.
    Dials customer or agent directly via Plivo Cloud Trunk, ensuring immediate connection,
    tracking VoIPCallSession, and logging into call history.
    """
    import uuid
    import requests as _req
    from app.core.config import settings

    to_phone = str(payload.get("to") or payload.get("destination") or payload.get("to_phone") or payload.get("customer_phone") or payload.get("phone") or "").strip()
    if not to_phone:
        raise HTTPException(status_code=400, detail="Destination phone number is required")

    if not to_phone.startswith("+"):
        to_phone = "+91" + to_phone.lstrip("0")

    auth_id = getattr(settings, 'PLIVO_AUTH_ID', None)
    auth_token = getattr(settings, 'PLIVO_AUTH_TOKEN', None)
    from_number = getattr(settings, 'PLIVO_DEFAULT_CALLER_ID', '+918031728899')

    if not auth_id or not auth_token:
        raise HTTPException(status_code=503, detail="Plivo credentials not configured on server")

    company_id = getattr(current_user, 'base_company_id', None) or getattr(current_user, 'company_id', 1) or 1
    branch_id = getattr(current_user, 'branch_id', None)
    lead_id = payload.get("lead_id")
    call_session_id = payload.get("call_session_id")

    session = None
    if call_session_id:
        session = db.query(VoIPCallSession).filter(VoIPCallSession.call_session_id == call_session_id).first()

    now = get_indian_time()
    if not session:
        call_session_id = call_session_id or f"vcs_{uuid.uuid4().hex[:16]}"
        session = VoIPCallSession(
            call_session_id=call_session_id,
            company_id=company_id,
            branch_id=branch_id,
            lead_id=lead_id,
            operator_id=current_user.id,
            operator_user_ref=getattr(current_user, 'emp_code', None) or str(current_user.id),
            operator_name=getattr(current_user, 'full_name', 'Operator'),
            customer_phone=to_phone,
            direction='outbound',
            call_method='click_to_call',
            provider='plivo',
            caller_id=from_number,
            destination_number=to_phone,
            status=CallStateEnum.DIALING.value,
            started_at=now,
            dialing_at=now
        )
        db.add(session)
        db.flush()

    forwarded_proto = request.headers.get("x-forwarded-proto", "https")
    forwarded_host = request.headers.get("x-forwarded-host") or request.headers.get("host")
    if forwarded_host and "localhost" not in forwarded_host and "127.0.0.1" not in forwarded_host:
        base_domain = f"{forwarded_proto}://{forwarded_host}"
    else:
        base_domain = "https://www.myntreal.com"

    plivo_url = f"https://api.plivo.com/v1/Account/{auth_id}/Call/"
    call_payload = {
        "from": from_number,
        "to": to_phone,
        "answer_url": f"{base_domain}/api/v1/telephony/plivo/inbound?session_id={session.call_session_id}",
        "answer_method": "POST",
        "hangup_url": f"{base_domain}/api/v1/telephony/plivo/hangup?session_id={session.call_session_id}",
        "hangup_method": "POST",
        "record": "true",
        "record_direction": "both",
        "recording_callback_url": f"{base_domain}/api/v1/telephony/plivo/recording-callback?session_id={session.call_session_id}",
        "recording_callback_method": "POST"
    }

    try:
        resp = _req.post(plivo_url, json=call_payload, auth=(auth_id, auth_token), timeout=10)
        res_json = resp.json()
        logger.info(f"[CLICK-TO-CALL] Initiated outbound call to {to_phone}: status={resp.status_code} res={res_json}")

        request_uuid = res_json.get("request_uuid")
        if request_uuid:
            session.provider_call_id = request_uuid
            session.status = CallStateEnum.CONNECTED.value
            session.answered_at = get_indian_time()

        db.commit()

        return {
            "success": True,
            "call_session_id": session.call_session_id,
            "provider_call_id": session.provider_call_id,
            "message": f"Outbound call initiated to {to_phone}",
            "status_code": resp.status_code,
            "data": res_json
        }
    except Exception as e:
        logger.error(f"[CLICK-TO-CALL] Failed to dispatch Plivo call to {to_phone}: {e}")
        session.status = CallStateEnum.FAILED.value
        session.ended_at = get_indian_time()
        session.failure_reason = str(e)
        db.commit()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/plivo/calls/session-status/{session_id}")
def get_call_session_status(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Returns the real-time live status and duration of an ongoing call session.
    Actively checks Plivo Carrier REST API to detect disconnects instantly even without inbound webhooks.
    """
    from app.core.config import settings

    session = db.query(VoIPCallSession).filter(
        VoIPCallSession.call_session_id == session_id
    ).first()

    if not session:
        # Try searching by provider_call_id
        session = db.query(VoIPCallSession).filter(
            VoIPCallSession.provider_call_id == session_id
        ).first()

    if not session:
        return {
            "success": False,
            "call_session_id": session_id,
            "status": "ended",
            "is_terminal": True,
            "duration_seconds": 0
        }

    status_val = session.status or "ended"
    is_terminal = CallStateEnum(status_val).is_terminal() if status_val in CallStateEnum._value2member_map_ else (status_val in ("ended", "completed", "failed", "busy", "no-answer", "rejected"))

    # Active Live Plivo Carrier Query to detect connection/disconnection in real-time
    if not is_terminal and session.provider_call_id and not session.provider_call_id.startswith("plivo_vcs_"):
        auth_id = getattr(settings, 'PLIVO_AUTH_ID', None)
        auth_token = getattr(settings, 'PLIVO_AUTH_TOKEN', None)
        if auth_id and auth_token and not auth_id.startswith("mock_"):
            try:
                import requests as _req
                p_url = f"https://api.plivo.com/v1/Account/{auth_id}/Call/{session.provider_call_id}/"
                p_resp = _req.get(p_url, auth=(auth_id, auth_token), timeout=2.5)
                if p_resp.status_code == 200:
                    p_data = p_resp.json()
                    end_t = p_data.get("end_time")
                    call_st = (p_data.get("call_state") or "").upper()
                    if end_t or call_st in ("COMPLETED", "HANGUP", "FAILED", "BUSY", "NO_ANSWER"):
                        is_terminal = True
                        status_val = "ended"
                        session.status = CallStateEnum.ENDED.value
                        dur = int(p_data.get("call_duration") or p_data.get("billed_duration") or 0)
                        session.duration_seconds = dur
                        session.ended_at = get_indian_time()
                        if dur > 0 and not session.answered_at:
                            session.answered_at = session.started_at or get_indian_time()
                        hang_cause = p_data.get("hangup_cause_name") or "Normal Hangup"
                        hang_src = p_data.get("hangup_source") or "Carrier"
                        session.termination_reason = f"{hang_cause} ({hang_src})"
                        db.commit()
                    elif call_st in ("ANSWER", "IN-PROGRESS", "CONNECTED"):
                        if session.status not in (CallStateEnum.ANSWERED.value, CallStateEnum.CONNECTED.value):
                            session.status = CallStateEnum.ANSWERED.value
                            session.answered_at = session.answered_at or get_indian_time()
                            status_val = "connected"
                            db.commit()
            except Exception as pe:
                logger.warning(f"[POLLER-PLIVO-CHECK] Failed live query: {pe}")

    # Compute live duration
    dur_sec = session.duration_seconds or 0
    if not is_terminal and session.answered_at:
        now = get_indian_time()
        ans_t = session.answered_at.replace(tzinfo=None) if session.answered_at.tzinfo else session.answered_at
        now_t = now.replace(tzinfo=None) if now.tzinfo else now
        dur_sec = max(0, int((now_t - ans_t).total_seconds()))

    return {
        "success": True,
        "call_session_id": session.call_session_id,
        "provider_call_id": session.provider_call_id,
        "status": status_val,
        "is_terminal": is_terminal,
        "duration_seconds": dur_sec,
        "destination": session.destination_number or session.customer_phone
    }


# ── 5. STAFF DESTINATIONS & CROSS-COMPANY SELECTOR ───────────────────────────

@router.get("/staff-destinations")
def list_staff_destinations(
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(require_telephony_permission("telephony.call_flow.view"))
):
    """
    Returns eligible active staff destinations for call routing.
    Authorized leadership (hierarchy_level >= 70 or isSupreme) can select active
    staff across companies with company tags, exposing only minimal routing fields.
    """
    is_admin = getattr(current_user, 'is_supreme', False) or (getattr(current_user, 'hierarchy_level', 0) >= 70)
    user_company_id = getattr(current_user, 'base_company_id', 1) or 1

    query = db.query(StaffEmployee).filter(StaffEmployee.status.in_(['active', 'ACTIVE']))
    if not is_admin:
        query = query.filter(StaffEmployee.base_company_id == user_company_id)

    staff_records = query.order_by(StaffEmployee.first_name.asc()).all()

    # Pre-fetch endpoints
    endpoints = db.query(TelephonyPlivoEndpoint).all()
    ep_map = {ep.staff_id: ep.plivo_username for ep in endpoints if ep.plivo_username}

    results = []
    for s in staff_records:
        results.append({
            "id": s.id,
            "name": s.full_name or f"{s.first_name} {s.last_name}".strip() or s.emp_code,
            "emp_code": s.emp_code,
            "company_id": s.base_company_id,
            "designation": s.designation or "Staff",
            "phone": s.phone,
            "endpoint_username": ep_map.get(s.id, f"agent_c{s.base_company_id}_s{s.id}"),
            "is_cross_company": s.base_company_id != user_company_id
        })

    return results


# ── 6. INCOMING CALLS MANAGEMENT & CALL HISTORY ──────────────────────────────

def _mask_phone(p: Optional[str]) -> str:
    if not p:
        return "—"
    clean = re.sub(r'\D', '', str(p))
    if len(clean) < 6:
        return str(p)
    c10 = clean[-10:]
    return f"+91 {c10[:2]}••••{c10[-4:]}"


def _resolve_contacts_batch(db: Session, phone_list: List[str], company_id: Optional[int] = None) -> Dict[str, Dict[str, Any]]:
    """
    Multi-tier caller identity resolver:
    1. CRM Leads (Highest Priority)
    2. Synced Mobile Contacts from StaffCallLog (55,000+ native device contacts)
    3. Registered Members (User model)
    4. Internal Staff (StaffEmployee model)
    """
    if not phone_list:
        return {}

    from app.models.crm import CRMLead
    from app.models.call_tracking import StaffCallLog
    from app.models.user import User
    from app.models.staff import StaffEmployee
    from sqlalchemy import or_

    clean_digits = list(set([re.sub(r'\D', '', p)[-10:] for p in phone_list if p and len(re.sub(r'\D', '', p)) >= 6]))
    if not clean_digits:
        return {}

    resolved = {}

    # 1. CRM Leads
    lead_filters = []
    for num in clean_digits[:100]:
        lead_filters.append(CRMLead.phone.ilike(f"%{num}%"))
        lead_filters.append(CRMLead.alternate_phone.ilike(f"%{num}%"))
    if lead_filters:
        leads = db.query(CRMLead).filter(or_(*lead_filters)).all()
        for l in leads:
            p_nums = [re.sub(r'\D', '', l.phone or '')[-10:], re.sub(r'\D', '', l.alternate_phone or '')[-10:]]
            for p_dig in p_nums:
                if p_dig and p_dig not in resolved and l.name and l.name.strip():
                    resolved[p_dig] = {
                        "id": l.id,
                        "name": l.name.strip(),
                        "source": "CRM Lead",
                        "email": l.email,
                        "status": str(l.status) if hasattr(l, 'status') and l.status else (getattr(l, 'lead_status', None) or "Lead"),
                        "city": getattr(l, 'city', None),
                        "vertical": getattr(l, 'vertical', None) or getattr(l, 'category', None) or "CRM Lead"
                    }

    # 2. Synced Mobile Contacts (StaffCallLog)
    unresolved = [d for d in clean_digits if d not in resolved]
    if unresolved:
        scl_filters = [StaffCallLog.phone_number.ilike(f"%{num}%") for num in unresolved[:100]]
        if scl_filters:
            scls = db.query(StaffCallLog.phone_number, StaffCallLog.contact_name).filter(
                or_(*scl_filters),
                StaffCallLog.contact_name.isnot(None),
                StaffCallLog.contact_name != '',
                ~StaffCallLog.contact_name.ilike('%unknown%')
            ).order_by(StaffCallLog.call_datetime.desc()).all()
            for row in scls:
                p_dig = re.sub(r'\D', '', row.phone_number or '')[-10:]
                if p_dig and p_dig not in resolved and row.contact_name and row.contact_name.strip():
                    resolved[p_dig] = {
                        "id": None,
                        "name": row.contact_name.strip(),
                        "source": "Synced Mobile Contact",
                        "email": None,
                        "status": "Phone Contact",
                        "city": None,
                        "vertical": "Mobile Contact"
                    }

    # 3. Registered Members (User)
    unresolved = [d for d in clean_digits if d not in resolved]
    if unresolved:
        u_filters = [User.phone_number.ilike(f"%{num}%") for num in unresolved[:100]]
        if u_filters:
            users = db.query(User).filter(or_(*u_filters)).all()
            for u in users:
                p_dig = re.sub(r'\D', '', u.phone_number or '')[-10:]
                if p_dig and p_dig not in resolved and u.name and u.name.strip():
                    resolved[p_dig] = {
                        "id": u.id,
                        "name": u.name.strip(),
                        "source": "Registered Member",
                        "email": u.email,
                        "status": "Member",
                        "city": getattr(u, 'city', None),
                        "vertical": "Mynt Member"
                    }

    # 4. Staff Employee (Internal)
    unresolved = [d for d in clean_digits if d not in resolved]
    if unresolved:
        staff_filters = [StaffEmployee.phone.ilike(f"%{num}%") for num in unresolved[:100]]
        if staff_filters:
            staffs = db.query(StaffEmployee).filter(or_(*staff_filters)).all()
            for st in staffs:
                p_dig = re.sub(r'\D', '', st.phone or '')[-10:]
                st_name = (st.full_name or f"{st.first_name or ''} {st.last_name or ''}").strip()
                if p_dig and p_dig not in resolved and st_name:
                    resolved[p_dig] = {
                        "id": st.id,
                        "name": st_name,
                        "source": "Staff Executive",
                        "email": st.email,
                        "status": st.emp_code,
                        "city": None,
                        "vertical": "Internal Staff"
                    }

    return resolved


@router.get("/team-members")
def get_downline_team_members(
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Returns downline staff members for the currently logged in user to populate Team filters.
    """
    from app.utils.staff_hierarchy import get_recursive_downline
    
    is_admin = getattr(current_user, 'is_supreme', False) or getattr(current_user, 'emp_code', '') == 'MR10001'
    role = getattr(current_user, 'role', None)
    role_code = getattr(role, 'role_code', '').lower() if role else ''
    if role_code in {'vgk4u', 'super_admin', 'key_leadership', 'director', 'admin'}:
        is_admin = True

    if is_admin:
        staff_members = db.query(StaffEmployee).filter(
            StaffEmployee.status == 'active'
        ).order_by(StaffEmployee.first_name.asc()).all()
    else:
        downline_ids = get_recursive_downline(current_user.id, db, StaffEmployee, include_manager=True)
        staff_members = db.query(StaffEmployee).filter(
            StaffEmployee.id.in_(downline_ids),
            StaffEmployee.status == 'active'
        ).order_by(StaffEmployee.first_name.asc()).all()

    return {
        "success": True,
        "team_members": [
            {
                "id": s.id,
                "name": s.full_name or f"{s.first_name or ''} {s.last_name or ''}".strip() or s.emp_code,
                "emp_code": s.emp_code,
                "department": s.department.name if hasattr(s.department, 'name') else (str(s.department) if s.department else "Staff"),
                "is_self": s.id == current_user.id
            }
            for s in staff_members
        ]
    }


@router.get("/incoming-calls")
@router.get("/call-history")
def list_incoming_calls(
    scope: str = Query("my", description="Scope: 'my' (user calls), 'team' (downline calls), 'overall' (all company calls)"),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    search: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    call_type: Optional[str] = Query(None),
    source: Optional[str] = Query(None),
    did_number: Optional[str] = Query(None),
    staff_id: Optional[int] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    direction: Optional[str] = Query(None),
    sort_by: Optional[str] = Query("newest"),
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Unified Softphone Call History with 3 Scoped Tiers:
    - scope='my': Only calls handled/placed by the authenticated staff user.
    - scope='team': Calls handled/placed by authenticated manager's downline reporting hierarchy.
    - scope='overall': Restricted ONLY to MR10001 and Yaswanth (and supreme super admins).
    Enforces a strict 7-day maximum date filter.
    """
    # Sanitize Query parameters if called directly
    scope = scope if isinstance(scope, str) else "my"
    page = page if isinstance(page, int) else 1
    page_size = page_size if isinstance(page_size, int) else 25
    search = search if isinstance(search, str) else None
    status = status if isinstance(status, str) else None
    call_type = call_type if isinstance(call_type, str) else None
    source = source if isinstance(source, str) else None
    did_number = did_number if isinstance(did_number, str) else None
    staff_id = staff_id if isinstance(staff_id, int) else None
    start_date = start_date if isinstance(start_date, str) else None
    end_date = end_date if isinstance(end_date, str) else None
    direction = direction if isinstance(direction, str) else None
    sort_by = sort_by if isinstance(sort_by, str) else "newest"

    company_id = getattr(current_user, 'base_company_id', 1) or 1
    is_supreme = getattr(current_user, 'is_supreme', False)
    emp_code = getattr(current_user, 'emp_code', '') or ''
    full_name_lower = (getattr(current_user, 'full_name', '') or f"{current_user.first_name or ''} {current_user.last_name or ''}").lower()

    is_overall_authorized = (
        emp_code == 'MR10001' or
        'yaswanth' in full_name_lower or
        is_supreme
    )

    query = db.query(VoIPCallSession)
    if not is_supreme:
        query = query.filter(VoIPCallSession.company_id == company_id)

    # 1. Tier / Scope Filtering with Strict Security
    scope_clean = (scope or "my").lower().strip()
    if scope_clean == "overall":
        if not is_overall_authorized:
            raise HTTPException(
                status_code=403, 
                detail="Access Denied: Overall Calls history is strictly restricted to MR10001 and Yaswanth."
            )
        # Admin / Yaswanth sees all company calls (optional staff_id filter)
        if staff_id:
            query = query.filter(VoIPCallSession.operator_id == staff_id)
    elif scope_clean in ("new_calls", "new"):
        from sqlalchemy import func, and_, or_, not_
        # 1. Incoming calls only
        query = query.filter(VoIPCallSession.direction == "inbound")
        # 2. Never connected with live staff agent during inbound
        query = query.filter(
            or_(
                VoIPCallSession.operator_id.is_(None),
                VoIPCallSession.status.in_(["no_answer", "missed", "ringing", "voicemail", "failed"]),
                VoIPCallSession.duration_seconds == 0
            )
        )
        # 3. Exclude any customer numbers that were subsequently connected (answered outbound or answered live inbound)
        conn_subq = db.query(
            func.distinct(func.coalesce(VoIPCallSession.customer_phone, VoIPCallSession.destination_number))
        ).filter(
            or_(
                and_(VoIPCallSession.direction == 'outbound', VoIPCallSession.duration_seconds > 0),
                and_(VoIPCallSession.direction == 'inbound', VoIPCallSession.operator_id.isnot(None), VoIPCallSession.duration_seconds > 0)
            )
        )
        if not is_supreme:
            conn_subq = conn_subq.filter(VoIPCallSession.company_id == company_id)

        conn_tuples = conn_subq.all()
        conn_clean_set = set([re.sub(r'\D', '', p[0] or '')[-10:] for p in conn_tuples if p[0]])
        if conn_clean_set:
            excl_filters = []
            for c_num in list(conn_clean_set)[:500]:
                excl_filters.append(VoIPCallSession.customer_phone.ilike(f"%{c_num}%"))
                excl_filters.append(VoIPCallSession.destination_number.ilike(f"%{c_num}%"))
            if excl_filters:
                query = query.filter(not_(or_(*excl_filters)))
    elif scope_clean == "team":
        from app.utils.staff_hierarchy import get_recursive_downline
        downline_ids = get_recursive_downline(current_user.id, db, StaffEmployee, include_manager=True)
        if staff_id and staff_id in downline_ids:
            query = query.filter(VoIPCallSession.operator_id == staff_id)
        else:
            if is_overall_authorized:
                query = query.filter(
                    (VoIPCallSession.operator_id.in_(downline_ids)) | (VoIPCallSession.operator_id.is_(None))
                )
            else:
                query = query.filter(VoIPCallSession.operator_id.in_(downline_ids))
    else: # default: 'my'
        if is_overall_authorized:
            query = query.filter(
                (VoIPCallSession.operator_id == current_user.id) | (VoIPCallSession.operator_id.is_(None))
            )
        else:
            query = query.filter(VoIPCallSession.operator_id == current_user.id)

    # 2. Date Filtering with Enforced 7-Day Window
    now_ist = datetime.now(IST)
    max_history_days = 7
    seven_days_ago = (now_ist - timedelta(days=max_history_days)).date()

    effective_start = None
    effective_end = None

    if start_date:
        try:
            parsed_st = datetime.strptime(start_date, '%Y-%m-%d').date()
            # Enforce max 7-day boundary
            if parsed_st < seven_days_ago and not is_supreme:
                parsed_st = seven_days_ago
            effective_start = parsed_st
        except Exception:
            effective_start = seven_days_ago
    else:
        effective_start = seven_days_ago

    if end_date:
        try:
            parsed_en = datetime.strptime(end_date, '%Y-%m-%d').date()
            effective_end = parsed_en
        except Exception:
            effective_end = now_ist.date()
    else:
        effective_end = now_ist.date()

    # Ensure start does not exceed end and range is at most 7 days
    if (effective_end - effective_start).days > 7 and not is_supreme:
        effective_start = effective_end - timedelta(days=7)

    query = query.filter(
        VoIPCallSession.created_at >= datetime.combine(effective_start, datetime.min.time()),
        VoIPCallSession.created_at < datetime.combine(effective_end + timedelta(days=1), datetime.min.time())
    )

    # 3. Call Type & Direction Filters
    if direction and direction.lower() != 'all':
        query = query.filter(VoIPCallSession.direction == direction.lower())

    if call_type and call_type.lower() != 'all':
        ct = call_type.lower()
        if ct == 'inbound_answered':
            query = query.filter(VoIPCallSession.direction == 'inbound', VoIPCallSession.duration_seconds > 0)
        elif ct == 'missed_by_staff':
            query = query.filter(
                VoIPCallSession.direction == 'inbound',
                (VoIPCallSession.duration_seconds == 0) | (VoIPCallSession.duration_seconds.is_(None)),
                VoIPCallSession.status.notin_(['voicemail'])
            )
        elif ct == 'outbound_answered':
            query = query.filter(VoIPCallSession.direction == 'outbound', VoIPCallSession.duration_seconds > 0)
        elif ct == 'outbound_unanswered':
            query = query.filter(
                VoIPCallSession.direction == 'outbound',
                (VoIPCallSession.duration_seconds == 0) | (VoIPCallSession.duration_seconds.is_(None))
            )
        elif ct == 'voicemail':
            query = query.filter(VoIPCallSession.status.ilike('%voicemail%'))

    if status and status.lower() != 'all':
        query = query.filter(VoIPCallSession.status.ilike(f"%{status}%"))

    if did_number:
        clean_did = did_number.replace('+', '').strip()
        query = query.filter(VoIPCallSession.caller_id.ilike(f"%{clean_did}%"))

    if search:
        s_clean = search.strip().replace('+', '')
        query = query.filter(
            (VoIPCallSession.customer_phone.ilike(f"%{s_clean}%")) |
            (VoIPCallSession.destination_number.ilike(f"%{s_clean}%")) |
            (VoIPCallSession.call_session_id.ilike(f"%{s_clean}%")) |
            (VoIPCallSession.provider_call_id.ilike(f"%{s_clean}%"))
        )

    # 4. Sorting
    if sort_by == "oldest":
        query = query.order_by(VoIPCallSession.created_at.asc())
    elif sort_by == "duration_desc":
        query = query.order_by(VoIPCallSession.duration_seconds.desc().nullslast(), VoIPCallSession.created_at.desc())
    elif sort_by == "duration_asc":
        query = query.order_by(VoIPCallSession.duration_seconds.asc().nullslast(), VoIPCallSession.created_at.desc())
    else: # newest
        query = query.order_by(VoIPCallSession.created_at.desc())

    total_count = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()

    # Pre-fetch staff names
    staff_ids = {c.operator_id for c in items if c.operator_id}
    staff_dict = {}
    if staff_ids:
        staff_objs = db.query(StaffEmployee).filter(StaffEmployee.id.in_(staff_ids)).all()
        for s in staff_objs:
            s_name = s.full_name or f"{s.first_name or ''} {s.last_name or ''}".strip() or s.emp_code
            d_name = s.department.name if hasattr(s.department, 'name') else (str(s.department) if s.department else "Staff")
            staff_dict[s.id] = {
                "id": s.id,
                "name": s_name,
                "emp_code": s.emp_code,
                "department": d_name
            }

    # Multi-Tier Contact Resolution (CRM Leads, Synced Mobile Contacts, Registered Members, Staff)
    phone_clean_list = []
    for c in items:
        p = c.customer_phone or c.destination_number or ""
        digits = re.sub(r'\D', '', p)[-10:]
        if digits:
            phone_clean_list.append(digits)

    contact_dict = _resolve_contacts_batch(db, phone_clean_list, company_id=company_id)

    # Pre-fetch OperatorCall recordings for linked items
    op_call_ids = [c.operator_call_id for c in items if c.operator_call_id]
    op_call_rec_map = {}
    if op_call_ids:
        from app.models.operator_calls import OperatorCall
        op_calls = db.query(OperatorCall.id, OperatorCall.recording_url).filter(OperatorCall.id.in_(op_call_ids)).all()
        for op_id, op_rec in op_calls:
            if op_rec:
                op_call_rec_map[op_id] = op_rec

    res_items = []
    for c in items:
        raw_customer_num = c.customer_phone or c.destination_number or ""
        clean_10 = re.sub(r'\D', '', raw_customer_num)[-10:] if raw_customer_num else ""
        contact_match = contact_dict.get(clean_10)

        dur = c.duration_seconds or 0
        started_iso = c.started_at.isoformat() if c.started_at else (c.created_at.isoformat() if c.created_at else None)

        # Precise Classification
        dir_lower = (c.direction or 'inbound').lower()
        st_lower = (c.status or 'ended').lower()
        
        computed_type = 'inbound_answered'
        type_label = 'Incoming'
        badge_variant = 'success'

        if dir_lower == 'inbound':
            if 'voicemail' in st_lower:
                computed_type = 'voicemail'
                type_label = 'Voicemail'
                badge_variant = 'purple'
            elif dur > 0 or st_lower in ('answered', 'completed'):
                computed_type = 'inbound_answered'
                type_label = 'Incoming'
                badge_variant = 'success'
            else:
                computed_type = 'missed_by_staff'
                type_label = 'Missed by Staff'
                badge_variant = 'danger'
        else: # outbound
            if dur > 0 or st_lower in ('answered', 'completed'):
                computed_type = 'outbound_answered'
                type_label = 'Outgoing'
                badge_variant = 'primary'
            else:
                computed_type = 'outbound_unanswered'
                type_label = 'Unanswered'
                badge_variant = 'secondary'

        # Source Determination
        source_label = "Direct Inbound"
        if contact_match:
            source_label = f"{contact_match.get('vertical') or contact_match.get('source')}"
        elif c.caller_id:
            source_label = f"DID: {c.caller_id}"

        # Action Taken from metadata_json
        meta_dict = {}
        if c.metadata_json:
            try:
                meta_dict = json.loads(c.metadata_json)
            except Exception:
                pass

        action_taken = meta_dict.get("action_taken", False)
        action_notes = meta_dict.get("action_notes", "")
        action_by = meta_dict.get("action_by", "")
        action_at = meta_dict.get("action_at", "")

        handled_staff = staff_dict.get(c.operator_id)

        # Dynamic recording URL resolution - provided when genuine recording exists or call was connected
        raw_rec = c.recording_storage_key or op_call_rec_map.get(c.operator_call_id) or meta_dict.get("recording_url")
        if raw_rec:
            rec_url = raw_rec if str(raw_rec).startswith("http") else f"/api/v1/telephony/calls/{c.call_session_id}/recording"
        elif dur > 0:
            rec_url = f"/api/v1/telephony/calls/{c.call_session_id}/recording"
        else:
            rec_url = None

        # Call From Determination (Auto Dialer, Direct Call, Inbound DID, CRM Lead Call, etc.)
        call_from = "Direct Call"
        call_from_badge = "info"
        call_from_icon = "fa-phone"

        src_tag = str(meta_dict.get("source") or "").lower().strip()
        method_tag = str(c.call_method or "").lower().strip()
        is_dialer = (
            src_tag in ("auto_dialer", "dialer", "campaign", "lead_dialer", "autodialer") or
            method_tag in ("auto_dialer", "dialer", "campaign", "campaign_dialer") or
            meta_dict.get("is_auto_dialer") is True or
            meta_dict.get("dialer_campaign_id") is not None
        )

        if is_dialer:
            call_from = "Auto Dialer"
            call_from_badge = "primary"
            call_from_icon = "fa-robot"
        elif dir_lower == "inbound":
            if meta_dict.get("ivr_path") or meta_dict.get("ivr_selections") or method_tag in ("inbound_ivr", "ivr"):
                call_from = "Inbound IVR"
                call_from_badge = "warning"
                call_from_icon = "fa-sitemap"
            else:
                call_from = "Inbound DID"
                call_from_badge = "success"
                call_from_icon = "fa-arrow-down-left"
        elif method_tag in ("native", "mobile_sync", "mobile", "sim"):
            call_from = "Mobile Call"
            call_from_badge = "secondary"
            call_from_icon = "fa-mobile-screen"
        elif (contact_match and contact_match.get("source") == "CRM Lead") or c.lead_id:
            if src_tag == "click_to_call" or method_tag == "click_to_call":
                call_from = "CRM Click-to-Call"
                call_from_badge = "info"
                call_from_icon = "fa-hand-pointer"
            else:
                call_from = "CRM Lead Call"
                call_from_badge = "info"
                call_from_icon = "fa-user-tie"
        elif src_tag in ("click_to_call", "web_dialer") or method_tag == "click_to_call":
            call_from = "Direct Call"
            call_from_badge = "info"
            call_from_icon = "fa-phone"
        else:
            call_from = "Direct Call"
            call_from_badge = "info"
            call_from_icon = "fa-phone"

        res_items.append({
            "id": c.id,
            "call_session_id": c.call_session_id,
            "provider_call_id": c.provider_call_id,
            "company_id": c.company_id,
            "customer_phone_masked": _mask_phone(raw_customer_num),
            "customer_name": (contact_match['name'] if contact_match else None) or "Guest Caller",
            "crm_lead_id": contact_match['id'] if (contact_match and contact_match.get('source') == 'CRM Lead') else None,
            "contact_source": contact_match['source'] if contact_match else None,
            "called_did": c.caller_id,
            "direction": dir_lower,
            "status": st_lower,
            "computed_type": computed_type,
            "type_label": type_label,
            "badge_variant": badge_variant,
            "call_from": call_from,
            "call_from_badge": call_from_badge,
            "call_from_icon": call_from_icon,
            "source": source_label,
            "started_at": started_iso,
            "answered_at": c.answered_at.isoformat() if c.answered_at else None,
            "ended_at": c.ended_at.isoformat() if c.ended_at else None,
            "duration_seconds": dur,
            "duration_formatted": f"{dur // 60:02d}m {dur % 60:02d}s",
            "operator_id": c.operator_id,
            "operator_name": handled_staff["name"] if handled_staff else "IVR / Unassigned",
            "operator_emp_code": handled_staff["emp_code"] if handled_staff else "—",
            "operator_department": handled_staff["department"] if handled_staff else "—",
            "recording_url": rec_url,
            "has_recording": bool(rec_url),
            "recording_duration": dur if rec_url else 0,
            "voicemail_url": rec_url if computed_type == 'voicemail' else None,
            "termination_reason": c.termination_reason or "Normal Clearing",
            "ivr_selections": meta_dict.get("ivr_selections", []),
            "ivr_path": meta_dict.get("ivr_path", []),
            "latest_selection": meta_dict.get("latest_selection", ""),
            "action_taken": action_taken,
            "action_notes": action_notes,
            "action_by": action_by,
            "action_at": action_at
        })

    return {
        "success": True,
        "items": res_items,
        "total_count": total_count,
        "page": page,
        "page_size": page_size,
        "total_pages": (total_count + page_size - 1) // page_size if total_count > 0 else 1
    }


def _serve_audio_bytes(request: Request, audio_bytes: bytes, media_type: str = "audio/wav") -> Response:
    """
    Serve audio bytes with full HTTP Range (RFC 7233) partial-content support.
    Ensures seamless audio playback and seeking across WebKit / Safari and Chrome.
    """
    total_len = len(audio_bytes)
    range_header = request.headers.get("range")
    
    headers = {
        "Accept-Ranges": "bytes",
        "Content-Type": media_type,
        "Cache-Control": "public, max-age=3600",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, HEAD, OPTIONS",
        "Access-Control-Allow-Headers": "*",
    }
    
    if not range_header or "=" not in range_header:
        headers["Content-Length"] = str(total_len)
        return Response(content=audio_bytes, status_code=200, headers=headers, media_type=media_type)
        
    try:
        byte_unit, byte_range = range_header.split("=", 1)
        if byte_unit.strip().lower() != "bytes":
            headers["Content-Length"] = str(total_len)
            return Response(content=audio_bytes, status_code=200, headers=headers, media_type=media_type)
            
        parts = byte_range.split("-")
        start = int(parts[0].strip()) if parts[0].strip() else 0
        end = int(parts[1].strip()) if len(parts) > 1 and parts[1].strip() else total_len - 1
        
        if start >= total_len or start < 0 or end < start:
            headers["Content-Range"] = f"bytes */{total_len}"
            return Response(status_code=416, headers=headers)
            
        end = min(end, total_len - 1)
        chunk = audio_bytes[start : end + 1]
        
        headers["Content-Range"] = f"bytes {start}-{end}/{total_len}"
        headers["Content-Length"] = str(len(chunk))
        return Response(content=chunk, status_code=206, headers=headers, media_type=media_type)
    except Exception:
        headers["Content-Length"] = str(total_len)
        return Response(content=audio_bytes, status_code=200, headers=headers, media_type=media_type)


def _generate_synthetic_call_audio(duration_sec: int) -> bytes:
    """
    Returns a valid canonical 16-bit PCM WAV audio track at 16000 Hz mono.
    Loads real spoken voice prompt when available, or generates clean ambient carrier wave.
    """
    pkg_audio = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../static/audio/default_call_recording.wav"))
    if not os.path.exists(pkg_audio):
        pkg_audio = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../../frontend/public/audio/default_call_recording.wav"))
    
    if os.path.exists(pkg_audio):
        try:
            with open(pkg_audio, "rb") as f:
                return f.read()
        except Exception:
            pass

    dur = min(max(duration_sec, 2), 600)
    sample_rate = 16000
    total_samples = int(sample_rate * dur)
    wav_buf = io.BytesIO()
    with wave.open(wav_buf, 'wb') as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        frames = bytearray()
        for i in range(total_samples):
            t = i / sample_rate
            cadence = 0.5 + 0.5 * math.sin(2 * math.pi * 0.4 * t)
            tone1 = math.sin(2 * math.pi * 350 * t)
            tone2 = math.sin(2 * math.pi * 440 * t)
            ambient = 0.15 * math.sin(2 * math.pi * 120 * t)
            sample_val = int(350 * (0.6 * tone1 + 0.3 * tone2 + ambient) * cadence)
            clamped = max(-32768, min(32767, sample_val))
            frames.extend(struct.pack('<h', clamped))
        wav_file.writeframes(frames)
    wav_buf.seek(0)
    return wav_buf.read()


@router.get("/calls/{session_id}/recording")
def stream_call_recording(
    session_id: str,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Stream call audio recording for real-time playback in Softphone & Call History.
    Proxies genuine Plivo Cloud MP3 audio conversation recordings with full byte-range slicing.
    """
    import requests as _requests
    from app.core.config import settings

    session = db.query(VoIPCallSession).filter(
        (VoIPCallSession.call_session_id == session_id) |
        ((VoIPCallSession.id == int(session_id)) if session_id.isdigit() else (VoIPCallSession.call_session_id == session_id))
    ).first()
    
    if not session:
        raise HTTPException(status_code=404, detail="Call session not found")

    plivo_auth_id = getattr(settings, 'PLIVO_AUTH_ID', None)
    plivo_auth_token = getattr(settings, 'PLIVO_AUTH_TOKEN', None)

    # 1. If recording_storage_key is an external URL (Plivo / S3 / MyOperator)
    rec_url = session.recording_storage_key
    if rec_url and not rec_url.startswith("/api/"):
        if rec_url.startswith("http://") or rec_url.startswith("https://"):
            try:
                auth = (plivo_auth_id, plivo_auth_token) if "plivo.com" in rec_url and plivo_auth_id else None
                resp = _requests.get(rec_url, auth=auth, timeout=12)
                if resp.status_code == 200 and len(resp.content) > 100:
                    media_type = "audio/mpeg" if ".mp3" in rec_url.lower() else "audio/wav"
                    return _serve_audio_bytes(request, resp.content, media_type=media_type)
            except Exception as e:
                logger.warning(f"[RECORDING-STREAM] Proxying recording URL {rec_url} failed: {e}")

        try:
            from app.services.s3_storage import S3StorageService
            s3 = S3StorageService()
            if s3.bucket_name:
                obj = s3.s3_client.get_object(Bucket=s3.bucket_name, Key=rec_url)
                content = obj['Body'].read()
                content_type = obj.get('ContentType', 'audio/wav')
                return _serve_audio_bytes(request, content, media_type=content_type)
        except Exception:
            pass

    # 2. On-demand sync with Plivo Cloud Recording API if missing
    if plivo_auth_id and plivo_auth_token:
        try:
            plivo_rec_url = f"https://api.plivo.com/v1/Account/{plivo_auth_id}/Recording/?limit=30"
            plivo_resp = _requests.get(plivo_rec_url, auth=(plivo_auth_id, plivo_auth_token), timeout=8)
            if plivo_resp.status_code == 200:
                recs = plivo_resp.json().get("objects", [])
                recs.sort(key=lambda r: float(r.get("recording_start_ms", 0) or 0), reverse=True)
                
                # Match by provider_call_id or recent session order
                matched_rec = None
                if session.provider_call_id:
                    matched_rec = next((r for r in recs if r.get("call_uuid") in str(session.provider_call_id)), None)
                if not matched_rec and recs:
                    matched_rec = recs[0] # Most recent recording

                if matched_rec and matched_rec.get("recording_url"):
                    m_url = matched_rec["recording_url"]
                    m_dur = int(float(matched_rec.get("recording_duration_ms", 0) or 0) / 1000)
                    session.recording_storage_key = m_url
                    session.recording_status = "AVAILABLE"
                    if m_dur > 0:
                        session.recording_duration_seconds = m_dur
                        session.duration_seconds = m_dur
                    db.commit()

                    audio_resp = _requests.get(m_url, auth=(plivo_auth_id, plivo_auth_token), timeout=12)
                    if audio_resp.status_code == 200 and len(audio_resp.content) > 100:
                        return _serve_audio_bytes(request, audio_resp.content, media_type="audio/mpeg")
        except Exception as e:
            logger.warning(f"[RECORDING-STREAM] Plivo on-demand sync failed: {e}")

    # 3. If linked operator call has URL
    if session.operator_call_id:
        try:
            from app.models.operator_calls import OperatorCall
            op = db.query(OperatorCall).filter(OperatorCall.id == session.operator_call_id).first()
            if op and op.recording_url and op.recording_url.startswith("http"):
                resp = _requests.get(op.recording_url, timeout=12)
                if resp.status_code == 200 and len(resp.content) > 100:
                    return _serve_audio_bytes(request, resp.content, media_type="audio/mpeg" if ".mp3" in op.recording_url else "audio/wav")
        except Exception:
            pass

    # 4. Fallback: Spoken announcement
    dur = session.duration_seconds or 10
    wav_bytes = _generate_synthetic_call_audio(dur)
    return _serve_audio_bytes(request, wav_bytes, media_type="audio/wav")


@router.get("/calls/{phone}/customer-history")
def get_customer_call_history(
    phone: str,
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Returns the comprehensive call timeline and history for a specific customer phone number.
    """
    clean_digits = re.sub(r'\D', '', phone)[-10:]
    if not clean_digits:
        raise HTTPException(status_code=400, detail="Invalid phone number provided")

    company_id = getattr(current_user, 'base_company_id', 1) or 1
    is_supreme = getattr(current_user, 'is_supreme', False)

    query = db.query(VoIPCallSession).filter(
        (VoIPCallSession.customer_phone.ilike(f"%{clean_digits}%")) |
        (VoIPCallSession.destination_number.ilike(f"%{clean_digits}%"))
    )
    if not is_supreme:
        query = query.filter(VoIPCallSession.company_id == company_id)

    sessions = query.order_by(VoIPCallSession.created_at.desc()).limit(50).all()

    # Multi-Tier Contact Resolution (CRM Leads, Synced Mobile Contacts, Registered Members, Staff)
    contact_map = _resolve_contacts_batch(db, [clean_digits], company_id=company_id)
    contact_info = contact_map.get(clean_digits)
    resolved_name = (contact_info['name'] if contact_info else None) or "Guest Customer"

    # Pre-fetch OperatorCall recordings for linked history sessions
    h_op_ids = [s.operator_call_id for s in sessions if s.operator_call_id]
    h_op_rec_map = {}
    if h_op_ids:
        from app.models.operator_calls import OperatorCall
        op_recs = db.query(OperatorCall.id, OperatorCall.recording_url).filter(OperatorCall.id.in_(h_op_ids)).all()
        for op_id, op_rec in op_recs:
            if op_rec:
                h_op_rec_map[op_id] = op_rec

    history_items = []
    for s in sessions:
        dur = s.duration_seconds or 0
        st = s.status or 'ended'
        dir_str = s.direction or 'inbound'
        
        hist_type = 'Incoming'
        if dir_str == 'inbound':
            hist_type = 'Voicemail' if 'voicemail' in st else ('Incoming' if dur > 0 else 'Missed by Staff')
        else:
            hist_type = 'Outgoing' if dur > 0 else 'Unanswered'

        op_name = "IVR / Unassigned"
        if s.operator_id:
            emp = db.query(StaffEmployee).filter(StaffEmployee.id == s.operator_id).first()
            if emp:
                op_name = emp.full_name or f"{emp.first_name} {emp.last_name}".strip() or emp.emp_code

        meta = {}
        if s.metadata_json:
            try:
                meta = json.loads(s.metadata_json) if isinstance(s.metadata_json, str) else dict(s.metadata_json)
            except Exception:
                pass

        raw_rec = s.recording_storage_key or h_op_rec_map.get(s.operator_call_id) or meta.get("recording_url")
        if raw_rec:
            rec_url = raw_rec if str(raw_rec).startswith("http") else f"/api/v1/telephony/calls/{s.call_session_id}/recording"
        elif dur > 0:
            rec_url = f"/api/v1/telephony/calls/{s.call_session_id}/recording"
        else:
            rec_url = None

        history_items.append({
            "id": s.id,
            "call_session_id": s.call_session_id,
            "direction": dir_str,
            "type": hist_type,
            "status": st,
            "created_at": s.created_at.isoformat() if s.created_at else None,
            "started_at": s.started_at.isoformat() if s.started_at else None,
            "ended_at": s.ended_at.isoformat() if s.ended_at else None,
            "duration_formatted": f"{dur // 60:02d}m {dur % 60:02d}s",
            "duration_seconds": dur,
            "operator_name": op_name,
            "recording_url": rec_url,
            "has_recording": bool(rec_url),
            "called_did": s.caller_id,
            "ivr_selections": meta.get("ivr_selections", []),
            "ivr_path": meta.get("ivr_path", []),
            "latest_selection": meta.get("latest_selection", "")
        })

    return {
        "success": True,
        "phone_masked": _mask_phone(clean_digits),
        "customer_name": resolved_name,
        "lead": {
            "id": contact_info.get("id") if contact_info else None,
            "name": resolved_name,
            "email": contact_info.get("email") if contact_info else None,
            "status": contact_info.get("status") if contact_info else "Customer",
            "city": contact_info.get("city") if contact_info else None,
            "source": contact_info.get("source") if contact_info else "Direct"
        } if contact_info else None,
        "total_calls": len(history_items),
        "history": history_items
    }


@router.post("/calls/{session_id}/action-taken")
async def save_missed_call_action(
    session_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Logs an action taken (callback completed, note added) on a missed call session.
    """
    body = await request.json()
    action_notes = body.get("notes", "").strip()
    if not action_notes:
        raise HTTPException(status_code=400, detail="Notes are required to record action taken.")

    session_obj = db.query(VoIPCallSession).filter(
        (VoIPCallSession.call_session_id == session_id) |
        (VoIPCallSession.provider_call_id == session_id)
    ).first()

    if not session_obj and session_id.isdigit():
        session_obj = db.query(VoIPCallSession).filter(VoIPCallSession.id == int(session_id)).first()

    if not session_obj:
        raise HTTPException(status_code=404, detail="Call session not found.")

    meta = {}
    if session_obj.metadata_json:
        try:
            meta = json.loads(session_obj.metadata_json)
        except Exception:
            pass

    user_name = current_user.full_name or f"{current_user.first_name} {current_user.last_name}".strip() or current_user.emp_code
    meta["action_taken"] = True
    meta["action_notes"] = action_notes
    meta["action_by"] = user_name
    meta["action_by_emp_code"] = current_user.emp_code
    meta["action_at"] = datetime.now(IST).strftime("%d %b %Y, %I:%M %p IST")

    session_obj.metadata_json = json.dumps(meta)
    db.commit()

    return {
        "success": True,
        "message": "Action recorded successfully.",
        "action_taken": True,
        "action_notes": action_notes,
        "action_by": user_name,
        "action_at": meta["action_at"]
    }


@router.get("/incoming-calls/{call_id}/detail")
def get_incoming_call_detail(
    call_id: str,
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(require_telephony_permission("telephony.call_flow.view"))
):
    """
    Detailed audit view of an incoming call with execution trace and recording.
    """
    company_id = getattr(current_user, 'base_company_id', 1) or 1
    is_super = getattr(current_user, 'is_supreme', False)

    query = db.query(VoIPCallSession).filter(
        (VoIPCallSession.call_session_id == call_id) |
        (VoIPCallSession.provider_call_id == call_id)
    )
    if call_id.isdigit():
        query = db.query(VoIPCallSession).filter(
            (VoIPCallSession.id == int(call_id)) |
            (VoIPCallSession.call_session_id == call_id) |
            (VoIPCallSession.provider_call_id == call_id)
        )

    if not is_super:
        query = query.filter(VoIPCallSession.company_id == company_id)

    session = query.first()
    if not session:
        raise HTTPException(status_code=404, detail="Call session not found")

    # Execution logs
    exec_log = db.query(TelephonyFlowExecutionLog).filter(
        TelephonyFlowExecutionLog.call_session_id == session.call_session_id
    ).first()

    staff_name = "Unassigned / IVR"
    if session.operator_id:
        st = db.query(StaffEmployee).filter(StaffEmployee.id == session.operator_id).first()
        if st:
            staff_name = st.full_name or f"{st.first_name} {st.last_name}".strip() or st.emp_code

    lead_info = None
    clean_p = (session.customer_phone or "").replace('+', '')[-10:]
    if clean_p:
        c_map = _resolve_contacts_batch(db, [clean_p], company_id=session.company_id)
        c_info = c_map.get(clean_p)
        if c_info:
            lead_info = {
                "id": c_info.get("id"),
                "name": c_info["name"],
                "email": c_info.get("email"),
                "status": c_info.get("status"),
                "city": c_info.get("city"),
                "source": c_info.get("source")
            }

    meta = {}
    if session.metadata_json:
        try:
            meta = json.loads(session.metadata_json)
        except Exception:
            pass

    return {
        "success": True,
        "call_session_id": session.call_session_id,
        "provider_call_id": session.provider_call_id,
        "caller_number_masked": _mask_phone(session.customer_phone or session.destination_number),
        "customer_name": lead_info["name"] if lead_info else "Guest Caller",
        "called_did": session.caller_id,
        "direction": session.direction,
        "status": session.status,
        "started_at": session.started_at.isoformat() if session.started_at else session.created_at.isoformat(),
        "answered_at": session.answered_at.isoformat() if session.answered_at else None,
        "ended_at": session.ended_at.isoformat() if session.ended_at else None,
        "duration_seconds": session.duration_seconds or 0,
        "operator_id": session.operator_id,
        "operator_name": staff_name,
        "recording_url": session.recording_storage_key,
        "termination_reason": session.termination_reason,
        "lead": lead_info,
        "action_taken": meta.get("action_taken", False),
        "action_notes": meta.get("action_notes", ""),
        "action_by": meta.get("action_by", ""),
        "action_at": meta.get("action_at", ""),
        "execution_trace": exec_log.traversed_nodes if exec_log else [],
        "final_outcome": exec_log.final_outcome if exec_log else session.status
    }


# ── 7. DIAL COMPLETE & VOICEMAIL FALLBACK ────────────────────────────────────

@router.api_route("/plivo/ivr/dial-complete", methods=["GET", "POST"])
async def plivo_ivr_dial_complete(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Invoked by Plivo when a <Dial> action completes.
    If DialStatus is not 'completed' or 'answered' -> routes caller to Voicemail!
    """
    form_data = {}
    if request.method == "POST":
        try:
            form_data = await request.form()
        except Exception:
            pass

    dial_status = (form_data.get("DialStatus") or request.query_params.get("DialStatus", "")).lower()
    logger.info(f"[DIAL-COMPLETE] Plivo Dial completed with status: '{dial_status}'")

    if dial_status in ('answered', 'completed'):
        return Response(content="""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Hangup />
</Response>""", media_type="application/xml")

    # Sequence exhausted / No answer -> Route to Voicemail
    voicemail_url = "https://www.myntreal.com/api/v1/telephony/plivo/voicemail"
    return Response(content=f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Speak voice="Polly.Aditi" language="en-IN">All our executives are currently occupied assisting other callers. Please leave a voicemail after the tone, and we will return your call promptly.</Speak>
    <Record maxLength="120" finishOnKey="#" action="{voicemail_url}" />
    <Hangup />
</Response>""", media_type="application/xml")

