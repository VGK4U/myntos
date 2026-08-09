"""
Phase 2K.2 Real Meta Ad Proof & Verification Script
Queries Meta Graph API v24.0 directly to verify:
Target Account: act_560062103113819
Primary Campaign: 120254919777680348
Primary Ad Set: 120254919777930348
Facebook Page: 894208310452980
Lead Form: form_3kw_solar_ap
Strict Real World Verification — No mock / no simulation.
"""

import sys
import os
import requests
import json

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.core.database import SessionLocal
from app.services.meta_real_ad_verification_service import execute_real_meta_ad_verification


def main():
    db = SessionLocal()
    print("============================================================")
    print("MYNT OS — PHASE 2K.2 REAL META AD CREATION PROOF EXECUTION")
    print("Target Ad Account: act_560062103113819")
    print("Primary Campaign ID: 120254919777680348")
    print("Primary Ad Set ID: 120254919777930348")
    print("============================================================\n")

    res = execute_real_meta_ad_verification(db, company_id=1, language="en_te")
    db.close()

    print(f"FINAL STATUS: {res.get('status')}\n")
    print(f"1. Live Inventory Discovered on Meta Graph API: {json.dumps(res.get('live_inventory'), indent=2)}")
    print(f"2. Image Hash: {res.get('image_hash')}")
    print(f"3. Real Meta Creative ID: {res.get('real_meta_creative_id')}")
    print(f"4. Real Meta Ad ID: {res.get('real_meta_ad_id')}")
    print(f"5. QA Result: {res.get('qa_result', {}).get('qa_decision')} (Mismatch: {res.get('qa_result', {}).get('mismatch_percentage')}%)")
    print(f"6. Spend: ₹{res.get('spend_inr'):.2f}")
    print(f"7. Error 1815202 Analysis: {json.dumps(res.get('error_1815202_result'), indent=2)}")
    if res.get("upload_error"):
        print(f"8. Upload Error: {json.dumps(res.get('upload_error'), indent=2)}")
    if res.get("creative_error"):
        print(f"9. Creative Error: {json.dumps(res.get('creative_error'), indent=2)}")
    if res.get("ad_error"):
        print(f"10. Ad Error: {json.dumps(res.get('ad_error'), indent=2)}")

    return res


if __name__ == "__main__":
    main()
