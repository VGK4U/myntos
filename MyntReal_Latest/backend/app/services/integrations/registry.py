"""
Integration Registry & Seed Engine — MyntOS Central Integration Management
Declares the dynamic categories, provider definitions, and configuration schemas.
Seeds initial registry data and default platform connections idempotently.
Created: September 2026
"""

from typing import List, Dict, Any, Optional
import os
import json
import logging
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.models.integration_framework import (
    IntegrationCategory, IntegrationDefinition, IntegrationConnection, IntegrationAuditLog
)
from app.models.platform_b2b import PlatformClient
from app.core.security_encryption import encrypt_credential, decrypt_credential_safe
from app.services.integrations.adapters import get_adapter_for_integration

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# REGISTRY CANONICAL DEFINITIONS
# ─────────────────────────────────────────────────────────────────────────────
DEFAULT_CATEGORIES = [
    {
        "category_code": "telephony",
        "display_name": "Communication & Telephony",
        "description": "Voice calling, WebRTC softphone, cloud PBX, and PSTN trunking providers.",
        "icon": "fas fa-phone-alt",
        "display_order": 1
    },
    {
        "category_code": "messaging",
        "display_name": "Messaging & Chat",
        "description": "WhatsApp Business API, customer notifications, and team chat webhooks.",
        "icon": "fab fa-whatsapp",
        "display_order": 2
    },
    {
        "category_code": "marketing",
        "display_name": "Marketing & Advertising",
        "description": "Social media ad accounts, Facebook/Instagram campaigns, and lead capture forms.",
        "icon": "fab fa-meta",
        "display_order": 3
    },
    {
        "category_code": "ai",
        "display_name": "AI & Voice Intelligence",
        "description": "Large Language Models, speech-to-text, streaming TTS, and conversational agents.",
        "icon": "fas fa-brain",
        "display_order": 4
    },
    {
        "category_code": "productivity",
        "display_name": "Productivity & CRM Sync",
        "description": "Spreadsheet lead sync, Google Workspace, and office workflows.",
        "icon": "fas fa-table",
        "display_order": 5
    },
    {
        "category_code": "payments",
        "display_name": "Payments & Billing",
        "description": "Payment gateways, SaaS subscription invoicing, and recharge utilities.",
        "icon": "fas fa-credit-card",
        "display_order": 6
    },
    {
        "category_code": "infrastructure",
        "display_name": "Cloud & Push Infrastructure",
        "description": "AWS S3 media vaults and Apple/Firebase mobile push signaling.",
        "icon": "fas fa-cloud",
        "display_order": 7
    }
]

