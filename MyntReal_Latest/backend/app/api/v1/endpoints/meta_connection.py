"""
Meta Connection & Asset Verification Endpoint (Phase 2B/2C)
Provides Meta connection dashboard status, token syncing, and real asset reading.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Dict, Any

from app.core.database import get_db
from app.services.meta_account_connection_service import (
    get_meta_connection_dashboard_status,
    read_real_meta_account_assets
)
from app.services.facebook_leads_service import facebook_leads_service

router = APIRouter(prefix="/meta", tags=["Meta Connection & Real Asset Verification"])


class ConnectTokenRequest(BaseModel):
    user_token: str
    company_id: int = 1


@router.get("/connection-status")
def get_meta_connection_status(
    company_id: int = Query(default=1),
    db: Session = Depends(get_db)
):
    """
    Get Meta Connection Dashboard status, permissions audit, and encryption status.
    """
    return get_meta_connection_dashboard_status(db, company_id)


@router.get("/read-assets")
def read_meta_real_assets(
    company_id: int = Query(default=1),
    db: Session = Depends(get_db)
):
    """
    Read-only inspection of real connected Meta assets (Ad Accounts, Lead Forms, Campaigns, Insights).
    """
    return read_real_meta_account_assets(db, company_id)


@router.post("/connect-token")
def connect_meta_token(
    data: ConnectTokenRequest,
    db: Session = Depends(get_db)
):
    """
    Connect a new Meta Page or User Access Token with encrypted storage at rest (STRICT_ENCRYPTED_CREDS_ONLY = True).
    """
    if not data.user_token or len(data.user_token) < 10:
        raise HTTPException(status_code=400, detail="Invalid token provided")

    result = facebook_leads_service.sync_pages_from_user_token(
        user_token=data.user_token,
        db=db,
        company_id=data.company_id
    )

    return {
        "status": "CONNECTED — REAL META ACCOUNT VERIFIED",
        "synced_pages_count": result.get("total", 0),
        "stored_pages_count": result.get("stored", 0),
        "details": result
    }


@router.get("/first-campaign-readiness")
def get_first_campaign_readiness_status(
    company_id: int = Query(default=1),
    db: Session = Depends(get_db)
):
    """
    Evaluates 18 pre-publish risk & validation checks for the first real Meta campaign.
    """
    from app.services.first_campaign_readiness_service import evaluate_first_campaign_readiness
    return evaluate_first_campaign_readiness(db, company_id)


@router.post("/create-first-campaign")
def create_first_controlled_meta_campaign(
    company_id: int = Query(default=1),
    db: Session = Depends(get_db)
):
    """
    Executes sequential controlled creation of the first Meta campaign in PAUSED status with read-back verification.
    """
    from app.services.meta_live_creation_service import execute_first_live_meta_campaign_creation
    return execute_first_live_meta_campaign_creation(db, company_id)


@router.get("/asset-mapping-preflight")
def get_asset_mapping_preflight_report(
    company_id: int = Query(default=1),
    db: Session = Depends(get_db)
):
    """
    Executes complete Phase 2G Real Meta Asset Mapping & Pre-Flight verification.
    """
    from app.services.meta_asset_mapping_service import evaluate_phase2g_preflight_checks
    return evaluate_phase2g_preflight_checks(db, company_id)
