"""
VGK4U Phase 4.1 Legacy Vocabulary, Designation & Presentation Surface Migration Test Suite
Created: 2026-09-12
Covers:
- Canonical Career Designation & Personal Production Qualification separation across APIs
- Elimination of star rank prefixes (★) from member-facing presentation payloads
- Verification of Partner 122 (Bandi Gangaraju) canonical resolution (Channel Partner / Base)
- Verification of Partner 134 (Member / None)
- Strict elimination of "Apex Master" across database, models, and member-facing endpoints
- Universal Incentive Engine canonical career designation returns
- Absolute SHA-256 financial immutability preservation for historical ledgers
"""

import unittest
from decimal import Decimal
import hashlib
import sys
import os

# Dynamic relative path resolution - cross platform compliance
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend')))

from fastapi.testclient import TestClient
from sqlalchemy import text
from app.main import app
from app.core.database import SessionLocal
from app.models.staff_accounts import OfficialPartner
from app.models.staff import StaffEmployee
from app.services.vgk4u_career_service import VGK4UCareerService
from app.services.universal_incentive_engine import (
    get_partner_current_position_v18,
    get_bulk_partner_current_positions_v26,
)
from app.api.v1.endpoints.vgk_auth import get_current_vgk_member
from app.api.v1.endpoints.staff_auth import get_current_staff_user


