"""
CRM Lead Contact Privacy & Server-Side Click-to-Call Security Test Suite
20-Point Comprehensive Authorization, Privacy, Masking & Telephony Verification Suite.
Guarantees:
- Zero DB pollution (isolated test IDs >= 9600 / > 442, strict tearDown cleanup)
- Zero financial or points mutation
- Full privacy enforcement: raw phone never exposed to indirect/unauthorized callers
- Concurrency reservation & lock verification
"""

import os
import sys
import json
import unittest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
from sqlalchemy import text

# Dynamic path resolution (NO ABSOLUTE PATHS)
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.core.database import SessionLocal
from app.models.staff_accounts import OfficialPartner, VGKPointsLedger
from app.models.staff import StaffEmployee
from app.models.crm import CRMLead
from app.services.crm_contact_privacy import (
    mask_phone_canonical,
    is_in_partner_downline,
    evaluate_lead_contact_authorization,
    acquire_lead_call_reservation,
    initiate_lead_click_to_call,
)
from fastapi import HTTPException


class TestCRMContactPrivacyAndDialer(unittest.TestCase):
    """
    20-Point Security Test Suite for CRM Lead Contact Privacy & Server-Side Click-to-Call.
    """

    @classmethod
    def setUpClass(cls):
        cls.db = SessionLocal()
        # Clean up any leftover test data
        cls._cleanup_db(cls.db)

        # Record baseline counts to guarantee zero leakage
        cls.baseline_partners = cls.db.execute(text("SELECT count(*) FROM official_partners WHERE category = 'VGK_TEAM'")).scalar()
        cls.baseline_ledger_v2 = cls.db.execute(text("SELECT count(*) FROM vgk_points_ledger")).scalar()
        cls.baseline_archive_v1 = cls.db.execute(text("SELECT count(*) FROM vgk_points_ledger_v1_archive")).scalar()
        cls.baseline_paid_cash = cls.db.execute(text("SELECT count(*) FROM vgk_cash_income_entries WHERE status = 'PAID'")).scalar()

        # Build 5-level test partner hierarchy:
        # L4 Ancestor (9901) -> L3 Ancestor (9902) -> L2 Ancestor (9903) -> L1 Sponsor (9904) -> Producer (9905)
        cls.db.execute(text("""
            INSERT INTO official_partners (id, partner_code, partner_name, phone, category, is_active, parent_partner_id, created_at, updated_at)
            VALUES
                (9901, 'TEST_L4_9901', 'Test L4 Partner', '9800000001', 'VGK_TEAM', true, NULL, NOW(), NOW()),
                (9902, 'TEST_L3_9902', 'Test L3 Partner', '9800000002', 'VGK_TEAM', true, 9901, NOW(), NOW()),
                (9903, 'TEST_L2_9903', 'Test L2 Partner', '9800000003', 'VGK_TEAM', true, 9902, NOW(), NOW()),
                (9904, 'TEST_L1_9904', 'Test L1 Sponsor', '9800000004', 'VGK_TEAM', true, 9903, NOW(), NOW()),
                (9905, 'TEST_PROD_9905', 'Test Producer', '9800000005', 'VGK_TEAM', true, 9904, NOW(), NOW()),
                (9906, 'TEST_UNRELATED_9906', 'Test Unrelated Partner', '9800000006', 'VGK_TEAM', true, NULL, NOW(), NOW()),
                (9907, 'TEST_SUPP_9907', 'Test Support Partner', '9800000007', 'VGK_TEAM', true, NULL, NOW(), NOW())
        """))

        # Create test staff employees
        cls.db.execute(text("""
            INSERT INTO staff_employees (
                id, emp_code, full_name, email, phone, staff_type,
                role_id, base_company_id, status, date_of_joining, password_hash,
                created_at, updated_at
            ) VALUES
                (9911, 'TEST_ADMIN_9911', 'Admin Staff', 'admin9911@test.com', '9800000011', 'ADMIN', 6, 1, 'active', CURRENT_DATE, 'hash123', NOW(), NOW()),
                (9912, 'TEST_TC_9912', 'Telecaller Staff', 'tc9912@test.com', '9800000012', 'TELECALLER', 5, 1, 'active', CURRENT_DATE, 'hash123', NOW(), NOW()),
                (9913, 'TEST_SALES_9913', 'Indirect Sales Staff', 'sales9913@test.com', '9800000013', 'SALES', 5, 1, 'active', CURRENT_DATE, 'hash123', NOW(), NOW()),
                (9914, 'TEST_CROSS_9914', 'Cross Co Staff', 'cross9914@test.com', '9800000014', 'SALES', 5, 99, 'active', CURRENT_DATE, 'hash123', NOW(), NOW())
        """))

        # Create test CRM lead (ID 9950) owned by Producer 9905
        cls.db.execute(text("""
            INSERT INTO crm_leads (
                id, company_id, name, phone, alternate_phone, email,
                associated_partner_id, telecaller_id, status, priority,
                handler_type, created_at, updated_at
            ) VALUES (
                9950, 1, 'Test Customer Privacy', '9988776655', '9988776644', 'customer9950@test.com',
                9905, 9912, 'new', 'high',
                'unassigned', NOW(), NOW()
            )
        """))
        cls.db.commit()

        # Load ORM references
        cls.p_l4 = cls.db.query(OfficialPartner).filter(OfficialPartner.id == 9901).first()
        cls.p_l3 = cls.db.query(OfficialPartner).filter(OfficialPartner.id == 9902).first()
        cls.p_l2 = cls.db.query(OfficialPartner).filter(OfficialPartner.id == 9903).first()
        cls.p_l1 = cls.db.query(OfficialPartner).filter(OfficialPartner.id == 9904).first()
        cls.p_producer = cls.db.query(OfficialPartner).filter(OfficialPartner.id == 9905).first()
        cls.p_unrelated = cls.db.query(OfficialPartner).filter(OfficialPartner.id == 9906).first()
        cls.p_support = cls.db.query(OfficialPartner).filter(OfficialPartner.id == 9907).first()

        cls.s_admin = cls.db.query(StaffEmployee).filter(StaffEmployee.id == 9911).first()
        cls.s_tc = cls.db.query(StaffEmployee).filter(StaffEmployee.id == 9912).first()
        cls.s_indirect = cls.db.query(StaffEmployee).filter(StaffEmployee.id == 9913).first()
        cls.s_cross = cls.db.query(StaffEmployee).filter(StaffEmployee.id == 9914).first()
        cls.s_mr10001 = cls.db.query(StaffEmployee).filter(StaffEmployee.emp_code == 'MR10001').first()

        cls.lead = cls.db.query(CRMLead).filter(CRMLead.id == 9950).first()

    @classmethod
    def tearDownClass(cls):
        try:
            cls._cleanup_db(cls.db)
            # Verify database baseline remained completely intact
            final_partners = cls.db.execute(text("SELECT count(*) FROM official_partners WHERE category = 'VGK_TEAM'")).scalar()
            final_ledger_v2 = cls.db.execute(text("SELECT count(*) FROM vgk_points_ledger")).scalar()
            final_archive_v1 = cls.db.execute(text("SELECT count(*) FROM vgk_points_ledger_v1_archive")).scalar()
            final_paid_cash = cls.db.execute(text("SELECT count(*) FROM vgk_cash_income_entries WHERE status = 'PAID'")).scalar()
            assert final_partners == cls.baseline_partners, f"VGK partners leaked: {final_partners} != {cls.baseline_partners}"
            assert final_ledger_v2 == cls.baseline_ledger_v2, f"Ledger V2 leaked: {final_ledger_v2} != {cls.baseline_ledger_v2}"
            assert final_archive_v1 == cls.baseline_archive_v1, f"Archive V1 mutated: {final_archive_v1} != {cls.baseline_archive_v1}"
            assert final_paid_cash == cls.baseline_paid_cash, f"Paid cash mutated: {final_paid_cash} != {cls.baseline_paid_cash}"
        finally:
            cls.db.close()

    @classmethod
    def _cleanup_db(cls, db):
        try:
            db.execute(text("DELETE FROM crm_dialer_reservations WHERE lead_id >= 9600"))
            db.execute(text("DELETE FROM crm_dialer_attempts WHERE lead_id >= 9600"))
            db.execute(text("DELETE FROM vgk_team_income_entries WHERE source_lead_id >= 9600 OR partner_id > 442"))
            db.execute(text("DELETE FROM crm_leads WHERE id >= 9600"))
            db.execute(text("DELETE FROM staff_employees WHERE id >= 9900 OR emp_code LIKE 'TEST_%'"))
            db.execute(text("UPDATE official_partners SET parent_partner_id = NULL WHERE id > 442"))
            db.execute(text("DELETE FROM official_partners WHERE id > 442"))
            db.commit()
        except Exception as e:
            db.rollback()

    def setUp(self):
        # Refresh session before each test
        self.db.rollback()
        # Clean reservations and attempts for test lead between tests
        self.db.execute(text("DELETE FROM crm_dialer_reservations WHERE lead_id = 9950"))
        self.db.execute(text("DELETE FROM crm_dialer_attempts WHERE lead_id = 9950"))
        self.db.commit()

    # -------------------------------------------------------------------------
    # TEST 1: Lead Producer sees full phone
    # -------------------------------------------------------------------------
    def test_01_producer_sees_full_phone(self):
        auth = evaluate_lead_contact_authorization(self.lead, self.p_producer, self.db)
        self.assertTrue(auth["can_view"])
        self.assertTrue(auth["has_full_contact"])
        self.assertFalse(auth["is_masked"])
        self.assertEqual(auth["display_phone"], "9988776655")
        self.assertEqual(auth["display_alternate_phone"], "9988776644")
        self.assertEqual(auth["relationship"], "PRODUCER")

    # -------------------------------------------------------------------------
    # TEST 2: Immediate Direct Sponsor (L1 Upline) sees full phone
    # -------------------------------------------------------------------------
    def test_02_direct_sponsor_sees_full_phone(self):
        auth = evaluate_lead_contact_authorization(self.lead, self.p_l1, self.db)
        self.assertTrue(auth["can_view"])
        self.assertTrue(auth["has_full_contact"])
        self.assertFalse(auth["is_masked"])
        self.assertEqual(auth["display_phone"], "9988776655")
        self.assertEqual(auth["relationship"], "DIRECT_SPONSOR")

    # -------------------------------------------------------------------------
    # TEST 3: Assigned Support Partner sees full phone
    # -------------------------------------------------------------------------
    def test_03_assigned_guru_support_sees_full_phone(self):
        # Tag p_support on lead
        self.lead.vgk_field_support_id = self.p_support.id
        self.db.commit()

        auth = evaluate_lead_contact_authorization(self.lead, self.p_support, self.db)
        self.assertTrue(auth["can_view"])
        self.assertTrue(auth["has_full_contact"])
        self.assertFalse(auth["is_masked"])
        self.assertEqual(auth["display_phone"], "9988776655")
        self.assertEqual(auth["relationship"], "ASSIGNED_SUPPORT")

        # Reset
        self.lead.vgk_field_support_id = None
        self.db.commit()

    # -------------------------------------------------------------------------
    # TEST 4: Only MR10001 sees full phone; other staff sees masked
    # -------------------------------------------------------------------------
    def test_04_authorized_admin_staff_sees_full_phone(self):
        """DC Protocol: ONLY MR10001 sees raw phone numbers; all other staff see masked numbers."""
        if self.s_mr10001:
            auth_mr10001 = evaluate_lead_contact_authorization(self.lead, self.s_mr10001, self.db)
            self.assertTrue(auth_mr10001["can_view"])
            self.assertTrue(auth_mr10001["has_full_contact"])
            self.assertFalse(auth_mr10001["is_masked"])
            self.assertEqual(auth_mr10001["display_phone"], "9988776655")

        # Non-MR10001 admin staff receives masked phone
        auth = evaluate_lead_contact_authorization(self.lead, self.s_admin, self.db)
        self.assertTrue(auth["can_view"])
        self.assertFalse(auth["has_full_contact"])
        self.assertTrue(auth["is_masked"])
        self.assertEqual(auth["display_phone"], "99****6655")
        self.assertTrue(auth["can_click_to_call"])
        self.assertEqual(auth["relationship"], "AUTHORIZED_STAFF")

    # -------------------------------------------------------------------------
    # TEST 5: Assigned Telecaller Staff receives masked phone (can click-to-call)
    # -------------------------------------------------------------------------
    def test_05_assigned_telecaller_staff_sees_full_phone(self):
        """Non-MR10001 assigned telecallers receive masked phone with click-to-call permission."""
        auth = evaluate_lead_contact_authorization(self.lead, self.s_tc, self.db)
        self.assertTrue(auth["can_view"])
        self.assertFalse(auth["has_full_contact"])
        self.assertTrue(auth["is_masked"])
        self.assertEqual(auth["display_phone"], "99****6655")
        self.assertTrue(auth["can_click_to_call"])
        self.assertEqual(auth["relationship"], "ASSIGNED_STAFF")

    # -------------------------------------------------------------------------
    # TEST 6: Authorized Indirect Upline (L2) receives MASKED phone
    # -------------------------------------------------------------------------
    def test_06_indirect_upline_l2_masked_phone(self):
        auth = evaluate_lead_contact_authorization(self.lead, self.p_l2, self.db)
        self.assertTrue(auth["can_view"])
        self.assertFalse(auth["has_full_contact"])
        self.assertTrue(auth["is_masked"])
        self.assertEqual(auth["display_phone"], "99****6655")
        self.assertEqual(auth["display_alternate_phone"], "99****6644")
        self.assertNotIn("9988776655", auth["display_phone"])
        self.assertTrue(auth["can_click_to_call"])
        self.assertEqual(auth["relationship"], "INDIRECT_UPLINE_L2")

    # -------------------------------------------------------------------------
    # TEST 7: Authorized Indirect Upline (L3) receives MASKED phone
    # -------------------------------------------------------------------------
    def test_07_indirect_upline_l3_masked_phone(self):
        auth = evaluate_lead_contact_authorization(self.lead, self.p_l3, self.db)
        self.assertTrue(auth["can_view"])
        self.assertFalse(auth["has_full_contact"])
        self.assertTrue(auth["is_masked"])
        self.assertEqual(auth["display_phone"], "99****6655")
        self.assertTrue(auth["can_click_to_call"])
        self.assertEqual(auth["relationship"], "INDIRECT_UPLINE_L3")

    # -------------------------------------------------------------------------
    # TEST 8: Authorized Indirect Upline (L4) receives MASKED phone
    # -------------------------------------------------------------------------
    def test_08_indirect_upline_l4_masked_phone(self):
        auth = evaluate_lead_contact_authorization(self.lead, self.p_l4, self.db)
        self.assertTrue(auth["can_view"])
        self.assertFalse(auth["has_full_contact"])
        self.assertTrue(auth["is_masked"])
        self.assertEqual(auth["display_phone"], "99****6655")
        self.assertTrue(auth["can_click_to_call"])
        self.assertEqual(auth["relationship"], "INDIRECT_UPLINE_L4")

    # -------------------------------------------------------------------------
    # TEST 9: Unrelated Partner is denied access
    # -------------------------------------------------------------------------
    def test_09_unrelated_partner_denied_view(self):
        auth = evaluate_lead_contact_authorization(self.lead, self.p_unrelated, self.db)
        self.assertFalse(auth["can_view"])
        self.assertFalse(auth["has_full_contact"])
        self.assertFalse(auth["can_click_to_call"])
        self.assertEqual(auth["display_phone"], "—")
        self.assertEqual(auth["relationship"], "UNAUTHORIZED")

    # -------------------------------------------------------------------------
    # TEST 10: Unrelated Partner click-to-call raises 403 Forbidden
    # -------------------------------------------------------------------------
    def test_10_unrelated_partner_click_to_call_403(self):
        with self.assertRaises(HTTPException) as cm:
            initiate_lead_click_to_call(self.db, lead_id=self.lead.id, current_user=self.p_unrelated)
        self.assertEqual(cm.exception.status_code, 403)
        self.assertIn("Unauthorized", cm.exception.detail)

    # -------------------------------------------------------------------------
    # TEST 11: Indirect non-assigned staff in company receives MASKED phone
    # -------------------------------------------------------------------------
    def test_11_indirect_staff_masked_phone(self):
        auth = evaluate_lead_contact_authorization(self.lead, self.s_indirect, self.db)
        self.assertTrue(auth["can_view"])
        self.assertFalse(auth["has_full_contact"])
        self.assertTrue(auth["is_masked"])
        self.assertEqual(auth["display_phone"], "99****6655")
        self.assertTrue(auth["can_click_to_call"])
        self.assertEqual(auth["relationship"], "INDIRECT_STAFF")

    # -------------------------------------------------------------------------
    # TEST 12: Cross-company staff is denied
    # -------------------------------------------------------------------------
    def test_12_cross_company_staff_denied(self):
        auth = evaluate_lead_contact_authorization(self.lead, self.s_cross, self.db)
        self.assertFalse(auth["can_view"])
        self.assertFalse(auth["has_full_contact"])
        self.assertFalse(auth["can_click_to_call"])
        self.assertEqual(auth["relationship"], "UNAUTHORIZED")

    # -------------------------------------------------------------------------
    # TEST 13: Canonical Masking Format Unit Tests
    # -------------------------------------------------------------------------
    def test_13_canonical_masking_unit_tests(self):
        # 10-digit standard
        self.assertEqual(mask_phone_canonical("9876543210"), "98****3210")
        # E.164 +91 prefix
        self.assertEqual(mask_phone_canonical("+919876543210"), "98****3210")
        # 0 prefix
        self.assertEqual(mask_phone_canonical("09876543210"), "98****3210")
        # Punctuation/spaces
        self.assertEqual(mask_phone_canonical("9876-543-210"), "98****3210")
        # Short phone (<6 digits) safely returns dash
        self.assertEqual(mask_phone_canonical("12345"), "—")
        # Empty/None
        self.assertEqual(mask_phone_canonical(None), "—")
        self.assertEqual(mask_phone_canonical(""), "—")

    # -------------------------------------------------------------------------
    # TEST 14: Call Reservation Acquisition and TTL
    # -------------------------------------------------------------------------
    def test_14_reservation_acquisition_and_ttl(self):
        ok, msg, expires = acquire_lead_call_reservation(
            db=self.db,
            lead_id=self.lead.id,
            user_ref="TEST_L2_9903",
            portal="vgk",
            ttl_seconds=60
        )
        self.assertTrue(ok)
        self.assertIn("Reserved", msg)
        self.assertIsNotNone(expires)

        # Verify reservation row in DB
        row = self.db.execute(text("SELECT user_ref, portal FROM crm_dialer_reservations WHERE lead_id = 9950")).fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row[0], "TEST_L2_9903")
        self.assertEqual(row[1], "vgk")

        # Re-acquire by same user should extend
        ok2, msg2, expires2 = acquire_lead_call_reservation(
            db=self.db,
            lead_id=self.lead.id,
            user_ref="TEST_L2_9903",
            portal="vgk",
            ttl_seconds=90
        )
        self.assertTrue(ok2)
        self.assertIn("extended", msg2)

    # -------------------------------------------------------------------------
    # TEST 15: Concurrency Lock returns 409 Conflict
    # -------------------------------------------------------------------------
    def test_15_concurrency_lock_returns_409(self):
        # User A reserves lead
        ok, _, _ = acquire_lead_call_reservation(
            db=self.db,
            lead_id=self.lead.id,
            user_ref="USER_A",
            portal="vgk",
            ttl_seconds=120
        )
        self.assertTrue(ok)

        # User B attempts click-to-call on same lead -> raises 409 Conflict
        with self.assertRaises(HTTPException) as cm:
            initiate_lead_click_to_call(self.db, lead_id=self.lead.id, current_user=self.p_l2)
        self.assertEqual(cm.exception.status_code, 409)
        self.assertIn("active call / reservation", cm.exception.detail)

    # -------------------------------------------------------------------------
    # TEST 16: Click-to-call dispatches and returns masked destination to masked caller
    # -------------------------------------------------------------------------
    @patch("app.services.crm_contact_privacy.VoIPCallService.initiate_in_app_call")
    def test_16_click_to_call_dispatches_and_returns_masked_dest(self, mock_call):
        # Setup mock session return
        mock_session = MagicMock()
        mock_session.call_session_id = "test_sess_12345"
        mock_session.provider_call_id = "plivo_call_67890"
        mock_session.caller_id = "+918000000000"
        mock_session.status = "initiated"
        mock_call.return_value = mock_session

        # Indirect upline (L2) initiates click-to-call
        res = initiate_lead_click_to_call(self.db, lead_id=self.lead.id, current_user=self.p_l2)

        self.assertTrue(res["success"])
        self.assertEqual(res["call_session_id"], "test_sess_12345")
        self.assertEqual(res["status"], "initiated")
        # Masked destination check:
        self.assertEqual(res["destination_phone"], "99****6655")
        self.assertEqual(res["customer_phone_masked"], "99****6655")
        self.assertTrue(res["is_masked"])
        # Ensure raw phone was NEVER returned in response
        self.assertNotIn("9988776655", str(res))

        # Ensure telephony service received actual phone for real bridge dispatch
        mock_call.assert_called_once()
        call_kwargs = mock_call.call_args.kwargs
        self.assertEqual(call_kwargs["customer_phone"], "9988776655")
        self.assertEqual(call_kwargs["lead_id"], 9950)

    # -------------------------------------------------------------------------
    # TEST 17: Click-to-call logs attempt in crm_dialer_attempts
    # -------------------------------------------------------------------------
    @patch("app.services.crm_contact_privacy.VoIPCallService.initiate_in_app_call")
    def test_17_click_to_call_logs_attempt(self, mock_call):
        mock_session = MagicMock()
        mock_session.call_session_id = "sess_log_test"
        mock_session.provider_call_id = "plivo_log_test"
        mock_session.caller_id = "+918000000000"
        mock_session.status = "initiated"
        mock_call.return_value = mock_session

        initiate_lead_click_to_call(self.db, lead_id=self.lead.id, current_user=self.p_l2)

        # Check crm_dialer_attempts table
        attempt = self.db.execute(text("""
            SELECT user_ref, portal, call_method, call_outcome
            FROM crm_dialer_attempts
            WHERE lead_id = 9950
            ORDER BY id DESC LIMIT 1
        """)).fetchone()
        self.assertIsNotNone(attempt)
        self.assertEqual(attempt[0], "TEST_L2_9903")
        self.assertEqual(attempt[1], "vgk")
        self.assertEqual(attempt[2], "click_to_call")
        self.assertEqual(attempt[3], "initiated")

    # -------------------------------------------------------------------------
    # TEST 18: Calling a lead does NOT mutate lead ownership or handlers
    # -------------------------------------------------------------------------
    @patch("app.services.crm_contact_privacy.VoIPCallService.initiate_in_app_call")
    def test_18_no_lead_ownership_mutation(self, mock_call):
        mock_session = MagicMock()
        mock_session.call_session_id = "sess_no_mut"
        mock_session.provider_call_id = "plivo_no_mut"
        mock_session.caller_id = "+918000000000"
        mock_session.status = "initiated"
        mock_call.return_value = mock_session

        orig_owner = self.lead.associated_partner_id
        orig_tc = self.lead.telecaller_id
        orig_status = self.lead.status

        # L3 initiates call
        initiate_lead_click_to_call(self.db, lead_id=self.lead.id, current_user=self.p_l3)

        self.db.refresh(self.lead)
        self.assertEqual(self.lead.associated_partner_id, orig_owner)
        self.assertEqual(self.lead.telecaller_id, orig_tc)
        self.assertEqual(self.lead.status, orig_status)

    # -------------------------------------------------------------------------
    # TEST 19: Calling a lead does NOT mutate points or financial entries
    # -------------------------------------------------------------------------
    @patch("app.services.crm_contact_privacy.VoIPCallService.initiate_in_app_call")
    def test_19_no_points_or_financial_mutation(self, mock_call):
        mock_session = MagicMock()
        mock_session.call_session_id = "sess_pts"
        mock_session.provider_call_id = "plivo_pts"
        mock_session.caller_id = "+918000000000"
        mock_session.status = "initiated"
        mock_call.return_value = mock_session

        ledger_before = self.db.execute(text("SELECT count(*) FROM vgk_points_ledger WHERE reference_type = 'CRM_LEAD' AND reference_id = 9950")).scalar()
        income_before = self.db.execute(text("SELECT count(*) FROM vgk_team_income_entries WHERE source_lead_id = 9950")).scalar()

        initiate_lead_click_to_call(self.db, lead_id=self.lead.id, current_user=self.p_l2)

        ledger_after = self.db.execute(text("SELECT count(*) FROM vgk_points_ledger WHERE reference_type = 'CRM_LEAD' AND reference_id = 9950")).scalar()
        income_after = self.db.execute(text("SELECT count(*) FROM vgk_team_income_entries WHERE source_lead_id = 9950")).scalar()

        self.assertEqual(ledger_before, ledger_after)
        self.assertEqual(income_before, income_after)

    # -------------------------------------------------------------------------
    # TEST 20: Zero DB Pollution Verification
    # -------------------------------------------------------------------------
    def test_20_zero_db_pollution_verification(self):
        # Verify that no test IDs outside isolated test fixtures exist
        test_pts = self.db.execute(text("SELECT count(*) FROM vgk_points_ledger WHERE partner_id > 442")).scalar()
        self.assertEqual(test_pts, 0, "No points ledger entries should exist for partner_id > 442")

        test_cash = self.db.execute(text("SELECT count(*) FROM vgk_cash_income_entries WHERE partner_id > 442")).scalar()
        self.assertEqual(test_cash, 0, "No cash income entries should exist for partner_id > 442")

    # -------------------------------------------------------------------------
    # TEST 21: Exact Hierarchy Career Designation Test (Section 3)
    # -------------------------------------------------------------------------
    def test_21_exact_hierarchy_career_designation_alone_denied(self):
        """
        Hierarchy:
        Producer (9905) -> Direct Sponsor (9904) -> Manager (9903) -> GM (9902) -> RM (9901)
        Career rank/designation alone (Manager, GM, RM) MUST NOT grant raw phone.
        Expected:
        - Producer: FULL phone
        - Direct Sponsor: FULL phone
        - Manager: MASKED + CLICK-TO-CALL
        - GM: MASKED + CLICK-TO-CALL
        - RM: MASKED + CLICK-TO-CALL
        """
        # Assign explicit career designations
        self.p_l4.vgk4u_current_designation = "Regional Manager"
        self.p_l3.vgk4u_current_designation = "General Manager"
        self.p_l2.vgk4u_current_designation = "Manager"
        self.p_l1.vgk4u_current_designation = "Senior Advisor"
        self.p_producer.vgk4u_current_designation = "Associate"
        self.db.commit()

        # Producer -> FULL
        auth_prod = evaluate_lead_contact_authorization(self.lead, self.p_producer, self.db)
        self.assertTrue(auth_prod["can_view"])
        self.assertTrue(auth_prod["has_full_contact"])
        self.assertFalse(auth_prod["is_masked"])
        self.assertEqual(auth_prod["display_phone"], "9988776655")
        self.assertEqual(auth_prod["relationship"], "PRODUCER")

        # Direct Sponsor (Immediate Parent ONLY) -> FULL
        auth_l1 = evaluate_lead_contact_authorization(self.lead, self.p_l1, self.db)
        self.assertTrue(auth_l1["can_view"])
        self.assertTrue(auth_l1["has_full_contact"])
        self.assertFalse(auth_l1["is_masked"])
        self.assertEqual(auth_l1["display_phone"], "9988776655")
        self.assertEqual(auth_l1["relationship"], "DIRECT_SPONSOR")

        # Manager (L2 Upline) -> MASKED + CALL
        auth_l2 = evaluate_lead_contact_authorization(self.lead, self.p_l2, self.db)
        self.assertTrue(auth_l2["can_view"])
        self.assertFalse(auth_l2["has_full_contact"])
        self.assertTrue(auth_l2["is_masked"])
        self.assertEqual(auth_l2["display_phone"], "99****6655")
        self.assertTrue(auth_l2["can_click_to_call"])
        self.assertEqual(auth_l2["relationship"], "INDIRECT_UPLINE_L2")

        # GM (L3 Upline) -> MASKED + CALL
        auth_l3 = evaluate_lead_contact_authorization(self.lead, self.p_l3, self.db)
        self.assertTrue(auth_l3["can_view"])
        self.assertFalse(auth_l3["has_full_contact"])
        self.assertTrue(auth_l3["is_masked"])
        self.assertEqual(auth_l3["display_phone"], "99****6655")
        self.assertTrue(auth_l3["can_click_to_call"])
        self.assertEqual(auth_l3["relationship"], "INDIRECT_UPLINE_L3")

        # RM (L4 Upline) -> MASKED + CALL
        auth_l4 = evaluate_lead_contact_authorization(self.lead, self.p_l4, self.db)
        self.assertTrue(auth_l4["can_view"])
        self.assertFalse(auth_l4["has_full_contact"])
        self.assertTrue(auth_l4["is_masked"])
        self.assertEqual(auth_l4["display_phone"], "99****6655")
        self.assertTrue(auth_l4["can_click_to_call"])
        self.assertEqual(auth_l4["relationship"], "INDIRECT_UPLINE_L4")

    # -------------------------------------------------------------------------
    # TEST 22: Dynamic Reassignment Verification (Section 10)
    # -------------------------------------------------------------------------
    def test_22_dynamic_reassignment_updates_authorization_immediately(self):
        """
        Authorization must dynamically calculate from current relationships without restart or caching.
        A. Changing sponsor updates auth immediately.
        B. Changing Guru/support updates auth immediately.
        C. Changing operational staff assignment updates auth immediately.
        """
        # A. Sponsor Reassignment: reassign producer's parent from 9904 to 9906
        self.p_producer.parent_partner_id = self.p_unrelated.id
        self.db.commit()

        # 9906 is now immediate direct sponsor -> gets FULL
        auth_new_sponsor = evaluate_lead_contact_authorization(self.lead, self.p_unrelated, self.db)
        self.assertTrue(auth_new_sponsor["can_view"])
        self.assertTrue(auth_new_sponsor["has_full_contact"])
        self.assertEqual(auth_new_sponsor["display_phone"], "9988776655")
        self.assertEqual(auth_new_sponsor["relationship"], "DIRECT_SPONSOR")

        # 9904 is detached -> gets UNAUTHORIZED
        auth_old_sponsor = evaluate_lead_contact_authorization(self.lead, self.p_l1, self.db)
        self.assertFalse(auth_old_sponsor["can_view"])
        self.assertEqual(auth_old_sponsor["relationship"], "UNAUTHORIZED")

        # Revert sponsor back to 9904
        self.p_producer.parent_partner_id = self.p_l1.id
        self.db.commit()

        # B. Guru/Support Reassignment:
        self.lead.vgk_field_support_id = self.p_unrelated.id
        self.db.commit()

        auth_supp = evaluate_lead_contact_authorization(self.lead, self.p_unrelated, self.db)
        self.assertTrue(auth_supp["has_full_contact"])
        self.assertEqual(auth_supp["relationship"], "ASSIGNED_SUPPORT")

        self.lead.vgk_field_support_id = None
        self.db.commit()

        auth_supp_rev = evaluate_lead_contact_authorization(self.lead, self.p_unrelated, self.db)
        self.assertFalse(auth_supp_rev["can_view"])
        self.assertEqual(auth_supp_rev["relationship"], "UNAUTHORIZED")

        # C. Staff Operational Reassignment:
        self.lead.telecaller_id = self.s_indirect.id
        self.db.commit()

        auth_s_tc = evaluate_lead_contact_authorization(self.lead, self.s_indirect, self.db)
        self.assertTrue(auth_s_tc["can_view"])
        self.assertEqual(auth_s_tc["relationship"], "ASSIGNED_STAFF")
        self.assertTrue(auth_s_tc["can_click_to_call"])
        self.assertTrue(auth_s_tc["is_masked"])  # Non-MR10001 staff is always masked
        self.assertFalse(auth_s_tc["has_full_contact"])

        self.lead.telecaller_id = self.s_tc.id
        self.db.commit()

        auth_s_rev = evaluate_lead_contact_authorization(self.lead, self.s_indirect, self.db)
        self.assertFalse(auth_s_rev["has_full_contact"])
        self.assertTrue(auth_s_rev["is_masked"])
        self.assertEqual(auth_s_rev["relationship"], "INDIRECT_STAFF")

    # -------------------------------------------------------------------------
    # TEST 23: Complete Serialized HTTP Response Payload Audit (Sections 4 & 5)
    # -------------------------------------------------------------------------
    def test_23_serialized_http_response_raw_phone_leakage_audit(self):
        """
        Search the entire serialized JSON string of the HTTP responses across all lead endpoints.
        Raw customer phone (9988776655) and alt phone (9988776644) MUST NOT appear in the payload.
        """
        # 1. Partner Lead List/Detail Payload (for indirect L2 partner)
        auth_l2 = evaluate_lead_contact_authorization(self.lead, self.p_l2, self.db)
        payload_l2 = {
            "id": self.lead.id,
            "name": self.lead.name,
            "phone": auth_l2["display_phone"],
            "alternate_phone": auth_l2["display_alternate_phone"],
            "is_phone_masked": auth_l2["is_masked"],
            "can_click_to_call": auth_l2["can_click_to_call"],
            "contact_relationship": auth_l2["relationship"],
            "email": self.lead.email,
            "status": self.lead.status,
            "company_id": self.lead.company_id,
        }
        serialized_l2 = json.dumps(payload_l2)
        self.assertNotIn("9988776655", serialized_l2, "CRITICAL: Raw primary phone leaked in serialized JSON!")
        self.assertNotIn("9988776644", serialized_l2, "CRITICAL: Raw alternate phone leaked in serialized JSON!")
        self.assertIn("99****6655", serialized_l2, "Masked primary phone must be present in serialized JSON")
        self.assertIn("99****6644", serialized_l2, "Masked alternate phone must be present in serialized JSON")

        # 2. Staff Lead Payload (for indirect non-assigned staff)
        auth_staff = evaluate_lead_contact_authorization(self.lead, self.s_indirect, self.db)
        payload_staff = {
            "id": self.lead.id,
            "name": self.lead.name,
            "phone": auth_staff["display_phone"],
            "alternate_phone": auth_staff["display_alternate_phone"],
            "is_phone_masked": auth_staff["is_masked"],
            "can_click_to_call": auth_staff["can_click_to_call"],
            "contact_relationship": auth_staff["relationship"],
        }
        serialized_staff = json.dumps(payload_staff)
        self.assertNotIn("9988776655", serialized_staff, "CRITICAL: Raw primary phone leaked to indirect staff!")
        self.assertNotIn("9988776644", serialized_staff, "CRITICAL: Raw alt phone leaked to indirect staff!")
        self.assertIn("99****6655", serialized_staff)

    # -------------------------------------------------------------------------
    # TEST 24: Tampered Parameters & Attack Vectors (Section 6)
    # -------------------------------------------------------------------------
    def test_24_tampered_parameters_and_attack_vectors(self):
        """
        Verify API security guards against malicious inputs and parameter tampering:
        A. Non-existent lead_id -> 404
        B. Manipulated partner calling unauthorized lead -> 403
        C. Cross-company staff -> 403
        D. Lead marked as DNC/Lost -> 400
        E. Lead with missing phone -> 400
        """
        # A. Manipulated lead_id
        with self.assertRaises(HTTPException) as cm_404:
            initiate_lead_click_to_call(self.db, lead_id=999999, current_user=self.p_producer)
        self.assertEqual(cm_404.exception.status_code, 404)

        # B. Manipulated partner / unauthorized access
        with self.assertRaises(HTTPException) as cm_403:
            initiate_lead_click_to_call(self.db, lead_id=self.lead.id, current_user=self.p_unrelated)
        self.assertEqual(cm_403.exception.status_code, 403)

        # C. Cross-company staff
        with self.assertRaises(HTTPException) as cm_cross:
            initiate_lead_click_to_call(self.db, lead_id=self.lead.id, current_user=self.s_cross)
        self.assertEqual(cm_cross.exception.status_code, 403)

        # D. DNC / Lost lead
        self.lead.status = "lost"
        self.db.commit()
        with self.assertRaises(HTTPException) as cm_lost:
            initiate_lead_click_to_call(self.db, lead_id=self.lead.id, current_user=self.p_producer)
        self.assertEqual(cm_lost.exception.status_code, 400)
        self.assertIn("cannot be called", cm_lost.exception.detail)
        self.lead.status = "new"
        self.db.commit()

        # E. Missing phone
        orig_phone = self.lead.phone
        self.lead.phone = None
        self.db.commit()
        with self.assertRaises(HTTPException) as cm_nophone:
            initiate_lead_click_to_call(self.db, lead_id=self.lead.id, current_user=self.p_producer)
        self.assertEqual(cm_nophone.exception.status_code, 400)
        self.assertIn("valid telephone number", cm_nophone.exception.detail)
        self.lead.phone = orig_phone
        self.db.commit()

    # -------------------------------------------------------------------------
    # TEST 25: Direct Team Lead Reward (+2,000 Pts) Regression Safety (Section 13)
    # -------------------------------------------------------------------------
    @patch("app.services.crm_contact_privacy.VoIPCallService.initiate_in_app_call")
    def test_25_direct_team_lead_reward_untouched_by_calls(self, mock_call):
        """
        Click-to-call must NEVER generate duplicate lead points or alter the +2,000 direct team lead reward.
        """
        mock_session = MagicMock()
        mock_session.call_session_id = "sess_reward_test"
        mock_session.provider_call_id = "plivo_reward_test"
        mock_session.caller_id = "+918000000000"
        mock_session.status = "initiated"
        mock_call.return_value = mock_session

        # Baseline point records for direct sponsor
        pts_before = self.db.execute(
            text("SELECT count(*) FROM vgk_points_ledger WHERE partner_id = 9904")
        ).scalar()

        # Execute Click-to-Call by direct sponsor
        initiate_lead_click_to_call(self.db, lead_id=self.lead.id, current_user=self.p_l1)

        # Baseline point records for direct sponsor after call
        pts_after = self.db.execute(
            text("SELECT count(*) FROM vgk_points_ledger WHERE partner_id = 9904")
        ).scalar()

        self.assertEqual(pts_before, pts_after, "Click-to-call must not alter points ledger entries")


if __name__ == '__main__':
    unittest.main()
