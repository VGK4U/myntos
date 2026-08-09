"""
AI WhatsApp Engine & State Machine (Release 1A Engine)
Deterministic 10-state WhatsApp conversation manager.
Supports Mode 0 (Standard WA) and Mode 1 (AI Shadow Mode — AI proposals visible ONLY to staff UI; 0 customer sends).
Autonomous AI dispatches remain strictly OFF (WA_AI_ENABLED = False).
"""

import logging
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from app.core.config import settings

logger = logging.getLogger(__name__)

# Deterministic 10-State Conversation Framework
VALID_STATES = [
    "NEW_LEAD",
    "WELCOME",
    "AWAITING_RESPONSE",
    "QUALIFYING",
    "HIGH_INTENT",
    "APPOINTMENT",
    "HUMAN_HANDOVER",
    "NURTURE",
    "NOT_INTERESTED",
    "CLOSED"
]


class WhatsAppAIEngine:
    """
    WhatsApp AI State Machine & Proposal Engine.
    Evaluates customer messages and determines state transitions.
    Mode 1 (AI Shadow Mode): Generates proposed response for staff UI only. Customer receives NOTHING.
    """

    def __init__(self, db: Session):
        self.db = db

    def process_inbound_message(
        self,
        company_id: int,
        lead_id: int,
        phone: str,
        message_text: str,
        current_state: str = "QUALIFYING"
    ) -> Dict[str, Any]:
        """
        Process inbound message through deterministic state machine.
        Returns AI analysis and proposed response without dispatching to customer.
        """
        # Validate state
        state = current_state if current_state in VALID_STATES else "QUALIFYING"
        
        # Mode check
        shadow_mode = getattr(settings, "AI_SHADOW_MODE_ENABLED", True)  # Default True for internal analysis
        ai_enabled = getattr(settings, "WA_AI_ENABLED", False)         # Autonomous dispatch strictly False

        # State transition analysis
        msg_lower = message_text.lower()
        next_state = state
        handover_triggered = False
        handover_reason = None

        if "talk to human" in msg_lower or "agent" in msg_lower or "call me" in msg_lower:
            next_state = "HUMAN_HANDOVER"
            handover_triggered = True
            handover_reason = "CUSTOMER_REQUESTED_HUMAN"
        elif "visit" in msg_lower or "appointment" in msg_lower or "demo" in msg_lower:
            next_state = "APPOINTMENT"
        elif "not interested" in msg_lower or "stop" in msg_lower:
            next_state = "NOT_INTERESTED"

        # Generate proposal
        proposed_reply = f"Hello! Thanks for your message regarding '{message_text[:30]}...'. How can our specialist assist you today?"

        result = {
            "company_id": company_id,
            "lead_id": lead_id,
            "previous_state": state,
            "next_state": next_state,
            "handover_triggered": handover_triggered,
            "handover_reason": handover_reason,
            "ai_proposed_response": proposed_reply,
            "mode": "MODE_1_SHADOW_STAFF_ONLY" if shadow_mode else "MODE_0_STANDARD",
            "sent_to_customer": False  # ALWAYS False in Release 1A
        }

        logger.info(f"[WA-AI-ENGINE] Shadow mode analysis for lead {lead_id}: State {state} -> {next_state}")
        return result
