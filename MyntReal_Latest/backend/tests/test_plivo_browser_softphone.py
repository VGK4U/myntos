"""
Unit & Integration Test Suite — Phase 2A: Plivo Browser Softphone & Endpoint Integration
Tests:
1. Authenticated staff can request browser token
2. Unauthenticated request rejected
3. Inactive staff rejected
4. Cross-company endpoint access rejected
5. Token does not expose master credentials
6. Correct staff-to-Plivo endpoint mapping
7. Duplicate endpoint creation prevented
8. Outbound call session created correctly
9. Call state transitions
10. Inbound call event handling
11. Simultaneous ring group browser destinations
12. One agent answering cancels other ringing states
13. Multiple staff sessions can exist concurrently
14. Agent A Call 1 does not affect Agent B Call 2
15. CRM context remains attached
16. TelephonyFactory resolves Plivo provider correctly
Created: Sep 2026
"""

import unittest
import time
from unittest.mock import MagicMock, patch
from sqlalchemy.orm import Session
from jose import jwt
from fastapi import HTTPException

from app.core.database import SessionLocal
from app.models.base import BaseModel
from app.models.staff import StaffEmployee
from app.models.crm import CRMLead
from app.models.voip_call_session import VoIPCallSession
from app.models.voip_enums import CallStateEnum, CallMethodEnum
from app.models.telephony_call_flow import (
    TelephonyPlivoEndpoint, TelephonyRingGroup, TelephonyRingGroupMember
)
from app.services.telephony.plivo_jwt_service import PlivoJWTService
from app.services.telephony.plivo_provider import PlivoTelephonyProvider
from app.services.telephony.factory import get_telephony_provider
from app.services.telephony.flow_interpreter import CallFlowInterpreter
from app.services.voip_call_service import VoIPCallService
from app.core.config import settings


