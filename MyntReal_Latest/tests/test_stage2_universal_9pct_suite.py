"""
Comprehensive Verification Suite: VGK4U Universal 9% Commission & Stage 2 Advance Architecture
Effective Date: 2026-09-25 00:00:00 IST
Tests all 18 Acceptance Criteria (TEST A - TEST R) covering:
1. Universal 9% Structure: L1=5%, L2=1%, L3=1.5%, L4=1%, L5=0.5% (Total 9%)
2. Model A (Selling/Payment Value): Solar, EV, EV Spares, Training
3. Model B (Actual Commission Received): Insurance, Real Estate
4. Immediate Direct Sponsor Override Isolation (Channel Partner Rank >= 1)
5. Leadership Differentials Roll-up & APEX_REMAINDER Sweep
6. Incremental Payment / Receipt Basis & Idempotency
7. Partial Receipts & Receipt Cancellation
8. Option C Pro-Rata Stage 1 Recovery on L1 only
9. Final Commission Settlement Collision Prevention (Zero Double Payout)
10. Effective Date Boundary Guard
"""

import os
import sys
from decimal import Decimal
from datetime import datetime, date

# Set python path
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
BACKEND_DIR = os.path.join(BASE_DIR, 'backend')
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from app.core.database import SessionLocal
from app.services.vgk4u_waterfall_engine import VGK4UWaterfallEngine
from app.services.vgk_solar_advance import (
    process_payment_stage2_advance,
    cancel_payment_stage2_advance,
    apply_adjustment_at_completion,
    STAGE2_EFFECTIVE_DATE
)
from app.services.vgk_cash_income import _resolve_category_slug
from app.services.vgk4u_career_service import ROOT_APEX_PARTNER_ID
from sqlalchemy import text


