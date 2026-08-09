"""
System Feature Flags Model (Release 1A Feature Flag Layer)
Provides Layer 2 granular operational feature control per company and vertical.
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, UniqueConstraint, ForeignKey
from datetime import datetime
from app.models.base import Base


class SystemFeatureFlag(Base):
    """
    Granular feature flag control.
    Precedence: Layer 1 Environment Flag (OFF) > Layer 2 DB Flag (OFF) > Feature Enabled.
    """
    __tablename__ = 'system_feature_flags'
    __table_args__ = (
        UniqueConstraint('company_id', 'vertical', 'feature_key', name='uq_feature_flag_company_vert_key'),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    company_id = Column(Integer, ForeignKey('associated_companies.id', ondelete='RESTRICT'), nullable=False, default=1, index=True)
    vertical = Column(String(50), nullable=False, default='GENERAL', index=True)  # SOLAR, EV, REAL_ESTATE, GENERAL, ALL
    feature_key = Column(String(100), nullable=False, index=True) # WA_AI_SHADOW, READONLY_ADS_SYNC, CAPI_DISPATCH, etc.
    is_enabled = Column(Boolean, nullable=False, default=False)
    
    updated_by_staff_id = Column(Integer, ForeignKey('staff_employees.id', ondelete='SET NULL'), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<SystemFeatureFlag company={self.company_id} vert={self.vertical} key={self.feature_key} enabled={self.is_enabled}>'
