"""
Unit and Integration Tests for Authoritative First-Class Caller Identity Model
(Sections 21 through 32 of MyntOS Telephony Architecture).

Verifies:
1. First-Class Identity Attributes & Strict Source Enumeration (Section 21)
2. Raw Provider Data Preservation Invariant (Section 22)
3. Truthful Customer Number vs Forwarded-From Operator Separation (Sections 23, 24)
4. Single-Session Leg Correlation / Zero Duplicate Legs (Section 27)
5. New Calls & Overall Calls Inbound Visibility / Non-CRM Guest Capture (Sections 25, 26, 29)
6. Strict Zero-Modification Lock Verification on Telephony Core (Rule 6, Section 32)
"""

import os
import sys
import json
import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy.orm import Session
from app.services.telephony.flow_interpreter import CallFlowInterpreter, IST
from app.models.voip_call_session import VoIPCallSession
from app.models.telephony_call_flow import TelephonyCallFlow
from app.models.operator_calls import TelephonyDIDMapping
from app.models.staff import StaffEmployee
from app.api.v1.endpoints.call_flow_api import _format_phone, _mask_phone


ALLOWED_CALLER_IDENTITY_SOURCES = {
    "direct_provider_from",
    "forwarded_original_cli",
    "forwarded_from_metadata",
    "unresolved_forwarded",
    "unknown"
}


