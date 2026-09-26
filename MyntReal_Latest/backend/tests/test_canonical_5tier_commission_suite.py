"""
Test Suite: Canonical 5-Tier Commission Hierarchy & Final Payment Triggers
- L1 Source: 5.0%
- L2 Senior: 1.5%
- L3 Extended: 1.0%
- L4 Core: 0.5%
- L5 Support: 1.5% (Solar, EV, Training, EV Spares; Real Estate & Insurance based on staff pool)
- L6 Showroom: 3.5% on Solar (triggers along with final payment)
- Brand Commission: ₹2,000 based on selected brands (triggers along with final payment)
"""

import os
import unittest
from decimal import Decimal
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.models.vgk4u_models import VGK4UCategoryCommissionConfig
from app.services.vgk_solar_advance import check_and_create_dvr_advance
from app.services.vgk_brand_incentive import generate_brand_commission_entries, check_and_create_brand_advance


class TestCanonical5TierCommissionSuite(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        dev_url = os.environ.get("DEV_DATABASE_URL") or "postgresql://postgres:postgres@localhost:5433/myntreal_dev"
        cls.engine = create_engine(dev_url)
        cls.Session = sessionmaker(bind=cls.engine)
        cls.db = cls.Session()

        # Clean old test records
        try:
            cls.db.execute(text("DELETE FROM vgk_wallet_transactions WHERE partner_id IN (99881, 99882, 99883, 99884, 99885)"))
            cls.db.execute(text("DELETE FROM vgk_cash_income_entries WHERE source_lead_id >= 99880"))
            cls.db.execute(text("DELETE FROM vgk_solar_cibil_advances WHERE lead_id >= 99880 OR id IN (998811, 998812)"))
            cls.db.execute(text("DELETE FROM crm_lead_transactions WHERE lead_id >= 99880 OR id >= 99880"))
            cls.db.execute(text("DELETE FROM crm_leads WHERE id >= 99880"))
            cls.db.execute(text("DELETE FROM official_partners WHERE id IN (99881, 99882, 99883, 99884, 99885)"))
            cls.db.commit()

            # Create test unilevel upline chain:
            # L4 Core: 99884 (parent: 99885)
            # L3 Extended: 99883 (parent: 99884)
            # L2 Senior: 99882 (parent: 99883)
            # L1 Source: 99881 (parent: 99882)
            # L5 Support: 99885
            cls.db.execute(text("""
                INSERT INTO official_partners (id, partner_code, partner_name, phone, parent_partner_id, company_id, vgk_cash_wallet, vgk_points_balance, category, is_active, kyc_status, bank_details_status, created_at, updated_at)
                VALUES
                    (99885, 'TEST_P885', 'Test Support Partner', '9999998885', NULL,  4, 0.00, 50000.00, 'VGK_TEAM', true, 'Approved', 'Approved', NOW(), NOW()),
                    (99884, 'TEST_P884', 'Test Core Partner L4', '9999998884', 99885, 4, 0.00, 50000.00, 'VGK_TEAM', true, 'Approved', 'Approved', NOW(), NOW()),
                    (99883, 'TEST_P883', 'Test Extended Partner L3', '9999998883', 99884, 4, 0.00, 50000.00, 'VGK_TEAM', true, 'Approved', 'Approved', NOW(), NOW()),
                    (99882, 'TEST_P882', 'Test Senior Partner L2', '9999998882', 99883, 4, 0.00, 50000.00, 'VGK_TEAM', true, 'Approved', 'Approved', NOW(), NOW()),
                    (99881, 'TEST_P881', 'Test Source Partner L1', '9999998881', 99882, 4, 0.00, 50000.00, 'VGK_TEAM', true, 'Approved', 'Approved', NOW(), NOW());
            """))
            cls.db.commit()
        except Exception as e:
            cls.db.rollback()
            raise e

    @classmethod
    def tearDownClass(cls):
        try:
            cls.db.execute(text("DELETE FROM vgk_wallet_transactions WHERE partner_id IN (99881, 99882, 99883, 99884, 99885)"))
            cls.db.execute(text("DELETE FROM vgk_cash_income_entries WHERE source_lead_id >= 99880"))
            cls.db.execute(text("DELETE FROM vgk_solar_cibil_advances WHERE lead_id >= 99880 OR id IN (998811, 998812)"))
            cls.db.execute(text("DELETE FROM crm_lead_transactions WHERE lead_id >= 99880 OR id >= 99880"))
            cls.db.execute(text("DELETE FROM crm_leads WHERE id >= 99880"))
            cls.db.execute(text("DELETE FROM official_partners WHERE id IN (99881, 99882, 99883, 99884, 99885)"))
            cls.db.commit()
        finally:
            cls.db.close()

    def test_01_canonical_configs_active(self):
        """TEST 1: Verify all active category commission configs reflect the canonical hierarchy."""
        db = self.db
        slugs = ['solar', 'ev', 'etc-training', 'ev-spares', 'real-dreams', 'insurance']
        for slug in slugs:
            cfg = db.query(VGK4UCategoryCommissionConfig).filter_by(category_slug=slug, is_active=True).first()
            self.assertIsNotNone(cfg, f"Config missing for category {slug}")
            self.assertEqual(Decimal(str(cfg.producer_base_pct)), Decimal('5.00'), f"L1 Producer mismatch for {slug}")
            self.assertEqual(Decimal(str(cfg.sponsor_override_pct)), Decimal('1.50'), f"L2 Senior mismatch for {slug}")
            self.assertEqual(Decimal(str(cfg.manager_diff_pct)), Decimal('1.00'), f"L3 Extended mismatch for {slug}")
            self.assertEqual(Decimal(str(cfg.gm_diff_pct)), Decimal('0.50'), f"L4 Core mismatch for {slug}")
            self.assertEqual(Decimal(str(cfg.support_end_to_end_pct)), Decimal('1.50'), f"L5 Support mismatch for {slug}")
            self.assertEqual(Decimal(str(cfg.max_network_pool_pct)), Decimal('8.00'), f"Network pool mismatch for {slug}")
            if slug == 'solar':
                self.assertEqual(Decimal(str(cfg.showroom_pct)), Decimal('3.50'), "Solar Showroom mismatch")
            if slug in ('real-dreams', 'insurance'):
                self.assertEqual(cfg.earning_basis_type, 'COMMISSION_RECEIVED')
            else:
                self.assertEqual(cfg.earning_basis_type, 'PAYMENT_RECEIVED')

    def test_02_solar_5tier_calculation_and_pro_rata_recovery(self):
        """TEST 2: Verify Stage 2 DVR Advance generates exact 5 canonical tiers with L1/L2 pro-rata recovery."""
        db = self.db
        lead_id = 99881
        deal_total = Decimal('200000.00')
        receipt_amt = Decimal('130000.00') # 65% payment ratio

        # Clean prior data
        db.execute(text("DELETE FROM vgk_solar_cibil_advances WHERE lead_id = :lid OR id IN (998811, 998812)"), {'lid': lead_id})
        db.execute(text("DELETE FROM crm_lead_transactions WHERE lead_id = :lid OR id = 99881"), {'lid': lead_id})
        db.commit()

        # Create lead with Stage 1 advances: L1=1000, L2=500
        db.execute(text("""
            INSERT INTO crm_leads (id, name, phone, category_id, company_id, status, priority, handler_type, solar_pipeline_status,
                                   deal_value, deal_value_total, deal_value_received, deal_value_balance,
                                   associated_partner_id, team_senior_partner_id, vgk_field_support_id,
                                   remaining_stage1_advance_l1, remaining_stage1_advance_l2, remaining_stage1_advance,
                                   created_at, updated_at)
            VALUES (:lid, 'Canonical Test Lead', '9999998881', 6, 4, 'won', 'medium', 'partner', 'installation_pending',
                    :tot, :tot, :rcv, :bal,
                    99881, 99882, 99885,
                    1000.00, 500.00, 1500.00,
                    NOW(), NOW())
            ON CONFLICT (id) DO UPDATE SET
                deal_value_received = EXCLUDED.deal_value_received,
                deal_value_balance = EXCLUDED.deal_value_balance;
        """), {'lid': lead_id, 'tot': float(deal_total), 'rcv': float(receipt_amt), 'bal': float(deal_total - receipt_amt)})
        db.commit()

        # Seed Stage 1 advance records for L1 and L2
        db.execute(text("""
            INSERT INTO vgk_solar_cibil_advances (id, company_id, lead_id, partner_id, entry_number, advance_amount, adjustment_amount, status, level, kind, created_at, updated_at)
            VALUES
                (998811, 4, :lid, 99881, 'VSCA-TEST-S1-L1', 1000.00, 0.00, 'RELEASED', 1, 'ADVANCE', NOW(), NOW()),
                (998812, 4, :lid, 99882, 'VSCA-TEST-S1-L2', 500.00, 0.00, 'RELEASED', 2, 'ADVANCE', NOW(), NOW());
        """), {'lid': lead_id})
        db.commit()

        # Seed validated transaction in crm_lead_transactions
        db.execute(text("""
            INSERT INTO crm_lead_transactions (id, company_id, lead_id, amount, transaction_date, transaction_type, payment_mode, validation_status, created_at, updated_at)
            VALUES (99881, 4, :lid, :rcv, NOW(), 'receipt', 'bank_transfer', 'validated', NOW(), NOW());
        """), {'lid': lead_id, 'rcv': float(receipt_amt)})
        db.commit()

        # Trigger Stage 2 advance calculation on receipt
        res = check_and_create_dvr_advance(db, lead_id)
        self.assertTrue(res.get('created'))

        # Check all 5 generated advances
        advs = db.execute(text("""
            SELECT partner_id, level, advance_amount, adjustment_amount, status, notes
            FROM vgk_solar_cibil_advances
            WHERE lead_id = :lid AND kind = 'DVR_ADVANCE'
            ORDER BY level ASC
        """), {'lid': lead_id}).fetchall()

        self.assertEqual(len(advs), 5, "Must generate exactly 5 canonical layers")

        # L1 Source: 5.0% on ₹130,000 = ₹6,500. S1 recovery = ₹650 (65% of ₹1000)
        l1 = advs[0]
        self.assertEqual(l1.level, 1)
        self.assertEqual(l1.partner_id, 99881)
        self.assertEqual(Decimal(str(l1.advance_amount)), Decimal('6500.00'))
        self.assertEqual(Decimal(str(l1.adjustment_amount)), Decimal('650.00'))

        # L2 Senior: 1.5% on ₹130,000 = ₹1,950. S1 recovery = ₹325 (65% of ₹500)
        l2 = advs[1]
        self.assertEqual(l2.level, 2)
        self.assertEqual(l2.partner_id, 99882)
        self.assertEqual(Decimal(str(l2.advance_amount)), Decimal('1950.00'))
        self.assertEqual(Decimal(str(l2.adjustment_amount)), Decimal('325.00'))

        # L3 Extended: 1.0% on ₹130,000 = ₹1,300. Zero S1 recovery
        l3 = advs[2]
        self.assertEqual(l3.level, 3)
        self.assertEqual(l3.partner_id, 99883)
        self.assertEqual(Decimal(str(l3.advance_amount)), Decimal('1300.00'))
        self.assertIsNone(l3.adjustment_amount)

        # L4 Core: 0.5% on ₹130,000 = ₹650. Zero S1 recovery
        l4 = advs[3]
        self.assertEqual(l4.level, 4)
        self.assertEqual(l4.partner_id, 99884)
        self.assertEqual(Decimal(str(l4.advance_amount)), Decimal('650.00'))
        self.assertIsNone(l4.adjustment_amount)

        # L5 Support: 1.5% on ₹130,000 = ₹1,950. Zero S1 recovery
        l5 = advs[4]
        self.assertEqual(l5.level, 5)
        self.assertEqual(l5.partner_id, 99885)
        self.assertEqual(Decimal(str(l5.advance_amount)), Decimal('1950.00'))
        self.assertIsNone(l5.adjustment_amount)

    def test_03_brand_commission_triggers_only_at_final_payment(self):
        """TEST 3: Brand commission (₹2,000) does NOT trigger as advance; triggers ONLY at final completion."""
        db = self.db
        lead_id = 99882

        # Create lead with solar_brand_id = 6 (Navgrun - ₹2,000) in installation_pending (partial stage)
        db.execute(text("""
            INSERT INTO crm_leads (id, name, phone, category_id, company_id, status, priority, handler_type, solar_pipeline_status,
                                   solar_brand_id, associated_partner_id, team_senior_partner_id,
                                   deal_value, deal_value_total, deal_value_received, deal_value_balance,
                                   created_at, updated_at)
            VALUES (:lid, 'Brand Test Lead', '9999998882', 6, 4, 'won', 'medium', 'partner', 'installation_pending',
                    6, 99881, 99882,
                    200000.00, 200000.00, 100000.00, 100000.00,
                    NOW(), NOW())
            ON CONFLICT (id) DO UPDATE SET
                solar_pipeline_status = 'installation_pending',
                status = 'won',
                solar_brand_id = 6;
        """), {'lid': lead_id})
        db.commit()

        # Step 1: In installation_pending stage, advance check must decline brand advance
        res_adv = check_and_create_brand_advance(db, lead_id)
        self.assertFalse(res_adv.get('created'))

        lead_obj = db.execute(text("SELECT * FROM crm_leads WHERE id = :lid"), {'lid': lead_id}).fetchone()
        created_count = generate_brand_commission_entries(db, lead_obj)
        self.assertEqual(created_count, 0, "Must not create brand commission before final completion")

        # Step 2: Transition lead to 'completed' stage
        db.execute(text("UPDATE crm_leads SET solar_pipeline_status = 'completed', status = 'completed' WHERE id = :lid"), {'lid': lead_id})
        db.commit()

        lead_completed = db.execute(text("SELECT * FROM crm_leads WHERE id = :lid"), {'lid': lead_id}).fetchone()
        created_count_final = generate_brand_commission_entries(db, lead_completed)
        self.assertGreaterEqual(created_count_final, 1, "Must generate brand commission upon final completion")

        # Verify ₹2,000 VCI entry created for L1
        b_entry = db.execute(text("""
            SELECT partner_id, kind, level, commission_amount
            FROM vgk_cash_income_entries
            WHERE source_lead_id = :lid AND kind = 'BRAND_COMMISSION' AND partner_id = 99881
        """), {'lid': lead_id}).fetchone()
        self.assertIsNotNone(b_entry)
        self.assertEqual(Decimal(str(b_entry.commission_amount)), Decimal('2000.00'))

    def test_04_solar_showroom_triggers_only_at_final_payment(self):
        """TEST 4: Showroom commission (3.5%) is omitted from Stage 2 DVR advances and reserved for final commission."""
        db = self.db
        lead_id = 99883

        # Clean prior data
        db.execute(text("DELETE FROM vgk_solar_cibil_advances WHERE lead_id = :lid"), {'lid': lead_id})
        db.execute(text("DELETE FROM crm_lead_transactions WHERE lead_id = :lid OR id = 99883"), {'lid': lead_id})
        db.commit()

        # Create lead with showroom_vgk_id = 99885
        db.execute(text("""
            INSERT INTO crm_leads (id, name, phone, category_id, company_id, status, priority, handler_type, solar_pipeline_status,
                                   associated_partner_id, team_senior_partner_id, showroom_vgk_id,
                                   deal_value, deal_value_total, deal_value_received, deal_value_balance,
                                   created_at, updated_at)
            VALUES (:lid, 'Showroom Test Lead', '9999998883', 6, 4, 'won', 'medium', 'partner', 'installation_pending',
                    99881, 99882, 99885,
                    200000.00, 200000.00, 100000.00, 100000.00,
                    NOW(), NOW())
            ON CONFLICT (id) DO UPDATE SET
                showroom_vgk_id = 99885,
                solar_pipeline_status = 'installation_pending';
        """), {'lid': lead_id})
        db.commit()

        # Seed validated transaction in crm_lead_transactions
        db.execute(text("""
            INSERT INTO crm_lead_transactions (id, company_id, lead_id, amount, transaction_date, transaction_type, payment_mode, validation_status, created_at, updated_at)
            VALUES (99883, 4, :lid, 100000.00, NOW(), 'receipt', 'bank_transfer', 'validated', NOW(), NOW());
        """), {'lid': lead_id})
        db.commit()

        # DVR advance generation must NOT create Level 6 Showroom advance
        res_dvr = check_and_create_dvr_advance(db, lead_id)
        self.assertTrue(res_dvr.get('created'))

        sh_adv = db.execute(text("""
            SELECT id FROM vgk_solar_cibil_advances
            WHERE lead_id = :lid AND level = 6 AND kind = 'DVR_ADVANCE'
        """), {'lid': lead_id}).fetchone()
        self.assertIsNone(sh_adv, "Showroom commission must NOT be issued as a Stage 2 DVR advance")


if __name__ == '__main__':
    unittest.main()
