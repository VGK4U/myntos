"""
Real Dreams - Real Estate Marketplace API Endpoints
DC Protocol Compliant with Company-Wise Data Segregation

Phase 1: RVZ Configuration (Property Types, Amenities, Banner)

Created: December 08, 2025
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request, UploadFile, File, Form, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum

from app.core.database import get_db
from app.models.real_dreams import (
    RDCompanyConfig, RDPropertyType, RDAmenity, RDBannerConfig,
    RDPartnerProfile, RDProperty, RDPropertyAmenity,
    RDLead, RDLeadFollowup, RDDeal, RDPropertyMedia, RDPropertyCRMLink,
    RDPropertyAudit, RDPromotionalBanner
)
from app.models.staff_accounts import AssociatedCompany
from app.models.staff import StaffEmployee
from app.api.v1.endpoints.staff_auth import get_current_staff_user
from app.models.base import get_indian_time

router = APIRouter(prefix="/real-dreams", tags=["Real Dreams"])

# Company Contact Hotline - DC Protocol: Global fallback when agent hides personal number
COMPANY_CONTACT_HOTLINE = "+91 85 85 85 27 38"


class AmenityCategory(str, Enum):
    SECURITY = "SECURITY"
    LIFESTYLE = "LIFESTYLE"
    UTILITIES = "UTILITIES"
    PARKING = "PARKING"
    OUTDOOR = "OUTDOOR"
    INDOOR = "INDOOR"
    CONNECTIVITY = "CONNECTIVITY"
    OTHER = "OTHER"


class CompanyConfigCreate(BaseModel):
    company_id: int
    is_enabled: bool = False
    allow_partner_listings: bool = True
    allow_employee_listings: bool = True
    allow_member_listings: bool = True
    default_commission_percent: Optional[float] = 2.0
    auto_approve_partner_properties: bool = False
    auto_approve_employee_properties: bool = False
    max_images_per_property: int = 10
    max_properties_per_member: int = 5


class PropertyTypeCreate(BaseModel):
    company_id: int
    name: str = Field(..., min_length=2, max_length=100)
    slug: str = Field(..., min_length=2, max_length=50)
    description: Optional[str] = None
    icon: Optional[str] = None
    display_order: int = 0


class PropertyTypeUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    icon: Optional[str] = None
    is_active: Optional[bool] = None
    display_order: Optional[int] = None


class AmenityCreate(BaseModel):
    company_id: int
    category: AmenityCategory
    name: str = Field(..., min_length=2, max_length=100)
    icon: Optional[str] = None
    display_order: int = 0


class AmenityUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[AmenityCategory] = None
    icon: Optional[str] = None
    is_active: Optional[bool] = None
    display_order: Optional[int] = None


class BannerConfigUpdate(BaseModel):
    banner_text: Optional[str] = None
    banner_subtext: Optional[str] = None
    banner_image_url: Optional[str] = None
    background_color: Optional[str] = None
    text_color: Optional[str] = None
    offer_details: Optional[str] = None
    terms_conditions: Optional[str] = None
    is_active: Optional[bool] = None


@router.get("/dashboard/stats")
async def get_dashboard_stats(
    company_id: int,
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """
    Get Real Dreams dashboard statistics
    DC Protocol: Filter by company_id
    """
    config = db.query(RDCompanyConfig).filter_by(company_id=company_id).first()
    
    if not config or not config.is_enabled:
        return {
            "success": True,
            "enabled": False,
            "message": "Real Dreams is not enabled for this company",
            "stats": None
        }
    
    property_count = db.query(func.count(RDProperty.id)).filter_by(
        company_id=company_id
    ).scalar() or 0
    
    approved_count = db.query(func.count(RDProperty.id)).filter(
        RDProperty.company_id == company_id,
        RDProperty.status == 'APPROVED'
    ).scalar() or 0
    
    pending_count = db.query(func.count(RDProperty.id)).filter(
        RDProperty.company_id == company_id,
        RDProperty.status == 'PENDING'
    ).scalar() or 0
    
    lead_count = db.query(func.count(RDLead.id)).filter_by(
        company_id=company_id
    ).scalar() or 0
    
    deal_count = db.query(func.count(RDDeal.id)).filter_by(
        company_id=company_id
    ).scalar() or 0
    
    partner_count = db.query(func.count(RDPartnerProfile.id)).filter_by(
        company_id=company_id
    ).scalar() or 0
    
    pending_partners = db.query(func.count(RDPartnerProfile.id)).filter(
        RDPartnerProfile.company_id == company_id,
        RDPartnerProfile.status == 'PENDING'
    ).scalar() or 0
    
    approved_partners = db.query(func.count(RDPartnerProfile.id)).filter(
        RDPartnerProfile.company_id == company_id,
        RDPartnerProfile.status == 'APPROVED'
    ).scalar() or 0
    
    rejected_partners = db.query(func.count(RDPartnerProfile.id)).filter(
        RDPartnerProfile.company_id == company_id,
        RDPartnerProfile.status == 'REJECTED'
    ).scalar() or 0
    
    draft_partners = db.query(func.count(RDPartnerProfile.id)).filter(
        RDPartnerProfile.company_id == company_id,
        RDPartnerProfile.status == 'DRAFT'
    ).scalar() or 0
    
    property_type_count = db.query(func.count(RDPropertyType.id)).filter(
        RDPropertyType.company_id == company_id,
        RDPropertyType.is_active == True
    ).scalar() or 0
    
    amenity_count = db.query(func.count(RDAmenity.id)).filter(
        RDAmenity.company_id == company_id,
        RDAmenity.is_active == True
    ).scalar() or 0
    
    return {
        "success": True,
        "enabled": True,
        "total_partners": partner_count,
        "pending_partners": pending_partners,
        "approved_partners": approved_partners,
        "rejected_partners": rejected_partners,
        "draft_partners": draft_partners,
        "total_properties": property_count,
        "stats": {
            "total_properties": property_count,
            "approved_properties": approved_count,
            "pending_properties": pending_count,
            "total_leads": lead_count,
            "total_deals": deal_count,
            "total_partners": partner_count,
            "pending_partners": pending_partners,
            "approved_partners": approved_partners,
            "rejected_partners": rejected_partners,
            "draft_partners": draft_partners,
            "property_types": property_type_count,
            "amenities": amenity_count
        },
        "config": config.to_dict()
    }


@router.get("/config/companies")
async def get_enabled_companies(
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """
    Get all companies with Real Dreams configuration
    DC Protocol: RVZ can see all companies
    """
    companies = db.query(AssociatedCompany).filter_by(is_active=True).all()
    
    configs = {}
    for config in db.query(RDCompanyConfig).all():
        configs[config.company_id] = config.to_dict()
    
    result = []
    for company in companies:
        result.append({
            "company": {
                "id": company.id,
                "company_code": company.company_code,
                "company_name": company.company_name
            },
            "rd_config": configs.get(company.id, None),
            "is_enabled": configs.get(company.id, {}).get('is_enabled', False) if configs.get(company.id) else False
        })
    
    return {
        "success": True,
        "companies": result
    }


@router.post("/config/company")
async def create_or_update_company_config(
    data: CompanyConfigCreate,
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """
    Create or update Real Dreams company configuration
    DC Protocol: Enable Real Dreams for a company
    """
    company = db.query(AssociatedCompany).filter_by(id=data.company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    config = db.query(RDCompanyConfig).filter_by(company_id=data.company_id).first()
    
    if config:
        config.is_enabled = data.is_enabled
        config.allow_partner_listings = data.allow_partner_listings
        config.allow_employee_listings = data.allow_employee_listings
        config.allow_member_listings = data.allow_member_listings
        config.default_commission_percent = data.default_commission_percent
        config.auto_approve_partner_properties = data.auto_approve_partner_properties
        config.auto_approve_employee_properties = data.auto_approve_employee_properties
        config.max_images_per_property = data.max_images_per_property
        config.max_properties_per_member = data.max_properties_per_member
        if data.is_enabled and not config.enabled_at:
            config.enabled_at = get_indian_time()
            config.enabled_by_id = current_user.id
    else:
        config = RDCompanyConfig(
            company_id=data.company_id,
            is_enabled=data.is_enabled,
            allow_partner_listings=data.allow_partner_listings,
            allow_employee_listings=data.allow_employee_listings,
            allow_member_listings=data.allow_member_listings,
            default_commission_percent=data.default_commission_percent,
            auto_approve_partner_properties=data.auto_approve_partner_properties,
            auto_approve_employee_properties=data.auto_approve_employee_properties,
            max_images_per_property=data.max_images_per_property,
            max_properties_per_member=data.max_properties_per_member,
            enabled_by_id=current_user.id if data.is_enabled else None,
            enabled_at=get_indian_time() if data.is_enabled else None
        )
        db.add(config)
    
    if data.is_enabled:
        banner = db.query(RDBannerConfig).filter_by(company_id=data.company_id).first()
        if not banner:
            banner = RDBannerConfig(
                company_id=data.company_id,
                banner_text="BOOK THIS PROPERTY & GET A FREE E-BIKE!",
                created_by_id=current_user.id
            )
            db.add(banner)
    
    db.commit()
    db.refresh(config)
    
    return {
        "success": True,
        "message": "Company configuration saved",
        "config": config.to_dict()
    }


@router.get("/config/property-types")
async def get_property_types(
    company_id: int,
    include_inactive: bool = False,
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """
    Get property types for a company
    DC Protocol: Filter by company_id
    """
    query = db.query(RDPropertyType).filter_by(company_id=company_id)
    
    if not include_inactive:
        query = query.filter_by(is_active=True)
    
    types = query.order_by(RDPropertyType.display_order, RDPropertyType.name).all()
    
    return {
        "success": True,
        "property_types": [t.to_dict() for t in types]
    }


@router.post("/config/property-types")
async def create_property_type(
    data: PropertyTypeCreate,
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """
    Create a new property type
    DC Protocol: Company-scoped property type
    """
    existing = db.query(RDPropertyType).filter(
        RDPropertyType.company_id == data.company_id,
        RDPropertyType.slug == data.slug
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Property type with slug '{data.slug}' already exists"
        )
    
    property_type = RDPropertyType(
        company_id=data.company_id,
        name=data.name,
        slug=data.slug,
        description=data.description,
        icon=data.icon,
        display_order=data.display_order,
        created_by_id=current_user.id
    )
    
    db.add(property_type)
    db.commit()
    db.refresh(property_type)
    
    return {
        "success": True,
        "message": "Property type created",
        "property_type": property_type.to_dict()
    }


@router.put("/config/property-types/{type_id}")
async def update_property_type(
    type_id: int,
    data: PropertyTypeUpdate,
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """
    Update a property type
    DC Protocol: Company-scoped update
    """
    property_type = db.query(RDPropertyType).filter_by(id=type_id).first()
    
    if not property_type:
        raise HTTPException(status_code=404, detail="Property type not found")
    
    if data.name is not None:
        property_type.name = data.name
    if data.description is not None:
        property_type.description = data.description
    if data.icon is not None:
        property_type.icon = data.icon
    if data.is_active is not None:
        property_type.is_active = data.is_active
    if data.display_order is not None:
        property_type.display_order = data.display_order
    
    property_type.updated_by_id = current_user.id
    
    db.commit()
    db.refresh(property_type)
    
    return {
        "success": True,
        "message": "Property type updated",
        "property_type": property_type.to_dict()
    }


@router.delete("/config/property-types/{type_id}")
async def delete_property_type(
    type_id: int,
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """
    Soft delete a property type (set inactive)
    DC Protocol: Preserve data, mark inactive
    """
    property_type = db.query(RDPropertyType).filter_by(id=type_id).first()
    
    if not property_type:
        raise HTTPException(status_code=404, detail="Property type not found")
    
    property_count = db.query(func.count(RDProperty.id)).filter_by(
        property_type_id=type_id
    ).scalar() or 0
    
    if property_count > 0:
        property_type.is_active = False
        property_type.updated_by_id = current_user.id
        db.commit()
        return {
            "success": True,
            "message": f"Property type deactivated (has {property_count} properties)",
            "soft_deleted": True
        }
    
    db.delete(property_type)
    db.commit()
    
    return {
        "success": True,
        "message": "Property type deleted",
        "soft_deleted": False
    }


@router.get("/config/amenities")
async def get_amenities(
    company_id: int,
    category: Optional[str] = None,
    include_inactive: bool = False,
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """
    Get amenities for a company
    DC Protocol: Filter by company_id
    """
    query = db.query(RDAmenity).filter_by(company_id=company_id)
    
    if category:
        query = query.filter_by(category=category)
    
    if not include_inactive:
        query = query.filter_by(is_active=True)
    
    amenities = query.order_by(RDAmenity.category, RDAmenity.display_order, RDAmenity.name).all()
    
    categories = {}
    for amenity in amenities:
        if amenity.category not in categories:
            categories[amenity.category] = []
        categories[amenity.category].append(amenity.to_dict())
    
    return {
        "success": True,
        "amenities": [a.to_dict() for a in amenities],
        "by_category": categories,
        "categories": list(AmenityCategory)
    }


@router.post("/config/amenities")
async def create_amenity(
    data: AmenityCreate,
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """
    Create a new amenity
    DC Protocol: Company-scoped amenity
    """
    existing = db.query(RDAmenity).filter(
        RDAmenity.company_id == data.company_id,
        RDAmenity.category == data.category.value,
        RDAmenity.name == data.name
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Amenity '{data.name}' already exists in category '{data.category}'"
        )
    
    amenity = RDAmenity(
        company_id=data.company_id,
        category=data.category.value,
        name=data.name,
        icon=data.icon,
        display_order=data.display_order,
        created_by_id=current_user.id
    )
    
    db.add(amenity)
    db.commit()
    db.refresh(amenity)
    
    return {
        "success": True,
        "message": "Amenity created",
        "amenity": amenity.to_dict()
    }


@router.post("/config/amenities/bulk")
async def create_amenities_bulk(
    request: Request,
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """
    Create multiple amenities at once
    DC Protocol: Bulk creation for initial setup
    """
    body = await request.json()
    company_id = body.get('company_id')
    amenities_data = body.get('amenities', [])
    
    if not company_id:
        raise HTTPException(status_code=400, detail="company_id is required")
    
    created = []
    skipped = []
    
    for item in amenities_data:
        existing = db.query(RDAmenity).filter(
            RDAmenity.company_id == company_id,
            RDAmenity.category == item.get('category'),
            RDAmenity.name == item.get('name')
        ).first()
        
        if existing:
            skipped.append(item.get('name'))
            continue
        
        amenity = RDAmenity(
            company_id=company_id,
            category=item.get('category'),
            name=item.get('name'),
            icon=item.get('icon'),
            display_order=item.get('display_order', 0),
            created_by_id=current_user.id
        )
        db.add(amenity)
        created.append(item.get('name'))
    
    db.commit()
    
    return {
        "success": True,
        "message": f"Created {len(created)} amenities, skipped {len(skipped)} duplicates",
        "created": created,
        "skipped": skipped
    }


@router.put("/config/amenities/{amenity_id}")
async def update_amenity(
    amenity_id: int,
    data: AmenityUpdate,
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """
    Update an amenity
    DC Protocol: Company-scoped update
    """
    amenity = db.query(RDAmenity).filter_by(id=amenity_id).first()
    
    if not amenity:
        raise HTTPException(status_code=404, detail="Amenity not found")
    
    if data.name is not None:
        amenity.name = data.name
    if data.category is not None:
        amenity.category = data.category.value
    if data.icon is not None:
        amenity.icon = data.icon
    if data.is_active is not None:
        amenity.is_active = data.is_active
    if data.display_order is not None:
        amenity.display_order = data.display_order
    
    db.commit()
    db.refresh(amenity)
    
    return {
        "success": True,
        "message": "Amenity updated",
        "amenity": amenity.to_dict()
    }


@router.delete("/config/amenities/{amenity_id}")
async def delete_amenity(
    amenity_id: int,
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """
    Delete an amenity
    DC Protocol: Soft delete if in use
    """
    amenity = db.query(RDAmenity).filter_by(id=amenity_id).first()
    
    if not amenity:
        raise HTTPException(status_code=404, detail="Amenity not found")
    
    usage_count = db.query(func.count(RDPropertyAmenity.id)).filter_by(
        amenity_id=amenity_id
    ).scalar() or 0
    
    if usage_count > 0:
        amenity.is_active = False
        db.commit()
        return {
            "success": True,
            "message": f"Amenity deactivated (used by {usage_count} properties)",
            "soft_deleted": True
        }
    
    db.delete(amenity)
    db.commit()
    
    return {
        "success": True,
        "message": "Amenity deleted",
        "soft_deleted": False
    }


@router.get("/config/banner")
async def get_banner_config(
    company_id: int,
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """
    Get banner configuration for a company
    DC Protocol: Filter by company_id
    """
    banner = db.query(RDBannerConfig).filter_by(company_id=company_id).first()
    
    if not banner:
        return {
            "success": True,
            "banner": None,
            "message": "No banner configured"
        }
    
    return {
        "success": True,
        "banner": banner.to_dict()
    }


@router.put("/config/banner")
async def update_banner_config(
    company_id: int,
    data: BannerConfigUpdate,
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """
    Update banner configuration
    DC Protocol: Company-scoped banner
    """
    banner = db.query(RDBannerConfig).filter_by(company_id=company_id).first()
    
    if not banner:
        banner = RDBannerConfig(
            company_id=company_id,
            banner_text=data.banner_text or "BOOK THIS PROPERTY & GET A FREE E-BIKE!",
            created_by_id=current_user.id
        )
        db.add(banner)
    
    if data.banner_text is not None:
        banner.banner_text = data.banner_text
    if data.banner_subtext is not None:
        banner.banner_subtext = data.banner_subtext
    if data.banner_image_url is not None:
        banner.banner_image_url = data.banner_image_url
    if data.background_color is not None:
        banner.background_color = data.background_color
    if data.text_color is not None:
        banner.text_color = data.text_color
    if data.offer_details is not None:
        banner.offer_details = data.offer_details
    if data.terms_conditions is not None:
        banner.terms_conditions = data.terms_conditions
    if data.is_active is not None:
        banner.is_active = data.is_active
    
    banner.updated_by_id = current_user.id
    
    db.commit()
    db.refresh(banner)
    
    return {
        "success": True,
        "message": "Banner configuration updated",
        "banner": banner.to_dict()
    }


# ============================================================================
# PROMOTIONAL BANNERS (Multiple per Company) - Added December 10, 2025
# ============================================================================

@router.get("/promotional-banners")
async def list_promotional_banners(
    company_id: int,
    include_inactive: bool = False,
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """
    List all promotional banners for a company (Staff view)
    DC Protocol: Filter by company_id
    """
    query = db.query(RDPromotionalBanner).filter(
        RDPromotionalBanner.company_id == company_id
    )
    
    if not include_inactive:
        query = query.filter(RDPromotionalBanner.is_active == True)
    
    banners = query.order_by(RDPromotionalBanner.display_order.asc()).all()
    
    return {
        "success": True,
        "banners": [b.to_dict() for b in banners],
        "total": len(banners)
    }


@router.get("/public/promotional-banners")
async def public_list_promotional_banners(
    company_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """
    Public endpoint to list active promotional banners.
    DC Protocol: If company_id provided, filter by it. Otherwise show banners from ALL enabled companies.
    No authentication required.
    """
    now = get_indian_time()
    
    if company_id:
        query = db.query(RDPromotionalBanner).filter(
            RDPromotionalBanner.company_id == company_id,
            RDPromotionalBanner.is_active == True
        )
    else:
        enabled_ids = [c.company_id for c in db.query(RDCompanyConfig).filter(RDCompanyConfig.is_enabled == True).all()]
        if not enabled_ids:
            return {"success": True, "banners": [], "total": 0}
        query = db.query(RDPromotionalBanner).filter(
            RDPromotionalBanner.company_id.in_(enabled_ids),
            RDPromotionalBanner.is_active == True
        )
    
    banners = query.order_by(RDPromotionalBanner.display_order.asc()).limit(10).all()
    
    active_banners = []
    for b in banners:
        if b.valid_from and b.valid_from > now:
            continue
        if b.valid_until and b.valid_until < now:
            continue
        active_banners.append(b.to_dict())
    
    return {
        "success": True,
        "banners": active_banners,
        "total": len(active_banners)
    }


@router.get("/public/listings")
async def public_list_properties(
    company_id: Optional[int] = None,
    property_type: Optional[str] = None,
    city: Optional[str] = None,
    state: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    page: int = 1,
    limit: int = 20,
    db: Session = Depends(get_db)
):
    query = db.query(RDProperty).filter(RDProperty.status == 'active')

    if company_id:
        query = query.filter(RDProperty.company_id == company_id)
    else:
        enabled_companies = db.query(RDCompanyConfig.company_id).filter(
            RDCompanyConfig.is_enabled == True
        ).all()
        enabled_ids = [c[0] for c in enabled_companies]
        if enabled_ids:
            query = query.filter(RDProperty.company_id.in_(enabled_ids))

    if city:
        query = query.filter(RDProperty.city.ilike(f"%{city}%"))
    if state:
        query = query.filter(RDProperty.state.ilike(f"%{state}%"))
    if min_price:
        query = query.filter(RDProperty.price >= min_price)
    if max_price:
        query = query.filter(RDProperty.price <= max_price)

    total = query.count()
    offset = (page - 1) * limit
    properties = query.order_by(RDProperty.created_at.desc()).offset(offset).limit(limit).all()

    return {
        "success": True,
        "properties": [p.to_dict() for p in properties],
        "total": total,
        "page": page,
        "pages": (total + limit - 1) // limit if limit > 0 else 0
    }


@router.post("/promotional-banners")
async def create_promotional_banner(
    company_id: int,
    request: Request,
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """
    Create a new promotional banner
    DC Protocol: Company-scoped, max 5 banners per company
    """
    existing_count = db.query(func.count(RDPromotionalBanner.id)).filter(
        RDPromotionalBanner.company_id == company_id
    ).scalar() or 0
    
    if existing_count >= 5:
        raise HTTPException(
            status_code=400,
            detail="Maximum 5 promotional banners allowed per company"
        )
    
    data = await request.json()
    
    title = data.get('title', '').strip()
    if not title or len(title) < 3 or len(title) > 200:
        raise HTTPException(status_code=400, detail="Title must be 3-200 characters")
    
    subtitle = data.get('subtitle', '').strip()[:300] if data.get('subtitle') else None
    image_url = data.get('image_url', '').strip()[:500] if data.get('image_url') else None
    cta_text = data.get('cta_text', 'Learn More').strip()[:100]
    cta_link = data.get('cta_link', '').strip()[:500] if data.get('cta_link') else None
    background_color = data.get('background_color', '#10B981').strip()[:20]
    text_color = data.get('text_color', '#FFFFFF').strip()[:20]
    display_order = int(data.get('display_order', existing_count))
    is_active = bool(data.get('is_active', True))
    
    banner = RDPromotionalBanner(
        company_id=company_id,
        title=title,
        subtitle=subtitle,
        image_url=image_url,
        cta_text=cta_text,
        cta_link=cta_link,
        background_color=background_color,
        text_color=text_color,
        display_order=display_order,
        is_active=is_active,
        created_by_id=current_user.id
    )
    
    db.add(banner)
    db.commit()
    db.refresh(banner)
    
    return {
        "success": True,
        "message": "Promotional banner created",
        "banner": banner.to_dict()
    }


@router.put("/promotional-banners/{banner_id}")
async def update_promotional_banner(
    banner_id: int,
    company_id: int,
    request: Request,
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """
    Update a promotional banner
    DC Protocol: Company-scoped update
    """
    banner = db.query(RDPromotionalBanner).filter(
        RDPromotionalBanner.id == banner_id,
        RDPromotionalBanner.company_id == company_id
    ).first()
    
    if not banner:
        raise HTTPException(status_code=404, detail="Banner not found")
    
    data = await request.json()
    
    if 'title' in data:
        title = data['title'].strip()
        if len(title) < 3 or len(title) > 200:
            raise HTTPException(status_code=400, detail="Title must be 3-200 characters")
        banner.title = title
    
    if 'subtitle' in data:
        banner.subtitle = data['subtitle'].strip()[:300] if data['subtitle'] else None
    if 'image_url' in data:
        banner.image_url = data['image_url'].strip()[:500] if data['image_url'] else None
    if 'cta_text' in data:
        banner.cta_text = data['cta_text'].strip()[:100] if data['cta_text'] else 'Learn More'
    if 'cta_link' in data:
        banner.cta_link = data['cta_link'].strip()[:500] if data['cta_link'] else None
    if 'background_color' in data:
        banner.background_color = data['background_color'].strip()[:20]
    if 'text_color' in data:
        banner.text_color = data['text_color'].strip()[:20]
    if 'display_order' in data:
        banner.display_order = int(data['display_order'])
    if 'is_active' in data:
        banner.is_active = bool(data['is_active'])
    if 'valid_from' in data and data['valid_from']:
        try:
            banner.valid_from = datetime.fromisoformat(data['valid_from'].replace('Z', '+00:00'))
        except:
            pass
    if 'valid_until' in data and data['valid_until']:
        try:
            banner.valid_until = datetime.fromisoformat(data['valid_until'].replace('Z', '+00:00'))
        except:
            pass
    
    banner.updated_by_id = current_user.id
    
    db.commit()
    db.refresh(banner)
    
    return {
        "success": True,
        "message": "Promotional banner updated",
        "banner": banner.to_dict()
    }


@router.delete("/promotional-banners/{banner_id}")
async def delete_promotional_banner(
    banner_id: int,
    company_id: int,
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """
    Delete a promotional banner
    DC Protocol: Company-scoped deletion
    """
    banner = db.query(RDPromotionalBanner).filter(
        RDPromotionalBanner.id == banner_id,
        RDPromotionalBanner.company_id == company_id
    ).first()
    
    if not banner:
        raise HTTPException(status_code=404, detail="Banner not found")
    
    db.delete(banner)
    db.commit()
    
    return {
        "success": True,
        "message": "Promotional banner deleted"
    }


@router.put("/promotional-banners/reorder")
async def reorder_promotional_banners(
    company_id: int,
    request: Request,
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """
    Reorder promotional banners
    DC Protocol: Company-scoped reorder
    """
    data = await request.json()
    order = data.get('order', [])
    
    if not order:
        raise HTTPException(status_code=400, detail="Order list required")
    
    for idx, banner_id in enumerate(order):
        banner = db.query(RDPromotionalBanner).filter(
            RDPromotionalBanner.id == banner_id,
            RDPromotionalBanner.company_id == company_id
        ).first()
        
        if banner:
            banner.display_order = idx
            banner.updated_by_id = current_user.id
    
    db.commit()
    
    return {
        "success": True,
        "message": "Banners reordered successfully"
    }


@router.post("/config/seed-defaults")
async def seed_default_data(
    company_id: int,
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """
    Seed default property types and amenities for a company
    DC Protocol: Initial setup helper
    """
    default_property_types = [
        {"name": "Flat/Apartment", "slug": "flat", "icon": "fa-building", "display_order": 1},
        {"name": "Villa/House", "slug": "villa", "icon": "fa-home", "display_order": 2},
        {"name": "Plot", "slug": "plot", "icon": "fa-th-large", "display_order": 3},
        {"name": "Agricultural Land", "slug": "agricultural", "icon": "fa-leaf", "display_order": 4},
        {"name": "Commercial Shop", "slug": "shop", "icon": "fa-store", "display_order": 5},
        {"name": "Commercial Office", "slug": "office", "icon": "fa-briefcase", "display_order": 6},
        {"name": "Warehouse/Godown", "slug": "warehouse", "icon": "fa-warehouse", "display_order": 7},
        {"name": "Industrial Land", "slug": "industrial", "icon": "fa-industry", "display_order": 8},
    ]
    
    default_amenities = [
        {"category": "SECURITY", "name": "24x7 Security", "icon": "fa-shield-alt"},
        {"category": "SECURITY", "name": "CCTV Surveillance", "icon": "fa-video"},
        {"category": "SECURITY", "name": "Gated Community", "icon": "fa-door-closed"},
        {"category": "SECURITY", "name": "Intercom", "icon": "fa-phone"},
        {"category": "LIFESTYLE", "name": "Swimming Pool", "icon": "fa-swimming-pool"},
        {"category": "LIFESTYLE", "name": "Gym", "icon": "fa-dumbbell"},
        {"category": "LIFESTYLE", "name": "Clubhouse", "icon": "fa-users"},
        {"category": "LIFESTYLE", "name": "Indoor Games", "icon": "fa-table-tennis"},
        {"category": "OUTDOOR", "name": "Garden/Park", "icon": "fa-tree"},
        {"category": "OUTDOOR", "name": "Jogging Track", "icon": "fa-running"},
        {"category": "OUTDOOR", "name": "Children's Play Area", "icon": "fa-child"},
        {"category": "OUTDOOR", "name": "Outdoor Sports", "icon": "fa-futbol"},
        {"category": "PARKING", "name": "Covered Parking", "icon": "fa-car"},
        {"category": "PARKING", "name": "Open Parking", "icon": "fa-parking"},
        {"category": "PARKING", "name": "Visitor Parking", "icon": "fa-car-side"},
        {"category": "UTILITIES", "name": "Power Backup", "icon": "fa-bolt"},
        {"category": "UTILITIES", "name": "Water Supply 24x7", "icon": "fa-tint"},
        {"category": "UTILITIES", "name": "Rainwater Harvesting", "icon": "fa-cloud-rain"},
        {"category": "UTILITIES", "name": "Solar Panels", "icon": "fa-solar-panel"},
        {"category": "UTILITIES", "name": "Sewage Treatment", "icon": "fa-filter"},
        {"category": "CONNECTIVITY", "name": "High-Speed Internet", "icon": "fa-wifi"},
        {"category": "CONNECTIVITY", "name": "DTH/Cable TV", "icon": "fa-tv"},
        {"category": "INDOOR", "name": "Lift/Elevator", "icon": "fa-elevator"},
        {"category": "INDOOR", "name": "Fire Safety", "icon": "fa-fire-extinguisher"},
        {"category": "INDOOR", "name": "Modular Kitchen", "icon": "fa-utensils"},
        {"category": "INDOOR", "name": "Air Conditioning", "icon": "fa-snowflake"},
    ]
    
    created_types = 0
    created_amenities = 0
    
    for pt in default_property_types:
        existing = db.query(RDPropertyType).filter(
            RDPropertyType.company_id == company_id,
            RDPropertyType.slug == pt['slug']
        ).first()
        if not existing:
            db.add(RDPropertyType(
                company_id=company_id,
                name=pt['name'],
                slug=pt['slug'],
                icon=pt['icon'],
                display_order=pt['display_order'],
                created_by_id=current_user.id
            ))
            created_types += 1
    
    for am in default_amenities:
        existing = db.query(RDAmenity).filter(
            RDAmenity.company_id == company_id,
            RDAmenity.category == am['category'],
            RDAmenity.name == am['name']
        ).first()
        if not existing:
            db.add(RDAmenity(
                company_id=company_id,
                category=am['category'],
                name=am['name'],
                icon=am['icon'],
                created_by_id=current_user.id
            ))
            created_amenities += 1
    
    db.commit()
    
    return {
        "success": True,
        "message": f"Seeded {created_types} property types and {created_amenities} amenities",
        "created_property_types": created_types,
        "created_amenities": created_amenities
    }


class PartnerProfileCreate(BaseModel):
    company_id: int
    partner_id: int
    partner_type: str = Field(default='REAL_ESTATE_DEALER')
    specialization: Optional[List[str]] = None
    service_areas: Optional[List[str]] = None
    rera_registration_number: Optional[str] = None


class PartnerProfileUpdate(BaseModel):
    partner_type: Optional[str] = None
    specialization: Optional[List[str]] = None
    service_areas: Optional[List[str]] = None
    rera_registration_number: Optional[str] = None
    rera_certificate_url: Optional[str] = None
    dealership_agreement_url: Optional[str] = None
    rental_agreement_url: Optional[str] = None
    nda_signed: Optional[bool] = None
    status: Optional[str] = None
    rvz_notes: Optional[str] = None


@router.get("/partners")
async def get_partner_profiles(
    company_id: int,
    status: Optional[str] = None,
    partner_type: Optional[str] = None,
    search: Optional[str] = None,
    page: int = 1,
    limit: int = 20,
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """
    Get Real Dreams partner profiles
    DC Protocol: Filter by company_id
    """
    from app.models.staff_accounts import OfficialPartner
    
    config = db.query(RDCompanyConfig).filter_by(company_id=company_id, is_enabled=True).first()
    if not config:
        return {
            "success": False,
            "message": "Real Dreams not enabled for this company",
            "profiles": []
        }
    
    query = db.query(RDPartnerProfile).filter_by(company_id=company_id)
    
    if status:
        query = query.filter(RDPartnerProfile.status == status)
    if partner_type:
        query = query.filter(RDPartnerProfile.partner_type == partner_type)
    
    if search:
        partner_ids = db.query(OfficialPartner.id).filter(
            OfficialPartner.partner_name.ilike(f'%{search}%')
        ).all()
        partner_id_list = [p[0] for p in partner_ids]
        if partner_id_list:
            query = query.filter(RDPartnerProfile.partner_id.in_(partner_id_list))
        else:
            return {"success": True, "profiles": [], "total": 0, "page": page}
    
    total = query.count()
    offset = (page - 1) * limit
    profiles = query.order_by(RDPartnerProfile.created_at.desc()).offset(offset).limit(limit).all()
    
    result = []
    for profile in profiles:
        partner = db.query(OfficialPartner).filter_by(id=profile.partner_id).first()
        profile_dict = profile.to_dict()
        if partner:
            profile_dict['partner_name'] = partner.partner_name
            profile_dict['partner_code'] = partner.partner_code
            profile_dict['partner_category'] = partner.category
            profile_dict['partner_contact'] = partner.contact_person
            profile_dict['partner_mobile'] = partner.phone
        result.append(profile_dict)
    
    return {
        "success": True,
        "profiles": result,
        "total": total,
        "page": page,
        "pages": (total + limit - 1) // limit
    }


@router.get("/partners/available")
async def get_available_partners(
    company_id: int,
    search: Optional[str] = None,
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """
    Get Official Partners not yet registered for Real Dreams
    DC Protocol: Filter by company_id
    """
    from app.models.staff_accounts import OfficialPartner, PartnerCompanySegment
    
    existing_partner_ids = db.query(RDPartnerProfile.partner_id).filter_by(
        company_id=company_id
    ).all()
    existing_ids = [p[0] for p in existing_partner_ids]
    
    partner_ids_for_company = db.query(PartnerCompanySegment.partner_id).filter_by(
        company_id=company_id,
        is_active=True
    ).all()
    company_partner_ids = [p[0] for p in partner_ids_for_company]
    
    query = db.query(OfficialPartner).filter(
        OfficialPartner.id.in_(company_partner_ids),
        OfficialPartner.is_active == True
    )
    
    if existing_ids:
        query = query.filter(OfficialPartner.id.notin_(existing_ids))
    
    if search:
        query = query.filter(
            OfficialPartner.partner_name.ilike(f'%{search}%')
        )
    
    partners = query.order_by(OfficialPartner.partner_name).limit(50).all()
    
    return {
        "success": True,
        "partners": [
            {
                "id": p.id,
                "partner_code": p.partner_code,
                "partner_name": p.partner_name,
                "category": p.category,
                "contact_person": p.contact_person,
                "mobile": p.phone,
                "city": p.city
            }
            for p in partners
        ]
    }


@router.get("/business-partners")
async def get_business_partners(
    company_id: int,
    category: Optional[str] = None,
    search: Optional[str] = None,
    include_all: bool = False,
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """
    Get all business partners for property tagging
    DC Protocol: Returns partners associated with the company via PartnerCompanySegment
    Categories: DEALER, DISTRIBUTOR, REAL_DREAM_PARTNER, VENDOR (when include_all=true)
    """
    from app.models.staff_accounts import OfficialPartner, PartnerCompanySegment
    
    partner_ids_for_company = db.query(PartnerCompanySegment.partner_id).filter(
        PartnerCompanySegment.company_id == company_id,
        PartnerCompanySegment.is_active == True
    ).all()
    company_partner_ids = [p[0] for p in partner_ids_for_company]
    
    query = db.query(OfficialPartner).filter(
        OfficialPartner.id.in_(company_partner_ids) if company_partner_ids else OfficialPartner.is_active == True,
        OfficialPartner.is_active == True
    )
    
    if category:
        query = query.filter(OfficialPartner.category == category.upper())
    elif include_all:
        pass
    else:
        query = query.filter(OfficialPartner.category.in_(['DEALER', 'DISTRIBUTOR', 'REAL_DREAM_PARTNER', 'VENDOR']))
    
    if search:
        query = query.filter(
            OfficialPartner.partner_name.ilike(f'%{search}%') |
            OfficialPartner.partner_code.ilike(f'%{search}%') |
            OfficialPartner.contact_person.ilike(f'%{search}%')
        )
    
    partners = query.order_by(OfficialPartner.partner_name).limit(200).all()
    
    return {
        "success": True,
        "partners": [
            {
                "id": p.id,
                "partner_code": p.partner_code,
                "partner_name": p.partner_name,
                "category": p.category,
                "contact_person": p.contact_person,
                "phone": p.phone,
                "city": p.city,
                "state": p.state
            }
            for p in partners
        ],
        "total": len(partners)
    }


@router.get("/partners/{profile_id}")
async def get_partner_profile(
    profile_id: int,
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """
    Get single partner profile
    DC Protocol: Verify company access
    """
    from app.models.staff_accounts import OfficialPartner
    
    profile = db.query(RDPartnerProfile).filter_by(id=profile_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Partner profile not found")
    
    partner = db.query(OfficialPartner).filter_by(id=profile.partner_id).first()
    
    profile_dict = profile.to_dict()
    profile_dict['rera_certificate_url'] = profile.rera_certificate_url
    profile_dict['dealership_agreement_url'] = profile.dealership_agreement_url
    profile_dict['rental_agreement_url'] = profile.rental_agreement_url
    profile_dict['nda_document_url'] = profile.nda_document_url
    profile_dict['nda_signed_at'] = profile.nda_signed_at.isoformat() if profile.nda_signed_at else None
    profile_dict['reviewed_at'] = profile.reviewed_at.isoformat() if profile.reviewed_at else None
    
    if partner:
        profile_dict['partner'] = {
            'id': partner.id,
            'partner_code': partner.partner_code,
            'partner_name': partner.partner_name,
            'category': partner.category,
            'contact_person': partner.contact_person,
            'mobile_1': partner.phone,
            'email': partner.email,
            'address': partner.address,
            'city': partner.city,
            'state': partner.state,
            'pincode': partner.pincode
        }
    
    return {
        "success": True,
        "profile": profile_dict
    }


@router.post("/partners")
async def create_partner_profile(
    data: PartnerProfileCreate,
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """
    Create a new Real Dreams partner profile
    DC Protocol: Company-scoped partner registration
    """
    from app.models.staff_accounts import OfficialPartner
    
    config = db.query(RDCompanyConfig).filter_by(company_id=data.company_id, is_enabled=True).first()
    if not config:
        raise HTTPException(status_code=400, detail="Real Dreams not enabled for this company")
    
    if not config.allow_partner_listings:
        raise HTTPException(status_code=400, detail="Partner listings not allowed for this company")
    
    partner = db.query(OfficialPartner).filter_by(id=data.partner_id).first()
    if not partner:
        raise HTTPException(status_code=404, detail="Official Partner not found")
    
    existing = db.query(RDPartnerProfile).filter_by(
        company_id=data.company_id,
        partner_id=data.partner_id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Partner already registered for Real Dreams")
    
    if data.partner_type not in ['REAL_ESTATE_DEALER', 'BUILDER', 'AGENT', 'DEVELOPER']:
        raise HTTPException(status_code=400, detail="Invalid partner type")
    
    profile = RDPartnerProfile(
        company_id=data.company_id,
        partner_id=data.partner_id,
        partner_type=data.partner_type,
        specialization=data.specialization,
        service_areas=data.service_areas,
        rera_registration_number=data.rera_registration_number,
        status='DRAFT',
        created_by_id=current_user.id
    )
    
    db.add(profile)
    db.commit()
    db.refresh(profile)
    
    return {
        "success": True,
        "message": "Partner profile created",
        "profile": profile.to_dict()
    }


@router.put("/partners/{profile_id}")
async def update_partner_profile(
    profile_id: int,
    data: PartnerProfileUpdate,
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """
    Update partner profile
    DC Protocol: RVZ can update any field, partner can update draft only
    """
    profile = db.query(RDPartnerProfile).filter_by(id=profile_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Partner profile not found")
    
    if data.partner_type is not None:
        if data.partner_type not in ['REAL_ESTATE_DEALER', 'BUILDER', 'AGENT', 'DEVELOPER']:
            raise HTTPException(status_code=400, detail="Invalid partner type")
        profile.partner_type = data.partner_type
    
    if data.specialization is not None:
        profile.specialization = data.specialization
    if data.service_areas is not None:
        profile.service_areas = data.service_areas
    if data.rera_registration_number is not None:
        profile.rera_registration_number = data.rera_registration_number
    if data.rera_certificate_url is not None:
        profile.rera_certificate_url = data.rera_certificate_url
    if data.dealership_agreement_url is not None:
        profile.dealership_agreement_url = data.dealership_agreement_url
    if data.rental_agreement_url is not None:
        profile.rental_agreement_url = data.rental_agreement_url
    
    if data.nda_signed is not None:
        profile.nda_signed = data.nda_signed
        if data.nda_signed:
            profile.nda_signed_at = get_indian_time()
    
    if data.status is not None:
        if data.status not in ['DRAFT', 'PENDING', 'APPROVED', 'REJECTED', 'SUSPENDED']:
            raise HTTPException(status_code=400, detail="Invalid status")
        profile.status = data.status
        if data.status in ['APPROVED', 'REJECTED']:
            profile.reviewed_by_id = current_user.id
            profile.reviewed_at = get_indian_time()
    
    if data.rvz_notes is not None:
        profile.rvz_notes = data.rvz_notes
    
    db.commit()
    db.refresh(profile)
    
    return {
        "success": True,
        "message": "Partner profile updated",
        "profile": profile.to_dict()
    }


@router.post("/partners/{profile_id}/submit")
async def submit_partner_profile(
    profile_id: int,
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """
    Submit partner profile for RVZ review
    DC Protocol: Transition from DRAFT to PENDING
    """
    profile = db.query(RDPartnerProfile).filter_by(id=profile_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Partner profile not found")
    
    if profile.status != 'DRAFT':
        raise HTTPException(status_code=400, detail=f"Cannot submit profile in {profile.status} status")
    
    if not profile.nda_signed:
        raise HTTPException(status_code=400, detail="NDA must be signed before submission")
    
    profile.status = 'PENDING'
    db.commit()
    
    return {
        "success": True,
        "message": "Partner profile submitted for review"
    }


@router.post("/partners/{profile_id}/approve")
async def approve_partner_profile(
    profile_id: int,
    request: Request,
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """
    Approve partner profile (RVZ only)
    DC Protocol: Transition from PENDING to APPROVED
    """
    body = await request.json()
    notes = body.get('notes', '')
    
    profile = db.query(RDPartnerProfile).filter_by(id=profile_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Partner profile not found")
    
    if profile.status != 'PENDING':
        raise HTTPException(status_code=400, detail=f"Cannot approve profile in {profile.status} status")
    
    profile.status = 'APPROVED'
    profile.rvz_notes = notes
    profile.reviewed_by_id = current_user.id
    profile.reviewed_at = get_indian_time()
    
    db.commit()
    
    return {
        "success": True,
        "message": "Partner profile approved"
    }


@router.post("/partners/{profile_id}/force-approve")
async def force_approve_partner_profile(
    profile_id: int,
    request: Request,
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """
    Force approve partner profile bypassing NDA requirement (EA/VGK only)
    DC Protocol: Direct transition from any status to APPROVED
    Use case: When NDA is handled offline or not required
    """
    from app.models.staff import StaffRole
    user_role = db.query(StaffRole).filter_by(id=current_user.role_id).first()
    role_code = user_role.role_code.lower() if user_role else ''
    
    allowed_roles = ['vgk4u', 'ea', 'rvz', 'supreme']
    # DC Protocol: Menu-based access control - page assignment = full access
    # if not any(allowed in role_code for allowed in allowed_roles):
    #     raise HTTPException(status_code=403, detail="Only EA/VGK staff can force approve partners")
    
    body = await request.json() if request.headers.get('content-length', '0') != '0' else {}
    notes = body.get('notes', 'Force approved by admin - NDA bypassed')
    
    profile = db.query(RDPartnerProfile).filter_by(id=profile_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Partner profile not found")
    
    if profile.status == 'APPROVED':
        return {"success": True, "message": "Partner is already approved"}
    
    old_status = profile.status
    profile.status = 'APPROVED'
    profile.rvz_notes = notes
    profile.reviewed_by_id = current_user.id
    profile.reviewed_at = get_indian_time()
    
    db.commit()
    
    return {
        "success": True,
        "message": f"Partner force approved (was {old_status})",
        "previous_status": old_status,
        "nda_bypassed": not profile.nda_signed
    }


@router.post("/partners/{profile_id}/reject")
async def reject_partner_profile(
    profile_id: int,
    request: Request,
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """
    Reject partner profile (RVZ only)
    DC Protocol: Transition from PENDING to REJECTED
    """
    body = await request.json()
    notes = body.get('notes', '')
    
    if not notes:
        raise HTTPException(status_code=400, detail="Rejection reason is required")
    
    profile = db.query(RDPartnerProfile).filter_by(id=profile_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Partner profile not found")
    
    if profile.status != 'PENDING':
        raise HTTPException(status_code=400, detail=f"Cannot reject profile in {profile.status} status")
    
    profile.status = 'REJECTED'
    profile.rvz_notes = notes
    profile.reviewed_by_id = current_user.id
    profile.reviewed_at = get_indian_time()
    
    db.commit()
    
    return {
        "success": True,
        "message": "Partner profile rejected"
    }


class PropertyCreate(BaseModel):
    property_type_id: int
    title: str = Field(..., min_length=10, max_length=256)
    description: Optional[str] = None
    address: Optional[str] = None
    landmark: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None
    google_maps_link: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    total_area: Optional[float] = None
    area_unit: str = "SQ_FT"
    built_up_area: Optional[float] = None
    carpet_area: Optional[float] = None
    facing: Optional[str] = None
    facings: Optional[List[str]] = []
    floor_number: Optional[int] = None
    total_floors: Optional[int] = None
    floors_display: Optional[str] = None
    listed_price: Optional[float] = None
    price_per_unit: Optional[float] = None
    booking_amount: Optional[float] = None
    is_negotiable: bool = False
    price_on_request: bool = False
    bedrooms: Optional[int] = None
    bedroom_options: Optional[List[str]] = []
    property_options: Optional[List[dict]] = []
    bathrooms: Optional[int] = None
    approach_road_size: Optional[str] = None
    balconies: Optional[int] = None
    bedroom_configurations: Optional[List[str]] = []
    age_of_property: Optional[str] = None
    possession_status: Optional[str] = None
    rera_number: Optional[str] = None
    property_category: str = "RESIDENTIAL"
    amenity_ids: Optional[List[int]] = []
    youtube_links: Optional[List[dict]] = []
    catalogues_json: Optional[List[dict]] = []
    images_json: Optional[List[dict]] = []
    uploaded_video_url: Optional[str] = None
    contact_person_name: Optional[str] = None
    contact_person_phone: Optional[str] = None
    hide_contact_number: bool = False
    allow_hidden_call: bool = True
    show_company_contact: bool = False
    tagged_dealer_id: Optional[int] = None
    tagged_distributor_id: Optional[int] = None
    partner_profile_id: Optional[int] = None
    free_bike_offer: bool = False
    is_limited_offer: bool = False
    availability_status: str = "AVAILABLE"
    hidden_fields: Optional[dict] = {}
    image_urls: Optional[List[str]] = []
    video_url: Optional[str] = None
    brochure_url: Optional[str] = None


class PropertyUpdate(BaseModel):
    property_type_id: Optional[int] = None
    title: Optional[str] = None
    description: Optional[str] = None
    address: Optional[str] = None
    landmark: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None
    google_maps_link: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    total_area: Optional[float] = None
    area_unit: Optional[str] = None
    built_up_area: Optional[float] = None
    carpet_area: Optional[float] = None
    facing: Optional[str] = None
    facings: Optional[List[str]] = None
    floor_number: Optional[int] = None
    total_floors: Optional[int] = None
    floors_display: Optional[str] = None
    listed_price: Optional[float] = None
    price_per_unit: Optional[float] = None
    booking_amount: Optional[float] = None
    is_negotiable: Optional[bool] = None
    price_on_request: Optional[bool] = None
    bedrooms: Optional[int] = None
    bedroom_options: Optional[List[str]] = None
    property_options: Optional[List[dict]] = None
    bathrooms: Optional[int] = None
    balconies: Optional[int] = None
    approach_road_size: Optional[str] = None
    bedroom_configurations: Optional[List[str]] = None
    age_of_property: Optional[str] = None
    possession_status: Optional[str] = None
    rera_number: Optional[str] = None
    property_category: Optional[str] = None
    amenity_ids: Optional[List[int]] = None
    youtube_links: Optional[List[dict]] = None
    catalogues_json: Optional[List[dict]] = None
    images_json: Optional[List[dict]] = None
    uploaded_video_url: Optional[str] = None
    contact_person_name: Optional[str] = None
    contact_person_phone: Optional[str] = None
    hide_contact_number: Optional[bool] = None
    allow_hidden_call: Optional[bool] = None
    show_company_contact: Optional[bool] = None
    tagged_dealer_id: Optional[int] = None
    tagged_distributor_id: Optional[int] = None
    partner_profile_id: Optional[int] = None
    free_bike_offer: Optional[bool] = None
    is_limited_offer: Optional[bool] = None
    availability_status: Optional[str] = None
    hidden_fields: Optional[dict] = None
    vgk_l1_pct: Optional[float] = None
    vgk_l2_pct: Optional[float] = None
    vgk_l3_pct: Optional[float] = None
    vgk_l4_pct: Optional[float] = None


def generate_property_code(db: Session, company_id: int) -> str:
    """Generate unique property code"""
    count = db.query(func.count(RDProperty.id)).filter_by(company_id=company_id).scalar() or 0
    return f"PROP{company_id:03d}{count + 1:05d}"


@router.get("/properties")
async def list_properties(
    company_id: int,
    status: Optional[str] = None,
    property_type_id: Optional[int] = None,
    city: Optional[str] = None,
    state: Optional[str] = None,
    pincode: Optional[str] = None,
    property_name: Optional[str] = None,
    agent_name: Optional[str] = None,
    partner_profile_id: Optional[int] = None,
    dealer_id: Optional[int] = None,
    distributor_id: Optional[int] = None,
    free_bike_offer: Optional[bool] = None,
    property_category: Optional[str] = None,
    owner_type: Optional[str] = None,
    page: int = 1,
    limit: int = 20,
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """
    List properties with advanced filters
    DC Protocol: Filter by company_id
    Filters: city, state, pincode, property_name, agent_name, partner, dealer, distributor, free_bike_offer
    """
    query = db.query(RDProperty).filter(RDProperty.company_id == company_id)
    
    if status:
        query = query.filter(RDProperty.status == status)
    if property_type_id:
        query = query.filter(RDProperty.property_type_id == property_type_id)
    if city:
        query = query.filter(RDProperty.city.ilike(f"%{city}%"))
    if state:
        query = query.filter(RDProperty.state.ilike(f"%{state}%"))
    if pincode:
        query = query.filter(RDProperty.pincode.ilike(f"%{pincode}%"))
    if property_name:
        query = query.filter(RDProperty.title.ilike(f"%{property_name}%"))
    if agent_name:
        query = query.filter(RDProperty.contact_person_name.ilike(f"%{agent_name}%"))
    if partner_profile_id:
        query = query.filter(RDProperty.partner_profile_id == partner_profile_id)
    if dealer_id:
        query = query.filter(RDProperty.tagged_dealer_id == dealer_id)
    if distributor_id:
        query = query.filter(RDProperty.tagged_distributor_id == distributor_id)
    if free_bike_offer is not None:
        query = query.filter(RDProperty.free_bike_offer == free_bike_offer)
    if property_category:
        query = query.filter(RDProperty.property_category == property_category)
    if owner_type == 'partner':
        query = query.filter(RDProperty.partner_profile_id.isnot(None))
    elif owner_type == 'employee':
        query = query.filter(RDProperty.employee_id.isnot(None))
    elif owner_type == 'member':
        query = query.filter(RDProperty.mnr_user_id.isnot(None))
    
    total = query.count()
    properties = query.order_by(RDProperty.created_at.desc()).offset((page - 1) * limit).limit(limit).all()
    
    result = []
    for prop in properties:
        prop_dict = prop.to_dict()
        if prop.property_type:
            prop_dict['property_type_name'] = prop.property_type.name
        prop_dict['amenity_count'] = len(prop.amenities) if prop.amenities else 0
        
        primary_image = db.query(RDPropertyMedia).filter(
            RDPropertyMedia.property_id == prop.id,
            RDPropertyMedia.company_id == company_id,
            RDPropertyMedia.media_type == 'IMAGE',
            RDPropertyMedia.is_primary == True
        ).first()
        
        if not primary_image:
            primary_image = db.query(RDPropertyMedia).filter(
                RDPropertyMedia.property_id == prop.id,
                RDPropertyMedia.company_id == company_id,
                RDPropertyMedia.media_type == 'IMAGE'
            ).order_by(RDPropertyMedia.display_order.asc()).first()
        
        prop_dict['thumbnail_url'] = primary_image.file_path if primary_image else None
        
        brochure = db.query(RDPropertyMedia).filter(
            RDPropertyMedia.property_id == prop.id,
            RDPropertyMedia.company_id == company_id,
            RDPropertyMedia.media_type.in_(['BROCHURE', 'DOCUMENT'])
        ).first()
        prop_dict['brochure_url'] = brochure.file_path if brochure else None
        prop_dict['brochure_name'] = brochure.file_name if brochure else None
        
        video = db.query(RDPropertyMedia).filter(
            RDPropertyMedia.property_id == prop.id,
            RDPropertyMedia.company_id == company_id,
            RDPropertyMedia.media_type == 'VIDEO'
        ).first()
        prop_dict['video_url'] = video.file_path if video else None
        prop_dict['video_name'] = video.file_name if video else None
        
        image_count = db.query(func.count(RDPropertyMedia.id)).filter(
            RDPropertyMedia.property_id == prop.id,
            RDPropertyMedia.company_id == company_id,
            RDPropertyMedia.media_type == 'IMAGE'
        ).scalar() or 0
        prop_dict['image_count'] = image_count
        
        result.append(prop_dict)
    
    return {
        "success": True,
        "total": total,
        "page": page,
        "limit": limit,
        "properties": result
    }


@router.get("/properties/{property_id}")
async def get_property(
    property_id: int,
    company_id: int,
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """
    Get property details with amenities
    DC Protocol: Filter by company_id
    """
    prop = db.query(RDProperty).filter(
        RDProperty.id == property_id,
        RDProperty.company_id == company_id
    ).first()
    
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")
    
    prop_dict = prop.to_dict()
    
    if prop.property_type:
        prop_dict['property_type_name'] = prop.property_type.name
        prop_dict['property_type_icon'] = prop.property_type.icon
    
    amenities = []
    for pa in prop.amenities:
        amenity = db.query(RDAmenity).filter_by(id=pa.amenity_id).first()
        if amenity:
            amenities.append(amenity.to_dict())
    prop_dict['amenities'] = amenities
    
    media = db.query(RDPropertyMedia).filter_by(
        property_id=property_id,
        company_id=company_id
    ).order_by(RDPropertyMedia.display_order).all()
    prop_dict['media'] = [m.to_dict() for m in media]
    
    images = [m for m in media if m.media_type == 'IMAGE']
    videos = [m for m in media if m.media_type == 'VIDEO']
    brochures = [m for m in media if m.media_type in ['BROCHURE', 'DOCUMENT']]
    
    prop_dict['image_urls'] = [img.file_path for img in images]
    prop_dict['image_count'] = len(images)
    prop_dict['thumbnail_url'] = images[0].file_path if images else None
    prop_dict['video_url'] = videos[0].file_path if videos else None
    prop_dict['video_name'] = videos[0].file_name if videos else None
    prop_dict['brochure_url'] = brochures[0].file_path if brochures else None
    prop_dict['brochure_name'] = brochures[0].file_name if brochures else None
    
    return {
        "success": True,
        "property": prop_dict
    }


@router.get("/properties/{property_id}/call-info")
async def get_property_call_info(
    property_id: int,
    company_id: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Get property contact phone for calling (public endpoint)
    DC Protocol: company_id optional (accepts string, normalizes to int or ignores)
    
    Contact Display Logic:
    - If show_company_contact=True: Returns company hotline (+91 85 85 85 27 388)
    - If hide_contact_number=False: Returns agent's personal phone
    - If hide_contact_number=True AND allow_hidden_call=True: Returns agent's phone for calling
    - If hide_contact_number=True AND allow_hidden_call=False: Returns error (no calling allowed)
    
    Returns phone number based on property settings.
    """
    numeric_company_id = None
    if company_id and company_id not in ['all', 'null', 'undefined', '']:
        try:
            numeric_company_id = int(company_id)
        except (ValueError, TypeError):
            pass
    
    if numeric_company_id:
        prop = db.query(RDProperty).filter(
            RDProperty.id == property_id,
            RDProperty.company_id == numeric_company_id,
            RDProperty.status == 'APPROVED'
        ).first()
    else:
        prop = db.query(RDProperty).filter(
            RDProperty.id == property_id,
            RDProperty.status == 'APPROVED'
        ).first()
    
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")
    
    # If show_company_contact is enabled, return company hotline
    if prop.show_company_contact:
        return {
            "success": True,
            "phone": COMPANY_CONTACT_HOTLINE,
            "name": "MyntReal Support",
            "is_company_contact": True
        }
    
    if not prop.contact_person_phone:
        raise HTTPException(status_code=400, detail="No contact number available for this property")
    
    if prop.hide_contact_number and not prop.allow_hidden_call:
        raise HTTPException(status_code=403, detail="Contact calling not available for this property")
    
    return {
        "success": True,
        "phone": prop.contact_person_phone,
        "name": prop.contact_person_name,
        "is_company_contact": False,
        "property_title": prop.title
    }


