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

        print("\n--- 3. Testing Duplicate Missed Call within 6 Hours (Spam Guard) ---")
        res2 = handle_missed_call_whatsapp_ack(db, test_phone, caller_name="Test Missed Caller")
        print(f"ACK Result 2 (Deduplication Check): {res2}")
        assert res2["success"] is True
        assert res2.get("reason") == "skipped_dedup_6h"

        print("\n✅ MISSED CALL ACK SERVICE UNIT TESTS PASSED SUCCESSFULLY!\n")
    finally:
        db.close()

if __name__ == "__main__":
    test_missed_call_ack()
