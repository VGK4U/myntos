"""
Bonanza Service Module - DC Protocol Schema Translation & Business Logic

Centralizes BonanzaProgress→DynamicBonanzaHistory migration logic with:
- Stateless schema mappers for OLD→NEW field translation
- Business logic for bonanza claim/approval workflows
- Prevents circular dependencies by keeping ORM logic separate from API routers
"""

from typing import Dict, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.bonanza import Bonanza, DynamicBonanzaHistory
from app.models.user import User


class BonanzaStatusMapper:
    """
    Stateless helper class for schema translation between legacy BonanzaProgress
    and new DynamicBonanzaHistory table structures (DC Protocol compliance).
    """
    
    @staticmethod
    def achievement_to_processed(achievement_status: str, has_claimed: bool = False) -> Optional[str]:
        """
        Map OLD achievement_status → NEW processed_status
        
        OLD Values (bonanza_progress):
        - 'In Progress' → Not in NEW table (user hasn't claimed yet)
        - 'Achieved' → 'Achieved - Pending Admin' (achieved but not claimed) OR 'Pending' (if claimed)
        - 'Claimed' → 'Pending' (user claimed, awaiting admin approval)
        
        NEW Values (dynamic_bonanza_history) - Full DC Protocol list:
        - 'Pending' → Awaiting admin approval (user claimed)
        - 'Achieved - Pending Admin' → User achieved but hasn't claimed yet
        - 'Admin Approved' → Admin approved, awaiting Super Admin/RVZ decision
        - 'Super Admin Approved' → Super Admin approved, ready for procurement
        - 'Procurement Pending' → RVZ approved, ready for finance processing
        - 'Processed for Dispatch' → Payment processed, ready for delivery
        - 'Rejected' → Rejected by admin/Super Admin/RVZ
        - 'Purchased - Pending Delivery' → Procured, awaiting delivery
        - 'Delivered - Completed' → Delivered to user
        """
        # Preserve distinction between achieved vs claimed
        if achievement_status == 'Achieved':
            return 'Pending' if has_claimed else 'Achieved - Pending Admin'
        
        mapping = {
            'In Progress': None,  # Not claimed yet - no record in NEW table
            'Claimed': 'Pending',  # User claimed reward
            'Pending': 'Pending',
            'Approved': 'Admin Approved',
            'Processed': 'Processed for Dispatch',  # CRITICAL: Already finance-cleared, not pre-finance!
            'Rejected': 'Rejected',
            'Achieved - Pending Admin': 'Achieved - Pending Admin'
        }
        return mapping.get(achievement_status)
    
    @staticmethod
    def processed_to_achievement(processed_status: str) -> str:
        """
        Reverse map NEW processed_status → OLD achievement_status
        (For backward compatibility in UI/responses)
        
        Complete mapping for ALL DC Protocol status values
        Maps to terminal states that UI expects: Achieved, Claimed, Approved, Processed, Completed, Rejected
        """
        mapping = {
            # Pre-claim stages
            'Achieved - Pending Admin': 'Achieved',  # User achieved but hasn't claimed
            
            # Claim & Initial Approval stages  
            'Pending': 'Claimed',  # User claimed, awaiting admin
            'Admin Approved': 'Approved',  # Admin approved
            'Super Admin Approved': 'Approved',  # Super Admin approved
            'Procurement Pending': 'Approved',  # RVZ approved
            'Pending RVZ Approval': 'Approved',  # Awaiting RVZ
            
            # Finance & Procurement stages (terminal state: Processed)
            'Processed for Dispatch': 'Processed',  # ✅ Finance cleared - show as "Processed"
            'Purchased - Pending Delivery': 'Processed',  # Procured, awaiting delivery
            
            # Final Delivery stage (terminal state: Completed)
            'Delivered - Completed': 'Completed',  # ✅ Delivered to user - show as "Completed"
            
            # Rejection states
            'Rejected': 'Rejected',
            'RVZ Rejected': 'Rejected',
            
            # Legacy statuses (preserve exact value)
            'Processed': 'Processed',
            'Approved': 'Approved',
            'Completed': 'Completed'
        }
        return mapping.get(processed_status, 'Claimed')  # Safe fallback
    
    @staticmethod
    def capture_progress_snapshot(
        criteria_type: str,
        direct_progress: int,
        matching_progress: int
    ) -> Dict[str, Optional[int]]:
        """
        Map OLD current_progress → NEW direct_count_achieved/matching_count_achieved
        
        Returns snapshot values to store when creating DynamicBonanzaHistory record
        """
        if criteria_type in ['direct_referrals', 'team_size']:
            return {
                'direct_count_achieved': direct_progress,
                'matching_count_achieved': None
            }
        elif criteria_type == 'matching_points':
            return {
                'direct_count_achieved': None,
                'matching_count_achieved': matching_progress
            }
        else:
            return {
                'direct_count_achieved': None,
                'matching_count_achieved': None
            }
    
    @staticmethod
    def map_claim_timestamps(
        achieved_date: Optional[datetime],
        processed_date: Optional[datetime]
    ) -> Dict[str, Optional[datetime]]:
        """
        Map OLD achieved_date/processed_date → NEW claimed_at/processed_at
        """
        return {
            'claimed_at': achieved_date,  # When user achieved/claimed
            'processed_at': processed_date  # When admin approved
        }


