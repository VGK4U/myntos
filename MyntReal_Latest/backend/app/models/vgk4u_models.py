"""
VGK4U Universal Career, Personal Production & Commission Configuration Models
Created: 2026-09-12
Scope: Authoritative configurations for VGK4U Career Ladder, Personal Production tiers, and Category Commission Waterfalls
"""

from sqlalchemy import Column, Integer, String, Numeric, Boolean, DateTime, ForeignKey, Text, UniqueConstraint
from sqlalchemy.sql import func
from app.models.base import BaseModel

class VGK4UCareerDesignationConfig(BaseModel):
    """
    Universal VGK4U Career Designation Targets & Differentials
    Ladder: MEMBER (0) -> CHANNEL_PARTNER (1) -> MANAGER (2) -> GENERAL_MANAGER (3) -> REGIONAL_MANAGER (4)
    """
    __tablename__ = 'vgk4u_career_designation_configs'

    id = Column(Integer, primary_key=True, index=True)
    designation_code = Column(String(30), unique=True, nullable=False, index=True)
    designation_name = Column(String(50), nullable=False)
    hierarchy_order = Column(Integer, unique=True, nullable=False)
    stage_own_qualifying_files = Column(Integer, nullable=False, default=0)
    required_own_qualifying_files = Column(Integer, nullable=False, default=0)
    required_active_team_members = Column(Integer, nullable=False, default=0) # Active team legs
    self_earning_pct = Column(Numeric(5, 2), nullable=False, default=0.00)
    team_differential_pct = Column(Numeric(5, 2), nullable=False, default=0.00)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f'<VGK4UCareerDesignationConfig {self.designation_code} (Order {self.hierarchy_order})>'


class VGK4UPersonalProdConfig(BaseModel):
    """
    Personal Production Commission Qualification Tiers
    Tiers: BASE (1-4 files) -> GM_QUALIFIED (5-9 files) -> RM_QUALIFIED (10+ files)
    """
    __tablename__ = 'vgk4u_personal_prod_configs'

    id = Column(Integer, primary_key=True, index=True)
    tier_code = Column(String(30), unique=True, nullable=False, index=True)
    tier_name = Column(String(50), nullable=False)
    min_qualifying_files = Column(Integer, nullable=False)
    commission_rate_pct = Column(Numeric(5, 2), nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f'<VGK4UPersonalProdConfig {self.tier_code}: {self.min_qualifying_files}+ files @ {self.commission_rate_pct}%>'


class VGK4UCategoryCommissionConfig(BaseModel):
    """
    Universal Category Commission Structure & Differential Waterfalls
    Supports: solar, ev, etc-training, real-dreams, insurance
    """
    __tablename__ = 'vgk4u_category_commission_configs'

    id = Column(Integer, primary_key=True, index=True)
    version_label = Column(String(50), nullable=False, default='v2_sep2026', index=True)
    effective_from = Column(DateTime, nullable=False)
    effective_to = Column(DateTime, nullable=True)
    category_slug = Column(String(50), nullable=False, index=True)
    category_name = Column(String(100), nullable=False)
    max_network_pool_pct = Column(Numeric(5, 2), nullable=False)
    producer_base_pct = Column(Numeric(5, 2), nullable=False)
    manager_diff_pct = Column(Numeric(5, 2), nullable=False)
    gm_diff_pct = Column(Numeric(5, 2), nullable=False)
    rm_diff_pct = Column(Numeric(5, 2), nullable=False)
    sponsor_override_pct = Column(Numeric(5, 2), nullable=False, default=0.00)
    support_journey_pct = Column(Numeric(5, 2), nullable=False, default=0.75)
    support_end_to_end_pct = Column(Numeric(5, 2), nullable=False, default=1.50)
    showroom_pct = Column(Numeric(5, 2), nullable=False, default=3.50)
    unallocated_balance_pct = Column(Numeric(5, 2), nullable=False, default=0.00)
    admin_charge_pct = Column(Numeric(5, 2), nullable=False, default=8.00)
    tds_pct = Column(Numeric(5, 2), nullable=False, default=2.00)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint('version_label', 'category_slug', name='uq_vgk4u_cat_version'),
    )

    def __repr__(self):
        return f'<VGK4UCategoryCommissionConfig {self.category_slug} ({self.version_label}) Max {self.max_network_pool_pct}%>'


class VGK4UCorporateMarginLedger(BaseModel):
    """
    VGK4U Corporate Retained Margin Ledger
    Authoritative corporate accounting ledger for Apex remainder, inactive sponsor forfeiture,
    and inactive producer forfeiture. Strictly separated from personal partner income.
    """
    __tablename__ = 'vgk4u_corporate_margin_ledger'

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, nullable=False, index=True)
    source_lead_id = Column(Integer, nullable=False, index=True)
    category_slug = Column(String(50), nullable=False, default='solar')
    program_version = Column(String(50), nullable=False, default='v2_sep2026')
    deal_value = Column(Numeric(15, 2), nullable=False)
    retained_pct = Column(Numeric(5, 2), nullable=False)
    retained_amount = Column(Numeric(15, 2), nullable=False)
    admin_charges = Column(Numeric(15, 2), nullable=False, default=0.00)
    tds_amount = Column(Numeric(15, 2), nullable=False, default=0.00)
    net_retained_amount = Column(Numeric(15, 2), nullable=False)
    retained_reason = Column(String(100), nullable=False)
    status = Column(String(20), nullable=False, default='RECORDED')
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint('company_id', 'source_lead_id', 'retained_reason', name='uq_vgk4u_corp_margin_lead_reason'),
    )

    def __repr__(self):
        return f'<VGK4UCorporateMarginLedger Lead={self.source_lead_id} {self.retained_reason} {self.retained_pct}% (₹{self.retained_amount})>'

