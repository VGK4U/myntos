"""
RVZ Supreme Withdrawal Management Endpoints
Skip-level approval system for RVZ ID role

DC Protocol Compliance:
- Uses existing pending_income and withdrawal tables (single source of truth)
- No new tables created
- Sets BOTH verified_at AND approved_at in single transaction for skip-level
"""

from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.orm import Session, joinedload, aliased
from sqlalchemy import update, text, func, case, exists, select, and_
from typing import List, Dict, Optional
from pydantic import BaseModel
from datetime import datetime, date, timedelta
from decimal import Decimal

import logging

from app.core.database import get_db
from app.core.security import get_current_admin_user_hybrid

logger = logging.getLogger(__name__)
from app.models.user import User
from app.models.transaction import PendingIncome
from app.models.withdrawal import WithdrawalRequest
from app.models.system_control import AppSettings
from app.models.ev_model import EVModel
from app.models.field_allowance import AllowanceTierDefinition
from app.models.awards import DirectAwardTier, MatchingAwardTier, UserAwardProgress, UserMatchingAwardProgress
from app.models.bonanza import Bonanza, DynamicBonanzaHistory  # DC Protocol: BonanzaProgress deprecated
from app.services.wallet_sync_service import WalletSyncService
from app.services.procurement_service import ProcurementService
from app.core.audit import AuditLogger
from app.models.base import get_indian_time

router = APIRouter(prefix="/rvz-supreme", tags=["RVZ Supreme"])


def _resolve_actor_id(current_user) -> str:
    from app.models.staff import StaffEmployee
    if isinstance(current_user, StaffEmployee):
        return str(current_user.emp_code or current_user.id)
    return str(current_user.id)


class SupremeApproveIncomeRequest(BaseModel):
    pending_income_ids: List[int]


class SupremeApproveWithdrawalRequest(BaseModel):
    withdrawal_ids: List[int]


class SupremeTransferRequest(BaseModel):
    withdrawal_ids: List[int]
    utr_number: str = None


@router.post("/income/supreme-approve")
async def supreme_approve_income(
    request: SupremeApproveIncomeRequest,
    current_user: User = Depends(get_current_admin_user_hybrid),
    db: Session = Depends(get_db)
):
    """
    RVZ Supreme Income Approval - WVV PROTOCOL COMPLIANT
    
    CORRECTED FLOW (WVV Protocol):
    1. Approve incomes → verification_status = 'Super Admin Verified'
    2. Finance must still process bank payment → 'Completed'
    3. No auto wallet sync or withdrawal creation
    
    DC Protocol: Updates pending_income status only
    WVV Protocol: RVZ verifies, Finance completes bank payment
    """
    try:
        # Get affected incomes
        affected_incomes = db.query(PendingIncome).filter(
            PendingIncome.id.in_(request.pending_income_ids),
            PendingIncome.verification_status == 'Pending'
        ).all()
        
        if not affected_incomes:
            return {
                "success": False,
                "message": "No pending incomes found with provided IDs",
                "approved_count": 0
            }
        
        # Update income status to 'Super Admin Verified' (WVV Protocol)
        # Finance will process bank payment and set to 'Completed'
        result = db.execute(
            update(PendingIncome)
            .where(PendingIncome.id.in_(request.pending_income_ids))
            .where(PendingIncome.verification_status == 'Pending')
            .values(
                verification_status='Super Admin Verified',  # WVV: Awaiting Finance payment
                admin_verified_by_id=current_user.id,
                admin_verified_at=datetime.utcnow(),
                super_admin_verified_by_id=current_user.id,
                super_admin_verified_at=datetime.utcnow(),
                notes=f"RVZ Supreme Verification by {current_user.id} - Awaiting Finance payment"
            )
        )
        
        # DC Protocol: Audit logging for skip-level income approvals
        for income in affected_incomes:
            AuditLogger.log_action(
                db=db,
                user=current_user,
                action="SUPREME_APPROVE_INCOME",
                resource_type="INCOME_VERIFICATION",
                resource_id=str(income.id),
                details={
                    "user_id": income.user_id,
                    "old_status": "Pending",
                    "new_status": "Super Admin Verified",
                    "note": f"RVZ Supreme skip-level approval: Income #{income.id} - Awaiting Finance"
                }
            )
        
        db.commit()
        
        rows_updated = result.rowcount
        
        return {
            "success": True,
            "message": f"RVZ Supreme: {rows_updated} income(s) verified → Awaiting Finance payment",
            "approved_count": rows_updated,
            "next_stage": "Finance must process bank payment to complete",
            "skip_level": True,
            "wvv_compliant": True
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to execute auto-workflow: {str(e)}"
        )


@router.post("/withdrawal/supreme-approve")
async def supreme_approve_withdrawal(
    request: SupremeApproveWithdrawalRequest,
    current_user: User = Depends(get_current_admin_user_hybrid),
    db: Session = Depends(get_db)
):
    """
    RVZ Supreme Withdrawal Approval - Skip-Level Workflow (UNIFORM WITH STANDARD FLOW)
    
    This endpoint BYPASSES Admin approval and sets status='Admin Verified' directly.
    Then Finance can send to bank using the standard 'send_to_bank' action.
    
    UNIFORM WORKFLOW:
    Standard: Pending → Admin Verified (by Admin) → Completed (by Finance) → Completed
    RVZ Supreme: Pending → Admin Verified (by RVZ, skip Admin) → Completed (by Finance) → Completed
    
    DC Protocol: Writes to existing withdrawal table (no new tables)
    """
    try:
        # Get affected withdrawals BEFORE update for audit logging
        affected_withdrawals = db.query(WithdrawalRequest).options(
            joinedload(WithdrawalRequest.user)
        ).filter(
            WithdrawalRequest.id.in_(request.withdrawal_ids),
            WithdrawalRequest.status == 'Pending'
        ).all()
        
        staff_id = _resolve_actor_id(current_user)
        
        kyc_not_approved_users = []
        for w in affected_withdrawals:
            if w.user:
                kyc_status = getattr(w.user, 'kyc_status', 'Pending')
                if kyc_status != 'Approved':
                    kyc_not_approved_users.append({
                        "user_id": w.user_id,
                        "user_name": getattr(w.user, 'name', 'Unknown'),
                        "kyc_status": kyc_status
                    })
        
        if kyc_not_approved_users:
            user_list = ", ".join([f"{u['user_id']} ({u['kyc_status']})" for u in kyc_not_approved_users])
            logger.warning(f"[KYC-BYPASS] Staff {staff_id} processing withdrawal for non-KYC users: {user_list}")
        
        # DC Protocol: Update existing withdrawal records (single source of truth)
        result = db.execute(
            update(WithdrawalRequest)
            .where(WithdrawalRequest.id.in_(request.withdrawal_ids))
            .where(WithdrawalRequest.status == 'Pending')  # Only process pending
            .values(
                # Skip-Level: Set status to Admin Verified (uniform with standard flow)
                status='Admin Verified',
                verified_by=current_user.id,
                verified_at=datetime.utcnow(),
                processed_at=datetime.utcnow(),
                notes=f"RVZ Supreme Skip-Level Approval by {current_user.id}"
            )
        )
        
        # DC Protocol: Audit logging for skip-level withdrawal approvals
        for withdrawal in affected_withdrawals:
            AuditLogger.log_action(
                db=db,
                user=current_user,
                action="SUPREME_APPROVE_WITHDRAWAL",
                resource_type="WITHDRAWAL",
                resource_id=str(withdrawal.id),
                details={
                    "user_id": withdrawal.user_id,
                    "old_status": "Pending",
                    "new_status": "Admin Verified",
                    "amount": float(withdrawal.withdrawal_amount),
                    "note": f"RVZ Supreme skip-level approval: Withdrawal #{withdrawal.id} ₹{withdrawal.withdrawal_amount}"
                }
            )
        
        db.commit()
        
        rows_updated = result.rowcount
        
        return {
            "success": True,
            "message": f"RVZ Supreme approved {rows_updated} withdrawal(s) - Ready for Finance bank transfer",
            "approved_count": rows_updated,
            "skip_level": True,
            "workflow": "RVZ → Admin Verified (skipped Admin) → Finance sends to bank"
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to approve withdrawals: {str(e)}"
        )


@router.post("/withdrawal/supreme-transfer")
async def supreme_bank_transfer(
    request: SupremeTransferRequest,
    current_user: User = Depends(get_current_admin_user_hybrid),
    db: Session = Depends(get_db)
):
    """
    RVZ Supreme Bank Transfer - UNIFORM WITH STANDARD FLOW
    
    This endpoint sends withdrawals to bank, EXACTLY like the standard Finance Admin flow.
    Processes 'Admin Verified' → 'Completed' with wallet deduction (DC Protocol Phase 1.7).
    
    UNIFORM WORKFLOW:
    Standard: Admin Verified → Completed (by Finance via send_to_bank action)
    RVZ Supreme: Admin Verified → Completed (by RVZ via this endpoint)
    
    DC Protocol Phase 1.7: Wallet deduction happens when status changes to 'Completed'
    """
    try:
        # Process each withdrawal individually to handle wallet deductions properly
        transferred_count = 0
        total_deducted = Decimal('0')
        errors = []
        
        for withdrawal_id in request.withdrawal_ids:
            try:
                # Step 1: Get withdrawal details and atomically change status
                withdrawal_result = db.execute(
                    text("""
                        UPDATE withdrawal_request
                        SET status = 'Completed',
                            processed_at = NOW(),
                            payment_reference = :ref
                        WHERE id = :req_id
                        AND status = 'Admin Verified'
                        RETURNING user_id, withdrawal_amount, final_payout
                    """),
                    {"req_id": withdrawal_id, "ref": request.utr_number or f"VGK_{int(datetime.utcnow().timestamp())}"}
                ).fetchone()
                
                if not withdrawal_result:
                    errors.append(f"Withdrawal {withdrawal_id} not in Admin Verified status")
                    continue
                
                user_id, amount, final_payout = withdrawal_result
                
                # Step 2: Deduct from withdrawable wallet (DC Protocol Phase 1.7)
                # Use final_payout (net amount after all deductions)
                deduction_result = db.execute(
                    text("""
                        UPDATE "user"
                        SET withdrawable_wallet = COALESCE(withdrawable_wallet, 0) - :amount
                        WHERE id = :user_id
                        AND COALESCE(withdrawable_wallet, 0) >= :amount
                        RETURNING withdrawable_wallet
                    """),
                    {"amount": final_payout, "user_id": user_id}
                ).fetchone()
                
                if not deduction_result:
                    # Insufficient balance - rollback this withdrawal's status
                    db.execute(
                        text("""
                            UPDATE withdrawal_request
                            SET status = 'Admin Verified',
                                processed_at = NULL
                            WHERE id = :req_id
                        """),
                        {"req_id": withdrawal_id}
                    )
                    errors.append(f"Withdrawal {withdrawal_id}: Insufficient wallet balance (need ₹{final_payout:,})")
                    continue
                
                transferred_count += 1
                total_deducted += Decimal(str(final_payout))
                
            except Exception as e:
                errors.append(f"Withdrawal {withdrawal_id}: {str(e)}")
                continue
        
        db.commit()
        
        message = f"RVZ Supreme: {transferred_count} withdrawal(s) sent to bank (₹{int(total_deducted):,} deducted from wallets)"
        if errors:
            message += f" | {len(errors)} failed"
        
        return {
            "success": True,
            "message": message,
            "transferred_count": transferred_count,
            "total_deducted": float(total_deducted),
            "errors": errors if errors else None,
            "skip_level": False,  # Not skip-level, this is standard Finance action
            "workflow": "Admin Verified → Completed (uniform with standard flow)"
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process bank transfers: {str(e)}"
        )


