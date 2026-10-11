"""
MyntOS Reward Campaign, Scratch Card & Outbox Models
Phase 3 Specification: Integer paise storage, idempotent ledgers, token hashing.
"""

from sqlalchemy import (
    Column, Integer, String, BigInteger, Boolean, DateTime, ForeignKey, Index, UniqueConstraint, Text
)
from sqlalchemy.orm import relationship
from datetime import datetime, timedelta
import hashlib
import secrets
from app.models.base import Base, BaseModel, get_indian_time


class RewardCampaign(BaseModel):
    """
    Reward Campaign configuration and budget tracker.
    Amounts stored in integer paise (1 INR = 100 paise).
    """
    __tablename__ = 'reward_campaigns'

    id = Column(Integer, primary_key=True, index=True)
    campaign_name = Column(String(100), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    
    start_date = Column(DateTime, default=get_indian_time, nullable=False)
    end_date = Column(DateTime, nullable=True)

    total_budget_paise = Column(BigInteger, default=50000, nullable=False) # e.g. 50,000 paise = ₹500
    reserved_liability_paise = Column(BigInteger, default=0, nullable=False) # issued but unclaimed
    settled_expenditure_paise = Column(BigInteger, default=0, nullable=False) # claimed rewards

    max_cards = Column(Integer, default=100, nullable=False)
    issued_cards_count = Column(Integer, default=0, nullable=False)

    max_ten_rupee_count = Column(Integer, default=9, nullable=False) # <10% max (9 out of 100)
    issued_ten_rupee_count = Column(Integer, default=0, nullable=False)

    min_reward_paise = Column(Integer, default=100, nullable=False) # ₹1
    max_standard_reward_paise = Column(Integer, default=500, nullable=False) # ₹5
    
    expiry_days = Column(Integer, default=7, nullable=False)

    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time, nullable=False)

    def __repr__(self):
        return f"<RewardCampaign '{self.campaign_name}' Budget=₹{self.total_budget_paise/100:.2f}>"


class ScratchCard(BaseModel):
    """
    Scratch Card reward entitlement for a qualifying recharge.
    Stores preallocated reward in integer paise and SHA256 token hash.
    """
    __tablename__ = 'scratch_cards'

    id = Column(Integer, primary_key=True, index=True)
    campaign_id = Column(Integer, ForeignKey('reward_campaigns.id'), nullable=False, index=True)
    recharge_transaction_id = Column(Integer, ForeignKey('recharge_transactions.id'), nullable=False, unique=True, index=True)

    mobile_number = Column(String(20), nullable=False, index=True)
    brand = Column(String(50), default="Zynova Mobility", nullable=False)

    token_hash = Column(String(64), nullable=False, unique=True, index=True) # SHA256 hash of secret token
    allocated_amount_paise = Column(Integer, nullable=False) # e.g. 100 to 1000

    status = Column(String(20), default="ISSUED", nullable=False) # ISSUED, CLAIMED, EXPIRED, CANCELLED
    
    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    claimed_at = Column(DateTime, nullable=True)

    wallet_ledger_id = Column(Integer, nullable=True)

    campaign = relationship('RewardCampaign', backref='scratch_cards')
    recharge_transaction = relationship('RechargeTransaction', backref='scratch_card')

    __table_args__ = (
        Index('idx_scratch_mobile_status', 'mobile_number', 'status'),
    )

    @staticmethod
    def hash_token(raw_token: str) -> str:
        return hashlib.sha256(raw_token.encode('utf-8')).hexdigest()

    def __repr__(self):
        return f"<ScratchCard #{self.id} Txn={self.recharge_transaction_id} Amt=₹{self.allocated_amount_paise/100:.2f} Status={self.status}>"


class RewardLedger(BaseModel):
    """
    Immutable ledger transaction for scratch card reward credit.
    Bridges guest mobile identity & member accounts with idempotency protection.
    """
    __tablename__ = 'reward_ledgers'

    id = Column(Integer, primary_key=True, index=True)
    scratch_card_id = Column(Integer, ForeignKey('scratch_cards.id'), nullable=False, unique=True, index=True)
    mobile_number = Column(String(20), nullable=False, index=True)
    user_id = Column(String(12), ForeignKey('user.id'), nullable=True, index=True)

    amount_paise = Column(Integer, nullable=False)
    transaction_type = Column(String(50), default="SCRATCH_REWARD_CREDIT", nullable=False)
    idempotency_key = Column(String(100), nullable=False, unique=True, index=True)

    created_at = Column(DateTime, default=get_indian_time, nullable=False)

    def __repr__(self):
        return f"<RewardLedger #{self.id} Mobile={self.mobile_number} Amt=₹{self.amount_paise/100:.2f}>"


class NotificationOutbox(BaseModel):
    """
    Durable notification queue/outbox for automated WhatsApp/SMS messages.
    Prevents single point of failure in in-process background tasks.
    """
    __tablename__ = 'notification_outbox'

    id = Column(Integer, primary_key=True, index=True)
    event_type = Column(String(50), nullable=False) # e.g. RECHARGE_SCRATCH_CARD
    destination_mobile = Column(String(20), nullable=False, index=True)
    brand = Column(String(50), default="Zynova Mobility", nullable=False)
    payload_json = Column(Text, nullable=False)

    status = Column(String(20), default="PENDING", nullable=False, index=True) # PENDING, SENT, FAILED
    retry_count = Column(Integer, default=0, nullable=False)
    error_message = Column(Text, nullable=True)

    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    processed_at = Column(DateTime, nullable=True)

    def __repr__(self):
        return f"<NotificationOutbox #{self.id} Event={self.event_type} Status={self.status}>"
