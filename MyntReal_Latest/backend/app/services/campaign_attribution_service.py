"""
Staff Campaign Revenue Attribution Service (Phase 2 Integration Layer)
Answers: "Which Meta campaign generated revenue and which staff member converted it?"
Calculates realized revenue per campaign broken down by staff employee assignment.
Uses validated transaction receipts (crm_lead_transactions).
"""

import logging
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import text

logger = logging.getLogger(__name__)


def calculate_campaign_staff_revenue_attribution(
    db: Session,
    company_id: int,
    campaign_id: str
) -> Dict[str, Any]:
    """
    Connect Meta Campaign -> Meta Attribution -> CRM Lead -> Staff Member -> Validated Cash Transactions.
    Provides complete staff revenue breakdown for a given campaign.
    """
    try:
        # Fetch campaign leads count & staff conversion breakdown
        rows = db.execute(text("""
            SELECT 
                COALESCE(l.telecaller_id, 0) AS staff_id,
                COUNT(DISTINCT l.id) AS total_leads,
                COUNT(DISTINCT CASE WHEN l.status IN ('qualified', 'won', 'completed') THEN l.id END) AS qualified_leads,
                COALESCE(SUM(t.amount), 0.0) AS realized_revenue
            FROM meta_leads_attribution a
            JOIN crm_leads l ON l.id = a.lead_id
            LEFT JOIN crm_lead_transactions t ON t.lead_id = l.id AND t.validation_status IN ('validated', 'COMPLETED', 'PAID', 'approved')
            WHERE a.company_id = :cid AND a.meta_campaign_id = :camp_id
            GROUP BY COALESCE(l.telecaller_id, 0)
        """), {"cid": company_id, "camp_id": campaign_id}).fetchall()

        staff_breakdown = []
        total_campaign_leads = 0
        total_campaign_qualified = 0
        total_campaign_revenue = 0.0

        for r in rows:
            sid = r[0]
            leads = int(r[1])
            qual = int(r[2])
            rev = float(r[3])

            staff_name = "Unassigned Staff"
            if sid > 0:
                s_row = db.execute(text("SELECT full_name FROM staff_employees WHERE id = :sid"), {"sid": sid}).fetchone()
                if s_row and s_row[0]:
                    staff_name = s_row[0]

            staff_breakdown.append({
                "staff_id": sid,
                "staff_name": staff_name,
                "leads_assigned": leads,
                "qualified_leads": qual,
                "realized_cash_revenue": rev
            })

            total_campaign_leads += leads
            total_campaign_qualified += qual
            total_campaign_revenue += rev

        return {
            "company_id": company_id,
            "campaign_id": campaign_id,
            "total_campaign_leads": total_campaign_leads,
            "total_qualified_leads": total_campaign_qualified,
            "total_realized_revenue": total_campaign_revenue,
            "staff_revenue_breakdown": staff_breakdown
        }
    except Exception as e:
        logger.error(f"[CAMPAIGN-ATTRIBUTION-ERROR] Query failed: {e}")
        return {
            "company_id": company_id,
            "campaign_id": campaign_id,
            "error": str(e),
            "staff_revenue_breakdown": []
        }
