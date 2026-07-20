"""
Award Processing Service for Multi-Role Approval Workflow
DC Protocol: All operations are staff-only. MNR admin types permanently removed.
Staff actors identified by emp_code (staff_actor_id) for audit trail.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc, text

from app.models.user import User
from app.models.awards import UserAwardProgress, UserMatchingAwardProgress, AwardAuditLog, DirectAwardTier, MatchingAwardTier
from app.models.bonanza import DynamicBonanza, DynamicBonanzaReward, DynamicBonanzaHistory, Bonanza  # DC Protocol: BonanzaProgress deprecated
from app.models.transaction import Transaction, CompanyEarnings, Expense, PendingIncome
from app.models.expense_category import ExpenseSubCategory
from app.models.system import SystemCheckpoint
from app.models.base import get_indian_time
from app.constants.award_statuses import AwardStatus, normalize_status  # DC Protocol: Centralized status values

logger = logging.getLogger(__name__)

# DC PROTOCOL: Production start date checkpoint
# Awards achieved before this date are permanently hidden from all roles
PRODUCTION_START_CHECKPOINT_NAME = 'awards_production_start'


def parse_date_filter(date_str: Optional[str]) -> Optional[datetime]:
    """
    Parse date filter string (YYYY-MM-DD or ISO format) into datetime object
    Returns None if date_str is None or invalid
    """
    if not date_str:
        return None
    
    try:
        # Try parsing ISO format first (YYYY-MM-DDTHH:MM:SS)
        return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
    except (ValueError, AttributeError):
        try:
            # Try parsing just YYYY-MM-DD
            return datetime.strptime(date_str, '%Y-%m-%d')
        except (ValueError, TypeError):
            return None


class AwardProcessingService:
    """
    Service for processing awards through multi-role approval chain
    
    DC PROTOCOL: Oct 21, 2025 Production Start Date Enforcement
    - All queries filter out awards where is_legacy_pre_reset = TRUE
    - Checkpoint date stored in system_checkpoints table
    - Legacy awards remain in database for audit but are hidden from ALL roles
    """
    
    def __init__(self, db: Session):
        self.db = db
        self._production_start_date_cache = None
    
    def _check_is_legacy_award(self, user_id: str) -> bool:
        """
        DC PROTOCOL: Centralized legacy award check
        
        Determines if a user's awards should be marked as legacy (pre-Oct 21, 2025)
        based on their activation date vs production start checkpoint.
        
        Args:
            user_id: User's MNR ID
            
        Returns:
            True if user activated before production start (legacy award)
            False if user activated on/after production start (production award)
            
        Raises:
            ValueError if production start checkpoint is missing
        """
        from datetime import datetime as dt, date
        
        # Get production start date from system checkpoint (single source of truth)
        production_start_date_dt = self.get_production_start_date()
        production_start_date = production_start_date_dt.date() if isinstance(production_start_date_dt, dt) else production_start_date_dt
        
        # Get user's activation date
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user or not user.activation_date:
            # No activation date = treat as legacy (safety measure)
            return True
        
        user_activation_date = user.activation_date.date() if isinstance(user.activation_date, dt) else user.activation_date
        
        # Return True if user activated before production start (is legacy)
        return user_activation_date < production_start_date
    
    def get_production_start_date(self) -> datetime:
        """
        Get production start date from system_checkpoints table
        
        Returns:
            datetime: Production start date (Oct 21, 2025)
        
        DC PROTOCOL: Single source of truth for reset date
        Raises RuntimeError if checkpoint is missing (fail-fast)
        """
        if self._production_start_date_cache:
            return self._production_start_date_cache
        
        checkpoint = self.db.query(SystemCheckpoint).filter(
            SystemCheckpoint.checkpoint_name == PRODUCTION_START_CHECKPOINT_NAME
        ).first()
        
        if not checkpoint:
            # DC PROTOCOL: FAIL LOUDLY if checkpoint is missing
            # This prevents silent fallback to hardcoded dates
            raise RuntimeError(
                f"CRITICAL: System checkpoint '{PRODUCTION_START_CHECKPOINT_NAME}' not found in database. "
                f"Run migration to create checkpoint or contact system administrator."
            )
        
        self._production_start_date_cache = checkpoint.checkpoint_date
        return checkpoint.checkpoint_date
    
    def apply_legacy_filter(self, query, model_class):
        """
        Apply is_legacy_pre_reset filter to award queries
        
        DC PROTOCOL: Centralized filtering to exclude legacy pre-Oct 21 awards
        
        Args:
            query: SQLAlchemy query object
            model_class: UserAwardProgress, UserMatchingAwardProgress, or DynamicBonanzaHistory
        
        Returns:
            Query with is_legacy_pre_reset filter applied
        
        Usage:
            query = self.apply_legacy_filter(query, UserAwardProgress)
        """
        # Filter out legacy awards (is_legacy_pre_reset = FALSE or NULL)
        # NULL is treated as FALSE (default for existing records)
        return query.filter(
            or_(
                model_class.is_legacy_pre_reset == False,
                model_class.is_legacy_pre_reset.is_(None)
            )
        )
    
    def _is_award_dynamically_achieved(self, award, tier, user_id: str, award_type: str) -> bool:
        """
        DC PROTOCOL: Calculate if award is achieved using SAME logic as user dashboard
        
        This ensures admin panel shows IDENTICAL data to what users see.
        
        Args:
            award: UserAwardProgress or UserMatchingAwardProgress record
            tier: DirectAwardTier or MatchingAwardTier record
            user_id: User's ID
            award_type: 'direct' or 'matching'
        
        Returns:
            True if user dynamically achieves this award, False otherwise
        """
        from app.services.award_service import AwardService
        from datetime import date, datetime
        
        # DC PROTOCOL: Short-circuit for legacy pre-Oct 21 awards
        # These awards are permanently hidden from all roles
        if hasattr(award, 'is_legacy_pre_reset') and award.is_legacy_pre_reset:
            return False
        
        AWARDS_RESET_DATE = date(2025, 10, 21)
        
        # Get user activation date
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return False
        
        user_activation_date = user.activation_date.date() if isinstance(user.activation_date, datetime) else user.activation_date
        
        # Determine if this is a pre-Oct 21 user (reset logic applies)
        reset_filter_applied = user_activation_date and user_activation_date < AWARDS_RESET_DATE
        
        # Calculate total points based on award type
        if award_type == 'direct':
            # Count direct referral points with date filtering
            if reset_filter_applied:
                total_points = self.db.query(func.sum(User.package_points)).filter(
                    User.referrer_id == user_id,
                    User.coupon_status == 'Activated',
                    User.activation_date >= AWARDS_RESET_DATE
                ).scalar() or 0.0
            else:
                total_points = self.db.query(func.sum(User.package_points)).filter(
                    User.referrer_id == user_id,
                    User.coupon_status == 'Activated'
                ).scalar() or 0.0
        else:  # matching
            # CRITICAL FIX: Use SAME SQL function as user dashboard for matching awards
            # This ensures Oct 21 reset logic is properly applied
            from app.services.sql_utils import get_matching_pairs_with_reset_logic_sql
            
            if reset_filter_applied:
                # Pre-Oct 21 user: Only count users activated ON or AFTER Oct 21
                reset_date_str = AWARDS_RESET_DATE.isoformat()
                matching_result = get_matching_pairs_with_reset_logic_sql(self.db, user_id, reset_date_str)
            else:
                # Post-Oct 21 user: Count all users (no reset filter)
                matching_result = get_matching_pairs_with_reset_logic_sql(self.db, user_id, None)
            
            total_points = matching_result['matching_pairs']
        
        # Get bonanza deductions
        award_service = AwardService(self.db)
        bonanza_data = award_service.get_bonanza_deduction(user_id, award_type)
        total_bonanza_deductions = bonanza_data.get('total_deduction', 0)
        
        # Calculate effective points after bonanza deductions
        effective_points = max(0, total_points - total_bonanza_deductions)
        
        # Determine if achieved
        dynamically_achieved = effective_points >= tier.cumulative_required
        
        # For pre-Oct 21 users, ONLY use dynamic calculation (ignore stale DB records)
        # For post-Oct 21 users, use hybrid logic (dynamic OR database)
        if reset_filter_applied:
            return dynamically_achieved
        else:
            # Hybrid: dynamic OR database record shows achievement
            if award_type == 'direct':
                database_achieved = award.effective_progress_count >= tier.cumulative_required if award.effective_progress_count is not None else False
            else:  # matching
                database_achieved = (
                    award.effective_matching_count >= tier.cumulative_required 
                    if hasattr(award, 'effective_matching_count') and award.effective_matching_count is not None 
                    else False
                )
            return dynamically_achieved or database_achieved
    
    # ========== ADMIN ROLE FUNCTIONS ==========
    
    def get_pending_awards_for_admin(
        self,
        award_type: Optional[str] = None,
        user_id: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> Dict[str, Any]:
        """
        Get all awards pending admin review
        Status: 'Pending' or 'pending'
        """
        results = []
        
        # Query direct awards if requested
        if not award_type or award_type == 'direct':
            # DC PROTOCOL: Fetch all pending awards, then filter using SAME dynamic logic as user dashboard
            # This ensures admin sees IDENTICAL data to what users see
            direct_query = self.db.query(UserAwardProgress).join(
                DirectAwardTier, UserAwardProgress.award_tier_id == DirectAwardTier.id
            )
            
            # DC PROTOCOL: Filter out legacy pre-Oct 21 awards (permanently hidden from all roles)
            direct_query = self.apply_legacy_filter(direct_query, UserAwardProgress)
            
            direct_query = direct_query.filter(
                or_(
                    UserAwardProgress.processed_status == 'Pending',
                    UserAwardProgress.processed_status == 'pending',
                    UserAwardProgress.processed_status == 'returned_for_correction'
                )
            )
            
            if user_id:
                direct_query = direct_query.filter(UserAwardProgress.user_id == user_id)
            
            date_from_parsed = parse_date_filter(date_from)
            if date_from_parsed:
                direct_query = direct_query.filter(UserAwardProgress.achieved_at >= date_from_parsed)
            
            date_to_parsed = parse_date_filter(date_to)
            if date_to_parsed:
                direct_query = direct_query.filter(UserAwardProgress.achieved_at <= date_to_parsed)
            
            direct_awards = direct_query.order_by(desc(UserAwardProgress.achieved_at)).all()
            
            for award in direct_awards:
                tier = self.db.query(DirectAwardTier).filter(DirectAwardTier.id == award.award_tier_id).first()
                
                # DC PROTOCOL: Only show awards that users see as "Achieved" on their dashboard
                if not self._is_award_dynamically_achieved(award, tier, award.user_id, 'direct'):
                    continue  # Skip awards that are not achieved dynamically
                
                user = self.db.query(User).filter(User.id == award.user_id).first()
                
                achieved_date = award.achieved_at.isoformat() if award.achieved_at else None
                results.append({
                    'id': award.id,
                    'award_type': 'Direct Referral Award',
                    'user_id': award.user_id,
                    'user_name': user.name if user else 'Unknown',
                    'tier_name': tier.award_name if tier else 'Unknown',
                    'award_name': tier.award_name if tier else 'Unknown',  # Frontend compatibility
                    'award_description': tier.award_description if tier else 'Unknown',  # Gift/Prize description
                    'award_amount': float(award.award_amount) if award.award_amount else 0,
                    'achieved_at': achieved_date,
                    'achieved_date': achieved_date,  # Frontend compatibility
                    'status': award.processed_status,  # DC PROTOCOL: Show same status as Awards Queue
                    'admin_notes': award.admin_notes,
                    'rejection_reason': award.rejection_reason
                })
        
        # Query matching awards if requested
        if not award_type or award_type == 'matching':
            # DC PROTOCOL: Fetch all pending awards, then filter using SAME dynamic logic as user dashboard
            matching_query = self.db.query(UserMatchingAwardProgress).join(
                MatchingAwardTier, UserMatchingAwardProgress.matching_award_tier_id == MatchingAwardTier.id
            )
            
            # DC PROTOCOL: Filter out legacy pre-Oct 21 awards (permanently hidden from all roles)
            matching_query = self.apply_legacy_filter(matching_query, UserMatchingAwardProgress)
            
            matching_query = matching_query.filter(
                or_(
                    UserMatchingAwardProgress.processed_status == 'Pending',
                    UserMatchingAwardProgress.processed_status == 'pending',
                    UserMatchingAwardProgress.processed_status == 'returned_for_correction'
                )
            )
            
            if user_id:
                matching_query = matching_query.filter(UserMatchingAwardProgress.user_id == user_id)
            
            date_from_parsed = parse_date_filter(date_from)
            if date_from_parsed:
                matching_query = matching_query.filter(UserMatchingAwardProgress.achievement_date >= date_from_parsed)
            
            date_to_parsed = parse_date_filter(date_to)
            if date_to_parsed:
                matching_query = matching_query.filter(UserMatchingAwardProgress.achievement_date <= date_to_parsed)
            
            matching_awards = matching_query.order_by(desc(UserMatchingAwardProgress.achievement_date)).all()
            
            for award in matching_awards:
                tier = self.db.query(MatchingAwardTier).filter(MatchingAwardTier.id == award.matching_award_tier_id).first()
                
                # DC PROTOCOL: Only show awards that users see as "Achieved" on their dashboard
                if not self._is_award_dynamically_achieved(award, tier, award.user_id, 'matching'):
                    continue  # Skip awards that are not achieved dynamically
                
                user = self.db.query(User).filter(User.id == award.user_id).first()
                
                # Get amount from tier
                amount = tier.actual_price if tier and tier.actual_price else 0
                
                achieved_date = award.achievement_date.isoformat() if award.achievement_date else None
                results.append({
                    'id': award.id,
                    'award_type': 'Matching Referral Award',
                    'user_id': award.user_id,
                    'user_name': user.name if user else 'Unknown',
                    'tier_name': tier.award_name if tier else 'Unknown',
                    'award_name': tier.award_name if tier else 'Unknown',  # Frontend compatibility
                    'award_description': tier.award_description if tier else 'Unknown',  # Gift/Prize description
                    'award_amount': float(amount),
                    'achieved_at': achieved_date,
                    'achieved_date': achieved_date,  # Frontend compatibility
                    'status': award.processed_status,  # DC PROTOCOL: Show same status as Awards Queue
                    'admin_notes': award.admin_notes,
                    'rejection_reason': award.rejection_reason
                })
        
        # Query bonanza if requested (DC PROTOCOL: Use NEW system only - DynamicBonanzaHistory)
        if not award_type or award_type == 'bonanza':
            bonanza_query = self.db.query(DynamicBonanzaHistory)
            
            # DC PROTOCOL: Filter out legacy pre-Oct 21 awards (permanently hidden from all roles)
            bonanza_query = self.apply_legacy_filter(bonanza_query, DynamicBonanzaHistory)
            
            bonanza_query = bonanza_query.filter(
                DynamicBonanzaHistory.processed_status == 'Pending'
            )
            
            if user_id:
                bonanza_query = bonanza_query.filter(DynamicBonanzaHistory.user_id == user_id)
            
            date_from_parsed = parse_date_filter(date_from)
            if date_from_parsed:
                bonanza_query = bonanza_query.filter(DynamicBonanzaHistory.claimed_at >= date_from_parsed)
            
            date_to_parsed = parse_date_filter(date_to)
            if date_to_parsed:
                bonanza_query = bonanza_query.filter(DynamicBonanzaHistory.claimed_at <= date_to_parsed)
            
            bonanza_awards = bonanza_query.order_by(desc(DynamicBonanzaHistory.claimed_at)).offset(skip).limit(limit).all()
            
            for award in bonanza_awards:
                user = self.db.query(User).filter(User.id == award.user_id).first()
                bonanza = self.db.query(Bonanza).filter(Bonanza.id == award.bonanza_id).first()
                
                # DC PROTOCOL: award_name contains the gift name in DynamicBonanzaHistory
                bonanza_name = bonanza.name if bonanza else 'Unknown'
                reward_name = award.award_name if award.award_name else 'Unknown'
                achieved_date = award.claimed_at.isoformat() if award.claimed_at else None
                results.append({
                    'id': award.id,
                    'award_type': 'Bonanza',
                    'user_id': award.user_id,
                    'user_name': user.name if user else 'Unknown',
                    'tier_name': f"{bonanza_name} - {reward_name}",  # Combined for tier column
                    'award_name': bonanza_name,  # DC Protocol: Bonanza campaign name
                    'reward_text': reward_name,  # DC Protocol: Gift name (award_name field in table)
                    'award_amount': float(award.reward_value_claimed) if award.reward_value_claimed else 0,
                    'achieved_at': achieved_date,
                    'achieved_date': achieved_date,  # Frontend compatibility
                    'status': award.processed_status,
                    'admin_notes': award.admin_notes if hasattr(award, 'admin_notes') else None,
                    'rejection_reason': award.rejection_reason if hasattr(award, 'rejection_reason') else None
                })
        
        return {
            'awards': results,
            'total': len(results),
            'skip': skip,
            'limit': limit
        }
    
    def admin_review_award(
        self,
        award_id: int,
        award_type: str,
        decision: str,
        staff_actor_id: str,
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Staff reviews and approves or returns an award
        DC Protocol: Staff-only operation. Uses UnifiedAwardStatusManager.
        """
        from app.services.unified_award_status_manager import UnifiedAwardStatusManager
        manager = UnifiedAwardStatusManager(self.db)
        
        if decision == 'approve':
            result = manager.admin_approve(
                award_id=award_id,
                award_type=award_type,
                admin_id=staff_actor_id,
                notes=notes
            )
            message = f"Award approved and forwarded for next review"
            
        elif decision == 'return':
            result = manager.update_status(
                award_id=award_id,
                award_type=award_type,
                new_status=AwardStatus.RETURNED_FOR_CORRECTION,
                actor_id=staff_actor_id,
                actor_role='staff',
                reason=notes or 'Returned for correction'
            )
            
            # Also set rejection_reason field
            model_class, award = manager.get_award_model_and_instance(award_id, award_type)
            award.rejection_reason = notes or 'Returned by admin for correction'
            self.db.commit()
            
            message = f"Award returned for correction"
        else:
            return {'error': 'Invalid decision. Must be "approve" or "return"'}
        
        return {
            'success': True,
            'award_id': award_id,
            'award_type': award_type,
            'decision': decision,
            'new_status': result['new_status'],
            'message': message
        }
    
    def admin_bulk_approve(
        self,
        award_ids: List[int],
        award_type: str,
        staff_actor_id: str,
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Bulk approve multiple awards - Staff-only operation
        """
        batch_id = f"BATCH_{datetime.now().strftime('%Y%m%d_%H%M%S')}_STAFF"
        
        successful = []
        failed = []
        
        for award_id in award_ids:
            try:
                result = self.admin_review_award(
                    award_id=award_id,
                    award_type=award_type,
                    decision='approve',
                    staff_actor_id=staff_actor_id,
                    notes=notes
                )
                
                if result.get('success'):
                    # Update batch_id
                    if award_type == 'direct':
                        award = self.db.query(UserAwardProgress).filter(UserAwardProgress.id == award_id).first()
                    elif award_type == 'matching':
                        award = self.db.query(UserMatchingAwardProgress).filter(UserMatchingAwardProgress.id == award_id).first()
                    else:
                        award = self.db.query(DynamicBonanzaHistory).filter(DynamicBonanzaHistory.id == award_id).first()
                    
                    if award:
                        award.bulk_batch_id = batch_id
                        self.db.commit()
                    
                    successful.append(award_id)
                else:
                    failed.append({'id': award_id, 'reason': result.get('error', 'Unknown error')})
            except Exception as e:
                failed.append({'id': award_id, 'reason': str(e)})
        
        return {
            'success': True,
            'batch_id': batch_id,
            'total_processed': len(award_ids),
            'successful': len(successful),
            'failed': len(failed),
            'successful_ids': successful,
            'failed_items': failed
        }
    
    # ========== SUPER ADMIN ROLE FUNCTIONS ==========
    
    def get_pending_awards_for_super_admin(
        self,
        award_type: Optional[str] = None,
        status_filter: Optional[List[str]] = None,
        skip: int = 0,
        limit: int = 100
    ) -> Dict[str, Any]:
        """
        Get all awards for RVZ Supreme Authority with dynamic MULTI-STATUS filtering
        
        RVZ has supreme authority and can view/approve awards at ANY stage.
        
        DYNAMIC MULTI-STATUS FILTERING (DC Protocol):
        - If status_filter is None/empty list: Returns ALL awards in ANY status (future-proof)
        - If status_filter contains values: Returns awards matching ANY of those statuses (OR logic)
        
        This design eliminates hardcoded status lists and automatically includes
        future statuses without requiring code changes.
        """
        from typing import List
        
        direct_results = []
        matching_results = []
        
        # Query direct awards - RVZ sees ALL awards across all statuses (DYNAMIC)
        if not award_type or award_type == 'direct':
            # DC PROTOCOL: Dynamic status filtering - no hardcoded status lists
            direct_query = self.db.query(UserAwardProgress).join(
                DirectAwardTier, UserAwardProgress.award_tier_id == DirectAwardTier.id
            )
            
            # DC PROTOCOL: Filter out legacy pre-Oct 21 awards (permanently hidden from all roles)
            direct_query = self.apply_legacy_filter(direct_query, UserAwardProgress)
            
            # DYNAMIC FILTER: Apply multi-status filter (OR logic)
            if status_filter and len(status_filter) > 0:
                direct_query = direct_query.filter(UserAwardProgress.processed_status.in_(status_filter))
            else:
                # No filter = show ALL statuses (excludes only NULL/None)
                direct_query = direct_query.filter(UserAwardProgress.processed_status.isnot(None))
            
            direct_awards = direct_query.order_by(desc(UserAwardProgress.achieved_at)).offset(skip).limit(limit).all()
            
            for award in direct_awards:
                tier = self.db.query(DirectAwardTier).filter(DirectAwardTier.id == award.award_tier_id).first()
                
                # DC PROTOCOL: Only show awards that users see as "Achieved" on their dashboard
                if not self._is_award_dynamically_achieved(award, tier, award.user_id, 'direct'):
                    continue  # Skip awards that are not achieved dynamically
                
                user = self.db.query(User).filter(User.id == award.user_id).first()
                admin = self.db.query(User).filter(User.id == award.admin_approved_by).first() if award.admin_approved_by else None
                
                direct_results.append({
                    'id': award.id,
                    'award_type': 'direct',
                    'user_id': award.user_id,
                    'user_name': user.name if user else 'Unknown',
                    'award_name': tier.award_name if tier else 'Unknown',
                    'award_description': tier.award_description if tier else 'N/A',
                    'award_amount': float(award.award_amount) if award.award_amount else 0,
                    'achieved_at': award.achieved_at.isoformat() if award.achieved_at else None,
                    'processed_status': award.processed_status,
                    'admin_approved_by': award.admin_approved_by,
                    'admin_name': admin.name if admin else None,
                    'admin_approved_at': award.admin_approved_at.isoformat() if award.admin_approved_at else None,
                    'admin_notes': award.admin_notes,
                    # DC PROTOCOL: Read budgeted amount dynamically from config (single source of truth)
                    'budgeted_amount': float(tier.actual_price) if tier and tier.actual_price else 0,
                    'actual_cost_paid': float(award.actual_cost_paid) if award.actual_cost_paid else None,
                    'cost_variance': float(award.cost_variance) if award.cost_variance else None,
                    # DC PROTOCOL: Include procurement tracking fields from single source of truth
                    'dispatch_date': award.dispatch_date.isoformat() if award.dispatch_date else None,
                    'received_date': award.received_date.isoformat() if award.received_date else None,
                    'delivery_notes': award.delivery_notes
                })
        
        # Query matching awards - RVZ sees ALL awards across all statuses (DYNAMIC)
        if not award_type or award_type == 'matching':
            # DC PROTOCOL: Dynamic status filtering - no hardcoded status lists
            matching_query = self.db.query(UserMatchingAwardProgress).join(
                MatchingAwardTier, UserMatchingAwardProgress.matching_award_tier_id == MatchingAwardTier.id
            )
            
            # DC PROTOCOL: Filter out legacy pre-Oct 21 awards (permanently hidden from all roles)
            matching_query = self.apply_legacy_filter(matching_query, UserMatchingAwardProgress)
            
            # DYNAMIC FILTER: Apply multi-status filter (OR logic)
            if status_filter and len(status_filter) > 0:
                matching_query = matching_query.filter(UserMatchingAwardProgress.processed_status.in_(status_filter))
            else:
                # No filter = show ALL statuses (excludes only NULL/None)
                matching_query = matching_query.filter(UserMatchingAwardProgress.processed_status.isnot(None))
            
            matching_awards = matching_query.order_by(desc(UserMatchingAwardProgress.achievement_date)).offset(skip).limit(limit).all()
            
            for award in matching_awards:
                tier = self.db.query(MatchingAwardTier).filter(MatchingAwardTier.id == award.matching_award_tier_id).first()
                
                # DC PROTOCOL: Only show awards that users see as "Achieved" on their dashboard
                if not self._is_award_dynamically_achieved(award, tier, award.user_id, 'matching'):
                    continue  # Skip awards that are not achieved dynamically
                
                user = self.db.query(User).filter(User.id == award.user_id).first()
                admin = self.db.query(User).filter(User.id == award.admin_approved_by).first() if award.admin_approved_by else None
                
                amount = tier.actual_price if tier and tier.actual_price else 0
                
                matching_results.append({
                    'id': award.id,
                    'award_type': 'matching',
                    'user_id': award.user_id,
                    'user_name': user.name if user else 'Unknown',
                    'award_name': tier.award_name if tier else 'Unknown',
                    'award_description': tier.award_description if tier else 'N/A',
                    'award_amount': float(amount),
                    'achieved_at': award.achievement_date.isoformat() if award.achievement_date else None,
                    'processed_status': award.processed_status,
                    'admin_approved_by': award.admin_approved_by,
                    'admin_name': admin.name if admin else None,
                    'admin_approved_at': award.admin_approved_at.isoformat() if award.admin_approved_at else None,
                    'admin_notes': award.admin_notes,
                    # DC PROTOCOL: Read budgeted amount dynamically from config (single source of truth)
                    'budgeted_amount': float(tier.actual_price) if tier and tier.actual_price else 0,
                    'actual_cost_paid': float(award.actual_cost_paid) if award.actual_cost_paid else None,
                    'cost_variance': float(award.cost_variance) if award.cost_variance else None,
                    # DC PROTOCOL: Include procurement tracking fields from single source of truth
                    'dispatch_date': award.dispatch_date.isoformat() if award.dispatch_date else None,
                    'received_date': award.received_date.isoformat() if award.received_date else None,
                    'delivery_notes': award.delivery_notes
                })
        
        # Query bonanza awards - RVZ sees ALL awards across all statuses (DYNAMIC)
        # DC Protocol Migration: Use ONLY NEW system - DynamicBonanzaHistory
        bonanza_results = []
        if not award_type or award_type == 'bonanza':
            from app.models.bonanza import DynamicBonanzaHistory
            
            # DC PROTOCOL: Dynamic status filtering - no hardcoded status lists
            bonanza_query = self.db.query(DynamicBonanzaHistory)
            
            # DC PROTOCOL: Filter out legacy pre-Oct 21 awards (permanently hidden from all roles)
            bonanza_query = self.apply_legacy_filter(bonanza_query, DynamicBonanzaHistory)
            
            # DYNAMIC FILTER: Apply multi-status filter (OR logic)
            if status_filter and len(status_filter) > 0:
                bonanza_query = bonanza_query.filter(DynamicBonanzaHistory.processed_status.in_(status_filter))
            else:
                # No filter = show ALL statuses (excludes only NULL/None)
                bonanza_query = bonanza_query.filter(DynamicBonanzaHistory.processed_status.isnot(None))
            
            mnr2_bonanza_awards = bonanza_query.order_by(desc(DynamicBonanzaHistory.claimed_at)).offset(skip).limit(limit).all()
            
            for mnr2_award in mnr2_bonanza_awards:
                user = self.db.query(User).filter(User.id == mnr2_award.user_id).first()
                bonanza = self.db.query(Bonanza).filter(Bonanza.id == mnr2_award.bonanza_id).first()
                admin = self.db.query(User).filter(User.id == mnr2_award.admin_approved_by).first() if mnr2_award.admin_approved_by else None
                
                # Get reward info (supports both monetary and non-monetary)
                reward_amount = float(mnr2_award.reward_value_claimed) if mnr2_award.reward_value_claimed else 0
                reward_name = mnr2_award.award_name if mnr2_award.reward_type == 'award' else f"₹{int(reward_amount):,} Cash"
                
                # DC PROTOCOL: Dynamic budget until paid - locked after payment
                # Read LIVE budget from bonanza config (single source of truth) until payment is processed
                is_paid = mnr2_award.processed_status in ['Processed for Dispatch', 'Delivered']
                live_budget = float(bonanza.actual_price) if bonanza and bonanza.actual_price else 0
                
                logger.warning(f"💰 DEBUG: Bonanza ID={mnr2_award.id}, bonanza_id={mnr2_award.bonanza_id}, bonanza.actual_price={bonanza.actual_price if bonanza else 'N/A'}, live_budget={live_budget}")
                
                bonanza_results.append({
                    'id': mnr2_award.id,
                    'award_type': 'bonanza',
                    'user_id': mnr2_award.user_id,
                    'user_name': user.name if user else 'Unknown',
                    'award_name': bonanza.name if bonanza else 'Unknown',
                    'award_description': reward_name,
                    'award_amount': reward_amount,
                    'reward_text': reward_name,
                    'achieved_at': mnr2_award.claimed_at.isoformat() if mnr2_award.claimed_at else None,
                    'processed_status': mnr2_award.processed_status,
                    'admin_approved_by': mnr2_award.admin_approved_by,
                    'admin_name': admin.name if admin else None,
                    'admin_approved_at': mnr2_award.admin_approved_at.isoformat() if mnr2_award.admin_approved_at else None,
                    'rvz_approval_status': mnr2_award.rvz_approval_status,
                    # DC PROTOCOL: Dynamic budget from config until paid, locked after payment
                    'budgeted_amount': live_budget,  # Always read from bonanza.actual_price config
                    'actual_cost_paid': float(mnr2_award.actual_cost_paid) if mnr2_award.actual_cost_paid else None,
                    'cost_variance': (live_budget - float(mnr2_award.actual_cost_paid)) if mnr2_award.actual_cost_paid else None,
                    'cost_variance_reason': mnr2_award.cost_variance_reason,
                    # DC PROTOCOL: Include procurement tracking fields from single source of truth
                    'dispatch_date': mnr2_award.dispatch_date.isoformat() if mnr2_award.dispatch_date else None,
                    'received_date': mnr2_award.received_date.isoformat() if mnr2_award.received_date else None,
                    'delivery_notes': mnr2_award.delivery_notes
                })
        
        # Return data structure compatible with frontend
        return {
            'data': {
                'direct_awards': direct_results,
                'matching_awards': matching_results,
                'bonanza_awards': bonanza_results
            },
            'total_direct': len(direct_results),
            'total_matching': len(matching_results),
            'total_bonanza': len(bonanza_results),
            'total': len(direct_results) + len(matching_results) + len(bonanza_results),
            'skip': skip,
            'limit': limit
        }
    
    def super_admin_decision(
        self,
        award_id: int,
        award_type: str,
        decision: str,
        staff_actor_id: str,
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Staff supreme authority makes final decision on award
        DC Protocol: Staff-only. Can approve awards at ANY stage.
        """
        # Get the award
        if award_type == 'direct':
            award = self.db.query(UserAwardProgress).filter(UserAwardProgress.id == award_id).first()
            entity_type = 'direct_award'
        elif award_type == 'matching':
            award = self.db.query(UserMatchingAwardProgress).filter(UserMatchingAwardProgress.id == award_id).first()
            entity_type = 'matching_award'
        elif award_type == 'bonanza':
            award = self.db.query(DynamicBonanzaHistory).filter(DynamicBonanzaHistory.id == award_id).first()
            entity_type = 'bonanza'
        else:
            return {'error': 'Invalid award type'}
        
        if not award:
            return {'error': 'Award not found'}
        
        old_status = award.processed_status
        
        # DC Protocol: Use UnifiedAwardStatusManager
        from app.services.unified_award_status_manager import UnifiedAwardStatusManager
        manager = UnifiedAwardStatusManager(self.db)
        
        model_class, award = manager.get_award_model_and_instance(award_id, award_type)
        
        if award.processed_status == AwardStatus.PENDING_APPROVAL and decision == 'approve':
            manager.admin_approve(
                award_id=award_id,
                award_type=award_type,
                admin_id=staff_actor_id,
                notes=notes or 'Auto-approved by Staff Supreme Authority',
                auto_commit=False
            )
        
        if decision == 'approve':
            result = manager.rvz_approve(
                award_id=award_id,
                award_type=award_type,
                rvz_id=staff_actor_id,
                notes=notes,
                auto_commit=False
            )
            
            self.db.refresh(award)
            
            award.super_admin_decision_by = staff_actor_id
            award.super_admin_decision_at = get_indian_time()
            award.super_admin_decision = 'approved'
            if notes:
                award.super_admin_notes = notes
            
            # Set budgeted amount for cost variance tracking
            if award_type == 'direct':
                award.budgeted_amount = award.award_amount
            elif award_type == 'matching':
                tier = self.db.query(MatchingAwardTier).filter(MatchingAwardTier.id == award.matching_award_tier_id).first()
                award.budgeted_amount = tier.actual_price if tier else 0
            elif award_type == 'bonanza':
                award.budgeted_amount = award.reward_value_claimed or 0
            
            message = f"Award approved by RVZ Supreme. Ready for finance processing."
            
        elif decision == 'reject':
            result = manager.reject_award(
                award_id=award_id,
                award_type=award_type,
                actor_id=staff_actor_id,
                actor_role='staff',
                reason=notes or 'Rejected by Staff',
                auto_commit=False
            )
            
            self.db.refresh(award)
            
            award.super_admin_decision_by = staff_actor_id
            award.super_admin_decision_at = get_indian_time()
            award.super_admin_decision = 'rejected'
            award.rejection_reason = notes or 'Rejected by Staff'
            
            message = f"Award rejected"
        else:
            return {'error': 'Invalid decision. Must be "approve" or "reject"'}
        
        self.db.commit()
        
        return {
            'success': True,
            'award_id': award.id,
            'award_type': award_type,
            'decision': decision,
            'new_status': award.processed_status,
            'message': message
        }
    
    def super_admin_bulk_approve(
        self,
        award_ids: List[int],
        award_type: str,
        staff_actor_id: str,
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Bulk approve multiple awards - Staff-only operation
        """
        batch_id = f"BATCH_{datetime.now().strftime('%Y%m%d_%H%M%S')}_STAFF"
        
        successful = []
        failed = []
        
        for award_id in award_ids:
            try:
                result = self.super_admin_decision(
                    award_id=award_id,
                    award_type=award_type,
                    decision='approve',
                    staff_actor_id=staff_actor_id,
                    notes=notes
                )
                
                if result.get('success'):
                    # Update batch_id
                    if award_type == 'direct':
                        award = self.db.query(UserAwardProgress).filter(UserAwardProgress.id == award_id).first()
                    elif award_type == 'matching':
                        award = self.db.query(UserMatchingAwardProgress).filter(UserMatchingAwardProgress.id == award_id).first()
                    else:
                        award = self.db.query(DynamicBonanzaHistory).filter(DynamicBonanzaHistory.id == award_id).first()
                    
                    if award:
                        award.bulk_batch_id = batch_id
                        self.db.commit()
                    
                    successful.append(award_id)
                else:
                    failed.append({'id': award_id, 'reason': result.get('error', 'Unknown error')})
            except Exception as e:
                failed.append({'id': award_id, 'reason': str(e)})
        
        return {
            'success': True,
            'batch_id': batch_id,
            'total_processed': len(award_ids),
            'successful': len(successful),
            'failed': len(failed),
            'successful_ids': successful,
            'failed_items': failed
        }
    
    # ========== FINANCE ROLE FUNCTIONS ==========
    
    def get_pending_awards_for_finance(
        self,
        award_type: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> Dict[str, Any]:
        """
        DC PROTOCOL: Get ALL awards in procurement queue (Procurement Pending, Processed for Dispatch, Delivered)
        Awards remain visible until user filters them out - allows updating payment/tracking details anytime
        """
        results = []
        
        # Query direct awards
        if not award_type or award_type == 'direct':
            # DC PROTOCOL: Fetch ALL awards in procurement queue (all post-RVZ-approval statuses)
            direct_query = self.db.query(UserAwardProgress).join(
                DirectAwardTier, UserAwardProgress.award_tier_id == DirectAwardTier.id
            )
            
            # DC PROTOCOL: Filter out legacy pre-Oct 21 awards (permanently hidden from all roles)
            direct_query = self.apply_legacy_filter(direct_query, UserAwardProgress)
            
            direct_awards = direct_query.filter(
                UserAwardProgress.processed_status.in_(['Procurement Pending', 'Processed for Dispatch', 'Delivered'])
            ).order_by(desc(UserAwardProgress.super_admin_decision_at)).offset(skip).limit(limit).all()
            
            for award in direct_awards:
                tier = self.db.query(DirectAwardTier).filter(DirectAwardTier.id == award.award_tier_id).first()
                
                # DC PROTOCOL: Only show awards that users see as "Achieved" on their dashboard
                if not self._is_award_dynamically_achieved(award, tier, award.user_id, 'direct'):
                    continue  # Skip awards that are not achieved dynamically
                
                user = self.db.query(User).filter(User.id == award.user_id).first()
                
                # WV Protocol: Validate tier attribute exists before accessing
                # DirectAwardTier doesn't have is_monetary - determine from actual_price
                is_monetary = False  # Default to physical award
                if tier and hasattr(tier, 'is_monetary'):
                    is_monetary = tier.is_monetary
                elif tier and tier.actual_price == 0:
                    is_monetary = True  # Cash award (no physical cost)
                
                results.append({
                    'id': award.id,
                    'award_type': 'Direct Referral Award',
                    'user_id': award.user_id,
                    'user_name': user.name if user else 'Unknown',
                    'tier_name': tier.award_description if tier and tier.award_description else (tier.award_name if tier else 'Unknown'),  # DC Protocol: Show gift description
                    'budgeted_amount': float(award.budgeted_amount) if award.budgeted_amount else 0,
                    'super_admin_approved_by': award.super_admin_decision_by,
                    'super_admin_approved_at': award.super_admin_decision_at.isoformat() if award.super_admin_decision_at else None,
                    'super_admin_notes': award.super_admin_notes,
                    'user_kyc_status': user.kyc_status if user else 'Not Verified',
                    'processed_status': award.processed_status,  # DC Protocol: Current status
                    'actual_cost_paid': float(award.actual_cost_paid) if award.actual_cost_paid else None,
                    'is_monetary': is_monetary,
                    # DC PROTOCOL: Return ALL delivery tracking fields (same as bonanza)
                    'dispatch_date': award.dispatch_date.isoformat() if award.dispatch_date else None,
                    'received_date': award.received_date.isoformat() if award.received_date else None,
                    'delivered_at': award.delivered_at.isoformat() if award.delivered_at else None,
                    'delivery_notes': award.delivery_notes,
                    'delivered_by': award.delivered_by,
                    'delivery_proof_path': award.delivery_proof_path,
                    'user_acknowledgment': award.user_acknowledgment,
                    # WV Protocol: Return existing payment details for editing
                    'handling_charges': float(getattr(award, 'handling_charges', 0) or 0),
                    'gst_amount': float(getattr(award, 'gst_amount', 0) or 0),
                    'tax_amount': float(getattr(award, 'tax_amount', 0) or 0),
                    'transport_charges': float(getattr(award, 'transport_charges', 0) or 0)
                })
        
        # Query matching awards
        if not award_type or award_type == 'matching':
            # DC PROTOCOL: Fetch ALL awards in procurement queue (all post-RVZ-approval statuses)
            matching_query = self.db.query(UserMatchingAwardProgress).join(
                MatchingAwardTier, UserMatchingAwardProgress.matching_award_tier_id == MatchingAwardTier.id
            )
            
            # DC PROTOCOL: Filter out legacy pre-Oct 21 awards (permanently hidden from all roles)
            matching_query = self.apply_legacy_filter(matching_query, UserMatchingAwardProgress)
            
            matching_awards = matching_query.filter(
                UserMatchingAwardProgress.processed_status.in_(['Procurement Pending', 'Processed for Dispatch', 'Delivered'])
            ).order_by(desc(UserMatchingAwardProgress.super_admin_decision_at)).offset(skip).limit(limit).all()
            
            for award in matching_awards:
                tier = self.db.query(MatchingAwardTier).filter(MatchingAwardTier.id == award.matching_award_tier_id).first()
                
                # DC PROTOCOL: Only show awards that users see as "Achieved" on their dashboard
                if not self._is_award_dynamically_achieved(award, tier, award.user_id, 'matching'):
                    continue  # Skip awards that are not achieved dynamically
                
                user = self.db.query(User).filter(User.id == award.user_id).first()
                
                # WV Protocol: Validate tier attribute exists before accessing
                # MatchingAwardTier doesn't have is_monetary - determine from actual_price
                is_monetary = False  # Default to physical award
                if tier and hasattr(tier, 'is_monetary'):
                    is_monetary = tier.is_monetary
                elif tier and tier.actual_price == 0:
                    is_monetary = True  # Cash award (no physical cost)
                
                results.append({
                    'id': award.id,
                    'award_type': 'Matching Referral Award',
                    'user_id': award.user_id,
                    'user_name': user.name if user else 'Unknown',
                    'tier_name': tier.award_description if tier and tier.award_description else (tier.award_name if tier else 'Unknown'),  # DC Protocol: Show gift description
                    'budgeted_amount': float(award.budgeted_amount) if award.budgeted_amount else 0,
                    'super_admin_approved_by': award.super_admin_decision_by,
                    'super_admin_approved_at': award.super_admin_decision_at.isoformat() if award.super_admin_decision_at else None,
                    'super_admin_notes': award.super_admin_notes,
                    'user_kyc_status': user.kyc_status if user else 'Not Verified',
                    'processed_status': award.processed_status,  # DC Protocol: Current status
                    'actual_cost_paid': float(award.actual_cost_paid) if award.actual_cost_paid else None,
                    'is_monetary': is_monetary,
                    # DC PROTOCOL: Return ALL delivery tracking fields (same as bonanza)
                    'dispatch_date': award.dispatch_date.isoformat() if award.dispatch_date else None,
                    'received_date': award.received_date.isoformat() if award.received_date else None,
                    'delivered_at': award.delivered_at.isoformat() if award.delivered_at else None,
                    'delivery_notes': award.delivery_notes,
                    'delivered_by': award.delivered_by,
                    'delivery_proof_path': award.delivery_proof_path,
                    'user_acknowledgment': award.user_acknowledgment,
                    # WV Protocol: Return existing payment details for editing
                    'handling_charges': float(getattr(award, 'handling_charges', 0) or 0),
                    'gst_amount': float(getattr(award, 'gst_amount', 0) or 0),
                    'tax_amount': float(getattr(award, 'tax_amount', 0) or 0),
                    'transport_charges': float(getattr(award, 'transport_charges', 0) or 0)
                })
        
        # DC Protocol: Legacy BonanzaProgress table deprecated - removed query
        # All bonanza data now in DynamicBonanzaHistory (see MNR query below)
        
        # Query NEW MNR bonanza system (DynamicBonanzaHistory)
        # Approved claims ready for procurement (processed_at IS NOT NULL)
        if not award_type or award_type == 'bonanza':
            from app.models.bonanza import Bonanza
            import logging
            logger = logging.getLogger(__name__)
            
            # DC PROTOCOL: Fetch ALL awards in procurement queue (all post-RVZ-approval statuses)
            # WV Protocol: Include both snake_case and human-readable status values for maximum compatibility
            bonanza_query = self.db.query(DynamicBonanzaHistory)
            
            # DC PROTOCOL: Filter out legacy pre-Oct 21 awards (permanently hidden from all roles)
            bonanza_query = self.apply_legacy_filter(bonanza_query, DynamicBonanzaHistory)
            
            mnr2_bonanzas = bonanza_query.filter(
                DynamicBonanzaHistory.processed_status.in_([
                    'Procurement Pending', 'Processed for Dispatch', 'Delivered',
                    'procurement_pending', 'processed_for_dispatch', 'delivered',  # Legacy snake_case variants
                    'Pending RVZ Approval', 'RVZ Approved', 'Finance Processed'  # Alternative status names
                ])
            ).order_by(desc(DynamicBonanzaHistory.claimed_at)).offset(skip).limit(limit).all()
            
            logger.warning(f"🔍 DEBUG: Bonanza procurement query returned {len(mnr2_bonanzas)} records (skip={skip}, limit={limit}, award_type={award_type})")
            
            for claim in mnr2_bonanzas:
                logger.warning(f"🔍 DEBUG: Processing bonanza claim ID={claim.id}, user_id={claim.user_id}, bonanza_id={claim.bonanza_id}, processed_status='{claim.processed_status}'")
                
                user = self.db.query(User).filter(User.id == claim.user_id).first()
                if not user:
                    logger.warning(f"⚠️ DEBUG: User NOT FOUND for bonanza claim ID={claim.id}, user_id={claim.user_id} - SKIPPING")
                    continue
                
                bonanza = self.db.query(Bonanza).filter(Bonanza.id == claim.bonanza_id).first()
                if not bonanza:
                    logger.warning(f"⚠️ DEBUG: Bonanza NOT FOUND for claim ID={claim.id}, bonanza_id={claim.bonanza_id} - SKIPPING")
                    continue
                
                # Determine reward display name - SHOW AWARD NAME PROMINENTLY
                if claim.reward_type == 'award':
                    tier_name = claim.award_name or 'Physical Award'
                elif claim.reward_type == 'cash':
                    tier_name = f"₹{int(claim.reward_value_claimed):,} Cash"
                else:
                    tier_name = 'Unknown Reward'
                
                award_data = {
                    'id': claim.id,
                    'award_type': 'MNR Bonanza',
                    'user_id': claim.user_id,
                    'user_name': user.name if user else 'Unknown',
                    'tier_name': tier_name,  # Award name (Fridge, Scooter, etc.)
                    'bonanza_name': bonanza.name if bonanza else 'Unknown',  # Campaign name
                    # DC PROTOCOL: Read budgeted_amount from DynamicBonanzaHistory (single source of truth)
                    'budgeted_amount': float(claim.budgeted_amount) if claim.budgeted_amount else 0,
                    'super_admin_approved_by': 'System',  # MNR auto-approved
                    'super_admin_approved_at': claim.processed_at.isoformat() if claim.processed_at else None,
                    'super_admin_notes': f"Claimed: {claim.claimed_at.isoformat() if claim.claimed_at else 'N/A'}",
                    'user_kyc_status': user.kyc_status if user else 'Not Verified',
                    'reward_type': claim.reward_type,  # 'award' or 'cash'
                    'is_monetary': claim.is_monetary,  # True/False
                    # DC PROTOCOL: Return ALL delivery tracking fields for editing (single source of truth)
                    'dispatch_date': claim.dispatch_date.isoformat() if claim.dispatch_date else None,
                    'received_date': claim.received_date.isoformat() if claim.received_date else None,
                    'delivered_at': claim.delivered_at.isoformat() if claim.delivered_at else None,
                    'delivery_notes': claim.delivery_notes,
                    'processed_status': claim.processed_status,  # DC PROTOCOL: Show same status as Awards Queue
                    # DC PROTOCOL: Use standardized actual_cost_paid field only (removed deprecated actual_cost_incurred)
                    'actual_cost_paid': float(claim.actual_cost_paid) if claim.actual_cost_paid else None,
                    # WV Protocol: Return existing payment details for editing
                    'handling_charges': float(getattr(claim, 'handling_charges', 0) or 0),
                    'gst_amount': float(getattr(claim, 'gst_amount', 0) or 0),
                    'tax_amount': float(getattr(claim, 'tax_amount', 0) or 0),
                    'transport_charges': float(getattr(claim, 'transport_charges', 0) or 0)
                }
                results.append(award_data)
                logger.warning(f"✅ DEBUG: Successfully appended bonanza claim ID={claim.id} to results (tier_name='{tier_name}', bonanza_name='{bonanza.name if bonanza else 'Unknown'}')")
        
        # Calculate stats
        from datetime import date, datetime
        from decimal import Decimal
        
        total_amount = sum(award.get('budgeted_amount', 0) or 0 for award in results)
        
        # Count processed today
        today = date.today()
        processed_today_count = 0
        
        # Query all award types for processed count
        direct_processed = self.db.query(UserAwardProgress).filter(
            UserAwardProgress.processed_status == 'completed',
            func.date(UserAwardProgress.finance_processed_at) == today
        ).count()
        
        matching_processed = self.db.query(UserMatchingAwardProgress).filter(
            UserMatchingAwardProgress.processed_status == 'completed',
            func.date(UserMatchingAwardProgress.finance_processed_at) == today
        ).count()
        
        # DC Protocol: Use DynamicBonanzaHistory for bonanza stats
        bonanza_processed = self.db.query(DynamicBonanzaHistory).filter(
            DynamicBonanzaHistory.processed_status == 'Processed for Dispatch',
            func.date(DynamicBonanzaHistory.finance_processed_at) == today
        ).count()
        
        processed_today_count = direct_processed + matching_processed + bonanza_processed
        
        # Calculate company earnings from processed awards today using CompanyEarnings table  
        company_earnings_today = self.db.query(
            func.coalesce(func.sum(CompanyEarnings.net_company_earnings), Decimal('0'))
        ).filter(
            CompanyEarnings.income_type.in_(['Ved Income', 'Matching Referral']),
            func.date(CompanyEarnings.timestamp) == today
        ).scalar() or Decimal('0')
        
        return {
            'awards': results,
            'total': len(results),
            'skip': skip,
            'limit': limit,
            'stats': {
                'pending': len(results),
                'total_amount': int(total_amount),
                'processed_today': processed_today_count,
                'company_earnings': int(company_earnings_today)
            }
        }
    
    def finance_process_payment(
        self,
        award_id: int,
        award_type: str,
        staff_actor_id: str,
        actual_cost: Optional[Decimal] = None,  # If None, uses budgeted amount
        cost_variance_reason: Optional[str] = None,
        notes: Optional[str] = None,
        handling_charges: Optional[Decimal] = None,  # Company handling charges base amount
        gst_amount: Optional[Decimal] = None,  # GST (18%) on handling charges (auto-calculated in frontend)
        tax_amount: Optional[Decimal] = None,  # Tax collected from winner (physical awards)
        transport_charges: Optional[Decimal] = None,  # Transport charges (physical awards)
        vendor_name: Optional[str] = None,  # Vendor/supplier name for expense record
        payment_mode: Optional[str] = None  # Payment method (Bank Transfer, Cash, UPI, etc.)
    ) -> Dict[str, Any]:
        """
        Finance processes payment with handling charges and GST
        DC Protocol: Handling charges and GST (18%) received separately from frontend, added to company revenue
        Creates transaction, credits wallet, records company earnings
        
        DC Protocol: Staff-only operation. staff_actor_id is staff emp_code for audit trail.
        """
        from datetime import date
        from app.models.bonanza import DynamicBonanzaHistory
        
        # Get the award
        is_mnr2_bonanza = False
        
        if award_type == 'direct':
            award = self.db.query(UserAwardProgress).filter(UserAwardProgress.id == award_id).first()
            entity_type = 'direct_award'
        elif award_type == 'matching':
            award = self.db.query(UserMatchingAwardProgress).filter(UserMatchingAwardProgress.id == award_id).first()
            entity_type = 'matching_award'
        elif award_type == 'bonanza':
            award = self.db.query(DynamicBonanzaHistory).filter(DynamicBonanzaHistory.id == award_id).first()
            entity_type = 'bonanza'
            is_mnr2_bonanza = True
        else:
            return {'error': 'Invalid award type'}
        
        if not award:
            return {'error': 'Award not found'}
        
        # DC Protocol: Allow payment updates at any time EXCEPT for Delivered awards
        # User requirement: Payment details should be always editable to update transport/tax/handling charges
        current_status = getattr(award, 'processed_status', None)
        if current_status == 'Delivered':
            return {'error': 'This award has already been delivered. Cannot update payment details.'}
        
        # Validate award is in correct status for finance processing (allow updates for Processed for Dispatch)
        if current_status not in ['Procurement Pending', 'Admin Approved', 'Processed for Dispatch']:
            return {'error': f'Award must be in Procurement Pending, Admin Approved, or Processed for Dispatch status to process/update payment. Current status: {current_status}'}
        
        # Get user
        user = self.db.query(User).filter(User.id == award.user_id).first()
        if not user:
            return {'error': 'User not found'}
        
        # DC Protocol: Determine if this is a PHYSICAL or CASH award
        # CRITICAL FIX: Check tax_amount/transport_charges for direct/matching awards
        is_physical_award = False
        
        if is_mnr2_bonanza:
            # Bonanza awards: Check is_monetary field
            is_physical_award = not award.is_monetary
        elif award_type == 'bonanza':
            # Legacy bonanza: Check MNR history record
            mnr2_claim = self.db.query(DynamicBonanzaHistory).filter(
                DynamicBonanzaHistory.user_id == award.user_id,
                DynamicBonanzaHistory.bonanza_id == award.bonanza_id
            ).first()
            if mnr2_claim and not mnr2_claim.is_monetary:
                is_physical_award = True
        else:
            # DC Protocol: Direct/Matching awards - check if tax/transport charges indicate physical award
            # Physical awards collect tax and transport charges from winners
            # Cash awards have NO tax/transport charges (direct wallet credit only)
            has_tax = tax_amount is not None and Decimal(str(tax_amount)) > 0
            has_transport = transport_charges is not None and Decimal(str(transport_charges)) > 0
            
            # If EITHER tax or transport is collected, it's a physical award
            if has_tax or has_transport:
                is_physical_award = True
                logger.info(f"🎁 Detected PHYSICAL award (tax={tax_amount}, transport={transport_charges}) for {award_type} award {award_id}")
        
        # Determine actual cost (with variance tracking)
        if is_mnr2_bonanza:
            # MNR bonanzas don't have budgeted_amount - use reward_value_claimed or 0
            budgeted_amount = Decimal(str(award.reward_value_claimed)) if award.reward_value_claimed else Decimal('0')
        else:
            budgeted_amount = Decimal(str(award.budgeted_amount)) if award.budgeted_amount else Decimal('0')
        
        if actual_cost is not None:
            actual_cost = Decimal(str(actual_cost))
            # Fix negative variance when budgeted_amount is NULL or 0
            cost_variance = budgeted_amount - actual_cost if budgeted_amount > 0 else Decimal('0')
        else:
            # No adjustment - use budgeted amount
            actual_cost = budgeted_amount if budgeted_amount > 0 else Decimal('0')
            cost_variance = Decimal('0')
        
        # DC Protocol: Use frontend-calculated GST amount (already computed as 18% of handling_charges)
        handling_charge_amount = Decimal(str(handling_charges)) if handling_charges else Decimal('0')
        handling_charge_gst = Decimal(str(gst_amount)) if gst_amount else Decimal('0')
        
        # Initialize physical award charges (if applicable)
        tax_collected = Decimal(str(tax_amount)) if tax_amount else Decimal('0')
        transport_collected = Decimal(str(transport_charges)) if transport_charges else Decimal('0')
        
        # Calculate net amount and company earnings (NO admin/TDS deductions)
        if is_physical_award:
            # PHYSICAL AWARD: No cash to user (they get physical item)
            net_amount = Decimal('0')
            # Company earnings = handling charges + GST + cost savings + tax/transport collected from winner
            total_company_earnings = handling_charge_amount + handling_charge_gst + cost_variance + tax_collected + transport_collected
        else:
            # CASH AWARD: Full amount goes to user (no deductions)
            net_amount = actual_cost
            # Company earnings = handling charges + GST + cost savings only
            total_company_earnings = handling_charge_amount + handling_charge_gst + cost_variance
        
        old_status = award.processed_status if hasattr(award, 'processed_status') else 'approved'
        
        try:
            # 1. Create Transaction record (skip if already exists - UPDATE mode)
            if award.transaction_id:
                # UPDATE mode: Reuse existing transaction
                transaction_id_ref = award.transaction_id
            else:
                # FIRST-TIME processing: Create new transaction
                transaction = Transaction(
                referrer_id=award.user_id,
                referred_user_id=award.user_id,  # Self-transaction for awards
                amount=net_amount,
                transaction_type=f'{award_type.title()} Referral Award' if award_type in ['direct', 'matching'] else 'Bonanza Reward',
                timestamp=get_indian_time(),
                referral_type='award',
                referral_id=award.id
                )
                self.db.add(transaction)
                self.db.flush()  # Get transaction ID
                transaction_id_ref = transaction.id
            
            # DC PROTOCOL CRITICAL FIX: Physical awards are GIFTS, not cash income
            # DO NOT create pending_income for physical awards (no cash to user)
            # Only create pending_income for CASH awards (actual money to user's wallet)
            
            if not is_physical_award:
                # CASH AWARD ONLY: Create pending_income record
                # Materialized views will compute wallet balances from pending_income ledger
                
                # Determine pending_income status based on KYC approval (DC Protocol - respects RVZ skip settings)
                from app.models.system_control import AppSettings
                skip_settings = AppSettings.get_kyc_skip_settings(self.db)
                
                # Check if KYC/Bank requirements are skipped OR user is approved
                kyc_satisfied = skip_settings.get('skip_kyc_requirement') or user.kyc_status == 'Approved'
                bank_satisfied = skip_settings.get('skip_bank_requirement') or getattr(user, 'kyc_bank_verified', False)
                
                if kyc_satisfied and bank_satisfied:
                    # KYC/Bank approved (or skipped by RVZ) → goes directly to withdrawable wallet
                    verification_status = 'Completed'
                    wallet_type = 'withdrawable'
                else:
                    # KYC not approved → goes to earning wallet (pending payment)
                    verification_status = 'Pending'
                    wallet_type = 'earning'
                
                # 2. Create pending_income record (single source of truth)
                # NO admin/TDS deductions - full amount goes to user
                # DC Protocol: Staff processes payments. FK columns (verified_by_id) reference user table,
                # so set to None. Staff identity captured in notes and award audit trail.
                pending_income = PendingIncome(
                    user_id=award.user_id,
                    related_user_id=award.user_id,
                    income_type=f'{award_type.title()} Award',
                    gross_amount=actual_cost,
                    gurudakshina_deduction=Decimal('0'),
                    admin_deduction=Decimal('0'),
                    tds_deduction=Decimal('0'),
                    net_amount=net_amount,
                    withdrawal_wallet_amount=net_amount,
                    upgraded_wallet_amount=Decimal('0'),
                    business_date=get_indian_time(),
                    verification_status=verification_status,
                    admin_verified_by_id=None,
                    admin_verified_at=get_indian_time() if verification_status == 'Completed' else None,
                    super_admin_verified_by_id=None,
                    super_admin_verified_at=get_indian_time() if verification_status == 'Completed' else None,
                    accounts_paid_by_id=None,
                    accounts_paid_at=get_indian_time() if verification_status == 'Completed' else None,
                    notes=f"Award payment - {award_type.title()} Award ID: {award.id} (Staff: {staff_actor_id})",
                    calculation_timestamp=get_indian_time()
                )
                self.db.add(pending_income)
                self.db.flush()  # Get pending_income ID
                logger.info(f"💰 Created cash income entry for {award_type} award {award_id} - User will receive ₹{net_amount}")
            else:
                logger.info(f"🎁 Skipped income entry for PHYSICAL {award_type} award {award_id} - This is a gift, not cash income")
            
            # 3. Record Company Earnings (DC Protocol: UPDATE existing record if payment is being re-processed)
            if is_physical_award:
                earnings_description = f'Physical Award - Handling Charges: ₹{handling_charge_amount}, GST (18%): ₹{handling_charge_gst}, Tax Collected: ₹{tax_collected}, Transport: ₹{transport_collected}, Cost Variance: ₹{cost_variance}'
            else:
                earnings_description = f'Cash Award - Handling Charges: ₹{handling_charge_amount}, GST (18%): ₹{handling_charge_gst}, Cost Variance: ₹{cost_variance}'
            
            # DC Protocol: Check if CompanyEarnings already exists for this award (UPDATE mode)
            # Search by user_id + income_type + original_amount to find the award's earning record
            existing_earning = self.db.query(CompanyEarnings).filter(
                CompanyEarnings.user_id == award.user_id,
                CompanyEarnings.income_type == f'{award_type.title()} Award',
                CompanyEarnings.description.like(f'%Award ID: {award.id}%')
            ).first()
            
            if existing_earning:
                # UPDATE existing record (payment details changed)
                existing_earning.excess_amount = cost_variance
                existing_earning.net_company_earnings = total_company_earnings
                existing_earning.paid_amount = net_amount
                existing_earning.description = earnings_description
                existing_earning.timestamp = get_indian_time()
                company_earning = existing_earning  # Reference for later use
            else:
                # CREATE new record (first-time processing)
                company_earning = CompanyEarnings(
                    user_id=award.user_id,
                    original_amount=budgeted_amount,
                    excess_amount=cost_variance,  # Cost savings
                    admin_deduction=Decimal('0'),  # NO admin deduction (removed)
                    tds_deduction=Decimal('0'),  # NO TDS deduction (removed)
                    net_company_earnings=total_company_earnings,
                    paid_amount=net_amount,
                    ceiling_date=date.today(),
                    income_type=f'{award_type.title()} Award',
                    daily_total_before=Decimal('0'),  # Not ceiling-related
                    description=earnings_description,
                    timestamp=get_indian_time()
                )
                self.db.add(company_earning)
            
            # 4. Create Expense Record using RVZ Expense Service (Supreme Authority Auto-Creation)
            # DC Protocol: Auto-create expense from award procurement with proper linkage
            from app.services.rvz_expense_service import RVZExpenseService
            
            category_name = "Cash" if award_type == 'bonanza' else "Award"
            expense_ref_no = f"AWARD-{award.id}-{award_type.upper()}"
            
            # Determine award reference details based on award type
            award_ref_id = None
            award_ref_type = None
            bonanza_ref_id = None
            bonanza_ref_type = None
            
            if award_type == 'direct':
                award_ref_id = award.id
                award_ref_type = 'Direct Award'
            elif award_type == 'matching':
                award_ref_id = award.id
                award_ref_type = 'Matching Award'
            elif award_type == 'bonanza':
                bonanza_ref_id = award.id
                if is_mnr2_bonanza:
                    bonanza_ref_type = 'Physical Bonanza'
                else:
                    bonanza_ref_type = 'Cash Bonanza'
            
            # Create expense using RVZ Expense Service (auto-approved, source_type='auto_award')
            expense = RVZExpenseService.create_award_procurement_expense(
                db=self.db,
                award_reference_id=award_ref_id,
                award_reference_type=award_ref_type,
                bonanza_reference_id=bonanza_ref_id,
                bonanza_reference_type=bonanza_ref_type,
                actual_cost_paid=actual_cost,
                expense_date=date.today(),
                category=category_name,
                description=f"Auto-created from award procurement: {award_type.title()} Award for {user.name} ({award.user_id}) - Award ID: {award.id}",
                vendor=vendor_name or f"Award Vendor - {award_type.title()}",
                payment_mode=payment_mode or "Bank Transfer",
                reference_no=expense_ref_no,
                rvz_user_id=staff_actor_id
            )
            
            # 5. Update award payment details
            if is_mnr2_bonanza:
                # DC PROTOCOL: Use standardized fields (actual_cost_paid, not actual_cost_incurred)
                award.actual_cost_paid = actual_cost
                award.cost_variance = cost_variance
                award.cost_variance_reason = cost_variance_reason
                # DC Protocol: Save payment breakdown fields
                award.handling_charges = handling_charge_amount
                award.gst_amount = handling_charge_gst
                award.tax_amount = tax_collected
                award.transport_charges = transport_collected
                award.finance_processed_by = staff_actor_id
                award.finance_processed_at = get_indian_time()
                award.transaction_id = transaction_id_ref
                # User requirement: Set award status to 'Ordered' for user visibility
                if hasattr(award, 'award_status'):
                    award.award_status = 'Ordered'
            else:
                # Legacy awards have full status tracking (DC Protocol)
                award.finance_processed_by = staff_actor_id
                award.finance_processed_at = get_indian_time()
                award.actual_cost_paid = actual_cost
                award.cost_variance = cost_variance
                award.cost_variance_reason = cost_variance_reason
                # DC Protocol: Save payment breakdown fields
                award.handling_charges = handling_charge_amount
                award.gst_amount = handling_charge_gst
                award.tax_amount = tax_collected
                award.transport_charges = transport_collected
                award.payment_status = 'released'
                award.transaction_id = transaction_id_ref
                award.processed_date = get_indian_time()
                # User requirement: Set award status to 'Ordered' for user visibility
                award.award_status = 'Ordered'
            
            # 6. ✅ DC Protocol: Update processed_status via UnifiedAwardStatusManager
            # Ensures audit trail and status consistency across all pages
            # Uses auto_commit=False to maintain transaction integrity with payment processing
            from app.services.unified_award_status_manager import UnifiedAwardStatusManager
            status_manager = UnifiedAwardStatusManager(self.db)
            
            target_status = AwardStatus.PROCESSED_FOR_DISPATCH
            
            status_manager.update_status(
                award_id=award.id,
                award_type=award_type,
                new_status=target_status,
                actor_id=staff_actor_id,
                actor_role='finance',
                reason=f'Payment processed: Actual cost ₹{actual_cost}, Handling charges ₹{handling_charge_amount}, GST ₹{handling_charge_gst}',
                skip_transition_validation=False,
                metadata={
                    'actual_cost': str(actual_cost),
                    'budgeted_amount': str(budgeted_amount),
                    'cost_variance': str(cost_variance),
                    'handling_charges': str(handling_charge_amount),
                    'gst_amount': str(handling_charge_gst),
                    'transaction_id': transaction_id_ref
                },
                auto_commit=False  # ✅ Defer commit - let caller commit atomically
            )
            logger.info(f"✅ Status updated to {target_status} via UnifiedAwardStatusManager for {award_type} award {award.id}")
            # ✅ Audit log automatically created by UnifiedAwardStatusManager - no duplicate needed
            
            # 7. If legacy bonanza, create history record (MNR already has history)
            if award_type == 'bonanza' and not is_mnr2_bonanza:
                reward = self.db.query(DynamicBonanzaReward).filter(DynamicBonanzaReward.id == award.reward_id).first()
                
                # DC PROTOCOL: Use standardized fields for new history records
                history = DynamicBonanzaHistory(
                    user_id=award.user_id,
                    bonanza_id=award.bonanza_id,
                    claimed_reward_id=award.reward_id,
                    reward_type=reward.reward_type if reward else 'cash',
                    reward_value_claimed=actual_cost,
                    # DC PROTOCOL: Use actual_cost_paid instead of deprecated actual_cost_incurred
                    actual_cost_paid=actual_cost,
                    budgeted_amount=actual_cost,  # Set budgeted amount
                    cost_variance=cost_variance,
                    cost_variance_reason=cost_variance_reason,
                    # DC PROTOCOL: Populate payment breakdown fields
                    handling_charges=handling_charge_amount,
                    gst_amount=handling_charge_gst,
                    tax_amount=tax_collected,
                    transport_charges=transport_collected,
                    # DC PROTOCOL: Populate vendor/payment fields
                    vendor_name=vendor_name,
                    payment_mode=payment_mode,
                    payment_reference=payment_ref,
                    claimed_at=award.achieved_date,
                    processed_at=get_indian_time(),
                    processed_by=staff_actor_id,
                    finance_processed_by=staff_actor_id,
                    finance_processed_at=get_indian_time(),
                    processed_status=AwardStatus.PROCESSED_FOR_DISPATCH
                )
                self.db.add(history)
            
            self.db.commit()
            
            # DC Protocol: Generate appropriate message based on award type
            if is_physical_award:
                # Physical award: User receives item, NO wallet credit
                success_message = (
                    f'Physical award processed successfully. '
                    f'User will receive physical item via delivery. '
                    f'Handling: ₹{handling_charge_amount} + GST: ₹{handling_charge_gst}'
                )
                wallet_credited_field = None  # No wallet credit for physical awards
            else:
                # Cash award: Money credited to wallet as per WVV protocol
                wallet_description = 'withdrawable wallet (as per WVV - ready for withdrawal)' if wallet_type == 'withdrawable' else 'earning wallet (as per WVV - pending KYC approval)'
                success_message = (
                    f'Cash award processed successfully. '
                    f'₹{net_amount} credited to {wallet_description}. '
                    f'Handling: ₹{handling_charge_amount} + GST: ₹{handling_charge_gst}'
                )
                wallet_credited_field = wallet_type
            
            return {
                'success': True,
                'award_id': award.id,
                'transaction_id': transaction_id_ref,
                'is_physical_award': is_physical_award,
                'budgeted_amount': float(budgeted_amount),
                'actual_cost': float(actual_cost),
                'cost_variance': float(cost_variance),
                'handling_charges': float(handling_charge_amount),
                'handling_charges_gst': float(handling_charge_gst),
                'tax_collected': float(tax_collected),
                'transport_collected': float(transport_collected),
                'net_amount': float(net_amount),
                'total_company_earnings': float(total_company_earnings),
                'wallet_credited': wallet_credited_field,
                'message': success_message
            }
            
        except Exception as e:
            self.db.rollback()
            
            # Mark payment as failed
            award.payment_status = 'failed'
            award.finance_processed_by = staff_actor_id
            award.finance_processed_at = get_indian_time()
            award.admin_notes = f"Payment failed: {str(e)}"
            self.db.commit()
            
            return {
                'error': f'Payment processing failed: {str(e)}',
                'award_id': award.id
            }
    
    # ========== RVZ ROLE FUNCTIONS ==========
    
    def rvz_get_all_awards(
        self,
        status: Optional[str] = None,
        award_type: Optional[str] = None,
        user_id: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> Dict[str, Any]:
        """
        RVZ gets complete oversight of all awards across all statuses
        """
        results = []
        
        # Build base query for each award type
        if not award_type or award_type == 'direct':
            direct_query = self.db.query(UserAwardProgress)
            
            # DC PROTOCOL: Filter out legacy pre-Oct 21 awards (permanently hidden from all roles)
            direct_query = self.apply_legacy_filter(direct_query, UserAwardProgress)
            
            if status:
                direct_query = direct_query.filter(UserAwardProgress.processed_status == status)
            if user_id:
                direct_query = direct_query.filter(UserAwardProgress.user_id == user_id)
            
            date_from_parsed = parse_date_filter(date_from)
            if date_from_parsed:
                direct_query = direct_query.filter(UserAwardProgress.achieved_at >= date_from_parsed)
            
            date_to_parsed = parse_date_filter(date_to)
            if date_to_parsed:
                direct_query = direct_query.filter(UserAwardProgress.achieved_at <= date_to_parsed)
            
            direct_awards = direct_query.order_by(desc(UserAwardProgress.created_at)).offset(skip).limit(limit).all()
            
            for award in direct_awards:
                user = self.db.query(User).filter(User.id == award.user_id).first()
                tier = self.db.query(DirectAwardTier).filter(DirectAwardTier.id == award.award_tier_id).first()
                
                results.append({
                    'id': award.id,
                    'award_type': 'Direct Referral Award',
                    'user_id': award.user_id,
                    'user_name': user.name if user else 'Unknown',
                    'tier_name': tier.award_name if tier else 'Unknown',
                    'budgeted_amount': float(award.budgeted_amount) if award.budgeted_amount else 0,
                    'actual_cost_paid': float(award.actual_cost_paid) if award.actual_cost_paid else None,
                    'cost_variance': float(award.cost_variance) if award.cost_variance else 0,
                    'status': award.processed_status,
                    'achieved_at': award.achieved_at.isoformat() if award.achieved_at else None,
                    'admin_approved_by': award.admin_approved_by,
                    'super_admin_decision_by': award.super_admin_decision_by,
                    'finance_processed_by': award.finance_processed_by,
                    'transaction_id': award.transaction_id,
                    'bulk_batch_id': award.bulk_batch_id
                })
        
        # Query matching awards
        if not award_type or award_type == 'matching':
            matching_query = self.db.query(UserMatchingAwardProgress)
            
            # DC PROTOCOL: Filter out legacy pre-Oct 21 awards (permanently hidden from all roles)
            matching_query = self.apply_legacy_filter(matching_query, UserMatchingAwardProgress)
            
            if status:
                matching_query = matching_query.filter(UserMatchingAwardProgress.processed_status == status)
            if user_id:
                matching_query = matching_query.filter(UserMatchingAwardProgress.user_id == user_id)
            
            date_from_parsed = parse_date_filter(date_from)
            if date_from_parsed:
                matching_query = matching_query.filter(UserMatchingAwardProgress.achievement_date >= date_from_parsed)
            
            date_to_parsed = parse_date_filter(date_to)
            if date_to_parsed:
                matching_query = matching_query.filter(UserMatchingAwardProgress.achievement_date <= date_to_parsed)
            
            matching_awards = matching_query.order_by(desc(UserMatchingAwardProgress.created_at)).offset(skip).limit(limit).all()
            
            for award in matching_awards:
                user = self.db.query(User).filter(User.id == award.user_id).first()
                tier = self.db.query(MatchingAwardTier).filter(MatchingAwardTier.id == award.matching_award_tier_id).first()
                
                results.append({
                    'id': award.id,
                    'award_type': 'Matching Referral Award',
                    'user_id': award.user_id,
                    'user_name': user.name if user else 'Unknown',
                    'tier_name': tier.award_name if tier else 'Unknown',
                    'budgeted_amount': float(award.budgeted_amount) if award.budgeted_amount else 0,
                    'actual_cost_paid': float(award.actual_cost_paid) if award.actual_cost_paid else None,
                    'cost_variance': float(award.cost_variance) if award.cost_variance else 0,
                    'status': award.processed_status,
                    'achieved_at': award.achievement_date.isoformat() if award.achievement_date else None,
                    'admin_approved_by': award.admin_approved_by,
                    'super_admin_decision_by': award.super_admin_decision_by,
                    'finance_processed_by': award.finance_processed_by,
                    'transaction_id': award.transaction_id,
                    'bulk_batch_id': award.bulk_batch_id
                })
        
        # DC Protocol: Query bonanza awards from DynamicBonanzaHistory
        if not award_type or award_type == 'bonanza':
            bonanza_query = self.db.query(DynamicBonanzaHistory)
            
            # DC PROTOCOL: Filter out legacy pre-Oct 21 awards (permanently hidden from all roles)
            bonanza_query = self.apply_legacy_filter(bonanza_query, DynamicBonanzaHistory)
            
            if status:
                bonanza_query = bonanza_query.filter(DynamicBonanzaHistory.processed_status == status)
            if user_id:
                bonanza_query = bonanza_query.filter(DynamicBonanzaHistory.user_id == user_id)
            
            date_from_parsed = parse_date_filter(date_from)
            if date_from_parsed:
                bonanza_query = bonanza_query.filter(DynamicBonanzaHistory.claimed_at >= date_from_parsed)
            
            date_to_parsed = parse_date_filter(date_to)
            if date_to_parsed:
                bonanza_query = bonanza_query.filter(DynamicBonanzaHistory.claimed_at <= date_to_parsed)
            
            bonanza_claims = bonanza_query.order_by(desc(DynamicBonanzaHistory.created_at)).offset(skip).limit(limit).all()
            
            for claim in bonanza_claims:
                user = self.db.query(User).filter(User.id == claim.user_id).first()
                bonanza = self.db.query(Bonanza).filter(Bonanza.id == claim.bonanza_id).first()
                
                results.append({
                    'id': claim.id,
                    'award_type': 'Bonanza Award',
                    'user_id': claim.user_id,
                    'user_name': user.name if user else 'Unknown',
                    'tier_name': claim.award_name or (bonanza.name if bonanza else 'Unknown'),
                    'budgeted_amount': float(claim.budgeted_amount) if claim.budgeted_amount else (float(claim.reward_value_claimed) if claim.reward_value_claimed else 0),
                    'actual_cost_paid': float(claim.actual_cost_paid) if claim.actual_cost_paid else None,
                    'cost_variance': float(claim.cost_variance) if claim.cost_variance else 0,
                    'status': claim.processed_status,
                    'achieved_at': claim.claimed_at.isoformat() if claim.claimed_at else None,
                    'admin_approved_by': claim.admin_approved_by,
                    'super_admin_decision_by': claim.super_admin_decision_by,
                    'finance_processed_by': claim.finance_processed_by,
                    'transaction_id': claim.transaction_id,
                    'bulk_batch_id': claim.bulk_batch_id
                })
        
        return {
            'awards': results,
            'total': len(results),
            'skip': skip,
            'limit': limit
        }
    
    def rvz_override_status(
        self,
        award_id: int,
        award_type: str,
        new_status: str,
        rvz_id: str,
        reason: str
    ) -> Dict[str, Any]:
        """
        RVZ override any award status (complete control)
        """
        # Get the award
        if award_type == 'direct':
            award = self.db.query(UserAwardProgress).filter(UserAwardProgress.id == award_id).first()
            entity_type = 'direct_award'
        elif award_type == 'matching':
            award = self.db.query(UserMatchingAwardProgress).filter(UserMatchingAwardProgress.id == award_id).first()
            entity_type = 'matching_award'
        elif award_type == 'bonanza':
            award = self.db.query(DynamicBonanzaHistory).filter(DynamicBonanzaHistory.id == award_id).first()
            entity_type = 'bonanza'
        else:
            return {'error': 'Invalid award type'}
        
        if not award:
            return {'error': 'Award not found'}
        
        old_status = award.processed_status
        
        # RVZ can change to any status
        award.processed_status = new_status
        award.rvz_action_by = rvz_id
        award.rvz_action_at = get_indian_time()
        award.rvz_action_type = 'override'
        award.rvz_notes = reason
        
        # Create audit log
        audit = AwardAuditLog(
            entity_type=entity_type,
            entity_id=award.id,
            action='rvz_override',
            old_status=old_status,
            new_status=new_status,
            actor_role='RVZ ID',
            actor_id=rvz_id,
            notes=reason,
            timestamp=get_indian_time()
        )
        self.db.add(audit)
        
        self.db.commit()
        
        return {
            'success': True,
            'award_id': award.id,
            'old_status': old_status,
            'new_status': new_status,
            'message': f'Status overridden from {old_status} to {new_status} by RVZ'
        }
    
    def _get_delivery_status(self, award) -> str:
        """
        DC PROTOCOL: Determine delivery/transit status based on NEW 6-stage processed_status field
        Returns user-friendly status string for Admin/Procurement view
        
        6-Stage Workflow Mapping:
        1. Pending Approval → Pending Dispatch
        2. Admin Approved → Pending Dispatch  
        3. Procurement Pending (RVZ Approved) → Pending Dispatch
        4. Processed for Dispatch (Ordered) → Ordered
        5. Dispatched (Shipped) → In Transit
        6. Delivered → Delivered
        """
        # DC PROTOCOL: Use processed_status field (single source of truth)
        status = award.processed_status if hasattr(award, 'processed_status') else None
        
        if not status:
            return 'Pending Dispatch'
        
        # 6-Stage Workflow Mapping
        status_mapping = {
            'Delivered': 'Delivered',
            'Dispatched': 'In Transit',
            'Processed for Dispatch': 'Ordered',
            'Procurement Pending': 'Pending Dispatch',
            'Admin Approved': 'Pending Dispatch',
            'Pending Approval': 'Pending Dispatch',
            'Pending': 'Pending Dispatch',
            'pending': 'Pending Dispatch',
            'RVZ Approved': 'Pending Dispatch',
            'Rejected': 'N/A',
            'RVZ Rejected': 'N/A'
        }
        
        return status_mapping.get(status, 'Pending Dispatch')
    
    def get_audit_trail(
        self,
        entity_type: Optional[str] = None,
        entity_id: Optional[int] = None,
        actor_id: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> Dict[str, Any]:
        """
        Get complete audit trail
        """
        query = self.db.query(AwardAuditLog)
        
        if entity_type:
            query = query.filter(AwardAuditLog.entity_type == entity_type)
        if entity_id:
            query = query.filter(AwardAuditLog.entity_id == entity_id)
        if actor_id:
            query = query.filter(AwardAuditLog.actor_id == actor_id)
        
        date_from_parsed = parse_date_filter(date_from)
        if date_from_parsed:
            query = query.filter(AwardAuditLog.timestamp >= date_from_parsed)
        
        date_to_parsed = parse_date_filter(date_to)
        if date_to_parsed:
            query = query.filter(AwardAuditLog.timestamp <= date_to_parsed)
        
        audit_logs = query.order_by(desc(AwardAuditLog.timestamp)).offset(skip).limit(limit).all()
        
        results = []
        for log in audit_logs:
            results.append({
                'id': log.id,
                'entity_type': log.entity_type,
                'entity_id': log.entity_id,
                'action': log.action,
                'old_status': log.old_status,
                'new_status': log.new_status,
                'actor_role': log.actor_role,
                'actor_id': log.actor_id,
                'notes': log.notes,
                'metadata': log.metadata,
                'timestamp': log.timestamp.isoformat() if log.timestamp else None,
                'batch_id': log.batch_id
            })
        
        return {
            'audit_logs': results,
            'total': len(results),
            'skip': skip,
            'limit': limit
        }
