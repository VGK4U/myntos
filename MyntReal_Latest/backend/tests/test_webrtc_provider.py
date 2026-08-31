"""
Automated Test Suite for InAppWebRTCTelephonyProvider (Zero-SIM PSTN Audio)
Phase 2C Verification: WebRTC Ephemeral Token, Session Allocation, HMAC Webhooks, S3 Recording Vault & Lifecycle.
Created: Aug 2026
"""

import os
import sys
import unittest
import json
import hmac
import hashlib
import time

# Set up test path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.models.voip_enums import CallStateEnum, RecordingStatusEnum
from app.services.telephony.webrtc_provider import InAppWebRTCTelephonyProvider
from app.services.telephony.factory import get_telephony_provider


class TestInAppWebRTCTelephonyProvider(unittest.TestCase):
    """Test suite for Phase 2C Zero-SIM WebRTC PSTN adapter"""

    def setUp(self):
        self.provider = InAppWebRTCTelephonyProvider(
            gateway_url="wss://webrtc-gateway.myntreal.local/ws",
            api_key="test_webrtc_key",
            api_secret="test_webrtc_secret_key_12345",
            webhook_secret="test_webhook_secret_789"
        )
        self.dummy_operator = {
            "id": 101,
            "name": "Yaswanth Y",
            "phone": "9053899899"
        }

    # ── 1. EPHEMERAL CLIENT TOKEN & SECURITY ────────────────────────────────

    def test_01_webrtc_token_generation_and_security(self):
        """Test generating short-lived cryptographically signed client media token"""
        token_data = self.provider._generate_ephemeral_client_token(
            call_session_id="vcs_rtc_001",
            destination_number="+919703118501",
            caller_id="+912269470537",
            operator_info=self.dummy_operator,
            expires_in=900
        )

        self.assertIsNotNone(token_data)
        self.assertEqual(token_data["token_type"], "Bearer")
        self.assertTrue("session_token" in token_data)
        self.assertEqual(token_data["caller_id"], "+912269470537")
        self.assertEqual(token_data["destination"], "+919703118501")
        self.assertEqual(token_data["expires_in_seconds"], 900)
        self.assertEqual(token_data["agent_leg"], "webrtc_in_app_audio")
        self.assertTrue(len(token_data["ice_servers"]) >= 2)

        # Verify HMAC signature on token payload
        raw_hex, sig = token_data["session_token"].split(".")
        payload_bytes = bytes.fromhex(raw_hex)
        expected_sig = hmac.new(self.provider.api_secret.encode('utf-8'), payload_bytes, hashlib.sha256).hexdigest()
        self.assertEqual(sig, expected_sig)

        # Ensure master secrets are NOT inside client payload
        payload_obj = json.loads(payload_bytes.decode('utf-8'))
        self.assertNotIn("api_secret", payload_obj)
        self.assertNotIn("webhook_secret", payload_obj)

    # ── 2. CALL CREATION & SESSION ALLOCATION ───────────────────────────────

    def test_02_webrtc_session_allocation(self):
        """Test zero-SIM call allocation via InAppWebRTCTelephonyProvider"""
        result = self.provider.create_call(
            call_session_id="vcs_rtc_002",
            destination_phone="9703118501",
            caller_id="+912269470537",
            operator_info=self.dummy_operator
        )

        self.assertTrue(result.success)
        self.assertTrue(result.provider_call_id.startswith("rtc_"))
        self.assertEqual(result.initial_status, CallStateEnum.DIALING)
        self.assertIsNotNone(result.client_token)
        self.assertEqual(result.client_token.get("agent_leg"), "webrtc_in_app_audio")
        self.assertEqual(result.client_token.get("destination"), "+919703118501")

    # ── 3. WEBHOOK AUTHENTICATION & PARSING ─────────────────────────────────

    def test_03_webrtc_webhook_hmac_signature_verification(self):
        """Test WebRTC gateway webhook parsing and HMAC validation"""
        payload = {
            "provider_call_id": "rtc_session_999",
            "call_session_id": "vcs_rtc_003",
            "status": "connected",
            "duration": 45,
            "recording_status": "available",
            "recording_url": "https://webrtc-gateway.local/recordings/rtc_session_999.wav"
        }
        body = json.dumps(payload).encode('utf-8')
        sig = hmac.new(self.provider.webhook_secret.encode('utf-8'), body, hashlib.sha256).hexdigest()
        headers = {"X-Telephony-Signature": sig}

        event = self.provider.handle_webhook(headers=headers, body=body, query_params={})
        self.assertTrue(event.is_valid)
        self.assertEqual(event.provider_call_id, "rtc_session_999")
        self.assertEqual(event.call_session_id, "vcs_rtc_003")
        self.assertEqual(event.status, CallStateEnum.CONNECTED)
        self.assertEqual(event.duration_seconds, 45)
        self.assertEqual(event.recording_status, RecordingStatusEnum.AVAILABLE)

    def test_04_webrtc_webhook_tampered_signature_rejected(self):
        """Test rejecting unauthenticated webhook events"""
        body = json.dumps({"provider_call_id": "rtc_session_999"}).encode('utf-8')
        headers = {"X-Telephony-Signature": "forged_signature_123"}

        event = self.provider.handle_webhook(headers=headers, body=body, query_params={})
        self.assertFalse(event.is_valid)
        self.assertIn("invalid", event.error_message.lower())

    # ── 4. TWO-WAY SERVER RECORDING RETRIEVAL ────────────────────────────────

    def test_05_webrtc_two_way_recording_download(self):
        """Test retrieving two-way mixed audio bytes from media gateway"""
        audio_bytes = self.provider.get_recording("rtc_session_999")
        self.assertIsNotNone(audio_bytes)
        self.assertTrue(audio_bytes.startswith(b"RIFF"))  # WAV RIFF header check


if __name__ == '__main__':
    unittest.main()
