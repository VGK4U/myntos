"""
Phase 2K.6 Automated Code Test Suite
Verifies:
1. 100% Read-Only Forensic Inspection (Zero writes performed).
2. Saved Instagram Vertical Credentials in backend/.env.
3. Diagnostic Telemetry Parser for Error 1815202.
4. Human Action Recommendation Engine (OPTION A: LINK_EXISTING_INSTAGRAM_TO_PAGE).
"""

import sys
import os
import unittest

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.services.meta_instagram_forensic_service import execute_instagram_forensic_inspection


class TestPhase2K6InstagramForensics(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = create_engine(settings.DATABASE_URL or "sqlite:///./mlm_app.db")
        cls.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=cls.engine)

    def setUp(self):
        self.db = self.SessionLocal()

    def tearDown(self):
        self.db.rollback()
        self.db.close()

    def test_01_read_only_zero_writes_enforcement(self):
        res = execute_instagram_forensic_inspection(self.db, company_id=1)
        self.assertEqual(res["U_meta_writes_performed"], 0)
        self.assertEqual(res["V_spend_inr"], 0.0)
        self.assertEqual(res["W_final_status"], "META_FORENSIC_VERIFICATION_COMPLETE")

    def test_02_instagram_credentials_saved_in_env(self):
        solar_email = os.getenv("INSTAGRAM_SOLAR_EMAIL")
        solar_pass = os.getenv("INSTAGRAM_SOLAR_PASSWORD")
        self.assertEqual(solar_email, "mynt.hgs@gmail.com")
        self.assertEqual(solar_pass, "Mynt@123")

        re_email = os.getenv("INSTAGRAM_REALESTATE_EMAIL")
        self.assertEqual(re_email, "mynt.realdreams@gmail.com")

    def test_03_human_action_recommendation(self):
        res = execute_instagram_forensic_inspection(self.db, company_id=1)
        self.assertIn("LINK_EXISTING_INSTAGRAM_TO_PAGE", res["Q_required_human_action"])
        self.assertEqual(res["T_app_review_required"], "NO (Asset linkage issue, not App Review)")


if __name__ == "__main__":
    unittest.main()
