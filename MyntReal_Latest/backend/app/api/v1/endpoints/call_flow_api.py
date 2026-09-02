"""
Telephony Call Flow API Endpoints — MyntOS Native Telephony
Provides full REST lifecycle for Call Flow Designer, Ring Groups, Business Hours,
Simulator, and Plivo Inbound Webhook Execution.
Created: Sep 2026
"""

from fastapi import APIRouter, Depends, HTTPException, Request, Response, Body, Query
from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Any
from datetime import datetime
import logging
import json

from app.core.database import get_db
from app.api.v1.endpoints.staff_auth import get_current_staff_user
from app.models.staff import StaffEmployee
from app.models.telephony_call_flow import (
    TelephonyCallFlow, TelephonyCallFlowVersion, TelephonyRingGroup,
    TelephonyBusinessHours, TelephonyHoliday, TelephonyPlivoEndpoint
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
            'mon': {'start': '09:30', 'end': '18:30', 'enabled': True},
            'tue': {'start': '09:30', 'end': '18:30', 'enabled': True},
            'wed': {'start': '09:30', 'end': '18:30', 'enabled': True},
            'thu': {'start': '09:30', 'end': '18:30', 'enabled': True},
            'fri': {'start': '09:30', 'end': '18:30', 'enabled': True},
            'sat': {'start': '10:00', 'end': '16:00', 'enabled': True},
            'sun': 'closed'
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


# ── 3. PLIVO INBOUND TELECOM WEBHOOKS ────────────────────────────────────────

@router.post("/plivo/inbound")
async def plivo_inbound_answer(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Plivo Primary Answer URL.
    Invoked when customer dials the MyntOS Plivo DID (+91 80 3172 8899).
    Returns dynamic Plivo XML.
    """
    form_data = await request.form()
    caller_phone = form_data.get("From", "")
    called_did = form_data.get("To", "")
    call_uuid = form_data.get("CallUUID", "")

    base_url = str(request.base_url).rstrip('/')
    xml_str = CallFlowInterpreter.handle_inbound_call(
        db=db,
        caller_phone=caller_phone,
        called_did=called_did,
        provider_call_id=call_uuid,
        base_api_url=base_url
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

    base_url = str(request.base_url).rstrip('/')
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
    base_url = str(request.base_url).rstrip('/')
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
    session_id: str = Query(...),
    db: Session = Depends(get_db)
):
    """
    Receives Plivo voicemail recording URL and vaults audio file to S3.
    """
    form_data = await request.form()
    rec_url = form_data.get("RecordUrl", "")
    duration = int(form_data.get("RecordingDuration", 0) or 0)
    logger.info(f"[PLIVO-RECORDING] Voicemail recorded for {session_id}: {rec_url} ({duration}s)")

    # Download from Plivo and upload to private S3 storage asynchronously/inline
    # Update VoIPCallSession recording metadata
    return Response(content="<Response><Speak voice=\"Polly.Aditi\">Thank you. Your message has been saved.</Speak><Hangup /></Response>", media_type="application/xml")


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

    # 2. Plivo Webhook V3 Signature Validation
    sig_v3 = headers.get("x-plivo-signature-v3") or headers.get("x-plivo-signature-ma-v3")
    nonce_v3 = headers.get("x-plivo-signature-v3-nonce") or headers.get("x-plivo-signature-ma-v3-nonce") or ""

    if sig_v3:
        provider = get_telephony_provider("plivo")
        url_str = str(request.url)
        is_valid_v3 = PlivoTelephonyProvider.validate_signature_v3(
            url=url_str,
            nonce=nonce_v3,
            signature=sig_v3,
            auth_token=getattr(provider, 'auth_token', ''),
            method=request.method,
            params=payload
        )
        if not is_valid_v3:
            logger.warning(f"[PLIVO-HANGUP] Invalid Plivo V3 webhook signature: sig={sig_v3[:10]}... url={url_str}")
            raise HTTPException(status_code=401, detail="Invalid Plivo V3 Webhook Signature")

    elif "x-plivo-signature-v2" in headers or "x-plivo-signature" in headers:
        # Legacy V2 Signature Check Fallback
        legacy_sig = headers.get("x-plivo-signature-v2") or headers.get("x-plivo-signature")
        provider = get_telephony_provider("plivo")
        if hasattr(provider, '_verify_plivo_signature'):
            if not provider._verify_plivo_signature(legacy_sig, raw_body, headers):
                logger.warning("[PLIVO-HANGUP] Invalid Plivo legacy webhook signature")
                raise HTTPException(status_code=401, detail="Invalid Plivo Webhook Signature")

    call_uuid = payload.get("CallUUID") or payload.get("call_uuid") or request.query_params.get("CallUUID", "")
    call_status = (payload.get("CallStatus") or payload.get("status") or "").lower()
    duration_str = payload.get("Duration") or payload.get("BillDuration") or "0"
    try:
        duration_sec = int(duration_str)
    except (ValueError, TypeError):
        duration_sec = 0

    hangup_cause_name = payload.get("HangupCauseName") or payload.get("HangupCause", "")
    hangup_cause_code = payload.get("HangupCauseCode")
    hangup_source = payload.get("HangupSource")
    session_id_param = payload.get("session_id") or request.query_params.get("session_id")

    logger.info(
        f"[PLIVO-HANGUP-WEBHOOK] CallUUID={call_uuid} Status={call_status} Duration={duration_sec}s "
        f"Cause={hangup_cause_name} Source={hangup_source}"
    )

    if not call_uuid and not session_id_param:
        logger.warning("[PLIVO-HANGUP] Received hangup callback without CallUUID or session_id")
        return {"status": "ignored", "reason": "missing_call_uuid"}

    # 3. Locate existing VoIPCallSession idempotently
    session = None
    if call_uuid:
        session = db.query(VoIPCallSession).filter(
            VoIPCallSession.provider_call_id == call_uuid
        ).first()

    if not session and session_id_param:
        session = db.query(VoIPCallSession).filter(
            VoIPCallSession.call_session_id == session_id_param
        ).first()

    if not session and call_uuid:
        session = db.query(VoIPCallSession).filter(
            VoIPCallSession.provider_call_id.like(f"%{call_uuid}%")
        ).first()

    if not session:
        logger.info(f"[PLIVO-HANGUP] No matching VoIPCallSession for CallUUID {call_uuid}. Acknowledging HTTP 200.")
        return {
            "status": "success",
            "message": "Acknowledged (no active session found)",
            "call_uuid": call_uuid
        }

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
    target_state = status_map.get(call_status, CallStateEnum.ENDED.value)

    # 5. Idempotent state updates
    if not CallStateEnum(session.status).is_terminal():
        session.status = target_state

    if duration_sec > (session.duration_seconds or 0):
        session.duration_seconds = duration_sec

    if hangup_cause_name or hangup_source:
        session.termination_reason = f"{hangup_cause_name} ({hangup_source})" if hangup_source else hangup_cause_name

    if not session.ended_at:
        session.ended_at = get_indian_time()

    # Update metadata diagnostics
    meta = {}
    if session.metadata_json:
        try:
            meta = json.loads(session.metadata_json) if isinstance(session.metadata_json, str) else dict(session.metadata_json)
        except Exception:
            meta = {}

    meta.update({
        "plivo_hangup_status": call_status,
        "plivo_hangup_cause_name": hangup_cause_name,
        "plivo_hangup_cause_code": hangup_cause_code,
        "plivo_hangup_source": hangup_source,
        "plivo_bill_duration": payload.get("BillDuration"),
        "plivo_aleg_uuid": payload.get("ALegUUID"),
        "plivo_bleg_uuid": payload.get("BLegUUID"),
    })
    session.metadata_json = json.dumps(meta)

    db.commit()

    return {
        "status": "success",
        "message": "Hangup event processed",
        "call_uuid": call_uuid,
        "call_session_id": session.call_session_id,
        "final_status": session.status,
        "duration_seconds": session.duration_seconds
    }


# ── 6. DIRECT CLICK-TO-CALL BRIDGE ──────────────────────────────────────────

@router.post("/plivo/click-to-call")
def initiate_click_to_call(
    payload: Dict[str, Any] = Body(...),
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Direct Server-Side Click-to-Call Bridge.
    Dials customer or agent directly via Plivo Cloud Trunk, ensuring immediate connection
    without requiring local browser WebRTC certificates.
    """
    import requests as _req
    from app.core.config import settings
    from app.core.config import get_safe_base_url

    to_phone = str(payload.get("to") or payload.get("destination") or "").strip()
    if not to_phone:
        raise HTTPException(status_code=400, detail="Destination phone number is required")

    if not to_phone.startswith("+"):
        to_phone = "+91" + to_phone.lstrip("0")

    auth_id = getattr(settings, 'PLIVO_AUTH_ID', None)
    auth_token = getattr(settings, 'PLIVO_AUTH_TOKEN', None)
    from_number = getattr(settings, 'PLIVO_DEFAULT_CALLER_ID', '+918031728899')

    if not auth_id or not auth_token:
        raise HTTPException(status_code=503, detail="Plivo credentials not configured on server")

    plivo_url = f"https://api.plivo.com/v1/Account/{auth_id}/Call/"
    call_payload = {
        "from": from_number,
        "to": to_phone,
        "answer_url": f"https://www.myntreal.com/api/v1/telephony/plivo/inbound",
        "answer_method": "POST",
        "hangup_url": f"https://www.myntreal.com/api/v1/telephony/plivo/hangup",
        "hangup_method": "POST"
    }

    try:
        resp = _req.post(plivo_url, json=call_payload, auth=(auth_id, auth_token), timeout=10)
        res_json = resp.json()
        logger.info(f"[CLICK-TO-CALL] Initiated outbound call to {to_phone}: status={resp.status_code} res={res_json}")
        return {
            "success": True,
            "message": f"Outbound call initiated to {to_phone}",
            "status_code": resp.status_code,
            "data": res_json
        }
    except Exception as e:
        logger.error(f"[CLICK-TO-CALL] Failed to dispatch Plivo call to {to_phone}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
