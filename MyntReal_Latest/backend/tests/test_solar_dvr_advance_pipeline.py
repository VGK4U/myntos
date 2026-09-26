import os
import sys
import unittest
from decimal import Decimal
from datetime import datetime, date

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from dotenv import load_dotenv
load_dotenv(os.path.join(backend_dir, ".env"))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.models.crm import CRMLead, CRMLeadTransaction
from app.models.staff import StaffEmployee
from app.models.staff_accounts import OfficialPartner, IncomeEntry
from app.services.vgk_solar_advance import check_and_create_dvr_advance, release_dvr_advance
from app.services.staff_accounts_service import IncomeEntryService
from pydantic import BaseModel
from typing import Optional


class StatusChangeData(BaseModel):
    status: str
    reason: Optional[str] = "Test approval"
    amount: Optional[float] = None
    payer_name: Optional[str] = None
    confirmation_type: Optional[str] = "TAXED"
    bank_account_id: Optional[int] = None
    solar_vendor_id: Optional[int] = None
    destination_type: Optional[str] = None
    destination_company_id: Optional[int] = None
    destination_employee_id: Optional[int] = None


class TestSolarDVRAdvancePipeline(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Use dev PostgreSQL database
        dev_url = os.environ.get("DEV_DATABASE_URL") or "postgresql://postgres:postgres@localhost:5433/myntreal_dev"
        cls.engine = create_engine(dev_url)
        cls.Session = sessionmaker(bind=cls.engine)
        cls.db = cls.Session()
        cls.cleanup_lead_ids = []
        cls.cleanup_partner_ids = []
        cls.cleanup_emp_ids = []

        # Setup base partners: Direct partner L1 (99152), Senior partner L2 (99031), Field support L5 (99221)
        try:
            # Clean old test data
            cls.db.execute(text("DELETE FROM vgk_wallet_transactions WHERE partner_id IN (99152, 99031, 99221, 99032)"))
            cls.db.execute(text("DELETE FROM vgk_cash_income_entries WHERE source_lead_id >= 99000"))
            cls.db.execute(text("DELETE FROM vgk_solar_cibil_advances WHERE lead_id >= 99000"))
            cls.db.execute(text("DELETE FROM income_entries WHERE lead_id >= 99000 OR entry_number LIKE 'TEST-INC-%'"))
            cls.db.execute(text("DELETE FROM crm_lead_transactions WHERE lead_id >= 99000"))
            cls.db.execute(text("DELETE FROM crm_leads WHERE id >= 99000"))
            cls.db.execute(text("DELETE FROM official_partners WHERE id IN (99152, 99031, 99221, 99032) OR partner_code LIKE 'TEST_P%'"))
            cls.db.commit()

            # Insert test partners
            # Partner 99152 has parent_partner_id = 99031 in official_partners
            cls.db.execute(text("""
                INSERT INTO official_partners (id, partner_code, partner_name, phone, parent_partner_id, company_id, vgk_cash_wallet, vgk_points_balance, category, is_active, kyc_status, bank_details_status, created_at, updated_at)
                VALUES 
                    (99152, 'TEST_P152', 'Test Partner Direct', '9999990152', 99031, 4, 0.00, 50000.00, 'VGK_TEAM', true, 'Approved', 'Approved', NOW(), NOW()),
                    (99031, 'TEST_P031', 'Test Partner Senior Parent', '9999990031', NULL, 4, 0.00, 50000.00, 'VGK_TEAM', true, 'Approved', 'Approved', NOW(), NOW()),
                    (99032, 'TEST_P032', 'Test Partner Explicit Senior', '9999990032', NULL, 4, 0.00, 50000.00, 'VGK_TEAM', true, 'Approved', 'Approved', NOW(), NOW()),
                    (99221, 'TEST_P221', 'Test Partner Support', '9999990221', NULL, 4, 0.00, 50000.00, 'VGK_TEAM', true, 'Approved', 'Approved', NOW(), NOW())
                ON CONFLICT (id) DO UPDATE SET 
                    parent_partner_id = EXCLUDED.parent_partner_id,
                    vgk_points_balance = 50000.00,
                    category = 'VGK_TEAM',
                    is_active = true,
                    kyc_status = 'Approved',
                    bank_details_status = 'Approved',
                    updated_at = NOW()
            """))
            cls.cleanup_partner_ids.extend([99152, 99031, 99032, 99221])
            cls.db.commit()

        except Exception as e:
            cls.db.rollback()
            raise RuntimeError(f"setUpClass failed: {e}")

    @classmethod
    def tearDownClass(cls):
        try:
            for lid in cls.cleanup_lead_ids:
                cls.db.execute(text("DELETE FROM vgk_wallet_transactions WHERE ref_id IN (SELECT id FROM vgk_solar_cibil_advances WHERE lead_id = :lid)"), {"lid": lid})
                cls.db.execute(text("DELETE FROM vgk_cash_income_entries WHERE source_lead_id = :lid"), {"lid": lid})
                cls.db.execute(text("DELETE FROM vgk_solar_cibil_advances WHERE lead_id = :lid"), {"lid": lid})
                cls.db.execute(text("DELETE FROM income_entries WHERE lead_id = :lid"), {"lid": lid})
                cls.db.execute(text("DELETE FROM crm_lead_transactions WHERE lead_id = :lid"), {"lid": lid})
                cls.db.execute(text("DELETE FROM crm_leads WHERE id = :lid"), {"lid": lid})
            for pid in cls.cleanup_partner_ids:
                cls.db.execute(text("DELETE FROM vgk_wallet_transactions WHERE partner_id = :pid"), {"pid": pid})
                cls.db.execute(text("DELETE FROM official_partners WHERE id = :pid"), {"pid": pid})
            cls.db.commit()
        except Exception:
            cls.db.rollback()
        finally:
            cls.db.close()

    def _create_test_lead(self, lead_id: int, sps: str = 'installation_pending', dvr: float = 0.0,
                          associated_partner_id: Optional[int] = 99152, senior_partner_id: Optional[int] = 99031,
                          field_support_id: Optional[int] = None):
        db = self.db
        db.execute(text("""
            INSERT INTO crm_leads (id, name, phone, category_id, company_id, status, priority, handler_type, solar_pipeline_status,
                                   deal_value, deal_value_total, deal_value_received, deal_value_balance,
                                   associated_partner_id, team_senior_partner_id, vgk_field_support_id,
                                   created_at, updated_at)
            VALUES (:id, :name, :phone, 6, 4, 'won', 'medium', 'partner', :sps,
                    200000.00, 200000.00, :dvr, :bal,
                    :ap_id, :sp_id, :fs_id,
                    NOW(), NOW())
            ON CONFLICT (id) DO UPDATE SET
                solar_pipeline_status = EXCLUDED.solar_pipeline_status,
                deal_value_received = EXCLUDED.deal_value_received,
                deal_value_balance = EXCLUDED.deal_value_balance,
                associated_partner_id = EXCLUDED.associated_partner_id,
                team_senior_partner_id = EXCLUDED.team_senior_partner_id,
                vgk_field_support_id = EXCLUDED.vgk_field_support_id
        """), {
            "id": lead_id,
            "name": f"Test Customer {lead_id}",
            "phone": f"99990{lead_id:05d}",
            "sps": sps,
            "dvr": dvr,
            "bal": max(0.0, 200000.00 - dvr),
            "ap_id": associated_partner_id,
            "sp_id": senior_partner_id,
            "fs_id": field_support_id
        })
        db.commit()
        if lead_id not in self.cleanup_lead_ids:
            self.cleanup_lead_ids.append(lead_id)

    def setUp(self):
        self.db.rollback()

    def test_01_confirmed_payment_dvr_created(self):
        """TEST 1: Confirmed payment via Accounts / IncomeEntryService -> DVR created."""
        db = self.db
        lead_id = 99001
        self._create_test_lead(lead_id=lead_id, sps='installation_pending', dvr=0.0)

        db.execute(text("DELETE FROM income_entries WHERE id = 99001 OR lead_id = :lid"), {"lid": lead_id})
        db.execute(text("DELETE FROM crm_lead_transactions WHERE id = 99001 OR lead_id = :lid"), {"lid": lead_id})
        db.commit()

        db.execute(text("""
            INSERT INTO crm_lead_transactions (id, company_id, lead_id, transaction_date, amount, transaction_type, payment_mode, validation_status, created_at, updated_at)
            VALUES (99001, 4, :lid, '2026-09-09 10:00:00', 150000.00, 'partial', 'neft', 'pending', NOW(), NOW())
        """), {"lid": lead_id})

        db.execute(text("""
            INSERT INTO income_entries (id, entry_number, company_id, income_source_id, income_date, amount, payment_mode, payer_name, status, crm_transaction_id, lead_id, tally_status, ledger_updated, created_at, updated_at)
            VALUES (99001, 'TEST-INC-99001', 4, 1, '2026-09-09', 150000.00, 'NEFT', 'Test Payer', 'PENDING', 99001, :lid, 'NOT_SYNCED', false, NOW(), NOW())
        """), {"lid": lead_id})
        db.commit()

        emp = db.query(StaffEmployee).filter(StaffEmployee.id == 1).first()
        data = StatusChangeData(status="CONFIRMED")
        IncomeEntryService.update_income_entry_status(db, 99001, data, emp)

        advs = db.execute(text("""
            SELECT id, lead_id, level, partner_id, advance_amount, kind, status
            FROM vgk_solar_cibil_advances
            WHERE lead_id = :lid AND kind = 'DVR_ADVANCE'
            ORDER BY level ASC
        """), {"lid": lead_id}).fetchall()

        self.assertEqual(len(advs), 2, "Expected exactly 2 DVR advances (L1 and L2)")
        self.assertEqual(advs[0].level, 1)
        self.assertEqual(advs[0].partner_id, 99152)
        self.assertEqual(Decimal(str(advs[0].advance_amount)), Decimal('1000.00'))
        self.assertEqual(advs[0].status, 'PENDING')

        self.assertEqual(advs[1].level, 2)
        self.assertEqual(advs[1].partner_id, 99031)
        self.assertEqual(Decimal(str(advs[1].advance_amount)), Decimal('500.00'))
        self.assertEqual(advs[1].status, 'PENDING')

    def test_02_pending_payment_no_dvr(self):
        """TEST 2: Pending/unconfirmed payment -> No DVR created."""
        db = self.db
        lead_id = 99002
        self._create_test_lead(lead_id=lead_id, sps='installation_pending', dvr=0.0)

        db.execute(text("DELETE FROM crm_lead_transactions WHERE id = 99002 OR lead_id = :lid"), {"lid": lead_id})
        db.execute(text("""
            INSERT INTO crm_lead_transactions (id, company_id, lead_id, transaction_date, amount, transaction_type, payment_mode, validation_status, created_at, updated_at)
            VALUES (99002, 4, :lid, '2026-09-09 10:00:00', 50000.00, 'partial', 'neft', 'pending', NOW(), NOW())
        """), {"lid": lead_id})
        db.commit()

        res = check_and_create_dvr_advance(db, lead_id)
        self.assertFalse(res.get('created'))
        self.assertEqual(res.get('reason'), 'DVR is zero')

        adv_count = db.execute(text("SELECT COUNT(*) FROM vgk_solar_cibil_advances WHERE lead_id = :lid"), {"lid": lead_id}).scalar()
        self.assertEqual(adv_count, 0)

    def test_03_pipeline_first_payment_later_dvr_created(self):
        """TEST 3: Pipeline reaches installation_pending first, payment confirmed later -> DVR created."""
        db = self.db
        lead_id = 99003
        self._create_test_lead(lead_id=lead_id, sps='installation_pending', dvr=0.0)

        res_zero = check_and_create_dvr_advance(db, lead_id)
        self.assertFalse(res_zero.get('created'))

        db.execute(text("UPDATE crm_leads SET deal_value_received = 150000.00, first_payment_received_date = '2026-09-09' WHERE id = :lid"), {"lid": lead_id})
        db.commit()

        res_paid = check_and_create_dvr_advance(db, lead_id)
        self.assertTrue(res_paid.get('created'))

        adv_count = db.execute(text("SELECT COUNT(*) FROM vgk_solar_cibil_advances WHERE lead_id = :lid AND kind = 'DVR_ADVANCE'"), {"lid": lead_id}).scalar()
        self.assertEqual(adv_count, 2)

    def test_04_payment_first_pipeline_later_dvr_created(self):
        """TEST 4: Payment confirmed while pipeline is at earlier stage -> DVR created, later transition does not duplicate."""
        db = self.db
        lead_id = 99004
        self._create_test_lead(lead_id=lead_id, sps='pending_with_bank', dvr=150000.00)

        res_paid = check_and_create_dvr_advance(db, lead_id)
        self.assertTrue(res_paid.get('created'))

        db.execute(text("UPDATE crm_leads SET solar_pipeline_status = 'installation_pending' WHERE id = :lid"), {"lid": lead_id})
        db.commit()

        res_repeat = check_and_create_dvr_advance(db, lead_id)
        self.assertFalse(res_repeat.get('created'))
        self.assertIn('already existed', res_repeat.get('reason', ''))

    def test_05_repeated_confirmation_no_duplicate(self):
        """TEST 5: Repeated confirmation calls never create duplicate advances or VCIs."""
        db = self.db
        lead_id = 99001

        res = check_and_create_dvr_advance(db, lead_id)
        self.assertFalse(res.get('created'))
        self.assertIn('already existed', res.get('reason', ''))

        count = db.execute(text("SELECT COUNT(*) FROM vgk_solar_cibil_advances WHERE lead_id = :lid AND kind = 'DVR_ADVANCE'"), {"lid": lead_id}).scalar()
        self.assertEqual(count, 2)

        vci_count = db.execute(text("SELECT COUNT(*) FROM vgk_cash_income_entries WHERE source_lead_id = :lid AND kind = 'DVR_ADVANCE'"), {"lid": lead_id}).scalar()
        self.assertEqual(vci_count, 2)

    def test_06_multiple_confirmation_paths_same_canonical_result(self):
        """TEST 6: Calling through different paths converges on same canonical result."""
        db = self.db
        lead_id = 99005
        self._create_test_lead(lead_id=lead_id, sps='installation_pending', dvr=100000.00)

        res1 = check_and_create_dvr_advance(db, lead_id)
        self.assertTrue(res1.get('created'))

        # Second path attempt (e.g. from finance review or ledger)
        res2 = check_and_create_dvr_advance(db, lead_id)
        self.assertFalse(res2.get('created'))

        count = db.execute(text("SELECT COUNT(*) FROM vgk_solar_cibil_advances WHERE lead_id = :lid AND kind = 'DVR_ADVANCE'"), {"lid": lead_id}).scalar()
        self.assertEqual(count, 2)

    def test_07_correct_l1_recipient_resolution(self):
        """TEST 7: Correct L1 recipient resolution matches associated_partner_id for ₹1,000."""
        db = self.db
        lead_id = 99001
        l1 = db.execute(text("""
            SELECT partner_id, advance_amount, status
            FROM vgk_solar_cibil_advances
            WHERE lead_id = :lid AND level = 1 AND kind = 'DVR_ADVANCE'
        """), {"lid": lead_id}).fetchone()

        self.assertIsNotNone(l1)
        self.assertEqual(l1.partner_id, 99152)
        self.assertEqual(Decimal(str(l1.advance_amount)), Decimal('1000.00'))

    def test_08_correct_l2_resolution_explicit_senior_partner(self):
        """TEST 8: Correct L2 resolution when lead has explicit team_senior_partner_id."""
        db = self.db
        lead_id = 99006
        self._create_test_lead(lead_id=lead_id, sps='installation_pending', dvr=200000.00,
                               associated_partner_id=99152, senior_partner_id=99032)
        res = check_and_create_dvr_advance(db, lead_id)
        self.assertTrue(res.get('created'))

        l2 = db.execute(text("""
            SELECT partner_id, advance_amount
            FROM vgk_solar_cibil_advances
            WHERE lead_id = :lid AND level = 2 AND kind = 'DVR_ADVANCE'
        """), {"lid": lead_id}).fetchone()

        self.assertIsNotNone(l2)
        self.assertEqual(l2.partner_id, 99032)
        self.assertEqual(Decimal(str(l2.advance_amount)), Decimal('500.00'))

    def test_09_correct_l2_resolution_fallback_to_parent_partner(self):
        """TEST 9: Generic L2 fallback to official_partners.parent_partner_id when team_senior_partner_id is NULL."""
        db = self.db
        lead_id = 99007
        self._create_test_lead(lead_id=lead_id, sps='installation_pending', dvr=200000.00,
                               associated_partner_id=99152, senior_partner_id=None)
        res = check_and_create_dvr_advance(db, lead_id)
        self.assertTrue(res.get('created'))

        l2 = db.execute(text("""
            SELECT partner_id, advance_amount
            FROM vgk_solar_cibil_advances
            WHERE lead_id = :lid AND level = 2 AND kind = 'DVR_ADVANCE'
        """), {"lid": lead_id}).fetchone()

        self.assertIsNotNone(l2)
        self.assertEqual(l2.partner_id, 99031, "L2 must resolve to parent_partner_id 99031 via generic fallback")
        self.assertEqual(Decimal(str(l2.advance_amount)), Decimal('500.00'))

    def test_10_no_l5_when_field_support_unassigned(self):
        """TEST 10: No L5 advance is created when vgk_field_support_id is NULL."""
        db = self.db
        lead_id = 99008
        self._create_test_lead(lead_id=lead_id, sps='installation_pending', dvr=200000.00, field_support_id=None)
        res = check_and_create_dvr_advance(db, lead_id)
        self.assertTrue(res.get('created'))

        l5 = db.execute(text("SELECT id FROM vgk_solar_cibil_advances WHERE lead_id = :lid AND level = 5"), {"lid": lead_id}).fetchone()
        self.assertIsNone(l5, "L5 advance must NOT exist when field support is NULL")

    def test_11_l5_created_when_legitimately_assigned(self):
        """TEST 11: L5 advance is created for ₹1,000 when vgk_field_support_id is set."""
        db = self.db
        lead_id = 99009
        self._create_test_lead(lead_id=lead_id, sps='installation_pending', dvr=200000.00, field_support_id=99221)
        res = check_and_create_dvr_advance(db, lead_id)
        self.assertTrue(res.get('created'))

        l5 = db.execute(text("""
            SELECT partner_id, advance_amount, kind, status
            FROM vgk_solar_cibil_advances
            WHERE lead_id = :lid AND level = 5 AND kind = 'DVR_ADVANCE'
        """), {"lid": lead_id}).fetchone()

        self.assertIsNotNone(l5)
        self.assertEqual(l5.partner_id, 99221)
        self.assertEqual(Decimal(str(l5.advance_amount)), Decimal('1000.00'))
        self.assertEqual(l5.status, 'PENDING')

    def test_12_dvr_creation_remains_pending(self):
        """TEST 12: DVR creation leaves advances and VCIs in PENDING status."""
        db = self.db
        lead_id = 99009
        advs = db.execute(text("SELECT status FROM vgk_solar_cibil_advances WHERE lead_id = :lid AND kind = 'DVR_ADVANCE'"), {"lid": lead_id}).fetchall()
        for a in advs:
            self.assertEqual(a.status, 'PENDING')

        vcis = db.execute(text("SELECT status FROM vgk_cash_income_entries WHERE source_lead_id = :lid AND kind = 'DVR_ADVANCE'"), {"lid": lead_id}).fetchall()
        for v in vcis:
            self.assertEqual(v.status, 'PENDING')

    def test_13_dvr_creation_does_not_credit_wallet(self):
        """TEST 13: Creation of DVR advance does not credit wallet or insert wallet txns."""
        db = self.db
        lead_id = 99010
        self._create_test_lead(lead_id=lead_id, sps='installation_pending', dvr=200000.00)
        
        # Reset partner wallet balance to 0 before creation
        db.execute(text("UPDATE official_partners SET vgk_cash_wallet = 0.00 WHERE id = 99152"))
        db.commit()

        check_and_create_dvr_advance(db, lead_id)

        wallet_bal = db.execute(text("SELECT vgk_cash_wallet FROM official_partners WHERE id = 99152")).scalar()
        self.assertEqual(Decimal(str(wallet_bal)), Decimal('0.00'))

        txns = db.execute(text("""
            SELECT t.id FROM vgk_wallet_transactions t
            JOIN vgk_solar_cibil_advances a ON t.ref_id = a.id
            WHERE a.lead_id = :lid AND a.kind = 'DVR_ADVANCE'
        """), {"lid": lead_id}).fetchall()
        self.assertEqual(len(txns), 0)

    def test_14_release_remains_idempotent(self):
        """TEST 14: Release of DVR advance executes accounting audit trail and prevents double release."""
        db = self.db
        lead_id = 99010

        # Initial release
        res_rel = release_dvr_advance(db, lead_id=lead_id, partner_id=99152, level=1, released_by_id=1, notes="Release Test")
        self.assertTrue(res_rel.get('success'))

        # Verify advance status is RELEASED and wallet_after_release recorded
        adv_row = db.execute(text("""
            SELECT status, wallet_before_release, wallet_after_release, released_by_id
            FROM vgk_solar_cibil_advances
            WHERE lead_id = :lid AND partner_id = 99152 AND kind = 'DVR_ADVANCE'
        """), {"lid": lead_id}).fetchone()
        self.assertIsNotNone(adv_row)
        self.assertEqual(adv_row.status, 'RELEASED')
        self.assertEqual(Decimal(str(adv_row.wallet_after_release)), Decimal(str(adv_row.wallet_before_release)) + Decimal('1000.00'))

        # Verify wallet audit transactions logged for credit and deductions
        txns = db.execute(text("""
            SELECT txn_type, direction, amount
            FROM vgk_wallet_transactions
            WHERE partner_id = 99152 AND ref_type = 'VGK_DVR_ADV' AND ref_id = (
                SELECT id FROM vgk_solar_cibil_advances WHERE lead_id = :lid AND partner_id = 99152 AND kind = 'DVR_ADVANCE'
            )
            ORDER BY id ASC
        """), {"lid": lead_id}).fetchall()
        txn_types = [t.txn_type for t in txns]
        self.assertIn('SOLAR_ADVANCE_CREDIT', txn_types)

        # Count credit transactions
        credit_count_before = len([t for t in txns if t.txn_type == 'SOLAR_ADVANCE_CREDIT'])
        self.assertEqual(credit_count_before, 1)

        # Duplicate release attempt
        res_dup = release_dvr_advance(db, lead_id=lead_id, partner_id=99152, level=1, released_by_id=1)
        self.assertTrue(res_dup.get('already_released') or not res_dup.get('success'))

        # Verify no duplicate credit transaction inserted
        txns_after = db.execute(text("""
            SELECT txn_type FROM vgk_wallet_transactions
            WHERE partner_id = 99152 AND ref_type = 'VGK_DVR_ADV' AND ref_id = (
                SELECT id FROM vgk_solar_cibil_advances WHERE lead_id = :lid AND partner_id = 99152 AND kind = 'DVR_ADVANCE'
            )
        """), {"lid": lead_id}).fetchall()
        credit_count_after = len([t for t in txns_after if t.txn_type == 'SOLAR_ADVANCE_CREDIT'])
        self.assertEqual(credit_count_after, 1)

    def test_15_downstream_rewards_remain_release_dependent(self):
        """TEST 15: Downstream rewards remain release-dependent; unreleased advances stay PENDING."""
        db = self.db
        lead_id = 99011
        self._create_test_lead(lead_id=lead_id, sps='installation_pending', dvr=200000.00)
        check_and_create_dvr_advance(db, lead_id)

        # Check that advance is PENDING, not RELEASED
        adv = db.execute(text("SELECT status FROM vgk_solar_cibil_advances WHERE lead_id = :lid AND level = 1 AND kind = 'DVR_ADVANCE'"), {"lid": lead_id}).fetchone()
        self.assertEqual(adv.status, 'PENDING')

    def test_16_orm_mutation_followed_by_dependent_query_sees_correct_value(self):
        """TEST 16: In-memory ORM mutation with db.flush() enables dependent raw SQL query to read updated deal_value_received."""
        db = self.db
        lead_id = 99012
        self._create_test_lead(lead_id=lead_id, sps='installation_pending', dvr=0.0)

        # ORM model fetch and mutation
        lead = db.query(CRMLead).filter(CRMLead.id == lead_id).first()
        lead.deal_value_received = Decimal('150000.00')

        # Prior to flush, raw SQL sees old value (0.00)
        raw_val_before = db.execute(text("SELECT deal_value_received FROM crm_leads WHERE id = :lid"), {"lid": lead_id}).scalar()
        self.assertEqual(float(raw_val_before or 0), 0.0)

        # Explicit db.flush()
        db.flush()

        # After flush, raw SQL sees updated value (150000.00) within the same transaction
        raw_val_after = db.execute(text("SELECT deal_value_received FROM crm_leads WHERE id = :lid"), {"lid": lead_id}).scalar()
        self.assertEqual(float(raw_val_after), 150000.00)

        db.rollback()

    def test_17_transaction_ordering_does_not_cause_missed_dvr(self):
        """TEST 17: Full sequence of ORM mutation -> db.flush() -> check_and_create_dvr_advance creates DVR advance successfully."""
        db = self.db
        lead_id = 99013
        self._create_test_lead(lead_id=lead_id, sps='installation_pending', dvr=0.0)

        lead = db.query(CRMLead).filter(CRMLead.id == lead_id).first()
        lead.deal_value_received = Decimal('175000.00')
        lead.deal_value_balance = Decimal('25000.00')
        lead.first_payment_received_date = date(2026, 9, 9)

        db.flush()

        res = check_and_create_dvr_advance(db, lead_id)
        self.assertTrue(res.get('created'), f"Failed to create DVR advance: {res}")

        advs = db.execute(text("SELECT id, level FROM vgk_solar_cibil_advances WHERE lead_id = :lid AND kind = 'DVR_ADVANCE'"), {"lid": lead_id}).fetchall()
        self.assertEqual(len(advs), 2)

    def test_18_advance_payout_not_blocked_by_zero_points_balance(self):
        """TEST 18: Milestone advances (kind=ADVANCE) can be marked PAID even when partner points balance is 0."""
        from app.services.vgk_cash_income import mark_paid_cash_income
        from app.models.vgk_cash_income import VGKCashIncomeEntry
        db = self.db
        lead_id = 99014
        partner_id = 99152

        # Ensure partner has 0 points
        db.execute(text("UPDATE official_partners SET vgk_points_balance = 0.00, vgk_cash_wallet = 1000.00 WHERE id = :pid"), {"pid": partner_id})
        db.commit()

        # Create a mock ADVANCE cash income entry in RELEASED status
        entry = VGKCashIncomeEntry(
            company_id=4,
            entry_number="VCI-TEST-ADV-001",
            partner_id=partner_id,
            source_lead_id=lead_id,
            kind="ADVANCE",
            level=1,
            commission_amount=Decimal('1000.00'),
            net_payout=Decimal('900.00'),
            status="RELEASED",
            notes="Test advance entry"
        )
        db.add(entry)
        db.commit()
        db.refresh(entry)

        res = mark_paid_cash_income(
            db=db,
            entry_id=entry.id,
            company_id=4,
            paid_by_id=1,
            payment_mode="BANK",
            utr="TESTUTR123456",
            notes="Testing advance payout with zero points"
        )

        self.assertTrue(res.get('success'), f"Advance payout failed: {res}")
        self.assertEqual(res.get('payment_mode'), 'BANK')

        # Clean up
        db.execute(text("DELETE FROM vgk_points_ledger WHERE reference_type = 'VGK_CASH_INCOME' AND reference_id = :eid"), {"eid": entry.id})
        db.execute(text("DELETE FROM vgk_wallet_transactions WHERE ref_type = 'VGK_CASH_INCOME' AND ref_id = :eid"), {"eid": entry.id})
        db.execute(text("DELETE FROM vgk_cash_income_entries WHERE id = :eid"), {"eid": entry.id})
        db.commit()

    def test_19_commission_payout_still_gated_by_points_capacity(self):
        """TEST 19: Full COMMISSION entries remain protected by points capacity gate when points are insufficient."""
        from app.services.vgk_cash_income import mark_paid_cash_income
        from app.models.vgk_cash_income import VGKCashIncomeEntry
        db = self.db
        lead_id = 99015
        partner_id = 99152

        # Ensure partner has 0 points
        db.execute(text("UPDATE official_partners SET vgk_points_balance = 0.00 WHERE id = :pid"), {"pid": partner_id})
        db.commit()

        # Create a COMMISSION entry
        entry = VGKCashIncomeEntry(
            company_id=4,
            entry_number="VCI-TEST-COMM-001",
            partner_id=partner_id,
            source_lead_id=lead_id,
            kind="COMMISSION",
            level=1,
            commission_amount=Decimal('5000.00'),
            net_payout=Decimal('4500.00'),
            status="RELEASED",
            notes="Test commission entry"
        )
        db.add(entry)
        db.commit()
        db.refresh(entry)

        res = mark_paid_cash_income(
            db=db,
            entry_id=entry.id,
            company_id=4,
            paid_by_id=1,
            payment_mode="BANK",
            utr="TESTUTR999999",
            notes="Testing commission payout with zero points"
        )

        # Should be blocked
        self.assertFalse(res.get('success'))
        self.assertEqual(res.get('error'), 'INSUFFICIENT_POINTS_FOR_PAYOUT')

        # Clean up
        db.execute(text("DELETE FROM vgk_cash_income_entries WHERE id = :eid"), {"eid": entry.id})
        db.commit()

    def test_20_single_file_partner_not_blocked_by_50_pct_cap(self):
        """TEST 20: Partner with 1 active file has cap_limit >= 1 and is not capped on their first file."""
        from app.services.vgk_advance_cap import get_cap_status
        db = self.db
        partner_id = 99152

        # Insert 1 eligible advance lead
        lead_id = 99016
        self._create_test_lead(lead_id=lead_id, sps='with_bank', dvr=0.0)
        db.execute(text("""
            INSERT INTO vgk_solar_cibil_advances
                (company_id, lead_id, partner_id, entry_number, advance_amount, status, level, kind)
            VALUES
                (4, :lid, :pid, 'VSCA-TEST-CAP-1', 1000.00, 'PENDING', 1, 'ADVANCE')
        """), {"lid": lead_id, "pid": partner_id})
        db.commit()

        status = get_cap_status(db, partner_id=partner_id, company_id=4)
        self.assertGreaterEqual(status.get('eligible_files', 0), 1)
        self.assertGreaterEqual(status.get('cap_limit', 0), 1)
        self.assertFalse(status.get('is_capped'), "Partner with 1 eligible file should not be capped")

        # Clean up
        db.execute(text("DELETE FROM vgk_solar_cibil_advances WHERE entry_number = 'VSCA-TEST-CAP-1'"))
        db.execute(text("DELETE FROM crm_leads WHERE id = :lid"), {"lid": lead_id})
        db.commit()

    def test_21_dvr_advance_release_not_blocked_by_zero_points(self):
        """TEST 21: release_dvr_advance succeeds even if partner has 0 points balance (DC-NO-PTS-GATE-002)."""
        db = self.db
        lead_id = 99017
        partner_id = 99152

        # Create test lead & DVR advance row
        self._create_test_lead(lead_id=lead_id, sps='installation_pending', dvr=100000.00)
        db.execute(text("""
            INSERT INTO vgk_solar_cibil_advances
                (company_id, lead_id, partner_id, entry_number, advance_amount, status, level, kind)
            VALUES
                (4, :lid, :pid, 'VSCA-TEST-DVR-001', 1000.00, 'PENDING', 1, 'DVR_ADVANCE')
        """), {"lid": lead_id, "pid": partner_id})
        # Set partner points to 0
        db.execute(text("UPDATE official_partners SET vgk_points_balance = 0.00 WHERE id = :pid"), {"pid": partner_id})
        db.commit()

        res = release_dvr_advance(db, lead_id=lead_id, partner_id=partner_id, level=1, released_by_id=1)
        self.assertTrue(res.get('success'), f"release_dvr_advance should succeed with 0 points: {res}")

        # Clean up
        db.execute(text("DELETE FROM vgk_wallet_transactions WHERE ref_type = 'VGK_DVR_ADV' AND partner_id = :pid"), {"pid": partner_id})
        db.execute(text("DELETE FROM vgk_solar_cibil_advances WHERE entry_number = 'VSCA-TEST-DVR-001'"))
        db.execute(text("DELETE FROM crm_leads WHERE id = :lid"), {"lid": lead_id})
        db.commit()

    def test_22_deficit_advance_can_be_released(self):
        """TEST 22: release_advance can process and heal legacy DEFICIT status advance rows."""
        from app.services.vgk_solar_advance import release_advance
        db = self.db
        lead_id = 99018
        partner_id = 99152

        self._create_test_lead(lead_id=lead_id, sps='with_bank', dvr=0.0)
        db.execute(text("""
            INSERT INTO vgk_solar_cibil_advances
                (company_id, lead_id, partner_id, entry_number, advance_amount, status, level, kind)
            VALUES
                (4, :lid, :pid, 'VSCA-TEST-DEF-001', 1000.00, 'DEFICIT', 1, 'ADVANCE')
        """), {"lid": lead_id, "pid": partner_id})
        db.commit()

        res = release_advance(db, lead_id=lead_id, released_by_id=1, _level=1)
        self.assertTrue(res.get('success'), f"release_advance should succeed for DEFICIT status: {res}")

        # Clean up
        db.execute(text("DELETE FROM vgk_wallet_transactions WHERE ref_type = 'VGK_SOLAR_ADV' AND partner_id = :pid"), {"pid": partner_id})
        db.execute(text("DELETE FROM vgk_solar_cibil_advances WHERE entry_number = 'VSCA-TEST-DEF-001'"))
        db.execute(text("DELETE FROM crm_leads WHERE id = :lid"), {"lid": lead_id})
        db.commit()


if __name__ == '__main__':
    unittest.main()
