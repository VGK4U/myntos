"""
Meta Ads Read-Only Models (Phase 2 Meta Integration Layer)
Stores synchronized campaign hierarchy, ad sets, ads, creatives, and API permission audit.
READ-ONLY tables. Zero write operations to Meta Ads Manager permitted.
"""

from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, JSON, ForeignKey, UniqueConstraint, Index
from datetime import datetime
from app.models.base import Base


class MetaCampaign(Base):
    """Meta Campaign Read-Only Snapshot Model."""
    __tablename__ = 'meta_campaigns'
    __table_args__ = (
        UniqueConstraint('company_id', 'campaign_id', name='uq_meta_campaign_company_id'),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    company_id = Column(Integer, ForeignKey('associated_companies.id', ondelete='RESTRICT'), nullable=False, index=True)
    
    campaign_id = Column(String(50), nullable=False, index=True)
    account_id = Column(String(50), nullable=False, index=True)
    name = Column(String(200), nullable=False)
    objective = Column(String(50), nullable=True)
    status = Column(String(30), nullable=False, default='PAUSED')  # ACTIVE, PAUSED, ARCHIVED
    
    daily_budget = Column(Float, nullable=True)
    lifetime_budget = Column(Float, nullable=True)
    start_time = Column(DateTime, nullable=True)
    stop_time = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class MetaAdSet(Base):
    """Meta Ad Set Read-Only Snapshot Model."""
    __tablename__ = 'meta_adsets'
    __table_args__ = (
        UniqueConstraint('company_id', 'adset_id', name='uq_meta_adset_company_id'),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    company_id = Column(Integer, ForeignKey('associated_companies.id', ondelete='RESTRICT'), nullable=False, index=True)
    
    adset_id = Column(String(50), nullable=False, index=True)
    campaign_id = Column(String(50), nullable=False, index=True)
    name = Column(String(200), nullable=False)
    status = Column(String(30), nullable=False, default='PAUSED')
    
    targeting_summary = Column(JSON, nullable=True)
    optimization_goal = Column(String(50), nullable=True)
    billing_event = Column(String(50), nullable=True)
    daily_budget = Column(Float, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class MetaAd(Base):
    """Meta Ad Read-Only Snapshot Model."""
    __tablename__ = 'meta_ads'
    __table_args__ = (
        UniqueConstraint('company_id', 'ad_id', name='uq_meta_ad_company_id'),
        UniqueConstraint('company_id', 'ad_fingerprint', name='uq_meta_ads_company_fingerprint'),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    company_id = Column(Integer, ForeignKey('associated_companies.id', ondelete='RESTRICT'), nullable=False, index=True)
    
    ad_id = Column(String(50), nullable=False, index=True)
    adset_id = Column(String(50), nullable=False, index=True)
    campaign_id = Column(String(50), nullable=False, index=True)
    name = Column(String(200), nullable=False)
    creative_id = Column(String(50), nullable=True, index=True)
    status = Column(String(30), nullable=False, default='PAUSED')
    ad_fingerprint = Column(String(100), nullable=True, index=True)
    fingerprint_version = Column(Integer, nullable=False, default=1)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class MetaCreative(Base):
    """Meta Creative Read-Only Snapshot Model."""
    __tablename__ = 'meta_creatives'
    __table_args__ = (
        UniqueConstraint('company_id', 'creative_id', name='uq_meta_creative_company_id'),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    company_id = Column(Integer, ForeignKey('associated_companies.id', ondelete='RESTRICT'), nullable=False, index=True)
    
    creative_id = Column(String(50), nullable=False, index=True)
    headline = Column(String(300), nullable=True)
    primary_text = Column(Text, nullable=True)
    description = Column(Text, nullable=True)
    call_to_action_type = Column(String(50), nullable=True)
    image_url_ref = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class MetaPermission(Base):
    """Meta Graph API Permission Audit Record."""
    __tablename__ = 'meta_permissions'

    id = Column(Integer, primary_key=True, autoincrement=True)
    company_id = Column(Integer, ForeignKey('associated_companies.id', ondelete='RESTRICT'), nullable=False, index=True)
    
    permission_name = Column(String(100), nullable=False)  # ads_read, read_insights, leads_retrieval
    endpoint_requiring = Column(String(150), nullable=False)
    token_type = Column(String(50), nullable=False, default='PAGE_ACCESS_TOKEN')
    verification_status = Column(String(100), nullable=False, default='VERIFIED')
    notes = Column(Text, nullable=True)
    
    checked_at = Column(DateTime, default=datetime.utcnow, nullable=False)
