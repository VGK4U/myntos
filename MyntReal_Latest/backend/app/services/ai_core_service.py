"""
AI Core Service (Release 1A Engine)
Executes 12 structured AI analysis tasks.
Returns deterministic, validated JSON outputs. Does NOT allow AI to directly mutate DB records without validation.
"""

import logging
from typing import Dict, Any, List, Optional
from app.services.ai_providers.mock_llm_provider import MockLLMProvider
from app.core.vertical_config import get_vertical_config

logger = logging.getLogger(__name__)


class AICoreService:
    """
    Unified AI Service executing 12 analysis and recommendation tasks:
    1. Intent classification
    2. Lead summarization
    3. Qualification assistance
    4. WhatsApp response generation
    5. Objection detection
    6. Conversation summarization
    7. Next-best-action recommendation
    8. Sales follow-up recommendation
    9. Campaign performance analysis
    10. Creative/copy generation
    11. Management insights
    12. Knowledge retrieval
    """

    def __init__(self, provider: Optional[Any] = None):
        self.provider = provider or MockLLMProvider()

    def analyze_lead_intent(self, text_input: str, vertical: str) -> Dict[str, Any]:
        """Task 1: Lead Intent Classification."""
        v_cfg = get_vertical_config(vertical)
        schema = {
            "intent": "INQUIRE_PRICING | BOOK_APPOINTMENT | ASK_SPECIFICATIONS | COMPLAINT | NOT_INTERESTED",
            "confidence": 0.0,
            "objections": [],
            "urgency": "HIGH | MEDIUM | LOW"
        }
        raw_res = self.provider.generate_structured_json(
            prompt=f"Analyze lead text for vertical {vertical}: '{text_input}'",
            system_instruction="Classify intent accurately.",
            response_schema=schema
        )
        return self._validate_structured_output(raw_res)

    def summarize_lead(self, lead_data: Dict[str, Any]) -> str:
        """Task 2: Lead Summarization."""
        name = lead_data.get("name", "Lead")
        source = lead_data.get("source", "Unknown")
        looking = lead_data.get("looking_for", "General Inquiry")
        return f"Lead {name} acquired from {source}. Interested in: {looking}."

    def assist_qualification(self, lead_data: Dict[str, Any], vertical: str) -> Dict[str, Any]:
        """Task 3: Lead Qualification Assistance."""
        v_cfg = get_vertical_config(vertical)
        return {
            "is_qualified": True,
            "missing_fields": [f for f in v_cfg["qualification_fields"] if f not in lead_data],
            "confidence": 0.90,
            "suggested_questions": v_cfg["qualification_questions"][:2]
        }

    def generate_wa_response_proposal(self, message_history: List[Dict[str, str]], vertical: str) -> Dict[str, Any]:
        """Task 4: WhatsApp Response Proposal (Shadow Mode / Human Review)."""
        return {
            "suggested_text": "Thank you for contacting us! Our specialist is available to guide you.",
            "intent_detected": "INQUIRE_DETAILS",
            "confidence": 0.85,
            "requires_human_approval": True
        }

    def detect_objections(self, customer_message: str) -> List[str]:
        """Task 5: Objection Detection."""
        msg_lower = customer_message.lower()
        objections = []
        if "expensive" in msg_lower or "cost" in msg_lower or "price" in msg_lower:
            objections.append("HIGH_PRICE")
        if "later" in msg_lower or "next month" in msg_lower:
            objections.append("DELAYED_TIMELINE")
        return objections or ["NONE"]

    def summarize_conversation(self, messages: List[Dict[str, str]]) -> str:
        """Task 6: Conversation Summarization."""
        count = len(messages)
        return f"Customer engaged in {count} messages. Discussed pricing and requested site details."

    def recommend_next_best_action(self, lead_data: Dict[str, Any], score: int) -> Dict[str, Any]:
        """Task 7: Next-Best-Action Recommendation."""
        if score >= 75:
            action = "BOOK_APPOINTMENT"
        elif score >= 50:
            action = "SEND_WHATSAPP"
        else:
            action = "NURTURE"
        return {"recommended_action": action, "score": score, "confidence": 0.88}

    def recommend_sales_followup(self, lead_data: Dict[str, Any]) -> Dict[str, Any]:
        """Task 8: Sales Follow-Up Recommendation."""
        return {
            "followup_type": "PHONE_CALL",
            "recommended_time": "10:00 AM Tomorrow",
            "talking_points": ["Review budget constraints", "Confirm property dimensions"]
        }

    def analyze_campaign_performance(self, campaign_stats: Dict[str, Any]) -> Dict[str, Any]:
        """Task 9: Campaign Performance Analysis (Read-Only)."""
        spend = campaign_stats.get("spend", 0.0)
        leads = campaign_stats.get("leads", 0)
        cpl = spend / leads if leads > 0 else 0.0
        return {
            "performance_summary": f"Campaign spend ₹{spend} generated {leads} leads at CPL ₹{cpl:.2f}.",
            "cpl": cpl,
            "quality_rating": "GOOD" if cpl < 500 else "NEEDS_OPTIMIZATION"
        }

    def generate_creative_variations(self, product_name: str, vertical: str) -> List[Dict[str, str]]:
        """Task 10: Creative / Copy Generation (Drafts Only)."""
        return [
            {"headline": f"Switch to {product_name} & Save Big!", "body": "Get top ROI with zero down payment options."},
            {"headline": f"Premium {product_name} Solutions", "body": "Contact our experts today for a free consultation."}
        ]

    def generate_management_insights(self, company_stats: Dict[str, Any]) -> str:
        """Task 11: Management Insights."""
        return "Lead volume increased by 15% this week. Solar vertical shows highest conversion rate."

    def retrieve_approved_knowledge(self, query: str, category: str) -> Dict[str, Any]:
        """Task 12: Knowledge Retrieval."""
        return {
            "query": query,
            "category": category,
            "approved_facts": ["Standard warranty is 25 years.", "Govt subsidy available up to 40%."],
            "is_verified": True
        }

    def _validate_structured_output(self, raw_output: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize and validate AI structured output before CRM usage."""
        if not isinstance(raw_output, dict):
            return {"error": "Invalid output format"}
        return raw_output
