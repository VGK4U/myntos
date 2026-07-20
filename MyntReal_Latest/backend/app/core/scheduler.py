"""
APScheduler Service for NEW 4-Package System
Handles midnight (12am) income calculations for previous day
"""

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime, date, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, func, text
from typing import Dict
from app.core.database import SessionLocal
from app.models.user import User
from app.models.transaction import PendingIncome, Transaction, CompanyEarnings
from app.models.coupon import Coupon
from app.models.placement import Placement
from app.constants import (
    PACKAGE_SYSTEM, INCOME_RATES, INCOME_LIMITS, COUPON_PACKAGE_MAP,
    get_earnings_split, get_ved_income, get_matching_income_per_point_match,
    PRODUCTION_START_DATE, get_package_config
)
from app.core.constants import ADMIN_DEDUCTION_RATE, TDS_DEDUCTION_RATE, NET_PAYOUT_RATE
from app.models.base import get_indian_time
import logging

logger = logging.getLogger(__name__)

# Global scheduler instance
scheduler = None

def check_duplicate_income(db: Session, user_id: str, income_type: str, business_date: date, related_user_id: str = None) -> bool:
    """
    DC PROTOCOL: Check if pending_income record already exists based on income-specific uniqueness rules
    
    This prevents duplicate income creation when the calculation job runs multiple times.
    
    UNIQUENESS RULES:
    - Matching Referral: (user_id, income_type, business_date) - ONE per day
    - Ved Income: (user_id, income_type, business_date, related_user_id) - ONE per activated user
    - Direct Referral: (user_id, income_type, business_date, related_user_id) - ONE per referral
    - Guru Dakshina: (user_id, income_type, business_date) - ONE per day (aggregated)
    
    Args:
        db: Database session
        user_id: User ID
        income_type: Income type (e.g., 'Matching Referral', 'Ved Income', 'Guru Dakshina')
        business_date: Business date
        related_user_id: Related user ID (required for Direct Referral, Ved Income)
    
    Returns:
        True if duplicate exists, False if safe to create
    """
    from sqlalchemy import cast, Date as SADate
    target_date = business_date.date() if hasattr(business_date, 'date') and callable(business_date.date) else business_date
    query = db.query(PendingIncome).filter(
        PendingIncome.user_id == user_id,
        PendingIncome.income_type == income_type,
        cast(PendingIncome.business_date, SADate) == target_date
    )
    
    # Add related_user_id filter for income types that can occur multiple times per day
    if income_type in ['Direct Referral', 'Ved Income']:
        if not related_user_id:
            logger.error(f"⚠️ DC PROTOCOL ERROR: related_user_id required for {income_type}")
            return False  # Allow creation if missing related_user_id (shouldn't happen)
        query = query.filter(PendingIncome.related_user_id == related_user_id)
    
    existing = query.first()
    
    if existing:
        key_desc = f"User {user_id}, Type {income_type}, Date {business_date}"
        if income_type in ['Direct Referral', 'Ved Income']:
            key_desc += f", Related User {related_user_id}"
        logger.warning(
            f"⚠️ DC PROTOCOL: Duplicate income blocked! "
            f"{key_desc} already exists (ID: {existing.id})"
        )
        return True
    return False

def auto_approve_and_credit_wallet(db: Session, pending_income: PendingIncome, auto_approved_by: str = "MNR00000000"):
    """
    Auto-approve pending income and immediately credit user wallet
    Bypasses manual approval workflow for automatic income distribution
    
    Args:
        db: Database session
        pending_income: PendingIncome record to auto-approve
        auto_approved_by: ID of auto-approver (default "MNR00000000" - SYSTEM_AUTO user)
    """
    from decimal import Decimal
    
    try:
        # Get user
        user = db.query(User).filter(User.id == pending_income.user_id).first()
        if not user:
            logger.error(f"User not found for auto-approval: {pending_income.user_id}")
            return False
        
        # DC Protocol Phase 1.7: Auto-approve to 'Completed' status
        # Materialized views compute wallet balances from pending_income records
        # No direct wallet writes needed - views automatically include 'Completed' status
        pending_income.verification_status = 'Completed'
        pending_income.admin_verified_by_id = auto_approved_by
        pending_income.admin_verified_at = get_indian_time()
        pending_income.super_admin_verified_by_id = auto_approved_by
        pending_income.super_admin_verified_at = get_indian_time()
        pending_income.accounts_paid_by_id = auto_approved_by
        pending_income.accounts_paid_at = get_indian_time()
        pending_income.notes = "AUTO-APPROVED: Automatic income distribution (no manual approval required)"
        
        # DC Protocol Phase 1.7: REMOVED direct wallet writes
        # Wallet balances are now computed from materialized views:
        # - user_withdrawable_wallet_balance: Includes 'Completed' status
        # Auto-approval instantly makes income available for withdrawal via materialized view
        
        # Create transaction record for audit trail (Transaction uses referrer_id/referred_user_id, not user_id)
        transaction = Transaction(
            referrer_id=pending_income.user_id,  # User receiving the income
            referred_user_id=pending_income.related_user_id or pending_income.user_id,  # Related user or self
            transaction_type=pending_income.income_type,
            amount=float(pending_income.net_amount),
            timestamp=get_indian_time()
        )
        db.add(transaction)
        
        # DC PROTOCOL PHASE 1.9 FIX: Create TransferQueue for auto-approved income
        # ISSUE: Auto-approved income had NO TransferQueue entry, breaking WVV workflow
        # This caused 20+ users to have incomplete Transfer Queue records
        # NOW: Creating TransferQueue for ALL income (auto-approved AND manually verified)
        from app.models.withdrawal import TransferQueue
        
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
                status='Completed',  # Mark as Completed since income already auto-approved
                created_at=get_indian_time(),
                created_by_id=auto_approved_by,
                notes='AUTO-CREATED: TransferQueue for auto-approved income (DC Protocol Phase 1.9)'
            )
            db.add(transfer_queue_entry)
            logger.info(f"✅ Created TransferQueue for auto-approved income {pending_income.id}")

        # DC-STATUTORY-GL-001: Post TDS + admin deductions to statutory GL accounts.
        # This closes the double-entry gap — wallet credits happen via materialized view
        # but the corresponding liability/income legs were never written to account_ledger.
        # Non-fatal: a GL failure must never block member wallet credit.
        try:
            from app.services.staff_accounts_service import LedgerPostingService as _LPS
            _co_id   = int(getattr(user, 'company_id', None) or 1)
            _biz     = pending_income.business_date
            _txn_dt  = _biz.date() if hasattr(_biz, 'date') else _biz
            _LPS.auto_post_statutory_deductions(
                db           = db,
                company_id   = _co_id,
                tds_amount   = pending_income.tds_deduction,
                admin_amount = pending_income.admin_deduction,
                txn_date     = _txn_dt,
                ref_type     = 'PENDING_INCOME',
                ref_id       = pending_income.id,
                ref_number   = f'PI-{pending_income.id:08d}',
                narration    = (
                    f'{pending_income.income_type} statutory deductions'
                    f' — {pending_income.user_id}'
                ),
                created_by_id = None,
            )
        except Exception as _sgl_e:
            logger.warning(f'[DC-STATUTORY-GL-001] GL post non-fatal for PI#{pending_income.id}: {_sgl_e}')

        # DC PROTOCOL: KEEP the pending income record (DO NOT DELETE)
        # pending_income table is the single source of truth for all earnings
        # Status 'Completed' indicates it's been processed and credited to wallet
        # Earnings pages read from pending_income table to display user's income history
        
        logger.info(f"✅ Auto-approved & credited: {pending_income.user_id} - ₹{pending_income.net_amount} ({pending_income.income_type})")
        return True
        
    except Exception as e:
        logger.error(f"Error auto-approving income {pending_income.id}: {e}")
        return False


def calculate_income_deductions_and_splits(gross_amount: float, package_points: float, apply_guru_dakshina: bool = True, upgrade_wallet_balance: float = None) -> dict:
    """
    Calculate deductions and wallet splits for an income amount
    
    CORRECT FORMULA (as per user requirement):
    - Guru Dakshina: gross × 2%
    - Admin Deduction: gross × 8%
    - TDS Deduction: gross × 2%
    - Net Amount: gross - (guru + admin + tds) = gross × 88%
    
    Diamond/Star/Loyal: 50/50 split until upgrade wallet reaches ₹15,000, then 100% withdrawable
    """
    guru_dakshina_deduction = 0.0
    if apply_guru_dakshina:
        guru_dakshina_deduction = gross_amount * (INCOME_RATES['guru_dakshina_percentage'] / 100)
    
    admin_deduction = gross_amount * (INCOME_RATES['admin_charge_rate'] / 100)
    tds_deduction = gross_amount * (INCOME_RATES['tds_rate'] / 100)
    
    net_amount = gross_amount - guru_dakshina_deduction - admin_deduction - tds_deduction
    
    split = get_earnings_split(package_points, upgrade_wallet_balance)
    withdrawal_percentage = split['withdrawable']
    upgrade_percentage = split['upgraded_wallet']
    
    withdrawal_amount = net_amount * (withdrawal_percentage / 100)
    upgrade_amount = net_amount * (upgrade_percentage / 100)
    
    return {
        'guru_dakshina_deduction': round(guru_dakshina_deduction),
        'admin_deduction': round(admin_deduction),
        'tds_deduction': round(tds_deduction),
        'net_amount': round(net_amount),
        'withdrawal_wallet_amount': round(withdrawal_amount),
        'upgraded_wallet_amount': round(upgrade_amount)
    }

def get_leg_points_recursive(db: Session, user_id: str, side: str) -> int:
    """
    Recursively calculate total package points in a leg (Left or Right)
    
    Args:
        user_id: Parent user ID
        side: 'Left' or 'Right' (will be converted to lowercase)
    
    Returns:
        Total package_points in that leg (full downline)
    """
    total_points = 0
    
    # Convert side to lowercase to match database values ('left', 'right')
    side_lower = side.lower()
    
    # Get all immediate children on this side
    placements = db.query(Placement).join(
        User, Placement.child_id == User.id
    ).filter(
        Placement.parent_id == user_id,
        Placement.side == side_lower,
        User.coupon_status.in_(['Activated', 'Active']),
        User.package_points > 0
    ).all()
    
    for placement in placements:
        child = db.query(User).filter(User.id == placement.child_id).first()
        if child and child.package_points:
            # Add this child's points
            total_points += child.package_points
            
            # Recursively add ALL downline points (both legs of this child)
            total_points += get_leg_points_recursive(db, child.id, 'Left')
            total_points += get_leg_points_recursive(db, child.id, 'Right')
    
    return total_points

def calculate_effective_matching_count(db: Session, user_id: str) -> dict:
    """
    Calculate effective matching count for Awards/Bonanza/Field Allowances
    
    OCTOBER 21, 2025 RESET LOGIC:
    - Uses post-Oct 21 activation date filtering for ALL users
    - ALWAYS calculate and return raw matching achievements (users MUST see progress)
    - Return eligibility flag separately
    - Let CALLERS decide how to use eligibility (lock UI, mark as pending, etc.)
    
    Eligibility Criteria (checked but not enforced here):
    1. User must have first_matching_achieved = True (database field)
    2. User must have direct referrals on BOTH sides (1:1 active points from direct referrals)
    
    Example:
    - Left: 5, Right: 12 (post-Oct 21) → Achievement = 5, is_eligible = True/False
    
    Returns:
        dict with effective_count (raw achievement), is_eligible (bool), left_points, right_points
    """
    try:
        # CRITICAL FIX: Use Oct 21 filtered calculation (not stale all-time data)
        from app.services.sql_utils import get_matching_pairs_with_reset_logic_sql
        AWARDS_RESET_DATE = date(2025, 10, 21)
        
        # Get POST-OCT 21 leg points and matching pairs
        reset_result = get_matching_pairs_with_reset_logic_sql(
            db, 
            user_id, 
            reset_date=str(AWARDS_RESET_DATE)
        )
        
        left_points = reset_result['left_points']
        right_points = reset_result['right_points']
        raw_matching = reset_result['matching_pairs']
        
        # ALWAYS CALCULATE ACHIEVEMENTS (regardless of eligibility)
        # EARNED MATCHING = Apply -1 to LARGER side first, then MIN(Left, Right)
        # First match bonus uses 2 points from larger side, 1 from smaller side
        # Example: Left=5, Right=12 → First match uses (2 from right, 1 from left)
        # After first match: Left=4, Right=10 → Matching = MIN(4, 10) = 4
        # Simplified: Apply -1 to larger side BEFORE taking minimum
        
        if left_points > right_points:
            # Left is larger, apply -1 to left for first match bonus
            adjusted_left = max(0, left_points - 1)
            matching_count = int(min(adjusted_left, right_points))
        elif right_points > left_points:
            # Right is larger, apply -1 to right for first match bonus
            adjusted_right = max(0, right_points - 1)
            matching_count = int(min(left_points, adjusted_right))
        else:
            # Both sides equal, apply -1 to either (doesn't matter)
            matching_count = max(0, int(left_points) - 1)
        
        # CHECK ELIGIBILITY (but don't gate achievements)
        has_first_matching = check_first_matching_achieved(db, user_id)
        has_both_sides = check_direct_referrals_both_sides(db, user_id)
        is_eligible = has_first_matching and has_both_sides
        
        return {
            'effective_count': float(matching_count),
            'raw_count': int(matching_count),
            'left_points': float(left_points),
            'right_points': float(right_points),
            'is_eligible': is_eligible,
            'has_first_matching': has_first_matching,
            'has_direct_both_sides': has_both_sides
        }
        
    except Exception as e:
        logger.error(f"Error calculating effective matching count for {user_id}: {e}")
        return {
            'effective_count': 0.0,
            'raw_count': 0,
            'left_points': 0,
            'right_points': 0,
            'is_eligible': False,
            'has_first_matching': False,
            'has_direct_both_sides': False
        }

def check_direct_referrals_both_sides(db: Session, user_id: str, return_details: bool = False):
    """
    CRITICAL PREREQUISITE: Check if user has at least 1 POINT on BOTH sides (Group A + Group B)
    
    DC Protocol Feb 2026: Only counts FRESH activations (on or after Oct 21, 2025)
    
    Logic:
    - User must have referred at least 1 point on Group A (LEFT subtree)
    - User must have referred at least 1 point on Group B (RIGHT subtree)
    - Points come from DIRECT referrals only (referrer_id = user_id)
    - Uses Placement table tree structure to determine subtree side
    - Falls back to User.position field for backward compatibility
    - Only counts activations >= PRODUCTION_START_DATE (Oct 21, 2025)
    
    Returns:
        bool: True if BOTH conditions met (when return_details=False)
        dict: Detailed status with group_a_points, group_b_points, is_eligible, message (when return_details=True)
    """
    from datetime import datetime
    from sqlalchemy import text as sql_text
    
    fresh_activation_date = datetime(2025, 10, 21)
    
    result = db.execute(sql_text("""
        WITH RECURSIVE left_tree AS (
            SELECT child_id FROM placement WHERE parent_id = :uid AND side = 'left'
            UNION ALL
            SELECT p.child_id FROM placement p JOIN left_tree lt ON p.parent_id = lt.child_id
        ),
        right_tree AS (
            SELECT child_id FROM placement WHERE parent_id = :uid AND side = 'right'
            UNION ALL
            SELECT p.child_id FROM placement p JOIN right_tree rt ON p.parent_id = rt.child_id
        )
        SELECT
            COALESCE(SUM(CASE
                WHEN u.id IN (SELECT child_id FROM left_tree) THEN u.package_points
                WHEN u.id NOT IN (SELECT child_id FROM right_tree)
                     AND u.id NOT IN (SELECT child_id FROM left_tree)
                     AND u.position IN ('LEFT', 'Left') THEN u.package_points
                ELSE 0 END), 0) as group_a,
            COALESCE(SUM(CASE
                WHEN u.id IN (SELECT child_id FROM right_tree) THEN u.package_points
                WHEN u.id NOT IN (SELECT child_id FROM left_tree)
                     AND u.id NOT IN (SELECT child_id FROM right_tree)
                     AND u.position IN ('RIGHT', 'Right') THEN u.package_points
                ELSE 0 END), 0) as group_b
        FROM "user" u
        WHERE u.referrer_id = :uid
          AND u.activation_date IS NOT NULL
          AND u.activation_date >= :cutoff
          AND u.package_points > 0
          AND u.is_welcome_coupon = false
    """), {"uid": user_id, "cutoff": fresh_activation_date}).fetchone()
    
    group_a_points = float(result[0]) if result else 0.0
    group_b_points = float(result[1]) if result else 0.0
    
    is_eligible = group_a_points >= 1.0 and group_b_points >= 1.0
    
    if return_details:
        if is_eligible:
            message = None
        elif group_a_points < 1.0 and group_b_points < 1.0:
            message = "To unlock your earnings, you need at least 1 activated member in both Group A and Group B from your direct referrals in MNR"
        elif group_a_points < 1.0:
            message = "To unlock your earnings, you need at least 1 activated member in Group A from your direct referrals in MNR"
        else:
            message = "To unlock your earnings, you need at least 1 activated member in Group B from your direct referrals in MNR"
        
        return {
            'is_eligible': is_eligible,
            'group_a_points': float(group_a_points),
            'group_b_points': float(group_b_points),
            'message': message
        }
    
    return is_eligible

def check_first_matching_achieved(db: Session, user_id: str) -> bool:
    """
    Check if user achieved first matching - CASCADING LOGIC
    
    User achieves first matching if ANY of the following is true:
    1. User's database field: first_matching_achieved = True (admin approved)
    2. User's own downline: Has 2:1 or 1:2 ratio (Left ≥ 2×Right OR Right ≥ 2×Left)
    3. Any UPLINER achieved it: Cascades down to all downline members
    
    Returns:
        bool: True if user has achieved first matching eligibility
    """
    from app.services.sql_utils import get_leg_points_sql
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return False
    
    # Method 1: Database field (admin approved or previously calculated)
    if user.first_matching_achieved:
        return True
    
    # Method 2: Check user's own downline ratio (2:1 or 1:2)
    leg_points = get_leg_points_sql(db, user_id)
    left_points = leg_points['left']
    right_points = leg_points['right']
    
    # Must have at least 1 active pair (both sides must have points)
    if left_points >= 0.5 and right_points >= 0.5:
        # Check 2:1 or 1:2 ratio
        if left_points >= 2.0 * right_points or right_points >= 2.0 * left_points:
            return True
    
    # Method 3: Check if ANY upliner has achieved it (CASCADE DOWN)
    current_id = user.referrer_id
    visited = set()
    
    while current_id:
        if current_id in visited:
            break
        visited.add(current_id)
        
        upliner = db.query(User).filter(User.id == current_id).first()
        if not upliner:
            break
        
        # Check if this upliner has achieved first matching
        if upliner.first_matching_achieved:
            return True
        
        # Check upliner's own ratio
        upliner_points = get_leg_points_sql(db, upliner.id)
        upliner_left = upliner_points['left']
        upliner_right = upliner_points['right']
        
        if upliner_left >= 0.5 and upliner_right >= 0.5:
            if upliner_left >= 2.0 * upliner_right or upliner_right >= 2.0 * upliner_left:
                return True
        
        current_id = upliner.referrer_id
    
    return False


def get_user_eligibility_status(db: Session, user) -> dict:
    """
    DC Protocol Feb 2026: Comprehensive eligibility check for claims/validation
    
    Checks:
    1. User self-activation (is_activated = True)
    2. KYC approval status
    3. Program Utilisation (service usage via MNRPointsTransaction)
    4. Both groups activated (1:1 on Group A + Group B)
    5. First matching achieved (for matching/Ved income)
    
    Returns dict with:
    - is_eligible: bool (True if ALL basic criteria met including utilisation)
    - is_fully_eligible: bool (True if ALL criteria including first matching met)
    - blocking_reasons: list of specific messages
    - group_a_points: float
    - group_b_points: float
    - has_first_matching: bool
    - kyc_status: str
    - is_activated: bool
    - program_utilisation_completed: bool
    """
    from sqlalchemy import func as sqla_func
    from app.models.myntreal_incentive import MNRPointsTransaction
    
    blocking_reasons = []
    
    # Check 1: User self-activation
    is_activated = getattr(user, 'activation_date', None) is not None
    if not is_activated:
        blocking_reasons.append("Your account is not yet activated. Please complete activation to proceed.")
    
    # Check 2: KYC approval
    kyc_status = getattr(user, 'kyc_status', 'pending') or 'pending'
    if kyc_status.lower() != 'approved':
        blocking_reasons.append("KYC verification is pending. Please complete KYC to proceed.")
    
    # Check 3: Program Utilisation - service usage through MNR ecosystem
    SERVICE_CATEGORIES = ['VGK_REAL_DREAMS', 'VGK_CARE', 'EV_PURCHASE', 'SOLAR_SERVICES']
    service_usage_count = db.query(sqla_func.count(MNRPointsTransaction.id)).filter(
        MNRPointsTransaction.user_id == user.id,
        MNRPointsTransaction.transaction_type == 'debit',
        MNRPointsTransaction.benefit_category.in_(SERVICE_CATEGORIES)
    ).scalar() or 0
    program_utilisation_completed = service_usage_count > 0
    
    if not program_utilisation_completed:
        blocking_reasons.append("Program utilisation is pending. Please use an eligible service through the MNR Business Access Program to proceed.")
    
    # Check 4: Both groups activated (1:1)
    both_groups_check = check_direct_referrals_both_sides(db, user.id, return_details=True)
    group_a_points = both_groups_check['group_a_points']
    group_b_points = both_groups_check['group_b_points']
    has_both_groups = both_groups_check['is_eligible']
    
    if not has_both_groups:
        blocking_reasons.append(both_groups_check['message'])
    
    # Check 5: First matching (for matching/Ved income eligibility)
    has_first_matching = check_first_matching_achieved(db, user.id)
    
    # Basic eligibility = activated + KYC + utilisation + both groups
    is_eligible = is_activated and kyc_status.lower() == 'approved' and program_utilisation_completed and has_both_groups
    
    # Full eligibility = basic + first matching (for matching/Ved income)
    is_fully_eligible = is_eligible and has_first_matching
    
    return {
        'is_eligible': is_eligible,
        'is_fully_eligible': is_fully_eligible,
        'blocking_reasons': blocking_reasons,
        'group_a_points': group_a_points,
        'group_b_points': group_b_points,
        'has_both_groups': has_both_groups,
        'has_first_matching': has_first_matching,
        'kyc_status': kyc_status,
        'is_activated': is_activated,
        'program_utilisation_completed': program_utilisation_completed,
        'banner_message': blocking_reasons[0] if blocking_reasons else None
    }


def _get_actual_business_date(consumed_members: dict, fallback_date: date) -> date:
    """
    Determine actual business_date from consumed member activation dates.
    The match date is when the pair completed — the latest activation_date
    among all consumed members. Use this instead of the scheduler's run date,
    whether the activation was before or after the scheduler date.
    Falls back to scheduler date only if no valid activation dates found.
    """
    from datetime import datetime as dt
    latest_activation = None
    for side in ('left', 'right'):
        for m in consumed_members.get(side, []):
            act = m.get('activation_date')
            if act:
                if isinstance(act, str):
                    try:
                        act_date = dt.strptime(act, '%Y-%m-%d').date()
                    except (ValueError, TypeError):
                        continue
                elif hasattr(act, 'date'):
                    act_date = act.date()
                else:
                    act_date = act
                if latest_activation is None or act_date > latest_activation:
                    latest_activation = act_date
    return latest_activation if latest_activation else fallback_date


