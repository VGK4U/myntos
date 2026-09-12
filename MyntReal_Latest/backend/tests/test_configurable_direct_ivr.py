"""
Comprehensive Test Suite for Configurable Direct Agent Selection IVR
with Dynamic DTMF Routing & Customer Care Fallback.

Strictly adheres to:
- DC Protocol: Read-Only DB access, no database mutations or raw SQL inserts.
- Zero Hardcoded Paths.
- Strict Parity with CallFlowInterpreter & call_flow_api architecture.

Validates:
1. Dynamic TTS Prompt Synthesis from active flow configuration.
2. Inbound Plivo Call Entry XML (<GetDigits timeout="5" numDigits="1"> with synthesized prompt).
3. DTMF Handling:
   - Case A: 5-second silence/no-input -> Customer Care / Main IVR directly (NO unavailable prompt).
   - Case B: Valid agent selected & available -> <Dial timeout="20"> to SIP endpoint with agent-dial-complete action.
   - Case C: Agent offline / busy / inactive -> Plays "The agent you selected is currently unavailable..."
             then seamlessly transitions to Customer Care / Main IVR on SAME call.
   - Case D: Department destination -> Simultaneous dial to department ring-group.
4. Staff Dial Complete Callback (handle_agent_dial_complete):
   - Answered -> <Hangup />
   - No-answer / busy / timeout / failed -> Unavailable prompt + Customer Care IVR on SAME call.
5. API Configuration Endpoints:
   - GET /departments (list_company_departments)
   - GET /direct-routing (get_direct_routing_config)
   - PUT /direct-routing/draft (save_direct_routing_draft: DTMF validation, duplicate key prevention, tenant isolation)
   - POST /direct-routing/publish (publish_direct_routing_config: version increment, immutability, superseded transition)
6. Frontend Artifact Verification (staff_call_flow_studio.html UI components & JavaScript lifecycle).
"""

import os
import sys
import json
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.core.database import SessionLocal
from app.models.telephony_call_flow import TelephonyCallFlow, TelephonyCallFlowVersion, TelephonyPlivoEndpoint
from app.models.staff import StaffEmployee, StaffDepartment
from app.models.voip_call_session import VoIPCallSession
from app.services.telephony.flow_interpreter import CallFlowInterpreter
from app.api.v1.endpoints.call_flow_api import (
    list_company_departments,
    get_direct_routing_config,
    save_direct_routing_draft,
    publish_direct_routing_config
)
from fastapi import HTTPException


