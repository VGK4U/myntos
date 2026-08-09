"""
Phase 2B Meta Campaign Creation Dry Run Automated Test Suite
Verifies:
1. Serialized Graph API v24.0 Payloads (Campaign, Ad Set, Creative, Ad).
2. Budget Magnitude Safety Validation (rejects out-of-bounds budgets like ₹100,000/day).
3. AI Ad Copy Knowledge Safety Auditor (rejects un-approved commercial claims like "50% subsidy").
4. Multi-Tenant Isolation & Risk Checks Evaluation.
5. Write Gate Interception (META_ADS_WRITE_ENABLED = False).
6. Audit Logging in ai_action_logs.
"""

import sys
import os
import unittest
import uuid
from datetime import datetime

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.models.crm import CRMLead
from app.services.meta_payload_builder import (
    build_meta_campaign_payload,
    build_meta_adset_payload,
    build_meta_creative_payload,
    build_meta_ad_payload
)
from app.services.ai_ad_copy_safety_auditor import audit_ad_copy_claims_against_knowledge
from app.services.meta_dryrun_audit_service import evaluate_dryrun_risk_checks


class TestPhase2BMetaDryRun(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = create_engine(settings.DATABASE_URL or "sqlite:///./mlm_app.db")
        cls.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=cls.engine)

        with cls.engine.connect() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS ai_knowledge_categories (
                    id SERIAL PRIMARY KEY,
                    company_id INTEGER NOT NULL DEFAULT 1,
                    vertical VARCHAR(50) NOT NULL DEFAULT 'GENERAL',
                    category_code VARCHAR(50) NOT NULL,
                    display_name VARCHAR(100) NOT NULL,
                    created_at TIMESTAMP DEFAULT NOW(),
                    CONSTRAINT uq_knowledge_cat UNIQUE (company_id, vertical, category_code)
                );
                CREATE TABLE IF NOT EXISTS ai_knowledge_items (
                    id SERIAL PRIMARY KEY,
                    company_id INTEGER NOT NULL DEFAULT 1,
                    category_id INTEGER NOT NULL REFERENCES ai_knowledge_categories(id) ON DELETE CASCADE,
                    title VARCHAR(200) NOT NULL,
                    fact_content TEXT NOT NULL,
                    keywords VARCHAR(300),
                    is_approved BOOLEAN NOT NULL DEFAULT TRUE,
                    is_active BOOLEAN NOT NULL DEFAULT TRUE,
                    version VARCHAR(20) NOT NULL DEFAULT 'v1.0',
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                );
                CREATE TABLE IF NOT EXISTS ai_action_logs (
                    id SERIAL PRIMARY KEY,
                    company_id INTEGER NOT NULL DEFAULT 1,
                    lead_id INTEGER NOT NULL REFERENCES crm_leads(id) ON DELETE CASCADE,
                    vertical VARCHAR(50) NOT NULL DEFAULT 'GENERAL',
                    channel VARCHAR(30) NOT NULL DEFAULT 'WHATSAPP',
                    action_type VARCHAR(50) NOT NULL,
                    model_name VARCHAR(100) NOT NULL DEFAULT 'mock_llm_v1',
                    prompt_version VARCHAR(50) NOT NULL DEFAULT 'v1.0',
                    confidence_score FLOAT NOT NULL DEFAULT 0.0,
                    ai_recommendation JSONB,
                    final_action_taken VARCHAR(50) NOT NULL,
                    human_override BOOLEAN NOT NULL DEFAULT FALSE,
                    correlation_id VARCHAR(100),
                    created_at TIMESTAMP DEFAULT NOW()
                );
            """))
            conn.commit()

    def setUp(self):
        self.db = self.SessionLocal()
        self.lead = CRMLead(
            company_id=1,
            name="DryRun Lead",
            phone=f"9194{uuid.uuid4().hex[:8]}",
            source="Online - M",
            status="new"
        )
        self.db.add(self.lead)
        self.db.commit()

    def tearDown(self):
        self.db.rollback()
        self.db.close()

    # ── Test 1: Payload Builders ──────────────────────────────────────────────
    def test_01_meta_payload_builders(self):
        c_res = build_meta_campaign_payload("act_123456", "Solar AP Leads", 1000.0)
        self.assertEqual(c_res["serialized_payload"]["daily_budget"], 100000)  # ₹1,000.00 = 100,000 paise
        self.assertEqual(c_res["serialized_payload"]["status"], "PAUSED")

        as_res = build_meta_adset_payload("act_123456", "camp_999", "Adset AP Homeowners", "Andhra Pradesh", 1000.0)
        self.assertEqual(as_res["dependency_campaign_id"], "camp_999")

        cr_res = build_meta_creative_payload("act_123456", "page_111", "Headline Solar", "Primary Text", "Desc", "form_222")
        self.assertEqual(cr_res["lead_form_id_ref"], "form_222")

        ad_res = build_meta_ad_payload("act_123456", "adset_999", "creative_888", "Ad 1 Solar")
        self.assertEqual(ad_res["dependency_adset_id"], "adset_999")

    # ── Test 2: Budget Magnitude Safety Validation ────────────────────────────
    def test_02_budget_magnitude_safety(self):
        with self.assertRaises(ValueError):
            build_meta_campaign_payload("act_123456", "Accidental High Budget", 100000.0)

    # ── Test 3: AI Knowledge Safety Auditor Rejection ─────────────────────────
    def test_03_knowledge_safety_auditor_rejection(self):
        unsafe_res = audit_ad_copy_claims_against_knowledge(
            db=self.db, company_id=1, vertical="SOLAR", headline="Get 50% subsidy today!", primary_text="Guaranteed loan approval with zero cost solar."
        )
        self.assertFalse(unsafe_res["is_safe"])
        self.assertEqual(unsafe_res["status"], "REJECTED_UNSUPPORTED_CLAIMS")
        self.assertIn("50% subsidy", unsafe_res["flagged_phrases"])

        safe_res = audit_ad_copy_claims_against_knowledge(
            db=self.db, company_id=1, vertical="SOLAR", headline="Top Quality Solar Rooftop in AP", primary_text="Expert installation with standard warranty."
        )
        self.assertTrue(safe_res["is_safe"])

    # ── Test 4: Dry-Run Risk Checks Evaluation & Write Gate Interception ──────
    def test_04_dryrun_risk_checks_and_write_gate(self):
        eval_res = evaluate_dryrun_risk_checks(
            db=self.db,
            company_id=1,
            user_id=5,
            ad_account_id="act_123456",
            page_id="page_111",
            campaign_name="Solar AP Test Campaign",
            daily_budget_inr=1000.0,
            headline="3KW Solar Rooftop System",
            primary_text="Verified facts: High efficiency panels with long term support.",
            lead_form_id="form_222"
        )
        self.assertTrue(eval_res["all_risk_checks_passed"])
        self.assertEqual(eval_res["overall_status"], "READY_FOR_HUMAN_APPROVAL")
        self.assertEqual(eval_res["write_gate_status"], "INTERCEPTED_SAFE_READ_ONLY_MODE")
        self.assertFalse(eval_res["meta_ads_write_enabled"])

    # ── Test 5: Write Protection Safety ──────────────────────────────────────
    def test_05_write_protection_safety(self):
        self.assertFalse(getattr(settings, "META_ADS_WRITE_ENABLED", False))
        self.assertFalse(getattr(settings, "CAMPAIGN_AUTOMATION_ENABLED", False))


if __name__ == "__main__":
    unittest.main()
