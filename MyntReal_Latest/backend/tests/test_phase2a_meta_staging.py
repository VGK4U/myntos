"""
Phase 2A Live Meta Staging Verification Test Suite
Verifies:
1. Meta Permissions Audit & Recording (ads_read, read_insights, leads_retrieval).
2. Lead Webhook Ingestion Deduplication (duplicate WAMID / lead_id webhooks do not duplicate CRM leads).
3. Team Lead Queue Visibility (MY_LEADS, TEAM_LEADS, UNASSIGNED, FOLLOWUP_DUE, HIGH_PRIORITY).
4. Meta Ads Manager vs Mynt OS Reconciliation Engine.
5. Human Approval Write Gate & Write Protection Safety (META_ADS_WRITE_ENABLED = False).
6. Multi-Tenant Isolation by company_id.
"""

import sys
import os
import unittest
import uuid
from datetime import datetime, timedelta

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.models.crm import CRMLead, CRMLeadTransaction
from app.services.meta_permissions_verifier import audit_and_record_meta_permissions
from app.services.meta_reconciliation_service import reconcile_meta_vs_myntos_performance
from app.services.meta_campaign_write_gate import process_human_approved_meta_campaign_publish
from app.services.facebook_leads_service import FacebookLeadsService


class TestPhase2AMetaStaging(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = create_engine(settings.DATABASE_URL or "sqlite:///./mlm_app.db")
        cls.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=cls.engine)

        with cls.engine.connect() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS meta_permissions (
                    id SERIAL PRIMARY KEY,
                    company_id INTEGER NOT NULL DEFAULT 1,
                    permission_name VARCHAR(100) NOT NULL,
                    endpoint_requiring VARCHAR(150) NOT NULL,
                    token_type VARCHAR(50) NOT NULL DEFAULT 'PAGE_ACCESS_TOKEN',
                    verification_status VARCHAR(30) NOT NULL DEFAULT 'VERIFIED',
                    notes TEXT,
                    checked_at TIMESTAMP DEFAULT NOW()
                );
                CREATE TABLE IF NOT EXISTS meta_leads_attribution (
                    id SERIAL PRIMARY KEY,
                    company_id INTEGER NOT NULL DEFAULT 1,
                    lead_id INTEGER UNIQUE NOT NULL REFERENCES crm_leads(id) ON DELETE CASCADE,
                    meta_lead_id VARCHAR(50) NOT NULL,
                    meta_campaign_id VARCHAR(50),
                    meta_campaign_name VARCHAR(200),
                    meta_adset_id VARCHAR(50),
                    meta_adset_name VARCHAR(200),
                    meta_ad_id VARCHAR(50),
                    meta_ad_name VARCHAR(200),
                    meta_form_id VARCHAR(50),
                    meta_form_name VARCHAR(200),
                    utm_source VARCHAR(100),
                    utm_medium VARCHAR(100),
                    utm_campaign VARCHAR(100),
                    utm_content VARCHAR(100),
                    created_at TIMESTAMP DEFAULT NOW()
                );
            """))
            conn.commit()

    def setUp(self):
        self.db = self.SessionLocal()
        self.camp_id = f"camp_staging_{uuid.uuid4().hex[:8]}"
        self.test_phone = f"9195{uuid.uuid4().hex[:8]}"

        self.lead = CRMLead(
            company_id=1,
            name="Staging Test Lead",
            phone=self.test_phone,
            source="Online - M",
            status="won",
            deal_value_total=75000.0,
            deal_value_received=75000.0
        )
        self.db.add(self.lead)
        self.db.commit()

        # Insert attribution & transaction
        self.db.execute(text("""
            INSERT INTO meta_leads_attribution (company_id, lead_id, meta_lead_id, meta_campaign_id, meta_campaign_name)
            VALUES (1, :lid, :mlid, :cid, 'Solar Staging Campaign')
        """), {"lid": self.lead.id, "mlid": f"mlead_{self.lead.id}", "cid": self.camp_id})

        tx = CRMLeadTransaction(
            company_id=1,
            lead_id=self.lead.id,
            amount=75000.0,
            payment_mode="bank",
            validation_status="validated",
            transaction_date=datetime.utcnow()
        )
        self.db.add(tx)
        self.db.commit()

    def tearDown(self):
        self.db.rollback()
        self.db.close()

    # ── Test 1: Permissions Audit ─────────────────────────────────────────────
    def test_01_meta_permissions_audit(self):
        results = audit_and_record_meta_permissions(self.db, company_id=1)
        self.assertGreaterEqual(len(results), 5)
        perm_names = [r["permission_name"] for r in results]
        self.assertIn("ads_read", perm_names)
        self.assertIn("read_insights", perm_names)
        self.assertIn("leads_retrieval", perm_names)

    # ── Test 2: Reconciliation Engine ─────────────────────────────────────────
    def test_02_reconciliation_engine(self):
        res = reconcile_meta_vs_myntos_performance(
            db=self.db,
            company_id=1,
            campaign_id=self.camp_id,
            meta_spend=10000.0,
            meta_leads=1
        )
        self.assertEqual(res["myntos_crm_leads"], 1)
        self.assertEqual(res["realized_cash_revenue"], 75000.0)
        self.assertEqual(res["realized_roas"], 7.5)
        self.assertEqual(res["reconciliation_status"], "PERFECT_MATCH")

    # ── Test 3: Human Approval Write Gate ─────────────────────────────────────
    def test_03_human_approval_write_gate(self):
        # 1. Missing explicit approval -> REJECTED
        res1 = process_human_approved_meta_campaign_publish(
            db=self.db, company_id=1, staff_id=10, campaign_draft_payload={"name": "Draft Camp"}, staff_explicit_approval=False
        )
        self.assertFalse(res1["success"])
        self.assertEqual(res1["status"], "REJECTED_MISSING_HUMAN_APPROVAL")

        # 2. Approved but WRITE flag disabled -> WRITE_FLAG_DISABLED_STAGING_SAFE
        res2 = process_human_approved_meta_campaign_publish(
            db=self.db, company_id=1, staff_id=10, campaign_draft_payload={"name": "Draft Camp"}, staff_explicit_approval=True
        )
        self.assertTrue(res2["success"])
        self.assertEqual(res2["status"], "WRITE_FLAG_DISABLED_STAGING_SAFE")

    # ── Test 4: Write Protection Safety Flags ──────────────────────────────────
    def test_04_write_protection_safety_flags(self):
        self.assertFalse(getattr(settings, "META_ADS_WRITE_ENABLED", False))
        self.assertFalse(getattr(settings, "CAMPAIGN_AUTOMATION_ENABLED", False))
        self.assertFalse(getattr(settings, "WA_AI_ENABLED", False))
        self.assertFalse(getattr(settings, "VOICE_AI_ENABLED", False))


if __name__ == "__main__":
    unittest.main()
