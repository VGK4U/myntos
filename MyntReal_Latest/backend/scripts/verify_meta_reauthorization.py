"""
Phase 2K.4 Real Meta OAuth Reauthorization Verification Script
Queries Meta Graph API v24.0 directly to verify:
Target Account: 560062103113819 (act_560062103113819)
Page: 894208310452980
Lead Form: form_3kw_solar_ap
Primary Campaign: 120254919777680348
Primary Ad Set: 120254919777930348
Strict Read-Only Verification — No mock / no simulation.
"""

import sys
import os
import json

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.core.database import SessionLocal
from app.services.meta_reauthorization_service import verify_real_meta_reauthorization


def main():
    db = SessionLocal()
    print("============================================================")
    print("MYNT OS — PHASE 2K.4 REAL META OAUTH REAUTHORIZATION PROOF")
    print("Target Ad Account: 560062103113819 (act_560062103113819)")
    print("Facebook Page: 894208310452980 (Myntreal - Har Ghar Solar)")
    print("============================================================\n")

    res = verify_real_meta_reauthorization(db, company_id=1)
    db.close()

    print(f"FINAL STATUS: {res.get('status')}\n")
    print(f"Authentication: {res.get('authentication')}")
    print(f"New Token Status: {res.get('new_token_status')}")
    print(f"Token Expiry: {res.get('token_expiry')}")
    print(f"Meta User ID: {res.get('meta_user_id')}")
    print(f"Meta User Name: {res.get('meta_user_name')}")
    print(f"Granted Permissions: {json.dumps(res.get('granted_permissions'), indent=2)}")
    print(f"Ad Account Details: {json.dumps(res.get('ad_account'), indent=2)}")
    print(f"Facebook Page: {json.dumps(res.get('facebook_page'), indent=2)}")
    print(f"Lead Form: {json.dumps(res.get('lead_form'), indent=2)}")
    print(f"Primary Campaign: {json.dumps(res.get('primary_campaign'), indent=2)}")
    print(f"Primary Ad Set: {json.dumps(res.get('primary_adset'), indent=2)}")
    print(f"Fresh Live Inventory: {json.dumps(res.get('fresh_live_inventory'), indent=2)}")
    spend_val = res.get('spend_inr') or 0.0
    print(f"Spend: ₹{spend_val:.2f}")
    print(f"Token Encryption: {res.get('token_encryption')}")
    print(f"OAuth State Validation: {res.get('oauth_state_validation')}")
    print(f"Token Expiration Protection: {res.get('token_expiration_protection')}")
    print(f"Write Protection: {res.get('write_protection')}")
    print(f"Error 1815202: {res.get('error_1815202_result')}")
    print(f"Meta Write Operations Count: {res.get('meta_write_operations_count')}")

    return res


if __name__ == "__main__":
    main()
