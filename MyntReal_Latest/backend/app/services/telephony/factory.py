"""
Telephony Provider Factory
Instantiates and configures the appropriate Telephony Provider based on runtime environment.
Supports: 'mock', 'myoperator', 'in_app_webrtc' / 'webrtc'
Created: Aug 2026
"""

import os
import logging
from typing import Optional
from app.core.config import settings
from app.services.telephony.base import BaseTelephonyProvider
from app.services.telephony.mock_provider import MockTelephonyProvider
from app.services.telephony.myoperator_provider import MyOperatorTelephonyProvider
from app.services.telephony.webrtc_provider import InAppWebRTCTelephonyProvider

logger = logging.getLogger(__name__)

# Registry of singleton provider instances
_provider_instances = {}


def get_telephony_provider(provider_name: Optional[str] = None) -> BaseTelephonyProvider:
    """
    Returns the active Telephony Provider instance.
    Defaults to settings.TELEPHONY_PROVIDER (e.g. 'in_app_webrtc', 'myoperator', 'mock').
    """
    name = (provider_name or settings.TELEPHONY_PROVIDER or "in_app_webrtc").lower().strip()
    
    if name in _provider_instances:
        return _provider_instances[name]

    secret = settings.TELEPHONY_WEBHOOK_SECRET or os.getenv("TELEPHONY_WEBHOOK_SECRET", "mock-secret-key-12345")

    if name == "mock":
        instance = MockTelephonyProvider(webhook_secret=secret)
    elif name in ("myoperator", "myoperator_bridge"):
        instance = MyOperatorTelephonyProvider(
            api_token=os.getenv("MYOPERATOR_API_TOKEN"),
            x_api_key=os.getenv("MYOPERATOR_X_API_KEY"),
            api_company_id=os.getenv("MYOPERATOR_API_COMPANY_ID"),
            webhook_secret=os.getenv("MYOPERATOR_WEBHOOK_SECRET"),
            public_ivr_id=os.getenv("MYOPERATOR_PUBLIC_IVR_ID")
        )
    elif name in ("in_app_webrtc", "webrtc", "in_app_pstn"):
        instance = InAppWebRTCTelephonyProvider(
            gateway_url=os.getenv("WEBRTC_GATEWAY_URL", "wss://webrtc-gateway.myntreal.local/ws"),
            api_key=settings.TELEPHONY_API_KEY or os.getenv("TELEPHONY_API_KEY"),
            api_secret=settings.TELEPHONY_API_SECRET or os.getenv("TELEPHONY_API_SECRET"),
            webhook_secret=secret
        )
    else:
        logger.warning(
            f"[TELEPHONY-FACTORY] Provider '{name}' requested but specific driver not configured. "
            f"Defaulting to MockTelephonyProvider for safety."
        )
        instance = MockTelephonyProvider(webhook_secret=secret)

    _provider_instances[name] = instance
    return instance
