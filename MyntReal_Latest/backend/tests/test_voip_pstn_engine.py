"""
Comprehensive Automated Test Suite for MyntReal In-App PSTN Telephony & Backend Call Session Engine
Phase 1 Verification: Call Creation, Validation, State Machine, Webhooks, Idempotency, Security & S3 Recordings.
Created: Aug 2026
"""

import os
import sys
import unittest
import json
from datetime import datetime

# Set up test path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.core.database import SessionLocal, engine
from app.models.voip_enums import CallMethodEnum, CallStateEnum, RecordingStatusEnum
from app.models.voip_call_session import VoIPCallSession
from app.models.operator_calls import OperatorCall
from app.models.crm import CRMLead, CRMLeadAuditLog
from app.models.staff import StaffEmployee
from app.services.voip_call_service import VoIPCallService
from app.services.telephony.factory import get_telephony_provider
from app.services.telephony.mock_provider import MockTelephonyProvider
from fastapi import HTTPException


class DummyStaffUser:
    """Mock staff employee user for unit testing"""
    def __init__(self, user_id=1, emp_code="MR10001", name="Yaswanth Y", company_id=1, phone="9053899899"):
        self.id = user_id
        self.emp_code = emp_code
        self.full_name = name
        self.name = name
        self.company_id = company_id
        self.branch_id = 1
        self.phone = phone
        self.phone_number = phone