class BonanzaService:
    """
    Business logic service for bonanza operations using DynamicBonanzaHistory
    (DC Protocol - single source of truth)
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_user_claim(self, user_id: str, bonanza_id: int) -> Optional[DynamicBonanzaHistory]:
        """
        Get user's bonanza claim from DynamicBonanzaHistory (NEW table)
        Replaces: db.query(BonanzaProgress).filter(...)
        """
        return self.db.query(DynamicBonanzaHistory).filter(
            DynamicBonanzaHistory.user_id == user_id,
            DynamicBonanzaHistory.bonanza_id == bonanza_id
        ).first()
    
    def get_user_claims(self, user_id: str, include_bonanza: bool = True) -> list:
        """
        Get all bonanza claims for a user
        Replaces: db.query(BonanzaProgress).filter(user_id=...)
        
        Args:
            user_id: User ID to fetch claims for
            include_bonanza: Whether to LEFT JOIN bonanza table (default: True)
                             Note: bonanza_id in dynamic_bonanza_history references bonanza.id
                             but there's NO FK constraint, so we use LEFT JOIN for safety
        """
        query = self.db.query(DynamicBonanzaHistory).filter(
            DynamicBonanzaHistory.user_id == user_id
        )
        
        # Optional LEFT JOIN to bonanza table (safe even if bonanza is deleted)
        if include_bonanza:
            query = query.join(
                Bonanza,
                DynamicBonanzaHistory.bonanza_id == Bonanza.id,
                isouter=True  # LEFT JOIN - handles deleted bonanzas gracefully
            )
        
        return query.all()
    
    def count_claimed_bonanzas(self, bonanza_id: int) -> int:
        """
        Count how many users have claimed a specific bonanza
        Replaces: db.query(BonanzaProgress).filter(achievement_status.in_(['Claimed', 'Achieved']))
        """
        return self.db.query(DynamicBonanzaHistory).filter(
            DynamicBonanzaHistory.bonanza_id == bonanza_id,
            DynamicBonanzaHistory.claimed_at.isnot(None)  # Has been claimed
        ).count()
    
    def has_user_claimed(self, user_id: str, bonanza_id: int) -> bool:
        """
        Check if user has already claimed this bonanza
        """
        claim = self.get_user_claim(user_id, bonanza_id)
        return claim is not None
    
    def get_pending_claims(self) -> list:
        """
        Get all pending claims awaiting admin approval
        Replaces: db.query(BonanzaProgress).filter(processed_status='Pending')
        """
        return self.db.query(DynamicBonanzaHistory).filter(
            DynamicBonanzaHistory.processed_status == 'Pending',
            DynamicBonanzaHistory.admin_approved_at.is_(None)
        ).all()