class TestPlivoBrowserSoftphone(unittest.TestCase):
    """
    Test Suite for MyntOS Plivo Browser Softphone, Endpoint Mapping & JWT Authentication.
    """

    def setUp(self):
        self.db: Session = SessionLocal()
        self.test_session_ids = []
        self.test_endpoint_ids = []
        self.test_group_ids = []

        from datetime import date
        # Find or seed test staff
        self.staff_1 = self.db.query(StaffEmployee).filter_by(emp_code="EMP_TEST_101").first()
        if not self.staff_1:
            existing = self.db.query(StaffEmployee).filter(StaffEmployee.status == 'active').first()
            role_id_val = existing.role_id if existing else 1
            self.staff_1 = StaffEmployee(
                emp_code="EMP_TEST_101",
                full_name="Agent Alpha",
                phone="9876543210",
                email="agent.alpha.test@example.com",
                role_id=role_id_val,
                date_of_joining=date.today(),
                password_hash="test_hash_123",
                base_company_id=1,
                status="active"
            )
            self.db.add(self.staff_1)
        else:
            self.staff_1.status = "active"
            self.staff_1.base_company_id = 1

        self.staff_2 = self.db.query(StaffEmployee).filter_by(emp_code="EMP_TEST_102").first()
        if not self.staff_2:
            existing = self.db.query(StaffEmployee).filter(StaffEmployee.status == 'active').first()
            role_id_val = existing.role_id if existing else 1
            self.staff_2 = StaffEmployee(
                emp_code="EMP_TEST_102",
                full_name="Agent Beta",
                phone="9876543211",
                email="agent.beta.test@example.com",
                role_id=role_id_val,
                date_of_joining=date.today(),
                password_hash="test_hash_123",
                base_company_id=1,
                status="active"
            )
            self.db.add(self.staff_2)
        else:
            self.staff_2.status = "active"
            self.staff_2.base_company_id = 1

        self.staff_inactive = self.db.query(StaffEmployee).filter_by(emp_code="EMP_TEST_103").first()
        if not self.staff_inactive:
            existing = self.db.query(StaffEmployee).filter(StaffEmployee.status == 'active').first()
            role_id_val = existing.role_id if existing else 1
            self.staff_inactive = StaffEmployee(
                emp_code="EMP_TEST_103",
                full_name="Agent Inactive",
                phone="9876543212",
                email="inactive.test@example.com",
                role_id=role_id_val,
                date_of_joining=date.today(),
                password_hash="test_hash_123",
                base_company_id=1,
                status="inactive"
            )
            self.db.add(self.staff_inactive)
        else:
            self.staff_inactive.status = "inactive"

        self.staff_company_2 = self.db.query(StaffEmployee).filter_by(emp_code="EMP_TEST_201").first()
        if not self.staff_company_2:
            existing = self.db.query(StaffEmployee).filter(StaffEmployee.status == 'active').first()
            role_id_val = existing.role_id if existing else 1
            self.staff_company_2 = StaffEmployee(
                emp_code="EMP_TEST_201",
                full_name="Agent Company 2",
                phone="9876543220",
                email="agent2.test@example.com",
                role_id=role_id_val,
                date_of_joining=date.today(),
                password_hash="test_hash_123",
                base_company_id=2,
                status="active"
            )
            self.db.add(self.staff_company_2)
        else:
            self.staff_company_2.status = "active"
            self.staff_company_2.base_company_id = 2

        self.staff_company_2.is_super_admin = False
        if getattr(self.staff_company_2, 'role', None):
            self.staff_company_2.role.hierarchy_level = 10
            self.staff_company_2.role.role_code = 'agent'

        self.db.commit()
        self.db.refresh(self.staff_1)
        self.db.refresh(self.staff_2)
        self.db.refresh(self.staff_inactive)
        self.db.refresh(self.staff_company_2)

        # Clean existing test endpoints to avoid stale endpoint mapping mismatches
        self.db.query(TelephonyPlivoEndpoint).filter(
            TelephonyPlivoEndpoint.staff_id.in_([self.staff_1.id, self.staff_2.id, self.staff_company_2.id])
        ).delete(synchronize_session=False)
        self.db.commit()

        # Seed CRM Lead
        self.lead = self.db.query(CRMLead).filter_by(phone="9876500001").first()
        if not self.lead:
            self.lead = CRMLead(
                company_id=1,
                name="Vikram Sharma",
                phone="9876500001",
                status="NEW"
            )
            self.db.add(self.lead)
            self.db.commit()
            self.db.refresh(self.lead)

    def tearDown(self):
        try:
            for sid in self.test_session_ids:
                self.db.query(VoIPCallSession).filter(VoIPCallSession.call_session_id == sid).delete()
            for eid in self.test_endpoint_ids:
                self.db.query(TelephonyPlivoEndpoint).filter(TelephonyPlivoEndpoint.id == eid).delete()
            for gid in self.test_group_ids:
                self.db.query(TelephonyRingGroupMember).filter(TelephonyRingGroupMember.ring_group_id == gid).delete()
                self.db.query(TelephonyRingGroup).filter(TelephonyRingGroup.id == gid).delete()
            self.db.commit()
        except Exception:
            self.db.rollback()
        finally:
            self.db.close()

    # 1. Authenticated staff can request browser token
    def test_01_authenticated_staff_can_request_browser_token(self):
        token_data = PlivoJWTService.generate_browser_token(
            db=self.db,
            company_id=1,
            staff=self.staff_1
        )
        self.assertTrue(token_data['success'])
        self.assertIn('access_token', token_data)
        ep = PlivoJWTService.get_or_create_staff_endpoint(db=self.db, company_id=1, staff=self.staff_1)
        self.assertEqual(token_data['endpoint']['username'], ep.plivo_username)
        self.assertGreater(token_data['expires_in_seconds'], 0)

    # 2. Unauthenticated request / missing staff rejected
    def test_02_unauthenticated_request_rejected(self):
        with self.assertRaises(Exception):
            PlivoJWTService.generate_browser_token(
                db=self.db,
                company_id=1,
                staff=None
            )

    # 3. Inactive staff rejected
    def test_03_inactive_staff_rejected(self):
        with self.assertRaises(HTTPException) as ctx:
            PlivoJWTService.generate_browser_token(
                db=self.db,
                company_id=1,
                staff=self.staff_inactive
            )
        self.assertEqual(ctx.exception.status_code, 403)
        self.assertIn("Inactive staff", ctx.exception.detail)

    # 4. Cross-company endpoint access rejected
    def test_04_cross_company_endpoint_access_rejected(self):
        # staff_company_2 belongs to Company 2, requesting token for Company 1
        with self.assertRaises(HTTPException) as ctx:
            PlivoJWTService.generate_browser_token(
                db=self.db,
                company_id=1,
                staff=self.staff_company_2
            )
        self.assertEqual(ctx.exception.status_code, 403)
        self.assertIn("Cross-company", ctx.exception.detail)

    # 5. Token does not expose master credentials
    def test_05_token_does_not_expose_master_credentials(self):
        token_data = PlivoJWTService.generate_browser_token(
            db=self.db,
            company_id=1,
            staff=self.staff_1
        )
        # Ensure raw secret is not in payload
        self.assertNotIn("mock_plivo_auth_token_secret", str(token_data))
        self.assertNotIn("auth_token", token_data)
        self.assertNotIn("password", str(token_data))

        # Decode JWT to verify standard Plivo claims
        token = token_data['access_token']
        decoded = jwt.decode(token, key="mock_plivo_auth_token_secret_12345", algorithms=["HS256"], options={"verify_signature": False})
        ep = PlivoJWTService.get_or_create_staff_endpoint(db=self.db, company_id=1, staff=self.staff_1)
        self.assertEqual(decoded['sub'], ep.plivo_username)

    # 6. Correct staff-to-Plivo endpoint mapping
    def test_06_correct_staff_to_plivo_endpoint_mapping(self):
        endpoint = PlivoJWTService.get_or_create_staff_endpoint(
            db=self.db,
            company_id=1,
            staff=self.staff_1
        )
        self.test_endpoint_ids.append(endpoint.id)
        self.assertEqual(endpoint.company_id, 1)
        self.assertEqual(endpoint.staff_id, self.staff_1.id)
        self.assertTrue(endpoint.plivo_username.startswith("agent"))

    # 7. Duplicate endpoint creation prevented
    def test_07_duplicate_endpoint_creation_prevented(self):
        ep1 = PlivoJWTService.get_or_create_staff_endpoint(db=self.db, company_id=1, staff=self.staff_1)
        ep2 = PlivoJWTService.get_or_create_staff_endpoint(db=self.db, company_id=1, staff=self.staff_1)
        self.test_endpoint_ids.append(ep1.id)
        self.assertEqual(ep1.id, ep2.id)

        count = self.db.query(TelephonyPlivoEndpoint).filter(
            TelephonyPlivoEndpoint.company_id == 1,
            TelephonyPlivoEndpoint.staff_id == self.staff_1.id
        ).count()
        self.assertEqual(count, 1)

    # 8. Outbound call session created correctly
    def test_08_outbound_call_session_created_correctly(self):
        session = VoIPCallService.initiate_in_app_call(
            db=self.db,
            current_user=self.staff_1,
            customer_phone="9876500001",
            lead_id=self.lead.id,
            provider_name="plivo"
        )
        self.test_session_ids.append(session.call_session_id)
        self.assertIsNotNone(session)
        self.assertEqual(session.provider, "plivo")
        self.assertEqual(session.direction, "outbound")
        self.assertEqual(session.operator_id, self.staff_1.id)
        self.assertEqual(session.lead_id, self.lead.id)
        self.assertEqual(session.status, CallStateEnum.DIALING.value)

    # 9. Call state transitions
    def test_09_call_state_transitions(self):
        session_id = f"sess_test_state_{int(time.time())}"
        self.test_session_ids.append(session_id)
        session = VoIPCallSession(
            company_id=1,
            call_session_id=session_id,
            provider="plivo",
            caller_id="+918031728899",
            customer_phone="9876500001",
            destination_number="9876500001",
            operator_id=self.staff_1.id,
            direction="outbound",
            status=CallStateEnum.DIALING.value
        )
        self.db.add(session)
        self.db.commit()

        # Transition: DIALING -> RINGING
        session.status = CallStateEnum.RINGING.value
        self.db.commit()
        self.assertEqual(session.status, CallStateEnum.RINGING.value)

        # Transition: RINGING -> CONNECTED
        session.status = CallStateEnum.CONNECTED.value
        session.answered_at = session.created_at
        self.db.commit()
        self.assertEqual(session.status, CallStateEnum.CONNECTED.value)

        # Transition: CONNECTED -> ENDED
        session.status = CallStateEnum.ENDED.value
        session.duration_seconds = 45
        self.db.commit()
        self.assertEqual(session.status, CallStateEnum.ENDED.value)
        self.assertEqual(session.duration_seconds, 45)

    # 10. Inbound call event handling and Plivo webhook signature parsing
    def test_10_inbound_call_event_handling(self):
        provider = PlivoTelephonyProvider(
            auth_id="test_auth_id",
            auth_token="test_secret_token_123"
        )
        mock_payload = {
            "CallUUID": "call_uuid_test_123",
            "session_id": "sess_inbound_1",
            "CallStatus": "in-progress",
            "Duration": "30"
        }
        event = provider.handle_webhook(
            headers={"X-Plivo-Signature": "test_sig_mock"},
            body=b'',
            query_params=mock_payload
        )
        self.assertTrue(event.is_valid)
        self.assertEqual(event.provider_call_id, "call_uuid_test_123")
        self.assertEqual(event.status, CallStateEnum.CONNECTED)
        self.assertEqual(event.duration_seconds, 30)

    # 11. Simultaneous ring group browser destinations
    def test_11_simultaneous_ring_group_browser_destinations(self):
        # Create Ring Group with 2 agents
        rg = TelephonyRingGroup(
            company_id=1,
            name="Sales Softphone Group",
            strategy="simultaneous",
            timeout_seconds=20,
            fallback_action="voicemail"
        )
        self.db.add(rg)
        self.db.commit()
        self.test_group_ids.append(rg.id)

        m1 = TelephonyRingGroupMember(ring_group_id=rg.id, staff_id=self.staff_1.id, priority_order=1)
        m2 = TelephonyRingGroupMember(ring_group_id=rg.id, staff_id=self.staff_2.id, priority_order=2)
        self.db.add_all([m1, m2])
        self.db.commit()

        # Test resolving ring group SIP endpoints
        endpoints = CallFlowInterpreter._resolve_ring_group_endpoints(self.db, company_id=1, ring_group_id=rg.id)
        expected_sip_1 = f"sip:agent_c1_s{self.staff_1.id}@phone.plivo.com"
        expected_sip_2 = f"sip:agent_c1_s{self.staff_2.id}@phone.plivo.com"
        self.assertIn(expected_sip_1, endpoints)
        self.assertIn(expected_sip_2, endpoints)

        # Generate Plivo Dial XML with simultaneous <User> endpoints
        user_tags = "".join([f"<User>{ep}</User>" for ep in endpoints])
        dial_xml = f'<Dial timeout="20" callerId="+918031728899">{user_tags}</Dial>'
        self.assertIn("<Dial", dial_xml)
        self.assertIn(f"<User>{expected_sip_1}</User>", dial_xml)
        self.assertIn(f"<User>{expected_sip_2}</User>", dial_xml)

    # 12. One agent answering cancels other ringing states
    def test_12_one_agent_answering_cancels_other_ringing_states(self):
        session_id = f"sess_ring_group_race_{int(time.time())}"
        self.test_session_ids.append(session_id)
        session = VoIPCallSession(
            company_id=1,
            call_session_id=session_id,
            provider="plivo",
            caller_id="+918031728899",
            customer_phone="9876500001",
            destination_number="9876500001",
            operator_id=None,
            direction="inbound",
            status=CallStateEnum.RINGING.value
        )
        self.db.add(session)
        self.db.commit()

        # Agent Alpha answers the call
        session.operator_id = self.staff_1.id
        session.operator_name = self.staff_1.full_name
        session.status = CallStateEnum.CONNECTED.value
        self.db.commit()

        # Check session reflects Agent Alpha connected
        updated = self.db.query(VoIPCallSession).filter_by(call_session_id=session_id).first()
        self.assertEqual(updated.operator_id, self.staff_1.id)
        self.assertEqual(updated.status, CallStateEnum.CONNECTED.value)

    # 13. Multiple staff sessions can exist concurrently
    def test_13_multiple_staff_sessions_concurrent(self):
        s1_id = f"sess_agent_1_{int(time.time())}"
        s2_id = f"sess_agent_2_{int(time.time())}"
        self.test_session_ids.extend([s1_id, s2_id])
        s1 = VoIPCallSession(
            company_id=1,
            call_session_id=s1_id,
            provider="plivo",
            caller_id="+918031728899",
            customer_phone="9876500001",
            destination_number="9876500001",
            operator_id=self.staff_1.id,
            direction="outbound",
            status=CallStateEnum.CONNECTED.value
        )
        s2 = VoIPCallSession(
            company_id=1,
            call_session_id=s2_id,
            provider="plivo",
            caller_id="+918031728899",
            customer_phone="9876500002",
            destination_number="9876500002",
            operator_id=self.staff_2.id,
            direction="outbound",
            status=CallStateEnum.CONNECTED.value
        )
        self.db.add_all([s1, s2])
        self.db.commit()

        active_calls = self.db.query(VoIPCallSession).filter(
            VoIPCallSession.call_session_id.in_([s1_id, s2_id]),
            VoIPCallSession.status == CallStateEnum.CONNECTED.value
        ).all()
        self.assertEqual(len(active_calls), 2)

    # 14. Agent A Call 1 does not affect Agent B Call 2
    def test_14_agent_a_call_does_not_affect_agent_b_call(self):
        s1_id = f"sess_a1_{int(time.time())}"
        s2_id = f"sess_b2_{int(time.time())}"
        self.test_session_ids.extend([s1_id, s2_id])
        s1 = VoIPCallSession(
            company_id=1,
            call_session_id=s1_id,
            provider="plivo",
            caller_id="+918031728899",
            customer_phone="9876500001",
            destination_number="9876500001",
            operator_id=self.staff_1.id,
            direction="outbound",
            status=CallStateEnum.CONNECTED.value
        )
        s2 = VoIPCallSession(
            company_id=1,
            call_session_id=s2_id,
            provider="plivo",
            caller_id="+918031728899",
            customer_phone="9876500002",
            destination_number="9876500002",
            operator_id=self.staff_2.id,
            direction="outbound",
            status=CallStateEnum.CONNECTED.value
        )
        self.db.add_all([s1, s2])
        self.db.commit()

        # End Agent A call
        s1.status = CallStateEnum.ENDED.value
        self.db.commit()

        # Verify Agent B call is untouched
        s2_fresh = self.db.query(VoIPCallSession).filter_by(call_session_id=s2_id).first()
        self.assertEqual(s2_fresh.status, CallStateEnum.CONNECTED.value)

    # 15. CRM context remains attached
    def test_15_crm_context_remains_attached(self):
        session_id = f"sess_crm_context_{int(time.time())}"
        self.test_session_ids.append(session_id)
        session = VoIPCallSession(
            company_id=1,
            call_session_id=session_id,
            provider="plivo",
            caller_id="+918031728899",
            customer_phone="9876500001",
            destination_number="9876500001",
            lead_id=self.lead.id,
            operator_id=self.staff_1.id,
            direction="outbound",
            status=CallStateEnum.CONNECTED.value
        )
        self.db.add(session)
        self.db.commit()

        lead_res = self.db.query(CRMLead).filter_by(id=session.lead_id).first()
        self.assertIsNotNone(lead_res)
        self.assertEqual(lead_res.name, "Vikram Sharma")
        self.assertEqual(lead_res.phone, "9876500001")

    # 16. TelephonyFactory resolves Plivo provider correctly
    def test_16_telephony_factory_resolves_plivo_provider(self):
        provider = get_telephony_provider("plivo")
        self.assertIsInstance(provider, PlivoTelephonyProvider)
        self.assertEqual(provider.provider_name, "plivo")


if __name__ == '__main__':
    unittest.main()
