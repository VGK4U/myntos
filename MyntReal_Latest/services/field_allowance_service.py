"""
Field Allowance Service - Centralized Field Allowance calculations and data management

This service provides consistent data across all Field Allowance components:
- Summary statistics (top section)
- Quick status information  
- Monthly performance calculations
- Eligibility tracking

ARCHITECTURE: Single source of truth for all Field Allowance related data
"""

from datetime import datetime, timedelta
from collections import defaultdict
from sqlalchemy import text, func, and_, or_
import calendar


class FieldAllowanceDTO:
    """Data Transfer Object for Field Allowance information"""
    
    def __init__(self):
        # Summary Stats (for top section)
        self.active_direct_referrals = 0
        self.active_matching_referrals = 0
        self.left_side_active = 0
        self.right_side_active = 0
        
        # Quick Status (unified data)
        self.total_direct_referrals = 0
        self.days_remaining = 0
        self.scheme_status = "None"
        self.scheme_monthly_amount = 0
        self.scheme_tenure_months = 0
        
        # Monthly Performance
        self.monthly_performance = []  # List of monthly data
        
        # Eligibility
        self.field_allowance_eligible = False
        self.car_allowance_eligible = False
        self.eligibility_message = ""


class FieldAllowanceService:
    """Centralized Field Allowance Service"""
    
    def __init__(self, db, user_model, placement_model, transaction_model, 
                 allowance_scheme_model, super_admin_settings_model):
        self.db = db
        self.User = user_model
        self.Placement = placement_model
        self.Transaction = transaction_model
        self.AllowanceSchemeSelector = allowance_scheme_model
        self.SuperAdminSettings = super_admin_settings_model
    
    def get_field_allowance_data(self, user_id):
        """
        Get complete Field Allowance data for a user
        
        Returns: FieldAllowanceDTO with all necessary data
        """
        dto = FieldAllowanceDTO()
        
        try:
            # Get user
            user = self.User.query.get(user_id)
            if not user:
                return dto
            
            # 1. Calculate Summary Stats (consistent with active-only filters)
            self._populate_summary_stats(dto, user_id)
            
            # 2. Calculate Quick Status (unified approach)
            self._populate_quick_status(dto, user_id)
            
            # 3. Calculate Monthly Performance
            self._populate_monthly_performance(dto, user_id)
            
            # 4. Check Eligibility
            self._populate_eligibility(dto, user_id)
            
            return dto
            
        except Exception as e:
            print(f"Error in FieldAllowanceService.get_field_allowance_data: {e}")
            return dto
    
    def _populate_summary_stats(self, dto, user_id):
        """Populate summary statistics with consistent filters"""
        try:
            # Active Direct Referrals (KYC not required, just Active status)
            active_direct = self.User.query.filter(
                self.User.referrer_id == user_id,
                self.User.coupon_status == 'Active'
            ).count()
            dto.active_direct_referrals = active_direct
            
            # Active Matching Referrals (KYC + Active required for matching)
            matching_query = self.db.session.execute(text("""
                SELECT 
                    COUNT(CASE WHEN p.side = 'left' AND u.coupon_status = 'Active' AND u.kyc_status = 'Approved' THEN 1 END) as left_active,
                    COUNT(CASE WHEN p.side = 'right' AND u.coupon_status = 'Active' AND u.kyc_status = 'Approved' THEN 1 END) as right_active
                FROM placement p
                JOIN "user" u ON u.id = p.child_id
                WHERE p.parent_id = :user_id
            """), {'user_id': user_id})
            
            result = matching_query.fetchone()
            if result:
                dto.left_side_active = result.left_active or 0
                dto.right_side_active = result.right_active or 0
                dto.active_matching_referrals = min(dto.left_side_active, dto.right_side_active)
            
        except Exception as e:
            print(f"Error calculating summary stats: {e}")
            # Critical: Rollback session to prevent cascade failures
            self.db.session.rollback()
            dto.active_direct_referrals = 0
            dto.active_matching_referrals = 0
            dto.left_side_active = 0
            dto.right_side_active = 0
    
    def _populate_quick_status(self, dto, user_id):
        """Populate quick status with scheme information"""
        try:
            # Get total direct referrals (lifetime, same as summary for consistency)
            dto.total_direct_referrals = dto.active_direct_referrals
            
            # Get allowance scheme selector
            scheme = self.AllowanceSchemeSelector.query.filter_by(user_id=user_id).first()
            if scheme:
                dto.scheme_status = scheme.selected_scheme
                dto.scheme_monthly_amount = scheme.monthly_amount
                dto.scheme_tenure_months = scheme.tenure_months
                
                # Calculate days remaining based on scheme
                if scheme.selected_scheme == 'Field':
                    dto.days_remaining = max(0, (36 * 30) - ((datetime.utcnow() - scheme.created_at).days))
                elif scheme.selected_scheme == 'Car':
                    dto.days_remaining = max(0, (72 * 30) - ((datetime.utcnow() - scheme.created_at).days))
                else:
                    dto.days_remaining = 0
            
        except Exception as e:
            print(f"Error calculating quick status: {e}")
            # Rollback and set defaults
            self.db.session.rollback()
            dto.total_direct_referrals = 0
            dto.scheme_status = "None"
            dto.scheme_monthly_amount = 0
            dto.scheme_tenure_months = 0
            dto.days_remaining = 0
    
    def _populate_monthly_performance(self, dto, user_id):
        """Populate monthly performance data (last 6 months)"""
        try:
            # Get last 6 months
            current_date = datetime.utcnow()
            months_data = []
            
            for i in range(6):
                # Calculate month boundaries
                month_date = current_date - timedelta(days=30 * i)
                month_start = month_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                
                # Calculate next month start
                if month_start.month == 12:
                    next_month = month_start.replace(year=month_start.year + 1, month=1)
                else:
                    next_month = month_start.replace(month=month_start.month + 1)
                
                # Get direct referrals for this month
                direct_count = self.User.query.filter(
                    self.User.referrer_id == user_id,
                    self.User.coupon_status == 'Active',
                    self.User.registration_date >= month_start,
                    self.User.registration_date < next_month
                ).count()
                
                # Get matching referrals for this month
                matching_query = self.db.session.execute(text("""
                    SELECT COUNT(*) as matching_count
                    FROM placement p
                    JOIN "user" u ON u.id = p.child_id
                    WHERE p.parent_id = :user_id
                    AND u.coupon_status = 'Active' 
                    AND u.kyc_status = 'Approved'
                    AND u.registration_date >= :month_start
                    AND u.registration_date < :next_month
                """), {
                    'user_id': user_id,
                    'month_start': month_start,
                    'next_month': next_month
                })
                
                matching_result = matching_query.fetchone()
                matching_count = matching_result.matching_count if matching_result else 0
                
                # Get Field Allowance transactions for this month
                field_target = direct_count >= 7 and dto.active_matching_referrals >= 20
                car_target = dto.active_matching_referrals >= 250 and matching_count >= 40
                
                months_data.append({
                    'month': month_start.strftime('%B %Y'),
                    'month_key': month_start.strftime('%Y-%m'),
                    'direct_count': direct_count,
                    'matching_count': matching_count,
                    'field_target_met': field_target,
                    'car_target_met': car_target
                })
            
            # Reverse to show oldest first
            dto.monthly_performance = list(reversed(months_data))
            
        except Exception as e:
            print(f"Error calculating monthly performance: {e}")
            # Rollback and set defaults
            self.db.session.rollback()
            dto.monthly_performance = []
    
    def _populate_eligibility(self, dto, user_id):
        """Populate eligibility information"""
        try:
            # Get current settings (default to 7 if SuperAdminSettings doesn't exist)
            field_requirement = 7  # Default requirement
            try:
                if hasattr(self, 'SuperAdminSettings') and self.SuperAdminSettings:
                    settings = self.SuperAdminSettings.query.first()
                    field_requirement = settings.field_allowance_eligibility_count if settings else 7
            except:
                pass  # Use default if model doesn't exist
            
            # Field Allowance eligibility: 7 direct + 20 matching + balanced sides
            field_eligible = (
                dto.active_direct_referrals >= field_requirement and
                dto.active_matching_referrals >= 20 and
                dto.left_side_active >= 1 and
                dto.right_side_active >= 1
            )
            
            # Car Allowance eligibility: 250 matching + 40 monthly matching + balanced sides
            car_eligible = (
                dto.active_matching_referrals >= 250 and
                dto.left_side_active >= 1 and
                dto.right_side_active >= 1
            )
            
            dto.field_allowance_eligible = field_eligible
            dto.car_allowance_eligible = car_eligible
            
            if car_eligible:
                dto.eligibility_message = "Eligible for Car Allowance (₹25,000/month for 72 months)"
            elif field_eligible:
                dto.eligibility_message = "Eligible for Field Allowance (₹10,000/month for 36 months)"
            else:
                if dto.active_direct_referrals < field_requirement:
                    remaining_direct = field_requirement - dto.active_direct_referrals
                    dto.eligibility_message = f"Need {remaining_direct} more direct referrals to qualify"
                elif dto.active_matching_referrals < 20:
                    remaining_matching = 20 - dto.active_matching_referrals
                    dto.eligibility_message = f"Need {remaining_matching} more matching referrals to qualify"
                else:
                    dto.eligibility_message = "Need balanced matching team (1:1 left/right ratio)"
            
        except Exception as e:
            print(f"Error calculating eligibility: {e}")
            # Rollback and set defaults
            self.db.session.rollback()
            dto.field_allowance_eligible = False
            dto.car_allowance_eligible = False
            dto.eligibility_message = "Error calculating eligibility"