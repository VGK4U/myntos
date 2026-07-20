"""
DC Protocol Apr 2026: CRM Commission Entries — MNR / Partner referral chain.

Separate from vgk_team_income_entries (VGK-only path, untouched).
L1   = source earner (non-activated VGK L1 rate for the lead's category)
guru = upline of source (2% OF L1 commission amount — not of revenue)
L4   = adi_guru / support manually set on lead (non-activated VGK L4 rate)
"""

from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Numeric, DateTime,
    ForeignKey, UniqueConstraint, Index, Text, Boolean
)
from app.models.base import BaseModel, get_indian_time


class CRMCommissionEntry(BaseModel):
    __tablename__ = 'crm_commission_entries'

    id = Column(Integer, primary_key=True, index=True)
    entry_number = Column(String(30), unique=True, nullable=False, index=True)
    company_id = Column(Integer, nullable=True)

    referrer_type = Column(String(20), nullable=False)       # 'mnr' | 'partner'
    referrer_id = Column(String(50), nullable=False, index=True)
    referrer_name = Column(String(200), nullable=True)

    level = Column(String(10), nullable=False)               # 'L1' | 'guru' | 'L4'

    source_lead_id = Column(
        Integer,
        ForeignKey('crm_leads.id', ondelete='SET NULL'),
        nullable=True,
        index=True,
    )
    source_transaction_id = Column(Integer, nullable=True, index=True)

    category_id = Column(
        Integer,
        ForeignKey('signup_categories.id', ondelete='SET NULL'),
        nullable=True,
    )
    category_name = Column(String(150), nullable=True)       # snapshot at creation time

    revenue_amount = Column(Numeric(12, 2), nullable=False, default=0)
    commission_pct = Column(Numeric(5, 2), nullable=False, default=0)
    commission_amount = Column(Numeric(10, 2), nullable=False, default=0)

    status = Column(String(20), nullable=False, default='PENDING')   # PENDING | CONFIRMED | CANCELLED
    notes = Column(Text, nullable=True)

    confirmed_at = Column(DateTime, nullable=True)
    confirmed_by_id = Column(
        Integer,
        ForeignKey('staff_employees.id', ondelete='SET NULL'),
        nullable=True,
    )

    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time, nullable=False)

    __table_args__ = (
        UniqueConstraint(
            'source_transaction_id', 'referrer_id', 'level',
            name='uq_crm_comm_txn_ref_level',
        ),
        Index('idx_crm_comm_referrer', 'referrer_type', 'referrer_id'),
        Index('idx_crm_comm_lead', 'source_lead_id'),
        Index('idx_crm_comm_status', 'status'),
        Index('idx_crm_comm_company', 'company_id'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'entry_number': self.entry_number,
            'company_id': self.company_id,
            'referrer_type': self.referrer_type,
            'referrer_id': self.referrer_id,
            'referrer_name': self.referrer_name,
            'level': self.level,
            'source_lead_id': self.source_lead_id,
            'source_transaction_id': self.source_transaction_id,
            'category_id': self.category_id,
            'category_name': self.category_name,
            'revenue_amount': float(self.revenue_amount or 0),
            'commission_pct': float(self.commission_pct or 0),
            'commission_amount': float(self.commission_amount or 0),
            'status': self.status,
            'notes': self.notes,
            'confirmed_at': self.confirmed_at.isoformat() if self.confirmed_at else None,
            'confirmed_by_id': self.confirmed_by_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
