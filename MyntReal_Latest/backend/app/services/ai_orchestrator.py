"""
Central AI Lead Engagement Orchestrator (Release 1A Engine)
Evaluates Deterministic Business Rules + AI Recommendations.
Strict Rule: AI MUST NOT independently bypass business rules, opt-out status, or consent limits.
"""

import logging
from typing import Dict, Any
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.vertical_config import get_vertical_config
from app.services.lead_scoring_service import calculate_lead_score
from app.services.human_handover_service import execute_human_handover
from app.models.ai_audit import AIActionLog

logger = logging.getLogger(__name__)

POSSIBLE_ACTIONS = [
    "SEND_WHATSAPP",
    "START_AI_CALL",
    "ASSIGN_HUMAN",
    "SCHEDULE_FOLLOWUP",
    "BOOK_APPOINTMENT",
    "NURTURE",
    "NO_ACTION"
]


class AILeadOrchestrator:
    """
    Central AI Lead Engagement Orchestrator.
    Combines deterministic CRM business rules with AI recommendations.
    Outputs safe, validated action decisions.
    """

    def __init__(self, db: Session):
        self.db = db

    def orchestrate_lead_action(
        self,
        company_id: int,
        lead_id: int,
        lead_data: Dict[str, Any],
        ai_recommendation: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Evaluate lead state and decide next system action.
        """
        vertical = lead_data.get("tags", "GENERAL").upper()
        v_cfg = get_vertical_config(vertical)

        # 1. Deterministic Business Safeguards (Bypass AI if triggered)
        if lead_data.get("opt_out") or lead_data.get("do_not_contact"):
            return self._record_action(company_id, lead_id, vertical, "NO_ACTION", "OPT_OUT_ENFORCED", ai_recommendation)

        if lead_data.get("is_human_takeover") or lead_data.get("status") == "HUMAN_HANDOVER":
            return self._record_action(company_id, lead_id, vertical, "ASSIGN_HUMAN", "HUMAN_TAKEOVER_ACTIVE", ai_recommendation)

        # 2. Score evaluation
        score_info = calculate_lead_score(self.db, company_id, lead_id, lead_data, ai_recommendation)
        score = score_info["score"]

        # 3. Action Decision Engine
        rec_action = ai_recommendation.get("recommended_action", "NO_ACTION")
        if rec_action not in POSSIBLE_ACTIONS:
            rec_action = "NO_ACTION"

        final_action = rec_action

        # Enforce feature flags for autonomous dispatches
        if final_action == "SEND_WHATSAPP" and not getattr(settings, "WA_AI_ENABLED", False):
            final_action = "ASSIGN_HUMAN"
        elif final_action == "START_AI_CALL" and not getattr(settings, "VOICE_AI_ENABLED", False):
            final_action = "ASSIGN_HUMAN"

        if score >= 80:
            if "BOOK_APPOINTMENT" in v_cfg["allowed_ai_actions"]:
                final_action = "BOOK_APPOINTMENT"
        elif score < 30:
            final_action = "NURTURE"

        return self._record_action(company_id, lead_id, vertical, final_action, f"SCORE_{score}", ai_recommendation)

    def _record_action(
        self,
        company_id: int,
        lead_id: int,
        vertical: str,
        action: str,
        reason: str,
        ai_rec: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Record action in ai_action_logs table."""
        try:
            log_entry = AIActionLog(
                company_id=company_id,
                lead_id=lead_id,
                vertical=vertical,
                channel="ORCHESTRATOR",
                action_type=action,
                confidence_score=float(ai_rec.get("confidence", 0.90)),
                ai_recommendation=ai_rec,
                final_action_taken=action,
                human_override=False
            )
            self.db.add(log_entry)
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            logger.error(f"[ORCHESTRATOR-LOG-ERROR] Failed to log action: {e}")

        logger.info(f"[ORCHESTRATOR] Lead {lead_id} -> Action: {action} ({reason})")
        return {
            "lead_id": lead_id,
            "company_id": company_id,
            "vertical": vertical,
            "final_action": action,
            "reason": reason,
            "ai_recommendation": ai_rec
        }
