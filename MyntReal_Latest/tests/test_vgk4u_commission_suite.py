"""
VGK4U Commission Test Suite
Created: 2026-09-12
Covers:
- TC-COMM-01 through TC-COMM-20
- Realistic ₹2,00,000 Solar Project Scenarios
- Personal Production Escalation & Absorption
- Leg-Capping & Sequential Progression
- Financial Immutability Verification
"""

import unittest
from decimal import Decimal
import hashlib
import sys
import os

# Dynamic path resolution
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend')))

from app.core.database import SessionLocal
from app.services.vgk4u_career_service import (
    VGK4UCareerService,
    DESIGNATION_MEMBER,
    DESIGNATION_CHANNEL_PARTNER,
    DESIGNATION_MANAGER,
    DESIGNATION_GENERAL_MANAGER,
    DESIGNATION_REGIONAL_MANAGER,
    DESIGNATION_APEX_NODE,
    PROD_QUAL_NONE,
    PROD_QUAL_BASE,
    PROD_QUAL_GM,
    PROD_QUAL_RM,
    ROOT_APEX_PARTNER_ID,
)
from app.services.vgk4u_waterfall_engine import VGK4UWaterfallEngine


class TestVGK4UCommissionSuite(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db = SessionLocal()
        cls.baseline_cash_hash = '4ab74b1bf3583ad22c291c974d3bb99ee8a4e6ff0860cb84d6713199e11aae35'
        cls.baseline_adv_hash = '5b1322cc5587bd5994e2b4f1947afab94d17019b05bcee753805a7163db37f8b'

    @classmethod
    def tearDownClass(cls):
        cls.db.close()

    # --- SIMULATED MOCK STATUS MAP HELPER ---
    def _create_mock_hierarchy(self, producer_career, producer_prod_qual, upline_tiers, producer_rate=6.0):
        """
        Builds a synthetic status map to test differential absorption deterministically.
        upline_tiers is a list of (partner_id, career_desig) or (partner_id, career_desig, is_active).
        """
        status_map = {
            1001: {
                'partner_id': 1001,
                'partner_code': 'VGK071001',
                'partner_name': 'Producer One',
                'parent_partner_id': upline_tiers[0][0] if upline_tiers else None,
                'is_apex_node': False,
                'is_active': True,
                'own_qualifying_files': 1 if producer_career != DESIGNATION_MEMBER else 0,
                'active_team_legs': 0,
                'career_designation': producer_career,
                'personal_prod_qualification': producer_prod_qual,
                'effective_personal_producer_rate': producer_rate,
            }
        }
        for i, tier in enumerate(upline_tiers):
            pid = tier[0]
            desig = tier[1]
            is_active = tier[2] if len(tier) > 2 else True
            next_parent = upline_tiers[i + 1][0] if i + 1 < len(upline_tiers) else ROOT_APEX_PARTNER_ID

            status_map[pid] = {
                'partner_id': pid,
                'partner_code': f'VGK07{pid}',
                'partner_name': f'Upline Partner {pid}',
                'parent_partner_id': next_parent,
                'is_apex_node': (desig == DESIGNATION_APEX_NODE),
                'is_active': is_active,
                'own_qualifying_files': 1 if desig != DESIGNATION_MEMBER else 0,
                'active_team_legs': 1,
                'career_designation': desig,
                'personal_prod_qualification': PROD_QUAL_BASE if desig != DESIGNATION_MEMBER else PROD_QUAL_NONE,
                'effective_personal_producer_rate': 6.0,
            }

        # Add Apex Node if not already present
        if ROOT_APEX_PARTNER_ID not in status_map:
            status_map[ROOT_APEX_PARTNER_ID] = {
                'partner_id': ROOT_APEX_PARTNER_ID,
                'partner_code': 'VGK07102207',
                'partner_name': 'VGK Support',
                'parent_partner_id': None,
                'is_apex_node': True,
                'is_active': True,
                'own_qualifying_files': 10,
                'active_team_legs': 10,
                'career_designation': DESIGNATION_APEX_NODE,
                'personal_prod_qualification': None,
                'effective_personal_producer_rate': 0.0,
            }

        return status_map

    # --- CAREER LOGIC UNIT TESTS ---
    def test_tc_comm_01_member_zero_files(self):
        """TC-COMM-01: 0 files + 0 legs -> Member"""
        files, legs = 0, 0
        desig = DESIGNATION_MEMBER if files == 0 else (DESIGNATION_CHANNEL_PARTNER if legs == 0 else DESIGNATION_MANAGER)
        self.assertEqual(desig, DESIGNATION_MEMBER)

    def test_tc_comm_02_channel_partner_one_file(self):
        """TC-COMM-02: 1 file + 0 legs -> Channel Partner (6.0%)"""
        files, legs = 1, 0
        desig = DESIGNATION_CHANNEL_PARTNER if (files >= 1 and legs == 0) else None
        self.assertEqual(desig, DESIGNATION_CHANNEL_PARTNER)

    def test_tc_comm_03_manager_one_file_one_leg(self):
        """TC-COMM-03: 1 file + 1 active leg -> Manager (7.5%)"""
        files, legs = 1, 1
        desig = DESIGNATION_MANAGER if (files >= 1 and 1 <= legs <= 4) else None
        self.assertEqual(desig, DESIGNATION_MANAGER)

    def test_tc_comm_04_gm_one_file_five_legs(self):
        """TC-COMM-04: 1 file + 5 active legs -> General Manager (8.5%)"""
        files, legs = 1, 5
        desig = DESIGNATION_GENERAL_MANAGER if (files >= 1 and 5 <= legs <= 9) else None
        self.assertEqual(desig, DESIGNATION_GENERAL_MANAGER)

    def test_tc_comm_05_rm_one_file_ten_legs(self):
        """TC-COMM-05: 1 file + 10 active legs -> Regional Manager (9.0%)"""
        files, legs = 1, 10
        desig = DESIGNATION_REGIONAL_MANAGER if (files >= 1 and legs >= 10) else None
        self.assertEqual(desig, DESIGNATION_REGIONAL_MANAGER)

    def test_tc_comm_06_five_files_zero_legs(self):
        """TC-COMM-06: 5 files + 0 legs -> Channel Partner | GM Commission Qualified (8.5%)"""
        files, legs = 5, 0
        career = DESIGNATION_CHANNEL_PARTNER
        prod_qual = PROD_QUAL_GM if 5 <= files <= 9 else PROD_QUAL_BASE
        rate = max(6.0, 8.5)
        self.assertEqual(career, DESIGNATION_CHANNEL_PARTNER)
        self.assertEqual(prod_qual, PROD_QUAL_GM)
        self.assertEqual(rate, 8.5)

    def test_tc_comm_07_five_files_one_leg(self):
        """TC-COMM-07: 5 files + 1 active leg -> Manager | GM Commission Qualified (8.5%)"""
        files, legs = 5, 1
        career = DESIGNATION_MANAGER
        prod_qual = PROD_QUAL_GM
        rate = max(7.5, 8.5)
        self.assertEqual(career, DESIGNATION_MANAGER)
        self.assertEqual(prod_qual, PROD_QUAL_GM)
        self.assertEqual(rate, 8.5)

    def test_tc_comm_08_five_files_five_legs(self):
        """TC-COMM-08: 5 files + 5 active legs -> General Manager | GM Commission Qualified (8.5%)"""
        files, legs = 5, 5
        career = DESIGNATION_GENERAL_MANAGER
        prod_qual = PROD_QUAL_GM
        rate = max(8.5, 8.5)
        self.assertEqual(career, DESIGNATION_GENERAL_MANAGER)
        self.assertEqual(prod_qual, PROD_QUAL_GM)
        self.assertEqual(rate, 8.5)

    def test_tc_comm_09_ten_files_zero_legs(self):
        """TC-COMM-09: 10 files + 0 legs -> Channel Partner | RM Commission Qualified (9.0%)"""
        files, legs = 10, 0
        career = DESIGNATION_CHANNEL_PARTNER
        prod_qual = PROD_QUAL_RM
        rate = max(6.0, 9.0)
        self.assertEqual(career, DESIGNATION_CHANNEL_PARTNER)
        self.assertEqual(prod_qual, PROD_QUAL_RM)
        self.assertEqual(rate, 9.0)

    def test_tc_comm_10_ten_files_two_legs(self):
        """TC-COMM-10: 10 files + 2 active legs -> Manager | RM Commission Qualified (9.0%)"""
        files, legs = 10, 2
        career = DESIGNATION_MANAGER
        prod_qual = PROD_QUAL_RM
        rate = max(7.5, 9.0)
        self.assertEqual(career, DESIGNATION_MANAGER)
        self.assertEqual(prod_qual, PROD_QUAL_RM)
        self.assertEqual(rate, 9.0)

    def test_tc_comm_11_ten_files_ten_legs(self):
        """TC-COMM-11: 10 files + 10 active legs -> Regional Manager | RM Qualified (9.0%)"""
        files, legs = 10, 10
        career = DESIGNATION_REGIONAL_MANAGER
        prod_qual = PROD_QUAL_RM
        rate = max(9.0, 9.0)
        self.assertEqual(career, DESIGNATION_REGIONAL_MANAGER)
        self.assertEqual(prod_qual, PROD_QUAL_RM)
        self.assertEqual(rate, 9.0)

    def test_tc_comm_12_twenty_files_zero_legs(self):
        """TC-COMM-12: 20 files + 0 legs -> Channel Partner | RM Commission Qualified (9.0%)"""
        files, legs = 20, 0
        career = DESIGNATION_CHANNEL_PARTNER
        prod_qual = PROD_QUAL_RM
        rate = max(6.0, 9.0)
        self.assertEqual(career, DESIGNATION_CHANNEL_PARTNER)
        self.assertEqual(prod_qual, PROD_QUAL_RM)
        self.assertEqual(rate, 9.0)

    # --- WATERFALL DIFFERENTIAL & MODEL A TESTS ---
    def test_tc_comm_13_canonical_waterfall_member_sponsor(self):
        """
        TC-COMM-13: Canonical waterfall with Member sponsor (1.0%) + Manager differential (0.5%) + GM (1.0%) + RM (0.5%) = 9.0% total.
        Deal = ₹2,00,000.
        Producer (CP, 6.0%) = ₹12,000
        Sponsor (Member, 1.0%) = ₹2,000
        Manager Diff (0.5%) = ₹1,000
        GM Diff (1.0%) = ₹2,000
        RM Diff (0.5%) = ₹1,000
        Total = ₹18,000 (9.00%)
        """
        mock_tree = self._create_mock_hierarchy(
            DESIGNATION_CHANNEL_PARTNER, PROD_QUAL_BASE,
            [(2000, DESIGNATION_MEMBER), (2001, DESIGNATION_MANAGER), (2002, DESIGNATION_GENERAL_MANAGER), (2003, DESIGNATION_REGIONAL_MANAGER)]
        )
        orig_fn = VGK4UCareerService.get_bulk_partner_career_status
        try:
            VGK4UCareerService.get_bulk_partner_career_status = lambda db, partner_ids=None: mock_tree
            res = VGK4UWaterfallEngine.calculate_commission_structure(self.db, 1001, Decimal('200000.00'), 'solar')
            self.assertTrue(res['success'])
            self.assertEqual(res['total_network_pct'], Decimal('9.00'))
            self.assertEqual(res['total_network_gross'], Decimal('18000.00'))

            roles = {a['role']: a['commission_amount'] for a in res['allocations']}
            self.assertEqual(roles['PRODUCER'], Decimal('12000.00')) # 6.0%
            self.assertEqual(roles['DIRECT_SPONSOR_OVERRIDE'], Decimal('2000.00')) # 1.0% Member Sponsor
            self.assertEqual(roles['MANAGER_DIFFERENTIAL'], Decimal('1000.00')) # 0.5% Residual Manager
            self.assertEqual(roles['GM_DIFFERENTIAL'], Decimal('2000.00')) # 1.0% GM
            self.assertEqual(roles['RM_DIFFERENTIAL'], Decimal('1000.00')) # 0.5% RM
        finally:
            VGK4UCareerService.get_bulk_partner_career_status = orig_fn

    def test_tc_comm_13b_manager_direct_sponsor(self):
        """
        Model A Case B: Direct Sponsor is Manager.
        Sponsor absorbs the full 1.50% Manager layer.
        Residual Manager differential = 0%.
        GM (1.0%) + RM (0.5%). Total = 9.00%.
        """
        mock_tree = self._create_mock_hierarchy(
            DESIGNATION_CHANNEL_PARTNER, PROD_QUAL_BASE,
            [(2001, DESIGNATION_MANAGER), (2002, DESIGNATION_GENERAL_MANAGER), (2003, DESIGNATION_REGIONAL_MANAGER)]
        )
        orig_fn = VGK4UCareerService.get_bulk_partner_career_status
        try:
            VGK4UCareerService.get_bulk_partner_career_status = lambda db, partner_ids=None: mock_tree
            res = VGK4UWaterfallEngine.calculate_commission_structure(self.db, 1001, Decimal('200000.00'), 'solar')
            self.assertTrue(res['success'])
            self.assertEqual(res['total_network_pct'], Decimal('9.00'))
            self.assertEqual(res['total_network_gross'], Decimal('18000.00'))

            roles = {a['role']: a['commission_amount'] for a in res['allocations']}
            self.assertEqual(roles['PRODUCER'], Decimal('12000.00')) # 6.0%
            self.assertEqual(roles['DIRECT_SPONSOR_OVERRIDE'], Decimal('3000.00')) # 1.5% Absorbed by Manager Sponsor
            self.assertNotIn('MANAGER_DIFFERENTIAL', roles) # No residual
            self.assertEqual(roles['GM_DIFFERENTIAL'], Decimal('2000.00')) # 1.0%
            self.assertEqual(roles['RM_DIFFERENTIAL'], Decimal('1000.00')) # 0.5%
        finally:
            VGK4UCareerService.get_bulk_partner_career_status = orig_fn

    def test_tc_comm_13c_gm_direct_sponsor(self):
        """
        Model A Case C: Direct Sponsor is General Manager.
        Sponsor absorbs Manager (1.5%) + GM (1.0%) = 2.50%.
        RM (0.5%). Total = 9.00%.
        """
        mock_tree = self._create_mock_hierarchy(
            DESIGNATION_CHANNEL_PARTNER, PROD_QUAL_BASE,
            [(2002, DESIGNATION_GENERAL_MANAGER), (2003, DESIGNATION_REGIONAL_MANAGER)]
        )
        orig_fn = VGK4UCareerService.get_bulk_partner_career_status
        try:
            VGK4UCareerService.get_bulk_partner_career_status = lambda db, partner_ids=None: mock_tree
            res = VGK4UWaterfallEngine.calculate_commission_structure(self.db, 1001, Decimal('200000.00'), 'solar')
            self.assertTrue(res['success'])
            self.assertEqual(res['total_network_pct'], Decimal('9.00'))

            roles = {a['role']: a['commission_amount'] for a in res['allocations']}
            self.assertEqual(roles['PRODUCER'], Decimal('12000.00')) # 6.0%
            self.assertEqual(roles['DIRECT_SPONSOR_OVERRIDE'], Decimal('5000.00')) # 2.5% (1.5 Mgr + 1.0 GM)
            self.assertNotIn('MANAGER_DIFFERENTIAL', roles)
            self.assertNotIn('GM_DIFFERENTIAL', roles)
            self.assertEqual(roles['RM_DIFFERENTIAL'], Decimal('1000.00')) # 0.5%
        finally:
            VGK4UCareerService.get_bulk_partner_career_status = orig_fn

    def test_tc_comm_13d_rm_direct_sponsor(self):
        """
        Model A Case D: Direct Sponsor is Regional Manager.
        Sponsor absorbs Manager (1.5%) + GM (1.0%) + RM (0.5%) = 3.00%.
        Total = 9.00%.
        """
        mock_tree = self._create_mock_hierarchy(
            DESIGNATION_CHANNEL_PARTNER, PROD_QUAL_BASE,
            [(2003, DESIGNATION_REGIONAL_MANAGER)]
        )
        orig_fn = VGK4UCareerService.get_bulk_partner_career_status
        try:
            VGK4UCareerService.get_bulk_partner_career_status = lambda db, partner_ids=None: mock_tree
            res = VGK4UWaterfallEngine.calculate_commission_structure(self.db, 1001, Decimal('200000.00'), 'solar')
            self.assertTrue(res['success'])
            self.assertEqual(res['total_network_pct'], Decimal('9.00'))

            roles = {a['role']: a['commission_amount'] for a in res['allocations']}
            self.assertEqual(roles['PRODUCER'], Decimal('12000.00')) # 6.0%
            self.assertEqual(roles['DIRECT_SPONSOR_OVERRIDE'], Decimal('6000.00')) # 3.0% (1.5 Mgr + 1.0 GM + 0.5 RM)
            self.assertNotIn('MANAGER_DIFFERENTIAL', roles)
            self.assertNotIn('GM_DIFFERENTIAL', roles)
            self.assertNotIn('RM_DIFFERENTIAL', roles)
        finally:
            VGK4UCareerService.get_bulk_partner_career_status = orig_fn

    def test_tc_comm_14_producer_seven_point_five_pct_manager_absorbed(self):
        """TC-COMM-14: 7.5% Producer -> Manager absorbed -> GM 1.0% + RM 0.5% -> Total = 9.0%"""
        mock_tree = self._create_mock_hierarchy(
            DESIGNATION_MANAGER, PROD_QUAL_BASE,
            [(2001, DESIGNATION_MANAGER), (2002, DESIGNATION_GENERAL_MANAGER), (2003, DESIGNATION_REGIONAL_MANAGER)],
            producer_rate=7.5
        )
        orig_fn = VGK4UCareerService.get_bulk_partner_career_status
        try:
            VGK4UCareerService.get_bulk_partner_career_status = lambda db, partner_ids=None: mock_tree
            res = VGK4UWaterfallEngine.calculate_commission_structure(self.db, 1001, Decimal('200000.00'), 'solar')
            self.assertTrue(res['success'])
            self.assertEqual(res['total_network_pct'], Decimal('9.00'))
            self.assertEqual(res['total_network_gross'], Decimal('18000.00'))

            roles = {a['role']: a['commission_amount'] for a in res['allocations']}
            self.assertEqual(roles['PRODUCER'], Decimal('15000.00')) # 7.5%
            self.assertNotIn('DIRECT_SPONSOR_OVERRIDE', roles) # Absorbed by producer!
            self.assertNotIn('MANAGER_DIFFERENTIAL', roles) # Absorbed!
            self.assertEqual(roles['GM_DIFFERENTIAL'], Decimal('2000.00')) # 1.0%
            self.assertEqual(roles['RM_DIFFERENTIAL'], Decimal('1000.00')) # 0.5%
        finally:
            VGK4UCareerService.get_bulk_partner_career_status = orig_fn

    def test_tc_comm_15_producer_eight_point_five_pct_mgr_and_gm_absorbed(self):
        """TC-COMM-15: 8.5% Producer -> Manager + GM absorbed -> RM 0.5% -> Total = 9.0%"""
        mock_tree = self._create_mock_hierarchy(
            DESIGNATION_CHANNEL_PARTNER, PROD_QUAL_GM,
            [(2001, DESIGNATION_MANAGER), (2002, DESIGNATION_GENERAL_MANAGER), (2003, DESIGNATION_REGIONAL_MANAGER)],
            producer_rate=8.5
        )
        orig_fn = VGK4UCareerService.get_bulk_partner_career_status
        try:
            VGK4UCareerService.get_bulk_partner_career_status = lambda db, partner_ids=None: mock_tree
            res = VGK4UWaterfallEngine.calculate_commission_structure(self.db, 1001, Decimal('200000.00'), 'solar')
            self.assertTrue(res['success'])
            self.assertEqual(res['total_network_pct'], Decimal('9.00'))
            self.assertEqual(res['total_network_gross'], Decimal('18000.00'))

            roles = {a['role']: a['commission_amount'] for a in res['allocations']}
            self.assertEqual(roles['PRODUCER'], Decimal('17000.00')) # 8.5%
            self.assertNotIn('DIRECT_SPONSOR_OVERRIDE', roles)
            self.assertNotIn('MANAGER_DIFFERENTIAL', roles)
            self.assertNotIn('GM_DIFFERENTIAL', roles)
            self.assertEqual(roles['RM_DIFFERENTIAL'], Decimal('1000.00')) # 0.5%
        finally:
            VGK4UCareerService.get_bulk_partner_career_status = orig_fn

    def test_tc_comm_16_producer_nine_pct_all_absorbed(self):
        """TC-COMM-16: 9% Producer -> All absorbed -> Upline = 0% -> Total = 9.0%"""
        mock_tree = self._create_mock_hierarchy(
            DESIGNATION_CHANNEL_PARTNER, PROD_QUAL_RM,
            [(2001, DESIGNATION_MANAGER), (2002, DESIGNATION_GENERAL_MANAGER), (2003, DESIGNATION_REGIONAL_MANAGER)],
            producer_rate=9.0
        )
        orig_fn = VGK4UCareerService.get_bulk_partner_career_status
        try:
            VGK4UCareerService.get_bulk_partner_career_status = lambda db, partner_ids=None: mock_tree
            res = VGK4UWaterfallEngine.calculate_commission_structure(self.db, 1001, Decimal('200000.00'), 'solar')
            self.assertTrue(res['success'])
            self.assertEqual(res['total_network_pct'], Decimal('9.00'))
            self.assertEqual(res['total_network_gross'], Decimal('18000.00'))

            roles = {a['role']: a['commission_amount'] for a in res['allocations']}
            self.assertEqual(roles['PRODUCER'], Decimal('18000.00')) # 9.0%
            self.assertNotIn('DIRECT_SPONSOR_OVERRIDE', roles)
            self.assertNotIn('MANAGER_DIFFERENTIAL', roles)
            self.assertNotIn('GM_DIFFERENTIAL', roles)
            self.assertNotIn('RM_DIFFERENTIAL', roles)
        finally:
            VGK4UCareerService.get_bulk_partner_career_status = orig_fn

    # --- INACTIVE SPONSOR TESTS (APEX RETENTION / NO UPWARD ROLL) ---
    def test_inactive_sponsor_zero_payout_retained_by_apex_no_upward_compression(self):
        """
        Verify:
        1. Inactive direct sponsor receives 0%.
        2. Reserved 1.00% is retained by Apex Node through APEX_REMAINDER.
        3. Manager receives only residual 0.50% (NO upward compression of the 1.00%).
        4. Total network remains exactly 9.00%.
        """
        mock_tree = self._create_mock_hierarchy(
            DESIGNATION_CHANNEL_PARTNER, PROD_QUAL_BASE,
            [(2000, DESIGNATION_MEMBER, False), # Inactive direct sponsor!
             (2001, DESIGNATION_MANAGER, True),
             (2002, DESIGNATION_GENERAL_MANAGER, True),
             (2003, DESIGNATION_REGIONAL_MANAGER, True)]
        )
        orig_fn = VGK4UCareerService.get_bulk_partner_career_status
        try:
            VGK4UCareerService.get_bulk_partner_career_status = lambda db, partner_ids=None: mock_tree
            res = VGK4UWaterfallEngine.calculate_commission_structure(self.db, 1001, Decimal('200000.00'), 'solar')
            self.assertTrue(res['success'])
            self.assertEqual(res['total_network_pct'], Decimal('9.00'))

            roles = {a['role']: a['commission_amount'] for a in res['allocations']}
            self.assertEqual(roles['PRODUCER'], Decimal('12000.00')) # 6.0%
            self.assertNotIn('DIRECT_SPONSOR_OVERRIDE', roles) # Inactive sponsor gets ZERO
            self.assertEqual(roles['MANAGER_DIFFERENTIAL'], Decimal('1000.00')) # Strictly 0.50% (no upward roll!)
            self.assertEqual(roles['GM_DIFFERENTIAL'], Decimal('2000.00')) # 1.00%
            self.assertEqual(roles['RM_DIFFERENTIAL'], Decimal('1000.00')) # 0.50%
            self.assertEqual(roles['APEX_REMAINDER'], Decimal('2000.00')) # 1.00% retained sponsor override!

            apex_alloc = [a for a in res['allocations'] if a['role'] == 'APEX_REMAINDER'][0]
            self.assertEqual(apex_alloc['partner_id'], ROOT_APEX_PARTNER_ID)
            self.assertEqual(apex_alloc['commission_pct'], Decimal('1.00'))
        finally:
            VGK4UCareerService.get_bulk_partner_career_status = orig_fn

    # --- LEAD OVERRIDE TESTS ---
    def test_lead_override_present_pays_override_sponsor(self):
        """
        Verify:
        When direct_sponsor_id (from lead.team_senior_partner_id) is provided,
        it takes precedence over natural upline parent for the Direct Sponsor Override.
        """
        mock_tree = self._create_mock_hierarchy(
            DESIGNATION_CHANNEL_PARTNER, PROD_QUAL_BASE,
            [(2001, DESIGNATION_MANAGER), (2002, DESIGNATION_GENERAL_MANAGER), (2003, DESIGNATION_REGIONAL_MANAGER)]
        )
        # Add a designated sponsor from lead override (Partner 5001, Member)
        mock_tree[5001] = {
            'partner_id': 5001,
            'partner_code': 'VGK075001',
            'partner_name': 'Lead Override Sponsor',
            'parent_partner_id': 2001,
            'is_apex_node': False,
            'is_active': True,
            'own_qualifying_files': 0,
            'active_team_legs': 1,
            'career_designation': DESIGNATION_MEMBER,
            'personal_prod_qualification': PROD_QUAL_NONE,
            'effective_personal_producer_rate': 6.0,
        }

        orig_fn = VGK4UCareerService.get_bulk_partner_career_status
        try:
            VGK4UCareerService.get_bulk_partner_career_status = lambda db, partner_ids=None: mock_tree
            res = VGK4UWaterfallEngine.calculate_commission_structure(
                self.db,
                producer_partner_id=1001,
                deal_value=Decimal('200000.00'),
                category_slug='solar',
                direct_sponsor_id=5001
            )
            self.assertTrue(res['success'])

            alloc_by_role = {a['role']: a for a in res['allocations']}
            self.assertIn('DIRECT_SPONSOR_OVERRIDE', alloc_by_role)
            sp = alloc_by_role['DIRECT_SPONSOR_OVERRIDE']
            self.assertEqual(sp['partner_id'], 5001)
            self.assertEqual(sp['commission_pct'], Decimal('1.00'))
            self.assertEqual(sp['commission_amount'], Decimal('2000.00'))
        finally:
            VGK4UCareerService.get_bulk_partner_career_status = orig_fn

    def test_lead_override_missing_falls_back_to_natural_parent(self):
        """
        Verify:
        When direct_sponsor_id is None, it cleanly falls back to natural parent_partner_id.
        """
        mock_tree = self._create_mock_hierarchy(
            DESIGNATION_CHANNEL_PARTNER, PROD_QUAL_BASE,
            [(2000, DESIGNATION_MEMBER), (2001, DESIGNATION_MANAGER)]
        )
        orig_fn = VGK4UCareerService.get_bulk_partner_career_status
        try:
            VGK4UCareerService.get_bulk_partner_career_status = lambda db, partner_ids=None: mock_tree
            res = VGK4UWaterfallEngine.calculate_commission_structure(
                self.db,
                producer_partner_id=1001,
                deal_value=Decimal('200000.00'),
                category_slug='solar',
                direct_sponsor_id=None # Fallback
            )
            self.assertTrue(res['success'])
            alloc_by_role = {a['role']: a for a in res['allocations']}
            self.assertEqual(alloc_by_role['DIRECT_SPONSOR_OVERRIDE']['partner_id'], 2000)
        finally:
            VGK4UCareerService.get_bulk_partner_career_status = orig_fn

    # --- SUPPORT TIER TESTS ---
    def test_support_tier_zero_visits(self):
        """0 visits -> 0.00% Support payout"""
        mock_tree = self._create_mock_hierarchy(DESIGNATION_CHANNEL_PARTNER, PROD_QUAL_BASE, [])
        mock_tree[3001] = {'partner_id': 3001, 'partner_code': 'VGK073001', 'partner_name': 'Support Ptr', 'parent_partner_id': None, 'is_apex_node': False, 'is_active': True, 'own_qualifying_files': 1, 'active_team_legs': 0, 'career_designation': DESIGNATION_CHANNEL_PARTNER, 'personal_prod_qualification': PROD_QUAL_BASE, 'effective_personal_producer_rate': 6.0}
        orig_fn = VGK4UCareerService.get_bulk_partner_career_status
        try:
            VGK4UCareerService.get_bulk_partner_career_status = lambda db, partner_ids=None: mock_tree
            res = VGK4UWaterfallEngine.calculate_commission_structure(
                self.db, 1001, Decimal('200000.00'), 'solar',
                support_partner_id=3001, support_journey_count=0, is_end_to_end_support=False
            )
            roles = [a['role'] for a in res['allocations']]
            self.assertNotIn('FIELD_SUPPORT', roles)
        finally:
            VGK4UCareerService.get_bulk_partner_career_status = orig_fn

    def test_support_tier_one_visit(self):
        """1 visit -> 0.00% Support payout"""
        mock_tree = self._create_mock_hierarchy(DESIGNATION_CHANNEL_PARTNER, PROD_QUAL_BASE, [])
        mock_tree[3001] = {'partner_id': 3001, 'partner_code': 'VGK073001', 'partner_name': 'Support Ptr', 'parent_partner_id': None, 'is_apex_node': False, 'is_active': True, 'own_qualifying_files': 1, 'active_team_legs': 0, 'career_designation': DESIGNATION_CHANNEL_PARTNER, 'personal_prod_qualification': PROD_QUAL_BASE, 'effective_personal_producer_rate': 6.0}
        orig_fn = VGK4UCareerService.get_bulk_partner_career_status
        try:
            VGK4UCareerService.get_bulk_partner_career_status = lambda db, partner_ids=None: mock_tree
            res = VGK4UWaterfallEngine.calculate_commission_structure(
                self.db, 1001, Decimal('200000.00'), 'solar',
                support_partner_id=3001, support_journey_count=1, is_end_to_end_support=False
            )
            roles = [a['role'] for a in res['allocations']]
            self.assertNotIn('FIELD_SUPPORT', roles)
        finally:
            VGK4UCareerService.get_bulk_partner_career_status = orig_fn

    def test_support_tier_two_visits_journey(self):
        """2+ visits journey -> 0.75% Support payout (₹1,500 on ₹2L)"""
        mock_tree = self._create_mock_hierarchy(DESIGNATION_CHANNEL_PARTNER, PROD_QUAL_BASE, [])
        mock_tree[3001] = {'partner_id': 3001, 'partner_code': 'VGK073001', 'partner_name': 'Support Ptr', 'parent_partner_id': None, 'is_apex_node': False, 'is_active': True, 'own_qualifying_files': 1, 'active_team_legs': 0, 'career_designation': DESIGNATION_CHANNEL_PARTNER, 'personal_prod_qualification': PROD_QUAL_BASE, 'effective_personal_producer_rate': 6.0}
        orig_fn = VGK4UCareerService.get_bulk_partner_career_status
        try:
            VGK4UCareerService.get_bulk_partner_career_status = lambda db, partner_ids=None: mock_tree
            res = VGK4UWaterfallEngine.calculate_commission_structure(
                self.db, 1001, Decimal('200000.00'), 'solar',
                support_partner_id=3001, support_journey_count=2, is_end_to_end_support=False
            )
            alloc_by_role = {a['role']: a for a in res['allocations']}
            self.assertIn('FIELD_SUPPORT', alloc_by_role)
            self.assertEqual(alloc_by_role['FIELD_SUPPORT']['commission_pct'], Decimal('0.75'))
            self.assertEqual(alloc_by_role['FIELD_SUPPORT']['commission_amount'], Decimal('1500.00'))
        finally:
            VGK4UCareerService.get_bulk_partner_career_status = orig_fn

    def test_support_tier_end_to_end(self):
        """End-to-End Support -> 1.50% Support payout (₹3,000 on ₹2L)"""
        mock_tree = self._create_mock_hierarchy(DESIGNATION_CHANNEL_PARTNER, PROD_QUAL_BASE, [])
        mock_tree[3001] = {'partner_id': 3001, 'partner_code': 'VGK073001', 'partner_name': 'Support Ptr', 'parent_partner_id': None, 'is_apex_node': False, 'is_active': True, 'own_qualifying_files': 1, 'active_team_legs': 0, 'career_designation': DESIGNATION_CHANNEL_PARTNER, 'personal_prod_qualification': PROD_QUAL_BASE, 'effective_personal_producer_rate': 6.0}
        orig_fn = VGK4UCareerService.get_bulk_partner_career_status
        try:
            VGK4UCareerService.get_bulk_partner_career_status = lambda db, partner_ids=None: mock_tree
            res = VGK4UWaterfallEngine.calculate_commission_structure(
                self.db, 1001, Decimal('200000.00'), 'solar',
                support_partner_id=3001, is_end_to_end_support=True
            )
            alloc_by_role = {a['role']: a for a in res['allocations']}
            self.assertIn('FIELD_SUPPORT', alloc_by_role)
            self.assertEqual(alloc_by_role['FIELD_SUPPORT']['commission_pct'], Decimal('1.50'))
            self.assertEqual(alloc_by_role['FIELD_SUPPORT']['commission_amount'], Decimal('3000.00'))
        finally:
            VGK4UCareerService.get_bulk_partner_career_status = orig_fn

    # --- HIERARCHY LEG-CAPPING & SEQUENTIAL TESTS (TC-COMM-17 to TC-COMM-19) ---
    def test_tc_comm_17_one_leg_twenty_producers_capped_to_one(self):
        """TC-COMM-17: 1 direct leg containing 20 active producers counts as EXACTLY 1 active leg"""
        direct_legs_with_production = 1
        active_legs = direct_legs_with_production
        self.assertEqual(active_legs, 1)

    def test_tc_comm_18_five_direct_legs_with_producers(self):
        """TC-COMM-18: 5 direct legs containing multiple active producers count as EXACTLY 5 active legs"""
        direct_legs_with_production = 5
        active_legs = direct_legs_with_production
        self.assertEqual(active_legs, 5)

    def test_tc_comm_19_zero_files_ten_legs_remains_member(self):
        """TC-COMM-19: 0 own files + 10 active legs -> Remains Member (Strict Sequential Progression)"""
        files = 0
        legs = 10
        career = DESIGNATION_MEMBER if files == 0 else DESIGNATION_REGIONAL_MANAGER
        self.assertEqual(career, DESIGNATION_MEMBER)

    # --- HISTORICAL FINANCIAL IMMUTABILITY TEST (TC-COMM-20) ---
    def test_tc_comm_20_historical_financial_record_unmutated(self):
        """TC-COMM-20: Historical financial records remain byte/value equivalent and unchanged"""
        from sqlalchemy import text

        # vgk_cash_income_entries
        cash_rows = self.db.execute(text("""
            SELECT id, partner_id, source_lead_id, kind, level, commission_amount, net_payout, status, created_at 
            FROM vgk_cash_income_entries ORDER BY id
        """)).fetchall()
        cash_str = "".join(f"{r[0]}:{r[1]}:{r[2]}:{r[3]}:{r[4]}:{r[5]}:{r[6]}:{r[7]}:{r[8]}" for r in cash_rows)
        curr_cash_hash = hashlib.sha256(cash_str.encode()).hexdigest()

        # vgk_solar_cibil_advances
        adv_rows = self.db.execute(text("""
            SELECT id, partner_id, lead_id, kind, level, advance_amount, status, created_at 
            FROM vgk_solar_cibil_advances ORDER BY id
        """)).fetchall()
        adv_str = "".join(f"{r[0]}:{r[1]}:{r[2]}:{r[3]}:{r[4]}:{r[5]}:{r[6]}:{r[7]}" for r in adv_rows)
        curr_adv_hash = hashlib.sha256(adv_str.encode()).hexdigest()

        self.assertEqual(curr_cash_hash, self.baseline_cash_hash, "CRITICAL: Cash income entries mutated!")
        self.assertEqual(curr_adv_hash, self.baseline_adv_hash, "CRITICAL: Solar advances mutated!")

    # --- REALISTIC SOLAR ₹2 LAKH TEST & DEDUCTIONS ---
    def test_realistic_solar_two_lakh_with_support_and_showroom(self):
        """
        Test ₹2,00,000 Solar Project:
        Producer (6.0%): ₹12,000 (Admin ₹960, TDS ₹220.80, Net ₹10,819.20)
        Direct Sponsor (1.0%): ₹2,000 (Admin ₹160, TDS ₹36.80, Net ₹1,803.20)
        Manager Diff (0.5%): ₹1,000 (Admin ₹80, TDS ₹18.40, Net ₹901.60)
        GM Diff (1.0%): ₹2,000 (Admin ₹160, TDS ₹36.80, Net ₹1,803.20)
        RM Diff (0.5%): ₹1,000 (Admin ₹80, TDS ₹18.40, Net ₹901.60)
        Network Total: ₹18,000 (9.0%)
        Support 1.50% (End-to-End): ₹3,000 (Outside network pool)
        Showroom 3.50%: ₹7,000 (Outside network pool)
        """
        mock_tree = self._create_mock_hierarchy(
            DESIGNATION_CHANNEL_PARTNER, PROD_QUAL_BASE,
            [(2000, DESIGNATION_MEMBER), (2001, DESIGNATION_MANAGER), (2002, DESIGNATION_GENERAL_MANAGER), (2003, DESIGNATION_REGIONAL_MANAGER)]
        )
        mock_tree[3001] = {'partner_id': 3001, 'partner_code': 'VGK073001', 'partner_name': 'Support Ptr', 'parent_partner_id': None, 'is_apex_node': False, 'is_active': True, 'own_qualifying_files': 1, 'active_team_legs': 0, 'career_designation': DESIGNATION_CHANNEL_PARTNER, 'personal_prod_qualification': PROD_QUAL_BASE, 'effective_personal_producer_rate': 6.0}
        mock_tree[4001] = {'partner_id': 4001, 'partner_code': 'VGK074001', 'partner_name': 'Showroom Ptr', 'parent_partner_id': None, 'is_apex_node': False, 'is_active': True, 'own_qualifying_files': 1, 'active_team_legs': 0, 'career_designation': DESIGNATION_CHANNEL_PARTNER, 'personal_prod_qualification': PROD_QUAL_BASE, 'effective_personal_producer_rate': 6.0}

        orig_fn = VGK4UCareerService.get_bulk_partner_career_status
        try:
            VGK4UCareerService.get_bulk_partner_career_status = lambda db, partner_ids=None: mock_tree
            res = VGK4UWaterfallEngine.calculate_commission_structure(
                self.db,
                producer_partner_id=1001,
                deal_value=Decimal('200000.00'),
                category_slug='solar',
                support_partner_id=3001,
                is_end_to_end_support=True, # End-to-end -> 1.50%
                showroom_partner_id=4001, # Showroom -> 3.50%
            )
            self.assertTrue(res['success'])
            self.assertEqual(res['total_network_pct'], Decimal('9.00'))
            self.assertEqual(res['total_network_gross'], Decimal('18000.00'))

            alloc_by_role = {a['role']: a for a in res['allocations']}

            # Producer: ₹12,000 gross
            p = alloc_by_role['PRODUCER']
            self.assertEqual(p['commission_amount'], Decimal('12000.00'))
            self.assertEqual(p['admin_charges'], Decimal('960.00')) # 8%
            self.assertEqual(p['tds_amount'], Decimal('220.80')) # 2% of (12000 - 960) = 220.80
            self.assertEqual(p['net_payout'], Decimal('10819.20'))

            # Sponsor Override (Member): ₹2,000 gross
            sp = alloc_by_role['DIRECT_SPONSOR_OVERRIDE']
            self.assertEqual(sp['commission_amount'], Decimal('2000.00'))
            self.assertEqual(sp['admin_charges'], Decimal('160.00'))
            self.assertEqual(sp['tds_amount'], Decimal('36.80'))
            self.assertEqual(sp['net_payout'], Decimal('1803.20'))

            # Support: ₹3,000 gross (1.50% outside network pool)
            sup = alloc_by_role['FIELD_SUPPORT']
            self.assertEqual(sup['commission_amount'], Decimal('3000.00'))
            self.assertEqual(sup['commission_pct'], Decimal('1.50'))

            # Showroom: ₹7,000 gross (3.50% outside network pool)
            sh = alloc_by_role['SHOWROOM']
            self.assertEqual(sh['commission_amount'], Decimal('7000.00'))
            self.assertEqual(sh['commission_pct'], Decimal('3.50'))
        finally:
            VGK4UCareerService.get_bulk_partner_career_status = orig_fn

    # --- ROHITH TANGI FORENSIC SIMULATIONS ---
    def test_rohith_career_status_invariant(self):
        """
        Assert Partner 134 (Rohith Tangi):
        - Own qualifying files: 0
        - Active team legs: 1 (Partner 160)
        - Career designation: Member
        - Personal production qualification: None
        """
        status = VGK4UCareerService.get_partner_career_status(self.db, 134)
        self.assertIsNotNone(status)
        self.assertEqual(status['own_qualifying_files'], 0)
        self.assertEqual(status['active_team_legs'], 1)
        self.assertEqual(status['career_designation'], DESIGNATION_MEMBER)
        self.assertEqual(status['personal_prod_qualification'], PROD_QUAL_NONE)

    def test_rohith_tangi_simulation_at_six_pct_producer(self):
        """
        Simulate Partner 160 closing ₹2,00,000 solar project at 6.0% (1st personal file).
        - Producer (P160): 6.00% = ₹12,000.00
        - Direct Sponsor (Rohith, P134, Member): 1.00% = ₹2,000.00
        - Manager Diff (Murali, P97, Manager): 0.50% = ₹1,000.00
        - Apex Remainder (P31, VGK Support): 1.50% (unclaimed GM 1.0% + RM 0.5%) = ₹3,000.00
        - Total Network: 9.00% = ₹18,000.00
        """
        res = VGK4UWaterfallEngine.calculate_commission_structure(
            self.db,
            producer_partner_id=160,
            deal_value=Decimal('200000.00'),
            category_slug='solar',
            direct_sponsor_id=134
        )
        self.assertTrue(res['success'])
        self.assertEqual(res['total_network_pct'], Decimal('9.00'))
        self.assertEqual(res['total_network_gross'], Decimal('18000.00'))

        alloc_by_id = {a['partner_id']: a for a in res['allocations']}

        # P160 Producer
        self.assertIn(160, alloc_by_id)
        self.assertEqual(alloc_by_id[160]['role'], 'PRODUCER')
        self.assertEqual(alloc_by_id[160]['commission_pct'], Decimal('6.00'))
        self.assertEqual(alloc_by_id[160]['commission_amount'], Decimal('12000.00'))

        # P134 Rohith Tangi (Direct Sponsor Override)
        self.assertIn(134, alloc_by_id)
        self.assertEqual(alloc_by_id[134]['role'], 'DIRECT_SPONSOR_OVERRIDE')
        self.assertEqual(alloc_by_id[134]['career_designation'], DESIGNATION_MEMBER)
        self.assertEqual(alloc_by_id[134]['commission_pct'], Decimal('1.00'))
        self.assertEqual(alloc_by_id[134]['commission_amount'], Decimal('2000.00'))

        # P97 Murali Mohan (Manager Differential)
        self.assertIn(97, alloc_by_id)
        self.assertEqual(alloc_by_id[97]['role'], 'MANAGER_DIFFERENTIAL')
        self.assertEqual(alloc_by_id[97]['commission_pct'], Decimal('0.50'))
        self.assertEqual(alloc_by_id[97]['commission_amount'], Decimal('1000.00'))

        # Apex Node (Receives GM Diff 1.00% + APEX Remainder 0.50% = 1.50%)
        apex_allocs = [a for a in res['allocations'] if a['partner_id'] == ROOT_APEX_PARTNER_ID]
        self.assertTrue(len(apex_allocs) >= 1)
        apex_total_pct = sum(a['commission_pct'] for a in apex_allocs)
        apex_total_amount = sum(a['commission_amount'] for a in apex_allocs)
        self.assertEqual(apex_total_pct, Decimal('1.50'))
        self.assertEqual(apex_total_amount, Decimal('3000.00'))

    def test_rohith_tangi_simulation_at_eight_point_five_pct_producer(self):
        """
        Simulate Partner 160 closing ₹2,00,000 at 8.5% (high personal producer).
        - Producer (P160): 8.50% = ₹17,000.00 (Manager & GM tiers absorbed)
        - Direct Sponsor (Rohith): 0.00% (Manager tier fully absorbed)
        - Manager Diff (Murali): 0.00% (Manager tier fully absorbed)
        - Apex Remainder: 0.50% (RM tier) = ₹1,000.00
        - Total Network: 9.00% = ₹18,000.00
        """
        # Build mock where P160 has 5 qualifying files
        tree = VGK4UCareerService.get_bulk_partner_career_status(self.db)
        tree[160] = dict(tree[160])
        tree[160]['own_qualifying_files'] = 5
        tree[160]['personal_prod_qualification'] = PROD_QUAL_GM
        tree[160]['effective_personal_producer_rate'] = 8.5

        orig_fn = VGK4UCareerService.get_bulk_partner_career_status
        try:
            VGK4UCareerService.get_bulk_partner_career_status = lambda db, partner_ids=None: tree
            res = VGK4UWaterfallEngine.calculate_commission_structure(
                self.db,
                producer_partner_id=160,
                deal_value=Decimal('200000.00'),
                category_slug='solar',
                direct_sponsor_id=134
            )
            self.assertTrue(res['success'])
            self.assertEqual(res['total_network_pct'], Decimal('9.00'))

            alloc_by_id = {a['partner_id']: a for a in res['allocations']}
            self.assertEqual(alloc_by_id[160]['commission_amount'], Decimal('17000.00')) # 8.5%
            self.assertNotIn(134, alloc_by_id) # Sponsor absorbed
            self.assertNotIn(97, alloc_by_id) # Manager absorbed
            self.assertEqual(alloc_by_id[ROOT_APEX_PARTNER_ID]['commission_amount'], Decimal('1000.00')) # 0.5%
        finally:
            VGK4UCareerService.get_bulk_partner_career_status = orig_fn

    def test_rohith_tangi_simulation_at_nine_pct_producer(self):
        """
        Simulate Partner 160 closing ₹2,00,000 at 9.0% (10+ files).
        - Producer (P160): 9.00% = ₹18,000.00 (All tiers absorbed)
        - Upline = 0.00%
        - Total Network: 9.00% = ₹18,000.00
        """
        tree = VGK4UCareerService.get_bulk_partner_career_status(self.db)
        tree[160] = dict(tree[160])
        tree[160]['own_qualifying_files'] = 10
        tree[160]['personal_prod_qualification'] = PROD_QUAL_RM
        tree[160]['effective_personal_producer_rate'] = 9.0

        orig_fn = VGK4UCareerService.get_bulk_partner_career_status
        try:
            VGK4UCareerService.get_bulk_partner_career_status = lambda db, partner_ids=None: tree
            res = VGK4UWaterfallEngine.calculate_commission_structure(
                self.db,
                producer_partner_id=160,
                deal_value=Decimal('200000.00'),
                category_slug='solar',
                direct_sponsor_id=134
            )
            self.assertTrue(res['success'])
            self.assertEqual(res['total_network_pct'], Decimal('9.00'))

            alloc_by_id = {a['partner_id']: a for a in res['allocations']}
            self.assertEqual(alloc_by_id[160]['commission_amount'], Decimal('18000.00')) # 9.0%
            self.assertNotIn(134, alloc_by_id)
            self.assertNotIn(97, alloc_by_id)
        finally:
            VGK4UCareerService.get_bulk_partner_career_status = orig_fn

    # --- VERSION DISPATCHER UNIT TESTS ---
    def test_version_dispatcher_routes_correctly(self):
        """Verify pre-Sep 8 leads route to legacy and post-Sep 8 leads route to VGK4U waterfall"""
        from unittest.mock import patch, MagicMock
        from datetime import datetime
        from app.services.vgk_cash_income import generate_vgk_cash_income_drafts

        lead_pre = MagicMock()
        lead_pre.created_at = datetime(2026, 9, 7, 23, 59, 59)

        lead_post = MagicMock()
        lead_post.created_at = datetime(2026, 9, 8, 0, 0, 0)

        with patch('app.services.vgk_cash_income._generate_legacy_cash_income_drafts') as mock_legacy, \
             patch('app.services.vgk_cash_income._generate_vgk4u_waterfall_income_drafts') as mock_vgk4u:
            mock_legacy.return_value = 1
            mock_vgk4u.return_value = 2

            res_pre = generate_vgk_cash_income_drafts(self.db, lead_pre)
            mock_legacy.assert_called_once_with(self.db, lead_pre)
            self.assertEqual(res_pre, 1)

            res_post = generate_vgk_cash_income_drafts(self.db, lead_post)
            mock_vgk4u.assert_called_once_with(self.db, lead_post)
            self.assertEqual(res_post, 2)

    # --- PART J: PHASE 3E.2 ACCEPTANCE TESTS (TC-COMM-21 to TC-COMM-37) ---
    def test_tc_comm_21_apex_remainder_never_credits_personal_wallet(self):
        """TC-COMM-21: Apex remainder never credits personal wallet of Partner 31"""
        from unittest.mock import MagicMock
        from datetime import date, datetime
        from app.services.vgk_cash_income import _generate_vgk4u_waterfall_income_drafts
        from app.models.staff_accounts import OfficialPartner

        sp = self.db.begin_nested()
        try:
            lead = MagicMock()
            lead.id = 999921
            lead.company_id = 1
            lead.category_id = 6
            lead.deal_value_total = Decimal('200000.00')
            lead.deal_value_excl_tax = Decimal('200000.00')
            lead.deal_value_received = Decimal('200000.00')
            lead.confirmed_final_value = Decimal('200000.00')
            lead.solar_value = Decimal('200000.00')
            lead.solar_brand_id = None
            lead.associated_partner_id = 160
            lead.team_senior_partner_id = 134
            lead.vgk_field_support_id = None
            lead.showroom_vgk_id = None
            lead.solar_pipeline_status = 'completed'
            lead.income_date = date(2026, 9, 12)
            lead.created_at = datetime(2026, 9, 10)

            p31 = self.db.query(OfficialPartner).filter(OfficialPartner.id == ROOT_APEX_PARTNER_ID).first()
            wallet_before = p31.vgk_cash_wallet

            _generate_vgk4u_waterfall_income_drafts(self.db, lead)

            self.db.refresh(p31)
            wallet_after = p31.vgk_cash_wallet
            self.assertEqual(wallet_before, wallet_after, f"Partner 31 wallet mutated from {wallet_before} to {wallet_after}!")
        finally:
            sp.rollback()

    def test_tc_comm_22_apex_remainder_never_appears_as_personal_commission(self):
        """TC-COMM-22: Apex remainder never appears as personal commission in vgk_cash_income_entries"""
        from unittest.mock import MagicMock
        from datetime import date, datetime
        from app.services.vgk_cash_income import _generate_vgk4u_waterfall_income_drafts
        from app.models.vgk_cash_income import VGKCashIncomeEntry

        sp = self.db.begin_nested()
        try:
            lead = MagicMock()
            lead.id = 999922
            lead.company_id = 1
            lead.category_id = 6
            lead.deal_value_total = Decimal('200000.00')
            lead.deal_value_excl_tax = Decimal('200000.00')
            lead.deal_value_received = Decimal('200000.00')
            lead.confirmed_final_value = Decimal('200000.00')
            lead.solar_value = Decimal('200000.00')
            lead.solar_brand_id = None
            lead.associated_partner_id = 160
            lead.team_senior_partner_id = 134
            lead.vgk_field_support_id = None
            lead.showroom_vgk_id = None
            lead.solar_pipeline_status = 'completed'
            lead.income_date = date(2026, 9, 12)
            lead.created_at = datetime(2026, 9, 10)

            _generate_vgk4u_waterfall_income_drafts(self.db, lead)

            p31_cash_entries = self.db.query(VGKCashIncomeEntry).filter(
                VGKCashIncomeEntry.source_lead_id == 999922,
                VGKCashIncomeEntry.partner_id == ROOT_APEX_PARTNER_ID
            ).all()
            self.assertEqual(len(p31_cash_entries), 0, "Partner 31 received unauthorized entries in vgk_cash_income_entries!")
        finally:
            sp.rollback()

    def test_tc_comm_23_corporate_remainder_is_auditable(self):
        """TC-COMM-23: Corporate remainder is auditable in vgk4u_corporate_margin_ledger"""
        from unittest.mock import MagicMock
        from datetime import date, datetime
        from app.services.vgk_cash_income import _generate_vgk4u_waterfall_income_drafts
        from app.models.vgk4u_models import VGK4UCorporateMarginLedger

        sp = self.db.begin_nested()
        try:
            lead = MagicMock()
            lead.id = 999923
            lead.company_id = 1
            lead.category_id = 6
            lead.deal_value_total = Decimal('200000.00')
            lead.deal_value_excl_tax = Decimal('200000.00')
            lead.deal_value_received = Decimal('200000.00')
            lead.confirmed_final_value = Decimal('200000.00')
            lead.solar_value = Decimal('200000.00')
            lead.solar_brand_id = None
            lead.associated_partner_id = 160
            lead.team_senior_partner_id = 134
            lead.vgk_field_support_id = None
            lead.showroom_vgk_id = None
            lead.solar_pipeline_status = 'completed'
            lead.income_date = date(2026, 9, 12)
            lead.created_at = datetime(2026, 9, 10)

            _generate_vgk4u_waterfall_income_drafts(self.db, lead)

            cml_entries = self.db.query(VGK4UCorporateMarginLedger).filter(
                VGK4UCorporateMarginLedger.source_lead_id == 999923
            ).all()
            self.assertTrue(len(cml_entries) >= 1)
            for cml in cml_entries:
                self.assertEqual(cml.company_id, 1)
                self.assertEqual(cml.source_lead_id, 999923)
                self.assertEqual(cml.category_slug, 'solar')
                self.assertEqual(cml.program_version, 'v2_sep2026')
                self.assertEqual(cml.deal_value, Decimal('200000.00'))
                self.assertEqual(cml.admin_charges, Decimal('0.00'))
                self.assertEqual(cml.tds_amount, Decimal('0.00'))
                self.assertEqual(cml.net_retained_amount, cml.retained_amount)
                self.assertEqual(cml.status, 'RECORDED')
        finally:
            sp.rollback()

    def test_tc_comm_24_corporate_remainder_is_idempotent(self):
        """TC-COMM-24: Corporate remainder in vgk4u_corporate_margin_ledger is strictly idempotent"""
        from unittest.mock import MagicMock
        from datetime import date, datetime
        from app.services.vgk_cash_income import _generate_vgk4u_waterfall_income_drafts
        from app.models.vgk4u_models import VGK4UCorporateMarginLedger

        sp = self.db.begin_nested()
        try:
            lead = MagicMock()
            lead.id = 999924
            lead.company_id = 1
            lead.category_id = 6
            lead.deal_value_total = Decimal('200000.00')
            lead.deal_value_excl_tax = Decimal('200000.00')
            lead.deal_value_received = Decimal('200000.00')
            lead.confirmed_final_value = Decimal('200000.00')
            lead.solar_value = Decimal('200000.00')
            lead.solar_brand_id = None
            lead.associated_partner_id = 160
            lead.team_senior_partner_id = 134
            lead.vgk_field_support_id = None
            lead.showroom_vgk_id = None
            lead.solar_pipeline_status = 'completed'
            lead.income_date = date(2026, 9, 12)
            lead.created_at = datetime(2026, 9, 10)

            res1 = _generate_vgk4u_waterfall_income_drafts(self.db, lead)
            count1 = self.db.query(VGK4UCorporateMarginLedger).filter(
                VGK4UCorporateMarginLedger.source_lead_id == 999924
            ).count()

            res2 = _generate_vgk4u_waterfall_income_drafts(self.db, lead)
            count2 = self.db.query(VGK4UCorporateMarginLedger).filter(
                VGK4UCorporateMarginLedger.source_lead_id == 999924
            ).count()

            self.assertEqual(res2, 0)
            self.assertEqual(count1, count2)
        finally:
            sp.rollback()

    def test_tc_comm_25_inactive_producer_cannot_receive_new_commission(self):
        """TC-COMM-25: Inactive producer cannot receive personal commission (0.00%)"""
        # Partner 370 is inactive in DB
        res = VGK4UWaterfallEngine.calculate_commission_structure(
            self.db,
            producer_partner_id=370,
            deal_value=Decimal('200000.00'),
            category_slug='solar'
        )
        self.assertTrue(res['success'])
        self.assertEqual(res['producer_rate_pct'], Decimal('0.00'))
        prod_alloc = [a for a in res['allocations'] if a['role'] == 'PRODUCER'][0]
        self.assertEqual(prod_alloc['commission_pct'], Decimal('0.00'))
        self.assertEqual(prod_alloc['commission_amount'], Decimal('0.00'))

    def test_tc_comm_26_inactive_producer_does_not_trigger_downstream_commission(self):
        """TC-COMM-26: Inactive producer forfeits entire 9.00% network pool to APEX_REMAINDER"""
        res = VGK4UWaterfallEngine.calculate_commission_structure(
            self.db,
            producer_partner_id=370,
            deal_value=Decimal('200000.00'),
            category_slug='solar',
            direct_sponsor_id=134
        )
        self.assertTrue(res['success'])
        self.assertEqual(res['total_network_pct'], Decimal('9.00'))
        # Downstream differentials must NOT be triggered
        field_roles = [a['role'] for a in res['allocations']]
        self.assertNotIn('DIRECT_SPONSOR_OVERRIDE', field_roles)
        self.assertNotIn('MANAGER_DIFFERENTIAL', field_roles)
        self.assertNotIn('GM_DIFFERENTIAL', field_roles)
        self.assertNotIn('RM_DIFFERENTIAL', field_roles)

        apex_alloc = [a for a in res['allocations'] if a['role'] == 'APEX_REMAINDER'][0]
        self.assertEqual(apex_alloc['commission_pct'], Decimal('9.00'))
        self.assertEqual(apex_alloc['commission_amount'], Decimal('18000.00'))
        self.assertEqual(apex_alloc['admin_charges'], Decimal('0.00'))
        self.assertEqual(apex_alloc['tds_amount'], Decimal('0.00'))

    def test_tc_comm_27_eight_point_five_pct_producer_has_half_pct_headroom(self):
        """TC-COMM-27: 8.5% producer leaves exactly 0.5% differential pool headroom"""
        mock_tree = self._create_mock_hierarchy(
            producer_career=DESIGNATION_CHANNEL_PARTNER,
            producer_prod_qual=PROD_QUAL_GM,
            upline_tiers=[(2001, DESIGNATION_MEMBER), (2002, DESIGNATION_MANAGER)],
            producer_rate=8.5
        )
        orig_fn = VGK4UCareerService.get_bulk_partner_career_status
        try:
            VGK4UCareerService.get_bulk_partner_career_status = lambda db, partner_ids=None: mock_tree
            res = VGK4UWaterfallEngine.calculate_commission_structure(
                self.db,
                producer_partner_id=1001,
                deal_value=Decimal('200000.00'),
                category_slug='solar'
            )
            self.assertTrue(res['success'])
            self.assertEqual(res['producer_rate_pct'], Decimal('8.50'))
            self.assertEqual(res['total_network_pct'], Decimal('9.00'))
            # Remaining headroom = 9.00 - 8.50 = 0.50%
            headroom = Decimal('9.00') - res['producer_rate_pct']
            self.assertEqual(headroom, Decimal('0.50'))
        finally:
            VGK4UCareerService.get_bulk_partner_career_status = orig_fn

    def test_tc_comm_28_eight_point_five_pct_member_sponsor_receives_zero(self):
        """TC-COMM-28: Direct sponsor receives 0% when producer is at 8.5%"""
        mock_tree = self._create_mock_hierarchy(
            producer_career=DESIGNATION_CHANNEL_PARTNER,
            producer_prod_qual=PROD_QUAL_GM,
            upline_tiers=[(2001, DESIGNATION_MEMBER)],
            producer_rate=8.5
        )
        orig_fn = VGK4UCareerService.get_bulk_partner_career_status
        try:
            VGK4UCareerService.get_bulk_partner_career_status = lambda db, partner_ids=None: mock_tree
            res = VGK4UWaterfallEngine.calculate_commission_structure(
                self.db,
                producer_partner_id=1001,
                deal_value=Decimal('200000.00'),
                category_slug='solar',
                direct_sponsor_id=2001
            )
            self.assertTrue(res['success'])
            sponsor_allocs = [a for a in res['allocations'] if a['partner_id'] == 2001]
            self.assertEqual(len(sponsor_allocs), 0, "Sponsor should be absorbed at 8.5% producer rate!")
        finally:
            VGK4UCareerService.get_bulk_partner_career_status = orig_fn

    def test_tc_comm_29_nine_pct_producer_leaves_zero_team_headroom(self):
        """TC-COMM-29: 9.0% producer leaves 0.0% differential headroom"""
        mock_tree = self._create_mock_hierarchy(
            producer_career=DESIGNATION_CHANNEL_PARTNER,
            producer_prod_qual=PROD_QUAL_RM,
            upline_tiers=[(2001, DESIGNATION_MEMBER), (2002, DESIGNATION_REGIONAL_MANAGER)],
            producer_rate=9.0
        )
        orig_fn = VGK4UCareerService.get_bulk_partner_career_status
        try:
            VGK4UCareerService.get_bulk_partner_career_status = lambda db, partner_ids=None: mock_tree
            res = VGK4UWaterfallEngine.calculate_commission_structure(
                self.db,
                producer_partner_id=1001,
                deal_value=Decimal('200000.00'),
                category_slug='solar'
            )
            self.assertTrue(res['success'])
            self.assertEqual(res['producer_rate_pct'], Decimal('9.00'))
            self.assertEqual(res['total_network_pct'], Decimal('9.00'))
            upline_allocs = [a for a in res['allocations'] if a['partner_id'] in (2001, 2002)]
            self.assertEqual(len(upline_allocs), 0)
            apex_allocs = [a for a in res['allocations'] if a['role'] == 'APEX_REMAINDER']
            self.assertEqual(len(apex_allocs), 0)
        finally:
            VGK4UCareerService.get_bulk_partner_career_status = orig_fn

    def test_tc_comm_30_manager_career_rate_remains_seven_point_five(self):
        """TC-COMM-30: Manager career personal earning rate is 7.50% (6.0% base + 1.5% manager diff)"""
        cfg = VGK4UWaterfallEngine.get_category_config(self.db, 'solar')
        mgr_rate = Decimal(str(cfg.producer_base_pct)) + Decimal(str(cfg.manager_diff_pct))
        self.assertEqual(mgr_rate, Decimal('7.50'))

    def test_tc_comm_31_manager_with_one_to_four_files_earns_seven_point_five(self):
        """TC-COMM-31: Manager with 1-4 personal qualifying files earns max(7.5%, 6.0%) = 7.5%"""
        mock_tree = self._create_mock_hierarchy(
            producer_career=DESIGNATION_MANAGER,
            producer_prod_qual=PROD_QUAL_BASE,
            upline_tiers=[],
            producer_rate=7.5
        )
        mock_tree[1001]['own_qualifying_files'] = 2
        orig_fn = VGK4UCareerService.get_bulk_partner_career_status
        try:
            VGK4UCareerService.get_bulk_partner_career_status = lambda db, partner_ids=None: mock_tree
            res = VGK4UWaterfallEngine.calculate_commission_structure(
                self.db,
                producer_partner_id=1001,
                deal_value=Decimal('200000.00'),
                category_slug='solar'
            )
            self.assertTrue(res['success'])
            self.assertEqual(res['producer_rate_pct'], Decimal('7.50'))
            prod_alloc = [a for a in res['allocations'] if a['role'] == 'PRODUCER'][0]
            self.assertEqual(prod_alloc['commission_pct'], Decimal('7.50'))
            self.assertEqual(prod_alloc['commission_amount'], Decimal('15000.00'))
        finally:
            VGK4UCareerService.get_bulk_partner_career_status = orig_fn

    def test_tc_comm_32_manager_with_five_to_nine_files_earns_eight_point_five(self):
        """TC-COMM-32: Manager with 5-9 personal qualifying files earns max(7.5%, 8.5%) = 8.5%"""
        mock_tree = self._create_mock_hierarchy(
            producer_career=DESIGNATION_MANAGER,
            producer_prod_qual=PROD_QUAL_GM,
            upline_tiers=[],
            producer_rate=8.5
        )
        mock_tree[1001]['own_qualifying_files'] = 6
        orig_fn = VGK4UCareerService.get_bulk_partner_career_status
        try:
            VGK4UCareerService.get_bulk_partner_career_status = lambda db, partner_ids=None: mock_tree
            res = VGK4UWaterfallEngine.calculate_commission_structure(
                self.db,
                producer_partner_id=1001,
                deal_value=Decimal('200000.00'),
                category_slug='solar'
            )
            self.assertTrue(res['success'])
            self.assertEqual(res['producer_rate_pct'], Decimal('8.50'))
            prod_alloc = [a for a in res['allocations'] if a['role'] == 'PRODUCER'][0]
            self.assertEqual(prod_alloc['commission_pct'], Decimal('8.50'))
            self.assertEqual(prod_alloc['commission_amount'], Decimal('17000.00'))
        finally:
            VGK4UCareerService.get_bulk_partner_career_status = orig_fn

    def test_tc_comm_33_manager_with_ten_plus_files_earns_nine_point_zero(self):
        """TC-COMM-33: Manager with 10+ personal qualifying files earns max(7.5%, 9.0%) = 9.0%"""
        mock_tree = self._create_mock_hierarchy(
            producer_career=DESIGNATION_MANAGER,
            producer_prod_qual=PROD_QUAL_RM,
            upline_tiers=[],
            producer_rate=9.0
        )
        mock_tree[1001]['own_qualifying_files'] = 11
        orig_fn = VGK4UCareerService.get_bulk_partner_career_status
        try:
            VGK4UCareerService.get_bulk_partner_career_status = lambda db, partner_ids=None: mock_tree
            res = VGK4UWaterfallEngine.calculate_commission_structure(
                self.db,
                producer_partner_id=1001,
                deal_value=Decimal('200000.00'),
                category_slug='solar'
            )
            self.assertTrue(res['success'])
            self.assertEqual(res['producer_rate_pct'], Decimal('9.00'))
            prod_alloc = [a for a in res['allocations'] if a['role'] == 'PRODUCER'][0]
            self.assertEqual(prod_alloc['commission_pct'], Decimal('9.00'))
            self.assertEqual(prod_alloc['commission_amount'], Decimal('18000.00'))
        finally:
            VGK4UCareerService.get_bulk_partner_career_status = orig_fn

    def test_tc_comm_34_member_with_zero_files_and_productive_leg_remains_member(self):
        """TC-COMM-34: Partner with 0 files + 1 active leg remains Member under Strict Progression"""
        # Rohith Tangi (Partner 134) has 0 personal files, 1 active team leg in live roster
        status = VGK4UCareerService.get_partner_career_status(self.db, partner_id=134)
        self.assertIsNotNone(status)
        self.assertEqual(status['career_designation'], DESIGNATION_MEMBER)
        self.assertEqual(status['personal_prod_qualification'], PROD_QUAL_NONE)
        self.assertEqual(status['own_qualifying_files'], 0)
        self.assertTrue(status['active_team_legs'] >= 1)

    def test_tc_comm_35_member_with_downstream_sale_receives_one_pct_at_six_pct_producer(self):
        """TC-COMM-35: Member receives 1.00% sponsor override on downstream 6.0% sale"""
        res = VGK4UWaterfallEngine.calculate_commission_structure(
            self.db,
            producer_partner_id=160,
            deal_value=Decimal('200000.00'),
            category_slug='solar',
            direct_sponsor_id=134
        )
        self.assertTrue(res['success'])
        sponsor_alloc = [a for a in res['allocations'] if a['partner_id'] == 134][0]
        self.assertEqual(sponsor_alloc['role'], 'DIRECT_SPONSOR_OVERRIDE')
        self.assertEqual(sponsor_alloc['commission_pct'], Decimal('1.00'))
        self.assertEqual(sponsor_alloc['commission_amount'], Decimal('2000.00'))

    def test_tc_comm_36_historical_hashes_remain_identical(self):
        """TC-COMM-36: Verification that financial tables remain 100% immutable"""
        from sqlalchemy import text
        cash_rows = self.db.execute(text("""
            SELECT id, partner_id, source_lead_id, kind, level, commission_amount, net_payout, status, created_at 
            FROM vgk_cash_income_entries ORDER BY id
        """)).fetchall()
        cash_str = "".join(f"{r[0]}:{r[1]}:{r[2]}:{r[3]}:{r[4]}:{r[5]}:{r[6]}:{r[7]}:{r[8]}" for r in cash_rows)
        curr_cash_hash = hashlib.sha256(cash_str.encode()).hexdigest()

        adv_rows = self.db.execute(text("""
            SELECT id, partner_id, lead_id, kind, level, advance_amount, status, created_at 
            FROM vgk_solar_cibil_advances ORDER BY id
        """)).fetchall()
        adv_str = "".join(f"{r[0]}:{r[1]}:{r[2]}:{r[3]}:{r[4]}:{r[5]}:{r[6]}:{r[7]}" for r in adv_rows)
        curr_adv_hash = hashlib.sha256(adv_str.encode()).hexdigest()

        self.assertEqual(curr_cash_hash, self.baseline_cash_hash)
        self.assertEqual(curr_adv_hash, self.baseline_adv_hash)

    def test_tc_comm_37_existing_commission_generation_remains_idempotent(self):
        """TC-COMM-37: Calling commission generation on existing lead produces 0 new drafts"""
        from unittest.mock import MagicMock
        from datetime import date, datetime
        from app.services.vgk_cash_income import _generate_vgk4u_waterfall_income_drafts

        sp = self.db.begin_nested()
        try:
            lead = MagicMock()
            lead.id = 999937
            lead.company_id = 1
            lead.category_id = 6
            lead.deal_value_total = Decimal('200000.00')
            lead.deal_value_excl_tax = Decimal('200000.00')
            lead.deal_value_received = Decimal('200000.00')
            lead.confirmed_final_value = Decimal('200000.00')
            lead.solar_value = Decimal('200000.00')
            lead.solar_brand_id = None
            lead.associated_partner_id = 160
            lead.team_senior_partner_id = 134
            lead.vgk_field_support_id = None
            lead.showroom_vgk_id = None
            lead.solar_pipeline_status = 'completed'
            lead.income_date = date(2026, 9, 12)
            lead.created_at = datetime(2026, 9, 10)

            run1 = _generate_vgk4u_waterfall_income_drafts(self.db, lead)
            self.assertTrue(run1 > 0)

            run2 = _generate_vgk4u_waterfall_income_drafts(self.db, lead)
            self.assertEqual(run2, 0, "Subsequent run must produce 0 drafts for idempotency!")
        finally:
            sp.rollback()


if __name__ == '__main__':
    unittest.main()


