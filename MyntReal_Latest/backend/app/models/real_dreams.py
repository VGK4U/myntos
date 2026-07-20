"""
Real Dreams - Real Estate Marketplace Models
DC Protocol Compliant with Company-Wise Data Segregation

Tables Created:
- rd_company_config: Company category configuration for Real Dreams
- rd_property_types: RVZ configurable property types
- rd_amenities: Amenity master list by category
- rd_banner_config: Promotional banner settings
- rd_partner_profiles: Real Estate extension for Official Partners
- rd_properties: Property listings
- rd_property_amenities: Junction table
- rd_leads: CRM leads
- rd_lead_followups: Follow-up history
- rd_deals: Closed deals

Created: December 08, 2025
DC Protocol: All tables have company_id for strict segregation
"""

from sqlalchemy import (
    Column, Integer, String, DateTime, Date, Boolean, Text,
    ForeignKey, CheckConstraint, Index, Numeric, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from datetime import datetime
from decimal import Decimal
import pytz

from app.models.base import Base, BaseModel, get_indian_time


class RDCompanyConfig(BaseModel):
    """
    Real Dreams Company Configuration
    DC Protocol: Controls which companies can use Real Dreams module
    """
    __tablename__ = 'rd_company_config'
    
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey('associated_companies.id'), nullable=False, unique=True, index=True)
    
    is_enabled = Column(Boolean, default=False, nullable=False)
    
    allow_partner_listings = Column(Boolean, default=True, nullable=False)
    allow_employee_listings = Column(Boolean, default=True, nullable=False)
    allow_member_listings = Column(Boolean, default=True, nullable=False)
    
    default_commission_percent = Column(Numeric(5, 2), nullable=True, default=2.0)
    auto_approve_partner_properties = Column(Boolean, default=False, nullable=False)
    auto_approve_employee_properties = Column(Boolean, default=False, nullable=False)
    
    max_images_per_property = Column(Integer, default=10, nullable=False)
    max_properties_per_member = Column(Integer, default=5, nullable=False)
    
    enabled_by_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    enabled_at = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time, nullable=False)
    
    def __repr__(self):
        return f'<RDCompanyConfig Company:{self.company_id} Enabled:{self.is_enabled}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'company_id': self.company_id,
            'is_enabled': self.is_enabled,
            'allow_partner_listings': self.allow_partner_listings,
            'allow_employee_listings': self.allow_employee_listings,
            'allow_member_listings': self.allow_member_listings,
            'default_commission_percent': float(self.default_commission_percent) if self.default_commission_percent else None,
            'auto_approve_partner_properties': self.auto_approve_partner_properties,
            'auto_approve_employee_properties': self.auto_approve_employee_properties,
            'max_images_per_property': self.max_images_per_property,
            'max_properties_per_member': self.max_properties_per_member,
            'enabled_at': self.enabled_at.isoformat() if self.enabled_at else None
        }


