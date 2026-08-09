"""
Phase 2L.5 Meta Ad Review & Delivery Verification Script
Monitors live Meta Graph API v24.0 state for Har Ghar Solar Ad 120254925638870348.
Strict Read-Only Execution: Zero Meta Write Operations.
"""

import os
import sys
import requests
import json
from typing import Dict, Any

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.core.database import SessionLocal
from sqlalchemy import text
from app.core.security_encryption import decrypt_credential_safe

GRAPH_API_VERSION = "v24.0"
AD_ACCOUNT_ID = "act_560062103113819"
CAMPAIGN_ID = "120254919777680348"

# Har Ghar Solar Objects
HGS_ADSET_ID = "120254925638200348"
HGS_CREATIVE_ID = "1063753229511074"
HGS_AD_ID = "120254925638870348"
HGS_PAGE_ID = "894208310452980"

# VGK4U Protected Objects
VGK_ADSET_ID = "120254919777930348"
VGK_AD_ID = "120254925357440348"

DESTINATION_URL = "https://vgk4u.com"
LEAD_FORM = "form_3kw_solar_ap"


def run_review_verification() -> Dict[str, Any]:
    db = SessionLocal()

    p_row = db.execute(text("SELECT access_token FROM facebook_pages WHERE company_id = 1 AND is_active = TRUE LIMIT 1")).fetchone()
    token = decrypt_credential_safe(p_row[0]) if p_row else None
    if not token:
        db.close()
        return {"status": "META_STATUS_REQUIRES_REVIEW", "reason": "MISSING_DECRYPTED_TOKEN"}

    print("============================================================")
    print("MYNT OS — PHASE 2L.5 LIVE META REVIEW & DELIVERY CHECK")
    print("============================================================\n")

    # 1. Query Campaign
    c_res = requests.get(f"https://graph.facebook.com/{GRAPH_API_VERSION}/{CAMPAIGN_ID}", params={"access_token": token, "fields": "id,name,status,effective_status,objective"}).json()
    
    # 2. Query Har Ghar Solar AdSet
    as_res = requests.get(f"https://graph.facebook.com/{GRAPH_API_VERSION}/{HGS_ADSET_ID}", params={"access_token": token, "fields": "id,name,status,effective_status,promoted_object,daily_budget"}).json()
    
    # 3. Query Har Ghar Solar Ad
    ad_res = requests.get(f"https://graph.facebook.com/{GRAPH_API_VERSION}/{HGS_AD_ID}", params={"access_token": token, "fields": "id,name,status,effective_status,issues_info,creative,ad_review_feedback"}).json()
    
    # 4. Query Creative
    cr_res = requests.get(f"https://graph.facebook.com/{GRAPH_API_VERSION}/{HGS_CREATIVE_ID}", params={"access_token": token, "fields": "id,name,object_story_spec"}).json()
    
    # 5. Query Insights / Spend Telemetry
    insights_res = requests.get(f"https://graph.facebook.com/{GRAPH_API_VERSION}/{HGS_AD_ID}/insights", params={"access_token": token, "fields": "spend,impressions,reach,clicks,ctr,actions", "date_preset": "maximum"}).json()
    insights_data = insights_res.get("data", [])
    
    spend = "₹0.00"
    impressions = "0"
    reach = "0"
    clicks = "0"
    ctr = "0.00%"
    leads = "0"

    if len(insights_data) > 0:
        row = insights_data[0]
        spend = f"₹{float(row.get('spend', 0.0)):.2f}"
        impressions = str(row.get("impressions", "0"))
        reach = str(row.get("reach", "0"))
        clicks = str(row.get("clicks", "0"))
        ctr = f"{float(row.get('ctr', 0.0)):.2f}%"
        for act in row.get("actions", []):
            if act.get("action_type") in ("lead", "onsite_conversion.lead_grouped"):
                leads = str(act.get("value", "0"))

    # 6. VGK4U Protection Check
    vgk_as_res = requests.get(f"https://graph.facebook.com/{GRAPH_API_VERSION}/{VGK_ADSET_ID}", params={"access_token": token, "fields": "id,name,status"}).json()
    vgk_ad_res = requests.get(f"https://graph.facebook.com/{GRAPH_API_VERSION}/{VGK_AD_ID}", params={"access_token": token, "fields": "id,name,status"}).json()

    if vgk_as_res.get("status") != "PAUSED" or vgk_ad_res.get("status") != "PAUSED":
        db.close()
        return {
            "status": "UNAUTHORIZED_VGK4U_ACTIVATION",
            "reason": f"VGK4U UNEXPECTEDLY ACTIVATED: AdSet {vgk_as_res.get('status')}, Ad {vgk_ad_res.get('status')}"
        }

    # 7. Database Reconciliation Verification
    db_ad = db.execute(text("SELECT id, ad_id, creative_id, status, ad_fingerprint, fingerprint_version FROM meta_ads WHERE ad_id = :adid"), {"adid": HGS_AD_ID}).fetchone()
    db_reconciled = "RECONCILED" if db_ad else "NOT RECONCILED"

    db.close()

    # Determine Final Classification Status
    ad_eff_status = ad_res.get("effective_status", "UNKNOWN")
    issues = ad_res.get("issues_info", [])

    if len(issues) > 0 or ad_eff_status in ("DISAPPROVED", "WITH_ISSUES"):
        final_status = "META_AD_REJECTED" if ad_eff_status == "DISAPPROVED" else "META_DELIVERY_ERROR"
    elif ad_eff_status in ("IN_PROCESS", "PENDING_REVIEW"):
        final_status = "META_REVIEW_IN_PROGRESS"
    elif ad_eff_status == "ACTIVE" and (float(impressions) > 0 or float(spend.replace('₹','')) > 0):
        final_status = "META_AD_DELIVERING"
    elif ad_eff_status in ("ACTIVE", "CAMPAIGN_PAUSED", "ADSET_PAUSED", "IN_PROCESS"):
        # Currently in Meta Ad Review / Approved Ready to Deliver
        if ad_eff_status == "ACTIVE":
            final_status = "META_AD_APPROVED_READY_TO_DELIVER"
        else:
            final_status = "META_REVIEW_IN_PROGRESS"
    else:
        final_status = "META_STATUS_REQUIRES_REVIEW"

    return {
        "status": final_status,
        "campaign": {
            "id": CAMPAIGN_ID,
            "status": c_res.get("status"),
            "effective_status": c_res.get("effective_status")
        },
        "hgs_adset": {
            "id": HGS_ADSET_ID,
            "status": as_res.get("status"),
            "effective_status": as_res.get("effective_status")
        },
        "hgs_ad": {
            "id": HGS_AD_ID,
            "status": ad_res.get("status"),
            "effective_status": ad_res.get("effective_status")
        },
        "review_status": ad_eff_status,
        "issues_info": issues,
        "telemetry": {
            "spend": spend,
            "impressions": impressions,
            "reach": reach,
            "clicks": clicks,
            "ctr": ctr,
            "leads": leads,
            "delivery_note": "NO_DELIVERY_DATA_YET" if impressions == "0" else "DELIVERY_ACTIVE"
        },
        "lead_form": {
            "form": LEAD_FORM,
            "verification_status": "LEAD_RETRIEVAL_NOT_YET_EMPIRICALLY_VERIFIED" if leads == "0" else "VERIFIED"
        },
        "destination_url": DESTINATION_URL,
        "vgk4u_adset": vgk_as_res.get("status"),
        "vgk4u_ad": vgk_ad_res.get("status"),
        "database": {
            "reconciliation_status": db_reconciled,
            "db_id": db_ad[0] if db_ad else None,
            "ad_id": db_ad[1] if db_ad else None,
            "creative_id": db_ad[2] if db_ad else None,
            "fingerprint": db_ad[4] if db_ad else None,
            "fingerprint_version": db_ad[5] if db_ad else None
        }
    }


if __name__ == "__main__":
    res = run_review_verification()
    print(json.dumps(res, indent=2))
