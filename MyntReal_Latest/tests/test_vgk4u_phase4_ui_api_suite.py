"""
VGK4U Phase 4 UI & API Cross-Surface Integration Test Suite
Created: 2026-09-12
Covers:
- Decoupled Career vs Personal Production in Dashboard Summary API
- Dynamic Ladder metadata (Career Designation & Personal Production configs)
- 6-Stream Earnings breakdown in Member Cash Income API
- Stream labels and categorization for individual entries
- Staff Configs API security wall & payload verification
- Corporate Retained Margin API security wall, segregation & payload verification
- Partner Privacy Protection (Corporate Margins strictly excluded from Member surfaces)
- Phase 3E Financial Immutability Verification (SHA256 baselines)
"""

import unittest
from decimal import Decimal
import hashlib
import sys
import os

# Dynamic path resolution
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend')))

from fastapi.testclient import TestClient
from sqlalchemy import text
from app.main import app
from app.core.database import SessionLocal
from app.models.staff_accounts import OfficialPartner
from app.models.staff import StaffEmployee
from app.api.v1.endpoints.vgk_auth import get_current_vgk_member
from app.api.v1.endpoints.staff_auth import get_current_staff_user


class TestVGK4UPhase4UIAPISuite(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db = SessionLocal()
        cls.client = TestClient(app)
        cls.baseline_cash_hash = '4ab74b1bf3583ad22c291c974d3bb99ee8a4e6ff0860cb84d6713199e11aae35'
        cls.baseline_adv_hash = '5b1322cc5587bd5994e2b4f1947afab94d17019b05bcee753805a7163db37f8b'

        # Fetch representative live partners for authenticated mocking
        cls.partner_134 = cls.db.query(OfficialPartner).filter(OfficialPartner.id == 134).first()
        cls.partner_160 = cls.db.query(OfficialPartner).filter(OfficialPartner.id == 160).first()
        cls.partner_31  = cls.db.query(OfficialPartner).filter(OfficialPartner.id == 31).first()

        # Fetch or mock staff employee
        cls.staff_emp = cls.db.query(StaffEmployee).first()
        if not cls.staff_emp:
            cls.staff_emp = StaffEmployee(id=1, emp_code="STAFF001", role="ADMIN", is_active=True)

    @classmethod
    def tearDownClass(cls):
        app.dependency_overrides.clear()
        cls.db.close()

    def tearDown(self):
        app.dependency_overrides.clear()

    # ──────────────────────────────────────────────────────────────────────────
    # TEST 1: Dashboard Summary Decoupled Career & Production Status
    # ──────────────────────────────────────────────────────────────────────────
    def test_01_dashboard_summary_career_decoupling(self):
        """Verify dashboard summary returns decoupled career designation and personal production."""
        self.assertIsNotNone(self.partner_134, "Partner 134 must exist in test database")

        # Test Partner 134 (Member with active legs, 0 files)
        app.dependency_overrides[get_current_vgk_member] = lambda: self.partner_134
        response = self.client.get("/api/v1/vgk/dashboard/summary")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data.get("success"))

        cs = data.get("vgk4u_career_status")
        self.assertIsNotNone(cs, "vgk4u_career_status must be present in dashboard summary")
        self.assertEqual(cs.get("career_designation"), "Member")
        self.assertEqual(cs.get("career_designation_label"), "Member")
        self.assertEqual(cs.get("personal_prod_tier"), "None")
        self.assertEqual(cs.get("own_qualifying_files"), 0)
        self.assertGreaterEqual(cs.get("active_legs"), 1)

        # Confirm dynamic career ladder metadata
        career_ladder = data.get("career_ladder")
        self.assertIsNotNone(career_ladder)
        self.assertGreaterEqual(len(career_ladder), 5)
        codes = [c["code"] for c in career_ladder]
        self.assertIn("MEMBER", codes)
        self.assertIn("CHANNEL_PARTNER", codes)
        self.assertIn("MANAGER", codes)
        self.assertIn("GENERAL_MANAGER", codes)
        self.assertIn("REGIONAL_MANAGER", codes)

        # Confirm dynamic personal production ladder metadata
        prod_ladder = data.get("personal_prod_ladder")
        self.assertIsNotNone(prod_ladder)
        self.assertGreaterEqual(len(prod_ladder), 3)

        # Test Partner 160 (Channel Partner with 1 personal file, 0 legs)
        app.dependency_overrides[get_current_vgk_member] = lambda: self.partner_160
        res_160 = self.client.get("/api/v1/vgk/dashboard/summary")
        self.assertEqual(res_160.status_code, 200)
        cs_160 = res_160.json().get("vgk4u_career_status")
        self.assertEqual(cs_160.get("career_designation"), "Channel Partner")
        self.assertEqual(cs_160.get("personal_prod_tier"), "Base")
        self.assertEqual(cs_160.get("own_qualifying_files"), 1)
        self.assertEqual(cs_160.get("effective_personal_rate"), 6.0)

    # ──────────────────────────────────────────────────────────────────────────
    # TEST 2: 6 Distinct Earning Streams in Member Cash Income API
    # ──────────────────────────────────────────────────────────────────────────
    def test_02_member_cash_income_six_earning_streams(self):
        """Verify member cash income summary provides all 6 distinct earning streams."""
        app.dependency_overrides[get_current_vgk_member] = lambda: self.partner_134

        response = self.client.get("/api/v1/vgk/member/cash-income?per_page=20")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data.get("success"))

        summary = data.get("summary", {})
        expected_streams = [
            "personal_producer_total",
            "team_differential_total",
            "support_total",
            "showroom_total",
            "stage_advances_total",
            "stage_bonuses_total",
        ]
        for stream in expected_streams:
            self.assertIn(stream, summary, f"Stream {stream} must be present in cash income summary")
            self.assertIsInstance(summary[stream], (int, float))

        # Check entry level stream labels
        entries = data.get("data", [])
        for e in entries:
            self.assertIn("earning_stream", e)
            self.assertIn("stream_label", e)
            self.assertIsInstance(e["stream_label"], str)

    # ──────────────────────────────────────────────────────────────────────────
    # TEST 3: Staff Configs API Security & Response Schema
    # ──────────────────────────────────────────────────────────────────────────
    def test_03_staff_configs_endpoint_security_and_payload(self):
        """Verify staff configs API rejects unauthenticated requests and returns authoritative configs for staff."""
        # 1. Unauthenticated request must fail with 401
        res_unauth = self.client.get("/api/v1/vgk/staff/vgk4u/configs")
        self.assertIn(res_unauth.status_code, [401, 403])

        # 2. Staff authenticated request succeeds
        app.dependency_overrides[get_current_staff_user] = lambda: self.staff_emp

        res_staff = self.client.get("/api/v1/vgk/staff/vgk4u/configs")
        self.assertEqual(res_staff.status_code, 200)
        data = res_staff.json()
        self.assertTrue(data.get("success"))

        # Check career designations
        careers = data.get("career_designations", [])
        self.assertGreaterEqual(len(careers), 5)
        desig_names = [c["designation_name"] for c in careers]
        self.assertIn("Member", desig_names)
        self.assertIn("Channel Partner", desig_names)
        self.assertIn("Manager", desig_names)
        self.assertIn("General Manager", desig_names)
        self.assertIn("Regional Manager", desig_names)

        # Check personal production tiers
        prods = data.get("personal_prod_tiers", [])
        self.assertGreaterEqual(len(prods), 3)

        # Check category configs
        cats = data.get("category_configs", [])
        self.assertGreaterEqual(len(cats), 1)
        solar_cfg = next((c for c in cats if c["category_slug"] == "solar"), None)
        self.assertIsNotNone(solar_cfg)
        self.assertEqual(solar_cfg["max_network_pool_pct"], 9.0)
        self.assertEqual(solar_cfg["producer_base_pct"], 6.0)
        self.assertEqual(solar_cfg["sponsor_override_pct"], 1.0)
        self.assertEqual(solar_cfg["manager_diff_pct"], 1.5)
        self.assertEqual(solar_cfg["gm_diff_pct"], 1.0)
        self.assertEqual(solar_cfg["rm_diff_pct"], 0.5)

    # ──────────────────────────────────────────────────────────────────────────
    # TEST 4: Corporate Retained Margin API Security & Ledger Segregation
    # ──────────────────────────────────────────────────────────────────────────
    def test_04_corporate_margin_ledger_security_and_segregation(self):
        """Verify corporate retained margin ledger is strictly staff-only and segregated."""
        # 1. Unauthenticated request must fail
        res_unauth = self.client.get("/api/v1/vgk/staff/vgk4u/corporate-margins")
        self.assertIn(res_unauth.status_code, [401, 403])

        # 2. Staff authenticated request succeeds
        app.dependency_overrides[get_current_staff_user] = lambda: self.staff_emp

        res_staff = self.client.get("/api/v1/vgk/staff/vgk4u/corporate-margins")
        self.assertEqual(res_staff.status_code, 200)
        data = res_staff.json()
        self.assertTrue(data.get("success"))
        self.assertIn("total_count", data)
        self.assertIn("total_retained_amount", data)
        self.assertIn("records", data)

    # ──────────────────────────────────────────────────────────────────────────
    # TEST 5: Partner Privacy Wall (Zero Exposure of Corporate Margins)
    # ──────────────────────────────────────────────────────────────────────────
    def test_05_partner_privacy_wall_corporate_margin_exclusion(self):
        """Verify that member endpoints never expose corporate margin ledger entries or company balances."""
        app.dependency_overrides[get_current_vgk_member] = lambda: self.partner_134

        # Member wallet
        res_wallet = self.client.get("/api/v1/vgk/member/wallet")
        self.assertEqual(res_wallet.status_code, 200)
        w_data = res_wallet.json()
        self.assertNotIn("corporate_margin", str(w_data))
        self.assertNotIn("retained_margin", str(w_data))

        # Member cash income
        res_income = self.client.get("/api/v1/vgk/member/cash-income")
        self.assertEqual(res_income.status_code, 200)
        i_data = res_income.json()
        self.assertNotIn("corporate_margin", str(i_data))
        self.assertNotIn("retained_margin", str(i_data))

    # ──────────────────────────────────────────────────────────────────────────
    # TEST 6: Financial Immutability Baseline Check
    # ──────────────────────────────────────────────────────────────────────────
    def test_06_financial_immutability_hashes(self):
        """Verify SHA256 hashes of financial tables have not drifted."""
        # vgk_cash_income_entries
        cash_rows = self.db.execute(text("""
            SELECT id, partner_id, source_lead_id, kind, level, commission_amount, net_payout, status, created_at 
            FROM vgk_cash_income_entries ORDER BY id
        """)).fetchall()
        cash_str = "".join(f"{r[0]}:{r[1]}:{r[2]}:{r[3]}:{r[4]}:{r[5]}:{r[6]}:{r[7]}:{r[8]}" for r in cash_rows)
        cash_hash = hashlib.sha256(cash_str.encode()).hexdigest()
        self.assertEqual(cash_hash, self.baseline_cash_hash, "vgk_cash_income_entries SHA256 hash modified!")

        # vgk_solar_cibil_advances
        adv_rows = self.db.execute(text("""
            SELECT id, partner_id, lead_id, kind, level, advance_amount, status, created_at 
            FROM vgk_solar_cibil_advances ORDER BY id
        """)).fetchall()
        adv_str = "".join(f"{r[0]}:{r[1]}:{r[2]}:{r[3]}:{r[4]}:{r[5]}:{r[6]}:{r[7]}" for r in adv_rows)
        adv_hash = hashlib.sha256(adv_str.encode()).hexdigest()
        self.assertEqual(adv_hash, self.baseline_adv_hash, "vgk_solar_cibil_advances SHA256 hash modified!")


if __name__ == '__main__':
    unittest.main()
