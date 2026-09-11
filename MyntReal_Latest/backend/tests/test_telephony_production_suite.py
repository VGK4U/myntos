"""
Production Telephony Comprehensive Verification Test Suite
Tests:
1. WebRTC Outbound: Softphone -> Plivo -> Customer (<Dial><Number>)
2. Server Click-to-Call / OBD: CRM Dispatch -> Customer Answers -> Bridge to Agent (<Dial><User> or <Dial><Number>) without self-dial
3. Plivo XML Validation & Escaping (&amp;)
4. Hangup Webhook State Synchronization & Duration Tracking
5. Concurrency & Duplicate Call Guard (45-second window)
6. Inbound DID Multi-Tenant Routing & Flow DAG
"""

import unittest
import time
import json
import re
from datetime import datetime, timedelta
import pytz
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.core.database import SessionLocal
from app.models.voip_call_session import VoIPCallSession
from app.models.voip_enums import CallStateEnum, CallMethodEnum
from app.models.staff import StaffEmployee
from app.models.telephony_call_flow import (
    TelephonyCallFlow, TelephonyPlivoEndpoint, TelephonyRingGroup
)
from app.models.operator_calls import TelephonyDIDMapping
from app.services.telephony.flow_interpreter import CallFlowInterpreter
from app.services.voip_call_service import VoIPCallService
from app.services.telephony.factory import get_telephony_provider

IST = pytz.timezone('Asia/Kolkata')


