"""
AI Provider Abstraction Layer (Core Interfaces)
Defines provider-neutral abstract base classes for LLM, STT, TTS, Voice, WhatsApp AI, and Creative AI.
Allows changing backend providers (OpenAI, Gemini, ElevenLabs, Vapi, Exotel, etc.) without altering CRM business logic.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List


class AIProvider(ABC):
    """Base interface for all AI service providers."""
    @property
    @abstractmethod
    def provider_name(self) -> str:
        pass


class LLMProvider(AIProvider):
    """Abstract LLM Provider interface (OpenAI, Gemini, Anthropic, Ollama, etc.)."""
    @abstractmethod
    def generate_structured_json(
        self,
        prompt: str,
        system_instruction: str,
        response_schema: Dict[str, Any],
        temperature: float = 0.2
    ) -> Dict[str, Any]:
        """Generate validated structured JSON output from LLM."""
        pass


class SpeechToTextProvider(AIProvider):
    """Abstract Speech-to-Text Provider interface."""
    @abstractmethod
    def transcribe_audio(self, audio_bytes: bytes, language_code: str = "en") -> Dict[str, Any]:
        pass


class TextToSpeechProvider(AIProvider):
    """Abstract Text-to-Speech Provider interface."""
    @abstractmethod
    def synthesize_speech(self, text: str, voice_id: str) -> bytes:
        pass


class VoiceProvider(AIProvider):
    """
    Abstract Voice Calling Provider interface.
    Neutral adapter interface covering call initiation, status lookup, webhook handling, and transfers.
    """
    @abstractmethod
    def initiate_call(
        self,
        to_phone: str,
        from_phone: str,
        prompt_instructions: str,
        webhook_url: str,
        metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Initiate outbound voice call."""
        pass

    @abstractmethod
    def get_call_status(self, provider_call_id: str) -> Dict[str, Any]:
        """Fetch real-time call status."""
        pass

    @abstractmethod
    def handle_webhook_event(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process inbound provider webhook event."""
        pass

    @abstractmethod
    def transfer_to_human(self, provider_call_id: str, target_staff_phone: str) -> Dict[str, Any]:
        """Execute live human transfer."""
        pass


class WhatsAppAIAdapter(AIProvider):
    """Abstract WhatsApp AI response adapter interface."""
    @abstractmethod
    def generate_wa_response(self, conversation_history: List[Dict[str, str]], lead_context: Dict[str, Any]) -> Dict[str, Any]:
        pass


class CreativeAIAdapter(AIProvider):
    """Abstract Creative & Ad Copy Generation adapter interface."""
    @abstractmethod
    def generate_ad_copy_variations(self, product_details: Dict[str, Any], vertical: str) -> List[Dict[str, str]]:
        pass