class TestVoIPPSTNEngine(unittest.TestCase):
    """Test suite for Phase 1 In-App PSTN Calling Engine"""

    def setUp(self):
        self.db = SessionLocal()
        self.provider = get_telephony_provider("mock")
        self.operator_comp1 = DummyStaffUser(user_id=101, emp_code="TEST101", name="Agent One", company_id=1, phone="9053899899")
        self.operator_comp2 = DummyStaffUser(user_id=202, emp_code="TEST202", name="Agent Two", company_id=2, phone="9888877777")
        self.created_sessions = []
        self.created_leads = []

        # Ensure clean state for test operators
        self.db.query(VoIPCallSession).filter(
            VoIPCallSession.operator_user_ref.in_(["TEST101", "TEST202", "101", "202"])
        ).delete()
        self.db.commit()

    def tearDown(self):
        # Clean up created test records
        try:
            for s_id in self.created_sessions:
                self.db.query(VoIPCallSession).filter(VoIPCallSession.call_session_id == s_id).delete()
            for l_id in self.created_leads:
                self.db.query(CRMLeadAuditLog).filter(CRMLeadAuditLog.lead_id == l_id).delete()
                self.db.query(CRMLead).filter(CRMLead.id == l_id).delete()
            self.db.query(VoIPCallSession).filter(
                VoIPCallSession.operator_user_ref.in_(["TEST101", "TEST202", "101", "202"])
            ).delete()
            self.db.commit()
        except Exception:
            self.db.rollback()
        finally:
            self.db.close()

    def _create_test_lead(self, company_id=1, phone="9703118501", name="Test Customer"):
        lead = CRMLead(
            company_id=company_id,
            name=name,
            phone=phone,
            status='new'
        )
        self.db.add(lead)
        self.db.commit()
        self.db.refresh(lead)
        self.created_leads.append(lead.id)
        return lead

    # ── 1. CALL CREATION TESTS ──────────────────────────────────────────────

    def test_01_create_valid_in_app_pstn_call(self):
        """Test successful call creation with valid lead and authorized operator"""
        lead = self._create_test_lead(company_id=1, phone="9703118501", name="John Doe")
        
        session = VoIPCallService.initiate_in_app_call(
            db=self.db,
            current_user=self.operator_comp1,
            customer_phone="9703118501",
            lead_id=lead.id,
            provider_name="mock"
        )
        self.created_sessions.append(session.call_session_id)

        # Verifications
        self.assertIsNotNone(session.id)
        self.assertTrue(session.call_session_id.startswith("vcs_"))
        self.assertEqual(session.status, CallStateEnum.DIALING.value)
        self.assertEqual(session.call_method, CallMethodEnum.IN_APP_PSTN.value)
        self.assertEqual(session.destination_number, "+919703118501")
        self.assertEqual(session.caller_id, "+912269470537")  # Dedicated MyntReal Business Number
        self.assertEqual(session.operator_name, "Agent One")
        self.assertEqual(session.customer_phone_masked, "******8501")
        self.assertIsNotNone(session.provider_call_id)
        self.assertIsNotNone(session.operator_call_id)

        # Verify OperatorCall link
        op_call = self.db.query(OperatorCall).filter(OperatorCall.id == session.operator_call_id).first()
        self.assertIsNotNone(op_call)
        self.assertEqual(op_call.call_type, "outbound")
        self.assertEqual(op_call.called_number, "+919703118501")

        # Verify CRM Lead Audit Log
        audit = self.db.query(CRMLeadAuditLog).filter(CRMLeadAuditLog.lead_id == lead.id).first()
        self.assertIsNotNone(audit)
        self.assertEqual(audit.field_name, "call_session_id")
        self.assertEqual(audit.change_category, "call")

    # ── 2. VALIDATION & ERROR HANDLING TESTS ────────────────────────────────

    def test_02_validation_invalid_phone_number(self):
        """Test that invalid phone numbers are rejected with 400 Bad Request"""
        invalid_numbers = ["123", "abcdef", "9999", "++91000"]
        for invalid_phone in invalid_numbers:
            with self.assertRaises(HTTPException) as ctx:
                VoIPCallService.initiate_in_app_call(
                    db=self.db,
                    current_user=self.operator_comp1,
                    customer_phone=invalid_phone,
                    provider_name="mock"
                )
            self.assertEqual(ctx.exception.status_code, 400)

    def test_03_validation_nonexistent_lead(self):
        """Test that nonexistent lead ID raises 404 Not Found"""
        with self.assertRaises(HTTPException) as ctx:
            VoIPCallService.initiate_in_app_call(
                db=self.db,
                current_user=self.operator_comp1,
                customer_phone="9703118501",
                lead_id=999999999,
                provider_name="mock"
            )
        self.assertEqual(ctx.exception.status_code, 404)

    def test_04_security_tenant_isolation_lead_access(self):
        """Test that an operator from Company 2 cannot call a lead belonging to Company 1"""
        lead_comp1 = self._create_test_lead(company_id=1, phone="9703118501")
        
        with self.assertRaises(HTTPException) as ctx:
            VoIPCallService.initiate_in_app_call(
                db=self.db,
                current_user=self.operator_comp2,  # Company 2 operator
                customer_phone="9703118501",
                lead_id=lead_comp1.id,            # Company 1 lead
                provider_name="mock"
            )
        self.assertEqual(ctx.exception.status_code, 403)

    # ── 3. STATE MACHINE & WEBHOOK TESTS ────────────────────────────────────

    def test_05_state_machine_lifecycle_via_webhooks(self):
        """Test complete lifecycle: CREATED -> DIALING -> RINGING -> ANSWERED -> ENDED"""
        session = VoIPCallService.initiate_in_app_call(
            db=self.db,
            current_user=self.operator_comp1,
            customer_phone="9876543210",
            provider_name="mock"
        )
        self.created_sessions.append(session.call_session_id)
        mock_p: MockTelephonyProvider = self.provider

        # 1. Simulate RINGING Webhook
        body, headers = mock_p.create_signed_webhook_payload({
            "provider_call_id": session.provider_call_id,
            "call_session_id": session.call_session_id,
            "status": "ringing"
        })
        res1 = VoIPCallService.process_telephony_webhook(self.db, headers, body, {}, provider_name="mock")
        self.assertTrue(res1["success"])
        self.db.refresh(session)
        self.assertEqual(session.status, CallStateEnum.RINGING.value)
        self.assertIsNotNone(session.ringing_at)

        # 2. Simulate ANSWERED / CONNECTED Webhook
        body, headers = mock_p.create_signed_webhook_payload({
            "provider_call_id": session.provider_call_id,
            "call_session_id": session.call_session_id,
            "status": "answered"
        })
        res2 = VoIPCallService.process_telephony_webhook(self.db, headers, body, {}, provider_name="mock")
        self.assertTrue(res2["success"])
        self.db.refresh(session)
        self.assertEqual(session.status, CallStateEnum.ANSWERED.value)
        self.assertIsNotNone(session.answered_at)

        # 3. Simulate ENDED Webhook with duration and recording
        body, headers = mock_p.create_signed_webhook_payload({
            "provider_call_id": session.provider_call_id,
            "call_session_id": session.call_session_id,
            "status": "ended",
            "duration_seconds": 125,
            "termination_reason": "customer_hangup",
            "recording_status": "available",
            "recording_url": f"https://mock-telephony.local/rec/{session.provider_call_id}.mp3"
        })
        res3 = VoIPCallService.process_telephony_webhook(self.db, headers, body, {}, provider_name="mock")
        self.assertTrue(res3["success"])
        self.db.refresh(session)
        self.assertEqual(session.status, CallStateEnum.ENDED.value)
        self.assertEqual(session.duration_seconds, 125)
        self.assertEqual(session.termination_reason, "customer_hangup")
        self.assertEqual(session.recording_status, RecordingStatusEnum.AVAILABLE.value)
        self.assertIsNotNone(session.recording_storage_key)

    def test_06_state_machine_distinct_terminal_outcomes(self):
        """Test distinct terminal states: BUSY, NO_ANSWER, REJECTED, FAILED"""
        terminal_outcomes = [
            ("busy", CallStateEnum.BUSY),
            ("no_answer", CallStateEnum.NO_ANSWER),
            ("rejected", CallStateEnum.REJECTED),
            ("failed", CallStateEnum.FAILED)
        ]
        mock_p: MockTelephonyProvider = self.provider

        for status_str, expected_enum in terminal_outcomes:
            session = VoIPCallService.initiate_in_app_call(
                db=self.db,
                current_user=self.operator_comp1,
                customer_phone="9988776655",
                provider_name="mock"
            )
            self.created_sessions.append(session.call_session_id)

            body, headers = mock_p.create_signed_webhook_payload({
                "provider_call_id": session.provider_call_id,
                "status": status_str,
                "termination_reason": f"telephony_{status_str}"
            })
            VoIPCallService.process_telephony_webhook(self.db, headers, body, {}, provider_name="mock")
            self.db.refresh(session)
            self.assertEqual(session.status, expected_enum.value)
            self.assertTrue(CallStateEnum(session.status).is_terminal())

    # ── 4. WEBHOOK SIGNATURE & IDEMPOTENCY TESTS ────────────────────────────

    def test_07_webhook_signature_verification_failure(self):
        """Test that webhooks with invalid HMAC signature are rejected"""
        invalid_headers = {
            "Content-Type": "application/json",
            "X-Telephony-Signature": "tampered_invalid_signature"
        }
        body = json.dumps({"provider_call_id": "test_123", "status": "ended"}).encode('utf-8')
        
        result = VoIPCallService.process_telephony_webhook(self.db, invalid_headers, body, {}, provider_name="mock")
        self.assertFalse(result["success"])
        self.assertIn("signature", result["error"].lower())

    def test_08_webhook_idempotency_duplicate_delivery(self):
        """Test that duplicate webhook deliveries are processed idempotently without duplicating data"""
        session = VoIPCallService.initiate_in_app_call(
            db=self.db,
            current_user=self.operator_comp1,
            customer_phone="9123456780",
            provider_name="mock"
        )
        self.created_sessions.append(session.call_session_id)
        mock_p: MockTelephonyProvider = self.provider

        body, headers = mock_p.create_signed_webhook_payload({
            "provider_call_id": session.provider_call_id,
            "status": "ended",
            "duration_seconds": 45
        })

        # Send webhook 3 times
        res1 = VoIPCallService.process_telephony_webhook(self.db, headers, body, {}, provider_name="mock")
        res2 = VoIPCallService.process_telephony_webhook(self.db, headers, body, {}, provider_name="mock")
        res3 = VoIPCallService.process_telephony_webhook(self.db, headers, body, {}, provider_name="mock")

        self.assertTrue(res1["success"])
        self.assertTrue(res2["success"])
        self.assertTrue(res3["success"])

        # Ensure session count is still 1
        count = self.db.query(VoIPCallSession).filter(VoIPCallSession.call_session_id == session.call_session_id).count()
        self.assertEqual(count, 1)

    def test_09_webhook_out_of_order_protection(self):
        """Test that non-terminal webhook does not overwrite an already terminal call state"""
        session = VoIPCallService.initiate_in_app_call(
            db=self.db,
            current_user=self.operator_comp1,
            customer_phone="9333322221",
            provider_name="mock"
        )
        self.created_sessions.append(session.call_session_id)
        mock_p: MockTelephonyProvider = self.provider

        # First mark call as ENDED
        body_ended, headers_ended = mock_p.create_signed_webhook_payload({
            "provider_call_id": session.provider_call_id,
            "status": "ended",
            "duration_seconds": 60
        })
        VoIPCallService.process_telephony_webhook(self.db, headers_ended, body_ended, {}, provider_name="mock")
        self.db.refresh(session)
        self.assertEqual(session.status, CallStateEnum.ENDED.value)

        # Now send a delayed/out-of-order RINGING webhook
        body_ringing, headers_ringing = mock_p.create_signed_webhook_payload({
            "provider_call_id": session.provider_call_id,
            "status": "ringing"
        })
        VoIPCallService.process_telephony_webhook(self.db, headers_ringing, body_ringing, {}, provider_name="mock")
        self.db.refresh(session)

        # Must remain ENDED (no regression to RINGING)
        self.assertEqual(session.status, CallStateEnum.ENDED.value)

    # ── 5. CONCURRENCY & DOUBLE-DIAL PROTECTION ─────────────────────────────

    def test_10_concurrency_double_dial_protection(self):
        """Test that rapid retry/double-click returns existing active session without creating duplicate"""
        session1 = VoIPCallService.initiate_in_app_call(
            db=self.db,
            current_user=self.operator_comp1,
            customer_phone="9555544443",
            provider_name="mock"
        )
        self.created_sessions.append(session1.call_session_id)

        # Second rapid dial attempt by same operator to same phone while DIALING
        session2 = VoIPCallService.initiate_in_app_call(
            db=self.db,
            current_user=self.operator_comp1,
            customer_phone="9555544443",
            provider_name="mock"
        )

        # Must return the same existing active session ID
        self.assertEqual(session1.call_session_id, session2.call_session_id)

    # ── 6. SECURE RECORDING ACCESS & PLAYBACK TESTS ─────────────────────────

    def test_11_secure_presigned_recording_url_generation(self):
        """Test generation of short-lived signed S3 URL for private recording playback"""
        lead = self._create_test_lead(company_id=1, phone="9444433332")
        session = VoIPCallService.initiate_in_app_call(
            db=self.db,
            current_user=self.operator_comp1,
            customer_phone="9444433332",
            lead_id=lead.id,
            provider_name="mock"
        )
        self.created_sessions.append(session.call_session_id)
        mock_p: MockTelephonyProvider = self.provider

        # Complete call with recording
        body, headers = mock_p.create_signed_webhook_payload({
            "provider_call_id": session.provider_call_id,
            "status": "ended",
            "duration_seconds": 88,
            "recording_status": "available",
            "recording_url": "https://mock.local/test.mp3"
        })
        VoIPCallService.process_telephony_webhook(self.db, headers, body, {}, provider_name="mock")

        # Fetch signed recording playback URL
        rec_data = VoIPCallService.get_recording_signed_url(
            db=self.db,
            current_user=self.operator_comp1,
            call_session_id=session.call_session_id,
            expiration=900
        )
        self.assertTrue(rec_data["success"])
        self.assertIsNotNone(rec_data["playback_url"])
        self.assertEqual(rec_data["expires_in_seconds"], 900)

    def test_12_security_cross_company_recording_access_blocked(self):
        """Test that an operator from Company 2 cannot access recording of Company 1 session"""
        session = VoIPCallService.initiate_in_app_call(
            db=self.db,
            current_user=self.operator_comp1,  # Company 1
            customer_phone="9222211110",
            provider_name="mock"
        )
        self.created_sessions.append(session.call_session_id)
        mock_p: MockTelephonyProvider = self.provider

        # Mark recording available
        body, headers = mock_p.create_signed_webhook_payload({
            "provider_call_id": session.provider_call_id,
            "status": "ended",
            "recording_status": "available",
            "recording_url": "https://mock.local/test.mp3"
        })
        VoIPCallService.process_telephony_webhook(self.db, headers, body, {}, provider_name="mock")

        # Company 2 operator attempts access -> 403 Forbidden
        with self.assertRaises(HTTPException) as ctx:
            VoIPCallService.get_recording_signed_url(
                db=self.db,
                current_user=self.operator_comp2,
                call_session_id=session.call_session_id
            )
        self.assertEqual(ctx.exception.status_code, 403)


if __name__ == '__main__':
    unittest.main()