def calculate_matching_referral_income(db: Session, user: User, business_date: date) -> dict:
    """
    Calculate matching referral income - UPDATED WITH NEW ELIGIBILITY LOGIC
    
    NEW Logic (Per User Requirements):
    1. ALWAYS CALCULATE income (even if not eligible)
    2. Check eligibility criteria:
       - Must have 1:1 direct active points (at least 1 point on each side from direct referrals)
       - Must have first matching achieved (2:1 or 1:2 ratio from downline)
    3. If NOT eligible: Mark as "Not Eligible - Unlock your opportunity"
    4. Once eligible: Unlock and credit to wallet
    
    Income Formula:
    - Pairs = MIN(Available Left Points, Available Right Points)
    - Gross = Pairs × ₹2,000
    
    Package Points:
    - Platinum: 1.0 point
    - Diamond: 0.5 points
    - Star/Loyal: 0 points (not eligible)
    
    Returns:
        dict with gross_income, pairs_matched, left_consumed, right_consumed, match_type, is_eligible
    """
    try:
        # Check package points
        if not user.package_points or user.package_points == 0:
            return {
                'gross_income': 0.0, 
                'pairs_matched': 0, 
                'left_consumed': 0, 
                'right_consumed': 0, 
                'match_type': None,
                'is_eligible': False
            }
        
        # Get total leg points using SQL (10x faster!)
        from app.services.sql_utils import get_leg_points_sql, get_consumed_points_sql, get_consumed_zero_point_sql
        leg_points = get_leg_points_sql(db, user.id)
        total_left_points = leg_points['left']  # Total normal points in left leg
        total_right_points = leg_points['right']  # Total normal points in right leg
        left_zero_point_count = leg_points.get('left_zero_point_count', 0)
        right_zero_point_count = leg_points.get('right_zero_point_count', 0)
        
        # Get previously consumed points using SQL
        consumed_points = get_consumed_points_sql(db, user.id, 'Matching Referral')
        consumed_left = consumed_points['left']
        consumed_right = consumed_points['right']
        
        # Get previously consumed zero-point members
        consumed_zero = get_consumed_zero_point_sql(db, user.id)
        consumed_left_zero = consumed_zero['left']
        consumed_right_zero = consumed_zero['right']
        
        avail_left_zero = max(left_zero_point_count - consumed_left_zero, 0)
        avail_right_zero = max(right_zero_point_count - consumed_right_zero, 0)
        
        # Available points = total - consumed
        available_left = total_left_points - consumed_left
        available_right = total_right_points - consumed_right
        
        has_normal_match = available_left > 0 and available_right > 0
        has_exempted_left = available_left > 0 and avail_right_zero > 0
        has_exempted_right = available_right > 0 and avail_left_zero > 0
        
        if not has_normal_match and not has_exempted_left and not has_exempted_right:
            return {
                'gross_income': 0.0, 
                'pairs_matched': 0, 
                'left_consumed': 0, 
                'right_consumed': 0, 
                'match_type': None,
                'is_eligible': False,
                'exempted': None
            }
        
        # ALWAYS CALCULATE income (even if not eligible)
        FIXED_RATE_PER_MATCH = get_matching_income_per_point_match()  # ₹2,000
        
        # Check if this is the first matching income
        from app.models.transaction import PendingIncome
        previous_matching_count = db.query(func.count(PendingIncome.id)).filter(
            PendingIncome.user_id == user.id,
            PendingIncome.income_type == 'Matching Referral'
        ).scalar() or 0
        
        is_first_matching = (previous_matching_count == 0)
        
        matching_count = 0
        left_consumed = 0.0
        right_consumed = 0.0
        match_type = None
        
        if has_normal_match:
            # FIRST MATCHING: Use 2:1 or 1:2 ratio (for BOTH consumption AND display)
            if is_first_matching:
                if total_left_points > total_right_points:
                    matching_count = int(min(available_left / 2, available_right))
                    left_consumed = float(matching_count * 2)
                    right_consumed = float(matching_count * 1)
                    match_type = '2_to_1_first_matching'
                elif total_right_points > total_left_points:
                    matching_count = int(min(available_left, available_right / 2))
                    left_consumed = float(matching_count * 1)
                    right_consumed = float(matching_count * 2)
                    match_type = '1_to_2_first_matching'
                else:
                    matching_count = 0
                    match_type = None
                    logger.info(f"⚠️ First matching rejected for {user.id}: Equal points ({total_left_points}:{total_right_points}) - requires 2:1 or 1:2 ratio")
            else:
                matching_count = int(min(available_left, available_right))
                left_consumed = float(matching_count)
                right_consumed = float(matching_count)
                match_type = '1_to_1_matching'
        
        # DC Protocol (Feb 2026): Calculate exempted matches for zero-point members
        # Star/Loyal/Welcome (0 points) matched against normal → ₹0 income, shown as Exempted
        remaining_left_after_normal = max(available_left - left_consumed, 0)
        remaining_right_after_normal = max(available_right - right_consumed, 0)
        
        exempt_left_normal_right_zero = 0
        exempt_right_normal_left_zero = 0
        
        if remaining_left_after_normal > 0 and avail_right_zero > 0:
            exempt_left_normal_right_zero = min(int(remaining_left_after_normal), avail_right_zero)
        if remaining_right_after_normal > 0 and avail_left_zero > 0:
            exempt_right_normal_left_zero = min(int(remaining_right_after_normal), avail_left_zero)
        
        total_exempted = exempt_left_normal_right_zero + exempt_right_normal_left_zero
        exempted_data = None
        
        if total_exempted > 0:
            exempt_left_pts_consumed = float(exempt_left_normal_right_zero)
            exempt_right_pts_consumed = float(exempt_right_normal_left_zero)
            exempted_data = {
                'pairs': total_exempted,
                'left_points_consumed': exempt_left_pts_consumed,
                'right_points_consumed': exempt_right_pts_consumed,
                'left_zero_consumed': exempt_right_normal_left_zero,
                'right_zero_consumed': exempt_left_normal_right_zero,
            }
            logger.info(f"🔓 Exempted matching for {user.id}: {total_exempted} pairs (L-Normal×R-Zero={exempt_left_normal_right_zero}, R-Normal×L-Zero={exempt_right_normal_left_zero}) → ₹0 income")
        
        if matching_count <= 0 and total_exempted <= 0:
            return {
                'gross_income': 0.0, 
                'pairs_matched': 0, 
                'left_consumed': 0, 
                'right_consumed': 0, 
                'match_type': match_type if is_first_matching else None,
                'is_eligible': False,
                'exempted': None
            }
        
        # DC Protocol: Income calculation uses normal member points only
        from app.services.sql_utils import get_leg_points_with_welcome_coupon_breakdown
        breakdown = get_leg_points_with_welcome_coupon_breakdown(db, user.id)
        
        left_normal_pts = breakdown['left_normal']
        right_normal_pts = breakdown['right_normal']
        left_normal_count = breakdown['left_normal_count']
        right_normal_count = breakdown['right_normal_count']
        
        RATE_PER_POINT_SUM = 1000.0
        
        left_normal_avg = left_normal_pts / left_normal_count if left_normal_count > 0 else 0
        right_normal_avg = right_normal_pts / right_normal_count if right_normal_count > 0 else 0
        
        if matching_count > 0:
            gross_income = float(matching_count * (left_normal_avg + right_normal_avg) * RATE_PER_POINT_SUM)
        else:
            gross_income = 0.0
        
        # CHECK ELIGIBILITY (but don't block calculation)
        has_direct_both_sides = check_direct_referrals_both_sides(db, user.id)
        has_first_matching = check_first_matching_achieved(db, user.id)
        is_eligible = has_direct_both_sides and has_first_matching
        
        if matching_count > 0:
            if is_eligible:
                logger.info(f"✅ Matching Income (ELIGIBLE): {user.id} - {matching_count} pairs [{match_type}] × ₹{FIXED_RATE_PER_MATCH:,.0f} = ₹{gross_income:,.2f}")
            else:
                logger.info(f"🔒 Matching Income (NOT ELIGIBLE - will be held): {user.id} - {matching_count} pairs [{match_type}] × ₹{FIXED_RATE_PER_MATCH:,.0f} = ₹{gross_income:,.2f}")
        
        logger.info(f"  Match Type: {match_type} | Available: L={available_left} R={available_right} | Consumed: L={left_consumed} R={right_consumed} | Zero-Point: L={avail_left_zero} R={avail_right_zero}")
        
        return {
            'gross_income': float(gross_income),
            'pairs_matched': int(matching_count),
            'left_consumed': float(left_consumed),
            'right_consumed': float(right_consumed),
            'match_type': match_type,
            'is_eligible': is_eligible,
            'exempted': exempted_data
        }
        
    except Exception as e:
        logger.error(f"Error calculating matching income for {user.id}: {e}")
        return {
            'gross_income': 0.0, 
            'pairs_matched': 0, 
            'left_consumed': 0, 
            'right_consumed': 0, 
            'match_type': None,
            'is_eligible': False
        }

def is_user_in_binary_downline(db: Session, ancestor_id: str, descendant_id: str, max_depth: int = 20) -> bool:
    """
    Check if descendant_id is in the binary tree downline of ancestor_id
    
    Args:
        ancestor_id: The ancestor user ID (e.g., Ved member)
        descendant_id: The user to check if they're in the downline
        max_depth: Maximum depth to traverse (default 20 levels)
    
    Returns:
        True if descendant is in ancestor's binary downline, False otherwise
    """
    try:
        # Start from ancestor and traverse binary tree downward
        visited = set()
        queue = [(ancestor_id, 0)]  # (user_id, depth)
        
        while queue:
            current_id, depth = queue.pop(0)
            
            # Check depth limit
            if depth >= max_depth:
                continue
            
            # Prevent infinite loops
            if current_id in visited:
                continue
            visited.add(current_id)
            
            # Found the descendant
            if current_id == descendant_id:
                return True
            
            # Get children in binary tree
            children = db.query(Placement).filter(
                Placement.parent_id == current_id
            ).all()
            
            for child_placement in children:
                queue.append((child_placement.child_id, depth + 1))
        
        return False
        
    except Exception as e:
        logger.error(f"Error checking binary downline: {e}")
        return False

def find_closest_ved_owner(db: Session, activating_user_id: str) -> tuple:
    """
    Find Ved owner using ved_team_member table (FAST & ACCURATE)
    
    NEW LOGIC (Using dedicated table):
    - Query ved_team_member table for activating user
    - If found, return (ved_owner_id, ved_head_id)
    - If not found, user is NOT in any Ved Team → return (None, None)
    
    This eliminates:
    - Recursive CTE queries
    - Placement tree traversal bugs
    - Performance issues
    
    Returns:
        (ved_owner_id, ved_head_id) or (None, None) if not in Ved Team
    """
    try:
        from app.models.ved_team import VedTeamMember
        
        # FAST LOOKUP: Check if user is in any Ved Team
        ved_membership = db.query(VedTeamMember).filter(
            VedTeamMember.member_id == activating_user_id,
            VedTeamMember.is_active == True
        ).first()
        
        if not ved_membership:
            # User is NOT in any Ved Team → No Ved Income
            return (None, None)
        
        # User IS in Ved Team → Return owner and head
        logger.debug(f"Ved Income: {activating_user_id} is in Ved Team of {ved_membership.ved_owner_id} (Head: {ved_membership.ved_head_id})")
        return (ved_membership.ved_owner_id, ved_membership.ved_head_id)
        
    except Exception as e:
        logger.error(f"Error finding Ved owner for {activating_user_id}: {e}")
        return (None, None)


def calculate_ved_income(db: Session, user: User, business_date: date) -> tuple:
    """
    Calculate Ved Income when users activate in Ved member's binary tree (NO CASCADING)
    
    VED PROGRAM LOGIC:
    - Ved Head (3rd direct referral) must be ACTIVATED to generate income
    - Ved Head activation check: activation_date IS NOT NULL AND package_points >= 0.5
    - If Ved Head NOT activated → NO income generated (nobody gets it)
    - If Ved Head IS activated → Income goes to ved_owner_id (direct owner)
    - When user activates, find their CLOSEST Ved Head ancestor in placement tree
    - NO CASCADING: Stop at Ved Head boundaries
    
    Ved Income Rates:
    - Platinum activation (package_points >= 1.0): ₹1,000
    - Diamond activation (package_points >= 0.5): ₹500
    
    Prerequisites:
    - Ved Head must be activated
    - Ved owner must have 1:1 active direct referrals on both sides
    - Ved owner must have first matching achieved
    
    Returns:
        (gross_income_for_referrer, referrer_id) tuple
    """
    try:
        # Check if user activated on business_date
        if not user.activation_date:
            return (0.0, None)
        
        activation_date_only = user.activation_date.date() if hasattr(user.activation_date, 'date') else user.activation_date
        if activation_date_only != business_date:
            return (0.0, None)
        
        # User must have package points
        if not user.package_points or user.package_points == 0:
            return (0.0, None)
        
        # DC Protocol (Jan 2026): Welcome Coupon users generate ₹0 Ved Income for upliners
        if getattr(user, 'is_welcome_coupon', False):
            logger.info(f"Ved Income: ₹0 for {user.id} (Welcome Coupon - no income for Ved owner)")
            return (0.0, None)
        
        # Find Ved owner using ved_team_member table
        ved_owner_id, ved_head_id = find_closest_ved_owner(db, user.id)
        
        if not ved_owner_id or not ved_head_id:
            # User is NOT in any Ved Team
            return (0.0, None)
        
        # CRITICAL: Check if Ved Head is ACTIVATED
        # Ved Head must be activated to generate income
        ved_head = db.query(User).filter(User.id == ved_head_id).first()
        if not ved_head:
            return (0.0, None)
        
        if not ved_head.activation_date or ved_head.package_points < 0.5:
            logger.debug(f"Ved Income MISSED: Ved Head {ved_head_id} is NOT activated (income not generated)")
            return (0.0, None)
        
        # Get the Ved owner (person who earns Ved Income)
        ved_owner = db.query(User).filter(User.id == ved_owner_id).first()
        if not ved_owner:
            return (0.0, None)
        
        # CRITICAL: Exclude direct referrals (prevents double attribution)
        # Direct referrals should ONLY earn Direct Referral Income, NOT Ved Income
        if user.referrer_id == ved_owner_id:
            logger.debug(f"Ved Income skipped: {user.id} is a direct referral of Ved owner {ved_owner_id} (earns Direct Referral Income instead)")
            return (0.0, None)
        
        # CHECK: Ved income paused by Super Admin/RVZ ID
        if ved_owner.ved_paused:
            logger.debug(f"Ved Income skipped: Ved owner {ved_owner.id} has Ved income paused by admin")
            return (0.0, None)
        
        # CRITICAL PREREQUISITE: Ved owner must have 1:1 active direct referrals on both sides
        if not check_direct_referrals_both_sides(db, ved_owner.id):
            logger.debug(f"Ved Income skipped: Ved owner {ved_owner.id} missing 1:1 active direct referrals on both sides")
            return (0.0, None)
        
        # Ved owner must have first matching achieved (Step 2 prerequisite)
        if not check_first_matching_achieved(db, ved_owner.id):
            logger.debug(f"Ved Income skipped: Ved owner {ved_owner.id} hasn't achieved first matching")
            return (0.0, None)
        
        # CRITICAL VED PROGRAM RULE 6: ONE-TIME INCOME PER ACTIVATION (Lifetime Protection)
        # Check if Ved income already paid OR PENDING for this user's activation
        # Prevents duplicates even if scheduler reruns before auto-approval completes
        from app.models.transaction import Transaction
        
        # Check for existing Transaction
        existing_transaction = db.query(Transaction).filter(
            Transaction.referred_user_id == user.id,
            Transaction.transaction_type == 'Ved Income'
        ).first()
        
        if existing_transaction:
            logger.debug(f"Ved Income skipped: User {user.id} activation already generated Ved income (txn {existing_transaction.id})")
            return (0.0, None)
        
        # Check for existing PendingIncome (protects against scheduler reruns)
        existing_pending = db.query(PendingIncome).filter(
            PendingIncome.related_user_id == user.id,
            PendingIncome.income_type == 'Ved Income'
        ).first()
        
        if existing_pending:
            logger.debug(f"Ved Income skipped: User {user.id} activation already has pending Ved income (pending {existing_pending.id})")
            return (0.0, None)
        
        # Calculate Ved income amount based on activating user's package
        ved_amount = get_ved_income(user.package_points)
        if ved_amount <= 0:
            return (0.0, None)
        
        # Ved Income: User {user.id} activated under Ved member {ved_member_id}
        # NO CASCADING: Only Ved owner {ved_owner.id} earns ₹{ved_amount}
        logger.info(f"Ved Income (NO CASCADE): {user.id} activated under Ved {ved_member_id} -> Owner {ved_owner.id} earns ₹{ved_amount}")
        return (float(ved_amount), ved_owner.id)
        
    except Exception as e:
        logger.error(f"Error calculating Ved income for {user.id}: {e}")
        return (0.0, None)

def calculate_direct_referral_income(db: Session, user: User, business_date: date) -> tuple:
    """
    Calculate Direct Referral bonus when a referred user activates
    
    Logic:
    - Bonus triggers when referred user ACTIVATES (on activation date)
    - Bonus based on activated user's package:
      * Platinum (15000): ₹3,000 (UNLIMITED - no cap)
      * Diamond (7500): ₹1,500 (UNLIMITED - no cap)
      * Blue/Loyal (1000/500): ₹0 initially
    - Referrer must be activated (have package_points > 0)
    - NO LIMIT on number of direct referral bonuses
    
    Returns:
        (gross_bonus_for_referrer, referrer_id) tuple
    """
    try:
        # Check if user activated on business_date
        if not user.activation_date:
            return (0.0, None)
        
        activation_date_only = user.activation_date.date() if hasattr(user.activation_date, 'date') else user.activation_date
        if activation_date_only != business_date:
            return (0.0, None)
        
        # User must have package points
        if not user.package_points or user.package_points == 0:
            return (0.0, None)
        
        # User must have referrer
        if not user.referrer_id:
            return (0.0, None)
        
        # CRITICAL VALIDATION: Prevent self-referral bug (user cannot refer themselves)
        if user.id == user.referrer_id:
            logger.error(f"❌ SELF-REFERRAL BUG BLOCKED: User {user.id} has referrer_id = themselves! This violates business logic.")
            return (0.0, None)
        
        # DC Protocol (Jan 2026): Welcome Coupon users generate ₹0 for sponsors
        if getattr(user, 'is_welcome_coupon', False):
            logger.info(f"Direct Referral: ₹0 for {user.id} (Welcome Coupon - no income for sponsor)")
            return (0.0, None)
        
        # Get referrer
        referrer = db.query(User).filter(User.id == user.referrer_id).first()
        if not referrer:
            return (0.0, None)
        
        # Referrer must be activated (have package points)
        # DC Protocol: Welcome Coupon referrers CAN earn Direct Referral income (reward for sponsoring)
        if not referrer.package_points or referrer.package_points == 0:
            # Welcome Coupon referrers have package_points=0, but still earn Direct Referral
            if not getattr(referrer, 'is_welcome_coupon', False):
                logger.debug(f"Direct Referral skipped: Referrer {referrer.id} not activated")
                return (0.0, None)
        
        # Determine bonus amount based on activated user's package
        # package_points represents matching points:
        # 1.0 = Platinum, 0.5 = Diamond, 0 = Star/Loyal
        bonus_amount = 0.0
        
        if user.package_points == 1.0 or user.package_points == 1:  # Platinum
            bonus_amount = 3000.0
        elif user.package_points == 0.5:  # Diamond
            bonus_amount = 1500.0
        else:  # Star (0) or Loyal (0) - no bonus
            return (0.0, None)
        
        # NO CAP - Direct referrals are UNLIMITED
        current_bonus_count = referrer.referral_bonus_count or 0
        logger.info(f"Direct Referral: {user.id} (activated under {referrer.id}) - Referrer earns ₹{bonus_amount} (bonus #{current_bonus_count + 1})")
        return (float(bonus_amount), referrer.id)
        
    except Exception as e:
        logger.error(f"Error calculating direct referral income for {user.id}: {e}")
        return (0.0, None)

def calculate_guru_dakshina(db: Session, user: User, business_date: date) -> float:
    """
    Calculate Guru Dakshina (2% of each direct referral's total daily GROSS earnings)
    
    NOTE: Guru Dakshina does NOT require 1:1 active direct referrals check
    (Unlike Matching Referral and Ved Income which do require it)
    
    Logic:
    1. Get all direct referrals
    2. Sum their GROSS earnings for business_date (EXCLUDING Guru Dakshina itself)
    3. Guru Dakshina = 2% of total GROSS earnings
    
    Returns:
        Gross Guru Dakshina amount
    """
    try:
        # Get all direct referrals
        direct_referrals = db.query(User).filter(
            User.referrer_id == user.id
        ).all()
        
        if not direct_referrals:
            return 0.0
        
        total_referral_gross_earnings = 0.0
        
        # Sum each referral's GROSS earnings for business_date (EXCLUDING Guru Dakshina)
        # DC Protocol (Jan 2026): Welcome Coupon users have ₹0 earnings to contribute
        for referral in direct_referrals:
            # Skip Welcome Coupon users - they have no earnings to contribute
            if getattr(referral, 'is_welcome_coupon', False):
                continue
            # Sum gross_amount from PendingIncome, excluding Guru Dakshina income type
            referral_gross = db.query(func.sum(PendingIncome.gross_amount)).filter(
                PendingIncome.user_id == referral.id,
                PendingIncome.business_date == business_date,
                PendingIncome.income_type != 'Guru Dakshina'  # EXCLUDE Guru Dakshina to avoid circular dependency
            ).scalar() or 0.0
            
            total_referral_gross_earnings += float(referral_gross)
        
        if total_referral_gross_earnings <= 0:
            return 0.0
        
        # Calculate 2% Guru Dakshina on GROSS
        guru_dakshina = total_referral_gross_earnings * (INCOME_RATES['guru_dakshina_percentage'] / 100)
        
        if guru_dakshina > 0:
            logger.info(f"Guru Dakshina: {user.id} - 2% of ₹{total_referral_gross_earnings:.2f} GROSS = ₹{guru_dakshina:.2f}")
        
        return float(guru_dakshina)
        
    except Exception as e:
        logger.error(f"Error calculating Guru Dakshina for {user.id}: {e}")
        return 0.0

def check_field_allowance_eligibility(db: Session, user: User) -> dict:
    """
    Check field allowance eligibility with UPDATED CRITERIA
    
    NEW ELIGIBILITY REQUIREMENTS (MANDATORY):
    1. UNIVERSAL CRITERIA (MUST have BOTH):
       - 1:1 active direct referrals on both LEFT and RIGHT positions
       - First matching achieved (2:1 or 1:2 ratio from downline)
    
    2. SPECIFIC CRITERIA (in addition to universal):
       - Standard Field Allowance: ≥7 direct referral POINTS + ≥20 effective matching + balanced sides
       - Car Allowance: ≥250 effective matching + balanced sides
    
    POINTS: Platinum=1.0, Diamond=0.5, Blue/Loyal=0
    
    Returns:
        dict with eligible_type ('standard'/'car'/None), effective_matching_count, direct_points, eligibility_status
    """
    try:
        # CHECK UNIVERSAL ELIGIBILITY CRITERIA (same as Matching/Ved Income/Awards/Bonanza)
        has_direct_both_sides = check_direct_referrals_both_sides(db, user.id)
        has_first_matching = check_first_matching_achieved(db, user.id)
        meets_universal_criteria = has_direct_both_sides and has_first_matching
        
        # Build eligibility reasons if not meeting universal criteria
        eligibility_reasons = []
        if not has_direct_both_sides:
            eligibility_reasons.append("Missing 1:1 active direct referrals on both LEFT and RIGHT positions")
        if not has_first_matching:
            eligibility_reasons.append("Missing first matching achievement (requires 2:1 or 1:2 ratio)")
        
        # Get direct referrals POINTS (not count)
        # Platinum=1.0, Diamond=0.5, Blue/Loyal=0
        direct_points = db.query(func.sum(User.package_points)).filter(
            User.referrer_id == user.id,
            User.coupon_status.in_(['Active', 'Activated'])
        ).scalar() or 0
        
        # Get effective matching count with multiplier
        matching_result = calculate_effective_matching_count(db, user.id)
        effective_matching = matching_result['effective_count']
        left_points = matching_result['left_points']
        right_points = matching_result['right_points']
        
        # Check balanced sides (both legs must have at least some points)
        balanced_sides = left_points > 0 and right_points > 0
        
        # Check Car Allowance eligibility (higher tier)
        # MUST meet universal criteria PLUS specific requirements
        if effective_matching >= 250 and balanced_sides:
            if meets_universal_criteria:
                return {
                    'eligible_type': 'car',
                    'is_eligible': True,
                    'effective_matching_count': effective_matching,
                    'direct_points': float(direct_points),
                    'monthly_amount': 25000,
                    'max_months': 72,
                    'multiplier_details': matching_result,
                    'eligibility_status': 'Eligible',
                    'eligibility_reasons': []
                }
            else:
                return {
                    'eligible_type': 'car',
                    'is_eligible': False,
                    'effective_matching_count': effective_matching,
                    'direct_points': float(direct_points),
                    'monthly_amount': 25000,
                    'max_months': 72,
                    'multiplier_details': matching_result,
                    'eligibility_status': 'Locked - Requirements Not Met',
                    'eligibility_reasons': eligibility_reasons
                }
        
        # Check Standard Field Allowance eligibility (7 POINTS)
        # MUST meet universal criteria PLUS specific requirements
        if direct_points >= 7 and effective_matching >= 20 and balanced_sides:
            if meets_universal_criteria:
                return {
                    'eligible_type': 'standard',
                    'is_eligible': True,
                    'effective_matching_count': effective_matching,
                    'direct_points': float(direct_points),
                    'monthly_amount': 10000,
                    'max_months': 36,
                    'multiplier_details': matching_result,
                    'eligibility_status': 'Eligible',
                    'eligibility_reasons': []
                }
            else:
                return {
                    'eligible_type': 'standard',
                    'is_eligible': False,
                    'effective_matching_count': effective_matching,
                    'direct_points': float(direct_points),
                    'monthly_amount': 10000,
                    'max_months': 36,
                    'multiplier_details': matching_result,
                    'eligibility_status': 'Locked - Requirements Not Met',
                    'eligibility_reasons': eligibility_reasons
                }
        
        # Not eligible - doesn't meet specific criteria
        return {
            'eligible_type': None,
            'is_eligible': False,
            'effective_matching_count': effective_matching,
            'direct_points': float(direct_points),
            'monthly_amount': 0,
            'max_months': 0,
            'multiplier_details': matching_result,
            'eligibility_status': 'Not eligible - criteria not met',
            'eligibility_reasons': eligibility_reasons if not meets_universal_criteria else ['Insufficient direct points or matching count']
        }
        
    except Exception as e:
        logger.error(f"Error checking field allowance eligibility for {user.id}: {e}")
        return {
            'eligible_type': None,
            'effective_matching_count': 0,
            'direct_points': 0,
            'monthly_amount': 0,
            'max_months': 0,
            'multiplier_details': None
        }

