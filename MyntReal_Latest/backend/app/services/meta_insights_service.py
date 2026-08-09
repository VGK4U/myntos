"""
Meta Daily Insights Sync Service (Release 1A Analytics Layer)
Read-Only synchronization of Meta ad performance metrics from Graph API.
Zero ad write/modification capabilities. Preserves Meta's native reporting date.
"""

import os
import logging
import requests
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import text

logger = logging.getLogger(__name__)

GRAPH_API_VERSION = "v24.0"


def sync_meta_insights_for_company(db: Session, company_id: int) -> Dict[str, Any]:
    """
    Fetch daily insights for active Facebook pages/ad accounts belonging to company_id.
    READ-ONLY operation: GET /v24.0/act_<ID>/insights.
    Upserts into meta_daily_insights table using meta_reporting_date.
    """
    from app.core.config import settings
    if not getattr(settings, 'META_SYNC_ENABLED', False):
        logger.info("[META-INSIGHTS] Read-only Meta Insights sync disabled via Layer 1 feature flag")
        return {"success": False, "reason": "disabled_by_flag"}

    # Get active facebook page tokens for company
    try:
        pages = db.execute(text(
            "SELECT page_id, page_name, access_token FROM facebook_pages WHERE company_id = :cid AND is_active = TRUE"
        ), {"cid": company_id}).fetchall()
    except Exception as e:
        logger.error(f"[META-INSIGHTS] DB page fetch failed: {e}")
        return {"success": False, "error": str(e)}

    if not pages:
        return {"success": True, "synced_rows": 0, "message": "No active Facebook pages found"}

    from app.core.security_encryption import decrypt_credential_safe

    synced_count = 0
    errors = []

    for page_id, page_name, enc_token in pages:
        token = decrypt_credential_safe(enc_token)
        if not token:
            continue

        # Fetch ad accounts associated with page token
        try:
            url = f"https://graph.facebook.com/{GRAPH_API_VERSION}/me/adaccounts"
            params = {"access_token": token, "fields": "id,name,account_id,timezone_name"}
            resp = requests.get(url, params=params, timeout=15)
            if resp.status_code != 200:
                continue
            ad_accounts = resp.json().get("data", [])
        except Exception as e:
            errors.append(f"Ad account fetch [{page_name}]: {e}")
            continue

        for acc in ad_accounts:
            act_id = acc.get("id")  # e.g. "act_12345678"
            tz_name = acc.get("timezone_name", "Asia/Kolkata")
            if not act_id:
                continue

            # Query daily insights for yesterday
            try:
                insights_url = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{act_id}/insights"
                insights_params = {
                    "access_token": token,
                    "level": "ad",
                    "date_preset": "yesterday",
                    "fields": "campaign_id,campaign_name,adset_id,adset_name,ad_id,ad_name,spend,impressions,reach,clicks,ctr,cpc,cpm,actions"
                }
                i_resp = requests.get(insights_url, params=insights_params, timeout=20)
                if i_resp.status_code != 200:
                    continue

                insights_data = i_resp.json().get("data", [])
                for row in insights_data:
                    c_id = row.get("campaign_id", "")
                    c_name = row.get("campaign_name", "")
                    as_id = row.get("adset_id", "")
                    as_name = row.get("adset_name", "")
                    ad_id = row.get("ad_id", "")
                    ad_name = row.get("ad_name", "")
                    
                    rep_date_str = row.get("date_start")  # Authoritative Meta Reporting Date
                    if not rep_date_str or not ad_id:
                        continue

                    spend = float(row.get("spend", 0.0))
                    impressions = int(row.get("impressions", 0))
                    reach = int(row.get("reach", 0))
                    clicks = int(row.get("clicks", 0))
                    ctr = float(row.get("ctr", 0.0))
                    cpc = float(row.get("cpc", 0.0))
                    cpm = float(row.get("cpm", 0.0))

                    # Count lead actions
                    leads_cnt = 0
                    for act in row.get("actions", []):
                        if act.get("action_type") in ("lead", "leadgen", "offsite_conversion.fb_pixel_lead"):
                            leads_cnt += int(act.get("value", 0))
                    
                    cpl = (spend / leads_cnt) if leads_cnt > 0 else 0.0

                    # Atomic UPSERT into meta_daily_insights preserving Meta native reporting date
                    db.execute(text("""
                        INSERT INTO meta_daily_insights (
                            company_id, ad_account_id, campaign_id, campaign_name,
                            adset_id, adset_name, ad_id, ad_name,
                            meta_ad_account_timezone, meta_reporting_date,
                            myntos_display_timezone, spend, impressions, reach,
                            clicks, ctr, cpc, cpm, leads_count, cpl, updated_at
                        ) VALUES (
                            :cid, :act_id, :camp_id, :camp_name,
                            :adset_id, :adset_name, :ad_id, :ad_name,
                            :tz, :rep_date,
                            'Asia/Kolkata', :spend, :imp, :reach,
                            :clicks, :ctr, :cpc, :cpm, :leads, :cpl, NOW()
                        )
                        ON CONFLICT (company_id, ad_id, meta_reporting_date) DO UPDATE SET
                            campaign_name = EXCLUDED.campaign_name,
                            adset_name    = EXCLUDED.adset_name,
                            ad_name       = EXCLUDED.ad_name,
                            spend         = EXCLUDED.spend,
                            impressions   = EXCLUDED.impressions,
                            reach         = EXCLUDED.reach,
                            clicks        = EXCLUDED.clicks,
                            ctr           = EXCLUDED.ctr,
                            cpc           = EXCLUDED.cpc,
                            cpm           = EXCLUDED.cpm,
                            leads_count   = EXCLUDED.leads_count,
                            cpl           = EXCLUDED.cpl,
                            updated_at    = NOW()
                    """), {
                        "cid": company_id, "act_id": act_id,
                        "camp_id": c_id, "camp_name": c_name,
                        "adset_id": as_id, "adset_name": as_name,
                        "ad_id": ad_id, "ad_name": ad_name,
                        "tz": tz_name, "rep_date": rep_date_str,
                        "spend": spend, "imp": impressions, "reach": reach,
                        "clicks": clicks, "ctr": ctr, "cpc": cpc, "cpm": cpm,
                        "leads": leads_cnt, "cpl": cpl
                    })
                    db.commit()
                    synced_count += 1
            except Exception as ie:
                db.rollback()
                errors.append(f"Insights sync [{act_id}]: {ie}")

    return {"success": True, "synced_rows": synced_count, "errors": errors}