DEFAULT_DEFINITIONS = [
    # ── 1. Plivo ──
    {
        "integration_code": "plivo",
        "category_code": "telephony",
        "display_name": "Plivo Cloud Telephony",
        "provider_name": "Plivo Inc.",
        "description": "Browser WebRTC softphone token issuance, outbound dialing, inbound IVR, and session recording.",
        "icon": "fas fa-phone-volume",
        "auth_type": "account_token",
        "supports_platform_connection": True,
        "supports_tenant_connection": True,
        "supports_multiple_connections": True,
        "supports_oauth": False,
        "supports_webhooks": True,
        "supports_connection_test": True,
        "adapter_class": "PlivoAdapter",
        "display_order": 1,
        "configuration_schema": [
            {"key": "auth_id", "label": "Plivo Auth ID", "type": "string", "required": True, "is_secret": False, "placeholder": "MAMTLIY2...", "description": "Found on your Plivo console overview page."},
            {"key": "auth_token", "label": "Plivo Auth Token", "type": "string", "required": True, "is_secret": True, "placeholder": "Enter secret auth token", "description": "Master REST authentication token."},
            {"key": "app_id", "label": "Plivo XML Application ID", "type": "string", "required": False, "is_secret": False, "placeholder": "1058340...", "description": "XML Application ID configured with MyntOS answer/hangup URLs."},
            {"key": "default_caller_id", "label": "Outbound Caller ID (DID)", "type": "string", "required": True, "is_secret": False, "placeholder": "+918031728899", "description": "E.164 caller phone number to present to dial recipients."}
        ]
    },
    # ── 2. Twilio ──
    {
        "integration_code": "twilio",
        "category_code": "telephony",
        "display_name": "Twilio Voice & SMS",
        "provider_name": "Twilio Inc.",
        "description": "Secondary automated outbound AI voice calling and carrier delivery.",
        "icon": "fas fa-satellite-dish",
        "auth_type": "account_token",
        "supports_platform_connection": True,
        "supports_tenant_connection": True,
        "supports_multiple_connections": True,
        "supports_oauth": False,
        "supports_webhooks": True,
        "supports_connection_test": True,
        "adapter_class": "TwilioAdapter",
        "display_order": 2,
        "configuration_schema": [
            {"key": "account_sid", "label": "Account SID", "type": "string", "required": True, "is_secret": False, "placeholder": "ACxxxxxxxx...", "description": "Twilio Master Account SID."},
            {"key": "auth_token", "label": "Auth Token", "type": "string", "required": True, "is_secret": True, "placeholder": "Enter Twilio auth token", "description": "Twilio primary authentication token."},
            {"key": "phone_number", "label": "Twilio Phone Number", "type": "string", "required": False, "is_secret": False, "placeholder": "+1234567890", "description": "Twilio purchased phone number."}
        ]
    },
    # ── 3. MyOperator ──
    {
        "integration_code": "myoperator",
        "category_code": "telephony",
        "display_name": "MyOperator Cloud PBX",
        "provider_name": "VoiceTree Technologies",
        "description": "Virtual business numbers, missed-call auto capture, and OBD 2-leg telephony bridge.",
        "icon": "fas fa-headset",
        "auth_type": "api_key",
        "supports_platform_connection": True,
        "supports_tenant_connection": True,
        "supports_multiple_connections": False,
        "supports_oauth": False,
        "supports_webhooks": True,
        "supports_connection_test": True,
        "adapter_class": "MyOperatorAdapter",
        "display_order": 3,
        "configuration_schema": [
            {"key": "api_token", "label": "Developer API Token", "type": "string", "required": True, "is_secret": True, "placeholder": "Enter MyOperator API token", "description": "Permanent token for log searching and user sync."},
            {"key": "x_api_key", "label": "X-API-KEY", "type": "string", "required": False, "is_secret": True, "placeholder": "Enter X-API-KEY", "description": "Required for outbound OBD bridge calls."},
            {"key": "company_id", "label": "MyOperator Company ID", "type": "string", "required": False, "is_secret": False, "placeholder": "1", "description": "Numeric company ID in MyOperator portal."}
        ]
    },
    # ── 4. Meta WhatsApp Cloud API ──
    {
        "integration_code": "meta_whatsapp",
        "category_code": "messaging",
        "display_name": "Meta WhatsApp Cloud API",
        "provider_name": "Meta Platforms Inc.",
        "description": "Official Meta Graph API v21.0+ for template notifications, interactive buttons, and CRM conversations.",
        "icon": "fab fa-whatsapp",
        "auth_type": "api_key",
        "supports_platform_connection": True,
        "supports_tenant_connection": True,
        "supports_multiple_connections": True,
        "supports_oauth": False,
        "supports_webhooks": True,
        "supports_connection_test": True,
        "adapter_class": "MetaWhatsAppAdapter",
        "display_order": 1,
        "configuration_schema": [
            {"key": "access_token", "label": "Permanent Access Token", "type": "string", "required": True, "is_secret": True, "placeholder": "EAAX...", "description": "System User Token with whatsapp_business_messaging & management permissions."},
            {"key": "phone_number_id", "label": "Phone Number ID", "type": "string", "required": True, "is_secret": False, "placeholder": "1000...", "description": "15-digit ID from WhatsApp App Manager."},
            {"key": "business_account_id", "label": "WABA ID (Business Account ID)", "type": "string", "required": False, "is_secret": False, "placeholder": "2000...", "description": "WhatsApp Business Account ID."},
            {"key": "verify_token", "label": "Webhook Verify Token", "type": "string", "required": False, "is_secret": False, "default": "vgk4u_webhook", "description": "Custom secret string entered in Meta Webhook config."},
            {"key": "facebook_app_id", "label": "Meta App ID", "type": "string", "required": False, "is_secret": False, "placeholder": "3000...", "description": "Meta App ID for resumable media uploads."}
        ]
    },
    # ── 5. Baileys WhatsApp Gateway ──
    {
        "integration_code": "baileys_wa",
        "category_code": "messaging",
        "display_name": "Baileys WhatsApp Bot Gateway",
        "provider_name": "WhiskeySockets / Baileys",
        "description": "Headless web-socket bot gateway for automated dispatches into internal sales groups.",
        "icon": "fas fa-robot",
        "auth_type": "session_scan",
        "supports_platform_connection": True,
        "supports_tenant_connection": False,
        "supports_multiple_connections": False,
        "supports_oauth": False,
        "supports_webhooks": False,
        "supports_connection_test": True,
        "adapter_class": "BaileysWAAdapter",
        "display_order": 2,
        "configuration_schema": [
            {"key": "service_url", "label": "Local Gateway URL", "type": "string", "required": True, "is_secret": False, "default": "http://127.0.0.1:5002", "description": "Local supervisor daemon endpoint on port 5002."},
            {"key": "session_id", "label": "Session Name", "type": "string", "required": False, "is_secret": False, "default": "dev_baileys", "description": "Multi-file auth state identifier."}
        ]
    },
    # ── 6. Meta Ads & Lead Ads ──
    {
        "integration_code": "meta_ads",
        "category_code": "marketing",
        "display_name": "Meta Ads & Lead Ads Center",
        "provider_name": "Meta Platforms Inc.",
        "description": "Facebook/Instagram Marketing API, Ad Accounts, instant lead form webhooks, and CAPI.",
        "icon": "fab fa-facebook",
        "auth_type": "oauth2",
        "supports_platform_connection": True,
        "supports_tenant_connection": True,
        "supports_multiple_connections": True,
        "supports_oauth": True,
        "supports_webhooks": True,
        "supports_connection_test": True,
        "adapter_class": "MetaAdsAdapter",
        "display_order": 1,
        "configuration_schema": [
            {"key": "access_token", "label": "User / Page Access Token", "type": "string", "required": True, "is_secret": True, "placeholder": "EAAX...", "description": "Long-lived access token with ads_read & leads_retrieval permissions."},
            {"key": "ad_account_id", "label": "Target Ad Account ID", "type": "string", "required": True, "is_secret": False, "placeholder": "560062103113819", "description": "Numeric Meta Ad Account ID (without act_ prefix)."},
            {"key": "app_id", "label": "Meta App ID", "type": "string", "required": False, "is_secret": False, "placeholder": "123456...", "description": "Meta developer App ID."},
            {"key": "app_secret", "label": "Meta App Secret", "type": "string", "required": False, "is_secret": True, "placeholder": "Enter app secret", "description": "Used for server-side token renewal."}
        ]
    },
    # ── 7. Google Gemini AI ──
    {
        "integration_code": "gemini",
        "category_code": "ai",
        "display_name": "Google Gemini AI",
        "provider_name": "Google LLC",
        "description": "Primary dialogue generation, prompt reasoning, speech processing, and multi-key pooling.",
        "icon": "fas fa-sparkles",
        "auth_type": "api_key",
        "supports_platform_connection": True,
        "supports_tenant_connection": True,
        "supports_multiple_connections": True,
        "supports_oauth": False,
        "supports_webhooks": False,
        "supports_connection_test": True,
        "adapter_class": "GeminiAdapter",
        "display_order": 1,
        "configuration_schema": [
            {"key": "api_key", "label": "Google Gemini API Key", "type": "string", "required": True, "is_secret": True, "placeholder": "AIzaSy...", "description": "API Key from Google AI Studio / Cloud Console."},
            {"key": "model", "label": "Default Model", "type": "select", "required": False, "is_secret": False, "default": "gemini-2.0-flash", "options": ["gemini-2.0-flash", "gemini-1.5-flash", "gemini-1.5-pro"], "description": "Default generative model."}
        ]
    },
    # ── 8. OpenAI ──
    {
        "integration_code": "openai",
        "category_code": "ai",
        "display_name": "OpenAI (GPT-4o & TTS)",
        "provider_name": "OpenAI LLC",
        "description": "Fallback conversation logic and tts-1 natural voice synthesis.",
        "icon": "fas fa-microchip",
        "auth_type": "api_key",
        "supports_platform_connection": True,
        "supports_tenant_connection": True,
        "supports_multiple_connections": True,
        "supports_oauth": False,
        "supports_webhooks": False,
        "supports_connection_test": True,
        "adapter_class": "OpenAIAdapter",
        "display_order": 2,
        "configuration_schema": [
            {"key": "api_key", "label": "OpenAI API Key", "type": "string", "required": True, "is_secret": True, "placeholder": "sk-proj-...", "description": "Secret key from OpenAI dashboard."},
            {"key": "model", "label": "Default Model", "type": "select", "required": False, "is_secret": False, "default": "gpt-4o", "options": ["gpt-4o", "gpt-4o-mini", "gpt-3.5-turbo"], "description": "Default chat model."}
        ]
    },
    # ── 9. Sarvam AI ──
    {
        "integration_code": "sarvam",
        "category_code": "ai",
        "display_name": "Sarvam AI (Indian Languages)",
        "provider_name": "Sarvam AI",
        "description": "Real-time speech-to-text (Saaras) and low-latency streaming TTS (Bulbul) for regional Indian languages.",
        "icon": "fas fa-language",
        "auth_type": "api_key",
        "supports_platform_connection": True,
        "supports_tenant_connection": True,
        "supports_multiple_connections": False,
        "supports_oauth": False,
        "supports_webhooks": False,
        "supports_connection_test": True,
        "adapter_class": "SarvamAdapter",
        "display_order": 3,
        "configuration_schema": [
            {"key": "api_key", "label": "Sarvam API Key", "type": "string", "required": True, "is_secret": True, "placeholder": "Enter Sarvam key", "description": "Sarvam AI subscription key."}
        ]
    },
    # ── 10. Google Sheets Lead Sync ──
    {
        "integration_code": "google_sheets",
        "category_code": "productivity",
        "display_name": "Google Sheets Lead Sync",
        "provider_name": "Google LLC",
        "description": "Automated recurring ingestion of prospective leads from Google Spreadsheets directly into CRM.",
        "icon": "fas fa-file-excel",
        "auth_type": "public_url",
        "supports_platform_connection": True,
        "supports_tenant_connection": True,
        "supports_multiple_connections": True,
        "supports_oauth": False,
        "supports_webhooks": False,
        "supports_connection_test": True,
        "adapter_class": "GoogleSheetsAdapter",
        "display_order": 1,
        "configuration_schema": [
            {"key": "sheet_url", "label": "Google Spreadsheet URL", "type": "string", "required": True, "is_secret": False, "placeholder": "https://docs.google.com/spreadsheets/d/...", "description": "Link with 'Anyone with the link can view' permission."},
            {"key": "sync_schedule", "label": "Sync Schedule", "type": "string", "required": False, "is_secret": False, "default": "9am, 12pm, 3pm, 6pm", "description": "Automated sync times."}
        ]
    },
    # ── 11. Razorpay ──
    {
        "integration_code": "razorpay",
        "category_code": "payments",
        "display_name": "Razorpay Payment Gateway",
        "provider_name": "Razorpay Software",
        "description": "B2B SaaS subscription invoices, checkout orders, and utility recharges.",
        "icon": "fas fa-receipt",
        "auth_type": "api_key",
        "supports_platform_connection": True,
        "supports_tenant_connection": True,
        "supports_multiple_connections": True,
        "supports_oauth": False,
        "supports_webhooks": True,
        "supports_connection_test": True,
        "adapter_class": "RazorpayAdapter",
        "display_order": 1,
        "configuration_schema": [
            {"key": "key_id", "label": "Razorpay Key ID", "type": "string", "required": True, "is_secret": False, "placeholder": "rzp_live_...", "description": "Public Key ID."},
            {"key": "key_secret", "label": "Razorpay Key Secret", "type": "string", "required": True, "is_secret": True, "placeholder": "Enter key secret", "description": "Private Key Secret."},
            {"key": "webhook_secret", "label": "Webhook Secret", "type": "string", "required": False, "is_secret": True, "placeholder": "Enter webhook secret", "description": "Validates X-Razorpay-Signature."}
        ]
    },
    # ── 12. A1Topup ──
    {
        "integration_code": "a1topup",
        "category_code": "payments",
        "display_name": "A1Topup Recharge Gateway",
        "provider_name": "A1Topup Services",
        "description": "Multi-operator mobile balance, DTH, and electricity bill payments.",
        "icon": "fas fa-bolt",
        "auth_type": "api_key",
        "supports_platform_connection": True,
        "supports_tenant_connection": False,
        "supports_multiple_connections": False,
        "supports_oauth": False,
        "supports_webhooks": False,
        "supports_connection_test": True,
        "adapter_class": "A1TopupAdapter",
        "display_order": 2,
        "configuration_schema": [
            {"key": "username", "label": "A1Topup Username", "type": "string", "required": True, "is_secret": False, "placeholder": "Enter username"},
            {"key": "password", "label": "A1Topup Password", "type": "string", "required": True, "is_secret": True, "placeholder": "Enter password"},
            {"key": "test_mode", "label": "Test Mode Enabled", "type": "boolean", "required": False, "is_secret": False, "default": True}
        ]
    },
    # ── 13. AWS S3 ──
    {
        "integration_code": "aws_s3",
        "category_code": "infrastructure",
        "display_name": "Amazon Web Services (S3)",
        "provider_name": "Amazon Web Services",
        "description": "Cloud object storage for media vault, invoices, documents, and call audio recordings.",
        "icon": "fab fa-aws",
        "auth_type": "storage_keys",
        "supports_platform_connection": True,
        "supports_tenant_connection": True,
        "supports_multiple_connections": False,
        "supports_oauth": False,
        "supports_webhooks": False,
        "supports_connection_test": True,
        "adapter_class": "AWSS3Adapter",
        "display_order": 1,
        "configuration_schema": [
            {"key": "access_key_id", "label": "AWS Access Key ID", "type": "string", "required": True, "is_secret": False, "placeholder": "AKIA..."},
            {"key": "secret_access_key", "label": "AWS Secret Access Key", "type": "string", "required": True, "is_secret": True, "placeholder": "Enter AWS secret key"},
            {"key": "bucket_name", "label": "S3 Bucket Name", "type": "string", "required": True, "is_secret": False, "default": "myntreal-media-vault"},
            {"key": "region", "label": "AWS Region", "type": "string", "required": True, "is_secret": False, "default": "ap-south-2"}
        ]
    },
    # ── 14. Firebase FCM & Apple APNs ──
    {
        "integration_code": "fcm_apns",
        "category_code": "infrastructure",
        "display_name": "Firebase (FCM) & Apple APNs",
        "provider_name": "Google LLC / Apple Inc.",
        "description": "High-priority background VoIP push signaling to ring Android and iOS devices on screen-off incoming calls.",
        "icon": "fas fa-bell",
        "auth_type": "service_account",
        "supports_platform_connection": True,
        "supports_tenant_connection": False,
        "supports_multiple_connections": False,
        "supports_oauth": False,
        "supports_webhooks": False,
        "supports_connection_test": True,
        "adapter_class": "FCMAPNsAdapter",
        "display_order": 2,
        "configuration_schema": [
            {"key": "project_id", "label": "Firebase Project ID", "type": "string", "required": True, "is_secret": False, "default": "myntrealosg"},
            {"key": "service_account_json", "label": "Service Account JSON", "type": "textarea", "required": False, "is_secret": True, "placeholder": "{\n  \"type\": \"service_account\", ...\n}"}
        ]
    }
]


