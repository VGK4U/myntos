"""
Meta Ads Management Center API Router (Phase 2J Master Endpoints)
Provides comprehensive API namespace /api/v1/meta-ads/ covering Dashboard, Connections, Campaigns,
AdSets, Ads, Creative Studio, Leads, Insights, Budget, Approvals, Reports, Audit, and Sync.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from pydantic import BaseModel
from typing import Dict, Any, List, Optional

from app.core.database import get_db
from app.services.meta_sync_engine import execute_meta_account_sync
from app.services.meta_insights_analytics_service import get_meta_ads_dashboard_kpis
from app.services.meta_budget_alert_service import evaluate_meta_budget_alerts
from app.services.meta_approval_engine import create_action_request, approve_and_execute_action
from app.services.multilingual_creative_qa_service import evaluate_creative_multilingual_qa
from app.services.meta_reports_generator import generate_meta_ads_export_report

router = APIRouter(prefix="/meta-ads", tags=["Meta Ads Management Center (Supreme Admin)"])


class ActionRequestInput(BaseModel):
    company_id: int = 1
    requested_by: str = "MR10001"
    action_type: str = "PAUSE_CAMPAIGN"
    target_object_type: str = "CAMPAIGN"
    target_object_id: str = "120254919777680348"
    current_value: Optional[Dict[str, Any]] = None
    proposed_value: Optional[Dict[str, Any]] = None
    reason: str = "Routine campaign pause"


class MultilingualQARequest(BaseModel):
    company_id: int = 1
    generation_id: int = 1
    language: str = "te"
    source_text: str = "3KW సోలార్ రూఫ్‌టాప్ సిస్టమ్ - ఆంధ్రా ప్రదేశ్"
    rendered_ocr_text: str = "3KW సోలార్ రూఫ్‌టాప్ సిస్టమ్ - ఆంధ్రా ప్రదేశ్"


@router.get("/dashboard")
def get_meta_dashboard(
    company_id: int = Query(default=1),
    db: Session = Depends(get_db)
):
    """
    Returns Supreme Admin Meta Ads Dashboard KPIs & Lead Funnel Metrics.
    """
    return get_meta_ads_dashboard_kpis(db, company_id)


@router.get("/connections")
def get_meta_connections(
    company_id: int = Query(default=1),
    db: Session = Depends(get_db)
):
    """
    Returns connection health and asset discovery for Ad Account act_560062103113819.
    Zero sensitive tokens exposed.
    """
    from app.services.meta_account_connection_service import get_meta_connection_dashboard_status
    return get_meta_connection_dashboard_status(db, company_id)


@router.get("/campaigns")
def get_campaigns_list(
    company_id: int = Query(default=1),
    db: Session = Depends(get_db)
):
    """
    Fetch all synchronized Meta campaigns for company.
    """
    rows = db.execute(text("""
        SELECT campaign_id, account_id, name, objective, status, daily_budget, updated_at
        FROM meta_campaigns
        WHERE company_id = :cid
        ORDER BY updated_at DESC
    """), {"cid": company_id}).fetchall()

    campaigns = [
        {
            "campaign_id": r[0],
            "account_id": r[1],
            "name": r[2],
            "objective": r[3],
            "status": r[4],
            "daily_budget_inr": float(r[5] or 1000.0),
            "spend_today_inr": 0.0,
            "impressions": 0,
            "reach": 0,
            "clicks": 0,
            "leads": 0,
            "updated_at": str(r[6])
        }
        for r in rows
    ]

    return {
        "company_id": company_id,
        "total_campaigns_count": len(campaigns),
        "campaigns": campaigns
    }


@router.get("/campaigns/{campaign_id}")
def get_campaign_detail(
    campaign_id: str,
    company_id: int = Query(default=1),
    db: Session = Depends(get_db)
):
    """
    Fetch detailed performance overview and ad sets under target campaign.
    """
    row = db.execute(text("""
        SELECT campaign_id, account_id, name, objective, status, daily_budget, updated_at
        FROM meta_campaigns
        WHERE company_id = :cid AND campaign_id = :camp_id
    """), {"cid": company_id, "camp_id": campaign_id}).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail=f"Campaign {campaign_id} not found.")

    adsets = db.execute(text("""
        SELECT adset_id, name, status, daily_budget
        FROM meta_adsets
        WHERE company_id = :cid AND campaign_id = :camp_id
    """), {"cid": company_id, "camp_id": campaign_id}).fetchall()

    return {
        "campaign": {
            "campaign_id": row[0],
            "account_id": row[1],
            "name": row[2],
            "objective": row[3],
            "status": row[4],
            "daily_budget_inr": float(row[5] or 1000.0),
            "spend_inr": 0.0,
            "impressions": 0,
            "leads": 0,
            "updated_at": str(row[6])
        },
        "adsets_count": len(adsets),
        "adsets": [{"adset_id": a[0], "name": a[1], "status": a[2]} for a in adsets]
    }


@router.get("/adsets")
def get_adsets_list(
    company_id: int = Query(default=1),
    db: Session = Depends(get_db)
):
    """
    Fetch all synchronized Meta Ad Sets.
    """
    rows = db.execute(text("""
        SELECT adset_id, campaign_id, name, status, daily_budget
        FROM meta_adsets
        WHERE company_id = :cid
    """), {"cid": company_id}).fetchall()

    return {
        "company_id": company_id,
        "adsets": [{"adset_id": r[0], "campaign_id": r[1], "name": r[2], "status": r[3]} for r in rows]
    }


@router.get("/ads")
def get_ads_list(
    company_id: int = Query(default=1),
    db: Session = Depends(get_db)
):
    """
    Fetch all synchronized Meta Ads.
    """
    rows = db.execute(text("""
        SELECT ad_id, adset_id, campaign_id, name, creative_id, status
        FROM meta_ads
        WHERE company_id = :cid
    """), {"cid": company_id}).fetchall()

    return {
        "company_id": company_id,
        "ads": [{"ad_id": r[0], "adset_id": r[1], "campaign_id": r[2], "name": r[3], "status": r[5]} for r in rows]
    }


@router.get("/creatives")
def get_creatives_library(
    company_id: int = Query(default=1),
    db: Session = Depends(get_db)
):
    """
    Fetch all generated and saved creative assets.
    """
    rows = db.execute(text("""
        SELECT id, concept_name, aspect_ratio, resolution, provider_name, image_url_or_path, quality_score, decision_status, created_at
        FROM creative_generations
        WHERE company_id = :cid
        ORDER BY id DESC
    """), {"cid": company_id}).fetchall()

    return {
        "company_id": company_id,
        "creatives_count": len(rows),
        "creatives": [
            {
                "id": r[0],
                "concept_name": r[1],
                "aspect_ratio": r[2],
                "resolution": r[3],
                "provider": r[4],
                "path": r[5],
                "quality_score": r[6],
                "status": r[7],
                "created_at": str(r[8])
            }
            for r in rows
        ]
    }


@router.get("/leads")
def get_meta_leads_attribution_list(
    company_id: int = Query(default=1),
    db: Session = Depends(get_db)
):
    """
    Fetch Meta Leads attributed to crm_leads.
    """
    rows = db.execute(text("""
        SELECT m.meta_lead_id, m.lead_id, m.meta_campaign_name, m.meta_adset_name, c.name, c.phone, c.city, c.created_at
        FROM meta_leads_attribution m
        JOIN crm_leads c ON m.lead_id = c.id
        WHERE m.company_id = :cid
        ORDER BY m.id DESC
    """), {"cid": company_id}).fetchall()

    return {
        "company_id": company_id,
        "leads_count": len(rows),
        "leads": [
            {
                "meta_lead_id": r[0],
                "crm_lead_id": r[1],
                "campaign_name": r[2],
                "adset_name": r[3],
                "name": r[4],
                "phone": r[5],
                "city": r[6],
                "created_at": str(r[7])
            }
            for r in rows
        ]
    }


@router.get("/insights")
def get_meta_insights(
    company_id: int = Query(default=1),
    db: Session = Depends(get_db)
):
    """
    Returns Meta Ads performance & comparison insights.
    """
    return get_meta_ads_dashboard_kpis(db, company_id)


@router.get("/budget")
def get_meta_budget_status(
    company_id: int = Query(default=1),
    db: Session = Depends(get_db)
):
    """
    Returns Budget & Spend Center alerts.
    """
    return evaluate_meta_budget_alerts(db, company_id)


@router.get("/approvals")
def get_approval_queue(
    company_id: int = Query(default=1),
    db: Session = Depends(get_db)
):
    """
    Fetch pending and historical Two-Step Approval Requests.
    """
    rows = db.execute(text("""
        SELECT id, requested_by, action_type, target_object_type, target_object_id, risk_level, status, created_at
        FROM meta_action_requests
        WHERE company_id = :cid
        ORDER BY id DESC
    """), {"cid": company_id}).fetchall()

    return {
        "company_id": company_id,
        "approval_requests_count": len(rows),
        "requests": [
            {
                "id": r[0],
                "requested_by": r[1],
                "action_type": r[2],
                "target_object_type": r[3],
                "target_object_id": r[4],
                "risk_level": r[5],
                "status": r[6],
                "created_at": str(r[7])
            }
            for r in rows
        ]
    }


@router.post("/approvals/request")
def submit_approval_request(
    data: ActionRequestInput,
    db: Session = Depends(get_db)
):
    """
    Submit a write operation request to the Two-Step Approval Queue.
    """
    return create_action_request(
        db=db,
        company_id=data.company_id,
        requested_by=data.requested_by,
        action_type=data.action_type,
        target_object_type=data.target_object_type,
        target_object_id=data.target_object_id,
        current_value=data.current_value or {},
        proposed_value=data.proposed_value or {},
        reason=data.reason
    )


@router.post("/approvals/{request_id}/approve")
def execute_approval_request(
    request_id: int,
    approved_by: str = Query(default="MR10001"),
    db: Session = Depends(get_db)
):
    """
    Supreme Admin approves and executes a queued Meta write operation.
    """
    return approve_and_execute_action(db, request_id, approved_by)


@router.post("/multilingual-qa")
def run_multilingual_qa(
    data: MultilingualQARequest,
    db: Session = Depends(get_db)
):
    """
    Runs multilingual copy, typography, and OCR QA validation (English, Telugu, Hindi).
    """
    return evaluate_creative_multilingual_qa(
        db=db,
        company_id=data.company_id,
        generation_id=data.generation_id,
        language=data.language,
        source_text=data.source_text,
        rendered_ocr_text=data.rendered_ocr_text
    )


@router.get("/reports")
def export_meta_report(
    report_type: str = Query(default="CAMPAIGN_ROI"),
    export_format: str = Query(default="CSV"),
    company_id: int = Query(default=1),
    db: Session = Depends(get_db)
):
    """
    Generate PDF/Excel/CSV performance and attribution report.
    """
    return generate_meta_ads_export_report(db, company_id, report_type, export_format)


@router.get("/audit")
def get_audit_trail(
    company_id: int = Query(default=1),
    db: Session = Depends(get_db)
):
    """
    Fetch immutable audit log trail for Meta Ads Admin Control Center.
    """
    rows = db.execute(text("""
        SELECT id, user_id, user_role, action, target_object, result_status, graph_api_trace_id, created_at
        FROM meta_audit_logs
        WHERE company_id = :cid
        ORDER BY id DESC LIMIT 50
    """), {"cid": company_id}).fetchall()

    return {
        "company_id": company_id,
        "audit_logs_count": len(rows),
        "audit_logs": [
            {
                "id": r[0],
                "user_id": r[1],
                "user_role": r[2],
                "action": r[3],
                "target_object": r[4],
                "result_status": r[5],
                "trace_id": r[6],
                "created_at": str(r[7])
            }
            for r in rows
        ]
    }


@router.post("/sync")
def trigger_meta_sync(
    company_id: int = Query(default=1),
    db: Session = Depends(get_db)
):
    """
    Triggers manual synchronization of Meta Ad Account assets.
    """
    return execute_meta_account_sync(db, company_id)


@router.get("/forensic-reconciliation")
def get_forensic_reconciliation(
    company_id: int = Query(default=1),
    db: Session = Depends(get_db)
):
    """
    Returns full read-only live Graph API forensic reconciliation audit and proposed cleanup plan.
    """
    from app.services.meta_forensic_service import get_meta_live_forensic_inventory
    return get_meta_live_forensic_inventory(db, company_id)


@router.post("/execute-real-ad-pipeline")
def execute_real_ad_pipeline_endpoint(
    company_id: int = Query(default=1),
    vertical: str = Query(default="SOLAR"),
    product_name: str = Query(default="3KW Rooftop Solar System"),
    language: str = Query(default="en"),
    db: Session = Depends(get_db)
):
    """
    Executes the complete 11-step Real Meta Ad Creation & Publication Pipeline in PAUSED status.
    """
    from app.services.meta_real_ad_pipeline_service import execute_full_real_ad_creation_pipeline
    return execute_full_real_ad_creation_pipeline(db, company_id, vertical, product_name, language)
