"""
Immutable Meta Attribution Model (Release 1A Attribution Layer)
Stores original, unalterable acquisition source parameters for Meta Lead Ads.
"""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Index
from datetime import datetime
from app.models.base import Base


class MetaLeadsAttribution(Base):
    """
    Immutable Meta Lead Attribution model.
    1:1 relationship with crm_leads.
    Preserves original campaign, adset, ad, form, and UTM values at time of acquisition.
    """
    __tablename__ = 'meta_leads_attribution'

    id = Column(Integer, primary_key=True, autoincrement=True)
    company_id = Column(Integer, ForeignKey('associated_companies.id', ondelete='RESTRICT'), nullable=False, default=1, index=True)
    lead_id = Column(Integer, ForeignKey('crm_leads.id', ondelete='CASCADE'), nullable=False, unique=True, index=True)
    
    meta_lead_id = Column(String(50), nullable=False, index=True)
    meta_campaign_id = Column(String(50), nullable=True, index=True)
    meta_campaign_name = Column(String(200), nullable=True)
    meta_adset_id = Column(String(50), nullable=True, index=True)
    meta_adset_name = Column(String(200), nullable=True)
    meta_ad_id = Column(String(50), nullable=True, index=True)
    meta_ad_name = Column(String(200), nullable=True)
    meta_form_id = Column(String(50), nullable=True, index=True)
    meta_form_name = Column(String(200), nullable=True)
    
    utm_source = Column(String(100), nullable=True)
    utm_medium = Column(String(100), nullable=True)
    utm_campaign = Column(String(100), nullable=True)
    utm_content = Column(String(100), nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f'<MetaLeadsAttribution lead_id={self.lead_id} fb_lead_id={self.meta_lead_id} campaign={self.meta_campaign_id}>'
