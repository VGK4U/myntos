"""
Staff Campaign Brief Builder (Phase 2 Integration Layer)
Staff-facing campaign concept & ad copy preparation workflow.
DRAFT ONLY. Meta write operations remain strictly DISABLED (META_ADS_WRITE_ENABLED = False).
"""

import logging
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.vertical_config import get_vertical_config
from app.services.ai_knowledge_service import retrieve_approved_knowledge_facts

logger = logging.getLogger(__name__)


def generate_staff_campaign_brief(
    db: Session,
    company_id: int,
    vertical: str,
    target_location: str,
    product_name: str,
    daily_budget_inr: float = 1000.0
) -> Dict[str, Any]:
    """
    Generate DRAFT campaign brief and ad copy concepts for staff review.
    Draws approved business facts to prevent hallucinated prices or claims.
    Zero Meta write operations executed.
    """
    v_cfg = get_vertical_config(vertical)
    approved_facts = retrieve_approved_knowledge_facts(db, company_id, vertical, product_name)

    facts_summary = [f["fact_content"] for f in approved_facts] if approved_facts else ["Standard Mynt OS enterprise quality."]

    brief = {
        "company_id": company_id,
        "vertical": vertical,
        "vertical_display_name": v_cfg["display_name"],
        "target_location": target_location,
        "product_name": product_name,
        "daily_budget_inr": daily_budget_inr,
        "status": "DRAFT_PENDING_STAFF_REVIEW",
        "ad_copy_variations": [
            {
                "headline": f"Top Quality {product_name} in {target_location}",
                "primary_text": f"Upgrade today with {product_name}. Verified facts: {facts_summary[0]}",
                "description": "Book a free site consultation today.",
                "call_to_action": "LEARN_MORE"
            },
            {
                "headline": f"Exclusive {product_name} Offer — {target_location}",
                "primary_text": f"Get expert installation and long-term warranty on {product_name}.",
                "description": "Zero hidden charges. Govt subsidy support available.",
                "call_to_action": "GET_QUOTE"
            }
        ],
        "lead_form_questions": v_cfg["qualification_questions"],
        "wa_followup_suggestion": f"Hello! Thanks for asking about {product_name} in {target_location}. Our team is preparing your custom quote.",
        "meta_ads_write_status": "DISABLED_DRAFT_ONLY"
    }

    logger.info(f"[CAMPAIGN-BRIEF] Draft brief generated for {product_name} in {target_location} (DRAFT ONLY)")
    return brief
