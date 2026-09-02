"""
Plivo Browser Softphone & Token API Endpoints — MyntOS Native Telephony
Provides secure token issuance, WebRTC endpoint state sync, and browser call session orchestration.
Created: Sep 2026
"""

from fastapi import APIRouter, Depends, HTTPException, Request, Response, Body, Query
from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Any
from datetime import datetime
import logging

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

    lead_id = payload.get("lead_id")
    company_id = getattr(current_user, 'base_company_id', 1) or 1

    # Use VoIPCallService to coordinate session creation, validation, and CRM audit log
    session = VoIPCallService.initiate_in_app_call(
        db=db,
        current_user=current_user,
        customer_phone=destination_phone,
        lead_id=lead_id,
        provider_name="plivo"
    )

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

    return VoIPCallService.end_in_app_call(
        db=db,
        current_user=current_user,
        call_session_id=call_session_id
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
            if session.answered_at:
                session.duration_seconds = int((session.ended_at - session.answered_at).total_seconds())

        db.commit()

    return {
        "success": True,
        "call_session_id": call_session_id,
        "status": session.status,
        "duration_seconds": session.duration_seconds
    }
