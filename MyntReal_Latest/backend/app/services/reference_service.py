"""
Reference Service for FastAPI - Binary Tree & Income Calculations
Preserves exact Flask business logic and calculation methods
"""

from typing import List, Dict, Optional, Tuple, Any
from datetime import datetime, date, timedelta
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc, asc, text

from app.models.user import User
from app.models.placement import Placement, PlacementLog
from app.models.transaction import Transaction, VedIncome, CompanyEarnings
from app.models.awards import DirectAwardTier, UserAwardProgress, MatchingAwardTier, UserMatchingAwardProgress
from app.models.bonanza import DynamicBonanza  # DC Protocol: BonanzaProgress deprecated
from app.models.base import get_indian_time
from app.services.sql_utils import get_binary_tree_bulk_sql

class ReferenceService:
    """
    Reference Service handling all binary tree operations and income calculations
    Preserves exact Flask calculation logic
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    # Binary Tree Management
    def get_user_placement_as_child(self, user_id: str) -> Optional[Placement]:
        """Get user's placement as a child in binary tree (preserves Flask placement logic)"""
        return self.db.query(Placement).filter(Placement.child_id == user_id).first()
    
    def get_children_placements(self, parent_id: str) -> Dict[str, Optional[str]]:
        """Get left and right children for a parent user"""
        placements = self.db.query(Placement).filter(
            and_(
                Placement.parent_id == parent_id,
                Placement.status.ilike('active')
            )
        ).all()
        
        children = {"left": None, "right": None}
        for placement in placements:
            if placement.side == 'left':
                children["left"] = placement.child_id
            elif placement.side == 'right':
                children["right"] = placement.child_id
        
        return children
    
    def get_team_tree(self, user_id: str, levels: int = 10) -> Dict[str, Any]:
        """
        Get complete team tree structure - OPTIMIZED with bulk SQL fetch
        
        Performance: 100x faster than recursive queries
        - 3 levels: 1 query vs 15 queries (old method)
        - 4 levels: 1 query vs 31 queries (old method)
        
        Uses bulk SQL CTE to fetch all nodes in one query,
        then assembles tree structure in Python memory
        """
        # Fetch ALL nodes in one query using recursive CTE
        nodes = get_binary_tree_bulk_sql(self.db, user_id, levels)
        
        if not nodes:
            return {
                "user_id": user_id,
                "user_name": "Unknown",
                "registration_date": None,
                "package_type": "none",
                "is_active": False,
                "level": 0,
                "children": {"left": None, "right": None}
            }
        
        # Build tree structure in memory using dict lookups
        def build_tree_from_nodes(current_id: str) -> Dict[str, Any]:
            node_data = nodes.get(current_id)
            if not node_data:
                return None
            
            # Map package_points to package_type
            pkg_points = node_data.get("package_points", 0)
            if pkg_points >= 1.0:
                package_type = "Platinum"
            elif pkg_points >= 0.5:
                package_type = "Diamond"
            elif pkg_points > 0:
                package_type = "Star/Loyal"
            else:
                package_type = "none"
            
            tree_node = {
                "user_id": node_data["user_id"],
                "user_name": node_data.get("name", "Unknown"),
                "gender": node_data.get("gender"),  # 'Male', 'Female', or None
                "registration_date": node_data.get("registration_date").isoformat() if node_data.get("registration_date") else None,
                "package_type": package_type,
                "activation_date": node_data.get("activation_date"),
                "is_active": node_data.get("activation_date") is not None,
                "level": node_data.get("level", 0),
                "children": {
                    "left": None,
                    "right": None
                }
            }
            
            # Find children by looking for nodes with this as parent_id
            for child_id, child_data in nodes.items():
                if child_data.get("parent_id") == current_id:
                    child_side = child_data.get("side")
                    if child_side == "left":
                        tree_node["children"]["left"] = build_tree_from_nodes(child_id)
                    elif child_side == "right":
                        tree_node["children"]["right"] = build_tree_from_nodes(child_id)
            
            return tree_node
        
        return build_tree_from_nodes(user_id)
    
    def get_team_counts(self, user_id: str, active_only: bool = True) -> Dict[str, int]:
        """
        Get team counts for left and right legs using SQL (10x faster!)
        Now counts ONLY ACTIVE members (activation_date IS NOT NULL) by default
        
        CRITICAL: Always traverses ALL nodes (active or inactive) but only COUNTS active ones.
        This ensures active descendants under inactive parents are still counted.
        
        Args:
            user_id: The parent user ID
            active_only: If True (default), only count activated members
        """
        # Use SQL-optimized version for 10x performance
        from app.services.sql_utils import get_team_counts_sql
        return get_team_counts_sql(self.db, user_id, active_only)
        
        # Old recursive Python version (kept for reference, not used)
        def count_team_recursive_old(current_user_id: str) -> int:
            if not current_user_id:
                return 0
            
            # ALWAYS traverse children, but only count if active
            count = 0
            
            if active_only:
                user = self.db.query(User).filter(User.id == current_user_id).first()
                if user and user.activation_date:
                    count = 1  # Count this node only if active
                # CONTINUE TRAVERSING even if inactive (to count active descendants)
            else:
                count = 1  # Count all nodes when active_only=False
            
            # Always get and traverse children regardless of current node's activation status
            children = self.get_children_placements(current_user_id)
            
            if children["left"]:
                count += count_team_recursive_old(children["left"])
            if children["right"]:
                count += count_team_recursive(children["right"])
            
            return count
        
        children = self.get_children_placements(user_id)
        
        left_count = count_team_recursive(children["left"]) if children["left"] else 0
        right_count = count_team_recursive(children["right"]) if children["right"] else 0
        
        return {
            "left_count": left_count,
            "right_count": right_count,
            "total_count": left_count + right_count
        }
    
    def auto_place_user(self, new_user_id: str, sponsor_id: str, 
                       preferred_position: Optional[str] = None) -> Dict[str, Any]:
        """
        Auto-place new user in binary tree using parent/child/side schema
        Preserves Flask auto-placement algorithm
        """
        def find_placement_position(start_user_id: str, position_preference: str = "left") -> Tuple[str, str]:
            """Find the next available position using breadth-first search"""
            queue = [(start_user_id, position_preference)]
            
            while queue:
                current_user_id, preferred_side = queue.pop(0)
                children = self.get_children_placements(current_user_id)
                
                # Check preferred side first
                if preferred_side == "left" and not children["left"]:
                    return current_user_id, "left"
                elif preferred_side == "right" and not children["right"]:
                    return current_user_id, "right"
                
                # Check other side
                other_side = "right" if preferred_side == "left" else "left"
                if other_side == "left" and not children["left"]:
                    return current_user_id, "left"
                elif other_side == "right" and not children["right"]:
                    return current_user_id, "right"
                
                # Add children to queue for next level
                if children["left"]:
                    queue.append((children["left"], "left"))
                if children["right"]:
                    queue.append((children["right"], "right"))
            
            return sponsor_id, "left"  # Fallback
        
        # Find placement position
        parent_id, side = find_placement_position(
            sponsor_id, 
            preferred_position or "left"
        )
        
        # Create new placement using parent/child/side schema
        new_placement = Placement(
            parent_id=parent_id,
            child_id=new_user_id,
            side=side,
            placed_at=get_indian_time(),
            placement_method="automatic",
            status="active"
        )
        
        # Log the placement
        placement_log = PlacementLog(
            new_user_id=new_user_id,
            sponsor_user_id=sponsor_id,
            target_parent_id=parent_id,
            side=side,
            action="Placed",
            status_after="active",
            actor_role="system",
            timestamp=get_indian_time()
        )
        
        self.db.add(new_placement)
        self.db.add(placement_log)
        
        # Update User.position field for Ved Income eligibility check
        new_user = self.db.query(User).filter(User.id == new_user_id).first()
        if new_user:
            new_user.position = side.upper()  # Set to 'LEFT' or 'RIGHT'
        
        self.db.commit()
        
        # Update cache for affected users (new user, parent, and ancestors)
        try:
            from app.services.leg_metrics_cache_service import LegMetricsCacheService
            cache_service = LegMetricsCacheService(self.db)
            
            # Update new user's cache
            cache_service.refresh_user_metrics(new_user_id, source='placement_hook')
            
            # Update parent's cache (they now have a new child)
            cache_service.refresh_user_metrics(parent_id, source='placement_hook')
            
            logger.info(f"✅ Cache updated for user {new_user_id} and parent {parent_id} after placement")
        except Exception as e:
            logger.error(f"⚠️ Cache update failed after placement: {e}")
        
        # Sync Ved Team membership
        try:
            from app.services.ved_team_service import VedTeamService
            ved_service = VedTeamService(self.db)
            ved_service.sync_ved_team_for_new_placement(new_user_id, parent_id, side)
        except Exception as e:
            logger.error(f"⚠️ Ved Team sync failed after placement: {e}")
        
        return {
            "success": True,
            "placement": {
                "user_id": new_user_id,
                "sponsor_id": sponsor_id,
                "parent_id": parent_id,
                "position": side,
                "placement_date": new_placement.placed_at.isoformat()
            }
        }
    
    def manual_place_user(self, new_user_id: str, position_id: str, position: str) -> Dict[str, Any]:
        """
        Manually place user in binary tree at specified position
        NO AUTO-PLACEMENT - User must specify exact position_id and position (Left/Right)
        
        Args:
            new_user_id: MNR ID of new user to place
            position_id: MNR ID of user under whom to place
            position: "Left" or "Right" placement side
        """
        # Validate position
        if position not in ["Left", "Right"]:
            raise ValueError(f"Position must be 'Left' or 'Right', got: {position}")
        
        # Check if position is already occupied
        children = self.get_children_placements(position_id)
        side_lower = position.lower()
        
        if children[side_lower]:
            raise ValueError(f"Position '{position}' under {position_id} is already occupied by {children[side_lower]}")
        
        # Create placement record
        new_placement = Placement(
            parent_id=position_id,
            child_id=new_user_id,
            side=side_lower,
            placed_at=get_indian_time(),
            placement_method="manual",
            status="active"
        )
        
        # Log the placement
        placement_log = PlacementLog(
            new_user_id=new_user_id,
            sponsor_user_id=None,  # Sponsor not tracked in manual placement
            target_parent_id=position_id,
            side=side_lower,
            action="manual_placement",
            status_after="active",
            timestamp=get_indian_time(),
            actor_role="system"
        )
        
        try:
            self.db.add(new_placement)
            self.db.add(placement_log)
            
            # Update User.position field for Ved Income eligibility check
            new_user = self.db.query(User).filter(User.id == new_user_id).first()
            if new_user:
                new_user.position = side_lower.upper()  # Set to 'LEFT' or 'RIGHT'
            
            self.db.commit()
        except Exception as e:
            import traceback
            logger.error(f"Database commit error in manual_place_user: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise
        
        # Update cache
        try:
            from app.services.leg_metrics_cache_service import LegMetricsCacheService
            cache_service = LegMetricsCacheService(self.db)
            
            cache_service.refresh_user_metrics(new_user_id, source='manual_placement')
            cache_service.refresh_user_metrics(position_id, source='manual_placement')
        except Exception as e:
            # Cache update is not critical
            pass
        
        # Sync Ved Team membership
        try:
            from app.services.ved_team_service import VedTeamService
            ved_service = VedTeamService(self.db)
            ved_service.sync_ved_team_for_new_placement(new_user_id, position_id, side_lower)
        except Exception as e:
            logger.error(f"⚠️ Ved Team sync failed after manual placement: {e}")
        
        return {
            "success": True,
            "placement": {
                "user_id": new_user_id,
                "parent_id": position_id,
                "position": position,
                "placement_method": "manual",
                "placement_date": new_placement.placed_at.isoformat()
            }
        }
    
    def extreme_place_user(self, new_user_id: str, sponsor_id: str, position: str) -> Dict[str, Any]:
        """
        Place user at EXTREME LEFT or EXTREME RIGHT position under sponsor
        Uses DEPTH-FIRST SEARCH to find the deepest available position on one side
        
        Logic:
        - User chooses LEFT or RIGHT position during signup
        - System finds EXTREME position (leftmost in left subtree OR rightmost in right subtree)
        - Start from sponsor's chosen side, keep going deep on that side until empty position found
        
        Args:
            new_user_id: MNR ID of new user to place
            sponsor_id: MNR ID of sponsor (referrer)
            position: "Left" or "Right" - user's chosen position preference
        
        Returns:
            Dict with placement details
        """
        import logging
        logger = logging.getLogger(__name__)
        
        # Validate position
        position_normalized = position.capitalize() if position else "Left"
        if position_normalized not in ["Left", "Right"]:
            raise ValueError(f"Position must be 'Left' or 'Right', got: {position}")
        
        side_lower = position_normalized.lower()  # "left" or "right"
        
        def find_extreme_position(current_user_id: str, target_side: str) -> str:
            """
            Find extreme position using DEPTH-FIRST SEARCH
            Keep going on target_side until we find an empty position
            
            Args:
                current_user_id: Current node in the tree
                target_side: "left" or "right" - which side to go deep on
            
            Returns:
                MNR ID of the parent where we can place the new user
            """
            children = self.get_children_placements(current_user_id)
            
            # If target side is empty, we found our position!
            if not children[target_side]:
                return current_user_id
            
            # Target side is occupied, go deeper on that side (DEPTH-FIRST)
            return find_extreme_position(children[target_side], target_side)
        
        # Find the extreme position starting from sponsor
        parent_id = find_extreme_position(sponsor_id, side_lower)
        
        # Double-check the position is actually available
        children = self.get_children_placements(parent_id)
        if children[side_lower]:
            raise ValueError(
                f"CRITICAL ERROR: Extreme position calculation failed. "
                f"Position '{side_lower}' under {parent_id} is occupied by {children[side_lower]}"
            )
        
        # Create placement record
        new_placement = Placement(
            parent_id=parent_id,
            child_id=new_user_id,
            side=side_lower,
            placed_at=get_indian_time(),
            placement_method="automatic_extreme",  # Mark as automatic extreme placement
            status="active"
        )
        
        # Log the placement
        placement_log = PlacementLog(
            new_user_id=new_user_id,
            sponsor_user_id=sponsor_id,
            target_parent_id=parent_id,
            side=side_lower,
            action="Placed",
            status_after="active",
            actor_role="system",
            timestamp=get_indian_time()
        )
        
        try:
            self.db.add(new_placement)
            self.db.add(placement_log)
            self.db.commit()
            
            logger.info(
                f"✅ Extreme placement successful: User {new_user_id} placed under {parent_id} "
                f"on {side_lower} side (sponsor: {sponsor_id})"
            )
        except Exception as e:
            import traceback
            logger.error(f"Database commit error in extreme_place_user: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            self.db.rollback()
            raise
        
        # Update cache for affected users
        try:
            from app.services.leg_metrics_cache_service import LegMetricsCacheService
            cache_service = LegMetricsCacheService(self.db)
            
            # Update new user's cache
            cache_service.refresh_user_metrics(new_user_id, source='extreme_placement')
            
            # Update parent's cache (they now have a new child)
            cache_service.refresh_user_metrics(parent_id, source='extreme_placement')
            
            logger.info(f"✅ Cache updated for user {new_user_id} and parent {parent_id} after extreme placement")
        except Exception as e:
            # Cache update is not critical, log and continue
            logger.warning(f"⚠️ Cache update failed after extreme placement: {e}")
        
        # Sync Ved Team membership
        try:
            from app.services.ved_team_service import VedTeamService
            ved_service = VedTeamService(self.db)
            ved_service.sync_ved_team_for_new_placement(new_user_id, parent_id, side_lower)
        except Exception as e:
            logger.error(f"⚠️ Ved Team sync failed after extreme placement: {e}")
        
        return {
            "success": True,
            "placement": {
                "user_id": new_user_id,
                "sponsor_id": sponsor_id,
                "parent_id": parent_id,
                "position": side_lower,
                "placement_date": new_placement.placed_at.isoformat(),
                "placement_method": "automatic_extreme"
            }
        }
    
    # Income Calculation Methods
    def calculate_direct_referral_income(self, user_id: str, month: Optional[str] = None) -> Dict[str, Any]:
        """
        Calculate direct referral income based on NEW 4-package system
        - Platinum (15k): ₹3,000 (1x max)
        - Diamond (7.5k): ₹1,500 (2x max)
        - Blue (1k): ₹0 initially, can get ₹1,500 up to 2x on upgrade
        - Loyal (500): ₹0 initially, can get ₹1,500 up to 2x on upgrade
        
        Shows all historical data
        """
        from app.constants import get_referral_bonus
        
        if not month:
            month = datetime.now().strftime("%Y-%m")
        
        start_date = datetime.strptime(f"{month}-01", "%Y-%m-%d")
        if month == datetime.now().strftime("%Y-%m"):
            end_date = datetime.now()
        else:
            next_month = start_date.replace(month=start_date.month + 1 if start_date.month < 12 else 1,
                                          year=start_date.year if start_date.month < 12 else start_date.year + 1)
            end_date = next_month - timedelta(days=1)
        
        # Get direct referrals for the period
        direct_referrals = self.db.query(User).filter(
            and_(
                User.referrer_id == user_id,
                User.registration_date >= start_date,
                User.registration_date <= end_date
            )
        ).all()
        
        total_income = Decimal('0.00')
        referrals_detail = []
        
        for referral in direct_referrals:
            # Get package points (15000, 7500, 1000, 500)
            points = referral.get_points()
            
            # Get current bonus count for this referral
            bonus_count = getattr(referral, 'referral_bonus_count', 0)
            
            # Calculate referral bonus based on points and bonus count
            referral_income = Decimal(str(get_referral_bonus(points, bonus_count)))
            
            if referral_income > 0:
                total_income += referral_income
            
            referrals_detail.append({
                "user_id": referral.id,
                "name": referral.name,
                "package_points": points,
                "registration_date": referral.registration_date.isoformat(),
                "income_amount": float(referral_income),
                "bonus_count": bonus_count,
                "can_earn_more": bonus_count < (1 if points == 15000 else 2)
            })
        
        return {
            "user_id": user_id,
            "period": month,
            "total_income": float(total_income),
            "referral_count": len(direct_referrals),
            "referrals_detail": referrals_detail
        }
    
    def calculate_matching_referral_income(self, user_id: str, month: Optional[str] = None) -> Dict[str, Any]:
        """
        Calculate matching referral income (binary tree pairs)
        CORRECT FORMULA: pairs × package_points × ₹2,000
        
        FIRST MATCHING RULE: Requires 1:2 or 2:1 (minimum 3 active members)
        ELIGIBILITY: Requires 1:1 direct active + 1:2/2:1 matching balance
        """
        from app.services.award_service import AwardService
        
        if not month:
            month = datetime.now().strftime("%Y-%m")
        
        # Get user details
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return {"error": "User not found"}
        
        # Get PACKAGE POINTS by leg (not user count)
        from app.services.sql_utils import get_leg_points_sql
        leg_points = get_leg_points_sql(self.db, user_id, side='both')
        left_points = leg_points['left']
        right_points = leg_points['right']
        
        # UNIVERSAL ELIGIBILITY CHECK
        award_service = AwardService(self.db)
        eligibility = award_service.check_universal_eligibility(user_id)
        
        # Check if user has received any matching referral income before (first matching done?)
        from app.models.transaction import PendingIncome
        first_matching_done = self.db.query(PendingIncome).filter(
            PendingIncome.user_id == user_id,
            PendingIncome.income_type == 'Matching Referral',
            PendingIncome.gross_amount > 0
        ).first() is not None
        
        # Calculate matching pairs with FIRST MATCHING RULE (POINTS-BASED)
        # IMPORTANT: Progress CONTINUES regardless of eligibility (for matching income only)
        if not first_matching_done:
            # First matching requires 2:1 or 1:2 POINTS (minimum 3 points total)
            # Once condition is met, calculate ALL pairs using MIN formula
            if left_points >= 1.0 and right_points >= 2.0:
                matching_pairs = min(left_points, right_points)  # Calculate ALL available pairs
            elif left_points >= 2.0 and right_points >= 1.0:
                matching_pairs = min(left_points, right_points)  # Calculate ALL available pairs
            else:
                matching_pairs = 0  # Not enough points for first matching yet
        else:
            # Subsequent matchings use standard 1:1 formula (MIN of both legs)
            matching_pairs = min(left_points, right_points)
        
        # Get user package details
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return {"error": "User not found"}
        
        # CORRECT RATE: ₹2,000 per pair (base rate)
        # Total income = pairs × package_points × ₹2,000
        package_points = Decimal(str(user.package_points)) if user.package_points else Decimal('0')
        base_rate = Decimal('2000.00')
        per_pair_income = base_rate
        matching_pairs_decimal = Decimal(str(matching_pairs))
        
        # ELIGIBILITY ENFORCEMENT: If not eligible, income = 0 (not calculated/held)
        if not eligibility["is_eligible"]:
            return {
                "user_id": user_id,
                "period": month,
                "left_points": left_points,
                "right_points": right_points,
                "matching_pairs": 0,
                "per_pair_income": 0.0,
                "total_income": 0.0,
                "calculated_income": 0.0,
                "income_status": "not_eligible",
                "carry_forward": {"left": 0, "right": 0},
                "eligibility": eligibility,
                "note": f"Not eligible: {', '.join([r for r in eligibility.get('failed_checks', []) if r])}"
            }
        
        # Calculate income (only for eligible users)
        calculated_income = matching_pairs_decimal * package_points * base_rate
        total_income = calculated_income
        income_status = "releasable"
        
        return {
            "user_id": user_id,
            "period": month,
            "left_points": left_points,  # Changed from left_count to left_points
            "right_points": right_points,  # Changed from right_count to right_points
            "matching_pairs": matching_pairs,
            "per_pair_income": float(per_pair_income),
            "total_income": float(total_income),
            "calculated_income": float(calculated_income),
            "income_status": income_status,
            "carry_forward": {
                "left": left_points - float(matching_pairs_decimal),
                "right": right_points - float(matching_pairs_decimal)
            },
            "eligibility": eligibility,
            "note": "Progress continues but income released only when eligible" if income_status == "held_pending_eligibility" else "Income released - eligibility met"
        }
    
    def calculate_ved_income(self, user_id: str, month: Optional[str] = None, 
                            custom_start_date: Optional[str] = None, 
                            custom_end_date: Optional[str] = None) -> Dict[str, Any]:
        """
        Calculate Ved income based on VED PROGRAM
        - Ved Head (3rd direct referral) must be ACTIVATED to generate income
        - Ved Head activation: activation_date IS NOT NULL AND package_points >= 0.5
        - If Ved Head NOT activated → NO income generated (shows as "Missed")
        - If Ved Head IS activated → Income goes to Ved Owner
        - Rates: ₹1,000 (Platinum), ₹500 (Diamond)
        
        ELIGIBILITY: Requires 1:1 direct active + 1:2/2:1 matching balance
        Shows ALL historical data (lifetime) when no dates provided
        Supports custom date range for filtering
        """
        from app.constants import get_ved_income
        from app.services.award_service import AwardService
        
        # Handle custom date range (for lifetime data or filtering)
        if custom_start_date and custom_end_date:
            start_date = datetime.strptime(custom_start_date, "%Y-%m-%d")
            end_date = datetime.strptime(custom_end_date, "%Y-%m-%d")
        else:
            if not month:
                month = datetime.now().strftime("%Y-%m")
            
            # If month is very old (1970-01), it means show all lifetime data
            if month == "1970-01":
                start_date = datetime.strptime("1970-01-01", "%Y-%m-%d")
                end_date = datetime.now()
            else:
                start_date = datetime.strptime(f"{month}-01", "%Y-%m-%d")
                if month == datetime.now().strftime("%Y-%m"):
                    end_date = datetime.now()
                else:
                    next_month = start_date.replace(month=start_date.month + 1 if start_date.month < 12 else 1,
                                                  year=start_date.year if start_date.month < 12 else start_date.year + 1)
                    end_date = next_month - timedelta(days=1)
        
        # Get user who owns Ved members
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return {"error": "User not found"}
        
        # UNIVERSAL ELIGIBILITY CHECK
        award_service = AwardService(self.db)
        eligibility = award_service.check_universal_eligibility(user_id)
        
        if not eligibility["is_eligible"]:
            return {
                "user_id": user_id,
                "period": month,
                "is_ved_owner": False,
                "ved_amount": 0.0,
                "ved_members_count": 0,
                "activations_under_ved": [],
                "eligibility": eligibility,
                "ineligible_reason": "Does not meet universal eligibility requirements"
            }
        
        # Find all ACTIVATED Ved members owned by this user
        # CRITICAL: Only activated Ved Heads can generate income
        ved_members = self.db.query(User).filter(
            User.ved_owner_id == user_id,
            User.is_ved == True,
            User.activation_date.isnot(None),
            User.package_points >= 0.5
        ).all()
        
        if not ved_members:
            return {
                "user_id": user_id,
                "period": month,
                "is_ved_owner": False,
                "ved_amount": 0.0,
                "ved_members_count": 0,
                "activations_under_ved": [],
                "eligibility": eligibility
            }
        
        # Calculate income from ACTIVATIONS under Ved members
        # DC PROTOCOL: Use ved_team_member table as SINGLE SOURCE
        # Filter by is_active=true to exclude disconnected Ved Owners
        total_ved_income = Decimal('0.00')
        activations_detail = []
        
        for ved_member in ved_members:
            # Get ALL ACTIVE Ved Team members under this Ved Head
            # Use ved_team_member table (DC Protocol) - NO recursive CTE needed
            ved_team_query = text("""
                SELECT 
                    vtm.member_id as user_id,
                    u.name,
                    u.activation_date,
                    u.coupon_status,
                    u.package_points,
                    vtm.level
                FROM ved_team_member vtm
                INNER JOIN "user" u ON u.id = vtm.member_id
                WHERE vtm.ved_owner_id = :ved_owner_id
                    AND vtm.ved_head_id = :ved_member_id
                    AND vtm.is_active = TRUE
                    AND u.activation_date IS NOT NULL
                    AND u.activation_date >= :start_date
                    AND u.activation_date <= :end_date
                    AND u.coupon_status IN ('Active', 'Activated', 'Used', 'Platinum')
                    AND u.package_points >= 0.5
                    AND vtm.member_id != :ved_member_id
                ORDER BY vtm.level, vtm.member_id
            """)
            
            result = self.db.execute(ved_team_query, {
                'ved_owner_id': user_id,
                'ved_member_id': ved_member.id,
                'start_date': start_date,
                'end_date': end_date
            })
            
            users_under_ved = result.fetchall()
            
            for row in users_under_ved:
                # Use package_points directly (1.0 = Platinum, 0.5 = Diamond)
                ved_income_amount = Decimal(str(get_ved_income(row.package_points)))
                
                if ved_income_amount > 0:
                    total_ved_income += ved_income_amount
                    activations_detail.append({
                        "user_id": row.user_id,
                        "user_name": row.name,
                        "ved_member_id": ved_member.id,
                        "ved_member_name": ved_member.name,
                        "package_points": float(row.package_points),
                        "ved_income": float(ved_income_amount),
                        "activation_date": row.activation_date.isoformat() if row.activation_date else None
                    })
        
        return {
            "user_id": user_id,
            "period": month,
            "is_ved_owner": True,
            "ved_amount": float(total_ved_income),
            "ved_members_count": len(ved_members),
            "activations_under_ved": activations_detail,
            "ved_members": [{"id": vm.id, "name": vm.name} for vm in ved_members],
            "eligibility": eligibility
        }
    
    def calculate_guru_dakshina(self, user_id: str, month: Optional[str] = None) -> Dict[str, Any]:
        """
        Calculate Guru Dakshina based on NEW system
        - Sponsor receives 2% of each direct referral's total earnings
        - Same as Flask system - NOT pool-based
        
        Shows all historical data
        """
        from app.constants import INCOME_RATES
        from app.models.transaction import Transaction
        
        if not month:
            month = datetime.now().strftime("%Y-%m")
        
        start_date = datetime.strptime(f"{month}-01", "%Y-%m-%d")
        if month == datetime.now().strftime("%Y-%m"):
            end_date = datetime.now()
        else:
            next_month = start_date.replace(month=start_date.month + 1 if start_date.month < 12 else 1,
                                          year=start_date.year if start_date.month < 12 else start_date.year + 1)
            end_date = next_month - timedelta(days=1)
        
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return {"error": "User not found"}
        
        # Get all direct referrals
        direct_referrals = self.db.query(User).filter(User.referrer_id == user_id).all()
        
        if not direct_referrals:
            return {
                "user_id": user_id,
                "period": month,
                "guru_dakshina_amount": 0.0,
                "direct_referrals_count": 0,
                "referrals_earnings": []
            }
        
        # Calculate 2% of each direct referral's earnings
        guru_dakshina_rate = Decimal(str(INCOME_RATES['guru_dakshina_percentage'] / 100))
        total_guru_dakshina = Decimal('0.00')
        referrals_earnings_detail = []
        
        for referral in direct_referrals:
            # Get total earnings of this referral in the period
            referral_earnings = self.db.query(func.sum(Transaction.amount)).filter(
                and_(
                    Transaction.referrer_id == referral.id,
                    Transaction.transaction_type.in_([
                        'Direct Referral', 'Matching Referral', 'Ved Income', 'Field Allowance'
                    ]),
                    Transaction.timestamp >= start_date,
                    Transaction.timestamp <= end_date
                )
            ).scalar() or Decimal('0.00')
            
            if referral_earnings > 0:
                guru_dakshina_from_referral = referral_earnings * guru_dakshina_rate
                total_guru_dakshina += guru_dakshina_from_referral
                
                referrals_earnings_detail.append({
                    "user_id": referral.id,
                    "user_name": referral.name,
                    "total_earnings": float(referral_earnings),
                    "guru_dakshina_2_percent": float(guru_dakshina_from_referral)
                })
        
        return {
            "user_id": user_id,
            "period": month,
            "guru_dakshina_amount": float(total_guru_dakshina),
            "direct_referrals_count": len(direct_referrals),
            "referrals_earnings": referrals_earnings_detail,
            "guru_dakshina_rate": "2%"
        }
    
    def get_comprehensive_income_summary(self, user_id: str, month: Optional[str] = None) -> Dict[str, Any]:
        """
        Get comprehensive income summary for all four income streams
        Preserves Flask comprehensive income calculation
        """
        direct_income = self.calculate_direct_referral_income(user_id, month)
        matching_income = self.calculate_matching_referral_income(user_id, month)
        ved_income = self.calculate_ved_income(user_id, month)
        guru_dakshina = self.calculate_guru_dakshina(user_id, month)
        
        total_income = (
            direct_income.get("total_income", 0) +
            matching_income.get("total_income", 0) +
            ved_income.get("ved_amount", 0) +
            guru_dakshina.get("guru_dakshina_amount", 0)
        )
        
        return {
            "user_id": user_id,
            "period": month or datetime.now().strftime("%Y-%m"),
            "income_streams": {
                "direct_referral": direct_income,
                "matching_referral": matching_income, 
                "ved_income": ved_income,
                "guru_dakshina": guru_dakshina
            },
            "total_monthly_income": total_income,
            "generated_at": get_indian_time().isoformat()
        }
    
    def get_user_team(self, user_id: str) -> Dict[str, Any]:
        """
        Get user's team members (direct referrals)
        """
        from app.models.user import User
        
        # Get direct referrals
        direct_referrals = self.db.query(User).filter(
            User.referrer_id == user_id
        ).all()
        
        # Format team data
        team_members = []
        for member in direct_referrals:
            team_members.append({
                "id": member.id,
                "mnr_id": member.id,
                "name": member.name,
                "first_name": member.name.split()[0] if member.name else "",
                "last_name": " ".join(member.name.split()[1:]) if member.name and len(member.name.split()) > 1 else "",
                "email": member.email,
                "mobile": member.phone_number,
                "package_type": member.get_package_type() if hasattr(member, 'get_package_type') else 'None',
                "is_active": member.coupon_status in ['Active', 'Activated'] if member.coupon_status else False,
                "registration_date": member.registration_date.isoformat() if member.registration_date else None,
                "is_ved_member": member.is_ved if hasattr(member, 'is_ved') else False
            })
        
        return {
            "user_id": user_id,
            "direct_referrals": team_members,
            "total_count": len(team_members)
        }