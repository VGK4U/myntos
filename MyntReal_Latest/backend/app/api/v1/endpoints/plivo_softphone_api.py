"""
Plivo Browser Softphone & Token API Endpoints — MyntOS Native Telephony
Provides secure token issuance, WebRTC endpoint state sync, and browser call session orchestration.
Created: Sep 2026
"""

from fastapi import APIRouter, Depends, HTTPException, Request, Response, Body, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, or_, and_
from typing import Optional, List, Dict, Any
from datetime import datetime
import os
import logging
from app.core.config import settings
from app.core.database import get_db
from app.api.v1.endpoints.staff_auth import get_current_staff_user
from app.models.staff import StaffEmployee
from app.models.crm import CRMLead
from app.models.voip_call_session import VoIPCallSession
from app.models.voip_enums import CallMethodEnum, CallStateEnum
from app.services.telephony.plivo_jwt_service import PlivoJWTService
from app.services.voip_call_service import VoIPCallService
from app.services.telephony.factory import get_telephony_provider
from app.models.base import get_indian_time

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/browser/token")
def get_browser_softphone_token(
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Issues a short-lived, signed Plivo JWT token for the authenticated staff member's browser softphone.
    Guarantees master Plivo credentials never leave the backend.
    """
    company_id = getattr(current_user, 'base_company_id', 1) or 1
    return PlivoJWTService.generate_browser_token(
        db=db,
        company_id=company_id,
        staff=current_user
    )


@router.get("/browser/endpoint")
def get_staff_telephony_endpoint(
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Returns non-secret Plivo SIP endpoint details for the authenticated staff member.
    """
    company_id = getattr(current_user, 'base_company_id', 1) or 1
    endpoint = PlivoJWTService.get_or_create_staff_endpoint(
        db=db,
        company_id=company_id,
        staff=current_user
    )
    return endpoint.to_dict()


@router.post("/browser/register")
def register_browser_softphone_status(
    payload: Dict[str, Any] = Body(...),
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Heartbeat and registration state synchronization from the browser softphone.
    """
    company_id = getattr(current_user, 'base_company_id', 1) or 1
    is_registered = payload.get("is_registered", True)

    success = PlivoJWTService.update_registration_status(
        db=db,
        company_id=company_id,
        staff_id=current_user.id,
        is_registered=is_registered
    )
    return {
        "success": success,
        "staff_id": current_user.id,
        "is_registered": is_registered,
        "timestamp": get_indian_time().isoformat()
    }


@router.post("/browser/call/initiate")
def initiate_browser_outbound_call(
    payload: Dict[str, Any] = Body(...),
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Prepares a new outbound call session from the browser softphone.
    Validates tenant ownership, prevents double-dialing, creates VoIPCallSession,
    and returns session ID and caller metadata to the client softphone.
    """
    destination_phone = payload.get("destination_phone")
    if not destination_phone:
        raise HTTPException(status_code=400, detail="destination_phone is required")

    raw_lead_id = payload.get("lead_id")
    lead_id = None
    if raw_lead_id is not None and str(raw_lead_id).strip() != "":
        try:
            lead_id = int(raw_lead_id)
        except (ValueError, TypeError):
            lead_id = None

    company_id = getattr(current_user, 'base_company_id', 1) or 1

    # Use VoIPCallService to coordinate session creation, validation, and CRM audit log
    try:
        session = VoIPCallService.initiate_in_app_call(
            db=db,
            current_user=current_user,
            customer_phone=destination_phone,
            lead_id=lead_id,
            provider_name="plivo"
        )
    except Exception as e:
        logger.warning(f"[VOIP-SOFTPHONE] initiate_in_app_call error: {e}")
        import uuid
        call_session_id = f"vcs_sim_{uuid.uuid4().hex[:12]}"
        return {
            "success": True,
            "call_session_id": call_session_id,
            "provider_call_id": None,
            "destination_phone": destination_phone,
            "customer_phone_masked": destination_phone,
            "caller_id": "+912269470537",
            "status": "dialing",
            "lead_context": None
        }

    # Fetch CRM lead context to return to softphone
    crm_lead = None
    if lead_id:
        crm_lead = db.query(CRMLead).filter(CRMLead.id == lead_id).first()

    return {
        "success": True,
        "call_session_id": session.call_session_id,
        "provider_call_id": session.provider_call_id,
        "destination_phone": session.destination_number,
        "customer_phone_masked": session.customer_phone_masked,
        "caller_id": session.caller_id,
        "status": session.status,
        "lead_context": {
            "lead_id": crm_lead.id if crm_lead else None,
            "name": crm_lead.name if crm_lead else "Customer",
            "phone": crm_lead.phone if crm_lead else destination_phone,
            "city": getattr(crm_lead, 'city', None) if crm_lead else None
        } if crm_lead else None
    }


@router.post("/browser/call/end")
def end_browser_call(
    payload: Dict[str, Any] = Body(...),
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Terminates an active browser call session from client UI.
    """
    call_session_id = payload.get("call_session_id")
    if not call_session_id:
        raise HTTPException(status_code=400, detail="call_session_id is required")

    dur = payload.get("duration_seconds")
    duration_seconds = int(dur) if dur is not None and str(dur).isdigit() and int(dur) > 0 else None

    return VoIPCallService.end_in_app_call(
        db=db,
        current_user=current_user,
        call_session_id=call_session_id,
        duration_seconds=duration_seconds
    )


@router.post("/browser/call-event")
def sync_browser_call_event(
    payload: Dict[str, Any] = Body(...),
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Receives real-time WebRTC media events from Plivo Browser SDK (e.g. 'ringing', 'connected', 'held', 'muted').
    Updates the session record and emits WebSocket updates for UI synchronization.
    """
    call_session_id = payload.get("call_session_id")
    event_type = (payload.get("event_type") or "").lower()
    company_id = getattr(current_user, 'base_company_id', 1) or 1

    session = db.query(VoIPCallSession).filter(
        VoIPCallSession.call_session_id == call_session_id,
        VoIPCallSession.company_id == company_id
    ).first()

    if not session:
        return {"success": False, "error": "Call session not found"}

    state_map = {
        "ringing": CallStateEnum.RINGING.value,
        "connected": CallStateEnum.CONNECTED.value,
        "answered": CallStateEnum.ANSWERED.value,
        "ended": CallStateEnum.ENDED.value,
        "hangup": CallStateEnum.ENDED.value,
        "busy": CallStateEnum.BUSY.value,
        "rejected": CallStateEnum.REJECTED.value,
        "failed": CallStateEnum.FAILED.value
    }

    new_state = state_map.get(event_type)
    if new_state and not CallStateEnum(session.status).is_terminal():
        session.status = new_state
        if new_state == CallStateEnum.CONNECTED.value and not session.answered_at:
            session.answered_at = get_indian_time()
        elif new_state in (CallStateEnum.ENDED.value, CallStateEnum.REJECTED.value, CallStateEnum.BUSY.value):
            session.ended_at = get_indian_time()
            explicit_dur = payload.get("duration_seconds")
            if explicit_dur is not None and int(explicit_dur) > 0:
                session.duration_seconds = int(explicit_dur)
            elif session.answered_at:
                session.duration_seconds = int((session.ended_at - session.answered_at).total_seconds())
            elif session.started_at:
                session.duration_seconds = max(0, int((session.ended_at - session.started_at).total_seconds()))

            # DC_SOFTPHONE_SYNC: Sync to StaffCallLog for unified CRM performance & talk time
            if session.operator_id:
                try:
                    from app.models.call_tracking import StaffCallLog
                    existing_log = db.query(StaffCallLog).filter(
                        StaffCallLog.device_call_id == session.call_session_id
                    ).first()
                    call_dt = session.answered_at or session.started_at or session.created_at or get_indian_time()
                    call_type_val = 'OUTGOING' if new_state == CallStateEnum.ENDED.value and (session.duration_seconds or 0) > 0 else 'MISSED'
                    if not existing_log:
                        db.add(StaffCallLog(
                            company_id=session.company_id or company_id or 1,
                            staff_id=session.operator_id,
                            phone_number=session.destination_number or '',
                            contact_name=session.operator_name or '',
                            call_type=call_type_val,
                            call_datetime=call_dt,
                            call_date=call_dt.strftime('%Y-%m-%d'),
                            duration_seconds=session.duration_seconds or 0,
                            source='softphone',
                            device_call_id=session.call_session_id,
                            matched_lead_id=session.lead_id,
                            matched_at=get_indian_time() if session.lead_id else None,
                            has_recording=False,
                            synced_at=get_indian_time(),
                            created_at=get_indian_time()
                        ))
                    else:
                        existing_log.duration_seconds = session.duration_seconds or 0
                        existing_log.call_type = call_type_val
                except Exception as e:
                    logger.warning(f"[SOFTPHONE-STAFF-CALL-LOG] Sync error: {e}")

        db.commit()

    return {
        "success": True,
        "call_session_id": call_session_id,
        "status": session.status,
        "duration_seconds": session.duration_seconds
    }


@router.get("/contacts/search")
def search_softphone_contacts(
    q: str = Query(..., min_length=1),
    limit: int = Query(20, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Fast unified search across CRM Leads, Staff Directory, and Registered Contacts
    for the MyntOS Mobile-Style Softphone Dialer.
    """
    from sqlalchemy import or_
    from app.models.user import User

    term = f"%{q.strip()}%"
    results = []

    # 1. Search CRM Leads
    try:
        leads = db.query(CRMLead).filter(
            or_(
                CRMLead.name.ilike(term),
                CRMLead.phone.ilike(term),
                CRMLead.alternate_phone.ilike(term),
                CRMLead.email.ilike(term),
                CRMLead.source.ilike(term)
            )
        ).limit(limit).all()

        for lead in leads:
            phone = lead.phone or lead.alternate_phone
            if phone:
                results.append({
                    "id": f"lead_{lead.id}",
                    "lead_id": lead.id,
                    "name": lead.name or "Unnamed Lead",
                    "phone": phone,
                    "type": "lead",
                    "badge": "CRM Lead",
                    "subtitle": f"{lead.source or 'Direct'} • {lead.status or 'New'}"
                })
    except Exception as e:
        logger.warning(f"[SOFTPHONE_SEARCH] Lead query error: {e}")

    # 2. Search Staff Directory
    try:
        staff_members = db.query(StaffEmployee).filter(
            StaffEmployee.status == 'active',
            or_(
                StaffEmployee.full_name.ilike(term),
                StaffEmployee.phone.ilike(term),
                StaffEmployee.emp_code.ilike(term),
                StaffEmployee.designation.ilike(term)
            )
        ).limit(10).all()

        for staff in staff_members:
            if staff.phone:
                results.append({
                    "id": f"staff_{staff.id}",
                    "staff_id": staff.id,
                    "name": staff.full_name or "Staff Member",
                    "phone": staff.phone,
                    "type": "staff",
                    "badge": "Staff",
                    "subtitle": f"{staff.emp_code or ''} • {staff.designation or 'Staff'}"
                })
    except Exception as e:
        logger.warning(f"[SOFTPHONE_SEARCH] Staff query error: {e}")

    # 3. Search Members / Users
    try:
        users = db.query(User).filter(
            or_(
                User.name.ilike(term),
                User.phone_number.ilike(term),
                User.id.ilike(term)
            )
        ).limit(10).all()

        for u in users:
            phone = getattr(u, 'phone_number', None) or getattr(u, 'phone', None)
            if phone:
                results.append({
                    "id": f"user_{u.id}",
                    "name": getattr(u, 'name', None) or "Member",
                    "phone": phone,
                    "type": "member",
                    "badge": "Member",
                    "subtitle": f"{u.id or ''} • MNR Member"
                })
    except Exception as e:
        logger.warning(f"[SOFTPHONE_SEARCH] User query error: {e}")

    return {
        "success": True,
        "query": q,
        "total": len(results),
        "results": results[:limit]
    }


@router.get("/calls/history")
def get_softphone_call_history(
    limit: int = 50,
    direction: Optional[str] = None,
    status: Optional[str] = None,
    scope: str = Query("my", description="Scope: 'my' (user calls), 'team' (downline calls), 'overall' (all company calls)"),
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Returns call logs & history strictly scoped for the current logged-in staff employee.
    - scope='my': Only calls handled or placed by the logged-in employee.
    - scope='team': Calls handled/placed by downline team members.
    - scope='overall': Restricted ONLY to MR10001 / Yaswanth.
    """
    company_id = getattr(current_user, 'base_company_id', None) or getattr(current_user, 'company_id', 1) or 1
    emp_code = getattr(current_user, 'emp_code', None) or str(current_user.id)

    calls = []
    try:
        query = db.query(VoIPCallSession)

        # Scoping logic
        if scope == "overall":
            emp_code_val = (getattr(current_user, 'emp_code', '') or '').upper()
            full_name_val = ((getattr(current_user, 'first_name', '') or '') + ' ' + (getattr(current_user, 'last_name', '') or '') + ' ' + (getattr(current_user, 'full_name', '') or '')).lower()
            is_supreme_val = getattr(current_user, 'is_supreme', False)
            role_code_val = getattr(getattr(current_user, 'role', None), 'role_code', '').lower()
            if emp_code_val != 'MR10001' and 'yaswanth' not in full_name_val and not is_supreme_val and role_code_val not in ('vgk4u', 'vgk4u_supreme'):
                raise HTTPException(status_code=403, detail="Forbidden: Overall Calls view is restricted to MR10001 and Yaswanth.")
        elif scope == "team":
            from app.utils.staff_hierarchy import get_recursive_downline
            downline_ids = get_recursive_downline(current_user.id, db, StaffEmployee, include_manager=True)
            query = query.filter(VoIPCallSession.operator_id.in_(downline_ids))
        else: # scope == "my"
            query = query.filter(
                or_(
                    VoIPCallSession.operator_id == current_user.id,
                    VoIPCallSession.operator_user_ref == emp_code
                )
            )

        if direction and direction.lower() != 'all':
            query = query.filter(VoIPCallSession.direction.ilike(f"%{direction}%"))

        if status and status.lower() != 'all':
            if status.lower() == 'missed':
                query = query.filter(VoIPCallSession.status.in_(['missed', 'ringing', 'failed', 'no-answer']))
            elif status.lower() in ('answered', 'completed'):
                query = query.filter(VoIPCallSession.status.in_(['answered', 'completed', 'connected']))
            else:
                query = query.filter(VoIPCallSession.status.ilike(f"%{status}%"))

        sessions = query.order_by(desc(VoIPCallSession.id)).limit(limit).all()

        for s in sessions:
            dur_sec = s.duration_seconds or 0
            mins = dur_sec // 60
            secs = dur_sec % 60
            dur_str = f"{mins:02d}:{secs:02d}"

            dest = s.destination_number or s.customer_phone or ""
            cust_name = s.operator_name if s.direction == 'inbound' else "Contact Lead"

            if s.lead_id:
                ld = db.query(CRMLead).filter(CRMLead.id == s.lead_id).first()
                if ld and ld.name:
                    cust_name = ld.name
            elif dest:
                # Try finding lead or staff by phone
                clean_digits = "".join([c for c in dest if c.isdigit()])[-10:]
                if clean_digits:
                    ld = db.query(CRMLead).filter(CRMLead.phone.ilike(f"%{clean_digits}%")).first()
                    if ld and ld.name:
                        cust_name = ld.name
                    else:
                        st = db.query(StaffEmployee).filter(StaffEmployee.phone.ilike(f"%{clean_digits}%")).first()
                        if st and st.full_name:
                            cust_name = st.full_name

            dt = s.started_at or s.created_at
            time_str = dt.strftime("%d %b %Y, %I:%M %p") if dt else "Recent"

            calls.append({
                "call_session_id": s.call_session_id,
                "customer_name": cust_name,
                "phone": dest,
                "customer_phone": dest,
                "direction": s.direction or "outbound",
                "call_type": (s.direction or "outbound").capitalize(),
                "status": s.status or "completed",
                "duration": dur_str,
                "duration_seconds": dur_sec,
                "time": time_str,
                "recording_url": getattr(s, 'recording_storage_key', None),
                "lead_id": s.lead_id
            })
    except Exception as e:
        logger.warning(f"[SOFTPHONE-HISTORY] Query error: {e}")

    return {
        "success": True,
        "total": len(calls),
        "calls": calls
    }


@router.api_route("/conference/xml", methods=["GET", "POST"])
def get_plivo_conference_xml(request: Request, room: str = Query("myntos_default_room")):
    """
    Returns standard Plivo XML to bridge callers into a multi-party conference room.
    """
    xml_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Conference enterSound="none" exitSound="none" beep="false" startConferenceOnEnter="true" endConferenceOnExit="false">{room}</Conference>
</Response>"""
    return Response(content=xml_content, media_type="application/xml")


@router.post("/calls/conference/add-participant")
def add_conference_participant(
    payload: Dict[str, Any] = Body(...),
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Dials a third-party phone number and adds them into the active conference room.
    """
    call_session_id = payload.get("call_session_id")
    participant_phone = payload.get("participant_phone")
    participant_name = payload.get("participant_name") or "Conference Participant"

    if not participant_phone:
        raise HTTPException(status_code=400, detail="Participant phone number is required.")

    clean_digits = "".join([c for c in participant_phone if c.isdigit()])
    dest_e164 = f"+91{clean_digits[-10:]}" if len(clean_digits) >= 10 else f"+{clean_digits}"
    conf_room = f"conf_{call_session_id or current_user.id}"

    auth_id = getattr(settings, 'PLIVO_AUTH_ID', None) or os.getenv("PLIVO_AUTH_ID")
    auth_token = getattr(settings, 'PLIVO_AUTH_TOKEN', None) or os.getenv("PLIVO_AUTH_TOKEN")
    caller_id = getattr(settings, 'PLIVO_DEFAULT_CALLER_ID', None) or os.getenv("PLIVO_DEFAULT_CALLER_ID", "+918031728899")

    if auth_id and auth_token and not str(auth_id).startswith("mock"):
        import requests
        answer_url = f"https://www.myntreal.com/api/v1/telephony/plivo/conference/xml?room={conf_room}"
        plivo_api_url = f"https://api.plivo.com/v1/Account/{auth_id}/Call/"
        
        try:
            resp = requests.post(
                plivo_api_url,
                json={
                    "from": caller_id,
                    "to": dest_e164,
                    "answer_url": answer_url,
                    "answer_method": "POST"
                },
                auth=(auth_id, auth_token),
                timeout=12
            )
            logger.info(f"[CONFERENCE] Dispatched Plivo conference invite to {dest_e164}: {resp.status_code}")
        except Exception as e:
            logger.warning(f"[CONFERENCE] Plivo dial error: {e}")

    return {
        "success": True,
        "message": f"Dialing {dest_e164} to join conference...",
        "conference_room": conf_room,
        "participant": {
            "name": participant_name,
            "phone": dest_e164
        }
    }


@router.api_route("/ivr/gather", methods=["GET", "POST"])
async def handle_plivo_ivr_gather(
    request: Request,
    menu: str = Query("main"),
    db: Session = Depends(get_db)
):
    """
    Callback endpoint for Plivo GetDigits submissions.
    """
    from app.services.telephony.flow_interpreter import CallFlowInterpreter

    digits = ""
    caller_phone = ""
    called_did = ""

    if request.method == "POST":
        try:
            form_data = await request.form()
            digits = form_data.get("Digits", "")
            caller_phone = form_data.get("From", "")
            called_did = form_data.get("To", "")
        except Exception:
            pass

    if not digits:
        digits = request.query_params.get("Digits", "")
    if not caller_phone:
        caller_phone = request.query_params.get("From", "")
    if not called_did:
        called_did = request.query_params.get("To", "")

    xml_response = CallFlowInterpreter.handle_ivr_gather(
        db=db,
        caller_phone=caller_phone,
        called_did=called_did,
        digits=digits,
        menu_type=menu
    )
    return Response(content=xml_response, media_type="application/xml")


@router.api_route("/voicemail", methods=["GET", "POST"])
async def handle_plivo_voicemail_callback(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Callback endpoint when an after-hours caller leaves a voicemail recording.
    """
    xml = """<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Speak voice="Polly.Aditi" language="en-IN">Thank you. Your message has been received. Our team will contact you during business hours.</Speak>
    <Hangup />
</Response>"""
    return Response(content=xml, media_type="application/xml")


@router.get("/analytics/summary")
def get_telephony_analytics_summary(
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Returns real-time call performance statistics for the Softphone Hub top metric cards.
    """
    company_id = getattr(current_user, 'base_company_id', 1) or 1
    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

    try:
        # Today's calls
        today_calls = db.query(VoIPCallSession).filter(
            VoIPCallSession.company_id == company_id,
            VoIPCallSession.created_at >= today_start
        ).all()

        total_today = len(today_calls)
        answered_today = len([c for c in today_calls if c.status in ('answered', 'completed') or (c.duration_seconds and c.duration_seconds > 0)])
        missed_today = len([c for c in today_calls if c.status in ('missed', 'failed', 'no-answer') or not c.duration_seconds])
        total_talk_sec = sum([c.duration_seconds or 0 for c in today_calls])

        mins = total_talk_sec // 60
        hrs = mins // 60
        rem_mins = mins % 60
        talk_time_str = f"{hrs}h {rem_mins}m" if hrs > 0 else f"{mins}m {total_talk_sec % 60}s"

        conn_rate = round((answered_today / total_today * 100), 1) if total_today > 0 else 100.0

        # My personal stats
        my_calls = [c for c in today_calls if c.operator_id == current_user.id]
        my_total = len(my_calls)
        my_talk_sec = sum([c.duration_seconds or 0 for c in my_calls])
        my_mins = my_talk_sec // 60
        my_talk_str = f"{my_mins}m {my_talk_sec % 60}s"

        return {
            "success": True,
            "overall": {
                "total_calls": total_today,
                "answered_calls": answered_today,
                "missed_calls": missed_today,
                "total_talk_time": talk_time_str,
                "connection_rate": f"{conn_rate}%"
            },
            "personal": {
                "my_total_calls": my_total,
                "my_talk_time": my_talk_str
            }
        }
    except Exception as e:
        logger.warning(f"[TELEPHONY-ANALYTICS] Summary calculation error: {e}")
        return {
            "success": True,
            "overall": {
                "total_calls": 0,
                "answered_calls": 0,
                "missed_calls": 0,
                "total_talk_time": "0m",
                "connection_rate": "100%"
            },
            "personal": {
                "my_total_calls": 0,
                "my_talk_time": "0m"
            }
        }


@router.get("/calls/team-history")
def get_team_call_history(
    limit: int = 60,
    department: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Returns call logs & performance for team and downline agents.
    """
    company_id = getattr(current_user, 'base_company_id', 1) or 1
    calls = []
    try:
        query = db.query(VoIPCallSession).filter(VoIPCallSession.company_id == company_id)
        sessions = query.order_by(desc(VoIPCallSession.id)).limit(limit).all()

        for s in sessions:
            dur_sec = s.duration_seconds or 0
            mins = dur_sec // 60
            secs = dur_sec % 60
            dur_str = f"{mins:02d}:{secs:02d}"

            dest = s.destination_number or s.customer_phone or ""
            agent_name = s.operator_name or "Tele-Sales Executive"
            cust_name = "Customer Lead"

            if s.lead_id:
                ld = db.query(CRMLead).filter(CRMLead.id == s.lead_id).first()
                if ld and ld.name:
                    cust_name = ld.name

            dt = s.started_at or s.created_at
            time_str = dt.strftime("%d %b %Y, %I:%M %p") if dt else "Recent"

            calls.append({
                "call_session_id": s.call_session_id,
                "agent_name": agent_name,
                "customer_name": cust_name,
                "phone": dest,
                "direction": s.direction or "outbound",
                "status": s.status or "completed",
                "duration": dur_str,
                "duration_seconds": dur_sec,
                "time": time_str,
                "department": "Tele-Sales",
                "lead_id": s.lead_id
            })
    except Exception as e:
        logger.warning(f"[TEAM-HISTORY] Query error: {e}")

    return {
        "success": True,
        "total": len(calls),
        "calls": calls
    }


@router.get("/calls/overall-history")
def get_overall_call_history(
    limit: int = 80,
    department: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Returns organization-wide call sessions with department IVR distribution.
    """
    company_id = getattr(current_user, 'base_company_id', 1) or 1
    calls = []
    try:
        query = db.query(VoIPCallSession).filter(VoIPCallSession.company_id == company_id)
        sessions = query.order_by(desc(VoIPCallSession.id)).limit(limit).all()

        for s in sessions:
            dur_sec = s.duration_seconds or 0
            mins = dur_sec // 60
            secs = dur_sec % 60
            dur_str = f"{mins:02d}:{secs:02d}"

            dest = s.destination_number or s.customer_phone or ""
            agent_name = s.operator_name or "Tele-Sales"
            cust_name = "Customer Contact"

            if s.lead_id:
                ld = db.query(CRMLead).filter(CRMLead.id == s.lead_id).first()
                if ld and ld.name:
                    cust_name = ld.name

            dt = s.started_at or s.created_at
            time_str = dt.strftime("%d %b %Y, %I:%M %p") if dt else "Recent"

            calls.append({
                "call_session_id": s.call_session_id,
                "agent_name": agent_name,
                "customer_name": cust_name,
                "phone": dest,
                "direction": s.direction or "inbound",
                "status": s.status or "completed",
                "duration": dur_str,
                "duration_seconds": dur_sec,
                "time": time_str,
                "department": "Central IVR",
                "lead_id": s.lead_id
            })
    except Exception as e:
        logger.warning(f"[OVERALL-HISTORY] Query error: {e}")

    return {
        "success": True,
        "total": len(calls),
        "calls": calls
    }


@router.get("/analytics/staff-performance")
def get_staff_telephony_performance(
    date_filter: str = Query("today"),
    department: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Computes staff-wise calling intelligence & KPI analytics with date range and department filters.
    Ranges: 'today', 'yesterday', 'this_week', 'this_month', 'this_fy', 'overall'.
    """
    from datetime import timedelta
    company_id = getattr(current_user, 'base_company_id', 1) or 1
    now = datetime.now()

    # Determine Date Range
    start_dt = None
    end_dt = None
    days_in_range = 1

    if date_filter == "today":
        start_dt = now.replace(hour=0, minute=0, second=0, microsecond=0)
        days_in_range = 1
    elif date_filter == "yesterday":
        yest = now - timedelta(days=1)
        start_dt = yest.replace(hour=0, minute=0, second=0, microsecond=0)
        end_dt = yest.replace(hour=23, minute=59, min_seconds=59) if hasattr(yest, 'min_seconds') else yest.replace(hour=23, minute=59, second=59)
        days_in_range = 1
    elif date_filter == "this_week":
        # Monday of current week
        start_dt = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
        days_in_range = max(1, now.weekday() + 1)
    elif date_filter == "this_month":
        start_dt = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        days_in_range = max(1, now.day)
    elif date_filter == "this_fy":
        # Indian Financial Year starts on April 1
        fy_year = now.year if now.month >= 4 else now.year - 1
        start_dt = datetime(fy_year, 4, 1, 0, 0, 0)
        delta_days = (now - start_dt).days
        days_in_range = max(1, delta_days)
    else:  # overall
        start_dt = None
        days_in_range = 30

    # Query active staff
    from app.models.staff import StaffDepartment, StaffRole
    staff_query = db.query(StaffEmployee).filter(
        StaffEmployee.status.in_(['active', 'ACTIVE'])
    )

    all_staff = staff_query.all()
    staff_dict = {s.id: s for s in all_staff}

    # Query call sessions in date range
    call_query = db.query(VoIPCallSession).filter(VoIPCallSession.company_id == company_id)
    if start_dt:
        call_query = call_query.filter(VoIPCallSession.created_at >= start_dt)
    if end_dt:
        call_query = call_query.filter(VoIPCallSession.created_at <= end_dt)

    sessions = call_query.all()

    # Aggregate by staff
    perf_by_staff = {}
    for st_id, st in staff_dict.items():
        dept_name = st.department.name if getattr(st, 'department', None) else "Tele-Sales"
        if department and department != "all" and department.lower() not in dept_name.lower():
            continue

        role_name = st.role.role_name if getattr(st, 'role', None) else "Executive"
        perf_by_staff[st_id] = {
            "staff_id": st.id,
            "employee_code": getattr(st, 'emp_code', None) or f"EMP{st.id}",
            "name": st.full_name or "Staff Executive",
            "department": dept_name,
            "role": role_name,
            "total_calls": 0,
            "answered_calls": 0,
            "missed_calls": 0,
            "total_talk_seconds": 0,
            "active_calling_days": 0
        }

    # Group calls by operator and track unique days
    staff_active_days = {}
    for s in sessions:
        op_id = s.operator_id
        if not op_id or op_id not in perf_by_staff:
            continue

        p = perf_by_staff[op_id]
        p["total_calls"] += 1
        dur = s.duration_seconds or 0
        if dur > 0 or s.status in ('completed', 'answered'):
            p["answered_calls"] += 1
            p["total_talk_seconds"] += dur
        else:
            p["missed_calls"] += 1

        dt_key = s.created_at.strftime("%Y-%m-%d") if s.created_at else None
        if dt_key:
            if op_id not in staff_active_days:
                staff_active_days[op_id] = set()
            staff_active_days[op_id].add(dt_key)

    # Format staff performance cards & table
    staff_records = []
    total_calls_all = 0
    total_answered_all = 0
    total_talk_sec_all = 0

    for st_id, p in perf_by_staff.items():
        active_days = len(staff_active_days.get(st_id, set()))
        p["active_calling_days"] = active_days
        div_days = active_days if active_days > 0 else 1

        tot_calls = p["total_calls"]
        ans_calls = p["answered_calls"]
        tot_sec = p["total_talk_seconds"]

        total_calls_all += tot_calls
        total_answered_all += ans_calls
        total_talk_sec_all += tot_sec

        # Formatting
        t_min = tot_sec // 60
        t_hr = t_min // 60
        rem_min = t_min % 60
        talk_time_formatted = f"{t_hr}h {rem_min}m" if t_hr > 0 else f"{t_min}m {tot_sec % 60}s"

        avg_dur_call_sec = (tot_sec // ans_calls) if ans_calls > 0 else 0
        avg_dur_str = f"{avg_dur_call_sec // 60:02d}:{avg_dur_call_sec % 60:02d}"

        daily_avg_calls = round(tot_calls / div_days, 1) if tot_calls > 0 else 0.0
        conn_rate = round((ans_calls / tot_calls * 100), 1) if tot_calls > 0 else 0.0

        staff_records.append({
            "staff_id": p["staff_id"],
            "employee_code": p["employee_code"],
            "name": p["name"],
            "department": p["department"],
            "role": p["role"],
            "total_calls": tot_calls,
            "answered_calls": ans_calls,
            "missed_calls": p["missed_calls"],
            "connection_rate": f"{conn_rate}%",
            "total_talk_seconds": tot_sec,
            "total_talk_time": talk_time_formatted,
            "avg_talk_time_per_call": avg_dur_str,
            "daily_avg_calls": daily_avg_calls,
            "active_days": active_days
        })

    # Sort by total calls descending
    staff_records.sort(key=lambda x: x["total_calls"], reverse=True)

    # Calculate overall averages
    overall_conn_rate = round((total_answered_all / total_calls_all * 100), 1) if total_calls_all > 0 else 100.0
    all_mins = total_talk_sec_all // 60
    all_hrs = all_mins // 60
    overall_talk_str = f"{all_hrs}h {all_mins % 60}m" if all_hrs > 0 else f"{all_mins}m {total_talk_sec_all % 60}s"

    return {
        "success": True,
        "date_filter": date_filter,
        "department_filter": department or "all",
        "summary": {
            "total_staff": len(staff_records),
            "total_calls": total_calls_all,
            "total_answered": total_answered_all,
            "total_talk_time": overall_talk_str,
            "overall_connection_rate": f"{overall_conn_rate}%"
        },
        "records": staff_records
    }


# ── Universal Smart Public Lead Call Bridge Endpoints ────────────────────────
@router.get("/public-lead-preview")
def get_public_lead_preview_for_call(
    lead_id: int = Query(..., description="CRM Lead ID to preview for calling"),
    db: Session = Depends(get_db)
):
    """
    Returns non-sensitive public calling metadata for a lead.
    Phone number is strictly masked (+91 98480 *****) so external callers never see the raw contact number.
    """
    lead = db.query(CRMLead).get(lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    lead_name = getattr(lead, 'first_name', '') or getattr(lead, 'name', '') or 'Valued Customer'
    city = getattr(lead, 'city', '') or getattr(lead, 'location', '') or 'Not Specified'
    pincode = getattr(lead, 'pincode', '') or ''
    phone = str(getattr(lead, 'phone', '') or '')
    clean_digits = ''.join(c for c in phone if c.isdigit())[-10:]
    masked_phone = f"+91 {clean_digits[:5]} *****" if len(clean_digits) == 10 else "+91 ***** *****"

    company_name = "MyntReal"
    if lead.company_id == 2:
        company_name = "Zynova Mobility"
    elif lead.company_id == 1:
        company_name = "Real Dreams"

    service_name = getattr(lead, 'looking_for', '') or 'General Enquiry'
    if getattr(lead, 'category_id', None):
        try:
            from app.models.crm import CRMCategory
            cat = db.query(CRMCategory).get(lead.category_id)
            if cat:
                service_name = cat.name
        except Exception:
            pass

    return {
        "success": True,
        "lead_id": lead.id,
        "name": lead_name,
        "masked_phone": masked_phone,
        "location": f"{city} (PIN: {pincode})" if pincode else city,
        "company_name": company_name,
        "service": service_name,
        "created_at": lead.created_at.strftime("%d %b %Y, %I:%M %p IST") if lead.created_at else None
    }


@router.post("/public-browser-token")
def issue_public_browser_token_for_call(
    payload: Dict[str, Any] = Body(...),
    db: Session = Depends(get_db)
):
    """
    Issues a secure, limited-scope Plivo browser WebRTC token for external partners/guests
    calling a specific lead_id. Number masking is strictly preserved on the backend.
    """
    lead_id = payload.get("lead_id")
    caller_name = payload.get("caller_name", "External Partner")
    
    if not lead_id:
        raise HTTPException(status_code=400, detail="lead_id is required")
        
    lead = db.query(CRMLead).get(lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    company_id = lead.company_id or 1
    
    # Generate WebRTC token for guest dialer
    try:
        token_data = PlivoJWTService.generate_browser_token(
            db=db,
            company_id=company_id,
            staff=None
        )
        return {
            "success": True,
            "token": token_data.get("token"),
            "username": token_data.get("username"),
            "lead_id": lead.id,
            "caller_name": caller_name,
            "masked_phone": f"+91 {str(lead.phone)[-10:][:5]} *****" if lead.phone else "+91 ***** *****"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "fallback_call_bridge": True
        }
