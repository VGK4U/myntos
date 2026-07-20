"""
Award Price Change Request Model - Admin requests, Finance Admin approves
"""

from sqlalchemy import Column, String, Integer, Numeric, DateTime, Text
from app.models.base import BaseModel, get_indian_time

class AwardPriceChangeRequest(BaseModel):
    """
    Award price change request with approval workflow
    Admin requests → Finance Admin approves
    """
    __tablename__ = 'award_price_change_request'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Award reference
    award_type = Column(String, nullable=False)  # 'direct' or 'matching'
    award_tier_id = Column(Integer, nullable=False)
    award_name = Column(Text, nullable=False)
    
    # Price change details
    current_price = Column(Numeric, nullable=False)
    new_price = Column(Numeric, nullable=False)
    change_reason = Column(Text, nullable=False)
    
    # Request details
    requested_by_id = Column(String, nullable=False)
    requested_at = Column(DateTime, default=get_indian_time, nullable=False)
    
    # Approval workflow
    status = Column(String, default='pending', nullable=False)  # pending, approved, rejected
    approved_by_id = Column(String, nullable=True)
    approved_at = Column(DateTime, nullable=True)
    approval_notes = Column(Text, nullable=True)
    
    def __repr__(self):
        return f'<AwardPriceChangeRequest {self.award_name}: ₹{self.current_price} → ₹{self.new_price} ({self.status})>'