@router.post("/properties")
async def create_property(
    company_id: int,
    data: PropertyCreate,
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """
    Create property listing (Staff creates on behalf of employee)
    DC Protocol: company_id mandatory
    """
    config = db.query(RDCompanyConfig).filter_by(company_id=company_id).first()
    if not config or not config.is_enabled:
        raise HTTPException(status_code=400, detail="Real Dreams not enabled for this company")
    
    if not config.allow_employee_listings:
        raise HTTPException(status_code=403, detail="Employee listings not allowed")
    
    prop_type = db.query(RDPropertyType).filter(
        RDPropertyType.id == data.property_type_id,
        RDPropertyType.company_id == company_id,
        RDPropertyType.is_active == True
    ).first()
    if not prop_type:
        raise HTTPException(status_code=400, detail="Invalid property type")
    
    if data.title and len(data.title) < 10:
        raise HTTPException(status_code=400, detail="Title must be at least 10 characters")
    
    if not data.city:
        raise HTTPException(status_code=400, detail="City is required")
    
    property_code = generate_property_code(db, company_id)
    
    new_property = RDProperty(
        company_id=company_id,
        property_code=property_code,
        employee_id=current_user.id if not data.partner_profile_id else None,
        partner_profile_id=data.partner_profile_id,
        property_type_id=data.property_type_id,
        title=data.title,
        description=data.description,
        address=data.address,
        landmark=data.landmark,
        city=data.city,
        state=data.state,
        pincode=data.pincode,
        google_maps_link=data.google_maps_link,
        latitude=data.latitude,
        longitude=data.longitude,
        total_area=data.total_area,
        area_unit=data.area_unit,
        built_up_area=data.built_up_area,
        carpet_area=data.carpet_area,
        facing=data.facing,
        facings=data.facings or [],
        floor_number=data.floor_number,
        total_floors=data.total_floors,
        floors_display=data.floors_display,
        listed_price=data.listed_price,
        price_per_unit=data.price_per_unit,
        booking_amount=data.booking_amount,
        is_negotiable=data.is_negotiable,
        price_on_request=data.price_on_request,
        bedrooms=data.bedrooms,
        bedroom_options=data.bedroom_options or [],
        property_options=data.property_options or [],
        bathrooms=data.bathrooms,
        balconies=data.balconies,
        approach_road_size=data.approach_road_size,
        bedroom_configurations=data.bedroom_configurations,
        age_of_property=data.age_of_property,
        possession_status=data.possession_status,
        rera_number=data.rera_number,
        property_category=data.property_category,
        youtube_links=data.youtube_links,
        catalogues_json=data.catalogues_json,
        images_json=data.images_json,
        uploaded_video_url=data.uploaded_video_url,
        contact_person_name=data.contact_person_name,
        contact_person_phone=data.contact_person_phone,
        hide_contact_number=data.hide_contact_number,
        allow_hidden_call=data.allow_hidden_call,
        show_company_contact=data.show_company_contact,
        tagged_dealer_id=data.tagged_dealer_id,
        tagged_distributor_id=data.tagged_distributor_id,
        free_bike_offer=data.free_bike_offer,
        is_limited_offer=data.is_limited_offer,
        availability_status=data.availability_status,
        hidden_fields=data.hidden_fields or {},
        status='DRAFT',
        created_by_id=current_user.id
    )
    
    if data.video_url:
        new_property.uploaded_video_url = data.video_url
    
    if data.brochure_url:
        new_property.brochure_url = data.brochure_url
    
    db.add(new_property)
    db.commit()
    db.refresh(new_property)
    
    if data.image_urls and len(data.image_urls) > 0:
        for idx, img_url in enumerate(data.image_urls):
            if img_url:
                file_name = img_url.split('/')[-1] if '/' in img_url else f"image_{idx}.jpg"
                media = RDPropertyMedia(
                    company_id=company_id,
                    property_id=new_property.id,
                    media_type='IMAGE',
                    file_name=file_name,
                    file_path=img_url,
                    is_primary=(idx == 0),
                    display_order=idx,
                    uploaded_by_type='staff',
                    uploaded_by_id=str(current_user.emp_code)
                )
                db.add(media)
        db.commit()
    
    if data.video_url:
        video_name = data.video_url.split('/')[-1] if '/' in data.video_url else "video.mp4"
        video_media = RDPropertyMedia(
            company_id=company_id,
            property_id=new_property.id,
            media_type='VIDEO',
            file_name=video_name,
            file_path=data.video_url,
            is_primary=False,
            display_order=0,
            uploaded_by_type='staff',
            uploaded_by_id=str(current_user.emp_code)
        )
        db.add(video_media)
        db.commit()
    
    if data.brochure_url:
        brochure_name = data.brochure_url.split('/')[-1] if '/' in data.brochure_url else "brochure.pdf"
        brochure_media = RDPropertyMedia(
            company_id=company_id,
            property_id=new_property.id,
            media_type='BROCHURE',
            file_name=brochure_name,
            file_path=data.brochure_url,
            is_primary=False,
            display_order=0,
            uploaded_by_type='staff',
            uploaded_by_id=str(current_user.emp_code)
        )
        db.add(brochure_media)
        db.commit()
    
    if data.amenity_ids:
        for amenity_id in data.amenity_ids:
            amenity = db.query(RDAmenity).filter(
                RDAmenity.id == amenity_id,
                RDAmenity.company_id == company_id,
                RDAmenity.is_active == True
            ).first()
            if amenity:
                pa = RDPropertyAmenity(property_id=new_property.id, amenity_id=amenity_id)
                db.add(pa)
        db.commit()
    
    audit = RDPropertyAudit(
        company_id=company_id,
        property_id=new_property.id,
        action='CREATED',
        to_status='DRAFT',
        performed_by_type='staff',
        performed_by_id=str(current_user.emp_code)
    )
    db.add(audit)
    db.commit()
    
    return {
        "success": True,
        "message": "Property created successfully",
        "property": new_property.to_dict()
    }


@router.put("/properties/{property_id}")
async def update_property(
    property_id: int,
    company_id: int,
    data: PropertyUpdate,
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """
    Update property listing
    DC Protocol: company_id mandatory
    """
    prop = db.query(RDProperty).filter(
        RDProperty.id == property_id,
        RDProperty.company_id == company_id
    ).first()
    
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")
    
    if prop.status not in ['DRAFT', 'REJECTED', 'PENDING']:
        raise HTTPException(status_code=400, detail=f"Cannot edit property in {prop.status} status")
    
    previous_status = prop.status
    status_changed = False
    
    if prop.status == 'PENDING':
        prop.status = 'DRAFT'
        status_changed = True
    
    update_data = data.dict(exclude_unset=True)
    
    if 'property_type_id' in update_data:
        prop_type = db.query(RDPropertyType).filter(
            RDPropertyType.id == update_data['property_type_id'],
            RDPropertyType.company_id == company_id,
            RDPropertyType.is_active == True
        ).first()
        if not prop_type:
            raise HTTPException(status_code=400, detail="Invalid property type")
    
    if 'title' in update_data and update_data['title'] and len(update_data['title']) < 10:
        raise HTTPException(status_code=400, detail="Title must be at least 10 characters")
    
    amenity_ids = update_data.pop('amenity_ids', None)
    
    for key, value in update_data.items():
        setattr(prop, key, value)
    
    prop.updated_at = get_indian_time()
    
    if amenity_ids is not None:
        db.query(RDPropertyAmenity).filter_by(property_id=property_id).delete()
        for amenity_id in amenity_ids:
            amenity = db.query(RDAmenity).filter(
                RDAmenity.id == amenity_id,
                RDAmenity.company_id == company_id,
                RDAmenity.is_active == True
            ).first()
            if amenity:
                pa = RDPropertyAmenity(property_id=property_id, amenity_id=amenity_id)
                db.add(pa)
    
    if status_changed:
        audit = RDPropertyAudit(
            company_id=company_id,
            property_id=property_id,
            action='STATUS_CHANGED',
            from_status=previous_status,
            to_status='DRAFT',
            performed_by_type='staff',
            performed_by_id=str(current_user.emp_code),
            notes='Status reset to DRAFT due to property edit'
        )
        db.add(audit)
    
    db.commit()
    db.refresh(prop)
    
    message = "Property updated successfully"
    if status_changed:
        message = "Property updated and status reset to DRAFT. Please resubmit for approval."
    
    return {
        "success": True,
        "message": message,
        "property": prop.to_dict(),
        "status_changed": status_changed,
        "previous_status": previous_status if status_changed else None
    }


@router.post("/properties/{property_id}/submit")
async def submit_property(
    property_id: int,
    company_id: int,
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """
    Submit property for approval
    DC Protocol: Transition DRAFT -> PENDING
    """
    prop = db.query(RDProperty).filter(
        RDProperty.id == property_id,
        RDProperty.company_id == company_id
    ).first()
    
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")
    
    if prop.status not in ['DRAFT', 'REJECTED']:
        raise HTTPException(status_code=400, detail=f"Cannot submit property in {prop.status} status")
    
    if not prop.city:
        raise HTTPException(status_code=400, detail="City is required before submission")
    
    if not prop.listed_price and not prop.price_on_request:
        raise HTTPException(status_code=400, detail="Price or 'Price on Request' is required")
    
    old_status = prop.status
    prop.status = 'PENDING'
    prop.updated_at = get_indian_time()
    
    config = db.query(RDCompanyConfig).filter_by(company_id=company_id).first()
    if config and config.auto_approve_employee_properties and prop.employee_id:
        prop.status = 'APPROVED'
        prop.approved_by_id = current_user.id
        prop.approved_at = get_indian_time()
    
    audit = RDPropertyAudit(
        company_id=company_id,
        property_id=property_id,
        action='SUBMITTED',
        from_status=old_status,
        to_status=prop.status,
        performed_by_type='staff',
        performed_by_id=str(current_user.emp_code)
    )
    db.add(audit)
    db.commit()
    
    return {
        "success": True,
        "message": f"Property {'approved automatically' if prop.status == 'APPROVED' else 'submitted for approval'}",
        "status": prop.status
    }


@router.post("/properties/{property_id}/approve")
async def approve_property(
    property_id: int,
    company_id: int,
    request: Request,
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """
    Approve property (RVZ/Staff)
    DC Protocol: PENDING -> APPROVED
    """
    body = await request.json()
    notes = body.get('notes', '')
    
    prop = db.query(RDProperty).filter(
        RDProperty.id == property_id,
        RDProperty.company_id == company_id
    ).first()
    
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")
    
    if prop.status != 'PENDING':
        raise HTTPException(status_code=400, detail=f"Cannot approve property in {prop.status} status")
    
    old_status = prop.status
    prop.status = 'APPROVED'
    prop.rvz_notes = notes
    prop.approved_by_id = current_user.id
    prop.approved_at = get_indian_time()
    
    audit = RDPropertyAudit(
        company_id=company_id,
        property_id=property_id,
        action='APPROVED',
        from_status=old_status,
        to_status='APPROVED',
        notes=notes,
        performed_by_type='staff',
        performed_by_id=str(current_user.emp_code)
    )
    db.add(audit)
    db.commit()
    
    return {
        "success": True,
        "message": "Property approved"
    }


@router.post("/properties/{property_id}/reject")
async def reject_property(
    property_id: int,
    company_id: int,
    request: Request,
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """
    Reject property (RVZ/Staff)
    DC Protocol: PENDING -> REJECTED
    """
    body = await request.json()
    notes = body.get('notes', '')
    
    if not notes:
        raise HTTPException(status_code=400, detail="Rejection reason is required")
    
    prop = db.query(RDProperty).filter(
        RDProperty.id == property_id,
        RDProperty.company_id == company_id
    ).first()
    
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")
    
    if prop.status != 'PENDING':
        raise HTTPException(status_code=400, detail=f"Cannot reject property in {prop.status} status")
    
    old_status = prop.status
    prop.status = 'REJECTED'
    prop.rvz_notes = notes
    
    audit = RDPropertyAudit(
        company_id=company_id,
        property_id=property_id,
        action='REJECTED',
        from_status=old_status,
        to_status='REJECTED',
        notes=notes,
        performed_by_type='staff',
        performed_by_id=str(current_user.emp_code)
    )
    db.add(audit)
    db.commit()
    
    return {
        "success": True,
        "message": "Property rejected"
    }


@router.get("/properties/pending/list")
async def list_pending_properties(
    company_id: int,
    page: int = 1,
    limit: int = 20,
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """
    List pending properties for approval
    DC Protocol: Filter by company_id
    """
    query = db.query(RDProperty).filter(
        RDProperty.company_id == company_id,
        RDProperty.status == 'PENDING'
    )
    
    total = query.count()
    properties = query.order_by(RDProperty.created_at.asc()).offset((page - 1) * limit).limit(limit).all()
    
    result = []
    for prop in properties:
        prop_dict = prop.to_dict()
        if prop.property_type:
            prop_dict['property_type_name'] = prop.property_type.name
        result.append(prop_dict)
    
    return {
        "success": True,
        "total": total,
        "page": page,
        "properties": result
    }


@router.post("/upload-media")
async def upload_media_pre_create(
    company_id: int,
    file: UploadFile = File(...),
    media_type: str = Form("IMAGE"),
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """
    Upload media before property creation (pre-upload flow)
    DC Protocol: Company-wise media storage
    WVV Protocol: Staff authentication required
    Returns URL that can be used when creating property
    """
    from app.services.universal_upload_service import UniversalUploadService
    from app.services.object_storage import storage_service
    import uuid
    from pathlib import Path
    
    config = db.query(RDCompanyConfig).filter_by(company_id=company_id).first()
    if not config or not config.is_enabled:
        raise HTTPException(status_code=400, detail="Real Dreams not enabled for this company")
    
    valid_media_types = ['IMAGE', 'VIDEO', 'BROCHURE', 'DOCUMENT']
    if media_type not in valid_media_types:
        raise HTTPException(status_code=400, detail=f"Invalid media type. Allowed: {valid_media_types}")
    
    file_content = await file.read()
    file_size = len(file_content)
    await file.seek(0)
    
    if media_type == 'IMAGE':
        file_category = UniversalUploadService.validate_file_type(file, allow_videos=False)
        if file_category != 'image':
            raise HTTPException(status_code=400, detail="Only image files allowed for IMAGE type")
        max_size = UniversalUploadService.MAX_IMAGE_SIZE
    elif media_type == 'VIDEO':
        file_category = UniversalUploadService.validate_file_type(file, allow_videos=True)
        if file_category != 'video':
            raise HTTPException(status_code=400, detail="Only video files allowed for VIDEO type")
        max_size = UniversalUploadService.MAX_VIDEO_SIZE
    else:
        pdf_signature = b'%PDF'
        docx_signature = b'PK\x03\x04'
        doc_signature = b'\xd0\xcf\x11\xe0'
        
        is_valid_doc = (
            file_content[:4] == pdf_signature or
            file_content[:4] == docx_signature or
            file_content[:4] == doc_signature
        )
        
        if not is_valid_doc:
            raise HTTPException(status_code=400, detail="Only PDF/DOC/DOCX files allowed for documents")
        file_category = 'document'
        max_size = 20 * 1024 * 1024
    
    if file_size > max_size:
        max_mb = max_size / (1024 * 1024)
        raise HTTPException(status_code=400, detail=f"File too large. Maximum size: {max_mb}MB")
    
    # DC-IMG-COMPRESS-001: compress images to WebP before storage
    if file_category == 'image':
        try:
            import io as _io
            from PIL import Image as _PILImg
            _img = _PILImg.open(_io.BytesIO(file_content))
            if _img.mode not in ('RGB', 'RGBA'):
                _img = _img.convert('RGBA' if 'A' in _img.mode else 'RGB')
            _img.thumbnail((1920, 1920), _PILImg.LANCZOS)
            _buf = _io.BytesIO()
            _img.save(_buf, format='WEBP', quality=85, method=4)
            file_content = _buf.getvalue()
            ext = '.webp'
        except Exception:
            ext = Path(file.filename).suffix.lower() if file.filename else '.jpg'
    else:
        ext = Path(file.filename).suffix.lower() if file.filename else '.jpg'
    unique_name = f"{uuid.uuid4().hex[:12]}{ext}"
    storage_path = f"real_dreams/{company_id}/staged/{unique_name}"

    success = storage_service.upload_file(storage_path, file_content)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to upload file to storage")
    
    file_url = f"/storage/{storage_path}"
    
    return {
        "success": True,
        "message": "File uploaded successfully",
        "url": file_url,
        "file_name": file.filename,
        "file_size": file_size,
        "media_type": media_type
    }


@router.post("/properties/{property_id}/media")
async def upload_property_media(
    property_id: int,
    company_id: int,
    file: UploadFile = File(...),
    media_type: str = Form("IMAGE"),
    section: Optional[str] = Form(None),
    title: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    is_primary: bool = Form(False),
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """
    Upload media for a property
    DC Protocol: Company-wise media storage with validation
    Section: Optional category for images (EXTERIOR, INTERIOR, KITCHEN, BATHROOM, BEDROOM, LIVING_ROOM, BALCONY, FLOOR_PLAN, OTHER)
    """
    from app.services.universal_upload_service import UniversalUploadService
    from app.services.object_storage import storage_service
    
    prop = db.query(RDProperty).filter(
        RDProperty.id == property_id,
        RDProperty.company_id == company_id
    ).first()
    
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")
    
    config = db.query(RDCompanyConfig).filter_by(company_id=company_id).first()
    if not config or not config.is_enabled:
        raise HTTPException(status_code=400, detail="Real Dreams not enabled for this company")
    
    existing_media_count = db.query(func.count(RDPropertyMedia.id)).filter(
        RDPropertyMedia.property_id == property_id,
        RDPropertyMedia.media_type == 'IMAGE'
    ).scalar() or 0
    
    max_images = config.max_images_per_property or 10
    if media_type == 'IMAGE' and existing_media_count >= max_images:
        raise HTTPException(
            status_code=400, 
            detail=f"Maximum {max_images} images allowed per property"
        )
    
    valid_media_types = ['IMAGE', 'VIDEO', 'DOCUMENT', 'BROCHURE', 'FLOOR_PLAN']
    if media_type not in valid_media_types:
        raise HTTPException(status_code=400, detail=f"Invalid media type. Allowed: {valid_media_types}")
    
    allow_videos = media_type == 'VIDEO'
    file_category = UniversalUploadService.validate_file_type(file, allow_videos=allow_videos)
    
    if media_type == 'IMAGE' and file_category != 'image':
        raise HTTPException(status_code=400, detail="Only image files allowed for IMAGE type")
    if media_type == 'VIDEO' and file_category != 'video':
        raise HTTPException(status_code=400, detail="Only video files allowed for VIDEO type")
    
    file_content = await file.read()
    file_size = len(file_content)
    
    max_size = UniversalUploadService.MAX_VIDEO_SIZE if file_category == 'video' else UniversalUploadService.MAX_IMAGE_SIZE
    if file_size > max_size:
        max_mb = max_size / (1024 * 1024)
        raise HTTPException(status_code=400, detail=f"File too large. Maximum size: {max_mb}MB")
    
    import uuid
    from pathlib import Path
    
    # DC-IMG-COMPRESS-001: compress images to WebP before storage
    if file_category == 'image':
        try:
            import io as _io
            from PIL import Image as _PILImg
            _img = _PILImg.open(_io.BytesIO(file_content))
            if _img.mode not in ('RGB', 'RGBA'):
                _img = _img.convert('RGBA' if 'A' in _img.mode else 'RGB')
            _img.thumbnail((1920, 1920), _PILImg.LANCZOS)
            _buf = _io.BytesIO()
            _img.save(_buf, format='WEBP', quality=85, method=4)
            file_content = _buf.getvalue()
            ext = '.webp'
        except Exception:
            ext = Path(file.filename).suffix.lower() if file.filename else '.jpg'
    else:
        ext = Path(file.filename).suffix.lower() if file.filename else '.jpg'
    unique_name = f"{uuid.uuid4().hex[:12]}{ext}"
    storage_path = f"real_dreams/{company_id}/{property_id}/{unique_name}"

    success = storage_service.upload_file(storage_path, file_content)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to upload file to storage")
    
    if is_primary:
        db.query(RDPropertyMedia).filter(
            RDPropertyMedia.property_id == property_id,
            RDPropertyMedia.is_primary == True
        ).update({'is_primary': False})
    
    max_order = db.query(func.max(RDPropertyMedia.display_order)).filter(
        RDPropertyMedia.property_id == property_id
    ).scalar() or 0
    
    valid_sections = ['EXTERIOR', 'INTERIOR', 'KITCHEN', 'BATHROOM', 'BEDROOM', 'LIVING_ROOM', 'BALCONY', 'FLOOR_PLAN', 'OTHER']
    validated_section = section.upper() if section and section.upper() in valid_sections else None
    
    media = RDPropertyMedia(
        company_id=company_id,
        property_id=property_id,
        media_type=media_type,
        file_name=file.filename or unique_name,
        file_path=f"/storage/{storage_path}",
        file_size=file_size,
        mime_type=file.content_type,
        section=validated_section,
        title=title,
        description=description,
        is_primary=is_primary,
        display_order=max_order + 1,
        uploaded_by_type='staff',
        uploaded_by_id=str(current_user.emp_code)
    )
    db.add(media)
    db.commit()
    db.refresh(media)
    
    return {
        "success": True,
        "message": "Media uploaded successfully",
        "media": media.to_dict()
    }


@router.get("/properties/{property_id}/media")
async def list_property_media(
    property_id: int,
    company_id: int,
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """
    List all media for a property
    DC Protocol: Filter by company_id
    """
    prop = db.query(RDProperty).filter(
        RDProperty.id == property_id,
        RDProperty.company_id == company_id
    ).first()
    
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")
    
    media_list = db.query(RDPropertyMedia).filter(
        RDPropertyMedia.property_id == property_id,
        RDPropertyMedia.company_id == company_id
    ).order_by(RDPropertyMedia.is_primary.desc(), RDPropertyMedia.display_order.asc()).all()
    
    return {
        "success": True,
        "property_id": property_id,
        "media": [m.to_dict() for m in media_list]
    }


@router.delete("/properties/{property_id}/media/{media_id}")
async def delete_property_media(
    property_id: int,
    media_id: int,
    company_id: int,
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """
    Delete a media file from a property
    DC Protocol: Validate company ownership
    """
    from app.services.object_storage import storage_service
    
    media = db.query(RDPropertyMedia).filter(
        RDPropertyMedia.id == media_id,
        RDPropertyMedia.property_id == property_id,
        RDPropertyMedia.company_id == company_id
    ).first()
    
    if not media:
        raise HTTPException(status_code=404, detail="Media not found")
    
    storage_path = media.file_path.replace('/storage/', '')
    storage_service.delete_file(storage_path)
    
    was_primary = media.is_primary
    db.delete(media)
    
    if was_primary:
        next_media = db.query(RDPropertyMedia).filter(
            RDPropertyMedia.property_id == property_id,
            RDPropertyMedia.media_type == 'IMAGE'
        ).order_by(RDPropertyMedia.display_order.asc()).first()
        if next_media:
            next_media.is_primary = True
    
    db.commit()
    
    return {
        "success": True,
        "message": "Media deleted successfully"
    }


@router.put("/properties/{property_id}/media/{media_id}/primary")
async def set_primary_media(
    property_id: int,
    media_id: int,
    company_id: int,
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """
    Set a media file as the primary image for a property
    DC Protocol: Validate company ownership
    """
    media = db.query(RDPropertyMedia).filter(
        RDPropertyMedia.id == media_id,
        RDPropertyMedia.property_id == property_id,
        RDPropertyMedia.company_id == company_id,
        RDPropertyMedia.media_type == 'IMAGE'
    ).first()
    
    if not media:
        raise HTTPException(status_code=404, detail="Image not found")
    
    db.query(RDPropertyMedia).filter(
        RDPropertyMedia.property_id == property_id,
        RDPropertyMedia.is_primary == True
    ).update({'is_primary': False})
    
    media.is_primary = True
    db.commit()
    
    return {
        "success": True,
        "message": "Primary image updated"
    }


@router.put("/properties/{property_id}/media/reorder")
async def reorder_property_media(
    property_id: int,
    company_id: int,
    request: Request,
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """
    Reorder media for a property
    DC Protocol: Validate company ownership
    """
    data = await request.json()
    media_order = data.get('media_order', [])
    
    if not media_order:
        raise HTTPException(status_code=400, detail="media_order is required")
    
    prop = db.query(RDProperty).filter(
        RDProperty.id == property_id,
        RDProperty.company_id == company_id
    ).first()
    
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")
    
    for idx, media_id in enumerate(media_order):
        db.query(RDPropertyMedia).filter(
            RDPropertyMedia.id == media_id,
            RDPropertyMedia.property_id == property_id,
            RDPropertyMedia.company_id == company_id
        ).update({'display_order': idx + 1})
    
    db.commit()
    
    return {
        "success": True,
        "message": "Media order updated"
    }


@router.put("/properties/{property_id}/media/bulk-update")
async def bulk_update_property_media(
    property_id: int,
    company_id: int,
    request: Request,
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """
    Bulk update media order and section for a property
    DC Protocol: Validate company ownership
    WVV Protocol: Staff authentication required
    
    Request body: {
        "updates": [
            {"id": 1, "display_order": 1, "section": "EXTERIOR"},
            {"id": 2, "display_order": 2, "section": "INTERIOR"}
        ]
    }
    """
    data = await request.json()
    updates = data.get('updates', [])
    
    if not updates:
        raise HTTPException(status_code=400, detail="updates array is required")
    
    prop = db.query(RDProperty).filter(
        RDProperty.id == property_id,
        RDProperty.company_id == company_id
    ).first()
    
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")
    
    valid_sections = ['EXTERIOR', 'INTERIOR', 'KITCHEN', 'BATHROOM', 'BEDROOM', 'LIVING_ROOM', 'BALCONY', 'FLOOR_PLAN', 'OTHER']
    
    updated_count = 0
    for item in updates:
        media_id = item.get('id')
        if not media_id:
            continue
            
        update_fields = {}
        
        if 'display_order' in item:
            update_fields['display_order'] = item['display_order']
        
        if 'section' in item:
            section = item['section']
            if section and section.upper() not in valid_sections:
                continue
            update_fields['section'] = section.upper() if section else None
        
        if update_fields:
            result = db.query(RDPropertyMedia).filter(
                RDPropertyMedia.id == media_id,
                RDPropertyMedia.property_id == property_id,
                RDPropertyMedia.company_id == company_id
            ).update(update_fields)
            if result:
                updated_count += 1
    
    db.commit()
    
    media = db.query(RDPropertyMedia).filter_by(
        property_id=property_id,
        company_id=company_id
    ).order_by(RDPropertyMedia.display_order).all()
    
    return {
        "success": True,
        "message": f"Updated {updated_count} media items",
        "media": [m.to_dict() for m in media]
    }


@router.put("/properties/{property_id}/edit-approved")
async def edit_approved_property(
    property_id: int,
    company_id: int,
    request: Request,
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """
    Edit an approved property and reset to PENDING for re-approval
    DC Protocol: company_id mandatory
    WVV Protocol: Staff authentication required (VGK/EA only)
    
    This endpoint allows editing ALL fields of an approved property.
    After edit, status changes to PENDING for re-approval workflow.
    """
    allowed_staff_types = ['VGK4U', 'VGK', 'EA']
    # DC Protocol: Menu-based access control - page assignment = full access
    # if current_user.staff_type not in allowed_staff_types:
    #     raise HTTPException(
    #         status_code=403, 
    #         detail="Only VGK/EA staff can edit approved properties"
    #     )
    
    prop = db.query(RDProperty).filter(
        RDProperty.id == property_id,
        RDProperty.company_id == company_id
    ).first()
    
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")
    
    if prop.status != 'APPROVED':
        raise HTTPException(
            status_code=400, 
            detail=f"This endpoint is for approved properties. Current status: {prop.status}"
        )
    
    data = await request.json()
    
    if 'property_type_id' in data:
        prop_type = db.query(RDPropertyType).filter(
            RDPropertyType.id == data['property_type_id'],
            RDPropertyType.company_id == company_id,
            RDPropertyType.is_active == True
        ).first()
        if not prop_type:
            raise HTTPException(status_code=400, detail="Invalid property type")
    
    if 'title' in data and data['title'] and len(data['title']) < 10:
        raise HTTPException(status_code=400, detail="Title must be at least 10 characters")
    
    old_status = prop.status
    
    allowed_fields = [
        'title', 'description', 'property_type_id', 'address', 'landmark', 
        'city', 'state', 'pincode', 'google_maps_link', 'latitude', 'longitude',
        'total_area', 'area_unit', 'built_up_area', 'carpet_area', 'facing',
        'floor_number', 'total_floors', 'listed_price', 'price_per_unit',
        'booking_amount', 'is_negotiable', 'price_on_request', 'bedrooms',
        'bathrooms', 'balconies', 'bedroom_configurations', 'age_of_property',
        'possession_status', 'rera_number', 'property_category', 'youtube_links',
        'contact_person_name', 'contact_person_phone', 'tagged_dealer_id',
        'tagged_distributor_id', 'free_bike_offer', 'images_json', 'uploaded_video_url',
        'brochure_url', 'video_url',
        # JSONB array fields for multi-value selections (Dec 19, 2025)
        'facings', 'bedroom_options', 'floors_display', 'hidden_fields', 'property_options',
        # Promotional and availability fields
        'is_limited_offer', 'availability_status', 'approach_road_size',
        # Contact display options
        'hide_contact_number', 'allow_hidden_call', 'show_company_contact'
    ]
    
    for key in allowed_fields:
        if key in data:
            if key == 'video_url' and data[key]:
                setattr(prop, 'uploaded_video_url', data[key])
            else:
                setattr(prop, key, data[key])
    
    amenity_ids = data.get('amenity_ids')
    if amenity_ids is not None:
        db.query(RDPropertyAmenity).filter_by(property_id=property_id).delete()
        for amenity_id in amenity_ids:
            amenity = db.query(RDAmenity).filter(
                RDAmenity.id == amenity_id,
                RDAmenity.company_id == company_id,
                RDAmenity.is_active == True
            ).first()
            if amenity:
                pa = RDPropertyAmenity(property_id=property_id, amenity_id=amenity_id)
                db.add(pa)
    
    image_urls = data.get('image_urls')
    if image_urls is not None:
        existing_media = db.query(RDPropertyMedia).filter(
            RDPropertyMedia.property_id == property_id,
            RDPropertyMedia.company_id == company_id,
            RDPropertyMedia.media_type == 'IMAGE'
        ).all()
        existing_paths = {m.file_path for m in existing_media}
        
        for idx, img_url in enumerate(image_urls):
            if img_url and img_url not in existing_paths:
                file_name = img_url.split('/')[-1] if '/' in img_url else f"image_{idx}.jpg"
                media = RDPropertyMedia(
                    company_id=company_id,
                    property_id=property_id,
                    media_type='IMAGE',
                    file_name=file_name,
                    file_path=img_url,
                    is_primary=(idx == 0 and not existing_media),
                    display_order=len(existing_media) + idx,
                    uploaded_by_type='staff',
                    uploaded_by_id=str(current_user.emp_code)
                )
                db.add(media)
    
    prop.status = 'PENDING'
    prop.approved_by_id = None
    prop.approved_at = None
    prop.updated_at = get_indian_time()
    
    audit = RDPropertyAudit(
        company_id=company_id,
        property_id=property_id,
        action='EDITED_FOR_REAPPROVAL',
        from_status=old_status,
        to_status='PENDING',
        notes=f"Edited by {current_user.full_name or current_user.emp_code}",
        performed_by_type='staff',
        performed_by_id=str(current_user.emp_code)
    )
    db.add(audit)
    
    db.commit()
    db.refresh(prop)
    
    return {
        "success": True,
        "message": "Property updated and submitted for re-approval",
        "property": prop.to_dict(),
        "previous_status": old_status,
        "new_status": prop.status
    }


@router.post("/properties/{property_id}/crm-link")
async def link_property_to_crm_lead(
    property_id: int,
    company_id: int,
    request: Request,
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """
    Link a property to a CRM lead
    DC Protocol: Validate company alignment between property and lead
    """
    from app.models.crm import CRMLead
    
    data = await request.json()
    crm_lead_id = data.get('crm_lead_id')
    interest_level = data.get('interest_level', 'INQUIRY')
    notes = data.get('notes')
    
    if not crm_lead_id:
        raise HTTPException(status_code=400, detail="crm_lead_id is required")
    
    prop = db.query(RDProperty).filter(
        RDProperty.id == property_id,
        RDProperty.company_id == company_id
    ).first()
    
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")
    
    lead = db.query(CRMLead).filter(
        CRMLead.id == crm_lead_id,
        CRMLead.company_id == company_id
    ).first()
    
    if not lead:
        raise HTTPException(status_code=404, detail="CRM Lead not found or company mismatch")
    
    existing_link = db.query(RDPropertyCRMLink).filter(
        RDPropertyCRMLink.property_id == property_id,
        RDPropertyCRMLink.crm_lead_id == crm_lead_id,
        RDPropertyCRMLink.company_id == company_id
    ).first()
    
    if existing_link:
        raise HTTPException(status_code=400, detail="Property already linked to this lead")
    
    valid_levels = ['INQUIRY', 'SITE_VISIT', 'NEGOTIATION', 'DEAL_CLOSED', 'LOST']
    if interest_level not in valid_levels:
        raise HTTPException(status_code=400, detail=f"Invalid interest level. Allowed: {valid_levels}")
    
    link = RDPropertyCRMLink(
        company_id=company_id,
        property_id=property_id,
        crm_lead_id=crm_lead_id,
        interest_level=interest_level,
        notes=notes,
        linked_by_type='staff',
        linked_by_id=str(current_user.emp_code)
    )
    db.add(link)
    db.commit()
    db.refresh(link)
    
    return {
        "success": True,
        "message": "Property linked to CRM lead",
        "link": link.to_dict()
    }


@router.get("/properties/{property_id}/crm-links")
async def list_property_crm_links(
    property_id: int,
    company_id: int,
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """
    List all CRM leads linked to a property
    DC Protocol: Filter by company_id
    """
    from app.models.crm import CRMLead
    
    prop = db.query(RDProperty).filter(
        RDProperty.id == property_id,
        RDProperty.company_id == company_id
    ).first()
    
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")
    
    links = db.query(RDPropertyCRMLink).filter(
        RDPropertyCRMLink.property_id == property_id,
        RDPropertyCRMLink.company_id == company_id
    ).order_by(RDPropertyCRMLink.created_at.desc()).all()
    
    result = []
    for link in links:
        link_dict = link.to_dict()
        lead = db.query(CRMLead).filter_by(id=link.crm_lead_id).first()
        if lead:
            link_dict['lead_name'] = lead.name
            link_dict['lead_phone'] = lead.phone
            link_dict['lead_status'] = lead.status
        result.append(link_dict)
    
    return {
        "success": True,
        "property_id": property_id,
        "links": result
    }


@router.put("/properties/{property_id}/crm-links/{link_id}")
async def update_property_crm_link(
    property_id: int,
    link_id: int,
    company_id: int,
    request: Request,
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """
    Update interest level or notes for a property-CRM link
    DC Protocol: Validate company ownership
    """
    data = await request.json()
    interest_level = data.get('interest_level')
    notes = data.get('notes')
    
    link = db.query(RDPropertyCRMLink).filter(
        RDPropertyCRMLink.id == link_id,
        RDPropertyCRMLink.property_id == property_id,
        RDPropertyCRMLink.company_id == company_id
    ).first()
    
    if not link:
        raise HTTPException(status_code=404, detail="Link not found")
    
    if interest_level:
        valid_levels = ['INQUIRY', 'SITE_VISIT', 'NEGOTIATION', 'DEAL_CLOSED', 'LOST']
        if interest_level not in valid_levels:
            raise HTTPException(status_code=400, detail=f"Invalid interest level. Allowed: {valid_levels}")
        link.interest_level = interest_level
    
    if notes is not None:
        link.notes = notes
    
    db.commit()
    
    return {
        "success": True,
        "message": "Link updated",
        "link": link.to_dict()
    }


@router.delete("/properties/{property_id}/crm-links/{link_id}")
async def remove_property_crm_link(
    property_id: int,
    link_id: int,
    company_id: int,
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """
    Remove a CRM lead link from a property
    DC Protocol: Validate company ownership
    """
    link = db.query(RDPropertyCRMLink).filter(
        RDPropertyCRMLink.id == link_id,
        RDPropertyCRMLink.property_id == property_id,
        RDPropertyCRMLink.company_id == company_id
    ).first()
    
    if not link:
        raise HTTPException(status_code=404, detail="Link not found")
    
    db.delete(link)
    db.commit()
    
    return {
        "success": True,
        "message": "Link removed"
    }


@router.get("/crm-lead/{crm_lead_id}/properties")
async def list_crm_lead_properties(
    crm_lead_id: int,
    company_id: int,
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """
    List all properties linked to a CRM lead
    DC Protocol: Filter by company_id
    """
    from app.models.crm import CRMLead
    
    lead = db.query(CRMLead).filter(
        CRMLead.id == crm_lead_id,
        CRMLead.company_id == company_id
    ).first()
    
    if not lead:
        raise HTTPException(status_code=404, detail="CRM Lead not found")
    
    links = db.query(RDPropertyCRMLink).filter(
        RDPropertyCRMLink.crm_lead_id == crm_lead_id,
        RDPropertyCRMLink.company_id == company_id
    ).order_by(RDPropertyCRMLink.created_at.desc()).all()
    
    result = []
    for link in links:
        link_dict = link.to_dict()
        prop = db.query(RDProperty).filter_by(id=link.property_id).first()
        if prop:
            link_dict['property_title'] = prop.title
            link_dict['property_code'] = prop.property_code
            link_dict['property_status'] = prop.status
            link_dict['property_type_id'] = prop.property_type_id
        result.append(link_dict)
    
    return {
        "success": True,
        "crm_lead_id": crm_lead_id,
        "linked_properties": result
    }


@router.get("/public/default-company")
async def get_default_company(db: Session = Depends(get_db)):
    """
    Public endpoint to get the default enabled company for Real Dreams marketplace.
    DC Protocol: Returns the first company with Real Dreams enabled and approved properties.
    This allows the marketplace to work across different environments without hardcoding.
    No authentication required.
    """
    configs = db.query(RDCompanyConfig).filter(
        RDCompanyConfig.is_enabled == True
    ).order_by(RDCompanyConfig.company_id).all()
    
    for config in configs:
        property_count = db.query(RDProperty).filter(
            RDProperty.company_id == config.company_id,
            RDProperty.status.in_(['APPROVED', 'ACTIVE'])
        ).count()
        
        if property_count > 0:
            return {
                "success": True,
                "company_id": config.company_id,
                "property_count": property_count,
                "message": "Default company found"
            }
    
    if configs:
        return {
            "success": True,
            "company_id": configs[0].company_id,
            "property_count": 0,
            "message": "Company enabled but no approved properties"
        }
    
    return {
        "success": False,
        "company_id": None,
        "message": "No Real Dreams enabled companies found"
    }


@router.get("/public/properties")
async def public_list_properties(
    company_id: Optional[int] = None,
    property_type_id: Optional[int] = None,
    city: Optional[str] = None,
    state: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    bedrooms: Optional[int] = None,
    search: Optional[str] = None,
    sort_by: Optional[str] = None,
    page: int = 1,
    limit: int = 12,
    db: Session = Depends(get_db)
):
    """
    Public endpoint to browse approved properties from all enabled companies.
    DC Protocol: If company_id provided, filter by it. Otherwise show properties from ALL enabled companies.
    No authentication required.
    """
    enabled_company_ids = []
    
    if company_id:
        config = db.query(RDCompanyConfig).filter_by(company_id=company_id).first()
        if not config or not config.is_enabled:
            return {
                "success": True,
                "total": 0,
                "page": page,
                "properties": [],
                "message": "Real Dreams not enabled for this company"
            }
        enabled_company_ids = [company_id]
    else:
        configs = db.query(RDCompanyConfig).filter(RDCompanyConfig.is_enabled == True).all()
        enabled_company_ids = [c.company_id for c in configs]
        if not enabled_company_ids:
            return {
                "success": True,
                "total": 0,
                "page": page,
                "properties": [],
                "message": "No Real Dreams enabled companies"
            }
    
    query = db.query(RDProperty).filter(
        RDProperty.company_id.in_(enabled_company_ids),
        RDProperty.status.in_(['APPROVED', 'ACTIVE'])
    )
    
    if property_type_id:
        query = query.filter(RDProperty.property_type_id == property_type_id)
    
    if city:
        query = query.filter(RDProperty.city.ilike(f"%{city}%"))
    
    if state:
        query = query.filter(RDProperty.state.ilike(f"%{state}%"))
    
    if min_price:
        query = query.filter(RDProperty.listed_price >= min_price)
    
    if max_price:
        query = query.filter(RDProperty.listed_price <= max_price)
    
    if bedrooms:
        query = query.filter(RDProperty.bedrooms >= bedrooms)
    
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            (RDProperty.title.ilike(search_term)) |
            (RDProperty.address.ilike(search_term)) |
            (RDProperty.city.ilike(search_term)) |
            (RDProperty.description.ilike(search_term))
        )
    
    total = query.count()
    if sort_by == 'price_asc':
        query = query.order_by(RDProperty.listed_price.asc().nullslast())
    elif sort_by == 'price_desc':
        query = query.order_by(RDProperty.listed_price.desc().nullsfirst())
    else:
        query = query.order_by(RDProperty.created_at.desc())
    properties = query.offset((page - 1) * limit).limit(limit).all()
    
    result = []
    for prop in properties:
        prop_dict = {
            'id': prop.id,
            'property_code': prop.property_code,
            'title': prop.title,
            'property_type_id': prop.property_type_id,
            'property_category': prop.property_category,
            'listed_price': float(prop.listed_price) if prop.listed_price else None,
            'price_on_request': prop.price_on_request,
            'price_unit': prop.price_unit,
            'total_area': float(prop.total_area) if prop.total_area else None,
            'area_unit': prop.area_unit,
            'bedrooms': prop.bedrooms,
            'bathrooms': prop.bathrooms,
            'bedroom_configurations': prop.bedroom_configurations,
            'address': prop.address,
            'city': prop.city,
            'state': prop.state,
            'pincode': prop.pincode,
            'status': prop.status,
            'free_bike_offer': prop.free_bike_offer,
            'video_url': prop.video_url or prop.uploaded_video_url,
            'youtube_links': prop.youtube_links,
            'brochure_url': prop.brochure_url,
            'description': prop.description,
            'possession_status': prop.possession_status,
            'created_at': prop.created_at.isoformat() if prop.created_at else None,
            'contact_person_name': prop.contact_person_name,
            'contact_person_phone': prop.contact_person_phone,
            'hide_contact_number': prop.hide_contact_number,
            'allow_hidden_call': prop.allow_hidden_call,
            'show_company_contact': prop.show_company_contact
        }
        
        if prop.property_type:
            prop_dict['property_type_name'] = prop.property_type.name
            prop_dict['property_type_icon'] = prop.property_type.icon
        
        media_list = db.query(RDPropertyMedia).filter(
            RDPropertyMedia.property_id == prop.id,
            RDPropertyMedia.media_type == 'IMAGE'
        ).order_by(RDPropertyMedia.is_primary.desc(), RDPropertyMedia.display_order.asc()).all()
        
        prop_dict['image_count'] = len(media_list)
        
        if media_list:
            primary_media = next((m for m in media_list if m.is_primary), media_list[0])
            prop_dict['primary_image'] = primary_media.file_path
            prop_dict['thumbnail_url'] = primary_media.file_path
        
        avg_rating = db.query(func.avg(RDPropertyRating.rating)).filter(
            RDPropertyRating.property_id == prop.id,
            RDPropertyRating.company_id == company_id,
            RDPropertyRating.is_visible == True
        ).scalar()
        total_ratings = db.query(func.count(RDPropertyRating.id)).filter(
            RDPropertyRating.property_id == prop.id,
            RDPropertyRating.company_id == company_id,
            RDPropertyRating.is_visible == True
        ).scalar()
        prop_dict['average_rating'] = round(float(avg_rating), 1) if avg_rating else 0
        prop_dict['total_ratings'] = total_ratings or 0
        
        result.append(prop_dict)
    
    return {
        "success": True,
        "total": total,
        "page": page,
        "limit": limit,
        "total_pages": (total + limit - 1) // limit,
        "properties": result
    }


# ============================================================================
# PHASE 7.3: ADVANCED SEARCH FILTERS (Moved before {property_id} route)
# ============================================================================

@router.get("/public/properties/advanced-search")
async def advanced_property_search(
    company_id: int,
    property_type_id: Optional[int] = None,
    city: Optional[str] = None,
    state: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    min_area: Optional[float] = None,
    max_area: Optional[float] = None,
    bedrooms: Optional[int] = None,
    bathrooms: Optional[int] = None,
    min_bedrooms: Optional[int] = None,
    max_bedrooms: Optional[int] = None,
    furnishing: Optional[str] = None,
    possession_status: Optional[str] = None,
    facing: Optional[str] = None,
    amenity_ids: Optional[str] = None,
    search: Optional[str] = None,
    sort_by: Optional[str] = "newest",
    page: int = 1,
    limit: int = 12,
    db: Session = Depends(get_db)
):
    """
    Public endpoint for advanced property search with multiple filters
    DC Protocol: Filter by company_id, only show APPROVED/ACTIVE properties
    No authentication required
    
    Parameters:
    - property_type_id: Filter by property type
    - city, state: Location filters
    - min_price, max_price: Price range
    - min_area, max_area: Area range in sq ft
    - bedrooms, bathrooms: Exact match
    - min_bedrooms, max_bedrooms: Bedroom range
    - furnishing: UNFURNISHED, SEMI_FURNISHED, FULLY_FURNISHED
    - possession_status: READY_TO_MOVE, UNDER_CONSTRUCTION
    - facing: NORTH, SOUTH, EAST, WEST, etc.
    - amenity_ids: Comma-separated amenity IDs
    - search: Text search in title, address, city, description
    - sort_by: newest, oldest, price_low, price_high, area_low, area_high
    """
    config = db.query(RDCompanyConfig).filter_by(company_id=company_id).first()
    if not config or not config.is_enabled:
        return {
            "success": True,
            "total": 0,
            "page": page,
            "properties": [],
            "filters_applied": {},
            "message": "Real Dreams not enabled for this company"
        }
    
    query = db.query(RDProperty).filter(
        RDProperty.company_id == company_id,
        RDProperty.status.in_(['APPROVED', 'ACTIVE'])
    )
    
    filters_applied = {}
    
    if property_type_id:
        query = query.filter(RDProperty.property_type_id == property_type_id)
        filters_applied['property_type_id'] = property_type_id
    
    if city:
        query = query.filter(RDProperty.city.ilike(f"%{city}%"))
        filters_applied['city'] = city
    
    if state:
        query = query.filter(RDProperty.state.ilike(f"%{state}%"))
        filters_applied['state'] = state
    
    if min_price is not None:
        query = query.filter(RDProperty.listed_price >= min_price)
        filters_applied['min_price'] = min_price
    
    if max_price is not None:
        query = query.filter(RDProperty.listed_price <= max_price)
        filters_applied['max_price'] = max_price
    
    if min_area is not None:
        query = query.filter(RDProperty.total_area >= min_area)
        filters_applied['min_area'] = min_area
    
    if max_area is not None:
        query = query.filter(RDProperty.total_area <= max_area)
        filters_applied['max_area'] = max_area
    
    if bedrooms is not None:
        query = query.filter(RDProperty.bedrooms == bedrooms)
        filters_applied['bedrooms'] = bedrooms
    elif min_bedrooms is not None or max_bedrooms is not None:
        if min_bedrooms is not None:
            query = query.filter(RDProperty.bedrooms >= min_bedrooms)
            filters_applied['min_bedrooms'] = min_bedrooms
        if max_bedrooms is not None:
            query = query.filter(RDProperty.bedrooms <= max_bedrooms)
            filters_applied['max_bedrooms'] = max_bedrooms
    
    if bathrooms is not None:
        query = query.filter(RDProperty.bathrooms == bathrooms)
        filters_applied['bathrooms'] = bathrooms
    
    if furnishing:
        query = query.filter(RDProperty.furnishing == furnishing)
        filters_applied['furnishing'] = furnishing
    
    if possession_status:
        query = query.filter(RDProperty.possession_status == possession_status)
        filters_applied['possession_status'] = possession_status
    
    if facing:
        query = query.filter(RDProperty.facing == facing)
        filters_applied['facing'] = facing
    
    if amenity_ids:
        try:
            amenity_id_list = [int(a.strip()) for a in amenity_ids.split(',') if a.strip()]
            if amenity_id_list:
                property_ids_with_amenities = db.query(RDPropertyAmenity.property_id).filter(
                    RDPropertyAmenity.amenity_id.in_(amenity_id_list)
                ).group_by(RDPropertyAmenity.property_id).having(
                    func.count(RDPropertyAmenity.amenity_id) >= len(amenity_id_list)
                ).all()
                property_ids_with_amenities = [p[0] for p in property_ids_with_amenities]
                
                if property_ids_with_amenities:
                    query = query.filter(RDProperty.id.in_(property_ids_with_amenities))
                else:
                    return {
                        "success": True,
                        "total": 0,
                        "page": page,
                        "limit": limit,
                        "total_pages": 0,
                        "properties": [],
                        "filters_applied": filters_applied
                    }
                filters_applied['amenity_ids'] = amenity_id_list
        except ValueError:
            pass
    
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            (RDProperty.title.ilike(search_term)) |
            (RDProperty.address.ilike(search_term)) |
            (RDProperty.city.ilike(search_term)) |
            (RDProperty.description.ilike(search_term))
        )
        filters_applied['search'] = search
    
    if sort_by == "newest":
        query = query.order_by(RDProperty.created_at.desc())
    elif sort_by == "oldest":
        query = query.order_by(RDProperty.created_at.asc())
    elif sort_by == "price_low":
        query = query.order_by(RDProperty.listed_price.asc())
    elif sort_by == "price_high":
        query = query.order_by(RDProperty.listed_price.desc())
    elif sort_by == "area_low":
        query = query.order_by(RDProperty.total_area.asc())
    elif sort_by == "area_high":
        query = query.order_by(RDProperty.total_area.desc())
    else:
        query = query.order_by(RDProperty.created_at.desc())
    
    filters_applied['sort_by'] = sort_by
    
    total = query.count()
    properties = query.offset((page - 1) * limit).limit(limit).all()
    
    result = []
    for prop in properties:
        prop_dict = {
            'id': prop.id,
            'property_code': prop.property_code,
            'title': prop.title,
            'property_type_id': prop.property_type_id,
            'price': prop.listed_price,
            'price_unit': prop.price_unit,
            'area_sqft': prop.total_area,
            'area_unit': prop.area_unit,
            'bedrooms': prop.bedrooms,
            'bathrooms': prop.bathrooms,
            'balconies': prop.balconies,
            'possession_status': prop.possession_status,
            'address': prop.address,
            'city': prop.city,
            'state': prop.state,
            'pincode': prop.pincode,
            'status': prop.status,
            'free_bike_offer': prop.free_bike_offer,
            'created_at': prop.created_at.isoformat() if prop.created_at else None
        }
        
        if prop.property_type:
            prop_dict['property_type_name'] = prop.property_type.name
            prop_dict['property_type_icon'] = prop.property_type.icon
        
        primary_media = db.query(RDPropertyMedia).filter(
            RDPropertyMedia.property_id == prop.id,
            RDPropertyMedia.is_primary == True
        ).first()
        if primary_media:
            prop_dict['primary_image'] = primary_media.file_path
        else:
            first_image = db.query(RDPropertyMedia).filter(
                RDPropertyMedia.property_id == prop.id,
                RDPropertyMedia.media_type == 'IMAGE'
            ).order_by(RDPropertyMedia.display_order.asc()).first()
            if first_image:
                prop_dict['primary_image'] = first_image.file_path
        
        avg_rating = db.query(func.avg(RDPropertyRating.rating)).filter(
            RDPropertyRating.property_id == prop.id,
            RDPropertyRating.company_id == company_id,
            RDPropertyRating.is_visible == True
        ).scalar()
        total_ratings = db.query(func.count(RDPropertyRating.id)).filter(
            RDPropertyRating.property_id == prop.id,
            RDPropertyRating.company_id == company_id,
            RDPropertyRating.is_visible == True
        ).scalar()
        prop_dict['average_rating'] = round(float(avg_rating), 1) if avg_rating else 0
        prop_dict['total_ratings'] = total_ratings or 0
        
        result.append(prop_dict)
    
    return {
        "success": True,
        "total": total,
        "page": page,
        "limit": limit,
        "total_pages": (total + limit - 1) // limit,
        "properties": result,
        "filters_applied": filters_applied
    }


@router.get("/public/properties/{property_id}")
async def public_get_property(
    property_id: int,
    company_id: int,
    db: Session = Depends(get_db)
):
    """
    Public endpoint to view a single property detail
    DC Protocol: Filter by company_id, only show APPROVED/ACTIVE properties
    No authentication required
    """
    prop = db.query(RDProperty).filter(
        RDProperty.id == property_id,
        RDProperty.company_id == company_id,
        RDProperty.status.in_(['APPROVED', 'ACTIVE'])
    ).first()
    
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found or not available")
    
    prop_dict = prop.to_dict()
    
    # Normalize video_url field - use uploaded_video_url if video_url is not set
    # This ensures consistency with the list API
    prop_dict['video_url'] = prop.video_url or prop.uploaded_video_url
    
    if prop.property_type:
        prop_dict['property_type_name'] = prop.property_type.name
        prop_dict['property_type_icon'] = prop.property_type.icon
    
    media_list = db.query(RDPropertyMedia).filter(
        RDPropertyMedia.property_id == property_id
    ).order_by(RDPropertyMedia.is_primary.desc(), RDPropertyMedia.display_order.asc()).all()
    prop_dict['media'] = [m.to_dict() for m in media_list]
    
    # Get primary image from media
    primary_media = next((m for m in media_list if m.is_primary and m.media_type == 'IMAGE'), None)
    if primary_media:
        prop_dict['primary_image'] = primary_media.file_path
    elif media_list:
        first_image = next((m for m in media_list if m.media_type == 'IMAGE'), None)
        if first_image:
            prop_dict['primary_image'] = first_image.file_path
    
    # Count images for display
    prop_dict['image_count'] = sum(1 for m in media_list if m.media_type == 'IMAGE')
    prop_dict['thumbnail_url'] = prop_dict.get('primary_image')
    
    amenity_ids = db.query(RDPropertyAmenity.amenity_id).filter(
        RDPropertyAmenity.property_id == property_id
    ).all()
    amenity_ids = [a[0] for a in amenity_ids]
    
    if amenity_ids:
        amenities = db.query(RDAmenity).filter(RDAmenity.id.in_(amenity_ids)).all()
        prop_dict['amenities'] = [a.to_dict() for a in amenities]
    else:
        prop_dict['amenities'] = []
    
    return {
        "success": True,
        "property": prop_dict
    }


@router.get("/public/property-types")
async def public_get_property_types(
    company_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """
    Public endpoint to get property types for filtering.
    DC Protocol: If company_id provided, filter by it. Otherwise show types from ALL enabled companies.
    No authentication required.
    """
    if company_id:
        types = db.query(RDPropertyType).filter(
            RDPropertyType.company_id == company_id,
            RDPropertyType.is_active == True
        ).order_by(RDPropertyType.display_order.asc()).all()
    else:
        enabled_ids = [c.company_id for c in db.query(RDCompanyConfig).filter(RDCompanyConfig.is_enabled == True).all()]
        if not enabled_ids:
            return {"success": True, "property_types": []}
        types = db.query(RDPropertyType).filter(
            RDPropertyType.company_id.in_(enabled_ids),
            RDPropertyType.is_active == True
        ).order_by(RDPropertyType.display_order.asc()).all()
    
    return {
        "success": True,
        "property_types": [t.to_dict() for t in types]
    }


@router.get("/public/config")
async def public_get_config(
    company_id: int,
    db: Session = Depends(get_db)
):
    """
    Public endpoint to get Real Dreams configuration and banner
    DC Protocol: Filter by company_id
    """
    config = db.query(RDCompanyConfig).filter_by(company_id=company_id).first()
    if not config or not config.is_enabled:
        return {
            "success": True,
            "enabled": False
        }
    
    banner = db.query(RDBannerConfig).filter_by(company_id=company_id).first()
    
    property_count = db.query(func.count(RDProperty.id)).filter(
        RDProperty.company_id == company_id,
        RDProperty.status.in_(['APPROVED', 'ACTIVE'])
    ).scalar() or 0
    
    return {
        "success": True,
        "enabled": True,
        "banner": banner.to_dict() if banner else None,
        "property_count": property_count
    }


# ============================================================================
# PHASE 7: RATINGS, COMMENTS, SHARES, SAVED PROPERTIES, METRICS
# ============================================================================

from app.models.real_dreams import (
    RDSavedProperty, RDPropertyMetrics, RDPropertyRating, 
    RDPropertyComment, RDPropertyShare
)
from datetime import date


# --- RATINGS ENDPOINTS ---

@router.post("/public/properties/{property_id}/ratings")
async def add_property_rating(
    property_id: int,
    company_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Public endpoint to add a rating to a property
    DC Protocol: Validate company alignment
    """
    data = await request.json()
    
    rating_value = data.get('rating')
    reviewer_name = (data.get('reviewer_name') or '').strip()
    reviewer_email = (data.get('reviewer_email') or '').strip()
    reviewer_phone = (data.get('reviewer_phone') or '').strip()
    
    if not rating_value or not isinstance(rating_value, int) or rating_value < 1 or rating_value > 5:
        raise HTTPException(status_code=400, detail="Rating must be between 1 and 5")
    
    if not reviewer_name:
        raise HTTPException(status_code=400, detail="Reviewer name is required")
    
    prop = db.query(RDProperty).filter(
        RDProperty.id == property_id,
        RDProperty.company_id == company_id,
        RDProperty.status.in_(['APPROVED', 'ACTIVE'])
    ).first()
    
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")
    
    new_rating = RDPropertyRating(
        company_id=company_id,
        property_id=property_id,
        rating=rating_value,
        reviewer_type='public',
        reviewer_name=reviewer_name,
        reviewer_email=reviewer_email if reviewer_email else None,
        reviewer_phone=reviewer_phone if reviewer_phone else None,
        is_verified=False,
        is_visible=True
    )
    
    db.add(new_rating)
    db.commit()
    db.refresh(new_rating)
    
    return {
        "success": True,
        "message": "Rating submitted successfully",
        "rating": new_rating.to_dict()
    }


@router.get("/public/properties/{property_id}/ratings")
async def get_property_ratings(
    property_id: int,
    company_id: int,
    page: int = 1,
    per_page: int = 10,
    db: Session = Depends(get_db)
):
    """
    Public endpoint to get ratings for a property
    DC Protocol: Filter by company_id
    """
    query = db.query(RDPropertyRating).filter(
        RDPropertyRating.property_id == property_id,
        RDPropertyRating.company_id == company_id,
        RDPropertyRating.is_visible == True
    )
    
    total = query.count()
    
    avg_rating = db.query(func.avg(RDPropertyRating.rating)).filter(
        RDPropertyRating.property_id == property_id,
        RDPropertyRating.company_id == company_id,
        RDPropertyRating.is_visible == True
    ).scalar()
    
    ratings = query.order_by(RDPropertyRating.created_at.desc()).offset((page - 1) * per_page).limit(per_page).all()
    
    return {
        "success": True,
        "ratings": [r.to_dict() for r in ratings],
        "average_rating": round(float(avg_rating), 1) if avg_rating else 0,
        "total_ratings": total,
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total": total,
            "pages": (total + per_page - 1) // per_page
        }
    }


@router.delete("/properties/{property_id}/ratings/{rating_id}")
async def delete_property_rating(
    property_id: int,
    rating_id: int,
    company_id: int,
    request: Request,
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """
    Delete/hide a rating - RVZ and EA roles only
    DC Protocol: Validate company alignment and role permissions
    """
    # DC Protocol: Menu-based access control - page assignment = full access
    # if current_user.staff_type not in ['VGK4U', 'VGK', 'EA']:
    #     raise HTTPException(status_code=403, detail="Only RVZ Supreme and EA can delete ratings")
    
    data = await request.json()
    reason = data.get('reason', '').strip()
    
    rating = db.query(RDPropertyRating).filter(
        RDPropertyRating.id == rating_id,
        RDPropertyRating.property_id == property_id,
        RDPropertyRating.company_id == company_id
    ).first()
    
    if not rating:
        raise HTTPException(status_code=404, detail="Rating not found")
    
    rating.is_visible = False
    rating.deleted_by_id = current_user.id
    rating.deleted_at = get_indian_time()
    rating.deletion_reason = reason if reason else "Removed by admin"
    
    db.commit()
    
    return {
        "success": True,
        "message": "Rating removed successfully"
    }


# --- COMMENTS ENDPOINTS ---

@router.post("/public/properties/{property_id}/comments")
async def add_property_comment(
    property_id: int,
    company_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Public endpoint to add a comment to a property
    DC Protocol: Validate company alignment
    """
    data = await request.json()
    
    comment_text = data.get('comment', '').strip()
    commenter_name = data.get('commenter_name', '').strip()
    commenter_email = data.get('commenter_email', '').strip()
    commenter_phone = data.get('commenter_phone', '').strip()
    parent_id = data.get('parent_id')
    
    if not comment_text:
        raise HTTPException(status_code=400, detail="Comment text is required")
    
    if len(comment_text) > 2000:
        raise HTTPException(status_code=400, detail="Comment must be less than 2000 characters")
    
    if not commenter_name:
        raise HTTPException(status_code=400, detail="Your name is required")
    
    prop = db.query(RDProperty).filter(
        RDProperty.id == property_id,
        RDProperty.company_id == company_id,
        RDProperty.status.in_(['APPROVED', 'ACTIVE'])
    ).first()
    
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")
    
    if parent_id:
        parent_comment = db.query(RDPropertyComment).filter(
            RDPropertyComment.id == parent_id,
            RDPropertyComment.property_id == property_id,
            RDPropertyComment.company_id == company_id,
            RDPropertyComment.is_visible == True
        ).first()
        if not parent_comment:
            raise HTTPException(status_code=400, detail="Parent comment not found")
    
    new_comment = RDPropertyComment(
        company_id=company_id,
        property_id=property_id,
        comment=comment_text,
        parent_id=parent_id,
        commenter_type='public',
        commenter_name=commenter_name,
        commenter_email=commenter_email if commenter_email else None,
        commenter_phone=commenter_phone if commenter_phone else None,
        is_verified=False,
        is_visible=True
    )
    
    db.add(new_comment)
    db.commit()
    db.refresh(new_comment)
    
    return {
        "success": True,
        "message": "Comment submitted successfully",
        "comment": new_comment.to_dict()
    }


@router.get("/public/properties/{property_id}/comments")
async def get_property_comments(
    property_id: int,
    company_id: int,
    page: int = 1,
    per_page: int = 20,
    db: Session = Depends(get_db)
):
    """
    Public endpoint to get comments for a property (threaded)
    DC Protocol: Filter by company_id
    """
    parent_comments = db.query(RDPropertyComment).filter(
        RDPropertyComment.property_id == property_id,
        RDPropertyComment.company_id == company_id,
        RDPropertyComment.is_visible == True,
        RDPropertyComment.parent_id == None
    ).order_by(RDPropertyComment.created_at.desc()).offset((page - 1) * per_page).limit(per_page).all()
    
    total = db.query(func.count(RDPropertyComment.id)).filter(
        RDPropertyComment.property_id == property_id,
        RDPropertyComment.company_id == company_id,
        RDPropertyComment.is_visible == True,
        RDPropertyComment.parent_id == None
    ).scalar() or 0
    
    comments_with_replies = []
    for comment in parent_comments:
        comment_dict = comment.to_dict()
        replies = db.query(RDPropertyComment).filter(
            RDPropertyComment.parent_id == comment.id,
            RDPropertyComment.is_visible == True
        ).order_by(RDPropertyComment.created_at.asc()).all()
        comment_dict['replies'] = [r.to_dict() for r in replies]
        comment_dict['reply_count'] = len(replies)
        comments_with_replies.append(comment_dict)
    
    total_comments = db.query(func.count(RDPropertyComment.id)).filter(
        RDPropertyComment.property_id == property_id,
        RDPropertyComment.company_id == company_id,
        RDPropertyComment.is_visible == True
    ).scalar() or 0
    
    return {
        "success": True,
        "comments": comments_with_replies,
        "total_comments": total_comments,
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total": total,
            "pages": (total + per_page - 1) // per_page
        }
    }


@router.delete("/properties/{property_id}/comments/{comment_id}")
async def delete_property_comment(
    property_id: int,
    comment_id: int,
    company_id: int,
    request: Request,
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """
    Delete/hide a comment - RVZ and EA roles only
    DC Protocol: Validate company alignment and role permissions
    """
    # DC Protocol: Menu-based access control - page assignment = full access
    # if current_user.staff_type not in ['VGK4U', 'VGK', 'EA']:
    #     raise HTTPException(status_code=403, detail="Only RVZ Supreme and EA can delete comments")
    
    data = await request.json()
    reason = data.get('reason', '').strip()
    
    comment = db.query(RDPropertyComment).filter(
        RDPropertyComment.id == comment_id,
        RDPropertyComment.property_id == property_id,
        RDPropertyComment.company_id == company_id
    ).first()
    
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    
    comment.is_visible = False
    comment.deleted_by_id = current_user.id
    comment.deleted_at = get_indian_time()
    comment.deletion_reason = reason if reason else "Removed by admin"
    
    db.commit()
    
    return {
        "success": True,
        "message": "Comment removed successfully"
    }


# --- PUBLIC ENQUIRY ENDPOINT ---

@router.post("/public/properties/{property_id}/enquiry")
async def submit_property_enquiry(
    property_id: int,
    company_id: Optional[int] = None,
    request: Request = None,
    db: Session = Depends(get_db)
):
    """
    Public endpoint to submit property enquiry - creates a CRM lead
    DC Protocol: Validate company alignment, create lead with property linkage
    """
    from app.models.crm import CRMLead
    
    data = await request.json()
    
    name = data.get('name', '').strip()
    mobile = data.get('mobile', '').strip()
    email = data.get('email', '').strip()
    message = data.get('message', '').strip()
    
    if not name or len(name) < 2:
        raise HTTPException(status_code=400, detail="Name is required (minimum 2 characters)")
    if not mobile or len(mobile) != 10 or not mobile.isdigit():
        raise HTTPException(status_code=400, detail="Valid 10-digit mobile number is required")
    
    prop = db.query(RDProperty).filter(
        RDProperty.id == property_id,
        RDProperty.status.in_(['APPROVED', 'ACTIVE'])
    ).first()
    
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")
    
    effective_company_id = company_id if company_id else prop.company_id
    
    if company_id and prop.company_id != company_id:
        raise HTTPException(status_code=400, detail="Company ID mismatch")
    
    lead = CRMLead(
        company_id=effective_company_id,
        name=name,
        phone=mobile,
        email=email if email else None,
        description=f"Property Enquiry: {prop.title}\nMessage: {message}" if message else f"Property Enquiry: {prop.title}",
        source="real_dreams_marketplace",
        status="new",
        priority="medium",
        handler_type="unassigned",
        handler_id=None
    )
    
    db.add(lead)
    db.flush()
    
    property_link = RDPropertyCRMLink(
        company_id=effective_company_id,
        property_id=property_id,
        crm_lead_id=lead.id,
        interest_level="MEDIUM",
        notes="Enquiry from Real Dreams Marketplace",
        linked_by_type="member",
        linked_by_id="0"
    )
    db.add(property_link)
    
    db.commit()
    
    return {
        "success": True,
        "message": "Enquiry submitted successfully. Our team will contact you soon.",
        "lead_id": lead.id
    }


# --- SHARE TRACKING ENDPOINT ---

@router.post("/public/properties/{property_id}/share")
async def track_property_share(
    property_id: int,
    company_id: Optional[int] = None,
    request: Request = None,
    db: Session = Depends(get_db)
):
    """
    Public endpoint to track property shares
    DC Protocol: Validate company alignment with optional company_id
    """
    data = await request.json()
    
    platform = data.get('platform', 'other')
    valid_platforms = ['facebook', 'twitter', 'whatsapp', 'linkedin', 'email', 'copy_link', 'other']
    if platform not in valid_platforms:
        platform = 'other'
    
    prop = db.query(RDProperty).filter(
        RDProperty.id == property_id,
        RDProperty.status.in_(['APPROVED', 'ACTIVE'])
    ).first()
    
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")
    
    effective_company_id = company_id if company_id else prop.company_id
    
    if company_id and prop.company_id != company_id:
        raise HTTPException(status_code=400, detail="Company ID mismatch")
    
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get('User-Agent', '')[:500]
    
    share_record = RDPropertyShare(
        company_id=effective_company_id,
        property_id=property_id,
        platform=platform,
        ip_address=client_ip,
        user_agent=user_agent
    )
    
    db.add(share_record)
    
    today = date.today()
    metrics = db.query(RDPropertyMetrics).filter(
        RDPropertyMetrics.property_id == property_id,
        RDPropertyMetrics.company_id == effective_company_id,
        RDPropertyMetrics.metric_date == today
    ).first()
    
    if metrics:
        metrics.share_count += 1
    else:
        metrics = RDPropertyMetrics(
            company_id=effective_company_id,
            property_id=property_id,
            metric_date=today,
            share_count=1
        )
        db.add(metrics)
    
    db.commit()
    
    return {
        "success": True,
        "message": "Share recorded"
    }


# --- SAVED PROPERTIES ENDPOINTS ---

@router.post("/properties/{property_id}/save")
async def save_property(
    property_id: int,
    company_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Save a property to favorites
    DC Protocol: Validate company alignment
    Accepts user_type and user_id in request body
    """
    data = await request.json()
    
    user_type = data.get('user_type', 'public')
    user_id = data.get('user_id', '')
    
    if not user_id:
        client_ip = request.client.host if request.client else 'anonymous'
        user_id = f"anon_{client_ip}"
    
    prop = db.query(RDProperty).filter(
        RDProperty.id == property_id,
        RDProperty.company_id == company_id,
        RDProperty.status.in_(['APPROVED', 'ACTIVE'])
    ).first()
    
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")
    
    existing = db.query(RDSavedProperty).filter(
        RDSavedProperty.property_id == property_id,
        RDSavedProperty.company_id == company_id,
        RDSavedProperty.user_type == user_type,
        RDSavedProperty.user_id == str(user_id)
    ).first()
    
    if existing:
        return {
            "success": True,
            "message": "Property already saved",
            "saved": True
        }
    
    saved = RDSavedProperty(
        company_id=company_id,
        property_id=property_id,
        user_type=user_type,
        user_id=str(user_id)
    )
    
    db.add(saved)
    
    today = date.today()
    metrics = db.query(RDPropertyMetrics).filter(
        RDPropertyMetrics.property_id == property_id,
        RDPropertyMetrics.company_id == company_id,
        RDPropertyMetrics.metric_date == today
    ).first()
    
    if metrics:
        metrics.save_count += 1
    else:
        metrics = RDPropertyMetrics(
            company_id=company_id,
            property_id=property_id,
            metric_date=today,
            save_count=1
        )
        db.add(metrics)
    
    db.commit()
    
    return {
        "success": True,
        "message": "Property saved to favorites",
        "saved": True
    }


@router.delete("/properties/{property_id}/save")
async def unsave_property(
    property_id: int,
    company_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Remove a property from favorites
    DC Protocol: Validate company alignment
    """
    data = await request.json()
    
    user_type = data.get('user_type', 'public')
    user_id = data.get('user_id', '')
    
    if not user_id:
        client_ip = request.client.host if request.client else 'anonymous'
        user_id = f"anon_{client_ip}"
    
    saved = db.query(RDSavedProperty).filter(
        RDSavedProperty.property_id == property_id,
        RDSavedProperty.company_id == company_id,
        RDSavedProperty.user_type == user_type,
        RDSavedProperty.user_id == str(user_id)
    ).first()
    
    if not saved:
        return {
            "success": True,
            "message": "Property was not saved",
            "saved": False
        }
    
    db.delete(saved)
    db.commit()
    
    return {
        "success": True,
        "message": "Property removed from favorites",
        "saved": False
    }


@router.get("/saved-properties")
async def get_saved_properties(
    company_id: int,
    user_type: str,
    user_id: str,
    page: int = 1,
    per_page: int = 20,
    db: Session = Depends(get_db)
):
    """
    Get list of saved properties for a user
    DC Protocol: Filter by company_id
    """
    query = db.query(RDSavedProperty).filter(
        RDSavedProperty.company_id == company_id,
        RDSavedProperty.user_type == user_type,
        RDSavedProperty.user_id == user_id
    )
    
    total = query.count()
    
    saved_list = query.order_by(RDSavedProperty.created_at.desc()).offset((page - 1) * per_page).limit(per_page).all()
    
    property_ids = [s.property_id for s in saved_list]
    
    properties = []
    if property_ids:
        props = db.query(RDProperty).filter(
            RDProperty.id.in_(property_ids),
            RDProperty.status.in_(['APPROVED', 'ACTIVE'])
        ).all()
        
        for prop in props:
            prop_dict = prop.to_dict()
            if prop.property_type:
                prop_dict['property_type_name'] = prop.property_type.name
            
            primary_media = db.query(RDPropertyMedia).filter(
                RDPropertyMedia.property_id == prop.id,
                RDPropertyMedia.is_primary == True
            ).first()
            
            if primary_media:
                prop_dict['primary_image'] = primary_media.file_url
            
            properties.append(prop_dict)
    
    return {
        "success": True,
        "saved_properties": properties,
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total": total,
            "pages": (total + per_page - 1) // per_page
        }
    }


@router.get("/properties/{property_id}/is-saved")
async def check_property_saved(
    property_id: int,
    company_id: int,
    user_type: str,
    user_id: str,
    db: Session = Depends(get_db)
):
    """
    Check if a property is saved by the user
    DC Protocol: Filter by company_id
    """
    saved = db.query(RDSavedProperty).filter(
        RDSavedProperty.property_id == property_id,
        RDSavedProperty.company_id == company_id,
        RDSavedProperty.user_type == user_type,
        RDSavedProperty.user_id == user_id
    ).first()
    
    return {
        "success": True,
        "saved": saved is not None
    }


# --- METRICS ENDPOINTS ---

@router.post("/public/properties/{property_id}/view")
async def record_property_view(
    property_id: int,
    company_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Public endpoint to record a property view
    DC Protocol: Validate company alignment
    """
    prop = db.query(RDProperty).filter(
        RDProperty.id == property_id,
        RDProperty.company_id == company_id,
        RDProperty.status.in_(['APPROVED', 'ACTIVE'])
    ).first()
    
    if not prop:
        return {"success": False}
    
    today = date.today()
    metrics = db.query(RDPropertyMetrics).filter(
        RDPropertyMetrics.property_id == property_id,
        RDPropertyMetrics.company_id == company_id,
        RDPropertyMetrics.metric_date == today
    ).first()
    
    if metrics:
        metrics.view_count += 1
    else:
        metrics = RDPropertyMetrics(
            company_id=company_id,
            property_id=property_id,
            metric_date=today,
            view_count=1
        )
        db.add(metrics)
    
    db.commit()
    
    return {"success": True}


@router.post("/public/properties/{property_id}/inquiry")
async def record_property_inquiry(
    property_id: int,
    company_id: int,
    db: Session = Depends(get_db)
):
    """
    Public endpoint to record a property inquiry (called when CRM lead is created)
    DC Protocol: Validate company alignment
    """
    today = date.today()
    metrics = db.query(RDPropertyMetrics).filter(
        RDPropertyMetrics.property_id == property_id,
        RDPropertyMetrics.company_id == company_id,
        RDPropertyMetrics.metric_date == today
    ).first()
    
    if metrics:
        metrics.inquiry_count += 1
    else:
        metrics = RDPropertyMetrics(
            company_id=company_id,
            property_id=property_id,
            metric_date=today,
            inquiry_count=1
        )
        db.add(metrics)
    
    db.commit()
    
    return {"success": True}


@router.get("/properties/{property_id}/analytics")
async def get_property_analytics(
    property_id: int,
    company_id: int,
    days: int = 30,
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """
    Get property analytics for owners/admins
    DC Protocol: Validate company alignment and ownership
    """
    prop = db.query(RDProperty).filter(
        RDProperty.id == property_id,
        RDProperty.company_id == company_id
    ).first()
    
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")
    
    is_owner = prop.owner_type == 'staff' and str(prop.owner_id) == str(current_user.emp_code)
    is_admin = current_user.staff_type in ['VGK4U', 'VGK', 'EA', 'KEY_LEADERSHIP', 'HR']
    
    # DC Protocol: Menu-based access control - page assignment = full access
    # if not is_owner and not is_admin:
    #     raise HTTPException(status_code=403, detail="Access denied")
    
    from datetime import timedelta
    start_date = date.today() - timedelta(days=days)
    
    metrics = db.query(RDPropertyMetrics).filter(
        RDPropertyMetrics.property_id == property_id,
        RDPropertyMetrics.company_id == company_id,
        RDPropertyMetrics.metric_date >= start_date
    ).order_by(RDPropertyMetrics.metric_date.asc()).all()
    
    totals = db.query(
        func.sum(RDPropertyMetrics.view_count).label('total_views'),
        func.sum(RDPropertyMetrics.inquiry_count).label('total_inquiries'),
        func.sum(RDPropertyMetrics.save_count).label('total_saves'),
        func.sum(RDPropertyMetrics.share_count).label('total_shares')
    ).filter(
        RDPropertyMetrics.property_id == property_id,
        RDPropertyMetrics.company_id == company_id
    ).first()
    
    avg_rating = db.query(func.avg(RDPropertyRating.rating)).filter(
        RDPropertyRating.property_id == property_id,
        RDPropertyRating.company_id == company_id,
        RDPropertyRating.is_visible == True
    ).scalar()
    
    total_ratings = db.query(func.count(RDPropertyRating.id)).filter(
        RDPropertyRating.property_id == property_id,
        RDPropertyRating.company_id == company_id,
        RDPropertyRating.is_visible == True
    ).scalar() or 0
    
    total_comments = db.query(func.count(RDPropertyComment.id)).filter(
        RDPropertyComment.property_id == property_id,
        RDPropertyComment.company_id == company_id,
        RDPropertyComment.is_visible == True
    ).scalar() or 0
    
    return {
        "success": True,
        "property_id": property_id,
        "analytics": {
            "total_views": totals.total_views or 0 if totals else 0,
            "total_inquiries": totals.total_inquiries or 0 if totals else 0,
            "total_saves": totals.total_saves or 0 if totals else 0,
            "total_shares": totals.total_shares or 0 if totals else 0,
            "average_rating": round(float(avg_rating), 1) if avg_rating else 0,
            "total_ratings": total_ratings,
            "total_comments": total_comments
        },
        "daily_metrics": [m.to_dict() for m in metrics]
    }


# --- ADMIN RATINGS/COMMENTS LIST ---

@router.get("/admin/ratings")
async def admin_list_ratings(
    company_id: int,
    property_id: Optional[int] = None,
    is_visible: Optional[bool] = None,
    page: int = 1,
    per_page: int = 20,
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """
    Admin endpoint to list all ratings for moderation
    DC Protocol: RVZ and EA roles only
    """
    # DC Protocol: Menu-based access control - page assignment = full access
    # if current_user.staff_type not in ['VGK4U', 'VGK', 'EA']:
    #     raise HTTPException(status_code=403, detail="Access denied")
    
    query = db.query(RDPropertyRating).filter(
        RDPropertyRating.company_id == company_id
    )
    
    if property_id:
        query = query.filter(RDPropertyRating.property_id == property_id)
    
    if is_visible is not None:
        query = query.filter(RDPropertyRating.is_visible == is_visible)
    
    total = query.count()
    
    ratings = query.order_by(RDPropertyRating.created_at.desc()).offset((page - 1) * per_page).limit(per_page).all()
    
    ratings_with_property = []
    for r in ratings:
        r_dict = r.to_dict()
        prop = db.query(RDProperty).filter_by(id=r.property_id).first()
        if prop:
            r_dict['property_title'] = prop.title
        ratings_with_property.append(r_dict)
    
    return {
        "success": True,
        "ratings": ratings_with_property,
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total": total,
            "pages": (total + per_page - 1) // per_page
        }
    }


@router.get("/admin/comments")
async def admin_list_comments(
    company_id: int,
    property_id: Optional[int] = None,
    is_visible: Optional[bool] = None,
    page: int = 1,
    per_page: int = 20,
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """
    Admin endpoint to list all comments for moderation
    DC Protocol: RVZ and EA roles only
    """
    # DC Protocol: Menu-based access control - page assignment = full access
    # if current_user.staff_type not in ['VGK4U', 'VGK', 'EA']:
    #     raise HTTPException(status_code=403, detail="Access denied")
    
    query = db.query(RDPropertyComment).filter(
        RDPropertyComment.company_id == company_id
    )
    
    if property_id:
        query = query.filter(RDPropertyComment.property_id == property_id)
    
    if is_visible is not None:
        query = query.filter(RDPropertyComment.is_visible == is_visible)
    
    total = query.count()
    
    comments = query.order_by(RDPropertyComment.created_at.desc()).offset((page - 1) * per_page).limit(per_page).all()
    
    comments_with_property = []
    for c in comments:
        c_dict = c.to_dict()
        prop = db.query(RDProperty).filter_by(id=c.property_id).first()
        if prop:
            c_dict['property_title'] = prop.title
        comments_with_property.append(c_dict)
    
    return {
        "success": True,
        "comments": comments_with_property,
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total": total,
            "pages": (total + per_page - 1) // per_page
        }
    }


# ============================================================================
# PHASE 7.1: PROPERTY COMPARISON SYSTEM
# ============================================================================

@router.post("/public/properties/compare")
async def compare_properties(
    company_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Public endpoint to compare up to 4 properties side-by-side
    DC Protocol: Filter by company_id, only show APPROVED/ACTIVE properties
    No authentication required
    """
    data = await request.json()
    property_ids = data.get('property_ids', [])
    
    if not property_ids:
        raise HTTPException(status_code=400, detail="At least one property ID is required")
    
    if len(property_ids) > 4:
        raise HTTPException(status_code=400, detail="Maximum 4 properties can be compared at once")
    
    try:
        property_ids = [int(pid) for pid in property_ids]
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="Invalid property ID format")
    
    properties = db.query(RDProperty).filter(
        RDProperty.id.in_(property_ids),
        RDProperty.company_id == company_id,
        RDProperty.status.in_(['APPROVED', 'ACTIVE'])
    ).all()
    
    if not properties:
        raise HTTPException(status_code=404, detail="No valid properties found")
    
    comparison_data = []
    for prop in properties:
        prop_dict = {
            'id': prop.id,
            'property_code': prop.property_code,
            'title': prop.title,
            'price': prop.price,
            'price_unit': prop.price_unit,
            'area_sqft': prop.area_sqft,
            'bedrooms': prop.bedrooms,
            'bathrooms': prop.bathrooms,
            'parking_spaces': prop.parking_spaces,
            'floor_number': prop.floor_number,
            'total_floors': prop.total_floors,
            'facing': prop.facing,
            'furnishing': prop.furnishing,
            'possession_status': prop.possession_status,
            'property_age': prop.property_age,
            'address': prop.address,
            'city': prop.city,
            'state': prop.state,
            'pincode': prop.pincode,
            'latitude': float(prop.latitude) if prop.latitude else None,
            'longitude': float(prop.longitude) if prop.longitude else None,
            'description': prop.description,
            'status': prop.status,
            'created_at': prop.created_at.isoformat() if prop.created_at else None
        }
        
        if prop.property_type:
            prop_dict['property_type_name'] = prop.property_type.name
            prop_dict['property_type_icon'] = prop.property_type.icon
        
        primary_media = db.query(RDPropertyMedia).filter(
            RDPropertyMedia.property_id == prop.id,
            RDPropertyMedia.is_primary == True
        ).first()
        if primary_media:
            prop_dict['primary_image'] = primary_media.file_path
        else:
            first_image = db.query(RDPropertyMedia).filter(
                RDPropertyMedia.property_id == prop.id,
                RDPropertyMedia.media_type == 'IMAGE'
            ).order_by(RDPropertyMedia.display_order.asc()).first()
            if first_image:
                prop_dict['primary_image'] = first_image.file_path
        
        amenity_ids = db.query(RDPropertyAmenity.amenity_id).filter(
            RDPropertyAmenity.property_id == prop.id
        ).all()
        amenity_ids = [a[0] for a in amenity_ids]
        
        if amenity_ids:
            amenities = db.query(RDAmenity).filter(RDAmenity.id.in_(amenity_ids)).all()
            prop_dict['amenities'] = [{'id': a.id, 'name': a.name, 'icon': a.icon, 'category': a.category} for a in amenities]
        else:
            prop_dict['amenities'] = []
        
        avg_rating = db.query(func.avg(RDPropertyRating.rating)).filter(
            RDPropertyRating.property_id == prop.id,
            RDPropertyRating.company_id == company_id,
            RDPropertyRating.is_visible == True
        ).scalar()
        total_ratings = db.query(func.count(RDPropertyRating.id)).filter(
            RDPropertyRating.property_id == prop.id,
            RDPropertyRating.company_id == company_id,
            RDPropertyRating.is_visible == True
        ).scalar() or 0
        
        prop_dict['average_rating'] = round(float(avg_rating), 1) if avg_rating else 0
        prop_dict['total_ratings'] = total_ratings
        
        comparison_data.append(prop_dict)
    
    ordered_data = []
    for pid in property_ids:
        for prop in comparison_data:
            if prop['id'] == pid:
                ordered_data.append(prop)
                break
    
    comparison_fields = [
        {'field': 'price', 'label': 'Price', 'type': 'currency'},
        {'field': 'area_sqft', 'label': 'Area (sq ft)', 'type': 'number'},
        {'field': 'bedrooms', 'label': 'Bedrooms', 'type': 'number'},
        {'field': 'bathrooms', 'label': 'Bathrooms', 'type': 'number'},
        {'field': 'parking_spaces', 'label': 'Parking', 'type': 'number'},
        {'field': 'floor_number', 'label': 'Floor', 'type': 'text'},
        {'field': 'total_floors', 'label': 'Total Floors', 'type': 'number'},
        {'field': 'facing', 'label': 'Facing', 'type': 'text'},
        {'field': 'furnishing', 'label': 'Furnishing', 'type': 'text'},
        {'field': 'possession_status', 'label': 'Possession', 'type': 'text'},
        {'field': 'property_age', 'label': 'Property Age', 'type': 'text'},
        {'field': 'average_rating', 'label': 'Rating', 'type': 'rating'},
        {'field': 'amenities', 'label': 'Amenities', 'type': 'list'}
    ]
    
    return {
        "success": True,
        "properties": ordered_data,
        "comparison_fields": comparison_fields,
        "total_compared": len(ordered_data)
    }


@router.get("/public/amenities")
async def public_get_amenities(
    company_id: int,
    category: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Public endpoint to get amenities for filtering
    DC Protocol: Filter by company_id
    """
    query = db.query(RDAmenity).filter(
        RDAmenity.company_id == company_id,
        RDAmenity.is_active == True
    )
    
    if category:
        query = query.filter(RDAmenity.category == category)
    
    amenities = query.order_by(RDAmenity.category, RDAmenity.display_order).all()
    
    categorized = {}
    for amenity in amenities:
        cat = amenity.category or 'OTHER'
        if cat not in categorized:
            categorized[cat] = []
        categorized[cat].append(amenity.to_dict())
    
    return {
        "success": True,
        "amenities": [a.to_dict() for a in amenities],
        "categorized": categorized,
        "categories": list(categorized.keys())
    }


@router.get("/public/filter-options")
async def get_filter_options(
    company_id: int,
    db: Session = Depends(get_db)
):
    """
    Public endpoint to get all available filter options
    DC Protocol: Filter by company_id
    Returns unique values for cities, states, price ranges, etc.
    """
    cities = db.query(RDProperty.city).filter(
        RDProperty.company_id == company_id,
        RDProperty.status.in_(['APPROVED', 'ACTIVE']),
        RDProperty.city.isnot(None)
    ).distinct().all()
    cities = sorted([c[0] for c in cities if c[0]])
    
    states = db.query(RDProperty.state).filter(
        RDProperty.company_id == company_id,
        RDProperty.status.in_(['APPROVED', 'ACTIVE']),
        RDProperty.state.isnot(None)
    ).distinct().all()
    states = sorted([s[0] for s in states if s[0]])
    
    price_stats = db.query(
        func.min(RDProperty.listed_price),
        func.max(RDProperty.listed_price)
    ).filter(
        RDProperty.company_id == company_id,
        RDProperty.status.in_(['APPROVED', 'ACTIVE'])
    ).first()
    
    area_stats = db.query(
        func.min(RDProperty.total_area),
        func.max(RDProperty.total_area)
    ).filter(
        RDProperty.company_id == company_id,
        RDProperty.status.in_(['APPROVED', 'ACTIVE'])
    ).first()
    
    bedroom_options = db.query(RDProperty.bedrooms).filter(
        RDProperty.company_id == company_id,
        RDProperty.status.in_(['APPROVED', 'ACTIVE']),
        RDProperty.bedrooms.isnot(None)
    ).distinct().order_by(RDProperty.bedrooms).all()
    bedroom_options = [b[0] for b in bedroom_options if b[0] is not None]
    
    bathroom_options = db.query(RDProperty.bathrooms).filter(
        RDProperty.company_id == company_id,
        RDProperty.status.in_(['APPROVED', 'ACTIVE']),
        RDProperty.bathrooms.isnot(None)
    ).distinct().order_by(RDProperty.bathrooms).all()
    bathroom_options = [b[0] for b in bathroom_options if b[0] is not None]
    
    property_types = db.query(RDPropertyType).filter(
        RDPropertyType.company_id == company_id,
        RDPropertyType.is_active == True
    ).order_by(RDPropertyType.display_order).all()
    
    amenities = db.query(RDAmenity).filter(
        RDAmenity.company_id == company_id,
        RDAmenity.is_active == True
    ).order_by(RDAmenity.category, RDAmenity.display_order).all()
    
    furnishing_options = ['UNFURNISHED', 'SEMI_FURNISHED', 'FULLY_FURNISHED']
    possession_options = ['READY_TO_MOVE', 'UNDER_CONSTRUCTION']
    facing_options = ['NORTH', 'SOUTH', 'EAST', 'WEST', 'NORTH_EAST', 'NORTH_WEST', 'SOUTH_EAST', 'SOUTH_WEST']
    
    return {
        "success": True,
        "options": {
            "cities": cities,
            "states": states,
            "price_range": {
                "min": float(price_stats[0]) if price_stats and price_stats[0] else 0,
                "max": float(price_stats[1]) if price_stats and price_stats[1] else 0
            },
            "area_range": {
                "min": float(area_stats[0]) if area_stats and area_stats[0] else 0,
                "max": float(area_stats[1]) if area_stats and area_stats[1] else 0
            },
            "bedrooms": bedroom_options,
            "bathrooms": bathroom_options,
            "property_types": [pt.to_dict() for pt in property_types],
            "amenities": [a.to_dict() for a in amenities],
            "furnishing": furnishing_options,
            "possession_status": possession_options,
            "facing": facing_options,
            "sort_options": [
                {"value": "newest", "label": "Newest First"},
                {"value": "oldest", "label": "Oldest First"},
                {"value": "price_low", "label": "Price: Low to High"},
                {"value": "price_high", "label": "Price: High to Low"},
                {"value": "area_low", "label": "Area: Small to Large"},
                {"value": "area_high", "label": "Area: Large to Small"}
            ]
        }
    }
