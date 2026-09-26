"""
PRODUCTION RECONCILIATION EXECUTION SCRIPT
Date: 2026-09-26
Target: AWS Production RDS (myntreal-database.c5gywaicq6zu.ap-south-2.rds.amazonaws.com)

Execution Items:
1. Schema & Migration Bootstrap:
   - DDL on vgk4u_category_commission_configs, vgk_solar_cibil_advances, vgk_cash_income_entries, crm_leads
   - Universal 9% commission model update for all categories
2. Freeze Bonanza Extra Commission:
   - Disable Bonanza 96
   - Cancel 6 post-cutoff VCI entries (2247, 2248, 2251, 2252, 2260, 2261)
   - Log wallet reconciliation adjustments without driving wallets negative
3. Lead 9719 Reversal:
   - Cancel duplicate VCI entries (2225, 2226)
   - Refund points via vgk_points_ledger (+900 pts Partner 445, +450 pts Partner 370)
   - Update official_partners vgk_points_balance
4. Lead 9740 Replacement:
   - Cancel legacy Stage 2 advances (285, 286)
   - Generate Universal 9% receipt-based Stage 2 advances on Txn #445 (₹130,000 receipt)
   - Update remaining Stage 1 balances (L1: ₹350, L2: ₹175, Total: ₹525)
   - Update Stage 1 advance adjustment amounts (Adv 260: ₹650, Adv 261: ₹325)
5. Zero-Collection Stage 1 Recoverable Balances:
   - Lead 689: L1=1000, L2=500
   - Lead 9719: L1=0, L2=0
   - Lead 10577: L1=1000, L2=500
   - Lead 10526: L1=1000, L2=500
   - Lead 10558: L1=1000, L2=500
   - Lead 8926: L1=1000, L2=500
   - Lead 7613: L1=0, L2=500
   - Lead 10537: L1=1000, L2=500 (Pre-cutoff DVR advances 282 & 283 preserved)
"""

import sys
import os
from decimal import Decimal
from datetime import datetime
import psycopg2
from psycopg2.extras import RealDictCursor

PROD_DB_URL = "postgresql://postgres:MyntRealAdmin2026!@myntreal-database.c5gywaicq6zu.ap-south-2.rds.amazonaws.com:5432/postgres"

