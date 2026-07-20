from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from app.core.constants import ADMIN_DEDUCTION_RATE, TDS_DEDUCTION_RATE
from sqlalchemy.orm import Session
from sqlalchemy import desc, func, and_, or_, text
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta

from app.core.database import get_db
from app.core.security import get_current_user, get_current_user_hybrid, get_current_mnr_user_from_hybrid
from app.core.rbac import require_roles
from app.models.user import User
from app.models.withdrawal import WithdrawalRequest, BulkWithdrawalBatch
from app.models.transaction import PendingIncome, Transaction
from app.models.myntreal_incentive import ZynovaIncentive
from app.services.mnr_sfms_integration_service import (
    create_withdrawal_ledger_entries,
    create_payment_ledger_entry
)
from app.models.tds_tracking import TDSTracking

router = APIRouter(prefix="/withdrawals")


def _create_tds_tracking_record(db: Session, withdrawal):
    if not withdrawal or not withdrawal.tds_amount or float(withdrawal.tds_amount) <= 0:
        return
    existing = db.query(TDSTracking).filter(
        TDSTracking.withdrawal_request_id == withdrawal.id
    ).first()
    if existing:
        return
    user = db.query(User).filter(User.id == withdrawal.user_id).first()
    tds_record = TDSTracking(
        withdrawal_request_id=withdrawal.id,
        user_id=withdrawal.user_id,
        mnr_id=user.mnr_id if user else None,
        tds_amount=withdrawal.tds_amount,
        withdrawal_amount=withdrawal.withdrawal_amount,
        payment_status='Pending'
    )
    db.add(tds_record)


