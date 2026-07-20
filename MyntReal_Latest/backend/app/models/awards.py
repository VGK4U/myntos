"""
Award system models for FastAPI - Direct & Matching Referral Tiers
Preserves exact Flask award progression and achievement tracking
"""

from sqlalchemy import Column, String, Integer, Boolean, DateTime, Date, Text, Numeric, CheckConstraint, JSON
from sqlalchemy.orm import relationship
from sqlalchemy import ForeignKey
from app.models.base import BaseModel, TimestampMixin, get_indian_time

class DirectAwardTier(BaseModel):
    """
    Direct referral award tiers model - LEGACY SCHEMA
    Uses existing database fields: award_name, referral_count, actual_price, cumulative_required
    
    DC PROTOCOL TERMINOLOGY:
    - award_name field → Contains RANK (e.g., "Super Star", "Super Prime Star", "Super Gold Star")
    - award_description field → Contains AWARD ITEM (e.g., "Smart Watch", "Fridge", "GOA Trip")
    """
    __tablename__ = 'direct_award_tier'
    
    id = Column(Integer, primary_key=True)
    referral_count = Column(Integer, nullable=False)
    award_name = Column(Text, nullable=False)  # DC Protocol: This is the RANK
    award_description = Column(Text, nullable=False)  # DC Protocol: This is the AWARD ITEM
    
    # Price fields
    price_range_from = Column(Numeric, nullable=True)
    price_range_to = Column(Numeric, nullable=True)
    actual_price = Column(Numeric, nullable=True)
    price_last_updated_at = Column(DateTime, nullable=True)
    price_last_updated_by = Column(String, nullable=True)
    
    # Cumulative tracking (used for progressive awards)
    cumulative_required = Column(Integer, nullable=False, default=0)
    
    # Admin tracking
    created_at = Column(DateTime, nullable=True)
    last_updated_by = Column(String, nullable=True)
    last_updated_at = Column(DateTime, nullable=True)
    
    def __repr__(self):
        return f'<DirectAwardTier {self.award_name}: {self.referral_count} refs, ₹{self.actual_price}>'

class UserAwardProgress(BaseModel):
    """
    User progress tracking for direct referral awards - LEGACY SCHEMA
    """
    __tablename__ = 'user_award_progress'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(String, nullable=False)
    award_tier_id = Column(Integer, nullable=False)
    
    # Progress tracking (legacy fields)
    current_referrals = Column(Integer, default=0, nullable=True)
    required_referrals = Column(Integer, nullable=False)
    award_amount = Column(Numeric, nullable=True)
    status = Column(String, default='In Progress', nullable=True)
    
    # Achievement dates
    achieved_at = Column(DateTime, nullable=True)
    awarded_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=get_indian_time, nullable=True)
    
    # Eligibility and processing
    is_eligible = Column(Boolean, default=True, nullable=True)
    processed_date = Column(DateTime, nullable=True)
    processed_by = Column(String, nullable=True)
    admin_notes = Column(Text, nullable=True)
    
    # Bonanza tracking
    achieved_via_bonanza = Column(Boolean, default=False, nullable=True)
    bonanza_name = Column(String, nullable=True)
    bonanza_deductions_applied = Column(Integer, default=0, nullable=False)
    
    # Cumulative tracking
    cumulative_target_adjustment = Column(Integer, default=0, nullable=False)
    effective_progress_count = Column(Integer, default=0, nullable=False)
    lifetime_achievement_status = Column(String, default='Active', nullable=False)
    achievement_date = Column(DateTime, nullable=True)
    initial_qualification_met = Column(Boolean, default=False, nullable=False)
    requires_balanced_growth = Column(Boolean, default=False, nullable=False)
    
    # Verification status
    award_status = Column(String, default='pending', nullable=True)
    processed_status = Column(String, default='Pending', nullable=False)
    
    # Multi-role approval tracking
    admin_approved_by = Column(String, nullable=True)
    admin_approved_at = Column(DateTime, nullable=True)
    
    super_admin_decision_by = Column(String, nullable=True)
    super_admin_decision_at = Column(DateTime, nullable=True)
    super_admin_decision = Column(String, nullable=True)  # 'approved', 'rejected'
    super_admin_notes = Column(Text, nullable=True)
    
    finance_processed_by = Column(String, nullable=True)
    finance_processed_at = Column(DateTime, nullable=True)
    payment_status = Column(String, nullable=True)  # 'queued', 'released', 'failed'
    transaction_id = Column(Integer, nullable=True)
    
    rvz_action_by = Column(String, nullable=True)
    rvz_action_at = Column(DateTime, nullable=True)
    rvz_action_type = Column(String, nullable=True)  # 'override', 'hold', 'release'
    rvz_notes = Column(Text, nullable=True)
    
    # Cost variance tracking
    budgeted_amount = Column(Numeric, nullable=True)  # Original budgeted amount
    actual_cost_paid = Column(Numeric, nullable=True)  # Actual amount paid
    cost_variance = Column(Numeric, nullable=True)  # Difference (budgeted - actual)
    cost_variance_reason = Column(Text, nullable=True)  # Why variance exists
    
    # Payment breakdown (DC Protocol: Unified schema across all award types)
    handling_charges = Column(Numeric, nullable=True)  # Company handling charges (base amount excluding GST)
    gst_amount = Column(Numeric, nullable=True)  # GST (18%) on handling charges
    tax_amount = Column(Numeric, nullable=True)  # Tax collected from winner (physical awards only)
    transport_charges = Column(Numeric, nullable=True)  # Transport charges (physical awards only)
    
    # Procurement fields
    vendor_name = Column(String(255), nullable=True)
    payment_mode = Column(String(50), nullable=True)
    payment_reference = Column(String(255), nullable=True)
    bill_upload_path = Column(String(500), nullable=True)
    
    # Delivery tracking (DC Protocol: Unified tracking fields)
    dispatch_date = Column(Date, nullable=True)  # DC Protocol: Date item was dispatched
    received_date = Column(Date, nullable=True)  # DC Protocol: Date item was received by user
    delivery_notes = Column(Text, nullable=True)  # DC Protocol: Tracking notes
    delivered_by = Column(String(12), nullable=True)  # DC: Removed FK - stores MNR ID or Staff emp_code
    delivered_at = Column(DateTime, nullable=True)  # Backward compatibility
    delivery_proof_path = Column(String(500), nullable=True)
    user_acknowledgment = Column(Boolean, default=False, nullable=False)
    
    # Batch processing
    bulk_batch_id = Column(String, nullable=True)
    rejection_reason = Column(Text, nullable=True)
    
    # Oct 21, 2025 Production Start Date - Legacy Award Filtering
    is_legacy_pre_reset = Column(Boolean, default=False, nullable=False)  # DC Protocol: Permanently hide pre-Oct 21 awards
    
    def __repr__(self):
        return f'<UserAwardProgress {self.user_id}: {self.current_referrals}/{self.required_referrals}>'

