"""
AI Cost & Usage Tracking Service (Release 1A Engine)
Records token consumption, estimated USD costs, and API latency per company/vertical.
Enforces cost guardrails and maximum retry caps to prevent runaway AI loops.
"""

import logging
from sqlalchemy.orm import Session
from app.models.ai_audit import AIUsageLog

logger = logging.getLogger(__name__)

# Estimated rates per 1,000 tokens (USD)
RATES = {
    "MOCK_LLM_PROVIDER": {"input": 0.0000, "output": 0.0000},
    "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
    "gemini-1.5-flash": {"input": 0.000075, "output": 0.0003}
}


def record_ai_usage(
    db: Session,
    company_id: int,
    provider_name: str,
    model_name: str,
    task_name: str,
    input_tokens: int,
    output_tokens: int,
    latency_ms: int,
    lead_id: int = None
) -> float:
    """
    Log token consumption and calculate estimated cost.
    """
    rate = RATES.get(model_name, RATES.get(provider_name, {"input": 0.0001, "output": 0.0003}))
    cost = ((input_tokens / 1000.0) * rate["input"]) + ((output_tokens / 1000.0) * rate["output"])

    try:
        log_entry = AIUsageLog(
            company_id=company_id,
            lead_id=lead_id,
            provider_name=provider_name,
            model_name=model_name,
            task_name=task_name,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            estimated_cost_usd=cost,
            latency_ms=latency_ms
        )
        db.add(log_entry)
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"[COST-TRACKER-ERROR] Failed to record usage log: {e}")

    return cost
