"""
Digital Catalog Models — MyntOS Single-Page Digital Catalog Platform
DC Protocol Compliant:
- Strict multi-company and multi-tenant scoping (company_id, tenant_id)
- Ordered, category-tailored sections with JSONB configuration
- Multilingual content variants (en, te, hi, ta) with language fallback
- Lead dispatch tracking and link analytics
"""

from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, Text, ForeignKey,
    Index, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from app.models.base import Base, BaseModel, get_indian_time


class DigitalCatalog(BaseModel):
    """
    Master record for a single-page digital catalog.
    Represents an entire vertical or offering (e.g., Commercial Solar, Industrial Hub Franchise).
    """
    __tablename__ = 'digital_catalogs'
    __table_args__ = (
        UniqueConstraint('company_id', 'slug', name='uq_digital_catalogs_company_slug'),
        Index('ix_digital_catalogs_company_status', 'company_id', 'status'),
        Index('ix_digital_catalogs_segment', 'segment_code'),
        Index('ix_digital_catalogs_category', 'category_id'),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    company_id = Column(Integer, ForeignKey('associated_companies.id'), nullable=False, index=True)
    tenant_id = Column(Integer, ForeignKey('platform_clients.id', ondelete='SET NULL'), nullable=True, index=True)
    category_id = Column(Integer, nullable=True, index=True)

    segment_code = Column(String(50), nullable=False)  # SOLAR, INDUSTRIAL_HUB, EV_B2B, EV_B2C, EV_SPARES, ETC_TRAINING, REAL_DREAMS, INSURANCE
    slug = Column(String(120), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    subtitle = Column(String(500), nullable=True)
    summary = Column(Text, nullable=True)

    hero_media_url = Column(String(500), nullable=True)  # S3 banner image/video URL
    catalog_type = Column(String(50), default='SINGLE_PAGE', nullable=False)  # SINGLE_PAGE, PROSPECTUS, BROCHURE
    status = Column(String(20), default='published', nullable=False)  # draft, in_review, published, archived

    is_active = Column(Boolean, default=True, nullable=False)
    is_featured = Column(Boolean, default=False, nullable=False)
    sort_order = Column(Integer, default=0, nullable=False)

    seo_title = Column(String(255), nullable=True)
    seo_description = Column(Text, nullable=True)
    seo_keywords = Column(Text, nullable=True)

    theme_config = Column(JSONB, default=dict, nullable=False)  # {"primary_color": "#2563eb", "accent_color": "#f59e0b", "dark_mode": false}
    default_language = Column(String(10), default='en', nullable=False)  # en
    active_languages = Column(JSONB, default=list, nullable=False)  # ["en", "te", "hi", "ta"]

    pdf_brochure_url = Column(String(500), nullable=True)  # S3 direct PDF URL for document dispatch
    whatsapp_template_name = Column(String(100), nullable=True)  # Meta approved template name
    version = Column(Integer, default=1, nullable=False)

    created_by_id = Column(Integer, ForeignKey('staff_employees.id', ondelete='SET NULL'), nullable=True)
    updated_by_id = Column(Integer, ForeignKey('staff_employees.id', ondelete='SET NULL'), nullable=True)

    published_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time, nullable=False)

    # Relationships
    sections = relationship("CatalogSection", back_populates="catalog", cascade="all, delete-orphan", order_by="CatalogSection.sort_order")
    items = relationship("CatalogItem", back_populates="catalog", cascade="all, delete-orphan", order_by="CatalogItem.sort_order")
    dispatches = relationship("CatalogLeadSend", back_populates="catalog", cascade="all, delete-orphan")

    def to_dict(self, include_sections=False, include_items=False, language='en'):
        d = {
            'id': self.id,
            'company_id': self.company_id,
            'tenant_id': self.tenant_id,
            'category_id': self.category_id,
            'segment_code': self.segment_code,
            'slug': self.slug,
            'title': self.title,
            'subtitle': self.subtitle,
            'summary': self.summary,
            'hero_media_url': self.hero_media_url,
            'catalog_type': self.catalog_type,
            'status': self.status,
            'is_active': self.is_active,
            'is_featured': self.is_featured,
            'sort_order': self.sort_order,
            'seo_title': self.seo_title,
            'seo_description': self.seo_description,
            'seo_keywords': self.seo_keywords,
            'theme_config': self.theme_config or {},
            'default_language': self.default_language or 'en',
            'active_languages': self.active_languages or ['en'],
            'pdf_brochure_url': self.pdf_brochure_url,
            'whatsapp_template_name': self.whatsapp_template_name,
            'version': self.version,
            'published_at': self.published_at.isoformat() if self.published_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'sections_count': len(self.sections) if self.sections else 0,
            'items_count': len(self.items) if self.items else 0,
        }
        if include_sections and self.sections:
            d['sections'] = [s.to_dict(language=language) for s in self.sections if s.is_visible]
        if include_items and self.items:
            d['items'] = [it.to_dict(language=language) for it in self.items if it.is_active]
        return d


class CatalogSection(BaseModel):
    """
    Ordered modular section within a single-page digital catalog.
    Governed by the controlled section type registry.
    """
    __tablename__ = 'catalog_sections'
    __table_args__ = (
        Index('ix_catalog_sections_catalog_order', 'catalog_id', 'sort_order'),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    catalog_id = Column(Integer, ForeignKey('digital_catalogs.id', ondelete='CASCADE'), nullable=False, index=True)

    section_type = Column(String(50), nullable=False)  # hero, introduction, highlights_grid, specifications_table, packages_pricing, comparison_table, process_workflow, media_gallery, roi_calculator, downloads, faqs, contact_cta
    section_key = Column(String(50), nullable=False)  # unique identifier within catalog (e.g., 'hero', 'specs', 'packages')
    title = Column(String(255), nullable=True)
    subtitle = Column(String(500), nullable=True)

    # Multilingual copy variants: {"en": {"title": "...", "desc": "..."}, "te": {"title": "...", "desc": "..."}}
    content_variants = Column(JSONB, default=dict, nullable=False)
    media_gallery = Column(JSONB, default=list, nullable=False)  # List of S3 URLs or video embeds
    configuration = Column(JSONB, default=dict, nullable=False)  # Specific configuration: cards, plans, steps, FAQs, specs

    sort_order = Column(Integer, default=0, nullable=False)
    is_visible = Column(Boolean, default=True, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time, nullable=False)

    catalog = relationship("DigitalCatalog", back_populates="sections")

    def to_dict(self, language='en'):
        variants = self.content_variants or {}
        lang_content = variants.get(language) or variants.get('en') or {}
        return {
            'id': self.id,
            'catalog_id': self.catalog_id,
            'section_type': self.section_type,
            'section_key': self.section_key,
            'title': lang_content.get('title') or self.title,
            'subtitle': lang_content.get('subtitle') or self.subtitle,
            'raw_title': self.title,
            'raw_subtitle': self.subtitle,
            'content_variants': self.content_variants or {},
            'localized_content': lang_content,
            'media_gallery': self.media_gallery or [],
            'configuration': self.configuration or {},
            'sort_order': self.sort_order,
            'is_visible': self.is_visible,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class CatalogItem(BaseModel):
    """
    Sub-items within a catalog when displaying product/service/package grids.
    Can optionally reference source entities (e.g., ev_model, rd_properties).
    """
    __tablename__ = 'catalog_items'
    __table_args__ = (
        Index('ix_catalog_items_catalog_order', 'catalog_id', 'sort_order'),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    catalog_id = Column(Integer, ForeignKey('digital_catalogs.id', ondelete='CASCADE'), nullable=False, index=True)

    item_type = Column(String(50), default='PRODUCT', nullable=False)  # PRODUCT, SERVICE, PACKAGE, COURSE, PROPERTY
    source_entity_type = Column(String(50), nullable=True)  # ev_model, rd_property, etc.
    source_entity_id = Column(Integer, nullable=True)

    item_code = Column(String(50), nullable=True)  # SKU, model code
    title = Column(String(255), nullable=False)
    subtitle = Column(String(500), nullable=True)

    specifications = Column(JSONB, default=list, nullable=False)  # [{"label": "Range", "value": "100 km"}, ...]
    pricing = Column(JSONB, default=dict, nullable=False)  # {"base_price": 75000, "price_text": "₹75,000", "subsidy": 15000}
    media_urls = Column(JSONB, default=list, nullable=False)  # S3 image URLs
    video_url = Column(String(500), nullable=True)

    content_variants = Column(JSONB, default=dict, nullable=False)  # Multilingual descriptions & highlights
    badges = Column(JSONB, default=list, nullable=False)  # ["Best Seller", "Govt Subsidy"]

    sort_order = Column(Integer, default=0, nullable=False)
    is_featured = Column(Boolean, default=False, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time, nullable=False)

    catalog = relationship("DigitalCatalog", back_populates="items")

    def to_dict(self, language='en'):
        variants = self.content_variants or {}
        lang_content = variants.get(language) or variants.get('en') or {}
        return {
            'id': self.id,
            'catalog_id': self.catalog_id,
            'item_type': self.item_type,
            'source_entity_type': self.source_entity_type,
            'source_entity_id': self.source_entity_id,
            'item_code': self.item_code,
            'title': lang_content.get('title') or self.title,
            'subtitle': lang_content.get('subtitle') or self.subtitle,
            'raw_title': self.title,
            'raw_subtitle': self.subtitle,
            'description': lang_content.get('description', ''),
            'specifications': self.specifications or [],
            'pricing': self.pricing or {},
            'media_urls': self.media_urls or [],
            'video_url': self.video_url,
            'badges': self.badges or [],
            'sort_order': self.sort_order,
            'is_featured': self.is_featured,
            'is_active': self.is_active,
            'content_variants': self.content_variants or {},
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class CatalogLeadSend(BaseModel):
    """
    Immutable ledger of catalog dispatches to CRM leads and recipients.
    Tracks delivery channel, method (web link vs PDF), views, and engagement.
    """
    __tablename__ = 'catalog_lead_sends'
    __table_args__ = (
        Index('ix_catalog_sends_catalog', 'catalog_id'),
        Index('ix_catalog_sends_lead', 'lead_id'),
        Index('ix_catalog_sends_phone', 'recipient_phone'),
        Index('ix_catalog_sends_ref_code', 'share_ref_code'),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    catalog_id = Column(Integer, ForeignKey('digital_catalogs.id', ondelete='CASCADE'), nullable=False)
    lead_id = Column(Integer, ForeignKey('crm_leads.id', ondelete='SET NULL'), nullable=True)
    company_id = Column(Integer, nullable=False, default=4)
    staff_id = Column(Integer, ForeignKey('staff_employees.id', ondelete='SET NULL'), nullable=True)

    recipient_phone = Column(String(20), nullable=False)
    recipient_name = Column(String(200), nullable=True)
    language_code = Column(String(10), default='en', nullable=False)

    delivery_channel = Column(String(30), default='whatsapp', nullable=False)  # whatsapp, sms, web
    delivery_method = Column(String(30), default='web_link', nullable=False)  # web_link, pdf_document, both
    share_ref_code = Column(String(64), unique=True, nullable=False, index=True)

    whatsapp_message_id = Column(String(255), nullable=True)
    status = Column(String(30), default='sent', nullable=False)  # pending, sent, delivered, read, failed
    failure_reason = Column(Text, nullable=True)

    view_count = Column(Integer, default=0, nullable=False)
    first_viewed_at = Column(DateTime, nullable=True)
    last_viewed_at = Column(DateTime, nullable=True)
    sent_at = Column(DateTime, default=get_indian_time, nullable=False)

    catalog = relationship("DigitalCatalog", back_populates="dispatches")

    def to_dict(self):
        return {
            'id': self.id,
            'catalog_id': self.catalog_id,
            'lead_id': self.lead_id,
            'company_id': self.company_id,
            'staff_id': self.staff_id,
            'recipient_phone': self.recipient_phone,
            'recipient_name': self.recipient_name,
            'language_code': self.language_code,
            'delivery_channel': self.delivery_channel,
            'delivery_method': self.delivery_method,
            'share_ref_code': self.share_ref_code,
            'whatsapp_message_id': self.whatsapp_message_id,
            'status': self.status,
            'failure_reason': self.failure_reason,
            'view_count': self.view_count,
            'first_viewed_at': self.first_viewed_at.isoformat() if self.first_viewed_at else None,
            'last_viewed_at': self.last_viewed_at.isoformat() if self.last_viewed_at else None,
            'sent_at': self.sent_at.isoformat() if self.sent_at else None
        }
