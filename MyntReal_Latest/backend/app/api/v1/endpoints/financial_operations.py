"""
Financial Operations API Endpoints for FastAPI
Handles Reference System income calculations, transactions, and financial management
"""

from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, date

from app.core.database import get_db
from app.core.security import get_current_user, get_current_user_hybrid, get_current_mnr_user_from_hybrid, require_finance_admin, require_admin
from app.models.user import User
from app.services.reference_service import ReferenceService
from app.services.user_service import UserService
from app.services.wallet_balance_service import get_withdrawable_wallet

router = APIRouter()

@router.get("/{user_id}/comprehensive")
async def get_comprehensive_income_report(
    user_id: str,
    month: Optional[str] = Query(default=None, description="Month in YYYY-MM format"),
    current_user = Depends(get_current_user_hybrid),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get comprehensive income report for all 4 income streams
    PRODUCTION RESET: Returns structure with ALL amounts = ₹0
    """
    # DC Protocol: Menu-based access control - any authenticated staff has full access
    if current_user.id != user_id and not hasattr(current_user, 'emp_code'):
        raise HTTPException(status_code=403, detail="Access denied")
    
    if not month:
        month = datetime.now().strftime("%Y-%m")
    
    reference_service = ReferenceService(db)
    
    # Get comprehensive income summary
    income_summary = reference_service.get_comprehensive_income_summary(user_id, month)
    
    if "error" in income_summary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=income_summary["error"]
        )
    
    return {
        "success": True,
        "income_report": income_summary
    }

@router.get("/{user_id}/actual-paid")
async def get_actual_paid_income(
    user_id: str,
    month: Optional[str] = Query(default=None, description="Month in YYYY-MM format"),
    current_user = Depends(get_current_user_hybrid),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get actual paid income from pending_income table
    Shows what has actually been calculated and paid to the user
    """
    from app.models.transaction import PendingIncome
    from sqlalchemy import func, and_, extract
    
    # DC Protocol: Menu-based access control - any authenticated staff has full access
    if current_user.id != user_id and not hasattr(current_user, 'emp_code'):
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Get user
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    # Parse month parameter
    if not month:
        month = datetime.now().strftime("%Y-%m")
    
    year, month_num = map(int, month.split('-'))
    
    # Query pending_income
    paid_incomes = db.query(PendingIncome).filter(
        and_(
            PendingIncome.user_id == user_id,
            extract('year', PendingIncome.business_date) == year,
            extract('month', PendingIncome.business_date) == month_num
        )
    ).all()
    
    # Aggregate by income type
    direct_total = sum(float(pi.gross_amount) for pi in paid_incomes if pi.income_type == 'Direct Referral')
    matching_total = sum(float(pi.gross_amount) for pi in paid_incomes if pi.income_type == 'Matching Referral')
    ved_total = sum(float(pi.gross_amount) for pi in paid_incomes if pi.income_type == 'Ved Income')
    guru_total = sum(float(pi.gross_amount) for pi in paid_incomes if pi.income_type == 'Guru Dakshina')
    
    total_gross = direct_total + matching_total + ved_total + guru_total
    tds_total = sum(float(pi.tds_deduction) for pi in paid_incomes)
    admin_total = sum(float(pi.admin_deduction) for pi in paid_incomes)
    net_total = sum(float(pi.net_amount) for pi in paid_incomes)
    
    # Count referrals and pairs
    direct_count = len([pi for pi in paid_incomes if pi.income_type == 'Direct Referral'])
    matching_pairs = sum(float(pi.pairs_matched or 0) for pi in paid_incomes if pi.income_type == 'Matching Referral')
    
    return {
        "success": True,
        "income_report": {
            "user_id": user_id,
            "period": month,
            "direct_referral_income": direct_total,
            "direct_referral_count": direct_count,
            "matching_referral_income": matching_total,
            "matching_pairs": int(matching_pairs),
            "ved_income": ved_total,
            "ved_members_count": 0,
            "guru_dakshina": guru_total,
            "total_monthly_income": total_gross,
            "tds_deduction": tds_total,
            "admin_deduction": admin_total,
            "net_monthly_income": net_total,
            "withdrawal_wallet": float(get_withdrawable_wallet(db, user_id)),
            "upgraded_wallet": float(user.upgrade_wallet_balance or 0),
            "generated_at": datetime.now().isoformat()
        }
    }

@router.get("/{user_id}/direct-referral")
async def get_direct_referral_income(
    user_id: str,
    month: Optional[str] = Query(default=None, description="Month in YYYY-MM format"),
    current_user = Depends(get_current_user_hybrid),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get detailed direct referral income breakdown
    PRODUCTION RESET: Returns structure with ALL amounts = ₹0
    """
    # DC Protocol: Menu-based access control - any authenticated staff has full access
    if current_user.id != user_id and not hasattr(current_user, 'emp_code'):
        raise HTTPException(status_code=403, detail="Access denied")
    
    if not month:
        month = datetime.now().strftime("%Y-%m")
    
    reference_service = ReferenceService(db)
    
    # Get direct referral income details
    direct_income = reference_service.calculate_direct_referral_income(user_id, month)
    
    if "error" in direct_income:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=direct_income["error"]
        )
    
    return {
        "success": True,
        "direct_referral_income": direct_income
    }

@router.get("/{user_id}/matching-referral")
async def get_matching_referral_income(
    user_id: str,
    month: Optional[str] = Query(default=None, description="Month in YYYY-MM format"),
    current_user = Depends(get_current_user_hybrid),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get detailed matching referral income (binary pairs)
    PRODUCTION RESET: Returns structure with ALL amounts = ₹0
    """
    # DC Protocol: Menu-based access control - any authenticated staff has full access
    if current_user.id != user_id and not hasattr(current_user, 'emp_code'):
        raise HTTPException(status_code=403, detail="Access denied")
    
    if not month:
        month = datetime.now().strftime("%Y-%m")
    
    reference_service = ReferenceService(db)
    
    # Get matching referral income details
    matching_income = reference_service.calculate_matching_referral_income(user_id, month)
    
    if "error" in matching_income:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=matching_income["error"]
        )
    
    return {
        "success": True,
        "matching_referral_income": matching_income
    }

@router.get("/{user_id}/ved-income")
async def get_ved_income(
    user_id: str,
    month: Optional[str] = Query(default=None, description="Month in YYYY-MM format"),
    start_date: Optional[str] = Query(default=None, description="Start date in YYYY-MM-DD format (for lifetime data)"),
    end_date: Optional[str] = Query(default=None, description="End date in YYYY-MM-DD format (for lifetime data)"),
    current_user = Depends(get_current_user_hybrid),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get Ved income distribution details - DC PROTOCOL COMPLIANT
    Queries pending_income table directly (single source of truth)
    Shows ALL Ved Income records when no dates provided
    Supports custom date range for filtering
    """
    from app.models.transaction import PendingIncome
    from sqlalchemy import and_, func
    
    # DC Protocol: Menu-based access control - any authenticated staff has full access
    if current_user.id != user_id and not hasattr(current_user, 'emp_code'):
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Get user
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Build date filter
    date_filters = [PendingIncome.user_id == user_id, PendingIncome.income_type == 'Ved Income']
    
    if start_date and end_date:
        # Custom date range - inclusive of end date (full day)
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")
        # Include entire end date by going to start of next day (exclusive upper bound)
        end_of_day = end + timedelta(days=1)
        date_filters.append(PendingIncome.business_date >= start)
        date_filters.append(PendingIncome.business_date < end_of_day)
    elif month and month != "1970-01":
        # Specific month - inclusive of entire last day
        start = datetime.strptime(f"{month}-01", "%Y-%m-%d")
        if month == datetime.now().strftime("%Y-%m"):
            # Current month - use now() as upper bound
            end = datetime.now()
            date_filters.append(PendingIncome.business_date >= start)
            date_filters.append(PendingIncome.business_date <= end)
        else:
            # Past month - use exclusive upper bound (start of next month)
            next_month = start.replace(month=start.month + 1 if start.month < 12 else 1,
                                      year=start.year if start.month < 12 else start.year + 1)
            date_filters.append(PendingIncome.business_date >= start)
            date_filters.append(PendingIncome.business_date < next_month)
    # else: No date filter = show ALL records (lifetime)
    
    # DC PROTOCOL: Query pending_income table directly (single source of truth)
    ved_income_records = db.query(PendingIncome).filter(
        and_(*date_filters)
    ).order_by(PendingIncome.business_date.desc()).all()
    
    # Get related user details (Ved Team members who generated this income)
    member_ids = [record.related_user_id for record in ved_income_records if record.related_user_id]
    members = db.query(User).filter(User.id.in_(member_ids)).all() if member_ids else []
    member_dict = {m.id: m for m in members}
    
    # Format response - INCLUDE ALL RECORDS even if related user is missing/removed
    members_data = []
    total_gross = 0.0
    total_net = 0.0
    
    for record in ved_income_records:
        # Always include record in totals (even if related user is missing)
        total_gross += float(record.gross_amount or 0)
        total_net += float(record.net_amount or 0)
        
        # Get member info (or use placeholder if missing/removed)
        member = member_dict.get(record.related_user_id)
        member_id = record.related_user_id or "UNKNOWN"
        member_name = member.name if member else f"[Removed User {member_id}]"
        
        members_data.append({
            "member_id": member_id,
            "name": member_name,
            "from_date": record.business_date.strftime("%d/%m/%Y") if record.business_date else "",
            "to_date": record.business_date.strftime("%d/%m/%Y") if record.business_date else "",
            "total_amount": float(record.gross_amount or 0)
        })
    
    return {
        "success": True,
        "ved_income": {
            "members": members_data,
            "total_amount": total_gross,
            "total_net": total_net,
            "count": len(ved_income_records)
        }
    }

@router.get("/{user_id}/guru-dakshina")
async def get_guru_dakshina(
    user_id: str,
    month: Optional[str] = Query(default=None, description="Month in YYYY-MM format"),
    current_user = Depends(get_current_user_hybrid),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get Guru Dakshina (leadership bonus) details
    Preserves Flask Guru Dakshina calculation logic
    """
    # DC Protocol: Menu-based access control - any authenticated staff has full access
    if current_user.id != user_id and not hasattr(current_user, 'emp_code'):
        raise HTTPException(status_code=403, detail="Access denied")
    
    if not month:
        month = datetime.now().strftime("%Y-%m")
    
    reference_service = ReferenceService(db)
    
    # Get Guru Dakshina details
    guru_dakshina = reference_service.calculate_guru_dakshina(user_id, month)
    
    if "error" in guru_dakshina:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=guru_dakshina["error"]
        )
    
    return {
        "success": True,
        "guru_dakshina": guru_dakshina
    }

@router.get("/{user_id}/direct-referral-transactions")
async def get_direct_referral_transactions(
    user_id: str,
    request: Request,
    start_date: Optional[str] = Query(default=None, description="Start date in YYYY-MM-DD format"),
    end_date: Optional[str] = Query(default=None, description="End date in YYYY-MM-DD format"),
    current_user = Depends(get_current_user_hybrid),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get transaction-wise Direct Referral earnings with user details
    Shows all individual direct referral records from pending_income
    DC Protocol: Accepts "me" as user_id to auto-resolve from MNR session
    """
    from app.models.transaction import PendingIncome
    from app.models.staff import StaffEmployee
    from app.core.security import SecurityManager
    from sqlalchemy import and_, func
    
    target_user_id = user_id
    
    if user_id == "me":
        # DC Protocol: Check both cookies (web) and Authorization header (mobile)
        session_token = request.cookies.get("session_token") or request.cookies.get("session")
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            session_token = auth_header.replace("Bearer ", "")
        
        if session_token:
            try:
                payload = SecurityManager.verify_token(session_token)
                if payload and payload.get("sub"):
                    mnr_id = str(payload["sub"])
                    if mnr_id.startswith("MNR"):
                        mnr_user = SecurityManager.get_user_by_id(db, mnr_id)
                        if mnr_user:
                            if getattr(mnr_user, 'account_locked', False):
                                raise HTTPException(status_code=status.HTTP_423_LOCKED, detail="Account is locked")
                            is_red_coupon = getattr(mnr_user, 'is_red_coupon', False)
                            red_coupon_locked = getattr(mnr_user, 'red_coupon_locked', False)
                            if is_red_coupon and red_coupon_locked:
                                raise HTTPException(status_code=status.HTTP_423_LOCKED, detail="Account locked due to Red Coupon status")
                            target_user_id = mnr_id
                        else:
                            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="MNR user not found")
                    else:
                        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid MNR session")
                else:
                    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="MNR session required")
            except HTTPException:
                raise
            except Exception:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired MNR session")
        else:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="MNR session required")
    else:
        # DC Protocol: Menu-based access control - any authenticated staff has full access
        if isinstance(current_user, StaffEmployee):
            pass
        elif str(current_user.id) != user_id and not hasattr(current_user, 'emp_code'):
            raise HTTPException(status_code=403, detail="Access denied")
    
    query = db.query(
        PendingIncome.id,
        PendingIncome.business_date,
        PendingIncome.gross_amount,
        PendingIncome.related_user_id,
        PendingIncome.payment_status,
        PendingIncome.verification_status,
        User.name.label('referred_name')
    ).join(
        User, PendingIncome.related_user_id == User.id, isouter=True
    ).filter(
        PendingIncome.user_id == target_user_id,
        PendingIncome.income_type == 'Direct Referral'
    )
    
    if start_date and end_date:
        query = query.filter(and_(
            func.date(PendingIncome.business_date) >= start_date,
            func.date(PendingIncome.business_date) <= end_date
        ))
    
    results = query.order_by(PendingIncome.business_date.desc()).all()
    
    user = db.query(User).filter(User.id == target_user_id).first()
    
    transactions = []
    for row in results:
        v_status = row.verification_status or 'Pending'
        is_paid = v_status.lower() == 'completed'
        bdate = row.business_date.date() if hasattr(row.business_date, 'date') and callable(row.business_date.date) else row.business_date
        if bdate and bdate < date(2026, 2, 12):
            display_status = 'Cleared'
            is_paid = True
        elif v_status == 'Staff Validated':
            display_status = 'Staff Validated'
        elif v_status == 'Completed':
            display_status = 'Completed'
        else:
            display_status = 'Pending Validation'
        transactions.append({
            "member_id": target_user_id,
            "member_name": user.name if user else "",
            "referred_user_id": row.related_user_id or "",
            "referred_user_name": row.referred_name or "",
            "from_date": row.business_date.strftime('%d/%m/%Y') if row.business_date else "",
            "to_date": row.business_date.strftime('%d/%m/%Y') if row.business_date else "",
            "total_amount": float(row.gross_amount or 0),
            "is_paid": is_paid,
            "display_status": display_status,
            "payment_status": row.payment_status or "PENDING",
            "verification_status": v_status
        })
    
    # Get total historical earnings from earned_total field
    total_historical = float(user.earned_total or 0) if user else 0
    
    return {
        "success": True,
        "data": {
            "member_id": target_user_id,
            "member_name": user.name if user else "",
            "transactions": transactions,
            "total_count": len(transactions),
            "total_amount": total_historical  # Show historical total from earned_total field
        }
    }

@router.get("/{user_id}/matching-referral-transactions")
async def get_matching_referral_transactions(
    user_id: str,
    request: Request,
    start_date: Optional[str] = Query(default=None, description="Start date in YYYY-MM-DD format"),
    end_date: Optional[str] = Query(default=None, description="End date in YYYY-MM-DD format"),
    current_user = Depends(get_current_user_hybrid),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get individual pair-wise Matching Referral transactions
    Shows ALL historical matching records with ACTUAL activation dates (not generation dates)
    NOTE: October 20th reset does NOT apply here - users see complete transaction history
    DC Protocol: Accepts "me" as user_id to auto-resolve from MNR session
    """
    from app.models.transaction import PendingIncome
    from app.models.staff import StaffEmployee
    from app.core.security import SecurityManager
    from sqlalchemy import and_, func
    
    target_user_id = user_id
    
    if user_id == "me":
        # DC Protocol: Check both cookies (web) and Authorization header (mobile)
        session_token = request.cookies.get("session_token") or request.cookies.get("session")
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            session_token = auth_header.replace("Bearer ", "")
        
        if session_token:
            try:
                payload = SecurityManager.verify_token(session_token)
                if payload and payload.get("sub"):
                    mnr_id = str(payload["sub"])
                    if mnr_id.startswith("MNR"):
                        mnr_user = SecurityManager.get_user_by_id(db, mnr_id)
                        if mnr_user:
                            if getattr(mnr_user, 'account_locked', False):
                                raise HTTPException(status_code=status.HTTP_423_LOCKED, detail="Account is locked")
                            is_red_coupon = getattr(mnr_user, 'is_red_coupon', False)
                            red_coupon_locked = getattr(mnr_user, 'red_coupon_locked', False)
                            if is_red_coupon and red_coupon_locked:
                                raise HTTPException(status_code=status.HTTP_423_LOCKED, detail="Account locked due to Red Coupon status")
                            target_user_id = mnr_id
                        else:
                            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="MNR user not found")
                    else:
                        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid MNR session")
                else:
                    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="MNR session required")
            except HTTPException:
                raise
            except Exception:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired MNR session")
        else:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="MNR session required")
    else:
        # DC Protocol: Menu-based access control - any authenticated staff has full access
        if isinstance(current_user, StaffEmployee):
            pass
        elif str(current_user.id) != user_id and not hasattr(current_user, 'emp_code'):
            raise HTTPException(status_code=403, detail="Access denied")
    
    # Get matching referral records
    query = db.query(PendingIncome).filter(
        PendingIncome.user_id == target_user_id,
        PendingIncome.income_type == 'Matching Referral'
    )
    
    if start_date and end_date:
        query = query.filter(and_(
            func.date(PendingIncome.business_date) >= start_date,
            func.date(PendingIncome.business_date) <= end_date
        ))
    
    records = query.order_by(PendingIncome.business_date.asc()).all()
    
    user = db.query(User).filter(User.id == target_user_id).first()
    reference_service = ReferenceService(db)
    team_counts = reference_service.get_team_counts(target_user_id)
    
    transactions = []
    per_pair_amount = 2000.0
    
    # Get first matching record for 2:1 or 1:2 detection
    first_matching_record = db.query(PendingIncome).filter(
        PendingIncome.user_id == target_user_id,
        PendingIncome.income_type == 'Matching Referral',
        PendingIncome.gross_amount > 0
    ).order_by(PendingIncome.business_date.asc()).first()
    
    # Get actual contributors from both legs
    from sqlalchemy import text
    
    def get_leg_contributors(target_id: str, side: str):
        """Get actual team members with points from specified leg
        DC Protocol Fix: Use same criteria as cache (package_points > 0 only)
        to ensure count consistency between dashboard and transaction list
        """
        team_query = db.execute(text("""
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
            ORDER BY COALESCE(u.activation_date, u.registration_date)
        """), {"user_id": target_id, "side": side})
        return [{"id": row[0], "name": row[1], "points": float(row[2]), "activation_date": row[3]} for row in team_query]
    
    left_contributors = get_leg_contributors(target_user_id, 'left')
    right_contributors = get_leg_contributors(target_user_id, 'right')
    
    # DC Protocol: Pre-calculate daily income totals for ceiling check
    # ₹50,000 daily limit applies to Ved Income + Matching Referral combined
    daily_income_query = db.execute(text("""
        SELECT 
            DATE(business_date) as income_date,
            SUM(CASE WHEN income_type IN ('Ved Income', 'Matching Referral') THEN gross_amount ELSE 0 END) as daily_total
        FROM pending_income
        WHERE user_id = :user_id
          AND income_type IN ('Ved Income', 'Matching Referral')
        GROUP BY DATE(business_date)
    """), {"user_id": target_user_id})
    daily_income_map = {row[0]: float(row[1]) for row in daily_income_query.fetchall()}
    
    # DC Protocol Fix: Use POINTS-based pair calculation (consistent with scheduler)
    # total_pairs = MIN(sum_left_points, sum_right_points) — matches get_leg_points_sql logic
    left_total_points = sum(c['points'] for c in left_contributors)
    right_total_points = sum(c['points'] for c in right_contributors)
    total_pairs = int(min(left_total_points, right_total_points))
    
    # Calculate how many pairs have been PAID (from pending_income records)
    # DC Protocol: Exclude Exempted/Informational records - they use zero-point contributors
    # NOT from the left_contributors/right_contributors lists, so must not reduce pending count
    total_paid_pairs = sum(int(r.pairs_matched or 0) for r in records
                          if r.verification_status not in ('Exempted', 'Informational'))
    
    # Track which contributors have been used
    left_index = 0
    right_index = 0
    global_pair_number = 0
    
    # DC Protocol: Generate rows for ALL pairs (paid + pending)
    # First handle paid pairs from pending_income records
    for record in records:
        is_first_matching_record = (first_matching_record and record.id == first_matching_record.id)
        pairs_matched = int(record.pairs_matched or 0)
        # DC Protocol: Track ceiling applied status per record
        record_ceiling_applied = getattr(record, 'ceiling_applied', False) or False
        record_ceiling_excess = float(getattr(record, 'ceiling_excess_amount', 0) or 0)
        
        if pairs_matched == 0 and record.verification_status == 'Informational':
            global_pair_number += 1
            date_str = record.business_date.strftime('%d/%m/%Y') if record.business_date else ''
            transactions.append({
                'pair_number': global_pair_number,
                'member_id': target_user_id,
                'name': user.name if user else '',
                'date': date_str,
                'from_date': date_str,
                'to_date': date_str,
                'pairs_matched': 0,
                'left_user_id': '',
                'left_user_name': '',
                'left_points': 0,
                'right_user_id': '',
                'right_user_name': '',
                'right_points': 0,
                'left_contributors': [],
                'right_contributors': [],
                'total_amount': 0,
                'gross_per_pair': 0,
                'guru_dakshina': 0,
                'admin_tds': 0,
                'net_per_pair': 0,
                'pair_format': 'N/A',
                'ceiling_applied': False,
                'ceiling_excess': 0,
                'is_paid': False,
                'display_status': 'Informational',
                'verification_status': 'Informational',
                'is_informational': True,
                'notes': record.notes or 'Network activity (0-point members)',
                'business_date': record.business_date.isoformat() if record.business_date else None,
                'pending_income_id': record.id,
            })
            continue
        
        if record.verification_status == 'Exempted':
            snapshot = record.matching_contributors_snapshot or {}
            exempt_left_zero = snapshot.get('left_zero_point_members', [])
            exempt_right_zero = snapshot.get('right_zero_point_members', [])
            date_str = record.business_date.strftime('%d/%m/%Y') if record.business_date else ''
            
            for ep in range(pairs_matched):
                global_pair_number += 1
                left_member = exempt_left_zero[ep] if ep < len(exempt_left_zero) else None
                right_member = exempt_right_zero[ep] if ep < len(exempt_right_zero) else None
                left_zp = [left_member] if left_member else []
                right_zp = [right_member] if right_member else []
                transactions.append({
                    'pair_number': global_pair_number,
                    'member_id': target_user_id,
                    'name': user.name if user else '',
                    'date': date_str,
                    'from_date': date_str,
                    'to_date': date_str,
                    'pairs_matched': 1,
                    'left_user_id': left_member.get('user_id', '') if left_member else '',
                    'left_user_name': left_member.get('name', '') if left_member else '',
                    'left_points': 0,
                    'right_user_id': right_member.get('user_id', '') if right_member else '',
                    'right_user_name': right_member.get('name', '') if right_member else '',
                    'right_points': 0,
                    'left_contributors': left_zp,
                    'right_contributors': right_zp,
                    'total_amount': 0,
                    'gross_per_pair': 0,
                    'guru_dakshina': 0,
                    'admin_tds': 0,
                    'net_per_pair': 0,
                    'pair_format': 'N/A',
                    'ceiling_applied': False,
                    'ceiling_excess': 0,
                    'is_paid': False,
                    'display_status': 'Exempted',
                    'verification_status': 'Exempted',
                    'is_exempted': True,
                    'notes': record.notes or 'Zero-point member matched (Star/Loyal/Welcome)',
                    'business_date': record.business_date.isoformat() if record.business_date else None,
                    'pending_income_id': record.id,
                })
            continue
        
        if pairs_matched == 0:
            continue
        
        # Determine if first pair should be 2:1 or 1:2
        # Use total leg POINTS (not counts) to determine first pair format
        first_pair_format = "1:1"
        first_pair_left_count = 1
        first_pair_right_count = 1
        
        if is_first_matching_record:
            # Calculate leg points AT THE TIME of ELIGIBILITY (when 1:1 direct was met)
            # Find when the second direct referral was activated (eligibility date)
            eligibility_date_query = db.execute(text("""
                SELECT activation_date
                FROM "user"
                WHERE referrer_id = :user_id
                  AND activation_date IS NOT NULL
                ORDER BY activation_date ASC
                LIMIT 1 OFFSET 1
            """), {"user_id": target_user_id})
            
            eligibility_row = eligibility_date_query.fetchone()
            eligibility_date = eligibility_row[0] if eligibility_row else record.business_date
            
            # Query historical leg balance at the time of eligibility
            historical_leg_balance = db.execute(text("""
                WITH RECURSIVE leg_team AS (
                    SELECT p.child_id, p.side, 1 as level
                    FROM placement p
                    WHERE p.parent_id = :user_id
                    UNION ALL
                    SELECT p.child_id, lt.side, lt.level + 1
                    FROM placement p
                    INNER JOIN leg_team lt ON p.parent_id = lt.child_id
                    WHERE lt.level < 200
                )
                SELECT 
                    lt.side,
                    COALESCE(SUM(u.package_points), 0) as total_points
                FROM leg_team lt
                JOIN "user" u ON u.id = lt.child_id
                WHERE u.activation_date IS NOT NULL
                  AND u.activation_date <= :eligibility_date
                  AND u.package_points > 0
                GROUP BY lt.side
            """), {"user_id": target_user_id, "eligibility_date": eligibility_date})
            
            leg_balance = {row[0]: float(row[1]) for row in historical_leg_balance}
            left_total_points = leg_balance.get('left', 0)
            right_total_points = leg_balance.get('right', 0)
            
            if left_total_points > right_total_points:
                first_pair_left_count = 2
                first_pair_right_count = 1
                first_pair_format = "2:1"
            elif right_total_points > left_total_points:
                first_pair_left_count = 1
                first_pair_right_count = 2
                first_pair_format = "1:2"
            # If equal, keep 1:1 format
        
        # Create individual rows for each pair
        date_str = record.business_date.strftime('%d/%m/%Y') if record.business_date else ''
        
        for pair_idx in range(pairs_matched):
            global_pair_number += 1
            is_very_first_pair = (is_first_matching_record and pair_idx == 0)
            
            # For first pair, use 2:1 or 1:2 format; for rest, use 1:1
            if is_very_first_pair:
                left_count = first_pair_left_count
                right_count = first_pair_right_count
                pair_format = first_pair_format
            else:
                left_count = 1
                right_count = 1
                pair_format = "1:1"
            
            # Get left contributors for this pair
            left_ids = []
            left_names = []
            left_points_list = []
            left_activation_dates = []
            
            for i in range(left_count):
                if left_index < len(left_contributors):
                    contributor = left_contributors[left_index]
                    left_ids.append(contributor['id'])
                    left_names.append(contributor['name'])
                    left_points_list.append(contributor['points'])
                    left_activation_dates.append(contributor['activation_date'])
                    left_index += 1
            
            # Get right contributors for this pair
            right_ids = []
            right_names = []
            right_points_list = []
            right_activation_dates = []
            
            for i in range(right_count):
                if right_index < len(right_contributors):
                    contributor = right_contributors[right_index]
                    right_ids.append(contributor['id'])
                    right_names.append(contributor['name'])
                    right_points_list.append(contributor['points'])
                    right_activation_dates.append(contributor['activation_date'])
                    right_index += 1
            
            # DC Protocol: Use income record's business_date for paid pairs
            # This ensures member page dates match Income Management dates
            # Activation date kept as supplementary info for context
            all_activation_dates = [d for d in (left_activation_dates + right_activation_dates) if d is not None]
            activation_date_display = max(all_activation_dates).strftime('%d/%m/%Y') if all_activation_dates else None
            pair_date = record.business_date
            pair_date_str = date_str
            
            # DC Protocol: Calculate ceiling_applied per pair based on pair formation date
            # ₹50,000 daily ceiling applies to Ved Income + Matching Referral combined
            pair_ceiling_applied = False
            if pair_date:
                pair_date_only = pair_date.date() if hasattr(pair_date, 'date') else pair_date
                daily_total = daily_income_map.get(pair_date_only, 0)
                # If daily total exceeds ₹50,000, ceiling was applied on this day
                pair_ceiling_applied = daily_total >= 50000
            
            # Create one transaction row for this individual pair
            # NOTE: No October 20th filtering here - show ALL historical transactions
            transactions.append({
                "member_id": target_user_id,
                "name": user.name if user else "",
                "pair_number": global_pair_number,
                "left_user_id": ", ".join(left_ids) if left_ids else "",
                "left_user_name": ", ".join(left_names) if left_names else "",
                "left_points": sum(left_points_list) if left_points_list else 0,
                "right_user_id": ", ".join(right_ids) if right_ids else "",
                "right_user_name": ", ".join(right_names) if right_names else "",
                "right_points": sum(right_points_list) if right_points_list else 0,
                "from_date": pair_date_str,
                "to_date": pair_date_str,
                "total_amount": per_pair_amount,  # Each pair = ₹2,000
                "pair_format": pair_format,
                "ceiling_applied": pair_ceiling_applied,  # DC Protocol: Per-pair ceiling check
                "ceiling_excess": 0,  # Excess tracked at daily level, not per pair
                "is_paid": True,  # Paid from pending_income
                "activation_date": activation_date_display
            })
    
    # DC Protocol Fix: Add PENDING pairs (activations not yet processed by midnight scheduler)
    # These pairs exist based on current tree state but haven't generated income yet
    # Guard against negative count if users deactivate after income was generated
    pending_pairs_count = max(0, total_pairs - total_paid_pairs)
    if pending_pairs_count > 0:
        for _ in range(pending_pairs_count):
            global_pair_number += 1
            
            # Get next left contributor
            left_id = ""
            left_name = ""
            left_pts = 0
            left_act_date = None
            if left_index < len(left_contributors):
                contributor = left_contributors[left_index]
                left_id = contributor['id']
                left_name = contributor['name']
                left_pts = contributor['points']
                left_act_date = contributor.get('activation_date')
                left_index += 1
            
            # Get next right contributor
            right_id = ""
            right_name = ""
            right_pts = 0
            right_act_date = None
            if right_index < len(right_contributors):
                contributor = right_contributors[right_index]
                right_id = contributor['id']
                right_name = contributor['name']
                right_pts = contributor['points']
                right_act_date = contributor.get('activation_date')
                right_index += 1
            
            # DC Protocol: Use LATEST activation date from contributors (same logic as paid pairs)
            pending_activation_dates = [d for d in [left_act_date, right_act_date] if d is not None]
            if pending_activation_dates:
                pending_pair_date = max(pending_activation_dates)
                pending_date_str = pending_pair_date.strftime('%d/%m/%Y') if hasattr(pending_pair_date, 'strftime') else str(pending_pair_date)
            else:
                from datetime import datetime
                pending_date_str = datetime.now().strftime('%d/%m/%Y')
            
            transactions.append({
                "member_id": target_user_id,
                "name": user.name if user else "",
                "pair_number": global_pair_number,
                "left_user_id": left_id,
                "left_user_name": left_name,
                "left_points": left_pts,
                "right_user_id": right_id,
                "right_user_name": right_name,
                "right_points": right_pts,
                "from_date": pending_date_str,
                "to_date": pending_date_str,
                "total_amount": per_pair_amount,
                "pair_format": "1:1",
                "ceiling_applied": False,
                "ceiling_excess": 0,
                "is_paid": False
            })
    
    # Get total historical earnings from earned_total field
    total_historical = float(user.earned_total or 0) if user else 0
    
    return {
        "success": True,
        "data": {
            "member_id": target_user_id,
            "member_name": user.name if user else "",
            "current_left": team_counts.get('left_count', 0),
            "current_right": team_counts.get('right_count', 0),
            "left_points": left_total_points,
            "right_points": right_total_points,
            "total_pairs_by_points": total_pairs,
            "paid_pairs": total_paid_pairs,
            "pending_pairs": max(0, total_pairs - total_paid_pairs),
            "transactions": transactions,
            "total_count": len(transactions),
            "total_amount": total_historical
        }
    }

