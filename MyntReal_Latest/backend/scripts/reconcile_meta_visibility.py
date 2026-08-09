"""
Reconcile Meta Object Visibility & Account ID Mismatch (Urgent Reconciliation Script)
Queries Graph API v24.0 and database records to explain Ads Manager visibility mismatch.
"""

import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.core.database import SessionLocal
from sqlalchemy import text
from app.core.security_encryption import decrypt_credential_safe
import requests

GRAPH_API_VERSION = "v24.0"

db = SessionLocal()

print("=" * 60)
print("REAL-TIME META OBJECT VISIBILITY RECONCILIATION")
print("=" * 60)

# 1. Fetch DB Page & Token
p_row = db.execute(text("SELECT page_id, page_name, access_token FROM facebook_pages WHERE is_active = TRUE ORDER BY id ASC LIMIT 1")).fetchone()

if p_row:
    token = decrypt_credential_safe(p_row[2])
    print(f"[DB-CHECK] Page ID: {p_row[0]} ({p_row[1]}), Token Decrypted: {'YES' if token else 'NO'}")
else:
    token = None
    print("[DB-CHECK] No active page token in facebook_pages")

# 2. Query DB for reported IDs
reported_ids = ['23849182374619', '23850293847120', '23851384729103', '23852495830192']
print("\n[DB-SEARCH] Searching database for reported IDs:")
for rid in reported_ids:
    c_found = db.execute(text("SELECT id, campaign_id, account_id, name, status FROM meta_campaigns WHERE campaign_id = :rid"), {"rid": rid}).fetchone()
    print(f" - Campaign {rid}: {'FOUND IN DB: ' + str(c_found) if c_found else 'NOT FOUND IN DB'}")

# 3. Query Graph API for accessible Ad Accounts
accessible_accounts = []
if token:
    try:
        url = f"https://graph.facebook.com/{GRAPH_API_VERSION}/me/adaccounts"
        resp = requests.get(url, params={"access_token": token, "fields": "id,account_id,name,account_status,currency"}, timeout=10)
        if resp.status_code == 200:
            accessible_accounts = resp.json().get("data", [])
            print(f"\n[GRAPH-API] Accessible Ad Accounts for Token ({len(accessible_accounts)}):")
            for acc in accessible_accounts:
                print(f" - ID: {acc.get('id')} | Name: {acc.get('name')} | Currency: {acc.get('currency')}")
        else:
            print(f"\n[GRAPH-API] GET /me/adaccounts returned HTTP {resp.status_code}: {resp.text}")
    except Exception as e:
        print(f"\n[GRAPH-API] Error querying ad accounts: {e}")

# 4. Direct GET /v24.0/23849182374619
if token:
    for rid in reported_ids:
        try:
            r_resp = requests.get(f"https://graph.facebook.com/{GRAPH_API_VERSION}/{rid}", params={"access_token": token}, timeout=10)
            print(f"\n[GRAPH-API-DIRECT] GET /{rid} -> HTTP {r_resp.status_code}: {r_resp.text[:200]}")
        except Exception as e:
            print(f"\n[GRAPH-API-DIRECT] GET /{rid} Exception: {e}")

db.close()
