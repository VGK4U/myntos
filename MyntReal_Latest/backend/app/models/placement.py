"""
Placement model for FastAPI - Binary Tree Structure
Preserves exact Reference System tree placement logic from Flask app
"""

from sqlalchemy import Column, String, Integer, DateTime, CheckConstraint, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy import ForeignKey
from app.models.base import BaseModel, get_indian_time

class Placement(BaseModel):
    """
    Binary tree placement model preserving exact Flask schema
    Manages 943 users in binary tree structure (441 left, 502 right)
    """
    __tablename__ = 'placement'
    
    id = Column(Integer, primary_key=True)
    parent_id = Column(String(12), ForeignKey('user.id'), nullable=False)
    child_id = Column(String(12), ForeignKey('user.id'), nullable=False)
    side = Column(String(5), nullable=False)  # 'left' or 'right'
    
    # Placement metadata
    placed_at = Column(DateTime, default=get_indian_time, nullable=False)
    placed_by_id = Column(String(12), ForeignKey('user.id'), nullable=True)
    placement_method = Column(String(20), default='automatic', nullable=False)  # 'automatic', 'user_choice', 'admin'
    
    # Status tracking
    status = Column(String(20), default='active', nullable=False)  # 'active', 'removed'
    
    # Constraints to ensure data integrity (preserve Flask logic)
    __table_args__ = (
        # Ensure each child can only be placed once
        UniqueConstraint('child_id', name='unique_child_placement'),
        
        # Ensure each parent-side combination is unique (no duplicate left/right under same parent)
        UniqueConstraint('parent_id', 'side', name='unique_parent_side'),
        
        # Ensure side is only 'left' or 'right'
        CheckConstraint("side IN ('left', 'right')", name='valid_placement_side'),
        
        # Ensure status is valid
        CheckConstraint("status IN ('active', 'removed')", name='valid_placement_status'),
        
        # Ensure placement method is valid
        CheckConstraint("placement_method IN ('automatic', 'user_choice', 'admin')", name='valid_placement_method'),
    )
    
    def __repr__(self):
        return f'<Placement {self.child_id} under {self.parent_id} ({self.side})>'

class PlacementRequest(BaseModel):
    """
    Placement request model for admin approval workflow
    Preserves exact Flask placement request system
    """
    __tablename__ = 'placement_request'
    
    id = Column(Integer, primary_key=True)
    new_user_id = Column(String(12), ForeignKey('user.id'), nullable=False, unique=True)
    sponsor_user_id = Column(String(12), ForeignKey('user.id'), nullable=False)
    target_parent_id = Column(String(12), ForeignKey('user.id'), nullable=False)
    side = Column(String(10), nullable=False)  # 'Left' or 'Right' (note: capitalized in original)
    requested_by_type = Column(String(20), nullable=False)  # 'User' or 'Admin'
    requested_by_id = Column(String(12), ForeignKey('user.id'), nullable=False)
    status = Column(String(20), default='Pending', nullable=False)  # 'Pending', 'Approved', 'Rejected'
    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    decided_at = Column(DateTime, nullable=True)
    decided_by_id = Column(String(12), ForeignKey('user.id'), nullable=True)
    rejection_reason = Column(String, nullable=True)
    
    # Constraints
    __table_args__ = (
        CheckConstraint("side IN ('Left', 'Right')", name='valid_request_side'),
        CheckConstraint("requested_by_type IN ('User', 'Admin')", name='valid_requester_type'),
        CheckConstraint("status IN ('Pending', 'Approved', 'Rejected')", name='valid_request_status'),
    )
    
    def __repr__(self):
        return f'<PlacementRequest {self.new_user_id} -> {self.target_parent_id} ({self.side})>'

class PlacementLog(BaseModel):
    """
    Audit log for all placement actions
    Preserves exact Flask placement logging system
    """
    __tablename__ = 'placement_log'
    
    id = Column(Integer, primary_key=True)
    actor_id = Column(String(12), ForeignKey('user.id'), nullable=True)
    actor_role = Column(String(20), nullable=False)
    new_user_id = Column(String(12), ForeignKey('user.id'), nullable=False)
    sponsor_user_id = Column(String(12), ForeignKey('user.id'), nullable=True)
    target_parent_id = Column(String(12), ForeignKey('user.id'), nullable=True)
    side = Column(String(10), nullable=True)
    action = Column(String(30), nullable=False)  # 'Requested', 'Approved', 'Rejected', 'Placed'
    status_after = Column(String(20), nullable=False)
    timestamp = Column(DateTime, default=get_indian_time, nullable=False)
    additional_data = Column(String, nullable=True)  # JSON string for context
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String, nullable=True)
    
    # Constraints
    __table_args__ = (
        CheckConstraint("action IN ('Requested', 'Approved', 'Rejected', 'Placed')", name='valid_log_action'),
    )
    
    def __repr__(self):
        return f'<PlacementLog {self.action}: {self.new_user_id} by {self.actor_id}>'