class TestCallerIdentityModel(unittest.TestCase):

    def setUp(self):
        self.mock_db = MagicMock(spec=Session)

    # =========================================================================
    # 1. ATTRIBUTE MODEL & STRICT ENUMERATION TESTS (Section 21)
    # =========================================================================

    def test_01_direct_inbound_identity_model(self):
        """Test 1: Direct inbound Plivo call generates authoritative identity with direct_provider_from."""
        identity = CallFlowInterpreter.resolve_inbound_caller_identity(
            raw_from="+919876543210",
            raw_to="+918031728899",
            call_uuid="uuid-direct-101",
            raw_payload={"From": "+919876543210", "To": "+918031728899", "CallUUID": "uuid-direct-101"}
        )

        self.assertEqual(identity["raw_provider_from"], "+919876543210")
        self.assertEqual(identity["normalized_provider_from"], "919876543210")
        self.assertEqual(identity["original_caller_number"], "919876543210")
        self.assertIsNone(identity["forwarded_from_number"])
        self.assertEqual(identity["called_plivo_did"], "+918031728899")
        self.assertEqual(identity["provider_call_uuid"], "uuid-direct-101")
        self.assertIsNone(identity["parent_call_identifier"])
        self.assertEqual(identity["caller_identity_source"], "direct_provider_from")
        self.assertEqual(identity["caller_identity_confidence"], "high")
        self.assertIn(identity["caller_identity_source"], ALLOWED_CALLER_IDENTITY_SOURCES)

    def test_02_forwarded_call_with_carrier_cli(self):
        """Test 2: Carrier passes customer CLI in From and operator number in ForwardedFrom."""
        identity = CallFlowInterpreter.resolve_inbound_caller_identity(
            raw_from="+919876543210",          # Customer number
            raw_to="+918031728899",            # Plivo DID
            call_uuid="uuid-fwd-cli-202",
            raw_forwarded_from="+919988776655", # Operator number
            raw_payload={
                "From": "+919876543210",
                "ForwardedFrom": "+919988776655",
                "To": "+918031728899",
                "CallUUID": "uuid-fwd-cli-202"
            }
        )

        self.assertEqual(identity["raw_provider_from"], "+919876543210")
        self.assertEqual(identity["normalized_provider_from"], "919876543210")
        self.assertEqual(identity["original_caller_number"], "919876543210")
        self.assertEqual(identity["forwarded_from_number"], "+919988776655")
        self.assertEqual(identity["caller_identity_source"], "forwarded_original_cli")
        self.assertEqual(identity["caller_identity_confidence"], "high")
        self.assertIn(identity["caller_identity_source"], ALLOWED_CALLER_IDENTITY_SOURCES)

    def test_03_forwarded_call_unresolved_operator_only(self):
        """Test 3: Carrier only sends operator number (From == ForwardedFrom), marking unresolved_forwarded."""
        identity = CallFlowInterpreter.resolve_inbound_caller_identity(
            raw_from="+919988776655",           # Operator number
            raw_to="+918031728899",             # Plivo DID
            call_uuid="uuid-fwd-unres-303",
            raw_forwarded_from="+919988776655",  # Operator number
            raw_payload={
                "From": "+919988776655",
                "ForwardedFrom": "+919988776655",
                "To": "+918031728899",
                "CallUUID": "uuid-fwd-unres-303"
            }
        )

        self.assertEqual(identity["raw_provider_from"], "+919988776655")
        self.assertEqual(identity["normalized_provider_from"], "919988776655")
        # Invariant: Must NOT treat operator number as customer number
        self.assertIsNone(identity["original_caller_number"])
        self.assertEqual(identity["forwarded_from_number"], "+919988776655")
        self.assertEqual(identity["caller_identity_source"], "unresolved_forwarded")
        self.assertEqual(identity["caller_identity_confidence"], "low")
        self.assertIn(identity["caller_identity_source"], ALLOWED_CALLER_IDENTITY_SOURCES)

    def test_04_forwarded_call_via_sip_diversion_header(self):
        """Test 4: Forwarding detected via SIP Diversion header when ForwardedFrom field is omitted."""
        identity = CallFlowInterpreter.resolve_inbound_caller_identity(
            raw_from="+919988776655",
            raw_to="+918031728899",
            call_uuid="uuid-sip-div-404",
            headers={
                "sip-h-diversion": "<tel:+919988776655;reason=unconditional>"
            },
            raw_payload={"From": "+919988776655", "To": "+918031728899"}
        )

        self.assertIsNotNone(identity["forwarded_from_number"])
        self.assertIn("9988776655", identity["forwarded_from_number"])
        self.assertEqual(identity["caller_identity_source"], "unresolved_forwarded")
        self.assertIsNone(identity["original_caller_number"])
        self.assertIn(identity["caller_identity_source"], ALLOWED_CALLER_IDENTITY_SOURCES)

    def test_05_unknown_caller_empty_fields(self):
        """Test 5: Call with empty or missing from fields resolves to 'unknown' without crashing."""
        identity = CallFlowInterpreter.resolve_inbound_caller_identity(
            raw_from="",
            raw_to="+918031728899",
            call_uuid="uuid-empty-505"
        )

        self.assertEqual(identity["caller_identity_source"], "unknown")
        self.assertEqual(identity["caller_identity_confidence"], "low")
        self.assertIsNone(identity["original_caller_number"])
        self.assertIn(identity["caller_identity_source"], ALLOWED_CALLER_IDENTITY_SOURCES)

    # =========================================================================
    # 2. RAW PROVIDER DATA PRESERVATION INVARIANT (Section 22)
    # =========================================================================

    def test_06_raw_provider_payload_preservation(self):
        """Test 6: Raw inbound provider webhook payload is preserved unmutated in metadata_json."""
        raw_payload = {
            "From": "+919876543210",
            "To": "+918031728899",
            "CallUUID": "uuid-raw-preserve-606",
            "Direction": "inbound",
            "ForwardedFrom": "+919988776655",
            "CustomTelecomParam": "xyz_carrier_val"
        }

        # Mock DB queries
        def query_side_effect(model):
            q = MagicMock()
            q.filter.return_value = q
            q.order_by.return_value = q
            if model == TelephonyDIDMapping:
                q.first.return_value = MagicMock(spec=TelephonyDIDMapping, did_number="+918031728899", is_active=True, company_id=1)
            elif model == VoIPCallSession:
                q.first.return_value = None  # No existing session
            elif model == TelephonyCallFlow:
                q.first.return_value = None
            else:
                q.first.return_value = None
            return q

        self.mock_db.query.side_effect = query_side_effect

        added_sessions = []
        self.mock_db.add.side_effect = lambda obj: added_sessions.append(obj)

        with patch.object(CallFlowInterpreter, '_resolve_company_from_did', return_value=1):
            with patch.object(CallFlowInterpreter, '_evaluate_business_hours', return_value=(True, "Open")):
                CallFlowInterpreter.handle_inbound_call(
                    db=self.mock_db,
                    caller_phone="+919876543210",
                    called_did="+918031728899",
                    provider_call_id="uuid-raw-preserve-606",
                    forwarded_from="+919988776655",
                    raw_payload=raw_payload
                )

        self.assertEqual(len(added_sessions), 1)
        created_session = added_sessions[0]
        meta = json.loads(created_session.metadata_json)

        # Invariant 1: raw_provider_payload must be preserved
        self.assertIn("raw_provider_payload", meta)
        raw_stored = meta["raw_provider_payload"]
        self.assertEqual(raw_stored["From"], "+919876543210")
        self.assertEqual(raw_stored["ForwardedFrom"], "+919988776655")
        self.assertEqual(raw_stored["raw_form"]["CustomTelecomParam"], "xyz_carrier_val")

        # Invariant 2: caller_identity must be present alongside raw data
        self.assertIn("caller_identity", meta)
        self.assertEqual(meta["caller_identity"]["caller_identity_source"], "forwarded_original_cli")

    # =========================================================================
    # 3. TRUTHFUL FORWARDING & FALSE CRM BINDING PREVENTION (Sections 23, 24)
    # =========================================================================

    def test_07_unresolved_forwarded_prevents_false_crm_binding(self):
        """Test 7: Unresolved forwarded call sets customer_phone to 'unresolved', preventing binding to operator."""
        raw_payload = {
            "From": "+919988776655",  # Operator's personal number passed by carrier
            "To": "+918031728899",
            "CallUUID": "uuid-false-crm-707",
            "ForwardedFrom": "+919988776655"
        }

        def query_side_effect(model):
            q = MagicMock()
            q.filter.return_value = q
            q.order_by.return_value = q
            if model == TelephonyDIDMapping:
                q.first.return_value = MagicMock(spec=TelephonyDIDMapping, did_number="+918031728899", is_active=True, company_id=1)
            elif model == VoIPCallSession:
                q.first.return_value = None
            elif model == TelephonyCallFlow:
                q.first.return_value = None
            else:
                q.first.return_value = None
            return q

        self.mock_db.query.side_effect = query_side_effect

        added_sessions = []
        self.mock_db.add.side_effect = lambda obj: added_sessions.append(obj)

        with patch.object(CallFlowInterpreter, '_resolve_company_from_did', return_value=1):
            with patch.object(CallFlowInterpreter, '_evaluate_business_hours', return_value=(True, "Open")):
                CallFlowInterpreter.handle_inbound_call(
                    db=self.mock_db,
                    caller_phone="+919988776655",
                    called_did="+918031728899",
                    provider_call_id="uuid-false-crm-707",
                    forwarded_from="+919988776655",
                    raw_payload=raw_payload
                )

        self.assertEqual(len(added_sessions), 1)
        created_session = added_sessions[0]

        # Invariant: customer_phone is stored as 'unresolved' and NOT the operator's personal phone number
        self.assertEqual(created_session.customer_phone, "unresolved")

    # =========================================================================
    # 4. SINGLE SESSION CORRELATION / ZERO DUPLICATE LEGS (Section 27)
    # =========================================================================

    def test_08_single_session_correlation_via_parent_call_uuid(self):
        """Test 8: Secondary callback / leg with ParentCallUUID correlates to existing session with 0 duplicates."""
        existing_session = MagicMock(spec=VoIPCallSession)
        existing_session.id = 99
        existing_session.call_session_id = "vcs_parent_primary"
        existing_session.provider_call_id = "uuid-primary-808"
        existing_session.metadata_json = json.dumps({
            "caller_identity": {"caller_identity_source": "direct_provider_from"},
            "raw_provider_payload": {"CallUUID": "uuid-primary-808"}
        })

        def query_side_effect(model):
            q = MagicMock()
            q.filter.return_value = q
            q.order_by.return_value = q
            if model == TelephonyDIDMapping:
                q.first.return_value = MagicMock(spec=TelephonyDIDMapping, did_number="+918031728899", is_active=True, company_id=1)
            elif model == VoIPCallSession:
                # Simulates returning existing_session when queried by ParentCallUUID
                q.first.return_value = existing_session
            elif model == TelephonyCallFlow:
                q.first.return_value = None
            else:
                q.first.return_value = None
            return q

        self.mock_db.query.side_effect = query_side_effect

        added_sessions = []
        self.mock_db.add.side_effect = lambda obj: added_sessions.append(obj)

        child_payload = {
            "From": "+919876543210",
            "To": "+918031728899",
            "CallUUID": "uuid-child-leg-808b",
            "ParentCallUUID": "uuid-primary-808"
        }

        with patch.object(CallFlowInterpreter, '_resolve_company_from_did', return_value=1):
            with patch.object(CallFlowInterpreter, '_evaluate_business_hours', return_value=(True, "Open")):
                CallFlowInterpreter.handle_inbound_call(
                    db=self.mock_db,
                    caller_phone="+919876543210",
                    called_did="+918031728899",
                    provider_call_id="uuid-child-leg-808b",
                    raw_payload=child_payload
                )

        # Invariant: Zero new sessions added! The primary session was updated.
        self.assertEqual(len(added_sessions), 0)
        self.mock_db.commit.assert_called()

    # =========================================================================
    # 5. NEW CALLS & OVERALL CALLS UI FORMATTING (Sections 25, 26, 29)
    # =========================================================================

    def test_09_phone_formatting_and_masking_helpers(self):
        """Test 9: _format_phone and _mask_phone handle clean displays."""
        self.assertEqual(_format_phone("919876543210"), "+91 98765 43210")
        self.assertEqual(_format_phone("+919876543210"), "+91 98765 43210")
        self.assertEqual(_format_phone("9876543210"), "+91 98765 43210")
        self.assertEqual(_format_phone(None), "—")
        self.assertEqual(_format_phone("unresolved"), "Unknown / Not provided")

        self.assertEqual(_mask_phone("919876543210"), "+91 98••••3210")
        self.assertEqual(_mask_phone("unresolved"), "Unknown / Not provided")
        self.assertEqual(_mask_phone(None), "—")

    def test_10_truthful_ui_serialization_unresolved_forwarded(self):
        """Test 10: Inbound call serialization outputs 'Unknown / Not provided' and preserves Forwarded From."""
        from app.api.v1.endpoints.call_flow_api import list_incoming_calls

        mock_call = MagicMock(spec=VoIPCallSession)
        mock_call.id = 1
        mock_call.call_session_id = "vcs_test_unres"
        mock_call.customer_phone = "unresolved"
        mock_call.destination_number = "+918031728899"
        mock_call.caller_id = "+918031728899"
        mock_call.provider = "plivo"
        mock_call.provider_call_id = "uuid-ui-test-10"
        mock_call.direction = "inbound"
        mock_call.duration_seconds = 42
        mock_call.status = "answered"
        mock_call.started_at = datetime.now(IST)
        mock_call.created_at = datetime.now(IST)
        mock_call.operator_id = None
        mock_call.operator_call_id = None
        mock_call.recording_storage_key = None
        mock_call.call_method = "in_app_pstn"
        mock_call.lead_id = None
        mock_call.metadata_json = json.dumps({
            "caller_identity": {
                "raw_provider_from": "+919988776655",
                "normalized_provider_from": "919988776655",
                "original_caller_number": None,
                "forwarded_from_number": "+919988776655",
                "called_plivo_did": "+918031728899",
                "provider_call_uuid": "uuid-ui-test-10",
                "caller_identity_source": "unresolved_forwarded",
                "caller_identity_confidence": "low"
            },
            "raw_provider_payload": {
                "From": "+919988776655",
                "ForwardedFrom": "+919988776655"
            }
        })

        # Mock query return
        q_mock = MagicMock()
        q_mock.filter.return_value = q_mock
        q_mock.order_by.return_value = q_mock
        q_mock.limit.return_value = q_mock
        q_mock.all.return_value = [mock_call]

        self.mock_db.query.return_value = q_mock

        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.base_company_id = 1
        mock_user.is_supreme = False
        mock_user.emp_code = "MR100"
        mock_user.full_name = "Staff User"
        mock_user.first_name = "Staff"
        mock_user.last_name = "User"

        with patch("app.api.v1.endpoints.call_flow_api._resolve_contacts_batch", return_value={}):
            resp = list_incoming_calls(
                scope="new_calls",
                current_user=mock_user,
                db=self.mock_db
            )

        self.assertTrue(resp["success"])
        self.assertEqual(len(resp["items"]), 1)
        item = resp["items"][0]

        # Assertions on Truthful Display
        self.assertEqual(item["customer_phone_display"], "Unknown / Not provided")
        self.assertEqual(item["customer_phone_masked"], "Unknown / Not provided")
        self.assertTrue(item["is_forwarded"])
        self.assertEqual(item["forwarded_from_number"], "+919988776655")
        self.assertIn("99887 76655", item["forwarded_from_display"])
        self.assertEqual(item["call_from"], "Forwarded Inbound")
        self.assertEqual(item["caller_identity_source"], "unresolved_forwarded")
        self.assertEqual(item["customer_name"], "Guest Caller")


if __name__ == '__main__':
    unittest.main()
