"""
Unit test for Service Group Alerts and VGK4U Community/Channel Alerts
"""
import sys, os
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from app.core.database import SessionLocal
from app.services.service_group_alert_service import (
    send_daily_service_summary_report,
    send_instant_service_ticket_alert
)
from app.services.vgk4u_community_alert_service import (
    dispatch_daily_vgk4u_morning_wish,
    send_partner_lead_added_congratulations,
    send_partner_payout_disbursed_congratulations
)

def test_service_and_vgk4u_alerts():
    db = SessionLocal()
    try:
        print("\n--- 1. Testing Daily Service Summary Report Formatting ---")
        srv_res = send_daily_service_summary_report(db)
        print(f"Service Summary Result: {srv_res}")
        assert "success" in srv_res

        print("\n--- 2. Testing Daily VGK4U 8 AM Morning Wish Dispatch ---")
        wish_res = dispatch_daily_vgk4u_morning_wish(db)
        print(f"Morning Wish Result: {wish_res}")
        assert "success" in wish_res

        print("\n--- 3. Testing Partner Lead Addition Congratulatory Alert ---")
        lead_congrat_res = send_partner_lead_added_congratulations(
            db, partner_name="R. Venkatesh", lead_name="K. Satyanarayana", city="Visakhapatnam"
        )
        print(f"Lead Congratulation Result: {lead_congrat_res}")
        assert "success" in lead_congrat_res

        print("\n--- 4. Testing Partner Payout Disbursal Congratulatory Alert ---")
        payout_congrat_res = send_partner_payout_disbursed_congratulations(
            db, partner_name="K. Anjaneyulu", amount=15000.00, payout_type="3KW Solar Commission"
        )
        print(f"Payout Congratulation Result: {payout_congrat_res}")
        assert "success" in payout_congrat_res

        print("\n✅ ALL SERVICE & VGK4U COMMUNITY ALERT UNIT TESTS PASSED SUCCESSFULLY!\n")
    finally:
        db.close()

if __name__ == "__main__":
    test_service_and_vgk4u_alerts()
