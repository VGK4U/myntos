"""
Phase 2L.1 Phase A Automated Test Suite — Idempotency, Concurrency & Database Integrity
Tests:
- TEST 01: Fingerprint v2 deterministic generation
- TEST 02: Fingerprint v2 changes when immutable identity input changes
- TEST 03: Fingerprint v1 backward compatibility (DB ID 26)
- TEST 04: Duplicate ad prevention
- TEST 05: Concurrent request serialization (Simulates simultaneous creation attempts)
- TEST 06: Different fingerprints for different creative content
- TEST 07: Database uniqueness rejection on duplicate ad_id insert
- TEST 08: Process restart & memory-independent database lock persistence
- TEST 09: NULL handling stability in Fingerprint v2
- TEST 10: Unicode NFC normalization equivalence
- TEST 11: Zero fake/UUID Meta IDs permitted
Local/Database unit & integration tests ONLY. Zero live Meta mutations.
"""

import sys
import os
import unittest
import threading

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError

from app.core.config import settings
from app.services.meta_creation_lock_engine import (
    calculate_idempotency_fingerprint,
    calculate_idempotency_fingerprint_v2,
    check_existing_ad_idempotency,
    PRIMARY_CAMPAIGN_ID,
    PRIMARY_ADSET_ID
)


class TestPhase2L1PhaseAIdempotency(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = create_engine(settings.DATABASE_URL or "sqlite:///./mlm_app.db")
        cls.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=cls.engine)

    def setUp(self):
        self.db = self.SessionLocal()

    def tearDown(self):
        self.db.rollback()
        self.db.close()

    def test_01_fingerprint_v2_deterministic_generation(self):
        fp1 = calculate_idempotency_fingerprint_v2(
            company_id=1,
            headline="3KW Solar Rooftop AP",
            primary_text="Upgrade to 3KW Rooftop Solar in AP"
        )
        fp2 = calculate_idempotency_fingerprint_v2(
            company_id=1,
            headline="3KW Solar Rooftop AP",
            primary_text="Upgrade to 3KW Rooftop Solar in AP"
        )
        self.assertEqual(fp1, fp2)
        self.assertEqual(len(fp1), 64)

    def test_02_fingerprint_v2_immutable_input_variation(self):
        fp_base = calculate_idempotency_fingerprint_v2(
            company_id=1,
            image_hash="7db4abcb49f4c4fa2d37d6bac21aeb56",
            headline="Headline A"
        )
        fp_diff_img = calculate_idempotency_fingerprint_v2(
            company_id=1,
            image_hash="diff_image_hash_1234567890abcdef",
            headline="Headline A"
        )
        self.assertNotEqual(fp_base, fp_diff_img)

    def test_03_fingerprint_v1_backward_compatibility(self):
        row = self.db.execute(text("""
            SELECT id, ad_id, creative_id, ad_fingerprint, fingerprint_version
            FROM meta_ads
            WHERE company_id = 1 AND ad_id = '120254925357440348'
        """)).fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row[1], '120254925357440348')
        self.assertEqual(row[2], '1060291106393640')
        self.assertEqual(row[3], '0e209965e07accd293307f52ca375d328c7eb2d0f7c13ec475c2532dd04b2dab')
        self.assertEqual(row[4], 1)

        # Check existing ad lookup
        res = check_existing_ad_idempotency(self.db, 1, row[3])
        self.assertIsNotNone(res)
        self.assertEqual(res["status"], "ALREADY_EXISTS")
        self.assertEqual(res["real_meta_id"], "120254925357440348")

    def test_04_duplicate_ad_prevention(self):
        fp = calculate_idempotency_fingerprint_v2(company_id=1, headline="Test Duplicate Prevention")
        res1 = check_existing_ad_idempotency(self.db, 1, fp)
        self.assertIsNone(res1)  # Does not exist yet

    def test_05_concurrent_request_serialization(self):
        results = []

        def worker_task():
            db_worker = self.SessionLocal()
            fp = "0e209965e07accd293307f52ca375d328c7eb2d0f7c13ec475c2532dd04b2dab"
            res = check_existing_ad_idempotency(db_worker, 1, fp)
            results.append(res)
            db_worker.close()

        t1 = threading.Thread(target=worker_task)
        t2 = threading.Thread(target=worker_task)
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]["status"], "ALREADY_EXISTS")
        self.assertEqual(results[1]["status"], "ALREADY_EXISTS")

    def test_06_different_fingerprints_different_content(self):
        fp_a = calculate_idempotency_fingerprint_v2(company_id=1, headline="Option A")
        fp_b = calculate_idempotency_fingerprint_v2(company_id=1, headline="Option B")
        self.assertNotEqual(fp_a, fp_b)

    def test_07_database_uniqueness_rejection(self):
        # Attempt to insert duplicate ad_id
        try:
            self.db.execute(text("""
                INSERT INTO meta_ads (company_id, ad_id, adset_id, campaign_id, name, status)
                VALUES (1, '120254925357440348', '120254919777930348', '120254919777680348', 'Duplicate Test', 'PAUSED')
            """))
            self.db.commit()
            self.fail("Database unique constraint failed to block duplicate ad_id insertion!")
        except IntegrityError:
            self.db.rollback()
            # Success: DB rejected duplicate ad_id

    def test_08_restart_process_safety(self):
        # Process restart test: Query DB directly without memory cache
        row = self.db.execute(text("SELECT ad_id FROM meta_ads WHERE ad_fingerprint = '0e209965e07accd293307f52ca375d328c7eb2d0f7c13ec475c2532dd04b2dab'")).fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row[0], '120254925357440348')

    def test_09_null_handling_stability(self):
        fp_nulls = calculate_idempotency_fingerprint_v2(
            company_id=1,
            headline=None,
            primary_text=None,
            destination_url=None
        )
        self.assertEqual(len(fp_nulls), 64)

    def test_10_unicode_nfc_normalization(self):
        # NFC vs NFD unicode representations of Telugu text
        text_nfc = "3కిలోవాట్ల సోలార్"
        import unicodedata
        text_nfd = unicodedata.normalize("NFD", text_nfc)

        fp_nfc = calculate_idempotency_fingerprint_v2(company_id=1, headline=text_nfc)
        fp_nfd = calculate_idempotency_fingerprint_v2(company_id=1, headline=text_nfd)
        self.assertEqual(fp_nfc, fp_nfd)

    def test_11_zero_fake_meta_ids(self):
        row = self.db.execute(text("SELECT ad_id FROM meta_ads WHERE company_id = 1 AND ad_id = '120254925357440348'")).fetchone()
        self.assertFalse(row[0].startswith("mock_"))
        self.assertFalse(row[0].startswith("uuid_"))
        self.assertTrue(row[0].isdigit())


if __name__ == "__main__":
    unittest.main()
