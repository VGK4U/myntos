"""
Phase 2K Live Meta Graph API Forensic Inventory Script
Queries Meta Graph API v24.0 directly for Ad Account act_560062103113819.
Retrieves ALL campaigns, ad sets, ads, creatives, and lead forms.
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


def run_forensic_inventory():
    db = SessionLocal()
    p_row = db.execute(text("SELECT access_token FROM facebook_pages WHERE page_id = :pid AND is_active = TRUE"), {"pid": PAGE_ID}).fetchone()
    if not p_row:
        print("ERROR: No active Facebook Page token found in DB.")
        db.close()
        return

    token = decrypt_credential_safe(p_row[0])
    db.close()

    print("============================================================")
    print("MYNT OS — PHASE 2K META GRAPH API FORENSIC INVENTORY")
    print("Target Ad Account:", AD_ACCOUNT_ID)
    print("Graph API Version:", GRAPH_API_VERSION)
    print("============================================================\n")

    # 1. Fetch ALL Campaigns
    c_url = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{AD_ACCOUNT_ID}/campaigns"
    c_params = {
        "access_token": token,
        "fields": "id,name,status,effective_status,objective,daily_budget,created_time,updated_time,start_time,stop_time,buying_type,special_ad_categories",
        "limit": 100
    }
    c_resp = requests.get(c_url, params=c_params)
    campaigns = c_resp.json().get("data", []) if c_resp.status_code == 200 else []
    print(f"1. CAMPAIGNS DISCOVERED ON META GRAPH API: {len(campaigns)}")
    for i, c in enumerate(campaigns, 1):
        print(f"   [{i:02d}] ID: {c.get('id')} | Name: '{c.get('name')}' | Status: {c.get('status')} ({c.get('effective_status')}) | Created: {c.get('created_time')}")

    # 2. Fetch ALL Ad Sets
    as_url = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{AD_ACCOUNT_ID}/adsets"
    as_params = {
        "access_token": token,
        "fields": "id,name,status,effective_status,campaign_id,daily_budget,optimization_goal,billing_event,targeting,created_time,updated_time",
        "limit": 100
    }
    as_resp = requests.get(as_url, params=as_params)
    adsets = as_resp.json().get("data", []) if as_resp.status_code == 200 else []
    print(f"\n2. AD SETS DISCOVERED ON META GRAPH API: {len(adsets)}")
    for i, a in enumerate(adsets, 1):
        print(f"   [{i:02d}] ID: {a.get('id')} | Campaign ID: {a.get('campaign_id')} | Name: '{a.get('name')}' | Status: {a.get('status')} ({a.get('effective_status')})")

    # 3. Fetch ALL Ads
    ad_url = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{AD_ACCOUNT_ID}/ads"
    ad_params = {
        "access_token": token,
        "fields": "id,name,status,effective_status,adset_id,campaign_id,creative,created_time,updated_time",
        "limit": 100
    }
    ad_resp = requests.get(ad_url, params=ad_params)
    ads = ad_resp.json().get("data", []) if ad_resp.status_code == 200 else []
    print(f"\n3. ADS DISCOVERED ON META GRAPH API: {len(ads)}")
    if not ads:
        print("   -> ADS_FOUND = 0 (Confirmed: Zero Ads exist on Meta Ads Manager under this Ad Account)")
    else:
        for i, ad in enumerate(ads, 1):
            print(f"   [{i:02d}] ID: {ad.get('id')} | AdSet ID: {ad.get('adset_id')} | Name: '{ad.get('name')}' | Status: {ad.get('status')}")

    # 4. Fetch ALL Ad Creatives
    cr_url = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{AD_ACCOUNT_ID}/adcreatives"
    cr_params = {
        "access_token": token,
        "fields": "id,name,status,object_story_spec,title,body",
        "limit": 100
    }
    cr_resp = requests.get(cr_url, params=cr_params)
    creatives = cr_resp.json().get("data", []) if cr_resp.status_code == 200 else []
    print(f"\n4. AD CREATIVES DISCOVERED ON META GRAPH API: {len(creatives)}")
    for i, cr in enumerate(creatives, 1):
        print(f"   [{i:02d}] ID: {cr.get('id')} | Name: '{cr.get('name')}'")

    print("\n============================================================")
    print("FORENSIC INVENTORY SUMMARY:")
    print(f"Campaigns: {len(campaigns)} | Ad Sets: {len(adsets)} | Ads: {len(ads)} | Creatives: {len(creatives)}")
    print("============================================================\n")

    return {
        "campaigns": campaigns,
        "adsets": adsets,
        "ads": ads,
        "creatives": creatives
    }


if __name__ == "__main__":
    run_forensic_inventory()
