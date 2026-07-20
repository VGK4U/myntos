"""
Coupon Transfer Model for FastAPI
Tracks all coupon transfers with approval workflows and audit logging
"""

from sqlalchemy import Column, String, Integer, Boolean, DateTime, Text, CheckConstraint
from sqlalchemy.orm import relationship
from sqlalchemy import ForeignKey
from app.models.base import BaseModel, TimestampMixin, get_indian_time

class CouponTransfer(BaseModel, TimestampMixin):
    """
    Coupon Transfer model with approval workflow
    Supports:
    - User-to-user transfers (instant, no approval)
    - Admin transfers (requires Super Admin approval)
    """
    __tablename__ = 'coupon_transfer'
    
    id = Column(Integer, primary_key=True)
    
    # Transfer Details
    from_user_id = Column(String(12), ForeignKey('user.id'), nullable=False)
    to_user_id = Column(String(12), ForeignKey('user.id'), nullable=False)
    coupon_id = Column(Integer, ForeignKey('coupon.id'), nullable=True)  # For legacy coupons
    enhanced_coupon_id = Column(Integer, ForeignKey('enhanced_coupon.coupon_id'), nullable=True)  # For enhanced coupons
    
    # Package Information
    package_type = Column(String(20), nullable=False)  # 'Platinum', 'Diamond', 'Blue', 'Loyal'
    
    # Transfer Type and Workflow
    transfer_type = Column(String(20), nullable=False)  # 'user_to_user', 'admin_transfer'
    initiated_by_id = Column(String(12), ForeignKey('user.id'), nullable=False)  # Who initiated the transfer
    
    # Status and Approval
    status = Column(String(20), default='Pending', nullable=False)  # 'Pending', 'Approved', 'Rejected', 'Completed'
    requires_approval = Column(Boolean, default=False, nullable=False)  # True for admin transfers
    
    # Approval Workflow (for admin-initiated transfers)
    approved_by_id = Column(String(12), ForeignKey('user.id'), nullable=True)  # Super Admin who approved
    approved_at = Column(DateTime, nullable=True)
    approval_notes = Column(Text, nullable=True)
    
    # Rejection Tracking
    rejected_by_id = Column(String(12), ForeignKey('user.id'), nullable=True)
    rejected_at = Column(DateTime, nullable=True)
    rejection_reason = Column(Text, nullable=True)
    
    # Transfer Execution
    transfer_date = Column(DateTime, default=get_indian_time, nullable=False)  # When transfer was initiated
    completed_at = Column(DateTime, nullable=True)  # When transfer was actually completed
    
    # Audit Trail
    transfer_reason = Column(Text, nullable=True)  # Why was this transfer made
    admin_notes = Column(Text, nullable=True)  # Additional notes by admins
    ip_address = Column(String(45), nullable=True)  # IP from which transfer was initiated
    
    # Constraints
    __table_args__ = (
        CheckConstraint("transfer_type IN ('user_to_user', 'admin_transfer')", name='valid_transfer_type'),
        CheckConstraint("status IN ('Pending', 'Approved', 'Rejected', 'Completed')", name='valid_transfer_status'),
        CheckConstraint("package_type IN ('Platinum', 'Diamond', 'Blue', 'Loyal', 'Star')", name='valid_package_type_transfer'),
    )
    
    def __repr__(self):
        return f'<CouponTransfer {self.id}: {self.from_user_id} → {self.to_user_id} ({self.package_type}) - {self.status}>'