def calculate_monthly_field_allowances():
    """
    Monthly job (1st day midnight): Calculate field allowance for previous month
    
    Flow:
    1. Check eligibility using effective matching count (7.5k multiplier)
    2. Verify tenure hasn't expired (36 months for Standard, 72 for Car)
    3. Create PendingIncome with fixed monthly amount (₹10k or ₹25k)
    4. Apply standard deductions and wallet splits
    5. NOT subject to ₹50k ceiling (separate from Ved+Matching)
    """
    db: Session = SessionLocal()
    
    try:
        from app.models.field_allowance import AllowanceSchemeSelector, FieldAllowanceProgress
        
        logger.info("🏆 Starting monthly field allowance calculation...")
        
        # Get first day of current month (payment for previous month)
        today = date.today()
        first_of_month = today.replace(day=1)
        previous_month = first_of_month - timedelta(days=1)
        
        logger.info(f"📅 Calculating field allowances for: {previous_month.strftime('%B %Y')}")
        
        # Get all activated users
        activated_users = db.query(User).filter(
            User.coupon_status.in_(['Activated', 'Active']),
            User.package_points > 0
        ).all()
        
        logger.info(f"Processing {len(activated_users)} activated users for field allowances...")
        
        total_allowances_paid = 0
        total_amount_paid = 0.0
        
        for user in activated_users:
            try:
                # Check eligibility using multiplier logic
                eligibility = check_field_allowance_eligibility(db, user)
                
                if not eligibility['eligible_type']:
                    continue
                
                eligible_type = eligibility['eligible_type']
                monthly_amount = eligibility['monthly_amount']
                max_months = eligibility['max_months']
                
                # Get or create allowance scheme selector
                scheme = db.query(AllowanceSchemeSelector).filter_by(user_id=user.id).first()
                
                if not scheme:
                    # Create new scheme selector
                    scheme = AllowanceSchemeSelector(
                        user_id=user.id,
                        selected_scheme=eligible_type,
                        effective_from_date=first_of_month,
                        qualified_for_standard=(eligible_type == 'standard'),
                        qualified_for_car=(eligible_type == 'car')
                    )
                    db.add(scheme)
                    db.flush()
                
                # Get or create field allowance progress
                progress = db.query(FieldAllowanceProgress).filter_by(
                    user_id=user.id,
                    allowance_type=eligible_type
                ).first()
                
                if not progress:
                    progress = FieldAllowanceProgress(
                        user_id=user.id,
                        allowance_type=eligible_type,
                        amount_paid=0,
                        status='Pending'
                    )
                    db.add(progress)
                    db.flush()
                
                existing_months_paid = db.query(FieldAllowanceProgress).filter_by(
                    user_id=user.id,
                    allowance_type=eligible_type,
                    status='Payout Completed'
                ).count()
                if existing_months_paid >= max_months:
                    logger.info(f"⏰ Tenure expired: {user.id} - {existing_months_paid}/{max_months} months paid")
                    continue
                
                # Calculate deductions and splits
                deductions = calculate_income_deductions_and_splits(monthly_amount, user.package_points)
                
                # Create PendingIncome for field allowance
                income_type = f"Field Allowance - {'Standard' if eligible_type == 'standard' else 'Car'}"
                
                pending_income = PendingIncome(
                    user_id=user.id,
                    income_type=income_type,
                    gross_amount=monthly_amount,
                    admin_deduction=deductions['admin_deduction'],
                    tds_deduction=deductions['tds_deduction'],
                    net_amount=deductions['net_amount'],
                    withdrawal_wallet_amount=deductions['withdrawal_wallet_amount'],
                    upgraded_wallet_amount=deductions['upgraded_wallet_amount'],
                    business_date=previous_month,
                    verification_status='Pending',
                    metadata=f"Month {existing_months_paid + 1} of {max_months} | Effective Matching: {eligibility['effective_matching_count']}",
                    payment_status='PAID',
                )
                db.add(pending_income)
                db.flush()
                # WVV PROTOCOL: Keep as 'Pending' for manual admin approval workflow
                # Do NOT auto-approve - admin must manually review and approve
                logger.info(f"📋 Field Allowance created as PENDING for {user.id} - awaiting admin approval")
                
                progress.status = 'Pending'
                progress.amount_paid = monthly_amount
                progress.month_year = previous_month.strftime('%Y-%m')
                progress.is_eligible = True
                progress.eligibility_checked_at = get_indian_time()
                
                total_allowances_paid += 1
                total_amount_paid += monthly_amount
                
                logger.info(f"💰 Field Allowance: {user.id} - ₹{monthly_amount:,.0f} ({eligible_type}, month {existing_months_paid + 1}/{max_months})")
                
                db.commit()
                
            except Exception as e:
                logger.error(f"Error calculating field allowance for {user.id}: {e}")
                db.rollback()
                continue
        
        logger.info(f"✅ Field allowance calculation complete: {total_allowances_paid} users, ₹{total_amount_paid:,.2f} total")
        
    except Exception as e:
        logger.error(f"Error in monthly field allowance calculation: {e}")
        db.rollback()
    finally:
        db.close()

def calculate_total_leg_points(db: Session, user_id: int, leg: str) -> float:
    """
    Calculate total leg points for a user from UserLegMetrics
    
    Args:
        db: Database session
        user_id: User ID
        leg: 'L' for left leg, 'R' for right leg
    
    Returns:
        float: Total points for the specified leg
    """
    from app.models.user_leg_metrics import UserLegMetrics
    
    metrics = db.query(UserLegMetrics).filter(
        UserLegMetrics.user_id == user_id
    ).first()
    
    if not metrics:
        return 0.0
    
    return metrics.left_points if leg == 'L' else metrics.right_points

def calculate_awards_income(db: Session, business_date: date) -> int:
    """
    Calculate Awards Income (Direct & Matching Award Tiers) - OPTIMIZED WITH BULK SQL
    - Direct Awards: Based on direct referral count (cumulative, one-time per tier)
    - Matching Awards: Based on DECIMAL POINTS (Platinum=1, Diamond=0.5, Blue/Loyal=0)
    - Physical rewards: NO Guru Dakshina (only for cash bonanza rewards)
    
    50x faster with bulk SQL!
    """
    from app.models.awards import UserAwardProgress, UserMatchingAwardProgress
    from app.services.sql_utils import calculate_awards_income_bulk_sql
    
    total_awards_created = 0
    
    try:
        # Use bulk SQL to find NEW awards (50x faster!)
        results = calculate_awards_income_bulk_sql(db)
        
        # 1. Process NEW Direct Awards
        for award in results['new_direct_awards']:
            try:
                # DC PROTOCOL: Check if this is a legacy award
                from app.services.award_processing_service import AwardProcessingService
                award_service = AwardProcessingService(db)
                is_legacy = award_service._check_is_legacy_award(award['user_id'])
                
                # WV Protocol: Set budgeted_amount at achievement (NET amount = final budget)
                # DC PROTOCOL FIX (Nov 11, 2025): Set achievement_date as authoritative field
                # Keep achieved_at for backward compatibility
                now_time = get_indian_time()
                new_progress = UserAwardProgress(
                    user_id=award['user_id'],
                    award_tier_id=award['tier_id'],
                    current_referrals=award['current_referrals'],
                    required_referrals=award['required_referrals'],
                    award_amount=award['award_amount'],
                    budgeted_amount=award['award_amount'],  # WV Protocol: NET amount at achievement
                    status='Achieved',
                    achieved_at=now_time,  # Legacy field (backward compatibility)
                    achievement_date=now_time,  # DC PROTOCOL: Authoritative achievement timestamp
                    is_eligible=True,
                    processed_status='Pending',
                    is_legacy_pre_reset=is_legacy  # DC PROTOCOL: Mark legacy awards
                )
                db.add(new_progress)
                total_awards_created += 1
                logger.info(f"✅ Direct Award (WV): {award['user_id']} achieved {award['award_name']} (Budget: ₹{award['award_amount']})")
            except Exception as e:
                logger.error(f"Error creating direct award for {award['user_id']}: {e}")
                continue
        
        # 2. Process NEW Matching Awards
        for award in results['new_matching_awards']:
            try:
                # DC PROTOCOL: Check if this is a legacy award
                from app.services.award_processing_service import AwardProcessingService
                award_service = AwardProcessingService(db)
                is_legacy = award_service._check_is_legacy_award(award['user_id'])
                
                # WV Protocol: Set budgeted_amount at achievement (NET amount = final budget)
                new_match_progress = UserMatchingAwardProgress(
                    user_id=award['user_id'],
                    matching_award_tier_id=award['tier_id'],
                    current_matches=award['current_matches'],
                    required_matches=award['required_matches'],
                    budgeted_amount=award['award_amount'],  # WV Protocol: NET amount at achievement
                    is_eligible=True,
                    status='Achieved',
                    achievement_date=get_indian_time(),
                    processed_status='Pending',
                    is_legacy_pre_reset=is_legacy  # DC PROTOCOL: Mark legacy awards
                )
                db.add(new_match_progress)
                total_awards_created += 1
                logger.info(f"✅ Matching Award (WV): {award['user_id']} achieved {award['award_name']} (Budget: ₹{award['award_amount']})")
            except Exception as e:
                logger.error(f"Error creating matching award for {award['user_id']}: {e}")
                continue
        
        db.commit()
        logger.info(f"✅ Awards calculation complete: {total_awards_created} new awards created (BULK SQL)")
        return total_awards_created
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error in awards calculation: {e}")
        return 0

def calculate_awards_income_DISABLED(db: Session, business_date: date) -> int:
    """
    DISABLED - Calculate Awards Income (Direct & Matching Award Tiers) - LEGACY SCHEMA
    - Uses existing database schema: award_name, referral_count, actual_price
    - Achievement bonus: One-time payment when tier is first achieved
    """
    total_awards_paid = 0
    
    try:
        # Process Direct Award Tiers (using raw SQL for legacy schema)
        active_users = db.query(User).filter(
            User.coupon_status.in_(['Activated', 'Active']),
            User.package_points > 0
        ).all()
        
        for user in active_users:
            try:
                # Count active direct referrals using package_points
                direct_count = db.query(func.count(User.id)).filter(
                    User.referrer_id == user.id,
                    User.package_points > 0
                ).scalar() or 0
                
                # Get highest eligible direct award tier (legacy schema)
                tier_result = db.execute("""
                    SELECT id, award_name, actual_price, referral_count
                    FROM direct_award_tier
                    WHERE cumulative_required <= :direct_count
                    ORDER BY cumulative_required DESC
                    LIMIT 1
                """, {"direct_count": direct_count}).fetchone()
                
                if tier_result:
                    highest_tier = direct_tiers[0]
                    
                    # Check if user has progress record
                    progress = db.query(UserAwardProgress).filter(
                        UserAwardProgress.user_id == user.id,
                        UserAwardProgress.award_tier_id == highest_tier.id
                    ).first()
                    
                    if not progress:
                        # Create progress and pay achievement bonus
                        progress = UserAwardProgress(
                            user_id=user.id,
                            award_tier_id=highest_tier.id,
                            current_direct_count=direct_count,
                            required_count=highest_tier.required_direct_referrals,
                            achieved=True,
                            achievement_date=get_indian_time()
                        )
                        db.add(progress)
                        
                        # Pay achievement bonus (one-time)
                        if highest_tier.achievement_bonus > 0 and not progress.achievement_bonus_paid:
                            deductions = calculate_income_deductions_and_splits(
                                float(highest_tier.achievement_bonus),
                                user.package_points,
                                apply_guru_dakshina=True
                            )
                            
                            pending_income = PendingIncome(
                                user_id=user.id,
                                income_type='Award Bonus - Direct',
                                gross_amount=float(highest_tier.achievement_bonus),
                                admin_deduction=deductions['admin_deduction'],
                                tds_deduction=deductions['tds_deduction'],
                                net_amount=deductions['net_amount'],
                                withdrawal_wallet_amount=deductions['withdrawal_wallet_amount'],
                                upgraded_wallet_amount=deductions['upgraded_wallet_amount'],
                                business_date=business_date,
                                verification_status='Pending',
                                notes=f"Direct Award Achievement: {highest_tier.tier_name}",
                                payment_status='PAID',
                            )
                            db.add(pending_income)
                            total_awards_paid += 1
                            
                            progress.achievement_bonus_paid = True
                            progress.bonus_payment_date = get_indian_time()
                            progress.bonus_amount_paid = float(highest_tier.achievement_bonus)
                            
                            # Guru Dakshina to referrer
                            if deductions['guru_dakshina_deduction'] > 0 and user.referrer_id:
                                referrer = db.query(User).filter(User.id == user.referrer_id).first()
                                if referrer and referrer.package_points > 0:
                                    gd_deductions = calculate_income_deductions_and_splits(
                                        deductions['guru_dakshina_deduction'],
                                        referrer.package_points,
                                        apply_guru_dakshina=False
                                    )
                                    
                                    gd_income = PendingIncome(
                                        user_id=referrer.id,
                                        income_type='Guru Dakshina',
                                        gross_amount=deductions['guru_dakshina_deduction'],
                                        admin_deduction=gd_deductions['admin_deduction'],
                                        tds_deduction=gd_deductions['tds_deduction'],
                                        net_amount=gd_deductions['net_amount'],
                                        withdrawal_wallet_amount=gd_deductions['withdrawal_wallet_amount'],
                                        upgraded_wallet_amount=gd_deductions['upgraded_wallet_amount'],
                                        business_date=business_date,
                                        verification_status='Pending',
                                        related_user_id=user.id,
                                        payment_status='PAID',
                                    )
                                    db.add(gd_income)
                                    total_awards_paid += 1
                        
                        db.commit()
                
                # Check for Matching Award Tier achievements
                matching_result = calculate_effective_matching_count(db, user.id)
                total_pairs = matching_result['raw_count']
                
                matching_tiers = db.query(MatchingAwardTier).filter(
                    MatchingAwardTier.is_active == True,
                    MatchingAwardTier.required_matching_pairs <= total_pairs
                ).order_by(MatchingAwardTier.tier_level.desc()).all()
                
                if matching_tiers:
                    highest_match_tier = matching_tiers[0]
                    
                    # Check if user has progress record
                    match_progress = db.query(UserMatchingAwardProgress).filter(
                        UserMatchingAwardProgress.user_id == user.id,
                        UserMatchingAwardProgress.matching_award_tier_id == highest_match_tier.id
                    ).first()
                    
                    if not match_progress:
                        # Create progress and pay achievement bonus
                        match_progress = UserMatchingAwardProgress(
                            user_id=user.id,
                            matching_award_tier_id=highest_match_tier.id,
                            current_matching_count=total_pairs,
                            required_matching_count=highest_match_tier.required_matching_pairs,
                            achieved=True,
                            achievement_date=get_indian_time()
                        )
                        db.add(match_progress)
                        
                        # Pay achievement bonus (one-time)
                        if highest_match_tier.achievement_bonus > 0 and not match_progress.achievement_bonus_paid:
                            deductions = calculate_income_deductions_and_splits(
                                float(highest_match_tier.achievement_bonus),
                                user.package_points,
                                apply_guru_dakshina=True
                            )
                            
                            pending_income = PendingIncome(
                                user_id=user.id,
                                income_type='Award Bonus - Matching',
                                gross_amount=float(highest_match_tier.achievement_bonus),
                                admin_deduction=deductions['admin_deduction'],
                                tds_deduction=deductions['tds_deduction'],
                                net_amount=deductions['net_amount'],
                                withdrawal_wallet_amount=deductions['withdrawal_wallet_amount'],
                                upgraded_wallet_amount=deductions['upgraded_wallet_amount'],
                                business_date=business_date,
                                verification_status='Pending',
                                notes=f"Matching Award Achievement: {highest_match_tier.tier_name}",
                                payment_status='PAID',
                            )
                            db.add(pending_income)
                            total_awards_paid += 1
                            
                            match_progress.achievement_bonus_paid = True
                            match_progress.bonus_payment_date = get_indian_time()
                            match_progress.bonus_amount_paid = float(highest_match_tier.achievement_bonus)
                            
                            # Guru Dakshina to referrer
                            if deductions['guru_dakshina_deduction'] > 0 and user.referrer_id:
                                referrer = db.query(User).filter(User.id == user.referrer_id).first()
                                if referrer and referrer.package_points > 0:
                                    gd_deductions = calculate_income_deductions_and_splits(
                                        deductions['guru_dakshina_deduction'],
                                        referrer.package_points,
                                        apply_guru_dakshina=False
                                    )
                                    
                                    gd_income = PendingIncome(
                                        user_id=referrer.id,
                                        income_type='Guru Dakshina',
                                        gross_amount=deductions['guru_dakshina_deduction'],
                                        admin_deduction=gd_deductions['admin_deduction'],
                                        tds_deduction=gd_deductions['tds_deduction'],
                                        net_amount=gd_deductions['net_amount'],
                                        withdrawal_wallet_amount=gd_deductions['withdrawal_wallet_amount'],
                                        upgraded_wallet_amount=gd_deductions['upgraded_wallet_amount'],
                                        business_date=business_date,
                                        verification_status='Pending',
                                        related_user_id=user.id,
                                        payment_status='PAID',
                                    )
                                    db.add(gd_income)
                                    total_awards_paid += 1
                        
                        db.commit()
                        
            except Exception as e:
                logger.error(f"Error calculating awards for {user.id}: {e}")
                db.rollback()
                continue
        
        logger.info(f"✅ Awards calculation complete: {total_awards_paid} awards processed")
        return total_awards_paid
        
    except Exception as e:
        logger.error(f"Error in awards calculation: {e}")
        db.rollback()
        return 0

def calculate_bonanza_income(db: Session, business_date: date) -> int:
    """
    Calculate Bonanza Income for active campaigns - OPTIMIZED WITH BULK SQL + ELIGIBILITY CHECKS
    
    NEW LOGIC (Updated):
    1. ALWAYS CALCULATE achievements (users see what they earned)
    2. Check BOTH eligibility criteria:
       - Must have 1:1 direct active points (at least 1 point on each side from direct referrals)
       - Must have first matching achieved (2:1 or 1:2 ratio from downline)
    3. If NOT eligible: Mark as "Locked - Requirements Not Met"
    4. Once eligible: Process and credit to wallet
    
    CRITICAL: Metric Deduction Logic
    - Any metrics used for bonanza rewards are DEDUCTED from award progress
    - Prevents double benefits (same achievement can't earn both bonanza AND award)
    - Guru Dakshina APPLIES to cash bonanza rewards (2% to referrer)
    
    20x faster with bulk SQL!
    """
    from app.models.user import User  # DC Protocol: BonanzaProgress deprecated
    from app.models.awards import UserAwardProgress, UserMatchingAwardProgress
    from app.models.transaction import PendingIncome
    from app.services.sql_utils import calculate_bonanza_eligible_bulk_sql
    
    total_bonanza_rewards = 0
    total_bonanza_locked = 0
    
    try:
        # Use bulk SQL to get all eligible rewards (20x faster!)
        eligible_rewards = calculate_bonanza_eligible_bulk_sql(db, str(business_date))
        
        if not eligible_rewards:
            logger.info("No bonanza rewards to process")
            return 0
        
        # Process each eligible reward
        for reward_data in eligible_rewards:
            try:
                user_id = reward_data['user_id']
                bonanza_id = reward_data['bonanza_id']
                bonanza_name = reward_data['bonanza_name']
                progress_id = reward_data['progress_id']
                metrics_used = reward_data['current_progress']
                package_points = reward_data['package_points']
                referrer_id = reward_data['referrer_id']
                
                # CHECK ELIGIBILITY CRITERIA (same as Matching/Ved Income)
                has_direct_both_sides = check_direct_referrals_both_sides(db, user_id)
                has_first_matching = check_first_matching_achieved(db, user_id)
                is_eligible = has_direct_both_sides and has_first_matching
                
                # Build eligibility reason if not eligible
                if not is_eligible:
                    eligibility_reasons = []
                    if not has_direct_both_sides:
                        eligibility_reasons.append("Missing 1:1 active direct referrals")
                    if not has_first_matching:
                        eligibility_reasons.append("Missing first matching achievement")
                    eligibility_note = f"Locked - {' | '.join(eligibility_reasons)}"
                    logger.info(f"🔒 Bonanza (NOT ELIGIBLE - held): {user_id} achieved {bonanza_name} but {eligibility_note}")
                    total_bonanza_locked += 1
                else:
                    eligibility_note = None
                    logger.info(f"✅ Bonanza (ELIGIBLE): {user_id} achieved {bonanza_name}")
                
                # Get reward amount from bonanza budget (placeholder for now)
                # In production, this should come from bonanza_reward table
                reward_amount = 10000.00  # This should be dynamic based on bonanza config
                
                # CRITICAL: Apply Metric Deduction Logic
                if reward_data['has_direct_target']:
                    # Deduct from direct award progress
                    direct_awards = db.query(UserAwardProgress).filter(
                        UserAwardProgress.user_id == user_id
                    ).all()
                    
                    for award in direct_awards:
                        # Handle NULL by initializing to 0
                        if award.bonanza_deductions_applied is None:
                            award.bonanza_deductions_applied = 0
                        award.bonanza_deductions_applied += metrics_used
                        award.effective_progress_count = award.current_referrals - award.bonanza_deductions_applied
                    
                    logger.info(f"🎁 Bonanza: Deducted {metrics_used} direct referrals from {user_id}'s award progress")
                
                if reward_data['has_matching_target']:
                    # Deduct from matching award progress
                    matching_awards = db.query(UserMatchingAwardProgress).filter(
                        UserMatchingAwardProgress.user_id == user_id
                    ).all()
                    
                    for award in matching_awards:
                        # Handle NULL by initializing to 0
                        if award.bonanza_deductions_applied is None:
                            award.bonanza_deductions_applied = 0
                        award.bonanza_deductions_applied += metrics_used
                        award.effective_progress_count = award.current_matches - award.bonanza_deductions_applied
                    
                    logger.info(f"🎁 Bonanza: Deducted {metrics_used} matching points from {user_id}'s award progress")
                
                # Calculate with Guru Dakshina (2% to referrer) - BUT only if eligible
                deductions = calculate_income_deductions_and_splits(
                    reward_amount,
                    package_points,
                    apply_guru_dakshina=True  # Bonanza cash rewards have Guru Dakshina
                )
                
                guru_dakshina_amount = deductions.get('guru_dakshina_amount', 0) if is_eligible else 0
                
                # Create PendingIncome for bonanza reward
                # If NOT eligible: verification_status = 'Not Eligible' instead of 'Pending'
                bonanza_notes = f"Bonanza: {bonanza_name}"
                if eligibility_note:
                    bonanza_notes += f" | {eligibility_note}"
                
                bonanza_income = PendingIncome(
                    user_id=user_id,
                    income_type='Bonanza Reward',
                    gross_amount=deductions['gross_after_gd'] if is_eligible else reward_amount,
                    admin_deduction=deductions['admin_deduction'] if is_eligible else 0,
                    tds_deduction=deductions['tds_deduction'] if is_eligible else 0,
                    net_amount=deductions['net_amount'] if is_eligible else 0,
                    withdrawal_wallet_amount=deductions['withdrawal_wallet_amount'] if is_eligible else 0,
                    upgraded_wallet_amount=deductions['upgraded_wallet_amount'] if is_eligible else 0,
                    business_date=business_date,
                    verification_status='Not Eligible' if not is_eligible else 'Pending',
                    related_user_id=bonanza_id,  # Track bonanza campaign
                    notes=bonanza_notes,
                    payment_status='PAID',
                )
                db.add(bonanza_income)
                
                # DC Protocol: Mark bonanza claim as rewarded (use DynamicBonanzaHistory)
                from app.models.bonanza import DynamicBonanzaHistory
                claim = db.query(DynamicBonanzaHistory).filter(
                    DynamicBonanzaHistory.id == progress_id
                ).first()
                
                if claim:
                    claim.delivered_at = get_indian_time()
                    claim.processed_status = 'Delivered - Completed'
                
                total_bonanza_rewards += 1
                
                # Create Guru Dakshina for referrer (if applicable)
                if guru_dakshina_amount > 0 and referrer_id:
                    referrer = db.query(User).filter(User.id == referrer_id).first()
                    if referrer and referrer.package_points > 0:
                        gd_deductions = calculate_income_deductions_and_splits(
                            guru_dakshina_amount,
                            referrer.package_points,
                            apply_guru_dakshina=False
                        )
                        
                        gd_income = PendingIncome(
                            user_id=referrer.id,
                            income_type='Guru Dakshina',
                            gross_amount=guru_dakshina_amount,
                            admin_deduction=gd_deductions['admin_deduction'],
                            tds_deduction=gd_deductions['tds_deduction'],
                            net_amount=gd_deductions['net_amount'],
                            withdrawal_wallet_amount=gd_deductions['withdrawal_wallet_amount'],
                            upgraded_wallet_amount=gd_deductions['upgraded_wallet_amount'],
                            business_date=business_date,
                            verification_status='Pending',
                            related_user_id=user_id,
                            notes=f"2% Royalty received from {user_id}'s Bonanza Reward",
                            payment_status='PAID',
                        )
                        db.add(gd_income)
                
                logger.info(f"🎁 Bonanza reward: {user_id} earned ₹{reward_amount} from {bonanza_name}")
                
            except Exception as e:
                logger.error(f"Error processing bonanza reward for {reward_data.get('user_id')}: {e}")
                db.rollback()
                continue
        
        db.commit()
        logger.info(f"✅ Bonanza calculation complete: {total_bonanza_rewards} rewards processed ({total_bonanza_locked} locked - awaiting eligibility)")
        return total_bonanza_rewards
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error in bonanza calculation: {e}")
        return 0

