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
from typing import Optional, List, Dict, Any
from datetime import datetime

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
    lang: str = Query("en", regex="^(en|te|hi|ta)$"),
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


@router.get("/dispatches/my-history")
def get_my_dispatch_history(
    limit: int = Query(50, le=100),
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """
    Returns personal catalog dispatch history for the currently logged-in staff member.
    """
    sends = db.query(CatalogLeadSend).filter(
        CatalogLeadSend.staff_id == current_user.id
    ).order_by(CatalogLeadSend.sent_at.desc()).limit(limit).all()

    items = []
    for s in sends:
        sd = s.to_dict()
        if s.catalog:
            sd["catalog_title"] = s.catalog.title
            sd["segment_code"] = s.catalog.segment_code
            sd["catalog_slug"] = s.catalog.slug
        items.append(sd)

    return {"success": True, "dispatches": items}


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
    if catalog.segment_code == "CUSTOMER_EV_PRICING" or cat_slug == "customer-2w-ev-pricing":
        web_catalog_url = f"{base_url}/catalog/customer-2w-ev-pricing?ref={share_ref_code}&name={urllib.parse.quote(recip_display)}&staff={urllib.parse.quote(staff_name)}{ext_param}&lang={payload.language_code}"
    elif catalog.segment_code == "HUB_PRICING" or cat_slug == "hub-ev-pricing":
        web_catalog_url = f"{base_url}/catalog/hub-ev-pricing?ref={share_ref_code}&name={urllib.parse.quote(recip_display)}&staff={urllib.parse.quote(staff_name)}{ext_param}&lang={payload.language_code}"
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

    sig_lines = [
        "",
        "For queries or an immediate site audit, feel free to reply directly.",
        "Best regards,",
        f"*{staff_name}*",
        "📞 Helpline: +91 858585 2738"
    ]
    if staff_ext:
        sig_lines.append(f"Ext: {staff_ext}")
    sig_lines.append("MYNTREAL Har Ghar Solar")
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
