"""
Phase 2K.5 Real Meta Ad Creation — Single-Ad Controlled Verification Script
Queries Meta Graph API v24.0 directly to execute:
1. One image upload (POST /adimages)
2. One ad creative creation (POST /adcreatives)
3. One ad creation (POST /ads) in PAUSED status under Ad Set 120254919777930348
Strict Real-World Verification — Zero fallback IDs / Zero mock responses.
"""

import sys
import os
import json

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.core.database import SessionLocal
from app.services.meta_single_ad_creation_service import execute_single_ad_controlled_verification


def main():
    db = SessionLocal()
    print("============================================================")
    print("MYNT OS — PHASE 2K.5 SINGLE-AD CONTROLLED VERIFICATION")
    print("Target Ad Account: act_560062103113819")
    print("Primary Campaign ID: 120254919777680348")
    print("Primary Ad Set ID: 120254919777930348")
    print("============================================================\n")

    res = execute_single_ad_controlled_verification(db, company_id=1, language="en_te")
    db.close()

    print(f"FINAL STATUS: {res.get('status') or res.get('Z_final_status')}\n")
    print(f"A. Authentication: {res.get('A_authentication')}")
    print(f"B. Ad Account: {res.get('B_ad_account')}")
    print(f"C. Campaign: {res.get('C_campaign')}")
    print(f"D. Ad Set: {res.get('D_ad_set')}")
    print(f"E. Page: {res.get('E_page')}")
    print(f"F. Lead Form: {res.get('F_lead_form')}")
    print(f"G. Creative QA: {res.get('G_creative_qa')}")
    print(f"H. OCR English Result: {res.get('H_ocr_english_result')}")
    print(f"I. OCR Telugu Result: {res.get('I_ocr_telugu_result')}")
    print(f"J. Image Upload Result: {res.get('J_image_upload_result')}")
    print(f"K. Real Meta Image Hash: {res.get('K_real_meta_image_hash')}")
    print(f"L. Error 1815202 Result: {res.get('L_error_1815202_result')}")
    print(f"M. Real Meta Creative ID: {res.get('M_real_meta_creative_id')}")
    print(f"N. Real Meta Ad ID: {res.get('N_real_meta_ad_id')}")
    print(f"O. Final Ad Status: {res.get('O_final_ad_status')}")
    print(f"P. Campaign Status: {res.get('P_campaign_status')}")
    print(f"Q. Ad Set Status: {res.get('Q_adset_status')}")
    print(f"R. Spend: ₹{res.get('R_spend_inr', 0.0):.2f}")
    print(f"S. Database Reconciliation: {res.get('S_database_reconciliation')}")
    print(f"T. Idempotency Fingerprint: {res.get('T_idempotency_fingerprint')}")
    print(f"U. Campaigns Created Count: {res.get('U_campaigns_created_count')}")
    print(f"V. Ad Sets Created Count: {res.get('V_adsets_created_count')}")
    print(f"W. Ads Created Count: {res.get('W_ads_created_count')}")
    print(f"X. Creatives Created Count: {res.get('X_creatives_created_count')}")
    print(f"Y. Meta Write Operations Count: {res.get('Y_meta_write_operations_count')}")
    print(f"Z. Final Status: {res.get('Z_final_status') or res.get('status')}")

    if res.get("meta_response"):
        print(f"\nMeta Response Telemetry: {json.dumps(res.get('meta_response'), indent=2)}")

    return res


if __name__ == "__main__":
    main()
