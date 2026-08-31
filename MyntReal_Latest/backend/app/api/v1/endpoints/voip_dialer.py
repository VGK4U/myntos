"""
VoIP In-App PSTN Calling & Centralized Recording Endpoints
FastAPI routes for initiating calls, querying status, terminating sessions, secure playback, and processing provider webhooks.
Created: Aug 2026
"""

from typing import Optional
from fastapi import APIRouter, Depends, Body, Header, Request, Query, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.v1.endpoints.crm_dialer import get_current_user_hybrid
from app.services.voip_call_service import VoIPCallService
from app.models.voip_call_session import VoIPCallSession

router = APIRouter()


class InAppCallRequest(BaseModel):
    customer_phone: str = Field(..., description="Customer destination phone number (e.g. 9703118501 or +919703118501)")
    lead_id: Optional[int] = Field(None, description="Optional CRM Lead ID to associate with this call")
    provider: Optional[str] = Field(None, description="Optional telephony provider override (defaults to server config)")


class InAppCallEndRequest(BaseModel):
    reason: Optional[str] = Field(None, description="Optional termination reason (e.g. operator_hangup)")


@router.post("/crm/dialer/in-app-call")
async def initiate_in_app_pstn_call(
    payload: InAppCallRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_hybrid)
):
    """
    DC_VOIP_001: Initiate an authoritative In-App PSTN Outbound Call.
    Presents the dedicated MyntReal business outbound calling number to the customer.
    """
    session = VoIPCallService.initiate_in_app_call(
        db=db,
        current_user=current_user,
        customer_phone=payload.customer_phone,
        lead_id=payload.lead_id,
        provider_name=payload.provider
    )

    client_token_obj = None
    if session.client_token:
        try:
            import json
            client_token_obj = json.loads(session.client_token)
        except Exception:
            client_token_obj = None

    return {
        "success": True,
        "call_session_id": session.call_session_id,
        "status": session.status,
        "call_method": session.call_method,
        "caller_id": session.caller_id,
        "customer_phone_masked": session.customer_phone_masked,
        "provider": session.provider,
        "client_token": client_token_obj,
        "started_at": session.started_at.isoformat() if session.started_at else None
    }


@router.post("/crm/dialer/in-app-call/{call_session_id}/end")
async def end_in_app_pstn_call(
    call_session_id: str,
    payload: Optional[InAppCallEndRequest] = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_hybrid)
):
    """
    DC_VOIP_002: Request termination of an ongoing in-app call.
    """
    reason = payload.reason if payload else None
    session = VoIPCallService.end_in_app_call(
        db=db,
        current_user=current_user,
        call_session_id=call_session_id,
        reason=reason
    )
    return {
        "success": True,
        "call_session_id": session.call_session_id,
        "status": session.status,
        "duration_seconds": session.duration_seconds,
        "ended_at": session.ended_at.isoformat() if session.ended_at else None
    }


@router.get("/crm/dialer/in-app-call/{call_session_id}/status")
async def get_in_app_call_status(
    call_session_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_hybrid)
):
    """
    DC_VOIP_003: Query live status and recording availability of a call session.
    """
    session = db.query(VoIPCallSession).filter(
        VoIPCallSession.call_session_id == call_session_id
    ).first()

    if not session:
        raise HTTPException(status_code=404, detail="Call session not found")

    user_company_id = getattr(current_user, 'company_id', 1) or 1
    if session.company_id != user_company_id:
        raise HTTPException(status_code=403, detail="Unauthorized access to this call session")

    return {
        "success": True,
        "session": session.to_dict()
    }


@router.get("/crm/dialer/in-app-call/{call_session_id}/recording")
async def get_in_app_call_recording(
    call_session_id: str,
    expiration: int = Query(900, ge=60, le=3600, description="Signed URL validity in seconds (1-60 mins)"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_hybrid)
):
    """
    DC_VOIP_004: Generate short-lived signed S3 URL for private call recording playback.
    """
    return VoIPCallService.get_recording_signed_url(
        db=db,
        current_user=current_user,
        call_session_id=call_session_id,
        expiration=expiration
    )


@router.post("/crm/dialer/webhooks/telephony")
async def handle_telephony_webhook(
    request: Request,
    provider: Optional[str] = Query(None, description="Optional provider identifier"),
    db: Session = Depends(get_db)
):
    """
    DC_VOIP_005: Idempotent provider webhook listener for live call state and recording events.
    """
    headers = dict(request.headers)
    body = await request.body()
    query_params = dict(request.query_params)

    result = VoIPCallService.process_telephony_webhook(
        db=db,
        headers=headers,
        body=body,
        query_params=query_params,
        provider_name=provider
    )
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Webhook processing failed"))

    return result
