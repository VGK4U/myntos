"""
Ved Team Member tracking model
Dedicated table for explicit Ved Team management - eliminates recursive query bugs
"""

from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey, UniqueConstraint, Index
from app.models.base import BaseModel, get_indian_time

class VedTeamMember(BaseModel):
    """
    Ved Team Member tracking - EXPLICIT placement tree membership
    
    Purpose:
    - Track which users belong to which Ved Team (placement tree under Ved Head)
    - Eliminate recursive CTE queries and potential bugs
    - Fast lookups for Ved Income calculation
    - Clear audit trail of Ved Team structure
    
    Ved Program Logic:
    - Ved Owner = User with 3+ direct referrals (e.g., MNR1800359)
    - Ved Head = 3rd direct referral of Ved Owner (e.g., MNR1800362)
    - Ved Team = All users in placement tree under Ved Head (NO CASCADING)
    - Ved Income = Generated when Ved Team member activates
    
    Example:
    - MNR1800359 (Ved Owner) has 6 direct referrals
    - MNR1800362 (3rd referral) = Ved Head
    - MNR1800427, MNR1800428 (placement tree under MNR1800362) = Ved Team
    - When MNR1800427 activates → Ved Income for MNR1800359
    """
    __tablename__ = 'ved_team_member'
    
    # Primary Key
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Ved Structure
    ved_owner_id = Column(String(12), ForeignKey('user.id'), nullable=False, index=True)  # Who earns Ved Income
    ved_head_id = Column(String(12), ForeignKey('user.id'), nullable=False, index=True)   # 3rd direct referral
    member_id = Column(String(12), ForeignKey('user.id'), nullable=False, index=True)     # Team member
    
    # Placement Tree Metadata
    level = Column(Integer, nullable=False, default=1)  # Distance from Ved Head (1 = direct child)
    parent_id = Column(String(12), ForeignKey('user.id'), nullable=True)  # Parent in placement tree
    position = Column(String(10), nullable=True)  # 'LEFT' or 'RIGHT' under parent
    
    # Lifecycle Tracking
    joined_date = Column(DateTime, nullable=False, default=get_indian_time)  # When placed in tree
    is_active = Column(Boolean, default=True, nullable=False, index=True)  # Track if still in tree
    removed_date = Column(DateTime, nullable=True)  # If Ved structure changes
    
    # Audit Trail
    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time, nullable=True)
    
    # Constraints
    __table_args__ = (
        # Prevent duplicate entries
        UniqueConstraint('ved_owner_id', 'member_id', name='unique_ved_owner_member'),
        
        # Fast lookups
        Index('idx_ved_owner_active', 'ved_owner_id', 'is_active'),
        Index('idx_ved_head_active', 'ved_head_id', 'is_active'),
        Index('idx_member_active', 'member_id', 'is_active'),
    )
    
    def __repr__(self):
        status = "Active" if self.is_active else "Removed"
        return f'<VedTeamMember Owner:{self.ved_owner_id} Head:{self.ved_head_id} Member:{self.member_id} L{self.level} {status}>'