def calculate_field_allowances(db: Session, business_date: date) -> int:
    """
    Calculate Field Allowances with HIERARCHY logic - OPTIMIZED WITH BULK SQL
    
    HIERARCHY (Only ONE allowance at a time):
    1. Jaguar Car Fund Award (Emerald - 10,000 points) → NO allowances
    2. Car Allowance (250 points in 90 days, 40/month) → DISCONNECTS Field Allowance
    3. Field Allowance (7 directs in 45 days, 20/month) → Only if no Car Allowance
    
    Field Allowance: ₹10,000/month × 18 months
    Car Allowance: ₹25,000/month × 72 months
    
    100x faster with bulk SQL!
    """
    from app.models.field_allowance import FieldAllowanceEligibility, CarAllowanceEligibility
    from app.services.sql_utils import sync_field_allowance_status_bulk_sql
    
    total_status_updates = 0
    
    try:
        # Use bulk SQL to check eligibility for ALL users (100x faster!)
        results = sync_field_allowance_status_bulk_sql(db)
        
        # 1. Process Jaguar users - DISCONNECT all allowances
        for user_data in results['jaguar_users']:
            user_id = user_data['user_id']
            try:
                db.query(FieldAllowanceEligibility).filter(
                    FieldAllowanceEligibility.user_id == user_id
                ).update({'overall_status': 'Disconnected - Jaguar Award'})
                
                db.query(CarAllowanceEligibility).filter(
                    CarAllowanceEligibility.user_id == user_id
                ).update({'overall_status': 'Disconnected - Jaguar Award'})
                
                logger.info(f"🚗 {user_id} has Jaguar Car Fund - all allowances disconnected")
                total_status_updates += 1
            except Exception as e:
                logger.error(f"Error disconnecting allowances for Jaguar user {user_id}: {e}")
                continue
        
        # 2. Process Car Allowance eligible users
        for user_data in results['car_eligible']:
            user_id = user_data['user_id']
            try:
                # Disconnect Field Allowance
                db.query(FieldAllowanceEligibility).filter(
                    FieldAllowanceEligibility.user_id == user_id
                ).update({'overall_status': 'Disconnected - Car Allowance Active'})
                
                # Create or update Car Allowance
                car_allowance = db.query(CarAllowanceEligibility).filter(
                    CarAllowanceEligibility.user_id == user_id
                ).first()
                
                if not car_allowance:
                    car_allowance = CarAllowanceEligibility(
                        user_id=user_id,
                        scheme_name='Car Allowance',
                        monthly_amount=25000.00,
                        tenure_months=72,
                        total_value=1800000.00,
                        matching_referrals_count=user_data['total_points'],
                        matching_referrals_target=250,
                        initial_eligibility_met=True,
                        initial_eligibility_date=get_indian_time(),
                        overall_status='Active',
                        month_year=business_date.strftime('%Y-%m')
                    )
                    db.add(car_allowance)
                    logger.info(f"🚗 {user_id} qualified for Car Allowance (₹25K/month × 72 months)")
                    total_status_updates += 1
            except Exception as e:
                logger.error(f"Error setting car allowance for {user_id}: {e}")
                continue
        
        # 3. Process Field Allowance eligible users
        for user_data in results['field_eligible']:
            user_id = user_data['user_id']
            try:
                # Create or update Field Allowance
                field_allowance = db.query(FieldAllowanceEligibility).filter(
                    FieldAllowanceEligibility.user_id == user_id
                ).first()
                
                if not field_allowance:
                    field_allowance = FieldAllowanceEligibility(
                        user_id=user_id,
                        scheme_name='Standard',
                        monthly_amount=10000.00,
                        tenure_months=18,
                        total_value=180000.00,
                        eligibility_requirement='7 Direct Referrals in 45 days',
                        monthly_requirement='20 Active Matches per month',
                        direct_referrals_count=int(user_data['direct_points']),
                        direct_referrals_target=7,
                        initial_eligibility_met=True,
                        initial_eligibility_date=get_indian_time(),
                        overall_status='Active',
                        month_year=business_date.strftime('%Y-%m')
                    )
                    db.add(field_allowance)
                    logger.info(f"📋 {user_id} qualified for Field Allowance (₹10K/month × 18 months)")
                    total_status_updates += 1
            except Exception as e:
                logger.error(f"Error setting field allowance for {user_id}: {e}")
                continue
        
        db.commit()
        logger.info(f"✅ Field Allowances status sync complete: {total_status_updates} updates (BULK SQL)")
        return total_status_updates
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error in field allowances calculation: {e}")
        return 0

def calculate_bonanza_income_DISABLED(db: Session, business_date: date) -> int:
    """
    DISABLED - Calculate Bonanza Income for active campaigns
    - Checks active bonanza campaigns
    - Evaluates user achievements against reward criteria
    - Creates PendingIncome for qualifying users
    """
    from app.models.bonanza import DynamicBonanza, DynamicBonanzaReward, DynamicBonanzaHistory  # DC Protocol: BonanzaProgress deprecated
    
    total_bonanza_rewards = 0
    
    try:
        # Get active bonanza campaigns
        active_bonanzas = db.query(DynamicBonanza).filter(
            DynamicBonanza.status == 'active',
            DynamicBonanza.start_date <= get_indian_time(),
            DynamicBonanza.end_date >= get_indian_time()
        ).all()
        
        if not active_bonanzas:
            logger.info("No active bonanza campaigns")
            return 0
        
        for bonanza in active_bonanzas:
            try:
                # Get reward criteria for this bonanza
                rewards = db.query(DynamicBonanzaReward).filter(
                    DynamicBonanzaReward.bonanza_id == bonanza.id,
                    DynamicBonanzaReward.is_active == True
                ).all()
                
                # DC Protocol: Get all approved bonanza claims (use DynamicBonanzaHistory)
                from app.models.bonanza import DynamicBonanzaHistory
                progresses = db.query(DynamicBonanzaHistory).filter(
                    DynamicBonanzaHistory.bonanza_id == bonanza.id,
                    DynamicBonanzaHistory.processed_status.in_(['Admin Approved', 'Procurement Pending', 'Processed for Dispatch'])
                ).all()
                
                for progress in progresses:
                    try:
                        user = db.query(User).filter(User.id == progress.user_id).first()
                        if not user or user.package_points == 0:
                            continue
                        
                        # Find matching reward criteria
                        for reward in rewards:
                            eligible = False
                            
                            if reward.criteria_type == 'points_threshold':
                                if reward.criteria_operator == '>=':
                                    eligible = progress.current_points >= float(reward.criteria_value)
                                elif reward.criteria_operator == '>':
                                    eligible = progress.current_points > float(reward.criteria_value)
                                elif reward.criteria_operator == '=':
                                    eligible = progress.current_points == float(reward.criteria_value)
                            
                            if eligible and reward.reward_type == 'cash':
                                # Pay bonanza reward
                                deductions = calculate_income_deductions_and_splits(
                                    float(reward.reward_amount),
                                    user.package_points,
                                    apply_guru_dakshina=True
                                )
                                
                                pending_income = PendingIncome(
                                    user_id=user.id,
                                    income_type='Bonanza Reward',
                                    gross_amount=float(reward.reward_amount),
                                    admin_deduction=deductions['admin_deduction'],
                                    tds_deduction=deductions['tds_deduction'],
                                    net_amount=deductions['net_amount'],
                                    withdrawal_wallet_amount=deductions['withdrawal_wallet_amount'],
                                    upgraded_wallet_amount=deductions['upgraded_wallet_amount'],
                                    business_date=business_date,
                                    verification_status='Pending',
                                    notes=f"Bonanza: {bonanza.campaign_name} - {reward.reward_name}",
                                    payment_status='PAID',
                                )
                                db.add(pending_income)
                                db.flush()
                                # WVV PROTOCOL: Keep as 'Pending' for manual admin approval
                                logger.info(f"📋 Bonanza reward created as PENDING for {user.id} - awaiting admin approval")
                                total_bonanza_rewards += 1
                                
                                # Mark as claimed
                                progress.reward_claimed = True
                                progress.reward_amount = float(reward.reward_amount)
                                
                                # Create history record
                                history = DynamicBonanzaHistory(
                                    user_id=user.id,
                                    bonanza_id=bonanza.id,
                                    claimed_reward_id=reward.id,
                                    reward_value_claimed=float(reward.reward_amount)
                                )
                                db.add(history)
                                
                                # Guru Dakshina to referrer
                                if deductions['guru_dakshina_deduction'] > 0 and user.referrer_id:
                                    referrer = db.query(User).filter(User.id == user.referrer_id).first()
                                    if referrer and referrer.package_points > 0:
                                        gd_deductions = calculate_income_deductions_and_splits(
                                            deductions['guru_dakshina_deduction'],
                                            referrer.package_points,
                                            apply_guru_dakshina=False
                                        )
                                        
                                        gd_income = PendingIncome(
                                            user_id=referrer.id,
                                            income_type='Guru Dakshina',
                                            gross_amount=deductions['guru_dakshina_deduction'],
                                            admin_deduction=gd_deductions['admin_deduction'],
                                            tds_deduction=gd_deductions['tds_deduction'],
                                            net_amount=gd_deductions['net_amount'],
                                            withdrawal_wallet_amount=gd_deductions['withdrawal_wallet_amount'],
                                            upgraded_wallet_amount=gd_deductions['upgraded_wallet_amount'],
                                            business_date=business_date,
                                            verification_status='Pending',
                                            related_user_id=user.id,
                                            payment_status='PAID',
                                        )
                                        db.add(gd_income)
                                        total_bonanza_rewards += 1
                                
                                db.commit()
                                break  # One reward per user per bonanza
                    
                    except Exception as e:
                        logger.error(f"Error processing bonanza progress for {progress.user_id}: {e}")
                        db.rollback()
                        continue
            
            except Exception as e:
                logger.error(f"Error processing bonanza {bonanza.id}: {e}")
                db.rollback()
                continue
        
        logger.info(f"✅ Bonanza calculation complete: {total_bonanza_rewards} rewards processed")
        return total_bonanza_rewards
        
    except Exception as e:
        logger.error(f"Error in bonanza calculation: {e}")
        db.rollback()
        return 0

def calculate_incomes_for_date_manual(target_date: date, triggered_by: str = "SYSTEM") -> Dict:
    """
    MANUAL income calculation for specific date (WV PROTOCOL)
    
    WV PROTOCOL: ALL deductions (12%) applied at income calculation stage ONLY
    DC PROTOCOL: Database is the single source of truth for all financial data
    
    Args:
        target_date: Date to calculate incomes for (activation date = target_date)
        triggered_by: User ID who triggered (for audit trail)
    
    Returns:
        Dict with calculation results
    """
    # Delegate to main function with custom date
    return _calculate_incomes_with_date(target_date=target_date, is_manual=True, triggered_by=triggered_by)

def calculate_previous_day_incomes():
    """
    Midnight job: Calculate incomes for yesterday (automatic)
    DC Protocol Fix: Use IST date (not UTC date.today()) since scheduler fires at midnight IST
    
    SELF-HEALING: Before processing yesterday, checks for any missed dates
    in the last 7 days where the scheduler failed or created 0 incomes despite
    having activated users. Automatically backfills those dates first.
    Duplicate protection in _calculate_incomes_with_date ensures safe re-runs.
    """
    import pytz
    ist = pytz.timezone('Asia/Kolkata')
    today_ist = datetime.now(ist).date()
    yesterday = today_ist - timedelta(days=1)
    
    _recover_missed_dates(today_ist, yesterday)
    
    return _calculate_incomes_with_date(target_date=yesterday, is_manual=False, triggered_by="SCHEDULER")


def _recover_missed_dates(today_ist: date, yesterday: date):
    """
    Self-healing: Detect and recover missed income calculation dates.
    
    Checks the last 7 days for dates where:
    1. Scheduler log shows Failed status, OR
    2. Scheduler log shows 0 incomes but there were activations that day, OR
    3. No scheduler log exists at all for that date
    
    Safe to re-run because _calculate_incomes_with_date has duplicate protection
    (check_duplicate_income) for every income type.
    """
    db = SessionLocal()
    try:
        lookback_days = 7
        start_date = today_ist - timedelta(days=lookback_days)
        
        missed_dates = []
        
        for day_offset in range(lookback_days):
            check_date = start_date + timedelta(days=day_offset)
            if check_date >= yesterday:
                break
            
            from app.models.system_log import SchedulerLog
            logs = db.query(SchedulerLog).filter(
                SchedulerLog.job_id.in_([
                    'midnight_income_calculation', 
                    'manual_income_calculation',
                    'self_healing_income_calculation'
                ]),
                func.date(SchedulerLog.scheduled_date) == check_date
            ).all()
            
            has_successful_run = False
            for log in logs:
                if log.overall_status in ('Completed', 'Completed with Errors'):
                    has_successful_run = True
                    break
            
            if has_successful_run:
                continue
            
            eligible_activations = db.query(func.count(User.id)).filter(
                func.date(User.activation_date) == check_date,
                User.package_points >= 0.5
            ).scalar() or 0
            
            if eligible_activations > 0:
                missed_dates.append(check_date)
                logger.warning(f"🔄 SELF-HEALING: Detected missed date {check_date} "
                             f"({eligible_activations} eligible activations, no completed income run)")
        
        if missed_dates:
            logger.warning(f"🔄 SELF-HEALING: Recovering {len(missed_dates)} missed dates: {missed_dates}")
            for missed_date in sorted(missed_dates):
                try:
                    logger.warning(f"🔄 SELF-HEALING: Processing missed date {missed_date}...")
                    _calculate_incomes_with_date(
                        target_date=missed_date, 
                        is_manual=False, 
                        triggered_by="SELF-HEALING"
                    )
                    logger.warning(f"✅ SELF-HEALING: Successfully recovered {missed_date}")
                except Exception as e:
                    logger.error(f"❌ SELF-HEALING: Failed to recover {missed_date}: {e}")
        else:
            logger.info("✅ SELF-HEALING: No missed dates found in last 7 days")
            
    except Exception as e:
        logger.error(f"❌ SELF-HEALING check failed (non-blocking): {e}")
    finally:
        db.close()

