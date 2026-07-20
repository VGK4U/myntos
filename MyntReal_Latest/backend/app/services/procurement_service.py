"""
RVZ Supreme Procurement Service
Consolidated service for Awards and Bonanza procurement workflows
Eliminates 300+ lines of duplicate code
"""

from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Dict, Any, Optional
from decimal import Decimal
from datetime import datetime

from app.models.awards import UserAwardProgress, UserMatchingAwardProgress, DirectAwardTier, MatchingAwardTier
from app.models.bonanza import Bonanza, DynamicBonanzaHistory, DynamicBonanza  # DC Protocol: BonanzaProgress removed
from app.models.transaction import Expense
from app.models.user import User
from app.core.audit import AuditLogger
from app.models.base import get_indian_time


class ProcurementService:
    """
    Unified procurement service for Awards and Bonanza
    Handles: Queue viewing, Purchase processing, Delivery tracking, Expense creation
    """
    
    @staticmethod
    def get_procurement_queue(
        db: Session,
        item_type: str,  # 'award' or 'bonanza'
        status_filter: str = 'pending_purchase',
        award_type: Optional[str] = None  # Only for awards: 'direct' or 'matching'
    ) -> Dict[str, Any]:
        """
        Get procurement queue for awards or bonanza
        
        Args:
            db: Database session
            item_type: 'award' or 'bonanza'
            status_filter: 'pending_purchase', 'pending_delivery', or 'all'
            award_type: For awards only - 'direct', 'matching', or None for all
        
        Returns:
            Dict with items list and statistics
        """
        
        if item_type == 'award':
            return ProcurementService._get_awards_queue(db, status_filter, award_type)
        elif item_type == 'bonanza':
            return ProcurementService._get_bonanza_queue(db, status_filter)
        else:
            raise ValueError(f"Invalid item_type: {item_type}")
    
    @staticmethod
    def _get_awards_queue(
        db: Session,
        status_filter: str,
        award_type: Optional[str]
    ) -> Dict[str, Any]:
        """Get awards procurement queue"""
        items = []
        
        # Query direct awards if needed
        if not award_type or award_type == 'direct' or award_type == 'all':
            query = db.query(UserAwardProgress, DirectAwardTier, User).join(
                DirectAwardTier, UserAwardProgress.award_tier_id == DirectAwardTier.id
            ).join(
                User, UserAwardProgress.user_id == User.id
            )
            
            query = ProcurementService._apply_status_filter(query, status_filter, UserAwardProgress)
            
            for progress, tier, user in query.all():
                items.append(ProcurementService._format_award_item(
                    progress, tier, user, 'direct'
                ))
        
        # Query matching awards if needed
        if not award_type or award_type == 'matching' or award_type == 'all':
            query = db.query(UserMatchingAwardProgress, MatchingAwardTier, User).join(
                MatchingAwardTier, UserMatchingAwardProgress.matching_award_tier_id == MatchingAwardTier.id
            ).join(
                User, UserMatchingAwardProgress.user_id == User.id
            )
            
            query = ProcurementService._apply_status_filter(query, status_filter, UserMatchingAwardProgress)
            
            for progress, tier, user in query.all():
                items.append(ProcurementService._format_award_item(
                    progress, tier, user, 'matching'
                ))
        
        return ProcurementService._calculate_statistics(items)
    
    @staticmethod
    def _get_bonanza_queue(db: Session, status_filter: str) -> Dict[str, Any]:
        """
        DC Protocol: Get bonanza procurement queue from DynamicBonanzaHistory ONLY
        Legacy BonanzaProgress table deprecated - removed from queue
        """
        items = []
        
        # DC PROTOCOL FIX (Nov 10, 2025): Use processed_status for filtering (single source of truth)
        # REMOVED: Obsolete rvz_approval_status and procurement_status filtering
        # MNR 2.0 BONANZA SYSTEM - Uses same _apply_status_filter as direct/matching awards
        mnr2_query = db.query(DynamicBonanzaHistory, DynamicBonanza, User).join(
            DynamicBonanza, DynamicBonanzaHistory.bonanza_id == DynamicBonanza.id
        ).join(
            User, DynamicBonanzaHistory.user_id == User.id
        )
        
        # DC PROTOCOL: Apply unified status filtering using processed_status field
        # Reuses same helper function as direct/matching awards for consistency
        mnr2_query = ProcurementService._apply_status_filter(mnr2_query, status_filter, DynamicBonanzaHistory)
        
        for history, bonanza, user in mnr2_query.all():
            items.append(ProcurementService._format_mnr2_bonanza_item(history, bonanza, user))
        
        return ProcurementService._calculate_statistics(items)
    
    @staticmethod
    def _apply_status_filter(query, status_filter: str, ProgressModel):
        """Apply status filter to query - DC Protocol: Use unified status values"""
        if status_filter == 'pending_purchase':
            query = query.filter(ProgressModel.processed_status == 'Procurement Pending')
        elif status_filter == 'pending_delivery':
            query = query.filter(ProgressModel.processed_status == 'Processed for Dispatch')
        elif status_filter == 'delivered':
            query = query.filter(ProgressModel.processed_status == 'Delivered')
        else:  # all - show everything including delivered items
            query = query.filter(ProgressModel.processed_status.in_([
                'Procurement Pending', 
                'Processed for Dispatch',
                'Delivered'
            ]))
        
        return query
    
    @staticmethod
    def _format_award_item(progress, tier, user, award_type: str) -> Dict[str, Any]:
        """Format award item for response"""
        
        # DC PROTOCOL: Dynamic budget from config until paid (single source of truth)
        live_budget = float(tier.actual_price) if tier and tier.actual_price else 0
        
        return {
            'id': progress.id,
            'type': award_type,
            'user_id': user.id,
            'user_name': user.name,
            'award_name': tier.award_name,
            # DC PROTOCOL: Always read from tier.actual_price config (live values)
            'budgeted_amount': live_budget,
            'actual_cost_paid': float(progress.actual_cost_paid) if progress.actual_cost_paid else None,
            'cost_variance': (live_budget - float(progress.actual_cost_paid)) if progress.actual_cost_paid else None,
            'vendor_name': progress.vendor_name,
            'payment_mode': progress.payment_mode,
            'payment_reference': progress.payment_reference,
            'processed_status': progress.processed_status,
            'achieved_at': progress.achieved_at.isoformat() if hasattr(progress, 'achieved_at') and progress.achieved_at else (progress.achievement_date.isoformat() if hasattr(progress, 'achievement_date') and progress.achievement_date else None),
            'finance_processed_at': progress.finance_processed_at.isoformat() if progress.finance_processed_at else None,
            'delivered_at': progress.delivered_at.isoformat() if hasattr(progress, 'delivered_at') and progress.delivered_at else None
        }
    
    @staticmethod
    def _format_bonanza_item(progress, bonanza, user, system_type='old_system') -> Dict[str, Any]:
        """Format old bonanza system item for response"""
        
        return {
            'id': progress.id,
            'type': 'bonanza',  # Award type for consistency with awards
            'system': system_type,  # 'old_system' for bonanza_progress table
            'user_id': user.id,
            'user_name': user.name,
            'bonanza_name': bonanza.name,
            'budgeted_amount': float(progress.budgeted_amount) if progress.budgeted_amount else 0,
            'actual_cost_paid': float(progress.actual_cost_paid) if progress.actual_cost_paid else None,
            'cost_variance': float(progress.cost_variance) if progress.cost_variance else None,
            'vendor_name': progress.vendor_name,
            'payment_mode': progress.payment_mode,
            'payment_reference': progress.payment_reference,
            'processed_status': progress.processed_status,
            'achieved_date': progress.achieved_date.isoformat() if hasattr(progress, 'achieved_date') and progress.achieved_date else None,
            'finance_processed_at': progress.finance_processed_at.isoformat() if progress.finance_processed_at else None,
            'delivered_at': progress.delivered_at.isoformat() if hasattr(progress, 'delivered_at') and progress.delivered_at else None
        }
    
    @staticmethod
    def _format_mnr2_bonanza_item(history, bonanza, user) -> Dict[str, Any]:
        """Format MNR bonanza item for response"""
        
        # DC PROTOCOL FIX (Nov 10, 2025): Read processed_status directly from database
        # REMOVED: 17 lines of fake status generation from obsolete rvz_approval_status/procurement_status fields
        # Single source of truth: history.processed_status (matches Gift-Wise Status and RVZ Approval Queue)
        processed_status = history.processed_status or 'Unknown'
        
        # DC PROTOCOL: Dynamic budget from config until paid (single source of truth)
        live_budget = float(bonanza.actual_price) if bonanza and bonanza.actual_price else 0
        
        return {
            'id': history.id,
            'type': 'bonanza_mnr2',  # Distinguish MNR bonanza from old system
            'system': 'mnr2',  # 'mnr2' for dynamic_bonanza_history table
            'user_id': user.id,
            'user_name': user.name,
            'bonanza_name': history.award_name or bonanza.bonanza_name,
            # DC PROTOCOL: Always read from bonanza.actual_price config (live values)
            'budgeted_amount': live_budget,
            'actual_cost_paid': float(history.actual_cost_paid) if history.actual_cost_paid else None,
            'cost_variance': (live_budget - float(history.actual_cost_paid)) if history.actual_cost_paid else None,
            'cost_variance_reason': history.cost_variance_reason,
            'vendor_name': history.vendor_name,
            'payment_mode': history.payment_mode,
            'payment_reference': history.payment_reference,
            'processed_status': processed_status,
            'rvz_approval_status': history.rvz_approval_status,
            'procurement_status': history.procurement_status,
            'claimed_at': history.claimed_at.isoformat() if history.claimed_at else None,
            'achieved_date': history.claimed_at.isoformat() if history.claimed_at else None,  # Use claimed_at as achieved_date
            'finance_processed_at': history.finance_processed_at.isoformat() if history.finance_processed_at else None,
            'delivered_at': history.delivered_at.isoformat() if history.delivered_at else None,
            'deduction_amount_direct': history.deduction_amount_direct  # For breakdown feature
        }
    
    
    @staticmethod
    def _calculate_statistics(items: List[Dict]) -> Dict[str, Any]:
        """Calculate procurement statistics"""
        total_budgeted = sum(item['budgeted_amount'] for item in items)
        total_spent = sum(item['actual_cost_paid'] for item in items if item['actual_cost_paid'])
        
        pending_purchase_count = sum(
            1 for item in items 
            if item['processed_status'] == 'Procurement Pending'
        )
        
        pending_delivery_count = sum(
            1 for item in items 
            if item['processed_status'] == 'Processed for Dispatch'
        )
        
        delivered_count = sum(
            1 for item in items 
            if item['processed_status'] == 'Delivered'
        )
        
        return {
            'items': items,
            'total_count': len(items),
            'total_budgeted': total_budgeted,
            'total_spent': total_spent,
            'pending_purchase_count': pending_purchase_count,
            'pending_delivery_count': pending_delivery_count,
            'delivered_count': delivered_count
        }
    
    @staticmethod
    def purchase_item(
        db: Session,
        item_id: int,
        item_type: str,  # 'direct', 'matching', or 'bonanza'
        vendor_name: str,
        actual_cost_paid: Decimal,
        payment_mode: str,
        payment_reference: Optional[str],
        cost_variance_reason: Optional[str],
        current_user: User
    ) -> Dict[str, Any]:
        """
        Purchase an award or bonanza
        
        Returns:
            Dict with purchase details and expense ID
        """
        
        # Get progress record
        progress = ProcurementService._get_progress_record(db, item_id, item_type)
        
        if not progress:
            raise ValueError(f"Item not found: {item_type} ID {item_id}")
        
        # Verify item is ready for purchase - DC Protocol
        if progress.processed_status != 'Procurement Pending':
            raise ValueError(f"Item must be RVZ Approved. Current status: {progress.processed_status}")
        
        # Calculate cost variance
        budgeted = Decimal(str(progress.budgeted_amount or 0))
        actual = Decimal(str(actual_cost_paid))
        progress.actual_cost_paid = actual
        progress.cost_variance = budgeted - actual
        progress.cost_variance_reason = cost_variance_reason
        
        # Update procurement fields
        progress.vendor_name = vendor_name
        progress.payment_mode = payment_mode
        progress.payment_reference = payment_reference
        from app.models.staff import StaffEmployee
        progress.finance_processed_by = str(current_user.emp_code or current_user.id) if isinstance(current_user, StaffEmployee) else str(current_user.id)
        progress.finance_processed_at = get_indian_time()
        progress.payment_status = 'released'
        progress.processed_status = 'Processed for Dispatch'  # DC Protocol status
        
        # DC PROTOCOL: Update procurement_status for bonanza items (DynamicBonanzaHistory)
        if item_type == 'bonanza_mnr2' and hasattr(progress, 'procurement_status'):
            progress.procurement_status = 'Purchased - Pending Delivery'
        
        # Create expense record
        expense = ProcurementService._create_expense_record(
            db=db,
            item_id=item_id,
            item_type=item_type,
            amount=actual,
            vendor_name=vendor_name,
            payment_mode=payment_mode,
            payment_reference=payment_reference,
            current_user=current_user
        )
        
        db.commit()
        
        # Audit log
        AuditLogger.log_action(
            db=db,
            user=current_user,
            action=f"RVZ_SUPREME_{item_type.upper()}_PURCHASE",
            resource_type=item_type.capitalize(),
            resource_id=str(item_id),
            details={
                "actual_cost": float(actual),
                "budgeted": float(budgeted),
                "variance": float(progress.cost_variance),
                "expense_id": expense.id
            }
        )
        
        return {
            "award_id" if 'award' in item_type else "bonanza_progress_id": item_id,
            "expense_id": expense.id,
            "actual_cost": float(actual),
            "variance": float(progress.cost_variance)
        }
    
    @staticmethod
    def deliver_item(
        db: Session,
        item_id: int,
        item_type: str,  # 'direct', 'matching', or 'bonanza'
        delivery_notes: Optional[str],
        current_user: User
    ) -> Dict[str, Any]:
        """
        Mark award or bonanza as delivered
        
        Returns:
            Dict with delivery details
        """
        
        # Get progress record
        progress = ProcurementService._get_progress_record(db, item_id, item_type)
        
        if not progress:
            raise ValueError(f"Item not found: {item_type} ID {item_id}")
        
        if not progress.finance_processed_by:
            raise ValueError("Item must be purchased first")
        
        # Mark as delivered - DC Protocol
        from app.models.staff import StaffEmployee
        progress.delivered_by = str(current_user.emp_code or current_user.id) if isinstance(current_user, StaffEmployee) else str(current_user.id)
        progress.delivered_at = get_indian_time()
        progress.user_acknowledgment = True
        progress.reward_given = True
        progress.reward_given_date = get_indian_time()
        progress.processed_status = 'Delivered'  # DC Protocol status
        
        # DC PROTOCOL: Update procurement_status for bonanza items (DynamicBonanzaHistory)
        if hasattr(progress, 'procurement_status'):
            progress.procurement_status = 'Delivered'
        
        # Add delivery notes
        if delivery_notes:
            if progress.admin_notes:
                progress.admin_notes += f"\n[RVZ DELIVERY] {delivery_notes}"
            else:
                progress.admin_notes = f"[RVZ DELIVERY] {delivery_notes}"
        
        db.commit()
        
        # Audit log
        AuditLogger.log_action(
            db=db,
            user=current_user,
            action=f"RVZ_SUPREME_{item_type.upper()}_DELIVERY",
            resource_type=item_type.capitalize(),
            resource_id=str(item_id),
            details={
                "user_id": progress.user_id,
                "notes": delivery_notes
            }
        )
        
        return {
            "award_id" if 'award' in item_type else "bonanza_progress_id": item_id,
            "delivered_at": progress.delivered_at.isoformat()
        }
    
    @staticmethod
    def _get_progress_record(db: Session, item_id: int, item_type: str):
        """Get progress record based on item type"""
        if item_type == 'direct':
            return db.query(UserAwardProgress).filter(UserAwardProgress.id == item_id).first()
        elif item_type == 'matching':
            return db.query(UserMatchingAwardProgress).filter(UserMatchingAwardProgress.id == item_id).first()
        elif item_type == 'bonanza':
            # DC Protocol: Use DynamicBonanzaHistory (single source of truth)
            from app.models.bonanza import DynamicBonanzaHistory
            return db.query(DynamicBonanzaHistory).filter(DynamicBonanzaHistory.id == item_id).first()
        else:
            raise ValueError(f"Invalid item_type: {item_type}")
    
    @staticmethod
    def _create_expense_record(
        db: Session,
        item_id: int,
        item_type: str,
        amount: Decimal,
        vendor_name: str,
        payment_mode: str,
        payment_reference: Optional[str],
        current_user: User
    ) -> Expense:
        """Create expense record for procurement"""
        
        expense = Expense(
            expense_date=get_indian_time().date(),
            amount=amount,
            category='Award',  # Using 'Award' category per database constraint
            description=f"RVZ Supreme: {item_type.capitalize()} procurement for item #{item_id}",
            vendor=vendor_name,
            payment_mode=payment_mode,
            reference_no=payment_reference,
            award_reference_id=item_id if 'award' in item_type else None,
            award_reference_type=item_type.capitalize() if 'award' in item_type else None,
            bonanza_reference_id=item_id if item_type == 'bonanza' else None,
            bonanza_reference_type='Bonanza Claim' if item_type == 'bonanza' else None,
            created_by_id=str(current_user.emp_code or current_user.id) if isinstance(current_user, StaffEmployee) else str(current_user.id),
            status='approved',
            approved_by_id=str(current_user.emp_code or current_user.id) if isinstance(current_user, StaffEmployee) else str(current_user.id),
            approved_at=get_indian_time()
        )
        
        db.add(expense)
        return expense
