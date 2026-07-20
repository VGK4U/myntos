"""
Training Course Claim System
Tracks user claims for training course discounts
Uses SAME coupon as EV Scooter (combined balance tracking)
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

class TrainingClaim(BaseModel):
    """
    Training Course Claim Table
    Tracks user claims for training course discounts
    
    Business Rules:
    - Platinum: 20% discount (no cap)
    - Diamond: 10% discount (no cap)
    - Uses SAME coupon as EV Scooter
    - Extra usage allowed ONLY for training (show as Bonus)
    """
    __tablename__ = 'training_claim'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # User & Coupon Reference (Same coupon as EV Scooter)
    user_id = Column(String(12), ForeignKey('user.id'), nullable=False)
    coupon_id = Column(Integer, ForeignKey('coupon.id'), nullable=True)
    
    # Training Course Selection
    training_course_id = Column(Integer, ForeignKey('training_course.id'), nullable=False)
    
    # Trainee Details
    trainee_name = Column(String(100), nullable=False)
    trainee_contact = Column(String(15), nullable=False)
    trainee_email = Column(String(100), nullable=True)
    
    # Training Institute Information
    institute_name = Column(String(200), nullable=True)
    institute_contact = Column(String(15), nullable=True)
    
    # Financial Details
    course_fee_at_claim = Column(Float, nullable=False)  # Course fee when claim was made
    discount_percentage = Column(Float, nullable=False)  # 20 for Platinum, 10 for Diamond
    discount_amount = Column(Float, nullable=False)  # Actual discount applied
    is_bonus = Column(Boolean, default=False, nullable=False)  # True if exceeds coupon balance
    bonus_amount = Column(Float, default=0.0, nullable=False)  # Amount beyond coupon balance
    
    # Payment & Proof
    payment_proof_url = Column(Text, nullable=True)
    payment_reference = Column(String(100), nullable=True)
    
    # Claim Status Workflow
    # Pending → Admin Approved → Institute Confirmed → Completed
    claim_status = Column(String(30), default='Pending', nullable=False)
    
    # Admin Actions
    created_by_admin = Column(Boolean, default=False, nullable=False)
    created_by_user_id = Column(String(12), ForeignKey('user.id'), nullable=True)
    
    approved_by_user_id = Column(String(12), ForeignKey('user.id'), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    
    # Institute Assignment
    assigned_to_institute_at = Column(DateTime, nullable=True)
    institute_confirmed_at = Column(DateTime, nullable=True)
    
    # Completion
    completed_at = Column(DateTime, nullable=True)
    completion_notes = Column(Text, nullable=True)
    
    # Rejection
    rejection_reason = Column(Text, nullable=True)
    rejected_at = Column(DateTime, nullable=True)
    rejected_by_user_id = Column(String(12), ForeignKey('user.id'), nullable=True)
    
    # Package Info at Time of Claim
    package_at_claim = Column(String(20), nullable=True)  # Platinum, Diamond
    
    # Timestamps
    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time, nullable=False)
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id], backref="training_claims")
    training_course = relationship("TrainingCourse", backref="claims")
    created_by = relationship("User", foreign_keys=[created_by_user_id])
    approved_by = relationship("User", foreign_keys=[approved_by_user_id])
    rejected_by = relationship("User", foreign_keys=[rejected_by_user_id])
    
    def __repr__(self):
        return f"<TrainingClaim {self.id} - {self.user_id} - {self.claim_status}>"
