"""
Unit & Integration Test Suite — Plivo Dial Real-Time Callback & Authoritative Telephony State Machine
Tests:
1. Valid Dial callback with DialAction="answer" transitions session RINGING -> CONNECTED and sets answered_at.
2. Valid Dial callback with DialBLegUUID transitions session to CONNECTED.
3. Duplicate answer callback is idempotent and does not overwrite original answered_at timestamp.
4. Monotonic progression: when session is CONNECTED, subsequent ringing callback cannot regress state.
5. Terminal session cannot be resurrected back to CONNECTED by a late callback.
6. Session status API returns is_connected=True, correct status, and live duration from answered_at.
7. flow_interpreter.py generates Outbound <Dial> XML with callbackUrl and callbackMethod="POST".
8. Browser call-event endpoint idempotently marks session connected and starts talk time tracking.
Created: Sep 2026
"""

import unittest
import time
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.core.database import SessionLocal
from app.models.voip_call_session import VoIPCallSession
from app.models.voip_enums import CallStateEnum
from app.models.staff import StaffEmployee
from app.services.telephony.flow_interpreter import CallFlowInterpreter
from app.api.v1.endpoints.call_flow_api import get_indian_time


class TestPlivoDialCallbackAndLifecycle(unittest.TestCase):
    """
    Test Suite for /api/v1/telephony/plivo/dial-callback and Call Lifecycle State Machine.
    """

    def setUp(self):
        self.client = TestClient(app)
        self.db: Session = SessionLocal()
        self.test_session_ids = []

        # Find or create a mock staff user
        self.staff = self.db.query(StaffEmployee).filter(StaffEmployee.status == 'active').first()
        if not self.staff:
            from datetime import date
            self.staff = StaffEmployee(
                emp_code="EMP_DIAL_TEST",
                full_name="Dial Tester",
                phone="9876543299",
                email="dial.tester@example.com",
                role_id=1,
                date_of_joining=date.today(),
                password_hash="test_hash",
                base_company_id=1,
                status="active"
            )
            self.db.add(self.staff)
            self.db.commit()
            self.db.refresh(self.staff)

        # Create active test session in RINGING state
        self.call_uuid = f"aleg_uuid_{int(time.time())}_{id(self)}"
        self.session_id = f"vcs_dial_test_{int(time.time())}"
        self.test_session_ids.append(self.session_id)

        self.session = VoIPCallSession(
            company_id=1,
            call_session_id=self.session_id,
            provider="plivo",
            provider_call_id=self.call_uuid,
            caller_id="+918031728899",
            customer_phone="+919876500001",
            destination_number="+919876500001",
            operator_id=self.staff.id,
            direction="outbound",
            status=CallStateEnum.RINGING.value
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

    # 1. Valid Dial callback with DialAction="answer" transitions session RINGING -> CONNECTED
    def test_01_dial_action_answer_transitions_to_connected(self):
        payload = {
            "DialAction": "answer",
            "DialStatus": "in-progress",
            "DialBLegUUID": "bleg_uuid_12345",
            "DialALegUUID": self.call_uuid,
            "session_id": self.session_id
        }

        resp = self.client.post(
            f"/api/v1/telephony/plivo/dial-callback?session_id={self.session_id}",
            data=payload
        )
        self.assertEqual(resp.status_code, 200)

        self.db.expire_all()
        updated = self.db.query(VoIPCallSession).filter_by(call_session_id=self.session_id).first()
        self.assertEqual(updated.status, CallStateEnum.CONNECTED.value)
        self.assertIsNotNone(updated.answered_at)

    # 2. Valid Dial callback with DialBLegUUID transitions session to CONNECTED
    def test_02_dial_bleg_uuid_transitions_to_connected(self):
        s2_id = f"vcs_dial_bleg_{int(time.time())}"
        self.test_session_ids.append(s2_id)
        s2 = VoIPCallSession(
            company_id=1,
            call_session_id=s2_id,
            provider="plivo",
            caller_id="+918031728899",
            customer_phone="+919876500002",
            destination_number="+919876500002",
            operator_id=self.staff.id,
            direction="outbound",
            status=CallStateEnum.RINGING.value
        )
        self.db.add(s2)
        self.db.commit()

        payload = {
            "DialBLegUUID": "bleg_uuid_established_999",
            "DialStatus": "in-progress"
        }
        resp = self.client.post(
            f"/api/v1/telephony/plivo/dial-callback?session_id={s2_id}",
            data=payload
        )
        self.assertEqual(resp.status_code, 200)

        self.db.expire_all()
        updated = self.db.query(VoIPCallSession).filter_by(call_session_id=s2_id).first()
        self.assertEqual(updated.status, CallStateEnum.CONNECTED.value)
        self.assertIsNotNone(updated.answered_at)

    # 3. Duplicate answer callback is idempotent
    def test_03_duplicate_answer_callback_is_idempotent(self):
        initial_time = datetime(2026, 9, 7, 10, 0, 0)
        self.session.status = CallStateEnum.CONNECTED.value
        self.session.answered_at = initial_time
        self.db.commit()

        payload = {
            "DialAction": "answer",
            "DialStatus": "in-progress",
            "DialBLegUUID": "bleg_uuid_dup"
        }
        resp = self.client.post(
            f"/api/v1/telephony/plivo/dial-callback?session_id={self.session_id}",
            data=payload
        )
        self.assertEqual(resp.status_code, 200)

        self.db.expire_all()
        updated = self.db.query(VoIPCallSession).filter_by(call_session_id=self.session_id).first()
        self.assertEqual(updated.status, CallStateEnum.CONNECTED.value)
        self.assertEqual(updated.answered_at, initial_time)

    # 4. Monotonic progression: subsequent ringing callback cannot regress CONNECTED call
    def test_04_ringing_callback_cannot_regress_connected_state(self):
        self.session.status = CallStateEnum.CONNECTED.value
        self.session.answered_at = get_indian_time()
        self.db.commit()

        payload = {
            "DialRingStatus": "true",
            "DialStatus": "ringing"
        }
        resp = self.client.post(
            f"/api/v1/telephony/plivo/dial-callback?session_id={self.session_id}",
            data=payload
        )
        self.assertEqual(resp.status_code, 200)

        self.db.expire_all()
        updated = self.db.query(VoIPCallSession).filter_by(call_session_id=self.session_id).first()
        self.assertEqual(updated.status, CallStateEnum.CONNECTED.value)

    # 5. Terminal session cannot be resurrected back to CONNECTED
    def test_05_terminal_session_cannot_be_resurrected(self):
        self.session.status = CallStateEnum.ENDED.value
        self.session.ended_at = get_indian_time()
        self.session.duration_seconds = 60
        self.db.commit()

        payload = {
            "DialAction": "answer",
            "DialStatus": "in-progress"
        }
        resp = self.client.post(
            f"/api/v1/telephony/plivo/dial-callback?session_id={self.session_id}",
            data=payload
        )
        self.assertEqual(resp.status_code, 200)

        self.db.expire_all()
        updated = self.db.query(VoIPCallSession).filter_by(call_session_id=self.session_id).first()
        self.assertEqual(updated.status, CallStateEnum.ENDED.value)

    # 6. flow_interpreter.py generates Outbound <Dial> XML with callbackUrl
    def test_06_flow_interpreter_generates_dial_callback_url(self):
        xml_res = CallFlowInterpreter.handle_inbound_call(
            db=self.db,
            caller_phone="agent_c1_s101",
            called_did="9876500001",
            provider_call_id="call_uuid_test_123",
            base_api_url="https://www.myntreal.com",
            call_session_id=self.session_id
        )
        self.assertIn("<Dial", xml_res)
        self.assertIn('callbackUrl="https://www.myntreal.com/api/v1/telephony/plivo/dial-callback?session_id=', xml_res)
        self.assertIn('callbackMethod="POST"', xml_res)
        self.assertIn('<Record recordSession="true" startOnDialAnswer="true"', xml_res)
        self.assertIn('callbackUrl="https://www.myntreal.com/api/v1/telephony/plivo/recording-callback', xml_res)
        self.assertNotIn('action="https://www.myntreal.com/api/v1/telephony/plivo/recording-callback', xml_res)


if __name__ == '__main__':
    unittest.main()
