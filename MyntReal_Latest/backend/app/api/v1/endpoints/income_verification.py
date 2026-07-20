"""
Income Verification Workflow endpoints

DC Protocol Feb 2026: 2-Step Staff-Only Workflow
- Step 1: Staff with page access VALIDATES (Pending → Staff Validated)
- Step 2: Accounts/VGK Supreme APPROVES and marks as PAID (Staff Validated → Completed)

Legacy 3-step Admin workflow preserved for backward compatibility but deprecated.
"""


import logging

from fastapi import APIRouter, Depends, HTTPException, status, Response, Body
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from typing import List, Optional

logger = logging.getLogger(__name__)
from pydantic import BaseModel
from datetime import datetime, date

from app.core.database import get_db
from app.core.security import (
    get_current_admin_user,
    get_current_user_hybrid,
    get_current_admin_user_hybrid,
    require_super_admin,
    require_finance_admin,
    require_staff_accounts_or_vgk,
    require_staff_with_page_access
)
from app.models.user import User
from app.models.transaction import PendingIncome, Transaction
from app.models.base import get_indian_time
from app.core.audit import AuditLogger
from app.core.scheduler import check_direct_referrals_both_sides
from decimal import Decimal
from app.core.constants import ADMIN_DEDUCTION_RATE, TDS_DEDUCTION_RATE, TOTAL_DEDUCTION_RATE, NET_PAYOUT_RATE

router = APIRouter()


def _resolve_actor_id(current_user) -> str:
    from app.models.staff import StaffEmployee
    if isinstance(current_user, StaffEmployee):
        return str(current_user.emp_code or current_user.id)
    return str(current_user.id)

INCOME_TYPE_REBRAND = {
    'Direct Referral': 'Direct Facilitation',
    'Matching Referral': 'Group Performance Recognition',
    'Ved Income': 'VED Leadership Recognition',
    'Guru Dakshina': 'Mentorship Contribution Benefit'
}

def get_display_income_type(db_type: str) -> str:
    return INCOME_TYPE_REBRAND.get(db_type, db_type)

