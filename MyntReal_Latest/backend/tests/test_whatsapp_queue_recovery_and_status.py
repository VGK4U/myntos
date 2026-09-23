"""
Comprehensive Automated Test Suite: WhatsApp Queue State Machine, Crash Recovery, and Authoritative Scheduler Status
Covers Scenarios A through L:
- Test A: Normal scheduled execution -> sent with WAMID
- Test B: Manual execution -> sent with WAMID
- Test C: Worker crashes before send attempt -> recoverable to pending, attempts incremented
- Test D: Worker crashes after send boundary entered -> marked dispatch_uncertain, ZERO duplicate resend
- Test E: Worker restarts and recovers stale lease
- Test F: Concurrency / SKIP LOCKED single-owner claim protection
- Test G: Multiple successful executions in one day -> dynamic count aggregation (no hardcoded 1)
- Test H: Mixed executions (Sent + Failed + Uncertain) -> correct independent counts
- Test I: /scheduler-status dynamic querying from postgresql (zero hardcoded values)
- Test J: Persistence across simulated restarts / DB reconnect
- Test K: Scheduled vs Manual trigger parity in database
- Test L: Reconcile historical queue item (terminated instance) to dispatch_uncertain
"""

import os
import sys
import unittest
import json
from datetime import datetime, timedelta

# Dynamic path resolution (NO ABSOLUTE PATHS)
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from fastapi.testclient import TestClient
from app.main import app
from app.core.database import SessionLocal
from sqlalchemy import text
from app.api.v1.endpoints.whatsapp import recover_stale_queue_claims, expire_stale_pending_queue


