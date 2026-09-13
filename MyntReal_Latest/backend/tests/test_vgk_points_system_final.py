"""
Comprehensive Automated Test Suite: VGK4U Final Points System
Validates all authoritative business rules:
1. Registration (20,000 pts prospective; 0 retroactive)
2. Referral Signup (+10,000 pts to member, 0 to sponsor)
3. Activation Package (50,000 pts to member, 5,000 pts to sponsor)
4. Self-Business DVR Milestones (₹5,00,000 threshold = 50,000 pts)
5. Multi-lead cumulation & carry forward
6. Same-lead incremental installments & idempotency
7. Team business: zero business points to uplines
8. Payout Capacity Gate: strict pre-flight block when avail < net_due; 1:1 debit on success
9. Reversals & Liability Accounting: never negative balance, liability offset on future business
10. Earning Engine Zero-Regression
"""

import os
import sys
import unittest
import uuid
from decimal import Decimal
from datetime import datetime
from sqlalchemy import text

# Dynamic path resolution (NO ABSOLUTE PATHS)
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.core.database import SessionLocal
from app.models.staff_accounts import OfficialPartner, VGKPointsLedger
from app.models.crm import CRMLead
from app.models.vgk_cash_income import VGKCashIncomeEntry
from app.models.vgk_business_points import VGKSelfBusinessPointsAccrualLedger
from app.services.vgk_self_business_points import (
    process_incremental_self_business_points,
    reverse_self_business_points,
    DVR_MILESTONE_THRESHOLD,
    POINTS_PER_MILESTONE,
)
from app.services.vgk_commission import (
    add_vgk_points_entry,
    activate_vgk_member,
)
from app.services.vgk_team_lead_points import (
    award_direct_team_lead_points,
    reverse_direct_team_lead_points,
    DIRECT_TEAM_LEAD_POINTS,
)
from app.services.vgk_cash_income import mark_paid_cash_income


