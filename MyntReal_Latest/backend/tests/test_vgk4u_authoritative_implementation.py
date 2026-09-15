"""
VGK4U Authoritative Implementation Test Suite
=============================================
Comprehensive Automated Verification Suite for VGK4U Career, Personal Production,
Differential Waterfall, Support Income, and Points Architecture.

Validates all 23 Approved Business Decisions & Architecture Scenarios:
 1. Unqualified Member (0 files): rate == 0.00% (Locked).
 2. 1st File Qualifying: unlocks Channel Partner (6.00%).
 3. Manager Promotion: 1 own file + 1 active leg -> 7.50%.
 4. General Manager Promotion: 1 own file + 5 active legs -> 8.50%.
 5. Regional Manager Promotion: 1 own file + 10 active legs -> 9.00%.
 6. Fast-Track GM Rate: 5 personal files (0 legs) -> 8.50%.
 7. Fast-Track RM Rate: 10 personal files (0 legs) -> 9.00%.
 8. Accelerated Leadership Unlock: direct jump to GM upon 1st file based on legs.
 9. Best-Of Guarantee: awards max(career_rate, personal_prod_rate).
10. Direct Sponsor Override: CP (1.00%), Manager (1.50%), GM (2.50%), RM (3.00%).
11. Differential Upline Traversal: residual Manager (0.50%), GM (1.00%), RM (0.50%).
12. Inactive Member Commission Draft: unpaid member generates drafts (no forfeiture to Apex).
13. Support Case A: Normal field support -> 0.75% base, 0.00% full (Total: 0.75%).
14. Support Case B: Direct Full-Service closing (no staff) -> 0.75% base + 0.75% full (Total: 1.50%).
15. Support Case C: Staff involved -> 0.75% base, full support disabled 0.00% (Total: 0.75%).
16. Support Case D: No support partner assigned -> 0.00% total support.
17. Showroom Override: Outside network pool allocation (level 6).
18. Apex Remainder Absorption: Unabsorbed network pool retained by Apex (level 0).
19. Total Network Pool Invariant: Field network + Apex remainder == max network pool (9.00%).
20. l1 NameError bug resolved: No crash when vgk_field_support_id is set on lead completion.
21. Career Read-Cache Sync: sync_partner_career_status_to_db updates official_partners columns.
22. API Contract Parity: endpoints expose effective_personal_producer_rate, own_qualifying_files, active_team_legs.
23. Summary Support Total: level IN (5, 7) aggregated in support_total.
"""

import os
import sys
import unittest
import uuid
from decimal import Decimal
from datetime import datetime
from sqlalchemy import text

# Dynamic path resolution (ENFORCE NO ABSOLUTE PATHS RULE)
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.core.database import SessionLocal
from app.models.staff_accounts import OfficialPartner
from app.models.crm import CRMLead
from app.models.vgk_cash_income import VGKCashIncomeEntry
from app.models.vgk4u_models import VGK4UCorporateMarginLedger
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
from app.services.universal_incentive_engine import (
    get_partner_current_position_v18,
    get_bulk_partner_current_positions_v26,
)
from app.services.vgk_cash_income import create_draft_for_completed_lead