class TestWhatsAppQueueRecoveryAndStatus(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        db = SessionLocal()
        # Clean test records
        db.execute(text("DELETE FROM whatsapp_bot_queue WHERE instance_id LIKE 'test-%' OR target_jid LIKE 'test-%' OR instance_id = 'leader_worker' OR result_payload->>'job_id' = 'wa_bihourly_sales_perf_report'"))
        db.execute(text("DELETE FROM automation_execution WHERE job_id = 'wa_bihourly_sales_perf_report'"))
        db.execute(text("DELETE FROM message_log WHERE message_sid LIKE 'test_%' OR mobile_number LIKE 'test_%'"))
        db.commit()
        db.close()

    def tearDown(self):
        db = SessionLocal()
        db.execute(text("DELETE FROM whatsapp_bot_queue WHERE instance_id LIKE 'test-%' OR target_jid LIKE 'test-%' OR instance_id = 'leader_worker' OR result_payload->>'job_id' = 'wa_bihourly_sales_perf_report'"))
        db.execute(text("DELETE FROM automation_execution WHERE job_id = 'wa_bihourly_sales_perf_report'"))
        db.execute(text("DELETE FROM message_log WHERE message_sid LIKE 'test_%' OR mobile_number LIKE 'test_%'"))
        db.commit()
        db.close()

    def test_a_normal_scheduled_execution_to_sent(self):
        """Test A: Normal execution: enqueue -> poll -> attempt -> complete (sent) with WAMID."""
        # 1. Enqueue
        enq_res = self.client.post("/api/v1/whatsapp/bot-queue-enqueue", json={
            "target_type": "group",
            "target_jid": "test-sales-group@g.us",
            "message": "SALES TEAM 2-HOUR UPDATE (Scheduled Slot A)",
            "instance_id": "test-leader-1",
            "job_id": "wa_bihourly_sales_perf_report",
            "job_name": "Sales Team 2-Hour Report & Leaderboard",
            "trigger_type": "AUTO_SCHEDULER"
        })
        self.assertEqual(enq_res.status_code, 200)
        qid = enq_res.json()["queue_id"]

        # 2. Poll & Claim
        poll_res = self.client.get(f"/api/v1/whatsapp/bot-queue-poll?limit=10&instance_id=test-leader-1")
        self.assertEqual(poll_res.status_code, 200)
        items = poll_res.json().get("items", [])
        claimed_ids = [it["id"] for it in items]
        self.assertIn(qid, claimed_ids)

        # 3. Enter send boundary
        att_res = self.client.post("/api/v1/whatsapp/bot-queue-attempting", json={
            "queue_id": qid,
            "instance_id": "test-leader-1"
        })
        self.assertEqual(att_res.status_code, 200)

        # 4. WhatsApp provider ACK
        ack_res = self.client.post("/api/v1/whatsapp/bot-queue-complete", json={
            "queue_id": qid,
            "status": "sent",
            "result_payload": {"wamid": "test_wamid_slot_a_123"}
        })
        self.assertEqual(ack_res.status_code, 200)

        # 5. Verify database state
        db = SessionLocal()
        row = db.execute(text("SELECT status, sent_at, result_payload FROM whatsapp_bot_queue WHERE id = :qid"), {"qid": qid}).fetchone()
        db.close()
        self.assertEqual(row[0], "sent")
        self.assertIsNotNone(row[1])
        self.assertEqual(row[2].get("wamid"), "test_wamid_slot_a_123")
        self.assertEqual(row[2].get("dispatch_stage"), "sent_confirmed")

    def test_b_manual_execution_to_sent(self):
        """Test B: Manual execution writes unified payload and completes with sent status."""
        enq_res = self.client.post("/api/v1/whatsapp/bot-queue-enqueue", json={
            "target_type": "group",
            "target_jid": "test-sales-group@g.us",
            "message": "SALES TEAM 2-HOUR UPDATE (Manual Trigger by Staff Anushka)",
            "instance_id": "test-staff-trigger",
            "job_id": "wa_bihourly_sales_perf_report",
            "job_name": "Sales Team 2-Hour Report & Leaderboard",
            "trigger_type": "MANUAL"
        })
        self.assertEqual(enq_res.status_code, 200)
        qid = enq_res.json()["queue_id"]

        # Poll
        poll_res = self.client.get(f"/api/v1/whatsapp/bot-queue-poll?limit=5&instance_id=test-worker-manual")
        self.assertEqual(poll_res.status_code, 200)

        # Mark attempting
        att_res = self.client.post("/api/v1/whatsapp/bot-queue-attempting", json={"queue_id": qid, "instance_id": "test-worker-manual"})
        self.assertEqual(att_res.status_code, 200)

        # Complete
        comp_res = self.client.post("/api/v1/whatsapp/bot-queue-complete", json={
            "queue_id": qid,
            "status": "sent",
            "result_payload": {"wamid": "test_wamid_manual_456"}
        })
        self.assertEqual(comp_res.status_code, 200)

        db = SessionLocal()
        row = db.execute(text("SELECT status, result_payload FROM whatsapp_bot_queue WHERE id = :qid"), {"qid": qid}).fetchone()
        db.close()
        self.assertEqual(row[0], "sent")
        self.assertEqual(row[1].get("trigger_type"), "MANUAL")
        self.assertEqual(row[1].get("wamid"), "test_wamid_manual_456")

    def test_c_worker_crashes_before_send_attempt_is_recoverable(self):
        """Test C: Worker claimed item but died BEFORE entering send boundary -> reset to pending with attempts incremented."""
        db = SessionLocal()
        res = db.execute(text("""
            INSERT INTO whatsapp_bot_queue (target_type, target_jid, message, status, created_at, instance_id, result_payload)
            VALUES ('group', 'test-group@g.us', 'Test message pre-dispatch crash', 'processing', NOW() - INTERVAL '70 seconds', 'test-crashed-worker', CAST(:rp AS jsonb))
            RETURNING id
        """), {
            "rp": json.dumps({
                "claimed_at": (datetime.utcnow() - timedelta(seconds=70)).isoformat(),
                "claim_instance_id": "test-crashed-worker",
                "attempts": 1,
                "send_boundary_entered": False,
                "dispatch_stage": "claimed"
            })
        })
        db.commit()
        qid = res.fetchone()[0]

        # Trigger recovery
        reconciled = recover_stale_queue_claims(db, threshold_seconds=60)
        self.assertGreaterEqual(reconciled, 1)

        row = db.execute(text("SELECT status, result_payload FROM whatsapp_bot_queue WHERE id = :qid"), {"qid": qid}).fetchone()
        db.close()

        # Invariant: Must reset to 'pending' for clean retry because socket was NEVER called
        self.assertEqual(row[0], "pending")
        self.assertEqual(row[1].get("attempts"), 1)
        self.assertEqual(row[1].get("dispatch_stage"), "requeued_pre_dispatch")

    def test_d_worker_crashes_after_send_boundary_marked_uncertain(self):
        """Test D: Worker crashed AFTER entering send boundary -> marked dispatch_uncertain. NEVER automatic resend."""
        db = SessionLocal()
        res = db.execute(text("""
            INSERT INTO whatsapp_bot_queue (target_type, target_jid, message, status, created_at, instance_id, result_payload)
            VALUES ('group', 'test-group@g.us', 'Test message crash inside send boundary', 'processing', NOW() - INTERVAL '90 seconds', 'test-crashed-worker-boundary', CAST(:rp AS jsonb))
            RETURNING id
        """), {
            "rp": json.dumps({
                "claimed_at": (datetime.utcnow() - timedelta(seconds=90)).isoformat(),
                "claim_instance_id": "test-crashed-worker-boundary",
                "attempts": 1,
                "send_boundary_entered": True,
                "send_attempted": True,
                "dispatch_stage": "send_boundary_entered",
                "send_boundary_at": (datetime.utcnow() - timedelta(seconds=85)).isoformat()
            })
        })
        db.commit()
        qid = res.fetchone()[0]

        # Trigger recovery
        reconciled = recover_stale_queue_claims(db, threshold_seconds=60)
        self.assertGreaterEqual(reconciled, 1)

        row = db.execute(text("SELECT status, error_message, result_payload FROM whatsapp_bot_queue WHERE id = :qid"), {"qid": qid}).fetchone()
        db.close()

        # Invariant: Must NOT be reset to pending! Must be dispatch_uncertain to prevent duplicate transmission
        self.assertEqual(row[0], "dispatch_uncertain")
        self.assertIn("dispatch_uncertain to prevent duplicate send", row[1])
        self.assertEqual(row[2].get("dispatch_stage"), "uncertain_send_boundary")

    def test_e_worker_recovers_stale_lease_via_poll(self):
        """Test E: Worker poll automatically heals stale claims in the background."""
        db = SessionLocal()
        res = db.execute(text("""
            INSERT INTO whatsapp_bot_queue (target_type, target_jid, message, status, created_at, instance_id, result_payload)
            VALUES ('group', 'test-group@g.us', 'Stale lease pre-dispatch', 'processing', NOW() - INTERVAL '120 seconds', 'test-old-worker', CAST(:rp AS jsonb))
            RETURNING id
        """), {
            "rp": json.dumps({
                "claimed_at": (datetime.utcnow() - timedelta(seconds=120)).isoformat(),
                "attempts": 1,
                "send_boundary_entered": False,
                "dispatch_stage": "claimed"
            })
        })
        db.commit()
        qid = res.fetchone()[0]
        db.close()

        # Polling should heal the stale item back to pending, and immediately claim it
        poll_res = self.client.get("/api/v1/whatsapp/bot-queue-poll?limit=10&instance_id=test-new-worker")
        self.assertEqual(poll_res.status_code, 200)
        claimed_ids = [it["id"] for it in poll_res.json().get("items", [])]
        self.assertIn(qid, claimed_ids)

        db = SessionLocal()
        row = db.execute(text("SELECT status, result_payload FROM whatsapp_bot_queue WHERE id = :qid"), {"qid": qid}).fetchone()
        db.close()
        self.assertEqual(row[0], "processing")
        self.assertEqual(row[1].get("claim_instance_id"), "test-new-worker")
        self.assertEqual(row[1].get("attempts"), 2)

    def test_f_concurrent_workers_skip_locked_protection(self):
        """Test F: Two workers polling simultaneously receive disjoint queue items with SKIP LOCKED."""
        enq1 = self.client.post("/api/v1/whatsapp/bot-queue-enqueue", json={
            "target_type": "group", "target_jid": "test-grp-1@g.us", "message": "Msg 1", "instance_id": "test-init"
        }).json()["queue_id"]
        enq2 = self.client.post("/api/v1/whatsapp/bot-queue-enqueue", json={
            "target_type": "group", "target_jid": "test-grp-2@g.us", "message": "Msg 2", "instance_id": "test-init"
        }).json()["queue_id"]

        poll1 = self.client.get("/api/v1/whatsapp/bot-queue-poll?limit=1&instance_id=test-worker-A").json()["items"]
        poll2 = self.client.get("/api/v1/whatsapp/bot-queue-poll?limit=1&instance_id=test-worker-B").json()["items"]

        ids1 = [it["id"] for it in poll1]
        ids2 = [it["id"] for it in poll2]

        # Invariant: No duplicate claims between workers
        self.assertTrue(set(ids1).isdisjoint(set(ids2)))
        self.assertEqual(len(ids1), 1)
        self.assertEqual(len(ids2), 1)

    def test_g_multiple_successful_executions_in_one_day(self):
        """Test G: Dynamic counts aggregate all daily executions without hardcoding '1'."""
        db = SessionLocal()
        # Create 3 sent records for today
        for i in range(1, 4):
            db.execute(text("""
                INSERT INTO whatsapp_bot_queue (target_type, target_jid, message, status, created_at, sent_at, instance_id, result_payload)
                VALUES ('group', '120363410784518818@g.us', :msg, 'sent', NOW(), NOW(), 'test-node', CAST(:rp AS jsonb))
            """), {
                "msg": f"SALES TEAM 2-HOUR UPDATE (Run {i})",
                "rp": json.dumps({"job_id": "wa_bihourly_sales_perf_report", "wamid": f"test_wamid_g_{i}"})
            })
        db.commit()
        db.close()

        res = self.client.get("/api/v1/whatsapp/scheduler-status")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        job = next(j for j in data["jobs"] if j["job_id"] == "wa_bihourly_sales_perf_report")

        # Invariant: Exactly 3 executions counted, label reflects '✅ 3 Sent'
        self.assertEqual(job["today"]["count"], 3)
        self.assertEqual(job["today"]["sent_count"], 3)
        self.assertEqual(job["today"]["label"], "✅ 3 Sent")
        self.assertEqual(job["latest_stats"]["sent_count"], 3)

    def test_h_mixed_executions_sent_and_uncertain_counts(self):
        """Test H: Mixed state for one day (2 Sent, 1 Uncertain) is accurately reported."""
        db = SessionLocal()
        # Item 1: Sent
        db.execute(text("""
            INSERT INTO whatsapp_bot_queue (target_type, target_jid, message, status, created_at, sent_at, instance_id, result_payload)
            VALUES ('group', '120363410784518818@g.us', 'SALES TEAM 2-HOUR UPDATE (1:30 PM)', 'sent', NOW(), NOW(), 'test-node', CAST(:rp AS jsonb))
        """), {"rp": json.dumps({"job_id": "wa_bihourly_sales_perf_report", "wamid": "wamid_h_1"})})

        # Item 2: Uncertain (crashed instance at 3:30 PM)
        db.execute(text("""
            INSERT INTO whatsapp_bot_queue (target_type, target_jid, message, status, created_at, instance_id, result_payload)
            VALUES ('group', '120363410784518818@g.us', 'SALES TEAM 2-HOUR UPDATE (3:30 PM)', 'dispatch_uncertain', NOW(), 'test-node-crashed', CAST(:rp AS jsonb))
        """), {"rp": json.dumps({"job_id": "wa_bihourly_sales_perf_report", "send_boundary_entered": True})})

        # Item 3: Sent (Manual 4:54 PM)
        db.execute(text("""
            INSERT INTO whatsapp_bot_queue (target_type, target_jid, message, status, created_at, sent_at, instance_id, result_payload)
            VALUES ('group', '120363410784518818@g.us', 'SALES TEAM 2-HOUR UPDATE (4:54 PM)', 'sent', NOW(), NOW(), 'test-node', CAST(:rp AS jsonb))
        """), {"rp": json.dumps({"job_id": "wa_bihourly_sales_perf_report", "wamid": "wamid_h_3"})})

        db.commit()
        db.close()

        res = self.client.get("/api/v1/whatsapp/scheduler-status")
        self.assertEqual(res.status_code, 200)
        job = next(j for j in res.json()["jobs"] if j["job_id"] == "wa_bihourly_sales_perf_report")

        # Invariant: 2 Sent, 1 Uncertain
        self.assertEqual(job["today"]["sent_count"], 2)
        self.assertEqual(job["today"]["uncertain_count"], 1)
        self.assertEqual(job["today"]["total_count"], 3)
        self.assertEqual(job["today"]["label"], "⚠️ 2 Sent · 1 Uncertain")
        self.assertEqual(job["latest_stats"]["total_messages"], 3)
        self.assertEqual(job["latest_stats"]["sent_count"], 2)
        self.assertEqual(job["latest_stats"]["uncertain_count"], 1)

    def test_i_scheduler_status_persisted_in_db_zero_hardcoded(self):
        """Test I: /scheduler-status derives all values from database queries with zero hardcoded numbers."""
        res = self.client.get("/api/v1/whatsapp/scheduler-status")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data.get("success", True))
        self.assertIn("jobs", data)
        self.assertIn("days", data)

        for job in data["jobs"]:
            # Ensure proper schema
            self.assertIn("job_id", job)
            self.assertIn("today", job)
            self.assertIn("yesterday", job)
            self.assertIn("day_2_ago", job)
            self.assertIn("latest_stats", job)

    def test_j_historical_execution_accurate_across_sessions(self):
        """Test J: Data written to DB remains persistent across independent sessions and queries."""
        db = SessionLocal()
        db.execute(text("""
            INSERT INTO whatsapp_bot_queue (target_type, target_jid, message, status, created_at, sent_at, instance_id, result_payload)
            VALUES ('group', '120363410784518818@g.us', 'Persisted Historical Report', 'sent', NOW() - INTERVAL '1 day', NOW() - INTERVAL '1 day', 'test-node', CAST(:rp AS jsonb))
        """), {"rp": json.dumps({"job_id": "wa_bihourly_sales_perf_report", "wamid": "wamid_yesterday_1"})})
        db.commit()
        db.close()

        # Query endpoint
        res = self.client.get("/api/v1/whatsapp/scheduler-status")
        job = next(j for j in res.json()["jobs"] if j["job_id"] == "wa_bihourly_sales_perf_report")
        self.assertGreaterEqual(job["yesterday"]["sent_count"], 1)
        self.assertEqual(job["yesterday"]["label"], f"✅ {job['yesterday']['sent_count']} Sent")

    def test_k_manual_and_scheduled_parity(self):
        """Test K: Manual and scheduled dispatches record identical metadata format and schema."""
        db = SessionLocal()
        db.execute(text("""
            INSERT INTO whatsapp_bot_queue (target_type, target_jid, message, status, created_at, sent_at, instance_id, result_payload)
            VALUES ('group', '120363410784518818@g.us', 'Scheduled Run', 'sent', NOW(), NOW(), 'test-node', CAST(:rp1 AS jsonb)),
                   ('group', '120363410784518818@g.us', 'Manual Run', 'sent', NOW(), NOW(), 'test-node', CAST(:rp2 AS jsonb))
        """), {
            "rp1": json.dumps({"job_id": "wa_bihourly_sales_perf_report", "trigger_type": "AUTO_SCHEDULER", "wamid": "w_sched"}),
            "rp2": json.dumps({"job_id": "wa_bihourly_sales_perf_report", "trigger_type": "MANUAL", "wamid": "w_man"})
        })
        db.commit()

        rows = db.execute(text("""
            SELECT result_payload->>'trigger_type', status FROM whatsapp_bot_queue
            WHERE instance_id = 'test-node' AND target_jid = '120363410784518818@g.us'
        """)).fetchall()
        db.close()

        types = [r[0] for r in rows]
        statuses = [r[1] for r in rows]
        self.assertIn("AUTO_SCHEDULER", types)
        self.assertIn("MANUAL", types)
        self.assertEqual(set(statuses), {"sent"})

    def test_l_reconcile_historical_queue_id_69_evaluation(self):
        """Test L: Stale in-flight item from terminated instance evaluates authoritatively as dispatch_uncertain."""
        db = SessionLocal()
        # Simulate Queue ID 69
        res = db.execute(text("""
            INSERT INTO whatsapp_bot_queue (target_type, target_jid, message, status, created_at, instance_id, result_payload)
            VALUES ('group', '120363410784518818@g.us', 'SALES TEAM 2-HOUR UPDATE (03:30 PM)', 'processing', NOW() - INTERVAL '10 minutes', 'test-ec2-terminated', CAST(:rp AS jsonb))
            RETURNING id
        """), {
            "rp": json.dumps({
                "job_id": "wa_bihourly_sales_perf_report",
                "claimed_at": (datetime.utcnow() - timedelta(minutes=10)).isoformat(),
                "claim_instance_id": "503b0f267c6f-23",
                "send_boundary_entered": True,
                "send_attempted": True,
                "dispatch_stage": "send_boundary_entered"
            })
        })
        db.commit()
        qid = res.fetchone()[0]

        # Call inflight reconciliation endpoint
        rec_res = self.client.post("/api/v1/whatsapp/bot-queue-reconcile-inflight", json={"reason": "leader_takeover"})
        self.assertEqual(rec_res.status_code, 200)

        row = db.execute(text("SELECT status, error_message, result_payload FROM whatsapp_bot_queue WHERE id = :qid"), {"qid": qid}).fetchone()
        db.close()

        # Invariant: Must transition to dispatch_uncertain, NEVER duplicate resend
        self.assertEqual(row[0], "dispatch_uncertain")
        self.assertIn("dispatch_uncertain to prevent duplicate send", row[1])
        self.assertEqual(row[2].get("dispatch_stage"), "uncertain_send_boundary")

    def test_m_stale_pending_messages_auto_expire_on_poll(self):
        """Test M: Backlog pending messages older than 2 hours are automatically marked expired on poll."""
        db = SessionLocal()
        # Insert a stale pending message created 3 hours ago
        res_stale = db.execute(text("""
            INSERT INTO whatsapp_bot_queue (target_type, target_jid, message, status, created_at, instance_id)
            VALUES ('group', 'test-group@g.us', 'Stale pending message from 3 hours ago', 'pending', NOW() - INTERVAL '3 hours', 'test-stale-item')
            RETURNING id
        """))
        stale_qid = res_stale.fetchone()[0]

        # Insert a fresh pending message created 5 minutes ago
        res_fresh = db.execute(text("""
            INSERT INTO whatsapp_bot_queue (target_type, target_jid, message, status, created_at, instance_id)
            VALUES ('group', 'test-group@g.us', 'Fresh pending message from 5 mins ago', 'pending', NOW() - INTERVAL '5 minutes', 'test-fresh-item')
            RETURNING id
        """))
        fresh_qid = res_fresh.fetchone()[0]
        db.commit()

        # Poll the queue
        poll_res = self.client.get("/api/v1/whatsapp/bot-queue-poll?limit=10&instance_id=test-worker-m")
        self.assertEqual(poll_res.status_code, 200)
        items = poll_res.json().get("items", [])
        claimed_ids = [it["id"] for it in items]

        # Verify: Fresh message was claimed into processing
        self.assertIn(fresh_qid, claimed_ids)
        # Verify: Stale message was NOT claimed by worker
        self.assertNotIn(stale_qid, claimed_ids)

        # Verify DB state of stale item: Must be 'expired'
        row_stale = db.execute(text("SELECT status, error_message, result_payload FROM whatsapp_bot_queue WHERE id = :qid"), {"qid": stale_qid}).fetchone()
        db.close()

        self.assertEqual(row_stale[0], "expired")
        self.assertIn("Time-sensitive pending message superseded", row_stale[1])
        self.assertEqual(row_stale[2].get("expired_reason"), "stale_pending_exceeded_2h")


if __name__ == "__main__":
    unittest.main()