# ─────────────────────────────────────────────────────────────────────────────
# REGISTRY SEED & QUERY FUNCTIONS
# ─────────────────────────────────────────────────────────────────────────────
def seed_default_registry(db: Session) -> Dict[str, int]:
    """
    Populates integration_categories and integration_definitions from declarative metadata.
    Idempotent upsert pattern.
    """
    cat_count = 0
    def_count = 0

    # 1. Upsert categories
    for cat in DEFAULT_CATEGORIES:
        existing = db.query(IntegrationCategory).filter_by(category_code=cat["category_code"]).first()
        if not existing:
            row = IntegrationCategory(
                category_code=cat["category_code"],
                display_name=cat["display_name"],
                description=cat.get("description"),
                icon=cat.get("icon", "fas fa-plug"),
                display_order=cat.get("display_order", 10),
                is_active=True
            )
            db.add(row)
            cat_count += 1
        else:
            existing.display_name = cat["display_name"]
            existing.description = cat.get("description")
            existing.icon = cat.get("icon", existing.icon)
            existing.display_order = cat.get("display_order", existing.display_order)

    db.commit()

    # 2. Upsert definitions
    for idef in DEFAULT_DEFINITIONS:
        existing = db.query(IntegrationDefinition).filter_by(integration_code=idef["integration_code"]).first()
        if not existing:
            row = IntegrationDefinition(
                integration_code=idef["integration_code"],
                category_code=idef["category_code"],
                display_name=idef["display_name"],
                provider_name=idef["provider_name"],
                description=idef.get("description"),
                icon=idef.get("icon", "fas fa-cube"),
                auth_type=idef.get("auth_type", "api_key"),
                supports_platform_connection=idef.get("supports_platform_connection", True),
                supports_tenant_connection=idef.get("supports_tenant_connection", True),
                supports_multiple_connections=idef.get("supports_multiple_connections", False),
                supports_oauth=idef.get("supports_oauth", False),
                supports_webhooks=idef.get("supports_webhooks", False),
                supports_connection_test=idef.get("supports_connection_test", True),
                supports_enable_disable=idef.get("supports_enable_disable", True),
                configuration_schema=idef.get("configuration_schema", []),
                status_rules=idef.get("status_rules", {}),
                adapter_class=idef.get("adapter_class"),
                display_order=idef.get("display_order", 10),
                is_active=True
            )
            db.add(row)
            def_count += 1
        else:
            existing.display_name = idef["display_name"]
            existing.provider_name = idef["provider_name"]
            existing.description = idef.get("description")
            existing.icon = idef.get("icon", existing.icon)
            existing.auth_type = idef.get("auth_type", existing.auth_type)
            existing.supports_platform_connection = idef.get("supports_platform_connection", existing.supports_platform_connection)
            existing.supports_tenant_connection = idef.get("supports_tenant_connection", existing.supports_tenant_connection)
            existing.supports_multiple_connections = idef.get("supports_multiple_connections", existing.supports_multiple_connections)
            existing.supports_oauth = idef.get("supports_oauth", existing.supports_oauth)
            existing.supports_webhooks = idef.get("supports_webhooks", existing.supports_webhooks)
            existing.configuration_schema = idef.get("configuration_schema", existing.configuration_schema)
            existing.adapter_class = idef.get("adapter_class", existing.adapter_class)
            existing.display_order = idef.get("display_order", existing.display_order)

    db.commit()

    # 3. Seed default platform connections from environment variables if not present
    seed_platform_connections_from_env(db)

    return {"categories_upserted": cat_count, "definitions_upserted": def_count}


