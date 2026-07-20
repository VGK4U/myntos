"""
Field Allowance models for FastAPI - Performance-Based Allowance System
Preserves exact Flask two-tier allowance system (Standard and Car Allowance)
"""

from sqlalchemy import Column, String, Integer, Boolean, DateTime, Date, Text, Numeric, CheckConstraint
from sqlalchemy.orm import relationship
from sqlalchemy import ForeignKey
from app.models.base import BaseModel, TimestampMixin, get_indian_time

class FieldAllowanceEligibility(BaseModel):
    """
    Field allowance eligibility - LEGACY SCHEMA
    Standard Field Allowance: 7 directs in 45 days, 20 matches/month, ₹10K/month × 18 months
    """
    __tablename__ = 'field_allowance_eligibility'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(String, nullable=False)
    
    # Scheme configuration
    scheme_name = Column(String, default='Standard', nullable=False)
    monthly_amount = Column(Numeric, nullable=False)
    tenure_months = Column(Integer, nullable=False)
    total_value = Column(Numeric, nullable=False)
    
    # Initial qualification
    eligibility_requirement = Column(String, nullable=False)
    monthly_requirement = Column(String, nullable=False)
    initial_eligibility_met = Column(Boolean, default=False, nullable=True)
    initial_eligibility_date = Column(DateTime, nullable=True)
    activation_deadline = Column(DateTime, nullable=True)
    
    # Direct referrals tracking
    direct_referrals_count = Column(Integer, default=0, nullable=False)
    direct_referrals_target = Column(Integer, default=7, nullable=False)
    
    # Monthly matching tracking
    month_year = Column(String, default='2025-09', nullable=False)
    monthly_target_matchings = Column(Integer, default=20, nullable=False)
    monthly_achieved_matchings = Column(Integer, default=0, nullable=False)
    monthly_target_met = Column(Boolean, default=False, nullable=True)
    
    # Progress tracking
    overall_status = Column(String, default='Inactive', nullable=True)
    started_at = Column(DateTime, nullable=True)
    expected_completion = Column(DateTime, nullable=True)
    current_month_number = Column(Integer, default=0, nullable=False)
    months_completed = Column(Integer, default=0, nullable=False)
    months_missed = Column(Integer, default=0, nullable=False)
    
    # Payment tracking
    is_claimable = Column(Boolean, default=False, nullable=False)
    amount_paid = Column(Numeric, default=0.0, nullable=False)
    payment_date = Column(DateTime, nullable=True)
    total_paid_to_date = Column(Numeric, default=0.0, nullable=False)
    
    # Compliance
    zoom_calls_attended = Column(Boolean, default=False, nullable=False)
    promotional_activities_participated = Column(Boolean, default=False, nullable=False)
    terms_compliance = Column(Boolean, default=False, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=get_indian_time, nullable=True)
    updated_at = Column(DateTime, default=get_indian_time, nullable=True)
    eligibility_checked_at = Column(DateTime, default=get_indian_time, nullable=False)
    
    def __repr__(self):
        return f'<FieldAllowanceEligibility {self.user_id}: {self.overall_status}>'

