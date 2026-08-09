"""
Phase 2K.3 Automated Test Suite for Token Expiration & Health Verification
Verifies:
1. Token Expiration Protection Handler (190 / 463 error code handling).
2. AES-256-GCM Encryption & Token Security Compliance.
3. Write Protection Safety Enforcement (META_ADS_WRITE_ENABLED = False).
4. Re-authorization OAuth Login URL Generator with required permissions.
5. Strict Status Rules (Prevents false claims when OAuth token is expired).
"""

import sys
import os
import unittest

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.services.meta_token_health_service import (
    verify_meta_oauth_token_health,
    evaluate_token_expiration_protection,
    get_oauth_login_url
)


class TestPhase2K3TokenHealth(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = create_engine(settings.DATABASE_URL or "sqlite:///./mlm_app.db")
        cls.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=cls.engine)

    def setUp(self):
        self.db = self.SessionLocal()

    def tearDown(self):
        self.db.rollback()
        self.db.close()

    def test_01_token_expiration_protection_handler(self):
        handler = evaluate_token_expiration_protection(190, 463)
        self.assertEqual(handler["status"], "AUTH_EXPIRED")
        self.assertFalse(handler["meta_write_enabled"])
        self.assertTrue(handler["stop_retry_loops"])
        self.assertTrue(handler["stop_ad_creation"])
        self.assertTrue(handler["reauthorization_required"])
        self.assertFalse(handler["fallback_ids_allowed"])

    def test_02_oauth_login_url_permissions(self):
        url = get_oauth_login_url(company_id=1)
        self.assertIn("dialog/oauth", url)
        self.assertIn("ads_read", url)
        self.assertIn("read_insights", url)
        self.assertIn("leads_retrieval", url)
        self.assertIn("pages_show_list", url)
        self.assertIn("ads_management", url)

    def test_03_token_health_verification_read_only(self):
        res = verify_meta_oauth_token_health(self.db, company_id=1)
        self.assertIn(res["status"], ["META_REAUTHORIZATION_REQUIRED", "META_AUTHENTICATION_FAILED", "META_AUTHENTICATION_RESTORED"])
        self.assertEqual(res["token_encryption"], "PASS")
        self.assertEqual(res["write_protection"], "PASS")
        self.assertEqual(res["fallback_protection"], "PASS")
        self.assertEqual(res["error_1815202_result"], "NOT TESTED — AUTHENTICATION FIRST")


if __name__ == "__main__":
    unittest.main()