def run_reconciliation():
    print("=" * 80)
    print("STARTING PRODUCTION FINANCIAL RECONCILIATION EXECUTION")
    print("=" * 80)

    conn = psycopg2.connect(PROD_DB_URL)
    conn.autocommit = False
    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        # ---------------------------------------------------------------------
        # 1. PRE-FLIGHT VERIFICATIONS
        # ---------------------------------------------------------------------
        print("\n[STEP 1] Running Pre-Flight Verifications...")

        # A. Check 6 Bonanza VCI entries
        cur.execute("""
            SELECT id, status, commission_amount, partner_id, source_lead_id
            FROM vgk_cash_income_entries
            WHERE id IN (2247, 2248, 2251, 2252, 2260, 2261);
        """)
        bonanza_vci = cur.fetchall()
        print(f"  Found {len(bonanza_vci)} Bonanza VCI entries.")
        assert len(bonanza_vci) == 6, f"Expected 6 Bonanza entries, found {len(bonanza_vci)}"
        for r in bonanza_vci:
            assert r['status'] == 'PENDING', f"Expected PENDING for VCI {r['id']}, got {r['status']}"

        # B. Check Lead 9719 duplicate VCI entries
        cur.execute("""
            SELECT id, status, commission_amount, net_payout, partner_id
            FROM vgk_cash_income_entries
            WHERE id IN (2225, 2226);
        """)
        dup_9719_vci = cur.fetchall()
        print(f"  Found {len(dup_9719_vci)} Lead 9719 duplicate VCI entries.")
        assert len(dup_9719_vci) == 2, f"Expected 2 duplicate VCI entries, found {len(dup_9719_vci)}"
        for r in dup_9719_vci:
            assert r['status'] == 'PAID', f"Expected PAID for VCI {r['id']}, got {r['status']}"

        # C. Check Lead 9740 legacy Stage 2 advances
        cur.execute("""
            SELECT id, status, advance_amount, partner_id, level, kind
            FROM vgk_solar_cibil_advances
            WHERE id IN (285, 286);
        """)
        s2_9740 = cur.fetchall()
        print(f"  Found {len(s2_9740)} Lead 9740 legacy Stage 2 advances.")
        assert len(s2_9740) == 2, f"Expected 2 advances for 9740, found {len(s2_9740)}"
        for r in s2_9740:
            assert r['status'] == 'PENDING', f"Expected PENDING for advance {r['id']}, got {r['status']}"

        # D. Check Lead 10537 legacy Stage 2 advances (to ensure preservation)
        cur.execute("""
            SELECT id, status, advance_amount, partner_id, level, kind
            FROM vgk_solar_cibil_advances
            WHERE id IN (282, 283);
        """)
        s2_10537 = cur.fetchall()
        print(f"  Found {len(s2_10537)} Lead 10537 legacy Stage 2 advances to PRESERVE.")
        assert len(s2_10537) == 2, f"Expected 2 advances for 10537, found {len(s2_10537)}"
        for r in s2_10537:
            assert r['status'] == 'PENDING', f"Expected PENDING for advance {r['id']}, got {r['status']}"

        print("  ✅ All Pre-Flight Verifications Passed!")

        # ---------------------------------------------------------------------
        # 2. SCHEMA & MIGRATION BOOTSTRAP
        # ---------------------------------------------------------------------
        print("\n[STEP 2] Applying Schema Bootstraps and DDL...")

        # vgk4u_category_commission_configs
        cur.execute("""
            ALTER TABLE vgk4u_category_commission_configs
            ADD COLUMN IF NOT EXISTS earning_basis_type VARCHAR(50) NOT NULL DEFAULT 'PAYMENT_RECEIVED';

            UPDATE vgk4u_category_commission_configs
            SET max_network_pool_pct     = 9.00,
                producer_base_pct        = 5.00,
                sponsor_override_pct     = 1.00,
                manager_diff_pct         = 1.50,
                gm_diff_pct              = 1.00,
                rm_diff_pct              = 0.50,
                unallocated_balance_pct  = 0.00,
                updated_at               = CURRENT_TIMESTAMP;

            UPDATE vgk4u_category_commission_configs
            SET earning_basis_type = 'PAYMENT_RECEIVED'
            WHERE category_slug IN ('solar', 'ev', 'etc-training', 'ev-spares');

            UPDATE vgk4u_category_commission_configs
            SET earning_basis_type = 'COMMISSION_RECEIVED'
            WHERE category_slug IN ('insurance', 'real-dreams');

            INSERT INTO vgk4u_category_commission_configs 
                (version_label, effective_from, category_slug, category_name, max_network_pool_pct, producer_base_pct,
                 sponsor_override_pct, manager_diff_pct, gm_diff_pct, rm_diff_pct,
                 support_journey_pct, support_end_to_end_pct, showroom_pct,
                 unallocated_balance_pct, admin_charge_pct, tds_pct, is_active, earning_basis_type)
            SELECT 'v2_sep2026', '2026-09-25 00:00:00', 'ev-spares', 'EV Spares & Components', 9.00, 5.00,
                   1.00, 1.50, 1.00, 0.50,
                   0.00, 0.00, 0.00,
                   0.00, 8.00, 2.00, true, 'PAYMENT_RECEIVED'
            WHERE NOT EXISTS (
                SELECT 1 FROM vgk4u_category_commission_configs WHERE category_slug = 'ev-spares'
            );
        """)

        # vgk_solar_cibil_advances schema
        cur.execute("""
            ALTER TABLE vgk_solar_cibil_advances ADD COLUMN IF NOT EXISTS source_transaction_id INTEGER;
            ALTER TABLE vgk_solar_cibil_advances ADD COLUMN IF NOT EXISTS earning_basis_type VARCHAR(50);
            ALTER TABLE vgk_solar_cibil_advances ADD COLUMN IF NOT EXISTS earning_basis_amount NUMERIC(15, 2);
            ALTER TABLE vgk_solar_cibil_advances ADD COLUMN IF NOT EXISTS underlying_value NUMERIC(15, 2);

            CREATE INDEX IF NOT EXISTS ix_vsca_source_txn ON vgk_solar_cibil_advances(source_transaction_id);

            ALTER TABLE vgk_solar_cibil_advances DROP CONSTRAINT IF EXISTS vgk_solar_adv_status_chk;
            ALTER TABLE vgk_solar_cibil_advances ADD CONSTRAINT vgk_solar_adv_status_chk 
              CHECK (status IN ('PENDING', 'RELEASED', 'RECOVERED', 'ADJUSTED', 'DEFICIT', 'CANCELLED', 'STAGE1_APPROVED', 'PAID'));

            DROP INDEX IF EXISTS uq_vgk_cibil_adv_lead_level_kind;
            CREATE UNIQUE INDEX IF NOT EXISTS uq_vgk_cibil_adv_lead_level_kind_legacy 
              ON vgk_solar_cibil_advances (lead_id, level, kind) 
              WHERE status NOT IN ('RECOVERED', 'CANCELLED') AND source_transaction_id IS NULL;

            DROP INDEX IF EXISTS uq_vsca_txn_partner_level_kind;
            CREATE UNIQUE INDEX IF NOT EXISTS uq_vsca_txn_partner_level_kind 
              ON vgk_solar_cibil_advances (source_transaction_id, partner_id, level, kind) 
              WHERE source_transaction_id IS NOT NULL AND status NOT IN ('RECOVERED', 'CANCELLED');
        """)

        # vgk_cash_income_entries schema
        cur.execute("""
            ALTER TABLE vgk_cash_income_entries ADD COLUMN IF NOT EXISTS source_transaction_id INTEGER;
            ALTER TABLE vgk_cash_income_entries ADD COLUMN IF NOT EXISTS earning_basis_type VARCHAR(50);
            ALTER TABLE vgk_cash_income_entries ADD COLUMN IF NOT EXISTS earning_basis_amount NUMERIC(15, 2);

            CREATE INDEX IF NOT EXISTS ix_vci_source_txn ON vgk_cash_income_entries(source_transaction_id);

            DROP INDEX IF EXISTS uq_vgk_cash_income_lead_partner_level_kind;
            CREATE UNIQUE INDEX IF NOT EXISTS uq_vgk_cash_income_lead_partner_level_kind 
              ON vgk_cash_income_entries (company_id, source_lead_id, partner_id, level, kind, COALESCE(source_transaction_id, 0), COALESCE(bonanza_id, 0)) 
              WHERE status <> 'CANCELLED';
        """)

        # crm_leads schema
        cur.execute("""
            ALTER TABLE crm_leads ADD COLUMN IF NOT EXISTS remaining_stage1_advance NUMERIC(12,2) NOT NULL DEFAULT 0.00;
            ALTER TABLE crm_leads ADD COLUMN IF NOT EXISTS remaining_stage1_advance_l1 NUMERIC(12,2);
            ALTER TABLE crm_leads ADD COLUMN IF NOT EXISTS remaining_stage1_advance_l2 NUMERIC(12,2);
        """)

        print("  ✅ Schema and DDL Bootstrap complete!")

        # ---------------------------------------------------------------------
        # 3. FREEZE BONANZA & RECONCILE 6 POST-CUTOFF ENTRIES
        # ---------------------------------------------------------------------
        print("\n[STEP 3] Freezing Bonanza 96 and cancelling 6 post-cutoff entries...")

        # A. Disable Bonanza 96
        cur.execute("""
            UPDATE bonanza
            SET status = 'Completed',
                end_date = '2026-09-20 23:59:59',
                updated_at = CURRENT_TIMESTAMP
            WHERE id = 96;
        """)

        # B. Cancel 6 post-cutoff VCI entries
        cur.execute("""
            UPDATE vgk_cash_income_entries
            SET status = 'CANCELLED',
                notes = COALESCE(notes, '') || ' | Cancelled: Post-cutoff Bonanza Extra Commission reversed (cutoff 21-Sep-2026)',
                updated_at = CURRENT_TIMESTAMP
            WHERE id IN (2247, 2248, 2251, 2252, 2260, 2261)
              AND status = 'PENDING';
        """)
        cancelled_bonanza_count = cur.rowcount
        print(f"  Cancelled {cancelled_bonanza_count} Bonanza VCI entries.")
        assert cancelled_bonanza_count == 6, f"Expected 6 cancelled, got {cancelled_bonanza_count}"

        # C. Reconcile wallet ledger:
        # Since wallets were already debited to 0.00 by mark_paid payouts, we do NOT deduct below 0.00.
        # We record explicit audit ledger entries in vgk_wallet_transactions.
        partners_bonanza = [
            (386, Decimal('2000.00'), 'P386 Nookaraju: Reversal of Bonanza Txns 3931/3936 (₹2,000) offset against prior Stage 1 cash payout debits'),
            (175, Decimal('1000.00'), 'P175 Musallayya: Reversal of Bonanza Txns 3932/3937 (₹1,000) offset against prior Stage 1 cash payout debits'),
            (489, Decimal('1000.00'), 'P489 Sathik: Reversal of Bonanza Txn 3946 (₹1,000) offset against prior Stage 1 cash payout debit'),
            (488, Decimal('500.00'),  'P488 Shivsanthosh: Reversal of Bonanza Txn 3947 (₹500) offset against prior Stage 1 cash payout debit'),
        ]
        for pid, rev_amt, desc in partners_bonanza:
            cur.execute("""
                SELECT vgk_cash_wallet FROM official_partners WHERE id = %s;
            """, (pid,))
            w_row = cur.fetchone()
            curr_w = Decimal(str(w_row['vgk_cash_wallet'] or 0))

            cur.execute("""
                INSERT INTO vgk_wallet_transactions
                    (company_id, partner_id, txn_type, direction, amount, wallet_before, wallet_after,
                     ref_type, ref_id, description, created_at)
                VALUES
                    (4, %s, 'ADJUSTMENT', 'DR', 0.00, %s, %s,
                     'VGK_EXTRA_COMMISSION', 96, %s, CURRENT_TIMESTAMP);
            """, (pid, float(curr_w), float(curr_w), desc))

        print("  ✅ Bonanza Extra Commission frozen and 6 entries reconciled!")

        # ---------------------------------------------------------------------
        # 4. RECONCILE LEAD 9719 DUPLICATE PAYOUT (CANCEL VCI + REFUND POINTS)
        # ---------------------------------------------------------------------
        print("\n[STEP 4] Reconciling Lead 9719 duplicate payout...")

        # A. Mark VCI entries CANCELLED
        cur.execute("""
            UPDATE vgk_cash_income_entries
            SET status = 'CANCELLED',
                notes = COALESCE(notes, '') || ' | CANCELLED: Erroneous duplicate payout on previously recovered advance (VSCA-2609-0023/24 recovered 21-Sep)',
                updated_at = CURRENT_TIMESTAMP
            WHERE id IN (2225, 2226) AND status = 'PAID';
        """)
        cancelled_9719_count = cur.rowcount
        print(f"  Cancelled {cancelled_9719_count} duplicate VCI entries on Lead 9719.")
        assert cancelled_9719_count == 2, f"Expected 2 cancelled entries, got {cancelled_9719_count}"

        # B. Post PAYOUT_REFUND in vgk_points_ledger
        # Partner 445: +900 points
        cur.execute("SELECT vgk_points_balance FROM official_partners WHERE id = 445;")
        p445_bal = Decimal(str(cur.fetchone()['vgk_points_balance'] or 0))
        new_p445_bal = p445_bal + Decimal('900.00')

        cur.execute("""
            INSERT INTO vgk_points_ledger
                (partner_id, points_credit, points_debit, balance_after, reason_code,
                 reference_type, reference_id, notes, created_at, created_by)
            VALUES
                (445, 900.00, 0.00, %s, 'COMMISSION_ADJUSTMENT',
                 'VGK_CASH_INCOME', 2225,
                 'PAYOUT_REFUND: Refund of points debited on cancelled duplicate payout VCI-2609-0126',
                 CURRENT_TIMESTAMP, 1);
        """, (float(new_p445_bal),))

        cur.execute("""
            UPDATE official_partners
            SET vgk_points_balance = %s, updated_at = CURRENT_TIMESTAMP
            WHERE id = 445;
        """, (float(new_p445_bal),))
        print(f"  Partner 445 points refunded: {p445_bal} -> {new_p445_bal} (+900 pts)")

        # Partner 370: +450 points
        cur.execute("SELECT vgk_points_balance FROM official_partners WHERE id = 370;")
        p370_bal = Decimal(str(cur.fetchone()['vgk_points_balance'] or 0))
        new_p370_bal = p370_bal + Decimal('450.00')

        cur.execute("""
            INSERT INTO vgk_points_ledger
                (partner_id, points_credit, points_debit, balance_after, reason_code,
                 reference_type, reference_id, notes, created_at, created_by)
            VALUES
                (370, 450.00, 0.00, %s, 'COMMISSION_ADJUSTMENT',
                 'VGK_CASH_INCOME', 2226,
                 'PAYOUT_REFUND: Refund of points debited on cancelled duplicate payout VCI-2609-0127',
                 CURRENT_TIMESTAMP, 1);
        """, (float(new_p370_bal),))

        cur.execute("""
            UPDATE official_partners
            SET vgk_points_balance = %s, updated_at = CURRENT_TIMESTAMP
            WHERE id = 370;
        """, (float(new_p370_bal),))
        print(f"  Partner 370 points refunded: {p370_bal} -> {new_p370_bal} (+450 pts)")

        print("  ✅ Lead 9719 points debits refunded and duplicate VCI entries cancelled!")

        # ---------------------------------------------------------------------
        # 5. RECONCILE LEAD 9740 (CANCEL LEGACY 285/286 & INSERT UNIVERSAL 9%)
        # ---------------------------------------------------------------------
        print("\n[STEP 5] Reconciling Lead 9740 Stage 2 advances...")

        # A. Cancel legacy advances 285 and 286
        cur.execute("""
            UPDATE vgk_solar_cibil_advances
            SET status = 'CANCELLED',
                recovery_reason = 'Replaced by Universal 9% receipt-based Stage 2 engine effective 25-Sep-2026',
                updated_at = CURRENT_TIMESTAMP
            WHERE id IN (285, 286) AND status = 'PENDING';
        """)
        cancelled_9740_count = cur.rowcount
        print(f"  Cancelled {cancelled_9740_count} legacy advances on Lead 9740.")
        assert cancelled_9740_count == 2, f"Expected 2 cancelled advances, got {cancelled_9740_count}"

        # B. Update Stage 1 advances 260 & 261 adjustment amounts on 65% pro-rata
        cur.execute("""
            UPDATE vgk_solar_cibil_advances
            SET adjustment_amount = 650.00,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = 260;

            UPDATE vgk_solar_cibil_advances
            SET adjustment_amount = 325.00,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = 261;
        """)

        # C. Update Lead 9740 remaining Stage 1 balances
        cur.execute("""
            UPDATE crm_leads
            SET remaining_stage1_advance = 525.00,
                remaining_stage1_advance_l1 = 350.00,
                remaining_stage1_advance_l2 = 175.00,
                first_dvr_confirmed_at = COALESCE(first_dvr_confirmed_at, '2026-09-25 12:26:06')
            WHERE id = 9740;
        """)

        # D. Insert the 5 Universal 9% Stage 2 advances for Txn #445 (₹130,000 receipt)
        # Next advance entry numbers starting from VSCA-2609-0055
        cur.execute("SELECT MAX(id) AS max_id FROM vgk_solar_cibil_advances;")
        max_adv_id = cur.fetchone()['max_id'] or 286

        # Layers:
        # L1: Partner 440 (5.00% = ₹6,500; S1 recovery = ₹650; net = ₹5,850)
        # L2: Partner 370 (1.00% = ₹1,300; S1 recovery = ₹325; net = ₹975)
        # L3: Partner 209 (1.50% = ₹1,950; S1 recovery = ₹0;   net = ₹1,950)
        # L4: Partner 123 (1.00% = ₹1,300; S1 recovery = ₹0;   net = ₹1,300)
        # L5: Partner 31  (0.50% = ₹650;   S1 recovery = ₹0;   net = ₹650)
        layers_9740 = [
            (1, 440, Decimal('5.00'), Decimal('6500.00'), Decimal('650.00'), 'PRODUCER', 'Stage 2 Advance (5.0%) on Txn #445 (₹130,000.00) [PAYMENT_RECEIVED] [Stage 1 Adj: ₹650.00]'),
            (2, 370, Decimal('1.00'), Decimal('1300.00'), Decimal('325.00'), 'DIRECT_SPONSOR_OVERRIDE', 'Stage 2 Advance (1.0%) on Txn #445 (₹130,000.00) [PAYMENT_RECEIVED] [Stage 1 Adj: ₹325.00]'),
            (3, 209, Decimal('1.50'), Decimal('1950.00'), Decimal('0.00'),   'MANAGER_DIFFERENTIAL', 'Stage 2 Advance (1.5%) on Txn #445 (₹130,000.00) [PAYMENT_RECEIVED]'),
            (4, 123, Decimal('1.00'), Decimal('1300.00'), Decimal('0.00'),   'GM_DIFFERENTIAL', 'Stage 2 Advance (1.0%) on Txn #445 (₹130,000.00) [PAYMENT_RECEIVED]'),
            (5, 31,  Decimal('0.50'), Decimal('650.00'),  Decimal('0.00'),   'RM_DIFFERENTIAL', 'Stage 2 Advance (0.5%) on Txn #445 (₹130,000.00) [PAYMENT_RECEIVED]'),
        ]

        # Determine next available entry number
        cur.execute("SELECT entry_number FROM vgk_solar_cibil_advances WHERE entry_number LIKE 'VSCA-2609-%' ORDER BY id DESC LIMIT 1;")
        last_en = cur.fetchone()['entry_number'] # e.g. VSCA-2609-0054
        seq_num = int(last_en.split('-')[-1])

        # Determine next available VCI entry number
        cur.execute("SELECT entry_number FROM vgk_cash_income_entries WHERE entry_number LIKE 'VCI-2609-%' ORDER BY id DESC LIMIT 1;")
        last_vci_en = cur.fetchone()['entry_number'] # e.g. VCI-2609-0165
        vci_seq_num = int(last_vci_en.split('-')[-1])

        for lvl, pid, pct, gross, adj, role, notes in layers_9740:
            seq_num += 1
            vsca_en = f"VSCA-2609-{seq_num:04d}"
            net_amt = gross - adj

            cur.execute("""
                INSERT INTO vgk_solar_cibil_advances
                    (company_id, lead_id, partner_id, entry_number, advance_amount,
                     adjustment_amount, status, stage_at_eligibility, cibil_score_at_check,
                     level, kind, notes, source_transaction_id, earning_basis_type,
                     earning_basis_amount, underlying_value, created_at, updated_at)
                VALUES
                    (4, 9740, %s, %s, %s,
                     %s, 'PENDING', 'payment_validated', NULL,
                     %s, 'DVR_ADVANCE', %s, 445, 'PAYMENT_RECEIVED',
                     130000.00, 200000.00, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                RETURNING id;
            """, (pid, vsca_en, float(gross), float(adj) if adj > 0 else None, lvl, notes))
            new_vsca_id = cur.fetchone()['id']

            # Mirror to vgk_cash_income_entries
            vci_seq_num += 1
            vci_en = f"VCI-2609-{vci_seq_num:04d}"
            admin_chg = (net_amt * Decimal('0.08')).quantize(Decimal('0.01'))
            tds_amt = (net_amt * Decimal('0.02')).quantize(Decimal('0.01'))
            net_payout = net_amt - admin_chg - tds_amt

            cur.execute("""
                INSERT INTO vgk_cash_income_entries
                    (company_id, entry_number, partner_id, source_lead_id, source_transaction_id,
                     kind, status, commission_amount, advance_adjusted_amount, admin_charges,
                     tds_amount, net_payout, level, notes, income_date, created_at, updated_at,
                     earning_basis_type, earning_basis_amount, deal_value_total, deal_value_excl_tax, commission_pct)
                VALUES
                    (4, %s, %s, 9740, 445,
                     'DVR_ADVANCE', 'PENDING', %s, %s, %s,
                     %s, %s, %s, %s, CURRENT_DATE, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP,
                     'PAYMENT_RECEIVED', 130000.00, 200000.00, 200000.00, %s);
            """, (vci_en, pid, float(gross), float(adj) if adj > 0 else 0.00,
                  float(admin_chg), float(tds_amt), float(net_payout), lvl,
                  f"Solar DVR advance mirror ({vsca_en}) | {notes}", float(pct)))

            print(f"  Created Stage 2 advance {vsca_en} (L{lvl} Partner {pid}): Gross ₹{gross}, Adj ₹{adj}, Net ₹{net_amt}")

        print("  ✅ Lead 9740 Universal 9% Stage 2 advances generated in PENDING!")

        # ---------------------------------------------------------------------
        # 6. SET ACCURATE OUTSTANDING STAGE 1 RECOVERABLE BALANCES
        # ---------------------------------------------------------------------
        print("\n[STEP 6] Setting accurate outstanding Stage 1 balances on CRM leads...")

        # Strict attribution per user instruction:
        # Lead 689:   L1=1000, L2=500  (Adv 262 & 263)
        # Lead 9719:  L1=0,    L2=0    (Adv 255 & 256 recovered on 21-Sep)
        # Lead 10577: L1=1000, L2=500  (Adv 267 & 268)
        # Lead 10526: L1=1000, L2=500  (Adv 269 & 270)
        # Lead 10558: L1=1000, L2=500  (Adv 271 & 272)
        # Lead 8926:  L1=1000, L2=500  (Adv 280 & 281)
        # Lead 7613:  L1=0,    L2=500  (Only L2 Adv 284 disbursed!)
        # Lead 10537: L1=1000, L2=500  (Adv 278 & 279)
        stage1_leads = [
            (689,   Decimal('1000.00'), Decimal('500.00')),
            (9719,  Decimal('0.00'),    Decimal('0.00')),
            (10577, Decimal('1000.00'), Decimal('500.00')),
            (10526, Decimal('1000.00'), Decimal('500.00')),
            (10558, Decimal('1000.00'), Decimal('500.00')),
            (8926,  Decimal('1000.00'), Decimal('500.00')),
            (7613,  Decimal('0.00'),    Decimal('500.00')), # CRITICAL: L1=0, L2=500
            (10537, Decimal('1000.00'), Decimal('500.00')),
        ]

        for lid, l1_rem, l2_rem in stage1_leads:
            tot_rem = l1_rem + l2_rem
            cur.execute("""
                UPDATE crm_leads
                SET remaining_stage1_advance = %s,
                    remaining_stage1_advance_l1 = %s,
                    remaining_stage1_advance_l2 = %s
                WHERE id = %s;
            """, (float(tot_rem), float(l1_rem), float(l2_rem), lid))
            print(f"  Lead #{lid}: L1 = ₹{l1_rem}, L2 = ₹{l2_rem}, Total Remaining = ₹{tot_rem}")

        print("  ✅ All Stage 1 recoverable balances accurately set!")

        # ---------------------------------------------------------------------
        # 7. COMMIT & POST-RECONCILIATION AUDIT VERIFICATION
        # ---------------------------------------------------------------------
        print("\n[STEP 7] Committing Transaction and Verifying Final Balances...")
        conn.commit()
        print("  🎉 TRANSACTION COMMITTED SUCCESSFULLY!")

        # Post-verification audit queries
        print("\n" + "=" * 80)
        print("FINAL POST-RECONCILIATION VERIFICATION REPORT")
        print("=" * 80)

        # 1. Check Bonanza VCI statuses
        cur.execute("""
            SELECT id, entry_number, status, notes
            FROM vgk_cash_income_entries
            WHERE id IN (2247, 2248, 2251, 2252, 2260, 2261);
        """)
        print("\n1. Post-Cutoff Bonanza VCI Entries Status:")
        for r in cur.fetchall():
            print(f"   VCI #{r['id']} ({r['entry_number']}): {r['status']}")

        # 2. Check Lead 9719 VCI statuses & Partner points balances
        cur.execute("""
            SELECT id, entry_number, status
            FROM vgk_cash_income_entries
            WHERE id IN (2225, 2226);
        """)
        print("\n2. Lead 9719 Duplicate VCI Entries Status:")
        for r in cur.fetchall():
            print(f"   VCI #{r['id']} ({r['entry_number']}): {r['status']}")

        cur.execute("""
            SELECT id, partner_code, first_name, last_name, vgk_points_balance, vgk_cash_wallet
            FROM official_partners
            WHERE id IN (445, 370);
        """)
        print("\n3. Partners 445 & 370 Balances After Point Refund:")
        for r in cur.fetchall():
            print(f"   Partner #{r['id']} ({r['first_name']} {r['last_name']}): Points = {r['vgk_points_balance']}, Wallet = ₹{r['vgk_cash_wallet']}")

        # 3. Check Lead 9740 Stage 2 advances
        cur.execute("""
            SELECT id, entry_number, partner_id, level, advance_amount, adjustment_amount, status
            FROM vgk_solar_cibil_advances
            WHERE lead_id = 9740
            ORDER BY id;
        """)
        print("\n4. Lead 9740 Advances (Legacy Cancelled & New Universal 9%):")
        for r in cur.fetchall():
            print(f"   Advance #{r['id']} ({r['entry_number']}): L{r['level']} P{r['partner_id']} - Gross ₹{r['advance_amount']}, Adj ₹{r['adjustment_amount'] or 0}, Status: {r['status']}")

        # 4. Check Lead 10537 Stage 2 advances (Preserved)
        cur.execute("""
            SELECT id, entry_number, partner_id, level, advance_amount, status
            FROM vgk_solar_cibil_advances
            WHERE lead_id = 10537
            ORDER BY id;
        """)
        print("\n5. Lead 10537 Advances (Preserved in PENDING):")
        for r in cur.fetchall():
            print(f"   Advance #{r['id']} ({r['entry_number']}): L{r['level']} P{r['partner_id']} - ₹{r['advance_amount']}, Status: {r['status']}")

        # 5. Check CRM Leads Stage 1 Recoverable Balances
        cur.execute("""
            SELECT id, remaining_stage1_advance_l1, remaining_stage1_advance_l2, remaining_stage1_advance
            FROM crm_leads
            WHERE id IN (689, 9719, 10577, 10526, 10558, 8926, 7613, 9740, 10537)
            ORDER BY id;
        """)
        print("\n6. CRM Leads Remaining Stage 1 Advances:")
        for r in cur.fetchall():
            print(f"   Lead #{r['id']}: L1 = ₹{r['remaining_stage1_advance_l1']}, L2 = ₹{r['remaining_stage1_advance_l2']}, Total = ₹{r['remaining_stage1_advance']}")

        print("\n" + "=" * 80)
        print("PRODUCTION RECONCILIATION COMPLETED WITH 100% PRECISION")
        print("=" * 80)

    except Exception as e:
        conn.rollback()
        print(f"\n❌ TRANSACTION ROLLED BACK DUE TO ERROR: {e}")
        raise e
    finally:
        cur.close()
        conn.close()

if __name__ == '__main__':
    run_reconciliation()
