"""
Comprehensive Automated Test Suite for MyntOS Call Flow Designer & Execution Engine
Verifies complete flow lifecycle: Draft, Validation, Immutability, Publishing, Rollback,
Simulator, Time Routing, IVR Branching, Ring Groups, Voicemail, Tenant Isolation, and RBAC.
Created: Sep 2026
"""

import os
import sys
import unittest
import json
from datetime import datetime
import pytz

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.core.database import SessionLocal
from app.models.telephony_call_flow import (
    TelephonyCallFlow, TelephonyCallFlowVersion, TelephonyFlowNode,
    TelephonyFlowEdge, TelephonyRingGroup, TelephonyRingGroupMember,
    TelephonyBusinessHours, TelephonyHoliday, TelephonyPlivoEndpoint,
    TelephonyFlowExecutionLog
)
from app.models.operator_calls import TelephonyDIDMapping
from app.models.staff import StaffEmployee
from app.models.crm import CRMLead
from app.services.telephony.call_flow_service import CallFlowService
from app.services.telephony.flow_validator import CallFlowValidator
from app.services.telephony.flow_simulator import CallFlowSimulator
from app.services.telephony.flow_interpreter import CallFlowInterpreter
from fastapi import HTTPException

IST = pytz.timezone('Asia/Kolkata')


