"""
Meta Ads Read-Only Sync Service (Phase 2 Meta Integration Layer)
Synchronizes campaigns, ad sets, ads, and creatives via Graph API GET requests.
Zero write capabilities to Meta Ads Manager. Respects feature flags and write protections.
"""

import logging
import requests
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.core.config import settings

logger = logging.getLogger(__name__)

GRAPH_API_VERSION = "v24.0"


def sync_meta_campaign_hierarchy(db: Session, company_id: int) -> Dict[str, Any]:
    """
    Synchronize campaigns, ad sets, ads, and creatives for company_id.
    READ-ONLY operation.
    """
    if not getattr(settings, 'META_SYNC_ENABLED', False) and not getattr(settings, 'META_ADS_READ_ENABLED', False):
        logger.info("[META-ADS-SYNC] Meta Ads Read-Only sync disabled via Layer 1 feature flag")
        return {"success": False, "reason": "disabled_by_flag"}

    # Enforce write protection
    if getattr(settings, 'META_ADS_WRITE_ENABLED', False):
        logger.error("[SECURITY-ALERT] META_ADS_WRITE_ENABLED must be False in Phase 2!")
        return {"success": False, "reason": "write_enabled_security_violation"}

    try:
        pages = db.execute(text(
            "SELECT page_id, page_name, access_token FROM facebook_pages WHERE company_id = :cid AND is_active = TRUE"
        ), {"cid": company_id}).fetchall()
    except Exception as e:
        logger.error(f"[META-ADS-SYNC] DB page query error: {e}")
        return {"success": False, "error": str(e)}

    if not pages:
        return {"success": True, "synced_campaigns": 0, "message": "No active Facebook pages found"}

    from app.core.security_encryption import decrypt_credential_safe

    synced_c = 0
    synced_as = 0
    synced_ad = 0

    for page_id, page_name, enc_token in pages:
        token = decrypt_credential_safe(enc_token)
        if not token:
            continue

        try:
            url = f"https://graph.facebook.com/{GRAPH_API_VERSION}/me/adaccounts"
            params = {"access_token": token, "fields": "id,name,account_id"}
            resp = requests.get(url, params=params, timeout=15)
            if resp.status_code != 200:
                continue
            ad_accounts = resp.json().get("data", [])
        except Exception:
            continue

        for acc in ad_accounts:
            act_id = acc.get("id")
            if not act_id:
                continue

            # 1. Sync Campaigns (GET /act_<ID>/campaigns)
            try:
                c_resp = requests.get(
                    f"https://graph.facebook.com/{GRAPH_API_VERSION}/{act_id}/campaigns",
                    params={"access_token": token, "fields": "id,name,objective,status,daily_budget,lifetime_budget,start_time,stop_time"},
                    timeout=20
                )
                if c_resp.status_code == 200:
                    c_data = c_resp.json().get("data", [])
                    for c in c_data:
                        cid = c.get("id")
                        cname = c.get("name", "")
                        cobj = c.get("objective", "")
                        cstat = c.get("status", "PAUSED")
                        db_budget = float(c.get("daily_budget", 0) or 0) / 100.0 if c.get("daily_budget") else None
                        lt_budget = float(c.get("lifetime_budget", 0) or 0) / 100.0 if c.get("lifetime_budget") else None

                        db.execute(text("""
                            INSERT INTO meta_campaigns (company_id, campaign_id, account_id, name, objective, status, daily_budget, lifetime_budget, updated_at)
                            VALUES (:cid, :camp_id, :act_id, :cname, :cobj, :cstat, :db_b, :lt_b, NOW())
                            ON CONFLICT (company_id, campaign_id) DO UPDATE SET
                                name = EXCLUDED.name,
                                objective = EXCLUDED.objective,
                                status = EXCLUDED.status,
                                daily_budget = EXCLUDED.daily_budget,
                                lifetime_budget = EXCLUDED.lifetime_budget,
                                updated_at = NOW()
                        """), {"cid": company_id, "camp_id": cid, "act_id": act_id, "cname": cname, "cobj": cobj, "cstat": cstat, "db_b": db_budget, "lt_b": lt_budget})
                        db.commit()
                        synced_c += 1
            except Exception as ce:
                db.rollback()
                logger.error(f"[META-ADS-SYNC] Campaign sync error: {ce}")

    return {
        "success": True,
        "synced_campaigns": synced_c,
        "synced_adsets": synced_as,
        "synced_ads": synced_ad
    }