class MatchingAwardTier(BaseModel):
    """
    Matching referral award tiers model - LEGACY SCHEMA
    Uses existing database fields: award_name, match_count, actual_price, cumulative_required
    
    DC PROTOCOL TERMINOLOGY:
    - award_name field → Contains RANK (e.g., "Master Star", "Elite Star", "Crown Star")
    - award_description field → Contains AWARD ITEM (e.g., "Fridge", "GOA Trip", "Cruise Trip")
    """
    __tablename__ = 'matching_award_tier'
    
    id = Column(Integer, primary_key=True)
    match_count = Column(Integer, nullable=False)
    award_name = Column(Text, nullable=False)  # DC Protocol: This is the RANK
    award_description = Column(Text, nullable=False)  # DC Protocol: This is the AWARD ITEM
    
    # Price fields
    price_range_from = Column(Numeric, nullable=True)
    price_range_to = Column(Numeric, nullable=True)
    actual_price = Column(Numeric, nullable=True)
    price_last_updated_at = Column(DateTime, nullable=True)
    price_last_updated_by = Column(String, nullable=True)
    
    # Cumulative tracking (used for progressive awards)
    cumulative_required = Column(Integer, nullable=False, default=0)
    
    # Admin tracking
    created_at = Column(DateTime, nullable=True)
    last_updated_by = Column(String, nullable=True)
    last_updated_at = Column(DateTime, nullable=True)
    
    def __repr__(self):
        return f'<MatchingAwardTier {self.award_name}: {self.match_count} matches, ₹{self.actual_price}>'

