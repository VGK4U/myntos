"""
Meta Daily Insights Model (Release 1A Analytics Layer)
Stores daily performance metrics synced from Meta Graph Insights API.
Preserves Meta's native reporting date for 1:1 reconciliation against Ads Manager.
"""

from sqlalchemy import Column, Integer, String, Date, DateTime, Numeric, UniqueConstraint, ForeignKey, Index
from datetime import datetime
from app.models.base import Base


class MetaDailyInsights(Base):
    """
    Meta Daily Insights performance table.
    Atomic UPSERT on (company_id, ad_id, meta_reporting_date).
    READ-ONLY reporting model.
    """
    __tablename__ = 'meta_daily_insights'
    __table_args__ = (
        UniqueConstraint('company_id', 'ad_id', 'meta_reporting_date', name='uq_meta_daily_insights'),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    company_id = Column(Integer, ForeignKey('associated_companies.id', ondelete='RESTRICT'), nullable=False, index=True)
    
    ad_account_id = Column(String(50), nullable=False, index=True)
    campaign_id = Column(String(50), nullable=False, index=True)
    campaign_name = Column(String(200), nullable=True)
    adset_id = Column(String(50), nullable=False, index=True)
    adset_name = Column(String(200), nullable=True)
    ad_id = Column(String(50), nullable=False, index=True)
    ad_name = Column(String(200), nullable=True)
    
    # Timezone & Dates (Decoupled)
    meta_ad_account_timezone = Column(String(50), nullable=False, default='Asia/Kolkata')
    meta_reporting_date = Column(Date, nullable=False, index=True)  # Native Meta Date (Authoritative)
    myntos_display_timezone = Column(String(50), nullable=False, default='Asia/Kolkata')
    myntos_display_date = Column(Date, nullable=True)
    
    spend = Column(Numeric(12, 2), nullable=False, default=0.00)
    impressions = Column(Integer, nullable=False, default=0)
    reach = Column(Integer, nullable=False, default=0)
    clicks = Column(Integer, nullable=False, default=0)
    ctr = Column(Numeric(6, 4), nullable=False, default=0.0000)
    cpc = Column(Numeric(10, 2), nullable=False, default=0.00)
    cpm = Column(Numeric(10, 2), nullable=False, default=0.00)
    leads_count = Column(Integer, nullable=False, default=0)
    cpl = Column(Numeric(10, 2), nullable=False, default=0.00)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f'<MetaDailyInsights ad={self.ad_id} date={self.meta_reporting_date} spend={self.spend}>'
