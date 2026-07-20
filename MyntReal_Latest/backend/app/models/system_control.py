"""
System Control models for RVZ ID functionality
Preserves Flask SystemControl and AppSettings models
"""

from sqlalchemy import Column, String, Boolean, DateTime, Text, Integer, Float, Index
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
from app.models.base import BaseModel
from datetime import datetime
from typing import Dict, Any, Optional

class SystemControl(BaseModel):
    """
    System Control model for RVZ ID feature management
    Allows pausing/resuming system features during maintenance/testing
    """
    __tablename__ = 'system_control'
    
    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Feature identification
    feature_name = Column(String, nullable=False, unique=True)  # e.g., 'whatsapp_otp', 'email_notifications'
    
    # Control status (matches actual database structure)
    is_paused = Column(Boolean, default=False, nullable=False)  # False = active, True = paused
    pause_reason = Column(String, nullable=True, default="Development/Testing")
    controlled_by_user_id = Column(String, nullable=False)
    
    # Tracking (matches actual database structure)
    paused_at = Column(DateTime, nullable=True)
    resumed_at = Column(DateTime, nullable=True)
    last_action = Column(String, nullable=False, default="created")
    
    # Additional fields from actual database
    settings_data = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    @classmethod
    def get_feature_status(cls, db: Session, feature_name: str) -> bool:
        """Get current status of a system feature (True = active, False = paused)"""
        try:
            feature = db.query(cls).filter(cls.feature_name == feature_name).first()
            if feature:
                return not feature.is_paused  # Convert: is_paused=False means active=True
            else:
                # Create default active feature if not exists
                new_feature = cls(
                    feature_name=feature_name,
                    is_paused=False,  # False = active
                    controlled_by_user_id="MNR182364369",  # Use RVZ user ID
                    last_action="created"
                )
                db.add(new_feature)
                db.commit()
                return True
        except Exception as e:
            print(f"Error getting feature status: {e}")
            return True  # Default to active if error
    
    @classmethod
    def pause_feature(cls, db: Session, feature_name: str, paused_by: str, reason: str = None) -> bool:
        """Pause a system feature"""
        try:
            feature = db.query(cls).filter(cls.feature_name == feature_name).first()
            if not feature:
                # Create feature if it doesn't exist, then pause it
                feature = cls(
                    feature_name=feature_name,
                    is_paused=False,  # Start as active
                    controlled_by_user_id=paused_by,
                    last_action="created"
                )
                db.add(feature)
                db.commit()
                db.refresh(feature)
            
            # Pause the feature
            feature.is_paused = True  # True = paused
            feature.controlled_by_user_id = paused_by
            feature.paused_at = datetime.utcnow()
            feature.pause_reason = reason or f"Paused by RVZ ID {paused_by}"
            feature.last_action = "paused"
            feature.updated_at = datetime.utcnow()
            
            db.commit()
            return True
            
        except Exception as e:
            print(f"Error pausing feature: {e}")
            db.rollback()
            return False
    
    @classmethod 
    def resume_feature(cls, db: Session, feature_name: str, resumed_by: str, reason: str = None) -> bool:
        """Resume a system feature"""
        try:
            feature = db.query(cls).filter(cls.feature_name == feature_name).first()
            if not feature:
                # Create feature if it doesn't exist (default active)
                feature = cls(
                    feature_name=feature_name,
                    is_paused=False,  # False = active
                    controlled_by_user_id=resumed_by,
                    last_action="created"
                )
                db.add(feature)
                db.commit()
                return True
            
            # Resume the feature
            feature.is_paused = False  # False = active
            feature.controlled_by_user_id = resumed_by
            feature.resumed_at = datetime.utcnow()
            feature.pause_reason = reason or f"Resumed by RVZ ID {resumed_by}"
            feature.last_action = "resumed"
            feature.updated_at = datetime.utcnow()
            
            db.commit()
            return True
            
        except Exception as e:
            print(f"Error resuming feature: {e}")
            db.rollback()
            return False
    
    @classmethod
    def get_all_features_status(cls, db: Session) -> Dict[str, bool]:
        """Get status of all system features (True = active, False = paused)"""
        try:
            # Define the core system features
            core_features = [
                'whatsapp_otp',
                'email_notifications', 
                'income_calculations',
                'bonanza_system',
                'kyc_processing',
                'payout_system'
            ]
            
            feature_status = {}
            
            for feature_name in core_features:
                feature = db.query(cls).filter(cls.feature_name == feature_name).first()
                if feature:
                    feature_status[feature_name] = not feature.is_paused  # Convert to active status
                else:
                    # Create default active feature
                    new_feature = cls(
                        feature_name=feature_name,
                        is_paused=False,  # False = active
                        controlled_by_user_id="MNR182364369",  # Use RVZ user ID
                        last_action="created"
                    )
                    db.add(new_feature)
                    feature_status[feature_name] = True
            
            db.commit()
            return feature_status
            
        except Exception as e:
            print(f"Error getting all features status: {e}")
            # Return default active status for all features
            return {
                'whatsapp_otp': True,
                'email_notifications': True, 
                'income_calculations': True,
                'bonanza_system': True,
                'kyc_processing': True,
                'payout_system': True
            }