def seed_platform_connections_from_env(db: Session):
    """
    Reads existing environment variables and creates default platform connections (tenant_id = 1)
    so existing operations continue working seamlessly without requiring manual re-entry.
    """
    # 1. Plivo
    p_auth = os.getenv("PLIVO_AUTH_ID")
    p_tok = os.getenv("PLIVO_AUTH_TOKEN")
    if p_auth and p_tok:
        _upsert_seed_connection(
            db=db,
            tenant_id=1,
            integration_code="plivo",
            conn_name="MyntOS Default Carrier (Plivo)",
            scope="platform",
            auth_type="account_token",
            creds={"auth_id": p_auth, "auth_token": p_tok},
            public_cfg={
                "auth_id": p_auth,
                "app_id": os.getenv("PLIVO_APP_ID", "10583407997011554"),
                "default_caller_id": os.getenv("PLIVO_DEFAULT_CALLER_ID", "+918031728899")
            },
            account_id=p_auth
        )

    # 2. Twilio
    t_sid = os.getenv("TWILIO_SID")
    t_tok = os.getenv("TWILIO_AUTH_TOKEN")
    if t_sid and t_tok:
        _upsert_seed_connection(
            db=db,
            tenant_id=1,
            integration_code="twilio",
            conn_name="Twilio Outbound Fallback",
            scope="platform",
            auth_type="account_token",
            creds={"account_sid": t_sid, "auth_token": t_tok},
            public_cfg={"account_sid": t_sid, "phone_number": os.getenv("TWILIO_PHONE_NUMBER", "")},
            account_id=t_sid
        )

    # 3. Meta WhatsApp
    wa_tok = os.getenv("META_WHATSAPP_ACCESS_TOKEN") or os.getenv("META_ACCESS_TOKEN")
    wa_pid = os.getenv("META_WHATSAPP_PHONE_NUMBER_ID")
    if wa_tok and wa_pid:
        _upsert_seed_connection(
            db=db,
            tenant_id=1,
            integration_code="meta_whatsapp",
            conn_name="Meta WhatsApp Cloud API (Primary)",
            scope="platform",
            auth_type="api_key",
            creds={"access_token": wa_tok},
            public_cfg={
                "phone_number_id": wa_pid,
                "business_account_id": os.getenv("META_WHATSAPP_BUSINESS_ACCOUNT_ID", ""),
                "verify_token": os.getenv("META_WHATSAPP_VERIFY_TOKEN", "vgk4u_webhook")
            },
            account_id=wa_pid
        )

    # 4. Meta Ads
    meta_tok = os.getenv("META_ACCESS_TOKEN")
    if meta_tok:
        _upsert_seed_connection(
            db=db,
            tenant_id=1,
            integration_code="meta_ads",
            conn_name="Meta Marketing & Ad Account 560062103113819",
            scope="platform",
            auth_type="oauth2",
            creds={"access_token": meta_tok, "app_secret": os.getenv("FACEBOOK_APP_SECRET", "")},
            public_cfg={"ad_account_id": "560062103113819", "app_id": os.getenv("META_APP_ID", "")},
            account_id="560062103113819"
        )

    # 5. Gemini
    gem_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if gem_key:
        _upsert_seed_connection(
            db=db,
            tenant_id=1,
            integration_code="gemini",
            conn_name="Google Gemini 2.0 Flash (Platform)",
            scope="platform",
            auth_type="api_key",
            creds={"api_key": gem_key},
            public_cfg={"model": "gemini-2.0-flash"},
            account_id="gemini-default"
        )

    # 6. OpenAI
    oai_key = os.getenv("OPENAI_API_KEY")
    if oai_key:
        _upsert_seed_connection(
            db=db,
            tenant_id=1,
            integration_code="openai",
            conn_name="OpenAI GPT-4o & TTS (Fallback)",
            scope="platform",
            auth_type="api_key",
            creds={"api_key": oai_key},
            public_cfg={"model": "gpt-4o"},
            account_id="openai-default"
        )

    # 7. Sarvam AI
    sarvam_key = os.getenv("SARVAM_API_KEY")
    if sarvam_key:
        _upsert_seed_connection(
            db=db,
            tenant_id=1,
            integration_code="sarvam",
            conn_name="Sarvam AI Regional STT/TTS",
            scope="platform",
            auth_type="api_key",
            creds={"api_key": sarvam_key},
            public_cfg={},
            account_id="sarvam-default"
        )

    # 8. Razorpay
    rzp_key = os.getenv("RAZORPAY_KEY_ID")
    rzp_sec = os.getenv("RAZORPAY_KEY_SECRET")
    if rzp_key and rzp_sec:
        _upsert_seed_connection(
            db=db,
            tenant_id=1,
            integration_code="razorpay",
            conn_name="Razorpay Standard Gateway",
            scope="platform",
            auth_type="api_key",
            creds={"key_id": rzp_key, "key_secret": rzp_sec, "webhook_secret": os.getenv("RAZORPAY_WEBHOOK_SECRET", "")},
            public_cfg={"key_id": rzp_key},
            account_id=rzp_key
        )

    # 9. AWS S3
    aws_key = os.getenv("AWS_ACCESS_KEY_ID")
    aws_sec = os.getenv("AWS_SECRET_ACCESS_KEY")
    if aws_key and aws_sec:
        _upsert_seed_connection(
            db=db,
            tenant_id=1,
            integration_code="aws_s3",
            conn_name="AWS S3 Media Vault (ap-south-2)",
            scope="platform",
            auth_type="storage_keys",
            creds={"access_key_id": aws_key, "secret_access_key": aws_sec},
            public_cfg={
                "bucket_name": os.getenv("AWS_S3_BUCKET_NAME", "myntreal-media-vault"),
                "region": os.getenv("AWS_REGION", "ap-south-2")
            },
            account_id=os.getenv("AWS_S3_BUCKET_NAME", "myntreal-media-vault")
        )

    # 10. Baileys
    _upsert_seed_connection(
        db=db,
        tenant_id=1,
        integration_code="baileys_wa",
        conn_name="Baileys WhatsApp Bot (Port 5002)",
        scope="platform",
        auth_type="session_scan",
        creds={},
        public_cfg={"service_url": "http://127.0.0.1:5002", "session_id": "dev_baileys"},
        account_id="baileys-5002"
    )

    db.commit()


