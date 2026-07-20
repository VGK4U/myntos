"""
Banner and Communication System Service
Handles TOP Performers calculation, banner management, popups, and emails
"""

from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_, or_
from app.models.banner import Banner, CustomBanner, BannerSkippedUser, PopupMessage, UserCouponAcceptance, EmailTemplate
from app.models.system_control import TermsAndConditionsVersion
from app.models.user import User
from app.models.transaction import PendingIncome
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class BannerService:
    """Service for banner and communication system operations"""
    
    @staticmethod
    def calculate_top_earners(db: Session, limit: int = 7, exclude_skipped: bool = True) -> List[Dict[str, Any]]:
        """
        Calculate top earners based on LATEST EARNING DAY GROSS income
        Only shows users with > ₹1,000 on the latest day
        Args:
            db: Database session
            limit: Number of top earners to return (max 7)
            exclude_skipped: Whether to exclude skipped users
        Returns:
            List of top earners with user_id, name, total_earnings, rank, photo, badge
        """
        try:
            # Step 1: Find the LATEST DATE that has users with earnings > ₹1,000
            # This ensures we show the most recent valid data, not just today's empty data
            latest_date_with_earners = db.query(
                func.date(PendingIncome.business_date).label('earning_date')
            ).group_by(
                func.date(PendingIncome.business_date),
                PendingIncome.user_id
            ).having(
                func.sum(PendingIncome.gross_amount) > 1000
            ).order_by(
                desc(func.date(PendingIncome.business_date))
            ).limit(1).first()
            
            if not latest_date_with_earners:
                logger.warning("No earnings data found with users earning > ₹1,000")
                return []
            
            latest_date = latest_date_with_earners[0]
            logger.info(f"Latest earning date with valid earners: {latest_date}")
            
            # Step 2: Get earnings for that specific date, grouped by user
            earnings_query = db.query(
                PendingIncome.user_id,
                func.sum(PendingIncome.gross_amount).label('total_earnings')
            ).filter(
                func.date(PendingIncome.business_date) == latest_date
            ).group_by(
                PendingIncome.user_id
            ).having(
                func.sum(PendingIncome.gross_amount) > 1000  # Only > ₹1,000
            )
            
            # Step 3: Exclude skipped users if requested
            if exclude_skipped:
                skipped_user_ids = db.query(BannerSkippedUser.user_id).filter(
                    BannerSkippedUser.is_active == True
                ).all()
                skipped_ids = [user_id[0] for user_id in skipped_user_ids]
                if skipped_ids:
                    earnings_query = earnings_query.filter(
                        PendingIncome.user_id.notin_(skipped_ids)
                    )
            
            # Step 4: Order by total earnings DESC and limit to 7
            top_earners_data = earnings_query.order_by(
                desc('total_earnings')
            ).limit(limit).all()
            
            # Step 5: Get user details with photo and badge
            # DC Protocol (Jan 31, 2026): Exclude Suspended/Inactive users from top performers
            top_earners = []
            for rank, (user_id, total_earnings) in enumerate(top_earners_data, start=1):
                user = db.query(User).filter(User.id == user_id).first()
                # Only include Active users
                if user and user.account_status == 'Active':
                    # Determine badge based on earnings
                    badge = None
                    if total_earnings >= 50000:
                        badge = "🏆 Diamond"
                    elif total_earnings >= 25000:
                        badge = "💎 Platinum"
                    elif total_earnings >= 10000:
                        badge = "🥇 Gold"
                    elif total_earnings >= 5000:
                        badge = "🥈 Silver"
                    elif total_earnings >= 1000:
                        badge = "🥉 Bronze"
                    
                    top_earners.append({
                        'user_id': user.id,
                        'name': user.name,
                        'total_earnings': float(total_earnings or 0),
                        'rank': rank,
                        'photo_url': user.profile_photo if hasattr(user, 'profile_photo') else None,
                        'badge': badge,
                        'latest_earning_date': latest_date.isoformat() if latest_date else None
                    })
            
            logger.info(f"Found {len(top_earners)} top performers for {latest_date}")
            return top_earners
            
        except Exception as e:
            logger.error(f"Error calculating top earners: {str(e)}")
            return []
    
    @staticmethod
    def calculate_top_earners_vgk4u(db: Session, limit: int = 7, exclude_skipped: bool = True) -> List[Dict[str, Any]]:
        """
        Calculate top VGK4U earners from vgk_team_income_entries.

        DC_AUDIENCE_001 / DC_VGK_TOP_EARNERS_001 (audit #35 follow-up, Phase A1):
        Mirrors :meth:`calculate_top_earners` (MNR) but reads from the VGK
        ledger and ranks ``OfficialPartner`` rows where ``category='VGK_TEAM'``.
        Confirmed entries only (status='CONFIRMED'). Same ₹1,000/day floor.

        ``exclude_skipped`` is accepted for signature parity but currently a
        no-op — a separate VGK skip table will be added in a later phase.
        Returns an empty list on any internal failure (never raises) so the
        endpoint stays resilient if vgk schema is missing on older DBs.
        """
        try:
            # DC_AUDIENCE_001 — master-switch gate.  Returns [] silently
            # when the global vgk4u_enabled SystemControl flag is off so
            # MNR-only deployments never accidentally surface VGK data.
            from app.core.audience_resolver import is_vgk4u_enabled
            if not is_vgk4u_enabled(db):
                return []

            from app.models.staff_accounts import VGKTeamIncomeEntry, OfficialPartner

            # Step 1: latest day with > ₹1,000 commission for at least one partner.
            latest_date_row = db.query(
                func.date(VGKTeamIncomeEntry.created_at).label('earning_date')
            ).filter(
                VGKTeamIncomeEntry.status == 'CONFIRMED'
            ).group_by(
                func.date(VGKTeamIncomeEntry.created_at),
                VGKTeamIncomeEntry.partner_id
            ).having(
                func.sum(VGKTeamIncomeEntry.commission_amount) > 1000
            ).order_by(
                desc(func.date(VGKTeamIncomeEntry.created_at))
            ).limit(1).first()

            if not latest_date_row:
                logger.info("[DC_VGK_TOP_EARNERS_001] No VGK4U earnings > ₹1,000 yet")
                return []

            latest_date = latest_date_row[0]

            # Step 2: per-partner totals for that date.
            earnings = db.query(
                VGKTeamIncomeEntry.partner_id,
                func.sum(VGKTeamIncomeEntry.commission_amount).label('total_earnings')
            ).filter(
                VGKTeamIncomeEntry.status == 'CONFIRMED',
                func.date(VGKTeamIncomeEntry.created_at) == latest_date
            ).group_by(
                VGKTeamIncomeEntry.partner_id
            ).having(
                func.sum(VGKTeamIncomeEntry.commission_amount) > 1000
            ).order_by(
                desc('total_earnings')
            ).limit(limit).all()

            # Step 3: enrich with partner profile + badge tier (mirror MNR).
            results: List[Dict[str, Any]] = []
            for rank, (partner_id, total_earnings) in enumerate(earnings, start=1):
                partner = db.query(OfficialPartner).filter(
                    OfficialPartner.id == partner_id,
                    OfficialPartner.is_active == True,
                ).first()
                if not partner:
                    continue

                amt = float(total_earnings or 0)
                if amt >= 50000:
                    badge = "🏆 Diamond"
                elif amt >= 25000:
                    badge = "💎 Platinum"
                elif amt >= 10000:
                    badge = "🥇 Gold"
                elif amt >= 5000:
                    badge = "🥈 Silver"
                else:
                    badge = "🥉 Bronze"

                results.append({
                    'user_id': partner.partner_code,
                    'name': partner.partner_name,
                    'total_earnings': amt,
                    'rank': rank,
                    'photo_url': getattr(partner, 'logo_path', None),
                    'badge': badge,
                    'latest_earning_date': latest_date.isoformat() if latest_date else None,
                })

            logger.info(f"[DC_VGK_TOP_EARNERS_001] {len(results)} VGK4U top earners for {latest_date}")
            return results

        except Exception as e:
            logger.error(f"[DC_VGK_TOP_EARNERS_001] VGK4U top earners failed safely: {e}")
            return []

    @staticmethod
    def skip_user_from_banner(db: Session, user_id: str, skipped_by: str, reason: Optional[str] = None) -> Dict[str, Any]:
        """Skip a user from top earners banner display"""
        try:
            # Check if user exists
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                return {"success": False, "message": "User not found"}
            
            # Check if already skipped
            existing_skip = db.query(BannerSkippedUser).filter(
                BannerSkippedUser.user_id == user_id,
                BannerSkippedUser.is_active == True
            ).first()
            
            if existing_skip:
                return {"success": False, "message": "User is already skipped from banner"}
            
            # Create or update skip record
            skip_record = BannerSkippedUser(
                user_id=user_id,
                skipped_by=skipped_by,
                skipped_date=datetime.utcnow(),
                is_active=True,
                reason=reason or f"Skipped by {skipped_by}"
            )
            
            db.add(skip_record)
            db.commit()
            
            return {"success": True, "message": f"User {user.name} skipped from top earners banner"}
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error skipping user from banner: {str(e)}")
            return {"success": False, "message": f"Error skipping user: {str(e)}"}
    
    @staticmethod
    def reactivate_user_for_banner(db: Session, user_id: str) -> Dict[str, Any]:
        """Reactivate a skipped user for top earners banner display"""
        try:
            skip_record = db.query(BannerSkippedUser).filter(
                BannerSkippedUser.user_id == user_id,
                BannerSkippedUser.is_active == True
            ).first()
            
            if not skip_record:
                return {"success": False, "message": "No active skip record found for this user"}
            
            skip_record.is_active = False
            db.commit()
            
            user = db.query(User).filter(User.id == user_id).first()
            user_name = user.name if user else "Unknown"
            
            return {"success": True, "message": f"User {user_name} reactivated for top earners banner"}
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error reactivating user for banner: {str(e)}")
            return {"success": False, "message": f"Error reactivating user: {str(e)}"}
    
    @staticmethod
    def get_active_custom_banners(db: Session) -> List[CustomBanner]:
        """Get all active custom banners sorted by priority and display order"""
        try:
            now = datetime.utcnow()
            return db.query(CustomBanner).filter(
                CustomBanner.is_active == True,
                or_(
                    CustomBanner.show_start_date.is_(None),
                    CustomBanner.show_start_date <= now
                ),
                or_(
                    CustomBanner.show_end_date.is_(None),
                    CustomBanner.show_end_date >= now
                )
            ).order_by(
                CustomBanner.priority.asc(),
                CustomBanner.display_order.asc()
            ).all()
        except Exception as e:
            logger.error(f"Error getting active custom banners: {str(e)}")
            return []
    
    @staticmethod
    def get_active_image_banners(db: Session) -> List[Banner]:
        """Get all active approved image banners"""
        try:
            return db.query(Banner).filter(
                Banner.status == 'Active'
            ).order_by(
                Banner.display_order.asc()
            ).all()
        except Exception as e:
            logger.error(f"Error getting active image banners: {str(e)}")
            return []
    
    @staticmethod
    def get_popups_for_page(db: Session, page: str) -> List[PopupMessage]:
        """Get active popups for a specific page"""
        try:
            now = datetime.utcnow()
            return db.query(PopupMessage).filter(
                PopupMessage.target_page == page,
                PopupMessage.status == 'Approved',
                PopupMessage.is_active == True,
                or_(
                    PopupMessage.show_start_date.is_(None),
                    PopupMessage.show_start_date <= now
                ),
                or_(
                    PopupMessage.show_end_date.is_(None),
                    PopupMessage.show_end_date >= now
                )
            ).order_by(
                PopupMessage.priority.asc()
            ).all()
        except Exception as e:
            logger.error(f"Error getting popups for page {page}: {str(e)}")
            return []
    
    @staticmethod
    def check_coupon_acceptance(db: Session, user_id: str) -> Dict[str, Any]:
        """
        Check if user should see coupon benefits popup
        Returns dict with should_show_popup, attempt_number, remaining_attempts
        NOTE: Only shows once per login session (not on every page refresh)
        """
        try:
            # Get user to check coupon status
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                return {'should_show_popup': False, 'attempt_number': None, 'remaining_attempts': 0}
            
            # Exempt admin users
            admin_user_types = ['Admin', 'Operations', 'Finance Admin', 'Accounts', 'Super Admin', 'Super Login', 'RVZ ID']
            if user.user_type in admin_user_types:
                return {'should_show_popup': False, 'attempt_number': None, 'remaining_attempts': 0}
            
            # Only show for Active coupon status users
            if user.coupon_status != 'Active':
                return {'should_show_popup': False, 'attempt_number': None, 'remaining_attempts': 0}
            
            # Count existing acceptances
            acceptance_count = db.query(UserCouponAcceptance).filter(
                UserCouponAcceptance.user_id == user_id
            ).count()
            
            if acceptance_count >= 3:
                return {'should_show_popup': False, 'attempt_number': None, 'remaining_attempts': 0}
            
            # Check if popup was already shown recently (within last 2 hours)
            # This prevents showing on every page refresh during the same login session
            from datetime import datetime, timedelta
            recent_check = datetime.utcnow() - timedelta(hours=2)
            recent_acceptance = db.query(UserCouponAcceptance).filter(
                UserCouponAcceptance.user_id == user_id,
                UserCouponAcceptance.acceptance_timestamp >= recent_check
            ).order_by(UserCouponAcceptance.acceptance_timestamp.desc()).first()
            
            if recent_acceptance:
                # Already shown in this login session (within last 2 hours)
                return {'should_show_popup': False, 'attempt_number': None, 'remaining_attempts': 0}
            
            next_attempt = acceptance_count + 1
            remaining = 3 - acceptance_count
            
            return {
                'should_show_popup': True,
                'attempt_number': next_attempt,
                'remaining_attempts': remaining
            }
            
        except Exception as e:
            logger.error(f"Error checking coupon acceptance for user {user_id}: {str(e)}")
            return {'should_show_popup': False, 'attempt_number': None, 'remaining_attempts': 0}
    
    @staticmethod
    def record_coupon_acceptance(
        db: Session,
        user_id: str,
        attempt_number: int,
        ip_address: str,
        user_agent: Optional[str] = None
    ) -> Dict[str, Any]:
        """Record user's coupon acceptance"""
        try:
            # Check if already recorded
            existing = db.query(UserCouponAcceptance).filter(
                UserCouponAcceptance.user_id == user_id,
                UserCouponAcceptance.login_attempt_number == attempt_number
            ).first()
            
            if existing:
                return {
                    'success': False,
                    'message': f'Login attempt {attempt_number} already recorded',
                    'attempt_number': attempt_number
                }
            
            # Get active T&C version from database
            active_version = db.query(TermsAndConditionsVersion).filter(
                TermsAndConditionsVersion.is_active == True
            ).first()
            active_version_str = active_version.version if active_version else '1.0'
            
            # Create acceptance record
            acceptance = UserCouponAcceptance(
                user_id=user_id,
                login_attempt_number=attempt_number,
                ip_address=ip_address[:45],  # Truncate for IPv6
                user_agent=user_agent,
                accepted_terms_version=active_version_str,
                acceptance_timestamp=datetime.utcnow()
            )
            
            db.add(acceptance)
            db.commit()
            
            logger.info(f"✅ Coupon acceptance recorded: User {user_id}, Attempt {attempt_number}")
            
            return {
                'success': True,
                'message': f'Acceptance recorded successfully for attempt {attempt_number}',
                'attempt_number': attempt_number
            }
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error recording coupon acceptance: {str(e)}")
            return {
                'success': False,
                'message': f'Error recording acceptance: {str(e)}',
                'attempt_number': attempt_number
            }
