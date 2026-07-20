"""
Dashboard Service for FastAPI - Dashboard Data Aggregation
Preserves exact Flask dashboard data structure and calculations
"""

from typing import List, Dict, Optional, Any
from datetime import datetime, date, timedelta
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc, asc

from app.models.user import User
from app.models.placement import Placement
from app.models.transaction import Transaction, CompanyEarnings, VedIncome, PendingIncome
from app.models.coupon import Coupon, CouponActivationTracker
from app.models.awards import DirectAwardTier, UserAwardProgress, MatchingAwardTier, UserMatchingAwardProgress
from app.models.bonanza import DynamicBonanza  # DC Protocol: BonanzaProgress deprecated
from app.models.field_allowance import FieldAllowanceProgress, AllowanceSchemeSelector
from app.services.reference_service import ReferenceService
from app.services.user_service import UserService
from app.services.award_service import AwardService
from app.models.base import get_indian_time

class DashboardService:
    """
    Dashboard Service handling all dashboard data aggregation and calculations
    Preserves exact Flask dashboard data structure
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.reference_service = ReferenceService(db)
        self.user_service = UserService(db)
        self.award_service = AwardService(db)
    
    def get_user_dashboard(self, user_id: str) -> Dict[str, Any]:
        """
        Get comprehensive user dashboard data
        Preserves Flask dashboard structure with all 9 sections
        """
        user = self.user_service.get_user_by_id(user_id)
        if not user:
            return {"error": "User not found"}
        
        current_month = datetime.now().strftime("%Y-%m")
        
        # 1. Personal Information Section
        personal_info = {
            "user_id": user.id,
            "name": user.name,
            "email": user.email,
            "mobile": user.phone_number,
            "registration_date": user.registration_date.isoformat() if user.registration_date else None,
            "user_type": user.user_type,
            "current_package": getattr(user, 'current_package_type', 'none'),
            "account_status": "Active" if user.activation_date is not None else "Inactive",
            "is_red_coupon": getattr(user, 'is_red_coupon', False)
        }
        
        # 2. Financial Summary Section
        financial_summary = self._get_financial_summary(user_id, current_month)
        
        # 3. Team Statistics Section
        team_stats = self._get_team_statistics(user_id)
        
        # 4. Income Breakdown Section
        income_breakdown = self._get_income_breakdown(user_id, current_month)
        
        # 5. Award Progress Section
        award_progress = self._get_award_progress_summary(user_id)
        
        # 6. Coupon Management Section
        coupon_summary = self._get_coupon_summary(user_id)
        
        # 7. Bonanza Status Section
        bonanza_status = self._get_bonanza_status(user_id)
        
        # 8. Field Allowance Section
        field_allowance = self._get_field_allowance_status(user_id)
        
        # 9. Recent Activity Section
        recent_activity = self._get_recent_activity(user_id)
        
        return {
            "user_id": user_id,
            "dashboard_sections": {
                "personal_info": personal_info,
                "financial_summary": financial_summary,
                "team_statistics": team_stats,
                "income_breakdown": income_breakdown,
                "award_progress": award_progress,
                "coupon_management": coupon_summary,
                "bonanza_status": bonanza_status,
                "field_allowance": field_allowance,
                "recent_activity": recent_activity
            },
            "generated_at": get_indian_time().isoformat()
        }
    
    def _get_financial_summary(self, user_id: str, month: str) -> Dict[str, Any]:
        """
        DC Protocol Phase 1.7 Compliant: Financial summary from pending_income table
        Returns BOTH GROSS and NET earnings with full deduction breakdown
        """
        # LIFETIME EARNINGS (all-time from pending_income)
        lifetime_summary = self.db.query(
            func.sum(PendingIncome.gross_amount).label('total_gross'),
            func.sum(PendingIncome.net_amount).label('total_net'),
            func.sum(PendingIncome.gurudakshina_deduction).label('total_gd'),
            func.sum(PendingIncome.admin_deduction).label('total_admin'),
            func.sum(PendingIncome.tds_deduction).label('total_tds'),
            func.count(PendingIncome.id).label('total_count')
        ).filter(
            PendingIncome.user_id == user_id
        ).first()
        
        # CURRENT MONTH EARNINGS (from pending_income with business_date filter)
        # Parse month as YYYY-MM and create date range
        month_start = datetime.strptime(f"{month}-01", "%Y-%m-%d")
        if month_start.month == 12:
            month_end = datetime(month_start.year + 1, 1, 1)
        else:
            month_end = datetime(month_start.year, month_start.month + 1, 1)
        
        current_month_summary = self.db.query(
            func.sum(PendingIncome.gross_amount).label('month_gross'),
            func.sum(PendingIncome.net_amount).label('month_net'),
            func.sum(PendingIncome.gurudakshina_deduction).label('month_gd'),
            func.sum(PendingIncome.admin_deduction).label('month_admin'),
            func.sum(PendingIncome.tds_deduction).label('month_tds'),
            func.count(PendingIncome.id).label('month_count')
        ).filter(
            and_(
                PendingIncome.user_id == user_id,
                PendingIncome.business_date >= month_start,
                PendingIncome.business_date < month_end
            )
        ).first()
        
        # Extract values with safe defaults
        lifetime_gross = float(lifetime_summary.total_gross or 0)
        lifetime_net = float(lifetime_summary.total_net or 0)
        lifetime_gd_ded = float(lifetime_summary.total_gd or 0)
        lifetime_admin_ded = float(lifetime_summary.total_admin or 0)
        lifetime_tds_ded = float(lifetime_summary.total_tds or 0)
        lifetime_total_ded = lifetime_gd_ded + lifetime_admin_ded + lifetime_tds_ded
        lifetime_count = int(lifetime_summary.total_count or 0)
        
        month_gross = float(current_month_summary.month_gross or 0)
        month_net = float(current_month_summary.month_net or 0)
        month_gd_ded = float(current_month_summary.month_gd or 0)
        month_admin_ded = float(current_month_summary.month_admin or 0)
        month_tds_ded = float(current_month_summary.month_tds or 0)
        month_total_ded = month_gd_ded + month_admin_ded + month_tds_ded
        month_count = int(current_month_summary.month_count or 0)
        
        # Get total withdrawals from withdrawal_request table (BOTH GROSS and NET)
        from app.models.withdrawal import WithdrawalRequest
        withdrawal_summary = self.db.query(
            func.sum(WithdrawalRequest.withdrawal_amount).label('gross_withdrawn'),
            func.sum(WithdrawalRequest.final_payout).label('net_withdrawn')
        ).filter(
            and_(
                WithdrawalRequest.user_id == user_id,
                WithdrawalRequest.status == 'Completed'
            )
        ).first()
        
        total_withdrawn_gross = float(withdrawal_summary.gross_withdrawn or 0)
        total_withdrawn_net = float(withdrawal_summary.net_withdrawn or 0)
        
        # Calculate pending balances (BOTH GROSS and NET)
        pending_balance_net = lifetime_net - total_withdrawn_net
        pending_balance_gross = lifetime_gross - total_withdrawn_gross
        
        return {
            # LIFETIME SUMMARY (Overall Earnings)
            "lifetime": {
                "gross_earnings": round(lifetime_gross, 2),
                "net_earnings": round(lifetime_net, 2),
                "total_deductions": round(lifetime_total_ded, 2),
                "deduction_breakdown": {
                    "guru_dakshina": round(lifetime_gd_ded, 2),
                    "admin_charge": round(lifetime_admin_ded, 2),
                    "tds": round(lifetime_tds_ded, 2)
                },
                # BOTH GROSS and NET withdrawn (no reverse calculations!)
                "withdrawn_gross": round(total_withdrawn_gross, 2),
                "withdrawn_net": round(total_withdrawn_net, 2),
                # BOTH GROSS and NET pending
                "pending_balance_gross": round(pending_balance_gross, 2),
                "pending_balance_net": round(pending_balance_net, 2),
                # Legacy field (NET withdrawn for backward compatibility)
                "total_withdrawn": round(total_withdrawn_net, 2),
                "pending_balance": round(pending_balance_net, 2),
                "transaction_count": lifetime_count
            },
            # CURRENT MONTH SUMMARY
            "current_month": {
                "gross_earnings": round(month_gross, 2),
                "net_earnings": round(month_net, 2),
                "total_deductions": round(month_total_ded, 2),
                "deduction_breakdown": {
                    "guru_dakshina": round(month_gd_ded, 2),
                    "admin_charge": round(month_admin_ded, 2),
                    "tds": round(month_tds_ded, 2)
                },
                "transaction_count": month_count
            },
            # Legacy fields for backward compatibility
            "wallet_balance": round(pending_balance_net, 2),
            "lifetime_earnings": round(lifetime_net, 2)
        }
    
    def _get_team_statistics(self, user_id: str) -> Dict[str, Any]:
        """Get team statistics for dashboard using corrected binary tree logic"""
        team_counts = self.reference_service.get_team_counts(user_id)
        direct_referrals = self.db.query(User).filter(User.referrer_id == user_id).count()
        
        # Get active team members (registered in last 30 days)
        thirty_days_ago = datetime.now() - timedelta(days=30)
        recent_additions = self.db.query(User).filter(
            and_(
                User.referrer_id == user_id,
                User.registration_date >= thirty_days_ago
            )
        ).count()
        
        return {
            "binary_tree": {
                "left_count": team_counts["left_count"],
                "right_count": team_counts["right_count"],
                "total_count": team_counts["total_count"]
            },
            "direct_referrals": direct_referrals,
            "recent_additions": recent_additions,
            "team_balance": {
                "left_percentage": (team_counts["left_count"] / max(team_counts["total_count"], 1)) * 100,
                "right_percentage": (team_counts["right_count"] / max(team_counts["total_count"], 1)) * 100
            }
        }
    
    def _get_income_breakdown(self, user_id: str, month: str) -> Dict[str, Any]:
        """Get income breakdown by type for dashboard"""
        # Get comprehensive income summary from Reference System service
        income_summary = self.reference_service.get_comprehensive_income_summary(user_id, month)
        
        # Simplify for dashboard display
        return {
            "current_month": month,
            "income_streams": {
                "direct_referral": {
                    "amount": income_summary["income_streams"]["direct_referral"].get("total_income", 0),
                    "count": income_summary["income_streams"]["direct_referral"].get("referral_count", 0)
                },
                "matching_referral": {
                    "amount": income_summary["income_streams"]["matching_referral"].get("total_income", 0),
                    "pairs": income_summary["income_streams"]["matching_referral"].get("matching_pairs", 0)
                },
                "ved_income": {
                    "amount": income_summary["income_streams"]["ved_income"].get("ved_amount", 0),
                    "qualified": income_summary["income_streams"]["ved_income"].get("qualified", False)
                },
                "guru_dakshina": {
                    "amount": income_summary["income_streams"]["guru_dakshina"].get("guru_dakshina_amount", 0),
                    "qualified": income_summary["income_streams"]["guru_dakshina"].get("qualified", False)
                }
            },
            "total_monthly_income": income_summary["total_monthly_income"]
        }
    
    def _get_award_progress_summary(self, user_id: str) -> Dict[str, Any]:
        """Get award progress summary for dashboard"""
        direct_progress = self.award_service.get_user_direct_award_progress(user_id)
        matching_progress = self.award_service.get_user_matching_award_progress(user_id)
        
        # Count achievements
        direct_achieved = sum(1 for tier in direct_progress.get("tier_progress", []) if tier["achieved"])
        matching_achieved = sum(1 for tier in matching_progress.get("tier_progress", []) if tier["achieved"])
        
        # Get next achievable tier
        next_direct_tier = None
        next_matching_tier = None
        
        for tier in direct_progress.get("tier_progress", []):
            if not tier["achieved"]:
                next_direct_tier = {
                    "tier_name": tier["tier_info"]["tier_name"],
                    "required_referrals": tier["tier_info"]["required_direct_referrals"],
                    "current_referrals": tier["current_direct_count"],
                    "progress_percentage": tier["progress_percentage"]
                }
                break
        
        for tier in matching_progress.get("tier_progress", []):
            if not tier["achieved"]:
                next_matching_tier = {
                    "tier_name": tier["tier_info"]["tier_name"],
                    "required_pairs": tier["tier_info"]["required_matching_pairs"],
                    "current_pairs": tier["current_matching_pairs"],
                    "progress_percentage": (tier["current_matching_pairs"] / tier["tier_info"]["required_matching_pairs"]) * 100 if tier["tier_info"]["required_matching_pairs"] > 0 else 0
                }
                break
        
        return {
            "achievements_summary": {
                "direct_awards_achieved": direct_achieved,
                "matching_awards_achieved": matching_achieved,
                "total_achievements": direct_achieved + matching_achieved
            },
            "next_targets": {
                "direct_award": next_direct_tier,
                "matching_award": next_matching_tier
            }
        }
    
    def _get_coupon_summary(self, user_id: str) -> Dict[str, Any]:
        """Get coupon summary for dashboard"""
        # Get active coupons
        active_coupons = self.db.query(Coupon).filter(
            and_(
                Coupon.owner_id == user_id,
                Coupon.status == 'Active'
            )
        ).all()
        
        # Get Red Coupon status
        red_coupon_tracker = self.db.query(CouponActivationTracker).filter(
            and_(
                CouponActivationTracker.user_id == user_id,
                CouponActivationTracker.status == 'Pending'
            )
        ).first()
        
        # Calculate total coupon value
        total_value = sum(coupon.package_value for coupon in active_coupons)
        
        return {
            "active_coupons": {
                "count": len(active_coupons),
                "total_value": float(total_value),
                "coupons": [
                    {
                        "coupon_code": coupon.coupon_code,
                        "package_type": coupon.package_type,
                        "package_value": float(coupon.package_value),
                        "issue_date": coupon.issue_date.isoformat() if coupon.issue_date else None
                    }
                    for coupon in active_coupons[:5]  # Show only first 5
                ]
            },
            "red_coupon_alert": {
                "is_red_coupon": getattr(self.user_service.get_user_by_id(user_id), 'is_red_coupon', False),
                "has_pending_activation": red_coupon_tracker is not None,
                "activation_deadline": red_coupon_tracker.activation_deadline.isoformat() if red_coupon_tracker else None,
                "days_remaining": (red_coupon_tracker.activation_deadline - get_indian_time()).days if red_coupon_tracker else None
            }
        }
    
    def _get_bonanza_status(self, user_id: str) -> Dict[str, Any]:
        """Get bonanza status for dashboard"""
        active_bonanzas = self.award_service.get_active_bonanzas()
        
        # DC Protocol: Get user's bonanza claims from DynamicBonanzaHistory
        from app.models.bonanza import DynamicBonanzaHistory
        user_bonanza_participations = []
        for bonanza in active_bonanzas:
            claim = self.db.query(DynamicBonanzaHistory).filter(
                and_(
                    DynamicBonanzaHistory.user_id == user_id,
                    DynamicBonanzaHistory.bonanza_id == bonanza["id"],
                    # DC PROTOCOL: Filter out legacy pre-Oct 21 awards (permanently hidden from users)
                    or_(
                        DynamicBonanzaHistory.is_legacy_pre_reset == False,
                        DynamicBonanzaHistory.is_legacy_pre_reset.is_(None)
                    )
                )
            ).first()
            
            if claim:
                user_bonanza_participations.append({
                    "bonanza_name": bonanza["campaign_name"],
                    "current_points": float(claim.direct_count_achieved or claim.matching_count_achieved or 0),
                    "rank_position": 0,  # Rank not tracked in new system
                    "eligible_for_reward": claim.processed_status in ['Admin Approved', 'Procurement Pending', 'Processed for Dispatch'],
                    "end_date": bonanza["end_date"]
                })
        
        return {
            "active_bonanzas_count": len(active_bonanzas),
            "user_participations": user_bonanza_participations,
            "available_bonanzas": [
                {
                    "campaign_name": bonanza["campaign_name"],
                    "end_date": bonanza["end_date"],
                    "total_reward_pool": bonanza["total_reward_pool"]
                }
                for bonanza in active_bonanzas[:3]  # Show only first 3
            ]
        }
    
    def _get_field_allowance_status(self, user_id: str) -> Dict[str, Any]:
        """Get field allowance status for dashboard"""
        # Get user's allowance scheme selection
        scheme_selector = self.db.query(AllowanceSchemeSelector).filter(
            AllowanceSchemeSelector.user_id == user_id
        ).first()
        
        # Get allowance progress
        allowance_progress = self.db.query(FieldAllowanceProgress).filter(
            FieldAllowanceProgress.user_id == user_id
        ).all()
        
        current_allowances = []
        for progress in allowance_progress:
            if progress.amount_paid and float(progress.amount_paid) > 0:
                current_allowances.append({
                    "allowance_type": progress.allowance_type,
                    "monthly_amount": float(progress.amount_paid),
                    "last_payment_date": progress.paid_at.isoformat() if progress.paid_at else None,
                    "total_paid": float(progress.amount_paid or 0),
                    "status": progress.status
                })
        
        return {
            "selected_scheme": scheme_selector.selected_scheme if scheme_selector else "none",
            "is_scheme_locked": scheme_selector.is_locked if scheme_selector else False,
            "current_allowances": current_allowances,
            "total_monthly_allowance": sum(allowance["monthly_amount"] for allowance in current_allowances)
        }
    
    def _get_recent_activity(self, user_id: str, limit: int = 10) -> Dict[str, Any]:
        """Get recent activity for dashboard"""
        # Get recent transactions
        recent_transactions = self.db.query(Transaction).filter(
            Transaction.user_id == user_id
        ).order_by(desc(Transaction.transaction_date)).limit(limit).all()
        
        # Get recent team additions
        recent_team_additions = self.db.query(User).filter(
            User.referrer_id == user_id
        ).order_by(desc(User.registration_date)).limit(5).all()
        
        activity_feed = []
        
        # Add transactions to activity feed
        for transaction in recent_transactions:
            activity_feed.append({
                "type": "transaction",
                "date": transaction.transaction_date.isoformat(),
                "description": f"{transaction.transaction_type.title()}: {transaction.income_type}",
                "amount": float(transaction.net_amount),
                "details": transaction.description
            })
        
        # Add team additions to activity feed
        for member in recent_team_additions:
            activity_feed.append({
                "type": "team_addition",
                "date": member.registration_date.isoformat() if member.registration_date else None,
                "description": f"New team member: {member.name}",
                "member_id": member.id,
                "details": f"Direct referral registered"
            })
        
        # Sort by date (most recent first)
        activity_feed.sort(key=lambda x: x["date"] or "", reverse=True)
        
        return {
            "recent_activities": activity_feed[:limit],
            "total_activities": len(activity_feed)
        }
    
    def get_admin_dashboard(self, admin_user_id: str) -> Dict[str, Any]:
        """
        Get admin dashboard with system-wide statistics
        Preserves Flask admin dashboard structure
        """
        admin_user = self.user_service.get_user_by_id(admin_user_id)
        if not admin_user or admin_user.user_type not in ['Admin', 'Finance Admin', 'Super Admin']:
            return {"error": "Access denied"}
        
        current_month = datetime.now().strftime("%Y-%m")
        
        # System Statistics
        system_stats = self._get_system_statistics()
        
        # Financial Overview
        financial_overview = self._get_admin_financial_overview(current_month)
        
        # User Growth Analytics
        user_growth = self._get_user_growth_analytics()
        
        # Top Performers
        top_performers = self._get_top_performers()
        
        # Recent System Activities
        recent_activities = self._get_recent_system_activities()
        
        return {
            "admin_user_id": admin_user_id,
            "admin_dashboard_sections": {
                "system_statistics": system_stats,
                "financial_overview": financial_overview,
                "user_growth_analytics": user_growth,
                "top_performers": top_performers,
                "recent_system_activities": recent_activities
            },
            "generated_at": get_indian_time().isoformat()
        }
    
    def _get_system_statistics(self) -> Dict[str, Any]:
        """Get system-wide statistics"""
        total_users = self.db.query(User).count()
        active_users = self.db.query(User).filter(User.activation_date.isnot(None)).count()
        total_placements = self.db.query(Placement).count()
        active_bonanzas = self.db.query(DynamicBonanza).filter(DynamicBonanza.status == 'active').count()
        
        return {
            "total_users": total_users,
            "active_users": active_users,
            "inactive_users": total_users - active_users,
            "total_placements": total_placements,
            "active_bonanzas": active_bonanzas,
            "system_health": "Operational"
        }
    
    def _get_admin_financial_overview(self, month: str) -> Dict[str, Any]:
        """Get financial overview for admin dashboard"""
        # Get company earnings for the month
        company_earnings = self.db.query(CompanyEarnings).filter(
            CompanyEarnings.financial_period == month
        ).first()
        
        # Get total payouts for the month
        total_payouts = self.db.query(func.sum(Transaction.net_amount)).filter(
            and_(
                Transaction.financial_period == month,
                Transaction.transaction_type == 'credit'
            )
        ).scalar() or Decimal('0.00')
        
        return {
            "current_month": month,
            "company_gross_income": float(company_earnings.gross_income) if company_earnings else 0.0,
            "total_member_payouts": float(total_payouts),
            "company_profit": float(company_earnings.net_profit) if company_earnings else 0.0,
            "profit_margin": float(company_earnings.profit_margin) if company_earnings else 0.0
        }
    
    def _get_user_growth_analytics(self) -> Dict[str, Any]:
        """Get user growth analytics"""
        # Get registrations for last 30 days
        thirty_days_ago = datetime.now() - timedelta(days=30)
        recent_registrations = self.db.query(User).filter(
            User.registration_date >= thirty_days_ago
        ).count()
        
        # Get registrations for last 7 days
        seven_days_ago = datetime.now() - timedelta(days=7)
        weekly_registrations = self.db.query(User).filter(
            User.registration_date >= seven_days_ago
        ).count()
        
        return {
            "monthly_growth": recent_registrations,
            "weekly_growth": weekly_registrations,
            "growth_rate": (recent_registrations / max(thirty_days_ago.day, 1)) * 100
        }
    
    def _get_top_performers(self, limit: int = 10) -> Dict[str, Any]:
        """Get top performing users"""
        current_month = datetime.now().strftime("%Y-%m")
        
        # Get top earners for current month
        top_earners = self.db.query(
            Transaction.user_id,
            func.sum(Transaction.net_amount).label('total_earnings')
        ).filter(
            and_(
                Transaction.financial_period == current_month,
                Transaction.transaction_type == 'credit'
            )
        ).group_by(Transaction.user_id).order_by(
            desc('total_earnings')
        ).limit(limit).all()
        
        top_performers_list = []
        for earner in top_earners:
            user = self.user_service.get_user_by_id(earner.user_id)
            if user:
                top_performers_list.append({
                    "user_id": user.id,
                    "name": user.name,
                    "total_earnings": float(earner.total_earnings),
                    "user_type": user.user_type
                })
        
        return {
            "top_earners": top_performers_list
        }
    
    def _get_recent_system_activities(self, limit: int = 20) -> Dict[str, Any]:
        """Get recent system activities for admin dashboard"""
        # Get recent transactions
        recent_transactions = self.db.query(Transaction).order_by(
            desc(Transaction.transaction_date)
        ).limit(limit).all()
        
        # Get recent user registrations
        recent_users = self.db.query(User).order_by(
            desc(User.registration_date)
        ).limit(10).all()
        
        activities = []
        
        # Add transactions
        for transaction in recent_transactions[:10]:
            user = self.user_service.get_user_by_id(transaction.user_id)
            activities.append({
                "type": "transaction",
                "date": transaction.transaction_date.isoformat(),
                "description": f"Transaction: {transaction.income_type}",
                "user_id": transaction.user_id,
                "user_name": user.name if user else "Unknown",
                "amount": float(transaction.net_amount)
            })
        
        # Add registrations
        for user in recent_users:
            activities.append({
                "type": "registration",
                "date": user.registration_date.isoformat() if user.registration_date else None,
                "description": f"New user registration",
                "user_id": user.id,
                "user_name": user.name,
                "amount": None
            })
        
        # Sort by date
        activities.sort(key=lambda x: x["date"] or "", reverse=True)
        
        return {
            "recent_activities": activities[:limit]
        }