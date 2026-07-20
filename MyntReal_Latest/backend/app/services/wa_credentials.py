"""
[DC-WA-CREDS] WhatsApp Credential Helper
Reads from whatsapp_api_config DB table first, falls back to environment variables.
This allows credentials to be updated at runtime via the admin UI without redeployment.
"""
import os
import logging
from typing import Optional, Dict

logger = logging.getLogger(__name__)

_TABLE = "whatsapp_api_config"


def get_wa_credentials(db) -> Dict[str, str]:
    """
    Return WhatsApp API credentials.
    Priority: DB table → env vars → empty string.
    """
    try:
        from sqlalchemy import text as _t
        row = db.execute(_t(f"SELECT access_token, phone_number_id, verify_token, business_account_id, facebook_app_id FROM {_TABLE} ORDER BY id DESC LIMIT 1")).fetchone()
        if row and row[0]:
            return {
                "access_token":        row[0] or "",
                "phone_number_id":     row[1] or os.environ.get("META_WHATSAPP_PHONE_NUMBER_ID", ""),
                "verify_token":        row[2] or os.environ.get("META_WHATSAPP_VERIFY_TOKEN", ""),
                "business_account_id": row[3] or os.environ.get("META_WHATSAPP_BUSINESS_ACCOUNT_ID", ""),
                "facebook_app_id":     row[4] or os.environ.get("META_FACEBOOK_APP_ID", ""),
            }
    except Exception as e:
        logger.warning(f"[DC-WA-CREDS] Could not read from DB: {e}")

    return {
        "access_token":        os.environ.get("META_WHATSAPP_ACCESS_TOKEN", ""),
        "phone_number_id":     os.environ.get("META_WHATSAPP_PHONE_NUMBER_ID", ""),
        "verify_token":        os.environ.get("META_WHATSAPP_VERIFY_TOKEN", ""),
        "business_account_id": os.environ.get("META_WHATSAPP_BUSINESS_ACCOUNT_ID", ""),
        "facebook_app_id":     os.environ.get("META_FACEBOOK_APP_ID", ""),
    }