@router.post("/withdrawal/supreme-approve-and-pay")
async def supreme_approve_and_pay(
    request: SupremeTransferRequest,
    current_user: User = Depends(get_current_admin_user_hybrid),
    db: Session = Depends(get_db)
):
    """
    🚀 RVZ SUPREME ONE-CLICK APPROVAL & PAYMENT
    
    This is THE endpoint user requested: ONE button that does EVERYTHING.
    Processes: Pending → Completed (PAID to customer) in SINGLE atomic action.
    
    WORKFLOW COMPARISON:
    Standard: Pending → Admin Verified (Admin) → Super Admin Approves → Completed (Finance)
    RVZ ONE-CLICK: Pending → Completed (RVZ Supreme, bypasses all intermediate steps)
    
    DC Protocol Phase 1.7: Wallet deduction happens when status = 'Completed' (payment made)
    """
    try:
        # Process each withdrawal individually for atomic wallet deduction
        paid_count = 0
        total_paid = Decimal('0')
        errors = []
        successful_payments = []  # Track successful payments for audit logging
        
        for withdrawal_id in request.withdrawal_ids:
            try:
                # BUSINESS RULE: Only process 'Pending' withdrawals (≥ ₹1,000)
                # 'On Hold' withdrawals (< ₹1,000) are skipped
                
                # STEP 1: Atomically change status from Pending → Completed
                withdrawal_result = db.execute(
                    text("""
                        UPDATE withdrawal_request
                        SET status = 'Completed',
                            verified_by = :rvz_id,
                            verified_at = NOW(),
                            processed_by = :rvz_id,
                            processed_at = NOW(),
                            payment_reference = :ref
                        WHERE id = :req_id
                        AND status = 'Pending'
                        AND withdrawal_amount >= 1000
                        RETURNING user_id, withdrawal_amount, final_payout
                    """),
                    {
                        "req_id": withdrawal_id,
                        "rvz_id": current_user.id,
                        "ref": request.utr_number or f"RVZ_SUPREME_{int(datetime.utcnow().timestamp())}"
                    }
                ).fetchone()
                
                if not withdrawal_result:
                    # Check if it's 'On Hold' or just not 'Pending'
                    check_status = db.execute(
                        text("SELECT status, withdrawal_amount FROM withdrawal_request WHERE id = :req_id"),
                        {"req_id": withdrawal_id}
                    ).fetchone()
                    
                    if check_status and check_status[0] == 'On Hold':
                        errors.append(f"Withdrawal {withdrawal_id} is 'On Hold' (₹{check_status[1]:,} < minimum ₹1,000)")
                    else:
                        errors.append(f"Withdrawal {withdrawal_id} not in Pending status or below minimum")
                    continue
                
                user_id, amount, final_payout = withdrawal_result
                
                # STEP 2: Deduct from withdrawable wallet (DC Protocol Phase 1.7)
                # This is the INSTANT WALLET SYNC user requested
                deduction_result = db.execute(
                    text("""
                        UPDATE "user"
                        SET withdrawable_wallet = COALESCE(withdrawable_wallet, 0) - :amount
                        WHERE id = :user_id
                        AND COALESCE(withdrawable_wallet, 0) >= :amount
                        RETURNING withdrawable_wallet
                    """),
                    {"amount": final_payout, "user_id": user_id}
                ).fetchone()
                
                if not deduction_result:
                    # Insufficient balance - rollback this withdrawal
                    db.execute(
                        text("""
                            UPDATE withdrawal_request
                            SET status = 'Pending',
                                verified_by = NULL,
                                verified_at = NULL,
                                processed_by = NULL,
                                processed_at = NULL
                            WHERE id = :req_id
                        """),
                        {"req_id": withdrawal_id}
                    )
                    errors.append(f"Withdrawal {withdrawal_id}: Insufficient wallet balance (need ₹{final_payout:,})")
                    continue
                
                paid_count += 1
                total_paid += Decimal(str(final_payout))
                
                # Track for audit logging
                successful_payments.append({
                    'withdrawal_id': withdrawal_id,
                    'user_id': user_id,
                    'amount': final_payout
                })
                
            except Exception as e:
                errors.append(f"Withdrawal {withdrawal_id}: {str(e)}")
                continue
        
        # DC Protocol: Audit logging for RVZ Supreme one-click payments
        for payment in successful_payments:
            AuditLogger.log_action(
                db=db,
                user=current_user,
                action="SUPREME_ONE_CLICK_PAY",
                resource_type="WITHDRAWAL",
                resource_id=str(payment['withdrawal_id']),
                details={
                    "user_id": payment['user_id'],
                    "old_status": "Pending",
                    "new_status": "Completed",
                    "amount": float(payment['amount']),
                    "note": f"RVZ Supreme ONE-CLICK: Withdrawal #{payment['withdrawal_id']} PAID ₹{payment['amount']:,} (skip-level Pending → Completed)"
                }
            )
        
        db.commit()
        
        message = f"🚀 RVZ ONE-CLICK: {paid_count} withdrawal(s) PAID to customers (₹{int(total_paid):,} sent to bank)"
        if errors:
            message += f" | {len(errors)} failed"
        
        return {
            "success": True,
            "message": message,
            "paid_count": paid_count,
            "total_paid": float(total_paid),
            "errors": errors if errors else None,
            "one_click": True,
            "workflow": "Pending → Completed (ONE-CLICK by RVZ Supreme)"
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process one-click approval & payment: {str(e)}"
        )


# ===== HELPER FUNCTIONS FOR RVZ WITHDRAWAL LISTING =====