class CarAllowanceEligibility(BaseModel):
    """
    Car allowance eligibility - LEGACY SCHEMA
    Car Allowance: 250 points in 90 days, 40 matches/month, ₹25K/month × 72 months
    """
    __tablename__ = 'car_allowance_eligibility'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(String, nullable=False)
    
    # Scheme configuration
    scheme_name = Column(String, default='Car Allowance', nullable=False)
    monthly_amount = Column(Numeric, default=25000.00, nullable=False)
    tenure_months = Column(Integer, default=72, nullable=False)
    total_value = Column(Numeric, default=1800000.00, nullable=False)
    
    # Initial qualification
    initial_eligibility_met = Column(Boolean, default=False, nullable=False)
    initial_eligibility_date = Column(DateTime, nullable=True)
    activation_deadline = Column(DateTime, nullable=True)
    
    # Matching points tracking
    matching_referrals_count = Column(Integer, default=0, nullable=False)
    matching_referrals_target = Column(Integer, default=250, nullable=False)
    
    # Monthly tracking
    month_year = Column(String, nullable=False)
    monthly_target_matchings = Column(Integer, default=40, nullable=False)
    monthly_achieved_matchings = Column(Integer, default=0, nullable=False)
    monthly_target_met = Column(Boolean, default=False, nullable=False)
    
    # Progress tracking
    overall_status = Column(String, default='Not Eligible', nullable=False)
    current_month_number = Column(Integer, default=0, nullable=False)
    months_completed = Column(Integer, default=0, nullable=False)
    months_missed = Column(Integer, default=0, nullable=False)
    
    # Payment tracking
    is_claimable = Column(Boolean, default=False, nullable=False)
    amount_paid = Column(Numeric, default=0.00, nullable=False)
    payment_date = Column(DateTime, nullable=True)
    total_paid_to_date = Column(Numeric, default=0.00, nullable=False)
    
    # Compliance
    zoom_calls_attended = Column(Boolean, default=False, nullable=False)
    promotional_activities_participated = Column(Boolean, default=False, nullable=False)
    terms_compliance = Column(Boolean, default=False, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    updated_at = Column(DateTime, default=get_indian_time, nullable=False)
    eligibility_checked_at = Column(DateTime, default=get_indian_time, nullable=False)
    
    def __repr__(self):
        return f'<CarAllowanceEligibility {self.user_id}: {self.overall_status}>'

class FieldAllowanceProgress(BaseModel):
    """
    Field allowance progress tracking model
    Aligned to actual database schema - DC Protocol Feb 2026
    Tracks monthly allowance eligibility, status, and payment progress
    """
    __tablename__ = 'field_allowance_progress'

    id = Column(Integer, primary_key=True)
    user_id = Column(String, nullable=False)
    allowance_type = Column(String, nullable=False)  # 'standard', 'car'
    month_year = Column(String, nullable=True)
    is_eligible = Column(Boolean, default=False, nullable=True)
    status = Column(String, nullable=True)  # 'Pending', 'Validated', 'Payout Completed'
    amount_paid = Column(Numeric, default=0.0, nullable=True)
    eligibility_checked_at = Column(DateTime, nullable=True)
    paid_at = Column(DateTime, nullable=True)
    completion_percentage = Column(Numeric, default=0.0, nullable=True)
    price_range_from = Column(Numeric, nullable=True)
    price_range_to = Column(Numeric, nullable=True)
    actual_price = Column(Numeric, nullable=True)
    is_price_hidden = Column(Boolean, default=False, nullable=True)
    price_last_updated_at = Column(DateTime, nullable=True)
    price_created_by = Column(String, nullable=True)
    price_last_updated_by = Column(String, nullable=True)

    # DC_VGK_FIELD_ALLOWANCE_STAGE_20260615: Stage 1/2 approval pipeline
    stage_1_approved_by = Column(String(20), nullable=True)   # emp_code of approver
    stage_1_approved_at = Column(DateTime, nullable=True)
    stage_2_paid_by     = Column(String(20), nullable=True)   # emp_code who marked paid
    stage_2_paid_at     = Column(DateTime, nullable=True)

    def __repr__(self):
        return f'<FieldAllowanceProgress {self.user_id}: {self.allowance_type} - {self.status}>'

class AllowanceSchemeSelector(BaseModel, TimestampMixin):
    """
    Allowance scheme selection model for user preference
    Preserves Flask allowance scheme selection system
    """
    __tablename__ = 'allowance_scheme_selector'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(String(12), ForeignKey('user.id'), nullable=False, unique=True)
    
    # Current selection
    selected_scheme = Column(String(20), nullable=False)  # 'standard', 'car', 'none'
    selection_date = Column(DateTime, default=get_indian_time, nullable=False)
    effective_from_date = Column(Date, nullable=False)
    
    # Previous selections history
    previous_scheme = Column(String(20), nullable=True)
    scheme_change_count = Column(Integer, default=0, nullable=False)
    last_change_date = Column(Date, nullable=True)
    
    # Qualification status
    qualified_for_standard = Column(Boolean, default=False, nullable=False)
    qualified_for_car = Column(Boolean, default=False, nullable=False)
    qualification_verified = Column(Boolean, default=False, nullable=False)
    
    # Lock-in period management
    is_locked = Column(Boolean, default=False, nullable=False)
    lock_expiry_date = Column(Date, nullable=True)
    lock_reason = Column(Text, nullable=True)
    
    # Administrative controls
    admin_override = Column(Boolean, default=False, nullable=False)
    override_reason = Column(Text, nullable=True)
    override_by_id = Column(String(12), ForeignKey('user.id'), nullable=True)
    override_date = Column(DateTime, nullable=True)
    
    # Status tracking
    is_active = Column(Boolean, default=True, nullable=False)
    deactivation_reason = Column(Text, nullable=True)
    deactivated_by_id = Column(String(12), ForeignKey('user.id'), nullable=True)
    
    # Constraints
    __table_args__ = (
        CheckConstraint("selected_scheme IN ('standard', 'car', 'none')", name='valid_selected_scheme'),
        CheckConstraint("previous_scheme IN ('standard', 'car', 'none')", name='valid_previous_scheme'),
        CheckConstraint("scheme_change_count >= 0", name='positive_change_count'),
    )
    
    def __repr__(self):
        return f'<AllowanceSchemeSelector {self.user_id}: {self.selected_scheme.title()} Scheme {"(Locked)" if self.is_locked else ""}>'

class AllowanceTierDefinition(BaseModel, TimestampMixin):
    """
    Allowance tier definition model for configurable tier structure
    Preserves Flask allowance tier management system
    """
    __tablename__ = 'allowance_tier_definition'
    
    id = Column(Integer, primary_key=True)
    allowance_type = Column(String(20), nullable=False)  # 'standard', 'car'
    tier_level = Column(Integer, nullable=False)
    tier_name = Column(String(50), nullable=False)
    
    # Requirements for this tier
    min_team_size = Column(Integer, nullable=False)
    min_active_referrals = Column(Integer, nullable=False)
    min_monthly_volume = Column(Numeric(15, 2), nullable=False)
    min_personal_volume = Column(Numeric(15, 2), default=0.0, nullable=False)
    
    # Performance criteria
    min_retention_rate = Column(Numeric(5, 2), default=0.0, nullable=False)  # Percentage
    min_activity_score = Column(Numeric(5, 2), default=0.0, nullable=False)  # 0-100 scale
    leadership_requirements = Column(Text, nullable=True)  # JSON string
    
    # Allowance benefits
    monthly_allowance = Column(Numeric(12, 2), nullable=False)
    additional_benefits = Column(Text, nullable=True)  # JSON string of extra benefits
    bonus_multiplier = Column(Numeric(5, 2), default=1.0, nullable=False)
    
    # Tier progression
    promotion_criteria = Column(Text, nullable=True)  # JSON string
    auto_promotion = Column(Boolean, default=True, nullable=False)
    demotion_criteria = Column(Text, nullable=True)  # JSON string
    grace_period_days = Column(Integer, default=30, nullable=False)
    
    # Status and availability
    is_active = Column(Boolean, default=True, nullable=False)
    launch_date = Column(Date, nullable=True)
    retirement_date = Column(Date, nullable=True)
    
    # Visual and description
    tier_description = Column(Text, nullable=True)
    tier_icon = Column(String(100), nullable=True)
    tier_color = Column(String(20), nullable=True)
    
    # Constraints
    __table_args__ = (
        CheckConstraint("allowance_type IN ('standard', 'car')", name='valid_tier_allowance_type'),
        CheckConstraint("tier_level > 0", name='positive_tier_level'),
        CheckConstraint("min_team_size >= 0", name='positive_min_team'),
        CheckConstraint("min_active_referrals >= 0", name='positive_min_active'),
        CheckConstraint("min_monthly_volume >= 0", name='positive_min_monthly'),
        CheckConstraint("min_personal_volume >= 0", name='positive_min_personal'),
        CheckConstraint("min_retention_rate >= 0 AND min_retention_rate <= 100", name='valid_retention_rate'),
        CheckConstraint("min_activity_score >= 0 AND min_activity_score <= 100", name='valid_activity_score'),
        CheckConstraint("monthly_allowance >= 0", name='positive_monthly_allowance'),
        CheckConstraint("bonus_multiplier > 0", name='positive_bonus_multiplier'),
        CheckConstraint("grace_period_days >= 0", name='positive_grace_period'),
    )
    
    def __repr__(self):
        return f'<AllowanceTierDefinition {self.allowance_type.title()} Level {self.tier_level}: {self.tier_name} (₹{self.monthly_allowance}/month)>'