def _calculate_incomes_with_date(target_date: date, is_manual: bool = False, triggered_by: str = "SCHEDULER"):
    """
    Core income calculation logic (WV + DC PROTOCOL)
    
    WV PROTOCOL: ALL deductions (12%) applied at income calculation stage ONLY
    DC PROTOCOL: Database is the single source of truth for all financial data
    
    Flow:
    1. Calculate Matching, Ved, Direct Referral for all users
    2. Calculate Awards and Bonanza income
    3. Aggregate by RECIPIENT and apply ₹50k ceiling PER RECIPIENT
    4. Calculate Guru Dakshina (after other incomes)
    5. Apply deductions and wallet splits
    6. Create CompanyEarnings for ceiling excess
    
    Args:
        target_date: Date to calculate incomes for (activation_date = target_date)
        is_manual: True if manually triggered, False if automatic scheduler
        triggered_by: User ID or "SCHEDULER" for audit trail
    """
    from app.models.system_log import SchedulerLog
    
    db: Session = SessionLocal()
    scheduled_date = get_indian_time().replace(hour=0, minute=0, second=0, microsecond=0)
    
    # Create scheduler log with appropriate job_id
    if triggered_by == "SELF-HEALING":
        job_id = 'self_healing_income_calculation'
        job_name = f'Self-Healing Recovery (Auto-Backfill for {target_date})'
    elif is_manual:
        job_id = 'manual_income_calculation'
        job_name = f'Manual Income Calculation (By: {triggered_by})'
    else:
        job_id = 'midnight_income_calculation'
        job_name = 'Income Calculation'
    
    scheduler_log = SchedulerLog(
        job_id=job_id,
        job_name=job_name,
        scheduled_date=scheduled_date,
        triggered_at=get_indian_time(),
        income_triggered="Yes",
        overall_status="Running"
    )
    db.add(scheduler_log)
    db.commit()
    
    total_incomes = 0
    users_set = set()
    
    try:
        prefix = "🔧 MANUAL" if is_manual else "🕛 AUTO"
        logger.warning(f"{prefix} Income calculation for {target_date} (Log ID: {scheduler_log.id})")
        
        # Use the provided target_date (not yesterday)
        previous_day = target_date
        logger.warning(f"📅 Calculating incomes for: {previous_day}")
        
        # Get all activated users
        activated_users = db.query(User).filter(
            User.coupon_status.in_(['Activated', 'Active']),
            User.package_points > 0
        ).all()
        
        logger.info(f"Processing {len(activated_users)} activated users...")
        
        recipient_incomes = {}
        errors_in_calculation = []
        phase2_errors = []
        
        # PHASE 1: Calculate Matching & Direct Referral Income FIRST (to update first_matching_achieved flag)
        for user in activated_users:
            try:
                # 1. Calculate Matching Referral Income (ALWAYS calculate, mark eligibility)
                matching_result = calculate_matching_referral_income(db, user, previous_day)
                matching_income = matching_result['gross_income']
                pairs_matched = matching_result['pairs_matched']
                left_consumed = matching_result['left_consumed']
                right_consumed = matching_result['right_consumed']
                match_type = matching_result['match_type']
                is_eligible = matching_result.get('is_eligible', False)  # NEW: eligibility flag
                
                exempted_data = matching_result.get('exempted')
                
                if matching_income > 0 or exempted_data:
                    if user.id not in recipient_incomes:
                        recipient_incomes[user.id] = {'matching': None, 'ved': [], 'direct_referral': [], 'informational_matching': False}
                    if matching_income > 0:
                        recipient_incomes[user.id]['matching'] = {
                            'income': matching_income,
                            'pairs': pairs_matched,
                            'left_consumed': left_consumed,
                            'right_consumed': right_consumed,
                            'match_type': match_type,
                            'is_eligible': is_eligible
                        }
                    if exempted_data:
                        recipient_incomes[user.id]['exempted_matching'] = exempted_data
                elif matching_income == 0 and pairs_matched == 0 and not exempted_data:
                    from app.services.sql_utils import get_leg_member_counts_sql
                    leg_counts = get_leg_member_counts_sql(db, user.id)
                    has_team = (leg_counts['left_total'] > 0 or leg_counts['right_total'] > 0)
                    has_only_zero_point = has_team and leg_counts['left_active'] == 0 and leg_counts['right_active'] == 0
                    if has_only_zero_point:
                        if user.id not in recipient_incomes:
                            recipient_incomes[user.id] = {'matching': None, 'ved': [], 'direct_referral': [], 'informational_matching': False}
                        recipient_incomes[user.id]['informational_matching'] = True
                        recipient_incomes[user.id]['informational_leg_counts'] = leg_counts
                
                # 2. Calculate Direct Referral Income (income goes to REFERRER)
                referral_bonus_amount, referral_referrer_id = calculate_direct_referral_income(db, user, previous_day)
                
                if referral_bonus_amount > 0 and referral_referrer_id:
                    if referral_referrer_id not in recipient_incomes:
                        recipient_incomes[referral_referrer_id] = {'matching': None, 'ved': [], 'direct_referral': []}
                    if 'direct_referral' not in recipient_incomes[referral_referrer_id]:
                        recipient_incomes[referral_referrer_id]['direct_referral'] = []
                    recipient_incomes[referral_referrer_id]['direct_referral'].append({
                        'amount': referral_bonus_amount,
                        'referred_user_id': user.id
                    })
                    
            except Exception as e:
                import traceback
                error_tb = traceback.format_exc()
                logger.warning(f"⚠️ MATCHING_CALC_ERROR for {user.id}: {e}\n{error_tb}")
                errors_in_calculation.append({"user_id": user.id, "error": str(e)})
                continue
        
        if errors_in_calculation:
            logger.warning(f"⚠️ PHASE 1 ERRORS: {len(errors_in_calculation)}/{len(activated_users)} users failed matching calculation")
            for err in errors_in_calculation[:10]:
                logger.warning(f"  - {err['user_id']}: {err['error']}")
        else:
            logger.info(f"✅ Phase 1 complete: {len(recipient_incomes)} users with incomes, 0 errors")
        
        # PHASE 1B: Calculate Awards, Bonanza, and Field Allowances
        logger.info("📊 Calculating Awards, Bonanza, and Field Allowances...")
        awards_count = calculate_awards_income(db, previous_day)
        bonanza_count = calculate_bonanza_income(db, previous_day)
        allowances_count = calculate_field_allowances(db, previous_day)
        logger.info(f"✅ Phase 1B complete: {awards_count} awards, {bonanza_count} bonanza, {allowances_count} allowances")
        
        # PHASE 1C: Calculate Ved Income AFTER matching incomes are processed (so first_matching_achieved flags are current)
        # NOTE: This happens BEFORE creating PendingIncome records, but uses current eligibility status
        logger.info("💰 Calculating Ved Income (after matching eligibility updated)...")
        from app.services.sql_utils import calculate_ved_income_bulk_sql
        ved_incomes_bulk = calculate_ved_income_bulk_sql(db, str(previous_day))
        
        # Apply Ved Income prerequisites and add to recipient_incomes (one record per activated user)
        ved_eligible_count = 0
        for ved_data in ved_incomes_bulk:
            ved_owner_id = ved_data['ved_owner_id']  # SQL returns correct ved_owner_id from database
            ved_member_id = ved_data['ved_member_id']
            activated_user_id = ved_data['activated_user_id']
            ved_amount = ved_data['ved_income_amount']
            
            # Check prerequisites for Ved owner (using CURRENT matching status from recipient_incomes)
            if not check_direct_referrals_both_sides(db, ved_owner_id):
                logger.debug(f"Ved Income skipped: {ved_owner_id} missing 1:1 active direct referrals")
                continue
            
            # Check if Ved owner has eligible matching income (which means they achieved first matching)
            has_eligible_matching = False
            if ved_owner_id in recipient_incomes and recipient_incomes[ved_owner_id].get('matching'):
                has_eligible_matching = recipient_incomes[ved_owner_id]['matching'].get('is_eligible', False)
            
            if not has_eligible_matching:
                logger.debug(f"Ved Income skipped: {ved_owner_id} hasn't achieved first matching (no eligible matching income)")
                continue
            
            # Add to recipient incomes with activated_user_id for proper one-time tracking
            if ved_owner_id not in recipient_incomes:
                recipient_incomes[ved_owner_id] = {'matching': None, 'ved': [], 'direct_referral': []}
            if 'ved' not in recipient_incomes[ved_owner_id]:
                recipient_incomes[ved_owner_id]['ved'] = []
            recipient_incomes[ved_owner_id]['ved'].append({
                'amount': ved_amount,
                'ved_member_id': ved_member_id,
                'activated_user_id': activated_user_id  # Track activated user for one-time protection
            })
            ved_eligible_count += 1
        
        logger.info(f"✅ Ved Income calculated: {len(ved_incomes_bulk)} total, {ved_eligible_count} eligible after prerequisites")
        
        # PHASE 2: Apply ceiling PER RECIPIENT and create PendingIncome
        total_incomes_created = 0
        total_company_earnings = 0.0
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
                    matching_is_eligible = matching_data.get('is_eligible', False)  # NEW: get eligibility flag
                else:
                    matching_amount = 0
                    pairs_matched = 0
                    left_consumed = 0
                    right_consumed = 0
                    match_type = None
                    matching_is_eligible = False
                
                ved_incomes_list = incomes.get('ved', [])
                ved_amount = sum(v['amount'] for v in ved_incomes_list)
                
                # Apply ceiling to Ved+Matching GROSS for this RECIPIENT
                total_ved_matching = matching_amount + ved_amount
                
                if total_ved_matching > ceiling_limit:
                    excess_amount = total_ved_matching - ceiling_limit
                    total_company_earnings += excess_amount
                    
                    # Pro-rate incomes to fit ceiling
                    if matching_amount > 0:
                        matching_amount = (matching_amount / total_ved_matching) * ceiling_limit
                    if ved_amount > 0:
                        ved_amount = (ved_amount / total_ved_matching) * ceiling_limit
                    
                    # Create CompanyEarnings record
                    company_earning = CompanyEarnings(
                        user_id=recipient_id,
                        original_amount=total_ved_matching,
                        excess_amount=excess_amount,
                        paid_amount=excess_amount * float(NET_PAYOUT_RATE),
                        admin_deduction=excess_amount * float(ADMIN_DEDUCTION_RATE),
                        tds_deduction=excess_amount * float(TDS_DEDUCTION_RATE),
                        net_company_earnings=excess_amount * float(NET_PAYOUT_RATE),
                        ceiling_date=previous_day,  # Updated from business_date to match DB schema
                        income_type='Ved+Matching Ceiling Excess',
                        daily_total_before=total_ved_matching,  # Total before ceiling was applied
                        daily_ceiling_limit=ceiling_limit,  # Updated from ceiling_limit_applied
                        description=f'Ceiling excess for {previous_day}: Ved+Matching total ₹{total_ved_matching:.2f} exceeded ₹{ceiling_limit:.2f} limit'
                    )
                    db.add(company_earning)
                    logger.info(f"💰 Company Earnings: {recipient_id} - ₹{excess_amount:.2f} excess")
                
                # Create Matching Referral PendingIncome
                if matching_amount > 0:
                    # DC PROTOCOL: Check for duplicates before creating
                    from app.services.sql_utils import build_matching_contributor_snapshot, identify_consumed_members_sql
                    consumed_members = identify_consumed_members_sql(
                        db, recipient_id, left_consumed, right_consumed
                    )
                    actual_business_date = _get_actual_business_date(consumed_members, previous_day)
                    if actual_business_date != previous_day:
                        logger.info(f"📅 Business date adjusted for {recipient_id}: {previous_day} → {actual_business_date} (contributor activated later)")
                    
                    if check_duplicate_income(db, recipient_id, 'Matching Referral', actual_business_date):
                        logger.warning(f"⚠️ Skipping duplicate Matching Referral for {recipient_id} on {actual_business_date}")
                    else:
                        deductions = calculate_income_deductions_and_splits(matching_amount, recipient.package_points, apply_guru_dakshina=True)
                        guru_dakshina_amount = deductions['guru_dakshina_deduction']
                        
                        admin_deduction_full = matching_amount * (INCOME_RATES['admin_charge_rate'] / 100)
                        tds_deduction_full = matching_amount * (INCOME_RATES['tds_rate'] / 100)
                        net_after_all_deductions = matching_amount - guru_dakshina_amount - admin_deduction_full - tds_deduction_full
                        
                        split = get_earnings_split(recipient.package_points, getattr(recipient, 'upgrade_wallet_balance', None))
                        withdrawal_amount = net_after_all_deductions * (split['withdrawable'] / 100)
                        upgrade_amount = net_after_all_deductions * (split['upgraded_wallet'] / 100)
                        
                        contributor_snapshot = build_matching_contributor_snapshot(
                            db, recipient_id, pairs_matched, left_consumed, right_consumed,
                            match_type, business_date=actual_business_date,
                            consumed_members=consumed_members
                        )
                        
                        pending_income = PendingIncome(
                            user_id=recipient_id,
                            income_type='Matching Referral',
                            gross_amount=matching_amount,
                            admin_deduction=admin_deduction_full,
                            tds_deduction=tds_deduction_full,
                            net_amount=net_after_all_deductions,
                            withdrawal_wallet_amount=withdrawal_amount,
                            upgraded_wallet_amount=upgrade_amount,
                            pairs_matched=pairs_matched,
                            left_points_consumed=left_consumed,
                            right_points_consumed=right_consumed,
                            match_type=match_type,
                            matching_contributors_snapshot=contributor_snapshot,
                            business_date=actual_business_date,
                            verification_status='Pending',
                            payment_status='PAID',
                        )
                        db.add(pending_income)
                        db.flush()  # Get pending_income.id
                        
                        # WVV PROTOCOL: Do NOT auto-approve - keep as Pending for admin review
                        logger.info(f"📋 Matching income created as PENDING for {recipient_id} - awaiting admin approval")
                        
                        # Update first_matching_achieved flag if eligible
                        if matching_is_eligible and not recipient.first_matching_achieved:
                            recipient.first_matching_achieved = True
                            logger.info(f"🎯 First matching achieved for {recipient_id}")
                        
                        total_incomes_created += 1
                        
                        # Create Guru Dakshina income for referrer (if user has referrer)
                        if guru_dakshina_amount > 0 and recipient.referrer_id:
                            referrer = db.query(User).filter(User.id == recipient.referrer_id).first()
                            if referrer and referrer.package_points > 0:
                                if check_duplicate_income(db, referrer.id, 'Guru Dakshina', actual_business_date):
                                    logger.warning(f"⚠️ Skipping duplicate Guru Dakshina for {referrer.id} on {actual_business_date}")
                                else:
                                    gd_deductions = calculate_income_deductions_and_splits(guru_dakshina_amount, referrer.package_points, apply_guru_dakshina=False, upgrade_wallet_balance=getattr(referrer, 'upgrade_wallet_balance', None))
                                    
                                    guru_dakshina_income = PendingIncome(
                                        user_id=referrer.id,
                                        income_type='Guru Dakshina',
                                        gross_amount=guru_dakshina_amount,
                                        admin_deduction=gd_deductions['admin_deduction'],
                                        tds_deduction=gd_deductions['tds_deduction'],
                                        net_amount=gd_deductions['net_amount'],
                                        withdrawal_wallet_amount=gd_deductions['withdrawal_wallet_amount'],
                                        upgraded_wallet_amount=gd_deductions['upgraded_wallet_amount'],
                                        business_date=actual_business_date,
                                        verification_status='Pending',
                                        related_user_id=recipient_id,
                                        notes=f"2% Royalty received from {recipient_id}",
                                        payment_status='PAID',
                                    )
                                    db.add(guru_dakshina_income)
                                    db.flush()
                                    # WVV PROTOCOL: Keep as 'Pending' for manual admin approval
                                    logger.info(f"📋 Guru Dakshina created as PENDING for {referrer.id} - awaiting admin approval")
                                    total_incomes_created += 1
                
                exempted_matching_data = incomes.get('exempted_matching')
                if exempted_matching_data:
                    exempt_pairs = exempted_matching_data['pairs']
                    exempt_left_pts = exempted_matching_data['left_points_consumed']
                    exempt_right_pts = exempted_matching_data['right_points_consumed']
                    exempt_left_zero = exempted_matching_data['left_zero_consumed']
                    exempt_right_zero = exempted_matching_data['right_zero_consumed']
                    
                    from app.services.sql_utils import build_exempted_matching_snapshot, identify_exempted_members_sql
                    exempted_consumed = identify_exempted_members_sql(
                        db, recipient_id, exempt_left_zero, exempt_right_zero
                    )
                    exempt_actual_date = _get_actual_business_date(exempted_consumed, previous_day)
                    if exempt_actual_date != previous_day:
                        logger.info(f"📅 Exempted business date adjusted for {recipient_id}: {previous_day} → {exempt_actual_date} (zero-point member activated later)")
                    
                    exempt_snapshot = build_exempted_matching_snapshot(
                        db, recipient_id, exempt_pairs,
                        exempt_left_pts, exempt_right_pts,
                        exempt_left_zero, exempt_right_zero,
                        business_date=exempt_actual_date,
                        consumed_members=exempted_consumed
                    )
                    
                    exempt_notes_parts = []
                    if exempt_right_zero > 0:
                        exempt_notes_parts.append(f"{exempt_right_zero} right zero-point member(s) exempted")
                    if exempt_left_zero > 0:
                        exempt_notes_parts.append(f"{exempt_left_zero} left zero-point member(s) exempted")
                    exempt_notes = f"Exempted: {', '.join(exempt_notes_parts)} — ₹0 income (Star/Loyal/Welcome matched)"
                    
                    exempted_income = PendingIncome(
                        user_id=recipient_id,
                        income_type='Matching Referral',
                        gross_amount=0.0,
                        admin_deduction=0.0,
                        tds_deduction=0.0,
                        net_amount=0.0,
                        withdrawal_wallet_amount=0.0,
                        upgraded_wallet_amount=0.0,
                        pairs_matched=exempt_pairs,
                        left_points_consumed=exempt_left_pts,
                        right_points_consumed=exempt_right_pts,
                        match_type='exempted_matching',
                        matching_contributors_snapshot=exempt_snapshot,
                        business_date=exempt_actual_date,
                        verification_status='Exempted',
                        payment_status='N/A',
                        notes=exempt_notes,
                    )
                    db.add(exempted_income)
                    db.flush()
                    logger.info(f"🔓 Exempted matching record created for {recipient_id}: {exempt_notes}")
                    total_incomes_created += 1
                
                if not matching_data and not exempted_matching_data and incomes.get('informational_matching'):
                    if not check_duplicate_income(db, recipient_id, 'Matching Referral', previous_day):
                        leg_counts = incomes.get('informational_leg_counts', {})
                        info_notes = f"Informational: {leg_counts.get('left_total', 0)} left / {leg_counts.get('right_total', 0)} right team members (all 0-point)"
                        informational_income = PendingIncome(
                            user_id=recipient_id,
                            income_type='Matching Referral',
                            gross_amount=0.0,
                            admin_deduction=0.0,
                            tds_deduction=0.0,
                            net_amount=0.0,
                            withdrawal_wallet_amount=0.0,
                            upgraded_wallet_amount=0.0,
                            pairs_matched=0,
                            left_points_consumed=0.0,
                            right_points_consumed=0.0,
                            match_type='informational',
                            business_date=previous_day,
                            verification_status='Informational',
                            payment_status='N/A',
                            notes=info_notes,
                        )
                        db.add(informational_income)
                        db.flush()
                        logger.info(f"ℹ️ Informational matching record created for {recipient_id}: {info_notes}")
                        total_incomes_created += 1
                
                # Create Ved Income PendingIncome records (one per activated user for proper tracking)
                for ved_data in ved_incomes_list:
                    ved_amount_single = ved_data['amount']
                    ved_member_id = ved_data['ved_member_id']
                    activated_user_id = ved_data['activated_user_id']  # NEW: Individual activated user
                    
                    # DC PROTOCOL: Check for duplicates before creating (include activated_user_id for uniqueness)
                    if check_duplicate_income(db, recipient_id, 'Ved Income', previous_day, related_user_id=activated_user_id):
                        logger.warning(f"⚠️ Skipping duplicate Ved Income for {recipient_id} on {previous_day} for activated user {activated_user_id}")
                        continue
                    
                    # Calculate with Guru Dakshina deduction (2% goes to referrer)
                    deductions = calculate_income_deductions_and_splits(ved_amount_single, recipient.package_points, apply_guru_dakshina=True)
                    guru_dakshina_amount = deductions['guru_dakshina_deduction']
                    
                    # Store ORIGINAL ved_amount as gross (FULL amount without any deductions)
                    # Apply ALL deductions when calculating net (admin + tds + guru_dakshina)
                    admin_deduction_full = ved_amount_single * (INCOME_RATES['admin_charge_rate'] / 100)
                    tds_deduction_full = ved_amount_single * (INCOME_RATES['tds_rate'] / 100)
                    net_after_all_deductions = ved_amount_single - guru_dakshina_amount - admin_deduction_full - tds_deduction_full
                    
                    split = get_earnings_split(recipient.package_points, getattr(recipient, 'upgrade_wallet_balance', None))
                    withdrawal_amount = net_after_all_deductions * (split['withdrawable'] / 100)
                    upgrade_amount = net_after_all_deductions * (split['upgraded_wallet'] / 100)
                    
                    pending_income = PendingIncome(
                        user_id=recipient_id,
                        income_type='Ved Income',
                        gross_amount=ved_amount_single,  # FULL amount (e.g., ₹1,000)
                        admin_deduction=admin_deduction_full,
                        tds_deduction=tds_deduction_full,
                        net_amount=net_after_all_deductions,
                        withdrawal_wallet_amount=withdrawal_amount,
                        upgraded_wallet_amount=upgrade_amount,
                        business_date=previous_day,
                        verification_status='Pending',
                        related_user_id=activated_user_id,  # CRITICAL: Track activated user for one-time protection
                        notes=f"Ved Income from Ved member {ved_member_id}, activated user {activated_user_id}",
                        payment_status='PAID',
                    )
                    db.add(pending_income)
                    db.flush()
                    # WVV PROTOCOL: Keep as 'Pending' for manual admin approval
                    logger.info(f"📋 Ved Income created as PENDING for {recipient_id} - awaiting admin approval")
                    total_incomes_created += 1
                    
                    # Create Guru Dakshina income for referrer (if user has referrer)
                    if guru_dakshina_amount > 0 and recipient.referrer_id:
                        referrer = db.query(User).filter(User.id == recipient.referrer_id).first()
                        if referrer and referrer.package_points > 0:  # Referrer must be active
                            # DC PROTOCOL: Check for duplicates before creating
                            if check_duplicate_income(db, referrer.id, 'Guru Dakshina', previous_day):
                                logger.warning(f"⚠️ Skipping duplicate Guru Dakshina for {referrer.id} on {previous_day}")
                            else:
                                gd_deductions = calculate_income_deductions_and_splits(guru_dakshina_amount, referrer.package_points, apply_guru_dakshina=False, upgrade_wallet_balance=getattr(referrer, 'upgrade_wallet_balance', None))
                                
                                guru_dakshina_income = PendingIncome(
                                    user_id=referrer.id,
                                    income_type='Guru Dakshina',
                                    gross_amount=guru_dakshina_amount,
                                    admin_deduction=gd_deductions['admin_deduction'],
                                    tds_deduction=gd_deductions['tds_deduction'],
                                    net_amount=gd_deductions['net_amount'],
                                    withdrawal_wallet_amount=gd_deductions['withdrawal_wallet_amount'],
                                    upgraded_wallet_amount=gd_deductions['upgraded_wallet_amount'],
                                    business_date=previous_day,
                                    verification_status='Pending',
                                    related_user_id=recipient_id,
                                    notes=f"2% Royalty received from {recipient_id}",
                                    payment_status='PAID',
                                )
                                db.add(guru_dakshina_income)
                                db.flush()
                                # WVV PROTOCOL: Keep as 'Pending' for manual admin approval
                                logger.info(f"📋 Guru Dakshina created as PENDING for {referrer.id} - awaiting admin approval")
                                total_incomes_created += 1
                
                # Create Direct Referral PendingIncome records
                direct_referral_bonuses = incomes.get('direct_referral', [])
                for bonus_data in direct_referral_bonuses:
                    bonus_amount = bonus_data['amount']
                    referred_user_id = bonus_data['referred_user_id']
                    
                    # DC PROTOCOL: Check for duplicates before creating (include referred_user_id for uniqueness)
                    if check_duplicate_income(db, recipient_id, 'Direct Referral', previous_day, related_user_id=referred_user_id):
                        logger.warning(f"⚠️ Skipping duplicate Direct Referral for {recipient_id} on {previous_day} for referral {referred_user_id}")
                        continue
                    
                    # Calculate with Guru Dakshina deduction (2% goes to referrer)
                    deductions = calculate_income_deductions_and_splits(bonus_amount, recipient.package_points, apply_guru_dakshina=True)
                    guru_dakshina_amount = deductions['guru_dakshina_deduction']
                    
                    # Store ORIGINAL bonus_amount as gross (FULL amount without any deductions)
                    # Apply ALL deductions when calculating net (admin + tds + guru_dakshina)
                    admin_deduction_full = bonus_amount * (INCOME_RATES['admin_charge_rate'] / 100)
                    tds_deduction_full = bonus_amount * (INCOME_RATES['tds_rate'] / 100)
                    net_after_all_deductions = bonus_amount - guru_dakshina_amount - admin_deduction_full - tds_deduction_full
                    
                    split = get_earnings_split(recipient.package_points, getattr(recipient, 'upgrade_wallet_balance', None))
                    withdrawal_amount = net_after_all_deductions * (split['withdrawable'] / 100)
                    upgrade_amount = net_after_all_deductions * (split['upgraded_wallet'] / 100)
                    
                    pending_income = PendingIncome(
                        user_id=recipient_id,
                        income_type='Direct Referral',
                        gross_amount=bonus_amount,  # FULL amount (e.g., ₹3,000)
                        gurudakshina_deduction=guru_dakshina_amount,  # 2% Guru Dakshina (e.g., ₹60)
                        admin_deduction=admin_deduction_full,
                        tds_deduction=tds_deduction_full,
                        net_amount=net_after_all_deductions,
                        withdrawal_wallet_amount=withdrawal_amount,
                        upgraded_wallet_amount=upgrade_amount,
                        business_date=previous_day,
                        verification_status='Pending',
                        related_user_id=referred_user_id,  # Track which user triggered this bonus
                        payment_status='PAID',
                    )
                    db.add(pending_income)
                    db.flush()
                    # WVV PROTOCOL: Keep as 'Pending' for manual admin approval
                    logger.info(f"📋 Direct Referral created as PENDING for {recipient_id} - awaiting admin approval")
                    total_incomes_created += 1
                    
                    # Create Guru Dakshina income for referrer (if user has referrer)
                    if guru_dakshina_amount > 0 and recipient.referrer_id:
                        referrer = db.query(User).filter(User.id == recipient.referrer_id).first()
                        if referrer and referrer.package_points > 0:  # Referrer must be active
                            # DC PROTOCOL: Check for duplicates before creating
                            if check_duplicate_income(db, referrer.id, 'Guru Dakshina', previous_day):
                                logger.warning(f"⚠️ Skipping duplicate Guru Dakshina for {referrer.id} on {previous_day}")
                            else:
                                gd_deductions = calculate_income_deductions_and_splits(guru_dakshina_amount, referrer.package_points, apply_guru_dakshina=False, upgrade_wallet_balance=getattr(referrer, 'upgrade_wallet_balance', None))
                                
                                guru_dakshina_income = PendingIncome(
                                    user_id=referrer.id,
                                    income_type='Guru Dakshina',
                                    gross_amount=guru_dakshina_amount,
                                    admin_deduction=gd_deductions['admin_deduction'],
                                    tds_deduction=gd_deductions['tds_deduction'],
                                    net_amount=gd_deductions['net_amount'],
                                    withdrawal_wallet_amount=gd_deductions['withdrawal_wallet_amount'],
                                    upgraded_wallet_amount=gd_deductions['upgraded_wallet_amount'],
                                    business_date=previous_day,
                                    verification_status='Pending',
                                    related_user_id=recipient_id,
                                    notes=f"2% Royalty received from {recipient_id}",
                                    payment_status='PAID',
                                )
                                db.add(guru_dakshina_income)
                                db.flush()
                                # WVV PROTOCOL: Keep as 'Pending' for manual admin approval
                                logger.info(f"📋 Guru Dakshina created as PENDING for {referrer.id} - awaiting admin approval")
                                total_incomes_created += 1
                    
                    # ✅ FIX BUG #2: Increment REFERRER's bonus count (not activated user's count)
                    recipient.referral_bonus_count = (recipient.referral_bonus_count or 0) + 1
                    logger.info(f"Direct Referral Bonus: {recipient_id} earns ₹{bonus_amount} (Gross) → ₹{net_after_all_deductions} (Net after 12% deductions) from {referred_user_id} activation (referrer's bonus count: {recipient.referral_bonus_count})")
                
                db.commit()
                
            except Exception as e:
                import traceback
                phase2_tb = traceback.format_exc()
                logger.error(f"❌ PHASE 2 ERROR for recipient {recipient_id}: {e}\n{phase2_tb}")
                phase2_errors.append({"user_id": recipient_id, "error": str(e)})
                db.rollback()
                continue
        
        logger.info(f"✅ Midnight income calculation completed (WVV PROTOCOL - PENDING STATUS):")
        logger.info(f"   - {total_incomes_created} incomes created as 'Pending' for manual admin approval")
        logger.info(f"   - ₹{total_company_earnings:.2f} company earnings from ceiling excess")
        logger.info(f"   - {len(phase2_errors)} Phase 2 errors (record creation failures)")
        logger.info(f"   - All incomes require manual admin approval before wallet crediting")
        
        if phase2_errors:
            logger.warning(f"⚠️ PHASE 2 ERRORS: {len(phase2_errors)}/{len(recipient_incomes)} recipients failed record creation")
            for err in phase2_errors[:10]:
                logger.warning(f"  - {err['user_id']}: {err['error']}")
        
        try:
            from app.services.leg_metrics_cache_service import LegMetricsCacheService
            cache_service = LegMetricsCacheService(db)
            snapshot_count = cache_service.update_all_snapshots()
            logger.info(f"📸 Snapshots updated for {snapshot_count} users (dashboard Previous tracking)")
        except Exception as snapshot_error:
            logger.error(f"⚠️ Snapshot update failed (non-critical): {snapshot_error}")
        
        all_errors = errors_in_calculation + phase2_errors
        if all_errors:
            scheduler_log.overall_status = "Completed with Errors"
            error_parts = []
            if errors_in_calculation:
                error_parts.append(f"{len(errors_in_calculation)} Phase 1 (calculation) errors")
            if phase2_errors:
                error_parts.append(f"{len(phase2_errors)} Phase 2 (record creation) errors")
            scheduler_log.matching_status = "; ".join(error_parts)
        else:
            scheduler_log.overall_status = "Completed"
            scheduler_log.matching_status = f"Success: {total_incomes_created} incomes created"
        scheduler_log.direct_referral_status = f"Processed via midnight scheduler"
        scheduler_log.ved_income_status = f"Processed via midnight scheduler"
        scheduler_log.total_incomes_created = total_incomes_created
        scheduler_log.total_users_affected = len(users_set)
        db.commit()
        
        prefix = "🔧 MANUAL" if is_manual else "✅ AUTO"
        logger.warning(f"{prefix} Income calculation completed (Log ID: {scheduler_log.id})")
        
        # Return results for manual triggers
        if is_manual:
            return {
                "status": "success",
                "target_date": str(target_date),
                "total_incomes_created": total_incomes_created,
                "total_users_affected": len(users_set),
                "total_company_earnings": total_company_earnings,
                "log_id": scheduler_log.id
            }
        
    except Exception as e:
        logger.error(f"❌ Error in income calculation: {e}")
        scheduler_log.overall_status = "Failed"
        scheduler_log.error_message = str(e)
        db.rollback()
        db.commit()  # Commit the failure status
        
        # Re-raise for manual triggers
        if is_manual:
            raise
        
    finally:
        db.close()

def refresh_leg_metrics_cache():
    """
    Refresh user leg metrics cache for dashboard performance
    Runs daily at 11:30 PM (before midnight income calculation)
    """
    logger.info("🔄 Starting leg metrics cache refresh...")
    
    db = SessionLocal()
    try:
        from app.services.leg_metrics_cache_service import LegMetricsCacheService
        
        cache_service = LegMetricsCacheService(db)
        processed_count = cache_service.bulk_refresh_all_users(batch_size=100)
        
        logger.info(f"✅ Leg metrics cache refresh completed: {processed_count} users processed")
        
    except Exception as e:
        logger.error(f"❌ Error refreshing leg metrics cache: {e}")
        db.rollback()
    finally:
        db.close()

def run_daily_wallet_sync():
    """
    DC Protocol Phase 1.7: DEPRECATED - REMOVED FROM SCHEDULER (Nov 3, 2025)
    
    LEGACY BEHAVIOR (Pre-Phase 1.7):
    - Transferred earning wallet → withdrawable wallet daily at 3:00 AM IST
    - Required KYC approval and ≥₹1,000 balance
    
    DC PROTOCOL NEW BEHAVIOR (Phase 1.7+):
    - Materialized views compute both wallets independently from pending_income
    - Earning wallet = SUM(pending_income WHERE status IN unpaid statuses)
    - Withdrawable wallet = SUM(pending_income WHERE status IN paid statuses) - withdrawals
    - No manual "transfer" needed - status change automatically moves income between views
    - Auto-approval sets status to 'Completed' → instantly appears in withdrawable view
    
    STATUS: Removed from scheduler configuration. Function kept for reference only.
    This function is no longer called and can be safely deleted in future cleanup.
    """
    from app.models.system_log import SchedulerLog
    
    db = SessionLocal()
    scheduled_date = get_indian_time().replace(hour=3, minute=0, second=0, microsecond=0)
    
    # Create log (mark as skipped, not running)
    scheduler_log = SchedulerLog(
        job_id='daily_wallet_sync',
        job_name='Wallet Sync (DEPRECATED)',
        scheduled_date=scheduled_date,
        triggered_at=get_indian_time(),
        income_triggered="N/A",
        wallet_sync_status="Skipped (DC Protocol Phase 1.7)",
        overall_status="Skipped"
    )
    db.add(scheduler_log)
    db.commit()
    
    logger.info(f"ℹ️  Wallet sync skipped - replaced by materialized views (DC Protocol Phase 1.7)")
    logger.info(f"📊 Wallet balances now computed automatically from pending_income ledger")
    
    db.close()