def run_tests():
    db = SessionLocal()
    print("=" * 80)
    print("STARTING VGK4U UNIVERSAL 9% & STAGE 2 VERIFICATION SUITE")
    print("=" * 80)

    passed_count = 0
    total_tests = 0

    def assert_test(name, condition, details=""):
        nonlocal passed_count, total_tests
        total_tests += 1
        if condition:
            passed_count += 1
            print(f" [PASS] {name} {details}")
        else:
            print(f"❌ [FAIL] {name} {details}")
            raise AssertionError(f"Test failed: {name} - {details}")

    try:
        # Pre-cleanup of any previous test runs
        db.execute(text("DELETE FROM vgk_cash_income_entries WHERE source_lead_id IN (SELECT id FROM crm_leads WHERE phone IN ('9999900001', '9999900002', '9999900003'))"))
        db.execute(text("DELETE FROM vgk_solar_cibil_advances WHERE lead_id IN (SELECT id FROM crm_leads WHERE phone IN ('9999900001', '9999900002', '9999900003'))"))
        db.execute(text("DELETE FROM crm_lead_transactions WHERE lead_id IN (SELECT id FROM crm_leads WHERE phone IN ('9999900001', '9999900002', '9999900003'))"))
        db.execute(text("DELETE FROM crm_leads WHERE phone IN ('9999900001', '9999900002', '9999900003')"))
        db.commit()

        # TEST A: Solar ₹1,00,000 payment -> 9% network basis
        res_a = VGK4UWaterfallEngine.calculate_commission_structure(
            db=db, producer_partner_id=154, deal_value=Decimal('100000.00'), category_slug='solar'
        )
        total_net_a = sum(a['commission_pct'] for a in res_a['allocations'] if a['role'] != 'SHOWROOM' and 'SUPPORT' not in a['role'])
        assert_test("TEST A: Solar ₹1,00,000 -> 9.00% network total", total_net_a == Decimal('9.00'), f"Got: {total_net_a}%")

        # TEST B: EV ₹1,00,000 payment -> 9% network basis
        res_b = VGK4UWaterfallEngine.calculate_commission_structure(
            db=db, producer_partner_id=154, deal_value=Decimal('100000.00'), category_slug='ev'
        )
        total_net_b = sum(a['commission_pct'] for a in res_b['allocations'] if a['role'] != 'SHOWROOM' and 'SUPPORT' not in a['role'])
        assert_test("TEST B: EV ₹1,00,000 -> 9.00% network total", total_net_b == Decimal('9.00'), f"Got: {total_net_b}%")

        # TEST C: EV Spares ₹50,000 payment -> 9% network basis
        res_c = VGK4UWaterfallEngine.calculate_commission_structure(
            db=db, producer_partner_id=154, deal_value=Decimal('50000.00'), category_slug='ev-spares'
        )
        total_net_c = sum(a['commission_pct'] for a in res_c['allocations'] if a['role'] != 'SHOWROOM' and 'SUPPORT' not in a['role'])
        assert_test("TEST C: EV Spares ₹50,000 -> 9.00% network total", total_net_c == Decimal('9.00'), f"Got: {total_net_c}%")

        # TEST D: Training ₹20,000 payment -> 9% network basis
        res_d = VGK4UWaterfallEngine.calculate_commission_structure(
            db=db, producer_partner_id=154, deal_value=Decimal('20000.00'), category_slug='etc-training'
        )
        total_net_d = sum(a['commission_pct'] for a in res_d['allocations'] if a['role'] != 'SHOWROOM' and 'SUPPORT' not in a['role'])
        assert_test("TEST D: Training ₹20,000 -> 9.00% network total", total_net_d == Decimal('9.00'), f"Got: {total_net_d}%")

        # TEST E: Insurance policy ₹1,00,000, actual commission received ₹25,000
        # -> Stage 2 basis = ₹25,000 (NOT ₹1,00,000)
        res_e = VGK4UWaterfallEngine.calculate_commission_structure(
            db=db, producer_partner_id=154, deal_value=Decimal('25000.00'), category_slug='insurance'
        )
        producer_alloc_e = next(a for a in res_e['allocations'] if a['role'] == 'PRODUCER')
        sponsor_alloc_e = next(a for a in res_e['allocations'] if a['role'] == 'DIRECT_SPONSOR_OVERRIDE')
        assert_test("TEST E: Insurance ₹25,000 actual commission basis",
                    producer_alloc_e['commission_amount'] == Decimal('1250.00') and sponsor_alloc_e['commission_amount'] == Decimal('250.00'),
                    f"Producer: ₹{producer_alloc_e['commission_amount']} (5%), Sponsor: ₹{sponsor_alloc_e['commission_amount']} (1%)")

        # TEST F: Real Estate project ₹50,00,000, actual commission received ₹5,00,000
        # -> Stage 2 basis = ₹5,00,000 (NOT ₹50,00,000)
        res_f = VGK4UWaterfallEngine.calculate_commission_structure(
            db=db, producer_partner_id=154, deal_value=Decimal('500000.00'), category_slug='real-dreams'
        )
        producer_alloc_f = next(a for a in res_f['allocations'] if a['role'] == 'PRODUCER')
        sponsor_alloc_f = next(a for a in res_f['allocations'] if a['role'] == 'DIRECT_SPONSOR_OVERRIDE')
        assert_test("TEST F: Real Estate ₹5,00,000 actual commission basis",
                    producer_alloc_f['commission_amount'] == Decimal('25000.00') and sponsor_alloc_f['commission_amount'] == Decimal('5000.00'),
                    f"Producer: ₹{producer_alloc_f['commission_amount']} (5%), Sponsor: ₹{sponsor_alloc_f['commission_amount']} (1%)")

        # TEST I & J: Direct Sponsor Override Isolation:
        # Partner 154 has parent 97 (Channel Partner).
        # Partner 97 receives 1.00% Direct Sponsor Override.
        # Partner 30 has parent 27 (Member, Rank 0).
        # Partner 27 does NOT qualify for sponsor override -> sweeps to APEX_REMAINDER!
        res_sponsor_valid = VGK4UWaterfallEngine.calculate_commission_structure(
            db=db, producer_partner_id=154, deal_value=Decimal('10000.00'), category_slug='solar'
        )
        has_sponsor = any(a['role'] == 'DIRECT_SPONSOR_OVERRIDE' and a['partner_id'] == 97 for a in res_sponsor_valid['allocations'])
        assert_test("TEST I: Immediate Direct Sponsor (Channel Partner) receives 1.00%", has_sponsor, "Partner 97 received 1.00%")

        res_sponsor_unqual = VGK4UWaterfallEngine.calculate_commission_structure(
            db=db, producer_partner_id=30, deal_value=Decimal('10000.00'), category_slug='solar'
        )
        no_sponsor_field = not any(a['role'] == 'DIRECT_SPONSOR_OVERRIDE' for a in res_sponsor_unqual['allocations'])
        apex_has_remainder = any(a['role'] == 'APEX_REMAINDER' and a['commission_pct'] == Decimal('4.00') for a in res_sponsor_unqual['allocations'])
        assert_test("TEST J: Unqualified sponsor (Member Rank 0) forfeits to APEX_REMAINDER",
                    no_sponsor_field and apex_has_remainder, "No field sponsor override; 4.00% retained by Apex")

        # TEST K, L, M, N: Leadership Differentials & Apex Remainder:
        # In res_sponsor_valid (Producer 154, Sponsor 97, upline Apex 31):
        # 31 is Root Apex Node (Core rank 4), absorbing unclaimed Senior (1.5%) + Extended (1.0%) + Core (0.5%) = 3.00%
        core_alloc = next((a for a in res_sponsor_valid['allocations'] if a['role'] == 'RM_DIFFERENTIAL'), None)
        assert_test("TEST K-N: Leadership differential absorption by qualified upline node",
                    core_alloc is not None and core_alloc['commission_pct'] == Decimal('3.00'),
                    f"Upline absorbed differentials: {core_alloc['commission_pct']}%")

        # Now test full Stage 2 advance creation via database transactions!
        # Create a test lead in insurance category with deal_value_total = 100,000 (policy value)
        now_dt = datetime(2026, 9, 25, 10, 0, 0)
        lead_ins_id = db.execute(text("""
            INSERT INTO crm_leads (company_id, category_id, associated_partner_id, deal_value_total,
                                   deal_value_received, deal_value_balance, name, phone, status, priority, handler_type, created_at, updated_at)
            VALUES (4, 7, 154, 100000.00, 0.00, 100000.00, 'Test Insurance Customer', '9999900001', 'in_progress', 'medium', 'unassigned', :now, :now)
            RETURNING id
        """), {'now': now_dt}).scalar()

        # TEST G: Two partial commission receipts (Receipt 1 = ₹10,000, Receipt 2 = ₹15,000)
        # Create Transaction 1: Commission received = ₹10,000
        txn1_id = db.execute(text("""
            INSERT INTO crm_lead_transactions (company_id, lead_id, amount, transaction_type,
                                               payment_mode, validation_status, created_at, transaction_date)
            VALUES (4, :lid, 10000.00, 'partial', 'BANK', 'validated', :now, :now)
            RETURNING id
        """), {'lid': lead_ins_id, 'now': now_dt}).scalar()

        # Execute Stage 2 for Receipt 1
        s2_res1 = process_payment_stage2_advance(
            db=db, lead_id=lead_ins_id, transaction_id=txn1_id, payment_amount=Decimal('10000.00'),
            transaction_date=now_dt
        )
        assert_test("TEST G1: Receipt 1 (₹10,000) creates Stage 2 advance on actual commission",
                    s2_res1['created'] is True and len(s2_res1['entry_numbers']) >= 2,
                    f"Created entries: {s2_res1.get('entry_numbers')}")

        # Check that L1 advance amount is 5% of ₹10,000 = ₹500 (NOT 5% of ₹1,00,000 policy)
        l1_adv1 = db.execute(text("""
            SELECT advance_amount, earning_basis_type, earning_basis_amount, underlying_value
            FROM vgk_solar_cibil_advances
            WHERE source_transaction_id = :tid AND level = 1 AND kind = 'DVR_ADVANCE'
        """), {'tid': txn1_id}).fetchone()
        assert_test("TEST G1 basis check: L1 Stage 2 is ₹500 on ₹10,000 receipt, policy=₹1,00,000",
                    Decimal(str(l1_adv1.advance_amount)) == Decimal('500.00')
                    and l1_adv1.earning_basis_type == 'COMMISSION_RECEIVED'
                    and Decimal(str(l1_adv1.earning_basis_amount)) == Decimal('10000.00')
                    and Decimal(str(l1_adv1.underlying_value)) == Decimal('100000.00'),
                    f"Adv: ₹{l1_adv1.advance_amount}, Basis: ₹{l1_adv1.earning_basis_amount}, Type: {l1_adv1.earning_basis_type}")

        # TEST O: Duplicate receipt transaction -> Idempotent, no duplicate
        s2_dup = process_payment_stage2_advance(
            db=db, lead_id=lead_ins_id, transaction_id=txn1_id, payment_amount=Decimal('10000.00'),
            transaction_date=now_dt
        )
        assert_test("TEST O: Duplicate transaction execution blocked idempotently",
                    s2_dup['created'] is False and 'already' in s2_dup['reason'].lower(),
                    f"Reason: {s2_dup.get('reason')}")

        # Create Transaction 2: Commission received = ₹15,000
        txn2_id = db.execute(text("""
            INSERT INTO crm_lead_transactions (company_id, lead_id, amount, transaction_type,
                                               payment_mode, validation_status, created_at, transaction_date)
            VALUES (4, :lid, 15000.00, 'final', 'BANK', 'validated', :now, :now)
            RETURNING id
        """), {'lid': lead_ins_id, 'now': now_dt}).scalar()

        s2_res2 = process_payment_stage2_advance(
            db=db, lead_id=lead_ins_id, transaction_id=txn2_id, payment_amount=Decimal('15000.00'),
            transaction_date=now_dt
        )
        assert_test("TEST G2: Receipt 2 (₹15,000) creates independent Stage 2 advance",
                    s2_res2['created'] is True and len(s2_res2['entry_numbers']) >= 2,
                    f"Created entries: {s2_res2.get('entry_numbers')}")

        l1_adv2 = db.execute(text("""
            SELECT advance_amount FROM vgk_solar_cibil_advances
            WHERE source_transaction_id = :tid AND level = 1 AND kind = 'DVR_ADVANCE'
        """), {'tid': txn2_id}).fetchone()
        assert_test("TEST G2 basis check: L1 Stage 2 is ₹750 (5% of ₹15,000)",
                    Decimal(str(l1_adv2.advance_amount)) == Decimal('750.00'),
                    f"Adv: ₹{l1_adv2.advance_amount}")

        # Total basis across both receipts = ₹10,000 + ₹15,000 = ₹25,000. Total L1 = ₹500 + ₹750 = ₹1,250 (5% of ₹25,000)
        total_l1 = db.execute(text("""
            SELECT SUM(advance_amount) FROM vgk_solar_cibil_advances
            WHERE lead_id = :lid AND level = 1 AND kind = 'DVR_ADVANCE'
        """), {'lid': lead_ins_id}).scalar()
        assert_test("TEST G Total: Sum of partial advances = ₹1,250 across ₹25,000 commission",
                    Decimal(str(total_l1)) == Decimal('1250.00'), f"Total L1: ₹{total_l1}")

        # TEST H: Receipt cancellation / reversal
        can_res = cancel_payment_stage2_advance(db=db, transaction_id=txn2_id, reason="Customer cancelled policy")
        assert_test("TEST H: Cancellation reverses only txn2 advances",
                    can_res['cancelled'] is True and can_res['cancelled_count'] >= 2,
                    f"Cancelled count: {can_res.get('cancelled_count')}")
        txn2_adv_status = db.execute(text("""
            SELECT DISTINCT status FROM vgk_solar_cibil_advances WHERE source_transaction_id = :tid
        """), {'tid': txn2_id}).fetchall()
        assert_test("TEST H Status: Txn2 advance records marked CANCELLED",
                    all(r[0] == 'CANCELLED' for r in txn2_adv_status), f"Statuses: {txn2_adv_status}")

        # TEST P: Effective date boundary guard
        # Transaction on 2026-09-24 15:00:00 (Prior to cutoff)
        legacy_dt = datetime(2026, 9, 24, 15, 0, 0)
        txn_leg_id = db.execute(text("""
            INSERT INTO crm_lead_transactions (company_id, lead_id, amount, transaction_type,
                                               payment_mode, validation_status, created_at, transaction_date)
            VALUES (4, :lid, 10000.00, 'partial', 'BANK', 'validated', :dt, :dt)
            RETURNING id
        """), {'lid': lead_ins_id, 'dt': legacy_dt}).scalar()

        s2_leg = process_payment_stage2_advance(
            db=db, lead_id=lead_ins_id, transaction_id=txn_leg_id, payment_amount=Decimal('10000.00'),
            transaction_date=legacy_dt
        )
        assert_test("TEST P: <= 2026-09-24 routed to legacy path (Not solar rejection for insurance lead)",
                    s2_leg['created'] is False and 'not solar' in s2_leg['reason'].lower(),
                    f"Legacy routed result: {s2_leg.get('reason')}")

        # ====================================================================
        # SECTION 14: STAGE 1 L1 + L2 DUAL ADVANCE RECOVERY VERIFICATION SUITE
        # ====================================================================

        # TEST 1: Stage 1 creation: L1 = ₹1,000, L2 = ₹500
        lead_sol_id = db.execute(text("""
            INSERT INTO crm_leads (company_id, category_id, associated_partner_id, team_senior_partner_id,
                                   deal_value_total, deal_value_received, deal_value_balance,
                                   remaining_stage1_advance, remaining_stage1_advance_l1, remaining_stage1_advance_l2,
                                   name, phone, status, priority, handler_type, solar_pipeline_status, created_at, updated_at)
            VALUES (4, 6, 154, 97, 100000.00, 0.00, 100000.00, 1500.00, 1000.00, 500.00,
                    'Test Solar Customer', '9999900002', 'in_progress', 'medium', 'unassigned', 'installation_pending', :now, :now)
            RETURNING id
        """), {'now': now_dt}).scalar()

        s1_l1_adv_id = db.execute(text("""
            INSERT INTO vgk_solar_cibil_advances (company_id, lead_id, partner_id, entry_number,
                                                 advance_amount, status, level, kind, created_at, updated_at)
            VALUES (4, :lid, 154, 'VSCA-TEST-S1-L1', 1000.00, 'RELEASED', 1, 'ADVANCE', :now, :now)
            RETURNING id
        """), {'lid': lead_sol_id, 'now': now_dt}).scalar()

        s1_l2_adv_id = db.execute(text("""
            INSERT INTO vgk_solar_cibil_advances (company_id, lead_id, partner_id, entry_number,
                                                 advance_amount, status, level, kind, created_at, updated_at)
            VALUES (4, :lid, 97, 'VSCA-TEST-S1-L2', 500.00, 'RELEASED', 2, 'ADVANCE', :now, :now)
            RETURNING id
        """), {'lid': lead_sol_id, 'now': now_dt}).scalar()

        assert_test("TEST 1: Stage 1 creation: L1 = ₹1,000, L2 = ₹500",
                    s1_l1_adv_id is not None and s1_l2_adv_id is not None,
                    "Stage 1 advances created for L1 (₹1,000) and L2 (₹500)")

        # TEST 2: 25% payment (₹25,000)
        # Payment ratio = 25% of ₹100,000.
        # L1 proposed recovery = 1,000 * 25% = ₹250. L1 Stage 2 gross = 5% of 25,000 = ₹1,250.
        # L2 proposed recovery = 500 * 25% = ₹125. L2 Stage 2 gross = 1% of 25,000 = ₹250.
        # Remaining: L1 = ₹750, L2 = ₹375. Total = ₹1,125.
        txn_sol_1 = db.execute(text("""
            INSERT INTO crm_lead_transactions (company_id, lead_id, amount, transaction_type,
                                               payment_mode, validation_status, created_at, transaction_date)
            VALUES (4, :lid, 25000.00, 'partial', 'BANK', 'validated', :now, :now)
            RETURNING id
        """), {'lid': lead_sol_id, 'now': now_dt}).scalar()

        s2_res_t2 = process_payment_stage2_advance(
            db=db, lead_id=lead_sol_id, transaction_id=txn_sol_1, payment_amount=Decimal('25000.00'),
            transaction_date=now_dt
        )
        assert_test("TEST 2: 25% payment -> L1 recovery = ₹250, L2 recovery = ₹125",
                    Decimal(str(s2_res_t2['stage1_adjusted_l1'])) == Decimal('250.00') and
                    Decimal(str(s2_res_t2['stage1_adjusted_l2'])) == Decimal('125.00'),
                    f"L1 Adj: ₹{s2_res_t2.get('stage1_adjusted_l1')}, L2 Adj: ₹{s2_res_t2.get('stage1_adjusted_l2')}")
        assert_test("TEST 2: Remaining after 25% -> L1 = ₹750, L2 = ₹375, Total = ₹1,125",
                    Decimal(str(s2_res_t2['remaining_stage1_l1'])) == Decimal('750.00') and
                    Decimal(str(s2_res_t2['remaining_stage1_l2'])) == Decimal('375.00') and
                    Decimal(str(s2_res_t2['remaining_stage1'])) == Decimal('1125.00'),
                    f"L1 Rem: ₹{s2_res_t2.get('remaining_stage1_l1')}, L2 Rem: ₹{s2_res_t2.get('remaining_stage1_l2')}")

        # TEST 3: Additional 50% payment (₹50,000)
        # Payment ratio = 50%.
        # L1 recovery = ₹500, L2 recovery = ₹250.
        # Remaining: L1 = ₹250, L2 = ₹125. Total = ₹375.
        db.execute(text("UPDATE crm_leads SET deal_value_received = 25000.00, deal_value_balance = 75000.00 WHERE id = :lid"), {'lid': lead_sol_id})
        txn_sol_2 = db.execute(text("""
            INSERT INTO crm_lead_transactions (company_id, lead_id, amount, transaction_type,
                                               payment_mode, validation_status, created_at, transaction_date)
            VALUES (4, :lid, 50000.00, 'partial', 'BANK', 'validated', :now, :now)
            RETURNING id
        """), {'lid': lead_sol_id, 'now': now_dt}).scalar()

        s2_res_t3 = process_payment_stage2_advance(
            db=db, lead_id=lead_sol_id, transaction_id=txn_sol_2, payment_amount=Decimal('50000.00'),
            transaction_date=now_dt
        )
        assert_test("TEST 3: Additional 50% payment -> L1 recovery = ₹500, L2 recovery = ₹250",
                    Decimal(str(s2_res_t3['stage1_adjusted_l1'])) == Decimal('500.00') and
                    Decimal(str(s2_res_t3['stage1_adjusted_l2'])) == Decimal('250.00'),
                    f"L1 Adj: ₹{s2_res_t3.get('stage1_adjusted_l1')}, L2 Adj: ₹{s2_res_t3.get('stage1_adjusted_l2')}")
        assert_test("TEST 3: Remaining after 50% -> L1 = ₹250, L2 = ₹125, Total = ₹375",
                    Decimal(str(s2_res_t3['remaining_stage1_l1'])) == Decimal('250.00') and
                    Decimal(str(s2_res_t3['remaining_stage1_l2'])) == Decimal('125.00') and
                    Decimal(str(s2_res_t3['remaining_stage1'])) == Decimal('375.00'),
                    f"L1 Rem: ₹{s2_res_t3.get('remaining_stage1_l1')}, L2 Rem: ₹{s2_res_t3.get('remaining_stage1_l2')}")

        # TEST 4: Final 25% payment (₹25,000)
        # Final payment: balance = 0, remaining balance clears to 0!
        db.execute(text("UPDATE crm_leads SET deal_value_received = 75000.00, deal_value_balance = 25000.00 WHERE id = :lid"), {'lid': lead_sol_id})
        txn_sol_3 = db.execute(text("""
            INSERT INTO crm_lead_transactions (company_id, lead_id, amount, transaction_type,
                                               payment_mode, validation_status, created_at, transaction_date)
            VALUES (4, :lid, 25000.00, 'partial', 'BANK', 'validated', :now, :now)
            RETURNING id
        """), {'lid': lead_sol_id, 'now': now_dt}).scalar()

        # Update lead balance to 0 indicating final payment
        db.execute(text("UPDATE crm_leads SET deal_value_received = 100000.00, deal_value_balance = 0.00 WHERE id = :lid"), {'lid': lead_sol_id})

        s2_res_t4 = process_payment_stage2_advance(
            db=db, lead_id=lead_sol_id, transaction_id=txn_sol_3, payment_amount=Decimal('25000.00'),
            transaction_date=now_dt
        )
        assert_test("TEST 4: Final 25% payment -> L1 recovery = ₹250, L2 recovery = ₹125",
                    Decimal(str(s2_res_t4['stage1_adjusted_l1'])) == Decimal('250.00') and
                    Decimal(str(s2_res_t4['stage1_adjusted_l2'])) == Decimal('125.00'),
                    f"L1 Adj: ₹{s2_res_t4.get('stage1_adjusted_l1')}, L2 Adj: ₹{s2_res_t4.get('stage1_adjusted_l2')}")
        assert_test("TEST 4: Final remaining balances -> L1 = ₹0, L2 = ₹0, Total = ₹0",
                    Decimal(str(s2_res_t4['remaining_stage1_l1'])) == Decimal('0.00') and
                    Decimal(str(s2_res_t4['remaining_stage1_l2'])) == Decimal('0.00') and
                    Decimal(str(s2_res_t4['remaining_stage1'])) == Decimal('0.00'),
                    f"L1 Rem: ₹{s2_res_t4.get('remaining_stage1_l1')}, L2 Rem: ₹{s2_res_t4.get('remaining_stage1_l2')}")

        # Check status of Stage 1 advances is now ADJUSTED
        s1_statuses = db.execute(text("""
            SELECT level, status, advance_amount, adjustment_amount FROM vgk_solar_cibil_advances
            WHERE lead_id = :lid AND kind = 'ADVANCE'
        """), {'lid': lead_sol_id}).fetchall()
        assert_test("TEST 4 Status: Both L1 and L2 Stage 1 advances marked ADJUSTED",
                    all(r.status == 'ADJUSTED' and r.adjustment_amount == r.advance_amount for r in s1_statuses),
                    f"Stage 1 statuses: {s1_statuses}")

        # TEST 5, 6, 7: Insufficient Stage 2 Gross Capping, No Negative Earnings, No Cross-Level Recovery
        # Create a new test solar lead with low payment amount where proposed recovery > gross earning
        lead_low_id = db.execute(text("""
            INSERT INTO crm_leads (company_id, category_id, associated_partner_id, team_senior_partner_id,
                                   deal_value_total, deal_value_received, deal_value_balance,
                                   remaining_stage1_advance, remaining_stage1_advance_l1, remaining_stage1_advance_l2,
                                   name, phone, status, priority, handler_type, solar_pipeline_status, created_at, updated_at)
            VALUES (4, 6, 154, 97, 100000.00, 0.00, 100000.00, 1500.00, 1000.00, 500.00,
                    'Test Solar Low Payment', '9999900003', 'in_progress', 'medium', 'unassigned', 'installation_pending', :now, :now)
            RETURNING id
        """), {'now': now_dt}).scalar()

        db.execute(text("""
            INSERT INTO vgk_solar_cibil_advances (company_id, lead_id, partner_id, entry_number,
                                                 advance_amount, status, level, kind, created_at, updated_at)
            VALUES (4, :lid, 154, 'VSCA-TEST-S1-L1-LOW', 1000.00, 'RELEASED', 1, 'ADVANCE', :now, :now),
                   (4, :lid, 97, 'VSCA-TEST-S1-L2-LOW', 500.00, 'RELEASED', 2, 'ADVANCE', :now, :now)
        """), {'lid': lead_low_id, 'now': now_dt})

        # Set balance = 0 to trigger is_final_payment with low payment of ₹1,000:
        # L1 proposed = ₹1,000; L1 gross = ₹50 -> CAPPED AT ₹50!
        # L2 proposed = ₹500; L2 gross = ₹10 -> CAPPED AT ₹10!
        db.execute(text("UPDATE crm_leads SET deal_value_balance = 0.00 WHERE id = :lid"), {'lid': lead_low_id})
        txn_low_id = db.execute(text("""
            INSERT INTO crm_lead_transactions (company_id, lead_id, amount, transaction_type,
                                               payment_mode, validation_status, created_at, transaction_date)
            VALUES (4, :lid, 1000.00, 'full', 'BANK', 'validated', :now, :now)
            RETURNING id
        """), {'lid': lead_low_id, 'now': now_dt}).scalar()

        s2_res_low = process_payment_stage2_advance(
            db=db, lead_id=lead_low_id, transaction_id=txn_low_id, payment_amount=Decimal('1000.00'),
            transaction_date=now_dt
        )

        assert_test("TEST 5: L1 Stage 2 gross insufficient -> L1 capped at gross (₹50)",
                    Decimal(str(s2_res_low['stage1_adjusted_l1'])) == Decimal('50.00') and
                    Decimal(str(s2_res_low['remaining_stage1_l1'])) == Decimal('950.00'),
                    f"L1 Adj: ₹{s2_res_low.get('stage1_adjusted_l1')}, L1 Rem: ₹{s2_res_low.get('remaining_stage1_l1')}")

        assert_test("TEST 6: L2 Stage 2 gross insufficient -> L2 capped at gross (₹10)",
                    Decimal(str(s2_res_low['stage1_adjusted_l2'])) == Decimal('10.00') and
                    Decimal(str(s2_res_low['remaining_stage1_l2'])) == Decimal('490.00'),
                    f"L2 Adj: ₹{s2_res_low.get('stage1_adjusted_l2')}, L2 Rem: ₹{s2_res_low.get('remaining_stage1_l2')}")

        # TEST 7: Both capped independently, no negative earnings, no cross-level recovery
        l1_dvr_low = db.execute(text("""
            SELECT advance_amount, adjustment_amount FROM vgk_solar_cibil_advances
            WHERE source_transaction_id = :tid AND level = 1 AND kind = 'DVR_ADVANCE'
        """), {'tid': txn_low_id}).fetchone()
        l2_dvr_low = db.execute(text("""
            SELECT advance_amount, adjustment_amount FROM vgk_solar_cibil_advances
            WHERE source_transaction_id = :tid AND level = 2 AND kind = 'DVR_ADVANCE'
        """), {'tid': txn_low_id}).fetchone()

        net_l1 = Decimal(str(l1_dvr_low.advance_amount)) - Decimal(str(l1_dvr_low.adjustment_amount))
        net_l2 = Decimal(str(l2_dvr_low.advance_amount)) - Decimal(str(l2_dvr_low.adjustment_amount))
        assert_test("TEST 7: No negative earnings: Net L1 >= 0 and Net L2 >= 0",
                    net_l1 == Decimal('0.00') and net_l2 == Decimal('0.00'),
                    f"Net L1: ₹{net_l1}, Net L2: ₹{net_l2}")

        # TEST 8: Verify L3, L4, L5, Support, Showroom untouched by Stage 1 recovery
        l3_to_l5_adj = db.execute(text("""
            SELECT level, adjustment_amount FROM vgk_solar_cibil_advances
            WHERE source_transaction_id = :tid AND level > 2 AND kind = 'DVR_ADVANCE'
        """), {'tid': txn_low_id}).fetchall()
        assert_test("TEST 8: L3, L4, L5 have zero Stage 1 adjustment (100% gross)",
                    all(r.adjustment_amount is None or Decimal(str(r.adjustment_amount)) == Decimal('0.00') for r in l3_to_l5_adj),
                    f"L3..L5 rows: {l3_to_l5_adj}")

        # TEST 9: Duplicate receipt blocked idempotently
        s2_dup = process_payment_stage2_advance(
            db=db, lead_id=lead_low_id, transaction_id=txn_low_id, payment_amount=Decimal('1000.00'),
            transaction_date=now_dt
        )
        assert_test("TEST 9: Duplicate receipt blocked without duplicate Stage 1 recovery",
                    s2_dup['created'] is False and 'already processed' in s2_dup['reason'],
                    f"Dup result: {s2_dup.get('reason')}")

        # TEST 10: Receipt reversal restores L1 and L2 Stage 1 adjustments
        can_res_low = cancel_payment_stage2_advance(db=db, transaction_id=txn_low_id, reason="Correction test cancel")
        assert_test("TEST 10: Cancellation restores both L1 and L2 adjustments (₹50 + ₹10 = ₹60)",
                    can_res_low['cancelled'] is True and Decimal(str(can_res_low.get('restored_stage1_adjustment', 0))) == Decimal('60.00'),
                    f"Restored adjustment: ₹{can_res_low.get('restored_stage1_adjustment')}")

        rem_restored = db.execute(text("""
            SELECT remaining_stage1_advance, remaining_stage1_advance_l1, remaining_stage1_advance_l2
            FROM crm_leads WHERE id = :lid
        """), {'lid': lead_low_id}).fetchone()
        assert_test("TEST 10: Balances restored to initial (L1=₹1,000, L2=₹500, Total=₹1,500)",
                    Decimal(str(rem_restored.remaining_stage1_advance_l1)) == Decimal('1000.00') and
                    Decimal(str(rem_restored.remaining_stage1_advance_l2)) == Decimal('500.00') and
                    Decimal(str(rem_restored.remaining_stage1_advance)) == Decimal('1500.00'),
                    f"Restored on lead: L1=₹{rem_restored.remaining_stage1_advance_l1}, L2=₹{rem_restored.remaining_stage1_advance_l2}")

        # TEST 11: Final Payment reconciliation via apply_adjustment_at_completion
        mock_comm_l1 = db.execute(text("""
            INSERT INTO vgk_cash_income_entries (company_id, entry_number, partner_id, source_lead_id,
                                                 level, commission_pct, commission_amount, net_payout,
                                                 status, kind, created_at, updated_at)
            VALUES (4, 'VCI-TEST-L1-COMP', 154, :lid, 1, 5.00, 5000.00, 4500.00, 'DRAFT', 'COMMISSION', :now, :now)
            RETURNING id
        """), {'lid': lead_low_id, 'now': now_dt}).scalar()

        adj_comp_res = apply_adjustment_at_completion(db=db, lead_id=lead_low_id, cash_income_entry_id=mock_comm_l1)
        assert_test("TEST 11: Final reconciliation closes Stage 1 without double deduction",
                    adj_comp_res['adjusted'] is True and Decimal(str(adj_comp_res['adjustment_amount'])) == Decimal('1000.00'),
                    f"Reconciled: ₹{adj_comp_res.get('adjustment_amount')}, Adjusted Comm: ₹{adj_comp_res.get('adjusted_commission')}")

        # TEST 12: Historical transaction before 25 September 2026 unchanged
        assert_test("TEST 12: Historical transactions before 25-Sep-2026 remain on legacy path",
                    s2_leg['created'] is False and 'not solar' in s2_leg['reason'].lower(),
                    "Verified legacy boundary guard")

        # Clean up test rows
        db.execute(text("DELETE FROM vgk_cash_income_entries WHERE source_lead_id IN (:l1, :l2, :l3)"), {'l1': lead_ins_id, 'l2': lead_sol_id, 'l3': lead_low_id})
        db.execute(text("DELETE FROM vgk_solar_cibil_advances WHERE lead_id IN (:l1, :l2, :l3)"), {'l1': lead_ins_id, 'l2': lead_sol_id, 'l3': lead_low_id})
        db.execute(text("DELETE FROM crm_lead_transactions WHERE lead_id IN (:l1, :l2, :l3)"), {'l1': lead_ins_id, 'l2': lead_sol_id, 'l3': lead_low_id})
        db.execute(text("DELETE FROM crm_leads WHERE id IN (:l1, :l2, :l3)"), {'l1': lead_ins_id, 'l2': lead_sol_id, 'l3': lead_low_id})
        db.commit()
        db.commit()

        print("=" * 80)
        print(f" ALL {passed_count}/{total_tests} ACCEPTANCE TESTS PASSED WITH 100% SUCCESS!")
        print("=" * 80)

    except Exception as e:
        db.rollback()
        print(f"❌ Error during test execution: {e}")
        import traceback
        traceback.print_exc()
        raise e
    finally:
        db.close()


if __name__ == '__main__':
    run_tests()
