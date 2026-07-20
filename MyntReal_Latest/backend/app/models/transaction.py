"""
Transaction model for FastAPI - Financial System
Preserves exact income calculation and financial integrity from Flask app
"""

from sqlalchemy import Column, String, Integer, BigInteger, Numeric, DateTime, Text, UniqueConstraint, Date, Boolean
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy import ForeignKey
from app.models.base import BaseModel, get_indian_time

class Transaction(BaseModel):
    """
    Transaction model preserving exact Flask financial system
    Handles 4 income streams: Direct Referral, Matching Referral, Ved Income, Guru Dakshina
    """
    __tablename__ = 'transaction'
    
    id = Column(Integer, primary_key=True)
    referrer_id = Column(String(12), ForeignKey('user.id'), nullable=False)
    referred_user_id = Column(String(12), ForeignKey('user.id'), nullable=False)
    amount = Column(Numeric(12, 2), nullable=False)  # High precision for financial data
    transaction_type = Column(String(50), default='Direct Referral', nullable=False)
    timestamp = Column(DateTime, default=get_indian_time, nullable=False)
    
    # Referral linkage and idempotency (preserves Flask logic)
    referral_type = Column(String(20), nullable=True)  # 'insurance', 'ev_franchise', 'royal_fleet'
    referral_id = Column(Integer, nullable=True)  # ID of specific referral
    
    # Unique constraint to prevent duplicate payouts (preserves Flask safety)
    __table_args__ = (
        UniqueConstraint('referral_type', 'referral_id', 'transaction_type', name='unique_referral_payout'),
    )
    
    def __repr__(self):
        return f'<Transaction {self.transaction_type}: {self.amount} from {self.referrer_id} for {self.referred_user_id}>'

class CompanyEarnings(BaseModel):
    """
    Company earnings model for daily ceiling excess amounts
    Preserves exact Flask ceiling logic (₹50,000 daily limit)
    """
    __tablename__ = 'company_earnings'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(String(12), ForeignKey('user.id'), nullable=False)
    
    # Amount breakdown (preserves Flask deduction logic)
    original_amount = Column(Numeric(15, 2), nullable=False)  # Original calculated amount
    excess_amount = Column(Numeric(15, 2), nullable=False)    # Amount above ceiling
    admin_deduction = Column(Numeric(15, 2), nullable=True)  # 8% admin deduction
    tds_deduction = Column(Numeric(15, 2), nullable=True)    # 2% TDS deduction
    net_company_earnings = Column(Numeric(15, 2), nullable=False)  # 90% net to company
    paid_amount = Column(Numeric(15, 2), nullable=False)  # Amount paid (from DB schema)
    
    # Business context
    ceiling_date = Column(Date, nullable=False)  # Ceiling date for calculation (matches DB)
    income_type = Column(String(30), nullable=False)  # 'Ved Income' or 'Matching Referral'
    daily_total_before = Column(Numeric(15, 2), nullable=False)  # Daily total before this transaction
    daily_ceiling_limit = Column(Numeric(15, 2), nullable=True)  # Daily ceiling limit applied
    
    # Compliance tracking (DC Protocol: Source of truth for GST/Handling compliance)
    tally_status = Column(String(20), default='PENDING', nullable=False)  # 'PENDING', 'UPDATED'
    tally_updated_by_id = Column(String(12), ForeignKey('user.id'), nullable=True)
    tally_updated_at = Column(DateTime, nullable=True)
    collection_status = Column(String(20), default='PENDING', nullable=False)  # 'PENDING', 'COLLECTED'
    collection_updated_by_id = Column(String(12), ForeignKey('user.id'), nullable=True)
    collection_updated_at = Column(DateTime, nullable=True)
    
    # Audit trail
    timestamp = Column(DateTime, default=get_indian_time, nullable=True)
    description = Column(Text, nullable=True)  # Description (from DB schema)
    
    def __repr__(self):
        return f'<CompanyEarnings {self.user_id}: ₹{self.excess_amount} excess from {self.income_type}>'

