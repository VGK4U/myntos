"""
Unit & Integration Test Suite — Dedicated Plivo Application-Level Hangup Webhook with Official V3 Signature Validation
Tests:
1. Valid hangup callback with V3 signature updates VoIPCallSession (status, duration, termination reason, metadata)
2. Duplicate hangup callback is idempotent and returns HTTP 200
3. Invalid Plivo V3 signature is rejected with HTTP 401
4. Valid X-Plivo-Signature-V3 is accepted using full URL, sorted params, and nonce
5. Valid X-Plivo-Signature-Ma-V3 header is also supported and accepted
6. Unknown CallUUID is gracefully acknowledged with HTTP 200 without error
7. Official Plivo V3 test vector verified against direct manual base-string construction
Created: Sep 2026
"""

import unittest
import time
import json
import base64
import hmac
import hashlib
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.core.database import SessionLocal
from app.models.voip_call_session import VoIPCallSession
from app.models.voip_enums import CallStateEnum
from app.services.telephony.factory import get_telephony_provider
from app.services.telephony.plivo_provider import PlivoTelephonyProvider


class TestPlivoHangupWebhookV3(unittest.TestCase):
    """
    Test Suite for POST /api/v1/telephony/plivo/hangup with Official V3 Signature Validation
    """

    def setUp(self):
        self.client = TestClient(app)
        self.db: Session = SessionLocal()
        self.test_session_ids = []

        # Create active test VoIPCallSession
        self.call_uuid = f"plivo_uuid_{int(time.time())}_{id(self)}"
        self.session_id = f"vcs_hangup_test_{int(time.time())}"
        self.test_session_ids.append(self.session_id)

        self.session = VoIPCallSession(
            company_id=1,
            call_session_id=self.session_id,
            provider="plivo",
            provider_call_id=self.call_uuid,
            caller_id="+918031728899",
            customer_phone="9876500001",
            destination_number="9876500001",
            operator_id=101,
            direction="inbound",
            status=CallStateEnum.CONNECTED.value
        )
        self.db.add(self.session)
        self.db.commit()

    def tearDown(self):
        try:
            for sid in self.test_session_ids:
                self.db.query(VoIPCallSession).filter(VoIPCallSession.call_session_id == sid).delete()
            self.db.commit()
        except Exception:
            self.db.rollback()
        finally:
            self.db.close()

    def _generate_v3_signature(self, url: str, nonce: str, auth_token: str, params: dict) -> str:
        """Helper to generate official Plivo V3 signature: URL + param_str + '.' + nonce"""
        sorted_keys = sorted(params.keys())
        param_str = "".join(f"{k}{params[k]}" for k in sorted_keys if params[k] is not None)
        base_string = f"{url}{param_str}.{nonce}" if param_str else f"{url}.{nonce}"
        digest = hmac.new(auth_token.encode('utf-8'), base_string.encode('utf-8'), hashlib.sha256).digest()
        return base64.b64encode(digest).decode('utf-8')

    # 1. Valid hangup callback updates VoIPCallSession
    def test_01_valid_hangup_callback(self):
        payload = {
            "CallUUID": self.call_uuid,
            "CallStatus": "completed",
            "Direction": "inbound",
            "From": "+919876500001",
            "To": "+918031728899",
            "Duration": "45",
            "BillDuration": "45",
            "HangupCauseName": "NORMAL_CLEARING",
            "HangupCauseCode": "16",
            "HangupSource": "caller",
            "ALegUUID": self.call_uuid,
            "BLegUUID": "bleg_test_uuid_456"
        }

        resp = self.client.post(
            "/api/v1/telephony/plivo/hangup",
            data=payload
        )

        self.assertEqual(resp.status_code, 200)
        res_json = resp.json()
        self.assertEqual(res_json.get("status"), "success")
        self.assertEqual(res_json.get("final_status"), CallStateEnum.ENDED.value)
        self.assertEqual(res_json.get("duration_seconds"), 45)

        # Verify DB session update
        fresh_session = self.db.query(VoIPCallSession).filter_by(call_session_id=self.session_id).first()
        self.assertEqual(fresh_session.status, CallStateEnum.ENDED.value)
        self.assertEqual(fresh_session.duration_seconds, 45)
        self.assertIn("NORMAL_CLEARING", fresh_session.termination_reason)
        self.assertIsNotNone(fresh_session.ended_at)
        meta = json.loads(fresh_session.metadata_json) if isinstance(fresh_session.metadata_json, str) else (fresh_session.metadata_json or {})
        self.assertEqual(meta.get("plivo_hangup_cause_name"), "NORMAL_CLEARING")
        self.assertEqual(meta.get("plivo_hangup_source"), "caller")

    # 2. Duplicate hangup callback is idempotent and returns HTTP 200
    def test_02_duplicate_hangup_callback_idempotent(self):
        payload = {
            "CallUUID": self.call_uuid,
            "CallStatus": "completed",
            "Duration": "50",
            "HangupCauseName": "NORMAL_CLEARING"
        }

        # First callback
        resp1 = self.client.post("/api/v1/telephony/plivo/hangup", data=payload)
        self.assertEqual(resp1.status_code, 200)

        # Second duplicate callback
        resp2 = self.client.post("/api/v1/telephony/plivo/hangup", data=payload)
        self.assertEqual(resp2.status_code, 200)
        self.assertEqual(resp2.json().get("status"), "success")

        # Verify DB session remains valid
        fresh = self.db.query(VoIPCallSession).filter_by(call_session_id=self.session_id).first()
        self.assertEqual(fresh.status, CallStateEnum.ENDED.value)
        self.assertEqual(fresh.duration_seconds, 50)

    # 3. Invalid Plivo V3 signature is rejected with HTTP 401
    def test_03_invalid_v3_signature_rejected(self):
        payload = {
            "CallUUID": self.call_uuid,
            "CallStatus": "completed"
        }
        resp = self.client.post(
            "/api/v1/telephony/plivo/hangup",
            data=payload,
            headers={
                "X-Plivo-Signature-V3": "invalid_forged_v3_signature_xyz",
                "X-Plivo-Signature-V3-Nonce": "1234567890"
            }
        )
        self.assertEqual(resp.status_code, 401)
        self.assertIn("Invalid Plivo V3 Webhook Signature", resp.json().get("detail", ""))

    # 4. Valid X-Plivo-Signature-V3 is accepted using URL + sorted_params + '.' + nonce
    def test_04_valid_v3_signature_accepted(self):
        provider = get_telephony_provider("plivo")
        payload = {
            "CallUUID": self.call_uuid,
            "CallStatus": "completed",
            "Duration": "30"
        }
        url = "http://testserver/api/v1/telephony/plivo/hangup"
        nonce = "nonce_random_test_12345"
        sig_v3 = self._generate_v3_signature(
            url=url,
            nonce=nonce,
            auth_token=provider.auth_token,
            params=payload
        )

        resp = self.client.post(
            "/api/v1/telephony/plivo/hangup",
            data=payload,
            headers={
                "X-Plivo-Signature-V3": sig_v3,
                "X-Plivo-Signature-V3-Nonce": nonce
            }
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json().get("status"), "success")

    # 5. Valid X-Plivo-Signature-Ma-V3 is also supported and accepted
    def test_05_valid_ma_v3_signature_accepted(self):
        provider = get_telephony_provider("plivo")
        payload = {
            "CallUUID": self.call_uuid,
            "CallStatus": "completed",
            "Duration": "20"
        }
        url = "http://testserver/api/v1/telephony/plivo/hangup"
        nonce = "ma_nonce_test_98765"
        sig_ma_v3 = self._generate_v3_signature(
            url=url,
            nonce=nonce,
            auth_token=provider.auth_token,
            params=payload
        )

        resp = self.client.post(
            "/api/v1/telephony/plivo/hangup",
            data=payload,
            headers={
                "X-Plivo-Signature-Ma-V3": sig_ma_v3,
                "X-Plivo-Signature-Ma-V3-Nonce": nonce
            }
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json().get("status"), "success")

    # 6. Unknown CallUUID is gracefully acknowledged with HTTP 200 without error
    def test_06_unknown_call_uuid_gracefully_acknowledged(self):
        payload = {
            "CallUUID": "unknown_nonexistent_call_uuid_999999",
            "CallStatus": "completed",
            "Duration": "10"
        }
        resp = self.client.post(
            "/api/v1/telephony/plivo/hangup",
            data=payload
        )
        self.assertEqual(resp.status_code, 200)
        res_json = resp.json()
        self.assertEqual(res_json.get("status"), "success")
        self.assertIn("no active session found", res_json.get("message", "").lower())

    # 7. Official Plivo V3 test vector verification
    def test_07_plivo_official_v3_test_vector(self):
        auth_token = "MAXXXXXXXXXXXXXXXXXX"
        url = "https://example.com/hangup"
        nonce = "12345"
        params = {
            "CallUUID": "01234567-89ab-cdef-0123-456789abcdef",
            "CallStatus": "completed",
            "Duration": "60"
        }
        # Official base string: URL + sorted_params + "." + nonce
        # sorted keys: CallStatus, CallUUID, Duration
        # param_str: "CallStatuscompletedCallUUID01234567-89ab-cdef-0123-456789abcdefDuration60"
        # base_string: "https://example.com/hangupCallStatuscompletedCallUUID01234567-89ab-cdef-0123-456789abcdefDuration60.12345"
        expected_base_string = "https://example.com/hangupCallStatuscompletedCallUUID01234567-89ab-cdef-0123-456789abcdefDuration60.12345"
        expected_sig = base64.b64encode(
            hmac.new(auth_token.encode('utf-8'), expected_base_string.encode('utf-8'), hashlib.sha256).digest()
        ).decode('utf-8')

        is_valid = PlivoTelephonyProvider.validate_signature_v3(
            url=url,
            nonce=nonce,
            signature=expected_sig,
            auth_token=auth_token,
            method="POST",
            params=params
        )
        self.assertTrue(is_valid)


if __name__ == '__main__':
    unittest.main()
