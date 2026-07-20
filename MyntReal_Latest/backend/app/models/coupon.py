"""
Coupon models for FastAPI - Package & Activation System
Preserves exact Flask coupon management functionality
"""

from sqlalchemy import Column, String, Integer, BigInteger, Boolean, DateTime, Date, Time, Text, Numeric, CheckConstraint
from sqlalchemy.orm import relationship
from sqlalchemy import ForeignKey
from app.models.base import BaseModel, TimestampMixin, get_indian_time

class Coupon(BaseModel):
    """
    Coupon model - LEGACY SCHEMA (matches actual database)
    Manages package assignments and activation tracking
    """
    __tablename__ = 'coupon'
    
    id = Column(BigInteger, primary_key=True)
    owner_id = Column(String(12), ForeignKey('user.id'), nullable=True)
    used_by = Column(String(12), ForeignKey('user.id'), nullable=True)  # DC Protocol: Tracks who used/activated this coupon
    coupon_type = Column(String(50), nullable=True)  # Maps to package_type in business logic
    status = Column(String(20), nullable=True)
    activated_at = Column(DateTime, nullable=True)  # Maps to activation_date in business logic
    assignment_status = Column(String(50), nullable=True)
    assignment_status_changed_date = Column(Date, nullable=True)
    assignment_status_changed_time = Column(Time, nullable=True)
    assignment_status_changed_at = Column(DateTime, nullable=True)
    
    # Alias properties for compatibility with existing code
    @property
    def package_type(self):
        """Alias for coupon_type"""
        return self.coupon_type
    
    @package_type.setter
    def package_type(self, value):
        self.coupon_type = value
    
    @property
    def activation_date(self):
        """Alias for activated_at"""
        return self.activated_at
    
    @activation_date.setter
    def activation_date(self, value):
        self.activated_at = value
    
    def __repr__(self):
        return f'<Coupon {self.id}: {self.coupon_type} - {self.status}>'

class EnhancedCoupon(BaseModel):
    """
    Enhanced coupon model - MATCHES ACTUAL DATABASE SCHEMA
    Database uses coupon_id (not id), coupon_value (not package_value)
    """
    __tablename__ = 'enhanced_coupon'
    
    # Match actual database primary key
    coupon_id = Column(Integer, primary_key=True)
    coupon_code = Column(String(50), unique=True, nullable=False)
    coupon_value = Column(Integer, nullable=False)  # DB has integer coupon_value
    
    # Dates
    issue_date = Column(DateTime, nullable=True)
    ev_expiry_date = Column(DateTime, nullable=True)
    training_expiry_date = Column(DateTime, nullable=True)
    
    # Status and ownership
    status = Column(String(20), nullable=True)
    user_id = Column(String(12), ForeignKey('user.id'), nullable=True)
    
    # Admin claim workflow
    admin_claim_status = Column(String(50), nullable=True)
    redemption_type = Column(String(50), nullable=True)
    redeemed_amount = Column(Numeric(15, 2), nullable=True)
    redemption_date = Column(DateTime, nullable=True)
    approval_date = Column(DateTime, nullable=True)
    approved_by = Column(String(12), nullable=True)
    
    # Claim details
    training_course_fee = Column(Numeric(15, 2), nullable=True)
    ev_model_redeemed = Column(String(100), nullable=True)
    
    # Metadata
    created_by = Column(String(12), nullable=True)
    updated_at = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)
    
    # Legacy tracking
    legacy_coupon_id = Column(Integer, nullable=True)
    legacy_status = Column(String(50), nullable=True)
    
    # Compatibility properties for backward compatibility with old code
    @property
    def id(self):
        """Alias for coupon_id - backward compatibility"""
        return self.coupon_id
    
    @property
    def package_value(self):
        """Alias for coupon_value - backward compatibility"""
        return self.coupon_value
    
    @package_value.setter
    def package_value(self, value):
        self.coupon_value = value
    
    @property
    def package_tier(self):
        """Derive package tier from coupon_value for backward compatibility"""
        if self.coupon_value >= 40000:
            return 'Platinum'
        elif self.coupon_value >= 20000:
            return 'Diamond'
        elif self.coupon_value >= 10000:
            return 'Star'
        else:
            return 'Loyal'
    
    @property
    def package_type(self):
        """Alias for package_tier - backward compatibility"""
        return self.package_tier
    
    @property
    def remaining_value(self):
        """Calculate remaining value from coupon_value and redeemed_amount"""
        if self.redeemed_amount:
            return float(self.coupon_value) - float(self.redeemed_amount)
        return float(self.coupon_value)
    
    def __repr__(self):
        return f'<EnhancedCoupon {self.coupon_code}: ₹{self.coupon_value} - {self.status}>'

