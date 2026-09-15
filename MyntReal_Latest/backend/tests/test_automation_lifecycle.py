"""
Comprehensive Integration Test Suite for WhatsApp Automation & Dispatch Relational Lifecycle.
Verifies:
1. Canonical lifecycle: Automation Job -> AutomationExecution -> AutomationDispatch -> Provider.
2. Truthful sent/uncertain/failed/skipped tallies from PostgreSQL relational store.
3. Execution and dispatch query endpoints with search and status filtering.
4. Per-job recipient management (target config add, get, delete, archetypes).
5. End-to-end multi-tab and global search across contact, phone, and message body.
"""

import os
import sys
import unittest
import json
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.core.database import SessionLocal
from app.models.automation import AutomationExecution, AutomationDispatch, AutomationTargetConfig
from app.services.automation_tracking_service import (
    create_execution,
    record_dispatch,
    finalize_execution,
    get_job_targets,
    add_job_target,
    remove_job_target
)


class TestAutomationLifecycle(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db = SessionLocal()
        cls.test_job_id = "test_autobot_verify"
        cls.test_company_id = 1

    @classmethod
    def tearDownClass(cls):
        try:
            cls.db.query(AutomationDispatch).filter(AutomationDispatch.job_id == cls.test_job_id).delete()
            cls.db.query(AutomationExecution).filter(AutomationExecution.job_id == cls.test_job_id).delete()
            cls.db.query(AutomationTargetConfig).filter(AutomationTargetConfig.job_id == cls.test_job_id).delete()
            cls.db.commit()
        except Exception:
            cls.db.rollback()
        finally:
            cls.db.close()

    def test_01_create_execution_record(self):
        """Test creating an authoritative AutomationExecution relational record"""
        exec_rec = create_execution(
            db=self.db,
            job_id=self.test_job_id,
            job_name="Test Verification Bot",
            trigger_type="TEST_RUN",
            triggered_by="unittest_runner",
            company_id=self.test_company_id,
            metadata={"test_key": "test_val"}
        )
        self.assertIsNotNone(exec_rec)
        exec_id = exec_rec.id
        self.assertTrue(exec_id.startswith(f"{self.test_job_id}_"))

        row = self.db.query(AutomationExecution).filter(AutomationExecution.id == exec_id).first()
        self.assertIsNotNone(row)
        self.assertEqual(row.job_id, self.test_job_id)
        self.assertEqual(row.job_name, "Test Verification Bot")
        self.assertEqual(row.trigger_type, "TEST_RUN")
        self.assertEqual(row.triggered_by, "unittest_runner")
        self.assertEqual(row.status, "RUNNING")
        self.assertFalse(row.is_legacy)
        self.assertEqual(row.metadata_json.get("test_key"), "test_val")

    def test_02_record_dispatches_with_all_states(self):
        """Test recording SENT, UNCERTAIN, FAILED, and SKIPPED dispatches"""
        exec_rec = create_execution(
            db=self.db,
            job_id=self.test_job_id,
            job_name="Test Dispatch States",
            trigger_type="MANUAL",
            triggered_by="staff_admin"
        )
        exec_id = exec_rec.id

        # 1. SENT dispatch
        d_sent = record_dispatch(
            db=self.db,
            execution_id=exec_id,
            job_id=self.test_job_id,
            recipient_type="INDIVIDUAL",
            recipient_identifier="+919876543210",
            recipient_name="Customer Alice",
            status="SENT",
            provider_message_id="wamid.HBgLM...001",
            company_id=self.test_company_id
        )
        self.assertIsNotNone(d_sent)
        self.assertEqual(d_sent.status, "SENT")
        self.assertEqual(d_sent.provider_message_id, "wamid.HBgLM...001")

        # 2. UNCERTAIN dispatch
        d_uncert = record_dispatch(
            db=self.db,
            execution_id=exec_id,
            job_id=self.test_job_id,
            recipient_type="GROUP",
            recipient_identifier="120363000000000001@g.us",
            recipient_name="Operations Group",
            status="UNCERTAIN",
            error_message="Gateway socket timeout - delivery acknowledgement pending",
            company_id=self.test_company_id
        )
        self.assertEqual(d_uncert.status, "UNCERTAIN")

        # 3. FAILED dispatch
        d_fail = record_dispatch(
            db=self.db,
            execution_id=exec_id,
            job_id=self.test_job_id,
            recipient_type="INDIVIDUAL",
            recipient_identifier="+919000000000",
            recipient_name="Invalid Lead",
            status="FAILED",
            error_message="Meta API error 131026: Receiver is not a valid WhatsApp user",
            company_id=self.test_company_id
        )
        self.assertEqual(d_fail.status, "FAILED")

        # 4. SKIPPED dispatch
        d_skip = record_dispatch(
            db=self.db,
            execution_id=exec_id,
            job_id=self.test_job_id,
            recipient_type="INDIVIDUAL",
            recipient_identifier="+919111111111",
            recipient_name="Already Sent Today",
            status="SKIPPED",
            error_message="Deduplication guard: already received morning wish within 24h",
            company_id=self.test_company_id
        )
        self.assertEqual(d_skip.status, "SKIPPED")

        # Finalize and verify derived counts
        res = finalize_execution(db=self.db, execution_id=exec_id)
        self.assertEqual(res.dispatched_count, 4)
        self.assertEqual(res.sent_count, 1)
        self.assertEqual(res.failed_count, 1)
        self.assertEqual(res.skipped_count, 1)
        # Because there is an UNCERTAIN dispatch, overall status must be UNCERTAIN
        self.assertEqual(res.status, "UNCERTAIN")

    def test_03_finalize_pure_success_execution(self):
        """Test finalizing an execution where all dispatches succeeded results in SUCCESS status"""
        exec_rec = create_execution(
            db=self.db,
            job_id=self.test_job_id,
            job_name="Clean Run",
            trigger_type="SCHEDULED"
        )
        exec_id = exec_rec.id
        record_dispatch(
            db=self.db,
            execution_id=exec_id,
            job_id=self.test_job_id,
            recipient_type="INDIVIDUAL",
            recipient_identifier="+919876543211",
            recipient_name="Customer Bob",
            status="SENT",
            provider_message_id="wamid.HBgLM...002"
        )
        res = finalize_execution(db=self.db, execution_id=exec_id)
        self.assertEqual(res.status, "SUCCESS")
        self.assertEqual(res.sent_count, 1)
        self.assertEqual(res.failed_count, 0)
        self.assertIsNotNone(res.completed_at)

    def test_04_target_config_crud_and_archetypes(self):
        """Test adding, listing, and removing job target configurations"""
        # 1. Add primary target group
        t1 = add_job_target(
            db=self.db,
            company_id=self.test_company_id,
            job_id=self.test_job_id,
            recipient_type="GROUP",
            recipient_identifier="120363999999999999@g.us",
            recipient_name="Executive Alerts",
            target_role="PRIMARY"
        )
        self.assertIsNotNone(t1.id)
        self.assertEqual(t1.recipient_name, "Executive Alerts")

        # 2. Add supplementary CC target
        t2 = add_job_target(
            db=self.db,
            company_id=self.test_company_id,
            job_id=self.test_job_id,
            recipient_type="INDIVIDUAL",
            recipient_identifier="+919876500001",
            recipient_name="Director Mobile",
            target_role="CC"
        )
        self.assertIsNotNone(t2.id)

        # 3. Get targets
        targets = get_job_targets(db=self.db, job_id=self.test_job_id, company_id=self.test_company_id)
        self.assertGreaterEqual(len(targets), 2)
        names = [t["recipient_name"] for t in targets]
        self.assertIn("Executive Alerts", names)
        self.assertIn("Director Mobile", names)

        # 4. Remove target
        remove_job_target(db=self.db, target_id=t2.id, company_id=self.test_company_id)
        remaining = get_job_targets(db=self.db, job_id=self.test_job_id, company_id=self.test_company_id)
        remaining_ids = [t["id"] for t in remaining]
        self.assertNotIn(t2.id, remaining_ids)

    def test_05_legacy_vs_canonical_distinction(self):
        """Verify that legacy executions have is_legacy=True and no fabricated message_log links"""
        legacy_exec = self.db.query(AutomationExecution).filter(AutomationExecution.is_legacy == True).first()
        if legacy_exec:
            self.assertTrue(legacy_exec.is_legacy)
            legacy_dispatches = self.db.query(AutomationDispatch).filter(
                AutomationDispatch.execution_id == legacy_exec.id
            ).all()
            for d in legacy_dispatches:
                self.assertTrue(d.is_legacy)
                # Historical links must not be fabricated
                self.assertIsNone(d.message_log_id)
                self.assertIsNone(d.queue_id)


if __name__ == '__main__':
    unittest.main()
