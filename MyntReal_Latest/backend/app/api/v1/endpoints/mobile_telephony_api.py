"""
Mobile Telephony & VoIP Push Notification API — MyntOS
Endpoints for device push token registration, revocation, incoming call rejection, and testing.
Created: Sep 2026
"""

import logging
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.staff import StaffEmployee
from app.api.v1.endpoints.staff_auth import get_current_staff_user
from app.services.telephony.mobile_push_service import MobilePushService, MobileCallNotifier

logger = logging.getLogger("mobile_telephony_api")

router = APIRouter()


class PushTokenRegisterRequest(BaseModel):
    device_id: str = Field(..., description="Unique device hardware UUID")
    platform: str = Field(..., description="'android' or 'ios'")
    push_token: str = Field(..., description="FCM device token or APNs VoIP hex token")
    token_type: Optional[str] = Field(None, description="'fcm_data' or 'apns_voip'")
    app_version: Optional[str] = Field(None, description="App build version e.g. 1.0.1")


class PushTokenRevokeRequest(BaseModel):
    device_id: str = Field(..., description="Device UUID to unregister")
    token_type: Optional[str] = Field(None, description="Optional token type to selectively revoke")


class CallRejectRequest(BaseModel):
    call_session_id: str = Field(..., description="VoIP call session ID")
    provider_call_id: Optional[str] = Field(None, description="Plivo CallUUID if known")
    reason: Optional[str] = Field("user_declined", description="Reason for rejection")


class TestIncomingCallRequest(BaseModel):
    caller_phone: Optional[str] = Field("+919876543210", description="Mock caller phone number")
    caller_name: Optional[str] = Field("Rajesh Sharma", description="Mock lead name")
    lead_id: Optional[int] = Field(101, description="Mock lead ID")
    category: Optional[str] = Field("Solar", description="Mock vertical category (Solar, EV B2B, Real Dreams, etc.)")
    lead_type: Optional[str] = Field("5kW Residential Rooftop", description="Mock lead requirement/type")
    city: Optional[str] = Field("Hyderabad", description="Mock lead location")
    lead_status: Optional[str] = Field("Interested", description="Mock lead status")
    deal_value: Optional[str] = Field("₹3,50,000", description="Mock deal value")


@router.post("/mobile/push-token")
def register_push_token(
    payload: PushTokenRegisterRequest,
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Registers or updates an FCM/APNs push token for the authenticated staff user's mobile device.
    Enforces tenant isolation and updates Plivo endpoint registration status.
    """
    company_id = getattr(current_user, "base_company_id", 1) or 1

    try:
        token_record = MobilePushService.register_device_token(
            db=db,
            company_id=company_id,
            staff_id=current_user.id,
            device_id=payload.device_id,
            platform=payload.platform,
            push_token=payload.push_token,
            token_type=payload.token_type,
            app_version=payload.app_version
        )
        return {
            "success": True,
            "message": "Push token registered successfully",
            "data": token_record.to_dict()
        }
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except PermissionError as pe:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(pe))
    except Exception as e:
        logger.error(f"[MOBILE-PUSH-API-ERROR] Registration failed: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to register push token")


@router.post("/mobile/push-token/revoke")
def revoke_push_token(
    payload: PushTokenRevokeRequest,
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Revokes the push token for a specific device (called upon logout).
    Prevents ringing a logged-out device.
    """
    company_id = getattr(current_user, "base_company_id", 1) or 1

    success = MobilePushService.revoke_device_token(
        db=db,
        company_id=company_id,
        staff_id=current_user.id,
        device_id=payload.device_id,
        token_type=payload.token_type
    )
    return {
        "success": success,
        "message": "Push token revoked successfully" if success else "No active token found for device"
    }


@router.post("/mobile/call/reject")
def reject_incoming_call(
    payload: CallRejectRequest,
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Receives user decline action from native incoming-call screen (Android or CallKit).
    Terminates the ringing notification on other devices and cleans up state.
    """
    company_id = getattr(current_user, "base_company_id", 1) or 1

    cancel_res = MobileCallNotifier.notify_call_cancelled(
        call_session_id=payload.call_session_id,
        provider_call_id=payload.provider_call_id,
        target_staff_ids=[current_user.id],
        company_id=company_id,
        reason=payload.reason or "user_declined",
        db=db
    )

    return {
        "success": True,
        "session_id": payload.call_session_id,
        "status": "rejected",
        "details": cancel_res
    }


@router.post("/mobile/test/incoming-call")
def test_incoming_call_dispatch(
    payload: TestIncomingCallRequest,
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Development & diagnostic endpoint to trigger a simulated incoming call push
    to the authenticated staff member's registered mobile device(s).
    """
    company_id = getattr(current_user, "base_company_id", 1) or 1
    import uuid

    mock_session_id = f"vcs_test_{uuid.uuid4().hex[:8]}"
    mock_call_uuid = f"mock_uuid_{uuid.uuid4().hex[:12]}"

    dispatch_res = MobileCallNotifier.notify_inbound_call(
        caller_phone=payload.caller_phone or "+919876543210",
        called_did="+918031728899",
        provider_call_id=mock_call_uuid,
        call_session_id=mock_session_id,
        target_staff_ids=[current_user.id],
        company_id=company_id,
        lead_name=payload.caller_name or "Rajesh Sharma",
        lead_id=payload.lead_id,
        category=payload.category or "Solar",
        lead_type=payload.lead_type or "5kW Residential Rooftop",
        city=payload.city or "Hyderabad",
        lead_status=payload.lead_status or "Interested",
        deal_value=payload.deal_value or "₹3,50,000",
        db=db
    )

    return {
        "success": True,
        "test_session_id": mock_session_id,
        "dispatch_result": dispatch_res
    }
