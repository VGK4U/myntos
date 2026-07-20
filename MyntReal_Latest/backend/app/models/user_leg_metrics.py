"""
User Leg Metrics Cache Model
Stores precomputed leg points and eligibility flags to avoid recursive tree traversals
Updated by scheduler and placement hooks for performance optimization
"""

from sqlalchemy import Column, String, Float, Boolean, DateTime, Integer, Index
from sqlalchemy import ForeignKey
from app.models.base import BaseModel, get_indian_time

class UserLegMetrics(BaseModel):
    """
    Cache table for user leg metrics - eliminates slow recursive queries
    
    Updated by:
    - Nightly scheduler (bulk refresh)
    - Placement hooks (when placements/activations change)
    
    Reduces dashboard load time from 15-31s to <2s
    """
    __tablename__ = 'user_leg_metrics'
    
    # Primary key
    id = Column(Integer, primary_key=True)
    user_id = Column(String(12), ForeignKey('user.id'), nullable=False, unique=True, index=True)
    
    # Leg points (decimal system: Platinum=1.0, Diamond=0.5, Blue/Loyal=0)
    left_points = Column(Float, nullable=False, default=0.0)
    right_points = Column(Float, nullable=False, default=0.0)
    total_points = Column(Float, nullable=False, default=0.0)
    
    # Effective matching count (min of left/right points)
    effective_matching_count = Column(Integer, nullable=False, default=0)
    
    # Eligibility flags for Ved Income and Matching
    has_left_direct = Column(Boolean, nullable=False, default=False)
    has_right_direct = Column(Boolean, nullable=False, default=False)
    first_match_achieved = Column(Boolean, nullable=False, default=False)
    
    # Direct referral counts
    total_direct_referrals = Column(Integer, nullable=False, default=0)
    active_direct_referrals = Column(Integer, nullable=False, default=0)
    
    # Binary tree counts (for display)
    left_team_count = Column(Integer, nullable=False, default=0)
    right_team_count = Column(Integer, nullable=False, default=0)
    left_active_count = Column(Integer, nullable=False, default=0)
    right_active_count = Column(Integer, nullable=False, default=0)
    
    # Ved Team CURRENT counts (DC Protocol - single source, updated by scheduler/activation)
    ved_team_total = Column(Integer, nullable=False, default=0)  # Current total Ved team count
    ved_team_active = Column(Integer, nullable=False, default=0)  # Current activated Ved team count
    ved_metrics_refreshed_at = Column(DateTime, nullable=True)  # Last Ved calculation timestamp
    
    # Snapshot columns (for "Previous" dashboard difference tracking)
    snapshot_direct_referrals = Column(Integer, nullable=False, default=0)
    snapshot_active_direct_referrals = Column(Integer, nullable=False, default=0)
    snapshot_matching_count = Column(Integer, nullable=False, default=0)
    snapshot_left_team = Column(Integer, nullable=False, default=0)
    snapshot_right_team = Column(Integer, nullable=False, default=0)
    snapshot_left_active = Column(Integer, nullable=False, default=0)
    snapshot_right_active = Column(Integer, nullable=False, default=0)
    snapshot_ved_total = Column(Integer, nullable=False, default=0)
    snapshot_ved_active = Column(Integer, nullable=False, default=0)
    last_snapshot_at = Column(DateTime, nullable=True)
    
    # Metadata
    updated_at = Column(DateTime, nullable=False, default=get_indian_time, onupdate=get_indian_time)
    calculation_source = Column(String(50), nullable=False, default='scheduler')  # 'scheduler', 'placement_hook', 'manual'
    
    # Indexes for fast lookups
    __table_args__ = (
        Index('idx_user_leg_metrics_user_id', 'user_id'),
        Index('idx_user_leg_metrics_updated_at', 'updated_at'),
    )
    
    def __repr__(self):
        return f'<UserLegMetrics user_id={self.user_id} left={self.left_points} right={self.right_points}>'