def _upsert_seed_connection(db, tenant_id, integration_code, conn_name, scope, auth_type, creds, public_cfg, account_id):
    """Helper to upsert a default connection safely with encrypted secrets."""
    conn = db.query(IntegrationConnection).filter_by(
        tenant_id=tenant_id,
        integration_code=integration_code
    ).first()

    enc_creds = encrypt_credential(json.dumps(creds)) if creds else ""

    if not conn:
        conn = IntegrationConnection(
            tenant_id=tenant_id,
            integration_code=integration_code,
            connection_name=conn_name,
            scope=scope,
            auth_type=auth_type,
            encrypted_credentials=enc_creds,
            public_configuration=public_cfg,
            provider_account_id=str(account_id) if account_id else None,
            status="ACTIVE",
            is_active=True,
            is_default=True,
            created_by="SYSTEM_SEED"
        )
        db.add(conn)
    else:
        # Keep existing custom values if already modified, but ensure default fields populated
        if not conn.encrypted_credentials and enc_creds:
            conn.encrypted_credentials = enc_creds
        if not conn.public_configuration and public_cfg:
            conn.public_configuration = public_cfg


def mask_connection_credentials(connection) -> Dict[str, Any]:
    """Helper function to mask connection credentials using the provider adapter."""
    adapter = get_adapter_for_integration(connection.integration_code)
    return adapter.get_masked_credentials(connection)


