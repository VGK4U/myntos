"""
Phase 2K.3 Meta OAuth Token & Live API Health Verification Script
Executes 100% read-only Graph API v24.0 health verification.
Zero writes, zero creations, zero deletions.
"""

import sys
import os
import json

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.core.database import SessionLocal
from app.services.meta_token_health_service import verify_meta_oauth_token_health


def main():
    db = SessionLocal()
    print("============================================================")
    print("MYNT OS — PHASE 2K.3 TOKEN & LIVE API HEALTH VERIFICATION")
    print("Target Ad Account: act_560062103113819")
    print("Primary Campaign ID: 120254919777680348")
    print("Primary Ad Set ID: 120254919777930348")
    print("============================================================\n")

    res = verify_meta_oauth_token_health(db, company_id=1)
    db.close()

    print(f"FINAL STATUS: {res.get('status')}\n")
    print(f"Authentication: {res.get('authentication')}")
    print(f"OAuth Token: {res.get('oauth_token')}")
    print(f"OAuth Code: {res.get('oauth_code')}")
    print(f"OAuth Subcode: {res.get('oauth_subcode')}")
    print(f"OAuth Message: {res.get('oauth_message')}")
    print(f"Ad Account Health: {res.get('ad_account', {}).get('status')}")
    print(f"Page Health: {res.get('page', {}).get('status')}")
    print(f"Lead Form Health: {res.get('lead_form', {}).get('status')}")
    print(f"Primary Campaign Health: {res.get('primary_campaign', {}).get('status')}")
    print(f"Primary Ad Set Health: {res.get('primary_adset', {}).get('status')}")
    print(f"Live Ads Count: {res.get('live_ads_count')}")
    print(f"Live Creatives Count: {res.get('live_creatives_count')}")
    print(f"Spend: ₹{res.get('spend_inr'):.2f}")
    print(f"Token Encryption: {res.get('token_encryption')}")
    print(f"Write Protection: {res.get('write_protection')}")
    print(f"Fallback Protection: {res.get('fallback_protection')}")
    print(f"Token Expiration Handling: {res.get('token_expiration_handling')}")
    print(f"Error 1815202: {res.get('error_1815202_result')}")
    print(f"\nReauthorization Login URL: {res.get('reauthorization_login_url')}")

    return res


if __name__ == "__main__":
    main()
