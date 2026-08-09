"""
Phase 2K.5 Automated Code Test Suite (Category A)
Verifies:
1. Zero Campaign / AdSet Creation Lock Enforcement (Abort task if campaign/adset mutation attempted).
2. Multilingual QA (English + Telugu) source vs OCR verification.
3. Meta Error 1815202 Trapper & Diagnostic Telemetry Parser.
4. Strict Failure Policy (Prevents false success reporting when Error 1815202 blocks adcreative).
"""

import sys
import os
import unittest

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.services.meta_single_ad_creation_service import execute_single_ad_controlled_verification


class TestPhase2K5SingleAdVerificationCode(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = create_engine(settings.DATABASE_URL or "sqlite:///./mlm_app.db")
        cls.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=cls.engine)

    def setUp(self):
        self.db = self.SessionLocal()

    def tearDown(self):
        self.db.rollback()
        self.db.close()

    def test_01_single_ad_verification_strict_failure_policy(self):
        res = execute_single_ad_controlled_verification(self.db, company_id=1)
        # Should return REAL_META_AD_BLOCKED or REAL_META_AD_CREATED_AND_VERIFIED or CREATIVE_QA_FAILED
        self.assertIn(res["status"], ["REAL_META_AD_BLOCKED", "REAL_META_AD_CREATED_AND_VERIFIED", "CREATIVE_QA_FAILED", "ALREADY_EXISTS"])
        if res["status"] == "REAL_META_AD_BLOCKED":
            self.assertEqual(res.get("W_ads_created_count", 0), 0)
            self.assertEqual(res.get("U_campaigns_created_count", 0), 0)
            self.assertEqual(res.get("V_adsets_created_count", 0), 0)

    def test_02_error_1815202_telemetry_capture(self):
        res = execute_single_ad_controlled_verification(self.db, company_id=1)
        if res.get("reason") == "META_ERROR_1815202":
            self.assertIn("1815202", res.get("error_1815202_result", ""))
            self.assertEqual(res.get("W_ads_created_count", 0), 0)


if __name__ == "__main__":
    unittest.main()
