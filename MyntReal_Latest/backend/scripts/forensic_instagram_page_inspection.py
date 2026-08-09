"""
Phase 2K.6 Facebook Page / Instagram Identity Forensic Inspection Script
Queries Meta Graph API v24.0 directly to audit:
- Facebook Page 894208310452980 ("Myntreal - Har Ghar Solar")
- Instagram Account Linkage & Identity Relationships
- Ad Account act_560062103113819
Read-Only: Zero write, create, edit, or delete operations.
"""

import sys
import os
import requests
import json

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.core.database import SessionLocal
from sqlalchemy import text
from app.core.security_encryption import decrypt_credential_safe

GRAPH_API_VERSION = "v24.0"
AD_ACCOUNT_ID = "act_560062103113819"
PAGE_ID = "894208310452980"


def run_instagram_page_forensics():
    db = SessionLocal()
    p_row = db.execute(text("SELECT access_token FROM facebook_pages WHERE page_id = :pid AND is_active = TRUE LIMIT 1"), {"pid": PAGE_ID}).fetchone()
    if not p_row:
        print("ERROR: No active Facebook Page token found.")
        db.close()
        return

    token = decrypt_credential_safe(p_row[0])
    db.close()

    print("============================================================")
    print("MYNT OS — PHASE 2K.6 INSTAGRAM & PAGE FORENSIC INSPECTION")
    print("Target Facebook Page ID:", PAGE_ID)
    print("Target Ad Account ID:", AD_ACCOUNT_ID)
    print("Graph API Version:", GRAPH_API_VERSION)
    print("============================================================\n")

    # Step 2: Authentication Check
    me_resp = requests.get(f"https://graph.facebook.com/{GRAPH_API_VERSION}/me", params={"access_token": token, "fields": "id,name"})
    print("1. AUTHENTICATION /me RESPONSE:")
    print("   HTTP Status:", me_resp.status_code)
    print("   Response:", me_resp.json() if me_resp.status_code == 200 else me_resp.text)

    if me_resp.status_code != 200:
        print("\nSTOP: Authentication failed.")
        return

    # Step 3: Page Fields Inspection
    page_fields = "id,name,category,tasks"
    p_resp = requests.get(f"https://graph.facebook.com/{GRAPH_API_VERSION}/{PAGE_ID}", params={"access_token": token, "fields": page_fields})
    print("\n2. PAGE BASIC METADATA:")
    print("   HTTP Status:", p_resp.status_code)
    print("   Data:", json.dumps(p_resp.json(), indent=2) if p_resp.status_code == 200 else p_resp.text)

    # Step 4: Check connected_instagram_account
    ig_conn_resp = requests.get(f"https://graph.facebook.com/{GRAPH_API_VERSION}/{PAGE_ID}", params={"access_token": token, "fields": "connected_instagram_account,instagram_business_account"})
    print("\n3. CONNECTED INSTAGRAM ACCOUNT EDGE:")
    print("   HTTP Status:", ig_conn_resp.status_code)
    print("   Data:", json.dumps(ig_conn_resp.json(), indent=2) if ig_conn_resp.status_code == 200 else ig_conn_resp.text)

    # Step 5: Check instagram_accounts sub-edge
    ig_accs_resp = requests.get(f"https://graph.facebook.com/{GRAPH_API_VERSION}/{PAGE_ID}/instagram_accounts", params={"access_token": token})
    print("\n4. /instagram_accounts EDGE:")
    print("   HTTP Status:", ig_accs_resp.status_code)
    print("   Data:", json.dumps(ig_accs_resp.json(), indent=2) if ig_accs_resp.status_code == 200 else ig_accs_resp.text)

    # Step 6: Check page_backed_instagram_accounts sub-edge
    pbig_resp = requests.get(f"https://graph.facebook.com/{GRAPH_API_VERSION}/{PAGE_ID}/page_backed_instagram_accounts", params={"access_token": token})
    print("\n5. /page_backed_instagram_accounts EDGE:")
    print("   HTTP Status:", pbig_resp.status_code)
    print("   Data:", json.dumps(pbig_resp.json(), indent=2) if pbig_resp.status_code == 200 else pbig_resp.text)

    # Step 7: Check Ad Account Business Asset Group
    act_resp = requests.get(f"https://graph.facebook.com/{GRAPH_API_VERSION}/{AD_ACCOUNT_ID}", params={"access_token": token, "fields": "id,name,account_status,currency,timezone_name,business"})
    print("\n6. AD ACCOUNT BUSINESS METADATA:")
    print("   HTTP Status:", act_resp.status_code)
    print("   Data:", json.dumps(act_resp.json(), indent=2) if act_resp.status_code == 200 else act_resp.text)

    print("\n============================================================")
    print("FORENSIC INSPECTION COMPLETE")
    print("============================================================\n")


if __name__ == "__main__":
    run_instagram_page_forensics()
