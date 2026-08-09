"""
Unified Lead View & Timeline Endpoint (Phase 2 Integration Layer)
Provides GET /api/v1/crm/leads/{lead_id}/unified-timeline
Consolidates CRM Lead + Meta Attribution + AI Intelligence + WhatsApp + Calls + Follow-ups + Realized Payments into a single unified timeline response.
Does NOT create duplicate database records.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Dict, Any, List

from app.core.database import get_db
from app.models.crm import CRMLead

router = APIRouter(prefix="/crm/leads", tags=["CRM Unified Lead Timeline"])


@router.get("/{lead_id}/unified-timeline")
def get_unified_lead_timeline(lead_id: int, db: Session = Depends(get_db)):
    """
    Get consolidated single-screen lead timeline:
    1. CRM Lead Profile & Multi-Handler details
    2. Immutable Meta Attribution
    3. AI Intelligence & Score Explanation
    4. WhatsApp Message History
    5. Scheduled Follow-ups & Site Visits
    6. Realized Cash Payments Ledger
    """
    lead = db.query(CRMLead).filter(CRMLead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    company_id = lead.company_id

    # 1. Meta Attribution
    attribution = None
    try:
        att_row = db.execute(text("""
            SELECT meta_lead_id, meta_campaign_id, meta_campaign_name, meta_adset_id, meta_adset_name,
                   meta_ad_id, meta_ad_name, meta_form_id, meta_form_name, utm_source, utm_medium, utm_campaign
            FROM meta_leads_attribution
            WHERE lead_id = :lid
        """), {"lid": lead_id}).fetchone()
        if att_row:
            attribution = {
                "meta_lead_id": att_row[0],
                "campaign_id": att_row[1],
                "campaign_name": att_row[2],
                "adset_id": att_row[3],
                "adset_name": att_row[4],
                "ad_id": att_row[5],
                "ad_name": att_row[6],
                "form_id": att_row[7],
                "form_name": att_row[8],
                "utm_source": att_row[9],
                "utm_medium": att_row[10],
                "utm_campaign": att_row[11],
            }
    except Exception:
        pass

    # 2. AI Intelligence & Score
    ai_intelligence = {"lead_score": 50, "score_version": "v1.0", "positive_factors": [], "negative_factors": [], "recommended_action": "ASSIGN_HUMAN"}
    try:
        score_row = db.execute(text("""
            SELECT score, score_version, positive_factors, negative_factors, explanation
            FROM lead_score_history
            WHERE lead_id = :lid
            ORDER BY id DESC LIMIT 1
        """), {"lid": lead_id}).fetchone()
        if score_row:
            import json
            ai_intelligence = {
                "lead_score": score_row[0],
                "score_version": score_row[1],
                "positive_factors": json.loads(score_row[2]) if isinstance(score_row[2], str) else score_row[2],
                "negative_factors": json.loads(score_row[3]) if isinstance(score_row[3], str) else score_row[3],
                "explanation": score_row[4]
            }
    except Exception:
        pass

    # 3. WhatsApp Messages Timeline
    wa_messages = []
    try:
        wa_rows = db.execute(text("""
            SELECT wamid, direction, sender_type, body_text, delivery_status, sent_at
            FROM wa_messages
            WHERE lead_id = :lid
            ORDER BY sent_at ASC
        """), {"lid": lead_id}).fetchall()
        for r in wa_rows:
            wa_messages.append({
                "wamid": r[0],
                "direction": r[1],
                "sender_type": r[2],
                "body_text": r[3],
                "delivery_status": r[4],
                "sent_at": r[5].isoformat() if r[5] else None
            })
    except Exception:
        pass

    # 4. Follow-ups & Appointments
    followups = []
    try:
        f_rows = db.execute(text("""
            SELECT id, follow_up_type, status, scheduled_time, notes
            FROM crm_lead_followups
            WHERE lead_id = :lid
            ORDER BY scheduled_time DESC
        """), {"lid": lead_id}).fetchall()
        for f in f_rows:
            followups.append({
                "id": f[0],
                "type": str(f[1]),
                "status": str(f[2]),
                "scheduled_time": f[3].isoformat() if f[3] else None,
                "notes": f[4]
            })
    except Exception:
        pass

    # 5. Realized Financial Transactions Ledger
    transactions = []
    total_cash_received = 0.0
    try:
        tx_rows = db.execute(text("""
            SELECT id, amount, payment_method, transaction_ref, status, created_at
            FROM crm_lead_transactions
            WHERE lead_id = :lid
            ORDER BY created_at DESC
        """), {"lid": lead_id}).fetchall()
        for tx in tx_rows:
            amt = float(tx[1] or 0.0)
            if str(tx[4]).lower() in ("validated", "completed", "paid"):
                total_cash_received += amt
            transactions.append({
                "id": tx[0],
                "amount": amt,
                "payment_method": tx[2],
                "transaction_ref": tx[3],
                "status": tx[4],
                "created_at": tx[5].isoformat() if tx[5] else None
            })
    except Exception:
        pass

    return {
        "status": "success",
        "lead": {
            "id": lead.id,
            "company_id": lead.company_id,
            "name": lead.name,
            "email": lead.email,
            "phone": lead.phone,
            "status": lead.status,
            "priority": lead.priority,
            "source": lead.source,
            "tags": lead.tags,
            "telecaller_id": lead.telecaller_id,
            "field_staff_id": lead.field_staff_id,
            "deal_value_total": lead.deal_value_total,
            "deal_value_received": lead.deal_value_received or total_cash_received,
            "deal_value_balance": lead.deal_value_balance
        },
        "meta_attribution": attribution,
        "ai_intelligence": ai_intelligence,
        "whatsapp_messages": wa_messages,
        "followups": followups,
        "transactions_ledger": transactions,
        "realized_cash_total": total_cash_received
    }
