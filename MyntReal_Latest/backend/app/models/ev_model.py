"""
EV Model Configuration - Super Admin Created, RVZ Approved
Stores EV scooter models with variants, pricing and discount configuration
"""

from sqlalchemy import Column, String, Float, Boolean, Text, Integer, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.models.base import BaseModel
from datetime import datetime
import pytz

def get_indian_time():
    """Get current datetime in Indian Standard Time"""
    indian_tz = pytz.timezone('Asia/Kolkata')
    return datetime.now(indian_tz).replace(tzinfo=None)

class EVModel(BaseModel):
    """
    EV Model Configuration Table
    Super Admin creates/edits → RVZ approves → Users see approved models
    """
    __tablename__ = 'ev_model'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Model Information
    model_name = Column(String(100), nullable=False)  # e.g., "Royal EV K9"
    variant_name = Column(String(100), nullable=True)  # e.g., "Pro", "Standard", "LX"
    manufacturer = Column(String(100), default='Royal EV', nullable=False)
    base_price = Column(Float, nullable=False)  # Base price of the model
    
    # Discount Configuration
    max_discount_percentage = Column(Float, nullable=False)  # e.g., 100 or 5
    coupon_benefit_enabled = Column(Boolean, default=True, nullable=False)
    
    # MyntReal Incentive System - Exclusive model flag (Dec 28, 2025)
    # Exclusive models get ₹15,000 points vs regular ₹7,500
    is_exclusive = Column(Boolean, default=False, nullable=False)
    
    # Display
    image_url = Column(Text, nullable=True)  # URL to model image
    description = Column(Text, nullable=True)
    specifications = Column(Text, nullable=True)  # JSON or text specs
    
    # Approval Workflow (Super Admin creates → RVZ approves)
    approval_status = Column(String(20), default='Pending', nullable=False)  # Pending, Approved, Rejected
    created_by_user_id = Column(String(12), ForeignKey('user.id'), nullable=True)
    approved_by_user_id = Column(String(12), ForeignKey('user.id'), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    rejection_reason = Column(Text, nullable=True)
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Metadata
    display_order = Column(Integer, default=0, nullable=False)  # For sorting in dropdown
    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time, nullable=False)
    
    # Relationships
    created_by = relationship("User", foreign_keys=[created_by_user_id])
    approved_by = relationship("User", foreign_keys=[approved_by_user_id])
    
    def __repr__(self):
        variant = f" {self.variant_name}" if self.variant_name else ""
        return f"<EVModel {self.model_name}{variant} - {self.max_discount_percentage}%>"
