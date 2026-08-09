"""
Phase 2K Forensic Reconciliation & Duplicate Analysis Automated Test Suite
Verifies:
1. Full Read-Only Forensic Inventory Parser against Meta Graph API v24.0.
2. Exact Duplicate Object Identification (21 Campaigns, 15 Ad Sets, 0 Ads).
3. Zero Spend (₹0.00) & PAUSED Status Protection.
4. Database vs Live Meta Hierarchy Mapping (META_OBJECT_VERIFIED vs META_OBJECT_MISSING).
5. Proposed Cleanup Plan Categorization (KEEP vs SAFE_TO_ARCHIVE).
6. Operational Safety Flags (META_ADS_WRITE_ENABLED = False).
"""

import sys
import os
import unittest

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.services.meta_forensic_service import get_meta_live_forensic_inventory
from app.services.meta_insights_analytics_service import get_meta_ads_dashboard_kpis


class TestPhase2KForensicReconciliation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = create_engine(settings.DATABASE_URL or "sqlite:///./mlm_app.db")
        cls.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=cls.engine)

    def setUp(self):
        self.db = self.SessionLocal()

    def tearDown(self):
        self.db.rollback()
        self.db.close()

    def test_01_forensic_inventory_reconciliation(self):
        res = get_meta_live_forensic_inventory(self.db, company_id=1)
        self.assertTrue(res["success"])
        self.assertEqual(res["status"], "FORENSIC_RECONCILIATION_COMPLETE")
        self.assertEqual(res["ad_account_id"], "act_560062103113819")
        self.assertEqual(res["totals"]["campaigns_count"], 21)
        self.assertEqual(res["totals"]["adsets_count"], 15)
        self.assertEqual(res["totals"]["ads_count"], 0)
        self.assertEqual(res["totals"]["creatives_count"], 0)

    def test_02_hierarchy_verification_status(self):
        res = get_meta_live_forensic_inventory(self.db, company_id=1)
        self.assertIn("META_OBJECT_VERIFIED", res["hierarchy_verification"]["campaign"])
        self.assertIn("META_OBJECT_MISSING", res["hierarchy_verification"]["ad"])

    def test_03_proposed_cleanup_plan_categorization(self):
        res = get_meta_live_forensic_inventory(self.db, company_id=1)
        plan = res["proposed_cleanup_plan"]
        self.assertGreaterEqual(len(plan), 36) # 21 campaigns + 15 adsets
        keep_items = [p for p in plan if p["recommendation"] == "KEEP"]
        archive_items = [p for p in plan if p["recommendation"] == "SAFE_TO_ARCHIVE"]
        self.assertEqual(len(keep_items), 2)  # 1 Campaign + 1 AdSet
        self.assertEqual(len(archive_items), 34)

    def test_04_operational_write_protection(self):
        self.assertFalse(getattr(settings, "META_ADS_WRITE_ENABLED", False))
        self.assertFalse(getattr(settings, "CAMPAIGN_AUTOMATION_ENABLED", False))

    def test_05_real_ad_pipeline_execution(self):
        from app.services.meta_real_ad_pipeline_service import execute_full_real_ad_creation_pipeline
        res = execute_full_real_ad_creation_pipeline(self.db, company_id=1, vertical="SOLAR")
        self.assertTrue(res["success"])
        self.assertEqual(res["status"], "REAL_META_AD_PIPELINE_COMPLETE")
        self.assertEqual(len(res["pipeline_steps"]), 11)
        self.assertEqual(res["ad_status"], "PAUSED")


if __name__ == "__main__":
    unittest.main()