class AppSettings(BaseModel):
    """
    Application Settings model for RVZ ID system configuration
    Preserves Flask AppSettings functionality
    """
    __tablename__ = 'app_settings'
    
    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # ========== FINANCIAL DEDUCTIONS (Standard for all income) ==========
    admin_deduction_rate = Column(Float, default=8.0, nullable=False)  # 8% admin deduction
    tds_deduction_rate = Column(Float, default=2.0, nullable=False)    # 2% TDS deduction
    
    # ========== GURU DAKSHINA ==========
    guru_dakshina_rate = Column(Float, default=2.0, nullable=False)  # 2% paid to referrer
    
    # ========== DAILY INCOME CEILING ==========
    daily_income_ceiling = Column(Float, default=50000.0, nullable=False)  # ₹50,000 daily limit
    
    # ========== MINIMUM WITHDRAWAL ==========
    minimum_withdrawal_amount = Column(Float, default=1000.0, nullable=False)  # ₹1,000 minimum
    
    # ========== PACKAGE POINTS (Matching Points) ==========
    package_points_platinum = Column(Float, default=1.0, nullable=False)  # 1.0 points
    package_points_diamond = Column(Float, default=0.5, nullable=False)   # 0.5 points
    package_points_blue = Column(Float, default=0.0, nullable=False)      # 0 points
    package_points_loyal = Column(Float, default=0.0, nullable=False)     # 0 points
    
    # ========== DIRECT REFERRAL BONUSES (Referrer gets when downline activates) ==========
    direct_referral_platinum = Column(Float, default=3000.0, nullable=False)  # ₹3,000
    direct_referral_diamond = Column(Float, default=1500.0, nullable=False)   # ₹1,500
    direct_referral_blue = Column(Float, default=0.0, nullable=False)         # ₹0
    direct_referral_loyal = Column(Float, default=0.0, nullable=False)        # ₹0
    
    # ========== MATCHING INCOME RATE (Fixed per 1:1 point match) ==========
    matching_income_per_point = Column(Float, default=2000.0, nullable=False)  # ₹2,000 per point match
    
    # ========== VED INCOME RATES (Paid to Ved member on downline activation) ==========
    ved_income_platinum = Column(Float, default=1000.0, nullable=False)  # ₹1,000 for Platinum
    ved_income_diamond = Column(Float, default=500.0, nullable=False)    # ₹500 for Diamond
    ved_income_blue = Column(Float, default=0.0, nullable=False)         # ₹0 for Blue
    ved_income_loyal = Column(Float, default=0.0, nullable=False)        # ₹0 for Loyal
    
    # ========== WALLET SPLIT RATIOS ==========
    # Platinum: 100% withdrawable, 0% earning
    wallet_split_platinum_withdrawable = Column(Float, default=1.00, nullable=False)
    wallet_split_platinum_earning = Column(Float, default=0.00, nullable=False)
    # Others (Star, Loyal, Diamond): 50% withdrawable, 50% earning
    wallet_split_default_withdrawable = Column(Float, default=0.50, nullable=False)
    wallet_split_default_earning = Column(Float, default=0.50, nullable=False)
    
    # ========== LEGACY FIELDS (Keep for backward compatibility) ==========
    direct_referral_active_rate = Column(Integer, default=50, nullable=True)
    matching_referral_rate = Column(Integer, default=100, nullable=True) 
    pair_matching_rate = Column(Integer, default=100, nullable=True)
    ved_income_rate = Column(Integer, default=200, nullable=True)
    default_referrer_id = Column(String(12), nullable=True, default='MNR182371007')
    
    # Allowance Settings
    allowance_7_in_30_days_active = Column(Boolean, default=True, nullable=True)
    allowance_7_in_30_days_amount = Column(Integer, default=500, nullable=True)
    allowance_20_20_monthly_active = Column(Boolean, default=True, nullable=True)
    allowance_20_20_monthly_amount = Column(Integer, default=1000, nullable=True)
    
    # Automatic Withdrawal Settings
    max_withdrawal_limit = Column(Float, default=50000.0, nullable=False)
    withdrawal_buffer_amount = Column(Float, default=1000.0, nullable=False)
    auto_withdrawal_enabled = Column(Boolean, default=True, nullable=False)
    
    # RVZ ID KYC/Banking Skip Settings (DC Protocol)
    skip_kyc_requirement = Column(Boolean, default=False, nullable=False)
    skip_bank_requirement = Column(Boolean, default=False, nullable=False)
    
    # Popup Control Settings (matches actual database structure)
    coupon_popup_enabled = Column(Boolean, default=True, nullable=False)
    popup_config_updated_at = Column(DateTime, nullable=True)
    popup_config_updated_by = Column(String(12), nullable=True)
    mail_popup_enabled = Column(Boolean, default=True, nullable=False)
    banner_popup_enabled = Column(Boolean, default=True, nullable=False)
    whatsapp_popup_enabled = Column(Boolean, default=True, nullable=False)
    message_popup_enabled = Column(Boolean, default=True, nullable=False)
    system_alert_popup_enabled = Column(Boolean, default=True, nullable=False)
    
    # Banner Type Controls (NEW - added for comprehensive banner management)
    birthday_banner_enabled = Column(Boolean, default=True, nullable=False)
    top_performers_banner_enabled = Column(Boolean, default=True, nullable=False)
    custom_banners_enabled = Column(Boolean, default=True, nullable=False)
    image_banners_enabled = Column(Boolean, default=True, nullable=False)

    # ─────────────────────────────────────────────────────────────────────
    # VGK4U Member Parity — Phase 1 (Read-Only Modules)
    # DC Protocol: each MNR module has a paired VGK4U toggle. Default = TRUE so
    # the new VGK4U Members tab appears in every staff admin page out of the box,
    # but staff *menu* defaults remain Zero-Access (handled by sidebar registry).
    # ─────────────────────────────────────────────────────────────────────
    birthdays_vgk4u_enabled = Column(Boolean, default=True, nullable=False)
    top_earners_vgk4u_enabled = Column(Boolean, default=True, nullable=False)
    awards_vgk4u_enabled = Column(Boolean, default=True, nullable=False)
    daywise_income_vgk4u_enabled = Column(Boolean, default=True, nullable=False)
    income_types_vgk4u_enabled = Column(Boolean, default=True, nullable=False)
    direct_summary_vgk4u_enabled = Column(Boolean, default=True, nullable=False)
    matching_summary_vgk4u_enabled = Column(Boolean, default=True, nullable=False)
    guru_summary_vgk4u_enabled = Column(Boolean, default=True, nullable=False)
    ved_summary_vgk4u_enabled = Column(Boolean, default=True, nullable=False)
    ev_benefits_vgk4u_enabled = Column(Boolean, default=True, nullable=False)
    ev_discount_vgk4u_enabled = Column(Boolean, default=True, nullable=False)
    franchise_earnings_vgk4u_enabled = Column(Boolean, default=True, nullable=False)
    insurance_vgk4u_enabled = Column(Boolean, default=True, nullable=False)
    training_vgk4u_enabled = Column(Boolean, default=True, nullable=False)
    coupon_benefits_vgk4u_enabled = Column(Boolean, default=True, nullable=False)
    my_submissions_vgk4u_enabled = Column(Boolean, default=True, nullable=False)

    # ─────────────────────────────────────────────────────────────────────
    # VGK4U Member Parity — Phase 2 (Write-Flow Modules) — Task #34
    # DC Protocol: Zero-Default Access — every Phase-2 write toggle defaults
    # to FALSE. Super-Admin must explicitly enable each module before VGK4U
    # members can submit/edit. Migration column DDL is in main.py
    # `add_system_controls_vgk4u_phase2_flags`.
    # ─────────────────────────────────────────────────────────────────────
    feedback_vgk4u_enabled = Column(Boolean, default=False, nullable=False)
    announcements_vgk4u_enabled = Column(Boolean, default=False, nullable=False)
    kyc_vgk4u_enabled = Column(Boolean, default=False, nullable=False)
    bank_vgk4u_enabled = Column(Boolean, default=False, nullable=False)
    coupon_transfer_vgk4u_enabled = Column(Boolean, default=False, nullable=False)
    profile_edit_vgk4u_enabled = Column(Boolean, default=False, nullable=False)
    settings_vgk4u_enabled = Column(Boolean, default=False, nullable=False)

    # Terms & Conditions Content (RVZ ID Editable)
    terms_and_conditions_content = Column(Text, nullable=True, default="""
<h4>Terms & Conditions</h4>
<p>Welcome to our MNR platform. Please read these terms carefully.</p>
<ol>
    <li>By using this platform, you agree to comply with all applicable laws and regulations.</li>
    <li>All package purchases are final and non-refundable.</li>
    <li>Income calculations are based on your team's performance and package activation.</li>
    <li>KYC verification is mandatory for withdrawals.</li>
    <li>The company reserves the right to modify these terms at any time.</li>
    <li><strong>Important Note on Earnings:</strong> All earnings and withdrawals displayed in MNR2.0 are based on the updated calculation method and are shown for reference purposes only. These figures do not represent any financial commitments. Only the new earnings generated from 23rd October onwards will be officially payable.</li>
</ol>
<p>For support, please contact your upline or admin.</p>
    """)
    tc_version = Column(String(10), default='1.0', nullable=False)
    tc_last_updated = Column(DateTime, nullable=True)
    tc_updated_by = Column(String(12), nullable=True)
    tc_max_displays = Column(Integer, default=3, nullable=False)  # How many times to show T&C popup to new users
    
    @classmethod
    def get_popup_settings(cls, db: Session) -> Dict[str, bool]:
        """Get all popup settings from database"""
        # Get or create the settings record
        settings = db.query(cls).first()
        if not settings:
            # Create default settings if none exist
            settings = cls()
            db.add(settings)
            db.commit()
            db.refresh(settings)
        
        return {
            'coupon_popup_enabled': bool(settings.coupon_popup_enabled),
            'mail_popup_enabled': bool(settings.mail_popup_enabled),
            'banner_popup_enabled': bool(settings.banner_popup_enabled),
            'whatsapp_popup_enabled': bool(settings.whatsapp_popup_enabled),
            'message_popup_enabled': bool(settings.message_popup_enabled),
            'system_alert_popup_enabled': bool(settings.system_alert_popup_enabled),
            'birthday_banner_enabled': bool(settings.birthday_banner_enabled),
            'top_performers_banner_enabled': bool(settings.top_performers_banner_enabled),
            'custom_banners_enabled': bool(settings.custom_banners_enabled),
            'image_banners_enabled': bool(settings.image_banners_enabled)
        }
    
    @classmethod
    def update_popup_setting(cls, db: Session, popup_type: str, enabled: bool, modified_by: str) -> bool:
        """Update specific popup setting in database"""
        from datetime import datetime
        
        try:
            # Get or create the settings record
            settings = db.query(cls).first()
            if not settings:
                settings = cls()
                db.add(settings)
                db.commit()
                db.refresh(settings)
            
            # Map popup type to database field
            popup_field_map = {
                'coupon': 'coupon_popup_enabled',
                'mail': 'mail_popup_enabled', 
                'banner': 'banner_popup_enabled',
                'whatsapp': 'whatsapp_popup_enabled',
                'message': 'message_popup_enabled',
                'system_alert': 'system_alert_popup_enabled',
                'birthday_banner': 'birthday_banner_enabled',
                'top_performers': 'top_performers_banner_enabled',
                'custom_banners': 'custom_banners_enabled',
                'image_banners': 'image_banners_enabled'
            }
            
            if popup_type not in popup_field_map:
                return False
            
            # Update the specific popup setting
            field_name = popup_field_map[popup_type]
            setattr(settings, field_name, enabled)
            
            # Update tracking fields (using fields that actually exist)
            settings.popup_config_updated_by = modified_by
            settings.popup_config_updated_at = datetime.utcnow()
            
            db.commit()
            return True
            
        except Exception as e:
            print(f"Error updating popup setting: {e}")
            return False
    
    @classmethod
    def get_all_settings(cls, db: Session) -> 'AppSettings':
        """Get or create the settings record"""
        settings = db.query(cls).first()
        if not settings:
            settings = cls()
            db.add(settings)
            db.commit()
            db.refresh(settings)
        return settings
    
    @classmethod
    def get_deduction_rates(cls, db: Session) -> Dict[str, float]:
        """Get admin and TDS deduction rates"""
        settings = cls.get_all_settings(db)
        return {
            'admin_deduction_rate': float(settings.admin_deduction_rate),
            'tds_deduction_rate': float(settings.tds_deduction_rate),
            'total_deduction_rate': float(settings.admin_deduction_rate + settings.tds_deduction_rate)
        }
    
    @classmethod
    def get_package_points(cls, db: Session) -> Dict[str, float]:
        """Get package points (matching multipliers)"""
        settings = cls.get_all_settings(db)
        return {
            'Platinum': float(settings.package_points_platinum),
            'Diamond': float(settings.package_points_diamond),
            'Blue': float(settings.package_points_blue),
            'Loyal': float(settings.package_points_loyal)
        }
    
    @classmethod
    def get_direct_referral_bonuses(cls, db: Session) -> Dict[str, float]:
        """Get direct referral bonuses (what referrer receives)"""
        settings = cls.get_all_settings(db)
        return {
            'Platinum': float(settings.direct_referral_platinum),
            'Diamond': float(settings.direct_referral_diamond),
            'Blue': float(settings.direct_referral_blue),
            'Loyal': float(settings.direct_referral_loyal)
        }
    
    @classmethod
    def get_matching_income_rate(cls, db: Session) -> float:
        """Get matching income rate (fixed per 1:1 point match)"""
        settings = cls.get_all_settings(db)
        return float(settings.matching_income_per_point)
    
    @classmethod
    def get_ved_income_rates(cls, db: Session) -> Dict[str, float]:
        """Get Ved income rates by package"""
        settings = cls.get_all_settings(db)
        return {
            'Platinum': float(settings.ved_income_platinum),
            'Diamond': float(settings.ved_income_diamond),
            'Blue': float(settings.ved_income_blue),
            'Loyal': float(settings.ved_income_loyal)
        }
    
    @classmethod
    def get_wallet_split_ratios(cls, db: Session) -> Dict[str, Dict[str, float]]:
        """Get wallet split ratios by package"""
        settings = cls.get_all_settings(db)
        return {
            'Platinum': {
                'withdrawable': float(settings.wallet_split_platinum_withdrawable),
                'earning': float(settings.wallet_split_platinum_earning)
            },
            'default': {
                'withdrawable': float(settings.wallet_split_default_withdrawable),
                'earning': float(settings.wallet_split_default_earning)
            }
        }
    
    @classmethod
    def get_financial_rates(cls, db: Session) -> Dict[str, int]:
        """Get current financial rates from database (legacy compatibility)"""
        settings = cls.get_all_settings(db)
        return {
            'direct_referral_active_rate': int(settings.direct_referral_active_rate),
            'pair_matching_rate': int(settings.pair_matching_rate),
            'ved_income_rate': int(settings.ved_income_rate)
        }
    
    @classmethod
    def update_financial_rates(cls, db: Session, rates: Dict[str, int], modified_by: str) -> bool:
        """Update financial rates in database"""
        from datetime import datetime
        
        try:
            # Get or create the settings record
            settings = db.query(cls).first()
            if not settings:
                settings = cls()
                db.add(settings)
                db.commit()
                db.refresh(settings)
            
            # Update rates if provided
            if 'direct_referral_active_rate' in rates:
                settings.direct_referral_active_rate = rates['direct_referral_active_rate']
            if 'pair_matching_rate' in rates:
                settings.pair_matching_rate = rates['pair_matching_rate']
            if 'ved_income_rate' in rates:
                settings.ved_income_rate = rates['ved_income_rate']
            
            # Note: Tracking fields not available in current database schema
            # Financial rate changes are logged at API level
            
            db.commit()
            return True
            
        except Exception as e:
            print(f"Error updating financial rates: {e}")
            return False
    
    @classmethod
    def get_withdrawal_settings(cls, db: Session) -> Dict[str, Any]:
        """Get automatic withdrawal settings from database"""
        settings = db.query(cls).first()
        if not settings:
            settings = cls()
            db.add(settings)
            db.commit()
            db.refresh(settings)
        
        return {
            'max_withdrawal_limit': float(settings.max_withdrawal_limit),
            'withdrawal_buffer_amount': float(settings.withdrawal_buffer_amount),
            'auto_withdrawal_enabled': bool(settings.auto_withdrawal_enabled)
        }
    
    @classmethod
    def get_kyc_skip_settings(cls, db: Session) -> Dict[str, bool]:
        """Get KYC and Bank skip settings (DC Protocol - RVZ ID controlled)"""
        settings = cls.get_all_settings(db)
        return {
            'skip_kyc_requirement': bool(settings.skip_kyc_requirement),
            'skip_bank_requirement': bool(settings.skip_bank_requirement)
        }
    
    @classmethod
    def update_kyc_skip_settings(cls, db: Session, skip_kyc: bool = None, skip_bank: bool = None, modified_by: str = None) -> bool:
        """Update KYC and Bank skip settings (RVZ ID only)"""
        try:
            settings = db.query(cls).first()
            if not settings:
                settings = cls()
                db.add(settings)
                db.commit()
                db.refresh(settings)
            
            if skip_kyc is not None:
                settings.skip_kyc_requirement = skip_kyc
            if skip_bank is not None:
                settings.skip_bank_requirement = skip_bank
            
            db.commit()
            return True
        except Exception as e:
            print(f"Error updating KYC skip settings: {e}")
            return False
    
    @classmethod
    def update_withdrawal_settings(cls, db: Session, settings_data: Dict[str, Any], modified_by: str) -> bool:
        """Update automatic withdrawal settings in database"""
        try:
            settings = db.query(cls).first()
            if not settings:
                settings = cls()
                db.add(settings)
                db.commit()
                db.refresh(settings)
            
            if 'max_withdrawal_limit' in settings_data:
                settings.max_withdrawal_limit = float(settings_data['max_withdrawal_limit'])
            if 'withdrawal_buffer_amount' in settings_data:
                settings.withdrawal_buffer_amount = float(settings_data['withdrawal_buffer_amount'])
            if 'auto_withdrawal_enabled' in settings_data:
                settings.auto_withdrawal_enabled = bool(settings_data['auto_withdrawal_enabled'])
            
            db.commit()
            return True
            
        except Exception as e:
            print(f"Error updating withdrawal settings: {e}")
            return False