class TestCallFlowEngine(unittest.TestCase):
    """Test Suite for MyntOS Call Flow Designer & Execution Foundation"""

    def setUp(self):
        self.db = SessionLocal()
        self.company_id_1 = 1
        self.company_id_2 = 2
        self.test_flow_ids = []
        self.test_group_ids = []

    def tearDown(self):
        try:
            for fid in self.test_flow_ids:
                self.db.query(TelephonyFlowExecutionLog).filter(TelephonyFlowExecutionLog.flow_id == fid).delete()
                self.db.query(TelephonyFlowEdge).filter(TelephonyFlowEdge.flow_version_id.in_(
                    self.db.query(TelephonyCallFlowVersion.id).filter(TelephonyCallFlowVersion.flow_id == fid)
                )).delete()
                self.db.query(TelephonyFlowNode).filter(TelephonyFlowNode.flow_version_id.in_(
                    self.db.query(TelephonyCallFlowVersion.id).filter(TelephonyCallFlowVersion.flow_id == fid)
                )).delete()
                self.db.query(TelephonyCallFlowVersion).filter(TelephonyCallFlowVersion.flow_id == fid).delete()
                self.db.query(TelephonyCallFlow).filter(TelephonyCallFlow.id == fid).delete()

            for gid in self.test_group_ids:
                self.db.query(TelephonyRingGroupMember).filter(TelephonyRingGroupMember.ring_group_id == gid).delete()
                self.db.query(TelephonyRingGroup).filter(TelephonyRingGroup.id == gid).delete()

            self.db.commit()
        except Exception:
            self.db.rollback()
        finally:
            self.db.close()

    # ── 1. FLOW DRAFT & CRUD TESTS ──────────────────────────────────────────

    def test_01_create_flow_draft(self):
        """Test creating a new call flow creates draft Version 1"""
        flow_data = CallFlowService.create_flow(
            db=self.db,
            company_id=self.company_id_1,
            name="Test Inbound Flow 1",
            description="Testing draft creation",
            did_number="+918031728899"
        )
        self.test_flow_ids.append(flow_data['id'])

        self.assertIsNotNone(flow_data['id'])
        self.assertEqual(flow_data['status'], 'draft')
        self.assertIsNotNone(flow_data.get('draft_version'))
        self.assertEqual(flow_data['draft_version']['version_number'], 1)
        self.assertEqual(flow_data['draft_version']['status'], 'draft')

    def test_02_edit_flow_draft(self):
        """Test editing a draft updates flow graph without publishing"""
        flow = CallFlowService.create_flow(
            db=self.db,
            company_id=self.company_id_1,
            name="Test Inbound Flow 2",
            did_number="+918031728899"
        )
        self.test_flow_ids.append(flow['id'])

        modified_graph = {
            "nodes": [
                { "id": "node_trigger_did_1", "type": "trigger_did", "name": "DID", "config": { "did_number": "+918031728899" } },
                { "id": "node_hangup_1", "type": "hangup", "name": "Hangup", "config": {} }
            ],
            "edges": [
                { "from": "node_trigger_did_1", "to": "node_hangup_1", "condition": "always" }
            ]
        }

        updated = CallFlowService.save_draft(
            db=self.db,
            company_id=self.company_id_1,
            flow_id=flow['id'],
            flow_data=modified_graph,
            name="Updated Inbound Flow 2"
        )

        self.assertEqual(updated['name'], "Updated Inbound Flow 2")
        self.assertEqual(len(updated['draft_version']['flow_data']['nodes']), 2)

    # ── 2. SERVER-SIDE VALIDATION TESTS ─────────────────────────────────────

    def test_03_validation_missing_entry_trigger(self):
        """Test validator rejects flow graph with missing trigger_did node"""
        invalid_graph = {
            "nodes": [
                { "id": "node_greeting_1", "type": "speak_prompt", "name": "Greeting", "config": { "text": "Hello" } },
                { "id": "node_hangup_1", "type": "hangup", "name": "Hangup", "config": {} }
            ],
            "edges": [
                { "from": "node_greeting_1", "to": "node_hangup_1", "condition": "always" }
            ]
        }
        is_valid, issues = CallFlowValidator.validate_flow_graph(invalid_graph, company_id=1)
        self.assertFalse(is_valid)
        error_types = [i['error_type'] for i in issues]
        self.assertIn('MISSING_TRIGGER', error_types)

    def test_04_validation_unreachable_node_warning(self):
        """Test validator flags orphaned unreachable nodes"""
        graph_with_orphan = {
            "nodes": [
                { "id": "node_trigger_did_1", "type": "trigger_did", "name": "DID", "config": { "did_number": "+918031728899" } },
                { "id": "node_hangup_1", "type": "hangup", "name": "Hangup", "config": {} },
                { "id": "node_orphan_1", "type": "voicemail", "name": "Orphan Voicemail", "config": { "prompt_text": "Lost" } }
            ],
            "edges": [
                { "from": "node_trigger_did_1", "to": "node_hangup_1", "condition": "always" }
            ]
        }
        is_valid, issues = CallFlowValidator.validate_flow_graph(graph_with_orphan, company_id=1)
        self.assertTrue(is_valid)  # Warnings do not block validity
        warning_types = [i['error_type'] for i in issues if i['severity'] == 'warning']
        self.assertIn('UNREACHABLE_NODE', warning_types)

    def test_05_validation_unbounded_infinite_loop_rejected(self):
        """Test validator rejects un-escapable infinite loops"""
        infinite_loop_graph = {
            "nodes": [
                { "id": "node_trigger_did_1", "type": "trigger_did", "name": "DID", "config": { "did_number": "+918031728899" } },
                { "id": "node_speak_1", "type": "speak_prompt", "name": "Loop 1", "config": { "text": "A" } },
                { "id": "node_speak_2", "type": "speak_prompt", "name": "Loop 2", "config": { "text": "B" } }
            ],
            "edges": [
                { "from": "node_trigger_did_1", "to": "node_speak_1", "condition": "always" },
                { "from": "node_speak_1", "to": "node_speak_2", "condition": "always" },
                { "from": "node_speak_2", "to": "node_speak_1", "condition": "always" }  # Strict infinite loop
            ]
        }
        is_valid, issues = CallFlowValidator.validate_flow_graph(infinite_loop_graph, company_id=1)
        self.assertFalse(is_valid)
        error_types = [i['error_type'] for i in issues]
        self.assertIn('UNBOUNDED_INFINITE_LOOP', error_types)

    def test_06_validation_controlled_retry_loop_permitted(self):
        """Test validator permits controlled IVR retry loops with exit branches"""
        controlled_ivr_graph = {
            "nodes": [
                { "id": "node_trigger_did_1", "type": "trigger_did", "name": "DID", "config": { "did_number": "+918031728899" } },
                { "id": "node_ivr_1", "type": "ivr_menu", "name": "IVR Menu", "config": { "text": "Press 1", "valid_digits": ["1"], "max_retries": 2 } },
                { "id": "node_hangup_1", "type": "hangup", "name": "Hangup", "config": {} },
                { "id": "node_voicemail_1", "type": "voicemail", "name": "Voicemail", "config": { "prompt_text": "Leave msg" } }
            ],
            "edges": [
                { "from": "node_trigger_did_1", "to": "node_ivr_1", "condition": "always" },
                { "from": "node_ivr_1", "to": "node_hangup_1", "condition": "digit_1" },
                { "from": "node_ivr_1", "to": "node_ivr_1", "condition": "invalid" },  # Retry loop
                { "from": "node_ivr_1", "to": "node_voicemail_1", "condition": "timeout" }  # Safe exit
            ]
        }
        is_valid, issues = CallFlowValidator.validate_flow_graph(controlled_ivr_graph, company_id=1)
        self.assertTrue(is_valid)

    # ── 3. PUBLISHING, IMMUTABILITY & ROLLBACK ────────────────────────────────

    def test_07_publish_creates_immutable_version(self):
        """Test publishing activates version and creates immutable snapshot"""
        flow = CallFlowService.create_flow(
            db=self.db,
            company_id=self.company_id_1,
            name="Publish Test Flow",
            did_number="+918031728899"
        )
        self.test_flow_ids.append(flow['id'])

        published = CallFlowService.publish_flow(
            db=self.db,
            company_id=self.company_id_1,
            flow_id=flow['id']
        )

        self.assertEqual(published['status'], 'published')
        self.assertIsNotNone(published['current_published_version_id'])
        self.assertEqual(published['published_version']['status'], 'published')
        self.assertEqual(published['published_version']['version_number'], 1)

    def test_08_publish_version_2_supersedes_version_1(self):
        """Test publishing second version supersedes previous published version"""
        flow = CallFlowService.create_flow(
            db=self.db,
            company_id=self.company_id_1,
            name="Multi Version Flow",
            did_number="+918031728899"
        )
        self.test_flow_ids.append(flow['id'])

        # Publish v1
        CallFlowService.publish_flow(db=self.db, company_id=self.company_id_1, flow_id=flow['id'])

        # Create & edit draft v2
        draft_v2_graph = {
            "nodes": [
                { "id": "node_trigger_did_1", "type": "trigger_did", "name": "DID", "config": { "did_number": "+918031728899" } },
                { "id": "node_greeting_1", "type": "speak_prompt", "name": "Greeting v2", "config": { "text": "Welcome to version 2" } },
                { "id": "node_hangup_1", "type": "hangup", "name": "Hangup", "config": {} }
            ],
            "edges": [
                { "from": "node_trigger_did_1", "to": "node_greeting_1", "condition": "always" },
                { "from": "node_greeting_1", "to": "node_hangup_1", "condition": "always" }
            ]
        }
        CallFlowService.save_draft(db=self.db, company_id=self.company_id_1, flow_id=flow['id'], flow_data=draft_v2_graph)

        # Publish v2
        pub_v2 = CallFlowService.publish_flow(db=self.db, company_id=self.company_id_1, flow_id=flow['id'])
        self.assertEqual(pub_v2['published_version']['version_number'], 2)

        # Verify v1 is superseded
        v1 = self.db.query(TelephonyCallFlowVersion).filter(
            TelephonyCallFlowVersion.flow_id == flow['id'],
            TelephonyCallFlowVersion.version_number == 1
        ).first()
        self.assertEqual(v1.status, 'superseded')

    def test_09_rollback_to_prior_version(self):
        """Test rolling back restores previous published version as active"""
        flow = CallFlowService.create_flow(
            db=self.db,
            company_id=self.company_id_1,
            name="Rollback Test Flow"
        )
        self.test_flow_ids.append(flow['id'])

        # Publish v1
        pub_v1 = CallFlowService.publish_flow(db=self.db, company_id=self.company_id_1, flow_id=flow['id'])
        v1_id = pub_v1['published_version']['id']

        # Fork and publish v2
        graph_v2 = {
            "nodes": [
                { "id": "node_trigger_did_1", "type": "trigger_did", "name": "DID", "config": {} },
                { "id": "node_hangup_1", "type": "hangup", "name": "Hangup", "config": {} }
            ],
            "edges": [{ "from": "node_trigger_did_1", "to": "node_hangup_1", "condition": "always" }]
        }
        CallFlowService.save_draft(db=self.db, company_id=self.company_id_1, flow_id=flow['id'], flow_data=graph_v2)
        pub_v2 = CallFlowService.publish_flow(db=self.db, company_id=self.company_id_1, flow_id=flow['id'])
        self.assertEqual(pub_v2['published_version']['version_number'], 2)

        # Rollback to v1
        rolled_back = CallFlowService.rollback_flow(
            db=self.db,
            company_id=self.company_id_1,
            flow_id=flow['id'],
            target_version_id=v1_id
        )
        self.assertEqual(rolled_back['current_published_version_id'], v1_id)
        self.assertEqual(rolled_back['published_version']['version_number'], 1)

    # ── 4. SIMULATOR TESTS ───────────────────────────────────────────────────

    def test_10_simulator_open_business_hours_trace(self):
        """Test simulator executes Open branch during working hours (e.g. Wednesday 11:30 AM)"""
        flow = CallFlowService.create_flow(db=self.db, company_id=self.company_id_1, name="Sim Open Flow")
        self.test_flow_ids.append(flow['id'])

        sim_wed_11am = datetime(2026, 9, 2, 11, 30, 0)  # Wednesday 11:30 AM
        trace = CallFlowService.simulate_flow(
            db=self.db,
            company_id=self.company_id_1,
            flow_id=flow['id'],
            caller_phone="+919703118501",
            simulated_datetime=sim_wed_11am
        )

        self.assertTrue(trace['success'])
        self.assertEqual(trace['final_destination'], "Ring Group: General Inbound Team")
        self.assertEqual(trace['final_outcome'], "connected")

    def test_11_simulator_after_hours_voicemail_trace(self):
        """Test simulator executes Closed branch after working hours (e.g. Wednesday 10:30 PM)"""
        flow = CallFlowService.create_flow(db=self.db, company_id=self.company_id_1, name="Sim Closed Flow")
        self.test_flow_ids.append(flow['id'])

        sim_wed_10pm = datetime(2026, 9, 2, 22, 30, 0)  # Wednesday 10:30 PM (After hours)
        trace = CallFlowService.simulate_flow(
            db=self.db,
            company_id=self.company_id_1,
            flow_id=flow['id'],
            caller_phone="+919703118501",
            simulated_datetime=sim_wed_10pm
        )

        self.assertTrue(trace['success'])
        self.assertEqual(trace['final_destination'], "Voicemail Box")
        self.assertEqual(trace['final_outcome'], "voicemail_recorded")

    def test_12_simulator_ivr_digit_branching_trace(self):
        """Test simulator follows DTMF digit selection along IVR menu"""
        ivr_graph = {
            "nodes": [
                { "id": "node_trigger_did_1", "type": "trigger_did", "name": "DID", "config": {} },
                { "id": "node_ivr_1", "type": "ivr_menu", "name": "Menu", "config": { "text": "Press 1 or 2", "valid_digits": ["1", "2"] } },
                { "id": "node_sales_ring", "type": "dial_ring_group", "name": "Sales Group", "config": { "ring_group_id": 1 } },
                { "id": "node_support_ring", "type": "dial_ring_group", "name": "Support Group", "config": { "ring_group_id": 2 } }
            ],
            "edges": [
                { "from": "node_trigger_did_1", "to": "node_ivr_1", "condition": "always" },
                { "from": "node_ivr_1", "to": "node_sales_ring", "condition": "digit_1" },
                { "from": "node_ivr_1", "to": "node_support_ring", "condition": "digit_2" }
            ]
        }
        flow = CallFlowService.create_flow(db=self.db, company_id=self.company_id_1, name="IVR Test Flow", initial_graph=ivr_graph)
        self.test_flow_ids.append(flow['id'])

        # Press '2' for Support
        trace = CallFlowService.simulate_flow(
            db=self.db,
            company_id=self.company_id_1,
            flow_id=flow['id'],
            caller_phone="+919703118501",
            dtmf_inputs=["2"]
        )

        self.assertTrue(trace['success'])
        self.assertIn("Support", trace['final_destination'])

    # ── 5. RUNTIME PLIVO XML GENERATOR TESTS ─────────────────────────────────

    def test_13_plivo_xml_inbound_answer_generation(self):
        """Test live interpreter returns compliant Plivo XML on Inbound Answer"""
        flow = CallFlowService.create_flow(
            db=self.db,
            company_id=self.company_id_1,
            name="Live Plivo Flow",
            did_number="+918031728899"
        )
        self.test_flow_ids.append(flow['id'])
        CallFlowService.publish_flow(db=self.db, company_id=self.company_id_1, flow_id=flow['id'])

        xml_output = CallFlowInterpreter.handle_inbound_call(
            db=self.db,
            caller_phone="+919703118501",
            called_did="+918031728899",
            provider_call_id="plivo_call_uuid_12345",
            base_api_url="https://api.myntreal.com"
        )

        self.assertTrue(xml_output.startswith("<Response>"))
        self.assertTrue(xml_output.endswith("</Response>"))
        self.assertIn("<Speak", xml_output)

    def test_14_ring_group_simultaneous_multi_user_xml(self):
        """Test ring group renders multiple <User> tags for simultaneous softphone ringing"""
        group = CallFlowService.create_ring_group(
            db=self.db,
            company_id=self.company_id_1,
            name="Test Sales Group",
            strategy="simultaneous",
            member_staff_ids=[101, 102, 103]
        )
        self.test_group_ids.append(group['id'])

        rg_graph = {
            "nodes": [
                { "id": "node_trigger_did_1", "type": "trigger_did", "name": "DID", "config": { "did_number": "+918031728899" } },
                { "id": "node_rg_1", "type": "dial_ring_group", "name": "Ring Group", "config": { "ring_group_id": group['id'], "timeout_seconds": 20 } }
            ],
            "edges": [
                { "from": "node_trigger_did_1", "to": "node_rg_1", "condition": "always" }
            ]
        }
        flow = CallFlowService.create_flow(db=self.db, company_id=self.company_id_1, name="RG Sim Flow", did_number="+918031728899", initial_graph=rg_graph)
        self.test_flow_ids.append(flow['id'])
        CallFlowService.publish_flow(db=self.db, company_id=self.company_id_1, flow_id=flow['id'])

        xml_output = CallFlowInterpreter.handle_inbound_call(
            db=self.db,
            caller_phone="+919703118501",
            called_did="+918031728899",
            provider_call_id="plivo_uuid_rg_001",
            base_api_url="https://api.myntreal.com"
        )

        self.assertIn("<Dial timeout=\"20\"", xml_output)
        self.assertIn("<User>sip:agent_c1_s101@phone.plivo.com</User>", xml_output)
        self.assertIn("<User>sip:agent_c1_s102@phone.plivo.com</User>", xml_output)
        self.assertIn("<User>sip:agent_c1_s103@phone.plivo.com</User>", xml_output)

    # ── 6. TENANT ISOLATION & SECURITY TESTS ─────────────────────────────────

    def test_15_tenant_isolation_cross_company_flow_access(self):
        """Test Company 2 operator cannot access or modify Company 1 flows"""
        flow_comp1 = CallFlowService.create_flow(
            db=self.db,
            company_id=self.company_id_1,
            name="Company 1 Confidential Flow"
        )
        self.test_flow_ids.append(flow_comp1['id'])

        # Company 2 tries to access Company 1 flow -> 404 Not Found
        with self.assertRaises(HTTPException) as ctx:
            CallFlowService.get_flow_details(db=self.db, company_id=self.company_id_2, flow_id=flow_comp1['id'])
        self.assertEqual(ctx.exception.status_code, 404)


if __name__ == '__main__':
    unittest.main()