@router.get("/{user_id}/guru-dakshina-transactions")
async def get_guru_dakshina_transactions(
    user_id: str,
    request: Request,
    start_date: Optional[str] = Query(default=None, description="Start date in YYYY-MM-DD format"),
    end_date: Optional[str] = Query(default=None, description="End date in YYYY-MM-DD format"),
    current_user = Depends(get_current_user_hybrid),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Get transaction-wise Guru Dakshina earnings from referrals
    DC Protocol: Accepts "me" as user_id to auto-resolve from MNR session
    """
    from app.models.transaction import PendingIncome
    from app.models.staff import StaffEmployee
    from app.core.security import SecurityManager
    from sqlalchemy import and_, func
    
    target_user_id = user_id
    
    if user_id == "me":
        # DC Protocol: Check both cookies (web) and Authorization header (mobile)
        session_token = request.cookies.get("session_token") or request.cookies.get("session")
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            session_token = auth_header.replace("Bearer ", "")
        
        if session_token:
            try:
                payload = SecurityManager.verify_token(session_token)
                if payload and payload.get("sub"):
                    mnr_id = str(payload["sub"])
                    if mnr_id.startswith("MNR"):
                        mnr_user = SecurityManager.get_user_by_id(db, mnr_id)
                        if mnr_user:
                            if getattr(mnr_user, 'account_locked', False):
                                raise HTTPException(status_code=status.HTTP_423_LOCKED, detail="Account is locked")
                            is_red_coupon = getattr(mnr_user, 'is_red_coupon', False)
                            red_coupon_locked = getattr(mnr_user, 'red_coupon_locked', False)
                            if is_red_coupon and red_coupon_locked:
                                raise HTTPException(status_code=status.HTTP_423_LOCKED, detail="Account locked due to Red Coupon status")
                            target_user_id = mnr_id
                        else:
                            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="MNR user not found")
                    else:
                        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid MNR session")
                else:
                    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="MNR session required")
            except HTTPException:
                raise
            except Exception:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired MNR session")
        else:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="MNR session required")
    else:
        # DC Protocol: Menu-based access control - any authenticated staff has full access
        if isinstance(current_user, StaffEmployee):
            pass
        elif str(current_user.id) != user_id and not hasattr(current_user, 'emp_code'):
            raise HTTPException(status_code=403, detail="Access denied")
    
    query = db.query(
        PendingIncome.id,
        PendingIncome.business_date,
        PendingIncome.gross_amount,
        PendingIncome.related_user_id,
        PendingIncome.payment_status,
        PendingIncome.verification_status,
        User.name.label('for_name')
    ).join(
        User, PendingIncome.related_user_id == User.id, isouter=True
    ).filter(
        PendingIncome.user_id == target_user_id,
        PendingIncome.income_type == 'Guru Dakshina'
    )
    
    if start_date and end_date:
        query = query.filter(and_(
            func.date(PendingIncome.business_date) >= start_date,
            func.date(PendingIncome.business_date) <= end_date
        ))
    
    results = query.order_by(PendingIncome.business_date.desc()).all()
    
    user = db.query(User).filter(User.id == target_user_id).first()
    
    transactions = []
    for row in results:
        v_status = row.verification_status or 'Pending'
        is_paid = v_status.lower() == 'completed'
        bdate = row.business_date.date() if hasattr(row.business_date, 'date') and callable(row.business_date.date) else row.business_date
        if bdate and bdate < date(2026, 2, 12):
            display_status = 'Cleared'
            is_paid = True
        elif v_status == 'Staff Validated':
            display_status = 'Staff Validated'
        elif v_status == 'Completed':
            display_status = 'Completed'
        else:
            display_status = 'Pending Validation'
        transactions.append({
            "member_id": target_user_id,
            "name": user.name if user else "",
            "for_member_id": row.related_user_id or "",
            "for_name": row.for_name or "",
            "from_date": row.business_date.strftime('%d/%m/%Y') if row.business_date else "",
            "to_date": row.business_date.strftime('%d/%m/%Y') if row.business_date else "",
            "total_amount": float(row.gross_amount or 0),
            "is_paid": is_paid,
            "display_status": display_status,
            "payment_status": row.payment_status or "PENDING",
            "verification_status": v_status
        })
    
    # Get total historical earnings from earned_total field
    total_historical = float(user.earned_total or 0) if user else 0
    
    return {
        "success": True,
        "data": {
            "member_id": target_user_id,
            "member_name": user.name if user else "",
            "transactions": transactions,
            "total_count": len(transactions),
            "total_amount": total_historical  # Show historical total from earned_total field
        }
    }

@router.get("/{user_id}/ved-income-transactions")
async def get_ved_income_transactions(
    user_id: str,
    request: Request,
    start_date: Optional[str] = Query(default=None, description="Start date in YYYY-MM-DD format"),
    end_date: Optional[str] = Query(default=None, description="End date in YYYY-MM-DD format"),
    current_user = Depends(get_current_user_hybrid),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    DC PROTOCOL COMPLIANT: Get Ved Income transactions from pending_income table ONLY
    Single source of truth - no Transaction table queries
    Returns all Ved income earned by this user with proper date filtering
    DC Protocol: Accepts "me" as user_id to auto-resolve from MNR session
    """
    from app.models.transaction import PendingIncome
    from app.models.staff import StaffEmployee
    from app.core.security import SecurityManager
    from sqlalchemy import and_, func
    
    target_user_id = user_id
    
    if user_id == "me":
        # DC Protocol: Check both cookies (web) and Authorization header (mobile)
        session_token = request.cookies.get("session_token") or request.cookies.get("session")
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            session_token = auth_header.replace("Bearer ", "")
        
        if session_token:
            try:
                payload = SecurityManager.verify_token(session_token)
                if payload and payload.get("sub"):
                    mnr_id = str(payload["sub"])
                    if mnr_id.startswith("MNR"):
                        mnr_user = SecurityManager.get_user_by_id(db, mnr_id)
                        if mnr_user:
                            if getattr(mnr_user, 'account_locked', False):
                                raise HTTPException(status_code=status.HTTP_423_LOCKED, detail="Account is locked")
                            is_red_coupon = getattr(mnr_user, 'is_red_coupon', False)
                            red_coupon_locked = getattr(mnr_user, 'red_coupon_locked', False)
                            if is_red_coupon and red_coupon_locked:
                                raise HTTPException(status_code=status.HTTP_423_LOCKED, detail="Account locked due to Red Coupon status")
                            target_user_id = mnr_id
                        else:
                            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="MNR user not found")
                    else:
                        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid MNR session")
                else:
                    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="MNR session required")
            except HTTPException:
                raise
            except Exception:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired MNR session")
        else:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="MNR session required")
    else:
        # DC Protocol: Menu-based access control - any authenticated staff has full access
        if isinstance(current_user, StaffEmployee):
            pass
        elif str(current_user.id) != user_id and not hasattr(current_user, 'emp_code'):
            raise HTTPException(status_code=403, detail="Access denied")
    
    user = db.query(User).filter(User.id == target_user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    # DC PROTOCOL: Query ONLY pending_income table (single source of truth)
    pending_query = db.query(PendingIncome).filter(
        PendingIncome.user_id == target_user_id,
        PendingIncome.income_type == 'Ved Income'
    )
    
    # Apply date filters with proper inclusive end date handling
    if start_date and end_date:
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(end_date, "%Y-%m-%d")
        # Include entire end date by using exclusive upper bound (next day)
        end_of_day = end_dt + timedelta(days=1)
        pending_query = pending_query.filter(and_(
            PendingIncome.business_date >= start_dt,
            PendingIncome.business_date < end_of_day
        ))
    
    pending_results = pending_query.order_by(PendingIncome.business_date.desc()).all()
    
    # Get related user details for member names
    member_ids = [r.related_user_id for r in pending_results if r.related_user_id]
    members = db.query(User).filter(User.id.in_(member_ids)).all() if member_ids else []
    member_dict = {m.id: m for m in members}
    
    # Format transactions - INCLUDE ALL RECORDS even if related user is missing
    transactions = []
    total_ved_income = 0
    
    for record in pending_results:
        business_date = record.business_date
        
        # Always include in totals (even if related user is missing)
        total_ved_income += float(record.gross_amount or 0)
        
        # Get member info (or use placeholder if missing/removed)
        member = member_dict.get(record.related_user_id)
        member_name = member.name if member else f"[Removed User]"
        
        # DC Protocol: Track ceiling applied status
        record_ceiling_applied = getattr(record, 'ceiling_applied', False) or False
        record_ceiling_excess = float(getattr(record, 'ceiling_excess_amount', 0) or 0)
        
        v_status = record.verification_status or 'Pending'
        is_paid = v_status.lower() == 'completed'
        bdate_check = business_date.date() if hasattr(business_date, 'date') and callable(business_date.date) else business_date
        if bdate_check and bdate_check < date(2026, 2, 12):
            display_status = 'Cleared'
            is_paid = True
        elif v_status == 'Staff Validated':
            display_status = 'Staff Validated'
        elif v_status == 'Completed':
            display_status = 'Completed'
        else:
            display_status = 'Pending Validation'
        transactions.append({
            "for_member_id": record.related_user_id or "",
            "for_member_name": member_name,
            "from_date": business_date.strftime('%d/%m/%Y') if business_date else "",
            "to_date": business_date.strftime('%d/%m/%Y') if business_date else "",
            "gross_amount": float(record.gross_amount or 0),
            "admin_charges": float(record.admin_deduction or 0),
            "tds_deduction": float(record.tds_deduction or 0),
            "net_amount": float(record.net_amount or 0),
            "is_paid": is_paid,
            "display_status": display_status,
            "payment_status": getattr(record, 'payment_status', None) or "PENDING",
            "verification_status": v_status,
            "business_date": business_date.isoformat() if business_date else None,
            "ceiling_applied": record_ceiling_applied,
            "ceiling_excess": record_ceiling_excess if record_ceiling_applied else 0
        })
    
    return {
        "success": True,
        "data": {
            "transactions": transactions,
            "total_count": len(transactions),
            "total_ved_income": round(total_ved_income)
        }
    }

@router.get("/{user_id}/comprehensive-day-wise")
async def get_comprehensive_day_wise_income(
    user_id: str,
    request: Request,
    start_date: Optional[str] = Query(default=None, description="Start date in YYYY-MM-DD format"),
    end_date: Optional[str] = Query(default=None, description="End date in YYYY-MM-DD format"),
    month: Optional[str] = Query(default=None, description="Filter by month in YYYY-MM format"),
    limit: int = Query(default=30, ge=1, le=365, description="Number of days to retrieve"),
    current_user = Depends(get_current_user_hybrid),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get comprehensive day-wise income breakdown showing all 4 income types per day
    Supports date range, month, and limit filters
    Shows all historical income data
    
    DC Protocol: Accepts "me" as user_id to auto-resolve from MNR session
    When user_id is "me", prioritizes MNR session over staff session for dual-login scenarios
    """
    from app.models.transaction import PendingIncome
    from app.models.staff import StaffEmployee
    from app.core.security import SecurityManager
    from sqlalchemy import func, desc, and_, or_
    from datetime import datetime, timedelta
    
    target_user_id = user_id
    
    if user_id == "me":
        # DC Protocol: When "me" is requested, extract MNR user directly from session cookie
        # This handles dual-login scenarios where both staff and MNR sessions exist
        # Mirrors get_current_mnr_user_from_hybrid validation pattern
        session_token = request.cookies.get("session_token") or request.cookies.get("session")
        if session_token:
            try:
                payload = SecurityManager.verify_token(session_token)
                if payload and payload.get("sub"):
                    mnr_id = str(payload["sub"])
                    if mnr_id.startswith("MNR"):
                        # Load user from DB to enforce account-lock checks
                        mnr_user = SecurityManager.get_user_by_id(db, mnr_id)
                        if mnr_user:
                            # Enforce account-lock check (DC Protocol security)
                            if getattr(mnr_user, 'account_locked', False):
                                raise HTTPException(
                                    status_code=status.HTTP_423_LOCKED,
                                    detail="Account is locked"
                                )
                            # Enforce red-coupon lock check
                            is_red_coupon = getattr(mnr_user, 'is_red_coupon', False)
                            red_coupon_locked = getattr(mnr_user, 'red_coupon_locked', False)
                            if is_red_coupon and red_coupon_locked:
                                raise HTTPException(
                                    status_code=status.HTTP_423_LOCKED,
                                    detail="Account locked due to Red Coupon status"
                                )
                            target_user_id = mnr_id
                        else:
                            raise HTTPException(
                                status_code=status.HTTP_401_UNAUTHORIZED,
                                detail="MNR user not found. Please login again."
                            )
                    else:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Invalid MNR session. Please login with your MNR account."
                        )
                else:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="MNR session required to view earnings."
                    )
            except HTTPException:
                raise
            except Exception:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid or expired MNR session. Please login again."
                )
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="MNR session required. Please login with your MNR account."
            )
    else:
        # DC Protocol: Menu-based access control - any authenticated staff has full access
        if isinstance(current_user, StaffEmployee):
            pass  # Staff can query any user
        elif str(current_user.id) != user_id and not hasattr(current_user, 'emp_code'):
            raise HTTPException(status_code=403, detail="Access denied")
    
    # Build date filters
    filters = [
        PendingIncome.user_id == target_user_id
    ]
    
    if start_date and end_date:
        filters.append(and_(
            func.date(PendingIncome.business_date) >= start_date,
            func.date(PendingIncome.business_date) <= end_date
        ))
    elif month:
        filters.append(func.to_char(PendingIncome.business_date, 'YYYY-MM') == month)
    
    # DC PROTOCOL FIX: Query pending_income for amounts (use distinct counts for points separately)
    results = db.query(
        func.date(PendingIncome.business_date).label('date'),
        PendingIncome.income_type,
        func.sum(PendingIncome.gross_amount).label('gross_total'),
        func.sum(PendingIncome.net_amount).label('net_total'),
        func.sum(PendingIncome.gurudakshina_deduction).label('gurudakshina_deduction_total'),
        func.sum(PendingIncome.admin_deduction).label('admin_deduction_total'),
        func.sum(PendingIncome.tds_deduction).label('tds_deduction_total')
    ).filter(*filters).group_by(
        func.date(PendingIncome.business_date),
        PendingIncome.income_type
    ).order_by(desc(func.date(PendingIncome.business_date))).all()
    
    # DC PROTOCOL: Get DISTINCT counts for Ved Income (unique Ved members per date)
    ved_points_query = db.query(
        func.date(PendingIncome.business_date).label('date'),
        func.count(func.distinct(PendingIncome.related_user_id)).label('unique_ved_count')
    ).filter(
        PendingIncome.user_id == target_user_id,
        PendingIncome.income_type == 'Ved Income',
        PendingIncome.related_user_id.isnot(None)
    )
    
    # Apply same date filters to Ved points query
    if start_date and end_date:
        ved_points_query = ved_points_query.filter(and_(
            func.date(PendingIncome.business_date) >= start_date,
            func.date(PendingIncome.business_date) <= end_date
        ))
    elif month:
        ved_points_query = ved_points_query.filter(
            func.to_char(PendingIncome.business_date, 'YYYY-MM') == month
        )
    
    ved_points_results = ved_points_query.group_by(
        func.date(PendingIncome.business_date)
    ).all()
    
    # DC PROTOCOL: Get DISTINCT counts for Direct Referral (unique activations per date)
    direct_points_query = db.query(
        func.date(PendingIncome.business_date).label('date'),
        func.count(func.distinct(PendingIncome.related_user_id)).label('unique_direct_count')
    ).filter(
        PendingIncome.user_id == target_user_id,
        PendingIncome.income_type == 'Direct Referral',
        PendingIncome.related_user_id.isnot(None)
    )
    
    # Apply same date filters to Direct points query
    if start_date and end_date:
        direct_points_query = direct_points_query.filter(and_(
            func.date(PendingIncome.business_date) >= start_date,
            func.date(PendingIncome.business_date) <= end_date
        ))
    elif month:
        direct_points_query = direct_points_query.filter(
            func.to_char(PendingIncome.business_date, 'YYYY-MM') == month
        )
    
    direct_points_results = direct_points_query.group_by(
        func.date(PendingIncome.business_date)
    ).all()
    
    # Create lookup maps for distinct counts (DC Protocol: Single source of truth)
    ved_points_map = {row.date.isoformat(): int(row.unique_ved_count) for row in ved_points_results if row.date}
    direct_points_map = {row.date.isoformat(): int(row.unique_direct_count) for row in direct_points_results if row.date}
    
    # Organize data by date
    date_map = {}
    for row in results:
        date_str = row.date.isoformat() if row.date else None
        if not date_str:
            continue
            
        if date_str not in date_map:
            date_map[date_str] = {
                'date': date_str,
                'direct_referral': 0,
                'direct_points': 0,
                'matching_referral': 0,
                'matching_points': 0,
                'ved_income': 0,
                'ved_points': 0,
                'earned_guru_dakshina': 0,
                'gd_points': '2%',
                'other_adjustments': 0,  # DC Protocol: Manual adjustments, bonanza, etc.
                'gross_earning': 0,
                'paid_guru_dakshina': 0,
                'tds_admin': 0,
                'final_earning': 0
            }
        
        gross = float(row.gross_total or 0)
        net = float(row.net_total or 0)
        guru_ded = float(row.gurudakshina_deduction_total or 0)
        admin_ded = float(row.admin_deduction_total or 0)
        tds_ded = float(row.tds_deduction_total or 0)
        
        # DC PROTOCOL: Map income types using DISTINCT counts for points (single source of truth)
        if row.income_type == 'Direct Referral':
            date_map[date_str]['direct_referral'] += gross
            # DC FIX: Use distinct count from direct_points_map (unique activations)
            date_map[date_str]['direct_points'] = direct_points_map.get(date_str, 0)
        elif row.income_type == 'Matching Referral':
            date_map[date_str]['matching_referral'] += gross
            # Matching points = gross / 2000 (each pair = ₹2,000) - CORRECT calculation
            date_map[date_str]['matching_points'] += int(gross / 2000) if gross > 0 else 0
        elif row.income_type == 'Ved Income':
            date_map[date_str]['ved_income'] += gross
            # DC FIX: Use distinct count from ved_points_map (unique Ved members)
            date_map[date_str]['ved_points'] = ved_points_map.get(date_str, 0)
        elif row.income_type == 'Guru Dakshina':
            date_map[date_str]['earned_guru_dakshina'] += gross
            # GD points always 2% (rate) - CORRECT as-is
        else:
            # DC Protocol: Catch all other income types (Manual Adjustments, Bonanza, etc.)
            date_map[date_str]['other_adjustments'] += gross
        
        date_map[date_str]['gross_earning'] += gross
        # Don't sum individual deductions - we'll calculate from day total below
    
    # DC PROTOCOL SIMPLIFICATION: Calculate deductions from DAY TOTALS (not individual transaction sums)
    # This prevents inconsistencies when some income types don't have GD deductions in individual records
    for date_str in date_map:
        day_gross = date_map[date_str]['gross_earning']
        
        # Calculate deductions as percentages of day total (DC Protocol: Single source of truth)
        date_map[date_str]['paid_guru_dakshina'] = round(day_gross * 0.02, 2)  # 2% GD
        date_map[date_str]['tds_admin'] = round(day_gross * 0.10, 2)  # 10% (8% admin + 2% TDS)
        date_map[date_str]['final_earning'] = round(day_gross * 0.88, 2)  # 88% net after all deductions
    
    # Convert to list and limit
    day_wise_list = list(date_map.values())[:limit]
    
    # Get user and historical earnings
    # DC Protocol Fix: Use target_user_id (resolved from "me") not the literal user_id
    user = db.query(User).filter(User.id == target_user_id).first()
    historical_total = float(user.earned_total or 0) if user else 0
    
    # DC Protocol: Use WalletService as SINGLE SOURCE OF TRUTH for totals
    # DC Protocol Fix: Use target_user_id (resolved from "me") for all queries
    from app.services.wallet_service import WalletService
    wallet_service = WalletService(db)
    earnings_summary = wallet_service.get_earnings_summary(target_user_id)
    
    # Calculate totals from WalletService (SINGLE SOURCE OF TRUTH) WITH POINTS
    # DC Protocol: Calculate other_adjustments from total - known types
    total_known_types = (
        earnings_summary.get('direct_referral_total', 0) +
        earnings_summary.get('matching_referral_total', 0) +
        earnings_summary.get('ved_income_total', 0) +
        earnings_summary.get('guru_dakshina_total', 0)
    )
    other_adjustments_total = earnings_summary.get('total_gross_earnings', 0) - total_known_types
    
    totals = {
        'direct_referral': earnings_summary.get('direct_referral_total', 0),
        'direct_points': earnings_summary.get('direct_referral_count', 0),  # Activations
        'matching_referral': earnings_summary.get('matching_referral_total', 0),
        'matching_points': int(earnings_summary.get('matching_referral_total', 0) / 2000) if earnings_summary.get('matching_referral_total', 0) > 0 else 0,  # Pairs
        'ved_income': earnings_summary.get('ved_income_total', 0),
        'ved_points': earnings_summary.get('ved_income_count', 0),  # Ved activations
        'earned_guru_dakshina': earnings_summary.get('guru_dakshina_total', 0),
        'gd_points': '2%',  # GD rate
        'other_adjustments': round(other_adjustments_total, 2),  # DC Protocol: Manual adjustments, bonanza, etc.
        'gross_earning': earnings_summary.get('total_gross_earnings', 0),
        'paid_guru_dakshina': earnings_summary.get('total_gurudakshina_deduction', 0),
        'tds_admin': earnings_summary.get('total_admin_deduction', 0) + earnings_summary.get('total_tds_deduction', 0),
        'final_earning': earnings_summary.get('total_net_earnings', 0),
        'historical_total': historical_total  # Total historical earnings from earned_total field
    }
    
    # DC Protocol Phase 1.6: Get wallet balances from materialized views (computed values)
    # DC Protocol Fix: Use target_user_id (resolved from "me") for wallet queries
    from app.services.wallet_balance_service import get_earning_wallet, get_withdrawable_wallet
    wallet_info = {
        'earning_wallet': float(get_earning_wallet(db, target_user_id)),
        'withdrawable_wallet': float(get_withdrawable_wallet(db, target_user_id)),
        'earned_total': historical_total  # Add historical total to wallet info
    }
    
    return {
        "success": True,
        "data": {
            "user_id": target_user_id,
            "filter_applied": {
                "start_date": start_date,
                "end_date": end_date,
                "month": month,
                "limit": limit
            },
            "day_wise_breakdown": day_wise_list,
            "totals": totals,
            "wallet_balances": wallet_info
        }
    }

@router.get("/{user_id}/day-wise-income")
async def get_day_wise_income(
    user_id: str,
    income_type: Optional[str] = Query(default=None, description="Filter by income type: Direct Referral, Matching Referral, Ved Income, Guru Dakshina"),
    limit: int = Query(default=30, ge=1, le=90, description="Number of days to retrieve"),
    current_user = Depends(get_current_user_hybrid),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get day-wise income breakdown for user
    Shows daily income reports with consolidated totals
    """
    from app.models.transaction import PendingIncome
    from sqlalchemy import func, desc
    
    # DC Protocol: Menu-based access control - any authenticated staff has full access
    if current_user.id != user_id and not hasattr(current_user, 'emp_code'):
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Build query
    query = db.query(
        func.date(PendingIncome.business_date).label('date'),
        PendingIncome.income_type,
        func.sum(PendingIncome.gross_amount).label('gross_total'),
        func.sum(PendingIncome.net_amount).label('net_total'),
        func.sum(PendingIncome.admin_deduction).label('admin_deduction_total'),
        func.sum(PendingIncome.tds_deduction).label('tds_deduction_total'),
        func.count(PendingIncome.id).label('transaction_count')
    ).filter(
        PendingIncome.user_id == user_id
    )
    
    # Filter by income type if specified
    if income_type:
        query = query.filter(PendingIncome.income_type == income_type)
    
    # Group by date and income type
    query = query.group_by(func.date(PendingIncome.business_date), PendingIncome.income_type)
    query = query.order_by(desc(func.date(PendingIncome.business_date)))
    query = query.limit(limit)
    
    results = query.all()
    
    # Format day-wise data
    day_wise_data = []
    for row in results:
        day_wise_data.append({
            "date": row.date.isoformat() if row.date else None,
            "income_type": row.income_type,
            "gross_amount": float(row.gross_total or 0),
            "net_amount": float(row.net_total or 0),
            "admin_deduction": float(row.admin_deduction_total or 0),
            "tds_deduction": float(row.tds_deduction_total or 0),
            "transaction_count": row.transaction_count
        })
    
    # Calculate consolidated totals
    consolidated_query = db.query(
        func.sum(PendingIncome.gross_amount).label('total_gross'),
        func.sum(PendingIncome.net_amount).label('total_net'),
        func.sum(PendingIncome.admin_deduction).label('total_admin_deduction'),
        func.sum(PendingIncome.tds_deduction).label('total_tds'),
        func.count(PendingIncome.id).label('total_count')
    ).filter(
        PendingIncome.user_id == user_id
    )
    
    if income_type:
        consolidated_query = consolidated_query.filter(PendingIncome.income_type == income_type)
    
    consolidated = consolidated_query.first()
    
    return {
        "success": True,
        "data": {
            "user_id": user_id,
            "income_type_filter": income_type or "All",
            "day_wise_breakdown": day_wise_data,
            "consolidated_totals": {
                "gross_amount": float(consolidated.total_gross or 0),
                "net_amount": float(consolidated.total_net or 0),
                "admin_deduction": float(consolidated.total_admin_deduction or 0),
                "tds_deduction": float(consolidated.total_tds or 0),
                "total_transactions": consolidated.total_count or 0
            }
        }
    }

@router.get("/transactions/{user_id}/history")
async def get_transaction_history(
    user_id: str,
    limit: int = Query(default=50, ge=1, le=200, description="Number of transactions to retrieve"),
    current_user = Depends(get_current_user_hybrid),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get user's financial transaction history
    Preserves Flask transaction history functionality
    """
    # DC Protocol: Menu-based access control - any authenticated staff has full access
    if current_user.id != user_id and not hasattr(current_user, 'emp_code'):
        raise HTTPException(status_code=403, detail="Access denied")
    
    user_service = UserService(db)
    
    # Get financial history
    financial_history = user_service.get_user_financial_history(user_id, limit)
    
    if "error" in financial_history:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=financial_history["error"]
        )
    
    return {
        "success": True,
        "transaction_history": financial_history
    }

@router.get("/admin/financial-overview")
async def get_admin_financial_overview(
    month: Optional[str] = Query(default=None, description="Month in YYYY-MM format"),
    current_user: User = Depends(require_finance_admin),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get comprehensive financial overview for admin dashboard
    Finance Admin only functionality
    """
    from app.models.transaction import Transaction, CompanyEarnings
    from sqlalchemy import func, and_
    
    if not month:
        month = datetime.now().strftime("%Y-%m")
    
    # Get company earnings for the month
    company_earnings = db.query(CompanyEarnings).filter(
        CompanyEarnings.financial_period == month
    ).first()
    
    # Get total payouts by income type
    payout_summary = db.query(
        Transaction.income_type,
        func.count(Transaction.id).label('transaction_count'),
        func.sum(Transaction.gross_amount).label('total_gross'),
        func.sum(Transaction.net_amount).label('total_net')
    ).filter(
        and_(
            Transaction.financial_period == month,
            Transaction.transaction_type == 'credit'
        )
    ).group_by(Transaction.income_type).all()
    
    # Get total deductions
    total_deductions = db.query(func.sum(Transaction.net_amount)).filter(
        and_(
            Transaction.financial_period == month,
            Transaction.transaction_type == 'debit'
        )
    ).scalar() or 0
    
    # Format payout breakdown
    payout_breakdown = []
    total_payouts = 0
    for summary in payout_summary:
        payout_breakdown.append({
            "income_type": summary.income_type,
            "transaction_count": summary.transaction_count,
            "total_gross": float(summary.total_gross),
            "total_net": float(summary.total_net)
        })
        total_payouts += float(summary.total_net)
    
    return {
        "success": True,
        "financial_overview": {
            "period": month,
            "company_performance": {
                "gross_income": float(company_earnings.gross_income) if company_earnings else 0.0,
                "net_profit": float(company_earnings.net_profit) if company_earnings else 0.0,
                "profit_margin": float(company_earnings.profit_margin) if company_earnings else 0.0
            },
            "member_payouts": {
                "total_payouts": total_payouts,
                "total_deductions": float(total_deductions),
                "net_member_payments": total_payouts - float(total_deductions),
                "payout_breakdown": payout_breakdown
            }
        }
    }

@router.get("/admin/income-analytics")
async def get_income_analytics(
    start_month: str = Query(..., description="Start month in YYYY-MM format"),
    end_month: str = Query(..., description="End month in YYYY-MM format"),
    current_user: User = Depends(require_finance_admin),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get detailed income analytics for date range
    Finance Admin only functionality
    """
    from app.models.transaction import Transaction
    from sqlalchemy import func, and_
    
    # Validate date range
    try:
        start_date = datetime.strptime(f"{start_month}-01", "%Y-%m-%d")
        end_date = datetime.strptime(f"{end_month}-01", "%Y-%m-%d")
        
        if start_date > end_date:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Start month must be before end month."
            )
    
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid date format. Use YYYY-MM."
        )
    
    # Generate month list
    current_date = start_date
    months = []
    while current_date <= end_date:
        months.append(current_date.strftime("%Y-%m"))
        # Move to next month
        if current_date.month == 12:
            current_date = current_date.replace(year=current_date.year + 1, month=1)
        else:
            current_date = current_date.replace(month=current_date.month + 1)
    
    # Get income data for each month
    monthly_analytics = []
    for month in months:
        # Get income by type for this month
        monthly_income = db.query(
            Transaction.income_type,
            func.count(Transaction.id).label('count'),
            func.sum(Transaction.net_amount).label('total')
        ).filter(
            and_(
                Transaction.financial_period == month,
                Transaction.transaction_type == 'credit'
            )
        ).group_by(Transaction.income_type).all()
        
        month_data = {
            "month": month,
            "income_streams": {},
            "total_month_income": 0
        }
        
        for income in monthly_income:
            month_data["income_streams"][income.income_type] = {
                "count": income.count,
                "total": float(income.total)
            }
            month_data["total_month_income"] += float(income.total)
        
        monthly_analytics.append(month_data)
    
    return {
        "success": True,
        "income_analytics": {
            "period": f"{start_month} to {end_month}",
            "monthly_data": monthly_analytics,
            "summary": {
                "total_months": len(months),
                "total_income": sum(month["total_month_income"] for month in monthly_analytics),
                "average_monthly_income": sum(month["total_month_income"] for month in monthly_analytics) / len(months) if months else 0
            }
        }
    }

@router.get("/wallet/{user_id}/balance")
async def get_wallet_balance(
    user_id: str,
    current_user = Depends(get_current_user_hybrid),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get user's wallet balance and recent activity
    Preserves Flask wallet functionality
    """
    # DC Protocol: Menu-based access control - any authenticated staff has full access
    if current_user.id != user_id and not hasattr(current_user, 'emp_code'):
        raise HTTPException(status_code=403, detail="Access denied")
    
    user_service = UserService(db)
    
    # Get user
    user = user_service.get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found."
        )
    
    # Get recent wallet transactions
    from app.models.transaction import Transaction
    recent_transactions = db.query(Transaction).filter(
        Transaction.user_id == user_id
    ).order_by(Transaction.transaction_date.desc()).limit(10).all()
    
    wallet_transactions = []
    for transaction in recent_transactions:
        wallet_transactions.append({
            "id": transaction.id,
            "type": transaction.transaction_type,
            "income_type": transaction.income_type,
            "amount": float(transaction.net_amount),
            "date": transaction.transaction_date.isoformat(),
            "description": transaction.description,
            "period": transaction.financial_period
        })
    
    return {
        "success": True,
        "wallet_data": {
            "user_id": user_id,
            "current_balance": float(getattr(user, 'wallet_balance', 0)),
            "recent_transactions": wallet_transactions,
            "transaction_count": len(wallet_transactions)
        }
    }