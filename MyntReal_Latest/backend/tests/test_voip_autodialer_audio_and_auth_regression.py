"""
Regression Test Suite — Auto-Dialer One-Way Audio & Call-Disconnect Architectural Fixes
Verifies:
1. Lead ID type safety in VoIPCallService.initiate_in_app_call:
   - Valid integer lead_id preserved
   - Numeric string lead_id converted to int
   - Empty string, whitespace, None, invalid non-numeric strings normalized to None
2. Call termination authorization:
   - Legitimate operator owner can terminate their call
   - Supreme / Super-admin (MR10001, VGK4U, is_supreme) can terminate
   - Multi-company staff with data_companies containing dicts [{'company_id': 4}] can terminate
   - Unauthorized cross-user and cross-company terminations are rejected with 403
3. Plivo Browser SDK & Mobile SDK configuration:
   - enableNoiseReduction: false (bypasses AudioWorklet / WASM one-way audio failure)
   - Native WebRTC constraints (echoCancellation, noiseSuppression, autoGainControl) preserved
4. Synchronous user gesture audio unlock in staff_dialer.html, staff_header.js, plivo-softphone.js
5. Session watcher monotonic safety guarding healthy connected calls from stale pre-answer states
Created: Sep 2026
"""

import unittest
from unittest.mock import MagicMock, patch
from fastapi import HTTPException
from pathlib import Path

from app.models.voip_call_session import VoIPCallSession
from app.models.voip_enums import CallStateEnum, CallMethodEnum
from app.services.voip_call_service import VoIPCallService
from app.models.base import get_indian_time