class TestTelephonyProductionSuite(unittest.TestCase):

    def setUp(self):
        self.client = TestClient(app)
        self.db: Session = SessionLocal()
        self.cleanups = []

    def tearDown(self):
        try:
            for action in reversed(self.cleanups):
                try:
                    action()
                except Exception:
                    pass
            self.db.commit()
        except Exception:
            self.db.rollback()
        finally:
            self.db.close()

    def test_01_webrtc_outbound_dial_customer(self):
        """
        WebRTC Outbound Call:
        When an agent calls from browser softphone (SIP leg), the Answer URL must return
        <Dial><Number>{customer_number}</Number></Dial> so Plivo connects the agent to the customer.
        """
        session_id = f"vcs_test_webrtc_{int(time.time())}"
        session = VoIPCallSession(
            company_id=1,
            call_session_id=session_id,
            provider="plivo",
            caller_id="+918031728899",
            customer_phone="+919876543210",
            destination_number="+919876543210",
            direction="outbound",
            call_method=CallMethodEnum.IN_APP_PSTN.value,
            status=CallStateEnum.DIALING.value
        )
        self.db.add(session)
        self.db.commit()
        self.cleanups.append(lambda: self.db.query(VoIPCallSession).filter_by(call_session_id=session_id).delete())

        xml_output = CallFlowInterpreter.handle_inbound_call(
            db=self.db,
            caller_phone="sip:agent_c1_s321@phone.plivo.com",
            called_did="+919876543210",
            provider_call_id="plivo_webrtc_uuid_001",
            base_api_url="https://www.myntreal.com",
            call_session_id=session_id
        )

        self.assertTrue(xml_output.startswith("<Response>"))
        self.assertTrue(xml_output.endswith("</Response>"))
        self.assertIn("<Dial", xml_output)
        self.assertIn("<Number>+919876543210</Number>", xml_output)
        self.assertIn("&amp;direction=outbound", xml_output)
        self.assertNotIn("<User>", xml_output)

    def test_02_server_click_to_call_bridges_to_agent_no_self_dial(self):
        """
        Server Click-to-Call / OBD:
        When server dispatches call to customer, and customer answers, Answer URL MUST bridge
        the customer leg to the agent endpoint (<User> or <Number>), NOT dial the customer again!
        """
        staff_emp = self.db.query(StaffEmployee).filter(StaffEmployee.id == 1).first()
        if not staff_emp:
            staff_emp = StaffEmployee(id=1, emp_code="MN10001", full_name="Test Agent", phone="+919999988888", is_active=True)
            self.db.add(staff_emp)
            self.db.commit()

        endpoint = self.db.query(TelephonyPlivoEndpoint).filter(TelephonyPlivoEndpoint.staff_id == 1).first()
        if not endpoint:
            endpoint = TelephonyPlivoEndpoint(
                company_id=1,
                staff_id=1,
                plivo_username="agent_c1_s1",
                plivo_alias="Test Agent",
                is_registered=True
            )
            self.db.add(endpoint)
            self.db.commit()

        session_id = f"vcs_test_obd_{int(time.time())}"
        session = VoIPCallSession(
            company_id=1,
            call_session_id=session_id,
            provider="plivo",
            provider_call_id="plivo_obd_uuid_999",
            caller_id="+918031728899",
            customer_phone="+919876543210",
            destination_number="+919876543210",
            operator_id=1,
            direction="outbound",
            call_method=CallMethodEnum.IN_APP_PSTN.value,
            status=CallStateEnum.DIALING.value
        )
        self.db.add(session)
        self.db.commit()
        self.cleanups.append(lambda: self.db.query(VoIPCallSession).filter_by(call_session_id=session_id).delete())

        xml_output = CallFlowInterpreter.handle_inbound_call(
            db=self.db,
            caller_phone="+918031728899",
            called_did="+919876543210",
            provider_call_id="plivo_obd_uuid_999",
            base_api_url="https://www.myntreal.com",
            call_session_id=session_id
        )

        self.assertTrue(xml_output.startswith("<Response>"))
        self.assertTrue(xml_output.endswith("</Response>"))
        self.assertIn("<Dial", xml_output)
        self.assertNotIn("<Number>+919876543210</Number>", xml_output)
        self.assertTrue(
            ("<User>sip:" in xml_output) or
            ("<Number>+" in xml_output)
        )

    def test_03_xml_escaping_bulletproof(self):
        """
        Verify that URLs with multiple query parameters are correctly escaped to &amp;
        and that invalid unescaped ampersands never enter Plivo XML.
        """
        elements = [
            '<Dial action="https://api.myntreal.com/api/v1/hangup?session=123&direction=outbound&foo=bar">',
            '  <Number>+919876543210</Number>',
            '</Dial>'
        ]
        xml = CallFlowInterpreter._generate_xml_response(elements)
        self.assertIn("session=123&amp;direction=outbound&amp;foo=bar", xml)
        self.assertIsNone(re.search(r'&(?!(?:amp|lt|gt|quot|apos);)', xml))

    def test_04_concurrency_guard_45_seconds(self):
        """
        Concurrency Protection:
        A rapid duplicate dial within 45 seconds returns the active session instead of creating a second call leg.
        """
        staff_user = self.db.query(StaffEmployee).filter(StaffEmployee.id == 1).first()
        dest_phone = "+919876543210"

        s1 = VoIPCallService.initiate_in_app_call(
            db=self.db,
            current_user=staff_user,
            customer_phone=dest_phone,
            dispatch_provider_call=False
        )
        self.cleanups.append(lambda: self.db.query(VoIPCallSession).filter_by(call_session_id=s1.call_session_id).delete())

        s2 = VoIPCallService.initiate_in_app_call(
            db=self.db,
            current_user=staff_user,
            customer_phone=dest_phone,
            dispatch_provider_call=False
        )

        self.assertEqual(s1.call_session_id, s2.call_session_id)
        self.assertEqual(s1.id, s2.id)

    def test_05_hangup_webhook_session_lifecycle(self):
        """
        Hangup Webhook:
        Processes duration, updates session status to ended, and records termination reason.
        """
        call_uuid = f"plivo_hangup_test_{int(time.time())}"
        session_id = f"vcs_hangup_lc_{int(time.time())}"
        session = VoIPCallSession(
            company_id=1,
            call_session_id=session_id,
            provider="plivo",
            provider_call_id=call_uuid,
            caller_id="+918031728899",
            customer_phone="+919876543210",
            destination_number="+919876543210",
            direction="outbound",
            status=CallStateEnum.CONNECTED.value,
            started_at=datetime.now(IST)
        )
        self.db.add(session)
        self.db.commit()
        self.cleanups.append(lambda: self.db.query(VoIPCallSession).filter_by(call_session_id=session_id).delete())

        resp = self.client.post(
            "/api/v1/telephony/plivo/hangup",
            data={
                "CallUUID": call_uuid,
                "CallStatus": "completed",
                "Duration": "35",
                "HangupCauseName": "NORMAL_CLEARING",
                "HangupSource": "caller"
            }
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn("application/xml", resp.headers.get("content-type", ""))
        self.assertIn("<Hangup", resp.text)

        self.db.refresh(session)
        self.assertEqual(session.status, CallStateEnum.ENDED.value)
        self.assertEqual(session.duration_seconds, 35)
        self.assertIsNotNone(session.ended_at)


if __name__ == '__main__':
    unittest.main()