def auto_approve_stuck_income():
    """
    Auto-approve income stuck in approval pipeline and create withdrawal requests
    Runs daily at 6:30 AM IST (before withdrawal generation)
    
    DC Protocol Feb 2026: Only auto-approve records created BEFORE Feb 12, 2026.
    Records from Feb 12, 2026 onwards MUST go through staff 2-step workflow.
    """
    from app.models.system_log import SchedulerLog
    from app.models.withdrawal import WithdrawalRequest
    from sqlalchemy import text
    from datetime import date as date_type
    
    STAFF_WORKFLOW_CUTOFF = date_type(2026, 2, 12)
    
    db = SessionLocal()
    scheduled_date = get_indian_time().replace(hour=6, minute=30, second=0, microsecond=0)
    
    scheduler_log = SchedulerLog(
        job_id='auto_approve_stuck_income',
        job_name='Auto-Approve Stuck Income',
        scheduled_date=scheduled_date,
        triggered_at=get_indian_time(),
        income_triggered="N/A",
        overall_status="Running"
    )
    db.add(scheduler_log)
    db.commit()
    
    logger.warning(f"🔓 Auto-approve stuck income triggered (Log ID: {scheduler_log.id})")
    try:
        stuck_income = db.query(PendingIncome).filter(
            PendingIncome.verification_status.in_(['Pending', 'Admin Verified', 'Super Admin Verified']),
            PendingIncome.business_date < STAFF_WORKFLOW_CUTOFF
        ).all()
        
        if not stuck_income:
            logger.info("✅ No stuck income found - all records flowing through approval pipeline")
            scheduler_log.overall_status = "Completed"
            db.commit()
            db.close()
            return
        
        approved_count = 0
        approved_amount = 0
        affected_users = set()
        
        # STEP 2: Auto-approve all stuck income
        for income in stuck_income:
            try:
                income.verification_status = 'Completed'
                income.admin_verified_by_id = 'MNR00000000'
                income.admin_verified_at = get_indian_time()
                income.super_admin_verified_by_id = 'MNR00000000'
                income.super_admin_verified_at = get_indian_time()
                income.accounts_paid_by_id = 'MNR00000000'
                income.accounts_paid_at = get_indian_time()
                income.notes = 'AUTO-APPROVED: Daily scheduler auto-approval (Phase 1.11)'
                
                approved_count += 1
                approved_amount += float(income.net_amount)
                affected_users.add(income.user_id)
                
                db.add(income)
            except Exception as e:
                logger.error(f"❌ Error auto-approving income {income.id}: {e}")
                continue
        
        db.commit()
        
        if approved_count > 0:
            logger.info(f"✅ Auto-approved {approved_count} stuck income records: ₹{int(approved_amount)}")
        
        # STEP 3: Create withdrawal requests for newly approved users
        created_count = 0
        created_amount = 0
        
        for user_id in affected_users:
            try:
                # Calculate earnings and withdrawals for this user
                earnings = db.query(func.sum(PendingIncome.net_amount)).filter(
                    PendingIncome.user_id == user_id,
                    PendingIncome.verification_status.in_(['Completed', 'Staff Validated'])
                ).scalar() or 0
                
                withdrawn = db.query(func.sum(WithdrawalRequest.final_payout)).filter(
                    WithdrawalRequest.user_id == user_id,
                    WithdrawalRequest.status == 'Completed'
                ).scalar() or 0
                
                withdrawal_amount = int(float(earnings) - float(withdrawn))
                
                if withdrawal_amount <= 0:
                    logger.debug(f"⏭️  {user_id}: No new amount to withdraw (earned={earnings}, withdrawn={withdrawn})")
                    continue
                
                # Get user's bank details
                user = db.query(User).filter(User.id == user_id).first()
                if not user or not user.bank_account_number:
                    logger.warning(f"⏭️  {user_id}: Missing bank details")
                    continue
                
                # DC_WITHDRAW_001: Skip if user already has an active withdrawal
                from app.models.withdrawal import get_active_withdrawal
                if get_active_withdrawal(db, user_id):
                    logger.debug(f"⏭️  {user_id}: Already has active withdrawal — skipping auto-approve creation")
                    continue

                # DC Protocol: NO deductions at withdrawal level
                # Deductions (2% GD + 8% Admin + 2% TDS = 12%) already applied at income level
                # Withdrawal pays full NET amount from wallet to bank
                
                # DC Protocol Fix (Dec 30, 2025): Create withdrawal with status='Pending'
                # Previously created with status='Completed' which bypassed all approval
                # Now requires Finance staff approval via SFMS before marking as paid
                withdrawal = WithdrawalRequest(
                    user_id=user_id,
                    withdrawal_amount=withdrawal_amount,
                    admin_charges=0,
                    tds_amount=0,
                    final_payout=withdrawal_amount,
                    bank_name=user.bank_name or 'Bank',
                    account_number=user.bank_account_number,
                    ifsc_code=user.bank_ifsc_code,
                    account_holder_name=user.bank_account_holder or user.name,
                    status='Pending',
                    request_date=get_indian_time().date(),
                    created_at=get_indian_time(),
                    is_auto_generated=True
                )
                db.add(withdrawal)
                db.commit()
                
                created_count += 1
                created_amount += withdrawal_amount
                logger.info(f"✅ Created withdrawal for {user_id}: ₹{withdrawal_amount}")
                
            except Exception as e:
                logger.error(f"❌ Error creating withdrawal for {user_id}: {e}")
                db.rollback()
                continue
        
        if created_count > 0:
            logger.info(f"✅ Created {created_count} withdrawal requests: ₹{created_amount}")
        
        scheduler_log.overall_status = "Completed"
        scheduler_log.income_triggered = f"{approved_count} approved, {created_count} withdrawn"
        db.commit()
        logger.info(f"✅ Auto-approve stuck income completed: {approved_count} incomes, {created_count} withdrawals")
        
    except Exception as e:
        scheduler_log.overall_status = "Failed"
        scheduler_log.error_message = str(e)
        db.commit()
        logger.error(f"❌ Auto-approve stuck income failed: {e}")
    finally:
        db.close()

def backfill_direct_referral_income():
    """
    DC PROTOCOL (Jan 2026): Backfill Direct Referral income for all historical activations
    that were missed because the scheduler wasn't running or the feature was added later.
    
    This is a ONE-TIME backfill that:
    1. Finds all activated users who have referrers
    2. Checks if Direct Referral income already exists for that user
    3. Creates Direct Referral income if missing
    
    Uses existing utility functions for DC Protocol compliance:
    - check_duplicate_income() for uniqueness
    - calculate_income_deductions_and_splits() for correct deduction rates (8% admin, 2% TDS, 2% GD)
    
    Safe to run multiple times - uses duplicate check before creating.
    """
    from app.core.database import SessionLocal
    from app.models.user import User
    from app.models.transaction import PendingIncome
    
    db = SessionLocal()
    created_count = 0
    skipped_count = 0
    
    try:
        logger.info("🔄 Starting Direct Referral Income backfill (DC Protocol compliant)...")
        
        # Find all activated users with referrers (potential Direct Referral candidates)
        activated_users = db.query(User).filter(
            User.activation_date.isnot(None),
            User.referrer_id.isnot(None),
            User.package_points > 0
        ).all()
        
        logger.info(f"📊 Found {len(activated_users)} activated users with referrers to process")
        
        for user in activated_users:
            try:
                # Skip self-referrals
                if user.id == user.referrer_id:
                    continue
                
                # Use activation date as business date
                business_date = user.activation_date.date() if hasattr(user.activation_date, 'date') else user.activation_date
                
                # DC PROTOCOL: Use check_duplicate_income with business_date + related_user_id
                if check_duplicate_income(db, user.referrer_id, 'Direct Referral', business_date, related_user_id=user.id):
                    skipped_count += 1
                    continue
                
                # Get referrer
                referrer = db.query(User).filter(User.id == user.referrer_id).first()
                if not referrer or not referrer.package_points or referrer.package_points == 0:
                    skipped_count += 1
                    continue
                
                # Calculate bonus amount based on user's package
                bonus_amount = 0.0
                if user.package_points == 1.0 or user.package_points == 1:  # Platinum
                    bonus_amount = 3000.0
                elif user.package_points == 0.5:  # Diamond
                    bonus_amount = 1500.0
                else:
                    skipped_count += 1
                    continue
                
                # DC PROTOCOL: Use calculate_income_deductions_and_splits for correct rates
                # Rates: 8% admin, 2% TDS, 2% Guru Dakshina = 88% net
                deductions = calculate_income_deductions_and_splits(bonus_amount, referrer.package_points, apply_guru_dakshina=True)
                
                # Create Direct Referral income
                pending_income = PendingIncome(
                    user_id=referrer.id,
                    income_type='Direct Referral',
                    gross_amount=bonus_amount,
                    gurudakshina_deduction=deductions['guru_dakshina_deduction'],
                    admin_deduction=deductions['admin_deduction'],
                    tds_deduction=deductions['tds_deduction'],
                    net_amount=deductions['net_amount'],
                    withdrawal_wallet_amount=deductions['withdrawal_wallet_amount'],
                    upgraded_wallet_amount=deductions['upgraded_wallet_amount'],
                    business_date=business_date,
                    verification_status='Pending',
                    related_user_id=user.id,
                    notes=f"Backfill: Direct Referral from {user.id} activation",
                    payment_status='PAID',
                )
                db.add(pending_income)
                created_count += 1
                
                # Also create Guru Dakshina for referrer's referrer if applicable
                guru_dakshina_amount = deductions['guru_dakshina_deduction']
                if guru_dakshina_amount > 0 and referrer.referrer_id:
                    grandparent = db.query(User).filter(User.id == referrer.referrer_id).first()
                    if grandparent and grandparent.package_points and grandparent.package_points > 0:
                        # DC PROTOCOL: Check for duplicate Guru Dakshina
                        if not check_duplicate_income(db, grandparent.id, 'Guru Dakshina', business_date, related_user_id=referrer.id):
                            # Use proper deduction calculation for Guru Dakshina (no nested GD)
                            gd_deductions = calculate_income_deductions_and_splits(guru_dakshina_amount, grandparent.package_points, apply_guru_dakshina=False)
                            
                            guru_dakshina_income = PendingIncome(
                                user_id=grandparent.id,
                                income_type='Guru Dakshina',
                                gross_amount=guru_dakshina_amount,
                                admin_deduction=gd_deductions['admin_deduction'],
                                tds_deduction=gd_deductions['tds_deduction'],
                                net_amount=gd_deductions['net_amount'],
                                withdrawal_wallet_amount=gd_deductions['withdrawal_wallet_amount'],
                                upgraded_wallet_amount=gd_deductions['upgraded_wallet_amount'],
                                business_date=business_date,
                                verification_status='Pending',
                                related_user_id=referrer.id,
                                notes=f"Backfill: Guru Dakshina from {referrer.id}",
                                payment_status='PAID',
                            )
                            db.add(guru_dakshina_income)
                
                if created_count % 50 == 0:
                    db.commit()
                    logger.info(f"   Progress: {created_count} created, {skipped_count} skipped")
                    
            except Exception as e:
                logger.error(f"Error processing user {user.id}: {e}")
                continue
        
        db.commit()
        logger.info(f"✅ Direct Referral backfill completed: {created_count} created, {skipped_count} skipped")
        return {"created": created_count, "skipped": skipped_count}
        
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Direct Referral backfill failed: {e}")
        return {"error": str(e)}
    finally:
        db.close()


def backfill_ved_income():
    """
    DC PROTOCOL (Jan 2026): Backfill Ved Income for all historical activations
    that were missed because the scheduler wasn't running or processes day-by-day.
    
    Ved Income Logic:
    - Ved member must be in ved_team_member table
    - Ved Head must be activated
    - Ved owner must have 1:1 active direct referrals on both sides
    - Ved owner must have first matching achieved
    - User must NOT be a direct referral of Ved owner
    
    Ved Income Rates:
    - Platinum (1.0 points): ₹1,000
    - Diamond (0.5 points): ₹500
    
    Uses DC Protocol compliant utilities for deduction calculation.
    Safe to run multiple times - uses duplicate check before creating.
    """
    from app.core.database import SessionLocal
    from app.models.user import User
    from app.models.transaction import PendingIncome
    from app.models.ved_team import VedTeamMember
    
    db = SessionLocal()
    created_count = 0
    skipped_count = 0
    
    try:
        logger.info("🔄 Starting Ved Income backfill (DC Protocol compliant)...")
        
        # Find all Ved team members who are activated and could generate Ved income
        ved_members = db.query(VedTeamMember).filter(
            VedTeamMember.is_active == True
        ).all()
        
        logger.info(f"📊 Found {len(ved_members)} active Ved team members to process")
        
        for ved_member in ved_members:
            try:
                member_id = ved_member.member_id
                ved_owner_id = ved_member.ved_owner_id
                ved_head_id = ved_member.ved_head_id
                
                # Skip if member is the Ved owner (no self-income)
                if member_id == ved_owner_id:
                    continue
                
                # Get the member user
                member = db.query(User).filter(User.id == member_id).first()
                if not member or not member.activation_date or not member.package_points or member.package_points == 0:
                    skipped_count += 1
                    continue
                
                # Skip direct referrals of Ved owner (they get Direct Referral income instead)
                if member.referrer_id == ved_owner_id:
                    skipped_count += 1
                    continue
                
                # Use activation date as business date
                business_date = member.activation_date.date() if hasattr(member.activation_date, 'date') else member.activation_date
                
                # DC PROTOCOL: Check for duplicate Ved Income
                if check_duplicate_income(db, ved_owner_id, 'Ved Income', business_date, related_user_id=member_id):
                    skipped_count += 1
                    continue
                
                # Check if Ved Head is activated
                ved_head = db.query(User).filter(User.id == ved_head_id).first()
                if not ved_head or not ved_head.activation_date or ved_head.package_points < 0.5:
                    skipped_count += 1
                    continue
                
                # Get Ved owner
                ved_owner = db.query(User).filter(User.id == ved_owner_id).first()
                if not ved_owner or not ved_owner.activation_date or not ved_owner.package_points:
                    skipped_count += 1
                    continue
                
                # Check if Ved owner has ved_paused flag
                if hasattr(ved_owner, 'ved_paused') and ved_owner.ved_paused:
                    skipped_count += 1
                    continue
                
                # Check prerequisite: Ved owner must have 1:1 active direct referrals on both sides
                if not check_direct_referrals_both_sides(db, ved_owner_id):
                    skipped_count += 1
                    continue
                
                # Check prerequisite: Ved owner must have first matching achieved
                if not check_first_matching_achieved(db, ved_owner_id):
                    skipped_count += 1
                    continue
                
                # Calculate Ved Income amount based on member's package
                if member.package_points >= 1.0:  # Platinum
                    ved_amount = 1000.0
                elif member.package_points >= 0.5:  # Diamond
                    ved_amount = 500.0
                else:
                    skipped_count += 1
                    continue
                
                # DC PROTOCOL: Use calculate_income_deductions_and_splits for correct rates
                deductions = calculate_income_deductions_and_splits(ved_amount, ved_owner.package_points, apply_guru_dakshina=True)
                
                # Create Ved Income record
                pending_income = PendingIncome(
                    user_id=ved_owner_id,
                    income_type='Ved Income',
                    gross_amount=ved_amount,
                    gurudakshina_deduction=deductions['guru_dakshina_deduction'],
                    admin_deduction=deductions['admin_deduction'],
                    tds_deduction=deductions['tds_deduction'],
                    net_amount=deductions['net_amount'],
                    withdrawal_wallet_amount=deductions['withdrawal_wallet_amount'],
                    upgraded_wallet_amount=deductions['upgraded_wallet_amount'],
                    business_date=business_date,
                    verification_status='Pending',
                    related_user_id=member_id,
                    notes=f"Backfill: Ved Income from {member_id} activation",
                    payment_status='PAID',
                )
                db.add(pending_income)
                created_count += 1
                
                # Also create Guru Dakshina for Ved owner's referrer if applicable
                guru_dakshina_amount = deductions['guru_dakshina_deduction']
                if guru_dakshina_amount > 0 and ved_owner.referrer_id:
                    grandparent = db.query(User).filter(User.id == ved_owner.referrer_id).first()
                    if grandparent and grandparent.package_points and grandparent.package_points > 0:
                        # DC PROTOCOL: Check for duplicate Guru Dakshina
                        if not check_duplicate_income(db, grandparent.id, 'Guru Dakshina', business_date, related_user_id=ved_owner_id):
                            gd_deductions = calculate_income_deductions_and_splits(guru_dakshina_amount, grandparent.package_points, apply_guru_dakshina=False)
                            
                            guru_dakshina_income = PendingIncome(
                                user_id=grandparent.id,
                                income_type='Guru Dakshina',
                                gross_amount=guru_dakshina_amount,
                                admin_deduction=gd_deductions['admin_deduction'],
                                tds_deduction=gd_deductions['tds_deduction'],
                                net_amount=gd_deductions['net_amount'],
                                withdrawal_wallet_amount=gd_deductions['withdrawal_wallet_amount'],
                                upgraded_wallet_amount=gd_deductions['upgraded_wallet_amount'],
                                business_date=business_date,
                                verification_status='Pending',
                                related_user_id=ved_owner_id,
                                notes=f"Backfill: Guru Dakshina from Ved Income of {ved_owner_id}",
                                payment_status='PAID',
                            )
                            db.add(guru_dakshina_income)
                
                if created_count % 50 == 0:
                    db.commit()
                    logger.info(f"   Ved Progress: {created_count} created, {skipped_count} skipped")
                    
            except Exception as e:
                logger.error(f"Error processing Ved member {ved_member.member_id}: {e}")
                continue
        
        db.commit()
        logger.info(f"✅ Ved Income backfill completed: {created_count} created, {skipped_count} skipped")
        return {"created": created_count, "skipped": skipped_count}
        
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Ved Income backfill failed: {e}")
        return {"error": str(e)}
    finally:
        db.close()

def generate_automatic_withdrawals():
    """
    Generate automatic withdrawal requests for eligible users
    Runs Monday-Saturday at 7:00 AM IST
    
    Eligibility Criteria:
    - withdrawable_wallet >= buffer amount (₹1,000)
    - No pending withdrawal requests
    - Valid bank details (from KYC or profile)
    - KYC approved status
    
    Withdrawal Amount:
    - Amount above buffer (withdrawable_wallet - buffer)
    - Capped at max_withdrawal_limit (default ₹50,000)
    """
    from app.models.system_log import SchedulerLog
    from sqlalchemy.exc import IntegrityError as _IntegrityError
    from sqlalchemy import func as _sqlfunc

    # ── DC_WITHDRAW_GUARD_001 (Phase 4): stale-recovery + constraint-based guard
    #
    # Unique index in play:
    #   uq_scheduler_log_job_per_day
    #   ON scheduler_log (job_id, (scheduled_date::date))
    #   WHERE overall_status IN ('Running', 'Completed')
    #
    # Full decision tree:
    #
    #   1. SELECT today's Running row (if any)
    #      a. Found, age > 60 min  → mark Failed + commit (free the constraint
    #                                 slot), fall through to INSERT
    #      b. Found, age ≤ 60 min  → log "already running", exit safely
    #      c. Not found            → fall through to INSERT
    #
    #   2. Blind INSERT of Running row
    #      a. Succeeds             → no Running/Completed row existed → proceed
    #      b. IntegrityError       → Completed row exists today → exit safely
    #      c. Any other exception  → FAIL-CLOSED: rollback + return
    #
    # Race-condition note:
    #   Two concurrent instances that both see a stale row will both issue the
    #   same UPDATE (idempotent — both set status=Failed on the same row).
    #   PostgreSQL row-level locking serialises the two commits harmlessly.
    #   The subsequent INSERT is then serialised by the unique constraint:
    #   exactly one succeeds; the other gets IntegrityError and exits.
    #
    _STALE_THRESHOLD_MINUTES = 60

    db = SessionLocal()
    scheduled_date = get_indian_time().replace(hour=7, minute=0, second=0, microsecond=0)
    _today_ist = scheduled_date.date()

    try:
        # ── Step 1: stale RUNNING recovery ────────────────────────────────────
        _stale = (
            db.query(SchedulerLog)
            .filter(
                SchedulerLog.job_id == 'auto_withdrawal_generation',
                _sqlfunc.date(SchedulerLog.scheduled_date) == _today_ist,
                SchedulerLog.overall_status == 'Running',
            )
            .first()
        )
        if _stale:
            _age_minutes = (get_indian_time() - _stale.triggered_at).total_seconds() / 60
            if _age_minutes > _STALE_THRESHOLD_MINUTES:
                logger.warning(
                    f"⚠️  DC_WITHDRAW_GUARD_001: Stale RUNNING detected "
                    f"(Log #{_stale.id}, age={_age_minutes:.1f}m) — marking as Failed"
                )
                _stale.overall_status = 'Failed'
                _stale.error_message = (
                    f"Marked Failed by stale-recovery guard after {_age_minutes:.1f} minutes"
                )
                db.commit()
                # Constraint slot is now free — fall through to INSERT below
            else:
                logger.info(
                    f"⏭️  generate_automatic_withdrawals: job already running today "
                    f"(Log #{_stale.id}, age={_age_minutes:.1f}m) — skipping"
                )
                db.close()
                return

        # ── Step 2: atomic INSERT via unique constraint ────────────────────────
        # Blind INSERT — no prior SELECT for Completed.
        # If a Completed row already exists today the unique index fires
        # IntegrityError, caught below.
        scheduler_log = SchedulerLog(
            job_id='auto_withdrawal_generation',
            job_name='Withdrawal Generation',
            scheduled_date=scheduled_date,
            triggered_at=get_indian_time(),
            income_triggered="N/A",
            withdrawal_status="Running",
            overall_status="Running",
        )
        db.add(scheduler_log)
        db.commit()

    except _IntegrityError:
        # Unique constraint fired — Completed row already exists today
        logger.info(
            f"⏭️  generate_automatic_withdrawals: job already completed today "
            f"({_today_ist}) — skipping"
        )
        try:
            db.rollback()
            db.close()
        except Exception:
            pass
        return

    except Exception as _guard_exc:
        # FAIL-CLOSED — any other DB error: do NOT proceed
        logger.error(
            f"❌ DC_WITHDRAW_GUARD_001: guard failed — "
            f"job will NOT proceed. Reason: {_guard_exc}"
        )
        try:
            db.rollback()
            db.close()
        except Exception:
            pass
        return
    # ── end guard ─────────────────────────────────────────────────────────────

    logger.warning(f"💸 Withdrawal generation triggered (Log ID: {scheduler_log.id})")
    try:
        from app.models.withdrawal import WithdrawalRequest
        from app.models.system_control import AppSettings
        from decimal import Decimal
        from sqlalchemy import text
        
        # Get withdrawal settings
        settings = AppSettings.get_withdrawal_settings(db)
        if not settings.get('auto_withdrawal_enabled', True):
            logger.info("⚠️  Automatic withdrawals disabled in system settings")
            return
        
        max_limit = Decimal(str(settings.get('max_withdrawal_limit', 50000)))
        buffer_amount = Decimal(str(settings.get('withdrawal_buffer_amount', 1000)))
        
        logger.info(f"📊 Settings: Max=₹{max_limit}, Buffer=₹{buffer_amount}")
        
        # DC Protocol Phase 1.6: Get wallet balances from materialized views
        from app.services.wallet_balance_service import get_withdrawable_wallet
        
        # Find potentially eligible users (DC Protocol - respects RVZ skip settings)
        # Get RVZ skip settings first
        skip_settings = AppSettings.get_kyc_skip_settings(db)
        
        # Build filter based on skip settings
        filters = [User.account_status == 'Active']
        
        # Add KYC check only if NOT skipped by RVZ
        if not skip_settings.get('skip_kyc_requirement'):
            filters.append(User.kyc_status == 'Approved')
        
        # Add Bank check only if NOT skipped by RVZ
        if not skip_settings.get('skip_bank_requirement'):
            filters.append(User.bank_details_status == 'Approved')
        
        potential_users = db.query(User).filter(*filters).all()
        
        # Filter by computed withdrawable wallet balance (from materialized view)
        eligible_users = []
        for user in potential_users:
            computed_balance = get_withdrawable_wallet(db, user.id)
            if computed_balance >= buffer_amount:
                eligible_users.append(user)
        
        generated_count = 0
        skipped_count = 0
        total_amount = Decimal('0')
        
        for user in eligible_users:
            try:
                # DC_WITHDRAW_001: Check for any in-flight withdrawal before creating
                from app.models.withdrawal import get_active_withdrawal
                existing_pending = get_active_withdrawal(db, user.id)
                
                if existing_pending:
                    logger.debug(f"⏭️  Skipped {user.id}: Has active withdrawal #{existing_pending.id} [{existing_pending.status}]")
                    skipped_count += 1
                    continue
                
                # DC Protocol Phase 1.6: Calculate withdrawal amount from computed balance
                available = get_withdrawable_wallet(db, user.id)
                withdrawal_amount = available - buffer_amount
                
                # Cap at max limit
                if withdrawal_amount > max_limit:
                    withdrawal_amount = max_limit
                
                # Round to nearest rupee
                withdrawal_amount = int(withdrawal_amount)
                
                if withdrawal_amount < 1000:
                    logger.debug(f"⏭️  Skipped {user.id}: Amount below ₹1,000 after buffer")
                    skipped_count += 1
                    continue
                
                # STF v2.0 LAYER 1: CRITICAL VALIDATION - Prevent Over-Withdrawal
                # ================================================================
                # RULE: User cannot withdraw more than they have EARNED
                # Get total earned vs total withdrawn BEFORE creating new request
                total_earned = db.query(func.sum(PendingIncome.net_amount)).filter(
                    PendingIncome.user_id == user.id,
                    PendingIncome.verification_status.in_(['Completed', 'Staff Validated'])
                ).scalar() or 0
                
                total_withdrawn = db.query(func.sum(WithdrawalRequest.final_payout)).filter(
                    WithdrawalRequest.user_id == user.id,
                    WithdrawalRequest.status == 'Completed'
                ).scalar() or 0
                
                # Check if this withdrawal would cause over-withdrawal
                proposed_total = total_withdrawn + withdrawal_amount
                if proposed_total > total_earned:
                    # Cap the withdrawal to prevent over-withdrawal
                    safe_withdrawal = int(total_earned - total_withdrawn)
                    if safe_withdrawal < 1000:
                        logger.warning(f"⏭️  Skipped {user.id}: Cannot withdraw safely (earned={total_earned}, already_withdrawn={total_withdrawn})")
                        skipped_count += 1
                        continue
                    withdrawal_amount = safe_withdrawal
                    logger.info(f"⚠️  ADJUSTED withdrawal for {user.id}: ₹{withdrawal_amount} (STF v2.0 - prevent over-withdrawal)")
                
                # Get bank details (prefer KYC data, fallback to profile)
                bank_name = None
                account_number = None
                ifsc_code = None
                account_holder_name = None
                
                # Try to get from KYC documents first
                try:
                    from app.models.kyc import KYCDocument
                    kyc_doc = db.query(KYCDocument).filter(
                        KYCDocument.user_id == user.id,
                        KYCDocument.status == 'Approved'
                    ).first()
                    if kyc_doc and hasattr(kyc_doc, 'bank_name'):
                        bank_name = kyc_doc.bank_name
                        account_number = kyc_doc.account_number
                        ifsc_code = kyc_doc.ifsc_code
                        account_holder_name = kyc_doc.account_holder_name
                except:
                    pass
                
                # Fallback to user profile fields
                if not bank_name:
                    if hasattr(user, 'bank_name'):
                        bank_name = user.bank_name
                        account_number = user.bank_account_number
                        ifsc_code = user.bank_ifsc_code
                        account_holder_name = user.bank_account_holder or user.name
                
                # Validate bank details
                if not all([bank_name, account_number, ifsc_code, account_holder_name]):
                    logger.warning(f"⚠️  Skipped {user.id}: Incomplete bank details")
                    skipped_count += 1
                    continue
                
                # DC Protocol: NO deductions at withdrawal level
                # Deductions (2% GD + 8% Admin + 2% TDS = 12%) already applied at income level
                # Withdrawal pays full NET amount from wallet to bank
                admin_charges = 0
                tds_amount = 0
                final_payout = withdrawal_amount
                
                # DC Protocol Phase 1.7: OPTION 1 - No deduction until Completed
                # Auto-withdrawal creates request with status='Pending' ONLY
                # Wallet deduction happens when admin changes status to 'Completed' (after manual approval)
                # This ensures manual approval control and matches materialized view logic
                
                # Create automatic withdrawal request (NO wallet deduction)
                withdrawal = WithdrawalRequest(
                    user_id=user.id,
                    withdrawal_amount=withdrawal_amount,
                    admin_charges=admin_charges,
                    tds_amount=tds_amount,
                    final_payout=final_payout,
                    bank_name=bank_name,
                    account_number=account_number,
                    ifsc_code=ifsc_code,
                    account_holder_name=account_holder_name,
                    status='Pending',
                    is_auto_generated=True
                )
                
                db.add(withdrawal)
                db.commit()
                
                generated_count += 1
                total_amount += Decimal(str(withdrawal_amount))
                
                logger.info(f"✅ Generated withdrawal for {user.id}: ₹{withdrawal_amount:,} (ID: {withdrawal.id})")
                
            except Exception as user_error:
                logger.error(f"❌ Error generating withdrawal for {user.id}: {user_error}")
                db.rollback()
                skipped_count += 1
                continue
        
        scheduler_log.total_incomes_created = generated_count
        scheduler_log.total_users_affected = len(eligible_users)
        scheduler_log.withdrawal_status = "Completed"
        scheduler_log.overall_status = "Completed"
        db.commit()
        
        logger.info(f"✅ Withdrawal generation completed: {generated_count} withdrawals created")
        
    except Exception as e:
        scheduler_log.withdrawal_status = "Failed"
        scheduler_log.overall_status = "Failed"
        scheduler_log.error_message = str(e)
        db.commit()
        logger.error(f"❌ Withdrawal generation failed: {e}")
    finally:
        db.close()