def add_no_cache_headers(response: Response):
    """Add cache-control headers to prevent browser caching of admin data"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

class VerifyIncomeRequest(BaseModel):
    pending_income_ids: List[int]
    notes: Optional[str] = None
    transaction_reference: Optional[str] = None
    comments: Optional[str] = None

class ManualIncomeCalculationRequest(BaseModel):
    calculation_date: str  # Format: YYYY-MM-DD

# ===== ADMIN VERIFICATION =====

@router.get("/admin/pending-incomes")
async def get_pending_incomes_for_admin(
    response: Response,
    status_filter: str = 'Pending',
    user_id: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    current_admin: User = Depends(get_current_admin_user_hybrid),
    db: Session = Depends(get_db)
):
    """
    Get pending incomes for Admin verification with filters - NO CACHE
    
    Filters:
    - status_filter: Filter by verification status (default: 'Pending')
    - user_id: Filter by specific user ID
    - from_date: Filter incomes from this date (format: YYYY-MM-DD)
    - to_date: Filter incomes until this date (format: YYYY-MM-DD)
    """
    add_no_cache_headers(response)
    try:
        # Start with base query
        query = db.query(PendingIncome)
        
        # Apply status filter only if provided and not "All"
        if status_filter and status_filter.strip() and status_filter.lower() != 'all':
            query = query.filter(PendingIncome.verification_status == status_filter)
        
        # Filter by user_id if provided (for RVZ Supreme modal details)
        if user_id:
            query = query.filter(PendingIncome.user_id == user_id)
        
        # Filter by date range
        if from_date:
            from_date_obj = datetime.strptime(from_date, '%Y-%m-%d').date()
            query = query.filter(PendingIncome.business_date >= from_date_obj)
        
        if to_date:
            to_date_obj = datetime.strptime(to_date, '%Y-%m-%d').date()
            # Add one day to include the entire to_date
            query = query.filter(PendingIncome.business_date <= to_date_obj)
        
        query = query.order_by(PendingIncome.business_date.desc())
        
        pending_incomes = query.all()
        
        # Get user names from User table for each pending income
        user_ids = list(set([pi.user_id for pi in pending_incomes]))
        users = db.query(User).filter(User.id.in_(user_ids)).all() if user_ids else []
        user_map = {u.id: u.name for u in users}
        
        return {
            "success": True,
            "count": len(pending_incomes),
            "data": [
                {
                    "id": pi.id,
                    "user_id": pi.user_id,
                    "user_name": user_map.get(pi.user_id, "Unknown"),
                    "income_type": pi.income_type,
                    "gross_amount": round(float(pi.gross_amount)),
                    "net_amount": round(float(pi.net_amount)),
                    "business_date": pi.business_date.isoformat(),
                    "verification_status": pi.verification_status
                }
                for pi in pending_incomes
            ]
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid date format. Use YYYY-MM-DD. Error: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Server error: {str(e)}"
        )

@router.post("/admin/verify")
async def admin_verify_incomes(
    request: VerifyIncomeRequest,
    current_admin: User = Depends(get_current_admin_user_hybrid),
    db: Session = Depends(get_db)
):
    """Admin verifies pending incomes"""
    try:
        verified_count = 0
        
        for income_id in request.pending_income_ids:
            pending_income = db.query(PendingIncome).filter(
                PendingIncome.id == income_id,
                PendingIncome.verification_status == 'Pending'
            ).first()
            
            if pending_income:
                pending_income.verification_status = 'Admin Verified'
                pending_income.admin_verified_by_id = _resolve_actor_id(current_admin)
                pending_income.admin_verified_at = get_indian_time()
                if request.notes:
                    pending_income.notes = request.notes
                verified_count += 1
        
        db.commit()
        
        AuditLogger.log_action(
            db=db,
            user=current_admin,
            action='ADMIN_VERIFY_INCOMES',
            resource_type='PendingIncome',
            details={"verified_count": verified_count, "income_ids": request.pending_income_ids}
        )
        
        return {
            "success": True,
            "message": f"Admin verified {verified_count} pending incomes",
            "verified_count": verified_count
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Server error: {str(e)}"
        )

# ===== SUPER ADMIN VERIFICATION =====

@router.get("/super-admin/pending-incomes")
async def get_admin_verified_incomes(
    response: Response,
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db)
):
    """Get admin-verified incomes for Super Admin verification - NO CACHE"""
    add_no_cache_headers(response)
    try:
        pending_incomes = db.query(PendingIncome).filter(
            PendingIncome.verification_status == 'Admin Verified'
        ).order_by(PendingIncome.business_date.desc()).all()
        
        return {
            "success": True,
            "count": len(pending_incomes),
            "data": [
                {
                    "id": pi.id,
                    "user_id": pi.user_id,
                    "income_type": pi.income_type,
                    "gross_amount": round(float(pi.gross_amount)),
                    "net_amount": round(float(pi.net_amount)),
                    "business_date": pi.business_date.isoformat(),
                    "verification_status": pi.verification_status,
                    "admin_verified_by": pi.admin_verified_by_id,
                    "admin_verified_at": pi.admin_verified_at.isoformat() if pi.admin_verified_at else None
                }
                for pi in pending_incomes
            ]
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Server error: {str(e)}"
        )

@router.post("/super-admin/verify")
async def super_admin_verify_incomes(
    request: VerifyIncomeRequest,
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db)
):
    """Super Admin verifies admin-verified incomes and creates Transfer Queue entries"""
    try:
        from app.models.withdrawal import TransferQueue
        
        verified_count = 0
        queue_created = 0
        
        for income_id in request.pending_income_ids:
            pending_income = db.query(PendingIncome).filter(
                PendingIncome.id == income_id,
                PendingIncome.verification_status == 'Admin Verified'
            ).first()
            
            if pending_income:
                # Update pending income status
                pending_income.verification_status = 'Super Admin Verified'
                pending_income.super_admin_verified_by_id = _resolve_actor_id(current_user)
                pending_income.super_admin_verified_at = get_indian_time()
                if request.notes:
                    pending_income.notes = (pending_income.notes or '') + f"\nSuper Admin: {request.notes}"
                verified_count += 1
                
                # WVV WORKFLOW: Create Transfer Queue entry for Finance Admin
                # Check if queue entry already exists (prevent duplicates)
                existing_queue = db.query(TransferQueue).filter(
                    TransferQueue.pending_income_id == pending_income.id
                ).first()
                
                if not existing_queue:
                    transfer_queue_entry = TransferQueue(
                        pending_income_id=pending_income.id,
                        user_id=pending_income.user_id,
                        income_type=pending_income.income_type,
                        net_amount=pending_income.net_amount,
                        withdrawal_wallet_amount=pending_income.withdrawal_wallet_amount,
                        upgrade_wallet_amount=pending_income.upgraded_wallet_amount,
                        business_date=pending_income.business_date,
                        status='Awaiting Finance',
                        created_at=get_indian_time(),
                        created_by_id=_resolve_actor_id(current_user),
                        notes=request.notes
                    )
                    db.add(transfer_queue_entry)
                    queue_created += 1
        
        db.commit()
        
        AuditLogger.log_action(
            db=db,
            user=current_user,
            action='SUPER_ADMIN_VERIFY_INCOMES',
            resource_type='PendingIncome',
            details={
                "verified_count": verified_count,
                "queue_created": queue_created,
                "income_ids": request.pending_income_ids
            }
        )
        
        return {
            "success": True,
            "message": f"Super Admin verified {verified_count} incomes, created {queue_created} transfer queue entries",
            "verified_count": verified_count,
            "queue_created": queue_created
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Server error: {str(e)}"
        )

# ===== FINANCE ADMIN PAYMENT =====

@router.get("/finance-admin/transfer-queue")
async def get_transfer_queue(
    response: Response,
    current_finance_admin: User = Depends(require_finance_admin),
    db: Session = Depends(get_db)
):
    """Get Transfer Queue entries for Finance Admin payment processing - WVV WORKFLOW"""
    add_no_cache_headers(response)
    try:
        from app.models.withdrawal import TransferQueue
        
        # Get all awaiting finance entries
        queue_entries = db.query(TransferQueue).filter(
            TransferQueue.status == 'Awaiting Finance'
        ).order_by(TransferQueue.business_date.desc()).all()
        
        return {
            "success": True,
            "count": len(queue_entries),
            "data": [
                {
                    "id": q.id,
                    "pending_income_id": q.pending_income_id,
                    "user_id": q.user_id,
                    "income_type": q.income_type,
                    "net_amount": round(float(q.net_amount)),
                    "withdrawal_wallet_amount": round(float(q.withdrawal_wallet_amount)),
                    "upgrade_wallet_amount": round(float(q.upgrade_wallet_amount)),
                    "business_date": q.business_date.isoformat(),
                    "status": q.status,
                    "created_at": q.created_at.isoformat() if q.created_at else None,
                    "notes": q.notes
                }
                for q in queue_entries
            ]
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Server error: {str(e)}"
        )

@router.get("/finance-admin/verified-incomes")
async def get_verified_incomes_for_payment(
    response: Response,
    current_finance_admin: User = Depends(require_finance_admin),
    db: Session = Depends(get_db)
):
    """DEPRECATED: Use /finance-admin/transfer-queue instead - NO CACHE"""
    add_no_cache_headers(response)
    try:
        pending_incomes = db.query(PendingIncome).filter(
            PendingIncome.verification_status == 'Super Admin Verified'
        ).order_by(PendingIncome.business_date.desc()).all()
        
        return {
            "success": True,
            "count": len(pending_incomes),
            "data": [
                {
                    "id": pi.id,
                    "user_id": pi.user_id,
                    "income_type": pi.income_type,
                    "gross_amount": round(float(pi.gross_amount)),
                    "admin_deduction": round(float(pi.admin_deduction)),
                    "tds_deduction": round(float(pi.tds_deduction)),
                    "net_amount": round(float(pi.net_amount)),
                    "withdrawal_wallet_amount": round(float(pi.withdrawal_wallet_amount)),
                    "upgraded_wallet_amount": round(float(pi.upgraded_wallet_amount)),
                    "business_date": pi.business_date.isoformat(),
                    "verification_status": pi.verification_status
                }
                for pi in pending_incomes
            ]
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Server error: {str(e)}"
        )

@router.post("/finance-admin/process-payment")
async def process_verified_payments(
    request: VerifyIncomeRequest,
    current_finance_admin: User = Depends(require_finance_admin),
    db: Session = Depends(get_db)
):
    """
    STANDARD WORKFLOW - Finance Admin processes payments (SAME as RVZ Supreme)
    
    Flow:
    1. Instant wallet sync (real-time, not nightly)
    2. Auto-create withdrawal with ₹1,000 minimum rule
    3. Mark income as 'Completed'
    
    ONLY DIFFERENCE from RVZ Supreme: Income went through Admin → Super Admin → Finance
    """
    try:
        from app.models.withdrawal import WithdrawalRequest, TransferQueue
        from datetime import date
        
        processed_count = 0
        total_paid = Decimal('0')
        withdrawal_results = []
        
        # Support both queue_entry_ids (new) and pending_income_ids (backward compatibility)
        entry_ids = getattr(request, 'queue_entry_ids', None) or request.pending_income_ids
        
        # Group entries by user for batch processing
        users_map = {}
        
        for entry_id in entry_ids:
            # Try to get from transfer queue first
            queue_entry = db.query(TransferQueue).filter(
                TransferQueue.id == entry_id,
                TransferQueue.status == 'Awaiting Finance'
            ).first()
            
            # Fallback: try pending_income directly
            if not queue_entry:
                pending_income = db.query(PendingIncome).filter(
                    PendingIncome.id == entry_id,
                    PendingIncome.verification_status == 'Super Admin Verified'
                ).first()
            else:
                pending_income = db.query(PendingIncome).filter(
                    PendingIncome.id == queue_entry.pending_income_id
                ).first()
            
            if pending_income:
                user_id = pending_income.user_id
                if user_id not in users_map:
                    users_map[user_id] = {'incomes': [], 'queues': []}
                users_map[user_id]['incomes'].append(pending_income)
                if queue_entry:
                    users_map[user_id]['queues'].append(queue_entry)
        
        # Process each user: mark as 'Completed' → auto-create withdrawal
        # CRITICAL: We DON'T use wallet_sync_service here because it would promote
        # ALL pending incomes for the user, bypassing Admin/Super Admin approval.
        # Instead, we manually mark ONLY the selected incomes and create withdrawals.
        
        for user_id, data in users_map.items():
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                continue
            
            # STEP 1: Mark ONLY selected incomes as 'Completed'
            # This respects the approval chain (only processes Finance-approved incomes)
            total_for_user = Decimal('0')
            for income in data['incomes']:
                income.verification_status = 'Completed'
                income.accounts_paid_by_id = None
                income.accounts_paid_at = get_indian_time()
                staff_id = str(getattr(current_finance_admin, 'emp_code', None) or current_finance_admin.id)
                if request.notes:
                    income.notes = (income.notes or '') + f"\nStaff {staff_id}: {request.notes}"
                else:
                    income.notes = (income.notes or '') + f"\nProcessed by Staff: {staff_id}"
                total_for_user += income.net_amount
                processed_count += 1
                total_paid += income.net_amount
                # DC-STATUTORY-GL-001: post TDS + admin to statutory GL accounts
                try:
                    from app.services.staff_accounts_service import LedgerPostingService as _LPS
                    _biz = income.business_date
                    _LPS.auto_post_statutory_deductions(
                        db=db,
                        company_id=int(getattr(user, 'company_id', None) or 1),
                        tds_amount=income.tds_deduction,
                        admin_amount=income.admin_deduction,
                        txn_date=_biz.date() if hasattr(_biz, 'date') else _biz,
                        ref_type='PENDING_INCOME',
                        ref_id=income.id,
                        ref_number=f'PI-{income.id:08d}',
                        narration=f'{income.income_type} statutory deductions — {income.user_id}',
                        created_by_id=None,
                    )
                except Exception as _sgl_e:
                    logger.warning(f'[DC-STATUTORY-GL-001] GL post non-fatal for PI#{income.id}: {_sgl_e}')

            # STEP 2: Credit withdrawable wallet (CRITICAL: Must credit before creating withdrawal!)
            # Use withdrawal_wallet_amount (already calculated with package splits)
            withdrawal_amount = sum(int(inc.withdrawal_wallet_amount) for inc in data['incomes'])
            
            # DC Protocol Phase 1.7: Manually credit withdrawable wallet
            # This is necessary because we're not using wallet_sync_service (which would bypass approvals)
            from sqlalchemy import text
            db.execute(
                text("""
                    UPDATE "user"
                    SET withdrawable_wallet = COALESCE(withdrawable_wallet, 0) + :amount
                    WHERE id = :user_id
                """),
                {"amount": withdrawal_amount, "user_id": user_id}
            )
            
            # STEP 3: Auto-create withdrawal with ₹1,000 minimum rule
            if withdrawal_amount > 0:
                # DC_WITHDRAW_001: Skip if user already has an active withdrawal
                from app.models.withdrawal import get_active_withdrawal
                _existing_wr = get_active_withdrawal(db, user.id)
                if _existing_wr:
                    logger.info(f"⏭️  {user.id}: Skipping withdrawal creation — active withdrawal #{_existing_wr.id} [{_existing_wr.status}] already exists")
                    withdrawal_amount = 0

            if withdrawal_amount > 0:
                # ₹1,000 minimum rule
                withdrawal_status = 'On Hold' if withdrawal_amount < 1000 else 'Pending'
                
                withdrawal = WithdrawalRequest(
                    user_id=user.id,
                    withdrawal_amount=withdrawal_amount,
                    admin_charges=0,
                    tds_amount=0,
                    final_payout=withdrawal_amount,
                    request_date=date.today(),
                    status=withdrawal_status,
                    is_auto_generated=True,
                    bank_name=user.bank_name or 'Not Set',
                    account_number=user.bank_account_number or 'Not Set',
                    ifsc_code=user.bank_ifsc_code or 'Not Set',
                    account_holder_name=user.bank_account_holder or user.name
                )
                
                db.add(withdrawal)
                
                withdrawal_results.append({
                    "user_id": user.id,
                    "amount_approved": float(total_for_user),
                    "withdrawal_created": withdrawal.id,
                    "withdrawal_amount": withdrawal_amount,
                    "withdrawal_status": withdrawal_status
                })
            
            # Update transfer queues
            for queue in data['queues']:
                queue.status = 'Completed'
                queue.processed_at = get_indian_time()
                queue.processed_by_id = None
        
        db.commit()
        
        AuditLogger.log_action(
            db=db,
            user=current_finance_admin,
            action='FINANCE_ADMIN_PROCESS_PAYMENT',
            resource_type='TransferQueue',
            details={
                "processed_count": processed_count,
                "total_paid": round(float(total_paid)),
                "withdrawals_created": len(withdrawal_results),
                "entry_ids": entry_ids
            }
        )
        
        return {
            "success": True,
            "message": f"Standard Flow: {processed_count} income(s) approved → {len(withdrawal_results)} withdrawal(s) auto-created",
            "processed_count": processed_count,
            "total_paid": round(float(total_paid)),
            "withdrawal_results": withdrawal_results,
            "workflow": "Admin → Super Admin → Finance (with instant wallet sync + auto-withdrawal)"
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Server error: {str(e)}"
        )


# ===== DC PROTOCOL FEB 2026: STAFF-ONLY 2-STEP WORKFLOW =====
# Step 1: Staff Validates (Pending → Staff Validated)
# Step 2: Accounts/VGK Approves (Staff Validated → Completed + Paid)

STAFF_WORKFLOW_CUTOFF = date(2026, 2, 12)

STATUS_PRIORITY = {'Pending': 0, 'Staff Validated': 1, 'Completed': 2}

def _get_kyc_status(user):
    if not user:
        return 'Unknown'
    kyc_approved = getattr(user, 'kyc_approved', False)
    if kyc_approved:
        return 'Approved'
    has_aadhar = bool(getattr(user, 'aadhar_front', None) or getattr(user, 'aadhar_back', None))
    has_pan = bool(getattr(user, 'pan_card', None))
    has_bank = bool(getattr(user, 'bank_account_number', None))
    if has_aadhar or has_pan or has_bank:
        return 'Submitted'
    return 'Pending'

def _get_group_eligibility(db, user_ids):
    import logging
    logger = logging.getLogger(__name__)
    result = {}
    for uid in user_ids:
        try:
            eligibility = check_direct_referrals_both_sides(db, uid, return_details=True)
            if eligibility.get('is_eligible'):
                result[uid] = 'Yes'
            else:
                group_a = eligibility.get('group_a_points', 0)
                group_b = eligibility.get('group_b_points', 0)
                if group_a < 1.0 and group_b < 1.0:
                    result[uid] = 'No'
                elif group_a < 1.0:
                    result[uid] = 'Group A Missing'
                else:
                    result[uid] = 'Group B Missing'
        except Exception as e:
            logger.error(f"[DC-ELIGIBILITY] Error checking {uid}: {e}")
            result[uid] = 'Unknown'
    return result

def _compute_clubbed_status(incomes_list):
    statuses = set(pi.verification_status for pi in incomes_list)
    if len(statuses) == 1:
        return statuses.pop()
    lowest = min(statuses, key=lambda s: STATUS_PRIORITY.get(s, 99))
    return lowest

@router.get("/staff/pending-incomes")
async def get_pending_incomes_for_staff(
    response: Response,
    status_filter: str = 'all',
    user_id: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    income_type: Optional[str] = None,
    current_staff = Depends(require_staff_with_page_access),
    db: Session = Depends(get_db)
):
    """
    DC Protocol Feb 2026: Consolidated Income Management
    
    Default mode: Returns CLUBBED rows (1 per user per day) with combined totals.
    Each row includes all underlying income IDs for bulk validate/approve.
    
    When income_type filter is applied: UN-CLUBS and returns individual records.
    
    Status rules:
    - business_date < 2026-02-12: Always shows as 'Cleared'
    - business_date >= 2026-02-12: Shows actual status (lowest priority wins if mixed)
    """
    add_no_cache_headers(response)
    try:
        is_unclubbed = income_type and income_type.lower() != 'all'
        
        query = db.query(PendingIncome)
        
        if status_filter and status_filter.lower() != 'all':
            if status_filter == 'Cleared':
                query = query.filter(PendingIncome.business_date < STAFF_WORKFLOW_CUTOFF)
            else:
                query = query.filter(PendingIncome.verification_status == status_filter)
                query = query.filter(PendingIncome.business_date >= STAFF_WORKFLOW_CUTOFF)
        
        if user_id:
            query = query.filter(PendingIncome.user_id == user_id)
        
        if from_date:
            from_date_obj = datetime.strptime(from_date, '%Y-%m-%d').date()
            query = query.filter(PendingIncome.business_date >= from_date_obj)
        
        if to_date:
            to_date_obj = datetime.strptime(to_date, '%Y-%m-%d').date()
            query = query.filter(PendingIncome.business_date <= to_date_obj)
        
        if is_unclubbed:
            reverse_rebrand = {v: k for k, v in INCOME_TYPE_REBRAND.items()}
            db_income_type = reverse_rebrand.get(income_type, income_type)
            query = query.filter(PendingIncome.income_type == db_income_type)
        
        query = query.order_by(PendingIncome.business_date.desc(), PendingIncome.user_id)
        pending_incomes = query.all()
        
        user_ids = list(set([pi.user_id for pi in pending_incomes]))
        users = db.query(User).filter(User.id.in_(user_ids)).all() if user_ids else []
        user_map = {u.id: u.name for u in users}
        kyc_map = {u.id: _get_kyc_status(u) for u in users}
        group_eligibility_map = _get_group_eligibility(db, user_ids)
        
        stats_query = db.query(PendingIncome)
        if from_date:
            stats_query = stats_query.filter(PendingIncome.business_date >= from_date_obj)
        if to_date:
            stats_query = stats_query.filter(PendingIncome.business_date <= to_date_obj)
        if user_id:
            stats_query = stats_query.filter(PendingIncome.user_id == user_id)
        if is_unclubbed:
            stats_query = stats_query.filter(PendingIncome.income_type == db_income_type)
        all_incomes_for_stats = stats_query.all()
        
        cleared_list = []
        pending_list = []
        validated_list = []
        completed_list = []
        for pi in all_incomes_for_stats:
            bdate = pi.business_date.date() if hasattr(pi.business_date, 'date') and callable(pi.business_date.date) else pi.business_date
            if bdate < STAFF_WORKFLOW_CUTOFF:
                cleared_list.append(pi)
            elif pi.verification_status == 'Pending':
                pending_list.append(pi)
            elif pi.verification_status == 'Staff Validated':
                validated_list.append(pi)
            elif pi.verification_status == 'Completed':
                completed_list.append(pi)
        
        pending_amount = round(sum(float(pi.net_amount or 0) for pi in pending_list))
        validated_amount = round(sum(float(pi.net_amount or 0) for pi in validated_list))
        completed_amount = round(sum(float(pi.net_amount or 0) for pi in completed_list))
        cleared_amount = round(sum(float(pi.net_amount or 0) for pi in cleared_list))
        
        pending_users = len(set(pi.user_id for pi in pending_list))
        validated_users = len(set(pi.user_id for pi in validated_list))
        completed_users = len(set(pi.user_id for pi in completed_list))
        cleared_users = len(set(pi.user_id for pi in cleared_list))
        
        overall_pending_list = pending_list + validated_list
        overall_pending_users = len(set(pi.user_id for pi in overall_pending_list))
        overall_pending_amount = pending_amount + validated_amount
        
        stats = {
            'pending': len(pending_list),
            'staff_validated': len(validated_list),
            'completed': len(completed_list),
            'cleared': len(cleared_list),
            'pending_amount': pending_amount,
            'staff_validated_amount': validated_amount,
            'completed_amount': completed_amount,
            'cleared_amount': cleared_amount,
            'pending_users': pending_users,
            'validated_users': validated_users,
            'completed_users': completed_users,
            'cleared_users': cleared_users,
            'overall_pending_users': overall_pending_users,
            'overall_pending_amount': overall_pending_amount,
            'overall_pending_rows': len(pending_list) + len(validated_list),
            'total_gross': round(sum(float(pi.gross_amount or 0) for pi in all_incomes_for_stats)),
            'total_net': round(sum(float(pi.net_amount or 0) for pi in all_incomes_for_stats))
        }
        
        if is_unclubbed:
            data = []
            for pi in pending_incomes:
                bdate = pi.business_date.date() if hasattr(pi.business_date, 'date') and callable(pi.business_date.date) else pi.business_date
                display_status = 'Cleared' if bdate < STAFF_WORKFLOW_CUTOFF else pi.verification_status
                data.append({
                    "id": pi.id,
                    "income_ids": [pi.id],
                    "user_id": pi.user_id,
                    "user_name": user_map.get(pi.user_id, "Unknown"),
                    "income_type": pi.income_type,
                    "display_income_type": get_display_income_type(pi.income_type),
                    "gross_amount": round(float(pi.gross_amount)),
                    "net_amount": round(float(pi.net_amount)),
                    "admin_deduction": round(float(pi.admin_deduction)) if pi.admin_deduction else 0,
                    "tds_deduction": round(float(pi.tds_deduction)) if pi.tds_deduction else 0,
                    "gurudakshina_deduction": round(float(pi.gurudakshina_deduction)) if pi.gurudakshina_deduction else 0,
                    "business_date": pi.business_date.isoformat(),
                    "verification_status": display_status,
                    "record_count": 1,
                    "validated_by": pi.admin_verified_by_id,
                    "validated_at": pi.admin_verified_at.isoformat() if pi.admin_verified_at else None,
                    "approved_by": pi.accounts_paid_by_id,
                    "approved_at": pi.accounts_paid_at.isoformat() if pi.accounts_paid_at else None,
                    "kyc_status": kyc_map.get(pi.user_id, "Unknown"),
                    "group_eligibility": group_eligibility_map.get(pi.user_id, "Unknown"),
                    "notes": pi.notes or "",
                    "is_clubbed": False
                })
            return {
                "success": True,
                "count": len(data),
                "stats": stats,
                "mode": "unclubbed",
                "data": data
            }
        
        clubbed = {}
        for pi in pending_incomes:
            bdate = pi.business_date.date() if hasattr(pi.business_date, 'date') and callable(pi.business_date.date) else pi.business_date
            key = (pi.user_id, bdate.isoformat() if bdate else '')
            if key not in clubbed:
                clubbed[key] = []
            clubbed[key].append(pi)
        
        data = []
        for (uid, bdate_str), incomes in clubbed.items():
            total_gross = sum(float(pi.gross_amount or 0) for pi in incomes)
            total_net = sum(float(pi.net_amount or 0) for pi in incomes)
            total_admin = sum(float(pi.admin_deduction or 0) for pi in incomes)
            total_tds = sum(float(pi.tds_deduction or 0) for pi in incomes)
            total_guru = sum(float(pi.gurudakshina_deduction or 0) for pi in incomes)
            all_ids = [pi.id for pi in incomes]
            
            bdate = incomes[0].business_date
            bdate_obj = bdate.date() if hasattr(bdate, 'date') and callable(bdate.date) else bdate
            
            if bdate_obj < STAFF_WORKFLOW_CUTOFF:
                display_status = 'Cleared'
            else:
                display_status = _compute_clubbed_status(incomes)
            
            income_types_present = list(set(get_display_income_type(pi.income_type) for pi in incomes))
            
            validated_incomes = [pi for pi in incomes if pi.admin_verified_by_id]
            approved_incomes = [pi for pi in incomes if pi.accounts_paid_by_id]
            
            data.append({
                "id": all_ids[0],
                "income_ids": all_ids,
                "user_id": uid,
                "user_name": user_map.get(uid, "Unknown"),
                "gross_amount": round(total_gross),
                "net_amount": round(total_net),
                "admin_deduction": round(total_admin),
                "tds_deduction": round(total_tds),
                "gurudakshina_deduction": round(total_guru),
                "business_date": bdate_str,
                "verification_status": display_status,
                "record_count": len(incomes),
                "income_types": income_types_present,
                "validated_by": validated_incomes[0].admin_verified_by_id if validated_incomes else None,
                "validated_at": validated_incomes[0].admin_verified_at.isoformat() if validated_incomes and validated_incomes[0].admin_verified_at else None,
                "approved_by": approved_incomes[0].accounts_paid_by_id if approved_incomes else None,
                "approved_at": approved_incomes[0].accounts_paid_at.isoformat() if approved_incomes and approved_incomes[0].accounts_paid_at else None,
                "kyc_status": kyc_map.get(uid, "Unknown"),
                "group_eligibility": group_eligibility_map.get(uid, "Unknown"),
                "is_clubbed": True
            })
        
        return {
            "success": True,
            "count": len(data),
            "stats": stats,
            "mode": "clubbed",
            "data": data
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid date format. Use YYYY-MM-DD. Error: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Server error: {str(e)}"
        )


@router.get("/staff/income-detail/{target_user_id}/{business_date_str}")
async def get_income_detail_for_staff(
    target_user_id: str,
    business_date_str: str,
    response: Response,
    current_staff = Depends(require_staff_with_page_access),
    db: Session = Depends(get_db)
):
    """
    DC Protocol Feb 2026: Get segmented income detail for a user on a specific date
    
    Returns:
    - segment_summary: Per income type totals (gross, deductions, net)
    - segments: Per income type contributor tables
    - all_income_ids: All PendingIncome IDs for this user+date (for validate/approve)
    """
    add_no_cache_headers(response)
    try:
        from app.models.transaction import VedIncome
        from sqlalchemy import cast, Date, text
        
        target_date = datetime.strptime(business_date_str, '%Y-%m-%d').date()
        
        incomes = db.query(PendingIncome).filter(
            PendingIncome.user_id == target_user_id,
            PendingIncome.business_date == target_date
        ).order_by(PendingIncome.income_type).all()
        
        if not incomes:
            raise HTTPException(status_code=404, detail="No income records found for this user and date")
        
        user = db.query(User).filter(User.id == target_user_id).first()
        user_name = user.name if user else "Unknown"
        kyc_status = _get_kyc_status(user) if user else "Unknown"
        
        for pi in incomes:
            if pi.income_type == 'Matching Referral' and hasattr(pi, 'matching_contributors_snapshot') and pi.matching_contributors_snapshot:
                try:
                    from app.core.scheduler import _get_actual_business_date
                    import json as _jdc
                    snap_dc = pi.matching_contributors_snapshot
                    if isinstance(snap_dc, str):
                        snap_dc = _jdc.loads(snap_dc)
                    if snap_dc and isinstance(snap_dc, dict):
                        all_m_dc = {}
                        if snap_dc.get('pairs'):
                            all_m_dc = {
                                'left': [m for p in snap_dc['pairs'] for m in p.get('left', [])],
                                'right': [m for p in snap_dc['pairs'] for m in p.get('right', [])]
                            }
                        elif snap_dc.get('is_exempted'):
                            all_m_dc = {
                                'left': snap_dc.get('left_zero_point_members', []),
                                'right': snap_dc.get('right_zero_point_members', [])
                            }
                        if all_m_dc:
                            old_bd_dc = pi.business_date
                            if hasattr(old_bd_dc, 'date') and callable(old_bd_dc.date):
                                old_bd_only_dc = old_bd_dc.date()
                            else:
                                old_bd_only_dc = old_bd_dc
                            correct_bd_dc = _get_actual_business_date(all_m_dc, old_bd_only_dc)
                            if correct_bd_dc != old_bd_only_dc:
                                dup_dc = db.execute(text("""
                                    SELECT id FROM pending_income
                                    WHERE user_id = :uid AND income_type = 'Matching Referral'
                                    AND DATE(business_date) = :bdate AND id != :rec_id
                                """), {"uid": pi.user_id, "bdate": correct_bd_dc, "rec_id": pi.id}).fetchone()
                                if not dup_dc:
                                    db.execute(text("""
                                        UPDATE pending_income SET business_date = :new_date
                                        WHERE user_id = :uid AND DATE(business_date) = :old_date
                                        AND income_type IN ('Matching Referral', 'Exempted Matching')
                                    """), {"new_date": correct_bd_dc, "uid": target_user_id, "old_date": old_bd_only_dc})
                                    db.commit()
                                    target_date = correct_bd_dc
                                    business_date_str = correct_bd_dc.strftime('%Y-%m-%d')
                                    incomes = db.query(PendingIncome).filter(
                                        PendingIncome.user_id == target_user_id,
                                        PendingIncome.business_date == target_date
                                    ).order_by(PendingIncome.income_type).all()
                                    logger.info(f"Auto-corrected business_date for {target_user_id}: {old_bd_only_dc} → {correct_bd_dc}")
                                    break
                except Exception as e:
                    logger.warning(f"Date auto-correction failed in income-detail: {e}")
        
        all_income_ids = [pi.id for pi in incomes]
        
        type_groups = {}
        for pi in incomes:
            itype = pi.income_type
            if itype not in type_groups:
                type_groups[itype] = []
            type_groups[itype].append(pi)
        
        segment_order = ['Direct Referral', 'Matching Referral', 'Ved Income', 'Guru Dakshina']
        
        _mr_pair_map = {}
        if 'Matching Referral' in type_groups:
            def _get_leg_contributors_mr(tid, side, dbs):
                params = {"user_id": tid, "side": side}
                tq = dbs.execute(text("""
                    WITH RECURSIVE leg_team AS (
                        SELECT p.child_id, p.side as root_leg, 1 as level
                        FROM placement p
                        WHERE p.parent_id = :user_id AND p.side = :side
                        UNION ALL
                        SELECT p.child_id, lt.root_leg, lt.level + 1
                        FROM placement p
                        INNER JOIN leg_team lt ON p.parent_id = lt.child_id
                        WHERE lt.level < 50
                    )
                    SELECT u.id, u.name, u.package_points, u.activation_date
                    FROM leg_team lt
                    JOIN "user" u ON u.id = lt.child_id
                    WHERE u.package_points > 0
                      AND COALESCE(u.is_welcome_coupon, false) = false
                      AND (u.activation_date IS NOT NULL OR u.coupon_status IN ('Active', 'Activated'))
                    ORDER BY COALESCE(u.activation_date, u.registration_date) ASC, u.id ASC
                """), params)
                return [{"id": row[0], "name": row[1], "points": float(row[2]), "activation_date": row[3]} for row in tq]
            
            mr_left = _get_leg_contributors_mr(target_user_id, 'left', db)
            mr_right = _get_leg_contributors_mr(target_user_id, 'right', db)
            
            all_mr_records = db.query(PendingIncome).filter(
                PendingIncome.user_id == target_user_id,
                PendingIncome.income_type == 'Matching Referral'
            ).order_by(PendingIncome.business_date.asc()).all()
            
            first_mr_record = None
            for mrr in all_mr_records:
                if int(mrr.pairs_matched or 0) > 0:
                    first_mr_record = mrr
                    break
            
            first_pair_left_count = 1
            first_pair_right_count = 1
            if first_mr_record:
                eligibility_date_query = db.execute(text("""
                    SELECT activation_date FROM "user"
                    WHERE referrer_id = :user_id AND activation_date IS NOT NULL
                    ORDER BY activation_date ASC LIMIT 1 OFFSET 1
                """), {"user_id": target_user_id})
                eligibility_row = eligibility_date_query.fetchone()
                eligibility_date = eligibility_row[0] if eligibility_row else first_mr_record.business_date
                
                historical_leg_balance = db.execute(text("""
                    WITH RECURSIVE leg_team AS (
                        SELECT p.child_id, p.side, 1 as level FROM placement p
                        WHERE p.parent_id = :user_id
                        UNION ALL
                        SELECT p.child_id, lt.side, lt.level + 1 FROM placement p
                        INNER JOIN leg_team lt ON p.parent_id = lt.child_id
                        WHERE lt.level < 200
                    )
                    SELECT lt.side, COALESCE(SUM(u.package_points), 0) as total_points
                    FROM leg_team lt JOIN "user" u ON u.id = lt.child_id
                    WHERE u.activation_date IS NOT NULL AND u.activation_date <= :eligibility_date AND u.package_points > 0
                    GROUP BY lt.side
                """), {"user_id": target_user_id, "eligibility_date": eligibility_date})
                leg_balance = {row[0]: float(row[1]) for row in historical_leg_balance}
                ltp = leg_balance.get('left', 0)
                rtp = leg_balance.get('right', 0)
                if ltp > rtp:
                    first_pair_left_count = 2
                    first_pair_right_count = 1
                elif rtp > ltp:
                    first_pair_left_count = 1
                    first_pair_right_count = 2
            
            mr_left_idx = 0
            mr_right_idx = 0
            global_pair_num = 0
            
            for mr_rec in all_mr_records:
                rec_pairs = int(mr_rec.pairs_matched or 0)
                if rec_pairs == 0:
                    continue
                snap = mr_rec.matching_contributors_snapshot if hasattr(mr_rec, 'matching_contributors_snapshot') else None
                if snap and isinstance(snap, dict) and snap.get('is_exempted'):
                    continue
                is_first_mr = (first_mr_record and mr_rec.id == first_mr_record.id)
                rec_contributors = []
                for pair_idx in range(rec_pairs):
                    global_pair_num += 1
                    is_very_first = (is_first_mr and pair_idx == 0)
                    lc = first_pair_left_count if is_very_first else 1
                    rc = first_pair_right_count if is_very_first else 1
                    
                    left_members = []
                    for _ in range(lc):
                        if mr_left_idx < len(mr_left):
                            left_members.append(mr_left[mr_left_idx])
                            mr_left_idx += 1
                    right_members = []
                    for _ in range(rc):
                        if mr_right_idx < len(mr_right):
                            right_members.append(mr_right[mr_right_idx])
                            mr_right_idx += 1
                    rec_contributors.append({"left": left_members, "right": right_members})
                _mr_pair_map[mr_rec.id] = rec_contributors
        
        segment_summary = []
        segments = []
        
        for itype in segment_order:
            if itype not in type_groups:
                continue
            group = type_groups[itype]
            
            seg_gross = sum(float(pi.gross_amount or 0) for pi in group)
            seg_admin = sum(float(pi.admin_deduction or 0) for pi in group)
            seg_tds = sum(float(pi.tds_deduction or 0) for pi in group)
            seg_guru = sum(float(pi.gurudakshina_deduction or 0) for pi in group)
            seg_net = sum(float(pi.net_amount or 0) for pi in group)
            seg_ids = [pi.id for pi in group]
            
            display_type = get_display_income_type(itype)
            
            segment_summary.append({
                "income_type": itype,
                "display_income_type": display_type,
                "gross_amount": round(seg_gross),
                "admin_deduction": round(seg_admin),
                "tds_deduction": round(seg_tds),
                "gurudakshina_deduction": round(seg_guru),
                "net_amount": round(seg_net),
                "record_count": len(group),
                "income_ids": seg_ids
            })
            
            def _fmt_activation_date(u):
                if u and hasattr(u, 'activation_date') and u.activation_date:
                    ad = u.activation_date
                    if hasattr(ad, 'strftime'):
                        return ad.strftime('%Y-%m-%d')
                    return str(ad)[:10]
                return None
            
            def _make_contributor(pi, src_id, src_name, src_activation_date, itype, **extra):
                entry = {
                    "source_user_id": src_id,
                    "source_user_name": src_name,
                    "activation_date": src_activation_date,
                    "income_type": itype,
                    "gross_amount": round(float(pi.gross_amount or 0)),
                    "admin_deduction": round(float(pi.admin_deduction or 0)),
                    "tds_deduction": round(float(pi.tds_deduction or 0)),
                    "guru_deduction": round(float(pi.gurudakshina_deduction or 0)),
                    "net_amount": round(float(pi.net_amount or 0))
                }
                entry.update(extra)
                return entry
            
            contributors = []
            for pi in group:
                if itype == 'Direct Referral':
                    if pi.related_user_id:
                        related_user = db.query(User).filter(User.id == pi.related_user_id).first()
                        contributors.append(_make_contributor(
                            pi, pi.related_user_id,
                            related_user.name if related_user else "Unknown",
                            _fmt_activation_date(related_user), itype
                        ))
                    else:
                        contributors.append(_make_contributor(
                            pi, "System", "Direct Referral", None, itype
                        ))
                
                elif itype == 'Matching Referral':
                    pairs_count = int(pi.pairs_matched or 0)
                    per_pair = float(pi.gross_amount or 0) / pairs_count if pairs_count > 0 else float(pi.gross_amount or 0)
                    
                    def _fmt_act_snap(members):
                        dates = []
                        for m in members:
                            ad = m.get('activation_date')
                            if ad:
                                dates.append(ad if isinstance(ad, str) else (ad.strftime('%Y-%m-%d') if hasattr(ad, 'strftime') else str(ad)[:10]))
                        return ", ".join(dates) if dates else None
                    
                    snapshot = pi.matching_contributors_snapshot if hasattr(pi, 'matching_contributors_snapshot') else None
                    
                    if snapshot and isinstance(snapshot, dict) and snapshot.get('is_exempted'):
                        left_zp = snapshot.get('left_zero_point_members', [])
                        right_zp = snapshot.get('right_zero_point_members', [])
                        left_display = left_zp if left_zp else []
                        right_display = right_zp if right_zp else []
                        contributors.append({
                            "source_user_id": ", ".join(m.get('user_id', 'N/A') for m in left_display) if left_display else "N/A",
                            "source_user_name": ", ".join(m.get('name', '') for m in left_display) if left_display else "No zero-point member",
                            "activation_date": _fmt_act_snap(left_display),
                            "partner_user_id": ", ".join(m.get('user_id', 'N/A') for m in right_display) if right_display else "N/A",
                            "partner_user_name": ", ".join(m.get('name', '') for m in right_display) if right_display else "No zero-point member",
                            "partner_activation_date": _fmt_act_snap(right_display),
                            "income_type": itype,
                            "gross_amount": 0,
                            "admin_deduction": 0,
                            "tds_deduction": 0,
                            "guru_deduction": 0,
                            "net_amount": 0
                        })
                    elif snapshot and isinstance(snapshot, dict) and snapshot.get('pairs'):
                        for pair_info in snapshot['pairs']:
                            left_list = pair_info.get("left", [])
                            right_list = pair_info.get("right", [])
                            admin_d = round(per_pair * float(ADMIN_DEDUCTION_RATE), 2)
                            tds_d = round(per_pair * float(TDS_DEDUCTION_RATE), 2)
                            guru_d = round(per_pair * 0.02, 2)
                            
                            contributors.append({
                                "source_user_id": ", ".join(m['user_id'] for m in left_list) if left_list else "N/A",
                                "source_user_name": ", ".join(m['name'] for m in left_list) if left_list else "",
                                "activation_date": _fmt_act_snap(left_list),
                                "partner_user_id": ", ".join(m['user_id'] for m in right_list) if right_list else "N/A",
                                "partner_user_name": ", ".join(m['name'] for m in right_list) if right_list else "",
                                "partner_activation_date": _fmt_act_snap(right_list),
                                "income_type": itype,
                                "gross_amount": round(per_pair, 2),
                                "admin_deduction": admin_d,
                                "tds_deduction": tds_d,
                                "guru_deduction": guru_d,
                                "net_amount": round(per_pair - admin_d - tds_d - guru_d, 2)
                            })
                    else:
                        pairs_for_this = _mr_pair_map.get(pi.id, [])
                        for pair_info in pairs_for_this:
                            left_list = pair_info.get("left", [])
                            right_list = pair_info.get("right", [])
                            admin_d = round(per_pair * float(ADMIN_DEDUCTION_RATE), 2)
                            tds_d = round(per_pair * float(TDS_DEDUCTION_RATE), 2)
                            guru_d = round(per_pair * 0.02, 2)
                            
                            def _fmt_act_legacy(members):
                                dates = []
                                for m in members:
                                    ad = m.get('activation_date')
                                    if ad:
                                        dates.append(ad.strftime('%Y-%m-%d') if hasattr(ad, 'strftime') else str(ad)[:10])
                                return ", ".join(dates) if dates else None
                            
                            contributors.append({
                                "source_user_id": ", ".join(m['id'] for m in left_list) if left_list else "N/A",
                                "source_user_name": ", ".join(m['name'] for m in left_list) if left_list else "",
                                "activation_date": _fmt_act_legacy(left_list),
                                "partner_user_id": ", ".join(m['id'] for m in right_list) if right_list else "N/A",
                                "partner_user_name": ", ".join(m['name'] for m in right_list) if right_list else "",
                                "partner_activation_date": _fmt_act_legacy(right_list),
                                "income_type": itype,
                                "gross_amount": round(per_pair, 2),
                                "admin_deduction": admin_d,
                                "tds_deduction": tds_d,
                                "guru_deduction": guru_d,
                                "net_amount": round(per_pair - admin_d - tds_d - guru_d, 2)
                            })
                
                elif itype == 'Ved Income':
                    if pi.related_user_id:
                        related_user = db.query(User).filter(User.id == pi.related_user_id).first()
                        contributors.append(_make_contributor(
                            pi, pi.related_user_id,
                            related_user.name if related_user else "Unknown",
                            _fmt_activation_date(related_user), itype
                        ))
                    else:
                        contributors.append(_make_contributor(
                            pi, "System", "VED Chain", None, itype
                        ))
                
                elif itype == 'Guru Dakshina':
                    if pi.related_user_id:
                        related_user = db.query(User).filter(User.id == pi.related_user_id).first()
                        contributors.append(_make_contributor(
                            pi, pi.related_user_id,
                            related_user.name if related_user else "Unknown",
                            _fmt_activation_date(related_user), itype
                        ))
                    else:
                        contributors.append(_make_contributor(
                            pi, "System", "Mentorship", None, itype
                        ))
            
            segments.append({
                "income_type": itype,
                "display_income_type": display_type,
                "gross_amount": round(seg_gross),
                "admin_deduction": round(seg_admin),
                "tds_deduction": round(seg_tds),
                "gurudakshina_deduction": round(seg_guru),
                "net_amount": round(seg_net),
                "contributors": contributors
            })
        
        for itype, group in type_groups.items():
            if itype not in segment_order:
                seg_gross = sum(float(pi.gross_amount or 0) for pi in group)
                seg_net = sum(float(pi.net_amount or 0) for pi in group)
                display_type = get_display_income_type(itype)
                segment_summary.append({
                    "income_type": itype,
                    "display_income_type": display_type,
                    "gross_amount": round(seg_gross),
                    "admin_deduction": round(sum(float(pi.admin_deduction or 0) for pi in group)),
                    "tds_deduction": round(sum(float(pi.tds_deduction or 0) for pi in group)),
                    "gurudakshina_deduction": round(sum(float(pi.gurudakshina_deduction or 0) for pi in group)),
                    "net_amount": round(seg_net),
                    "record_count": len(group),
                    "income_ids": [pi.id for pi in group]
                })
                segments.append({
                    "income_type": itype,
                    "display_income_type": display_type,
                    "gross_amount": round(seg_gross),
                    "admin_deduction": round(sum(float(pi.admin_deduction or 0) for pi in group)),
                    "tds_deduction": round(sum(float(pi.tds_deduction or 0) for pi in group)),
                    "gurudakshina_deduction": round(sum(float(pi.gurudakshina_deduction or 0) for pi in group)),
                    "net_amount": round(seg_net),
                    "contributors": [{
                        "source_user_id": pi.related_user_id or "System",
                        "source_user_name": "Unknown",
                        "income_type": itype,
                        "gross_amount": round(float(pi.gross_amount or 0)),
                        "admin_deduction": round(float(pi.admin_deduction or 0)),
                        "tds_deduction": round(float(pi.tds_deduction or 0)),
                        "guru_deduction": round(float(pi.gurudakshina_deduction or 0)),
                        "net_amount": round(float(pi.net_amount or 0))
                    } for pi in group]
                })
        
        total_gross = sum(s['gross_amount'] for s in segment_summary)
        total_net = sum(s['net_amount'] for s in segment_summary)
        total_deductions = sum(s['admin_deduction'] + s['tds_deduction'] + s['gurudakshina_deduction'] for s in segment_summary)
        
        bdate_obj = target_date
        display_status = 'Cleared' if bdate_obj < STAFF_WORKFLOW_CUTOFF else _compute_clubbed_status(incomes)
        
        return {
            "success": True,
            "user_id": target_user_id,
            "user_name": user_name,
            "business_date": business_date_str,
            "kyc_status": kyc_status,
            "verification_status": display_status,
            "total_gross": round(total_gross),
            "total_deductions": round(total_deductions),
            "total_net": round(total_net),
            "all_income_ids": all_income_ids,
            "segment_summary": segment_summary,
            "segments": segments
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid date format. Use YYYY-MM-DD. Error: {str(e)}"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Server error: {str(e)}"
        )


@router.get("/staff/role")
async def get_staff_income_role(
    current_staff = Depends(require_staff_with_page_access),
    db: Session = Depends(get_db)
):
    """
    DC Protocol Feb 2026: Get staff role for income approval workflow
    
    DC Protocol: Menu-based access control - page assignment = full access
    If staff has page access (verified by require_staff_with_page_access),
    they have COMPLETE rights including validate and approve.
    """
    from app.models.staff import StaffEmployee
    
    staff_type = getattr(current_staff, 'staff_type', None) or ''
    emp_code = getattr(current_staff, 'emp_code', None) or ''
    staff_type_upper = staff_type.upper() if staff_type else ''
    
    is_vgk4u = staff_type_upper == 'VGK4U'
    
    is_finance = 'finance' in staff_type.lower() if staff_type else False
    is_super_admin = 'super' in staff_type.lower() and 'admin' in staff_type.lower() if staff_type else False
    
    is_accounts = False
    dept = getattr(current_staff, 'department', None)
    if dept:
        dept_name = getattr(dept, 'name', '') or ''
        is_accounts = 'accounts' in dept_name.lower() or 'finance' in dept_name.lower()
    
    role = getattr(current_staff, 'role', None)
    is_key_leadership = False
    if role:
        hierarchy_level = getattr(role, 'hierarchy_level', 0)
        is_key_leadership = hierarchy_level >= 100
    
    # DC Protocol: Validation open to all staff with page access
    # Final approval restricted to MR10001 VGK Supreme + Accounts department only
    # Also check additional departments for Accounts
    if not is_accounts:
        additional_depts = getattr(current_staff, 'additional_departments', [])
        for ad in additional_depts:
            ad_dept = getattr(ad, 'department', None)
            if ad_dept:
                ad_name = (getattr(ad_dept, 'name', '') or '').lower()
                if 'accounts' in ad_name or 'finance' in ad_name:
                    is_accounts = True
                    break
    
    is_mr10001 = emp_code == 'MR10001'
    can_approve_directly = is_accounts or is_mr10001
    
    return {
        "success": True,
        "message": "Staff role retrieved",
        "data": {
            "emp_code": emp_code,
            "staff_type": staff_type,
            "can_validate": True,
            "can_approve": can_approve_directly,
            "is_vgk4u": is_vgk4u,
            "is_accounts": is_accounts,
            "is_finance": is_finance,
            "is_super_admin": is_super_admin,
            "is_key_leadership": is_key_leadership
        }
    }


def _snapshot_has_na(snap):
    if not snap or not isinstance(snap, dict):
        return True
    is_exempted = snap.get('is_exempted', False)
    if snap.get('pairs'):
        for p in snap['pairs']:
            if not p.get('left') or not p.get('right'):
                return True
    elif is_exempted:
        if not snap.get('left_zero_point_members') and not snap.get('right_zero_point_members'):
            return True
    return False


@router.get("/staff/income-contributors/{income_id}")
async def get_income_contributors(
    income_id: int,
    current_staff = Depends(require_staff_with_page_access),
    db: Session = Depends(get_db)
):
    """
    DC Protocol Feb 2026: Get individual contributors for an income record
    
    Returns individual rows for each source user who contributed to this income:
    - Direct Referral: Each referred user who activated
    - Matching Referral: Each new user who triggered matching
    - Ved Income: Source users in Ved chain
    - Guru Dakshina: Source users who paid Guru Dakshina
    """
    from app.models.transaction import VedIncome
    from sqlalchemy import cast, Date
    
    # Get the pending income record
    income = db.query(PendingIncome).filter(PendingIncome.id == income_id).first()
    if not income:
        raise HTTPException(status_code=404, detail="Income record not found")
    
    contributors = []
    business_date = income.business_date.date() if hasattr(income.business_date, 'date') else income.business_date
    
    # Calculate per-user amount distribution
    income_type = income.income_type
    gross_amount = float(income.gross_amount) if income.gross_amount else 0
    
    if income_type == 'Direct Referral':
        # Find all users referred by this user who activated on this date
        referred_users = db.query(User).filter(
            User.referrer_id == income.user_id,
            cast(User.activation_date, Date) == business_date
        ).all()
        
        if referred_users:
            per_user_gross = gross_amount / len(referred_users)
            for user in referred_users:
                admin_ded = round(per_user_gross * float(ADMIN_DEDUCTION_RATE), 2)
                tds_ded = round(per_user_gross * float(TDS_DEDUCTION_RATE), 2)
                guru_ded = round(per_user_gross * 0.02, 2)
                net = round(per_user_gross - admin_ded - tds_ded - guru_ded, 2)
                
                contributors.append({
                    "source_user_id": user.id,
                    "source_user_name": user.name or "Unknown",
                    "income_type": income_type,
                    "package_type": getattr(user, 'package_type', None) or "N/A",
                    "package_points": float(user.package_points) if user.package_points else 0,
                    "gross_amount": round(per_user_gross, 2),
                    "admin_deduction": admin_ded,
                    "tds_deduction": tds_ded,
                    "guru_deduction": guru_ded,
                    "net_amount": net,
                    "activation_date": user.activation_date.isoformat() if user.activation_date else None
                })
        else:
            # Fallback: If no referred users found, show consolidated
            if income.related_user_id:
                related_user = db.query(User).filter(User.id == income.related_user_id).first()
                contributors.append({
                    "source_user_id": income.related_user_id,
                    "source_user_name": related_user.name if related_user else "Unknown",
                    "income_type": income_type,
                    "package_type": "N/A",
                    "package_points": 0,
                    "gross_amount": gross_amount,
                    "admin_deduction": round(gross_amount * float(ADMIN_DEDUCTION_RATE), 2),
                    "tds_deduction": round(gross_amount * float(TDS_DEDUCTION_RATE), 2),
                    "guru_deduction": round(gross_amount * 0.02, 2),
                    "net_amount": float(income.net_amount) if income.net_amount else 0,
                    "activation_date": None
                })
    
    elif income_type == 'Matching Referral':
        from sqlalchemy import text
        
        pairs_matched = income.pairs_matched or 0
        per_pair_gross = gross_amount / pairs_matched if pairs_matched > 0 else gross_amount
        
        snapshot = income.matching_contributors_snapshot if hasattr(income, 'matching_contributors_snapshot') else None
        
        if snapshot and isinstance(snapshot, str):
            import json as _json
            try:
                snapshot = _json.loads(snapshot)
            except (ValueError, TypeError):
                snapshot = None
        
        has_na_snapshot = False
        is_exempted = snapshot.get('is_exempted', False) if snapshot and isinstance(snapshot, dict) else False
        
        if snapshot and isinstance(snapshot, dict):
            if snapshot.get('pairs'):
                for pair_info in snapshot['pairs']:
                    if not pair_info.get("left") or not pair_info.get("right"):
                        has_na_snapshot = True
                        break
            elif is_exempted:
                left_zero = snapshot.get('left_zero_point_members', [])
                right_zero = snapshot.get('right_zero_point_members', [])
                if not left_zero and not right_zero:
                    has_na_snapshot = True
        
        if has_na_snapshot and (pairs_matched > 0 or is_exempted):
            try:
                from app.services.sql_utils import identify_consumed_members_sql, identify_exempted_members_sql, build_matching_contributor_snapshot, build_exempted_matching_snapshot
                left_consumed = float(income.left_points_consumed) if income.left_points_consumed else 0
                right_consumed = float(income.right_points_consumed) if income.right_points_consumed else 0
                match_type = snapshot.get('match_type', 'normal') if snapshot else 'normal'
                
                rebuilt = None
                if is_exempted:
                    left_zero_consumed = snapshot.get('exempted_left_consumed', 0)
                    right_zero_consumed = snapshot.get('exempted_right_consumed', 0)
                    if left_consumed > 0 or right_consumed > 0 or left_zero_consumed > 0 or right_zero_consumed > 0:
                        exempted_members = identify_exempted_members_sql(
                            db, income.user_id, left_zero_consumed, right_zero_consumed
                        )
                        rebuilt = build_exempted_matching_snapshot(
                            db, income.user_id, pairs_matched,
                            left_consumed, right_consumed,
                            left_zero_consumed, right_zero_consumed,
                            consumed_members=exempted_members
                        )
                elif left_consumed > 0 or right_consumed > 0:
                    consumed = identify_consumed_members_sql(
                        db, income.user_id, left_consumed, right_consumed,
                        exclude_record_id=income.id
                    )
                    rebuilt = build_matching_contributor_snapshot(
                        db, income.user_id, pairs_matched,
                        left_consumed, right_consumed, match_type,
                        consumed_members=consumed
                    )
                
                if rebuilt and not _snapshot_has_na(rebuilt):
                    snapshot = rebuilt
                    income.matching_contributors_snapshot = rebuilt
                    db.commit()
                    logger.info(f"Auto-repaired N/A snapshot for income {income.id}")
            except Exception as e:
                logger.warning(f"Auto-repair failed for income {income.id}: {e}")
        
        if snapshot and isinstance(snapshot, dict):
            try:
                from app.core.scheduler import _get_actual_business_date
                from datetime import datetime as _dt_seg
                old_bd = income.business_date
                if hasattr(old_bd, 'date') and callable(old_bd.date):
                    old_bd_only = old_bd.date()
                elif isinstance(old_bd, str):
                    old_bd_only = _dt_seg.strptime(str(old_bd)[:10], '%Y-%m-%d').date()
                else:
                    old_bd_only = old_bd

                all_m_seg = {}
                if snapshot.get('pairs'):
                    all_m_seg = {
                        'left': [m for p in snapshot['pairs'] for m in p.get('left', [])],
                        'right': [m for p in snapshot['pairs'] for m in p.get('right', [])]
                    }
                elif snapshot.get('is_exempted'):
                    all_m_seg = {
                        'left': snapshot.get('left_zero_point_members', []),
                        'right': snapshot.get('right_zero_point_members', [])
                    }
                if all_m_seg:
                    correct_bd = _get_actual_business_date(all_m_seg, old_bd_only)
                    if correct_bd != old_bd_only:
                        dup = db.execute(text("""
                            SELECT id FROM pending_income
                            WHERE user_id = :uid AND income_type = 'Matching Referral'
                            AND DATE(business_date) = :bdate AND id != :rec_id
                        """), {"uid": income.user_id, "bdate": correct_bd, "rec_id": income.id}).fetchone()
                        if not dup:
                            income.business_date = correct_bd
                            db.commit()
                            logger.info(f"Auto-corrected business_date for income {income.id}: {old_bd_only} → {correct_bd}")
            except Exception as e:
                logger.warning(f"Auto date-correction failed for income {income.id}: {e}")

        if snapshot and isinstance(snapshot, dict) and snapshot.get('pairs'):
            for pair_info in snapshot['pairs']:
                left_list = pair_info.get("left", [])
                right_list = pair_info.get("right", [])
                admin_ded = round(per_pair_gross * float(ADMIN_DEDUCTION_RATE), 2)
                tds_ded = round(per_pair_gross * float(TDS_DEDUCTION_RATE), 2)
                guru_ded = round(per_pair_gross * 0.02, 2)
                net = round(per_pair_gross - admin_ded - tds_ded - guru_ded, 2)
                
                contributors.append({
                    "source_user_id": ", ".join(m['user_id'] for m in left_list) if left_list else "N/A",
                    "source_user_name": ", ".join(m['name'] for m in left_list) if left_list else "",
                    "partner_user_id": ", ".join(m['user_id'] for m in right_list) if right_list else "N/A",
                    "partner_user_name": ", ".join(m['name'] for m in right_list) if right_list else "",
                    "income_type": income_type,
                    "package_type": "Matched Pair",
                    "package_points": float(per_pair_gross),
                    "gross_amount": round(per_pair_gross, 2),
                    "admin_deduction": admin_ded,
                    "tds_deduction": tds_ded,
                    "guru_deduction": guru_ded,
                    "net_amount": net
                })
        else:
            income_business_date = income.business_date
            if hasattr(income_business_date, 'date') and callable(income_business_date.date):
                income_business_date = income_business_date.date()
            end_of_business_day = datetime.combine(income_business_date, datetime.max.time()) if income_business_date else None
            
            left_query = text("""
                WITH RECURSIVE left_tree AS (
                    SELECT child_id, placed_at, 1 as level
                    FROM placement 
                    WHERE parent_id = :user_id AND side = 'left' AND status = 'active'
                    UNION ALL
                    SELECT p.child_id, p.placed_at, lt.level + 1
                    FROM placement p
                    JOIN left_tree lt ON p.parent_id = lt.child_id
                    WHERE p.status = 'active' AND lt.level < 200
                )
                SELECT lt.child_id, u.name, u.activation_date
                FROM left_tree lt
                JOIN "user" u ON lt.child_id = u.id
                WHERE (u.activation_date IS NOT NULL OR u.coupon_status IN ('Active', 'Activated'))
                  AND u.package_points > 0
                  AND COALESCE(u.is_welcome_coupon, false) = false
                ORDER BY COALESCE(u.activation_date, u.registration_date) ASC, u.id ASC
                LIMIT :limit
            """)
            
            right_query = text("""
                WITH RECURSIVE right_tree AS (
                    SELECT child_id, placed_at, 1 as level
                    FROM placement 
                    WHERE parent_id = :user_id AND side = 'right' AND status = 'active'
                    UNION ALL
                    SELECT p.child_id, p.placed_at, rt.level + 1
                    FROM placement p
                    JOIN right_tree rt ON p.parent_id = rt.child_id
                    WHERE p.status = 'active' AND rt.level < 200
                )
                SELECT rt.child_id, u.name, u.activation_date
                FROM right_tree rt
                JOIN "user" u ON rt.child_id = u.id
                WHERE (u.activation_date IS NOT NULL OR u.coupon_status IN ('Active', 'Activated'))
                  AND u.package_points > 0
                  AND COALESCE(u.is_welcome_coupon, false) = false
                ORDER BY COALESCE(u.activation_date, u.registration_date) ASC, u.id ASC
                LIMIT :limit
            """)
            
            limit_count = pairs_matched if pairs_matched > 0 else 20
            
            left_result = db.execute(left_query, {"user_id": income.user_id, "limit": limit_count})
            left_members = [(row[0], row[1], row[2]) for row in left_result.fetchall()]
            
            right_result = db.execute(right_query, {"user_id": income.user_id, "limit": limit_count})
            right_members = [(row[0], row[1], row[2]) for row in right_result.fetchall()]
            
            num_pairs = min(len(left_members), len(right_members), pairs_matched if pairs_matched > 0 else 100)
            
            for i in range(num_pairs):
                left_user = left_members[i] if i < len(left_members) else None
                right_user = right_members[i] if i < len(right_members) else None
                
                if left_user and right_user:
                    left_date = left_user[2]
                    right_date = right_user[2]
                    
                    if left_date and right_date and left_date >= right_date:
                        recent_id, recent_name = left_user[0], left_user[1]
                        older_id, older_name = right_user[0], right_user[1]
                    else:
                        recent_id, recent_name = right_user[0], right_user[1]
                        older_id, older_name = left_user[0], left_user[1]
                    
                    admin_ded = round(per_pair_gross * float(ADMIN_DEDUCTION_RATE), 2)
                    tds_ded = round(per_pair_gross * float(TDS_DEDUCTION_RATE), 2)
                    guru_ded = round(per_pair_gross * 0.02, 2)
                    net = round(per_pair_gross - admin_ded - tds_ded - guru_ded, 2)
                    
                    contributors.append({
                        "source_user_id": recent_id,
                        "source_user_name": recent_name or "Unknown",
                        "partner_user_id": older_id,
                        "partner_user_name": older_name or "Unknown",
                        "income_type": income_type,
                        "package_type": "Matched Pair",
                        "package_points": float(per_pair_gross),
                        "gross_amount": round(per_pair_gross, 2),
                        "admin_deduction": admin_ded,
                        "tds_deduction": tds_ded,
                        "guru_deduction": guru_ded,
                        "net_amount": net
                    })
    
    elif income_type == 'Ved Income':
        # Query VedIncome table for individual records
        ved_records = db.query(VedIncome).filter(
            VedIncome.ved_owner_id == income.user_id,
            cast(VedIncome.business_date, Date) == business_date
        ).all()
        
        if ved_records:
            for ved in ved_records:
                ved_gross = float(ved.base_amount) if ved.base_amount else 0
                admin_ded = round(ved_gross * float(ADMIN_DEDUCTION_RATE), 2)
                tds_ded = round(ved_gross * float(TDS_DEDUCTION_RATE), 2)
                guru_ded = round(ved_gross * 0.02, 2)
                net = round(ved_gross - admin_ded - tds_ded - guru_ded, 2)
                
                # Get source user info
                source_user = db.query(User).filter(User.id == ved.new_member_id).first()
                contributors.append({
                    "source_user_id": ved.new_member_id,
                    "source_user_name": source_user.name if source_user else "Unknown",
                    "income_type": income_type,
                    "package_type": "N/A",
                    "package_points": float(source_user.package_points) if source_user and source_user.package_points else 0,
                    "gross_amount": ved_gross,
                    "admin_deduction": admin_ded,
                    "tds_deduction": tds_ded,
                    "guru_deduction": guru_ded,
                    "net_amount": net,
                    "ved_level": ved.ved_relationship_level
                })
        else:
            # Fallback consolidated
            if income.related_user_id:
                related_user = db.query(User).filter(User.id == income.related_user_id).first()
                contributors.append({
                    "source_user_id": income.related_user_id,
                    "source_user_name": related_user.name if related_user else "Unknown",
                    "income_type": income_type,
                    "package_type": "N/A",
                    "package_points": 0,
                    "gross_amount": gross_amount,
                    "admin_deduction": round(gross_amount * float(ADMIN_DEDUCTION_RATE), 2),
                    "tds_deduction": round(gross_amount * float(TDS_DEDUCTION_RATE), 2),
                    "guru_deduction": round(gross_amount * 0.02, 2),
                    "net_amount": float(income.net_amount) if income.net_amount else 0
                })
    
    elif income_type == 'Guru Dakshina':
        # Query users who paid Guru Dakshina to this user on this date
        # Guru Dakshina comes from downline's income deductions
        downline_incomes = db.query(PendingIncome).filter(
            PendingIncome.related_user_id == income.user_id,
            cast(PendingIncome.business_date, Date) == business_date,
            PendingIncome.gurudakshina_deduction > 0
        ).all()
        
        if downline_incomes:
            for di in downline_incomes:
                source_user = db.query(User).filter(User.id == di.user_id).first()
                gd_amount = float(di.gurudakshina_deduction) if di.gurudakshina_deduction else 0
                
                contributors.append({
                    "source_user_id": di.user_id,
                    "source_user_name": source_user.name if source_user else "Unknown",
                    "income_type": income_type,
                    "package_type": "N/A",
                    "package_points": 0,
                    "gross_amount": gd_amount,
                    "admin_deduction": 0,
                    "tds_deduction": 0,
                    "guru_deduction": 0,
                    "net_amount": gd_amount,
                    "from_income_type": di.income_type
                })
        else:
            # Fallback - try to get actual user info
            related_user = None
            if income.related_user_id:
                related_user = db.query(User).filter(User.id == income.related_user_id).first()
            
            contributors.append({
                "source_user_id": income.related_user_id or "N/A",
                "source_user_name": related_user.name if related_user else "N/A",
                "income_type": income_type,
                "package_type": "N/A",
                "package_points": 0,
                "gross_amount": gross_amount,
                "admin_deduction": 0,
                "tds_deduction": 0,
                "guru_deduction": 0,
                "net_amount": float(income.net_amount) if income.net_amount else 0
            })
    
    # If still no contributors, create a single entry with actual user info
    if not contributors:
        related_user = None
        if income.related_user_id:
            related_user = db.query(User).filter(User.id == income.related_user_id).first()
        
        contributors.append({
            "source_user_id": income.related_user_id or "N/A",
            "source_user_name": related_user.name if related_user else "N/A",
            "income_type": income_type,
            "package_type": "N/A",
            "package_points": 0,
            "gross_amount": gross_amount,
            "admin_deduction": float(income.admin_deduction) if income.admin_deduction else 0,
            "tds_deduction": float(income.tds_deduction) if income.tds_deduction else 0,
            "guru_deduction": float(income.gurudakshina_deduction) if income.gurudakshina_deduction else 0,
            "net_amount": float(income.net_amount) if income.net_amount else 0
        })
    
    return {
        "success": True,
        "income_id": income_id,
        "user_id": income.user_id,
        "income_type": income_type,
        "business_date": str(business_date),
        "total_gross": gross_amount,
        "total_net": float(income.net_amount) if income.net_amount else 0,
        "contributor_count": len(contributors),
        "contributors": contributors
    }


@router.post("/staff/validate")
async def staff_validate_incomes(
    request: VerifyIncomeRequest = Body(...),
    current_staff = Depends(require_staff_with_page_access),
    db: Session = Depends(get_db)
):
    """
    DC Protocol Feb 2026: Staff validates pending incomes
    
    Step 1 of 2-step workflow: Pending → Staff Validated
    Any Staff with page access can validate.
    """
    try:
        from app.models.staff import StaffEmployee
        
        validated_count = 0
        staff_id = _resolve_actor_id(current_staff)
        
        for income_id in request.pending_income_ids:
            pending_income = db.query(PendingIncome).filter(
                PendingIncome.id == income_id,
                PendingIncome.verification_status == 'Pending'
            ).first()
            
            if pending_income:
                pending_income.verification_status = 'Staff Validated'
                pending_income.admin_verified_by_id = staff_id
                pending_income.admin_verified_at = get_indian_time()
                notes_parts = []
                if request.transaction_reference:
                    notes_parts.append(f"Ref: {request.transaction_reference}")
                if request.comments:
                    notes_parts.append(f"Comments: {request.comments}")
                if request.notes:
                    notes_parts.append(request.notes)
                if notes_parts:
                    pending_income.notes = f"Staff Validation [{staff_id}]: {' | '.join(notes_parts)}"
                validated_count += 1
        
        db.commit()
        
        AuditLogger.log_action(
            db=db,
            user=current_staff,
            action='STAFF_VALIDATE_INCOMES',
            resource_type='PendingIncome',
            details={
                "validated_count": validated_count,
                "income_ids": request.pending_income_ids,
                "staff_id": staff_id,
                "transaction_reference": request.transaction_reference,
                "comments": request.comments
            }
        )
        
        return {
            "success": True,
            "message": f"Staff validated {validated_count} income(s). Ready for Accounts/VGK approval.",
            "validated_count": validated_count,
            "workflow": "DC Protocol Feb 2026: 2-Step Staff Workflow"
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Server error: {str(e)}"
        )


@router.get("/staff/validated-incomes")
async def get_validated_incomes_for_approval(
    response: Response,
    user_id: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    current_staff = Depends(require_staff_accounts_or_vgk),
    db: Session = Depends(get_db)
):
    """
    DC Protocol Feb 2026: Get Staff-Validated incomes for final approval
    
    Only Accounts department or VGK Supreme can access this endpoint.
    Returns incomes with status = 'Staff Validated' ready for approval.
    """
    add_no_cache_headers(response)
    try:
        query = db.query(PendingIncome).filter(
            PendingIncome.verification_status == 'Staff Validated'
        )
        
        if user_id:
            query = query.filter(PendingIncome.user_id == user_id)
        
        if from_date:
            from_date_obj = datetime.strptime(from_date, '%Y-%m-%d').date()
            query = query.filter(PendingIncome.business_date >= from_date_obj)
        
        if to_date:
            to_date_obj = datetime.strptime(to_date, '%Y-%m-%d').date()
            query = query.filter(PendingIncome.business_date <= to_date_obj)
        
        query = query.order_by(PendingIncome.business_date.desc())
        validated_incomes = query.all()
        
        # Get user names
        user_ids = list(set([pi.user_id for pi in validated_incomes]))
        users = db.query(User).filter(User.id.in_(user_ids)).all() if user_ids else []
        user_map = {u.id: u.name for u in users}
        
        return {
            "success": True,
            "count": len(validated_incomes),
            "data": [
                {
                    "id": pi.id,
                    "user_id": pi.user_id,
                    "user_name": user_map.get(pi.user_id, "Unknown"),
                    "income_type": pi.income_type,
                    "gross_amount": round(float(pi.gross_amount)),
                    "admin_deduction": round(float(pi.admin_deduction)) if pi.admin_deduction else 0,
                    "tds_deduction": round(float(pi.tds_deduction)) if pi.tds_deduction else 0,
                    "net_amount": round(float(pi.net_amount)),
                    "withdrawal_wallet_amount": round(float(pi.withdrawal_wallet_amount)) if pi.withdrawal_wallet_amount else 0,
                    "upgrade_wallet_amount": round(float(pi.upgraded_wallet_amount)) if pi.upgraded_wallet_amount else 0,
                    "business_date": pi.business_date.isoformat(),
                    "verification_status": pi.verification_status,
                    "validated_by": pi.admin_verified_by_id,
                    "validated_at": pi.admin_verified_at.isoformat() if pi.admin_verified_at else None
                }
                for pi in validated_incomes
            ]
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid date format. Use YYYY-MM-DD. Error: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Server error: {str(e)}"
        )


@router.post("/staff/approve")
async def staff_approve_and_pay_incomes(
    request: VerifyIncomeRequest = Body(...),
    current_staff = Depends(require_staff_accounts_or_vgk),
    db: Session = Depends(get_db)
):
    """
    DC Protocol Feb 2026: Final approval by Accounts/VGK Supreme
    
    Step 2 of 2-step workflow: Staff Validated → Completed (with wallet credit + withdrawal)
    
    Only Accounts department or VGK Supreme can approve.
    This action:
    1. Marks income as 'Completed'
    2. Credits user's withdrawable wallet
    3. Auto-creates withdrawal request (with ₹1,000 minimum rule)
    """
    try:
        from app.models.withdrawal import WithdrawalRequest
        from sqlalchemy import text
        
        processed_count = 0
        total_paid = Decimal('0')
        withdrawal_results = []
        
        staff_id = _resolve_actor_id(current_staff)
        
        # Group incomes by user for batch processing
        users_map = {}
        
        for income_id in request.pending_income_ids:
            pending_income = db.query(PendingIncome).filter(
                PendingIncome.id == income_id,
                PendingIncome.verification_status == 'Staff Validated'
            ).first()
            
            if pending_income:
                user_id = pending_income.user_id
                if user_id not in users_map:
                    users_map[user_id] = []
                users_map[user_id].append(pending_income)
        
        # DC Protocol Feb 2026: KYC bypass for VGK Supreme / Accounts department
        # These authorized staff (enforced by require_staff_accounts_or_vgk) can process
        # payments regardless of KYC status. Log non-approved KYC for audit trail.
        kyc_not_approved_users = []
        for user_id in users_map.keys():
            user = db.query(User).filter(User.id == user_id).first()
            if user:
                kyc_status = getattr(user, 'kyc_status', 'Pending')
                if kyc_status != 'Approved':
                    kyc_not_approved_users.append({
                        "user_id": user_id,
                        "user_name": getattr(user, 'name', 'Unknown'),
                        "kyc_status": kyc_status
                    })
        
        if kyc_not_approved_users:
            user_list = ", ".join([f"{u['user_id']} ({u['kyc_status']})" for u in kyc_not_approved_users])
            logger.warning(f"[KYC-BYPASS] Staff {staff_id} processing payment for non-KYC users: {user_list}")
        
        # Process each user
        for user_id, incomes in users_map.items():
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                continue
            
            # Mark incomes as Completed
            total_for_user = Decimal('0')
            withdrawal_amount = 0
            
            for income in incomes:
                income.verification_status = 'Completed'
                income.accounts_paid_by_id = staff_id
                income.accounts_paid_at = get_indian_time()
                notes_parts = []
                if request.transaction_reference:
                    notes_parts.append(f"Ref: {request.transaction_reference}")
                if request.comments:
                    notes_parts.append(f"Comments: {request.comments}")
                if request.notes:
                    notes_parts.append(request.notes)
                if notes_parts:
                    existing_notes = income.notes or ''
                    income.notes = f"{existing_notes}\nApproval [{staff_id}]: {' | '.join(notes_parts)}".strip()
                total_for_user += income.net_amount
                processed_count += 1
                total_paid += income.net_amount
                withdrawal_amount += int(income.withdrawal_wallet_amount) if income.withdrawal_wallet_amount else 0
                # DC-STATUTORY-GL-001: post TDS + admin to statutory GL accounts
                try:
                    from app.services.staff_accounts_service import LedgerPostingService as _LPS2
                    _biz2 = income.business_date
                    _LPS2.auto_post_statutory_deductions(
                        db=db,
                        company_id=int(getattr(user, 'company_id', None) or 1),
                        tds_amount=income.tds_deduction,
                        admin_amount=income.admin_deduction,
                        txn_date=_biz2.date() if hasattr(_biz2, 'date') else _biz2,
                        ref_type='PENDING_INCOME',
                        ref_id=income.id,
                        ref_number=f'PI-{income.id:08d}',
                        narration=f'{income.income_type} statutory deductions — {income.user_id}',
                        created_by_id=None,
                    )
                except Exception as _sgl2_e:
                    logger.warning(f'[DC-STATUTORY-GL-001] GL post non-fatal for PI#{income.id}: {_sgl2_e}')

            # Credit withdrawable wallet - DC Protocol: Set wallet write context to bypass trigger
            if withdrawal_amount > 0:
                db.execute(text("SET LOCAL app.wallet_write_allowed = 'wallet_sync'"))
                db.execute(
                    text("""
                        UPDATE "user"
                        SET withdrawable_wallet = COALESCE(withdrawable_wallet, 0) + :amount
                        WHERE id = :user_id
                    """),
                    {"amount": withdrawal_amount, "user_id": user_id}
                )
                
                # DC_WITHDRAW_001: Skip if user already has an active withdrawal
                from app.models.withdrawal import get_active_withdrawal
                _existing_wr2 = get_active_withdrawal(db, user.id)
                if _existing_wr2:
                    logger.info(f"⏭️  {user.id}: Skipping withdrawal creation — active withdrawal #{_existing_wr2.id} [{_existing_wr2.status}] already exists")
                else:
                    # Auto-create withdrawal (₹1,000 minimum rule)
                    withdrawal_status = 'On Hold' if withdrawal_amount < 1000 else 'Pending'
                    
                    withdrawal = WithdrawalRequest(
                        user_id=user.id,
                        withdrawal_amount=withdrawal_amount,
                        admin_charges=0,
                        tds_amount=0,
                        final_payout=withdrawal_amount,
                        request_date=date.today(),
                        status=withdrawal_status,
                        is_auto_generated=True,
                        bank_name=user.bank_name or 'Not Set',
                        account_number=user.bank_account_number or 'Not Set',
                        ifsc_code=user.bank_ifsc_code or 'Not Set',
                        account_holder_name=user.bank_account_holder or user.name
                    )
                    db.add(withdrawal)
                    
                    withdrawal_results.append({
                        "user_id": user.id,
                        "amount_approved": float(total_for_user),
                        "withdrawal_amount": withdrawal_amount,
                        "withdrawal_status": withdrawal_status
                    })
        
        db.commit()
        
        AuditLogger.log_action(
            db=db,
            user=current_staff,
            action='STAFF_APPROVE_INCOMES',
            resource_type='PendingIncome',
            details={
                "processed_count": processed_count,
                "total_paid": round(float(total_paid)),
                "withdrawals_created": len(withdrawal_results),
                "staff_id": staff_id,
                "income_ids": request.pending_income_ids
            }
        )
        
        return {
            "success": True,
            "message": f"Approved {processed_count} income(s) → {len(withdrawal_results)} withdrawal(s) auto-created",
            "processed_count": processed_count,
            "total_paid": round(float(total_paid)),
            "withdrawal_results": withdrawal_results,
            "workflow": "DC Protocol Feb 2026: 2-Step Staff Workflow (Completed)"
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Server error: {str(e)}"
        )


# ===== LEGACY ADMIN ENDPOINTS (DEPRECATED) =====
# The following Admin/Super Admin/Finance Admin endpoints are kept for backward compatibility
# but will be removed in future versions. Use Staff endpoints above instead.


# ===== MANUAL INCOME CALCULATION (ADMIN/SUPER ADMIN ONLY) =====

@router.post("/admin/manual-calculate")
async def manually_calculate_income(
    request: ManualIncomeCalculationRequest,
    current_user: dict = Depends(get_current_admin_user_hybrid),
    db: Session = Depends(get_db)
):
    """
    Manually trigger income calculation for a specific date
    Useful for recalculating missed incomes or backdating calculations
    """
    try:
        from app.core.scheduler import (
            calculate_matching_referral_income,
            calculate_ved_income,
            calculate_direct_referral_income,
            calculate_income_deductions_and_splits,
            auto_approve_and_credit_wallet
        )
        from app.models.transaction import CompanyEarnings
        from app.constants import INCOME_LIMITS
        import logging
        
        logger = logging.getLogger(__name__)
        
        # Parse calculation date
        try:
            calculation_date = datetime.strptime(request.calculation_date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Invalid date format. Use YYYY-MM-DD"
            )
        
        logger.info(f"🔧 Manual income calculation triggered by {current_user.get('user_id', 'unknown') if isinstance(current_user, dict) else getattr(current_user, 'id', 'unknown')} for date: {calculation_date}")
        
        # Get all activated users
        activated_users = db.query(User).filter(
            User.coupon_status.in_(['Activated', 'Active']),
            User.package_points > 0
        ).all()
        
        # Store calculated incomes by recipient_id
        recipient_incomes = {}
        
        # Calculate Matching, Ved & Direct Referral Income
        for user in activated_users:
            try:
                # 1. Calculate Matching Referral Income
                matching_result = calculate_matching_referral_income(db, user, calculation_date)
                matching_income = matching_result['gross_income']
                pairs_matched = matching_result['pairs_matched']
                left_consumed = matching_result['left_consumed']
                right_consumed = matching_result['right_consumed']
                match_type = matching_result['match_type']
                
                if matching_income > 0:
                    if user.id not in recipient_incomes:
                        recipient_incomes[user.id] = {'matching': None, 'ved': 0, 'direct_referral': []}
                    recipient_incomes[user.id]['matching'] = {
                        'income': matching_income,
                        'pairs': pairs_matched,
                        'left_consumed': left_consumed,
                        'right_consumed': right_consumed,
                        'match_type': match_type
                    }
                
                # 2. Calculate Ved Income
                ved_income_amount, ved_referrer_id = calculate_ved_income(db, user, calculation_date)
                
                if ved_income_amount > 0 and ved_referrer_id:
                    if ved_referrer_id not in recipient_incomes:
                        recipient_incomes[ved_referrer_id] = {'matching': None, 'ved': 0, 'direct_referral': []}
                    recipient_incomes[ved_referrer_id]['ved'] = ved_income_amount
                
                # 3. Calculate Direct Referral Income
                referral_bonus_amount, referral_referrer_id = calculate_direct_referral_income(db, user, calculation_date)
                
                if referral_bonus_amount > 0 and referral_referrer_id:
                    if referral_referrer_id not in recipient_incomes:
                        recipient_incomes[referral_referrer_id] = {'matching': None, 'ved': 0, 'direct_referral': []}
                    if 'direct_referral' not in recipient_incomes[referral_referrer_id]:
                        recipient_incomes[referral_referrer_id]['direct_referral'] = []
                    recipient_incomes[referral_referrer_id]['direct_referral'].append({
                        'amount': referral_bonus_amount,
                        'referred_user_id': user.id
                    })
                    
            except Exception as e:
                logger.error(f"Error calculating incomes for {user.id}: {e}")
                continue
        
        # Calculate Awards, Bonanza, and Field Allowances
        logger.info("📊 Calculating Awards, Bonanza, and Field Allowances...")
        from app.core.scheduler import (
            calculate_awards_income,
            calculate_bonanza_income,
            calculate_field_allowances
        )
        
        awards_count = calculate_awards_income(db, calculation_date)
        bonanza_count = calculate_bonanza_income(db, calculation_date)
        allowances_count = calculate_field_allowances(db, calculation_date)
        logger.info(f"✅ Awards/Bonanza/Allowances: {awards_count} awards, {bonanza_count} bonanza, {allowances_count} allowances")
        
        # Apply ceiling and create PendingIncome with auto-approval
        total_incomes_created = awards_count + bonanza_count + allowances_count
        ceiling_limit = INCOME_LIMITS['daily_ved_matching_ceiling']
        
        for recipient_id, incomes in recipient_incomes.items():
            try:
                recipient = db.query(User).filter(User.id == recipient_id).first()
                if not recipient:
                    continue
                
                matching_data = incomes.get('matching')
                if matching_data:
                    matching_amount = matching_data['income']
                    pairs_matched = matching_data['pairs']
                    left_consumed = matching_data['left_consumed']
                    right_consumed = matching_data['right_consumed']
                    match_type = matching_data['match_type']
                else:
                    matching_amount = 0
                    pairs_matched = 0
                    left_consumed = 0
                    right_consumed = 0
                    match_type = None
                
                ved_amount = incomes.get('ved', 0)
                
                # Apply ceiling
                total_ved_matching = matching_amount + ved_amount
                
                if total_ved_matching > ceiling_limit:
                    excess_amount = total_ved_matching - ceiling_limit
                    
                    # Pro-rate incomes
                    if matching_amount > 0:
                        matching_amount = (matching_amount / total_ved_matching) * ceiling_limit
                    if ved_amount > 0:
                        ved_amount = (ved_amount / total_ved_matching) * ceiling_limit
                    
                    # Create CompanyEarnings (updated schema: ceiling_date, paid_amount, daily_total_before, daily_ceiling_limit)
                    company_earning = CompanyEarnings(
                        user_id=recipient_id,
                        original_amount=total_ved_matching,
                        excess_amount=excess_amount,
                        paid_amount=excess_amount * float(NET_PAYOUT_RATE),
                        admin_deduction=excess_amount * float(ADMIN_DEDUCTION_RATE),
                        tds_deduction=excess_amount * float(TDS_DEDUCTION_RATE),
                        net_company_earnings=excess_amount * float(NET_PAYOUT_RATE),
                        ceiling_date=calculation_date,  # Updated from business_date
                        income_type='Ved+Matching Ceiling Excess',
                        daily_total_before=total_ved_matching,  # Total before ceiling was applied
                        daily_ceiling_limit=ceiling_limit,  # Updated from ceiling_limit_applied
                        description=f'Manual calculation ceiling excess for {calculation_date}: Ved+Matching total ₹{total_ved_matching:.2f} exceeded ₹{ceiling_limit:.2f} limit'
                    )
                    db.add(company_earning)
                
                # Create Matching Referral PendingIncome with auto-approval
                if matching_amount > 0:
                    # DC Protocol: Check for duplicates before creating
                    from app.core.scheduler import check_duplicate_income
                    if check_duplicate_income(db, recipient_id, 'Matching Referral', calculation_date):
                        logger.warning(f"⚠️ Skipping duplicate Matching Referral for {recipient_id} on {calculation_date}")
                    else:
                        deductions = calculate_income_deductions_and_splits(matching_amount, recipient.package_points, apply_guru_dakshina=True)
                        guru_dakshina_amount = deductions['guru_dakshina_deduction']
                        
                        pending_income = PendingIncome(
                            user_id=recipient_id,
                            income_type='Matching Referral',
                            gross_amount=matching_amount,
                            admin_deduction=deductions['admin_deduction'],
                            tds_deduction=deductions['tds_deduction'],
                            net_amount=deductions['net_amount'],
                            withdrawal_wallet_amount=deductions['withdrawal_wallet_amount'],
                            upgraded_wallet_amount=deductions['upgraded_wallet_amount'],
                            pairs_matched=pairs_matched,
                            left_points_consumed=left_consumed,
                            right_points_consumed=right_consumed,
                            match_type=match_type,
                            business_date=calculation_date,
                            verification_status='Pending'
                        )
                        db.add(pending_income)
                        db.flush()
                        auto_approve_and_credit_wallet(db, pending_income)
                        total_incomes_created += 1
                        
                        # Guru Dakshina for referrer
                        if guru_dakshina_amount > 0 and recipient.referrer_id:
                            referrer = db.query(User).filter(User.id == recipient.referrer_id).first()
                            if referrer and referrer.package_points > 0:
                                gd_deductions = calculate_income_deductions_and_splits(guru_dakshina_amount, referrer.package_points, apply_guru_dakshina=False)
                                
                                guru_dakshina_income = PendingIncome(
                                    user_id=referrer.id,
                                    income_type='Guru Dakshina',
                                    gross_amount=guru_dakshina_amount,
                                    admin_deduction=gd_deductions['admin_deduction'],
                                    tds_deduction=gd_deductions['tds_deduction'],
                                    net_amount=gd_deductions['net_amount'],
                                    withdrawal_wallet_amount=gd_deductions['withdrawal_wallet_amount'],
                                    upgraded_wallet_amount=gd_deductions['upgraded_wallet_amount'],
                                    business_date=calculation_date,
                                    verification_status='Pending',
                                    related_user_id=recipient_id,
                                    notes=f"2% Royalty received from {recipient_id} (Manual Calculation)"
                                )
                                db.add(guru_dakshina_income)
                                db.flush()
                                auto_approve_and_credit_wallet(db, guru_dakshina_income)
                                total_incomes_created += 1
                
                # Create Ved Income with auto-approval
                if ved_amount > 0:
                    deductions = calculate_income_deductions_and_splits(ved_amount, recipient.package_points, apply_guru_dakshina=True)
                    guru_dakshina_amount = deductions['guru_dakshina_deduction']
                    
                    pending_income = PendingIncome(
                        user_id=recipient_id,
                        income_type='Ved Income',
                        gross_amount=ved_amount,
                        admin_deduction=deductions['admin_deduction'],
                        tds_deduction=deductions['tds_deduction'],
                        net_amount=deductions['net_amount'],
                        withdrawal_wallet_amount=deductions['withdrawal_wallet_amount'],
                        upgraded_wallet_amount=deductions['upgraded_wallet_amount'],
                        business_date=calculation_date,
                        verification_status='Pending'
                    )
                    db.add(pending_income)
                    db.flush()
                    auto_approve_and_credit_wallet(db, pending_income)
                    total_incomes_created += 1
                    
                    # Guru Dakshina for referrer
                    if guru_dakshina_amount > 0 and recipient.referrer_id:
                        referrer = db.query(User).filter(User.id == recipient.referrer_id).first()
                        if referrer and referrer.package_points > 0:
                            gd_deductions = calculate_income_deductions_and_splits(guru_dakshina_amount, referrer.package_points, apply_guru_dakshina=False)
                            
                            guru_dakshina_income = PendingIncome(
                                user_id=referrer.id,
                                income_type='Guru Dakshina',
                                gross_amount=guru_dakshina_amount,
                                admin_deduction=gd_deductions['admin_deduction'],
                                tds_deduction=gd_deductions['tds_deduction'],
                                net_amount=gd_deductions['net_amount'],
                                withdrawal_wallet_amount=gd_deductions['withdrawal_wallet_amount'],
                                upgraded_wallet_amount=gd_deductions['upgraded_wallet_amount'],
                                business_date=calculation_date,
                                verification_status='Pending',
                                related_user_id=recipient_id,
                                notes=f"2% Royalty received from {recipient_id} (Manual Calculation)"
                            )
                            db.add(guru_dakshina_income)
                            db.flush()
                            auto_approve_and_credit_wallet(db, guru_dakshina_income)
                            total_incomes_created += 1
                
                # Create Direct Referral incomes with auto-approval
                direct_referral_bonuses = incomes.get('direct_referral', [])
                for bonus_data in direct_referral_bonuses:
                    bonus_amount = bonus_data['amount']
                    referred_user_id = bonus_data['referred_user_id']
                    
                    deductions = calculate_income_deductions_and_splits(bonus_amount, recipient.package_points, apply_guru_dakshina=True)
                    guru_dakshina_amount = deductions['guru_dakshina_deduction']
                    
                    pending_income = PendingIncome(
                        user_id=recipient_id,
                        income_type='Direct Referral',
                        gross_amount=bonus_amount,
                        admin_deduction=deductions['admin_deduction'],
                        tds_deduction=deductions['tds_deduction'],
                        net_amount=deductions['net_amount'],
                        withdrawal_wallet_amount=deductions['withdrawal_wallet_amount'],
                        upgraded_wallet_amount=deductions['upgraded_wallet_amount'],
                        business_date=calculation_date,
                        verification_status='Pending',
                        related_user_id=referred_user_id
                    )
                    db.add(pending_income)
                    db.flush()
                    auto_approve_and_credit_wallet(db, pending_income)
                    total_incomes_created += 1
                    
                    # Guru Dakshina for referrer
                    if guru_dakshina_amount > 0 and recipient.referrer_id:
                        referrer = db.query(User).filter(User.id == recipient.referrer_id).first()
                        if referrer and referrer.package_points > 0:
                            gd_deductions = calculate_income_deductions_and_splits(guru_dakshina_amount, referrer.package_points, apply_guru_dakshina=False)
                            
                            guru_dakshina_income = PendingIncome(
                                user_id=referrer.id,
                                income_type='Guru Dakshina',
                                gross_amount=guru_dakshina_amount,
                                admin_deduction=gd_deductions['admin_deduction'],
                                tds_deduction=gd_deductions['tds_deduction'],
                                net_amount=gd_deductions['net_amount'],
                                withdrawal_wallet_amount=gd_deductions['withdrawal_wallet_amount'],
                                upgraded_wallet_amount=gd_deductions['upgraded_wallet_amount'],
                                business_date=calculation_date,
                                verification_status='Pending',
                                related_user_id=recipient_id,
                                notes=f"2% Royalty received from {recipient_id} (Manual Calculation)"
                            )
                            db.add(guru_dakshina_income)
                            db.flush()
                            auto_approve_and_credit_wallet(db, guru_dakshina_income)
                            total_incomes_created += 1
                    
                    # Increment bonus count
                    recipient.referral_bonus_count = (recipient.referral_bonus_count or 0) + 1
                
                db.commit()
                
            except Exception as e:
                logger.error(f"Error creating incomes for recipient {recipient_id}: {e}")
                db.rollback()
                continue
        
        # Calculate total amount credited
        total_amount_credited = db.query(func.sum(PendingIncome.net_amount)).filter(
            PendingIncome.business_date == calculation_date,
            PendingIncome.verification_status == 'Completed'
        ).scalar() or 0.0
        
        # Log audit trail
        AuditLogger.log_action(
            db=db,
            user=current_admin,
            action='MANUAL_INCOME_CALCULATION',
            resource_type='Income',
            details={
                "calculation_date": request.calculation_date,
                "incomes_created": total_incomes_created,
                "total_amount_credited": round(float(total_amount_credited)),
                "recipients_count": len(recipient_incomes),
                "awards_count": awards_count,
                "bonanza_count": bonanza_count,
                "allowances_count": allowances_count
            }
        )
        
        logger.info(f"✅ Manual income calculation completed: {total_incomes_created} incomes, ₹{total_amount_credited:.2f} credited")
        
        return {
            "success": True,
            "message": f"Manual income calculation completed for {request.calculation_date}",
            "total_incomes_calculated": total_incomes_created,
            "total_amount_credited": round(float(total_amount_credited)),
            "calculation_date": request.calculation_date,
            "breakdown": {
                "direct_matching_ved": len(recipient_incomes),
                "awards": awards_count,
                "bonanza": bonanza_count,
                "field_allowances": allowances_count
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error in manual income calculation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Manual calculation failed: {str(e)}"
        )


# ===== UNIFIED APPROVAL ENDPOINTS (Multi-Role Income History Page) =====

class UnifiedApprovalRequest(BaseModel):
    income_ids: List[int]
    notes: Optional[str] = None

@router.post("/admin/approve-unified")
async def admin_approve_unified(
    request: UnifiedApprovalRequest,
    current_admin: User = Depends(get_current_admin_user_hybrid),
    db: Session = Depends(get_db)
):
    """
    Unified Admin Approval Endpoint
    Used by Income History page for Admin role
    Approves: Pending → Admin Verified
    """
    try:
        # DC Protocol: Menu-based access control - page assignment = full access
        # user_type = getattr(current_admin, 'staff_type', None) or getattr(current_admin, 'user_type', None)
        # is_staff = hasattr(current_admin, 'emp_code')
        # if user_type not in ["Admin", "Super Admin", "RVZ ID", "VGK4U Supreme", "VGK4U", "staff"] and not is_staff:
        #     raise HTTPException(
        #         status_code=status.HTTP_403_FORBIDDEN,
        #         detail="Admin access required"
        #     )
        
        approved_count = 0
        skipped = []
        
        for income_id in request.income_ids:
            pending_income = db.query(PendingIncome).filter(
                PendingIncome.id == income_id,
                PendingIncome.verification_status == 'Pending'
            ).first()
            
            if pending_income:
                pending_income.verification_status = 'Admin Verified'
                pending_income.admin_verified_by_id = _resolve_actor_id(current_admin)
                pending_income.admin_verified_at = get_indian_time()
                if request.notes:
                    pending_income.notes = request.notes
                approved_count += 1
            else:
                skipped.append(income_id)
        
        db.commit()
        
        AuditLogger.log_action(
            db=db,
            user=current_admin,
            action='ADMIN_APPROVE_UNIFIED',
            resource_type='PendingIncome',
            details={"approved_count": approved_count, "income_ids": request.income_ids}
        )
        
        message = f"✅ {approved_count} income(s) approved as Admin"
        if skipped:
            message += f" | {len(skipped)} skipped (not Pending)"
        
        return {
            "success": True,
            "message": message,
            "approved_count": approved_count,
            "skipped_count": len(skipped)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Admin approval failed: {str(e)}"
        )


@router.post("/super-admin/approve-unified")
async def super_admin_approve_unified(
    request: UnifiedApprovalRequest,
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db)
):
    """
    Unified Super Admin Approval Endpoint
    Used by Income History page for Super Admin role
    Approves: Pending OR Admin Verified → Super Admin Verified (can skip Admin)
    """
    try:
        approved_count = 0
        skipped = []
        
        for income_id in request.income_ids:
            # Super Admin can approve Pending (skip Admin) OR Admin Verified
            pending_income = db.query(PendingIncome).filter(
                PendingIncome.id == income_id,
                PendingIncome.verification_status.in_(['Pending', 'Admin Verified'])
            ).first()
            
            if pending_income:
                pending_income.verification_status = 'Super Admin Verified'
                pending_income.super_admin_verified_by_id = _resolve_actor_id(current_user)
                pending_income.super_admin_verified_at = get_indian_time()
                # If skipped Admin, mark Admin fields as well (for audit trail)
                if not pending_income.admin_verified_by_id:
                    pending_income.admin_verified_by_id = _resolve_actor_id(current_user)
                    pending_income.admin_verified_at = get_indian_time()
                if request.notes:
                    pending_income.notes = request.notes
                approved_count += 1
            else:
                skipped.append(income_id)
        
        db.commit()
        
        AuditLogger.log_action(
            db=db,
            user=current_user,
            action='SUPER_ADMIN_APPROVE_UNIFIED',
            resource_type='PendingIncome',
            details={"approved_count": approved_count, "income_ids": request.income_ids}
        )
        
        message = f"✅ {approved_count} income(s) verified by Super Admin"
        if skipped:
            message += f" | {len(skipped)} skipped (already verified or completed)"
        
        return {
            "success": True,
            "message": message,
            "approved_count": approved_count,
            "skipped_count": len(skipped)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Super Admin approval failed: {str(e)}"
        )


@router.post("/finance/pay-unified")
async def finance_pay_unified(
    request: UnifiedApprovalRequest,
    current_user: User = Depends(require_finance_admin),
    db: Session = Depends(get_db)
):
    """
    Unified Finance Admin Payment Endpoint
    Used by Income History page for Finance Admin role
    Processes: Super Admin Verified → Completed (transfers to wallet)
    """
    try:
        from app.core.wallet_sync import sync_user_wallet_realtime
        
        paid_count = 0
        skipped = []
        total_paid = Decimal('0')
        
        for income_id in request.income_ids:
            pending_income = db.query(PendingIncome).filter(
                PendingIncome.id == income_id,
                PendingIncome.verification_status == 'Super Admin Verified'
            ).first()
            
            if pending_income:
                # Mark as Completed
                pending_income.verification_status = 'Completed'
                pending_income.accounts_paid_by_id = _resolve_actor_id(current_user)
                pending_income.accounts_paid_at = get_indian_time()
                if request.notes:
                    pending_income.notes = request.notes
                
                # Sync wallet (triggers transfer from Earning → Withdrawable)
                sync_user_wallet_realtime(db, pending_income.user_id)
                
                paid_count += 1
                total_paid += pending_income.net_amount
            else:
                skipped.append(income_id)
        
        db.commit()
        
        AuditLogger.log_action(
            db=db,
            user=current_user,
            action='FINANCE_PAY_UNIFIED',
            resource_type='PendingIncome',
            details={
                "paid_count": paid_count,
                "total_paid": float(total_paid),
                "income_ids": request.income_ids
            }
        )
        
        message = f"✅ {paid_count} income(s) paid successfully (₹{int(total_paid):,} transferred to wallets)"
        if skipped:
            message += f" | {len(skipped)} skipped (not Super Admin Verified)"
        
        return {
            "success": True,
            "message": message,
            "paid_count": paid_count,
            "total_paid": float(total_paid),
            "skipped_count": len(skipped)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Finance payment failed: {str(e)}"
        )


# ===== UNIFIED INCOME MANAGEMENT (DC Protocol Feb 2026) =====
# Single endpoint for Staff Portal to view, validate, approve, and process all incomes

class UnifiedIncomeActionRequest(BaseModel):
    income_ids: List[int]
    action: str  # 'verify', 'approve', 'pay'
    notes: Optional[str] = None

@router.get("/staff/unified-income-list")
async def get_unified_income_list(
    response: Response,
    status_filter: Optional[str] = None,
    user_id: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    income_type: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    current_user = Depends(get_current_admin_user_hybrid),
    db: Session = Depends(get_db)
):
    """
    UNIFIED INCOME LIST - DC Protocol (Feb 2026)
    Single endpoint for Staff Portal to view all incomes across all statuses
    with action buttons based on current status.
    
    Returns incomes with available_actions field indicating what actions are possible:
    - Pending: ['verify'] (Admin can verify)
    - Admin Verified: ['approve'] (Super Admin can approve)
    - Super Admin Verified: ['pay'] (Finance can pay)
    - Completed: [] (No actions)
    """
    add_no_cache_headers(response)
    
    try:
        query = db.query(PendingIncome)
        
        # Apply filters
        if status_filter and status_filter.lower() != 'all':
            query = query.filter(PendingIncome.verification_status == status_filter)
        
        if user_id:
            query = query.filter(PendingIncome.user_id == user_id)
        
        if income_type and income_type.lower() != 'all':
            query = query.filter(PendingIncome.income_type == income_type)
        
        if from_date:
            from_date_obj = datetime.strptime(from_date, '%Y-%m-%d').date()
            query = query.filter(PendingIncome.business_date >= from_date_obj)
        
        if to_date:
            to_date_obj = datetime.strptime(to_date, '%Y-%m-%d').date()
            query = query.filter(PendingIncome.business_date <= to_date_obj)
        
        # Get total count before pagination
        total_count = query.count()
        
        # Apply pagination and ordering
        query = query.order_by(PendingIncome.business_date.desc())
        pending_incomes = query.offset(skip).limit(limit).all()
        
        # Get user names and KYC status
        user_ids = list(set([pi.user_id for pi in pending_incomes]))
        users = db.query(User).filter(User.id.in_(user_ids)).all() if user_ids else []
        user_map = {u.id: {'name': u.name, 'kyc_status': u.kyc_status} for u in users}
        
        # DC Protocol Feb 2026: Get group eligibility for each user (1:1 direct referrals both sides)
        group_eligibility_map = {}
        for uid in user_ids:
            try:
                eligibility = check_direct_referrals_both_sides(db, uid, return_details=True)
                if eligibility.get('is_eligible'):
                    group_eligibility_map[uid] = {'status': 'Yes', 'message': 'Both Groups Active'}
                else:
                    group_a = eligibility.get('group_a_points', 0)
                    group_b = eligibility.get('group_b_points', 0)
                    if group_a < 1.0 and group_b < 1.0:
                        group_eligibility_map[uid] = {'status': 'No', 'message': 'Both Groups Missing'}
                    elif group_a < 1.0:
                        group_eligibility_map[uid] = {'status': 'Group A Missing', 'message': 'Group A Missing'}
                    else:
                        group_eligibility_map[uid] = {'status': 'Group B Missing', 'message': 'Group B Missing'}
            except Exception:
                group_eligibility_map[uid] = {'status': 'Unknown', 'message': 'Error checking'}
        
        # Define action mapping based on status
        def get_available_actions(status):
            action_map = {
                'Pending': ['verify'],
                'Admin Verified': ['approve'],
                'Super Admin Verified': ['pay'],
                'Completed': [],
                'Rejected': []
            }
            return action_map.get(status, [])
        
        # Get summary by status
        status_summary = db.query(
            PendingIncome.verification_status,
            func.count(PendingIncome.id).label('count'),
            func.sum(PendingIncome.net_amount).label('total_amount')
        ).group_by(PendingIncome.verification_status).all()
        
        summary = {
            s.verification_status: {
                'count': s.count,
                'total_amount': float(s.total_amount or 0)
            } for s in status_summary
        }
        
        return {
            "success": True,
            "total_count": total_count,
            "showing": len(pending_incomes),
            "skip": skip,
            "limit": limit,
            "summary": summary,
            "data": [
                {
                    "id": pi.id,
                    "user_id": pi.user_id,
                    "user_name": user_map.get(pi.user_id, {}).get('name', 'Unknown'),
                    "income_type": pi.income_type,
                    "gross_amount": round(float(pi.gross_amount)),
                    "admin_deduction": round(float(pi.admin_deduction or 0)),
                    "tds_deduction": round(float(pi.tds_deduction or 0)),
                    "net_amount": round(float(pi.net_amount)),
                    "withdrawal_wallet": round(float(pi.withdrawal_wallet_amount or 0)),
                    "upgrade_wallet": round(float(pi.upgraded_wallet_amount or 0)),
                    "business_date": pi.business_date.isoformat(),
                    "verification_status": pi.verification_status,
                    "kyc_status": user_map.get(pi.user_id, {}).get('kyc_status', 'Unknown'),
                    "group_eligibility": group_eligibility_map.get(pi.user_id, {}).get('status', 'Unknown'),
                    "group_eligibility_message": group_eligibility_map.get(pi.user_id, {}).get('message', ''),
                    "admin_verified_by": pi.admin_verified_by_id,
                    "admin_verified_at": pi.admin_verified_at.isoformat() if pi.admin_verified_at else None,
                    "super_admin_verified_by": pi.super_admin_verified_by_id,
                    "super_admin_verified_at": pi.super_admin_verified_at.isoformat() if pi.super_admin_verified_at else None,
                    "accounts_paid_by": pi.accounts_paid_by_id,
                    "accounts_paid_at": pi.accounts_paid_at.isoformat() if pi.accounts_paid_at else None,
                    "available_actions": get_available_actions(pi.verification_status),
                    "notes": pi.notes
                }
                for pi in pending_incomes
            ]
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid date format. Use YYYY-MM-DD. Error: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Server error: {str(e)}"
        )


@router.post("/staff/unified-income-action")
async def perform_unified_income_action(
    request: UnifiedIncomeActionRequest,
    current_user = Depends(get_current_admin_user_hybrid),
    db: Session = Depends(get_db)
):
    """
    UNIFIED INCOME ACTION - DC Protocol (Feb 2026)
    Single endpoint for Staff Portal to perform all income actions:
    - verify: Pending → Admin Verified
    - approve: Pending/Admin Verified → Super Admin Verified
    - pay: Super Admin Verified → Completed (transfers to wallet)
    
    Staff with page-level permissions can perform all actions.
    """
    from app.core.wallet_sync import sync_user_wallet_realtime
    
    try:
        action = request.action.lower()
        processed_count = 0
        skipped = []
        total_amount = Decimal('0')
        
        for income_id in request.income_ids:
            pending_income = db.query(PendingIncome).filter(PendingIncome.id == income_id).first()
            
            if not pending_income:
                skipped.append({"id": income_id, "reason": "Not found"})
                continue
            
            current_status = pending_income.verification_status
            
            if action == 'verify':
                # Admin Verification: Pending → Admin Verified
                if current_status != 'Pending':
                    skipped.append({"id": income_id, "reason": f"Status is {current_status}, expected Pending"})
                    continue
                pending_income.verification_status = 'Admin Verified'
                pending_income.admin_verified_by_id = _resolve_actor_id(current_user)
                pending_income.admin_verified_at = get_indian_time()
                
            elif action == 'approve':
                # Super Admin Approval: Pending or Admin Verified → Super Admin Verified
                if current_status not in ['Pending', 'Admin Verified']:
                    skipped.append({"id": income_id, "reason": f"Status is {current_status}, expected Pending or Admin Verified"})
                    continue
                pending_income.verification_status = 'Super Admin Verified'
                pending_income.super_admin_verified_by_id = _resolve_actor_id(current_user)
                pending_income.super_admin_verified_at = get_indian_time()
                # If skipping from Pending, also mark admin verified
                if current_status == 'Pending':
                    pending_income.admin_verified_by_id = _resolve_actor_id(current_user)
                    pending_income.admin_verified_at = get_indian_time()
                
            elif action == 'pay':
                # Finance Payment: Super Admin Verified → Completed
                if current_status != 'Super Admin Verified':
                    skipped.append({"id": income_id, "reason": f"Status is {current_status}, expected Super Admin Verified"})
                    continue
                pending_income.verification_status = 'Completed'
                pending_income.accounts_paid_by_id = _resolve_actor_id(current_user)
                pending_income.accounts_paid_at = get_indian_time()
                # Sync wallet (triggers transfer from Earning → Withdrawable)
                sync_user_wallet_realtime(db, pending_income.user_id)
                total_amount += pending_income.net_amount
                
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid action: {action}. Use 'verify', 'approve', or 'pay'"
                )
            
            if request.notes:
                pending_income.notes = request.notes
            
            processed_count += 1
        
        db.commit()
        
        # Log the action
        actor_id = str(getattr(current_user, 'id', getattr(current_user, 'emp_code', 'staff')))
        AuditLogger.log_action(
            db=db,
            user=current_user,
            action=f'UNIFIED_INCOME_{action.upper()}',
            resource_type='PendingIncome',
            details={
                "processed_count": processed_count,
                "skipped_count": len(skipped),
                "income_ids": request.income_ids,
                "total_amount": float(total_amount) if action == 'pay' else None
            }
        )
        
        action_labels = {
            'verify': 'verified (Admin)',
            'approve': 'approved (Super Admin)',
            'pay': 'paid (Finance)'
        }
        
        message = f"✅ {processed_count} income(s) {action_labels.get(action, action)}"
        if action == 'pay' and total_amount > 0:
            message += f" (₹{int(total_amount):,} transferred)"
        if skipped:
            message += f" | {len(skipped)} skipped"
        
        return {
            "success": True,
            "message": message,
            "action": action,
            "processed_count": processed_count,
            "skipped": skipped,
            "total_amount": float(total_amount) if action == 'pay' else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Action failed: {str(e)}"
        )


@router.get("/staff/user-wise-income-summary")
async def get_user_wise_income_summary(
    response: Response,
    status_filter: Optional[str] = None,
    user_id: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    income_type: Optional[str] = None,
    current_staff = Depends(require_staff_with_page_access),
    db: Session = Depends(get_db)
):
    add_no_cache_headers(response)
    try:
        query = db.query(PendingIncome)

        from_date_obj = None
        to_date_obj = None

        if from_date:
            from_date_obj = datetime.strptime(from_date, '%Y-%m-%d').date()
            query = query.filter(PendingIncome.business_date >= from_date_obj)
        if to_date:
            to_date_obj = datetime.strptime(to_date, '%Y-%m-%d').date()
            query = query.filter(PendingIncome.business_date <= to_date_obj)
        if user_id:
            query = query.filter(PendingIncome.user_id == user_id)
        if income_type and income_type.lower() != 'all':
            reverse_rebrand = {v: k for k, v in INCOME_TYPE_REBRAND.items()}
            db_income_type = reverse_rebrand.get(income_type, income_type)
            query = query.filter(PendingIncome.income_type == db_income_type)
        if status_filter and status_filter.lower() != 'all':
            if status_filter == 'Cleared':
                query = query.filter(PendingIncome.business_date < STAFF_WORKFLOW_CUTOFF)
            else:
                query = query.filter(PendingIncome.verification_status == status_filter)
                query = query.filter(PendingIncome.business_date >= STAFF_WORKFLOW_CUTOFF)

        all_incomes = query.order_by(PendingIncome.user_id).all()

        user_ids = list(set([pi.user_id for pi in all_incomes]))
        users = db.query(User).filter(User.id.in_(user_ids)).all() if user_ids else []
        user_map = {u.id: u.name for u in users}

        user_agg = {}
        for pi in all_incomes:
            uid = pi.user_id
            if uid not in user_agg:
                user_agg[uid] = {
                    'user_id': uid,
                    'user_name': user_map.get(uid, 'Unknown'),
                    'total_gross': 0,
                    'total_net': 0,
                    'total_deductions': 0,
                    'cleared_amount': 0,
                    'pending_amount': 0,
                    'validated_amount': 0,
                    'completed_amount': 0,
                    'total_records': 0,
                    'income_dates': set(),
                    'income_types': set(),
                }
            agg = user_agg[uid]
            gross = float(pi.gross_amount or 0)
            net = float(pi.net_amount or 0)
            deductions = float(pi.admin_deduction or 0) + float(pi.tds_deduction or 0) + float(pi.gurudakshina_deduction or 0)
            agg['total_gross'] += gross
            agg['total_net'] += net
            agg['total_deductions'] += deductions
            agg['total_records'] += 1
            agg['income_types'].add(get_display_income_type(pi.income_type))

            bdate = pi.business_date.date() if hasattr(pi.business_date, 'date') and callable(pi.business_date.date) else pi.business_date
            agg['income_dates'].add(bdate.isoformat() if bdate else '')

            if bdate < STAFF_WORKFLOW_CUTOFF:
                agg['cleared_amount'] += net
            elif pi.verification_status == 'Pending':
                agg['pending_amount'] += net
            elif pi.verification_status == 'Staff Validated':
                agg['validated_amount'] += net
            elif pi.verification_status == 'Completed':
                agg['completed_amount'] += net

        data = []
        for uid, agg in user_agg.items():
            data.append({
                'user_id': agg['user_id'],
                'user_name': agg['user_name'],
                'total_gross': round(agg['total_gross']),
                'total_net': round(agg['total_net']),
                'total_deductions': round(agg['total_deductions']),
                'cleared_amount': round(agg['cleared_amount']),
                'pending_amount': round(agg['pending_amount']),
                'validated_amount': round(agg['validated_amount']),
                'completed_amount': round(agg['completed_amount']),
                'total_records': agg['total_records'],
                'total_dates': len(agg['income_dates']),
                'income_types': sorted(list(agg['income_types'])),
            })

        grand_total_gross = sum(d['total_gross'] for d in data)
        grand_total_net = sum(d['total_net'] for d in data)
        grand_cleared = sum(d['cleared_amount'] for d in data)
        grand_pending = sum(d['pending_amount'] for d in data)
        grand_validated = sum(d['validated_amount'] for d in data)
        grand_completed = sum(d['completed_amount'] for d in data)

        stats = {
            'total_users': len(data),
            'total_records': sum(d['total_records'] for d in data),
            'total_gross': round(grand_total_gross),
            'total_net': round(grand_total_net),
            'cleared_amount': round(grand_cleared),
            'cleared_users': sum(1 for d in data if d['cleared_amount'] > 0),
            'pending_amount': round(grand_pending),
            'pending_users': sum(1 for d in data if d['pending_amount'] > 0),
            'validated_amount': round(grand_validated),
            'validated_users': sum(1 for d in data if d['validated_amount'] > 0),
            'completed_amount': round(grand_completed),
            'completed_users': sum(1 for d in data if d['completed_amount'] > 0),
            'overall_pending_amount': round(grand_pending + grand_validated),
            'overall_pending_users': sum(1 for d in data if (d['pending_amount'] + d['validated_amount']) > 0),
        }

        return {
            "success": True,
            "count": len(data),
            "stats": stats,
            "data": data
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid date format. Use YYYY-MM-DD. Error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Server error: {str(e)}")


@router.get("/staff/user-income-datewise/{target_user_id}")
async def get_user_income_datewise(
    target_user_id: str,
    response: Response,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    income_type: Optional[str] = None,
    current_staff = Depends(require_staff_with_page_access),
    db: Session = Depends(get_db)
):
    add_no_cache_headers(response)
    try:
        query = db.query(PendingIncome).filter(PendingIncome.user_id == target_user_id)

        if from_date:
            from_date_obj = datetime.strptime(from_date, '%Y-%m-%d').date()
            query = query.filter(PendingIncome.business_date >= from_date_obj)
        if to_date:
            to_date_obj = datetime.strptime(to_date, '%Y-%m-%d').date()
            query = query.filter(PendingIncome.business_date <= to_date_obj)
        if income_type and income_type.lower() != 'all':
            reverse_rebrand = {v: k for k, v in INCOME_TYPE_REBRAND.items()}
            db_income_type = reverse_rebrand.get(income_type, income_type)
            query = query.filter(PendingIncome.income_type == db_income_type)

        incomes = query.order_by(PendingIncome.business_date.desc(), PendingIncome.income_type).all()

        user = db.query(User).filter(User.id == target_user_id).first()
        user_name = user.name if user else "Unknown"

        income_type_order = ['Direct Referral', 'Matching Referral', 'Ved Income', 'Guru Dakshina']
        all_types_present = sorted(set(pi.income_type for pi in incomes), key=lambda t: income_type_order.index(t) if t in income_type_order else 99)
        display_types = [get_display_income_type(t) for t in all_types_present]

        date_groups = {}
        for pi in incomes:
            bdate = pi.business_date.date() if hasattr(pi.business_date, 'date') and callable(pi.business_date.date) else pi.business_date
            bdate_str = bdate.isoformat() if bdate else ''
            if bdate_str not in date_groups:
                date_groups[bdate_str] = []
            date_groups[bdate_str].append(pi)

        date_rows = []
        type_totals = {t: {'gross': 0, 'net': 0, 'deductions': 0} for t in all_types_present}
        grand_gross = 0
        grand_net = 0
        grand_deductions = 0

        for bdate_str in sorted(date_groups.keys(), reverse=True):
            pis = date_groups[bdate_str]
            bdate_obj = datetime.strptime(bdate_str, '%Y-%m-%d').date() if bdate_str else None

            if bdate_obj and bdate_obj < STAFF_WORKFLOW_CUTOFF:
                display_status = 'Cleared'
            else:
                statuses = [pi.verification_status for pi in pis]
                priority = {'Pending': 0, 'Staff Validated': 1, 'Completed': 2}
                display_status = min(statuses, key=lambda s: priority.get(s, 99))

            type_columns = {}
            row_gross = 0
            row_net = 0
            row_deductions = 0

            for t in all_types_present:
                type_pis = [pi for pi in pis if pi.income_type == t]
                if type_pis:
                    t_gross = round(sum(float(pi.gross_amount or 0) for pi in type_pis))
                    t_ded = round(sum(float(pi.admin_deduction or 0) + float(pi.tds_deduction or 0) + float(pi.gurudakshina_deduction or 0) for pi in type_pis))
                    t_net = round(sum(float(pi.net_amount or 0) for pi in type_pis))
                    type_columns[get_display_income_type(t)] = {'gross': t_gross, 'deductions': t_ded, 'net': t_net}
                    type_totals[t]['gross'] += t_gross
                    type_totals[t]['net'] += t_net
                    type_totals[t]['deductions'] += t_ded
                    row_gross += t_gross
                    row_net += t_net
                    row_deductions += t_ded
                else:
                    type_columns[get_display_income_type(t)] = {'gross': 0, 'deductions': 0, 'net': 0}

            grand_gross += row_gross
            grand_net += row_net
            grand_deductions += row_deductions

            date_rows.append({
                'date': bdate_str,
                'status': display_status,
                'types': type_columns,
                'sub_total_gross': row_gross,
                'sub_total_deductions': row_deductions,
                'sub_total_net': row_net,
            })

        type_footer_totals = []
        for t in all_types_present:
            type_footer_totals.append({
                'type': get_display_income_type(t),
                'gross': round(type_totals[t]['gross']),
                'deductions': round(type_totals[t]['deductions']),
                'net': round(type_totals[t]['net']),
            })

        summary = {
            'total_gross': round(grand_gross),
            'total_net': round(grand_net),
            'total_deductions': round(grand_deductions),
            'total_dates': len(date_rows),
            'total_records': len(incomes),
        }

        return {
            "success": True,
            "user_id": target_user_id,
            "user_name": user_name,
            "income_types": display_types,
            "summary": summary,
            "type_totals": type_footer_totals,
            "date_rows": date_rows,
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid date format. Use YYYY-MM-DD. Error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Server error: {str(e)}")


@router.post("/staff/repair-matching-snapshots")
async def repair_matching_snapshots(
    current_staff = Depends(require_staff_with_page_access),
    db: Session = Depends(get_db)
):
    from sqlalchemy import text as sa_text
    from app.services.sql_utils import identify_consumed_members_sql, identify_exempted_members_sql, build_matching_contributor_snapshot, build_exempted_matching_snapshot
    import json

    all_records = db.execute(sa_text("""
        SELECT id, user_id, pairs_matched, left_points_consumed, right_points_consumed,
               matching_contributors_snapshot, match_type, bev_user_id, business_date
        FROM pending_income
        WHERE income_type = 'Matching Referral'
        AND (pairs_matched > 0 OR (matching_contributors_snapshot IS NOT NULL AND matching_contributors_snapshot::text LIKE '%"is_exempted": true%'))
        ORDER BY user_id ASC, business_date ASC, id ASC
    """)).fetchall()

    repaired = 0
    skipped = 0
    failed = 0
    details = []

    for rec in all_records:
        try:
            snap = rec.matching_contributors_snapshot
            if isinstance(snap, str):
                snap = json.loads(snap)

            needs_rebuild = False
            is_exempted = False

            if not snap:
                needs_rebuild = True
            else:
                is_exempted = snap.get('is_exempted', False)
                if 'pairs' in snap:
                    for p in snap.get('pairs', []):
                        if not p.get('left') or not p.get('right'):
                            needs_rebuild = True
                            break
                elif is_exempted:
                    left_zero = snap.get('left_zero_point_members', [])
                    right_zero = snap.get('right_zero_point_members', [])
                    if not left_zero and not right_zero:
                        needs_rebuild = True

            if not needs_rebuild:
                from app.core.scheduler import _get_actual_business_date
                from datetime import datetime as _dt2
                old_d = rec.business_date
                if hasattr(old_d, 'date') and callable(old_d.date):
                    old_d_only = old_d.date()
                elif isinstance(old_d, str):
                    old_d_only = _dt2.strptime(str(old_d)[:10], '%Y-%m-%d').date()
                else:
                    old_d_only = old_d

                all_m = {}
                if snap.get('pairs'):
                    all_m = {
                        'left': [m for p in snap['pairs'] for m in p.get('left', [])],
                        'right': [m for p in snap['pairs'] for m in p.get('right', [])]
                    }
                elif is_exempted:
                    all_m = {
                        'left': snap.get('left_zero_point_members', []),
                        'right': snap.get('right_zero_point_members', [])
                    }
                if all_m:
                    correct_d = _get_actual_business_date(all_m, old_d_only)
                    if correct_d != old_d_only:
                        dup_check = db.execute(sa_text("""
                            SELECT id FROM pending_income
                            WHERE user_id = :uid AND income_type = 'Matching Referral'
                            AND DATE(business_date) = :bdate AND id != :rec_id
                        """), {"uid": rec.user_id, "bdate": correct_d, "rec_id": rec.id}).fetchone()
                        if not dup_check:
                            db.execute(sa_text("""
                                UPDATE pending_income SET business_date = :bdate WHERE id = :id
                            """), {"bdate": correct_d, "id": rec.id})
                            repaired += 1
                            details.append({
                                "id": rec.id,
                                "mnr_id": rec.bev_user_id,
                                "date": str(rec.business_date),
                                "status": "date_corrected",
                                "date_corrected": f"{old_d_only} → {correct_d}"
                            })
                        else:
                            skipped += 1
                        continue
                skipped += 1
                continue

            left_consumed = float(rec.left_points_consumed) if rec.left_points_consumed else 0
            right_consumed = float(rec.right_points_consumed) if rec.right_points_consumed else 0
            match_type = (snap.get('match_type', rec.match_type or 'normal') if snap else rec.match_type) or 'normal'

            rebuilt = None
            if is_exempted and snap:
                left_zero_consumed = snap.get('exempted_left_consumed', 0)
                right_zero_consumed = snap.get('exempted_right_consumed', 0)
                if left_consumed > 0 or right_consumed > 0 or left_zero_consumed > 0 or right_zero_consumed > 0:
                    exempted_members = identify_exempted_members_sql(
                        db, rec.user_id, left_zero_consumed, right_zero_consumed
                    )
                    rebuilt = build_exempted_matching_snapshot(
                        db, rec.user_id, rec.pairs_matched,
                        left_consumed, right_consumed,
                        left_zero_consumed, right_zero_consumed,
                        consumed_members=exempted_members
                    )
            elif left_consumed > 0 or right_consumed > 0:
                consumed = identify_consumed_members_sql(
                    db, rec.user_id, left_consumed, right_consumed,
                    exclude_record_id=rec.id
                )
                rebuilt = build_matching_contributor_snapshot(
                    db, rec.user_id, rec.pairs_matched,
                    left_consumed, right_consumed, match_type,
                    consumed_members=consumed
                )

            if not rebuilt or _snapshot_has_na(rebuilt):
                if not rebuilt and left_consumed == 0 and right_consumed == 0:
                    status_msg = "unfixable_zero_consumed"
                else:
                    status_msg = "still_na_after_rebuild"
                failed += 1
                details.append({
                    "id": rec.id,
                    "mnr_id": rec.bev_user_id,
                    "date": str(rec.business_date),
                    "status": status_msg
                })
            else:
                from app.core.scheduler import _get_actual_business_date
                from datetime import datetime as _dt
                old_date = rec.business_date
                if hasattr(old_date, 'date') and callable(old_date.date):
                    old_date_only = old_date.date()
                elif isinstance(old_date, str):
                    old_date_only = _dt.strptime(str(old_date)[:10], '%Y-%m-%d').date()
                else:
                    old_date_only = old_date

                all_members_for_date = {}
                if rebuilt.get('pairs'):
                    all_members_for_date = {
                        'left': [m for p in rebuilt['pairs'] for m in p.get('left', [])],
                        'right': [m for p in rebuilt['pairs'] for m in p.get('right', [])]
                    }
                elif rebuilt.get('left_zero_point_members') or rebuilt.get('right_zero_point_members'):
                    all_members_for_date = {
                        'left': rebuilt.get('left_zero_point_members', []),
                        'right': rebuilt.get('right_zero_point_members', [])
                    }
                corrected_date = _get_actual_business_date(all_members_for_date, old_date_only)
                date_changed = corrected_date != old_date_only

                update_date = corrected_date
                if date_changed:
                    dup_check = db.execute(sa_text("""
                        SELECT id FROM pending_income
                        WHERE user_id = :uid AND income_type = 'Matching Referral'
                        AND DATE(business_date) = :bdate AND id != :rec_id
                    """), {"uid": rec.user_id, "bdate": corrected_date, "rec_id": rec.id}).fetchone()
                    if dup_check:
                        update_date = old_date_only
                        date_changed = False

                db.execute(sa_text("""
                    UPDATE pending_income 
                    SET matching_contributors_snapshot = :snap,
                        business_date = :bdate
                    WHERE id = :id
                """), {"snap": json.dumps(rebuilt, default=str), "id": rec.id, "bdate": update_date})
                repaired += 1
                detail_entry = {
                    "id": rec.id,
                    "mnr_id": rec.bev_user_id,
                    "date": str(rec.business_date),
                    "status": "repaired"
                }
                if date_changed:
                    detail_entry["date_corrected"] = f"{old_date_only} → {corrected_date}"
                details.append(detail_entry)

        except Exception as e:
            failed += 1
            logger.error(f"Repair failed for income {rec.id}: {e}")

    db.commit()

    return {
        "success": True,
        "total_checked": len(all_records),
        "repaired": repaired,
        "skipped_ok": skipped,
        "failed": failed,
        "details": details
    }


# ── DC-STATUTORY-CANCEL-001: Reject / void a PendingIncome entry ──────────────
class RejectIncomeRequest(BaseModel):
    reason: str
    notes: Optional[str] = None


@router.post("/admin/reject-income/{income_id}")
def reject_income(
    income_id: int,
    request: RejectIncomeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_finance_admin),
):
    """
    DC-STATUTORY-CANCEL-001: Reject (void) a PendingIncome entry that has not yet
    reached 'Completed' status.

    Actions taken:
      1. Sets verification_status = 'Rejected' with audit fields.
      2. Calls handle_statutory_income_cancellation — reverses any DUTIES_TAXES /
         INCOME statutory GL rows that were posted by auto_post_statutory_deductions.
         If no GL rows exist (entry rejected before it was ever completed) the reversal
         is a no-op and the call returns cleanly.

    Allowed from: Pending | Admin Verified | Super Admin Verified | Staff Validated.
    Blocked for:  Completed (already paid out — reversals require a separate process).
    """
    income = db.query(PendingIncome).filter(PendingIncome.id == income_id).first()
    if not income:
        raise HTTPException(status_code=404, detail="Income record not found")

    if income.verification_status == 'Completed':
        raise HTTPException(
            status_code=400,
            detail="Cannot reject an already-Completed income. Raise a separate reversal."
        )
    if income.verification_status == 'Rejected':
        raise HTTPException(status_code=400, detail="Income is already Rejected")

    prev_status = income.verification_status
    now = get_indian_time()
    staff_id = str(getattr(current_user, 'emp_code', None) or current_user.id)

    income.verification_status = 'Rejected'
    income.rejection_reason     = request.reason
    income.rejected_by_id       = str(current_user.id)
    income.rejected_at          = now
    if request.notes:
        income.notes = ((income.notes or '') + f'\nRejected [{staff_id}]: {request.notes}').strip()

    # Reverse statutory GL entries (idempotent — no-op if nothing was posted)
    try:
        from app.services.staff_accounts_service import LedgerPostingService as _LPS
        _co_id = int(getattr(current_user, 'company_id', None) or 1)
        _LPS.handle_statutory_income_cancellation(
            db=db,
            company_id=_co_id,
            pending_income_id=income_id,
            cancelled_by_id=None,
        )
    except Exception as _rev_e:
        logger.warning(f'[DC-STATUTORY-CANCEL-001] GL reversal non-fatal for PI#{income_id}: {_rev_e}')

    db.commit()

    return {
        "success":       True,
        "income_id":     income_id,
        "user_id":       income.user_id,
        "income_type":   income.income_type,
        "prev_status":   prev_status,
        "new_status":    "Rejected",
        "rejected_by":   staff_id,
        "rejected_at":   now.isoformat(),
        "reason":        request.reason,
    }