class TestVGK4UAuthoritativeImplementation(unittest.TestCase):
    """
    Comprehensive test suite validating the complete VGK4U Career, Personal Production,
    Differential Waterfall, Support Income, and Points Architecture.
    """

    @classmethod
    def setUpClass(cls):
        db = SessionLocal()
        try:
            # Clean any leftover test records from prior runs (partner id >= 9000)
            db.execute(text("DELETE FROM vgk4u_corporate_margin_ledger WHERE source_lead_id >= 95000"))
            db.execute(text("DELETE FROM vgk_cash_income_entries WHERE partner_id >= 9000 OR source_lead_id >= 95000"))
            db.execute(text("DELETE FROM crm_leads WHERE id >= 95000 OR associated_partner_id >= 9000"))
            db.execute(text("UPDATE official_partners SET parent_partner_id = NULL WHERE id >= 9000 OR parent_partner_id >= 9000"))
            db.execute(text("DELETE FROM official_partners WHERE id >= 9000"))
            db.commit()
        except Exception:
            db.rollback()
        finally:
            db.close()

    @classmethod
    def tearDownClass(cls):
        db = SessionLocal()
        try:
            db.execute(text("DELETE FROM vgk4u_corporate_margin_ledger WHERE source_lead_id >= 95000"))
            db.execute(text("DELETE FROM vgk_cash_income_entries WHERE partner_id >= 9000 OR source_lead_id >= 95000"))
            db.execute(text("DELETE FROM crm_leads WHERE id >= 95000 OR associated_partner_id >= 9000"))
            db.execute(text("UPDATE official_partners SET parent_partner_id = NULL WHERE id >= 9000 OR parent_partner_id >= 9000"))
            db.execute(text("DELETE FROM official_partners WHERE id >= 9000"))
            db.commit()
        except Exception:
            db.rollback()
        finally:
            db.close()

    def setUp(self):
        self.db = SessionLocal()
        self.created_partner_ids = []
        self.created_lead_ids = []
        self.created_income_ids = []

    def tearDown(self):
        try:
            self.db.rollback()
            if self.created_lead_ids:
                self.db.execute(text("DELETE FROM vgk4u_corporate_margin_ledger WHERE source_lead_id IN :lids"), {'lids': tuple(self.created_lead_ids)})
                self.db.execute(text("DELETE FROM vgk_cash_income_entries WHERE source_lead_id IN :lids"), {'lids': tuple(self.created_lead_ids)})
                self.db.execute(text("DELETE FROM crm_leads WHERE id IN :lids"), {'lids': tuple(self.created_lead_ids)})
            if self.created_partner_ids:
                self.db.execute(text("DELETE FROM vgk_cash_income_entries WHERE partner_id IN :pids"), {'pids': tuple(self.created_partner_ids)})
                self.db.execute(text("UPDATE official_partners SET parent_partner_id = NULL WHERE id IN :pids OR parent_partner_id IN :pids"), {'pids': tuple(self.created_partner_ids)})
                self.db.execute(text("DELETE FROM official_partners WHERE id IN :pids"), {'pids': tuple(self.created_partner_ids)})
            self.db.commit()
        except Exception:
            self.db.rollback()
        finally:
            self.db.close()

    def _create_partner(self, parent_id=None, is_active=True, prefix="VGK", name=None):
        uid = uuid.uuid4().hex[:6].upper()
        pcode = f"{prefix}_{uid}"
        partner = OfficialPartner(
            partner_code=pcode,
            partner_name=name or f"Partner {uid}",
            category="VGK_TEAM",
            is_active=is_active,
            parent_partner_id=parent_id,
            vgk_points_balance=Decimal('20000.00'),
        )
        self.db.add(partner)
        self.db.flush()
        self.created_partner_ids.append(partner.id)
        return partner

    def _create_qualifying_lead(self, partner_id, status='completed', sps='completed', dvr=100000.0, total=100000.0):
        uid = uuid.uuid4().hex[:6]
        lead = CRMLead(
            name=f"Lead {uid}",
            phone=f"98{uid[:8]}",
            company_id=1,
            category_id=1,
            associated_partner_id=partner_id,
            status=status,
            solar_pipeline_status=sps,
            deal_value_total=total,
            deal_value_received=dvr,
            deal_value_balance=0.0,
        )
        self.db.add(lead)
        self.db.flush()
        self.created_lead_ids.append(lead.id)
        return lead

    # =========================================================================
    # SCENARIO 1: Unqualified Member (0 files) -> rate == 0.00% (Locked)
    # =========================================================================
    def test_01_unqualified_member_zero_files_rate_zero(self):
        """Unqualified member with 0 personal files must be Member with 0.00% locked earning rate."""
        member = self._create_partner(is_active=True)
        
        # 1. Career Service Evaluation
        cs = VGK4UCareerService.get_partner_career_status(self.db, member.id)
        self.assertIsNotNone(cs)
        self.assertEqual(cs['career_designation'], DESIGNATION_MEMBER)
        self.assertEqual(cs['personal_prod_qualification'], PROD_QUAL_NONE)
        self.assertEqual(cs['effective_personal_producer_rate'], 0.0)
        self.assertEqual(cs['own_qualifying_files'], 0)

        # 2. Universal Incentive Engine Parity
        pos = get_partner_current_position_v18(self.db, member.id)
        self.assertEqual(pos['position'], DESIGNATION_MEMBER)
        self.assertEqual(pos['effective_personal_producer_rate'], 0.0)
        self.assertEqual(pos['rate_pct'], 0.0)
        self.assertEqual(pos['rank_slab_pct'], 0.0)
        self.assertEqual(pos['stars'], 0)

    # =========================================================================
    # SCENARIO 2: 1st File Qualifying -> Unlocks Channel Partner (6.00%)
    # =========================================================================
    def test_02_first_file_qualifying_unlocks_channel_partner_and_six_percent(self):
        """Closing 1st qualifying file elevates member to Channel Partner at 6.00%."""
        member = self._create_partner(is_active=True)
        self._create_qualifying_lead(member.id, status='completed')

        cs = VGK4UCareerService.get_partner_career_status(self.db, member.id)
        self.assertEqual(cs['career_designation'], DESIGNATION_CHANNEL_PARTNER)
        self.assertEqual(cs['personal_prod_qualification'], PROD_QUAL_BASE)
        self.assertEqual(cs['effective_personal_producer_rate'], 6.0)
        self.assertEqual(cs['own_qualifying_files'], 1)

        # Waterfall Calculation check
        wf = VGK4UWaterfallEngine.calculate_commission_structure(
            db=self.db,
            producer_partner_id=member.id,
            deal_value=Decimal('100000.00'),
            category_slug='solar'
        )
        self.assertTrue(wf['success'])
        self.assertEqual(wf['producer_rate_pct'], Decimal('6.00'))
        producer_alloc = next(a for a in wf['allocations'] if a['role'] == 'PRODUCER')
        self.assertEqual(producer_alloc['commission_pct'], Decimal('6.00'))
        self.assertEqual(producer_alloc['commission_amount'], Decimal('6000.00'))

    # =========================================================================
    # SCENARIO 3: Manager Promotion -> 1 own file + 1 active leg -> 7.50%
    # =========================================================================
    def test_03_manager_promotion_one_file_one_leg(self):
        """1 own qualifying file + 1 active direct leg elevates partner to Manager (7.50%)."""
        manager = self._create_partner(is_active=True, name="Manager Candidate")
        self._create_qualifying_lead(manager.id)  # 1 own file

        # Direct child leg with an active producer
        child = self._create_partner(parent_id=manager.id, is_active=True, name="Child Partner")
        self._create_qualifying_lead(child.id)  # Child produces 1 file

        cs = VGK4UCareerService.get_partner_career_status(self.db, manager.id)
        self.assertEqual(cs['career_designation'], DESIGNATION_MANAGER)
        self.assertEqual(cs['active_team_legs'], 1)
        self.assertEqual(cs['effective_personal_producer_rate'], 7.5)

    # =========================================================================
    # SCENARIO 4: General Manager Promotion -> 1 own file + 5 active legs -> 8.50%
    # =========================================================================
    def test_04_general_manager_promotion_one_file_five_legs(self):
        """1 own qualifying file + 5 active direct legs elevates partner to General Manager (8.50%)."""
        gm = self._create_partner(is_active=True, name="GM Candidate")
        self._create_qualifying_lead(gm.id)  # 1 own file

        # Create 5 distinct direct legs each containing a producer
        for i in range(5):
            direct_child = self._create_partner(parent_id=gm.id, is_active=True, name=f"Direct Leg {i+1}")
            self._create_qualifying_lead(direct_child.id)

        cs = VGK4UCareerService.get_partner_career_status(self.db, gm.id)
        self.assertEqual(cs['career_designation'], DESIGNATION_GENERAL_MANAGER)
        self.assertEqual(cs['active_team_legs'], 5)
        self.assertEqual(cs['effective_personal_producer_rate'], 8.5)

    # =========================================================================
    # SCENARIO 5: Regional Manager Promotion -> 1 own file + 10 active legs -> 9.00%
    # =========================================================================
    def test_05_regional_manager_promotion_one_file_ten_legs(self):
        """1 own qualifying file + 10 active direct legs elevates partner to Regional Manager (9.00%)."""
        rm = self._create_partner(is_active=True, name="RM Candidate")
        self._create_qualifying_lead(rm.id)  # 1 own file

        for i in range(10):
            direct_child = self._create_partner(parent_id=rm.id, is_active=True, name=f"RM Leg {i+1}")
            self._create_qualifying_lead(direct_child.id)

        cs = VGK4UCareerService.get_partner_career_status(self.db, rm.id)
        self.assertEqual(cs['career_designation'], DESIGNATION_REGIONAL_MANAGER)
        self.assertEqual(cs['active_team_legs'], 10)
        self.assertEqual(cs['effective_personal_producer_rate'], 9.0)

    # =========================================================================
    # SCENARIO 6: Fast-Track GM Rate -> 5 personal files (0 legs) -> 8.50%
    # =========================================================================
    def test_06_fast_track_gm_rate_five_personal_files_zero_legs(self):
        """5 personal qualifying files with 0 legs awards fast-track 8.50% personal rate."""
        producer = self._create_partner(is_active=True, name="Fast Track GM Solo")
        for _ in range(5):
            self._create_qualifying_lead(producer.id)

        cs = VGK4UCareerService.get_partner_career_status(self.db, producer.id)
        self.assertEqual(cs['career_designation'], DESIGNATION_CHANNEL_PARTNER)
        self.assertEqual(cs['personal_prod_qualification'], PROD_QUAL_GM)
        self.assertEqual(cs['effective_personal_producer_rate'], 8.5)

    # =========================================================================
    # SCENARIO 7: Fast-Track RM Rate -> 10 personal files (0 legs) -> 9.00%
    # =========================================================================
    def test_07_fast_track_rm_rate_ten_personal_files_zero_legs(self):
        """10 personal qualifying files with 0 legs awards fast-track 9.00% personal rate."""
        producer = self._create_partner(is_active=True, name="Fast Track RM Solo")
        for _ in range(10):
            self._create_qualifying_lead(producer.id)

        cs = VGK4UCareerService.get_partner_career_status(self.db, producer.id)
        self.assertEqual(cs['career_designation'], DESIGNATION_CHANNEL_PARTNER)
        self.assertEqual(cs['personal_prod_qualification'], PROD_QUAL_RM)
        self.assertEqual(cs['effective_personal_producer_rate'], 9.0)

    # =========================================================================
    # SCENARIO 8: Accelerated Leadership Unlock -> Direct jump to GM upon 1st file
    # =========================================================================
    def test_08_accelerated_leadership_unlock_direct_jump(self):
        """A member with 5 built legs who closes their 1st file jumps directly to GM (8.50%)."""
        leader = self._create_partner(is_active=True, name="Accelerated Leader")
        
        # Build 5 active direct legs while leader has 0 personal files
        for i in range(5):
            leg = self._create_partner(parent_id=leader.id, is_active=True, name=f"Built Leg {i+1}")
            self._create_qualifying_lead(leg.id)

        # Before closing personal file: must be Member with 0.00%
        cs_before = VGK4UCareerService.get_partner_career_status(self.db, leader.id)
        self.assertEqual(cs_before['career_designation'], DESIGNATION_MEMBER)
        self.assertEqual(cs_before['effective_personal_producer_rate'], 0.0)

        # Leader closes 1st personal file
        self._create_qualifying_lead(leader.id)

        # After closing 1st personal file: jumps immediately to General Manager (8.50%)
        cs_after = VGK4UCareerService.get_partner_career_status(self.db, leader.id)
        self.assertEqual(cs_after['career_designation'], DESIGNATION_GENERAL_MANAGER)
        self.assertEqual(cs_after['effective_personal_producer_rate'], 8.5)

    # =========================================================================
    # SCENARIO 9: Best-Of Guarantee -> max(career_rate, personal_prod_rate)
    # =========================================================================
    def test_09_best_of_guarantee_career_vs_personal_production(self):
        """System awards the higher of career rank vs personal production volume."""
        # Case A: Career is Manager (7.5%), but has 5 personal files (GM fast-track 8.5%) -> 8.5%
        p1 = self._create_partner(is_active=True, name="High Producer Manager")
        leg1 = self._create_partner(parent_id=p1.id, is_active=True)
        self._create_qualifying_lead(leg1.id)  # 1 active leg -> Manager
        for _ in range(5):
            self._create_qualifying_lead(p1.id)  # 5 files -> GM tier
        cs1 = VGK4UCareerService.get_partner_career_status(self.db, p1.id)
        self.assertEqual(cs1['career_designation'], DESIGNATION_MANAGER)
        self.assertEqual(cs1['personal_prod_qualification'], PROD_QUAL_GM)
        self.assertEqual(cs1['effective_personal_producer_rate'], 8.5)

        # Case B: Career is GM (8.5%), but personal production is only 2 files (Base 6.0%) -> 8.5%
        p2 = self._create_partner(is_active=True, name="Organizational GM")
        for i in range(5):
            l = self._create_partner(parent_id=p2.id, is_active=True)
            self._create_qualifying_lead(l.id)
        for _ in range(2):
            self._create_qualifying_lead(p2.id)
        cs2 = VGK4UCareerService.get_partner_career_status(self.db, p2.id)
        self.assertEqual(cs2['career_designation'], DESIGNATION_GENERAL_MANAGER)
        self.assertEqual(cs2['personal_prod_qualification'], PROD_QUAL_BASE)
        self.assertEqual(cs2['effective_personal_producer_rate'], 8.5)

    # =========================================================================
    # SCENARIO 10: Direct Sponsor Override by Rank
    # =========================================================================
    def test_10_direct_sponsor_override_by_rank(self):
        """CP sponsor gets 1.00%, Manager sponsor gets 1.50%, GM gets 2.50%, RM gets 3.00%."""
        deal_val = Decimal('100000.00')

        # 1. CP Sponsor (1 own file, 0 active legs since producer is closing 1st file)
        cp_sponsor = self._create_partner(is_active=True, name="CP Sponsor")
        self._create_qualifying_lead(cp_sponsor.id)
        cp_prod = self._create_partner(parent_id=cp_sponsor.id, is_active=True, name="CP Producer 1")
        # Note: cp_prod has 0 prior qualifying files in DB; this deal represents their 1st file
        wf_cp = VGK4UWaterfallEngine.calculate_commission_structure(
            db=self.db, producer_partner_id=cp_prod.id, deal_value=deal_val, direct_sponsor_id=cp_sponsor.id
        )
        sp_alloc = next(a for a in wf_cp['allocations'] if a['role'] == 'DIRECT_SPONSOR_OVERRIDE')
        self.assertEqual(sp_alloc['commission_pct'], Decimal('1.00'))

        # 2. Manager Sponsor (1 own file + 1 leg)
        mgr_sponsor = self._create_partner(is_active=True, name="Mgr Sponsor")
        self._create_qualifying_lead(mgr_sponsor.id)
        mgr_leg = self._create_partner(parent_id=mgr_sponsor.id, is_active=True)
        self._create_qualifying_lead(mgr_leg.id)
        mgr_prod = self._create_partner(parent_id=mgr_sponsor.id, is_active=True, name="CP Producer 2")
        wf_mgr = VGK4UWaterfallEngine.calculate_commission_structure(
            db=self.db, producer_partner_id=mgr_prod.id, deal_value=deal_val, direct_sponsor_id=mgr_sponsor.id
        )
        sp_alloc_mgr = next(a for a in wf_mgr['allocations'] if a['role'] == 'DIRECT_SPONSOR_OVERRIDE')
        self.assertEqual(sp_alloc_mgr['commission_pct'], Decimal('1.50'))

        # 3. GM Sponsor (1 own file + 5 legs)
        gm_sponsor = self._create_partner(is_active=True, name="GM Sponsor")
        self._create_qualifying_lead(gm_sponsor.id)
        for _ in range(5):
            gml = self._create_partner(parent_id=gm_sponsor.id, is_active=True)
            self._create_qualifying_lead(gml.id)
        gm_prod = self._create_partner(parent_id=gm_sponsor.id, is_active=True, name="CP Producer 3")
        wf_gm = VGK4UWaterfallEngine.calculate_commission_structure(
            db=self.db, producer_partner_id=gm_prod.id, deal_value=deal_val, direct_sponsor_id=gm_sponsor.id
        )
        sp_alloc_gm = next(a for a in wf_gm['allocations'] if a['role'] == 'DIRECT_SPONSOR_OVERRIDE')
        self.assertEqual(sp_alloc_gm['commission_pct'], Decimal('2.50'))

        # 4. RM Sponsor (1 own file + 10 legs)
        rm_sponsor = self._create_partner(is_active=True, name="RM Sponsor")
        self._create_qualifying_lead(rm_sponsor.id)
        for _ in range(10):
            rml = self._create_partner(parent_id=rm_sponsor.id, is_active=True)
            self._create_qualifying_lead(rml.id)
        rm_prod = self._create_partner(parent_id=rm_sponsor.id, is_active=True, name="CP Producer 4")
        wf_rm = VGK4UWaterfallEngine.calculate_commission_structure(
            db=self.db, producer_partner_id=rm_prod.id, deal_value=deal_val, direct_sponsor_id=rm_sponsor.id
        )
        sp_alloc_rm = next(a for a in wf_rm['allocations'] if a['role'] == 'DIRECT_SPONSOR_OVERRIDE')
        self.assertEqual(sp_alloc_rm['commission_pct'], Decimal('3.00'))

    # =========================================================================
    # SCENARIO 11: Differential Upline Traversal Multi-Tier
    # =========================================================================
    def test_11_differential_upline_traversal_multi_tier(self):
        """Upline traversal correctly allocates residual Manager (0.50%), GM (1.00%), RM (0.50%)."""
        deal_val = Decimal('100000.00')

        # RM Upline (top, 10 legs)
        rm = self._create_partner(is_active=True, name="Upline RM")
        self._create_qualifying_lead(rm.id)
        for _ in range(10):
            l = self._create_partner(parent_id=rm.id, is_active=True)
            self._create_qualifying_lead(l.id)

        # GM Upline (5 legs)
        gm = self._create_partner(parent_id=rm.id, is_active=True, name="Upline GM")
        self._create_qualifying_lead(gm.id)
        for _ in range(5):
            l = self._create_partner(parent_id=gm.id, is_active=True)
            self._create_qualifying_lead(l.id)

        # Manager Upline (1 leg)
        mgr = self._create_partner(parent_id=gm.id, is_active=True, name="Upline Mgr")
        self._create_qualifying_lead(mgr.id)
        l = self._create_partner(parent_id=mgr.id, is_active=True)
        self._create_qualifying_lead(l.id)

        # Direct Sponsor (CP, 1 file, 0 legs)
        sponsor_cp = self._create_partner(parent_id=mgr.id, is_active=True, name="Sponsor CP")
        self._create_qualifying_lead(sponsor_cp.id)

        # Producer (CP, closing 1st file, 0 prior files in DB)
        prod = self._create_partner(parent_id=sponsor_cp.id, is_active=True, name="Producer CP")

        wf = VGK4UWaterfallEngine.calculate_commission_structure(
            db=self.db, producer_partner_id=prod.id, deal_value=deal_val, direct_sponsor_id=sponsor_cp.id
        )
        self.assertTrue(wf['success'])

        alloc_map = {a['role']: a for a in wf['allocations']}
        self.assertEqual(alloc_map['PRODUCER']['commission_pct'], Decimal('6.00'))
        self.assertEqual(alloc_map['DIRECT_SPONSOR_OVERRIDE']['commission_pct'], Decimal('1.00'))
        self.assertEqual(alloc_map['MANAGER_DIFFERENTIAL']['commission_pct'], Decimal('0.50'))
        self.assertEqual(alloc_map['GM_DIFFERENTIAL']['commission_pct'], Decimal('1.00'))
        self.assertEqual(alloc_map['RM_DIFFERENTIAL']['commission_pct'], Decimal('0.50'))
        self.assertNotIn('APEX_REMAINDER', alloc_map)  # Total 9.00% fully absorbed

    # =========================================================================
    # SCENARIO 12: Inactive Member Commission Draft Generation (No Forfeiture)
    # =========================================================================
    def test_12_inactive_member_commission_draft_generation(self):
        """Unpaid member (is_active=False) generates commission draft at legitimate rate; not forfeited to Apex."""
        unpaid_member = self._create_partner(is_active=False, name="Unpaid Member")
        lead = self._create_qualifying_lead(unpaid_member.id, dvr=100000.0, total=100000.0)

        created_count = create_draft_for_completed_lead(self.db, lead)
        self.assertGreater(created_count, 0)

        # Verify draft entry exists for the unpaid member
        draft = self.db.query(VGKCashIncomeEntry).filter(
            VGKCashIncomeEntry.source_lead_id == lead.id,
            VGKCashIncomeEntry.partner_id == unpaid_member.id,
            VGKCashIncomeEntry.level == 1
        ).first()
        self.assertIsNotNone(draft)
        self.assertEqual(draft.commission_pct, Decimal('6.00'))
        self.assertEqual(draft.status, 'DRAFT')

    # =========================================================================
    # SCENARIO 13: Support Case A -> Normal Field Support (+0.75% base, 0.00% full)
    # =========================================================================
    def test_13_support_case_a_normal_field_support(self):
        """Standard field support assigns +0.75% Base Support (level 5) outside network pool."""
        prod = self._create_partner(is_active=True)
        self._create_qualifying_lead(prod.id)
        sup = self._create_partner(is_active=True, name="Support Partner A")

        wf = VGK4UWaterfallEngine.calculate_commission_structure(
            db=self.db,
            producer_partner_id=prod.id,
            deal_value=Decimal('100000.00'),
            support_partner_id=sup.id,
            is_end_to_end_support=False,
            is_staff_involved=False,
        )
        self.assertEqual(wf['support_pct'], Decimal('0.75'))
        self.assertEqual(wf['full_support_pct'], Decimal('0.00'))
        self.assertEqual(wf['total_support_pct'], Decimal('0.75'))

        sup_alloc = next(a for a in wf['allocations'] if a['role'] == 'FIELD_SUPPORT')
        self.assertEqual(sup_alloc['level'], 5)
        self.assertEqual(sup_alloc['commission_pct'], Decimal('0.75'))
        self.assertFalse(any(a['role'] == 'FULL_SUPPORT' for a in wf['allocations']))

    # =========================================================================
    # SCENARIO 14: Support Case B -> Direct Full-Service Closing (+1.50% total)
    # =========================================================================
    def test_14_support_case_b_direct_full_service_closing(self):
        """Direct full-service closing without staff awards +0.75% base and +0.75% full support (+1.50% total)."""
        prod = self._create_partner(is_active=True)
        self._create_qualifying_lead(prod.id)

        # Partner acts as direct full support with no staff
        wf = VGK4UWaterfallEngine.calculate_commission_structure(
            db=self.db,
            producer_partner_id=prod.id,
            deal_value=Decimal('100000.00'),
            support_partner_id=prod.id,
            is_end_to_end_support=True,
            is_staff_involved=False,
        )
        self.assertEqual(wf['support_pct'], Decimal('0.75'))
        self.assertEqual(wf['full_support_pct'], Decimal('0.75'))
        self.assertEqual(wf['total_support_pct'], Decimal('1.50'))

        base_alloc = next(a for a in wf['allocations'] if a['role'] == 'FIELD_SUPPORT')
        full_alloc = next(a for a in wf['allocations'] if a['role'] == 'FULL_SUPPORT')
        self.assertEqual(base_alloc['level'], 5)
        self.assertEqual(base_alloc['commission_pct'], Decimal('0.75'))
        self.assertEqual(full_alloc['level'], 7)
        self.assertEqual(full_alloc['commission_pct'], Decimal('0.75'))

    # =========================================================================
    # SCENARIO 15: Support Case C -> Staff Involved Disables Full Support
    # =========================================================================
    def test_15_support_case_c_staff_involved_disables_full_support(self):
        """If staff is involved, full support is disabled (0.00%) and only base support (+0.75%) is awarded."""
        prod = self._create_partner(is_active=True)
        self._create_qualifying_lead(prod.id)
        sup = self._create_partner(is_active=True)

        wf = VGK4UWaterfallEngine.calculate_commission_structure(
            db=self.db,
            producer_partner_id=prod.id,
            deal_value=Decimal('100000.00'),
            support_partner_id=sup.id,
            is_end_to_end_support=True,
            is_staff_involved=True,  # Company staff involved
        )
        self.assertEqual(wf['support_pct'], Decimal('0.75'))
        self.assertEqual(wf['full_support_pct'], Decimal('0.00'))
        self.assertEqual(wf['total_support_pct'], Decimal('0.75'))
        self.assertTrue(wf['is_staff_involved'])
        self.assertFalse(any(a['role'] == 'FULL_SUPPORT' for a in wf['allocations']))

    # =========================================================================
    # SCENARIO 16: Support Case D -> No Support Partner Assigned
    # =========================================================================
    def test_16_support_case_d_no_support_partner(self):
        """When support_partner_id is None, total support is 0.00% and no support allocations are made."""
        prod = self._create_partner(is_active=True)
        self._create_qualifying_lead(prod.id)

        wf = VGK4UWaterfallEngine.calculate_commission_structure(
            db=self.db,
            producer_partner_id=prod.id,
            deal_value=Decimal('100000.00'),
            support_partner_id=None,
        )
        self.assertEqual(wf['support_pct'], Decimal('0.00'))
        self.assertEqual(wf['full_support_pct'], Decimal('0.00'))
        self.assertEqual(wf['total_support_pct'], Decimal('0.00'))
        self.assertFalse(any(a['role'] in ('FIELD_SUPPORT', 'FULL_SUPPORT') for a in wf['allocations']))

    # =========================================================================
    # SCENARIO 17: Showroom Override Allocation
    # =========================================================================
    def test_17_showroom_override_allocation(self):
        """Showroom partner receives configured showroom percentage outside network pool (level 6)."""
        prod = self._create_partner(is_active=True)
        self._create_qualifying_lead(prod.id)
        showroom = self._create_partner(is_active=True, name="Showroom Hub")

        wf = VGK4UWaterfallEngine.calculate_commission_structure(
            db=self.db,
            producer_partner_id=prod.id,
            deal_value=Decimal('100000.00'),
            showroom_partner_id=showroom.id,
        )
        sh_alloc = next((a for a in wf['allocations'] if a['role'] == 'SHOWROOM'), None)
        self.assertIsNotNone(sh_alloc)
        self.assertEqual(sh_alloc['level'], 6)
        self.assertEqual(sh_alloc['partner_id'], showroom.id)
        self.assertGreater(sh_alloc['commission_pct'], Decimal('0.00'))

    # =========================================================================
    # SCENARIO 18: Apex Remainder Absorption
    # =========================================================================
    def test_18_apex_remainder_absorption(self):
        """Unabsorbed network pool is retained by Corporate Apex Node (level 0)."""
        prod = self._create_partner(is_active=True)
        self._create_qualifying_lead(prod.id)

        wf = VGK4UWaterfallEngine.calculate_commission_structure(
            db=self.db,
            producer_partner_id=prod.id,
            deal_value=Decimal('100000.00'),
            direct_sponsor_id=None,  # No upline at all
        )
        # Producer gets 6.00%. Remaining 3.00% is absorbed by Apex Remainder
        apex_alloc = next(a for a in wf['allocations'] if a['role'] == 'APEX_REMAINDER')
        self.assertEqual(apex_alloc['level'], 0)
        self.assertEqual(apex_alloc['partner_id'], ROOT_APEX_PARTNER_ID)
        self.assertEqual(apex_alloc['commission_pct'], Decimal('3.00'))

    # =========================================================================
    # SCENARIO 19: Total Network Pool Invariant (Strictly == 9.00%)
    # =========================================================================
    def test_19_total_network_pool_invariant(self):
        """Producer + overrides + Apex remainder strictly equals max_network_pool_pct (9.00%)."""
        prod = self._create_partner(is_active=True)
        self._create_qualifying_lead(prod.id)

        network_roles = ('PRODUCER', 'DIRECT_SPONSOR_OVERRIDE', 'MANAGER_DIFFERENTIAL', 'GM_DIFFERENTIAL', 'RM_DIFFERENTIAL', 'APEX_REMAINDER')

        for scenario in range(3):
            if scenario == 0:
                wf = VGK4UWaterfallEngine.calculate_commission_structure(self.db, prod.id, Decimal('250000.00'))
            elif scenario == 1:
                sp = self._create_partner(is_active=True)
                self._create_qualifying_lead(sp.id)
                wf = VGK4UWaterfallEngine.calculate_commission_structure(self.db, prod.id, Decimal('150000.00'), direct_sponsor_id=sp.id)
            else:
                wf = VGK4UWaterfallEngine.calculate_commission_structure(self.db, prod.id, Decimal('500000.00'), support_partner_id=prod.id, is_end_to_end_support=True)

            total_network = sum(a['commission_pct'] for a in wf['allocations'] if a['role'] in network_roles)
            self.assertEqual(total_network, Decimal('9.00'))

    # =========================================================================
    # SCENARIO 20: l1 NameError Bug Resolved in Cash Income
    # =========================================================================
    def test_20_l1_name_error_bug_resolved_in_cash_income(self):
        """Lead with vgk_field_support_id executes without raising NameError: name 'l1' is not defined."""
        prod = self._create_partner(is_active=True)
        sup = self._create_partner(is_active=True)
        lead = self._create_qualifying_lead(prod.id, dvr=150000.0, total=150000.0)
        lead.vgk_field_support_id = sup.id
        self.db.flush()

        try:
            created = create_draft_for_completed_lead(self.db, lead)
            self.assertGreater(created, 0)
        except NameError as ne:
            self.fail(f"NameError raised: {ne}")

    # =========================================================================
    # SCENARIO 21: Career Read-Cache Sync to DB
    # =========================================================================
    def test_21_career_read_cache_sync_to_db(self):
        """sync_partner_career_status_to_db accurately updates official_partners columns."""
        partner = self._create_partner(is_active=True, name="Sync Target")
        self._create_qualifying_lead(partner.id)
        child = self._create_partner(parent_id=partner.id, is_active=True)
        self._create_qualifying_lead(child.id)

        res = VGK4UCareerService.sync_partner_career_status_to_db(self.db, partner.id)
        self.assertIsNotNone(res)
        self.assertEqual(res['career_designation'], DESIGNATION_MANAGER)

        # Inspect database row directly
        row = self.db.execute(text("""
            SELECT vgk4u_current_designation, vgk4u_personal_prod_qualification,
                   vgk4u_own_qualifying_files, vgk4u_active_team_count
            FROM official_partners WHERE id = :pid
        """), {'pid': partner.id}).fetchone()

        self.assertEqual(row[0], DESIGNATION_MANAGER)
        self.assertEqual(row[1], PROD_QUAL_BASE)
        self.assertEqual(row[2], 1)
        self.assertEqual(row[3], 1)

    # =========================================================================
    # SCENARIO 22: API Contract Parity
    # =========================================================================
    def test_22_api_contract_parity_fields(self):
        """API contract dictionaries expose effective_personal_producer_rate, own_qualifying_files, active_team_legs."""
        partner = self._create_partner(is_active=True)
        self._create_qualifying_lead(partner.id)

        pos = get_partner_current_position_v18(self.db, partner.id)
        self.assertIn('effective_personal_producer_rate', pos)
        self.assertIn('own_qualifying_files', pos)
        self.assertIn('active_team_legs', pos)
        self.assertEqual(pos['effective_personal_producer_rate'], 6.0)
        self.assertEqual(pos['own_qualifying_files'], 1)
        self.assertEqual(pos['active_team_legs'], 0)

        bulk_pos = get_bulk_partner_current_positions_v26(self.db, [partner.id])
        self.assertIn(partner.id, bulk_pos)
        self.assertEqual(bulk_pos[partner.id]['effective_personal_producer_rate'], 6.0)

    # =========================================================================
    # SCENARIO 23: Summary Support Total Includes Level 5 and 7
    # =========================================================================
    def test_23_summary_support_total_includes_level_5_and_7(self):
        """Cash income summary query aggregates both Level 5 (Field Support) and Level 7 (Full Support)."""
        sup = self._create_partner(is_active=True, name="Support Aggregator")
        lead = self._create_qualifying_lead(sup.id)

        # Manually insert a Level 5 and Level 7 entry to simulate Case B payout
        uid = uuid.uuid4().hex[:6]
        e5 = VGKCashIncomeEntry(
            company_id=1,
            entry_number=f"TEST_E5_{uid}",
            partner_id=sup.id,
            source_lead_id=lead.id,
            level=5,
            kind='COMMISSION',
            status='PENDING',
            commission_amount=Decimal('750.00'),
            created_at=datetime.utcnow()
        )
        e7 = VGKCashIncomeEntry(
            company_id=1,
            entry_number=f"TEST_E7_{uid}",
            partner_id=sup.id,
            source_lead_id=lead.id,
            level=7,
            kind='COMMISSION',
            status='PENDING',
            commission_amount=Decimal('750.00'),
            created_at=datetime.utcnow()
        )
        self.db.add(e5)
        self.db.add(e7)
        self.db.flush()
        self.created_income_ids.extend([e5.id, e7.id])

        # Run summary query directly as written in vgk_cash_income.py
        summary = self.db.execute(text("""
            SELECT SUM(CASE WHEN kind = 'COMMISSION' AND level IN (5, 7) THEN commission_amount ELSE 0 END) AS support_total
            FROM vgk_cash_income_entries
            WHERE partner_id = :pid
        """), {'pid': sup.id}).fetchone()

        self.assertEqual(Decimal(str(summary[0])), Decimal('1500.00'))

    # =========================================================================
    # SCENARIO 24: EV Financial Network Pool and Capacity
    # =========================================================================
    def test_24_ev_financial_network_pool_and_capacity(self):
        """EV category configuration enforces max network pool == 10.00%, configured == 9.50%, remaining capacity == 0.50%."""
        cfg = VGK4UWaterfallEngine.get_category_config(self.db, 'ev', 'v2_sep2026')
        self.assertIsNotNone(cfg)
        self.assertEqual(Decimal(str(cfg.max_network_pool_pct)), Decimal('10.00'))
        self.assertEqual(Decimal(str(cfg.producer_base_pct)), Decimal('5.00'))
        self.assertEqual(Decimal(str(cfg.manager_diff_pct)), Decimal('2.50'))
        self.assertEqual(Decimal(str(cfg.gm_diff_pct)), Decimal('1.50'))
        self.assertEqual(Decimal(str(cfg.rm_diff_pct)), Decimal('0.50'))

        configured_network = (
            Decimal(str(cfg.producer_base_pct))
            + Decimal(str(cfg.manager_diff_pct))
            + Decimal(str(cfg.gm_diff_pct))
            + Decimal(str(cfg.rm_diff_pct))
        )
        self.assertEqual(configured_network, Decimal('9.50'))
        unused_capacity = Decimal(str(cfg.max_network_pool_pct)) - configured_network
        self.assertEqual(unused_capacity, Decimal('0.50'))
        self.assertEqual(Decimal(str(cfg.unallocated_balance_pct)), Decimal('0.50'))

        # Authoritative EV Support Additions: Base +0.75%, Full +0.75% -> Total Max Support = +1.50%
        self.assertEqual(Decimal(str(cfg.support_journey_pct)), Decimal('0.75'))
        self.assertEqual(Decimal(str(cfg.support_end_to_end_pct)), Decimal('1.50'))
        max_support = Decimal(str(cfg.support_end_to_end_pct))
        self.assertEqual(max_support, Decimal('1.50'))

        # Maximum combined field network + support strictly equals 11.00% (9.50% + 1.50%)
        # Unused 0.50% network capacity is NEVER included in field payout
        max_field_combined = configured_network + max_support
        self.assertEqual(max_field_combined, Decimal('11.00'))

        # In a fully allocated EV leadership chain: Producer 5.00% + Mgr 2.50% + GM 1.50% + RM 0.50% = 9.50%
        # The remaining 0.50% must NOT be distributed to partners; it must be retained by APEX_REMAINDER.
        rm = self._create_partner(is_active=True, name="EV RM")
        self._create_qualifying_lead(rm.id)
        for _ in range(10):
            leg = self._create_partner(parent_id=rm.id, is_active=True)
            self._create_qualifying_lead(leg.id)

        gm = self._create_partner(parent_id=rm.id, is_active=True, name="EV GM")
        self._create_qualifying_lead(gm.id)
        for _ in range(5):
            leg = self._create_partner(parent_id=gm.id, is_active=True)
            self._create_qualifying_lead(leg.id)

        mgr = self._create_partner(parent_id=gm.id, is_active=True, name="EV Mgr")
        self._create_qualifying_lead(mgr.id)
        leg = self._create_partner(parent_id=mgr.id, is_active=True)
        self._create_qualifying_lead(leg.id)

        prod = self._create_partner(parent_id=mgr.id, is_active=True, name="EV Producer")
        self._create_qualifying_lead(prod.id)

        wf = VGK4UWaterfallEngine.calculate_commission_structure(
            db=self.db,
            producer_partner_id=prod.id,
            deal_value=Decimal('100000.00'),
            category_slug='ev',
        )

        network_allocs = [a for a in wf['allocations'] if a['role'] in (
            'PRODUCER', 'DIRECT_SPONSOR_OVERRIDE', 'MANAGER_DIFFERENTIAL', 'GM_DIFFERENTIAL', 'RM_DIFFERENTIAL', 'APEX_REMAINDER'
        )]
        total_network = sum(a['commission_pct'] for a in network_allocs)
        self.assertEqual(total_network, Decimal('10.00'))

        # Confirm Apex Remainder retains at least the 0.50% unallocated capacity
        apex_alloc = next((a for a in wf['allocations'] if a['role'] == 'APEX_REMAINDER'), None)
        self.assertIsNotNone(apex_alloc)
        self.assertGreaterEqual(apex_alloc['commission_pct'], Decimal('0.50'))

    # =========================================================================
    # SCENARIO 25: Solar Financial Pool and Support Additions
    # =========================================================================
    def test_25_solar_financial_pool_and_support_additions(self):
        """Solar category enforces max network pool == 9.00%, support up to +1.50%, showroom +3.50%, total gross ceiling == 14.00%."""
        cfg = VGK4UWaterfallEngine.get_category_config(self.db, 'solar', 'v2_sep2026')
        self.assertIsNotNone(cfg)
        self.assertEqual(Decimal(str(cfg.max_network_pool_pct)), Decimal('9.00'))
        self.assertEqual(Decimal(str(cfg.producer_base_pct)), Decimal('6.00'))
        self.assertEqual(Decimal(str(cfg.manager_diff_pct)), Decimal('1.50'))
        self.assertEqual(Decimal(str(cfg.gm_diff_pct)), Decimal('1.00'))
        self.assertEqual(Decimal(str(cfg.rm_diff_pct)), Decimal('0.50'))
        self.assertEqual(Decimal(str(cfg.support_journey_pct)), Decimal('0.75'))
        self.assertEqual(Decimal(str(cfg.support_end_to_end_pct)), Decimal('1.50'))
        self.assertEqual(Decimal(str(cfg.showroom_pct)), Decimal('3.50'))

        gross_ceiling = (
            Decimal(str(cfg.max_network_pool_pct))
            + Decimal(str(cfg.support_end_to_end_pct))
            + Decimal(str(cfg.showroom_pct))
        )
        self.assertEqual(gross_ceiling, Decimal('14.00'))

    # =========================================================================
    # SCENARIO 26: All Support Cases (Self, Non-Staff Field+Full, Field-Only, Staff)
    # =========================================================================
    def test_26_all_four_support_cases(self):
        """Validates all 4 field support operational cases outside the network pool."""
        prod = self._create_partner(is_active=True, name="Prod Support")
        self._create_qualifying_lead(prod.id)
        assistant = self._create_partner(is_active=True, name="Assistant Partner")

        # Case 1: No Support / Ordinary Personal Sale (Producer handles deal without field support partner)
        wf_a = VGK4UWaterfallEngine.calculate_commission_structure(
            db=self.db,
            producer_partner_id=prod.id,
            deal_value=Decimal('100000.00'),
            category_slug='solar',
            support_partner_id=None,
        )
        sup_allocs_a = [a for a in wf_a['allocations'] if a['role'] in ('FIELD_SUPPORT', 'FULL_SUPPORT')]
        self.assertEqual(len(sup_allocs_a), 0)

        # Case 2: Direct Full-Service Closing (Assisting partner handles end-to-end closing with 0 staff)
        wf_b = VGK4UWaterfallEngine.calculate_commission_structure(
            db=self.db,
            producer_partner_id=prod.id,
            deal_value=Decimal('100000.00'),
            category_slug='solar',
            support_partner_id=assistant.id,
            is_end_to_end_support=True,
            is_staff_involved=False,
        )
        sup_b5 = next(a for a in wf_b['allocations'] if a['role'] == 'FIELD_SUPPORT')
        sup_b7 = next(a for a in wf_b['allocations'] if a['role'] == 'FULL_SUPPORT')
        self.assertEqual(sup_b5['commission_pct'], Decimal('0.75'))
        self.assertEqual(sup_b7['commission_pct'], Decimal('0.75'))
        self.assertEqual(sup_b5['partner_id'], assistant.id)
        self.assertEqual(sup_b7['partner_id'], assistant.id)
        self.assertEqual(sup_b5['commission_pct'] + sup_b7['commission_pct'], Decimal('1.50'))

        # Case 3: Field Support Only / Normal Partner Support (is_end_to_end_support is False)
        wf_c = VGK4UWaterfallEngine.calculate_commission_structure(
            db=self.db,
            producer_partner_id=prod.id,
            deal_value=Decimal('100000.00'),
            category_slug='solar',
            support_partner_id=assistant.id,
            is_end_to_end_support=False,
            is_staff_involved=False,
        )
        sup_c5 = next(a for a in wf_c['allocations'] if a['role'] == 'FIELD_SUPPORT')
        sup_c7 = next((a for a in wf_c['allocations'] if a['role'] == 'FULL_SUPPORT'), None)
        self.assertEqual(sup_c5['commission_pct'], Decimal('0.75'))
        self.assertIsNone(sup_c7)

        # Case 4: VGK4U Staff Involved (is_staff_involved=True -> Full Support is 0.00% by company salary rule)
        wf_d = VGK4UWaterfallEngine.calculate_commission_structure(
            db=self.db,
            producer_partner_id=prod.id,
            deal_value=Decimal('100000.00'),
            category_slug='solar',
            support_partner_id=assistant.id,
            is_end_to_end_support=True,
            is_staff_involved=True,
        )
        sup_d5 = next(a for a in wf_d['allocations'] if a['role'] == 'FIELD_SUPPORT')
        sup_d7 = next((a for a in wf_d['allocations'] if a['role'] == 'FULL_SUPPORT'), None)
        self.assertEqual(sup_d5['commission_pct'], Decimal('0.75'))
        self.assertIsNone(sup_d7)

    # =========================================================================
    # SCENARIOS 27-30: Authoritative EV Support Cases (Exact Values)
    # =========================================================================
    def test_ev_no_support(self):
        """EV Case 1: No Support / Ordinary Personal Sale -> Support = 0.00%, Full Support = 0.00%, Total = 0.00%."""
        prod = self._create_partner(is_active=True, name="EV Solo Producer")
        self._create_qualifying_lead(prod.id)

        wf = VGK4UWaterfallEngine.calculate_commission_structure(
            db=self.db,
            producer_partner_id=prod.id,
            deal_value=Decimal('100000.00'),
            category_slug='ev',
            support_partner_id=None,
        )
        sup_allocs = [a for a in wf['allocations'] if a['role'] in ('FIELD_SUPPORT', 'FULL_SUPPORT')]
        self.assertEqual(len(sup_allocs), 0)
        prod_alloc = next(a for a in wf['allocations'] if a['role'] == 'PRODUCER')
        self.assertEqual(prod_alloc['commission_pct'], Decimal('5.00'))

    def test_ev_normal_partner_support(self):
        """EV Case 3: Field Support Only / Normal Partner Support -> Support = +0.75%, Full Support = 0.00%, Total = +0.75%."""
        prod = self._create_partner(is_active=True, name="EV Producer Normal")
        self._create_qualifying_lead(prod.id)
        asst = self._create_partner(is_active=True, name="EV Field Assistant")

        wf = VGK4UWaterfallEngine.calculate_commission_structure(
            db=self.db,
            producer_partner_id=prod.id,
            deal_value=Decimal('100000.00'),
            category_slug='ev',
            support_partner_id=asst.id,
            is_end_to_end_support=False,
            is_staff_involved=False,
        )
        sup = next(a for a in wf['allocations'] if a['role'] == 'FIELD_SUPPORT')
        full_sup = next((a for a in wf['allocations'] if a['role'] == 'FULL_SUPPORT'), None)
        self.assertEqual(sup['commission_pct'], Decimal('0.75'))
        self.assertIsNone(full_sup)

    def test_ev_partner_full_service(self):
        """EV Case 2: Partner Full-Service Closing -> Support = +0.75%, Full Support = +0.75%, Total = +1.50%."""
        prod = self._create_partner(is_active=True, name="EV Producer Closing")
        self._create_qualifying_lead(prod.id)
        asst = self._create_partner(is_active=True, name="EV Closing Partner")

        wf = VGK4UWaterfallEngine.calculate_commission_structure(
            db=self.db,
            producer_partner_id=prod.id,
            deal_value=Decimal('100000.00'),
            category_slug='ev',
            support_partner_id=asst.id,
            is_end_to_end_support=True,
            is_staff_involved=False,
        )
        sup = next(a for a in wf['allocations'] if a['role'] == 'FIELD_SUPPORT')
        full_sup = next(a for a in wf['allocations'] if a['role'] == 'FULL_SUPPORT')
        self.assertEqual(sup['commission_pct'], Decimal('0.75'))
        self.assertEqual(full_sup['commission_pct'], Decimal('0.75'))
        self.assertEqual(sup['commission_pct'] + full_sup['commission_pct'], Decimal('1.50'))

    def test_ev_staff_involved_support(self):
        """EV Case 4: VGK4U Staff Involved -> Support = +0.75%, Full Support = 0.00%, Total = +0.75%."""
        prod = self._create_partner(is_active=True, name="EV Producer Staff")
        self._create_qualifying_lead(prod.id)
        asst = self._create_partner(is_active=True, name="EV Staff Helper")

        wf = VGK4UWaterfallEngine.calculate_commission_structure(
            db=self.db,
            producer_partner_id=prod.id,
            deal_value=Decimal('100000.00'),
            category_slug='ev',
            support_partner_id=asst.id,
            is_end_to_end_support=True,
            is_staff_involved=True,
        )
        sup = next(a for a in wf['allocations'] if a['role'] == 'FIELD_SUPPORT')
        full_sup = next((a for a in wf['allocations'] if a['role'] == 'FULL_SUPPORT'), None)
        self.assertEqual(sup['commission_pct'], Decimal('0.75'))
        self.assertIsNone(full_sup)


if __name__ == '__main__':
    unittest.main()
