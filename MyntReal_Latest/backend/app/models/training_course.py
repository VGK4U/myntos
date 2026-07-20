"""
Training Course Configuration - Super Admin/RVZ Created, RVZ Approved
Stores training courses with fee, duration, and discount configuration
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

class TrainingCourse(BaseModel):
    """
    Training Course Configuration Table
    Super Admin/RVZ creates → RVZ approves → Users see approved courses
    
    Discount: Platinum 20%, Diamond 10% (no cap)
    """
    __tablename__ = 'training_course'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Course Information
    course_name = Column(String(200), nullable=False)
    course_category = Column(String(100), nullable=True)  # Technical, Business, etc. (open)
    course_fee = Column(Float, nullable=False)
    duration = Column(String(100), nullable=True)  # e.g., "3 months", "40 hours"
    trainer_name = Column(String(100), nullable=True)
    trainer_contact = Column(String(15), nullable=True)
    
    # Display
    description = Column(Text, nullable=True)
    syllabus = Column(Text, nullable=True)
    image_url = Column(Text, nullable=True)
    
    # Approval Workflow (Super Admin/RVZ creates → RVZ approves)
    approval_status = Column(String(20), default='Pending', nullable=False)  # Pending, Approved, Rejected
    created_by_user_id = Column(String(12), ForeignKey('user.id'), nullable=True)
    approved_by_user_id = Column(String(12), ForeignKey('user.id'), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    rejection_reason = Column(Text, nullable=True)
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Metadata
    display_order = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time, nullable=False)
    
    # Relationships
    created_by = relationship("User", foreign_keys=[created_by_user_id])
    approved_by = relationship("User", foreign_keys=[approved_by_user_id])
    
    def __repr__(self):
        return f"<TrainingCourse {self.course_name} - ₹{self.course_fee}>"
