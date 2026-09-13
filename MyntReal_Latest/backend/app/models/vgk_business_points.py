"""
VGK Self-Business Points Accrual Models
Tracks self-business DVR milestones (₹5,00,000 threshold), points accruals,
carry forward volumes, liability offsets, and reversals per partner and lead.
"""

from sqlalchemy import Column, Integer, String, Numeric, DateTime, ForeignKey, text
from app.models.base import BaseModel
from datetime import datetime
import pytz


def get_indian_time():
    """Get current datetime in Indian Standard Time (Asia/Kolkata)"""
    indian_tz = pytz.timezone('Asia/Kolkata')
    return datetime.now(indian_tz)


class VGKSelfBusinessPointsAccrualLedger(BaseModel):
    """
    Audit ledger tracking every incremental evaluation of deal value received (DVR)
    for self-business points.
    Milestone threshold: ₹5,00,000 DVR = 50,000 points.
    """
    __tablename__ = 'vgk_self_business_points_accrual_ledger'

    id = Column(Integer, primary_key=True, autoincrement=True)
    partner_id = Column(Integer, ForeignKey('official_partners.id', ondelete='CASCADE'), nullable=False, index=True)
    lead_id = Column(Integer, ForeignKey('crm_leads.id', ondelete='CASCADE'), nullable=False, index=True)

    previous_lead_dvr = Column(Numeric(12, 2), nullable=False, default=0.00)
    current_lead_dvr = Column(Numeric(12, 2), nullable=False, default=0.00)
    incremental_dvr = Column(Numeric(12, 2), nullable=False, default=0.00)

    partner_cumulative_dvr_before = Column(Numeric(14, 2), nullable=False, default=0.00)
    partner_cumulative_dvr_after = Column(Numeric(14, 2), nullable=False, default=0.00)

    milestones_crossed = Column(Integer, nullable=False, default=0)
    points_awarded = Column(Numeric(12, 2), nullable=False, default=0.00)
    carry_forward_volume = Column(Numeric(12, 2), nullable=False, default=0.00)

    ledger_entry_id = Column(Integer, nullable=True)
    transaction_type = Column(String(30), nullable=False, default='ACCRUAL')  # 'ACCRUAL' or 'REVERSAL'
    liability_offset_amount = Column(Numeric(12, 2), nullable=False, default=0.00)

    created_at = Column(DateTime(timezone=True), default=get_indian_time, nullable=False, index=True)

    def to_dict(self):
        return {
            'id': self.id,
            'partner_id': self.partner_id,
            'lead_id': self.lead_id,
            'previous_lead_dvr': float(self.previous_lead_dvr or 0),
            'current_lead_dvr': float(self.current_lead_dvr or 0),
            'incremental_dvr': float(self.incremental_dvr or 0),
            'partner_cumulative_dvr_before': float(self.partner_cumulative_dvr_before or 0),
            'partner_cumulative_dvr_after': float(self.partner_cumulative_dvr_after or 0),
            'milestones_crossed': self.milestones_crossed,
            'points_awarded': float(self.points_awarded or 0),
            'carry_forward_volume': float(self.carry_forward_volume or 0),
            'ledger_entry_id': self.ledger_entry_id,
            'transaction_type': self.transaction_type,
            'liability_offset_amount': float(self.liability_offset_amount or 0),
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
