"""
Mock Telephony Provider for Testing, Sandbox & Development
Provides deterministic state management, simulated audio recordings, and webhook generation.
Created: Aug 2026
"""

import hmac
import hashlib
import json
import uuid
import logging
from typing import Optional, Dict, Any
from datetime import datetime
from app.models.voip_enums import CallStateEnum, RecordingStatusEnum
from app.services.telephony.base import (
    BaseTelephonyProvider,
    TelephonyCallResult,
    TelephonyCallStatus,
    TelephonyWebhookEvent
)

logger = logging.getLogger(__name__)


class MockTelephonyProvider(BaseTelephonyProvider):
    """
    In-memory mock telephony provider for local dev and automated test suites.
    """

    def __init__(self, webhook_secret: str = "mock-secret-key-12345"):
        self.webhook_secret = webhook_secret
        # In-memory store of active mock calls: provider_call_id -> dict
        self._calls: Dict[str, Dict[str, Any]] = {}
        # In-memory store of mock recordings: provider_call_id -> bytes
        self._recordings: Dict[str, bytes] = {}

    @property
    def provider_name(self) -> str:
        return "mock"

    def create_call(
        self,
        call_session_id: str,
        destination_phone: str,
        caller_id: str,
        operator_info: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> TelephonyCallResult:
        """Create a mock call session"""
        provider_call_id = f"mock_call_{uuid.uuid4().hex[:12]}"
        
        call_record = {
            "provider_call_id": provider_call_id,
            "call_session_id": call_session_id,
            "destination_phone": destination_phone,
            "caller_id": caller_id,
            "operator_info": operator_info,
            "metadata": metadata or {},
            "status": CallStateEnum.DIALING,
            "started_at": datetime.utcnow(),
            "answered_at": None,
            "ended_at": None,
            "duration_seconds": 0,
            "recording_status": RecordingStatusEnum.NOT_STARTED,
            "termination_reason": None
        }
        self._calls[provider_call_id] = call_record
        logger.info(f"[MOCK-TELEPHONY] Created call: session={call_session_id}, provider_id={provider_call_id}, to={destination_phone}")

        client_token = {
            "token": f"mock_webrtc_jwt_{uuid.uuid4().hex}",
            "expires_in": 3600,
            "server": "wss://mock-webrtc.myntreal.local/ws",
            "session_id": call_session_id
        }

        return TelephonyCallResult(
            success=True,
            provider_call_id=provider_call_id,
            initial_status=CallStateEnum.DIALING,
            client_token=client_token,
            raw_response={"status": "queued", "id": provider_call_id}
        )

    def get_call_status(self, provider_call_id: str) -> TelephonyCallStatus:
        call = self._calls.get(provider_call_id)
        if not call:
            return TelephonyCallStatus(
                provider_call_id=provider_call_id,
                status=CallStateEnum.FAILED,
                termination_reason="Call not found in mock provider"
            )

        return TelephonyCallStatus(
            provider_call_id=provider_call_id,
            status=call["status"],
            duration_seconds=call["duration_seconds"],
            started_at=call["started_at"],
            answered_at=call["answered_at"],
            ended_at=call["ended_at"],
            recording_status=call["recording_status"],
            recording_url=f"https://mock-telephony.local/recordings/{provider_call_id}.mp3" if call["recording_status"] == RecordingStatusEnum.AVAILABLE else None,
            termination_reason=call["termination_reason"],
            raw_data=call
        )

    def hangup_call(self, provider_call_id: str) -> bool:
        call = self._calls.get(provider_call_id)
        if not call:
            return False
        call["status"] = CallStateEnum.ENDED
        call["ended_at"] = datetime.utcnow()
        call["termination_reason"] = "operator_hangup"
        logger.info(f"[MOCK-TELEPHONY] Hangup call: {provider_call_id}")
        return True

    def get_recording(self, provider_call_id: str, recording_url: Optional[str] = None) -> Optional[bytes]:
        # Return generated mock audio bytes (RIFF/WAV header stub)
        if provider_call_id in self._recordings:
            return self._recordings[provider_call_id]
        
        # Standard dummy 44-byte WAV header + mock PCM data for testing
        mock_wav = (
            b"RIFF\x2c\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00"
            b"\x44\xac\x00\x00\x88\x58\x01\x00\x02\x00\x10\x00data\x08\x00\x00\x00"
            b"\x00\x00\x00\x00\x00\x00\x00\x00"
        )
        self._recordings[provider_call_id] = mock_wav
        return mock_wav

    def handle_webhook(
        self,
        headers: Dict[str, str],
        body: bytes,
        query_params: Dict[str, str]
    ) -> TelephonyWebhookEvent:
        """
        Validates HMAC signature and parses mock event.
        Header: X-Telephony-Signature = sha256_hmac(body, secret)
        """
        # Signature Verification
        expected_sig = hmac.new(
            self.webhook_secret.encode('utf-8'),
            body,
            hashlib.sha256
        ).hexdigest()

        provided_sig = headers.get("X-Telephony-Signature") or headers.get("x-telephony-signature") or ""
        
        # Allow testing bypass if header matches or explicit bypass query flag is passed
        is_authenticated = (provided_sig == expected_sig) or (query_params.get("mock_auth") == "true")
        
        if not is_authenticated:
            return TelephonyWebhookEvent(
                is_valid=False,
                event_type="auth_failed",
                provider_call_id="",
                error_message="Invalid webhook HMAC signature"
            )

        try:
            payload = json.loads(body.decode('utf-8'))
        except Exception as e:
            return TelephonyWebhookEvent(
                is_valid=False,
                event_type="parse_error",
                provider_call_id="",
                error_message=f"JSON parse error: {str(e)}"
            )

        provider_call_id = payload.get("provider_call_id") or payload.get("call_id") or ""
        event_type = payload.get("event_type") or payload.get("status") or "unknown"
        call_session_id = payload.get("call_session_id")
        
        # Status mapping
        status_str = str(payload.get("status", "")).lower()
        status_map = {
            "created": CallStateEnum.CREATED,
            "dialing": CallStateEnum.DIALING,
            "ringing": CallStateEnum.RINGING,
            "answered": CallStateEnum.ANSWERED,
            "connected": CallStateEnum.CONNECTED,
            "ended": CallStateEnum.ENDED,
            "completed": CallStateEnum.ENDED,
            "busy": CallStateEnum.BUSY,
            "no_answer": CallStateEnum.NO_ANSWER,
            "no-answer": CallStateEnum.NO_ANSWER,
            "rejected": CallStateEnum.REJECTED,
            "failed": CallStateEnum.FAILED,
            "cancelled": CallStateEnum.CANCELLED,
        }
        mapped_status = status_map.get(status_str)

        # Recording status mapping
        rec_status_str = str(payload.get("recording_status", "")).lower()
        rec_status_map = {
            "not_started": RecordingStatusEnum.NOT_STARTED,
            "recording": RecordingStatusEnum.RECORDING,
            "processing": RecordingStatusEnum.PROCESSING,
            "available": RecordingStatusEnum.AVAILABLE,
            "completed": RecordingStatusEnum.AVAILABLE,
            "failed": RecordingStatusEnum.FAILED,
        }
        mapped_rec_status = rec_status_map.get(rec_status_str)
        if payload.get("recording_url") and not mapped_rec_status:
            mapped_rec_status = RecordingStatusEnum.AVAILABLE

        # Update in-memory state if call exists
        if provider_call_id in self._calls:
            if mapped_status:
                self._calls[provider_call_id]["status"] = mapped_status
            if payload.get("duration_seconds") is not None:
                self._calls[provider_call_id]["duration_seconds"] = int(payload["duration_seconds"])
            if mapped_rec_status:
                self._calls[provider_call_id]["recording_status"] = mapped_rec_status

        return TelephonyWebhookEvent(
            is_valid=True,
            event_type=event_type,
            provider_call_id=provider_call_id,
            call_session_id=call_session_id,
            status=mapped_status,
            duration_seconds=payload.get("duration_seconds"),
            termination_reason=payload.get("termination_reason"),
            recording_url=payload.get("recording_url"),
            recording_status=mapped_rec_status,
            recording_duration_seconds=payload.get("recording_duration_seconds"),
            raw_payload=payload
        )

    def generate_client_token(
        self,
        call_session_id: str,
        operator_info: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        return {
            "token": f"mock_jwt_{uuid.uuid4().hex}",
            "expires_in": 3600,
            "identity": str(operator_info.get("id") or "staff"),
            "session_id": call_session_id
        }

    # Helper method for tests to generate signed webhook payload
    def create_signed_webhook_payload(self, payload: Dict[str, Any]) -> tuple[bytes, Dict[str, str]]:
        body = json.dumps(payload).encode('utf-8')
        sig = hmac.new(self.webhook_secret.encode('utf-8'), body, hashlib.sha256).hexdigest()
        headers = {
            "Content-Type": "application/json",
            "X-Telephony-Signature": sig
        }
        return body, headers
