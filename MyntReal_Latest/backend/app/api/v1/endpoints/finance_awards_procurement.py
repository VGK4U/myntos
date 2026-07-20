"""
Finance Awards & Bonanza Procurement Endpoints
Follows WV (Withdrawal-Validation) and DC (Data Consistency) Protocols

Finance Admin/RVZ ONLY - Contains full cost data
"""

from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from decimal import Decimal

from app.core.database import get_db
from app.core.rbac import require_finance_admin
from app.models.user import User
from app.models.awards import UserAwardProgress, UserMatchingAwardProgress, DirectAwardTier, MatchingAwardTier
from app.models.bonanza import DynamicBonanza  # DC Protocol: BonanzaProgress deprecated
from app.models.transaction import Expense
from app.models.base import get_indian_time
from app.models.api_response import success_response
from app.core.audit import AuditLogger

router = APIRouter()

# ===== REQUEST/RESPONSE MODELS =====

class AwardPurchaseRequest(BaseModel):
    vendor_name: str
    actual_cost_paid: float
    payment_mode: str  # 'Bank Transfer', 'Cash', 'UPI', 'Cheque', etc.
    payment_reference: Optional[str] = None
    cost_variance_reason: Optional[str] = None

class AwardDeliveryRequest(BaseModel):
    notes: Optional[str] = None


# ===== AWARDS PROCUREMENT ENDPOINTS =====

