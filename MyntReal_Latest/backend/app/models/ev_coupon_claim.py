"""
EV Coupon Claim System
Tracks user claims for EV discount benefits
"""

from sqlalchemy import Column, String, Float, DateTime, Text, Integer, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from app.models.base import BaseModel
from datetime import datetime
import pytz

def get_indian_time():
    """Get current datetime in Indian Standard Time"""
    indian_tz = pytz.timezone('Asia/Kolkata')
    return datetime.now(indian_tz).replace(tzinfo=None)

class EVCouponClaim(BaseModel):
    """
    EV Coupon Claim Table
    Tracks user claims for EV purchase discounts
    
    Business Rules:
    - Platinum: ₹15,000 x 1 claim per coupon
    - Diamond: ₹7,500 x 2 claims per coupon
    - Requires: Active package + KYC approved
    """
    __tablename__ = 'ev_coupon_claim'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # User & Coupon Reference
    user_id = Column(String(12), ForeignKey('user.id'), nullable=False)
    coupon_id = Column(Integer, ForeignKey('coupon.id'), nullable=True)  # Track which coupon used
    
    # EV Model Selection
    ev_model_id = Column(Integer, ForeignKey('ev_model.id'), nullable=False)
    
    # Customer Details
    customer_name = Column(String(100), nullable=False)
    customer_contact = Column(String(15), nullable=False)
    delivery_address = Column(Text, nullable=False)
    
    # Dealer Information
    dealer_showroom = Column(String(200), nullable=True)
    dealer_contact = Column(String(15), nullable=True)
    
    # Financial Details
    discount_amount = Column(Float, nullable=False)  # Actual discount applied (₹15k or ₹7.5k)
    model_price_at_claim = Column(Float, nullable=False)  # Model price when claim was made
    
    # Payment & Proof
    payment_proof_url = Column(Text, nullable=True)  # URL to uploaded payment proof
    payment_reference = Column(String(100), nullable=True)
    
    # Claim Status Workflow
    # Pending → Admin Approved → Dealer Confirmed → Delivered
    claim_status = Column(String(30), default='Pending', nullable=False)
    
    # Admin Actions
    created_by_admin = Column(Boolean, default=False, nullable=False)  # True if admin/super admin created
    created_by_user_id = Column(String(12), ForeignKey('user.id'), nullable=True)  # Who created the claim
    
    approved_by_user_id = Column(String(12), ForeignKey('user.id'), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    
    # Dealer Assignment
    assigned_to_dealer_at = Column(DateTime, nullable=True)
    dealer_confirmed_at = Column(DateTime, nullable=True)
    
    # Delivery
    delivered_at = Column(DateTime, nullable=True)
    delivery_notes = Column(Text, nullable=True)
    
    # Rejection
    rejection_reason = Column(Text, nullable=True)
    rejected_at = Column(DateTime, nullable=True)
    rejected_by_user_id = Column(String(12), ForeignKey('user.id'), nullable=True)
    
    # Package Info at Time of Claim (for audit)
    package_at_claim = Column(String(20), nullable=True)  # Platinum, Diamond, etc.
    claim_number_for_coupon = Column(Integer, default=1, nullable=False)  # 1st or 2nd claim for this coupon
    
    # Timestamps
    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time, nullable=False)
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id], backref="ev_claims")
    ev_model = relationship("EVModel", backref="claims")
    created_by = relationship("User", foreign_keys=[created_by_user_id])
    approved_by = relationship("User", foreign_keys=[approved_by_user_id])
    rejected_by = relationship("User", foreign_keys=[rejected_by_user_id])
    
    def __repr__(self):
        return f"<EVCouponClaim {self.id} - {self.user_id} - {self.claim_status}>"
