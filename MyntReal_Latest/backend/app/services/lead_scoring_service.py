"""
Versioned Lead Scoring Service (Release 1A Engine)
Calculates Lead Score (0 to 100) combining Deterministic Rule Score + AI Intent Score.
Provides transparent, human-readable explanations (positive & negative factors).
"""

import logging
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from app.models.ai_lead_intelligence import LeadScoreHistory
from app.core.vertical_config import get_vertical_config

logger = logging.getLogger(__name__)


def calculate_lead_score(
    db: Session,
    company_id: int,
    lead_id: int,
    lead_data: Dict[str, Any],
    ai_analysis: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Calculate versioned lead score.
    Structure: Rule Score (Deterministic) + AI Intent Score.
    Generates human-readable positive and negative factors.
    """
    vertical = lead_data.get("tags", "GENERAL").upper()
    v_cfg = get_vertical_config(vertical)
    scoring_weights = v_cfg.get("scoring_factors", {})

    rule_score = 0
    positives = []
    negatives = []

    # 1. Deterministic Rule Factors
    if lead_data.get("phone"):
        rule_score += 20
        positives.append("Valid phone number provided")
    else:
        negatives.append("Missing phone number")

    if lead_data.get("email"):
        rule_score += 10
        positives.append("Email address provided")

    if lead_data.get("requirements") or lead_data.get("looking_for"):
        rule_score += 20
        positives.append("Detailed customer requirements stated")
    else:
        negatives.append("No specific requirements mentioned")

    if lead_data.get("investment_capacity") or lead_data.get("budget"):
        rule_score += 20
        positives.append("Confirmed budget/investment capacity")
    else:
        negatives.append("Budget not yet confirmed")

    # 2. AI Intent Factors
    ai_intent = ai_analysis.get("intent", "GENERAL")
    ai_confidence = float(ai_analysis.get("confidence", 0.80))
    ai_score = 0

    if ai_intent in ("BOOK_APPOINTMENT", "BUY_NOW", "HIGH_INTENT"):
        ai_score = 30
        positives.append(f"High purchase intent detected by AI ({ai_intent})")
    elif ai_intent in ("INQUIRE_PRICING", "ASK_SPECIFICATIONS"):
        ai_score = 20
        positives.append("Active inquiry intent detected")
    elif ai_intent == "COMPLAINT":
        ai_score = 5
        negatives.append("Customer expressed dissatisfaction or complaint")
    elif ai_intent == "NOT_INTERESTED":
        ai_score = 0
        negatives.append("Customer indicated lack of interest")
    else:
        ai_score = 10

    total_score = min(100, rule_score + ai_score)

    explanation = f"Lead Score: {total_score}/100 based on {len(positives)} positive factors and {len(negatives)} negative factors."

    # Record in LeadScoreHistory
    try:
        score_rec = LeadScoreHistory(
            company_id=company_id,
            lead_id=lead_id,
            score=total_score,
            score_version="v1.0_RULES_PLUS_AI",
            rule_score=rule_score,
            ai_intent_score=ai_score,
            ai_confidence=ai_confidence,
            positive_factors=positives,
            negative_factors=negatives,
            explanation=explanation
        )
        db.add(score_rec)
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"[SCORE-LOG-ERROR] Failed to record score log: {e}")

    return {
        "score": total_score,
        "score_version": "v1.0_RULES_PLUS_AI",
        "rule_score": rule_score,
        "ai_intent_score": ai_score,
        "positive_factors": positives,
        "negative_factors": negatives,
        "explanation": explanation
    }