class VedIncome(BaseModel):
    """
    Ved Income model preserving exact Flask Ved system
    Multi-level ownership and income distribution
    """
    __tablename__ = 'ved_income'
    
    id = Column(Integer, primary_key=True)
    ved_member_id = Column(String(12), ForeignKey('user.id'), nullable=False)  # Ved member
    ved_owner_id = Column(String(12), ForeignKey('user.id'), nullable=False)   # Ved owner
    new_member_id = Column(String(12), ForeignKey('user.id'), nullable=False)  # New member triggering income
    
    # Financial details
    base_amount = Column(Numeric(12, 2), nullable=False)      # Base income amount
    ceiling_applied_amount = Column(Numeric(12, 2), nullable=False)  # After ceiling logic
    excess_amount = Column(Numeric(12, 2), default=0.0, nullable=False)  # Excess to company
    
    # Business context
    business_date = Column(DateTime, nullable=False)
    calculation_timestamp = Column(DateTime, default=get_indian_time, nullable=False)
    
    # Ved relationship metadata
    ved_relationship_level = Column(Integer, nullable=True)   # Level in Ved hierarchy
    income_percentage = Column(Numeric(5, 2), nullable=True) # Percentage of base income
    
    def __repr__(self):
        return f'<VedIncome {self.ved_owner_id} from {self.new_member_id}: ₹{self.ceiling_applied_amount}>'

class DailyCostCalculation(BaseModel):
    """
    Daily cost calculation model for financial reporting
    Preserves exact Flask financial tracking system
    """
    __tablename__ = 'daily_cost_calculation'
    
    id = Column(Integer, primary_key=True)
    business_date = Column(DateTime, nullable=False, unique=True)  # Date of calculation
    
    # Income type totals (preserves Flask calculation structure)
    direct_referral_total = Column(Numeric(15, 2), default=0.0, nullable=False)
    matching_referral_total = Column(Numeric(15, 2), default=0.0, nullable=False)
    ved_income_total = Column(Numeric(15, 2), default=0.0, nullable=False)
    guru_dakshina_total = Column(Numeric(15, 2), default=0.0, nullable=False)
    
    # Deduction totals
    admin_deduction_total = Column(Numeric(15, 2), default=0.0, nullable=False)  # 8%
    tds_total = Column(Numeric(15, 2), default=0.0, nullable=False)              # 2%
    
    # Company earnings from ceiling excess
    company_earnings_total = Column(Numeric(15, 2), default=0.0, nullable=False)
    
    # Summary calculations
    gross_payout = Column(Numeric(15, 2), default=0.0, nullable=False)     # Total before deductions
    net_payout = Column(Numeric(15, 2), default=0.0, nullable=False)       # Total after deductions
    total_users_paid = Column(Integer, default=0, nullable=False)          # Number of users receiving income
    
    # Calculation metadata
    calculation_completed_at = Column(DateTime, nullable=True)
    calculation_status = Column(String(20), default='Pending', nullable=False)  # 'Pending', 'Completed', 'Failed'
    
    # Audit trail
    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    notes = Column(Text, nullable=True)  # Any special notes about the calculation
    
    def __repr__(self):
        return f'<DailyCostCalculation {self.business_date}: ₹{self.net_payout} total payout>'

class TDSPayable(BaseModel):
    """
    TDS payable tracking model - DC Protocol: Matches actual database schema
    Actual columns in database: id, user_id, tds_amount, paid_amount, pending_amount,
    payment_status, period_start, period_end, generated_date, last_payment_date,
    updated_at, updated_by, payment_notes, is_active,
    it_section, challan_number, challan_date, bank_bsr_code  (DC-TDS-CHALLAN-001)
    """
    __tablename__ = 'tds_payable'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(String(12), ForeignKey('user.id'), nullable=False)
    
    # TDS amounts
    tds_amount = Column(Numeric(12, 2), nullable=False)
    paid_amount = Column(Numeric(12, 2), nullable=True)
    pending_amount = Column(Numeric(12, 2), nullable=True)
    
    # Payment tracking
    payment_status = Column(String(20), default='Pending', nullable=False)  # 'Pending', 'Paid'
    last_payment_date = Column(DateTime, nullable=True)  # DC Protocol: Actual column name in DB
    payment_notes = Column(Text, nullable=True)
    
    # Period tracking
    period_start = Column(Date, nullable=True)
    period_end = Column(Date, nullable=True)
    generated_date = Column(DateTime, nullable=True)  # When TDS was calculated
    business_date = Column(DateTime, nullable=True)   # Business date for grouping

    # DC-TDS-CHALLAN-001: IT section classification + government challan reconciliation
    # it_section: Income Tax Act section under which TDS is deducted
    #   194H = Commission  |  194I = Rent  |  194J = Professional/Technical fees
    it_section     = Column(String(20), default='194H', nullable=True)
    # challan_number: BSR/CIN reference from government OLTAS portal after remittance
    challan_number = Column(String(50), nullable=True)
    # challan_date: Date on which TDS was remitted to government bank
    challan_date   = Column(Date, nullable=True)
    # bank_bsr_code: 7-digit BSR code of the collecting bank branch
    bank_bsr_code  = Column(String(10), nullable=True)
    
    # Audit trail
    updated_at = Column(DateTime, default=get_indian_time, nullable=True)
    updated_by = Column(String(12), nullable=True)
    is_active = Column(Boolean, default=True, nullable=True)
    
    def __repr__(self):
        return f'<TDSPayable {self.user_id}: ₹{self.tds_amount} ({self.payment_status}) [{self.it_section}]>'

