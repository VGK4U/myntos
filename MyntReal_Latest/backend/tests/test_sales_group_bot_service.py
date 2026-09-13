"""
Unit test for Sales WhatsApp Group Bot Service, 2-Hour Performance Updates, & Lead Alerts
"""
import sys, os
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from app.core.database import SessionLocal
from app.services.sales_performance_report_service import (
    get_today_sales_performance_stats,
    generate_bi_hourly_performance_message
)
from app.services.whatsapp_group_alert_service import send_instant_new_lead_group_alert

def test_sales_group_bot():
    db = SessionLocal()
    try:
        print("\n--- 1. Testing Today Sales Performance Statistics Calculation ---")
        stats = get_today_sales_performance_stats(db)
        print(f"Calculated Stats: {stats}")
        assert "total_calls" in stats
        assert "total_talk_formatted" in stats
        assert "leaderboard" in stats

        # 1b. Verify Canonical Tele Sales Roster Invariants
        staff_names = [item["handled_by"] for item in stats["leaderboard"]]
        print(f"Roster Staff Names ({len(staff_names)}): {staff_names}")

        # Assert Hema (MN10017) and Poojitha (MN10016) are present
        assert any("Hema" in name and "Janapala" in name for name in staff_names), "Mrs. Janapala Hema must be in sales performance roster"
        assert any("pujitha" in name.lower() or "poojitha" in name.lower() for name in staff_names), "Ms. Narsi Kurmasri pujitha must be in sales performance roster"

        # Assert Service staff (Hema Chandra Prasad Adigarla) and Freelancers (Padma Rao) are strictly excluded
        assert not any("Adigarla" in name for name in staff_names), "Service employee Mr. Hema Chandra Prasad Adigarla must NOT be in sales roster"
        assert not any("Padma Rao" in name for name in staff_names), "Freelancer Mr. Padma Rao must NOT be in sales roster"

        print("\n--- 2. Testing 2-Hour Progress Update Message Generation ---")
        msg = generate_bi_hourly_performance_message(db, slot_name="11:30 AM Update")
        print("Generated Message Output:\n")
        print(msg)
        assert "SALES TEAM" in msg
        assert "STAFF LEADERBOARD TODAY" in msg
        assert "Janapala Hema" in msg, "Mrs. Janapala Hema must appear in the WhatsApp message text"
        assert "pujitha" in msg.lower() or "poojitha" in msg.lower(), "Ms. Narsi Kurmasri pujitha must appear in the WhatsApp message text"

        print("\n--- 3. Testing Instant New Lead Group Alert Formatting ---")
        # Find any sample lead
        from app.models.crm import CRMLead
        sample_lead = db.query(CRMLead).first()
        if sample_lead:
            alert_res = send_instant_new_lead_group_alert(db, sample_lead.id)
            print(f"Lead Alert Dispatch Attempt Result: {alert_res}")

        print("\n✅ ALL SALES GROUP BOT & ROSTER ELIGIBILITY UNIT TESTS PASSED SUCCESSFULLY!\n")
    finally:
        db.close()

import unittest

class TestSalesGroupBotService(unittest.TestCase):
    def test_sales_group_bot(self):
        test_sales_group_bot()

if __name__ == "__main__":
    unittest.main()