class RDPropertyType(BaseModel):
    """
    Real Dreams Property Types
    DC Protocol: Company-wise configurable property types
    """
    __tablename__ = 'rd_property_types'
    
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey('associated_companies.id'), nullable=False, index=True)
    
    name = Column(String(100), nullable=False)
    slug = Column(String(50), nullable=False)
    description = Column(Text, nullable=True)
    icon = Column(String(50), nullable=True)
    
    is_active = Column(Boolean, default=True, nullable=False)
    display_order = Column(Integer, default=0, nullable=False)
    
    created_by_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    updated_by_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time, nullable=False)
    
    properties = relationship('RDProperty', back_populates='property_type')
    
    __table_args__ = (
        UniqueConstraint('company_id', 'slug', name='uq_rd_property_type_slug'),
        Index('idx_rd_property_type_company', 'company_id', 'is_active'),
    )
    
    def __repr__(self):
        return f'<RDPropertyType {self.name}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'company_id': self.company_id,
            'name': self.name,
            'slug': self.slug,
            'description': self.description,
            'icon': self.icon,
            'is_active': self.is_active,
            'display_order': self.display_order,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class RDAmenity(BaseModel):
    """
    Real Dreams Amenities Master
    DC Protocol: Company-wise amenity catalog
    """
    __tablename__ = 'rd_amenities'
    
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey('associated_companies.id'), nullable=False, index=True)
    
    category = Column(String(50), nullable=False)
    name = Column(String(100), nullable=False)
    icon = Column(String(50), nullable=True)
    
    is_active = Column(Boolean, default=True, nullable=False)
    display_order = Column(Integer, default=0, nullable=False)
    
    created_by_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time, nullable=False)
    
    __table_args__ = (
        UniqueConstraint('company_id', 'category', 'name', name='uq_rd_amenity_cat_name'),
        Index('idx_rd_amenity_company_cat', 'company_id', 'category'),
        CheckConstraint(
            "category IN ('SECURITY', 'LIFESTYLE', 'UTILITIES', 'PARKING', 'OUTDOOR', 'INDOOR', 'CONNECTIVITY', 'OTHER')",
            name='rd_amenity_category_check'
        ),
    )
    
    def __repr__(self):
        return f'<RDAmenity {self.category}: {self.name}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'company_id': self.company_id,
            'category': self.category,
            'name': self.name,
            'icon': self.icon,
            'is_active': self.is_active,
            'display_order': self.display_order,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class RDBannerConfig(BaseModel):
    """
    Real Dreams Promotional Banner
    DC Protocol: Company-wise configurable banner
    """
    __tablename__ = 'rd_banner_config'
    
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey('associated_companies.id'), nullable=False, unique=True, index=True)
    
    banner_text = Column(String(200), nullable=False, default='BOOK THIS PROPERTY & GET A FREE E-BIKE!')
    banner_subtext = Column(String(300), nullable=True)
    banner_image_url = Column(String(500), nullable=True)
    
    background_color = Column(String(20), default='#10B981', nullable=False)
    text_color = Column(String(20), default='#FFFFFF', nullable=False)
    
    offer_details = Column(Text, nullable=True)
    terms_conditions = Column(Text, nullable=True)
    
    is_active = Column(Boolean, default=True, nullable=False)
    
    created_by_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    updated_by_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time, nullable=False)
    
    def __repr__(self):
        return f'<RDBannerConfig Company:{self.company_id}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'company_id': self.company_id,
            'banner_text': self.banner_text,
            'banner_subtext': self.banner_subtext,
            'banner_image_url': self.banner_image_url,
            'background_color': self.background_color,
            'text_color': self.text_color,
            'offer_details': self.offer_details,
            'terms_conditions': self.terms_conditions,
            'is_active': self.is_active,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class RDPromotionalBanner(BaseModel):
    """
    Real Dreams Promotional Banners (Multiple per Company)
    DC Protocol: Company-wise configurable promotional banners (up to 5)
    Created: December 10, 2025
    """
    __tablename__ = 'rd_promotional_banners'
    
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey('associated_companies.id'), nullable=False, index=True)
    
    title = Column(String(200), nullable=False)
    subtitle = Column(String(300), nullable=True)
    image_url = Column(String(500), nullable=True)
    cta_text = Column(String(100), nullable=True, default='Learn More')
    cta_link = Column(String(500), nullable=True)
    
    background_color = Column(String(20), default='#10B981', nullable=False)
    text_color = Column(String(20), default='#FFFFFF', nullable=False)
    
    display_order = Column(Integer, default=0, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    
    valid_from = Column(DateTime, nullable=True)
    valid_until = Column(DateTime, nullable=True)
    
    created_by_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    updated_by_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time, nullable=False)
    
    __table_args__ = (
        Index('idx_rd_promo_banner_company', 'company_id', 'is_active', 'display_order'),
    )
    
    def __repr__(self):
        return f'<RDPromotionalBanner {self.id}: {self.title[:30]}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'company_id': self.company_id,
            'title': self.title,
            'subtitle': self.subtitle,
            'image_url': self.image_url,
            'cta_text': self.cta_text,
            'cta_link': self.cta_link,
            'background_color': self.background_color,
            'text_color': self.text_color,
            'display_order': self.display_order,
            'is_active': self.is_active,
            'valid_from': self.valid_from.isoformat() if self.valid_from else None,
            'valid_until': self.valid_until.isoformat() if self.valid_until else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class RDPartnerProfile(BaseModel):
    """
    Real Dreams Partner Profile
    DC Protocol: Extension of Official Partners for Real Estate
    """
    __tablename__ = 'rd_partner_profiles'
    
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey('associated_companies.id'), nullable=False, index=True)
    partner_id = Column(Integer, ForeignKey('official_partners.id'), nullable=False, index=True)
    
    partner_type = Column(String(30), nullable=False, default='REAL_ESTATE_DEALER')
    specialization = Column(JSONB, nullable=True)
    service_areas = Column(JSONB, nullable=True)
    
    rera_registration_number = Column(String(50), nullable=True)
    rera_certificate_url = Column(String(500), nullable=True)
    dealership_agreement_url = Column(String(500), nullable=True)
    rental_agreement_url = Column(String(500), nullable=True)
    other_documents_json = Column(JSONB, nullable=True)
    
    nda_signed = Column(Boolean, default=False, nullable=False)
    nda_signed_at = Column(DateTime, nullable=True)
    nda_document_url = Column(String(500), nullable=True)
    
    status = Column(String(30), default='PENDING', nullable=False)
    rvz_notes = Column(Text, nullable=True)
    reviewed_by_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    
    created_by_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time, nullable=False)
    
    properties = relationship('RDProperty', back_populates='partner_profile')
    
    __table_args__ = (
        UniqueConstraint('company_id', 'partner_id', name='uq_rd_partner_profile'),
        CheckConstraint(
            "partner_type IN ('REAL_ESTATE_DEALER', 'BUILDER', 'AGENT', 'DEVELOPER')",
            name='rd_partner_type_check'
        ),
        CheckConstraint(
            "status IN ('DRAFT', 'PENDING', 'APPROVED', 'REJECTED', 'SUSPENDED')",
            name='rd_partner_status_check'
        ),
        Index('idx_rd_partner_status', 'company_id', 'status'),
    )
    
    def __repr__(self):
        return f'<RDPartnerProfile Partner:{self.partner_id} Status:{self.status}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'company_id': self.company_id,
            'partner_id': self.partner_id,
            'partner_type': self.partner_type,
            'specialization': self.specialization,
            'service_areas': self.service_areas,
            'rera_registration_number': self.rera_registration_number,
            'nda_signed': self.nda_signed,
            'status': self.status,
            'rvz_notes': self.rvz_notes,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class RDProperty(BaseModel):
    """
    Real Dreams Property Listing
    DC Protocol: Company-wise property listings
    Listers: Official Partners, Employees, or MNR Members
    """
    __tablename__ = 'rd_properties'
    
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey('associated_companies.id'), nullable=False, index=True)
    property_code = Column(String(20), nullable=False)
    
    partner_profile_id = Column(Integer, ForeignKey('rd_partner_profiles.id'), nullable=True)
    employee_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    mnr_user_id = Column(String(12), ForeignKey('user.id'), nullable=True)
    
    property_type_id = Column(Integer, ForeignKey('rd_property_types.id'), nullable=False)
    
    title = Column(String(256), nullable=False)
    description = Column(Text, nullable=True)
    
    address = Column(Text, nullable=True)
    landmark = Column(String(200), nullable=True)
    city = Column(String(100), nullable=True)
    state = Column(String(100), nullable=True)
    pincode = Column(String(10), nullable=True)
    google_maps_link = Column(String(500), nullable=True)
    latitude = Column(Numeric(10, 8), nullable=True)
    longitude = Column(Numeric(11, 8), nullable=True)
    
    total_area = Column(Numeric(15, 2), nullable=True)
    area_unit = Column(String(20), default='SQ_FT', nullable=False)
    length = Column(Numeric(10, 2), nullable=True)
    width = Column(Numeric(10, 2), nullable=True)
    built_up_area = Column(Numeric(15, 2), nullable=True)
    carpet_area = Column(Numeric(15, 2), nullable=True)
    plot_dimensions = Column(String(100), nullable=True)
    facing = Column(String(20), nullable=True)
    facings = Column(JSONB, nullable=True, default=[])
    road_width = Column(String(50), nullable=True)
    approach_road_size = Column(String(100), nullable=True)
    floor_number = Column(Integer, nullable=True)
    total_floors = Column(Integer, nullable=True)
    floors_display = Column(String(50), nullable=True)
    
    listed_price = Column(Numeric(15, 2), nullable=True)
    price_per_unit = Column(Numeric(15, 2), nullable=True)
    price_unit = Column(String(20), nullable=True)
    discount_percent = Column(Numeric(5, 2), nullable=True)
    discounted_price = Column(Numeric(15, 2), nullable=True)
    booking_amount = Column(Numeric(15, 2), nullable=True)
    is_negotiable = Column(Boolean, default=False, nullable=False)
    price_on_request = Column(Boolean, default=False, nullable=False)
    
    images_json = Column(JSONB, nullable=True)
    video_url = Column(String(500), nullable=True)
    uploaded_video_url = Column(String(500), nullable=True)
    virtual_tour_url = Column(String(500), nullable=True)
    brochure_url = Column(String(500), nullable=True)
    youtube_links = Column(JSONB, nullable=True, default=[])
    catalogues_json = Column(JSONB, nullable=True, default=[])
    
    bedrooms = Column(Integer, nullable=True)
    bedroom_options = Column(JSONB, nullable=True, default=[])
    property_options = Column(JSONB, nullable=True, default=[])
    bathrooms = Column(Integer, nullable=True)
    balconies = Column(Integer, nullable=True)
    bedroom_configurations = Column(JSONB, nullable=True, default=[])
    age_of_property = Column(String(50), nullable=True)
    possession_status = Column(String(30), nullable=True)
    possession_date = Column(Date, nullable=True)
    rera_number = Column(String(50), nullable=True)
    property_category = Column(String(30), default='RESIDENTIAL', nullable=False)
    
    contact_person_name = Column(String(100), nullable=True)
    contact_person_phone = Column(String(15), nullable=True)
    hide_contact_number = Column(Boolean, default=False, nullable=False)
    allow_hidden_call = Column(Boolean, default=True, nullable=False)
    show_company_contact = Column(Boolean, default=False, nullable=False)
    hidden_fields = Column(JSONB, nullable=False, default={})
    
    incentive_percentage = Column(Numeric(5, 2), default=50.0, nullable=True)
    zynova_eligible = Column(Boolean, default=True, nullable=True)
    custom_promoter_rate = Column(Numeric(5, 2), nullable=True)
    custom_team_leader_rate = Column(Numeric(5, 2), nullable=True)
    custom_zonal_manager_rate = Column(Numeric(5, 2), nullable=True)
    custom_director_rate = Column(Numeric(5, 2), nullable=True)
    vgk_l1_pct = Column(Numeric(5, 2), nullable=True)
    vgk_l2_pct = Column(Numeric(5, 2), nullable=True)
    vgk_l3_pct = Column(Numeric(5, 2), nullable=True)
    vgk_l4_pct = Column(Numeric(5, 2), nullable=True)
    
    tagged_dealer_id = Column(Integer, ForeignKey('official_partners.id'), nullable=True)
    tagged_distributor_id = Column(Integer, ForeignKey('official_partners.id'), nullable=True)
    
    status = Column(String(30), default='DRAFT', nullable=False)
    availability_status = Column(String(20), default='AVAILABLE', nullable=False)
    is_featured = Column(Boolean, default=False, nullable=False)
    is_premium = Column(Boolean, default=False, nullable=False)
    is_limited_offer = Column(Boolean, default=False, nullable=False)
    free_bike_offer = Column(Boolean, default=False, nullable=False)
    view_count = Column(Integer, default=0, nullable=False)
    
    rvz_notes = Column(Text, nullable=True)
    approved_by_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    
    created_by_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time, nullable=False)
    
    property_type = relationship('RDPropertyType', back_populates='properties')
    partner_profile = relationship('RDPartnerProfile', back_populates='properties')
    amenities = relationship('RDPropertyAmenity', back_populates='property', cascade='all, delete-orphan')
    leads = relationship('RDLead', back_populates='property')
    
    __table_args__ = (
        UniqueConstraint('company_id', 'property_code', name='uq_rd_property_code'),
        CheckConstraint(
            "area_unit IN ('SQ_FT', 'SQ_M', 'ACRES', 'GUNTHA', 'HECTARES', 'CENT')",
            name='rd_property_area_unit_check'
        ),
        CheckConstraint(
            "facing IN ('EAST', 'WEST', 'NORTH', 'SOUTH', 'NORTH_EAST', 'NORTH_WEST', 'SOUTH_EAST', 'SOUTH_WEST')",
            name='rd_property_facing_check'
        ),
        CheckConstraint(
            "possession_status IN ('READY', 'UNDER_CONSTRUCTION', 'UPCOMING')",
            name='rd_property_possession_check'
        ),
        CheckConstraint(
            "status IN ('DRAFT', 'PENDING', 'APPROVED', 'REJECTED', 'SOLD', 'EXPIRED')",
            name='rd_property_status_check'
        ),
        CheckConstraint(
            "availability_status IN ('AVAILABLE', 'LIMITED', 'SOLD_OUT', 'ARCHIVED')",
            name='rd_property_availability_check'
        ),
        Index('idx_rd_property_company_status', 'company_id', 'status'),
        Index('idx_rd_property_type', 'property_type_id'),
        Index('idx_rd_property_city', 'city'),
        Index('idx_rd_property_state', 'state'),
        Index('idx_rd_property_pincode', 'pincode'),
        Index('idx_rd_property_free_bike', 'free_bike_offer'),
        Index('idx_rd_property_limited_offer', 'is_limited_offer'),
        Index('idx_rd_property_availability', 'availability_status'),
    )
    
    def __repr__(self):
        return f'<RDProperty {self.property_code}: {self.title}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'company_id': self.company_id,
            'property_code': self.property_code,
            'partner_profile_id': self.partner_profile_id,
            'employee_id': self.employee_id,
            'mnr_user_id': self.mnr_user_id,
            'property_type_id': self.property_type_id,
            'title': self.title,
            'description': self.description,
            'address': self.address,
            'landmark': self.landmark,
            'city': self.city,
            'state': self.state,
            'pincode': self.pincode,
            'google_maps_link': self.google_maps_link,
            'latitude': float(self.latitude) if self.latitude else None,
            'longitude': float(self.longitude) if self.longitude else None,
            'total_area': float(self.total_area) if self.total_area else None,
            'area_unit': self.area_unit,
            'length': float(self.length) if self.length else None,
            'width': float(self.width) if self.width else None,
            'built_up_area': float(self.built_up_area) if self.built_up_area else None,
            'carpet_area': float(self.carpet_area) if self.carpet_area else None,
            'plot_dimensions': self.plot_dimensions,
            'facing': self.facing,
            'facings': self.facings or [],
            'road_width': self.road_width,
            'approach_road_size': self.approach_road_size,
            'floor_number': self.floor_number,
            'total_floors': self.total_floors,
            'floors_display': self.floors_display,
            'listed_price': float(self.listed_price) if self.listed_price else None,
            'price_per_unit': float(self.price_per_unit) if self.price_per_unit else None,
            'price_unit': self.price_unit,
            'discount_percent': float(self.discount_percent) if self.discount_percent else None,
            'discounted_price': float(self.discounted_price) if self.discounted_price else None,
            'booking_amount': float(self.booking_amount) if self.booking_amount else None,
            'is_negotiable': self.is_negotiable,
            'price_on_request': self.price_on_request,
            'images_json': self.images_json,
            'video_url': self.video_url,
            'uploaded_video_url': self.uploaded_video_url,
            'virtual_tour_url': self.virtual_tour_url,
            'brochure_url': self.brochure_url,
            'youtube_links': self.youtube_links,
            'catalogues_json': self.catalogues_json,
            'bedrooms': self.bedrooms,
            'bedroom_options': self.bedroom_options or [],
            'property_options': self.property_options or [],
            'bathrooms': self.bathrooms,
            'balconies': self.balconies,
            'bedroom_configurations': self.bedroom_configurations,
            'age_of_property': self.age_of_property,
            'possession_status': self.possession_status,
            'possession_date': self.possession_date.isoformat() if self.possession_date else None,
            'rera_number': self.rera_number,
            'property_category': self.property_category,
            'contact_person_name': self.contact_person_name,
            'contact_person_phone': self.contact_person_phone,
            'hide_contact_number': self.hide_contact_number,
            'allow_hidden_call': self.allow_hidden_call,
            'show_company_contact': self.show_company_contact,
            'hidden_fields': self.hidden_fields or {},
            'incentive_percentage': float(self.incentive_percentage) if self.incentive_percentage is not None else 50.0,
            'zynova_eligible': self.zynova_eligible if self.zynova_eligible is not None else True,
            'custom_promoter_rate': float(self.custom_promoter_rate) if self.custom_promoter_rate is not None else None,
            'custom_team_leader_rate': float(self.custom_team_leader_rate) if self.custom_team_leader_rate is not None else None,
            'custom_zonal_manager_rate': float(self.custom_zonal_manager_rate) if self.custom_zonal_manager_rate is not None else None,
            'custom_director_rate': float(self.custom_director_rate) if self.custom_director_rate is not None else None,
            'vgk_l1_pct': float(self.vgk_l1_pct) if self.vgk_l1_pct is not None else None,
            'vgk_l2_pct': float(self.vgk_l2_pct) if self.vgk_l2_pct is not None else None,
            'vgk_l3_pct': float(self.vgk_l3_pct) if self.vgk_l3_pct is not None else None,
            'vgk_l4_pct': float(self.vgk_l4_pct) if self.vgk_l4_pct is not None else None,
            'tagged_dealer_id': self.tagged_dealer_id,
            'tagged_distributor_id': self.tagged_distributor_id,
            'status': self.status,
            'availability_status': self.availability_status,
            'is_featured': self.is_featured,
            'is_premium': self.is_premium,
            'is_limited_offer': self.is_limited_offer,
            'free_bike_offer': self.free_bike_offer,
            'view_count': self.view_count,
            'rvz_notes': self.rvz_notes,
            'approved_at': self.approved_at.isoformat() if self.approved_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class RDPropertyAmenity(BaseModel):
    """
    Real Dreams Property-Amenity Junction
    """
    __tablename__ = 'rd_property_amenities'
    
    id = Column(Integer, primary_key=True, index=True)
    property_id = Column(Integer, ForeignKey('rd_properties.id', ondelete='CASCADE'), nullable=False, index=True)
    amenity_id = Column(Integer, ForeignKey('rd_amenities.id'), nullable=False, index=True)
    
    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    
    property = relationship('RDProperty', back_populates='amenities')
    
    __table_args__ = (
        UniqueConstraint('property_id', 'amenity_id', name='uq_rd_property_amenity'),
    )
    
    def __repr__(self):
        return f'<RDPropertyAmenity Property:{self.property_id} Amenity:{self.amenity_id}>'


