"""
VGK Incentive Brands Model (DC Protocol Jun 2026)

DC-VGK-BRAND-INCENTIVE-001: Per-brand fixed additional incentive amounts
for L1 (source partner), L2 (senior partner), and L5 (field support partner).
Brand is optionally linked to a solar lead via crm_leads.solar_brand_id.
"""

from sqlalchemy import Column, Integer, String, Numeric, Boolean, DateTime, ForeignKey, Index
from app.models.base import Base, BaseModel, get_indian_time


class VGKIncentiveBrand(BaseModel):
    """
    Brand-level additional incentive configuration.
    One row per brand per company. Staff edits via /staff/vgk/config brand section.
    """
    __tablename__ = 'vgk_incentive_brands'

    id          = Column(Integer, primary_key=True, index=True)
    company_id  = Column(Integer, ForeignKey('associated_companies.id'), nullable=False, index=True)
    brand_name  = Column(String(200), nullable=False)

    l1_amount   = Column(Numeric(12, 2), nullable=False, default=0)
    l2_amount   = Column(Numeric(12, 2), nullable=False, default=0)
    l5_amount   = Column(Numeric(12, 2), nullable=False, default=0)

    is_active   = Column(Boolean, nullable=False, default=True)

    created_at  = Column(DateTime, default=get_indian_time, nullable=False)
    updated_at  = Column(DateTime, default=get_indian_time, onupdate=get_indian_time, nullable=False)

    __table_args__ = (
        Index('idx_vgk_incentive_brands_co_active', 'company_id', 'is_active'),
    )

    def __repr__(self):
        return f'<VGKIncentiveBrand {self.brand_name} co={self.company_id}>'

    def to_dict(self):
        return {
            'id':         self.id,
            'company_id': self.company_id,
            'brand_name': self.brand_name,
            'l1_amount':  float(self.l1_amount or 0),
            'l2_amount':  float(self.l2_amount or 0),
            'l5_amount':  float(self.l5_amount or 0),
            'is_active':  self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
