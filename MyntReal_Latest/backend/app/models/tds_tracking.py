"""
TDS Tracking Model - DC Protocol
Tracks TDS payable to government on behalf of MNR members
Auto-created when withdrawal is completed with tds_amount > 0

TDSUserStatus: Lightweight user-level status tracking for TDS filing
Statuses: Pending (default), Completed (filed with govt), Exception (not subject to TDS)
"""

from sqlalchemy import Column, String, Integer, DateTime, Text, Numeric, ForeignKey
from app.models.base import BaseModel, get_indian_time


class TDSTracking(BaseModel):
    __tablename__ = 'tds_tracking'

    id = Column(Integer, primary_key=True)
    withdrawal_request_id = Column(Integer, ForeignKey('withdrawal_request.id'), nullable=False)
    user_id = Column(String(20), ForeignKey('user.id'), nullable=False)
    mnr_id = Column(String(20), nullable=True)
    tds_amount = Column(Numeric(12, 2), nullable=False)
    withdrawal_amount = Column(Numeric(12, 2), nullable=False)
    payment_status = Column(String(20), default='Pending', nullable=False)
    paid_at = Column(DateTime, nullable=True)
    paid_by = Column(String(50), nullable=True)
    government_reference = Column(String(255), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time, nullable=False)

    def __repr__(self):
        return f'<TDSTracking {self.id}: User {self.user_id} - ₹{self.tds_amount} - {self.payment_status}>'


class TDSUserStatus(BaseModel):
    __tablename__ = 'tds_user_status'

    id = Column(Integer, primary_key=True)
    user_id = Column(String(20), ForeignKey('user.id'), nullable=False, unique=True, index=True)
    status = Column(String(20), default='Pending', nullable=False)
    marked_by = Column(String(50), nullable=True)
    marked_at = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time, nullable=False)

    def __repr__(self):
        return f'<TDSUserStatus {self.user_id}: {self.status}>'
