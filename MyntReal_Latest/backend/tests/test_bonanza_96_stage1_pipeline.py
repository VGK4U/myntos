import os
import sys
import unittest
from decimal import Decimal
from datetime import datetime, date

# Add backend directory to sys.path
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, backend_dir)

from dotenv import load_dotenv
load_dotenv(os.path.join(backend_dir, ".env"))

from sqlalchemy import text
from app.core.database import SessionLocal
from app.models.crm import CRMLead
from app.models.staff_accounts import OfficialPartner
from app.services.vgk_solar_advance import check_and_create_advance, release_advance
from app.services.vgk_extra_commission import apply_extra_commission_if_active


class TestBonanza96Stage1Pipeline(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db = SessionLocal()
        cls.cleanup_ids = []
        try:
            cls.db.execute(text("DELETE FROM official_partners WHERE partner_code LIKE 'TEST_B96_%' OR phone LIKE '999999901%'"))
            cls.db.execute(text("DELETE FROM crm_leads WHERE phone LIKE '999999901%'"))
            cls.db.commit()
        except Exception:
            cls.db.rollback()

    @classmethod
    def tearDownClass(cls):
        # Clean up test entities
        try:
            for lid in cls.cleanup_ids:
                cls.db.execute(text("DELETE FROM bonanza_extra_commission_log WHERE lead_id = :lid"), {"lid": lid})
                cls.db.execute(text("DELETE FROM vgk_cash_income_entries WHERE source_lead_id = :lid"), {"lid": lid})
                cls.db.execute(text("DELETE FROM vgk_solar_cibil_advances WHERE lead_id = :lid"), {"lid": lid})
                cls.db.execute(text("DELETE FROM crm_leads WHERE id = :lid"), {"lid": lid})
            cls.db.execute(text("DELETE FROM official_partners WHERE partner_code LIKE 'TEST_B96_%'"))
            cls.db.commit()
        except Exception:
            cls.db.rollback()
        finally:
            cls.db.close()

    def test_full_stage1_pipeline_and_idempotency(self):
        db = self.db

        # 1. Ensure Bonanza #96 exists in dev DB
        db.execute(text("""
            INSERT INTO bonanza (id, name, start_date, end_date, grace_days, reward_type,
                                ec_l1_amount, ec_l2_amount, ec_l1_trigger, ec_l2_trigger,
                                status, is_deleted, advance_count_basis, criteria_type, target_requirement)
            VALUES (96, 'Extra Bonanza September 2026', '2026-09-10 00:00:00', '2026-09-20 00:00:00',
                    0, 'extra_commission', 1000.00, 500.00, 'file_submitted', 'file_submitted',
                    'Approved', false, 'CIBIL', 'completed_deals', 0)
            ON CONFLICT (id) DO UPDATE SET
                start_date = '2026-09-10 00:00:00',
                end_date = '2026-09-20 00:00:00',
                status = 'Approved',
                is_deleted = false,
                reward_type = 'extra_commission',
                ec_l1_amount = 1000.00,
                ec_l2_amount = 500.00,
                ec_l1_trigger = 'file_submitted',
                ec_l2_trigger = 'file_submitted'
        """))
        db.commit()

        # 2. Create test partners
        p1 = db.execute(text("""
            INSERT INTO official_partners (partner_code, partner_name, phone, category, is_active, vgk_cash_wallet, company_id, created_at, updated_at)
            VALUES ('TEST_B96_P1', 'Test L1 Partner', '9999999011', 'VGK_TEAM', true, 0, 4, NOW(), NOW())
            RETURNING id
        """)).scalar()
        p2 = db.execute(text("""
            INSERT INTO official_partners (partner_code, partner_name, phone, category, is_active, vgk_cash_wallet, company_id, created_at, updated_at)
            VALUES ('TEST_B96_P2', 'Test L2 Partner', '9999999012', 'VGK_TEAM', true, 0, 4, NOW(), NOW())
            RETURNING id
        """)).scalar()
        db.commit()

        # 3. Create test qualifying solar lead in Bonanza window (submit_date = 2026-09-12)
        lead_id = db.execute(text("""
            INSERT INTO crm_leads (
                company_id, name, phone, category_id, solar_pipeline_status,
                cibil_score, cibil_confirmed, submit_date, created_at,
                associated_partner_id, team_senior_partner_id, status, priority, handler_type
            ) VALUES (
                4, 'Test Lead B96 Qualified', '9999999013', 6, 'pending_with_bank',
                720, true, '2026-09-12', '2026-09-12 10:00:00',
                :p1, :p2, 'active', 'medium', 'partner'
            ) RETURNING id
        """), {"p1": p1, "p2": p2}).scalar()
        db.commit()
        self.cleanup_ids.append(lead_id)

        # 4. FIRST EXECUTION: Call check_and_create_advance
        res1 = check_and_create_advance(db, lead_id)
        self.assertTrue(res1.get('created'), f"Expected advance creation to succeed, got: {res1}")

        # Check advances created in vgk_solar_cibil_advances
        advs = db.execute(text("""
            SELECT id, level, partner_id, advance_amount, status
            FROM vgk_solar_cibil_advances
            WHERE lead_id = :lid ORDER BY level
        """), {"lid": lead_id}).fetchall()
        self.assertEqual(len(advs), 2, "Expected 2 advance rows (L1 and L2)")
        self.assertEqual(advs[0].level, 1)
        self.assertEqual(advs[0].partner_id, p1)
        self.assertEqual(Decimal(str(advs[0].advance_amount)), Decimal('1000.00'))
        self.assertEqual(advs[1].level, 2)
        self.assertEqual(advs[1].partner_id, p2)
        self.assertEqual(Decimal(str(advs[1].advance_amount)), Decimal('500.00'))

        # Check vgk_cash_income_entries: ADVANCE rows
        adv_vcis = db.execute(text("""
            SELECT id, level, partner_id, commission_amount, status, kind
            FROM vgk_cash_income_entries
            WHERE source_lead_id = :lid AND kind = 'ADVANCE' ORDER BY level
        """), {"lid": lead_id}).fetchall()
        self.assertEqual(len(adv_vcis), 2, "Expected 2 ADVANCE mirror rows")
        self.assertEqual(adv_vcis[0].status, 'STAGE1_APPROVED')
        self.assertEqual(Decimal(str(adv_vcis[0].commission_amount)), Decimal('1000.00'))
        self.assertEqual(adv_vcis[1].status, 'STAGE1_APPROVED')
        self.assertEqual(Decimal(str(adv_vcis[1].commission_amount)), Decimal('500.00'))

        # Check vgk_cash_income_entries: Bonanza #96 EXTRA_COMMISSION rows
        ec_vcis = db.execute(text("""
            SELECT id, level, partner_id, commission_amount, status, kind, bonanza_id
            FROM vgk_cash_income_entries
            WHERE source_lead_id = :lid AND kind = 'EXTRA_COMMISSION' ORDER BY level
        """), {"lid": lead_id}).fetchall()
        self.assertEqual(len(ec_vcis), 2, "Expected 2 Bonanza #96 EXTRA_COMMISSION rows")
        self.assertEqual(ec_vcis[0].level, 1)
        self.assertEqual(ec_vcis[0].partner_id, p1)
        self.assertEqual(ec_vcis[0].bonanza_id, 96)
        self.assertEqual(Decimal(str(ec_vcis[0].commission_amount)), Decimal('1000.00'))
        self.assertEqual(ec_vcis[0].status, 'PENDING')

        self.assertEqual(ec_vcis[1].level, 2)
        self.assertEqual(ec_vcis[1].partner_id, p2)
        self.assertEqual(ec_vcis[1].bonanza_id, 96)
        self.assertEqual(Decimal(str(ec_vcis[1].commission_amount)), Decimal('500.00'))
        self.assertEqual(ec_vcis[1].status, 'PENDING')

        # Check bonanza_extra_commission_log entries
        ec_logs = db.execute(text("""
            SELECT id, bonanza_id, lead_id, level, partner_id
            FROM bonanza_extra_commission_log
            WHERE lead_id = :lid ORDER BY level
        """), {"lid": lead_id}).fetchall()
        self.assertEqual(len(ec_logs), 2, "Expected 2 bonanza_extra_commission_log rows")
        self.assertEqual(ec_logs[0].level, 1)
        self.assertEqual(ec_logs[1].level, 2)

        # 5. SECOND EXECUTION: Call check_and_create_advance again on same lead
        res2 = check_and_create_advance(db, lead_id)
        self.assertFalse(res2.get('created'), "Expected second execution to be idempotent (created=False)")
        self.assertEqual(res2.get('reason'), 'All advances already existed')

        # Assert no duplicates were created
        total_vcis = db.execute(text("""
            SELECT count(*) FROM vgk_cash_income_entries WHERE source_lead_id = :lid
        """), {"lid": lead_id}).scalar()
        self.assertEqual(total_vcis, 4, "Total income entries must remain exactly 4 (2 ADVANCE + 2 EXTRA_COMMISSION)")

        total_logs = db.execute(text("""
            SELECT count(*) FROM bonanza_extra_commission_log WHERE lead_id = :lid
        """), {"lid": lead_id}).scalar()
        self.assertEqual(total_logs, 2, "Total bonanza log rows must remain exactly 2")

        # 6. SUBSEQUENT release_advance() CALL: Verify no duplicate bonanza rewards
        rel_res = release_advance(db, lead_id=lead_id, released_by_id=1, _level=1)
        # Advance is already STAGE1_APPROVED / not pending or already handled
        total_vcis_after_rel = db.execute(text("""
            SELECT count(*) FROM vgk_cash_income_entries WHERE source_lead_id = :lid
        """), {"lid": lead_id}).scalar()
        self.assertEqual(total_vcis_after_rel, 4, "Total income entries must remain 4 after release_advance()")

        # 7. LEVEL 0 (SLAB_BONUS) AGGREGATION VERIFICATION:
        # Insert a genuine SLAB_BONUS entry with level=0 for Partner 1
        db.execute(text("""
            INSERT INTO vgk_cash_income_entries (
                company_id, entry_number, partner_id, source_lead_id, level,
                kind, status, commission_amount, net_payout, created_at, updated_at
            ) VALUES (
                4, 'TEST-SLAB-001', :p1, :lid, 0,
                'SLAB_BONUS', 'STAGE1_APPROVED', 3000.00, 2700.00, '2026-09-12 11:00:00', '2026-09-12 11:00:00'
            )
        """), {"p1": p1, "lid": lead_id})
        db.commit()

        # Simulate the member_earnings_dashboard query and loop
        cibil_join_sql = " LEFT JOIN vgk_solar_cibil_advances _cba ON (_cba.lead_id = e.source_lead_id AND _cba.partner_id = e.partner_id AND _cba.level = e.level) "
        cust_join_sql = " LEFT JOIN crm_leads _cbl ON _cbl.id = e.source_lead_id "
        combined_sql = (
            "SELECT e.partner_id, e.status, e.level, e.source_lead_id, e.commission_amount, e.net_payout, "
            "       (_cbl.status IN ('completed', 'installed', 'subsidy_pending') OR _cbl.solar_pipeline_status IN ('completed', 'subsidy_pending', 'subsidy_received', 'net_meter_done', 'installed', 'net_meter_pending', 'balance_pending', 'balance_received')) AS is_installed "
            "FROM vgk_cash_income_entries e " + cibil_join_sql + cust_join_sql +
            " WHERE e.partner_id = :pid AND e.status != 'CANCELLED'"
        )
        combined_rows = db.execute(text(combined_sql), {"pid": p1}).fetchall()

        lvl_map = {}
        for pid_raw, st, lv_raw, lid, comm_amt, net_p, is_inst in combined_rows:
            pid = int(pid_raw)
            if st != 'CANCELLED':
                # Exact line from our vgk_team.py fix:
                lv = int(lv_raw) if lv_raw is not None else 1
                if pid not in lvl_map:
                    lvl_map[pid] = {}
                lv_entry = lvl_map[pid].setdefault(lv, {"count": 0, "amount": 0.0, "net_amount": 0.0})
                lv_entry["count"] += 1
                lv_entry["amount"] += float(comm_amt or 0)
                lv_entry["net_amount"] += float(net_p or 0)

        p1_lvl = lvl_map.get(p1, {})
        l0_bonus = float(p1_lvl.get(0, {}).get("amount", 0))
        l1_source = float(p1_lvl.get(1, {}).get("amount", 0))

        self.assertEqual(l0_bonus, 3000.0, f"Expected l0_bonus=3000.0, got {l0_bonus}")
        self.assertEqual(l1_source, 2000.0, f"Expected l1_source=2000.0 (1000 Advance + 1000 Bonanza EC), got {l1_source}")

        # 8. OUTSIDE WINDOW (NO ACTIVE BONANZA) TEST:
        # Create a lead with submit_date = 2026-11-01 (outside Bonanza #96)
        lead2_id = db.execute(text("""
            INSERT INTO crm_leads (
                company_id, name, phone, category_id, solar_pipeline_status,
                cibil_score, cibil_confirmed, submit_date, created_at,
                associated_partner_id, team_senior_partner_id, status, priority, handler_type
            ) VALUES (
                4, 'Test Lead Outside Window', '9999999014', 6, 'pending_with_bank',
                730, true, '2026-11-01', '2026-11-01 10:00:00',
                :p1, :p2, 'active', 'medium', 'partner'
            ) RETURNING id
        """), {"p1": p1, "p2": p2}).scalar()
        db.commit()
        self.cleanup_ids.append(lead2_id)

        res_outside = check_and_create_advance(db, lead2_id)
        self.assertTrue(res_outside.get('created'))
        
        # Advances exist
        adv2_count = db.execute(text("""
            SELECT count(*) FROM vgk_solar_cibil_advances WHERE lead_id = :lid
        """), {"lid": lead2_id}).scalar()
        self.assertEqual(adv2_count, 2)

        # Zero Bonanza #96 Extra Commission entries because submit_date is in November
        b96_count_outside = db.execute(text("""
            SELECT count(*) FROM vgk_cash_income_entries
            WHERE source_lead_id = :lid AND kind = 'EXTRA_COMMISSION' AND bonanza_id = 96
        """), {"lid": lead2_id}).scalar()
        self.assertEqual(b96_count_outside, 0, "No Bonanza #96 extra commissions should be created outside window")

    def test_bonanza_97_isolation_and_triggers(self):
        db = self.db

        # Verify Bonanza #97 properties: reward_type='award', qualification_event='first_payment'
        b97 = db.execute(text("""
            SELECT id, name, reward_type, qualification_event, advance_count_basis
            FROM bonanza WHERE id = 97
        """)).fetchone()
        if not b97:
            # Insert if not present in dev
            db.execute(text("""
                INSERT INTO bonanza (id, name, start_date, end_date, grace_days, reward_type,
                                    status, is_deleted, advance_count_basis, criteria_type, target_requirement,
                                    qualification_event, award_name, is_monetary)
                VALUES (97, 'Mega Solar Festival Bonanza 2026', '2026-09-01 00:00:00', '2026-10-31 23:59:59',
                        15, 'award', 'Approved', false, 'DVR', 'completed_deals', 3,
                        'first_payment', 'Solar Festival Milestones', true)
                ON CONFLICT (id) DO NOTHING
            """))
            db.commit()

        # Create test partner and qualifying Stage 1 lead in September
        p1 = db.execute(text("""
            INSERT INTO official_partners (partner_code, partner_name, phone, category, is_active, vgk_cash_wallet, company_id, created_at, updated_at)
            VALUES ('TEST_B96_P3', 'Test L1 Isolation', '9999999015', 'VGK_TEAM', true, 0, 4, NOW(), NOW())
            RETURNING id
        """)).scalar()
        db.commit()

        lead_id = db.execute(text("""
            INSERT INTO crm_leads (
                company_id, name, phone, category_id, solar_pipeline_status,
                cibil_score, cibil_confirmed, submit_date, created_at,
                associated_partner_id, status, priority, handler_type
            ) VALUES (
                4, 'Test Lead B97 Isolation', '9999999016', 6, 'pending_with_bank',
                740, true, '2026-09-15', '2026-09-15 10:00:00',
                :p1, 'active', 'medium', 'partner'
            ) RETURNING id
        """), {"p1": p1}).scalar()
        db.commit()
        self.cleanup_ids.append(lead_id)

        # Trigger Stage 1
        res = check_and_create_advance(db, lead_id)
        self.assertTrue(res.get('created'))

        # Assert Bonanza #96 WAS triggered (file_submitted EC)
        b96_cnt = db.execute(text("""
            SELECT count(*) FROM vgk_cash_income_entries
            WHERE source_lead_id = :lid AND kind = 'EXTRA_COMMISSION' AND bonanza_id = 96
        """), {"lid": lead_id}).scalar()
        self.assertEqual(b96_cnt, 1, "Bonanza #96 should fire for L1")

        # Assert Bonanza #97 was NOT triggered (it is an award for first_payment/DVR, not file_submitted)
        b97_cnt = db.execute(text("""
            SELECT count(*) FROM vgk_cash_income_entries
            WHERE source_lead_id = :lid AND bonanza_id = 97
        """), {"lid": lead_id}).scalar()
        self.assertEqual(b97_cnt, 0, "Bonanza #97 must NOT fire on Stage 1 CIBIL advance")


if __name__ == '__main__':
    unittest.main()

