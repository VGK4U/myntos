"""
VGK Wallet Transaction Ledger (DC Protocol Mar 2026)

Every credit and debit against a member's vgk_cash_wallet is logged here.
txn_type values:
  INCOME_CREDIT    — cash income credited at Sales confirmation (gross)
  INCOME_DEDUCTION — admin charges + TDS deducted at Accounts release
  SERVICE_DEBIT    — member uses wallet to pay for a VGK service
  VENDOR_DEBIT     — member uses wallet to pay for a vendor/marketplace purchase
  WITHDRAWAL       — staff initiates payout/withdrawal
  ADJUSTMENT       — manual adjustment by admin
"""

from sqlalchemy import (
    Column, Integer, String, Numeric, DateTime, Text, ForeignKey, Index, CheckConstraint
)
from app.models.base import Base, BaseModel, get_indian_time


class VGKWalletTransaction(BaseModel):
    __tablename__ = 'vgk_wallet_transactions'

    id                    = Column(Integer, primary_key=True, index=True)
    company_id            = Column(Integer, ForeignKey('associated_companies.id'), nullable=False, index=True)
    partner_id            = Column(Integer, ForeignKey('official_partners.id', ondelete='CASCADE'), nullable=False, index=True)

    txn_type              = Column(String(30), nullable=False)
    direction             = Column(String(2),  nullable=False)

    amount                = Column(Numeric(15, 2), nullable=False)
    wallet_before         = Column(Numeric(15, 2), nullable=False, default=0)
    wallet_after          = Column(Numeric(15, 2), nullable=False, default=0)

    ref_type              = Column(String(40), nullable=True)
    ref_id                = Column(Integer, nullable=True)

    description           = Column(Text, nullable=True)
    initiated_by_staff_id = Column(Integer, ForeignKey('staff_employees.id', ondelete='SET NULL'), nullable=True)

    created_at            = Column(DateTime, default=get_indian_time, nullable=False)

    __table_args__ = (
        CheckConstraint("direction IN ('CR','DR')", name='vgk_wallet_txn_direction_check'),
        CheckConstraint(
            "txn_type IN ("
            "'INCOME_CREDIT','INCOME_DEDUCTION','SERVICE_DEBIT','VENDOR_DEBIT',"
            "'WITHDRAWAL','ADJUSTMENT',"
            "'SOLAR_ADVANCE_CREDIT','SLAB_BONUS_CREDIT','SOLAR_ADVANCE_RECOVERY',"
            "'SOLAR_ADV_PAYOUT','SLAB_BONUS_PAYOUT',"
            "'COMPANY_PAYOUT','COMPANY_PAYOUT_DEDUCT'"
            ")",
            name='vgk_wallet_txn_type_check'
        ),
        Index('idx_vgk_wallet_txn_partner', 'company_id', 'partner_id', 'created_at'),
        Index('idx_vgk_wallet_txn_ref', 'ref_type', 'ref_id'),
    )

    def __repr__(self):
        return f'<VGKWalletTxn {self.direction} ₹{self.amount} partner={self.partner_id}>'

    def to_dict(self):
        return {
            'id':                    self.id,
            'company_id':            self.company_id,
            'partner_id':            self.partner_id,
            'txn_type':              self.txn_type,
            'direction':             self.direction,
            'amount':                float(self.amount or 0),
            'wallet_before':         float(self.wallet_before or 0),
            'wallet_after':          float(self.wallet_after or 0),
            'ref_type':              self.ref_type,
            'ref_id':                self.ref_id,
            'description':           self.description,
            'initiated_by_staff_id': self.initiated_by_staff_id,
            'created_at':            self.created_at.isoformat() if self.created_at else None,
        }
