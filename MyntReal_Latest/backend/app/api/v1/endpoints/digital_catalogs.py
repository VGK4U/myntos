"""
Digital Catalog API Endpoints — MyntOS Single-Page Digital Catalog Platform
DC Protocol Compliant:
- Multi-company and multi-tenant scoping
- Public catalog viewing with multilingual support (en, te, hi, ta) and fallback
- Lead tracking & referral code resolution
- Staff catalog library, section builder, item manager
- S3 media uploads (AWS S3 myntreal-media-vault)
- Gemini AI copy drafting
- WhatsApp dispatch (Web link + PDF brochure delivery)
"""

import os
import sys
import uuid
import json
import logging
import re
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta

from fastapi import (
    APIRouter, Depends, HTTPException, status, Query, Body, 
    UploadFile, File, Form, Request
)
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import text, or_, and_, desc

# Dynamic path resolution (System Rule 1)
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.abspath(os.path.join(current_dir, '..', '..', '..'))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.core.database import get_db
from app.models.base import get_indian_time
from app.models.digital_catalog import (
    DigitalCatalog, CatalogSection, CatalogItem, CatalogLeadSend
)
from app.models.staff import StaffEmployee
from app.models.crm import CRMLead, CRMLeadNote
from app.models.staff_accounts import AssociatedCompany
from app.api.v1.endpoints.staff_auth import get_current_staff_user
from app.services.s3_storage import s3_storage_service

logger = logging.getLogger("digital_catalogs_api")

router = APIRouter()


# ── Role & Authoring Permission Helpers ─────────────────────────────────────

def _is_catalog_author(user: StaffEmployee) -> bool:
    """
    Validates whether the authenticated staff member has authoring / administrative privileges.
    Authorized: Leadership / EA / Admin / Managers (hierarchy_level >= 60 or administrative roles, or VGK4U superadmin).
    """
    if not user:
        return False
    if user.id == 1 or user.emp_code == "MR10001" or getattr(user, 'staff_type', '') in ['VGK4U', 'VGK4U Supreme']:
        return True
    h_level = getattr(user, 'hierarchy_level', 0) or 0
    if h_level >= 60:
        return True
    
    role_name = str(getattr(user, 'role', '') or getattr(user, 'system_role', '') or '').lower()
    allowed_roles = {
        'admin', 'super_admin', 'tenant_admin', 'saas_segment_admin', 
        'manager', 'leadership_role', 'key_leadership', 'ea', 'vgk4u',
        'managing_director', 'director', 'general_manager'
    }
    return role_name in allowed_roles


# ── Pydantic Request Schemas ────────────────────────────────────────────────

class CatalogCreateRequest(BaseModel):
    title: str = Field(..., min_length=2, max_length=255)
    segment_code: str = Field(..., max_length=50)
    slug: str = Field(..., min_length=2, max_length=120)
    subtitle: Optional[str] = None
    summary: Optional[str] = None
    hero_media_url: Optional[str] = None
    catalog_type: str = "SINGLE_PAGE"
    status: str = "published"
    is_active: bool = True
    is_featured: bool = False
    sort_order: int = 0
    seo_title: Optional[str] = None
    seo_description: Optional[str] = None
    seo_keywords: Optional[str] = None
    theme_config: Dict[str, Any] = Field(default_factory=dict)
    default_language: str = "en"
    active_languages: List[str] = Field(default_factory=lambda: ["en", "te", "hi", "ta"])
    pdf_brochure_url: Optional[str] = None


class CatalogUpdateRequest(BaseModel):
    title: Optional[str] = None
    subtitle: Optional[str] = None
    summary: Optional[str] = None
    hero_media_url: Optional[str] = None
    catalog_type: Optional[str] = None
    status: Optional[str] = None
    is_active: Optional[bool] = None
    is_featured: Optional[bool] = None
    sort_order: Optional[int] = None
    seo_title: Optional[str] = None
    seo_description: Optional[str] = None
    seo_keywords: Optional[str] = None
    theme_config: Optional[Dict[str, Any]] = None
    default_language: Optional[str] = None
    active_languages: Optional[List[str]] = None
    pdf_brochure_url: Optional[str] = None


class SectionCreateRequest(BaseModel):
    section_type: str = Field(..., max_length=50)
    section_key: str = Field(..., max_length=50)
    title: Optional[str] = None
    subtitle: Optional[str] = None
    content_variants: Dict[str, Any] = Field(default_factory=dict)
    media_gallery: List[Dict[str, Any]] = Field(default_factory=list)
    configuration: Dict[str, Any] = Field(default_factory=dict)
    sort_order: int = 0
    is_visible: bool = True


class SectionUpdateRequest(BaseModel):
    section_type: Optional[str] = None
    section_key: Optional[str] = None
    title: Optional[str] = None
    subtitle: Optional[str] = None
    content_variants: Optional[Dict[str, Any]] = None
    media_gallery: Optional[List[Dict[str, Any]]] = None
    configuration: Optional[Dict[str, Any]] = None
    sort_order: Optional[int] = None
    is_visible: Optional[bool] = None


class ItemCreateRequest(BaseModel):
    item_type: str = "PRODUCT"
    item_code: Optional[str] = None
    title: str = Field(..., min_length=2, max_length=255)
    subtitle: Optional[str] = None
    specifications: List[Dict[str, Any]] = Field(default_factory=list)
    pricing: Dict[str, Any] = Field(default_factory=dict)
    media_urls: List[str] = Field(default_factory=list)
    video_url: Optional[str] = None
    content_variants: Dict[str, Any] = Field(default_factory=dict)
    badges: List[str] = Field(default_factory=list)
    sort_order: int = 0
    is_featured: bool = False
    is_active: bool = True


class ItemUpdateRequest(BaseModel):
    item_type: Optional[str] = None
    item_code: Optional[str] = None
    title: Optional[str] = None
    subtitle: Optional[str] = None
    specifications: Optional[List[Dict[str, Any]]] = None
    pricing: Optional[Dict[str, Any]] = None
    media_urls: Optional[List[str]] = None
    video_url: Optional[str] = None
    content_variants: Optional[Dict[str, Any]] = None
    badges: Optional[List[str]] = None
    sort_order: Optional[int] = None
    is_featured: Optional[bool] = None
    is_active: Optional[bool] = None


class WhatsAppDispatchRequest(BaseModel):
    lead_id: Optional[int] = None
    partner_id: Optional[int] = None
    recipient_phone: str = Field(..., min_length=10, max_length=20)
    recipient_name: Optional[str] = None
    language_code: str = "en"
    delivery_method: str = "web_link"  # web_link, pdf_document, both
    custom_note: Optional[str] = None


class InquiryRequest(BaseModel):
    name: str
    phone: str
    email: Optional[str] = None
    notes: Optional[str] = None
    share_ref_code: Optional[str] = None
    selected_language: Optional[str] = "en"


class AIDraftRequest(BaseModel):
    vertical: str
    section_type: str
    topic: str
    prompt: Optional[str] = None
    target_languages: List[str] = Field(default_factory=lambda: ["en", "te", "hi", "ta"])


def _get_catalog_branding(catalog: DigitalCatalog) -> dict:
    """Resolve vertical-specific brand identity, logo, and contacts."""
    seg = (catalog.segment_code or "").upper()
    if seg == "ETC_TRAINING":
        return {
            "platform_name": "EVolution Training Centre",
            "tagline": "Evolve & Power Your Future — EV Technology & Entrepreneurship Certifications",
            "logo_url": "/public/images/etc_training/evolution_training_centre_logo.png",
            "primary_contact_phone": "+91 858585 2738",
            "whatsapp_business_number": "918585852738",
            "support_email": "contact@myntreal.com"
        }
    elif seg == "SOLAR":
        return {
            "platform_name": "MYNTREAL Har Ghar Solar",
            "tagline": "MYNTREAL – Redefining Future",
            "logo_url": "/public/images/myntreal-har-ghar-solar-nav.png",
            "primary_contact_phone": "+91 858585 2738",
            "whatsapp_business_number": "918585852738",
            "support_email": "support@myntreal.com"
        }
    return {
        "platform_name": catalog.title,
        "tagline": catalog.subtitle or "MYNTREAL – Redefining Future",
        "logo_url": "/public/vgk4u-logo.png",
        "primary_contact_phone": "+91 858585 2738",
        "whatsapp_business_number": "918585852738",
        "support_email": "support@myntreal.com"
    }


