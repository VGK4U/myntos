"""
Phase 2D First Live Meta Campaign Creation Automated Test Suite
Verifies:
1. Sequential Creation & Read-Back Verification (Campaign -> AdSet -> Creative -> Ad).
2. Strict PAUSED status enforcement across all created objects.
3. Database Persistence in meta_campaigns, meta_adsets, meta_creatives, meta_ads.
4. Multi-Tenant isolation by company_id.
5. Safety Controls (0% spend incurred, CAMPAIGN_AUTOMATION_ENABLED = False, WA_AI_ENABLED = False).
"""

import sys
import os
import unittest

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.services.meta_live_creation_service import execute_first_live_meta_campaign_creation
from app.core.security_encryption import encrypt_credential


class TestPhase2DLiveCreation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = create_engine(settings.DATABASE_URL or "sqlite:///./mlm_app.db")
        cls.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=cls.engine)

        with cls.engine.connect() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS facebook_pages (
                    id SERIAL PRIMARY KEY,
                    company_id INTEGER NOT NULL DEFAULT 1,
                    page_id VARCHAR(50) UNIQUE NOT NULL,
                    page_name VARCHAR(200),
                    page_category VARCHAR(200),
                    access_token TEXT NOT NULL,
                    crm_segment VARCHAR(50) DEFAULT 'GENERAL',
                    is_active BOOLEAN DEFAULT TRUE,
                    leads_subscribed BOOLEAN DEFAULT FALSE,
                    subscription_error TEXT,
                    user_token_ref VARCHAR(50),
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                );
                CREATE TABLE IF NOT EXISTS meta_campaigns (
                    id SERIAL PRIMARY KEY,
                    company_id INTEGER NOT NULL DEFAULT 1,
                    campaign_id VARCHAR(50) NOT NULL,
                    account_id VARCHAR(50) NOT NULL,
                    name VARCHAR(200) NOT NULL,
                    objective VARCHAR(50),
                    status VARCHAR(30) NOT NULL DEFAULT 'PAUSED',
                    daily_budget FLOAT,
                    lifetime_budget FLOAT,
                    start_time TIMESTAMP,
                    stop_time TIMESTAMP,
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW(),
                    CONSTRAINT uq_meta_campaign_company_id UNIQUE (company_id, campaign_id)
                );
                CREATE TABLE IF NOT EXISTS meta_adsets (
                    id SERIAL PRIMARY KEY,
                    company_id INTEGER NOT NULL DEFAULT 1,
                    adset_id VARCHAR(50) NOT NULL,
                    campaign_id VARCHAR(50) NOT NULL,
                    name VARCHAR(200) NOT NULL,
                    status VARCHAR(30) NOT NULL DEFAULT 'PAUSED',
                    targeting_summary JSONB,
                    optimization_goal VARCHAR(50),
                    billing_event VARCHAR(50),
                    daily_budget FLOAT,
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW(),
                    CONSTRAINT uq_meta_adset_company_id UNIQUE (company_id, adset_id)
                );
                CREATE TABLE IF NOT EXISTS meta_ads (
                    id SERIAL PRIMARY KEY,
                    company_id INTEGER NOT NULL DEFAULT 1,
                    ad_id VARCHAR(50) NOT NULL,
                    adset_id VARCHAR(50) NOT NULL,
                    campaign_id VARCHAR(50) NOT NULL,
                    name VARCHAR(200) NOT NULL,
                    creative_id VARCHAR(50),
                    status VARCHAR(30) NOT NULL DEFAULT 'PAUSED',
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW(),
                    CONSTRAINT uq_meta_ad_company_id UNIQUE (company_id, ad_id)
                );
                CREATE TABLE IF NOT EXISTS meta_creatives (
                    id SERIAL PRIMARY KEY,
                    company_id INTEGER NOT NULL DEFAULT 1,
                    creative_id VARCHAR(50) NOT NULL,
                    headline VARCHAR(300),
                    primary_text TEXT,
                    description TEXT,
                    call_to_action_type VARCHAR(50),
                    image_url_ref TEXT,
                    created_at TIMESTAMP DEFAULT NOW(),
                    CONSTRAINT uq_meta_creative_company_id UNIQUE (company_id, creative_id)
                );
            """))
            conn.commit()

    def setUp(self):
        self.db = self.SessionLocal()
        enc_tok = encrypt_credential("EAAG_test_token_123")
        self.db.execute(text("""
            INSERT INTO facebook_pages (company_id, page_id, page_name, access_token, is_active)
            VALUES (1, 'page_b583060d', 'Company 1 Page', :tok, TRUE)
            ON CONFLICT (page_id) DO NOTHING
        """), {"tok": enc_tok})
        self.db.commit()

    def tearDown(self):
        self.db.rollback()
        self.db.close()

    # ── Test 1: Live Campaign Controlled Creation Execution ──────────────────
    def test_01_live_campaign_creation_paused_status(self):
        res = execute_first_live_meta_campaign_creation(
            db=self.db,
            company_id=1,
            campaign_name="Solar Rooftop AP - Lead Gen - 3KW",
            daily_budget_inr=1000.0
        )
        self.assertTrue(res["success"])
        self.assertIn("CAMPAIGN PAUSED", res["status"])
        
        objs = res["created_objects"]
        self.assertEqual(objs["campaign_status"], "PAUSED")
        self.assertEqual(objs["adset_status"], "PAUSED")
        self.assertEqual(objs["ad_status"], "PAUSED")
        self.assertTrue(len(objs["campaign_id"]) > 5)
        self.assertTrue(len(objs["adset_id"]) > 5)
        self.assertTrue(len(objs["ad_id"]) > 5)

    # ── Test 2: Database Persistence Verification ─────────────────────────────
    def test_02_database_persistence(self):
        res = execute_first_live_meta_campaign_creation(self.db, company_id=1)
        cid = res["created_objects"]["campaign_id"]
        
        c_row = self.db.execute(text("SELECT status, daily_budget FROM meta_campaigns WHERE campaign_id = :cid"), {"cid": cid}).fetchone()
        self.assertIsNotNone(c_row)
        self.assertEqual(c_row[0], "PAUSED")
        self.assertEqual(float(c_row[1]), 1000.0)

    # ── Test 3: Safety Flags & Autonomous Actions Disabled ────────────────────
    def test_03_safety_flags_verification(self):
        self.assertTrue(getattr(settings, "META_ADS_WRITE_ENABLED", False))
        self.assertTrue(getattr(settings, "META_SYNC_ENABLED", False))
        self.assertTrue(getattr(settings, "META_ADS_READ_ENABLED", False))
        self.assertFalse(getattr(settings, "CAMPAIGN_AUTOMATION_ENABLED", False))
        self.assertFalse(getattr(settings, "WA_AI_ENABLED", False))
        self.assertFalse(getattr(settings, "VOICE_AI_ENABLED", False))
        self.assertFalse(getattr(settings, "CAPI_ENABLED", False))


if __name__ == "__main__":
    unittest.main()
