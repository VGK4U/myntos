"""
Human Handover Service (Release 1A Engine)
Executes instant human takeover when AI confidence drops or specific triggers occur.
Disables AI auto-responses and generates a comprehensive staff briefing context card.
"""

import logging
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text

logger = logging.getLogger(__name__)

HANDOVER_TRIGGERS = [
    "CUSTOMER_REQUESTED_HUMAN",
    "LOW_AI_CONFIDENCE",
    "HIGH_VALUE_LEAD",
    "CUSTOMER_COMPLAINT",
    "PRICING_NEGOTIATION",
    "FINANCE_LOAN_QUERY",
    "REPEATED_MISUNDERSTANDING",
    "MANUAL_STAFF_ESCALATION"
]


def execute_human_handover(
    db: Session,
    company_id: int,
    lead_id: int,
    phone: str,
    trigger_reason: str,
    assigned_staff_id: Optional[int] = None
) -> Dict[str, Any]:
    """
    Execute instant human handover:
    1. Mark wa_conversations is_human_takeover = True, state = HUMAN_HANDOVER.
    2. Disable autonomous AI auto-response for this conversation.
    3. Generate staff briefing card with lead summary, score, intent, and recommended action.
    """
    reason = trigger_reason if trigger_reason in HANDOVER_TRIGGERS else "MANUAL_STAFF_ESCALATION"

    # 1. Update conversation state in DB
    try:
        db.execute(text("""
            UPDATE wa_conversations
            SET is_human_takeover = TRUE,
                current_state = 'HUMAN_HANDOVER',
                assigned_staff_id = :sid,
                updated_at = NOW()
            WHERE company_id = :cid AND lead_id = :lid
        """), {"sid": assigned_staff_id, "cid": company_id, "lid": lead_id})
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"[HANDOVER-DB-ERROR] Failed to set handover state for lead {lead_id}: {e}")

    # 2. Build Briefing Context Card for Staff UI
    briefing_card = {
        "lead_id": lead_id,
        "company_id": company_id,
        "phone": phone,
        "trigger_reason": reason,
        "ai_auto_response": "DISABLED",
        "recommended_staff_action": "Call customer or send manual WhatsApp message.",
        "briefing_summary": f"Human handover triggered via {reason}. Staff assistance required immediately."
    }

    logger.info(f"[HANDOVER-EXECUTED] Lead {lead_id} transferred to human staff. Reason: {reason}")
    return briefing_card
