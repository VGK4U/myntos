"""
Unit test for MyOperator missed call WhatsApp auto-acknowledgement service
"""
import sys, os
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from app.core.database import SessionLocal
from app.services.whatsapp_missed_call_service import (
    seed_and_submit_missed_call_template,
    handle_missed_call_whatsapp_ack
)

def test_missed_call_ack():
    db = SessionLocal()
    try:
        print("\n--- 1. Testing Missed Call Template Seeding & Meta Submission ---")
        seed_res = seed_and_submit_missed_call_template(db)
        print(f"Seed Result: {seed_res}")
        assert seed_res["success"] is True

        print("\n--- 2. Testing First Missed Call (Auto-Creates Lead + Sends ACK) ---")
        test_phone = "919988776655"
        res1 = handle_missed_call_whatsapp_ack(db, test_phone, caller_name="Test Missed Caller")
        print(f"ACK Result 1: {res1}")
        assert res1["success"] is True

        print("\n--- 3. Testing Outbound Call Guard (Skips Outbound Dialing Attempts) ---")
        res_outbound = handle_missed_call_whatsapp_ack(db, test_phone, caller_name="Test Missed Caller", call_type="outbound")
        print(f"Outbound Test Result: {res_outbound}")
        assert res_outbound["success"] is True
        assert res_outbound.get("reason") == "skipped_outbound_call"

        print("\n--- 4. Testing 24-Hour Deduplication Guard (Max 1 ACK per 24 hours) ---")
        res_dedup = handle_missed_call_whatsapp_ack(db, test_phone, caller_name="Test Missed Caller", call_type="inbound")
        print(f"24h Dedup Result: {res_dedup}")
        assert res_dedup["success"] is True
        assert res_dedup.get("reason") == "skipped_dedup_24h"

        print("\n✅ ALL ENHANCED SPAM GUARD UNIT TESTS PASSED SUCCESSFULLY!\n")
    finally:
        db.close()

if __name__ == "__main__":
    test_missed_call_ack()
