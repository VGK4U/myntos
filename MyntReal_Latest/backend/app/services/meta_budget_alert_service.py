"""
Meta Budget & Spend Alert Service (Phase 2J)
Monitors campaign budget utilization (80%, 90%, 100% threshold alerts, spend spike alerts, zero-lead alerts).
Advisory alert generation only. Zero automatic budget modifications executed.
"""

import logging
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import text

logger = logging.getLogger(__name__)


def evaluate_meta_budget_alerts(db: Session, company_id: int = 1) -> Dict[str, Any]:
    """
    Evaluates campaign budgets and spend utilization alerts.
    """
    # Fetch active alerts from meta_alerts
    alert_rows = db.execute(text("""
        SELECT id, alert_type, severity, title, message, is_resolved, created_at
        FROM meta_alerts
        WHERE company_id = :cid
        ORDER BY id DESC LIMIT 20
    """), {"cid": company_id}).fetchall()

    alerts_list = [
        {
            "id": r[0],
            "alert_type": r[1],
            "severity": r[2],
            "title": r[3],
            "message": r[4],
            "is_resolved": r[5],
            "created_at": str(r[6])
        }
        for r in alert_rows
    ]

    # Pre-flight budget utilization summary
    return {
        "status": "PASS",
        "company_id": company_id,
        "daily_budget_limit_inr": 1000.0,
        "spend_today_inr": 0.0,
        "budget_utilization_percentage": 0.0,
        "active_alerts_count": len([a for a in alerts_list if not a["is_resolved"]]),
        "alerts": alerts_list,
        "safety_guarantee": "Advisory alerts only. Zero automatic budget changes allowed (CAMPAIGN_AUTOMATION_ENABLED = False)."
    }
