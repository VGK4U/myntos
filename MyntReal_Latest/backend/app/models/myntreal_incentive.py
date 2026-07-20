"""
MyntReal & Zynova Incentive System Models
DC Protocol: All tables include company_id for multi-company segregation
Supports MNR Points system, category-based incentives, and Zynova hierarchical structure
Created: December 2025
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey, Float, Index, Enum as SQLEnum, Numeric
from sqlalchemy.orm import relationship
from app.models.base import BaseModel
from datetime import datetime
import pytz
import enum


def get_indian_time():
    """Get current datetime in Indian Standard Time (Asia/Kolkata)"""
    indian_tz = pytz.timezone('Asia/Kolkata')
    return datetime.now(indian_tz).replace(tzinfo=None)


class PointsTransactionType(enum.Enum):
    INITIAL_ALLOCATION = "initial_allocation"
    CONSUMPTION = "consumption"
    CREDIT = "credit"
    DEBIT = "debit"
    REFUND = "refund"


class IncentiveCalculationMode(enum.Enum):
    POINTS = "points"
    PERCENTAGE = "percentage"


class IncentiveStatus(enum.Enum):
    DRAFT = "draft"
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class ZynovaRole(enum.Enum):
    PROMOTER = "promoter"
    TEAM_LEADER = "team_leader"
    ZONAL_MANAGER = "zonal_manager"
    DIRECTOR = "director"


class MNRPointsBalance(BaseModel):
    """
    MNR Points Balance Table
    Tracks the 15,000 initial points allocation for each active MNR member
    DC Protocol: company_id for multi-company segregation
    Updated Dec 28, 2025: Added receipt_no and expiry_date for receipt generation
    """
    __tablename__ = 'mnr_points_balance'
    __table_args__ = (
        Index('ix_mnr_points_balance_company', 'company_id'),
        Index('ix_mnr_points_balance_user', 'user_id'),
        Index('ix_mnr_points_balance_receipt', 'receipt_no'),
    )
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    company_id = Column(Integer, ForeignKey('associated_companies.id'), nullable=False, index=True)
    user_id = Column(String(12), ForeignKey('user.id'), nullable=False, index=True)
    
    # DC Protocol (Feb 2026): Default 30000 points for all activated users
    initial_points = Column(Float, default=30000, nullable=False)
    current_balance = Column(Float, default=30000, nullable=False)
    total_consumed = Column(Float, default=0, nullable=False)
    total_credited = Column(Float, default=0, nullable=False)
    
    receipt_no = Column(String(15), nullable=True, unique=True, index=True)
    expiry_date = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time)
    
    def to_dict(self):
        return {
            'id': self.id,
            'company_id': self.company_id,
            'user_id': self.user_id,
            'initial_points': self.initial_points,
            'current_balance': self.current_balance,
            'total_consumed': self.total_consumed,
            'total_credited': self.total_credited,
            'receipt_no': self.receipt_no,
            'expiry_date': self.expiry_date.isoformat() if self.expiry_date else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class MNRPointsTransaction(BaseModel):
    """
    MNR Points Transaction History Table
    Tracks all points consumption, credits, and debits
    DC Protocol: company_id for multi-company segregation
    """
    __tablename__ = 'mnr_points_transactions'
    __table_args__ = (
        Index('ix_mnr_points_txn_company', 'company_id'),
        Index('ix_mnr_points_txn_user', 'user_id'),
        Index('ix_mnr_points_txn_type', 'transaction_type'),
        Index('ix_mnr_points_txn_date', 'created_at'),
    )
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    company_id = Column(Integer, ForeignKey('associated_companies.id'), nullable=False, index=True)
    user_id = Column(String(12), ForeignKey('user.id'), nullable=False, index=True)
    
    transaction_type = Column(String(30), nullable=False)
    amount = Column(Float, nullable=False)
    balance_after = Column(Float, nullable=False)
    
    category_id = Column(Integer, ForeignKey('signup_categories.id'), nullable=True)
    lead_id = Column(Integer, ForeignKey('crm_leads.id', ondelete='SET NULL'), nullable=True)
    crm_transaction_id = Column(Integer, ForeignKey('crm_lead_transactions.id', ondelete='SET NULL'), nullable=True)
    
    benefit_category = Column(String(50), nullable=True)
    
    description = Column(Text, nullable=True)
    
    created_by_id = Column(String(50), nullable=True)
    created_by_type = Column(String(20), nullable=True)
    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    
    def to_dict(self):
        return {
            'id': self.id,
            'company_id': self.company_id,
            'user_id': self.user_id,
            'transaction_type': self.transaction_type,
            'amount': self.amount,
            'balance_after': self.balance_after,
            'category_id': self.category_id,
            'lead_id': self.lead_id,
            'crm_transaction_id': self.crm_transaction_id,
            'benefit_category': self.benefit_category,
            'description': self.description,
            'created_by_id': self.created_by_id,
            'created_by_type': self.created_by_type,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class MyntRealIncentive(BaseModel):
    """
    MyntReal Incentive Records Table
    Tracks incentives for EV, Solar categories with Guru/Adi Guru structure
    DC Protocol: company_id for multi-company segregation
    """
    __tablename__ = 'myntreal_incentives'
    __table_args__ = (
        Index('ix_myntreal_inc_company', 'company_id'),
        Index('ix_myntreal_inc_lead', 'lead_id'),
        Index('ix_myntreal_inc_mnr', 'mnr_id'),
        Index('ix_myntreal_inc_status', 'status'),
        Index('ix_myntreal_inc_date', 'created_at'),
    )
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    company_id = Column(Integer, ForeignKey('associated_companies.id'), nullable=False, index=True)
    
    lead_id = Column(Integer, ForeignKey('crm_leads.id', ondelete='CASCADE'), nullable=False)
    transaction_id = Column(Integer, ForeignKey('crm_lead_transactions.id', ondelete='SET NULL'), nullable=True)
    category_id = Column(Integer, ForeignKey('signup_categories.id'), nullable=True)
    property_id = Column(Integer, nullable=True)
    
    revenue_amount = Column(Float, nullable=False)
    calculation_mode = Column(String(20), default='percentage', nullable=False)
    is_repeat_deal = Column(Boolean, default=False, nullable=False)
    is_exclusive_model = Column(Boolean, default=False, nullable=False)
    
    mnr_id = Column(String(12), ForeignKey('user.id', ondelete='SET NULL'), nullable=True)
    mnr_rate = Column(Float, nullable=True)
    mnr_rate_type = Column(String(20), nullable=True)
    mnr_amount = Column(Float, nullable=True)
    points_consumed = Column(Float, nullable=True)
    
    guru_id = Column(String(12), ForeignKey('user.id', ondelete='SET NULL'), nullable=True)
    guru_rate = Column(Float, nullable=True)
    guru_amount = Column(Float, nullable=True)
    guru_locked = Column(Boolean, default=True, nullable=False)
    
    adiguru_id = Column(String(12), ForeignKey('user.id', ondelete='SET NULL'), nullable=True)
    adiguru_rate = Column(Float, nullable=True)
    adiguru_amount = Column(Float, nullable=True)
    
    primary_assignee_type = Column(String(20), nullable=True)
    primary_assignee_id = Column(Integer, nullable=True)
    primary_assignee_rate = Column(Float, nullable=True)
    primary_assignee_amount = Column(Float, nullable=True)
    
    supporter_type = Column(String(20), nullable=True)
    supporter_id = Column(Integer, nullable=True)
    supporter_rate = Column(Float, nullable=True)
    supporter_amount = Column(Float, nullable=True)
    
    partner_id = Column(Integer, ForeignKey('official_partners.id', ondelete='SET NULL'), nullable=True)
    partner_rate = Column(Float, nullable=True)
    partner_amount = Column(Float, nullable=True)
    
    status = Column(String(20), default='draft', nullable=False)
    approved_by_id = Column(Integer, ForeignKey('staff_employees.id', ondelete='SET NULL'), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    rejection_reason = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time)
    
    def to_dict(self):
        return {
            'id': self.id,
            'company_id': self.company_id,
            'lead_id': self.lead_id,
            'transaction_id': self.transaction_id,
            'category_id': self.category_id,
            'property_id': self.property_id,
            'revenue_amount': self.revenue_amount,
            'calculation_mode': self.calculation_mode,
            'is_repeat_deal': self.is_repeat_deal,
            'is_exclusive_model': self.is_exclusive_model,
            'mnr_id': self.mnr_id,
            'mnr_rate': self.mnr_rate,
            'mnr_rate_type': self.mnr_rate_type,
            'mnr_amount': self.mnr_amount,
            'points_consumed': self.points_consumed,
            'guru_id': self.guru_id,
            'guru_rate': self.guru_rate,
            'guru_amount': self.guru_amount,
            'guru_locked': self.guru_locked,
            'adiguru_id': self.adiguru_id,
            'adiguru_rate': self.adiguru_rate,
            'adiguru_amount': self.adiguru_amount,
            'primary_assignee_type': self.primary_assignee_type,
            'primary_assignee_id': self.primary_assignee_id,
            'primary_assignee_rate': self.primary_assignee_rate,
            'primary_assignee_amount': self.primary_assignee_amount,
            'supporter_type': self.supporter_type,
            'supporter_id': self.supporter_id,
            'supporter_rate': self.supporter_rate,
            'supporter_amount': self.supporter_amount,
            'partner_id': self.partner_id,
            'partner_rate': self.partner_rate,
            'partner_amount': self.partner_amount,
            'status': self.status,
            'approved_by_id': self.approved_by_id,
            'approved_at': self.approved_at.isoformat() if self.approved_at else None,
            'rejection_reason': self.rejection_reason,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class ZynovaMember(BaseModel):
    """
    Zynova Membership Table
    Tracks MNR members in the Zynova hierarchy with SEGMENT-SPECIFIC structures
    VGK Care (Insurance) and VGK Real Dreams (Real Estate) have separate teams, uplines, and promotions
    DC Protocol: company_id for multi-company segregation
    Updated: December 2025 - Added segment-specific fields for dual program support
    """
    __tablename__ = 'zynova_members'
    __table_args__ = (
        Index('ix_zynova_member_company', 'company_id'),
        Index('ix_zynova_member_user', 'user_id'),
        Index('ix_zynova_member_parent', 'parent_id'),
        Index('ix_zynova_member_role', 'role'),
        Index('ix_zynova_member_re_role', 'real_estate_role'),
        Index('ix_zynova_member_ins_role', 'insurance_role'),
    )
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    company_id = Column(Integer, ForeignKey('associated_companies.id'), nullable=False, index=True)
    user_id = Column(String(12), ForeignKey('user.id'), nullable=False, index=True)
    
    # Legacy fields (kept for backward compatibility)
    role = Column(String(20), default='promoter', nullable=False)
    parent_id = Column(Integer, ForeignKey('zynova_members.id', ondelete='SET NULL'), nullable=True)
    
    # VGK Real Dreams (Real Estate) - Segment-specific fields
    real_estate_role = Column(String(20), default='promoter', nullable=True)
    real_estate_upline_id = Column(Integer, ForeignKey('zynova_members.id', ondelete='SET NULL'), nullable=True)
    real_estate_revenue_total = Column(Float, default=0, nullable=False)
    real_estate_team_revenue = Column(Float, default=0, nullable=False)
    real_estate_promoted_at = Column(DateTime, nullable=True)
    real_estate_promotion_deadline = Column(DateTime, nullable=True)
    
    # VGK Care (Insurance) - Segment-specific fields
    insurance_role = Column(String(20), default='promoter', nullable=True)
    insurance_upline_id = Column(Integer, ForeignKey('zynova_members.id', ondelete='SET NULL'), nullable=True)
    insurance_revenue_total = Column(Float, default=0, nullable=False)
    insurance_team_revenue = Column(Float, default=0, nullable=False)
    insurance_promoted_at = Column(DateTime, nullable=True)
    insurance_promotion_deadline = Column(DateTime, nullable=True)
    
    # Activation date for time limit calculations (6 months from Jan 1, 2026 for existing users)
    activation_date = Column(DateTime, nullable=True)
    
    joined_at = Column(DateTime, default=get_indian_time, nullable=False)
    role_promoted_at = Column(DateTime, nullable=True)
    promotion_deadline = Column(DateTime, nullable=True)
    
    revenue_since_role_start = Column(Float, default=0, nullable=False)
    total_revenue = Column(Float, default=0, nullable=False)
    team_revenue = Column(Float, default=0, nullable=False)
    
    is_active = Column(Boolean, default=True, nullable=False)
    deactivation_reason = Column(Text, nullable=True)
    deactivation_date = Column(DateTime, nullable=True)
    deactivated_by_id = Column(String(50), nullable=True)
    reactivation_date = Column(DateTime, nullable=True)
    reactivated_by_id = Column(String(50), nullable=True)
    
    created_by_id = Column(String(50), nullable=True)
    created_by_type = Column(String(20), nullable=True)
    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time)
    
    def to_dict(self):
        return {
            'id': self.id,
            'company_id': self.company_id,
            'user_id': self.user_id,
            'role': self.role,
            'parent_id': self.parent_id,
            # VGK Real Dreams (Real Estate) segment
            'real_estate_role': self.real_estate_role,
            'real_estate_upline_id': self.real_estate_upline_id,
            'real_estate_revenue_total': self.real_estate_revenue_total,
            'real_estate_team_revenue': self.real_estate_team_revenue,
            'real_estate_promoted_at': self.real_estate_promoted_at.isoformat() if self.real_estate_promoted_at else None,
            'real_estate_promotion_deadline': self.real_estate_promotion_deadline.isoformat() if self.real_estate_promotion_deadline else None,
            # VGK Care (Insurance) segment
            'insurance_role': self.insurance_role,
            'insurance_upline_id': self.insurance_upline_id,
            'insurance_revenue_total': self.insurance_revenue_total,
            'insurance_team_revenue': self.insurance_team_revenue,
            'insurance_promoted_at': self.insurance_promoted_at.isoformat() if self.insurance_promoted_at else None,
            'insurance_promotion_deadline': self.insurance_promotion_deadline.isoformat() if self.insurance_promotion_deadline else None,
            # Activation and legacy fields
            'activation_date': self.activation_date.isoformat() if self.activation_date else None,
            'joined_at': self.joined_at.isoformat() if self.joined_at else None,
            'role_promoted_at': self.role_promoted_at.isoformat() if self.role_promoted_at else None,
            'promotion_deadline': self.promotion_deadline.isoformat() if self.promotion_deadline else None,
            'revenue_since_role_start': self.revenue_since_role_start,
            'total_revenue': self.total_revenue,
            'team_revenue': self.team_revenue,
            'is_active': self.is_active,
            'deactivation_reason': self.deactivation_reason,
            'deactivation_date': self.deactivation_date.isoformat() if self.deactivation_date else None,
            'deactivated_by_id': self.deactivated_by_id,
            'reactivation_date': self.reactivation_date.isoformat() if self.reactivation_date else None,
            'reactivated_by_id': self.reactivated_by_id,
            'created_by_id': self.created_by_id,
            'created_by_type': self.created_by_type,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class ZynovaIncentive(BaseModel):
    """
    Zynova Incentive Records Table
    Tracks incentives for Insurance/Real Estate/Training with TL/ZM/Director hierarchy
    DC Protocol: company_id for multi-company segregation
    """
    __tablename__ = 'zynova_incentives'
    __table_args__ = (
        Index('ix_zynova_inc_company', 'company_id'),
        Index('ix_zynova_inc_lead', 'lead_id'),
        Index('ix_zynova_inc_promoter', 'promoter_id'),
        Index('ix_zynova_inc_status', 'status'),
        Index('ix_zynova_inc_date', 'created_at'),
    )
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    company_id = Column(Integer, ForeignKey('associated_companies.id'), nullable=False, index=True)
    
    lead_id = Column(Integer, ForeignKey('crm_leads.id', ondelete='CASCADE'), nullable=False)
    transaction_id = Column(Integer, ForeignKey('crm_lead_transactions.id', ondelete='SET NULL'), nullable=True)
    category_slug = Column(String(50), nullable=False)
    property_id = Column(Integer, nullable=True)
    
    revenue_amount = Column(Float, nullable=False)
    
    promoter_id = Column(String(12), ForeignKey('user.id', ondelete='SET NULL'), nullable=True)
    promoter_rate = Column(Float, default=50, nullable=False)
    promoter_amount = Column(Float, nullable=True)
    
    team_leader_id = Column(String(12), ForeignKey('user.id', ondelete='SET NULL'), nullable=True)
    team_leader_rate = Column(Float, default=10, nullable=True)
    team_leader_amount = Column(Float, nullable=True)
    
    zonal_manager_id = Column(String(12), ForeignKey('user.id', ondelete='SET NULL'), nullable=True)
    zonal_manager_rate = Column(Float, default=10, nullable=True)
    zonal_manager_amount = Column(Float, nullable=True)
    
    director_id = Column(String(12), ForeignKey('user.id', ondelete='SET NULL'), nullable=True)
    director_rate = Column(Float, default=5, nullable=True)
    director_amount = Column(Float, nullable=True)
    
    status = Column(String(20), default='draft', nullable=False)
    approved_by_id = Column(Integer, ForeignKey('staff_employees.id', ondelete='SET NULL'), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    rejection_reason = Column(Text, nullable=True)
    
    disbursed_at = Column(DateTime, nullable=True)
    disbursed_withdrawal_id = Column(Integer, ForeignKey('withdrawal_request.id', ondelete='SET NULL'), nullable=True)
    pending_income_id = Column(Integer, nullable=True)
    
    zynova_member_id = Column(Integer, ForeignKey('zynova_members.id', ondelete='SET NULL'), nullable=True)
    previous_status = Column(String(20), nullable=True)
    status_changed_at = Column(DateTime, nullable=True)
    status_changed_reason = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time)
    
    def to_dict(self):
        return {
            'id': self.id,
            'company_id': self.company_id,
            'lead_id': self.lead_id,
            'transaction_id': self.transaction_id,
            'category_slug': self.category_slug,
            'property_id': self.property_id,
            'revenue_amount': self.revenue_amount,
            'promoter_id': self.promoter_id,
            'promoter_rate': self.promoter_rate,
            'promoter_amount': self.promoter_amount,
            'team_leader_id': self.team_leader_id,
            'team_leader_rate': self.team_leader_rate,
            'team_leader_amount': self.team_leader_amount,
            'zonal_manager_id': self.zonal_manager_id,
            'zonal_manager_rate': self.zonal_manager_rate,
            'zonal_manager_amount': self.zonal_manager_amount,
            'director_id': self.director_id,
            'director_rate': self.director_rate,
            'director_amount': self.director_amount,
            'status': self.status,
            'approved_by_id': self.approved_by_id,
            'approved_at': self.approved_at.isoformat() if self.approved_at else None,
            'rejection_reason': self.rejection_reason,
            'disbursed_at': self.disbursed_at.isoformat() if self.disbursed_at else None,
            'disbursed_withdrawal_id': self.disbursed_withdrawal_id,
            'pending_income_id': self.pending_income_id,
            'zynova_member_id': self.zynova_member_id,
            'previous_status': self.previous_status,
            'status_changed_at': self.status_changed_at.isoformat() if self.status_changed_at else None,
            'status_changed_reason': self.status_changed_reason,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class MyntRealIncentiveRate(BaseModel):
    """
    MyntReal Incentive Rate Configuration Table
    Stores default rates for each category
    DC Protocol: company_id for multi-company segregation
    """
    __tablename__ = 'myntreal_incentive_rates'
    __table_args__ = (
        Index('ix_myntreal_rate_company', 'company_id'),
        Index('ix_myntreal_rate_category', 'category_id'),
    )
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    company_id = Column(Integer, ForeignKey('associated_companies.id'), nullable=False, index=True)
    category_id = Column(Integer, ForeignKey('signup_categories.id'), nullable=False)
    
    category_slug = Column(String(50), nullable=True)
    points_amount = Column(Float, nullable=True)
    percentage_rate = Column(Float, nullable=True)
    repeat_rate = Column(Float, nullable=True)
    
    is_points_consumable = Column(Boolean, default=False, nullable=False)
    is_exclusive = Column(Boolean, default=False, nullable=False)
    exclusive_points_amount = Column(Float, nullable=True)
    
    guru_rate = Column(Float, default=2, nullable=False)
    adiguru_rate = Column(Float, default=10, nullable=False)
    
    is_active = Column(Boolean, default=True, nullable=False)
    
    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time)
    
    def to_dict(self):
        return {
            'id': self.id,
            'company_id': self.company_id,
            'category_id': self.category_id,
            'category_slug': self.category_slug,
            'points_amount': self.points_amount,
            'percentage_rate': self.percentage_rate,
            'repeat_rate': self.repeat_rate,
            'is_points_consumable': self.is_points_consumable,
            'is_exclusive': self.is_exclusive,
            'exclusive_points_amount': self.exclusive_points_amount,
            'guru_rate': self.guru_rate,
            'adiguru_rate': self.adiguru_rate,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


DEFAULT_INCENTIVE_RATES = [
    {
        'category_slug': 'ev-franchise-b2b',
        'percentage_rate': 2,
        'repeat_rate': 1,
        'is_points_consumable': False,
        'guru_rate': 2,
        'adiguru_rate': 10
    },
    {
        'category_slug': 'ev-b2c',
        'points_amount': 7500,
        'percentage_rate': 5,
        'is_points_consumable': True,
        'is_exclusive': True,
        'exclusive_points_amount': 15000,
        'guru_rate': 2,
        'adiguru_rate': 10
    },
    {
        'category_slug': 'ev-spares',
        'percentage_rate': 5,
        'is_points_consumable': False,
        'guru_rate': 2,
        'adiguru_rate': 10
    },
    {
        'category_slug': 'solar-energy',
        'points_amount': 15000,
        'percentage_rate': 5,
        'is_points_consumable': True,
        'guru_rate': 2,
        'adiguru_rate': 10
    },
    {
        'category_slug': 'training',
        'points_amount': 7500,
        'percentage_rate': 5,
        'is_points_consumable': True,
        'guru_rate': 0,
        'adiguru_rate': 0
    },
    {
        'category_slug': 'insurance',
        'percentage_rate': 50,
        'is_points_consumable': False,
        'guru_rate': 0,
        'adiguru_rate': 0
    },
    {
        'category_slug': 'real-estate',
        'percentage_rate': 50,
        'is_points_consumable': False,
        'guru_rate': 0,
        'adiguru_rate': 0
    }
]


ZYNOVA_PROMOTION_TARGETS = {
    'team_leader': {
        'revenue_target': 100000,
        'months_limit': 6,
        'revenue_base': 'self'
    },
    'zonal_manager': {
        'revenue_target': 500000,
        'months_limit': 6,
        'revenue_base': 'self_and_team'
    },
    'director': {
        'revenue_target': 1000000,
        'months_limit': 6,
        'revenue_base': 'self_and_team'
    }
}

# VGK Care (Insurance) - Segment-specific promotion targets
ZYNOVA_INSURANCE_PROMOTION_TARGETS = {
    'promoter': {
        'revenue_target': 0,  # As soon as revenue added
        'months_limit': None,
        'revenue_base': 'self'
    },
    'team_leader': {
        'revenue_target': 100000,  # ₹1,00,000
        'months_limit': 6,  # 6 months from activation or Jan 1, 2026
        'revenue_base': 'self'
    },
    'zonal_manager': {
        'revenue_target': 500000,  # ₹5,00,000
        'months_limit': 6,  # 6 months from last promotion
        'revenue_base': 'self_and_team'
    },
    'director': {
        'revenue_target': 1000000,  # ₹10,00,000
        'months_limit': 6,  # 6 months from last promotion
        'revenue_base': 'self_and_team'
    }
}

# VGK Real Dreams (Real Estate) - Segment-specific promotion targets
ZYNOVA_REAL_ESTATE_PROMOTION_TARGETS = {
    'promoter': {
        'revenue_target': 0,  # As soon as revenue added
        'months_limit': None,
        'revenue_base': 'self'
    },
    'team_leader': {
        'revenue_target': 100000,  # ₹1,00,000
        'months_limit': 6,  # 6 months from activation or Jan 1, 2026
        'revenue_base': 'self'
    },
    'zonal_manager': {
        'revenue_target': 5000000,  # ₹50,00,000
        'months_limit': 6,  # 6 months from last promotion
        'revenue_base': 'self_and_team'
    },
    'director': {
        'revenue_target': 10000000,  # ₹1,00,00,000 (1 Crore)
        'months_limit': 6,  # 6 months from last promotion
        'revenue_base': 'self_and_team'
    }
}

# Default activation deadline for existing users (Jan 1, 2026 + 6 months = July 1, 2026)
ZYNOVA_DEFAULT_ACTIVATION_DEADLINE = '2026-07-01'


# DC Protocol (Jan 29, 2026): Stub models for Zynova segment profiles
# These models are referenced by staff_mnr_user_sidebar but may not be fully implemented
class ZynovaRealEstateProfile(BaseModel):
    """
    Zynova Real Estate Segment Profile
    Tracks user's Real Estate segment membership and progress
    """
    __tablename__ = 'zynova_real_estate_profiles'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(20), nullable=False, index=True)
    status = Column(String(20), default='inactive')
    tier = Column(String(50), nullable=True)
    properties_count = Column(Integer, default=0)
    total_commission = Column(Numeric(15, 2), default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ZynovaInsuranceProfile(BaseModel):
    """
    Zynova Insurance Segment Profile
    Tracks user's Insurance segment membership and progress
    """
    __tablename__ = 'zynova_insurance_profiles'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(20), nullable=False, index=True)
    status = Column(String(20), default='inactive')
    tier = Column(String(50), nullable=True)
    policies_count = Column(Integer, default=0)
    total_commission = Column(Numeric(15, 2), default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class MNRAccidentalInsurance(BaseModel):
    """
    MNR Accidental Insurance Records
    DC Protocol Feb 2026: Track 5 Lakhs accidental insurance for paid MNR members
    Eligibility:
    - New users: Activated on/after 3rd Feb 2026 -> Auto-eligible
    - Old users (before Feb 3, 2026): Need 2 direct activated referrals after Feb 3, 2026
    """
    __tablename__ = 'mnr_accidental_insurance'
    __table_args__ = (
        Index('ix_mnr_insurance_user', 'user_id'),
        Index('ix_mnr_insurance_status', 'status'),
        Index('ix_mnr_insurance_policy', 'policy_number'),
    )
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(12), ForeignKey('user.id'), nullable=False, index=True)
    
    policy_number = Column(String(50), nullable=True)
    insurer_name = Column(String(100), nullable=True)
    insured_amount = Column(Float, default=500000, nullable=False)
    
    insured_date = Column(DateTime, nullable=True)
    expiry_date = Column(DateTime, nullable=True)
    
    eligibility_type = Column(String(30), nullable=False)
    eligibility_met_at = Column(DateTime, nullable=True)
    referral_count_at_eligibility = Column(Integer, default=0)
    
    status = Column(String(20), default='Pending', nullable=False)
    
    issued_by_id = Column(String(50), nullable=True)
    issued_by_type = Column(String(20), nullable=True)
    issued_at = Column(DateTime, nullable=True)
    
    notes = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time)
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'policy_number': self.policy_number,
            'insurer_name': self.insurer_name,
            'insured_amount': self.insured_amount,
            'insured_date': self.insured_date.isoformat() if self.insured_date else None,
            'expiry_date': self.expiry_date.isoformat() if self.expiry_date else None,
            'eligibility_type': self.eligibility_type,
            'eligibility_met_at': self.eligibility_met_at.isoformat() if self.eligibility_met_at else None,
            'referral_count_at_eligibility': self.referral_count_at_eligibility,
            'status': self.status,
            'issued_by_id': self.issued_by_id,
            'issued_by_type': self.issued_by_type,
            'issued_at': self.issued_at.isoformat() if self.issued_at else None,
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class PointsBenefitCategory(BaseModel):
    """
    Points Benefit Categories Master Table
    DC Protocol Feb 2026: Categories for points utilization tracking
    Examples: VGK Real Dreams, VGK Care, Manual Adjustment, etc.
    """
    __tablename__ = 'points_benefit_categories'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    category_code = Column(String(30), unique=True, nullable=False)
    category_name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    display_order = Column(Integer, default=0)
    
    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    
    def to_dict(self):
        return {
            'id': self.id,
            'category_code': self.category_code,
            'category_name': self.category_name,
            'description': self.description,
            'is_active': self.is_active,
            'display_order': self.display_order
        }
