"""
MyOperator Telephony Provider Adapter
Concrete implementation of BaseTelephonyProvider for MyOperator OBD (Outbound Dialer) Cloud Bridge.
Handles outbound call dispatching, webhook authentication, status querying, and server-side MP3 recording retrieval.
Created: Aug 2026
"""

import os
import re
import json
import hmac
import hashlib
import logging
import requests
from typing import Optional, Dict, Any
from datetime import datetime

from app.core.config import settings
from app.models.voip_enums import CallStateEnum, RecordingStatusEnum
from app.services.telephony.base import (
    BaseTelephonyProvider,
    TelephonyCallResult,
    TelephonyCallStatus,
    TelephonyWebhookEvent
)

logger = logging.getLogger(__name__)


class MyOperatorTelephonyProvider(BaseTelephonyProvider):
    """
    MyOperator 2-Leg Cloud Bridge Telephony Provider Adapter.
    Leg 1: Telephony server dials telecaller's mobile phone.
    Leg 2: Telephony server dials customer mobile presenting +912269470537.
    Bridges both audio streams and mixes two-way recording on MyOperator servers.
    """

    OBD_URL = "https://obd-api.myoperator.co/obd-api-v1"
    DEV_BASE_URL = "https://developers.myoperator.co"

    def __init__(
        self,
        api_token: Optional[str] = None,
        x_api_key: Optional[str] = None,
        api_company_id: Optional[str] = None,
        webhook_secret: Optional[str] = None,
        public_ivr_id: Optional[str] = None
    ):
        self.api_token = api_token or os.getenv("MYOPERATOR_API_TOKEN", "")
        self.x_api_key = x_api_key or os.getenv("MYOPERATOR_X_API_KEY", "")
        self.api_company_id = api_company_id or os.getenv("MYOPERATOR_API_COMPANY_ID", "")
        self.webhook_secret = webhook_secret or os.getenv("MYOPERATOR_WEBHOOK_SECRET", "")
        self.public_ivr_id = public_ivr_id or os.getenv("MYOPERATOR_PUBLIC_IVR_ID", "")
        self._user_cache = {}

    @property
    def provider_name(self) -> str:
        return "myoperator"

    def _get_agent_user_id(self, operator_info: Dict[str, Any]) -> Optional[str]:
        """Resolve operator user_id from MyOperator developer API /user list"""
        if not self.api_token:
            return None

        # Check local cache or fetch fresh list
        if not self._user_cache:
            try:
                resp = requests.get(
                    f"{self.DEV_BASE_URL}/user",
                    params={"token": self.api_token},
                    timeout=8
                )
                data = resp.json()
                if data.get("status") == "success" and data.get("data"):
                    self._user_cache = {
                        re.sub(r'[^\d]', '', str(u.get("contact_number", "")))[-10:]: u.get("user_id")
                        for u in data.get("data", [])
                        if u.get("contact_number")
                    }
                    # Also map by name
                    for u in data.get("data", []):
                        if u.get("name"):
                            self._user_cache[u.get("name").lower().strip()] = u.get("user_id")
            except Exception as e:
                logger.warning(f"[MYOP-PROVIDER] Could not refresh user cache: {e}")

        # Match by phone
        phone = re.sub(r'[^\d]', '', str(operator_info.get("phone", "")))[-10:]
        if phone and phone in self._user_cache:
            return self._user_cache[phone]

        # Match by name
        name = str(operator_info.get("name", "")).lower().strip()
        if name and name in self._user_cache:
            return self._user_cache[name]

        return None

    def create_call(
        self,
        call_session_id: str,
        destination_phone: str,
        caller_id: str,
        operator_info: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> TelephonyCallResult:
        """
        Dispatch Outbound 2-Leg Call via MyOperator OBD API.
        """
        if not self.x_api_key:
            return TelephonyCallResult(
                success=False,
                error_message="MYOPERATOR_X_API_KEY is not configured on server"
            )

        if not self.public_ivr_id:
            return TelephonyCallResult(
                success=False,
                error_message="MYOPERATOR_PUBLIC_IVR_ID is not configured (Required for live OBD calls)"
            )

        # Resolve MyOperator Agent user_id
        myop_user_id = self._get_agent_user_id(operator_info)
        if not myop_user_id:
            op_name = operator_info.get("name", "Staff")
            return TelephonyCallResult(
                success=False,
                error_message=f"Operator '{op_name}' not mapped to an active agent in MyOperator account"
            )

        # Format E.164 phone
        dest_digits = re.sub(r'[^\d]', '', str(destination_phone))
        if len(dest_digits) == 10:
            dest_e164 = f"+91{dest_digits}"
        elif dest_digits.startswith("91") and len(dest_digits) == 12:
            dest_e164 = f"+{dest_digits}"
        else:
            dest_e164 = f"+{dest_digits}" if not destination_phone.startswith("+") else destination_phone

        payload = {
            "company_id": self.api_company_id,
            "secret_token": self.webhook_secret,
            "type": "1",
            "user_id": myop_user_id,
            "number": dest_e164,
            "public_ivr_id": self.public_ivr_id,
            "reference_id": call_session_id
        }

        headers = {
            "x-api-key": self.x_api_key,
            "Content-Type": "application/json"
        }

        try:
            resp = requests.post(self.OBD_URL, json=payload, headers=headers, timeout=12)
            try:
                data = resp.json()
            except Exception:
                return TelephonyCallResult(
                    success=False,
                    error_message=f"MyOperator returned non-JSON response (HTTP {resp.status_code})"
                )

            status_val = str(data.get("status", "")).lower()
            code_val = str(data.get("code", ""))

            if status_val == "error" or (code_val and code_val not in ("200", "201", "202")):
                err_msg = data.get("details") or data.get("message") or "MyOperator OBD call rejected"
                return TelephonyCallResult(
                    success=False,
                    error_message=f"MyOperator Error ({code_val}): {err_msg}",
                    raw_response=data
                )

            provider_call_id = str(
                data.get("unique_id") or data.get("call_id") or data.get("uuid") or call_session_id
            )

            client_info = {
                "call_method": "myoperator_bridge",
                "agent_leg": "physical_mobile",
                "caller_id": caller_id,
                "agent_name": operator_info.get("name"),
                "agent_phone": operator_info.get("phone")
            }

            return TelephonyCallResult(
                success=True,
                provider_call_id=provider_call_id,
                initial_status=CallStateEnum.DIALING,
                client_token=client_info,
                raw_response=data
            )

        except Exception as e:
            logger.error(f"[MYOP-OBD-CALL-FAILED] Request error: {e}")
            return TelephonyCallResult(
                success=False,
                error_message=f"Unable to connect to MyOperator gateway: {str(e)}"
            )

    def get_call_status(self, provider_call_id: str) -> TelephonyCallStatus:
        """Query MyOperator Search API for call record and status"""
        if not self.api_token:
            return TelephonyCallStatus(
                provider_call_id=provider_call_id,
                status=CallStateEnum.CREATED,
                termination_reason="API token not configured"
            )

        try:
            import time
            now_ts = int(time.time())
            resp = requests.post(
                f"{self.DEV_BASE_URL}/search",
                data={
                    "token": self.api_token,
                    "from": now_ts - 86400,
                    "to": now_ts + 3600,
                    "page_size": 10
                },
                timeout=8
            )
            data = resp.json()
            hits = (data.get("data") or {}).get("hits") or []
            for hit in hits:
                src = hit.get("_source") or {}
                raw_uid = src.get("allcaller_id") or ""
                add_params = src.get("additional_parameters") or []
                uniq_id = next((p.get("vl") for p in add_params if p.get("ky") == "unique_id"), "")

                if provider_call_id in (raw_uid, uniq_id):
                    # Status code mapping: 1 = answered, 2 = missed, 3 = voicemail
                    sc = int(src.get("status", 2))
                    dur = int(src.get("seconds") or 0)
                    mapped_state = CallStateEnum.ENDED if (sc == 1 and dur > 0) else CallStateEnum.NO_ANSWER
                    rec_url = src.get("fileurl") or None

                    return TelephonyCallStatus(
                        provider_call_id=provider_call_id,
                        status=mapped_state,
                        duration_seconds=dur,
                        recording_status=RecordingStatusEnum.AVAILABLE if rec_url else RecordingStatusEnum.NOT_STARTED,
                        recording_url=rec_url,
                        raw_data=src
                    )
        except Exception as e:
            logger.warning(f"[MYOP-PROVIDER] Status lookup error: {e}")

        return TelephonyCallStatus(
            provider_call_id=provider_call_id,
            status=CallStateEnum.DIALING
        )

    def hangup_call(self, provider_call_id: str) -> bool:
        """MyOperator OBD calls are managed by the telecom switch leg timeout"""
        logger.info(f"[MYOP-PROVIDER] Hangup requested for provider_call_id: {provider_call_id}")
        return True

    def get_recording(self, provider_call_id: str, recording_url: Optional[str] = None) -> Optional[bytes]:
        """Download raw audio bytes from MyOperator storage URL"""
        if not recording_url or not recording_url.startswith("http"):
            return None

        try:
            resp = requests.get(recording_url, timeout=25)
            if resp.status_code == 200 and len(resp.content) > 100:
                return resp.content
            logger.warning(f"[MYOP-PROVIDER] Recording download failed (HTTP {resp.status_code}) from {recording_url}")
        except Exception as e:
            logger.error(f"[MYOP-PROVIDER] Error downloading recording {recording_url}: {e}")

        return None

    def handle_webhook(
        self,
        headers: Dict[str, str],
        body: bytes,
        query_params: Dict[str, str]
    ) -> TelephonyWebhookEvent:
        """
        Authenticate and normalize incoming MyOperator call webhook.
        Validates: X-MyOperator-Signature, X-Api-Key, or body token.
        """
        try:
            payload = json.loads(body.decode('utf-8'))
        except Exception:
            try:
                from urllib.parse import parse_qs
                qs = parse_qs(body.decode('utf-8', errors='replace'))
                payload = {k: v[0] if len(v) == 1 else v for k, v in qs.items()}
            except Exception as pe:
                return TelephonyWebhookEvent(
                    is_valid=False,
                    event_type="parse_error",
                    provider_call_id="",
                    error_message=f"Payload parse error: {pe}"
                )

        # Multi-layer authentication check
        auth_ok = False
        # 1. HMAC signature
        if self.webhook_secret:
            sig = (
                headers.get("X-MyOperator-Signature") or
                headers.get("x-myoperator-signature") or
                headers.get("x-signature") or ""
            ).strip()
            if sig:
                expected = hmac.new(self.webhook_secret.encode('utf-8'), body, hashlib.sha256).hexdigest()
                if hmac.compare_digest(sig, expected):
                    auth_ok = True

        # 2. X-Api-Key header
        if not auth_ok and self.x_api_key:
            hdr_key = (headers.get("X-Api-Key") or headers.get("x-api-key") or "").strip()
            if hdr_key and hdr_key == self.x_api_key:
                auth_ok = True

        # 3. Body token
        if not auth_ok and (self.api_token or self.x_api_key):
            tok = str(payload.get("token") or payload.get("api_token") or "").strip()
            if tok and tok in (self.api_token, self.x_api_key):
                auth_ok = True

        # If no security secrets configured in test mode
        if not (self.webhook_secret or self.x_api_key or self.api_token):
            auth_ok = True

        if not auth_ok:
            return TelephonyWebhookEvent(
                is_valid=False,
                event_type="auth_failed",
                provider_call_id="",
                error_message="MyOperator webhook authentication failed (Invalid signature/token)"
            )

        provider_call_id = str(
            payload.get("call_id") or payload.get("uuid") or payload.get("unique_id") or payload.get("session_id") or ""
        )
        call_session_id = payload.get("reference_id") or payload.get("call_session_id")

        # Map status
        raw_status = str(payload.get("status", "")).lower()
        duration = int(payload.get("duration") or payload.get("duration_seconds") or 0)
        
        if raw_status in ("answered", "connected", "1"):
            status_enum = CallStateEnum.ENDED if duration > 0 else CallStateEnum.ANSWERED
        elif raw_status in ("missed", "2"):
            status_enum = CallStateEnum.NO_ANSWER
        elif raw_status in ("busy"):
            status_enum = CallStateEnum.BUSY
        elif raw_status in ("failed"):
            status_enum = CallStateEnum.FAILED
        else:
            status_enum = CallStateEnum.ENDED if duration > 0 else CallStateEnum.RINGING

        rec_url = payload.get("fileurl") or payload.get("recording_url") or None
        rec_status = RecordingStatusEnum.AVAILABLE if rec_url else RecordingStatusEnum.NOT_STARTED

        return TelephonyWebhookEvent(
            is_valid=True,
            event_type="call_completed" if duration > 0 else "status_update",
            provider_call_id=provider_call_id,
            call_session_id=call_session_id,
            status=status_enum,
            duration_seconds=duration,
            termination_reason=payload.get("miss_reason") or payload.get("disconnection_reason"),
            recording_url=rec_url,
            recording_status=rec_status,
            raw_payload=payload
        )

    def generate_client_token(
        self,
        call_session_id: str,
        operator_info: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Returns client connection info for MyOperator Bridge mode.
        Note: MyOperator standard developer API uses physical GSM handset leg, not client WebRTC token.
        """
        return {
            "mode": "myoperator_bridge",
            "caller_id": "+912269470537",
            "agent_name": operator_info.get("name"),
            "agent_phone": operator_info.get("phone"),
            "session_id": call_session_id
        }
