from sqlalchemy import Column, Integer, String, DateTime, Date, ForeignKey, Text, Float, Boolean, Numeric
from sqlalchemy.orm import Session, relationship
from app.models.base import Base, get_indian_time

_ACTIVE_STATUSES = ('Pending', 'Admin Verified', 'Super Admin Approved', 'On Hold')

def get_active_withdrawal(db: Session, user_id: str):
    """
    DC_WITHDRAW_001: Return the first in-flight WithdrawalRequest for user_id,
    or None if no active withdrawal exists.
    Reuse this at every creation site to prevent duplicates.
    Active = any status that is not yet Completed/Rejected/Cancelled.
    """
    from app.models.withdrawal import WithdrawalRequest
    return (
        db.query(WithdrawalRequest)
        .filter(
            WithdrawalRequest.user_id == user_id,
            WithdrawalRequest.status.in_(_ACTIVE_STATUSES),
        )
        .first()
    )

class TransferQueue(Base):
    """
    Transfer Queue for WVV Workflow - Stage 2 to Stage 3 transition
    Created when Super Admin verifies income, processed by Finance Admin
    """
    __tablename__ = 'transfer_queue'
    
    id = Column(Integer, primary_key=True)
    pending_income_id = Column(Integer, ForeignKey('pending_income.id'), nullable=False, unique=True)
    user_id = Column(String(12), ForeignKey('user.id'), nullable=False)
    income_type = Column(String(50), nullable=False)
    net_amount = Column(Numeric(10, 2), nullable=False)
    withdrawal_wallet_amount = Column(Numeric(10, 2), nullable=False)
    upgrade_wallet_amount = Column(Numeric(10, 2), nullable=False)
    business_date = Column(Date, nullable=False)
    status = Column(String(30), default='Awaiting Finance', nullable=False)  # Awaiting Finance, Completed, Cancelled
    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    created_by_id = Column(String(12), ForeignKey('user.id'), nullable=True)  # Super Admin who created
    processed_at = Column(DateTime, nullable=True)
    processed_by_id = Column(String(12), ForeignKey('user.id'), nullable=True)  # Finance Admin who processed
    notes = Column(Text, nullable=True)
    
    # Relationships
    pending_income = relationship('PendingIncome', foreign_keys=[pending_income_id], backref='transfer_queue_entry')
    user = relationship('User', foreign_keys=[user_id], backref='transfer_queue_items')
    created_by = relationship('User', foreign_keys=[created_by_id])
    processed_by = relationship('User', foreign_keys=[processed_by_id])
    
    def __repr__(self):
        return f'<TransferQueue {self.id}: User {self.user_id} - ₹{self.net_amount} - {self.status}>'

class WithdrawalRequest(Base):
    __tablename__ = 'withdrawal_request'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(String(12), ForeignKey('user.id'), nullable=False)
    withdrawal_amount = Column(Integer, nullable=False)
    admin_charges = Column(Integer, nullable=False)
    tds_amount = Column(Integer, nullable=False)
    final_payout = Column(Integer, nullable=False)
    request_date = Column(Date, default=lambda: get_indian_time().date(), nullable=False)
    status = Column(String(30), default='Pending', nullable=False)
    is_auto_generated = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    processed_at = Column(DateTime, nullable=True)
    bulk_batch_id = Column(Integer, ForeignKey('bulk_withdrawal_batch.id'), nullable=True)
    payment_reference = Column(String(255), nullable=True)
    paid_date = Column(DateTime, nullable=True)
    bank_name = Column(String(255), nullable=True)
    account_number = Column(String(255), nullable=True)
    ifsc_code = Column(String(255), nullable=True)
    account_holder_name = Column(String(255), nullable=True)
    
    user = relationship('User', foreign_keys=[user_id], backref='withdrawal_requests')
    batch = relationship('BulkWithdrawalBatch', foreign_keys=[bulk_batch_id], backref='requests')
    
    def __repr__(self):
        return f'<WithdrawalRequest {self.id}: User {self.user_id} - ₹{self.withdrawal_amount}>'

class BulkWithdrawalBatch(Base):
    __tablename__ = 'bulk_withdrawal_batch'
    
    id = Column(Integer, primary_key=True)
    batch_name = Column(String(255), nullable=False)
    created_by = Column(String(12), ForeignKey('user.id'), nullable=False)
    total_requests = Column(Integer, nullable=False, default=0)
    total_amount = Column(Float, nullable=False, default=0.0)
    total_payout = Column(Float, nullable=False, default=0.0)
    status = Column(String(30), default='Draft', nullable=False)
    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    submitted_at = Column(DateTime, nullable=True)
    approved_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    admin_notes = Column(Text, nullable=True)
    approval_notes = Column(Text, nullable=True)
    rejection_reason = Column(Text, nullable=True)
    assigned_to = Column(String(12), ForeignKey('user.id'), nullable=True)
    
    creator = relationship('User', foreign_keys=[created_by], backref='created_batches')
    assignee = relationship('User', foreign_keys=[assigned_to], backref='assigned_batches')
    
    def __repr__(self):
        return f'<BulkWithdrawalBatch {self.id}: {self.batch_name} - {self.status}>'
