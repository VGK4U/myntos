"""
User model for FastAPI - Matches exact PostgreSQL database schema
MNR ID System with 943 active users and binary tree structure
"""

from sqlalchemy import Column, String, Boolean, Float, DateTime, Date, Time, Text, Integer
from sqlalchemy.orm import relationship
from sqlalchemy import ForeignKey
from app.models.base import BaseModel
from datetime import datetime
import pytz

def get_indian_time():
    """Get current datetime in Indian Standard Time (Asia/Kolkata)"""
    indian_tz = pytz.timezone('Asia/Kolkata')
    return datetime.now(indian_tz).replace(tzinfo=None)

class User(BaseModel):
    """
    User model preserving exact Flask app schema
    Primary entity in MNR ID System with 943 users
    """
    __tablename__ = 'user'
    
    # Primary Key - MNR ID System (MNR1823XXXXX format)
    id = Column(String(12), primary_key=True)  # MNR ID format
    
    # Basic User Information
    name = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, nullable=True)  # Allow NULL for duplicate cleanup
    password = Column(String(255), nullable=False)  # Hashed password
    
    # User Type & Roles (preserve exact Flask types)
    user_type = Column(String(20), default='Member', nullable=False)  # 'Member', 'Admin', 'Super Admin', 'Finance Admin' (User→Member migration 2025-11-02)
    
    # Referral System (Binary Tree Structure)
    referrer_id = Column(String(12), ForeignKey('user.id'), nullable=True)  # Sponsor/Referrer
    
    # Financial Wallets
    wallet_balance = Column(Float, default=0.0, nullable=False)
    upgrade_wallet_balance = Column(Float, default=0.0, nullable=False)  # Star/Loyal auto-upgrade
    
    # DEPRECATED: KYC-Gated Wallet System (DC Protocol Phase 1.9)
    # These columns are deprecated - use computed properties instead
    earning_wallet = Column(Float, nullable=True)  # DEPRECATED - Use earning_wallet_balance property
    withdrawable_wallet = Column(Float, nullable=True)  # DEPRECATED - Use withdrawable_wallet_balance property
    last_wallet_sync_at = Column(DateTime, nullable=True)  # Last daily sync timestamp
    
    # KYC System
    kyc_status = Column(String(30), default='Pending', nullable=False)
    
    # KYC Bypass System (Super Admin override)
    kyc_bypass_active = Column(Boolean, default=False, nullable=False)
    kyc_original_status = Column(String(20), nullable=True)
    kyc_bypassed_at = Column(DateTime, nullable=True)
    kyc_bypassed_by = Column(String(12), ForeignKey('user.id'), nullable=True)
    kyc_bypass_reason = Column(Text, nullable=True)
    
    # Coupon & Package System
    coupon_status = Column(String(20), default='Inactive', nullable=False)
    package_points = Column(Float, default=0.0, nullable=False)  # 1.0 (Platinum), 0.5 (Diamond), 0.0 (Blue/Loyal/Eligible)
    
    # Lifecycle Tracking (30-day timer system)
    coupon_status_changed_date = Column(Date, nullable=True)
    coupon_status_changed_time = Column(Time, nullable=True)
    coupon_status_changed_at = Column(DateTime, nullable=True)
    last_package_assigned_at = Column(DateTime, nullable=True)
    package_assignment_timer_reset = Column(Boolean, default=False, nullable=False)
    
    # Placement System
    placement_status = Column(String(20), default='Unplaced', nullable=False)
    
    # Ved System (Multi-level ownership)
    is_ved = Column(Boolean, default=False, nullable=False)
    ved_owner_id = Column(String(12), ForeignKey('user.id'), nullable=True)
    ved_paused = Column(Boolean, default=False, nullable=False)
    ved_disconnected_date = Column(DateTime, nullable=True)
    ved_activation_date = Column(DateTime, nullable=True)
    
    # Account Management
    account_status = Column(String(20), default='Active', nullable=False)
    registration_date = Column(DateTime, nullable=False)
    activation_date = Column(DateTime, nullable=True)  # When user's package was activated
    last_login = Column(DateTime, nullable=True)
    
    # Contact Information
    phone_number = Column(String(15), nullable=True)
    
    # Security Fields (Encrypted data)
    pan_number_encrypted = Column(Text, nullable=True)
    aadhaar_number_encrypted = Column(Text, nullable=True)
    mobile_number_encrypted = Column(Text, nullable=True)
    pan_hash = Column(String(64), nullable=True)
    aadhaar_hash = Column(String(64), nullable=True)
    mobile_hash = Column(String(64), nullable=True)
    
    # Verification Status  
    mobile_verified = Column(Boolean, default=False, nullable=False)
    mobile_verification_code_hash = Column(String, nullable=True)
    mobile_verification_expires = Column(DateTime, nullable=True)
    
    # Password Reset
    password_reset_token = Column(String(100), nullable=True)
    password_reset_expires = Column(DateTime, nullable=True)
    reset_code = Column(String, nullable=True)
    reset_code_expires = Column(DateTime, nullable=True)
    secondary_password = Column(String(255), nullable=True)
    force_password_change = Column(Boolean, default=False, nullable=False)
    temp_password = Column(String(255), nullable=True)
    temp_password_expires_at = Column(DateTime, nullable=True)
    
    # KYC Documentation
    kyc_documents_complete = Column(Boolean, default=False, nullable=False)
    profile_completion_score = Column(Integer, default=0, nullable=False)
    
    # System Fields
    user_level = Column(String, nullable=True)  # Changed to String to match database
    activation_sequence = Column(Integer, nullable=True)
    
    # Financial Tracking
    earned_total = Column(Float, default=0.0, nullable=False)
    released_total = Column(Float, default=0.0, nullable=False)
    
    # Red Coupon System
    is_red_coupon = Column(Boolean, default=False, nullable=False)
    red_coupon_locked = Column(Boolean, default=False, nullable=False)
    red_coupon_date = Column(DateTime, nullable=True)
    red_coupon_unlock_requests = Column(Integer, default=0, nullable=False)
    
    # Welcome Coupon System (DC Protocol Jan 2026)
    # Users activated with Welcome Coupon generate ₹0 income for sponsors/upliners
    # They can still earn from their own downline normally
    is_welcome_coupon = Column(Boolean, default=False, nullable=False)
    
    # Account Locking
    account_locked = Column(Boolean, default=False, nullable=False)
    
    # Personal Information
    gender = Column(String(10), nullable=True)
    certificate_date_of_birth = Column(Date, nullable=True)
    actual_date_of_birth = Column(Date, nullable=True)
    
    # KYC Unique Identifiers (for validation & uniqueness)
    aadhaar_number = Column(String(12), unique=True, nullable=True)  # 12-digit Aadhaar
    pan_number = Column(String(10), unique=True, nullable=True)  # 10-character PAN
    
    # Award System
    excluded_from_regular_awards = Column(Boolean, default=False, nullable=False)
    
    # Import/Migration Fields  
    registration_source = Column(String(50), default='web', nullable=True)
    position = Column(String(20), nullable=True)  # MANDATORY for NEW users (validated in API), nullable for legacy users
    position_id = Column(String(12), ForeignKey('user.id'), nullable=True)  # MANDATORY for NEW users (validated in API), nullable for legacy users
    position_name = Column(String, nullable=True)  
    sponsor_name = Column(String, nullable=True)
    date_of_joining = Column(Date, nullable=True)
    joining_time = Column(Time, nullable=True)
    
    # Address Information
    address_line1 = Column(String, nullable=True)
    address_line2 = Column(String, nullable=True)
    city = Column(String, nullable=True)
    state = Column(String, nullable=True)
    postal_code = Column(String, nullable=True)
    country = Column(String, nullable=True)
    
    # Bank Information
    bank_account_holder = Column(String, nullable=True)
    bank_name = Column(String, nullable=True)
    bank_account_number = Column(String, nullable=True)
    bank_ifsc_code = Column(String, nullable=True)
    bank_branch_name = Column(String, nullable=True)
    upi_id = Column(String, nullable=True)
    profile_updated_at = Column(DateTime, nullable=True)
    
    # Bank Approval Workflow (Admin → Finance Admin)
    bank_details_status = Column(String(20), default='Not Submitted', nullable=False)  # Not Submitted, Pending Admin, Pending Finance, Approved, Rejected
    bank_admin_approved_by = Column(String(12), ForeignKey('user.id'), nullable=True)
    bank_admin_approved_at = Column(DateTime, nullable=True)
    bank_finance_approved_by = Column(String(12), ForeignKey('user.id'), nullable=True)
    bank_finance_approved_at = Column(DateTime, nullable=True)
    bank_rejection_reason = Column(Text, nullable=True)
    
    # Granular KYC/Bank Verification System (DC Protocol - Individual Field Approvals)
    # KYC Field Verifications
    aadhaar_verified = Column(Boolean, default=False, nullable=False)
    pan_verified = Column(Boolean, default=False, nullable=False)
    document_verified = Column(Boolean, default=False, nullable=False)
    
    # Bank Field Verifications
    account_holder_verified = Column(Boolean, default=False, nullable=False)
    account_number_verified = Column(Boolean, default=False, nullable=False)
    ifsc_verified = Column(Boolean, default=False, nullable=False)
    bank_name_verified = Column(Boolean, default=False, nullable=False)
    branch_verified = Column(Boolean, default=False, nullable=False)
    
    # Approval Tracking - Records which staff/admin approved each field (DC Protocol Feb 2026)
    # NO FK constraints - stores staff emp_code or MNR ID (independent of any user table)
    aadhaar_verified_by = Column(String(20), nullable=True)
    pan_verified_by = Column(String(20), nullable=True)
    document_verified_by = Column(String(20), nullable=True)
    account_holder_verified_by = Column(String(20), nullable=True)
    account_number_verified_by = Column(String(20), nullable=True)
    ifsc_verified_by = Column(String(20), nullable=True)
    bank_name_verified_by = Column(String(20), nullable=True)
    branch_verified_by = Column(String(20), nullable=True)
    
    # Approval Timestamps - When each field was verified
    aadhaar_verified_at = Column(DateTime, nullable=True)
    pan_verified_at = Column(DateTime, nullable=True)
    document_verified_at = Column(DateTime, nullable=True)
    account_holder_verified_at = Column(DateTime, nullable=True)
    account_number_verified_at = Column(DateTime, nullable=True)
    ifsc_verified_at = Column(DateTime, nullable=True)
    bank_name_verified_at = Column(DateTime, nullable=True)
    branch_verified_at = Column(DateTime, nullable=True)
    
    # DC Protocol Feb 2026: Validation Tracking (Staff validates → Accounts approves)
    # Separate from approval tracking - tracks first-level validation by staff
    aadhaar_validated = Column(Boolean, default=False, nullable=False)
    aadhaar_validated_by = Column(String(20), nullable=True)
    aadhaar_validated_at = Column(DateTime, nullable=True)
    
    pan_validated = Column(Boolean, default=False, nullable=False)
    pan_validated_by = Column(String(20), nullable=True)
    pan_validated_at = Column(DateTime, nullable=True)
    
    document_validated = Column(Boolean, default=False, nullable=False)
    document_validated_by = Column(String(20), nullable=True)
    document_validated_at = Column(DateTime, nullable=True)
    
    account_holder_validated = Column(Boolean, default=False, nullable=False)
    account_holder_validated_by = Column(String(20), nullable=True)
    account_holder_validated_at = Column(DateTime, nullable=True)
    
    account_number_validated = Column(Boolean, default=False, nullable=False)
    account_number_validated_by = Column(String(20), nullable=True)
    account_number_validated_at = Column(DateTime, nullable=True)
    
    ifsc_validated = Column(Boolean, default=False, nullable=False)
    ifsc_validated_by = Column(String(20), nullable=True)
    ifsc_validated_at = Column(DateTime, nullable=True)
    
    bank_name_validated = Column(Boolean, default=False, nullable=False)
    bank_name_validated_by = Column(String(20), nullable=True)
    bank_name_validated_at = Column(DateTime, nullable=True)
    
    branch_validated = Column(Boolean, default=False, nullable=False)
    branch_validated_by = Column(String(20), nullable=True)
    branch_validated_at = Column(DateTime, nullable=True)
    
    # Referral Bonus System
    referral_bonus_eligible = Column(Boolean, default=False, nullable=False)
    first_referral_bonus_paid = Column(Boolean, default=False, nullable=False)
    first_matching_achieved = Column(Boolean, default=False, nullable=False)
    referral_bonus_count = Column(Integer, default=0, nullable=False)  # Track bonuses received by referrer (max 2 for Diamond/Blue/Loyal)
    
    # Terms and Conditions Acceptance Tracking
    accepted_terms_version = Column(String(10), nullable=True)  # e.g., "1.0", "2.0"
    acceptance_timestamp = Column(DateTime, nullable=True)  # When user accepted terms
    
    def __repr__(self):
        return f'<User {self.id}: {self.name} ({self.email})>'
    
    def is_admin(self):
        """DEPRECATED: MNR admin types removed. Admin operations are staff-only. Always returns False."""
        return False
    
    def is_super_admin(self):
        """DEPRECATED: MNR admin types removed. Admin operations are staff-only. Always returns False."""
        return False
    
    def get_package_type(self):
        """
        Get user's package type based on package_points
        Maps to decimal point system: Platinum=1.0, Diamond=0.5, Star/Loyal=0.0
        DC Protocol (Jan 2026): Welcome Coupon users return 'Welcome Coupon' regardless of points
        """
        if getattr(self, 'is_welcome_coupon', False):
            return 'Welcome Coupon'
        
        points = self.package_points if self.package_points else 0
        
        if points >= 1.0:
            return 'Platinum'
        elif points >= 0.5:
            return 'Diamond'
        elif points > 0:
            return 'Star/Loyal'
        else:
            return 'Eligible'
    
    def get_points(self):
        """
        Get user's package points value
        Returns actual points: 15000 (Platinum), 7500 (Diamond), 1000 (Blue), 500 (Loyal)
        """
        return self.package_points if self.package_points else 0
    
    def set_secondary_password(self, password: str):
        """Set and hash the secondary password for Super Admin"""
        from app.core.security import SecurityManager as _SM
        self.secondary_password = _SM.get_password_hash(password)
    
    def check_secondary_password(self, password: str) -> bool:
        """Check if provided secondary password matches stored hash"""
        from werkzeug.security import check_password_hash
        if not self.secondary_password:
            return False
        return check_password_hash(self.secondary_password, password)
    
    def has_secondary_password(self) -> bool:
        """Check if user has a secondary password set"""
        return self.secondary_password is not None and self.secondary_password != ''
    
    def clear_secondary_password(self):
        """Clear the secondary password"""
        self.secondary_password = None
    
    # DC Protocol Phase 1.9: Computed Properties (Source of Truth)
    @property
    def earning_wallet_balance(self):
        """
        DC Protocol Phase 1.9: Compute earning wallet from pending_income
        Source: pending_income WHERE verification_status IN ('Pending', 'Admin Verified', ...)
        """
        from sqlalchemy import text
        from app.core.database import get_db
        
        db = next(get_db())
        try:
            result = db.execute(text("""
                SELECT COALESCE(earning_wallet, 0) as balance
                FROM user_earning_wallet_balance
                WHERE user_id = :user_id
            """), {"user_id": self.id}).fetchone()
            return float(result[0]) if result else 0.0
        finally:
            db.close()
    
    @property
    def withdrawable_wallet_balance(self):
        """
        DC Protocol Phase 1.9: Compute withdrawable wallet from pending_income - withdrawals
        Source: pending_income (Paid) - withdrawal_request (Completed, Completed)
        """
        from sqlalchemy import text
        from app.core.database import get_db
        
        db = next(get_db())
        try:
            result = db.execute(text("""
                SELECT COALESCE(withdrawable_wallet, 0) as balance
                FROM user_withdrawable_wallet_balance
                WHERE user_id = :user_id
            """), {"user_id": self.id}).fetchone()
            return float(result[0]) if result else 0.0
        finally:
            db.close()