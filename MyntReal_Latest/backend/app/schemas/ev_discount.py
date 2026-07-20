"""
EV Discount Coupon Schemas
Pydantic models for EV purchase and coupon redemption
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, date
from decimal import Decimal


# ===== EV Model Schemas =====

class EVBase(BaseModel):
    model: str
    price: int
    is_available: bool = True
    discount_rate: int = 0
    manufacturer: Optional[str] = None
    category: Optional[str] = None
    specifications: Optional[str] = None
    image_url: Optional[str] = None


class EVCreate(EVBase):
    pass


class EVResponse(EVBase):
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True


# ===== Purchase Schemas =====

class PurchaseCreate(BaseModel):
    ev_id: int
    coupon_code: str
    delivery_address: Optional[str] = None


class PurchaseResponse(BaseModel):
    id: int
    user_id: str
    ev_id: int
    amount_redeemed: int
    original_price: int
    discount_amount: int
    final_price: int
    coupon_code: Optional[str]
    purchase_date: date
    status: str
    delivery_status: Optional[str]
    admin_notes: Optional[str]
    
    class Config:
        from_attributes = True


# ===== Redemption Schemas =====

class EVRedemptionCreate(BaseModel):
    coupon_code: str
    ev_model: str
    redemption_type: str = 'ev'  # 'ev' or 'training'
    course_name: Optional[str] = None
    course_fee: Optional[Decimal] = None


class EVRedemptionResponse(BaseModel):
    id: int
    request_id: str
    user_id: str
    coupon_code: str
    ev_model: str
    redemption_type: str
    redemption_amount: Decimal
    status: str
    admin_claim_status: str
    request_date: datetime
    admin_notes: Optional[str]
    
    class Config:
        from_attributes = True


class RedemptionApproval(BaseModel):
    action: str  # 'approve' or 'reject'
    admin_notes: Optional[str] = None
    rejection_reason: Optional[str] = None


# ===== Coupon Benefit Schemas =====

class CouponBenefitCreate(BaseModel):
    ev_coupon_id: int
    user_id: str
    purchase_id: Optional[int] = None
    benefit_type: str
    benefit_description: str
    original_amount: Optional[Decimal] = None
    discount_amount: Optional[Decimal] = None
    final_amount: Optional[Decimal] = None


class CouponBenefitResponse(BaseModel):
    id: int
    ev_coupon_id: int
    user_id: str
    benefit_type: str
    benefit_description: str
    discount_amount: Optional[Decimal]
    status: str
    applied_date: datetime
    
    class Config:
        from_attributes = True


# ===== Training Course Schemas =====

class TrainingCourseCreate(BaseModel):
    course_code: str
    course_name: str
    course_fee: Decimal
    course_description: Optional[str] = None
    duration: Optional[str] = None
    mode: Optional[str] = None
    category: Optional[str] = None
    discount_eligible: bool = True
    max_discount_percentage: int = 20


class TrainingCourseResponse(BaseModel):
    id: int
    course_code: str
    course_name: str
    course_fee: Decimal
    discount_eligible: bool
    max_discount_percentage: int
    is_active: bool
    
    class Config:
        from_attributes = True


# ===== User Coupon Info =====

class UserCouponInfo(BaseModel):
    coupon_code: str
    coupon_value: int
    status: str
    category: str
    valid_until: Optional[datetime]
    can_redeem_ev: bool
    can_redeem_training: bool
    ev_expiry_date: Optional[datetime]
    training_expiry_date: Optional[datetime]


# ===== Dashboard Schemas =====

class EVDashboardStats(BaseModel):
    total_ev_models: int
    available_ev_models: int
    total_purchases: int
    pending_redemptions: int
    total_discount_given: Decimal


class UserEVStats(BaseModel):
    available_coupons: int
    redeemed_coupons: int
    total_discount_received: Decimal
    pending_redemptions: int
