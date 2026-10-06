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


def get_wa_credentials(db, company_id: Optional[int] = None) -> Dict[str, str]:
    """
    Return WhatsApp API credentials for a specific tenant company.
    If company_id credentials are not configured in whatsapp_api_config,
    fallback to Direct Meta WhatsApp credentials (Madhava Meta configuration).
    """
    default_creds = {
        "access_token":        os.environ.get("META_WHATSAPP_ACCESS_TOKEN", "").strip(),
        "phone_number_id":     os.environ.get("META_WHATSAPP_PHONE_NUMBER_ID", "").strip(),
        "verify_token":        os.environ.get("META_WHATSAPP_VERIFY_TOKEN", "").strip(),
        "business_account_id": os.environ.get("META_WHATSAPP_BUSINESS_ACCOUNT_ID", "").strip(),
        "facebook_app_id":     os.environ.get("META_APP_ID", os.environ.get("FACEBOOK_APP_ID", "")).strip(),
    }
    
    if db is None:
        return default_creds
        
    try:
        from sqlalchemy import text as _t
        from app.core.security_encryption import decrypt_credential_safe
        
        row = None
        if company_id is not None:
            row = db.execute(
                _t(f"SELECT access_token, phone_number_id, verify_token, business_account_id, facebook_app_id FROM {_TABLE} WHERE company_id = :cid ORDER BY id DESC LIMIT 1"),
                {"cid": company_id}
            ).fetchone()
        
        if not row:
            # Fallback to general table row or active default config
            row = db.execute(_t(f"SELECT access_token, phone_number_id, verify_token, business_account_id, facebook_app_id FROM {_TABLE} ORDER BY id DESC LIMIT 1")).fetchone()
            
        if row and row[0]:
            token = decrypt_credential_safe(row[0] or "")
            if token and row[1]:
                return {
                    "access_token":        token,
                    "phone_number_id":     row[1] or "",
                    "verify_token":        row[2] or "",
                    "business_account_id": row[3] or "",
                    "facebook_app_id":     row[4] or "",
                }
    except Exception as e:
        logger.warning(f"[DC-WA-CREDS] Could not read from DB, using default Direct Meta WhatsApp creds: {e}")

    return default_creds


def resolve_company_id_by_phone_number_id(db, phone_number_id: str) -> Optional[int]:
    """
    Resolve the owning tenant company_id for an inbound WhatsApp message via its phone_number_id.
    """
    if not phone_number_id:
        return None
    try:
        from sqlalchemy import text as _t
        row = db.execute(
            _t(f"SELECT company_id FROM {_TABLE} WHERE phone_number_id = :pid ORDER BY id DESC LIMIT 1"),
            {"pid": str(phone_number_id)}
        ).fetchone()
        if row and row[0]:
            return int(row[0])
    except Exception as e:
        logger.warning(f"[DC-WA-CREDS] Phone ID company lookup failed: {e}")
    return None
