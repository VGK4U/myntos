"""
Tenant Single Page Landing Site & AI Content Generator Endpoints
DC Protocol (Oct 2026):
- Single Page Content Management restricted to Staff/Admin on Company Profile page
- AI Prompt & Text layout generator
- Image Change Controls (Logo, Banner, Gallery Images) & Video Links (YouTube/Vimeo/MP4)
- Dual Contact Numbers, Official Website, Email, and Google Maps embed
- Public Unauthenticated Landing View API via myntreal.com/{tenant_short_code}
"""

import logging
import re
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Path, Body, status
from sqlalchemy.orm import Session
from sqlalchemy import text, or_, and_

from app.core.database import get_db
from app.models.staff import StaffEmployee
from app.models.staff_accounts import AssociatedCompany
from app.models.platform_b2b import PlatformClient
from app.models.tenant_landing_page import TenantLandingPage
from app.api.v1.endpoints.staff_auth import get_current_staff_user
from app.utils.phone_otp import normalize_phone_10
from app.utils.name_formatter import format_proper_name

logger = logging.getLogger(__name__)

router = APIRouter()
public_router = APIRouter()


def _get_company_id(current_user: StaffEmployee) -> int:
    company_id = getattr(current_user, 'base_company_id', None) or getattr(current_user, 'company_id', None)
    if not company_id:
        raise HTTPException(status_code=400, detail="Tenant context missing for user.")
    return company_id


def _get_or_create_landing_page(db: Session, company_id: int) -> TenantLandingPage:
    landing = db.query(TenantLandingPage).filter(TenantLandingPage.company_id == company_id).first()
    if not landing:
        company = db.query(AssociatedCompany).filter(AssociatedCompany.id == company_id).first()
        comp_name = company.company_name if company else "SaaS Partner"
        comp_code = company.company_code if company else f"TENANT_{company_id}"

        # Clean short code (e.g., TENANT_95 -> TENANT95 or extract suffix)
        short_code = comp_code.replace("COMP_", "").replace("TENANT_", "").upper()

        landing = TenantLandingPage(
            company_id=company_id,
            tenant_short_code=short_code,
            hero_title=f"Welcome to {comp_name}",
            hero_subtitle=f"Leading provider of premium products and customized solutions.",
            primary_phone=company.phone if company else "",
            official_email=company.email if company else "",
            official_website=company.website if company else "",
            address=company.address if company else "",
            logo_image_url=company.logo_path if company else "",
            banner_image_url="",
            gallery_images=[],
            video_links=[],
            generated_content={
                "about": f"{comp_name} is committed to excellence, providing industry-leading services and customer satisfaction.",
                "services": ["Custom Installation & Setup", "24/7 Priority Support", "Certified Quality Guarantee"],
                "highlights": ["100% Reliable", "Dedicated Customer Service", "Transparent Pricing"]
            },
            is_published=True
        )
        db.add(landing)
        db.commit()
        db.refresh(landing)

    return landing


def _generate_ai_landing_content(prompt_text: str, company_name: str) -> Dict[str, Any]:
    """
    AI Content Generator Service:
    Parses raw text/prompt instructions and structures landing page sections.
    """
    p_clean = prompt_text.strip()
    words = p_clean.split()
    
    hero_t = f"Innovating Solutions with {company_name}"
    if len(words) > 3:
        hero_t = " ".join(words[:6]).title()

    hero_sub = p_clean[:180] + ("..." if len(p_clean) > 180 else "")

    # Extract bullet items or sentences
    sentences = [s.strip() for s in re.split(r'[.\n;]', p_clean) if s.strip()]
    
    services = sentences[:4] if len(sentences) >= 2 else [
        "End-to-End Project Execution",
        "Expert Inspection & Consultation",
        "Lifetime Support & Maintenance"
    ]

    highlights = [
        "ISO Certified Operational Excellence",
        "Fast Turnaround & Rapid Delivery",
        "Transparent & Verified Pricing Model"
    ]

    return {
        "hero_title": hero_t,
        "hero_subtitle": hero_sub,
        "generated_content": {
            "about": p_clean if len(p_clean) > 50 else f"{company_name} is dedicated to delivering cutting-edge solutions customized to client requirements.",
            "services": services,
            "highlights": highlights,
            "cta_heading": "Ready to Get Started?",
            "cta_subtext": "Contact our team today for a free consultation and project quote."
        }
    }


# ===================== STAFF MANAGEMENT ENDPOINTS =====================