def auto_sync_marketplace_sheets():
    """
    Daily auto-sync of VGK4U Marketplace spares catalog from Google Sheets.
    Runs at 5:00 AM IST — updates prices, stock quantities, new SKUs, and
    auto-raises procurement for zero-qty items.
    Manual sync via the admin page remains available at any time.
    """
    from app.services.marketplace_sync import run_sync
    from app.models.marketplace import MarketspareItem
    from sqlalchemy import text

    db = SessionLocal()
    try:
        logger.info("[MARKETPLACE-AUTO-SYNC] Starting scheduled Google Sheets sync...")

        # Get all distinct company_ids that have marketplace data
        rows = db.execute(
            text("SELECT DISTINCT company_id FROM marketplace_spares WHERE company_id IS NOT NULL ORDER BY company_id")
        ).fetchall()

        if not rows:
            # Fall back to company_id=1 if no data yet
            company_ids = [1]
            logger.info("[MARKETPLACE-AUTO-SYNC] No existing data — syncing for company_id=1")
        else:
            company_ids = [r[0] for r in rows]
            logger.info(f"[MARKETPLACE-AUTO-SYNC] Syncing for {len(company_ids)} company(s): {company_ids}")

        total_upserted = 0
        total_proc_raised = 0

        for cid in company_ids:
            try:
                result = run_sync(db, company_id=cid, triggered_by='scheduled_daily')
                upserted = result.get('upserted', 0)
                proc = result.get('auto_procurement_raised', 0)
                total_upserted += upserted
                total_proc_raised += proc
                logger.info(
                    f"[MARKETPLACE-AUTO-SYNC] company_id={cid}: "
                    f"{upserted} upserted, {proc} procurement raised"
                )
            except Exception as company_err:
                logger.error(f"[MARKETPLACE-AUTO-SYNC] company_id={cid} failed: {company_err}")

        logger.info(
            f"[MARKETPLACE-AUTO-SYNC] ✅ Complete — "
            f"{total_upserted} total SKUs synced, {total_proc_raised} procurement requests raised"
        )

        # DC-STOCK-MKT-001: Stock→marketplace sync — MANUAL ONLY (auto disabled per DC-DEDUP-001)
        # Use the Stock Items admin page to trigger a manual sync.
        logger.info("[MARKETPLACE-AUTO-SYNC] Stock→marketplace auto-sync is disabled (manual only).")

    except Exception as e:
        logger.error(f"[MARKETPLACE-AUTO-SYNC] ❌ Scheduler sync failed: {e}")
        db.rollback()
    finally:
        db.close()


def refresh_materialized_wallet_views():
    """
    DC Protocol Phase 1.3: Refresh wallet materialized views
    Scheduled job to keep views in sync with ledger (replaces per-transaction triggers)
    """
    from sqlalchemy import text
    db = SessionLocal()
    
    try:
        logger.info("🔄 DC Protocol: Refreshing wallet materialized views...")
        
        # Use CONCURRENTLY for non-blocking refresh (safe outside triggers)
        db.execute(text("SELECT refresh_wallet_materialized_views()"))
        db.commit()
        
        # Get view stats
        result = db.execute(text("""
            SELECT 
                (SELECT COUNT(*) FROM user_earning_wallet_balance) as earning_count,
                (SELECT COUNT(*) FROM user_withdrawable_wallet_balance) as withdrawable_count
        """)).first()
        
        logger.info(f"✅ DC Protocol: Views refreshed - {result[0]} earning, {result[1]} withdrawable")
        
    except Exception as e:
        logger.error(f"❌ DC Protocol: View refresh failed: {e}")
        db.rollback()
    finally:
        db.close()

def run_vgk_points_refill_safety_net():
    """
    [DC-POINTS-REFILL] Apr 2026 — Daily safety-net job at 2:00 AM IST.
    Catches any activated members whose balance is 0 and whose refill was missed by
    the inline hook (e.g. edge cases, direct DB debits). Only fires within the
    180-day window of the most recent 50k credit (max 2 refills).
    """
    from decimal import Decimal
    from app.models.staff_accounts import OfficialPartner, VGKPointsLedger
    from app.api.v1.endpoints.vgk_team import _check_and_apply_auto_refill
    db = SessionLocal()
    try:
        now = get_indian_time()
        now_naive = now.replace(tzinfo=None)
        candidates = db.query(OfficialPartner).filter(
            OfficialPartner.is_paid_activation == True,
            OfficialPartner.vgk_points_balance == 0,
            OfficialPartner.is_active == True,
            OfficialPartner.category == 'VGK_TEAM',
        ).all()
        applied = 0
        for partner in candidates:
            if _check_and_apply_auto_refill(partner, db, now_naive):
                applied += 1
        if applied:
            db.commit()
        logger.info(
            '[DC-POINTS-REFILL-SAFETY-NET] ✅ Checked %d candidates, applied %d refills',
            len(candidates), applied
        )
    except Exception as e:
        logger.error('[DC-POINTS-REFILL-SAFETY-NET] ❌ Error: %s', e)
        db.rollback()
    finally:
        db.close()


def check_shadow_mode_reconciliation():
    """
    DC Protocol Phase 1.4: Shadow Mode Reconciliation Monitor
    Daily check to ensure stored wallets match computed values from materialized views
    Alerts if mismatches detected (indicates data inconsistency)
    """
    from sqlalchemy import text
    db = SessionLocal()
    
    try:
        logger.info("🔍 DC Protocol Shadow Mode: Running daily reconciliation check...")
        
        # Get mismatch count
        result = db.execute(text("""
            WITH reconciliation AS (
                SELECT 
                    u.id,
                    COALESCE(u.earning_wallet, 0) as stored_earning,
                    COALESCE(e.earning_wallet, 0) as view_earning,
                    ABS(COALESCE(u.earning_wallet, 0) - COALESCE(e.earning_wallet, 0)) as earning_diff,
                    COALESCE(u.withdrawable_wallet, 0) as stored_withdrawable,
                    COALESCE(w.withdrawable_wallet, 0) as view_withdrawable,
                    ABS(COALESCE(u.withdrawable_wallet, 0) - COALESCE(w.withdrawable_wallet, 0)) as withdrawable_diff
                FROM "user" u
                LEFT JOIN user_earning_wallet_balance e ON u.id = e.user_id
                LEFT JOIN user_withdrawable_wallet_balance w ON u.id = w.user_id
                WHERE u.id != 'MNR00000000'
            )
            SELECT 
                COUNT(*) as total_users,
                COUNT(CASE WHEN earning_diff > 0.01 THEN 1 END) as earning_mismatches,
                COUNT(CASE WHEN withdrawable_diff > 0.01 THEN 1 END) as withdrawable_mismatches,
                COUNT(CASE WHEN earning_diff > 0.01 OR withdrawable_diff > 0.01 THEN 1 END) as total_mismatches,
                SUM(earning_diff) as total_earning_diff,
                SUM(withdrawable_diff) as total_withdrawable_diff
            FROM reconciliation
        """)).first()
        
        total_users = result.total_users
        total_mismatches = result.total_mismatches
        earning_mismatches = result.earning_mismatches
        withdrawable_mismatches = result.withdrawable_mismatches
        
        if total_mismatches > 0:
            # CRITICAL ALERT: Mismatches detected
            logger.error(
                f"🚨 DC PROTOCOL SHADOW MODE ALERT: {total_mismatches} mismatches detected!\n"
                f"   Total users: {total_users}\n"
                f"   Earning wallet mismatches: {earning_mismatches}\n"
                f"   Withdrawable wallet mismatches: {withdrawable_mismatches}\n"
                f"   Total earning difference: ₹{result.total_earning_diff:,.2f}\n"
                f"   Total withdrawable difference: ₹{result.total_withdrawable_diff:,.2f}\n"
                f"   ACTION REQUIRED: Review reconciliation report at /api/v1/dc-protocol/shadow-mode/reconciliation"
            )
            
            # Get sample mismatches for diagnosis
            sample_mismatches = db.execute(text("""
                SELECT 
                    u.id,
                    COALESCE(u.earning_wallet, 0) as stored_earning,
                    COALESCE(e.earning_wallet, 0) as view_earning,
                    COALESCE(u.withdrawable_wallet, 0) as stored_withdrawable,
                    COALESCE(w.withdrawable_wallet, 0) as view_withdrawable
                FROM "user" u
                LEFT JOIN user_earning_wallet_balance e ON u.id = e.user_id
                LEFT JOIN user_withdrawable_wallet_balance w ON u.id = w.user_id
                WHERE u.id != 'MNR00000000'
                    AND (ABS(COALESCE(u.earning_wallet, 0) - COALESCE(e.earning_wallet, 0)) > 0.01
                         OR ABS(COALESCE(u.withdrawable_wallet, 0) - COALESCE(w.withdrawable_wallet, 0)) > 0.01)
                LIMIT 5
            """)).fetchall()
            
            logger.error("   Sample mismatches:")
            for row in sample_mismatches:
                logger.error(
                    f"      {row.id}: Earning({row.stored_earning} vs {row.view_earning}), "
                    f"Withdrawable({row.stored_withdrawable} vs {row.view_withdrawable})"
                )
        else:
            # SUCCESS: 100% reconciliation
            reconciliation_rate = 100.0
            logger.info(
                f"✅ DC Protocol Shadow Mode: 100% reconciliation ({total_users}/{total_users} users)\n"
                f"   Earning wallets: All match ✅\n"
                f"   Withdrawable wallets: All match ✅\n"
                f"   Shadow Mode operating normally"
            )
        
    except Exception as e:
        logger.error(f"❌ DC Protocol Shadow Mode check failed: {e}")
    finally:
        db.close()

def auto_midnight_clockout():
    """
    DC Protocol: Auto clock-out for staff who forgot to clock out.
    Runs daily at 23:59 IST. Finds all StaffAttendance records for today
    where clock_in is set but clock_out is None, and auto-clocks them out at 23:59.
    Open breaks are closed first, then worked/break/overtime minutes are calculated.
    """
    from app.core.database import SessionLocal
    from app.models.staff_attendance import StaffAttendance, StaffAttendanceBreak, get_indian_date
    from app.models.base import get_indian_time

    db = SessionLocal()
    try:
        today = get_indian_date()
        # Build a fixed 23:59:00 datetime for today in IST
        from datetime import datetime as _dt, time as _time
        clockout_time = _dt.combine(today, _time(23, 59, 0))

        pending = db.query(StaffAttendance).filter(
            StaffAttendance.date == today,
            StaffAttendance.clock_in != None,
            StaffAttendance.clock_out == None
        ).all()

        count = 0
        for attendance in pending:
            # Close any open breaks
            open_breaks = db.query(StaffAttendanceBreak).filter(
                StaffAttendanceBreak.attendance_id == attendance.id,
                StaffAttendanceBreak.break_end == None
            ).all()
            for br in open_breaks:
                br.break_end = clockout_time
                if hasattr(br, 'calculate_duration'):
                    br.duration_minutes = br.calculate_duration()

            attendance.clock_out = clockout_time
            attendance.clock_out_device = {
                "auto": "midnight_clockout",
                "reason": "DC_AUTO_CLOCKOUT: System auto clock-out at 23:59 IST"
            }
            attendance.worked_minutes = attendance.calculate_worked_time()
            total_break_mins = sum(b.duration_minutes or 0 for b in attendance.breaks)
            attendance.break_minutes = total_break_mins
            attendance.overtime_minutes = attendance.calculate_overtime()
            attendance.update_status()
            existing_remarks = attendance.remarks or ''
            attendance.remarks = (
                (existing_remarks + ' | ' if existing_remarks else '') +
                'Auto clocked-out at 23:59 by system'
            )
            count += 1

        if count > 0:
            db.commit()
            logger.info(f"[DC_MIDNIGHT_CLOCKOUT] ✅ Auto clocked-out {count} staff for {today}")
        else:
            logger.info(f"[DC_MIDNIGHT_CLOCKOUT] No pending clock-outs for {today}")

    except Exception as e:
        logger.error(f"[DC_MIDNIGHT_CLOCKOUT] ❌ Failed: {e}")
        db.rollback()
    finally:
        db.close()


def run_daily_lead_sync(slot: str = '9am'):
    """
    Scheduled Google Sheets → CRM Lead Sync.
    DC Protocol Mar 2026: Runs at 9 AM, 12 PM, 3 PM, 6 PM IST.
    slot: '9am' | '12pm' | '3pm' | '6pm'
    Only syncs configs that have the matching slot enabled.
    """
    col_map = {'9am': 'sync_9am', '12pm': 'sync_12pm', '3pm': 'sync_3pm', '6pm': 'sync_6pm'}
    is_manual = slot == 'manual'
    col = col_map.get(slot, 'sync_9am')
    logger.info(f"[LEAD-SYNC] 🔄 Scheduled sync starting — slot: {slot}")
    db = SessionLocal()
    try:
        from sqlalchemy import text
        from app.services.sheets_leads_service import sync_all_tabs
        # Manual runs sync all active configs regardless of slot settings
        if is_manual:
            query = "SELECT id, name, sheet_url, source_tag, company_id FROM lead_sync_configs WHERE is_active=TRUE"
        else:
            query = f"SELECT id, name, sheet_url, source_tag, company_id FROM lead_sync_configs WHERE is_active=TRUE AND daily_sync_enabled=TRUE AND {col}=TRUE"
        configs = db.execute(text(query)).fetchall()

        if not configs:
            logger.info(f"[LEAD-SYNC] No configs for slot {slot} — skipping")
            return

        total_imported = 0
        for cfg in configs:
            cfg_id, name, sheet_url, source_tag, company_id = cfg
            logger.info(f"[LEAD-SYNC] Syncing: {name} ({slot})")
            try:
                result = sync_all_tabs(sheet_url, db, company_id=company_id or 1,
                                       source_tag=source_tag or 'Online - M')
                imported   = result.get('total_imported', 0)
                duplicates = result.get('total_skipped',  0)
                tabs_done  = len(result.get('tab_results', []))
                total_imported += imported
                import json as _json
                summary = {
                    'total_imported': imported, 'total_skipped': duplicates,
                    'tabs_synced': tabs_done, 'slot': slot,
                    'tab_results': [
                        {'tab': t.get('tab_name', ''), 'imported': t.get('imported', 0),
                         'skipped': t.get('skipped', 0), 'error': str(t.get('error', ''))[:200]}
                        for t in (result.get('tab_results') or [])
                    ]
                }
                res_json = _json.dumps(summary)
                db.execute(text("""
                    UPDATE lead_sync_configs
                    SET last_synced_at=NOW(), last_sync_result=CAST(:res AS jsonb),
                        total_imported=total_imported+:n, updated_at=NOW()
                    WHERE id=:id
                """), {'res': res_json, 'n': imported, 'id': cfg_id})
                db.execute(text("""
                    INSERT INTO lead_sync_history
                        (config_id, config_name, triggered_by, slot, tabs_synced, new_leads, duplicates, detail)
                    VALUES (:cid, :cname, 'auto', :slot, :tabs, :new, :dup, CAST(:det AS jsonb))
                """), {'cid': cfg_id, 'cname': name, 'slot': slot, 'tabs': tabs_done,
                       'new': imported, 'dup': duplicates, 'det': res_json})
                db.commit()
                logger.info(f"[LEAD-SYNC] ✅ {name}: {imported} new leads imported ({slot})")
            except Exception as e:
                db.rollback()
                logger.error(f"[LEAD-SYNC] ❌ {name} failed ({slot}): {e}")

        logger.info(f"[LEAD-SYNC] ✅ {slot} sync done — {total_imported} total new leads")
    except Exception as e:
        logger.error(f"[LEAD-SYNC] ❌ Sync error ({slot}): {e}")
    finally:
        db.close()


def run_staff_morning_reminders():
    """
    DC Protocol — WhatsApp: Send daily 8AM IST morning reminders to all active staff.
    Iterates every active employee record and calls send_staff_morning_reminder().
    Wrapped in a top-level try/except so scheduler cannot be disrupted.
    DC-FIX-DUPWA-001: PostgreSQL advisory lock (id=88890001) ensures only ONE of the
    4 uvicorn workers executes sends. Other workers log and return immediately.
    """
    try:
        from app.services.whatsapp_auto_service import send_staff_morning_reminder
        from app.models.staff import StaffEmployee
        from sqlalchemy import text
        db = SessionLocal()
        try:
            # DC-FIX-DUPWA-001: Acquire session-level advisory lock so only one worker runs
            lock_acquired = db.execute(
                text("SELECT pg_try_advisory_lock(88890001)")
            ).scalar()
            if not lock_acquired:
                logger.info("[MorningWA] Advisory lock held by another worker — skipping duplicate run")
                return
            from app.services.whatsapp_auto_service import send_staff_morning_leadership
            employees = db.query(StaffEmployee).filter(StaffEmployee.status == 'active').all()
            sent, skipped, errors = 0, 0, 0
            for emp in employees:
                try:
                    _role = getattr(emp, 'role', None)
                    _level = getattr(_role, 'hierarchy_level', 0) if _role else 0
                    _role_code = (getattr(_role, 'role_code', '') or '').lower() if _role else ''
                    _is_leadership = _level >= 90 or _role_code in ('ea', 'key_leadership', 'vgk4u')
                    if _is_leadership:
                        result = send_staff_morning_leadership(db, emp)
                    else:
                        result = send_staff_morning_reminder(db, emp)
                    if result and result.get('success'):
                        sent += 1
                    else:
                        skipped += 1
                except Exception as e_inner:
                    errors += 1
                    logger.error(f"[MorningWA] Error for employee {getattr(emp, 'id', '?')}: {e_inner}")
            logger.info(f"[MorningWA] Daily reminders done — sent={sent}, skipped={skipped}, errors={errors}")
        finally:
            db.close()
    except Exception as e:
        logger.error(f"[MorningWA] Fatal error in run_staff_morning_reminders: {e}")


