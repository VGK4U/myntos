"""
Field Allowance Service - Comprehensive eligibility and progress tracking
Handles Standard Field Allowance (₹10K/month) and Car Allowance (₹25K/month)
"""

from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from app.models.user import User
from app.models.field_allowance import FieldAllowanceEligibility, CarAllowanceEligibility
from app.models.base import get_indian_time

# Field Allowance Eligibility Cutoff Date
# Users activated on or after this date use activation_date for eligibility
# Users activated before this date use the cutoff date as fresh start
# RESET (2026-01-09): Changed from Dec 21, 2025 to Jan 10, 2026 per admin request
FIELD_ALLOWANCE_CUTOFF_DATE = datetime(2026, 1, 10).date()

class FieldAllowanceService:
    """Service for Field Allowance calculations and eligibility tracking"""
    
    @staticmethod
    def _get_field_allowance_start_date(user: User) -> Optional[datetime]:
        """
        Determine which date to use for Field Allowance eligibility
        
        Rules:
        - Users activated on or after Jan 10, 2026 → use activation_date (their actual activation)
        - Users activated before Jan 10, 2026 → use Jan 10, 2026 (fresh start for existing users)
        """
        if not user.activation_date:
            # Not activated yet - use cutoff date as default
            return datetime.combine(FIELD_ALLOWANCE_CUTOFF_DATE, datetime.min.time())
        
        activation_date_only = user.activation_date.date() if isinstance(user.activation_date, datetime) else user.activation_date
        
        if activation_date_only >= FIELD_ALLOWANCE_CUTOFF_DATE:
            # New users: Use their actual activation_date
            return user.activation_date
        else:
            # Existing users: Fresh start from Jan 10, 2026
            return datetime.combine(FIELD_ALLOWANCE_CUTOFF_DATE, datetime.min.time())
    
    @staticmethod
    def get_user_allowance_status(user_id: int, db: Session) -> Dict[str, Any]:
        """
        Get comprehensive field allowance status for a user
        Returns requirements, progress, remaining numbers, and target dates
        """
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return {"success": False, "message": "User not found"}
        
        standard_data = FieldAllowanceService._get_standard_allowance_status(user, db)
        car_data = FieldAllowanceService._get_car_allowance_status(user, db)
        
        return {
            "success": True,
            "data": {
                "user_id": user_id,
                "user_name": user.name,
                "standard_allowance": standard_data,
                "car_allowance": car_data,
                "current_active": FieldAllowanceService._get_active_allowance(user_id, db)
            }
        }
    
    @staticmethod
    def _get_standard_allowance_status(user: User, db: Session) -> Dict[str, Any]:
        """Get Standard Field Allowance status (7 directs in 45 days, ₹10K/month × 18 months)"""
        
        eligibility = db.query(FieldAllowanceEligibility).filter(
            FieldAllowanceEligibility.user_id == str(user.id)
        ).first()
        
        # Check if opportunity is missed (deadline passed and not eligible)
        is_opportunity_missed = False
        frozen_direct_count = 0
        
        # Get the appropriate start date (registration_date for existing users, activation_date for new users)
        start_date = FieldAllowanceService._get_field_allowance_start_date(user)
        
        if start_date:
            deadline = start_date + timedelta(days=45)
            current_time = get_indian_time()
            
            if current_time > deadline:
                # Deadline has passed
                is_eligible = eligibility.initial_eligibility_met if eligibility else False
                is_active = (eligibility.overall_status == 'Active') if eligibility else False
                
                if not is_eligible and not is_active:
                    # Opportunity MISSED - freeze the count at deadline
                    is_opportunity_missed = True
                    # Store the count as it was at the deadline (if we have it)
                    frozen_direct_count = eligibility.frozen_direct_count if (eligibility and hasattr(eligibility, 'frozen_direct_count')) else 0
        
        # Calculate current POINTS (for background tracking or active display)
        # Use SUM of package_points instead of COUNT
        current_direct_points = db.query(func.sum(User.package_points)).filter(
            User.referrer_id == str(user.id),
            User.coupon_status == 'Activated'
        ).scalar() or 0
        
        # If opportunity missed, show frozen count; otherwise show current points
        display_direct_points = frozen_direct_count if is_opportunity_missed else float(current_direct_points)
        
        requirement = {
            "name": "Standard Field Allowance",
            "monthly_amount": 10000,
            "tenure_months": 18,
            "total_value": 180000,
            
            "initial_requirements": {
                "direct_referrals": {
                    "required": 7,
                    "current": display_direct_points,
                    "remaining": max(0, 7 - display_direct_points),
                    "progress_percentage": min(100, round((display_direct_points / 7) * 100, 2)),
                    "description": "Get 7 direct referral POINTS within 45 days (Platinum=1.0, Diamond=0.5)",
                    "is_frozen": is_opportunity_missed
                },
                "timeframe": {
                    "days": 45,
                    "description": "Complete within 45 days from registration"
                }
            },
            
            "monthly_requirements": {
                "matching_pairs": {
                    "required": 20,
                    "current": eligibility.monthly_achieved_matchings if eligibility else 0,
                    "remaining": max(0, 20 - (eligibility.monthly_achieved_matchings if eligibility else 0)),
                    "progress_percentage": min(100, round(((eligibility.monthly_achieved_matchings if eligibility else 0) / 20) * 100, 2)),
                    "description": "Maintain 20 matching pairs per month"
                }
            },
            
            "status": {
                "is_eligible": eligibility.initial_eligibility_met if eligibility else False,
                "overall_status": eligibility.overall_status if eligibility else "Not Started",
                "months_completed": eligibility.months_completed if eligibility else 0,
                "months_remaining": max(0, 18 - (eligibility.months_completed if eligibility else 0)),
                "total_paid": float(eligibility.total_paid_to_date if eligibility else 0),
                "opportunity_missed": is_opportunity_missed
            },
            
            "target_dates": {
                "initial_eligibility_deadline": FieldAllowanceService._calculate_deadline(start_date, 45) if start_date else None,
                "initial_achieved_date": eligibility.initial_eligibility_date.isoformat() if eligibility and eligibility.initial_eligibility_date else None,
                "expected_completion": eligibility.expected_completion.isoformat() if eligibility and eligibility.expected_completion else None,
                "next_payment_date": FieldAllowanceService._calculate_next_payment_date(eligibility) if eligibility else None
            }
        }
        
        return requirement
    
    @staticmethod
    def _get_car_allowance_status(user: User, db: Session) -> Dict[str, Any]:
        """Get Car Allowance status (250 points in 90 days, ₹25K/month × 72 months)"""
        
        eligibility = db.query(CarAllowanceEligibility).filter(
            CarAllowanceEligibility.user_id == str(user.id)
        ).first()
        
        # Check binary qualification (1:1, 1:2, or 2:1 active members)
        qualification_status = FieldAllowanceService._check_binary_qualification(user.id, db)
        
        # Check if opportunity is missed (deadline passed and not eligible)
        is_opportunity_missed = False
        frozen_points = 0
        
        # Get the appropriate start date (registration_date for existing users, activation_date for new users)
        start_date = FieldAllowanceService._get_field_allowance_start_date(user)
        
        if start_date:
            deadline = start_date + timedelta(days=90)
            current_time = get_indian_time()
            
            if current_time > deadline:
                # Deadline has passed
                is_eligible = eligibility.initial_eligibility_met if eligibility else False
                is_active = (eligibility.overall_status == 'Active') if eligibility else False
                
                if not is_eligible and not is_active:
                    # Opportunity MISSED - freeze the count at deadline
                    is_opportunity_missed = True
                    frozen_points = eligibility.frozen_matching_points if (eligibility and hasattr(eligibility, 'frozen_matching_points')) else 0
        
        # Calculate current matching points (background counting)
        current_matching_points = FieldAllowanceService._get_matching_points_with_qualification(
            user.id, db, qualification_status["qualified"]
        )
        
        # If opportunity missed, show frozen points; otherwise show current points (but only if qualified)
        if is_opportunity_missed:
            display_points = frozen_points
        elif qualification_status["qualified"]:
            display_points = current_matching_points
        else:
            # Not qualified yet - hide the actual count (show 0)
            display_points = 0
        
        requirement = {
            "name": "Car Allowance (Premium)",
            "monthly_amount": 25000,
            "tenure_months": 72,
            "total_value": 1800000,
            
            "initial_requirements": {
                "matching_points": {
                    "required": 250,
                    "current": display_points,
                    "remaining": max(0, 250 - display_points),
                    "progress_percentage": min(100, round((display_points / 250) * 100, 2)),
                    "description": "Achieve 250 matching points within 90 days",
                    "is_frozen": is_opportunity_missed,
                    "qualification_status": qualification_status
                },
                "timeframe": {
                    "days": 90,
                    "description": "Complete within 90 days from registration"
                }
            },
            
            "monthly_requirements": {
                "matching_pairs": {
                    "required": 40,
                    "current": eligibility.monthly_achieved_matchings if eligibility else 0,
                    "remaining": max(0, 40 - (eligibility.monthly_achieved_matchings if eligibility else 0)),
                    "progress_percentage": min(100, round(((eligibility.monthly_achieved_matchings if eligibility else 0) / 40) * 100, 2)),
                    "description": "Maintain 40 matching pairs per month"
                }
            },
            
            "status": {
                "is_eligible": eligibility.initial_eligibility_met if eligibility else False,
                "overall_status": eligibility.overall_status if eligibility else "Not Eligible",
                "months_completed": eligibility.months_completed if eligibility else 0,
                "months_remaining": max(0, 72 - (eligibility.months_completed if eligibility else 0)),
                "total_paid": float(eligibility.total_paid_to_date if eligibility else 0),
                "opportunity_missed": is_opportunity_missed
            },
            
            "target_dates": {
                "initial_eligibility_deadline": FieldAllowanceService._calculate_deadline(start_date, 90) if start_date else None,
                "initial_achieved_date": eligibility.initial_eligibility_date.isoformat() if eligibility and eligibility.initial_eligibility_date else None,
                "expected_completion": FieldAllowanceService._calculate_expected_completion(eligibility, 72) if eligibility else None,
                "next_payment_date": FieldAllowanceService._calculate_next_payment_date(eligibility) if eligibility else None
            }
        }
        
        return requirement
    
    @staticmethod
    def _check_binary_qualification(user_id: int, db: Session) -> Dict[str, Any]:
        """
        Check binary qualification using UNIVERSAL ELIGIBILITY (POINTS-based)
        
        Requirements:
        1. 1:1 Direct Active POINTS (1+ point on BOTH left and right legs)
        2. 2:1 or 1:2 Matching POINTS (2 points on one leg, 1 on other)
        
        Package Points:
        - Diamond (₹7,500) = 0.5 points
        - Platinum (₹15,000) = 1.0 points
        """
        from app.services.award_service import AwardService
        
        award_service = AwardService(db)
        eligibility = award_service.check_universal_eligibility(str(user_id))
        
        qualified = eligibility['is_eligible']
        left_points = eligibility.get('left_points', 0)
        right_points = eligibility.get('right_points', 0)
        
        if qualified:
            message = f"Qualified with Group A:{left_points} / Group B:{right_points} points (meets 1:1 + 2:1/1:2 requirements)"
        else:
            failed_checks = [check for check in eligibility['failed_checks'] if check]
            message = f"Not qualified. {'; '.join(failed_checks)}"
        
        return {
            "qualified": qualified,
            "group_a_points": left_points,
            "group_b_points": right_points,
            "left_active": left_points,
            "right_active": right_points,
            "message": message
        }
    
    @staticmethod
    def _get_matching_points_with_qualification(user_id: int, db: Session, is_qualified: bool) -> int:
        """
        Calculate total matching points for the user
        Background counting: Always calculate, but only reveal if qualified
        """
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return 0
        
        package_points = {
            'Platinum': 1.0,
            'Diamond': 0.5,
            'Blue': 0,
            'Loyal': 0
        }
        
        left_points = FieldAllowanceService._calculate_leg_points(user_id, 'L', db, package_points)
        right_points = FieldAllowanceService._calculate_leg_points(user_id, 'R', db, package_points)
        
        # Calculate actual matching points (always happens in background)
        actual_points = int(min(left_points, right_points))
        
        # Return actual points (caller decides whether to display based on qualification)
        return actual_points
    
    @staticmethod
    def _get_matching_points(user_id: int, db: Session) -> int:
        """Calculate total matching points for the user (legacy method)"""
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return 0
        
        package_points = {
            'Platinum': 1.0,
            'Diamond': 0.5,
            'Blue': 0,
            'Loyal': 0
        }
        
        left_points = FieldAllowanceService._calculate_leg_points(user_id, 'L', db, package_points)
        right_points = FieldAllowanceService._calculate_leg_points(user_id, 'R', db, package_points)
        
        return int(min(left_points, right_points))
    
    @staticmethod
    def _calculate_leg_points(user_id: int, leg: str, db: Session, package_points: Dict[str, float]) -> float:
        """Calculate points for a specific leg"""
        total = 0.0
        
        direct_children = db.query(User).filter(
            User.referrer_id == str(user_id),
            User.position.in_(['L', 'LEFT']) if leg == 'L' else User.position.in_(['R', 'RIGHT']),
            User.coupon_status == 'Activated'
        ).all()
        
        for child in direct_children:
            # Use package_points directly from user model (1.0=Platinum, 0.5=Diamond, 0=Blue/Loyal)
            child_points = float(child.package_points) if child.package_points else 0
            total += child_points
            total += FieldAllowanceService._calculate_leg_points(child.id, leg, db, package_points)
        
        return total
    
    @staticmethod
    def _calculate_deadline(start_date, days: int) -> Optional[str]:
        """Calculate deadline date from start date"""
        if not start_date:
            return None
        deadline = start_date + timedelta(days=days)
        return deadline.isoformat()
    
    @staticmethod
    def _calculate_expected_completion(eligibility, tenure_months: int) -> Optional[str]:
        """Calculate expected completion date"""
        if not eligibility or not eligibility.initial_eligibility_date:
            return None
        completion = eligibility.initial_eligibility_date + timedelta(days=tenure_months * 30)
        return completion.isoformat()
    
    @staticmethod
    def _calculate_next_payment_date(eligibility) -> Optional[str]:
        """Calculate next payment date"""
        if not eligibility or not eligibility.is_claimable:
            return None
        
        if eligibility.payment_date:
            next_payment = eligibility.payment_date + timedelta(days=30)
        elif eligibility.initial_eligibility_date:
            next_payment = eligibility.initial_eligibility_date + timedelta(days=30)
        else:
            return None
        
        return next_payment.isoformat()
    
    @staticmethod
    def _get_active_allowance(user_id: int, db: Session) -> Optional[str]:
        """Determine which allowance is currently active"""
        car_allowance = db.query(CarAllowanceEligibility).filter(
            CarAllowanceEligibility.user_id == str(user_id),
            CarAllowanceEligibility.overall_status == 'Active'
        ).first()
        
        if car_allowance:
            return "car"
        
        standard_allowance = db.query(FieldAllowanceEligibility).filter(
            FieldAllowanceEligibility.user_id == str(user_id),
            FieldAllowanceEligibility.overall_status == 'Active'
        ).first()
        
        if standard_allowance:
            return "standard"
        
        return None
    
    @staticmethod
    def get_all_users_allowance_summary(db: Session) -> List[Dict[str, Any]]:
        """Get field allowance summary for all users (Admin view)"""
        
        users = db.query(User).filter(User.coupon_status == 'Activated').all()
        summary = []
        
        for user in users:
            standard = db.query(FieldAllowanceEligibility).filter(
                FieldAllowanceEligibility.user_id == str(user.id)
            ).first()
            
            car = db.query(CarAllowanceEligibility).filter(
                CarAllowanceEligibility.user_id == str(user.id)
            ).first()
            
            summary.append({
                "user_id": user.id,
                "user_name": user.name,
                "email": user.email,
                "standard_status": standard.overall_status if standard else "Not Started",
                "standard_paid": float(standard.total_paid_to_date if standard else 0),
                "car_status": car.overall_status if car else "Not Eligible",
                "car_paid": float(car.total_paid_to_date if car else 0),
                "active_allowance": FieldAllowanceService._get_active_allowance(user.id, db)
            })
        
        return summary