class CustomRole(BaseModel):
    """
    Custom Role model for RVZ ID role management
    """
    __tablename__ = 'custom_roles'
    
    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Role details
    role_name = Column(String(50), nullable=False, unique=True)
    role_description = Column(Text, nullable=True)
    role_level = Column(Integer, nullable=False)  # Hierarchy level
    
    # Permissions (JSON or individual boolean fields)
    can_view_users = Column(Boolean, default=False, nullable=False)
    can_edit_users = Column(Boolean, default=False, nullable=False)
    can_manage_finances = Column(Boolean, default=False, nullable=False)
    can_approve_kyc = Column(Boolean, default=False, nullable=False)
    can_manage_bonanza = Column(Boolean, default=False, nullable=False)
    can_system_control = Column(Boolean, default=False, nullable=False)
    
    # Tracking
    created_by = Column(String(12), nullable=False)  # RVZ ID who created it
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_by = Column(String(12), nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False)


class TermsAndConditionsVersion(BaseModel):
    """
    Terms & Conditions Version Management Model
    Allows RVZ to maintain multiple T&C versions with version control
    """
    __tablename__ = 'terms_and_conditions_versions'
    
    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Version details
    version = Column(String(10), nullable=False, unique=True)  # v1.0, v1.1, v2.0
    content = Column(Text, nullable=False)  # HTML content
    
    # Status - Only one version can be active at a time
    is_active = Column(Boolean, default=False, nullable=False)
    
    # Creation tracking
    created_by = Column(String(12), nullable=False)  # RVZ user_id who created this version
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Activation tracking
    activated_at = Column(DateTime, nullable=True)  # When this version was set as active
    activated_by = Column(String(12), nullable=True)  # RVZ user_id who activated this version
    
    # Optional metadata
    notes = Column(Text, nullable=True)  # Optional notes about this version
    source_version = Column(String(10), nullable=True)  # Which version this was copied from
    
    # Settings (inherited from app_settings for compatibility)
    max_displays = Column(Integer, default=3, nullable=False)  # How many times to show T&C to new users

    # DC Protocol Mar 2026: Platform routing — 'MNR' | 'VGK' | 'ALL'
    platform_type = Column(String(10), default='MNR', nullable=False, server_default='MNR')

    __table_args__ = (
        # One active version per platform_type (MNR, VGK, ALL each get their own active)
        Index('idx_one_active_per_platform', 'platform_type',
              unique=True, postgresql_where=text('is_active = TRUE')),
    )
    
    @classmethod
    def get_active_version(cls, db: Session) -> Optional['TermsAndConditionsVersion']:
        """Get the currently active T&C version"""
        return db.query(cls).filter(cls.is_active == True).first()
    
    @classmethod
    def create_version(cls, db: Session, version: str, content: str, created_by: str,
                      source_version: str = None, notes: str = None,
                      platform_type: str = 'MNR') -> 'TermsAndConditionsVersion':
        """Create a new T&C version (inactive by default)"""
        try:
            new_version = cls(
                version=version,
                content=content,
                created_by=created_by,
                source_version=source_version,
                notes=notes,
                is_active=False,
                platform_type=platform_type or 'MNR',
            )
            db.add(new_version)
            db.commit()
            db.refresh(new_version)
            return new_version
        except Exception as e:
            db.rollback()
            raise e
    
    @classmethod
    def activate_version(cls, db: Session, version: str, activated_by: str) -> bool:
        """
        Activate a specific version and deactivate others on the same platform.
        Returns True on success, False on failure.
        """
        try:
            target_version = db.query(cls).filter(cls.version == version).first()
            if not target_version:
                return False

            # Deactivate only versions with the same platform_type
            db.query(cls).filter(
                cls.platform_type == target_version.platform_type
            ).update({'is_active': False})

            target_version.is_active = True
            target_version.activated_at = datetime.utcnow()
            target_version.activated_by = activated_by

            db.commit()
            return True
        except Exception as e:
            db.rollback()
            print(f"Error activating version: {e}")
            return False
    
    @classmethod
    def get_all_versions(cls, db: Session) -> list:
        """Get all T&C versions, sorted by creation date (newest first)"""
        return db.query(cls).order_by(cls.created_at.desc()).all()
    
    @classmethod
    def migrate_from_app_settings(cls, db: Session) -> bool:
        """
        One-time migration: Copy current T&C from app_settings to v1.0
        Only runs if no versions exist yet
        """
        try:
            # Check if any versions already exist
            existing = db.query(cls).first()
            if existing:
                print("✅ T&C versions already exist, skipping migration")
                return True
            
            # Get current T&C from app_settings
            settings = db.query(AppSettings).first()
            if not settings or not settings.terms_and_conditions_content:
                print("⚠️ No T&C content in app_settings, creating default v1.0")
                content = "<h4>Terms & Conditions</h4><p>Please update this content.</p>"
                version = "v1.0"
                created_by = "MNR182364369"  # Default RVZ ID
            else:
                content = settings.terms_and_conditions_content
                version = settings.tc_version or "v1.0"
                created_by = settings.tc_updated_by or "MNR182364369"
            
            # Create v1.0 as active
            v1 = cls(
                version=version,
                content=content,
                created_by=created_by,
                is_active=True,
                activated_at=datetime.utcnow(),
                activated_by=created_by,
                notes="Migrated from app_settings table"
            )
            db.add(v1)
            db.commit()
            
            print(f"✅ Successfully migrated T&C to version {version}")
            return True
            
        except Exception as e:
            db.rollback()
            print(f"❌ Error migrating T&C: {e}")
            return False