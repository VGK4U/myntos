"""
Unit and Integration Tests for Dynamic IVR Extension / User Routing & WhatsApp Staff Signatures.
Strictly Read-Only on live database (uses rollback transactions and unit mocks).
"""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy.orm import Session
from app.services.telephony.flow_interpreter import CallFlowInterpreter
from app.services.whatsapp_auto_service import (
    format_staff_whatsapp_message,
    strip_staff_whatsapp_signature,
    resolve_staff_extension,
)
from app.models.telephony_call_flow import (
    TelephonyCallFlow,
    TelephonyCallFlowVersion,
    TelephonyPlivoEndpoint,
)
from app.models.operator_calls import TelephonyDIDMapping
from app.models.voip_call_session import VoIPCallSession
from app.models.staff import StaffEmployee, StaffDepartment


class TestDynamicIVRExtensions(unittest.TestCase):

    def setUp(self):
        self.mock_db = MagicMock(spec=Session)

    # =========================================================================
    # 1. CANONICAL RUNTIME RESOLVER TESTS (resolve_extension_destination)
    # =========================================================================

    def test_01_valid_staff_extension_available(self):
        """Test A: Valid active staff extension with registered endpoint resolves to available."""
        mock_emp = MagicMock(spec=StaffEmployee)
        mock_emp.id = 101
        mock_emp.full_name = "Pujita Sharma"
        mock_emp.emp_code = "MR10101"
        mock_emp.status = "active"
        mock_emp.is_deleted = False
        mock_emp.base_company_id = 1
        mock_emp.data_companies = [1]

        mock_ep = MagicMock(spec=TelephonyPlivoEndpoint)
        mock_ep.staff_id = 101
        mock_ep.is_registered = True
        mock_ep.plivo_username = "pujita_101"

        test_options = [
            {
                "dtmf_key": "1",
                "destination_type": "staff",
                "destination_id": 101,
                "display_name": "Pujita Sharma",
                "ring_timeout": 20,
                "is_active": True,
                "fallback_action": "main_ivr"
            }
        ]

        with patch.object(CallFlowInterpreter, '_get_published_direct_routing_options', return_value=test_options):
            query_mock = MagicMock()
            self.mock_db.query.return_value = query_mock
            query_mock.filter.return_value = query_mock
            query_mock.order_by.return_value = query_mock
            query_mock.first.side_effect = [mock_emp, mock_ep, None]

            res = CallFlowInterpreter.resolve_extension_destination(
                db=self.mock_db,
                company_id=1,
                extension="1",
                called_did="+918031728899"
            )

            self.assertEqual(res["status"], "available")
            self.assertEqual(res["destination_type"], "staff")
            self.assertEqual(res["destination_id"], 101)
            self.assertEqual(res["sip_uri"], "sip:pujita_101@phone.plivo.com")
            self.assertEqual(res["ring_timeout"], 20)

    def test_02_reassignment_without_code_changes(self):
        """Test B: Reallocating DTMF 1 to Staff B instantly routes to Staff B."""
        mock_emp_b = MagicMock(spec=StaffEmployee)
        mock_emp_b.id = 202
        mock_emp_b.full_name = "Nandana V"
        mock_emp_b.emp_code = "MR10202"
        mock_emp_b.status = "active"
        mock_emp_b.is_deleted = False
        mock_emp_b.base_company_id = 1
        mock_emp_b.data_companies = [1]

        mock_ep_b = MagicMock(spec=TelephonyPlivoEndpoint)
        mock_ep_b.staff_id = 202
        mock_ep_b.is_registered = True
        mock_ep_b.plivo_username = "nandana_202"

        # Reassigned in flow configuration: DTMF 1 is now Nandana (id 202) instead of Pujita
        test_options = [
            {
                "dtmf_key": "1",
                "destination_type": "staff",
                "destination_id": 202,
                "display_name": "Nandana V",
                "ring_timeout": 25,
                "is_active": True,
                "fallback_action": "main_ivr"
            }
        ]

        with patch.object(CallFlowInterpreter, '_get_published_direct_routing_options', return_value=test_options):
            query_mock = MagicMock()
            self.mock_db.query.return_value = query_mock
            query_mock.filter.return_value = query_mock
            query_mock.order_by.return_value = query_mock
            query_mock.first.side_effect = [mock_emp_b, mock_ep_b, None]

            res = CallFlowInterpreter.resolve_extension_destination(
                db=self.mock_db,
                company_id=1,
                extension="1"
            )

            self.assertEqual(res["status"], "available")
            self.assertEqual(res["destination_id"], 202)
            self.assertEqual(res["sip_uri"], "sip:nandana_202@phone.plivo.com")
            self.assertEqual(res["ring_timeout"], 25)

    def test_03_new_extension_dtmf_7(self):
        """Test C: Adding a new extension slot 7 routes correctly to Staff C."""
        mock_emp_c = MagicMock(spec=StaffEmployee)
        mock_emp_c.id = 303
        mock_emp_c.full_name = "Kavitha R"
        mock_emp_c.status = "active"
        mock_emp_c.is_deleted = False
        mock_emp_c.base_company_id = 1

        mock_ep_c = MagicMock(spec=TelephonyPlivoEndpoint)
        mock_ep_c.staff_id = 303
        mock_ep_c.is_registered = True
        mock_ep_c.plivo_username = "kavitha_303"

        test_options = [
            {
                "dtmf_key": "7",
                "destination_type": "staff",
                "destination_id": 303,
                "display_name": "Kavitha R",
                "ring_timeout": 20,
                "is_active": True,
            }
        ]

        with patch.object(CallFlowInterpreter, '_get_published_direct_routing_options', return_value=test_options):
            query_mock = MagicMock()
            self.mock_db.query.return_value = query_mock
            query_mock.filter.return_value = query_mock
            query_mock.order_by.return_value = query_mock
            query_mock.first.side_effect = [mock_emp_c, mock_ep_c, None]

            res = CallFlowInterpreter.resolve_extension_destination(
                db=self.mock_db,
                company_id=1,
                extension="7"
            )

            self.assertEqual(res["status"], "available")
            self.assertEqual(res["destination_id"], 303)
            self.assertEqual(res["sip_uri"], "sip:kavitha_303@phone.plivo.com")

    def test_04_disabled_extension_returns_inactive(self):
        """Test D: Disabling an extension slot (is_active=False) returns inactive_extension."""
        test_options = [
            {
                "dtmf_key": "7",
                "destination_type": "staff",
                "destination_id": 303,
                "is_active": False,
            }
        ]

        with patch.object(CallFlowInterpreter, '_get_published_direct_routing_options', return_value=test_options):
            res = CallFlowInterpreter.resolve_extension_destination(
                db=self.mock_db,
                company_id=1,
                extension="7"
            )

            self.assertEqual(res["status"], "inactive_extension")
            self.assertEqual(res["extension"], "7")

    def test_05_draft_vs_published_version_isolation(self):
        """Test E: Changes saved in draft flow do NOT affect live routing until published."""
        published_version = MagicMock(spec=TelephonyCallFlowVersion)
        published_version.id = 10
        published_version.version_number = 1
        published_version.status = 'published'
        published_version.flow_data = {
            "direct_routing": [
                {"dtmf_key": "1", "destination_type": "staff", "destination_id": 101, "is_active": True}
            ]
        }

        mock_flow = MagicMock(spec=TelephonyCallFlow)
        mock_flow.id = 1
        mock_flow.company_id = 1
        mock_flow.current_published_version_id = 10
        mock_flow.status = 'published'

        query_mock = MagicMock()
        self.mock_db.query.return_value = query_mock
        query_mock.filter.return_value = query_mock
        query_mock.order_by.return_value = query_mock
        query_mock.first.side_effect = [mock_flow, published_version]

        options = CallFlowInterpreter._get_published_direct_routing_options(
            db=self.mock_db,
            company_id=1,
            called_did="+918031728899"
        )

        self.assertEqual(len(options), 1)
        self.assertEqual(options[0]["destination_id"], 101)
        self.assertEqual(options[0]["dtmf_key"], "1")

    def test_06_multi_tenant_isolation(self):
        """Test F: Target employee belonging to a different company is rejected with tenant_mismatch."""
        mock_emp = MagicMock(spec=StaffEmployee)
        mock_emp.id = 101
        mock_emp.full_name = "External Staff"
        mock_emp.status = "active"
        mock_emp.is_deleted = False
        mock_emp.base_company_id = 99  # Company 99
        mock_emp.data_companies = [99]

        test_options = [
            {
                "dtmf_key": "1",
                "destination_type": "staff",
                "destination_id": 101,
                "is_active": True,
            }
        ]

        with patch.object(CallFlowInterpreter, '_get_published_direct_routing_options', return_value=test_options):
            query_mock = MagicMock()
            self.mock_db.query.return_value = query_mock
            query_mock.filter.return_value = query_mock
            query_mock.first.return_value = mock_emp

            res = CallFlowInterpreter.resolve_extension_destination(
                db=self.mock_db,
                company_id=1,
                extension="1"
            )

            self.assertEqual(res["status"], "tenant_mismatch")
            self.assertEqual(res["reason"], "cross_company_access_denied")

    def test_07_offline_and_busy_fallbacks(self):
        """Test G: Target staff offline (no endpoint) or busy (in call) returns offline/busy."""
        mock_emp = MagicMock(spec=StaffEmployee)
        mock_emp.id = 101
        mock_emp.full_name = "Pujita Sharma"
        mock_emp.status = "active"
        mock_emp.is_deleted = False
        mock_emp.base_company_id = 1
        mock_emp.data_companies = [1]

        test_options = [{"dtmf_key": "1", "destination_type": "staff", "destination_id": 101, "is_active": True}]

        # Case 1: No registered endpoint -> offline
        with patch.object(CallFlowInterpreter, '_get_published_direct_routing_options', return_value=test_options):
            query_mock = MagicMock()
            self.mock_db.query.return_value = query_mock
            query_mock.filter.return_value = query_mock
            query_mock.order_by.return_value = query_mock
            query_mock.first.side_effect = [mock_emp, None]

            res = CallFlowInterpreter.resolve_extension_destination(self.mock_db, 1, "1")
            self.assertEqual(res["status"], "offline")

        # Case 2: Endpoint registered, but active call session in progress -> busy
        mock_ep = MagicMock(spec=TelephonyPlivoEndpoint)
        mock_ep.staff_id = 101
        mock_ep.is_registered = True
        mock_ep.plivo_username = "pujita_101"

        mock_active_call = MagicMock(spec=VoIPCallSession)
        mock_active_call.id = 999

        with patch.object(CallFlowInterpreter, '_get_published_direct_routing_options', return_value=test_options):
            query_mock = MagicMock()
            self.mock_db.query.return_value = query_mock
            query_mock.filter.return_value = query_mock
            query_mock.order_by.return_value = query_mock
            query_mock.first.side_effect = [mock_emp, mock_ep, mock_active_call]

            res = CallFlowInterpreter.resolve_extension_destination(self.mock_db, 1, "1")
            self.assertEqual(res["status"], "busy")
            self.assertEqual(res["active_call_id"], 999)

    # =========================================================================
    # 2. INBOUND ROUTING & GATE INVARIANTS (Sticky, Generic Prompt, Gather)
    # =========================================================================

    def test_08_sticky_routing_precedes_extension_prompt(self):
        """Test H: Sticky caller evaluation strictly precedes extension prompt."""
        mock_sess = MagicMock(spec=VoIPCallSession, call_session_id="vcs_test_123")

        def query_side_effect(model):
            q = MagicMock()
            q.filter.return_value = q
            q.order_by.return_value = q
            if model == TelephonyDIDMapping:
                q.first.return_value = MagicMock(spec=TelephonyDIDMapping, did_number="+918031728899", is_active=True)
            elif model == VoIPCallSession:
                q.first.return_value = mock_sess
            elif model == TelephonyCallFlow:
                q.first.return_value = None
            else:
                q.first.return_value = None
            return q

        self.mock_db.query.side_effect = query_side_effect

        with patch.object(CallFlowInterpreter, '_resolve_company_from_did', return_value=1):
            with patch.object(CallFlowInterpreter, '_evaluate_business_hours', return_value=(True, "Open")):
                with patch.object(CallFlowInterpreter, '_is_qualified_sticky_caller', return_value=True):
                    with patch.object(CallFlowInterpreter, '_check_sticky_agent', return_value="<Response><Dial>StickyAgent</Dial></Response>"):
                        xml = CallFlowInterpreter.handle_inbound_call(
                            db=self.mock_db,
                            caller_phone="+919876543210",
                            called_did="+918031728899",
                            provider_call_id="call_uuid_test"
                        )
                        self.assertIn("StickyAgent", xml)
                        self.assertNotIn("Please press the extension number", xml)

    def test_09_sticky_caller_with_offline_agent_bypasses_extension_prompt(self):
        """Test H2: Sticky caller whose agent is offline goes to Main IVR and NEVER enters extension prompt."""
        mock_sess = MagicMock(spec=VoIPCallSession, call_session_id="vcs_test_123")

        def query_side_effect(model):
            q = MagicMock()
            q.filter.return_value = q
            q.order_by.return_value = q
            if model == TelephonyDIDMapping:
                q.first.return_value = MagicMock(spec=TelephonyDIDMapping, did_number="+918031728899", is_active=True)
            elif model == VoIPCallSession:
                q.first.return_value = mock_sess
            elif model == TelephonyCallFlow:
                q.first.return_value = None
            else:
                q.first.return_value = None
            return q

        self.mock_db.query.side_effect = query_side_effect

        with patch.object(CallFlowInterpreter, '_resolve_company_from_did', return_value=1):
            with patch.object(CallFlowInterpreter, '_evaluate_business_hours', return_value=(True, "Open")):
                with patch.object(CallFlowInterpreter, '_is_qualified_sticky_caller', return_value=True):
                    with patch.object(CallFlowInterpreter, '_check_sticky_agent', return_value=None):
                        with patch.object(CallFlowInterpreter, '_detect_crm_caller_language', return_value='en'):
                            with patch.object(CallFlowInterpreter, '_get_department_menu_xml', return_value="<Response><Speak>Main IVR Menu</Speak></Response>"):
                                xml = CallFlowInterpreter.handle_inbound_call(
                                    db=self.mock_db,
                                    caller_phone="+919876543210",
                                    called_did="+918031728899",
                                    provider_call_id="call_uuid_test"
                                )
                                self.assertIn("Main IVR Menu", xml)
                                self.assertNotIn("Please press the extension number", xml)

    def test_10_generic_extension_prompt_without_employee_names(self):
        """Test I: Direct routing prompt does NOT announce employee names."""
        options = [
            {"dtmf_key": "1", "display_name": "Pujita", "is_active": True},
            {"dtmf_key": "2", "display_name": "Nandana", "is_active": True}
        ]
        prompt = CallFlowInterpreter._build_direct_routing_prompt(options)
        self.assertEqual(prompt, "Please press the extension number, or stay on the line for our main menu.")
        self.assertNotIn("Pujita", prompt)
        self.assertNotIn("Nandana", prompt)

    def test_11_gather_timeout_silence_seamlessly_falls_through_to_main_ivr(self):
        """Test J: Silence / no DTMF seamlessly falls through to Main IVR without error message."""
        with patch.object(CallFlowInterpreter, '_get_department_menu_xml', return_value="<Response><Speak>Welcome to Main Menu</Speak></Response>"):
            xml = CallFlowInterpreter.handle_ivr_gather(
                db=self.mock_db,
                caller_phone="+919876543210",
                called_did="+918031728899",
                digits="",
                menu_type="direct_routing",
                lang="en"
            )
            self.assertIn("Welcome to Main Menu", xml)
            self.assertNotIn("unavailable", xml.lower())
            self.assertNotIn("invalid", xml.lower())

    # =========================================================================
    # 3. WHATSAPP STAFF SIGNATURE & DYNAMIC EXTENSION INTEGRATION
    # =========================================================================

    def test_12_whatsapp_signature_with_extension(self):
        """Test K: Message sent by staff with active extension has full signature block."""
        msg = "Hello, your solar quote is ready."
        formatted = format_staff_whatsapp_message(
            message=msg,
            staff_name="Pujita",
            contact_number="8585852738",
            extension="1"
        )
        expected = (
            "Hello, your solar quote is ready.\n\n"
            "Regards,\n"
            "Pujita\n"
            "8585852738\n"
            "Ext: 1"
        )
        self.assertEqual(formatted, expected)

    def test_13_whatsapp_signature_without_extension(self):
        """Test L: Message sent by staff without extension includes Name + 8585852738 ONLY."""
        msg = "Namaskaram! Here is the brochure."
        formatted = format_staff_whatsapp_message(
            message=msg,
            staff_name="Pujita",
            contact_number="8585852738",
            extension=None
        )
        expected = (
            "Namaskaram! Here is the brochure.\n\n"
            "Regards,\n"
            "Pujita\n"
            "8585852738"
        )
        self.assertEqual(formatted, expected)
        self.assertNotIn("Ext:", formatted)
        self.assertNotIn("N/A", formatted)
        self.assertNotIn("undefined", formatted)

    def test_14_whatsapp_signature_idempotency_and_stripping(self):
        """Test M: Re-formatting or forwarding strips previous signature cleanly."""
        orig_msg = (
            "Hello!\n\n"
            "Regards,\n"
            "Pujita\n"
            "8585852738\n"
            "Ext: 1"
        )

        stripped = strip_staff_whatsapp_signature(orig_msg)
        self.assertEqual(stripped, "Hello!")

        # Forwarding from Nandana (Ext: 2) replaces Pujita's signature
        reformatted = format_staff_whatsapp_message(
            message=orig_msg,
            staff_name="Nandana",
            contact_number="8585852738",
            extension="2"
        )
        expected = (
            "Hello!\n\n"
            "Regards,\n"
            "Nandana\n"
            "8585852738\n"
            "Ext: 2"
        )
        self.assertEqual(reformatted, expected)
        self.assertNotIn("Pujita", reformatted)

    def test_15_dynamic_extension_lookup_reflects_flow_updates(self):
        """Test N: Staff extension dynamically updates when call flow is published."""
        test_options_v1 = [
            {"dtmf_key": "1", "destination_type": "staff", "destination_id": 101, "is_active": True}
        ]

        with patch.object(CallFlowInterpreter, '_get_published_direct_routing_options', return_value=test_options_v1):
            ext_v1 = CallFlowInterpreter.get_staff_configured_extension(self.mock_db, 1, 101)
            self.assertEqual(ext_v1, "1")

        # Now suppose in Call Flow Studio, Admin swaps Staff 101 to Extension 4 and publishes
        test_options_v2 = [
            {"dtmf_key": "4", "destination_type": "staff", "destination_id": 101, "is_active": True}
        ]

        with patch.object(CallFlowInterpreter, '_get_published_direct_routing_options', return_value=test_options_v2):
            ext_v2 = CallFlowInterpreter.get_staff_configured_extension(self.mock_db, 1, 101)
            self.assertEqual(ext_v2, "4")

            # Signature automatically reflects Ext: 4 without any code edit
            msg_v2 = format_staff_whatsapp_message("Test message", "Pujita", extension=ext_v2)
            self.assertIn("Ext: 4", msg_v2)


if __name__ == '__main__':
    unittest.main()