@router.get("/finance/awards/procurement")
async def get_awards_for_procurement(
    status_filter: Optional[str] = Query('pending_purchase', description="Filter: 'pending_purchase', 'pending_delivery', 'all'"),
    award_type: Optional[str] = Query('all', description="Filter: 'direct', 'matching', 'all'"),
    cost_impact: Optional[str] = Query('all', description="Filter: 'pending', 'incurred', 'completed', 'all'"),
    current_user: User = Depends(require_finance_admin),
    db: Session = Depends(get_db)
):
    """
    Get all awards pending procurement - Finance Admin view with FULL COST DATA
    
    WV Protocol: Shows budgeted_amount, actual_cost_paid, cost_variance
    DC Protocol: Data from user_award_progress and user_matching_award_progress (single source)
    
    Finance/RVZ ONLY - Contains cost data
    """
    try:
        awards_data = []
        
        # Get Direct Awards
        if not award_type or award_type in ['direct', 'all']:
            direct_query = db.query(
                UserAwardProgress,
                DirectAwardTier,
                User
            ).join(
                DirectAwardTier, UserAwardProgress.award_tier_id == DirectAwardTier.id
            ).join(
                User, UserAwardProgress.user_id == User.id
            )
            
            # Apply status filter - DC Protocol: All 6-stage workflow statuses
            if status_filter == 'pending_purchase':
                direct_query = direct_query.filter(UserAwardProgress.processed_status == 'Procurement Pending')
            elif status_filter == 'pending_delivery':
                direct_query = direct_query.filter(UserAwardProgress.processed_status.in_(['Processed for Dispatch', 'Dispatched']))
            elif status_filter != 'all':
                # Default: Show all procurement pipeline statuses (post-RVZ-approval)
                direct_query = direct_query.filter(UserAwardProgress.processed_status.in_([
                    'Procurement Pending', 'Processed for Dispatch', 'Dispatched', 'Delivered'
                ]))
            
            for progress, tier, user in direct_query.all():
                # Calculate cost impact state
                if progress.delivered_at:
                    cost_impact_state = 'completed'
                elif progress.actual_cost_paid:
                    cost_impact_state = 'incurred'
                else:
                    cost_impact_state = 'pending'
                
                # Apply cost impact filter
                if cost_impact != 'all' and cost_impact_state != cost_impact:
                    continue
                
                awards_data.append({
                    'id': progress.id,
                    'type': 'direct',
                    'user_id': user.id,
                    'user_name': user.name,
                    'award_type': 'Direct Award',
                    'award_name': tier.award_name,
                    'progress': f"{progress.current_referrals}/{progress.required_referrals}",
                    'achieved_at': progress.achieved_at.isoformat() if progress.achieved_at else None,
                    # ✅ COST DATA (Finance/RVZ only - WV Protocol)
                    'budgeted_amount': float(progress.budgeted_amount) if progress.budgeted_amount else None,
                    'actual_cost_paid': float(progress.actual_cost_paid) if progress.actual_cost_paid else None,
                    'cost_variance': float(progress.cost_variance) if progress.cost_variance else None,
                    'cost_variance_reason': progress.cost_variance_reason,
                    # DC Protocol: Payment breakdown fields
                    'handling_charges': float(progress.handling_charges) if progress.handling_charges else None,
                    'gst_amount': float(progress.gst_amount) if progress.gst_amount else None,
                    'tax_amount': float(progress.tax_amount) if progress.tax_amount else None,
                    'transport_charges': float(progress.transport_charges) if progress.transport_charges else None,
                    'vendor_name': progress.vendor_name,
                    'payment_mode': progress.payment_mode,
                    'payment_reference': progress.payment_reference,
                    'bill_upload_path': progress.bill_upload_path,
                    # Status tracking
                    'processed_status': progress.processed_status,
                    'cost_impact': cost_impact_state,
                    # Delivery tracking
                    'delivered_at': progress.delivered_at.isoformat() if progress.delivered_at else None,
                    'delivery_proof_path': progress.delivery_proof_path,
                    'user_acknowledgment': progress.user_acknowledgment,
                    # Approval tracking
                    'admin_approved_by': progress.admin_approved_by,
                    'super_admin_decision_by': progress.super_admin_decision_by,
                    'finance_processed_by': progress.finance_processed_by
                })
        
        # Get Matching Awards
        if not award_type or award_type in ['matching', 'all']:
            matching_query = db.query(
                UserMatchingAwardProgress,
                MatchingAwardTier,
                User
            ).join(
                MatchingAwardTier, UserMatchingAwardProgress.matching_award_tier_id == MatchingAwardTier.id
            ).join(
                User, UserMatchingAwardProgress.user_id == User.id
            )
            
            # Apply status filter - DC Protocol: All 6-stage workflow statuses
            if status_filter == 'pending_purchase':
                matching_query = matching_query.filter(UserMatchingAwardProgress.processed_status == 'Procurement Pending')
            elif status_filter == 'pending_delivery':
                matching_query = matching_query.filter(UserMatchingAwardProgress.processed_status.in_(['Processed for Dispatch', 'Dispatched']))
            elif status_filter != 'all':
                # Default: Show all procurement pipeline statuses (post-RVZ-approval)
                matching_query = matching_query.filter(UserMatchingAwardProgress.processed_status.in_([
                    'Procurement Pending', 'Processed for Dispatch', 'Dispatched', 'Delivered'
                ]))
            
            for progress, tier, user in matching_query.all():
                # Calculate cost impact state
                if progress.delivered_at:
                    cost_impact_state = 'completed'
                elif progress.actual_cost_paid:
                    cost_impact_state = 'incurred'
                else:
                    cost_impact_state = 'pending'
                
                # Apply cost impact filter
                if cost_impact != 'all' and cost_impact_state != cost_impact:
                    continue
                
                awards_data.append({
                    'id': progress.id,
                    'type': 'matching',
                    'user_id': user.id,
                    'user_name': user.name,
                    'award_type': 'Matching Award',
                    'award_name': tier.award_name,
                    'progress': f"{progress.current_matches}/{progress.required_matches}",
                    'achieved_at': progress.achievement_date.isoformat() if progress.achievement_date else None,
                    # ✅ COST DATA (Finance/RVZ only - WV Protocol)
                    'budgeted_amount': float(progress.budgeted_amount) if progress.budgeted_amount else None,
                    'actual_cost_paid': float(progress.actual_cost_paid) if progress.actual_cost_paid else None,
                    'cost_variance': float(progress.cost_variance) if progress.cost_variance else None,
                    'cost_variance_reason': progress.cost_variance_reason,
                    # DC Protocol: Payment breakdown fields
                    'handling_charges': float(progress.handling_charges) if progress.handling_charges else None,
                    'gst_amount': float(progress.gst_amount) if progress.gst_amount else None,
                    'tax_amount': float(progress.tax_amount) if progress.tax_amount else None,
                    'transport_charges': float(progress.transport_charges) if progress.transport_charges else None,
                    'vendor_name': progress.vendor_name,
                    'payment_mode': progress.payment_mode,
                    'payment_reference': progress.payment_reference,
                    'bill_upload_path': progress.bill_upload_path,
                    # Status tracking
                    'processed_status': progress.processed_status,
                    'cost_impact': cost_impact_state,
                    # Delivery tracking
                    'delivered_at': progress.delivered_at.isoformat() if progress.delivered_at else None,
                    'delivery_proof_path': progress.delivery_proof_path,
                    'user_acknowledgment': progress.user_acknowledgment,
                    # Approval tracking
                    'admin_approved_by': progress.admin_approved_by,
                    'super_admin_decision_by': progress.super_admin_decision_by,
                    'finance_processed_by': progress.finance_processed_by
                })
        
        # Calculate summary statistics (WV Protocol validation)
        summary = {
            'total_count': len(awards_data),
            'total_budgeted': sum(a['budgeted_amount'] for a in awards_data if a['budgeted_amount']),
            'total_actual_cost': sum(a['actual_cost_paid'] for a in awards_data if a['actual_cost_paid']),
            'total_saved': sum(a['cost_variance'] for a in awards_data if a['cost_variance'] and a['cost_variance'] > 0),
            'total_overspent': sum(abs(a['cost_variance']) for a in awards_data if a['cost_variance'] and a['cost_variance'] < 0),
            'pending_count': sum(1 for a in awards_data if a['cost_impact'] == 'pending'),
            'incurred_count': sum(1 for a in awards_data if a['cost_impact'] == 'incurred'),
            'completed_count': sum(1 for a in awards_data if a['cost_impact'] == 'completed')
        }
        
        return success_response(
            message="Awards procurement list retrieved (Finance view with full cost data - WV Protocol)",
            data={
                'awards': awards_data,
                'summary': summary
            }
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching awards for procurement: {str(e)}"
        )