@router.get("/landing-page", summary="Get tenant single page landing config")
def get_tenant_landing_page(
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """
    Fetch single page configuration for staff company profile.
    """
    company_id = _get_company_id(current_user)
    landing = _get_or_create_landing_page(db, company_id)

    return {
        "success": True,
        "data": landing.to_dict()
    }


@router.post("/landing-page/generate-ai", summary="Generate single page content from AI prompt")
def generate_ai_landing_page_content(
    payload: Dict[str, Any] = Body(...),
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """
    Generate landing page HTML content from raw user prompt / text.
    Restricted strictly to Staff/Admin.
    """
    company_id = _get_company_id(current_user)
    landing = _get_or_create_landing_page(db, company_id)

    prompt = (payload.get('ai_prompt') or '').strip()
    if not prompt:
        raise HTTPException(status_code=400, detail="Prompt text is required for AI content generation.")

    company = db.query(AssociatedCompany).filter(AssociatedCompany.id == company_id).first()
    comp_name = company.company_name if company else "Our Company"

    ai_result = _generate_ai_landing_content(prompt, comp_name)

    landing.ai_prompt = prompt
    landing.hero_title = ai_result['hero_title']
    landing.hero_subtitle = ai_result['hero_subtitle']
    landing.generated_content = ai_result['generated_content']
    landing.updated_by_id = current_user.id

    db.commit()
    db.refresh(landing)

    return {
        "success": True,
        "message": "Landing page content generated successfully with AI.",
        "data": landing.to_dict()
    }


@router.patch("/landing-page", summary="Update tenant single page landing site & media")
def update_tenant_landing_page(
    payload: Dict[str, Any] = Body(...),
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """
    Update image controls (Logo, Banner, Gallery), Video Links, Dual Contact numbers,
    Official Website, Address, and publish state.
    """
    company_id = _get_company_id(current_user)
    landing = _get_or_create_landing_page(db, company_id)

    if 'tenant_short_code' in payload and payload['tenant_short_code']:
        sc = payload['tenant_short_code'].strip().upper().replace(" ", "")
        # Check uniqueness
        existing = db.query(TenantLandingPage).filter(
            TenantLandingPage.tenant_short_code == sc,
            TenantLandingPage.company_id != company_id
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail=f"Short code '{sc}' is already in use by another tenant.")
        landing.tenant_short_code = sc

    if 'hero_title' in payload:
        landing.hero_title = (payload['hero_title'] or '').strip() or landing.hero_title
    if 'hero_subtitle' in payload:
        landing.hero_subtitle = (payload['hero_subtitle'] or '').strip() or landing.hero_subtitle
    if 'ai_prompt' in payload:
        landing.ai_prompt = (payload['ai_prompt'] or '').strip() or None
    if 'generated_content' in payload and isinstance(payload['generated_content'], dict):
        landing.generated_content = payload['generated_content']

    # Media Asset Updates
    if 'logo_image_url' in payload:
        landing.logo_image_url = (payload['logo_image_url'] or '').strip() or None
    if 'banner_image_url' in payload:
        landing.banner_image_url = (payload['banner_image_url'] or '').strip() or None
    if 'gallery_images' in payload and isinstance(payload['gallery_images'], list):
        landing.gallery_images = [img for img in payload['gallery_images'] if isinstance(img, str) and img.strip()]
    if 'video_links' in payload and isinstance(payload['video_links'], list):
        landing.video_links = [v for v in payload['video_links'] if isinstance(v, str) and v.strip()]

    # Contact Info Updates
    if 'primary_phone' in payload:
        p1 = (payload['primary_phone'] or '').strip()
        landing.primary_phone = normalize_phone_10(p1) or p1 if p1 else None
    if 'secondary_phone' in payload:
        p2 = (payload['secondary_phone'] or '').strip()
        landing.secondary_phone = normalize_phone_10(p2) or p2 if p2 else None
    if 'official_website' in payload:
        landing.official_website = (payload['official_website'] or '').strip() or None
    if 'official_email' in payload:
        landing.official_email = (payload['official_email'] or '').strip() or None
    if 'address' in payload:
        landing.address = (payload['address'] or '').strip() or None
    if 'google_maps_url' in payload:
        landing.google_maps_url = (payload['google_maps_url'] or '').strip() or None
    if 'theme_color' in payload and payload['theme_color']:
        landing.theme_color = payload['theme_color'].strip()
    if 'is_published' in payload:
        landing.is_published = bool(payload['is_published'])

    landing.updated_by_id = current_user.id
    db.commit()
    db.refresh(landing)

    return {
        "success": True,
        "message": "Tenant landing page configuration updated successfully.",
        "data": landing.to_dict()
    }


# ===================== PUBLIC UNAUTHENTICATED ENDPOINTS =====================

@public_router.get("/public/tenant/{tenant_short_code}/landing", summary="Public tenant landing page view")
def get_public_tenant_landing(
    tenant_short_code: str = Path(...),
    db: Session = Depends(get_db)
):
    """
    Public unauthenticated view for myntreal.com/{tenant_short_code} landing site.
    """
    sc = tenant_short_code.strip().upper()

    landing = db.query(TenantLandingPage).filter(
        TenantLandingPage.tenant_short_code == sc,
        TenantLandingPage.is_published == True
    ).first()

    if not landing:
        # Try fallback matching by company_code
        company = db.query(AssociatedCompany).filter(
            or_(
                AssociatedCompany.company_code.ilike(sc),
                AssociatedCompany.company_code.ilike(f"TENANT_{sc}"),
                AssociatedCompany.company_name.ilike(f"%{sc}%")
            )
        ).first()
        if company:
            landing = _get_or_create_landing_page(db, company.id)
        else:
            raise HTTPException(status_code=404, detail=f"Tenant landing page for '{sc}' not found or not published.")

    company = db.query(AssociatedCompany).filter(AssociatedCompany.id == landing.company_id).first()
    comp_name = company.company_name if company else "SaaS Partner"

    res = landing.to_dict()
    res['company_name'] = comp_name
    return {
        "success": True,
        "data": res
    }
