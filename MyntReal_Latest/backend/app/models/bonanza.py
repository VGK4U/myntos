"""
Bonanza system models for FastAPI - Dynamic Reward Campaigns
Preserves exact Flask bonanza campaign and reward tracking
"""

from sqlalchemy import Column, String, Integer, Boolean, DateTime, Text, Numeric, CheckConstraint, UniqueConstraint, text
from sqlalchemy.orm import relationship
from sqlalchemy import ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from app.models.base import BaseModel, TimestampMixin, get_indian_time

class DynamicBonanza(BaseModel):
    """
    Dynamic bonanza campaign model - LEGACY SCHEMA
    Time-bound campaigns with metric deduction logic to prevent double benefits
    """
    __tablename__ = 'dynamic_bonanza'
    
    id = Column(Integer, primary_key=True)
    bonanza_name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    
    # Campaign period
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    
    # Target types (what metrics are required)
    has_direct_target = Column(Boolean, default=False, nullable=False)
    has_matching_target = Column(Boolean, default=False, nullable=False)
    
    # Status and management
    status = Column(String, default='draft', nullable=False)  # 'draft', 'active', 'approved', 'completed', 'cancelled'
    created_by = Column(String, nullable=False)
    approved_by = Column(String, nullable=True)
    approved_at = Column(DateTime, nullable=True)
    
    # Admin tracking
    admin_notes = Column(Text, nullable=True)
    approval_comments = Column(Text, nullable=True)
    
    # Budget
    total_budget_allocated = Column(Numeric, nullable=True)
    budget_notes = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    updated_at = Column(DateTime, default=get_indian_time, nullable=False)
    
    def __repr__(self):
        return f'<DynamicBonanza {self.bonanza_name}: {self.status}>'

class BonanzaProgress(BaseModel):
    """
    User progress tracking within bonanza campaigns
    Matches actual database schema - no extra columns
    FIXED: FK now correctly references bonanza.id (active system), not dynamic_bonanza.id (legacy)
    """
    __tablename__ = 'bonanza_progress'
    
    id = Column(Integer, primary_key=True)
    bonanza_id = Column(Integer, ForeignKey('bonanza.id'), nullable=False)  # FIXED: Points to active bonanza table
    user_id = Column(String(12), ForeignKey('user.id'), nullable=True)   # MNR member (nullable: VGK rows use partner_id)
    partner_id = Column(Integer, ForeignKey('official_partners.id', ondelete='CASCADE'), nullable=True)  # VGK partner progress
    reward_id = Column(Integer, ForeignKey('dynamic_bonanza_reward.id'), nullable=True)
    
    # Progress tracking (actual columns in DB)
    current_progress = Column(Integer, default=0, nullable=False)
    achievement_status = Column(String(30), default='In Progress', nullable=False)
    achieved_date = Column(DateTime, nullable=True)
    
    # Delivery/Processing tracking
    reward_given = Column(Boolean, default=False, nullable=False)
    reward_given_date = Column(DateTime, nullable=True)
    processed_status = Column(String(30), default='Pending', nullable=False)
    processed_date = Column(DateTime, nullable=True)
    processed_by = Column(String(12), nullable=True)  # DC: Removed FK - stores MNR ID or Staff emp_code
    
    # Notes
    notes = Column(Text, nullable=True)
    admin_notes = Column(Text, nullable=True)
    
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
    
    # Procurement fields
    vendor_name = Column(String(255), nullable=True)
    payment_mode = Column(String(50), nullable=True)
    payment_reference = Column(String(255), nullable=True)
    bill_upload_path = Column(String(500), nullable=True)
    
    # Delivery tracking
    delivered_by = Column(String(12), nullable=True)  # DC: Removed FK - stores MNR ID or Staff emp_code
    delivered_at = Column(DateTime, nullable=True)
    delivery_proof_path = Column(String(500), nullable=True)
    user_acknowledgment = Column(Boolean, default=False, nullable=False)
    
    # Batch processing
    bulk_batch_id = Column(String, nullable=True)
    rejection_reason = Column(Text, nullable=True)

    # DC-AWARD-TRIGGER-001 (Jul 2026): auto-trigger tracking on BonanzaProgress
    auto_triggered       = Column(Boolean, default=False, nullable=True)   # True if created by vgk_award_trigger service
    trigger_event_source = Column(String(30), nullable=True)               # which trigger event fired
    claim_level          = Column(Integer, nullable=True)                  # DC-EC-PER-LEVEL-TRIGGER-001: partner level that created this auto-triggered claim
    
    # Timestamps
    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time, nullable=False)
    
    def __repr__(self):
        return f'<BonanzaProgress {self.user_id} in Bonanza {self.bonanza_id}: {self.current_progress} - {self.achievement_status}>'

