"""
Production Creative Studio API Endpoints (Phase 2H)
Endpoints for creative concepts discovery, multi-format asset rendering, and brand creative benchmark.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Dict, Any, List, Optional

from app.core.database import get_db
from app.services.creative_intelligence_engine import get_vertical_creative_concepts
from app.services.creative_studio_service import generate_production_ad_creative, generate_solar_real_brand_benchmark

router = APIRouter(prefix="/crm/creatives", tags=["Creative AI Studio & Ad Composition"])


class BuildCreativeAssetRequest(BaseModel):
    company_id: int = 1
    vertical: str = "SOLAR"
    product_name: str = "3KW Rooftop Solar System"
    target_location: str = "Andhra Pradesh"
    concept_id: str = "PREMIUM_HOME_SOLAR"
    aspect_ratio: str = "1:1"
    headline: Optional[str] = "3KW Solar Rooftop System - Andhra Pradesh"
    primary_text: Optional[str] = "Upgrade to 3KW Rooftop Solar. High efficiency panels with long-term warranty support."
    cta_type: Optional[str] = "LEARN_MORE"


@router.get("/concepts")
def get_concepts_for_vertical(
    vertical: str = Query(default="SOLAR"),
    product_name: str = Query(default="3KW Rooftop Solar System"),
    location: str = Query(default="Andhra Pradesh")
):
    """
    Fetch structured creative concepts for specified vertical.
    """
    return {
        "vertical": vertical,
        "product_name": product_name,
        "location": location,
        "concepts": get_vertical_creative_concepts(vertical, product_name, location)
    }


@router.post("/build-studio-asset")
def build_studio_creative_asset(
    data: BuildCreativeAssetRequest,
    db: Session = Depends(get_db)
):
    """
    Build a production-quality ad creative asset (1:1, 4:5, 9:16, 16:9) with brand logo and typography.
    """
    return generate_production_ad_creative(
        db=db,
        company_id=data.company_id,
        vertical=data.vertical,
        product_name=data.product_name,
        target_location=data.target_location,
        concept_id=data.concept_id,
        aspect_ratio=data.aspect_ratio,
        headline=data.headline or "3KW Solar Rooftop System - Andhra Pradesh",
        primary_text=data.primary_text or "Upgrade to 3KW Rooftop Solar.",
        cta_type=data.cta_type or "LEARN_MORE"
    )


@router.get("/benchmark-solar-test")
def run_solar_brand_creative_benchmark(
    company_id: int = Query(default=1),
    db: Session = Depends(get_db)
):
    """
    Generates 9 production-quality test creatives for Solar 3KW AP benchmark (1:1, 4:5, 9:16 across 3 concepts).
    """
    return generate_solar_real_brand_benchmark(db, company_id)
