"""
Mock LLM Provider (Offline Testing & Shadow Mode Analysis)
Implements LLMProvider returning structured JSON for offline testing, local validation, and shadow mode analysis.
"""

import logging
import json
from typing import Dict, Any
from app.services.ai_providers.base import LLMProvider

logger = logging.getLogger(__name__)


class MockLLMProvider(LLMProvider):
    """
    Mock/Local LLM provider returning validated structured JSON.
    Used for local testing, offline development, and shadow mode.
    """
    @property
    def provider_name(self) -> str:
        return "MOCK_LLM_PROVIDER"

    def generate_structured_json(
        self,
        prompt: str,
        system_instruction: str,
        response_schema: Dict[str, Any],
        temperature: float = 0.2
    ) -> Dict[str, Any]:
        logger.debug(f"[MOCK-LLM] Generating structured JSON for prompt length {len(prompt)}")
        
        # Default structured output fallback
        return {
            "intent": "INQUIRE_PRICING",
            "confidence": 0.88,
            "qualification": "QUALIFIED",
            "extracted_fields": {
                "budget": "5 Lakhs",
                "timeline": "Immediate",
                "location": "Hyderabad"
            },
            "objections": ["PRICE_CONCERN"],
            "suggested_response": "Thank you for your interest! Our team will provide a detailed quote shortly.",
            "recommended_action": "ASSIGN_HUMAN",
            "escalation_required": False
        }