class DynamicBonanzaReward(BaseModel, TimestampMixin):
    """
    Specific reward definitions within bonanza campaigns
    Preserves Flask dynamic reward structure
    """
    __tablename__ = 'dynamic_bonanza_reward'
    
    id = Column(Integer, primary_key=True)
    bonanza_id = Column(Integer, ForeignKey('dynamic_bonanza.id'), nullable=False)
    reward_name = Column(String(100), nullable=False)
    
    # Reward criteria
    criteria_type = Column(String(30), nullable=False)  # 'achievement_count', 'points_threshold', 'rank_position'
    criteria_value = Column(Numeric(10, 2), nullable=False)
    criteria_operator = Column(String(10), default='>=', nullable=False)  # '>=', '>', '=', '<', '<='
    
    # Reward details
    reward_type = Column(String(30), nullable=False)  # 'cash', 'bonus', 'upgrade', 'recognition', 'award', 'gift'
    reward_amount = Column(Numeric(12, 2), nullable=True)  # Nullable for award/gift types
    reward_description = Column(Text, nullable=True)
    
    # Award/Gift specific fields (follows Awards tracking structure)
    award_name = Column(String(200), nullable=True)  # For award/gift types
    award_image = Column(String(255), nullable=True)  # Image/icon for the award/gift
    is_monetary = Column(Boolean, default=True, nullable=False)  # False for awards/gifts
    
    # Budget per award tier
    budget_amount = Column(Numeric(12, 2), nullable=True)

    # Availability and limits
    max_recipients = Column(Integer, nullable=True)
    current_recipients = Column(Integer, default=0, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Constraints
    __table_args__ = (
        CheckConstraint("criteria_type IN ('achievement_count', 'points_threshold', 'rank_position')", name='valid_criteria_type'),
        CheckConstraint("criteria_operator IN ('>=', '>', '=', '<', '<=')", name='valid_criteria_operator'),
        CheckConstraint("reward_type IN ('cash', 'bonus', 'upgrade', 'recognition', 'award', 'gift')", name='valid_reward_type'),
        CheckConstraint("reward_amount >= 0 OR reward_amount IS NULL", name='positive_or_null_reward_amount'),
        CheckConstraint("criteria_value >= 0", name='positive_criteria_value'),
    )
    
    def __repr__(self):
        return f'<DynamicBonanzaReward {self.reward_name}: ₹{self.reward_amount} for {self.criteria_type} {self.criteria_operator} {self.criteria_value}>'

class DynamicBonanzaHistory(BaseModel, TimestampMixin):
    """
    Historical record of bonanza reward claims and deductions
    Preserves Flask bonanza financial tracking and award deduction logic
    """
    __tablename__ = 'dynamic_bonanza_history'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(String(12), ForeignKey('user.id'), nullable=False)
    bonanza_id = Column(Integer, ForeignKey('dynamic_bonanza.id'), nullable=False)
    claimed_reward_id = Column(Integer, ForeignKey('dynamic_bonanza_reward.id'), nullable=True)
    
    # Achievement counts at claim time (CRITICAL for deduction calculation)
    direct_count_achieved = Column(Integer, nullable=True)
    matching_count_achieved = Column(Integer, nullable=True)
    
    # Award deduction tracking (CRITICAL for regular award eligibility)
    deduction_applied_to_direct_awards = Column(Boolean, default=False, nullable=False)
    deduction_applied_to_matching_awards = Column(Boolean, default=False, nullable=False)
    deduction_amount_direct = Column(Integer, default=0, nullable=False)
    deduction_amount_matching = Column(Integer, default=0, nullable=False)
    
    # Reward details (supports both monetary and non-monetary)
    reward_type = Column(String(30), nullable=True)  # 'cash', 'bonus', 'award', 'gift'
    reward_value_claimed = Column(Numeric(12, 2), nullable=True)  # Nullable for award/gift
    award_name = Column(String(200), nullable=True)  # For award/gift types
    award_image = Column(String(255), nullable=True)
    is_monetary = Column(Boolean, default=True, nullable=False)
    
    # Legacy delivery fields (kept for backward compatibility with existing code)
    delivery_notes = Column(Text, nullable=True)  # DEPRECATED: Use delivery_proof_path instead
    dispatch_date = Column(DateTime, nullable=True)  # DEPRECATED: Use delivered_at instead
    received_date = Column(DateTime, nullable=True)  # DEPRECATED: Use delivered_at instead
    
    # ========== UNIFIED COST VARIANCE TRACKING (DC PROTOCOL: IDENTICAL TO DIRECT/MATCHING AWARDS) ==========
    
    # Cost tracking and variance analysis
    budgeted_amount = Column(Numeric, nullable=True)  # Original budgeted amount (standardized name)
    actual_cost_paid = Column(Numeric, nullable=True)  # Actual amount paid (standardized name)
    cost_variance = Column(Numeric, nullable=True)  # Difference (budgeted - actual)
    cost_variance_reason = Column(Text, nullable=True)  # Why variance exists
    
    # Payment breakdown (DC Protocol: Unified schema across all award types)
    handling_charges = Column(Numeric, nullable=True)  # Company handling charges (base amount excluding GST)
    gst_amount = Column(Numeric, nullable=True)  # GST (18%) on handling charges
    tax_amount = Column(Numeric, nullable=True)  # Tax collected from winner (physical awards only)
    transport_charges = Column(Numeric, nullable=True)  # Transport charges (physical awards only)
    
    # Legacy field (kept for backward compatibility)
    actual_cost_incurred = Column(Numeric(15, 2), nullable=True)
    
    # Processing details
    claimed_at = Column(DateTime, nullable=True)
    processed_at = Column(DateTime, nullable=True)
    processed_by = Column(String(12), nullable=True)  # DC: Removed FK - stores MNR ID or Staff emp_code
    
    # ========== UNIFIED APPROVAL WORKFLOW (DC PROTOCOL: IDENTICAL TO DIRECT/MATCHING AWARDS) ==========
    
    # Admin approval (first stage)
    admin_approved_by = Column(String, nullable=True)
    admin_approved_at = Column(DateTime, nullable=True)
    
    # Super Admin decision (second stage)
    super_admin_decision_by = Column(String, nullable=True)
    super_admin_decision_at = Column(DateTime, nullable=True)
    super_admin_decision = Column(String, nullable=True)  # 'approved', 'rejected'
    super_admin_notes = Column(Text, nullable=True)
    
    # Finance processing (third stage)
    finance_processed_by = Column(String, nullable=True)
    finance_processed_at = Column(DateTime, nullable=True)
    payment_status = Column(String, nullable=True)  # 'queued', 'released', 'failed'
    transaction_id = Column(Integer, nullable=True)
    
    # RVZ Supreme Authority (skip-level approval/override)
    rvz_action_by = Column(String, nullable=True)
    rvz_action_at = Column(DateTime, nullable=True)
    rvz_action_type = Column(String, nullable=True)  # 'override', 'hold', 'release'
    rvz_notes = Column(Text, nullable=True)
    
    # Legacy RVZ fields (kept for backward compatibility, map to rvz_action_*)
    rvz_approval_status = Column(String(30), default='Pending RVZ Approval', nullable=False)  # 'Pending RVZ Approval', 'Procurement Pending', 'RVZ Rejected'
    rvz_approved_by = Column(String(12), nullable=True)  # DC: Removed FK - stores MNR ID or Staff emp_code
    rvz_approved_at = Column(DateTime, nullable=True)
    rvz_rejection_reason = Column(Text, nullable=True)
    
    # Status tracking
    processed_status = Column(String, default='Pending', nullable=False)  # Overall status: 'Pending', 'Admin Approved', 'Super Admin Approved', 'Processed for Dispatch', 'Procurement Pending', 'Rejected'
    procurement_status = Column(String(30), nullable=True)  # 'Pending Purchase', 'Purchased - Pending Delivery', 'Delivered'
    
    # ========== UNIFIED PROCUREMENT FIELDS (DC PROTOCOL: IDENTICAL TO DIRECT/MATCHING AWARDS) ==========
    
    vendor_name = Column(String(255), nullable=True)
    payment_mode = Column(String(50), nullable=True)
    payment_reference = Column(String(255), nullable=True)
    bill_upload_path = Column(String(500), nullable=True)
    
    # ========== UNIFIED DELIVERY TRACKING (DC PROTOCOL: IDENTICAL TO DIRECT/MATCHING AWARDS) ==========
    
    delivered_by = Column(String(12), nullable=True)  # DC: Removed FK - stores MNR ID or Staff emp_code
    delivered_at = Column(DateTime, nullable=True)
    delivery_proof_path = Column(String(500), nullable=True)
    user_acknowledgment = Column(Boolean, default=False, nullable=False)
    
    # Legacy delivery fields (kept for backward compatibility)
    delivery_notes = Column(Text, nullable=True)
    dispatch_date = Column(DateTime, nullable=True)
    received_date = Column(DateTime, nullable=True)
    
    # ========== UNIFIED BATCH PROCESSING (DC PROTOCOL: IDENTICAL TO DIRECT/MATCHING AWARDS) ==========
    
    bulk_batch_id = Column(String, nullable=True)
    rejection_reason = Column(Text, nullable=True)
    
    # Oct 21, 2025 Production Start Date - Legacy Award Filtering
    is_legacy_pre_reset = Column(Boolean, default=False, nullable=False)  # DC Protocol: Permanently hide pre-Oct 21 awards
    
    # ========== DC PROTOCOL: IMMUTABLE CONTRIBUTOR SNAPSHOTS ==========
    # Store exact contributors at claim time to prevent historical data drift
    # These snapshots ensure bonanza breakdowns never change due to activation_date modifications
    direct_contributors_snapshot = Column(JSONB, nullable=True)  # [{user_id, name, package, points, activation_date}]
    matching_contributors_snapshot = Column(JSONB, nullable=True)  # {left_leg: [...], right_leg: [...]}
    
    # Constraints
    __table_args__ = (
        CheckConstraint("deduction_amount_direct >= 0", name='positive_deduction_direct'),
        CheckConstraint("deduction_amount_matching >= 0", name='positive_deduction_matching'),
    )
    
    def __repr__(self):
        return f'<DynamicBonanzaHistory {self.user_id}: Bonanza {self.bonanza_id} ₹{self.reward_value_claimed}>'


# ========== MAIN BONANZA SYSTEM (Flask-compatible) ==========

class Bonanza(BaseModel):
    """
    Main Bonanza campaign model - matches Flask app exactly
    Features: Price ranges (hidden), Award linking, 3-tier approval workflow
    """
    __tablename__ = 'bonanza'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False)
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    
    # Portal targeting
    portal = Column(String(10), nullable=False, default='MNR')  # 'MNR' or 'VGK'
    grace_days = Column(Integer, nullable=False, default=30)    # days after bonanza END date for physical completion
    lead_source_id = Column(Integer, ForeignKey('crm_lead_sources.id', ondelete='SET NULL'), nullable=True)
    segment_id = Column(Integer, ForeignKey('signup_categories.id', ondelete='SET NULL'), nullable=True)  # DC Protocol: VGK segment filter (Solar/EV/etc)

    # Criteria
    criteria_type = Column(String(20), nullable=False)  # 'direct_referral', 'matching_points', 'completed_deals'
    target_requirement = Column(Integer, nullable=False)
    counts_towards_regular = Column(Boolean, default=False, nullable=False)
    consume_achievements = Column(Boolean, default=False, nullable=False)  # When True, deduct claimed bonanzas from future bonanza eligibility
    
    # Reward - supports both monetary and non-monetary (awards/gifts)
    reward_type = Column(String(30), default='cash', nullable=False)  # 'cash', 'bonus', 'award', 'gift'
    reward_amount = Column(Numeric(12, 2), nullable=True)  # Null for award/gift types
    reward_text = Column(Text, nullable=True)  # Description
    reward_file = Column(String(255), nullable=True)  # Image/document
    image_url = Column(Text, nullable=True)  # DC-BONANZA-IMG-001: Promo/banner image URL
    
    # Award/Gift specific fields
    award_name = Column(String(200), nullable=True)  # Name of award/gift
    is_monetary = Column(Boolean, default=True, nullable=False)  # False for awards/gifts
    
    # Status and approval
    status = Column(String(20), default='Pending', nullable=False)
    created_by = Column(String(12), nullable=False)  # DC: Removed FK - stores MNR ID or Staff emp_code
    approved_by = Column(String(12), nullable=True)  # DC: Removed FK - stores MNR ID or Staff emp_code
    approved_date = Column(DateTime, nullable=True)
    
    # Budget tracking
    total_budget = Column(Numeric(12, 2), nullable=True)
    current_spending = Column(Numeric(12, 2), default=0.00, nullable=False)
    
    # Winners limit (First Come First Served)
    max_winners = Column(Integer, default=50, nullable=False)  # Top 20/30/50 limit
    current_winners = Column(Integer, default=0, nullable=False)  # Count of claimed users
    
    # Hidden price range fields (Super Admin only)
    price_range_from = Column(Numeric(12, 2), default=0.00, nullable=False)
    price_range_to = Column(Numeric(12, 2), default=0.00, nullable=False)
    actual_price = Column(Numeric(12, 2), default=0.00, nullable=False)
    is_price_hidden = Column(Boolean, default=True, nullable=False)
    price_created_by = Column(String(12), nullable=True)  # DC: Removed FK - stores MNR ID or Staff emp_code
    price_last_updated_by = Column(String(12), nullable=True)  # DC: Removed FK - stores MNR ID or Staff emp_code
    price_last_updated_at = Column(DateTime, nullable=True)
    
    # Award linking fields
    linked_award_type = Column(String(20), nullable=True)
    linked_award_tier_id = Column(Integer, nullable=True)
    reduced_target = Column(Integer, nullable=True)

    # DC Protocol: Registered-member target bonus (VGK only)
    # When set, non-activated (registered) partners must hit (target_requirement + registered_target_bonus) deals.
    # Activated partners keep the standard target_requirement.
    # NULL = feature disabled for this bonanza (all members see same target).
    registered_target_bonus = Column(Integer, nullable=True)

    # DC_BONANZA_SLABWISE_001: Slab Wise bonus columns
    # slab_extra_amount  — the actual bonus paid by this bonanza (e.g. ₹3000); NULL = not a slab campaign
    # slab_base_reference — display-only reference to the base payout member already gets (e.g. ₹1000 Solar File Advance)
    slab_extra_amount   = Column(Numeric(12, 2), nullable=True)
    slab_base_reference = Column(Numeric(12, 2), nullable=True)

    # DC-SOLAR-DVR-ADV-20260701-001: Which advance kind counts toward this bonanza's target.
    # 'CIBIL' (default) = count CIBIL-cleared advances (kind='ADVANCE') — existing behaviour.
    # 'DVR'             = count first-payment DVR advances (kind='DVR_ADVANCE') only.
    # 'BOTH'            = count either type (DISTINCT lead_id to avoid double-counting).
    advance_count_basis = Column(String(10), default='CIBIL', nullable=True)

    # DC-EXTRA-COMM-001 (Jul 2026): Special Bonanza — per-file extra commission.
    # reward_type = 'extra_commission'; fires automatically when a lead hits trigger_event.
    # ec_l1_amount … ec_l5_amount: per-file bonus for each level (NULL = level not included).
    # Category filter lives in bonanza_category_filters (NULL = all categories).
    trigger_event  = Column(String(20), nullable=True)   # 'file_submitted'|'first_payment'|'file_completed'
    ec_l1_amount   = Column(Numeric(12, 2), nullable=True)
    ec_l2_amount   = Column(Numeric(12, 2), nullable=True)
    ec_l3_amount   = Column(Numeric(12, 2), nullable=True)
    ec_l4_amount   = Column(Numeric(12, 2), nullable=True)
    ec_l5_amount   = Column(Numeric(12, 2), nullable=True)

    # DC-AWARD-TRIGGER-001 (Jul 2026): Award/Gift trigger bonanzas.
    # reward_type = 'award'|'gift'; trigger_event shared with extra_commission column above.
    # award_level_notes: JSONB — per-level participation + display note.
    #   Schema: {"1": {"participate": true, "note": "..."}, "2": {"participate": false}, ...}
    #   Absent or empty = all levels with a non-null partner participate.
    # Category filter reuses bonanza_category_filters (NULL = all categories).
    award_level_notes = Column(JSONB, nullable=True)

    # DC-EC-PER-LEVEL-TRIGGER-001 (Jul 2026): per-level trigger events — all trigger-capable types.
    # ec_lN_trigger overrides global trigger_event for level N. NULL = fall back to global trigger_event.
    # Applies to extra_commission (immediate VCI), cash/bonus (BonanzaProgress claim), award/gift (claim).
    ec_l1_trigger = Column(String(30), nullable=True)
    ec_l2_trigger = Column(String(30), nullable=True)
    ec_l3_trigger = Column(String(30), nullable=True)
    ec_l4_trigger = Column(String(30), nullable=True)
    ec_l5_trigger = Column(String(30), nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time, nullable=False)
    
    # Soft Delete (RVZ-only protection)
    is_deleted = Column(Boolean, default=False, nullable=False)
    deleted_at = Column(DateTime, nullable=True)
    deleted_by = Column(String(12), nullable=True)  # DC: Removed FK - stores MNR ID or Staff emp_code
    deletion_reason = Column(Text, nullable=True)
    
    def calculate_actual_price(self):
        """Auto-calculate and update actual_price as MAX(price_range_from, price_range_to)"""
        try:
            from_price = float(self.price_range_from or 0)
            to_price = float(self.price_range_to or 0)
            self.actual_price = max(from_price, to_price)
            return self.actual_price
        except (ValueError, TypeError):
            self.actual_price = 0.00
            return 0.00
    
    def get_display_price_for_role(self, user_role):
        """Return price information only if user has permission to view it"""
        if user_role in ['Super Admin', 'Finance Admin']:
            return {
                'can_view_price': True,
                'price_range_from': float(self.price_range_from or 0),
                'price_range_to': float(self.price_range_to or 0),
                'actual_price': float(self.actual_price or 0),
                'price_created_by': self.price_created_by,
                'price_last_updated_by': self.price_last_updated_by,
                'price_last_updated_at': self.price_last_updated_at.isoformat() if self.price_last_updated_at else None
            }
        else:
            return {
                'can_view_price': False,
                'message': 'Price information is restricted'
            }
    
    def __repr__(self):
        return f'<Bonanza {self.name}: {self.status}>'