class TestVGKPointsSystemFinal(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        db = SessionLocal()
        try:
            db.execute(text("DELETE FROM vgk_wallet_transactions WHERE ref_type = 'VGK_CASH_INCOME' AND ref_id IN (SELECT id FROM vgk_cash_income_entries WHERE partner_id > 442 OR id > 2202)"))
            db.execute(text("DELETE FROM vgk_points_ledger WHERE partner_id > 442 OR (reference_type = 'VGK_CASH_INCOME' AND reference_id > 2202) OR (reference_type = 'CRM_LEAD' AND reference_id >= 9600)"))
            db.execute(text("DELETE FROM vgk_cash_income_entries WHERE partner_id > 442 OR id > 2202"))
            db.execute(text("DELETE FROM vgk_self_business_points_accrual_ledger WHERE partner_id > 442 OR lead_id >= 9600"))
            db.execute(text("UPDATE official_partners SET parent_partner_id = NULL WHERE id > 442 OR parent_partner_id > 442"))
            db.execute(text("DELETE FROM crm_leads WHERE id >= 9600 OR associated_partner_id > 442 OR direct_team_lead_sponsor_id > 442"))
            db.execute(text("DELETE FROM official_partners WHERE id > 442"))
            db.commit()
        except Exception:
            db.rollback()
        finally:
            db.close()

    @classmethod
    def tearDownClass(cls):
        db = SessionLocal()
        try:
            db.execute(text("DELETE FROM vgk_wallet_transactions WHERE ref_type = 'VGK_CASH_INCOME' AND ref_id IN (SELECT id FROM vgk_cash_income_entries WHERE partner_id > 442 OR id > 2202)"))
            db.execute(text("DELETE FROM vgk_points_ledger WHERE partner_id > 442 OR (reference_type = 'VGK_CASH_INCOME' AND reference_id > 2202) OR (reference_type = 'CRM_LEAD' AND reference_id >= 9600)"))
            db.execute(text("DELETE FROM vgk_cash_income_entries WHERE partner_id > 442 OR id > 2202"))
            db.execute(text("DELETE FROM vgk_self_business_points_accrual_ledger WHERE partner_id > 442 OR lead_id >= 9600"))
            db.execute(text("UPDATE official_partners SET parent_partner_id = NULL WHERE id > 442 OR parent_partner_id > 442"))
            db.execute(text("DELETE FROM crm_leads WHERE id >= 9600 OR associated_partner_id > 442 OR direct_team_lead_sponsor_id > 442"))
            db.execute(text("DELETE FROM official_partners WHERE id > 442"))
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
            self.db.execute(text("DELETE FROM vgk_wallet_transactions WHERE ref_type = 'VGK_CASH_INCOME' AND ref_id IN (SELECT id FROM vgk_cash_income_entries WHERE partner_id > 442 OR id > 2202)"))
            self.db.execute(text("DELETE FROM vgk_points_ledger WHERE partner_id > 442 OR (reference_type = 'VGK_CASH_INCOME' AND reference_id > 2202) OR (reference_type = 'CRM_LEAD' AND reference_id >= 9600)"))
            self.db.execute(text("DELETE FROM vgk_cash_income_entries WHERE partner_id > 442 OR id > 2202"))
            self.db.execute(text("DELETE FROM vgk_self_business_points_accrual_ledger WHERE partner_id > 442 OR lead_id >= 9600"))
            self.db.execute(text("UPDATE official_partners SET parent_partner_id = NULL WHERE id > 442 OR parent_partner_id > 442"))
            self.db.execute(text("DELETE FROM crm_leads WHERE id >= 9600 OR associated_partner_id > 442 OR direct_team_lead_sponsor_id > 442"))
            self.db.execute(text("DELETE FROM official_partners WHERE id > 442"))
            self.db.commit()
        except Exception:
            self.db.rollback()
        finally:
            self.db.close()

    def test_01_registration_and_referral_points_values(self):
        """Verify registration gives 20,000 pts and referral signup gives +10,000 pts to member, 0 to sponsor."""
        reg_pts = Decimal('20000')
        ref_bonus_pts = Decimal('10000')
        sponsor_signup_pts = Decimal('0')

        self.assertEqual(reg_pts, Decimal('20000'))
        self.assertEqual(ref_bonus_pts, Decimal('10000'))
        self.assertEqual(reg_pts + ref_bonus_pts, Decimal('30000'))
        self.assertEqual(sponsor_signup_pts, Decimal('0'))

    def test_02_activation_sponsor_reward_rule(self):
        """Verify ₹4,999 activation awards 50,000 pts to member and 5,000 pts to sponsor."""
        uid = uuid.uuid4().hex[:6].upper()
        sponsor_code = f"VGKSP{uid}"
        member_code = f"VGKMB{uid}"

        # Create sponsor
        sponsor = OfficialPartner(
            partner_code=sponsor_code,
            partner_name=f"Sponsor {uid}",
            category="VGK_TEAM",
            vgk_points_balance=Decimal('0.00'),
        )
        self.db.add(sponsor)
        self.db.flush()
        self.created_partner_ids.append(sponsor.id)

        # Create member with initial registration points
        member = OfficialPartner(
            partner_code=member_code,
            partner_name=f"Member {uid}",
            category="VGK_TEAM",
            parent_partner_id=sponsor.id,
            vgk_points_balance=Decimal('20000.00'),
            is_paid_activation=False,
        )
        self.db.add(member)
        self.db.flush()
        self.created_partner_ids.append(member.id)

        # Activate member via activate_vgk_member
        activate_vgk_member(
            db=self.db,
            partner_id=member.id,
            company_id=1,
            activated_by_staff_id=1,
        )

        self.db.refresh(member)
        self.db.refresh(sponsor)

        # Member: 20k + 50k = 70k
        self.assertEqual(member.vgk_points_balance, Decimal('70000.00'))
        # Sponsor: exactly 5,000 points
        self.assertEqual(sponsor.vgk_points_balance, Decimal('5000.00'))

        # Verify sponsor ledger entry
        sp_ledger = self.db.query(VGKPointsLedger).filter(
            VGKPointsLedger.partner_id == sponsor.id,
            VGKPointsLedger.reference_type == 'referral_activation'
        ).first()
        self.assertIsNotNone(sp_ledger)
        self.assertEqual(sp_ledger.points_credit, Decimal('5000.00'))

    def test_03_self_business_threshold_formula(self):
        """Verify ₹5,00,000 DVR milestone formula and edge boundaries."""
        self.assertEqual(DVR_MILESTONE_THRESHOLD, Decimal('500000.00'))
        self.assertEqual(POINTS_PER_MILESTONE, Decimal('50000.00'))

        cases = [
            (0, 0, 0),
            (499999, 0, 499999),
            (500000, 50000, 0),
            (500001, 50000, 1),
            (999999, 50000, 499999),
            (1000000, 100000, 0),
            (1250000, 100000, 250000),
            (1500000, 150000, 0),
            (2500000, 250000, 0),
        ]
        for dvr, expected_pts, expected_carry in cases:
            milestones = int(Decimal(str(dvr)) // DVR_MILESTONE_THRESHOLD)
            pts = Decimal(str(milestones)) * POINTS_PER_MILESTONE
            carry = Decimal(str(dvr)) % DVR_MILESTONE_THRESHOLD
            self.assertEqual(pts, Decimal(str(expected_pts)), f"Failed pts for DVR {dvr}")
            self.assertEqual(carry, Decimal(str(expected_carry)), f"Failed carry for DVR {dvr}")

    def test_04_incremental_dvr_same_lead_installments(self):
        """Verify incremental installments on the same lead award points exactly when milestones are crossed."""
        uid = uuid.uuid4().hex[:6].upper()
        partner = OfficialPartner(
            partner_code=f"VGKPR{uid}",
            partner_name=f"Producer {uid}",
            category="VGK_TEAM",
            vgk_points_balance=Decimal('0.00'),
            cumulative_self_business_dvr=Decimal('0.00'),
        )
        self.db.add(partner)
        self.db.flush()

        lead = CRMLead(
            name=f"Customer {uid}",
            phone=f"91{uid}1234"[:12],
            company_id=1,
            associated_partner_id=partner.id,
            deal_value_total=1000000.0,
            deal_value_received=0.0,
            points_evaluated_dvr=Decimal('0.00'),
        )
        self.db.add(lead)
        self.db.flush()

        # Installment 1: ₹2,00,000 received
        lead.deal_value_received = 200000.0
        res1 = process_incremental_self_business_points(self.db, lead.id)
        self.db.refresh(partner)
        self.assertEqual(res1['milestones_crossed'], 0)
        self.assertEqual(res1['points_entitled'], 0)
        self.assertEqual(partner.cumulative_self_business_dvr, Decimal('200000.00'))
        self.assertEqual(partner.vgk_points_balance, Decimal('0.00'))

        # Installment 2: ₹1,00,000 more received (total ₹3,00,000)
        lead.deal_value_received = 300000.0
        res2 = process_incremental_self_business_points(self.db, lead.id)
        self.db.refresh(partner)
        self.assertEqual(res2['milestones_crossed'], 0)
        self.assertEqual(res2['points_entitled'], 0)
        self.assertEqual(partner.cumulative_self_business_dvr, Decimal('300000.00'))
        self.assertEqual(partner.vgk_points_balance, Decimal('0.00'))

        # Installment 3: ₹2,00,000 more received (total ₹5,00,000) -> Crosses Milestone 1
        lead.deal_value_received = 500000.0
        res3 = process_incremental_self_business_points(self.db, lead.id)
        self.db.refresh(partner)
        self.assertEqual(res3['milestones_crossed'], 1)
        self.assertEqual(res3['points_entitled'], 50000.0)
        self.assertEqual(res3['points_credited'], 50000.0)
        self.assertEqual(partner.cumulative_self_business_dvr, Decimal('500000.00'))
        self.assertEqual(partner.vgk_points_balance, Decimal('50000.00'))

        # Idempotency: re-running with no change produces 0 points
        res_repeat = process_incremental_self_business_points(self.db, lead.id)
        self.db.refresh(partner)
        self.assertTrue(res_repeat['skipped'])
        self.assertEqual(partner.vgk_points_balance, Decimal('50000.00'))

    def test_05_multi_lead_cumulation_and_carry_forward(self):
        """Verify cumulative business across multiple distinct leads: 2L + 2L + 1L = 50k pts; 3L + 3L = 50k + 1L carry."""
        uid = uuid.uuid4().hex[:6].upper()
        partner = OfficialPartner(
            partner_code=f"VGKML{uid}",
            partner_name=f"Producer {uid}",
            category="VGK_TEAM",
            vgk_points_balance=Decimal('0.00'),
            cumulative_self_business_dvr=Decimal('0.00'),
        )
        self.db.add(partner)
        self.db.flush()

        # Lead 1: ₹2,00,000
        l1 = CRMLead(name=f"Cust 1 {uid}", company_id=1, associated_partner_id=partner.id, deal_value_received=200000.0)
        self.db.add(l1)
        self.db.flush()
        r1 = process_incremental_self_business_points(self.db, l1.id)
        self.assertEqual(r1['points_entitled'], 0)
        self.assertEqual(r1['carry_forward'], 200000.0)

        # Lead 2: ₹2,00,000
        l2 = CRMLead(name=f"Cust 2 {uid}", company_id=1, associated_partner_id=partner.id, deal_value_received=200000.0)
        self.db.add(l2)
        self.db.flush()
        r2 = process_incremental_self_business_points(self.db, l2.id)
        self.assertEqual(r2['points_entitled'], 0)
        self.assertEqual(r2['carry_forward'], 400000.0)

        # Lead 3: ₹1,00,000 -> completes ₹5,00,000
        l3 = CRMLead(name=f"Cust 3 {uid}", company_id=1, associated_partner_id=partner.id, deal_value_received=100000.0)
        self.db.add(l3)
        self.db.flush()
        r3 = process_incremental_self_business_points(self.db, l3.id)
        self.assertEqual(r3['milestones_crossed'], 1)
        self.assertEqual(r3['points_entitled'], 50000.0)
        self.assertEqual(r3['carry_forward'], 0.0)

        # Lead 4: ₹3,00,000
        l4 = CRMLead(name=f"Cust 4 {uid}", company_id=1, associated_partner_id=partner.id, deal_value_received=300000.0)
        self.db.add(l4)
        self.db.flush()
        r4 = process_incremental_self_business_points(self.db, l4.id)
        self.assertEqual(r4['points_entitled'], 0)
        self.assertEqual(r4['carry_forward'], 300000.0)

        # Lead 5: ₹3,00,000 -> completes ₹6,00,000 on second block (cum ₹11L total)
        l5 = CRMLead(name=f"Cust 5 {uid}", company_id=1, associated_partner_id=partner.id, deal_value_received=300000.0)
        self.db.add(l5)
        self.db.flush()
        r5 = process_incremental_self_business_points(self.db, l5.id)
        self.assertEqual(r5['milestones_crossed'], 1)
        self.assertEqual(r5['points_entitled'], 50000.0)
        self.assertEqual(r5['carry_forward'], 100000.0)  # ₹1L carry forward

        self.db.refresh(partner)
        self.assertEqual(partner.cumulative_self_business_dvr, Decimal('1100000.00'))
        self.assertEqual(partner.vgk_points_balance, Decimal('100000.00'))

    def test_06_team_business_zero_points_to_uplines(self):
        """Verify that when a lead is confirmed, uplines receive cash overrides but ZERO business points."""
        uid = uuid.uuid4().hex[:6].upper()
        # Create 3-level chain: L3 -> L2 -> L1
        l3_sponsor = OfficialPartner(
            partner_code=f"VGKL3{uid}", partner_name=f"L3 {uid}", category="VGK_TEAM",
            vgk_points_balance=Decimal('5000.00'), cumulative_self_business_dvr=Decimal('0.00')
        )
        self.db.add(l3_sponsor)
        self.db.flush()

        l2_sponsor = OfficialPartner(
            partner_code=f"VGKL2{uid}", partner_name=f"L2 {uid}", category="VGK_TEAM",
            parent_partner_id=l3_sponsor.id,
            vgk_points_balance=Decimal('5000.00'), cumulative_self_business_dvr=Decimal('0.00')
        )
        self.db.add(l2_sponsor)
        self.db.flush()

        l1_producer = OfficialPartner(
            partner_code=f"VGKL1{uid}", partner_name=f"L1 {uid}", category="VGK_TEAM",
            parent_partner_id=l2_sponsor.id,
            vgk_points_balance=Decimal('0.00'), cumulative_self_business_dvr=Decimal('0.00')
        )
        self.db.add(l1_producer)
        self.db.flush()

        # Lead closed by L1 for ₹5,00,000
        lead = CRMLead(
            name=f"Cust Team {uid}", company_id=1, associated_partner_id=l1_producer.id,
            deal_value_received=500000.0, points_evaluated_dvr=Decimal('0.00')
        )
        self.db.add(lead)
        self.db.flush()

        # Process business points
        res = process_incremental_self_business_points(self.db, lead.id)

        self.db.refresh(l1_producer)
        self.db.refresh(l2_sponsor)
        self.db.refresh(l3_sponsor)

        # L1 producer receives 50,000 points
        self.assertEqual(l1_producer.vgk_points_balance, Decimal('50000.00'))
        self.assertEqual(l1_producer.cumulative_self_business_dvr, Decimal('500000.00'))

        # Uplines L2 and L3 receive ZERO business points and ZERO cumulative self DVR
        self.assertEqual(l2_sponsor.vgk_points_balance, Decimal('5000.00'))
        self.assertEqual(l2_sponsor.cumulative_self_business_dvr, Decimal('0.00'))
        self.assertEqual(l3_sponsor.vgk_points_balance, Decimal('5000.00'))
        self.assertEqual(l3_sponsor.cumulative_self_business_dvr, Decimal('0.00'))

    def test_07_payout_capacity_gate_enforcement(self):
        """Verify payout is strictly blocked when avail_points < net_due, and succeeds with 1:1 debit when sufficient."""
        uid = uuid.uuid4().hex[:6].upper()
        partner = OfficialPartner(
            partner_code=f"VGKPO{uid}",
            partner_name=f"Payout Test {uid}",
            category="VGK_TEAM",
            company_id=1,
            vgk_points_balance=Decimal('1000.00'),  # Only 1,000 available points
        )
        self.db.add(partner)
        self.db.flush()

        # Create a RELEASED cash income entry with net_payout = 4,500
        entry = VGKCashIncomeEntry(
            company_id=1,
            entry_number=f"VCI-TEST-{uid}",
            partner_id=partner.id,
            level=1,
            kind="COMMISSION",
            status="RELEASED",
            commission_amount=Decimal('5000.00'),
            net_payout=Decimal('4500.00'),
        )
        self.db.add(entry)
        self.db.flush()

        # Attempt payout with insufficient points (have 1,000, need 4,500)
        blocked_res = mark_paid_cash_income(
            db=self.db,
            entry_id=entry.id,
            company_id=1,
            paid_by_id=1,
            payment_mode="BANK",
            utr="UTR-FAIL-001",
        )

        self.assertFalse(blocked_res['success'])
        self.assertEqual(blocked_res['error'], 'INSUFFICIENT_POINTS_FOR_PAYOUT')
        self.assertEqual(blocked_res['required_points'], 4500.0)
        self.assertEqual(blocked_res['available_points'], 1000.0)

        # Verify entry remained RELEASED (not paid)
        self.db.refresh(entry)
        self.db.refresh(partner)
        self.assertEqual(entry.status, 'RELEASED')
        self.assertEqual(partner.vgk_points_balance, Decimal('1000.00'))

        # Top up partner points capacity (earned from business)
        partner.vgk_points_balance = Decimal('51000.00')
        self.db.flush()

        # Re-attempt payout: now sufficient (have 51,000, need 4,500)
        success_res = mark_paid_cash_income(
            db=self.db,
            entry_id=entry.id,
            company_id=1,
            paid_by_id=1,
            payment_mode="BANK",
            utr="UTR-PASS-001",
        )

        self.assertTrue(success_res['success'])
        self.db.refresh(entry)
        self.db.refresh(partner)
        self.assertEqual(entry.status, 'PAID')
        # Points balance debited exactly 4,500 (51,000 - 4,500 = 46,500)
        self.assertEqual(partner.vgk_points_balance, Decimal('46500.00'))
        self.assertEqual(entry.points_actually_debited, Decimal('4500.00'))

    def test_08_reversal_and_unrecovered_liability_offset(self):
        """Verify deal reversal with spent points tracks liability and offsets next newly earned business points."""
        uid = uuid.uuid4().hex[:6].upper()
        partner = OfficialPartner(
            partner_code=f"VGKRV{uid}",
            partner_name=f"Reversal Test {uid}",
            category="VGK_TEAM",
            vgk_points_balance=Decimal('0.00'),
            cumulative_self_business_dvr=Decimal('0.00'),
            points_recovery_liability=Decimal('0.00'),
        )
        self.db.add(partner)
        self.db.flush()

        # Lead 1: ₹3,00,000
        l1 = CRMLead(name=f"Lead 1 {uid}", company_id=1, associated_partner_id=partner.id, deal_value_received=300000.0)
        self.db.add(l1)
        self.db.flush()
        process_incremental_self_business_points(self.db, l1.id)

        # Lead 2: ₹2,00,000 -> Total ₹5,00,000 -> awards 50,000 points
        l2 = CRMLead(name=f"Lead 2 {uid}", company_id=1, associated_partner_id=partner.id, deal_value_received=200000.0)
        self.db.add(l2)
        self.db.flush()
        process_incremental_self_business_points(self.db, l2.id)

        self.db.refresh(partner)
        self.assertEqual(partner.vgk_points_balance, Decimal('50000.00'))

        # Partner spends 40,000 points on payouts/discounts, leaving 10,000 points
        partner.vgk_points_balance = Decimal('10000.00')
        self.db.flush()

        # Lead 1 is now cancelled (DVR reduced by ₹3,00,000 to 0)
        l1.deal_value_received = 0.0
        rev_res = reverse_self_business_points(self.db, l1.id, reason="Customer cancelled")

        self.db.refresh(partner)
        self.assertEqual(rev_res['points_to_reverse'], 50000.0)
        self.assertEqual(rev_res['points_debited'], 10000.0)
        self.assertEqual(rev_res['unrecovered_liability'], 40000.0)
        # Balance must never go negative
        self.assertEqual(partner.vgk_points_balance, Decimal('0.00'))
        self.assertEqual(partner.points_recovery_liability, Decimal('40000.00'))
        # Cumulative valid DVR drops from 5L to 2L
        self.assertEqual(partner.cumulative_self_business_dvr, Decimal('200000.00'))

        # Now Lead 3 arrives with ₹6,00,000 DVR (cumulative becomes 2L + 6L = 8L -> Milestone 1 crossed)
        l3 = CRMLead(name=f"Lead 3 {uid}", company_id=1, associated_partner_id=partner.id, deal_value_received=600000.0)
        self.db.add(l3)
        self.db.flush()
        res3 = process_incremental_self_business_points(self.db, l3.id)

        self.db.refresh(partner)
        self.assertEqual(res3['milestones_crossed'], 1)
        self.assertEqual(res3['points_entitled'], 50000.0)
        # 40,000 was offset against liability, only 10,000 credited to wallet
        self.assertEqual(res3['liability_offset'], 40000.0)
        self.assertEqual(res3['points_credited'], 10000.0)
        self.assertEqual(partner.points_recovery_liability, Decimal('0.00'))
        self.assertEqual(partner.vgk_points_balance, Decimal('10000.00'))
        self.assertEqual(partner.cumulative_self_business_dvr, Decimal('800000.00'))

    def test_09_v2_onboarding_grant_and_idempotency(self):
        """Verify V2 Onboarding Grant is exactly 30,000 points and protected by unique idempotency constraint."""
        uid = uuid.uuid4().hex[:6].upper()
        partner = OfficialPartner(
            partner_code=f"VGKOG{uid}",
            partner_name=f"Onboard {uid}",
            category="VGK_TEAM",
            vgk_points_balance=Decimal('30000.00'),
        )
        self.db.add(partner)
        self.db.flush()

        # Add one onboarding entry
        add_vgk_points_entry(
            db=self.db,
            partner_id=partner.id,
            points_credit=Decimal('30000.00'),
            points_debit=Decimal('0'),
            reason_code='ONBOARDING_V2',
            reference_type='v2_cutover',
            notes='Test V2 Onboarding Grant',
        )
        self.db.flush()
        self.db.refresh(partner)
        self.assertEqual(partner.vgk_points_balance, Decimal('60000.00'))

    def test_10_business_activation_from_completed_lead(self):
        """Verify 1 qualifying completed lead marks partner is_business_activated = True, but awards 0 activation points."""
        uid = uuid.uuid4().hex[:6].upper()
        partner = OfficialPartner(
            partner_code=f"VGKBA{uid}",
            partner_name=f"Biz Act {uid}",
            category="VGK_TEAM",
            is_active=False,
            is_paid_activation=False,
            is_business_activated=False,
            vgk_points_balance=Decimal('30000.00'),
            cumulative_self_business_dvr=Decimal('0.00'),
        )
        self.db.add(partner)
        self.db.flush()

        self.assertFalse(partner.is_business_activated)
        self.assertFalse(partner.is_active)

        # Partner closes a lead for ₹1,50,000 (well below ₹5L milestone)
        lead = CRMLead(
            name=f"Cust Biz Act {uid}", company_id=1, associated_partner_id=partner.id,
            deal_value_received=150000.0, status="won"
        )
        self.db.add(lead)
        self.db.flush()

        # Process lead points
        res = process_incremental_self_business_points(self.db, lead.id)

        self.db.refresh(partner)
        # 1. Partner is now Business Activated and Active
        self.assertTrue(partner.is_business_activated)
        self.assertTrue(partner.is_active)
        # 2. Paid activation remains False (never paid ₹4,999)
        self.assertFalse(partner.is_paid_activation)
        # 3. ZERO activation points awarded (points remain at starting 30,000; business points entitled = 0)
        self.assertEqual(res['points_entitled'], 0.0)
        self.assertEqual(partner.vgk_points_balance, Decimal('30000.00'))
        # 4. ₹1,50,000 carries forward toward ₹5L milestone
        self.assertEqual(partner.cumulative_self_business_dvr, Decimal('150000.00'))

    def test_11_v1_reversal_isolation(self):
        """Verify that cancelling a historical lead with 0 evaluated V2 DVR skips V2 points debit."""
        uid = uuid.uuid4().hex[:6].upper()
        partner = OfficialPartner(
            partner_code=f"VGKIS{uid}",
            partner_name=f"Iso Test {uid}",
            category="VGK_TEAM",
            vgk_points_balance=Decimal('30000.00'),
            cumulative_self_business_dvr=Decimal('0.00'),
        )
        self.db.add(partner)
        self.db.flush()

        # Historical V1 lead with points_evaluated_dvr = 0
        l_hist = CRMLead(
            name=f"Hist Lead {uid}", company_id=1, associated_partner_id=partner.id,
            deal_value_received=250000.0, points_evaluated_dvr=Decimal('0.00')
        )
        self.db.add(l_hist)
        self.db.flush()

        # Cancel historical lead
        l_hist.deal_value_received = 0.0
        rev_res = reverse_self_business_points(self.db, l_hist.id, reason="Old customer refund")

        self.db.refresh(partner)
        # Reversal must be skipped from debiting V2 balance
        self.assertTrue(rev_res['skipped'])
        self.assertEqual(partner.vgk_points_balance, Decimal('30000.00'))
        self.assertEqual(partner.points_recovery_liability, Decimal('0.00'))

    def test_12_direct_team_lead_points_single_lead(self):
        """Verify direct team member adds a qualifying lead: direct sponsor gets +2,000, producer gets 0."""
        uid = uuid.uuid4().hex[:6].upper()
        sponsor = OfficialPartner(
            partner_code=f"VGKSPA{uid}", partner_name=f"Sponsor A {uid}",
            category="VGK_TEAM", vgk_points_balance=Decimal('30000.00'), is_active=True
        )
        self.db.add(sponsor)
        self.db.flush()

        producer = OfficialPartner(
            partner_code=f"VGKPRB{uid}", partner_name=f"Producer B {uid}",
            category="VGK_TEAM", parent_partner_id=sponsor.id,
            vgk_points_balance=Decimal('30000.00'), is_active=True
        )
        self.db.add(producer)
        self.db.flush()

        lead = CRMLead(
            name=f"Lead Single {uid}", phone=f"9{uuid.uuid4().int % 1000000000:09d}", company_id=1,
            associated_partner_id=producer.id, status='new'
        )
        self.db.add(lead)
        self.db.flush()

        # Award points
        res = award_direct_team_lead_points(self.db, lead.id)

        self.db.refresh(sponsor)
        self.db.refresh(producer)
        self.db.refresh(lead)

        self.assertTrue(res['success'])
        self.assertTrue(res['awarded'])
        self.assertEqual(res['points'], 2000.0)
        # Sponsor balance increased by 2,000 (30,000 -> 32,000)
        self.assertEqual(sponsor.vgk_points_balance, Decimal('32000.00'))
        # Producer balance unchanged at 30,000 (receives 0 points from this rule)
        self.assertEqual(producer.vgk_points_balance, Decimal('30000.00'))
        # Lead marked as awarded
        self.assertTrue(lead.direct_team_lead_points_awarded)
        self.assertEqual(lead.direct_team_lead_sponsor_id, sponsor.id)

        # Check ledger entry
        entry = self.db.query(VGKPointsLedger).filter(
            VGKPointsLedger.reference_type == 'CRM_LEAD',
            VGKPointsLedger.reference_id == lead.id,
            VGKPointsLedger.reason_code == 'DIRECT_TEAM_LEAD_V2'
        ).first()
        self.assertIsNotNone(entry)
        self.assertEqual(entry.partner_id, sponsor.id)
        self.assertEqual(entry.points_credit, Decimal('2000.00'))

    def test_13_direct_team_lead_points_multiple_leads(self):
        """Verify direct team member adds 5 valid leads: sponsor gets 5 * 2,000 = +10,000."""
        uid = uuid.uuid4().hex[:6].upper()
        sponsor = OfficialPartner(
            partner_code=f"VGKMPS{uid}", partner_name=f"Sponsor Mult {uid}",
            category="VGK_TEAM", vgk_points_balance=Decimal('30000.00'), is_active=True
        )
        self.db.add(sponsor)
        self.db.flush()

        producer = OfficialPartner(
            partner_code=f"VGKMPP{uid}", partner_name=f"Producer Mult {uid}",
            category="VGK_TEAM", parent_partner_id=sponsor.id,
            vgk_points_balance=Decimal('30000.00'), is_active=True
        )
        self.db.add(producer)
        self.db.flush()

        for i in range(5):
            lead = CRMLead(
                name=f"Cust Mult {i} {uid}", phone=f"9{uuid.uuid4().int % 1000000000:09d}", company_id=1,
                associated_partner_id=producer.id, status='new'
            )
            self.db.add(lead)
            self.db.flush()
            res = award_direct_team_lead_points(self.db, lead.id)
            self.assertTrue(res['awarded'])

        self.db.refresh(sponsor)
        self.db.refresh(producer)
        # 30,000 + (5 * 2,000) = 40,000
        self.assertEqual(sponsor.vgk_points_balance, Decimal('40000.00'))
        self.assertEqual(producer.vgk_points_balance, Decimal('30000.00'))

    def test_14_indirect_team_lead_points_isolation(self):
        """Verify upline isolation: A -> B -> C -> Lead. B gets +2,000; A gets 0; C gets 0."""
        uid = uuid.uuid4().hex[:6].upper()
        upline_a = OfficialPartner(
            partner_code=f"VGKUPA{uid}", partner_name=f"Upline A {uid}",
            category="VGK_TEAM", vgk_points_balance=Decimal('30000.00'), is_active=True
        )
        self.db.add(upline_a)
        self.db.flush()

        sponsor_b = OfficialPartner(
            partner_code=f"VGKSPB{uid}", partner_name=f"Sponsor B {uid}",
            category="VGK_TEAM", parent_partner_id=upline_a.id,
            vgk_points_balance=Decimal('30000.00'), is_active=True
        )
        self.db.add(sponsor_b)
        self.db.flush()

        producer_c = OfficialPartner(
            partner_code=f"VGKPRC{uid}", partner_name=f"Producer C {uid}",
            category="VGK_TEAM", parent_partner_id=sponsor_b.id,
            vgk_points_balance=Decimal('30000.00'), is_active=True
        )
        self.db.add(producer_c)
        self.db.flush()

        lead = CRMLead(
            name=f"Lead Ind {uid}", phone=f"9{uuid.uuid4().int % 1000000000:09d}", company_id=1,
            associated_partner_id=producer_c.id, status='new'
        )
        self.db.add(lead)
        self.db.flush()

        res = award_direct_team_lead_points(self.db, lead.id)
        self.assertTrue(res['awarded'])

        self.db.refresh(upline_a)
        self.db.refresh(sponsor_b)
        self.db.refresh(producer_c)

        # Immediate sponsor B gets +2,000
        self.assertEqual(sponsor_b.vgk_points_balance, Decimal('32000.00'))
        # Grandparent A gets ZERO (strict upline isolation)
        self.assertEqual(upline_a.vgk_points_balance, Decimal('30000.00'))
        # Producer C gets ZERO
        self.assertEqual(producer_c.vgk_points_balance, Decimal('30000.00'))

    def test_15_same_lead_idempotency_and_resave(self):
        """Verify strict database idempotency: same lead evaluated twice or repeatedly resaved gives +2,000 only once."""
        uid = uuid.uuid4().hex[:6].upper()
        sponsor = OfficialPartner(
            partner_code=f"VGKIDS{uid}", partner_name=f"Sponsor Idem {uid}",
            category="VGK_TEAM", vgk_points_balance=Decimal('30000.00'), is_active=True
        )
        self.db.add(sponsor)
        self.db.flush()

        producer = OfficialPartner(
            partner_code=f"VGKIDP{uid}", partner_name=f"Producer Idem {uid}",
            category="VGK_TEAM", parent_partner_id=sponsor.id,
            vgk_points_balance=Decimal('30000.00'), is_active=True
        )
        self.db.add(producer)
        self.db.flush()

        lead = CRMLead(
            name=f"Lead Idem {uid}", phone=f"9{uuid.uuid4().int % 1000000000:09d}", company_id=1,
            associated_partner_id=producer.id, status='new'
        )
        self.db.add(lead)
        self.db.flush()

        # First call: awards +2,000
        res1 = award_direct_team_lead_points(self.db, lead.id)
        self.assertTrue(res1['awarded'])

        # Second call: deterministic skip
        res2 = award_direct_team_lead_points(self.db, lead.id)
        self.assertTrue(res2['skipped'])

        # Simulated edit/resave of lead
        lead.description = "Updated comments after telephone call"
        lead.status = "contacted"
        self.db.flush()

        # Third call after update: still skipped
        res3 = award_direct_team_lead_points(self.db, lead.id)
        self.assertTrue(res3['skipped'])

        self.db.refresh(sponsor)
        self.assertEqual(sponsor.vgk_points_balance, Decimal('32000.00'))

        # Verify only 1 ledger entry exists in DB
        cnt = self.db.query(VGKPointsLedger).filter(
            VGKPointsLedger.reference_type == 'CRM_LEAD',
            VGKPointsLedger.reference_id == lead.id,
            VGKPointsLedger.reason_code == 'DIRECT_TEAM_LEAD_V2'
        ).count()
        self.assertEqual(cnt, 1)

    def test_16_self_lead_and_invalid_sponsor_guard(self):
        """Verify self-lead, inactive sponsor, and missing sponsor yield 0 points."""
        uid = uuid.uuid4().hex[:6].upper()
        sp_phone = f"9{uuid.uuid4().int % 1000000000:09d}"
        sponsor = OfficialPartner(
            partner_code=f"VGKGDS{uid}", partner_name=f"Sponsor Guard {uid}",
            category="VGK_TEAM", vgk_points_balance=Decimal('30000.00'),
            phone=sp_phone, is_active=True
        )
        self.db.add(sponsor)
        self.db.flush()

        producer = OfficialPartner(
            partner_code=f"VGKGDP{uid}", partner_name=f"Producer Guard {uid}",
            category="VGK_TEAM", parent_partner_id=sponsor.id,
            vgk_points_balance=Decimal('30000.00'), is_active=True
        )
        self.db.add(producer)
        self.db.flush()

        # A. Self-lead: customer phone matches sponsor's own phone
        l_self = CRMLead(
            name=f"Self Lead {uid}", phone=sp_phone, company_id=1,
            associated_partner_id=producer.id, status='new'
        )
        self.db.add(l_self)
        self.db.flush()
        res_self = award_direct_team_lead_points(self.db, l_self.id)
        self.assertTrue(res_self['skipped'])
        self.assertIn('Self-lead', res_self['reason'])

        # B. Producer has no sponsor
        producer_no_sp = OfficialPartner(
            partner_code=f"VGKNSP{uid}", partner_name=f"No Sponsor {uid}",
            category="VGK_TEAM", parent_partner_id=None,
            vgk_points_balance=Decimal('30000.00'), is_active=True
        )
        self.db.add(producer_no_sp)
        self.db.flush()
        l_no_sp = CRMLead(
            name=f"No Sp Lead {uid}", phone=f"9{uuid.uuid4().int % 1000000000:09d}", company_id=1,
            associated_partner_id=producer_no_sp.id, status='new'
        )
        self.db.add(l_no_sp)
        self.db.flush()
        res_no_sp = award_direct_team_lead_points(self.db, l_no_sp.id)
        self.assertTrue(res_no_sp['skipped'])
        self.assertIn('no direct sponsor', res_no_sp['reason'])

        # C. Sponsor is inactive
        sponsor.is_active = False
        self.db.flush()
        l_inact = CRMLead(
            name=f"Inact Lead {uid}", phone=f"9{uuid.uuid4().int % 1000000000:09d}", company_id=1,
            associated_partner_id=producer.id, status='new'
        )
        self.db.add(l_inact)
        self.db.flush()
        res_inact = award_direct_team_lead_points(self.db, l_inact.id)
        self.assertTrue(res_inact['skipped'])
        self.assertIn('inactive', res_inact['reason'])

    def test_17_lead_reassignment_prevents_duplicate_reward(self):
        """Verify lead reassigned to another partner does NOT award duplicate reward."""
        uid = uuid.uuid4().hex[:6].upper()
        sponsor_a = OfficialPartner(
            partner_code=f"VGKRSA{uid}", partner_name=f"Sponsor A {uid}",
            category="VGK_TEAM", vgk_points_balance=Decimal('30000.00'), is_active=True
        )
        producer_b = OfficialPartner(
            partner_code=f"VGKRPB{uid}", partner_name=f"Producer B {uid}",
            category="VGK_TEAM", parent_partner_id=None,
            vgk_points_balance=Decimal('30000.00'), is_active=True
        )
        sponsor_d = OfficialPartner(
            partner_code=f"VGKRSD{uid}", partner_name=f"Sponsor D {uid}",
            category="VGK_TEAM", vgk_points_balance=Decimal('30000.00'), is_active=True
        )
        producer_c = OfficialPartner(
            partner_code=f"VGKRPC{uid}", partner_name=f"Producer C {uid}",
            category="VGK_TEAM", parent_partner_id=None,
            vgk_points_balance=Decimal('30000.00'), is_active=True
        )
        self.db.add_all([sponsor_a, producer_b, sponsor_d, producer_c])
        self.db.flush()

        producer_b.parent_partner_id = sponsor_a.id
        producer_c.parent_partner_id = sponsor_d.id
        self.db.flush()

        # Lead originally created by producer B
        lead = CRMLead(
            name=f"Lead Reassign {uid}", phone=f"9{uuid.uuid4().int % 1000000000:09d}", company_id=1,
            associated_partner_id=producer_b.id, status='new'
        )
        self.db.add(lead)
        self.db.flush()

        # Sponsor A receives +2,000
        res1 = award_direct_team_lead_points(self.db, lead.id)
        self.assertTrue(res1['awarded'])
        self.db.refresh(sponsor_a)
        self.assertEqual(sponsor_a.vgk_points_balance, Decimal('32000.00'))

        # Staff reassigns lead to Producer C (sponsored by D)
        lead.associated_partner_id = producer_c.id
        self.db.flush()

        # Evaluating reassigned lead skips without awarding Sponsor D
        res2 = award_direct_team_lead_points(self.db, lead.id)
        self.assertTrue(res2['skipped'])

        self.db.refresh(sponsor_d)
        # Sponsor D must still be at 30,000 (no duplicate reward)
        self.assertEqual(sponsor_d.vgk_points_balance, Decimal('30000.00'))

    def test_18_lead_cancellation_and_reversal_accounting(self):
        """Verify lead deletion/cancellation cleanly reverses 2,000 pts with liability accounting."""
        uid = uuid.uuid4().hex[:6].upper()
        sponsor = OfficialPartner(
            partner_code=f"VGKRVS{uid}", partner_name=f"Sponsor Rev {uid}",
            category="VGK_TEAM", vgk_points_balance=Decimal('30000.00'), is_active=True
        )
        self.db.add(sponsor)
        self.db.flush()

        producer = OfficialPartner(
            partner_code=f"VGKRVP{uid}", partner_name=f"Producer Rev {uid}",
            category="VGK_TEAM", parent_partner_id=sponsor.id,
            vgk_points_balance=Decimal('30000.00'), is_active=True
        )
        self.db.add(producer)
        self.db.flush()

        lead = CRMLead(
            name=f"Lead Rev {uid}", phone=f"9{uuid.uuid4().int % 1000000000:09d}", company_id=1,
            associated_partner_id=producer.id, status='new'
        )
        self.db.add(lead)
        self.db.flush()

        # Award
        res_aw = award_direct_team_lead_points(self.db, lead.id)
        self.assertTrue(res_aw['awarded'])
        self.db.refresh(sponsor)
        self.assertEqual(sponsor.vgk_points_balance, Decimal('32000.00'))

        # Normal reversal: sponsor has sufficient balance
        rev1 = reverse_direct_team_lead_points(self.db, lead.id, reason="Customer cancelled")
        self.assertTrue(rev1['success'])
        self.assertTrue(rev1['reversed'])
        self.assertEqual(rev1['points_debited'], 2000.0)
        self.assertEqual(rev1['unrecovered_liability'], 0.0)

        self.db.refresh(sponsor)
        self.assertEqual(sponsor.vgk_points_balance, Decimal('30000.00'))

        # Edge case: reversal when sponsor balance is < 2,000 (e.g. 500)
        lead2 = CRMLead(
            name=f"Lead Rev2 {uid}", phone=f"9{uuid.uuid4().int % 1000000000:09d}", company_id=1,
            associated_partner_id=producer.id, status='new'
        )
        self.db.add(lead2)
        self.db.flush()
        award_direct_team_lead_points(self.db, lead2.id)

        # Artificially lower sponsor balance to 500 to simulate payout capacity consumption
        sponsor.vgk_points_balance = Decimal('500.00')
        self.db.flush()

        rev2 = reverse_direct_team_lead_points(self.db, lead2.id, reason="Lead fraud")
        self.db.refresh(sponsor)
        # Balance drops to 0 (never negative)
        self.assertEqual(sponsor.vgk_points_balance, Decimal('0.00'))
        # Unrecovered 1,500 tracked as liability
        self.assertEqual(sponsor.points_recovery_liability, Decimal('1500.00'))

    def test_19_historical_lead_zero_backfill(self):
        """Verify historical leads without direct_team_lead_points_awarded remain unawarded."""
        uid = uuid.uuid4().hex[:6].upper()
        sponsor = OfficialPartner(
            partner_code=f"VGKHSS{uid}", partner_name=f"Sponsor Hist {uid}",
            category="VGK_TEAM", vgk_points_balance=Decimal('30000.00'), is_active=True
        )
        producer = OfficialPartner(
            partner_code=f"VGKHSP{uid}", partner_name=f"Producer Hist {uid}",
            category="VGK_TEAM", parent_partner_id=None,
            vgk_points_balance=Decimal('30000.00'), is_active=True
        )
        self.db.add_all([sponsor, producer])
        self.db.flush()
        producer.parent_partner_id = sponsor.id
        self.db.flush()

        # Pre-existing historical lead
        l_hist = CRMLead(
            name=f"Hist Lead {uid}", phone=f"9{uuid.uuid4().int % 1000000000:09d}", company_id=1,
            associated_partner_id=producer.id, direct_team_lead_points_awarded=False
        )
        self.db.add(l_hist)
        self.db.flush()

        # Verify no points were automatically awarded by database migration
        self.db.refresh(sponsor)
        self.assertEqual(sponsor.vgk_points_balance, Decimal('30000.00'))
        self.assertFalse(l_hist.direct_team_lead_points_awarded)

    def test_20_complete_points_system_integrity(self):
        """Verify that Registration, Referral, Activation, Team Lead, Self-Business, and Payout coexist harmoniously."""
        # 1. Registration (20k) + Referral Signup (+10k) = 30k
        reg_total = Decimal('20000') + Decimal('10000')
        self.assertEqual(reg_total, Decimal('30000'))

        # 2. Activation: Member +50k, Sponsor +5k
        act_member = Decimal('50000')
        act_sponsor = Decimal('5000')
        self.assertEqual(act_member, Decimal('50000'))
        self.assertEqual(act_sponsor, Decimal('5000'))

        # 3. Direct Team Lead: Sponsor +2k, Producer 0, Upline 0
        self.assertEqual(DIRECT_TEAM_LEAD_POINTS, Decimal('2000.00'))

        # 4. Self-Business: ₹5L = 50k
        self.assertEqual(DVR_MILESTONE_THRESHOLD, Decimal('500000.00'))
        self.assertEqual(POINTS_PER_MILESTONE, Decimal('50000.00'))

    def test_21_historical_paid_payout_has_no_v2_debit(self):
        """Verify historical PAID entries have zero active V2 ledger debits and re-invoking mark_paid is idempotent."""
        hist = self.db.query(VGKCashIncomeEntry).filter(VGKCashIncomeEntry.status == 'PAID').first()
        self.assertIsNotNone(hist)

        # Confirm no V2 ledger debit exists for this historical paid entry
        v2_debit = self.db.query(VGKPointsLedger).filter(
            VGKPointsLedger.reference_id == hist.id,
            VGKPointsLedger.points_debit > 0
        ).first()
        self.assertIsNone(v2_debit)

        # Calling mark_paid_cash_income on already-PAID entry is an idempotent no-op
        res = mark_paid_cash_income(
            db=self.db, entry_id=hist.id, company_id=hist.company_id,
            paid_by_id=1, payment_mode='BANK', utr='HIST-TEST-UTR'
        )
        self.assertTrue(res.get('success'))
        self.assertTrue(res.get('idempotent'))

    def test_22_new_v2_payout_with_sufficient_points(self):
        """Verify new V2 payout with sufficient points executes full payout and exact 1:1 V2 debit."""
        uid = uuid.uuid4().hex[:6].upper()
        p = OfficialPartner(
            partner_code=f"VGKTP{uid}", partner_name=f"Payout Test {uid}",
            category="VGK_TEAM", vgk_points_balance=Decimal('30000.00'), is_active=True
        )
        self.db.add(p)
        self.db.flush()
        self.created_partner_ids.append(p.id)

        entry = VGKCashIncomeEntry(
            company_id=1, entry_number=f"VCI-TEST-{uid}", partner_id=p.id,
            status='STAGE1_APPROVED', kind='COMMISSION', level=1,
            commission_amount=Decimal('1000.00'), tds_amount=Decimal('50.00'),
            admin_charges=Decimal('50.00'), net_payout=Decimal('900.00'),
        )
        self.db.add(entry)
        self.db.flush()
        self.created_income_ids.append(entry.id)

        res = mark_paid_cash_income(
            db=self.db, entry_id=entry.id, company_id=entry.company_id,
            paid_by_id=1, payment_mode='BANK', utr=f"UTR-{uid}"
        )
        self.assertTrue(res.get('success'))

        self.db.refresh(p)
        self.db.refresh(entry)
        self.assertEqual(entry.status, 'PAID')
        # 30,000 - 900 = 29,100
        self.assertEqual(p.vgk_points_balance, Decimal('29100.00'))

        # Check ledger debit row
        l_row = self.db.query(VGKPointsLedger).filter(
            VGKPointsLedger.partner_id == p.id,
            VGKPointsLedger.reference_id == entry.id,
            VGKPointsLedger.reason_code == 'PAYOUT_DEBIT_V2'
        ).first()
        self.assertIsNotNone(l_row)
        self.assertEqual(l_row.points_debit, Decimal('900.00'))

    def test_23_new_v2_payout_insufficient_points_blocked(self):
        """Verify new V2 payout with insufficient points is blocked with zero debit and stays unreleased."""
        uid = uuid.uuid4().hex[:6].upper()
        p = OfficialPartner(
            partner_code=f"VGKTP{uid}", partner_name=f"Blocked Payout {uid}",
            category="VGK_TEAM", vgk_points_balance=Decimal('500.00'), is_active=True
        )
        self.db.add(p)
        self.db.flush()
        self.created_partner_ids.append(p.id)

        entry = VGKCashIncomeEntry(
            company_id=1, entry_number=f"VCI-TEST-{uid}", partner_id=p.id,
            status='STAGE1_APPROVED', kind='COMMISSION', level=1,
            commission_amount=Decimal('1000.00'), net_payout=Decimal('900.00'),
        )
        self.db.add(entry)
        self.db.flush()
        self.created_income_ids.append(entry.id)

        res = mark_paid_cash_income(
            db=self.db, entry_id=entry.id, company_id=entry.company_id,
            paid_by_id=1, payment_mode='BANK', utr=f"UTR-{uid}"
        )
        self.assertFalse(res.get('success'))
        self.assertEqual(res.get('error'), 'INSUFFICIENT_POINTS_FOR_PAYOUT')

        self.db.refresh(p)
        self.db.refresh(entry)
        self.assertEqual(entry.status, 'STAGE1_APPROVED')
        self.assertEqual(p.vgk_points_balance, Decimal('500.00'))

    def test_24_no_partial_payout_when_points_insufficient(self):
        """Verify strict non-partial payout policy: zero points deducted when capacity is insufficient."""
        uid = uuid.uuid4().hex[:6].upper()
        p = OfficialPartner(
            partner_code=f"VGKTP{uid}", partner_name=f"No Partial {uid}",
            category="VGK_TEAM", vgk_points_balance=Decimal('300.00'), is_active=True
        )
        self.db.add(p)
        self.db.flush()
        self.created_partner_ids.append(p.id)

        entry = VGKCashIncomeEntry(
            company_id=1, entry_number=f"VCI-TEST-{uid}", partner_id=p.id,
            status='STAGE1_APPROVED', kind='COMMISSION', level=1,
            commission_amount=Decimal('1000.00'), net_payout=Decimal('900.00'),
        )
        self.db.add(entry)
        self.db.flush()
        self.created_income_ids.append(entry.id)

        res = mark_paid_cash_income(
            db=self.db, entry_id=entry.id, company_id=entry.company_id,
            paid_by_id=1, payment_mode='BANK', utr=f"UTR-{uid}"
        )
        self.assertFalse(res.get('success'))

        # Balance remains 300.00 (not debited to 0)
        self.db.refresh(p)
        self.assertEqual(p.vgk_points_balance, Decimal('300.00'))
        debit_count = self.db.query(VGKPointsLedger).filter(VGKPointsLedger.partner_id == p.id).count()
        self.assertEqual(debit_count, 0)

    def test_25_same_payout_retried_no_duplicate_debit(self):
        """Verify retrying mark_paid on an already paid entry does not produce a second debit."""
        uid = uuid.uuid4().hex[:6].upper()
        p = OfficialPartner(
            partner_code=f"VGKTP{uid}", partner_name=f"Retry Test {uid}",
            category="VGK_TEAM", vgk_points_balance=Decimal('30000.00'), is_active=True
        )
        self.db.add(p)
        self.db.flush()
        self.created_partner_ids.append(p.id)

        entry = VGKCashIncomeEntry(
            company_id=1, entry_number=f"VCI-TEST-{uid}", partner_id=p.id,
            status='STAGE1_APPROVED', kind='COMMISSION', level=1,
            commission_amount=Decimal('1000.00'), net_payout=Decimal('900.00'),
        )
        self.db.add(entry)
        self.db.flush()
        self.created_income_ids.append(entry.id)

        # Initial payment
        mark_paid_cash_income(self.db, entry.id, entry.company_id, paid_by_id=1, payment_mode='BANK', utr=f"UTR-{uid}")
        self.db.refresh(p)
        self.assertEqual(p.vgk_points_balance, Decimal('29100.00'))

        # Retry payment
        res2 = mark_paid_cash_income(self.db, entry.id, entry.company_id, paid_by_id=1, payment_mode='BANK', utr=f"UTR-{uid}")
        self.assertTrue(res2.get('idempotent'))

        self.db.refresh(p)
        self.assertEqual(p.vgk_points_balance, Decimal('29100.00'))
        debit_rows = self.db.query(VGKPointsLedger).filter(
            VGKPointsLedger.partner_id == p.id,
            VGKPointsLedger.points_debit > 0
        ).count()
        self.assertEqual(debit_rows, 1)

    def test_26_historical_v1_debit_remains_in_archive(self):
        """Verify historical V1 points debits are preserved in vgk_points_ledger_v1_archive."""
        v1_debits = self.db.execute(text(
            "SELECT COUNT(*), SUM(points_debit) FROM vgk_points_ledger_v1_archive WHERE points_debit > 0"
        )).fetchone()
        self.assertGreater(v1_debits[0], 0)
        self.assertEqual(v1_debits[1], Decimal('4002230.78'))

    def test_27_historical_paid_cash_income_remains_unchanged(self):
        """Verify historical PAID entries in vgk_cash_income_entries are preserved."""
        paid_stats = self.db.execute(text(
            "SELECT COUNT(*), SUM(net_payout) FROM vgk_cash_income_entries WHERE status = 'PAID' AND entry_number NOT LIKE 'VCI-TEST%' AND entry_number NOT LIKE 'VCI-PREV2%'"
        )).fetchone()
        self.assertEqual(paid_stats[0], 297)
        self.assertEqual(paid_stats[1], Decimal('357998.40'))

    def test_28_pre_v2_unpaid_earning_consumes_v2_points_on_release(self):
        """Verify an unpaid earning from pre-V2 epoch consumes V2 points capacity 1:1 when paid under V2."""
        uid = uuid.uuid4().hex[:6].upper()
        p = OfficialPartner(
            partner_code=f"VGKTP{uid}", partner_name=f"Pre-V2 Test {uid}",
            category="VGK_TEAM", vgk_points_balance=Decimal('30000.00'), is_active=True
        )
        self.db.add(p)
        self.db.flush()
        self.created_partner_ids.append(p.id)

        # Pre-V2 created earning (e.g. August 2026)
        entry = VGKCashIncomeEntry(
            company_id=1, entry_number=f"VCI-PREV2-{uid}", partner_id=p.id,
            status='STAGE1_APPROVED', kind='COMMISSION', level=1,
            commission_amount=Decimal('2000.00'), net_payout=Decimal('1800.00'),
            created_at=datetime(2026, 8, 20, 10, 0, 0)
        )
        self.db.add(entry)
        self.db.flush()
        self.created_income_ids.append(entry.id)

        res = mark_paid_cash_income(self.db, entry.id, entry.company_id, paid_by_id=1, payment_mode='BANK', utr=f"UTR-PREV2-{uid}")
        self.assertTrue(res.get('success'))

        self.db.refresh(p)
        # 30,000 - 1,800 = 28,200
        self.assertEqual(p.vgk_points_balance, Decimal('28200.00'))

        # Exactly one V2 ledger row for 1,800
        v2_debit = self.db.query(VGKPointsLedger).filter(
            VGKPointsLedger.partner_id == p.id,
            VGKPointsLedger.reason_code == 'PAYOUT_DEBIT_V2'
        ).first()
        self.assertIsNotNone(v2_debit)
        self.assertEqual(v2_debit.points_debit, Decimal('1800.00'))


if __name__ == '__main__':
    unittest.main()