def run_overdue_wa_alerts():
    """
    DC_WA_TEMPLATES_SEED_001 — Daily overdue alerts at 9AM IST (Mon-Sat).
    Sends: task overdue to assignee, KRA overdue to employee,
    overdue lead summary to sales staff, overdue lead team summary to leadership.
    """
    try:
        from sqlalchemy import text
        from app.models.staff import StaffEmployee
        from app.services.whatsapp_auto_service import send_auto_whatsapp
        db = SessionLocal()
        try:
            lock = db.execute(text("SELECT pg_try_advisory_lock(88890050)")).scalar()
            if not lock:
                return
            today_ist = __import__('datetime').datetime.utcnow() + __import__('datetime').timedelta(hours=5, minutes=30)
            today = today_ist.date()
            today_str = today_ist.strftime('%d %b %Y')

            # ── Task overdue alerts ────────────────────────────────────────────
            overdue_tasks = db.execute(text("""
                SELECT t.id, t.title, t.due_date, t.primary_assignee_id,
                       e.full_name, e.phone, e.id as emp_id,
                       c.full_name as creator_name
                FROM staff_tasks t
                JOIN staff_employees e ON e.id = t.primary_assignee_id
                LEFT JOIN staff_employees c ON c.id = t.created_by
                WHERE t.due_date < :today
                  AND t.status NOT IN ('completed','cancelled')
                  AND e.status = 'active'
                  AND e.phone IS NOT NULL
            """), {'today': today}).fetchall()

            for row in overdue_tasks:
                try:
                    overdue_days = (today - row.due_date).days if row.due_date else 1
                    send_auto_whatsapp(
                        db=db, event_key='task_overdue_alert', phone=str(row.phone),
                        context={
                            'name': row.full_name or '',
                            'task_title': row.title or '',
                            'due_date': row.due_date.strftime('%d %b %Y') if row.due_date else '',
                            'overdue_days': str(overdue_days),
                            'assigned_by': row.creator_name or 'Manager',
                        },
                        staff_id=row.emp_id,
                    )
                except Exception as _te:
                    logger.warning(f"[WA-OVERDUE] Task WA error for {row.emp_id}: {_te}")

            # ── KRA overdue alerts (yesterday's pending instances) ─────────────
            yesterday = (today_ist - __import__('datetime').timedelta(days=1)).date()
            overdue_kras = db.execute(text("""
                SELECT ki.id, ki.instance_date, ki.completion_status,
                       kt.title as kra_name, kt.target_value,
                       e.full_name, e.phone, e.id as emp_id
                FROM staff_kra_daily_instances ki
                JOIN staff_kra_templates kt ON kt.id = ki.kra_template_id
                JOIN staff_employees e ON e.id = ki.employee_id
                WHERE ki.instance_date = :yesterday
                  AND ki.completion_status IN ('pending','in_progress')
                  AND e.status = 'active'
                  AND e.phone IS NOT NULL
            """), {'yesterday': yesterday}).fetchall()

            for row in overdue_kras:
                try:
                    send_auto_whatsapp(
                        db=db, event_key='kra_overdue_alert', phone=str(row.phone),
                        context={
                            'name': row.full_name or '',
                            'kra_name': row.kra_name or '',
                            'kra_date': yesterday.strftime('%d %b %Y'),
                            'kra_target': str(row.target_value or ''),
                            'completion_status': row.completion_status.replace('_', ' ').title(),
                        },
                        staff_id=row.emp_id,
                    )
                except Exception as _ke:
                    logger.warning(f"[WA-OVERDUE] KRA WA error for {row.emp_id}: {_ke}")

            # ── Overdue leads — per sales staff ────────────────────────────────
            overdue_lead_staff = db.execute(text("""
                SELECT e.id, e.full_name, e.phone, COUNT(*) as cnt,
                       MIN(l.next_followup_date) as oldest_date,
                       (SELECT l2.name FROM crm_leads l2
                        WHERE (l2.telecaller_id=e.id OR l2.field_staff_id=e.id)
                          AND l2.next_followup_date IS NOT NULL
                          AND l2.next_followup_date < NOW()
                          AND l2.status NOT IN ('won','lost')
                        ORDER BY l2.next_followup_date ASC LIMIT 1) as oldest_name
                FROM crm_leads l
                JOIN staff_employees e ON (e.id=l.telecaller_id OR e.id=l.field_staff_id)
                WHERE l.next_followup_date < NOW()
                  AND l.status NOT IN ('won','lost')
                  AND e.status='active' AND e.phone IS NOT NULL
                GROUP BY e.id, e.full_name, e.phone
                HAVING COUNT(*) > 0
            """)).fetchall()

            for row in overdue_lead_staff:
                try:
                    oldest_str = row.oldest_date.strftime('%d %b %Y') if row.oldest_date else today_str
                    send_auto_whatsapp(
                        db=db, event_key='lead_overdue_sales', phone=str(row.phone),
                        context={
                            'name': row.full_name or '',
                            'count': str(row.cnt),
                            'oldest_lead': str(row.oldest_name or 'Lead'),
                            'overdue_since': oldest_str,
                        },
                        staff_id=row.id,
                    )
                except Exception as _le:
                    logger.warning(f"[WA-OVERDUE] Lead sales WA error for {row.id}: {_le}")

            # ── Overdue leads — leadership summary ─────────────────────────────
            lead_summary = db.execute(text("""
                SELECT COUNT(*) as total,
                       COUNT(DISTINCT COALESCE(l.telecaller_id, l.field_staff_id)) as staff_count,
                       MAX(DATE_PART('day', NOW() - l.next_followup_date)) as max_days
                FROM crm_leads l
                WHERE l.next_followup_date < NOW()
                  AND l.status NOT IN ('won','lost')
            """)).fetchone()

            if lead_summary and lead_summary.total and int(lead_summary.total) > 0:
                leaders = db.execute(text("""
                    SELECT e.full_name, e.phone, e.id
                    FROM staff_employees e
                    JOIN staff_roles r ON r.id = e.role_id
                    WHERE e.status='active' AND e.phone IS NOT NULL
                      AND (r.hierarchy_level >= 90
                           OR r.role_code IN ('ea','key_leadership','vgk4u'))
                """)).fetchall()
                for ldr in leaders:
                    try:
                        send_auto_whatsapp(
                            db=db, event_key='lead_overdue_leadership', phone=str(ldr.phone),
                            context={
                                'date': today_str,
                                'name': ldr.full_name or '',
                                'total_overdue': str(int(lead_summary.total)),
                                'staff_count': str(int(lead_summary.staff_count or 0)),
                                'max_days': str(int(lead_summary.max_days or 0)),
                            },
                            staff_id=ldr.id,
                        )
                    except Exception as _lde:
                        logger.warning(f"[WA-OVERDUE] Leadership WA error for {ldr.id}: {_lde}")

            logger.info(f"[WA-OVERDUE] 9AM overdue alerts dispatched — tasks={len(overdue_tasks)}, kras={len(overdue_kras)}, lead_staff={len(overdue_lead_staff)}")
        finally:
            db.close()
    except Exception as e:
        logger.error(f"[WA-OVERDUE] Fatal error: {e}")


def run_partner_agreement_reminders():
    """
    [DC-PARTNER-TERMS-001] Daily at 9:30AM IST — Send WhatsApp reminders for partner
    agreements expiring within reminder_days_before (default 90) days.
    Sends to: the partner (WhatsApp), and all VGK4U/EA/key-leadership staff.
    """
    try:
        db = SessionLocal()
        try:
            lock = db.execute(text("SELECT pg_try_advisory_lock(88890099)")).scalar()
            if not lock:
                return
            from app.services.whatsapp_auto_service import send_auto_whatsapp
            import datetime as _dt
            today = _dt.date.today()

            # Find partners whose end_date is approaching within their reminder_days_before window
            rows = db.execute(text("""
                SELECT id, partner_code, partner_name, phone, whatsapp_number,
                       partner_end_date, reminder_days_before
                FROM official_partners
                WHERE partner_end_date IS NOT NULL
                  AND is_active = TRUE
                  AND partner_end_date >= :today
                  AND partner_end_date <= :today + CAST(COALESCE(reminder_days_before, 90) AS INT) * INTERVAL '1 day'
            """), {"today": today}).fetchall()

            if not rows:
                logger.info("[DC-PARTNER-TERMS-001] No expiring partners today")
                return

            # Fetch leadership staff (VGK4U, EA, key_leadership roles, hierarchy_level >= 90)
            leaders = db.execute(text("""
                SELECT se.id, se.name, se.phone
                FROM staff_employees se
                JOIN staff_roles sr ON sr.id = se.role_id
                WHERE se.is_active = TRUE
                  AND (sr.role_code IN ('VGK4U','EA','RVZ','key_leadership')
                       OR se.hierarchy_level >= 90)
                  AND se.phone IS NOT NULL
            """)).fetchall()

            sent = 0
            for r in rows:
                days_left = (r.partner_end_date - today).days
                partner_phone = r.whatsapp_number or r.phone or ''
                ctx = {
                    "partner_name": r.partner_name,
                    "partner_code": r.partner_code,
                    "partner_end_date": r.partner_end_date.strftime("%d %b %Y"),
                    "days_left": days_left,
                }
                # Send to partner
                if partner_phone:
                    send_auto_whatsapp(db, 'partner_agreement_expiry_partner', partner_phone, ctx)
                    sent += 1
                # Send to all leadership staff
                for ldr in leaders:
                    if ldr.phone:
                        send_auto_whatsapp(db, 'partner_agreement_expiry_staff', ldr.phone, ctx)

            logger.info(f"[DC-PARTNER-TERMS-001] Expiry reminders sent for {len(rows)} partner(s), {sent} partner notifications")
        finally:
            db.close()
    except Exception as e:
        logger.error(f"[DC-PARTNER-TERMS-001] Fatal error in reminder job: {e}")


def run_lead_followup_reminders():
    """
    DC_WA_TEMPLATES_SEED_001 — Lead follow-up reminders at 8:30AM IST (Mon-Sat).
    Sends each telecaller/field staff a summary of leads due for follow-up today.
    """
    try:
        from sqlalchemy import text
        db = SessionLocal()
        try:
            lock = db.execute(text("SELECT pg_try_advisory_lock(88890051)")).scalar()
            if not lock:
                return
            from app.services.whatsapp_auto_service import send_auto_whatsapp
            today_ist = __import__('datetime').datetime.utcnow() + __import__('datetime').timedelta(hours=5, minutes=30)
            today_start = today_ist.replace(hour=0, minute=0, second=0, microsecond=0)
            today_end = today_ist.replace(hour=23, minute=59, second=59)
            # Convert IST to UTC for DB comparison
            today_start_utc = today_start - __import__('datetime').timedelta(hours=5, minutes=30)
            today_end_utc = today_end - __import__('datetime').timedelta(hours=5, minutes=30)

            followup_staff = db.execute(text("""
                SELECT e.id, e.full_name, e.phone, COUNT(*) as cnt,
                       (SELECT l2.name FROM crm_leads l2
                        WHERE (l2.telecaller_id=e.id OR l2.field_staff_id=e.id)
                          AND l2.next_followup_date BETWEEN :start AND :end
                          AND l2.status NOT IN ('won','lost')
                        ORDER BY l2.next_followup_date ASC LIMIT 1) as next_name,
                       (SELECT l2.phone FROM crm_leads l2
                        WHERE (l2.telecaller_id=e.id OR l2.field_staff_id=e.id)
                          AND l2.next_followup_date BETWEEN :start AND :end
                          AND l2.status NOT IN ('won','lost')
                        ORDER BY l2.next_followup_date ASC LIMIT 1) as next_phone
                FROM crm_leads l
                JOIN staff_employees e ON (e.id=l.telecaller_id OR e.id=l.field_staff_id)
                WHERE l.next_followup_date BETWEEN :start AND :end
                  AND l.status NOT IN ('won','lost')
                  AND e.status='active' AND e.phone IS NOT NULL
                GROUP BY e.id, e.full_name, e.phone
            """), {'start': today_start_utc, 'end': today_end_utc}).fetchall()

            for row in followup_staff:
                try:
                    send_auto_whatsapp(
                        db=db, event_key='lead_followup_reminder', phone=str(row.phone),
                        context={
                            'name': row.full_name or '',
                            'count': str(row.cnt),
                            'next_lead': str(row.next_name or 'Lead'),
                            'phone': str(row.next_phone or '—'),
                        },
                        staff_id=row.id,
                    )
                except Exception as _fe:
                    logger.warning(f"[WA-FOLLOWUP] WA error for {row.id}: {_fe}")

            logger.info(f"[WA-FOLLOWUP] 8:30AM follow-up reminders dispatched — {len(followup_staff)} staff")
        finally:
            db.close()
    except Exception as e:
        logger.error(f"[WA-FOLLOWUP] Fatal error: {e}")


def init_scheduler():
    """
    Initialize APScheduler with midnight job in IST timezone
    UPDATED: Added thread pool executor and PostgreSQL job store for background job queue
    """
    global scheduler
    
    if scheduler is not None:
        logger.warning("Scheduler already initialized")
        return scheduler
    
    # Configure thread pool executor for async background jobs
    from apscheduler.executors.pool import ThreadPoolExecutor
    from apscheduler.jobstores.memory import MemoryJobStore

    # DC Protocol (May 2026): Reduced from 20 → 8 concurrent threads.
    # Each background job opens a DB connection. 20 threads could saturate the
    # Neon pool (15 max) and starve incoming API requests. 8 threads leaves
    # enough pool slots for simultaneous user traffic.
    executors = {
        'default': ThreadPoolExecutor(8),   # 8 concurrent background jobs (was 20)
    }

    # DC Protocol Mar 2026: MemoryJobStore replaces SQLAlchemyJobStore
    # SQLAlchemyJobStore opened its own connection pool without pool_pre_ping —
    # Neon PostgreSQL drops idle SSL connections after ~5min, causing repeated
    # "SSL connection has been closed unexpectedly" errors every 5 minutes.
    # All jobs are re-registered from code on each server start, so persistence
    # across restarts is not needed.
    job_stores = {
        'default': MemoryJobStore()
    }

    # Job defaults (max instances, coalescing, etc.)
    job_defaults = {
        'coalesce': False,  # Don't combine missed job executions
        'max_instances': 3,  # Max 3 instances of same job
        'misfire_grace_time': 60  # 60 seconds grace period for missed jobs
    }

    scheduler = BackgroundScheduler(
        executors=executors,
        jobstores=job_stores,
        job_defaults=job_defaults,
        timezone='Asia/Kolkata'
    )

    logger.info("✅ APScheduler initialized with thread pool executor and MemoryJobStore")
    
    # DC Protocol: Refresh materialized wallet views once daily at 1:30 AM IST
    # Runs after midnight income calculation completes (~12:00 AM job).
    # On-demand refresh still happens inside wallet_balance_service when needed.
    scheduler.add_job(
        refresh_materialized_wallet_views,
        trigger=CronTrigger(hour=1, minute=30, timezone='Asia/Kolkata'),
        id='wallet_view_refresh',
        name='DC Protocol: Refresh Wallet Views (Daily)',
        replace_existing=True
    )
    
    # Add leg metrics cache refresh job (runs every day at 11:30 PM IST)
    scheduler.add_job(
        refresh_leg_metrics_cache,
        trigger=CronTrigger(hour=23, minute=30, timezone='Asia/Kolkata'),
        id='leg_metrics_cache_refresh',
        name='Refresh Leg Metrics Cache',
        replace_existing=True
    )

    # DC Protocol: Auto clock-out unclosed attendance at 23:59 IST daily
    # Any staff still clocked in (clock_in set, clock_out None) get auto-clocked out at 23:59
    scheduler.add_job(
        auto_midnight_clockout,
        trigger=CronTrigger(hour=23, minute=59, timezone='Asia/Kolkata'),
        id='midnight_auto_clockout',
        name='DC Protocol: Auto Clock-Out Unclosed Attendance (23:59 IST)',
        replace_existing=True
    )

    # Add midnight job (runs every day at 12:00 AM IST)
    scheduler.add_job(
        calculate_previous_day_incomes,
        trigger=CronTrigger(hour=0, minute=0, timezone='Asia/Kolkata'),
        id='midnight_income_calculation',
        name='Calculate Previous Day Incomes',
        replace_existing=True
    )
    
    # Add monthly field allowance job (runs 1st day of month at 12:00 AM IST)
    scheduler.add_job(
        calculate_monthly_field_allowances,
        trigger=CronTrigger(day=1, hour=0, minute=0, timezone='Asia/Kolkata'),
        id='monthly_field_allowance_calculation',
        name='Calculate Monthly Field Allowances',
        replace_existing=True
    )
    
    # DC Protocol Phase 1.7: REMOVED daily wallet sync job (replaced by materialized views)
    # Legacy behavior: Transferred earning → withdrawable wallet daily at 3:00 AM
    # New behavior: Materialized views compute both wallets independently from pending_income
    # No manual "transfer" needed - status change automatically moves income between views
    
    # DC Protocol Phase 1.4: Shadow Mode reconciliation check (runs every day at 6:00 AM IST)
    scheduler.add_job(
        check_shadow_mode_reconciliation,
        trigger=CronTrigger(hour=6, minute=0, timezone='Asia/Kolkata'),
        id='dc_shadow_mode_reconciliation',
        name='DC Protocol: Shadow Mode Reconciliation Check',
        replace_existing=True
    )
    
    # DC Protocol Phase 1.11: Auto-approve stuck income (runs every day at 6:30 AM IST)
    # Before withdrawal generation to unstick blocked income and create withdrawals
    scheduler.add_job(
        auto_approve_stuck_income,
        trigger=CronTrigger(hour=6, minute=30, timezone='Asia/Kolkata'),
        id='auto_approve_stuck_income',
        name='Auto-Approve Stuck Income (Phase 1.11)',
        replace_existing=True
    )
    
    # Add automatic withdrawal generation job (runs Mon-Sat at 7:00 AM IST)
    scheduler.add_job(
        generate_automatic_withdrawals,
        trigger=CronTrigger(day_of_week='mon-sat', hour=7, minute=0, timezone='Asia/Kolkata'),
        id='automatic_withdrawal_generation',
        name='Automatic Withdrawal Generation',
        replace_existing=True
    )
    
    # DC_CREDIT_001: Update overdue status for payables/receivables (runs daily at 1:00 AM IST)
    scheduler.add_job(
        update_credit_overdue_status,
        trigger=CronTrigger(hour=1, minute=0, timezone='Asia/Kolkata'),
        id='credit_overdue_status_update',
        name='DC_CREDIT_001: Update Overdue Status',
        replace_existing=True
    )

    # Marketplace Google Sheets auto-sync — DISABLED (manual-only per user preference)
    # Trigger manually from Stock Items page → "Sync from Google Sheet" button.
    # scheduler.add_job(
    #     auto_sync_marketplace_sheets,
    #     trigger=CronTrigger(hour=5, minute=0, timezone='Asia/Kolkata'),
    #     id='marketplace_sheets_auto_sync',
    #     name='Marketplace: Daily Google Sheets Sync',
    #     replace_existing=True
    # )

    # DC Protocol: Scheduler Retry Dispatcher (durable retry for failed APScheduler enqueues)
    # Runs every 5 minutes to retry jobs with scheduler_status='failed'
    from app.core.scheduler_retry_dispatcher import init_retry_dispatcher_schedule
    init_retry_dispatcher_schedule(scheduler)

    # ── Lead Sync — 4 daily slots (IST) ───────────────────────────────────────
    for _slot, _hour in [('9am', 9), ('12pm', 12), ('3pm', 15), ('6pm', 18)]:
        scheduler.add_job(
            run_daily_lead_sync,
            CronTrigger(hour=_hour, minute=0, timezone='Asia/Kolkata'),
            id=f'lead_sync_{_slot}',
            name=f'Lead Sync {_slot.upper()} IST',
            replace_existing=True,
            misfire_grace_time=3600,
            kwargs={'slot': _slot}
        )
    logger.info("   📊 Lead sync scheduled at 9AM, 12PM, 3PM, 6PM IST")

    # WhatsApp DC Protocol: Staff daily morning reminder at 8:00 AM IST (Mon-Sat)
    scheduler.add_job(
        run_staff_morning_reminders,
        trigger=CronTrigger(day_of_week='mon-sat', hour=8, minute=0, timezone='Asia/Kolkata'),
        id='wa_staff_morning_reminder',
        name='WhatsApp: Staff Daily Morning Reminder (8AM IST)',
        replace_existing=True,
        misfire_grace_time=600
    )
    logger.info("   📱 WhatsApp morning reminders scheduled at 8AM IST Mon-Sat")

    # [DC-PARTNER-TERMS-001] Partner agreement expiry reminders at 9:30 AM IST daily
    scheduler.add_job(
        run_partner_agreement_reminders,
        trigger=CronTrigger(hour=9, minute=30, timezone='Asia/Kolkata'),
        id='partner_agreement_reminders',
        name='Partner Agreement Expiry Reminders (9:30AM IST)',
        replace_existing=True,
        misfire_grace_time=600,
    )
    logger.info("   📋 Partner agreement expiry reminders scheduled at 9:30AM IST daily")

    # DC_WA_TEMPLATES_SEED_001: WA Lead follow-up reminders at 8:30 AM IST Mon-Sat
    scheduler.add_job(
        run_lead_followup_reminders,
        trigger=CronTrigger(day_of_week='mon-sat', hour=8, minute=30, timezone='Asia/Kolkata'),
        id='wa_lead_followup_reminders',
        name='WhatsApp: Lead Follow-up Reminders (8:30AM IST)',
        replace_existing=True,
        misfire_grace_time=600,
    )
    logger.info("   📱 WhatsApp lead follow-up reminders scheduled at 8:30AM IST Mon-Sat")

    # DC_WA_TEMPLATES_SEED_001: WA Overdue alerts at 9:00 AM IST Mon-Sat
    scheduler.add_job(
        run_overdue_wa_alerts,
        trigger=CronTrigger(day_of_week='mon-sat', hour=9, minute=0, timezone='Asia/Kolkata'),
        id='wa_overdue_alerts',
        name='WhatsApp: Overdue Task/KRA/Lead Alerts (9AM IST)',
        replace_existing=True,
        misfire_grace_time=600,
    )
    logger.info("   📱 WhatsApp overdue alerts scheduled at 9AM IST Mon-Sat")

    # [DC-POINTS-REFILL] Safety-net: daily at 2:00 AM IST — catch any missed auto-refills
    scheduler.add_job(
        run_vgk_points_refill_safety_net,
        trigger=CronTrigger(hour=2, minute=0, timezone='Asia/Kolkata'),
        id='vgk_points_refill_safety_net',
        name='VGK Points: Auto-Refill Safety Net (2AM IST)',
        replace_existing=True,
        misfire_grace_time=3600,
    )
    logger.info("   💎 VGK points auto-refill safety net scheduled at 2AM IST")

    # DC-OPERATOR-CALLS: MyOperator periodic log sync (every 30 minutes)
    try:
        from app.services.operator_call_sync import run_operator_call_sync_job
        scheduler.add_job(
            run_operator_call_sync_job,
            trigger=CronTrigger(minute='*/30', timezone='Asia/Kolkata'),
            id='myoperator_log_sync',
            name='MyOperator: Periodic Call Log Sync (every 30 min)',
            replace_existing=True,
            misfire_grace_time=300,
            max_instances=1,
        )
        logger.info("   📞 MyOperator log sync scheduled every 30 minutes")
    except Exception as _op_e:
        logger.warning(f"[DC-OPERATOR-CALLS] Could not schedule sync job: {_op_e}")

    # DC-OPERATOR-CALLS: Daily full backfill at 9 AM IST (last 30 days) to fill all gaps
    try:
        from app.services.operator_call_sync import run_operator_call_daily_backfill_job
        scheduler.add_job(
            run_operator_call_daily_backfill_job,
            trigger=CronTrigger(hour=9, minute=0, timezone='Asia/Kolkata'),
            id='myoperator_log_daily_backfill',
            name='MyOperator: Daily Call Log Backfill (9AM IST, last 30 days)',
            replace_existing=True,
            misfire_grace_time=3600,
            max_instances=1,
        )
        logger.info("   📞 MyOperator daily backfill (30 days) scheduled at 9 AM IST")
    except Exception as _op_e2:
        logger.warning(f"[DC-OPERATOR-CALLS] Could not schedule daily backfill job: {_op_e2}")

    # DC_TRAINING_SYNC_001: Sync training videos from Google Doc every hour
    try:
        from app.services.training_sync import sync_training_videos_from_gdoc
        scheduler.add_job(
            sync_training_videos_from_gdoc,
            trigger=CronTrigger(minute=0, timezone='Asia/Kolkata'),
            id='training_videos_sync',
            name='Training Videos: Sync from Google Doc (Hourly)',
            replace_existing=True,
            misfire_grace_time=600,
            max_instances=1,
        )
        logger.info("   🎬 Training videos sync scheduled every hour (top of hour)")
    except Exception as _tv_sched_e:
        logger.warning(f"[DC_TRAINING_SYNC_001] Could not schedule sync job: {_tv_sched_e}")

    scheduler.start()
    logger.info("✅ APScheduler initialized with IST timezone - All jobs scheduled in Asia/Kolkata time")
    logger.info(f"   📅 Next midnight run: {scheduler.get_job('midnight_income_calculation').next_run_time}")
    
    return scheduler

def shutdown_scheduler():
    """Shutdown APScheduler gracefully"""
    global scheduler
    
    if scheduler is not None:
        scheduler.shutdown()
        scheduler = None
        logger.info("✅ APScheduler shut down")

def get_scheduler():
    """Get the scheduler instance"""
    return scheduler

def enqueue_background_job(job_func, job_id: str, args=None, kwargs=None):
    """
    Enqueue a one-time background job for immediate execution
    Used for async image compression, video processing, etc.
    
    Args:
        job_func: Function to execute
        job_id: Unique job identifier
        args: Positional arguments for job_func
        kwargs: Keyword arguments for job_func
    
    Returns:
        Job instance
    """
    global scheduler
    
    if scheduler is None:
        logger.error("Scheduler not initialized! Call init_scheduler() first.")
        raise RuntimeError("Scheduler not initialized")
    
    # Add one-time job for immediate execution
    job = scheduler.add_job(
        job_func,
        id=job_id,
        args=args or [],
        kwargs=kwargs or {},
        replace_existing=True,  # Replace if job with same ID exists
        misfire_grace_time=300  # 5 minutes grace period
    )
    
    logger.info(f"[BACKGROUND JOB] Enqueued: {job_id}")
    
    return job



# DC_CREDIT_001: Scheduled job to update overdue status for payables/receivables
def update_credit_overdue_status():
    """
    Update overdue status for payables and receivables
    DC: Runs daily at 1:00 AM IST to mark items as overdue
    """
    from app.core.database import SessionLocal
    from app.services.staff_accounts_service import AccountsCreditService
    
    logger.info("🔄 DC_CREDIT_001: Starting overdue status update...")
    
    db = SessionLocal()
    try:
        updated_count = AccountsCreditService.update_overdue_status(db)
        logger.info(f"✅ DC_CREDIT_001: Updated {updated_count} items to OVERDUE status")
    except Exception as e:
        logger.error(f"❌ DC_CREDIT_001: Failed to update overdue status: {e}")
    finally:
        db.close()