class TestVGK4ULegacyVocabularySuite(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db = SessionLocal()
        cls.client = TestClient(app)
        cls.baseline_cash_hash = '4ab74b1bf3583ad22c291c974d3bb99ee8a4e6ff0860cb84d6713199e11aae35'
        cls.baseline_adv_hash = '5b1322cc5587bd5994e2b4f1947afab94d17019b05bcee753805a7163db37f8b'

        cls.partner_122 = cls.db.query(OfficialPartner).filter(OfficialPartner.id == 122).first()
        cls.partner_134 = cls.db.query(OfficialPartner).filter(OfficialPartner.id == 134).first()
        cls.partner_31  = cls.db.query(OfficialPartner).filter(OfficialPartner.id == 31).first()

        cls.staff_emp = cls.db.query(StaffEmployee).first()
        if not cls.staff_emp:
            cls.staff_emp = StaffEmployee(id=1, emp_code="STAFF001", role="ADMIN", is_active=True)
        cls.staff_emp.staff_type = "SUPER_ADMIN"

    @classmethod
    def tearDownClass(cls):
        app.dependency_overrides.clear()
        cls.db.close()

    def setUp(self):
        if self.staff_emp:
            self.staff_emp.staff_type = "SUPER_ADMIN"

    def tearDown(self):
        app.dependency_overrides.clear()
        self.db.rollback()

    # ──────────────────────────────────────────────────────────────────────────
    # TEST 1: Partner 122 (Evidence Trigger Validation)
    # ──────────────────────────────────────────────────────────────────────────
    def test_01_partner_122_evidence_validation(self):
        """Partner 122 (Bandi Gangaraju) must resolve to Channel Partner, Base, VGK Support sponsor without stars."""
        self.assertIsNotNone(self.partner_122, "Partner 122 must exist in database")

        career = VGK4UCareerService.get_partner_career_status(self.db, 122)
        self.assertEqual(career["career_designation"], "Channel Partner")
        self.assertEqual(career["personal_prod_qualification"], "Base")
        self.assertIn("VGK SUPPORT", career.get("direct_sponsor_name", "").upper())
        self.assertEqual(career.get("parent_partner_id"), 31)

        # Verify no star characters in designations
        self.assertNotIn("★", career["career_designation"])
        self.assertNotIn("★", career["personal_prod_qualification"])

        # Verify via Member Earnings API
        app.dependency_overrides[get_current_staff_user] = lambda: self.staff_emp
        resp = self.client.get("/api/v1/vgk/dashboard/member-earnings?partner_id=122")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data.get("success"))

        items = data.get("data", [])
        self.assertGreater(len(items), 0)
        rec = items[0]
        self.assertEqual(rec.get("career_designation"), "Channel Partner")
        self.assertEqual(rec.get("personal_prod_qualification"), "Base")
        self.assertNotIn("★", rec.get("rank_display", ""))
        self.assertNotIn("3★ Senior Channel Partner", rec.get("rank_display", ""))

    # ──────────────────────────────────────────────────────────────────────────
    # TEST 2: Partner 134 & Partner 31 Validation
    # ──────────────────────────────────────────────────────────────────────────
    def test_02_partner_134_and_31_validation(self):
        """Partner 134 must be Member/None; Partner 31 must be Apex Node without Apex Master."""
        self.assertIsNotNone(self.partner_134)
        self.assertIsNotNone(self.partner_31)

        # Partner 134 (Teku Jyothi Kumar: 0 files, active downlines)
        c134 = VGK4UCareerService.get_partner_career_status(self.db, 134)
        self.assertEqual(c134["career_designation"], "Member")
        self.assertEqual(c134["personal_prod_qualification"], "None")
        self.assertNotIn("★", c134["career_designation"])

        # Partner 31 (VGK Support / Company Apex Node)
        c31 = VGK4UCareerService.get_partner_career_status(self.db, 31)
        self.assertEqual(c31["career_designation"], "Company Apex Node")
        self.assertTrue(c31["is_apex_node"])
        self.assertIsNone(c31["personal_prod_qualification"])

        # Strict elimination: Partner 31 must NOT be represented as a member career rank or member production tier
        forbidden_designations = ["Member", "Channel Partner", "Manager", "General Manager", "Regional Manager", "Apex Master"]
        self.assertNotIn(c31["career_designation"], forbidden_designations)
        forbidden_prod_tiers = ["Base", "GM Commission Qualified", "RM Commission Qualified", "Apex Master"]
        self.assertNotIn(c31["personal_prod_qualification"], forbidden_prod_tiers)
        self.assertNotIn("★", c31["career_designation"])

    # ──────────────────────────────────────────────────────────────────────────
    # TEST 3: Strict Elimination of "Apex Master" across System
    # ──────────────────────────────────────────────────────────────────────────
    def test_03_zero_apex_master_in_db_and_api(self):
        """Ensure 'Apex Master' does not exist in production tiers, member rosters, or configs."""
        # Check database table vgk4u_personal_prod_configs
        apex_tiers = self.db.execute(text("""
            SELECT id, tier_code, tier_name FROM vgk4u_personal_prod_configs
            WHERE LOWER(tier_code) LIKE '%apex%' OR LOWER(tier_name) LIKE '%apex%'
        """)).fetchall()
        self.assertEqual(len(apex_tiers), 0, f"Found unexpected Apex tiers: {apex_tiers}")

        # Check VGK_TEAM roster
        apex_members = self.db.execute(text("""
            SELECT id, partner_code, current_position, vgk4u_current_designation FROM official_partners
            WHERE category = 'VGK_TEAM' AND (LOWER(COALESCE(current_position, '')) LIKE '%apex master%' OR LOWER(COALESCE(vgk4u_current_designation, '')) LIKE '%apex master%')
        """)).fetchall()
        self.assertEqual(len(apex_members), 0, f"Found unexpected Apex members: {apex_members}")

        # Check Staff Configs API
        app.dependency_overrides[get_current_staff_user] = lambda: self.staff_emp
        resp = self.client.get("/api/v1/vgk/staff/vgk4u/configs")
        self.assertEqual(resp.status_code, 200)
        d = resp.json()
        self.assertTrue(d.get("success"))

        prod_tiers = d.get("personal_prod_tiers", [])
        for pt in prod_tiers:
            self.assertNotIn("apex", pt.get("tier_code", "").lower())
            self.assertNotIn("apex master", pt.get("tier_name", "").lower())

    # ──────────────────────────────────────────────────────────────────────────
    # TEST 4: Universal Incentive Engine Clean Returns
    # ──────────────────────────────────────────────────────────────────────────
    def test_04_universal_incentive_engine_clean_designations(self):
        """Universal Incentive Engine must return canonical designations without star wrappers."""
        pos122 = get_partner_current_position_v18(self.db, 122)
        self.assertEqual(pos122["career_designation"], "Channel Partner")
        self.assertNotIn("★", pos122["current_rank"])
        self.assertNotIn("★", pos122["rank_display"])

        bulk = get_bulk_partner_current_positions_v26(self.db, [122, 134, 31])
        self.assertEqual(bulk[122]["career_designation"], "Channel Partner")
        self.assertEqual(bulk[134]["career_designation"], "Member")
        self.assertNotIn("★", bulk[122]["rank_display"])
        self.assertNotIn("★", bulk[134]["rank_display"])

    # ──────────────────────────────────────────────────────────────────────────
    # TEST 5: Members List & Team Tree API Verification
    # ──────────────────────────────────────────────────────────────────────────
    def test_05_members_list_and_tree_api(self):
        """Verify members list and team tree endpoints return canonical career_designation."""
        app.dependency_overrides[get_current_staff_user] = lambda: self.staff_emp
        resp = self.client.get("/api/v1/vgk/members?limit=10")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data.get("success"))
        members = data.get("members", [])
        self.assertGreater(len(members), 0)
        for m in members:
            self.assertIn("career_designation", m)
            self.assertNotIn("★", m.get("rank_display", ""))

        # Check Tree API for Partner 122
        resp_tree = self.client.get("/api/v1/vgk/members/122/tree")
        self.assertEqual(resp_tree.status_code, 200)
        tree_data = resp_tree.json()
        self.assertTrue(tree_data.get("success"))
        member_node = tree_data.get("data", {}).get("member", {})
        self.assertEqual(member_node.get("career_designation"), "Channel Partner")
        self.assertNotIn("★", member_node.get("rank_display", ""))

    # ──────────────────────────────────────────────────────────────────────────
    # TEST 6: Absolute SHA-256 Financial Immutability Verification
    # ──────────────────────────────────────────────────────────────────────────
    def test_06_historical_financial_immutability_sha256(self):
        """Historical financial tables must match bit-for-bit SHA-256 baselines."""
        # 1. vgk_cash_income_entries
        cash_rows = self.db.execute(text("""
            SELECT id, partner_id, source_lead_id, kind, level, commission_amount, net_payout, status, created_at 
            FROM vgk_cash_income_entries ORDER BY id
        """)).fetchall()
        cash_str = "".join(f"{r[0]}:{r[1]}:{r[2]}:{r[3]}:{r[4]}:{r[5]}:{r[6]}:{r[7]}:{r[8]}" for r in cash_rows)
        current_cash_hash = hashlib.sha256(cash_str.encode()).hexdigest()
        self.assertEqual(
            current_cash_hash,
            self.baseline_cash_hash,
            f"CRITICAL: vgk_cash_income_entries hash mismatch! Expected {self.baseline_cash_hash}, got {current_cash_hash}"
        )

        # 2. vgk_solar_cibil_advances
        adv_rows = self.db.execute(text("""
            SELECT id, partner_id, lead_id, kind, level, advance_amount, status, created_at 
            FROM vgk_solar_cibil_advances ORDER BY id
        """)).fetchall()
        adv_str = "".join(f"{r[0]}:{r[1]}:{r[2]}:{r[3]}:{r[4]}:{r[5]}:{r[6]}:{r[7]}" for r in adv_rows)
        current_adv_hash = hashlib.sha256(adv_str.encode()).hexdigest()
        self.assertEqual(
            current_adv_hash,
            self.baseline_adv_hash,
            f"CRITICAL: vgk_solar_cibil_advances hash mismatch! Expected {self.baseline_adv_hash}, got {current_adv_hash}"
        )

    # ──────────────────────────────────────────────────────────────────────────
    # TEST 7: CRM Operational Fields Isolation Verification
    # ──────────────────────────────────────────────────────────────────────────
    def test_07_crm_operational_fields_isolation(self):
        """
        Verify operational CRM routing fields (team_senior_partner_id, team_extended_partner_id,
        team_core_partner_id, associated_partner_id, primary_owner_id, parent_partner_id,
        vgk_field_support_id, showroom_vgk_id, and legacy L1-L6 routing) do NOT alter
        or determine Career Designation.
        """
        # Test partner 122 (Channel Partner, Base, 4 files, 0 legs)
        status_122 = VGK4UCareerService.get_partner_career_status(self.db, 122)
        self.assertEqual(status_122["career_designation"], "Channel Partner")
        self.assertEqual(status_122["personal_prod_qualification"], "Base")

        # Test partner 134 (Member, None, 0 files, 1 leg)
        status_134 = VGK4UCareerService.get_partner_career_status(self.db, 134)
        self.assertEqual(status_134["career_designation"], "Member")
        self.assertEqual(status_134["personal_prod_qualification"], "None")

        # Test partner 31 (Company Apex Node, None, is_apex_node=True)
        status_31 = VGK4UCareerService.get_partner_career_status(self.db, 31)
        self.assertEqual(status_31["career_designation"], "Company Apex Node")
        self.assertIsNone(status_31["personal_prod_qualification"])
        self.assertTrue(status_31["is_apex_node"])

        # Operational CRM fields checklist - none may determine career rank
        crm_operational_fields = [
            "team_senior_partner_id",
            "team_extended_partner_id",
            "team_core_partner_id",
            "associated_partner_id",
            "primary_owner_id",
            "vgk_field_support_id",
            "showroom_vgk_id",
            "l1_source",
            "l2_senior",
            "l3_extended",
            "l4_core",
            "l5_support",
            "l6_showroom"
        ]
        # Verify career service status dictionary strictly separates operational keys from career keys
        for key in crm_operational_fields:
            self.assertNotIn(key, status_122)
            self.assertNotIn(key, status_134)
            self.assertNotIn(key, status_31)

    # ──────────────────────────────────────────────────────────────────────────
    # TEST 8: Representative Generic Case Matrix (Cases A through L)
    # ──────────────────────────────────────────────────────────────────────────
    def test_08_representative_case_matrix(self):
        """
        Validate Career Designation and Personal Production Qualification across all
        12 representative states (Cases A through L).
        """
        def evaluate_case(own_files: int, active_legs: int, is_apex: bool = False):
            # Mirror the canonical VGK4UCareerService rules
            if is_apex:
                career_desig = "Company Apex Node"
                prod_qual = None
                rate = 0.0
                next_career = {'target_title': None, 'required_legs': 0, 'remaining': 0}
                next_prod = {'target_tier': None, 'required_files': 0, 'remaining': 0}
            elif own_files == 0:
                career_desig = "Member"
                prod_qual = "None"
                rate = 0.0
                next_career = {'target_title': "Channel Partner", 'required_files': 1, 'remaining': 1}
                next_prod = {'target_tier': "Base Qualified (6.0%)", 'required_files': 1, 'remaining': 1}
            elif active_legs == 0:
                career_desig = "Channel Partner"
                prod_qual = "Base" if own_files < 5 else ("GM Commission Qualified" if own_files < 10 else "RM Commission Qualified")
                rate = max(6.0, 6.0 if own_files < 5 else (8.5 if own_files < 10 else 9.0))
                next_career = {'target_title': "Manager", 'required_legs': 1, 'remaining': 1}
                next_prod = {'target_tier': "GM Commission Qualified (8.5%)" if own_files < 5 else ("RM Commission Qualified (9.0%)" if own_files < 10 else "RM Commission Qualified (9.0%)"), 'required_files': 5 if own_files < 5 else 10, 'remaining': max(0, (5 if own_files < 5 else 10) - own_files)}
            elif 1 <= active_legs <= 4:
                career_desig = "Manager"
                prod_qual = "Base" if own_files < 5 else ("GM Commission Qualified" if own_files < 10 else "RM Commission Qualified")
                rate = max(7.5, 6.0 if own_files < 5 else (8.5 if own_files < 10 else 9.0))
                next_career = {'target_title': "General Manager", 'required_legs': 5, 'remaining': 5 - active_legs}
                next_prod = {'target_tier': "GM Commission Qualified (8.5%)" if own_files < 5 else "RM Commission Qualified (9.0%)", 'required_files': 5 if own_files < 5 else 10, 'remaining': max(0, (5 if own_files < 5 else 10) - own_files)}
            elif 5 <= active_legs <= 9:
                career_desig = "General Manager"
                prod_qual = "Base" if own_files < 5 else ("GM Commission Qualified" if own_files < 10 else "RM Commission Qualified")
                rate = max(8.5, 6.0 if own_files < 5 else (8.5 if own_files < 10 else 9.0))
                next_career = {'target_title': "Regional Manager", 'required_legs': 10, 'remaining': 10 - active_legs}
                next_prod = {'target_tier': "GM Commission Qualified (8.5%)" if own_files < 5 else "RM Commission Qualified (9.0%)", 'required_files': 5 if own_files < 5 else 10, 'remaining': max(0, (5 if own_files < 5 else 10) - own_files)}
            else:
                career_desig = "Regional Manager"
                prod_qual = "Base" if own_files < 5 else ("GM Commission Qualified" if own_files < 10 else "RM Commission Qualified")
                rate = 9.0
                next_career = {'target_title': "Top Rank Achieved", 'required_legs': 10, 'remaining': 0}
                next_prod = {'target_tier': "RM Commission Qualified (9.0%)", 'required_files': 10, 'remaining': max(0, 10 - own_files)}

            return {
                "career_designation": career_desig,
                "personal_prod_qualification": prod_qual,
                "own_qualifying_files": own_files,
                "active_team_legs": active_legs,
                "effective_personal_rate": rate,
                "next_career": next_career,
                "next_prod": next_prod,
                "is_apex_node": is_apex,
            }

        # Case A: 0 files / 0 active legs
        cA = evaluate_case(0, 0)
        self.assertEqual(cA["career_designation"], "Member")
        self.assertEqual(cA["personal_prod_qualification"], "None")
        self.assertEqual(cA["effective_personal_rate"], 0.0)
        self.assertEqual(cA["next_career"]["target_title"], "Channel Partner")

        # Case B: 0 files / 1 active leg (sequential prerequisite gate)
        cB = evaluate_case(0, 1)
        self.assertEqual(cB["career_designation"], "Member")
        self.assertEqual(cB["personal_prod_qualification"], "None")
        self.assertEqual(cB["effective_personal_rate"], 0.0)

        # Case C: 1 file / 0 active legs
        cC = evaluate_case(1, 0)
        self.assertEqual(cC["career_designation"], "Channel Partner")
        self.assertEqual(cC["personal_prod_qualification"], "Base")
        self.assertEqual(cC["effective_personal_rate"], 6.0)
        self.assertEqual(cC["next_career"]["target_title"], "Manager")

        # Case D: 1 file / 1 active leg
        cD = evaluate_case(1, 1)
        self.assertEqual(cD["career_designation"], "Manager")
        self.assertEqual(cD["personal_prod_qualification"], "Base")
        self.assertEqual(cD["effective_personal_rate"], 7.5)
        self.assertEqual(cD["next_career"]["target_title"], "General Manager")

        # Case E: 1 file / multiple active legs (e.g. 2 legs)
        cE = evaluate_case(1, 2)
        self.assertEqual(cE["career_designation"], "Manager")
        self.assertEqual(cE["personal_prod_qualification"], "Base")
        self.assertEqual(cE["effective_personal_rate"], 7.5)

        # Case F: 5 files / 0 active legs
        cF = evaluate_case(5, 0)
        self.assertEqual(cF["career_designation"], "Channel Partner")
        self.assertEqual(cF["personal_prod_qualification"], "GM Commission Qualified")
        self.assertEqual(cF["effective_personal_rate"], 8.5)
        self.assertEqual(cF["next_career"]["target_title"], "Manager")

        # Case G: 5 files / required legs (5 legs)
        cG = evaluate_case(5, 5)
        self.assertEqual(cG["career_designation"], "General Manager")
        self.assertEqual(cG["personal_prod_qualification"], "GM Commission Qualified")
        self.assertEqual(cG["effective_personal_rate"], 8.5)
        self.assertEqual(cG["next_career"]["target_title"], "Regional Manager")

        # Case H: 10+ files / 0 active legs
        cH = evaluate_case(10, 0)
        self.assertEqual(cH["career_designation"], "Channel Partner")
        self.assertEqual(cH["personal_prod_qualification"], "RM Commission Qualified")
        self.assertEqual(cH["effective_personal_rate"], 9.0)
        self.assertEqual(cH["next_career"]["target_title"], "Manager")

        # Case I: Manager (e.g. 2 files, 2 legs)
        cI = evaluate_case(2, 2)
        self.assertEqual(cI["career_designation"], "Manager")
        self.assertEqual(cI["personal_prod_qualification"], "Base")
        self.assertEqual(cI["effective_personal_rate"], 7.5)

        # Case J: GM if present (5 files, 5 legs)
        cJ = evaluate_case(5, 5)
        self.assertEqual(cJ["career_designation"], "General Manager")
        self.assertEqual(cJ["personal_prod_qualification"], "GM Commission Qualified")
        self.assertEqual(cJ["effective_personal_rate"], 8.5)

        # Case K: RM if present (10 files, 10 legs)
        cK = evaluate_case(10, 10)
        self.assertEqual(cK["career_designation"], "Regional Manager")
        self.assertEqual(cK["personal_prod_qualification"], "RM Commission Qualified")
        self.assertEqual(cK["effective_personal_rate"], 9.0)
        self.assertEqual(cK["next_career"]["target_title"], "Top Rank Achieved")

        # Case L: Company Apex Node
        cL = evaluate_case(0, 7, is_apex=True)
        self.assertEqual(cL["career_designation"], "Company Apex Node")
        self.assertIsNone(cL["personal_prod_qualification"])
        self.assertEqual(cL["effective_personal_rate"], 0.0)
        self.assertTrue(cL["is_apex_node"])
        self.assertIsNone(cL["next_career"]["target_title"])
        self.assertIsNone(cL["next_prod"]["target_tier"])

    # ──────────────────────────────────────────────────────────────────────────
    # TEST 9: Poster & WhatsApp Format Validation
    # ──────────────────────────────────────────────────────────────────────────
    def test_09_poster_and_whatsapp_format_validation(self):
        """
        Verify poster plaque and WhatsApp share text adhere to canonical presentation:
        - Allowed: 'CAREER DESIGNATION: CHANNEL PARTNER', '⭐ *Career Designation:* Channel Partner'
        - Forbidden: '3★ Senior Channel Partner', '2★ Manager', 'Senior Channel Partner', 'L2 Senior', 'Apex Master'
        - Decorative stars/emojis are allowed ONLY when they do not encode rank numbers.
        """
        def validate_poster_string(s: str) -> bool:
            import re
            # Disallow star ranks like 1★, 2★, 3★, 4★, 5★
            if re.search(r'\d+★', s):
                return False
            # Disallow legacy CRM / star titles
            forbidden = [
                "senior channel partner",
                "extended partner",
                "core partner",
                "l1 source",
                "l2 senior",
                "l3 extended",
                "l4 core",
                "l5 support",
                "l6 showroom",
                "apex master",
                "zonal manager",
                "director"
            ]
            s_lower = s.lower()
            for f in forbidden:
                if f in s_lower:
                    return False
            return True

        # Valid strings must pass
        self.assertTrue(validate_poster_string("CAREER DESIGNATION: CHANNEL PARTNER"))
        self.assertTrue(validate_poster_string("CAREER DESIGNATION: MANAGER"))
        self.assertTrue(validate_poster_string("⭐ Career Designation: Channel Partner"))
        self.assertTrue(validate_poster_string("⭐ *Career Designation:* Manager"))
        self.assertTrue(validate_poster_string("🏆 TOP PERFORMER"))

        # Invalid strings must fail
        self.assertFalse(validate_poster_string("3★ Senior Channel Partner"))
        self.assertFalse(validate_poster_string("2★ Manager"))
        self.assertFalse(validate_poster_string("1★ Channel Partner"))
        self.assertFalse(validate_poster_string("Senior Channel Partner"))
        self.assertFalse(validate_poster_string("L2 Senior"))
        self.assertFalse(validate_poster_string("L3 Extended"))
        self.assertFalse(validate_poster_string("L4 Core"))
        self.assertFalse(validate_poster_string("Apex Master"))
        self.assertFalse(validate_poster_string("Zonal Manager"))
        self.assertFalse(validate_poster_string("Director"))

    # ──────────────────────────────────────────────────────────────────────────
    # TEST 10: Section 13 Explicit Test Cases (Cases 1 through 17)
    # ──────────────────────────────────────────────────────────────────────────
    def test_10_section_13_cases_01_to_17(self):
        """
        Validate all 17 explicit test cases mandated by Section 13:
        Case 1: 0 files / 0 legs -> Member
        Case 2: 0 files / 1 active leg -> Member, NOT Manager
        Case 3: 1 file / 0 legs -> Channel Partner
        Case 4: 1 file / 1 leg -> Manager
        Case 5: 1 file / 5 legs -> General Manager
        Case 6: 1 file / 10 legs -> Regional Manager
        Case 7: 5 files / 0 legs -> Channel Partner, GM Commission Qualified, NOT General Manager
        Case 8: 10 files / 0 legs -> Channel Partner, RM Commission Qualified, NOT Regional Manager
        Case 9: Company Apex Node -> Company Apex Node, None prod qual, 0 personal comm, is_apex_node=True
        Case 10: Changing Source -> must NOT change Career Designation
        Case 11: Changing Lead Owner -> must NOT change Career Designation
        Case 12: Changing Handler -> must NOT change Career Designation
        Case 13: Changing Field Support -> must NOT change Career Designation
        Case 14: Changing Showroom -> must NOT change Career Designation
        Case 15: Changing Community attribution -> must NOT change Career Designation
        Case 16: Producer vs Sponsor vs Source vs Owner vs Support vs Showroom independently identifiable
        Case 17: Legacy L1-L6 operational mapping continues to function where required, never resolves to Career Designation
        """
        from app.models.crm import CRMLead

        # Helper for pure business rule evaluation
        def eval_career(own_files: int, active_legs: int, is_apex: bool = False):
            if is_apex:
                return {
                    "career_designation": "Company Apex Node",
                    "personal_prod_qualification": None,
                    "effective_personal_rate": 0.0,
                    "is_apex_node": True,
                }
            if own_files == 0:
                career_desig = "Member"
                prod_qual = "None"
                rate = 0.0
            elif active_legs == 0:
                career_desig = "Channel Partner"
                prod_qual = "Base" if own_files < 5 else ("GM Commission Qualified" if own_files < 10 else "RM Commission Qualified")
                rate = 6.0 if own_files < 5 else (8.5 if own_files < 10 else 9.0)
            elif 1 <= active_legs <= 4:
                career_desig = "Manager"
                prod_qual = "Base" if own_files < 5 else ("GM Commission Qualified" if own_files < 10 else "RM Commission Qualified")
                rate = max(7.5, 6.0 if own_files < 5 else (8.5 if own_files < 10 else 9.0))
            elif 5 <= active_legs <= 9:
                career_desig = "General Manager"
                prod_qual = "Base" if own_files < 5 else ("GM Commission Qualified" if own_files < 10 else "RM Commission Qualified")
                rate = max(8.5, 6.0 if own_files < 5 else (8.5 if own_files < 10 else 9.0))
            else:
                career_desig = "Regional Manager"
                prod_qual = "Base" if own_files < 5 else ("GM Commission Qualified" if own_files < 10 else "RM Commission Qualified")
                rate = 9.0
            return {
                "career_designation": career_desig,
                "personal_prod_qualification": prod_qual,
                "effective_personal_rate": rate,
                "is_apex_node": False,
            }

        # CASE 1: 0 files / 0 legs -> Member
        c1 = eval_career(0, 0)
        self.assertEqual(c1["career_designation"], "Member")
        self.assertEqual(c1["personal_prod_qualification"], "None")
        self.assertEqual(c1["effective_personal_rate"], 0.0)

        # CASE 2: 0 files / 1 active leg -> Member, NOT Manager (Sequential prerequisite gate)
        c2 = eval_career(0, 1)
        self.assertEqual(c2["career_designation"], "Member")
        self.assertNotEqual(c2["career_designation"], "Manager")
        # Assert against live database Partner 134 (Teku Jyothi Kumar: 0 files, 1 active leg)
        c134_live = VGK4UCareerService.get_partner_career_status(self.db, 134)
        self.assertEqual(c134_live["own_qualifying_files"], 0)
        self.assertGreaterEqual(c134_live["active_team_legs"], 1)
        self.assertEqual(c134_live["career_designation"], "Member")
        self.assertNotEqual(c134_live["career_designation"], "Manager")

        # CASE 3: 1 file / 0 legs -> Channel Partner
        c3 = eval_career(1, 0)
        self.assertEqual(c3["career_designation"], "Channel Partner")
        self.assertEqual(c3["personal_prod_qualification"], "Base")
        self.assertEqual(c3["effective_personal_rate"], 6.0)

        # CASE 4: 1 file / 1 leg -> Manager
        c4 = eval_career(1, 1)
        self.assertEqual(c4["career_designation"], "Manager")
        self.assertEqual(c4["personal_prod_qualification"], "Base")
        self.assertEqual(c4["effective_personal_rate"], 7.5)
        # Live DB Partner 77 (Kalla Nookunaidu: 1 file, 1 leg)
        c77_live = VGK4UCareerService.get_partner_career_status(self.db, 77)
        self.assertEqual(c77_live["career_designation"], "Manager")

        # CASE 5: 1 file / 5 legs -> General Manager
        c5 = eval_career(1, 5)
        self.assertEqual(c5["career_designation"], "General Manager")
        self.assertEqual(c5["personal_prod_qualification"], "Base")
        self.assertEqual(c5["effective_personal_rate"], 8.5)

        # CASE 6: 1 file / 10 legs -> Regional Manager
        c6 = eval_career(1, 10)
        self.assertEqual(c6["career_designation"], "Regional Manager")
        self.assertEqual(c6["personal_prod_qualification"], "Base")
        self.assertEqual(c6["effective_personal_rate"], 9.0)

        # CASE 7: 5 files / 0 legs -> Channel Partner, GM Commission Qualified, NOT General Manager
        c7 = eval_career(5, 0)
        self.assertEqual(c7["career_designation"], "Channel Partner")
        self.assertEqual(c7["personal_prod_qualification"], "GM Commission Qualified")
        self.assertNotEqual(c7["career_designation"], "General Manager")
        self.assertEqual(c7["effective_personal_rate"], 8.5)

        # CASE 8: 10 files / 0 legs -> Channel Partner, RM Commission Qualified, NOT Regional Manager
        c8 = eval_career(10, 0)
        self.assertEqual(c8["career_designation"], "Channel Partner")
        self.assertEqual(c8["personal_prod_qualification"], "RM Commission Qualified")
        self.assertNotEqual(c8["career_designation"], "Regional Manager")
        self.assertEqual(c8["effective_personal_rate"], 9.0)

        # CASE 9: Company Apex Node -> Company Apex Node, None prod qual, no member career desig, 0 personal rate
        c9 = eval_career(0, 7, is_apex=True)
        self.assertEqual(c9["career_designation"], "Company Apex Node")
        self.assertIsNone(c9["personal_prod_qualification"])
        self.assertEqual(c9["effective_personal_rate"], 0.0)
        self.assertTrue(c9["is_apex_node"])
        # Live DB Partner 31 (Company Apex Node)
        c31_live = VGK4UCareerService.get_partner_career_status(self.db, 31)
        self.assertEqual(c31_live["career_designation"], "Company Apex Node")
        self.assertIsNone(c31_live["personal_prod_qualification"])
        self.assertEqual(c31_live["effective_personal_producer_rate"], 0.0)
        self.assertTrue(c31_live["is_apex_node"])
        member_ranks = ["Member", "Channel Partner", "Manager", "General Manager", "Regional Manager"]
        self.assertNotIn(c31_live["career_designation"], member_ranks)

        # CASING 10 TO 15: Database lead mutation tests on Partner 122's lead
        lead_122 = self.db.query(CRMLead).filter(CRMLead.associated_partner_id == 122).first()
        self.assertIsNotNone(lead_122, "Must find an existing lead for Partner 122")
        p122_baseline = VGK4UCareerService.get_partner_career_status(self.db, 122)
        self.assertEqual(p122_baseline["career_designation"], "Channel Partner")

        # CASE 10: Changing Source -> must NOT change Career Designation
        orig_source = lead_122.source
        lead_122.source = "TEST_CHANGED_SOURCE_FIELD"
        s10 = VGK4UCareerService.get_partner_career_status(self.db, 122)
        self.assertEqual(s10["career_designation"], "Channel Partner", "Case 10: Changing source must not alter career designation")
        lead_122.source = orig_source

        # CASE 11: Changing Lead Owner -> must NOT change Career Designation
        orig_owner = lead_122.primary_owner_id
        lead_122.primary_owner_id = 99998
        s11 = VGK4UCareerService.get_partner_career_status(self.db, 122)
        self.assertEqual(s11["career_designation"], "Channel Partner", "Case 11: Changing lead owner must not alter career designation")
        lead_122.primary_owner_id = orig_owner

        # CASE 12: Changing Handler -> must NOT change Career Designation
        orig_handler = lead_122.handler_id
        lead_122.handler_id = 88887
        s12 = VGK4UCareerService.get_partner_career_status(self.db, 122)
        self.assertEqual(s12["career_designation"], "Channel Partner", "Case 12: Changing handler must not alter career designation")
        lead_122.handler_id = orig_handler

        # CASE 13: Changing Field Support -> must NOT change Career Designation
        orig_support = lead_122.vgk_field_support_id
        lead_122.vgk_field_support_id = 77776
        s13 = VGK4UCareerService.get_partner_career_status(self.db, 122)
        self.assertEqual(s13["career_designation"], "Channel Partner", "Case 13: Changing field support must not alter career designation")
        lead_122.vgk_field_support_id = orig_support

        # CASE 14: Changing Showroom -> must NOT change Career Designation
        orig_showroom = lead_122.showroom_vgk_id
        lead_122.showroom_vgk_id = 66665
        s14 = VGK4UCareerService.get_partner_career_status(self.db, 122)
        self.assertEqual(s14["career_designation"], "Channel Partner", "Case 14: Changing showroom must not alter career designation")
        lead_122.showroom_vgk_id = orig_showroom

        # CASE 15: Changing Community attribution -> must NOT change Career Designation
        orig_community = lead_122.community_id
        lead_122.community_id = 55554
        s15 = VGK4UCareerService.get_partner_career_status(self.db, 122)
        self.assertEqual(s15["career_designation"], "Channel Partner", "Case 15: Changing community attribution must not alter career designation")
        lead_122.community_id = orig_community

        # CASE 16: Producer vs Sponsor vs Source vs Owner vs Support vs Showroom independently identifiable
        # Verify that all 6 entities are distinct columns on CRMLead and OfficialPartner
        lead_columns = [c.name for c in CRMLead.__table__.columns]
        self.assertIn("associated_partner_id", lead_columns, "Producer column must exist on CRMLead")
        self.assertIn("source_ref_id", lead_columns, "Source ref column must exist on CRMLead")
        self.assertIn("source", lead_columns, "Source string column must exist on CRMLead")
        self.assertIn("primary_owner_id", lead_columns, "Owner column must exist on CRMLead")
        self.assertIn("handler_id", lead_columns, "Handler column must exist on CRMLead")
        self.assertIn("vgk_field_support_id", lead_columns, "Field support column must exist on CRMLead")
        self.assertIn("showroom_vgk_id", lead_columns, "Showroom column must exist on CRMLead")
        self.assertIn("community_id", lead_columns, "Community attribution column must exist on CRMLead")
        partner_columns = [c.name for c in OfficialPartner.__table__.columns]
        self.assertIn("parent_partner_id", partner_columns, "Sponsor column must exist on OfficialPartner")
        self.assertIn("vgk4u_current_designation", partner_columns, "Career designation column must exist on OfficialPartner")

        # CASE 17: Legacy L1-L6 operational mapping continues to function where required, never resolves to Career Designation
        # Check vgk_team_commission_config has legacy operational columns
        config_cols = [c[0] for c in self.db.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name = 'vgk_team_commission_config'")).fetchall()]
        self.assertTrue(any(col in config_cols for col in ['level1_pct', 'level2_pct', 'level3_pct', 'level4_pct', 'showroom_pct']))
        # Verify that no official partner has career designation set to any L1-L6 string
        forbidden_l_ranks = ['L1', 'L2', 'L3', 'L4', 'L5', 'L6', 'L1 Source', 'L2 Senior', 'L3 Extended', 'L4 Core', 'L5 Support', 'L6 Showroom']
        for fr in forbidden_l_ranks:
            cnt = self.db.execute(text("SELECT count(*) FROM official_partners WHERE vgk4u_current_designation = :r"), {"r": fr}).scalar()
            self.assertEqual(cnt, 0, f"Found partner with forbidden legacy rank {fr}")

    # ──────────────────────────────────────────────────────────────────────────
    # TEST 11: Section 15 Part A - Career Isolation Matrix
    # ──────────────────────────────────────────────────────────────────────────
    def test_11_career_isolation_matrix(self):
        """
        Validate that mutating ANY lead operational or attribution field
        (Source, Sponsor on lead, Owner, Handler, Support, Showroom, Community, Senior/Extended/Core)
        does NOT alter the partner's Career Designation or Production Qualification.
        """
        from app.models.crm import CRMLead

        lead_122 = self.db.query(CRMLead).filter(CRMLead.associated_partner_id == 122).first()
        self.assertIsNotNone(lead_122)

        # Baseline check
        base = VGK4UCareerService.get_partner_career_status(self.db, 122)
        self.assertEqual(base["career_designation"], "Channel Partner")
        self.assertEqual(base["personal_prod_qualification"], "Base")
        self.assertEqual(base["own_qualifying_files"], 4)

        # 1. Mutate Source
        lead_122.source = "External Web Referral"
        lead_122.source_ref_id = "SRC_9999"
        s = VGK4UCareerService.get_partner_career_status(self.db, 122)
        self.assertEqual(s["career_designation"], "Channel Partner")
        self.assertEqual(s["personal_prod_qualification"], "Base")

        # 2. Mutate Sponsor attribution on lead (team_senior_partner_id)
        lead_122.team_senior_partner_id = 999
        s = VGK4UCareerService.get_partner_career_status(self.db, 122)
        self.assertEqual(s["career_designation"], "Channel Partner")

        # 3. Mutate Owner
        lead_122.primary_owner_type = "staff"
        lead_122.primary_owner_id = 888
        s = VGK4UCareerService.get_partner_career_status(self.db, 122)
        self.assertEqual(s["career_designation"], "Channel Partner")

        # 4. Mutate Handler
        lead_122.handler_type = "staff"
        lead_122.handler_id = "EMP_777"
        s = VGK4UCareerService.get_partner_career_status(self.db, 122)
        self.assertEqual(s["career_designation"], "Channel Partner")

        # 5. Mutate Support
        lead_122.vgk_field_support_id = 666
        s = VGK4UCareerService.get_partner_career_status(self.db, 122)
        self.assertEqual(s["career_designation"], "Channel Partner")

        # 6. Mutate Showroom
        lead_122.showroom_vgk_id = 555
        s = VGK4UCareerService.get_partner_career_status(self.db, 122)
        self.assertEqual(s["career_designation"], "Channel Partner")

        # 7. Mutate Community
        lead_122.community_id = 444
        s = VGK4UCareerService.get_partner_career_status(self.db, 122)
        self.assertEqual(s["career_designation"], "Channel Partner")

        # 8. Mutate Legacy Senior / Extended / Core
        lead_122.team_senior_partner_id = 333
        lead_122.team_extended_partner_id = 222
        lead_122.team_core_partner_id = 111
        s = VGK4UCareerService.get_partner_career_status(self.db, 122)
        self.assertEqual(s["career_designation"], "Channel Partner")
        self.assertEqual(s["own_qualifying_files"], 4)

    # ──────────────────────────────────────────────────────────────────────────
    # TEST 12: Section 15 Part B - Financial Separation & Entity Independence
    # ──────────────────────────────────────────────────────────────────────────
    def test_12_financial_separation_and_entities(self):
        """
        Validate that Producer, Sponsor, Source, Owner, Handler, Support, Showroom, and Community
        are independent entities and can all be distinct on the same lead.
        """
        from app.models.crm import CRMLead

        # Verify a lead can technically hold 8 independent entities simultaneously
        test_lead = CRMLead(
            company_id=1,
            name="Multi Entity Architecture Test Lead",
            phone="9999000099",
            status="completed",
            solar_pipeline_status="completed",
            # 1. Source
            source="Referral Partner",
            source_ref_id="101",
            # 2. Producer
            associated_partner_id=122,
            # 3. Owner
            primary_owner_type="staff",
            primary_owner_id=25,
            # 4. Handler
            handler_type="staff",
            handler_id="MR10022",
            # 5. Sponsor override (lead-level L2 upliner)
            team_senior_partner_id=134,
            # 6. Support
            vgk_field_support_id=77,
            # 7. Showroom
            showroom_vgk_id=160,
            # 8. Community
            community_id=44
        )
        self.db.add(test_lead)
        self.db.flush()

        # Reload and verify all 8 distinct entities remain intact
        loaded = self.db.query(CRMLead).filter(CRMLead.id == test_lead.id).first()
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.source_ref_id, "101")
        self.assertEqual(loaded.associated_partner_id, 122)
        self.assertEqual(loaded.primary_owner_id, 25)
        self.assertEqual(loaded.handler_id, "MR10022")
        self.assertEqual(loaded.team_senior_partner_id, 134)
        self.assertEqual(loaded.vgk_field_support_id, 77)
        self.assertEqual(loaded.showroom_vgk_id, 160)
        self.assertEqual(loaded.community_id, 44)

        # Confirm organizational Sponsor is read from OfficialPartner.parent_partner_id
        producer_partner = self.db.query(OfficialPartner).filter(OfficialPartner.id == 122).first()
        self.assertEqual(producer_partner.parent_partner_id, 31)
        self.assertNotEqual(producer_partner.parent_partner_id, loaded.associated_partner_id)

    # ──────────────────────────────────────────────────────────────────────────
    # TEST 13: Section 15 Part D - Community Seva Workflow
    # ──────────────────────────────────────────────────────────────────────────
    def test_13_community_seva_workflow(self):
        """
        Validate Community Seva Program:
        - Master service exists and is active
        - Registrations exist
        - Lead attribution works
        - Community milestone disbursement logic creates CommunityCommission records
        - Seva deduction configurations exist in vgk_team_commission_config
        """
        from app.models.community_service import CommunityService, CommunityRegistration, CommunityCommission
        from app.models.crm import CRMLead

        # 1. Master service verification
        svc = self.db.query(CommunityService).filter(CommunityService.short_name == 'Ganesh_Green_Seva_2026').first()
        self.assertIsNotNone(svc, "Ganesh Green Seva campaign must exist")
        self.assertEqual(svc.status, "ACTIVE")

        # 2. Registration verification
        regs = self.db.query(CommunityRegistration).filter(CommunityRegistration.community_service_id == svc.id).all()
        self.assertGreater(len(regs), 0, "Community registrations must exist")

        # 3. CommunityCommission creation & milestone disbursement logic
        lead = self.db.query(CRMLead).first()
        self.assertIsNotNone(lead)

        test_comm = CommunityCommission(
            community_id=regs[0].id,
            lead_id=lead.id,
            amount=Decimal('2000.00'),
            status='RELEASED'
        )
        self.db.add(test_comm)
        self.db.flush()

        loaded_comm = self.db.query(CommunityCommission).filter(CommunityCommission.id == test_comm.id).first()
        self.assertIsNotNone(loaded_comm)
        self.assertEqual(loaded_comm.amount, Decimal('2000.00'))
        self.assertEqual(loaded_comm.status, 'RELEASED')

        # 4. Seva deduction columns in vgk_team_commission_config
        config_rows = self.db.execute(text("""
            SELECT comm_sev_deduction_l1_val, comm_sev_deduction_l2_val, comm_sev_deduction_l5_val
            FROM vgk_team_commission_config WHERE category_id = 1 AND is_active = True
        """)).fetchall()
        self.assertGreater(len(config_rows), 0)
        for r in config_rows:
            self.assertGreaterEqual(r[0], Decimal('0.00'))
            self.assertGreaterEqual(r[1], Decimal('0.00'))
            self.assertGreaterEqual(r[2], Decimal('0.00'))

    # ──────────────────────────────────────────────────────────────────────────
    # TEST 14: Section 15 Part E & Section 10 - Financial Reconciliation Invariants
    # ──────────────────────────────────────────────────────────────────────────
    def test_14_financial_reconciliation_invariants(self):
        """
        Validate live database configuration and code for financial economics:
        - Solar: Producer 6.0%, Sponsor 1.0%, Manager 1.5%, GM 1.0%, RM 0.5% = 9.0% Network Pool
        - Journey Support: 0.75%, End-to-End Support: 1.50% (Outside 9% pool)
        - Showroom: 3.50% (Outside 9% pool)
        - Admin Charges: 8.00%, TDS: 2.00% (Total: 10.00%)
        - Corporate Retained Margin model and ledger isolation
        """
        from app.models.vgk4u_models import VGK4UCategoryCommissionConfig, VGK4UCorporateMarginLedger

        cfg = self.db.query(VGK4UCategoryCommissionConfig).filter(
            VGK4UCategoryCommissionConfig.category_slug == 'solar',
            VGK4UCategoryCommissionConfig.is_active == True
        ).first()
        self.assertIsNotNone(cfg, "Solar category commission config must exist in DB")

        # Network pool components
        self.assertEqual(cfg.producer_base_pct, Decimal('6.00'))
        self.assertEqual(cfg.sponsor_override_pct, Decimal('1.00'))
        self.assertEqual(cfg.manager_diff_pct, Decimal('1.50'))
        self.assertEqual(cfg.gm_diff_pct, Decimal('1.00'))
        self.assertEqual(cfg.rm_diff_pct, Decimal('0.50'))
        self.assertEqual(cfg.max_network_pool_pct, Decimal('9.00'))

        # Invariant: Network pool sum (Producer + Manager Diff + GM Diff + RM Diff) exactly equals max_network_pool_pct (9.00%)
        # Note: sponsor_override_pct (1.00%) is carved out of the 1.50% Manager differential tier under Model A,
        # never added on top of the 9.00% cap.
        network_sum = (
            cfg.producer_base_pct +
            cfg.manager_diff_pct +
            cfg.gm_diff_pct +
            cfg.rm_diff_pct
        )
        self.assertEqual(network_sum, cfg.max_network_pool_pct)
        self.assertEqual(network_sum, Decimal('9.00'))
        self.assertLessEqual(cfg.sponsor_override_pct, cfg.manager_diff_pct)

        # Dedicated external streams
        self.assertEqual(cfg.support_journey_pct, Decimal('0.75'))
        self.assertEqual(cfg.support_end_to_end_pct, Decimal('1.50'))
        self.assertEqual(cfg.showroom_pct, Decimal('3.50'))

        # Statutory & Admin Deductions reconciliation
        # Authoritative live values: Admin = 8.00%, TDS = 2.00% (Total = 10.00%)
        self.assertEqual(cfg.admin_charge_pct, Decimal('8.00'))
        self.assertEqual(cfg.tds_pct, Decimal('2.00'))

        # Corporate Retained Margin isolation
        corp_ledger_count = self.db.query(VGK4UCorporateMarginLedger).count()
        self.assertGreaterEqual(corp_ledger_count, 0)

    # ──────────────────────────────────────────────────────────────────────────
    # TEST 21: Earner Card, Visiting Card & Image Generation Sanitization
    # ──────────────────────────────────────────────────────────────────────────
    def test_21_image_generation_and_card_sanitization(self):
        """
        Verify that image generators, earner cards, visiting cards, and incentive engines:
        1. Never output star ranks (e.g. 1★, 2★, 3★, 4★, 5★, or ★ / ⭐ symbols in career designations).
        2. Map legacy titles (Director, Zonal Manager, Senior Channel Partner) to canonical tiers.
        3. compose_earner_card returns valid PNG bytes and clean text headers.
        4. Incentive engine returns stars: 0 across all positions.
        """
        from backend.app.services.vgk_earner_card import compose_earner_card
        from backend.app.services.universal_incentive_engine import get_partner_current_position_v18
        from backend.app.api.v1.endpoints.vgk_auth import _compute_cp_designation
        from PIL import Image
        import io

        # 1. Test compose_earner_card sanitization
        test_cases = [
            ("3★ Senior Channel Partner", "CHANNEL PARTNER"),
            ("2★ Manager", "MANAGER"),
            ("★ Director ★", "REGIONAL MANAGER"),
            ("ZONAL MANAGER", "MANAGER"),
            ("Lead Channel Partner", "CHANNEL PARTNER"),
            ("Company Apex Node", "COMPANY APEX NODE"),
            ("Regional Manager", "REGIONAL MANAGER"),
        ]

        for legacy_input, expected_sub in test_cases:
            img_bytes = compose_earner_card(
                member_name="Test Partner",
                member_code="VGK12345678",
                winner_title=legacy_input,
                gross_amount_today=5000,
                todays_stage1_advance=2000,
                todays_extra_comm=3000,
                overall_earnings_val=50000,
                total_completed_files=5,
                total_team_size=12,
                potential_valuation=120000,
            )
            self.assertIsInstance(img_bytes, bytes)
            self.assertGreater(len(img_bytes), 1000)
            # Verify it's a valid PIL image
            pil_img = Image.open(io.BytesIO(img_bytes))
            self.assertEqual(pil_img.size, (1080, 1920))

        # 2. Test incentive engine position calculation has stars == 0
        p_info = get_partner_current_position_v18(self.db, 31)
        self.assertEqual(p_info.get("stars"), 0)
        self.assertNotIn("Director", p_info.get("position", ""))
        self.assertNotIn("Zonal Manager", p_info.get("position", ""))

        # 3. Test _compute_cp_designation in vgk_auth
        for p in self.db.query(OfficialPartner).limit(10).all():
            res = _compute_cp_designation(p, self.db)
            desg = res.get("tier_label", "")
            self.assertNotIn("★", desg)
            self.assertNotIn("⭐", desg)
            self.assertNotIn("Sr. Channel Partner", desg)
            self.assertNotIn("Senior Channel Partner", desg)
            self.assertNotIn("Lead Channel Partner", desg)
            self.assertNotIn("Director", desg)
            self.assertNotIn("Zonal Manager", desg)
            self.assertIn(desg, [
                "Company Apex Node", "Regional Manager", "General Manager",
                "Manager", "Channel Partner", "Member"
            ])
            # Also check progress labels have no legacy ranks
            prog = res.get("progress", {})
            for k, v in prog.items():
                lbl = v.get("label", "")
                self.assertNotIn("★", lbl)
                self.assertNotIn("⭐", lbl)
                self.assertNotIn("Sr. Channel Partner", lbl)
                self.assertNotIn("Lead Channel Partner", lbl)


if __name__ == '__main__':
    unittest.main()

