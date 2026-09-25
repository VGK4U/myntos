"""
Runtime Credential Resolver — MyntOS Central Integration Framework
Resolves: Current Tenant → Active / Default Connection → Decrypted Credentials
With graceful fallback to Platform-level connection and legacy environment variables.
Created: September 2026
"""

from typing import Dict, Any, Optional, Tuple
import os
import json
import logging
from sqlalchemy.orm import Session

from app.models.integration_framework import IntegrationConnection, IntegrationDefinition
from app.core.security_encryption import decrypt_credential_safe
from app.core.config import settings

logger = logging.getLogger(__name__)


def resolve_integration_credentials(
    db: Session,
    tenant_id: Optional[int],
    integration_code: str,
    account_id: Optional[str] = None
) -> Tuple[Dict[str, Any], Dict[str, Any], Optional[IntegrationConnection]]:
    """
    Standard resolution pipeline:
    1. Query IntegrationConnection for specific tenant_id and integration_code.
       - Prioritize is_default=True if multiple exist.
       - Match account_id if specified.
    2. If found and active:
       - Decrypt credentials using AES-256-GCM (app.core.security_encryption).
       - Return (decrypted_creds, public_config, connection)
    3. If not found or tenant has no custom connection:
       - Check if integration supports_platform_connection.
       - If yes, query platform connection (tenant_id = 1 or scope = 'platform').
    4. If still not found:
       - Fallback to environment variables / settings (zero-regression guarantee).
    """
    conn = None

    # Step 1: Query tenant connection
    if tenant_id:
        q = db.query(IntegrationConnection).filter(
            IntegrationConnection.tenant_id == tenant_id,
            IntegrationConnection.integration_code == integration_code,
            IntegrationConnection.is_active == True
        )
        if account_id:
            conn = q.filter(
                (IntegrationConnection.provider_account_id == str(account_id)) |
                (IntegrationConnection.id == int(account_id) if str(account_id).isdigit() else False)
            ).first()
        else:
            conn = q.order_by(IntegrationConnection.is_default.desc(), IntegrationConnection.id.asc()).first()

    # Step 2: Fallback to Platform Connection (tenant_id = 1 or scope = 'platform')
    if not conn:
        idef = db.query(IntegrationDefinition).filter_by(integration_code=integration_code).first()
        if not idef or idef.supports_platform_connection:
            q_plat = db.query(IntegrationConnection).filter(
                IntegrationConnection.integration_code == integration_code,
                IntegrationConnection.is_active == True,
                (IntegrationConnection.tenant_id == 1) | (IntegrationConnection.scope == 'platform')
            )
            if account_id:
                conn = q_plat.filter(
                    (IntegrationConnection.provider_account_id == str(account_id)) |
                    (IntegrationConnection.id == int(account_id) if str(account_id).isdigit() else False)
                ).first()
            else:
                conn = q_plat.order_by(IntegrationConnection.is_default.desc(), IntegrationConnection.id.asc()).first()

    # Step 3: Decrypt if connection found
    if conn and conn.encrypted_credentials:
        try:
            raw_json = decrypt_credential_safe(conn.encrypted_credentials)
            creds = json.loads(raw_json) if raw_json else {}
            pub = conn.public_configuration or {}
            return creds, pub, conn
        except Exception as e:
            logger.error(f"[INTEGRATION-RESOLVER] Failed to decrypt credentials for {integration_code} (conn_id={conn.id}): {e}")

    # Step 4: Legacy Environment Fallback (guarantees existing services never break)
    fallback_creds = _resolve_env_fallback(integration_code)
    return fallback_creds, {}, conn


def _resolve_env_fallback(integration_code: str) -> Dict[str, Any]:
    """Provides backward-compatible fallback directly from environment variables."""
    if integration_code == "plivo":
        return {
            "auth_id": os.getenv("PLIVO_AUTH_ID") or getattr(settings, "PLIVO_AUTH_ID", None),
            "auth_token": os.getenv("PLIVO_AUTH_TOKEN") or getattr(settings, "PLIVO_AUTH_TOKEN", None),
            "app_id": os.getenv("PLIVO_APP_ID", "10583407997011554"),
            "default_caller_id": os.getenv("PLIVO_DEFAULT_CALLER_ID", "+918031728899")
        }
    elif integration_code == "twilio":
        return {
            "account_sid": os.getenv("TWILIO_SID", ""),
            "auth_token": os.getenv("TWILIO_AUTH_TOKEN", ""),
            "phone_number": os.getenv("TWILIO_PHONE_NUMBER", "")
        }
    elif integration_code == "meta_whatsapp":
        return {
            "access_token": os.getenv("META_WHATSAPP_ACCESS_TOKEN") or os.getenv("META_ACCESS_TOKEN", ""),
            "phone_number_id": os.getenv("META_WHATSAPP_PHONE_NUMBER_ID", ""),
            "verify_token": os.getenv("META_WHATSAPP_VERIFY_TOKEN", "vgk4u_webhook")
        }
    elif integration_code == "gemini":
        return {
            "api_key": os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or getattr(settings, "GEMINI_API_KEY", "")
        }
    elif integration_code == "openai":
        return {
            "api_key": os.getenv("OPENAI_API_KEY") or getattr(settings, "OPENAI_API_KEY", "")
        }
    elif integration_code == "sarvam":
        return {
            "api_key": os.getenv("SARVAM_API_KEY") or getattr(settings, "SARVAM_API_KEY", "")
        }
    elif integration_code == "razorpay":
        return {
            "key_id": os.getenv("RAZORPAY_KEY_ID") or getattr(settings, "RAZORPAY_KEY_ID", ""),
            "key_secret": os.getenv("RAZORPAY_KEY_SECRET") or getattr(settings, "RAZORPAY_KEY_SECRET", ""),
            "webhook_secret": os.getenv("RAZORPAY_WEBHOOK_SECRET") or getattr(settings, "RAZORPAY_WEBHOOK_SECRET", "")
        }
    elif integration_code == "aws_s3":
        return {
            "access_key_id": os.getenv("AWS_ACCESS_KEY_ID", ""),
            "secret_access_key": os.getenv("AWS_SECRET_ACCESS_KEY", ""),
            "bucket_name": os.getenv("AWS_S3_BUCKET_NAME", "myntreal-media-vault"),
            "region": os.getenv("AWS_REGION", "ap-south-2")
        }
    return {}
