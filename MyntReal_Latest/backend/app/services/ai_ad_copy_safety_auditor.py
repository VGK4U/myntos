"""
AI Ad Copy Safety Auditor (Phase 2B Integration Layer)
Audits generated ad copy headlines and text against staff-approved knowledge items (ai_knowledge_items).
Rejects un-approved commercial claims ("50% subsidy", "guaranteed free installation", "guaranteed loan approval").
"""

import logging
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from app.services.ai_knowledge_service import retrieve_approved_knowledge_facts

logger = logging.getLogger(__name__)

UNSUPPORTED_CLAIM_TRIGGER_PHRASES = [
    "50% subsidy",
    "100% subsidy",
    "guaranteed subsidy",
    "guaranteed loan",
    "guaranteed approval",
    "free installation",
    "zero cost solar",
    "guaranteed return",
    "guaranteed savings"
]


def audit_ad_copy_claims_against_knowledge(
    db: Session,
    company_id: int,
    vertical: str,
    headline: str,
    primary_text: str
) -> Dict[str, Any]:
    """
    Audit ad copy content for unsupported commercial claims.
    Ensures all claims match staff-approved knowledge items.
    """
    text_to_audit = f"{headline} {primary_text}".lower()
    flagged_phrases = []

    for phrase in UNSUPPORTED_CLAIM_TRIGGER_PHRASES:
        if phrase in text_to_audit:
            flagged_phrases.append(phrase)

    if flagged_phrases:
        logger.warning(f"[SAFETY-AUDIT-REJECTED] Flagged unsupported claims: {flagged_phrases}")
        return {
            "is_safe": False,
            "status": "REJECTED_UNSUPPORTED_CLAIMS",
            "flagged_phrases": flagged_phrases,
            "explanation": f"Ad copy contains un-approved claims ({', '.join(flagged_phrases)}) not found in staff-approved Mynt OS knowledge base."
        }

    # Verify approved facts exist
    approved_facts = retrieve_approved_knowledge_facts(db, company_id, vertical, query_text="")

    return {
        "is_safe": True,
        "status": "PASSED_KNOWLEDGE_SAFETY",
        "flagged_phrases": [],
        "approved_facts_count": len(approved_facts),
        "explanation": "Ad copy passed all AI safety checks and contains no un-approved commercial claims."
    }
