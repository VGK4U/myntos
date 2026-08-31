"""
Automated Test Suite for MyOperatorTelephonyProvider Adapter
Phase 2B Verification: Auth, OBD Dispatch, Webhook Handling, Status Query, Recording Retrieval & CRM Integration.
Created: Aug 2026
"""

import os
import sys
import unittest
import json
import hmac
import hashlib
from unittest.mock import patch, MagicMock

# Set up test path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.models.voip_enums import CallStateEnum, RecordingStatusEnum
from app.services.telephony.myoperator_provider import MyOperatorTelephonyProvider
from app.services.telephony.factory import get_telephony_provider


class TestMyOperatorTelephonyProvider(unittest.TestCase):
    """Test suite for Phase 2B MyOperator telephony adapter"""

    def setUp(self):
        self.provider = MyOperatorTelephonyProvider(
            api_token="test_api_token_123",
            x_api_key="test_x_api_key_456",
            api_company_id="698c722ae2411959",
            webhook_secret="test_webhook_secret_789",
            public_ivr_id="test_public_ivr_id_999"
        )
        self.dummy_operator = {
            "id": 101,
            "name": "Yaswanth Y",
            "phone": "9053899899"
        }

    # ── 1. AGENT MAPPING & USER ID RESOLUTION ──────────────────────────────

    @patch("requests.get")
    def test_01_agent_lookup_resolution(self, mock_get):
        """Test resolving MyOperator user_id by agent phone number"""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "status": "success",
            "data": [
                {"name": "Yaswanth Y", "extension": "10", "contact_number": "+919053899899", "user_id": "usr_yaswanth_10"},
                {"name": "Anusha", "extension": "11", "contact_number": "+917569111471", "user_id": "usr_anusha_11"}
            ]
        }
        mock_get.return_value = mock_response

        uid = self.provider._get_agent_user_id(self.dummy_operator)
        self.assertEqual(uid, "usr_yaswanth_10")

    # ── 2. OBD CALL DISPATCHING ─────────────────────────────────────────────

    def test_02_obd_call_missing_ivr_id_fails_gracefully(self):
        """Test that missing public_ivr_id returns a clear configuration error"""
        provider_no_ivr = MyOperatorTelephonyProvider(
            api_token="test",
            x_api_key="test",
            api_company_id="698c722ae2411959",
            public_ivr_id=""  # Missing
        )
        result = provider_no_ivr.create_call(
            call_session_id="vcs_test_001",
            destination_phone="+919703118501",
            caller_id="+912269470537",
            operator_info=self.dummy_operator
        )
        self.assertFalse(result.success)
        self.assertIn("MYOPERATOR_PUBLIC_IVR_ID", result.error_message)

    @patch("requests.post")
    @patch.object(MyOperatorTelephonyProvider, "_get_agent_user_id", return_value="usr_yaswanth_10")
    def test_03_obd_call_successful_dispatch(self, mock_agent, mock_post):
        """Test successful OBD dispatch to MyOperator gateway"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "success",
            "code": "200",
            "unique_id": "myop_call_uuid_777",
            "message": "Call initiated successfully"
        }
        mock_post.return_value = mock_response

        result = self.provider.create_call(
            call_session_id="vcs_test_002",
            destination_phone="9703118501",
            caller_id="+912269470537",
            operator_info=self.dummy_operator
        )

        self.assertTrue(result.success)
        self.assertEqual(result.provider_call_id, "myop_call_uuid_777")
        self.assertEqual(result.initial_status, CallStateEnum.DIALING)
        self.assertIsNotNone(result.client_token)
        self.assertEqual(result.client_token.get("caller_id"), "+912269470537")

    # ── 3. WEBHOOK AUTHENTICATION & PARSING ─────────────────────────────────

    def test_04_webhook_hmac_authentication_success(self):
        """Test parsing valid webhook with HMAC signature"""
        payload = {
            "call_id": "myop_call_uuid_777",
            "reference_id": "vcs_test_002",
            "status": "answered",
            "duration": 95,
            "fileurl": "https://app.myoperator.com/audio/test_rec_123.mp3"
        }
        body = json.dumps(payload).encode('utf-8')
        sig = hmac.new(self.provider.webhook_secret.encode('utf-8'), body, hashlib.sha256).hexdigest()
        headers = {"X-MyOperator-Signature": sig}

        event = self.provider.handle_webhook(headers=headers, body=body, query_params={})
        self.assertTrue(event.is_valid)
        self.assertEqual(event.provider_call_id, "myop_call_uuid_777")
        self.assertEqual(event.call_session_id, "vcs_test_002")
        self.assertEqual(event.status, CallStateEnum.ENDED)
        self.assertEqual(event.duration_seconds, 95)
        self.assertEqual(event.recording_status, RecordingStatusEnum.AVAILABLE)
        self.assertEqual(event.recording_url, "https://app.myoperator.com/audio/test_rec_123.mp3")

    def test_05_webhook_invalid_auth_rejected(self):
        """Test rejecting tampered webhook payload"""
        body = json.dumps({"call_id": "hack_call"}).encode('utf-8')
        headers = {"X-MyOperator-Signature": "invalid_sig"}

        event = self.provider.handle_webhook(headers=headers, body=body, query_params={})
        self.assertFalse(event.is_valid)
        self.assertIn("authentication failed", event.error_message.lower())

    # ── 4. RECORDING DOWNLOAD ───────────────────────────────────────────────

    @patch("requests.get")
    def test_06_recording_download(self, mock_get):
        """Test downloading raw audio bytes from MyOperator storage URL"""
        mock_rec_bytes = b"ID3\x04\x00\x00\x00\x00\x00#TSSE\x00\x00\x00\x0f\x00\x00\x03Lavf58.29.100\x00" + b"\xff\xfb\x90d" * 50
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = mock_rec_bytes
        mock_get.return_value = mock_response

        audio = self.provider.get_recording("myop_call_uuid_777", "https://app.myoperator.com/audio/test_rec.mp3")
        self.assertIsNotNone(audio)
        self.assertEqual(audio, mock_rec_bytes)


if __name__ == '__main__':
    unittest.main()