# DC-EXTRA-COMM-001 (Jul 2026): Category filter for extra_commission bonanzas.
# NULL = all categories. Non-NULL = only leads in listed category_ids qualify.
class BonanzaCategoryFilter(BaseModel):
    __tablename__ = 'bonanza_category_filters'

    id         = Column(Integer, primary_key=True)
    bonanza_id = Column(Integer, ForeignKey('bonanza.id', ondelete='CASCADE'), nullable=False, index=True)
    category_id = Column(Integer, ForeignKey('signup_categories.id', ondelete='CASCADE'), nullable=False)

    __table_args__ = (
        UniqueConstraint('bonanza_id', 'category_id', name='uq_bonanza_cat_filter'),
    )

    def __repr__(self):
        return f'<BonanzaCategoryFilter bonanza={self.bonanza_id} cat={self.category_id}>'


# DC-EXTRA-COMM-001 (Jul 2026): Idempotency log for extra commission payouts.
# Prevents double-firing if trigger is called more than once for the same lead+level.
class BonanzaExtraCommissionLog(BaseModel):
    __tablename__ = 'bonanza_extra_commission_log'

    id         = Column(Integer, primary_key=True)
    bonanza_id = Column(Integer, ForeignKey('bonanza.id', ondelete='CASCADE'), nullable=False, index=True)
    lead_id    = Column(Integer, nullable=False, index=True)
    level      = Column(Integer, nullable=False)          # 1–5
    partner_id = Column(Integer, nullable=True)
    vci_entry_id = Column(Integer, nullable=True)         # back-ref to VGKCashIncomeEntry.id
    created_at = Column(DateTime, nullable=False)

    __table_args__ = (
        UniqueConstraint('bonanza_id', 'lead_id', 'level', name='uq_bonanza_ec_log'),
    )

    def __repr__(self):
        return f'<BonanzaExtraCommissionLog bonanza={self.bonanza_id} lead={self.lead_id} L{self.level}>'


