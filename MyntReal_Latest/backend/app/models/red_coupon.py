"""
Red Coupon Voting System Models
User account reactivation approval with 3-tier workflow and voting mechanism
"""

from sqlalchemy import Column, String, Integer, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB
from app.models.base import BaseModel, get_indian_time

class RedCouponApproval(BaseModel):
    """
    Red Coupon reactivation approval requests
    """
    __tablename__ = 'red_coupon_approval'
    
    id = Column(Integer, primary_key=True)
    tracker_id = Column(Integer, nullable=False)
    user_id = Column(String(12), ForeignKey('user.id'), nullable=False)
    
    # Approval type and routing
    approval_type = Column(String(50), nullable=False)
    requested_by = Column(String(12), ForeignKey('user.id'), nullable=True)
    approved_by = Column(String(12), ForeignKey('user.id'), nullable=True)
    
    # Status and decision
    status = Column(String(20), default='pending', nullable=False)
    approval_reason = Column(Text, nullable=True)
    rejection_reason = Column(Text, nullable=True)
    
    # Approval requirements
    requires_super_admin = Column(Boolean, default=False, nullable=False)
    requires_accounts_admin = Column(Boolean, default=False, nullable=False)
    requires_member_votes = Column(Integer, default=0, nullable=False)
    
    # Timestamps
    requested_date = Column(DateTime, default=get_indian_time, nullable=False)
    approved_date = Column(DateTime, nullable=True)
    rejected_date = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time, nullable=False)
    
    # Voting status
    voting_closed = Column(Boolean, default=False, nullable=False)
    voting_closed_date = Column(DateTime, nullable=True)
    early_majority_reached = Column(Boolean, default=False, nullable=False)
    
    def __repr__(self):
        return f'<RedCouponApproval {self.user_id}: {self.status}>'


class RedCouponReassignmentVote(BaseModel):
    """
    Individual votes for Red Coupon reactivation (3-person voting)
    """
    __tablename__ = 'red_coupon_reassignment_vote'
    
    id = Column(Integer, primary_key=True)
    approval_id = Column(Integer, ForeignKey('red_coupon_approval.id'), nullable=False)
    voter_id = Column(String(12), ForeignKey('user.id'), nullable=False)
    
    # Vote details
    vote = Column(String(10), nullable=False)
    vote_reason = Column(Text, nullable=True)
    vote_weight = Column(Integer, default=1, nullable=False)
    voter_role = Column(String(20), nullable=False)
    is_qualified_voter = Column(Boolean, default=True, nullable=False)
    
    # Timestamps
    voted_date = Column(DateTime, default=get_indian_time, nullable=False)
    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    
    def __repr__(self):
        return f'<RedCouponVote {self.voter_id}: {self.vote}>'


class RedCouponAuditLog(BaseModel):
    """
    Audit log for Red Coupon actions
    """
    __tablename__ = 'red_coupon_audit_log'
    
    id = Column(Integer, primary_key=True)
    tracker_id = Column(Integer, nullable=False)
    user_id = Column(String(12), ForeignKey('user.id'), nullable=False)
    performed_by = Column(String(12), ForeignKey('user.id'), nullable=False)
    
    # Action details
    action_type = Column(String(50), nullable=False)
    action_description = Column(Text, nullable=True)
    old_status = Column(String(20), nullable=True)
    new_status = Column(String(20), nullable=True)
    
    # Request metadata
    ip_address = Column(String(50), nullable=True)
    user_agent = Column(String(255), nullable=True)
    additional_data = Column(JSONB, nullable=True)
    
    # Timestamps
    performed_date = Column(DateTime, default=get_indian_time, nullable=False)
    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    
    def __repr__(self):
        return f'<RedCouponAuditLog {self.action_type} by {self.performed_by}>'
