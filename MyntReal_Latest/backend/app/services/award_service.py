"""
Award Service for FastAPI - Award System Management
Preserves exact Flask award progression and achievement tracking
"""

from typing import List, Dict, Optional, Any
from datetime import datetime, date, timedelta
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc, asc

from app.models.user import User
from app.models.awards import DirectAwardTier, UserAwardProgress, MatchingAwardTier, UserMatchingAwardProgress
from app.models.bonanza import DynamicBonanza, DynamicBonanzaReward, DynamicBonanzaHistory  # DC Protocol: BonanzaProgress deprecated
from app.models.transaction import Transaction
from app.models.base import get_indian_time
from app.constants.award_statuses import AwardStatus  # DC Protocol: Unified status constants

class AwardService:
    """
    Award Service handling all award progression and achievement tracking
    Preserves exact Flask award system logic
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    def check_universal_eligibility(self, user_id: str) -> Dict[str, Any]:
        """
        UNIVERSAL ELIGIBILITY CHECK for Awards, Bonanzas, and Field Allowances
        
        Uses STANDARDIZED eligibility functions from scheduler (same as Matching/Ved Income):
        1. check_direct_referrals_both_sides() - Must have at least 1 point on LEFT and RIGHT positions
        2. check_first_matching_achieved() - Must have achieved first matching (2:1 or 1:2 ratio)
        
        This applies to:
        - Direct Awards
        - Matching Awards
        - Bonanza Rewards
        - Field Allowances
        """
        from app.core.scheduler import check_direct_referrals_both_sides, check_first_matching_achieved
        from app.services.sql_utils import get_leg_points_sql
        
        # Use STANDARDIZED checks (same as Matching/Ved Income)
        has_direct_both_sides = check_direct_referrals_both_sides(self.db, user_id)
        has_first_matching = check_first_matching_achieved(self.db, user_id)
        
        # Get leg points for display
        leg_points = get_leg_points_sql(self.db, user_id)
        left_points = leg_points['left']
        right_points = leg_points['right']
        
        # Overall eligibility: BOTH conditions must be met
        is_eligible = has_direct_both_sides and has_first_matching
        
        # Build eligibility reasons
        failed_checks = []
        if not has_direct_both_sides:
            failed_checks.append("Missing 1:1 active direct referrals on both LEFT and RIGHT positions")
        if not has_first_matching:
            failed_checks.append("Missing first matching achievement (requires 2:1 or 1:2 ratio)")
        
        return {
            "is_eligible": is_eligible,
            "has_direct_both_sides": has_direct_both_sides,
            "has_first_matching": has_first_matching,
            "left_points": left_points,
            "right_points": right_points,
            "requirements": {
                "direct_both_sides": "At least 1 active point on BOTH left and right positions (User.position field)",
                "first_matching": "First matching achieved (2:1 or 1:2 ratio from downline)"
            },
            "failed_checks": failed_checks,
            "eligibility_reason": " | ".join(failed_checks) if failed_checks else "All criteria met"
        }
    
    def _get_multiplier_explanation(self, match_type: str) -> str:
        """Get human-readable explanation of multiplier logic"""
        explanations = {
            'full_100': 'Both legs ≥ 15,000 points → 100% multiplier (1.0)',
            'one_75': 'One leg ≥ 15,000, other ≥ 7,500 → 75% multiplier (0.75)',
            'both_50': 'Both legs ≥ 7,500 points → 50% multiplier (0.5)',
            None: 'Insufficient points for matching'
        }
        return explanations.get(match_type, 'Unknown match type')
    
    # Direct Award Management
    def get_direct_award_tiers(self) -> List[Dict[str, Any]]:
        """Get all direct award tiers (preserves Flask tier structure)"""
        tiers = self.db.query(DirectAwardTier).order_by(asc(DirectAwardTier.cumulative_required)).all()
        
        return [
            {
                "id": tier.id,
                "referral_count": tier.referral_count,
                "award_name": tier.award_name,
                "award_description": tier.award_description,
                "price_range_from": float(tier.price_range_from) if tier.price_range_from else None,
                "price_range_to": float(tier.price_range_to) if tier.price_range_to else None,
                "actual_price": float(tier.actual_price) if tier.actual_price else None
            }
            for tier in tiers
        ]
    
    def get_user_direct_award_progress(self, user_id: str) -> Dict[str, Any]:
        """
        Get user's direct award progress with Option A logic:
        - Awards based on PACKAGE POINTS (not referral count)
        - Requires 1:1 direct active points (both LEFT and RIGHT)
        - Requires 1:2 or 2:1 matching referral points
        - Achievement based on cumulative_required comparison
        - Bonanza deductions affect current working tier
        """
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return {"error": "User not found"}
        
        # OCTOBER 21ST RESET LOGIC: Pre-Oct 21st users start fresh from Oct 21, 2025
        # Users activated before Oct 21: Only count referrals activated ON or AFTER Oct 21, 2025
        # Users activated on/after Oct 21: Count all referrals (normal)
        from datetime import date, datetime as dt
        AWARDS_RESET_DATE = date(2025, 10, 21)
        
        user_activation_date = user.activation_date.date() if isinstance(user.activation_date, dt) else user.activation_date
        
        # Determine cutoff date for counting referrals
        # DC Protocol: Exclude Welcome Coupon AND Star/Loyal (package_points=0) users from award achievement counting
        if user_activation_date and user_activation_date < AWARDS_RESET_DATE:
            # Pre-Oct 20th user: Reset to 0, only count referrals activated AFTER Oct 20
            total_package_points = self.db.query(func.sum(User.package_points)).filter(
                User.referrer_id == user_id,
                User.coupon_status == 'Activated',
                User.is_welcome_coupon.is_(False),
                User.package_points > 0,
                User.activation_date >= AWARDS_RESET_DATE
            ).scalar() or 0.0
            
            direct_count = self.db.query(User).filter(
                User.referrer_id == user_id,
                User.coupon_status == 'Activated',
                User.is_welcome_coupon.is_(False),
                User.package_points > 0,
                User.activation_date >= AWARDS_RESET_DATE
            ).count()
        else:
            # Post-Oct 20th user: Count all referrals (no cutoff)
            total_package_points = self.db.query(func.sum(User.package_points)).filter(
                User.referrer_id == user_id,
                User.coupon_status == 'Activated',
                User.is_welcome_coupon.is_(False),
                User.package_points > 0
            ).scalar() or 0.0
            
            direct_count = self.db.query(User).filter(
                User.referrer_id == user_id,
                User.coupon_status == 'Activated',
                User.is_welcome_coupon.is_(False),
                User.package_points > 0
            ).count()
        
        # UNIVERSAL ELIGIBILITY CHECK (STANDARDIZED - same as Matching/Ved Income)
        eligibility = self.check_universal_eligibility(user_id)
        is_eligible_for_awards = eligibility['is_eligible']
        has_direct_both_sides = eligibility['has_direct_both_sides']
        has_first_matching = eligibility['has_first_matching']
        left_points = eligibility['left_points']
        right_points = eligibility['right_points']
        eligibility_reason = eligibility['eligibility_reason']
        
        # Get bonanza deductions for direct awards
        bonanza_deduction_data = self.get_bonanza_deduction(user_id, 'direct')
        total_bonanza_deductions = bonanza_deduction_data.get('total_deduction', 0)
        
        # Effective points after bonanza deductions
        effective_points = max(0, total_package_points - total_bonanza_deductions)
        
        # Get all direct award tiers ordered by cumulative requirement
        tiers = self.db.query(DirectAwardTier).order_by(asc(DirectAwardTier.cumulative_required)).all()
        
        # Get user's progress records
        progress_records = self.db.query(UserAwardProgress).filter(
            and_(
                UserAwardProgress.user_id == user_id,
                # DC PROTOCOL: Filter out legacy pre-Oct 21 awards (permanently hidden from users)
                or_(
                    UserAwardProgress.is_legacy_pre_reset == False,
                    UserAwardProgress.is_legacy_pre_reset.is_(None)
                )
            )
        ).all()
        
        progress_data = []
        previous_cumulative = 0
        
        for tier in tiers:
            # Find existing progress record
            existing_progress = next(
                (p for p in progress_records if p.award_tier_id == tier.id), 
                None
            )
            
            # Achievement based on PACKAGE POINTS + ELIGIBILITY
            # Must have: sufficient points AND 1:1 direct both sides AND 1:2/2:1 matching
            achieved = (effective_points >= tier.cumulative_required) and is_eligible_for_awards
            
            # Calculate incremental progress (Option A) - based on POINTS
            if achieved:
                # Achieved tier shows full incremental requirement
                display_progress = tier.referral_count
            else:
                # Current/future tier: show progress toward incremental requirement
                # Progress for this tier = effective_points - previous_cumulative
                incremental_progress = max(0, effective_points - previous_cumulative)
                display_progress = min(incremental_progress, tier.referral_count)
            
            tier_progress = {
                "tier_info": {
                    "id": tier.id,
                    "referral_count": tier.referral_count,  # Incremental requirement (in points)
                    "cumulative_required": tier.cumulative_required,  # Total points from start
                    "rank_name": tier.award_name,  # Rank: "Super Star", "Super Prime Star"
                    "award_item": tier.award_description,  # Item: "Smart Watch", "GOA Trip"
                    "actual_price": float(tier.actual_price) if tier.actual_price else None
                },
                "current_direct_count": display_progress,  # Incremental progress for this tier (in points)
                "lifetime_referral_count": direct_count,  # Total activated referrals (for display)
                "total_package_points": float(total_package_points),  # Total points from referrals
                "effective_points": float(effective_points),  # After bonanza deductions
                "bonanza_deductions": total_bonanza_deductions if not achieved else 0,  # Show only for working tier
                "progress_percentage": min(100.0, (display_progress / tier.referral_count) * 100) if tier.referral_count > 0 else 100.0,
                "achieved": achieved,
                "achievement_date": existing_progress.achieved_at.isoformat() if existing_progress and existing_progress.achieved_at else None,
                "achievement_bonus_paid": getattr(existing_progress, 'achievement_bonus_paid', False) if existing_progress else False,
                "processed_date": existing_progress.processed_date.isoformat() if existing_progress and existing_progress.processed_date else None,
                # DC PROTOCOL: Add procurement workflow fields for user dashboard visibility
                "processed_status": existing_progress.processed_status if existing_progress else "Pending",
                "admin_approved_by": existing_progress.admin_approved_by if existing_progress else None,
                "admin_approved_at": existing_progress.admin_approved_at.isoformat() if existing_progress and existing_progress.admin_approved_at else None,
                # DC PROTOCOL: Delivery tracking fields
                "dispatch_date": existing_progress.dispatch_date.isoformat() if existing_progress and existing_progress.dispatch_date else None,
                "received_date": existing_progress.received_date.isoformat() if existing_progress and existing_progress.received_date else None,
                "delivery_notes": existing_progress.delivery_notes if existing_progress else None
            }
            
            progress_data.append(tier_progress)
            previous_cumulative = tier.cumulative_required
        
        return {
            "user_id": user_id,
            "current_direct_referrals": direct_count,
            "total_package_points": float(total_package_points),
            "effective_points": float(effective_points),
            "bonanza_deductions": total_bonanza_deductions,
            "left_points": float(left_points),
            "right_points": float(right_points),
            "eligibility": {
                "is_eligible": is_eligible_for_awards,
                "has_direct_both_sides": has_direct_both_sides,
                "has_first_matching": has_first_matching,
                "left_points": float(left_points),
                "right_points": float(right_points),
                "eligibility_reason": eligibility_reason,
                "requirements": {
                    "direct_both_sides": "At least 1 active point on BOTH left and right positions",
                    "first_matching": "First matching achieved (2:1 or 1:2 ratio from downline)"
                }
            },
            "tier_progress": progress_data
        }
    
    def update_direct_award_progress(self, user_id: str) -> Dict[str, Any]:
        """
        Update user's direct award progress and process achievements
        Preserves Flask award processing logic
        
        DC PROTOCOL: Sets is_legacy_pre_reset flag based on activation date using centralized helper
        """
        from app.services.award_processing_service import AwardProcessingService
        
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return {"error": "User not found"}
        
        # DC PROTOCOL: Use centralized legacy check helper (single source of truth)
        award_processing_service = AwardProcessingService(self.db)
        is_legacy = award_processing_service._check_is_legacy_award(user_id)
        
        direct_count = self.db.query(User).filter(User.referrer_id == user_id).count()
        tiers = self.db.query(DirectAwardTier).order_by(asc(DirectAwardTier.cumulative_required)).all()
        
        new_achievements = []
        
        for tier in tiers:
            # Check if user qualifies for this tier
            if direct_count >= tier.referral_count:
                # Check if progress record exists
                progress = self.db.query(UserAwardProgress).filter(
                    and_(
                        UserAwardProgress.user_id == user_id,
                        UserAwardProgress.award_tier_id == tier.id
                    )
                ).first()
                
                if not progress:
                    # Create new progress record - DC Protocol: Always start at Pending Approval
                    progress = UserAwardProgress(
                        user_id=user_id,
                        award_tier_id=tier.id,
                        current_direct_count=direct_count,
                        required_count=tier.required_direct_referrals,
                        progress_percentage=100.0,
                        achieved=True,
                        achievement_date=get_indian_time(),
                        processed_status=AwardStatus.PENDING_APPROVAL,  # DC Protocol: Standardized starting status
                        is_legacy_pre_reset=is_legacy  # DC PROTOCOL: Mark pre-Oct 21 awards as legacy
                    )
                    self.db.add(progress)
                    new_achievements.append({
                        "tier_name": tier.tier_name,
                        "tier_level": tier.tier_level,
                        "achievement_bonus": float(tier.achievement_bonus)
                    })
                
                elif not progress.achieved:
                    # Update existing progress to achieved
                    progress.achieved = True
                    progress.achievement_date = get_indian_time()
                    progress.current_direct_count = direct_count
                    progress.progress_percentage = 100.0
                    new_achievements.append({
                        "tier_name": tier.tier_name,
                        "tier_level": tier.tier_level,
                        "achievement_bonus": float(tier.achievement_bonus)
                    })
                
                else:
                    # Update count but already achieved
                    progress.current_direct_count = direct_count
            
            else:
                # Update progress but not achieved yet
                progress = self.db.query(UserAwardProgress).filter(
                    and_(
                        UserAwardProgress.user_id == user_id,
                        UserAwardProgress.award_tier_id == tier.id
                    )
                ).first()
                
                if progress:
                    progress.current_direct_count = direct_count
                    progress.progress_percentage = (direct_count / tier.required_direct_referrals) * 100
                else:
                    # Create progress record for tracking - DC Protocol: Use Pending Approval even for in-progress
                    progress = UserAwardProgress(
                        user_id=user_id,
                        award_tier_id=tier.id,
                        current_direct_count=direct_count,
                        required_count=tier.required_direct_referrals,
                        progress_percentage=(direct_count / tier.required_direct_referrals) * 100,
                        achieved=False,
                        processed_status=AwardStatus.PENDING_APPROVAL,  # DC Protocol: Standardized starting status
                        is_legacy_pre_reset=is_legacy  # DC PROTOCOL: Mark pre-Oct 21 awards as legacy
                    )
                    self.db.add(progress)
        
        self.db.commit()
        
        return {
            "user_id": user_id,
            "current_direct_count": direct_count,
            "new_achievements": new_achievements,
            "message": f"Progress updated. {len(new_achievements)} new achievements unlocked."
        }
    
    # Matching Award Management
    def get_matching_award_tiers(self) -> List[Dict[str, Any]]:
        """
        Get all matching award tiers using ACTUAL database structure
        Database columns: match_count, award_name, actual_price, cumulative_required
        """
        from sqlalchemy import text
        
        query = text("""
            SELECT id, match_count, award_name, award_description, 
                   actual_price, price_range_from, price_range_to, cumulative_required
            FROM matching_award_tier
            ORDER BY cumulative_required ASC
        """)
        
        result = self.db.execute(query)
        rows = result.fetchall()
        
        return [
            {
                "id": row[0],
                "tier_name": row[2],  # award_name
                "award_description": row[3],
                "required_matching_pairs": row[1],  # match_count
                "cumulative_required": row[7],
                "achievement_bonus": float(row[4]),  # actual_price
                "price_range_from": float(row[5]),
                "price_range_to": float(row[6]),
                "min_personal_referrals": 0  # Default, can be added to DB later
            }
            for row in rows
        ]
    
    def get_bonanza_deduction(self, user_id: str, award_type: str) -> Dict[str, Any]:
        """
        Get bonanza deduction to apply to regular awards (Flask-compatible)
        
        WVV COMPLIANT WORKFLOW (IMMEDIATE DEDUCTION):
        - User claims bonanza → claimed_at = NOW(), deduction_applied_* = True
        - Deduction applies IMMEDIATELY to award calculations
        - RVZ approval is for procurement/delivery tracking ONLY
        
        PRINCIPLE: Claim = Commitment = Instant Deduction
        
        This ensures:
        1. Single source of truth (claimed_at timestamp)
        2. Immediate feedback to users (awards drop instantly)
        3. No approval delay for deductions
        4. DC Protocol compliance across all roles
        
        Args:
            user_id: User's MNR ID
            award_type: 'direct' or 'matching'
        
        Returns:
            dict with total_deduction, deduction_details, affected_bonanzas
        """
        if award_type not in ['direct', 'matching']:
            return {'total_deduction': 0, 'deduction_details': [], 'affected_bonanzas': []}
        
        # Get ALL CLAIMED bonanza records (claimed_at IS NOT NULL)
        # IMMEDIATE DEDUCTION: As soon as user claims, deduction applies
        # RVZ approval is for procurement tracking, not deduction gating
        if award_type == 'direct':
            history_records = self.db.query(DynamicBonanzaHistory).filter(
                and_(
                    DynamicBonanzaHistory.user_id == user_id,
                    DynamicBonanzaHistory.deduction_applied_to_direct_awards == True,
                    DynamicBonanzaHistory.claimed_at.isnot(None)  # Claimed = Deduction applies
                )
            ).all()
        else:  # matching
            history_records = self.db.query(DynamicBonanzaHistory).filter(
                and_(
                    DynamicBonanzaHistory.user_id == user_id,
                    DynamicBonanzaHistory.deduction_applied_to_matching_awards == True,
                    DynamicBonanzaHistory.claimed_at.isnot(None)  # Claimed = Deduction applies
                )
            ).all()
        
        total_deduction = 0
        deduction_details = []
        affected_bonanzas = []
        
        for history in history_records:
            if award_type == 'direct':
                deduction_amount = history.deduction_amount_direct or 0
            else:
                deduction_amount = history.deduction_amount_matching or 0
            
            if deduction_amount > 0:
                total_deduction += deduction_amount
                
                # Get bonanza details
                bonanza = self.db.query(DynamicBonanza).filter(
                    DynamicBonanza.id == history.bonanza_id
                ).first()
                bonanza_name = bonanza.campaign_name if bonanza else f"Bonanza ID {history.bonanza_id}"
                
                deduction_details.append({
                    'bonanza_id': history.bonanza_id,
                    'bonanza_name': bonanza_name,
                    'deduction_amount': deduction_amount,
                    'claimed_at': history.claimed_at.isoformat() if history.claimed_at else None,
                    'reward_value': float(history.reward_value_claimed) if history.reward_value_claimed else 0.0
                })
                
                if bonanza_name not in affected_bonanzas:
                    affected_bonanzas.append(bonanza_name)
        
        return {
            'total_deduction': total_deduction,
            'deduction_details': deduction_details,
            'affected_bonanzas': affected_bonanzas
        }
    
    def calculate_matching_pairs(self, user_id: str) -> Dict[str, int]:
        """
        Calculate user's LIFETIME matching count for Awards and Bonanza
        
        Calculates total accumulated matching pairs from income transaction history.
        This ensures users get credit for all their accumulated matching pairs over time.
        
        Used for Awards, Bonanza, Field Allowances eligibility
        """
        from app.models.transaction import PendingIncome
        
        # Get user data
        user = self.db.query(User).filter(User.id == user_id).first()
        
        if not user:
            return {
                "left_points": 0,
                "right_points": 0,
                "raw_matching_count": 0,
                "effective_matching_count": 0,
                "bonanza_deductions": 0,
                "effective_remaining": 0,
                "multiplier": 1.0,
                "match_type": "lifetime_matching",
                "bonanza_details": {"total_deduction": 0, "deduction_details": [], "affected_bonanzas": []}
            }
        
        # OCTOBER 21ST RESET LOGIC: Pre-Oct 21st users start fresh from Oct 21, 2025
        # Users activated before Oct 21: Only count users activated AFTER Oct 21, 2025
        # Users activated on/after Oct 21: Count all users (normal)
        from datetime import date, datetime as dt
        from app.services.sql_utils import get_matching_pairs_with_reset_logic_sql
        
        AWARDS_RESET_DATE = date(2025, 10, 21)
        user_activation_date = user.activation_date.date() if isinstance(user.activation_date, dt) else user.activation_date
        
        # Determine if we need to apply the reset filter
        if user_activation_date and user_activation_date < AWARDS_RESET_DATE:
            # Pre-Oct 20th user: Only count users activated ON or AFTER Oct 20
            reset_date_str = AWARDS_RESET_DATE.isoformat()
            matching_result = get_matching_pairs_with_reset_logic_sql(self.db, user_id, reset_date_str)
        else:
            # Post-Oct 20th user: Count all users (no reset filter)
            matching_result = get_matching_pairs_with_reset_logic_sql(self.db, user_id, None)
        
        lifetime_matching = matching_result['matching_pairs']
        
        # Get bonanza deductions for matching awards
        bonanza_deduction = self.get_bonanza_deduction(user_id, 'matching')
        
        # Calculate effective remaining after bonanza deductions
        effective_remaining = max(0, lifetime_matching - bonanza_deduction['total_deduction'])
        
        return {
            "left_points": 0,  # Not tracked in User model
            "right_points": 0,  # Not tracked in User model
            "raw_matching_count": lifetime_matching,
            "effective_matching_count": lifetime_matching,
            "bonanza_deductions": bonanza_deduction['total_deduction'],
            "effective_remaining": effective_remaining,
            "multiplier": 1.0,  # Lifetime matching uses 1:1 counting
            "match_type": "lifetime_matching",
            "bonanza_details": bonanza_deduction
        }
    
    def get_user_matching_award_progress(self, user_id: str) -> Dict[str, Any]:
        """
        Get user's matching award progress with Option A logic:
        - Incremental progress display (e.g., 6/8 for current tier)
        - Achievement based on cumulative_required comparison
        - Uses EFFECTIVE matching count (with 100%/75%/50% multipliers)
        - Bonanza deductions affect current working tier
        - Qualification check: 1:1, 1:2, or 2:1 active required for achievement
        """
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return {"error": "User not found"}
        
        # Calculate current matching status with NEW multiplier
        matching_data = self.calculate_matching_pairs(user_id)
        # USER DATA FIX: Show ALL user data (no production date filter)
        # DC Protocol: Exclude Welcome Coupon AND Star/Loyal (package_points=0) users from award achievement counting
        direct_count = self.db.query(User).filter(
            User.referrer_id == user_id,
            User.coupon_status == 'Activated',
            User.is_welcome_coupon.is_(False),
            User.package_points > 0
        ).count()
        
        # Effective count after bonanza deductions
        effective_remaining = matching_data["effective_remaining"]
        bonanza_deductions = matching_data["bonanza_deductions"]
        
        # UNIVERSAL ELIGIBILITY CHECK (uses POINTS, not user count)
        eligibility = self.check_universal_eligibility(user_id)
        qualification_met = eligibility['is_eligible']
        left_points = eligibility['left_points']
        right_points = eligibility['right_points']
        
        # Calculate left_active and right_active based on points
        left_active = left_points >= 1.0
        right_active = right_points >= 1.0
        
        if not qualification_met:
            failed_checks = [check for check in eligibility['failed_checks'] if check]
            qualification_message = f"Matching qualification not met. {'; '.join(failed_checks)}"
        else:
            qualification_message = ""
        
        # Get all matching award tiers ordered by cumulative requirement
        tiers_raw = self.get_matching_award_tiers()
        
        # Get user's progress records
        progress_records = self.db.query(UserMatchingAwardProgress).filter(
            and_(
                UserMatchingAwardProgress.user_id == user_id,
                # DC PROTOCOL: Filter out legacy pre-Oct 21 awards (permanently hidden from users)
                or_(
                    UserMatchingAwardProgress.is_legacy_pre_reset == False,
                    UserMatchingAwardProgress.is_legacy_pre_reset.is_(None)
                )
            )
        ).all()
        
        progress_data = []
        previous_cumulative = 0
        
        for tier in tiers_raw:
            # Find existing progress record
            existing_progress = next(
                (p for p in progress_records if p.matching_award_tier_id == tier["id"]), 
                None
            )
            
            # Achievement based on cumulative_required AND qualification
            meets_matching_requirement = effective_remaining >= tier["cumulative_required"]
            meets_personal_requirement = direct_count >= tier["min_personal_referrals"]
            meets_qualification = qualification_met
            
            # Achievement requires ALL conditions: count + personal + qualification
            achieved = meets_matching_requirement and meets_personal_requirement and meets_qualification
            
            # Calculate incremental progress (Option A)
            if achieved:
                # Achieved tier shows full incremental requirement
                display_progress = tier["required_matching_pairs"]
            else:
                # Current/future tier: show progress toward incremental requirement
                # Progress for this tier = effective_remaining - previous_cumulative
                incremental_progress = max(0, effective_remaining - previous_cumulative)
                display_progress = min(incremental_progress, tier["required_matching_pairs"])
            
            tier_progress = {
                "tier_info": {
                    "id": tier["id"],
                    "required_matching_pairs": tier["required_matching_pairs"],  # Incremental requirement
                    "cumulative_required": tier["cumulative_required"],  # Total from start
                    "rank_name": tier["tier_name"],  # Rank: "Star", "Prime Star", "Silver Star"
                    "award_item": tier["award_description"],  # Item: "Water Park Entry", "GOA Tour"
                    "achievement_bonus": tier["achievement_bonus"]
                },
                "current_matching_count": display_progress,  # Incremental progress for this tier
                "lifetime_matching_count": matching_data["effective_matching_count"],  # Total effective matches
                "effective_remaining": effective_remaining,  # After bonanza deductions
                "bonanza_deductions": bonanza_deductions if not achieved else 0,  # Show only for working tier
                "raw_matching_count": matching_data["raw_matching_count"],
                "multiplier": matching_data["multiplier"],
                "match_type": matching_data["match_type"],
                "left_points": matching_data["left_points"],
                "right_points": matching_data["right_points"],
                "left_active": left_active,
                "right_active": right_active,
                "current_personal_referrals": direct_count,
                "meets_matching_requirement": meets_matching_requirement,
                "meets_personal_requirement": meets_personal_requirement,
                "meets_qualification": meets_qualification,
                "achieved": achieved,
                "achievement_date": existing_progress.achievement_date.isoformat() if existing_progress and existing_progress.achievement_date else None,
                "processed_date": existing_progress.processed_date.isoformat() if existing_progress and existing_progress.processed_date else None,
                # DC PROTOCOL: Add procurement workflow fields for user dashboard visibility
                "processed_status": existing_progress.processed_status if existing_progress else "Pending",
                "admin_approved_by": existing_progress.admin_approved_by if existing_progress else None,
                "admin_approved_at": existing_progress.admin_approved_at.isoformat() if existing_progress and existing_progress.admin_approved_at else None,
                # DC PROTOCOL: Delivery tracking fields
                "dispatch_date": existing_progress.dispatch_date.isoformat() if existing_progress and existing_progress.dispatch_date else None,
                "received_date": existing_progress.received_date.isoformat() if existing_progress and existing_progress.received_date else None,
                "delivery_notes": existing_progress.delivery_notes if existing_progress else None
            }
            
            progress_data.append(tier_progress)
            previous_cumulative = tier["cumulative_required"]
        
        return {
            "user_id": user_id,
            "matching_status": matching_data,
            "current_personal_referrals": direct_count,
            "effective_remaining": effective_remaining,
            "bonanza_deductions": bonanza_deductions,
            "qualification_met": qualification_met,
            "qualification_message": qualification_message,
            "left_active": left_active,
            "right_active": right_active,
            "tier_progress": progress_data
        }
    
    # Bonanza Management
    def get_active_bonanzas(self) -> List[Dict[str, Any]]:
        """Get all active bonanza campaigns using actual database structure"""
        from sqlalchemy import text
        
        now = get_indian_time()
        
        query = text("""
            SELECT id, bonanza_name, description, start_date, end_date,
                   has_direct_target, has_matching_target, status, total_budget_allocated
            FROM dynamic_bonanza
            WHERE status = 'active'
              AND start_date <= :now
              AND end_date >= :now
            ORDER BY start_date DESC
        """)
        
        result = self.db.execute(query, {"now": now})
        bonanzas = result.fetchall()
        
        return [
            {
                "id": row[0],
                "campaign_name": row[1],
                "description": row[2],
                "start_date": row[3].isoformat(),
                "end_date": row[4].isoformat(),
                "targets_direct_awards": row[5],
                "targets_matching_awards": row[6],
                "status": row[7],
                "total_budget": float(row[8]) if row[8] else 0.0
            }
            for row in bonanzas
        ]
    
    def calculate_bonanza_eligibility(self, user_id: str, bonanza_id: int) -> Dict[str, Any]:
        """
        Calculate bonanza eligibility using NEW multiplier logic
        
        CRITICAL: Bonanza eligibility uses TOTAL effective count (NO deductions)
        This allows double counting: achievements count for BOTH bonanza AND regular awards
        Only AFTER claiming bonanza, deductions apply to regular awards
        
        Args:
            user_id: User's MNR ID
            bonanza_id: DynamicBonanza ID
        
        Returns:
            dict with eligible_rewards, user_progress, bonanza_info
        """
        from app.core.scheduler import calculate_effective_matching_count
        from sqlalchemy import text
        
        # Get bonanza details using raw SQL
        bonanza_query = text("""
            SELECT id, bonanza_name, description, start_date, end_date, 
                   has_direct_target, has_matching_target, status
            FROM dynamic_bonanza
            WHERE id = :bonanza_id
        """)
        bonanza_result = self.db.execute(bonanza_query, {"bonanza_id": bonanza_id})
        bonanza_row = bonanza_result.fetchone()
        
        if not bonanza_row:
            return {
                'error': f'Bonanza {bonanza_id} not found',
                'eligible_rewards': [],
                'user_progress': None,
                'bonanza_info': None
            }
        
        # UNIVERSAL ELIGIBILITY CHECK (MANDATORY for all income including Bonanza)
        eligibility = self.check_universal_eligibility(user_id)
        if not eligibility['is_eligible']:
            return {
                'error': 'Not eligible for bonanza',
                'eligible_rewards': [],
                'user_progress': None,
                'bonanza_info': None,
                'eligibility': eligibility,
                'ineligible_reason': 'Does not meet universal eligibility requirements (1:1 points + 2:1/1:2 balance)'
            }
        
        direct_count = self.db.query(User).filter(
            User.referrer_id == user_id,
            User.is_welcome_coupon != True,
            User.package_points > 0
        ).count()
        
        # Get EFFECTIVE matching count with multiplier (NO deductions for bonanza)
        matching_result = calculate_effective_matching_count(self.db, user_id)
        effective_matching = matching_result['effective_count']
        
        # Get bonanza rewards
        query = text("""
            SELECT id, reward_name, reward_description, reward_value,
                   direct_referral_target, matching_referral_target, tier_level
            FROM dynamic_bonanza_reward
            WHERE bonanza_id = :bonanza_id AND is_active = true
            ORDER BY tier_level ASC
        """)
        
        result = self.db.execute(query, {"bonanza_id": bonanza_id})
        rewards = result.fetchall()
        
        eligible_rewards = []
        
        for reward in rewards:
            direct_target = reward[4] or 0
            matching_target = reward[5] or 0
            
            # Check eligibility using effective matching count
            # Respect bonanza configuration flags
            if bonanza_row[5]:  # has_direct_target
                meets_direct = direct_count >= direct_target
            else:
                meets_direct = True  # No direct requirement
            
            if bonanza_row[6]:  # has_matching_target  
                meets_matching = effective_matching >= matching_target
            else:
                meets_matching = True  # No matching requirement
                
            is_eligible = meets_direct and meets_matching
            
            reward_data = {
                'id': reward[0],
                'reward_name': reward[1],
                'reward_description': reward[2],
                'reward_value': float(reward[3]),
                'direct_target': direct_target,
                'matching_target': matching_target,
                'tier_level': reward[6],
                'is_eligible': is_eligible,
                'meets_direct': meets_direct,
                'meets_matching': meets_matching
            }
            
            if is_eligible:
                eligible_rewards.append(reward_data)
        
        # Sort by tier level (highest first for best reward)
        eligible_rewards.sort(key=lambda x: x['tier_level'], reverse=True)
        
        return {
            'eligible_rewards': eligible_rewards,
            'user_progress': {
                'direct_count': direct_count,
                'matching_details': {
                    'effective_matching_count': effective_matching,
                    'raw_matching_count': matching_result['raw_count'],
                    'multiplier': matching_result['multiplier'],
                    'match_type': matching_result['match_type'],
                    'multiplier_explanation': self._get_multiplier_explanation(matching_result['match_type'])
                },
                'leg_details': {
                    'left_points': matching_result['left_points'],
                    'right_points': matching_result['right_points'],
                    'left_formatted': f"{matching_result['left_points']:,}",
                    'right_formatted': f"{matching_result['right_points']:,}"
                }
            },
            'bonanza_info': {
                'id': bonanza_row[0],
                'campaign_name': bonanza_row[1],
                'description': bonanza_row[2],
                'start_date': bonanza_row[3].isoformat(),
                'end_date': bonanza_row[4].isoformat(),
                'has_direct_target': bonanza_row[5],
                'has_matching_target': bonanza_row[6],
                'status': bonanza_row[7]
            }
        }
    
    def get_user_bonanza_progress(self, user_id: str, bonanza_id: int) -> Dict[str, Any]:
        """Get user's progress in specific bonanza campaign"""
        bonanza = self.db.query(DynamicBonanza).filter(DynamicBonanza.id == bonanza_id).first()
        if not bonanza:
            return {"error": "Bonanza not found"}
        
        # DC Protocol: Use DynamicBonanzaHistory instead of BonanzaProgress
        from app.models.bonanza import DynamicBonanzaHistory
        claim = self.db.query(DynamicBonanzaHistory).filter(
            and_(
                DynamicBonanzaHistory.user_id == user_id,
                DynamicBonanzaHistory.bonanza_id == bonanza_id
            )
        ).first()
        
        if not claim:
            return {
                "user_id": user_id,
                "bonanza_id": bonanza_id,
                "enrolled": False,
                "message": "User has not claimed this bonanza"
            }
        
        # Get bonanza rewards
        rewards = self.db.query(DynamicBonanzaReward).filter(
            DynamicBonanzaReward.bonanza_id == bonanza_id
        ).all()
        
        return {
            "user_id": user_id,
            "bonanza_info": {
                "id": bonanza.id,
                "campaign_name": bonanza.campaign_name,
                "start_date": bonanza.start_date.isoformat(),
                "end_date": bonanza.end_date.isoformat()
            },
            "progress": {
                "enrollment_date": progress.enrollment_date.isoformat(),
                "current_points": float(progress.current_points),
                "rank_position": progress.rank_position,
                "qualifying_achievements": progress.qualifying_achievements,
                "campaign_completed": progress.campaign_completed,
                "eligible_for_reward": progress.eligible_for_reward,
                "reward_amount": float(progress.reward_amount),
                "reward_paid": progress.reward_paid
            },
            "available_rewards": [
                {
                    "reward_name": reward.reward_name,
                    "criteria_type": reward.criteria_type,
                    "criteria_value": float(reward.criteria_value),
                    "reward_amount": float(reward.reward_amount),
                    "reward_type": reward.reward_type
                }
                for reward in rewards
            ]
        }
    
    def get_user_award_summary(self, user_id: str) -> Dict[str, Any]:
        """
        Get comprehensive award summary for user
        Preserves Flask award summary logic
        """
        direct_progress = self.get_user_direct_award_progress(user_id)
        matching_progress = self.get_user_matching_award_progress(user_id)
        active_bonanzas = self.get_active_bonanzas()
        
        # Calculate achievement counts
        direct_achievements = sum(1 for tier in direct_progress.get("tier_progress", []) if tier["achieved"])
        matching_achievements = sum(1 for tier in matching_progress.get("tier_progress", []) if tier["achieved"])
        
        # Get total bonuses paid
        total_achievement_bonuses = self.db.query(func.sum(Transaction.net_amount)).filter(
            and_(
                Transaction.user_id == user_id,
                Transaction.income_type.in_(['direct_award', 'matching_award']),
                Transaction.transaction_type == 'credit'
            )
        ).scalar() or Decimal('0.00')
        
        return {
            "user_id": user_id,
            "achievement_summary": {
                "direct_award_achievements": direct_achievements,
                "matching_award_achievements": matching_achievements,
                "total_achievement_bonuses": float(total_achievement_bonuses),
                "active_bonanza_count": len(active_bonanzas)
            },
            "direct_award_progress": direct_progress,
            "matching_award_progress": matching_progress,
            "active_bonanzas": active_bonanzas
        }