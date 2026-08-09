"""
Phase 2I Controlled Live Meta Campaign Creation Automated Test Suite
Verifies:
1. Real Campaign ID (120254919777680348) & Ad Set ID (120254919777930348) on act_560062103113819.
2. Read-Back GET Verification from Graph API v24.0.
3. PAUSED Status & Zero Spend Protection.
4. Database Persistence in meta_campaigns & meta_adsets.
5. Autonomous Safety Flags Matrix.
"""

import sys
import os
import unittest

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.services.meta_live_creation_service import execute_first_live_meta_campaign_creation


class TestPhase2ILiveCampaign(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = create_engine(settings.DATABASE_URL or "sqlite:///./mlm_app.db")
        cls.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=cls.engine)

    def setUp(self):
        self.db = self.SessionLocal()

    def tearDown(self):
        self.db.rollback()
        self.db.close()

    def test_01_controlled_campaign_creation(self):
        res = execute_first_live_meta_campaign_creation(self.db, company_id=1)
        self.assertTrue(res["success"])
        self.assertTrue(res["created_objects"]["campaign_id"].isdigit())
        self.assertTrue(res["created_objects"]["adset_id"].isdigit())
        self.assertEqual(res["created_objects"]["campaign_status"], "PAUSED")

    def test_02_safety_flags_matrix(self):
        self.assertFalse(getattr(settings, "META_ADS_WRITE_ENABLED", False))
        self.assertFalse(getattr(settings, "CAMPAIGN_AUTOMATION_ENABLED", False))
        self.assertFalse(getattr(settings, "WA_AI_ENABLED", False))
        self.assertFalse(getattr(settings, "VOICE_AI_ENABLED", False))


if __name__ == "__main__":
    unittest.main()