@router.post("/finance/awards/{award_id}/purchase")
async def record_award_purchase(
    award_id: int,
    award_type: str = Query(..., description="'direct' or 'matching'"),
    purchase_data: AwardPurchaseRequest = ...,
    current_user: User = Depends(require_finance_admin),
    db: Session = Depends(get_db)
):
    """
    Record award purchase by Finance Admin
    
    WV Protocol: actual_cost_paid set at purchase (may differ from budgeted_amount)
    DC Protocol: Creates expense record linked via award_reference_id
    
    Finance/RVZ ONLY
    """
    try:
        # Get the progress record
        if award_type == 'direct':
            progress = db.query(UserAwardProgress).filter(UserAwardProgress.id == award_id).first()
        elif award_type == 'matching':
            progress = db.query(UserMatchingAwardProgress).filter(UserMatchingAwardProgress.id == award_id).first()
        else:
            raise HTTPException(status_code=400, detail="Invalid award_type. Must be 'direct' or 'matching'")
        
        if not progress:
            raise HTTPException(status_code=404, detail="Award progress not found")
        
        # Verify status is RVZ Approved - DC Protocol
        if progress.processed_status != 'Procurement Pending':
            raise HTTPException(
                status_code=400,
                detail=f"Award must be RVZ Approved to purchase. Current status: {progress.processed_status}"
            )
        
        # WV Protocol: Set actual_cost_paid and calculate variance
        budgeted = Decimal(str(progress.budgeted_amount or 0))
        actual = Decimal(str(purchase_data.actual_cost_paid))
        progress.actual_cost_paid = actual
        progress.cost_variance = budgeted - actual  # Positive = saved, Negative = overspent
        progress.cost_variance_reason = purchase_data.cost_variance_reason
        
        # Set procurement fields (DC Protocol: Single source in progress table)
        progress.vendor_name = purchase_data.vendor_name
        progress.payment_mode = purchase_data.payment_mode
        progress.payment_reference = purchase_data.payment_reference
        progress.finance_processed_by = current_user.id
        progress.finance_processed_at = get_indian_time()
        progress.processed_status = 'Processed for Dispatch'  # DC Protocol status
        
        # DC Protocol: Create expense record (linked to award via reference_id)
        # BUG FIX: Database constraint allows 'Award' not 'Awards - Direct'
        expense_category = 'Award'  # Valid category per valid_expense_category constraint
        
        expense = Expense(
            expense_date=get_indian_time().date(),
            amount=actual,
            category=expense_category,
            description=f"Award purchase for user {progress.user_id}",
            vendor=purchase_data.vendor_name,
            payment_mode=purchase_data.payment_mode,
            reference_no=purchase_data.payment_reference,
            award_reference_id=progress.id,
            award_reference_type='Direct Award' if award_type == 'direct' else 'Matching Award',
            created_by_id=current_user.id,
            status='approved',  # Auto-approve since Finance is creating
            approved_by_id=current_user.id,
            approved_at=get_indian_time()
        )
        db.add(expense)
        
        db.commit()
        
        # BUG FIX: Correct AuditLogger.log_action() signature
        AuditLogger.log_action(
            db=db,
            user=current_user,
            action=f"FINANCE_AWARD_PURCHASE",
            resource_type='Award',
            resource_id=str(award_id),
            details={"award_type": award_type, "actual_cost": float(actual), "budgeted": float(budgeted), "variance": float(progress.cost_variance)}
        )
        
        variance_message = f"₹{abs(progress.cost_variance)} {'saved' if progress.cost_variance > 0 else 'overspent'}"
        
        return success_response(
            message=f"Award purchase recorded successfully (WV: {variance_message})",
            data={
                'award_id': progress.id,
                'budgeted_amount': float(budgeted),
                'actual_cost_paid': float(actual),
                'cost_variance': float(progress.cost_variance),
                'variance_percentage': float((progress.cost_variance / budgeted * 100)) if budgeted > 0 else 0,
                'expense_id': expense.id,
                'processed_status': progress.processed_status
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error recording award purchase: {str(e)}"
        )


@router.post("/finance/awards/{award_id}/deliver")
async def record_award_delivery(
    award_id: int,
    award_type: str = Query(..., description="'direct' or 'matching'"),
    delivery_data: AwardDeliveryRequest = ...,
    current_user: User = Depends(require_finance_admin),
    db: Session = Depends(get_db)
):
    """
    Mark award as delivered by Finance Admin
    
    WV Protocol: NO additional deductions at delivery (NET amount already paid)
    DC Protocol: Updates delivery fields in progress table (single source)
    
    Finance/RVZ ONLY
    """
    try:
        # Get the progress record
        if award_type == 'direct':
            progress = db.query(UserAwardProgress).filter(UserAwardProgress.id == award_id).first()
        elif award_type == 'matching':
            progress = db.query(UserMatchingAwardProgress).filter(UserMatchingAwardProgress.id == award_id).first()
        else:
            raise HTTPException(status_code=400, detail="Invalid award_type")
        
        if not progress:
            raise HTTPException(status_code=404, detail="Award progress not found")
        
        # Verify status is Finance Processed - DC Protocol
        if progress.processed_status != 'Processed for Dispatch':
            raise HTTPException(
                status_code=400,
                detail=f"Award must be Finance Processed before delivery. Current status: {progress.processed_status}"
            )
        
        # WV Protocol: NO additional deductions (user receives full item)
        progress.delivered_by = current_user.id
        progress.delivered_at = get_indian_time()
        progress.user_acknowledgment = True  # Assume acknowledged (can be updated later)
        progress.reward_given = True
        progress.reward_given_date = get_indian_time()
        progress.processed_status = 'Delivered'  # DC Protocol status
        
        if delivery_data and delivery_data.notes:
            if progress.notes:
                progress.notes += f"\n[DELIVERY] {delivery_data.notes}"
            else:
                progress.notes = f"[DELIVERY] {delivery_data.notes}"
        
        db.commit()
        
        # BUG FIX: Correct AuditLogger.log_action() signature
        AuditLogger.log_action(
            db=db,
            user=current_user,
            action=f"FINANCE_AWARD_DELIVERY",
            resource_type='Award',
            resource_id=str(award_id),
            details={"award_type": award_type, "user_id": progress.user_id}
        )
        
        return success_response(
            message="Award delivery recorded successfully (WV: User received full item, no additional deductions)",
            data={
                'award_id': progress.id,
                'user_id': progress.user_id,
                'delivered_at': progress.delivered_at.isoformat(),
                'delivered_by': current_user.id,
                'processed_status': progress.processed_status,
                'actual_cost_paid': float(progress.actual_cost_paid) if progress.actual_cost_paid else None
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error recording award delivery: {str(e)}"
        )
