"""
Approved Knowledge Retrieval Service (Release 1A Engine)
Retrieves staff-approved business facts for customer queries.
Strict Rule: AI MUST NOT invent prices, discounts, delivery dates, or legal guarantees.
"""

import logging
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.models.ai_knowledge import AIKnowledgeItem

logger = logging.getLogger(__name__)


def retrieve_approved_knowledge_facts(
    db: Session,
    company_id: int,
    vertical: str,
    query_text: str,
    limit: int = 5
) -> List[Dict[str, Any]]:
    """
    Search and return staff-approved active knowledge items for company_id.
    Filters strictly for is_approved = True and is_active = True.
    """
    try:
        items = db.query(AIKnowledgeItem).filter(
            AIKnowledgeItem.company_id == company_id,
            AIKnowledgeItem.is_approved == True,
            AIKnowledgeItem.is_active == True
        ).limit(limit).all()

        results = []
        for item in items:
            results.append({
                "id": item.id,
                "title": item.title,
                "fact_content": item.fact_content,
                "version": item.version,
                "is_approved": True
            })
        return results
    except Exception as e:
        logger.error(f"[KNOWLEDGE-RETRIEVAL-ERROR] DB lookup failed: {e}")
        return []