class PendingIncome(BaseModel):
    """
    Pending Income model for NEW 4-package system
    Tracks calculated incomes awaiting Admin → Super Admin → Accounts verification
    """
    __tablename__ = 'pending_income'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(String(12), ForeignKey('user.id'), nullable=False)
    
    # Income details
    income_type = Column(String(50), nullable=False)  # 'Direct Referral', 'Matching Referral', 'Ved Income', 'Guru Dakshina'
    gross_amount = Column(Numeric(12, 2), nullable=False)  # Before deductions
    gurudakshina_deduction = Column(Numeric(12, 2), default=0.0, nullable=False)  # 2% Guru Dakshina paid to referrer
    admin_deduction = Column(Numeric(12, 2), nullable=False)  # 8%
    tds_deduction = Column(Numeric(12, 2), nullable=False)  # 2%
    net_amount = Column(Numeric(12, 2), nullable=False)  # After all deductions (88% of gross for non-GD income, 90% for GD income)
    
    # Wallet allocation (for Diamond/Blue/Loyal packages)
    withdrawal_wallet_amount = Column(Numeric(12, 2), default=0.0, nullable=False)
    upgraded_wallet_amount = Column(Numeric(12, 2), default=0.0, nullable=False)
    
    # Matching Referral tracking
    pairs_matched = Column(Integer, default=0, nullable=False)  # Number of pairs matched (for Matching Referral income)
    left_points_consumed = Column(Integer, default=0, nullable=False)  # Left leg points consumed
    right_points_consumed = Column(Integer, default=0, nullable=False)  # Right leg points consumed
    match_type = Column(String(50), nullable=True)  # NEW: '2_to_1_first_matching', '1_to_2_first_matching', 'subsequent_1_to_1'
    
    # Business context
    business_date = Column(DateTime, nullable=False)  # Date income was earned
    calculation_timestamp = Column(DateTime, default=get_indian_time, nullable=False)
    
    # Verification workflow (Admin → Super Admin → Accounts)
    verification_status = Column(String(30), default='Pending', nullable=False)  # 'Pending', 'Admin Verified', 'Super Admin Verified', 'Completed', 'Rejected', 'Informational'
    admin_verified_by_id = Column(String(12), ForeignKey('user.id'), nullable=True)
    admin_verified_at = Column(DateTime, nullable=True)
    super_admin_verified_by_id = Column(String(12), ForeignKey('user.id'), nullable=True)
    super_admin_verified_at = Column(DateTime, nullable=True)
    accounts_paid_by_id = Column(String(12), ForeignKey('user.id'), nullable=True)
    accounts_paid_at = Column(DateTime, nullable=True)
    
    # Rejection handling
    rejection_reason = Column(Text, nullable=True)
    rejected_by_id = Column(String(12), ForeignKey('user.id'), nullable=True)
    rejected_at = Column(DateTime, nullable=True)
    
    # Link to related records
    related_user_id = Column(String(12), ForeignKey('user.id'), nullable=True)  # For referral incomes
    coupon_id = Column(BigInteger, ForeignKey('coupon.id'), nullable=True)  # Link to activation coupon
    
    # Compliance tracking (DC Protocol: Source of truth for TDS compliance)
    tally_status = Column(String(20), default='PENDING', nullable=False)  # 'PENDING', 'UPDATED'
    tally_updated_by_id = Column(String(12), ForeignKey('user.id'), nullable=True)
    tally_updated_at = Column(DateTime, nullable=True)
    payment_status = Column(String(20), default='PENDING', nullable=False)  # 'PENDING', 'PAID'
    payment_updated_by_id = Column(String(12), ForeignKey('user.id'), nullable=True)
    payment_updated_at = Column(DateTime, nullable=True)
    
    # Ceiling tracking (DC Protocol: Track when daily ₹50k ceiling applied)
    ceiling_applied = Column(Boolean, default=False, nullable=False)  # True if ceiling reduced this income
    original_gross_amount = Column(Numeric(12, 2), nullable=True)  # Pre-ceiling amount (if ceiling applied)
    ceiling_excess_amount = Column(Numeric(12, 2), default=0.0, nullable=False)  # Amount sent to company earnings
    
    matching_contributors_snapshot = Column(JSONB, nullable=True)
    
    # Audit trail
    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time, nullable=False)
    notes = Column(Text, nullable=True)
    
    def __repr__(self):
        return f'<PendingIncome {self.user_id}: ₹{self.net_amount} {self.income_type} - {self.verification_status}>'