def _add_no_cache_headers(response: Response):
    """Add cache-control headers to prevent browser caching of admin data"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


def _validate_and_clamp_pagination(page: int, per_page: int) -> tuple[int, int]:
    """Validate and clamp pagination parameters"""
    page = max(1, page)
    per_page = max(1, min(100, per_page))
    return page, per_page


def _validate_status(status_filter: Optional[str]) -> Optional[str]:
    """Validate status filter against known enum"""
    if not status_filter or status_filter.strip() == '' or status_filter.lower() == 'all':
        return None
    valid_statuses = ['Pending', 'Admin Verified', 'Completed', 'On Hold', 'Rejected']
    if status_filter not in valid_statuses:
        raise ValueError(f"Invalid status. Must be one of: {', '.join(valid_statuses)}")
    return status_filter


def _parse_date(date_str: Optional[str], label: str) -> Optional[date]:
    """Parse and validate date string in YYYY-MM-DD format"""
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        raise ValueError(f"Invalid {label}. Use YYYY-MM-DD format.")


def _enforce_date_window(from_date: Optional[date], to_date: Optional[date], user_id: Optional[str]):
    """Enforce 90-day window unless user_id is provided"""
    if from_date and to_date and not user_id:
        days_diff = (to_date - from_date).days
        if days_diff > 90:
            raise ValueError("Date range cannot exceed 90 days unless user_id is provided")


def _validate_amounts(min_amount: Optional[int], max_amount: Optional[int]) -> tuple[Optional[int], Optional[int]]:
    """Validate and auto-swap amounts if needed"""
    if min_amount is not None and min_amount < 0:
        raise ValueError("min_amount must be positive")
    if max_amount is not None and max_amount < 0:
        raise ValueError("max_amount must be positive")
    
    # Auto-swap if inverted
    if min_amount is not None and max_amount is not None and min_amount > max_amount:
        min_amount, max_amount = max_amount, min_amount
    
    return min_amount, max_amount


def _mask_account_number(account_number: Optional[str]) -> Optional[str]:
    """Mask account number to show only last 4 digits"""
    if not account_number or len(account_number) < 4:
        return account_number
    return "****" + account_number[-4:]


# ===== RVZ SUPREME WITHDRAWAL LISTING ENDPOINT =====

@router.get("/withdrawals")
async def get_rvz_withdrawals(
    response: Response,
    status_filter: Optional[str] = None,
    user_id: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    min_amount: Optional[int] = None,
    max_amount: Optional[int] = None,
    page: int = 1,
    per_page: int = 20,
    current_user: User = Depends(get_current_admin_user_hybrid),
    db: Session = Depends(get_db)
):
    """
    RVZ Supreme Withdrawal Listing - WITH FILTERS & PAGINATION
    
    Filters:
    - status_filter: 'Pending', 'Admin Verified', 'Completed', 'On Hold', 'Rejected' (blank/'All' = show all)
    - user_id: Filter by specific MNR ID
    - from_date / to_date: Date range (YYYY-MM-DD, max 90 days unless user_id provided)
    - min_amount / max_amount: Amount range (positive integers)
    - page / per_page: Pagination (per_page max 100)
    
    Returns paginated withdrawal list with summary statistics and status counts.
    
    MPE Protocol: Input validation, NO CACHE headers, account masking, audit logging
    DC Protocol: Queries withdrawal_request table (single source of truth)
    """
    _add_no_cache_headers(response)
    
    try:
        # STEP 1: VALIDATE ALL INPUTS
        page, per_page = _validate_and_clamp_pagination(page, per_page)
        status_filter = _validate_status(status_filter)
        from_date_obj = _parse_date(from_date, "from_date")
        to_date_obj = _parse_date(to_date, "to_date")
        _enforce_date_window(from_date_obj, to_date_obj, user_id)
        min_amount, max_amount = _validate_amounts(min_amount, max_amount)
        
        # STEP 2: BUILD BASE QUERY WITH EAGER LOADING
        query = db.query(WithdrawalRequest).options(joinedload(WithdrawalRequest.user))
        
        # Apply filters conditionally
        if status_filter:
            query = query.filter(WithdrawalRequest.status == status_filter)
        
        if user_id:
            query = query.filter(WithdrawalRequest.user_id == user_id)
        
        if from_date_obj:
            query = query.filter(WithdrawalRequest.request_date >= from_date_obj)
        
        if to_date_obj:
            query = query.filter(WithdrawalRequest.request_date <= to_date_obj)
        
        if min_amount is not None:
            query = query.filter(WithdrawalRequest.withdrawal_amount >= min_amount)
        
        if max_amount is not None:
            query = query.filter(WithdrawalRequest.withdrawal_amount <= max_amount)
        
        # STEP 3: PAGINATION & COUNTS
        total_records = query.count()
        total_pages = (total_records + per_page - 1) // per_page if total_records > 0 else 1
        
        # Clamp page to valid range
        page = min(page, total_pages)
        
        # Order by request_date DESC, id DESC (deterministic)
        query = query.order_by(WithdrawalRequest.request_date.desc(), WithdrawalRequest.id.desc())
        
        # Fetch current page
        offset = (page - 1) * per_page
        withdrawals = query.limit(per_page).offset(offset).all()
        
        # STEP 4: AGGREGATIONS
        # Status counts (overall, not just current page)
        base_query_for_counts = db.query(WithdrawalRequest)
        if user_id:
            base_query_for_counts = base_query_for_counts.filter(WithdrawalRequest.user_id == user_id)
        if from_date_obj:
            base_query_for_counts = base_query_for_counts.filter(WithdrawalRequest.request_date >= from_date_obj)
        if to_date_obj:
            base_query_for_counts = base_query_for_counts.filter(WithdrawalRequest.request_date <= to_date_obj)
        if min_amount is not None:
            base_query_for_counts = base_query_for_counts.filter(WithdrawalRequest.withdrawal_amount >= min_amount)
        if max_amount is not None:
            base_query_for_counts = base_query_for_counts.filter(WithdrawalRequest.withdrawal_amount <= max_amount)
        
        status_counts_raw = base_query_for_counts.with_entities(
            WithdrawalRequest.status,
            func.count(WithdrawalRequest.id)
        ).group_by(WithdrawalRequest.status).all()
        
        status_counts = {
            "pending": 0,
            "admin_verified": 0,
            "completed": 0,
            "on_hold": 0,
            "rejected": 0
        }
        
        for status, count in status_counts_raw:
            key = status.lower().replace(' ', '_')
            if key in status_counts:
                status_counts[key] = count
        
        # Per-page totals
        total_amount_page = sum(w.withdrawal_amount for w in withdrawals)
        total_payout_page = sum(w.final_payout for w in withdrawals)
        
        # DC Protocol: Fetch income-level gross and deductions for each user
        # Shows ORIGINAL gross from income before 12% deductions were applied
        user_ids = list(set(w.user_id for w in withdrawals))
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
                    'income_gross': float(row.total_gross or 0),
                    'income_gd_deduction': float(row.total_gd or 0),
                    'income_admin_deduction': float(row.total_admin or 0),
                    'income_tds_deduction': float(row.total_tds or 0),
                    'income_net': float(row.total_net or 0)
                }
        
        # STEP 5: RESPONSE ASSEMBLY
        data = []
        for w in withdrawals:
            # Get income data for this user
            income_data = user_income_totals.get(w.user_id, {
                'income_gross': 0, 'income_gd_deduction': 0,
                'income_admin_deduction': 0, 'income_tds_deduction': 0, 'income_net': 0
            })
            
            # Calculate proportional gross/deductions for this withdrawal
            proportion = 1.0
            if income_data['income_net'] > 0:
                proportion = w.withdrawal_amount / income_data['income_net']
            
            # Proportional values based on withdrawal amount vs total income
            proportional_gross = round(income_data['income_gross'] * proportion)
            proportional_gd = round(income_data['income_gd_deduction'] * proportion)
            proportional_admin = round(income_data['income_admin_deduction'] * proportion)
            proportional_tds = round(income_data['income_tds_deduction'] * proportion)
            proportional_deductions = proportional_gd + proportional_admin + proportional_tds
            
            data.append({
                "id": w.id,
                "user_id": w.user_id,
                "user_name": w.user.name if w.user else "Unknown",
                "withdrawal_amount": w.withdrawal_amount,
                "income_gross": proportional_gross,
                "income_gd_deduction": proportional_gd,
                "income_admin_deduction": proportional_admin,
                "income_tds_deduction": proportional_tds,
                "income_total_deductions": proportional_deductions,
                "admin_charges": w.admin_charges,
                "tds_amount": w.tds_amount,
                "final_payout": w.final_payout,
                "request_date": w.request_date.isoformat() if w.request_date else None,
                "status": w.status,
                "created_at": w.created_at.isoformat() if w.created_at else None,
                "processed_at": w.processed_at.isoformat() if w.processed_at else None,
                "bank_name": w.bank_name,
                "account_number": _mask_account_number(w.account_number),
                "ifsc_code": w.ifsc_code,
                "account_holder_name": w.account_holder_name,
                "payment_reference": w.payment_reference,
                "paid_date": w.paid_date.isoformat() if w.paid_date else None,
                "is_auto_generated": w.is_auto_generated,
                "kyc_status": w.user.kyc_status if w.user else "Unknown"
            })
        
        # AUDIT LOGGING
        AuditLogger.log_action(
            db=db,
            user=current_user,
            action="RVZ_SUPREME_WITHDRAWAL_LIST",
            resource_type="WithdrawalRequest",
            details={
                "filters": {
                    "status": status_filter,
                    "user_id": user_id,
                    "from_date": from_date,
                    "to_date": to_date,
                    "min_amount": min_amount,
                    "max_amount": max_amount
                },
                "page": page,
                "records_returned": len(withdrawals)
            }
        )
        
        return {
            "success": True,
            "count": len(withdrawals),
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total_pages": total_pages,
                "total_records": total_records
            },
            "summary": {
                "total_amount": total_amount_page,
                "total_payout": total_payout_page,
                "status_counts": status_counts
            },
            "data": data
        }
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Server error: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch withdrawals: {str(e)}"
        )


@router.get("/income/history")
async def get_income_history(
    user_id: str = None,
    status_filter: str = 'Completed',
    start_date: str = None,
    end_date: str = None,
    page: int = 1,
    per_page: int = 20,
    current_user: User = Depends(get_current_admin_user_hybrid),
    db: Session = Depends(get_db)
):
    """
    RVZ Supreme Income History - Show approved incomes with date range filtering
    
    This shows incomes that were approved via RVZ Supreme workflow.
    Separate from withdrawal history (those are different processes).
    
    DC Protocol: Reads from pending_income table (single source of truth)
    
    Date filtering uses business_date (the date income was earned)
    """
    try:
        # Join with User table to get user_name
        query = db.query(PendingIncome, User.name).outerjoin(
            User, PendingIncome.user_id == User.id
        )
        
        # Filter by status (default: Completed = fully approved)
        if status_filter:
            query = query.filter(PendingIncome.verification_status == status_filter)
        
        # Filter by user if provided
        if user_id:
            query = query.filter(PendingIncome.user_id == user_id)
        
        # Filter by date range if provided
        if start_date:
            try:
                from datetime import date
                start_dt = date.fromisoformat(start_date)
                query = query.filter(PendingIncome.business_date >= start_dt)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Invalid start_date format. Expected YYYY-MM-DD, got: {start_date}"
                )
        
        if end_date:
            try:
                from datetime import date
                end_dt = date.fromisoformat(end_date)
                # Use <= to include the full end_date
                query = query.filter(PendingIncome.business_date <= end_dt)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Invalid end_date format. Expected YYYY-MM-DD, got: {end_date}"
                )
        
        # Order by most recent first
        query = query.order_by(PendingIncome.accounts_paid_at.desc())
        
        # Get all results (returns tuples of (PendingIncome, user_name))
        results = query.all()
        
        return {
            "success": True,
            "count": len(results),
            "data": [
                {
                    "id": pi.id,
                    "user_id": pi.user_id,
                    "user_name": user_name or "Unknown",
                    "income_type": pi.income_type,
                    "gross_amount": float(pi.gross_amount),
                    "net_amount": float(pi.net_amount),
                    "business_date": pi.business_date.isoformat() if pi.business_date else None,
                    "verification_status": pi.verification_status,
                    "admin_verified_at": pi.admin_verified_at.isoformat() if pi.admin_verified_at else None,
                    "super_admin_verified_at": pi.super_admin_verified_at.isoformat() if pi.super_admin_verified_at else None,
                    "accounts_paid_at": pi.accounts_paid_at.isoformat() if pi.accounts_paid_at else None,
                    "accounts_paid_by_id": pi.accounts_paid_by_id,
                    "notes": pi.notes
                }
                for pi, user_name in results
            ]
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch income history: {str(e)}"
        )


@router.get("/income/user-wise")
async def get_income_user_wise(
    start_date: str = None,
    end_date: str = None,
    user_id: str = None,
    status_filter: str = 'Completed',
    income_type: str = None,
    package_filter: str = None,
    page: int = 1,
    per_page: int = 20,
    current_user: User = Depends(get_current_admin_user_hybrid),
    db: Session = Depends(get_db)
):
    """
    RVZ Income Records - User-Wise View
    
    Groups income records by user with gross/net breakups
    DC Protocol: Single source from pending_income table
    """
    try:
        # Build base query with JOIN to User table
        query = db.query(
            PendingIncome.user_id,
            User.name.label('user_name'),
            func.count(PendingIncome.id).label('total_transactions'),
            func.sum(
                case(
                    (PendingIncome.income_type == 'Direct Referral', PendingIncome.gross_amount),
                    else_=0
                )
            ).label('direct_referral'),
            func.sum(
                case(
                    (PendingIncome.income_type == 'Matching Referral', PendingIncome.gross_amount),
                    else_=0
                )
            ).label('matching_referral'),
            func.sum(
                case(
                    (PendingIncome.income_type == 'Ved Income', PendingIncome.gross_amount),
                    else_=0
                )
            ).label('ved_income'),
            func.sum(
                case(
                    (PendingIncome.income_type == 'Guru Dakshina', PendingIncome.gross_amount),
                    else_=0
                )
            ).label('guru_dakshina'),
            func.sum(PendingIncome.gross_amount).label('total_gross'),
            func.sum(PendingIncome.net_amount).label('total_net'),
            func.sum(PendingIncome.gross_amount - PendingIncome.net_amount).label('total_deductions')
        ).outerjoin(User, PendingIncome.user_id == User.id)
        
        # Apply filters
        if status_filter:
            query = query.filter(PendingIncome.verification_status == status_filter)
        
        if user_id:
            query = query.filter(PendingIncome.user_id == user_id)
        
        if income_type:
            query = query.filter(PendingIncome.income_type == income_type)
        
        # Package filter removed: User.package_name column doesn't exist (DC Protocol fix)
        
        if start_date:
            try:
                start_dt = date.fromisoformat(start_date)
                query = query.filter(PendingIncome.business_date >= start_dt)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Invalid start_date format: {start_date}"
                )
        
        if end_date:
            try:
                end_dt = date.fromisoformat(end_date)
                query = query.filter(PendingIncome.business_date <= end_dt)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Invalid end_date format: {end_date}"
                )
        
        # Group by user
        query = query.group_by(
            PendingIncome.user_id,
            User.name
        )
        
        # Get total count for pagination
        total_count = query.count()
        
        # Apply pagination and ordering
        query = query.order_by(func.sum(PendingIncome.net_amount).desc())
        query = query.offset((page - 1) * per_page).limit(per_page)
        
        results = query.all()
        
        # Calculate statistics
        stats_query = db.query(
            func.count(func.distinct(PendingIncome.user_id)).label('total_users'),
            func.sum(PendingIncome.gross_amount).label('total_gross'),
            func.sum(PendingIncome.net_amount).label('total_net'),
            func.count(PendingIncome.id).label('total_transactions')
        ).outerjoin(User, PendingIncome.user_id == User.id)
        
        # Apply same filters to statistics
        if status_filter:
            stats_query = stats_query.filter(PendingIncome.verification_status == status_filter)
        if user_id:
            stats_query = stats_query.filter(PendingIncome.user_id == user_id)
        if income_type:
            stats_query = stats_query.filter(PendingIncome.income_type == income_type)
        if package_filter:
            stats_query = stats_query.filter(User.package_name == package_filter)
        if start_date:
            stats_query = stats_query.filter(PendingIncome.business_date >= date.fromisoformat(start_date))
        if end_date:
            stats_query = stats_query.filter(PendingIncome.business_date <= date.fromisoformat(end_date))
        
        stats = stats_query.first()
        
        # Get date-wise transactions for each user
        data = []
        for row in results:
            # Get transactions for this user
            transactions_query = db.query(PendingIncome).filter(
                PendingIncome.user_id == row.user_id
            )
            
            # Apply same filters
            if status_filter:
                transactions_query = transactions_query.filter(PendingIncome.verification_status == status_filter)
            if income_type:
                transactions_query = transactions_query.filter(PendingIncome.income_type == income_type)
            if start_date:
                transactions_query = transactions_query.filter(PendingIncome.business_date >= date.fromisoformat(start_date))
            if end_date:
                transactions_query = transactions_query.filter(PendingIncome.business_date <= date.fromisoformat(end_date))
            
            transactions = transactions_query.order_by(PendingIncome.business_date.desc()).all()
            
            user_data = {
                "user_id": row.user_id,
                "user_name": row.user_name or "Unknown",
                "total_transactions": row.total_transactions,
                "gross_breakup": {
                    "direct_referral": float(row.direct_referral or 0),
                    "matching_referral": float(row.matching_referral or 0),
                    "ved_income": float(row.ved_income or 0),
                    "guru_dakshina": float(row.guru_dakshina or 0),
                    "total_gross": float(row.total_gross or 0)
                },
                "deduction_breakup": {
                    "total_deductions": float(row.total_deductions or Decimal('0')),
                    "admin_deduction": float((row.total_gross or Decimal('0')) * Decimal('0.08')),
                    "tds_deduction": float((row.total_gross or Decimal('0')) * Decimal('0.02')),
                    "guru_dakshina_deduction": float((row.total_gross or Decimal('0')) * Decimal('0.02'))
                },
                "total_net": float(row.total_net or 0),
                "date_wise_transactions": [
                    {
                        "business_date": t.business_date.isoformat() if t.business_date else None,
                        "income_type": t.income_type,
                        "gross_amount": float(t.gross_amount),
                        "net_amount": float(t.net_amount),
                        "deductions": float(t.gross_amount - t.net_amount),
                        "verification_status": t.verification_status
                    }
                    for t in transactions
                ]
            }
            data.append(user_data)
        
        return {
            "success": True,
            "count": total_count,
            "total_pages": (total_count + per_page - 1) // per_page,
            "current_page": page,
            "statistics": {
                "total_users": stats.total_users or 0,
                "total_gross_amount": float(stats.total_gross or 0),
                "total_net_amount": float(stats.total_net or 0),
                "total_transactions": stats.total_transactions or 0,
                "avg_per_user": float(stats.total_net / stats.total_users) if stats.total_users else 0
            },
            "data": data
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch user-wise income records: {str(e)}"
        )


@router.get("/income/date-wise")
async def get_income_date_wise(
    start_date: str = None,
    end_date: str = None,
    user_id: str = None,
    status_filter: str = 'Completed',
    income_type: str = None,
    package_filter: str = None,
    page: int = 1,
    per_page: int = 20,
    current_user: User = Depends(get_current_admin_user_hybrid),
    db: Session = Depends(get_db)
):
    """
    RVZ Income Records - Date-Wise View
    
    Groups income records by business date with user breakdowns
    DC Protocol: Single source from pending_income table
    """
    try:
        # Build base query
        query = db.query(
            PendingIncome.business_date,
            func.count(func.distinct(PendingIncome.user_id)).label('total_users'),
            func.count(PendingIncome.id).label('total_transactions'),
            func.sum(PendingIncome.gross_amount).label('total_gross'),
            func.sum(PendingIncome.gross_amount - PendingIncome.net_amount).label('total_deductions'),
            func.sum(PendingIncome.net_amount).label('total_net')
        ).outerjoin(User, PendingIncome.user_id == User.id)
        
        # Apply filters
        if status_filter:
            query = query.filter(PendingIncome.verification_status == status_filter)
        
        if user_id:
            query = query.filter(PendingIncome.user_id == user_id)
        
        if income_type:
            query = query.filter(PendingIncome.income_type == income_type)
        
        # Package filter removed: User.package_name column doesn't exist (DC Protocol fix)
        
        if start_date:
            try:
                start_dt = date.fromisoformat(start_date)
                query = query.filter(PendingIncome.business_date >= start_dt)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Invalid start_date format: {start_date}"
                )
        
        if end_date:
            try:
                end_dt = date.fromisoformat(end_date)
                query = query.filter(PendingIncome.business_date <= end_dt)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Invalid end_date format: {end_date}"
                )
        
        # Group by date
        query = query.group_by(PendingIncome.business_date)
        
        # Get total count for pagination
        total_count = query.count()
        
        # Apply pagination and ordering
        query = query.order_by(PendingIncome.business_date.desc())
        query = query.offset((page - 1) * per_page).limit(per_page)
        
        results = query.all()
        
        # Calculate statistics (same as user-wise)
        stats_query = db.query(
            func.count(func.distinct(PendingIncome.business_date)).label('total_dates'),
            func.sum(PendingIncome.gross_amount).label('total_gross'),
            func.sum(PendingIncome.net_amount).label('total_net'),
            func.count(PendingIncome.id).label('total_transactions')
        ).outerjoin(User, PendingIncome.user_id == User.id)
        
        # Apply same filters
        if status_filter:
            stats_query = stats_query.filter(PendingIncome.verification_status == status_filter)
        if user_id:
            stats_query = stats_query.filter(PendingIncome.user_id == user_id)
        if income_type:
            stats_query = stats_query.filter(PendingIncome.income_type == income_type)
        if package_filter:
            stats_query = stats_query.filter(User.package_name == package_filter)
        if start_date:
            stats_query = stats_query.filter(PendingIncome.business_date >= date.fromisoformat(start_date))
        if end_date:
            stats_query = stats_query.filter(PendingIncome.business_date <= date.fromisoformat(end_date))
        
        stats = stats_query.first()
        
        # Get user transactions for each date
        data = []
        for row in results:
            # Get users for this date
            users_query = db.query(
                PendingIncome,
                User.name.label('user_name')
            ).outerjoin(User, PendingIncome.user_id == User.id).filter(
                PendingIncome.business_date == row.business_date
            )
            
            # Apply same filters
            if status_filter:
                users_query = users_query.filter(PendingIncome.verification_status == status_filter)
            if user_id:
                users_query = users_query.filter(PendingIncome.user_id == user_id)
            if income_type:
                users_query = users_query.filter(PendingIncome.income_type == income_type)
            # Package filter removed: User.package_name column doesn't exist (DC Protocol fix)
            
            users = users_query.all()
            
            date_data = {
                "business_date": row.business_date.isoformat() if row.business_date else None,
                "total_users": row.total_users,
                "total_transactions": row.total_transactions,
                "total_gross": float(row.total_gross or 0),
                "total_deductions": float(row.total_deductions or 0),
                "total_net": float(row.total_net or 0),
                "user_transactions": [
                    {
                        "user_id": pi.user_id,
                        "user_name": user_name or "Unknown",
                        "income_type": pi.income_type,
                        "gross_amount": float(pi.gross_amount),
                        "net_amount": float(pi.net_amount),
                        "deductions": float(pi.gross_amount - pi.net_amount),
                        "verification_status": pi.verification_status
                    }
                    for pi, user_name in users
                ]
            }
            data.append(date_data)
        
        return {
            "success": True,
            "count": total_count,
            "total_pages": (total_count + per_page - 1) // per_page,
            "current_page": page,
            "statistics": {
                "total_dates": stats.total_dates or 0,
                "total_gross_amount": float(stats.total_gross or 0),
                "total_net_amount": float(stats.total_net or 0),
                "total_transactions": stats.total_transactions or 0
            },
            "data": data
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch date-wise income records: {str(e)}"
        )


@router.get("/payment-settings")
async def get_payment_settings(
    current_user: User = Depends(get_current_admin_user_hybrid),
    db: Session = Depends(get_db)
):
    """
    RVZ Payment & Financial Settings - DC Protocol Compliant
    
    Single source of truth from app_settings table
    Returns all financial rates, deductions, withdrawal settings
    """
    try:
        # DC Protocol: Single source from app_settings table
        settings = AppSettings.get_all_settings(db)
        
        if not settings:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Payment settings not found. Please initialize system settings."
            )
        
        return {
            "success": True,
            "data": {
                "financial_deductions": {
                    "admin_deduction_rate": float(settings.admin_deduction_rate),
                    "tds_deduction_rate": float(settings.tds_deduction_rate),
                    "guru_dakshina_rate": float(settings.guru_dakshina_rate)
                },
                "income_limits": {
                    "daily_income_ceiling": float(settings.daily_income_ceiling),
                    "minimum_withdrawal_amount": float(settings.minimum_withdrawal_amount)
                },
                "package_points": {
                    "platinum": float(settings.package_points_platinum),
                    "diamond": float(settings.package_points_diamond),
                    "blue": float(settings.package_points_blue),
                    "loyal": float(settings.package_points_loyal)
                },
                "direct_referral_bonuses": {
                    "platinum": float(settings.direct_referral_platinum),
                    "diamond": float(settings.direct_referral_diamond),
                    "blue": float(settings.direct_referral_blue),
                    "loyal": float(settings.direct_referral_loyal)
                },
                "matching_income": {
                    "per_point_rate": float(settings.matching_income_per_point)
                },
                "ved_income_rates": {
                    "platinum": float(settings.ved_income_platinum),
                    "diamond": float(settings.ved_income_diamond),
                    "blue": float(settings.ved_income_blue),
                    "loyal": float(settings.ved_income_loyal)
                },
                "wallet_split_ratios": {
                    "platinum": {
                        "withdrawable": float(settings.wallet_split_platinum_withdrawable),
                        "earning": float(settings.wallet_split_platinum_earning)
                    },
                    "default_packages": {
                        "withdrawable": float(settings.wallet_split_default_withdrawable),
                        "earning": float(settings.wallet_split_default_earning)
                    }
                },
                "withdrawal_settings": {
                    "auto_withdrawal_enabled": settings.auto_withdrawal_enabled if hasattr(settings, 'auto_withdrawal_enabled') else False,
                    "max_withdrawal_limit": float(settings.max_withdrawal_limit) if hasattr(settings, 'max_withdrawal_limit') else 50000.0,
                    "withdrawal_buffer_amount": float(settings.withdrawal_buffer_amount) if hasattr(settings, 'withdrawal_buffer_amount') else 1000.0
                }
            },
            "dc_protocol": "Payment settings from single source (app_settings table)"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load payment settings: {str(e)}\n{traceback.format_exc()}"
        )


@router.get("/users")
async def get_rvz_users(
    page: int = 1,
    per_page: int = 50,
    status_filter: str = None,
    user_type: str = None,
    search: str = None,
    current_user: User = Depends(get_current_admin_user_hybrid),
    db: Session = Depends(get_db)
):
    """
    RVZ User Management - List all users with filtering
    
    DC Protocol: Single source of truth from user table
    Supports pagination, filtering by status/type, and search
    """
    try:
        from sqlalchemy import and_, or_, func
        
        # DC Protocol: Query from user table only (single source of truth)
        query = db.query(User)
        
        # Apply filters
        if status_filter:
            if status_filter.lower() == 'active':
                query = query.filter(User.account_status == 'Active')
            elif status_filter.lower() == 'inactive':
                query = query.filter(User.account_status == 'Inactive')
        
        if user_type:
            query = query.filter(User.user_type == user_type)
        
        if search:
            query = query.filter(
                or_(
                    User.id.ilike(f'%{search}%'),
                    User.name.ilike(f'%{search}%'),
                    User.email.ilike(f'%{search}%'),
                    User.phone_number.ilike(f'%{search}%')
                )
            )
        
        # Get total count before pagination
        total_users = query.count()
        
        # Apply pagination
        offset = (page - 1) * per_page
        users = query.order_by(User.registration_date.desc()).offset(offset).limit(per_page).all()
        
        # Format user data
        user_list = []
        for user in users:
            user_list.append({
                "id": user.id,
                "name": user.name,
                "email": user.email,
                "phone_number": user.phone_number,
                "user_type": user.user_type,
                "account_status": user.account_status,
                "registration_date": user.registration_date.isoformat() if user.registration_date else None,
                "activation_date": user.activation_date.isoformat() if user.activation_date else None,
                "referrer_id": user.referrer_id,
                "ved_owner_id": user.ved_owner_id,
                "package_type": user.get_package_type() if hasattr(user, 'get_package_type') else 'Unknown',
                "kyc_verified": user.kyc_verified if hasattr(user, 'kyc_verified') else False,
                "bank_verified": user.bank_verified if hasattr(user, 'bank_verified') else False
            })
        
        # Calculate pagination info
        total_pages = (total_users + per_page - 1) // per_page
        
        return {
            "success": True,
            "data": {
                "users": user_list,
                "pagination": {
                    "current_page": page,
                    "per_page": per_page,
                    "total_users": total_users,
                    "total_pages": total_pages,
                    "has_next": page < total_pages,
                    "has_prev": page > 1
                },
                "filters": {
                    "status": status_filter,
                    "user_type": user_type,
                    "search": search
                }
            },
            "dc_protocol": "User list from single source (user table)"
        }
        
    except Exception as e:
        import traceback
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load user list: {str(e)}\n{traceback.format_exc()}"
        )


@router.get("/dashboard-stats")
async def get_rvz_dashboard_stats(
    current_user: User = Depends(get_current_admin_user_hybrid),
    db: Session = Depends(get_db)
):
    """
    RVZ Dashboard Statistics - DC Protocol Compliant
    
    Single source of truth from:
    - user table (user counts)
    - pending_income table (income stats)
    - withdrawal_request table (withdrawal stats)
    - bonanza/awards tables (pending approvals)
    
    DC Protocol: All stats calculated from source tables, no duplication
    """
    try:
        from sqlalchemy import func, and_
        from app.models.awards import UserAwardProgress
        from app.models.bonanza import DynamicBonanzaHistory, Bonanza  # DC Protocol: BonanzaProgress deprecated
        from app.models.base import get_indian_time
        
        today = get_indian_time().date()
        today_start = datetime.combine(today, datetime.min.time())
        today_end = datetime.combine(today, datetime.max.time())
        month_start = today.replace(day=1)
        
        # USER STATISTICS - DC Protocol: Single source = user table
        total_users = db.query(func.count(User.id)).scalar() or 0
        active_users = db.query(func.count(User.id)).filter(User.activation_date.isnot(None)).scalar() or 0
        inactive_users = db.query(func.count(User.id)).filter(User.account_status == 'Inactive').scalar() or 0
        users_today = db.query(func.count(User.id)).filter(
            and_(User.registration_date >= today_start, User.registration_date <= today_end)
        ).scalar() or 0
        users_this_month = db.query(func.count(User.id)).filter(
            User.registration_date >= month_start
        ).scalar() or 0
        
        # INCOME STATISTICS - DC Protocol: Single source = pending_income table
        pending_income_count = db.query(func.count(PendingIncome.id)).filter(
            PendingIncome.verification_status == 'Pending'
        ).scalar() or 0
        pending_income_amount = db.query(func.sum(PendingIncome.net_amount)).filter(
            PendingIncome.verification_status == 'Pending'
        ).scalar() or 0
        
        # WITHDRAWAL STATISTICS - DC Protocol: Single source = withdrawal_request table
        pending_withdrawals = db.query(func.count(WithdrawalRequest.id)).filter(
            WithdrawalRequest.status == 'Pending'
        ).scalar() or 0
        pending_withdrawal_amount = db.query(func.sum(WithdrawalRequest.final_payout)).filter(
            WithdrawalRequest.status == 'Pending'
        ).scalar() or 0
        
        # AWARDS & BONANZA PENDING APPROVALS - DC Protocol
        awards_pending = db.query(func.count(UserAwardProgress.id)).filter(
            and_(
                UserAwardProgress.admin_approved_by.isnot(None),
                UserAwardProgress.super_admin_decision.is_(None)
            )
        ).scalar() or 0
        
        # DC Protocol: Query bonanza claims from DynamicBonanzaHistory
        bonanza_pending = db.query(func.count(DynamicBonanzaHistory.id)).filter(
            and_(
                DynamicBonanzaHistory.admin_approved_by.isnot(None),
                DynamicBonanzaHistory.super_admin_decision.is_(None)
            )
        ).scalar() or 0
        
        bonanza_campaigns_pending = db.query(func.count(Bonanza.id)).filter(
            Bonanza.status == 'Pending'
        ).scalar() or 0
        
        return {
            "success": True,
            "debug_backend_timestamp": "1762917227",
            "data": {
                "user_stats": {
                    "all_time": {
                        "total_users": total_users,
                        "active_users": active_users,
                        "inactive_users": inactive_users
                    },
                    "today": {
                        "total_users": users_today
                    },
                    "this_month": {
                        "total_users": users_this_month
                    }
                },
                "income_stats": {
                    "pending_count": pending_income_count,
                    "pending_amount": float(pending_income_amount) if pending_income_amount else 0.0
                },
                "withdrawal_stats": {
                    "pending_count": pending_withdrawals,
                    "pending_amount": float(pending_withdrawal_amount) if pending_withdrawal_amount else 0.0
                },
                "approval_queue": {
                    "awards_pending_super_admin": awards_pending,
                    "bonanza_pending_super_admin": bonanza_pending,
                    "bonanza_campaigns_pending": bonanza_campaigns_pending
                }
            },
            "dc_protocol": "Stats calculated from single source of truth (user, pending_income, withdrawal_request, awards, bonanza)"
        }
        
    except Exception as e:
        import traceback
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load RVZ dashboard statistics: {str(e)}\n{traceback.format_exc()}"
        )


@router.get("/brands")
async def get_brands(
    current_user: User = Depends(get_current_admin_user_hybrid),
    db: Session = Depends(get_db)
):
    """RVZ Brands (EV Models) - DC Protocol Compliant"""
    try:
        brands = db.query(EVModel).filter(EVModel.is_active == True).order_by(EVModel.display_order).all()
        return {
            "success": True,
            "data": [{"id": b.id, "model_name": b.model_name, "manufacturer": b.manufacturer, "base_price": float(b.base_price)} for b in brands],
            "dc_protocol": "Brands from ev_model table"
        }
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/levels")
async def get_levels(
    current_user: User = Depends(get_current_admin_user_hybrid),
    db: Session = Depends(get_db)
):
    """RVZ Levels (Allowance Tiers) - DC Protocol Compliant"""
    try:
        levels = db.query(AllowanceTierDefinition).filter(AllowanceTierDefinition.is_active == True).order_by(AllowanceTierDefinition.tier_level).all()
        return {
            "success": True,
            "data": [{"id": l.id, "tier_name": l.tier_name, "tier_level": l.tier_level, "monthly_allowance": float(l.monthly_allowance)} for l in levels],
            "dc_protocol": "Levels from allowance_tier_definition table"
        }
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/awards")
async def get_awards(
    current_user: User = Depends(get_current_admin_user_hybrid),
    db: Session = Depends(get_db)
):
    """RVZ Awards (Direct & Matching Tiers) - DC Protocol Compliant"""
    try:
        direct_awards = db.query(DirectAwardTier).order_by(DirectAwardTier.cumulative_required).all()
        matching_awards = db.query(MatchingAwardTier).order_by(MatchingAwardTier.cumulative_required).all()
        return {
            "success": True,
            "data": {
                "direct_awards": [{"id": a.id, "award_name": a.award_name, "referral_count": a.referral_count, "actual_price": float(a.actual_price) if a.actual_price else 0} for a in direct_awards],
                "matching_awards": [{"id": a.id, "award_name": a.award_name, "points_target": a.match_count, "actual_price": float(a.actual_price) if a.actual_price else 0} for a in matching_awards]
            },
            "dc_protocol": "Awards from direct_award_tier and matching_award_tier tables"
        }
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/packages")
async def get_packages(
    current_user: User = Depends(get_current_admin_user_hybrid),
    db: Session = Depends(get_db)
):
    """RVZ Packages (Package Points Config) - DC Protocol Compliant"""
    try:
        settings = AppSettings.get_all_settings(db)
        return {
            "success": True,
            "data": {
                "packages": [
                    {"name": "Platinum", "points": float(settings.package_points_platinum), "direct_referral": float(settings.direct_referral_platinum)},
                    {"name": "Diamond", "points": float(settings.package_points_diamond), "direct_referral": float(settings.direct_referral_diamond)},
                    {"name": "Blue", "points": float(settings.package_points_blue), "direct_referral": float(settings.direct_referral_blue)},
                    {"name": "Loyal", "points": float(settings.package_points_loyal), "direct_referral": float(settings.direct_referral_loyal)}
                ]
            },
            "dc_protocol": "Packages from app_settings table"
        }
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/bonanza/rvz/all")
async def get_all_bonanzas(
    current_user: User = Depends(get_current_admin_user_hybrid),
    db: Session = Depends(get_db)
):
    """RVZ All Bonanzas - DC Protocol Compliant"""
    try:
        bonanzas = db.query(Bonanza).filter(Bonanza.is_deleted == False).order_by(Bonanza.created_at.desc()).all()
        return {
            "success": True,
            "data": [{"id": b.id, "name": b.name, "status": b.status, "start_date": b.start_date.isoformat(), "end_date": b.end_date.isoformat()} for b in bonanzas],
            "dc_protocol": "Bonanzas from bonanza table"
        }
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/admins")
async def get_admins(
    current_user: User = Depends(get_current_admin_user_hybrid),
    db: Session = Depends(get_db)
):
    """RVZ Admin Users List - DC Protocol Compliant"""
    try:
        admins = db.query(User).filter(User.user_type.in_(['Admin', 'Super Admin', 'Finance Admin', 'RVZ ID'])).order_by(User.name).all()
        return {
            "success": True,
            "data": [{"id": a.id, "name": a.name, "user_type": a.user_type, "email": a.email} for a in admins],
            "dc_protocol": "Admins from user table"
        }
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/app-settings")
async def get_app_settings(
    current_user: User = Depends(get_current_admin_user_hybrid),
    db: Session = Depends(get_db)
):
    """RVZ App Settings (Complete System Config) - DC Protocol Compliant"""
    try:
        settings = AppSettings.get_all_settings(db)
        if not settings:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="App settings not found")
        
        return {
            "success": True,
            "data": {
                "id": settings.id,
                "financial_deductions": {"admin": float(settings.admin_deduction_rate), "tds": float(settings.tds_deduction_rate), "guru_dakshina": float(settings.guru_dakshina_rate)},
                "income_limits": {"daily_ceiling": float(settings.daily_income_ceiling), "min_withdrawal": float(settings.minimum_withdrawal_amount)},
                "package_points": {"platinum": float(settings.package_points_platinum), "diamond": float(settings.package_points_diamond), "blue": float(settings.package_points_blue), "loyal": float(settings.package_points_loyal)},
                "direct_referral": {"platinum": float(settings.direct_referral_platinum), "diamond": float(settings.direct_referral_diamond), "blue": float(settings.direct_referral_blue), "loyal": float(settings.direct_referral_loyal)},
                "matching_income_per_point": float(settings.matching_income_per_point),
                "ved_income": {"platinum": float(settings.ved_income_platinum), "diamond": float(settings.ved_income_diamond), "blue": float(settings.ved_income_blue), "loyal": float(settings.ved_income_loyal)}
            },
            "dc_protocol": "App settings from app_settings table"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# ===== RVZ SUPREME AWARDS APPROVAL =====

class SupremeApproveAwardsRequest(BaseModel):
    award_ids: List[int]
    award_type: str  # 'direct' or 'matching'


class SupremeRejectAwardsRequest(BaseModel):
    award_ids: List[int]
    award_type: str  # 'direct' or 'matching'
    rejection_reason: str


@router.get("/awards/pending-approval")
async def get_pending_awards_for_approval(
    award_type: str = 'all',  # 'all', 'direct', 'matching'
    current_user: User = Depends(get_current_admin_user_hybrid),
    db: Session = Depends(get_db)
):
    """
    RVZ Supreme: Get all awards pending approval
    
    Shows awards in ANY status that needs approval:
    - Pending (not yet admin approved)
    - Admin Approved (waiting for super admin)
    
    DC Protocol: Reads from user_award_progress and user_matching_award_progress tables
    """
    try:
        pending_awards = []
        
        # DC PROTOCOL: Production start date for eligibility
        PRODUCTION_START_DATE = date(2025, 10, 21)
        
        # Get Direct Awards pending approval
        if award_type in ['all', 'direct']:
            # DC PROTOCOL: Only show awards for users with eligible referrals (activated on/after Oct 21, 2025)
            # Use aliased User to avoid correlation issues
            ReferralUser = aliased(User)
            eligible_referral_subquery = exists(
                select(ReferralUser.id).where(
                    and_(
                        ReferralUser.referrer_id == UserAwardProgress.user_id,
                        ReferralUser.activation_date >= PRODUCTION_START_DATE
                    )
                )
            )
            
            # DC PROTOCOL: Exclude users who have claimed bonanza
            bonanza_exclusion = ~exists(
                select(DynamicBonanzaHistory.id).where(
                    DynamicBonanzaHistory.user_id == UserAwardProgress.user_id
                )
            )
            
            direct_awards = db.query(
                UserAwardProgress,
                DirectAwardTier,
                User
            ).join(
                DirectAwardTier, UserAwardProgress.award_tier_id == DirectAwardTier.id
            ).join(
                User, UserAwardProgress.user_id == User.id
            ).filter(
                UserAwardProgress.processed_status.in_(['Pending Approval', 'Admin Approved']),
                eligible_referral_subquery,
                bonanza_exclusion
            ).all()
            
            for progress, tier, user in direct_awards:
                pending_awards.append({
                    'id': progress.id,
                    'type': 'direct',
                    'user_id': user.id,
                    'user_name': user.name,
                    'award_name': tier.award_name,
                    'award_description': tier.award_description,
                    'referral_count': progress.current_referrals,
                    'required_count': progress.required_referrals,
                    'budgeted_amount': float(progress.budgeted_amount) if progress.budgeted_amount else 0,
                    'achieved_at': progress.achieved_at.isoformat() if progress.achieved_at else None,
                    'current_status': progress.processed_status,
                    'admin_approved_by': progress.admin_approved_by,
                    'admin_approved_at': progress.admin_approved_at.isoformat() if progress.admin_approved_at else None,
                    # DC Protocol: Include procurement tracking fields from single source of truth
                    'dispatch_date': progress.dispatch_date.isoformat() if progress.dispatch_date else None,
                    'received_date': progress.received_date.isoformat() if progress.received_date else None,
                    'delivery_notes': progress.delivery_notes
                })
        
        # Get Matching Awards pending approval
        if award_type in ['all', 'matching']:
            # DC PROTOCOL: Only show awards for users with eligible referrals (activated on/after Oct 21, 2025)
            # Use aliased User to avoid correlation issues
            ReferralUser = aliased(User)
            eligible_referral_subquery = exists(
                select(ReferralUser.id).where(
                    and_(
                        ReferralUser.referrer_id == UserMatchingAwardProgress.user_id,
                        ReferralUser.activation_date >= PRODUCTION_START_DATE
                    )
                )
            )
            
            # NOTE: NO bonanza exclusion for matching awards
            # Bonanza only consumes DIRECT points (deduction_applied_to_direct_awards = True)
            # Bonanza does NOT consume MATCHING points (deduction_applied_to_matching_awards = False)
            # Therefore, bonanza claimants can still receive matching awards
            
            matching_awards = db.query(
                UserMatchingAwardProgress,
                MatchingAwardTier,
                User
            ).join(
                MatchingAwardTier, UserMatchingAwardProgress.matching_award_tier_id == MatchingAwardTier.id
            ).join(
                User, UserMatchingAwardProgress.user_id == User.id
            ).filter(
                UserMatchingAwardProgress.processed_status.in_(['Pending Approval', 'Admin Approved']),
                eligible_referral_subquery
            ).all()
            
            for progress, tier, user in matching_awards:
                pending_awards.append({
                    'id': progress.id,
                    'type': 'matching',
                    'user_id': user.id,
                    'user_name': user.name,
                    'award_name': tier.award_name,
                    'award_description': tier.award_description,
                    'match_count': progress.current_matches,
                    'required_count': progress.required_matches,
                    'budgeted_amount': float(progress.budgeted_amount) if progress.budgeted_amount else 0,
                    'achieved_at': progress.achievement_date.isoformat() if progress.achievement_date else None,
                    'current_status': progress.processed_status,
                    'admin_approved_by': progress.admin_approved_by,
                    'admin_approved_at': progress.admin_approved_at.isoformat() if progress.admin_approved_at else None,
                    # DC Protocol: Include procurement tracking fields from single source of truth
                    'dispatch_date': progress.dispatch_date.isoformat() if progress.dispatch_date else None,
                    'received_date': progress.received_date.isoformat() if progress.received_date else None,
                    'delivery_notes': progress.delivery_notes
                })
        
        # Get Bonanza Awards pending approval
        if award_type in ['all', 'bonanza']:
            # DC PROTOCOL: Only show bonanza for users with eligible referrals (activated on/after Oct 21, 2025)
            # Use aliased User to avoid correlation issues
            ReferralUser = aliased(User)
            eligible_referral_subquery = exists(
                select(ReferralUser.id).where(
                    and_(
                        ReferralUser.referrer_id == DynamicBonanzaHistory.user_id,
                        ReferralUser.activation_date >= PRODUCTION_START_DATE
                    )
                )
            )
            
            bonanza_awards = db.query(
                DynamicBonanzaHistory,
                User
            ).join(
                User, DynamicBonanzaHistory.user_id == User.id
            ).filter(
                DynamicBonanzaHistory.rvz_approval_status.in_(['Pending', 'Admin Approved']),
                eligible_referral_subquery
            ).all()
            
            for bonanza_history, user in bonanza_awards:
                pending_awards.append({
                    'id': bonanza_history.id,
                    'type': 'bonanza',
                    'user_id': user.id,
                    'user_name': user.name,
                    'award_name': bonanza_history.reward_name or bonanza_history.bonanza_name,
                    'award_description': bonanza_history.bonanza_name,
                    'bonanza_name': bonanza_history.bonanza_name,
                    'current_progress': bonanza_history.user_achieved_count,
                    'required_count': bonanza_history.target_count,
                    'budgeted_amount': float(bonanza_history.reward_amount) if bonanza_history.reward_amount else 0,
                    'achieved_at': bonanza_history.claimed_at.isoformat() if bonanza_history.claimed_at else None,
                    'current_status': bonanza_history.rvz_approval_status,
                    'admin_approved_by': bonanza_history.admin_approved_by,
                    'admin_approved_at': bonanza_history.admin_approved_at.isoformat() if bonanza_history.admin_approved_at else None,
                    # Bonanza-specific fields
                    'rvz_approval_status': bonanza_history.rvz_approval_status,
                    'procurement_status': bonanza_history.procurement_status,
                    'dispatch_date': bonanza_history.dispatch_date.isoformat() if bonanza_history.dispatch_date else None,
                    'received_date': bonanza_history.received_date.isoformat() if bonanza_history.received_date else None,
                    'delivery_notes': bonanza_history.delivery_notes
                })
        
        return {
            "success": True,
            "data": {
                "pending_awards": pending_awards,
                "total_count": len(pending_awards),
                "direct_count": sum(1 for a in pending_awards if a['type'] == 'direct'),
                "matching_count": sum(1 for a in pending_awards if a['type'] == 'matching'),
                "bonanza_count": sum(1 for a in pending_awards if a['type'] == 'bonanza')
            },
            "message": f"Found {len(pending_awards)} awards pending approval"
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch pending awards: {str(e)}"
        )


@router.post("/awards/supreme-approve")
async def supreme_approve_awards(
    request: SupremeApproveAwardsRequest,
    current_user: User = Depends(get_current_admin_user_hybrid),
    db: Session = Depends(get_db)
):
    """
    RVZ Supreme Award Approval - SKIP ALL APPROVAL STAGES
    
    RVZ can approve awards directly, skipping:
    - Admin Approval
    - Super Admin Approval
    
    Sets status directly to 'Super Admin Approved' for Finance processing
    
    DC Protocol: Updates user_award_progress or user_matching_award_progress tables
    Similar to income supreme approval workflow
    """
    try:
        if request.award_type not in ['direct', 'matching']:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="award_type must be 'direct' or 'matching'"
            )
        
        approved_count = 0
        failed_awards = []
        now = get_indian_time()
        
        # Process based on award type
        if request.award_type == 'direct':
            for award_id in request.award_ids:
                try:
                    progress = db.query(UserAwardProgress).filter(
                        UserAwardProgress.id == award_id
                    ).first()
                    
                    if not progress:
                        failed_awards.append({
                            'id': award_id,
                            'reason': 'Award not found'
                        })
                        continue
                    
                    if progress.processed_status not in ['Pending', 'Admin Approved']:
                        failed_awards.append({
                            'id': award_id,
                            'reason': f'Already processed: {progress.processed_status}'
                        })
                        continue
                    
                    # RVZ SUPREME APPROVAL - Set all approval fields (DC Protocol)
                    progress.admin_approved_by = _resolve_actor_id(current_user)
                    progress.admin_approved_at = now
                    progress.super_admin_decision_by = _resolve_actor_id(current_user)
                    progress.super_admin_decision_at = now
                    progress.super_admin_decision = 'approved'
                    progress.super_admin_notes = 'RVZ Supreme Approval - Auto-approved'
                    progress.processed_status = 'Procurement Pending'  # DC Protocol status
                    
                    # Audit log
                    AuditLogger.log(
                        db=db,
                        user_id=current_user.id,
                        action="RVZ_SUPREME_AWARD_APPROVAL",
                        entity_type="direct_award",
                        entity_id=str(award_id),
                        details=f"RVZ {current_user.id} supreme-approved direct award {award_id} for user {progress.user_id}",
                        severity="info"
                    )
                    
                    approved_count += 1
                    
                except Exception as e:
                    failed_awards.append({
                        'id': award_id,
                        'reason': str(e)
                    })
        
        elif request.award_type == 'matching':
            for award_id in request.award_ids:
                try:
                    progress = db.query(UserMatchingAwardProgress).filter(
                        UserMatchingAwardProgress.id == award_id
                    ).first()
                    
                    if not progress:
                        failed_awards.append({
                            'id': award_id,
                            'reason': 'Award not found'
                        })
                        continue
                    
                    if progress.processed_status not in ['Pending', 'Admin Approved']:
                        failed_awards.append({
                            'id': award_id,
                            'reason': f'Already processed: {progress.processed_status}'
                        })
                        continue
                    
                    # RVZ SUPREME APPROVAL - Set all approval fields (DC Protocol)
                    progress.admin_approved_by = _resolve_actor_id(current_user)
                    progress.admin_approved_at = now
                    progress.super_admin_decision_by = _resolve_actor_id(current_user)
                    progress.super_admin_decision_at = now
                    progress.super_admin_decision = 'approved'
                    progress.super_admin_notes = 'RVZ Supreme Approval - Auto-approved'
                    progress.processed_status = 'Procurement Pending'  # DC Protocol status
                    
                    # Audit log
                    AuditLogger.log(
                        db=db,
                        user_id=current_user.id,
                        action="RVZ_SUPREME_AWARD_APPROVAL",
                        entity_type="matching_award",
                        entity_id=str(award_id),
                        details=f"RVZ {current_user.id} supreme-approved matching award {award_id} for user {progress.user_id}",
                        severity="info"
                    )
                    
                    approved_count += 1
                    
                except Exception as e:
                    failed_awards.append({
                        'id': award_id,
                        'reason': str(e)
                    })
        
        db.commit()
        
        return {
            "success": True,
            "data": {
                "approved_count": approved_count,
                "failed_count": len(failed_awards),
                "failed_awards": failed_awards
            },
            "message": f"RVZ Supreme Approval: {approved_count} {request.award_type} awards approved, ready for Finance processing"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Supreme approval failed: {str(e)}"
        )
@router.post("/awards/supreme-reject")
async def supreme_reject_awards(
    request: SupremeRejectAwardsRequest,
    current_user: User = Depends(get_current_admin_user_hybrid),
    db: Session = Depends(get_db)
):
    """
    RVZ Supreme Award Rejection
    
    RVZ can reject awards with reason, setting:
    - Super Admin decision to 'rejected'
    - Processed status to 'Rejected'
    - Rejection reason documented
    
    DC Protocol: Updates user_award_progress or user_matching_award_progress tables
    """
    try:
        if request.award_type not in ['direct', 'matching']:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="award_type must be 'direct' or 'matching'"
            )
        
        rejected_count = 0
        failed_awards = []
        now = get_indian_time()
        
        # Process based on award type
        if request.award_type == 'direct':
            for award_id in request.award_ids:
                try:
                    progress = db.query(UserAwardProgress).filter(
                        UserAwardProgress.id == award_id
                    ).first()
                    
                    if not progress:
                        failed_awards.append({
                            'id': award_id,
                            'reason': 'Award not found'
                        })
                        continue
                    
                    if progress.processed_status not in ['Pending', 'Admin Approved']:
                        failed_awards.append({
                            'id': award_id,
                            'reason': f'Already processed: {progress.processed_status}'
                        })
                        continue
                    
                    # RVZ SUPREME REJECTION
                    progress.super_admin_decision_by = current_user.id
                    progress.super_admin_decision_at = now
                    progress.super_admin_decision = 'rejected'
                    progress.super_admin_notes = f'RVZ Supreme Rejection: {request.rejection_reason}'
                    progress.processed_status = 'Rejected'
                    progress.rejection_reason = request.rejection_reason
                    
                    # Audit log
                    AuditLogger.log(
                        db=db,
                        user_id=current_user.id,
                        action="RVZ_SUPREME_AWARD_REJECTION",
                        entity_type="direct_award",
                        entity_id=str(award_id),
                        details=f"RVZ {current_user.id} rejected direct award {award_id} for user {progress.user_id}. Reason: {request.rejection_reason}",
                        severity="warning"
                    )
                    
                    rejected_count += 1
                    
                except Exception as e:
                    failed_awards.append({
                        'id': award_id,
                        'reason': str(e)
                    })
        
        elif request.award_type == 'matching':
            for award_id in request.award_ids:
                try:
                    progress = db.query(UserMatchingAwardProgress).filter(
                        UserMatchingAwardProgress.id == award_id
                    ).first()
                    
                    if not progress:
                        failed_awards.append({
                            'id': award_id,
                            'reason': 'Award not found'
                        })
                        continue
                    
                    if progress.processed_status not in ['Pending', 'Admin Approved']:
                        failed_awards.append({
                            'id': award_id,
                            'reason': f'Already processed: {progress.processed_status}'
                        })
                        continue
                    
                    # RVZ SUPREME REJECTION
                    progress.super_admin_decision_by = current_user.id
                    progress.super_admin_decision_at = now
                    progress.super_admin_decision = 'rejected'
                    progress.super_admin_notes = f'RVZ Supreme Rejection: {request.rejection_reason}'
                    progress.processed_status = 'Rejected'
                    progress.rejection_reason = request.rejection_reason
                    
                    # Audit log
                    AuditLogger.log(
                        db=db,
                        user_id=current_user.id,
                        action="RVZ_SUPREME_AWARD_REJECTION",
                        entity_type="matching_award",
                        entity_id=str(award_id),
                        details=f"RVZ {current_user.id} rejected matching award {award_id} for user {progress.user_id}. Reason: {request.rejection_reason}",
                        severity="warning"
                    )
                    
                    rejected_count += 1
                    
                except Exception as e:
                    failed_awards.append({
                        'id': award_id,
                        'reason': str(e)
                    })
        
        db.commit()
        
        return {
            "success": True,
            "data": {
                "rejected_count": rejected_count,
                "failed_count": len(failed_awards),
                "failed_awards": failed_awards
            },
            "message": f"RVZ Supreme Rejection: {rejected_count} {request.award_type} awards rejected"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Supreme rejection failed: {str(e)}"
        )


@router.get("/awards/export-csv")
async def export_pending_awards_csv(
    award_type: str = 'all',
    current_user: User = Depends(get_current_admin_user_hybrid),
    db: Session = Depends(get_db)
):
    """
    RVZ Export Pending Awards to CSV
    
    Similar to member search CSV export
    Returns all pending awards as downloadable CSV file
    """
    try:
        import io
        import csv
        from fastapi.responses import StreamingResponse
        
        # Get pending awards (reuse same logic as pending-approval endpoint)
        pending_awards = []
        
        # Get Direct Awards
        if award_type in ['all', 'direct']:
            direct_awards = db.query(
                UserAwardProgress,
                DirectAwardTier,
                User
            ).join(
                DirectAwardTier, UserAwardProgress.award_tier_id == DirectAwardTier.id
            ).join(
                User, UserAwardProgress.user_id == User.id
            ).filter(
                UserAwardProgress.processed_status.in_(['Pending Approval', 'Admin Approved'])
            ).all()
            
            for progress, tier, user in direct_awards:
                pending_awards.append({
                    'Type': 'Direct',
                    'Award ID': progress.id,
                    'User ID': user.id,
                    'User Name': user.name,
                    'Award Name': tier.award_name,
                    'Progress': f"{progress.current_referrals}/{progress.required_referrals}",
                    'Budget': f"₹{float(progress.budgeted_amount) if progress.budgeted_amount else 0:,.2f}",
                    'Status': progress.processed_status,
                    'Achieved Date': progress.achieved_at.strftime('%Y-%m-%d') if progress.achieved_at else 'N/A',
                    'Admin Approved By': progress.admin_approved_by or 'N/A',
                    'Admin Approved At': progress.admin_approved_at.strftime('%Y-%m-%d %H:%M') if progress.admin_approved_at else 'N/A'
                })
        
        # Get Matching Awards
        if award_type in ['all', 'matching']:
            matching_awards = db.query(
                UserMatchingAwardProgress,
                MatchingAwardTier,
                User
            ).join(
                MatchingAwardTier, UserMatchingAwardProgress.matching_award_tier_id == MatchingAwardTier.id
            ).join(
                User, UserMatchingAwardProgress.user_id == User.id
            ).filter(
                UserMatchingAwardProgress.processed_status.in_(['Pending Approval', 'Admin Approved'])
            ).all()
            
            for progress, tier, user in matching_awards:
                pending_awards.append({
                    'Type': 'Matching',
                    'Award ID': progress.id,
                    'User ID': user.id,
                    'User Name': user.name,
                    'Award Name': tier.award_name,
                    'Progress': f"{progress.current_matches}/{progress.required_matches}",
                    'Budget': f"₹{float(progress.budgeted_amount) if progress.budgeted_amount else 0:,.2f}",
                    'Status': progress.processed_status,
                    'Achieved Date': progress.achievement_date.strftime('%Y-%m-%d') if progress.achievement_date else 'N/A',
                    'Admin Approved By': progress.admin_approved_by or 'N/A',
                    'Admin Approved At': progress.admin_approved_at.strftime('%Y-%m-%d %H:%M') if progress.admin_approved_at else 'N/A'
                })
        
        # Create CSV
        output = io.StringIO()
        if pending_awards:
            writer = csv.DictWriter(output, fieldnames=pending_awards[0].keys())
            writer.writeheader()
            writer.writerows(pending_awards)
        
        # Generate filename with timestamp
        from datetime import datetime
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"rvz_pending_awards_{award_type}_{timestamp}.csv"
        
        # Return as streaming response
        output.seek(0)
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"CSV export failed: {str(e)}"
        )


# ===================================================================================================
# RVZ SUPREME AWARDS PROCUREMENT ENDPOINTS
# RVZ has complete control: Approve → Purchase → Deliver
# ===================================================================================================

class RVZAwardPurchaseRequest(BaseModel):
    award_id: int
    award_type: str  # 'direct' or 'matching'
    vendor_name: str
    actual_cost_paid: float
    payment_mode: str
    payment_reference: str = None
    cost_variance_reason: str = None

class RVZAwardDeliveryRequest(BaseModel):
    award_id: int
    award_type: str  # 'direct' or 'matching'
    delivery_notes: str = None


@router.get("/awards/procurement-queue")
async def rvz_get_procurement_queue(
    status_filter: str = 'pending_purchase',
    award_type: str = 'all',
    current_user: User = Depends(get_current_admin_user_hybrid),
    db: Session = Depends(get_db)
):
    """
    RVZ Supreme: Get awards procurement queue
    Shows awards ready for purchase or delivery
    
    Status filters:
    - pending_purchase: Super Admin Approved, ready for RVZ to purchase
    - pending_delivery: Purchased, ready for RVZ to mark as delivered
    - all: All procurement stages
    """
    try:
        # Use ProcurementService for unified queue management
        result = ProcurementService.get_procurement_queue(
            db=db,
            item_type='award',
            status_filter=status_filter,
            award_type=award_type if award_type != 'all' else None
        )
        
        return {
            "success": True,
            "data": {
                "awards": result['items'],
                "total_count": result['total_count'],
                "total_budgeted": result['total_budgeted'],
                "total_spent": result['total_spent'],
                "pending_purchase_count": result['pending_purchase_count'],
                "pending_delivery_count": result['pending_delivery_count']
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching procurement queue: {str(e)}"
        )


@router.post("/awards/supreme-purchase")
async def rvz_supreme_purchase_award(
    request: RVZAwardPurchaseRequest,
    current_user: User = Depends(get_current_admin_user_hybrid),
    db: Session = Depends(get_db)
):
    """
    RVZ Supreme: Process award purchase
    RVZ can directly purchase awards (skip Finance Admin stage)
    """
    try:
        # Use ProcurementService for unified purchase processing
        result = ProcurementService.purchase_item(
            db=db,
            item_id=request.award_id,
            item_type=request.award_type,
            vendor_name=request.vendor_name,
            actual_cost_paid=Decimal(str(request.actual_cost_paid)),
            payment_mode=request.payment_mode,
            payment_reference=request.payment_reference,
            cost_variance_reason=request.cost_variance_reason,
            current_user=current_user
        )
        
        return {
            "success": True,
            "message": f"Award purchased successfully by RVZ (Variance: ₹{abs(result['variance'])} {'saved' if result['variance'] > 0 else 'overspent'})",
            "data": result
        }
        
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing purchase: {str(e)}"
        )


@router.post("/awards/supreme-deliver")
async def rvz_supreme_deliver_award(
    request: RVZAwardDeliveryRequest,
    current_user: User = Depends(get_current_admin_user_hybrid),
    db: Session = Depends(get_db)
):
    """
    RVZ Supreme: Mark award as delivered
    RVZ can directly mark awards as delivered
    """
    try:
        # Use ProcurementService for unified delivery processing
        result = ProcurementService.deliver_item(
            db=db,
            item_id=request.award_id,
            item_type=request.award_type,
            delivery_notes=request.delivery_notes,
            current_user=current_user
        )
        
        return {
            "success": True,
            "message": "Award marked as delivered by RVZ Supreme",
            "data": result
        }
        
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error marking delivery: {str(e)}"
        )


# ===================================================================================================
# RVZ SUPREME MNR 2.0 BONANZA APPROVAL ENDPOINTS
# RVZ must approve MNR bonanza claims before they go to procurement queue
# ===================================================================================================

class RVZBonanzaApprovalRequest(BaseModel):
    bonanza_history_id: int
    decision: str  # 'approve' or 'reject'
    rejection_reason: str = None


@router.post("/bonanza/mnr2-approve")
async def rvz_approve_mnr2_bonanza(
    request: RVZBonanzaApprovalRequest,
    current_user: User = Depends(get_current_admin_user_hybrid),
    db: Session = Depends(get_db)
):
    """
    RVZ Supreme: Approve or Reject MNR Bonanza Claim
    After RVZ approval, bonanza goes to procurement queue for purchase
    """
    try:
        # Get bonanza history record
        bonanza_record = db.query(DynamicBonanzaHistory).filter(
            DynamicBonanzaHistory.id == request.bonanza_history_id
        ).first()
        
        if not bonanza_record:
            raise HTTPException(status_code=404, detail="Bonanza claim not found")
        
        if bonanza_record.rvz_approval_status not in ['Pending RVZ Approval', 'RVZ Rejected']:
            raise HTTPException(
                status_code=400, 
                detail=f"Bonanza is already {bonanza_record.rvz_approval_status}"
            )
        
        if request.decision == 'approve':
            # RVZ Approve - move to procurement queue
            bonanza_record.rvz_approval_status = 'Procurement Pending'
            bonanza_record.rvz_approved_by = _resolve_actor_id(current_user)
            bonanza_record.rvz_approved_at = get_indian_time()
            bonanza_record.procurement_status = 'Pending Purchase'
            bonanza_record.rvz_rejection_reason = None
            
            message = f"MNR Bonanza approved by RVZ and added to procurement queue"
            
        elif request.decision == 'reject':
            # RVZ Reject - bonanza claim denied
            if not request.rejection_reason:
                raise HTTPException(
                    status_code=400,
                    detail="Rejection reason is required when rejecting bonanza"
                )
            
            bonanza_record.rvz_approval_status = 'RVZ Rejected'
            bonanza_record.rvz_approved_by = _resolve_actor_id(current_user)
            bonanza_record.rvz_approved_at = get_indian_time()
            bonanza_record.rvz_rejection_reason = request.rejection_reason
            bonanza_record.procurement_status = None
            
            message = f"MNR Bonanza rejected by RVZ"
            
        else:
            raise HTTPException(
                status_code=400,
                detail="Decision must be 'approve' or 'reject'"
            )
        
        db.commit()
        
        # Audit log
        AuditLogger.log_rvz_action(
            db=db,
            action_type=f"MNR Bonanza {request.decision.title()}",
            resource_type="DynamicBonanzaHistory",
            resource_id=bonanza_record.id,
            current_user=current_user,
            details={
                'user_id': bonanza_record.user_id,
                'bonanza_id': bonanza_record.bonanza_id,
                'award_name': bonanza_record.award_name,
                'decision': request.decision,
                'rejection_reason': request.rejection_reason
            }
        )
        
        return {
            "success": True,
            "message": message,
            "data": {
                'bonanza_history_id': bonanza_record.id,
                'user_id': bonanza_record.user_id,
                'rvz_approval_status': bonanza_record.rvz_approval_status,
                'procurement_status': bonanza_record.procurement_status
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing bonanza approval: {str(e)}"
        )


# ===================================================================================================
# RVZ SUPREME BONANZA PROCUREMENT ENDPOINTS
# RVZ has complete control: Approve → Purchase → Deliver
# Same pattern as Awards Procurement
# ===================================================================================================

class RVZBonanzaPurchaseRequest(BaseModel):
    bonanza_progress_id: int
    vendor_name: str
    actual_cost_paid: float
    payment_mode: str
    payment_reference: str = None
    cost_variance_reason: str = None

class RVZBonanzaDeliveryRequest(BaseModel):
    bonanza_progress_id: int
    delivery_notes: str = None


@router.get("/bonanza/procurement-queue")
async def rvz_get_bonanza_procurement_queue(
    status_filter: str = 'pending_purchase',
    current_user: User = Depends(get_current_admin_user_hybrid),
    db: Session = Depends(get_db)
):
    """
    RVZ Supreme: Get bonanza procurement queue
    Shows bonanza claims ready for purchase or delivery
    
    Status filters:
    - pending_purchase: Super Admin Approved, ready for RVZ to purchase
    - pending_delivery: Purchased, ready for RVZ to mark as delivered
    - all: All procurement stages
    """
    try:
        # Use ProcurementService for unified queue management
        result = ProcurementService.get_procurement_queue(
            db=db,
            item_type='bonanza',
            status_filter=status_filter
        )
        
        return {
            "success": True,
            "data": {
                "bonanzas": result['items'],
                "total_count": result['total_count'],
                "total_budgeted": result['total_budgeted'],
                "total_spent": result['total_spent'],
                "pending_purchase_count": result['pending_purchase_count'],
                "pending_delivery_count": result['pending_delivery_count']
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching bonanza procurement queue: {str(e)}"
        )


@router.post("/bonanza/supreme-purchase")
async def rvz_supreme_purchase_bonanza(
    request: RVZBonanzaPurchaseRequest,
    current_user: User = Depends(get_current_admin_user_hybrid),
    db: Session = Depends(get_db)
):
    """
    RVZ Supreme: Process bonanza purchase
    RVZ can directly purchase bonanza claims (skip Finance Admin stage)
    """
    try:
        # Use ProcurementService for unified purchase processing
        result = ProcurementService.purchase_item(
            db=db,
            item_id=request.bonanza_progress_id,
            item_type='bonanza',
            vendor_name=request.vendor_name,
            actual_cost_paid=Decimal(str(request.actual_cost_paid)),
            payment_mode=request.payment_mode,
            payment_reference=request.payment_reference,
            cost_variance_reason=request.cost_variance_reason,
            current_user=current_user
        )
        
        return {
            "success": True,
            "message": f"Bonanza purchased successfully by RVZ (Variance: ₹{abs(result['variance'])} {'saved' if result['variance'] > 0 else 'overspent'})",
            "data": result
        }
        
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing bonanza purchase: {str(e)}"
        )


@router.post("/bonanza/supreme-deliver")
async def rvz_supreme_deliver_bonanza(
    request: RVZBonanzaDeliveryRequest,
    current_user: User = Depends(get_current_admin_user_hybrid),
    db: Session = Depends(get_db)
):
    """
    RVZ Supreme: Mark bonanza as delivered
    RVZ can directly mark bonanza claims as delivered
    """
    try:
        # Use ProcurementService for unified delivery processing
        result = ProcurementService.deliver_item(
            db=db,
            item_id=request.bonanza_progress_id,
            item_type='bonanza',
            delivery_notes=request.delivery_notes,
            current_user=current_user
        )
        
        return {
            "success": True,
            "message": "Bonanza marked as delivered by RVZ Supreme",
            "data": result
        }
        
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error marking bonanza delivery: {str(e)}"
        )


# ===================================================================================================
# RVZ SUPREME TRAINING CLAIMS APPROVAL
# RVZ has complete control over training claim approvals
# ===================================================================================================

class RVZTrainingClaimApprovalRequest(BaseModel):
    claim_ids: List[int]
    action: str  # 'approve' or 'reject'
    rejection_reason: str = None


@router.get("/training-claims/pending")
async def rvz_get_pending_training_claims(
    current_user: User = Depends(get_current_admin_user_hybrid),
    db: Session = Depends(get_db)
):
    """
    RVZ Supreme: Get all pending training claims
    """
    try:
        from app.models.training_claim import TrainingClaim
        from app.models.training_course import TrainingCourse
        
        claims = db.query(
            TrainingClaim,
            TrainingCourse,
            User
        ).join(
            TrainingCourse, TrainingClaim.training_course_id == TrainingCourse.id
        ).join(
            User, TrainingClaim.user_id == User.id
        ).filter(
            TrainingClaim.status == 'Pending'
        ).all()
        
        claims_data = []
        for claim, course, user in claims:
            claims_data.append({
                'id': claim.id,
                'user_id': user.id,
                'user_name': user.name,
                'course_name': course.course_name,
                'course_fee': float(course.course_fee) if course.course_fee else 0,
                'trainee_name': claim.trainee_name,
                'trainee_contact': claim.trainee_contact,
                'submitted_at': claim.created_at.isoformat() if claim.created_at else None,
                'status': claim.status
            })
        
        return {
            "success": True,
            "data": {
                "claims": claims_data,
                "total_count": len(claims_data),
                "total_amount": sum(c['course_fee'] for c in claims_data)
            }
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching training claims: {str(e)}"
        )


@router.post("/training-claims/supreme-approve")
async def rvz_supreme_approve_training_claims(
    request: RVZTrainingClaimApprovalRequest,
    current_user: User = Depends(get_current_admin_user_hybrid),
    db: Session = Depends(get_db)
):
    """
    RVZ Supreme: Bulk approve/reject training claims
    """
    try:
        from app.models.training_claim import TrainingClaim
        
        claims = db.query(TrainingClaim).filter(
            TrainingClaim.id.in_(request.claim_ids),
            TrainingClaim.status == 'Pending'
        ).all()
        
        if not claims:
            raise HTTPException(status_code=404, detail="No pending claims found")
        
        processed_count = 0
        for claim in claims:
            if request.action == 'approve':
                claim.status = 'Approved'
                claim.approved_by_user_id = _resolve_actor_id(current_user)
                claim.approved_at = get_indian_time()
            elif request.action == 'reject':
                claim.status = 'Rejected'
                claim.rejection_reason = request.rejection_reason or 'Rejected by RVZ Supreme'
                claim.approved_by_user_id = _resolve_actor_id(current_user)
                claim.approved_at = get_indian_time()
            
            processed_count += 1
        
        db.commit()
        
        # Audit log
        AuditLogger.log_action(
            db=db,
            user=current_user,
            action=f"RVZ_SUPREME_TRAINING_CLAIMS_{request.action.upper()}",
            resource_type='TrainingClaim',
            resource_id=','.join(map(str, request.claim_ids)),
            details={"count": processed_count, "action": request.action}
        )
        
        return {
            "success": True,
            "message": f"RVZ Supreme {request.action}d {processed_count} training claims",
            "data": {"processed": processed_count}
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing training claims: {str(e)}"
        )




# ===================================================================================================
# RVZ SUPREME USER MANAGEMENT - BULK OPERATIONS
# RVZ can bulk activate, deactivate, upgrade users
# ===================================================================================================

class RVZBulkUserOperationRequest(BaseModel):
    user_ids: List[str]
    operation: str  # 'activate', 'deactivate', 'upgrade_package', 'pause_ved'
    package_id: int = None  # For package upgrades
    reason: str = None


@router.post("/users/supreme-bulk-operation")
async def rvz_supreme_bulk_user_operation(
    request: RVZBulkUserOperationRequest,
    current_user: User = Depends(get_current_admin_user_hybrid),
    db: Session = Depends(get_db)
):
    """
    RVZ Supreme: Bulk user operations
    RVZ can perform bulk activate/deactivate/upgrade operations
    """
    try:
        users = db.query(User).filter(User.id.in_(request.user_ids)).all()
        
        if not users:
            raise HTTPException(status_code=404, detail="No users found")
        
        processed_count = 0
        for user in users:
            if request.operation == 'activate':
                user.is_active = True
                user.activated_at = get_indian_time()
                user.activated_by = current_user.id
            elif request.operation == 'deactivate':
                user.is_active = False
            elif request.operation == 'upgrade_package' and request.package_id:
                user.package_id = request.package_id
            elif request.operation == 'pause_ved':
                user.ved_income_paused = True
            
            processed_count += 1
        
        db.commit()
        
        # Audit log
        AuditLogger.log_action(
            db=db,
            user=current_user,
            action=f"RVZ_SUPREME_BULK_{request.operation.upper()}",
            resource_type='User',
            resource_id=','.join(request.user_ids[:10]),  # First 10 IDs
            details={"count": processed_count, "operation": request.operation, "reason": request.reason}
        )
        
        return {
            "success": True,
            "message": f"RVZ Supreme bulk {request.operation} completed for {processed_count} users",
            "data": {"processed": processed_count}
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error performing bulk operation: {str(e)}"
        )


# ===================================================================================================
# RVZ SUPREME KYC/BANKING INDIVIDUAL APPROVALS
# RVZ can approve individual KYC/Banking requests on-demand
# ===================================================================================================

class RVZIndividualApprovalRequest(BaseModel):
    user_ids: List[str]
    approval_type: str  # 'kyc', 'banking', 'both'


@router.post("/users/supreme-kyc-banking-approve")
async def rvz_supreme_kyc_banking_approve(
    request: RVZIndividualApprovalRequest,
    current_user: User = Depends(get_current_admin_user_hybrid),
    db: Session = Depends(get_db)
):
    """
    RVZ Supreme: Individual KYC/Banking approvals
    RVZ can approve KYC/Banking for specific users on-demand
    """
    try:
        users = db.query(User).filter(User.id.in_(request.user_ids)).all()
        
        if not users:
            raise HTTPException(status_code=404, detail="No users found")
        
        processed_count = 0
        for user in users:
            if request.approval_type in ['kyc', 'both']:
                user.kyc_document_status = 'Approved'
                user.kyc_approved_at = get_indian_time()
                user.kyc_approved_by = _resolve_actor_id(current_user)
            
            if request.approval_type in ['banking', 'both']:
                user.bank_details_status = 'Approved'
                user.bank_approved_at = get_indian_time()
                user.bank_approved_by = _resolve_actor_id(current_user)
            
            processed_count += 1
        
        db.commit()
        
        # Trigger wallet sync for approved users
        from app.services.wallet_sync_service import WalletSyncService
        for user in users:
            try:
                WalletSyncService.sync_user_wallet_realtime(db, user.id)
            except:
                pass  # Continue even if sync fails
        
        # Audit log
        AuditLogger.log_action(
            db=db,
            user=current_user,
            action=f"RVZ_SUPREME_{request.approval_type.upper()}_APPROVE",
            resource_type='User',
            resource_id=','.join(request.user_ids),
            details={"count": processed_count, "approval_type": request.approval_type}
        )
        
        return {
            "success": True,
            "message": f"RVZ Supreme {request.approval_type} approved for {processed_count} users",
            "data": {
                "processed": processed_count,
                "approval_type": request.approval_type,
                "wallet_sync_triggered": True
            }
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing KYC/Banking approvals: {str(e)}"
        )





# ===================================================================================================
# FRONTEND PAGE ROUTES - RVZ SUPREME PAGES
# ===================================================================================================

import os
from fastapi.responses import HTMLResponse

@router.get("/rvz/awards/procurement")
async def rvz_awards_procurement_page(
    current_user: User = Depends(get_current_admin_user_hybrid)
):
    """RVZ Supreme Awards Procurement frontend page"""
    html_path = os.path.join(os.getcwd(), "frontend/templates/rvz/awards_procurement.html")
    with open(html_path, 'r') as f:
        html_content = f.read()
    return HTMLResponse(content=html_content)


@router.get("/rvz/bonanza/procurement")
async def rvz_bonanza_procurement_page(
    current_user: User = Depends(get_current_admin_user_hybrid)
):
    """RVZ Supreme Bonanza Procurement frontend page"""
    html_path = os.path.join(os.getcwd(), "frontend/templates/rvz/bonanza_procurement.html")
    with open(html_path, 'r') as f:
        html_content = f.read()
    return HTMLResponse(content=html_content)


@router.get("/rvz/training-claims/approval")
async def rvz_training_claims_approval_page(
    current_user: User = Depends(get_current_admin_user_hybrid)
):
    """RVZ Supreme Training Claims Approval frontend page"""
    html_path = os.path.join(os.getcwd(), "frontend/templates/rvz/training_claims_approval.html")
    with open(html_path, 'r') as f:
        html_content = f.read()
    return HTMLResponse(content=html_content)



@router.get("/rvz/user-management")
async def rvz_user_management_page(
    current_user: User = Depends(get_current_admin_user_hybrid)
):
    """RVZ Supreme User Management frontend page"""
    html_path = os.path.join(os.getcwd(), "frontend/templates/rvz/user_management.html")
    with open(html_path, 'r') as f:
        html_content = f.read()
    return HTMLResponse(content=html_content)


@router.get("/rvz/kyc-banking/approval")
async def rvz_kyc_banking_approval_page(
    current_user: User = Depends(get_current_admin_user_hybrid)
):
    """RVZ Supreme KYC/Banking Approval frontend page"""
    html_path = os.path.join(os.getcwd(), "frontend/templates/rvz/kyc_banking_approval.html")
    with open(html_path, 'r') as f:
        html_content = f.read()
    return HTMLResponse(content=html_content)


@router.get("/vgk/partner-kyc-review")
async def vgk_partner_kyc_review_page(
    current_user: User = Depends(get_current_admin_user_hybrid)
):
    """VGK Partner KYC Document Review — staff view individual docs, validate/approve/reject"""
    html_path = os.path.join(os.getcwd(), "frontend/templates/vgk/partner_kyc_review.html")
    with open(html_path, 'r') as f:
        html_content = f.read()
    return HTMLResponse(content=html_content)




