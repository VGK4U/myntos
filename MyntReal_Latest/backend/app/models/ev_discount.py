"""
EV Discount Coupon System Models
Handles Electric Vehicle purchases with coupon discount redemption
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, Text, Boolean, ForeignKey, Numeric, Date, CheckConstraint
from sqlalchemy.orm import relationship
from datetime import datetime
from app.models.base import Base


class EV(Base):
    """
    Electric Vehicle Models and Inventory
    Stores available EV models with pricing and discount rates
    """
    __tablename__ = "ev"
    
    id = Column(Integer, primary_key=True, index=True)
    model = Column(String(200), nullable=False)
    price = Column(Integer, nullable=False)
    is_available = Column(Boolean, default=True, nullable=False)
    discount_rate = Column(Integer, default=0, nullable=False)  # Percentage discount for Star and Loyal coupons
    
    # Additional details
    manufacturer = Column(String(100))
    category = Column(String(50))  # Two-wheeler, Three-wheeler, Four-wheeler
    specifications = Column(Text)
    image_url = Column(String(500))
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    purchases = relationship("Purchase", back_populates="ev")
    
    def __repr__(self):
        return f'<EV {self.model}: ₹{self.price} (Available: {self.is_available})>'


class Purchase(Base):
    """
    EV Purchase Records
    Tracks user EV purchases with coupon redemption
    """
    __tablename__ = "purchase"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(20), ForeignKey('user.id'), nullable=False, index=True)
    ev_id = Column(Integer, ForeignKey('ev.id'), nullable=False, index=True)
    
    # Purchase details
    amount_redeemed = Column(Integer, nullable=False)  # Coupon value used
    original_price = Column(Integer, nullable=False)
    discount_amount = Column(Integer, nullable=False, default=0)
    final_price = Column(Integer, nullable=False)
    
    # Coupon details
    enhanced_coupon_id = Column(Integer)  # Reference to EnhancedCoupon
    coupon_code = Column(String(50))
    
    # Status tracking
    purchase_date = Column(Date, default=datetime.utcnow().date, nullable=False)
    status = Column(String(20), default='Pending', nullable=False)  # Pending, Approved, Completed, Cancelled, Rejected
    
    # Admin verification
    verified_by_admin_id = Column(String(20))
    verification_date = Column(DateTime)
    admin_notes = Column(Text)
    rejection_reason = Column(Text)
    
    # Delivery tracking
    delivery_status = Column(String(30))  # Ordered, Dispatched, Delivered, Cancelled
    delivery_date = Column(DateTime)
    delivery_address = Column(Text)
    
    # Relationships
    user = relationship("User", backref="ev_purchases")
    ev = relationship("EV", back_populates="purchases")
    
    # Constraints
    __table_args__ = (
        CheckConstraint("status IN ('Pending', 'Approved', 'Completed', 'Cancelled', 'Rejected')", name='valid_purchase_status'),
    )
    
    def __repr__(self):
        return f'<Purchase User:{self.user_id} EV:{self.ev_id} Amount:₹{self.amount_redeemed} Status:{self.status}>'


class CouponBenefit(Base):
    """
    Coupon Benefit Tracking
    Records benefits applied through EV purchase coupons
    """
    __tablename__ = "coupon_benefit"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Associated records
    ev_coupon_id = Column(Integer, nullable=False, index=True)  # EnhancedCoupon ID
    user_id = Column(String(20), ForeignKey('user.id'), nullable=False, index=True)
    purchase_id = Column(Integer, ForeignKey('purchase.id'), index=True)
    
    # Benefit details
    benefit_type = Column(String(50), nullable=False)  # EV_Discount, RoyalEV_Bonus, Training_Cashback, Referral_Opportunity, etc.
    benefit_description = Column(Text, nullable=False)
    
    # Financial tracking
    original_amount = Column(Numeric(12, 2))  # Original price/amount
    discount_amount = Column(Numeric(12, 2))  # Discount applied
    final_amount = Column(Numeric(12, 2))  # Final amount after discount
    cashback_amount = Column(Numeric(12, 2))  # Cashback credited
    
    # Status tracking
    status = Column(String(20), default='Applied', nullable=False)  # Applied, Verified, Reversed
    applied_date = Column(DateTime, default=datetime.utcnow, nullable=False)
    applied_by = Column(String(20))  # Admin who applied benefit
    
    # Verification
    verified_by = Column(String(20))
    verification_date = Column(DateTime)
    
    # Additional info
    notes = Column(Text)
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id], backref="received_coupon_benefits")
    purchase = relationship("Purchase", backref="coupon_benefits")
    
    # Constraints
    __table_args__ = (
        CheckConstraint("benefit_type IN ('EV_Discount', 'RoyalEV_Bonus', 'Training_Cashback', 'Referral_Opportunity', 'Franchise_Referral', 'Insurance_Referral', 'Fleet_Referral')", name='valid_benefit_type'),
        CheckConstraint("status IN ('Applied', 'Verified', 'Reversed')", name='valid_benefit_status'),
        CheckConstraint("discount_amount >= 0", name='non_negative_discount'),
        CheckConstraint("cashback_amount >= 0", name='non_negative_cashback'),
    )
    
    def __repr__(self):
        return f'<CouponBenefit Coupon:{self.ev_coupon_id} Type:{self.benefit_type} User:{self.user_id} Amount:₹{self.discount_amount}>'


class EVRedemptionRequest(Base):
    """
    EV Coupon Redemption Requests
    Tracks user requests to redeem coupons for EV purchases
    """
    __tablename__ = "ev_redemption_request"
    
    id = Column(Integer, primary_key=True, index=True)
    request_id = Column(String(50), unique=True, nullable=False, index=True)
    
    # User and coupon details
    user_id = Column(String(20), ForeignKey('user.id'), nullable=False, index=True)
    enhanced_coupon_id = Column(Integer, nullable=False, index=True)
    coupon_code = Column(String(50), nullable=False)
    
    # Redemption details
    ev_model = Column(String(200), nullable=False)
    redemption_type = Column(String(20), default='ev', nullable=False)  # 'ev' or 'training'
    redemption_amount = Column(Numeric(12, 2), nullable=False)
    
    # For training redemptions
    course_name = Column(String(200))
    course_fee = Column(Numeric(12, 2))
    training_benefit_amount = Column(Numeric(12, 2))
    
    # Status tracking
    status = Column(String(30), default='Pending', nullable=False)  # Pending, Approved, Rejected, Completed
    request_date = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Admin processing
    admin_claim_status = Column(String(20), default='pending')  # pending, approved, rejected
    processed_by_admin_id = Column(String(20))
    processed_date = Column(DateTime)
    admin_notes = Column(Text)
    rejection_reason = Column(Text)
    
    # Relationships
    user = relationship("User", backref="ev_redemption_requests")
    
    # Constraints
    __table_args__ = (
        CheckConstraint("redemption_type IN ('ev', 'training')", name='valid_redemption_type'),
        CheckConstraint("status IN ('Pending', 'Approved', 'Rejected', 'Completed')", name='valid_redemption_status'),
        CheckConstraint("admin_claim_status IN ('pending', 'approved', 'rejected')", name='valid_admin_claim_status'),
    )
    
    def __repr__(self):
        return f'<EVRedemptionRequest {self.request_id}: User {self.user_id} - {self.status}>'


class ReferralIncome(Base):
    """
    Referral Income Tracking for EV/Insurance/Franchise/Fleet Sales
    Tracks commission earned when downline members make purchases
    """
    __tablename__ = "referral_income"
    
    id = Column(Integer, primary_key=True, index=True)
    referral_code = Column(String(50), unique=True, nullable=False, index=True)
    
    # Earner and purchaser
    earner_user_id = Column(String(20), ForeignKey('user.id'), nullable=False, index=True)
    purchaser_user_id = Column(String(20), ForeignKey('user.id'), nullable=False, index=True)
    
    # Referral details
    referral_type = Column(String(30), nullable=False)  # EV, Insurance, Franchise, Fleet
    purchase_amount = Column(Numeric(12, 2), nullable=False)
    commission_rate = Column(Numeric(5, 2), nullable=False)  # Percentage
    commission_amount = Column(Numeric(12, 2), nullable=False)
    
    # Related records
    purchase_id = Column(Integer, ForeignKey('purchase.id'), nullable=True)
    benefit_id = Column(Integer, ForeignKey('coupon_benefit.id'), nullable=True)
    
    # Status
    status = Column(String(20), default='Pending', nullable=False)  # Pending, Approved, Paid, Reversed
    earned_date = Column(DateTime, default=datetime.utcnow, nullable=False)
    approved_date = Column(DateTime)
    paid_date = Column(DateTime)
    
    # Admin tracking
    approved_by = Column(String(20))
    notes = Column(Text)
    
    # Relationships
    earner = relationship("User", foreign_keys=[earner_user_id], backref="referral_incomes_earned")
    purchaser = relationship("User", foreign_keys=[purchaser_user_id], backref="referral_incomes_generated")
    
    # Constraints
    __table_args__ = (
        CheckConstraint("referral_type IN ('EV', 'Insurance', 'Franchise', 'Fleet')", name='valid_referral_type'),
        CheckConstraint("status IN ('Pending', 'Approved', 'Paid', 'Reversed')", name='valid_referral_status'),
    )
    
    def __repr__(self):
        return f'<ReferralIncome {self.referral_code}: {self.earner_user_id} earns ₹{self.commission_amount} from {self.purchaser_user_id}>'


class FranchisePurchase(Base):
    """
    Franchise EV Purchase Records
    Tracks bulk/franchise EV purchases with higher commission rates
    """
    __tablename__ = "franchise_purchase"
    
    id = Column(Integer, primary_key=True, index=True)
    franchise_code = Column(String(50), unique=True, nullable=False, index=True)
    
    # Franchise details
    franchisee_user_id = Column(String(20), ForeignKey('user.id'), nullable=False, index=True)
    franchise_name = Column(String(200), nullable=False)
    gst_number = Column(String(50))
    
    # Purchase details
    vehicle_count = Column(Integer, nullable=False)
    vehicle_model = Column(String(200), nullable=False)
    unit_price = Column(Numeric(12, 2), nullable=False)
    total_amount = Column(Numeric(15, 2), nullable=False)
    discount_amount = Column(Numeric(15, 2), default=0)
    final_amount = Column(Numeric(15, 2), nullable=False)
    
    # Commission tracking
    commission_tier = Column(String(20))  # Tier1, Tier2, Tier3 based on quantity
    commission_rate = Column(Numeric(5, 2))
    total_commission = Column(Numeric(15, 2))
    
    # Status
    status = Column(String(30), default='Pending', nullable=False)
    order_date = Column(DateTime, default=datetime.utcnow, nullable=False)
    approval_date = Column(DateTime)
    delivery_date = Column(DateTime)
    
    # Relationships
    franchisee = relationship("User", backref="franchise_purchases")
    
    # Constraints
    __table_args__ = (
        CheckConstraint("status IN ('Pending', 'Approved', 'Processing', 'Delivered', 'Cancelled')", name='valid_franchise_status'),
        CheckConstraint("vehicle_count > 0", name='positive_vehicle_count'),
    )
    
    def __repr__(self):
        return f'<FranchisePurchase {self.franchise_code}: {self.franchise_name} - {self.vehicle_count} units>'


class InsurancePolicy(Base):
    """
    Vehicle Insurance Policies
    Tracks insurance sales and referral commissions
    """
    __tablename__ = "insurance_policy"
    
    id = Column(Integer, primary_key=True, index=True)
    policy_number = Column(String(50), unique=True, nullable=False, index=True)
    
    # Policy holder
    user_id = Column(String(20), ForeignKey('user.id'), nullable=False, index=True)
    vehicle_registration = Column(String(50), nullable=False)
    
    # Insurance details
    insurance_provider = Column(String(100), nullable=False)
    policy_type = Column(String(50), nullable=False)  # Comprehensive, Third-Party, etc.
    coverage_amount = Column(Numeric(15, 2), nullable=False)
    premium_amount = Column(Numeric(12, 2), nullable=False)
    
    # Referral commission
    referred_by_user_id = Column(String(20), ForeignKey('user.id'), nullable=True, index=True)
    commission_rate = Column(Numeric(5, 2), default=5.0)  # 5% default
    commission_amount = Column(Numeric(12, 2))
    
    # Policy dates
    policy_start_date = Column(Date, nullable=False)
    policy_end_date = Column(Date, nullable=False)
    issue_date = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Status
    status = Column(String(20), default='Active', nullable=False)
    
    # Relationships
    policy_holder = relationship("User", foreign_keys=[user_id], backref="insurance_policies")
    referrer = relationship("User", foreign_keys=[referred_by_user_id], backref="insurance_referrals")
    
    # Constraints
    __table_args__ = (
        CheckConstraint("status IN ('Active', 'Expired', 'Cancelled', 'Renewed')", name='valid_insurance_status'),
    )
    
    def __repr__(self):
        return f'<InsurancePolicy {self.policy_number}: {self.user_id} - ₹{self.premium_amount}>'


class FleetOrder(Base):
    """
    Fleet/Bulk EV Orders
    Enterprise-level bulk vehicle purchases with tier-based commissions
    """
    __tablename__ = "fleet_order"
    
    id = Column(Integer, primary_key=True, index=True)
    fleet_order_number = Column(String(50), unique=True, nullable=False, index=True)
    
    # Corporate buyer
    company_name = Column(String(200), nullable=False)
    contact_person_user_id = Column(String(20), ForeignKey('user.id'), nullable=False, index=True)
    gst_number = Column(String(50), nullable=False)
    
    # Fleet details
    vehicle_model = Column(String(200), nullable=False)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Numeric(12, 2), nullable=False)
    total_order_value = Column(Numeric(15, 2), nullable=False)
    negotiated_discount = Column(Numeric(15, 2), default=0)
    final_order_value = Column(Numeric(15, 2), nullable=False)
    
    # Commission structure
    tier_level = Column(String(20))  # Small(1-10), Medium(11-50), Large(51+)
    base_commission_rate = Column(Numeric(5, 2))
    bonus_commission_rate = Column(Numeric(5, 2))  # Extra for large orders
    total_commission_pool = Column(Numeric(15, 2))
    
    # Referral chain
    primary_referrer_id = Column(String(20), ForeignKey('user.id'), nullable=True)
    secondary_referrer_id = Column(String(20), ForeignKey('user.id'), nullable=True)
    
    # Status & dates
    status = Column(String(30), default='Pending', nullable=False)
    order_date = Column(DateTime, default=datetime.utcnow, nullable=False)
    expected_delivery_date = Column(Date)
    
    # Relationships
    contact_person = relationship("User", foreign_keys=[contact_person_user_id], backref="fleet_orders")
    primary_referrer = relationship("User", foreign_keys=[primary_referrer_id], backref="primary_fleet_referrals")
    secondary_referrer = relationship("User", foreign_keys=[secondary_referrer_id], backref="secondary_fleet_referrals")
    
    # Constraints
    __table_args__ = (
        CheckConstraint("status IN ('Pending', 'Approved', 'Production', 'Delivered', 'Cancelled')", name='valid_fleet_status'),
        CheckConstraint("quantity > 0", name='positive_fleet_quantity'),
    )
    
    def __repr__(self):
        return f'<FleetOrder {self.fleet_order_number}: {self.company_name} - {self.quantity} units>'