# DC Protocol (Apr 2026): T007 — Multiple slabs/gifts per bonanza campaign
class BonanzaSlab(BaseModel):
    """
    Per-slab reward tiers within a bonanza campaign.
    Each bonanza can have multiple slabs with different target ranges and rewards.
    """
    __tablename__ = 'bonanza_slabs'

    id = Column(Integer, primary_key=True)
    bonanza_id = Column(Integer, ForeignKey('bonanza.id', ondelete='CASCADE'), nullable=False, index=True)

    # Slab identification
    slab_label = Column(String(100), nullable=False)        # e.g. "Bronze", "Silver", "Gold"
    slab_order = Column(Integer, default=1, nullable=False)  # display order

    # Target range for this slab
    target_from = Column(Integer, nullable=False)            # Minimum target (inclusive)
    target_to = Column(Integer, nullable=True)               # Maximum target (NULL = unlimited / last slab)

    # Reward fields (mirrors Bonanza model)
    reward_type = Column(String(30), default='cash', nullable=False)  # 'cash', 'bonus', 'award', 'gift'
    reward_amount = Column(Numeric(12, 2), nullable=True)    # Null for non-monetary
    award_name = Column(String(200), nullable=True)          # Name for award/gift types
    is_monetary = Column(Boolean, default=True, nullable=False)

    # Winner limits for this slab
    max_winners = Column(Integer, nullable=True)             # NULL = unlimited
    current_winners = Column(Integer, default=0, nullable=False)

    # Budget per slab
    budget_amount = Column(Numeric(12, 2), nullable=True)

    is_active = Column(Boolean, default=True, nullable=False)

    # DC-SLAB-IMG-001: Optional slab-level promo image
    image_url = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time, nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'bonanza_id': self.bonanza_id,
            'slab_label': self.slab_label,
            'slab_order': self.slab_order,
            'target_from': self.target_from,
            'target_to': self.target_to,
            'reward_type': self.reward_type,
            'reward_amount': float(self.reward_amount) if self.reward_amount is not None else None,
            'award_name': self.award_name,
            'is_monetary': self.is_monetary,
            'max_winners': self.max_winners,
            'current_winners': self.current_winners,
            'budget_amount': float(self.budget_amount) if self.budget_amount is not None else None,
            'is_active': self.is_active,
            'image_url': self.image_url,
        }

    def __repr__(self):
        return f'<BonanzaSlab bonanza={self.bonanza_id} label={self.slab_label} target={self.target_from}-{self.target_to}>'