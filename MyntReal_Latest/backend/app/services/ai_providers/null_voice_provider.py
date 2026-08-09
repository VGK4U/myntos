"""
Null Voice Provider (Default Placeholder)
Implements VoiceProvider interface. Safe fallback when external AI Voice calling APIs are not configured.
Returns 'VOICE_PROVIDER_NOT_CONFIGURED' without executing fake API calls.
"""

import logging
from typing import Dict, Any
from app.services.ai_providers.base import VoiceProvider

logger = logging.getLogger(__name__)


class NullVoiceProvider(VoiceProvider):
    """
    Default null provider implementation.
    Safely handles call requests when VOICE_AI_ENABLED = False or credentials are missing.
    """
    @property
    def provider_name(self) -> str:
        return "NULL_VOICE_PROVIDER"

    def initiate_call(
        self,
        to_phone: str,
        from_phone: str,
        prompt_instructions: str,
        webhook_url: str,
        metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        logger.info(f"[NULL-VOICE] Initiate call requested for {to_phone}. Voice provider is NOT configured.")
        return {
            "success": False,
            "status": "VOICE_PROVIDER_NOT_CONFIGURED",
            "provider_call_id": None,
            "error": "External AI Voice calling provider API details are not configured yet."
        }

    def get_call_status(self, provider_call_id: str) -> Dict[str, Any]:
        return {
            "success": False,
            "status": "VOICE_PROVIDER_NOT_CONFIGURED",
            "provider_call_id": provider_call_id
        }

    def handle_webhook_event(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "success": False,
            "status": "VOICE_PROVIDER_NOT_CONFIGURED"
        }

    def transfer_to_human(self, provider_call_id: str, target_staff_phone: str) -> Dict[str, Any]:
        return {
            "success": False,
            "status": "VOICE_PROVIDER_NOT_CONFIGURED",
            "error": "Voice transfer unavailable on NullVoiceProvider."
        }