class UserMatchingAwardProgress(BaseModel):
    """
    User progress tracking for matching referral awards - LEGACY SCHEMA
    """
    __tablename__ = 'user_matching_award_progress'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(String, nullable=False)
    matching_award_tier_id = Column(Integer, nullable=False)
    
    # Progress tracking (legacy fields)
    current_matches = Column(Integer, default=0, nullable=True)
    required_matches = Column(Integer, default=0, nullable=True)
    is_eligible = Column(Boolean, default=False, nullable=False)
    status = Column(String, default='Pending', nullable=False)
    
    # Processing
    processed_date = Column(DateTime, nullable=True)
    processed_by = Column(String, nullable=True)
    admin_notes = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=get_indian_time, nullable=True)
    updated_at = Column(DateTime, default=get_indian_time, nullable=True)
    
    # Bonanza tracking
    achieved_via_bonanza = Column(Boolean, default=False, nullable=True)
    bonanza_name = Column(String, nullable=True)
    bonanza_deductions_applied = Column(Integer, default=0, nullable=False)
    
    # Cumulative tracking
    cumulative_target_adjustment = Column(Integer, default=0, nullable=False)
    effective_progress_count = Column(Integer, default=0, nullable=False)
    lifetime_achievement_status = Column(String, default='Active', nullable=False)
    achievement_date = Column(DateTime, nullable=True)
    initial_qualification_met = Column(Boolean, default=False, nullable=False)
    requires_balanced_growth = Column(Boolean, default=False, nullable=False)
    qualification_start_date = Column(DateTime, nullable=True)
    
    # Verification status
    award_status = Column(String, default='pending', nullable=True)
    processed_status = Column(String, default='Pending', nullable=False)
    
    # Multi-role approval tracking
    admin_approved_by = Column(String, nullable=True)
    admin_approved_at = Column(DateTime, nullable=True)
    
    super_admin_decision_by = Column(String, nullable=True)
    super_admin_decision_at = Column(DateTime, nullable=True)
    super_admin_decision = Column(String, nullable=True)  # 'approved', 'rejected'
    super_admin_notes = Column(Text, nullable=True)
    
    finance_processed_by = Column(String, nullable=True)
    finance_processed_at = Column(DateTime, nullable=True)
    payment_status = Column(String, nullable=True)  # 'queued', 'released', 'failed'
    transaction_id = Column(Integer, nullable=True)
    
    rvz_action_by = Column(String, nullable=True)
    rvz_action_at = Column(DateTime, nullable=True)
    rvz_action_type = Column(String, nullable=True)  # 'override', 'hold', 'release'
    rvz_notes = Column(Text, nullable=True)
    
    # Cost variance tracking
    budgeted_amount = Column(Numeric, nullable=True)  # Original budgeted amount
    actual_cost_paid = Column(Numeric, nullable=True)  # Actual amount paid
    cost_variance = Column(Numeric, nullable=True)  # Difference (budgeted - actual)
    cost_variance_reason = Column(Text, nullable=True)  # Why variance exists
    
    # Payment breakdown (DC Protocol: Unified schema across all award types)
    handling_charges = Column(Numeric, nullable=True)  # Company handling charges (base amount excluding GST)
    gst_amount = Column(Numeric, nullable=True)  # GST (18%) on handling charges
    tax_amount = Column(Numeric, nullable=True)  # Tax collected from winner (physical awards only)
    transport_charges = Column(Numeric, nullable=True)  # Transport charges (physical awards only)
    
    # Procurement fields
    vendor_name = Column(String(255), nullable=True)
    payment_mode = Column(String(50), nullable=True)
    payment_reference = Column(String(255), nullable=True)
    bill_upload_path = Column(String(500), nullable=True)
    
    # Delivery tracking (DC Protocol: Unified tracking fields)
    dispatch_date = Column(Date, nullable=True)  # DC Protocol: Date item was dispatched
    received_date = Column(Date, nullable=True)  # DC Protocol: Date item was received by user
    delivery_notes = Column(Text, nullable=True)  # DC Protocol: Tracking notes
    delivered_by = Column(String(12), nullable=True)  # DC: Removed FK - stores MNR ID or Staff emp_code
    delivered_at = Column(DateTime, nullable=True)  # Backward compatibility
    delivery_proof_path = Column(String(500), nullable=True)
    user_acknowledgment = Column(Boolean, default=False, nullable=False)
    
    # Batch processing
    bulk_batch_id = Column(String, nullable=True)
    rejection_reason = Column(Text, nullable=True)
    
    # Oct 21, 2025 Production Start Date - Legacy Award Filtering
    is_legacy_pre_reset = Column(Boolean, default=False, nullable=False)  # DC Protocol: Permanently hide pre-Oct 21 awards
    
    def __repr__(self):
        return f'<UserMatchingAwardProgress {self.user_id}: {self.current_matches}/{self.required_matches}>'


class AwardAuditLog(BaseModel):
    """
    Complete audit trail for all award-related actions
    Tracks every status change, approval, rejection, and override
    """
    __tablename__ = 'award_audit_log'
    
    id = Column(Integer, primary_key=True)
    
    # Entity identification
    entity_type = Column(String, nullable=False)  # 'direct_award', 'matching_award', 'bonanza'
    entity_id = Column(Integer, nullable=False)  # ID of the award progress record
    
    # Action details
    action = Column(String, nullable=False)  # 'admin_approved', 'super_admin_rejected', 'finance_processed', etc.
    old_status = Column(String, nullable=True)  # Previous processed_status
    new_status = Column(String, nullable=False)  # New processed_status
    
    # Actor details
    actor_role = Column(String, nullable=False)  # 'Admin', 'Super Admin', 'Finance Admin', 'RVZ ID'
    actor_id = Column(String, nullable=False)  # User ID who performed action
    
    # Additional context
    notes = Column(Text, nullable=True)  # Admin/system notes
    audit_metadata = Column(JSON, nullable=True)  # Additional context (amount, deductions, etc.)
    
    # Timestamp
    timestamp = Column(DateTime, default=get_indian_time, nullable=False)
    
    # Batch tracking (if part of bulk operation)
    batch_id = Column(String, nullable=True)
    
    def __repr__(self):
        return f'<AwardAuditLog {self.entity_type}#{self.entity_id}: {self.action} by {self.actor_role} {self.actor_id}>'