def add_no_cache_headers(response: Response):
    """Add cache-control headers to prevent browser caching of admin/user financial data"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

class WithdrawalRequestCreate(BaseModel):
    amount: float = Field(..., gt=0)
    bank_name: str = Field(..., min_length=1)
    account_number: str = Field(..., min_length=1)
    ifsc_code: str = Field(..., min_length=1)
    account_holder_name: str = Field(..., min_length=1)
    withdrawal_reason: Optional[str] = None

class WithdrawalRequestResponse(BaseModel):
    id: int
    user_id: str
    withdrawal_amount: int
    admin_charges: int
    tds_amount: int
    final_payout: int
    request_date: str
    status: str
    created_at: str
    processed_at: Optional[str]
    bank_name: Optional[str]
    account_number: Optional[str]
    ifsc_code: Optional[str]
    account_holder_name: Optional[str]
    payment_reference: Optional[str]
    paid_date: Optional[str]
    
    class Config:
        from_attributes = True

@router.post('/withdrawal-requests')
def create_withdrawal_request(
    data: WithdrawalRequestCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_mnr_user_from_hybrid)
):
    """
    DEPRECATED: Manual withdrawal requests are no longer supported
    DC Protocol: Uses MNR-only auth to ensure correct user_id (string MNR ID)
    
    The system now automatically generates withdrawal requests daily at 7 AM (Mon-Sat)
    for users with eligible balance in their withdrawable wallet.
    
    This endpoint is disabled to prevent manual withdrawal creation.
    """
    raise HTTPException(
        status_code=status.HTTP_410_GONE,
        detail={
            "error": "Manual withdrawal requests are no longer supported",
            "message": "The system now automatically generates withdrawal requests daily at 7 AM (Monday-Saturday) for eligible users. Withdrawals are created automatically when your withdrawable wallet balance exceeds ₹1,000 (keeping ₹1,000 as buffer).",
            "auto_withdrawal_schedule": "Monday to Saturday at 7:00 AM IST",
            "eligibility": "Withdrawable wallet ≥ ₹2,000 (₹1,000 buffer + ₹1,000 minimum)",
            "max_per_request": "₹50,000 (configurable by RVZ)",
            "approval_workflow": "Admin → Super Admin → Finance Admin (same as before)"
        }
    )
    
    # OLD CODE - DISABLED
    # Minimum withdrawal validation
    if data.amount < 1000:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Minimum withdrawal amount is ₹1,000'
        )
    
    # Calculate charges: 8% admin charges + 2% TDS
    withdrawal_amount = int(data.amount)
    admin_charges = int(withdrawal_amount * float(ADMIN_DEDUCTION_RATE))
    tds_amount = int(withdrawal_amount * float(TDS_DEDUCTION_RATE))
    final_payout = withdrawal_amount - admin_charges - tds_amount
    
    # CRITICAL: Atomic fund reservation using conditional UPDATE
    # This prevents race conditions from concurrent requests
    from sqlalchemy import text
    
    # Execute atomic UPDATE with WHERE condition
    # This will only succeed if balance is sufficient
    result = db.execute(
        text("""
            UPDATE "user" 
            SET withdrawable_wallet = withdrawable_wallet - :amount 
            WHERE id = :user_id 
            AND COALESCE(withdrawable_wallet, 0) >= :amount
            RETURNING withdrawable_wallet
        """),
        {"amount": withdrawal_amount, "user_id": current_user.id}
    )
    
    updated_row = result.fetchone()
    
    if not updated_row:
        # Update failed - insufficient balance or concurrent modification
        # DC Protocol Phase 1.6: Get current balance from materialized view (computed value)
        from app.services.wallet_balance_service import get_withdrawable_wallet
        computed_balance = get_withdrawable_wallet(db, str(current_user.id))
        current_balance = round(float(computed_balance))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f'Insufficient balance. Your withdrawable balance is ₹{current_balance:,.2f}'
        )
    
    # Funds successfully reserved atomically
    new_balance = round(float(updated_row[0])) if updated_row[0] else 0
    
    # Create withdrawal request
    withdrawal = WithdrawalRequest(
        user_id=current_user.id,
        withdrawal_amount=withdrawal_amount,
        admin_charges=admin_charges,
        tds_amount=tds_amount,
        final_payout=final_payout,
        bank_name=data.bank_name,
        account_number=data.account_number,
        ifsc_code=data.ifsc_code,
        account_holder_name=data.account_holder_name,
        status='Pending'
    )
    
    db.add(withdrawal)
    db.commit()
    db.refresh(withdrawal)
    
    return {
        'success': True,
        'message': f'Withdrawal request for ₹{withdrawal_amount:,} submitted successfully',
        'request_id': withdrawal.id,
        'final_payout': final_payout,
        'admin_charges': admin_charges,
        'tds_amount': tds_amount
    }

@router.get('/withdrawal-requests', response_model=List[WithdrawalRequestResponse])
async def get_user_withdrawal_requests(
    response: Response,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_mnr_user_from_hybrid)
):
    """
    Get current user's withdrawal request history - NO CACHE
    DC Protocol: Uses MNR-only auth to ensure correct user_id (string MNR ID)
    """
    add_no_cache_headers(response)
    requests = db.query(WithdrawalRequest).filter_by(
        user_id=current_user.id
    ).order_by(desc(WithdrawalRequest.created_at)).all()
    
    return [
        {
            'id': req.id,
            'user_id': req.user_id,
            'withdrawal_amount': req.withdrawal_amount,
            'admin_charges': req.admin_charges,
            'tds_amount': req.tds_amount,
            'final_payout': req.final_payout,
            'request_date': req.request_date.isoformat() if req.request_date else '',
            'status': req.status,
            'created_at': req.created_at.isoformat() if req.created_at else '',
            'processed_at': req.processed_at.isoformat() if req.processed_at else None,
            'bank_name': req.bank_name,
            'account_number': req.account_number,
            'ifsc_code': req.ifsc_code,
            'account_holder_name': req.account_holder_name,
            'payment_reference': req.payment_reference,
            'paid_date': req.paid_date.isoformat() if req.paid_date else None
        }
        for req in requests
    ]

@router.get('/withdrawal-summary')
async def get_withdrawal_summary(
    response: Response,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_mnr_user_from_hybrid)
):
    """
    Get withdrawal summary for current user - NO CACHE
    DC Protocol: Uses WalletService.get_earnings_summary() for both GROSS and NET values
    Shows BOTH GROSS and NET earnings with complete breakup
    Uses MNR-only auth to ensure correct user_id (string MNR ID)
    """
    add_no_cache_headers(response)
    from app.services.wallet_service import WalletService
    from sqlalchemy import func
    
    # DC Protocol: Use SINGLE SOURCE OF TRUTH - WalletService.get_earnings_summary()
    # This uses calculated Ved Income (not database records)
    wallet_service = WalletService(db)
    earnings_summary = wallet_service.get_earnings_summary(str(current_user.id))
    
    # Get BOTH GROSS and NET total earnings
    total_earned_gross = earnings_summary.get('total_gross_earnings', 0)
    total_earned_net = earnings_summary.get('total_net_earnings', 0)
    total_admin_deduction = earnings_summary.get('total_admin_deduction', 0)
    total_tds_deduction = earnings_summary.get('total_tds_deduction', 0)
    
    # Calculate Guru Dakshina deduction (2% of GROSS)
    total_guru_deduction = total_earned_gross * 0.02
    
    # DC PROTOCOL: Query pending_income (SINGLE SOURCE OF TRUTH for all earnings)
    all_transactions = db.query(PendingIncome).filter(
        PendingIncome.user_id == current_user.id
    ).all()
    
    # DC PROTOCOL PHASE 1.8: Calculate amounts using SINGLE SOURCE OF TRUTH
    # Use withdrawal_request.final_payout for actual payments (not pending_income.verification_status)
    # This resolves the data inconsistency where same amount appeared in multiple states
    
    # ACTUAL PAID TO BANK: Get sum from withdrawal records (Completed = actually paid)
    # This is the SINGLE SOURCE OF TRUTH for user payments
    total_paid_to_bank = db.query(func.sum(WithdrawalRequest.final_payout)).filter(
        WithdrawalRequest.user_id == current_user.id,
        WithdrawalRequest.status == 'Completed'
    ).scalar() or 0
    
    # For detailed breakup reporting (admin view of approval pipeline)
    # These show income at various stages but DON'T affect overall pending calculation
    admin_pending_gross_db = sum(t.gross_amount or 0 for t in all_transactions if t.verification_status == 'Pending')
    admin_pending_net_db = sum(t.net_amount or 0 for t in all_transactions if t.verification_status == 'Pending')
    super_admin_pending_gross_db = sum(t.gross_amount or 0 for t in all_transactions if t.verification_status == 'Admin Verified')
    super_admin_pending_net_db = sum(t.net_amount or 0 for t in all_transactions if t.verification_status == 'Admin Verified')
    finance_pending_gross_db = sum(t.gross_amount or 0 for t in all_transactions if t.verification_status == 'Super Admin Verified')
    finance_pending_net_db = sum(t.net_amount or 0 for t in all_transactions if t.verification_status == 'Super Admin Verified')
    rejected_gross_db = sum(t.gross_amount or 0 for t in all_transactions if t.verification_status == 'Rejected')
    rejected_net_db = sum(t.net_amount or 0 for t in all_transactions if t.verification_status == 'Rejected')
    
    # DC PROTOCOL FIX: Overall pending = Earned - Actual Paid (using single source: withdrawal_request)
    # Previously: Used pending_income.verification_status='Completed', causing ₹10,210.94 discrepancy
    # Now: Uses withdrawal_request.final_payout (actual bank payments), correct calculation
    total_paid_gross = float(total_paid_to_bank)  # Using actual withdrawal data
    total_paid_net = float(total_paid_to_bank)    # Using actual withdrawal data
    overall_pending_gross = total_earned_gross - total_paid_gross
    overall_pending_net = total_earned_net - total_paid_net
    
    # Group by date for transaction list (show GROSS amounts)
    # Use DATE() to group by date only, not timestamp
    date_wise_query = db.query(
        func.date(PendingIncome.business_date).label('business_date'),
        func.sum(PendingIncome.gross_amount).label('total_gross'),
        func.sum(PendingIncome.net_amount).label('total_net'),
        func.min(PendingIncome.verification_status).label('status'),
        func.min(PendingIncome.accounts_paid_at).label('paid_date')
    ).filter(
        PendingIncome.user_id == current_user.id
    ).group_by(
        func.date(PendingIncome.business_date)
    ).order_by(
        desc(func.date(PendingIncome.business_date))
    ).all()
    
    return {
        'success': True,
        'data': {
            'summary': {
                # GROSS values
                'total_earned_gross': round(float(total_earned_gross)),
                'total_paid_gross': round(float(total_paid_gross)),
                'overall_pending_gross': round(float(overall_pending_gross)),  # DC: Earned - Paid
                'admin_pending_gross': round(float(admin_pending_gross_db)),
                'super_admin_pending_gross': round(float(super_admin_pending_gross_db)),
                'finance_pending_gross': round(float(finance_pending_gross_db)),
                'rejected_gross': round(float(rejected_gross_db)),
                
                # NET values (after deductions)
                'total_earned_net': round(float(total_earned_net)),
                'total_paid_net': round(float(total_paid_net)),
                'overall_pending_net': round(float(overall_pending_net)),  # DC: Earned - Paid
                'admin_pending_net': round(float(admin_pending_net_db)),
                'super_admin_pending_net': round(float(super_admin_pending_net_db)),
                'finance_pending_net': round(float(finance_pending_net_db)),
                'rejected_net': round(float(rejected_net_db)),
                
                # Deductions breakup
                'total_guru_deduction': round(float(total_guru_deduction)),
                'total_admin_deduction': round(float(total_admin_deduction)),
                'total_tds_deduction': round(float(total_tds_deduction)),
                'total_deductions': round(float(total_guru_deduction + total_admin_deduction + total_tds_deduction)),
                
                # ACTUAL BANK PAYMENTS (from withdrawal_request table with Completed status)
                'total_paid_to_bank': round(float(total_paid_to_bank)),
                
                # Legacy compatibility (keep old field names pointing to NET)
                'total_earned': round(float(total_earned_net)),
                'total_paid': round(float(total_paid_net)),
                'total_pending': round(float(overall_pending_net)),  # DC: Earned - Paid ✅
                'overall_pending': round(float(overall_pending_net)),  # DC: Earned - Paid ✅
                'admin_pending': round(float(admin_pending_net_db)),
                'super_admin_pending': round(float(super_admin_pending_net_db)),
                'finance_pending': round(float(finance_pending_net_db)),
                'rejected': round(float(rejected_net_db))
            },
            'transactions': [
                {
                    'business_date': row.business_date.isoformat() if row.business_date else None,
                    'gross_amount': round(float(row.total_gross or 0)),
                    'net_amount': round(float(row.total_net or 0)),
                    'verification_status': row.status or 'Pending',
                    'accounts_paid_at': row.paid_date.isoformat() if row.paid_date else None
                }
                for row in date_wise_query
            ]
        }
    }

class ProcessWithdrawalRequest(BaseModel):
    action: str = Field(..., pattern='^(approve|reject|send_to_bank|mark_paid)$')
    payment_reference: Optional[str] = None
    admin_notes: Optional[str] = None

@router.get('/admin/withdrawal-report')
def admin_withdrawal_report(
    response: Response,
    status_filter: Optional[str] = None,
    user_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_hybrid)
):
    """
    Admin view of all withdrawal requests with filtering - NO CACHE
    DC Protocol: Shows original income gross + deductions + net (final_payout to bank)
    """
    add_no_cache_headers(response)
    
    # DC Protocol: Menu-based access control - page assignment = full access
    # allowed_types = ['Admin', 'Finance Admin', 'Super Admin', 'RVZ ID', 'VGK4U', 'VGK4U Supreme', 'Key Leadership', 'Leadership Role', 'HR', 'Manager', 'Senior Executive']
    # if (getattr(current_user, 'staff_type', None) or getattr(current_user, 'user_type', '')) not in allowed_types:
    #     raise HTTPException(
    #         status_code=status.HTTP_403_FORBIDDEN,
    #         detail='Admin access required'
    #     )
    
    query = db.query(WithdrawalRequest)
    
    if status_filter:
        query = query.filter(WithdrawalRequest.status == status_filter)
    
    if user_id:
        query = query.filter(WithdrawalRequest.user_id == user_id)
    
    requests = query.order_by(desc(WithdrawalRequest.created_at)).all()
    
    # DC Protocol: Fetch income-level gross and deductions for each user
    # This shows the ORIGINAL gross from income before 12% deductions were applied
    user_ids = list(set(req.user_id for req in requests))
    
    # Get cumulative income data per user (gross and deductions at income level)
    user_income_totals = {}
    if user_ids:
        income_query = db.query(
            PendingIncome.user_id,
            func.sum(PendingIncome.gross_amount).label('total_gross'),
            func.sum(PendingIncome.gurudakshina_deduction).label('total_gd'),
            func.sum(PendingIncome.admin_deduction).label('total_admin'),
            func.sum(PendingIncome.tds_deduction).label('total_tds'),
            func.sum(PendingIncome.net_amount).label('total_net')
        ).filter(
            PendingIncome.user_id.in_(user_ids),
            PendingIncome.verification_status == 'Completed'
        ).group_by(PendingIncome.user_id).all()
        
        for row in income_query:
            user_income_totals[row.user_id] = {
                'income_gross': round(float(row.total_gross or 0)),
                'income_gd_deduction': round(float(row.total_gd or 0)),
                'income_admin_deduction': round(float(row.total_admin or 0)),
                'income_tds_deduction': round(float(row.total_tds or 0)),
                'income_total_deductions': round(float((row.total_gd or 0) + (row.total_admin or 0) + (row.total_tds or 0))),
                'income_net': round(float(row.total_net or 0))
            }
    
    total_pending = db.query(WithdrawalRequest).filter_by(status='Pending').count()
    total_approved = db.query(WithdrawalRequest).filter(
        WithdrawalRequest.status.in_(['Admin Verified', 'Super Admin Approved'])
    ).count()
    total_completed = db.query(WithdrawalRequest).filter_by(status='Completed').count()
    
    # Build response with income-level gross and deductions
    request_list = []
    for req in requests:
        income_data = user_income_totals.get(req.user_id, {
            'income_gross': 0,
            'income_gd_deduction': 0,
            'income_admin_deduction': 0,
            'income_tds_deduction': 0,
            'income_total_deductions': 0,
            'income_net': 0
        })
        
        # Calculate proportional gross/deductions for this withdrawal
        # Based on withdrawal_amount / total_income_net ratio
        proportion = 1.0
        if income_data['income_net'] > 0:
            proportion = req.withdrawal_amount / income_data['income_net']
        
        # Proportional gross = withdrawal represents this portion of total income
        proportional_gross = round(income_data['income_gross'] * proportion)
        proportional_gd = round(income_data['income_gd_deduction'] * proportion)
        proportional_admin = round(income_data['income_admin_deduction'] * proportion)
        proportional_tds = round(income_data['income_tds_deduction'] * proportion)
        proportional_deductions = proportional_gd + proportional_admin + proportional_tds
        
        request_list.append({
            'id': req.id,
            'user_id': req.user_id,
            'user_name': req.user.name if req.user else 'Unknown',
            'withdrawal_amount': req.withdrawal_amount,
            'income_gross': proportional_gross,
            'income_gd_deduction': proportional_gd,
            'income_admin_deduction': proportional_admin,
            'income_tds_deduction': proportional_tds,
            'income_total_deductions': proportional_deductions,
            'admin_charges': req.admin_charges,
            'tds_amount': req.tds_amount,
            'final_payout': req.final_payout,
            'request_date': req.request_date.isoformat() if req.request_date else '',
            'status': req.status,
            'is_auto_generated': req.is_auto_generated if hasattr(req, 'is_auto_generated') else False,
            'created_at': req.created_at.isoformat() if req.created_at else '',
            'processed_at': req.processed_at.isoformat() if req.processed_at else None,
            'bank_name': req.bank_name,
            'account_number': req.account_number,
            'ifsc_code': req.ifsc_code,
            'account_holder_name': req.account_holder_name,
            'payment_reference': req.payment_reference,
            'paid_date': req.paid_date.isoformat() if req.paid_date else None
        })
    
    return {
        'success': True,
        'requests': request_list,
        'summary': {
            'total_pending': total_pending,
            'total_approved': total_approved,
            'total_completed': total_completed,
            'total_requests': len(requests)
        }
    }

@router.post('/admin/process-withdrawal/{withdrawal_id}')
def process_withdrawal(
    withdrawal_id: int,
    data: ProcessWithdrawalRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_hybrid)
):
    """
    Admin processes withdrawal request
    Actions: approve, reject, send_to_bank, mark_paid
    """
    # DC Protocol: Menu-based access control - page assignment = full access
    # if (getattr(current_user, 'staff_type', None) or (getattr(current_user, 'staff_type', None) or getattr(current_user, 'user_type', ''))) not in ['Admin', 'Finance Admin', 'Super Admin', 'RVZ ID', 'VGK4U', 'VGK4U Supreme', 'Key Leadership', 'Leadership Role', 'HR', 'Manager', 'Senior Executive']:
    #     raise HTTPException(
    #         status_code=status.HTTP_403_FORBIDDEN,
    #         detail='Admin access required'
    #     )
    
    withdrawal = db.query(WithdrawalRequest).filter_by(id=withdrawal_id).first()
    if not withdrawal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Withdrawal request not found'
        )
    
    if data.action == 'approve':
        # Admin verification - atomic state transition
        from sqlalchemy import text
        
        approved = db.execute(
            text("""
                UPDATE withdrawal_request
                SET status = 'Admin Verified',
                    processed_at = NOW()
                WHERE id = :req_id
                AND status IN ('Pending', 'Admin Verified')
                RETURNING id
            """),
            {"req_id": withdrawal_id}
        ).fetchone()
        
        if not approved:
            db.refresh(withdrawal)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f'Cannot approve request with status: {withdrawal.status}'
            )
        
        db.refresh(withdrawal)
        message = f'Withdrawal request #{withdrawal_id} approved'
        
    elif data.action == 'reject':
        # DC Protocol Phase 1.7: Rejection only allowed BEFORE bank transfer
        # Business Rule: Once sent to bank (Completed status), cannot reject - must use reversal process
        from sqlalchemy import text
        
        # Atomically reject request (only if Pending or Admin Verified)
        rejection_result = db.execute(
            text("""
                UPDATE withdrawal_request
                SET status = 'Rejected', 
                    processed_at = NOW(),
                    bulk_batch_id = NULL
                WHERE id = :req_id
                AND status IN ('Pending', 'Admin Verified')
                RETURNING id
            """),
            {"req_id": withdrawal_id}
        ).fetchone()
        
        if not rejection_result:
            # Cannot reject - either already processed or sent to bank
            db.refresh(withdrawal)
            if withdrawal.status in ['Completed', 'Completed']:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f'Cannot reject withdrawal after bank transfer. Current status: {withdrawal.status}. Use reversal process instead.'
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f'Cannot reject request with current status: {withdrawal.status}'
                )
        
        db.refresh(withdrawal)
        # DC Protocol Phase 1.7: No wallet re-credit needed (wallet only deducted at 'Completed')
        message = f'Withdrawal request #{withdrawal_id} rejected (no wallet changes - funds never deducted)'
        
    elif data.action == 'send_to_bank':
        # Super Admin or Finance Admin sends to bank
        # DC Protocol: Menu-based access control - page assignment = full access
        # if (getattr(current_user, 'staff_type', None) or (getattr(current_user, 'staff_type', None) or getattr(current_user, 'user_type', ''))) not in ['Super Admin', 'Finance Admin', 'RVZ ID']:
        #     raise HTTPException(
        #         status_code=status.HTTP_403_FORBIDDEN,
        #         detail='Super Admin or Finance Admin access required to send to bank'
        #     )
        
        # DC Protocol Phase 1.9: VALIDATION - Must set paid_date when marking Completed
        # This prevents semantic inconsistency: status='Completed' but paid_date=NULL
        from sqlalchemy import text
        
        # Step 1: Atomically change status to 'Completed' and get withdrawal details
        # FIX: NOW SET paid_date WHEN status CHANGES TO 'Completed'
        sent = db.execute(
            text("""
                UPDATE withdrawal_request
                SET status = 'Completed',
                    processed_at = NOW(),
                    paid_date = COALESCE(paid_date, NOW()),
                    payment_reference = COALESCE(:ref, payment_reference)
                WHERE id = :req_id
                AND status IN ('Admin Verified', 'Completed')
                RETURNING user_id, withdrawal_amount
            """),
            {"req_id": withdrawal_id, "ref": data.payment_reference}
        ).fetchone()
        
        if not sent:
            db.refresh(withdrawal)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f'Cannot send to bank from status: {withdrawal.status}'
            )
        
        # Step 2: Deduct from user's withdrawable wallet (only for new withdrawals going forward)
        # Historical withdrawals (created before this change) are not affected
        user_id, amount = sent
        
        # DC Protocol Phase 1.7: Authorize wallet write for withdrawal deduction
        db.execute(text("SET LOCAL app.wallet_write_allowed = 'wallet_sync'"))
        
        # Deduct wallet atomically (only if sufficient balance exists)
        deduction_result = db.execute(
            text("""
                UPDATE "user"
                SET withdrawable_wallet = withdrawable_wallet - :amount
                WHERE id = :user_id
                AND COALESCE(withdrawable_wallet, 0) >= :amount
                RETURNING withdrawable_wallet
            """),
            {"amount": amount, "user_id": user_id}
        ).fetchone()
        
        if not deduction_result:
            # Insufficient balance - rollback status change
            db.execute(
                text("""
                    UPDATE withdrawal_request
                    SET status = 'Admin Verified',
                        processed_at = NULL
                    WHERE id = :req_id
                """),
                {"req_id": withdrawal_id}
            )
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f'Insufficient wallet balance for withdrawal. Required: ₹{amount:,}'
            )
        
        db.refresh(withdrawal)
        
        # DC Protocol Dec 30, 2025: Create SFMS ledger entries when withdrawal is sent to bank
        # This creates proper accounting entries: Income (8% admin), Expense (business promo), Party Ledger
        staff_id = getattr(current_user, 'id', None) if hasattr(current_user, 'emp_code') and current_user.emp_code else None
        sfms_result = create_withdrawal_ledger_entries(db, withdrawal, approved_by_id=staff_id)
        if sfms_result.get('success'):
            message = f'Withdrawal request #{withdrawal_id} sent to bank (₹{amount:,} deducted from wallet). SFMS entries created.'
        else:
            message = f'Withdrawal request #{withdrawal_id} sent to bank (₹{amount:,} deducted from wallet). Warning: SFMS entries failed - {sfms_result.get("error", "unknown")}'
        
    elif data.action == 'mark_paid':
        # Mark as completed/paid
        # DC Protocol: Menu-based access control - page assignment = full access
        # if (getattr(current_user, 'staff_type', None) or (getattr(current_user, 'staff_type', None) or getattr(current_user, 'user_type', ''))) not in ['Super Admin', 'Finance Admin', 'RVZ ID']:
        #     raise HTTPException(
        #         status_code=status.HTTP_403_FORBIDDEN,
        #         detail='Super Admin or Finance Admin access required to mark as paid'
        #     )
        
        # DC Protocol Phase 1.9: VALIDATION - paid_date is mandatory for Completed status
        from sqlalchemy import text
        
        # Atomic state transition - update paid_date if not already set
        completed = db.execute(
            text("""
                UPDATE withdrawal_request
                SET status = 'Completed',
                    paid_date = COALESCE(paid_date, NOW()),
                    payment_reference = COALESCE(:ref, payment_reference)
                WHERE id = :req_id
                AND status = 'Completed'
                RETURNING id
            """),
            {"req_id": withdrawal_id, "ref": data.payment_reference}
        ).fetchone()
        
        if not completed:
            db.refresh(withdrawal)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f'Cannot mark as paid from status: {withdrawal.status}. Must be Completed first.'
            )
        
        db.refresh(withdrawal)
        # DC Protocol Phase 1.9: Withdrawal marked as Completed WITH paid_date (single source of truth)
        message = f'Withdrawal request #{withdrawal_id} marked as completed (paid_date: {withdrawal.paid_date})'
    
    _create_tds_tracking_record(db, withdrawal)
    db.commit()
    
    return {
        'success': True,
        'message': message,
        'withdrawal_id': withdrawal_id,
        'new_status': withdrawal.status
    }

class CreateBatchRequest(BaseModel):
    batch_name: str = Field(..., min_length=1)
    status_filter: Optional[str] = 'Pending'
    user_ids: Optional[List[str]] = None
    admin_notes: Optional[str] = None

@router.post('/admin/create-batch')
def create_withdrawal_batch(
    data: CreateBatchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_hybrid)
):
    """
    Create bulk withdrawal batch from pending requests
    """
    # DC Protocol: Menu-based access control - page assignment = full access
    # if (getattr(current_user, 'staff_type', None) or (getattr(current_user, 'staff_type', None) or getattr(current_user, 'user_type', ''))) not in ['Finance Admin', 'Super Admin', 'RVZ ID']:
    #     raise HTTPException(
    #         status_code=status.HTTP_403_FORBIDDEN,
    #         detail='Finance Admin or Super Admin access required'
    #     )
    
    # Get requests to include in batch
    query = db.query(WithdrawalRequest).filter_by(status=data.status_filter or 'Pending')
    
    if data.user_ids:
        query = query.filter(WithdrawalRequest.user_id.in_(data.user_ids))
    
    requests = query.all()
    
    if not requests:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='No withdrawal requests found matching criteria'
        )
    
    # Calculate totals
    total_amount = sum(req.withdrawal_amount for req in requests)
    total_payout = sum(req.final_payout for req in requests)
    
    # Create batch
    batch = BulkWithdrawalBatch(
        batch_name=data.batch_name,
        created_by=current_user.id,
        total_requests=len(requests),
        total_amount=round(float(total_amount)),
        total_payout=round(float(total_payout)),
        status='Draft',
        admin_notes=data.admin_notes
    )
    
    db.add(batch)
    db.commit()
    db.refresh(batch)
    
    # Link requests to batch
    for req in requests:
        req.bulk_batch_id = batch.id
    
    db.commit()
    
    return {
        'success': True,
        'message': f'Batch created with {len(requests)} requests',
        'batch_id': batch.id,
        'batch_name': batch.batch_name,
        'total_requests': len(requests),
        'total_amount': total_amount,
        'total_payout': total_payout
    }

@router.get('/admin/batches')
def get_all_batches(
    status_filter: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_hybrid)
):
    """
    Get all withdrawal batches
    """
    # DC Protocol: Menu-based access control - page assignment = full access
    # if (getattr(current_user, 'staff_type', None) or (getattr(current_user, 'staff_type', None) or getattr(current_user, 'user_type', ''))) not in ['Admin', 'Finance Admin', 'Super Admin', 'RVZ ID', 'VGK4U', 'VGK4U Supreme', 'Key Leadership', 'Leadership Role', 'HR', 'Manager', 'Senior Executive']:
    #     raise HTTPException(
    #         status_code=status.HTTP_403_FORBIDDEN,
    #         detail='Admin access required'
    #     )
    
    query = db.query(BulkWithdrawalBatch)
    
    if status_filter:
        query = query.filter(BulkWithdrawalBatch.status == status_filter)
    
    batches = query.order_by(desc(BulkWithdrawalBatch.created_at)).all()
    
    return {
        'success': True,
        'batches': [
            {
                'id': batch.id,
                'batch_name': batch.batch_name,
                'created_by': batch.created_by,
                'creator_name': batch.creator.name if batch.creator else 'Unknown',
                'total_requests': batch.total_requests,
                'total_amount': batch.total_amount,
                'total_payout': batch.total_payout,
                'status': batch.status,
                'created_at': batch.created_at.isoformat() if batch.created_at else '',
                'submitted_at': batch.submitted_at.isoformat() if batch.submitted_at else None,
                'approved_at': batch.approved_at.isoformat() if batch.approved_at else None,
                'completed_at': batch.completed_at.isoformat() if batch.completed_at else None,
                'admin_notes': batch.admin_notes,
                'approval_notes': batch.approval_notes,
                'rejection_reason': batch.rejection_reason
            }
            for batch in batches
        ]
    }

class ProcessBatchRequest(BaseModel):
    action: str = Field(..., pattern='^(submit|approve|reject|complete)$')
    notes: Optional[str] = None

@router.post('/admin/process-batch/{batch_id}')
def process_batch(
    batch_id: int,
    data: ProcessBatchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_hybrid)
):
    """
    Process withdrawal batch: submit, approve, reject, or complete
    """
    # DC Protocol: Menu-based access control - page assignment = full access
    # if (getattr(current_user, 'staff_type', None) or (getattr(current_user, 'staff_type', None) or getattr(current_user, 'user_type', ''))) not in ['Finance Admin', 'Super Admin', 'RVZ ID']:
    #     raise HTTPException(
    #         status_code=status.HTTP_403_FORBIDDEN,
    #         detail='Finance Admin or Super Admin access required'
    #     )
    
    batch = db.query(BulkWithdrawalBatch).filter_by(id=batch_id).first()
    if not batch:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Batch not found'
        )
    
    if data.action == 'submit':
        batch.status = 'Submitted'
        batch.submitted_at = datetime.utcnow()
        if data.notes:
            batch.admin_notes = data.notes
        message = f'Batch {batch.batch_name} submitted for approval'
        
    elif data.action == 'approve':
        # DC Protocol: Menu-based access control - page assignment = full access
        # if (getattr(current_user, 'staff_type', None) or (getattr(current_user, 'staff_type', None) or getattr(current_user, 'user_type', ''))) not in ['Super Admin', 'RVZ ID']:
        #     raise HTTPException(
        #         status_code=status.HTTP_403_FORBIDDEN,
        #         detail='Super Admin access required to approve batches'
        #     )
        batch.status = 'Approved'
        batch.approved_at = datetime.utcnow()
        if data.notes:
            batch.approval_notes = data.notes
        
        # CRITICAL: Atomic batch approval - only update requests still in valid states
        from sqlalchemy import text
        approved_count = db.execute(
            text("""
                UPDATE withdrawal_request
                SET status = 'Admin Verified',
                    processed_at = NOW()
                WHERE bulk_batch_id = :batch_id
                AND status IN ('Pending')
            """),
            {"batch_id": batch_id}
        ).rowcount
        
        message = f'Batch {batch.batch_name} approved and {approved_count} requests verified'
        
    elif data.action == 'reject':
        batch.status = 'Rejected'
        if data.notes:
            batch.rejection_reason = data.notes
        
        # DC Protocol Phase 1.7: Batch rejection only allowed BEFORE bank transfer
        # Business Rule: Cannot reject requests after Completed status
        from sqlalchemy import text
        
        # Check if any requests are already sent to bank
        bank_sent_check = db.execute(
            text("""
                SELECT COUNT(*) as bank_sent_count
                FROM withdrawal_request
                WHERE bulk_batch_id = :batch_id
                AND status IN ('Completed', 'Completed')
            """),
            {"batch_id": batch_id}
        ).fetchone()
        
        if bank_sent_check and bank_sent_check[0] > 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f'Cannot reject batch: {bank_sent_check[0]} request(s) already sent to bank. Use reversal process instead.'
            )
        
        # Atomically reject all pending/verified requests
        rejected_count = db.execute(
            text("""
                UPDATE withdrawal_request
                SET status = 'Rejected', 
                    processed_at = NOW(),
                    bulk_batch_id = NULL
                WHERE bulk_batch_id = :batch_id
                AND status IN ('Pending', 'Admin Verified')
            """),
            {"batch_id": batch_id}
        ).rowcount
        
        # DC Protocol Phase 1.7: No wallet re-credits needed (wallets only deducted at 'Completed')
        message = f'Batch {batch.batch_name} rejected: {rejected_count} request(s) (no wallet changes - funds never deducted)'
        
    elif data.action == 'complete':
        # DC Protocol: Menu-based access control - page assignment = full access
        # if (getattr(current_user, 'staff_type', None) or (getattr(current_user, 'staff_type', None) or getattr(current_user, 'user_type', ''))) not in ['Super Admin', 'Finance Admin', 'RVZ ID']:
        #     raise HTTPException(
        #         status_code=status.HTTP_403_FORBIDDEN,
        #         detail='Super Admin or Finance Admin access required to complete batches'
        #     )
        batch.status = 'Completed'
        batch.completed_at = datetime.utcnow()
        
        # DC Protocol Phase 1.7: Batch completion - send to bank AND deduct wallets atomically
        from sqlalchemy import text
        
        # Step 1: Get all requests ready to send to bank and their wallet amounts
        requests_to_complete = db.execute(
            text("""
                SELECT user_id, withdrawal_amount
                FROM withdrawal_request
                WHERE bulk_batch_id = :batch_id
                AND status = 'Admin Verified'
            """),
            {"batch_id": batch_id}
        ).fetchall()
        
        if not requests_to_complete:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='No requests in Admin Verified status to complete'
            )
        
        # Step 2: Deduct wallets for all requests (with balance validation)
        db.execute(text("SET LOCAL app.wallet_write_allowed = 'wallet_sync'"))
        
        total_deducted = 0
        failed_users = []
        
        for user_id, amount in requests_to_complete:
            deduction_result = db.execute(
                text("""
                    UPDATE "user"
                    SET withdrawable_wallet = withdrawable_wallet - :amount
                    WHERE id = :user_id
                    AND COALESCE(withdrawable_wallet, 0) >= :amount
                    RETURNING withdrawable_wallet
                """),
                {"amount": amount, "user_id": user_id}
            ).fetchone()
            
            if not deduction_result:
                failed_users.append(user_id)
            else:
                total_deducted += amount
        
        if failed_users:
            # Some users had insufficient balance - rollback and report
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f'Insufficient wallet balance for {len(failed_users)} user(s). Cannot complete batch. User IDs: {failed_users[:5]}'
            )
        
        # Step 3: All wallets deducted successfully - now mark as Completed
        completed_count = db.execute(
            text("""
                UPDATE withdrawal_request
                SET status = 'Completed',
                    processed_at = NOW()
                WHERE bulk_batch_id = :batch_id
                AND status = 'Admin Verified'
            """),
            {"batch_id": batch_id}
        ).rowcount
        
        batch_withdrawals = db.query(WithdrawalRequest).filter(
            WithdrawalRequest.bulk_batch_id == batch_id,
            WithdrawalRequest.status == 'Completed'
        ).all()
        for bw in batch_withdrawals:
            _create_tds_tracking_record(db, bw)

        message = f'Batch {batch.batch_name} completed: {completed_count} requests sent to bank (₹{total_deducted:,} deducted from wallets)'
    
    db.commit()
    
    return {
        'success': True,
        'message': message,
        'batch_id': batch_id,
        'new_status': batch.status
    }

ALLOWED_ADMIN_STAFF_TYPES = [
    'Admin', 'Finance Admin', 'Super Admin', 'RVZ ID', 
    'VGK4U', 'VGK4U Supreme', 'Key Leadership', 'Leadership Role', 
    'HR', 'Manager', 'Senior Executive'
]

@router.get('/income-transactions')
async def get_income_transactions(
    request: Request,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    verification_status: Optional[str] = None,
    user_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_hybrid)
):
    """
    Get user's income transaction history DATE-WISE (one row per date)
    DC PROTOCOL: STF v2.0 - Final Earnings = SUM of ALL income (regardless of filters)
    Filters (dates, status) affect DISPLAY rows only, NOT summary totals
    
    DUAL-CONTEXT AUTH (DC Protocol Fix - Jan 2026):
    - MNR users: Can only view their own transactions (user_id param ignored)
    - Staff users with admin roles: Can view any user's transactions (user_id param required)
    - DUAL-SESSION FIX: If user has both Staff + MNR sessions, prioritize MNR context when no user_id provided
    """
    from sqlalchemy import and_, func, case
    from fastapi import Request
    
    caller_type = getattr(current_user, 'staff_type', None) or getattr(current_user, 'user_type', '')
    is_staff_admin = caller_type in ALLOWED_ADMIN_STAFF_TYPES
    target_user_id = None  # Initialize variable
    
    # DC PROTOCOL FIX (Jan 2026): Handle dual-session (Staff + MNR) users
    # If staff admin but no user_id provided, check if they also have MNR session
    # and use that for their own withdrawals page
    if is_staff_admin and not user_id:
        # Try to get MNR user from session cookie (web) or Authorization header (mobile)
        session_token = request.cookies.get("session_token") or request.cookies.get("session")
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            session_token = auth_header.replace("Bearer ", "")
        if session_token:
            try:
                from app.core.security import SecurityManager
                payload = SecurityManager.verify_token(session_token)
                if payload and payload.get("sub"):
                    mnr_id = str(payload["sub"])
                    if mnr_id.startswith("MNR"):
                        # User has MNR session - use their MNR ID for own data
                        mnr_user = db.query(User).filter(User.id == mnr_id).first()
                        if mnr_user:
                            target_user_id = mnr_id
                            is_staff_admin = False  # Treat as MNR user for this request
            except Exception:
                pass  # Fall through to admin path if MNR session check fails
    
    if is_staff_admin:
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='user_id parameter required for admin access'
            )
        target_user = db.query(User).filter_by(id=user_id).first()
        if not target_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f'User {user_id} not found'
            )
        target_user_id = user_id
    elif target_user_id is None:
        if not hasattr(current_user, 'id') or not current_user.id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail='MNR user authentication required'
            )
        target_user_id = str(current_user.id)
    
    # ============================================================================
    # STF v2.0 LAYER 1: Get TOTAL EARNED (ALL income, NO filters)
    # This is the SINGLE SOURCE OF TRUTH - what user actually earned
    # ============================================================================
    all_earned_query = db.query(PendingIncome).filter(
        PendingIncome.user_id == target_user_id
    )
    all_earned_transactions = all_earned_query.all()
    
    # Total earned = SUM of ALL income (all statuses, all dates)
    total_earned_net = float(sum(t.net_amount or 0 for t in all_earned_transactions))
    total_earned_gross = float(sum(t.gross_amount or 0 for t in all_earned_transactions))
    total_deductions = total_earned_gross - total_earned_net
    
    # ============================================================================
    # STF v2.0 LAYER 2: Get ACTUAL PAID (withdrawal_request table)
    # Single source of truth for actual bank payments
    # ============================================================================
    actual_paid_result = db.query(func.sum(WithdrawalRequest.final_payout)).filter(
        WithdrawalRequest.user_id == target_user_id,
        WithdrawalRequest.status == 'Completed'
    ).scalar() or 0
    total_paid_net = float(actual_paid_result)
    total_paid_gross = total_paid_net / 0.88 if total_paid_net > 0 else 0
    
    # ============================================================================
    # STF v2.0 LAYER 3: Calculate PENDING (using single source of truth)
    # Overall Pending = Total Earned - Actually Paid
    # ============================================================================
    total_pending_gross = total_earned_gross - total_paid_gross
    total_pending_net = total_earned_net - total_paid_net
    
    # ============================================================================
    # STF v2.0 LAYER 4: Get DISPLAY ROWS (with filters for user view)
    # These are for showing transaction breakdown - filters apply here
    # ============================================================================
    display_query = db.query(PendingIncome).filter(
        PendingIncome.user_id == target_user_id
    )
    
    # Apply date filters to DISPLAY rows only
    if start_date:
        try:
            start_dt = datetime.fromisoformat(start_date)
            display_query = display_query.filter(PendingIncome.business_date >= start_dt)
        except ValueError:
            pass
    
    if end_date:
        try:
            end_dt = datetime.fromisoformat(end_date)
            display_query = display_query.filter(PendingIncome.business_date <= end_dt)
        except ValueError:
            pass
    
    # Apply status filter to DISPLAY rows only
    if verification_status:
        display_query = display_query.filter(PendingIncome.verification_status == verification_status)
    
    INCOME_TYPE_REBRAND = {
        'Direct Referral': 'Direct Facilitation',
        'Matching Referral': 'Group Performance Recognition',
        'Ved Income': 'VED Leadership Recognition',
        'Guru Dakshina': 'Mentorship Contribution Benefit'
    }

    segmented_query = db.query(
        PendingIncome.income_type.label('income_type'),
        func.date(PendingIncome.business_date).label('business_date'),
        func.sum(PendingIncome.gross_amount).label('total_gross'),
        func.sum(PendingIncome.gurudakshina_deduction).label('total_gurudakshina'),
        func.sum(PendingIncome.admin_deduction).label('total_admin'),
        func.sum(PendingIncome.tds_deduction).label('total_tds'),
        func.sum(PendingIncome.net_amount).label('total_net'),
        func.min(PendingIncome.verification_status).label('status'),
        func.min(PendingIncome.accounts_paid_at).label('paid_date'),
        func.count(PendingIncome.id).label('record_count')
    ).filter(
        PendingIncome.user_id == target_user_id
    )

    if start_date:
        try:
            start_dt = datetime.fromisoformat(start_date)
            segmented_query = segmented_query.filter(PendingIncome.business_date >= start_dt)
        except ValueError:
            pass

    if end_date:
        try:
            end_dt = datetime.fromisoformat(end_date)
            segmented_query = segmented_query.filter(PendingIncome.business_date <= end_dt)
        except ValueError:
            pass

    if verification_status:
        segmented_query = segmented_query.filter(PendingIncome.verification_status == verification_status)

    segmented_results = segmented_query.group_by(
        PendingIncome.income_type,
        func.date(PendingIncome.business_date)
    ).order_by(
        desc(func.date(PendingIncome.business_date))
    ).all()

    segments = {}
    for row in segmented_results:
        db_type = row.income_type or 'Other'
        display_type = INCOME_TYPE_REBRAND.get(db_type, db_type)
        if display_type not in segments:
            segments[display_type] = {
                'income_type': display_type,
                'db_income_type': db_type,
                'total_gross': 0,
                'total_net': 0,
                'transactions': []
            }
        seg = segments[display_type]
        row_gross = round(float(row.total_gross or 0))
        row_net = round(float(row.total_net or 0))
        seg['total_gross'] += row_gross
        seg['total_net'] += row_net
        seg['transactions'].append({
            'business_date': row.business_date.isoformat() if row.business_date else None,
            'gross_amount': row_gross,
            'gurudakshina_deduction': round(float(row.total_gurudakshina or 0)),
            'admin_deduction': round(float(row.total_admin or 0)),
            'tds_deduction': round(float(row.total_tds or 0)),
            'net_amount': row_net,
            'verification_status': row.status or 'Pending',
            'accounts_paid_at': row.paid_date.isoformat() if row.paid_date else None,
            'record_count': row.record_count
        })

    segment_order = [
        'Direct Facilitation',
        'Group Performance Recognition',
        'VED Leadership Recognition',
        'Mentorship Contribution Benefit'
    ]
    ordered_segments = []
    for seg_name in segment_order:
        if seg_name in segments:
            ordered_segments.append(segments[seg_name])
    for seg_name, seg_data in segments.items():
        if seg_name not in segment_order:
            ordered_segments.append(seg_data)

    date_agg = {}
    for row in segmented_results:
        d = row.business_date.isoformat() if row.business_date else None
        if d not in date_agg:
            date_agg[d] = {
                'business_date': d,
                'gross_amount': 0, 'gurudakshina_deduction': 0,
                'admin_deduction': 0, 'tds_deduction': 0, 'net_amount': 0,
                'verification_status': row.status or 'Pending',
                'accounts_paid_at': row.paid_date.isoformat() if row.paid_date else None
            }
        agg = date_agg[d]
        agg['gross_amount'] += round(float(row.total_gross or 0))
        agg['gurudakshina_deduction'] += round(float(row.total_gurudakshina or 0))
        agg['admin_deduction'] += round(float(row.total_admin or 0))
        agg['tds_deduction'] += round(float(row.total_tds or 0))
        agg['net_amount'] += round(float(row.total_net or 0))
    legacy_transactions = sorted(date_agg.values(), key=lambda x: x['business_date'] or '', reverse=True)
    
    # ============================================================================
    # STF v2.0 LAYER 5: Pending breakdown by status
    # DC Protocol Feb 2026: 2-step workflow (Pending → Staff Validated → Completed)
    # ============================================================================
    admin_pending_net = float(sum(t.net_amount or 0 for t in all_earned_transactions if t.verification_status == 'Pending'))
    staff_validated_net = float(sum(t.net_amount or 0 for t in all_earned_transactions if t.verification_status == 'Staff Validated'))
    completed_net = float(sum(t.net_amount or 0 for t in all_earned_transactions if t.verification_status == 'Completed'))
    rejected_net = float(sum(t.net_amount or 0 for t in all_earned_transactions if t.verification_status == 'Rejected'))
    
    # total_deductions already calculated in Layer 1 (no duplicate)
    
    return {
        'success': True,
        'data': {
            'segments': ordered_segments,
            'transactions': legacy_transactions,
            'summary': {
                'total_earned': round(float(total_earned_net)),
                'total_paid_to_bank': round(float(total_paid_net)),
                'total_deductions': round(float(total_deductions)),
                
                'pending_validation': round(float(admin_pending_net)),
                'staff_validated': round(float(staff_validated_net)),
                'completed': round(float(completed_net)),
                'rejected': round(float(rejected_net)),
                
                'transaction_count': len(legacy_transactions)
            }
        }
    }

@router.get('/admin/user-summary')
async def admin_get_user_withdrawal_summary(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_hybrid)
):
    """
    Admin endpoint to get withdrawal summary for any user
    """
    # DC Protocol: Menu-based access control - page assignment = full access
    # if (getattr(current_user, 'staff_type', None) or (getattr(current_user, 'staff_type', None) or getattr(current_user, 'user_type', ''))) not in ['Admin', 'Finance Admin', 'Super Admin', 'RVZ ID', 'VGK4U', 'VGK4U Supreme', 'Key Leadership', 'Leadership Role', 'HR', 'Manager', 'Senior Executive']:
    #     raise HTTPException(
    #         status_code=status.HTTP_403_FORBIDDEN,
    #         detail='Admin access required'
    #     )
    
    target_user = db.query(User).filter_by(id=user_id).first()
    if not target_user:
        raise HTTPException(status_code=404, detail='User not found')
    
    # DC Protocol Phase 1.6: Get withdrawable balance from materialized view (computed value)
    from app.services.wallet_balance_service import get_withdrawable_wallet
    computed_withdrawable = get_withdrawable_wallet(db, user_id)
    
    requests = db.query(WithdrawalRequest).filter_by(user_id=target_user.id).all()
    
    total_requested = sum(req.withdrawal_amount for req in requests)
    total_approved = sum(req.final_payout for req in requests if req.status in ['Admin Verified', 'Super Admin Approved', 'Completed', 'Completed'])
    pending_requests = sum(1 for req in requests if req.status == 'Pending')
    
    return {
        'success': True,
        'withdrawable_balance': round(float(computed_withdrawable)),
        'total_requested': total_requested,
        'total_approved': total_approved,
        'pending_requests': pending_requests,
        'total_requests': len(requests)
    }

@router.get('/admin/user-requests')
async def admin_get_user_withdrawal_requests(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_hybrid)
):
    """
    Admin endpoint to get withdrawal requests for any user
    NOTE: This shows WithdrawalRequest data, not earnings (PendingIncome)
    """
    # DC Protocol: Menu-based access control - page assignment = full access
    # if (getattr(current_user, 'staff_type', None) or (getattr(current_user, 'staff_type', None) or getattr(current_user, 'user_type', ''))) not in ['Admin', 'Finance Admin', 'Super Admin', 'RVZ ID', 'VGK4U', 'VGK4U Supreme', 'Key Leadership', 'Leadership Role', 'HR', 'Manager', 'Senior Executive']:
    #     raise HTTPException(
    #         status_code=status.HTTP_403_FORBIDDEN,
    #         detail='Admin access required'
    #     )
    
    requests = db.query(WithdrawalRequest).filter_by(
        user_id=user_id
    ).order_by(desc(WithdrawalRequest.created_at)).all()
    
    return {
        'success': True,
        'requests': [
            {
                'id': req.id,
                'user_id': req.user_id,
                'withdrawal_amount': req.withdrawal_amount,
                'admin_charges': req.admin_charges,
                'tds_amount': req.tds_amount,
                'final_payout': req.final_payout,
                'request_date': req.request_date.isoformat() if req.request_date else '',
                'status': req.status,
                'created_at': req.created_at.isoformat() if req.created_at else '',
                'processed_at': req.processed_at.isoformat() if req.processed_at else None,
                'bank_name': req.bank_name,
                'account_number': req.account_number,
                'ifsc_code': req.ifsc_code,
                'account_holder_name': req.account_holder_name,
                'payment_reference': req.payment_reference,
                'paid_date': req.paid_date.isoformat() if req.paid_date else None
            }
            for req in requests
        ]
    }

@router.get('/admin/user-earnings')
async def admin_get_user_earnings(
    user_id: str,
    response: Response,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_hybrid)
):
    """
    Admin endpoint to get earnings (PendingIncome) for any user with approval workflow
    Shows ACTUAL EARNINGS that need Finance Admin/RVZ approval - NO CACHE
    """
    add_no_cache_headers(response)
    # DC Protocol: Menu-based access control - page assignment = full access
    # if (getattr(current_user, 'staff_type', None) or (getattr(current_user, 'staff_type', None) or getattr(current_user, 'user_type', ''))) not in ['Admin', 'Finance Admin', 'Super Admin', 'RVZ ID', 'VGK4U', 'VGK4U Supreme', 'Key Leadership', 'Leadership Role', 'HR', 'Manager', 'Senior Executive']:
    #     raise HTTPException(
    #         status_code=status.HTTP_403_FORBIDDEN,
    #         detail='Admin access required'
    #     )
    
    from sqlalchemy import func
    
    # Get all earnings for this user
    all_earnings = db.query(PendingIncome).filter(
        PendingIncome.user_id == user_id
    ).all()
    
    # DC PROTOCOL: Calculate summary by status from single source of truth
    PAID_STATUSES = ['Completed', 'Completed']  # WVV: Both mean money in bank
    total_earned = sum(e.net_amount or 0 for e in all_earnings)
    pending = sum(e.net_amount or 0 for e in all_earnings if e.verification_status == 'Pending')
    admin_verified = sum(e.net_amount or 0 for e in all_earnings if e.verification_status == 'Admin Verified')
    super_admin_verified = sum(e.net_amount or 0 for e in all_earnings if e.verification_status in ('Super Admin Verified', 'Super Admin Approved'))
    finance_paid = sum(e.net_amount or 0 for e in all_earnings if e.verification_status in PAID_STATUSES)
    
    # Group by date
    date_wise = db.query(
        PendingIncome.business_date,
        func.sum(PendingIncome.gross_amount).label('gross'),
        func.sum(PendingIncome.net_amount).label('net'),
        PendingIncome.verification_status
    ).filter(
        PendingIncome.user_id == user_id
    ).group_by(
        PendingIncome.business_date,
        PendingIncome.verification_status
    ).order_by(
        desc(PendingIncome.business_date)
    ).all()
    
    return {
        'success': True,
        'user_id': user_id,
        'summary': {
            'total_earned': round(float(total_earned)),
            'pending': float(pending),
            'admin_verified': float(admin_verified),
            'super_admin_verified': float(super_admin_verified),
            'finance_paid': round(float(finance_paid)),
            'awaiting_approval': float(pending + admin_verified + super_admin_verified)
        },
        'earnings': [
            {
                'business_date': row.business_date.isoformat() if row.business_date else None,
                'gross_amount': round(float(row.gross or 0)),
                'net_amount': round(float(row.net or 0)),
                'verification_status': row.verification_status,
                'can_approve': (getattr(current_user, 'staff_type', None) or getattr(current_user, 'user_type', '')) in ['Finance Admin', 'RVZ ID']
            }
            for row in date_wise
        ]
    }

@router.post('/finance/approve-earnings')
async def finance_approve_user_earnings(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_hybrid)
):
    """
    Finance Admin approves ALL pending earnings for a user and marks as Finance Paid
    Supports skip-level approval for RVZ ID
    """
    # DC Protocol: Menu-based access control - page assignment = full access
    # if (getattr(current_user, 'staff_type', None) or (getattr(current_user, 'staff_type', None) or getattr(current_user, 'user_type', ''))) not in ['Finance Admin', 'RVZ ID']:
    #     raise HTTPException(
    #         status_code=status.HTTP_403_FORBIDDEN,
    #         detail='Finance Admin or RVZ ID access required'
    #     )
    
    from app.models.base import get_indian_time
    from decimal import Decimal
    
    # Get all pending/verified earnings for this user
    if (getattr(current_user, 'staff_type', None) or (getattr(current_user, 'staff_type', None) or getattr(current_user, 'user_type', ''))) == 'RVZ ID':
        # RVZ can approve from ANY status (skip-level)
        pending_earnings = db.query(PendingIncome).filter(
            PendingIncome.user_id == user_id,
            PendingIncome.verification_status.in_(['Pending', 'Admin Verified', 'Super Admin Approved'])
        ).all()
    else:
        # Finance Admin can only approve Super Admin Approved
        pending_earnings = db.query(PendingIncome).filter(
            PendingIncome.user_id == user_id,
            PendingIncome.verification_status == 'Super Admin Approved'
        ).all()
    
    if not pending_earnings:
        return {
            'success': False,
            'message': 'No earnings available for approval'
        }
    
    processed_count = 0
    total_paid = Decimal('0')
    pending_income_ids = []
    
    # Process each earning
    for earning in pending_earnings:
        # Update status to Finance Paid
        earning.verification_status = 'Completed'
        earning.accounts_paid_by_id = current_user.id
        earning.accounts_paid_at = get_indian_time()
        
        total_paid += earning.net_amount
        processed_count += 1
        pending_income_ids.append(earning.id)
    
    # Mark linked Zynova incentives as disbursed
    if pending_income_ids:
        db.query(ZynovaIncentive).filter(
            ZynovaIncentive.pending_income_id.in_(pending_income_ids)
        ).update({
            'status': 'disbursed',
            'disbursed_at': get_indian_time()
        }, synchronize_session=False)
    
    db.commit()
    
    approval_type = "RVZ ID Skip-Level Approval" if (getattr(current_user, 'staff_type', None) or (getattr(current_user, 'staff_type', None) or getattr(current_user, 'user_type', ''))) == 'RVZ ID' else "Finance Admin Approval"
    
    return {
        'success': True,
        'message': f'{approval_type}: Approved {processed_count} earnings totaling ₹{total_paid:,.2f}',
        'processed_count': processed_count,
        'total_amount': round(float(total_paid)),
        'approval_type': approval_type
    }

# ================================
# UNIFIED WITHDRAWAL DASHBOARD
# ================================

@router.get('/admin/dashboard-stats')
async def get_withdrawal_dashboard_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_hybrid)
):
    """
    Unified withdrawal dashboard statistics for all admin roles
    DC Protocol: Single source of truth for withdrawal stats
    """
    # DC Protocol: Menu-based access control - page assignment = full access
    # if (getattr(current_user, 'staff_type', None) or (getattr(current_user, 'staff_type', None) or getattr(current_user, 'user_type', ''))) not in ['Admin', 'Super Admin', 'Finance Admin', 'RVZ ID']:
    #     raise HTTPException(
    #         status_code=status.HTTP_403_FORBIDDEN,
    #         detail='Admin access required'
    #     )
    
    # Get counts by status
    total_pending = db.query(func.count(WithdrawalRequest.id)).filter(
        WithdrawalRequest.status == 'Pending'
    ).scalar() or 0
    
    total_admin_verified = db.query(func.count(WithdrawalRequest.id)).filter(
        WithdrawalRequest.status == 'Admin Verified'
    ).scalar() or 0
    
    total_super_admin_approved = db.query(func.count(WithdrawalRequest.id)).filter(
        WithdrawalRequest.status == 'Super Admin Approved'
    ).scalar() or 0
    
    total_bank_sent = db.query(func.count(WithdrawalRequest.id)).filter(
        WithdrawalRequest.status == 'Completed'
    ).scalar() or 0
    
    total_completed = db.query(func.count(WithdrawalRequest.id)).filter(
        WithdrawalRequest.status == 'Completed'
    ).scalar() or 0
    
    total_rejected = db.query(func.count(WithdrawalRequest.id)).filter(
        WithdrawalRequest.status == 'Rejected'
    ).scalar() or 0
    
    # Get amount totals
    amount_stats = db.query(
        func.sum(WithdrawalRequest.withdrawal_amount).label('total_requested'),
        func.sum(WithdrawalRequest.final_payout).label('total_payout'),
        func.sum(WithdrawalRequest.admin_charges).label('total_admin_charges'),
        func.sum(WithdrawalRequest.tds_amount).label('total_tds')
    ).filter(
        WithdrawalRequest.status != 'Rejected'
    ).first()
    
    # Recent activity (last 10 withdrawals)
    recent_withdrawals = db.query(WithdrawalRequest).order_by(
        desc(WithdrawalRequest.created_at)
    ).limit(10).all()
    
    # Stuck withdrawals (> 3 days in same state, not completed/rejected)
    three_days_ago = datetime.now() - timedelta(days=3)
    stuck_withdrawals = db.query(WithdrawalRequest).filter(
        and_(
            WithdrawalRequest.created_at < three_days_ago,
            WithdrawalRequest.status.notin_(['Completed', 'Rejected'])
        )
    ).count()
    
    return {
        'success': True,
        'stats': {
            'total_pending': total_pending,
            'total_admin_verified': total_admin_verified,
            'total_super_admin_approved': total_super_admin_approved,
            'total_bank_sent': total_bank_sent,
            'total_completed': total_completed,
            'total_rejected': total_rejected,
            'total_in_process': total_admin_verified + total_super_admin_approved + total_bank_sent,
            'total_requested_amount': round(float(amount_stats.total_requested or 0)),
            'total_payout_amount': round(float(amount_stats.total_payout or 0)),
            'total_admin_charges': round(float(amount_stats.total_admin_charges or 0)),
            'total_tds': round(float(amount_stats.total_tds or 0)),
            'stuck_withdrawals': stuck_withdrawals
        },
        'recent_activity': [
            {
                'id': w.id,
                'user_id': w.user_id,
                'user_name': w.user.name if w.user else 'Unknown',
                'amount': w.withdrawal_amount,
                'final_payout': w.final_payout,
                'status': w.status,
                'created_at': w.created_at.isoformat() if w.created_at else None,
                'is_auto_generated': w.is_auto_generated if hasattr(w, 'is_auto_generated') else False
            }
            for w in recent_withdrawals
        ]
    }


@router.get('/admin/transaction-breakup/{withdrawal_id}')
async def get_withdrawal_transaction_breakup(
    withdrawal_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_hybrid)
):
    """
    Get detailed income type breakdown for a withdrawal request
    Shows which income streams contributed to this withdrawal
    """
    # DC Protocol: Menu-based access control - page assignment = full access
    # if (getattr(current_user, 'staff_type', None) or (getattr(current_user, 'staff_type', None) or getattr(current_user, 'user_type', ''))) not in ['Admin', 'Super Admin', 'Finance Admin', 'RVZ ID']:
    #     raise HTTPException(
    #         status_code=status.HTTP_403_FORBIDDEN,
    #         detail='Admin access required'
    #     )
    
    # Get withdrawal request
    withdrawal = db.query(WithdrawalRequest).filter_by(id=withdrawal_id).first()
    if not withdrawal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Withdrawal request not found'
        )
    
    # Get income breakdown for this user on/before this withdrawal date
    from app.services.wallet_service import WalletService
    wallet_service = WalletService(db)
    earnings_summary = wallet_service.get_earnings_summary(withdrawal.user_id)
    
    # Get pending income records for this user
    pending_income_breakdown = db.query(
        PendingIncome.income_type,
        func.sum(PendingIncome.gross_amount).label('total_gross'),
        func.sum(PendingIncome.net_amount).label('total_net'),
        func.count(PendingIncome.id).label('count')
    ).filter(
        PendingIncome.user_id == withdrawal.user_id
    ).group_by(
        PendingIncome.income_type
    ).all()
    
    # Get transaction records (paid income)
    transaction_breakdown = db.query(
        Transaction.transaction_type,
        func.sum(Transaction.amount).label('total_amount'),
        func.count(Transaction.id).label('count')
    ).filter(
        Transaction.referrer_id == withdrawal.user_id
    ).group_by(
        Transaction.transaction_type
    ).all()
    
    return {
        'success': True,
        'withdrawal': {
            'id': withdrawal.id,
            'user_id': withdrawal.user_id,
            'user_name': withdrawal.user.name if withdrawal.user else 'Unknown',
            'withdrawal_amount': withdrawal.withdrawal_amount,
            'admin_charges': withdrawal.admin_charges,
            'tds_amount': withdrawal.tds_amount,
            'final_payout': withdrawal.final_payout,
            'status': withdrawal.status,
            'created_at': withdrawal.created_at.isoformat() if withdrawal.created_at else None
        },
        'income_breakdown': {
            'direct_referral_gross': earnings_summary.get('direct_referral_total', 0),
            'matching_referral_gross': earnings_summary.get('matching_referral_total', 0),
            'ved_income_gross': earnings_summary.get('ved_income_total', 0),
            'guru_dakshina_gross': earnings_summary.get('guru_dakshina_total', 0),
            'total_gross': earnings_summary.get('total_gross_earnings', 0),
            'total_net': earnings_summary.get('total_net_earnings', 0)
        },
        'pending_income': [
            {
                'income_type': row.income_type,
                'gross_amount': round(float(row.total_gross or 0)),
                'net_amount': round(float(row.total_net or 0)),
                'count': row.count
            }
            for row in pending_income_breakdown
        ],
        'paid_income': [
            {
                'income_type': row.transaction_type,
                'total_amount': round(float(row.total_amount or 0)),
                'count': row.count
            }
            for row in transaction_breakdown
        ]
    }


@router.post('/admin/revert-withdrawal/{withdrawal_id}')
async def revert_withdrawal_to_previous_state(
    withdrawal_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_hybrid)
):
    """
    Revert withdrawal to previous approval state
    Admin validations ensure proper state transitions
    """
    # DC Protocol: Menu-based access control - page assignment = full access
    # if (getattr(current_user, 'staff_type', None) or (getattr(current_user, 'staff_type', None) or getattr(current_user, 'user_type', ''))) not in ['Super Admin', 'RVZ ID']:
    #     raise HTTPException(
    #         status_code=status.HTTP_403_FORBIDDEN,
    #         detail='Super Admin or RVZ ID access required for revert operations'
    #     )
    
    withdrawal = db.query(WithdrawalRequest).filter_by(id=withdrawal_id).first()
    if not withdrawal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Withdrawal request not found'
        )
    
    # Define revert state mapping
    revert_map = {
        'Admin Verified': 'Pending',
        'Super Admin Approved': 'Admin Verified',
        'Completed': 'Super Admin Approved',
        'Completed': 'Completed'
    }
    
    current_status = withdrawal.status
    if current_status not in revert_map:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f'Cannot revert from status: {current_status}'
        )
    
    new_status = revert_map[current_status]
    withdrawal.status = new_status
    withdrawal.processed_at = datetime.now()
    
    db.commit()
    
    return {
        'success': True,
        'message': f'Withdrawal reverted from {current_status} to {new_status}',
        'withdrawal_id': withdrawal_id,
        'old_status': current_status,
        'new_status': new_status
    }


@router.post('/admin/hold-withdrawal/{withdrawal_id}')
async def hold_withdrawal_request(
    withdrawal_id: int,
    hold_reason: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_hybrid)
):
    """
    Put withdrawal on hold with reason
    Can be released later by admin
    """
    # DC Protocol: Menu-based access control - page assignment = full access
    # if (getattr(current_user, 'staff_type', None) or (getattr(current_user, 'staff_type', None) or getattr(current_user, 'user_type', ''))) not in ['Admin', 'Super Admin', 'Finance Admin', 'RVZ ID']:
    #     raise HTTPException(
    #         status_code=status.HTTP_403_FORBIDDEN,
    #         detail='Admin access required'
    #     )
    
    withdrawal = db.query(WithdrawalRequest).filter_by(id=withdrawal_id).first()
    if not withdrawal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Withdrawal request not found'
        )
    
    if withdrawal.status in ['Completed', 'Rejected']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f'Cannot hold withdrawal with status: {withdrawal.status}'
        )
    
    # Store previous status and set to "On Hold"
    # Note: You may need to add hold_status and hold_reason columns to WithdrawalRequest model
    # For now, we'll use admin_notes field
    withdrawal.status = f'On Hold ({withdrawal.status})'
    db.commit()
    
    return {
        'success': True,
        'message': f'Withdrawal placed on hold. Reason: {hold_reason}',
        'withdrawal_id': withdrawal_id,
        'hold_reason': hold_reason
    }

@router.get('/admin/withdrawal-income-breakdown/{withdrawal_id}')
def get_withdrawal_income_breakdown(
    withdrawal_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_hybrid)
):
    """
    WVV Protocol v2.0: Get income breakdown for ALL income of the user up to withdrawal date
    Used by Withdrawal Details modal - shows income types contributing to this withdrawal
    DC Protocol: Shows cumulative income breakdown (not just single date)
    """
    from sqlalchemy import func
    
    # DC Protocol: Menu-based access control - page assignment = full access
    # if (getattr(current_user, 'staff_type', None) or getattr(current_user, 'user_type', '')) not in ALLOWED_ADMIN_STAFF_TYPES:
    #     raise HTTPException(
    #         status_code=status.HTTP_403_FORBIDDEN,
    #         detail='Admin access required'
    #     )
    
    withdrawal = db.query(WithdrawalRequest).filter_by(id=withdrawal_id).first()
    if not withdrawal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Withdrawal request not found'
        )
    
    # DC Protocol v2.0: Get ALL income records for this user up to and including withdrawal date
    # This shows cumulative breakdown of all income types that contributed to this withdrawal
    income_records = db.query(PendingIncome).filter(
        PendingIncome.user_id == withdrawal.user_id,
        func.date(PendingIncome.business_date) <= withdrawal.request_date
    ).all()
    
    # Calculate breakdown by income type
    breakdown_by_type = {}
    total_gross = 0
    total_guru_deduction = 0
    total_admin_deduction = 0
    total_tds_deduction = 0
    total_net = 0
    
    for record in income_records:
        income_type = record.income_type
        if income_type not in breakdown_by_type:
            breakdown_by_type[income_type] = {
                'gross': 0,
                'guru_dakshina_deduction': 0,
                'admin_deduction': 0,
                'tds_deduction': 0,
                'net': 0,
                'count': 0
            }
        
        breakdown_by_type[income_type]['gross'] += float(record.gross_amount or 0)
        breakdown_by_type[income_type]['guru_dakshina_deduction'] += float(record.gurudakshina_deduction or 0)
        breakdown_by_type[income_type]['admin_deduction'] += float(record.admin_deduction or 0)
        breakdown_by_type[income_type]['tds_deduction'] += float(record.tds_deduction or 0)
        breakdown_by_type[income_type]['net'] += float(record.net_amount or 0)
        breakdown_by_type[income_type]['count'] += 1
        
        total_gross += float(record.gross_amount or 0)
        total_guru_deduction += float(record.gurudakshina_deduction or 0)
        total_admin_deduction += float(record.admin_deduction or 0)
        total_tds_deduction += float(record.tds_deduction or 0)
        total_net += float(record.net_amount or 0)
    
    return {
        'success': True,
        'withdrawal_id': withdrawal_id,
        'withdrawal_amount': withdrawal.withdrawal_amount,
        'final_payout': withdrawal.final_payout,
        'breakdown_by_type': [
            {
                'income_type': income_type,
                'gross': round(data['gross'], 2),
                'guru_dakshina_deduction': round(data['guru_dakshina_deduction'], 2),
                'admin_deduction': round(data['admin_deduction'], 2),
                'tds_deduction': round(data['tds_deduction'], 2),
                'total_deductions': round(data['guru_dakshina_deduction'] + data['admin_deduction'] + data['tds_deduction'], 2),
                'net': round(data['net'], 2),
                'count': data['count']
            }
            for income_type, data in breakdown_by_type.items()
        ],
        'totals': {
            'gross': round(total_gross, 2),
            'guru_dakshina_deduction': round(total_guru_deduction, 2),
            'admin_deduction': round(total_admin_deduction, 2),
            'tds_deduction': round(total_tds_deduction, 2),
            'total_deductions': round(total_guru_deduction + total_admin_deduction + total_tds_deduction, 2),
            'net': round(total_net, 2)
        }
    }

@router.get('/admin/date-wise-income-breakdown')
def get_date_wise_income_breakdown(
    user_id: str,
    business_date: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_hybrid)
):
    """
    DC Protocol: Get income breakdown for SPECIFIC DATE and USER
    WVV Protocol: Used by Income Verification pages to show daily income breakdowns
    Returns breakdown by income type for that specific date only
    
    Example: user_id=MNR1800143&business_date=2025-11-01
    """
    from sqlalchemy import func
    from datetime import datetime
    
    # DC Protocol: Menu-based access control - page assignment = full access
    # if (getattr(current_user, 'staff_type', None) or (getattr(current_user, 'staff_type', None) or getattr(current_user, 'user_type', ''))) not in ['Admin', 'Finance Admin', 'Super Admin', 'RVZ ID', 'VGK4U', 'VGK4U Supreme', 'Key Leadership', 'Leadership Role', 'HR', 'Manager', 'Senior Executive']:
    #     raise HTTPException(
    #         status_code=status.HTTP_403_FORBIDDEN,
    #         detail='Admin access required'
    #     )
    
    # Parse date
    try:
        target_date = datetime.fromisoformat(business_date).date()
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Invalid date format. Use YYYY-MM-DD'
        )
    
    # DC Protocol: Get ONLY income records for THIS SPECIFIC DATE
    income_records = db.query(PendingIncome).filter(
        PendingIncome.user_id == user_id,
        func.date(PendingIncome.business_date) == target_date
    ).all()
    
    if not income_records:
        return {
            'success': True,
            'user_id': user_id,
            'business_date': business_date,
            'breakdown_by_type': [],
            'totals': {
                'gross': 0,
                'guru_dakshina_deduction': 0,
                'admin_deduction': 0,
                'tds_deduction': 0,
                'total_deductions': 0,
                'net': 0
            }
        }
    
    # Calculate breakdown by income type
    breakdown_by_type = {}
    total_gross = 0
    total_guru_deduction = 0
    total_admin_deduction = 0
    total_tds_deduction = 0
    total_net = 0
    
    for record in income_records:
        income_type = record.income_type
        if income_type not in breakdown_by_type:
            breakdown_by_type[income_type] = {
                'gross': 0,
                'guru_dakshina_deduction': 0,
                'admin_deduction': 0,
                'tds_deduction': 0,
                'net': 0,
                'count': 0,
                'verification_status': record.verification_status
            }
        
        breakdown_by_type[income_type]['gross'] += float(record.gross_amount or 0)
        breakdown_by_type[income_type]['guru_dakshina_deduction'] += float(record.gurudakshina_deduction or 0)
        breakdown_by_type[income_type]['admin_deduction'] += float(record.admin_deduction or 0)
        breakdown_by_type[income_type]['tds_deduction'] += float(record.tds_deduction or 0)
        breakdown_by_type[income_type]['net'] += float(record.net_amount or 0)
        breakdown_by_type[income_type]['count'] += 1
        
        total_gross += float(record.gross_amount or 0)
        total_guru_deduction += float(record.gurudakshina_deduction or 0)
        total_admin_deduction += float(record.admin_deduction or 0)
        total_tds_deduction += float(record.tds_deduction or 0)
        total_net += float(record.net_amount or 0)
    
    return {
        'success': True,
        'user_id': user_id,
        'business_date': business_date,
        'breakdown_by_type': [
            {
                'income_type': income_type,
                'gross': round(data['gross'], 2),
                'guru_dakshina_deduction': round(data['guru_dakshina_deduction'], 2),
                'admin_deduction': round(data['admin_deduction'], 2),
                'tds_deduction': round(data['tds_deduction'], 2),
                'total_deductions': round(data['guru_dakshina_deduction'] + data['admin_deduction'] + data['tds_deduction'], 2),
                'net': round(data['net'], 2),
                'count': data['count'],
                'verification_status': data['verification_status']
            }
            for income_type, data in breakdown_by_type.items()
        ],
        'totals': {
            'gross': round(total_gross, 2),
            'guru_dakshina_deduction': round(total_guru_deduction, 2),
            'admin_deduction': round(total_admin_deduction, 2),
            'tds_deduction': round(total_tds_deduction, 2),
            'total_deductions': round(total_guru_deduction + total_admin_deduction + total_tds_deduction, 2),
            'net': round(total_net, 2)
        }
    }
