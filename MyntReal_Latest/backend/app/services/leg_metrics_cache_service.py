"""
Leg Metrics Cache Service
Populates and maintains user_leg_metrics table for dashboard performance optimization
"""

from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional, List
import logging

from app.models.user import User
from app.models.user_leg_metrics import UserLegMetrics
from app.models.placement import Placement
from app.core.scheduler import (
    calculate_effective_matching_count,
    check_direct_referrals_both_sides,
    check_first_matching_achieved
)

logger = logging.getLogger(__name__)

class LegMetricsCacheService:
    """Service to manage user_leg_metrics cache table"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def refresh_user_metrics(self, user_id: str, source: str = 'scheduler') -> Optional[UserLegMetrics]:
        """
        Refresh metrics for a single user
        
        Args:
            user_id: User ID to refresh
            source: Source of calculation ('scheduler', 'placement_hook', 'manual')
        
        Returns:
            Updated UserLegMetrics record or None if user not found
        """
        try:
            user = self.db.query(User).filter(User.id == user_id).first()
            if not user:
                logger.warning(f"User {user_id} not found, skipping metrics refresh")
                return None
            
            # Calculate matching data (for left/right points and eligibility)
            matching_result = calculate_effective_matching_count(self.db, user_id)
            
            # Import text for SQL queries
            from sqlalchemy import text
            
            # Calculate eligibility flags
            has_left_direct = check_direct_referrals_both_sides(self.db, user_id)
            has_right_direct = has_left_direct  # Same function checks both sides
            first_match = check_first_matching_achieved(self.db, user_id)
            
            # Get direct referral counts
            direct_refs = self.db.query(User).filter(User.referrer_id == user_id).all()
            total_direct = len(direct_refs)
            active_direct = sum(1 for ref in direct_refs if ref.activation_date is not None)
            
            # Get binary tree counts - RECURSIVE to count ALL downline (not just direct children)
            # CRITICAL: Preserve root_leg throughout recursion (not immediate parent's side)
            from sqlalchemy import text
            
            # Recursive query to get ALL downline counts
            recursive_query = text("""
                WITH RECURSIVE downline AS (
                    -- Base case: Direct children (establishes root LEFT or RIGHT leg)
                    SELECT child_id, side as root_leg
                    FROM placement
                    WHERE parent_id = :user_id
                    
                    UNION ALL
                    
                    -- Recursive: PRESERVE root_leg from parent (not p.side!)
                    SELECT p.child_id, d.root_leg
                    FROM placement p
                    INNER JOIN downline d ON p.parent_id = d.child_id
                )
                SELECT 
                    COUNT(*) FILTER (WHERE root_leg = 'left') as left_count,
                    COUNT(*) FILTER (WHERE root_leg = 'right') as right_count
                FROM downline
            """)
            
            result = self.db.execute(recursive_query, {"user_id": user_id}).fetchone()
            left_count = result[0] if result and result[0] else 0
            right_count = result[1] if result and result[1] else 0
            
            # Active counts - RECURSIVE for ALL active downline
            # CRITICAL: Preserve root_leg throughout recursion
            active_query = text("""
                WITH RECURSIVE downline AS (
                    -- Base case: Direct children (establishes root LEFT or RIGHT leg)
                    SELECT p.child_id, p.side as root_leg
                    FROM placement p
                    WHERE p.parent_id = :user_id
                    
                    UNION ALL
                    
                    -- Recursive: PRESERVE root_leg from parent (not p.side!)
                    SELECT p.child_id, d.root_leg
                    FROM placement p
                    INNER JOIN downline d ON p.parent_id = d.child_id
                )
                SELECT 
                    COUNT(*) FILTER (WHERE d.root_leg = 'left' AND u.package_points > 0) as left_active,
                    COUNT(*) FILTER (WHERE d.root_leg = 'right' AND u.package_points > 0) as right_active
                FROM downline d
                INNER JOIN "user" u ON u.id = d.child_id
            """)
            
            active_result = self.db.execute(active_query, {"user_id": user_id}).fetchone()
            left_active = active_result[0] if active_result and active_result[0] else 0
            right_active = active_result[1] if active_result and active_result[1] else 0
            
            # DC Protocol Fix: Matching count = MIN(left_active, right_active)
            # Income is generated same day as activation, so count should reflect current active state
            # Base structure: matching pairs = minimum of both legs' active counts
            earned_matching_pairs = min(left_active, right_active)
            
            # DC Protocol: Ved metrics updated ONLY by midnight scheduler (not activation hooks)
            # This keeps activation fast - no heavy recursive Ved queries
            # Ved data may be slightly stale until next scheduler run (acceptable per user requirements)
            
            # Check if record exists
            metrics = self.db.query(UserLegMetrics).filter(
                UserLegMetrics.user_id == user_id
            ).first()
            
            if metrics:
                # Update existing record
                metrics.left_points = matching_result['left_points']
                metrics.right_points = matching_result['right_points']
                metrics.total_points = matching_result['left_points'] + matching_result['right_points']
                metrics.effective_matching_count = earned_matching_pairs
                metrics.has_left_direct = has_left_direct
                metrics.has_right_direct = has_right_direct
                metrics.first_match_achieved = first_match
                metrics.total_direct_referrals = total_direct
                metrics.active_direct_referrals = active_direct
                metrics.left_team_count = left_count
                metrics.right_team_count = right_count
                metrics.left_active_count = left_active
                metrics.right_active_count = right_active
                # DC Protocol: Ved metrics NOT updated on activation (only by scheduler)
                # Keep existing Ved values - will be refreshed at midnight
                metrics.calculation_source = source
            else:
                # Create new record
                from datetime import datetime
                metrics = UserLegMetrics(
                    user_id=user_id,
                    left_points=matching_result['left_points'],
                    right_points=matching_result['right_points'],
                    total_points=matching_result['left_points'] + matching_result['right_points'],
                    effective_matching_count=earned_matching_pairs,
                    has_left_direct=has_left_direct,
                    has_right_direct=has_right_direct,
                    first_match_achieved=first_match,
                    total_direct_referrals=total_direct,
                    active_direct_referrals=active_direct,
                    left_team_count=left_count,
                    right_team_count=right_count,
                    left_active_count=left_active,
                    right_active_count=right_active,
                    # DC Protocol: Ved metrics default to 0, will be set by midnight scheduler
                    ved_team_total=0,
                    ved_team_active=0,
                    ved_metrics_refreshed_at=None,
                    calculation_source=source
                )
                self.db.add(metrics)
            
            self.db.commit()
            self.db.refresh(metrics)
            logger.info(f"✅ Refreshed metrics for user {user_id} (source: {source})")
            return metrics
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"❌ Error refreshing metrics for user {user_id}: {e}")
            return None
    
    def bulk_refresh_all_users(self, batch_size: int = 100) -> int:
        """
        Bulk refresh metrics for all users (called by nightly scheduler)
        
        Args:
            batch_size: Number of users to process in each batch
        
        Returns:
            Number of users processed
        """
        logger.info("🔄 Starting bulk refresh of all user leg metrics...")
        
        try:
            # Get all active users
            users = self.db.query(User).filter(User.package_points > 0).all()
            total_users = len(users)
            processed = 0
            
            for i in range(0, total_users, batch_size):
                batch = users[i:i + batch_size]
                for user in batch:
                    self.refresh_user_metrics(user.id, source='scheduler')
                    processed += 1
                
                logger.info(f"📊 Processed {processed}/{total_users} users")
            
            logger.info(f"✅ Bulk refresh complete: {processed} users processed")
            return processed
            
        except Exception as e:
            logger.error(f"❌ Error in bulk refresh: {e}")
            return 0
    
    def refresh_affected_users(self, affected_user_ids: List[str]) -> int:
        """
        Refresh metrics for specific affected users (called by placement hooks)
        
        Args:
            affected_user_ids: List of user IDs to refresh
        
        Returns:
            Number of users refreshed
        """
        logger.info(f"🔄 Refreshing metrics for {len(affected_user_ids)} affected users...")
        
        refreshed = 0
        for user_id in affected_user_ids:
            if self.refresh_user_metrics(user_id, source='placement_hook'):
                refreshed += 1
        
        logger.info(f"✅ Refreshed metrics for {refreshed} users")
        return refreshed
    
    def get_user_metrics(self, user_id: str) -> Optional[UserLegMetrics]:
        """
        Get cached metrics for a user (fast read for dashboard)
        
        Args:
            user_id: User ID to fetch
        
        Returns:
            UserLegMetrics record or None
        """
        return self.db.query(UserLegMetrics).filter(
            UserLegMetrics.user_id == user_id
        ).first()
    
    def update_all_snapshots(self) -> int:
        """
        Update all user snapshots to current values
        Called after earnings calculation to capture current state for "Previous" difference tracking
        DC Protocol: Uses pg_try_advisory_lock to ensure only one worker runs this at a time.
        Uses IST Kolkata time for all timestamp fields (DC Protocol - IST standard).
        
        Returns:
            Number of users updated
        """
        from datetime import datetime
        from sqlalchemy import text
        import pytz

        _IST = pytz.timezone('Asia/Kolkata')
        _SNAPSHOT_LOCK_ID = 98765432

        def _ist_now():
            return datetime.now(_IST).replace(tzinfo=None)

        lock_acquired = self.db.execute(
            text("SELECT pg_try_advisory_lock(:lid)"), {"lid": _SNAPSHOT_LOCK_ID}
        ).scalar()
        if not lock_acquired:
            logger.info("📸 Snapshot update skipped — another worker already running it")
            return 0

        logger.info("📸 Starting snapshot update for all users...")
        updated_count = 0

        try:
            all_metrics = self.db.query(UserLegMetrics).all()
            
            for metrics in all_metrics:
                # Calculate current Ved counts for this user
                user = self.db.query(User).filter(User.id == metrics.user_id).first()
                if not user:
                    continue
                
                # Get direct referrals ordered by registration date
                direct_refs = self.db.query(User).filter(
                    User.referrer_id == metrics.user_id
                ).order_by(User.registration_date).all()
                
                ved_total = 0
                ved_activated = 0
                
                # Calculate Ved team (position 3 onwards)
                if len(direct_refs) >= 3:
                    ved_root = direct_refs[2]
                    
                    # DC Protocol: Consistent Ved counting (EXCLUDING Ved Head)
                    # Count downline under Ved root, NOT including the Ved head itself
                    ved_query = text("""
                        WITH RECURSIVE ved_downline AS (
                            SELECT 
                                p.child_id as user_id,
                                u.activation_date,
                                u.is_ved,
                                1 as level
                            FROM placement p
                            INNER JOIN "user" u ON u.id = p.child_id
                            WHERE p.parent_id = :ved_root_id
                            
                            UNION ALL
                            
                            SELECT 
                                p.child_id,
                                u.activation_date,
                                u.is_ved,
                                vd.level + 1
                            FROM ved_downline vd
                            INNER JOIN placement p ON p.parent_id = vd.user_id
                            INNER JOIN "user" u ON u.id = p.child_id
                            WHERE vd.level < 50
                              AND vd.is_ved = FALSE
                        )
                        SELECT 
                            COUNT(*) as total_count,
                            COUNT(CASE WHEN activation_date IS NOT NULL THEN 1 END) as activated_count
                        FROM ved_downline
                    """)
                    
                    result = self.db.execute(ved_query, {
                        'ved_root_id': str(ved_root.id)
                    }).fetchone()
                    
                    if result:
                        ved_total = result[0] or 0
                        ved_activated = result[1] or 0
                
                # Update CURRENT Ved values (DC Protocol - single source for dashboard reads)
                metrics.ved_team_total = ved_total
                metrics.ved_team_active = ved_activated
                metrics.ved_metrics_refreshed_at = _ist_now()
                
                # Update snapshot columns to current values (for delta calculation)
                metrics.snapshot_direct_referrals = metrics.total_direct_referrals
                metrics.snapshot_active_direct_referrals = metrics.active_direct_referrals
                metrics.snapshot_matching_count = metrics.effective_matching_count
                metrics.snapshot_left_team = metrics.left_team_count
                metrics.snapshot_right_team = metrics.right_team_count
                metrics.snapshot_left_active = metrics.left_active_count
                metrics.snapshot_right_active = metrics.right_active_count
                metrics.snapshot_ved_total = ved_total
                metrics.snapshot_ved_active = ved_activated
                metrics.last_snapshot_at = _ist_now()
                
                updated_count += 1
            
            self.db.commit()
            logger.info(f"✅ Snapshots updated for {updated_count} users")
            return updated_count
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"❌ Error updating snapshots: {e}")
            return 0
        finally:
            try:
                self.db.execute(
                    text("SELECT pg_advisory_unlock(:lid)"), {"lid": _SNAPSHOT_LOCK_ID}
                )
            except Exception:
                pass
