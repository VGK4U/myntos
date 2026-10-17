"""
Social Media Manager Database Models — MintOS / ZynovaOS
Supports:
- Multi-Tenant Social Account Connections (Zernio / Provider Profile Isolation)
- Company Calendar Configuration & Generation Settings
- Shared Content Items (SocialPost) with bi-daily 30-day cadence
- Platform-Specific Dispatches (SocialPostDispatch) with independent status, idempotency & live URLs
- Normalized Engagement Analytics Snapshots (SocialAnalyticsSnapshot) with explicit data availability
- Idempotent Webhook Events (SocialWebhookEvent)
"""

from sqlalchemy import (
    Column, Integer, String, Text, Boolean, DateTime, Float,
    ForeignKey, Index, UniqueConstraint, text
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import JSON
from sqlalchemy.orm import relationship
from datetime import datetime

from app.models.base import Base, BaseModel, get_indian_time

# Universal JSON type compatible with PostgreSQL JSONB and SQLite JSON
JSON_TYPE = JSONB().with_variant(JSON(), "sqlite")


# ─────────────────────────────────────────────────────────────────────────────
# 1. social_account_connections — External Accounts linked per Company
# ─────────────────────────────────────────────────────────────────────────────
class SocialAccountConnection(BaseModel):
    __tablename__ = 'social_account_connections'
    __table_args__ = (
        UniqueConstraint('company_id', 'platform', 'platform_account_id', name='uq_company_social_account'),
        Index('ix_soc_conn_comp_platform', 'company_id', 'platform'),
        Index('ix_soc_conn_tenant_status', 'tenant_id', 'status'),
    )

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey('platform_clients.id', ondelete='CASCADE'), nullable=False, index=True)
    company_id = Column(Integer, ForeignKey('associated_companies.id', ondelete='CASCADE'), nullable=False, index=True)

    platform = Column(String(32), nullable=False, index=True) # facebook, instagram, linkedin, twitter, youtube, threads, google_business
    platform_account_id = Column(String(128), nullable=False) # External Page ID / Account ID
    account_name = Column(String(200), nullable=False) # e.g. "Suryanz Solar Official Page"
    account_username = Column(String(100), nullable=True) # e.g. "@suryanzsolar"
    profile_image_url = Column(Text, nullable=True)

    provider_profile_id = Column(String(128), nullable=False, index=True) # Provider Profile Key (Zernio/Ayrshare)
    provider_account_id = Column(String(128), nullable=True, index=True) # Provider-specific account ID

    status = Column(String(32), default='ACTIVE', nullable=False, index=True) # ACTIVE, REQUIRES_REAUTH, REVOKED, DISCONNECTED
    capabilities = Column(JSON_TYPE, nullable=False, default=list) # ['publish_post', 'publish_video', 'insights']

    access_token_encrypted = Column(Text, nullable=True) # AES-256-GCM encrypted token if stored locally
    last_synced_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time, nullable=False)

    dispatches = relationship("SocialPostDispatch", back_populates="connection", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "company_id": self.company_id,
            "platform": self.platform,
            "platform_account_id": self.platform_account_id,
            "account_name": self.account_name,
            "account_username": self.account_username,
            "profile_image_url": self.profile_image_url,
            "provider_profile_id": self.provider_profile_id,
            "status": self.status,
            "capabilities": self.capabilities or [],
            "last_synced_at": self.last_synced_at.isoformat() if self.last_synced_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


# ─────────────────────────────────────────────────────────────────────────────
# 2. social_calendar_settings — Company-level posting defaults
# ─────────────────────────────────────────────────────────────────────────────
class SocialCalendarSetting(BaseModel):
    __tablename__ = 'social_calendar_settings'
    __table_args__ = (
        Index('ix_soc_cal_comp', 'company_id'),
    )

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey('platform_clients.id', ondelete='CASCADE'), nullable=False, index=True)
    company_id = Column(Integer, ForeignKey('associated_companies.id', ondelete='CASCADE'), unique=True, nullable=False, index=True)

    posting_frequency_days = Column(Integer, default=2, nullable=False) # 1 post every 2 days (~15 per month)
    preferred_time_ist = Column(String(10), default="10:30", nullable=False)
    timezone = Column(String(50), default="Asia/Kolkata", nullable=False)

    brand_voice = Column(String(100), default="Professional & Engaging", nullable=False)
    target_audience = Column(Text, nullable=True)
    content_themes = Column(JSON_TYPE, default=lambda: ["Educational Insights", "Product Spotlight", "Customer Benefits", "Industry Facts", "Community Engagement"], nullable=False)
    default_hashtags = Column(JSON_TYPE, default=list, nullable=False)

    helpline_phone = Column(String(30), nullable=True)
    website_url = Column(String(255), nullable=True)
    enabled_platforms = Column(JSON_TYPE, default=lambda: ["facebook", "instagram", "linkedin"], nullable=False)
    require_admin_approval = Column(Boolean, default=True, nullable=False)
    provider_profile_id = Column(String(128), nullable=True, index=True)

    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "company_id": self.company_id,
            "posting_frequency_days": self.posting_frequency_days,
            "preferred_time_ist": self.preferred_time_ist,
            "timezone": self.timezone,
            "brand_voice": self.brand_voice,
            "target_audience": self.target_audience,
            "content_themes": self.content_themes or [],
            "default_hashtags": self.default_hashtags or [],
            "helpline_phone": self.helpline_phone,
            "website_url": self.website_url,
            "enabled_platforms": self.enabled_platforms or [],
            "require_admin_approval": self.require_admin_approval,
            "provider_profile_id": self.provider_profile_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