class RDLead(BaseModel):
    """
    Real Dreams CRM Lead
    DC Protocol: Company-wise lead tracking
    """
    __tablename__ = 'rd_leads'
    
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey('associated_companies.id'), nullable=False, index=True)
    lead_code = Column(String(20), nullable=False)
    
    property_id = Column(Integer, ForeignKey('rd_properties.id'), nullable=True, index=True)
    partner_profile_id = Column(Integer, ForeignKey('rd_partner_profiles.id'), nullable=True)
    assigned_to_employee_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=True, index=True)
    
    lead_type = Column(String(30), nullable=False, default='PROPERTY_INQUIRY')
    lead_source = Column(String(30), nullable=False, default='WEBSITE')
    lead_date = Column(Date, nullable=False)
    
    customer_name = Column(String(200), nullable=False)
    mobile_1 = Column(String(20), nullable=False)
    mobile_2 = Column(String(20), nullable=True)
    email = Column(String(200), nullable=True)
    address = Column(Text, nullable=True)
    city = Column(String(100), nullable=True)
    state = Column(String(100), nullable=True)
    
    mnr_user_id = Column(String(12), ForeignKey('user.id'), nullable=True)
    
    enquiry_for = Column(Text, nullable=True)
    budget_min = Column(Numeric(15, 2), nullable=True)
    budget_max = Column(Numeric(15, 2), nullable=True)
    preferred_location = Column(String(200), nullable=True)
    requirements_notes = Column(Text, nullable=True)
    
    status = Column(String(30), default='PENDING', nullable=False)
    last_contacted_at = Column(DateTime, nullable=True)
    last_pitch_notes = Column(Text, nullable=True)
    next_followup_date = Column(Date, nullable=True)
    next_followup_notes = Column(Text, nullable=True)
    
    visible_to_employees_json = Column(JSONB, nullable=True)
    visible_to_partner = Column(Boolean, default=False, nullable=False)
    
    deal_amount = Column(Numeric(15, 2), nullable=True)
    deal_notes = Column(Text, nullable=True)
    deal_closed_at = Column(DateTime, nullable=True)
    
    created_by_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time, nullable=False)
    
    property = relationship('RDProperty', back_populates='leads')
    followups = relationship('RDLeadFollowup', back_populates='lead', cascade='all, delete-orphan')
    
    __table_args__ = (
        UniqueConstraint('company_id', 'lead_code', name='uq_rd_lead_code'),
        CheckConstraint(
            "lead_type IN ('PROPERTY_INQUIRY', 'GENERAL', 'PARTNER_REFERRAL', 'WALK_IN')",
            name='rd_lead_type_check'
        ),
        CheckConstraint(
            "lead_source IN ('WEBSITE', 'WALK_IN', 'REFERRAL', 'SOCIAL_MEDIA', 'CALL', 'WHATSAPP', 'EMAIL', 'OTHER')",
            name='rd_lead_source_check'
        ),
        CheckConstraint(
            "status IN ('PENDING', 'IN_PROGRESS', 'CONTACTED', 'NEGOTIATION', 'SITE_VISIT', 'DEAL_CLOSED', 'DEAL_LOST', 'HOLD')",
            name='rd_lead_status_check'
        ),
        Index('idx_rd_lead_company_status', 'company_id', 'status'),
        Index('idx_rd_lead_date', 'lead_date'),
    )
    
    def __repr__(self):
        return f'<RDLead {self.lead_code}: {self.customer_name}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'company_id': self.company_id,
            'lead_code': self.lead_code,
            'property_id': self.property_id,
            'partner_profile_id': self.partner_profile_id,
            'assigned_to_employee_id': self.assigned_to_employee_id,
            'lead_type': self.lead_type,
            'lead_source': self.lead_source,
            'lead_date': self.lead_date.isoformat() if self.lead_date else None,
            'customer_name': self.customer_name,
            'mobile_1': self.mobile_1,
            'mobile_2': self.mobile_2,
            'email': self.email,
            'city': self.city,
            'state': self.state,
            'mnr_user_id': self.mnr_user_id,
            'enquiry_for': self.enquiry_for,
            'budget_min': float(self.budget_min) if self.budget_min else None,
            'budget_max': float(self.budget_max) if self.budget_max else None,
            'preferred_location': self.preferred_location,
            'status': self.status,
            'next_followup_date': self.next_followup_date.isoformat() if self.next_followup_date else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class RDLeadFollowup(BaseModel):
    """
    Real Dreams Lead Follow-up History
    """
    __tablename__ = 'rd_lead_followups'
    
    id = Column(Integer, primary_key=True, index=True)
    lead_id = Column(Integer, ForeignKey('rd_leads.id', ondelete='CASCADE'), nullable=False, index=True)
    
    followup_date = Column(Date, nullable=False)
    followup_type = Column(String(30), nullable=False)
    notes = Column(Text, nullable=True)
    outcome = Column(String(50), nullable=True)
    next_action = Column(Text, nullable=True)
    
    created_by_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    
    lead = relationship('RDLead', back_populates='followups')
    
    __table_args__ = (
        CheckConstraint(
            "followup_type IN ('CALL', 'WHATSAPP', 'EMAIL', 'SITE_VISIT', 'MEETING', 'VIDEO_CALL', 'OTHER')",
            name='rd_followup_type_check'
        ),
        Index('idx_rd_followup_date', 'followup_date'),
    )
    
    def __repr__(self):
        return f'<RDLeadFollowup Lead:{self.lead_id} Type:{self.followup_type}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'lead_id': self.lead_id,
            'followup_date': self.followup_date.isoformat() if self.followup_date else None,
            'followup_type': self.followup_type,
            'notes': self.notes,
            'outcome': self.outcome,
            'next_action': self.next_action,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class RDDeal(BaseModel):
    """
    Real Dreams Closed Deal
    DC Protocol: Company-wise deal tracking with commission
    """
    __tablename__ = 'rd_deals'
    
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey('associated_companies.id'), nullable=False, index=True)
    deal_code = Column(String(20), nullable=False)
    
    property_id = Column(Integer, ForeignKey('rd_properties.id'), nullable=False, index=True)
    lead_id = Column(Integer, ForeignKey('rd_leads.id'), nullable=True)
    partner_profile_id = Column(Integer, ForeignKey('rd_partner_profiles.id'), nullable=True)
    
    buyer_name = Column(String(200), nullable=False)
    buyer_phone = Column(String(20), nullable=False)
    buyer_email = Column(String(200), nullable=True)
    buyer_address = Column(Text, nullable=True)
    buyer_mnr_id = Column(String(12), ForeignKey('user.id'), nullable=True)
    
    deal_amount = Column(Numeric(15, 2), nullable=False)
    booking_amount_paid = Column(Numeric(15, 2), nullable=True)
    payment_mode = Column(String(30), nullable=True)
    deal_date = Column(Date, nullable=False)
    deal_notes = Column(Text, nullable=True)
    
    commission_amount = Column(Numeric(15, 2), nullable=True)
    commission_status = Column(String(30), default='PENDING', nullable=False)
    
    status = Column(String(30), default='PENDING_RVZ', nullable=False)
    rvz_notes = Column(Text, nullable=True)
    rvz_approved_by_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    rvz_approved_at = Column(DateTime, nullable=True)
    
    agreement_url = Column(String(500), nullable=True)
    receipt_url = Column(String(500), nullable=True)
    other_docs_json = Column(JSONB, nullable=True)
    
    created_by_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time, nullable=False)
    
    __table_args__ = (
        UniqueConstraint('company_id', 'deal_code', name='uq_rd_deal_code'),
        CheckConstraint(
            "status IN ('PENDING_RVZ', 'APPROVED', 'COMPLETED', 'CANCELLED')",
            name='rd_deal_status_check'
        ),
        CheckConstraint(
            "commission_status IN ('PENDING', 'CALCULATED', 'PAID', 'WAIVED')",
            name='rd_deal_commission_status_check'
        ),
        Index('idx_rd_deal_company_status', 'company_id', 'status'),
        Index('idx_rd_deal_date', 'deal_date'),
    )
    
    def __repr__(self):
        return f'<RDDeal {self.deal_code}: {self.deal_amount}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'company_id': self.company_id,
            'deal_code': self.deal_code,
            'property_id': self.property_id,
            'lead_id': self.lead_id,
            'partner_profile_id': self.partner_profile_id,
            'buyer_name': self.buyer_name,
            'buyer_phone': self.buyer_phone,
            'buyer_email': self.buyer_email,
            'buyer_mnr_id': self.buyer_mnr_id,
            'deal_amount': float(self.deal_amount) if self.deal_amount else None,
            'booking_amount_paid': float(self.booking_amount_paid) if self.booking_amount_paid else None,
            'payment_mode': self.payment_mode,
            'deal_date': self.deal_date.isoformat() if self.deal_date else None,
            'commission_amount': float(self.commission_amount) if self.commission_amount else None,
            'commission_status': self.commission_status,
            'status': self.status,
            'rvz_notes': self.rvz_notes,
            'rvz_approved_at': self.rvz_approved_at.isoformat() if self.rvz_approved_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class RDPropertyMedia(BaseModel):
    """
    Real Dreams Property Media
    DC Protocol: Company-wise structured media storage for properties
    """
    __tablename__ = 'rd_property_media'
    
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey('associated_companies.id'), nullable=False, index=True)
    property_id = Column(Integer, ForeignKey('rd_properties.id', ondelete='CASCADE'), nullable=False, index=True)
    
    media_type = Column(String(20), nullable=False, default='IMAGE')
    file_name = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer, nullable=True)
    mime_type = Column(String(100), nullable=True)
    
    section = Column(String(50), nullable=True)
    title = Column(String(200), nullable=True)
    description = Column(Text, nullable=True)
    
    is_primary = Column(Boolean, default=False, nullable=False)
    display_order = Column(Integer, default=0, nullable=False)
    
    uploaded_by_type = Column(String(20), nullable=False)
    uploaded_by_id = Column(String(50), nullable=False)
    
    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    
    __table_args__ = (
        CheckConstraint(
            "media_type IN ('IMAGE', 'VIDEO', 'DOCUMENT', 'BROCHURE', 'FLOOR_PLAN')",
            name='rd_media_type_check'
        ),
        CheckConstraint(
            "uploaded_by_type IN ('staff', 'partner', 'member')",
            name='rd_media_uploader_type_check'
        ),
        Index('idx_rd_media_property', 'property_id', 'display_order'),
        Index('idx_rd_media_section', 'property_id', 'section'),
    )
    
    def __repr__(self):
        return f'<RDPropertyMedia Property:{self.property_id} Type:{self.media_type}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'company_id': self.company_id,
            'property_id': self.property_id,
            'media_type': self.media_type,
            'file_name': self.file_name,
            'file_path': self.file_path,
            'file_size': self.file_size,
            'mime_type': self.mime_type,
            'section': self.section,
            'title': self.title,
            'description': self.description,
            'is_primary': self.is_primary,
            'display_order': self.display_order,
            'uploaded_by_type': self.uploaded_by_type,
            'uploaded_by_id': self.uploaded_by_id,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class RDPropertyCRMLink(BaseModel):
    """
    Real Dreams Property-CRM Lead Link
    DC Protocol: Links Universal CRM leads to properties for interest tracking
    """
    __tablename__ = 'rd_property_crm_links'
    
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey('associated_companies.id'), nullable=False, index=True)
    property_id = Column(Integer, ForeignKey('rd_properties.id', ondelete='CASCADE'), nullable=False, index=True)
    crm_lead_id = Column(Integer, ForeignKey('crm_leads.id', ondelete='CASCADE'), nullable=False, index=True)
    
    interest_level = Column(String(20), default='MEDIUM', nullable=False)
    notes = Column(Text, nullable=True)
    
    linked_by_type = Column(String(20), nullable=False)
    linked_by_id = Column(String(50), nullable=False)
    
    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    
    __table_args__ = (
        UniqueConstraint('property_id', 'crm_lead_id', name='uq_rd_property_crm_link'),
        CheckConstraint(
            "interest_level IN ('LOW', 'MEDIUM', 'HIGH', 'HOT')",
            name='rd_interest_level_check'
        ),
        CheckConstraint(
            "linked_by_type IN ('staff', 'partner', 'member')",
            name='rd_linker_type_check'
        ),
    )
    
    def __repr__(self):
        return f'<RDPropertyCRMLink Property:{self.property_id} Lead:{self.crm_lead_id}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'company_id': self.company_id,
            'property_id': self.property_id,
            'crm_lead_id': self.crm_lead_id,
            'interest_level': self.interest_level,
            'notes': self.notes,
            'linked_by_type': self.linked_by_type,
            'linked_by_id': self.linked_by_id,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class RDPropertyAudit(BaseModel):
    """
    Real Dreams Property Status Audit Trail
    DC Protocol: Tracks all status changes for properties
    """
    __tablename__ = 'rd_property_audit'
    
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey('associated_companies.id'), nullable=False, index=True)
    property_id = Column(Integer, ForeignKey('rd_properties.id', ondelete='CASCADE'), nullable=False, index=True)
    
    action = Column(String(50), nullable=False)
    from_status = Column(String(30), nullable=True)
    to_status = Column(String(30), nullable=True)
    notes = Column(Text, nullable=True)
    
    performed_by_type = Column(String(20), nullable=False)
    performed_by_id = Column(String(50), nullable=False)
    
    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    
    __table_args__ = (
        Index('idx_rd_property_audit', 'property_id', 'created_at'),
    )
    
    def __repr__(self):
        return f'<RDPropertyAudit Property:{self.property_id} Action:{self.action}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'company_id': self.company_id,
            'property_id': self.property_id,
            'action': self.action,
            'from_status': self.from_status,
            'to_status': self.to_status,
            'notes': self.notes,
            'performed_by_type': self.performed_by_type,
            'performed_by_id': self.performed_by_id,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class RDSavedProperty(BaseModel):
    """
    Real Dreams Saved/Favorite Properties
    DC Protocol: User-scoped saved properties with company segregation
    Phase 7 Enhancement: Allows users to bookmark properties for later viewing
    """
    __tablename__ = 'rd_saved_properties'
    
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey('associated_companies.id'), nullable=False, index=True)
    property_id = Column(Integer, ForeignKey('rd_properties.id', ondelete='CASCADE'), nullable=False, index=True)
    
    user_type = Column(String(20), nullable=False)
    user_id = Column(String(50), nullable=False)
    
    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    
    __table_args__ = (
        UniqueConstraint('company_id', 'property_id', 'user_type', 'user_id', name='uq_rd_saved_property'),
        CheckConstraint(
            "user_type IN ('staff', 'partner', 'member', 'public')",
            name='rd_saved_user_type_check'
        ),
        Index('idx_rd_saved_property_user', 'company_id', 'user_type', 'user_id'),
    )
    
    def __repr__(self):
        return f'<RDSavedProperty Property:{self.property_id} User:{self.user_type}:{self.user_id}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'company_id': self.company_id,
            'property_id': self.property_id,
            'user_type': self.user_type,
            'user_id': self.user_id,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class RDPropertyMetrics(BaseModel):
    """
    Real Dreams Property Analytics/Metrics
    DC Protocol: Tracks property views and inquiries with company segregation
    Phase 7 Enhancement: Analytics for property owners and admins
    """
    __tablename__ = 'rd_property_metrics'
    
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey('associated_companies.id'), nullable=False, index=True)
    property_id = Column(Integer, ForeignKey('rd_properties.id', ondelete='CASCADE'), nullable=False, index=True)
    
    metric_date = Column(Date, nullable=False, index=True)
    view_count = Column(Integer, default=0, nullable=False)
    inquiry_count = Column(Integer, default=0, nullable=False)
    save_count = Column(Integer, default=0, nullable=False)
    share_count = Column(Integer, default=0, nullable=False)
    
    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time, nullable=False)
    
    __table_args__ = (
        UniqueConstraint('company_id', 'property_id', 'metric_date', name='uq_rd_property_metrics_date'),
        Index('idx_rd_property_metrics', 'company_id', 'property_id', 'metric_date'),
    )
    
    def __repr__(self):
        return f'<RDPropertyMetrics Property:{self.property_id} Date:{self.metric_date}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'company_id': self.company_id,
            'property_id': self.property_id,
            'metric_date': self.metric_date.isoformat() if self.metric_date else None,
            'view_count': self.view_count,
            'inquiry_count': self.inquiry_count,
            'save_count': self.save_count,
            'share_count': self.share_count,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class RDPropertyRating(BaseModel):
    """
    Real Dreams Property Ratings
    DC Protocol: Public ratings with company segregation
    Phase 7 Enhancement: Visitors can rate properties (1-5 stars)
    RVZ and EA roles can delete inappropriate ratings
    """
    __tablename__ = 'rd_property_ratings'
    
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey('associated_companies.id'), nullable=False, index=True)
    property_id = Column(Integer, ForeignKey('rd_properties.id', ondelete='CASCADE'), nullable=False, index=True)
    
    rating = Column(Integer, nullable=False)
    
    reviewer_type = Column(String(20), nullable=False)
    reviewer_id = Column(String(100), nullable=True)
    reviewer_name = Column(String(100), nullable=False)
    reviewer_email = Column(String(255), nullable=True)
    reviewer_phone = Column(String(20), nullable=True)
    
    is_verified = Column(Boolean, default=False, nullable=False)
    is_visible = Column(Boolean, default=True, nullable=False)
    
    deleted_by_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    deleted_at = Column(DateTime, nullable=True)
    deletion_reason = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    
    __table_args__ = (
        CheckConstraint('rating >= 1 AND rating <= 5', name='rd_rating_range_check'),
        CheckConstraint(
            "reviewer_type IN ('staff', 'partner', 'member', 'public')",
            name='rd_rating_reviewer_type_check'
        ),
        Index('idx_rd_property_rating', 'company_id', 'property_id', 'is_visible'),
    )
    
    def __repr__(self):
        return f'<RDPropertyRating Property:{self.property_id} Rating:{self.rating}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'company_id': self.company_id,
            'property_id': self.property_id,
            'rating': self.rating,
            'reviewer_type': self.reviewer_type,
            'reviewer_name': self.reviewer_name,
            'is_verified': self.is_verified,
            'is_visible': self.is_visible,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class RDPropertyComment(BaseModel):
    """
    Real Dreams Property Comments
    DC Protocol: Public comments with company segregation
    Phase 7 Enhancement: Visitors can comment on properties
    RVZ and EA roles can delete inappropriate comments
    """
    __tablename__ = 'rd_property_comments'
    
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey('associated_companies.id'), nullable=False, index=True)
    property_id = Column(Integer, ForeignKey('rd_properties.id', ondelete='CASCADE'), nullable=False, index=True)
    
    comment = Column(Text, nullable=False)
    
    parent_id = Column(Integer, ForeignKey('rd_property_comments.id', ondelete='CASCADE'), nullable=True, index=True)
    
    commenter_type = Column(String(20), nullable=False)
    commenter_id = Column(String(100), nullable=True)
    commenter_name = Column(String(100), nullable=False)
    commenter_email = Column(String(255), nullable=True)
    commenter_phone = Column(String(20), nullable=True)
    
    is_verified = Column(Boolean, default=False, nullable=False)
    is_visible = Column(Boolean, default=True, nullable=False)
    
    deleted_by_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    deleted_at = Column(DateTime, nullable=True)
    deletion_reason = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time, nullable=False)
    
    __table_args__ = (
        CheckConstraint(
            "commenter_type IN ('staff', 'partner', 'member', 'public')",
            name='rd_comment_commenter_type_check'
        ),
        Index('idx_rd_property_comment', 'company_id', 'property_id', 'is_visible'),
        Index('idx_rd_property_comment_parent', 'parent_id'),
    )
    
    def __repr__(self):
        return f'<RDPropertyComment Property:{self.property_id} ID:{self.id}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'company_id': self.company_id,
            'property_id': self.property_id,
            'comment': self.comment,
            'parent_id': self.parent_id,
            'commenter_type': self.commenter_type,
            'commenter_name': self.commenter_name,
            'is_verified': self.is_verified,
            'is_visible': self.is_visible,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class RDPropertyShare(BaseModel):
    """
    Real Dreams Property Share Tracking
    DC Protocol: Tracks property shares with company segregation
    Phase 7 Enhancement: Analytics for property sharing
    """
    __tablename__ = 'rd_property_shares'
    
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey('associated_companies.id'), nullable=False, index=True)
    property_id = Column(Integer, ForeignKey('rd_properties.id', ondelete='CASCADE'), nullable=False, index=True)
    
    platform = Column(String(30), nullable=False)
    
    sharer_type = Column(String(20), nullable=True)
    sharer_id = Column(String(100), nullable=True)
    
    ip_address = Column(String(50), nullable=True)
    user_agent = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    
    __table_args__ = (
        CheckConstraint(
            "platform IN ('facebook', 'twitter', 'whatsapp', 'linkedin', 'email', 'copy_link', 'other')",
            name='rd_share_platform_check'
        ),
        Index('idx_rd_property_share', 'company_id', 'property_id', 'platform'),
    )
    
    def __repr__(self):
        return f'<RDPropertyShare Property:{self.property_id} Platform:{self.platform}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'company_id': self.company_id,
            'property_id': self.property_id,
            'platform': self.platform,
            'sharer_type': self.sharer_type,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