class Expense(BaseModel):
    """
    Expense tracking model - RVZ Supreme Authority System
    Finance Admin creates → RVZ approves
    RVZ creates → Auto-approved (supreme authority)
    Award procurement → Auto-creates expense
    """
    __tablename__ = 'expense'
    
    id = Column(Integer, primary_key=True)
    
    # Core expense details
    expense_date = Column(Date, nullable=False)
    amount = Column(Numeric(12, 2), nullable=False)
    category = Column(String(20), nullable=False)
    description = Column(Text, nullable=False)
    vendor = Column(String(200), nullable=True)
    
    # Payment details
    payment_mode = Column(String(20), nullable=False)
    reference_no = Column(String(100), nullable=True)
    
    # Bill upload details
    bill_filename = Column(String(255), nullable=True)
    bill_mime_type = Column(String(100), nullable=True)
    bill_size = Column(Integer, nullable=True)
    
    # Award/Bonanza linkage (for procurement tracking)
    award_reference_id = Column(Integer, nullable=True)  # Links to user_award_progress or user_matching_award_progress
    award_reference_type = Column(String(50), nullable=True)  # 'Direct Award', 'Matching Award'
    bonanza_reference_id = Column(Integer, nullable=True)  # Links to bonanza_progress
    bonanza_reference_type = Column(String(50), nullable=True)  # 'Cash Bonanza', 'Physical Bonanza'
    procurement_reference_id = Column(Integer, nullable=True)  # Generic procurement reference
    
    # RVZ Supreme Authority fields
    source_type = Column(String(30), default='finance_manual', nullable=False)  # 'finance_manual', 'rvz_manual', 'auto_award'
    rvz_auto_approved = Column(Boolean, default=False, nullable=False)  # True if RVZ created (auto-approved)
    
    # User relationships and workflow
    created_by_id = Column(String(12), ForeignKey('user.id'), nullable=False)
    approved_by_id = Column(String(12), ForeignKey('user.id'), nullable=True)  # Legacy Super Admin approval
    rvz_approved_by_id = Column(String(12), ForeignKey('user.id'), nullable=True)  # RVZ approval
    
    # Status and workflow
    status = Column(String(20), default='pending', nullable=False)  # 'pending', 'approved', 'rejected'
    approved_at = Column(DateTime, nullable=True)
    rvz_approved_at = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)
    
    # Soft delete with RVZ tracking
    is_deleted = Column(Boolean, default=False, nullable=False)
    deleted_by_id = Column(String(12), ForeignKey('user.id'), nullable=True)
    deleted_at = Column(DateTime, nullable=True)
    deletion_reason = Column(Text, nullable=True)
    
    # DC Protocol: Semantic file naming (Nov 29, 2025)
    download_filename = Column(String(255), nullable=True)  # Semantic download filename
    uses_new_naming = Column(Boolean, default=False, nullable=False)  # Flag for new naming convention
    
    # Timestamps
    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time, nullable=False)
    
    def __repr__(self):
        return f'<Expense {self.category}: ₹{self.amount} - {self.status} ({self.source_type})>'


class ExpenseAuditEvent(BaseModel):
    """
    Immutable audit trail for all expense actions
    Tracks RVZ supreme authority actions: create, edit, approve, delete
    """
    __tablename__ = 'expense_audit_event'
    
    id = Column(Integer, primary_key=True)
    expense_id = Column(Integer, ForeignKey('expense.id'), nullable=False)
    
    # Actor and action
    actor_id = Column(String(12), ForeignKey('user.id'), nullable=False)
    actor_role = Column(String(30), nullable=False)  # 'Finance Admin', 'RVZ ID', 'Super Admin'
    action = Column(String(30), nullable=False)  # 'create', 'edit', 'approve', 'reject', 'delete', 'restore'
    
    # Before/After state (JSON-like text storage)
    before_state = Column(Text, nullable=True)  # JSON snapshot of expense before action
    after_state = Column(Text, nullable=True)  # JSON snapshot of expense after action
    
    # Context
    action_notes = Column(Text, nullable=True)
    ip_address = Column(String(50), nullable=True)
    
    # Immutable timestamp
    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    
    def __repr__(self):
        return f'<ExpenseAuditEvent {self.action} by {self.actor_id} on Expense #{self.expense_id}>'