# ─────────────────────────────────────────────────────────────────────────────
# 3. social_posts — Core Planned Content Items
# ─────────────────────────────────────────────────────────────────────────────
class SocialPost(BaseModel):
    __tablename__ = 'social_posts'
    __table_args__ = (
        Index('ix_social_posts_sched_status', 'status', 'scheduled_at'),
        Index('ix_social_posts_comp_sched', 'company_id', 'scheduled_at'),
    )

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey('platform_clients.id', ondelete='CASCADE'), nullable=False, index=True)
    company_id = Column(Integer, ForeignKey('associated_companies.id', ondelete='CASCADE'), nullable=False, index=True)

    campaign_name = Column(String(150), nullable=True)
    topic_theme = Column(String(100), nullable=False) # e.g. "Rooftop Solar Subsidy Guide"
    master_caption = Column(Text, nullable=False)
    master_hashtags = Column(JSON_TYPE, default=list, nullable=False)
    call_to_action_url = Column(Text, nullable=True)
    call_to_action_text = Column(String(100), nullable=True)

    media_urls = Column(JSON_TYPE, default=list, nullable=False)
    media_type = Column(String(20), default="IMAGE", nullable=False) # IMAGE, CAROUSEL, VIDEO, TEXT
    suggested_media_brief = Column(Text, nullable=True)

    scheduled_at = Column(DateTime, nullable=False, index=True)
    status = Column(String(32), default="DRAFT", nullable=False, index=True) 
    # DRAFT, PENDING_APPROVAL, APPROVED, SCHEDULED, PUBLISHING, PUBLISHED, PARTIALLY_FAILED, FAILED, CANCELLED

    created_by_staff_id = Column(Integer, ForeignKey('staff_employees.id', ondelete='SET NULL'), nullable=True)
    approved_by_staff_id = Column(Integer, ForeignKey('staff_employees.id', ondelete='SET NULL'), nullable=True)
    approved_at = Column(DateTime, nullable=True)

    retry_count = Column(Integer, default=0, nullable=False)
    next_retry_at = Column(DateTime, nullable=True)
    last_error = Column(Text, nullable=True)

    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time, nullable=False)

    dispatches = relationship("SocialPostDispatch", back_populates="post", cascade="all, delete-orphan")

    def to_dict(self, include_dispatches: bool = True):
        res = {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "company_id": self.company_id,
            "campaign_name": self.campaign_name,
            "topic_theme": self.topic_theme,
            "master_caption": self.master_caption,
            "master_hashtags": self.master_hashtags or [],
            "call_to_action_url": self.call_to_action_url,
            "call_to_action_text": self.call_to_action_text,
            "media_urls": self.media_urls or [],
            "media_type": self.media_type,
            "suggested_media_brief": self.suggested_media_brief,
            "scheduled_at": self.scheduled_at.isoformat() if self.scheduled_at else None,
            "status": self.status,
            "created_by_staff_id": self.created_by_staff_id,
            "approved_by_staff_id": self.approved_by_staff_id,
            "approved_at": self.approved_at.isoformat() if self.approved_at else None,
            "retry_count": self.retry_count,
            "last_error": self.last_error,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        res["platform_captions"] = {d.platform: d.tailored_caption for d in (self.dispatches or [])}
        if include_dispatches:
            res["dispatches"] = [d.to_dict() for d in (self.dispatches or [])]
        return res


# ─────────────────────────────────────────────────────────────────────────────
# 4. social_post_dispatches — Per-Platform Publication Records
# ─────────────────────────────────────────────────────────────────────────────
class SocialPostDispatch(BaseModel):
    __tablename__ = 'social_post_dispatches'
    __table_args__ = (
        Index('ix_soc_disp_post_plat', 'post_id', 'platform'),
        Index('ix_soc_disp_status', 'status'),
    )

    id = Column(Integer, primary_key=True, index=True)
    post_id = Column(Integer, ForeignKey('social_posts.id', ondelete='CASCADE'), nullable=False, index=True)
    connection_id = Column(Integer, ForeignKey('social_account_connections.id', ondelete='CASCADE'), nullable=False, index=True)

    platform = Column(String(32), nullable=False, index=True) # facebook, instagram, linkedin, twitter
    tailored_caption = Column(Text, nullable=False)
    tailored_media_urls = Column(JSON_TYPE, default=list, nullable=False)

    dispatch_key = Column(String(128), unique=True, nullable=False, index=True) # Idempotency key
    provider_post_id = Column(String(128), nullable=True, index=True)
    published_url = Column(Text, nullable=True) # Live link to published post

    status = Column(String(32), default="PENDING", nullable=False, index=True) # PENDING, SUBMITTED, PUBLISHED, FAILED
    error_message = Column(Text, nullable=True)
    published_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time, nullable=False)

    post = relationship("SocialPost", back_populates="dispatches")
    connection = relationship("SocialAccountConnection", back_populates="dispatches")
    analytics = relationship("SocialAnalyticsSnapshot", back_populates="dispatch", uselist=False, cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "post_id": self.post_id,
            "connection_id": self.connection_id,
            "platform": self.platform,
            "account_name": self.connection.account_name if self.connection else self.platform,
            "tailored_caption": self.tailored_caption,
            "tailored_media_urls": self.tailored_media_urls or [],
            "dispatch_key": self.dispatch_key,
            "provider_post_id": self.provider_post_id,
            "published_url": self.published_url,
            "status": self.status,
            "error_message": self.error_message,
            "published_at": self.published_at.isoformat() if self.published_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


# ─────────────────────────────────────────────────────────────────────────────
# 5. social_analytics_snapshots — Engagement Data Per Dispatch
# ─────────────────────────────────────────────────────────────────────────────
class SocialAnalyticsSnapshot(BaseModel):
    __tablename__ = 'social_analytics_snapshots'
    __table_args__ = (
        Index('ix_soc_ana_comp_plat', 'company_id', 'platform'),
    )

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey('platform_clients.id', ondelete='CASCADE'), nullable=False, index=True)
    company_id = Column(Integer, ForeignKey('associated_companies.id', ondelete='CASCADE'), nullable=False, index=True)
    dispatch_id = Column(Integer, ForeignKey('social_post_dispatches.id', ondelete='CASCADE'), unique=True, nullable=False, index=True)

    platform = Column(String(32), nullable=False, index=True)

    # Metrics (nullable to distinguish actual 0 from unsupported / missing)
    impressions = Column(Integer, nullable=True)
    reach = Column(Integer, nullable=True)
    likes = Column(Integer, nullable=True)
    comments = Column(Integer, nullable=True)
    shares = Column(Integer, nullable=True)
    clicks = Column(Integer, nullable=True)
    video_views = Column(Integer, nullable=True)
    engagement_rate = Column(Float, nullable=True)

    data_availability = Column(String(32), default="AVAILABLE", nullable=False) # AVAILABLE, ZERO_METRICS, UNSUPPORTED, PENDING_PLATFORM_DATA
    raw_metrics = Column(JSON_TYPE, default=dict, nullable=False)
    synced_at = Column(DateTime, default=get_indian_time, nullable=False)

    dispatch = relationship("SocialPostDispatch", back_populates="analytics")

    def to_dict(self):
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "company_id": self.company_id,
            "dispatch_id": self.dispatch_id,
            "platform": self.platform,
            "impressions": self.impressions,
            "reach": self.reach,
            "likes": self.likes,
            "comments": self.comments,
            "shares": self.shares,
            "clicks": self.clicks,
            "video_views": self.video_views,
            "engagement_rate": self.engagement_rate,
            "data_availability": self.data_availability,
            "raw_metrics": self.raw_metrics or {},
            "synced_at": self.synced_at.isoformat() if self.synced_at else None,
        }


# ─────────────────────────────────────────────────────────────────────────────
# 6. social_webhook_events — Idempotent Webhook Processing Log
# ─────────────────────────────────────────────────────────────────────────────
class SocialWebhookEvent(BaseModel):
    __tablename__ = 'social_webhook_events'

    id = Column(Integer, primary_key=True, index=True)
    provider = Column(String(32), default="zernio", nullable=False)
    event_id = Column(String(128), unique=True, nullable=False, index=True)
    event_type = Column(String(64), nullable=False)
    payload = Column(JSON_TYPE, default=dict, nullable=False)
    processed = Column(Boolean, default=False, nullable=False)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=get_indian_time, nullable=False)
