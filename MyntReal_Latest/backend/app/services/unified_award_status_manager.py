"""
DC Protocol: Unified Award Status Manager
Single source of truth for ALL award status management across Direct, Matching, and Bonanza awards

This service ensures:
1. Consistent status transitions across all award types
2. Automatic audit trail for all status changes
3. Delivery tracking auto-calculates processed_status
4. Prevention of invalid status transitions
5. Zero data duplication or inconsistency

Author: MNR Development Team
Created: Nov 9, 2025
"""

import logging
from typing import Dict, Any, Optional, Tuple
from datetime import date, datetime
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.models.user import User
from app.models.awards import UserAwardProgress, UserMatchingAwardProgress, AwardAuditLog
from app.models.bonanza import DynamicBonanzaHistory
from app.constants.award_statuses import AwardStatus, normalize_status
from app.models.base import get_indian_time

logger = logging.getLogger(__name__)


class UnifiedAwardStatusManager:
    """
    DC Protocol: Unified status manager for all award types
    
    Handles status transitions for:
    - Direct Awards (UserAwardProgress)
    - Matching Awards (UserMatchingAwardProgress)
    - Bonanza Awards (DynamicBonanzaHistory)
    
    All status updates must go through this manager to ensure consistency.
    """
    
    # DC Protocol: Valid status transitions
    # Workflow: Pending Approval → Admin Approved (Finance) → Procurement Pending (RVZ) → Dispatch → Delivered
    # RVZ Supreme Override: Pending Approval → Procurement Pending (skips Finance step)
    STATUS_TRANSITIONS = {
        AwardStatus.PENDING_APPROVAL: [
            AwardStatus.ADMIN_APPROVED,  # Finance Admin approves
            AwardStatus.PROCUREMENT_PENDING,  # RVZ Supreme direct approval (skips Finance)
            AwardStatus.REJECTED,
            AwardStatus.RETURNED_FOR_CORRECTION
        ],
        AwardStatus.ADMIN_APPROVED: [  # Finance Approved
            AwardStatus.PROCUREMENT_PENDING,  # RVZ approves after Finance
            AwardStatus.REJECTED,
            AwardStatus.RETURNED_FOR_CORRECTION
        ],
        AwardStatus.PROCUREMENT_PENDING: [  # RVZ Approved
            AwardStatus.PROCESSED_FOR_DISPATCH,  # Procurement recorded
            AwardStatus.REJECTED,
            AwardStatus.RETURNED_FOR_CORRECTION
        ],
        AwardStatus.PROCESSED_FOR_DISPATCH: [
            AwardStatus.DELIVERED,  # Mark as delivered
            AwardStatus.PROCUREMENT_PENDING  # Revert to procurement if needed
        ],
        AwardStatus.DELIVERED: [
            AwardStatus.PROCUREMENT_PENDING  # Revert if delivery was incorrect
        ],
        AwardStatus.REJECTED: [
            AwardStatus.PENDING_APPROVAL  # Can re-approve rejected awards
        ],
        AwardStatus.RETURNED_FOR_CORRECTION: [
            AwardStatus.PENDING_APPROVAL  # Can re-submit after correction
        ]
    }
    
    def __init__(self, db: Session):
        """Initialize manager with database session"""
        self.db = db
    
    def get_award_model_and_instance(
        self,
        award_id: int,
        award_type: str
    ) -> Tuple[Any, Any]:
        """
        Get the model class and specific award instance
        
        Args:
            award_id: Award ID
            award_type: 'direct', 'matching', or 'bonanza'
        
        Returns:
            Tuple of (model_class, award_instance)
        
        Raises:
            ValueError: If award_type is invalid
            HTTPException: If award not found
        """
        if award_type == 'direct':
            model_class = UserAwardProgress
            award = self.db.query(UserAwardProgress).filter(
                UserAwardProgress.id == award_id
            ).first()
        elif award_type == 'matching':
            model_class = UserMatchingAwardProgress
            award = self.db.query(UserMatchingAwardProgress).filter(
                UserMatchingAwardProgress.id == award_id
            ).first()
        elif award_type == 'bonanza':
            model_class = DynamicBonanzaHistory
            award = self.db.query(DynamicBonanzaHistory).filter(
                DynamicBonanzaHistory.id == award_id
            ).first()
        else:
            raise ValueError(f"Invalid award_type: {award_type}. Must be 'direct', 'matching', or 'bonanza'")
        
        if not award:
            raise ValueError(f"{award_type.capitalize()} award with ID {award_id} not found")
        
        return model_class, award
    
    def can_transition(
        self,
        current_status: str,
        new_status: str,
        allow_rvz_override: bool = False
    ) -> bool:
        """
        Check if status transition is valid
        
        Args:
            current_status: Current award status (will be normalized)
            new_status: Desired new status (will be normalized)
            allow_rvz_override: If True, RVZ can bypass transition rules
        
        Returns:
            True if transition is allowed, False otherwise
        """
        if allow_rvz_override:
            return True
        
        normalized_current = normalize_status(current_status)
        normalized_new = normalize_status(new_status)
        
        if normalized_current == normalized_new:
            return True
        
        allowed_transitions = self.STATUS_TRANSITIONS.get(normalized_current, [])
        return normalized_new in allowed_transitions
    
    def calculate_delivery_status(
        self,
        dispatch_date: Optional[date],
        received_date: Optional[date],
        current_status: str,
        has_changes: bool = True
    ) -> str:
        """
        DC Protocol: Calculate processed_status from delivery tracking
        
        IDEMPOTENT: Only changes status if delivery tracking actually changed
        
        Rules:
        1. If received_date exists → DELIVERED
        2. Elif dispatch_date exists → PROCESSED_FOR_DISPATCH
        3. Else → keep current_status (idempotent - don't downgrade)
        
        Args:
            dispatch_date: Date item was dispatched
            received_date: Date item was received by user
            current_status: Current processed_status (will be normalized)
            has_changes: If False, return current_status unchanged (idempotent)
        
        Returns:
            Calculated status based on delivery tracking
        """
        if not has_changes:
            return normalize_status(current_status)
        
        if received_date:
            return AwardStatus.DELIVERED
        elif dispatch_date:
            return AwardStatus.PROCESSED_FOR_DISPATCH
        else:
            return normalize_status(current_status)
    
    def _create_audit_log(
        self,
        award_id: int,
        award_type: str,
        old_status: str,
        new_status: str,
        changed_by: str,
        change_reason: Optional[str] = None,
        changed_by_role: Optional[str] = None,
        metadata: Optional[Dict] = None
    ):
        """
        Create audit log entry for status change
        
        Args:
            award_id: Award ID
            award_type: 'direct', 'matching', or 'bonanza'
            old_status: Previous status
            new_status: New status
            changed_by: User ID who made the change
            change_reason: Reason for change
            changed_by_role: Role of user making change
            metadata: Additional context data
        """
        try:
            entity_type_map = {
                'direct': 'direct_award',
                'matching': 'matching_award',
                'bonanza': 'bonanza'
            }
            
            log = AwardAuditLog(
                entity_type=entity_type_map.get(award_type, award_type),
                entity_id=award_id,
                action='status_change',
                old_status=old_status,
                new_status=new_status,
                actor_id=changed_by,
                actor_role=changed_by_role or 'system',
                notes=change_reason,
                audit_metadata=metadata,
                timestamp=get_indian_time()
            )
            self.db.add(log)
            logger.info(f"📝 Audit log created: {award_type} award {award_id} | {old_status} → {new_status} | by {changed_by}")
        except Exception as e:
            logger.error(f"❌ Failed to create audit log: {str(e)}")
    
    def update_status(
        self,
        award_id: int,
        award_type: str,
        new_status: str,
        actor_id: str,
        actor_role: str,
        reason: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        skip_transition_validation: bool = False,
        auto_commit: bool = True
    ) -> Dict[str, Any]:
        """
        Update award status with validation and audit trail
        
        Args:
            award_id: Award ID
            award_type: 'direct', 'matching', or 'bonanza'
            new_status: New status to set
            actor_id: User ID making the change
            actor_role: Role of user ('admin', 'rvz', 'finance', 'system')
            reason: Reason for status change
            metadata: Additional context data
            skip_transition_validation: If True, skip transition validation (RVZ override)
            auto_commit: If True, commit changes immediately (default). 
                        Set to False when called within another transaction.
        
        Returns:
            Dict with success status and details
        
        Raises:
            ValueError: If transition is invalid or award not found
        """
        try:
            model_class, award = self.get_award_model_and_instance(award_id, award_type)
            
            old_status = normalize_status(award.processed_status)
            new_status_normalized = normalize_status(new_status)
            
            if old_status == new_status_normalized:
                logger.info(f"ℹ️ Status unchanged for {award_type} award {award_id}: {new_status_normalized}")
                return {
                    'success': True,
                    'award_id': award_id,
                    'award_type': award_type,
                    'old_status': old_status,
                    'new_status': new_status_normalized,
                    'message': 'Status unchanged'
                }
            
            allow_override = (actor_role == 'rvz' or skip_transition_validation)
            
            if not self.can_transition(old_status, new_status_normalized, allow_override):
                error_msg = f"Invalid status transition: {old_status} → {new_status_normalized}"
                logger.error(f"❌ {error_msg} for {award_type} award {award_id}")
                raise ValueError(error_msg)
            
            award.processed_status = new_status_normalized
            
            if actor_role == 'rvz':
                award.rvz_action_by = actor_id
                award.rvz_action_at = get_indian_time()
                award.rvz_action_type = 'status_change'
                if reason:
                    award.rvz_notes = reason
            
            self._create_audit_log(
                award_id=award_id,
                award_type=award_type,
                old_status=old_status,
                new_status=new_status_normalized,
                changed_by=actor_id,
                change_reason=reason,
                changed_by_role=actor_role,
                metadata=metadata
            )
            
            if auto_commit:
                self.db.commit()
                logger.info(f"✅ Status updated (committed) for {award_type} award {award_id}: {old_status} → {new_status_normalized} by {actor_id} ({actor_role})")
            else:
                logger.info(f"✅ Status updated (deferred commit) for {award_type} award {award_id}: {old_status} → {new_status_normalized} by {actor_id} ({actor_role})")
            
            return {
                'success': True,
                'award_id': award_id,
                'award_type': award_type,
                'old_status': old_status,
                'new_status': new_status_normalized,
                'changed_by': actor_id,
                'message': f'Status updated from {old_status} to {new_status_normalized}'
            }
            
        except SQLAlchemyError as e:
            if auto_commit:
                self.db.rollback()
            logger.error(f"❌ Database error updating status: {str(e)}")
            raise
        except Exception as e:
            if auto_commit:
                self.db.rollback()
            logger.error(f"❌ Error updating status: {str(e)}")
            raise
    
    def update_delivery_status(
        self,
        award_id: int,
        award_type: str,
        dispatch_date: Optional[date] = None,
        received_date: Optional[date] = None,
        actor_id: Optional[str] = None,
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        ✅ DC Protocol: Update delivery tracking fields for ALL award types
        
        Works for 'direct', 'matching', AND 'bonanza' awards - all use identical tracking fields:
        - dispatch_date: When item was dispatched
        - received_date: When user received the item
        - delivery_notes: Delivery notes/tracking info
        
        Auto-updates processed_status based on delivery tracking state.
        
        Args:
            award_id: Award ID
            award_type: 'direct', 'matching', or 'bonanza'
            dispatch_date: Date item was dispatched
            received_date: Date item was received
            actor_id: User ID making the update
            notes: Delivery notes
        
        Returns:
            Dict with success status and details
        
        Raises:
            ValueError: If dates are invalid or award not found
        """
        try:
            # ✅ DC Protocol: All award types now support delivery tracking
            model_class, award = self.get_award_model_and_instance(award_id, award_type)
            
            if dispatch_date and received_date and dispatch_date > received_date:
                raise ValueError("Dispatch date cannot be after received date")
            
            old_status = normalize_status(award.processed_status)
            old_dispatch = award.dispatch_date
            old_received = award.received_date
            
            has_changes = False
            
            if dispatch_date is not None and dispatch_date != old_dispatch:
                award.dispatch_date = dispatch_date
                has_changes = True
            if received_date is not None and received_date != old_received:
                award.received_date = received_date
                has_changes = True
            if notes is not None:
                award.delivery_notes = notes
                has_changes = True
            
            new_status = self.calculate_delivery_status(
                award.dispatch_date,
                award.received_date,
                award.processed_status,
                has_changes=has_changes
            )
            
            normalized_old = normalize_status(old_status)
            normalized_new = normalize_status(new_status)
            
            if normalized_new != normalized_old:
                award.processed_status = normalized_new
                
                if normalized_new == AwardStatus.DELIVERED:
                    award.delivered_by = actor_id
                    award.delivered_at = get_indian_time()
                
                audit_reason = []
                if dispatch_date and dispatch_date != old_dispatch:
                    audit_reason.append(f"Dispatch date: {dispatch_date}")
                if received_date and received_date != old_received:
                    audit_reason.append(f"Received date: {received_date}")
                if notes:
                    audit_reason.append(f"Notes: {notes}")
                
                self._create_audit_log(
                    award_id=award_id,
                    award_type=award_type,
                    old_status=normalized_old,
                    new_status=normalized_new,
                    changed_by=actor_id or 'system',
                    change_reason=f"Delivery tracking updated: {'; '.join(audit_reason) if audit_reason else 'Auto-calculated'}",
                    changed_by_role='system',
                    metadata={
                        'dispatch_date': str(dispatch_date) if dispatch_date else None,
                        'received_date': str(received_date) if received_date else None,
                        'notes': notes
                    }
                )
            
            self.db.commit()
            
            logger.info(f"✅ Delivery tracking updated for {award_type} award {award_id}: {normalized_old} → {normalized_new}")
            
            return {
                'success': True,
                'award_id': award_id,
                'award_type': award_type,
                'old_status': normalized_old,
                'new_status': award.processed_status,
                'dispatch_date': award.dispatch_date.isoformat() if award.dispatch_date else None,
                'received_date': award.received_date.isoformat() if award.received_date else None,
                'delivery_notes': award.delivery_notes,
                'message': f'Delivery tracking updated. Status: {award.processed_status}'
            }
            
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"❌ Database error updating delivery status: {str(e)}")
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"❌ Error updating delivery status: {str(e)}")
            raise
    
    # ========== WORKFLOW-SPECIFIC CONVENIENCE METHODS ==========
    # These methods provide simplified interfaces for common admin workflows
    # All funnel through update_status() to ensure DC Protocol compliance
    
    def admin_approve(
        self,
        award_id: int,
        award_type: str,
        admin_id: str,
        notes: Optional[str] = None,
        auto_commit: bool = True
    ) -> Dict[str, Any]:
        """
        Admin approves award (Pending → Admin Approved)
        
        Args:
            award_id: Award ID
            award_type: 'direct', 'matching', or 'bonanza'
            admin_id: Admin user ID
            notes: Optional approval notes
            auto_commit: If True, commit immediately
        
        Returns:
            Dict with success status and details
        """
        model_class, award = self.get_award_model_and_instance(award_id, award_type)
        
        # Update admin approval fields
        award.admin_approved_by = admin_id
        award.admin_approved_at = get_indian_time()
        if notes:
            award.admin_notes = notes
        
        # Update status through unified manager
        return self.update_status(
            award_id=award_id,
            award_type=award_type,
            new_status=AwardStatus.ADMIN_APPROVED,
            actor_id=admin_id,
            actor_role='admin',
            reason=notes or 'Admin approved',
            auto_commit=auto_commit
        )
    
    def reject_award(
        self,
        award_id: int,
        award_type: str,
        actor_id: str,
        actor_role: str,
        reason: Optional[str] = None,
        auto_commit: bool = True
    ) -> Dict[str, Any]:
        """
        Reject award (Any status → Rejected)
        
        Args:
            award_id: Award ID
            award_type: 'direct', 'matching', or 'bonanza'
            actor_id: User ID rejecting
            actor_role: Role ('admin', 'rvz', 'finance')
            reason: Rejection reason
            auto_commit: If True, commit immediately
        
        Returns:
            Dict with success status and details
        """
        model_class, award = self.get_award_model_and_instance(award_id, award_type)
        
        # Update rejection fields based on role
        if actor_role == 'rvz':
            award.rvz_action_by = actor_id
            award.rvz_action_at = get_indian_time()
            award.rvz_action_type = 'rejected'
            if reason:
                award.rvz_notes = reason
        elif actor_role == 'admin':
            if reason:
                award.admin_notes = reason
        
        # Update status through unified manager
        return self.update_status(
            award_id=award_id,
            award_type=award_type,
            new_status=AwardStatus.REJECTED,
            actor_id=actor_id,
            actor_role=actor_role,
            reason=reason or 'Award rejected',
            skip_transition_validation=True,  # Allow rejection from any status
            auto_commit=auto_commit
        )
    
    def rvz_approve(
        self,
        award_id: int,
        award_type: str,
        rvz_id: str,
        notes: Optional[str] = None,
        auto_commit: bool = True
    ) -> Dict[str, Any]:
        """
        RVZ approves award (Admin Approved → Procurement Pending)
        
        Args:
            award_id: Award ID
            award_type: 'direct', 'matching', or 'bonanza'
            rvz_id: RVZ user ID
            notes: Optional RVZ notes
            auto_commit: If True, commit immediately
        
        Returns:
            Dict with success status and details
        """
        model_class, award = self.get_award_model_and_instance(award_id, award_type)
        
        # Update RVZ approval fields
        award.rvz_action_by = rvz_id
        award.rvz_action_at = get_indian_time()
        award.rvz_action_type = 'approved'
        if notes:
            award.rvz_notes = notes
        
        # Update status through unified manager
        return self.update_status(
            award_id=award_id,
            award_type=award_type,
            new_status=AwardStatus.PROCUREMENT_PENDING,
            actor_id=rvz_id,
            actor_role='rvz',
            reason=notes or 'RVZ approved',
            auto_commit=auto_commit
        )
    
    def finance_process(
        self,
        award_id: int,
        award_type: str,
        finance_id: str,
        notes: Optional[str] = None,
        auto_commit: bool = True
    ) -> Dict[str, Any]:
        """
        Finance processes award (Procurement Pending → Processed for Dispatch)
        
        Args:
            award_id: Award ID
            award_type: 'direct', 'matching', or 'bonanza'
            finance_id: Finance admin user ID
            notes: Optional processing notes
            auto_commit: If True, commit immediately
        
        Returns:
            Dict with success status and details
        """
        model_class, award = self.get_award_model_and_instance(award_id, award_type)
        
        # Update finance processing fields
        award.finance_processed_by = finance_id
        award.finance_processed_at = get_indian_time()
        if notes:
            award.finance_notes = notes
        
        # Update status through unified manager
        return self.update_status(
            award_id=award_id,
            award_type=award_type,
            new_status=AwardStatus.PROCESSED_FOR_DISPATCH,
            actor_id=finance_id,
            actor_role='finance',
            reason=notes or 'Finance processed',
            auto_commit=auto_commit
        )
    
    def bulk_update_status(
        self,
        award_ids: list,
        award_type: str,
        new_status: str,
        actor_id: str,
        actor_role: str,
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Bulk update status for multiple awards
        
        Args:
            award_ids: List of award IDs
            award_type: 'direct', 'matching', or 'bonanza'
            new_status: New status to set
            actor_id: User ID making the change
            actor_role: Role of user
            reason: Reason for bulk update
        
        Returns:
            Dict with success/failure counts
        """
        results = {
            'success_count': 0,
            'failed_count': 0,
            'failures': []
        }
        
        for award_id in award_ids:
            try:
                self.update_status(
                    award_id=award_id,
                    award_type=award_type,
                    new_status=new_status,
                    actor_id=actor_id,
                    actor_role=actor_role,
                    reason=reason,
                    auto_commit=False  # Defer commits for performance
                )
                results['success_count'] += 1
            except Exception as e:
                results['failed_count'] += 1
                results['failures'].append({
                    'award_id': award_id,
                    'error': str(e)
                })
                logger.error(f"❌ Bulk update failed for {award_type} award {award_id}: {str(e)}")
        
        # Commit all changes at once
        try:
            self.db.commit()
            logger.info(f"✅ Bulk update committed: {results['success_count']} awards updated")
        except Exception as e:
            self.db.rollback()
            logger.error(f"❌ Bulk update commit failed: {str(e)}")
            raise
        
        return results
