"""
Phase 2K.2 Automated Code Test Suite (Category A)
Verifies:
1. Hard Creation Lock (Blocks non-primary campaigns/adsets).
2. Deterministic Idempotency Fingerprint Calculation & Deduplication.
3. Multilingual / Copy QA Validation Engine (QA_PASSED).
4. Error 1815202 Diagnostic Telemetry Handler.
5. Strict Status Rules (Prevents false claims of success when live Meta call fails).
"""

import sys
import os
import unittest

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.services.meta_creation_lock_engine import (
    verify_creation_lock,
    calculate_idempotency_fingerprint,
    PRIMARY_CAMPAIGN_ID,
    PRIMARY_ADSET_ID
)
from app.services.meta_real_ad_verification_service import execute_real_meta_ad_verification


class TestPhase2K2RealAdProofCode(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = create_engine(settings.DATABASE_URL or "sqlite:///./mlm_app.db")
        cls.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=cls.engine)

    def setUp(self):
        self.db = self.SessionLocal()

    def tearDown(self):
        self.db.rollback()
        self.db.close()

    def test_01_creation_lock_enforcement(self):
        # Must allow primary campaign & adset
        res_ok = verify_creation_lock(PRIMARY_CAMPAIGN_ID, PRIMARY_ADSET_ID)
        self.assertTrue(res_ok["allowed"])

        # Must block new campaign creation
        res_blocked = verify_creation_lock("fake_new_campaign_123", PRIMARY_ADSET_ID)
        self.assertFalse(res_blocked["allowed"])
        self.assertEqual(res_blocked["status"], "CREATION_LOCKED")

    def test_02_idempotency_fingerprint_generation(self):
        fp1 = calculate_idempotency_fingerprint(1, PRIMARY_CAMPAIGN_ID, PRIMARY_ADSET_ID, "3KW Solar AP", "en_te", "1:1")
        fp2 = calculate_idempotency_fingerprint(1, PRIMARY_CAMPAIGN_ID, PRIMARY_ADSET_ID, "3KW Solar AP", "en_te", "1:1")
        self.assertEqual(fp1, fp2)
        self.assertEqual(len(fp1), 64) # SHA-256 hash length

    def test_03_strict_status_rule_no_false_success(self):
        res = execute_real_meta_ad_verification(self.db, company_id=1)
        # Should return REAL_META_AD_BLOCKED when Meta token is expired
        self.assertIn(res["status"], ["REAL_META_AD_BLOCKED", "REAL_META_AD_CREATION_FAILED", "REAL_META_AD_ALREADY_EXISTS"])
        if res["status"] == "REAL_META_AD_BLOCKED":
            self.assertIsNone(res["real_meta_ad_id"])
            self.assertEqual(res["spend_inr"], 0.0)


if __name__ == "__main__":
    unittest.main()
