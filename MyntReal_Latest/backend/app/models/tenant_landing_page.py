"""
Tenant Single Page Landing Site & AI Prompt Model
DC Protocol (Oct 2026):
- Stores AI prompt text, generated HTML section layouts, media assets (logo, banner, gallery), video links, and contact details
- company_id & tenant_short_code indexed for fast public landing page lookups
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from datetime import datetime
import pytz

from app.models.base import BaseModel


def get_indian_time():
    """Get current datetime in Indian Standard Time (Asia/Kolkata)"""
    indian_tz = pytz.timezone('Asia/Kolkata')
    return datetime.now(indian_tz).replace(tzinfo=None)


class TenantLandingPage(BaseModel):
    """
    Tenant Single Page Content & AI Prompt Configuration
    Restricted to Staff/Admin management interface on tenant profile page
    Publicly served via myntreal.com/{tenant_short_code}
    """
    __tablename__ = 'tenant_landing_pages'
    __table_args__ = (
        UniqueConstraint('company_id', name='uq_tenant_landing_company_id'),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    company_id = Column(Integer, ForeignKey('associated_companies.id', ondelete='CASCADE'), nullable=False, index=True)
    tenant_short_code = Column(String(32), nullable=False, index=True)

    # AI Prompt & Content Configuration
    ai_prompt = Column(Text, nullable=True)
    hero_title = Column(String(250), nullable=True)
    hero_subtitle = Column(Text, nullable=True)
    generated_content = Column(JSONB, nullable=True, default=dict)

    # Media Assets (Image Change Controls & Video Links)
    logo_image_url = Column(String(500), nullable=True)
    banner_image_url = Column(String(500), nullable=True)
    gallery_images = Column(JSONB, nullable=True, default=list)  # List of image URLs
    video_links = Column(JSONB, nullable=True, default=list)     # List of video URLs (YouTube/Vimeo/MP4)

    # Contact & Official Business Information
    primary_phone = Column(String(20), nullable=True)
    secondary_phone = Column(String(20), nullable=True)
    official_website = Column(String(250), nullable=True)
    official_email = Column(String(250), nullable=True)
    address = Column(Text, nullable=True)
    google_maps_url = Column(Text, nullable=True)

    # Theme & Status
    theme_color = Column(String(20), default='#2563eb', nullable=False)
    is_published = Column(Boolean, default=True, nullable=False)

    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time, nullable=False)
    updated_by_id = Column(Integer, ForeignKey('staff_employees.id', ondelete='SET NULL'), nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'company_id': self.company_id,
            'tenant_short_code': self.tenant_short_code,
            'ai_prompt': self.ai_prompt or '',
            'hero_title': self.hero_title or '',
            'hero_subtitle': self.hero_subtitle or '',
            'generated_content': self.generated_content or {},
            'logo_image_url': self.logo_image_url or '',
            'banner_image_url': self.banner_image_url or '',
            'gallery_images': self.gallery_images or [],
            'video_links': self.video_links or [],
            'primary_phone': self.primary_phone or '',
            'secondary_phone': self.secondary_phone or '',
            'official_website': self.official_website or '',
            'official_email': self.official_email or '',
            'address': self.address or '',
            'google_maps_url': self.google_maps_url or '',
            'theme_color': self.theme_color,
            'is_published': self.is_published,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
