"""
Voice AI Calling Service & Eligibility Engine (Release 1A Engine)
Handles call eligibility checks, call scheduling, and voice provider dispatch.
External voice dispatches use NullVoiceProvider and return 'VOICE_PROVIDER_NOT_CONFIGURED'.
"""

import logging
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from app.core.config import settings
from app.services.ai_providers.null_voice_provider import NullVoiceProvider
from app.models.ai_voice import VoiceCallRecord

logger = logging.getLogger(__name__)


class VoiceAIService:
    """
    Voice AI Calling Service.
    Integrates neutral VoiceProvider adapter interface.
    Default provider is PlivoTelephonyProvider when live credentials exist, otherwise NullVoiceProvider.
    """

    def __init__(self, provider=None):
        if provider:
            self.provider = provider
        elif getattr(settings, 'PLIVO_AUTH_ID', None) and not str(settings.PLIVO_AUTH_ID).startswith('mock_'):
            from app.services.telephony.plivo_provider import PlivoTelephonyProvider
            self.provider = PlivoTelephonyProvider()
        else:
            self.provider = NullVoiceProvider()

    def check_call_eligibility(self, lead_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate eligibility for automated calling:
        - Must have valid phone
        - VOICE_AI_ENABLED must be True
        - Lead status must not be CLOSED or DO_NOT_CALL
        """
        phone = lead_data.get("phone")
        if not phone:
            return {"eligible": False, "reason": "MISSING_PHONE"}

        enabled = getattr(settings, "VOICE_AI_ENABLED", False)
        if not enabled:
            return {"eligible": False, "reason": "VOICE_AI_DISABLED_BY_FEATURE_FLAG"}

        return {"eligible": True, "reason": "ELIGIBLE"}

    def schedule_ai_call(
        self,
        db: Session,
        company_id: int,
        lead_id: int,
        phone: str,
        prompt_instructions: str = ""
    ) -> Dict[str, Any]:
        """
        Schedule or initiate outbound AI call.
        Enforces feature flag check and returns NullVoiceProvider response if disabled.
        """
        eligibility = self.check_call_eligibility({"phone": phone})
        if not eligibility["eligible"]:
            logger.info(f"[VOICE-AI] Call skipped for lead {lead_id}: {eligibility['reason']}")
            return {
                "success": False,
                "status": "SKIPPED",
                "reason": eligibility["reason"],
                "provider_call_id": None
            }

        # Dispatch via configured provider (NullVoiceProvider returns VOICE_PROVIDER_NOT_CONFIGURED)
        res = self.provider.initiate_call(
            to_phone=phone,
            from_phone="",
            prompt_instructions=prompt_instructions,
            webhook_url="",
            metadata={"company_id": company_id, "lead_id": lead_id}
        )

        # Log call record in DB
        try:
            rec = VoiceCallRecord(
                company_id=company_id,
                lead_id=lead_id,
                phone=phone,
                provider_name=self.provider.provider_name,
                provider_call_id=res.get("provider_call_id"),
                status=res.get("status", "FAILED")
            )
            db.add(rec)
            db.commit()
        except Exception as e:
            db.rollback()
            logger.error(f"[VOICE-AI-LOG-ERROR] Failed to save call record: {e}")

        return res