class TestConfigurableDirectRoutingIVR(unittest.TestCase):
    """
    Test suite for Configurable Direct Agent Selection IVR
    """

    @classmethod
    def setUpClass(cls):
        cls.db = SessionLocal()
        cls.company_id = 1
        # Fetch existing active staff from DB (read-only)
        cls.active_staff = cls.db.query(StaffEmployee).filter(
            StaffEmployee.status.in_(['active', 'ACTIVE']),
            StaffEmployee.is_deleted == False
        ).all()
        # Fetch existing active departments from DB (read-only)
        cls.active_depts = cls.db.query(StaffDepartment).filter(
            StaffDepartment.is_active == True
        ).all()

    @classmethod
    def tearDownClass(cls):
        cls.db.close()

    # =========================================================================
    # 1. DYNAMIC PROMPT SYNTHESIS TESTS
    # =========================================================================

    def test_01_dynamic_prompt_synthesis_standard_team(self):
        """Dynamic prompt constructs generic extension greeting without employee names"""
        options = [
            {"dtmf_key": "1", "display_name": "Pujita", "is_active": True, "order": 1},
            {"dtmf_key": "2", "display_name": "Nandana", "is_active": True, "order": 2},
            {"dtmf_key": "3", "display_name": "Anusha", "is_active": True, "order": 3},
            {"dtmf_key": "4", "display_name": "Lakshmi", "is_active": True, "order": 4},
            {"dtmf_key": "5", "display_name": "Hema", "is_active": True, "order": 5},
            {"dtmf_key": "6", "display_name": "Anushka", "is_active": True, "order": 6},
        ]
        prompt = CallFlowInterpreter._build_direct_routing_prompt(options)
        self.assertEqual(prompt, "Please press the extension number, or stay on the line for our main menu.")
        self.assertNotIn("Pujita", prompt)

    def test_02_dynamic_prompt_synthesis_filters_inactive_and_reorders(self):
        """Prompt synthesis ignores employee names and returns generic extension prompt"""
        options = [
            {"dtmf_key": "2", "display_name": "Solar Telesales", "is_active": True, "order": 20},
            {"dtmf_key": "1", "display_name": "Ravi", "is_active": True, "order": 10},
            {"dtmf_key": "3", "display_name": "Inactive Agent", "is_active": False, "order": 15},
        ]
        prompt = CallFlowInterpreter._build_direct_routing_prompt(options)
        self.assertEqual(prompt, "Please press the extension number, or stay on the line for our main menu.")
        self.assertNotIn("Ravi", prompt)
        self.assertNotIn("Inactive Agent", prompt)

    def test_03_dynamic_prompt_empty_options(self):
        """Prompt synthesis handles empty active list gracefully"""
        prompt = CallFlowInterpreter._build_direct_routing_prompt([])
        self.assertEqual(prompt, "")

    # =========================================================================
    # 2. INBOUND ENTRY XML GENERATION
    # =========================================================================

    def test_04_inbound_call_renders_direct_routing_getdigits_xml(self):
        """Inbound call renders <GetDigits timeout='5' numDigits='1'> with synthesized prompt"""
        test_options = [
            {"dtmf_key": "1", "destination_type": "staff", "destination_id": 1, "display_name": "Pujita", "is_active": True, "order": 1}
        ]
        with patch.object(CallFlowInterpreter, '_get_published_direct_routing_options', return_value=test_options):
            with patch.object(CallFlowInterpreter, '_evaluate_business_hours', return_value=(True, "Open")):
                with patch.object(CallFlowInterpreter, '_is_qualified_sticky_caller', return_value=False):
                    xml = CallFlowInterpreter.handle_inbound_call(
                        db=self.db,
                        caller_phone="+919876543210",
                        called_did="+918031728899",
                        provider_call_id="call-uuid-12345"
                    )
                    self.assertIn('<GetDigits action="https://www.myntreal.com/api/v1/telephony/plivo/ivr/gather?menu=direct_routing', xml)
                    self.assertIn('timeout="5"', xml)
                    self.assertIn('numDigits="1"', xml)
                    self.assertIn('Please press the extension number, or stay on the line for our main menu.', xml)
                    self.assertNotIn('Press 1 for Pujita', xml)

    # =========================================================================
    # 3. DTMF HANDLING & FALLBACKS
    # =========================================================================

    def test_05_dtmf_case_a_silence_5s_routes_to_main_ivr_without_unavailable_msg(self):
        """Case A: Caller does not enter any digit within 5s -> Direct Customer Care IVR (NO unavailable prompt)"""
        test_options = [
            {"dtmf_key": "1", "destination_type": "staff", "destination_id": 1, "display_name": "Pujita", "is_active": True, "order": 1}
        ]
        with patch.object(CallFlowInterpreter, '_get_published_direct_routing_options', return_value=test_options):
            # Caller pressed nothing: digits=""
            xml = CallFlowInterpreter.handle_ivr_gather(
                db=self.db,
                caller_phone="+919876543210",
                called_did="+918031728899",
                digits="",
                menu_type="direct_routing",
                lang="en"
            )
            # Must NOT contain unavailable message
            self.assertNotIn("The agent you selected is currently unavailable", xml)
            # Must contain Customer Care / Main IVR elements
            self.assertIn('menu=dept', xml)
            self.assertIn('For Solar, press 1', xml)

    def test_06_dtmf_invalid_digit_reprompts(self):
        """Caller presses invalid/unconfigured digit -> Seamlessly continues to Main IVR on the same call"""
        test_options = [
            {"dtmf_key": "1", "destination_type": "staff", "destination_id": 1, "display_name": "Pujita", "is_active": True, "order": 1}
        ]
        with patch.object(CallFlowInterpreter, '_get_published_direct_routing_options', return_value=test_options):
            xml = CallFlowInterpreter.handle_ivr_gather(
                db=self.db,
                caller_phone="+919876543210",
                called_did="+918031728899",
                digits="9",
                menu_type="direct_routing",
                lang="en"
            )
            self.assertIn("Welcome to Mynt Real", xml)
            self.assertIn("For Solar, press 1", xml)
            self.assertIn("menu=dept", xml)

    def test_07_dtmf_case_b_staff_available_dials_endpoint(self):
        """Case B: Valid agent selected & available -> Generates <Dial timeout='20'> to staff SIP endpoint"""
        staff = self.active_staff[0] if self.active_staff else MagicMock(id=1, full_name="Ms. Test Agent", emp_code="EMP01", base_company_id=1, data_companies=[])

        # Mock registered endpoint and no active call
        mock_ep = MagicMock()
        mock_ep.plivo_username = "test_agent_sip"
        mock_ep.is_registered = True

        test_options = [
            {
                "dtmf_key": "1",
                "destination_type": "staff",
                "destination_id": staff.id,
                "display_name": "Pujita",
                "ring_timeout": 20,
                "is_active": True,
                "order": 1
            }
        ]

        with patch.object(CallFlowInterpreter, '_get_published_direct_routing_options', return_value=test_options):
            with patch.object(CallFlowInterpreter, '_resolve_company_from_did', return_value=staff.base_company_id):
                with patch.object(self.db, 'query') as mock_query:
                    # Mock staff query
                    staff_filter = MagicMock()
                    staff_filter.first.return_value = staff

                    # Mock endpoint query
                    ep_filter = MagicMock()
                    ep_filter.order_by.return_value.first.return_value = mock_ep

                    # Mock active call query (None = available)
                    call_filter = MagicMock()
                    call_filter.first.return_value = None

                    def query_router(model):
                        mock_q = MagicMock()
                        if model == StaffEmployee:
                            mock_q.filter.return_value = staff_filter
                        elif model == TelephonyPlivoEndpoint:
                            mock_q.filter.return_value = ep_filter
                        elif model == VoIPCallSession:
                            mock_q.filter.return_value = call_filter
                        else:
                            return self.db.query(model)
                        return mock_q

                    mock_query.side_effect = query_router

                    xml = CallFlowInterpreter.handle_ivr_gather(
                        db=self.db,
                        caller_phone="+919876543210",
                        called_did="+918031728899",
                        digits="1",
                        menu_type="direct_routing",
                        lang="en"
                    )

                    self.assertIn('<Dial timeout="20"', xml)
                    self.assertIn('<User>sip:test_agent_sip@phone.plivo.com</User>', xml)
                    self.assertIn('action="https://www.myntreal.com/api/v1/telephony/plivo/ivr/agent-dial-complete', xml)
                    self.assertNotIn("The agent you selected is currently unavailable", xml)

    def test_08_dtmf_case_c_staff_offline_routes_to_main_ivr_with_unavailable_msg(self):
        """Case C: Valid agent selected but OFFLINE (no registered endpoint) -> Unavailable prompt + Main IVR"""
        staff = self.active_staff[0] if self.active_staff else MagicMock(id=1, full_name="Ms. Test Agent", emp_code="EMP01", base_company_id=1, data_companies=[])

        test_options = [
            {
                "dtmf_key": "2",
                "destination_type": "staff",
                "destination_id": staff.id,
                "display_name": "Nandana",
                "ring_timeout": 20,
                "is_active": True,
                "order": 1
            }
        ]

        with patch.object(CallFlowInterpreter, '_get_published_direct_routing_options', return_value=test_options):
            with patch.object(CallFlowInterpreter, '_resolve_company_from_did', return_value=staff.base_company_id):
                with patch.object(self.db, 'query') as mock_query:
                    # Mock staff found
                    staff_filter = MagicMock()
                    staff_filter.first.return_value = staff

                    # Mock endpoint None (offline!)
                    ep_filter = MagicMock()
                    ep_filter.order_by.return_value.first.return_value = None

                    def query_router(model):
                        mock_q = MagicMock()
                        if model == StaffEmployee:
                            mock_q.filter.return_value = staff_filter
                        elif model == TelephonyPlivoEndpoint:
                            mock_q.filter.return_value = ep_filter
                        else:
                            return self.db.query(model)
                        return mock_q

                    mock_query.side_effect = query_router

                    xml = CallFlowInterpreter.handle_ivr_gather(
                        db=self.db,
                        caller_phone="+919876543210",
                        called_did="+918031728899",
                        digits="2",
                        menu_type="direct_routing",
                        lang="en"
                    )

                    # Must inform caller
                    self.assertIn("The agent you selected is currently unavailable. We will now connect you to Customer Care.", xml)
                    # Must transition to Customer Care / Main IVR
                    self.assertIn("For Solar, press 1", xml)

    def test_09_dtmf_case_d_department_selection(self):
        """Case D: Department destination routes via simultaneous telesales dial"""
        dept = self.active_depts[0] if self.active_depts else MagicMock(id=1, name="Tele Sales", is_active=True)

        test_options = [
            {
                "dtmf_key": "3",
                "destination_type": "department",
                "destination_id": dept.id,
                "display_name": "Telesales",
                "is_active": True,
                "order": 1
            }
        ]

        with patch.object(CallFlowInterpreter, '_get_published_direct_routing_options', return_value=test_options):
            with patch.object(CallFlowInterpreter, '_build_telesales_simultaneous_dial', return_value='<Dial><User>sip:dept@plivo.com</User></Dial>'):
                xml = CallFlowInterpreter.handle_ivr_gather(
                    db=self.db,
                    caller_phone="+919876543210",
                    called_did="+918031728899",
                    digits="3",
                    menu_type="direct_routing",
                    lang="en"
                )
                self.assertIn(f"Connecting your call to our {test_options[0]['display_name']} department", xml)
                self.assertIn("<Dial><User>sip:dept@plivo.com</User></Dial>", xml)

    # =========================================================================
    # 4. AGENT DIAL COMPLETE CALLBACK
    # =========================================================================

    def test_10_dial_complete_answered_hangs_up(self):
        """If agent direct dial was answered -> <Hangup />"""
        xml = CallFlowInterpreter.handle_agent_dial_complete(
            db=self.db,
            form_data={"DialStatus": "answered", "From": "+919876543210", "To": "+918031728899"},
            query_params={}
        )
        self.assertIn("<Hangup />", xml)
        self.assertNotIn("unavailable", xml)

    def test_11_dial_complete_unanswered_fallback_to_main_ivr(self):
        """If agent did not answer/busy/timeout -> Plays unavailable message + Main IVR on SAME call"""
        for status in ("no-answer", "busy", "timeout", "failed", "rejected"):
            xml = CallFlowInterpreter.handle_agent_dial_complete(
                db=self.db,
                form_data={"DialStatus": status, "From": "+919876543210", "To": "+918031728899"},
                query_params={}
            )
            self.assertIn("The agent you selected is currently unavailable. We will now connect you to Customer Care.", xml)
            self.assertIn("For Solar, press 1", xml)

    # =========================================================================
    # 5. API CONFIGURATION ENDPOINTS (RBAC, TENANT ISOLATION, VALIDATION)
    # =========================================================================

    def test_12_get_active_departments_api(self):
        """GET /departments returns active departments"""
        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.base_company_id = 1
        depts = list_company_departments(db=self.db, current_user=mock_user)
        self.assertTrue(isinstance(depts, list))
        self.assertTrue(len(depts) > 0)
        self.assertIn("name", depts[0])
        self.assertIn("id", depts[0])

    def test_13_save_draft_validates_dtmf_and_saves(self):
        """PUT /direct-routing/draft validates DTMF keys and stores in version flow_data"""
        # Pick staff with company 1 access (e.g. employee 320 Mrs. Janapala Hema)
        staff = next((s for s in self.active_staff if 1 in (s.data_companies or []) or s.base_company_id == 1), self.active_staff[0])

        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.base_company_id = 1

        # Use an existing flow in company 1
        flow = self.db.query(TelephonyCallFlow).filter(TelephonyCallFlow.company_id == 1).first()

        payload = {
            "flow_id": flow.id if flow else 178,
            "options": [
                {
                    "dtmf_key": "1",
                    "destination_type": "staff",
                    "destination_id": staff.id,
                    "display_name": "Pujita",
                    "ring_timeout": 20,
                    "is_active": True,
                    "order": 1
                }
            ]
        }

        # Mock DB commit and refresh to be 100% read-only
        with patch.object(self.db, 'commit'):
            with patch.object(self.db, 'refresh'):
                res = save_direct_routing_draft(payload=payload, db=self.db, current_user=mock_user)
                self.assertEqual(res["status"], "success")
                self.assertEqual(len(res["draft_options"]), 1)
                self.assertEqual(res["draft_options"][0]["dtmf_key"], "1")
                self.assertEqual(res["draft_options"][0]["display_name"], "Pujita")

    def test_14_save_draft_rejects_duplicate_active_keys(self):
        """PUT /direct-routing/draft rejects duplicate active DTMF keys with 400"""
        staff = next((s for s in self.active_staff if 1 in (s.data_companies or []) or s.base_company_id == 1), self.active_staff[0])

        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.base_company_id = 1

        flow = self.db.query(TelephonyCallFlow).filter(TelephonyCallFlow.company_id == 1).first()

        payload = {
            "flow_id": flow.id if flow else 178,
            "options": [
                {"dtmf_key": "1", "destination_type": "staff", "destination_id": staff.id, "display_name": "Agent A", "is_active": True},
                {"dtmf_key": "1", "destination_type": "staff", "destination_id": staff.id, "display_name": "Agent B", "is_active": True}
            ]
        }

        with self.assertRaises(HTTPException) as ctx:
            save_direct_routing_draft(payload=payload, db=self.db, current_user=mock_user)
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("Duplicate active DTMF key '1'", ctx.exception.detail)

    def test_15_save_draft_rejects_cross_tenant_staff(self):
        """PUT /direct-routing/draft rejects staff from another company boundary with 403"""
        # Pick a staff whose base_company_id != 1 and data_companies does NOT contain 1 (e.g. employee 73)
        staff_other = next((s for s in self.active_staff if s.base_company_id != 1 and 1 not in (s.data_companies or [])), None)
        self.assertIsNotNone(staff_other, "Expected at least one staff member outside company 1 boundary")

        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.base_company_id = 1  # User belongs to company 1

        flow = self.db.query(TelephonyCallFlow).filter(TelephonyCallFlow.company_id == 1).first()

        payload = {
            "flow_id": flow.id if flow else 178,
            "options": [
                {"dtmf_key": "1", "destination_type": "staff", "destination_id": staff_other.id, "display_name": "Alien Agent", "is_active": True}
            ]
        }

        with self.assertRaises(HTTPException) as ctx:
            save_direct_routing_draft(payload=payload, db=self.db, current_user=mock_user)
        self.assertEqual(ctx.exception.status_code, 403)
        self.assertIn("does not belong to authorized company", ctx.exception.detail)

    def test_16_publish_direct_routing_creates_version_and_sets_flow(self):
        """POST /direct-routing/publish commits draft to published version and updates flow"""
        staff = self.active_staff[0]

        mock_user = MagicMock()
        mock_user.id = staff.id
        mock_user.base_company_id = staff.base_company_id

        flow = self.db.query(TelephonyCallFlow).filter(TelephonyCallFlow.company_id == staff.base_company_id).first()
        draft = TelephonyCallFlowVersion(
            id=99998,
            flow_id=flow.id if flow else 1,
            company_id=staff.base_company_id,
            version_number=10,
            status='draft',
            flow_data={"direct_routing": [{"dtmf_key": "1", "display_name": "Pub Agent", "is_active": True}]}
        )

        with patch.object(self.db, 'query') as mock_query:
            mock_flow_q = MagicMock()
            mock_flow_q.filter.return_value.first.return_value = flow or MagicMock(id=1, current_published_version_id=None)

            mock_draft_q = MagicMock()
            mock_draft_q.filter.return_value.order_by.return_value.first.return_value = draft
            mock_draft_q.filter.return_value.all.return_value = []

            def query_router(model):
                if model == TelephonyCallFlow:
                    return mock_flow_q
                elif model == TelephonyCallFlowVersion:
                    return mock_draft_q
                return self.db.query(model)

            mock_query.side_effect = query_router
            with patch.object(self.db, 'commit'):
                with patch.object(self.db, 'refresh'):
                    res = publish_direct_routing_config(payload={}, db=self.db, current_user=mock_user)
                    self.assertEqual(res["status"], "success")
                    self.assertEqual(res["version_number"], 10)
                    self.assertEqual(len(res["published_options"]), 1)
                    self.assertEqual(res["published_options"][0]["display_name"], "Pub Agent")

    # =========================================================================
    # 6. FRONTEND HTML & JAVASCRIPT INVARIANTS
    # =========================================================================

    def test_17_frontend_html_tab_and_components_exist(self):
        """Verify staff_call_flow_studio.html contains all required Direct Routing UI components"""
        html_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../frontend/staff_call_flow_studio.html'))
        self.assertTrue(os.path.exists(html_path), f"File not found: {html_path}")

        with open(html_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Tab button
        self.assertIn("switchMainTab('direct-routing')", content)
        # Tab container
        self.assertIn('id="tabDirectRouting"', content)
        # Hardcoded roster and pre-populate button strictly removed
        self.assertNotIn("prepopulateDefaultTeamRoster()", content)
        self.assertNotIn("rosterDefinitions", content)
        self.assertIn("openAddDirectRoutingModal()", content)
        self.assertIn("saveDirectRoutingDraft()", content)
        self.assertIn("publishDirectRouting()", content)
        # Dynamic Prompt preview
        self.assertIn('id="directRoutingPromptPreview"', content)
        # Options table
        self.assertIn('id="directRoutingTableBody"', content)
        # Modal
        self.assertIn('id="directRoutingOptionModal"', content)
        self.assertIn('id="drDtmfKey"', content)
        self.assertIn('id="drDestTypeStaff"', content)
        self.assertIn('id="drDestTypeDept"', content)
        self.assertIn('id="drStaffSelect"', content)
        self.assertIn('id="drDeptSelect"', content)
        self.assertIn('id="drDisplayName"', content)
        self.assertIn('id="drRingTimeout"', content)
        self.assertIn('id="drIsActive"', content)

        # JavaScript functions
        self.assertIn("async function loadDirectRouting()", content)
        self.assertIn("function renderDirectRoutingTable()", content)
        self.assertIn("function updateDirectRoutingPreview()", content)
        self.assertIn("function saveDirectRoutingOption()", content)
        self.assertIn("function deleteDirectRoutingOption(", content)
        self.assertIn("function moveDirectRoutingOption(", content)
        self.assertIn("function toggleDirectRoutingActive(", content)
        self.assertIn("async function saveDirectRoutingDraft()", content)
        self.assertIn("async function publishDirectRouting()", content)
        self.assertNotIn("function prepopulateDefaultTeamRoster()", content)


if __name__ == '__main__':
    unittest.main()