def get_master_matrix_data(db: Session, tenant_id: Optional[int] = None) -> Dict[str, Any]:
    """
    Computes the dynamic Master Integration Matrix.
    Rows: All clients (internal & external) or single client if tenant_id is specified.
    Columns: All registered Integration Definitions.
    Cells: Connection status summary (Active, Inactive, 2 Accounts, Not Configured, etc.)
    """
    client_q = db.query(PlatformClient)
    if tenant_id:
        client_q = client_q.filter(PlatformClient.id == tenant_id)
    clients = client_q.order_by(PlatformClient.is_internal.desc(), PlatformClient.client_name.asc()).all()
    definitions = db.query(IntegrationDefinition).filter_by(is_active=True).order_by(IntegrationDefinition.display_order.asc()).all()
    categories = db.query(IntegrationCategory).filter_by(is_active=True).order_by(IntegrationCategory.display_order.asc()).all()

    # Pre-fetch all active connections indexed by (tenant_id, integration_code)
    all_connections = db.query(IntegrationConnection).filter_by(is_active=True).all()
    conn_map: Dict[tuple, List[IntegrationConnection]] = {}
    for c in all_connections:
        key = (c.tenant_id, c.integration_code)
        conn_map.setdefault(key, []).append(c)

    rows = []
    for client in clients:
        row = {
            "client_id": client.id,
            "client_code": client.client_code,
            "client_name": client.client_name,
            "is_internal": client.is_internal,
            "status": client.status,
            "integrations": {}
        }

        for idef in definitions:
            conns = conn_map.get((client.id, idef.integration_code), [])
            # If no tenant connection, check if platform fallback applies
            has_custom = len(conns) > 0
            if has_custom:
                if len(conns) == 1:
                    c = conns[0]
                    status_text = c.status.upper() if c.status else "ACTIVE"
                else:
                    status_text = f"{len(conns)} Accounts"
            else:
                platform_conns = conn_map.get((1, idef.integration_code), [])
                if platform_conns and idef.supports_platform_connection:
                    status_text = "Platform Default"
                else:
                    status_text = "Not Configured"

            row["integrations"][idef.integration_code] = {
                "status": status_text,
                "has_custom": has_custom,
                "connection_count": len(conns)
            }
        rows.append(row)

    return {
        "categories": [cat.to_dict() for cat in categories],
        "definitions": [d.to_dict() for d in definitions],
        "matrix": rows,
        "rows": rows
    }