class TestVoIPAutoDialerAudioAndAuthRegression(unittest.TestCase):

    def setUp(self):
        self.mock_db = MagicMock()
        # Mock CRM lead lookup
        self.mock_lead = MagicMock()
        self.mock_lead.id = 8850
        self.mock_lead.company_id = 4
        self.mock_lead.phone = "+918143450736"

        self.mock_db.query.return_value.filter.return_value.first.return_value = self.mock_lead
        self.mock_db.query.return_value.filter.return_value.order_by.return_value.first.return_value = None

    # ── 1. LEAD_ID TYPE SAFETY ──────────────────────────────────────────────

    def test_lead_id_type_safety_valid_int(self):
        user = MagicMock()
        user.id = 320
        user.emp_code = "MN10017"
        user.base_company_id = 4
        user.data_companies = [4]

        with patch("app.services.voip_call_service.get_telephony_provider") as mock_provider:
            prov_inst = MagicMock()
            prov_inst.provider_name = "plivo"
            mock_provider.return_value = prov_inst

            session = VoIPCallService.initiate_in_app_call(
                db=self.mock_db,
                current_user=user,
                customer_phone="+918143450736",
                lead_id=8850,
                dispatch_provider_call=False
            )
            self.assertEqual(session.lead_id, 8850)
            self.assertIsInstance(session.lead_id, int)

    def test_lead_id_type_safety_numeric_string(self):
        user = MagicMock()
        user.id = 320
        user.emp_code = "MN10017"
        user.base_company_id = 4
        user.data_companies = [4]

        with patch("app.services.voip_call_service.get_telephony_provider") as mock_provider:
            prov_inst = MagicMock()
            prov_inst.provider_name = "plivo"
            mock_provider.return_value = prov_inst

            session = VoIPCallService.initiate_in_app_call(
                db=self.mock_db,
                current_user=user,
                customer_phone="+918143450736",
                lead_id="8850",
                dispatch_provider_call=False
            )
            self.assertEqual(session.lead_id, 8850)
            self.assertIsInstance(session.lead_id, int)

    def test_lead_id_type_safety_empty_string(self):
        user = MagicMock()
        user.id = 320
        user.emp_code = "MN10017"
        user.base_company_id = 4
        user.data_companies = [4]

        with patch("app.services.voip_call_service.get_telephony_provider") as mock_provider:
            prov_inst = MagicMock()
            prov_inst.provider_name = "plivo"
            mock_provider.return_value = prov_inst

            session = VoIPCallService.initiate_in_app_call(
                db=self.mock_db,
                current_user=user,
                customer_phone="+918143450736",
                lead_id="",
                dispatch_provider_call=False
            )
            self.assertIsNone(session.lead_id)

    def test_lead_id_type_safety_whitespace_string(self):
        user = MagicMock()
        user.id = 320
        user.emp_code = "MN10017"
        user.base_company_id = 4
        user.data_companies = [4]

        with patch("app.services.voip_call_service.get_telephony_provider") as mock_provider:
            prov_inst = MagicMock()
            prov_inst.provider_name = "plivo"
            mock_provider.return_value = prov_inst

            session = VoIPCallService.initiate_in_app_call(
                db=self.mock_db,
                current_user=user,
                customer_phone="+918143450736",
                lead_id="   ",
                dispatch_provider_call=False
            )
            self.assertIsNone(session.lead_id)

    def test_lead_id_type_safety_none(self):
        user = MagicMock()
        user.id = 320
        user.emp_code = "MN10017"
        user.base_company_id = 4
        user.data_companies = [4]

        with patch("app.services.voip_call_service.get_telephony_provider") as mock_provider:
            prov_inst = MagicMock()
            prov_inst.provider_name = "plivo"
            mock_provider.return_value = prov_inst

            session = VoIPCallService.initiate_in_app_call(
                db=self.mock_db,
                current_user=user,
                customer_phone="+918143450736",
                lead_id=None,
                dispatch_provider_call=False
            )
            self.assertIsNone(session.lead_id)

    def test_lead_id_type_safety_invalid_non_numeric(self):
        user = MagicMock()
        user.id = 320
        user.emp_code = "MN10017"
        user.base_company_id = 4
        user.data_companies = [4]

        with patch("app.services.voip_call_service.get_telephony_provider") as mock_provider:
            prov_inst = MagicMock()
            prov_inst.provider_name = "plivo"
            mock_provider.return_value = prov_inst

            for bad_id in ["invalid_lead", "null", "undefined", "abc!@#"]:
                session = VoIPCallService.initiate_in_app_call(
                    db=self.mock_db,
                    current_user=user,
                    customer_phone="+918143450736",
                    lead_id=bad_id,
                    dispatch_provider_call=False
                )
                self.assertIsNone(session.lead_id)

    # ── 2. CALL TERMINATION AUTHORIZATION ───────────────────────────────────

    def _create_mock_session(self, company_id=4, operator_id=320, operator_ref="MN10017"):
        session = VoIPCallSession(
            call_session_id="vcs_test_auth_1234",
            company_id=company_id,
            operator_id=operator_id,
            operator_user_ref=operator_ref,
            destination_number="+918143450736",
            customer_phone="+918143450736",
            direction="outbound",
            provider="plivo",
            status=CallStateEnum.DIALING.value,
            started_at=get_indian_time()
        )
        return session

    def test_legitimate_operator_owner_can_terminate(self):
        session = self._create_mock_session(company_id=4, operator_id=320, operator_ref="MN10017")
        self.mock_db.query.return_value.filter.return_value.first.return_value = session

        user = MagicMock()
        user.id = 320
        user.emp_code = "MN10017"
        user.base_company_id = 1
        user.data_companies = []

        with patch("app.services.voip_call_service.get_telephony_provider") as mock_provider:
            prov_inst = MagicMock()
            mock_provider.return_value = prov_inst

            ended_session = VoIPCallService.end_in_app_call(
                db=self.mock_db,
                current_user=user,
                call_session_id=session.call_session_id
            )
            self.assertEqual(ended_session.status, CallStateEnum.ENDED.value)

    def test_supreme_admin_can_terminate_any_session(self):
        session = self._create_mock_session(company_id=99, operator_id=500, operator_ref="MN99999")
        self.mock_db.query.return_value.filter.return_value.first.return_value = session

        # Test MR10001
        admin1 = MagicMock()
        admin1.id = 1
        admin1.emp_code = "MR10001"
        admin1.staff_type = "STAFF"
        admin1.base_company_id = 1
        admin1.data_companies = []

        with patch("app.services.voip_call_service.get_telephony_provider") as mock_provider:
            prov_inst = MagicMock()
            mock_provider.return_value = prov_inst

            ended1 = VoIPCallService.end_in_app_call(
                db=self.mock_db,
                current_user=admin1,
                call_session_id=session.call_session_id
            )
            self.assertEqual(ended1.status, CallStateEnum.ENDED.value)

        # Test VGK4U Supreme staff_type
        session.status = CallStateEnum.CONNECTED.value
        admin2 = MagicMock()
        admin2.id = 10
        admin2.emp_code = "MN10002"
        admin2.staff_type = "VGK4U Supreme"
        admin2.base_company_id = 2
        admin2.data_companies = []

        with patch("app.services.voip_call_service.get_telephony_provider") as mock_provider:
            prov_inst = MagicMock()
            mock_provider.return_value = prov_inst

            ended2 = VoIPCallService.end_in_app_call(
                db=self.mock_db,
                current_user=admin2,
                call_session_id=session.call_session_id
            )
            self.assertEqual(ended2.status, CallStateEnum.ENDED.value)

    def test_data_companies_with_dictionaries_allows_authorized_tenant(self):
        session = self._create_mock_session(company_id=4, operator_id=500, operator_ref="OTHER_OP")
        self.mock_db.query.return_value.filter.return_value.first.return_value = session

        # User is not operator owner, not supreme, but has company 4 in data_companies as dict
        user = MagicMock()
        user.id = 320
        user.emp_code = "MN10017"
        user.staff_type = "STAFF"
        user.base_company_id = 1
        user.data_companies = [{"company_id": 4}, {"company_id": 2}]

        with patch("app.services.voip_call_service.get_telephony_provider") as mock_provider:
            prov_inst = MagicMock()
            mock_provider.return_value = prov_inst

            ended = VoIPCallService.end_in_app_call(
                db=self.mock_db,
                current_user=user,
                call_session_id=session.call_session_id
            )
            self.assertEqual(ended.status, CallStateEnum.ENDED.value)

    def test_unauthorized_cross_user_cross_company_termination_rejected(self):
        session = self._create_mock_session(company_id=4, operator_id=320, operator_ref="MN10017")
        self.mock_db.query.return_value.filter.return_value.first.return_value = session

        # Attacker / unauthorized user from different company (company 3)
        unauth_user = MagicMock()
        unauth_user.id = 999
        unauth_user.emp_code = "MN99999"
        unauth_user.staff_type = "STAFF"
        unauth_user.is_supreme = False
        unauth_user.base_company_id = 3
        unauth_user.data_companies = [3, {"company_id": 2}]

        with self.assertRaises(HTTPException) as ctx:
            VoIPCallService.end_in_app_call(
                db=self.mock_db,
                current_user=unauth_user,
                call_session_id=session.call_session_id
            )
        self.assertEqual(ctx.exception.status_code, 403)
        self.assertIn("Unauthorized access", ctx.exception.detail)

    # ── 3. AUDIO & NOISE REDUCTION CONFIGURATION VERIFICATION ───────────────

    def test_plivo_softphone_js_noise_reduction_disabled(self):
        js_path = Path(__file__).resolve().parent.parent.parent / "frontend" / "public" / "js" / "plivo-softphone.js"
        self.assertTrue(js_path.exists(), f"plivo-softphone.js not found at {js_path}")
        content = js_path.read_text(encoding="utf-8")

        # Verify enableNoiseReduction is set to false in SDK options
        self.assertIn("enableNoiseReduction: false", content)
        self.assertNotIn("enableNoiseReduction: true", content)

        # Verify native WebRTC constraints are preserved
        self.assertIn("echoCancellation: true", content)
        self.assertIn("noiseSuppression: true", content)
        self.assertIn("autoGainControl: true", content)

    def test_mobile_telephony_service_noise_reduction_disabled(self):
        ts_path = Path(__file__).resolve().parent.parent.parent / "mobile" / "src" / "services" / "telephony.service.ts"
        self.assertTrue(ts_path.exists(), f"telephony.service.ts not found at {ts_path}")
        content = ts_path.read_text(encoding="utf-8")

        # Verify enableNoiseReduction is set to false in SDK options
        self.assertIn("enableNoiseReduction: false", content)
        self.assertNotIn("enableNoiseReduction: true", content)

        # Verify native WebRTC constraints are preserved
        self.assertIn("echoCancellation: true", content)
        self.assertIn("noiseSuppression: true", content)
        self.assertIn("autoGainControl: true", content)

    # ── 4. SYNCHRONOUS USER GESTURE UNLOCK VERIFICATION ─────────────────────

    def test_staff_dialer_synchronous_user_activation(self):
        html_path = Path(__file__).resolve().parent.parent.parent / "frontend" / "staff_dialer.html"
        self.assertTrue(html_path.exists(), f"staff_dialer.html not found at {html_path}")
        content = html_path.read_text(encoding="utf-8")

        # Check doDial invokes unlockAudioOnUserGesture synchronously
        self.assertIn("unlockAudioOnUserGesture", content)
        do_dial_idx = content.find("function doDial(")
        self.assertNotEqual(do_dial_idx, -1)
        do_dial_body = content[do_dial_idx:do_dial_idx + 2500]
        unlock_idx = do_dial_body.find("unlockAudioOnUserGesture")
        dial_idx = do_dial_body.find("window.PlivoSoftphone.dial(")
        self.assertNotEqual(unlock_idx, -1)
        self.assertNotEqual(dial_idx, -1)
        # Unlock must precede the dial call, and dial must be synchronous
        self.assertLess(unlock_idx, dial_idx)

    def test_staff_header_synchronous_user_activation(self):
        header_path = Path(__file__).resolve().parent.parent.parent / "frontend" / "staff_header.js"
        self.assertTrue(header_path.exists(), f"staff_header.js not found at {header_path}")
        content = header_path.read_text(encoding="utf-8")

        self.assertIn("window.openCallDialer = function(intent)", content)
        open_dialer_idx = content.find("window.openCallDialer = function(intent)")
        open_dialer_body = content[open_dialer_idx:open_dialer_idx + 300]
        self.assertIn("unlockAudioOnUserGesture", open_dialer_body)

    # ── 5. SESSION WATCHER MONOTONIC SAFETY VERIFICATION ────────────────────

    def test_session_watcher_monotonic_safety_code(self):
        js_path = Path(__file__).resolve().parent.parent.parent / "frontend" / "public" / "js" / "plivo-softphone.js"
        content = js_path.read_text(encoding="utf-8")

        # Check that startSessionWatcher checks local connected state before terminating
        self.assertIn("isConnectedLocal = this.isCallConnected && !!this.callConnectedTime", content)
        self.assertIn("shouldTerminate = isTerminalState && (!isConnectedLocal", content)


if __name__ == "__main__":
    unittest.main()
