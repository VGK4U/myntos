"""
Unit test for 4-day rotating morning wish service
"""
import sys, os
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from app.core.database import SessionLocal
from app.services.whatsapp_morning_wish_service import (
    seed_and_submit_morning_wish_templates,
    get_current_rotation_template,
    get_eligible_leads_for_morning_wish,
    dispatch_daily_morning_wishes
)

def test_morning_wish_rotation():
    db = SessionLocal()
    try:
        print("\n--- 1. Testing Template Seeding ---")
        seed_res = seed_and_submit_morning_wish_templates(db)
        print(f"Seed Result: {seed_res}")
        assert seed_res["success"] is True
        assert len(seed_res["templates"]) == 4

        print("\n--- 2. Testing Rotation Calculation ---")
        rot_res = get_current_rotation_template(db)
        print(f"Current Rotation: {rot_res}")
        assert 1 <= rot_res["rot_index"] <= 4

        print("\n--- 3. Testing Lead Eligibility Query ---")
        leads = get_eligible_leads_for_morning_wish(db)
        print(f"Eligible Leads Found: {len(leads)}")

        print("\n--- 4. Testing Dispatch Function (Dry Run/Simulation on 5 leads) ---")
        dispatch_res = dispatch_daily_morning_wishes(db, force_test=True, limit_count=5)
        print(f"Dispatch Result: {dispatch_res}")
        assert dispatch_res["success"] is True

        print("\n✅ ALL MORNING WISH UNIT TESTS PASSED SUCCESSFULLY!\n")
    finally:
        db.close()

if __name__ == "__main__":
    test_morning_wish_rotation()
