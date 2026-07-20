"""
Ved Team Service
Manages Ved Team member tracking using dedicated ved_team_member table
"""

import logging
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional

from app.models.user import User
from app.models.ved_team import VedTeamMember
from app.models.base import get_indian_time

logger = logging.getLogger(__name__)

class VedTeamService:
    """Service for managing Ved Team member tracking"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def sync_ved_team_for_new_placement(self, child_user_id: str, parent_user_id: str, side: str):
        """
        Sync Ved Team after new placement
        
        Called after every placement to update Ved Team membership
        
        Logic:
        1. Check if parent is a Ved member (is_ved=True)
        2. If yes, add child to the same Ved Team
        3. Track placement tree metadata (level, side, parent)
        
        Args:
            child_user_id: ID of newly placed user
            parent_user_id: ID of placement parent
            side: 'LEFT' or 'RIGHT'
        """
        try:
            # Check if parent is in any Ved Team
            parent_ved_membership = self.db.query(VedTeamMember).filter(
                VedTeamMember.member_id == parent_user_id,
                VedTeamMember.is_active == True
            ).first()
            
            if not parent_ved_membership:
                # Parent is NOT in a Ved Team
                # Check if parent IS a Ved Head (is_ved=True)
                parent_user = self.db.query(User).filter(User.id == parent_user_id).first()
                if not parent_user or not parent_user.is_ved:
                    # Parent is neither Ved member nor Ved Head → child not in Ved Team
                    return
                
                # Parent IS a Ved Head → child becomes Level 1 Ved Team member
                if parent_user.ved_owner_id:
                    ved_owner_id = parent_user.ved_owner_id
                    ved_head_id = parent_user_id
                    level = 1
                else:
                    # Parent is Ved Head but ved_owner_id not set (shouldn't happen)
                    logger.warning(f"Ved Head {parent_user_id} has is_ved=True but ved_owner_id is NULL")
                    return
            else:
                # Parent IS in a Ved Team → child inherits Ved Team membership
                ved_owner_id = parent_ved_membership.ved_owner_id
                ved_head_id = parent_ved_membership.ved_head_id
                level = parent_ved_membership.level + 1
            
            # Check if child already in this Ved Team (prevent duplicates)
            existing = self.db.query(VedTeamMember).filter(
                VedTeamMember.ved_owner_id == ved_owner_id,
                VedTeamMember.member_id == child_user_id,
                VedTeamMember.is_active == True
            ).first()
            
            if existing:
                logger.debug(f"Ved Team member already exists: {child_user_id} in {ved_owner_id}'s team")
                return
            
            # Create new Ved Team member record
            new_member = VedTeamMember(
                ved_owner_id=ved_owner_id,
                ved_head_id=ved_head_id,
                member_id=child_user_id,
                level=level,
                parent_id=parent_user_id,
                position=side.upper() if side else None,
                is_active=True,
                joined_date=get_indian_time()
            )
            
            self.db.add(new_member)
            self.db.commit()
            
            logger.info(f"✅ Ved Team synced: {child_user_id} added to {ved_owner_id}'s team (Level {level})")
            
        except Exception as e:
            logger.error(f"Error syncing Ved Team for {child_user_id}: {e}")
            self.db.rollback()
    
    def disconnect_ved_owner_from_previous_teams(self, new_ved_owner_id: str):
        """
        Disconnect user from ALL previous Ved Teams when they become a Ved Owner
        
        NO CASCADING RULE: When user gets 3rd direct referral and becomes Ved Owner,
        they should DISCONNECT from any previous Ved structure they were in.
        Their downline now belongs to THEM, not their old Ved Owner.
        
        Called when user becomes Ved Owner (gets 3rd direct referral)
        
        Args:
            new_ved_owner_id: User ID who just became a Ved Owner
        """
        try:
            # Find all Ved Team memberships where this user is a member
            disconnected_count = self.db.query(VedTeamMember).filter(
                VedTeamMember.member_id == new_ved_owner_id,
                VedTeamMember.is_active == True
            ).update({
                'is_active': False,
                'removed_date': get_indian_time()
            }, synchronize_session=False)
            
            self.db.commit()
            
            if disconnected_count > 0:
                logger.info(f"✅ Ved Disconnect: {new_ved_owner_id} disconnected from {disconnected_count} previous Ved team(s)")
            
            return True
            
        except Exception as e:
            logger.error(f"Error disconnecting Ved Owner {new_ved_owner_id}: {e}")
            self.db.rollback()
            return False
    
    def rebuild_ved_team_for_owner(self, ved_owner_id: str):
        """
        Rebuild Ved Team for a specific owner (used for manual corrections)
        
        Args:
            ved_owner_id: User ID of Ved Owner
        """
        try:
            # Get Ved Owner
            ved_owner = self.db.query(User).filter(User.id == ved_owner_id).first()
            if not ved_owner:
                logger.error(f"Ved Owner not found: {ved_owner_id}")
                return False
            
            # Get 3rd direct referral (Ved Head)
            direct_refs = self.db.query(User).filter(
                User.referrer_id == ved_owner_id
            ).order_by(User.registration_date.asc(), User.id.asc()).all()
            
            if len(direct_refs) < 3:
                logger.warning(f"User {ved_owner_id} has <3 direct referrals, cannot be Ved Owner")
                return False
            
            ved_head = direct_refs[2]
            
            # Deactivate old Ved Team records
            self.db.query(VedTeamMember).filter(
                VedTeamMember.ved_owner_id == ved_owner_id
            ).update({
                'is_active': False,
                'removed_date': get_indian_time()
            })
            
            # Get Ved Team using recursive CTE
            ved_tree_query = text("""
                WITH RECURSIVE ved_downline AS (
                    -- Base: Start from Ved Head's children
                    SELECT 
                        p.child_id as user_id,
                        p.parent_id,
                        p.side,
                        u.is_ved,
                        1 as level
                    FROM placement p
                    INNER JOIN "user" u ON u.id = p.child_id
                    WHERE p.parent_id = :ved_root_id
                    
                    UNION ALL
                    
                    -- Recursive: Stop at other Ved owners (NO CASCADING)
                    SELECT 
                        p.child_id,
                        p.parent_id,
                        p.side,
                        u.is_ved,
                        vd.level + 1
                    FROM ved_downline vd
                    INNER JOIN placement p ON p.parent_id = vd.user_id
                    INNER JOIN "user" u ON u.id = p.child_id
                    WHERE vd.level < 50
                      AND vd.is_ved = FALSE  -- Stop at Ved members
                )
                SELECT user_id, parent_id, side, level
                FROM ved_downline
                ORDER BY level, user_id
            """)
            
            result = self.db.execute(ved_tree_query, {'ved_root_id': str(ved_head.id)})
            ved_team = result.fetchall()
            
            # Create new Ved Team member records
            for member in ved_team:
                new_member = VedTeamMember(
                    ved_owner_id=ved_owner_id,
                    ved_head_id=ved_head.id,
                    member_id=member.user_id,
                    level=member.level,
                    parent_id=member.parent_id,
                    position=member.side.upper() if member.side else None,
                    is_active=True,
                    joined_date=get_indian_time()
                )
                self.db.add(new_member)
            
            self.db.commit()
            
            logger.info(f"✅ Ved Team rebuilt for {ved_owner_id}: {len(ved_team)} members")
            return True
            
        except Exception as e:
            logger.error(f"Error rebuilding Ved Team for {ved_owner_id}: {e}")
            self.db.rollback()
            return False
