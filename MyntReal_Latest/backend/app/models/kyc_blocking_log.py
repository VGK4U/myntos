"""
KYC Blocking Log Model
Tracks users who were skipped during wallet sync due to KYC issues
"""

from sqlalchemy import Column, String, Integer, DateTime, Text, Numeric
from sqlalchemy import ForeignKey
from app.models.base import BaseModel, get_indian_time

class KYCBlockingLog(BaseModel):
    """
    Log of users blocked from wallet transfer due to KYC issues
    Used for admin reporting and audit trail
    """
    __tablename__ = 'kyc_blocking_log'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(String(12), ForeignKey('user.id'), nullable=False)
    
    # Blocking Details
    blocked_at = Column(DateTime, default=get_indian_time, nullable=False)
    earning_wallet_amount = Column(Numeric(12, 2), nullable=False)  # Amount that was blocked
    kyc_status = Column(String(30), nullable=False)  # User's KYC status at time of blocking
    reason = Column(Text, nullable=False)  # Why transfer was blocked
    
    # Sync Info
    sync_job_timestamp = Column(DateTime, nullable=False)  # Which daily sync job created this log
    
    def __repr__(self):
        return f'<KYCBlockingLog {self.user_id}: ₹{self.earning_wallet_amount} blocked - {self.kyc_status}>'


class WalletSyncLog(BaseModel):
    """
    Log of successful wallet sync operations
    Tracks transfers from earning to withdrawable wallet
    """
    __tablename__ = 'wallet_sync_log'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(String(12), ForeignKey('user.id'), nullable=False)
    
    # Transfer Details
    synced_at = Column(DateTime, default=get_indian_time, nullable=False)
    amount_transferred = Column(Numeric(12, 2), nullable=False)
    earning_wallet_before = Column(Numeric(12, 2), nullable=False)
    earning_wallet_after = Column(Numeric(12, 2), nullable=False)
    withdrawable_wallet_before = Column(Numeric(12, 2), nullable=False)
    withdrawable_wallet_after = Column(Numeric(12, 2), nullable=False)
    
    # Status Info
    kyc_status = Column(String(30), nullable=False)
    sync_job_timestamp = Column(DateTime, nullable=False)
    
    def __repr__(self):
        return f'<WalletSyncLog {self.user_id}: ₹{self.amount_transferred} transferred>'