# ════════════════════════════════════════════════════════════════════════════
# 1. PUBLIC ENDPOINTS (Unauthenticated, Single-Page Responsive Web Catalog)
# ════════════════════════════════════════════════════════════════════════════

@router.get("/public/{category_slug}/{catalog_slug}")
def get_public_catalog_by_slug(
    category_slug: str,
    catalog_slug: str,
    lang: str = Query("en", pattern="^(en|te|hi|ta)$"),
    ref: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Public single-page web catalog viewer endpoint.
    Returns full catalog structure with localized sections, items, company branding, and contact channels.
    """
    # Look up catalog by slug
    catalog = db.query(DigitalCatalog).filter(
        DigitalCatalog.slug == catalog_slug,
        DigitalCatalog.is_active == True,
        DigitalCatalog.status == 'published'
    ).first()

    if not catalog:
        # Fallback 1: match catalog_slug against slug or segment_code
        cat_match = db.query(DigitalCatalog).filter(
            or_(
                DigitalCatalog.slug.ilike(f"%{catalog_slug}%"),
                DigitalCatalog.segment_code.ilike(catalog_slug.replace('-', '_'))
            ),
            DigitalCatalog.is_active == True,
            DigitalCatalog.status == 'published'
        ).first()

        # Fallback 2: search by category_slug against segment_code or slug
        if not cat_match:
            cat_match = db.query(DigitalCatalog).filter(
                or_(
                    DigitalCatalog.segment_code.ilike(category_slug.replace('-', '_')),
                    DigitalCatalog.slug.ilike(f"%{category_slug}%")
                ),
                DigitalCatalog.is_active == True,
                DigitalCatalog.status == 'published'
            ).first()

        if not cat_match:
            raise HTTPException(status_code=404, detail="Catalog not found or is no longer active.")
        catalog = cat_match

    # If referral code provided, record view in ledger
    attribution = None
    if ref and isinstance(ref, str):
        send_record = db.query(CatalogLeadSend).filter(CatalogLeadSend.share_ref_code == ref).first()
        if send_record:
            send_record.view_count += 1
            now_t = get_indian_time()
            if not send_record.first_viewed_at:
                send_record.first_viewed_at = now_t
            send_record.last_viewed_at = now_t
            db.commit()

            staff_name = "MyntReal Specialist"
            staff_ext = None
            if send_record.staff_id:
                staff = db.query(StaffEmployee).filter(StaffEmployee.id == send_record.staff_id).first()
                if staff:
                    staff_name = f"{staff.first_name} {staff.last_name or ''}".strip()
                    try:
                        from app.services.whatsapp_auto_service import resolve_staff_extension
                        staff_ext = resolve_staff_extension(db, staff.id, company_id=getattr(staff, 'base_company_id', 1))
                    except Exception:
                        pass

            attribution = {
                "ref_code": ref,
                "staff_name": staff_name,
                "extension": staff_ext,
                "recipient_name": send_record.recipient_name,
                "language_code": send_record.language_code
            }

    data = catalog.to_dict(include_sections=True, include_items=True, language=lang)
    data["attribution"] = attribution
    data["branding"] = _get_catalog_branding(catalog)
    return {"success": True, "catalog": data}


@router.get("/public/by-ref/{share_ref_code}")
def get_public_catalog_by_ref(
    share_ref_code: str,
    lang: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Resolves a catalog directly from a short referral / WhatsApp share code.
    Records view telemetry and returns catalog with localized content.
    """
    send_record = db.query(CatalogLeadSend).filter(CatalogLeadSend.share_ref_code == share_ref_code).first()
    if not send_record:
        raise HTTPException(status_code=404, detail="Shared link is invalid or expired.")

    catalog = db.query(DigitalCatalog).filter(DigitalCatalog.id == send_record.catalog_id).first()
    if not catalog or not catalog.is_active:
        raise HTTPException(status_code=404, detail="Catalog is no longer active.")

    selected_lang = lang or send_record.language_code or 'en'

    # Update view counts
    send_record.view_count += 1
    now_t = get_indian_time()
    if not send_record.first_viewed_at:
        send_record.first_viewed_at = now_t
    send_record.last_viewed_at = now_t
    db.commit()

    staff_name = "MyntReal Specialist"
    staff_ext = None
    if send_record.staff_id:
        staff = db.query(StaffEmployee).filter(StaffEmployee.id == send_record.staff_id).first()
        if staff:
            staff_name = f"{staff.first_name} {staff.last_name or ''}".strip()
            try:
                from app.services.whatsapp_auto_service import resolve_staff_extension
                staff_ext = resolve_staff_extension(db, staff.id, company_id=getattr(staff, 'base_company_id', 1))
            except Exception:
                pass

    data = catalog.to_dict(include_sections=True, include_items=True, language=selected_lang)
    data["attribution"] = {
        "ref_code": share_ref_code,
        "staff_name": staff_name,
        "extension": staff_ext,
        "recipient_name": send_record.recipient_name,
        "language_code": selected_lang
    }
    data["branding"] = _get_catalog_branding(catalog)
    return {"success": True, "catalog": data}


@router.post("/public/{catalog_id}/track-view")
def track_catalog_view(
    catalog_id: int,
    payload: Dict[str, Any] = Body(...),
    db: Session = Depends(get_db)
):
    """
    Logs dwell time, section impressions, or CTA clicks for public catalog viewers.
    """
    ref_code = payload.get("share_ref_code")
    if ref_code:
        send_record = db.query(CatalogLeadSend).filter(CatalogLeadSend.share_ref_code == ref_code).first()
        if send_record:
            send_record.last_viewed_at = get_indian_time()
            db.commit()
    return {"success": True}


@router.post("/public/{catalog_id}/inquire")
def submit_catalog_inquiry(
    catalog_id: int,
    payload: InquiryRequest,
    db: Session = Depends(get_db)
):
    """
    Public catalog lead inquiry.
    If share_ref_code exists, links inquiry to existing lead and appends a CRM note.
    """
    catalog = db.query(DigitalCatalog).filter(DigitalCatalog.id == catalog_id).first()
    if not catalog:
        raise HTTPException(status_code=404, detail="Catalog not found")

    note_body = (
        f"🌐 Web Catalog Inquiry: {catalog.title}\n"
        f"Name: {payload.name}\n"
        f"Phone: {payload.phone}\n"
        f"Email: {payload.email or 'N/A'}\n"
        f"Language: {payload.selected_language or 'en'}\n"
        f"Note: {payload.notes or 'Interested in solutions'}"
    )

    if payload.share_ref_code:
        send_record = db.query(CatalogLeadSend).filter(CatalogLeadSend.share_ref_code == payload.share_ref_code).first()
        if send_record and send_record.lead_id:
            crm_note = CRMLeadNote(
                lead_id=send_record.lead_id,
                note=note_body,
                created_by_id="CATALOG_WEB",
                created_by_type="system",
                created_at=get_indian_time()
            )
            db.add(crm_note)
            db.commit()
            return {"success": True, "message": "Inquiry attached to existing CRM lead profile."}

    logger.info(f"Public catalog inquiry received for catalog_id={catalog_id}: {payload.name} ({payload.phone})")
    return {"success": True, "message": "Thank you! Our specialist will contact you shortly."}


# ════════════════════════════════════════════════════════════════════════════
# 2. STAFF CMS & LIBRARY ENDPOINTS (All active staff authenticated)
# ════════════════════════════════════════════════════════════════════════════

@router.get("/library")
def get_staff_catalog_library(
    segment_code: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """
    Returns digital catalogs library for staff browsing, sharing, and administration.
    All active staff can view and search catalogs.
    """
    company_id = getattr(current_user, 'company_id', 4) or 4
    query = db.query(DigitalCatalog)

    # Filter by company or default 4
    query = query.filter(or_(DigitalCatalog.company_id == company_id, DigitalCatalog.company_id == 4))

    if segment_code:
        query = query.filter(DigitalCatalog.segment_code == segment_code.upper())

    if status_filter:
        query = query.filter(DigitalCatalog.status == status_filter)
    else:
        query = query.filter(DigitalCatalog.is_active == True)

    if search:
        s = f"%{search}%"
        query = query.filter(
            or_(
                DigitalCatalog.title.ilike(s),
                DigitalCatalog.subtitle.ilike(s),
                DigitalCatalog.slug.ilike(s),
                DigitalCatalog.segment_code.ilike(s)
            )
        )

    catalogs = query.order_by(DigitalCatalog.sort_order.asc(), DigitalCatalog.id.asc()).all()

    # Pre-fetch dispatches count per catalog
    catalog_ids = [c.id for c in catalogs]
    dispatches_stats = {}
    if catalog_ids:
        res = db.execute(text("""
            SELECT catalog_id, COUNT(*) as total_sends, COALESCE(SUM(view_count), 0) as total_views
            FROM catalog_lead_sends
            WHERE catalog_id = ANY(:cids)
            GROUP BY catalog_id
        """), {"cids": catalog_ids}).fetchall()
        for row in res:
            dispatches_stats[row[0]] = {"total_sends": row[1], "total_views": row[2]}

    result = []
    is_author = _is_catalog_author(current_user)

    for c in catalogs:
        d = c.to_dict(include_sections=False, include_items=False)
        stats = dispatches_stats.get(c.id, {"total_sends": 0, "total_views": 0})
        d["stats"] = stats
        result.append(d)

    return {
        "success": True,
        "catalogs": result,
        "user_permissions": {
            "can_author": is_author,
            "can_dispatch": True,
            "staff_id": current_user.id,
            "staff_name": f"{current_user.first_name} {current_user.last_name or ''}".strip()
        }
    }


def _format_dispatch_record(s: CatalogLeadSend, staff_map: dict) -> dict:
    sd = s.to_dict()
    # Sender Staff Info
    if s.staff_id and s.staff_id in staff_map:
        st = staff_map[s.staff_id]
        s_name = f"{st.first_name or ''} {st.last_name or ''}".strip() or st.emp_code or "Staff Member"
        sd["staff_name"] = s_name
        sd["staff_code"] = st.emp_code or ""
        sd["staff_designation"] = st.designation or st.staff_type or "Sales Specialist"
        sd["staff_email"] = st.email or ""
    else:
        sd["staff_name"] = "System Administrator" if s.staff_id == 1 else "Staff Member"
        sd["staff_code"] = "MR10001" if s.staff_id == 1 else ""
        sd["staff_designation"] = "Platform Administrator" if s.staff_id == 1 else "Staff"
        sd["staff_email"] = ""

    # Catalog Model Info
    if s.catalog:
        sd["catalog_title"] = s.catalog.title
        sd["segment_code"] = s.catalog.segment_code
        sd["catalog_slug"] = s.catalog.slug
    else:
        sd["catalog_title"] = "Digital Catalog"
        sd["segment_code"] = "SOLAR"
        sd["catalog_slug"] = "commercial-residential-solar"

    # Resolved Tracked Live Link
    ref = sd.get("share_ref_code") or ""
    cat_slug = sd.get("catalog_slug") or ""
    seg_code = sd.get("segment_code") or "SOLAR"

    if seg_code == "HUB_PRICING" or cat_slug == "hub-ev-pricing":
        sd["tracked_url"] = f"/catalog/hub-ev-pricing?ref={ref}"
    elif seg_code == "EV_B2C" or cat_slug in ["ev-b2c-pricing", "customer-2w-ev-pricing"]:
        sd["tracked_url"] = f"/catalog/ev-b2c-pricing?ref={ref}"
    elif seg_code == "EV_SPARES" or cat_slug in ["ev-spares", "ev-spares-and-chargers"]:
        sd["tracked_url"] = f"/catalog/ev-spares?ref={ref}"
    elif seg_code == "REAL_DREAMS":
        sd["tracked_url"] = f"/catalog/real-dreams?ref={ref}"
    elif seg_code == "INSURANCE":
        sd["tracked_url"] = f"/catalog/insurance?ref={ref}"
    elif seg_code == "INDUSTRIAL_HUB" or cat_slug == "industrial-hub-franchise":
        sd["tracked_url"] = f"/catalog/industrial-hub?ref={ref}"
    elif seg_code == "ETC_TRAINING":
        sd["tracked_url"] = f"/catalog/etc-training?ref={ref}"
    else:
        sd["tracked_url"] = f"/catalog/solar/commercial-residential-solar?ref={ref}"

    # Engagement calculation
    views = s.view_count or 0
    if views >= 3:
        sd["engagement_badge"] = "high"
        sd["engagement_text"] = f"🔥 {views} clicks"
    elif views > 0:
        sd["engagement_badge"] = "active"
        sd["engagement_text"] = f"✓ {views} click{'s' if views > 1 else ''}"
    else:
        sd["engagement_badge"] = "unopened"
        sd["engagement_text"] = "0 clicks"

    return sd


@router.get("/dispatches/history")
def get_dispatch_history(
    scope: str = Query("my", description="'my' for current login, 'team' for entire team/company"),
    q: Optional[str] = Query(None, description="Search recipient name, phone, ref code, or staff name/code"),
    segment_code: Optional[str] = Query(None, description="Filter by catalog model segment"),
    delivery_method: Optional[str] = Query(None, description="web_link, pdf_document, both, all"),
    engagement: Optional[str] = Query(None, description="all, viewed, unviewed, high"),
    staff_id: Optional[int] = Query(None, description="Filter by specific staff sender"),
    timeframe: Optional[str] = Query(None, description="today, yesterday, 7d, 30d, all"),
    sort_by: str = Query("sent_desc", description="sent_desc, sent_asc, views_desc, name_asc"),
    limit: int = Query(100, le=500),
    offset: int = Query(0, ge=0),
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """
    Returns comprehensive catalog dispatch history with multi-model filtering,
    click telemetry, and dedicated 'my' vs 'team' scoping.
    """
    from collections import Counter
    query = db.query(CatalogLeadSend)

    # 1. Scope filter
    scope_str = scope if isinstance(scope, str) else "my"
    is_team_scope = (scope_str.lower() == "team")
    if not is_team_scope:
        query = query.filter(CatalogLeadSend.staff_id == current_user.id)
    elif staff_id and isinstance(staff_id, int):
        query = query.filter(CatalogLeadSend.staff_id == staff_id)

    # 2. Model / Segment filter
    if segment_code and isinstance(segment_code, str) and segment_code.upper() != "ALL":
        query = query.join(DigitalCatalog, CatalogLeadSend.catalog_id == DigitalCatalog.id).filter(
            DigitalCatalog.segment_code == segment_code.upper()
        )

    # 3. Delivery method filter
    if delivery_method and isinstance(delivery_method, str) and delivery_method.lower() != "all":
        query = query.filter(CatalogLeadSend.delivery_method == delivery_method)

    # 4. Engagement / Click filter
    eng_str = engagement if isinstance(engagement, str) else None
    if eng_str == "viewed":
        query = query.filter(CatalogLeadSend.view_count > 0)
    elif eng_str == "unviewed":
        query = query.filter(CatalogLeadSend.view_count == 0)
    elif eng_str == "high":
        query = query.filter(CatalogLeadSend.view_count >= 2)

    # 5. Timeframe filter
    now_ist = get_indian_time()
    tf_str = timeframe if isinstance(timeframe, str) else None
    if tf_str == "today":
        start_day = now_ist.replace(hour=0, minute=0, second=0, microsecond=0)
        query = query.filter(CatalogLeadSend.sent_at >= start_day)
    elif tf_str == "yesterday":
        start_yest = (now_ist - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        end_yest = start_yest + timedelta(days=1)
        query = query.filter(CatalogLeadSend.sent_at >= start_yest, CatalogLeadSend.sent_at < end_yest)
    elif tf_str == "7d":
        query = query.filter(CatalogLeadSend.sent_at >= (now_ist - timedelta(days=7)))
    elif tf_str == "30d":
        query = query.filter(CatalogLeadSend.sent_at >= (now_ist - timedelta(days=30)))

    # 6. Text Search
    if q and isinstance(q, str) and q.strip():
        term = f"%{q.strip()}%"
        query = query.join(DigitalCatalog, CatalogLeadSend.catalog_id == DigitalCatalog.id, isouter=True) \
                     .join(StaffEmployee, CatalogLeadSend.staff_id == StaffEmployee.id, isouter=True) \
                     .filter(or_(
                         CatalogLeadSend.recipient_name.ilike(term),
                         CatalogLeadSend.recipient_phone.ilike(term),
                         CatalogLeadSend.share_ref_code.ilike(term),
                         DigitalCatalog.title.ilike(term),
                         StaffEmployee.first_name.ilike(term),
                         StaffEmployee.last_name.ilike(term),
                         StaffEmployee.emp_code.ilike(term)
                     ))

    # 7. Sorting
    sort_str = sort_by if isinstance(sort_by, str) else "sent_desc"
    if sort_str == "sent_asc":
        query = query.order_by(CatalogLeadSend.sent_at.asc())
    elif sort_str == "views_desc":
        query = query.order_by(CatalogLeadSend.view_count.desc(), CatalogLeadSend.sent_at.desc())
    elif sort_str == "name_asc":
        query = query.order_by(CatalogLeadSend.recipient_name.asc())
    else:  # sent_desc
        query = query.order_by(CatalogLeadSend.sent_at.desc())

    # Calculate overall KPIs for current filtered query
    all_sends = query.all()
    total_count = len(all_sends)
    total_views = sum((s.view_count or 0) for s in all_sends)
    viewed_count = sum(1 for s in all_sends if (s.view_count or 0) > 0)
    high_count = sum(1 for s in all_sends if (s.view_count or 0) >= 2)
    view_rate = round((viewed_count / total_count * 100), 1) if total_count > 0 else 0.0

    # Top model
    model_counts = Counter(s.catalog.segment_code for s in all_sends if s.catalog)
    top_model = model_counts.most_common(1)[0][0] if model_counts else "SOLAR"

    # Paginate safely
    limit_val = limit if isinstance(limit, int) else (getattr(limit, "default", 100) if hasattr(limit, "default") else 100)
    offset_val = offset if isinstance(offset, int) else (getattr(offset, "default", 0) if hasattr(offset, "default") else 0)
    if not isinstance(limit_val, int):
        limit_val = 100
    if not isinstance(offset_val, int):
        offset_val = 0

    paged_sends = all_sends[offset_val:offset_val + limit_val]

    # Pre-fetch staff map for performance
    staff_ids = list({s.staff_id for s in paged_sends if s.staff_id})
    staff_map = {}
    if staff_ids:
        staff_records = db.query(StaffEmployee).filter(StaffEmployee.id.in_(staff_ids)).all()
        staff_map = {st.id: st for st in staff_records}

    items = [_format_dispatch_record(s, staff_map) for s in paged_sends]

    # Team members list for filter dropdown
    team_members = []
    if is_team_scope or _is_catalog_author(current_user):
        distinct_staff_ids = [r[0] for r in db.query(CatalogLeadSend.staff_id).distinct().all() if r[0]]
        if distinct_staff_ids:
            st_list = db.query(StaffEmployee).filter(StaffEmployee.id.in_(distinct_staff_ids)).all()
            for st in st_list:
                team_members.append({
                    "id": st.id,
                    "name": f"{st.first_name or ''} {st.last_name or ''}".strip() or st.emp_code,
                    "code": st.emp_code or "",
                    "designation": st.designation or st.staff_type or "Staff"
                })

    # Available catalog models
    all_catalogs = db.query(DigitalCatalog).filter(DigitalCatalog.is_active == True).order_by(DigitalCatalog.sort_order.asc()).all()
    available_models = [
        {"id": c.id, "segment_code": c.segment_code, "title": c.title, "slug": c.slug}
        for c in all_catalogs
    ]

    return {
        "success": True,
        "scope": scope,
        "total": total_count,
        "limit": limit,
        "offset": offset,
        "dispatches": items,
        "stats": {
            "total_dispatches": total_count,
            "total_views": total_views,
            "viewed_count": viewed_count,
            "unviewed_count": total_count - viewed_count,
            "high_engagement_count": high_count,
            "view_rate_percent": view_rate,
            "top_model": top_model
        },
        "team_members": team_members,
        "available_models": available_models
    }


@router.get("/dispatches/my-history")
def get_my_dispatch_history(
    limit: int = Query(100, le=500),
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """
    Backward-compatible personal catalog dispatch history endpoint.
    """
    return get_dispatch_history(
        scope="my",
        limit=limit,
        current_user=current_user,
        db=db
    )


@router.get("/{catalog_id}")
def get_catalog_detail(
    catalog_id: int,
    lang: str = Query("en"),
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """
    Returns full catalog structure (all sections and items) for CMS editing and preview.
    """
    catalog = db.query(DigitalCatalog).filter(DigitalCatalog.id == catalog_id).first()
    if not catalog:
        raise HTTPException(status_code=404, detail="Catalog not found")

    return {
        "success": True,
        "catalog": catalog.to_dict(include_sections=True, include_items=True, language=lang),
        "user_permissions": {
            "can_author": _is_catalog_author(current_user)
        }
    }


# ════════════════════════════════════════════════════════════════════════════
# 3. AUTHORING CMS ENDPOINTS (Leadership / EA / Admin permission required)
# ════════════════════════════════════════════════════════════════════════════

@router.post("/", status_code=status.HTTP_201_CREATED)
def create_catalog(
    payload: CatalogCreateRequest,
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """
    Creates a new digital catalog. Restricted to authorized administrators / leadership.
    """
    if not _is_catalog_author(current_user):
        raise HTTPException(status_code=403, detail="Unauthorized: Leadership or Admin privileges required.")

    company_id = getattr(current_user, 'company_id', 4) or 4

    # Ensure unique slug per company
    existing = db.query(DigitalCatalog).filter(
        DigitalCatalog.company_id == company_id,
        DigitalCatalog.slug == payload.slug
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"A catalog with slug '{payload.slug}' already exists.")

    catalog = DigitalCatalog(
        company_id=company_id,
        tenant_id=getattr(current_user, 'tenant_id', None),
        segment_code=payload.segment_code.upper(),
        slug=payload.slug.strip().lower(),
        title=payload.title,
        subtitle=payload.subtitle,
        summary=payload.summary,
        hero_media_url=payload.hero_media_url,
        catalog_type=payload.catalog_type,
        status=payload.status,
        is_active=payload.is_active,
        is_featured=payload.is_featured,
        sort_order=payload.sort_order,
        seo_title=payload.seo_title,
        seo_description=payload.seo_description,
        seo_keywords=payload.seo_keywords,
        theme_config=payload.theme_config,
        default_language=payload.default_language,
        active_languages=payload.active_languages,
        pdf_brochure_url=payload.pdf_brochure_url,
        created_by_id=current_user.id,
        updated_by_id=current_user.id,
        published_at=get_indian_time() if payload.status == 'published' else None,
        created_at=get_indian_time(),
        updated_at=get_indian_time()
    )
    db.add(catalog)
    db.commit()
    db.refresh(catalog)

    logger.info(f"Catalog '{catalog.title}' (ID: {catalog.id}) created by staff #{current_user.id}")
    return {"success": True, "catalog": catalog.to_dict()}


@router.put("/{catalog_id}")
def update_catalog(
    catalog_id: int,
    payload: CatalogUpdateRequest,
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """
    Updates catalog master details, theme, and SEO settings.
    """
    if not _is_catalog_author(current_user):
        raise HTTPException(status_code=403, detail="Unauthorized: Leadership or Admin privileges required.")

    catalog = db.query(DigitalCatalog).filter(DigitalCatalog.id == catalog_id).first()
    if not catalog:
        raise HTTPException(status_code=404, detail="Catalog not found")

    updatable = [
        "title", "subtitle", "summary", "hero_media_url", "catalog_type", "status",
        "is_active", "is_featured", "sort_order", "seo_title", "seo_description",
        "seo_keywords", "theme_config", "default_language", "active_languages",
        "pdf_brochure_url"
    ]
    data = payload.dict(exclude_unset=True)
    for k in updatable:
        if k in data:
            setattr(catalog, k, data[k])

    if data.get("status") == "published" and not catalog.published_at:
        catalog.published_at = get_indian_time()

    catalog.updated_by_id = current_user.id
    catalog.updated_at = get_indian_time()
    catalog.version += 1

    db.commit()
    db.refresh(catalog)
    return {"success": True, "catalog": catalog.to_dict()}


# ── Section Builder Endpoints ───────────────────────────────────────────────

@router.post("/{catalog_id}/sections", status_code=status.HTTP_201_CREATED)
def add_catalog_section(
    catalog_id: int,
    payload: SectionCreateRequest,
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """
    Adds a new modular section to a digital catalog.
    """
    if not _is_catalog_author(current_user):
        raise HTTPException(status_code=403, detail="Unauthorized: Leadership or Admin privileges required.")

    catalog = db.query(DigitalCatalog).filter(DigitalCatalog.id == catalog_id).first()
    if not catalog:
        raise HTTPException(status_code=404, detail="Catalog not found")

    # Get max sort order if 0
    sort_order = payload.sort_order
    if sort_order == 0:
        max_order = db.query(CatalogSection.sort_order).filter(CatalogSection.catalog_id == catalog_id).order_by(CatalogSection.sort_order.desc()).first()
        sort_order = (max_order[0] + 1) if max_order else 0

    section = CatalogSection(
        catalog_id=catalog_id,
        section_type=payload.section_type,
        section_key=payload.section_key,
        title=payload.title,
        subtitle=payload.subtitle,
        content_variants=payload.content_variants,
        media_gallery=payload.media_gallery,
        configuration=payload.configuration,
        sort_order=sort_order,
        is_visible=payload.is_visible,
        is_active=True,
        created_at=get_indian_time(),
        updated_at=get_indian_time()
    )
    db.add(section)
    catalog.updated_at = get_indian_time()
    catalog.version += 1
    db.commit()
    db.refresh(section)

    return {"success": True, "section": section.to_dict()}


@router.put("/{catalog_id}/sections/{section_id}")
def update_catalog_section(
    catalog_id: int,
    section_id: int,
    payload: SectionUpdateRequest,
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """
    Updates an existing section's content, multilingual variants, media, or configuration.
    """
    if not _is_catalog_author(current_user):
        raise HTTPException(status_code=403, detail="Unauthorized: Leadership or Admin privileges required.")

    section = db.query(CatalogSection).filter(
        CatalogSection.id == section_id,
        CatalogSection.catalog_id == catalog_id
    ).first()
    if not section:
        raise HTTPException(status_code=404, detail="Section not found")

    data = payload.dict(exclude_unset=True)
    updatable = [
        "section_type", "section_key", "title", "subtitle",
        "content_variants", "media_gallery", "configuration",
        "sort_order", "is_visible"
    ]
    for k in updatable:
        if k in data:
            setattr(section, k, data[k])

    section.updated_at = get_indian_time()
    section.catalog.updated_at = get_indian_time()
    section.catalog.version += 1

    db.commit()
    db.refresh(section)
    return {"success": True, "section": section.to_dict()}


@router.delete("/{catalog_id}/sections/{section_id}")
def delete_catalog_section(
    catalog_id: int,
    section_id: int,
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """
    Deletes a section from the catalog.
    """
    if not _is_catalog_author(current_user):
        raise HTTPException(status_code=403, detail="Unauthorized: Leadership or Admin privileges required.")

    section = db.query(CatalogSection).filter(
        CatalogSection.id == section_id,
        CatalogSection.catalog_id == catalog_id
    ).first()
    if not section:
        raise HTTPException(status_code=404, detail="Section not found")

    db.delete(section)
    db.commit()
    return {"success": True, "message": "Section removed successfully"}


@router.post("/{catalog_id}/sections/reorder")
def reorder_catalog_sections(
    catalog_id: int,
    order_data: List[Dict[str, int]] = Body(...),  # [{"id": 1, "sort_order": 0}, ...]
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """
    Reorders sections according to drag-and-drop hierarchy.
    """
    if not _is_catalog_author(current_user):
        raise HTTPException(status_code=403, detail="Unauthorized: Leadership or Admin privileges required.")

    for item in order_data:
        sec_id = item.get("id")
        sort_ord = item.get("sort_order", 0)
        if sec_id is not None:
            db.execute(text("""
                UPDATE catalog_sections 
                SET sort_order = :ord, updated_at = NOW() 
                WHERE id = :id AND catalog_id = :cid
            """), {"ord": sort_ord, "id": sec_id, "cid": catalog_id})

    db.commit()
    return {"success": True, "message": "Sections reordered successfully"}


# ── Item Manager Endpoints ──────────────────────────────────────────────────

@router.post("/{catalog_id}/items", status_code=status.HTTP_201_CREATED)
def add_catalog_item(
    catalog_id: int,
    payload: ItemCreateRequest,
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """
    Adds a product, package, course, or listing item to a catalog.
    """
    if not _is_catalog_author(current_user):
        raise HTTPException(status_code=403, detail="Unauthorized: Leadership or Admin privileges required.")

    catalog = db.query(DigitalCatalog).filter(DigitalCatalog.id == catalog_id).first()
    if not catalog:
        raise HTTPException(status_code=404, detail="Catalog not found")

    item = CatalogItem(
        catalog_id=catalog_id,
        item_type=payload.item_type,
        item_code=payload.item_code,
        title=payload.title,
        subtitle=payload.subtitle,
        specifications=payload.specifications,
        pricing=payload.pricing,
        media_urls=payload.media_urls,
        video_url=payload.video_url,
        content_variants=payload.content_variants,
        badges=payload.badges,
        sort_order=payload.sort_order,
        is_featured=payload.is_featured,
        is_active=payload.is_active,
        created_at=get_indian_time(),
        updated_at=get_indian_time()
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return {"success": True, "item": item.to_dict()}


@router.put("/{catalog_id}/items/{item_id}")
def update_catalog_item(
    catalog_id: int,
    item_id: int,
    payload: ItemUpdateRequest,
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """
    Updates an item's details, pricing, specifications, or media.
    """
    if not _is_catalog_author(current_user):
        raise HTTPException(status_code=403, detail="Unauthorized: Leadership or Admin privileges required.")

    item = db.query(CatalogItem).filter(
        CatalogItem.id == item_id,
        CatalogItem.catalog_id == catalog_id
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    data = payload.dict(exclude_unset=True)
    for k, v in data.items():
        setattr(item, k, v)

    item.updated_at = get_indian_time()
    db.commit()
    db.refresh(item)
    return {"success": True, "item": item.to_dict()}


@router.delete("/{catalog_id}/items/{item_id}")
def delete_catalog_item(
    catalog_id: int,
    item_id: int,
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """
    Removes an item from the catalog.
    """
    if not _is_catalog_author(current_user):
        raise HTTPException(status_code=403, detail="Unauthorized: Leadership or Admin privileges required.")

    item = db.query(CatalogItem).filter(
        CatalogItem.id == item_id,
        CatalogItem.catalog_id == catalog_id
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    db.delete(item)
    db.commit()
    return {"success": True, "message": "Item deleted successfully"}


# ── S3 Media Upload ─────────────────────────────────────────────────────────

@router.post("/upload-media")
async def upload_catalog_media(
    file: UploadFile = File(...),
    folder: str = Form("catalogs"),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Uploads catalog media (images, PDFs, documents) to AWS S3 (myntreal-media-vault)
    and returns a public S3 URL.
    """
    try:
        content = await file.read()
        if len(content) > 25 * 1024 * 1024:  # 25MB max
            raise HTTPException(status_code=400, detail="File size exceeds 25MB limit")

        ext = os.path.splitext(file.filename or "")[1].lower() or ".jpg"
        unique_name = f"{uuid.uuid4().hex[:12]}{ext}"
        s3_key = f"public/{folder}/{unique_name}"

        content_type = file.content_type or "image/jpeg"
        uploaded = s3_storage_service.upload_file(
            file_path=s3_key,
            file_data=content,
            content_type=content_type
        )

        if not uploaded:
            raise HTTPException(status_code=500, detail="S3 upload failed")

        public_url = s3_storage_service.get_public_url(s3_key)
        return {
            "success": True,
            "url": public_url,
            "filename": file.filename,
            "content_type": content_type
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Media upload error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


# ── AI Content Writing (Google Gemini) ──────────────────────────────────────

@router.post("/ai-draft")
def generate_ai_catalog_content(
    payload: AIDraftRequest,
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Uses Google Gemini to generate high-converting marketing copy and multilingual
    variants (English, Telugu, Hindi, Tamil) for digital catalog sections.
    """
    if not _is_catalog_author(current_user):
        raise HTTPException(status_code=403, detail="Unauthorized: Leadership or Admin privileges required.")

    api_key = os.environ.get('GEMINI_API_KEY') or os.environ.get('GOOGLE_API_KEY')
    if not api_key:
        raise HTTPException(status_code=500, detail="Gemini API Key is not configured on the server.")

    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)

        model = genai.GenerativeModel("gemini-1.5-flash")

        system_instruction = (
            "You are an elite, high-converting product marketing copywriter for MyntReal & VGK4U platform.\n"
            "Generate structured JSON copy variants for a single-page digital catalog.\n"
            "Return valid JSON ONLY, without Markdown code fences, matching this schema:\n"
            "{\n"
            '  "title": "English Title",\n'
            '  "subtitle": "English Subtitle",\n'
            '  "content_variants": {\n'
            '    "en": {"title": "...", "subtitle": "...", "highlights": ["..."]},\n'
            '    "te": {"title": "...", "subtitle": "...", "highlights": ["..."]},\n'
            '    "hi": {"title": "...", "subtitle": "...", "highlights": ["..."]},\n'
            '    "ta": {"title": "...", "subtitle": "...", "highlights": ["..."]}\n'
            "  }\n"
            "}\n"
            "Guidelines:\n"
            "- Telugu, Hindi, and Tamil must sound natural, professional, and culturally persuasive, keeping key technical terms (e.g., 'Mono-PERC', 'LFP Battery', 'RERA', 'ROI', 'Subsidy') in standard English or transliteration.\n"
            "- Focus on customer benefits, savings, reliability, and warranty."
        )

        user_prompt = (
            f"Vertical: {payload.vertical}\n"
            f"Section Type: {payload.section_type}\n"
            f"Topic/Offering: {payload.topic}\n"
            f"Additional Instructions: {payload.prompt or 'Create punchy, high-converting headlines and bullet points.'}"
        )

        response = model.generate_content(f"{system_instruction}\n\n{user_prompt}")
        raw_text = response.text.strip()
        # Clean JSON fences if any
        if raw_text.startswith("```json"):
            raw_text = raw_text[7:]
        if raw_text.startswith("```"):
            raw_text = raw_text[3:]
        if raw_text.endswith("```"):
            raw_text = raw_text[:-3]

        parsed = json.loads(raw_text.strip())
        return {"success": True, "generated": parsed}

    except Exception as e:
        logger.error(f"Gemini AI draft generation error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"AI generation failed: {str(e)}")


# ════════════════════════════════════════════════════════════════════════════
# 4. WHATSAPP DISPATCH & CRM TIMELINE INTEGRATION (Option A Delivery)
# ════════════════════════════════════════════════════════════════════════════

@router.post("/{catalog_id}/dispatch-whatsapp")
def dispatch_catalog_whatsapp(
    catalog_id: int,
    payload: WhatsAppDispatchRequest,
    request: Request,
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """
    Dispatches a digital catalog to a CRM lead or customer via WhatsApp.
    Supports Option A:
    1. Interactive single-page web catalog link (Primary)
    2. PDF brochure attachment, where available
    Generates a secure share_ref_code, logs dispatch to CatalogLeadSend,
    appends to CRM lead timeline note, and provides instant WhatsApp link for staff.
    """
    catalog = db.query(DigitalCatalog).filter(DigitalCatalog.id == catalog_id).first()
    if not catalog:
        raise HTTPException(status_code=404, detail="Catalog not found")

    # Clean phone number
    import re
    clean_digits = re.sub(r'\D', '', payload.recipient_phone)
    if len(clean_digits) == 10:
        full_phone = f"91{clean_digits}"
    elif len(clean_digits) == 12 and clean_digits.startswith('91'):
        full_phone = clean_digits
    else:
        full_phone = clean_digits

    # Generate unique secure share ref code
    share_ref_code = uuid.uuid4().hex[:16]

    # Resolve recipient name
    recip_name = payload.recipient_name
    lead = None
    if payload.lead_id:
        lead = db.query(CRMLead).filter(CRMLead.id == payload.lead_id).first()
        if lead and not recip_name:
            recip_name = lead.lead_name or lead.contact_person

    recip_display = recip_name or "Valued Customer"

    # Base web application domain
    host = request.headers.get("host") or "myntos.vgk4u.com"
    scheme = request.headers.get("x-forwarded-proto") or "https"
    base_url = f"{scheme}://{host}"
    if "localhost" in host:
        base_url = "http://localhost:5000"

    staff_name = f"{current_user.first_name} {current_user.last_name or ''}".strip()
    staff_ext = None
    try:
        from app.services.whatsapp_auto_service import resolve_staff_extension
        staff_ext = resolve_staff_extension(db, current_user.id, company_id=getattr(current_user, 'base_company_id', 1))
    except Exception:
        pass

    # Single-page web catalog personalized link
    import urllib.parse
    cat_slug = catalog.slug
    segment_slug = catalog.segment_code.lower().replace('_', '-')
    ext_param = f"&ext={urllib.parse.quote(str(staff_ext))}" if staff_ext else ""
    if catalog.segment_code == "HUB_PRICING" or cat_slug == "hub-ev-pricing":
        web_catalog_url = f"{base_url}/catalog/hub-ev-pricing?ref={share_ref_code}&name={urllib.parse.quote(recip_display)}&staff={urllib.parse.quote(staff_name)}{ext_param}&lang={payload.language_code}"
    elif catalog.segment_code == "EV_B2C" or cat_slug in ["ev-b2c-pricing", "customer-2w-ev-pricing"]:
        web_catalog_url = f"{base_url}/catalog/ev-b2c-pricing?ref={share_ref_code}&name={urllib.parse.quote(recip_display)}&staff={urllib.parse.quote(staff_name)}{ext_param}&lang={payload.language_code}"
    else:
        web_catalog_url = f"{base_url}/catalog/{segment_slug}/{cat_slug}?ref={share_ref_code}&name={urllib.parse.quote(recip_display)}&staff={urllib.parse.quote(staff_name)}{ext_param}&lang={payload.language_code}"

    # Build personalized WhatsApp message
    message_lines = [
        f"Dear {recip_display}! 👋",
        "",
        f"Here is your personalized *{catalog.title}* proposal prepared by *{staff_name}*:",
        "",
        f"📱 *Interactive Web Proposal & Calculator:*",
        f"{web_catalog_url}"
    ]

    if payload.delivery_method in ("pdf_document", "both") and catalog.pdf_brochure_url:
        message_lines.extend([
            "",
            f"📄 *Download PDF Brochure:*",
            f"{catalog.pdf_brochure_url}"
        ])

    if payload.custom_note:
        message_lines.extend([
            "",
            f"💬 *Note from our Specialist:*",
            f"_{payload.custom_note}_"
        ])

    branding = _get_catalog_branding(catalog)
    platform_label = branding.get("platform_name", "MYNTREAL")
    helpline = branding.get("primary_contact_phone", "+91 858585 2738")
    consult_text = "site audit" if catalog.segment_code == "SOLAR" else "consultation"
    sig_lines = [
        "",
        f"For queries or an immediate {consult_text}, feel free to reply directly.",
        "Best regards,",
        f"*{staff_name}*",
        f"📞 Helpline: {helpline}"
    ]
    if staff_ext:
        sig_lines.append(f"Ext: {staff_ext}")
    sig_lines.append(platform_label)
    message_lines.extend(sig_lines)

    full_message = "\n".join(message_lines)

    # Save to CatalogLeadSend ledger
    lead_send = CatalogLeadSend(
        catalog_id=catalog.id,
        lead_id=payload.lead_id,
        company_id=getattr(current_user, 'company_id', 4) or 4,
        staff_id=current_user.id,
        recipient_phone=full_phone,
        recipient_name=recip_name,
        language_code=payload.language_code,
        delivery_channel="whatsapp",
        delivery_method=payload.delivery_method,
        share_ref_code=share_ref_code,
        status="pending",
        view_count=0,
        sent_at=get_indian_time()
    )
    db.add(lead_send)
    db.commit()
    db.refresh(lead_send)

    # Attempt Meta Cloud API dispatch
    wa_result = {"success": False, "reason": "Not attempted"}
    try:
        from app.services.whatsapp_auto_service import send_direct_whatsapp
        wa_result = send_direct_whatsapp(
            db=db,
            phone=full_phone,
            message=full_message,
            lead_id=payload.lead_id,
            staff_id=current_user.id
        )
        if wa_result.get("success"):
            lead_send.status = "sent"
            lead_send.whatsapp_message_id = wa_result.get("wamid")
        else:
            lead_send.status = "failed"
            lead_send.failure_reason = str(wa_result.get("reason", "Meta API Error"))
        db.commit()
    except Exception as wa_err:
        logger.warning(f"WhatsApp direct send error (non-fatal, staff link available): {wa_err}")
        lead_send.status = "pending_staff_send"
        lead_send.failure_reason = str(wa_err)
        db.commit()

    # Log to CRM Lead Timeline if lead exists
    if payload.lead_id:
        try:
            crm_note = CRMLeadNote(
                lead_id=payload.lead_id,
                note=(
                    f"📱 Digital Catalog Dispatched [{catalog.title}]\n"
                    f"Method: {payload.delivery_method} | Language: {payload.language_code}\n"
                    f"Link: {web_catalog_url}\n"
                    f"Status: {lead_send.status}"
                ),
                created_by_id=current_user.emp_code if hasattr(current_user, 'emp_code') else str(current_user.id),
                created_by_type="staff",
                created_at=get_indian_time()
            )
            db.add(crm_note)
            db.commit()
        except Exception as _note_err:
            logger.warning(f"Failed to log CRM note for catalog send: {_note_err}")

    # Generate wa.me link for instant staff WhatsApp Web / App intent click
    import urllib.parse
    encoded_text = urllib.parse.quote(full_message)
    wa_me_url = f"https://wa.me/{full_phone}?text={encoded_text}"

    return {
        "success": True,
        "send_id": lead_send.id,
        "share_ref_code": share_ref_code,
        "web_catalog_url": web_catalog_url,
        "wa_me_url": wa_me_url,
        "delivery_status": lead_send.status,
        "whatsapp_api_result": wa_result
    }


# ── Smart Recipient Directory Search (Leads, Calls, Partners, Directory) ───

@router.get("/recipients/search")
def search_catalog_recipients(
    q: str = Query("", description="Name or phone digit search query"),
    limit: int = Query(25, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    """
    Intelligent recipient search for Digital Catalog WhatsApp sharing.
    Multi-source lookup across:
    1. CRM Leads (name, city, and phone digits)
    2. Recent Calls / Call Logs (contact name, phone digits, call time)
    3. Official Partners (partner name, contact person, partner code, city, and phone digits)
    4. Staff Team Colleagues (colleague name, employee code, and phone digits)

    - If query is empty: returns recent active interactions (recent calls & leads) for 1-click selection.
    - If 3+ digits entered: matches against phone numbers across all sources.
    - If letters entered: performs case-insensitive search across contact & entity names.
    - Automatically deduplicates by 10-digit mobile number.
    """
    query_str = (q or "").strip()
    clean_digits = re.sub(r'[^0-9]', '', query_str)
    has_digits = len(clean_digits) >= 3
    q_like = f"%{query_str}%"
    d_like = f"%{clean_digits}%" if has_digits else ""
    seen_phones = set()
    results = []

    # Case A: Empty query -> Return recent active contacts (recent calls & active leads)
    if not query_str:
        # 1. Recent Call Logs (calls from staff)
        try:
            calls_sql = text("""
                SELECT contact_name, phone_number, call_datetime, call_type
                FROM (
                    SELECT contact_name, phone_number, call_datetime, call_type,
                           ROW_NUMBER() OVER (
                               PARTITION BY RIGHT(REGEXP_REPLACE(phone_number, '[^0-9]', '', 'g'), 10)
                               ORDER BY id DESC
                           ) as rn
                    FROM staff_call_logs
                    WHERE phone_number IS NOT NULL 
                      AND LENGTH(REGEXP_REPLACE(phone_number, '[^0-9]', '', 'g')) >= 10
                ) sub
                WHERE rn = 1
                ORDER BY call_datetime DESC NULLS LAST
                LIMIT 10;
            """)
            call_rows = db.execute(calls_sql).fetchall()
            for c_name, c_ph, c_dt, c_type in call_rows:
                if not c_ph:
                    continue
                cp = re.sub(r'[^0-9]', '', str(c_ph))[-10:]
                if len(cp) == 10 and cp not in seen_phones:
                    seen_phones.add(cp)
                    time_str = c_dt.strftime("%d %b, %I:%M %p") if c_dt else "Recent"
                    c_type_label = (c_type or "Call").capitalize()
                    disp_name = (c_name or "").strip()
                    results.append({
                        "name": disp_name if disp_name else f"Caller ({cp})",
                        "phone": cp,
                        "formatted_phone": f"+91 {cp[:5]} {cp[5:]}",
                        "source": "Recent Call",
                        "badge_class": "badge-call",
                        "badge_color": "#0284c7",
                        "subtitle": f"{c_type_label} • {time_str}",
                        "lead_id": None,
                        "partner_id": None,
                        "city": ""
                    })
        except Exception as e:
            logger.warning(f"[RECIPIENT-SEARCH] Error loading recent calls: {e}")

        # 2. Recent Active CRM Leads
        try:
            leads_sql = text("""
                SELECT id, name, phone, alternate_phone, city, status
                FROM crm_leads
                WHERE phone IS NOT NULL AND LENGTH(REGEXP_REPLACE(phone, '[^0-9]', '', 'g')) >= 10
                ORDER BY id DESC
                LIMIT 10;
            """)
            lead_rows = db.execute(leads_sql).fetchall()
            for lid, l_name, l_ph, l_alt, l_city, l_stat in lead_rows:
                for ph in (l_ph, l_alt):
                    if not ph:
                        continue
                    cp = re.sub(r'[^0-9]', '', str(ph))[-10:]
                    if len(cp) == 10 and cp not in seen_phones:
                        seen_phones.add(cp)
                        disp_name = (l_name or "Valued Lead").strip()
                        sub = f"{l_stat or 'Active'} • {l_city or ''}".strip(" •")
                        results.append({
                            "name": disp_name,
                            "phone": cp,
                            "formatted_phone": f"+91 {cp[:5]} {cp[5:]}",
                            "source": "CRM Lead",
                            "badge_class": "badge-lead",
                            "badge_color": "#059669",
                            "subtitle": sub if sub else "Active Lead",
                            "lead_id": lid,
                            "partner_id": None,
                            "city": l_city or ""
                        })
        except Exception as e:
            logger.warning(f"[RECIPIENT-SEARCH] Error loading recent leads: {e}")

        # 3. Key Partners
        try:
            part_sql = text("""
                SELECT id, partner_name, partner_code, phone, city, category
                FROM official_partners
                WHERE phone IS NOT NULL AND LENGTH(REGEXP_REPLACE(phone, '[^0-9]', '', 'g')) >= 10
                  AND is_active = TRUE
                ORDER BY id DESC
                LIMIT 6;
            """)
            part_rows = db.execute(part_sql).fetchall()
            for pid, p_name, p_code, p_ph, p_city, p_cat in part_rows:
                if not p_ph:
                    continue
                cp = re.sub(r'[^0-9]', '', str(p_ph))[-10:]
                if len(cp) == 10 and cp not in seen_phones:
                    seen_phones.add(cp)
                    disp_name = f"{(p_name or '').strip()} ({p_code or 'Partner'})"
                    sub = f"{p_cat or 'Partner'} • {p_city or ''}".strip(" •")
                    results.append({
                        "name": disp_name,
                        "phone": cp,
                        "formatted_phone": f"+91 {cp[:5]} {cp[5:]}",
                        "source": "Channel Partner",
                        "badge_class": "badge-partner",
                        "badge_color": "#7c3aed",
                        "subtitle": sub if sub else "Channel Partner",
                        "lead_id": None,
                        "partner_id": pid,
                        "city": p_city or ""
                    })
        except Exception as e:
            logger.warning(f"[RECIPIENT-SEARCH] Error loading key partners: {e}")

        return {
            "success": True,
            "results": results[:limit],
            "total": len(results),
            "is_recent": True
        }

    # Case B: Search active query (Names or Phone Digits)
    # 1. Search CRM Leads (matches name, city, or phone digits)
    try:
        leads_sql = text("""
            SELECT id, name, phone, alternate_phone, city, status
            FROM crm_leads
            WHERE (name ILIKE :q_like OR city ILIKE :q_like)
               OR (:has_digits AND (phone LIKE :d_like OR alternate_phone LIKE :d_like))
            ORDER BY id DESC
            LIMIT 20;
        """)
        lead_rows = db.execute(leads_sql, {
            "q_like": q_like,
            "has_digits": has_digits,
            "d_like": d_like
        }).fetchall()
        for lid, l_name, l_ph, l_alt, l_city, l_stat in lead_rows:
            for ph in (l_ph, l_alt):
                if not ph:
                    continue
                cp = re.sub(r'[^0-9]', '', str(ph))[-10:]
                if len(cp) == 10 and cp not in seen_phones:
                    seen_phones.add(cp)
                    disp_name = (l_name or "Valued Lead").strip()
                    sub = f"{l_stat or 'Lead'} • {l_city or ''}".strip(" •")
                    results.append({
                        "name": disp_name,
                        "phone": cp,
                        "formatted_phone": f"+91 {cp[:5]} {cp[5:]}",
                        "source": "CRM Lead",
                        "badge_class": "badge-lead",
                        "badge_color": "#059669",
                        "subtitle": sub if sub else "CRM Lead",
                        "lead_id": lid,
                        "partner_id": None,
                        "city": l_city or ""
                    })
    except Exception as e:
        logger.warning(f"[RECIPIENT-SEARCH] Error searching CRM leads: {e}")

    # 2. Search Staff Call Logs (matches contact name or phone digits)
    try:
        calls_sql = text("""
            SELECT contact_name, phone_number, call_datetime, call_type
            FROM (
                SELECT contact_name, phone_number, call_datetime, call_type,
                       ROW_NUMBER() OVER (
                           PARTITION BY RIGHT(REGEXP_REPLACE(phone_number, '[^0-9]', '', 'g'), 10)
                           ORDER BY id DESC
                       ) as rn
                FROM staff_call_logs
                WHERE (contact_name IS NOT NULL AND contact_name ILIKE :q_like)
                   OR (:has_digits AND phone_number LIKE :d_like)
            ) sub
            WHERE rn = 1
            ORDER BY call_datetime DESC NULLS LAST
            LIMIT 15;
        """)
        call_rows = db.execute(calls_sql, {
            "q_like": q_like,
            "has_digits": has_digits,
            "d_like": d_like
        }).fetchall()
        for c_name, c_ph, c_dt, c_type in call_rows:
            if not c_ph:
                continue
            cp = re.sub(r'[^0-9]', '', str(c_ph))[-10:]
            if len(cp) == 10 and cp not in seen_phones:
                seen_phones.add(cp)
                time_str = c_dt.strftime("%d %b") if c_dt else "Call"
                c_type_label = (c_type or "Call").capitalize()
                disp_name = (c_name or "").strip()
                results.append({
                    "name": disp_name if disp_name else f"Caller ({cp})",
                    "phone": cp,
                    "formatted_phone": f"+91 {cp[:5]} {cp[5:]}",
                    "source": "Recent Call",
                    "badge_class": "badge-call",
                    "badge_color": "#0284c7",
                    "subtitle": f"{c_type_label} • {time_str}",
                    "lead_id": None,
                    "partner_id": None,
                    "city": ""
                })
    except Exception as e:
        logger.warning(f"[RECIPIENT-SEARCH] Error searching call logs: {e}")

    # 3. Search Official Partners (matches partner name, code, contact person, or phone digits)
    try:
        part_sql = text("""
            SELECT id, partner_name, partner_code, phone, contact_person_1_phone, city, category
            FROM official_partners
            WHERE partner_name ILIKE :q_like
               OR partner_code ILIKE :q_like
               OR contact_person_1_name ILIKE :q_like
               OR city ILIKE :q_like
               OR (:has_digits AND (phone LIKE :d_like OR contact_person_1_phone LIKE :d_like))
            ORDER BY id DESC
            LIMIT 15;
        """)
        part_rows = db.execute(part_sql, {
            "q_like": q_like,
            "has_digits": has_digits,
            "d_like": d_like
        }).fetchall()
        for pid, p_name, p_code, p_ph, p_alt, p_city, p_cat in part_rows:
            for ph in (p_ph, p_alt):
                if not ph:
                    continue
                cp = re.sub(r'[^0-9]', '', str(ph))[-10:]
                if len(cp) == 10 and cp not in seen_phones:
                    seen_phones.add(cp)
                    disp_name = f"{(p_name or '').strip()} ({p_code or 'Partner'})"
                    sub = f"{p_cat or 'Partner'} • {p_city or ''}".strip(" •")
                    results.append({
                        "name": disp_name,
                        "phone": cp,
                        "formatted_phone": f"+91 {cp[:5]} {cp[5:]}",
                        "source": "Channel Partner",
                        "badge_class": "badge-partner",
                        "badge_color": "#7c3aed",
                        "subtitle": sub if sub else "Channel Partner",
                        "lead_id": None,
                        "partner_id": pid,
                        "city": p_city or ""
                    })
    except Exception as e:
        logger.warning(f"[RECIPIENT-SEARCH] Error searching partners: {e}")

    # 4. Search Staff Colleagues (matches first/last name, emp_code, or phone digits)
    try:
        staff_sql = text("""
            SELECT id, first_name, last_name, emp_code, phone, designation
            FROM staff_employees
            WHERE first_name ILIKE :q_like
               OR last_name ILIKE :q_like
               OR emp_code ILIKE :q_like
               OR (:has_digits AND phone LIKE :d_like)
            ORDER BY id DESC
            LIMIT 10;
        """)
        staff_rows = db.execute(staff_sql, {
            "q_like": q_like,
            "has_digits": has_digits,
            "d_like": d_like
        }).fetchall()
        for sid, fn, ln, ecode, sph, desig in staff_rows:
            if not sph:
                continue
            cp = re.sub(r'[^0-9]', '', str(sph))[-10:]
            if len(cp) == 10 and cp not in seen_phones:
                seen_phones.add(cp)
                disp_name = f"{(fn or '').strip()} {(ln or '').strip()} ({ecode or ''})".strip()
                results.append({
                    "name": disp_name,
                    "phone": cp,
                    "formatted_phone": f"+91 {cp[:5]} {cp[5:]}",
                    "source": "Staff Team",
                    "badge_class": "badge-staff",
                    "badge_color": "#f59e0b",
                    "subtitle": desig or "Staff Colleague",
                    "lead_id": None,
                    "partner_id": None,
                    "city": ""
                })
    except Exception as e:
        logger.warning(f"[RECIPIENT-SEARCH] Error searching staff: {e}")

    return {
        "success": True,
        "results": results[:limit],
        "total": len(results),
        "is_recent": False
    }