class CouponActivationTracker(BaseModel, TimestampMixin):
    """
    Coupon activation deadline tracking model
    Preserves Flask Red Coupon enforcement system
    """
    __tablename__ = 'coupon_activation_tracker'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(String(12), ForeignKey('user.id'), nullable=False)
    coupon_id = Column(BigInteger, ForeignKey('coupon.id'), nullable=False)
    
    # Deadline management
    activation_deadline = Column(DateTime, nullable=False)
    deadline_extended = Column(Boolean, default=False, nullable=False)
    extension_count = Column(Integer, default=0, nullable=False)
    
    # Status tracking
    status = Column(String(20), default='Pending', nullable=False)  # 'Pending', 'Activated', 'Expired', 'Grace'
    activation_completed_at = Column(DateTime, nullable=True)
    
    # Red Coupon enforcement
    red_coupon_triggered = Column(Boolean, default=False, nullable=False)
    red_coupon_date = Column(DateTime, nullable=True)
    lockout_applied = Column(Boolean, default=False, nullable=False)
    
    # Grace period and appeals
    grace_period_granted = Column(Boolean, default=False, nullable=False)
    grace_period_expires = Column(DateTime, nullable=True)
    appeal_submitted = Column(Boolean, default=False, nullable=False)
    appeal_approved = Column(Boolean, default=False, nullable=False)
    
    # Administrative actions
    admin_notes = Column(Text, nullable=True)
    processed_by_id = Column(String(12), ForeignKey('user.id'), nullable=True)
    
    # Constraints
    __table_args__ = (
        CheckConstraint("status IN ('Pending', 'Activated', 'Expired', 'Grace')", name='valid_tracker_status'),
    )
    
    def __repr__(self):
        return f'<CouponActivationTracker User {self.user_id}: {self.status}>'

class PINPurchaseRequest(BaseModel):
    """
    PIN purchase request model for coupon acquisition
    Matches actual database schema with Flask columns
    """
    __tablename__ = 'pin_purchase_request'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(String(12), ForeignKey('user.id'), nullable=False)
    package_type = Column(String(20), nullable=False)  # Matches DB column name
    
    # Purchase details - Match actual DB columns
    package_value = Column(Integer, nullable=False)  # DB has integer package_value
    quantity = Column(Integer, default=1, nullable=False)  # DB has quantity
    total_amount = Column(Numeric(12, 2), nullable=False)
    
    # Payment tracking - Match actual DB columns
    payment_method = Column(String(30), nullable=True)
    transaction_id = Column(String(100), nullable=True)
    payment_amount = Column(Numeric(12, 2), nullable=True)  # DB has payment_amount
    payment_details = Column(Text, nullable=False)  # DB has payment_details - NOT NULL
    payment_screenshot_path = Column(String(255), nullable=True)
    
    # Request lifecycle
    status = Column(String(20), default='Pending', nullable=False)  # 'Pending', 'Approved', 'Rejected', 'Fulfilled'
    request_date = Column(DateTime, default=get_indian_time, nullable=False)
    
    # Approval workflow - Match actual DB columns
    superadmin_approved_date = Column(DateTime, nullable=True)
    finance_validated_date = Column(DateTime, nullable=True)
    completed_date = Column(DateTime, nullable=True)
    superadmin_approved_by = Column(String(12), nullable=True)
    finance_validated_by = Column(String(12), nullable=True)
    
    # Rejection tracking
    rejection_reason = Column(Text, nullable=True)
    rejected_by = Column(String(12), nullable=True)
    rejected_date = Column(DateTime, nullable=True)
    
    # Administrative notes
    superadmin_notes = Column(Text, nullable=True)
    finance_admin_notes = Column(Text, nullable=True)
    internal_reference = Column(String(100), nullable=True)
    payment_validation_id = Column(Integer, nullable=True)
    
    # DC Protocol: Semantic file naming (Nov 29, 2025)
    download_filename = Column(String(255), nullable=True)  # Semantic download filename
    uses_new_naming = Column(Boolean, default=False, nullable=False)  # Flag for new naming convention
    
    def __repr__(self):
        return f'<PINPurchaseRequest {self.user_id}: {self.package_type} x{self.quantity}>'